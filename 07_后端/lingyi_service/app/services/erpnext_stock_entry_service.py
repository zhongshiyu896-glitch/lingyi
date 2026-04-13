"""ERPNext Stock Entry adapter for subcontract stock outbox (TASK-002D)."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from app.core.error_codes import ERPNEXT_STOCK_ENTRY_CREATE_FAILED
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_STATUS_INVALID
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED
from app.core.exceptions import BusinessException
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError


@dataclass(frozen=True)
class ERPNextStockEntryLookup:
    """Existing ERPNext Stock Entry matched by outbox event key."""

    name: str
    docstatus: int


class ERPNextStockEntryService:
    """Create/submit/query ERPNext Stock Entry with service-account token."""

    def __init__(self):
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")

    def find_by_event_key(self, *, event_key: str) -> ERPNextStockEntryLookup | None:
        """Find existing stock entry by custom outbox event key."""
        encoded_fields = parse.quote('["name","docstatus","custom_ly_outbox_event_key"]', safe="")
        filters = parse.quote(json.dumps([["custom_ly_outbox_event_key", "=", event_key]]), safe="")
        payload = self._request_json(
            method="GET",
            path=f"/api/resource/Stock%20Entry?fields={encoded_fields}&filters={filters}&limit_page_length=2",
            body=None,
            allow_404=True,
        )
        if not payload:
            return None
        rows = payload.get("data", [])
        if not isinstance(rows, list) or not rows:
            return None
        if len(rows) > 1:
            raise BusinessException(
                code=ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY,
                message="ERPNext event_key 命中多条 Stock Entry，禁止继续同步",
            )
        row = rows[0]
        if not isinstance(row, dict):
            return None
        name = row.get("name")
        if not (isinstance(name, str) and name.strip()):
            raise BusinessException(
                code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID,
                message="ERPNext Stock Entry 返回异常，缺少 name",
            )
        docstatus_raw = row.get("docstatus", 0)
        try:
            docstatus = int(docstatus_raw)
        except (TypeError, ValueError) as exc:
            raise BusinessException(
                code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID,
                message="ERPNext Stock Entry docstatus 非法",
            ) from exc
        return ERPNextStockEntryLookup(name=name.strip(), docstatus=docstatus)

    def create_material_issue(self, *, payload_json: dict[str, Any]) -> str:
        """Create ERPNext Stock Entry and return name."""
        payload = self._request_json(
            method="POST",
            path="/api/resource/Stock%20Entry",
            body=payload_json,
        )
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict):
            name = data.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
        raise BusinessException(code=ERPNEXT_STOCK_ENTRY_CREATE_FAILED, message="ERPNext Stock Entry 创建失败")

    def submit_stock_entry(self, *, stock_entry_name: str) -> None:
        """Submit ERPNext Stock Entry by name."""
        payload = self._request_json(
            method="POST",
            path="/api/method/frappe.client.submit",
            body={"doctype": "Stock Entry", "name": stock_entry_name},
        )
        if not isinstance(payload, dict):
            raise BusinessException(code=ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED, message="ERPNext Stock Entry 提交失败")

    def create_and_submit_material_issue(self, *, payload_json: dict[str, Any]) -> str:
        """Create then submit Stock Entry and return final docname."""
        name = self.create_material_issue(payload_json=payload_json)
        self.submit_stock_entry(stock_entry_name=name)
        return name

    def create_material_receipt(self, *, payload_json: dict[str, Any]) -> str:
        """Create ERPNext Material Receipt and return name."""
        return self.create_material_issue(payload_json=payload_json)

    def create_and_submit_material_receipt(self, *, payload_json: dict[str, Any]) -> str:
        """Create then submit Material Receipt and return final docname."""
        name = self.create_material_receipt(payload_json=payload_json)
        self.submit_stock_entry(stock_entry_name=name)
        return name

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
            headers=headers,
            data=data,
        )

        try:
            with request.urlopen(req, timeout=10) as response:
                text = response.read().decode("utf-8")
        except error.HTTPError as exc:
            if allow_404 and exc.code == 404:
                return None
            if exc.code in {401, 403}:
                raise ERPNextServiceAccountForbiddenError("ERPNext 服务账号权限不足") from exc
            if method == "POST" and path.endswith("Stock%20Entry"):
                raise BusinessException(code=ERPNEXT_STOCK_ENTRY_CREATE_FAILED, message="ERPNext Stock Entry 创建失败") from exc
            if method == "POST" and path.endswith("frappe.client.submit"):
                raise BusinessException(code=ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED, message="ERPNext Stock Entry 提交失败") from exc
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

    @staticmethod
    def _build_headers() -> dict[str, str]:
        token = os.getenv("LINGYI_ERPNEXT_SERVICE_TOKEN", "").strip()
        if not token:
            raise ERPNextServiceUnavailableError("ERPNext 服务账号未配置")
        normalized = token
        lowered = normalized.lower()
        if not (lowered.startswith("token ") or lowered.startswith("bearer ")):
            normalized = f"token {normalized}"
        return {"Accept": "application/json", "Authorization": normalized}
