"""B1 FastAPI-native finished-goods delivery receivable closed flow."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.quality import Base as QualityBase
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LyDeliveryInvoiceOperation
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.sales_order import LySalesPaymentEntry
from app.models.sales_order import LySalesPaymentEntryOperation
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep


class SalesFinishedGoodsInvoicePaymentFlowTest(unittest.TestCase):
    """Validate B1 public APIs close finished goods -> delivery invoice -> payment."""

    STOCK_TAG = "Z003-WAREHOUSE-20260617-201"
    COMPANY = "COMP-B1"
    CUSTOMER = "CUST-B1"
    ITEM_CODE = "FG-B1-CLOSED"
    WAREHOUSE = "WH-B1-FG"
    SALES_ORDER = "SO-B1-CLOSED"
    DELIVERY_NOTE = "DN-B1-CLOSED"
    SALES_INVOICE = "SI-B1-CLOSED"
    BUSINESS_DATE = "2026-06-17"

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        StyleMasterBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LySalesPaymentEntry).delete()
            session.query(LyDeliveryInvoiceOperation).delete()
            session.query(LyDeliveryInvoice).delete()
            session.query(LySalesOrderIdempotency).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyStyleMaster).delete()
            session.query(LyWarehouseStockLedgerEntry).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.add(
                LyStyleMaster(
                    company=self.COMPANY,
                    ys_style_no=self.ITEM_CODE,
                    ys_style_name_cn="B1 Closed Tee",
                    ys_season="SS",
                    ys_year="2026",
                    ys_brand="LY",
                    ys_style_status="enabled",
                    colors=[],
                    sizes=[],
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

    @staticmethod
    def _carrier_code(value: object, *, length: int = 3) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-length:]

    @staticmethod
    def _decimal_text(value: object) -> str:
        normalized = format(Decimal(str(value)).normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return normalized or "0"

    @classmethod
    def _stock_request_id(cls, payload: dict[str, object]) -> str:
        return "-".join(
            [
                cls.STOCK_TAG,
                "RW",
                "C",
                cls._carrier_code(payload["idempotency_key"]),
                cls._carrier_code(payload["source_ref"]),
                cls._carrier_code(payload["warehouse"]),
                cls._carrier_code(payload["item_code"]),
                cls._carrier_code(cls._decimal_text(payload["quantity"])),
                cls._carrier_code(payload["business_date"]),
                cls._carrier_code("C"),
            ]
        )

    @staticmethod
    def _headers(request_id: str = "req-b1-closed-flow") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "b1.closed.flow",
            "X-LY-Dev-Roles": "System Manager",
            "X-Request-ID": request_id,
        }

    @classmethod
    def _sales_order_payload(cls) -> dict[str, object]:
        return {
            "company": cls.COMPANY,
            "customer": cls.CUSTOMER,
            "operation": "create_draft",
            "sales_order_no": cls.SALES_ORDER,
            "source_order_ref": cls.SALES_ORDER,
            "idempotency_key": "idem-b1-sales-order",
            "transaction_date": cls.BUSINESS_DATE,
            "delivery_date": "2026-06-30",
            "currency": "CNY",
            "items": [
                {
                    "item_code": cls.ITEM_CODE,
                    "item_name": "B1 Closed Tee",
                    "qty": 10,
                    "rate": 80,
                    "uom": "件",
                    "warehouse": cls.WAREHOUSE,
                }
            ],
        }

    @classmethod
    def _finished_goods_payload(cls, *, qty: str = "10") -> dict[str, object]:
        source_id = f"{cls.STOCK_TAG}:finished-goods:FGI-B1-CLOSED"
        return {
            "company": cls.COMPANY,
            "purpose": "Material Receipt",
            "source_type": "manual",
            "source_id": source_id,
            "source_ref": source_id,
            "warehouse": cls.WAREHOUSE,
            "item_code": cls.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": qty,
            "business_date": cls.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": cls.STOCK_TAG,
            "finished_goods_source_id": source_id,
            "source_warehouse": None,
            "target_warehouse": cls.WAREHOUSE,
            "idempotency_key": f"{cls.STOCK_TAG}:fg-inbound:idempotency",
            "items": [
                {
                    "item_code": cls.ITEM_CODE,
                    "qty": qty,
                    "uom": "件",
                    "batch_no": None,
                    "serial_no": None,
                    "source_warehouse": None,
                    "target_warehouse": cls.WAREHOUSE,
                }
            ],
        }

    @classmethod
    def _delivery_payload(cls) -> dict[str, object]:
        return {
            "company": cls.COMPANY,
            "sales_order": cls.SALES_ORDER,
            "customer": cls.CUSTOMER,
            "item_code": cls.ITEM_CODE,
            "item_name": "B1 Closed Tee",
            "warehouse": cls.WAREHOUSE,
            "delivered_qty": 4,
            "uom": "件",
            "rate": 80,
            "posting_date": cls.BUSINESS_DATE,
            "due_date": "2026-07-17",
            "delivery_note": cls.DELIVERY_NOTE,
            "sales_invoice": cls.SALES_INVOICE,
            "source_ref": "SRC-B1-DELIVERY",
            "idempotency_key": "idem-b1-delivery-invoice",
            "operation": "create_delivery_invoice",
        }

    @classmethod
    def _payment_payload(cls, *, amount: int, suffix: str) -> dict[str, object]:
        return {
            "company": cls.COMPANY,
            "sales_invoice": cls.SALES_INVOICE,
            "customer": cls.CUSTOMER,
            "posting_date": cls.BUSINESS_DATE,
            "paid_amount": amount,
            "mode_of_payment": "Bank Transfer",
            "reference_no": f"BANK-B1-{suffix}",
            "reference_date": cls.BUSINESS_DATE,
            "payment_entry": f"PE-B1-{suffix}",
            "source_ref": f"SRC-B1-PAY-{suffix}",
            "idempotency_key": f"idem-b1-payment-{suffix}",
            "operation": "create_payment_entry",
        }

    @classmethod
    def _delivery_cancel_payload(cls, **overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "company": cls.COMPANY,
            "delivery_note": cls.DELIVERY_NOTE,
            "sales_invoice": cls.SALES_INVOICE,
            "reason": "cancel delivery invoice",
            "idempotency_key": "idem-b1-delivery-invoice-cancel",
            "operation": "cancel_delivery_invoice",
        }
        payload.update(overrides)
        return payload

    @classmethod
    def _payment_cancel_payload(cls, **overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "company": cls.COMPANY,
            "sales_invoice": cls.SALES_INVOICE,
            "reason": "cancel sales payment",
            "idempotency_key": "idem-b1-payment-cancel",
            "operation": "cancel_payment_entry",
        }
        payload.update(overrides)
        return payload

    def test_finished_goods_delivery_invoice_payment_public_api_flow(self) -> None:
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json=self._sales_order_payload(),
        )
        self.assertEqual(order.status_code, 201, order.text)

        inbound_payload = self._finished_goods_payload()
        inbound = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(self._stock_request_id(inbound_payload)),
            json=inbound_payload,
        )
        self.assertEqual(inbound.status_code, 201, inbound.text)
        self.assertEqual(inbound.json()["data"]["source_type"], "finished_goods_inbound")

        delivery = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._delivery_payload(),
        )
        self.assertEqual(delivery.status_code, 201, delivery.text)
        self.assertEqual(Decimal(str(delivery.json()["data"]["outstanding_amount"])), Decimal("320.000000"))

        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.ITEM_CODE}",
            headers=self._headers(),
        )
        self.assertEqual(ledger.status_code, 200, ledger.text)
        ledger_rows = ledger.json()["data"]["items"]
        self.assertEqual([Decimal(str(row["actual_qty"])) for row in ledger_rows], [Decimal("10.000000"), Decimal("-4.000000")])
        self.assertEqual(Decimal(str(ledger_rows[-1]["qty_after_transaction"])), Decimal("6.000000"))

        partial_payment = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payment_payload(amount=120, suffix="001"),
        )
        self.assertEqual(partial_payment.status_code, 201, partial_payment.text)
        self.assertEqual(Decimal(str(partial_payment.json()["data"]["outstanding_after"])), Decimal("200.000000"))

        final_payment = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payment_payload(amount=200, suffix="002"),
        )
        self.assertEqual(final_payment.status_code, 201, final_payment.text)
        self.assertEqual(Decimal(str(final_payment.json()["data"]["outstanding_after"])), Decimal("0.000000"))

        receivables = self.client.get(
            f"/api/sales-inventory/sales-invoices?sales_order={self.SALES_ORDER}",
            headers=self._headers(),
        )
        self.assertEqual(receivables.status_code, 200, receivables.text)
        invoice = receivables.json()["data"]["items"][0]
        self.assertEqual(invoice["status"], "paid")
        self.assertEqual(Decimal(str(invoice["paid_amount"])), Decimal("320.000000"))
        self.assertEqual(Decimal(str(invoice["outstanding_amount"])), Decimal("0.000000"))

        final_payment_id = final_payment.json()["data"]["id"]
        cancelled_payment = self.client.post(
            f"/api/sales-inventory/payment-entries/{final_payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(),
        )
        replay_cancelled_payment = self.client.post(
            f"/api/sales-inventory/payment-entries/{final_payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(),
        )
        conflict_cancelled_payment = self.client.post(
            f"/api/sales-inventory/payment-entries/{final_payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(reason="changed reason"),
        )
        reopened_receivables = self.client.get(
            f"/api/sales-inventory/sales-invoices?sales_order={self.SALES_ORDER}",
            headers=self._headers(),
        )

        self.assertEqual(cancelled_payment.status_code, 200, cancelled_payment.text)
        self.assertEqual(replay_cancelled_payment.status_code, 200, replay_cancelled_payment.text)
        self.assertEqual(cancelled_payment.json()["data"]["id"], replay_cancelled_payment.json()["data"]["id"])
        self.assertEqual(cancelled_payment.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled_payment.json()["data"]["docstatus"], 2)
        self.assertEqual(cancelled_payment.json()["data"]["financial_ledger_status"], "cancelled")
        self.assertEqual(conflict_cancelled_payment.status_code, 409)
        self.assertEqual(conflict_cancelled_payment.json()["code"], "SALES_PAYMENT_ENTRY_CONFLICT")
        self.assertEqual(reopened_receivables.status_code, 200, reopened_receivables.text)
        reopened_invoice = reopened_receivables.json()["data"]["items"][0]
        self.assertEqual(reopened_invoice["status"], "partly_paid")
        self.assertEqual(Decimal(str(reopened_invoice["paid_amount"])), Decimal("120.000000"))
        self.assertEqual(Decimal(str(reopened_invoice["outstanding_amount"])), Decimal("200.000000"))
        self.assertEqual(reopened_invoice["financial_ledger_status"], "partial")
        self.assertEqual(Decimal(str(reopened_invoice["financial_ledger_cash_in_amount"])), Decimal("120.000000"))
        self.assertEqual(Decimal(str(reopened_invoice["financial_ledger_outstanding_amount"])), Decimal("200.000000"))

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyDeliveryInvoice).count(), 1)
            self.assertEqual(session.query(LySalesPaymentEntry).count(), 2)
            self.assertEqual(session.query(LySalesPaymentEntryOperation).count(), 1)
            invoice_row = session.query(LyDeliveryInvoice).one()
            self.assertEqual(str(invoice_row.status), "partly_paid")
            self.assertEqual(Decimal(str(invoice_row.paid_amount)), Decimal("120.000000"))
            self.assertEqual(Decimal(str(invoice_row.outstanding_amount)), Decimal("200.000000"))
            drafts = session.query(LyWarehouseStockEntryDraft).order_by(LyWarehouseStockEntryDraft.id.asc()).all()
            self.assertEqual([str(row.purpose) for row in drafts], ["Material Receipt", "Material Issue"])
            self.assertEqual([str(row.source_type) for row in drafts], ["finished_goods_inbound", "sales_delivery_invoice"])
            self.assertEqual({row.action for row in session.query(LyOperationAuditLog).all()}, {"sales_inventory:write", "warehouse:stock_entry_draft"})

    def test_cancel_delivery_invoice_reverses_stock_and_sales_order_delivery(self) -> None:
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json=self._sales_order_payload(),
        )
        self.assertEqual(order.status_code, 201, order.text)
        inbound_payload = self._finished_goods_payload()
        inbound = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(self._stock_request_id(inbound_payload)),
            json=inbound_payload,
        )
        self.assertEqual(inbound.status_code, 201, inbound.text)
        delivery = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._delivery_payload(),
        )
        self.assertEqual(delivery.status_code, 201, delivery.text)
        invoice_id = delivery.json()["data"]["id"]

        cancelled = self.client.post(
            f"/api/sales-inventory/delivery-invoices/{invoice_id}/cancel",
            headers=self._headers(),
            json=self._delivery_cancel_payload(),
        )
        replay = self.client.post(
            f"/api/sales-inventory/delivery-invoices/{invoice_id}/cancel",
            headers=self._headers(),
            json=self._delivery_cancel_payload(),
        )
        conflict = self.client.post(
            f"/api/sales-inventory/delivery-invoices/{invoice_id}/cancel",
            headers=self._headers(),
            json=self._delivery_cancel_payload(reason="changed reason"),
        )
        ledger = self.client.get(
            f"/api/warehouse/stock-ledger?company={self.COMPANY}&warehouse={self.WAREHOUSE}&item_code={self.ITEM_CODE}",
            headers=self._headers(),
        )

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(cancelled.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled.json()["data"]["docstatus"], 2)
        self.assertEqual(Decimal(str(cancelled.json()["data"]["outstanding_amount"])), Decimal("0.000000"))
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "SALES_DELIVERY_INVOICE_CONFLICT")
        self.assertEqual(ledger.status_code, 200, ledger.text)
        ledger_rows = ledger.json()["data"]["items"]
        self.assertEqual([Decimal(str(row["actual_qty"])) for row in ledger_rows], [Decimal("10.000000")])
        self.assertEqual(Decimal(str(ledger_rows[-1]["qty_after_transaction"])), Decimal("10.000000"))

        with self.SessionLocal() as session:
            invoice = session.query(LyDeliveryInvoice).one()
            self.assertEqual(str(invoice.status), "cancelled")
            self.assertEqual(int(invoice.docstatus), 2)
            self.assertEqual(Decimal(str(invoice.outstanding_amount)), Decimal("0.000000"))
            self.assertEqual(session.query(LyDeliveryInvoiceOperation).count(), 1)
            sales_item = session.query(LySalesOrderItem).one()
            self.assertEqual(Decimal(str(sales_item.delivered_qty)), Decimal("0.000000"))
            issue_draft = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == "sales_delivery_invoice")
                .one()
            )
            self.assertEqual(str(issue_draft.status), "cancelled")
            durable_rows = (
                session.query(LyWarehouseStockLedgerEntry)
                .filter(
                    LyWarehouseStockLedgerEntry.company == self.COMPANY,
                    LyWarehouseStockLedgerEntry.warehouse == self.WAREHOUSE,
                    LyWarehouseStockLedgerEntry.item_code == self.ITEM_CODE,
                )
                .order_by(LyWarehouseStockLedgerEntry.sort_at.asc(), LyWarehouseStockLedgerEntry.id.asc())
                .all()
            )
            self.assertEqual([Decimal(str(row.actual_qty)) for row in durable_rows], [Decimal("10.000000"), Decimal("-4.000000")])
            self.assertEqual([str(row.status) for row in durable_rows], ["active", "voided"])
            issue_event = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == int(issue_draft.id))
                .one()
            )
            self.assertEqual(str(issue_event.status), "cancelled")

    def test_paid_delivery_invoice_cannot_cancel_before_payment_reversal(self) -> None:
        order = self.client.post(
            "/api/sales-inventory/sales-orders/drafts",
            headers=self._headers(),
            json=self._sales_order_payload(),
        )
        self.assertEqual(order.status_code, 201, order.text)
        inbound_payload = self._finished_goods_payload()
        inbound = self.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=self._headers(self._stock_request_id(inbound_payload)),
            json=inbound_payload,
        )
        self.assertEqual(inbound.status_code, 201, inbound.text)
        delivery = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._delivery_payload(),
        )
        self.assertEqual(delivery.status_code, 201, delivery.text)
        payment = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payment_payload(amount=120, suffix="LOCK"),
        )
        self.assertEqual(payment.status_code, 201, payment.text)

        blocked = self.client.post(
            f"/api/sales-inventory/delivery-invoices/{delivery.json()['data']['id']}/cancel",
            headers=self._headers(),
            json=self._delivery_cancel_payload(idempotency_key="idem-b1-delivery-invoice-cancel-paid"),
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["code"], "SALES_DELIVERY_INVOICE_HAS_PAYMENT")


if __name__ == "__main__":
    unittest.main()
