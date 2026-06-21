"""Financial summary endpoints backed by FastAPI-native facts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
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
from app.models.factory_statement import Base as FactoryStatementBase
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementPayment
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchasePayment
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesPaymentEntry
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.factory_statement import get_db_session as factory_statement_db_dep


class FactoryStatementFinancialSummaryTest(unittest.TestCase):
    """Validate finance summary read pages aggregate local invoice/payment facts."""

    COMPANY = "COMP-FIN"

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
        AuditBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        FactoryStatementBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[factory_statement_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(factory_statement_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LyFactoryStatementPayment).delete()
            session.query(LyFactoryStatement).delete()
            session.query(LyMaterialPurchasePayment).delete()
            session.query(LyMaterialPurchaseInvoice).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LySalesPaymentEntry).delete()
            session.query(LyDeliveryInvoice).delete()
            session.commit()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "X-LY-Dev-User": "finance.summary.user",
            "X-LY-Dev-Roles": "Finance Manager",
            "X-Request-ID": "req-financial-summary",
        }

    def _seed_customer_receivable(self) -> None:
        with self.SessionLocal() as session:
            invoice = LyDeliveryInvoice(
                company=self.COMPANY,
                delivery_note="DN-FIN-001",
                sales_invoice="SINV-FIN-001",
                sales_order="SO-FIN-001",
                customer="CUS-FIN",
                item_code="STYLE-FIN",
                item_name="Finance style",
                warehouse="WH-FIN",
                delivered_qty=Decimal("4"),
                uom="件",
                rate=Decimal("80"),
                grand_total=Decimal("320"),
                paid_amount=Decimal("120"),
                outstanding_amount=Decimal("200"),
                posting_date=date(2026, 6, 20),
                due_date=date(2026, 6, 25),
                status="partly_paid",
                docstatus=1,
                source_ref="SRC-FIN-SINV-001",
                idempotency_key="idem-fin-sinv-001",
                request_hash="hash-fin-sinv-001",
                payload={},
                created_by="seed",
            )
            cancelled = LyDeliveryInvoice(
                company=self.COMPANY,
                delivery_note="DN-FIN-CANCEL",
                sales_invoice="SINV-FIN-CANCEL",
                sales_order="SO-FIN-CANCEL",
                customer="CUS-FIN",
                item_code="STYLE-FIN",
                item_name="Finance style",
                warehouse="WH-FIN",
                delivered_qty=Decimal("1"),
                uom="件",
                rate=Decimal("999"),
                grand_total=Decimal("999"),
                paid_amount=Decimal("0"),
                outstanding_amount=Decimal("0"),
                posting_date=date(2026, 6, 21),
                due_date=date(2026, 6, 25),
                status="cancelled",
                docstatus=2,
                source_ref="SRC-FIN-SINV-CANCEL",
                idempotency_key="idem-fin-sinv-cancel",
                request_hash="hash-fin-sinv-cancel",
                payload={},
                created_by="seed",
            )
            session.add_all([invoice, cancelled])
            session.flush()
            session.add(
                LySalesPaymentEntry(
                    company=self.COMPANY,
                    payment_entry="PE-FIN-001",
                    delivery_invoice_id=int(invoice.id),
                    delivery_note="DN-FIN-001",
                    sales_invoice="SINV-FIN-001",
                    sales_order="SO-FIN-001",
                    customer="CUS-FIN",
                    posting_date=date(2026, 6, 22),
                    paid_amount=Decimal("120"),
                    allocated_amount=Decimal("120"),
                    outstanding_before=Decimal("320"),
                    outstanding_after=Decimal("200"),
                    mode_of_payment="Bank Transfer",
                    reference_no="BANK-FIN-001",
                    reference_date=date(2026, 6, 22),
                    status="submitted",
                    docstatus=1,
                    source_ref="SRC-FIN-PE-001",
                    idempotency_key="idem-fin-pe-001",
                    request_hash="hash-fin-pe-001",
                    payload={},
                    created_by="seed",
                )
            )
            session.commit()

    def _seed_extra_customer_receivable(self, *, customer: str, suffix: str) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyDeliveryInvoice(
                    company=self.COMPANY,
                    delivery_note=f"DN-FIN-{suffix}",
                    sales_invoice=f"SINV-FIN-{suffix}",
                    sales_order=f"SO-FIN-{suffix}",
                    customer=customer,
                    item_code="STYLE-FIN",
                    item_name="Finance style",
                    warehouse="WH-FIN",
                    delivered_qty=Decimal("1"),
                    uom="件",
                    rate=Decimal("111"),
                    grand_total=Decimal("111"),
                    paid_amount=Decimal("0"),
                    outstanding_amount=Decimal("111"),
                    posting_date=date(2026, 6, 23),
                    due_date=date(2026, 6, 30),
                    status="submitted",
                    docstatus=1,
                    source_ref=f"SRC-FIN-SINV-{suffix}",
                    idempotency_key=f"idem-fin-sinv-{suffix}",
                    request_hash=f"hash-fin-sinv-{suffix}",
                    payload={},
                    created_by="seed",
                )
            )
            session.commit()

    def _seed_supplier_payable(self) -> None:
        with self.SessionLocal() as session:
            order = LyMaterialPurchaseOrder(
                company=self.COMPANY,
                purchase_no="PO-FIN-001",
                supplier_name="SUP-FIN",
                transaction_date=date(2026, 6, 18),
                expected_delivery_date=date(2026, 6, 28),
                status="received",
                total_qty=Decimal("20"),
                received_qty=Decimal("20"),
                total_amount=Decimal("250"),
                currency="CNY",
                created_by="seed",
            )
            session.add(order)
            session.flush()
            invoice = LyMaterialPurchaseInvoice(
                company=self.COMPANY,
                purchase_invoice="PINV-FIN-001",
                purchase_order_id=int(order.id),
                purchase_no="PO-FIN-001",
                supplier_name="SUP-FIN",
                material_item_code="MAT-FIN",
                material_name="Finance material",
                warehouse="WH-FIN",
                qty=Decimal("20"),
                uom="米",
                rate=Decimal("12.5"),
                grand_total=Decimal("250"),
                paid_amount=Decimal("100"),
                outstanding_amount=Decimal("150"),
                posting_date=date(2026, 6, 20),
                due_date=date(2026, 6, 25),
                status="partly_paid",
                docstatus=1,
                source_ref="SRC-FIN-PINV-001",
                idempotency_key="idem-fin-pinv-001",
                request_hash="hash-fin-pinv-001",
                payload={},
                created_by="seed",
            )
            session.add(invoice)
            session.flush()
            session.add(
                LyMaterialPurchasePayment(
                    company=self.COMPANY,
                    payment_entry="PP-FIN-001",
                    purchase_invoice_id=int(invoice.id),
                    purchase_invoice="PINV-FIN-001",
                    purchase_no="PO-FIN-001",
                    supplier_name="SUP-FIN",
                    posting_date=date(2026, 6, 22),
                    paid_amount=Decimal("100"),
                    allocated_amount=Decimal("100"),
                    outstanding_before=Decimal("250"),
                    outstanding_after=Decimal("150"),
                    mode_of_payment="Bank Transfer",
                    reference_no="BANK-FIN-SUP-001",
                    reference_date=date(2026, 6, 22),
                    status="submitted",
                    docstatus=1,
                    source_ref="SRC-FIN-PP-001",
                    idempotency_key="idem-fin-pp-001",
                    request_hash="hash-fin-pp-001",
                    payload={},
                    created_by="seed",
                )
            )
            session.commit()

    def _seed_factory_payable(self) -> None:
        with self.SessionLocal() as session:
            statement = LyFactoryStatement(
                statement_no="FS-FIN-001",
                company=self.COMPANY,
                supplier="FAC-FIN",
                from_date=date(2026, 6, 1),
                to_date=date(2026, 6, 20),
                source_type="subcontract_inspection",
                source_count=1,
                inspected_qty=Decimal("100"),
                rejected_qty=Decimal("0"),
                accepted_qty=Decimal("100"),
                gross_amount=Decimal("4700"),
                deduction_amount=Decimal("0"),
                net_amount=Decimal("4700"),
                rejected_rate=Decimal("0"),
                statement_status="confirmed",
                idempotency_key="idem-fin-fs-001",
                request_hash="hash-fin-fs-001",
                created_by="seed",
                confirmed_by="seed",
            )
            session.add(statement)
            session.flush()
            session.add(
                LyFactoryStatementPayment(
                    company=self.COMPANY,
                    payment_entry="FSP-FIN-001",
                    statement_id=int(statement.id),
                    statement_no="FS-FIN-001",
                    supplier="FAC-FIN",
                    posting_date=date(2026, 6, 22),
                    paid_amount=Decimal("1200"),
                    allocated_amount=Decimal("1200"),
                    outstanding_before=Decimal("4700"),
                    outstanding_after=Decimal("3500"),
                    mode_of_payment="Bank Transfer",
                    reference_no="BANK-FIN-FAC-001",
                    reference_date=date(2026, 6, 22),
                    status="submitted",
                    docstatus=1,
                    source_ref="SRC-FIN-FSP-001",
                    idempotency_key="idem-fin-fsp-001",
                    request_hash="hash-fin-fsp-001",
                    payload={},
                    created_by="seed",
                )
            )
            session.commit()

    def test_customer_receivable_summary_uses_delivery_invoice_and_payment_facts(self) -> None:
        self._seed_customer_receivable()

        response = self.client.get(
            "/api/factory-statements/customer-receivables",
            headers=self._headers(),
            params={"keyword": "CUS-FIN"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        row = payload["items"][0]
        self.assertEqual(row["customer_name"], "CUS-FIN")
        self.assertEqual(Decimal(str(row["current_receivable"])), Decimal("320.000000"))
        self.assertEqual(Decimal(str(row["received_amount"])), Decimal("120.000000"))
        self.assertEqual(Decimal(str(row["ending_receivable"])), Decimal("200.000000"))

    def test_customer_receivable_summary_uses_fastapi_customer_scope(self) -> None:
        self._seed_customer_receivable()
        self._seed_extra_customer_receivable(customer="CUS-OUT", suffix="OUT")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {"users": {"finance.summary.user": {"company": [self.COMPANY], "customer": ["CUS-FIN"]}}}
        )

        response = self.client.get(
            "/api/factory-statements/customer-receivables",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["customer_name"], "CUS-FIN")

    def test_customer_unpaid_reports_use_fastapi_customer_scope(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "finance.summary.user": {
                        "company": ["凌云服饰"],
                        "supplier": ["东莞卓越制衣厂"],
                        "customer": ["CUS-0132"],
                    }
                }
            }
        )

        response = self.client.get(
            "/api/factory-statements/customer-unpaid-reports",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["customer_code"], "CUS-0132")

    def test_supplier_payable_summary_uses_purchase_invoice_and_payment_facts(self) -> None:
        self._seed_supplier_payable()

        response = self.client.get(
            "/api/factory-statements/supplier-payable-summaries",
            headers=self._headers(),
            params={"keyword": "SUP-FIN"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        row = payload["items"][0]
        self.assertEqual(row["supplier"], "SUP-FIN")
        self.assertEqual(Decimal(str(row["current_payable"])), Decimal("250.000000"))
        self.assertEqual(Decimal(str(row["paid_amount"])), Decimal("100.000000"))
        self.assertEqual(Decimal(str(row["ending_payable"])), Decimal("150.000000"))

    def test_factory_payable_summary_uses_statement_and_payment_facts(self) -> None:
        self._seed_factory_payable()

        response = self.client.get(
            "/api/factory-statements/factory-payable-summaries",
            headers=self._headers(),
            params={"keyword": "FAC-FIN"},
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        row = payload["items"][0]
        self.assertEqual(row["supplier"], "FAC-FIN")
        self.assertEqual(Decimal(str(row["current_payable"])), Decimal("4700.000000"))
        self.assertEqual(Decimal(str(row["paid_amount"])), Decimal("1200.000000"))
        self.assertEqual(Decimal(str(row["ending_payable"])), Decimal("3500.000000"))


if __name__ == "__main__":
    unittest.main()
