"""Business service for production planning module (TASK-004A)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import PRODUCTION_BOM_ITEM_MISMATCH
from app.core.error_codes import PRODUCTION_BOM_NOT_ACTIVE
from app.core.error_codes import PRODUCTION_BOM_NOT_FOUND
from app.core.error_codes import PRODUCTION_IDEMPOTENCY_CONFLICT
from app.core.error_codes import PRODUCTION_IDEMPOTENCY_KEY_REQUIRED
from app.core.error_codes import PRODUCTION_PLANNED_QTY_EXCEEDED
from app.core.error_codes import PRODUCTION_SO_CLOSED_OR_CANCELLED
from app.core.error_codes import PRODUCTION_SO_ITEM_AMBIGUOUS
from app.core.error_codes import PRODUCTION_SO_ITEM_NOT_FOUND
from app.core.error_codes import PRODUCTION_SO_NOT_APPROVED
from app.core.error_codes import PRODUCTION_SO_NOT_FOUND
from app.core.error_codes import PRODUCTION_START_DATE_REQUIRED
from app.core.error_codes import PRODUCTION_WAREHOUSE_REQUIRED
from app.core.error_codes import PRODUCTION_WORK_ORDER_SYNC_FAILED
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.production import LyProductionStatusLog
from app.models.production import LyProductionWorkOrderLink
from app.schemas.production import ProductionCreateWorkOrderData
from app.schemas.production import ProductionCreateWorkOrderRequest
from app.schemas.production import ProductionJobCardLinkItem
from app.schemas.production import ProductionMaterialCheckData
from app.schemas.production import ProductionMaterialCheckRequest
from app.schemas.production import ProductionPlanCreateData
from app.schemas.production import ProductionPlanCreateRequest
from app.schemas.production import ProductionPlanDetailData
from app.schemas.production import ProductionPlanListData
from app.schemas.production import ProductionPlanListItem
from app.schemas.production import ProductionPlanMaterialSnapshotItem
from app.schemas.production import ProductionPlanQuery
from app.schemas.production import ProductionSyncJobCardsData
from app.schemas.production import ProductionWorkOrderOutboxSummary
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.erpnext_production_adapter import ERPNextSalesOrderItem
from app.services.production_work_order_outbox_service import ProductionWorkOrderOutboxService


class ProductionService:
    """Production plan service."""

    def __init__(self, *, session: Session, erp_adapter: ERPNextProductionAdapter):
        self.session = session
        self.erp_adapter = erp_adapter
        self.outbox_service = ProductionWorkOrderOutboxService(session=session)

    def create_plan(
        self,
        *,
        payload: ProductionPlanCreateRequest,
        operator: str,
    ) -> ProductionPlanCreateData:
        sales_order, target_item, company = self._load_sales_order_context(payload=payload)

        bom = self._resolve_bom(item_code=target_item.item_code, bom_id=payload.bom_id)
        if str(bom.item_code).strip() != target_item.item_code:
            raise BusinessException(code=PRODUCTION_BOM_ITEM_MISMATCH, message="BOM 与 Sales Order 行 item 不一致")

        planned_qty = Decimal(str(payload.planned_qty))
        remaining_qty = self._remaining_plannable_qty(sales_order_item=target_item)
        if planned_qty > remaining_qty:
            raise BusinessException(code=PRODUCTION_PLANNED_QTY_EXCEEDED, message="计划数量超过可计划剩余数量")

        request_hash = self._build_request_hash(
            {
                "sales_order": sales_order.name,
                "sales_order_item": target_item.name,
                "item_code": target_item.item_code,
                "bom_id": int(bom.id),
                "planned_qty": planned_qty,
                "planned_start_date": (payload.planned_start_date.isoformat() if payload.planned_start_date else None),
                "company": company,
            }
        )

        existing = (
            self.session.query(LyProductionPlan)
            .filter(
                LyProductionPlan.company == company,
                LyProductionPlan.idempotency_key == payload.idempotency_key.strip(),
            )
            .first()
        )
        if existing is not None:
            if str(existing.request_hash) == request_hash:
                return ProductionPlanCreateData(
                    plan_id=int(existing.id),
                    plan_no=str(existing.plan_no),
                    status=str(existing.status),
                    company=str(existing.company),
                )
            raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")

        plan_no = self._next_plan_no()
        row = LyProductionPlan(
            plan_no=plan_no,
            company=company,
            sales_order=sales_order.name,
            sales_order_item=target_item.name,
            customer=sales_order.customer,
            item_code=target_item.item_code,
            bom_id=int(bom.id),
            bom_version=str(bom.version_no) if bom.version_no is not None else None,
            planned_qty=planned_qty,
            planned_start_date=payload.planned_start_date,
            status="planned",
            idempotency_key=payload.idempotency_key.strip(),
            request_hash=request_hash,
            created_by=operator,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        self._log_status(
            plan_id=int(row.id),
            from_status="planned",
            to_status="planned",
            action="plan_create",
            operator=operator,
        )

        return ProductionPlanCreateData(
            plan_id=int(row.id),
            plan_no=plan_no,
            status="planned",
            company=company,
        )

    def resolve_create_scope(self, *, payload: ProductionPlanCreateRequest) -> tuple[str, str]:
        """Resolve company/item scope for create-plan permission checks."""
        _, target_item, company = self._load_sales_order_context(payload=payload)
        return company, str(target_item.item_code)

    def list_plans(
        self,
        *,
        query: ProductionPlanQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionPlanListData:
        try:
            sql = self.session.query(LyProductionPlan)
            if query.sales_order:
                sql = sql.filter(LyProductionPlan.sales_order == query.sales_order)
            if query.item_code:
                sql = sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.company:
                sql = sql.filter(LyProductionPlan.company == query.company)
            if query.status:
                sql = sql.filter(LyProductionPlan.status == query.status)

            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionPlanListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))

            if readable_companies is not None:
                if not readable_companies:
                    return ProductionPlanListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))

            total = sql.with_entities(func.count(LyProductionPlan.id)).scalar() or 0
            rows = (
                sql.order_by(LyProductionPlan.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        latest_map = self.outbox_service.latest_by_plan_ids(plan_ids=[int(row.id) for row in rows])

        items: list[ProductionPlanListItem] = []
        for row in rows:
            summary = None
            latest = latest_map.get(int(row.id))
            if latest is not None:
                summary = ProductionWorkOrderOutboxSummary(
                    outbox_id=int(latest.id),
                    status=str(latest.status),
                    erpnext_work_order=(str(latest.erpnext_work_order) if latest.erpnext_work_order else None),
                    error_code=(str(latest.last_error_code) if latest.last_error_code else None),
                )

            items.append(
                ProductionPlanListItem(
                    id=int(row.id),
                    plan_no=str(row.plan_no),
                    company=str(row.company),
                    sales_order=str(row.sales_order),
                    sales_order_item=str(row.sales_order_item),
                    customer=(str(row.customer) if row.customer else None),
                    item_code=str(row.item_code),
                    bom_id=int(row.bom_id),
                    bom_version=(str(row.bom_version) if row.bom_version else None),
                    planned_qty=Decimal(str(row.planned_qty)),
                    planned_start_date=row.planned_start_date,
                    status=str(row.status),
                    latest_work_order_outbox=summary,
                    created_at=row.created_at,
                )
            )

        return ProductionPlanListData(items=items, total=int(total), page=query.page, page_size=query.page_size)

    def get_plan_detail(self, *, plan_id: int) -> ProductionPlanDetailData:
        plan = self._must_get_plan(plan_id=plan_id)
        try:
            materials = (
                self.session.query(LyProductionPlanMaterial)
                .filter(LyProductionPlanMaterial.plan_id == int(plan.id))
                .order_by(LyProductionPlanMaterial.id.asc())
                .all()
            )
            work_order_link = (
                self.session.query(LyProductionWorkOrderLink)
                .filter(LyProductionWorkOrderLink.plan_id == int(plan.id))
                .first()
            )
            cards = (
                self.session.query(LyProductionJobCardLink)
                .filter(LyProductionJobCardLink.plan_id == int(plan.id))
                .order_by(LyProductionJobCardLink.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        latest = self.outbox_service.latest_by_plan_ids(plan_ids=[int(plan.id)]).get(int(plan.id))
        summary = None
        if latest is not None:
            summary = ProductionWorkOrderOutboxSummary(
                outbox_id=int(latest.id),
                status=str(latest.status),
                erpnext_work_order=(str(latest.erpnext_work_order) if latest.erpnext_work_order else None),
                error_code=(str(latest.last_error_code) if latest.last_error_code else None),
            )

        return ProductionPlanDetailData(
            id=int(plan.id),
            plan_no=str(plan.plan_no),
            company=str(plan.company),
            sales_order=str(plan.sales_order),
            sales_order_item=str(plan.sales_order_item),
            customer=(str(plan.customer) if plan.customer else None),
            item_code=str(plan.item_code),
            bom_id=int(plan.bom_id),
            bom_version=(str(plan.bom_version) if plan.bom_version else None),
            planned_qty=Decimal(str(plan.planned_qty)),
            planned_start_date=plan.planned_start_date,
            status=str(plan.status),
            work_order=(str(work_order_link.work_order) if work_order_link and work_order_link.work_order else None),
            erpnext_docstatus=(int(work_order_link.erpnext_docstatus) if work_order_link and work_order_link.erpnext_docstatus is not None else None),
            erpnext_status=(str(work_order_link.erpnext_status) if work_order_link and work_order_link.erpnext_status else None),
            sync_status=(str(work_order_link.sync_status) if work_order_link and work_order_link.sync_status else None),
            last_synced_at=(work_order_link.last_synced_at if work_order_link else None),
            latest_work_order_outbox=summary,
            material_snapshots=[
                ProductionPlanMaterialSnapshotItem(
                    bom_item_id=(int(row.bom_item_id) if row.bom_item_id is not None else None),
                    material_item_code=str(row.material_item_code),
                    warehouse=(str(row.warehouse) if getattr(row, "warehouse", None) is not None else None),
                    qty_per_piece=Decimal(str(row.qty_per_piece)),
                    loss_rate=Decimal(str(row.loss_rate)),
                    required_qty=Decimal(str(row.required_qty)),
                    available_qty=Decimal(str(row.available_qty)),
                    shortage_qty=Decimal(str(row.shortage_qty)),
                    checked_at=getattr(row, "checked_at", None),
                )
                for row in materials
            ],
            job_cards=[
                ProductionJobCardLinkItem(
                    job_card=str(row.job_card),
                    operation=(str(row.operation) if row.operation else None),
                    operation_sequence=(int(row.operation_sequence) if row.operation_sequence is not None else None),
                    company=(str(row.company) if getattr(row, "company", None) is not None else None),
                    item_code=(str(row.item_code) if getattr(row, "item_code", None) is not None else None),
                    expected_qty=Decimal(str(row.expected_qty)),
                    completed_qty=Decimal(str(row.completed_qty)),
                    erpnext_status=(str(row.erpnext_status) if row.erpnext_status else None),
                    synced_at=getattr(row, "synced_at", None),
                )
                for row in cards
            ],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    def material_check(
        self,
        *,
        plan_id: int,
        operator: str,
        payload: ProductionMaterialCheckRequest,
    ) -> ProductionMaterialCheckData:
        plan = self._must_get_plan(plan_id=plan_id)
        warehouse = self._require_non_blank(
            payload.warehouse,
            code=PRODUCTION_WAREHOUSE_REQUIRED,
            message="warehouse 不能为空",
        )

        try:
            bom_rows = (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == int(plan.bom_id))
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        try:
            self.session.query(LyProductionPlanMaterial).filter(LyProductionPlanMaterial.plan_id == int(plan.id)).delete()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        snapshot_items: list[ProductionPlanMaterialSnapshotItem] = []
        checked_at = datetime.utcnow()
        planned_qty = Decimal(str(plan.planned_qty))
        for row in bom_rows:
            qty_per_piece = Decimal(str(row.qty_per_piece))
            loss_rate = Decimal(str(row.loss_rate or 0))
            required_qty = (planned_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
            available_qty = Decimal("0")
            shortage_qty = max(Decimal("0"), required_qty - available_qty)

            self.session.add(
                LyProductionPlanMaterial(
                    plan_id=int(plan.id),
                    bom_item_id=int(row.id),
                    material_item_code=str(row.material_item_code),
                    warehouse=warehouse,
                    qty_per_piece=qty_per_piece,
                    loss_rate=loss_rate,
                    required_qty=required_qty,
                    available_qty=available_qty,
                    shortage_qty=shortage_qty,
                    checked_at=checked_at,
                )
            )
            snapshot_items.append(
                ProductionPlanMaterialSnapshotItem(
                    bom_item_id=int(row.id),
                    material_item_code=str(row.material_item_code),
                    warehouse=warehouse,
                    qty_per_piece=qty_per_piece,
                    loss_rate=loss_rate,
                    required_qty=required_qty,
                    available_qty=available_qty,
                    shortage_qty=shortage_qty,
                    checked_at=checked_at,
                )
            )

        previous = str(plan.status)
        plan.status = "material_checked"
        self._log_status(
            plan_id=int(plan.id),
            from_status=previous,
            to_status="material_checked",
            action="material_check",
            operator=operator,
        )

        return ProductionMaterialCheckData(
            plan_id=int(plan.id),
            snapshot_count=len(snapshot_items),
            items=snapshot_items,
        )

    def create_work_order_outbox(
        self,
        *,
        plan_id: int,
        payload: ProductionCreateWorkOrderRequest,
        operator: str,
        request_id: str,
    ) -> ProductionCreateWorkOrderData:
        plan = self._must_get_plan(plan_id=plan_id)
        fg_warehouse = self._require_non_blank(
            payload.fg_warehouse,
            code=PRODUCTION_WAREHOUSE_REQUIRED,
            message="fg_warehouse 不能为空",
        )
        wip_warehouse = self._require_non_blank(
            payload.wip_warehouse,
            code=PRODUCTION_WAREHOUSE_REQUIRED,
            message="wip_warehouse 不能为空",
        )
        if payload.start_date is None:
            raise BusinessException(code=PRODUCTION_START_DATE_REQUIRED, message="start_date 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )

        link = (
            self.session.query(LyProductionWorkOrderLink)
            .filter(LyProductionWorkOrderLink.plan_id == int(plan.id))
            .first()
        )
        if link is not None and str(link.sync_status) == "succeeded" and link.work_order:
            existing = self.outbox_service.find_existing(
                plan_id=int(plan.id),
                action=ProductionWorkOrderOutboxService.ACTION_CREATE_WORK_ORDER,
            )
            if existing is not None:
                return ProductionCreateWorkOrderData(
                    plan_id=int(plan.id),
                    outbox_id=int(existing.id),
                    event_key=str(existing.event_key),
                    sync_status=str(existing.status),
                    work_order=(str(existing.erpnext_work_order) if existing.erpnext_work_order else str(link.work_order)),
                )
            return ProductionCreateWorkOrderData(
                plan_id=int(plan.id),
                outbox_id=0,
                event_key="",
                sync_status="succeeded",
                work_order=str(link.work_order),
            )

        bom = self.session.query(LyApparelBom).filter(LyApparelBom.id == int(plan.bom_id)).first()
        if bom is None:
            raise BusinessException(code=PRODUCTION_BOM_NOT_FOUND, message="BOM 不存在")

        payload_json: dict[str, Any] = {
            "doctype": "Work Order",
            "production_item": str(plan.item_code),
            "qty": str(Decimal(str(plan.planned_qty))),
            "bom_no": str(bom.bom_no),
            "company": str(plan.company),
            "sales_order": str(plan.sales_order),
            "sales_order_item": str(plan.sales_order_item),
            "custom_ly_plan_id": str(plan.id),
            "custom_ly_plan_no": str(plan.plan_no),
            "fg_warehouse": fg_warehouse,
            "wip_warehouse": wip_warehouse,
            "planned_start_date": payload.start_date.isoformat(),
        }
        payload_hash = self.outbox_service.build_payload_hash(payload_json)

        existing_by_idempotency = self.outbox_service.find_existing_by_idempotency(
            plan_id=int(plan.id),
            action=ProductionWorkOrderOutboxService.ACTION_CREATE_WORK_ORDER,
            idempotency_key=idempotency_key,
        )
        if existing_by_idempotency is not None:
            existing_hash = str(existing_by_idempotency.payload_hash or "")
            if existing_hash != payload_hash:
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")
            return ProductionCreateWorkOrderData(
                plan_id=int(plan.id),
                outbox_id=int(existing_by_idempotency.id),
                event_key=str(existing_by_idempotency.event_key),
                sync_status=str(existing_by_idempotency.status),
                work_order=(str(existing_by_idempotency.erpnext_work_order) if existing_by_idempotency.erpnext_work_order else None),
            )

        existing_active = self.outbox_service.find_existing(
            plan_id=int(plan.id),
            action=ProductionWorkOrderOutboxService.ACTION_CREATE_WORK_ORDER,
            statuses=["pending", "processing"],
        )
        if existing_active is not None:
            return ProductionCreateWorkOrderData(
                plan_id=int(plan.id),
                outbox_id=int(existing_active.id),
                event_key=str(existing_active.event_key),
                sync_status=str(existing_active.status),
                work_order=(str(existing_active.erpnext_work_order) if existing_active.erpnext_work_order else None),
            )

        outbox = self.outbox_service.create_outbox(
            plan_id=int(plan.id),
            company=str(plan.company),
            item_code=str(plan.item_code),
            idempotency_key=idempotency_key,
            payload_json=payload_json,
            payload_hash=payload_hash,
            request_id=request_id,
            operator=operator,
        )

        previous = str(plan.status)
        if previous != "work_order_pending":
            plan.status = "work_order_pending"
            self._log_status(
                plan_id=int(plan.id),
                from_status=previous,
                to_status="work_order_pending",
                action="create_work_order",
                operator=operator,
                request_id=request_id,
            )

        return ProductionCreateWorkOrderData(
            plan_id=int(plan.id),
            outbox_id=int(outbox.id),
            event_key=str(outbox.event_key),
            sync_status=str(outbox.status),
            work_order=(str(outbox.erpnext_work_order) if outbox.erpnext_work_order else None),
        )

    def sync_job_cards(
        self,
        *,
        work_order: str,
        operator: str,
        request_id: str,
    ) -> ProductionSyncJobCardsData:
        link = (
            self.session.query(LyProductionWorkOrderLink)
            .filter(LyProductionWorkOrderLink.work_order == work_order)
            .first()
        )
        if link is None:
            raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="Work Order 映射不存在")

        cards = self.erp_adapter.list_job_cards(work_order=work_order)
        plan = self._must_get_plan(plan_id=int(link.plan_id))

        upserted: list[ProductionJobCardLinkItem] = []
        for card in cards:
            row = (
                self.session.query(LyProductionJobCardLink)
                .filter(LyProductionJobCardLink.job_card == card.name)
                .first()
            )
            if row is None:
                row = LyProductionJobCardLink(
                    plan_id=int(plan.id),
                    work_order=work_order,
                    job_card=card.name,
                    company=str(plan.company),
                    item_code=str(plan.item_code),
                )
                self.session.add(row)

            row.plan_id = int(plan.id)
            row.work_order = work_order
            row.company = str(plan.company)
            row.item_code = str(plan.item_code)
            row.operation = card.operation
            row.operation_sequence = card.operation_sequence
            row.expected_qty = card.expected_qty
            row.completed_qty = card.completed_qty
            row.erpnext_status = card.status
            row.synced_at = datetime.utcnow()

            upserted.append(
                ProductionJobCardLinkItem(
                    job_card=card.name,
                    operation=card.operation,
                    operation_sequence=card.operation_sequence,
                    company=str(plan.company),
                    item_code=str(plan.item_code),
                    expected_qty=card.expected_qty,
                    completed_qty=card.completed_qty,
                    erpnext_status=card.status,
                    synced_at=row.synced_at,
                )
            )

        self._log_status(
            plan_id=int(plan.id),
            from_status=str(plan.status),
            to_status=str(plan.status),
            action="sync_job_cards",
            operator=operator,
            request_id=request_id,
        )

        return ProductionSyncJobCardsData(
            work_order=work_order,
            plan_id=int(plan.id),
            synced_count=len(upserted),
            items=upserted,
        )

    def get_plan_resource(self, *, plan_id: int) -> tuple[str, str]:
        """Return `(company, item_code)` for resource permission checks."""
        row = self._must_get_plan(plan_id=plan_id)
        return str(row.company), str(row.item_code)

    def get_work_order_resource(self, *, work_order: str) -> tuple[int, str, str]:
        """Return `(plan_id, company, item_code)` from work-order local mapping."""
        try:
            link = (
                self.session.query(LyProductionWorkOrderLink)
                .filter(LyProductionWorkOrderLink.work_order == work_order)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if link is None:
            raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="Work Order 映射不存在")
        plan = self._must_get_plan(plan_id=int(link.plan_id))
        return int(plan.id), str(plan.company), str(plan.item_code)

    def _must_get_plan(self, *, plan_id: int) -> LyProductionPlan:
        try:
            row = self.session.query(LyProductionPlan).filter(LyProductionPlan.id == int(plan_id)).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="生产计划不存在")
        return row

    def _resolve_bom(self, *, item_code: str, bom_id: int | None) -> LyApparelBom:
        try:
            if bom_id is not None:
                row = self.session.query(LyApparelBom).filter(LyApparelBom.id == int(bom_id)).first()
            else:
                row = (
                    self.session.query(LyApparelBom)
                    .filter(
                        LyApparelBom.item_code == item_code,
                        LyApparelBom.status == "active",
                        LyApparelBom.is_default.is_(True),
                    )
                    .order_by(LyApparelBom.id.desc())
                    .first()
                )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if row is None:
            raise BusinessException(code=PRODUCTION_BOM_NOT_FOUND, message="未找到可用 BOM")
        if str(row.status) != "active":
            raise BusinessException(code=PRODUCTION_BOM_NOT_ACTIVE, message="BOM 未生效")
        return row

    def _load_sales_order_context(
        self,
        *,
        payload: ProductionPlanCreateRequest,
    ) -> tuple[Any, ERPNextSalesOrderItem, str]:
        sales_order = self.erp_adapter.get_sales_order(sales_order=payload.sales_order.strip())
        if sales_order is None:
            raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="Sales Order 不存在")
        if int(sales_order.docstatus) != 1:
            raise BusinessException(code=PRODUCTION_SO_NOT_APPROVED, message="Sales Order 未提交")
        if (sales_order.status or "").strip().lower() in {"cancelled", "closed"}:
            raise BusinessException(code=PRODUCTION_SO_CLOSED_OR_CANCELLED, message="Sales Order 已关闭或已取消")

        target_item = self._select_sales_order_item(
            sales_items=list(sales_order.items),
            item_code=payload.item_code.strip(),
            sales_order_item=(payload.sales_order_item.strip() if payload.sales_order_item else None),
        )
        company = (sales_order.company or "").strip()
        if not company:
            raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="Sales Order company 缺失")
        return sales_order, target_item, company

    def _remaining_plannable_qty(self, *, sales_order_item: ERPNextSalesOrderItem) -> Decimal:
        try:
            local_sum = (
                self.session.query(func.coalesce(func.sum(LyProductionPlan.planned_qty), 0))
                .filter(
                    LyProductionPlan.sales_order_item == sales_order_item.name,
                    LyProductionPlan.status != "cancelled",
                )
                .scalar()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        base = Decimal(str(sales_order_item.qty))
        occupied = Decimal(str(local_sum or 0))
        remaining = base - occupied
        return remaining if remaining > 0 else Decimal("0")

    def _select_sales_order_item(
        self,
        *,
        sales_items: list[ERPNextSalesOrderItem],
        item_code: str,
        sales_order_item: str | None,
    ) -> ERPNextSalesOrderItem:
        if sales_order_item:
            for row in sales_items:
                if row.name == sales_order_item:
                    if row.item_code != item_code:
                        raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="Sales Order 行物料不匹配")
                    return row
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="Sales Order 行不存在")

        candidates = [row for row in sales_items if row.item_code == item_code]
        if not candidates:
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="Sales Order 未找到该 item")
        if len(candidates) > 1:
            raise BusinessException(code=PRODUCTION_SO_ITEM_AMBIGUOUS, message="Sales Order 存在多行相同 item，必须指定 sales_order_item")
        return candidates[0]

    def _log_status(
        self,
        *,
        plan_id: int,
        from_status: str,
        to_status: str,
        action: str,
        operator: str,
        request_id: str | None = None,
    ) -> None:
        self.session.add(
            LyProductionStatusLog(
                plan_id=plan_id,
                from_status=from_status,
                to_status=to_status,
                action=action,
                operator=operator,
                request_id=request_id,
            )
        )

    def _build_request_hash(self, payload: dict[str, Any]) -> str:
        canonical = self._canonicalize(payload)
        encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _require_non_blank(value: str | None, *, code: str, message: str) -> str:
        text = (value or "").strip()
        if not text:
            raise BusinessException(code=code, message=message)
        return text

    @staticmethod
    def _canonicalize(value: Any) -> Any:
        if isinstance(value, Decimal):
            normalized = value.normalize()
            text = format(normalized, "f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            return text or "0"
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return ProductionService._canonicalize(Decimal(str(value)))
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, dict):
            return {str(k): ProductionService._canonicalize(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
        if isinstance(value, (list, tuple, set)):
            return [ProductionService._canonicalize(v) for v in value]
        return str(value)

    @staticmethod
    def _next_plan_no() -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"PP-{ts}"
