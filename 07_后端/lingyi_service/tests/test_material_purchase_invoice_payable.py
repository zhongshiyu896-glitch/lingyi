"""B2 purchase invoice and payable flow for FastAPI-native material purchase."""

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
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseIdempotency
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.material_purchase import LyMaterialPurchasePayment
from app.models.material_purchase import LyMaterialPurchasePaymentOperation
from app.models.quality import Base as QualityBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.material_purchase import get_db_session as material_purchase_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep


class MaterialPurchaseInvoicePayableFlowTest(unittest.TestCase):
    """Validate purchase receipt -> purchase invoice -> supplier payment."""

    SCENARIO_TAG = "Z003-WAREHOUSE-20260616-101"
    BUSINESS_DATE = date(2026, 6, 17).isoformat()
    COMPANY = "COMP-B2"
    WAREHOUSE = "WH-B2"
    ITEM_CODE = "FAB-B2"

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
        MasterDataBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[material_purchase_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(material_purchase_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyMaterialPurchasePaymentOperation).delete()
            session.query(LyMaterialPurchasePayment).delete()
            session.query(LyMaterialPurchaseInvoice).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMaterialPurchaseIdempotency).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyMasterDataRecord).delete()
            self._seed_purchase_master_data(session=session)
            session.commit()

    @staticmethod
    def _headers(*, request_id: str = "req-b2-material-purchase", role: str = "System Manager") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "b2.purchase.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _carrier_code(value: object, *, length: int = 3) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-length:]

    @classmethod
    def _seed_purchase_master_data(cls, *, session) -> None:
        session.add(
            LyMasterDataRecord(
                entity_type="supplier",
                company=cls.COMPANY,
                code="SUP-B2",
                name="SUP-B2",
                status="active",
                payload={},
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            LyMasterDataRecord(
                entity_type="material",
                company=cls.COMPANY,
                code=cls.ITEM_CODE,
                name="B2棉布",
                status="active",
                payload={"material_kind": "fabric", "material_item_code": cls.ITEM_CODE, "uom": "米"},
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            LyMasterDataRecord(
                entity_type="warehouse",
                company=cls.COMPANY,
                code=cls.WAREHOUSE,
                name=cls.WAREHOUSE,
                status="active",
                payload={},
                created_by="seed",
                updated_by="seed",
            )
        )

    @staticmethod
    def _decimal_text(value: object) -> str:
        normalized = format(Decimal(str(value)).normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return normalized or "0"

    @classmethod
    def _warehouse_request_id(
        cls,
        *,
        idempotency_key: str,
        source_ref: str,
        quantity: object,
    ) -> str:
        return "-".join(
            [
                cls.SCENARIO_TAG,
                "RW",
                "C",
                cls._carrier_code(idempotency_key),
                cls._carrier_code(source_ref),
                cls._carrier_code(cls.WAREHOUSE),
                cls._carrier_code(cls.ITEM_CODE),
                cls._carrier_code(cls._decimal_text(quantity)),
                cls._carrier_code(cls.BUSINESS_DATE),
                cls._carrier_code("C"),
            ]
        )

    @classmethod
    def _create_received_purchase_order(cls) -> None:
        purchase_payload = {
            "operation": "create",
            "company": cls.COMPANY,
            "purchase_no": "PO-B2-001",
            "supplier_name": "SUP-B2",
            "transaction_date": "2026-06-17",
            "expected_delivery_date": "2026-06-30",
            "currency": "CNY",
            "idempotency_key": "idem-po-b2-001",
            "items": [
                {
                    "material_item_code": cls.ITEM_CODE,
                    "material_name": "B2棉布",
                    "qty": "30",
                    "uom": "米",
                    "unit_price": "12.5",
                    "warehouse": cls.WAREHOUSE,
                }
            ],
        }
        create_po = cls.client.post("/api/material-purchase/orders", headers=cls._headers(), json=purchase_payload)
        assert create_po.status_code == 201, create_po.text

        receipt_idem = f"{cls.SCENARIO_TAG}:idem-whse-po-b2-001"
        receipt_source_ref = f"{cls.SCENARIO_TAG}:purchase:PO-B2-001"
        receipt_payload = {
            "company": cls.COMPANY,
            "purpose": "Material Receipt",
            "source_type": "material_purchase_order",
            "source_id": receipt_source_ref,
            "source_ref": receipt_source_ref,
            "warehouse": cls.WAREHOUSE,
            "item_code": cls.ITEM_CODE,
            "operation": "create_stock_entry_draft",
            "quantity": "20",
            "business_date": cls.BUSINESS_DATE,
            "status_action": "create",
            "scenario_tag": cls.SCENARIO_TAG,
            "target_warehouse": cls.WAREHOUSE,
            "idempotency_key": receipt_idem,
            "items": [
                {
                    "item_code": cls.ITEM_CODE,
                    "qty": "20",
                    "uom": "米",
                    "target_warehouse": cls.WAREHOUSE,
                }
            ],
        }
        receipt = cls.client.post(
            "/api/warehouse/stock-entry-drafts",
            headers=cls._headers(
                request_id=cls._warehouse_request_id(
                    idempotency_key=receipt_idem,
                    source_ref=receipt_source_ref,
                    quantity="20",
                )
            ),
            json=receipt_payload,
        )
        assert receipt.status_code == 201, receipt.text

    @staticmethod
    def _invoice_payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": "create_purchase_invoice",
            "company": "COMP-B2",
            "purchase_no": "PO-B2-001",
            "supplier_name": "SUP-B2",
            "material_item_code": "FAB-B2",
            "qty": "20",
            "rate": "12.5",
            "posting_date": "2026-06-17",
            "due_date": "2026-07-17",
            "purchase_invoice": "PINV-B2-001",
            "source_ref": "SRC-B2-PINV-001",
            "idempotency_key": "idem-b2-pinv-001",
            "scenario_tag": "B2-PURCHASE-INVOICE-001",
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def _payment_payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": "create_purchase_payment",
            "company": "COMP-B2",
            "purchase_invoice": "PINV-B2-001",
            "supplier_name": "SUP-B2",
            "posting_date": "2026-06-17",
            "paid_amount": "100",
            "mode_of_payment": "Bank Transfer",
            "reference_no": "BANK-B2-001",
            "reference_date": "2026-06-17",
            "payment_entry": "PP-B2-001",
            "source_ref": "SRC-B2-PP-001",
            "idempotency_key": "idem-b2-pp-001",
            "scenario_tag": "B2-PURCHASE-PAYMENT-001",
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def _payment_cancel_payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": "cancel_purchase_payment",
            "company": "COMP-B2",
            "purchase_invoice": "PINV-B2-001",
            "reason": "VOID-B2-PAYMENT-001",
            "idempotency_key": "idem-b2-pp-cancel-001",
            "scenario_tag": "B2-PURCHASE-PAYMENT-CANCEL-001",
        }
        payload.update(overrides)
        return payload

    def test_purchase_invoice_and_payment_reduce_payable(self) -> None:
        self._create_received_purchase_order()

        created_invoice = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers(),
            json=self._invoice_payload(),
        )
        replay_invoice = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers(),
            json=self._invoice_payload(),
        )
        conflict_invoice = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers(),
            json=self._invoice_payload(qty="10"),
        )
        list_invoices = self.client.get(
            "/api/material-purchase/purchase-invoices?keyword=PINV-B2-001",
            headers=self._headers(),
        )

        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)
        self.assertEqual(replay_invoice.status_code, 201, replay_invoice.text)
        self.assertEqual(created_invoice.json()["data"]["id"], replay_invoice.json()["data"]["id"])
        self.assertEqual(conflict_invoice.status_code, 409)
        self.assertEqual(conflict_invoice.json()["code"], "MATERIAL_PURCHASE_IDEMPOTENCY_CONFLICT")
        self.assertEqual(list_invoices.status_code, 200)
        self.assertEqual(list_invoices.json()["data"]["items"][0]["purchase_invoice"], "PINV-B2-001")
        self.assertEqual(Decimal(str(created_invoice.json()["data"]["grand_total"])), Decimal("250.000000"))
        self.assertEqual(Decimal(str(created_invoice.json()["data"]["outstanding_amount"])), Decimal("250.000000"))

        created_payment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers(),
            json=self._payment_payload(),
        )
        replay_payment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers(),
            json=self._payment_payload(),
        )
        overpayment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers(),
            json=self._payment_payload(
                paid_amount="200",
                payment_entry="PP-B2-OVER",
                source_ref="SRC-B2-PP-OVER",
                idempotency_key="idem-b2-pp-over",
            ),
        )
        list_payments = self.client.get(
            "/api/material-purchase/purchase-payments?keyword=PP-B2-001",
            headers=self._headers(),
        )
        refreshed_invoices = self.client.get(
            "/api/material-purchase/purchase-invoices?keyword=PINV-B2-001",
            headers=self._headers(),
        )

        self.assertEqual(created_payment.status_code, 201, created_payment.text)
        self.assertEqual(replay_payment.status_code, 201, replay_payment.text)
        self.assertEqual(created_payment.json()["data"]["id"], replay_payment.json()["data"]["id"])
        self.assertEqual(overpayment.status_code, 409)
        self.assertEqual(overpayment.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertEqual(Decimal(str(created_payment.json()["data"]["outstanding_before"])), Decimal("250.000000"))
        self.assertEqual(Decimal(str(created_payment.json()["data"]["outstanding_after"])), Decimal("150.000000"))
        self.assertEqual(list_payments.status_code, 200)
        self.assertEqual(list_payments.json()["data"]["items"][0]["payment_entry"], "PP-B2-001")
        self.assertEqual(refreshed_invoices.status_code, 200)
        invoice_row = refreshed_invoices.json()["data"]["items"][0]
        self.assertEqual(invoice_row["status"], "partly_paid")
        self.assertEqual(Decimal(str(invoice_row["paid_amount"])), Decimal("100.000000"))
        self.assertEqual(Decimal(str(invoice_row["outstanding_amount"])), Decimal("150.000000"))

        with self.SessionLocal() as session:
            order = session.query(LyMaterialPurchaseOrder).one()
            line = session.query(LyMaterialPurchaseOrderItem).one()
            invoice = session.query(LyMaterialPurchaseInvoice).one()
            payment = session.query(LyMaterialPurchasePayment).one()
            self.assertEqual(str(order.status), "partially_received")
            self.assertEqual(Decimal(str(line.received_qty)), Decimal("20.000000"))
            self.assertEqual(str(invoice.status), "partly_paid")
            self.assertEqual(str(payment.payment_entry), "PP-B2-001")
            audit_actions = [row.action for row in session.query(LyOperationAuditLog).all()]
            self.assertGreaterEqual(audit_actions.count("material_purchase:write"), 3)

    def test_purchase_invoice_blocks_unreceived_quantity(self) -> None:
        self._create_received_purchase_order()
        response = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers(),
            json=self._invoice_payload(
                qty="21",
                purchase_invoice="PINV-B2-OVER",
                source_ref="SRC-B2-PINV-OVER",
                idempotency_key="idem-b2-pinv-over",
            ),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "MATERIAL_PURCHASE_CONFLICT")

    def test_purchase_payment_cancel_reopens_payable_and_is_idempotent(self) -> None:
        self._create_received_purchase_order()
        created_invoice = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers(),
            json=self._invoice_payload(),
        )
        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)
        created_payment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers(),
            json=self._payment_payload(),
        )
        self.assertEqual(created_payment.status_code, 201, created_payment.text)
        payment_id = created_payment.json()["data"]["id"]

        cancelled = self.client.post(
            f"/api/material-purchase/purchase-payments/{payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(),
        )
        replay = self.client.post(
            f"/api/material-purchase/purchase-payments/{payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(),
        )
        conflict = self.client.post(
            f"/api/material-purchase/purchase-payments/{payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(reason="VOID-B2-PAYMENT-CHANGED"),
        )
        submitted_payments = self.client.get(
            "/api/material-purchase/purchase-payments?status=submitted",
            headers=self._headers(),
        )
        cancelled_payments = self.client.get(
            "/api/material-purchase/purchase-payments?status=cancelled",
            headers=self._headers(),
        )
        invoices = self.client.get(
            "/api/material-purchase/purchase-invoices?keyword=PINV-B2-001",
            headers=self._headers(),
        )

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(cancelled.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled.json()["data"]["docstatus"], 2)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "MATERIAL_PURCHASE_CONFLICT")
        self.assertEqual(submitted_payments.status_code, 200)
        self.assertEqual(submitted_payments.json()["data"]["total"], 0)
        self.assertEqual(cancelled_payments.status_code, 200)
        self.assertEqual(cancelled_payments.json()["data"]["total"], 1)
        invoice_row = invoices.json()["data"]["items"][0]
        self.assertEqual(invoice_row["status"], "submitted")
        self.assertEqual(Decimal(str(invoice_row["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(invoice_row["outstanding_amount"])), Decimal("250.000000"))

        with self.SessionLocal() as session:
            invoice = session.query(LyMaterialPurchaseInvoice).one()
            payment = session.query(LyMaterialPurchasePayment).one()
            self.assertEqual(str(invoice.status), "submitted")
            self.assertEqual(Decimal(str(invoice.paid_amount)), Decimal("0.000000"))
            self.assertEqual(Decimal(str(invoice.outstanding_amount)), Decimal("250.000000"))
            self.assertEqual(str(payment.status), "cancelled")
            self.assertEqual(int(payment.docstatus), 2)
            self.assertEqual(session.query(LyMaterialPurchasePaymentOperation).count(), 1)

    def test_purchase_payment_cancel_second_payment_reopens_paid_invoice_to_partly_paid(self) -> None:
        self._create_received_purchase_order()
        created_invoice = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers(),
            json=self._invoice_payload(),
        )
        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)

        first_payment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers(),
            json=self._payment_payload(),
        )
        second_payment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers(),
            json=self._payment_payload(
                paid_amount="150",
                payment_entry="PP-B2-002",
                reference_no="BANK-B2-002",
                source_ref="SRC-B2-PP-002",
                idempotency_key="idem-b2-pp-002",
                scenario_tag="B2-PURCHASE-PAYMENT-002",
            ),
        )
        paid_invoices = self.client.get(
            "/api/material-purchase/purchase-invoices?keyword=PINV-B2-001",
            headers=self._headers(),
        )

        self.assertEqual(first_payment.status_code, 201, first_payment.text)
        self.assertEqual(second_payment.status_code, 201, second_payment.text)
        self.assertEqual(Decimal(str(second_payment.json()["data"]["outstanding_before"])), Decimal("150.000000"))
        self.assertEqual(Decimal(str(second_payment.json()["data"]["outstanding_after"])), Decimal("0.000000"))
        paid_invoice = paid_invoices.json()["data"]["items"][0]
        self.assertEqual(paid_invoice["status"], "paid")
        self.assertEqual(Decimal(str(paid_invoice["paid_amount"])), Decimal("250.000000"))
        self.assertEqual(Decimal(str(paid_invoice["outstanding_amount"])), Decimal("0.000000"))

        second_payment_id = second_payment.json()["data"]["id"]
        cancelled = self.client.post(
            f"/api/material-purchase/purchase-payments/{second_payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(
                reason="VOID-B2-PAYMENT-002",
                idempotency_key="idem-b2-pp-cancel-002",
                scenario_tag="B2-PURCHASE-PAYMENT-CANCEL-002",
            ),
        )
        replay = self.client.post(
            f"/api/material-purchase/purchase-payments/{second_payment_id}/cancel",
            headers=self._headers(),
            json=self._payment_cancel_payload(
                reason="VOID-B2-PAYMENT-002",
                idempotency_key="idem-b2-pp-cancel-002",
                scenario_tag="B2-PURCHASE-PAYMENT-CANCEL-002",
            ),
        )
        submitted_payments = self.client.get(
            "/api/material-purchase/purchase-payments?status=submitted",
            headers=self._headers(),
        )
        cancelled_payments = self.client.get(
            "/api/material-purchase/purchase-payments?status=cancelled",
            headers=self._headers(),
        )
        reopened_invoices = self.client.get(
            "/api/material-purchase/purchase-invoices?keyword=PINV-B2-001",
            headers=self._headers(),
        )

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(cancelled.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(cancelled.json()["data"]["payment_entry"], "PP-B2-002")
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(submitted_payments.status_code, 200)
        self.assertEqual(submitted_payments.json()["data"]["total"], 1)
        self.assertEqual(submitted_payments.json()["data"]["items"][0]["payment_entry"], "PP-B2-001")
        self.assertEqual(cancelled_payments.status_code, 200)
        self.assertEqual(cancelled_payments.json()["data"]["total"], 1)
        self.assertEqual(cancelled_payments.json()["data"]["items"][0]["payment_entry"], "PP-B2-002")
        reopened_invoice = reopened_invoices.json()["data"]["items"][0]
        self.assertEqual(reopened_invoice["status"], "partly_paid")
        self.assertEqual(Decimal(str(reopened_invoice["paid_amount"])), Decimal("100.000000"))
        self.assertEqual(Decimal(str(reopened_invoice["outstanding_amount"])), Decimal("150.000000"))

        with self.SessionLocal() as session:
            invoice = session.query(LyMaterialPurchaseInvoice).one()
            payments = {
                row.payment_entry: row
                for row in session.query(LyMaterialPurchasePayment).order_by(LyMaterialPurchasePayment.payment_entry).all()
            }
            self.assertEqual(str(invoice.status), "partly_paid")
            self.assertEqual(Decimal(str(invoice.paid_amount)), Decimal("100.000000"))
            self.assertEqual(Decimal(str(invoice.outstanding_amount)), Decimal("150.000000"))
            self.assertEqual(str(payments["PP-B2-001"].status), "submitted")
            self.assertEqual(str(payments["PP-B2-002"].status), "cancelled")
            self.assertEqual(session.query(LyMaterialPurchasePaymentOperation).count(), 1)

    def test_purchase_payment_cancel_requires_write_permission(self) -> None:
        self._create_received_purchase_order()
        created_invoice = self.client.post(
            "/api/material-purchase/purchase-invoices",
            headers=self._headers(),
            json=self._invoice_payload(),
        )
        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)
        created_payment = self.client.post(
            "/api/material-purchase/purchase-payments",
            headers=self._headers(),
            json=self._payment_payload(),
        )
        self.assertEqual(created_payment.status_code, 201, created_payment.text)
        payment_id = created_payment.json()["data"]["id"]

        blocked = self.client.post(
            f"/api/material-purchase/purchase-payments/{payment_id}/cancel",
            headers=self._headers(role="Finance Manager"),
            json=self._payment_cancel_payload(),
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            invoice = session.query(LyMaterialPurchaseInvoice).one()
            payment = session.query(LyMaterialPurchasePayment).one()
            self.assertEqual(str(invoice.status), "partly_paid")
            self.assertEqual(str(payment.status), "submitted")
            self.assertEqual(session.query(LyMaterialPurchasePaymentOperation).count(), 0)


if __name__ == "__main__":
    unittest.main()
