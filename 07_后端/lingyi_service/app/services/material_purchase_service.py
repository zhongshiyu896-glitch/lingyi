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
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchasePayment
from app.schemas.material_purchase import MaterialPurchaseInvoiceCreateRequest
from app.schemas.material_purchase import MaterialPurchaseInvoiceData
from app.schemas.material_purchase import MaterialPurchaseInvoiceListData
from app.schemas.material_purchase import MaterialPurchaseOrderCreateData
from app.schemas.material_purchase import MaterialPurchaseOrderCreateRequest
from app.schemas.material_purchase import MaterialPurchaseOrderData
from app.schemas.material_purchase import MaterialPurchaseOrderListItem
from app.schemas.material_purchase import MaterialPurchasePaymentCreateRequest
from app.schemas.material_purchase import MaterialPurchasePaymentData
from app.schemas.material_purchase import MaterialPurchasePaymentListData


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
