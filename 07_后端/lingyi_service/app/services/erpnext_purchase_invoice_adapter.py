"""ERPNext adapter for Factory Statement payable draft outbox (TASK-006D)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from fastapi import Request

from app.core.error_codes import FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS
from app.core.error_codes import FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE
from app.core.exceptions import BusinessException
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError


@dataclass(frozen=True)
class ERPNextPurchaseInvoiceLookup:
    """ERPNext Purchase Invoice snapshot."""

    name: str
    docstatus: int
    status: str | None


class ERPNextPurchaseInvoiceAdapter:
    """Adapter for Purchase Invoice read/create under strict fail-closed policy."""

    def __init__(self, request_obj: Request | None = None, *, use_service_account: bool = False):
        self.request_obj = request_obj
        self.use_service_account = use_service_account
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")

    def validate_payable_account(self, *, company: str, payable_account: str) -> bool:
        account = str(payable_account or "").strip()
        if not account:
            return False
        payload = self._request_json(
            method="GET",
            path=(
                f"/api/resource/Account/{parse.quote(account, safe='')}"
                f"?fields={parse.quote('[\"name\",\"company\",\"disabled\",\"is_group\"]', safe='')}"
            ),
            body=None,
            allow_404=True,
        )
        if not payload:
            return False
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Account 返回结构异常")
        if self._to_bool(data.get("disabled")):
            return False
        if self._to_bool(data.get("is_group")):
            return False
        account_company = str(data.get("company") or "").strip()
        if account_company and account_company != str(company or "").strip():
            return False
        return True

    def validate_cost_center(self, *, company: str, cost_center: str) -> bool:
        center = str(cost_center or "").strip()
        if not center:
            return False
        payload = self._request_json(
            method="GET",
            path=(
                f"/api/resource/Cost%20Center/{parse.quote(center, safe='')}"
                f"?fields={parse.quote('[\"name\",\"company\",\"disabled\",\"is_group\"]', safe='')}"
            ),
            body=None,
            allow_404=True,
        )
        if not payload:
            return False
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Cost Center 返回结构异常")
        if self._to_bool(data.get("disabled")):
            return False
        if self._to_bool(data.get("is_group")):
            return False
        center_company = str(data.get("company") or "").strip()
        if center_company and center_company != str(company or "").strip():
            return False
        return True

    def find_purchase_invoice_by_event_key(self, *, event_key: str) -> ERPNextPurchaseInvoiceLookup | None:
        encoded_fields = parse.quote('["name","docstatus","status","custom_ly_outbox_event_key"]', safe="")
        filters = parse.quote(json.dumps([["custom_ly_outbox_event_key", "=", event_key]], ensure_ascii=False), safe="")
        payload = self._request_json(
            method="GET",
            path=f"/api/resource/Purchase%20Invoice?fields={encoded_fields}&filters={filters}&limit_page_length=2",
            body=None,
            allow_404=True,
        )
        if not payload:
            return None
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            return None
        if len(rows) > 1:
            raise BusinessException(
                code=FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS,
                message="ERPNext outbox_event_key 命中多条 Purchase Invoice，禁止继续处理",
            )
        return self._to_lookup(rows[0])

    def get_purchase_invoice(self, *, purchase_invoice: str) -> ERPNextPurchaseInvoiceLookup | None:
        payload = self._request_json(
            method="GET",
            path=(
                f"/api/resource/Purchase%20Invoice/{parse.quote(purchase_invoice, safe='')}"
                f"?fields={parse.quote('[\"name\",\"docstatus\",\"status\"]', safe='')}"
            ),
            body=None,
            allow_404=True,
        )
        if not payload:
            return None
        data = payload.get("data") if isinstance(payload, dict) else None
        return self._to_lookup(data)

    def create_purchase_invoice_draft(self, *, payload_json: dict[str, Any]) -> ERPNextPurchaseInvoiceLookup:
        payload = self._request_json(
            method="POST",
            path="/api/resource/Purchase%20Invoice",
            body=payload_json,
            allow_404=False,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise BusinessException(code=FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE, message="ERPNext Purchase Invoice 创建失败")

        name = str(data.get("name") or "").strip()
        if not name:
            raise BusinessException(code=FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE, message="ERPNext Purchase Invoice 返回缺少 name")

        lookup = self._to_lookup(data, require_name=False)
        if lookup is not None:
            return ERPNextPurchaseInvoiceLookup(name=name, docstatus=lookup.docstatus, status=lookup.status)

        reloaded = self.get_purchase_invoice(purchase_invoice=name)
        if reloaded is None:
            raise BusinessException(code=FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE, message="ERPNext Purchase Invoice 创建后查询失败")
        return reloaded

    def _to_lookup(self, raw: Any, *, require_name: bool = True) -> ERPNextPurchaseInvoiceLookup | None:
        if not isinstance(raw, dict):
            return None
        name = str(raw.get("name") or "").strip()
        if require_name and not name:
            raise BusinessException(
                code=FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS,
                message="ERPNext Purchase Invoice 返回缺少 name",
            )
        if not name:
            return None
        docstatus_raw = raw.get("docstatus")
        try:
            docstatus = int(docstatus_raw)
        except Exception as exc:
            raise BusinessException(
                code=FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS,
                message="ERPNext Purchase Invoice docstatus 非法",
            ) from exc
        status = str(raw.get("status") or "").strip() or None
        return ERPNextPurchaseInvoiceLookup(name=name, docstatus=docstatus, status=status)

    def _request_json(
        self,
        *,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        allow_404: bool,
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
            headers=headers,
            data=data,
        )
        try:
            with request.urlopen(req, timeout=10) as response:
                text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            if self.use_service_account and exc.code in {401, 403}:
                raise ERPNextServiceAccountForbiddenError("ERPNext 服务账号权限不足") from exc
            raise ERPNextServiceUnavailableError(f"ERPNext 请求失败: {exc.code}") from exc
        except (error.URLError, TimeoutError) as exc:
            raise ERPNextServiceUnavailableError("ERPNext 服务不可用") from exc
        except Exception as exc:  # pragma: no cover
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
            token = os.getenv("LINGYI_ERPNEXT_SERVICE_TOKEN", "").strip()
            if not token:
                raise ERPNextServiceUnavailableError("ERPNext 服务账号未配置")
            normalized = token
            lowered = normalized.lower()
            if not (lowered.startswith("token ") or lowered.startswith("bearer ")):
                normalized = f"token {normalized}"
            headers["Authorization"] = normalized
            return headers

        if self.request_obj is not None:
            auth = self.request_obj.headers.get("Authorization")
            cookie = self.request_obj.headers.get("Cookie")
            if auth:
                headers["Authorization"] = auth
            if cookie:
                headers["Cookie"] = cookie
        return headers

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return int(value) != 0
        text = str(value).strip().lower()
        return text in {"1", "true", "yes", "y"}
