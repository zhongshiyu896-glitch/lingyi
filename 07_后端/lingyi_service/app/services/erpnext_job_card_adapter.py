"""ERPNext adapter for Job Card / Employee integration (TASK-003)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from decimal import Decimal
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from fastapi import Request

from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError


@dataclass(frozen=True)
class JobCardInfo:
    """ERPNext Job Card snapshot."""

    name: str
    operation: str
    status: str
    work_order: str | None
    item_code: str | None
    company: str | None = None


@dataclass(frozen=True)
class WorkOrderInfo:
    """ERPNext Work Order snapshot."""

    name: str
    production_item: str | None
    company: str | None


@dataclass(frozen=True)
class EmployeeInfo:
    """ERPNext Employee snapshot."""

    name: str
    status: str | None
    disabled: bool

    @property
    def is_active(self) -> bool:
        status_value = (self.status or "").strip().lower()
        if self.disabled:
            return False
        if status_value in {"left", "inactive", "disabled"}:
            return False
        return True


@dataclass(frozen=True)
class ItemInfo:
    """ERPNext Item snapshot for wage-rate resource resolution."""

    name: str
    item_code: str
    disabled: bool
    companies: tuple[str, ...]

    @property
    def is_active(self) -> bool:
        return not self.disabled


@dataclass(frozen=True)
class CompanyInfo:
    """ERPNext Company snapshot."""

    name: str
    disabled: bool

    @property
    def is_active(self) -> bool:
        return not self.disabled


class ERPNextJobCardAdapter:
    """Adapter that calls ERPNext REST APIs without direct DB write."""

    def __init__(self, request_obj: Request | None = None, *, use_service_account: bool = False):
        self.request_obj = request_obj
        self.use_service_account = use_service_account
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")

    def get_job_card(self, job_card: str) -> JobCardInfo | None:
        """Read Job Card by name."""
        payload = self._get_json(f"/api/resource/Job%20Card/{parse.quote(job_card, safe='')}", allow_404=True)
        if not payload:
            return None
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Job Card 返回结构异常")
        operation = str(data.get("operation") or "").strip()
        if not operation:
            operation = str(data.get("operation_name") or "").strip()
        return JobCardInfo(
            name=str(data.get("name") or job_card),
            operation=operation,
            status=str(data.get("status") or ""),
            work_order=(str(data.get("work_order")).strip() if data.get("work_order") is not None else None),
            item_code=(str(data.get("production_item")).strip() if data.get("production_item") is not None else None),
            company=(str(data.get("company")).strip() if data.get("company") is not None else None),
        )

    def get_work_order(self, work_order: str) -> WorkOrderInfo | None:
        """Read Work Order by name."""
        payload = self._get_json(f"/api/resource/Work%20Order/{parse.quote(work_order, safe='')}", allow_404=True)
        if not payload:
            return None
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Work Order 返回结构异常")
        return WorkOrderInfo(
            name=str(data.get("name") or work_order),
            production_item=(str(data.get("production_item")).strip() if data.get("production_item") is not None else None),
            company=(str(data.get("company")).strip() if data.get("company") is not None else None),
        )

    def get_employee(self, employee: str) -> EmployeeInfo | None:
        """Read Employee by name."""
        payload = self._get_json(f"/api/resource/Employee/{parse.quote(employee, safe='')}", allow_404=True)
        if not payload:
            return None
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Employee 返回结构异常")
        disabled_value = data.get("status") if data.get("status") in {0, 1} else data.get("disabled")
        disabled = bool(disabled_value) if disabled_value is not None else False
        return EmployeeInfo(
            name=str(data.get("name") or employee),
            status=(str(data.get("status")).strip() if data.get("status") is not None else None),
            disabled=disabled,
        )

    def get_item(self, item_code: str) -> ItemInfo | None:
        """Read Item by name and parse company candidates.

        - Item 不存在(HTTP 404): 返回 None，供业务侧归类为“候选为空”
        - ERPNext 服务不可用/超时/结构异常: 抛 ERPNextServiceUnavailableError，供业务侧 fail closed
        """
        fields = parse.quote('["name","item_code","disabled","default_company","item_defaults"]', safe="")
        payload = self._get_json(
            f"/api/resource/Item/{parse.quote(item_code, safe='')}?fields={fields}",
            allow_404=True,
        )
        if not payload:
            return None
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Item 返回结构异常")

        companies: set[str] = set()
        default_company = data.get("default_company")
        if isinstance(default_company, str) and default_company.strip():
            companies.add(default_company.strip())

        item_defaults = data.get("item_defaults")
        if isinstance(item_defaults, list):
            for row in item_defaults:
                if not isinstance(row, dict):
                    continue
                company_name = row.get("company") or row.get("default_company")
                if isinstance(company_name, str) and company_name.strip():
                    companies.add(company_name.strip())

        return ItemInfo(
            name=str(data.get("name") or item_code),
            item_code=str(data.get("item_code") or data.get("name") or item_code),
            disabled=self._to_bool(data.get("disabled")),
            companies=tuple(sorted(companies)),
        )

    def get_company(self, company: str) -> CompanyInfo | None:
        """Read Company by name."""
        fields = parse.quote('["name","disabled"]', safe="")
        payload = self._get_json(
            f"/api/resource/Company/{parse.quote(company, safe='')}?fields={fields}",
            allow_404=True,
        )
        if not payload:
            return None
        data = payload.get("data", {})
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Company 返回结构异常")
        return CompanyInfo(
            name=str(data.get("name") or company),
            disabled=self._to_bool(data.get("disabled")),
        )

    def list_active_companies(self) -> list[CompanyInfo]:
        """List active companies from ERPNext."""
        fields = parse.quote('["name","disabled"]', safe="")
        payload = self._get_json(f"/api/resource/Company?fields={fields}&limit_page_length=200")
        if not payload:
            return []
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise ERPNextServiceUnavailableError("ERPNext Company 列表返回结构异常")

        companies: list[CompanyInfo] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = row.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            info = CompanyInfo(name=name.strip(), disabled=self._to_bool(row.get("disabled")))
            if info.is_active:
                companies.append(info)
        return companies

    def update_job_card_completed_qty(
        self,
        *,
        job_card: str,
        completed_qty: Decimal,
        request_id: str,
    ) -> dict[str, Any]:
        """Sync local net completed qty to ERPNext Job Card."""
        body = {"completed_qty": str(completed_qty), "custom_request_id": request_id}
        payload = self._request_json(
            method="PUT",
            path=f"/api/resource/Job%20Card/{parse.quote(job_card, safe='')}",
            body=body,
        )
        if not isinstance(payload, dict):
            raise ERPNextServiceUnavailableError("ERPNext Job Card 同步返回结构异常")
        return payload

    def _get_json(self, path: str, *, allow_404: bool = False) -> dict[str, Any] | None:
        return self._request_json(method="GET", path=path, body=None, allow_404=allow_404)

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        allow_404: bool = False,
    ) -> dict[str, Any] | None:
        if not self.base_url:
            raise ERPNextServiceUnavailableError("ERPNext 服务未配置")

        headers = self._build_headers()
        data = json.dumps(body).encode("utf-8") if body is not None else None
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            data=data,
            headers=headers,
        )
        try:
            with request.urlopen(req, timeout=8) as response:
                text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            if self.use_service_account and exc.code in {401, 403}:
                raise ERPNextServiceAccountForbiddenError("ERPNext 服务账号权限不足") from exc
            raise ERPNextServiceUnavailableError(f"ERPNext 请求失败: {exc.code}") from exc
        except (error.URLError, TimeoutError) as exc:
            raise ERPNextServiceUnavailableError("ERPNext 服务不可用") from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise ERPNextServiceUnavailableError("ERPNext 调用异常") from exc

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ERPNextServiceUnavailableError("ERPNext 返回非 JSON") from exc
        if not isinstance(payload, dict):
            raise ERPNextServiceUnavailableError("ERPNext 返回结构异常")
        return payload

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.use_service_account:
            service_token = os.getenv("LINGYI_ERPNEXT_SERVICE_TOKEN", "").strip()
            if not service_token:
                raise ERPNextServiceUnavailableError("ERPNext 服务账号未配置")
            normalized = service_token
            lowered = normalized.lower()
            if not (lowered.startswith("token ") or lowered.startswith("bearer ")):
                normalized = f"token {normalized}"
            headers["Authorization"] = normalized
            return headers

        if self.request_obj is not None:
            authorization = self.request_obj.headers.get("Authorization")
            cookie = self.request_obj.headers.get("Cookie")
            if authorization:
                headers["Authorization"] = authorization
            if cookie:
                headers["Cookie"] = cookie
        return headers

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return False
