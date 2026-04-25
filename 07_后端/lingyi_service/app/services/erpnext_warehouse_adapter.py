"""Fail-closed ERPNext read adapter for warehouse read-only APIs (TASK-050A)."""

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

from app.core.error_codes import ERPNEXT_STOCK_ENTRY_STATUS_INVALID
from app.core.error_codes import ERPNEXT_RESOURCE_NOT_FOUND
from app.core.exceptions import BusinessException
from app.services.erpnext_stock_entry_service import ERPNextStockEntryService
from app.core.error_codes import ERPNEXT_RESPONSE_INVALID
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import message_of
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_fail_closed_adapter import map_erpnext_exception
from app.services.erpnext_fail_closed_adapter import normalize_erpnext_response


class ERPNextWarehouseAdapter:
    """Read-only warehouse adapter with strict malformed-data fail-closed behavior."""

    STOCK_LEDGER_FIELDS = [
        "company",
        "warehouse",
        "item_code",
        "posting_date",
        "voucher_type",
        "voucher_no",
        "actual_qty",
        "qty_after_transaction",
        "valuation_rate",
    ]

    BIN_FIELDS = [
        "company",
        "warehouse",
        "item_code",
        "actual_qty",
        "projected_qty",
        "reserved_qty",
        "ordered_qty",
        "reorder_level",
        "safety_stock",
    ]

    MOVEMENT_FIELDS = ["item_code", "warehouse", "posting_date"]
    BATCH_FIELDS = [
        "company",
        "warehouse",
        "item_code",
        "item",
        "batch_no",
        "batch_id",
        "name",
        "manufacturing_date",
        "expiry_date",
        "disabled",
        "qty",
        "batch_qty",
    ]
    SERIAL_NO_FIELDS = [
        "company",
        "serial_no",
        "name",
        "item_code",
        "item",
        "warehouse",
        "batch_no",
        "status",
        "delivery_document_no",
        "purchase_document_no",
    ]
    TRACEABILITY_FIELDS = [
        "company",
        "warehouse",
        "item_code",
        "posting_date",
        "voucher_type",
        "voucher_no",
        "actual_qty",
        "qty_after_transaction",
        "batch_no",
        "serial_no",
    ]
    FINISHED_GOODS_INBOUND_OPTION_PATH = "/api/app/product-in-warehouse/manufacture-line-item-option"

    def __init__(
        self,
        request_obj: Request | None = None,
        *,
        stock_entry_service: ERPNextStockEntryService | None = None,
    ):
        self.request_obj = request_obj
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")
        self.stock_entry_service = stock_entry_service or ERPNextStockEntryService()

    def create_stock_entry_draft_from_outbox(
        self,
        *,
        event_key: str,
        payload_json: dict[str, Any],
    ) -> str:
        """Create ERPNext Stock Entry draft only, no submit."""
        existing = self.stock_entry_service.find_by_event_key(event_key=event_key)
        if existing is not None:
            if int(existing.docstatus) == 0:
                return existing.name
            raise BusinessException(
                code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID,
                message="ERPNext Stock Entry 状态非法，禁止继续同步",
            )

        payload = self._build_stock_entry_draft_payload(event_key=event_key, payload_json=payload_json)
        return self.stock_entry_service.create_material_issue(payload_json=payload)

    def list_stock_ledger(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = self._common_filters(company=company, warehouse=warehouse, item_code=item_code)
        if from_date is not None:
            filters.append(["posting_date", ">=", from_date.isoformat()])
        if to_date is not None:
            filters.append(["posting_date", "<=", to_date.isoformat()])

        rows = self._list_resource(
            doctype="Stock Ledger Entry",
            fields=self.STOCK_LEDGER_FIELDS,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="posting_date desc, name desc",
        )
        normalized = [self._normalize_stock_ledger_row(row) for row in rows]
        return normalized, len(normalized)

    def list_stock_summary(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> list[dict[str, Any]]:
        filters = self._common_filters(company=company, warehouse=warehouse, item_code=item_code)
        rows = self._list_resource(
            doctype="Bin",
            fields=self.BIN_FIELDS,
            filters=filters,
            page=1,
            page_size=500,
            order_by="item_code asc, warehouse asc",
        )
        return [self._normalize_bin_row(row) for row in rows]

    def latest_movement_by_item_warehouse(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> dict[tuple[str, str], date]:
        filters = self._common_filters(company=company, warehouse=warehouse, item_code=item_code)
        rows = self._list_resource(
            doctype="Stock Ledger Entry",
            fields=self.MOVEMENT_FIELDS,
            filters=filters,
            page=1,
            page_size=1000,
            order_by="posting_date desc, name desc",
        )
        latest: dict[tuple[str, str], date] = {}
        for row in rows:
            row_item_code = self._require_text(row, "item_code")
            row_warehouse = self._require_text(row, "warehouse")
            posting_date = self._require_date(row, "posting_date")
            key = (row_item_code, row_warehouse)
            if key not in latest or posting_date > latest[key]:
                latest[key] = posting_date
        return latest

    def list_traceability_entries(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        batch_no: str | None,
        serial_no: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = self._common_filters(company=company, warehouse=warehouse, item_code=item_code)
        normalized_batch = self._optional_text(batch_no)
        normalized_serial = self._optional_text(serial_no)
        if normalized_batch:
            filters.append(["batch_no", "=", normalized_batch])
        if normalized_serial:
            filters.append(["serial_no", "like", f"%{normalized_serial}%"])
        if from_date is not None:
            filters.append(["posting_date", ">=", from_date.isoformat()])
        if to_date is not None:
            filters.append(["posting_date", "<=", to_date.isoformat()])

        rows = self._list_resource(
            doctype="Stock Ledger Entry",
            fields=self.TRACEABILITY_FIELDS,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="posting_date desc, name desc",
        )
        normalized = [self._normalize_traceability_row(row) for row in rows]
        if normalized_serial:
            normalized = [
                row
                for row in normalized
                if self._serial_filter_match(row.get("serial_no"), normalized_serial)
            ]
        return normalized, len(normalized)

    def list_finished_goods_inbound_candidates(
        self,
        *,
        company: str | None,
        source_id: str | None = None,
        page_size: int = 200,
    ) -> list[dict[str, Any]]:
        payload = self._build_finished_goods_option_payload(source_id=source_id, page_size=page_size)
        response = self._request_json(
            self.FINISHED_GOODS_INBOUND_OPTION_PATH,
            doctype="Product In Warehouse Option",
            method="POST",
            payload=payload,
        )
        data = response.get("data") if isinstance(response.get("data"), dict) else response
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            self._raise_invalid(doctype="Product In Warehouse Option", detail="items payload required")
        return [self._normalize_finished_goods_candidate_row(row, company=company) for row in items]

    def get_finished_goods_inbound_candidate(
        self,
        *,
        source_id: str,
        company: str | None,
    ) -> dict[str, Any]:
        normalized_source = self._optional_text(source_id)
        if normalized_source is None:
            self._raise_invalid(doctype="Product In Warehouse Option", detail="source_id is required")
        rows = self.list_finished_goods_inbound_candidates(
            company=company,
            source_id=normalized_source,
            page_size=50,
        )
        for row in rows:
            if row.get("source_id") == normalized_source:
                return row
        raise ERPNextAdapterException(
            error_code=ERPNEXT_RESOURCE_NOT_FOUND,
            doctype="Product In Warehouse Option",
            safe_message=message_of(ERPNEXT_RESOURCE_NOT_FOUND),
            retryable=False,
        )

    def list_batches(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        batch_no: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = self._common_filters(company=company, warehouse=warehouse, item_code=item_code)
        rows = self._list_resource(
            doctype="Batch",
            fields=self.BATCH_FIELDS,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="name asc",
        )
        normalized = [self._normalize_batch_row(row) for row in rows]
        normalized_batch = self._optional_text(batch_no)
        if normalized_batch is not None:
            normalized = [row for row in normalized if row["batch_no"] == normalized_batch]
        return normalized, len(normalized)

    def get_batch_detail(
        self,
        *,
        batch_no: str,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> dict[str, Any]:
        normalized_batch = self._optional_text(batch_no)
        if normalized_batch is None:
            self._raise_invalid(doctype="Batch", detail="batch_no is required")
        try:
            raw_row = self._get_resource_doc(doctype="Batch", name=normalized_batch)
        except ERPNextAdapterException as exc:
            if exc.error_code == ERPNEXT_RESOURCE_NOT_FOUND:
                return {
                    "batch_no": normalized_batch,
                    "company": company,
                    "warehouse": warehouse,
                    "item_code": item_code,
                    "total": 0,
                    "items": [],
                }
            raise
        normalized_row = self._normalize_batch_row(raw_row)
        normalized_company = self._optional_text(company)
        normalized_warehouse = self._optional_text(warehouse)
        normalized_item_code = self._optional_text(item_code)
        if normalized_company is not None and normalized_row["company"] != normalized_company:
            items: list[dict[str, Any]] = []
        elif normalized_warehouse is not None and normalized_row["warehouse"] != normalized_warehouse:
            items = []
        elif normalized_item_code is not None and normalized_row["item_code"] != normalized_item_code:
            items = []
        else:
            items = [normalized_row]
        return {
            "batch_no": normalized_batch,
            "company": company,
            "warehouse": warehouse,
            "item_code": item_code,
            "total": len(items),
            "items": items,
        }

    def list_serial_numbers(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        batch_no: str | None,
        serial_no: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        filters = self._common_filters(company=company, warehouse=warehouse, item_code=item_code)
        normalized_batch = self._optional_text(batch_no)
        normalized_serial = self._optional_text(serial_no)
        if normalized_batch is not None:
            filters.append(["batch_no", "=", normalized_batch])
        if normalized_serial is not None:
            filters.append(["name", "like", f"%{normalized_serial}%"])

        rows = self._list_resource(
            doctype="Serial No",
            fields=self.SERIAL_NO_FIELDS,
            filters=filters,
            page=page,
            page_size=page_size,
            order_by="name asc",
        )
        normalized = [self._normalize_serial_number_row(row) for row in rows]
        if normalized_serial is not None:
            normalized = [row for row in normalized if row["serial_no"] == normalized_serial]
        return normalized, len(normalized)

    def get_serial_number_detail(
        self,
        *,
        serial_no: str,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> dict[str, Any]:
        normalized_serial = self._optional_text(serial_no)
        if normalized_serial is None:
            self._raise_invalid(doctype="Serial No", detail="serial_no is required")
        try:
            raw_row = self._get_resource_doc(doctype="Serial No", name=normalized_serial)
        except ERPNextAdapterException as exc:
            if exc.error_code == ERPNEXT_RESOURCE_NOT_FOUND:
                return {
                    "serial_no": normalized_serial,
                    "company": company,
                    "warehouse": warehouse,
                    "item_code": item_code,
                    "total": 0,
                    "items": [],
                }
            raise
        normalized_row = self._normalize_serial_number_row(raw_row)
        normalized_company = self._optional_text(company)
        normalized_warehouse = self._optional_text(warehouse)
        normalized_item_code = self._optional_text(item_code)
        if normalized_company is not None and normalized_row["company"] != normalized_company:
            items: list[dict[str, Any]] = []
        elif normalized_warehouse is not None and normalized_row["warehouse"] != normalized_warehouse:
            items = []
        elif normalized_item_code is not None and normalized_row["item_code"] != normalized_item_code:
            items = []
        else:
            items = [normalized_row]
        return {
            "serial_no": normalized_serial,
            "company": company,
            "warehouse": warehouse,
            "item_code": item_code,
            "total": len(items),
            "items": items,
        }

    def _common_filters(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> list[list[Any]]:
        filters: list[list[Any]] = []
        if company:
            filters.append(["company", "=", company])
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        if item_code:
            filters.append(["item_code", "=", item_code])
        return filters

    def _build_stock_entry_draft_payload(
        self,
        *,
        event_key: str,
        payload_json: dict[str, Any],
    ) -> dict[str, Any]:
        company = self._optional_text(payload_json.get("company")) or ""
        purpose = self._optional_text(payload_json.get("purpose")) or "Material Transfer"
        source_warehouse = self._optional_text(payload_json.get("source_warehouse"))
        target_warehouse = self._optional_text(payload_json.get("target_warehouse"))
        source_type = self._optional_text(payload_json.get("source_type")) or "manual"
        source_id = self._optional_text(payload_json.get("source_id")) or "-"
        allowed_purpose = {"Material Issue", "Material Receipt", "Material Transfer"}
        if purpose not in allowed_purpose:
            raise BusinessException(code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID, message="purpose 非法，禁止同步")

        item_rows: list[dict[str, Any]] = []
        raw_items = payload_json.get("items")
        if isinstance(raw_items, list):
            for raw in raw_items:
                if not isinstance(raw, dict):
                    continue
                item_code = self._optional_text(raw.get("item_code"))
                qty = self._optional_text(raw.get("qty"))
                if not item_code or not qty:
                    continue
                row_source_wh = self._optional_text(raw.get("source_warehouse")) or source_warehouse
                row_target_wh = self._optional_text(raw.get("target_warehouse")) or target_warehouse
                item_rows.append(
                    {
                        "item_code": item_code,
                        "qty": float(Decimal(qty)),
                        "uom": self._optional_text(raw.get("uom")),
                        "batch_no": self._optional_text(raw.get("batch_no")),
                        "serial_no": self._optional_text(raw.get("serial_no")),
                        "s_warehouse": row_source_wh,
                        "t_warehouse": row_target_wh,
                    }
                )
        if not company or not item_rows:
            raise BusinessException(code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID, message="缺少 company/items，禁止同步")

        return {
            "doctype": "Stock Entry",
            "stock_entry_type": purpose,
            "purpose": purpose,
            "company": company,
            "custom_ly_outbox_event_key": str(event_key),
            "remarks": f"Warehouse stock-entry outbox sync source={source_type}:{source_id}",
            "items": item_rows,
        }

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
        if not isinstance(normalized.data, list):
            self._raise_invalid(doctype=doctype, detail="list payload required")
        rows: list[dict[str, Any]] = []
        for row in normalized.data:
            if not isinstance(row, dict):
                self._raise_invalid(doctype=doctype, detail="list row is not dict")
            rows.append(dict(row))
        return rows

    def _get_resource_doc(self, *, doctype: str, name: str) -> dict[str, Any]:
        path = f"/api/resource/{parse.quote(doctype)}/{parse.quote(name)}"
        payload = self._request_json(path, doctype=doctype)
        normalized = normalize_erpnext_response(
            payload,
            doctype=doctype,
            resource_name=name,
            allow_list=False,
        )
        if not isinstance(normalized.data, dict):
            self._raise_invalid(doctype=doctype, detail="single document payload required")
        return dict(normalized.data)

    def _request_json(
        self,
        path: str,
        *,
        doctype: str | None = None,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.base_url:
            raise ERPNextAdapterException(
                error_code=EXTERNAL_SERVICE_UNAVAILABLE,
                doctype=doctype,
                safe_message=message_of(EXTERNAL_SERVICE_UNAVAILABLE),
                retryable=True,
            )
        headers = self._build_headers()
        if not headers:
            raise ERPNextAdapterException(
                error_code=EXTERNAL_SERVICE_UNAVAILABLE,
                doctype=doctype,
                safe_message="ERPNext 只读查询缺少鉴权上下文",
                retryable=True,
            )
        request_body: bytes | None = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            request_body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        req = urllib_request.Request(
            url=f"{self.base_url}{path}",
            method=method.upper(),
            headers=headers,
            data=request_body,
        )
        try:
            with urllib_request.urlopen(req, timeout=5) as response:
                body = response.read().decode("utf-8")
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise TypeError(f"payload type={type(payload)!r}")
            return payload
        except (JSONDecodeError, TypeError, ValueError, KeyError) as exc:
            raise map_erpnext_exception(exc, doctype=doctype) from exc
        except Exception as exc:  # pragma: no cover - mapped uniformly.
            raise map_erpnext_exception(exc, doctype=doctype) from exc

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

    def _normalize_stock_ledger_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "company": self._require_text(row, "company"),
            "warehouse": self._require_text(row, "warehouse"),
            "item_code": self._require_text(row, "item_code"),
            "posting_date": self._require_date(row, "posting_date"),
            "voucher_type": self._optional_text(row.get("voucher_type")),
            "voucher_no": self._optional_text(row.get("voucher_no")),
            "actual_qty": self._require_decimal(row, "actual_qty"),
            "qty_after_transaction": self._require_decimal(row, "qty_after_transaction"),
            "valuation_rate": self._require_decimal(row, "valuation_rate"),
        }

    def _normalize_bin_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "company": self._require_text(row, "company"),
            "warehouse": self._require_text(row, "warehouse"),
            "item_code": self._require_text(row, "item_code"),
            "actual_qty": self._require_decimal(row, "actual_qty"),
            "projected_qty": self._require_decimal(row, "projected_qty"),
            "reserved_qty": self._require_decimal(row, "reserved_qty"),
            "ordered_qty": self._require_decimal(row, "ordered_qty"),
            "reorder_level": self._optional_decimal(row.get("reorder_level")),
            "safety_stock": self._optional_decimal(row.get("safety_stock")),
        }

    def _normalize_traceability_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "company": self._require_text(row, "company"),
            "warehouse": self._require_text(row, "warehouse"),
            "item_code": self._require_text(row, "item_code"),
            "posting_date": self._require_date(row, "posting_date"),
            "voucher_type": self._optional_text(row.get("voucher_type")),
            "voucher_no": self._optional_text(row.get("voucher_no")),
            "actual_qty": self._require_decimal(row, "actual_qty"),
            "qty_after_transaction": self._require_decimal(row, "qty_after_transaction"),
            "batch_no": self._optional_text(row.get("batch_no")),
            "serial_no": self._optional_text(row.get("serial_no")),
        }

    def _normalize_batch_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "company": self._required_text_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("company",),
                logical_field="company",
            ),
            "batch_no": self._required_text_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("batch_no", "batch_id", "name"),
                logical_field="batch_no",
            ),
            "item_code": self._required_text_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("item_code", "item"),
                logical_field="item_code",
            ),
            "warehouse": self._required_text_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("warehouse",),
                logical_field="warehouse",
            ),
            "manufacturing_date": self._optional_date_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("manufacturing_date",),
                logical_field="manufacturing_date",
            ),
            "expiry_date": self._optional_date_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("expiry_date",),
                logical_field="expiry_date",
            ),
            "disabled": self._required_bool_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("disabled",),
                logical_field="disabled",
            ),
            "qty": self._required_decimal_from_candidates(
                row=row,
                doctype="Batch",
                candidates=("qty", "batch_qty"),
                logical_field="qty",
            ),
        }

    def _normalize_serial_number_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "company": self._required_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("company",),
                logical_field="company",
            ),
            "serial_no": self._required_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("serial_no", "name"),
                logical_field="serial_no",
            ),
            "item_code": self._required_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("item_code", "item"),
                logical_field="item_code",
            ),
            "warehouse": self._required_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("warehouse",),
                logical_field="warehouse",
            ),
            "batch_no": self._optional_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("batch_no",),
                logical_field="batch_no",
            ),
            "status": self._required_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("status",),
                logical_field="status",
            ),
            "delivery_document_no": self._optional_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("delivery_document_no",),
                logical_field="delivery_document_no",
            ),
            "purchase_document_no": self._optional_text_from_candidates(
                row=row,
                doctype="Serial No",
                candidates=("purchase_document_no",),
                logical_field="purchase_document_no",
            ),
        }

    def _require_text(self, row: dict[str, Any], field: str, *, doctype: str = "Warehouse") -> str:
        value = row.get(field)
        text = self._optional_text(value)
        if text is None:
            self._raise_invalid(doctype=doctype, detail=f"missing field: {field}")
        return text

    def _require_decimal(self, row: dict[str, Any], field: str, *, doctype: str = "Warehouse") -> Decimal:
        value = row.get(field)
        try:
            return Decimal(str(value))
        except Exception:
            self._raise_invalid(doctype=doctype, detail=f"invalid decimal field: {field}")

    def _require_date(self, row: dict[str, Any], field: str, *, doctype: str = "Warehouse") -> date:
        value = row.get(field)
        if value is None:
            self._raise_invalid(doctype=doctype, detail=f"missing date field: {field}")
        text = str(value).strip()
        if not text:
            self._raise_invalid(doctype=doctype, detail=f"empty date field: {field}")
        if "T" in text:
            text = text.split("T", 1)[0]
        if " " in text:
            text = text.split(" ", 1)[0]
        try:
            return date.fromisoformat(text)
        except ValueError:
            self._raise_invalid(doctype=doctype, detail=f"invalid date field: {field}")

    def _required_text_from_candidates(
        self,
        *,
        row: dict[str, Any],
        doctype: str,
        candidates: tuple[str, ...],
        logical_field: str,
    ) -> str:
        value = self._value_from_candidates(
            row=row,
            doctype=doctype,
            candidates=candidates,
            logical_field=logical_field,
        )
        text = self._optional_text(value)
        if text is None:
            self._raise_invalid(doctype=doctype, detail=f"missing field: {logical_field}")
        return text

    def _optional_text_from_candidates(
        self,
        *,
        row: dict[str, Any],
        doctype: str,
        candidates: tuple[str, ...],
        logical_field: str,
    ) -> str | None:
        value = self._value_from_candidates(
            row=row,
            doctype=doctype,
            candidates=candidates,
            logical_field=logical_field,
        )
        return self._optional_text(value)

    def _required_decimal_from_candidates(
        self,
        *,
        row: dict[str, Any],
        doctype: str,
        candidates: tuple[str, ...],
        logical_field: str,
    ) -> Decimal:
        value = self._value_from_candidates(
            row=row,
            doctype=doctype,
            candidates=candidates,
            logical_field=logical_field,
        )
        try:
            return Decimal(str(value))
        except Exception:
            self._raise_invalid(doctype=doctype, detail=f"invalid decimal field: {logical_field}")

    def _optional_date_from_candidates(
        self,
        *,
        row: dict[str, Any],
        doctype: str,
        candidates: tuple[str, ...],
        logical_field: str,
    ) -> date | None:
        value = self._value_from_candidates(
            row=row,
            doctype=doctype,
            candidates=candidates,
            logical_field=logical_field,
        )
        text = self._optional_text(value)
        if text is None:
            return None
        if "T" in text:
            text = text.split("T", 1)[0]
        if " " in text:
            text = text.split(" ", 1)[0]
        try:
            return date.fromisoformat(text)
        except ValueError:
            self._raise_invalid(doctype=doctype, detail=f"invalid date field: {logical_field}")

    def _required_bool_from_candidates(
        self,
        *,
        row: dict[str, Any],
        doctype: str,
        candidates: tuple[str, ...],
        logical_field: str,
    ) -> bool:
        value = self._value_from_candidates(
            row=row,
            doctype=doctype,
            candidates=candidates,
            logical_field=logical_field,
        )
        if isinstance(value, bool):
            return value
        text = self._optional_text(value)
        if text is None:
            self._raise_invalid(doctype=doctype, detail=f"missing field: {logical_field}")
        lowered = text.lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no"}:
            return False
        self._raise_invalid(doctype=doctype, detail=f"invalid bool field: {logical_field}")

    def _value_from_candidates(
        self,
        *,
        row: dict[str, Any],
        doctype: str,
        candidates: tuple[str, ...],
        logical_field: str,
    ) -> Any:
        for field_name in candidates:
            if field_name in row:
                return row[field_name]
        self._raise_invalid(doctype=doctype, detail=f"missing field: {logical_field}")

    @staticmethod
    def _build_finished_goods_option_payload(*, source_id: str | None, page_size: int) -> dict[str, Any]:
        source_ids: list[str] = []
        if source_id is not None:
            text = ERPNextWarehouseAdapter._optional_text(source_id)
            if text is not None:
                source_ids = [text]
        return {
            "manufactureLineItemIds": source_ids,
            "factoryId": "",
            "documentNo": "",
            "product": "",
            "categoryId": "",
            "seasonId": "",
            "barcode": "",
            "expectedReturnStartDate": "",
            "expectedReturnEndDate": "",
            "showCompleted": True,
            "approvalStatus": 2,
            "pageNumber": 1,
            "pageSize": max(1, min(int(page_size), 200)),
        }

    def _normalize_finished_goods_candidate_row(
        self,
        row: dict[str, Any],
        *,
        company: str | None,
    ) -> dict[str, Any]:
        source_id = self._required_text_from_candidates(
            row=row,
            doctype="Product In Warehouse Option",
            candidates=("manufactureLineItemId", "id"),
            logical_field="source_id",
        )
        item_code = self._required_text_from_candidates(
            row=row,
            doctype="Product In Warehouse Option",
            candidates=("productNo", "productId", "item_code"),
            logical_field="item_code",
        )
        qty = self._required_decimal_from_candidates(
            row=row,
            doctype="Product In Warehouse Option",
            candidates=("quantity",),
            logical_field="qty",
        )
        uom = self._optional_text_from_candidates(
            row=row,
            doctype="Product In Warehouse Option",
            candidates=("productUnit",),
            logical_field="uom",
        ) or "Nos"
        strict_alloc_qty = self._optional_decimal_from_candidates(
            row=row,
            doctype="Product In Warehouse Option",
            candidates=("surplusQuantity",),
            logical_field="strict_alloc_qty",
        ) or Decimal("0")
        manufacture_no = self._optional_text_from_candidates(
            row=row,
            doctype="Product In Warehouse Option",
            candidates=("manufactureNo",),
            logical_field="manufacture_no",
        )
        process_type = self._optional_text_from_candidates(
            row=row,
            doctype="Product In Warehouse Option",
            candidates=("processType", "productionProcessTypeName"),
            logical_field="process_type",
        )
        source_label_parts = [part for part in [manufacture_no, process_type, item_code] if part]
        source_label = " / ".join(source_label_parts) if source_label_parts else source_id

        disabled = qty <= Decimal("0")
        disabled_reason = "候选数量不足，禁止创建草稿" if disabled else None
        return {
            "company": self._optional_text(company),
            "source_id": source_id,
            "source_label": source_label,
            "item_code": item_code,
            "qty": qty,
            "uom": uom,
            "strict_alloc_qty": strict_alloc_qty,
            "disabled": disabled,
            "disabled_reason": disabled_reason,
        }

    def _optional_decimal_from_candidates(
        self,
        *,
        row: dict[str, Any],
        doctype: str,
        candidates: tuple[str, ...],
        logical_field: str,
    ) -> Decimal | None:
        for field_name in candidates:
            if field_name in row:
                return self._optional_decimal(row.get(field_name))
        return None

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_decimal(value: Any) -> Decimal | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return Decimal(text)
        except Exception:
            return None

    @staticmethod
    def _split_serial_numbers(value: Any) -> list[str]:
        text = ERPNextWarehouseAdapter._optional_text(value)
        if text is None:
            return []
        normalized = text.replace("\n", ",").replace(";", ",")
        values = [part.strip() for part in normalized.split(",")]
        return [value for value in values if value]

    @staticmethod
    def _serial_filter_match(value: Any, expected_serial: str) -> bool:
        serials = ERPNextWarehouseAdapter._split_serial_numbers(value)
        return expected_serial in serials

    def _raise_invalid(self, *, doctype: str | None, detail: str) -> None:
        raise ERPNextAdapterException(
            error_code=ERPNEXT_RESPONSE_INVALID,
            doctype=doctype,
            safe_message=message_of(ERPNEXT_RESPONSE_INVALID),
            retryable=False,
            raw_detail=detail,
        )
