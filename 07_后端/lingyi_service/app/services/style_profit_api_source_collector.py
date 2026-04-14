"""Server-side source collector for style-profit API (TASK-005E1)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import STYLE_PROFIT_SOURCE_UNAVAILABLE
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.schemas.style_profit import StyleProfitSnapshotSelectorRequest


class StyleProfitApiSourceCollector:
    """Collect trusted source rows on server side for snapshot creation.

    TASK-005E1 baseline keeps this collector lightweight and deterministic.
    Revenue/material/workshop/subcontract facts are assembled server-side
    and never read from client payload.
    """

    def __init__(self, session: Session):
        self.session = session

    def collect(self, selector: StyleProfitSnapshotSelectorRequest) -> StyleProfitSnapshotCreateRequest:
        """Build service request with server-side source rows only."""
        try:
            sales_invoice_rows = self._load_sales_invoice_rows(selector=selector)
            sales_order_rows = self._load_sales_order_rows(selector=selector)
            bom_material_rows = self._load_bom_material_rows(selector=selector)
            bom_operation_rows = self._load_bom_operation_rows(selector=selector)
            stock_ledger_rows = self._load_stock_ledger_rows(selector=selector)
            purchase_receipt_rows = self._load_purchase_receipt_rows(selector=selector)
            workshop_ticket_rows = self._load_workshop_ticket_rows(selector=selector)
            subcontract_rows = self._load_subcontract_rows(selector=selector)
            allowed_material_item_codes = self._load_allowed_material_codes(selector=selector)
        except DatabaseReadFailed:
            raise
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed("利润来源读取失败") from exc
        except BusinessException:
            raise
        except Exception as exc:
            raise BusinessException(
                code=STYLE_PROFIT_SOURCE_UNAVAILABLE,
                message="利润来源服务暂时不可用",
            ) from exc

        # TASK-005E2: fail closed when trusted revenue facts are missing.
        if not sales_invoice_rows and not sales_order_rows:
            raise BusinessException(
                code=STYLE_PROFIT_SOURCE_UNAVAILABLE,
                message="未检测到可信收入来源，拒绝创建利润快照",
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
            sales_invoice_rows=sales_invoice_rows,
            sales_order_rows=sales_order_rows,
            bom_material_rows=bom_material_rows,
            bom_operation_rows=bom_operation_rows,
            stock_ledger_rows=stock_ledger_rows,
            purchase_receipt_rows=purchase_receipt_rows,
            workshop_ticket_rows=workshop_ticket_rows,
            subcontract_rows=subcontract_rows,
            allowed_material_item_codes=allowed_material_item_codes,
            work_order=selector.work_order,
        )

    def _load_sales_invoice_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_sales_order_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_bom_material_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_bom_operation_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_stock_ledger_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_purchase_receipt_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_workshop_ticket_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_subcontract_rows(self, selector: StyleProfitSnapshotSelectorRequest) -> list[dict[str, Any]]:
        _ = selector
        return []

    def _load_allowed_material_codes(self, selector: StyleProfitSnapshotSelectorRequest) -> list[str]:
        _ = selector
        return []
