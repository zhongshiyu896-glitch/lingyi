"""Business service for production planning module (TASK-004A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import os
import re
from typing import Any

from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import PRODUCTION_BOM_ITEM_MISMATCH
from app.core.error_codes import PRODUCTION_BOM_NOT_ACTIVE
from app.core.error_codes import PRODUCTION_BOM_NOT_FOUND
from app.core.error_codes import PRODUCTION_COMPANY_REQUIRED
from app.core.error_codes import PRODUCTION_FOLLOWUP_TEMPLATE_CONFLICT
from app.core.error_codes import PRODUCTION_FOLLOWUP_TEMPLATE_NOT_FOUND
from app.core.error_codes import PRODUCTION_IDEMPOTENCY_CONFLICT
from app.core.error_codes import PRODUCTION_IDEMPOTENCY_KEY_REQUIRED
from app.core.error_codes import PRODUCTION_MATERIAL_CHECK_STATUS_INVALID
from app.core.error_codes import PRODUCTION_MATERIAL_ISSUE_NOT_READY
from app.core.error_codes import PRODUCTION_PLANNED_QTY_EXCEEDED
from app.core.error_codes import PRODUCTION_QUOTE_CONFLICT
from app.core.error_codes import PRODUCTION_QUOTE_NOT_FOUND
from app.core.error_codes import PRODUCTION_SO_CLOSED_OR_CANCELLED
from app.core.error_codes import PRODUCTION_SO_ITEM_AMBIGUOUS
from app.core.error_codes import PRODUCTION_SO_ITEM_NOT_FOUND
from app.core.error_codes import PRODUCTION_SO_NOT_APPROVED
from app.core.error_codes import PRODUCTION_SO_NOT_FOUND
from app.core.error_codes import PRODUCTION_START_DATE_REQUIRED
from app.core.error_codes import PRODUCTION_TRACKING_EXCEPTION_INVALID
from app.core.error_codes import PRODUCTION_TRACKING_NODE_INVALID
from app.core.error_codes import PRODUCTION_WAREHOUSE_REQUIRED
from app.core.error_codes import PRODUCTION_WORK_ORDER_SYNC_FAILED
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.request_id import is_request_id_valid
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchasePayment
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.master_data import LyMasterDataRecord
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionFollowupTemplate
from app.models.production import LyProductionFollowupTemplateNode
from app.models.production import LyProductionFollowupTemplateNodeOperation
from app.models.production import LyProductionFollowupTemplateOperation
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.production import LyProductionPlanOperation
from app.models.production import LyProductionQuote
from app.models.production import LyProductionQuoteOperation
from app.models.production import LyProductionStatusLog
from app.models.production import LyProductionTrackingException
from app.models.production import LyProductionTrackingNodeEvent
from app.models.production import LyProductionTrackingReconcile
from app.models.production import LyProductionTrackingReconcileBatch
from app.models.production import LyProductionWorkOrderLink
from app.models.sample import LySampleMaterialBom
from app.models.sample import LySampleMaterialBomItem
from app.models.sample import LySampleCostLine
from app.models.sample import LySampleOrder
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.sales_order import LySalesPaymentEntry
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.schemas.production import ProductionCreateWorkOrderData
from app.schemas.production import ProductionCreateWorkOrderRequest
from app.schemas.production import ProductionFollowupTemplateListData
from app.schemas.production import ProductionFollowupTemplateListItem
from app.schemas.production import ProductionFollowupTemplateActionRequest
from app.schemas.production import ProductionFollowupTemplateCopyRequest
from app.schemas.production import ProductionFollowupTemplateCreateRequest
from app.schemas.production import ProductionFollowupTemplateQuery
from app.schemas.production import ProductionFollowupTemplateNodeActionRequest
from app.schemas.production import ProductionFollowupTemplateNodeCreateRequest
from app.schemas.production import ProductionFollowupTemplateNodeDeleteData
from app.schemas.production import ProductionFollowupTemplateNodeItem
from app.schemas.production import ProductionFollowupTemplateNodeUpdateRequest
from app.schemas.production import ProductionFollowupTemplateUpdateRequest
from app.schemas.production import ProductionJobCardLinkItem
from app.schemas.production import ProductionMaterialCheckData
from app.schemas.production import ProductionMaterialCheckRequest
from app.schemas.production import ProductionMaterialIssueData
from app.schemas.production import ProductionMaterialIssueItem
from app.schemas.production import ProductionMaterialIssueListData
from app.schemas.production import ProductionMaterialIssueListItem
from app.schemas.production import ProductionMaterialIssueQuery
from app.schemas.production import ProductionMaterialIssueRequest
from app.schemas.production import ProductionMaterialCostListData
from app.schemas.production import ProductionMaterialCostListItem
from app.schemas.production import ProductionMaterialCostQuery
from app.schemas.production import ProductionOrderIOQuantityListData
from app.schemas.production import ProductionOrderIOQuantityListItem
from app.schemas.production import ProductionOrderIOQuantityQuery
from app.schemas.production import ProductionPlanCreateData
from app.schemas.production import ProductionPlanCreateRequest
from app.schemas.production import ProductionPlanDetailData
from app.schemas.production import ProductionPlanListData
from app.schemas.production import ProductionPlanListItem
from app.schemas.production import ProductionPlanMaterialSnapshotItem
from app.schemas.production import ProductionPlanQuery
from app.schemas.production import ProductionQuoteConvertData
from app.schemas.production import ProductionQuoteConvertRequest
from app.schemas.production import ProductionQuoteCopyRequest
from app.schemas.production import ProductionQuoteListData
from app.schemas.production import ProductionQuoteListItem
from app.schemas.production import ProductionQuoteCreateRequest
from app.schemas.production import ProductionQuoteQuery
from app.schemas.production import ProductionQuoteVoidRequest
from app.schemas.production import ProductionReportSuiteCompositionItem
from app.schemas.production import ProductionReportSuiteData
from app.schemas.production import ProductionReportSuiteQuery
from app.schemas.production import ProductionReportSuiteTrendPoint
from app.schemas.production import ProductionSalesForecastListData
from app.schemas.production import ProductionSalesForecastListItem
from app.schemas.production import ProductionSalesForecastQuery
from app.schemas.production import ProductionSalespersonPerformanceListData
from app.schemas.production import ProductionSalespersonPerformanceListItem
from app.schemas.production import ProductionSalespersonPerformanceQuery
from app.services.material_purchase_service import MaterialPurchaseService
from app.schemas.production import ProductionSyncJobCardsData
from app.schemas.production import ProductionSyncJobCardsRequest
from app.schemas.production import ProductionTrackingReconcileGenerateData
from app.schemas.production import ProductionTrackingReconcileGenerateRequest
from app.schemas.production import ProductionTrackingReconcileListData
from app.schemas.production import ProductionTrackingReconcileListItem
from app.schemas.production import ProductionTrackingReconcileQuery
from app.schemas.production import ProductionTrackingExceptionCreateRequest
from app.schemas.production import ProductionTrackingExceptionItem
from app.schemas.production import ProductionTrackingNodeEventData
from app.schemas.production import ProductionTrackingNodeEventRequest
from app.schemas.production import ProductionTrackingNodeItem
from app.schemas.production import ProductionTrackingSummary
from app.schemas.production import ProductionWorkOrderListData
from app.schemas.production import ProductionWorkOrderListItem
from app.schemas.production import ProductionWorkOrderQuery
from app.schemas.production import ProductionWorkOrderOutboxSummary
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.schemas.sales_inventory import SalesOrderDraftCreateRequest
from app.schemas.sales_inventory import SalesOrderDraftLineItemCreateRequest
from app.services.sales_inventory_service import SalesInventoryService
from app.services.sales_inventory_service import SalesInventoryServiceError
from app.services.erpnext_production_adapter import ERPNextSalesOrder
from app.services.erpnext_production_adapter import ERPNextSalesOrderItem
from app.services.production_work_order_outbox_service import ProductionWorkOrderOutboxService

PRODUCTION_WRITE_ENTRY_FROZEN_REASON = (
    "受控写门禁：create-work-order 与 sync-job-cards 仅允许 local-dev + local sqlite + scenario carrier 完整校验。"
)
PRODUCTION_MATERIAL_CHECK_ALLOWED_STATUSES = frozenset(
    {
        "planned",
        "material_checked",
        "work_order_pending",
        "work_order_created",
    }
)
PRODUCTION_PLAN_SCENARIO_TAG_PATTERN = re.compile(r"^Z003-PROD-PLAN-\d{8}-\d{3}$")
PRODUCTION_PLAN_DETAIL_SCENARIO_TAG_PATTERN = re.compile(r"^Z003-PROD-PLAN-DETAIL-\d{8}-\d{3}$")
PRODUCTION_TRACKING_EXCEPTION_TYPES = frozenset({"progress", "material", "quality", "delivery", "workshop", "other"})
PRODUCTION_TRACKING_EXCEPTION_SEVERITIES = frozenset({"low", "medium", "high", "blocker"})
PRODUCTION_TRACKING_EXCEPTION_STATUSES = frozenset({"open", "processing", "resolved", "ignored"})
PRODUCTION_TRACKING_NODE_STATUSES = frozenset({"pending", "in_progress", "done", "blocked"})
PRODUCTION_TRACKING_NODE_DEFAULT_NAMES = {
    "plan": "生产计划",
    "material": "齐料检查",
    "work_order": "生产工单",
    "job_card": "工票进度",
    "exception": "异常处理",
}
PRODUCTION_LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
PRODUCTION_LOCAL_DEFAULT_COMPANY = "LY-LOCAL-TEST"
PRODUCTION_GATE_ERROR_PREFIX = "LOCAL_GATE_FAIL_CLOSED:"


class ProductionService:
    """Production plan service."""

    def __init__(self, *, session: Session, erp_adapter: ERPNextProductionAdapter | None = None):
        self.session = session
        self.erp_adapter = erp_adapter
        self.outbox_service = ProductionWorkOrderOutboxService(session=session)

    def create_plan(
        self,
        *,
        payload: ProductionPlanCreateRequest,
        operator: str,
        request_id: str | None = None,
    ) -> ProductionPlanCreateData:
        self._validate_create_plan_gate(payload=payload, request_id=request_id)
        sales_order, target_item, company = self._load_sales_order_context(payload=payload, request_id=request_id)

        bom = self._resolve_bom(company=company, item_code=target_item.item_code, bom_id=payload.bom_id)
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
        self._apply_native_sales_order_planned_qty(
            sales_order=str(sales_order.name),
            sales_order_item=str(target_item.name),
            planned_qty=planned_qty,
            operator=operator,
        )

        return ProductionPlanCreateData(
            plan_id=int(row.id),
            plan_no=plan_no,
            status="planned",
            company=company,
        )

    def resolve_create_scope(
        self,
        *,
        payload: ProductionPlanCreateRequest,
        request_id: str | None = None,
    ) -> tuple[str, str]:
        """Resolve company/item scope for create-plan permission checks."""
        self._validate_create_plan_gate(payload=payload, request_id=request_id)
        _, target_item, company = self._load_sales_order_context(payload=payload, request_id=request_id)
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
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                sql = sql.filter(
                    or_(
                        LyProductionPlan.sales_order.like(keyword),
                        LyProductionPlan.sales_order_item.like(keyword),
                        LyProductionPlan.item_code.like(keyword),
                        LyProductionPlan.customer.like(keyword),
                        LyProductionPlan.plan_no.like(keyword),
                    )
                )
            if query.turnover_no:
                sql = sql.filter(LyProductionPlan.sales_order_item.like(f"%{query.turnover_no.strip()}%"))
            if query.item_code:
                sql = sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.company:
                sql = sql.filter(LyProductionPlan.company == query.company)
            if query.from_date:
                sql = sql.filter(LyProductionPlan.planned_start_date >= query.from_date)
            if query.to_date:
                sql = sql.filter(LyProductionPlan.planned_start_date <= query.to_date)
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

        plan_ids = [int(row.id) for row in rows]
        latest_map = self.outbox_service.latest_by_plan_ids(plan_ids=plan_ids)
        readiness_map = self._material_readiness_by_plan_ids(plan_ids=plan_ids)
        tracking_context = self._tracking_context_by_plan_ids(plan_ids=plan_ids)

        items: list[ProductionPlanListItem] = []
        for row in rows:
            material_readiness = readiness_map.get(int(row.id), self._empty_material_readiness_summary())
            summary = None
            latest = latest_map.get(int(row.id))
            if latest is not None:
                summary = ProductionWorkOrderOutboxSummary(
                    outbox_id=int(latest.id),
                    status=str(latest.status),
                    erpnext_work_order=(str(latest.erpnext_work_order) if latest.erpnext_work_order else None),
                    error_code=(str(latest.last_error_code) if latest.last_error_code else None),
                )
            context = tracking_context.get(int(row.id), {})
            tracking_nodes = self._production_tracking_nodes(
                plan=row,
                materials=context.get("materials", []),
                work_order_link=context.get("work_order_link"),
                cards=context.get("cards", []),
                exceptions=context.get("exceptions", []),
                node_events=context.get("node_events", []),
                latest_outbox=latest,
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
                    material_ready=bool(material_readiness["material_ready"]),
                    required_qty_total=Decimal(str(material_readiness["required_qty_total"])),
                    available_qty_total=Decimal(str(material_readiness["available_qty_total"])),
                    shortage_qty_total=Decimal(str(material_readiness["shortage_qty_total"])),
                    pending_requirement_count=int(material_readiness["pending_requirement_count"]),
                    purchase_status=str(material_readiness["purchase_status"]),
                    latest_work_order_outbox=summary,
                    tracking_summary=self._production_tracking_summary(
                        nodes=tracking_nodes,
                        exceptions=context.get("exceptions", []),
                    ),
                    created_at=row.created_at,
                )
            )

        return ProductionPlanListData(items=items, total=int(total), page=query.page, page_size=query.page_size)

    def _material_readiness_by_plan_ids(self, *, plan_ids: list[int]) -> dict[int, dict[str, Any]]:
        normalized_ids = sorted({int(plan_id) for plan_id in plan_ids if int(plan_id) > 0})
        if not normalized_ids:
            return {}

        summaries: dict[int, dict[str, Any]] = {
            plan_id: self._empty_material_readiness_summary(include_private=True) for plan_id in normalized_ids
        }
        try:
            material_rows = (
                self.session.query(
                    LyProductionPlanMaterial.plan_id.label("plan_id"),
                    func.count(LyProductionPlanMaterial.id).label("snapshot_count"),
                    func.coalesce(func.sum(LyProductionPlanMaterial.required_qty), 0).label("required_qty_total"),
                    func.coalesce(func.sum(LyProductionPlanMaterial.available_qty), 0).label("available_qty_total"),
                    func.coalesce(func.sum(LyProductionPlanMaterial.shortage_qty), 0).label("shortage_qty_total"),
                )
                .filter(LyProductionPlanMaterial.plan_id.in_(normalized_ids))
                .group_by(LyProductionPlanMaterial.plan_id)
                .all()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_table_error(exc, LyProductionPlanMaterial.__tablename__):
                material_rows = []
            else:
                raise DatabaseReadFailed() from exc

        try:
            requirement_rows = (
                self.session.query(
                    LyMaterialPurchaseRequirement.plan_id.label("plan_id"),
                    LyMaterialPurchaseRequirement.status.label("status"),
                    func.count(LyMaterialPurchaseRequirement.id).label("requirement_count"),
                )
                .filter(
                    LyMaterialPurchaseRequirement.plan_id.in_(normalized_ids),
                    LyMaterialPurchaseRequirement.status.in_(("pending", "purchased")),
                )
                .group_by(LyMaterialPurchaseRequirement.plan_id, LyMaterialPurchaseRequirement.status)
                .all()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_table_error(exc, LyMaterialPurchaseRequirement.__tablename__):
                requirement_rows = []
            else:
                raise DatabaseReadFailed() from exc

        for row in material_rows:
            plan_id = int(row.plan_id)
            summary = summaries.setdefault(plan_id, self._empty_material_readiness_summary(include_private=True))
            summary["_snapshot_count"] = int(row.snapshot_count or 0)
            summary["required_qty_total"] = Decimal(str(row.required_qty_total or 0))
            summary["available_qty_total"] = Decimal(str(row.available_qty_total or 0))
            summary["shortage_qty_total"] = Decimal(str(row.shortage_qty_total or 0))

        for row in requirement_rows:
            if row.plan_id is None:
                continue
            plan_id = int(row.plan_id)
            summary = summaries.setdefault(plan_id, self._empty_material_readiness_summary(include_private=True))
            count = int(row.requirement_count or 0)
            if str(row.status) == "purchased":
                summary["_purchased_requirement_count"] = int(summary["_purchased_requirement_count"]) + count
            else:
                summary["_pending_requirement_count"] = int(summary["_pending_requirement_count"]) + count

        return {plan_id: self._finalize_material_readiness_summary(summary) for plan_id, summary in summaries.items()}

    @classmethod
    def _filter_bom_rows_for_sales_order_item(
        cls,
        *,
        bom_rows: list[Any],
        sales_order_item: LySalesOrderItem,
    ) -> list[Any]:
        order_color = cls._normalized_dimension(getattr(sales_order_item, "color", None))
        order_size = cls._normalized_dimension(getattr(sales_order_item, "size", None))
        return [
            row
            for row in bom_rows
            if cls._dimension_matches(getattr(row, "color", None), order_color)
            and cls._dimension_matches(getattr(row, "size", None), order_size)
        ]

    @staticmethod
    def _normalized_dimension(value: Any) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def _dimension_matches(cls, bom_value: Any, order_value: str) -> bool:
        normalized_bom_value = cls._normalized_dimension(bom_value)
        if not order_value:
            return True
        return not normalized_bom_value or normalized_bom_value == order_value

    def _material_bom_rows_for_plan(self, *, plan: LyProductionPlan) -> list[Any]:
        sample_rows = self._sample_material_bom_rows_for_plan(plan=plan)
        if sample_rows is not None:
            return sample_rows
        try:
            return (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == int(plan.bom_id))
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _sample_material_bom_rows_for_plan(self, *, plan: LyProductionPlan) -> list[LySampleMaterialBomItem] | None:
        try:
            sales_order = (
                self.session.query(LySalesOrder)
                .filter(
                    LySalesOrder.company == str(plan.company),
                    LySalesOrder.sales_order_no == str(plan.sales_order),
                )
                .first()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_native_sales_order_table(exc):
                return None
            raise DatabaseReadFailed() from exc
        if sales_order is None:
            return None
        source_ref = str(sales_order.source_order_ref or "").strip()
        if not source_ref.startswith("SAMPLE-"):
            return None
        sample_no = source_ref.removeprefix("SAMPLE-").strip()
        if not sample_no:
            return None
        try:
            sample = (
                self.session.query(LySampleOrder)
                .filter(
                    LySampleOrder.company == str(plan.company),
                    LySampleOrder.sample_no == sample_no,
                )
                .first()
            )
            if sample is None:
                return None
            if sample.bulk_handoff_no and str(sample.bulk_handoff_no) != str(plan.sales_order):
                return None
            bom = (
                self.session.query(LySampleMaterialBom)
                .filter(
                    LySampleMaterialBom.company == str(plan.company),
                    LySampleMaterialBom.sample_order_id == int(sample.id),
                    LySampleMaterialBom.status.in_(("draft", "active")),
                )
                .order_by(LySampleMaterialBom.id.desc())
                .first()
            )
            if bom is None:
                return None
            return (
                self.session.query(LySampleMaterialBomItem)
                .filter(LySampleMaterialBomItem.bom_id == int(bom.id))
                .order_by(LySampleMaterialBomItem.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _ensure_material_bom_rows_active(self, *, company: str, bom_rows: list[Any]) -> None:
        if not self._has_sqlite_tables({LyMasterDataRecord.__tablename__}):
            return

        codes: list[str] = []
        for row in bom_rows:
            code = str(getattr(row, "material_item_code", "") or "").strip()
            if code and code not in codes:
                codes.append(code)
        if not codes:
            return

        try:
            material_master_count = (
                self.session.query(func.count(LyMasterDataRecord.id))
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == company,
                )
                .scalar()
            )
            if int(material_master_count or 0) == 0:
                return

            active_rows = (
                self.session.query(LyMasterDataRecord.code)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == company,
                    LyMasterDataRecord.code.in_(codes),
                    LyMasterDataRecord.status == "active",
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        active_codes = {str(row.code) for row in active_rows}
        invalid_codes = [code for code in codes if code not in active_codes]
        if invalid_codes:
            raise BusinessException(
                code=PRODUCTION_BOM_NOT_ACTIVE,
                message=f"用料物料主数据不存在或已停用: {', '.join(invalid_codes)}",
            )

    def _ensure_warehouse_master_active(self, *, company: str, warehouse: str) -> None:
        if not self._has_sqlite_tables({LyMasterDataRecord.__tablename__}):
            return

        normalized = str(warehouse or "").strip()
        if not normalized:
            return

        try:
            warehouse_master_count = (
                self.session.query(func.count(LyMasterDataRecord.id))
                .filter(
                    LyMasterDataRecord.entity_type == "warehouse",
                    LyMasterDataRecord.company == company,
                )
                .scalar()
            )
            if int(warehouse_master_count or 0) == 0:
                return

            active_count = (
                self.session.query(func.count(LyMasterDataRecord.id))
                .filter(
                    LyMasterDataRecord.entity_type == "warehouse",
                    LyMasterDataRecord.company == company,
                    LyMasterDataRecord.status == "active",
                    or_(LyMasterDataRecord.code == normalized, LyMasterDataRecord.name == normalized),
                )
                .scalar()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if int(active_count or 0) <= 0:
            raise BusinessException(
                code=PRODUCTION_BOM_NOT_ACTIVE,
                message=f"仓库主数据不存在或已停用: {normalized}",
            )

    @staticmethod
    def _empty_material_readiness_summary(*, include_private: bool = False) -> dict[str, Any]:
        summary: dict[str, Any] = {
            "material_ready": False,
            "required_qty_total": Decimal("0"),
            "available_qty_total": Decimal("0"),
            "shortage_qty_total": Decimal("0"),
            "pending_requirement_count": 0,
            "purchase_status": "not_calculated",
        }
        if include_private:
            summary.update(
                {
                    "_snapshot_count": 0,
                    "_pending_requirement_count": 0,
                    "_purchased_requirement_count": 0,
                }
            )
        return summary

    @staticmethod
    def _finalize_material_readiness_summary(summary: dict[str, Any]) -> dict[str, Any]:
        snapshot_count = int(summary.get("_snapshot_count") or 0)
        pending_count = int(summary.get("_pending_requirement_count") or 0)
        purchased_count = int(summary.get("_purchased_requirement_count") or 0)
        active_requirement_count = pending_count + purchased_count
        shortage_qty_total = Decimal(str(summary.get("shortage_qty_total") or 0))

        if snapshot_count <= 0:
            purchase_status = "not_calculated"
        elif shortage_qty_total <= Decimal("0") and active_requirement_count == 0:
            purchase_status = "ready"
        elif purchased_count > 0:
            purchase_status = "purchasing"
        elif pending_count > 0:
            purchase_status = "pending_purchase"
        elif shortage_qty_total > Decimal("0"):
            purchase_status = "shortage"
        else:
            purchase_status = "ready"

        return {
            "material_ready": purchase_status == "ready",
            "required_qty_total": Decimal(str(summary.get("required_qty_total") or 0)),
            "available_qty_total": Decimal(str(summary.get("available_qty_total") or 0)),
            "shortage_qty_total": shortage_qty_total,
            "pending_requirement_count": active_requirement_count,
            "purchase_status": purchase_status,
        }

    @staticmethod
    def _is_missing_table_error(exc: BaseException, table_name: str) -> bool:
        message = str(exc).lower()
        normalized_table = table_name.lower()
        return normalized_table in message and ("no such table" in message or "does not exist" in message)

    def list_tracking_reconciliations(
        self,
        *,
        query: ProductionTrackingReconcileQuery,
        readable_companies: set[str] | None = None,
    ) -> ProductionTrackingReconcileListData:
        try:
            sql = self.session.query(LyProductionTrackingReconcile)
            if query.company:
                sql = sql.filter(LyProductionTrackingReconcile.company == query.company.strip())
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                sql = sql.filter(
                    or_(
                        LyProductionTrackingReconcile.reconcile_no.like(keyword),
                        LyProductionTrackingReconcile.sample_no.like(keyword),
                        LyProductionTrackingReconcile.style_no.like(keyword),
                        LyProductionTrackingReconcile.style_name.like(keyword),
                        LyProductionTrackingReconcile.customer.like(keyword),
                        LyProductionTrackingReconcile.sales_order.like(keyword),
                    )
                )
            if query.customer:
                sql = sql.filter(LyProductionTrackingReconcile.customer.like(f"%{query.customer.strip()}%"))
            if query.diff_status and query.diff_status != "all":
                sql = sql.filter(LyProductionTrackingReconcile.diff_status == query.diff_status.strip())
            if query.from_date:
                sql = sql.filter(LyProductionTrackingReconcile.sealed_date >= query.from_date)
            if query.to_date:
                sql = sql.filter(LyProductionTrackingReconcile.sealed_date <= query.to_date)
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionTrackingReconcileListData(
                        items=[],
                        total=0,
                        page=query.page,
                        page_size=query.page_size,
                    )
                sql = sql.filter(LyProductionTrackingReconcile.company.in_(sorted(readable_companies)))

            total = sql.with_entities(func.count(LyProductionTrackingReconcile.id)).scalar() or 0
            rows = (
                sql.order_by(LyProductionTrackingReconcile.updated_at.desc(), LyProductionTrackingReconcile.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return ProductionTrackingReconcileListData(
            items=[self._tracking_reconcile_item(row) for row in rows],
            total=int(total),
            page=query.page,
            page_size=query.page_size,
        )

    def generate_tracking_reconciliations(
        self,
        *,
        payload: ProductionTrackingReconcileGenerateRequest,
        operator: str,
    ) -> ProductionTrackingReconcileGenerateData:
        company = self._require_non_blank(
            payload.company,
            code=PRODUCTION_COMPANY_REQUIRED,
            message="company 不能为空",
        )
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        request_hash = self._build_request_hash(
            {
                "company": company,
                "keyword": self._text(payload.keyword),
                "customer": self._text(payload.customer),
                "diff_status": self._text(payload.diff_status),
                "from_date": payload.from_date.isoformat() if payload.from_date else None,
                "to_date": payload.to_date.isoformat() if payload.to_date else None,
                "operation": self._text(payload.operation) or "generate",
            }
        )

        existing_batch = (
            self.session.query(LyProductionTrackingReconcileBatch)
            .filter(
                LyProductionTrackingReconcileBatch.company == company,
                LyProductionTrackingReconcileBatch.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_batch is not None:
            if str(existing_batch.request_hash) != request_hash:
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")
            return ProductionTrackingReconcileGenerateData.model_validate(existing_batch.response_json)

        batch_no = self._next_tracking_batch_no()
        candidates = self._load_tracking_reconcile_candidates(payload=payload, company=company)
        created_count = 0
        updated_count = 0
        items: list[ProductionTrackingReconcileListItem] = []

        for sample in candidates:
            draft = self._build_tracking_reconcile_draft(sample=sample, batch_no=batch_no, operator=operator)
            if payload.diff_status and payload.diff_status != "all" and draft["diff_status"] != payload.diff_status:
                continue

            row = (
                self.session.query(LyProductionTrackingReconcile)
                .filter(
                    LyProductionTrackingReconcile.company == company,
                    LyProductionTrackingReconcile.sample_no == draft["sample_no"],
                )
                .first()
            )
            if row is None:
                row = LyProductionTrackingReconcile(
                    reconcile_no=self._next_tracking_reconcile_no(),
                    company=company,
                    sample_order_id=int(sample.id),
                    sample_no=draft["sample_no"],
                    created_by=operator,
                )
                self.session.add(row)
                created_count += 1
            else:
                updated_count += 1

            self._apply_tracking_reconcile_draft(row=row, draft=draft, operator=operator)
            try:
                self.session.flush()
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc
            items.append(self._tracking_reconcile_item(row))

        matched_count = sum(1 for item in items if item.diff_status != "unmatched")
        unmatched_count = sum(1 for item in items if item.diff_status == "unmatched")
        data = ProductionTrackingReconcileGenerateData(
            batch_no=batch_no,
            company=company,
            created_count=created_count,
            updated_count=updated_count,
            matched_count=matched_count,
            unmatched_count=unmatched_count,
            items=items,
        )
        self.session.add(
            LyProductionTrackingReconcileBatch(
                batch_no=batch_no,
                company=company,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                created_count=created_count,
                updated_count=updated_count,
                matched_count=matched_count,
                unmatched_count=unmatched_count,
                response_json=data.model_dump(mode="json"),
                created_by=operator,
            )
        )
        return data

    def list_work_orders(
        self,
        *,
        query: ProductionWorkOrderQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionWorkOrderListData:
        try:
            sql = self.session.query(LyProductionWorkOrderLink, LyProductionPlan).join(
                LyProductionPlan,
                LyProductionWorkOrderLink.plan_id == LyProductionPlan.id,
            )
            if query.sales_order:
                sql = sql.filter(LyProductionPlan.sales_order == query.sales_order)
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                sql = sql.filter(
                    or_(
                        LyProductionPlan.sales_order.like(keyword),
                        LyProductionPlan.sales_order_item.like(keyword),
                        LyProductionPlan.item_code.like(keyword),
                        LyProductionPlan.customer.like(keyword),
                        LyProductionPlan.plan_no.like(keyword),
                        LyProductionWorkOrderLink.work_order.like(keyword),
                    )
                )
            if query.turnover_no:
                sql = sql.filter(LyProductionPlan.sales_order_item.like(f"%{query.turnover_no.strip()}%"))
            if query.item_code:
                sql = sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.company:
                sql = sql.filter(LyProductionPlan.company == query.company)
            if query.status:
                sql = sql.filter(LyProductionPlan.status == query.status)
            if query.sync_status:
                sql = sql.filter(LyProductionWorkOrderLink.sync_status == query.sync_status)
            if query.from_date:
                sql = sql.filter(func.date(LyProductionWorkOrderLink.created_at) >= query.from_date)
            if query.to_date:
                sql = sql.filter(func.date(LyProductionWorkOrderLink.created_at) <= query.to_date)

            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionWorkOrderListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))

            if readable_companies is not None:
                if not readable_companies:
                    return ProductionWorkOrderListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))

            total = sql.with_entities(func.count(LyProductionWorkOrderLink.id)).scalar() or 0
            rows: list[tuple[LyProductionWorkOrderLink, LyProductionPlan]] = (
                sql.order_by(LyProductionWorkOrderLink.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        items = [
            ProductionWorkOrderListItem(
                plan_id=int(plan.id),
                plan_no=str(plan.plan_no),
                company=str(plan.company),
                sales_order=str(plan.sales_order),
                sales_order_item=str(plan.sales_order_item),
                customer=(str(plan.customer) if plan.customer else None),
                item_code=str(plan.item_code),
                bom_id=int(plan.bom_id) if plan.bom_id is not None else None,
                bom_version=(str(plan.bom_version) if plan.bom_version else None),
                work_order=str(link.work_order),
                planned_qty=Decimal(str(plan.planned_qty)),
                produced_qty=Decimal("0"),
                status=str(plan.status),
                erpnext_docstatus=(int(link.erpnext_docstatus) if link.erpnext_docstatus is not None else None),
                erpnext_status=(str(link.erpnext_status) if link.erpnext_status else None),
                sync_status=(str(link.sync_status) if link.sync_status else None),
                last_synced_at=link.last_synced_at,
                created_at=link.created_at,
                updated_at=link.updated_at,
            )
            for link, plan in rows
        ]
        return ProductionWorkOrderListData(items=items, total=int(total), page=query.page, page_size=query.page_size)

    def list_material_cost_details(
        self,
        *,
        query: ProductionMaterialCostQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionMaterialCostListData:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if query.sales_order:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order == query.sales_order)
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                plan_sql = plan_sql.filter(
                    or_(
                        LyProductionPlan.sales_order.like(keyword),
                        LyProductionPlan.sales_order_item.like(keyword),
                        LyProductionPlan.item_code.like(keyword),
                        LyProductionPlan.customer.like(keyword),
                        LyProductionPlan.plan_no.like(keyword),
                    )
                )
            if query.turnover_no:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order_item.like(f"%{query.turnover_no.strip()}%"))
            if query.from_date:
                plan_sql = plan_sql.filter(LyProductionPlan.planned_start_date >= query.from_date)
            if query.to_date:
                plan_sql = plan_sql.filter(LyProductionPlan.planned_start_date <= query.to_date)
            if query.status:
                plan_sql = plan_sql.filter(LyProductionPlan.status == query.status)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionMaterialCostListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionMaterialCostListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))

            plans = plan_sql.order_by(LyProductionPlan.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        plan_ids = [int(row.id) for row in plans]
        bom_ids = {int(row.bom_id) for row in plans}
        try:
            snapshots = []
            if plan_ids:
                snapshots = (
                    self.session.query(LyProductionPlanMaterial)
                    .filter(LyProductionPlanMaterial.plan_id.in_(plan_ids))
                    .order_by(LyProductionPlanMaterial.plan_id.desc(), LyProductionPlanMaterial.id.asc())
                    .all()
                )
            bom_rows = []
            if bom_ids:
                bom_rows = (
                    self.session.query(LyApparelBomItem)
                    .filter(LyApparelBomItem.bom_id.in_(sorted(bom_ids)))
                    .order_by(LyApparelBomItem.bom_id.asc(), LyApparelBomItem.id.asc())
                    .all()
                )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        snapshot_map: dict[int, list[LyProductionPlanMaterial]] = {}
        for row in snapshots:
            snapshot_map.setdefault(int(row.plan_id), []).append(row)

        bom_map: dict[int, list[LyApparelBomItem]] = {}
        bom_item_by_id: dict[int, LyApparelBomItem] = {}
        for row in bom_rows:
            bom_id = int(row.bom_id)
            bom_map.setdefault(bom_id, []).append(row)
            bom_item_by_id[int(row.id)] = row

        normalized_supplier = (query.supplier or "").strip().lower()
        normalized_material_code = (query.material_item_code or "").strip().lower()

        rows: list[ProductionMaterialCostListItem] = []
        for plan in plans:
            plan_id = int(plan.id)
            items = snapshot_map.get(plan_id) or []
            if items:
                for snapshot in items:
                    bom_item = bom_item_by_id.get(int(snapshot.bom_item_id)) if snapshot.bom_item_id is not None else None
                    supplier = self._extract_supplier_from_remark(bom_item.remark if bom_item is not None else None)
                    unit_price = self._extract_unit_price_from_remark(bom_item.remark if bom_item is not None else None)
                    material_code = str(snapshot.material_item_code or "").strip()
                    if normalized_material_code and normalized_material_code not in material_code.lower():
                        continue
                    if normalized_supplier and normalized_supplier not in (supplier or "").lower():
                        continue
                    required_qty = Decimal(str(snapshot.required_qty or 0))
                    rows.append(
                        ProductionMaterialCostListItem(
                            plan_id=plan_id,
                            plan_no=str(plan.plan_no),
                            company=str(plan.company),
                            sales_order=str(plan.sales_order),
                            sales_order_item=str(plan.sales_order_item),
                            item_code=str(plan.item_code),
                            material_item_code=material_code,
                            supplier=supplier,
                            qty_per_piece=Decimal(str(snapshot.qty_per_piece or 0)),
                            loss_rate=Decimal(str(snapshot.loss_rate or 0)),
                            required_qty=required_qty,
                            estimated_unit_price=unit_price,
                            estimated_material_cost=(required_qty * unit_price),
                            status=str(plan.status),
                            planned_start_date=plan.planned_start_date,
                            checked_at=getattr(snapshot, "checked_at", None),
                        )
                    )
                continue

            planned_qty = Decimal(str(plan.planned_qty or 0))
            for bom_item in bom_map.get(int(plan.bom_id), []):
                supplier = self._extract_supplier_from_remark(bom_item.remark)
                unit_price = self._extract_unit_price_from_remark(bom_item.remark)
                material_code = str(bom_item.material_item_code or "").strip()
                if normalized_material_code and normalized_material_code not in material_code.lower():
                    continue
                if normalized_supplier and normalized_supplier not in (supplier or "").lower():
                    continue
                qty_per_piece = Decimal(str(bom_item.qty_per_piece or 0))
                loss_rate = Decimal(str(bom_item.loss_rate or 0))
                required_qty = (planned_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
                rows.append(
                    ProductionMaterialCostListItem(
                        plan_id=plan_id,
                        plan_no=str(plan.plan_no),
                        company=str(plan.company),
                        sales_order=str(plan.sales_order),
                        sales_order_item=str(plan.sales_order_item),
                        item_code=str(plan.item_code),
                        material_item_code=material_code,
                        supplier=supplier,
                        qty_per_piece=qty_per_piece,
                        loss_rate=loss_rate,
                        required_qty=required_qty,
                        estimated_unit_price=unit_price,
                        estimated_material_cost=(required_qty * unit_price),
                        status=str(plan.status),
                        planned_start_date=plan.planned_start_date,
                        checked_at=None,
                    )
                )

        total = len(rows)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paged_items = rows[start:end]
        return ProductionMaterialCostListData(
            items=paged_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_sales_forecast_details(
        self,
        *,
        query: ProductionSalesForecastQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionSalesForecastListData:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if query.sales_order:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order == query.sales_order)
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                plan_sql = plan_sql.filter(
                    or_(
                        LyProductionPlan.sales_order.like(keyword),
                        LyProductionPlan.sales_order_item.like(keyword),
                        LyProductionPlan.item_code.like(keyword),
                        LyProductionPlan.customer.like(keyword),
                        LyProductionPlan.plan_no.like(keyword),
                    )
                )
            if query.turnover_no:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order_item.like(f"%{query.turnover_no.strip()}%"))
            if query.item_code:
                plan_sql = plan_sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.customer:
                plan_sql = plan_sql.filter(LyProductionPlan.customer.like(f"%{query.customer.strip()}%"))
            if query.from_date:
                plan_sql = plan_sql.filter(LyProductionPlan.planned_start_date >= query.from_date)
            if query.to_date:
                plan_sql = plan_sql.filter(LyProductionPlan.planned_start_date <= query.to_date)
            if query.status:
                plan_sql = plan_sql.filter(LyProductionPlan.status == query.status)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionSalesForecastListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionSalesForecastListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))

            plans = plan_sql.order_by(LyProductionPlan.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        plan_ids = [int(row.id) for row in plans]
        bom_ids = {int(row.bom_id) for row in plans}
        try:
            snapshots = []
            if plan_ids:
                snapshots = (
                    self.session.query(LyProductionPlanMaterial)
                    .filter(LyProductionPlanMaterial.plan_id.in_(plan_ids))
                    .order_by(LyProductionPlanMaterial.plan_id.desc(), LyProductionPlanMaterial.id.asc())
                    .all()
                )
            bom_rows = []
            if bom_ids:
                bom_rows = (
                    self.session.query(LyApparelBomItem)
                    .filter(LyApparelBomItem.bom_id.in_(sorted(bom_ids)))
                    .order_by(LyApparelBomItem.bom_id.asc(), LyApparelBomItem.id.asc())
                    .all()
                )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        snapshot_map: dict[int, list[LyProductionPlanMaterial]] = {}
        for row in snapshots:
            snapshot_map.setdefault(int(row.plan_id), []).append(row)

        bom_map: dict[int, list[LyApparelBomItem]] = {}
        bom_item_by_id: dict[int, LyApparelBomItem] = {}
        for row in bom_rows:
            bom_id = int(row.bom_id)
            bom_map.setdefault(bom_id, []).append(row)
            bom_item_by_id[int(row.id)] = row

        rows: list[ProductionSalesForecastListItem] = []
        for plan in plans:
            planned_qty = Decimal(str(plan.planned_qty or 0))
            if planned_qty < 0:
                planned_qty = Decimal("0")

            plan_material_cost = Decimal("0")
            checked_at = None
            snapshot_items = snapshot_map.get(int(plan.id)) or []
            if snapshot_items:
                for snapshot in snapshot_items:
                    bom_item = bom_item_by_id.get(int(snapshot.bom_item_id)) if snapshot.bom_item_id is not None else None
                    unit_price = self._extract_unit_price_from_remark(bom_item.remark if bom_item is not None else None)
                    required_qty = Decimal(str(snapshot.required_qty or 0))
                    plan_material_cost += required_qty * unit_price
                    if getattr(snapshot, "checked_at", None) is not None:
                        if checked_at is None or snapshot.checked_at > checked_at:
                            checked_at = snapshot.checked_at
            else:
                for bom_item in bom_map.get(int(plan.bom_id), []):
                    qty_per_piece = Decimal(str(bom_item.qty_per_piece or 0))
                    loss_rate = Decimal(str(bom_item.loss_rate or 0))
                    unit_price = self._extract_unit_price_from_remark(bom_item.remark)
                    required_qty = (planned_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
                    plan_material_cost += required_qty * unit_price

            if planned_qty > 0:
                forecast_unit_price = (plan_material_cost / planned_qty).quantize(Decimal("0.000001"))
            else:
                forecast_unit_price = Decimal("0")
            forecast_amount = (forecast_unit_price * planned_qty).quantize(Decimal("0.000001"))

            rows.append(
                ProductionSalesForecastListItem(
                    plan_id=int(plan.id),
                    plan_no=str(plan.plan_no),
                    company=str(plan.company),
                    sales_order=str(plan.sales_order),
                    sales_order_item=str(plan.sales_order_item),
                    customer=(str(plan.customer) if plan.customer else None),
                    item_code=str(plan.item_code),
                    forecast_qty=planned_qty,
                    forecast_unit_price=forecast_unit_price,
                    forecast_amount=forecast_amount,
                    delivery_date=plan.planned_start_date,
                    status=str(plan.status),
                    checked_at=checked_at,
                )
            )

        total = len(rows)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paged_items = rows[start:end]
        return ProductionSalesForecastListData(
            items=paged_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_quotes(
        self,
        *,
        query: ProductionQuoteQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionQuoteListData:
        saved_rows = self._list_saved_quotes(
            query=query,
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
        )
        saved_plan_ids = {int(row.plan_id) for row in saved_rows}
        derived_rows = self._list_derived_quotes(
            query=query,
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
            exclude_plan_ids=saved_plan_ids,
        )
        rows = saved_rows + derived_rows
        rows.sort(key=lambda item: item.quoted_at.isoformat() if item.quoted_at else "", reverse=True)
        total = len(rows)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ProductionQuoteListData(
            items=rows[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def _list_saved_quotes(
        self,
        *,
        query: ProductionQuoteQuery,
        readable_item_codes: set[str] | None,
        readable_companies: set[str] | None,
    ) -> list[ProductionQuoteListItem]:
        normalized_quote_no = (query.quote_no or "").strip().lower()
        normalized_keyword = (query.keyword or "").strip().lower()
        try:
            sql = self.session.query(LyProductionQuote, LyProductionPlan).join(
                LyProductionPlan,
                LyProductionPlan.id == LyProductionQuote.plan_id,
            )
            if query.sales_order:
                sql = sql.filter(LyProductionQuote.sales_order == query.sales_order)
            if query.turnover_no:
                sql = sql.filter(LyProductionQuote.sales_order_item.like(f"%{query.turnover_no.strip()}%"))
            if query.item_code:
                sql = sql.filter(LyProductionQuote.item_code == query.item_code)
            if query.customer:
                sql = sql.filter(LyProductionQuote.customer.like(f"%{query.customer.strip()}%"))
            if query.status:
                sql = sql.filter(LyProductionQuote.status == query.status)
            if query.from_date:
                sql = sql.filter(func.date(LyProductionQuote.created_at) >= query.from_date)
            if query.to_date:
                sql = sql.filter(func.date(LyProductionQuote.created_at) <= query.to_date)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return []
                sql = sql.filter(LyProductionQuote.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return []
                sql = sql.filter(LyProductionQuote.company.in_(sorted(readable_companies)))
            if normalized_quote_no:
                sql = sql.filter(func.lower(LyProductionQuote.quote_no).like(f"%{normalized_quote_no}%"))
            if normalized_keyword:
                like_value = f"%{normalized_keyword}%"
                sql = sql.filter(
                    or_(
                        func.lower(LyProductionQuote.quote_no).like(like_value),
                        func.lower(LyProductionQuote.plan_no).like(like_value),
                        func.lower(LyProductionQuote.sales_order).like(like_value),
                        func.lower(LyProductionQuote.sales_order_item).like(like_value),
                        func.lower(LyProductionQuote.item_code).like(like_value),
                        func.lower(LyProductionQuote.customer).like(like_value),
                    )
                )
            rows = sql.order_by(LyProductionQuote.created_at.desc(), LyProductionQuote.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return [self._quote_item(row, plan=plan) for row, plan in rows]

    def _list_derived_quotes(
        self,
        *,
        query: ProductionQuoteQuery,
        readable_item_codes: set[str] | None,
        readable_companies: set[str] | None,
        exclude_plan_ids: set[int],
    ) -> list[ProductionQuoteListItem]:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if exclude_plan_ids:
                plan_sql = plan_sql.filter(~LyProductionPlan.id.in_(sorted(exclude_plan_ids)))
            if query.sales_order:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order == query.sales_order)
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                plan_sql = plan_sql.filter(
                    or_(
                        LyProductionPlan.sales_order.like(keyword),
                        LyProductionPlan.sales_order_item.like(keyword),
                        LyProductionPlan.item_code.like(keyword),
                        LyProductionPlan.customer.like(keyword),
                        LyProductionPlan.plan_no.like(keyword),
                    )
                )
            if query.turnover_no:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order_item.like(f"%{query.turnover_no.strip()}%"))
            if query.item_code:
                plan_sql = plan_sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.customer:
                plan_sql = plan_sql.filter(LyProductionPlan.customer.like(f"%{query.customer.strip()}%"))
            if query.status:
                plan_sql = plan_sql.filter(LyProductionPlan.status == query.status)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionQuoteListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionQuoteListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))

            plans = plan_sql.order_by(LyProductionPlan.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        plan_ids = [int(row.id) for row in plans]
        bom_ids = {int(row.bom_id) for row in plans}
        try:
            snapshots = []
            if plan_ids:
                snapshots = (
                    self.session.query(LyProductionPlanMaterial)
                    .filter(LyProductionPlanMaterial.plan_id.in_(plan_ids))
                    .order_by(LyProductionPlanMaterial.plan_id.desc(), LyProductionPlanMaterial.id.asc())
                    .all()
                )
            bom_rows = []
            if bom_ids:
                bom_rows = (
                    self.session.query(LyApparelBomItem)
                    .filter(LyApparelBomItem.bom_id.in_(sorted(bom_ids)))
                    .order_by(LyApparelBomItem.bom_id.asc(), LyApparelBomItem.id.asc())
                    .all()
                )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        snapshot_map: dict[int, list[LyProductionPlanMaterial]] = {}
        for row in snapshots:
            snapshot_map.setdefault(int(row.plan_id), []).append(row)

        bom_map: dict[int, list[LyApparelBomItem]] = {}
        bom_item_by_id: dict[int, LyApparelBomItem] = {}
        for row in bom_rows:
            bom_id = int(row.bom_id)
            bom_map.setdefault(bom_id, []).append(row)
            bom_item_by_id[int(row.id)] = row

        normalized_quote_no = (query.quote_no or "").strip().lower()
        rows: list[ProductionQuoteListItem] = []
        for plan in plans:
            quote_no = f"QT-{str(plan.plan_no)}"
            if normalized_quote_no and normalized_quote_no not in quote_no.lower():
                continue

            quoted_at = plan.updated_at or plan.created_at
            quoted_date = quoted_at.date() if quoted_at is not None else None
            if query.from_date and quoted_date is not None and quoted_date < query.from_date:
                continue
            if query.to_date and quoted_date is not None and quoted_date > query.to_date:
                continue

            quote_qty = Decimal(str(plan.planned_qty or 0))
            if quote_qty < 0:
                quote_qty = Decimal("0")

            quote_material_cost = Decimal("0")
            snapshot_items = snapshot_map.get(int(plan.id)) or []
            if snapshot_items:
                for snapshot in snapshot_items:
                    bom_item = bom_item_by_id.get(int(snapshot.bom_item_id)) if snapshot.bom_item_id is not None else None
                    unit_price = self._extract_unit_price_from_remark(bom_item.remark if bom_item is not None else None)
                    required_qty = Decimal(str(snapshot.required_qty or 0))
                    quote_material_cost += required_qty * unit_price
            else:
                for bom_item in bom_map.get(int(plan.bom_id), []):
                    qty_per_piece = Decimal(str(bom_item.qty_per_piece or 0))
                    loss_rate = Decimal(str(bom_item.loss_rate or 0))
                    unit_price = self._extract_unit_price_from_remark(bom_item.remark)
                    required_qty = (quote_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
                    quote_material_cost += required_qty * unit_price

            if quote_qty > 0:
                quote_unit_price = (quote_material_cost / quote_qty).quantize(Decimal("0.000001"))
            else:
                quote_unit_price = Decimal("0")
            quote_amount = (quote_unit_price * quote_qty).quantize(Decimal("0.000001"))

            rows.append(
                ProductionQuoteListItem(
                    quote_id=None,
                    plan_id=int(plan.id),
                    quote_no=quote_no,
                    plan_no=str(plan.plan_no),
                    company=str(plan.company),
                    sales_order=str(plan.sales_order),
                    sales_order_item=str(plan.sales_order_item),
                    customer=(str(plan.customer) if plan.customer else None),
                    item_code=str(plan.item_code),
                    quote_qty=quote_qty,
                    material_cost=quote_material_cost,
                    labor_cost=Decimal("0"),
                    management_fee=Decimal("0"),
                    quote_unit_price=quote_unit_price,
                    quote_amount=quote_amount,
                    gross_margin=Decimal("0"),
                    delivery_date=plan.planned_start_date,
                    quoted_at=quoted_at,
                    status=str(plan.status),
                    source="derived",
                )
            )

        return rows

    def create_quote(
        self,
        *,
        payload: ProductionQuoteCreateRequest,
        operator: str,
    ) -> ProductionQuoteListItem:
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        company_input = self._text(payload.company)
        quote_no_input = self._text(payload.quote_no)
        status = self._normalize_quote_status(payload.status)
        quote_qty_input = Decimal(str(payload.quote_qty)) if payload.quote_qty is not None else None
        labor_cost = self._decimal_nonnegative(payload.labor_cost, field_name="labor_cost")
        management_fee = self._decimal_nonnegative(payload.management_fee, field_name="management_fee")
        remark = self._text(payload.remark) or ""

        plan = self._get_plan_for_quote(plan_id=payload.plan_id, company=company_input)
        company = str(plan.company)
        quote_qty = quote_qty_input if quote_qty_input is not None else Decimal(str(plan.planned_qty or 0))
        if quote_qty <= 0:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="quote_qty 必须大于 0")

        request_hash = self._build_request_hash(
            {
                "operation": "create",
                "company": company,
                "plan_id": int(plan.id),
                "quote_no": quote_no_input,
                "quote_qty": quote_qty,
                "labor_cost": labor_cost,
                "management_fee": management_fee,
                "valid_until": payload.valid_until.isoformat() if payload.valid_until else None,
                "status": status,
                "remark": remark,
            }
        )
        existing_operation = self._get_quote_operation(company=company, operation="create", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_quote_operation_same(existing_operation, request_hash=request_hash)
            return self._quote_item_from_operation(existing_operation)

        quote_no = quote_no_input or self._next_quote_no()
        if self._get_quote_by_no(company=company, quote_no=quote_no) is not None:
            raise BusinessException(code=PRODUCTION_QUOTE_CONFLICT, message=f"{quote_no} 已存在")

        material_cost = self._calculate_quote_material_cost(plan=plan, quote_qty=quote_qty)
        quote_amount = (material_cost + labor_cost + management_fee).quantize(Decimal("0.000001"))

        try:
            row = LyProductionQuote(
                quote_no=quote_no,
                company=company,
                plan_id=int(plan.id),
                plan_no=str(plan.plan_no),
                sales_order=str(plan.sales_order),
                sales_order_item=str(plan.sales_order_item),
                customer=str(plan.customer) if plan.customer else None,
                item_code=str(plan.item_code),
                quote_qty=quote_qty,
                material_cost=material_cost,
                labor_cost=labor_cost,
                management_fee=management_fee,
                quote_amount=quote_amount,
                currency="CNY",
                valid_until=payload.valid_until,
                status=status,
                remark=remark,
                created_by=operator,
                updated_by=operator,
            )
            self.session.add(row)
            self.session.flush()
            item = self._quote_item(row, plan=plan)
            self._insert_quote_operation(
                quote_id=int(row.id),
                company=company,
                operation="create",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        return item

    def convert_quote_to_order(
        self,
        *,
        quote_id: int,
        payload: ProductionQuoteConvertRequest,
        operator: str,
    ) -> ProductionQuoteConvertData:
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        operation = (payload.operation or "convert").strip().lower()
        if operation != "convert":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="operation 必须为 convert")

        company_input = self._text(payload.company)
        row, plan = self._get_quote_for_convert(quote_id=quote_id, company=company_input)
        company = str(row.company)
        target_sales_order_no = self._text(payload.sales_order_no) or self._quote_sales_order_no(row)
        transaction_date = payload.transaction_date or date.today()
        delivery_date = payload.delivery_date or plan.planned_start_date or row.valid_until

        quote_qty = Decimal(str(row.quote_qty or 0))
        quote_amount = Decimal(str(row.quote_amount or 0))
        rate = (quote_amount / quote_qty).quantize(Decimal("0.000001")) if quote_qty > 0 else Decimal("0")
        request_hash = self._build_request_hash(
            {
                "operation": "convert",
                "company": company,
                "quote_id": int(row.id),
                "quote_no": str(row.quote_no),
                "sales_order_no": target_sales_order_no,
                "transaction_date": transaction_date.isoformat() if transaction_date else None,
                "delivery_date": delivery_date.isoformat() if delivery_date else None,
            }
        )
        existing_operation = self._get_quote_operation(company=company, operation="convert", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_quote_operation_same(existing_operation, request_hash=request_hash)
            return self._quote_convert_from_operation(existing_operation)

        status = str(row.status or "")
        if status == "converted":
            raise BusinessException(code=PRODUCTION_QUOTE_CONFLICT, message="报价已转订单")
        if status == "void":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="作废报价不能转订单")

        try:
            sales_order = SalesInventoryService(session=self.session).create_sales_order_draft(
                payload=SalesOrderDraftCreateRequest(
                    company=company,
                    customer=str(row.customer) if row.customer else None,
                    operation="create_draft",
                    scenario_tag="production_quote_convert",
                    sales_order_no=target_sales_order_no,
                    source_order_ref=f"QUOTE-{row.quote_no}",
                    idempotency_key=self._quote_sales_draft_idempotency_key(
                        company=company,
                        quote_no=str(row.quote_no),
                        quote_id=int(row.id),
                        quote_idempotency_key=idempotency_key,
                    ),
                    transaction_date=transaction_date,
                    delivery_date=delivery_date,
                    currency=str(row.currency or "CNY"),
                    items=[
                        SalesOrderDraftLineItemCreateRequest(
                            item_code=str(row.item_code),
                            item_name=str(row.item_code),
                            qty=quote_qty,
                            rate=rate,
                            uom="件",
                            delivery_date=delivery_date,
                        )
                    ],
                ),
                current_user=operator,
                scenario_tag="production_quote_convert",
            )
            row.status = "converted"
            row.updated_by = operator
            self.session.flush()
            quote_item = self._quote_item(row, plan=plan)
            data = ProductionQuoteConvertData(quote=quote_item, sales_order=sales_order)
            self._insert_quote_operation(
                quote_id=int(row.id),
                company=company,
                operation="convert",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=data,
                operator=operator,
            )
            self.session.flush()
        except SalesInventoryServiceError as exc:
            raise BusinessException(code=exc.code, message=exc.message, status_code=exc.status_code) from exc
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        return data

    def copy_quote(
        self,
        *,
        quote_id: int,
        payload: ProductionQuoteCopyRequest,
        operator: str,
    ) -> ProductionQuoteListItem:
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        operation = (payload.operation or "copy").strip().lower()
        if operation != "copy":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="operation 必须为 copy")

        company_input = self._text(payload.company)
        source, plan = self._get_quote_for_update(quote_id=quote_id, company=company_input)
        company = str(source.company)
        status = self._normalize_quote_status(payload.status)
        if status in {"converted", "void"}:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="复制报价的新状态只能是草稿、待核价或已报价")
        quote_no_input = self._text(payload.quote_no)
        remark = self._text(payload.remark)
        request_hash = self._build_request_hash(
            {
                "operation": "copy",
                "company": company,
                "source_quote_id": int(source.id),
                "source_quote_no": str(source.quote_no),
                "quote_no": quote_no_input,
                "valid_until": payload.valid_until.isoformat() if payload.valid_until else None,
                "status": status,
                "remark": remark,
            }
        )
        existing_operation = self._get_quote_operation(company=company, operation="copy", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_quote_operation_same(existing_operation, request_hash=request_hash)
            return self._quote_item_from_operation(existing_operation)

        quote_no = quote_no_input or self._copy_quote_no(company=company, source_quote_no=str(source.quote_no))
        if self._get_quote_by_no(company=company, quote_no=quote_no) is not None:
            raise BusinessException(code=PRODUCTION_QUOTE_CONFLICT, message=f"{quote_no} 已存在")

        try:
            row = LyProductionQuote(
                quote_no=quote_no,
                company=company,
                plan_id=int(source.plan_id),
                plan_no=str(source.plan_no),
                sales_order=str(source.sales_order),
                sales_order_item=str(source.sales_order_item),
                customer=str(source.customer) if source.customer else None,
                item_code=str(source.item_code),
                quote_qty=Decimal(str(source.quote_qty or 0)),
                material_cost=Decimal(str(source.material_cost or 0)),
                labor_cost=Decimal(str(source.labor_cost or 0)),
                management_fee=Decimal(str(source.management_fee or 0)),
                quote_amount=Decimal(str(source.quote_amount or 0)),
                currency=str(source.currency or "CNY"),
                valid_until=payload.valid_until if payload.valid_until is not None else source.valid_until,
                status=status,
                remark=remark if remark is not None else f"复制自 {source.quote_no}",
                created_by=operator,
                updated_by=operator,
            )
            self.session.add(row)
            self.session.flush()
            item = self._quote_item(row, plan=plan)
            self._insert_quote_operation(
                quote_id=int(row.id),
                company=company,
                operation="copy",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        return item

    def void_quote(
        self,
        *,
        quote_id: int,
        payload: ProductionQuoteVoidRequest,
        operator: str,
    ) -> ProductionQuoteListItem:
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        operation = (payload.operation or "void").strip().lower()
        if operation != "void":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="operation 必须为 void")

        company_input = self._text(payload.company)
        row, plan = self._get_quote_for_update(quote_id=quote_id, company=company_input)
        company = str(row.company)
        reason = self._text(payload.reason) or "报价作废"
        request_hash = self._build_request_hash(
            {
                "operation": "void",
                "company": company,
                "quote_id": int(row.id),
                "quote_no": str(row.quote_no),
                "reason": reason,
            }
        )
        existing_operation = self._get_quote_operation(company=company, operation="void", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_quote_operation_same(existing_operation, request_hash=request_hash)
            return self._quote_item_from_operation(existing_operation)

        status = str(row.status or "")
        if status == "converted":
            raise BusinessException(code=PRODUCTION_QUOTE_CONFLICT, message="已转订单报价不能作废")
        if status == "void":
            raise BusinessException(code=PRODUCTION_QUOTE_CONFLICT, message="报价已作废")

        try:
            row.status = "void"
            row.remark = reason
            row.updated_by = operator
            self.session.flush()
            item = self._quote_item(row, plan=plan)
            self._insert_quote_operation(
                quote_id=int(row.id),
                company=company,
                operation="void",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        return item

    def list_followup_templates(
        self,
        *,
        query: ProductionFollowupTemplateQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionFollowupTemplateListData:
        items = self._list_persisted_followup_templates(
            query=query,
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
        )
        items.extend(
            self._list_derived_followup_templates(
                query=query,
                readable_item_codes=readable_item_codes,
                readable_companies=readable_companies,
            )
        )
        items.sort(key=lambda item: item.updated_at, reverse=True)
        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ProductionFollowupTemplateListData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def _list_persisted_followup_templates(
        self,
        *,
        query: ProductionFollowupTemplateQuery,
        readable_item_codes: set[str] | None,
        readable_companies: set[str] | None,
    ) -> list[ProductionFollowupTemplateListItem]:
        normalized_template_no = (query.template_no or "").strip().lower()
        normalized_template_name = (query.template_name or "").strip().lower()
        normalized_template_type = (query.template_type or "").strip().lower()
        normalized_keyword = (query.keyword or "").strip().lower()
        normalized_company = (query.company or "").strip()
        try:
            sql = self.session.query(LyProductionFollowupTemplate)
            if normalized_company:
                sql = sql.filter(LyProductionFollowupTemplate.company == normalized_company)
            if query.item_code:
                sql = sql.filter(LyProductionFollowupTemplate.item_code == query.item_code.strip())
            if query.status:
                sql = sql.filter(LyProductionFollowupTemplate.status == query.status.strip())
            if query.from_date:
                sql = sql.filter(func.date(LyProductionFollowupTemplate.updated_at) >= query.from_date)
            if query.to_date:
                sql = sql.filter(func.date(LyProductionFollowupTemplate.updated_at) <= query.to_date)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return []
                sql = sql.filter(LyProductionFollowupTemplate.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return []
                sql = sql.filter(LyProductionFollowupTemplate.company.in_(sorted(readable_companies)))
            if normalized_template_no:
                sql = sql.filter(func.lower(LyProductionFollowupTemplate.template_no).like(f"%{normalized_template_no}%"))
            if normalized_template_name:
                sql = sql.filter(func.lower(LyProductionFollowupTemplate.template_name).like(f"%{normalized_template_name}%"))
            if normalized_template_type:
                sql = sql.filter(func.lower(LyProductionFollowupTemplate.template_type).like(f"%{normalized_template_type}%"))
            if normalized_keyword:
                like_value = f"%{normalized_keyword}%"
                sql = sql.filter(
                    or_(
                        func.lower(LyProductionFollowupTemplate.template_no).like(like_value),
                        func.lower(LyProductionFollowupTemplate.template_name).like(like_value),
                        func.lower(LyProductionFollowupTemplate.template_type).like(like_value),
                        func.lower(LyProductionFollowupTemplate.trigger_node).like(like_value),
                        func.lower(LyProductionFollowupTemplate.followup_role).like(like_value),
                        func.lower(LyProductionFollowupTemplate.item_code).like(like_value),
                        func.lower(LyProductionFollowupTemplate.company).like(like_value),
                    )
                )
            rows = sql.order_by(LyProductionFollowupTemplate.updated_at.desc(), LyProductionFollowupTemplate.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return [self._followup_template_item(row) for row in rows]

    def _list_derived_followup_templates(
        self,
        *,
        query: ProductionFollowupTemplateQuery,
        readable_item_codes: set[str] | None,
        readable_companies: set[str] | None,
    ) -> list[ProductionFollowupTemplateListItem]:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if query.company:
                plan_sql = plan_sql.filter(LyProductionPlan.company == query.company.strip())
            if query.item_code:
                plan_sql = plan_sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.from_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) >= query.from_date)
            if query.to_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) <= query.to_date)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return []
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return []
                plan_sql = plan_sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))
            plans = plan_sql.order_by(LyProductionPlan.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        normalized_template_no = (query.template_no or "").strip().lower()
        normalized_template_name = (query.template_name or "").strip().lower()
        normalized_template_type = (query.template_type or "").strip().lower()
        normalized_keyword = (query.keyword or "").strip().lower()

        template_config: dict[str, tuple[str, str, str, str, int]] = {
            "draft": ("基础跟进", "制单草稿", "业务跟单", "每周", 72),
            "planned": ("排期跟进", "已计划", "业务跟单", "每日", 24),
            "material_checked": ("物料跟进", "已物料检查", "物料专员", "每日", 24),
            "work_order_pending": ("工单跟进", "工单待同步", "生产跟单", "每班次", 8),
            "work_order_created": ("工单跟进", "已创建工单", "生产跟单", "每日", 12),
            "job_cards_synced": ("生产跟进", "工序卡已同步", "生产跟单", "每日", 24),
            "cancelled": ("异常跟进", "已取消", "业务跟单", "按需", 48),
            "failed": ("异常跟进", "失败", "业务跟单", "按需", 4),
        }

        items: list[ProductionFollowupTemplateListItem] = []
        for plan in plans:
            status = str(plan.status or "")
            template_type, trigger_node, followup_role, followup_frequency, sla_hours = template_config.get(
                status,
                ("基础跟进", status or "-", "业务跟单", "每日", 24),
            )
            template_no = f"FT-{str(plan.plan_no)}"
            template_name = f"{str(plan.item_code)} 跟进模板"
            template_status = "disabled" if status in {"cancelled", "failed"} else "enabled"
            updated_at = plan.updated_at or plan.created_at or datetime.utcnow()
            updated_date = updated_at.date() if updated_at is not None else None

            if query.status and template_status != query.status:
                continue
            if normalized_template_no and normalized_template_no not in template_no.lower():
                continue
            if normalized_template_name and normalized_template_name not in template_name.lower():
                continue
            if normalized_template_type and normalized_template_type not in template_type.lower():
                continue
            if query.from_date and updated_date is not None and updated_date < query.from_date:
                continue
            if query.to_date and updated_date is not None and updated_date > query.to_date:
                continue
            if normalized_keyword:
                target = " ".join(
                    [
                        template_no,
                        template_name,
                        template_type,
                        trigger_node,
                        followup_role,
                        str(plan.plan_no),
                        str(plan.sales_order),
                        str(plan.item_code),
                        str(plan.company),
                    ]
                ).lower()
                if normalized_keyword not in target:
                    continue

            items.append(
                ProductionFollowupTemplateListItem(
                    template_id=int(plan.id),
                    template_no=template_no,
                    template_name=template_name,
                    template_type=template_type,
                    trigger_node=trigger_node,
                    followup_role=followup_role,
                    followup_frequency=followup_frequency,
                    sla_hours=sla_hours,
                    item_code=str(plan.item_code),
                    company=str(plan.company),
                    status=template_status,
                    updated_at=updated_at,
                )
            )

        return items

    def create_followup_template(
        self,
        *,
        payload: ProductionFollowupTemplateCreateRequest,
        operator: str,
    ) -> ProductionFollowupTemplateListItem:
        company = self._require_non_blank(payload.company, code=PRODUCTION_COMPANY_REQUIRED, message="company 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        template_no = self._text(payload.template_no) or self._next_followup_template_no()
        status = self._normalize_followup_template_status(payload.status)
        request_hash = self._build_request_hash(
            {
                "operation": "create",
                "company": company,
                "template_no": template_no,
                "payload": payload.model_dump(mode="json"),
            }
        )
        existing_operation = self._get_followup_template_operation(company=company, operation="create", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_followup_operation_same(existing_operation, request_hash=request_hash)
            return self._followup_template_item_from_operation(existing_operation)
        if self._get_followup_template_by_no(company=company, template_no=template_no) is not None:
            raise BusinessException(code=PRODUCTION_FOLLOWUP_TEMPLATE_CONFLICT, message=f"{template_no} 已存在")

        try:
            row = LyProductionFollowupTemplate(
                company=company,
                template_no=template_no,
                template_name=self._require_non_blank(
                    payload.template_name,
                    code=PRODUCTION_TRACKING_EXCEPTION_INVALID,
                    message="template_name 不能为空",
                ),
                template_type=self._text(payload.template_type) or "基础跟进",
                trigger_node=self._text(payload.trigger_node) or "制单草稿",
                followup_role=self._text(payload.followup_role) or "业务跟单",
                followup_frequency=self._text(payload.followup_frequency) or "每日",
                sla_hours=int(payload.sla_hours or 0),
                item_code=self._text(payload.item_code) or "",
                status=status,
                created_by=operator,
                updated_by=operator,
            )
            self.session.add(row)
            self.session.flush()
            item = self._followup_template_item(row)
            self._insert_followup_template_operation(
                template_id=int(row.id),
                company=company,
                operation="create",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        return item

    def update_followup_template(
        self,
        *,
        template_id: int,
        payload: ProductionFollowupTemplateUpdateRequest,
        operator: str,
    ) -> tuple[ProductionFollowupTemplateListItem, dict[str, Any], dict[str, Any]]:
        company = self._require_non_blank(payload.company, code=PRODUCTION_COMPANY_REQUIRED, message="company 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        row = self._get_followup_template_for_mutation(template_id=template_id, company=company)
        next_values = self._followup_template_next_values(payload=payload)
        request_hash = self._build_request_hash(
            {
                "operation": "update",
                "company": company,
                "template_id": template_id,
                "payload": next_values,
            }
        )
        existing_operation = self._get_followup_template_operation(company=company, operation="update", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_followup_operation_same(existing_operation, request_hash=request_hash)
            item = self._followup_template_item_from_operation(existing_operation)
            return item, item.model_dump(mode="json"), item.model_dump(mode="json")

        before = self._snapshot_followup_template(row)
        new_template_no = next_values.get("template_no")
        if new_template_no and new_template_no != str(row.template_no):
            existing = self._get_followup_template_by_no(company=company, template_no=str(new_template_no))
            if existing is not None and int(existing.id) != int(row.id):
                raise BusinessException(code=PRODUCTION_FOLLOWUP_TEMPLATE_CONFLICT, message=f"{new_template_no} 已存在")

        try:
            for key, value in next_values.items():
                setattr(row, key, value)
            row.updated_by = operator
            self.session.flush()
            item = self._followup_template_item(row)
            self._insert_followup_template_operation(
                template_id=int(row.id),
                company=company,
                operation="update",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        after = self._snapshot_followup_template(row)
        return item, before, after

    def copy_followup_template(
        self,
        *,
        template_id: int,
        payload: ProductionFollowupTemplateCopyRequest,
        operator: str,
    ) -> ProductionFollowupTemplateListItem:
        company = self._require_non_blank(payload.company, code=PRODUCTION_COMPANY_REQUIRED, message="company 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        source = self._get_followup_template_item_for_copy(template_id=template_id, company=company)
        template_no = self._text(payload.template_no) or self._copy_followup_template_no(source.template_no)
        template_name = self._text(payload.template_name) or f"{source.template_name} 副本"
        item_code = self._text(payload.item_code) if payload.item_code is not None else source.item_code
        request_hash = self._build_request_hash(
            {
                "operation": "copy",
                "company": company,
                "source_template_id": template_id,
                "template_no": template_no,
                "template_name": template_name,
                "item_code": item_code,
                "payload": payload.model_dump(mode="json"),
            }
        )
        existing_operation = self._get_followup_template_operation(company=company, operation="copy", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_followup_operation_same(existing_operation, request_hash=request_hash)
            return self._followup_template_item_from_operation(existing_operation)
        if self._get_followup_template_by_no(company=company, template_no=template_no) is not None:
            raise BusinessException(code=PRODUCTION_FOLLOWUP_TEMPLATE_CONFLICT, message=f"{template_no} 已存在")

        try:
            row = LyProductionFollowupTemplate(
                company=company,
                template_no=template_no,
                template_name=template_name,
                template_type=source.template_type,
                trigger_node=source.trigger_node,
                followup_role=source.followup_role,
                followup_frequency=source.followup_frequency,
                sla_hours=int(source.sla_hours or 0),
                item_code=item_code or "",
                status="enabled",
                created_by=operator,
                updated_by=operator,
            )
            self.session.add(row)
            self.session.flush()
            item = self._followup_template_item(row)
            self._insert_followup_template_operation(
                template_id=int(row.id),
                company=company,
                operation="copy",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        return item

    def deactivate_followup_template(
        self,
        *,
        template_id: int,
        payload: ProductionFollowupTemplateActionRequest,
        operator: str,
    ) -> tuple[ProductionFollowupTemplateListItem, dict[str, Any], dict[str, Any]]:
        company = self._require_non_blank(payload.company, code=PRODUCTION_COMPANY_REQUIRED, message="company 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        row = self._get_followup_template_for_mutation(template_id=template_id, company=company)
        request_hash = self._build_request_hash(
            {
                "operation": "deactivate",
                "company": company,
                "template_id": template_id,
                "reason": self._text(payload.reason),
            }
        )
        existing_operation = self._get_followup_template_operation(company=company, operation="deactivate", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_followup_operation_same(existing_operation, request_hash=request_hash)
            item = self._followup_template_item_from_operation(existing_operation)
            return item, item.model_dump(mode="json"), item.model_dump(mode="json")

        before = self._snapshot_followup_template(row)
        try:
            row.status = "disabled"
            row.updated_by = operator
            self.session.flush()
            item = self._followup_template_item(row)
            self._insert_followup_template_operation(
                template_id=int(row.id),
                company=company,
                operation="deactivate",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        after = self._snapshot_followup_template(row)
        return item, before, after

    def create_followup_template_node(
        self,
        *,
        template_id: int,
        payload: ProductionFollowupTemplateNodeCreateRequest,
        operator: str,
    ) -> ProductionFollowupTemplateNodeItem:
        company = self._require_non_blank(payload.company, code=PRODUCTION_COMPANY_REQUIRED, message="company 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        if payload.operation is not None and self._text(payload.operation) != "create_node":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="operation 必须为 create_node")
        template = self._get_followup_template_for_mutation(template_id=template_id, company=company)
        status = self._normalize_followup_node_status(payload.status)
        request_hash = self._build_request_hash(
            {
                "operation": "create_node",
                "company": company,
                "template_id": template_id,
                "payload": payload.model_dump(mode="json"),
            }
        )
        existing_operation = self._get_followup_template_node_operation(company=company, operation="create_node", idempotency_key=idempotency_key)
        if existing_operation is not None:
            self._ensure_followup_operation_same(existing_operation, request_hash=request_hash)
            return self._followup_template_node_item_from_operation(existing_operation)

        try:
            row = LyProductionFollowupTemplateNode(
                template_id=int(template.id),
                company=company,
                node_name=self._require_non_blank(
                    payload.node_name,
                    code=PRODUCTION_TRACKING_EXCEPTION_INVALID,
                    message="node_name 不能为空",
                ),
                owner=self._text(payload.owner) or "",
                lead_time_hours=int(payload.lead_time_hours or 0),
                status=status,
                gate=self._text(payload.gate) or "",
                output=self._text(payload.output) or "",
                reminder=self._text(payload.reminder) or "",
                sequence_no=int(payload.sequence_no or 0),
                created_by=operator,
                updated_by=operator,
            )
            template.updated_by = operator
            self.session.add(row)
            self.session.flush()
            item = self._followup_template_node_item(row)
            self._insert_followup_template_node_operation(
                template_id=int(template.id),
                node_id=int(row.id),
                company=company,
                operation="create_node",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        return item

    def update_followup_template_node(
        self,
        *,
        template_id: int,
        node_id: int,
        payload: ProductionFollowupTemplateNodeUpdateRequest,
        operator: str,
    ) -> tuple[ProductionFollowupTemplateNodeItem, dict[str, Any], dict[str, Any]]:
        company = self._require_non_blank(payload.company, code=PRODUCTION_COMPANY_REQUIRED, message="company 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        if payload.operation is not None and self._text(payload.operation) != "update_node":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="operation 必须为 update_node")
        template = self._get_followup_template_for_mutation(template_id=template_id, company=company)
        row = self._get_followup_template_node_for_mutation(template_id=template_id, node_id=node_id, company=company)
        next_values = self._followup_template_node_next_values(payload=payload)
        request_hash = self._build_request_hash(
            {
                "operation": "update_node",
                "company": company,
                "template_id": template_id,
                "node_id": node_id,
                "payload": next_values,
            }
        )
        existing_operation = self._get_followup_template_node_operation(
            company=company,
            operation="update_node",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            self._ensure_followup_operation_same(existing_operation, request_hash=request_hash)
            item = self._followup_template_node_item_from_operation(existing_operation)
            return item, item.model_dump(mode="json"), item.model_dump(mode="json")

        before = self._snapshot_followup_template_node(row)
        try:
            for key, value in next_values.items():
                setattr(row, key, value)
            row.updated_by = operator
            template.updated_by = operator
            self.session.flush()
            item = self._followup_template_node_item(row)
            self._insert_followup_template_node_operation(
                template_id=int(template.id),
                node_id=int(row.id),
                company=company,
                operation="update_node",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=item,
                operator=operator,
            )
            self.session.flush()
        except (SQLAlchemyError, ValueError) as exc:
            raise DatabaseWriteFailed() from exc
        after = self._snapshot_followup_template_node(row)
        return item, before, after

    def delete_followup_template_node(
        self,
        *,
        template_id: int,
        node_id: int,
        payload: ProductionFollowupTemplateNodeActionRequest,
        operator: str,
    ) -> tuple[ProductionFollowupTemplateNodeDeleteData, dict[str, Any], dict[str, Any]]:
        company = self._require_non_blank(payload.company, code=PRODUCTION_COMPANY_REQUIRED, message="company 不能为空")
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        if payload.operation is not None and self._text(payload.operation) != "delete_node":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="operation 必须为 delete_node")
        template = self._get_followup_template_for_mutation(template_id=template_id, company=company)
        request_hash = self._build_request_hash(
            {
                "operation": "delete_node",
                "company": company,
                "template_id": template_id,
                "node_id": node_id,
                "reason": self._text(payload.reason),
            }
        )
        existing_operation = self._get_followup_template_node_operation(
            company=company,
            operation="delete_node",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            self._ensure_followup_operation_same(existing_operation, request_hash=request_hash)
            data = self._followup_template_node_delete_from_operation(existing_operation)
            return data, data.model_dump(mode="json"), data.model_dump(mode="json")

        row = self._get_followup_template_node_for_mutation(template_id=template_id, node_id=node_id, company=company)
        before = self._snapshot_followup_template_node(row)
        data = ProductionFollowupTemplateNodeDeleteData(id=int(row.id), template_id=int(template.id), deleted=True)
        try:
            self.session.query(LyProductionFollowupTemplateNodeOperation).filter(
                LyProductionFollowupTemplateNodeOperation.node_id == int(row.id),
            ).update({"node_id": None}, synchronize_session=False)
            self.session.delete(row)
            template.updated_by = operator
            self._insert_followup_template_node_operation(
                template_id=int(template.id),
                node_id=None,
                company=company,
                operation="delete_node",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response=data,
                operator=operator,
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return data, before, data.model_dump(mode="json")

    def list_order_io_quantities(
        self,
        *,
        query: ProductionOrderIOQuantityQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionOrderIOQuantityListData:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if query.sales_order:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order == query.sales_order)
            if query.turnover_no:
                plan_sql = plan_sql.filter(LyProductionPlan.sales_order_item.like(f"%{query.turnover_no.strip()}%"))
            if query.item_code:
                plan_sql = plan_sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.customer:
                plan_sql = plan_sql.filter(LyProductionPlan.customer.like(f"%{query.customer.strip()}%"))
            if query.status:
                plan_sql = plan_sql.filter(LyProductionPlan.status == query.status)
            if query.from_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) >= query.from_date)
            if query.to_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) <= query.to_date)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionOrderIOQuantityListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionOrderIOQuantityListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))
            plans = plan_sql.order_by(LyProductionPlan.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        normalized_keyword = (query.keyword or "").strip().lower()
        normalized_io_status = (query.io_status or "").strip().lower()
        quantity_facts = self._production_order_io_quantity_facts(plans)

        items: list[ProductionOrderIOQuantityListItem] = []
        for plan in plans:
            status = str(plan.status or "")
            ordered_qty = Decimal(str(plan.planned_qty or 0))
            if ordered_qty < 0:
                ordered_qty = Decimal("0")
            fact = quantity_facts.get(int(plan.id), {})
            inbound_qty = Decimal(str(fact.get("inbound_qty", Decimal("0")))).quantize(Decimal("0.000001"))
            outbound_qty = Decimal(str(fact.get("outbound_qty", Decimal("0")))).quantize(Decimal("0.000001"))
            pending_inbound_qty = (ordered_qty - inbound_qty).quantize(Decimal("0.000001"))
            if pending_inbound_qty < 0:
                pending_inbound_qty = Decimal("0")
            pending_outbound_qty = (ordered_qty - outbound_qty).quantize(Decimal("0.000001"))
            if pending_outbound_qty < 0:
                pending_outbound_qty = Decimal("0")

            if ordered_qty > 0:
                inbound_progress = min((inbound_qty / ordered_qty) * Decimal("100"), Decimal("100")).quantize(Decimal("0.01"))
                outbound_progress = min((outbound_qty / ordered_qty) * Decimal("100"), Decimal("100")).quantize(Decimal("0.01"))
            else:
                inbound_progress = Decimal("0")
                outbound_progress = Decimal("0")

            if status in {"cancelled", "failed"}:
                io_status = "blocked"
            elif outbound_qty > inbound_qty:
                io_status = "blocked"
            elif ordered_qty > Decimal("0") and outbound_qty >= ordered_qty:
                io_status = "done"
            elif inbound_qty > Decimal("0") or outbound_qty > Decimal("0"):
                io_status = "in_progress"
            else:
                io_status = "pending"

            if normalized_io_status and io_status.lower() != normalized_io_status:
                continue

            updated_at = plan.updated_at or plan.created_at or datetime.utcnow()
            updated_date = updated_at.date() if updated_at is not None else None
            if query.from_date and updated_date is not None and updated_date < query.from_date:
                continue
            if query.to_date and updated_date is not None and updated_date > query.to_date:
                continue

            if normalized_keyword:
                target = " ".join(
                    [
                        str(plan.plan_no),
                        str(plan.sales_order),
                        str(plan.sales_order_item),
                        str(plan.item_code),
                        str(plan.customer or ""),
                        status,
                        io_status,
                    ]
                ).lower()
                if normalized_keyword not in target:
                    continue

            items.append(
                ProductionOrderIOQuantityListItem(
                    plan_id=int(plan.id),
                    plan_no=str(plan.plan_no),
                    company=str(plan.company),
                    sales_order=str(plan.sales_order),
                    sales_order_item=str(plan.sales_order_item),
                    customer=(str(plan.customer) if plan.customer else None),
                    item_code=str(plan.item_code),
                    ordered_qty=ordered_qty,
                    inbound_qty=inbound_qty,
                    outbound_qty=outbound_qty,
                    pending_inbound_qty=pending_inbound_qty,
                    pending_outbound_qty=pending_outbound_qty,
                    inbound_progress=inbound_progress,
                    outbound_progress=outbound_progress,
                    io_status=io_status,
                    status=status,
                    planned_start_date=plan.planned_start_date,
                    updated_at=updated_at,
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ProductionOrderIOQuantityListData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def _production_order_io_quantity_facts(self, plans: list[LyProductionPlan]) -> dict[int, dict[str, Decimal]]:
        facts: dict[int, dict[str, Decimal]] = {
            int(plan.id): {"inbound_qty": Decimal("0"), "outbound_qty": Decimal("0")} for plan in plans
        }
        if not plans:
            return facts

        companies = {str(plan.company) for plan in plans if plan.company}
        item_codes = {str(plan.item_code) for plan in plans if plan.item_code}
        sales_orders = {str(plan.sales_order) for plan in plans if plan.sales_order}
        inbound_refs: dict[tuple[str, str, str], list[LyProductionPlan]] = {}
        outbound_refs: dict[tuple[str, str, str], list[LyProductionPlan]] = {}

        for plan in sorted(plans, key=lambda row: int(row.id)):
            company = str(plan.company)
            item_code = str(plan.item_code)
            for ref in self._production_order_inbound_refs(plan):
                key = (company, item_code, ref)
                bucket = inbound_refs.setdefault(key, [])
                if all(int(existing.id) != int(plan.id) for existing in bucket):
                    bucket.append(plan)
            outbound_refs.setdefault((company, item_code, str(plan.sales_order)), []).append(plan)

        try:
            if self._has_sqlite_tables({LyWarehouseStockEntryDraft.__tablename__, LyWarehouseStockEntryDraftItem.__tablename__}):
                inbound_query = (
                    self.session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
                    .join(LyWarehouseStockEntryDraftItem, LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id)
                    .filter(
                        LyWarehouseStockEntryDraft.status != "cancelled",
                        LyWarehouseStockEntryDraft.purpose == "Material Receipt",
                        LyWarehouseStockEntryDraft.source_type == "finished_goods_inbound",
                    )
                )
                if companies:
                    inbound_query = inbound_query.filter(LyWarehouseStockEntryDraft.company.in_(sorted(companies)))
                if item_codes:
                    inbound_query = inbound_query.filter(LyWarehouseStockEntryDraftItem.item_code.in_(sorted(item_codes)))
                if inbound_refs:
                    inbound_query = inbound_query.filter(
                        LyWarehouseStockEntryDraft.source_id.in_(sorted({key[2] for key in inbound_refs}))
                    )
                for draft, line in inbound_query.all():
                    key = (str(draft.company), str(line.item_code), str(draft.source_id))
                    self._allocate_order_io_quantity(
                        facts=facts,
                        plans=inbound_refs.get(key, []),
                        quantity=Decimal(str(line.qty or 0)),
                        field="inbound_qty",
                    )

            if self._has_sqlite_tables({LyDeliveryInvoice.__tablename__}):
                outbound_query = self.session.query(LyDeliveryInvoice).filter(LyDeliveryInvoice.status != "cancelled")
                if companies:
                    outbound_query = outbound_query.filter(LyDeliveryInvoice.company.in_(sorted(companies)))
                if item_codes:
                    outbound_query = outbound_query.filter(LyDeliveryInvoice.item_code.in_(sorted(item_codes)))
                if sales_orders:
                    outbound_query = outbound_query.filter(LyDeliveryInvoice.sales_order.in_(sorted(sales_orders)))
                for row in outbound_query.all():
                    key = (str(row.company), str(row.item_code), str(row.sales_order))
                    self._allocate_order_io_quantity(
                        facts=facts,
                        plans=outbound_refs.get(key, []),
                        quantity=Decimal(str(row.delivered_qty or 0)),
                        field="outbound_qty",
                    )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return facts

    @staticmethod
    def _production_order_inbound_refs(plan: LyProductionPlan) -> set[str]:
        plan_id = int(plan.id)
        return {
            str(plan.plan_no),
            str(plan.sales_order_item),
            str(plan.sales_order),
            f"production_plan:{plan_id}",
            f"production_plan:{plan_id}:finished_goods_inbound",
            f"plan:{plan_id}",
        }

    @staticmethod
    def _allocate_order_io_quantity(
        *,
        facts: dict[int, dict[str, Decimal]],
        plans: list[LyProductionPlan],
        quantity: Decimal,
        field: str,
    ) -> None:
        remaining = Decimal(str(quantity or 0))
        if remaining <= Decimal("0") or not plans:
            return
        assigned_plan_ids: list[int] = []
        for plan in sorted(plans, key=lambda row: int(row.id)):
            plan_id = int(plan.id)
            assigned_plan_ids.append(plan_id)
            planned_qty = Decimal(str(plan.planned_qty or 0))
            already_assigned = facts.setdefault(plan_id, {"inbound_qty": Decimal("0"), "outbound_qty": Decimal("0")}).setdefault(
                field,
                Decimal("0"),
            )
            remaining_capacity = planned_qty - already_assigned
            if remaining_capacity <= Decimal("0"):
                continue
            assigned_qty = min(remaining, remaining_capacity)
            facts[plan_id][field] = already_assigned + assigned_qty
            remaining -= assigned_qty
            if remaining <= Decimal("0"):
                return
        if remaining > Decimal("0") and assigned_plan_ids:
            last_plan_id = assigned_plan_ids[-1]
            facts[last_plan_id][field] = facts[last_plan_id].get(field, Decimal("0")) + remaining

    def list_salesperson_performance(
        self,
        *,
        query: ProductionSalespersonPerformanceQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionSalespersonPerformanceListData:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if query.salesperson:
                plan_sql = plan_sql.filter(LyProductionPlan.created_by.like(f"%{query.salesperson.strip()}%"))
            if query.item_code:
                plan_sql = plan_sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.customer:
                plan_sql = plan_sql.filter(LyProductionPlan.customer.like(f"%{query.customer.strip()}%"))
            if query.status:
                plan_sql = plan_sql.filter(LyProductionPlan.status == query.status)
            if query.from_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) >= query.from_date)
            if query.to_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) <= query.to_date)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionSalespersonPerformanceListData(
                        items=[],
                        total=0,
                        page=query.page,
                        page_size=query.page_size,
                    )
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionSalespersonPerformanceListData(
                        items=[],
                        total=0,
                        page=query.page,
                        page_size=query.page_size,
                    )
                plan_sql = plan_sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))
            plans = plan_sql.order_by(LyProductionPlan.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        normalized_keyword = (query.keyword or "").strip().lower()
        normalized_performance_status = (query.performance_status or "").strip().lower()
        completion_ratio_by_status: dict[str, Decimal] = {
            "draft": Decimal("0.10"),
            "planned": Decimal("0.35"),
            "material_checked": Decimal("0.55"),
            "work_order_pending": Decimal("0.72"),
            "work_order_created": Decimal("0.82"),
            "job_cards_synced": Decimal("0.95"),
            "cancelled": Decimal("0.00"),
            "failed": Decimal("0.20"),
        }
        unit_price_by_status: dict[str, Decimal] = {
            "draft": Decimal("95"),
            "planned": Decimal("105"),
            "material_checked": Decimal("112"),
            "work_order_pending": Decimal("118"),
            "work_order_created": Decimal("126"),
            "job_cards_synced": Decimal("132"),
            "cancelled": Decimal("90"),
            "failed": Decimal("88"),
        }

        items: list[ProductionSalespersonPerformanceListItem] = []
        for plan in plans:
            status = str(plan.status or "")
            salesperson = str(plan.created_by or "-")
            ordered_qty = Decimal(str(plan.planned_qty or 0))
            if ordered_qty < 0:
                ordered_qty = Decimal("0")

            completion_ratio = completion_ratio_by_status.get(status, Decimal("0.50"))
            completed_qty = (ordered_qty * completion_ratio).quantize(Decimal("0.000001"))
            completion_rate = (completion_ratio * Decimal("100")).quantize(Decimal("0.01"))
            unit_price = unit_price_by_status.get(status, Decimal("100"))
            settled_amount = (completed_qty * unit_price).quantize(Decimal("0.000001"))
            pending_amount = ((ordered_qty - completed_qty) * unit_price).quantize(Decimal("0.000001"))
            if pending_amount < 0:
                pending_amount = Decimal("0")

            if status in {"cancelled", "failed"}:
                performance_status = "risk"
            elif completion_rate >= Decimal("90"):
                performance_status = "excellent"
            elif completion_rate >= Decimal("60"):
                performance_status = "normal"
            else:
                performance_status = "attention"

            if normalized_performance_status and performance_status.lower() != normalized_performance_status:
                continue

            updated_at = plan.updated_at or plan.created_at or datetime.utcnow()
            updated_date = updated_at.date() if updated_at is not None else None
            if query.from_date and updated_date is not None and updated_date < query.from_date:
                continue
            if query.to_date and updated_date is not None and updated_date > query.to_date:
                continue

            if normalized_keyword:
                target = " ".join(
                    [
                        str(plan.plan_no),
                        str(plan.sales_order),
                        str(plan.sales_order_item),
                        str(plan.item_code),
                        str(plan.customer or ""),
                        str(plan.company),
                        salesperson,
                        status,
                        performance_status,
                    ]
                ).lower()
                if normalized_keyword not in target:
                    continue

            items.append(
                ProductionSalespersonPerformanceListItem(
                    plan_id=int(plan.id),
                    plan_no=str(plan.plan_no),
                    company=str(plan.company),
                    salesperson=salesperson,
                    sales_order=str(plan.sales_order),
                    sales_order_item=str(plan.sales_order_item),
                    customer=(str(plan.customer) if plan.customer else None),
                    item_code=str(plan.item_code),
                    ordered_qty=ordered_qty,
                    completed_qty=completed_qty,
                    completion_rate=completion_rate,
                    settled_amount=settled_amount,
                    pending_amount=pending_amount,
                    performance_status=performance_status,
                    status=status,
                    updated_at=updated_at,
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ProductionSalespersonPerformanceListData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def get_report_suite(
        self,
        *,
        query: ProductionReportSuiteQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionReportSuiteData:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if query.company:
                plan_sql = plan_sql.filter(LyProductionPlan.company == query.company)
            if query.customer:
                plan_sql = plan_sql.filter(LyProductionPlan.customer.like(f"%{query.customer.strip()}%"))
            if query.owner:
                plan_sql = plan_sql.filter(LyProductionPlan.created_by.like(f"%{query.owner.strip()}%"))
            if query.status and query.status != "all":
                plan_sql = plan_sql.filter(LyProductionPlan.status == query.status)
            if query.from_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.created_at) >= query.from_date)
            if query.to_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.created_at) <= query.to_date)
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                plan_sql = plan_sql.filter(
                    or_(
                        LyProductionPlan.plan_no.like(keyword),
                        LyProductionPlan.sales_order.like(keyword),
                        LyProductionPlan.sales_order_item.like(keyword),
                        LyProductionPlan.item_code.like(keyword),
                        LyProductionPlan.customer.like(keyword),
                    )
                )
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return self._empty_report_suite(query=query)
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return self._empty_report_suite(query=query)
                plan_sql = plan_sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))

            plans = plan_sql.order_by(LyProductionPlan.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        context = self._build_report_suite_context(plans)
        all_rows = self._build_report_suite_rows(query.report_key, plans=plans, context=context)
        total = len(all_rows)
        start = (query.page - 1) * query.page_size
        paged_rows = all_rows[start : start + query.page_size]

        return ProductionReportSuiteData(
            report_key=query.report_key,
            title=self._report_suite_title(query.report_key),
            items=paged_rows,
            total=total,
            page=query.page,
            page_size=query.page_size,
            trend=self._report_suite_trend(query.report_key, all_rows),
            composition=self._report_suite_composition(query.report_key, all_rows),
            data_basis=[
                "FastAPI 原生销售订单、生产计划、BOM、物料检查快照、款式利润快照",
                "收入优先取款式利润快照实际收入，其次取发货开票与回款实际口径；缺少实际收入时取销售订单行金额",
                "发货开票、回款已合并为报表收入、已回款与未收款口径，成本优先取款式利润快照，缺快照时按 BOM 用量、BOM 单价/本地采购单价、工序工价预测",
                "订单利润报表可生成款式利润快照：后端从销售、BOM、库存、工票与外发真实来源收集，已生成快照的行纳入实际工票工资",
                "样衣对比报表读取样板单成本归集；已转大货样板按 bulk_handoff_no 关联销售单并纳入样衣成本偏差",
                "报表行通过 sourceLabel/sourceStatus/hasSnapshot 显式标识实际快照、部分估算或纯估算口径",
                "B期报表继续披露经营测算/快照：已建成品入库、发货开票、回款、工资发放、付款审批与审批模板/角色矩阵接 FastAPI 执行数据",
                "财务总账按当前可追溯来源归集为 financialLedger* 字段：收入取利润快照实际收入或发货开票，回款取销售回款，成本取利润快照实际成本，采购应付/付款按待采购需求池回溯到订单款式",
            ],
            pending_b_phase_fields=[],
        )

    def _empty_report_suite(self, *, query: ProductionReportSuiteQuery) -> ProductionReportSuiteData:
        return ProductionReportSuiteData(
            report_key=query.report_key,
            title=self._report_suite_title(query.report_key),
            items=[],
            total=0,
            page=query.page,
            page_size=query.page_size,
            trend=[],
            composition=[],
            data_basis=[
                "FastAPI 原生销售订单、生产计划、BOM、物料检查快照、款式利润快照",
            ],
            pending_b_phase_fields=[],
        )

    def _build_report_suite_context(self, plans: list[LyProductionPlan]) -> dict[str, Any]:
        plan_ids = [int(plan.id) for plan in plans]
        bom_ids = sorted({int(plan.bom_id) for plan in plans if plan.bom_id is not None})
        sales_orders = sorted({str(plan.sales_order) for plan in plans if plan.sales_order})
        item_codes = sorted({str(plan.item_code) for plan in plans if plan.item_code})
        companies = sorted({str(plan.company) for plan in plans if plan.company})

        try:
            sales_rows = []
            if sales_orders and item_codes:
                sales_rows = (
                    self.session.query(LySalesOrder, LySalesOrderItem)
                    .join(LySalesOrderItem, LySalesOrderItem.sales_order_id == LySalesOrder.id)
                    .filter(LySalesOrder.sales_order_no.in_(sales_orders))
                    .filter(LySalesOrderItem.item_code.in_(item_codes))
                    .all()
                )

            material_snapshots = []
            if plan_ids:
                material_snapshots = (
                    self.session.query(LyProductionPlanMaterial)
                    .filter(LyProductionPlanMaterial.plan_id.in_(plan_ids))
                    .order_by(LyProductionPlanMaterial.plan_id.asc(), LyProductionPlanMaterial.id.asc())
                    .all()
                )

            bom_items = []
            bom_operations = []
            if bom_ids:
                bom_items = (
                    self.session.query(LyApparelBomItem)
                    .filter(LyApparelBomItem.bom_id.in_(bom_ids))
                    .order_by(LyApparelBomItem.bom_id.asc(), LyApparelBomItem.id.asc())
                    .all()
                )
                bom_operations = (
                    self.session.query(LyBomOperation)
                    .filter(LyBomOperation.bom_id.in_(bom_ids))
                    .order_by(LyBomOperation.bom_id.asc(), LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc())
                    .all()
                )

            job_cards = []
            if plan_ids:
                job_cards = (
                    self.session.query(LyProductionJobCardLink)
                    .filter(LyProductionJobCardLink.plan_id.in_(plan_ids))
                    .order_by(LyProductionJobCardLink.plan_id.asc(), LyProductionJobCardLink.id.asc())
                    .all()
                )

            work_order_links = []
            if plan_ids:
                work_order_links = (
                    self.session.query(LyProductionWorkOrderLink)
                    .filter(LyProductionWorkOrderLink.plan_id.in_(plan_ids))
                    .order_by(LyProductionWorkOrderLink.plan_id.asc(), LyProductionWorkOrderLink.id.asc())
                    .all()
                )

            purchase_unit_price_map: dict[tuple[str, str], Decimal] = {}
            material_item_codes = sorted(
                {
                    str(row.material_item_code)
                    for row in [*material_snapshots, *bom_items]
                    if getattr(row, "material_item_code", None)
                }
            )
            if (
                companies
                and material_item_codes
                and self._has_sqlite_tables(
                    {
                        LyMaterialPurchaseOrder.__tablename__,
                        LyMaterialPurchaseOrderItem.__tablename__,
                    }
                )
            ):
                purchase_rows = (
                    self.session.query(LyMaterialPurchaseOrderItem, LyMaterialPurchaseOrder)
                    .join(LyMaterialPurchaseOrder, LyMaterialPurchaseOrder.id == LyMaterialPurchaseOrderItem.order_id)
                    .filter(LyMaterialPurchaseOrderItem.company.in_(companies))
                    .filter(LyMaterialPurchaseOrderItem.material_item_code.in_(material_item_codes))
                    .filter(LyMaterialPurchaseOrder.status != "cancelled")
                    .filter(LyMaterialPurchaseOrderItem.unit_price > 0)
                    .order_by(
                        LyMaterialPurchaseOrder.transaction_date.desc().nullslast(),
                        LyMaterialPurchaseOrderItem.id.desc(),
                    )
                    .all()
                )
                for item, _order in purchase_rows:
                    key = (str(item.company), str(item.material_item_code))
                    purchase_unit_price_map.setdefault(key, self._dec(item.unit_price))

            snapshots = []
            if companies and item_codes:
                snapshots = (
                    self.session.query(LyStyleProfitSnapshot)
                    .filter(LyStyleProfitSnapshot.company.in_(companies))
                    .filter(LyStyleProfitSnapshot.item_code.in_(item_codes))
                    .order_by(LyStyleProfitSnapshot.created_at.desc(), LyStyleProfitSnapshot.id.desc())
                    .all()
                )

            sample_cost_rows = []
            if (
                sales_orders
                and item_codes
                and self._has_sqlite_tables({LySampleOrder.__tablename__, LySampleCostLine.__tablename__})
            ):
                sample_cost_rows = (
                    self.session.query(LySampleOrder, LySampleCostLine)
                    .join(LySampleCostLine, LySampleCostLine.sample_order_id == LySampleOrder.id)
                    .filter(LySampleOrder.company.in_(companies))
                    .filter(LySampleOrder.bulk_handoff_no.in_(sales_orders))
                    .filter(LySampleOrder.style_no.in_(item_codes))
                    .all()
                )

            delivery_invoice_rows = []
            if (
                companies
                and sales_orders
                and item_codes
                and self._has_sqlite_tables({LyDeliveryInvoice.__tablename__})
            ):
                delivery_invoice_rows = (
                    self.session.query(LyDeliveryInvoice)
                    .filter(LyDeliveryInvoice.company.in_(companies))
                    .filter(LyDeliveryInvoice.sales_order.in_(sales_orders))
                    .filter(LyDeliveryInvoice.item_code.in_(item_codes))
                    .filter(LyDeliveryInvoice.status != "cancelled")
                    .order_by(LyDeliveryInvoice.posting_date.desc(), LyDeliveryInvoice.id.desc())
                    .all()
                )

            sales_payment_rows = []
            if (
                companies
                and sales_orders
                and self._has_sqlite_tables({LySalesPaymentEntry.__tablename__})
            ):
                sales_payment_rows = (
                    self.session.query(LySalesPaymentEntry)
                    .filter(LySalesPaymentEntry.company.in_(companies))
                    .filter(LySalesPaymentEntry.sales_order.in_(sales_orders))
                    .filter(LySalesPaymentEntry.status != "cancelled")
                    .order_by(LySalesPaymentEntry.posting_date.desc(), LySalesPaymentEntry.id.desc())
                    .all()
                )

            purchase_requirement_rows = []
            purchase_invoice_rows = []
            purchase_payment_rows = []
            if (
                companies
                and sales_orders
                and item_codes
                and self._has_sqlite_tables({LyMaterialPurchaseRequirement.__tablename__})
            ):
                purchase_requirement_rows = (
                    self.session.query(LyMaterialPurchaseRequirement)
                    .filter(LyMaterialPurchaseRequirement.company.in_(companies))
                    .filter(LyMaterialPurchaseRequirement.sales_order.in_(sales_orders))
                    .filter(LyMaterialPurchaseRequirement.item_code.in_(item_codes))
                    .filter(LyMaterialPurchaseRequirement.status != "cancelled")
                    .filter(LyMaterialPurchaseRequirement.purchase_no.isnot(None))
                    .order_by(LyMaterialPurchaseRequirement.id.asc())
                    .all()
                )
                purchase_nos = sorted({str(row.purchase_no) for row in purchase_requirement_rows if row.purchase_no})
                purchase_material_codes = sorted(
                    {str(row.material_item_code) for row in purchase_requirement_rows if row.material_item_code}
                )
                if (
                    purchase_nos
                    and purchase_material_codes
                    and self._has_sqlite_tables({LyMaterialPurchaseInvoice.__tablename__})
                ):
                    purchase_invoice_rows = (
                        self.session.query(LyMaterialPurchaseInvoice)
                        .filter(LyMaterialPurchaseInvoice.company.in_(companies))
                        .filter(LyMaterialPurchaseInvoice.purchase_no.in_(purchase_nos))
                        .filter(LyMaterialPurchaseInvoice.material_item_code.in_(purchase_material_codes))
                        .filter(LyMaterialPurchaseInvoice.status != "cancelled")
                        .order_by(LyMaterialPurchaseInvoice.posting_date.desc(), LyMaterialPurchaseInvoice.id.desc())
                        .all()
                    )
                purchase_invoice_nos = sorted(
                    {str(row.purchase_invoice) for row in purchase_invoice_rows if row.purchase_invoice}
                )
                if (
                    purchase_invoice_nos
                    and self._has_sqlite_tables({LyMaterialPurchasePayment.__tablename__})
                ):
                    purchase_payment_rows = (
                        self.session.query(LyMaterialPurchasePayment)
                        .filter(LyMaterialPurchasePayment.company.in_(companies))
                        .filter(LyMaterialPurchasePayment.purchase_invoice.in_(purchase_invoice_nos))
                        .filter(LyMaterialPurchasePayment.status != "cancelled")
                        .order_by(LyMaterialPurchasePayment.posting_date.desc(), LyMaterialPurchasePayment.id.desc())
                        .all()
                    )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        sales_map: dict[tuple[str, str, str], LySalesOrderItem] = {}
        sales_header_map: dict[str, LySalesOrder] = {}
        for order, item in sales_rows:
            sales_header_map[str(order.sales_order_no)] = order
            sales_map.setdefault((str(order.company), str(order.sales_order_no), str(item.item_code)), item)

        material_map: dict[int, list[LyProductionPlanMaterial]] = {}
        for row in material_snapshots:
            material_map.setdefault(int(row.plan_id), []).append(row)

        bom_item_map: dict[int, list[LyApparelBomItem]] = {}
        bom_item_by_id: dict[int, LyApparelBomItem] = {}
        for row in bom_items:
            bom_item_map.setdefault(int(row.bom_id), []).append(row)
            bom_item_by_id[int(row.id)] = row

        operation_map: dict[int, list[LyBomOperation]] = {}
        for row in bom_operations:
            operation_map.setdefault(int(row.bom_id), []).append(row)

        job_card_map: dict[int, list[LyProductionJobCardLink]] = {}
        for row in job_cards:
            job_card_map.setdefault(int(row.plan_id), []).append(row)

        work_order_map: dict[int, LyProductionWorkOrderLink] = {}
        for row in work_order_links:
            work_order_map.setdefault(int(row.plan_id), row)

        snapshot_map: dict[tuple[str, str, str], LyStyleProfitSnapshot] = {}
        for row in snapshots:
            key = (str(row.company), str(row.sales_order or ""), str(row.item_code))
            snapshot_map.setdefault(key, row)

        sample_cost_map: dict[tuple[str, str, str], Decimal] = {}
        sample_cost_count_map: dict[tuple[str, str, str], int] = {}
        for order, cost in sample_cost_rows:
            key = (str(order.company), str(order.bulk_handoff_no or ""), str(order.style_no))
            sample_cost_map[key] = sample_cost_map.get(key, Decimal("0")) + self._dec(cost.amount)
            sample_cost_count_map[key] = sample_cost_count_map.get(key, 0) + 1

        delivery_invoice_map: dict[tuple[str, str, str], dict[str, Any]] = {}
        for invoice in delivery_invoice_rows:
            key = (str(invoice.company), str(invoice.sales_order), str(invoice.item_code))
            summary = delivery_invoice_map.setdefault(
                key,
                {
                    "invoice_count": 0,
                    "delivery_note_count": 0,
                    "invoiced_amount": Decimal("0"),
                    "received_amount": Decimal("0"),
                    "receivable_outstanding": Decimal("0"),
                    "delivered_qty": Decimal("0"),
                    "latest_sales_invoice": "",
                    "latest_delivery_note": "",
                    "latest_posting_date": None,
                },
            )
            summary["invoice_count"] += 1
            summary["delivery_note_count"] += 1
            summary["invoiced_amount"] += self._dec(invoice.grand_total)
            summary["received_amount"] += self._dec(invoice.paid_amount)
            summary["receivable_outstanding"] += self._dec(invoice.outstanding_amount)
            summary["delivered_qty"] += self._dec(invoice.delivered_qty)
            if not summary["latest_sales_invoice"]:
                summary["latest_sales_invoice"] = str(invoice.sales_invoice or "")
            if not summary["latest_delivery_note"]:
                summary["latest_delivery_note"] = str(invoice.delivery_note or "")
            if summary["latest_posting_date"] is None:
                summary["latest_posting_date"] = invoice.posting_date

        sales_order_invoice_amount_map: dict[tuple[str, str], Decimal] = {}
        for (company, sales_order, _item_code), summary in delivery_invoice_map.items():
            order_key = (company, sales_order)
            sales_order_invoice_amount_map[order_key] = sales_order_invoice_amount_map.get(order_key, Decimal("0")) + self._dec(
                summary.get("invoiced_amount")
            )

        sales_payment_amount_map: dict[tuple[str, str], Decimal] = {}
        for payment in sales_payment_rows:
            key = (str(payment.company), str(payment.sales_order))
            sales_payment_amount_map[key] = sales_payment_amount_map.get(key, Decimal("0")) + self._dec(
                payment.allocated_amount
            )

        purchase_requirement_map: dict[tuple[str, str, str], list[LyMaterialPurchaseRequirement]] = {}
        purchase_requirement_by_purchase: dict[tuple[str, str, str], list[LyMaterialPurchaseRequirement]] = {}
        for requirement in purchase_requirement_rows:
            source_key = (str(requirement.company), str(requirement.sales_order or ""), str(requirement.item_code or ""))
            purchase_key = (str(requirement.company), str(requirement.purchase_no or ""), str(requirement.material_item_code))
            purchase_requirement_map.setdefault(source_key, []).append(requirement)
            purchase_requirement_by_purchase.setdefault(purchase_key, []).append(requirement)

        purchase_invoice_by_no: dict[tuple[str, str], LyMaterialPurchaseInvoice] = {}
        purchase_invoice_amount_map: dict[tuple[str, str, str], Decimal] = {}
        for invoice in purchase_invoice_rows:
            purchase_invoice_by_no[(str(invoice.company), str(invoice.purchase_invoice))] = invoice
            purchase_key = (str(invoice.company), str(invoice.purchase_no), str(invoice.material_item_code))
            self._allocate_purchase_ledger_amount(
                target=purchase_invoice_amount_map,
                amount=self._dec(invoice.grand_total),
                requirements=purchase_requirement_by_purchase.get(purchase_key, []),
            )

        purchase_payment_amount_map: dict[tuple[str, str, str], Decimal] = {}
        for payment in purchase_payment_rows:
            invoice = purchase_invoice_by_no.get((str(payment.company), str(payment.purchase_invoice)))
            if invoice is None:
                continue
            purchase_key = (str(invoice.company), str(invoice.purchase_no), str(invoice.material_item_code))
            self._allocate_purchase_ledger_amount(
                target=purchase_payment_amount_map,
                amount=self._dec(payment.allocated_amount),
                requirements=purchase_requirement_by_purchase.get(purchase_key, []),
            )

        return {
            "sales_map": sales_map,
            "sales_header_map": sales_header_map,
            "material_map": material_map,
            "bom_item_map": bom_item_map,
            "bom_item_by_id": bom_item_by_id,
            "operation_map": operation_map,
            "job_card_map": job_card_map,
            "work_order_map": work_order_map,
            "snapshot_map": snapshot_map,
            "purchase_unit_price_map": purchase_unit_price_map,
            "sample_cost_map": sample_cost_map,
            "sample_cost_count_map": sample_cost_count_map,
            "delivery_invoice_map": delivery_invoice_map,
            "sales_order_invoice_amount_map": sales_order_invoice_amount_map,
            "sales_payment_amount_map": sales_payment_amount_map,
            "purchase_requirement_map": purchase_requirement_map,
            "purchase_invoice_amount_map": purchase_invoice_amount_map,
            "purchase_payment_amount_map": purchase_payment_amount_map,
        }

    def _allocate_purchase_ledger_amount(
        self,
        *,
        target: dict[tuple[str, str, str], Decimal],
        amount: Decimal,
        requirements: list[LyMaterialPurchaseRequirement],
    ) -> None:
        if amount <= Decimal("0") or not requirements:
            return
        basis_rows: list[tuple[LyMaterialPurchaseRequirement, Decimal]] = []
        for requirement in requirements:
            basis = self._dec(requirement.net_required_qty)
            if basis <= Decimal("0"):
                basis = self._dec(requirement.required_qty)
            if basis <= Decimal("0"):
                continue
            basis_rows.append((requirement, basis))
        if not basis_rows:
            share = amount / Decimal(str(len(requirements)))
            for requirement in requirements:
                key = (str(requirement.company), str(requirement.sales_order or ""), str(requirement.item_code or ""))
                target[key] = target.get(key, Decimal("0")) + share
            return
        total_basis = sum((basis for _requirement, basis in basis_rows), Decimal("0"))
        if total_basis <= Decimal("0"):
            return
        for requirement, basis in basis_rows:
            key = (str(requirement.company), str(requirement.sales_order or ""), str(requirement.item_code or ""))
            target[key] = target.get(key, Decimal("0")) + (amount * basis / total_basis)

    def _build_report_suite_rows(
        self,
        report_key: str,
        *,
        plans: list[LyProductionPlan],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if report_key == "orderTrackingReport":
            return self._build_report_suite_material_rows(plans=plans, context=context)
        if report_key == "productionCostMaterialDetailReport":
            return [self._build_report_suite_salesperson_row(plan=plan, context=context) for plan in plans]
        if report_key == "productOrderSampleCompare":
            return [self._build_report_suite_sample_row(plan=plan, context=context) for plan in plans]
        if report_key == "productOrderProfitReport":
            return [self._build_report_suite_profit_row(plan=plan, context=context) for plan in plans]
        return [self._build_report_suite_quantity_row(plan=plan, context=context) for plan in plans]

    def _build_report_suite_quantity_row(self, *, plan: LyProductionPlan, context: dict[str, Any]) -> dict[str, Any]:
        base = self._build_report_suite_base_row(plan=plan, context=context)
        qty = self._dec(base["qty"])
        planned_qty = self._dec(plan.planned_qty)
        finished_qty = self._completed_qty(plan=plan, context=context)
        stocked_qty = Decimal("0")
        return {
            **base,
            "id": f"OQ-{int(plan.id)}",
            "colorSize": "-",
            "plannedQty": planned_qty,
            "finishedQty": finished_qty,
            "stockedQty": stocked_qty,
            "varianceQty": planned_qty - qty,
            "progress": self._percent(finished_qty, planned_qty if planned_qty > 0 else qty),
        }

    def _build_report_suite_sample_row(self, *, plan: LyProductionPlan, context: dict[str, Any]) -> dict[str, Any]:
        base = self._build_report_suite_base_row(plan=plan, context=context)
        qty = self._dec(base["qty"])
        amount = self._dec(base["amount"])
        total_cost = self._dec(base["totalCost"])
        bulk_unit_price = self._divide(amount, qty)
        bulk_unit_cost = self._divide(total_cost, qty)
        sample_cost = self._dec(context.get("sample_cost_map", {}).get((str(plan.company), str(plan.sales_order), str(plan.item_code))))
        cost_delta = bulk_unit_cost - sample_cost if sample_cost > Decimal("0") else Decimal("0")
        sample_gap = self._sample_cost_gap(sample_cost=sample_cost, bulk_unit_cost=bulk_unit_cost)
        return {
            **base,
            "id": f"SC-{int(plan.id)}",
            "sampleCost": sample_cost,
            "bulkUnitPrice": bulk_unit_price,
            "bulkUnitCost": bulk_unit_cost,
            "costDelta": cost_delta,
            "sampleGap": sample_gap,
            "status": self._profit_status(self._dec(base["grossMargin"])),
        }

    def _build_report_suite_salesperson_row(self, *, plan: LyProductionPlan, context: dict[str, Any]) -> dict[str, Any]:
        base = self._build_report_suite_base_row(plan=plan, context=context)
        ordered_qty = self._dec(plan.planned_qty)
        if ordered_qty < Decimal("0"):
            ordered_qty = Decimal("0")
        completion_ratio_by_status: dict[str, Decimal] = {
            "draft": Decimal("0.10"),
            "planned": Decimal("0.35"),
            "material_checked": Decimal("0.55"),
            "work_order_pending": Decimal("0.72"),
            "work_order_created": Decimal("0.82"),
            "job_cards_synced": Decimal("0.95"),
            "cancelled": Decimal("0.00"),
            "failed": Decimal("0.20"),
        }
        unit_price_by_status: dict[str, Decimal] = {
            "draft": Decimal("95"),
            "planned": Decimal("105"),
            "material_checked": Decimal("112"),
            "work_order_pending": Decimal("118"),
            "work_order_created": Decimal("126"),
            "job_cards_synced": Decimal("132"),
            "cancelled": Decimal("90"),
            "failed": Decimal("88"),
        }
        status = str(plan.status or "")
        completion_ratio = completion_ratio_by_status.get(status, Decimal("0.50"))
        completed_qty = (ordered_qty * completion_ratio).quantize(Decimal("0.000001"))
        completion_rate = (completion_ratio * Decimal("100")).quantize(Decimal("0.01"))
        unit_price = unit_price_by_status.get(status, Decimal("100"))
        settled_amount = (completed_qty * unit_price).quantize(Decimal("0.000001"))
        pending_amount = ((ordered_qty - completed_qty) * unit_price).quantize(Decimal("0.000001"))
        if pending_amount < Decimal("0"):
            pending_amount = Decimal("0")
        if status in {"cancelled", "failed"}:
            performance_status = "risk"
            performance_status_name = "风险"
        elif completion_rate >= Decimal("90"):
            performance_status = "excellent"
            performance_status_name = "优秀"
        elif completion_rate >= Decimal("60"):
            performance_status = "normal"
            performance_status_name = "正常"
        else:
            performance_status = "attention"
            performance_status_name = "关注"
        return {
            **base,
            "id": f"SP-{int(plan.id)}",
            "salesperson": str(plan.created_by or "-"),
            "planNo": str(plan.plan_no),
            "orderedQty": ordered_qty,
            "completedQty": completed_qty,
            "completionRate": completion_rate,
            "settledAmount": settled_amount,
            "pendingAmount": pending_amount,
            "performanceStatus": performance_status,
            "performanceStatusName": performance_status_name,
            "status": performance_status_name,
            "progress": completion_rate,
        }

    def _build_report_suite_profit_row(self, *, plan: LyProductionPlan, context: dict[str, Any]) -> dict[str, Any]:
        base = self._build_report_suite_base_row(plan=plan, context=context)
        qty = self._dec(base["qty"])
        gross_margin = self._dec(base["grossMargin"])
        return {
            **base,
            "id": f"PF-{int(plan.id)}",
            "unitProfit": self._divide(self._dec(base["profit"]), qty),
            "risk": self._profit_risk(gross_margin),
            "status": self._profit_status(gross_margin),
        }

    def _build_report_suite_material_rows(
        self,
        *,
        plans: list[LyProductionPlan],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for plan in plans:
            base = self._build_report_suite_base_row(plan=plan, context=context)
            planned_qty = self._dec(plan.planned_qty)
            snapshot_items = context["material_map"].get(int(plan.id), [])
            if snapshot_items:
                for snapshot in snapshot_items:
                    bom_item = (
                        context["bom_item_by_id"].get(int(snapshot.bom_item_id))
                        if snapshot.bom_item_id is not None
                        else None
                    )
                    material_code = str(snapshot.material_item_code)
                    required_qty = self._dec(snapshot.required_qty)
                    available_qty = self._dec(snapshot.available_qty)
                    shortage_qty = self._dec(snapshot.shortage_qty)
                    unit_price = self._material_unit_price(
                        material_item_code=material_code,
                        company=str(plan.company),
                        remark=bom_item.remark if bom_item is not None else None,
                        context=context,
                    )
                    rows.append(
                        {
                            **base,
                            "id": f"MD-{int(plan.id)}-{int(snapshot.id)}",
                            "item_code": material_code,
                            "materialName": material_code,
                            "category": "物料",
                            "requiredQty": required_qty,
                            "unit": str(bom_item.uom) if bom_item is not None else "",
                            "unitPrice": unit_price,
                            "materialCost": required_qty * unit_price,
                            "lossRate": self._dec(snapshot.loss_rate) * Decimal("100"),
                            "availableQty": available_qty,
                            "gapQty": available_qty - required_qty,
                            "supplier": self._extract_supplier_from_remark(bom_item.remark if bom_item is not None else None) or "",
                            "status": "缺口" if shortage_qty > 0 else "库存充足",
                        }
                    )
                continue

            for bom_item in context["bom_item_map"].get(int(plan.bom_id), []):
                qty_per_piece = self._dec(bom_item.qty_per_piece)
                loss_rate = self._dec(bom_item.loss_rate)
                required_qty = (planned_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
                unit_price = self._material_unit_price(
                    material_item_code=str(bom_item.material_item_code),
                    company=str(plan.company),
                    remark=bom_item.remark,
                    context=context,
                )
                rows.append(
                    {
                        **base,
                        "id": f"MD-{int(plan.id)}-BOM-{int(bom_item.id)}",
                        "item_code": str(bom_item.material_item_code),
                        "materialName": str(bom_item.material_item_code),
                        "category": "物料",
                        "requiredQty": required_qty,
                        "unit": str(bom_item.uom),
                        "unitPrice": unit_price,
                        "materialCost": required_qty * unit_price,
                        "lossRate": loss_rate * Decimal("100"),
                        "availableQty": Decimal("0"),
                        "gapQty": -required_qty,
                        "supplier": self._extract_supplier_from_remark(bom_item.remark) or "",
                        "status": "待齐料",
                    }
                )
        return rows

    def _build_report_suite_base_row(self, *, plan: LyProductionPlan, context: dict[str, Any]) -> dict[str, Any]:
        company = str(plan.company)
        sales_order = str(plan.sales_order)
        item_code = str(plan.item_code)
        sales_item = context["sales_map"].get((company, sales_order, item_code))
        sales_header = context["sales_header_map"].get(sales_order)
        snapshot = context["snapshot_map"].get((company, sales_order, item_code))
        invoice_summary = context["delivery_invoice_map"].get((company, sales_order, item_code), {})
        work_order_link = context["work_order_map"].get(int(plan.id))
        job_cards = context["job_card_map"].get(int(plan.id), [])
        work_order = str(work_order_link.work_order or "") if work_order_link is not None else ""
        if not work_order and job_cards:
            work_order = str(job_cards[0].work_order or "")
        primary_job_card = str(job_cards[0].job_card or "") if job_cards else ""
        qty = self._dec(getattr(sales_item, "qty", None)) or self._dec(plan.planned_qty)
        invoiced_amount = self._dec(invoice_summary.get("invoiced_amount"))
        received_amount = self._dec(invoice_summary.get("received_amount"))
        receivable_outstanding = self._dec(invoice_summary.get("receivable_outstanding"))
        invoice_count = int(invoice_summary.get("invoice_count") or 0)
        delivered_qty = self._dec(invoice_summary.get("delivered_qty"))
        has_invoice_revenue = invoice_count > 0 and invoiced_amount > Decimal("0")
        snapshot_revenue_status = (
            str(getattr(snapshot, "revenue_status", "") or "").strip().lower() if snapshot is not None else ""
        )
        if snapshot is not None:
            amount = self._dec(getattr(snapshot, "revenue_amount", None))
            if snapshot_revenue_status != "actual" and has_invoice_revenue:
                amount = invoiced_amount
        elif has_invoice_revenue:
            amount = invoiced_amount
        else:
            amount = self._dec(getattr(sales_item, "amount", None))
        if snapshot is None and amount == Decimal("0") and sales_item is not None:
            amount = self._dec(getattr(sales_item, "qty", None)) * self._dec(getattr(sales_item, "rate", None))

        material_cost, labor_cost, outsource_cost = self._estimated_costs(plan=plan, context=context)
        has_snapshot = snapshot is not None
        snapshot_no = str(getattr(snapshot, "snapshot_no", "") or "") if has_snapshot else ""
        if has_snapshot and snapshot_revenue_status == "actual":
            revenue_source_status = "actual"
        elif has_invoice_revenue:
            revenue_source_status = "actual_invoice"
        elif has_snapshot:
            revenue_source_status = snapshot_revenue_status or "estimated"
        else:
            revenue_source_status = "sales_order_estimated"
        cost_source_status = "actual" if has_snapshot else "estimated"
        if has_snapshot and revenue_source_status == "actual":
            source_status = "actual"
            source_label = "利润快照"
            source_note = f"成本与收入来自款式利润快照 {snapshot_no}"
        elif has_snapshot and has_invoice_revenue:
            source_status = "actual"
            source_label = "利润快照/发货开票"
            source_note = (
                f"成本来自款式利润快照 {snapshot_no}；收入来自发货开票 "
                f"{invoice_summary.get('latest_sales_invoice') or '-'}"
            )
        elif has_snapshot:
            source_status = "mixed"
            source_label = "利润快照/估算收入"
            source_note = f"成本来自款式利润快照 {snapshot_no}；收入状态 {revenue_source_status or 'unknown'}"
        elif has_invoice_revenue:
            source_status = "mixed"
            source_label = "发货开票/BOM估算"
            source_note = (
                f"收入来自发货开票 {invoice_summary.get('latest_sales_invoice') or '-'}；"
                "成本缺少款式利润快照，按 BOM/采购价估算"
            )
        else:
            source_status = "estimated"
            source_label = "BOM/采购价估算"
            source_note = "缺少款式利润快照，成本按 BOM 用量、本地采购单价和工序工价预测"
        if snapshot is not None:
            material_cost = self._dec(snapshot.actual_material_cost)
            labor_cost = self._dec(snapshot.actual_workshop_cost)
            outsource_cost = self._dec(snapshot.actual_subcontract_cost)
            total_cost = self._dec(snapshot.actual_total_cost)
        else:
            total_cost = material_cost + labor_cost + outsource_cost
        profit = amount - total_cost
        gross_margin = self._percent(profit, amount)
        payment_status = self._report_suite_payment_status(
            invoice_count=invoice_count,
            invoiced_amount=invoiced_amount,
            received_amount=received_amount,
            receivable_outstanding=receivable_outstanding,
        )
        financial_ledger = self._build_financial_ledger_summary(
            company=company,
            sales_order=sales_order,
            item_code=item_code,
            context=context,
            amount=amount,
            total_cost=total_cost,
            material_cost=material_cost,
            has_snapshot=has_snapshot,
            snapshot_no=snapshot_no,
            revenue_source_status=revenue_source_status,
            invoiced_amount=invoiced_amount,
            received_amount=received_amount,
            receivable_outstanding=receivable_outstanding,
            invoice_count=invoice_count,
        )
        created_at = plan.created_at or datetime.utcnow()
        order_date = getattr(sales_header, "transaction_date", None) or created_at.date()

        return {
            "id": f"PR-{int(plan.id)}",
            "planId": int(plan.id),
            "planNo": str(plan.plan_no),
            "company": company,
            "sales_order": sales_order,
            "styleNo": item_code,
            "styleName": str(getattr(sales_item, "item_name", None) or item_code),
            "customer": str(plan.customer or getattr(sales_header, "customer", None) or ""),
            "merchandiser": str(plan.created_by or ""),
            "date": order_date.isoformat() if hasattr(order_date, "isoformat") else str(order_date),
            "status": self._production_report_status(plan_status=str(plan.status or ""), gross_margin=gross_margin),
            "qty": qty,
            "amount": amount,
            "materialCost": material_cost,
            "laborCost": labor_cost,
            "outsourceCost": outsource_cost,
            "totalCost": total_cost,
            "profit": profit,
            "grossMargin": gross_margin,
            "invoicedAmount": invoiced_amount,
            "receivedAmount": received_amount,
            "receivableOutstanding": receivable_outstanding,
            **financial_ledger,
            "invoiceCount": invoice_count,
            "deliveryNoteCount": int(invoice_summary.get("delivery_note_count") or 0),
            "deliveredQty": delivered_qty,
            "latestSalesInvoice": str(invoice_summary.get("latest_sales_invoice") or ""),
            "latestDeliveryNote": str(invoice_summary.get("latest_delivery_note") or ""),
            "paymentStatus": payment_status,
            "paymentStatusName": self._report_suite_payment_status_name(payment_status),
            "financialRevenueClosed": payment_status == "paid",
            "progress": Decimal("0"),
            "delayDays": Decimal("0"),
            "remark": "现有页：利润按本地真实订单、发货开票/回款、BOM/利润快照测算；发货开票后以实际开票收入为准；生成利润快照后纳入实际工票工资，financialLedger* 字段按可追溯财务来源归集。",
            "sourceType": (
                "style_profit_snapshot"
                if has_snapshot
                else ("delivery_invoice_actual" if has_invoice_revenue else "bom_purchase_estimate")
            ),
            "sourceLabel": source_label,
            "sourceNote": source_note,
            "sourceStatus": source_status,
            "isEstimated": source_status != "actual",
            "hasSnapshot": has_snapshot,
            "snapshotNo": snapshot_no,
            "revenueSourceStatus": revenue_source_status,
            "costSourceStatus": cost_source_status,
            "workOrder": work_order,
            "primaryJobCard": primary_job_card,
            "jobCardCount": len(job_cards),
        }

    def _build_financial_ledger_summary(
        self,
        *,
        company: str,
        sales_order: str,
        item_code: str,
        context: dict[str, Any],
        amount: Decimal,
        total_cost: Decimal,
        material_cost: Decimal,
        has_snapshot: bool,
        snapshot_no: str,
        revenue_source_status: str,
        invoiced_amount: Decimal,
        received_amount: Decimal,
        receivable_outstanding: Decimal,
        invoice_count: int,
    ) -> dict[str, Any]:
        row_key = (company, sales_order, item_code)
        order_key = (company, sales_order)
        order_invoice_amount = self._dec(context.get("sales_order_invoice_amount_map", {}).get(order_key))
        order_payment_amount = self._dec(context.get("sales_payment_amount_map", {}).get(order_key))
        if order_payment_amount > Decimal("0"):
            cash_in_amount = self._allocate_order_amount(
                amount=order_payment_amount,
                row_basis=invoiced_amount,
                total_basis=order_invoice_amount,
            )
        else:
            cash_in_amount = received_amount

        purchase_payable_amount = self._dec(context.get("purchase_invoice_amount_map", {}).get(row_key))
        purchase_cash_out_amount = self._dec(context.get("purchase_payment_amount_map", {}).get(row_key))
        revenue_posted_amount = Decimal("0")
        if revenue_source_status == "actual":
            revenue_posted_amount = amount
        elif invoice_count > 0:
            revenue_posted_amount = invoiced_amount

        cost_posted_amount = total_cost if has_snapshot else purchase_payable_amount
        gross_profit_amount = revenue_posted_amount - cost_posted_amount
        source_count = (
            int(invoice_count)
            + (1 if has_snapshot else 0)
            + (1 if purchase_payable_amount > Decimal("0") else 0)
            + (1 if purchase_cash_out_amount > Decimal("0") else 0)
            + (1 if cash_in_amount > Decimal("0") else 0)
        )
        if revenue_posted_amount > Decimal("0") and cost_posted_amount > Decimal("0"):
            payable_closed = purchase_payable_amount <= Decimal("0") or purchase_cash_out_amount >= purchase_payable_amount
            revenue_closed = cash_in_amount >= revenue_posted_amount and receivable_outstanding <= Decimal("0")
            ledger_status = "closed" if payable_closed and revenue_closed else "posted"
        elif any(
            value > Decimal("0")
            for value in (revenue_posted_amount, cost_posted_amount, purchase_payable_amount, purchase_cash_out_amount, cash_in_amount)
        ):
            ledger_status = "partial"
        else:
            ledger_status = "estimated"

        ledger_status_name = {
            "closed": "总账已闭合",
            "posted": "总账已归集",
            "partial": "部分归集",
            "estimated": "估算待归集",
        }[ledger_status]
        revenue_note = "利润快照实际收入" if revenue_source_status == "actual" else ("发货开票" if invoice_count > 0 else "待实际收入")
        cost_note = f"利润快照 {snapshot_no}" if has_snapshot else ("采购应付回溯" if purchase_payable_amount > Decimal("0") else "待利润快照")
        payable_note = "采购需求池回溯" if purchase_payable_amount > Decimal("0") else "无可追溯采购应付"
        return {
            "financialLedgerRevenueAmount": revenue_posted_amount,
            "financialLedgerCostAmount": cost_posted_amount,
            "financialLedgerMaterialCostAmount": material_cost if has_snapshot else purchase_payable_amount,
            "financialLedgerPayableAmount": purchase_payable_amount,
            "financialLedgerCashInAmount": cash_in_amount,
            "financialLedgerCashOutAmount": purchase_cash_out_amount,
            "financialLedgerGrossProfit": gross_profit_amount,
            "financialLedgerStatus": ledger_status,
            "financialLedgerStatusName": ledger_status_name,
            "financialLedgerClosed": ledger_status == "closed",
            "financialLedgerSourceCount": source_count,
            "financialLedgerSourceNote": f"收入：{revenue_note}；成本：{cost_note}；采购应付/付款：{payable_note}",
        }

    def _allocate_order_amount(self, *, amount: Decimal, row_basis: Decimal, total_basis: Decimal) -> Decimal:
        if amount <= Decimal("0"):
            return Decimal("0")
        if row_basis > Decimal("0") and total_basis > Decimal("0"):
            return amount * row_basis / total_basis
        return amount

    def _estimated_costs(self, *, plan: LyProductionPlan, context: dict[str, Any]) -> tuple[Decimal, Decimal, Decimal]:
        planned_qty = self._dec(plan.planned_qty)
        material_cost = Decimal("0")
        for snapshot in context["material_map"].get(int(plan.id), []):
            bom_item = (
                context["bom_item_by_id"].get(int(snapshot.bom_item_id))
                if snapshot.bom_item_id is not None
                else None
            )
            unit_price = self._material_unit_price(
                material_item_code=str(snapshot.material_item_code),
                company=str(plan.company),
                remark=bom_item.remark if bom_item is not None else None,
                context=context,
            )
            material_cost += self._dec(snapshot.required_qty) * unit_price
        if material_cost == Decimal("0"):
            for bom_item in context["bom_item_map"].get(int(plan.bom_id), []):
                qty_per_piece = self._dec(bom_item.qty_per_piece)
                loss_rate = self._dec(bom_item.loss_rate)
                required_qty = (planned_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
                material_cost += required_qty * self._material_unit_price(
                    material_item_code=str(bom_item.material_item_code),
                    company=str(plan.company),
                    remark=bom_item.remark,
                    context=context,
                )

        labor_cost = Decimal("0")
        outsource_cost = Decimal("0")
        for operation in context["operation_map"].get(int(plan.bom_id), []):
            if bool(operation.is_subcontract):
                outsource_cost += planned_qty * self._dec(operation.subcontract_cost_per_piece)
            else:
                labor_cost += planned_qty * self._dec(operation.wage_rate)
        return material_cost, labor_cost, outsource_cost

    @staticmethod
    def _report_suite_title(report_key: str) -> str:
        return {
            "orderQuantityReport": "订单生产加工数量对照表",
            "productOrderSampleCompare": "订单款式利润预测明细表",
            "orderTrackingReport": "大货成本物料明细表",
            "productOrderProfitReport": "大货销售预测明细表",
            "productionCostMaterialDetailReport": "业务员业绩分析报表",
        }.get(report_key, "生产报表")

    def _material_unit_price(
        self,
        *,
        material_item_code: str,
        company: str,
        remark: str | None,
        context: dict[str, Any],
    ) -> Decimal:
        remark_price = self._extract_unit_price_from_remark(remark)
        if remark_price > Decimal("0"):
            return remark_price
        purchase_prices: dict[tuple[str, str], Decimal] = context.get("purchase_unit_price_map", {})
        return self._dec(purchase_prices.get((company, material_item_code)))

    def _has_sqlite_tables(self, table_names: set[str]) -> bool:
        bind = self.session.get_bind()
        if bind.dialect.name != "sqlite":
            return True
        existing_tables = set(inspect(bind).get_table_names())
        return table_names.issubset(existing_tables)

    @staticmethod
    def _dec(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    @staticmethod
    def _divide(numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == Decimal("0"):
            return Decimal("0")
        return (numerator / denominator).quantize(Decimal("0.000001"))

    @classmethod
    def _percent(cls, numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == Decimal("0"):
            return Decimal("0")
        return ((numerator / denominator) * Decimal("100")).quantize(Decimal("0.01"))

    @classmethod
    def _completed_qty(cls, *, plan: LyProductionPlan, context: dict[str, Any]) -> Decimal:
        return sum((cls._dec(row.completed_qty) for row in context["job_card_map"].get(int(plan.id), [])), Decimal("0"))

    @staticmethod
    def _report_suite_payment_status(
        *,
        invoice_count: int,
        invoiced_amount: Decimal,
        received_amount: Decimal,
        receivable_outstanding: Decimal,
    ) -> str:
        if invoice_count <= 0 or invoiced_amount <= Decimal("0"):
            return "not_invoiced"
        if receivable_outstanding <= Decimal("0"):
            return "paid"
        if received_amount > Decimal("0"):
            return "partly_paid"
        return "unpaid"

    @staticmethod
    def _report_suite_payment_status_name(status: str) -> str:
        return {
            "not_invoiced": "未开票",
            "unpaid": "未回款",
            "partly_paid": "部分回款",
            "paid": "已回款",
        }.get(status, status)

    @classmethod
    def _delivered_qty(cls, *, plan: LyProductionPlan, context: dict[str, Any]) -> Decimal:
        item = context["sales_map"].get((str(plan.company), str(plan.sales_order), str(plan.item_code)))
        return cls._dec(getattr(item, "delivered_qty", None))

    @classmethod
    def _operation_qty(cls, job_cards: list[LyProductionJobCardLink], keywords: tuple[str, ...]) -> Decimal:
        total = Decimal("0")
        lowered_keywords = tuple(keyword.lower() for keyword in keywords)
        for row in job_cards:
            operation = str(row.operation or "").lower()
            if any(keyword in operation for keyword in lowered_keywords):
                total += cls._dec(row.completed_qty)
        return total

    @staticmethod
    def _production_report_status(*, plan_status: str, gross_margin: Decimal) -> str:
        if plan_status in {"cancelled", "failed"}:
            return "异常"
        if gross_margin < Decimal("20"):
            return "利润风险"
        if plan_status in {"job_cards_synced", "work_order_created"}:
            return "推进中"
        return "在产"

    @staticmethod
    def _profit_risk(gross_margin: Decimal) -> str:
        if gross_margin < Decimal("20"):
            return "高风险"
        if gross_margin < Decimal("30"):
            return "中风险"
        return "低风险"

    @staticmethod
    def _profit_status(gross_margin: Decimal) -> str:
        if gross_margin < Decimal("20"):
            return "需复核"
        if gross_margin < Decimal("30"):
            return "利润关注"
        return "利润稳定"

    @staticmethod
    def _sample_cost_gap(*, sample_cost: Decimal, bulk_unit_cost: Decimal) -> str:
        if sample_cost <= Decimal("0"):
            return "未归集样衣成本"
        delta = bulk_unit_cost - sample_cost
        if delta > Decimal("0"):
            return "大货高于样衣"
        if delta < Decimal("0"):
            return "大货低于样衣"
        return "成本持平"

    @staticmethod
    def _report_suite_trend(report_key: str, rows: list[dict[str, Any]]) -> list[ProductionReportSuiteTrendPoint]:
        if report_key == "orderTrackingReport":
            source_rows = rows[:8]
            return [
                ProductionReportSuiteTrendPoint(
                    label=str(row.get("materialName") or row.get("item_code") or "-")[:12],
                    amount=ProductionService._dec(row.get("materialCost")),
                    profit=ProductionService._dec(row.get("profit")),
                )
                for row in source_rows
            ]
        if report_key == "productionCostMaterialDetailReport":
            source_rows = rows[:8]
            return [
                ProductionReportSuiteTrendPoint(
                    label=str(row.get("salesperson") or row.get("merchandiser") or "-")[:12],
                    amount=ProductionService._dec(row.get("settledAmount")),
                    profit=ProductionService._dec(row.get("pendingAmount")),
                )
                for row in source_rows
            ]
        source_rows = rows[:8]
        return [
            ProductionReportSuiteTrendPoint(
                label=str(row.get("styleNo") or row.get("sales_order") or "-")[-12:],
                amount=ProductionService._dec(row.get("amount")),
                profit=ProductionService._dec(row.get("profit")),
            )
            for row in source_rows
        ]

    @staticmethod
    def _report_suite_composition(report_key: str, rows: list[dict[str, Any]]) -> list[ProductionReportSuiteCompositionItem]:
        if report_key == "orderTrackingReport":
            material_total = sum((ProductionService._dec(row.get("materialCost")) for row in rows), Decimal("0"))
            shortage_total = sum((abs(ProductionService._dec(row.get("gapQty"))) for row in rows if ProductionService._dec(row.get("gapQty")) < 0), Decimal("0"))
            enough_total = sum((ProductionService._dec(row.get("availableQty")) for row in rows if ProductionService._dec(row.get("gapQty")) >= 0), Decimal("0"))
            return [
                ProductionReportSuiteCompositionItem(label="物料金额", value=material_total, color="#4E88F3"),
                ProductionReportSuiteCompositionItem(label="缺口数量", value=shortage_total, color="#E65A5A"),
                ProductionReportSuiteCompositionItem(label="可用数量", value=enough_total, color="#27AE60"),
            ]
        if report_key == "productionCostMaterialDetailReport":
            settled_total = sum((ProductionService._dec(row.get("settledAmount")) for row in rows), Decimal("0"))
            pending_total = sum((ProductionService._dec(row.get("pendingAmount")) for row in rows), Decimal("0"))
            ordered_total = sum((ProductionService._dec(row.get("orderedQty")) for row in rows), Decimal("0"))
            return [
                ProductionReportSuiteCompositionItem(label="状态折算业绩", value=settled_total, color="#4E88F3"),
                ProductionReportSuiteCompositionItem(label="预测待完成", value=pending_total, color="#F5A623"),
                ProductionReportSuiteCompositionItem(label="订单件数", value=ordered_total, color="#27AE60"),
            ]
        material_total = sum((ProductionService._dec(row.get("materialCost")) for row in rows), Decimal("0"))
        labor_total = sum((ProductionService._dec(row.get("laborCost")) for row in rows), Decimal("0"))
        outsource_total = sum((ProductionService._dec(row.get("outsourceCost")) for row in rows), Decimal("0"))
        return [
            ProductionReportSuiteCompositionItem(label="面辅料", value=material_total, color="#4E88F3"),
            ProductionReportSuiteCompositionItem(label="工费", value=labor_total, color="#27AE60"),
            ProductionReportSuiteCompositionItem(label="外协", value=outsource_total, color="#F5A623"),
        ]

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
            exceptions = (
                self.session.query(LyProductionTrackingException)
                .filter(LyProductionTrackingException.plan_id == int(plan.id))
                .order_by(LyProductionTrackingException.created_at.desc(), LyProductionTrackingException.id.desc())
                .all()
            )
            node_events = (
                self.session.query(LyProductionTrackingNodeEvent)
                .filter(LyProductionTrackingNodeEvent.plan_id == int(plan.id))
                .order_by(LyProductionTrackingNodeEvent.created_at.asc(), LyProductionTrackingNodeEvent.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        plan_id_value = int(plan.id)
        latest = self.outbox_service.latest_by_plan_ids(plan_ids=[plan_id_value]).get(plan_id_value)
        material_readiness = self._material_readiness_by_plan_ids(plan_ids=[plan_id_value]).get(
            plan_id_value,
            self._empty_material_readiness_summary(),
        )
        summary = None
        if latest is not None:
            summary = ProductionWorkOrderOutboxSummary(
                outbox_id=int(latest.id),
                status=str(latest.status),
                erpnext_work_order=(str(latest.erpnext_work_order) if latest.erpnext_work_order else None),
                error_code=(str(latest.last_error_code) if latest.last_error_code else None),
            )
        tracking_nodes = self._production_tracking_nodes(
            plan=plan,
            materials=materials,
            work_order_link=work_order_link,
            cards=cards,
            exceptions=exceptions,
            node_events=node_events,
            latest_outbox=latest,
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
            write_entry_frozen=True,
            write_entry_frozen_reason=PRODUCTION_WRITE_ENTRY_FROZEN_REASON,
            material_ready=bool(material_readiness["material_ready"]),
            required_qty_total=Decimal(str(material_readiness["required_qty_total"])),
            available_qty_total=Decimal(str(material_readiness["available_qty_total"])),
            shortage_qty_total=Decimal(str(material_readiness["shortage_qty_total"])),
            pending_requirement_count=int(material_readiness["pending_requirement_count"]),
            purchase_status=str(material_readiness["purchase_status"]),
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
            tracking_nodes=tracking_nodes,
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
            tracking_exceptions=[self._tracking_exception_item(row) for row in exceptions],
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    def _tracking_context_by_plan_ids(self, *, plan_ids: list[int]) -> dict[int, dict[str, Any]]:
        normalized_ids = sorted({int(plan_id) for plan_id in plan_ids if int(plan_id) > 0})
        if not normalized_ids:
            return {}

        context: dict[int, dict[str, Any]] = {
            plan_id: {
                "materials": [],
                "work_order_link": None,
                "cards": [],
                "exceptions": [],
                "node_events": [],
            }
            for plan_id in normalized_ids
        }
        try:
            for row in (
                self.session.query(LyProductionPlanMaterial)
                .filter(LyProductionPlanMaterial.plan_id.in_(normalized_ids))
                .order_by(LyProductionPlanMaterial.plan_id.asc(), LyProductionPlanMaterial.id.asc())
                .all()
            ):
                context[int(row.plan_id)]["materials"].append(row)

            for row in (
                self.session.query(LyProductionWorkOrderLink)
                .filter(LyProductionWorkOrderLink.plan_id.in_(normalized_ids))
                .order_by(LyProductionWorkOrderLink.plan_id.asc(), LyProductionWorkOrderLink.id.desc())
                .all()
            ):
                plan_id = int(row.plan_id)
                if context[plan_id]["work_order_link"] is None:
                    context[plan_id]["work_order_link"] = row

            for row in (
                self.session.query(LyProductionJobCardLink)
                .filter(LyProductionJobCardLink.plan_id.in_(normalized_ids))
                .order_by(LyProductionJobCardLink.plan_id.asc(), LyProductionJobCardLink.id.asc())
                .all()
            ):
                context[int(row.plan_id)]["cards"].append(row)

            for row in (
                self.session.query(LyProductionTrackingException)
                .filter(LyProductionTrackingException.plan_id.in_(normalized_ids))
                .order_by(
                    LyProductionTrackingException.plan_id.asc(),
                    LyProductionTrackingException.created_at.desc(),
                    LyProductionTrackingException.id.desc(),
                )
                .all()
            ):
                context[int(row.plan_id)]["exceptions"].append(row)

            for row in (
                self.session.query(LyProductionTrackingNodeEvent)
                .filter(LyProductionTrackingNodeEvent.plan_id.in_(normalized_ids))
                .order_by(
                    LyProductionTrackingNodeEvent.plan_id.asc(),
                    LyProductionTrackingNodeEvent.created_at.asc(),
                    LyProductionTrackingNodeEvent.id.asc(),
                )
                .all()
            ):
                context[int(row.plan_id)]["node_events"].append(row)
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return context

    def _production_tracking_summary(
        self,
        *,
        nodes: list[ProductionTrackingNodeItem],
        exceptions: list[LyProductionTrackingException],
    ) -> ProductionTrackingSummary:
        open_exceptions = [
            row
            for row in exceptions
            if str(getattr(row, "status", "") or "").strip().lower() not in {"resolved", "ignored", "closed"}
        ]
        blocker_count = sum(
            1
            for row in open_exceptions
            if str(getattr(row, "severity", "") or "").strip().lower() == "blocker"
        )
        latest_candidates: list[datetime] = []
        for node in nodes:
            if node.updated_at is not None:
                latest_candidates.append(node.updated_at)
        for row in exceptions:
            updated_at = getattr(row, "updated_at", None) or getattr(row, "created_at", None)
            if updated_at is not None:
                latest_candidates.append(updated_at)

        current_node = next((node for node in nodes if node.node_key == "exception" and node.status == "blocked"), None)
        if current_node is None:
            explicit_nodes = [node for node in nodes if node.event_id is not None]
            if explicit_nodes:
                current_node = max(explicit_nodes, key=lambda node: node.updated_at or datetime.min)
        if current_node is None:
            current_node = next((node for node in nodes if node.status == "blocked"), None)
        if current_node is None and open_exceptions:
            current_node = next((node for node in nodes if node.node_key == "exception"), None)
        if current_node is None:
            current_node = next((node for node in nodes if node.status != "done"), None)
        if current_node is None and nodes:
            current_node = nodes[-1]

        return ProductionTrackingSummary(
            current_node_key=(current_node.node_key if current_node is not None else None),
            current_node_name=(current_node.node_name if current_node is not None else None),
            current_node_status=(current_node.status if current_node is not None else "pending"),
            current_node_progress=(int(current_node.progress) if current_node is not None else 0),
            open_exception_count=len(open_exceptions),
            blocker_count=blocker_count,
            latest_tracking_at=(max(latest_candidates) if latest_candidates else None),
        )

    def _production_tracking_nodes(
        self,
        *,
        plan: LyProductionPlan,
        materials: list[LyProductionPlanMaterial],
        work_order_link: LyProductionWorkOrderLink | None,
        cards: list[LyProductionJobCardLink],
        exceptions: list[LyProductionTrackingException],
        node_events: list[LyProductionTrackingNodeEvent],
        latest_outbox: Any | None,
    ) -> list[ProductionTrackingNodeItem]:
        plan_status = str(plan.status or "").strip()
        plan_progress = 100 if plan_status in {"planned", "material_checked", "work_order_created", "job_cards_synced"} else 30
        required_total = sum((Decimal(str(getattr(row, "required_qty", 0) or 0)) for row in materials), Decimal("0"))
        shortage_total = sum((Decimal(str(getattr(row, "shortage_qty", 0) or 0)) for row in materials), Decimal("0"))
        material_status = "pending"
        material_progress = 0
        if materials:
            if shortage_total > Decimal("0"):
                material_status = "blocked"
                material_progress = 60
            else:
                material_status = "done"
                material_progress = 100
        elif plan_status in {"material_checked", "work_order_created", "job_cards_synced"}:
            material_status = "done"
            material_progress = 100

        work_order_status = "pending"
        work_order_progress = 0
        work_order_ref = None
        work_order_updated = None
        if work_order_link is not None:
            work_order_ref = str(work_order_link.work_order) if work_order_link.work_order else None
            work_order_updated = getattr(work_order_link, "last_synced_at", None)
            work_order_status = "done" if work_order_ref else "in_progress"
            work_order_progress = 100 if work_order_ref else 60
        elif latest_outbox is not None:
            outbox_status = str(getattr(latest_outbox, "status", "") or "")
            work_order_status = "blocked" if outbox_status in {"failed", "dead"} else "in_progress"
            work_order_progress = 40

        completed_qty = sum((Decimal(str(getattr(row, "completed_qty", 0) or 0)) for row in cards), Decimal("0"))
        expected_qty = sum((Decimal(str(getattr(row, "expected_qty", 0) or 0)) for row in cards), Decimal("0"))
        if cards and expected_qty > Decimal("0"):
            card_progress = int(min((completed_qty / expected_qty) * Decimal("100"), Decimal("100")))
            card_status = "done" if card_progress >= 100 else "in_progress"
        elif cards:
            card_progress = 50
            card_status = "in_progress"
        else:
            card_progress = 0
            card_status = "pending"

        open_exceptions = [
            row
            for row in exceptions
            if str(getattr(row, "status", "") or "").strip().lower() not in {"resolved", "ignored", "closed"}
        ]
        material_times = [getattr(row, "checked_at", None) for row in materials if getattr(row, "checked_at", None) is not None]
        card_times = [getattr(row, "synced_at", None) for row in cards if getattr(row, "synced_at", None) is not None]
        blocker = any(str(getattr(row, "severity", "") or "").strip().lower() == "blocker" for row in open_exceptions)
        exception_status = "blocked" if blocker else "in_progress" if open_exceptions else "done"
        exception_progress = 30 if blocker else 60 if open_exceptions else 100
        exception_ref = str(open_exceptions[0].exception_no) if open_exceptions else None
        exception_updated = getattr(open_exceptions[0], "created_at", None) if open_exceptions else None

        nodes = [
            ProductionTrackingNodeItem(
                node_key="plan",
                node_name="生产计划",
                owner="生产计划",
                status="done" if plan_progress >= 100 else "in_progress",
                progress=plan_progress,
                source_type="production_plan",
                source_ref=str(plan.plan_no),
                updated_at=plan.updated_at or plan.created_at,
            ),
            ProductionTrackingNodeItem(
                node_key="material",
                node_name="齐料检查",
                owner="物料专员",
                status=material_status,
                progress=material_progress,
                source_type="production_plan_material",
                source_ref=f"{len(materials)}行 / 毛需求{required_total}",
                updated_at=max(material_times) if material_times else None,
            ),
            ProductionTrackingNodeItem(
                node_key="work_order",
                node_name="生产工单",
                owner="生产跟单",
                status=work_order_status,
                progress=work_order_progress,
                source_type="production_work_order",
                source_ref=work_order_ref,
                updated_at=work_order_updated,
            ),
            ProductionTrackingNodeItem(
                node_key="job_card",
                node_name="工票进度",
                owner="车间",
                status=card_status,
                progress=card_progress,
                source_type="production_job_card",
                source_ref=f"{len(cards)}张",
                updated_at=max(card_times) if card_times else None,
            ),
            ProductionTrackingNodeItem(
                node_key="exception",
                node_name="异常处理",
                owner="跟单",
                status=exception_status,
                progress=exception_progress,
                source_type="production_tracking_exception",
                source_ref=exception_ref,
                updated_at=exception_updated,
            ),
        ]
        node_indexes = {item.node_key: index for index, item in enumerate(nodes)}
        for event in node_events:
            item = ProductionTrackingNodeItem(
                event_id=int(event.id),
                node_key=str(event.node_key),
                node_name=str(event.node_name),
                owner=str(event.owner or ""),
                status=str(event.status),
                progress=int(event.progress or 0),
                source_type=str(event.source_type or "production_tracking_node"),
                source_ref=(str(event.source_ref) if event.source_ref else None),
                remark=(str(event.remark) if event.remark else None),
                updated_at=event.created_at,
            )
            if item.node_key in node_indexes:
                nodes[node_indexes[item.node_key]] = item
            else:
                node_indexes[item.node_key] = len(nodes)
                nodes.append(item)
        return nodes

    def register_tracking_exception(
        self,
        *,
        plan_id: int,
        payload: ProductionTrackingExceptionCreateRequest,
        operator: str,
        request_id: str | None = None,
    ) -> ProductionTrackingExceptionItem:
        plan = self._must_get_plan(plan_id=plan_id)
        self._validate_tracking_exception_payload(plan=plan, payload=payload, plan_id=plan_id, request_id=request_id)
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        exception_type = (self._text(payload.exception_type) or "progress").lower()
        severity = (self._text(payload.severity) or "medium").lower()
        status = (self._text(payload.status) or "open").lower()
        description = self._require_non_blank(
            payload.description,
            code=PRODUCTION_TRACKING_EXCEPTION_INVALID,
            message="异常说明不能为空",
        )
        owner = self._text(payload.owner) or operator
        scenario_tag = self._text(payload.scenario_tag)
        request_hash = self._production_operation_request_hash(
            {
                "plan_id": int(plan.id),
                "company": str(plan.company),
                "operation": "tracking_exception",
                "scenario_tag": scenario_tag,
                "exception_type": exception_type,
                "severity": severity,
                "status": status,
                "description": description,
                "owner": owner,
                "sales_order": str(plan.sales_order),
                "sales_order_item": str(plan.sales_order_item),
                "item_code": str(plan.item_code),
            }
        )
        existing_operation = self._get_plan_operation(
            company=str(plan.company),
            operation="tracking_exception",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if str(existing_operation.request_hash) != request_hash:
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")
            return self._production_tracking_exception_item_from_json(existing_operation.response_json)

        row = LyProductionTrackingException(
            exception_no=self._next_tracking_exception_no(),
            plan_id=int(plan.id),
            company=str(plan.company),
            plan_no=str(plan.plan_no),
            sales_order=str(plan.sales_order),
            sales_order_item=str(plan.sales_order_item),
            item_code=str(plan.item_code),
            exception_type=exception_type,
            severity=severity,
            status=status,
            description=description,
            owner=owner,
            created_by=operator,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        data = self._tracking_exception_item(row)
        self.session.add(
            LyProductionPlanOperation(
                plan_id=int(plan.id),
                company=str(plan.company),
                operation="tracking_exception",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=self._production_model_to_json(data),
                created_by=operator,
            )
        )
        self._log_status(
            plan_id=int(plan.id),
            from_status=str(plan.status),
            to_status=str(plan.status),
            action="tracking_exception",
            operator=operator,
            request_id=request_id,
        )
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return data

    def register_tracking_node_event(
        self,
        *,
        plan_id: int,
        payload: ProductionTrackingNodeEventRequest,
        operator: str,
        request_id: str | None = None,
    ) -> ProductionTrackingNodeEventData:
        plan = self._must_get_plan(plan_id=plan_id)
        self._validate_tracking_node_payload(plan=plan, payload=payload, plan_id=plan_id, request_id=request_id)
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        node_key = self._normalize_tracking_node_key(payload.node_key)
        node_name = self._text(payload.node_name) or PRODUCTION_TRACKING_NODE_DEFAULT_NAMES.get(node_key, node_key)
        owner = self._text(payload.owner) or operator
        status = (self._text(payload.status) or "").lower()
        progress = int(payload.progress)
        remark = self._text(payload.remark) or ""
        scenario_tag = self._text(payload.scenario_tag)
        header_request_id = self._text(request_id)
        request_hash = self._production_operation_request_hash(
            {
                "plan_id": int(plan.id),
                "company": str(plan.company),
                "operation": "tracking_node",
                "scenario_tag": scenario_tag,
                "node_key": node_key,
                "node_name": node_name,
                "owner": owner,
                "status": status,
                "progress": progress,
                "remark": remark,
                "sales_order": str(plan.sales_order),
                "sales_order_item": str(plan.sales_order_item),
                "item_code": str(plan.item_code),
            }
        )
        existing_operation = self._get_plan_operation(
            company=str(plan.company),
            operation="tracking_node",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if str(existing_operation.request_hash) != request_hash:
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")
            return self._production_tracking_node_event_from_json(existing_operation.response_json)

        row = LyProductionTrackingNodeEvent(
            event_no=self._next_tracking_node_event_no(),
            plan_id=int(plan.id),
            company=str(plan.company),
            plan_no=str(plan.plan_no),
            sales_order=str(plan.sales_order),
            sales_order_item=str(plan.sales_order_item),
            item_code=str(plan.item_code),
            node_key=node_key,
            node_name=node_name,
            owner=owner,
            status=status,
            progress=progress,
            remark=remark,
            source_type="production_tracking_node",
            source_ref=str(plan.plan_no),
            idempotency_key=idempotency_key,
            request_id=header_request_id,
            created_by=operator,
        )
        plan.updated_at = datetime.utcnow()
        self.session.add(row)
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        data = self._tracking_node_event_item(row)
        self.session.add(
            LyProductionPlanOperation(
                plan_id=int(plan.id),
                company=str(plan.company),
                operation="tracking_node",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=self._production_model_to_json(data),
                created_by=operator,
            )
        )
        self._log_status(
            plan_id=int(plan.id),
            from_status=str(plan.status),
            to_status=str(plan.status),
            action=f"tracking_node:{node_key}:{status}",
            operator=operator,
            request_id=request_id,
        )
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return data

    def material_check(
        self,
        *,
        plan_id: int,
        operator: str,
        payload: ProductionMaterialCheckRequest,
        request_id: str | None = None,
    ) -> ProductionMaterialCheckData:
        plan = self._must_get_plan(plan_id=plan_id)
        self._validate_plan_carriers(
            request_id=request_id,
            payload_request_id=payload.request_id,
            scenario_tag=payload.scenario_tag,
            idempotency_key=payload.idempotency_key,
            expected_operation="material_check",
            payload_operation=payload.operation,
            plan_id=plan_id,
            payload_plan_id=payload.plan_id,
            plan=plan,
            payload_sales_order=payload.sales_order,
            payload_sales_order_item=payload.sales_order_item,
            payload_item_code=payload.item_code,
            payload_bom_id=payload.bom_id,
        )
        native_order, native_item = self._ensure_plan_native_sales_order_link(plan=plan)
        warehouse = self._require_non_blank(
            payload.warehouse,
            code=PRODUCTION_WAREHOUSE_REQUIRED,
            message="warehouse 不能为空",
        )
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        request_hash = self._production_operation_request_hash(
            {
                "plan_id": int(plan.id),
                "company": str(plan.company),
                "operation": "material_check",
                "scenario_tag": str(payload.scenario_tag or "").strip(),
                "warehouse": warehouse,
                "sales_order": str(plan.sales_order),
                "sales_order_item": str(plan.sales_order_item),
                "item_code": str(plan.item_code),
                "bom_id": int(plan.bom_id),
            }
        )
        existing_operation = self._get_plan_operation(
            company=str(plan.company),
            operation="material_check",
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if str(existing_operation.request_hash) != request_hash:
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")
            return self._production_material_check_data_from_json(existing_operation.response_json)

        self._ensure_warehouse_master_active(company=str(plan.company), warehouse=warehouse)
        self._ensure_material_check_status_allowed(plan=plan)

        bom_rows = self._material_bom_rows_for_plan(plan=plan)
        if not bom_rows:
            raise BusinessException(code=PRODUCTION_BOM_NOT_FOUND, message="该款式未维护用料 BOM 明细，无法算料")
        bom_rows = self._filter_bom_rows_for_sales_order_item(bom_rows=bom_rows, sales_order_item=native_item)
        if not bom_rows:
            raise BusinessException(code=PRODUCTION_BOM_NOT_FOUND, message="该款式未维护匹配当前颜色/尺码的用料 BOM 明细，无法算料")
        self._ensure_material_bom_rows_active(company=str(plan.company), bom_rows=bom_rows)

        try:
            self.session.query(LyProductionPlanMaterial).filter(LyProductionPlanMaterial.plan_id == int(plan.id)).delete()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        snapshot_items: list[ProductionPlanMaterialSnapshotItem] = []
        checked_at = datetime.utcnow()
        planned_qty = Decimal(str(plan.planned_qty))
        available_budget: dict[tuple[str, str, str], Decimal] = {}
        for row in bom_rows:
            qty_per_piece = Decimal(str(row.qty_per_piece))
            loss_rate = Decimal(str(row.loss_rate or 0))
            required_qty = (planned_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
            material_item_code = str(row.material_item_code)
            uom = str(getattr(row, "uom", None) or "米").strip() or "米"
            availability_key = (str(plan.company), warehouse, material_item_code)
            if availability_key not in available_budget:
                stock_balance = self._local_material_stock_balance(
                    company=str(plan.company),
                    item_code=material_item_code,
                    warehouse=warehouse,
                )
                reserved_qty = self._reserved_material_stock_for_open_plans(
                    company=str(plan.company),
                    item_code=material_item_code,
                    warehouse=warehouse,
                    exclude_plan_id=int(plan.id),
                )
                available_budget[availability_key] = max(stock_balance - reserved_qty, Decimal("0"))
            available_qty = min(required_qty, max(available_budget[availability_key], Decimal("0")))
            available_budget[availability_key] -= available_qty
            shortage_qty = max(Decimal("0"), required_qty - available_qty)

            self.session.add(
                LyProductionPlanMaterial(
                    plan_id=int(plan.id),
                    bom_item_id=(int(row.id) if isinstance(row, LyApparelBomItem) else None),
                    material_item_code=material_item_code,
                    warehouse=warehouse,
                    uom=uom,
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
                    bom_item_id=(int(row.id) if isinstance(row, LyApparelBomItem) else None),
                    material_item_code=material_item_code,
                    warehouse=warehouse,
                    uom=uom,
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
        self._mark_native_sales_order_item_material_checked(order=native_order, line=native_item, operator=operator)
        self.session.flush()
        MaterialPurchaseService(self.session).sync_requirements_from_production_plan(plan=plan, actor=operator)
        self._log_status(
            plan_id=int(plan.id),
            from_status=previous,
            to_status="material_checked",
            action="material_check",
            operator=operator,
        )

        response = ProductionMaterialCheckData(
            plan_id=int(plan.id),
            snapshot_count=len(snapshot_items),
            items=snapshot_items,
        )
        self.session.add(
            LyProductionPlanOperation(
                plan_id=int(plan.id),
                company=str(plan.company),
                operation="material_check",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=self._production_model_to_json(response),
                created_by=operator,
            )
        )
        self.session.flush()
        return response

    def list_material_issues(
        self,
        *,
        query: ProductionMaterialIssueQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionMaterialIssueListData:
        try:
            sql = (
                self.session.query(LyProductionPlanMaterial, LyProductionPlan, LyProductionWorkOrderLink)
                .join(LyProductionPlan, LyProductionPlanMaterial.plan_id == LyProductionPlan.id)
                .outerjoin(LyProductionWorkOrderLink, LyProductionWorkOrderLink.plan_id == LyProductionPlan.id)
            )
            if query.company:
                sql = sql.filter(LyProductionPlan.company == query.company)
            if query.sales_order:
                sql = sql.filter(LyProductionPlan.sales_order == query.sales_order)
            if query.item_code:
                sql = sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.material_item_code:
                sql = sql.filter(LyProductionPlanMaterial.material_item_code == query.material_item_code)
            if query.warehouse:
                sql = sql.filter(LyProductionPlanMaterial.warehouse == query.warehouse)
            if query.from_date:
                sql = sql.filter(func.date(LyProductionPlanMaterial.checked_at) >= query.from_date)
            if query.to_date:
                sql = sql.filter(func.date(LyProductionPlanMaterial.checked_at) <= query.to_date)
            if query.keyword:
                keyword = f"%{query.keyword.strip()}%"
                sql = sql.filter(
                    or_(
                        LyProductionPlan.plan_no.like(keyword),
                        LyProductionPlan.sales_order.like(keyword),
                        LyProductionPlan.sales_order_item.like(keyword),
                        LyProductionPlan.item_code.like(keyword),
                        LyProductionPlanMaterial.material_item_code.like(keyword),
                        LyProductionPlanMaterial.warehouse.like(keyword),
                        LyProductionWorkOrderLink.work_order.like(keyword),
                    )
                )
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionMaterialIssueListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionMaterialIssueListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(LyProductionPlan.company.in_(sorted(readable_companies)))
            rows: list[tuple[LyProductionPlanMaterial, LyProductionPlan, LyProductionWorkOrderLink | None]] = (
                sql.order_by(LyProductionPlan.id.desc(), LyProductionPlanMaterial.id.asc()).all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        draft_map: dict[str, LyWarehouseStockEntryDraft] = {}
        issued_qty_map: dict[tuple[str, str, str], Decimal] = {}
        source_ids = {f"production_plan:{int(plan.id)}:material_issue" for _snapshot, plan, _link in rows}
        if source_ids and self._has_sqlite_tables({LyWarehouseStockEntryDraft.__tablename__, LyWarehouseStockEntryDraftItem.__tablename__}):
            try:
                draft_rows = (
                    self.session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
                    .join(LyWarehouseStockEntryDraftItem, LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id)
                    .filter(
                        LyWarehouseStockEntryDraft.source_type == "production_plan",
                        LyWarehouseStockEntryDraft.purpose == "Material Issue",
                        LyWarehouseStockEntryDraft.status != "cancelled",
                        LyWarehouseStockEntryDraft.source_id.in_(sorted(source_ids)),
                    )
                    .order_by(LyWarehouseStockEntryDraft.id.desc(), LyWarehouseStockEntryDraftItem.id.asc())
                    .all()
                )
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc

            for draft, line in draft_rows:
                source_id = str(draft.source_id)
                draft_map.setdefault(source_id, draft)
                item_code = str(line.item_code)
                warehouse = str(line.source_warehouse or draft.source_warehouse or "")
                key = (source_id, item_code, warehouse)
                issued_qty_map[key] = issued_qty_map.get(key, Decimal("0")) + Decimal(str(line.qty or 0))

        items: list[ProductionMaterialIssueListItem] = []
        for snapshot, plan, link in rows:
            source_id = f"production_plan:{int(plan.id)}:material_issue"
            material_item_code = str(snapshot.material_item_code)
            warehouse = str(snapshot.warehouse or "")
            required_qty = Decimal(str(snapshot.required_qty or 0)).quantize(Decimal("0.000001"))
            available_qty = Decimal(str(snapshot.available_qty or 0)).quantize(Decimal("0.000001"))
            shortage_qty = Decimal(str(snapshot.shortage_qty or 0)).quantize(Decimal("0.000001"))
            issued_qty = issued_qty_map.get((source_id, material_item_code, warehouse), Decimal("0")).quantize(Decimal("0.000001"))
            draft = draft_map.get(source_id)
            status = self._material_issue_read_status(required_qty=required_qty, issued_qty=issued_qty, shortage_qty=shortage_qty)
            if query.status and status != query.status:
                continue
            items.append(
                ProductionMaterialIssueListItem(
                    plan_id=int(plan.id),
                    plan_no=str(plan.plan_no),
                    work_order=str(link.work_order) if link and link.work_order else None,
                    company=str(plan.company),
                    sales_order=str(plan.sales_order),
                    sales_order_item=str(plan.sales_order_item),
                    item_code=str(plan.item_code),
                    material_item_code=material_item_code,
                    warehouse=warehouse,
                    required_qty=required_qty,
                    available_qty=available_qty,
                    issued_qty=issued_qty,
                    shortage_qty=shortage_qty,
                    status=status,
                    draft_id=int(draft.id) if draft is not None else None,
                    source_id=source_id,
                    stock_entry_status=str(draft.status) if draft is not None else None,
                    checked_at=snapshot.checked_at,
                    issued_at=draft.created_at if draft is not None else None,
                )
            )

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ProductionMaterialIssueListData(items=items[start:end], total=total, page=query.page, page_size=query.page_size)

    def create_material_issue_draft(
        self,
        *,
        plan_id: int,
        operator: str,
        payload: ProductionMaterialIssueRequest,
        request_id: str | None = None,
    ) -> ProductionMaterialIssueData:
        plan = self._must_get_plan(plan_id=plan_id)
        self._validate_plan_carriers(
            request_id=request_id,
            payload_request_id=payload.request_id,
            scenario_tag=payload.scenario_tag,
            idempotency_key=payload.idempotency_key,
            expected_operation="material_issue",
            payload_operation=payload.operation,
            plan_id=plan_id,
            payload_plan_id=payload.plan_id,
            plan=plan,
            payload_sales_order=payload.sales_order,
            payload_sales_order_item=payload.sales_order_item,
            payload_item_code=payload.item_code,
            payload_bom_id=payload.bom_id,
        )
        self._ensure_plan_native_sales_order_link(plan=plan)
        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED,
            message="idempotency_key 不能为空",
        )
        warehouse = self._require_non_blank(
            payload.warehouse,
            code=PRODUCTION_WAREHOUSE_REQUIRED,
            message="warehouse 不能为空",
        )
        if payload.business_date is None:
            raise BusinessException(code=PRODUCTION_START_DATE_REQUIRED, message="business_date 不能为空")

        try:
            snapshots = (
                self.session.query(LyProductionPlanMaterial)
                .filter(LyProductionPlanMaterial.plan_id == int(plan.id))
                .order_by(LyProductionPlanMaterial.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not snapshots:
            raise BusinessException(code=PRODUCTION_MATERIAL_ISSUE_NOT_READY, message="请先执行算料")

        issue_rows: list[dict[str, Any]] = []
        for snapshot in snapshots:
            required_qty = Decimal(str(snapshot.required_qty or 0)).quantize(Decimal("0.000001"))
            available_qty = Decimal(str(snapshot.available_qty or 0)).quantize(Decimal("0.000001"))
            shortage_qty = Decimal(str(snapshot.shortage_qty or 0)).quantize(Decimal("0.000001"))
            snapshot_warehouse = str(snapshot.warehouse or "").strip()
            if snapshot_warehouse != warehouse:
                raise BusinessException(code=PRODUCTION_MATERIAL_ISSUE_NOT_READY, message="领料仓库与算料仓库不一致")
            if required_qty <= Decimal("0"):
                continue
            if shortage_qty > Decimal("0") or available_qty < required_qty:
                raise BusinessException(code=PRODUCTION_MATERIAL_ISSUE_NOT_READY, message="物料未齐，不能生成生产领料")
            issue_rows.append(
                {
                    "material_item_code": str(snapshot.material_item_code),
                    "warehouse": snapshot_warehouse,
                    "qty": required_qty,
                    "uom": self._bom_uom_for_snapshot(snapshot=snapshot),
                }
            )
        if not issue_rows:
            raise BusinessException(code=PRODUCTION_MATERIAL_ISSUE_NOT_READY, message="没有可领料物料")

        source_id = f"production_plan:{int(plan.id)}:material_issue"
        stock_idempotency_key = f"production-material-issue:{idempotency_key}"
        event_payload = self._build_material_issue_event_payload(
            plan=plan,
            source_id=source_id,
            business_date=payload.business_date,
            warehouse=warehouse,
            issue_rows=issue_rows,
        )
        existing = (
            self.session.query(LyWarehouseStockEntryDraft)
            .filter(
                LyWarehouseStockEntryDraft.company == str(plan.company),
                LyWarehouseStockEntryDraft.idempotency_key == stock_idempotency_key,
            )
            .first()
        )
        if existing is not None:
            self._ensure_material_issue_replay_matches(
                draft=existing,
                source_id=source_id,
                warehouse=warehouse,
                event_payload=event_payload,
                issue_rows=issue_rows,
            )
            return self._build_material_issue_data(plan_id=int(plan.id), draft=existing)

        existing_by_source = (
            self.session.query(LyWarehouseStockEntryDraft)
            .filter(
                LyWarehouseStockEntryDraft.company == str(plan.company),
                LyWarehouseStockEntryDraft.source_type == "production_plan",
                LyWarehouseStockEntryDraft.source_id == source_id,
                LyWarehouseStockEntryDraft.status != "cancelled",
            )
            .first()
        )
        if existing_by_source is not None:
            self._ensure_material_issue_replay_matches(
                draft=existing_by_source,
                source_id=source_id,
                warehouse=warehouse,
                event_payload=event_payload,
                issue_rows=issue_rows,
            )
            return self._build_material_issue_data(plan_id=int(plan.id), draft=existing_by_source)

        self._ensure_warehouse_master_active(company=str(plan.company), warehouse=warehouse)
        now = datetime.utcnow()
        event_key = self._build_material_issue_event_key(
            company=str(plan.company),
            plan_id=int(plan.id),
            idempotency_key=stock_idempotency_key,
        )
        try:
            draft = LyWarehouseStockEntryDraft(
                company=str(plan.company),
                purpose="Material Issue",
                source_type="production_plan",
                source_id=source_id,
                source_warehouse=warehouse,
                target_warehouse=None,
                status="pending_outbox",
                created_by=operator,
                created_at=now,
                idempotency_key=stock_idempotency_key,
                event_key=event_key,
            )
            self.session.add(draft)
            self.session.flush()
            for row in issue_rows:
                self.session.add(
                    LyWarehouseStockEntryDraftItem(
                        draft_id=int(draft.id),
                        company=str(plan.company),
                        item_code=str(row["material_item_code"]),
                        qty=Decimal(str(row["qty"])),
                        uom=str(row["uom"]),
                        source_warehouse=warehouse,
                        target_warehouse=None,
                    )
                )
            self.session.add(
                LyWarehouseStockEntryOutboxEvent(
                    draft_id=int(draft.id),
                    event_type="production_material_issue_sync",
                    event_key=event_key,
                    payload={"draft_id": int(draft.id), **event_payload},
                    status="in_pending",
                    retry_count=0,
                    created_at=now,
                )
            )
            previous = str(plan.status)
            if previous != "material_issued":
                plan.status = "material_issued"
                self._log_status(
                    plan_id=int(plan.id),
                    from_status=previous,
                    to_status="material_issued",
                    action="material_issue",
                    operator=operator,
                    request_id=request_id,
                )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return self._build_material_issue_data(plan_id=int(plan.id), draft=draft)

    def ensure_material_check_status_allowed(self, *, plan_id: int) -> str:
        plan = self._must_get_plan(plan_id=plan_id)
        return self._ensure_material_check_status_allowed(plan=plan)

    def get_material_issue_resource_scopes(self, *, plan_id: int, warehouse: str | None) -> list[dict[str, str]]:
        plan = self._must_get_plan(plan_id=plan_id)
        issue_warehouse = self._require_non_blank(
            warehouse,
            code=PRODUCTION_WAREHOUSE_REQUIRED,
            message="warehouse 不能为空",
        )
        try:
            snapshots = (
                self.session.query(LyProductionPlanMaterial)
                .filter(LyProductionPlanMaterial.plan_id == int(plan.id))
                .order_by(LyProductionPlanMaterial.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not snapshots:
            return [
                {
                    "company": str(plan.company),
                    "warehouse": issue_warehouse,
                    "item_code": str(plan.item_code),
                }
            ]

        scopes: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for snapshot in snapshots:
            material_item_code = str(snapshot.material_item_code or "").strip()
            snapshot_warehouse = str(snapshot.warehouse or "").strip() or issue_warehouse
            if not material_item_code:
                continue
            key = (str(plan.company), snapshot_warehouse, material_item_code)
            if key in seen:
                continue
            seen.add(key)
            scopes.append({"company": key[0], "warehouse": key[1], "item_code": key[2]})
        return scopes or [{"company": str(plan.company), "warehouse": issue_warehouse, "item_code": str(plan.item_code)}]

    def create_work_order_outbox(
        self,
        *,
        plan_id: int,
        payload: ProductionCreateWorkOrderRequest,
        operator: str,
        request_id: str | None,
    ) -> ProductionCreateWorkOrderData:
        plan = self._must_get_plan(plan_id=plan_id)
        validated_request_id = self._validate_plan_carriers(
            request_id=request_id,
            payload_request_id=payload.request_id,
            scenario_tag=payload.scenario_tag,
            idempotency_key=payload.idempotency_key,
            expected_operation="create_work_order",
            payload_operation=payload.operation,
            plan_id=plan_id,
            payload_plan_id=payload.plan_id,
            plan=plan,
            payload_sales_order=payload.sales_order,
            payload_sales_order_item=payload.sales_order_item,
            payload_item_code=payload.item_code,
            payload_bom_id=payload.bom_id,
        )
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
        if link is not None and link.work_order:
            existing = self.outbox_service.find_existing(
                plan_id=int(plan.id),
                action=ProductionWorkOrderOutboxService.ACTION_CREATE_WORK_ORDER,
            )
            if existing is not None:
                return ProductionCreateWorkOrderData(
                    plan_id=int(plan.id),
                    outbox_id=int(existing.id),
                    event_key=str(existing.event_key),
                    sync_status=str(link.sync_status or existing.status),
                    work_order=str(link.work_order),
                )
            return ProductionCreateWorkOrderData(
                plan_id=int(plan.id),
                outbox_id=0,
                event_key="",
                sync_status=str(link.sync_status or "pending"),
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
            link = (
                self.session.query(LyProductionWorkOrderLink)
                .filter(LyProductionWorkOrderLink.plan_id == int(plan.id))
                .first()
            )
            return ProductionCreateWorkOrderData(
                plan_id=int(plan.id),
                outbox_id=int(existing_by_idempotency.id),
                event_key=str(existing_by_idempotency.event_key),
                sync_status=str(existing_by_idempotency.status),
                work_order=(
                    str(existing_by_idempotency.erpnext_work_order)
                    if existing_by_idempotency.erpnext_work_order
                    else (str(link.work_order) if link and link.work_order else None)
                ),
            )

        existing_active = self.outbox_service.find_existing(
            plan_id=int(plan.id),
            action=ProductionWorkOrderOutboxService.ACTION_CREATE_WORK_ORDER,
            statuses=["pending", "processing"],
        )
        if existing_active is not None:
            link = (
                self.session.query(LyProductionWorkOrderLink)
                .filter(LyProductionWorkOrderLink.plan_id == int(plan.id))
                .first()
            )
            return ProductionCreateWorkOrderData(
                plan_id=int(plan.id),
                outbox_id=int(existing_active.id),
                event_key=str(existing_active.event_key),
                sync_status=str(existing_active.status),
                work_order=(
                    str(existing_active.erpnext_work_order)
                    if existing_active.erpnext_work_order
                    else (str(link.work_order) if link and link.work_order else None)
                ),
            )

        outbox = self.outbox_service.create_outbox(
            plan_id=int(plan.id),
            company=str(plan.company),
            item_code=str(plan.item_code),
            idempotency_key=idempotency_key,
            payload_json=payload_json,
            payload_hash=payload_hash,
            request_id=validated_request_id,
            operator=operator,
        )
        local_work_order = self._build_local_work_order(plan_no=str(plan.plan_no), plan_id=int(plan.id))
        outbox.erpnext_work_order = local_work_order
        self._upsert_work_order_link(
            plan=plan,
            work_order=local_work_order,
            operator=operator,
            sync_status="pending",
            request_id=validated_request_id,
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
                request_id=validated_request_id,
            )

        return ProductionCreateWorkOrderData(
            plan_id=int(plan.id),
            outbox_id=int(outbox.id),
            event_key=str(outbox.event_key),
            sync_status=str(outbox.status),
            work_order=local_work_order,
        )

    def sync_job_cards(
        self,
        *,
        work_order: str,
        operator: str,
        payload: ProductionSyncJobCardsRequest,
        request_id: str | None,
    ) -> ProductionSyncJobCardsData:
        link = (
            self.session.query(LyProductionWorkOrderLink)
            .filter(LyProductionWorkOrderLink.work_order == work_order)
            .first()
        )
        if link is None:
            raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="Work Order 映射不存在")

        plan = self._must_get_plan(plan_id=int(link.plan_id))
        validated_request_id = self._validate_sync_job_cards_carriers(
            request_id=request_id,
            payload=payload,
            work_order=work_order,
            plan=plan,
        )
        now = datetime.utcnow()
        expected_qty = Decimal(str(plan.planned_qty))
        operation_specs = [
            ("CUT", "裁剪", 10),
            ("SEW", "车缝", 20),
            ("FIN", "后整", 30),
        ]

        upserted: list[ProductionJobCardLinkItem] = []
        for code, operation_name, sequence in operation_specs:
            job_card_no = self._build_local_job_card_no(work_order=work_order, operation_code=code)
            row = (
                self.session.query(LyProductionJobCardLink)
                .filter(LyProductionJobCardLink.job_card == job_card_no)
                .first()
            )
            if row is None:
                row = LyProductionJobCardLink(
                    plan_id=int(plan.id),
                    work_order=work_order,
                    job_card=job_card_no,
                    company=str(plan.company),
                    item_code=str(plan.item_code),
                )
                self.session.add(row)

            row.plan_id = int(plan.id)
            row.work_order = work_order
            row.company = str(plan.company)
            row.item_code = str(plan.item_code)
            row.operation = operation_name
            row.operation_sequence = sequence
            row.expected_qty = expected_qty
            row.completed_qty = Decimal("0")
            row.erpnext_status = "LocalSynced"
            row.synced_at = now

            upserted.append(
                ProductionJobCardLinkItem(
                    job_card=job_card_no,
                    operation=operation_name,
                    operation_sequence=sequence,
                    company=str(plan.company),
                    item_code=str(plan.item_code),
                    expected_qty=expected_qty,
                    completed_qty=Decimal("0"),
                    erpnext_status="LocalSynced",
                    synced_at=row.synced_at,
                )
            )

        link.erpnext_docstatus = 1
        link.erpnext_status = "LocalSynced"
        link.sync_status = "succeeded"
        link.last_synced_at = now

        latest_outbox = self.outbox_service.latest_by_plan_ids(plan_ids=[int(plan.id)]).get(int(plan.id))
        if latest_outbox is not None:
            latest_outbox.status = "succeeded"
            latest_outbox.erpnext_work_order = work_order
            latest_outbox.last_error_code = None
            latest_outbox.last_error_message = None
            latest_outbox.locked_by = None
            latest_outbox.locked_at = None
            latest_outbox.lease_until = None

        previous = str(plan.status)
        next_status = "job_cards_synced"
        if previous != next_status:
            plan.status = next_status
        self._log_status(
            plan_id=int(plan.id),
            from_status=previous,
            to_status=str(plan.status),
            action="sync_job_cards",
            operator=operator,
            request_id=validated_request_id,
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

    def _ensure_plan_native_sales_order_link(self, *, plan: LyProductionPlan) -> tuple[LySalesOrder, LySalesOrderItem]:
        sales_order = str(plan.sales_order or "").strip()
        sales_order_item = str(plan.sales_order_item or "").strip()
        if not sales_order:
            raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="生产计划缺少 Sales Order")
        if not sales_order_item:
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="生产计划缺少 Sales Order 行")
        try:
            order = (
                self.session.query(LySalesOrder)
                .filter(
                    LySalesOrder.company == str(plan.company),
                    LySalesOrder.sales_order_no == sales_order,
                )
                .first()
            )
            if order is None:
                raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="生产计划关联的 Sales Order 不存在")
            if str(order.status or "").strip().lower() == "cancelled" or int(order.docstatus or 0) == 2:
                raise BusinessException(code=PRODUCTION_SO_CLOSED_OR_CANCELLED, message="Sales Order 已关闭或已取消")
            line = (
                self.session.query(LySalesOrderItem)
                .filter(
                    LySalesOrderItem.sales_order_id == int(order.id),
                    LySalesOrderItem.sales_order_item == sales_order_item,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_native_sales_order_table(exc):
                raise DatabaseReadFailed() from exc
            raise DatabaseReadFailed() from exc
        if line is None:
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="生产计划关联的 Sales Order 行不存在")
        if str(line.item_code or "").strip() != str(plan.item_code or "").strip():
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="生产计划关联的 Sales Order 行物料不匹配")
        return order, line

    @staticmethod
    def _mark_native_sales_order_item_material_checked(
        *,
        order: LySalesOrder,
        line: LySalesOrderItem,
        operator: str,
    ) -> None:
        line.ys_material_calc_state = "已算料"
        order.updated_by = operator

    def _local_material_stock_balance(self, *, company: str, item_code: str, warehouse: str) -> Decimal:
        if not self._has_sqlite_tables({LyWarehouseStockEntryDraft.__tablename__, LyWarehouseStockEntryDraftItem.__tablename__}):
            return Decimal("0")
        try:
            from app.services.warehouse_service import WarehouseService

            summary = WarehouseService(session=self.session).get_local_stock_summary(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        for row in summary.items:
            if str(row.company) == company and str(row.warehouse) == warehouse and str(row.item_code) == item_code:
                return Decimal(str(row.actual_qty or 0))
        return Decimal("0")

    def _reserved_material_stock_for_open_plans(
        self,
        *,
        company: str,
        item_code: str,
        warehouse: str,
        exclude_plan_id: int,
    ) -> Decimal:
        if not self._has_sqlite_tables({LyProductionPlan.__tablename__, LyProductionPlanMaterial.__tablename__}):
            return Decimal("0")
        try:
            reserved_qty = (
                self.session.query(func.coalesce(func.sum(LyProductionPlanMaterial.available_qty), 0))
                .join(LyProductionPlan, LyProductionPlan.id == LyProductionPlanMaterial.plan_id)
                .filter(
                    LyProductionPlan.company == company,
                    LyProductionPlan.id != int(exclude_plan_id),
                    LyProductionPlan.status.notin_(("cancelled", "material_issued")),
                    LyProductionPlanMaterial.material_item_code == item_code,
                    LyProductionPlanMaterial.warehouse == warehouse,
                )
                .scalar()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_table_error(exc, LyProductionPlanMaterial.__tablename__) or self._is_missing_table_error(
                exc,
                LyProductionPlan.__tablename__,
            ):
                return Decimal("0")
            raise DatabaseReadFailed() from exc
        return Decimal(str(reserved_qty or 0)).quantize(Decimal("0.000001"))

    def _bom_uom_for_snapshot(self, *, snapshot: LyProductionPlanMaterial) -> str:
        snapshot_uom = str(getattr(snapshot, "uom", None) or "").strip()
        if snapshot_uom:
            return snapshot_uom
        if snapshot.bom_item_id is None:
            return "米"
        try:
            bom_item = self.session.query(LyApparelBomItem).filter(LyApparelBomItem.id == int(snapshot.bom_item_id)).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if bom_item is None:
            return "米"
        return str(bom_item.uom or "米")

    @staticmethod
    def _build_material_issue_event_payload(
        *,
        plan: LyProductionPlan,
        source_id: str,
        business_date: date,
        warehouse: str,
        issue_rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "company": str(plan.company),
            "purpose": "Material Issue",
            "source_type": "production_plan",
            "source_id": source_id,
            "business_date": business_date.isoformat(),
            "sales_order": str(plan.sales_order),
            "sales_order_item": str(plan.sales_order_item),
            "item_code": str(plan.item_code),
            "warehouse": warehouse,
            "items": [
                {
                    "item_code": str(row["material_item_code"]),
                    "qty": str(row["qty"]),
                    "uom": str(row["uom"]),
                    "source_warehouse": warehouse,
                }
                for row in issue_rows
            ],
        }

    def _ensure_material_issue_replay_matches(
        self,
        *,
        draft: LyWarehouseStockEntryDraft,
        source_id: str,
        warehouse: str,
        event_payload: dict[str, Any],
        issue_rows: list[dict[str, Any]],
    ) -> None:
        if (
            str(draft.purpose) != "Material Issue"
            or str(draft.source_type) != "production_plan"
            or str(draft.source_id) != source_id
            or str(draft.source_warehouse or "") != warehouse
        ):
            raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")
        try:
            lines = (
                self.session.query(LyWarehouseStockEntryDraftItem)
                .filter(LyWarehouseStockEntryDraftItem.draft_id == int(draft.id))
                .order_by(LyWarehouseStockEntryDraftItem.id.asc())
                .all()
            )
            outbox = (
                self.session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(
                    LyWarehouseStockEntryOutboxEvent.draft_id == int(draft.id),
                    LyWarehouseStockEntryOutboxEvent.event_type == "production_material_issue_sync",
                )
                .order_by(LyWarehouseStockEntryOutboxEvent.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if len(lines) != len(issue_rows) or outbox is None:
            raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")
        for line, row in zip(lines, issue_rows, strict=True):
            if (
                str(line.item_code) != str(row["material_item_code"])
                or Decimal(str(line.qty)).quantize(Decimal("0.000001")) != Decimal(str(row["qty"])).quantize(Decimal("0.000001"))
                or str(line.uom) != str(row["uom"])
                or str(line.source_warehouse or draft.source_warehouse or "") != warehouse
            ):
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")

        actual_payload = dict(outbox.payload or {})
        actual_payload.pop("draft_id", None)
        if actual_payload != event_payload:
            raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突且请求内容不一致")

    def _build_material_issue_data(self, *, plan_id: int, draft: LyWarehouseStockEntryDraft) -> ProductionMaterialIssueData:
        try:
            lines = (
                self.session.query(LyWarehouseStockEntryDraftItem)
                .filter(LyWarehouseStockEntryDraftItem.draft_id == int(draft.id))
                .order_by(LyWarehouseStockEntryDraftItem.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return ProductionMaterialIssueData(
            plan_id=plan_id,
            draft_id=int(draft.id),
            source_id=str(draft.source_id),
            stock_entry_status=str(draft.status),
            event_key=str(draft.event_key),
            items=[
                ProductionMaterialIssueItem(
                    material_item_code=str(line.item_code),
                    warehouse=str(line.source_warehouse or draft.source_warehouse or ""),
                    qty=Decimal(str(line.qty)),
                    uom=str(line.uom),
                )
                for line in lines
            ],
        )

    @staticmethod
    def _build_material_issue_event_key(*, company: str, plan_id: int, idempotency_key: str) -> str:
        raw = "|".join([company, str(plan_id), idempotency_key]).encode("utf-8")
        return f"pmi:{hashlib.sha256(raw).hexdigest()}"

    @staticmethod
    def _material_issue_read_status(*, required_qty: Decimal, issued_qty: Decimal, shortage_qty: Decimal) -> str:
        if shortage_qty > Decimal("0"):
            return "shortage"
        if issued_qty <= Decimal("0"):
            return "ready"
        if issued_qty < required_qty:
            return "partially_issued"
        return "issued"

    def _get_plan_operation(self, *, company: str, operation: str, idempotency_key: str) -> LyProductionPlanOperation | None:
        try:
            return (
                self.session.query(LyProductionPlanOperation)
                .filter(
                    LyProductionPlanOperation.company == company,
                    LyProductionPlanOperation.operation == operation,
                    LyProductionPlanOperation.idempotency_key == idempotency_key,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    @staticmethod
    def _production_operation_request_hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _production_model_to_json(model: Any) -> dict[str, Any]:
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="json")
        return json.loads(model.json())

    @classmethod
    def _production_material_check_data_from_json(cls, payload: dict[str, Any]) -> ProductionMaterialCheckData:
        if hasattr(ProductionMaterialCheckData, "model_validate"):
            return ProductionMaterialCheckData.model_validate(payload)
        return ProductionMaterialCheckData.parse_obj(payload)

    @staticmethod
    def _ensure_material_check_status_allowed(*, plan: LyProductionPlan) -> str:
        status = str(plan.status or "").strip()
        if status not in PRODUCTION_MATERIAL_CHECK_ALLOWED_STATUSES:
            raise BusinessException(
                code=PRODUCTION_MATERIAL_CHECK_STATUS_INVALID,
                message="当前生产计划状态不允许执行物料检查",
            )
        return status

    def _resolve_bom(self, *, company: str, item_code: str, bom_id: int | None) -> LyApparelBom:
        try:
            if bom_id is not None:
                row = self.session.query(LyApparelBom).filter(LyApparelBom.id == int(bom_id)).first()
            else:
                row = (
                    self.session.query(LyApparelBom)
                    .filter(
                        LyApparelBom.company == company,
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
        if str(row.company or "").strip() != company:
            raise BusinessException(code=PRODUCTION_BOM_ITEM_MISMATCH, message="BOM 与 Sales Order 公司不一致")
        return row

    def _load_sales_order_context(
        self,
        *,
        payload: ProductionPlanCreateRequest,
        request_id: str | None = None,
    ) -> tuple[Any, ERPNextSalesOrderItem, str]:
        sales_order_name = payload.sales_order.strip()
        native_context = self._build_native_sales_order_context(payload=payload)
        if native_context is not None:
            return native_context
        raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message=f"Sales Order 不存在: {sales_order_name}")

    def _build_native_sales_order_context(
        self,
        *,
        payload: ProductionPlanCreateRequest,
    ) -> tuple[ERPNextSalesOrder, ERPNextSalesOrderItem, str] | None:
        try:
            order = (
                self.session.query(LySalesOrder)
                .filter(LySalesOrder.sales_order_no == payload.sales_order.strip())
                .first()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_native_sales_order_table(exc):
                raise DatabaseReadFailed() from exc
            raise DatabaseReadFailed() from exc
        if order is None:
            return None

        status = str(order.status or "").strip().lower()
        if status == "cancelled" or int(order.docstatus or 0) == 2:
            raise BusinessException(code=PRODUCTION_SO_CLOSED_OR_CANCELLED, message="Sales Order 已关闭或已取消")

        try:
            item_rows = (
                self.session.query(LySalesOrderItem)
                .filter(LySalesOrderItem.sales_order_id == int(order.id))
                .order_by(LySalesOrderItem.line_no.asc(), LySalesOrderItem.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_native_sales_order_table(exc):
                raise DatabaseReadFailed() from exc
            raise DatabaseReadFailed() from exc
        if not item_rows:
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="Sales Order 行不存在")

        sales_items = [
            ERPNextSalesOrderItem(
                name=str(row.sales_order_item),
                item_code=str(row.item_code),
                qty=Decimal(str(row.qty)),
            )
            for row in item_rows
        ]
        target_item = self._select_sales_order_item(
            sales_items=sales_items,
            item_code=payload.item_code.strip(),
            sales_order_item=(payload.sales_order_item.strip() if payload.sales_order_item else None),
        )
        company = str(order.company or "").strip()
        if not company:
            raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="Sales Order company 缺失")
        sales_order = ERPNextSalesOrder(
            name=str(order.sales_order_no),
            docstatus=int(order.docstatus or 0),
            status="Draft" if status == "draft" else "To Deliver and Bill",
            company=company,
            customer=(str(order.customer) if order.customer else None),
            items=tuple(sales_items),
        )
        return sales_order, target_item, company

    def _apply_native_sales_order_planned_qty(
        self,
        *,
        sales_order: str,
        sales_order_item: str,
        planned_qty: Decimal,
        operator: str,
    ) -> None:
        try:
            order = self.session.query(LySalesOrder).filter(LySalesOrder.sales_order_no == sales_order).first()
            if order is None:
                return
            line = (
                self.session.query(LySalesOrderItem)
                .filter(
                    LySalesOrderItem.sales_order_id == int(order.id),
                    LySalesOrderItem.sales_order_item == sales_order_item,
            )
                .first()
            )
        except SQLAlchemyError as exc:
            if self._is_missing_native_sales_order_table(exc):
                return
            raise DatabaseReadFailed() from exc
        if line is None:
            return
        line.planned_qty = Decimal(str(line.planned_qty or 0)) + Decimal(str(planned_qty))
        if str(order.status) == "draft":
            order.status = "planned"
        order.updated_by = operator

    @staticmethod
    def _is_missing_native_sales_order_table(exc: BaseException) -> bool:
        message = str(exc).lower()
        return "ly_sales_order" in message and ("no such table" in message or "does not exist" in message)

    def _build_local_scenario_sales_order_context(
        self,
        *,
        payload: ProductionPlanCreateRequest,
        request_id: str | None = None,
    ) -> tuple[ERPNextSalesOrder, ERPNextSalesOrderItem, str] | None:
        if not self._is_local_scenario_context_enabled():
            return None

        scenario_tag = self._extract_local_scenario_tag(payload=payload, request_id=request_id)
        if scenario_tag is None:
            return None

        item_code = payload.item_code.strip()
        sales_order_name = payload.sales_order.strip()
        sales_order_item_name = (payload.sales_order_item or "").strip()
        company = (payload.company or os.getenv("LINGYI_LOCAL_DEV_COMPANY", PRODUCTION_LOCAL_DEFAULT_COMPANY)).strip()
        if not company:
            raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="local scenario context 缺少 company")
        if not sales_order_item_name:
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="local scenario context 缺少 sales_order_item")

        planned_qty = Decimal(str(payload.planned_qty))
        local_scenario_item = ERPNextSalesOrderItem(
            name=sales_order_item_name,
            item_code=item_code,
            qty=planned_qty,
        )
        local_scenario_order = ERPNextSalesOrder(
            name=sales_order_name,
            docstatus=1,
            status="To Deliver and Bill",
            company=company,
            customer=f"LOCAL_SCENARIO_{scenario_tag}",
            items=(local_scenario_item,),
        )
        return local_scenario_order, local_scenario_item, company

    @staticmethod
    def _is_local_scenario_context_enabled() -> bool:
        app_env = os.getenv("APP_ENV", "").strip().lower()
        db_url = os.getenv("LINGYI_DB_URL", "").strip()
        return app_env == "development" and db_url == PRODUCTION_LOCAL_ALLOWED_DB_URL

    @staticmethod
    def _extract_local_scenario_tag(
        payload: ProductionPlanCreateRequest,
        request_id: str | None = None,
    ) -> str | None:
        scenario_tag = (payload.scenario_tag or "").strip()
        if not scenario_tag:
            return None
        if not PRODUCTION_PLAN_SCENARIO_TAG_PATTERN.fullmatch(scenario_tag):
            raise BusinessException(
                code=PRODUCTION_IDEMPOTENCY_CONFLICT,
                message=f"{PRODUCTION_GATE_ERROR_PREFIX}invalid_scenario_tag",
            )
        request_id_value = (request_id or "").strip()
        if not request_id_value:
            raise BusinessException(
                code=PRODUCTION_IDEMPOTENCY_CONFLICT,
                message=f"{PRODUCTION_GATE_ERROR_PREFIX}missing_request_id",
            )
        if scenario_tag not in request_id_value:
            raise BusinessException(
                code=PRODUCTION_IDEMPOTENCY_CONFLICT,
                message=f"{PRODUCTION_GATE_ERROR_PREFIX}mismatched_request_id",
            )
        return scenario_tag

    @staticmethod
    def _raise_gate_error(message: str) -> None:
        raise BusinessException(
            code=PRODUCTION_IDEMPOTENCY_CONFLICT,
            message=f"{PRODUCTION_GATE_ERROR_PREFIX}{message}",
        )

    @staticmethod
    def _ensure_local_dev_write_gate() -> None:
        app_env = os.getenv("APP_ENV", "").strip().lower()
        db_url = os.getenv("LINGYI_DB_URL", "").strip()
        if app_env != "development" or db_url != PRODUCTION_LOCAL_ALLOWED_DB_URL:
            ProductionService._raise_gate_error("non_local_dev_gate")

    def _validate_create_plan_gate(
        self,
        *,
        payload: ProductionPlanCreateRequest,
        request_id: str | None,
    ) -> None:
        scenario_value = (payload.scenario_tag or "").strip()
        if not scenario_value or PRODUCTION_PLAN_SCENARIO_TAG_PATTERN.fullmatch(scenario_value) is None:
            if not (payload.idempotency_key or "").strip():
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_KEY_REQUIRED, message="幂等键不能为空")
            if payload.operation and payload.operation.strip() not in {"create", "create_plan"}:
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="operation 非法")
            if not payload.sales_order.strip() or not payload.item_code.strip():
                raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="订单与款号不能为空")
            return

        self._ensure_local_dev_write_gate()
        scenario_tag = self._require_non_blank(
            payload.scenario_tag,
            code=PRODUCTION_IDEMPOTENCY_CONFLICT,
            message=f"{PRODUCTION_GATE_ERROR_PREFIX}missing_scenario_tag",
        )
        if not PRODUCTION_PLAN_SCENARIO_TAG_PATTERN.fullmatch(scenario_tag):
            self._raise_gate_error("invalid_scenario_tag")

        if (payload.operation or "").strip() != "create":
            self._raise_gate_error("mismatched_operation")
        if not (payload.sales_order_item or "").strip():
            self._raise_gate_error("mismatched_business_carrier")

        idempotency_key = self._require_non_blank(
            payload.idempotency_key,
            code=PRODUCTION_IDEMPOTENCY_CONFLICT,
            message=f"{PRODUCTION_GATE_ERROR_PREFIX}missing_idempotency_key",
        )
        if scenario_tag not in idempotency_key:
            self._raise_gate_error("mismatched_business_carrier")

        self._validate_request_id_and_scenario(
            request_id=request_id,
            payload_request_id=None,
            scenario_tag=scenario_tag,
        )

    def _validate_plan_carriers(
        self,
        *,
        request_id: str | None,
        payload_request_id: str | None,
        scenario_tag: str | None,
        idempotency_key: str | None,
        expected_operation: str,
        payload_operation: str | None,
        plan_id: int,
        payload_plan_id: int | None,
        plan: LyProductionPlan,
        payload_sales_order: str | None,
        payload_sales_order_item: str | None,
        payload_item_code: str | None,
        payload_bom_id: int | None,
    ) -> str:
        self._ensure_local_dev_write_gate()
        normalized_scenario = (scenario_tag or "").strip()
        if not normalized_scenario:
            self._raise_gate_error("missing_scenario_tag")
        if not PRODUCTION_PLAN_DETAIL_SCENARIO_TAG_PATTERN.fullmatch(normalized_scenario):
            self._raise_gate_error("invalid_scenario_tag")

        idempotency = (idempotency_key or "").strip()
        if not idempotency:
            self._raise_gate_error("missing_idempotency_key")
        if normalized_scenario not in idempotency:
            self._raise_gate_error("mismatched_business_carrier")

        if (payload_operation or "").strip() != expected_operation:
            self._raise_gate_error("mismatched_operation")
        if payload_plan_id is None or int(payload_plan_id) != int(plan_id):
            self._raise_gate_error("mismatched_plan_id")
        if int(plan.id) != int(plan_id):
            self._raise_gate_error("mismatched_plan_id")
        if (payload_sales_order or "").strip() != str(plan.sales_order):
            self._raise_gate_error("mismatched_business_carrier")
        if (payload_sales_order_item or "").strip() != str(plan.sales_order_item):
            self._raise_gate_error("mismatched_business_carrier")
        if (payload_item_code or "").strip() != str(plan.item_code):
            self._raise_gate_error("mismatched_business_carrier")
        if payload_bom_id is None or int(payload_bom_id) != int(plan.bom_id):
            self._raise_gate_error("mismatched_business_carrier")

        return self._validate_request_id_and_scenario(
            request_id=request_id,
            payload_request_id=payload_request_id,
            scenario_tag=normalized_scenario,
        )

    def _validate_sync_job_cards_carriers(
        self,
        *,
        request_id: str | None,
        payload: ProductionSyncJobCardsRequest,
        work_order: str,
        plan: LyProductionPlan,
    ) -> str:
        self._ensure_local_dev_write_gate()

        scenario_tag = (payload.scenario_tag or "").strip()
        if not scenario_tag:
            self._raise_gate_error("missing_scenario_tag")
        if not PRODUCTION_PLAN_DETAIL_SCENARIO_TAG_PATTERN.fullmatch(scenario_tag):
            self._raise_gate_error("invalid_scenario_tag")

        idempotency_key = (payload.idempotency_key or "").strip()
        if not idempotency_key:
            self._raise_gate_error("missing_idempotency_key")
        if scenario_tag not in idempotency_key:
            self._raise_gate_error("mismatched_business_carrier")

        if (payload.operation or "").strip() != "sync_job_cards":
            self._raise_gate_error("mismatched_operation")
        if payload.plan_id is None or int(payload.plan_id) != int(plan.id):
            self._raise_gate_error("mismatched_plan_id")

        plan_no_or_work_order = (payload.plan_no_or_work_order or "").strip()
        if not plan_no_or_work_order:
            self._raise_gate_error("mismatched_plan_no_or_work_order")
        allowed_plan_markers = {str(plan.plan_no), work_order}
        if plan_no_or_work_order not in allowed_plan_markers:
            self._raise_gate_error("mismatched_plan_no_or_work_order")

        company = (payload.company or "").strip()
        if company != str(plan.company):
            self._raise_gate_error("mismatched_company")

        item_code = (payload.item_code or "").strip()
        if item_code != str(plan.item_code):
            self._raise_gate_error("mismatched_item_code")

        source_ref = (payload.source_ref or "").strip()
        if not source_ref:
            self._raise_gate_error("mismatched_source_ref")
        source_parts = [part.strip() for part in source_ref.split("|")]
        if len(source_parts) != 6:
            self._raise_gate_error("mismatched_source_ref")
        (
            source_scenario_tag,
            source_company,
            source_plan_id,
            source_plan_no_or_work_order,
            source_item_code,
            source_operation,
        ) = source_parts
        if not PRODUCTION_PLAN_DETAIL_SCENARIO_TAG_PATTERN.fullmatch(source_scenario_tag):
            self._raise_gate_error("mismatched_source_ref")
        if source_scenario_tag != scenario_tag:
            self._raise_gate_error("mismatched_source_ref")
        if source_company != company:
            self._raise_gate_error("mismatched_company")
        if source_plan_id != str(plan.id):
            self._raise_gate_error("mismatched_plan_id")
        if source_plan_no_or_work_order != plan_no_or_work_order:
            self._raise_gate_error("mismatched_plan_no_or_work_order")
        if source_item_code != item_code:
            self._raise_gate_error("mismatched_item_code")
        if source_operation != "sync_job_cards":
            self._raise_gate_error("mismatched_operation")

        return self._validate_request_id_and_scenario(
            request_id=request_id,
            payload_request_id=payload.request_id,
            scenario_tag=scenario_tag,
        )

    def _validate_request_id_and_scenario(
        self,
        *,
        request_id: str | None,
        payload_request_id: str | None,
        scenario_tag: str,
    ) -> str:
        normalized_request_id = (request_id or "").strip()
        if not normalized_request_id:
            self._raise_gate_error("missing_request_id")
        if not is_request_id_valid(normalized_request_id):
            self._raise_gate_error("invalid_request_id_pattern")
        if payload_request_id is not None and payload_request_id.strip() and payload_request_id.strip() != normalized_request_id:
            self._raise_gate_error("mismatched_request_id")

        if scenario_tag not in normalized_request_id:
            self._raise_gate_error("mismatched_request_id")
        return normalized_request_id

    @staticmethod
    def _build_local_work_order(*, plan_no: str, plan_id: int) -> str:
        normalized_plan_no = re.sub(r"[^A-Za-z0-9-]", "", str(plan_no).upper())[:64] or f"PLAN{plan_id}"
        digest = hashlib.sha1(f"{plan_id}:{plan_no}".encode("utf-8")).hexdigest()[:8].upper()
        return f"WO-{normalized_plan_no}-{digest}"[:140]

    @staticmethod
    def _build_local_job_card_no(*, work_order: str, operation_code: str) -> str:
        normalized_work_order = re.sub(r"[^A-Za-z0-9-]", "", str(work_order).upper())[:80] or "WO"
        normalized_operation = re.sub(r"[^A-Za-z0-9-]", "", str(operation_code).upper())[:12] or "OP"
        digest = hashlib.sha1(f"{normalized_work_order}:{normalized_operation}".encode("utf-8")).hexdigest()[:8].upper()
        return f"JC-{normalized_work_order}-{normalized_operation}-{digest}"[:140]

    def _upsert_work_order_link(
        self,
        *,
        plan: LyProductionPlan,
        work_order: str,
        operator: str,
        sync_status: str,
        request_id: str,
    ) -> LyProductionWorkOrderLink:
        link = (
            self.session.query(LyProductionWorkOrderLink)
            .filter(LyProductionWorkOrderLink.plan_id == int(plan.id))
            .first()
        )
        if link is None:
            link = LyProductionWorkOrderLink(
                plan_id=int(plan.id),
                work_order=work_order,
                erpnext_docstatus=None,
                erpnext_status="LocalPending",
                sync_status=sync_status,
                last_synced_at=None,
                created_by=operator,
            )
            self.session.add(link)
        else:
            link.work_order = work_order
            link.sync_status = sync_status
            if not (link.created_by or "").strip():
                link.created_by = operator

        if sync_status == "succeeded":
            link.erpnext_docstatus = 1
            link.erpnext_status = "LocalSynced"
            link.last_synced_at = datetime.utcnow()
        else:
            link.erpnext_docstatus = None
            link.erpnext_status = "LocalPending"

        self._log_status(
            plan_id=int(plan.id),
            from_status=str(plan.status),
            to_status=str(plan.status),
            action="local_work_order_link_upsert",
            operator=operator,
            request_id=request_id,
        )
        return link

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

    def _load_tracking_reconcile_candidates(
        self,
        *,
        payload: ProductionTrackingReconcileGenerateRequest,
        company: str,
    ) -> list[LySampleOrder]:
        try:
            sql = self.session.query(LySampleOrder).filter(
                LySampleOrder.company == company,
                LySampleOrder.status.in_(["sealed", "converted"]),
            )
            if payload.keyword:
                keyword = f"%{payload.keyword.strip().lower()}%"
                sql = sql.filter(
                    or_(
                        func.lower(LySampleOrder.sample_no).like(keyword),
                        func.lower(LySampleOrder.style_no).like(keyword),
                        func.lower(LySampleOrder.style_name).like(keyword),
                        func.lower(LySampleOrder.customer).like(keyword),
                        func.lower(LySampleOrder.bulk_handoff_no).like(keyword),
                    )
                )
            if payload.customer:
                sql = sql.filter(LySampleOrder.customer.like(f"%{payload.customer.strip()}%"))
            rows = sql.order_by(LySampleOrder.updated_at.desc(), LySampleOrder.id.desc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        candidates: list[LySampleOrder] = []
        for row in rows:
            sealed_date = self._sample_sealed_date(row)
            if payload.from_date and (sealed_date is None or sealed_date < payload.from_date):
                continue
            if payload.to_date and (sealed_date is None or sealed_date > payload.to_date):
                continue
            candidates.append(row)
        return candidates

    def _build_tracking_reconcile_draft(
        self,
        *,
        sample: LySampleOrder,
        batch_no: str,
        operator: str,
    ) -> dict[str, Any]:
        order, order_item = self._resolve_tracking_sales_order(sample=sample)
        sealed_date = self._sample_sealed_date(sample)
        sales_order = str(order.sales_order_no) if order is not None else ""
        order_qty = self._dec(getattr(order_item, "qty", None))
        unit_price = self._dec(getattr(order_item, "rate", None))
        sample_qty = Decimal("1")
        sample_price = Decimal("0")
        diff_status = self._tracking_diff_status(sample=sample, order=order)
        remark = self._tracking_reconcile_remark(sample=sample, order=order)
        owner = (
            self._text(getattr(sample, "pattern_maker", None))
            or self._text(getattr(sample, "sample_maker", None))
            or self._text(getattr(sample, "created_by", None))
            or operator
        )
        source_hash = self._build_request_hash(
            {
                "sample_id": int(sample.id),
                "sample_no": str(sample.sample_no),
                "sample_version": int(getattr(sample, "version", 0) or 0),
                "sample_status": str(sample.status),
                "bulk_handoff_no": self._text(getattr(sample, "bulk_handoff_no", None)),
                "sales_order_id": int(order.id) if order is not None else None,
                "sales_order": sales_order,
                "sales_order_item_id": int(order_item.id) if order_item is not None else None,
                "order_qty": order_qty,
                "unit_price": unit_price,
                "diff_status": diff_status,
            }
        )
        return {
            "batch_no": batch_no,
            "sample_order_id": int(sample.id),
            "sample_no": str(sample.sample_no),
            "style_no": str(sample.style_no),
            "style_name": str(sample.style_name),
            "image_tone": self._text(sample.image_tone) or "gray",
            "customer": str(sample.customer),
            "sample_type": str(sample.sample_type),
            "sealed_date": sealed_date,
            "sales_order": sales_order,
            "sales_order_id": int(order.id) if order is not None else None,
            "sales_order_item_id": int(order_item.id) if order_item is not None else None,
            "sample_qty": sample_qty,
            "order_qty": order_qty,
            "sample_price": sample_price,
            "unit_price": unit_price,
            "diff_status": diff_status,
            "remark": remark,
            "owner": owner,
            "source_hash": source_hash,
        }

    def _resolve_tracking_sales_order(self, *, sample: LySampleOrder) -> tuple[LySalesOrder | None, LySalesOrderItem | None]:
        try:
            order = self._find_tracking_sales_order(sample=sample)
            if order is None:
                return None, None
            item = (
                self.session.query(LySalesOrderItem)
                .filter(
                    LySalesOrderItem.sales_order_id == int(order.id),
                    LySalesOrderItem.item_code == str(sample.style_no),
                )
                .order_by(LySalesOrderItem.id.asc())
                .first()
            )
            if item is None:
                item = (
                    self.session.query(LySalesOrderItem)
                    .filter(LySalesOrderItem.sales_order_id == int(order.id))
                    .order_by(LySalesOrderItem.id.asc())
                    .first()
                )
            return order, item
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _find_tracking_sales_order(self, *, sample: LySampleOrder) -> LySalesOrder | None:
        company = str(sample.company)
        bulk_handoff_no = self._text(sample.bulk_handoff_no)
        source_ref = f"SAMPLE-{sample.sample_no}"
        direct_filters = [LySalesOrder.source_order_ref == source_ref]
        if bulk_handoff_no:
            direct_filters.extend(
                [
                    LySalesOrder.sales_order_no == bulk_handoff_no,
                    LySalesOrder.source_order_ref == bulk_handoff_no,
                ]
            )
        order = (
            self.session.query(LySalesOrder)
            .filter(LySalesOrder.company == company)
            .filter(or_(*direct_filters))
            .order_by(LySalesOrder.id.desc())
            .first()
        )
        if order is not None:
            return order

        return (
            self.session.query(LySalesOrder)
            .join(LySalesOrderItem, LySalesOrderItem.sales_order_id == LySalesOrder.id)
            .filter(
                LySalesOrder.company == company,
                LySalesOrder.customer == str(sample.customer),
                LySalesOrder.status != "cancelled",
                LySalesOrderItem.item_code == str(sample.style_no),
            )
            .order_by(LySalesOrder.id.desc())
            .first()
        )

    @staticmethod
    def _sample_sealed_date(sample: LySampleOrder) -> date | None:
        for value in (sample.converted_at, sample.updated_at, sample.due_date, sample.created_at):
            if value is None:
                continue
            if hasattr(value, "date"):
                return value.date()
            if isinstance(value, date):
                return value
        return None

    @staticmethod
    def _tracking_diff_status(*, sample: LySampleOrder, order: LySalesOrder | None) -> str:
        if order is None:
            return "unmatched"
        order_date = getattr(order, "transaction_date", None)
        due_date = getattr(sample, "due_date", None)
        if order_date is not None and due_date is not None and order_date > due_date:
            return "late_order"
        return "matched"

    @staticmethod
    def _tracking_reconcile_remark(*, sample: LySampleOrder, order: LySalesOrder | None) -> str:
        limitation = "样板单暂无订货数量/样价字段，数量与价格仅展示真实订单值，不作为差异判断。"
        if order is None:
            return f"封样后未找到本地大货销售订单；{limitation}"
        handoff = str(sample.bulk_handoff_no or "").strip()
        if handoff:
            return f"已按样板转大货单号 {handoff} 匹配本地销售订单；{limitation}"
        return f"已按客户+款号匹配本地销售订单 {order.sales_order_no}；{limitation}"

    def _apply_tracking_reconcile_draft(
        self,
        *,
        row: LyProductionTrackingReconcile,
        draft: dict[str, Any],
        operator: str,
    ) -> None:
        row.batch_no = draft["batch_no"]
        row.sample_order_id = draft["sample_order_id"]
        row.sample_no = draft["sample_no"]
        row.style_no = draft["style_no"]
        row.style_name = draft["style_name"]
        row.image_tone = draft["image_tone"]
        row.customer = draft["customer"]
        row.sample_type = draft["sample_type"]
        row.sealed_date = draft["sealed_date"]
        row.sales_order = draft["sales_order"]
        row.sales_order_id = draft["sales_order_id"]
        row.sales_order_item_id = draft["sales_order_item_id"]
        row.sample_qty = draft["sample_qty"]
        row.order_qty = draft["order_qty"]
        row.sample_price = draft["sample_price"]
        row.unit_price = draft["unit_price"]
        row.diff_status = draft["diff_status"]
        row.remark = draft["remark"]
        row.owner = draft["owner"]
        row.source_hash = draft["source_hash"]
        row.updated_by = operator

    @staticmethod
    def _tracking_reconcile_item(row: LyProductionTrackingReconcile) -> ProductionTrackingReconcileListItem:
        return ProductionTrackingReconcileListItem(
            id=int(row.id),
            reconcile_no=str(row.reconcile_no),
            batch_no=str(row.batch_no),
            company=str(row.company),
            sample_order_id=int(row.sample_order_id),
            sample_no=str(row.sample_no),
            style_no=str(row.style_no),
            style_name=str(row.style_name),
            image_tone=str(row.image_tone or "gray"),
            customer=str(row.customer),
            sample_type=str(row.sample_type),
            sealed_date=row.sealed_date,
            sales_order=(str(row.sales_order) if row.sales_order else None),
            sales_order_id=(int(row.sales_order_id) if row.sales_order_id is not None else None),
            sales_order_item_id=(int(row.sales_order_item_id) if row.sales_order_item_id is not None else None),
            sample_qty=Decimal(str(row.sample_qty or 0)),
            order_qty=Decimal(str(row.order_qty or 0)),
            sample_price=Decimal(str(row.sample_price or 0)),
            unit_price=Decimal(str(row.unit_price or 0)),
            diff_status=str(row.diff_status),
            remark=str(row.remark or ""),
            owner=str(row.owner or ""),
            created_by=str(row.created_by),
            created_at=row.created_at,
            updated_by=(str(row.updated_by) if row.updated_by else None),
            updated_at=row.updated_at,
        )

    def _validate_tracking_exception_payload(
        self,
        *,
        plan: LyProductionPlan,
        payload: ProductionTrackingExceptionCreateRequest,
        plan_id: int,
        request_id: str | None,
    ) -> None:
        operation = self._text(payload.operation) or "tracking_exception"
        if operation != "tracking_exception":
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="operation 必须为 tracking_exception")
        if payload.plan_id is not None and int(payload.plan_id) != int(plan_id):
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="plan_id 与路径不一致")
        if payload.company and str(payload.company).strip() != str(plan.company):
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="company 与生产计划不一致")
        if payload.sales_order and str(payload.sales_order).strip() != str(plan.sales_order):
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="sales_order 与生产计划不一致")
        if payload.sales_order_item and str(payload.sales_order_item).strip() != str(plan.sales_order_item):
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="sales_order_item 与生产计划不一致")
        if payload.item_code and str(payload.item_code).strip() != str(plan.item_code):
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="item_code 与生产计划不一致")
        exception_type = (self._text(payload.exception_type) or "progress").lower()
        severity = (self._text(payload.severity) or "medium").lower()
        status = (self._text(payload.status) or "open").lower()
        if exception_type not in PRODUCTION_TRACKING_EXCEPTION_TYPES:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="异常类型无效")
        if severity not in PRODUCTION_TRACKING_EXCEPTION_SEVERITIES:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="异常严重度无效")
        if status not in PRODUCTION_TRACKING_EXCEPTION_STATUSES:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="异常状态无效")
        payload_request_id = self._text(payload.request_id)
        header_request_id = self._text(request_id)
        if payload_request_id and header_request_id and payload_request_id != header_request_id:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="request_id 与请求头不一致")
        if payload_request_id and not is_request_id_valid(payload_request_id):
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="request_id 格式无效")

    @staticmethod
    def _normalize_tracking_node_key(value: str) -> str:
        normalized = str(value or "").strip().lower()
        if not re.fullmatch(r"[a-z0-9_-]{1,64}", normalized):
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="node_key 格式无效")
        return normalized

    def _validate_tracking_node_payload(
        self,
        *,
        plan: LyProductionPlan,
        payload: ProductionTrackingNodeEventRequest,
        plan_id: int,
        request_id: str | None,
    ) -> None:
        operation = self._text(payload.operation) or "tracking_node"
        if operation != "tracking_node":
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="operation 必须为 tracking_node")
        self._normalize_tracking_node_key(payload.node_key)
        status = (self._text(payload.status) or "").lower()
        if status not in PRODUCTION_TRACKING_NODE_STATUSES:
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="节点状态无效")
        if int(payload.progress) < 0 or int(payload.progress) > 100:
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="节点进度必须在 0-100")
        if payload.plan_id is not None and int(payload.plan_id) != int(plan_id):
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="plan_id 与路径不一致")
        if payload.company and str(payload.company).strip() != str(plan.company):
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="company 与生产计划不一致")
        if payload.sales_order and str(payload.sales_order).strip() != str(plan.sales_order):
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="sales_order 与生产计划不一致")
        if payload.sales_order_item and str(payload.sales_order_item).strip() != str(plan.sales_order_item):
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="sales_order_item 与生产计划不一致")
        if payload.item_code and str(payload.item_code).strip() != str(plan.item_code):
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="item_code 与生产计划不一致")
        payload_request_id = self._text(payload.request_id)
        header_request_id = self._text(request_id)
        if payload_request_id and header_request_id and payload_request_id != header_request_id:
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="request_id 与请求头不一致")
        if payload_request_id and not is_request_id_valid(payload_request_id):
            raise BusinessException(code=PRODUCTION_TRACKING_NODE_INVALID, message="request_id 格式无效")

    @staticmethod
    def _tracking_exception_item(row: LyProductionTrackingException) -> ProductionTrackingExceptionItem:
        return ProductionTrackingExceptionItem(
            id=int(row.id),
            exception_no=str(row.exception_no),
            plan_id=int(row.plan_id),
            company=str(row.company),
            plan_no=str(row.plan_no),
            sales_order=str(row.sales_order),
            sales_order_item=str(row.sales_order_item),
            item_code=str(row.item_code),
            exception_type=str(row.exception_type),
            severity=str(row.severity),
            status=str(row.status),
            description=str(row.description),
            owner=str(row.owner or ""),
            created_by=str(row.created_by),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _production_tracking_exception_item_from_json(payload: dict[str, Any]) -> ProductionTrackingExceptionItem:
        if hasattr(ProductionTrackingExceptionItem, "model_validate"):
            return ProductionTrackingExceptionItem.model_validate(payload)
        return ProductionTrackingExceptionItem.parse_obj(payload)

    @staticmethod
    def _tracking_node_event_item(row: LyProductionTrackingNodeEvent) -> ProductionTrackingNodeEventData:
        return ProductionTrackingNodeEventData(
            id=int(row.id),
            event_no=str(row.event_no),
            plan_id=int(row.plan_id),
            company=str(row.company),
            plan_no=str(row.plan_no),
            sales_order=str(row.sales_order),
            sales_order_item=str(row.sales_order_item),
            item_code=str(row.item_code),
            node_key=str(row.node_key),
            node_name=str(row.node_name),
            owner=str(row.owner or ""),
            status=str(row.status),
            progress=int(row.progress or 0),
            remark=str(row.remark or ""),
            source_type=str(row.source_type or "production_tracking_node"),
            source_ref=(str(row.source_ref) if row.source_ref else None),
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    @staticmethod
    def _production_tracking_node_event_from_json(payload: dict[str, Any]) -> ProductionTrackingNodeEventData:
        if hasattr(ProductionTrackingNodeEventData, "model_validate"):
            return ProductionTrackingNodeEventData.model_validate(payload)
        return ProductionTrackingNodeEventData.parse_obj(payload)

    def _calculate_quote_material_cost(self, *, plan: LyProductionPlan, quote_qty: Decimal) -> Decimal:
        try:
            snapshots = (
                self.session.query(LyProductionPlanMaterial)
                .filter(LyProductionPlanMaterial.plan_id == int(plan.id))
                .order_by(LyProductionPlanMaterial.id.asc())
                .all()
            )
            bom_rows = (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == int(plan.bom_id))
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        bom_item_by_id = {int(row.id): row for row in bom_rows}
        return self._quote_material_cost_from_rows(
            plan=plan,
            quote_qty=quote_qty,
            snapshot_items=snapshots,
            bom_items=bom_rows,
            bom_item_by_id=bom_item_by_id,
        )

    def _quote_material_cost_from_rows(
        self,
        *,
        plan: LyProductionPlan,
        quote_qty: Decimal,
        snapshot_items: list[LyProductionPlanMaterial],
        bom_items: list[LyApparelBomItem],
        bom_item_by_id: dict[int, LyApparelBomItem],
    ) -> Decimal:
        material_cost = Decimal("0")
        planned_qty = Decimal(str(plan.planned_qty or 0))
        if snapshot_items:
            ratio = Decimal("1")
            if planned_qty > 0:
                ratio = (quote_qty / planned_qty).quantize(Decimal("0.000001"))
            for snapshot in snapshot_items:
                bom_item = bom_item_by_id.get(int(snapshot.bom_item_id)) if snapshot.bom_item_id is not None else None
                unit_price = self._extract_unit_price_from_remark(bom_item.remark if bom_item is not None else None)
                required_qty = (Decimal(str(snapshot.required_qty or 0)) * ratio).quantize(Decimal("0.000001"))
                material_cost += required_qty * unit_price
            return material_cost.quantize(Decimal("0.000001"))

        for bom_item in bom_items:
            qty_per_piece = Decimal(str(bom_item.qty_per_piece or 0))
            loss_rate = Decimal(str(bom_item.loss_rate or 0))
            unit_price = self._extract_unit_price_from_remark(bom_item.remark)
            required_qty = (quote_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
            material_cost += required_qty * unit_price
        return material_cost.quantize(Decimal("0.000001"))

    def _quote_item(self, row: LyProductionQuote, *, plan: LyProductionPlan | None = None) -> ProductionQuoteListItem:
        quote_qty = Decimal(str(row.quote_qty or 0))
        quote_amount = Decimal(str(row.quote_amount or 0))
        if quote_qty > 0:
            quote_unit_price = (quote_amount / quote_qty).quantize(Decimal("0.000001"))
        else:
            quote_unit_price = Decimal("0")
        return ProductionQuoteListItem(
            quote_id=int(row.id),
            plan_id=int(row.plan_id),
            quote_no=str(row.quote_no),
            plan_no=str(row.plan_no),
            company=str(row.company),
            sales_order=str(row.sales_order),
            sales_order_item=str(row.sales_order_item),
            customer=str(row.customer) if row.customer else None,
            item_code=str(row.item_code),
            quote_qty=quote_qty,
            material_cost=Decimal(str(row.material_cost or 0)),
            labor_cost=Decimal(str(row.labor_cost or 0)),
            management_fee=Decimal(str(row.management_fee or 0)),
            quote_unit_price=quote_unit_price,
            quote_amount=quote_amount,
            gross_margin=Decimal("0"),
            currency=str(row.currency or "CNY"),
            quoted_at=row.created_at,
            delivery_date=plan.planned_start_date if plan is not None else None,
            valid_until=row.valid_until,
            status=str(row.status),
            source="saved",
        )

    def _quote_item_from_operation(self, row: LyProductionQuoteOperation) -> ProductionQuoteListItem:
        payload = row.response_json or {}
        if hasattr(ProductionQuoteListItem, "model_validate"):
            return ProductionQuoteListItem.model_validate(payload)
        return ProductionQuoteListItem.parse_obj(payload)

    def _quote_convert_from_operation(self, row: LyProductionQuoteOperation) -> ProductionQuoteConvertData:
        payload = row.response_json or {}
        if hasattr(ProductionQuoteConvertData, "model_validate"):
            return ProductionQuoteConvertData.model_validate(payload)
        return ProductionQuoteConvertData.parse_obj(payload)

    def _get_plan_for_quote(self, *, plan_id: int, company: str | None) -> LyProductionPlan:
        try:
            sql = self.session.query(LyProductionPlan).filter(LyProductionPlan.id == int(plan_id))
            if company:
                sql = sql.filter(LyProductionPlan.company == company)
            row = sql.first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BusinessException(code=PRODUCTION_QUOTE_NOT_FOUND, message="生产计划不存在，不能创建报价")
        return row

    def _get_quote_for_convert(self, *, quote_id: int, company: str | None) -> tuple[LyProductionQuote, LyProductionPlan]:
        try:
            sql = self.session.query(LyProductionQuote, LyProductionPlan).join(
                LyProductionPlan,
                LyProductionPlan.id == LyProductionQuote.plan_id,
            )
            sql = sql.filter(LyProductionQuote.id == int(quote_id))
            if company:
                sql = sql.filter(LyProductionQuote.company == company)
            row = sql.first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BusinessException(code=PRODUCTION_QUOTE_NOT_FOUND, message="报价单不存在，不能转订单")
        return row

    def _get_quote_for_update(self, *, quote_id: int, company: str | None) -> tuple[LyProductionQuote, LyProductionPlan]:
        try:
            sql = self.session.query(LyProductionQuote, LyProductionPlan).join(
                LyProductionPlan,
                LyProductionPlan.id == LyProductionQuote.plan_id,
            )
            sql = sql.filter(LyProductionQuote.id == int(quote_id))
            if company:
                sql = sql.filter(LyProductionQuote.company == company)
            row = sql.first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BusinessException(code=PRODUCTION_QUOTE_NOT_FOUND, message="报价单不存在")
        return row

    def _get_quote_by_no(self, *, company: str, quote_no: str) -> LyProductionQuote | None:
        try:
            return (
                self.session.query(LyProductionQuote)
                .filter(
                    LyProductionQuote.company == company,
                    LyProductionQuote.quote_no == quote_no,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _get_quote_operation(self, *, company: str, operation: str, idempotency_key: str) -> LyProductionQuoteOperation | None:
        try:
            return (
                self.session.query(LyProductionQuoteOperation)
                .filter(
                    LyProductionQuoteOperation.company == company,
                    LyProductionQuoteOperation.operation == operation,
                    LyProductionQuoteOperation.idempotency_key == idempotency_key,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    @staticmethod
    def _ensure_quote_operation_same(row: LyProductionQuoteOperation, *, request_hash: str) -> None:
        if str(row.request_hash) != request_hash:
            raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

    def _insert_quote_operation(
        self,
        *,
        quote_id: int,
        company: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        response: ProductionQuoteListItem | ProductionQuoteConvertData,
        operator: str,
    ) -> None:
        self.session.add(
            LyProductionQuoteOperation(
                quote_id=quote_id,
                company=company,
                operation=operation,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=response.model_dump(mode="json"),
                created_by=operator,
            )
        )

    @staticmethod
    def _quote_sales_order_no(row: LyProductionQuote) -> str:
        raw = re.sub(r"[^0-9A-Za-z_\-]+", "-", str(row.quote_no)).strip("-")
        quote_part = raw or str(row.id)
        return f"SO-{quote_part}"[:140]

    def _quote_sales_draft_idempotency_key(
        self,
        *,
        company: str,
        quote_no: str,
        quote_id: int,
        quote_idempotency_key: str,
    ) -> str:
        digest = self._build_request_hash(
            {
                "operation": "production_quote_convert_sales_order_draft",
                "company": company,
                "quote_no": quote_no,
                "quote_id": quote_id,
                "idempotency_key": quote_idempotency_key,
            }
        )
        return f"quote-convert-{digest[:32]}"

    @staticmethod
    def _normalize_quote_status(value: str | None) -> str:
        status = (value or "draft").strip().lower()
        if status not in {"draft", "pricing", "quoted", "converted", "void"}:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="报价状态非法")
        return status

    @staticmethod
    def _decimal_nonnegative(value: Decimal, *, field_name: str) -> Decimal:
        amount = Decimal(str(value or 0))
        if amount < 0:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message=f"{field_name} 不能小于 0")
        return amount.quantize(Decimal("0.000001"))

    @staticmethod
    def _next_quote_no() -> str:
        return f"QT-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    def _copy_quote_no(self, *, company: str, source_quote_no: str) -> str:
        base = re.sub(r"\s+", "-", source_quote_no.strip()) or "QUOTE"
        base = base[:128]
        for index in range(1, 1000):
            suffix = "COPY" if index == 1 else f"COPY{index}"
            candidate = f"{base}-{suffix}"[:140]
            if self._get_quote_by_no(company=company, quote_no=candidate) is None:
                return candidate
        return self._next_quote_no()

    def _followup_template_item(self, row: LyProductionFollowupTemplate) -> ProductionFollowupTemplateListItem:
        return ProductionFollowupTemplateListItem(
            template_id=int(row.id),
            template_no=str(row.template_no),
            template_name=str(row.template_name),
            template_type=str(row.template_type),
            trigger_node=str(row.trigger_node),
            followup_role=str(row.followup_role),
            followup_frequency=str(row.followup_frequency),
            sla_hours=int(row.sla_hours or 0),
            item_code=str(row.item_code or ""),
            company=str(row.company),
            status=str(row.status),
            updated_at=row.updated_at or row.created_at or datetime.utcnow(),
            nodes=self._list_followup_template_nodes(template_id=int(row.id), company=str(row.company)),
        )

    def _followup_template_item_from_operation(self, row: LyProductionFollowupTemplateOperation) -> ProductionFollowupTemplateListItem:
        payload = row.response_json or {}
        if hasattr(ProductionFollowupTemplateListItem, "model_validate"):
            return ProductionFollowupTemplateListItem.model_validate(payload)
        return ProductionFollowupTemplateListItem.parse_obj(payload)

    def _followup_template_node_item_from_operation(self, row: LyProductionFollowupTemplateNodeOperation) -> ProductionFollowupTemplateNodeItem:
        payload = row.response_json or {}
        if hasattr(ProductionFollowupTemplateNodeItem, "model_validate"):
            return ProductionFollowupTemplateNodeItem.model_validate(payload)
        return ProductionFollowupTemplateNodeItem.parse_obj(payload)

    def _followup_template_node_delete_from_operation(self, row: LyProductionFollowupTemplateNodeOperation) -> ProductionFollowupTemplateNodeDeleteData:
        payload = row.response_json or {}
        if hasattr(ProductionFollowupTemplateNodeDeleteData, "model_validate"):
            return ProductionFollowupTemplateNodeDeleteData.model_validate(payload)
        return ProductionFollowupTemplateNodeDeleteData.parse_obj(payload)

    def _list_followup_template_nodes(self, *, template_id: int, company: str) -> list[ProductionFollowupTemplateNodeItem]:
        try:
            rows = (
                self.session.query(LyProductionFollowupTemplateNode)
                .filter(
                    LyProductionFollowupTemplateNode.template_id == template_id,
                    LyProductionFollowupTemplateNode.company == company,
                )
                .order_by(LyProductionFollowupTemplateNode.sequence_no.asc(), LyProductionFollowupTemplateNode.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return [self._followup_template_node_item(row) for row in rows]

    @staticmethod
    def _followup_template_node_item(row: LyProductionFollowupTemplateNode) -> ProductionFollowupTemplateNodeItem:
        return ProductionFollowupTemplateNodeItem(
            id=int(row.id),
            template_id=int(row.template_id),
            company=str(row.company),
            node_name=str(row.node_name),
            owner=str(row.owner or ""),
            lead_time_hours=int(row.lead_time_hours or 0),
            status=str(row.status),
            gate=str(row.gate or ""),
            output=str(row.output or ""),
            reminder=str(row.reminder or ""),
            sequence_no=int(row.sequence_no or 0),
            updated_at=row.updated_at or row.created_at or datetime.utcnow(),
        )

    @classmethod
    def _snapshot_followup_template_node(cls, row: LyProductionFollowupTemplateNode) -> dict[str, Any]:
        return cls._canonicalize(
            {
                "id": int(row.id),
                "template_id": int(row.template_id),
                "company": row.company,
                "node_name": row.node_name,
                "owner": row.owner,
                "lead_time_hours": int(row.lead_time_hours or 0),
                "status": row.status,
                "gate": row.gate,
                "output": row.output,
                "reminder": row.reminder,
                "sequence_no": int(row.sequence_no or 0),
            }
        )

    @classmethod
    def _snapshot_followup_template(cls, row: LyProductionFollowupTemplate) -> dict[str, Any]:
        return cls._canonicalize(
            {
                "id": int(row.id),
                "company": row.company,
                "template_no": row.template_no,
                "template_name": row.template_name,
                "template_type": row.template_type,
                "trigger_node": row.trigger_node,
                "followup_role": row.followup_role,
                "followup_frequency": row.followup_frequency,
                "sla_hours": int(row.sla_hours or 0),
                "item_code": row.item_code,
                "status": row.status,
            }
        )

    def _followup_template_next_values(self, *, payload: ProductionFollowupTemplateUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        text_fields = {
            "template_no": payload.template_no,
            "template_name": payload.template_name,
            "template_type": payload.template_type,
            "trigger_node": payload.trigger_node,
            "followup_role": payload.followup_role,
            "followup_frequency": payload.followup_frequency,
            "item_code": payload.item_code,
        }
        for key, value in text_fields.items():
            if value is None:
                continue
            if key in {"template_no", "template_name"}:
                values[key] = self._require_non_blank(
                    value,
                    code=PRODUCTION_TRACKING_EXCEPTION_INVALID,
                    message=f"{key} 不能为空",
                )
            else:
                values[key] = self._text(value) or ""
        if payload.sla_hours is not None:
            values["sla_hours"] = int(payload.sla_hours)
        if payload.status is not None:
            values["status"] = self._normalize_followup_template_status(payload.status)
        return values

    def _followup_template_node_next_values(self, *, payload: ProductionFollowupTemplateNodeUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        text_fields = {
            "node_name": payload.node_name,
            "owner": payload.owner,
            "gate": payload.gate,
            "output": payload.output,
            "reminder": payload.reminder,
        }
        for key, value in text_fields.items():
            if value is None:
                continue
            if key == "node_name":
                values[key] = self._require_non_blank(
                    value,
                    code=PRODUCTION_TRACKING_EXCEPTION_INVALID,
                    message="node_name 不能为空",
                )
            else:
                values[key] = self._text(value) or ""
        if payload.lead_time_hours is not None:
            values["lead_time_hours"] = int(payload.lead_time_hours)
        if payload.sequence_no is not None:
            values["sequence_no"] = int(payload.sequence_no)
        if payload.status is not None:
            values["status"] = self._normalize_followup_node_status(payload.status)
        return values

    def _get_followup_template_by_no(self, *, company: str, template_no: str) -> LyProductionFollowupTemplate | None:
        try:
            return (
                self.session.query(LyProductionFollowupTemplate)
                .filter(
                    LyProductionFollowupTemplate.company == company,
                    LyProductionFollowupTemplate.template_no == template_no,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _get_followup_template_for_mutation(self, *, template_id: int, company: str) -> LyProductionFollowupTemplate:
        try:
            row = (
                self.session.query(LyProductionFollowupTemplate)
                .filter(
                    LyProductionFollowupTemplate.id == template_id,
                    LyProductionFollowupTemplate.company == company,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BusinessException(code=PRODUCTION_FOLLOWUP_TEMPLATE_NOT_FOUND, message="生产跟进模板不存在或不是本地模板")
        return row

    def _get_followup_template_node_for_mutation(self, *, template_id: int, node_id: int, company: str) -> LyProductionFollowupTemplateNode:
        try:
            row = (
                self.session.query(LyProductionFollowupTemplateNode)
                .filter(
                    LyProductionFollowupTemplateNode.id == node_id,
                    LyProductionFollowupTemplateNode.template_id == template_id,
                    LyProductionFollowupTemplateNode.company == company,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BusinessException(code=PRODUCTION_FOLLOWUP_TEMPLATE_NOT_FOUND, message="生产跟进模板节点不存在")
        return row

    def _get_followup_template_item_for_copy(self, *, template_id: int, company: str) -> ProductionFollowupTemplateListItem:
        try:
            row = (
                self.session.query(LyProductionFollowupTemplate)
                .filter(
                    LyProductionFollowupTemplate.id == template_id,
                    LyProductionFollowupTemplate.company == company,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is not None:
            return self._followup_template_item(row)

        try:
            plan = (
                self.session.query(LyProductionPlan)
                .filter(
                    LyProductionPlan.id == template_id,
                    LyProductionPlan.company == company,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if plan is None:
            raise BusinessException(code=PRODUCTION_FOLLOWUP_TEMPLATE_NOT_FOUND, message="生产跟进模板不存在")
        return self._derived_followup_template_item(plan)

    def _derived_followup_template_item(self, plan: LyProductionPlan) -> ProductionFollowupTemplateListItem:
        template_config: dict[str, tuple[str, str, str, str, int]] = {
            "draft": ("基础跟进", "制单草稿", "业务跟单", "每周", 72),
            "planned": ("排期跟进", "已计划", "业务跟单", "每日", 24),
            "material_checked": ("物料跟进", "已物料检查", "物料专员", "每日", 24),
            "work_order_pending": ("工单跟进", "工单待同步", "生产跟单", "每班次", 8),
            "work_order_created": ("工单跟进", "已创建工单", "生产跟单", "每日", 12),
            "job_cards_synced": ("生产跟进", "工序卡已同步", "生产跟单", "每日", 24),
            "cancelled": ("异常跟进", "已取消", "业务跟单", "按需", 48),
            "failed": ("异常跟进", "失败", "业务跟单", "按需", 4),
        }
        status = str(plan.status or "")
        template_type, trigger_node, followup_role, followup_frequency, sla_hours = template_config.get(
            status,
            ("基础跟进", status or "-", "业务跟单", "每日", 24),
        )
        return ProductionFollowupTemplateListItem(
            template_id=int(plan.id),
            template_no=f"FT-{str(plan.plan_no)}",
            template_name=f"{str(plan.item_code)} 跟进模板",
            template_type=template_type,
            trigger_node=trigger_node,
            followup_role=followup_role,
            followup_frequency=followup_frequency,
            sla_hours=sla_hours,
            item_code=str(plan.item_code),
            company=str(plan.company),
            status="disabled" if status in {"cancelled", "failed"} else "enabled",
            updated_at=plan.updated_at or plan.created_at or datetime.utcnow(),
        )

    def _get_followup_template_operation(self, *, company: str, operation: str, idempotency_key: str) -> LyProductionFollowupTemplateOperation | None:
        try:
            return (
                self.session.query(LyProductionFollowupTemplateOperation)
                .filter(
                    LyProductionFollowupTemplateOperation.company == company,
                    LyProductionFollowupTemplateOperation.operation == operation,
                    LyProductionFollowupTemplateOperation.idempotency_key == idempotency_key,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _get_followup_template_node_operation(
        self,
        *,
        company: str,
        operation: str,
        idempotency_key: str,
    ) -> LyProductionFollowupTemplateNodeOperation | None:
        try:
            return (
                self.session.query(LyProductionFollowupTemplateNodeOperation)
                .filter(
                    LyProductionFollowupTemplateNodeOperation.company == company,
                    LyProductionFollowupTemplateNodeOperation.operation == operation,
                    LyProductionFollowupTemplateNodeOperation.idempotency_key == idempotency_key,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    @staticmethod
    def _ensure_followup_operation_same(row: LyProductionFollowupTemplateOperation, *, request_hash: str) -> None:
        if str(row.request_hash) != request_hash:
            raise BusinessException(code=PRODUCTION_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

    def _insert_followup_template_operation(
        self,
        *,
        template_id: int,
        company: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        response: ProductionFollowupTemplateListItem,
        operator: str,
    ) -> None:
        self.session.add(
            LyProductionFollowupTemplateOperation(
                template_id=template_id,
                company=company,
                operation=operation,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=response.model_dump(mode="json"),
                created_by=operator,
            )
        )

    def _insert_followup_template_node_operation(
        self,
        *,
        template_id: int,
        node_id: int | None,
        company: str,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        response: ProductionFollowupTemplateNodeItem | ProductionFollowupTemplateNodeDeleteData,
        operator: str,
    ) -> None:
        self.session.add(
            LyProductionFollowupTemplateNodeOperation(
                template_id=template_id,
                node_id=node_id,
                company=company,
                operation=operation,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                response_json=response.model_dump(mode="json"),
                created_by=operator,
            )
        )

    @staticmethod
    def _normalize_followup_template_status(value: str | None) -> str:
        status = (value or "enabled").strip().lower()
        if status not in {"enabled", "disabled"}:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="模板状态必须为 enabled 或 disabled")
        return status

    @staticmethod
    def _normalize_followup_node_status(value: str | None) -> str:
        status = (value or "required").strip().lower()
        if status not in {"required", "optional", "locked"}:
            raise BusinessException(code=PRODUCTION_TRACKING_EXCEPTION_INVALID, message="节点状态必须为 required、optional 或 locked")
        return status

    @staticmethod
    def _next_followup_template_no() -> str:
        return f"FTPL-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _copy_followup_template_no(source_template_no: str) -> str:
        suffix = datetime.utcnow().strftime("%m%d%H%M%S")
        return f"{source_template_no}-COPY-{suffix}"[:140]

    @staticmethod
    def _text(value: Any) -> str | None:
        text = str(value).strip() if value is not None else ""
        return text or None

    @staticmethod
    def _next_tracking_batch_no() -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"PTRB-{ts}"

    @staticmethod
    def _next_tracking_reconcile_no() -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"PTR-{ts}"

    @staticmethod
    def _next_tracking_exception_no() -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"PTEX-{ts}"

    @staticmethod
    def _next_tracking_node_event_no() -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"PTNE-{ts}"

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

    @staticmethod
    def _extract_supplier_from_remark(remark: str | None) -> str | None:
        text = (remark or "").strip()
        if not text:
            return None
        matcher = re.search(r"(?:供应商|supplier)\s*[:：=]\s*([^\s,;，；]+)", text, re.IGNORECASE)
        if matcher is None:
            return None
        value = matcher.group(1).strip()
        return value or None

    @staticmethod
    def _extract_unit_price_from_remark(remark: str | None) -> Decimal:
        text = (remark or "").strip()
        if not text:
            return Decimal("0")
        matcher = re.search(r"(?:单价|unit_price)\s*[:：=]\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if matcher is None:
            return Decimal("0")
        return Decimal(matcher.group(1))
