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
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.schemas.material_purchase import MaterialPurchaseOrderCreateData
from app.schemas.material_purchase import MaterialPurchaseOrderCreateRequest
from app.schemas.material_purchase import MaterialPurchaseOrderData
from app.schemas.material_purchase import MaterialPurchaseOrderListItem


@dataclass(frozen=True)
class PurchaseMutationResult:
    """Mutation result with audit snapshots."""

    item: MaterialPurchaseOrderCreateData
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

    def apply_receipt(
        self,
        *,
        company: str,
        purchase_no: str,
        item_quantities: dict[str, Decimal],
    ) -> None:
        """Apply material receipt draft quantities to a purchase order."""
        order = self._get_order_by_no(company=company, purchase_no=purchase_no)
        if order is None:
            raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND, message="采购单不存在")
        if str(order.status) == "cancelled":
            raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message="采购单已取消")
        lines = self._get_lines(order_id=int(order.id))
        line_by_material = {str(line.material_item_code): line for line in lines}
        for item_code, qty in item_quantities.items():
            line = line_by_material.get(item_code)
            if line is None:
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"收货物料不在采购单中: {item_code}")
            next_received = Decimal(str(line.received_qty or 0)) + Decimal(str(qty))
            if next_received > Decimal(str(line.qty)):
                raise BusinessException(code=MATERIAL_PURCHASE_CONFLICT, message=f"收货数量超过采购数量: {item_code}")
            line.received_qty = next_received
        total_received = sum(Decimal(str(line.received_qty or 0)) for line in lines)
        order.received_qty = total_received
        order.status = "received" if total_received >= Decimal(str(order.total_qty or 0)) else "partially_received"
        self.session.flush()

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

    def _get_lines(self, *, order_id: int) -> list[LyMaterialPurchaseOrderItem]:
        return (
            self.session.query(LyMaterialPurchaseOrderItem)
            .filter(LyMaterialPurchaseOrderItem.order_id == order_id)
            .order_by(LyMaterialPurchaseOrderItem.id.asc())
            .all()
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
    def _next_purchase_no() -> str:
        return f"PO-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}"

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
