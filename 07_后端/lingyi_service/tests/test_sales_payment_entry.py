"""B5 FastAPI-native receivable payment flow."""

from __future__ import annotations

from datetime import date
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
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesPaymentEntry
from app.models.sales_order import LySalesPaymentEntryOperation
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep


class SalesPaymentEntryFlowTest(unittest.TestCase):
    """Validate B5 payment entries reduce local receivables."""

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
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LySalesPaymentEntryOperation).delete()
            session.query(LySalesPaymentEntry).delete()
            session.query(LyDeliveryInvoice).delete()
            session.add(
                LyDeliveryInvoice(
                    company="COMP-A",
                    delivery_note="DN-B5-001",
                    sales_invoice="SI-B5-001",
                    sales_order="SO-B5-001",
                    customer="CUST-A",
                    item_code="DEMO-TEE",
                    item_name="Demo Tee",
                    warehouse="WH-FG",
                    delivered_qty=Decimal("5"),
                    uom="件",
                    rate=Decimal("80"),
                    grand_total=Decimal("400"),
                    paid_amount=Decimal("0"),
                    outstanding_amount=Decimal("400"),
                    posting_date=date(2026, 6, 17),
                    due_date=date(2026, 7, 17),
                    status="submitted",
                    docstatus=1,
                    source_ref="SRC-B5-DI-001",
                    idempotency_key="idem-b5-delivery-001",
                    request_hash="hash-b5-delivery-001",
                    scenario_tag="B5-DELIVERY-INVOICE",
                    warehouse_draft_id=None,
                    payload={},
                    created_by="seed",
                )
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "System Manager") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "b5.payment.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": "req-b5-payment",
        }

    @staticmethod
    def _payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "company": "COMP-A",
            "sales_invoice": "SI-B5-001",
            "customer": "CUST-A",
            "posting_date": "2026-06-17",
            "paid_amount": 150,
            "mode_of_payment": "Bank Transfer",
            "reference_no": "BANK-B5-001",
            "reference_date": "2026-06-17",
            "payment_entry": "PE-B5-001",
            "source_ref": "SRC-B5-PAY-001",
            "idempotency_key": "idem-b5-payment-001",
            "scenario_tag": "B5-SALES-PAYMENT-001",
            "operation": "create_payment_entry",
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def _cancel_payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "company": "COMP-A",
            "sales_invoice": "SI-B5-001",
            "reason": "VOID-B5-PAYMENT-001",
            "idempotency_key": "idem-b5-payment-cancel-001",
            "scenario_tag": "B5-SALES-PAYMENT-CANCEL-001",
            "operation": "cancel_payment_entry",
        }
        payload.update(overrides)
        return payload

    def test_payment_entry_replay_and_receivable_readbacks(self) -> None:
        created = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payload(),
        )
        replay = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payload(),
        )
        conflict = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payload(paid_amount=160),
        )
        payments = self.client.get(
            "/api/sales-inventory/payment-entries?keyword=PE-B5-001",
            headers=self._headers(),
        )
        sales_invoices = self.client.get(
            "/api/sales-inventory/sales-invoices?sales_order=SO-B5-001",
            headers=self._headers(),
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(created.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "SALES_PAYMENT_ENTRY_CONFLICT")
        self.assertEqual(payments.status_code, 200)
        self.assertEqual(payments.json()["data"]["items"][0]["payment_entry"], "PE-B5-001")
        self.assertEqual(Decimal(str(created.json()["data"]["outstanding_before"])), Decimal("400.000000"))
        self.assertEqual(Decimal(str(created.json()["data"]["outstanding_after"])), Decimal("250.000000"))
        self.assertEqual(sales_invoices.status_code, 200)
        invoice_row = sales_invoices.json()["data"]["items"][0]
        self.assertEqual(invoice_row["status"], "partly_paid")
        self.assertEqual(Decimal(str(invoice_row["paid_amount"])), Decimal("150.000000"))
        self.assertEqual(Decimal(str(invoice_row["outstanding_amount"])), Decimal("250.000000"))

        closed = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payload(
                paid_amount=250,
                payment_entry="PE-B5-002",
                source_ref="SRC-B5-PAY-002",
                idempotency_key="idem-b5-payment-002",
                reference_no="BANK-B5-002",
            ),
        )
        self.assertEqual(closed.status_code, 201)
        self.assertEqual(Decimal(str(closed.json()["data"]["outstanding_after"])), Decimal("0.000000"))

        with self.SessionLocal() as session:
            invoice = session.query(LyDeliveryInvoice).one()
            self.assertEqual(str(invoice.status), "paid")
            self.assertEqual(Decimal(str(invoice.paid_amount)), Decimal("400.000000"))
            self.assertEqual(Decimal(str(invoice.outstanding_amount)), Decimal("0.000000"))
            self.assertEqual(session.query(LySalesPaymentEntry).count(), 2)
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("sales_inventory:write", audit_actions)

    def test_payment_entry_blocks_overpayment(self) -> None:
        response = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payload(paid_amount=401, idempotency_key="idem-b5-payment-over", source_ref="SRC-B5-PAY-OVER"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SALES_PAYMENT_AMOUNT_EXCEEDED")

    def test_payment_entry_cancel_reopens_receivable_and_is_idempotent(self) -> None:
        created = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(created.status_code, 201)
        payment_id = created.json()["data"]["id"]

        cancelled = self.client.post(
            f"/api/sales-inventory/payment-entries/{payment_id}/cancel",
            headers=self._headers(),
            json=self._cancel_payload(),
        )
        replay = self.client.post(
            f"/api/sales-inventory/payment-entries/{payment_id}/cancel",
            headers=self._headers(),
            json=self._cancel_payload(),
        )
        conflict = self.client.post(
            f"/api/sales-inventory/payment-entries/{payment_id}/cancel",
            headers=self._headers(),
            json=self._cancel_payload(reason="VOID-B5-PAYMENT-CHANGED"),
        )
        submitted_payments = self.client.get(
            "/api/sales-inventory/payment-entries?status=submitted",
            headers=self._headers(),
        )
        cancelled_payments = self.client.get(
            "/api/sales-inventory/payment-entries?status=cancelled",
            headers=self._headers(),
        )
        sales_invoices = self.client.get(
            "/api/sales-inventory/sales-invoices?sales_order=SO-B5-001",
            headers=self._headers(),
        )

        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(cancelled.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled.json()["data"]["docstatus"], 2)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "SALES_PAYMENT_ENTRY_CONFLICT")
        self.assertEqual(submitted_payments.status_code, 200)
        self.assertEqual(submitted_payments.json()["data"]["total"], 0)
        self.assertEqual(cancelled_payments.status_code, 200)
        self.assertEqual(cancelled_payments.json()["data"]["total"], 1)
        invoice_row = sales_invoices.json()["data"]["items"][0]
        self.assertEqual(invoice_row["status"], "submitted")
        self.assertEqual(Decimal(str(invoice_row["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(invoice_row["outstanding_amount"])), Decimal("400.000000"))

        with self.SessionLocal() as session:
            invoice = session.query(LyDeliveryInvoice).one()
            payment = session.query(LySalesPaymentEntry).one()
            self.assertEqual(str(invoice.status), "submitted")
            self.assertEqual(Decimal(str(invoice.paid_amount)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(invoice.outstanding_amount)), Decimal("400.000000"))
            self.assertEqual(str(payment.status), "cancelled")
            self.assertEqual(int(payment.docstatus), 2)
            self.assertEqual(session.query(LySalesPaymentEntryOperation).count(), 1)

    def test_payment_entry_cancel_requires_write_permission(self) -> None:
        created = self.client.post(
            "/api/sales-inventory/payment-entries",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(created.status_code, 201)
        payment_id = created.json()["data"]["id"]

        blocked = self.client.post(
            f"/api/sales-inventory/payment-entries/{payment_id}/cancel",
            headers=self._headers("Finance Manager"),
            json=self._cancel_payload(),
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            payment = session.query(LySalesPaymentEntry).one()
            invoice = session.query(LyDeliveryInvoice).one()
            self.assertEqual(str(payment.status), "submitted")
            self.assertEqual(str(invoice.status), "partly_paid")
            self.assertEqual(session.query(LySalesPaymentEntryOperation).count(), 0)


if __name__ == "__main__":
    unittest.main()
