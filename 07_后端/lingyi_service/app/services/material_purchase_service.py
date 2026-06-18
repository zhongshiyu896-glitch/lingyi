"""Service layer for FastAPI-native material purchase orders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import MATERIAL_PURCHASE_CONFLICT
from app.core.error_codes import MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT
from app.core.error_codes import MATERIAL_PURCHASE_NOT_FOUND
from app.core.exceptions import BusinessException
from app.models.bom import LyApparelBomItem
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchasePayment
from app.models.material_purchase import LyMaterialPurchaseRequirement
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
    ) -> MaterialPurchaseOrderData:
        try:
            query = (
                self.session.query(LyMaterialPurchaseOrder, LyMaterialPurchaseOrderItem)
                .join(LyMaterialPurchaseOrderItem, LyMaterialPurchaseOrderItem.order_id == LyMaterialPurchaseOrder.id)
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

        total_qty = Decimal("0")
        total_amount = Decimal("0")
        try:
            row = LyMaterialPurchaseOrder(
                company=company,
                purchase_no=purchase_no,
                supplier_name=self._require_text(payload.supplier_name, "supplier_name"),
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
        status: str | None,
        page: int,
        page_size: int,
    ) -> MaterialPurchaseRequirementListData:
        try:
            query = self.session.query(LyMaterialPurchaseRequirement)
            normalized_company = self._optional_text(company)
            if normalized_company:
                query = query.filter(LyMaterialPurchaseRequirement.company == normalized_company)
            normalized_material = self._optional_text(material_item_code)
            if normalized_material:
                query = query.filter(LyMaterialPurchaseRequirement.material_item_code == normalized_material)
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
                    | (func.lower(LyMaterialPurchaseRequirement.material_item_code).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.material_name).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.supplier_name).like(like_value))
                    | (func.lower(LyMaterialPurchaseRequirement.purchase_no).like(like_value))
                )
            total = int(query.count())
            rows = (
                query.order_by(
                    LyMaterialPurchaseRequirement.status.asc(),
                    LyMaterialPurchaseRequirement.created_at.desc(),
                    LyMaterialPurchaseRequirement.id.desc(),
                )
                .offset(max(page - 1, 0) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=DATABASE_READ_FAILED) from exc
        return MaterialPurchaseRequirementListData(
            items=[self._requirement_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def sync_requirements_from_production_plan(self, *, plan: Any, actor: str) -> list[MaterialPurchaseRequirementListItem]:
        """Upsert material requirement pool rows from a production material check."""
        try:
            snapshots = (
                self.session.query(LyProductionPlanMaterial)
                .filter(LyProductionPlanMaterial.plan_id == int(plan.id))
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

        synced: list[LyMaterialPurchaseRequirement] = []
        now = datetime.now(UTC)
        try:
            for snapshot in snapshots:
                material_code = self._require_text(snapshot.material_item_code, "material_item_code")
                warehouse = self._require_text(snapshot.warehouse, "warehouse")
                required_qty = Decimal(str(snapshot.required_qty or 0))
                available_qty = Decimal(str(snapshot.available_qty or 0))
                net_required_qty = max(Decimal("0"), required_qty - available_qty)
                bom_item = bom_items.get(int(snapshot.bom_item_id)) if snapshot.bom_item_id is not None else None
                existing = self._get_requirement_by_source(
                    company=str(plan.company),
                    source_type="production_plan",
                    source_id=str(plan.id),
                    bom_item_id=(int(snapshot.bom_item_id) if snapshot.bom_item_id is not None else None),
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
                        bom_item_id=(int(snapshot.bom_item_id) if snapshot.bom_item_id is not None else None),
                        material_item_code=material_code,
                        warehouse=warehouse,
                        status="pending",
                        created_by=actor,
                    )
                    self.session.add(row)
                row.source_no = str(plan.plan_no)
                row.sales_order = self._optional_text(plan.sales_order)
                row.sales_order_item = self._optional_text(plan.sales_order_item)
                row.item_code = self._optional_text(plan.item_code)
                row.material_name = material_code
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
                if current_status in {"pending", "completed"}:
                    if has_completed_purchase and net_required_qty == Decimal("0"):
                        row.status = "completed"
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
                synced.append(row)
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
        for item in self._normalize_receipt_rows(items):
            line = self._match_receipt_line(
                lines=lines,
                item_code=str(item["item_code"]),
                warehouse=self._optional_text(item.get("warehouse")),
            )
            line_id = int(line.id)
            delta = Decimal(str(item["qty"])) * direction
            if line_id in line_deltas:
                line_deltas[line_id] = (line, line_deltas[line_id][1] + delta)
            else:
                line_deltas[line_id] = (line, delta)

        for line, delta in line_deltas.values():
            current_received = Decimal(str(line.received_qty or 0))
            next_received = current_received + delta
            if next_received < Decimal("0"):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"反冲收货数量超过已收数量: {line.material_item_code}")
            if next_received > Decimal(str(line.qty)):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"收货数量超过采购数量: {line.material_item_code}")
            if mutate:
                line.received_qty = next_received

        if not mutate:
            return

        total_received = sum(Decimal(str(line.received_qty or 0)) for line in lines)
        total_qty = Decimal(str(order.total_qty or 0))
        order.received_qty = total_received
        if total_received <= Decimal("0"):
            order.status = "draft"
        else:
            order.status = "received" if total_received >= total_qty else "partially_received"
        self._apply_requirement_receipts(order=order, lines=lines)
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
    ) -> MaterialPurchaseInvoiceListData:
        try:
            query = self.session.query(LyMaterialPurchaseInvoice)
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
    ) -> MaterialPurchasePaymentListData:
        try:
            query = self.session.query(LyMaterialPurchasePayment)
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
        if supplier_name is not None and supplier_name != str(invoice.supplier_name):
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="供应商与采购发票不一致")
        outstanding_before = Decimal(str(invoice.outstanding_amount or 0))
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
            invoice.paid_amount = Decimal(str(invoice.paid_amount or 0)) + paid_amount
            invoice.outstanding_amount = outstanding_after
            invoice.status = "paid" if outstanding_after == Decimal("0") else "partly_paid"
            invoice.updated_by = actor
            invoice.updated_at = datetime.now(UTC)

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
                status="submitted",
                docstatus=1,
                source_ref=source_ref,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                scenario_tag=self._optional_text(payload.scenario_tag),
                payload={
                    "operation": "create_purchase_payment",
                    "purchase_invoice": purchase_invoice,
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
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    def _payment_data(self, row: LyMaterialPurchasePayment) -> MaterialPurchasePaymentData:
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
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

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
            if Decimal(str(bucket["unit_price"])) == Decimal("0") and Decimal(str(requirement.unit_price or 0)) > Decimal("0"):
                bucket["unit_price"] = Decimal(str(requirement.unit_price or 0))
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
                    "warehouse": self._optional_text(item.get("warehouse"))
                    or self._optional_text(item.get("target_warehouse"))
                    or self._optional_text(item.get("source_warehouse")),
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

    def _apply_requirement_receipts(
        self,
        *,
        order: LyMaterialPurchaseOrder,
        lines: list[LyMaterialPurchaseOrderItem],
    ) -> None:
        for line in lines:
            requirements = (
                self.session.query(LyMaterialPurchaseRequirement)
                .filter(
                    LyMaterialPurchaseRequirement.company == str(order.company),
                    LyMaterialPurchaseRequirement.purchase_order_item_id == int(line.id),
                )
                .order_by(LyMaterialPurchaseRequirement.id.asc())
                .all()
            )
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
