"""Service layer for FastAPI-native material purchase orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import false
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import MATERIAL_PURCHASE_CONFLICT
from app.core.error_codes import MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT
from app.core.error_codes import MATERIAL_PURCHASE_NOT_FOUND
from app.core.exceptions import BusinessException
from app.models.bom import LyApparelBomItem
from app.models.master_data import LyMasterDataRecord
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchasePayment
from app.models.material_purchase import LyMaterialPurchasePaymentOperation
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.schemas.material_purchase import MaterialPurchaseInvoiceCreateRequest
from app.schemas.material_purchase import MaterialPurchaseInvoiceData
from app.schemas.material_purchase import MaterialPurchaseInvoiceListData
from app.schemas.material_purchase import MaterialPurchaseOrderCancelData
from app.schemas.material_purchase import MaterialPurchaseOrderCancelRequest
from app.schemas.material_purchase import MaterialPurchaseOrderCreateData
from app.schemas.material_purchase import MaterialPurchaseOrderCreateRequest
from app.schemas.material_purchase import MaterialPurchaseOrderData
from app.schemas.material_purchase import MaterialPurchaseOrderListItem
from app.schemas.material_purchase import MaterialPurchasePaymentCancelRequest
from app.schemas.material_purchase import MaterialPurchasePaymentCreateRequest
from app.schemas.material_purchase import MaterialPurchasePaymentData
from app.schemas.material_purchase import MaterialPurchasePaymentListData
from app.schemas.material_purchase import MaterialPurchaseRequirementListData
from app.schemas.material_purchase import MaterialPurchaseRequirementListItem
from app.schemas.material_purchase import MaterialPurchaseRequirementToOrderData
from app.schemas.material_purchase import MaterialPurchaseRequirementToOrderRequest


@dataclass(frozen=True)
class PurchaseMutationResult:
    """Mutation result with audit snapshots."""

    item: MaterialPurchaseOrderCreateData
    before: dict[str, Any] | None
    after: dict[str, Any]
    resource_id: int
    resource_no: str
    idempotent: bool = False


@dataclass(frozen=True)
class PurchaseInvoiceMutationResult:
    """Purchase invoice mutation result with audit snapshots."""

    item: MaterialPurchaseInvoiceData
    before: dict[str, Any] | None
    after: dict[str, Any]
    resource_id: int
    resource_no: str
    idempotent: bool = False


@dataclass(frozen=True)
class PurchasePaymentMutationResult:
    """Purchase payment mutation result with audit snapshots."""

    item: MaterialPurchasePaymentData
    before: dict[str, Any] | None
    after: dict[str, Any]
    resource_id: int
    resource_no: str
    idempotent: bool = False


@dataclass(frozen=True)
class PurchaseRequirementOrderMutationResult:
    """Purchase order created from material requirement pool rows."""

    item: MaterialPurchaseRequirementToOrderData
    before: dict[str, Any] | None
    after: dict[str, Any]
    resource_id: int
    resource_no: str
    idempotent: bool = False


@dataclass(frozen=True)
class PurchaseOrderCancelMutationResult:
    """Purchase order cancel result with released requirement pool rows."""

    item: MaterialPurchaseOrderCancelData
    before: dict[str, Any] | None
    after: dict[str, Any]
    resource_id: int
    resource_no: str
    idempotent: bool = False


class MaterialPurchaseService:
    """Read and mutate material purchase orders."""

    PURCHASE_SOURCE_TYPE = "material_purchase_order"

    def __init__(self, session: Session):
        self.session = session

    def list_orders(
        self,
        *,
        company: str | None,
        keyword: str | None,
        supplier_name: str | None,
        status: str | None,
        page: int,
        page_size: int,
        allowed_companies: set[str] | None = None,
        allowed_materials: set[str] | None = None,
        allowed_suppliers: set[str] | None = None,
        allowed_warehouses: set[str] | None = None,
    ) -> MaterialPurchaseOrderData:
        try:
            query = (
                self.session.query(LyMaterialPurchaseOrder, LyMaterialPurchaseOrderItem)
                .join(LyMaterialPurchaseOrderItem, LyMaterialPurchaseOrderItem.order_id == LyMaterialPurchaseOrder.id)
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseOrder.company,
                allowed_values=allowed_companies,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseOrderItem.material_item_code,
                allowed_values=allowed_materials,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseOrder.supplier_name,
                allowed_values=allowed_suppliers,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseOrderItem.warehouse,
                allowed_values=allowed_warehouses,
            )
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyMaterialPurchaseOrder.company == normalized_company)
            normalized_supplier = self._optional_text(supplier_name)
            if normalized_supplier:
                query = query.filter(func.lower(LyMaterialPurchaseOrder.supplier_name).like(f"%{normalized_supplier.lower()}%"))
            normalized_status = self._optional_text(status)
            if normalized_status and normalized_status != "all":
                query = query.filter(LyMaterialPurchaseOrder.status == normalized_status)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyMaterialPurchaseOrder.purchase_no).like(like_value))
                    | (func.lower(LyMaterialPurchaseOrder.supplier_name).like(like_value))
                    | (func.lower(LyMaterialPurchaseOrderItem.material_item_code).like(like_value))
                    | (func.lower(LyMaterialPurchaseOrderItem.material_name).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(LyMaterialPurchaseOrder.created_at.desc(), LyMaterialPurchaseOrder.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return MaterialPurchaseOrderData(
            items=[self._list_item(order, line) for order, line in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_order(self, *, payload: MaterialPurchaseOrderCreateRequest, actor: str) -> PurchaseMutationResult:
        company = self._require_text(payload.company, "company")
        purchase_no = self._optional_text(payload.purchase_no) or self._next_purchase_no()
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        request_hash = self._request_hash(payload=payload.model_dump(mode="json"), purchase_no=purchase_no)

        idem = self._get_idempotency(company=company, idempotency_key=idempotency_key)
        if idem is not None:
            if str(idem.operation) != "create" or str(idem.request_hash) != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT, message="采购单幂等键重复但载荷不一致")
            row = self._get_order_by_id(int(idem.record_id))
            data = self._create_data(row=row, idempotency_key=idempotency_key)
            snapshot = data.model_dump(mode="json")
            return PurchaseMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(row.id),
                resource_no=str(row.purchase_no),
                idempotent=True,
            )

        if self._get_order_by_no(company=company, purchase_no=purchase_no) is not None:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"{purchase_no} 已存在")

        supplier_name = self._require_text(payload.supplier_name, "supplier_name")
        material_codes = [self._require_text(line.material_item_code, "material_item_code") for line in payload.items]
        uoms = [self._optional_text(line.uom) or "米" for line in payload.items]
        warehouses = [warehouse for line in payload.items if (warehouse := self._optional_text(line.warehouse))]
        self._ensure_active_master_records(
            company=company,
            entity_type="supplier",
            values=[supplier_name],
            label="供应商",
            match_name=True,
        )
        self._ensure_active_master_records(
            company=company,
            entity_type="material",
            values=material_codes,
            label="物料",
            match_name=False,
        )
        self._ensure_active_material_units(company=company, values=uoms)
        if warehouses:
            self._ensure_active_master_records(
                company=company,
                entity_type="warehouse",
                values=warehouses,
                label="仓库",
                match_name=True,
            )

        total_qty = Decimal("0")
        total_amount = Decimal("0")
        try:
            row = LyMaterialPurchaseOrder(
                company=company,
                purchase_no=purchase_no,
                supplier_name=supplier_name,
                transaction_date=payload.transaction_date,
                expected_delivery_date=payload.expected_delivery_date,
                status="draft",
                total_qty=Decimal("0"),
                received_qty=Decimal("0"),
                total_amount=Decimal("0"),
                currency=self._optional_text(payload.currency) or "CNY",
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
            for line in payload.items:
                qty = Decimal(str(line.qty))
                unit_price = Decimal(str(line.unit_price or 0))
                amount = qty * unit_price
                total_qty += qty
                total_amount += amount
                material_item_code = self._require_text(line.material_item_code, "material_item_code")
                self.session.add(
                    LyMaterialPurchaseOrderItem(
                        order_id=int(row.id),
                        company=company,
                        item_code=self._optional_text(line.item_code) or material_item_code,
                        material_item_code=material_item_code,
                        material_name=self._optional_text(line.material_name) or material_item_code,
                        qty=qty,
                        received_qty=Decimal("0"),
                        uom=self._optional_text(line.uom) or "米",
                        unit_price=unit_price,
                        amount=amount,
                        warehouse=self._optional_text(line.warehouse),
                    )
                )
            row.total_qty = total_qty
            row.total_amount = total_amount
            self.session.flush()
            data = self._create_data(row=row, idempotency_key=idempotency_key)
            self.session.add(
                LyMaterialPurchaseIdempotency(
                    company=company,
                    idempotency_key=idempotency_key,
                    operation="create",
                    request_hash=request_hash,
                    record_id=int(row.id),
                    response_data=data.model_dump(mode="json"),
                    created_by=actor,
                )
            )
            self.session.flush()
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        return PurchaseMutationResult(
            item=data,
            before=None,
            after=data.model_dump(mode="json"),
            resource_id=int(row.id),
            resource_no=str(row.purchase_no),
        )

    def list_requirements(
        self,
        *,
        company: str | None,
        keyword: str | None,
        material_item_code: str | None,
        supplier_name: str | None,
        status: str | None,
        page: int,
        page_size: int,
        group_by_material: bool = False,
        allowed_companies: set[str] | None = None,
        allowed_materials: set[str] | None = None,
        allowed_suppliers: set[str] | None = None,
        allowed_warehouses: set[str] | None = None,
    ) -> MaterialPurchaseRequirementListData:
        try:
            query = self.session.query(LyMaterialPurchaseRequirement)
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseRequirement.company,
                allowed_values=allowed_companies,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseRequirement.material_item_code,
                allowed_values=allowed_materials,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseRequirement.warehouse,
                allowed_values=allowed_warehouses,
            )
            query = self._apply_optional_scope_filter(
                query=query,
                column=LyMaterialPurchaseRequirement.supplier_name,
                allowed_values=allowed_suppliers,
            )
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyMaterialPurchaseRequirement.company == normalized_company)
            normalized_material = self._optional_text(material_item_code)
            if normalized_material:
                query = query.filter(LyMaterialPurchaseRequirement.material_item_code == normalized_material)
            normalized_supplier = self._optional_text(supplier_name)
            if normalized_supplier:
                query = query.filter(func.lower(LyMaterialPurchaseRequirement.supplier_name).like(f"%{normalized_supplier.lower()}%"))
            normalized_status = self._optional_text(status)
            if normalized_status and normalized_status != "all":
                query = query.filter(LyMaterialPurchaseRequirement.status == normalized_status)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyMaterialPurchaseRequirement.requirement_no).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.source_no).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.sales_order).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.sales_order_item).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.material_item_code).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.material_name).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.supplier_name).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.purchase_no).like(like_value))
                )
            ordered_query = query.order_by(
                LyMaterialPurchaseRequirement.status.asc(),
                LyMaterialPurchaseRequirement.created_at.desc(),
                LyMaterialPurchaseRequirement.id.desc(),
            )
            if group_by_material:
                rows = ordered_query.all()
                items = self._group_requirement_items_for_list(rows)
                total = len(items)
                start = max(page - 1, 0) * page_size
                items = items[start : start + page_size]
            else:
                total = int(query.count())
                rows = ordered_query.offset(max(page - 1, 0) * page_size).limit(page_size).all()
                items = [self._requirement_item(row) for row in rows]
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return MaterialPurchaseRequirementListData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_requirements_for_permission(
        self,
        *,
        company: str,
        requirement_ids: list[int],
    ) -> list[LyMaterialPurchaseRequirement]:
        """Fetch requirement rows for read-only resource-scope checks before mutation."""
        normalized_company = self._require_text(company, "company")
        normalized_ids = sorted({int(row_id) for row_id in requirement_ids})
        if not normalized_ids:
            return []
        try:
            return self._requirements_by_ids(company=normalized_company, requirement_ids=normalized_ids)
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc

    def sync_requirements_from_production_plan(self, *, plan: Any, actor: str) -> list[MaterialPurchaseRequirementListItem]:
        """Upsert material requirement pool rows from a production material check."""
        try:
            plan_id = int(plan.id)
            locked_plan = (
                self.session.query(LyProductionPlan)
                .filter(LyProductionPlan.id == plan_id)
                .with_for_update()
                .one_or_none()
            )
            if locked_plan is not None:
                plan = locked_plan
            snapshots = (
                self.session.query(LyProductionPlanMaterial)
                .filter(LyProductionPlanMaterial.plan_id == plan_id)
                .order_by(LyProductionPlanMaterial.id.asc())
                .all()
            )
            bom_item_ids = [int(row.bom_item_id) for row in snapshots if row.bom_item_id is not None]
            bom_items = {}
            if bom_item_ids:
                bom_items = {
                    int(row.id): row
                    for row in self.session.query(LyApparelBomItem)
                    .filter(LyApparelBomItem.id.in_(bom_item_ids))
                    .all()
                }
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc

        material_names = self._material_name_lookup(
            company=str(plan.company),
            material_codes=[str(row.material_item_code) for row in snapshots if row.material_item_code],
        )

        synced: list[LyMaterialPurchaseRequirement] = []
        pending_by_key: dict[
            tuple[str, str, str, int | None, str | None, str | None, str | None, str, str],
            LyMaterialPurchaseRequirement,
        ] = {}
        synced_keys: set[tuple[str, str, str, int | None, str | None, str | None, str | None, str, str]] = set()
        now = datetime.now(UTC)

        def _requirement_key(
            row: LyMaterialPurchaseRequirement,
        ) -> tuple[str, str, str, int | None, str | None, str | None, str | None, str, str]:
            return (
                str(row.company),
                str(row.source_type),
                str(row.source_id),
                int(row.bom_item_id) if row.bom_item_id is not None else None,
                self._optional_text(row.bom_color),
                self._optional_text(row.bom_size),
                self._optional_text(row.bom_part),
                str(row.material_item_code),
                str(row.warehouse),
            )

        try:
            for snapshot in snapshots:
                material_code = self._require_text(snapshot.material_item_code, "material_item_code")
                warehouse = self._require_text(snapshot.warehouse, "warehouse")
                required_qty = Decimal(str(snapshot.required_qty or 0))
                available_qty = Decimal(str(snapshot.available_qty or 0))
                net_required_qty = max(Decimal("0"), required_qty - available_qty)
                bom_item = bom_items.get(int(snapshot.bom_item_id)) if snapshot.bom_item_id is not None else None
                bom_color = self._optional_text(getattr(snapshot, "bom_color", None))
                bom_size = self._optional_text(getattr(snapshot, "bom_size", None))
                bom_part = self._optional_text(getattr(snapshot, "bom_part", None))
                bom_item_id = int(snapshot.bom_item_id) if snapshot.bom_item_id is not None else None
                requirement_key = (
                    str(plan.company),
                    "production_plan",
                    str(plan.id),
                    bom_item_id,
                    bom_color,
                    bom_size,
                    bom_part,
                    material_code,
                    warehouse,
                )
                existing = pending_by_key.get(requirement_key)
                if existing is None:
                    existing = self._get_requirement_by_source(
                        company=str(plan.company),
                        source_type="production_plan",
                        source_id=str(plan.id),
                        bom_item_id=bom_item_id,
                        bom_color=bom_color,
                        bom_size=bom_size,
                        bom_part=bom_part,
                        material_item_code=material_code,
                        warehouse=warehouse,
                    )
                row = existing
                if row is None:
                    row = LyMaterialPurchaseRequirement(
                        company=str(plan.company),
                        requirement_no=self._next_requirement_no(plan_id=int(plan.id), material_item_code=material_code),
                        source_type="production_plan",
                        source_id=str(plan.id),
                        source_no=str(plan.plan_no),
                        plan_id=int(plan.id),
                        bom_item_id=bom_item_id,
                        bom_color=bom_color,
                        bom_size=bom_size,
                        bom_part=bom_part,
                        material_item_code=material_code,
                        warehouse=warehouse,
                        status="pending",
                        created_by=actor,
                    )
                    self.session.add(row)
                pending_by_key[requirement_key] = row
                row.source_no = str(plan.plan_no)
                row.bom_color = bom_color
                row.bom_size = bom_size
                row.bom_part = bom_part
                row.sales_order = self._optional_text(plan.sales_order)
                row.sales_order_item = self._optional_text(plan.sales_order_item)
                row.item_code = self._optional_text(plan.item_code)
                row.material_name = material_names.get(material_code, material_code)
                row.supplier_name = self._extract_supplier_from_remark(bom_item.remark if bom_item is not None else None)
                row.required_qty = required_qty
                row.available_qty = available_qty
                row.net_required_qty = net_required_qty
                row.uom = self._optional_text(getattr(snapshot, "uom", None)) or str(
                    getattr(bom_item, "uom", None) or "米"
                )
                row.unit_price = self._extract_unit_price_from_remark(bom_item.remark if bom_item is not None else None)
                row.payload = {
                    "uom": row.uom,
                    "bom_color": row.bom_color,
                    "bom_size": row.bom_size,
                    "bom_part": row.bom_part,
                    "qty_per_piece": str(snapshot.qty_per_piece or 0),
                    "loss_rate": str(snapshot.loss_rate or 0),
                    "checked_at": snapshot.checked_at.isoformat() if snapshot.checked_at else None,
                }
                row.updated_by = actor
                row.updated_at = now
                current_status = str(row.status or "pending")
                has_completed_purchase = (
                    current_status == "completed"
                    and row.purchase_no is not None
                    and Decimal(str(row.purchased_qty or 0)) > Decimal("0")
                    and Decimal(str(row.received_qty or 0)) >= Decimal(str(row.purchased_qty or 0))
                )
                should_append = requirement_key not in synced_keys
                if should_append:
                    synced_keys.add(requirement_key)
                if current_status in {"pending", "completed", "cancelled"}:
                    if has_completed_purchase and net_required_qty == Decimal("0"):
                        row.status = "completed"
                        if should_append:
                            synced.append(row)
                        continue
                    row.purchased_qty = Decimal("0")
                    row.received_qty = Decimal("0")
                    row.purchase_order_id = None
                    row.purchase_order_item_id = None
                    row.purchase_no = None
                    row.status = "completed" if net_required_qty == Decimal("0") else "pending"
                elif current_status == "purchased":
                    purchased_qty = Decimal(str(row.purchased_qty or 0))
                    received_qty = Decimal(str(row.received_qty or 0))
                    row.status = "completed" if purchased_qty > Decimal("0") and received_qty >= purchased_qty else "purchased"
                if should_append:
                    synced.append(row)
            stale_candidates = (
                self.session.query(LyMaterialPurchaseRequirement)
                .filter(
                    LyMaterialPurchaseRequirement.company == str(plan.company),
                    LyMaterialPurchaseRequirement.source_type == "production_plan",
                    LyMaterialPurchaseRequirement.source_id == str(plan.id),
                    LyMaterialPurchaseRequirement.status == "pending",
                )
                .with_for_update()
                .all()
            )
            for stale in stale_candidates:
                if _requirement_key(stale) in synced_keys:
                    continue
                if (
                    stale.purchase_order_id is not None
                    or stale.purchase_order_item_id is not None
                    or stale.purchase_no is not None
                    or Decimal(str(stale.purchased_qty or 0)) > Decimal("0")
                    or Decimal(str(stale.received_qty or 0)) > Decimal("0")
                ):
                    continue
                payload = dict(stale.payload or {})
                payload.update(
                    {
                        "cancel_reason": "stale_material_check",
                        "cancelled_by_material_check_at": now.isoformat(),
                    }
                )
                stale.payload = payload
                stale.status = "cancelled"
                stale.updated_by = actor
                stale.updated_at = now
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc
        return [self._requirement_item(row) for row in synced]

    def create_order_from_requirements(
        self,
        *,
        payload: MaterialPurchaseRequirementToOrderRequest,
        actor: str,
    ) -> PurchaseRequirementOrderMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        requirement_ids = sorted({int(row_id) for row_id in payload.requirement_ids})
        if not requirement_ids:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="requirement_ids 不能为空")
        requested_purchase_no = self._optional_text(payload.purchase_no)
        requested_supplier = self._optional_text(payload.supplier_name)
        request_hash = self._mutation_hash(
            {
                "operation": "create_order_from_requirements",
                "company": company,
                "requirement_ids": requirement_ids,
                "supplier_name": requested_supplier,
                "purchase_no": requested_purchase_no,
                "transaction_date": payload.transaction_date.isoformat() if payload.transaction_date else None,
                "expected_delivery_date": payload.expected_delivery_date.isoformat() if payload.expected_delivery_date else None,
                "currency": self._optional_text(payload.currency) or "CNY",
                "group_by_material": bool(payload.group_by_material),
            }
        )

        existing_idem = self._get_idempotency(company=company, idempotency_key=idempotency_key)
        if existing_idem is not None:
            if str(existing_idem.operation) != "create_from_requirements" or str(existing_idem.request_hash) != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT, message="采购需求生成采购单幂等键重复但载荷不一致")
            order = self._get_order_by_id(int(existing_idem.record_id))
            data = self._requirement_order_data(order=order, requirements=self._requirements_by_ids(company=company, requirement_ids=requirement_ids))
            snapshot = data.model_dump(mode="json")
            return PurchaseRequirementOrderMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(order.id),
                resource_no=str(order.purchase_no),
                idempotent=True,
            )

        requirements = self._requirements_by_ids(company=company, requirement_ids=requirement_ids, for_update=True)
        if len(requirements) != len(requirement_ids):
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="待采购需求不存在")
        for row in requirements:
            if str(row.status) != "pending":
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"需求 {row.requirement_no} 不是待采购状态")
            if Decimal(str(row.net_required_qty or 0)) <= Decimal("0"):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"需求 {row.requirement_no} 无净需求")

        purchase_no = requested_purchase_no or self._next_purchase_no()
        if self._get_order_by_no(company=company, purchase_no=purchase_no) is not None:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"{purchase_no} 已存在")

        supplier_name = self._resolve_requirement_supplier(
            requirements=requirements,
            requested_supplier=requested_supplier,
        )
        self._ensure_active_master_records(
            company=company,
            entity_type="supplier",
            values=[supplier_name],
            label="供应商",
            match_name=True,
        )
        self._ensure_active_master_records(
            company=company,
            entity_type="material",
            values=[str(requirement.material_item_code) for requirement in requirements],
            label="物料",
            match_name=False,
        )
        self._ensure_active_material_units(
            company=company,
            values=[self._optional_text(requirement.uom) or "米" for requirement in requirements],
        )
        warehouses = [warehouse for requirement in requirements if (warehouse := self._optional_text(requirement.warehouse))]
        if warehouses:
            self._ensure_active_master_records(
                company=company,
                entity_type="warehouse",
                values=warehouses,
                label="仓库",
                match_name=True,
            )
        grouped = self._group_requirements_for_order(requirements=requirements, group_by_material=payload.group_by_material)
        total_qty = Decimal("0")
        total_amount = Decimal("0")
        try:
            order = LyMaterialPurchaseOrder(
                company=company,
                purchase_no=purchase_no,
                supplier_name=supplier_name,
                transaction_date=payload.transaction_date,
                expected_delivery_date=payload.expected_delivery_date,
                status="draft",
                total_qty=Decimal("0"),
                received_qty=Decimal("0"),
                total_amount=Decimal("0"),
                currency=self._optional_text(payload.currency) or "CNY",
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(order)
            self.session.flush()

            line_requirements: list[tuple[LyMaterialPurchaseOrderItem, list[LyMaterialPurchaseRequirement]]] = []
            for bucket in grouped:
                qty = Decimal(str(bucket["qty"]))
                unit_price = Decimal(str(bucket["unit_price"]))
                amount = qty * unit_price
                total_qty += qty
                total_amount += amount
                line = LyMaterialPurchaseOrderItem(
                    order_id=int(order.id),
                    company=company,
                    item_code=str(bucket["material_item_code"]),
                    material_item_code=str(bucket["material_item_code"]),
                    material_name=str(bucket["material_name"]),
                    qty=qty,
                    received_qty=Decimal("0"),
                    uom=str(bucket["uom"]),
                    unit_price=unit_price,
                    amount=amount,
                    warehouse=self._optional_text(bucket["warehouse"]),
                )
                self.session.add(line)
                self.session.flush()
                line_requirements.append((line, bucket["requirements"]))

            order.total_qty = total_qty
            order.total_amount = total_amount
            for line, bucket_requirements in line_requirements:
                for requirement in bucket_requirements:
                    requirement.status = "purchased"
                    requirement.purchased_qty = Decimal(str(requirement.net_required_qty or 0))
                    requirement.received_qty = Decimal("0")
                    requirement.purchase_order_id = int(order.id)
                    requirement.purchase_order_item_id = int(line.id)
                    requirement.purchase_no = purchase_no
                    requirement.updated_by = actor
                    requirement.updated_at = datetime.now(UTC)

            data = self._requirement_order_data(order=order, requirements=requirements)
            self.session.add(
                LyMaterialPurchaseIdempotency(
                    company=company,
                    idempotency_key=idempotency_key,
                    operation="create_from_requirements",
                    request_hash=request_hash,
                    record_id=int(order.id),
                    response_data=data.model_dump(mode="json"),
                    created_by=actor,
                )
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        return PurchaseRequirementOrderMutationResult(
            item=data,
            before=None,
            after=data.model_dump(mode="json"),
            resource_id=int(order.id),
            resource_no=str(order.purchase_no),
        )

    def cancel_order(
        self,
        *,
        order_id: int,
        payload: MaterialPurchaseOrderCancelRequest,
        actor: str,
    ) -> PurchaseOrderCancelMutationResult:
        company = self._require_text(payload.company, "company")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        reason = self._require_text(payload.reason, "reason")
        request_hash = self._mutation_hash(
            {
                "operation": "cancel_order",
                "company": company,
                "order_id": int(order_id),
                "reason": reason,
            }
        )

        existing_idem = self._get_idempotency(company=company, idempotency_key=idempotency_key)
        if existing_idem is not None:
            if str(existing_idem.operation) != "cancel_order" or str(existing_idem.request_hash) != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT, message="取消采购单幂等键重复但载荷不一致")
            data = MaterialPurchaseOrderCancelData.model_validate(existing_idem.response_data)
            snapshot = data.model_dump(mode="json")
            return PurchaseOrderCancelMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(data.purchase_order.id),
                resource_no=data.purchase_order.purchase_no,
                idempotent=True,
            )

        order = self._get_order_by_id_for_company(company=company, order_id=int(order_id), for_update=True)
        lines = self._get_lines(order_id=int(order.id))
        requirements = self._requirements_by_order(company=company, order_id=int(order.id), for_update=True)
        before = self._cancel_snapshot(order=order, requirements=requirements)
        if str(order.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购单已取消")
        if Decimal(str(order.received_qty or 0)) > Decimal("0") or any(
            Decimal(str(line.received_qty or 0)) > Decimal("0") for line in lines
        ):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购单已有收货，不能取消")
        if self._has_active_purchase_invoice(company=company, order=order):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购单已有发票或应付，不能取消")
        for requirement in requirements:
            if Decimal(str(requirement.received_qty or 0)) > Decimal("0") or str(requirement.status) == "completed":
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"需求 {requirement.requirement_no} 已齐料，不能取消采购单")
            if str(requirement.status) != "purchased":
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"需求 {requirement.requirement_no} 不是已采购状态")

        try:
            order.status = "cancelled"
            order.updated_by = actor
            order.updated_at = datetime.now(UTC)
            for requirement in requirements:
                requirement.status = "pending"
                requirement.purchased_qty = Decimal("0")
                requirement.received_qty = Decimal("0")
                requirement.purchase_order_id = None
                requirement.purchase_order_item_id = None
                requirement.purchase_no = None
                requirement.updated_by = actor
                requirement.updated_at = datetime.now(UTC)
                self._update_production_material_from_requirement(requirement=requirement)
            data = self._cancel_data(order=order, requirements=requirements, idempotency_key=idempotency_key, reason=reason)
            self.session.add(
                LyMaterialPurchaseIdempotency(
                    company=company,
                    idempotency_key=idempotency_key,
                    operation="cancel_order",
                    request_hash=request_hash,
                    record_id=int(order.id),
                    response_data=data.model_dump(mode="json"),
                    created_by=actor,
                )
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        return PurchaseOrderCancelMutationResult(
            item=data,
            before=before,
            after=data.model_dump(mode="json"),
            resource_id=int(order.id),
            resource_no=str(order.purchase_no),
        )

    def apply_receipt(
        self,
        *,
        company: str,
        purchase_no: str,
        item_quantities: dict[str, Decimal],
    ) -> None:
        """Apply material receipt draft quantities to a purchase order."""
        self.apply_receipt_rows(
            company=company,
            purchase_no=purchase_no,
            items=[{"item_code": item_code, "qty": qty} for item_code, qty in item_quantities.items()],
        )

    def validate_receipt_rows(
        self,
        *,
        company: str,
        purchase_no: str,
        items: list[dict[str, Any]],
    ) -> None:
        """Validate receipt rows against purchase order lines without mutating state."""
        self._apply_receipt_delta(company=company, purchase_no=purchase_no, items=items, direction=Decimal("1"), mutate=False)

    def apply_receipt_rows(
        self,
        *,
        company: str,
        purchase_no: str,
        items: list[dict[str, Any]],
    ) -> None:
        """Apply receipt rows to a purchase order, matching material and warehouse."""
        self._apply_receipt_delta(company=company, purchase_no=purchase_no, items=items, direction=Decimal("1"), mutate=True)

    def reverse_receipt_rows(
        self,
        *,
        company: str,
        purchase_no: str,
        items: list[dict[str, Any]],
    ) -> None:
        """Reverse receipt rows from a purchase order after a local draft cancel."""
        self._apply_receipt_delta(company=company, purchase_no=purchase_no, items=items, direction=Decimal("-1"), mutate=True)

    def expand_receipt_rows_for_requirement_context(
        self,
        *,
        company: str,
        purchase_no: str,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Split purchase receipt rows by demand context before they become stock facts."""
        order = self._get_order_by_no(company=company, purchase_no=purchase_no)
        if order is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购单不存在")
        if str(order.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购单已取消")

        lines = self._get_lines(order_id=int(order.id))
        expanded: list[dict[str, Any]] = []
        for source_index, item in enumerate(self._normalize_receipt_rows(items)):
            line = self._match_receipt_line(
                lines=lines,
                item_code=str(item["item_code"]),
                warehouse=self._optional_text(item.get("warehouse")),
            )
            requested_uom = self._optional_text(item.get("uom"))
            line_uom = self._optional_text(line.uom) or "米"
            if requested_uom is not None and requested_uom != line_uom:
                raise BusinessException(
                    code=MATERIAL_PURCHASE_CONFLICT,
                    message=f"采购入库单位与采购明细不一致: {item['item_code']} {requested_uom} != {line_uom}",
                )
            receipt_qty = Decimal(str(item["qty"]))
            requirement_id = item.get("purchase_requirement_id")
            if requirement_id is not None:
                requirement = self._match_receipt_requirement(
                    order=order,
                    line=line,
                    requirement_id=int(requirement_id),
                    item_code=str(item["item_code"]),
                    warehouse=self._optional_text(item.get("warehouse")),
                )
                expanded.append(
                    self._receipt_context_item(
                        source_index=source_index,
                        item=item,
                        line=line,
                        requirement=requirement,
                        qty=receipt_qty,
                    )
                )
                continue

            requirements = self._requirements_for_order_line(line=line)
            if not requirements:
                expanded.append(
                    {
                        **item,
                        "_source_index": source_index,
                    }
                )
                continue

            if len(requirements) == 1:
                expanded.append(
                    self._receipt_context_item(
                        source_index=source_index,
                        item=item,
                        line=line,
                        requirement=requirements[0],
                        qty=receipt_qty,
                    )
                )
                continue

            line_qty = Decimal(str(line.qty or 0))
            if receipt_qty != line_qty:
                raise BusinessException(
                    code=MATERIAL_PURCHASE_CONFLICT,
                    message=f"{line.material_item_code} 合并采购部分入库必须指定采购需求行",
                )

            remaining_qty = receipt_qty
            for requirement in requirements:
                purchased_qty = Decimal(str(requirement.purchased_qty or requirement.net_required_qty or 0))
                if purchased_qty <= Decimal("0"):
                    continue
                allocated_qty = min(purchased_qty, remaining_qty)
                if allocated_qty <= Decimal("0"):
                    continue
                expanded.append(
                    self._receipt_context_item(
                        source_index=source_index,
                        item=item,
                        line=line,
                        requirement=requirement,
                        qty=allocated_qty,
                    )
                )
                remaining_qty -= allocated_qty
            if remaining_qty != Decimal("0"):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"{line.material_item_code} 合并采购需求分摊数量不一致")
        return expanded

    def _apply_receipt_delta(
        self,
        *,
        company: str,
        purchase_no: str,
        items: list[dict[str, Any]],
        direction: Decimal,
        mutate: bool,
    ) -> None:
        order = self._get_order_by_no(company=company, purchase_no=purchase_no)
        if order is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购单不存在")
        if str(order.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购单已取消")
        lines = self._get_lines(order_id=int(order.id))
        line_deltas: dict[int, tuple[LyMaterialPurchaseOrderItem, Decimal]] = {}
        requirement_deltas: dict[int, tuple[LyMaterialPurchaseRequirement, Decimal]] = {}
        directed_line_ids: set[int] = set()
        undirected_line_ids: set[int] = set()
        for item in self._normalize_receipt_rows(items):
            line = self._match_receipt_line(
                lines=lines,
                item_code=str(item["item_code"]),
                warehouse=self._optional_text(item.get("warehouse")),
            )
            requested_uom = self._optional_text(item.get("uom"))
            line_uom = self._optional_text(line.uom) or "米"
            if requested_uom is not None and requested_uom != line_uom:
                raise BusinessException(
                    code=MATERIAL_PURCHASE_CONFLICT,
                    message=f"采购入库单位与采购明细不一致: {item['item_code']} {requested_uom} != {line_uom}",
                )
            line_id = int(line.id)
            requirement_id = item.get("purchase_requirement_id")
            if requirement_id is not None:
                directed_line_ids.add(line_id)
                requirement = self._match_receipt_requirement(
                    order=order,
                    line=line,
                    requirement_id=int(requirement_id),
                    item_code=str(item["item_code"]),
                    warehouse=self._optional_text(item.get("warehouse")),
                )
                requirement_delta = Decimal(str(item["qty"])) * direction
                requirement_key = int(requirement.id)
                if requirement_key in requirement_deltas:
                    requirement_deltas[requirement_key] = (requirement, requirement_deltas[requirement_key][1] + requirement_delta)
                else:
                    requirement_deltas[requirement_key] = (requirement, requirement_delta)
            else:
                undirected_line_ids.add(line_id)
            delta = Decimal(str(item["qty"])) * direction
            if line_id in line_deltas:
                line_deltas[line_id] = (line, line_deltas[line_id][1] + delta)
            else:
                line_deltas[line_id] = (line, delta)

        mixed_line_ids = directed_line_ids & undirected_line_ids
        if mixed_line_ids:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="同一采购明细不能混用指定和未指定采购需求行的入库")

        for line, delta in line_deltas.values():
            current_received = Decimal(str(line.received_qty or 0))
            next_received = current_received + delta
            if next_received < Decimal("0"):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"反冲收货数量超过已收数量: {line.material_item_code}")
            if next_received > Decimal(str(line.qty)):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"收货数量超过采购数量: {line.material_item_code}")
            if int(line.id) in undirected_line_ids:
                self._ensure_undirected_receipt_is_unambiguous(line=line, next_received=next_received)
            if mutate:
                line.received_qty = next_received

        for requirement, delta in requirement_deltas.values():
            current_received = Decimal(str(requirement.received_qty or 0))
            purchased_qty = Decimal(str(requirement.purchased_qty or requirement.net_required_qty or 0))
            next_received = current_received + delta
            if next_received < Decimal("0"):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"反冲收货数量超过需求已收数量: {requirement.requirement_no}")
            if next_received > purchased_qty:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"收货数量超过需求采购数量: {requirement.requirement_no}")

        if not mutate:
            return

        total_received = sum(Decimal(str(line.received_qty or 0)) for line in lines)
        total_qty = Decimal(str(order.total_qty or 0))
        order.received_qty = total_received
        if total_received <= Decimal("0"):
            order.status = "draft"
        else:
            order.status = "received" if total_received >= total_qty else "partially_received"
        self._apply_directed_requirement_receipt_deltas(order=order, requirement_deltas=requirement_deltas)
        undirected_lines = [line for line in lines if int(line.id) in undirected_line_ids]
        if undirected_lines:
            self._apply_requirement_receipts(order=order, lines=undirected_lines)
        self.session.flush()

    def list_purchase_invoices(
        self,
        *,
        company: str | None,
        keyword: str | None,
        supplier_name: str | None,
        status: str | None,
        page: int,
        page_size: int,
        allowed_companies: set[str] | None = None,
        allowed_materials: set[str] | None = None,
        allowed_suppliers: set[str] | None = None,
        allowed_warehouses: set[str] | None = None,
    ) -> MaterialPurchaseInvoiceListData:
        try:
            query = self.session.query(LyMaterialPurchaseInvoice)
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseInvoice.company,
                allowed_values=allowed_companies,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseInvoice.material_item_code,
                allowed_values=allowed_materials,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseInvoice.supplier_name,
                allowed_values=allowed_suppliers,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseInvoice.warehouse,
                allowed_values=allowed_warehouses,
            )
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyMaterialPurchaseInvoice.company == normalized_company)
            normalized_supplier = self._optional_text(supplier_name)
            if normalized_supplier:
                query = query.filter(func.lower(LyMaterialPurchaseInvoice.supplier_name).like(f"%{normalized_supplier.lower()}%"))
            normalized_status = self._optional_text(status)
            if normalized_status and normalized_status != "all":
                query = query.filter(LyMaterialPurchaseInvoice.status == normalized_status)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyMaterialPurchaseInvoice.purchase_invoice).like(like_value))
                    | (func.lower(LyMaterialPurchaseInvoice.purchase_no).like(like_value))
                    | (func.lower(LyMaterialPurchaseInvoice.supplier_name).like(like_value))
                    | (func.lower(LyMaterialPurchaseInvoice.material_item_code).like(like_value))
                    | (func.lower(LyMaterialPurchaseInvoice.material_name).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(LyMaterialPurchaseInvoice.created_at.desc(), LyMaterialPurchaseInvoice.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return MaterialPurchaseInvoiceListData(
            items=[self._invoice_data(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_purchase_invoice_create_scope_for_permission(
        self,
        *,
        payload: MaterialPurchaseInvoiceCreateRequest,
    ) -> dict[str, Any]:
        company = self._require_text(payload.company, "company")
        purchase_no = self._require_text(payload.purchase_no, "purchase_no")
        order = self._get_order_by_no(company=company, purchase_no=purchase_no)
        if order is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购单不存在")
        line = self._select_invoice_line(order_id=int(order.id), material_item_code=payload.material_item_code)
        return {
            "company": company,
            "item_code": str(line.material_item_code),
            "supplier": str(order.supplier_name),
            "warehouse": self._optional_text(line.warehouse),
        }

    def get_purchase_payment_create_scope_for_permission(
        self,
        *,
        payload: MaterialPurchasePaymentCreateRequest,
    ) -> dict[str, Any]:
        company = self._require_text(payload.company, "company")
        purchase_invoice = self._require_text(payload.purchase_invoice, "purchase_invoice")
        invoice = self._get_purchase_invoice_by_no(company=company, purchase_invoice=purchase_invoice)
        if invoice is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购发票不存在")
        return self._invoice_scope(invoice)

    def get_purchase_payment_cancel_scope_for_permission(
        self,
        *,
        payment_id: int,
        payload: MaterialPurchasePaymentCancelRequest,
    ) -> dict[str, Any]:
        company = self._require_text(payload.company, "company")
        payment = self._get_purchase_payment_by_id(company=company, payment_id=payment_id)
        if payment is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购付款单不存在")
        invoice = self._get_purchase_invoice_by_no(company=company, purchase_invoice=str(payment.purchase_invoice))
        if invoice is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购发票不存在")
        return self._invoice_scope(invoice)

    def create_purchase_invoice(
        self,
        *,
        payload: MaterialPurchaseInvoiceCreateRequest,
        actor: str,
    ) -> PurchaseInvoiceMutationResult:
        company = self._require_text(payload.company, "company")
        purchase_no = self._require_text(payload.purchase_no, "purchase_no")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        order = self._get_order_by_no(company=company, purchase_no=purchase_no)
        if order is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购单不存在")
        if str(order.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="已取消采购单不可开票")
        supplier_name = self._optional_text(payload.supplier_name) or str(order.supplier_name)
        if supplier_name != str(order.supplier_name):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="供应商与采购单不一致")

        line = self._select_invoice_line(order_id=int(order.id), material_item_code=payload.material_item_code)
        requested_qty = self._decimal_or_none(payload.qty)
        requested_rate = self._decimal_or_none(payload.rate)
        requested_purchase_invoice = self._optional_text(payload.purchase_invoice)
        requested_source_ref = self._optional_text(payload.source_ref)
        purchase_invoice = requested_purchase_invoice or self._next_purchase_invoice()
        source_ref = requested_source_ref or f"{purchase_invoice}:{purchase_no}:{line.material_item_code}"
        request_hash = self._mutation_hash(
            {
                "operation": "create_purchase_invoice",
                "company": company,
                "purchase_invoice": requested_purchase_invoice,
                "purchase_no": purchase_no,
                "supplier_name": supplier_name,
                "material_item_code": str(line.material_item_code),
                "qty": str(requested_qty) if requested_qty is not None else None,
                "rate": str(requested_rate) if requested_rate is not None else None,
                "posting_date": payload.posting_date.isoformat(),
                "due_date": payload.due_date.isoformat() if payload.due_date else None,
                "source_ref": requested_source_ref,
            }
        )

        existing_idem = self._get_purchase_invoice_by_idempotency(company=company, idempotency_key=idempotency_key)
        if existing_idem is not None:
            if str(existing_idem.request_hash) != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT, message="采购发票幂等键重复但载荷不一致")
            data = self._invoice_data(existing_idem)
            snapshot = data.model_dump(mode="json")
            return PurchaseInvoiceMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(existing_idem.id),
                resource_no=str(existing_idem.purchase_invoice),
                idempotent=True,
            )

        existing_source = self._get_purchase_invoice_by_source(company=company, source_ref=source_ref)
        if existing_source is not None:
            if str(existing_source.request_hash) != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="source_ref 已存在且载荷不一致")
            data = self._invoice_data(existing_source)
            snapshot = data.model_dump(mode="json")
            return PurchaseInvoiceMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(existing_source.id),
                resource_no=str(existing_source.purchase_invoice),
                idempotent=True,
            )

        received_qty = Decimal(str(line.received_qty or 0))
        invoiced_qty = self._invoiced_qty(
            company=company,
            purchase_no=purchase_no,
            material_item_code=str(line.material_item_code),
        )
        available_qty = received_qty - invoiced_qty
        qty = requested_qty or available_qty
        if qty <= Decimal("0"):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="无可开票入库数量")
        if qty > available_qty:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="开票数量超过已入库未开票数量")

        rate = requested_rate
        if rate is None:
            rate = Decimal(str(line.unit_price or 0))
        if rate < Decimal("0"):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="rate 不得为负数")
        grand_total = qty * rate

        if self._get_purchase_invoice_by_no(company=company, purchase_invoice=purchase_invoice) is not None:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="purchase_invoice 已存在")

        try:
            row = LyMaterialPurchaseInvoice(
                company=company,
                purchase_invoice=purchase_invoice,
                purchase_order_id=int(order.id),
                purchase_no=purchase_no,
                supplier_name=supplier_name,
                material_item_code=str(line.material_item_code),
                material_name=str(line.material_name or line.material_item_code),
                warehouse=line.warehouse,
                qty=qty,
                uom=str(line.uom or "米"),
                rate=rate,
                grand_total=grand_total,
                paid_amount=Decimal("0"),
                outstanding_amount=grand_total,
                posting_date=payload.posting_date,
                due_date=payload.due_date,
                status="submitted",
                docstatus=1,
                source_ref=source_ref,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                scenario_tag=self._optional_text(payload.scenario_tag),
                payload={
                    "operation": "create_purchase_invoice",
                    "purchase_no": purchase_no,
                    "material_item_code": str(line.material_item_code),
                },
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        data = self._invoice_data(row)
        return PurchaseInvoiceMutationResult(
            item=data,
            before=None,
            after=data.model_dump(mode="json"),
            resource_id=int(row.id),
            resource_no=str(row.purchase_invoice),
        )

    def list_purchase_payments(
        self,
        *,
        company: str | None,
        keyword: str | None,
        supplier_name: str | None,
        status: str | None,
        page: int,
        page_size: int,
        allowed_companies: set[str] | None = None,
        allowed_materials: set[str] | None = None,
        allowed_suppliers: set[str] | None = None,
        allowed_warehouses: set[str] | None = None,
    ) -> MaterialPurchasePaymentListData:
        try:
            query = self.session.query(LyMaterialPurchasePayment).join(
                LyMaterialPurchaseInvoice,
                LyMaterialPurchaseInvoice.id == LyMaterialPurchasePayment.purchase_invoice_id,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchasePayment.company,
                allowed_values=allowed_companies,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseInvoice.material_item_code,
                allowed_values=allowed_materials,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchasePayment.supplier_name,
                allowed_values=allowed_suppliers,
            )
            query = self._apply_required_scope_filter(
                query=query,
                column=LyMaterialPurchaseInvoice.warehouse,
                allowed_values=allowed_warehouses,
            )
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyMaterialPurchasePayment.company == normalized_company)
            normalized_supplier = self._optional_text(supplier_name)
            if normalized_supplier:
                query = query.filter(func.lower(LyMaterialPurchasePayment.supplier_name).like(f"%{normalized_supplier.lower()}%"))
            normalized_status = self._optional_text(status)
            if normalized_status and normalized_status != "all":
                query = query.filter(LyMaterialPurchasePayment.status == normalized_status)
            normalized_keyword = self._optional_text(keyword)
            if normalized_keyword:
                like_value = f"%{normalized_keyword.lower()}%"
                query = query.filter(
                    (func.lower(LyMaterialPurchasePayment.payment_entry).like(like_value))
                    | (func.lower(LyMaterialPurchasePayment.purchase_invoice).like(like_value))
                    | (func.lower(LyMaterialPurchasePayment.purchase_no).like(like_value))
                    | (func.lower(LyMaterialPurchasePayment.supplier_name).like(like_value))
                    | (func.lower(LyMaterialPurchasePayment.mode_of_payment).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(LyMaterialPurchasePayment.created_at.desc(), LyMaterialPurchasePayment.id.desc())
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return MaterialPurchasePaymentListData(
            items=[self._payment_data(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_purchase_payment(
        self,
        *,
        payload: MaterialPurchasePaymentCreateRequest,
        actor: str,
    ) -> PurchasePaymentMutationResult:
        company = self._require_text(payload.company, "company")
        purchase_invoice = self._require_text(payload.purchase_invoice, "purchase_invoice")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        paid_amount = self._positive_decimal(payload.paid_amount, "paid_amount")
        supplier_name = self._optional_text(payload.supplier_name)
        mode_of_payment = self._optional_text(payload.mode_of_payment) or "Bank Transfer"
        requested_payment_entry = self._optional_text(payload.payment_entry)
        source_ref = self._optional_text(payload.source_ref) or f"{purchase_invoice}:{idempotency_key}"
        request_hash = self._mutation_hash(
            {
                "operation": "create_purchase_payment",
                "company": company,
                "purchase_invoice": purchase_invoice,
                "supplier_name": supplier_name,
                "posting_date": payload.posting_date.isoformat(),
                "paid_amount": str(paid_amount),
                "mode_of_payment": mode_of_payment,
                "reference_no": self._optional_text(payload.reference_no),
                "reference_date": payload.reference_date.isoformat() if payload.reference_date else None,
                "requested_payment_entry": requested_payment_entry,
                "source_ref": source_ref,
            }
        )

        existing_idem = self._get_purchase_payment_by_idempotency(company=company, idempotency_key=idempotency_key)
        if existing_idem is not None:
            if str(existing_idem.request_hash) != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT, message="采购付款幂等键重复但载荷不一致")
            data = self._payment_data(existing_idem)
            snapshot = data.model_dump(mode="json")
            return PurchasePaymentMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(existing_idem.id),
                resource_no=str(existing_idem.payment_entry),
                idempotent=True,
            )

        existing_source = self._get_purchase_payment_by_source(company=company, source_ref=source_ref)
        if existing_source is not None:
            if str(existing_source.request_hash) != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="source_ref 已存在且载荷不一致")
            data = self._payment_data(existing_source)
            snapshot = data.model_dump(mode="json")
            return PurchasePaymentMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(existing_source.id),
                resource_no=str(existing_source.payment_entry),
                idempotent=True,
            )

        invoice = (
            self.session.query(LyMaterialPurchaseInvoice)
            .filter(
                LyMaterialPurchaseInvoice.company == company,
                LyMaterialPurchaseInvoice.purchase_invoice == purchase_invoice,
            )
            .with_for_update()
            .first()
        )
        if invoice is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购发票不存在")
        if str(invoice.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="已取消采购发票不可付款")
        if self._finance_approval_status(invoice) != "approved":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购发票财务审批通过后才能创建付款")
        if supplier_name is not None and supplier_name != str(invoice.supplier_name):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="供应商与采购发票不一致")
        invoice_outstanding_before = Decimal(str(invoice.outstanding_amount or 0))
        pending_amount = self._pending_purchase_payment_amount(company=company, purchase_invoice=purchase_invoice)
        outstanding_before = invoice_outstanding_before - pending_amount
        if outstanding_before < Decimal("0"):
            outstanding_before = Decimal("0")
        if outstanding_before <= Decimal("0"):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购发票无未付款余额")
        if paid_amount > outstanding_before:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="付款金额超过未付款余额")

        payment_entry = requested_payment_entry or self._next_purchase_payment()
        if self._get_purchase_payment_by_no(company=company, payment_entry=payment_entry) is not None:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="payment_entry 已存在")

        outstanding_after = outstanding_before - paid_amount
        before = self._invoice_data(invoice).model_dump(mode="json")
        try:
            row = LyMaterialPurchasePayment(
                company=company,
                payment_entry=payment_entry,
                purchase_invoice_id=int(invoice.id),
                purchase_invoice=str(invoice.purchase_invoice),
                purchase_no=str(invoice.purchase_no),
                supplier_name=str(invoice.supplier_name),
                posting_date=payload.posting_date,
                paid_amount=paid_amount,
                allocated_amount=paid_amount,
                outstanding_before=outstanding_before,
                outstanding_after=outstanding_after,
                mode_of_payment=mode_of_payment,
                reference_no=self._optional_text(payload.reference_no),
                reference_date=payload.reference_date,
                status="pending_approval",
                docstatus=0,
                source_ref=source_ref,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                scenario_tag=self._optional_text(payload.scenario_tag),
                payload={
                    "operation": "create_purchase_payment",
                    "purchase_invoice": purchase_invoice,
                    "approval_effect": "pending",
                    "invoice_outstanding_before": str(invoice_outstanding_before),
                    "reserved_outstanding_before": str(outstanding_before),
                    "reserved_outstanding_after": str(outstanding_after),
                },
                created_by=actor,
                updated_by=actor,
            )
            self.session.add(row)
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        data = self._payment_data(row)
        return PurchasePaymentMutationResult(
            item=data,
            before=before,
            after={
                "payment": data.model_dump(mode="json"),
                "invoice": self._invoice_data(invoice).model_dump(mode="json"),
            },
            resource_id=int(row.id),
                resource_no=str(row.payment_entry),
        )

    def apply_purchase_payment_approval(
        self,
        *,
        payment_id: int,
        actor: str,
        approved_at: datetime | None = None,
    ) -> PurchasePaymentMutationResult:
        row = self._get_purchase_payment_by_id_for_update(company=None, payment_id=payment_id)
        if row is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购付款单不存在")
        if str(row.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="已取消采购付款不可生效")

        invoice = (
            self.session.query(LyMaterialPurchaseInvoice)
            .filter(
                LyMaterialPurchaseInvoice.company == row.company,
                LyMaterialPurchaseInvoice.purchase_invoice == row.purchase_invoice,
            )
            .with_for_update()
            .first()
        )
        if invoice is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购发票不存在")
        if str(invoice.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="已取消采购发票不可付款")

        if str(row.status) == "submitted":
            data = self._payment_data(row)
            snapshot = data.model_dump(mode="json")
            return PurchasePaymentMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(row.id),
                resource_no=str(row.payment_entry),
                idempotent=True,
            )

        paid_amount = Decimal(str(row.paid_amount or 0))
        outstanding_before = Decimal(str(invoice.outstanding_amount or 0))
        if outstanding_before <= Decimal("0"):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购发票无未付款余额")
        if paid_amount > outstanding_before:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="付款金额超过未付款余额")

        outstanding_after = outstanding_before - paid_amount
        now = approved_at or datetime.now(UTC)
        before = {
            "payment": self._payment_data(row).model_dump(mode="json"),
            "invoice": self._invoice_data(invoice).model_dump(mode="json"),
        }
        try:
            invoice.paid_amount = Decimal(str(invoice.paid_amount or 0)) + paid_amount
            invoice.outstanding_amount = outstanding_after
            invoice.status = "paid" if outstanding_after == Decimal("0") else "partly_paid"
            invoice.updated_by = actor
            invoice.updated_at = now

            row.outstanding_before = outstanding_before
            row.outstanding_after = outstanding_after
            row.status = "submitted"
            row.docstatus = 1
            row.updated_by = actor
            row.updated_at = now
            payment_payload = row.payload if isinstance(row.payload, dict) else {}
            row.payload = {
                **payment_payload,
                "approval_effect": "applied",
                "applied_by": actor,
                "applied_at": now.isoformat(),
            }
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        data = self._payment_data(row)
        return PurchasePaymentMutationResult(
            item=data,
            before=before,
            after={
                "payment": data.model_dump(mode="json"),
                "invoice": self._invoice_data(invoice).model_dump(mode="json"),
            },
            resource_id=int(row.id),
            resource_no=str(row.payment_entry),
        )

    def reject_pending_purchase_payment(
        self,
        *,
        payment_id: int,
        actor: str,
        rejected_at: datetime | None = None,
    ) -> PurchasePaymentMutationResult:
        row = self._get_purchase_payment_by_id_for_update(company=None, payment_id=payment_id)
        if row is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购付款单不存在")
        if str(row.status) != "pending_approval":
            data = self._payment_data(row)
            snapshot = data.model_dump(mode="json")
            return PurchasePaymentMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(row.id),
                resource_no=str(row.payment_entry),
                idempotent=True,
            )

        now = rejected_at or datetime.now(UTC)
        before = self._payment_data(row).model_dump(mode="json")
        try:
            row.status = "cancelled"
            row.docstatus = 2
            row.updated_by = actor
            row.updated_at = now
            payment_payload = row.payload if isinstance(row.payload, dict) else {}
            row.payload = {
                **payment_payload,
                "approval_effect": "rejected",
                "rejected_by": actor,
                "rejected_at": now.isoformat(),
            }
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        data = self._payment_data(row)
        return PurchasePaymentMutationResult(
            item=data,
            before=before,
            after=data.model_dump(mode="json"),
            resource_id=int(row.id),
            resource_no=str(row.payment_entry),
        )

    def cancel_purchase_payment(
        self,
        *,
        payment_id: int,
        payload: MaterialPurchasePaymentCancelRequest,
        actor: str,
    ) -> PurchasePaymentMutationResult:
        company = self._require_text(payload.company, "company")
        purchase_invoice = self._require_text(payload.purchase_invoice, "purchase_invoice")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        reason = self._optional_text(payload.reason)
        operation = str(payload.operation or "cancel_purchase_payment")
        if operation != "cancel_purchase_payment":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="operation 非法")

        row = self._get_purchase_payment_by_id_for_update(company=company, payment_id=payment_id)
        if row is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购付款单不存在")
        if str(row.purchase_invoice) != purchase_invoice:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="purchase_invoice 与付款单不一致")

        request_hash = self._mutation_hash(
            {
                "operation": operation,
                "company": company,
                "purchase_invoice": purchase_invoice,
                "payment_id": int(row.id),
                "payment_entry": str(row.payment_entry),
                "reason": reason,
            }
        )
        existing_operation = self._get_purchase_payment_operation_by_idempotency(
            company=company,
            operation_type=operation,
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if str(existing_operation.request_hash or "") != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="幂等键冲突且请求内容不一致")
            replay_row = self._get_purchase_payment_by_id(
                company=company,
                payment_id=int(existing_operation.payment_id),
            )
            if replay_row is None:
                raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购付款单不存在")
            data = self._payment_data(replay_row)
            snapshot = data.model_dump(mode="json")
            return PurchasePaymentMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(replay_row.id),
                resource_no=str(replay_row.payment_entry),
                idempotent=True,
            )
        if str(row.status) != "submitted":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购付款单已作废")

        invoice = (
            self.session.query(LyMaterialPurchaseInvoice)
            .filter(
                LyMaterialPurchaseInvoice.company == company,
                LyMaterialPurchaseInvoice.purchase_invoice == purchase_invoice,
            )
            .with_for_update()
            .first()
        )
        if invoice is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购发票不存在")
        if str(invoice.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="已取消采购发票不可作废付款")

        before = self._invoice_data(invoice).model_dump(mode="json")
        paid_amount = Decimal(str(row.paid_amount or 0))
        paid_after = Decimal(str(invoice.paid_amount or 0)) - paid_amount
        if paid_after < Decimal("0"):
            paid_after = Decimal("0")
        grand_total = Decimal(str(invoice.grand_total or 0))
        outstanding_after = grand_total - paid_after
        if outstanding_after < Decimal("0"):
            outstanding_after = Decimal("0")

        now = datetime.now(UTC)
        try:
            invoice.paid_amount = paid_after
            invoice.outstanding_amount = outstanding_after
            invoice.status = "paid" if outstanding_after == Decimal("0") else ("submitted" if paid_after == Decimal("0") else "partly_paid")
            invoice.updated_by = actor
            invoice.updated_at = now

            row.status = "cancelled"
            row.docstatus = 2
            row.updated_by = actor
            row.updated_at = now

            self.session.add(
                LyMaterialPurchasePaymentOperation(
                    company=company,
                    purchase_invoice=purchase_invoice,
                    payment_id=int(row.id),
                    operation_type=operation,
                    idempotency_key=idempotency_key,
                    request_hash=request_hash,
                    result_status="cancelled",
                    result_user=actor,
                    result_at=now,
                    reason=reason,
                )
            )
            replay_operation = self._flush_purchase_payment_operation_or_resolve_replay(
                company=company,
                operation_type=operation,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_WRITE_FAILED) from exc

        if replay_operation is not None:
            replay_row = self._get_purchase_payment_by_id(
                company=company,
                payment_id=int(replay_operation.payment_id),
            )
            if replay_row is None:
                raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购付款单不存在")
            data = self._payment_data(replay_row)
            snapshot = data.model_dump(mode="json")
            return PurchasePaymentMutationResult(
                item=data,
                before=snapshot,
                after=snapshot,
                resource_id=int(replay_row.id),
                resource_no=str(replay_row.payment_entry),
                idempotent=True,
            )
        data = self._payment_data(row)
        return PurchasePaymentMutationResult(
            item=data,
            before=before,
            after={
                "payment": data.model_dump(mode="json"),
                "invoice": self._invoice_data(invoice).model_dump(mode="json"),
            },
            resource_id=int(data.id),
            resource_no=str(data.payment_entry),
        )

    def snapshot_order(self, *, order_id: int) -> dict[str, Any]:
        row = self._get_order_by_id(order_id)
        return self._create_data(row=row, idempotency_key="").model_dump(mode="json")

    def _create_data(self, *, row: LyMaterialPurchaseOrder, idempotency_key: str) -> MaterialPurchaseOrderCreateData:
        lines = self._get_lines(order_id=int(row.id))
        return MaterialPurchaseOrderCreateData(
            id=int(row.id),
            purchase_no=str(row.purchase_no),
            company=str(row.company),
            supplier_name=str(row.supplier_name),
            status=str(row.status),
            total_qty=Decimal(str(row.total_qty or 0)),
            received_qty=Decimal(str(row.received_qty or 0)),
            total_amount=Decimal(str(row.total_amount or 0)),
            currency=str(row.currency or "CNY"),
            idempotency_key=idempotency_key,
            created_at=row.created_at,
            items=[self._list_item(row, line) for line in lines],
        )

    def _requirement_order_data(
        self,
        *,
        order: LyMaterialPurchaseOrder,
        requirements: list[LyMaterialPurchaseRequirement],
    ) -> MaterialPurchaseRequirementToOrderData:
        return MaterialPurchaseRequirementToOrderData(
            purchase_order=self._create_data(row=order, idempotency_key=""),
            requirements=[self._requirement_item(row) for row in requirements],
        )

    def _cancel_data(
        self,
        *,
        order: LyMaterialPurchaseOrder,
        requirements: list[LyMaterialPurchaseRequirement],
        idempotency_key: str,
        reason: str,
    ) -> MaterialPurchaseOrderCancelData:
        return MaterialPurchaseOrderCancelData(
            purchase_order=self._create_data(row=order, idempotency_key=idempotency_key),
            requirements=[self._requirement_item(row) for row in requirements],
            reason=reason,
        )

    def _list_item(self, order: LyMaterialPurchaseOrder, line: LyMaterialPurchaseOrderItem) -> MaterialPurchaseOrderListItem:
        return MaterialPurchaseOrderListItem(
            id=int(line.id),
            order_id=int(order.id),
            line_id=int(line.id),
            company=str(order.company),
            purchase_no=str(order.purchase_no),
            supplier_name=str(order.supplier_name),
            item_code=str(line.item_code),
            material_item_code=str(line.material_item_code),
            material_name=str(line.material_name or ""),
            qty=Decimal(str(line.qty or 0)),
            received_qty=Decimal(str(line.received_qty or 0)),
            uom=str(line.uom or ""),
            unit_price=Decimal(str(line.unit_price or 0)),
            total_amount=Decimal(str(line.amount or 0)),
            expected_delivery_date=order.expected_delivery_date,
            transaction_date=order.transaction_date,
            status=str(order.status),
            warehouse=line.warehouse,
            currency=str(order.currency or "CNY"),
            created_at=order.created_at,
        )

    def _invoice_data(self, row: LyMaterialPurchaseInvoice) -> MaterialPurchaseInvoiceData:
        financial_ledger = self._purchase_invoice_financial_ledger(row)
        return MaterialPurchaseInvoiceData(
            id=int(row.id),
            company=str(row.company),
            purchase_invoice=str(row.purchase_invoice),
            purchase_order_id=int(row.purchase_order_id),
            purchase_no=str(row.purchase_no),
            supplier_name=str(row.supplier_name),
            material_item_code=str(row.material_item_code),
            material_name=str(row.material_name or ""),
            warehouse=self._optional_text(row.warehouse),
            qty=Decimal(str(row.qty or 0)),
            uom=str(row.uom or "米"),
            rate=Decimal(str(row.rate or 0)),
            grand_total=Decimal(str(row.grand_total or 0)),
            paid_amount=Decimal(str(row.paid_amount or 0)),
            outstanding_amount=Decimal(str(row.outstanding_amount or 0)),
            posting_date=row.posting_date,
            due_date=row.due_date,
            status=str(row.status),  # type: ignore[arg-type]
            docstatus=int(row.docstatus or 0),
            source_ref=str(row.source_ref),
            idempotency_key=str(row.idempotency_key),
            scenario_tag=self._optional_text(row.scenario_tag),
            approval_status=self._finance_approval_status(row),
            approval_no=self._finance_approval_no(row),
            **financial_ledger,
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    def _payment_data(self, row: LyMaterialPurchasePayment) -> MaterialPurchasePaymentData:
        financial_ledger = self._purchase_payment_financial_ledger(row)
        return MaterialPurchasePaymentData(
            id=int(row.id),
            company=str(row.company),
            payment_entry=str(row.payment_entry),
            purchase_invoice_id=int(row.purchase_invoice_id),
            purchase_invoice=str(row.purchase_invoice),
            purchase_no=str(row.purchase_no),
            supplier_name=str(row.supplier_name),
            posting_date=row.posting_date,
            paid_amount=Decimal(str(row.paid_amount or 0)),
            allocated_amount=Decimal(str(row.allocated_amount or 0)),
            outstanding_before=Decimal(str(row.outstanding_before or 0)),
            outstanding_after=Decimal(str(row.outstanding_after or 0)),
            mode_of_payment=str(row.mode_of_payment or "Bank Transfer"),
            reference_no=self._optional_text(row.reference_no),
            reference_date=row.reference_date,
            status=str(row.status),  # type: ignore[arg-type]
            docstatus=int(row.docstatus or 0),
            source_ref=str(row.source_ref),
            idempotency_key=str(row.idempotency_key),
            scenario_tag=self._optional_text(row.scenario_tag),
            approval_status=self._finance_approval_status(row),
            approval_no=self._finance_approval_no(row),
            **financial_ledger,
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    @staticmethod
    def _purchase_invoice_financial_ledger(row: LyMaterialPurchaseInvoice) -> dict[str, Decimal | bool | str]:
        status = str(row.status or "")
        grand_total = Decimal(str(row.grand_total or 0))
        paid_amount = Decimal(str(row.paid_amount or 0))
        outstanding_amount = Decimal(str(row.outstanding_amount or 0))
        if status == "cancelled":
            ledger_status = "cancelled"
            ledger_status_name = "已取消"
            ledger_payable_amount = Decimal("0")
            ledger_cash_out_amount = Decimal("0")
            ledger_outstanding_amount = Decimal("0")
        elif status == "paid" or outstanding_amount <= Decimal("0"):
            ledger_status = "closed"
            ledger_status_name = "总账已闭合"
            ledger_payable_amount = grand_total
            ledger_cash_out_amount = paid_amount
            ledger_outstanding_amount = Decimal("0")
        elif paid_amount > Decimal("0"):
            ledger_status = "partial"
            ledger_status_name = "部分归集"
            ledger_payable_amount = grand_total
            ledger_cash_out_amount = paid_amount
            ledger_outstanding_amount = outstanding_amount
        else:
            ledger_status = "posted"
            ledger_status_name = "总账已归集"
            ledger_payable_amount = grand_total
            ledger_cash_out_amount = Decimal("0")
            ledger_outstanding_amount = outstanding_amount
        return {
            "financial_ledger_status": ledger_status,
            "financial_ledger_status_name": ledger_status_name,
            "financial_ledger_payable_amount": ledger_payable_amount,
            "financial_ledger_cash_out_amount": ledger_cash_out_amount,
            "financial_ledger_outstanding_amount": ledger_outstanding_amount,
            "financial_ledger_closed": ledger_status == "closed",
            "financial_ledger_source_note": (
                f"采购发票 {row.purchase_invoice}；应付 {grand_total}；已付 {paid_amount}；未付 {outstanding_amount}"
            ),
        }

    @staticmethod
    def _purchase_payment_financial_ledger(row: LyMaterialPurchasePayment) -> dict[str, Decimal | bool | str]:
        status = str(row.status or "")
        paid_amount = Decimal(str(row.paid_amount or 0))
        outstanding_after = Decimal(str(row.outstanding_after or 0))
        if status == "submitted":
            ledger_status = "closed" if outstanding_after <= Decimal("0") else "partial"
            ledger_status_name = "总账已闭合" if ledger_status == "closed" else "部分归集"
            ledger_cash_out_amount = paid_amount
        elif status == "cancelled":
            ledger_status = "cancelled"
            ledger_status_name = "已取消"
            ledger_cash_out_amount = Decimal("0")
        else:
            ledger_status = "pending"
            ledger_status_name = "待审批"
            ledger_cash_out_amount = Decimal("0")
        return {
            "financial_ledger_status": ledger_status,
            "financial_ledger_status_name": ledger_status_name,
            "financial_ledger_cash_out_amount": ledger_cash_out_amount,
            "financial_ledger_outstanding_amount": Decimal("0") if status == "cancelled" else outstanding_after,
            "financial_ledger_closed": ledger_status == "closed",
            "financial_ledger_source_note": (
                f"采购付款 {row.payment_entry}；采购发票 {row.purchase_invoice}；状态 {status or '-'}"
            ),
        }

    @classmethod
    def _finance_approval_payload(cls, row: Any) -> dict[str, Any]:
        payload = row.payload if isinstance(row.payload, dict) else {}
        approval = payload.get("finance_approval")
        return approval if isinstance(approval, dict) else {}

    @classmethod
    def _finance_approval_status(cls, row: Any) -> str:
        status = cls._finance_approval_payload(row).get("status")
        return str(status or "not_submitted")

    @classmethod
    def _finance_approval_no(cls, row: Any) -> str | None:
        return cls._optional_text(cls._finance_approval_payload(row).get("approval_no"))

    def _requirement_item(self, row: LyMaterialPurchaseRequirement) -> MaterialPurchaseRequirementListItem:
        net_required = Decimal(str(row.net_required_qty or 0))
        received_qty = Decimal(str(row.received_qty or 0))
        has_completed = net_required == Decimal("0") or received_qty >= net_required or str(row.status) == "completed"
        return MaterialPurchaseRequirementListItem(
            id=int(row.id),
            company=str(row.company),
            requirement_no=str(row.requirement_no),
            source_type=str(row.source_type),
            source_id=str(row.source_id),
            source_no=self._optional_text(row.source_no),
            plan_id=(int(row.plan_id) if row.plan_id is not None else None),
            bom_item_id=(int(row.bom_item_id) if row.bom_item_id is not None else None),
            bom_color=self._optional_text(row.bom_color),
            bom_size=self._optional_text(row.bom_size),
            bom_part=self._optional_text(row.bom_part),
            sales_order=self._optional_text(row.sales_order),
            sales_order_item=self._optional_text(row.sales_order_item),
            item_code=self._optional_text(row.item_code),
            material_item_code=str(row.material_item_code),
            material_name=str(row.material_name or row.material_item_code),
            supplier_name=self._optional_text(row.supplier_name),
            warehouse=str(row.warehouse),
            required_qty=Decimal(str(row.required_qty or 0)),
            available_qty=Decimal(str(row.available_qty or 0)),
            net_required_qty=net_required,
            purchased_qty=Decimal(str(row.purchased_qty or 0)),
            received_qty=received_qty,
            uom=str(row.uom or "米"),
            unit_price=Decimal(str(row.unit_price or 0)),
            status=str(row.status),  # type: ignore[arg-type]
            has_completed=has_completed,
            purchase_no=self._optional_text(row.purchase_no),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def _group_requirement_items_for_list(
        self,
        rows: list[LyMaterialPurchaseRequirement],
    ) -> list[MaterialPurchaseRequirementListItem]:
        grouped: dict[tuple[str, str, str, str, str, str], list[LyMaterialPurchaseRequirement]] = {}
        for row in rows:
            key = (
                str(row.status or ""),
                self._optional_text(row.supplier_name) or "",
                str(row.material_item_code),
                str(row.warehouse),
                str(row.uom or "米"),
                self._optional_text(row.purchase_no) or "",
            )
            grouped.setdefault(key, []).append(row)

        return [self._grouped_requirement_item(bucket) for bucket in grouped.values()]

    def _grouped_requirement_item(
        self,
        rows: list[LyMaterialPurchaseRequirement],
    ) -> MaterialPurchaseRequirementListItem:
        first = rows[0]
        base = self._requirement_item(first)
        if len(rows) == 1:
            return base.model_copy(
                update={
                    "requirement_ids": [int(first.id)],
                    "requirement_count": 1,
                    "is_grouped": False,
                }
            )

        items = [self._requirement_item(row) for row in rows]
        requirement_ids = [int(row.id) for row in rows]
        required_qty = sum((item.required_qty for item in items), Decimal("0"))
        available_qty = sum((item.available_qty for item in items), Decimal("0"))
        net_required_qty = sum((item.net_required_qty for item in items), Decimal("0"))
        purchased_qty = sum((item.purchased_qty for item in items), Decimal("0"))
        received_qty = sum((item.received_qty for item in items), Decimal("0"))
        purchase_nos = self._unique_texts(item.purchase_no for item in items)
        sales_orders = self._unique_texts(item.sales_order for item in items)
        source_nos = self._unique_texts(item.source_no for item in items)
        sales_order_items = self._unique_texts(item.sales_order_item for item in items)
        item_codes = self._unique_texts(item.item_code for item in items)
        bom_colors = self._unique_texts(item.bom_color for item in items)
        bom_sizes = self._unique_texts(item.bom_size for item in items)
        bom_parts = self._unique_texts(item.bom_part for item in items)
        unit_prices = {Decimal(str(item.unit_price or 0)) for item in items}
        unit_price = unit_prices.pop() if len(unit_prices) == 1 else Decimal("0")

        return MaterialPurchaseRequirementListItem(
            id=int(first.id),
            requirement_ids=requirement_ids,
            requirement_count=len(rows),
            is_grouped=True,
            company=str(first.company),
            requirement_no=f"合并需求({len(rows)})",
            source_type="grouped_material_requirement",
            source_id=",".join(str(row_id) for row_id in requirement_ids),
            source_no=self._join_texts(source_nos),
            plan_id=(int(first.plan_id) if len({row.plan_id for row in rows}) == 1 and first.plan_id is not None else None),
            bom_item_id=None,
            bom_color=self._join_texts(bom_colors),
            bom_size=self._join_texts(bom_sizes),
            bom_part=self._join_texts(bom_parts),
            sales_order=self._join_texts(sales_orders),
            sales_order_item=self._join_texts(sales_order_items),
            item_code=self._join_texts(item_codes),
            material_item_code=str(first.material_item_code),
            material_name=str(first.material_name or first.material_item_code),
            supplier_name=self._optional_text(first.supplier_name),
            warehouse=str(first.warehouse),
            required_qty=required_qty,
            available_qty=available_qty,
            net_required_qty=net_required_qty,
            purchased_qty=purchased_qty,
            received_qty=received_qty,
            uom=str(first.uom or "米"),
            unit_price=unit_price,
            status=str(first.status),  # type: ignore[arg-type]
            has_completed=all(item.has_completed for item in items),
            purchase_no=self._join_texts(purchase_nos),
            created_at=first.created_at,
            updated_at=max((item.updated_at for item in items if item.updated_at is not None), default=first.updated_at),
        )

    @classmethod
    def _unique_texts(cls, values: Any) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = cls._optional_text(value)
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @classmethod
    def _join_texts(cls, values: list[str]) -> str | None:
        if not values:
            return None
        return "、".join(values[:3]) + (f"等{len(values)}项" if len(values) > 3 else "")

    def _get_order_by_no(self, *, company: str, purchase_no: str) -> LyMaterialPurchaseOrder | None:
        return (
            self.session.query(LyMaterialPurchaseOrder)
            .filter(LyMaterialPurchaseOrder.company == company, LyMaterialPurchaseOrder.purchase_no == purchase_no)
            .first()
        )

    def _get_order_by_id(self, order_id: int) -> LyMaterialPurchaseOrder:
        row = self.session.query(LyMaterialPurchaseOrder).filter(LyMaterialPurchaseOrder.id == order_id).first()
        if row is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购单不存在")
        return row

    def _get_order_by_id_for_company(self, *, company: str, order_id: int, for_update: bool = False) -> LyMaterialPurchaseOrder:
        query = self.session.query(LyMaterialPurchaseOrder).filter(
            LyMaterialPurchaseOrder.id == int(order_id),
            LyMaterialPurchaseOrder.company == company,
        )
        if for_update:
            query = query.with_for_update()
        row = query.first()
        if row is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购单不存在")
        return row

    def _get_lines(self, *, order_id: int) -> list[LyMaterialPurchaseOrderItem]:
        return (
            self.session.query(LyMaterialPurchaseOrderItem)
            .filter(LyMaterialPurchaseOrderItem.order_id == order_id)
            .order_by(LyMaterialPurchaseOrderItem.id.asc())
            .all()
        )

    def _requirements_by_order(
        self,
        *,
        company: str,
        order_id: int,
        for_update: bool = False,
    ) -> list[LyMaterialPurchaseRequirement]:
        query = (
            self.session.query(LyMaterialPurchaseRequirement)
            .filter(
                LyMaterialPurchaseRequirement.company == company,
                LyMaterialPurchaseRequirement.purchase_order_id == int(order_id),
            )
            .order_by(LyMaterialPurchaseRequirement.id.asc())
        )
        if for_update:
            query = query.with_for_update()
        return query.all()

    def _requirements_by_ids(
        self,
        *,
        company: str,
        requirement_ids: list[int],
        for_update: bool = False,
    ) -> list[LyMaterialPurchaseRequirement]:
        query = (
            self.session.query(LyMaterialPurchaseRequirement)
            .filter(
                LyMaterialPurchaseRequirement.company == company,
                LyMaterialPurchaseRequirement.id.in_(requirement_ids),
            )
            .order_by(LyMaterialPurchaseRequirement.id.asc())
        )
        if for_update:
            query = query.with_for_update()
        return query.all()

    def _has_active_purchase_invoice(self, *, company: str, order: LyMaterialPurchaseOrder) -> bool:
        return (
            self.session.query(LyMaterialPurchaseInvoice)
            .filter(
                LyMaterialPurchaseInvoice.company == company,
                LyMaterialPurchaseInvoice.purchase_order_id == int(order.id),
                LyMaterialPurchaseInvoice.purchase_no == str(order.purchase_no),
                LyMaterialPurchaseInvoice.status != "cancelled",
            )
            .first()
            is not None
        )

    def _cancel_snapshot(
        self,
        *,
        order: LyMaterialPurchaseOrder,
        requirements: list[LyMaterialPurchaseRequirement],
    ) -> dict[str, Any]:
        return {
            "purchase_order": self._create_data(row=order, idempotency_key="").model_dump(mode="json"),
            "requirements": [self._requirement_item(row).model_dump(mode="json") for row in requirements],
        }

    def _get_requirement_by_source(
        self,
        *,
        company: str,
        source_type: str,
        source_id: str,
        bom_item_id: int | None,
        bom_color: str | None,
        bom_size: str | None,
        bom_part: str | None,
        material_item_code: str,
        warehouse: str,
    ) -> LyMaterialPurchaseRequirement | None:
        query = self.session.query(LyMaterialPurchaseRequirement).filter(
            LyMaterialPurchaseRequirement.company == company,
            LyMaterialPurchaseRequirement.source_type == source_type,
            LyMaterialPurchaseRequirement.source_id == source_id,
            LyMaterialPurchaseRequirement.material_item_code == material_item_code,
            LyMaterialPurchaseRequirement.warehouse == warehouse,
        )
        if bom_item_id is None:
            query = query.filter(LyMaterialPurchaseRequirement.bom_item_id.is_(None))
        else:
            query = query.filter(LyMaterialPurchaseRequirement.bom_item_id == bom_item_id)
        for column, value in (
            (LyMaterialPurchaseRequirement.bom_color, bom_color),
            (LyMaterialPurchaseRequirement.bom_size, bom_size),
            (LyMaterialPurchaseRequirement.bom_part, bom_part),
        ):
            query = query.filter(column == value) if value is not None else query.filter(column.is_(None))
        return query.first()

    def _group_requirements_for_order(
        self,
        *,
        requirements: list[LyMaterialPurchaseRequirement],
        group_by_material: bool,
    ) -> list[dict[str, Any]]:
        grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
        for requirement in requirements:
            if group_by_material:
                key = (
                    str(requirement.material_item_code),
                    str(requirement.uom or "米"),
                    str(requirement.warehouse),
                )
            else:
                key = (int(requirement.id),)
            bucket = grouped.setdefault(
                key,
                {
                    "material_item_code": str(requirement.material_item_code),
                    "material_name": str(requirement.material_name or requirement.material_item_code),
                    "uom": str(requirement.uom or "米"),
                    "warehouse": str(requirement.warehouse),
                    "unit_price": Decimal(str(requirement.unit_price or 0)),
                    "qty": Decimal("0"),
                    "requirements": [],
                },
            )
            bucket_unit_price = Decimal(str(bucket["unit_price"]))
            requirement_unit_price = Decimal(str(requirement.unit_price or 0))
            if (
                group_by_material
                and bucket["requirements"]
                and bucket_unit_price > Decimal("0")
                and requirement_unit_price > Decimal("0")
                and bucket_unit_price != requirement_unit_price
            ):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"{requirement.material_item_code} 合并采购单价不一致")
            if bucket_unit_price == Decimal("0") and requirement_unit_price > Decimal("0"):
                bucket["unit_price"] = requirement_unit_price
            bucket["qty"] = Decimal(str(bucket["qty"])) + Decimal(str(requirement.net_required_qty or 0))
            bucket["requirements"].append(requirement)
        return list(grouped.values())

    def _resolve_requirement_supplier(
        self,
        *,
        requirements: list[LyMaterialPurchaseRequirement],
        requested_supplier: str | None,
    ) -> str:
        suppliers = sorted(
            {
                supplier
                for supplier in (
                    self._optional_text(requirement.supplier_name)
                    for requirement in requirements
                )
                if supplier is not None
            }
        )
        if len(suppliers) > 1:
            raise BusinessException(
                code=MATERIAL_PURCHASE_CONFLICT,
                message=f"所选需求供应商不一致: {'、'.join(suppliers)}",
            )
        requirement_supplier = suppliers[0] if suppliers else None
        if (
            requested_supplier is not None
            and requirement_supplier is not None
            and requested_supplier != requirement_supplier
        ):
            raise BusinessException(
                code=MATERIAL_PURCHASE_CONFLICT,
                message=f"请求供应商 {requested_supplier} 与需求供应商 {requirement_supplier} 不一致",
            )
        return requested_supplier or requirement_supplier or "未指定供应商"

    def _normalize_receipt_rows(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            item_code = self._require_text(item.get("item_code"), f"items[{index}].item_code")
            raw_requirement_id = item.get("purchase_requirement_id", item.get("requirement_id"))
            requirement_id: int | None = None
            if raw_requirement_id not in (None, ""):
                try:
                    requirement_id = int(raw_requirement_id)
                except Exception as exc:
                    raise BusinessException(
                        code=MATERIAL_PURCHASE_CONFLICT,
                        message=f"items[{index}].purchase_requirement_id 非法",
                    ) from exc
                if requirement_id <= 0:
                    raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"items[{index}].purchase_requirement_id 必须大于 0")
            try:
                qty = Decimal(str(item.get("qty")))
            except Exception as exc:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"items[{index}].qty 非法") from exc
            if qty <= Decimal("0"):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"items[{index}].qty 必须大于 0")
            normalized.append(
                {
                    "item_code": item_code,
                    "qty": qty,
                    "uom": self._optional_text(item.get("uom")),
                    "warehouse": self._optional_text(item.get("warehouse"))
                    or self._optional_text(item.get("target_warehouse"))
                    or self._optional_text(item.get("source_warehouse")),
                    "purchase_requirement_id": requirement_id,
                }
            )
        return normalized

    def _match_receipt_line(
        self,
        *,
        lines: list[LyMaterialPurchaseOrderItem],
        item_code: str,
        warehouse: str | None,
    ) -> LyMaterialPurchaseOrderItem:
        candidates = [
            line
            for line in lines
            if item_code in {str(line.material_item_code), str(line.item_code)}
        ]
        if not candidates:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"收货物料不在采购单中: {item_code}")

        if warehouse is not None:
            exact_warehouse = [line for line in candidates if self._optional_text(line.warehouse) == warehouse]
            if exact_warehouse:
                candidates = exact_warehouse
            else:
                warehouse_unspecified = [line for line in candidates if self._optional_text(line.warehouse) is None]
                if len(warehouse_unspecified) == 1:
                    candidates = warehouse_unspecified
                else:
                    raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"收货仓库与采购明细不一致: {item_code}")
        elif any(self._optional_text(line.warehouse) is not None for line in candidates):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"采购入库必须提供采购明细仓库: {item_code}")

        if len(candidates) != 1:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"采购单中物料明细不唯一: {item_code}")
        return candidates[0]

    def _requirements_for_order_line(self, *, line: LyMaterialPurchaseOrderItem) -> list[LyMaterialPurchaseRequirement]:
        return (
            self.session.query(LyMaterialPurchaseRequirement)
            .filter(
                LyMaterialPurchaseRequirement.company == str(line.company),
                LyMaterialPurchaseRequirement.purchase_order_item_id == int(line.id),
            )
            .order_by(LyMaterialPurchaseRequirement.id.asc())
            .all()
        )

    def _receipt_context_item(
        self,
        *,
        source_index: int,
        item: dict[str, Any],
        line: LyMaterialPurchaseOrderItem,
        requirement: LyMaterialPurchaseRequirement,
        qty: Decimal,
    ) -> dict[str, Any]:
        return {
            **item,
            "_source_index": source_index,
            "qty": qty,
            "uom": self._optional_text(item.get("uom")) or self._optional_text(line.uom) or self._optional_text(requirement.uom) or "米",
            "warehouse": self._optional_text(item.get("warehouse")) or self._optional_text(requirement.warehouse) or self._optional_text(line.warehouse),
            "purchase_requirement_id": int(requirement.id),
            "sales_order_item": self._optional_text(requirement.sales_order_item),
            "bom_color": self._optional_text(requirement.bom_color),
            "bom_size": self._optional_text(requirement.bom_size),
            "bom_part": self._optional_text(requirement.bom_part),
        }

    def _ensure_undirected_receipt_is_unambiguous(
        self,
        *,
        line: LyMaterialPurchaseOrderItem,
        next_received: Decimal,
    ) -> None:
        requirements = self._requirements_for_order_line(line=line)
        if len(requirements) <= 1:
            return
        line_qty = Decimal(str(line.qty or 0))
        if next_received in {Decimal("0"), line_qty}:
            return
        raise BusinessException(
            code=MATERIAL_PURCHASE_CONFLICT,
            message=f"{line.material_item_code} 合并采购部分入库必须指定采购需求行",
        )

    def _match_receipt_requirement(
        self,
        *,
        order: LyMaterialPurchaseOrder,
        line: LyMaterialPurchaseOrderItem,
        requirement_id: int,
        item_code: str,
        warehouse: str | None,
    ) -> LyMaterialPurchaseRequirement:
        requirement = (
            self.session.query(LyMaterialPurchaseRequirement)
            .filter(
                LyMaterialPurchaseRequirement.id == requirement_id,
                LyMaterialPurchaseRequirement.company == str(order.company),
                LyMaterialPurchaseRequirement.purchase_order_id == int(order.id),
                LyMaterialPurchaseRequirement.purchase_order_item_id == int(line.id),
            )
            .first()
        )
        if requirement is None:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"采购需求行不属于当前采购单: {requirement_id}")
        if item_code not in {str(requirement.material_item_code), str(line.material_item_code), str(line.item_code)}:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"采购需求行物料与入库物料不一致: {requirement.requirement_no}")
        requirement_warehouse = self._optional_text(requirement.warehouse)
        if warehouse is not None and requirement_warehouse is not None and warehouse != requirement_warehouse:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"采购需求行仓库与入库仓库不一致: {requirement.requirement_no}")
        return requirement

    def _apply_directed_requirement_receipt_deltas(
        self,
        *,
        order: LyMaterialPurchaseOrder,
        requirement_deltas: dict[int, tuple[LyMaterialPurchaseRequirement, Decimal]],
    ) -> None:
        for requirement, delta in requirement_deltas.values():
            current_received = Decimal(str(requirement.received_qty or 0))
            purchased_qty = Decimal(str(requirement.purchased_qty or requirement.net_required_qty or 0))
            next_received = current_received + delta
            requirement.received_qty = next_received
            requirement.status = "completed" if next_received >= purchased_qty else "purchased"
            requirement.updated_by = str(order.updated_by or order.created_by)
            requirement.updated_at = datetime.now(UTC)
            self._update_production_material_from_requirement(requirement=requirement)

    def _apply_requirement_receipts(
        self,
        *,
        order: LyMaterialPurchaseOrder,
        lines: list[LyMaterialPurchaseOrderItem],
    ) -> None:
        for line in lines:
            requirements = self._requirements_for_order_line(line=line)
            if not requirements:
                continue
            remaining_received = Decimal(str(line.received_qty or 0))
            for requirement in requirements:
                purchased_qty = Decimal(str(requirement.purchased_qty or requirement.net_required_qty or 0))
                allocated = min(purchased_qty, max(remaining_received, Decimal("0")))
                requirement.received_qty = allocated
                requirement.status = "completed" if allocated >= purchased_qty else "purchased"
                requirement.updated_by = str(order.updated_by or order.created_by)
                requirement.updated_at = datetime.now(UTC)
                self._update_production_material_from_requirement(requirement=requirement)
                remaining_received -= allocated

    def _update_production_material_from_requirement(self, *, requirement: LyMaterialPurchaseRequirement) -> None:
        if requirement.plan_id is None:
            return
        query = self.session.query(LyProductionPlanMaterial).filter(
            LyProductionPlanMaterial.plan_id == int(requirement.plan_id),
            LyProductionPlanMaterial.material_item_code == str(requirement.material_item_code),
            LyProductionPlanMaterial.warehouse == str(requirement.warehouse),
        )
        if requirement.bom_item_id is None:
            query = query.filter(LyProductionPlanMaterial.bom_item_id.is_(None))
        else:
            query = query.filter(LyProductionPlanMaterial.bom_item_id == int(requirement.bom_item_id))
        for column, value in (
            (LyProductionPlanMaterial.bom_color, self._optional_text(requirement.bom_color)),
            (LyProductionPlanMaterial.bom_size, self._optional_text(requirement.bom_size)),
            (LyProductionPlanMaterial.bom_part, self._optional_text(requirement.bom_part)),
        ):
            query = query.filter(column == value) if value is not None else query.filter(column.is_(None))
        snapshot = query.first()
        if snapshot is None:
            return
        required_qty = Decimal(str(snapshot.required_qty or requirement.required_qty or 0))
        effective_available = min(
            required_qty,
            Decimal(str(requirement.available_qty or 0)) + Decimal(str(requirement.received_qty or 0)),
        )
        snapshot.available_qty = effective_available
        snapshot.shortage_qty = max(Decimal("0"), required_qty - effective_available)

    def _select_invoice_line(
        self,
        *,
        order_id: int,
        material_item_code: str | None,
    ) -> LyMaterialPurchaseOrderItem:
        lines = self._get_lines(order_id=order_id)
        normalized_material = self._optional_text(material_item_code)
        if normalized_material:
            for line in lines:
                if str(line.material_item_code) == normalized_material:
                    return line
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="开票物料不在采购单中")
        if len(lines) != 1:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="多物料采购单必须指定 material_item_code")
        return lines[0]

    def _ensure_active_master_records(
        self,
        *,
        company: str,
        entity_type: str,
        values: list[str],
        label: str,
        match_name: bool,
    ) -> None:
        normalized_values: list[str] = []
        for value in values:
            normalized = self._require_text(value, label)
            if normalized not in normalized_values:
                normalized_values.append(normalized)
        if not normalized_values:
            return
        try:
            query = self.session.query(LyMasterDataRecord.code, LyMasterDataRecord.name).filter(
                LyMasterDataRecord.entity_type == entity_type,
                LyMasterDataRecord.company == company,
                LyMasterDataRecord.status == "active",
            )
            if match_name:
                query = query.filter(
                    (LyMasterDataRecord.code.in_(normalized_values))
                    | (LyMasterDataRecord.name.in_(normalized_values))
                )
            else:
                query = query.filter(LyMasterDataRecord.code.in_(normalized_values))
            rows = query.all()
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc

        active_values = {str(row.code) for row in rows}
        if match_name:
            active_values.update(str(row.name) for row in rows)
        invalid_values = [value for value in normalized_values if value not in active_values]
        if invalid_values:
            raise BusinessException(
                code=MATERIAL_PURCHASE_CONFLICT,
                message=f"{label}不存在或已停用: {', '.join(invalid_values)}",
            )

    def _material_name_lookup(self, *, company: str, material_codes: list[str]) -> dict[str, str]:
        codes: list[str] = []
        for code in material_codes:
            normalized = str(code or "").strip()
            if normalized and normalized not in codes:
                codes.append(normalized)
        if not codes or not self._has_sqlite_tables({LyMasterDataRecord.__tablename__}):
            return {}
        try:
            rows = (
                self.session.query(LyMasterDataRecord.code, LyMasterDataRecord.name)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == company,
                    LyMasterDataRecord.code.in_(codes),
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return {str(row.code): str(row.name) for row in rows if str(row.name or "").strip()}

    def _has_sqlite_tables(self, table_names: set[str]) -> bool:
        bind = self.session.get_bind()
        if bind.dialect.name != "sqlite":
            return True
        existing_tables = set(inspect(self.session.connection()).get_table_names())
        return table_names.issubset(existing_tables)

    def _ensure_active_material_units(self, *, company: str, values: list[str]) -> None:
        normalized_values: list[str] = []
        for value in values:
            normalized = self._require_text(value, "物料单位")
            if normalized not in normalized_values:
                normalized_values.append(normalized)
        if not normalized_values:
            return
        try:
            rows = (
                self.session.query(LyMasterDataRecord)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == company,
                    LyMasterDataRecord.status == "active",
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc

        active_values: set[str] = set()
        for row in rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            material_kind = self._optional_text(payload.get("material_kind") or payload.get("kind"))
            if material_kind != "unit":
                continue
            for candidate in (
                row.code,
                row.name,
                payload.get("unit_code"),
                payload.get("unit_name"),
                payload.get("uom"),
                payload.get("base_unit"),
            ):
                text = self._optional_text(candidate)
                if text:
                    active_values.add(text)
        invalid_values = [value for value in normalized_values if value not in active_values]
        if invalid_values:
            raise BusinessException(
                code=MATERIAL_PURCHASE_CONFLICT,
                message=f"物料单位不存在或已停用: {', '.join(invalid_values)}",
            )

    def _invoiced_qty(self, *, company: str, purchase_no: str, material_item_code: str) -> Decimal:
        value = (
            self.session.query(func.coalesce(func.sum(LyMaterialPurchaseInvoice.qty), 0))
            .filter(
                LyMaterialPurchaseInvoice.company == company,
                LyMaterialPurchaseInvoice.purchase_no == purchase_no,
                LyMaterialPurchaseInvoice.material_item_code == material_item_code,
                LyMaterialPurchaseInvoice.status != "cancelled",
            )
            .scalar()
        )
        return Decimal(str(value or 0))

    def _get_purchase_invoice_by_no(self, *, company: str, purchase_invoice: str) -> LyMaterialPurchaseInvoice | None:
        return (
            self.session.query(LyMaterialPurchaseInvoice)
            .filter(
                LyMaterialPurchaseInvoice.company == company,
                LyMaterialPurchaseInvoice.purchase_invoice == purchase_invoice,
            )
            .first()
        )

    def _invoice_scope(self, invoice: LyMaterialPurchaseInvoice) -> dict[str, Any]:
        return {
            "company": str(invoice.company),
            "item_code": str(invoice.material_item_code),
            "supplier": str(invoice.supplier_name),
            "warehouse": self._optional_text(invoice.warehouse),
        }

    def _get_purchase_invoice_by_idempotency(
        self,
        *,
        company: str,
        idempotency_key: str,
    ) -> LyMaterialPurchaseInvoice | None:
        return (
            self.session.query(LyMaterialPurchaseInvoice)
            .filter(
                LyMaterialPurchaseInvoice.company == company,
                LyMaterialPurchaseInvoice.idempotency_key == idempotency_key,
            )
            .first()
        )

    def _get_purchase_invoice_by_source(self, *, company: str, source_ref: str) -> LyMaterialPurchaseInvoice | None:
        return (
            self.session.query(LyMaterialPurchaseInvoice)
            .filter(
                LyMaterialPurchaseInvoice.company == company,
                LyMaterialPurchaseInvoice.source_ref == source_ref,
            )
            .first()
        )

    def _get_purchase_payment_by_no(self, *, company: str, payment_entry: str) -> LyMaterialPurchasePayment | None:
        return (
            self.session.query(LyMaterialPurchasePayment)
            .filter(
                LyMaterialPurchasePayment.company == company,
                LyMaterialPurchasePayment.payment_entry == payment_entry,
            )
            .first()
        )

    def _get_purchase_payment_by_id(self, *, company: str | None, payment_id: int) -> LyMaterialPurchasePayment | None:
        query = self.session.query(LyMaterialPurchasePayment).filter(LyMaterialPurchasePayment.id == int(payment_id))
        if company is not None:
            query = query.filter(LyMaterialPurchasePayment.company == company)
        return query.first()

    def _get_purchase_payment_by_id_for_update(self, *, company: str | None, payment_id: int) -> LyMaterialPurchasePayment | None:
        query = self.session.query(LyMaterialPurchasePayment).filter(LyMaterialPurchasePayment.id == int(payment_id))
        if company is not None:
            query = query.filter(LyMaterialPurchasePayment.company == company)
        return query.with_for_update().first()

    def _pending_purchase_payment_amount(self, *, company: str, purchase_invoice: str) -> Decimal:
        try:
            value = (
                self.session.query(func.coalesce(func.sum(LyMaterialPurchasePayment.paid_amount), 0))
                .filter(
                    LyMaterialPurchasePayment.company == company,
                    LyMaterialPurchasePayment.purchase_invoice == purchase_invoice,
                    LyMaterialPurchasePayment.status == "pending_approval",
                )
                .scalar()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return Decimal(str(value or 0))

    def _get_purchase_payment_by_idempotency(
        self,
        *,
        company: str,
        idempotency_key: str,
    ) -> LyMaterialPurchasePayment | None:
        return (
            self.session.query(LyMaterialPurchasePayment)
            .filter(
                LyMaterialPurchasePayment.company == company,
                LyMaterialPurchasePayment.idempotency_key == idempotency_key,
            )
            .first()
        )

    def _get_purchase_payment_operation_by_idempotency(
        self,
        *,
        company: str,
        operation_type: str,
        idempotency_key: str,
    ) -> LyMaterialPurchasePaymentOperation | None:
        return (
            self.session.query(LyMaterialPurchasePaymentOperation)
            .filter(
                LyMaterialPurchasePaymentOperation.company == company,
                LyMaterialPurchasePaymentOperation.operation_type == operation_type,
                LyMaterialPurchasePaymentOperation.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )

    def _flush_purchase_payment_operation_or_resolve_replay(
        self,
        *,
        company: str,
        operation_type: str,
        idempotency_key: str,
        request_hash: str,
    ) -> LyMaterialPurchasePaymentOperation | None:
        try:
            self.session.flush()
            return None
        except IntegrityError as exc:
            self.session.rollback()
            existing = self._get_purchase_payment_operation_by_idempotency(
                company=company,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购付款作废操作冲突") from exc
            if str(existing.request_hash or "") != request_hash:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="幂等键冲突且请求内容不一致") from exc
            return existing

    def _get_purchase_payment_by_source(self, *, company: str, source_ref: str) -> LyMaterialPurchasePayment | None:
        return (
            self.session.query(LyMaterialPurchasePayment)
            .filter(
                LyMaterialPurchasePayment.company == company,
                LyMaterialPurchasePayment.source_ref == source_ref,
            )
            .first()
        )

    def _get_idempotency(self, *, company: str, idempotency_key: str) -> LyMaterialPurchaseIdempotency | None:
        return (
            self.session.query(LyMaterialPurchaseIdempotency)
            .filter(
                LyMaterialPurchaseIdempotency.company == company,
                LyMaterialPurchaseIdempotency.idempotency_key == idempotency_key,
            )
            .first()
        )

    @staticmethod
    def _request_hash(*, payload: dict[str, Any], purchase_no: str) -> str:
        normalized = json.dumps({"purchase_no": purchase_no, "payload": payload}, sort_keys=True, default=str, ensure_ascii=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _mutation_hash(payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _next_purchase_no() -> str:
        return f"PO-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _next_requirement_no(*, plan_id: int, material_item_code: str) -> str:
        digest = hashlib.sha1(f"{plan_id}:{material_item_code}:{datetime.now(UTC).isoformat()}".encode("utf-8")).hexdigest()[:8]
        return f"MR-{plan_id}-{digest}".upper()

    @staticmethod
    def _next_purchase_invoice() -> str:
        return f"PI-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _next_purchase_payment() -> str:
        return f"PP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def _positive_decimal(self, value: Any, field_name: str) -> Decimal:
        amount = Decimal(str(value))
        if amount <= Decimal("0"):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"{field_name} 必须大于 0")
        return amount

    @staticmethod
    def _normalize_scope_values(values: set[str] | None) -> set[str] | None:
        if values is None:
            return None
        return {str(value).strip() for value in values if str(value).strip()}

    def _apply_required_scope_filter(self, *, query, column, allowed_values: set[str] | None):
        normalized_values = self._normalize_scope_values(allowed_values)
        if normalized_values is None:
            return query
        if not normalized_values:
            return query.filter(false())
        return query.filter(column.in_(normalized_values))

    def _apply_optional_scope_filter(self, *, query, column, allowed_values: set[str] | None):
        normalized_values = self._normalize_scope_values(allowed_values)
        if normalized_values is None:
            return query
        empty_scope = column.is_(None) | (column == "")
        if not normalized_values:
            return query.filter(empty_scope)
        return query.filter(empty_scope | column.in_(normalized_values))

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _require_text(self, value: Any, field_name: str) -> str:
        text = self._optional_text(value)
        if text is None:
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"{field_name} 不能为空")
        return text

    @staticmethod
    def _extract_supplier_from_remark(remark: str | None) -> str | None:
        text = (remark or "").strip()
        if not text:
            return None
        import re

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
        import re

        matcher = re.search(r"(?:单价|unit_price)\s*[:：=]\s*([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if matcher is None:
            return Decimal("0")
        return Decimal(matcher.group(1))
