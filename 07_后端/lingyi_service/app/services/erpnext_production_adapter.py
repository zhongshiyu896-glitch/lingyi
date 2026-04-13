"""ERPNext adapter for production planning and Work Order sync (TASK-004A)."""

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

from app.core.error_codes import PRODUCTION_WORK_ORDER_ALREADY_EXISTS
from app.core.error_codes import PRODUCTION_WORK_ORDER_SYNC_FAILED
from app.core.exceptions import BusinessException
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError


@dataclass(frozen=True)
class ERPNextSalesOrderItem:
    """ERPNext Sales Order item snapshot."""

    name: str
    item_code: str
    qty: Decimal


@dataclass(frozen=True)
class ERPNextSalesOrder:
    """ERPNext Sales Order snapshot."""

    name: str
    docstatus: int
    status: str
    company: str
    customer: str | None
    items: tuple[ERPNextSalesOrderItem, ...]


@dataclass(frozen=True)
class ERPNextWorkOrder:
    """ERPNext Work Order snapshot."""

    name: str
    docstatus: int
    status: str | None


@dataclass(frozen=True)
class ERPNextJobCard:
    """ERPNext Job Card snapshot."""

    name: str
    operation: str | None
    operation_sequence: int | None
    expected_qty: Decimal
    completed_qty: Decimal
    status: str | None


class ERPNextProductionAdapter:
    """Adapter for ERPNext production APIs.

    - User read paths use current request auth/session headers.
    - Worker write paths use service-account token.
    """

    def __init__(self, request_obj: Request | None = None, *, use_service_account: bool = False):
        self.request_obj = request_obj
        self.use_service_account = use_service_account
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")

    def get_sales_order(self, *, sales_order: str) -> ERPNextSalesOrder | None:
        """Read Sales Order with child items by docname."""
        fields = parse.quote('["name","docstatus","status","company","customer","items"]', safe="")
        payload = self._request_json(
            method="GET",
            path=f"/api/resource/Sales%20Order/{parse.quote(sales_order, safe='')}?fields={fields}",
            body=None,
            allow_404=True,
        )
        if not payload:
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Sales Order 返回结构异常")

        items_raw = data.get("items")
        if not isinstance(items_raw, list):
            items_raw = []

        items: list[ERPNextSalesOrderItem] = []
        for row in items_raw:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            item_code = str(row.get("item_code") or "").strip()
            qty = self._to_decimal(row.get("qty"), default=Decimal("0"))
            if not name or not item_code:
                continue
            items.append(ERPNextSalesOrderItem(name=name, item_code=item_code, qty=qty))

        return ERPNextSalesOrder(
            name=str(data.get("name") or sales_order),
            docstatus=self._to_int(data.get("docstatus"), default=0),
            status=str(data.get("status") or "").strip(),
            company=str(data.get("company") or "").strip(),
            customer=(str(data.get("customer")).strip() if data.get("customer") is not None else None),
            items=tuple(items),
        )

    def find_work_order_by_plan(self, *, plan_id: int, plan_no: str) -> ERPNextWorkOrder | None:
        """Find ERPNext Work Order by project custom trace fields."""
        fields = parse.quote('["name","docstatus","status"]', safe="")
        filters = parse.quote(
            json.dumps(
                [["custom_ly_plan_id", "=", str(plan_id)], ["custom_ly_plan_no", "=", str(plan_no)]],
                ensure_ascii=False,
            ),
            safe="",
        )
        payload = self._request_json(
            method="GET",
            path=f"/api/resource/Work%20Order?fields={fields}&filters={filters}&limit_page_length=2",
            body=None,
            allow_404=True,
        )
        if not payload:
            return None
        rows = payload.get("data")
        if not isinstance(rows, list) or not rows:
            return None
        if len(rows) > 1:
            raise BusinessException(
                code=PRODUCTION_WORK_ORDER_ALREADY_EXISTS,
                message="ERPNext Work Order 命中多条记录，禁止继续同步",
            )
        row = rows[0]
        if not isinstance(row, dict):
            raise ERPNextServiceUnavailableError("ERPNext Work Order 查询返回结构异常")
        name = str(row.get("name") or "").strip()
        if not name:
            raise ERPNextServiceUnavailableError("ERPNext Work Order 查询缺少 name")
        return ERPNextWorkOrder(
            name=name,
            docstatus=self._to_int(row.get("docstatus"), default=0),
            status=(str(row.get("status")).strip() if row.get("status") is not None else None),
        )

    def get_work_order(self, *, work_order: str) -> ERPNextWorkOrder | None:
        """Read ERPNext Work Order by docname."""
        fields = parse.quote('["name","docstatus","status"]', safe="")
        payload = self._request_json(
            method="GET",
            path=f"/api/resource/Work%20Order/{parse.quote(work_order, safe='')}?fields={fields}",
            body=None,
            allow_404=True,
        )
        if not payload:
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ERPNextServiceUnavailableError("ERPNext Work Order 返回结构异常")
        name = str(data.get("name") or work_order).strip()
        return ERPNextWorkOrder(
            name=name,
            docstatus=self._to_int(data.get("docstatus"), default=0),
            status=(str(data.get("status")).strip() if data.get("status") is not None else None),
        )

    def create_work_order(self, *, payload_json: dict[str, Any]) -> str:
        """Create ERPNext Work Order and return docname."""
        payload = self._request_json(
            method="POST",
            path="/api/resource/Work%20Order",
            body=payload_json,
            allow_404=False,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="ERPNext Work Order 创建失败")

    def submit_work_order(self, *, work_order: str) -> None:
        """Submit ERPNext Work Order by docname."""
        payload = self._request_json(
            method="POST",
            path="/api/method/frappe.client.submit",
            body={"doctype": "Work Order", "name": work_order},
            allow_404=False,
        )
        if not isinstance(payload, dict):
            raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="ERPNext Work Order 提交失败")

    def list_job_cards(self, *, work_order: str) -> list[ERPNextJobCard]:
        """List Job Cards by Work Order."""
        fields = parse.quote('["name","operation","sequence_id","for_quantity","total_completed_qty","status"]', safe="")
        filters = parse.quote(json.dumps([["work_order", "=", work_order]], ensure_ascii=False), safe="")
        payload = self._request_json(
            method="GET",
            path=f"/api/resource/Job%20Card?fields={fields}&filters={filters}&limit_page_length=500",
            body=None,
            allow_404=True,
        )
        if not payload:
            return []
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise ERPNextServiceUnavailableError("ERPNext Job Card 列表返回结构异常")

        cards: list[ERPNextJobCard] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            cards.append(
                ERPNextJobCard(
                    name=name,
                    operation=(str(row.get("operation")).strip() if row.get("operation") is not None else None),
                    operation_sequence=self._to_int(row.get("sequence_id"), default=0) if row.get("sequence_id") is not None else None,
                    expected_qty=self._to_decimal(row.get("for_quantity"), default=Decimal("0")),
                    completed_qty=self._to_decimal(row.get("total_completed_qty"), default=Decimal("0")),
                    status=(str(row.get("status")).strip() if row.get("status") is not None else None),
                )
            )
        return cards

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
    def _to_decimal(value: Any, *, default: Decimal) -> Decimal:
        try:
            if value is None:
                return default
            return Decimal(str(value))
        except Exception:
            return default

    @staticmethod
    def _to_int(value: Any, *, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default
