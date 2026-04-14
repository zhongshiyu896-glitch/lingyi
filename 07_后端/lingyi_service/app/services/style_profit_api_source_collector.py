"""Server-side source collector for style-profit API (TASK-005F)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation
import json
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import STYLE_PROFIT_BOM_REQUIRED
from app.core.error_codes import STYLE_PROFIT_REVENUE_SOURCE_REQUIRED
from app.core.error_codes import STYLE_PROFIT_SOURCE_UNAVAILABLE
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.schemas.style_profit import StyleProfitSnapshotSelectorRequest
from app.services.erpnext_style_profit_adapter import ERPNextStyleProfitAdapter


class StyleProfitApiSourceCollector:
    """Collect trusted source rows on server side for snapshot creation."""

    _VOLATILE_KEYS = {
        "created_at",
        "updated_at",
        "request_id",
        "operator",
        "snapshot_no",
        "id",
    }
    _SENSITIVE_KEY_PARTS = {
        "authorization",
        "cookie",
        "token",
        "password",
        "secret",
    }

    def __init__(
        self,
        session: Session,
        *,
        request_obj: Any | None = None,
        adapter: ERPNextStyleProfitAdapter | None = None,
    ):
        self.session = session
        self.request_obj = request_obj
        self.adapter = adapter or ERPNextStyleProfitAdapter(session=session, request_obj=request_obj)

    def collect(self, selector: StyleProfitSnapshotSelectorRequest) -> StyleProfitSnapshotCreateRequest:
        """Build service request with trusted server-side source rows only."""
        try:
            sales_invoice_rows = self.adapter.load_submitted_sales_invoice_rows(selector)
            sales_order_rows = self.adapter.load_submitted_sales_order_rows(selector)

            if not sales_invoice_rows and not sales_order_rows:
                raise BusinessException(
                    code=STYLE_PROFIT_REVENUE_SOURCE_REQUIRED,
                    message="未检测到有效收入来源，拒绝创建利润快照",
                )

            planned_qty = self._infer_planned_qty(
                sales_invoice_rows=sales_invoice_rows,
                sales_order_rows=sales_order_rows,
            )
            bom_material_rows, bom_operation_rows, allowed_material_item_codes = self.adapter.load_active_default_bom_rows(
                company=selector.company,
                item_code=selector.item_code,
                planned_qty=planned_qty,
            )
            if not bom_material_rows:
                raise BusinessException(
                    code=STYLE_PROFIT_BOM_REQUIRED,
                    message="缺少 active/default BOM 明细，无法创建利润快照",
                )

            stock_ledger_rows = self.adapter.load_stock_ledger_rows(
                selector,
                allowed_material_item_codes=allowed_material_item_codes,
            )
            purchase_receipt_rows = self.adapter.load_purchase_receipt_rows(
                selector,
                allowed_material_item_codes=allowed_material_item_codes,
            )
            workshop_ticket_rows = self.adapter.load_workshop_ticket_rows(selector)
            subcontract_rows = self.adapter.load_subcontract_rows(selector)

            stock_ledger_rows = self._filter_sle_by_allowed_materials(
                rows=stock_ledger_rows,
                allowed_material_item_codes=allowed_material_item_codes,
            )

            return StyleProfitSnapshotCreateRequest(
                company=selector.company,
                item_code=selector.item_code,
                sales_order=selector.sales_order,
                from_date=selector.from_date,
                to_date=selector.to_date,
                revenue_mode=selector.revenue_mode,
                include_provisional_subcontract=selector.include_provisional_subcontract,
                formula_version=selector.formula_version,
                idempotency_key=selector.idempotency_key,
                sales_invoice_rows=self._normalize_rows(sales_invoice_rows),
                sales_order_rows=self._normalize_rows(sales_order_rows),
                bom_material_rows=self._normalize_rows(bom_material_rows),
                bom_operation_rows=self._normalize_rows(bom_operation_rows),
                stock_ledger_rows=self._normalize_rows(stock_ledger_rows),
                purchase_receipt_rows=self._normalize_rows(purchase_receipt_rows),
                workshop_ticket_rows=self._normalize_rows(workshop_ticket_rows),
                subcontract_rows=self._normalize_rows(subcontract_rows),
                allowed_material_item_codes=sorted(
                    {self._normalize_text(code) for code in allowed_material_item_codes if self._normalize_text(code)}
                ),
                work_order=selector.work_order,
            )
        except (BusinessException, DatabaseReadFailed):
            raise
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed("利润来源读取失败") from exc
        except Exception as exc:
            raise BusinessException(
                code=STYLE_PROFIT_SOURCE_UNAVAILABLE,
                message="利润来源服务暂时不可用",
            ) from exc

    @classmethod
    def _filter_sle_by_allowed_materials(
        cls,
        *,
        rows: list[dict[str, Any]],
        allowed_material_item_codes: list[str],
    ) -> list[dict[str, Any]]:
        allowed = {cls._normalize_text(code) for code in allowed_material_item_codes if cls._normalize_text(code)}
        if not allowed:
            return []
        filtered: list[dict[str, Any]] = []
        for row in rows:
            item_code = cls._normalize_text(row.get("item_code"))
            if item_code in allowed:
                filtered.append(row)
        return filtered

    @classmethod
    def _infer_planned_qty(
        cls,
        *,
        sales_invoice_rows: list[dict[str, Any]],
        sales_order_rows: list[dict[str, Any]],
    ) -> Decimal:
        rows = sales_invoice_rows or sales_order_rows
        total = Decimal("0")
        for row in rows:
            total += cls._to_decimal(row.get("qty"))
        return total if total > Decimal("0") else Decimal("1")

    @classmethod
    def _normalize_rows(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            normalized.append(cls._normalize_row(row))

        normalized.sort(
            key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        return normalized

    @classmethod
    def _normalize_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key in sorted(row.keys()):
            key_text = str(key)
            lowered = key_text.lower().strip()
            if lowered in cls._VOLATILE_KEYS:
                continue
            if any(part in lowered for part in cls._SENSITIVE_KEY_PARTS):
                continue
            result[key_text] = cls._normalize_value(row[key])
        return result

    @classmethod
    def _normalize_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return cls._normalize_row(value)
        if isinstance(value, list):
            return [cls._normalize_value(item) for item in value]
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return cls._decimal_text(value)
        if isinstance(value, (int, float)):
            return cls._decimal_text(value)
        if isinstance(value, str):
            text = value.strip()
            try:
                return cls._decimal_text(Decimal(text))
            except (InvalidOperation, ValueError):
                return text
        return value

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    @classmethod
    def _decimal_text(cls, value: Decimal | int | float) -> str:
        decimal_value = Decimal(str(value))
        normalized = format(decimal_value, "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        if normalized in {"", "-0"}:
            normalized = "0"
        return normalized
