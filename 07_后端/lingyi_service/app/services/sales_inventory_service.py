"""Sales/inventory read-only aggregation service (TASK-011B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.error_codes import STYLE_MASTER_INVALID_REFERENCE
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesPaymentEntry
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.style_master import LyStyleMaster
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.schemas.sales_inventory import CustomerItem
from app.schemas.sales_inventory import CustomerReturnApplicationData
from app.schemas.sales_inventory import CustomerReturnApplicationItem
from app.schemas.sales_inventory import CustomerReturnInboundData
from app.schemas.sales_inventory import CustomerReturnInboundItem
from app.schemas.sales_inventory import DeliveryInvoiceCreateRequest
from app.schemas.sales_inventory import DeliveryInvoiceData
from app.schemas.sales_inventory import DeliveryInvoiceListData
from app.schemas.sales_inventory import DeliveryNoteItem
from app.schemas.sales_inventory import DeliveryNoteListData
from app.schemas.sales_inventory import FinishedGoodsOtherOutboundData
from app.schemas.sales_inventory import FinishedGoodsOtherOutboundItem
from app.schemas.sales_inventory import FinishedGoodsCountData
from app.schemas.sales_inventory import FinishedGoodsCountItem
from app.schemas.sales_inventory import FinishedGoodsAdjustmentData
from app.schemas.sales_inventory import FinishedGoodsAdjustmentItem
from app.schemas.sales_inventory import FinishedGoodsTransferData
from app.schemas.sales_inventory import FinishedGoodsTransferItem
from app.schemas.sales_inventory import FinishedGoodsReservedInboundData
from app.schemas.sales_inventory import FinishedGoodsReservedInboundItem
from app.schemas.sales_inventory import FinishedGoodsOtherInboundData
from app.schemas.sales_inventory import FinishedGoodsOtherInboundItem
from app.schemas.sales_inventory import FinishedGoodsShippingNoticeData
from app.schemas.sales_inventory import FinishedGoodsShippingNoticeItem
from app.schemas.sales_inventory import FinishedGoodsReportData
from app.schemas.sales_inventory import FinishedGoodsReportItem
from app.schemas.sales_inventory import InventoryMaterialRetentionReportData
from app.schemas.sales_inventory import InventoryMaterialRetentionReportItem
from app.schemas.sales_inventory import InventoryAggregationData
from app.schemas.sales_inventory import InventoryAggregationItem
from app.schemas.sales_inventory import MaterialCountData
from app.schemas.sales_inventory import MaterialCountItem
from app.schemas.sales_inventory import MaterialInventoryReportData
from app.schemas.sales_inventory import MaterialInventoryReportItem
from app.schemas.sales_inventory import MaterialTransferData
from app.schemas.sales_inventory import MaterialTransferItem
from app.schemas.sales_inventory import SalesInventoryListData
from app.schemas.sales_inventory import SalesInvoiceItem
from app.schemas.sales_inventory import SupplierItem
from app.schemas.sales_inventory import SalesInvoiceListData
from app.schemas.sales_inventory import SalesPaymentEntryCreateRequest
from app.schemas.sales_inventory import SalesPaymentEntryData
from app.schemas.sales_inventory import SalesPaymentEntryListData
from app.schemas.sales_inventory import ReferenceDraftCreateRequest
from app.schemas.sales_inventory import ReferenceDraftData
from app.schemas.sales_inventory import ReferenceDraftDeactivateRequest
from app.schemas.sales_inventory import SalesOrderDetailData
from app.schemas.sales_inventory import SalesOrderDraftCancelRequest
from app.schemas.sales_inventory import SalesOrderDraftCreateRequest
from app.schemas.sales_inventory import SalesOrderDraftData
from app.schemas.sales_inventory import SalesOrderDraftLineItemData
from app.schemas.sales_inventory import SalesOrderFulfillmentData
from app.schemas.sales_inventory import SalesOrderFulfillmentItem
from app.schemas.sales_inventory import SalesOrderLineItem
from app.schemas.sales_inventory import SalesOrderListItem
from app.schemas.sales_inventory import SemiFinishedInventoryData
from app.schemas.sales_inventory import SemiFinishedInventoryItem
from app.schemas.sales_inventory import StockLedgerData
from app.schemas.sales_inventory import StockLedgerItem
from app.schemas.sales_inventory import StockSummaryData
from app.schemas.sales_inventory import StockSummaryItem
from app.schemas.sales_inventory import WarehouseItem
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter


class SalesInventoryServiceError(Exception):
    """Domain error for local sales-order write closure APIs."""

    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = int(status_code)
        self.code = code
        self.message = message


class SalesInventoryService:
    """Build API DTOs from ERPNext read-only adapter facts."""

    BIN_FIELDS = [
        "item_code",
        "warehouse",
        "actual_qty",
        "ordered_qty",
        "indented_qty",
        "safety_stock",
        "reorder_level",
    ]

    def __init__(
        self,
        adapter: ERPNextSalesInventoryAdapter | None = None,
        session: Session | None = None,
    ):
        self.adapter = adapter
        self.session = session

    def list_sales_orders(
        self,
        *,
        order_no: str | None,
        keyword: str | None,
        company: str | None,
        customer: str | None,
        item_code: str | None,
        item_name: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[SalesOrderListItem]:
        normalized_keyword = self._text(keyword)
        normalized_order_no = self._text(order_no)
        normalized_item_name = self._text(item_name)
        adapter_item_name = normalized_item_name or normalized_keyword
        rows, total = self.adapter.list_sales_orders(
            company=company,
            customer=customer,
            item_code=item_code,
            item_name=adapter_item_name,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        filtered_rows = rows
        if normalized_order_no:
            needle = normalized_order_no.lower()
            filtered_rows = [
                row
                for row in filtered_rows
                if needle in str(row.get("name") or "").lower()
            ]
        if normalized_keyword:
            keyword_needle = normalized_keyword.lower()
            filtered_rows = [
                row
                for row in filtered_rows
                if keyword_needle in " ".join(
                    (
                        str(row.get("name") or ""),
                        str(row.get("customer") or ""),
                        str(row.get("company") or ""),
                        str(row.get("status") or ""),
                    )
                ).lower()
            ]
        return SalesInventoryListData[SalesOrderListItem](
            items=[self._sales_order_list_item(row) for row in filtered_rows],
            total=min(total, len(filtered_rows)),
            page=page,
            page_size=page_size,
        )

    def get_sales_order(self, *, name: str) -> SalesOrderDetailData:
        row = self.adapter.get_sales_order(name=name)
        return SalesOrderDetailData(
            name=str(row.get("name") or name),
            company=str(row.get("company") or ""),
            customer=self._text(row.get("customer")),
            transaction_date=row.get("transaction_date"),
            delivery_date=row.get("delivery_date"),
            status=self._text(row.get("status")),
            docstatus=int(row.get("docstatus")),
            grand_total=self._decimal_or_none(row.get("grand_total")),
            currency=self._text(row.get("currency")),
            items=[self._sales_order_line_item(item) for item in self._list_or_empty(row.get("items"))],
        )

    def create_sales_order_draft(
        self,
        *,
        payload: SalesOrderDraftCreateRequest,
        current_user: str,
        scenario_tag: str,
    ) -> SalesOrderDraftData:
        session = self._require_session()

        company = self._require_text(payload.company, "company")
        operation = self._text(payload.operation) or "create_draft"
        if operation not in {"create", "create_draft"}:
            raise SalesInventoryServiceError(409, "SALES_ORDER_IDEMPOTENCY_CONFLICT", "operation 非法")
        sales_order_no = self._text(payload.sales_order_no) or self._next_sales_order_no(company=company)
        source_order_ref = self._text(payload.source_order_ref) or sales_order_no
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        customer = self._text(payload.customer)
        currency = self._text(payload.currency) or "CNY"
        transaction_date = payload.transaction_date
        delivery_date = payload.delivery_date

        line_rows: list[dict[str, Any]] = []
        grand_total = Decimal("0")
        for index, line in enumerate(payload.items, start=1):
            item_code = self._require_text(line.item_code, f"items[{index}].item_code")
            style = self._resolve_enabled_style(company=company, style_no=item_code)
            qty = self._positive_decimal(line.qty, f"items[{index}].qty")
            rate = self._decimal_or_none(line.rate)
            amount = qty * rate if rate is not None else None
            if amount is not None:
                grand_total += amount
            line_rows.append(
                {
                    "item_code": str(style.ys_style_no),
                    "item_name": str(style.ys_style_name_cn),
                    "color": self._text(line.color),
                    "size": self._text(line.size),
                    "qty": qty,
                    "rate": rate,
                    "amount": amount,
                    "uom": self._require_text(line.uom, f"items[{index}].uom"),
                    "warehouse": self._text(line.warehouse),
                    "delivery_date": line.delivery_date,
                }
            )

        request_hash = self._native_sales_order_request_hash(
            {
                "company": company,
                "sales_order_no": sales_order_no,
                "source_order_ref": source_order_ref,
                "customer": customer,
                "currency": currency,
                "transaction_date": transaction_date.isoformat() if transaction_date else None,
                "delivery_date": delivery_date.isoformat() if delivery_date else None,
                "items": [
                    {
                        "item_code": row["item_code"],
                        "item_name": row["item_name"],
                        "color": row["color"],
                        "size": row["size"],
                        "qty": str(row["qty"]),
                        "rate": str(row["rate"]) if row["rate"] is not None else None,
                        "uom": row["uom"],
                        "warehouse": row["warehouse"],
                        "delivery_date": row["delivery_date"].isoformat() if row["delivery_date"] else None,
                    }
                    for row in line_rows
                ],
            }
        )

        existing_idem = (
            session.query(LySalesOrderIdempotency)
            .filter(
                LySalesOrderIdempotency.company == company,
                LySalesOrderIdempotency.operation == "create_draft",
                LySalesOrderIdempotency.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_idem is not None:
            if str(existing_idem.request_hash) != request_hash:
                raise SalesInventoryServiceError(409, "SALES_ORDER_IDEMPOTENCY_CONFLICT", "幂等键冲突且请求内容不一致")
            existing_order = session.query(LySalesOrder).filter(LySalesOrder.id == int(existing_idem.sales_order_id)).first()
            if existing_order is None:
                raise SalesInventoryServiceError(404, "SALES_ORDER_DRAFT_NOT_FOUND", "草稿不存在")
            return self._build_native_sales_order_draft_data(existing_order)

        existing_by_no = (
            session.query(LySalesOrder)
            .filter(
                LySalesOrder.company == company,
                LySalesOrder.sales_order_no == sales_order_no,
            )
            .first()
        )
        if existing_by_no is not None:
            raise SalesInventoryServiceError(409, "SALES_ORDER_IDEMPOTENCY_CONFLICT", "销售订单号已存在")

        row = LySalesOrder(
            company=company,
            sales_order_no=sales_order_no,
            source_order_ref=source_order_ref,
            customer=customer,
            status="draft",
            docstatus=0,
            transaction_date=transaction_date,
            delivery_date=delivery_date,
            currency=currency,
            grand_total=grand_total,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            scenario_tag=self._text(scenario_tag),
            payload={
                "scenario_tag": self._text(scenario_tag),
                "source_order_ref": source_order_ref,
            },
            created_by=current_user,
        )
        session.add(row)
        session.flush()

        for index, item in enumerate(line_rows, start=1):
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(row.id),
                    company=company,
                    line_no=index,
                    sales_order_item=f"{sales_order_no}-{index:03d}",
                    item_code=item["item_code"],
                    item_name=item["item_name"],
                    color=item["color"],
                    size=item["size"],
                    ys_material_calc_state="待算料",
                    qty=item["qty"],
                    planned_qty=Decimal("0"),
                    delivered_qty=Decimal("0"),
                    rate=item["rate"],
                    amount=item["amount"],
                    uom=item["uom"],
                    warehouse=item["warehouse"],
                    delivery_date=item["delivery_date"] or delivery_date,
                )
            )
        session.flush()

        response = self._build_native_sales_order_draft_data(row)
        session.add(
            LySalesOrderIdempotency(
                company=company,
                operation="create_draft",
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                sales_order_id=int(row.id),
                response_json=self._sales_order_draft_response_json(response),
                created_by=current_user,
            )
        )
        session.flush()
        return response

    def create_sales_order_draft_legacy_warehouse(
        self,
        *,
        payload: SalesOrderDraftCreateRequest,
        current_user: str,
        scenario_tag: str,
    ) -> SalesOrderDraftData:
        """Legacy TASK-011B warehouse-draft implementation kept for old probes."""
        session = self._require_session()

        company = self._require_text(payload.company, "company")
        sales_order_no = self._require_text(payload.sales_order_no, "sales_order_no")
        source_order_ref = self._require_text(payload.source_order_ref, "source_order_ref")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        customer = self._text(payload.customer)
        currency = self._text(payload.currency) or "CNY"
        transaction_date = payload.transaction_date
        delivery_date = payload.delivery_date

        line_rows: list[dict[str, Any]] = []
        grand_total = Decimal("0")
        for index, line in enumerate(payload.items, start=1):
            item_code = self._require_text(line.item_code, f"items[{index}].item_code")
            qty = self._positive_decimal(line.qty, f"items[{index}].qty")
            rate = self._decimal_or_none(line.rate)
            amount = qty * rate if rate is not None else None
            if amount is not None:
                grand_total += amount
            line_rows.append(
                {
                    "item_code": item_code,
                    "qty": qty,
                    "rate": rate,
                    "amount": amount,
                    "uom": self._require_text(line.uom, f"items[{index}].uom"),
                    "warehouse": self._text(line.warehouse),
                }
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
            return self._build_sales_order_draft_data(existing_by_idempotency)

        existing_by_source = (
            session.query(LyWarehouseStockEntryDraft)
            .filter(
                LyWarehouseStockEntryDraft.company == company,
                LyWarehouseStockEntryDraft.source_type == self._LOCAL_SALES_ORDER_SOURCE_TYPE,
                LyWarehouseStockEntryDraft.source_id == source_order_ref,
                LyWarehouseStockEntryDraft.status != "cancelled",
            )
            .first()
        )
        if existing_by_source is not None:
            return self._build_sales_order_draft_data(existing_by_source)

        now = datetime.now(timezone.utc)
        event_key = self._build_sales_order_event_key(
            company=company,
            sales_order_no=sales_order_no,
            source_order_ref=source_order_ref,
            idempotency_key=idempotency_key,
        )

        draft = LyWarehouseStockEntryDraft(
            company=company,
            purpose="Material Issue",
            source_type=self._LOCAL_SALES_ORDER_SOURCE_TYPE,
            source_id=source_order_ref,
            source_warehouse=None,
            target_warehouse=None,
            status="pending_outbox",
            created_by=current_user,
            created_at=now,
            cancelled_by=None,
            cancelled_at=None,
            cancel_reason=None,
            idempotency_key=idempotency_key,
            event_key=event_key,
        )
        session.add(draft)
        session.flush()

        for row in line_rows:
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=draft.id,
                    company=company,
                    item_code=row["item_code"],
                    qty=row["qty"],
                    uom=row["uom"],
                    batch_no=None,
                    serial_no=None,
                    source_warehouse=row["warehouse"],
                    target_warehouse=None,
                )
            )

        outbox_payload = {
            "scenario_tag": scenario_tag,
            "sales_order_no": sales_order_no,
            "source_order_ref": source_order_ref,
            "idempotency_key": idempotency_key,
            "company": company,
            "customer": customer,
            "currency": currency,
            "transaction_date": transaction_date.isoformat() if transaction_date else None,
            "delivery_date": delivery_date.isoformat() if delivery_date else None,
            "grand_total": str(grand_total),
            "items": [
                {
                    "item_code": row["item_code"],
                    "qty": str(row["qty"]),
                    "rate": (str(row["rate"]) if row["rate"] is not None else None),
                    "amount": (str(row["amount"]) if row["amount"] is not None else None),
                    "uom": row["uom"],
                    "warehouse": row["warehouse"],
                }
                for row in line_rows
            ],
        }
        session.add(
            LyWarehouseStockEntryOutboxEvent(
                draft_id=draft.id,
                event_type="sales_order_write_sync",
                event_key=event_key,
                payload=outbox_payload,
                status="in_pending",
                retry_count=0,
                external_ref=None,
                error_message=None,
                created_at=now,
                processed_at=None,
            )
        )
        session.flush()
        return self._build_sales_order_draft_data(draft)

    def cancel_sales_order_draft(
        self,
        *,
        draft_id: int,
        reason: str,
        cancelled_by: str,
    ) -> SalesOrderDraftData:
        session = self._require_session()
        native_order = session.query(LySalesOrder).filter(LySalesOrder.id == int(draft_id)).first()
        if native_order is not None:
            if str(native_order.status) == "cancelled":
                raise SalesInventoryServiceError(409, "SALES_ORDER_DRAFT_ALREADY_CANCELLED", "草稿已取消")
            if str(native_order.status) not in {"draft", "planned"}:
                raise SalesInventoryServiceError(409, "SALES_ORDER_DRAFT_INVALID_STATUS", "当前状态不允许取消")
            now = datetime.now(timezone.utc)
            cancel_reason = self._require_text(reason, "reason")
            request_hash = self._native_sales_order_request_hash(
                {
                    "draft_id": int(native_order.id),
                    "company": str(native_order.company),
                    "sales_order_no": str(native_order.sales_order_no),
                    "reason": cancel_reason,
                }
            )
            idem_key = f"cancel:{native_order.id}:{cancel_reason}"
            existing_idem = (
                session.query(LySalesOrderIdempotency)
                .filter(
                    LySalesOrderIdempotency.company == str(native_order.company),
                    LySalesOrderIdempotency.operation == "cancel_draft",
                    LySalesOrderIdempotency.idempotency_key == idem_key,
                )
                .first()
            )
            if existing_idem is not None and str(existing_idem.request_hash) != request_hash:
                raise SalesInventoryServiceError(409, "SALES_ORDER_IDEMPOTENCY_CONFLICT", "幂等键冲突且请求内容不一致")
            native_order.status = "cancelled"
            native_order.docstatus = 2
            native_order.cancelled_by = cancelled_by
            native_order.cancelled_at = now
            native_order.cancel_reason = cancel_reason
            native_order.updated_by = cancelled_by
            response = self._build_native_sales_order_draft_data(native_order)
            if existing_idem is None:
                session.add(
                    LySalesOrderIdempotency(
                        company=str(native_order.company),
                        operation="cancel_draft",
                        idempotency_key=idem_key,
                        request_hash=request_hash,
                        sales_order_id=int(native_order.id),
                        response_json=self._sales_order_draft_response_json(response),
                        created_by=cancelled_by,
                    )
                )
            session.flush()
            return response

        draft = self._find_sales_order_draft(draft_id=draft_id)
        if draft is None:
            raise SalesInventoryServiceError(404, "SALES_ORDER_DRAFT_NOT_FOUND", "草稿不存在")
        status = str(draft.status)
        if status == "cancelled":
            raise SalesInventoryServiceError(409, "SALES_ORDER_DRAFT_ALREADY_CANCELLED", "草稿已取消")
        if status not in {"draft", "pending_outbox"}:
            raise SalesInventoryServiceError(409, "SALES_ORDER_DRAFT_INVALID_STATUS", "当前状态不允许取消")

        now = datetime.now(timezone.utc)
        draft.status = "cancelled"
        draft.cancelled_by = cancelled_by
        draft.cancelled_at = now
        draft.cancel_reason = self._require_text(reason, "reason")

        for event in self._list_outbox_events_for_draft(draft_id=draft_id):
            if str(event.status) in {"in_pending", "processing", "failed"}:
                event.status = "cancelled"
                event.processed_at = now
        session.flush()
        return self._build_sales_order_draft_data(draft)

    def get_sales_order_draft_gate_carriers(self, *, draft_id: int) -> dict[str, str]:
        native = self._require_session().query(LySalesOrder).filter(LySalesOrder.id == int(draft_id)).first()
        if native is not None:
            return {
                "idempotency_key": str(native.idempotency_key),
                "source_order_ref": self._text(native.source_order_ref) or str(native.sales_order_no),
                "sales_order_no": str(native.sales_order_no),
                "company": str(native.company),
                "scenario_tag": self._text(native.scenario_tag) or "",
            }
        draft = self._find_sales_order_draft(draft_id=draft_id)
        if draft is None:
            raise SalesInventoryServiceError(404, "SALES_ORDER_DRAFT_NOT_FOUND", "草稿不存在")
        payload = self._sales_order_payload_for_draft(draft_id=draft_id)
        sales_order_no = self._require_text(payload.get("sales_order_no"), "sales_order_no")
        scenario_tag = self._require_text(payload.get("scenario_tag"), "scenario_tag")
        return {
            "idempotency_key": str(draft.idempotency_key),
            "source_order_ref": str(draft.source_id),
            "sales_order_no": sales_order_no,
            "company": str(draft.company),
            "scenario_tag": scenario_tag,
        }

    def list_local_sales_orders(
        self,
        *,
        order_no: str | None,
        keyword: str | None,
        company: str | None,
        customer: str | None,
        item_code: str | None,
        item_name: str | None,
        from_date: date | None,
        to_date: date | None,
    ) -> list[SalesOrderListItem]:
        session = self._require_session()
        query = session.query(LyWarehouseStockEntryDraft).filter(
            LyWarehouseStockEntryDraft.source_type == self._LOCAL_SALES_ORDER_SOURCE_TYPE
        )
        if company:
            query = query.filter(LyWarehouseStockEntryDraft.company == company)
        try:
            rows = query.order_by(LyWarehouseStockEntryDraft.id.desc()).all()
        except Exception as exc:
            if self._is_missing_legacy_sales_order_table(exc):
                rows = []
            else:
                raise

        normalized_order_no = self._text(order_no)
        normalized_keyword = self._text(keyword)
        normalized_customer = self._text(customer)
        normalized_item_code = self._text(item_code)
        normalized_item_name = self._text(item_name)

        items: list[SalesOrderListItem] = []
        try:
            native_query = session.query(LySalesOrder)
            if company:
                native_query = native_query.filter(LySalesOrder.company == company)
            native_rows = native_query.order_by(LySalesOrder.id.desc()).all()
        except Exception as exc:
            if self._is_missing_native_sales_order_table(exc):
                native_rows = []
            else:
                raise
        for order in native_rows:
            if normalized_order_no and normalized_order_no.lower() not in str(order.sales_order_no).lower():
                continue
            if normalized_customer and self._text(order.customer) != normalized_customer:
                continue
            if normalized_keyword:
                keyword_haystack = " ".join(
                    [
                        str(order.sales_order_no),
                        self._text(order.customer) or "",
                        str(order.company),
                        str(order.status),
                    ]
                )
                if not self._contains_like(keyword_haystack, normalized_keyword):
                    continue
            if from_date is not None and (order.transaction_date is None or order.transaction_date < from_date):
                continue
            if to_date is not None and (order.transaction_date is None or order.transaction_date > to_date):
                continue
            order_items = self._native_sales_order_items(order_id=int(order.id))
            if normalized_item_code and not any(item.item_code == normalized_item_code for item in order_items):
                continue
            if normalized_item_name and not any(
                self._contains_like(item.item_name or item.item_code, normalized_item_name) for item in order_items
            ):
                continue
            items.append(self._build_native_sales_order_list_item(order))

        for draft in rows:
            payload = self._sales_order_payload_for_draft(draft_id=int(draft.id))
            sales_order_no = self._text(payload.get("sales_order_no")) or str(draft.source_id)
            if any(existing.name == sales_order_no for existing in items):
                continue
            if normalized_order_no and normalized_order_no.lower() not in sales_order_no.lower():
                continue
            payload_customer = self._text(payload.get("customer"))
            if normalized_customer and payload_customer != normalized_customer:
                continue
            if normalized_keyword:
                keyword_haystack = " ".join(
                    [
                        sales_order_no,
                        payload_customer or "",
                        str(draft.company),
                    ]
                )
                if not self._contains_like(keyword_haystack, normalized_keyword):
                    continue
            tx_date = self._parse_optional_iso_date(self._text(payload.get("transaction_date")))
            if from_date is not None and (tx_date is None or tx_date < from_date):
                continue
            if to_date is not None and (tx_date is None or tx_date > to_date):
                continue

            line_items = self._sales_order_draft_items(draft_id=int(draft.id))
            if normalized_item_code and not any(item.item_code == normalized_item_code for item in line_items):
                continue
            if normalized_item_name and not any(
                self._contains_like(item.item_code, normalized_item_name) for item in line_items
            ):
                continue

            items.append(
                SalesOrderListItem(
                    name=sales_order_no,
                    company=str(draft.company),
                    customer=payload_customer,
                    transaction_date=tx_date,
                    delivery_date=self._parse_optional_iso_date(self._text(payload.get("delivery_date"))),
                    status=("Cancelled" if str(draft.status) == "cancelled" else "Draft"),
                    docstatus=(2 if str(draft.status) == "cancelled" else 0),
                    grand_total=self._decimal_or_none(payload.get("grand_total")),
                    currency=self._text(payload.get("currency")) or "CNY",
                )
            )
        return items

    def get_local_sales_order(self, *, name: str) -> SalesOrderDetailData | None:
        session = self._require_session()
        try:
            native_order = (
                session.query(LySalesOrder)
                .filter(
                    (LySalesOrder.sales_order_no == name) | (LySalesOrder.source_order_ref == name),
                )
                .order_by(LySalesOrder.id.desc())
                .first()
            )
        except Exception as exc:
            if self._is_missing_native_sales_order_table(exc):
                native_order = None
            else:
                raise
        if native_order is not None:
            return self._build_native_sales_order_detail(native_order)

        try:
            drafts = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == self._LOCAL_SALES_ORDER_SOURCE_TYPE)
                .order_by(LyWarehouseStockEntryDraft.id.desc())
                .all()
            )
        except Exception as exc:
            if self._is_missing_legacy_sales_order_table(exc):
                return None
            raise
        selected: LyWarehouseStockEntryDraft | None = None
        selected_payload: dict[str, Any] | None = None
        for draft in drafts:
            payload = self._sales_order_payload_for_draft(draft_id=int(draft.id))
            sales_order_no = self._text(payload.get("sales_order_no")) or str(draft.source_id)
            if sales_order_no == name or str(draft.source_id) == name:
                selected = draft
                selected_payload = payload
                break
        if selected is None or selected_payload is None:
            return None

        line_items = self._sales_order_draft_items(draft_id=int(selected.id))
        return SalesOrderDetailData(
            name=self._text(selected_payload.get("sales_order_no")) or str(selected.source_id),
            company=str(selected.company),
            customer=self._text(selected_payload.get("customer")),
            transaction_date=self._parse_optional_iso_date(self._text(selected_payload.get("transaction_date"))),
            delivery_date=self._parse_optional_iso_date(self._text(selected_payload.get("delivery_date"))),
            status=("Cancelled" if str(selected.status) == "cancelled" else "Draft"),
            docstatus=(2 if str(selected.status) == "cancelled" else 0),
            grand_total=self._decimal_or_none(selected_payload.get("grand_total")),
            currency=self._text(selected_payload.get("currency")) or "CNY",
            items=[
                SalesOrderLineItem(
                    name=f"LOCAL-SO-ITEM-{item.id}",
                    item_code=item.item_code,
                    item_name=item.item_code,
                    qty=item.qty,
                    delivered_qty=None,
                    rate=item.rate,
                    amount=item.amount,
                    warehouse=item.warehouse,
                    delivery_date=self._parse_optional_iso_date(self._text(selected_payload.get("delivery_date"))),
                )
                for item in line_items
            ],
        )

    def create_delivery_invoice(
        self,
        *,
        payload: DeliveryInvoiceCreateRequest,
        current_user: str,
        scenario_tag: str | None,
    ) -> DeliveryInvoiceData:
        session = self._require_session()
        company = self._require_text(payload.company, "company")
        sales_order = self._require_text(payload.sales_order, "sales_order")
        item_code = self._require_text(payload.item_code, "item_code")
        warehouse = self._require_text(payload.warehouse, "warehouse")
        delivered_qty = self._positive_decimal(payload.delivered_qty, "delivered_qty")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        operation = self._text(payload.operation) or "create_delivery_invoice"
        if operation != "create_delivery_invoice":
            raise SalesInventoryServiceError(409, "SALES_DELIVERY_INVOICE_CONFLICT", "operation 非法")
        posting_date = payload.posting_date
        rate = self._decimal_or_none(payload.rate)
        grand_total = self._decimal_or_none(payload.grand_total)
        if grand_total is None:
            grand_total = delivered_qty * rate if rate is not None else Decimal("0")
        if grand_total < Decimal("0"):
            raise SalesInventoryServiceError(400, "SALES_DELIVERY_INVOICE_INVALID_PAYLOAD", "grand_total 不得为负数")
        delivery_note = self._text(payload.delivery_note) or self._next_delivery_note(company=company, posting_date=posting_date)
        sales_invoice = self._text(payload.sales_invoice) or self._next_sales_invoice(company=company, posting_date=posting_date)
        source_ref = self._text(payload.source_ref) or f"{delivery_note}:{sales_invoice}"
        customer = self._text(payload.customer)
        item_name = self._text(payload.item_name)
        uom = self._require_text(payload.uom, "uom")

        request_hash = self._delivery_invoice_request_hash(
            {
                "company": company,
                "delivery_note": delivery_note,
                "sales_invoice": sales_invoice,
                "sales_order": sales_order,
                "customer": customer,
                "item_code": item_code,
                "item_name": item_name,
                "warehouse": warehouse,
                "delivered_qty": str(delivered_qty),
                "uom": uom,
                "rate": str(rate) if rate is not None else None,
                "grand_total": str(grand_total),
                "posting_date": posting_date.isoformat(),
                "due_date": payload.due_date.isoformat() if payload.due_date else None,
                "source_ref": source_ref,
            }
        )

        existing_idem = (
            session.query(LyDeliveryInvoice)
            .filter(
                LyDeliveryInvoice.company == company,
                LyDeliveryInvoice.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_idem is not None:
            if str(existing_idem.request_hash) != request_hash:
                raise SalesInventoryServiceError(409, "SALES_DELIVERY_INVOICE_CONFLICT", "幂等键冲突且请求内容不一致")
            return self._build_delivery_invoice_data(existing_idem)

        existing_source = (
            session.query(LyDeliveryInvoice)
            .filter(
                LyDeliveryInvoice.company == company,
                LyDeliveryInvoice.source_ref == source_ref,
            )
            .first()
        )
        if existing_source is not None:
            if str(existing_source.request_hash) != request_hash:
                raise SalesInventoryServiceError(409, "SALES_DELIVERY_INVOICE_CONFLICT", "source_ref 已存在且请求内容不一致")
            return self._build_delivery_invoice_data(existing_source)

        for field_name, value in {"delivery_note": delivery_note, "sales_invoice": sales_invoice}.items():
            existing_doc = (
                session.query(LyDeliveryInvoice)
                .filter(
                    LyDeliveryInvoice.company == company,
                    getattr(LyDeliveryInvoice, field_name) == value,
                )
                .first()
            )
            if existing_doc is not None:
                raise SalesInventoryServiceError(409, "SALES_DELIVERY_INVOICE_CONFLICT", f"{field_name} 已存在")

        self._assert_local_stock_available(
            company=company,
            item_code=item_code,
            warehouse=warehouse,
            required_qty=delivered_qty,
        )
        self._increase_native_sales_order_delivered_qty(
            company=company,
            sales_order=sales_order,
            item_code=item_code,
            warehouse=warehouse,
            delivered_qty=delivered_qty,
        )

        stock_draft = self._create_delivery_stock_issue(
            company=company,
            delivery_note=delivery_note,
            sales_invoice=sales_invoice,
            sales_order=sales_order,
            item_code=item_code,
            delivered_qty=delivered_qty,
            uom=uom,
            warehouse=warehouse,
            posting_date=posting_date,
            idempotency_key=idempotency_key,
            current_user=current_user,
        )
        row = LyDeliveryInvoice(
            company=company,
            delivery_note=delivery_note,
            sales_invoice=sales_invoice,
            sales_order=sales_order,
            customer=customer,
            item_code=item_code,
            item_name=item_name,
            warehouse=warehouse,
            delivered_qty=delivered_qty,
            uom=uom,
            rate=rate,
            grand_total=grand_total,
            paid_amount=Decimal("0"),
            outstanding_amount=grand_total,
            posting_date=posting_date,
            due_date=payload.due_date,
            status="submitted",
            docstatus=1,
            source_ref=source_ref,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            scenario_tag=self._text(scenario_tag) or self._text(payload.scenario_tag),
            warehouse_draft_id=int(stock_draft.id),
            payload={
                "operation": operation,
                "scenario_tag": self._text(scenario_tag) or self._text(payload.scenario_tag),
                "stock_source_id": delivery_note,
            },
            created_by=current_user,
        )
        session.add(row)
        session.flush()
        return self._build_delivery_invoice_data(row)

    def list_local_delivery_invoices(
        self,
        *,
        company: str | None,
        sales_order: str | None,
        customer: str | None,
        item_code: str | None,
        warehouse: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> DeliveryInvoiceListData:
        rows = self._query_local_delivery_invoices(
            company=company,
            sales_order=sales_order,
            customer=customer,
            item_code=item_code,
            warehouse=warehouse,
            status=status,
            keyword=keyword,
        )
        total = len(rows)
        start = max((page - 1) * page_size, 0)
        return DeliveryInvoiceListData(
            items=[self._build_delivery_invoice_data(row) for row in rows[start : start + page_size]],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_local_delivery_notes(
        self,
        *,
        company: str | None,
        sales_order: str | None,
        customer: str | None,
        item_code: str | None,
        warehouse: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> DeliveryNoteListData:
        rows = self._query_local_delivery_invoices(
            company=company,
            sales_order=sales_order,
            customer=customer,
            item_code=item_code,
            warehouse=warehouse,
            status=status,
            keyword=None,
        )
        total = len(rows)
        start = max((page - 1) * page_size, 0)
        return DeliveryNoteListData(
            items=[
                DeliveryNoteItem(
                    delivery_note=str(row.delivery_note),
                    company=str(row.company),
                    sales_order=str(row.sales_order),
                    customer=self._text(row.customer) or "",
                    item_code=str(row.item_code),
                    warehouse=str(row.warehouse),
                    delivered_qty=Decimal(str(row.delivered_qty)),
                    posting_date=row.posting_date,
                    status=str(row.status),
                )
                for row in rows[start : start + page_size]
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_local_sales_invoices(
        self,
        *,
        company: str | None,
        sales_order: str | None,
        customer: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> SalesInvoiceListData:
        rows = self._query_local_delivery_invoices(
            company=company,
            sales_order=sales_order,
            customer=customer,
            item_code=None,
            warehouse=None,
            status=status,
            keyword=None,
        )
        total = len(rows)
        start = max((page - 1) * page_size, 0)
        return SalesInvoiceListData(
            items=[
                SalesInvoiceItem(
                    sales_invoice=str(row.sales_invoice),
                    company=str(row.company),
                    sales_order=str(row.sales_order),
                    customer=self._text(row.customer) or "",
                    grand_total=Decimal(str(row.grand_total or 0)),
                    paid_amount=Decimal(str(row.paid_amount or 0)),
                    outstanding_amount=Decimal(str(row.outstanding_amount or 0)),
                    posting_date=row.posting_date,
                    status=str(row.status),
                )
                for row in rows[start : start + page_size]
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_payment_entry(
        self,
        *,
        payload: SalesPaymentEntryCreateRequest,
        current_user: str,
        scenario_tag: str | None,
    ) -> SalesPaymentEntryData:
        session = self._require_session()
        company = self._text(payload.company)
        sales_invoice = self._text(payload.sales_invoice)
        idempotency_key = self._text(payload.idempotency_key)
        operation = self._text(payload.operation) or "create_payment_entry"
        if company is None:
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "company 不能为空")
        if sales_invoice is None:
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "sales_invoice 不能为空")
        if idempotency_key is None:
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "idempotency_key 不能为空")
        if operation != "create_payment_entry":
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "operation 非法")
        paid_amount = self._decimal_or_zero(payload.paid_amount)
        if paid_amount <= Decimal("0"):
            raise SalesInventoryServiceError(400, "SALES_PAYMENT_ENTRY_INVALID_PAYLOAD", "paid_amount 必须大于 0")

        requested_payment_entry = self._text(payload.payment_entry)
        customer = self._text(payload.customer)
        mode_of_payment = self._text(payload.mode_of_payment) or "Bank Transfer"
        reference_no = self._text(payload.reference_no)
        source_ref = self._text(payload.source_ref) or f"{sales_invoice}:{idempotency_key}"
        request_hash = self._sales_payment_entry_request_hash(
            {
                "company": company,
                "sales_invoice": sales_invoice,
                "customer": customer,
                "posting_date": payload.posting_date.isoformat(),
                "paid_amount": str(paid_amount),
                "mode_of_payment": mode_of_payment,
                "reference_no": reference_no,
                "reference_date": payload.reference_date.isoformat() if payload.reference_date else None,
                "requested_payment_entry": requested_payment_entry,
                "source_ref": source_ref,
            }
        )

        existing_idem = (
            session.query(LySalesPaymentEntry)
            .filter(
                LySalesPaymentEntry.company == company,
                LySalesPaymentEntry.idempotency_key == idempotency_key,
            )
            .first()
        )
        if existing_idem is not None:
            if str(existing_idem.request_hash) != request_hash:
                raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "幂等键冲突且请求内容不一致")
            return self._build_sales_payment_entry_data(existing_idem)

        existing_source = (
            session.query(LySalesPaymentEntry)
            .filter(
                LySalesPaymentEntry.company == company,
                LySalesPaymentEntry.source_ref == source_ref,
            )
            .first()
        )
        if existing_source is not None:
            if str(existing_source.request_hash) != request_hash:
                raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "source_ref 已存在且请求内容不一致")
            return self._build_sales_payment_entry_data(existing_source)

        invoice = (
            session.query(LyDeliveryInvoice)
            .filter(
                LyDeliveryInvoice.company == company,
                LyDeliveryInvoice.sales_invoice == sales_invoice,
            )
            .with_for_update()
            .first()
        )
        if invoice is None:
            raise SalesInventoryServiceError(404, "SALES_PAYMENT_INVOICE_NOT_FOUND", "销售发票不存在")
        if str(invoice.status) == "cancelled":
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "已取消销售发票不可回款")
        if customer is not None and self._text(invoice.customer) not in {None, customer}:
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "客户与销售发票不一致")

        outstanding_before = Decimal(str(invoice.outstanding_amount or 0))
        if outstanding_before <= Decimal("0"):
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ALREADY_PAID", "销售发票无未收款余额")
        if paid_amount > outstanding_before:
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_AMOUNT_EXCEEDED", "回款金额超过未收款余额")

        payment_entry = requested_payment_entry or self._next_sales_payment_entry(
            company=company,
            posting_date=payload.posting_date,
        )
        existing_payment = (
            session.query(LySalesPaymentEntry)
            .filter(
                LySalesPaymentEntry.company == company,
                LySalesPaymentEntry.payment_entry == payment_entry,
            )
            .first()
        )
        if existing_payment is not None:
            raise SalesInventoryServiceError(409, "SALES_PAYMENT_ENTRY_CONFLICT", "payment_entry 已存在")

        outstanding_after = outstanding_before - paid_amount
        invoice.paid_amount = Decimal(str(invoice.paid_amount or 0)) + paid_amount
        invoice.outstanding_amount = outstanding_after
        invoice.status = "paid" if outstanding_after == Decimal("0") else "partly_paid"
        invoice.updated_by = current_user
        invoice.updated_at = datetime.now(timezone.utc)

        row = LySalesPaymentEntry(
            company=company,
            payment_entry=payment_entry,
            delivery_invoice_id=int(invoice.id),
            delivery_note=str(invoice.delivery_note),
            sales_invoice=str(invoice.sales_invoice),
            sales_order=str(invoice.sales_order),
            customer=customer or self._text(invoice.customer),
            posting_date=payload.posting_date,
            paid_amount=paid_amount,
            allocated_amount=paid_amount,
            outstanding_before=outstanding_before,
            outstanding_after=outstanding_after,
            mode_of_payment=mode_of_payment,
            reference_no=reference_no,
            reference_date=payload.reference_date,
            status="submitted",
            docstatus=1,
            source_ref=source_ref,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            scenario_tag=self._text(scenario_tag) or self._text(payload.scenario_tag),
            payload={
                "operation": operation,
                "scenario_tag": self._text(scenario_tag) or self._text(payload.scenario_tag),
                "sales_invoice": sales_invoice,
            },
            created_by=current_user,
        )
        session.add(row)
        session.flush()
        return self._build_sales_payment_entry_data(row)

    def list_local_payment_entries(
        self,
        *,
        company: str | None,
        sales_invoice: str | None,
        customer: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> SalesPaymentEntryListData:
        rows = self._query_local_payment_entries(
            company=company,
            sales_invoice=sales_invoice,
            customer=customer,
            status=status,
            keyword=keyword,
        )
        total = len(rows)
        start = max((page - 1) * page_size, 0)
        return SalesPaymentEntryListData(
            items=[self._build_sales_payment_entry_data(row) for row in rows[start : start + page_size]],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_local_sales_order_fulfillment(
        self,
        *,
        company: str | None,
        item_code: str | None,
        warehouse: str | None,
        item_name: str | None,
    ) -> SalesOrderFulfillmentData:
        local_orders = self.list_local_sales_orders(
            order_no=None,
            keyword=None,
            company=company,
            customer=None,
            item_code=item_code,
            item_name=item_name,
            from_date=None,
            to_date=None,
        )
        rows: list[SalesOrderFulfillmentItem] = []
        for order in local_orders:
            detail = self.get_local_sales_order(name=order.name)
            if detail is None:
                continue
            for line in detail.items:
                if item_code and line.item_code != item_code:
                    continue
                if warehouse and line.warehouse != warehouse:
                    continue
                if item_name and not self._contains_like(line.item_name, item_name):
                    continue
                ordered_qty = self._decimal_or_zero(line.qty)
                actual_qty = Decimal("0")
                rows.append(
                    SalesOrderFulfillmentItem(
                        company=detail.company,
                        sales_order=detail.name,
                        item_code=line.item_code,
                        warehouse=line.warehouse,
                        ordered_qty=ordered_qty,
                        actual_qty=actual_qty,
                        fulfillment_rate=self._fulfillment_rate(actual_qty=actual_qty, ordered_qty=ordered_qty),
                    )
                )
        rows.sort(key=lambda row: (row.sales_order, row.item_code, row.warehouse or ""))
        return SalesOrderFulfillmentData(company=company, items=rows)

    def get_stock_summary(
        self,
        *,
        item_code: str,
        company: str | None,
        warehouse: str | None,
    ) -> StockSummaryData:
        rows, dropped_count = self.adapter.get_stock_summary(item_code=item_code, company=company, warehouse=warehouse)
        return StockSummaryData(
            item_code=item_code,
            company=company,
            warehouse=warehouse,
            items=[
                StockSummaryItem(
                    company=str(row["company"]),
                    item_code=str(row["item_code"]),
                    warehouse=str(row["warehouse"]),
                    balance_qty=Decimal(str(row["balance_qty"])),
                    latest_posting_date=row.get("latest_posting_date"),
                    latest_posting_time=self._text(row.get("latest_posting_time")),
                )
                for row in rows
            ],
            dropped_count=dropped_count,
        )

    def list_stock_ledger(
        self,
        *,
        item_code: str,
        company: str | None,
        warehouse: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> StockLedgerData:
        rows, total, dropped_count = self.adapter.list_stock_ledger(
            item_code=item_code,
            company=company,
            warehouse=warehouse,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        return StockLedgerData(
            items=[
                StockLedgerItem(
                    name=self._text(row.get("name")),
                    company=str(row["company"]),
                    item_code=str(row["item_code"]),
                    warehouse=str(row["warehouse"]),
                    posting_date=row["posting_date"],
                    posting_time=self._text(row.get("posting_time")),
                    actual_qty=Decimal(str(row["actual_qty"])),
                    qty_after_transaction=Decimal(str(row["qty_after_transaction"])),
                    voucher_type=self._text(row.get("voucher_type")),
                    voucher_no=self._text(row.get("voucher_no")),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
            dropped_count=dropped_count,
        )

    def get_material_transfers(
        self,
        *,
        item_code: str | None,
        keyword: str | None,
        source_warehouse: str | None,
        target_warehouse: str | None,
        status: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> MaterialTransferData:
        normalized_item_code = self._text(item_code)
        normalized_keyword = self._text(keyword)
        normalized_source_warehouse = self._text(source_warehouse)
        normalized_target_warehouse = self._text(target_warehouse)
        normalized_status = self._text(status)

        seed_rows = [
            {
                "transfer_no": "MT-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "source_warehouse": "面料主仓",
                "target_warehouse": "成品前置仓",
                "transfer_qty": Decimal("360"),
                "inbound_qty": Decimal("360"),
                "diff_qty": Decimal("0"),
                "operator": "陈晓敏",
                "status": "已完成",
                "transfer_date": date(2026, 5, 1),
                "company": "凌云服饰",
            },
            {
                "transfer_no": "MT-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "source_warehouse": "辅料主仓",
                "target_warehouse": "车缝线边仓",
                "transfer_qty": Decimal("820"),
                "inbound_qty": Decimal("780"),
                "diff_qty": Decimal("40"),
                "operator": "刘俊伟",
                "status": "调拨中",
                "transfer_date": date(2026, 5, 2),
                "company": "凌云服饰",
            },
            {
                "transfer_no": "MT-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "source_warehouse": "包材仓",
                "target_warehouse": "发货备料仓",
                "transfer_qty": Decimal("1200"),
                "inbound_qty": Decimal("0"),
                "diff_qty": Decimal("1200"),
                "operator": "张瑞",
                "status": "待确认",
                "transfer_date": date(2026, 5, 3),
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_source_warehouse and row["source_warehouse"] != normalized_source_warehouse:
                continue
            if normalized_target_warehouse and row["target_warehouse"] != normalized_target_warehouse:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["transfer_date"] < from_date:
                continue
            if to_date and row["transfer_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["transfer_no"],
                        row["material_code"],
                        row["material_name"],
                        row["source_warehouse"],
                        row["target_warehouse"],
                        row["operator"],
                        row["status"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["transfer_date"], entry["transfer_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return MaterialTransferData(
            items=[
                MaterialTransferItem(
                    transfer_no=row["transfer_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    source_warehouse=row["source_warehouse"],
                    target_warehouse=row["target_warehouse"],
                    transfer_qty=row["transfer_qty"],
                    inbound_qty=row["inbound_qty"],
                    diff_qty=row["diff_qty"],
                    operator=row["operator"],
                    status=row["status"],
                    transfer_date=row["transfer_date"],
                    warehouse=row["source_warehouse"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_material_counts(
        self,
        *,
        item_code: str | None,
        keyword: str | None,
        warehouse: str | None,
        count_status: str | None,
        review_status: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> MaterialCountData:
        normalized_item_code = self._text(item_code)
        normalized_keyword = self._text(keyword)
        normalized_warehouse = self._text(warehouse)
        normalized_count_status = self._text(count_status)
        normalized_review_status = self._text(review_status)

        seed_rows = [
            {
                "count_no": "MC-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "warehouse": "面料主仓",
                "book_qty": Decimal("1280"),
                "counted_qty": Decimal("1280"),
                "diff_qty": Decimal("0"),
                "count_status": "已完成",
                "review_status": "已复核",
                "count_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "company": "凌云服饰",
            },
            {
                "count_no": "MC-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "warehouse": "辅料主仓",
                "book_qty": Decimal("2400"),
                "counted_qty": Decimal("2386"),
                "diff_qty": Decimal("-14"),
                "count_status": "盘点中",
                "review_status": "待复核",
                "count_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "company": "凌云服饰",
            },
            {
                "count_no": "MC-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "warehouse": "包材仓",
                "book_qty": Decimal("5300"),
                "counted_qty": Decimal("0"),
                "diff_qty": Decimal("-5300"),
                "count_status": "待盘点",
                "review_status": "待送审",
                "count_date": date(2026, 5, 3),
                "owner": "张瑞",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_count_status and row["count_status"] != normalized_count_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue
            if from_date and row["count_date"] < from_date:
                continue
            if to_date and row["count_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["count_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["owner"],
                        row["count_status"],
                        row["review_status"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["count_date"], entry["count_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return MaterialCountData(
            items=[
                MaterialCountItem(
                    count_no=row["count_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    book_qty=row["book_qty"],
                    counted_qty=row["counted_qty"],
                    diff_qty=row["diff_qty"],
                    count_status=row["count_status"],
                    review_status=row["review_status"],
                    count_date=row["count_date"],
                    owner=row["owner"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_material_inventory_report(
        self,
        *,
        report_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        business_type: str | None,
        status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> MaterialInventoryReportData:
        normalized_report_no = self._text(report_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_business_type = self._text(business_type)
        normalized_status = self._text(status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "report_no": "MIR-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "warehouse": "面料主仓",
                "business_type": "采购入仓",
                "in_qty": Decimal("820"),
                "out_qty": Decimal("120"),
                "balance_qty": Decimal("700"),
                "status": "已完成",
                "biz_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "ref_no": "PR-2026-0501",
                "company": "凌云服饰",
            },
            {
                "report_no": "MIR-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "warehouse": "辅料主仓",
                "business_type": "销售出仓",
                "in_qty": Decimal("0"),
                "out_qty": Decimal("460"),
                "balance_qty": Decimal("1940"),
                "status": "执行中",
                "biz_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "ref_no": "SO-2026-0418",
                "company": "凌云服饰",
            },
            {
                "report_no": "MIR-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "warehouse": "包材仓",
                "business_type": "盘点调整",
                "in_qty": Decimal("110"),
                "out_qty": Decimal("0"),
                "balance_qty": Decimal("5410"),
                "status": "待复核",
                "biz_date": date(2026, 5, 3),
                "owner": "张瑞",
                "ref_no": "MC-2026-0503",
                "company": "凌云服饰",
            },
            {
                "report_no": "MIR-2026-0504",
                "material_code": "MAT-PRO-088",
                "material_name": "压胶衬条",
                "warehouse": "加工备料仓",
                "business_type": "调仓入仓",
                "in_qty": Decimal("300"),
                "out_qty": Decimal("40"),
                "balance_qty": Decimal("260"),
                "status": "已完成",
                "biz_date": date(2026, 5, 4),
                "owner": "邓雅琪",
                "ref_no": "MT-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_report_no and row["report_no"] != normalized_report_no:
                continue
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_business_type and row["business_type"] != normalized_business_type:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["biz_date"] < from_date:
                continue
            if to_date and row["biz_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["report_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["business_type"],
                        row["status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["biz_date"], entry["report_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return MaterialInventoryReportData(
            items=[
                MaterialInventoryReportItem(
                    report_no=row["report_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    business_type=row["business_type"],
                    in_qty=row["in_qty"],
                    out_qty=row["out_qty"],
                    balance_qty=row["balance_qty"],
                    status=row["status"],
                    biz_date=row["biz_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_inventory_material_retention_report(
        self,
        *,
        report_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        retention_level: str | None,
        status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> InventoryMaterialRetentionReportData:
        normalized_report_no = self._text(report_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_retention_level = self._text(retention_level)
        normalized_status = self._text(status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "report_no": "IMR-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "warehouse": "面料主仓",
                "retention_level": "高滞留",
                "retention_days": Decimal("95"),
                "current_qty": Decimal("1260"),
                "stagnant_qty": Decimal("420"),
                "turnover_days": Decimal("58"),
                "status": "待处理",
                "biz_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "ref_no": "STL-2026-0501",
                "company": "凌云服饰",
            },
            {
                "report_no": "IMR-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "warehouse": "辅料主仓",
                "retention_level": "中滞留",
                "retention_days": Decimal("61"),
                "current_qty": Decimal("2386"),
                "stagnant_qty": Decimal("310"),
                "turnover_days": Decimal("37"),
                "status": "跟进中",
                "biz_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "ref_no": "STL-2026-0502",
                "company": "凌云服饰",
            },
            {
                "report_no": "IMR-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "warehouse": "包材仓",
                "retention_level": "低滞留",
                "retention_days": Decimal("32"),
                "current_qty": Decimal("5410"),
                "stagnant_qty": Decimal("160"),
                "turnover_days": Decimal("22"),
                "status": "已完成",
                "biz_date": date(2026, 5, 3),
                "owner": "张瑞",
                "ref_no": "STL-2026-0503",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_report_no and row["report_no"] != normalized_report_no:
                continue
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_retention_level and row["retention_level"] != normalized_retention_level:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["biz_date"] < from_date:
                continue
            if to_date and row["biz_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["report_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["retention_level"],
                        row["status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["biz_date"], entry["report_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return InventoryMaterialRetentionReportData(
            items=[
                InventoryMaterialRetentionReportItem(
                    report_no=row["report_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    retention_level=row["retention_level"],
                    retention_days=row["retention_days"],
                    current_qty=row["current_qty"],
                    stagnant_qty=row["stagnant_qty"],
                    turnover_days=row["turnover_days"],
                    status=row["status"],
                    biz_date=row["biz_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_semi_finished_inventory(
        self,
        *,
        record_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        process_stage: str | None,
        status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> SemiFinishedInventoryData:
        normalized_record_no = self._text(record_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_process_stage = self._text(process_stage)
        normalized_status = self._text(status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "record_no": "SFI-2026-0501",
                "material_code": "SF-TSHIRT-001",
                "material_name": "半成品T恤衣身",
                "warehouse": "半成品A仓",
                "process_stage": "车缝完成",
                "opening_qty": Decimal("260"),
                "in_qty": Decimal("140"),
                "out_qty": Decimal("120"),
                "closing_qty": Decimal("280"),
                "status": "在库",
                "biz_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "ref_no": "WIP-2026-0501",
                "company": "凌云服饰",
            },
            {
                "record_no": "SFI-2026-0502",
                "material_code": "SF-JACKET-014",
                "material_name": "半成品夹克前片",
                "warehouse": "半成品B仓",
                "process_stage": "锁边完成",
                "opening_qty": Decimal("180"),
                "in_qty": Decimal("90"),
                "out_qty": Decimal("70"),
                "closing_qty": Decimal("200"),
                "status": "在库",
                "biz_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "ref_no": "WIP-2026-0502",
                "company": "凌云服饰",
            },
            {
                "record_no": "SFI-2026-0503",
                "material_code": "SF-DRESS-031",
                "material_name": "半成品连衣裙裙摆",
                "warehouse": "半成品A仓",
                "process_stage": "整烫待检",
                "opening_qty": Decimal("120"),
                "in_qty": Decimal("60"),
                "out_qty": Decimal("30"),
                "closing_qty": Decimal("150"),
                "status": "待质检",
                "biz_date": date(2026, 5, 3),
                "owner": "张瑞",
                "ref_no": "WIP-2026-0503",
                "company": "凌云服饰",
            },
            {
                "record_no": "SFI-2026-0504",
                "material_code": "SF-PANTS-052",
                "material_name": "半成品休闲裤裤腿",
                "warehouse": "半成品C仓",
                "process_stage": "返修处理中",
                "opening_qty": Decimal("96"),
                "in_qty": Decimal("20"),
                "out_qty": Decimal("18"),
                "closing_qty": Decimal("98"),
                "status": "返修中",
                "biz_date": date(2026, 5, 4),
                "owner": "邓雅琪",
                "ref_no": "WIP-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_record_no and row["record_no"] != normalized_record_no:
                continue
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_process_stage and row["process_stage"] != normalized_process_stage:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["biz_date"] < from_date:
                continue
            if to_date and row["biz_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["record_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["process_stage"],
                        row["status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["biz_date"], entry["record_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return SemiFinishedInventoryData(
            items=[
                SemiFinishedInventoryItem(
                    record_no=row["record_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    process_stage=row["process_stage"],
                    opening_qty=row["opening_qty"],
                    in_qty=row["in_qty"],
                    out_qty=row["out_qty"],
                    closing_qty=row["closing_qty"],
                    status=row["status"],
                    biz_date=row["biz_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_reserved_inbound(
        self,
        *,
        reservation_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        reserve_status: str | None,
        inbound_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsReservedInboundData:
        normalized_reservation_no = self._text(reservation_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_reserve_status = self._text(reserve_status)
        normalized_inbound_status = self._text(inbound_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "reservation_no": "FGRI-2026-0501",
                "item_code": "FG-TSHIRT-001",
                "item_name": "圆领短袖T恤成品",
                "warehouse": "成品预约A仓",
                "reserve_qty": Decimal("360"),
                "inbound_qty": Decimal("0"),
                "pending_inbound_qty": Decimal("360"),
                "reserve_status": "已预约",
                "inbound_status": "待入仓",
                "reserved_date": date(2026, 5, 1),
                "expected_inbound_date": date(2026, 5, 6),
                "owner": "李佳琳",
                "ref_no": "RSV-2026-0501",
                "company": "凌云服饰",
            },
            {
                "reservation_no": "FGRI-2026-0502",
                "item_code": "FG-JACKET-014",
                "item_name": "机能夹克成品",
                "warehouse": "成品预约B仓",
                "reserve_qty": Decimal("180"),
                "inbound_qty": Decimal("60"),
                "pending_inbound_qty": Decimal("120"),
                "reserve_status": "部分入仓",
                "inbound_status": "入仓中",
                "reserved_date": date(2026, 5, 2),
                "expected_inbound_date": date(2026, 5, 8),
                "owner": "周晨",
                "ref_no": "RSV-2026-0502",
                "company": "凌云服饰",
            },
            {
                "reservation_no": "FGRI-2026-0503",
                "item_code": "FG-DRESS-031",
                "item_name": "碎花连衣裙成品",
                "warehouse": "成品预约A仓",
                "reserve_qty": Decimal("240"),
                "inbound_qty": Decimal("240"),
                "pending_inbound_qty": Decimal("0"),
                "reserve_status": "已入仓",
                "inbound_status": "已完成",
                "reserved_date": date(2026, 5, 3),
                "expected_inbound_date": date(2026, 5, 9),
                "owner": "吴静怡",
                "ref_no": "RSV-2026-0503",
                "company": "凌云服饰",
            },
            {
                "reservation_no": "FGRI-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品预约C仓",
                "reserve_qty": Decimal("150"),
                "inbound_qty": Decimal("0"),
                "pending_inbound_qty": Decimal("150"),
                "reserve_status": "待确认",
                "inbound_status": "未开始",
                "reserved_date": date(2026, 5, 4),
                "expected_inbound_date": date(2026, 5, 12),
                "owner": "邵伟",
                "ref_no": "RSV-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_reservation_no and row["reservation_no"] != normalized_reservation_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_reserve_status and row["reserve_status"] != normalized_reserve_status:
                continue
            if normalized_inbound_status and row["inbound_status"] != normalized_inbound_status:
                continue
            if from_date and row["reserved_date"] < from_date:
                continue
            if to_date and row["reserved_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["reservation_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["reserve_status"],
                        row["inbound_status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["reserved_date"], entry["reservation_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsReservedInboundData(
            items=[
                FinishedGoodsReservedInboundItem(
                    reservation_no=row["reservation_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    reserve_qty=row["reserve_qty"],
                    inbound_qty=row["inbound_qty"],
                    pending_inbound_qty=row["pending_inbound_qty"],
                    reserve_status=row["reserve_status"],
                    inbound_status=row["inbound_status"],
                    reserved_date=row["reserved_date"],
                    expected_inbound_date=row["expected_inbound_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_shipping_notices(
        self,
        *,
        notice_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        notice_status: str | None,
        logistics_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsShippingNoticeData:
        normalized_notice_no = self._text(notice_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_notice_status = self._text(notice_status)
        normalized_logistics_status = self._text(logistics_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "notice_no": "FGSN-2026-0501",
                "item_code": "FG-TSHIRT-001",
                "item_name": "圆领短袖T恤成品",
                "warehouse": "成品主仓",
                "planned_ship_qty": Decimal("360"),
                "shipped_qty": Decimal("120"),
                "pending_ship_qty": Decimal("240"),
                "notice_status": "已下发",
                "logistics_status": "待揽收",
                "notice_date": date(2026, 5, 1),
                "expected_delivery_date": date(2026, 5, 6),
                "owner": "李佳琳",
                "ref_no": "SO-2026-0401",
                "company": "凌云服饰",
            },
            {
                "notice_no": "FGSN-2026-0502",
                "item_code": "FG-JACKET-014",
                "item_name": "机能夹克成品",
                "warehouse": "成品发货A仓",
                "planned_ship_qty": Decimal("180"),
                "shipped_qty": Decimal("180"),
                "pending_ship_qty": Decimal("0"),
                "notice_status": "已完成",
                "logistics_status": "运输中",
                "notice_date": date(2026, 5, 2),
                "expected_delivery_date": date(2026, 5, 7),
                "owner": "周晨",
                "ref_no": "SO-2026-0402",
                "company": "凌云服饰",
            },
            {
                "notice_no": "FGSN-2026-0503",
                "item_code": "FG-DRESS-031",
                "item_name": "碎花连衣裙成品",
                "warehouse": "成品发货B仓",
                "planned_ship_qty": Decimal("240"),
                "shipped_qty": Decimal("0"),
                "pending_ship_qty": Decimal("240"),
                "notice_status": "待确认",
                "logistics_status": "未开始",
                "notice_date": date(2026, 5, 3),
                "expected_delivery_date": date(2026, 5, 9),
                "owner": "吴静怡",
                "ref_no": "SO-2026-0403",
                "company": "凌云服饰",
            },
            {
                "notice_no": "FGSN-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品主仓",
                "planned_ship_qty": Decimal("150"),
                "shipped_qty": Decimal("60"),
                "pending_ship_qty": Decimal("90"),
                "notice_status": "部分发货",
                "logistics_status": "待揽收",
                "notice_date": date(2026, 5, 4),
                "expected_delivery_date": date(2026, 5, 10),
                "owner": "邵伟",
                "ref_no": "SO-2026-0404",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_notice_no and row["notice_no"] != normalized_notice_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_notice_status and row["notice_status"] != normalized_notice_status:
                continue
            if normalized_logistics_status and row["logistics_status"] != normalized_logistics_status:
                continue
            if from_date and row["notice_date"] < from_date:
                continue
            if to_date and row["notice_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["notice_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["notice_status"],
                        row["logistics_status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["notice_date"], entry["notice_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsShippingNoticeData(
            items=[
                FinishedGoodsShippingNoticeItem(
                    notice_no=row["notice_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    planned_ship_qty=row["planned_ship_qty"],
                    shipped_qty=row["shipped_qty"],
                    pending_ship_qty=row["pending_ship_qty"],
                    notice_status=row["notice_status"],
                    logistics_status=row["logistics_status"],
                    notice_date=row["notice_date"],
                    expected_delivery_date=row["expected_delivery_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_other_inbound(
        self,
        *,
        inbound_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        inbound_status: str | None,
        settlement_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsOtherInboundData:
        normalized_inbound_no = self._text(inbound_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_inbound_status = self._text(inbound_status)
        normalized_settlement_status = self._text(settlement_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "inbound_no": "FGOI-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "warehouse": "成品其他入仓A仓",
                "planned_inbound_qty": Decimal("320"),
                "actual_inbound_qty": Decimal("200"),
                "pending_inbound_qty": Decimal("120"),
                "inbound_status": "入仓中",
                "settlement_status": "待核销",
                "inbound_date": date(2026, 5, 1),
                "source_doc_no": "OI-SRC-2026-0501",
                "owner": "李佳琳",
                "ref_no": "STK-OTH-2026-0501",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "FGOI-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "warehouse": "成品其他入仓B仓",
                "planned_inbound_qty": Decimal("180"),
                "actual_inbound_qty": Decimal("180"),
                "pending_inbound_qty": Decimal("0"),
                "inbound_status": "已完成",
                "settlement_status": "已核销",
                "inbound_date": date(2026, 5, 2),
                "source_doc_no": "OI-SRC-2026-0502",
                "owner": "周晨",
                "ref_no": "STK-OTH-2026-0502",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "FGOI-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "warehouse": "成品其他入仓A仓",
                "planned_inbound_qty": Decimal("260"),
                "actual_inbound_qty": Decimal("0"),
                "pending_inbound_qty": Decimal("260"),
                "inbound_status": "待确认",
                "settlement_status": "未开始",
                "inbound_date": date(2026, 5, 3),
                "source_doc_no": "OI-SRC-2026-0503",
                "owner": "吴静怡",
                "ref_no": "STK-OTH-2026-0503",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "FGOI-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品其他入仓C仓",
                "planned_inbound_qty": Decimal("150"),
                "actual_inbound_qty": Decimal("60"),
                "pending_inbound_qty": Decimal("90"),
                "inbound_status": "部分入仓",
                "settlement_status": "核销中",
                "inbound_date": date(2026, 5, 4),
                "source_doc_no": "OI-SRC-2026-0504",
                "owner": "邵伟",
                "ref_no": "STK-OTH-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_inbound_no and row["inbound_no"] != normalized_inbound_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_inbound_status and row["inbound_status"] != normalized_inbound_status:
                continue
            if normalized_settlement_status and row["settlement_status"] != normalized_settlement_status:
                continue
            if from_date and row["inbound_date"] < from_date:
                continue
            if to_date and row["inbound_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["inbound_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["inbound_status"],
                        row["settlement_status"],
                        row["source_doc_no"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["inbound_date"], entry["inbound_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsOtherInboundData(
            items=[
                FinishedGoodsOtherInboundItem(
                    inbound_no=row["inbound_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    planned_inbound_qty=row["planned_inbound_qty"],
                    actual_inbound_qty=row["actual_inbound_qty"],
                    pending_inbound_qty=row["pending_inbound_qty"],
                    inbound_status=row["inbound_status"],
                    settlement_status=row["settlement_status"],
                    inbound_date=row["inbound_date"],
                    source_doc_no=row["source_doc_no"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_report(
        self,
        *,
        no: str | None,
        style: str | None,
        warehouse: str | None,
        from_date: date | None,
        to_date: date | None,
        keyword: str | None,
        page: int,
        page_size: int,
        ) -> FinishedGoodsReportData:
        normalized_no = self._text(no)
        normalized_style = self._text(style)
        normalized_keyword = self._text(keyword)
        rows, _ = self.adapter.list_sales_orders(
            company=None,
            customer=None,
            item_code=None,
            item_name=normalized_style or normalized_keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        report_rows: list[FinishedGoodsReportItem] = []
        for order in rows:
            order_no = str(order.get("name") or "").strip()
            if not order_no:
                continue
            order_company = self._text(order.get("company"))
            order_customer = self._text(order.get("customer"))
            detail = self.adapter.get_sales_order(name=order_no)
            for line in self._list_or_empty(detail.get("items")):
                line_item_code = self._text(line.get("item_code")) or "-"
                line_item_name = self._text(line.get("item_name"))
                line_warehouse = self._text(line.get("warehouse"))
                processing_no = self._text(line.get("name"))
                style_type = self._text(line.get("custom_style_type")) or self._text(line.get("category"))
                season = self._text(line.get("custom_season")) or self._text(order.get("custom_season"))
                if normalized_no and not self._contains_like(order_no, normalized_no):
                    continue
                if normalized_style:
                    in_style = self._contains_like(line_item_code, normalized_style) or self._contains_like(
                        line_item_name, normalized_style
                    )
                    if not in_style:
                        continue
                if warehouse and line_warehouse != warehouse:
                    continue
                if normalized_keyword:
                    keyword_text = " ".join(
                        (
                            order_no,
                            line_item_code,
                            line_item_name or "",
                            order_customer or "",
                        )
                    )
                    if not self._contains_like(keyword_text, normalized_keyword):
                        continue
                report_rows.append(
                    FinishedGoodsReportItem(
                        image_url=None,
                        processing_no=processing_no,
                        production_order=None,
                        order_no=order_no,
                        item_code=line_item_code,
                        item_name=line_item_name,
                        warehouse=line_warehouse,
                        season=season,
                        style_type=style_type,
                        qty=self._decimal_or_zero(line.get("qty")),
                        receipt_date=detail.get("transaction_date"),
                        company=order_company,
                        customer=order_customer,
                        week_day_0="-",
                        week_day_1="-",
                        week_day_2="-",
                        week_day_3="-",
                        week_day_4="-",
                        week_day_5="-",
                        week_day_6="-",
                        message_title="-",
                        sent_at="-",
                        message_status=self._text(order.get("status")) or "-",
                        sender="-",
                    )
                )
        report_rows.sort(key=lambda row: (row.order_no, row.item_code, row.processing_no or ""))
        total = len(report_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_items = report_rows[start:end]
        return FinishedGoodsReportData(
            items=paged_items,
            total=total,
            page=page,
            page_size=page_size,
            dropped_count=0,
        )

    def get_customer_return_applications(
        self,
        *,
        application_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        application_status: str | None,
        approval_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> CustomerReturnApplicationData:
        normalized_application_no = self._text(application_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_application_status = self._text(application_status)
        normalized_approval_status = self._text(approval_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "application_no": "CRA-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "warehouse": "成品主仓",
                "requested_return_qty": Decimal("42"),
                "confirmed_return_qty": Decimal("20"),
                "pending_return_qty": Decimal("22"),
                "application_status": "已受理",
                "approval_status": "待复核",
                "application_date": date(2026, 5, 1),
                "source_doc_no": "SO-2026-0408",
                "owner": "李佳琳",
                "ref_no": "RET-REQ-2026-0501",
                "company": "凌云服饰",
            },
            {
                "application_no": "CRA-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "warehouse": "成品发货A仓",
                "requested_return_qty": Decimal("18"),
                "confirmed_return_qty": Decimal("18"),
                "pending_return_qty": Decimal("0"),
                "application_status": "已确认",
                "approval_status": "已通过",
                "application_date": date(2026, 5, 2),
                "source_doc_no": "SO-2026-0411",
                "owner": "周晨",
                "ref_no": "RET-REQ-2026-0502",
                "company": "凌云服饰",
            },
            {
                "application_no": "CRA-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "warehouse": "成品主仓",
                "requested_return_qty": Decimal("30"),
                "confirmed_return_qty": Decimal("0"),
                "pending_return_qty": Decimal("30"),
                "application_status": "草稿",
                "approval_status": "未开始",
                "application_date": date(2026, 5, 3),
                "source_doc_no": "SO-2026-0413",
                "owner": "吴静怡",
                "ref_no": "RET-REQ-2026-0503",
                "company": "凌云服饰",
            },
            {
                "application_no": "CRA-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品发货B仓",
                "requested_return_qty": Decimal("24"),
                "confirmed_return_qty": Decimal("12"),
                "pending_return_qty": Decimal("12"),
                "application_status": "已受理",
                "approval_status": "复核中",
                "application_date": date(2026, 5, 4),
                "source_doc_no": "SO-2026-0416",
                "owner": "邵伟",
                "ref_no": "RET-REQ-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_application_no and row["application_no"] != normalized_application_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_application_status and row["application_status"] != normalized_application_status:
                continue
            if normalized_approval_status and row["approval_status"] != normalized_approval_status:
                continue
            if from_date and row["application_date"] < from_date:
                continue
            if to_date and row["application_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["application_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["application_status"],
                        row["approval_status"],
                        row["source_doc_no"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["application_date"], entry["application_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return CustomerReturnApplicationData(
            items=[
                CustomerReturnApplicationItem(
                    application_no=row["application_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    requested_return_qty=row["requested_return_qty"],
                    confirmed_return_qty=row["confirmed_return_qty"],
                    pending_return_qty=row["pending_return_qty"],
                    application_status=row["application_status"],
                    approval_status=row["approval_status"],
                    application_date=row["application_date"],
                    source_doc_no=row["source_doc_no"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_customer_return_inbound(
        self,
        *,
        inbound_no: str | None,
        application_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        inbound_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> CustomerReturnInboundData:
        normalized_inbound_no = self._text(inbound_no)
        normalized_application_no = self._text(application_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_inbound_status = self._text(inbound_status)
        normalized_review_status = self._text(review_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "inbound_no": "CRI-2026-0501",
                "application_no": "CRA-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "warehouse": "成品主仓",
                "planned_inbound_qty": Decimal("20"),
                "actual_inbound_qty": Decimal("10"),
                "pending_inbound_qty": Decimal("10"),
                "inbound_status": "待入仓",
                "review_status": "待复核",
                "inbound_date": date(2026, 5, 1),
                "source_doc_no": "RET-IN-2026-0501",
                "owner": "李佳琳",
                "ref_no": "RET-INB-2026-0501",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "CRI-2026-0502",
                "application_no": "CRA-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "warehouse": "成品发货A仓",
                "planned_inbound_qty": Decimal("18"),
                "actual_inbound_qty": Decimal("18"),
                "pending_inbound_qty": Decimal("0"),
                "inbound_status": "已完成",
                "review_status": "已通过",
                "inbound_date": date(2026, 5, 2),
                "source_doc_no": "RET-IN-2026-0502",
                "owner": "周晨",
                "ref_no": "RET-INB-2026-0502",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "CRI-2026-0503",
                "application_no": "CRA-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "warehouse": "成品主仓",
                "planned_inbound_qty": Decimal("12"),
                "actual_inbound_qty": Decimal("0"),
                "pending_inbound_qty": Decimal("12"),
                "inbound_status": "草稿",
                "review_status": "未开始",
                "inbound_date": date(2026, 5, 3),
                "source_doc_no": "RET-IN-2026-0503",
                "owner": "吴静怡",
                "ref_no": "RET-INB-2026-0503",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "CRI-2026-0504",
                "application_no": "CRA-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品发货B仓",
                "planned_inbound_qty": Decimal("24"),
                "actual_inbound_qty": Decimal("12"),
                "pending_inbound_qty": Decimal("12"),
                "inbound_status": "入仓中",
                "review_status": "复核中",
                "inbound_date": date(2026, 5, 4),
                "source_doc_no": "RET-IN-2026-0504",
                "owner": "邵伟",
                "ref_no": "RET-INB-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_inbound_no and row["inbound_no"] != normalized_inbound_no:
                continue
            if normalized_application_no and row["application_no"] != normalized_application_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_inbound_status and row["inbound_status"] != normalized_inbound_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue
            if from_date and row["inbound_date"] < from_date:
                continue
            if to_date and row["inbound_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["inbound_no"],
                        row["application_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["inbound_status"],
                        row["review_status"],
                        row["source_doc_no"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["inbound_date"], entry["inbound_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return CustomerReturnInboundData(
            items=[
                CustomerReturnInboundItem(
                    inbound_no=row["inbound_no"],
                    application_no=row["application_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    planned_inbound_qty=row["planned_inbound_qty"],
                    actual_inbound_qty=row["actual_inbound_qty"],
                    pending_inbound_qty=row["pending_inbound_qty"],
                    inbound_status=row["inbound_status"],
                    review_status=row["review_status"],
                    inbound_date=row["inbound_date"],
                    source_doc_no=row["source_doc_no"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_other_outbound(
        self,
        *,
        outbound_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        outbound_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsOtherOutboundData:
        normalized_outbound_no = self._text(outbound_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_outbound_status = self._text(outbound_status)
        normalized_review_status = self._text(review_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "outbound_no": "FGOO-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "warehouse": "成品主仓",
                "planned_outbound_qty": Decimal("36"),
                "actual_outbound_qty": Decimal("18"),
                "pending_outbound_qty": Decimal("18"),
                "outbound_status": "待出仓",
                "review_status": "待复核",
                "outbound_date": date(2026, 5, 1),
                "source_doc_no": "FG-SRC-2026-0501",
                "owner": "李佳琳",
                "ref_no": "FG-OUT-2026-0501",
                "company": "凌云服饰",
            },
            {
                "outbound_no": "FGOO-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "warehouse": "成品发货A仓",
                "planned_outbound_qty": Decimal("24"),
                "actual_outbound_qty": Decimal("24"),
                "pending_outbound_qty": Decimal("0"),
                "outbound_status": "已完成",
                "review_status": "已通过",
                "outbound_date": date(2026, 5, 2),
                "source_doc_no": "FG-SRC-2026-0502",
                "owner": "周晨",
                "ref_no": "FG-OUT-2026-0502",
                "company": "凌云服饰",
            },
            {
                "outbound_no": "FGOO-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "warehouse": "成品主仓",
                "planned_outbound_qty": Decimal("20"),
                "actual_outbound_qty": Decimal("0"),
                "pending_outbound_qty": Decimal("20"),
                "outbound_status": "草稿",
                "review_status": "未开始",
                "outbound_date": date(2026, 5, 3),
                "source_doc_no": "FG-SRC-2026-0503",
                "owner": "吴静怡",
                "ref_no": "FG-OUT-2026-0503",
                "company": "凌云服饰",
            },
            {
                "outbound_no": "FGOO-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品发货B仓",
                "planned_outbound_qty": Decimal("30"),
                "actual_outbound_qty": Decimal("12"),
                "pending_outbound_qty": Decimal("18"),
                "outbound_status": "出仓中",
                "review_status": "复核中",
                "outbound_date": date(2026, 5, 4),
                "source_doc_no": "FG-SRC-2026-0504",
                "owner": "邵伟",
                "ref_no": "FG-OUT-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_outbound_no and row["outbound_no"] != normalized_outbound_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_outbound_status and row["outbound_status"] != normalized_outbound_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue
            if from_date and row["outbound_date"] < from_date:
                continue
            if to_date and row["outbound_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["outbound_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["outbound_status"],
                        row["review_status"],
                        row["source_doc_no"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["outbound_date"], entry["outbound_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsOtherOutboundData(
            items=[
                FinishedGoodsOtherOutboundItem(
                    outbound_no=row["outbound_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    planned_outbound_qty=row["planned_outbound_qty"],
                    actual_outbound_qty=row["actual_outbound_qty"],
                    pending_outbound_qty=row["pending_outbound_qty"],
                    outbound_status=row["outbound_status"],
                    review_status=row["review_status"],
                    outbound_date=row["outbound_date"],
                    source_doc_no=row["source_doc_no"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_count(
        self,
        *,
        count_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        count_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsCountData:
        normalized_count_no = self._text(count_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_count_status = self._text(count_status)
        normalized_review_status = self._text(review_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "count_no": "FGC-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "warehouse": "成品主仓",
                "book_qty": Decimal("180"),
                "counted_qty": Decimal("176"),
                "diff_qty": Decimal("-4"),
                "count_status": "盘点中",
                "review_status": "待复核",
                "count_date": date(2026, 5, 1),
                "owner": "李佳琳",
                "ref_no": "FG-CNT-2026-0501",
                "company": "凌云服饰",
            },
            {
                "count_no": "FGC-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "warehouse": "成品发货A仓",
                "book_qty": Decimal("96"),
                "counted_qty": Decimal("96"),
                "diff_qty": Decimal("0"),
                "count_status": "已完成",
                "review_status": "已通过",
                "count_date": date(2026, 5, 2),
                "owner": "周晨",
                "ref_no": "FG-CNT-2026-0502",
                "company": "凌云服饰",
            },
            {
                "count_no": "FGC-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "warehouse": "成品主仓",
                "book_qty": Decimal("128"),
                "counted_qty": Decimal("0"),
                "diff_qty": Decimal("-128"),
                "count_status": "待盘点",
                "review_status": "未开始",
                "count_date": date(2026, 5, 3),
                "owner": "吴静怡",
                "ref_no": "FG-CNT-2026-0503",
                "company": "凌云服饰",
            },
            {
                "count_no": "FGC-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品发货B仓",
                "book_qty": Decimal("142"),
                "counted_qty": Decimal("139"),
                "diff_qty": Decimal("-3"),
                "count_status": "盘点中",
                "review_status": "复核中",
                "count_date": date(2026, 5, 4),
                "owner": "邵伟",
                "ref_no": "FG-CNT-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_count_no and row["count_no"] != normalized_count_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_count_status and row["count_status"] != normalized_count_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue
            if from_date and row["count_date"] < from_date:
                continue
            if to_date and row["count_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["count_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["count_status"],
                        row["review_status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["count_date"], entry["count_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsCountData(
            items=[
                FinishedGoodsCountItem(
                    count_no=row["count_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    book_qty=row["book_qty"],
                    counted_qty=row["counted_qty"],
                    diff_qty=row["diff_qty"],
                    count_status=row["count_status"],
                    review_status=row["review_status"],
                    count_date=row["count_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_adjustment(
        self,
        *,
        adjustment_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        adjustment_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsAdjustmentData:
        normalized_adjustment_no = self._text(adjustment_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_adjustment_status = self._text(adjustment_status)
        normalized_review_status = self._text(review_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "adjustment_no": "FGA-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "warehouse": "成品主仓",
                "before_qty": Decimal("180"),
                "adjusted_qty": Decimal("176"),
                "diff_qty": Decimal("-4"),
                "adjustment_status": "调整中",
                "review_status": "待复核",
                "adjustment_date": date(2026, 5, 1),
                "adjust_reason": "盘点差异修正",
                "owner": "李佳琳",
                "ref_no": "FG-ADJ-2026-0501",
                "company": "凌云服饰",
            },
            {
                "adjustment_no": "FGA-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "warehouse": "成品发货A仓",
                "before_qty": Decimal("96"),
                "adjusted_qty": Decimal("99"),
                "diff_qty": Decimal("3"),
                "adjustment_status": "已完成",
                "review_status": "已通过",
                "adjustment_date": date(2026, 5, 2),
                "adjust_reason": "到货补差",
                "owner": "周晨",
                "ref_no": "FG-ADJ-2026-0502",
                "company": "凌云服饰",
            },
            {
                "adjustment_no": "FGA-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "warehouse": "成品主仓",
                "before_qty": Decimal("128"),
                "adjusted_qty": Decimal("128"),
                "diff_qty": Decimal("0"),
                "adjustment_status": "草稿",
                "review_status": "未开始",
                "adjustment_date": date(2026, 5, 3),
                "adjust_reason": "待业务确认",
                "owner": "吴静怡",
                "ref_no": "FG-ADJ-2026-0503",
                "company": "凌云服饰",
            },
            {
                "adjustment_no": "FGA-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品发货B仓",
                "before_qty": Decimal("142"),
                "adjusted_qty": Decimal("139"),
                "diff_qty": Decimal("-3"),
                "adjustment_status": "待确认",
                "review_status": "复核中",
                "adjustment_date": date(2026, 5, 4),
                "adjust_reason": "库存冻结回写",
                "owner": "邵伟",
                "ref_no": "FG-ADJ-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_adjustment_no and row["adjustment_no"] != normalized_adjustment_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_adjustment_status and row["adjustment_status"] != normalized_adjustment_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue
            if from_date and row["adjustment_date"] < from_date:
                continue
            if to_date and row["adjustment_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["adjustment_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["adjustment_status"],
                        row["review_status"],
                        row["adjust_reason"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["adjustment_date"], entry["adjustment_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsAdjustmentData(
            items=[
                FinishedGoodsAdjustmentItem(
                    adjustment_no=row["adjustment_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    before_qty=row["before_qty"],
                    adjusted_qty=row["adjusted_qty"],
                    diff_qty=row["diff_qty"],
                    adjustment_status=row["adjustment_status"],
                    review_status=row["review_status"],
                    adjustment_date=row["adjustment_date"],
                    adjust_reason=row["adjust_reason"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_transfer(
        self,
        *,
        transfer_no: str | None,
        item_code: str | None,
        source_warehouse: str | None,
        target_warehouse: str | None,
        transfer_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsTransferData:
        normalized_transfer_no = self._text(transfer_no)
        normalized_item_code = self._text(item_code)
        normalized_source_warehouse = self._text(source_warehouse)
        normalized_target_warehouse = self._text(target_warehouse)
        normalized_transfer_status = self._text(transfer_status)
        normalized_review_status = self._text(review_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "transfer_no": "FGTR-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "source_warehouse": "成品主仓",
                "target_warehouse": "电商前置仓",
                "planned_transfer_qty": Decimal("140"),
                "actual_transfer_qty": Decimal("90"),
                "pending_transfer_qty": Decimal("50"),
                "transfer_status": "调仓中",
                "review_status": "待复核",
                "transfer_date": date(2026, 5, 1),
                "transfer_reason": "大促前置备货",
                "owner": "李佳琳",
                "ref_no": "FG-TRF-2026-0501",
                "company": "凌云服饰",
            },
            {
                "transfer_no": "FGTR-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "source_warehouse": "成品主仓",
                "target_warehouse": "线下门店仓",
                "planned_transfer_qty": Decimal("80"),
                "actual_transfer_qty": Decimal("80"),
                "pending_transfer_qty": Decimal("0"),
                "transfer_status": "已完成",
                "review_status": "已通过",
                "transfer_date": date(2026, 5, 2),
                "transfer_reason": "门店补货",
                "owner": "周晨",
                "ref_no": "FG-TRF-2026-0502",
                "company": "凌云服饰",
            },
            {
                "transfer_no": "FGTR-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "source_warehouse": "成品发货A仓",
                "target_warehouse": "成品主仓",
                "planned_transfer_qty": Decimal("120"),
                "actual_transfer_qty": Decimal("0"),
                "pending_transfer_qty": Decimal("120"),
                "transfer_status": "待确认",
                "review_status": "未开始",
                "transfer_date": date(2026, 5, 3),
                "transfer_reason": "退回主仓整备",
                "owner": "吴静怡",
                "ref_no": "FG-TRF-2026-0503",
                "company": "凌云服饰",
            },
            {
                "transfer_no": "FGTR-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "source_warehouse": "成品发货B仓",
                "target_warehouse": "成品主仓",
                "planned_transfer_qty": Decimal("60"),
                "actual_transfer_qty": Decimal("40"),
                "pending_transfer_qty": Decimal("20"),
                "transfer_status": "草稿",
                "review_status": "复核中",
                "transfer_date": date(2026, 5, 4),
                "transfer_reason": "库存结构优化",
                "owner": "邵伟",
                "ref_no": "FG-TRF-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_transfer_no and row["transfer_no"] != normalized_transfer_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_source_warehouse and row["source_warehouse"] != normalized_source_warehouse:
                continue
            if normalized_target_warehouse and row["target_warehouse"] != normalized_target_warehouse:
                continue
            if normalized_transfer_status and row["transfer_status"] != normalized_transfer_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue
            if from_date and row["transfer_date"] < from_date:
                continue
            if to_date and row["transfer_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["transfer_no"],
                        row["item_code"],
                        row["item_name"],
                        row["source_warehouse"],
                        row["target_warehouse"],
                        row["transfer_status"],
                        row["review_status"],
                        row["transfer_reason"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["transfer_date"], entry["transfer_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsTransferData(
            items=[
                FinishedGoodsTransferItem(
                    transfer_no=row["transfer_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    source_warehouse=row["source_warehouse"],
                    target_warehouse=row["target_warehouse"],
                    planned_transfer_qty=row["planned_transfer_qty"],
                    actual_transfer_qty=row["actual_transfer_qty"],
                    pending_transfer_qty=row["pending_transfer_qty"],
                    transfer_status=row["transfer_status"],
                    review_status=row["review_status"],
                    transfer_date=row["transfer_date"],
                    transfer_reason=row["transfer_reason"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_warehouses(
        self,
        *,
        company: str | None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[WarehouseItem]:
        rows, total = self.adapter.list_warehouses(company=company, page=page, page_size=page_size)
        return SalesInventoryListData[WarehouseItem](
            items=[
                WarehouseItem(
                    name=str(row.get("name") or ""),
                    company=self._text(row.get("company")),
                    warehouse_name=self._text(row.get("warehouse_name")),
                    disabled=self._bool_or_none(row.get("disabled")),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_customers(self, *, page: int, page_size: int) -> SalesInventoryListData[CustomerItem]:
        rows, total = self.adapter.list_customers(page=page, page_size=page_size)
        return SalesInventoryListData[CustomerItem](
            items=[
                CustomerItem(
                    name=str(row.get("name") or ""),
                    customer_name=self._text(row.get("customer_name")),
                    disabled=self._bool_or_none(row.get("disabled")),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_suppliers(self, *, page: int, page_size: int) -> SalesInventoryListData[SupplierItem]:
        rows, total = self.adapter.list_suppliers(page=page, page_size=page_size)
        return SalesInventoryListData[SupplierItem](
            items=[
                SupplierItem(
                    name=str(row.get("name") or ""),
                    supplier_name=self._text(row.get("supplier_name")),
                    disabled=self._bool_or_none(row.get("disabled")),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_local_customers(
        self,
        *,
        keyword: str | None = None,
        company: str | None = None,
        disabled: bool | None = None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[CustomerItem]:
        drafts = self._list_reference_drafts_filtered(
            reference_type="customer",
            keyword=keyword,
            company=company,
            disabled=disabled,
            page=page,
            page_size=page_size,
        )
        return SalesInventoryListData[CustomerItem](
            items=[
                CustomerItem(
                    name=item.reference_no,
                    customer_name=item.reference_name,
                    disabled=item.status != "active",
                )
                for item in drafts.items
            ],
            total=drafts.total,
            page=page,
            page_size=page_size,
        )

    def list_local_suppliers(
        self,
        *,
        keyword: str | None = None,
        company: str | None = None,
        disabled: bool | None = None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[SupplierItem]:
        drafts = self._list_reference_drafts_filtered(
            reference_type="supplier",
            keyword=keyword,
            company=company,
            disabled=disabled,
            page=page,
            page_size=page_size,
        )
        return SalesInventoryListData[SupplierItem](
            items=[
                SupplierItem(
                    name=item.reference_no,
                    supplier_name=item.reference_name,
                    disabled=item.status != "active",
                )
                for item in drafts.items
            ],
            total=drafts.total,
            page=page,
            page_size=page_size,
        )

    def list_local_warehouses(
        self,
        *,
        company: str | None = None,
        keyword: str | None = None,
        disabled: bool | None = None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[WarehouseItem]:
        session = self._require_session()
        if disabled is True:
            return SalesInventoryListData[WarehouseItem](items=[], total=0, page=page, page_size=page_size)

        normalized_company = self._text(company)
        normalized_keyword = self._text(keyword)
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

        items_by_key: dict[tuple[str, str], WarehouseItem] = {}

        def add_warehouse(*, row_company: str, warehouse_name: str | None) -> None:
            normalized_warehouse = self._text(warehouse_name)
            if normalized_warehouse is None:
                return
            haystack = " ".join([normalized_warehouse, row_company])
            if normalized_keyword and not self._contains_like(haystack, normalized_keyword):
                return
            key = (row_company, normalized_warehouse)
            items_by_key[key] = WarehouseItem(
                name=normalized_warehouse,
                company=row_company,
                warehouse_name=normalized_warehouse,
                disabled=False,
            )

        for draft_row, item_row in query.all():
            row_company = str(draft_row.company)
            add_warehouse(row_company=row_company, warehouse_name=draft_row.source_warehouse)
            add_warehouse(row_company=row_company, warehouse_name=draft_row.target_warehouse)
            add_warehouse(row_company=row_company, warehouse_name=item_row.source_warehouse)
            add_warehouse(row_company=row_company, warehouse_name=item_row.target_warehouse)

        sorted_items = [
            items_by_key[key]
            for key in sorted(items_by_key, key=lambda value: (value[0], value[1]))
        ]
        total = len(sorted_items)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return SalesInventoryListData[WarehouseItem](
            items=sorted_items[start:end],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_reference_drafts(
        self,
        *,
        reference_type: str,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[ReferenceDraftData]:
        session = self._require_session()
        normalized_reference_type = self._normalize_reference_type(reference_type)
        self._ensure_reference_draft_table()
        offset = max(page - 1, 0) * page_size
        rows = session.execute(
            text(
                f"""
                SELECT
                    id,
                    reference_type,
                    reference_no,
                    reference_name,
                    company,
                    status,
                    scenario_tag,
                    idempotency_key,
                    created_by,
                    created_at,
                    deactivated_by,
                    deactivated_at,
                    deactivate_reason
                FROM {self._LOCAL_REFERENCE_DRAFT_TABLE}
                WHERE reference_type = :reference_type
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
                """,
            ),
            {"reference_type": normalized_reference_type, "limit": page_size, "offset": offset},
        ).mappings().all()
        total = int(
            session.execute(
                text(
                    f"SELECT COUNT(*) FROM {self._LOCAL_REFERENCE_DRAFT_TABLE} WHERE reference_type = :reference_type",
                ),
                {"reference_type": normalized_reference_type},
            ).scalar_one()
        )
        return SalesInventoryListData[ReferenceDraftData](
            items=[self._reference_draft_row_to_data(dict(row)) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def _list_reference_drafts_filtered(
        self,
        *,
        reference_type: str,
        keyword: str | None,
        company: str | None,
        disabled: bool | None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[ReferenceDraftData]:
        session = self._require_session()
        normalized_reference_type = self._normalize_reference_type(reference_type)
        normalized_company = self._text(company)
        normalized_keyword = self._text(keyword)
        self._ensure_reference_draft_table()

        clauses = ["reference_type = :reference_type"]
        params: dict[str, Any] = {"reference_type": normalized_reference_type}
        if normalized_company:
            clauses.append("company = :company")
            params["company"] = normalized_company
        if disabled is not None:
            clauses.append("status = :status")
            params["status"] = "inactive" if disabled else "active"
        if normalized_keyword:
            clauses.append("(LOWER(reference_no) LIKE :keyword OR LOWER(reference_name) LIKE :keyword)")
            params["keyword"] = f"%{normalized_keyword.lower()}%"

        where_sql = " AND ".join(clauses)
        offset = max(page - 1, 0) * page_size
        rows = session.execute(
            text(
                f"""
                SELECT
                    id,
                    reference_type,
                    reference_no,
                    reference_name,
                    company,
                    status,
                    scenario_tag,
                    idempotency_key,
                    created_by,
                    created_at,
                    deactivated_by,
                    deactivated_at,
                    deactivate_reason
                FROM {self._LOCAL_REFERENCE_DRAFT_TABLE}
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT :limit OFFSET :offset
                """,
            ),
            {**params, "limit": page_size, "offset": offset},
        ).mappings().all()
        total = int(
            session.execute(
                text(f"SELECT COUNT(*) FROM {self._LOCAL_REFERENCE_DRAFT_TABLE} WHERE {where_sql}"),
                params,
            ).scalar_one()
        )
        return SalesInventoryListData[ReferenceDraftData](
            items=[self._reference_draft_row_to_data(dict(row)) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_reference_draft(
        self,
        *,
        reference_type: str,
        payload: ReferenceDraftCreateRequest,
        created_by: str,
    ) -> ReferenceDraftData:
        session = self._require_session()
        normalized_reference_type = self._normalize_reference_type(reference_type)
        company = self._require_text(payload.company, "company")
        reference_no = self._require_text(payload.reference_no, "reference_no")
        reference_name = self._require_text(payload.reference_name, "reference_name")
        scenario_tag = self._require_text(payload.scenario_tag, "scenario_tag")
        idempotency_key = self._require_text(payload.idempotency_key, "idempotency_key")
        created_by_name = self._require_text(created_by, "created_by")
        self._ensure_reference_draft_table()

        existing_by_idempotency = session.execute(
            text(
                f"""
                SELECT * FROM {self._LOCAL_REFERENCE_DRAFT_TABLE}
                WHERE reference_type = :reference_type
                  AND company = :company
                  AND idempotency_key = :idempotency_key
                ORDER BY id DESC
                LIMIT 1
                """,
            ),
            {
                "reference_type": normalized_reference_type,
                "company": company,
                "idempotency_key": idempotency_key,
            },
        ).mappings().first()
        if existing_by_idempotency is not None:
            return self._reference_draft_row_to_data(dict(existing_by_idempotency))

        existing_active = session.execute(
            text(
                f"""
                SELECT * FROM {self._LOCAL_REFERENCE_DRAFT_TABLE}
                WHERE reference_type = :reference_type
                  AND company = :company
                  AND reference_no = :reference_no
                  AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """,
            ),
            {
                "reference_type": normalized_reference_type,
                "company": company,
                "reference_no": reference_no,
            },
        ).mappings().first()
        if existing_active is not None:
            raise SalesInventoryServiceError(
                409,
                "SALES_INVENTORY_REFERENCE_CONFLICT",
                f"{reference_no} 已存在启用中的本地草稿",
            )

        created_at = datetime.now(timezone.utc).isoformat()
        result = session.execute(
            text(
                f"""
                INSERT INTO {self._LOCAL_REFERENCE_DRAFT_TABLE} (
                    reference_type,
                    reference_no,
                    reference_name,
                    company,
                    status,
                    scenario_tag,
                    idempotency_key,
                    created_by,
                    created_at
                ) VALUES (
                    :reference_type,
                    :reference_no,
                    :reference_name,
                    :company,
                    'active',
                    :scenario_tag,
                    :idempotency_key,
                    :created_by,
                    :created_at
                )
                """,
            ),
            {
                "reference_type": normalized_reference_type,
                "reference_no": reference_no,
                "reference_name": reference_name,
                "company": company,
                "scenario_tag": scenario_tag,
                "idempotency_key": idempotency_key,
                "created_by": created_by_name,
                "created_at": created_at,
            },
        )
        session.commit()
        row = session.execute(
            text(f"SELECT * FROM {self._LOCAL_REFERENCE_DRAFT_TABLE} WHERE id = :draft_id"),
            {"draft_id": int(result.lastrowid)},
        ).mappings().one()
        return self._reference_draft_row_to_data(dict(row))

    def deactivate_reference_draft(
        self,
        *,
        reference_type: str,
        draft_id: int,
        payload: ReferenceDraftDeactivateRequest,
        deactivated_by: str,
    ) -> ReferenceDraftData:
        session = self._require_session()
        normalized_reference_type = self._normalize_reference_type(reference_type)
        company = self._require_text(payload.company, "company")
        reason = self._require_text(payload.reason, "reason")
        actor = self._require_text(deactivated_by, "deactivated_by")
        self._require_text(payload.scenario_tag, "scenario_tag")
        self._require_text(payload.idempotency_key, "idempotency_key")
        self._ensure_reference_draft_table()

        current = session.execute(
            text(
                f"""
                SELECT * FROM {self._LOCAL_REFERENCE_DRAFT_TABLE}
                WHERE id = :draft_id
                  AND reference_type = :reference_type
                  AND company = :company
                LIMIT 1
                """,
            ),
            {
                "draft_id": draft_id,
                "reference_type": normalized_reference_type,
                "company": company,
            },
        ).mappings().first()
        if current is None:
            raise SalesInventoryServiceError(
                409,
                "SALES_INVENTORY_REFERENCE_NOT_FOUND",
                "本地草稿不存在或 company 不匹配",
            )
        if str(current.get("status") or "") == "inactive":
            return self._reference_draft_row_to_data(dict(current))

        session.execute(
            text(
                f"""
                UPDATE {self._LOCAL_REFERENCE_DRAFT_TABLE}
                SET status = 'inactive',
                    deactivated_by = :deactivated_by,
                    deactivated_at = :deactivated_at,
                    deactivate_reason = :deactivate_reason
                WHERE id = :draft_id
                """,
            ),
            {
                "draft_id": draft_id,
                "deactivated_by": actor,
                "deactivated_at": datetime.now(timezone.utc).isoformat(),
                "deactivate_reason": reason,
            },
        )
        session.commit()
        updated = session.execute(
            text(f"SELECT * FROM {self._LOCAL_REFERENCE_DRAFT_TABLE} WHERE id = :draft_id"),
            {"draft_id": draft_id},
        ).mappings().one()
        return self._reference_draft_row_to_data(dict(updated))

    def get_inventory_aggregation(
        self,
        *,
        company: str | None,
        item_code: str | None,
        warehouse: str | None,
    ) -> InventoryAggregationData:
        allowed_warehouses = self._allowed_warehouses(company=company)
        rows = self._list_bin_rows(item_code=item_code, warehouse=warehouse)
        items: list[InventoryAggregationItem] = []
        for row in rows:
            row_item_code = self._text(row.get("item_code"))
            row_warehouse = self._text(row.get("warehouse"))
            if row_item_code is None or row_warehouse is None:
                continue
            if allowed_warehouses is not None and row_warehouse not in allowed_warehouses:
                continue
            actual_qty = self._decimal_or_zero(row.get("actual_qty"))
            ordered_qty = self._decimal_or_zero(row.get("ordered_qty"))
            indented_qty = self._decimal_or_zero(row.get("indented_qty"))
            safety_stock = self._decimal_or_zero(row.get("safety_stock"))
            reorder_level = self._decimal_or_zero(row.get("reorder_level"))
            items.append(
                InventoryAggregationItem(
                    item_code=row_item_code,
                    warehouse=row_warehouse,
                    actual_qty=actual_qty,
                    ordered_qty=ordered_qty,
                    indented_qty=indented_qty,
                    safety_stock=safety_stock,
                    reorder_level=reorder_level,
                    is_below_safety=safety_stock > Decimal("0") and actual_qty < safety_stock,
                    is_below_reorder=reorder_level > Decimal("0") and actual_qty < reorder_level,
                )
            )
        items.sort(key=lambda row: (row.item_code, row.warehouse))
        return InventoryAggregationData(
            company=company,
            item_code=item_code,
            warehouse=warehouse,
            items=items,
        )

    def get_sales_order_fulfillment(
        self,
        *,
        company: str | None,
        item_code: str | None,
        warehouse: str | None,
        item_name: str | None,
    ) -> SalesOrderFulfillmentData:
        aggregation = self.get_inventory_aggregation(company=company, item_code=item_code, warehouse=warehouse)
        actual_map = {
            (item.item_code, item.warehouse): item.actual_qty
            for item in aggregation.items
        }
        rows: list[SalesOrderFulfillmentItem] = []
        for order in self._list_sales_orders_all(company=company):
            sales_order = str(order.get("name") or "").strip()
            if not sales_order:
                continue
            detail = self.adapter.get_sales_order(name=sales_order)
            detail_company = self._text(detail.get("company"))
            for line in self._list_or_empty(detail.get("items")):
                line_item_code = self._text(line.get("item_code"))
                if line_item_code is None:
                    continue
                if item_code and line_item_code != item_code:
                    continue
                line_warehouse = self._text(line.get("warehouse"))
                if warehouse and line_warehouse != warehouse:
                    continue
                line_item_name = self._text(line.get("item_name"))
                if item_name and not self._contains_like(line_item_name, item_name):
                    continue
                ordered_qty = self._decimal_or_zero(line.get("qty"))
                actual_qty = actual_map.get((line_item_code, line_warehouse or ""), Decimal("0"))
                rows.append(
                    SalesOrderFulfillmentItem(
                        company=detail_company,
                        sales_order=sales_order,
                        item_code=line_item_code,
                        warehouse=line_warehouse,
                        ordered_qty=ordered_qty,
                        actual_qty=actual_qty,
                        fulfillment_rate=self._fulfillment_rate(actual_qty=actual_qty, ordered_qty=ordered_qty),
                    )
                )
        rows.sort(key=lambda row: (row.sales_order, row.item_code, row.warehouse or ""))
        return SalesOrderFulfillmentData(company=company, items=rows)

    @classmethod
    def _sales_order_list_item(cls, row: dict[str, Any]) -> SalesOrderListItem:
        return SalesOrderListItem(
            name=str(row.get("name") or ""),
            company=str(row.get("company") or ""),
            customer=cls._text(row.get("customer")),
            transaction_date=row.get("transaction_date"),
            delivery_date=row.get("delivery_date"),
            status=cls._text(row.get("status")),
            docstatus=int(row.get("docstatus")),
            grand_total=cls._decimal_or_none(row.get("grand_total")),
            currency=cls._text(row.get("currency")),
        )

    @classmethod
    def _sales_order_line_item(cls, row: dict[str, Any]) -> SalesOrderLineItem:
        return SalesOrderLineItem(
            name=cls._text(row.get("name")),
            item_code=str(row.get("item_code") or ""),
            item_name=cls._text(row.get("item_name")),
            color=cls._text(row.get("color")),
            size=cls._text(row.get("size")),
            qty=Decimal(str(row.get("qty") or "0")),
            delivered_qty=cls._decimal_or_none(row.get("delivered_qty")),
            rate=cls._decimal_or_none(row.get("rate")),
            amount=cls._decimal_or_none(row.get("amount")),
            warehouse=cls._text(row.get("warehouse")),
            delivery_date=row.get("delivery_date"),
            ys_material_calc_state=cls._text(row.get("ys_material_calc_state")) or "待算料",
        )

    _LOCAL_SALES_ORDER_SOURCE_TYPE = "sales_order_local"
    _LOCAL_REFERENCE_DRAFT_TABLE = "ly_sales_inventory_reference_draft"

    def _require_session(self) -> Session:
        if self.session is None:
            raise SalesInventoryServiceError(500, "SALES_ORDER_SESSION_UNAVAILABLE", "本地会话不可用")
        return self.session

    @classmethod
    def _require_text(cls, value: Any, field_name: str) -> str:
        normalized = cls._text(value)
        if normalized is None:
            raise SalesInventoryServiceError(409, "SALES_ORDER_IDEMPOTENCY_CONFLICT", f"{field_name} 不能为空")
        return normalized

    def _resolve_enabled_style(self, *, company: str, style_no: str) -> LyStyleMaster:
        session = self._require_session()
        row = (
            session.query(LyStyleMaster)
            .filter(LyStyleMaster.company == company, LyStyleMaster.ys_style_no == style_no)
            .first()
        )
        if row is None or str(row.ys_style_status) != "enabled":
            raise SalesInventoryServiceError(409, STYLE_MASTER_INVALID_REFERENCE, f"{style_no} 款式不存在或未启用")
        return row

    @classmethod
    def _positive_decimal(cls, value: Any, field_name: str) -> Decimal:
        numeric = cls._decimal_or_zero(value)
        if numeric <= Decimal("0"):
            raise SalesInventoryServiceError(400, "SALES_ORDER_INVALID_PAYLOAD", f"{field_name} 必须大于 0")
        return numeric

    @staticmethod
    def _parse_optional_iso_date(value: str | None) -> date | None:
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _build_sales_order_event_key(
        *,
        company: str,
        sales_order_no: str,
        source_order_ref: str,
        idempotency_key: str,
    ) -> str:
        raw = "|".join([company, sales_order_no, source_order_ref, idempotency_key]).encode("utf-8")
        return f"sow:{hashlib.sha256(raw).hexdigest()}"

    def _find_sales_order_draft(self, *, draft_id: int) -> LyWarehouseStockEntryDraft | None:
        return (
            self._require_session()
            .query(LyWarehouseStockEntryDraft)
            .filter(
                LyWarehouseStockEntryDraft.id == draft_id,
                LyWarehouseStockEntryDraft.source_type == self._LOCAL_SALES_ORDER_SOURCE_TYPE,
            )
            .first()
        )

    def _sales_order_payload_for_draft(self, *, draft_id: int) -> dict[str, Any]:
        outbox = (
            self._require_session()
            .query(LyWarehouseStockEntryOutboxEvent)
            .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
            .order_by(LyWarehouseStockEntryOutboxEvent.id.desc())
            .first()
        )
        if outbox is None or not isinstance(outbox.payload, dict):
            return {}
        return dict(outbox.payload)

    def _sales_order_draft_items(self, *, draft_id: int) -> list[SalesOrderDraftLineItemData]:
        rows = (
            self._require_session()
            .query(LyWarehouseStockEntryDraftItem)
            .filter(LyWarehouseStockEntryDraftItem.draft_id == draft_id)
            .order_by(LyWarehouseStockEntryDraftItem.id.asc())
            .all()
        )
        payload_items = self._sales_order_payload_for_draft(draft_id=draft_id).get("items")
        payload_rates: dict[int, Decimal | None] = {}
        payload_amounts: dict[int, Decimal | None] = {}
        if isinstance(payload_items, list):
            for index, payload_item in enumerate(payload_items):
                if not isinstance(payload_item, dict):
                    continue
                payload_rates[index] = self._decimal_or_none(payload_item.get("rate"))
                payload_amounts[index] = self._decimal_or_none(payload_item.get("amount"))
        items: list[SalesOrderDraftLineItemData] = []
        for index, row in enumerate(rows):
            items.append(
                SalesOrderDraftLineItemData(
                    id=int(row.id),
                    draft_id=int(row.draft_id),
                    item_code=str(row.item_code),
                    qty=Decimal(str(row.qty)),
                    rate=payload_rates.get(index),
                    amount=payload_amounts.get(index),
                    uom=str(row.uom),
                    warehouse=self._text(row.source_warehouse),
                )
            )
        return items

    def _list_outbox_events_for_draft(self, *, draft_id: int) -> list[LyWarehouseStockEntryOutboxEvent]:
        return (
            self._require_session()
            .query(LyWarehouseStockEntryOutboxEvent)
            .filter(LyWarehouseStockEntryOutboxEvent.draft_id == draft_id)
            .all()
        )

    def _build_sales_order_draft_data(self, draft: LyWarehouseStockEntryDraft) -> SalesOrderDraftData:
        payload = self._sales_order_payload_for_draft(draft_id=int(draft.id))
        transaction_date = self._parse_optional_iso_date(self._text(payload.get("transaction_date")))
        delivery_date = self._parse_optional_iso_date(self._text(payload.get("delivery_date")))
        scenario_tag = self._text(payload.get("scenario_tag")) or ""
        return SalesOrderDraftData(
            id=int(draft.id),
            sales_order_no=self._text(payload.get("sales_order_no")) or str(draft.source_id),
            source_order_ref=str(draft.source_id),
            company=str(draft.company),
            customer=self._text(payload.get("customer")),
            status=str(draft.status),  # type: ignore[arg-type]
            transaction_date=transaction_date,
            delivery_date=delivery_date,
            currency=self._text(payload.get("currency")) or "CNY",
            grand_total=self._decimal_or_none(payload.get("grand_total")),
            idempotency_key=str(draft.idempotency_key),
            scenario_tag=scenario_tag,
            created_by=str(draft.created_by),
            created_at=draft.created_at,
            cancelled_by=self._text(draft.cancelled_by),
            cancelled_at=draft.cancelled_at,
            cancel_reason=self._text(draft.cancel_reason),
            items=self._sales_order_draft_items(draft_id=int(draft.id)),
        )

    def _native_sales_order_items(self, *, order_id: int) -> list[LySalesOrderItem]:
        return (
            self._require_session()
            .query(LySalesOrderItem)
            .filter(LySalesOrderItem.sales_order_id == int(order_id))
            .order_by(LySalesOrderItem.line_no.asc(), LySalesOrderItem.id.asc())
            .all()
        )

    @staticmethod
    def _material_calc_state_from_items(items: list[LySalesOrderItem]) -> str:
        if items and all(str(item.ys_material_calc_state or "") == "已算料" for item in items):
            return "已算料"
        return "待算料"

    @classmethod
    def _native_status_display(cls, status: Any) -> str:
        normalized = (str(status or "")).strip().lower()
        if normalized == "cancelled":
            return "Cancelled"
        if normalized == "planned":
            return "生产计划"
        return "Draft"

    @classmethod
    def _native_draft_status(cls, status: Any) -> str:
        return "cancelled" if (str(status or "").strip().lower() == "cancelled") else "draft"

    def _build_native_sales_order_list_item(self, order: LySalesOrder) -> SalesOrderListItem:
        items = self._native_sales_order_items(order_id=int(order.id))
        return SalesOrderListItem(
            name=str(order.sales_order_no),
            company=str(order.company),
            customer=self._text(order.customer),
            transaction_date=order.transaction_date,
            delivery_date=order.delivery_date,
            status=self._native_status_display(order.status),
            docstatus=int(order.docstatus or 0),
            grand_total=Decimal(str(order.grand_total or 0)),
            currency=self._text(order.currency) or "CNY",
            ys_material_calc_state=self._material_calc_state_from_items(items),
        )

    def _build_native_sales_order_detail(self, order: LySalesOrder) -> SalesOrderDetailData:
        items = self._native_sales_order_items(order_id=int(order.id))
        return SalesOrderDetailData(
            name=str(order.sales_order_no),
            company=str(order.company),
            customer=self._text(order.customer),
            transaction_date=order.transaction_date,
            delivery_date=order.delivery_date,
            status=self._native_status_display(order.status),
            docstatus=int(order.docstatus or 0),
            grand_total=Decimal(str(order.grand_total or 0)),
            currency=self._text(order.currency) or "CNY",
            ys_material_calc_state=self._material_calc_state_from_items(items),
            items=[
                SalesOrderLineItem(
                    name=str(item.sales_order_item),
                    item_code=str(item.item_code),
                    item_name=self._text(item.item_name) or str(item.item_code),
                    color=self._text(item.color),
                    size=self._text(item.size),
                    qty=Decimal(str(item.qty)),
                    delivered_qty=Decimal(str(item.delivered_qty or 0)),
                    rate=self._decimal_or_none(item.rate),
                    amount=self._decimal_or_none(item.amount),
                    warehouse=self._text(item.warehouse),
                    delivery_date=item.delivery_date or order.delivery_date,
                    ys_material_calc_state=self._text(item.ys_material_calc_state) or "待算料",
                )
                for item in items
            ],
        )

    def _build_native_sales_order_draft_data(self, order: LySalesOrder) -> SalesOrderDraftData:
        items = self._native_sales_order_items(order_id=int(order.id))
        return SalesOrderDraftData(
            id=int(order.id),
            sales_order_no=str(order.sales_order_no),
            source_order_ref=self._text(order.source_order_ref) or str(order.sales_order_no),
            company=str(order.company),
            customer=self._text(order.customer),
            status=self._native_draft_status(order.status),  # type: ignore[arg-type]
            transaction_date=order.transaction_date,
            delivery_date=order.delivery_date,
            currency=self._text(order.currency) or "CNY",
            grand_total=Decimal(str(order.grand_total or 0)),
            idempotency_key=str(order.idempotency_key),
            scenario_tag=self._text(order.scenario_tag) or "",
            created_by=str(order.created_by),
            created_at=order.created_at,
            cancelled_by=self._text(order.cancelled_by),
            cancelled_at=order.cancelled_at,
            cancel_reason=self._text(order.cancel_reason),
            items=[
                SalesOrderDraftLineItemData(
                    id=int(item.id),
                    draft_id=int(order.id),
                    item_code=str(item.item_code),
                    item_name=self._text(item.item_name) or str(item.item_code),
                    color=self._text(item.color),
                    size=self._text(item.size),
                    qty=Decimal(str(item.qty)),
                    rate=self._decimal_or_none(item.rate),
                    amount=self._decimal_or_none(item.amount),
                    uom=str(item.uom),
                    warehouse=self._text(item.warehouse),
                    ys_material_calc_state=self._text(item.ys_material_calc_state) or "待算料",
                )
                for item in items
            ],
        )

    @staticmethod
    def _native_sales_order_request_hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _sales_order_draft_response_json(response: SalesOrderDraftData) -> dict[str, Any]:
        if hasattr(response, "model_dump"):
            return response.model_dump(mode="json")
        return json.loads(response.json())

    def _next_sales_order_no(self, *, company: str) -> str:
        today = date.today().strftime("%Y%m%d")
        prefix = f"SO-{today}-"
        latest = (
            self._require_session()
            .query(LySalesOrder)
            .filter(
                LySalesOrder.company == company,
                LySalesOrder.sales_order_no.like(f"{prefix}%"),
            )
            .order_by(LySalesOrder.id.desc())
            .first()
        )
        next_seq = 1
        if latest is not None:
            tail = str(latest.sales_order_no).replace(prefix, "", 1)
            if tail.isdigit():
                next_seq = int(tail) + 1
        return f"{prefix}{next_seq:03d}"

    @staticmethod
    def _delivery_invoice_request_hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _sales_payment_entry_request_hash(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _next_delivery_note(self, *, company: str, posting_date: date) -> str:
        prefix = f"DN-{posting_date.strftime('%Y%m%d')}-"
        latest = (
            self._require_session()
            .query(LyDeliveryInvoice)
            .filter(
                LyDeliveryInvoice.company == company,
                LyDeliveryInvoice.delivery_note.like(f"{prefix}%"),
            )
            .order_by(LyDeliveryInvoice.id.desc())
            .first()
        )
        return f"{prefix}{self._next_numeric_tail(latest.delivery_note if latest is not None else None, prefix):03d}"

    def _next_sales_invoice(self, *, company: str, posting_date: date) -> str:
        prefix = f"SI-{posting_date.strftime('%Y%m%d')}-"
        latest = (
            self._require_session()
            .query(LyDeliveryInvoice)
            .filter(
                LyDeliveryInvoice.company == company,
                LyDeliveryInvoice.sales_invoice.like(f"{prefix}%"),
            )
            .order_by(LyDeliveryInvoice.id.desc())
            .first()
        )
        return f"{prefix}{self._next_numeric_tail(latest.sales_invoice if latest is not None else None, prefix):03d}"

    def _next_sales_payment_entry(self, *, company: str, posting_date: date) -> str:
        prefix = f"PE-{posting_date.strftime('%Y%m%d')}-"
        latest = (
            self._require_session()
            .query(LySalesPaymentEntry)
            .filter(
                LySalesPaymentEntry.company == company,
                LySalesPaymentEntry.payment_entry.like(f"{prefix}%"),
            )
            .order_by(LySalesPaymentEntry.id.desc())
            .first()
        )
        return f"{prefix}{self._next_numeric_tail(latest.payment_entry if latest is not None else None, prefix):03d}"

    @staticmethod
    def _next_numeric_tail(value: Any, prefix: str) -> int:
        if value is None:
            return 1
        tail = str(value).replace(prefix, "", 1)
        if tail.isdigit():
            return int(tail) + 1
        return 1

    def _query_local_delivery_invoices(
        self,
        *,
        company: str | None,
        sales_order: str | None,
        customer: str | None,
        item_code: str | None,
        warehouse: str | None,
        status: str | None,
        keyword: str | None,
    ) -> list[LyDeliveryInvoice]:
        session = self._require_session()
        query = session.query(LyDeliveryInvoice)
        normalized_company = self._text(company)
        normalized_sales_order = self._text(sales_order)
        normalized_customer = self._text(customer)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_status = self._text(status)
        if normalized_company:
            query = query.filter(LyDeliveryInvoice.company == normalized_company)
        if normalized_sales_order:
            query = query.filter(LyDeliveryInvoice.sales_order == normalized_sales_order)
        if normalized_customer:
            query = query.filter(LyDeliveryInvoice.customer == normalized_customer)
        if normalized_item_code:
            query = query.filter(LyDeliveryInvoice.item_code == normalized_item_code)
        if normalized_warehouse:
            query = query.filter(LyDeliveryInvoice.warehouse == normalized_warehouse)
        if normalized_status:
            query = query.filter(LyDeliveryInvoice.status == normalized_status)
        rows = query.order_by(LyDeliveryInvoice.id.desc()).all()
        normalized_keyword = self._text(keyword)
        if normalized_keyword:
            rows = [
                row
                for row in rows
                if self._contains_like(
                    " ".join(
                        [
                            str(row.delivery_note),
                            str(row.sales_invoice),
                            str(row.sales_order),
                            self._text(row.customer) or "",
                            str(row.item_code),
                            str(row.warehouse),
                        ]
                    ),
                    normalized_keyword,
                )
            ]
        return rows

    def _query_local_payment_entries(
        self,
        *,
        company: str | None,
        sales_invoice: str | None,
        customer: str | None,
        status: str | None,
        keyword: str | None,
    ) -> list[LySalesPaymentEntry]:
        session = self._require_session()
        query = session.query(LySalesPaymentEntry)
        normalized_company = self._text(company)
        normalized_sales_invoice = self._text(sales_invoice)
        normalized_customer = self._text(customer)
        normalized_status = self._text(status)
        if normalized_company:
            query = query.filter(LySalesPaymentEntry.company == normalized_company)
        if normalized_sales_invoice:
            query = query.filter(LySalesPaymentEntry.sales_invoice == normalized_sales_invoice)
        if normalized_customer:
            query = query.filter(LySalesPaymentEntry.customer == normalized_customer)
        if normalized_status:
            query = query.filter(LySalesPaymentEntry.status == normalized_status)
        rows = query.order_by(LySalesPaymentEntry.id.desc()).all()
        normalized_keyword = self._text(keyword)
        if normalized_keyword:
            rows = [
                row
                for row in rows
                if self._contains_like(
                    " ".join(
                        [
                            str(row.payment_entry),
                            str(row.sales_invoice),
                            str(row.delivery_note),
                            str(row.sales_order),
                            self._text(row.customer) or "",
                            str(row.mode_of_payment),
                            self._text(row.reference_no) or "",
                        ]
                    ),
                    normalized_keyword,
                )
            ]
        return rows

    def _build_delivery_invoice_data(self, row: LyDeliveryInvoice) -> DeliveryInvoiceData:
        return DeliveryInvoiceData(
            id=int(row.id),
            company=str(row.company),
            delivery_note=str(row.delivery_note),
            sales_invoice=str(row.sales_invoice),
            sales_order=str(row.sales_order),
            customer=self._text(row.customer),
            item_code=str(row.item_code),
            item_name=self._text(row.item_name),
            warehouse=str(row.warehouse),
            delivered_qty=Decimal(str(row.delivered_qty)),
            uom=str(row.uom),
            rate=self._decimal_or_none(row.rate),
            grand_total=Decimal(str(row.grand_total or 0)),
            paid_amount=Decimal(str(row.paid_amount or 0)),
            outstanding_amount=Decimal(str(row.outstanding_amount or 0)),
            posting_date=row.posting_date,
            due_date=row.due_date,
            status=str(row.status),  # type: ignore[arg-type]
            docstatus=int(row.docstatus or 0),
            source_ref=str(row.source_ref),
            idempotency_key=str(row.idempotency_key),
            scenario_tag=self._text(row.scenario_tag),
            warehouse_draft_id=int(row.warehouse_draft_id) if row.warehouse_draft_id is not None else None,
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    def _build_sales_payment_entry_data(self, row: LySalesPaymentEntry) -> SalesPaymentEntryData:
        return SalesPaymentEntryData(
            id=int(row.id),
            company=str(row.company),
            payment_entry=str(row.payment_entry),
            delivery_invoice_id=int(row.delivery_invoice_id),
            delivery_note=str(row.delivery_note),
            sales_invoice=str(row.sales_invoice),
            sales_order=str(row.sales_order),
            customer=self._text(row.customer),
            posting_date=row.posting_date,
            paid_amount=Decimal(str(row.paid_amount)),
            allocated_amount=Decimal(str(row.allocated_amount)),
            outstanding_before=Decimal(str(row.outstanding_before)),
            outstanding_after=Decimal(str(row.outstanding_after)),
            mode_of_payment=str(row.mode_of_payment),
            reference_no=self._text(row.reference_no),
            reference_date=row.reference_date,
            status=str(row.status),  # type: ignore[arg-type]
            docstatus=int(row.docstatus or 0),
            source_ref=str(row.source_ref),
            idempotency_key=str(row.idempotency_key),
            scenario_tag=self._text(row.scenario_tag),
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

    def _assert_local_stock_available(
        self,
        *,
        company: str,
        item_code: str,
        warehouse: str,
        required_qty: Decimal,
    ) -> None:
        balance = self._local_stock_balance(company=company, item_code=item_code, warehouse=warehouse)
        if balance < required_qty:
            raise SalesInventoryServiceError(
                409,
                "SALES_DELIVERY_INVOICE_STOCK_SHORTAGE",
                f"库存不足：{warehouse}/{item_code} 当前 {balance}，需发 {required_qty}",
            )

    def _local_stock_balance(self, *, company: str, item_code: str, warehouse: str) -> Decimal:
        session = self._require_session()
        rows = (
            session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
            .join(
                LyWarehouseStockEntryDraftItem,
                LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id,
            )
            .filter(
                LyWarehouseStockEntryDraft.company == company,
                LyWarehouseStockEntryDraft.status != "cancelled",
                LyWarehouseStockEntryDraftItem.item_code == item_code,
            )
            .all()
        )
        balance = Decimal("0")
        for draft, item in rows:
            qty = Decimal(str(item.qty or 0))
            purpose = str(draft.purpose)
            source_warehouse = self._text(item.source_warehouse) or self._text(draft.source_warehouse)
            target_warehouse = self._text(item.target_warehouse) or self._text(draft.target_warehouse)
            if purpose == "Material Issue":
                if source_warehouse == warehouse:
                    balance -= qty
            elif purpose == "Material Transfer":
                if source_warehouse == warehouse:
                    balance -= qty
                if target_warehouse == warehouse:
                    balance += qty
            elif target_warehouse == warehouse:
                balance += qty
        return balance

    def _increase_native_sales_order_delivered_qty(
        self,
        *,
        company: str,
        sales_order: str,
        item_code: str,
        warehouse: str,
        delivered_qty: Decimal,
    ) -> None:
        order = (
            self._require_session()
            .query(LySalesOrder)
            .filter(
                LySalesOrder.company == company,
                (LySalesOrder.sales_order_no == sales_order) | (LySalesOrder.source_order_ref == sales_order),
            )
            .order_by(LySalesOrder.id.desc())
            .first()
        )
        if order is None:
            raise SalesInventoryServiceError(404, "SALES_DELIVERY_ORDER_NOT_FOUND", "销售订单不存在")
        candidates = [
            item
            for item in self._native_sales_order_items(order_id=int(order.id))
            if str(item.item_code) == item_code and (self._text(item.warehouse) in {None, warehouse})
        ]
        if not candidates:
            raise SalesInventoryServiceError(409, "SALES_DELIVERY_INVOICE_CONFLICT", "销售订单未包含该发货物料")
        line = candidates[0]
        next_delivered = Decimal(str(line.delivered_qty or 0)) + delivered_qty
        ordered_qty = Decimal(str(line.qty or 0))
        if next_delivered > ordered_qty:
            raise SalesInventoryServiceError(409, "SALES_DELIVERY_INVOICE_QTY_EXCEEDED", "发货数量超过销售订单未发数量")
        line.delivered_qty = next_delivered
        order.updated_at = datetime.now(timezone.utc)

    def _create_delivery_stock_issue(
        self,
        *,
        company: str,
        delivery_note: str,
        sales_invoice: str,
        sales_order: str,
        item_code: str,
        delivered_qty: Decimal,
        uom: str,
        warehouse: str,
        posting_date: date,
        idempotency_key: str,
        current_user: str,
    ) -> LyWarehouseStockEntryDraft:
        session = self._require_session()
        stock_idempotency_key = f"delivery:{idempotency_key}"
        existing = (
            session.query(LyWarehouseStockEntryDraft)
            .filter(
                LyWarehouseStockEntryDraft.company == company,
                LyWarehouseStockEntryDraft.idempotency_key == stock_idempotency_key,
            )
            .first()
        )
        if existing is not None:
            return existing
        event_key = self._build_delivery_stock_event_key(
            company=company,
            delivery_note=delivery_note,
            sales_invoice=sales_invoice,
            idempotency_key=idempotency_key,
        )
        now = datetime.now(timezone.utc)
        draft = LyWarehouseStockEntryDraft(
            company=company,
            purpose="Material Issue",
            source_type="sales_delivery_invoice",
            source_id=delivery_note,
            source_warehouse=warehouse,
            target_warehouse=None,
            status="pending_outbox",
            created_by=current_user,
            created_at=now,
            idempotency_key=stock_idempotency_key,
            event_key=event_key,
        )
        session.add(draft)
        session.flush()
        session.add(
            LyWarehouseStockEntryDraftItem(
                draft_id=int(draft.id),
                company=company,
                item_code=item_code,
                qty=delivered_qty,
                uom=uom,
                batch_no=None,
                serial_no=None,
                source_warehouse=warehouse,
                target_warehouse=None,
            )
        )
        session.add(
            LyWarehouseStockEntryOutboxEvent(
                draft_id=int(draft.id),
                event_type="sales_delivery_issue_sync",
                event_key=event_key,
                payload={
                    "business_date": posting_date.isoformat(),
                    "delivery_note": delivery_note,
                    "sales_invoice": sales_invoice,
                    "sales_order": sales_order,
                    "company": company,
                    "item_code": item_code,
                    "warehouse": warehouse,
                    "delivered_qty": str(delivered_qty),
                },
                status="in_pending",
                retry_count=0,
                external_ref=None,
                error_message=None,
                created_at=now,
                processed_at=None,
            )
        )
        session.flush()
        return draft

    @staticmethod
    def _build_delivery_stock_event_key(
        *,
        company: str,
        delivery_note: str,
        sales_invoice: str,
        idempotency_key: str,
    ) -> str:
        raw = "|".join([company, delivery_note, sales_invoice, idempotency_key]).encode("utf-8")
        return f"sdi:{hashlib.sha256(raw).hexdigest()}"

    @staticmethod
    def _is_missing_native_sales_order_table(exc: BaseException) -> bool:
        message = str(exc).lower()
        return "ly_sales_order" in message and ("no such table" in message or "does not exist" in message)

    @staticmethod
    def _is_missing_legacy_sales_order_table(exc: BaseException) -> bool:
        message = str(exc).lower()
        return "ly_warehouse_stock_entry" in message and ("no such table" in message or "does not exist" in message)

    @classmethod
    def _normalize_reference_type(cls, value: str) -> str:
        normalized = cls._require_text(value, "reference_type").lower()
        if normalized not in {"customer", "supplier"}:
            raise SalesInventoryServiceError(409, "SALES_INVENTORY_REFERENCE_CONFLICT", "reference_type 非法")
        return normalized

    @classmethod
    def _parse_optional_iso_datetime(cls, value: Any) -> datetime | None:
        normalized = cls._text(value)
        if normalized is None:
            return None
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    @classmethod
    def _reference_draft_row_to_data(cls, row: dict[str, Any]) -> ReferenceDraftData:
        reference_type = cls._normalize_reference_type(str(row.get("reference_type") or ""))
        status = str(row.get("status") or "inactive")
        if status not in {"active", "inactive"}:
            status = "inactive"
        return ReferenceDraftData(
            id=int(row.get("id") or 0),
            reference_type=reference_type,  # type: ignore[arg-type]
            reference_no=str(row.get("reference_no") or ""),
            reference_name=str(row.get("reference_name") or ""),
            company=str(row.get("company") or ""),
            status=status,  # type: ignore[arg-type]
            scenario_tag=str(row.get("scenario_tag") or ""),
            idempotency_key=str(row.get("idempotency_key") or ""),
            created_by=str(row.get("created_by") or ""),
            created_at=cls._parse_optional_iso_datetime(row.get("created_at")) or datetime.now(timezone.utc),
            deactivated_by=cls._text(row.get("deactivated_by")),
            deactivated_at=cls._parse_optional_iso_datetime(row.get("deactivated_at")),
            deactivate_reason=cls._text(row.get("deactivate_reason")),
        )

    def _ensure_reference_draft_table(self) -> None:
        session = self._require_session()
        session.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {self._LOCAL_REFERENCE_DRAFT_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference_type TEXT NOT NULL,
                    reference_no TEXT NOT NULL,
                    reference_name TEXT NOT NULL,
                    company TEXT NOT NULL,
                    status TEXT NOT NULL,
                    scenario_tag TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    deactivated_by TEXT,
                    deactivated_at TEXT,
                    deactivate_reason TEXT
                )
                """,
            )
        )
        session.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_{self._LOCAL_REFERENCE_DRAFT_TABLE}_idem
                ON {self._LOCAL_REFERENCE_DRAFT_TABLE} (reference_type, company, idempotency_key)
                """,
            )
        )
        session.commit()

    def _allowed_warehouses(self, *, company: str | None) -> set[str] | None:
        if not company:
            return None
        rows: list[dict[str, Any]] = []
        page = 1
        page_size = 200
        while True:
            chunk, _ = self.adapter.list_warehouses(company=company, page=page, page_size=page_size)
            if not chunk:
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
            if page > 100:
                break
        return {
            warehouse_name
            for row in rows
            if (warehouse_name := self._text(row.get("name"))) is not None
        }

    def _list_bin_rows(self, *, item_code: str | None, warehouse: str | None) -> list[dict[str, Any]]:
        filters: list[list[Any]] = []
        if item_code:
            filters.append(["item_code", "=", item_code])
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        rows: list[dict[str, Any]] = []
        page = 1
        page_size = 500
        while True:
            chunk = self.adapter._list_resource(  # noqa: SLF001 - read-only adapter pagination reuse.
                doctype="Bin",
                fields=self.BIN_FIELDS,
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="item_code asc, warehouse asc",
            )
            if not chunk:
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
            if page > 100:
                break
        return rows

    def _list_sales_orders_all(self, *, company: str | None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page = 1
        page_size = 200
        while True:
            chunk, _ = self.adapter.list_sales_orders(
                company=company,
                customer=None,
                item_code=None,
                item_name=None,
                from_date=None,
                to_date=None,
                page=page,
                page_size=page_size,
            )
            if not chunk:
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
            if page > 100:
                break
        return rows

    @staticmethod
    def _list_or_empty(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None or str(value).strip() == "":
            return None
        return Decimal(str(value))

    @staticmethod
    def _decimal_or_zero(value: Any) -> Decimal:
        if value is None or str(value).strip() == "":
            return Decimal("0")
        return Decimal(str(value))

    @staticmethod
    def _fulfillment_rate(*, actual_qty: Decimal, ordered_qty: Decimal) -> Decimal:
        if ordered_qty <= Decimal("0"):
            return Decimal("0")
        rate = actual_qty / ordered_qty
        if rate < Decimal("0"):
            return Decimal("0")
        return rate if rate <= Decimal("1") else Decimal("1")

    @staticmethod
    def _contains_like(value: str | None, keyword: str) -> bool:
        if value is None:
            return False
        return keyword.lower() in value.lower()

    @staticmethod
    def _bool_or_none(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        text = str(value).strip().lower()
        if text in {"1", "true", "yes"}:
            return True
        if text in {"0", "false", "no"}:
            return False
        return None
