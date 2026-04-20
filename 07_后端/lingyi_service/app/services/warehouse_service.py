"""Warehouse stock read and draft-outbox baseline service (TASK-050B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import hashlib
from typing import Any

from sqlalchemy.orm import Session

from app.core.error_codes import INTERNAL_ERROR
from app.core.exceptions import AppException
from app.core.exceptions import BusinessException
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseInventoryCount
from app.models.warehouse import LyWarehouseInventoryCountItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.schemas.warehouse import WarehouseAlertItem
from app.schemas.warehouse import WarehouseAlertsData
from app.schemas.warehouse import WarehouseBatchDetailData
from app.schemas.warehouse import WarehouseBatchItem
from app.schemas.warehouse import WarehouseBatchListData
from app.schemas.warehouse import WarehouseInventoryCountCreateRequest
from app.schemas.warehouse import WarehouseInventoryCountData
from app.schemas.warehouse import WarehouseInventoryCountItemCreateRequest
from app.schemas.warehouse import WarehouseInventoryCountItemData
from app.schemas.warehouse import WarehouseInventoryCountListData
from app.schemas.warehouse import WarehouseInventoryCountVarianceReviewRequest
from app.schemas.warehouse import WarehouseInventoryCountVarianceStatsData
from app.schemas.warehouse import WarehouseStockEntryDraftCreateRequest
from app.schemas.warehouse import WarehouseStockEntryDraftData
from app.schemas.warehouse import WarehouseStockEntryDraftItemCreateRequest
from app.schemas.warehouse import WarehouseStockEntryDraftItemData
from app.schemas.warehouse import WarehouseStockEntryOutboxStatusData
from app.schemas.warehouse import WarehouseStockEntryWorkerRunOnceData
from app.schemas.warehouse import WarehouseStockLedgerData
from app.schemas.warehouse import WarehouseStockLedgerItem
from app.schemas.warehouse import WarehouseSerialNumberDetailData
from app.schemas.warehouse import WarehouseSerialNumberItem
from app.schemas.warehouse import WarehouseSerialNumberListData
from app.schemas.warehouse import WarehouseStockSummaryData
from app.schemas.warehouse import WarehouseStockSummaryItem
from app.schemas.warehouse import WarehouseTraceabilityData
from app.schemas.warehouse import WarehouseTraceabilityItem
from app.services.erpnext_warehouse_adapter import ERPNextWarehouseAdapter


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


class WarehouseService:
    """Warehouse read-only and draft/outbox write service."""

    _PURPOSES = {"Material Issue", "Material Receipt", "Material Transfer"}
    _INVENTORY_ACTIVE_STATUSES = {"draft", "counted", "variance_review"}

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
        rows, total = self._require_adapter().list_stock_ledger(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
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
        rows = self._require_adapter().list_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        items = [self._summary_item(row) for row in rows]
        items.sort(key=lambda row: (row.company, row.warehouse, row.item_code))
        return WarehouseStockSummaryData(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            items=items,
        )

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

    def create_stock_entry_draft(
        self,
        *,
        payload: WarehouseStockEntryDraftCreateRequest,
        current_user: str,
    ) -> WarehouseStockEntryDraftData:
        session = self._require_session()

        company = self._require_text(payload.company, "company")
        purpose = self._require_text(payload.purpose, "purpose")
        if purpose not in self._PURPOSES:
            raise WarehouseServiceError(400, "WAREHOUSE_INVALID_PURPOSE", "purpose 非法")

        source_type = self._require_text(payload.source_type, "source_type")
        source_id = self._require_text(payload.source_id, "source_id")
        source_warehouse = self._text(payload.source_warehouse)
        target_warehouse = self._text(payload.target_warehouse)
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")

        self._validate_purpose_warehouses(
            purpose=purpose,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
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
            return self._build_draft_data(existing_by_source)

        item_rows = self._normalize_item_payloads(
            items=payload.items,
            fallback_source_warehouse=source_warehouse,
            fallback_target_warehouse=target_warehouse,
        )

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

        outbox_payload = {
            "draft_id": int(draft.id),
            "company": company,
            "purpose": purpose,
            "source_type": source_type,
            "source_id": source_id,
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

        return self._build_draft_data(draft)

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

        now = datetime.now(timezone.utc)
        draft.status = "cancelled"
        draft.cancelled_by = cancelled_by
        draft.cancelled_at = now
        draft.cancel_reason = self._require_text(reason, "reason")

        events = (
            session.query(LyWarehouseStockEntryOutboxEvent)
            .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
            .all()
        )
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
        item_rows = self._normalize_inventory_count_items(items=payload.items)
        count_no = self._build_inventory_count_no(company=company, warehouse=warehouse, count_date=payload.count_date)
        now = datetime.now(timezone.utc)

        inventory_count = LyWarehouseInventoryCount(
            company=company,
            warehouse=warehouse,
            status="draft",
            count_no=count_no,
            count_date=payload.count_date,
            created_by=current_user,
            created_at=now,
            remark=self._text(payload.remark),
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
        if str(inventory_count.status) != "variance_review":
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_INVALID_STATUS", "当前状态不允许确认")

        variance_items = self._variance_items_for_count(count_id=count_id)
        unresolved = [item for item in variance_items if str(item.review_status) == "pending"]
        if unresolved:
            raise WarehouseServiceError(409, "WAREHOUSE_VARIANCE_REVIEW_PENDING", "存在未复核差异行，无法确认")

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
        if status == "confirmed":
            raise WarehouseServiceError(409, "WAREHOUSE_INVENTORY_COUNT_CONFIRMED", "盘点单已确认，无法取消")
        if status not in self._INVENTORY_ACTIVE_STATUSES:
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

        return WarehouseStockEntryDraftData(
            id=draft_id,
            company=str(draft.company),
            purpose=str(draft.purpose),
            source_type=str(draft.source_type),
            source_id=str(draft.source_id),
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

    def _latest_outbox_for_draft(self, draft_id: int) -> LyWarehouseStockEntryOutboxEvent | None:
        return (
            self._require_session()
            .query(LyWarehouseStockEntryOutboxEvent)
            .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
            .order_by(LyWarehouseStockEntryOutboxEvent.id.desc())
            .first()
        )

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
            if variance_qty != Decimal("0") and variance_reason is None:
                raise WarehouseServiceError(
                    400,
                    "WAREHOUSE_VARIANCE_REASON_REQUIRED",
                    f"items[{idx}] 存在差异时 variance_reason 必填",
                )

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

    @staticmethod
    def _build_inventory_count_no(*, company: str, warehouse: str, count_date: date) -> str:
        raw = f"{company}|{warehouse}|{count_date.isoformat()}|{datetime.now(timezone.utc).isoformat()}".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()[:8].upper()
        return f"IC-{count_date.strftime('%Y%m%d')}-{digest}"

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
    def _require_text(value: Any, field_name: str) -> str:
        text = WarehouseService._text(value)
        if text is None:
            raise WarehouseServiceError(400, "WAREHOUSE_INVALID_PAYLOAD", f"{field_name} 不能为空")
        return text
