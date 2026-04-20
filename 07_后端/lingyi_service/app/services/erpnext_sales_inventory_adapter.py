"""Fail-closed ERPNext read adapter for sales/inventory APIs (TASK-011B)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from json import JSONDecodeError
import json
import os
from typing import Any
from urllib import parse
from urllib import request as urllib_request

from fastapi import Request

from app.core.error_codes import ERPNEXT_RESPONSE_INVALID
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import message_of
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_fail_closed_adapter import map_erpnext_exception
from app.services.erpnext_fail_closed_adapter import normalize_erpnext_response
from app.services.erpnext_fail_closed_adapter import require_submitted_doc


class ERPNextSalesInventoryAdapter:
    """Read ERPNext sales/inventory facts with fail-closed validation."""

    SALES_ORDER_FIELDS = [
        "name",
        "company",
        "customer",
        "transaction_date",
        "delivery_date",
        "status",
        "docstatus",
        "grand_total",
        "currency",
    ]
    SALES_ORDER_DETAIL_FIELDS = SALES_ORDER_FIELDS + ["items"]
    SALES_ORDER_ITEM_FIELDS = ["name", "item_code", "item_name", "qty", "delivered_qty", "rate", "amount", "warehouse", "delivery_date"]
    SLE_FIELDS = [
        "name",
        "company",
        "item_code",
        "warehouse",
        "posting_date",
        "posting_time",
        "actual_qty",
        "qty_after_transaction",
        "voucher_type",
        "voucher_no",
    ]
    WAREHOUSE_FIELDS = ["name", "company", "warehouse_name", "disabled"]
    CUSTOMER_FIELDS = ["name", "customer_name", "disabled"]

    def __init__(self, request_obj: Request | None = None):
        self.request_obj = request_obj
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")

    def list_sales_orders(
        self,
        *,
        company: str | None = None,
        customer: str | None = None,
        item_code: str | None = None,
        item_name: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return submitted Sales Order rows."""
        filters: list[list[Any]] = [["docstatus", "=", 1]]
        if company:
            filters.append(["company", "=", company])
        if customer:
            filters.append(["customer", "=", customer])
        if item_code:
            filters.append(["items", "item_code", "=", item_code])
        if item_name:
            filters.append(["items", "item_name", "like", f"%{item_name}%"])
        if from_date is not None:
            filters.append(["transaction_date", ">=", from_date.isoformat()])
        if to_date is not None:
            filters.append(["transaction_date", "<=", to_date.isoformat()])
        rows = self._list_resource(
            doctype="Sales Order",
            fields=self.SALES_ORDER_FIELDS,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="transaction_date desc, name desc",
        )
        return [self._require_sales_order(row) for row in rows], len(rows)

    def get_sales_order(self, *, name: str) -> dict[str, Any]:
        """Return a submitted Sales Order detail."""
        payload = self._request_json(
            f"/api/resource/Sales%20Order/{parse.quote(name, safe='')}?fields={self._encoded_fields(self.SALES_ORDER_DETAIL_FIELDS)}",
            doctype="Sales Order",
            resource_name=name,
        )
        normalized = normalize_erpnext_response(payload, doctype="Sales Order", resource_name=name)
        submitted = require_submitted_doc(normalized)
        data = dict(submitted.data)
        items = data.get("items")
        if items is None:
            data["items"] = []
        elif not isinstance(items, list):
            self._raise_invalid(doctype="Sales Order", resource_name=name, detail="items is not list")
        return data

    def list_stock_ledger(
        self,
        *,
        item_code: str,
        company: str | None = None,
        warehouse: str | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int, int]:
        """Return SLE rows, dropping malformed entries per TASK-011 fail-closed scope."""
        filters: list[list[Any]] = [["item_code", "=", item_code]]
        if company:
            filters.append(["company", "=", company])
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        if from_date is not None:
            filters.append(["posting_date", ">=", from_date.isoformat()])
        if to_date is not None:
            filters.append(["posting_date", "<=", to_date.isoformat()])
        rows = self._list_resource(
            doctype="Stock Ledger Entry",
            fields=self.SLE_FIELDS,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="posting_date desc, posting_time desc, name desc",
        )
        valid: list[dict[str, Any]] = []
        dropped = 0
        for row in rows:
            normalized = self._normalize_sle_row(row)
            if normalized is None:
                dropped += 1
                continue
            valid.append(normalized)
        return valid, len(valid), dropped

    def get_stock_summary(
        self,
        *,
        item_code: str,
        company: str | None = None,
        warehouse: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """Return latest quantity-after-transaction by warehouse."""
        rows, _, dropped = self.list_stock_ledger(
            item_code=item_code,
            company=company,
            warehouse=warehouse,
            page=1,
            page_size=500,
        )
        latest_by_warehouse: dict[str, dict[str, Any]] = {}
        for row in reversed(rows):
            latest_by_warehouse[str(row["warehouse"])] = row
        summary = [
            {
                "company": row["company"],
                "item_code": row["item_code"],
                "warehouse": row["warehouse"],
                "balance_qty": row["qty_after_transaction"],
                "latest_posting_date": row["posting_date"],
                "latest_posting_time": row.get("posting_time"),
            }
            for row in sorted(latest_by_warehouse.values(), key=lambda item: str(item["warehouse"]))
        ]
        return summary, dropped

    def list_warehouses(
        self,
        *,
        company: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        filters: list[list[Any]] = []
        if company:
            filters.append(["company", "=", company])
        rows = self._list_resource(
            doctype="Warehouse",
            fields=self.WAREHOUSE_FIELDS,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="name asc",
        )
        return [dict(row) for row in rows], len(rows)

    def list_customers(self, *, page: int = 1, page_size: int = 20) -> tuple[list[dict[str, Any]], int]:
        rows = self._list_resource(
            doctype="Customer",
            fields=self.CUSTOMER_FIELDS,
            filters=[],
            page=page,
            page_size=page_size,
            order_by="name asc",
        )
        return [dict(row) for row in rows], len(rows)

    def ping(self) -> None:
        """Validate ERPNext availability without returning raw payload."""
        self._request_json("/api/method/frappe.auth.get_logged_user", doctype="User")

    def _list_resource(
        self,
        *,
        doctype: str,
        fields: list[str],
        filters: list[list[Any]],
        page: int,
        page_size: int,
        order_by: str,
    ) -> list[dict[str, Any]]:
        start = max(int(page) - 1, 0) * int(page_size)
        query = {
            "fields": json.dumps(fields, separators=(",", ":")),
            "filters": json.dumps(filters, separators=(",", ":")),
            "limit_start": str(start),
            "limit_page_length": str(page_size),
            "order_by": order_by,
        }
        payload = self._request_json(
            f"/api/resource/{parse.quote(doctype)}?{parse.urlencode(query)}",
            doctype=doctype,
        )
        normalized = normalize_erpnext_response(payload, doctype=doctype, allow_list=True)
        if not isinstance(normalized.data, list):  # defensive; normalize guards this.
            self._raise_invalid(doctype=doctype, resource_name=None, detail="list payload required")
        rows: list[dict[str, Any]] = []
        for row in normalized.data:
            if not isinstance(row, dict):
                self._raise_invalid(doctype=doctype, resource_name=None, detail="list row is not dict")
            rows.append(dict(row))
        return rows

    def _request_json(self, path: str, *, doctype: str | None = None, resource_name: str | None = None) -> dict[str, Any]:
        if not self.base_url:
            raise ERPNextAdapterException(
                error_code=EXTERNAL_SERVICE_UNAVAILABLE,
                doctype=doctype,
                resource_name=resource_name,
                safe_message=message_of(EXTERNAL_SERVICE_UNAVAILABLE),
                retryable=True,
            )
        headers = self._build_headers()
        if not headers:
            raise ERPNextAdapterException(
                error_code=EXTERNAL_SERVICE_UNAVAILABLE,
                doctype=doctype,
                resource_name=resource_name,
                safe_message="ERPNext 只读查询缺少鉴权上下文",
                retryable=True,
            )
        req = urllib_request.Request(url=f"{self.base_url}{path}", method="GET", headers=headers)
        try:
            with urllib_request.urlopen(req, timeout=5) as response:
                body = response.read().decode("utf-8")
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise TypeError(f"payload type={type(payload)!r}")
            return payload
        except (JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            raise map_erpnext_exception(exc, doctype=doctype, resource_name=resource_name) from exc
        except Exception as exc:
            raise map_erpnext_exception(exc, doctype=doctype, resource_name=resource_name) from exc

    def _build_headers(self) -> dict[str, str] | None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.request_obj is not None:
            authorization = self.request_obj.headers.get("Authorization")
            cookie = self.request_obj.headers.get("Cookie")
            if authorization:
                headers["Authorization"] = authorization
            if cookie:
                headers["Cookie"] = cookie
        if "Authorization" not in headers and "Cookie" not in headers:
            return None
        return headers

    @staticmethod
    def _encoded_fields(fields: list[str]) -> str:
        return parse.quote(json.dumps(fields, separators=(",", ":")), safe="")

    @staticmethod
    def _require_sales_order(row: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_erpnext_response(row, doctype="Sales Order", resource_name=str(row.get("name") or ""))
        submitted = require_submitted_doc(normalized)
        return dict(submitted.data)

    @classmethod
    def _normalize_sle_row(cls, row: dict[str, Any]) -> dict[str, Any] | None:
        required = ("company", "item_code", "warehouse", "posting_date", "actual_qty", "qty_after_transaction")
        if any(cls._blank(row.get(field)) for field in required):
            return None
        try:
            actual_qty = Decimal(str(row["actual_qty"]))
            qty_after = Decimal(str(row["qty_after_transaction"]))
            posting_date = cls._coerce_date(row["posting_date"])
        except Exception:
            return None
        return {
            "name": cls._text(row.get("name")),
            "company": str(row["company"]).strip(),
            "item_code": str(row["item_code"]).strip(),
            "warehouse": str(row["warehouse"]).strip(),
            "posting_date": posting_date,
            "posting_time": cls._text(row.get("posting_time")),
            "actual_qty": actual_qty,
            "qty_after_transaction": qty_after,
            "voucher_type": cls._text(row.get("voucher_type")),
            "voucher_no": cls._text(row.get("voucher_no")),
        }

    @staticmethod
    def _coerce_date(value: Any) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value).strip())

    @staticmethod
    def _blank(value: Any) -> bool:
        return value is None or not str(value).strip()

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _raise_invalid(*, doctype: str | None, resource_name: str | None, detail: str) -> None:
        raise ERPNextAdapterException(
            error_code=ERPNEXT_RESPONSE_INVALID,
            doctype=doctype,
            resource_name=resource_name,
            safe_message=message_of(ERPNEXT_RESPONSE_INVALID),
            retryable=False,
            raw_detail=detail,
        )
