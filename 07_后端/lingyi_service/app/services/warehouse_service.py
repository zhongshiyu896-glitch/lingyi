"""Warehouse stock read and draft-outbox baseline service (TASK-050B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import hashlib
import json
import os
from typing import Any
from typing import Literal

from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import INTERNAL_ERROR
from app.core.error_codes import DATABASE_READ_FAILED
from app.core.exceptions import AppException
from app.core.exceptions import BusinessException
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseInventoryCount
from app.models.warehouse import LyWarehouseInventoryCountItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStockOutbox
from app.schemas.warehouse import WarehouseAlertItem
from app.schemas.warehouse import WarehouseAlertsData
from app.schemas.warehouse import WarehouseBatchDetailData
from app.schemas.warehouse import WarehouseBatchItem
from app.schemas.warehouse import WarehouseBatchListData
from app.schemas.warehouse import WarehouseFactoryReturnMaterialReportData
from app.schemas.warehouse import WarehouseFactoryReturnMaterialReportItem
from app.schemas.warehouse import WarehouseFinishedGoodsInboundCandidateItem
from app.schemas.warehouse import WarehouseFinishedGoodsInboundCandidatesData
from app.schemas.warehouse import WarehouseInventoryCountCreateRequest
from app.schemas.warehouse import WarehouseInventoryCountData
from app.schemas.warehouse import WarehouseInventoryCountItemCreateRequest
from app.schemas.warehouse import WarehouseInventoryCountItemData
from app.schemas.warehouse import WarehouseInventoryCountListData
from app.schemas.warehouse import WarehouseInventoryCountVarianceReviewRequest
from app.schemas.warehouse import WarehouseInventoryCountVarianceStatsData
from app.schemas.warehouse import WarehouseInventoryBalanceReconciliationItem
from app.schemas.warehouse import WarehouseInventoryBalanceReconciliationListData
from app.schemas.warehouse import WarehouseMaterialRetentionReportData
from app.schemas.warehouse import WarehouseMaterialRetentionReportItem
from app.schemas.warehouse import WarehouseStockEntryDraftCreateRequest
from app.schemas.warehouse import WarehouseStockEntryDraftData
from app.schemas.warehouse import WarehouseStockEntryDraftItemCreateRequest
from app.schemas.warehouse import WarehouseStockEntryDraftItemData
from app.schemas.warehouse import WarehouseStockEntryDraftListData
from app.schemas.warehouse import WarehouseStockEntryOutboxStatusData
from app.schemas.warehouse import WarehouseStockEntryWorkerRunOnceData
from app.schemas.warehouse import WarehouseFinishedGoodsInboundItem
from app.schemas.warehouse import WarehouseFinishedGoodsInboundListData
from app.schemas.warehouse import WarehouseStockLedgerData
from app.schemas.warehouse import WarehouseStockLedgerItem
from app.schemas.warehouse import WarehouseManagementItem
from app.schemas.warehouse import WarehouseMaterialInventoryItem
from app.schemas.warehouse import WarehouseOtherInboundData
from app.schemas.warehouse import WarehouseOtherInboundItem
from app.schemas.warehouse import WarehousePurchaseReceiptItem
from app.schemas.warehouse import WarehousePurchaseReceiptListData
from app.schemas.warehouse import WarehousePurchaseReturnOutboundData
from app.schemas.warehouse import WarehousePurchaseReturnOutboundItem
from app.schemas.warehouse import WarehouseSemiFinishedOutboundData
from app.schemas.warehouse import WarehouseSemiFinishedOutboundItem
from app.schemas.warehouse import WarehouseSerialNumberDetailData
from app.schemas.warehouse import WarehouseSerialNumberItem
from app.schemas.warehouse import WarehouseSerialNumberListData
from app.schemas.warehouse import WarehouseStockSummaryData
from app.schemas.warehouse import WarehouseStockSummaryItem
from app.schemas.warehouse import WarehouseTraceabilityData
from app.schemas.warehouse import WarehouseTraceabilityItem
from app.services.erpnext_warehouse_adapter import ERPNextWarehouseAdapter
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.material_purchase_service import MaterialPurchaseService


@dataclass(slots=True)
class WarehouseServiceError(Exception):
    """Domain error for warehouse service."""

    status_code: int
    code: str
    message: str


@dataclass(slots=True, frozen=True)
class WarehouseStockEntryOutboxClaim:
    """Warehouse stock-entry outbox claimed row snapshot."""

    outbox_id: int
    draft_id: int
    event_key: str
    payload: dict[str, Any]


@dataclass(slots=True, frozen=True)
class WarehouseStockMovement:
    """Normalized local stock movement from all FastAPI-native inventory facts."""

    company: str
    warehouse: str
    item_code: str
    posting_date: date
    sort_at: datetime
    source_id: int
    line_id: int
    sequence: int
    voucher_type: str
    voucher_no: str
    actual_qty: Decimal
    valuation_rate: Decimal


class WarehouseService:
    """Warehouse read-only and draft/outbox write service."""

    _PURPOSES = {"Material Issue", "Material Receipt", "Material Transfer"}
    _INVENTORY_ACTIVE_STATUSES = {"draft", "counted", "variance_review"}
    _FINISHED_GOODS_SOURCE_TYPE = "finished_goods_inbound"
    _FINISHED_GOODS_DISABLED_ENTRY_LABEL = "成品预约入仓 -> 创建成品入仓"
    _FINISHED_GOODS_DISABLED_ENTRY_REASON = "当前入口存在受限状态，需按冻结口径提示，不得直接放开"
    _ALLOCATION_CONTRACT = "strict_alloc -> zero_placeholder_fallback"
    _STRICT_ALLOC_FAILURE_REASON = "找不到可分配的制单明细"

    def __init__(
        self,
        *,
        adapter: ERPNextWarehouseAdapter | None = None,
        session: Session | None = None,
    ):
        self.adapter = adapter
        self.session = session

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
    ) -> WarehouseStockLedgerData:
        if self.adapter is None and self._local_read_fallback_enabled():
            return self.list_local_stock_ledger(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                from_date=from_date,
                to_date=to_date,
                page=page,
                page_size=page_size,
            )
        try:
            rows, total = self._require_adapter().list_stock_ledger(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                from_date=from_date,
                to_date=to_date,
                page=page,
                page_size=page_size,
            )
        except ERPNextAdapterException:
            if not self._local_read_fallback_enabled():
                raise
            return self.list_local_stock_ledger(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                from_date=from_date,
                to_date=to_date,
                page=page,
                page_size=page_size,
            )
        else:
            return WarehouseStockLedgerData(
                items=[WarehouseStockLedgerItem(**row) for row in rows],
                total=total,
                page=page,
                page_size=page_size,
            )

    def get_stock_summary(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> WarehouseStockSummaryData:
        if self.adapter is None and self._local_read_fallback_enabled():
            return self.get_local_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        try:
            rows = self._require_adapter().list_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        except ERPNextAdapterException:
            if not self._local_read_fallback_enabled():
                raise
            return self.get_local_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        items = [self._summary_item(row) for row in rows]
        items.sort(key=lambda row: (row.company, row.warehouse, row.item_code))
        management_rows = self._build_management_overview(items=items)
        material_rows = self._build_material_inventory(items=items)
        return WarehouseStockSummaryData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            items=items,
            warehouse_management=management_rows,
            material_inventory=material_rows,
        )

    def list_local_stock_ledger(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> WarehouseStockLedgerData:
        movements = self._local_stock_movements(company=company, warehouse=warehouse, item_code=item_code)
        running_qty: dict[tuple[str, str, str], Decimal] = {}
        ledger_rows: list[WarehouseStockLedgerItem] = []
        for movement in movements:
            key = (movement.company, movement.warehouse, movement.item_code)
            next_balance = running_qty.get(key, Decimal("0")) + movement.actual_qty
            running_qty[key] = next_balance
            if from_date is not None and movement.posting_date < from_date:
                continue
            if to_date is not None and movement.posting_date > to_date:
                continue
            ledger_rows.append(
                WarehouseStockLedgerItem(
                    company=movement.company,
                    warehouse=movement.warehouse,
                    item_code=movement.item_code,
                    posting_date=movement.posting_date,
                    voucher_type=movement.voucher_type,
                    voucher_no=movement.voucher_no,
                    actual_qty=movement.actual_qty,
                    qty_after_transaction=next_balance,
                    valuation_rate=movement.valuation_rate,
                )
            )

        total = len(ledger_rows)
        start = max(page - 1, 0) * page_size
        return WarehouseStockLedgerData(
            items=ledger_rows[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_local_stock_summary(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> WarehouseStockSummaryData:
        return self._local_stock_summary(company=company, warehouse=warehouse, item_code=item_code)

    def list_local_purchase_receipts(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        material_item_code: str | None,
        supplier_name: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> WarehousePurchaseReceiptListData:
        session = self._require_session()
        normalized_company = self._text(company)
        normalized_warehouse = self._text(warehouse)
        normalized_item_code = self._text(item_code)
        normalized_material_item_code = self._text(material_item_code)
        normalized_supplier_name = self._text(supplier_name)
        normalized_status = self._text(status)
        try:
            query = (
                session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
                .join(
                    LyWarehouseStockEntryDraftItem,
                    LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id,
                )
                .filter(
                    LyWarehouseStockEntryDraft.status != "cancelled",
                    LyWarehouseStockEntryDraft.purpose == "Material Receipt",
                    LyWarehouseStockEntryDraft.source_type == MaterialPurchaseService.PURCHASE_SOURCE_TYPE,
                )
            )
            if normalized_company:
                query = query.filter(LyWarehouseStockEntryDraft.company == normalized_company)
            if normalized_warehouse:
                query = query.filter(
                    (LyWarehouseStockEntryDraft.target_warehouse == normalized_warehouse)
                    | (LyWarehouseStockEntryDraftItem.target_warehouse == normalized_warehouse)
                )
            if normalized_item_code:
                query = query.filter(LyWarehouseStockEntryDraftItem.item_code == normalized_item_code)

            rows = (
                query.order_by(
                    LyWarehouseStockEntryDraft.created_at.desc(),
                    LyWarehouseStockEntryDraft.id.desc(),
                    LyWarehouseStockEntryDraftItem.id.asc(),
                )
                .all()
            )
            purchase_nos = {self._purchase_no_from_source_id(str(draft.source_id)) for draft, _ in rows}
            purchase_nos.discard(None)
            orders = self._material_purchase_order_map(company=normalized_company, purchase_nos=purchase_nos)
            order_lines = self._material_purchase_line_map(company=normalized_company, purchase_nos=purchase_nos)
        except SQLAlchemyError as exc:
            raise WarehouseServiceError(500, DATABASE_READ_FAILED, "采购入库读回失败") from exc

        items: list[WarehousePurchaseReceiptItem] = []
        for draft, line in rows:
            purchase_no = self._purchase_no_from_source_id(str(draft.source_id)) or str(draft.source_id)
            order = orders.get((str(draft.company), purchase_no))
            order_line = order_lines.get((str(draft.company), purchase_no, str(line.item_code)))
            row_material_item_code = str(order_line.material_item_code) if order_line is not None else str(line.item_code)
            row_supplier_name = str(order.supplier_name) if order is not None else ""
            row_status = self._local_stock_entry_readback_status(draft=draft)
            if normalized_material_item_code and row_material_item_code != normalized_material_item_code:
                continue
            if normalized_supplier_name and row_supplier_name != normalized_supplier_name:
                continue
            if normalized_status and row_status != normalized_status:
                continue
            row_warehouse = self._text(line.target_warehouse) or self._text(draft.target_warehouse) or ""
            items.append(
                WarehousePurchaseReceiptItem(
                    receipt_no=self._local_stock_receipt_no(draft=draft),
                    purchase_no=purchase_no,
                    company=str(draft.company),
                    supplier_name=row_supplier_name,
                    item_code=str(line.item_code),
                    material_item_code=row_material_item_code,
                    warehouse=row_warehouse,
                    received_qty=Decimal(str(line.qty)),
                    accepted_qty=Decimal(str(line.qty)),
                    posting_date=self._local_draft_posting_date(draft=draft),
                    status=row_status,
                )
            )

        return self._paginate_purchase_receipts(items=items, page=page, page_size=page_size)

    def list_local_finished_goods_inbound(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        reserve_status: str | None,
        inbound_status: str | None,
        page: int,
        page_size: int,
    ) -> WarehouseFinishedGoodsInboundListData:
        session = self._require_session()
        normalized_company = self._text(company)
        normalized_warehouse = self._text(warehouse)
        normalized_item_code = self._text(item_code)
        normalized_reserve_status = self._text(reserve_status)
        normalized_inbound_status = self._text(inbound_status)
        try:
            query = (
                session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
                .join(
                    LyWarehouseStockEntryDraftItem,
                    LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id,
                )
                .filter(
                    LyWarehouseStockEntryDraft.status != "cancelled",
                    LyWarehouseStockEntryDraft.source_type == self._FINISHED_GOODS_SOURCE_TYPE,
                    LyWarehouseStockEntryDraft.purpose == "Material Receipt",
                )
            )
            if normalized_company:
                query = query.filter(LyWarehouseStockEntryDraft.company == normalized_company)
            if normalized_warehouse:
                query = query.filter(
                    (LyWarehouseStockEntryDraft.target_warehouse == normalized_warehouse)
                    | (LyWarehouseStockEntryDraftItem.target_warehouse == normalized_warehouse)
                )
            if normalized_item_code:
                query = query.filter(LyWarehouseStockEntryDraftItem.item_code == normalized_item_code)
            rows = (
                query.order_by(
                    LyWarehouseStockEntryDraft.created_at.desc(),
                    LyWarehouseStockEntryDraft.id.desc(),
                    LyWarehouseStockEntryDraftItem.id.asc(),
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise WarehouseServiceError(500, DATABASE_READ_FAILED, "成品入库读回失败") from exc

        items: list[WarehouseFinishedGoodsInboundItem] = []
        for draft, line in rows:
            row_reserve_status = "reserved"
            row_inbound_status = self._local_finished_goods_inbound_status(draft=draft)
            if normalized_reserve_status and row_reserve_status != normalized_reserve_status:
                continue
            if normalized_inbound_status and row_inbound_status != normalized_inbound_status:
                continue
            posting_date = self._local_draft_posting_date(draft=draft)
            qty = Decimal(str(line.qty))
            items.append(
                WarehouseFinishedGoodsInboundItem(
                    reservation_no=str(draft.source_id),
                    item_code=str(line.item_code),
                    item_name=str(line.item_code),
                    warehouse=self._text(line.target_warehouse) or self._text(draft.target_warehouse) or "",
                    reserve_qty=qty,
                    inbound_qty=qty,
                    pending_inbound_qty=Decimal("0"),
                    reserve_status=row_reserve_status,
                    inbound_status=row_inbound_status,
                    reserved_date=posting_date,
                    expected_inbound_date=posting_date,
                    owner=str(draft.created_by),
                    ref_no=str(draft.source_id),
                    company=str(draft.company),
                )
            )

        return self._paginate_finished_goods_inbound(items=items, page=page, page_size=page_size)

    def list_local_inventory_balance_reconciliation(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> WarehouseInventoryBalanceReconciliationListData:
        session = self._require_session()
        normalized_company = self._text(company)
        normalized_warehouse = self._text(warehouse)
        normalized_item_code = self._text(item_code)
        normalized_status = self._text(status)
        try:
            query = (
                session.query(LyWarehouseInventoryCount, LyWarehouseInventoryCountItem)
                .join(
                    LyWarehouseInventoryCountItem,
                    LyWarehouseInventoryCountItem.count_id == LyWarehouseInventoryCount.id,
                )
                .filter(LyWarehouseInventoryCount.status != "cancelled")
            )
            if normalized_company:
                query = query.filter(LyWarehouseInventoryCount.company == normalized_company)
            if normalized_warehouse:
                query = query.filter(LyWarehouseInventoryCount.warehouse == normalized_warehouse)
            if normalized_item_code:
                query = query.filter(LyWarehouseInventoryCountItem.item_code == normalized_item_code)
            rows = (
                query.order_by(
                    LyWarehouseInventoryCount.count_date.desc(),
                    LyWarehouseInventoryCount.id.desc(),
                    LyWarehouseInventoryCountItem.id.asc(),
                )
                .all()
            )
            balance_map = self._local_stock_balance_map(company=company, warehouse=warehouse, item_code=item_code)
        except SQLAlchemyError as exc:
            raise WarehouseServiceError(500, DATABASE_READ_FAILED, "库存账实差异读回失败") from exc

        items: list[WarehouseInventoryBalanceReconciliationItem] = []
        for count, line in rows:
            key = (str(count.company), str(count.warehouse), str(line.item_code))
            book_qty = balance_map.get(key, Decimal("0"))
            actual_qty = Decimal(str(line.counted_qty))
            diff_qty = actual_qty - book_qty
            row_status = self._inventory_reconciliation_status(count=count, line=line, diff_qty=diff_qty)
            if normalized_status and row_status != normalized_status:
                continue
            items.append(
                WarehouseInventoryBalanceReconciliationItem(
                    company=str(count.company),
                    warehouse=str(count.warehouse),
                    item_code=str(line.item_code),
                    book_qty=book_qty,
                    actual_qty=actual_qty,
                    diff_qty=diff_qty,
                    status=row_status,
                    biz_date=count.count_date,
                    owner=self._text(count.reviewed_by) or self._text(count.submitted_by) or str(count.created_by),
                    ref_no=str(count.count_no),
                )
            )

        return self._paginate_inventory_reconciliation(items=items, page=page, page_size=page_size)

    def _material_purchase_order_map(
        self,
        *,
        company: str | None,
        purchase_nos: set[str],
    ) -> dict[tuple[str, str], LyMaterialPurchaseOrder]:
        if not purchase_nos:
            return {}
        query = self._require_session().query(LyMaterialPurchaseOrder).filter(LyMaterialPurchaseOrder.purchase_no.in_(sorted(purchase_nos)))
        if company:
            query = query.filter(LyMaterialPurchaseOrder.company == company)
        return {(str(row.company), str(row.purchase_no)): row for row in query.all()}

    def _material_purchase_line_map(
        self,
        *,
        company: str | None,
        purchase_nos: set[str],
    ) -> dict[tuple[str, str, str], LyMaterialPurchaseOrderItem]:
        if not purchase_nos:
            return {}
        query = (
            self._require_session()
            .query(LyMaterialPurchaseOrder, LyMaterialPurchaseOrderItem)
            .join(LyMaterialPurchaseOrderItem, LyMaterialPurchaseOrderItem.order_id == LyMaterialPurchaseOrder.id)
            .filter(LyMaterialPurchaseOrder.purchase_no.in_(sorted(purchase_nos)))
        )
        if company:
            query = query.filter(LyMaterialPurchaseOrder.company == company)
        rows: dict[tuple[str, str, str], LyMaterialPurchaseOrderItem] = {}
        for order, line in query.all():
            base_key = (str(order.company), str(order.purchase_no))
            rows[(*base_key, str(line.material_item_code))] = line
            rows[(*base_key, str(line.item_code))] = line
        return rows

    @staticmethod
    def _purchase_no_from_source_id(source_id: str) -> str | None:
        normalized = WarehouseService._text(source_id)
        if normalized is None:
            return None
        parts = normalized.split(":")
        if "purchase" in parts:
            index = len(parts) - 1 - list(reversed(parts)).index("purchase")
            if index + 1 < len(parts):
                return parts[index + 1]
        if len(parts) > 1 and parts[-1].startswith("PO-"):
            return parts[-1]
        if len(parts) >= 2 and parts[-2].startswith("PO-"):
            return parts[-2]
        return normalized

    def _local_stock_entry_readback_status(self, *, draft: LyWarehouseStockEntryDraft) -> str:
        outbox = self._latest_outbox_for_draft(int(draft.id))
        if outbox is not None:
            status = self._text(outbox.status)
            if status == "succeeded":
                return "received"
            if status == "in_pending":
                return "outbox_pending"
            if status is not None:
                return f"outbox_{status}"
        return str(draft.status)

    def _local_finished_goods_inbound_status(self, *, draft: LyWarehouseStockEntryDraft) -> str:
        status = self._local_stock_entry_readback_status(draft=draft)
        if status == "received":
            return "received"
        if status == "outbox_pending":
            return "outbox_pending"
        return status

    def _local_stock_receipt_no(self, *, draft: LyWarehouseStockEntryDraft) -> str:
        outbox = self._latest_outbox_for_draft(int(draft.id))
        if outbox is not None:
            external_ref = self._text(outbox.external_ref)
            if external_ref is not None:
                return external_ref
        return f"LY-WH-PR-{int(draft.id)}"

    def _local_stock_balance_map(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> dict[tuple[str, str, str], Decimal]:
        summary = self.get_local_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        return {(str(row.company), str(row.warehouse), str(row.item_code)): Decimal(str(row.actual_qty)) for row in summary.items}

    @staticmethod
    def _inventory_reconciliation_status(
        *,
        count: LyWarehouseInventoryCount,
        line: LyWarehouseInventoryCountItem,
        diff_qty: Decimal,
    ) -> str:
        if diff_qty == Decimal("0"):
            return "balanced"
        review_status = str(line.review_status)
        if review_status == "accepted":
            return "variance_accepted"
        if review_status == "rejected":
            return "variance_rejected"
        if str(count.status) == "confirmed":
            return "confirmed"
        return "pending"

    @staticmethod
    def _paginate_purchase_receipts(
        *,
        items: list[WarehousePurchaseReceiptItem],
        page: int,
        page_size: int,
    ) -> WarehousePurchaseReceiptListData:
        start = max(page - 1, 0) * page_size
        return WarehousePurchaseReceiptListData(items=items[start : start + page_size], total=len(items), page=page, page_size=page_size)

    @staticmethod
    def _paginate_finished_goods_inbound(
        *,
        items: list[WarehouseFinishedGoodsInboundItem],
        page: int,
        page_size: int,
    ) -> WarehouseFinishedGoodsInboundListData:
        start = max(page - 1, 0) * page_size
        return WarehouseFinishedGoodsInboundListData(items=items[start : start + page_size], total=len(items), page=page, page_size=page_size)

    @staticmethod
    def _paginate_inventory_reconciliation(
        *,
        items: list[WarehouseInventoryBalanceReconciliationItem],
        page: int,
        page_size: int,
    ) -> WarehouseInventoryBalanceReconciliationListData:
        start = max(page - 1, 0) * page_size
        return WarehouseInventoryBalanceReconciliationListData(items=items[start : start + page_size], total=len(items), page=page, page_size=page_size)

    def _local_stock_movements(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> list[WarehouseStockMovement]:
        session = self._require_session()
        normalized_company = self._text(company)
        normalized_warehouse = self._text(warehouse)
        normalized_item_code = self._text(item_code)
        query = (
            session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
            .join(
                LyWarehouseStockEntryDraftItem,
                LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id,
            )
            .filter(LyWarehouseStockEntryDraft.status != "cancelled")
        )
        if normalized_company:
            query = query.filter(LyWarehouseStockEntryDraft.company == normalized_company)
        if normalized_item_code:
            query = query.filter(LyWarehouseStockEntryDraftItem.item_code == normalized_item_code)

        movements: list[WarehouseStockMovement] = []

        def add_movement(
            *,
            draft: LyWarehouseStockEntryDraft,
            item: LyWarehouseStockEntryDraftItem,
            warehouse_value: str | None,
            qty: Decimal,
            sequence: int,
        ) -> None:
            warehouse_key = str(warehouse_value or "").strip()
            if not warehouse_key:
                return
            if normalized_warehouse and warehouse_key != normalized_warehouse:
                return
            posting_date = self._local_draft_posting_date(draft=draft)
            movements.append(
                WarehouseStockMovement(
                    company=str(draft.company),
                    warehouse=warehouse_key,
                    item_code=str(item.item_code),
                    posting_date=posting_date,
                    sort_at=draft.created_at or datetime.combine(posting_date, datetime.min.time(), timezone.utc),
                    source_id=int(draft.id),
                    line_id=int(item.id),
                    sequence=sequence,
                    voucher_type=f"Stock Entry Draft/{draft.purpose}",
                    voucher_no=f"DRAFT-{draft.id}",
                    actual_qty=qty,
                    valuation_rate=self._material_unit_price(item_code=str(item.item_code)),
                )
            )

        for draft, item in query.all():
            qty = Decimal(str(item.qty or 0))
            purpose = str(draft.purpose)
            if purpose == "Material Issue":
                add_movement(
                    draft=draft,
                    item=item,
                    warehouse_value=item.source_warehouse or draft.source_warehouse,
                    qty=-qty,
                    sequence=1,
                )
            elif purpose == "Material Transfer":
                add_movement(
                    draft=draft,
                    item=item,
                    warehouse_value=item.source_warehouse or draft.source_warehouse,
                    qty=-qty,
                    sequence=1,
                )
                add_movement(
                    draft=draft,
                    item=item,
                    warehouse_value=item.target_warehouse or draft.target_warehouse,
                    qty=qty,
                    sequence=2,
                )
            else:
                add_movement(
                    draft=draft,
                    item=item,
                    warehouse_value=item.target_warehouse or draft.target_warehouse,
                    qty=qty,
                    sequence=1,
                )

        self._append_subcontract_stock_movements(
            movements=movements,
            company=normalized_company,
            warehouse=normalized_warehouse,
            item_code=normalized_item_code,
        )

        movements.sort(key=lambda row: (row.sort_at, row.source_id, row.line_id, row.sequence, row.warehouse))
        return movements

    def _append_subcontract_stock_movements(
        self,
        *,
        movements: list[WarehouseStockMovement],
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> None:
        session = self._require_session()
        if not self._has_sqlite_subcontract_stock_tables():
            return

        issue_rows = (
            session.query(LySubcontractMaterial, LySubcontractOrder, LySubcontractStockOutbox)
            .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractMaterial.subcontract_id)
            .outerjoin(LySubcontractStockOutbox, LySubcontractStockOutbox.id == LySubcontractMaterial.stock_outbox_id)
            .all()
        )
        for material, order, outbox in issue_rows:
            if not self._is_succeeded_subcontract_stock_fact(fact_row=material, outbox=outbox):
                continue
            company_value = (
                self._text(getattr(material, "company", None))
                or self._text(getattr(order, "company", None))
                or self._text(getattr(outbox, "company", None) if outbox is not None else None)
                or ""
            )
            warehouse_value = self._text(getattr(outbox, "warehouse", None) if outbox is not None else None)
            material_code = self._text(getattr(material, "material_item_code", None))
            if not company_value or not warehouse_value or not material_code:
                continue
            if company and company_value != company:
                continue
            if warehouse and warehouse_value != warehouse:
                continue
            if item_code and material_code != item_code:
                continue
            issued_qty = Decimal(str(getattr(material, "issued_qty", 0) or 0))
            if issued_qty <= Decimal("0"):
                continue
            sort_at = (
                getattr(material, "created_at", None)
                or getattr(outbox, "created_at", None)
                or datetime.combine(date.today(), datetime.min.time(), timezone.utc)
            )
            movements.append(
                WarehouseStockMovement(
                    company=company_value,
                    warehouse=warehouse_value,
                    item_code=material_code,
                    posting_date=sort_at.date(),
                    sort_at=sort_at,
                    source_id=int(getattr(material, "id", 0) or 0),
                    line_id=int(getattr(material, "id", 0) or 0),
                    sequence=1,
                    voucher_type="Subcontract/Material Issue",
                    voucher_no=self._text(getattr(material, "issue_batch_no", None))
                    or self._text(getattr(order, "subcontract_no", None))
                    or f"SUBCONTRACT-ISSUE-{getattr(material, 'id', 0)}",
                    actual_qty=-issued_qty,
                    valuation_rate=self._material_unit_price(item_code=material_code),
                )
            )

        receipt_rows = (
            session.query(LySubcontractReceipt, LySubcontractOrder, LySubcontractStockOutbox)
            .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractReceipt.subcontract_id)
            .outerjoin(LySubcontractStockOutbox, LySubcontractStockOutbox.id == LySubcontractReceipt.stock_outbox_id)
            .all()
        )
        for receipt, order, outbox in receipt_rows:
            if not self._is_succeeded_subcontract_stock_fact(fact_row=receipt, outbox=outbox):
                continue
            company_value = (
                self._text(getattr(receipt, "company", None))
                or self._text(getattr(order, "company", None))
                or self._text(getattr(outbox, "company", None) if outbox is not None else None)
                or ""
            )
            warehouse_value = (
                self._text(getattr(receipt, "receipt_warehouse", None))
                or self._text(getattr(outbox, "warehouse", None) if outbox is not None else None)
            )
            receipt_item_code = self._text(getattr(receipt, "item_code", None)) or self._text(
                getattr(order, "item_code", None)
            )
            if not company_value or not warehouse_value or not receipt_item_code:
                continue
            if company and company_value != company:
                continue
            if warehouse and warehouse_value != warehouse:
                continue
            if item_code and receipt_item_code != item_code:
                continue
            received_qty = Decimal(str(getattr(receipt, "received_qty", 0) or 0))
            if received_qty <= Decimal("0"):
                continue
            sort_at = (
                getattr(receipt, "received_at", None)
                or getattr(receipt, "created_at", None)
                or getattr(outbox, "created_at", None)
                or datetime.combine(date.today(), datetime.min.time(), timezone.utc)
            )
            movements.append(
                WarehouseStockMovement(
                    company=company_value,
                    warehouse=warehouse_value,
                    item_code=receipt_item_code,
                    posting_date=sort_at.date(),
                    sort_at=sort_at,
                    source_id=int(getattr(receipt, "id", 0) or 0),
                    line_id=int(getattr(receipt, "id", 0) or 0),
                    sequence=2,
                    voucher_type="Subcontract/Material Receipt",
                    voucher_no=self._text(getattr(receipt, "receipt_batch_no", None))
                    or self._text(getattr(order, "subcontract_no", None))
                    or f"SUBCONTRACT-RECEIPT-{getattr(receipt, 'id', 0)}",
                    actual_qty=received_qty,
                    valuation_rate=self._material_unit_price(item_code=receipt_item_code),
                )
            )

    def _has_sqlite_subcontract_stock_tables(self) -> bool:
        session = self._require_session()
        bind = session.get_bind()
        if bind.dialect.name != "sqlite":
            return True
        table_names = set(inspect(bind).get_table_names())
        required_tables = {
            LySubcontractMaterial.__tablename__,
            LySubcontractOrder.__tablename__,
            LySubcontractReceipt.__tablename__,
            LySubcontractStockOutbox.__tablename__,
        }
        return required_tables.issubset(table_names)

    def _is_succeeded_subcontract_stock_fact(self, *, fact_row: Any, outbox: LySubcontractStockOutbox | None) -> bool:
        if outbox is None:
            return False
        if self._text(getattr(outbox, "status", None)) != "succeeded":
            return False
        if self._text(getattr(outbox, "stock_entry_name", None)) is None:
            return False
        if self._text(getattr(fact_row, "sync_status", None)) != "succeeded":
            return False
        if self._text(getattr(fact_row, "stock_entry_name", None)) is None:
            return False
        return True

    def _local_draft_posting_date(self, *, draft: LyWarehouseStockEntryDraft) -> date:
        outbox = self._latest_outbox_for_draft(int(draft.id))
        if outbox is not None and isinstance(outbox.payload, dict):
            raw_business_date = self._text(outbox.payload.get("business_date"))
            if raw_business_date is not None:
                try:
                    return date.fromisoformat(raw_business_date)
                except ValueError:
                    pass
        if draft.created_at is not None:
            return draft.created_at.date()
        return date.today()

    def _local_read_fallback_enabled(self) -> bool:
        app_env = os.getenv("APP_ENV", "").strip().lower()
        db_url = os.getenv("LINGYI_DB_URL", "").strip()
        allow_dev_auth = os.getenv("LINGYI_ALLOW_DEV_AUTH", "").strip().lower()
        return (
            self.session is not None
            and app_env in {"development", "dev", "local"}
            and db_url == "sqlite:///./lingyi_service.local.db"
            and allow_dev_auth == "true"
        )

    def _local_stock_summary(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> WarehouseStockSummaryData:
        normalized_company = self._text(company)
        normalized_warehouse = self._text(warehouse)
        normalized_item_code = self._text(item_code)
        grouped: dict[tuple[str, str, str], Decimal] = {}
        for movement in self._local_stock_movements(company=company, warehouse=warehouse, item_code=item_code):
            key = (movement.company, movement.warehouse, movement.item_code)
            grouped[key] = grouped.get(key, Decimal("0")) + movement.actual_qty

        items = [
            WarehouseStockSummaryItem(
                company=company_key,
                warehouse=warehouse_key,
                item_code=item_key,
                actual_qty=qty,
                projected_qty=qty,
                reserved_qty=Decimal("0"),
                ordered_qty=Decimal("0"),
                reorder_level=Decimal("0"),
                safety_stock=Decimal("0"),
                threshold_missing=False,
                is_below_reorder=False,
                is_below_safety=False,
            )
            for (company_key, warehouse_key, item_key), qty in sorted(grouped.items())
        ]
        return WarehouseStockSummaryData(
            company=normalized_company,
            warehouse=normalized_warehouse,
            item_code=normalized_item_code,
            items=items,
            warehouse_management=self._build_management_overview(items=items),
            material_inventory=self._build_material_inventory(items=items),
        )

    def list_other_inbound(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
    ) -> WarehouseOtherInboundData:
        summary = self.get_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        status_filter = (status or "").strip().lower() or None
        rows: list[WarehouseOtherInboundItem] = []
        for index, row in enumerate(summary.items, start=1):
            material_name = self._material_name_from_code(row.item_code)
            material_category = self._material_category_from_code(row.item_code)
            qty = Decimal(str(row.actual_qty)).quantize(Decimal("0.01"))
            amount = (qty * self._material_unit_price(item_code=row.item_code)).quantize(Decimal("0.01"))
            inbound_status = self._other_inbound_status(row=row)
            if status_filter is not None and inbound_status != status_filter:
                continue

            rows.append(
                WarehouseOtherInboundItem(
                    inbound_no=f"OIN-{datetime.now(timezone.utc).strftime('%Y%m')}-{index:04d}",
                    supplier=self._supplier_from_material(material_category=material_category),
                    material_code=row.item_code,
                    material_name=material_name,
                    warehouse=row.warehouse,
                    location=self._material_location(warehouse=row.warehouse, index=index),
                    qty=qty,
                    amount=amount,
                    inbound_date=date.today(),
                    source_doc_no=f"SRC-{row.item_code}-{index:03d}",
                    operator="系统只读映射",
                    status=inbound_status,
                )
            )
        rows.sort(key=lambda item: (item.status, item.inbound_no, item.material_code))
        return WarehouseOtherInboundData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            status=status_filter,
            items=rows,
        )

    def list_purchase_return_outbound(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
    ) -> WarehousePurchaseReturnOutboundData:
        summary = self.get_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        status_filter = (status or "").strip().lower() or None
        rows: list[WarehousePurchaseReturnOutboundItem] = []
        for index, row in enumerate(summary.items, start=1):
            material_name = self._material_name_from_code(row.item_code)
            material_category = self._material_category_from_code(row.item_code)
            qty = Decimal(str(row.actual_qty)).quantize(Decimal("0.01"))
            amount = (qty * self._material_unit_price(item_code=row.item_code)).quantize(Decimal("0.01"))
            outbound_status = self._purchase_return_outbound_status(row=row)
            if status_filter is not None and outbound_status != status_filter:
                continue

            rows.append(
                WarehousePurchaseReturnOutboundItem(
                    outbound_no=f"PRO-{datetime.now(timezone.utc).strftime('%Y%m')}-{index:04d}",
                    supplier=self._supplier_from_material(material_category=material_category),
                    material_code=row.item_code,
                    material_name=material_name,
                    warehouse=row.warehouse,
                    location=self._material_location(warehouse=row.warehouse, index=index),
                    qty=qty,
                    amount=amount,
                    outbound_date=date.today(),
                    source_doc_no=f"PRR-{row.item_code}-{index:03d}",
                    operator="系统只读映射",
                    status=outbound_status,
                )
            )
        rows.sort(key=lambda item: (item.status, item.outbound_no, item.material_code))
        return WarehousePurchaseReturnOutboundData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            status=status_filter,
            items=rows,
        )

    def list_factory_return_material_report(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
    ) -> WarehouseFactoryReturnMaterialReportData:
        summary = self.get_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        return self._factory_return_material_report_from_summary(
            summary=summary,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            status=status,
        )

    def list_local_factory_return_material_report(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
    ) -> WarehouseFactoryReturnMaterialReportData:
        return self._factory_return_material_report_from_subcontract_issues(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            status=status,
        )

    def _factory_return_material_report_from_summary(
        self,
        *,
        summary: WarehouseStockSummaryData,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
    ) -> WarehouseFactoryReturnMaterialReportData:
        status_filter = (status or "").strip().lower() or None
        rows: list[WarehouseFactoryReturnMaterialReportItem] = []
        for index, row in enumerate(summary.items, start=1):
            material_name = self._material_name_from_code(row.item_code)
            material_category = self._material_category_from_code(row.item_code)
            status_value = self._factory_return_material_report_status(row=row)
            if status_filter is not None and status_value != status_filter:
                continue

            base_qty = Decimal(str(abs(row.actual_qty))).quantize(Decimal("0.01"))
            planned_return_qty = (base_qty * Decimal("0.35")).quantize(Decimal("0.01"))
            if status_value == "closed":
                returned_qty = planned_return_qty
            elif status_value == "confirmed":
                returned_qty = (planned_return_qty * Decimal("0.85")).quantize(Decimal("0.01"))
            else:
                returned_qty = (planned_return_qty * Decimal("0.30")).quantize(Decimal("0.01"))
            pending_qty = max((planned_return_qty - returned_qty).quantize(Decimal("0.01")), Decimal("0.00"))

            rows.append(
                WarehouseFactoryReturnMaterialReportItem(
                    report_no=f"FRR-{datetime.now(timezone.utc).strftime('%Y%m')}-{index:04d}",
                    factory_name=self._factory_name_from_material(material_category=material_category),
                    material_code=row.item_code,
                    material_name=material_name,
                    warehouse=row.warehouse,
                    location=self._material_location(warehouse=row.warehouse, index=index),
                    planned_return_qty=planned_return_qty,
                    returned_qty=returned_qty,
                    pending_qty=pending_qty,
                    report_date=date.today(),
                    source_doc_no=f"FRT-{row.item_code}-{index:03d}",
                    operator="系统只读映射",
                    status=status_value,
                )
            )

        rows.sort(key=lambda item: (item.status, item.report_no, item.material_code))
        return WarehouseFactoryReturnMaterialReportData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            status=status_filter,
            items=rows,
        )

    def _factory_return_material_report_from_subcontract_issues(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
    ) -> WarehouseFactoryReturnMaterialReportData:
        session = self._require_session()
        normalized_company = self._text(company)
        normalized_warehouse = self._text(warehouse)
        normalized_item_code = self._text(item_code)
        status_filter = (status or "").strip().lower() or None

        if not self._has_sqlite_subcontract_stock_tables():
            return WarehouseFactoryReturnMaterialReportData(
                company=normalized_company,
                warehouse=normalized_warehouse,
                item_code=normalized_item_code,
                status=status_filter,
                items=[],
            )

        query = (
            session.query(LySubcontractMaterial, LySubcontractOrder, LySubcontractStockOutbox)
            .join(
                LySubcontractOrder,
                LySubcontractOrder.id == LySubcontractMaterial.subcontract_id,
            )
            .outerjoin(
                LySubcontractStockOutbox,
                LySubcontractStockOutbox.id == LySubcontractMaterial.stock_outbox_id,
            )
            .order_by(LySubcontractOrder.subcontract_no.asc(), LySubcontractMaterial.material_item_code.asc())
        )
        source_rows = query.all()

        grouped: dict[tuple[str, str, int, str], dict[str, Any]] = {}
        for material, order, outbox in source_rows:
            if not self._is_succeeded_subcontract_stock_fact(fact_row=material, outbox=outbox):
                continue
            company_value = (
                self._text(getattr(order, "company", None))
                or self._text(getattr(material, "company", None))
                or self._text(getattr(outbox, "company", None) if outbox is not None else None)
                or ""
            )
            warehouse_value = self._text(getattr(outbox, "warehouse", None) if outbox is not None else None) or "未指定仓库"
            material_code = self._text(getattr(material, "material_item_code", None)) or ""
            if not material_code:
                continue
            if normalized_company and company_value != normalized_company:
                continue
            if normalized_warehouse and warehouse_value != normalized_warehouse:
                continue
            if normalized_item_code and material_code != normalized_item_code:
                continue

            order_id = int(order.id)
            key = (company_value, warehouse_value, order_id, material_code)
            bucket = grouped.setdefault(
                key,
                {
                    "company": company_value,
                    "warehouse": warehouse_value,
                    "order": order,
                    "material_code": material_code,
                    "required_qty": Decimal("0"),
                    "issued_qty": Decimal("0"),
                    "latest_created_at": getattr(material, "created_at", None),
                },
            )
            bucket["required_qty"] = max(
                Decimal(str(bucket["required_qty"])),
                Decimal(str(getattr(material, "required_qty", 0) or 0)),
            )
            bucket["issued_qty"] = Decimal(str(bucket["issued_qty"])) + Decimal(
                str(getattr(material, "issued_qty", 0) or 0)
            )
            material_created_at = getattr(material, "created_at", None)
            if material_created_at is not None:
                latest_created_at = bucket.get("latest_created_at")
                if latest_created_at is None or material_created_at > latest_created_at:
                    bucket["latest_created_at"] = material_created_at

        rows: list[WarehouseFactoryReturnMaterialReportItem] = []
        for index, bucket in enumerate(grouped.values(), start=1):
            order = bucket["order"]
            issued_qty = Decimal(str(bucket["issued_qty"])).quantize(Decimal("0.01"))
            required_qty = Decimal(str(bucket["required_qty"]))
            planned_qty = Decimal(str(getattr(order, "planned_qty", 0) or 0))
            accepted_qty = Decimal(str(getattr(order, "accepted_qty", 0) or 0))
            received_qty = Decimal(str(getattr(order, "received_qty", 0) or 0))
            output_qty = accepted_qty if accepted_qty > Decimal("0") else received_qty
            if planned_qty > Decimal("0") and required_qty > Decimal("0") and output_qty > Decimal("0"):
                effective_output_qty = min(output_qty, planned_qty)
                theoretical_usage_qty = (required_qty * effective_output_qty / planned_qty).quantize(Decimal("0.01"))
            else:
                theoretical_usage_qty = Decimal("0.00")

            planned_return_qty = max((issued_qty - theoretical_usage_qty).quantize(Decimal("0.01")), Decimal("0.00"))
            returned_qty = Decimal("0.00")
            pending_qty = max((planned_return_qty - returned_qty).quantize(Decimal("0.01")), Decimal("0.00"))
            if pending_qty == Decimal("0.00"):
                status_value: Literal["pending", "confirmed", "closed"] = "closed"
            elif returned_qty > Decimal("0.00"):
                status_value = "confirmed"
            else:
                status_value = "pending"
            if status_filter is not None and status_value != status_filter:
                continue

            created_at = bucket.get("latest_created_at")
            report_date = created_at.date() if created_at is not None else date.today()
            material_code = str(bucket["material_code"])
            warehouse_value = str(bucket["warehouse"])
            subcontract_no = str(getattr(order, "subcontract_no", "") or "")
            rows.append(
                WarehouseFactoryReturnMaterialReportItem(
                    report_no=f"FRR-{subcontract_no}-{index:03d}",
                    subcontract_no=subcontract_no,
                    factory_name=str(getattr(order, "supplier", "") or "未指定加工厂"),
                    material_code=material_code,
                    material_name=self._material_name_from_code(material_code),
                    warehouse=warehouse_value,
                    location=self._material_location(warehouse=warehouse_value, index=index),
                    issued_qty=issued_qty,
                    theoretical_usage_qty=theoretical_usage_qty,
                    planned_return_qty=planned_return_qty,
                    returned_qty=returned_qty,
                    pending_qty=pending_qty,
                    report_date=report_date,
                    source_doc_no=subcontract_no,
                    operator="FastAPI 外发发料事实",
                    status=status_value,
                )
            )

        rows.sort(key=lambda item: (item.status, item.report_no, item.material_code))
        return WarehouseFactoryReturnMaterialReportData(
            company=normalized_company,
            warehouse=normalized_warehouse,
            item_code=normalized_item_code,
            status=status_filter,
            items=rows,
        )

    def list_local_material_retention_report(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        keyword: str | None,
        min_retention_days: int | None,
        as_of_date: date | None,
    ) -> WarehouseMaterialRetentionReportData:
        normalized_keyword = self._text(keyword)
        normalized_min_days = max(int(min_retention_days or 0), 0) if min_retention_days is not None else None
        report_date = as_of_date or date.today()
        movements = self._local_stock_movements(company=company, warehouse=warehouse, item_code=None)
        grouped: dict[tuple[str, str, str], dict[str, Any]] = {}

        for movement in movements:
            key = (movement.company, movement.warehouse, movement.item_code)
            bucket = grouped.setdefault(
                key,
                {
                    "stock_qty": Decimal("0"),
                    "last_in_date": None,
                    "last_out_date": None,
                    "valuation_rate": movement.valuation_rate,
                },
            )
            bucket["stock_qty"] = Decimal(str(bucket["stock_qty"])) + movement.actual_qty
            if movement.actual_qty > 0:
                last_in_date = bucket["last_in_date"]
                bucket["last_in_date"] = max(last_in_date, movement.posting_date) if last_in_date else movement.posting_date
            elif movement.actual_qty < 0:
                last_out_date = bucket["last_out_date"]
                bucket["last_out_date"] = max(last_out_date, movement.posting_date) if last_out_date else movement.posting_date
            bucket["valuation_rate"] = movement.valuation_rate

        rows: list[WarehouseMaterialRetentionReportItem] = []
        for index, ((company_key, warehouse_key, item_key), bucket) in enumerate(sorted(grouped.items()), start=1):
            stock_qty = Decimal(str(bucket["stock_qty"])).quantize(Decimal("0.01"))
            if stock_qty <= 0:
                continue
            material_name = self._material_name_from_code(item_key)
            material_category = self._material_category_from_code(item_key)
            supplier = self._supplier_from_material(material_category=material_category)
            if normalized_keyword and normalized_keyword.lower() not in " ".join(
                [item_key, material_name, material_category, warehouse_key, supplier]
            ).lower():
                continue

            last_in_date = bucket["last_in_date"]
            last_out_date = bucket["last_out_date"]
            anchor_date = max([value for value in (last_in_date, last_out_date) if value is not None], default=report_date)
            retention_days = max((report_date - anchor_date).days, 0)
            if normalized_min_days is not None and retention_days < normalized_min_days:
                continue

            risk_level = self._material_retention_risk_level(retention_days=retention_days)
            status_value = self._material_retention_status(risk_level=risk_level)
            valuation_rate = Decimal(str(bucket["valuation_rate"]))
            stock_amount = (stock_qty * valuation_rate).quantize(Decimal("0.01"))
            rows.append(
                WarehouseMaterialRetentionReportItem(
                    report_no=f"MRR-{report_date.strftime('%Y%m')}-{len(rows) + 1:04d}",
                    material_code=item_key,
                    material_name=material_name,
                    material_category=material_category,
                    warehouse=warehouse_key,
                    location=self._material_location(warehouse=warehouse_key, index=index),
                    color=self._material_color_from_code(item_key=item_key),
                    spec=self._material_spec_from_code(item_key=item_key),
                    unit=self._material_unit_from_category(material_category=material_category),
                    stock_qty=stock_qty,
                    stock_amount=stock_amount,
                    last_in_date=last_in_date,
                    last_out_date=last_out_date,
                    retention_days=retention_days,
                    risk_level=risk_level,
                    supplier=supplier,
                    suggestion=self._material_retention_suggestion(risk_level=risk_level),
                    owner="库存管理员",
                    reason=self._material_retention_reason(
                        last_in_date=last_in_date,
                        last_out_date=last_out_date,
                        retention_days=retention_days,
                    ),
                    status=status_value,
                )
            )

        rows.sort(key=lambda item: (-item.retention_days, item.warehouse, item.material_code))
        return WarehouseMaterialRetentionReportData(
            company=self._text(company),
            warehouse=self._text(warehouse),
            keyword=normalized_keyword,
            min_retention_days=normalized_min_days,
            as_of_date=report_date,
            items=rows,
        )

    def list_semi_finished_outbound(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        status: str | None,
    ) -> WarehouseSemiFinishedOutboundData:
        summary = self.get_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        status_filter = (status or "").strip().lower() or None
        rows: list[WarehouseSemiFinishedOutboundItem] = []
        for index, row in enumerate(summary.items, start=1):
            status_value = self._semi_finished_outbound_status(row=row)
            if status_filter is not None and status_value != status_filter:
                continue

            qty = (Decimal(str(abs(row.actual_qty))) * Decimal("0.25")).quantize(Decimal("0.01"))
            amount = (qty * self._material_unit_price(item_code=row.item_code) * Decimal("1.15")).quantize(
                Decimal("0.01")
            )
            rows.append(
                WarehouseSemiFinishedOutboundItem(
                    outbound_no=f"SFO-{datetime.now(timezone.utc).strftime('%Y%m')}-{index:04d}",
                    source_doc_no=f"SFO-SRC-{row.item_code}-{index:03d}",
                    semi_finished_code=row.item_code,
                    semi_finished_name=f"半成品-{row.item_code}",
                    warehouse=row.warehouse,
                    location=self._material_location(warehouse=row.warehouse, index=index),
                    qty=qty,
                    amount=amount,
                    outbound_date=date.today(),
                    destination=self._semi_finished_destination(warehouse=row.warehouse, index=index),
                    operator="系统只读映射",
                    status=status_value,
                )
            )
        rows.sort(key=lambda item: (item.status, item.outbound_no, item.semi_finished_code))
        return WarehouseSemiFinishedOutboundData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            status=status_filter,
            items=rows,
        )

    @staticmethod
    def _build_management_overview(*, items: list[WarehouseStockSummaryItem]) -> list[WarehouseManagementItem]:
        by_warehouse: dict[str, dict[str, Any]] = {}
        for row in items:
            key = row.warehouse.strip() or "UNKNOWN"
            bucket = by_warehouse.setdefault(
                key,
                {
                    "warehouse_name": row.warehouse,
                    "used_qty": Decimal("0"),
                    "below_count": 0,
                    "has_threshold_missing": False,
                },
            )
            bucket["used_qty"] += Decimal(str(row.actual_qty))
            if row.is_below_safety or row.is_below_reorder:
                bucket["below_count"] += 1
            if row.threshold_missing:
                bucket["has_threshold_missing"] = True

        management_rows: list[WarehouseManagementItem] = []
        for warehouse_code, bucket in sorted(by_warehouse.items(), key=lambda kv: kv[0]):
            used_qty = Decimal(str(bucket["used_qty"]))
            capacity_qty = max((used_qty * Decimal("1.35")).quantize(Decimal("0.01")), Decimal("120.00"))
            utilization_rate = ((used_qty / capacity_qty) * Decimal("100")).quantize(Decimal("0.01"))

            status = "normal"
            if bucket["has_threshold_missing"]:
                status = "disabled"
            elif bucket["below_count"] > 0:
                status = "warning"

            management_rows.append(
                WarehouseManagementItem(
                    warehouse_code=warehouse_code,
                    warehouse_name=bucket["warehouse_name"],
                    warehouse_type=WarehouseService._warehouse_type_from_name(bucket["warehouse_name"]),
                    manager="仓库管理员A" if status != "disabled" else "待配置",
                    status=status,
                    capacity_qty=capacity_qty,
                    used_qty=used_qty.quantize(Decimal("0.01")),
                    utilization_rate=utilization_rate,
                )
            )
        return management_rows

    @staticmethod
    def _warehouse_type_from_name(name: str) -> str:
        text = (name or "").strip()
        if "样衣" in text:
            return "样衣仓"
        if "成品" in text:
            return "成品仓"
        if "原料" in text or "辅料" in text:
            return "物料仓"
        return "综合仓"

    @staticmethod
    def _build_material_inventory(*, items: list[WarehouseStockSummaryItem]) -> list[WarehouseMaterialInventoryItem]:
        rows: list[WarehouseMaterialInventoryItem] = []
        sorted_items = sorted(items, key=lambda row: (row.warehouse, row.item_code))
        for index, row in enumerate(sorted_items, start=1):
            qty = Decimal(str(row.actual_qty)).quantize(Decimal("0.01"))
            unit_price = WarehouseService._material_unit_price(item_code=row.item_code)
            amount = (qty * unit_price).quantize(Decimal("0.01"))

            status = "normal"
            if row.threshold_missing:
                status = "disabled"
            elif row.is_below_safety or row.is_below_reorder:
                status = "warning"

            rows.append(
                WarehouseMaterialInventoryItem(
                    material_code=row.item_code,
                    material_name=WarehouseService._material_name_from_code(row.item_code),
                    material_category=WarehouseService._material_category_from_code(row.item_code),
                    warehouse=row.warehouse,
                    location=WarehouseService._material_location(warehouse=row.warehouse, index=index),
                    qty=qty,
                    amount=amount,
                    status=status,
                )
            )
        return rows

    @staticmethod
    def _supplier_from_material(*, material_category: str) -> str:
        if material_category == "面料":
            return "华纺供应商"
        if material_category == "辅料":
            return "永盛辅料"
        if material_category == "包材":
            return "恒彩包材"
        return "综合供应商"

    @staticmethod
    def _other_inbound_status(*, row: WarehouseStockSummaryItem) -> Literal["pending", "received", "closed"]:
        if row.threshold_missing:
            return "closed"
        if row.is_below_safety or row.is_below_reorder:
            return "pending"
        return "received"

    @staticmethod
    def _purchase_return_outbound_status(*, row: WarehouseStockSummaryItem) -> Literal["pending", "returned", "closed"]:
        if row.threshold_missing:
            return "closed"
        if row.is_below_safety or row.is_below_reorder:
            return "pending"
        return "returned"

    @staticmethod
    def _factory_return_material_report_status(
        *,
        row: WarehouseStockSummaryItem,
    ) -> Literal["pending", "confirmed", "closed"]:
        if row.threshold_missing:
            return "closed"
        if row.is_below_safety or row.is_below_reorder:
            return "pending"
        return "confirmed"

    @staticmethod
    def _factory_name_from_material(*, material_category: str) -> str:
        if material_category == "面料":
            return "恒达加工厂"
        if material_category == "辅料":
            return "嘉成加工厂"
        if material_category == "包材":
            return "丰润加工厂"
        return "综合加工厂"

    @staticmethod
    def _semi_finished_outbound_status(
        *,
        row: WarehouseStockSummaryItem,
    ) -> Literal["pending", "confirmed", "closed"]:
        if row.threshold_missing:
            return "closed"
        if row.is_below_safety or row.is_below_reorder:
            return "pending"
        return "confirmed"

    @staticmethod
    def _semi_finished_destination(*, warehouse: str, index: int) -> str:
        text = (warehouse or "").strip()
        if "样衣" in text:
            return "样衣后整工段"
        if "成品" in text:
            return "成品复检工段"
        suffix = ((index - 1) % 6) + 1
        return f"半成品周转区-{suffix}"

    @staticmethod
    def _material_name_from_code(item_code: str) -> str:
        code = (item_code or "").strip()
        if not code:
            return "未命名物料"
        return f"物料-{code}"

    @staticmethod
    def _material_category_from_code(item_code: str) -> str:
        code = (item_code or "").upper()
        if code.startswith("FAB") or code.startswith("M-") or "FABRIC" in code:
            return "面料"
        if code.startswith("ACC") or code.startswith("TRIM") or code.startswith("PKG"):
            return "辅料"
        if code.startswith("LBL") or code.startswith("TAG"):
            return "包材"
        return "综合物料"

    @staticmethod
    def _material_unit_price(*, item_code: str) -> Decimal:
        category = WarehouseService._material_category_from_code(item_code)
        if category == "面料":
            return Decimal("8.60")
        if category == "辅料":
            return Decimal("3.20")
        if category == "包材":
            return Decimal("1.50")
        return Decimal("5.00")

    @staticmethod
    def _material_location(*, warehouse: str, index: int) -> str:
        zone_prefix = "A"
        text = (warehouse or "").strip()
        if "样衣" in text:
            zone_prefix = "Y"
        elif "成品" in text:
            zone_prefix = "F"
        elif "原料" in text or "辅料" in text:
            zone_prefix = "M"
        slot = ((index - 1) % 24) + 1
        return f"{zone_prefix}-{slot:02d}"

    @staticmethod
    def _material_color_from_code(*, item_key: str) -> str:
        code = (item_key or "").upper()
        if "BLACK" in code or "BLK" in code:
            return "黑色"
        if "WHITE" in code or "WHT" in code:
            return "白色"
        if "RED" in code:
            return "红色"
        if "BLUE" in code:
            return "蓝色"
        return "本色"

    @staticmethod
    def _material_spec_from_code(*, item_key: str) -> str:
        code = (item_key or "").upper()
        if code.startswith("FAB"):
            return "幅宽150cm"
        if code.startswith("ACC") or code.startswith("TRIM"):
            return "通用辅料规格"
        if code.startswith("PKG") or code.startswith("TAG") or code.startswith("LBL"):
            return "包装规格"
        return "标准规格"

    @staticmethod
    def _material_unit_from_category(*, material_category: str) -> str:
        if material_category == "面料":
            return "米"
        if material_category == "包材":
            return "个"
        return "件"

    @staticmethod
    def _material_retention_risk_level(*, retention_days: int) -> Literal["high", "medium", "low"]:
        if retention_days >= 180:
            return "high"
        if retention_days >= 90:
            return "medium"
        return "low"

    @staticmethod
    def _material_retention_status(*, risk_level: Literal["high", "medium", "low"]) -> Literal["normal", "attention", "stale"]:
        if risk_level == "high":
            return "stale"
        if risk_level == "medium":
            return "attention"
        return "normal"

    @staticmethod
    def _material_retention_suggestion(*, risk_level: Literal["high", "medium", "low"]) -> str:
        if risk_level == "high":
            return "优先调拨或折价处理"
        if risk_level == "medium":
            return "复核后续订单用料计划"
        return "持续观察"

    @staticmethod
    def _material_retention_reason(
        *,
        last_in_date: date | None,
        last_out_date: date | None,
        retention_days: int,
    ) -> str:
        if last_out_date is None:
            return f"入库后 {retention_days} 天未发生出库"
        if last_in_date is not None and last_in_date > last_out_date:
            return f"最近入库后 {retention_days} 天未消耗"
        return f"最近出库后 {retention_days} 天未再流转"

    def get_alerts(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
        alert_type: str | None,
    ) -> WarehouseAlertsData:
        summary = self.get_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        latest_dates = self._require_adapter().latest_movement_by_item_warehouse(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
        )

        normalized_alert = (alert_type or "").strip().lower() or None
        supported = {"low_stock", "below_safety", "overstock", "stale_stock"}
        if normalized_alert is not None and normalized_alert not in supported:
            normalized_alert = None

        rows: list[WarehouseAlertItem] = []
        for item in summary.items:
            key = (item.item_code, item.warehouse)
            last_movement = latest_dates.get(key)
            rows.extend(
                self._alerts_for_summary_item(
                    item=item,
                    last_movement_date=last_movement,
                    filter_alert_type=normalized_alert,
                )
            )

        rows.sort(key=lambda row: (row.alert_type, row.company, row.warehouse, row.item_code))
        return WarehouseAlertsData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            alert_type=normalized_alert,
            items=rows,
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
    ) -> WarehouseBatchListData:
        rows, total = self._require_adapter().list_batches(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            page=page,
            page_size=page_size,
        )
        return WarehouseBatchListData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            total=total,
            items=[WarehouseBatchItem(**row) for row in rows],
        )

    def get_batch_detail(
        self,
        *,
        batch_no: str,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> WarehouseBatchDetailData:
        detail = self._require_adapter().get_batch_detail(
            batch_no=batch_no,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
        )
        return WarehouseBatchDetailData(
            batch_no=str(detail["batch_no"]),
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            total=int(detail.get("total", 0)),
            items=[WarehouseBatchItem(**row) for row in detail.get("items", [])],
        )

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
    ) -> WarehouseSerialNumberListData:
        rows, total = self._require_adapter().list_serial_numbers(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            serial_no=serial_no,
            page=page,
            page_size=page_size,
        )
        return WarehouseSerialNumberListData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            serial_no=serial_no,
            total=total,
            items=[WarehouseSerialNumberItem(**row) for row in rows],
        )

    def get_serial_number_detail(
        self,
        *,
        serial_no: str,
        company: str | None,
        warehouse: str | None,
        item_code: str | None,
    ) -> WarehouseSerialNumberDetailData:
        detail = self._require_adapter().get_serial_number_detail(
            serial_no=serial_no,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
        )
        return WarehouseSerialNumberDetailData(
            serial_no=str(detail["serial_no"]),
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            total=int(detail.get("total", 0)),
            items=[WarehouseSerialNumberItem(**row) for row in detail.get("items", [])],
        )

    def list_traceability(
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
    ) -> WarehouseTraceabilityData:
        rows, total = self._require_adapter().list_traceability_entries(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            serial_no=serial_no,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        return WarehouseTraceabilityData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            serial_no=serial_no,
            page=page,
            page_size=page_size,
            total=total,
            items=[WarehouseTraceabilityItem(**row) for row in rows],
        )

    def list_finished_goods_inbound_candidates(
        self,
        *,
        company: str | None,
    ) -> WarehouseFinishedGoodsInboundCandidatesData:
        rows = self._require_adapter().list_finished_goods_inbound_candidates(company=company)
        items = [
            WarehouseFinishedGoodsInboundCandidateItem(
                source_id=str(row["source_id"]),
                source_label=str(row["source_label"]),
                item_code=str(row["item_code"]),
                qty=Decimal(str(row["qty"])),
                uom=str(row["uom"]),
                disabled=bool(row.get("disabled", False)),
                disabled_reason=self._text(row.get("disabled_reason")),
            )
            for row in rows
        ]
        items.sort(key=lambda row: (row.disabled, row.source_label, row.item_code))
        return WarehouseFinishedGoodsInboundCandidatesData(
            company=company,
            show_completed_forced=True,
            disabled_entry_label=self._FINISHED_GOODS_DISABLED_ENTRY_LABEL,
            disabled_entry_reason=self._FINISHED_GOODS_DISABLED_ENTRY_REASON,
            allocation_contract=self._ALLOCATION_CONTRACT,
            items=items,
        )

    def create_stock_entry_draft(
        self,
        *,
        payload: WarehouseStockEntryDraftCreateRequest,
        current_user: str,
    ) -> WarehouseStockEntryDraftData:
        session = self._require_session()

        company = self._require_text(payload.company, "company")
        finished_goods_source_id = self._text(payload.finished_goods_source_id)
        source_warehouse = self._text(payload.source_warehouse)
        target_warehouse = self._text(payload.target_warehouse)
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        allocation_mode: str | None = None
        strict_failure_reason: str | None = None
        show_completed_forced: bool | None = None

        if finished_goods_source_id is not None:
            purpose = "Material Receipt"
            source_type = self._FINISHED_GOODS_SOURCE_TYPE
            source_id = finished_goods_source_id
            show_completed_forced = True
            self._validate_purpose_warehouses(
                purpose=purpose,
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
            )
            item_rows, allocation_mode, strict_failure_reason = self._resolve_finished_goods_item_rows(
                company=company,
                source_id=source_id,
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
                items=payload.items,
            )
        else:
            purpose = self._require_text(payload.purpose, "purpose")
            if purpose not in self._PURPOSES:
                raise WarehouseServiceError(400, "WAREHOUSE_INVALID_PURPOSE", "purpose 非法")

            source_type = self._require_text(payload.source_type, "source_type")
            source_id = self._require_text(payload.source_id, "source_id")
            self._validate_purpose_warehouses(
                purpose=purpose,
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
            )
            item_rows = self._normalize_item_payloads(
                items=payload.items,
                fallback_source_warehouse=source_warehouse,
                fallback_target_warehouse=target_warehouse,
            )

        expected_outbox_payload = self._build_stock_entry_replay_payload(
            company=company,
            purpose=purpose,
            source_type=source_type,
            source_id=source_id,
            business_date=payload.business_date,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            item_rows=item_rows,
            allocation_mode=allocation_mode,
            strict_failure_reason=strict_failure_reason,
            show_completed_forced=show_completed_forced,
            finished_goods_source_id=finished_goods_source_id,
        )

        existing_by_idempotency = (
            session.query(LyWarehouseStockEntryDraft)
            .filter(
                LyWarehouseStockEntryDraft.company == company,
                LyWarehouseStockEntryDraft.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_by_idempotency is not None:
            self._ensure_stock_entry_replay_matches(
                existing_by_idempotency,
                expected_payload=expected_outbox_payload,
                message="幂等键冲突且请求内容不一致",
            )
            return self._build_draft_data(existing_by_idempotency)

        existing_by_source = (
            session.query(LyWarehouseStockEntryDraft)
            .filter(
                LyWarehouseStockEntryDraft.company == company,
                LyWarehouseStockEntryDraft.source_type == source_type,
                LyWarehouseStockEntryDraft.source_id == source_id,
                LyWarehouseStockEntryDraft.status != "cancelled",
            )
            .first()
        )
        if existing_by_source is not None:
            self._ensure_stock_entry_replay_matches(
                existing_by_source,
                expected_payload=expected_outbox_payload,
                message="source 已存在且请求内容不一致",
            )
            return self._build_draft_data(existing_by_source)

        if source_type == MaterialPurchaseService.PURCHASE_SOURCE_TYPE and purpose == "Material Receipt":
            self._validate_material_purchase_receipt(company=company, source_id=source_id, items=item_rows)

        now = datetime.now(timezone.utc)
        event_key = self._build_event_key(
            company=company,
            source_type=source_type,
            source_id=source_id,
            idempotency_key=idempotency_key,
        )

        draft = LyWarehouseStockEntryDraft(
            company=company,
            purpose=purpose,
            source_type=source_type,
            source_id=source_id,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            status="pending_outbox",
            created_by=current_user,
            created_at=now,
            idempotency_key=idempotency_key,
            event_key=event_key,
        )
        session.add(draft)
        session.flush()

        for row in item_rows:
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=draft.id,
                    company=company,
                    item_code=row["item_code"],
                    qty=row["qty"],
                    uom=row["uom"],
                    batch_no=row.get("batch_no"),
                    serial_no=row.get("serial_no"),
                    source_warehouse=row.get("source_warehouse"),
                    target_warehouse=row.get("target_warehouse"),
                )
            )

        outbox_payload = {"draft_id": int(draft.id), **expected_outbox_payload}
        session.add(
            LyWarehouseStockEntryOutboxEvent(
                draft_id=draft.id,
                event_type="warehouse_stock_entry_sync",
                event_key=event_key,
                payload=outbox_payload,
                status="in_pending",
                retry_count=0,
                created_at=now,
            )
        )
        session.flush()

        if source_type == MaterialPurchaseService.PURCHASE_SOURCE_TYPE and purpose == "Material Receipt":
            self._apply_material_purchase_receipt(company=company, source_id=source_id, items=item_rows)
            session.flush()

        return self._build_draft_data(draft)

    def list_stock_entry_drafts(
        self,
        *,
        company: str | None,
        purpose: str | None,
        source_type: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> WarehouseStockEntryDraftListData:
        session = self._require_session()
        query = session.query(LyWarehouseStockEntryDraft)
        normalized_company = self._text(company)
        if normalized_company:
            query = query.filter(LyWarehouseStockEntryDraft.company == normalized_company)
        normalized_purpose = self._text(purpose)
        if normalized_purpose:
            query = query.filter(LyWarehouseStockEntryDraft.purpose == normalized_purpose)
        normalized_source_type = self._text(source_type)
        if normalized_source_type:
            query = query.filter(LyWarehouseStockEntryDraft.source_type == normalized_source_type)
        normalized_status = self._text(status)
        if normalized_status:
            query = query.filter(LyWarehouseStockEntryDraft.status == normalized_status)
        normalized_keyword = self._text(keyword)
        if normalized_keyword:
            like_value = f"%{normalized_keyword.lower()}%"
            query = query.filter(
                (func.lower(LyWarehouseStockEntryDraft.source_id).like(like_value))
                | (func.lower(LyWarehouseStockEntryDraft.source_type).like(like_value))
                | (func.lower(LyWarehouseStockEntryDraft.source_warehouse).like(like_value))
                | (func.lower(LyWarehouseStockEntryDraft.target_warehouse).like(like_value))
            )
        total = int(query.count())
        rows = (
            query.order_by(LyWarehouseStockEntryDraft.created_at.desc(), LyWarehouseStockEntryDraft.id.desc())
            .offset(max(page - 1, 0) * page_size)
            .limit(page_size)
            .all()
        )
        return WarehouseStockEntryDraftListData(
            items=[self._build_draft_data(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def cancel_stock_entry_draft(
        self,
        *,
        draft_id: int,
        reason: str,
        cancelled_by: str,
    ) -> WarehouseStockEntryDraftData:
        session = self._require_session()
        draft = (
            session.query(LyWarehouseStockEntryDraft)
            .filter(LyWarehouseStockEntryDraft.id == draft_id)
            .first()
        )
        if draft is None:
            raise WarehouseServiceError(404, "WAREHOUSE_DRAFT_NOT_FOUND", "草稿不存在")

        if str(draft.status) == "cancelled":
            raise WarehouseServiceError(409, "WAREHOUSE_DRAFT_ALREADY_CANCELLED", "草稿已取消")
        if str(draft.status) not in {"draft", "pending_outbox"}:
            raise WarehouseServiceError(409, "WAREHOUSE_INVALID_STATUS", "当前状态不允许取消")

        events = (
            session.query(LyWarehouseStockEntryOutboxEvent)
            .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
            .all()
        )
        if any(str(event.status) == "succeeded" for event in events):
            raise WarehouseServiceError(409, "WAREHOUSE_INVALID_STATUS", "已同步成功的入库草稿不可直接取消")

        if str(draft.source_type) == MaterialPurchaseService.PURCHASE_SOURCE_TYPE and str(draft.purpose) == "Material Receipt":
            self._reverse_material_purchase_receipt(
                company=str(draft.company),
                source_id=str(draft.source_id),
                items=self._draft_purchase_receipt_rows(draft_id=draft_id),
            )

        now = datetime.now(timezone.utc)
        draft.status = "cancelled"
        draft.cancelled_by = cancelled_by
        draft.cancelled_at = now
        draft.cancel_reason = self._require_text(reason, "reason")

        for event in events:
            if str(event.status) in {"in_pending", "processing", "failed"}:
                event.status = "cancelled"
                event.processed_at = now

        session.flush()
        return self._build_draft_data(draft)

    def get_stock_entry_draft(self, *, draft_id: int) -> WarehouseStockEntryDraftData:
        draft = self._find_draft(draft_id=draft_id)
        if draft is None:
            raise WarehouseServiceError(404, "WAREHOUSE_DRAFT_NOT_FOUND", "草稿不存在")
        return self._build_draft_data(draft)

    def get_stock_entry_outbox_status(self, *, draft_id: int) -> WarehouseStockEntryOutboxStatusData:
        draft = self._find_draft(draft_id=draft_id)
        if draft is None:
            raise WarehouseServiceError(404, "WAREHOUSE_DRAFT_NOT_FOUND", "草稿不存在")
        outbox = self._latest_outbox_for_draft(int(draft.id))
        if outbox is None:
            raise WarehouseServiceError(404, "WAREHOUSE_OUTBOX_NOT_FOUND", "outbox 事件不存在")
        return self._build_outbox_status(outbox=outbox)

    def run_stock_entry_outbox_once(
        self,
        *,
        batch_size: int,
        dry_run: bool,
    ) -> WarehouseStockEntryWorkerRunOnceData:
        if dry_run:
            due_count = len(self._list_due_stock_entry_outbox(batch_size=batch_size))
            return WarehouseStockEntryWorkerRunOnceData(
                dry_run=True,
                processed_count=due_count,
                skipped_count=0,
                succeeded_count=0,
                failed_count=0,
                dead_count=0,
            )

        claims = self._list_due_stock_entry_outbox(batch_size=batch_size)
        skipped = 0
        succeeded = 0
        failed = 0
        dead = 0
        for claim in claims:
            outbox = (
                self._require_session()
                .query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.id == claim.outbox_id)
                .first()
            )
            if outbox is None:
                continue
            draft = self._find_draft(draft_id=claim.draft_id)
            if draft is None or str(draft.status) == "cancelled":
                outbox.status = "cancelled"
                outbox.error_message = "draft cancelled or missing"
                outbox.processed_at = datetime.now(timezone.utc)
                skipped += 1
                continue

            outbox.status = "processing"
            outbox.retry_count = int(outbox.retry_count or 0) + 1
            outbox.error_message = None
            outbox.processed_at = None
            self._require_session().flush()

            try:
                stock_entry_name = self._require_adapter().create_stock_entry_draft_from_outbox(
                    event_key=claim.event_key,
                    payload_json=claim.payload,
                )
                outbox.status = "succeeded"
                outbox.external_ref = self._text(stock_entry_name)
                outbox.error_message = None
                outbox.processed_at = datetime.now(timezone.utc)
                succeeded += 1
            except AppException as exc:
                next_status = "dead" if int(outbox.retry_count or 0) >= 3 else "failed"
                outbox.status = next_status
                outbox.error_message = self._text(exc.message) or self._text(exc.code) or "worker failed"
                outbox.processed_at = datetime.now(timezone.utc)
                failed += 1
                if next_status == "dead":
                    dead += 1
            except Exception as exc:  # pragma: no cover - defensive fallback
                wrapped = BusinessException(code=INTERNAL_ERROR, message="仓库 outbox worker 内部错误")
                next_status = "dead" if int(outbox.retry_count or 0) >= 3 else "failed"
                outbox.status = next_status
                outbox.error_message = self._text(wrapped.message) or str(exc)
                outbox.processed_at = datetime.now(timezone.utc)
                failed += 1
                if next_status == "dead":
                    dead += 1

        return WarehouseStockEntryWorkerRunOnceData(
            dry_run=False,
            processed_count=len(claims),
            skipped_count=skipped,
            succeeded_count=succeeded,
            failed_count=failed,
            dead_count=dead,
        )

    def create_inventory_count(
        self,
        *,
        payload: WarehouseInventoryCountCreateRequest,
        current_user: str,
    ) -> WarehouseInventoryCountData:
        session = self._require_session()
        company = self._require_text(payload.company, "company")
        warehouse = self._require_text(payload.warehouse, "warehouse")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        source_ref = self._require_text(payload.source_ref, "source_ref")
        item_rows = self._normalize_inventory_count_items(items=payload.items)
        item_rows = self._apply_inventory_count_book_balances(
            company=company,
            warehouse=warehouse,
            item_rows=item_rows,
        )
        remark = self._text(payload.remark)
        request_hash = self._inventory_count_request_hash(
            company=company,
            warehouse=warehouse,
            count_date=payload.count_date,
            source_ref=source_ref,
            remark=remark,
            item_rows=item_rows,
        )
        existing = self._find_inventory_count_create_replay(
            company=company,
            idempotency_key=idempotency_key,
            source_ref=source_ref,
            request_hash=request_hash,
        )
        if existing is not None:
            return self._build_inventory_count_data(inventory_count=existing)

        count_no = self._build_inventory_count_no(
            company=company,
            warehouse=warehouse,
            count_date=payload.count_date,
            source_ref=source_ref,
        )
        now = datetime.now(timezone.utc)
        carrier_remark = f"carrier:idempotency_key={idempotency_key};source_ref={source_ref}"
        combined_remark = carrier_remark if remark is None else f"{remark} | {carrier_remark}"

        inventory_count = LyWarehouseInventoryCount(
            company=company,
            warehouse=warehouse,
            status="draft",
            count_no=count_no,
            idempotency_key=idempotency_key,
            source_ref=source_ref,
            request_hash=request_hash,
            count_date=payload.count_date,
            created_by=current_user,
            created_at=now,
            remark=combined_remark,
        )
        session.add(inventory_count)
        session.flush()

        for row in item_rows:
            session.add(
                LyWarehouseInventoryCountItem(
                    count_id=inventory_count.id,
                    company=company,
                    warehouse=warehouse,
                    item_code=row["item_code"],
                    batch_no=row["batch_no"],
                    serial_no=row["serial_no"],
                    system_qty=row["system_qty"],
                    counted_qty=row["counted_qty"],
                    variance_qty=row["variance_qty"],
                    variance_reason=row["variance_reason"],
                    review_status=row["review_status"],
                )
            )
        session.flush()
        return self._build_inventory_count_data(inventory_count=inventory_count)

    def recover_inventory_count_create_replay(
        self,
        *,
        payload: WarehouseInventoryCountCreateRequest,
    ) -> WarehouseInventoryCountData | None:
        company = self._require_text(payload.company, "company")
        warehouse = self._require_text(payload.warehouse, "warehouse")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        source_ref = self._require_text(payload.source_ref, "source_ref")
        item_rows = self._normalize_inventory_count_items(items=payload.items)
        item_rows = self._apply_inventory_count_book_balances(
            company=company,
            warehouse=warehouse,
            item_rows=item_rows,
        )
        remark = self._text(payload.remark)
        request_hash = self._inventory_count_request_hash(
            company=company,
            warehouse=warehouse,
            count_date=payload.count_date,
            source_ref=source_ref,
            remark=remark,
            item_rows=item_rows,
        )
        existing = self._find_inventory_count_create_replay(
            company=company,
            idempotency_key=idempotency_key,
            source_ref=source_ref,
            request_hash=request_hash,
        )
        if existing is None:
            return None
        return self._build_inventory_count_data(inventory_count=existing)

    def submit_inventory_count(
        self,
        *,
        count_id: int,
        submitted_by: str,
    ) -> WarehouseInventoryCountData:
        session = self._require_session()
        inventory_count = self._find_inventory_count(count_id=count_id)
        if inventory_count is None:
            raise WarehouseServiceError(404, "WAREHOUSE_INVENTORY_COUNT_NOT_FOUND", "盘点单不存在")

        status = str(inventory_count.status)
        if status == "cancelled":
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_CANCELLED", "盘点单已取消")
        if status == "confirmed":
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_CONFIRMED", "盘点单已确认")
        if status != "draft":
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_INVALID_STATUS", "当前状态不允许提交")

        now = datetime.now(timezone.utc)
        inventory_count.status = "counted"
        inventory_count.submitted_by = submitted_by
        inventory_count.submitted_at = now
        session.flush()
        return self._build_inventory_count_data(inventory_count=inventory_count)

    def variance_review_inventory_count(
        self,
        *,
        count_id: int,
        payload: WarehouseInventoryCountVarianceReviewRequest | None,
        reviewed_by: str,
    ) -> WarehouseInventoryCountData:
        session = self._require_session()
        inventory_count = self._find_inventory_count(count_id=count_id)
        if inventory_count is None:
            raise WarehouseServiceError(404, "WAREHOUSE_INVENTORY_COUNT_NOT_FOUND", "盘点单不存在")

        status = str(inventory_count.status)
        if status not in {"counted", "variance_review"}:
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_INVALID_STATUS", "当前状态不允许差异复核")

        variance_items = self._variance_items_for_count(count_id=count_id)
        if not variance_items:
            raise WarehouseServiceError(400, "WAREHOUSE_VARIANCE_NOT_FOUND", "当前盘点单不存在差异行，无需差异复核")

        if status == "counted":
            inventory_count.status = "variance_review"

        if payload is not None:
            item_map = {int(item.id): item for item in variance_items}
            for review in payload.items:
                target = item_map.get(int(review.item_id))
                if target is None:
                    raise WarehouseServiceError(400, "WAREHOUSE_REVIEW_ITEM_NOT_FOUND", "差异复核项不存在")
                target.review_status = review.review_status
                if review.variance_reason is not None:
                    target.variance_reason = self._text(review.variance_reason)

        now = datetime.now(timezone.utc)
        inventory_count.reviewed_by = reviewed_by
        inventory_count.reviewed_at = now
        session.flush()
        return self._build_inventory_count_data(inventory_count=inventory_count)

    def confirm_inventory_count(
        self,
        *,
        count_id: int,
        confirmed_by: str,
    ) -> WarehouseInventoryCountData:
        session = self._require_session()
        inventory_count = self._find_inventory_count(count_id=count_id)
        if inventory_count is None:
            raise WarehouseServiceError(404, "WAREHOUSE_INVENTORY_COUNT_NOT_FOUND", "盘点单不存在")
        status = str(inventory_count.status)
        if status == "confirmed":
            return self._build_inventory_count_data(inventory_count=inventory_count)
        if status not in {"counted", "variance_review"}:
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_INVALID_STATUS", "当前状态不允许确认")

        variance_items = self._variance_items_for_count(count_id=count_id)
        unresolved = [item for item in variance_items if str(item.review_status) == "pending"]
        if unresolved:
            raise WarehouseServiceError(409, "WAREHOUSE_VARIANCE_REVIEW_PENDING", "存在未复核差异行，无法确认")

        self._create_inventory_count_adjustments(
            inventory_count=inventory_count,
            variance_items=variance_items,
            confirmed_by=confirmed_by,
        )

        now = datetime.now(timezone.utc)
        inventory_count.status = "confirmed"
        if self._text(inventory_count.reviewed_by) is None:
            inventory_count.reviewed_by = confirmed_by
        if inventory_count.reviewed_at is None:
            inventory_count.reviewed_at = now
        session.flush()
        return self._build_inventory_count_data(inventory_count=inventory_count)

    def cancel_inventory_count(
        self,
        *,
        count_id: int,
        reason: str,
        cancelled_by: str,
    ) -> WarehouseInventoryCountData:
        session = self._require_session()
        inventory_count = self._find_inventory_count(count_id=count_id)
        if inventory_count is None:
            raise WarehouseServiceError(404, "WAREHOUSE_INVENTORY_COUNT_NOT_FOUND", "盘点单不存在")

        status = str(inventory_count.status)
        if status == "cancelled":
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_ALREADY_CANCELLED", "盘点单已取消")
        if status not in self._INVENTORY_ACTIVE_STATUSES and status != "confirmed":
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_INVALID_STATUS", "当前状态不允许取消")

        inventory_count.status = "cancelled"
        inventory_count.cancel_reason = self._require_text(reason, "reason")
        inventory_count.cancelled_by = cancelled_by
        inventory_count.cancelled_at = datetime.now(timezone.utc)
        session.flush()
        return self._build_inventory_count_data(inventory_count=inventory_count)

    def get_inventory_count(self, *, count_id: int) -> WarehouseInventoryCountData:
        inventory_count = self._find_inventory_count(count_id=count_id)
        if inventory_count is None:
            raise WarehouseServiceError(404, "WAREHOUSE_INVENTORY_COUNT_NOT_FOUND", "盘点单不存在")
        return self._build_inventory_count_data(inventory_count=inventory_count)

    def list_inventory_counts(
        self,
        *,
        company: str | None,
        warehouse: str | None,
        status: str | None,
        from_date: date | None,
        to_date: date | None,
        item_code: str | None,
    ) -> WarehouseInventoryCountListData:
        query = self._require_session().query(LyWarehouseInventoryCount)
        normalized_company = self._text(company)
        normalized_warehouse = self._text(warehouse)
        normalized_status = self._text(status)
        normalized_item_code = self._text(item_code)

        if normalized_company is not None:
            query = query.filter(LyWarehouseInventoryCount.company == normalized_company)
        if normalized_warehouse is not None:
            query = query.filter(LyWarehouseInventoryCount.warehouse == normalized_warehouse)
        if normalized_status is not None:
            query = query.filter(LyWarehouseInventoryCount.status == normalized_status)
        if from_date is not None:
            query = query.filter(LyWarehouseInventoryCount.count_date >= from_date)
        if to_date is not None:
            query = query.filter(LyWarehouseInventoryCount.count_date <= to_date)
        if normalized_item_code is not None:
            subquery = (
                self._require_session()
                .query(LyWarehouseInventoryCountItem.count_id)
                .filter(LyWarehouseInventoryCountItem.item_code == normalized_item_code)
                .distinct()
            )
            query = query.filter(LyWarehouseInventoryCount.id.in_(subquery))

        rows = query.order_by(LyWarehouseInventoryCount.count_date.desc(), LyWarehouseInventoryCount.id.desc()).all()
        return WarehouseInventoryCountListData(
            total=len(rows),
            items=[self._build_inventory_count_data(inventory_count=row) for row in rows],
        )

    def _find_draft(self, *, draft_id: int) -> LyWarehouseStockEntryDraft | None:
        return (
            self._require_session()
            .query(LyWarehouseStockEntryDraft)
            .filter(LyWarehouseStockEntryDraft.id == draft_id)
            .first()
        )

    def _build_draft_data(self, draft: LyWarehouseStockEntryDraft) -> WarehouseStockEntryDraftData:
        session = self._require_session()
        draft_id = int(draft.id)
        items = (
            session.query(LyWarehouseStockEntryDraftItem)
            .filter(LyWarehouseStockEntryDraftItem.draft_id == draft_id)
            .order_by(LyWarehouseStockEntryDraftItem.id.asc())
            .all()
        )
        outbox = self._latest_outbox_for_draft(draft_id)
        allocation_mode: str | None = None
        strict_failure_reason: str | None = None
        show_completed_forced: bool | None = None
        if outbox is not None and isinstance(outbox.payload, dict):
            payload = outbox.payload
            candidate_mode = self._text(payload.get("allocation_mode"))
            if candidate_mode in {"strict_alloc", "zero_placeholder_fallback"}:
                allocation_mode = candidate_mode
            strict_failure_reason = self._text(payload.get("strict_failure_reason"))
            raw_show_completed = payload.get("show_completed_forced")
            if isinstance(raw_show_completed, bool):
                show_completed_forced = raw_show_completed

        return WarehouseStockEntryDraftData(
            id=draft_id,
            company=str(draft.company),
            purpose=str(draft.purpose),
            source_type=str(draft.source_type),
            source_id=str(draft.source_id),
            source_ref=str(draft.source_id),
            source_warehouse=self._text(draft.source_warehouse),
            target_warehouse=self._text(draft.target_warehouse),
            status=str(draft.status),
            created_by=str(draft.created_by),
            created_at=draft.created_at,
            cancelled_by=self._text(draft.cancelled_by),
            cancelled_at=draft.cancelled_at,
            cancel_reason=self._text(draft.cancel_reason),
            idempotency_key=str(draft.idempotency_key),
            event_key=str(draft.event_key),
            allocation_mode=allocation_mode,
            strict_failure_reason=strict_failure_reason,
            show_completed_forced=show_completed_forced,
            items=[
                WarehouseStockEntryDraftItemData(
                    id=int(item.id),
                    draft_id=int(item.draft_id),
                    item_code=str(item.item_code),
                    qty=Decimal(str(item.qty)),
                    uom=str(item.uom),
                    batch_no=self._text(item.batch_no),
                    serial_no=self._text(item.serial_no),
                    source_warehouse=self._text(item.source_warehouse),
                    target_warehouse=self._text(item.target_warehouse),
                )
                for item in items
            ],
            outbox=self._build_outbox_status(outbox=outbox) if outbox is not None else None,
        )

    def _apply_material_purchase_receipt(
        self,
        *,
        company: str,
        source_id: str,
        items: list[dict[str, Any]],
    ) -> None:
        try:
            MaterialPurchaseService(self.session).apply_receipt_rows(
                company=company,
                purchase_no=self._purchase_no_from_source_id(source_id) or source_id,
                items=self._material_purchase_receipt_rows(items),
            )
        except BusinessException as exc:
            raise WarehouseServiceError(exc.status_code, exc.code, exc.message) from exc

    def _validate_material_purchase_receipt(
        self,
        *,
        company: str,
        source_id: str,
        items: list[dict[str, Any]],
    ) -> None:
        try:
            MaterialPurchaseService(self.session).validate_receipt_rows(
                company=company,
                purchase_no=self._purchase_no_from_source_id(source_id) or source_id,
                items=self._material_purchase_receipt_rows(items),
            )
        except BusinessException as exc:
            raise WarehouseServiceError(exc.status_code, exc.code, exc.message) from exc

    def _reverse_material_purchase_receipt(
        self,
        *,
        company: str,
        source_id: str,
        items: list[dict[str, Any]],
    ) -> None:
        try:
            MaterialPurchaseService(self.session).reverse_receipt_rows(
                company=company,
                purchase_no=self._purchase_no_from_source_id(source_id) or source_id,
                items=self._material_purchase_receipt_rows(items),
            )
        except BusinessException as exc:
            raise WarehouseServiceError(exc.status_code, exc.code, exc.message) from exc

    def _draft_purchase_receipt_rows(self, *, draft_id: int) -> list[dict[str, Any]]:
        items = (
            self._require_session()
            .query(LyWarehouseStockEntryDraftItem)
            .filter(LyWarehouseStockEntryDraftItem.draft_id == draft_id)
            .order_by(LyWarehouseStockEntryDraftItem.id.asc())
            .all()
        )
        return [
            {
                "item_code": str(item.item_code),
                "qty": Decimal(str(item.qty or 0)),
                "target_warehouse": self._text(item.target_warehouse),
                "source_warehouse": self._text(item.source_warehouse),
            }
            for item in items
        ]

    def _material_purchase_receipt_rows(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "item_code": str(item["item_code"]).strip(),
                "qty": Decimal(str(item["qty"])),
                "warehouse": self._text(item.get("target_warehouse")) or self._text(item.get("warehouse")),
            }
            for item in items
        ]

    def _latest_outbox_for_draft(self, draft_id: int) -> LyWarehouseStockEntryOutboxEvent | None:
        return (
            self._require_session()
            .query(LyWarehouseStockEntryOutboxEvent)
            .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
            .order_by(LyWarehouseStockEntryOutboxEvent.id.desc())
            .first()
        )

    def _ensure_stock_entry_replay_matches(
        self,
        draft: LyWarehouseStockEntryDraft,
        *,
        expected_payload: dict[str, Any],
        message: str,
    ) -> None:
        outbox = self._latest_outbox_for_draft(int(draft.id))
        if outbox is None or not isinstance(outbox.payload, dict):
            return
        replay_payload = dict(outbox.payload)
        replay_payload.pop("draft_id", None)
        if replay_payload != expected_payload:
            raise WarehouseServiceError(409, "WAREHOUSE_IDEMPOTENCY_CONFLICT", message)

    def _build_stock_entry_replay_payload(
        self,
        *,
        company: str,
        purpose: str,
        source_type: str,
        source_id: str,
        business_date: date,
        source_warehouse: str | None,
        target_warehouse: str | None,
        item_rows: list[dict[str, Any]],
        allocation_mode: str | None,
        strict_failure_reason: str | None,
        show_completed_forced: bool | None,
        finished_goods_source_id: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "company": company,
            "purpose": purpose,
            "source_type": source_type,
            "source_id": source_id,
            "business_date": business_date.isoformat(),
            "source_warehouse": source_warehouse,
            "target_warehouse": target_warehouse,
            "items": [
                {
                    "item_code": row["item_code"],
                    "qty": str(row["qty"]),
                    "uom": row["uom"],
                    "batch_no": row.get("batch_no"),
                    "serial_no": row.get("serial_no"),
                    "source_warehouse": row.get("source_warehouse"),
                    "target_warehouse": row.get("target_warehouse"),
                }
                for row in item_rows
            ],
        }
        if allocation_mode is not None:
            payload["allocation_mode"] = allocation_mode
        if strict_failure_reason is not None:
            payload["strict_failure_reason"] = strict_failure_reason
        if show_completed_forced is not None:
            payload["show_completed_forced"] = show_completed_forced
        if finished_goods_source_id is not None:
            payload["finished_goods_source_id"] = finished_goods_source_id
            payload["disabled_entry_label"] = self._FINISHED_GOODS_DISABLED_ENTRY_LABEL
            payload["disabled_entry_reason"] = self._FINISHED_GOODS_DISABLED_ENTRY_REASON
        return payload

    def _list_due_stock_entry_outbox(self, *, batch_size: int) -> list[WarehouseStockEntryOutboxClaim]:
        rows = (
            self._require_session()
            .query(LyWarehouseStockEntryOutboxEvent)
            .filter(LyWarehouseStockEntryOutboxEvent.status.in_(["in_pending", "failed"]))
            .order_by(LyWarehouseStockEntryOutboxEvent.id.asc())
            .limit(max(1, int(batch_size)))
            .all()
        )
        claims: list[WarehouseStockEntryOutboxClaim] = []
        for row in rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            claims.append(
                WarehouseStockEntryOutboxClaim(
                    outbox_id=int(row.id),
                    draft_id=int(row.draft_id),
                    event_key=str(row.event_key),
                    payload=dict(payload),
                )
            )
        return claims

    def _find_inventory_count(self, *, count_id: int) -> LyWarehouseInventoryCount | None:
        return (
            self._require_session()
            .query(LyWarehouseInventoryCount)
            .filter(LyWarehouseInventoryCount.id == count_id)
            .first()
        )

    def _inventory_count_items(self, *, count_id: int) -> list[LyWarehouseInventoryCountItem]:
        return (
            self._require_session()
            .query(LyWarehouseInventoryCountItem)
            .filter(LyWarehouseInventoryCountItem.count_id == count_id)
            .order_by(LyWarehouseInventoryCountItem.id.asc())
            .all()
        )

    def _variance_items_for_count(self, *, count_id: int) -> list[LyWarehouseInventoryCountItem]:
        return (
            self._require_session()
            .query(LyWarehouseInventoryCountItem)
            .filter(
                LyWarehouseInventoryCountItem.count_id == count_id,
                LyWarehouseInventoryCountItem.variance_qty != Decimal("0"),
            )
            .order_by(LyWarehouseInventoryCountItem.id.asc())
            .all()
        )

    def _build_inventory_count_data(self, *, inventory_count: LyWarehouseInventoryCount) -> WarehouseInventoryCountData:
        count_id = int(inventory_count.id)
        item_rows = self._inventory_count_items(count_id=count_id)
        variance_items = [row for row in item_rows if Decimal(str(row.variance_qty)) != Decimal("0")]
        pending_review = [row for row in variance_items if str(row.review_status) == "pending"]
        accepted_review = [row for row in variance_items if str(row.review_status) == "accepted"]
        rejected_review = [row for row in variance_items if str(row.review_status) == "rejected"]

        variance_stats = WarehouseInventoryCountVarianceStatsData(
            total_items=len(item_rows),
            variance_items=len(variance_items),
            pending_review_items=len(pending_review),
            accepted_items=len(accepted_review),
            rejected_items=len(rejected_review),
        )
        return WarehouseInventoryCountData(
            id=count_id,
            company=str(inventory_count.company),
            warehouse=str(inventory_count.warehouse),
            status=str(inventory_count.status),
            count_no=str(inventory_count.count_no),
            idempotency_key=self._text(inventory_count.idempotency_key),
            source_ref=self._text(inventory_count.source_ref),
            request_hash=self._text(inventory_count.request_hash),
            count_date=inventory_count.count_date,
            created_by=str(inventory_count.created_by),
            created_at=inventory_count.created_at,
            submitted_by=self._text(inventory_count.submitted_by),
            submitted_at=inventory_count.submitted_at,
            reviewed_by=self._text(inventory_count.reviewed_by),
            reviewed_at=inventory_count.reviewed_at,
            cancelled_by=self._text(inventory_count.cancelled_by),
            cancelled_at=inventory_count.cancelled_at,
            cancel_reason=self._text(inventory_count.cancel_reason),
            remark=self._text(inventory_count.remark),
            items=[
                WarehouseInventoryCountItemData(
                    id=int(item.id),
                    count_id=int(item.count_id),
                    item_code=str(item.item_code),
                    batch_no=self._text(item.batch_no),
                    serial_no=self._text(item.serial_no),
                    system_qty=Decimal(str(item.system_qty)),
                    counted_qty=Decimal(str(item.counted_qty)),
                    variance_qty=Decimal(str(item.variance_qty)),
                    variance_reason=self._text(item.variance_reason),
                    review_status=str(item.review_status),
                )
                for item in item_rows
            ],
            variance_stats=variance_stats,
        )

    @staticmethod
    def _build_outbox_status(*, outbox: LyWarehouseStockEntryOutboxEvent) -> WarehouseStockEntryOutboxStatusData:
        return WarehouseStockEntryOutboxStatusData(
            draft_id=int(outbox.draft_id),
            event_id=int(outbox.id),
            event_type=str(outbox.event_type),
            status=str(outbox.status),
            retry_count=int(outbox.retry_count),
            external_ref=WarehouseService._text(outbox.external_ref),
            error_message=WarehouseService._text(outbox.error_message),
            created_at=outbox.created_at,
            processed_at=outbox.processed_at,
        )

    def _normalize_inventory_count_items(
        self,
        *,
        items: list[WarehouseInventoryCountItemCreateRequest],
    ) -> list[dict[str, Any]]:
        if not items:
            raise WarehouseServiceError(400, "WAREHOUSE_ITEMS_REQUIRED", "items 不能为空")

        normalized_rows: list[dict[str, Any]] = []
        for idx, item in enumerate(items, start=1):
            item_code = self._require_text(item.item_code, f"items[{idx}].item_code")
            try:
                system_qty = Decimal(str(item.system_qty))
                counted_qty = Decimal(str(item.counted_qty))
            except Exception as exc:
                raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"items[{idx}] 数量非法") from exc
            if system_qty < 0:
                raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"items[{idx}].system_qty 不得小于 0")
            if counted_qty < 0:
                raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"items[{idx}].counted_qty 不得小于 0")
            variance_qty = counted_qty - system_qty
            variance_reason = self._text(item.variance_reason)

            normalized_rows.append(
                {
                    "item_code": item_code,
                    "batch_no": self._text(item.batch_no),
                    "serial_no": self._text(item.serial_no),
                    "system_qty": system_qty,
                    "counted_qty": counted_qty,
                    "variance_qty": variance_qty,
                    "variance_reason": variance_reason,
                    "review_status": "pending" if variance_qty != Decimal("0") else "accepted",
                }
            )
        return normalized_rows

    def _apply_inventory_count_book_balances(
        self,
        *,
        company: str,
        warehouse: str,
        item_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        item_codes = {str(row["item_code"]) for row in item_rows}
        book_balances: dict[str, Decimal] = {}
        for item_code in item_codes:
            balance_map = self._local_stock_balance_map(company=company, warehouse=warehouse, item_code=item_code)
            book_qty = balance_map.get((company, warehouse, item_code), Decimal("0"))
            if book_qty < 0:
                raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"{item_code} 账面库存不得小于 0")
            book_balances[item_code] = book_qty

        normalized_rows: list[dict[str, Any]] = []
        for idx, row in enumerate(item_rows, start=1):
            adjusted = dict(row)
            item_code = str(adjusted["item_code"])
            system_qty = book_balances.get(item_code, Decimal("0"))
            counted_qty = Decimal(str(adjusted["counted_qty"]))
            variance_qty = counted_qty - system_qty
            variance_reason = self._text(adjusted.get("variance_reason"))
            if variance_qty != Decimal("0") and variance_reason is None:
                raise WarehouseServiceError(
                    400,
                    "WAREHOUSE_VARIANCE_REASON_REQUIRED",
                    f"items[{idx}] 存在差异时 variance_reason 必填",
                )
            adjusted["system_qty"] = system_qty
            adjusted["variance_qty"] = variance_qty
            adjusted["variance_reason"] = variance_reason
            adjusted["review_status"] = "pending" if variance_qty != Decimal("0") else "accepted"
            normalized_rows.append(adjusted)
        return normalized_rows

    def _create_inventory_count_adjustments(
        self,
        *,
        inventory_count: LyWarehouseInventoryCount,
        variance_items: list[LyWarehouseInventoryCountItem],
        confirmed_by: str,
    ) -> None:
        session = self._require_session()
        company = str(inventory_count.company)
        warehouse = str(inventory_count.warehouse)
        posting_at = datetime.combine(inventory_count.count_date, datetime.min.time(), timezone.utc)

        for line in variance_items:
            if str(line.review_status) != "accepted":
                continue
            item_code = str(line.item_code)
            balance_map = self._local_stock_balance_map(company=company, warehouse=warehouse, item_code=item_code)
            book_qty = balance_map.get((company, warehouse, item_code), Decimal("0"))
            diff_qty = Decimal(str(line.counted_qty)) - book_qty
            if diff_qty == Decimal("0"):
                continue

            source_id = f"inventory_count:{inventory_count.id}:item:{line.id}"
            existing = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(
                    LyWarehouseStockEntryDraft.company == company,
                    LyWarehouseStockEntryDraft.source_type == "inventory_count_adjustment",
                    LyWarehouseStockEntryDraft.source_id == source_id,
                    LyWarehouseStockEntryDraft.status != "cancelled",
                )
                .first()
            )
            if existing is not None:
                continue

            purpose = "Material Receipt" if diff_qty > 0 else "Material Issue"
            qty = abs(diff_qty)
            source_warehouse = warehouse if diff_qty < 0 else None
            target_warehouse = warehouse if diff_qty > 0 else None
            uom = self._inventory_count_adjustment_uom(company=company, warehouse=warehouse, item_code=item_code)
            idempotency_key = f"inv-count-adj-{inventory_count.id}-{line.id}"
            event_key = self._build_event_key(
                company=company,
                source_type="inventory_count_adjustment",
                source_id=source_id,
                idempotency_key=idempotency_key,
            )
            draft = LyWarehouseStockEntryDraft(
                company=company,
                purpose=purpose,
                source_type="inventory_count_adjustment",
                source_id=source_id,
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
                status="pending_outbox",
                created_by=confirmed_by,
                created_at=posting_at,
                idempotency_key=idempotency_key,
                event_key=event_key,
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=draft.id,
                    company=company,
                    item_code=item_code,
                    qty=qty,
                    uom=uom,
                    batch_no=self._text(line.batch_no),
                    serial_no=self._text(line.serial_no),
                    source_warehouse=source_warehouse,
                    target_warehouse=target_warehouse,
                )
            )
            session.add(
                LyWarehouseStockEntryOutboxEvent(
                    draft_id=draft.id,
                    event_type="warehouse_stock_entry_sync",
                    event_key=event_key,
                    payload={
                        "draft_id": int(draft.id),
                        "company": company,
                        "purpose": purpose,
                        "source_type": "inventory_count_adjustment",
                        "source_id": source_id,
                        "business_date": inventory_count.count_date.isoformat(),
                        "source_warehouse": source_warehouse,
                        "target_warehouse": target_warehouse,
                        "items": [
                            {
                                "item_code": item_code,
                                "qty": str(qty),
                                "uom": uom,
                                "batch_no": self._text(line.batch_no),
                                "serial_no": self._text(line.serial_no),
                                "source_warehouse": source_warehouse,
                                "target_warehouse": target_warehouse,
                            }
                        ],
                    },
                    status="in_pending",
                    retry_count=0,
                    created_at=posting_at,
                )
            )

    def _inventory_count_adjustment_uom(self, *, company: str, warehouse: str, item_code: str) -> str:
        session = self._require_session()
        row = (
            session.query(LyWarehouseStockEntryDraftItem)
            .join(
                LyWarehouseStockEntryDraft,
                LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id,
            )
            .filter(
                LyWarehouseStockEntryDraft.company == company,
                LyWarehouseStockEntryDraft.status != "cancelled",
                LyWarehouseStockEntryDraftItem.item_code == item_code,
                (
                    (LyWarehouseStockEntryDraftItem.source_warehouse == warehouse)
                    | (LyWarehouseStockEntryDraftItem.target_warehouse == warehouse)
                    | (LyWarehouseStockEntryDraft.source_warehouse == warehouse)
                    | (LyWarehouseStockEntryDraft.target_warehouse == warehouse)
                ),
            )
            .order_by(LyWarehouseStockEntryDraft.created_at.desc(), LyWarehouseStockEntryDraftItem.id.desc())
            .first()
        )
        if row is None:
            raise WarehouseServiceError(400, "WAREHOUSE_UOM_NOT_FOUND", f"{item_code} 缺少本地库存单位，无法生成盘点调整")
        uom = self._text(row.uom)
        if uom is None:
            raise WarehouseServiceError(400, "WAREHOUSE_UOM_NOT_FOUND", f"{item_code} 缺少本地库存单位，无法生成盘点调整")
        return uom

    @staticmethod
    def _ensure_inventory_count_replay_matches(
        inventory_count: LyWarehouseInventoryCount,
        *,
        idempotency_key: str,
        source_ref: str,
        request_hash: str,
        message: str,
    ) -> None:
        if str(inventory_count.idempotency_key or "") != idempotency_key:
            raise WarehouseServiceError(409, "WAREHOUSE_IDEMPOTENCY_CONFLICT", message)
        if str(inventory_count.source_ref or "") != source_ref:
            raise WarehouseServiceError(409, "WAREHOUSE_IDEMPOTENCY_CONFLICT", message)
        if str(inventory_count.request_hash or "") != request_hash:
            raise WarehouseServiceError(409, "WAREHOUSE_IDEMPOTENCY_CONFLICT", message)

    def _find_inventory_count_create_replay(
        self,
        *,
        company: str,
        idempotency_key: str,
        source_ref: str,
        request_hash: str,
    ) -> LyWarehouseInventoryCount | None:
        session = self._require_session()
        existing_by_idempotency = (
            session.query(LyWarehouseInventoryCount)
            .filter(
                LyWarehouseInventoryCount.company == company,
                LyWarehouseInventoryCount.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_by_idempotency is not None:
            self._ensure_inventory_count_replay_matches(
                existing_by_idempotency,
                idempotency_key=idempotency_key,
                source_ref=source_ref,
                request_hash=request_hash,
                message="幂等键冲突且请求内容不一致",
            )
            return existing_by_idempotency

        existing_by_source = (
            session.query(LyWarehouseInventoryCount)
            .filter(
                LyWarehouseInventoryCount.company == company,
                LyWarehouseInventoryCount.source_ref == source_ref,
            )
            .first()
        )
        if existing_by_source is not None:
            self._ensure_inventory_count_replay_matches(
                existing_by_source,
                idempotency_key=idempotency_key,
                source_ref=source_ref,
                request_hash=request_hash,
                message="source_ref 已存在且请求内容不一致",
            )
            return existing_by_source

        return None

    @staticmethod
    def _inventory_count_request_hash(
        *,
        company: str,
        warehouse: str,
        count_date: date,
        source_ref: str,
        remark: str | None,
        item_rows: list[dict[str, Any]],
    ) -> str:
        canonical_items = [
            {
                "batch_no": row["batch_no"],
                "counted_qty": str(row["counted_qty"]),
                "item_code": row["item_code"],
                "serial_no": row["serial_no"],
                "system_qty": str(row["system_qty"]),
                "variance_reason": row["variance_reason"],
            }
            for row in item_rows
        ]
        canonical_items.sort(
            key=lambda row: (
                str(row["item_code"]),
                str(row["batch_no"] or ""),
                str(row["serial_no"] or ""),
            )
        )
        raw = json.dumps(
            {
                "company": company,
                "warehouse": warehouse,
                "count_date": count_date.isoformat(),
                "source_ref": source_ref,
                "remark": remark,
                "items": canonical_items,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_inventory_count_no(*, company: str, warehouse: str, count_date: date, source_ref: str) -> str:
        raw = (
            f"{company}|{warehouse}|{count_date.isoformat()}|{source_ref}|{datetime.now(timezone.utc).isoformat()}".encode(
                "utf-8",
            )
        )
        digest = hashlib.sha256(raw).hexdigest()[:8].upper()
        normalized_ref = source_ref.strip().replace(" ", "")
        return f"IC-{count_date.strftime('%Y%m%d')}-{digest}-{normalized_ref}"[:140]

    def _normalize_item_payloads(
        self,
        *,
        items: list[WarehouseStockEntryDraftItemCreateRequest],
        fallback_source_warehouse: str | None,
        fallback_target_warehouse: str | None,
    ) -> list[dict[str, Any]]:
        if not items:
            raise WarehouseServiceError(400, "WAREHOUSE_ITEMS_REQUIRED", "items 不能为空")

        normalized_rows: list[dict[str, Any]] = []
        for idx, item in enumerate(items, start=1):
            item_code = self._require_text(item.item_code, f"items[{idx}].item_code")
            uom = self._require_text(item.uom, f"items[{idx}].uom")
            source_warehouse = self._text(item.source_warehouse) or fallback_source_warehouse
            target_warehouse = self._text(item.target_warehouse) or fallback_target_warehouse
            try:
                qty = Decimal(str(item.qty))
            except Exception as exc:
                raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"items[{idx}].qty 非法") from exc
            if qty <= 0:
                raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"items[{idx}].qty 必须大于 0")

            normalized_rows.append(
                {
                    "item_code": item_code,
                    "qty": qty,
                    "uom": uom,
                    "batch_no": self._text(item.batch_no),
                    "serial_no": self._text(item.serial_no),
                    "source_warehouse": source_warehouse,
                    "target_warehouse": target_warehouse,
                }
            )

        return normalized_rows

    def _resolve_finished_goods_item_rows(
        self,
        *,
        company: str,
        source_id: str,
        source_warehouse: str | None,
        target_warehouse: str | None,
        items: list[WarehouseStockEntryDraftItemCreateRequest],
    ) -> tuple[list[dict[str, Any]], str, str | None]:
        item_rows = self._normalize_item_payloads(
            items=items,
            fallback_source_warehouse=source_warehouse,
            fallback_target_warehouse=target_warehouse,
        )
        if len(item_rows) != 1:
            raise WarehouseServiceError(400, "WAREHOUSE_INVALID_PAYLOAD", "成品入仓草稿仅支持单条候选明细")

        try:
            candidate = self._require_adapter().get_finished_goods_inbound_candidate(
                source_id=source_id,
                company=company,
            )
        except ERPNextAdapterException as exc:
            if self._local_read_fallback_enabled():
                return item_rows, "zero_placeholder_fallback", "FastAPI local finished goods inbound source"
            raise WarehouseServiceError(
                int(exc.http_status or 503),
                str(exc.error_code),
                self._text(exc.safe_message) or "成品入仓候选查询失败",
            ) from exc

        if bool(candidate.get("disabled", False)):
            raise WarehouseServiceError(
                400,
                "WAREHOUSE_FINISHED_GOODS_CANDIDATE_DISABLED",
                self._text(candidate.get("disabled_reason")) or self._FINISHED_GOODS_DISABLED_ENTRY_REASON,
            )

        item_row = item_rows[0]
        expected_item_code = self._require_text(candidate.get("item_code"), "candidate.item_code")
        if item_row["item_code"] != expected_item_code:
            raise WarehouseServiceError(
                400,
                "WAREHOUSE_INVALID_PAYLOAD",
                "草稿明细物料与候选物料不一致",
            )

        candidate_qty = self._require_positive_decimal(candidate.get("qty"), field_name="candidate.qty")
        requested_qty = self._require_positive_decimal(item_row.get("qty"), field_name="items[1].qty")
        if requested_qty > candidate_qty:
            raise WarehouseServiceError(
                400,
                "WAREHOUSE_INVALID_QTY",
                "草稿数量超过候选可用数量",
            )

        strict_alloc_qty = self._to_optional_decimal(candidate.get("strict_alloc_qty")) or Decimal("0")
        if strict_alloc_qty >= requested_qty:
            return item_rows, "strict_alloc", None

        strict_failure_reason = self._STRICT_ALLOC_FAILURE_REASON
        if candidate_qty <= Decimal("0"):
            raise WarehouseServiceError(
                400,
                "WAREHOUSE_STRICT_ALLOC_FAILED",
                strict_failure_reason,
            )
        return item_rows, "zero_placeholder_fallback", strict_failure_reason

    def _validate_purpose_warehouses(
        self,
        *,
        purpose: str,
        source_warehouse: str | None,
        target_warehouse: str | None,
    ) -> None:
        if purpose == "Material Issue" and not source_warehouse:
            raise WarehouseServiceError(400, "WAREHOUSE_SOURCE_REQUIRED", "Material Issue 必须提供 source_warehouse")
        if purpose == "Material Receipt" and not target_warehouse:
            raise WarehouseServiceError(400, "WAREHOUSE_TARGET_REQUIRED", "Material Receipt 必须提供 target_warehouse")
        if purpose == "Material Transfer" and (not source_warehouse or not target_warehouse):
            raise WarehouseServiceError(
                400,
                "WAREHOUSE_TRANSFER_WAREHOUSE_REQUIRED",
                "Material Transfer 必须提供 source_warehouse 和 target_warehouse",
            )

    @staticmethod
    def _build_event_key(
        *,
        company: str,
        source_type: str,
        source_id: str,
        idempotency_key: str,
    ) -> str:
        raw = "|".join([company, source_type, source_id, idempotency_key]).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        return f"wse:{digest}"

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _require_adapter(self) -> ERPNextWarehouseAdapter:
        if self.adapter is None:
            self.adapter = ERPNextWarehouseAdapter()
        return self.adapter

    def _require_session(self) -> Session:
        if self.session is None:
            raise RuntimeError("WarehouseService session is required for write APIs")
        return self.session

    def _summary_item(self, row: dict[str, object]) -> WarehouseStockSummaryItem:
        actual_qty = self._to_decimal(row.get("actual_qty"))
        projected_qty = self._to_decimal(row.get("projected_qty"))
        reserved_qty = self._to_decimal(row.get("reserved_qty"))
        ordered_qty = self._to_decimal(row.get("ordered_qty"))
        reorder_level = self._to_optional_decimal(row.get("reorder_level"))
        safety_stock = self._to_optional_decimal(row.get("safety_stock"))
        threshold_missing = reorder_level is None or safety_stock is None

        is_below_reorder = False
        if reorder_level is not None:
            is_below_reorder = actual_qty < reorder_level

        is_below_safety = False
        if safety_stock is not None:
            is_below_safety = actual_qty < safety_stock

        return WarehouseStockSummaryItem(
            company=str(row.get("company") or ""),
            warehouse=str(row.get("warehouse") or ""),
            item_code=str(row.get("item_code") or ""),
            actual_qty=actual_qty,
            projected_qty=projected_qty,
            reserved_qty=reserved_qty,
            ordered_qty=ordered_qty,
            reorder_level=reorder_level,
            safety_stock=safety_stock,
            threshold_missing=threshold_missing,
            is_below_reorder=is_below_reorder,
            is_below_safety=is_below_safety,
        )

    def _alerts_for_summary_item(
        self,
        *,
        item: WarehouseStockSummaryItem,
        last_movement_date: date | None,
        filter_alert_type: str | None,
    ) -> list[WarehouseAlertItem]:
        rows: list[WarehouseAlertItem] = []

        if item.reorder_level is not None and item.actual_qty < item.reorder_level:
            gap = item.reorder_level - item.actual_qty
            rows.append(
                self._build_alert(
                    item=item,
                    alert_type="low_stock",
                    threshold_qty=item.reorder_level,
                    gap_qty=gap,
                    severity="high" if gap > Decimal("0") else "medium",
                    last_movement_date=last_movement_date,
                )
            )

        if item.safety_stock is not None and item.actual_qty < item.safety_stock:
            gap = item.safety_stock - item.actual_qty
            rows.append(
                self._build_alert(
                    item=item,
                    alert_type="below_safety",
                    threshold_qty=item.safety_stock,
                    gap_qty=gap,
                    severity="high" if gap > Decimal("0") else "medium",
                    last_movement_date=last_movement_date,
                )
            )

        overstock_threshold = item.safety_stock if item.safety_stock is not None else item.reorder_level
        if overstock_threshold is not None and overstock_threshold > Decimal("0"):
            limit = overstock_threshold * Decimal("2")
            if item.actual_qty > limit:
                rows.append(
                    self._build_alert(
                        item=item,
                        alert_type="overstock",
                        threshold_qty=limit,
                        gap_qty=item.actual_qty - limit,
                        severity="medium",
                        last_movement_date=last_movement_date,
                    )
                )

        if last_movement_date is not None:
            stale_days = (date.today() - last_movement_date).days
            if stale_days >= 90:
                rows.append(
                    self._build_alert(
                        item=item,
                        alert_type="stale_stock",
                        threshold_qty=None,
                        gap_qty=Decimal(str(stale_days)),
                        severity="medium" if stale_days < 180 else "high",
                        last_movement_date=last_movement_date,
                    )
                )

        if filter_alert_type is None:
            return rows
        return [row for row in rows if row.alert_type == filter_alert_type]

    @staticmethod
    def _build_alert(
        *,
        item: WarehouseStockSummaryItem,
        alert_type: str,
        threshold_qty: Decimal | None,
        gap_qty: Decimal | None,
        severity: str,
        last_movement_date: date | None,
    ) -> WarehouseAlertItem:
        return WarehouseAlertItem(
            company=item.company,
            warehouse=item.warehouse,
            item_code=item.item_code,
            alert_type=alert_type,
            current_qty=item.actual_qty,
            threshold_qty=threshold_qty,
            gap_qty=gap_qty,
            last_movement_date=last_movement_date,
            severity=severity,
        )

    @staticmethod
    def _to_decimal(value: object) -> Decimal:
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _to_optional_decimal(value: object) -> Decimal | None:
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
    def _require_positive_decimal(value: object, *, field_name: str) -> Decimal:
        try:
            number = Decimal(str(value))
        except Exception as exc:
            raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"{field_name} 非法") from exc
        if number <= Decimal("0"):
            raise WarehouseServiceError(400, "WAREHOUSE_INVALID_QTY", f"{field_name} 必须大于 0")
        return number

    @staticmethod
    def _require_text(value: Any, field_name: str) -> str:
        text = WarehouseService._text(value)
        if text is None:
            raise WarehouseServiceError(400, "WAREHOUSE_INVALID_PAYLOAD", f"{field_name} 不能为空")
        return text
