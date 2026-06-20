"""Finance approval task API tests."""

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
from app.models.factory_statement import Base as FactoryStatementBase
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementPayment
from app.models.finance_approval import Base as FinanceApprovalBase
from app.models.finance_approval import LyFinanceApprovalOperation
from app.models.finance_approval import LyFinanceApprovalTask
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchasePayment
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.factory_statement import get_db_session as factory_statement_db_dep
from app.routers.finance_approval import get_db_session as finance_approval_db_dep
from app.routers.material_purchase import get_db_session as material_purchase_db_dep


class FinanceApprovalApiTest(unittest.TestCase):
    """Validate finance approval task creation, decisions and permissions."""

    COMPANY = "COMP-FIN"
    BUSINESS_DATE = date(2026, 6, 20)

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
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        FactoryStatementBase.metadata.create_all(bind=cls.engine)
        FinanceApprovalBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[factory_statement_db_dep] = _override_db
        app.dependency_overrides[finance_approval_db_dep] = _override_db
        app.dependency_overrides[material_purchase_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(factory_statement_db_dep, None)
        app.dependency_overrides.pop(finance_approval_db_dep, None)
        app.dependency_overrides.pop(material_purchase_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyFinanceApprovalOperation).delete()
            session.query(LyFinanceApprovalTask).delete()
            session.query(LyFactoryStatementPayment).delete()
            session.query(LyFactoryStatement).delete()
            session.query(LyMaterialPurchasePayment).delete()
            session.query(LyMaterialPurchaseInvoice).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            self._seed_sources(session)
            session.commit()

    @staticmethod
    def _headers(*, role: str = "System Manager", request_id: str = "req-finance-approval") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "finance.approver",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    def _seed_sources(self, session) -> None:
        order = LyMaterialPurchaseOrder(
            company=self.COMPANY,
            purchase_no="PO-FIN-001",
            supplier_name="FIN-SUP",
            transaction_date=self.BUSINESS_DATE,
            expected_delivery_date=self.BUSINESS_DATE,
            status="received",
            total_qty=Decimal("10"),
            received_qty=Decimal("10"),
            total_amount=Decimal("250"),
            currency="CNY",
            created_by="seed",
        )
        session.add(order)
        session.flush()
        session.add(
            LyMaterialPurchaseOrderItem(
                order_id=order.id,
                company=self.COMPANY,
                item_code="STYLE-FIN",
                material_item_code="MAT-FIN",
                material_name="审批面料",
                qty=Decimal("10"),
                received_qty=Decimal("10"),
                uom="米",
                unit_price=Decimal("25"),
                amount=Decimal("250"),
                warehouse="WH-FIN",
            )
        )
        invoice = LyMaterialPurchaseInvoice(
            company=self.COMPANY,
            purchase_invoice="PINV-FIN-001",
            purchase_order_id=order.id,
            purchase_no=order.purchase_no,
            supplier_name=order.supplier_name,
            material_item_code="MAT-FIN",
            material_name="审批面料",
            warehouse="WH-FIN",
            qty=Decimal("10"),
            uom="米",
            rate=Decimal("25"),
            grand_total=Decimal("250"),
            paid_amount=Decimal("100"),
            outstanding_amount=Decimal("150"),
            posting_date=self.BUSINESS_DATE,
            due_date=self.BUSINESS_DATE,
            status="partly_paid",
            docstatus=1,
            source_ref="SRC-PINV-FIN-001",
            idempotency_key="idem-pinv-fin-001",
            request_hash="hash-pinv-fin-001",
            payload={},
            created_by="seed",
        )
        session.add(invoice)
        session.flush()
        payment = LyMaterialPurchasePayment(
            company=self.COMPANY,
            payment_entry="PP-FIN-001",
            purchase_invoice_id=invoice.id,
            purchase_invoice=invoice.purchase_invoice,
            purchase_no=order.purchase_no,
            supplier_name=order.supplier_name,
            posting_date=self.BUSINESS_DATE,
            paid_amount=Decimal("100"),
            allocated_amount=Decimal("100"),
            outstanding_before=Decimal("250"),
            outstanding_after=Decimal("150"),
            mode_of_payment="Bank Transfer",
            reference_no="BANK-FIN-001",
            reference_date=self.BUSINESS_DATE,
            status="submitted",
            docstatus=1,
            source_ref="SRC-PP-FIN-001",
            idempotency_key="idem-pp-fin-001",
            request_hash="hash-pp-fin-001",
            payload={},
            created_by="seed",
        )
        statement = LyFactoryStatement(
            statement_no="FS-FIN-001",
            company=self.COMPANY,
            supplier="FIN-FACTORY",
            from_date=self.BUSINESS_DATE,
            to_date=self.BUSINESS_DATE,
            source_count=1,
            inspected_qty=Decimal("20"),
            rejected_qty=Decimal("0"),
            accepted_qty=Decimal("20"),
            gross_amount=Decimal("600"),
            deduction_amount=Decimal("0"),
            net_amount=Decimal("600"),
            rejected_rate=Decimal("0"),
            statement_status="confirmed",
            idempotency_key="idem-fs-fin-001",
            request_hash="hash-fs-fin-001",
            created_by="seed",
        )
        session.add_all([payment, statement])
        session.flush()
        factory_payment = LyFactoryStatementPayment(
            company=self.COMPANY,
            payment_entry="FSP-FIN-001",
            statement_id=statement.id,
            statement_no=statement.statement_no,
            supplier=statement.supplier,
            posting_date=self.BUSINESS_DATE,
            paid_amount=Decimal("200"),
            allocated_amount=Decimal("200"),
            outstanding_before=Decimal("600"),
            outstanding_after=Decimal("400"),
            mode_of_payment="Bank Transfer",
            reference_no="BANK-FSP-001",
            reference_date=self.BUSINESS_DATE,
            status="pending_approval",
            docstatus=0,
            source_ref="SRC-FSP-FIN-001",
            idempotency_key="idem-fsp-fin-001",
            request_hash="hash-fsp-fin-001",
            payload={"approval_effect": "pending"},
            created_by="seed",
        )
        session.add(factory_payment)
        session.flush()
        self.invoice_id = invoice.id
        self.purchase_payment_id = payment.id
        self.factory_payment_id = factory_payment.id

    def test_create_list_and_approve_purchase_invoice_task(self) -> None:
        create_payload = {
            "operation": "create_task",
            "company": self.COMPANY,
            "source_type": "purchase_invoice",
            "source_id": self.invoice_id,
            "idempotency_key": "idem-fin-task-pinv",
        }
        created = self.client.post(
            "/api/finance/approval-tasks",
            json=create_payload,
            headers=self._headers(request_id="req-fin-create-pinv"),
        )
        self.assertEqual(created.status_code, 201)
        created_data = created.json()["data"]
        self.assertEqual(created_data["source_no"], "PINV-FIN-001")
        self.assertEqual(created_data["amount"], "150.000000")
        self.assertEqual(created_data["status"], "pending")
        with self.SessionLocal() as session:
            invoice = session.query(LyMaterialPurchaseInvoice).filter_by(id=self.invoice_id).one()
            self.assertEqual(invoice.payload["finance_approval"]["status"], "pending")
            self.assertEqual(invoice.payload["finance_approval"]["approval_no"], created_data["approval_no"])

        replayed = self.client.post(
            "/api/finance/approval-tasks",
            json=create_payload,
            headers=self._headers(request_id="req-fin-create-pinv-replay"),
        )
        self.assertEqual(replayed.status_code, 201)
        self.assertEqual(replayed.json()["data"]["id"], created_data["id"])

        listed = self.client.get(
            "/api/finance/approval-tasks",
            params={"company": self.COMPANY, "keyword": "PINV-FIN"},
            headers=self._headers(request_id="req-fin-list-pinv"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

        approved = self.client.post(
            f"/api/finance/approval-tasks/{created_data['id']}/approve",
            json={"operation": "approve_task", "company": self.COMPANY, "idempotency_key": "idem-fin-approve-pinv"},
            headers=self._headers(request_id="req-fin-approve-pinv"),
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["data"]["status"], "approved")
        with self.SessionLocal() as session:
            invoice = session.query(LyMaterialPurchaseInvoice).filter_by(id=self.invoice_id).one()
            self.assertEqual(invoice.payload["finance_approval"]["status"], "approved")
            self.assertEqual(invoice.payload["finance_approval"]["approved_by"], "finance.approver")

        listed_invoices = self.client.get(
            "/api/material-purchase/purchase-invoices",
            params={"company": self.COMPANY, "keyword": "PINV-FIN"},
            headers=self._headers(request_id="req-fin-list-invoice-approval"),
        )
        self.assertEqual(listed_invoices.status_code, 200)
        invoice_row = listed_invoices.json()["data"]["items"][0]
        self.assertEqual(invoice_row["approval_status"], "approved")
        self.assertEqual(invoice_row["approval_no"], created_data["approval_no"])

        rejected_after_approve = self.client.post(
            f"/api/finance/approval-tasks/{created_data['id']}/reject",
            json={
                "operation": "reject_task",
                "company": self.COMPANY,
                "idempotency_key": "idem-fin-reject-approved",
                "reason": "审批后不可驳回",
            },
            headers=self._headers(request_id="req-fin-reject-approved"),
        )
        self.assertEqual(rejected_after_approve.status_code, 409)
        self.assertEqual(rejected_after_approve.json()["code"], "FINANCE_APPROVAL_INVALID_STATUS")

    def test_reject_purchase_payment_and_forbid_viewer(self) -> None:
        forbidden = self.client.get(
            "/api/finance/approval-tasks",
            params={"company": self.COMPANY},
            headers=self._headers(role="Viewer", request_id="req-fin-viewer"),
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(forbidden.json()["code"], "AUTH_FORBIDDEN")

        created = self.client.post(
            "/api/finance/approval-tasks",
            json={
                "operation": "create_task",
                "company": self.COMPANY,
                "source_type": "purchase_payment",
                "source_id": self.purchase_payment_id,
                "idempotency_key": "idem-fin-task-payment",
            },
            headers=self._headers(request_id="req-fin-create-payment"),
        )
        self.assertEqual(created.status_code, 201)
        task_id = created.json()["data"]["id"]

        rejected = self.client.post(
            f"/api/finance/approval-tasks/{task_id}/reject",
            json={
                "operation": "reject_task",
                "company": self.COMPANY,
                "idempotency_key": "idem-fin-reject-payment",
                "reason": "付款凭证需补充",
            },
            headers=self._headers(request_id="req-fin-reject-payment"),
        )
        self.assertEqual(rejected.status_code, 200)
        data = rejected.json()["data"]
        self.assertEqual(data["status"], "rejected")
        self.assertEqual(data["reject_reason"], "付款凭证需补充")
        with self.SessionLocal() as session:
            payment = session.query(LyMaterialPurchasePayment).filter_by(id=self.purchase_payment_id).one()
            self.assertEqual(payment.payload["finance_approval"]["status"], "rejected")
            self.assertEqual(payment.payload["finance_approval"]["reject_reason"], "付款凭证需补充")

        listed_payments = self.client.get(
            "/api/material-purchase/purchase-payments",
            params={"company": self.COMPANY, "keyword": "PP-FIN"},
            headers=self._headers(request_id="req-fin-list-payment-approval"),
        )
        self.assertEqual(listed_payments.status_code, 200)
        payment_row = listed_payments.json()["data"]["items"][0]
        self.assertEqual(payment_row["approval_status"], "rejected")
        self.assertEqual(payment_row["approval_no"], created.json()["data"]["approval_no"])

    def test_create_factory_statement_payment_task(self) -> None:
        created = self.client.post(
            "/api/finance/approval-tasks",
            json={
                "operation": "create_task",
                "company": self.COMPANY,
                "source_type": "factory_statement_payment",
                "source_id": self.factory_payment_id,
                "idempotency_key": "idem-fin-task-fsp",
            },
            headers=self._headers(request_id="req-fin-create-fsp"),
        )
        self.assertEqual(created.status_code, 201)
        data = created.json()["data"]
        self.assertEqual(data["source_no"], "FSP-FIN-001")
        self.assertEqual(data["partner_name"], "FIN-FACTORY")
        self.assertEqual(data["amount"], "200.000000")
        with self.SessionLocal() as session:
            payment = session.query(LyFactoryStatementPayment).filter_by(id=self.factory_payment_id).one()
            self.assertEqual(payment.payload["finance_approval"]["status"], "pending")
            self.assertEqual(payment.payload["finance_approval"]["approval_no"], data["approval_no"])

        listed = self.client.get(
            "/api/finance/approval-tasks",
            params={"company": self.COMPANY, "source_type": "factory_statement_payment"},
            headers=self._headers(request_id="req-fin-list-fsp"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

        listed_payments = self.client.get(
            "/api/factory-statements/payments",
            params={"company": self.COMPANY, "keyword": "FSP-FIN"},
            headers=self._headers(request_id="req-fin-list-fsp-approval"),
        )
        self.assertEqual(listed_payments.status_code, 200)
        payment_row = listed_payments.json()["data"]["items"][0]
        self.assertEqual(payment_row["approval_status"], "pending")
        self.assertEqual(payment_row["approval_no"], data["approval_no"])

        statement_before = self.client.get(
            "/api/factory-statements/",
            params={"company": self.COMPANY, "keyword": "FS-FIN"},
            headers=self._headers(request_id="req-fin-list-fsp-before-approve"),
        )
        self.assertEqual(statement_before.status_code, 200)
        statement_row = statement_before.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(statement_row["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(statement_row["outstanding_amount"])), Decimal("600.000000"))
        self.assertEqual(statement_row["payment_status"], "unpaid")

        approved = self.client.post(
            f"/api/finance/approval-tasks/{data['id']}/approve",
            json={
                "operation": "approve_task",
                "company": self.COMPANY,
                "idempotency_key": "idem-fin-approve-fsp",
                "reason": "加工厂付款审批通过",
            },
            headers=self._headers(request_id="req-fin-approve-fsp"),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["data"]["status"], "approved")
        self.assertEqual(approved.json()["data"]["source_status"], "submitted")

        statement_after = self.client.get(
            "/api/factory-statements/",
            params={"company": self.COMPANY, "keyword": "FS-FIN"},
            headers=self._headers(request_id="req-fin-list-fsp-after-approve"),
        )
        self.assertEqual(statement_after.status_code, 200)
        approved_statement = statement_after.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(approved_statement["paid_amount"])), Decimal("200.000000"))
        self.assertEqual(Decimal(str(approved_statement["outstanding_amount"])), Decimal("400.000000"))
        self.assertEqual(approved_statement["payment_status"], "partly_paid")

    def test_reject_factory_statement_payment_keeps_payable_open(self) -> None:
        created = self.client.post(
            "/api/finance/approval-tasks",
            json={
                "operation": "create_task",
                "company": self.COMPANY,
                "source_type": "factory_statement_payment",
                "source_id": self.factory_payment_id,
                "idempotency_key": "idem-fin-task-fsp-reject",
            },
            headers=self._headers(request_id="req-fin-create-fsp-reject"),
        )
        self.assertEqual(created.status_code, 201, created.text)
        task_id = created.json()["data"]["id"]

        rejected = self.client.post(
            f"/api/finance/approval-tasks/{task_id}/reject",
            json={
                "operation": "reject_task",
                "company": self.COMPANY,
                "idempotency_key": "idem-fin-reject-fsp",
                "reason": "加工厂付款凭证需补充",
            },
            headers=self._headers(request_id="req-fin-reject-fsp"),
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["data"]["status"], "rejected")
        self.assertEqual(rejected.json()["data"]["source_status"], "cancelled")

        with self.SessionLocal() as session:
            payment = session.query(LyFactoryStatementPayment).filter_by(id=self.factory_payment_id).one()
            self.assertEqual(payment.status, "cancelled")
            self.assertEqual(payment.docstatus, 2)
            self.assertEqual(payment.payload["finance_approval"]["status"], "rejected")
            self.assertEqual(payment.payload["finance_approval"]["reject_reason"], "加工厂付款凭证需补充")

        listed = self.client.get(
            "/api/factory-statements/",
            params={"company": self.COMPANY, "keyword": "FS-FIN"},
            headers=self._headers(request_id="req-fin-list-fsp-after-reject"),
        )
        self.assertEqual(listed.status_code, 200)
        statement_row = listed.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(statement_row["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(statement_row["outstanding_amount"])), Decimal("600.000000"))
        self.assertEqual(statement_row["payment_status"], "unpaid")

    def test_create_idempotency_conflict_is_explicit(self) -> None:
        payload = {
            "operation": "create_task",
            "company": self.COMPANY,
            "source_type": "purchase_invoice",
            "source_id": self.invoice_id,
            "idempotency_key": "idem-fin-conflict",
        }
        ok = self.client.post("/api/finance/approval-tasks", json=payload, headers=self._headers(request_id="req-fin-idem-1"))
        self.assertEqual(ok.status_code, 201)

        conflict_payload = dict(payload)
        conflict_payload["source_type"] = "purchase_payment"
        conflict_payload["source_id"] = self.purchase_payment_id
        conflict = self.client.post(
            "/api/finance/approval-tasks",
            json=conflict_payload,
            headers=self._headers(request_id="req-fin-idem-2"),
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FINANCE_APPROVAL_IDEMPOTENCY_CONFLICT")


if __name__ == "__main__":
    unittest.main()
