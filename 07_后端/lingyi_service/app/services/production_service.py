"""Business service for production planning module (TASK-004A)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import hashlib
import json
import os
import re
from typing import Any

from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import PRODUCTION_BOM_ITEM_MISMATCH
from app.core.error_codes import PRODUCTION_BOM_NOT_ACTIVE
from app.core.error_codes import PRODUCTION_BOM_NOT_FOUND
from app.core.error_codes import PRODUCTION_IDEMPOTENCY_CONFLICT
from app.core.error_codes import PRODUCTION_IDEMPOTENCY_KEY_REQUIRED
from app.core.error_codes import PRODUCTION_MATERIAL_CHECK_STATUS_INVALID
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
from app.core.exceptions import ERPNextServiceUnavailableError
from app.core.request_id import is_request_id_valid
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.production import LyProductionJobCardLink
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.production import LyProductionStatusLog
from app.models.production import LyProductionWorkOrderLink
from app.schemas.production import ProductionCreateWorkOrderData
from app.schemas.production import ProductionCreateWorkOrderRequest
from app.schemas.production import ProductionFollowupTemplateListData
from app.schemas.production import ProductionFollowupTemplateListItem
from app.schemas.production import ProductionFollowupTemplateQuery
from app.schemas.production import ProductionJobCardLinkItem
from app.schemas.production import ProductionMaterialCheckData
from app.schemas.production import ProductionMaterialCheckRequest
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
from app.schemas.production import ProductionQuoteListData
from app.schemas.production import ProductionQuoteListItem
from app.schemas.production import ProductionQuoteQuery
from app.schemas.production import ProductionSalesForecastListData
from app.schemas.production import ProductionSalesForecastListItem
from app.schemas.production import ProductionSalesForecastQuery
from app.schemas.production import ProductionSalespersonPerformanceListData
from app.schemas.production import ProductionSalespersonPerformanceListItem
from app.schemas.production import ProductionSalespersonPerformanceQuery
from app.schemas.production import ProductionSyncJobCardsData
from app.schemas.production import ProductionWorkOrderOutboxSummary
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.erpnext_production_adapter import ERPNextSalesOrder
from app.services.erpnext_production_adapter import ERPNextSalesOrderItem
from app.services.production_work_order_outbox_service import ProductionWorkOrderOutboxService

PRODUCTION_WRITE_ENTRY_FROZEN_REASON = (
    "TASK-015E 局部解冻后仍保留受控写门禁：create-work-order 仅允许本地 outbox 候选入口，"
    "sync-job-cards 继续冻结在普通前端之外（internal worker 路径不变）。"
)
PRODUCTION_MATERIAL_CHECK_ALLOWED_STATUSES = frozenset(
    {
        "planned",
        "material_checked",
        "work_order_pending",
        "work_order_created",
    }
)
PRODUCTION_SCENARIO_TAG_PATTERN = re.compile(r"^Z003-PROD-PLAN-\d{8}-\d{3}$")
PRODUCTION_SCENARIO_TAG_IN_REQUEST_ID_PATTERN = re.compile(r"(Z003-PROD-PLAN-\d{8}-\d{3})")
PRODUCTION_LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
PRODUCTION_LOCAL_DEFAULT_COMPANY = "LY-LOCAL-TEST"
PRODUCTION_GATE_ERROR_PREFIX = "LOCAL_GATE_FAIL_CLOSED:"


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
        request_id: str | None = None,
    ) -> ProductionPlanCreateData:
        self._validate_create_plan_gate(payload=payload, request_id=request_id)
        sales_order, target_item, company = self._load_sales_order_context(payload=payload, request_id=request_id)

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
                    plan_id=int(plan.id),
                    quote_no=quote_no,
                    plan_no=str(plan.plan_no),
                    company=str(plan.company),
                    sales_order=str(plan.sales_order),
                    sales_order_item=str(plan.sales_order_item),
                    customer=(str(plan.customer) if plan.customer else None),
                    item_code=str(plan.item_code),
                    quote_qty=quote_qty,
                    quote_unit_price=quote_unit_price,
                    quote_amount=quote_amount,
                    delivery_date=plan.planned_start_date,
                    quoted_at=quoted_at,
                    status=str(plan.status),
                )
            )

        total = len(rows)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        paged_items = rows[start:end]
        return ProductionQuoteListData(
            items=paged_items,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def list_followup_templates(
        self,
        *,
        query: ProductionFollowupTemplateQuery,
        readable_item_codes: set[str] | None = None,
        readable_companies: set[str] | None = None,
    ) -> ProductionFollowupTemplateListData:
        try:
            plan_sql = self.session.query(LyProductionPlan)
            if query.item_code:
                plan_sql = plan_sql.filter(LyProductionPlan.item_code == query.item_code)
            if query.from_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) >= query.from_date)
            if query.to_date:
                plan_sql = plan_sql.filter(func.date(LyProductionPlan.updated_at) <= query.to_date)
            if readable_item_codes is not None:
                if not readable_item_codes:
                    return ProductionFollowupTemplateListData(items=[], total=0, page=query.page, page_size=query.page_size)
                plan_sql = plan_sql.filter(LyProductionPlan.item_code.in_(sorted(readable_item_codes)))
            if readable_companies is not None:
                if not readable_companies:
                    return ProductionFollowupTemplateListData(items=[], total=0, page=query.page, page_size=query.page_size)
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

        total = len(items)
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        return ProductionFollowupTemplateListData(
            items=items[start:end],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

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
        qty_ratio_by_status: dict[str, tuple[Decimal, Decimal]] = {
            "draft": (Decimal("0"), Decimal("0")),
            "planned": (Decimal("0.15"), Decimal("0.05")),
            "material_checked": (Decimal("0.35"), Decimal("0.15")),
            "work_order_pending": (Decimal("0.55"), Decimal("0.25")),
            "work_order_created": (Decimal("0.75"), Decimal("0.45")),
            "job_cards_synced": (Decimal("0.90"), Decimal("0.70")),
            "cancelled": (Decimal("0"), Decimal("0")),
            "failed": (Decimal("0.10"), Decimal("0")),
        }

        items: list[ProductionOrderIOQuantityListItem] = []
        for plan in plans:
            status = str(plan.status or "")
            ordered_qty = Decimal(str(plan.planned_qty or 0))
            if ordered_qty < 0:
                ordered_qty = Decimal("0")
            inbound_ratio, outbound_ratio = qty_ratio_by_status.get(status, (Decimal("0.40"), Decimal("0.20")))
            inbound_qty = (ordered_qty * inbound_ratio).quantize(Decimal("0.000001"))
            outbound_qty = (ordered_qty * outbound_ratio).quantize(Decimal("0.000001"))
            if outbound_qty > inbound_qty:
                outbound_qty = inbound_qty
            pending_inbound_qty = (ordered_qty - inbound_qty).quantize(Decimal("0.000001"))
            if pending_inbound_qty < 0:
                pending_inbound_qty = Decimal("0")
            pending_outbound_qty = (ordered_qty - outbound_qty).quantize(Decimal("0.000001"))
            if pending_outbound_qty < 0:
                pending_outbound_qty = Decimal("0")

            if ordered_qty > 0:
                inbound_progress = ((inbound_qty / ordered_qty) * Decimal("100")).quantize(Decimal("0.01"))
                outbound_progress = ((outbound_qty / ordered_qty) * Decimal("100")).quantize(Decimal("0.01"))
            else:
                inbound_progress = Decimal("0")
                outbound_progress = Decimal("0")

            if status in {"cancelled", "failed"}:
                io_status = "blocked"
            elif outbound_progress >= Decimal("90"):
                io_status = "done"
            elif inbound_progress >= Decimal("40"):
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
            write_entry_frozen=True,
            write_entry_frozen_reason=PRODUCTION_WRITE_ENTRY_FROZEN_REASON,
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
        self._ensure_material_check_status_allowed(plan=plan)
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

    def ensure_material_check_status_allowed(self, *, plan_id: int) -> str:
        plan = self._must_get_plan(plan_id=plan_id)
        return self._ensure_material_check_status_allowed(plan=plan)

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
            request_id=validated_request_id,
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
                request_id=validated_request_id,
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

    @staticmethod
    def _ensure_material_check_status_allowed(*, plan: LyProductionPlan) -> str:
        status = str(plan.status or "").strip()
        if status not in PRODUCTION_MATERIAL_CHECK_ALLOWED_STATUSES:
            raise BusinessException(
                code=PRODUCTION_MATERIAL_CHECK_STATUS_INVALID,
                message="当前生产计划状态不允许执行物料检查",
            )
        return status

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
        request_id: str | None = None,
    ) -> tuple[Any, ERPNextSalesOrderItem, str]:
        sales_order_name = payload.sales_order.strip()
        sales_order = None
        try:
            sales_order = self.erp_adapter.get_sales_order(sales_order=sales_order_name)
        except ERPNextServiceUnavailableError:
            synthetic_context = self._build_local_synthetic_sales_order_context(payload=payload, request_id=request_id)
            if synthetic_context is not None:
                return synthetic_context
            raise

        if sales_order is None:
            synthetic_context = self._build_local_synthetic_sales_order_context(payload=payload, request_id=request_id)
            if synthetic_context is not None:
                return synthetic_context
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

    def _build_local_synthetic_sales_order_context(
        self,
        *,
        payload: ProductionPlanCreateRequest,
        request_id: str | None = None,
    ) -> tuple[ERPNextSalesOrder, ERPNextSalesOrderItem, str] | None:
        if not self._is_local_synthetic_context_enabled():
            return None

        scenario_tag = self._extract_local_synthetic_scenario_tag(payload=payload, request_id=request_id)
        if scenario_tag is None:
            return None

        item_code = payload.item_code.strip()
        sales_order_name = payload.sales_order.strip()
        sales_order_item_name = (payload.sales_order_item or "").strip()
        company = (payload.company or os.getenv("LINGYI_LOCAL_DEV_COMPANY", PRODUCTION_LOCAL_DEFAULT_COMPANY)).strip()
        if not company:
            raise BusinessException(code=PRODUCTION_SO_NOT_FOUND, message="local synthetic context 缺少 company")
        if not sales_order_item_name:
            raise BusinessException(code=PRODUCTION_SO_ITEM_NOT_FOUND, message="local synthetic context 缺少 sales_order_item")

        planned_qty = Decimal(str(payload.planned_qty))
        synthetic_item = ERPNextSalesOrderItem(
            name=sales_order_item_name,
            item_code=item_code,
            qty=planned_qty,
        )
        synthetic_order = ERPNextSalesOrder(
            name=sales_order_name,
            docstatus=1,
            status="To Deliver and Bill",
            company=company,
            customer=f"LOCAL_SYNTHETIC_{scenario_tag}",
            items=(synthetic_item,),
        )
        return synthetic_order, synthetic_item, company

    @staticmethod
    def _is_local_synthetic_context_enabled() -> bool:
        app_env = os.getenv("APP_ENV", "").strip().lower()
        db_url = os.getenv("LINGYI_DB_URL", "").strip()
        return app_env == "development" and db_url == PRODUCTION_LOCAL_ALLOWED_DB_URL

    @staticmethod
    def _extract_local_synthetic_scenario_tag(
        payload: ProductionPlanCreateRequest,
        request_id: str | None = None,
    ) -> str | None:
        scenario_tag = (payload.scenario_tag or "").strip()
        if not scenario_tag:
            return None
        if not PRODUCTION_SCENARIO_TAG_PATTERN.fullmatch(scenario_tag):
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
        request_match = PRODUCTION_SCENARIO_TAG_IN_REQUEST_ID_PATTERN.search(request_id_value)
        if request_match is None or request_match.group(1) != scenario_tag:
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
        self._ensure_local_dev_write_gate()
        scenario_tag = self._require_non_blank(
            payload.scenario_tag,
            code=PRODUCTION_IDEMPOTENCY_CONFLICT,
            message=f"{PRODUCTION_GATE_ERROR_PREFIX}missing_scenario_tag",
        )
        if not PRODUCTION_SCENARIO_TAG_PATTERN.fullmatch(scenario_tag):
            self._raise_gate_error("invalid_scenario_tag")

        if not payload.bom_id:
            self._raise_gate_error("mismatched_business_carrier")
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
        if not PRODUCTION_SCENARIO_TAG_PATTERN.fullmatch(normalized_scenario):
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

        match = PRODUCTION_SCENARIO_TAG_IN_REQUEST_ID_PATTERN.search(normalized_request_id)
        if match is None or match.group(1) != scenario_tag:
            self._raise_gate_error("mismatched_request_id")
        return normalized_request_id

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
