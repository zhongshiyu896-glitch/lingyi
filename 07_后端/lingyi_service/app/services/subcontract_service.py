"""Business service for subcontract module (TASK-002)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from decimal import ROUND_HALF_UP
import hashlib
import json
from typing import Any

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import SUBCONTRACT_MATERIAL_NOT_IN_BOM
from app.core.error_codes import SUBCONTRACT_MATERIAL_QTY_EXCEEDED
from app.core.error_codes import SUBCONTRACT_COMPANY_AMBIGUOUS
from app.core.error_codes import SUBCONTRACT_COMPANY_REQUIRED
from app.core.error_codes import SUBCONTRACT_COMPANY_UNRESOLVED
from app.core.error_codes import SUBCONTRACT_BOM_ITEM_MISMATCH
from app.core.error_codes import SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS
from app.core.error_codes import SUBCONTRACT_IDEMPOTENCY_CONFLICT
from app.core.error_codes import SUBCONTRACT_INSPECTION_NOT_READY
from app.core.error_codes import SUBCONTRACT_INSPECTION_QTY_EXCEEDED
from app.core.error_codes import SUBCONTRACT_INVALID_QTY
from app.core.error_codes import SUBCONTRACT_ITEM_NOT_FOUND
from app.core.error_codes import SUBCONTRACT_NOT_FOUND
from app.core.error_codes import SUBCONTRACT_PROCESS_NOT_SUBCONTRACT
from app.core.error_codes import SUBCONTRACT_RATE_REQUIRED
from app.core.error_codes import SUBCONTRACT_RECEIPT_BATCH_NOT_FOUND
from app.core.error_codes import SUBCONTRACT_RECEIPT_BATCH_REQUIRED
from app.core.error_codes import SUBCONTRACT_RECEIPT_ITEM_INVALID
from app.core.error_codes import SUBCONTRACT_RECEIPT_NOT_SYNCED
from app.core.error_codes import SUBCONTRACT_RECEIPT_QTY_EXCEEDED
from app.core.error_codes import SUBCONTRACT_RECEIPT_WAREHOUSE_REQUIRED
from app.core.error_codes import SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED
from app.core.error_codes import SUBCONTRACT_SCOPE_BLOCKED
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_LOCKED
from app.core.error_codes import SUBCONTRACT_STATUS_INVALID
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_CONFLICT
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import SubcontractInternalError
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.models.subcontract import LySubcontractStockOutbox
from app.schemas.subcontract import InspectRequest
from app.schemas.subcontract import InspectData
from app.schemas.subcontract import IssueMaterialData
from app.schemas.subcontract import IssueMaterialRequest
from app.schemas.subcontract import ReceiveData
from app.schemas.subcontract import ReceiveRequest
from app.schemas.subcontract import SubcontractCreateData
from app.schemas.subcontract import SubcontractCreateRequest
from app.schemas.subcontract import SubcontractInspectionDetailItem
from app.schemas.subcontract import SubcontractListData
from app.schemas.subcontract import SubcontractListItem
from app.schemas.subcontract import SubcontractListQuery
from app.schemas.subcontract import SubcontractReceiptDetailItem
from app.schemas.subcontract import SubcontractStockSyncRetryData
from app.services.subcontract_migration_service import SubcontractCompanyBackfillReport
from app.services.subcontract_migration_service import SubcontractMigrationService
from app.services.subcontract_stock_outbox_service import SubcontractStockOutboxService


class SubcontractService:
    """Subcontract order service with state transitions."""

    _INSPECTION_DECIMAL_KEYS = {
        "inspected_qty",
        "rejected_qty",
        "accepted_qty",
        "rejected_rate",
        "subcontract_rate",
        "deduction_amount_per_piece",
        "gross_amount",
        "deduction_amount",
        "net_amount",
    }

    def __init__(self, session: Session):
        self.session = session
        bind = getattr(session, "bind", None)
        self._is_sqlite = bool(bind and bind.dialect.name == "sqlite")

    def create_order(self, *, payload: SubcontractCreateRequest, operator: str) -> SubcontractCreateData:
        """Create subcontract order (no commit in service)."""
        bom_item_code = self._validate_bom_exists(bom_id=payload.bom_id)
        item_code = payload.item_code.strip()
        process_name = payload.process_name.strip()
        if item_code != bom_item_code:
            raise BusinessException(code=SUBCONTRACT_BOM_ITEM_MISMATCH, message="外发单与 BOM 物料不匹配")
        self._validate_subcontract_process(bom_id=payload.bom_id, process_name=process_name)
        subcontract_rate = self._resolve_subcontract_rate(
            bom_id=payload.bom_id,
            process_name=process_name,
        )
        company = self._normalize_company(payload.company)
        if company is None:
            raise BusinessException(code=SUBCONTRACT_COMPANY_REQUIRED, message="外发单 company 不能为空")

        now = datetime.utcnow()
        subcontract_no = f"SC-{now.strftime('%Y%m%d%H%M%S%f')}"
        order = LySubcontractOrder(
            subcontract_no=subcontract_no,
            supplier=payload.supplier.strip(),
            item_code=item_code,
            company=company,
            bom_id=payload.bom_id,
            process_name=process_name,
            planned_qty=payload.planned_qty,
            subcontract_rate=subcontract_rate,
            issued_qty=Decimal("0"),
            received_qty=Decimal("0"),
            inspected_qty=Decimal("0"),
            rejected_qty=Decimal("0"),
            accepted_qty=Decimal("0"),
            gross_amount=Decimal("0"),
            deduction_amount=Decimal("0"),
            net_amount=Decimal("0"),
            status="draft",
            resource_scope_status="ready",
            scope_error_code=None,
        )
        if self._is_sqlite:
            order.id = self._next_id(LySubcontractOrder)
        self.session.add(order)
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        self._log_status(
            order_id=order.id,
            from_status="draft",
            to_status="draft",
            operator=operator,
            company=company,
        )
        return SubcontractCreateData(name=order.subcontract_no, company=company)

    def list_orders(
        self,
        *,
        query: SubcontractListQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
        readable_suppliers: set[str] | None = None,
    ) -> SubcontractListData:
        """List subcontract orders with pagination."""
        try:
            sql = self.session.query(LySubcontractOrder)
            if query.supplier:
                sql = sql.filter(LySubcontractOrder.supplier == query.supplier)
            if query.status:
                sql = sql.filter(LySubcontractOrder.status == query.status)
            if query.from_date:
                sql = sql.filter(LySubcontractOrder.created_at >= query.from_date)
            if query.to_date:
                sql = sql.filter(LySubcontractOrder.created_at <= query.to_date)

            if readable_item_codes is not None:
                if not readable_item_codes:
                    return SubcontractListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LySubcontractOrder.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return SubcontractListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LySubcontractOrder.company.in_(sorted(readable_companies)))
            if readable_suppliers is not None:
                if not readable_suppliers:
                    return SubcontractListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LySubcontractOrder.supplier.in_(sorted(readable_suppliers)))

            total = sql.with_entities(func.count(LySubcontractOrder.id)).scalar() or 0
            rows: list[LySubcontractOrder] = (
                sql.order_by(LySubcontractOrder.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        except BusinessException:
            raise
        except Exception as exc:
            raise SubcontractInternalError() from exc

        order_ids = [int(row.id) for row in rows]
        latest_issue_by_order = self._latest_outbox_by_order_ids(
            order_ids=order_ids,
            stock_action=SubcontractStockOutboxService.STOCK_ACTION_ISSUE,
        )
        latest_receipt_by_order = self._latest_outbox_by_order_ids(
            order_ids=order_ids,
            stock_action=SubcontractStockOutboxService.STOCK_ACTION_RECEIPT,
        )

        return SubcontractListData(
            items=[
                SubcontractListItem(
                    id=int(row.id),
                    subcontract_no=str(row.subcontract_no),
                    supplier=str(row.supplier),
                    item_code=str(row.item_code),
                    company=(str(row.company).strip() if row.company is not None else None),
                    bom_id=int(row.bom_id),
                    process_name=str(row.process_name),
                    planned_qty=Decimal(row.planned_qty),
                    subcontract_rate=Decimal(str(getattr(row, "subcontract_rate", 0) or 0)),
                    issued_qty=Decimal(str(getattr(row, "issued_qty", 0) or 0)),
                    received_qty=Decimal(str(getattr(row, "received_qty", 0) or 0)),
                    inspected_qty=Decimal(str(getattr(row, "inspected_qty", 0) or 0)),
                    rejected_qty=Decimal(str(getattr(row, "rejected_qty", 0) or 0)),
                    accepted_qty=Decimal(str(getattr(row, "accepted_qty", 0) or 0)),
                    gross_amount=Decimal(str(getattr(row, "gross_amount", 0) or 0)),
                    deduction_amount=Decimal(str(getattr(row, "deduction_amount", 0) or 0)),
                    net_amount=Decimal(str(getattr(row, "net_amount", 0) or 0)),
                    status=str(row.status),
                    resource_scope_status=str(row.resource_scope_status),
                    latest_issue_outbox_id=(
                        int(latest_issue_by_order[int(row.id)].id) if int(row.id) in latest_issue_by_order else None
                    ),
                    latest_issue_sync_status=(
                        str(latest_issue_by_order[int(row.id)].status)
                        if int(row.id) in latest_issue_by_order
                        else None
                    ),
                    latest_issue_stock_entry_name=(
                        str(latest_issue_by_order[int(row.id)].stock_entry_name)
                        if int(row.id) in latest_issue_by_order
                        and latest_issue_by_order[int(row.id)].stock_entry_name
                        else None
                    ),
                    latest_issue_idempotency_key=(
                        str(latest_issue_by_order[int(row.id)].idempotency_key)
                        if int(row.id) in latest_issue_by_order
                        and latest_issue_by_order[int(row.id)].idempotency_key
                        else None
                    ),
                    latest_issue_error_code=(
                        str(latest_issue_by_order[int(row.id)].last_error_code)
                        if int(row.id) in latest_issue_by_order
                        and latest_issue_by_order[int(row.id)].last_error_code
                        else None
                    ),
                    latest_receipt_outbox_id=(
                        int(latest_receipt_by_order[int(row.id)].id)
                        if int(row.id) in latest_receipt_by_order
                        else None
                    ),
                    latest_receipt_sync_status=(
                        str(latest_receipt_by_order[int(row.id)].status)
                        if int(row.id) in latest_receipt_by_order
                        else None
                    ),
                    latest_receipt_stock_entry_name=(
                        str(latest_receipt_by_order[int(row.id)].stock_entry_name)
                        if int(row.id) in latest_receipt_by_order
                        and latest_receipt_by_order[int(row.id)].stock_entry_name
                        else None
                    ),
                    latest_receipt_idempotency_key=(
                        str(latest_receipt_by_order[int(row.id)].idempotency_key)
                        if int(row.id) in latest_receipt_by_order
                        and latest_receipt_by_order[int(row.id)].idempotency_key
                        else None
                    ),
                    latest_receipt_error_code=(
                        str(latest_receipt_by_order[int(row.id)].last_error_code)
                        if int(row.id) in latest_receipt_by_order
                        and latest_receipt_by_order[int(row.id)].last_error_code
                        else None
                    ),
                    created_at=row.created_at,
                )
                for row in rows
            ],
            total=int(total),
            page=query.page,
            page_size=query.page_size,
        )

    def issue_material(
        self,
        *,
        order_id: int,
        payload: IssueMaterialRequest,
        operator: str,
        request_id: str | None = None,
    ) -> IssueMaterialData:
        """Create local issue facts and pending issue outbox (TASK-002D)."""
        order = self._must_get_order(order_id=order_id)
        self._ensure_scope_ready(order)
        self._ensure_issue_allowed(order=order)

        warehouse = payload.warehouse.strip()
        if not warehouse:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="发料仓不能为空")

        idempotency_key = payload.idempotency_key.strip()
        if not idempotency_key:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="幂等键不能为空")

        outbox_service = SubcontractStockOutboxService(session=self.session)
        idempotency_payload = self._build_issue_idempotency_payload(
            order=order,
            warehouse=warehouse,
            materials=payload.materials,
        )
        idempotency_payload_hash = outbox_service.build_payload_hash(idempotency_payload)
        existing_outbox = outbox_service.find_by_idempotency(
            subcontract_id=order_id,
            stock_action=SubcontractStockOutboxService.STOCK_ACTION_ISSUE,
            idempotency_key=idempotency_key,
        )
        if existing_outbox is not None:
            if (existing_outbox.payload_hash or "") == idempotency_payload_hash:
                existing_batch_no = self._existing_issue_batch_no(outbox_id=int(existing_outbox.id))
                return IssueMaterialData(
                    outbox_id=int(existing_outbox.id),
                    issue_batch_no=existing_batch_no or self._next_issue_batch_no(order_id=order_id),
                    sync_status=str(existing_outbox.status),
                    stock_entry_name=(
                        str(existing_outbox.stock_entry_name) if existing_outbox.stock_entry_name else None
                    ),
                )
            raise BusinessException(
                code=SUBCONTRACT_IDEMPOTENCY_CONFLICT,
                message="幂等键冲突，且请求内容不一致",
            )

        bom_plan = self._load_bom_material_plan(order=order)
        issued_summary = self._issued_qty_summary(order_id=order_id)
        issue_lines = self._resolve_issue_lines(
            materials=payload.materials,
            bom_plan=bom_plan,
            issued_summary=issued_summary,
        )
        if not issue_lines:
            raise BusinessException(code=SUBCONTRACT_MATERIAL_QTY_EXCEEDED, message="没有可发料数量")

        issue_batch_no = self._next_issue_batch_no(order_id=order_id)
        payload_json = self._build_issue_stock_payload(
            order=order,
            warehouse=warehouse,
            issue_batch_no=issue_batch_no,
            issue_lines=issue_lines,
            request_id=request_id or "",
            outbox_id_placeholder=0,
            event_key_placeholder="",
        )
        outbox, created_new = outbox_service.enqueue_issue(
            subcontract_id=order_id,
            company=self._normalize_company(order.company) or "",
            supplier=str(order.supplier),
            item_code=str(order.item_code),
            warehouse=warehouse,
            idempotency_key=idempotency_key,
            payload_json=payload_json,
            idempotency_payload_hash=idempotency_payload_hash,
            request_id=request_id or "",
            created_by=operator,
        )

        if not created_new:
            existing_batch_no = self._existing_issue_batch_no(outbox_id=int(outbox.id)) or issue_batch_no
            return IssueMaterialData(
                outbox_id=int(outbox.id),
                issue_batch_no=existing_batch_no,
                sync_status=str(outbox.status),
                stock_entry_name=(str(outbox.stock_entry_name) if outbox.stock_entry_name else None),
            )

        # replace placeholders now that outbox id/event key are known
        payload_json = self._build_issue_stock_payload(
            order=order,
            warehouse=warehouse,
            issue_batch_no=issue_batch_no,
            issue_lines=issue_lines,
            request_id=request_id or "",
            outbox_id_placeholder=int(outbox.id),
            event_key_placeholder=str(outbox.event_key or ""),
        )
        outbox.payload_json = payload_json
        outbox.payload = payload_json
        outbox.action = SubcontractStockOutboxService.STOCK_ACTION_ISSUE

        next_material_id: int | None = self._next_id(LySubcontractMaterial) if self._is_sqlite else None

        for line in issue_lines:
            material_row = LySubcontractMaterial(
                subcontract_id=order_id,
                stock_outbox_id=int(outbox.id),
                company=self._normalize_company(order.company),
                issue_batch_no=issue_batch_no,
                material_item_code=line["material_item_code"],
                required_qty=line["required_qty"],
                issued_qty=line["issued_qty"],
                sync_status="pending",
                stock_entry_name=None,
            )
            if next_material_id is not None:
                material_row.id = next_material_id
                next_material_id += 1
            self.session.add(material_row)

        if str(order.status) == "draft":
            order.status = "issued"
            self._log_status(
                order_id=order_id,
                from_status="draft",
                to_status="issued",
                operator=operator,
                company=self._normalize_company(order.company),
            )
        issued_delta = sum(Decimal(str(line["issued_qty"])) for line in issue_lines)
        order.issued_qty = Decimal(str(getattr(order, "issued_qty", 0) or 0)) + issued_delta
        order.updated_at = datetime.utcnow()

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        return IssueMaterialData(
            outbox_id=int(outbox.id),
            issue_batch_no=issue_batch_no,
            sync_status="pending",
            stock_entry_name=None,
        )

    def receive(
        self,
        *,
        order_id: int,
        payload: ReceiveRequest | None = None,
        operator: str | None = None,
        request_id: str | None = None,
    ) -> ReceiveData:
        """Create local receipt facts and pending receipt outbox (TASK-002E)."""
        if payload is None:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="回料请求不能为空")
        if not operator:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="操作人不能为空")

        order = self._must_get_order(order_id=order_id)
        self._ensure_scope_ready(order)
        receipt_warehouse = payload.receipt_warehouse.strip()
        if not receipt_warehouse:
            raise BusinessException(code=SUBCONTRACT_RECEIPT_WAREHOUSE_REQUIRED, message="回料仓不能为空")
        idempotency_key = payload.idempotency_key.strip()
        if not idempotency_key:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="幂等键不能为空")

        received_qty = Decimal(str(payload.received_qty))
        if received_qty <= Decimal("0"):
            raise BusinessException(code=SUBCONTRACT_INVALID_QTY, message="回料数量必须大于 0")

        receipt_item_code = (payload.item_code or "").strip() or str(order.item_code)
        if receipt_item_code != str(order.item_code):
            raise BusinessException(code=SUBCONTRACT_RECEIPT_ITEM_INVALID, message="回料 item 必须与外发单 item 一致")

        outbox_service = SubcontractStockOutboxService(session=self.session)
        idempotency_payload = self._build_receive_idempotency_payload(
            order=order,
            receipt_warehouse=receipt_warehouse,
            received_qty=received_qty,
            payload=payload,
        )
        idempotency_payload_hash = outbox_service.build_payload_hash(idempotency_payload)
        existing_outbox = outbox_service.find_by_idempotency(
            subcontract_id=order_id,
            stock_action=SubcontractStockOutboxService.STOCK_ACTION_RECEIPT,
            idempotency_key=idempotency_key,
        )
        if existing_outbox is not None:
            if (existing_outbox.payload_hash or "") == idempotency_payload_hash:
                existing_batch_no = self._existing_receipt_batch_no(outbox_id=int(existing_outbox.id))
                return ReceiveData(
                    outbox_id=int(existing_outbox.id),
                    receipt_batch_no=existing_batch_no or self._next_receipt_batch_no(order_id=order_id),
                    sync_status=str(existing_outbox.status),
                    stock_entry_name=(
                        str(existing_outbox.stock_entry_name) if existing_outbox.stock_entry_name else None
                    ),
                )
            raise BusinessException(code=SUBCONTRACT_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

        self._ensure_receive_allowed(order=order)

        received_total = self._received_qty_total(order_id=order_id)
        remaining_receivable = Decimal(str(order.planned_qty)) - received_total
        if received_qty > remaining_receivable:
            raise BusinessException(code=SUBCONTRACT_RECEIPT_QTY_EXCEEDED, message="回料数量超过剩余可回数量")

        receipt_batch_no = self._next_receipt_batch_no(order_id=order_id)
        payload_json = self._build_receive_stock_payload(
            order=order,
            receipt_warehouse=receipt_warehouse,
            receipt_batch_no=receipt_batch_no,
            received_qty=received_qty,
            payload=payload,
            request_id=request_id or "",
            outbox_id_placeholder=0,
            event_key_placeholder="",
        )

        outbox, created_new = outbox_service.enqueue_receipt(
            subcontract_id=order_id,
            company=self._normalize_company(order.company) or "",
            supplier=str(order.supplier),
            item_code=str(order.item_code),
            warehouse=receipt_warehouse,
            idempotency_key=idempotency_key,
            payload_json=payload_json,
            idempotency_payload_hash=idempotency_payload_hash,
            request_id=request_id or "",
            created_by=operator,
        )
        if not created_new:
            existing_batch_no = self._existing_receipt_batch_no(outbox_id=int(outbox.id)) or receipt_batch_no
            return ReceiveData(
                outbox_id=int(outbox.id),
                receipt_batch_no=existing_batch_no,
                sync_status=str(outbox.status),
                stock_entry_name=(str(outbox.stock_entry_name) if outbox.stock_entry_name else None),
            )

        payload_json = self._build_receive_stock_payload(
            order=order,
            receipt_warehouse=receipt_warehouse,
            receipt_batch_no=receipt_batch_no,
            received_qty=received_qty,
            payload=payload,
            request_id=request_id or "",
            outbox_id_placeholder=int(outbox.id),
            event_key_placeholder=str(outbox.event_key or ""),
        )
        outbox.payload_json = payload_json
        outbox.payload = payload_json
        outbox.action = SubcontractStockOutboxService.STOCK_ACTION_RECEIPT

        next_receipt_id: int | None = self._next_id(LySubcontractReceipt) if self._is_sqlite else None
        receipt_row = LySubcontractReceipt(
            subcontract_id=order_id,
            stock_outbox_id=int(outbox.id),
            company=self._normalize_company(order.company),
            receipt_batch_no=receipt_batch_no,
            receipt_warehouse=receipt_warehouse,
            item_code=receipt_item_code,
            color=(payload.color.strip() if payload.color else None),
            size=(payload.size.strip() if payload.size else None),
            batch_no=(payload.batch_no.strip() if payload.batch_no else None),
            uom=(payload.uom.strip() if payload.uom else "Nos"),
            received_qty=received_qty,
            sync_status="pending",
            sync_error_code=None,
            idempotency_key=idempotency_key,
            payload_hash=idempotency_payload_hash,
            received_by=operator,
            received_at=datetime.utcnow(),
            stock_entry_name=None,
            inspected_qty=Decimal("0"),
            rejected_qty=Decimal("0"),
            rejected_rate=Decimal("0"),
            deduction_amount=Decimal("0"),
            net_amount=Decimal("0"),
            inspect_status="pending",
        )
        if next_receipt_id is not None:
            receipt_row.id = next_receipt_id
        self.session.add(receipt_row)

        from_status = str(order.status)
        if from_status != "waiting_inspection":
            order.status = "waiting_inspection"
            self._log_status(
                order_id=order_id,
                from_status=from_status,
                to_status="waiting_inspection",
                operator=operator,
                company=self._normalize_company(order.company),
            )
        order.received_qty = received_total + received_qty
        order.updated_at = datetime.utcnow()

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        return ReceiveData(
            outbox_id=int(outbox.id),
            receipt_batch_no=receipt_batch_no,
            sync_status="pending",
            stock_entry_name=None,
        )

    def inspect(
        self,
        *,
        order_id: int,
        payload: InspectRequest | None = None,
        operator: str | None = None,
        request_id: str | None = None,
    ) -> InspectData:
        """Create local inspection fact and update order rollups (TASK-002F)."""
        if payload is None:
            raise BusinessException(code=SUBCONTRACT_INSPECTION_NOT_READY, message="验货请求不能为空")
        if not operator:
            raise BusinessException(code=SUBCONTRACT_INSPECTION_NOT_READY, message="验货操作人不能为空")

        order = self._must_get_order(order_id=order_id)
        self._ensure_scope_ready(order)

        receipt_batch_no = str(payload.receipt_batch_no or "").strip()
        if not receipt_batch_no:
            raise BusinessException(code=SUBCONTRACT_RECEIPT_BATCH_REQUIRED, message="验货必须指定回料批次")

        idempotency_key = str(payload.idempotency_key or "").strip()
        if not idempotency_key:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="验货幂等键不能为空")

        inspected_qty = Decimal(str(payload.inspected_qty))
        rejected_qty = Decimal(str(payload.rejected_qty))
        deduction_amount_per_piece = Decimal(str(payload.deduction_amount_per_piece))

        if inspected_qty <= Decimal("0"):
            raise BusinessException(code=SUBCONTRACT_INVALID_QTY, message="验货数量必须大于 0")
        if rejected_qty < Decimal("0"):
            raise BusinessException(code=SUBCONTRACT_INVALID_QTY, message="不合格数量必须大于等于 0")
        if deduction_amount_per_piece < Decimal("0"):
            raise BusinessException(code=SUBCONTRACT_INVALID_QTY, message="扣款单价必须大于等于 0")
        if rejected_qty > inspected_qty:
            raise BusinessException(
                code=SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED,
                message="不合格数量不能大于验货数量",
            )

        idempotency_payload = self._build_inspection_idempotency_payload(
            order=order,
            payload=payload,
            receipt_batch_no=receipt_batch_no,
            inspected_qty=inspected_qty,
            rejected_qty=rejected_qty,
            deduction_amount_per_piece=deduction_amount_per_piece,
        )
        payload_hash = self.build_inspection_payload_hash(idempotency_payload)
        existing = self._find_inspection_by_idempotency(order_id=order_id, idempotency_key=idempotency_key)
        if existing is not None:
            if (existing.payload_hash or "") == payload_hash:
                return self._inspection_result_from_row(row=existing, status=str(order.status))
            raise BusinessException(code=SUBCONTRACT_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

        self._ensure_inspect_allowed(order=order)
        settlement_status = str(getattr(order, "settlement_status", "") or "").strip().lower()
        if settlement_status == "settled":
            raise BusinessException(code=SUBCONTRACT_SETTLEMENT_LOCKED, message="外发单已结算锁定")

        receipt_rows = self._must_get_receipt_batch_rows(order_id=order_id, receipt_batch_no=receipt_batch_no)
        for row in receipt_rows:
            if str(row.sync_status or "").strip().lower() != "succeeded" or not str(row.stock_entry_name or "").strip():
                raise BusinessException(code=SUBCONTRACT_RECEIPT_NOT_SYNCED, message="回料批次尚未同步成功，禁止验货")

        batch_received_qty = sum(Decimal(str(row.received_qty or "0")) for row in receipt_rows)
        batch_inspected_qty = self._inspected_qty_total(order_id=order_id, receipt_batch_no=receipt_batch_no)
        batch_remaining_qty = batch_received_qty - batch_inspected_qty
        if inspected_qty > batch_remaining_qty:
            raise BusinessException(
                code=SUBCONTRACT_INSPECTION_QTY_EXCEEDED,
                message="验货数量超过批次剩余可验数量",
            )

        subcontract_rate = self._effective_subcontract_rate(order=order)
        accepted_qty = inspected_qty - rejected_qty
        rejected_rate = self._quantize_ratio(rejected_qty / inspected_qty if inspected_qty > 0 else Decimal("0"))
        gross_amount = self._quantize_money(inspected_qty * subcontract_rate)
        deduction_amount = self._quantize_money(rejected_qty * deduction_amount_per_piece)
        if deduction_amount > gross_amount:
            raise BusinessException(code=SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS, message="扣款金额不能大于验货总金额")
        net_amount = self._quantize_money(gross_amount - deduction_amount)

        existing_totals = self._inspection_totals(order_id=order_id)
        total_inspected_qty = existing_totals["inspected_qty"] + inspected_qty
        total_rejected_qty = existing_totals["rejected_qty"] + rejected_qty
        total_accepted_qty = existing_totals["accepted_qty"] + accepted_qty
        total_gross_amount = self._quantize_money(existing_totals["gross_amount"] + gross_amount)
        total_deduction_amount = self._quantize_money(existing_totals["deduction_amount"] + deduction_amount)
        total_net_amount = self._quantize_money(existing_totals["net_amount"] + net_amount)
        total_received_qty = self._received_qty_total(order_id=order_id)

        from_status = str(order.status)
        to_status = self._next_status_after_inspection(
            planned_qty=Decimal(str(order.planned_qty)),
            total_received_qty=total_received_qty,
            total_inspected_qty=total_inspected_qty,
        )

        inspection_no = self._next_inspection_no(order_id=order_id)
        inspection_row = LySubcontractInspection(
            subcontract_id=order_id,
            company=self._normalize_company(order.company),
            inspection_no=inspection_no,
            receipt_batch_no=receipt_batch_no,
            receipt_warehouse=self._receipt_warehouse_from_rows(receipt_rows=receipt_rows),
            item_code=str(order.item_code),
            inspected_qty=inspected_qty,
            rejected_qty=rejected_qty,
            accepted_qty=accepted_qty,
            rejected_rate=rejected_rate,
            subcontract_rate=subcontract_rate,
            gross_amount=gross_amount,
            deduction_amount_per_piece=deduction_amount_per_piece,
            deduction_amount=deduction_amount,
            net_amount=net_amount,
            settlement_status="unsettled",
            statement_id=None,
            statement_no=None,
            settlement_locked_by=None,
            settlement_locked_at=None,
            settled_by=None,
            settled_at=None,
            settlement_request_id=None,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            inspected_by=operator,
            inspected_at=datetime.utcnow(),
            request_id=request_id,
            remark=(payload.remark.strip()[:200] if payload.remark and payload.remark.strip() else None),
            status="inspected",
        )
        if self._is_sqlite:
            inspection_row.id = self._next_id(LySubcontractInspection)
        self.session.add(inspection_row)

        for receipt_row in receipt_rows:
            receipt_row.inspect_status = "inspected" if inspected_qty == batch_remaining_qty else "pending"

        order.received_qty = total_received_qty
        order.inspected_qty = total_inspected_qty
        order.rejected_qty = total_rejected_qty
        order.accepted_qty = total_accepted_qty
        order.gross_amount = total_gross_amount
        order.deduction_amount = total_deduction_amount
        order.net_amount = total_net_amount
        order.status = to_status
        order.updated_at = datetime.utcnow()
        if from_status != to_status:
            self._log_status(
                order_id=order_id,
                from_status=from_status,
                to_status=to_status,
                operator=operator,
                company=self._normalize_company(order.company),
            )

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        if not str(inspection_row.settlement_line_key or "").strip() and inspection_row.id is not None:
            inspection_row.settlement_line_key = f"subcontract_inspection:{int(inspection_row.id)}"
            try:
                self.session.flush()
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc

        return self._inspection_result_from_row(row=inspection_row, status=to_status)

    @classmethod
    def build_inspection_payload_hash(cls, payload_json: dict[str, object]) -> str:
        """Build inspection idempotency hash with receipt-batch isolation semantics."""
        canonical_payload = cls._canonicalize_inspection_value(payload_json)
        if not isinstance(canonical_payload, dict):
            canonical_payload = {}
        canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def _canonicalize_inspection_value(cls, value: Any, *, key: str | None = None) -> Any:
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for child_key, child_value in value.items():
                normalized[child_key] = cls._canonicalize_inspection_value(child_value, key=child_key)
            return normalized
        if isinstance(value, list):
            return [cls._canonicalize_inspection_value(item) for item in value]
        if key in cls._INSPECTION_DECIMAL_KEYS:
            return cls._normalize_decimal_text(value)
        return value

    @staticmethod
    def _normalize_decimal_text(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, Decimal):
            decimal_value = value
        elif isinstance(value, (int, float)):
            decimal_value = Decimal(str(value))
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return raw
            try:
                decimal_value = Decimal(raw)
            except Exception:
                return value
        else:
            return value

        normalized = format(decimal_value, "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        if normalized in {"-0", ""}:
            normalized = "0"
        return normalized

    def get_receipt_batch_scope(self, *, order_id: int, receipt_batch_no: str) -> dict[str, str | None]:
        """Load receipt-batch scope used by router resource permission checks."""
        order = self._must_get_order(order_id=order_id)
        self._ensure_scope_ready(order)
        rows = self._must_get_receipt_batch_rows(order_id=order_id, receipt_batch_no=receipt_batch_no.strip())
        return {
            "company": self._normalize_company(order.company),
            "item_code": str(order.item_code),
            "supplier": str(order.supplier),
            "receipt_warehouse": self._receipt_warehouse_from_rows(receipt_rows=rows),
            "receipt_batch_no": receipt_batch_no.strip(),
        }

    def get_stock_outbox_for_retry(
        self,
        *,
        order_id: int,
        outbox_id: int,
        stock_action: str,
        idempotency_key: str,
    ) -> LySubcontractStockOutbox:
        """Load and validate retry target identity without mutating outbox state."""
        order = self._must_get_order(order_id=order_id)
        self._ensure_scope_ready(order)
        outbox_service = SubcontractStockOutboxService(session=self.session)
        row = outbox_service.get_by_id(outbox_id=outbox_id)
        outbox_service.ensure_retry_target_matches(
            row=row,
            subcontract_id=order_id,
            stock_action=stock_action,
            idempotency_key=idempotency_key,
        )
        return row

    def retry_stock_sync(
        self,
        *,
        order_id: int,
        outbox_id: int,
        stock_action: str,
        idempotency_key: str,
        request_id: str,
        operator: str,
        reason: str | None = None,
    ) -> SubcontractStockSyncRetryData:
        """Reset specific issue/receipt outbox for manual retry."""
        _ = operator
        _ = reason
        outbox_service = SubcontractStockOutboxService(session=self.session)
        outbox = self.get_stock_outbox_for_retry(
            order_id=order_id,
            outbox_id=outbox_id,
            stock_action=stock_action,
            idempotency_key=idempotency_key,
        )
        outbox_service.ensure_retryable_status(row=outbox)
        outbox_service.reset_for_retry(
            row=outbox,
            request_id=request_id,
            reset_attempts=(str(outbox.status) == SubcontractStockOutboxService.STATUS_DEAD),
        )
        return SubcontractStockSyncRetryData(
            outbox_id=int(outbox.id),
            stock_action=str(outbox.stock_action),
            status=str(outbox.status),
            next_retry_at=outbox.next_retry_at,
        )

    def get_order_or_raise(self, order_id: int) -> LySubcontractOrder:
        return self._must_get_order(order_id=order_id)

    def backfill_company_scope(
        self,
        *,
        dry_run: bool = True,
        operator: str = "migration",
        limit: int | None = None,
    ) -> SubcontractCompanyBackfillReport:
        """Backfill local company scope for historical subcontract orders."""
        migration_service = SubcontractMigrationService(session=self.session)
        return migration_service.backfill_subcontract_company_scope(
            dry_run=dry_run,
            operator=operator,
            limit=limit,
        )

    def get_order_by_no(self, *, subcontract_no: str) -> LySubcontractOrder | None:
        try:
            return (
                self.session.query(LySubcontractOrder)
                .filter(LySubcontractOrder.subcontract_no == subcontract_no)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def get_order_snapshot(self, *, order_id: int) -> dict[str, object]:
        order = self._must_get_order(order_id=order_id)
        latest_issue_outbox = self.latest_issue_outbox(order_id=order_id)
        latest_receipt_outbox = self.latest_receipt_outbox(order_id=order_id)
        return {
            "id": int(order.id),
            "subcontract_no": str(order.subcontract_no),
            "supplier": str(order.supplier),
            "item_code": str(order.item_code),
            "company": self._normalize_company(order.company),
            "bom_id": int(order.bom_id),
            "process_name": str(order.process_name),
            "planned_qty": str(order.planned_qty),
            "subcontract_rate": str(getattr(order, "subcontract_rate", 0) or 0),
            "issued_qty": str(getattr(order, "issued_qty", 0) or 0),
            "received_qty": str(getattr(order, "received_qty", 0) or 0),
            "inspected_qty": str(getattr(order, "inspected_qty", 0) or 0),
            "rejected_qty": str(getattr(order, "rejected_qty", 0) or 0),
            "accepted_qty": str(getattr(order, "accepted_qty", 0) or 0),
            "gross_amount": str(getattr(order, "gross_amount", 0) or 0),
            "deduction_amount": str(getattr(order, "deduction_amount", 0) or 0),
            "net_amount": str(getattr(order, "net_amount", 0) or 0),
            "status": str(order.status),
            "settlement_status": str(order.settlement_status or ""),
            "resource_scope_status": str(order.resource_scope_status),
            "scope_error_code": (str(order.scope_error_code) if order.scope_error_code else None),
            "latest_issue_outbox_id": int(latest_issue_outbox.id) if latest_issue_outbox else None,
            "latest_issue_sync_status": str(latest_issue_outbox.status) if latest_issue_outbox else None,
            "latest_issue_stock_entry_name": (
                str(latest_issue_outbox.stock_entry_name)
                if latest_issue_outbox and latest_issue_outbox.stock_entry_name
                else None
            ),
            "latest_issue_idempotency_key": (
                str(latest_issue_outbox.idempotency_key)
                if latest_issue_outbox and latest_issue_outbox.idempotency_key
                else None
            ),
            "latest_receipt_outbox_id": int(latest_receipt_outbox.id) if latest_receipt_outbox else None,
            "latest_receipt_sync_status": str(latest_receipt_outbox.status) if latest_receipt_outbox else None,
            "latest_receipt_stock_entry_name": (
                str(latest_receipt_outbox.stock_entry_name)
                if latest_receipt_outbox and latest_receipt_outbox.stock_entry_name
                else None
            ),
            "latest_receipt_idempotency_key": (
                str(latest_receipt_outbox.idempotency_key)
                if latest_receipt_outbox and latest_receipt_outbox.idempotency_key
                else None
            ),
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        }

    def list_receipts(self, *, order_id: int) -> list[SubcontractReceiptDetailItem]:
        """List receipt facts for subcontract detail response."""
        try:
            rows = (
                self.session.query(LySubcontractReceipt)
                .filter(LySubcontractReceipt.subcontract_id == order_id)
                .order_by(LySubcontractReceipt.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return [
            SubcontractReceiptDetailItem(
                receipt_batch_no=str(row.receipt_batch_no or ""),
                receipt_warehouse=(str(row.receipt_warehouse) if row.receipt_warehouse else None),
                item_code=(str(row.item_code) if row.item_code else None),
                color=(str(row.color) if row.color else None),
                size=(str(row.size) if row.size else None),
                batch_no=(str(row.batch_no) if row.batch_no else None),
                uom=(str(row.uom) if row.uom else None),
                received_qty=Decimal(str(row.received_qty or "0")),
                sync_status=str(row.sync_status or ""),
                stock_entry_name=(str(row.stock_entry_name) if row.stock_entry_name else None),
                inspect_status=(str(row.inspect_status) if row.inspect_status else None),
                idempotency_key=(str(row.idempotency_key) if row.idempotency_key else None),
                received_by=(str(row.received_by) if row.received_by else None),
                received_at=row.received_at,
            )
            for row in rows
        ]

    def list_inspections(self, *, order_id: int) -> list[SubcontractInspectionDetailItem]:
        """List inspection facts for subcontract detail response."""
        try:
            rows = (
                self.session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.subcontract_id == order_id)
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return [
            SubcontractInspectionDetailItem(
                inspection_no=str(row.inspection_no or ""),
                receipt_batch_no=str(row.receipt_batch_no or ""),
                inspected_qty=Decimal(str(row.inspected_qty or "0")),
                accepted_qty=Decimal(str(row.accepted_qty or "0")),
                rejected_qty=Decimal(str(row.rejected_qty or "0")),
                rejected_rate=Decimal(str(row.rejected_rate or "0")),
                subcontract_rate=Decimal(str(row.subcontract_rate or "0")),
                gross_amount=Decimal(str(row.gross_amount or "0")),
                deduction_amount_per_piece=Decimal(str(row.deduction_amount_per_piece or "0")),
                deduction_amount=Decimal(str(row.deduction_amount or "0")),
                net_amount=Decimal(str(row.net_amount or "0")),
                inspected_by=(str(row.inspected_by) if row.inspected_by else None),
                inspected_at=row.inspected_at,
                remark=(str(row.remark) if row.remark else None),
            )
            for row in rows
        ]

    def latest_issue_outbox(self, *, order_id: int) -> LySubcontractStockOutbox | None:
        outbox_service = SubcontractStockOutboxService(session=self.session)
        return outbox_service.latest_issue_for_subcontract(subcontract_id=order_id)

    def latest_receipt_outbox(self, *, order_id: int) -> LySubcontractStockOutbox | None:
        outbox_service = SubcontractStockOutboxService(session=self.session)
        return outbox_service.latest_receipt_for_subcontract(subcontract_id=order_id)

    def _latest_outbox_by_order_ids(
        self,
        *,
        order_ids: list[int],
        stock_action: str,
    ) -> dict[int, LySubcontractStockOutbox]:
        if not order_ids:
            return {}
        try:
            rows = (
                self.session.query(LySubcontractStockOutbox)
                .filter(
                    LySubcontractStockOutbox.subcontract_id.in_(order_ids),
                    LySubcontractStockOutbox.stock_action == stock_action,
                )
                .order_by(
                    LySubcontractStockOutbox.subcontract_id.asc(),
                    LySubcontractStockOutbox.created_at.desc(),
                    LySubcontractStockOutbox.id.desc(),
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        latest_map: dict[int, LySubcontractStockOutbox] = {}
        for row in rows:
            subcontract_id = int(row.subcontract_id)
            if subcontract_id not in latest_map:
                latest_map[subcontract_id] = row
        return latest_map

    def _must_get_order(self, *, order_id: int) -> LySubcontractOrder:
        try:
            order = self.session.query(LySubcontractOrder).filter(LySubcontractOrder.id == order_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not order:
            raise BusinessException(code=SUBCONTRACT_NOT_FOUND, message="外发单不存在")
        return order

    def _validate_bom_exists(self, *, bom_id: int) -> str:
        try:
            row = self.session.query(LyApparelBom.item_code).filter(LyApparelBom.id == bom_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            raise BusinessException(code=SUBCONTRACT_ITEM_NOT_FOUND, message="BOM 不存在")
        item_code = str(row[0] or "").strip()
        if not item_code:
            raise BusinessException(code=SUBCONTRACT_ITEM_NOT_FOUND, message="BOM 不存在")
        return item_code

    def _validate_subcontract_process(self, *, bom_id: int, process_name: str) -> None:
        try:
            row = (
                self.session.query(LyBomOperation.id)
                .filter(
                    and_(
                        LyBomOperation.bom_id == bom_id,
                        LyBomOperation.process_name == process_name,
                        LyBomOperation.is_subcontract.is_(True),
                    )
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row:
            return
        raise BusinessException(code=SUBCONTRACT_PROCESS_NOT_SUBCONTRACT, message="该工序不是外发工序")

    def _ensure_issue_allowed(self, *, order: LySubcontractOrder) -> None:
        settlement_status = str(getattr(order, "settlement_status", "") or "").strip().lower()
        if settlement_status == "settled":
            raise BusinessException(code=SUBCONTRACT_SETTLEMENT_LOCKED, message="外发单已结算锁定")
        allowed = {"draft", "issued", "processing", "waiting_receive"}
        if str(order.status) not in allowed:
            raise BusinessException(code=SUBCONTRACT_STATUS_INVALID, message="当前状态不允许发料")

    def _ensure_receive_allowed(self, *, order: LySubcontractOrder) -> None:
        settlement_status = str(getattr(order, "settlement_status", "") or "").strip().lower()
        if settlement_status == "settled":
            raise BusinessException(code=SUBCONTRACT_SETTLEMENT_LOCKED, message="外发单已结算锁定")
        allowed = {"issued", "processing", "waiting_receive", "waiting_inspection"}
        if str(order.status) not in allowed:
            raise BusinessException(code=SUBCONTRACT_STATUS_INVALID, message="当前状态不允许登记回料")

    def _ensure_inspect_allowed(self, *, order: LySubcontractOrder) -> None:
        allowed = {"waiting_inspection", "waiting_receive"}
        if str(order.status) not in allowed:
            raise BusinessException(code=SUBCONTRACT_INSPECTION_NOT_READY, message="当前状态不允许验货")

    def _must_get_receipt_batch_rows(
        self,
        *,
        order_id: int,
        receipt_batch_no: str,
    ) -> list[LySubcontractReceipt]:
        try:
            query = (
                self.session.query(LySubcontractReceipt)
                .filter(
                    LySubcontractReceipt.subcontract_id == order_id,
                    LySubcontractReceipt.receipt_batch_no == receipt_batch_no,
                )
                .order_by(LySubcontractReceipt.id.asc())
            )
            if not self._is_sqlite:
                query = query.with_for_update()
            rows = query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not rows:
            raise BusinessException(code=SUBCONTRACT_RECEIPT_BATCH_NOT_FOUND, message="回料批次不存在或不属于当前外发单")
        return rows

    def _find_inspection_by_idempotency(
        self,
        *,
        order_id: int,
        idempotency_key: str,
    ) -> LySubcontractInspection | None:
        try:
            return (
                self.session.query(LySubcontractInspection)
                .filter(
                    LySubcontractInspection.subcontract_id == order_id,
                    LySubcontractInspection.idempotency_key == idempotency_key,
                )
                .order_by(LySubcontractInspection.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _inspection_result_from_row(self, *, row: LySubcontractInspection, status: str) -> InspectData:
        return InspectData(
            inspection_no=str(row.inspection_no or ""),
            receipt_batch_no=str(row.receipt_batch_no or ""),
            inspected_qty=Decimal(str(row.inspected_qty or "0")),
            accepted_qty=Decimal(str(row.accepted_qty or "0")),
            rejected_qty=Decimal(str(row.rejected_qty or "0")),
            rejected_rate=Decimal(str(row.rejected_rate or "0")),
            gross_amount=Decimal(str(row.gross_amount or "0")),
            deduction_amount=Decimal(str(row.deduction_amount or "0")),
            net_amount=Decimal(str(row.net_amount or "0")),
            status=status,
        )

    def _inspected_qty_total(self, *, order_id: int, receipt_batch_no: str) -> Decimal:
        try:
            total = (
                self.session.query(func.sum(LySubcontractInspection.inspected_qty))
                .filter(
                    LySubcontractInspection.subcontract_id == order_id,
                    LySubcontractInspection.receipt_batch_no == receipt_batch_no,
                )
                .scalar()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return Decimal(str(total or "0"))

    def _inspection_totals(self, *, order_id: int) -> dict[str, Decimal]:
        try:
            row = (
                self.session.query(
                    func.sum(LySubcontractInspection.inspected_qty),
                    func.sum(LySubcontractInspection.rejected_qty),
                    func.sum(LySubcontractInspection.accepted_qty),
                    func.sum(LySubcontractInspection.gross_amount),
                    func.sum(LySubcontractInspection.deduction_amount),
                    func.sum(LySubcontractInspection.net_amount),
                )
                .filter(LySubcontractInspection.subcontract_id == order_id)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            return {
                "inspected_qty": Decimal("0"),
                "rejected_qty": Decimal("0"),
                "accepted_qty": Decimal("0"),
                "gross_amount": Decimal("0"),
                "deduction_amount": Decimal("0"),
                "net_amount": Decimal("0"),
            }
        return {
            "inspected_qty": Decimal(str(row[0] or "0")),
            "rejected_qty": Decimal(str(row[1] or "0")),
            "accepted_qty": Decimal(str(row[2] or "0")),
            "gross_amount": Decimal(str(row[3] or "0")),
            "deduction_amount": Decimal(str(row[4] or "0")),
            "net_amount": Decimal(str(row[5] or "0")),
        }

    def _next_status_after_inspection(
        self,
        *,
        planned_qty: Decimal,
        total_received_qty: Decimal,
        total_inspected_qty: Decimal,
    ) -> str:
        if total_inspected_qty > total_received_qty:
            raise BusinessException(code=SUBCONTRACT_INSPECTION_QTY_EXCEEDED, message="累计验货数量不能超过累计回料数量")
        if total_inspected_qty < total_received_qty:
            return "waiting_inspection"
        if total_received_qty < planned_qty:
            return "waiting_receive"
        return "completed"

    def _receipt_warehouse_from_rows(self, *, receipt_rows: list[LySubcontractReceipt]) -> str | None:
        for row in receipt_rows:
            text = str(row.receipt_warehouse or "").strip()
            if text:
                return text
        return None

    def _resolve_subcontract_rate(self, *, bom_id: int, process_name: str) -> Decimal:
        try:
            row = (
                self.session.query(
                    LyBomOperation.subcontract_cost_per_piece,
                    LyBomOperation.wage_rate,
                )
                .filter(
                    and_(
                        LyBomOperation.bom_id == bom_id,
                        LyBomOperation.process_name == process_name,
                        LyBomOperation.is_subcontract.is_(True),
                    )
                )
                .order_by(LyBomOperation.id.asc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            raise BusinessException(code=SUBCONTRACT_RATE_REQUIRED, message="外发单价缺失")
        subcontract_cost, wage_rate = row
        subcontract_rate = Decimal(str(subcontract_cost or "0"))
        if subcontract_rate <= Decimal("0"):
            subcontract_rate = Decimal(str(wage_rate or "0"))
        if subcontract_rate <= Decimal("0"):
            raise BusinessException(code=SUBCONTRACT_RATE_REQUIRED, message="外发单价缺失")
        return subcontract_rate

    def _effective_subcontract_rate(self, *, order: LySubcontractOrder) -> Decimal:
        explicit = Decimal(str(getattr(order, "subcontract_rate", "0") or "0"))
        if explicit > Decimal("0"):
            return explicit
        return self._resolve_subcontract_rate(bom_id=int(order.bom_id), process_name=str(order.process_name))

    @staticmethod
    def _quantize_ratio(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _quantize_money(value: Decimal) -> Decimal:
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _build_inspection_idempotency_payload(
        self,
        *,
        order: LySubcontractOrder,
        payload: InspectRequest,
        receipt_batch_no: str,
        inspected_qty: Decimal,
        rejected_qty: Decimal,
        deduction_amount_per_piece: Decimal,
    ) -> dict[str, object]:
        return {
            "stock_action": "inspection",
            "subcontract_id": int(order.id),
            "subcontract_no": str(order.subcontract_no),
            "company": self._normalize_company(order.company),
            "supplier": str(order.supplier),
            "item_code": str(order.item_code),
            "receipt_batch_no": receipt_batch_no,
            "inspected_qty": str(inspected_qty),
            "rejected_qty": str(rejected_qty),
            "deduction_amount_per_piece": str(deduction_amount_per_piece),
            "remark": payload.remark.strip() if payload.remark else None,
        }

    def _next_inspection_no(self, *, order_id: int) -> str:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"SIN-{order_id}-{now}"

    def _load_bom_material_plan(self, *, order: LySubcontractOrder) -> dict[str, dict[str, Decimal | str]]:
        try:
            rows = (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == order.bom_id)
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        plan: dict[str, dict[str, Decimal | str]] = {}
        planned_qty = Decimal(str(order.planned_qty))
        for row in rows:
            item_code = str(row.material_item_code or "").strip()
            if not item_code:
                continue
            qty_per_piece = Decimal(str(row.qty_per_piece or "0"))
            loss_rate = Decimal(str(row.loss_rate or "0"))
            required_total = planned_qty * qty_per_piece * (Decimal("1") + loss_rate)
            if item_code not in plan:
                plan[item_code] = {"required_qty": Decimal("0"), "uom": str(row.uom or "").strip() or "Nos"}
            plan[item_code]["required_qty"] = Decimal(str(plan[item_code]["required_qty"])) + required_total
        return plan

    def _issued_qty_summary(self, *, order_id: int) -> dict[str, Decimal]:
        try:
            rows = (
                self.session.query(
                    LySubcontractMaterial.material_item_code,
                    func.sum(LySubcontractMaterial.issued_qty),
                )
                .filter(LySubcontractMaterial.subcontract_id == order_id)
                .group_by(LySubcontractMaterial.material_item_code)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        summary: dict[str, Decimal] = {}
        for material_item_code, issued_qty in rows:
            key = str(material_item_code or "").strip()
            if key:
                summary[key] = Decimal(str(issued_qty or "0"))
        return summary

    def _resolve_issue_lines(
        self,
        *,
        materials: list | None,
        bom_plan: dict[str, dict[str, Decimal | str]],
        issued_summary: dict[str, Decimal],
    ) -> list[dict[str, Decimal | str]]:
        if not bom_plan:
            raise BusinessException(code=SUBCONTRACT_MATERIAL_NOT_IN_BOM, message="BOM 未配置可发料物料")

        requested_rows = materials or []
        if not requested_rows:
            auto_rows: list[dict[str, Decimal | str]] = []
            for item_code, plan_row in bom_plan.items():
                required_qty = Decimal(str(plan_row["required_qty"]))
                issued_qty = Decimal(str(issued_summary.get(item_code, Decimal("0"))))
                remaining = required_qty - issued_qty
                if remaining <= Decimal("0"):
                    continue
                auto_rows.append(
                    {
                        "material_item_code": item_code,
                        "required_qty": required_qty,
                        "issued_qty": remaining,
                        "uom": str(plan_row["uom"]),
                    }
                )
            return auto_rows

        lines: list[dict[str, Decimal | str]] = []
        for row in requested_rows:
            item_code = str(row.material_item_code).strip()
            if item_code not in bom_plan:
                raise BusinessException(
                    code=SUBCONTRACT_MATERIAL_NOT_IN_BOM,
                    message=f"发料物料不在 BOM 展开范围内: {item_code}",
                )
            required_qty = Decimal(str(bom_plan[item_code]["required_qty"]))
            already_issued = Decimal(str(issued_summary.get(item_code, Decimal("0"))))
            line_issue_qty = Decimal(str(row.issued_qty))
            remaining = required_qty - already_issued
            if line_issue_qty <= Decimal("0") or line_issue_qty > remaining:
                raise BusinessException(
                    code=SUBCONTRACT_MATERIAL_QTY_EXCEEDED,
                    message=f"发料数量超过剩余可发数量: {item_code}",
                )
            lines.append(
                {
                    "material_item_code": item_code,
                    "required_qty": required_qty,
                    "issued_qty": line_issue_qty,
                    "uom": str(bom_plan[item_code]["uom"]),
                }
            )
        return lines

    def _build_issue_stock_payload(
        self,
        *,
        order: LySubcontractOrder,
        warehouse: str,
        issue_batch_no: str,
        issue_lines: list[dict[str, Decimal | str]],
        request_id: str,
        outbox_id_placeholder: int,
        event_key_placeholder: str,
    ) -> dict[str, object]:
        return {
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Issue",
            "company": self._normalize_company(order.company),
            "custom_ly_subcontract_no": str(order.subcontract_no),
            "custom_ly_subcontract_outbox_id": outbox_id_placeholder,
            "custom_ly_outbox_event_key": event_key_placeholder,
            "custom_ly_stock_action": "issue",
            "custom_ly_request_id": request_id,
            "issue_batch_no": issue_batch_no,
            "items": [
                {
                    "item_code": str(line["material_item_code"]),
                    "qty": str(line["issued_qty"]),
                    "uom": str(line["uom"] or "Nos"),
                    "s_warehouse": warehouse,
                }
                for line in issue_lines
            ],
        }

    def _build_issue_idempotency_payload(
        self,
        *,
        order: LySubcontractOrder,
        warehouse: str,
        materials: list | None,
    ) -> dict[str, object]:
        """Build stable request-semantic payload for idempotency hash.

        Must not depend on mutable runtime facts such as current remaining qty,
        issue_batch_no, outbox id/event key, or request_id.
        """
        normalized_materials: list[dict[str, str]] = []
        if materials:
            for row in materials:
                material_item_code = str(getattr(row, "material_item_code", "")).strip()
                required_qty = str(getattr(row, "required_qty", "")).strip()
                issued_qty = str(getattr(row, "issued_qty", "")).strip()
                normalized_materials.append(
                    {
                        "material_item_code": material_item_code,
                        "required_qty": required_qty,
                        "issued_qty": issued_qty,
                    }
                )
        normalized_materials = sorted(
            normalized_materials,
            key=lambda x: (
                x.get("material_item_code", ""),
                x.get("issued_qty", ""),
                x.get("required_qty", ""),
            ),
        )
        return {
            "stock_action": "issue",
            "subcontract_id": int(order.id),
            "subcontract_no": str(order.subcontract_no),
            "company": self._normalize_company(order.company),
            "supplier": str(order.supplier),
            "item_code": str(order.item_code),
            "warehouse": warehouse,
            "materials_auto": not bool(materials),
            "materials": normalized_materials,
        }

    def _build_receive_stock_payload(
        self,
        *,
        order: LySubcontractOrder,
        receipt_warehouse: str,
        receipt_batch_no: str,
        received_qty: Decimal,
        payload: ReceiveRequest,
        request_id: str,
        outbox_id_placeholder: int,
        event_key_placeholder: str,
    ) -> dict[str, object]:
        return {
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Receipt",
            "company": self._normalize_company(order.company),
            "custom_ly_subcontract_no": str(order.subcontract_no),
            "custom_ly_subcontract_outbox_id": outbox_id_placeholder,
            "custom_ly_outbox_event_key": event_key_placeholder,
            "custom_ly_stock_action": "receipt",
            "custom_ly_request_id": request_id,
            "receipt_batch_no": receipt_batch_no,
            "items": [
                {
                    "item_code": str(order.item_code),
                    "qty": str(received_qty),
                    "uom": (payload.uom.strip() if payload.uom else "Nos"),
                    "t_warehouse": receipt_warehouse,
                    "batch_no": (payload.batch_no.strip() if payload.batch_no else None),
                }
            ],
        }

    def _build_receive_idempotency_payload(
        self,
        *,
        order: LySubcontractOrder,
        receipt_warehouse: str,
        received_qty: Decimal,
        payload: ReceiveRequest,
    ) -> dict[str, object]:
        return {
            "stock_action": "receipt",
            "subcontract_id": int(order.id),
            "subcontract_no": str(order.subcontract_no),
            "company": self._normalize_company(order.company),
            "supplier": str(order.supplier),
            "item_code": str(order.item_code),
            "receipt_warehouse": receipt_warehouse,
            "received_qty": str(received_qty),
            "color": payload.color.strip() if payload.color else None,
            "size": payload.size.strip() if payload.size else None,
            "batch_no": payload.batch_no.strip() if payload.batch_no else None,
            "uom": payload.uom.strip() if payload.uom else "Nos",
        }

    def _received_qty_total(self, *, order_id: int) -> Decimal:
        try:
            total = (
                self.session.query(func.sum(LySubcontractReceipt.received_qty))
                .filter(LySubcontractReceipt.subcontract_id == order_id)
                .scalar()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return Decimal(str(total or "0"))

    def _existing_issue_batch_no(self, *, outbox_id: int) -> str | None:
        try:
            row = (
                self.session.query(LySubcontractMaterial.issue_batch_no)
                .filter(LySubcontractMaterial.stock_outbox_id == outbox_id)
                .order_by(LySubcontractMaterial.id.asc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            return None
        value = row[0]
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _next_issue_batch_no(self, *, order_id: int) -> str:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"SIB-{order_id}-{now}"

    def _existing_receipt_batch_no(self, *, outbox_id: int) -> str | None:
        try:
            row = (
                self.session.query(LySubcontractReceipt.receipt_batch_no)
                .filter(LySubcontractReceipt.stock_outbox_id == outbox_id)
                .order_by(LySubcontractReceipt.id.asc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            return None
        value = row[0]
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _next_receipt_batch_no(self, *, order_id: int) -> str:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"SRB-{order_id}-{now}"

    def _log_status(
        self,
        *,
        order_id: int,
        from_status: str,
        to_status: str,
        operator: str,
        company: str | None = None,
    ) -> None:
        log_row = LySubcontractStatusLog(
            subcontract_id=order_id,
            company=company,
            from_status=from_status,
            to_status=to_status,
            operator=operator,
        )
        if self._is_sqlite:
            log_row.id = self._next_id(LySubcontractStatusLog)
        self.session.add(log_row)

    def _next_id(self, model: type) -> int:
        try:
            current = self.session.query(func.max(model.id)).scalar() or 0
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return int(current) + 1

    @staticmethod
    def _normalize_company(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None

    @staticmethod
    def _is_missing_company(value: str | None) -> bool:
        return SubcontractService._normalize_company(value) is None

    def _ensure_scope_ready(self, order: LySubcontractOrder) -> None:
        status = str(order.resource_scope_status or "").strip().lower()
        if status == "blocked_scope":
            code = str(order.scope_error_code or "").strip()
            if code in {SUBCONTRACT_COMPANY_UNRESOLVED, SUBCONTRACT_COMPANY_AMBIGUOUS}:
                raise BusinessException(code=SUBCONTRACT_SCOPE_BLOCKED, message="外发单资源范围已被阻断")
            raise BusinessException(code=SUBCONTRACT_SCOPE_BLOCKED, message="外发单资源范围已被阻断")
        if self._is_missing_company(order.company):
            raise BusinessException(code=SUBCONTRACT_SCOPE_BLOCKED, message="外发单缺少 company 资源范围")
