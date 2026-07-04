"""B4 FastAPI-native delivery note + sales invoice flow."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
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
from app.models.audit import LySecurityAuditLog
from app.models.quality import Base as QualityBase
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LyDeliveryInvoiceOperation
from app.models.sales_order import LySalesReturn
from app.models.sales_order import LySalesReturnOperation
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderItem
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep
from app.services.warehouse_service import WarehouseService


class SalesDeliveryInvoiceFlowTest(unittest.TestCase):
    """Validate B4 delivery invoice writes real local data and stock movement."""

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
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        os.environ.pop("LINGYI_FASTAPI_ROLE_ACTIONS_JSON", None)
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LySalesReturnOperation).delete()
            session.query(LySalesReturn).delete()
            session.query(LyDeliveryInvoiceOperation).delete()
            session.query(LyDeliveryInvoice).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrder).delete()
            session.query(LyWarehouseStockLedgerEntry).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()

            order = LySalesOrder(
                sales_order_no="SO-B4-001",
                source_order_ref="SRC-SO-B4-001",
                company="COMP-A",
                customer="CUST-A",
                status="planned",
                docstatus=0,
                transaction_date=date(2026, 6, 17),
                delivery_date=date(2026, 6, 30),
                currency="CNY",
                grand_total=Decimal("800"),
                idempotency_key="idem-so-b4-001",
                request_hash="hash-so-b4-001",
                scenario_tag="B4-SALES-ORDER",
                payload={},
                created_by="seed",
            )
            session.add(order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(order.id),
                    company="COMP-A",
                    line_no=1,
                    sales_order_item="SO-B4-001-001",
                    item_code="DEMO-TEE",
                    item_name="Demo Tee",
                    qty=Decimal("10"),
                    planned_qty=Decimal("10"),
                    delivered_qty=Decimal("0"),
                    rate=Decimal("80"),
                    amount=Decimal("800"),
                    uom="件",
                    warehouse="WH-FG",
                    delivery_date=date(2026, 6, 30),
                )
            )
            receipt = LyWarehouseStockEntryDraft(
                company="COMP-A",
                purpose="Material Receipt",
                source_type="finished_goods_inbound",
                source_id="FG-IN-B4-001",
                source_warehouse=None,
                target_warehouse="WH-FG",
                status="pending_outbox",
                created_by="seed",
                created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
                idempotency_key="idem-fg-in-b4-001",
                event_key="fg-in-b4-001",
            )
            session.add(receipt)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(receipt.id),
                    company="COMP-A",
                    item_code="DEMO-TEE",
                    qty=Decimal("10"),
                    uom="件",
                    source_warehouse=None,
                    target_warehouse="WH-FG",
                )
            )
            session.add(
                LyWarehouseStockEntryOutboxEvent(
                    draft_id=int(receipt.id),
                    event_type="finished_goods_inbound_sync",
                    event_key="fg-in-b4-001",
                    payload={"business_date": "2026-06-17"},
                    status="in_pending",
                    retry_count=0,
                    created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc),
                )
            )
            session.flush()
            WarehouseService(session=session)._refresh_projected_ledger_for_draft(receipt)
            session.commit()

    @staticmethod
    def _headers(role: str = "System Manager") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "b4.delivery.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": "req-b4-delivery",
        }

    @staticmethod
    def _cancel_payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": "cancel_delivery_invoice",
            "company": "COMP-A",
            "delivery_note": "DN-B4-001",
            "sales_invoice": "SI-B4-001",
            "reason": "VOID-B4-DELIVERY-001",
            "idempotency_key": "idem-b4-delivery-cancel-001",
            "scenario_tag": "B4-DELIVERY-CANCEL-001",
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def _return_payload(delivery_invoice_id: int, **overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": "create_sales_return",
            "company": "COMP-A",
            "delivery_invoice_id": delivery_invoice_id,
            "delivery_note": "DN-B4-001",
            "sales_invoice": "SI-B4-001",
            "return_no": "SR-B4-001",
            "return_qty": 2,
            "posting_date": "2026-06-18",
            "warehouse": "WH-RETURNS",
            "reason": "客户尺码不符退回",
            "source_ref": "SRC-B4-RETURN-001",
            "idempotency_key": "idem-b4-sales-return-001",
            "scenario_tag": "B4-SALES-RETURN-001",
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def _return_cancel_payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "operation": "cancel_sales_return",
            "company": "COMP-A",
            "return_no": "SR-B4-001",
            "sales_invoice": "SI-B4-001",
            "reason": "VOID-B4-SALES-RETURN-001",
            "idempotency_key": "idem-b4-sales-return-cancel-001",
            "scenario_tag": "B4-SALES-RETURN-CANCEL-001",
        }
        payload.update(overrides)
        return payload

    @staticmethod
    def _set_fastapi_scope(**overrides: list[str]) -> None:
        scope = {
            "companies": ["COMP-A"],
            "customers": ["CUST-A"],
            "item_codes": ["DEMO-TEE"],
            "warehouses": ["WH-FG"],
        }
        scope.update(overrides)
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_ROLE_ACTIONS_JSON"] = json.dumps(
            {"roles": {"Sales Manager": ["sales_inventory:write"]}}
        )
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps({"users": {"b4.delivery.user": scope}})

    @staticmethod
    def _payload(**overrides) -> dict[str, object]:
        payload: dict[str, object] = {
            "company": "COMP-A",
            "sales_order": "SO-B4-001",
            "customer": "CUST-A",
            "item_code": "DEMO-TEE",
            "item_name": "Demo Tee",
            "warehouse": "WH-FG",
            "delivered_qty": 4,
            "uom": "件",
            "rate": 80,
            "posting_date": "2026-06-17",
            "due_date": "2026-07-01",
            "delivery_note": "DN-B4-001",
            "sales_invoice": "SI-B4-001",
            "source_ref": "SRC-B4-001",
            "idempotency_key": "idem-b4-delivery-001",
            "scenario_tag": "B4-DELIVERY-INVOICE-001",
            "operation": "create_delivery_invoice",
        }
        payload.update(overrides)
        return payload

    def test_delivery_and_invoice_lists_do_not_fallback_to_readiness_seed(self) -> None:
        delivery_notes = self.client.get(
            "/api/sales-inventory/delivery-notes",
            headers=self._headers(),
        )
        sales_invoices = self.client.get(
            "/api/sales-inventory/sales-invoices",
            headers=self._headers(),
        )

        self.assertEqual(delivery_notes.status_code, 200, delivery_notes.text)
        self.assertEqual(delivery_notes.json()["data"]["items"], [])
        self.assertEqual(delivery_notes.json()["data"]["total"], 0)
        self.assertEqual(sales_invoices.status_code, 200, sales_invoices.text)
        self.assertEqual(sales_invoices.json()["data"]["items"], [])
        self.assertEqual(sales_invoices.json()["data"]["total"], 0)

    def test_delivery_invoice_create_replay_and_local_readbacks(self) -> None:
        created = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(),
        )
        replay = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(),
        )
        conflict = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(delivered_qty=5),
        )
        delivery_notes = self.client.get(
            "/api/sales-inventory/delivery-notes?sales_order=SO-B4-001",
            headers=self._headers(),
        )
        sales_invoices = self.client.get(
            "/api/sales-inventory/sales-invoices?sales_order=SO-B4-001",
            headers=self._headers(),
        )
        delivery_invoices = self.client.get(
            "/api/sales-inventory/delivery-invoices?keyword=SI-B4-001",
            headers=self._headers(),
        )
        fulfillment = self.client.get(
            "/api/sales-inventory/sales-order-fulfillment?company=COMP-A&item_code=DEMO-TEE&warehouse=WH-FG",
            headers=self._headers(),
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(created.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["financial_ledger_status"], "posted")
        self.assertEqual(created.json()["data"]["financial_ledger_status_name"], "总账已归集")
        self.assertEqual(Decimal(str(created.json()["data"]["financial_ledger_revenue_amount"])), Decimal("320.000000"))
        self.assertEqual(Decimal(str(created.json()["data"]["financial_ledger_cash_in_amount"])), Decimal("0"))
        self.assertEqual(Decimal(str(created.json()["data"]["financial_ledger_outstanding_amount"])), Decimal("320.000000"))
        self.assertFalse(created.json()["data"]["financial_ledger_closed"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "SALES_DELIVERY_INVOICE_CONFLICT")
        self.assertEqual(delivery_notes.status_code, 200)
        self.assertEqual(delivery_notes.json()["data"]["items"][0]["delivery_note"], "DN-B4-001")
        self.assertEqual(sales_invoices.status_code, 200)
        sales_invoice_row = sales_invoices.json()["data"]["items"][0]
        self.assertEqual(sales_invoice_row["sales_invoice"], "SI-B4-001")
        self.assertEqual(sales_invoice_row["financial_ledger_status"], "posted")
        self.assertEqual(Decimal(str(sales_invoice_row["financial_ledger_revenue_amount"])), Decimal("320.000000"))
        self.assertEqual(delivery_invoices.status_code, 200)
        delivery_invoice_row = delivery_invoices.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(delivery_invoice_row["outstanding_amount"])), Decimal("320.000000"))
        self.assertEqual(delivery_invoice_row["financial_ledger_status"], "posted")
        self.assertIn("销售发票 SI-B4-001", delivery_invoice_row["financial_ledger_source_note"])
        self.assertEqual(fulfillment.status_code, 200, fulfillment.text)
        fulfillment_item = fulfillment.json()["data"]["items"][0]
        self.assertEqual(fulfillment_item["sales_order"], "SO-B4-001")
        self.assertEqual(Decimal(str(fulfillment_item["ordered_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(fulfillment_item["actual_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(fulfillment_item["fulfillment_rate"])), Decimal("0.4"))

        with self.SessionLocal() as session:
            order_item = session.query(LySalesOrderItem).one()
            self.assertEqual(Decimal(str(order_item.delivered_qty)), Decimal("4.000000"))
            ledger = WarehouseService(session=session).list_local_stock_ledger(
                company="COMP-A",
                warehouse="WH-FG",
                item_code="DEMO-TEE",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            self.assertEqual([Decimal(str(row.actual_qty)) for row in ledger.items], [Decimal("10.000000"), Decimal("-4.000000")])
            self.assertEqual(Decimal(str(ledger.items[-1].qty_after_transaction)), Decimal("6.000000"))
            self.assertEqual([row.voucher_type for row in ledger.items], ["Stock Entry Draft/Material Receipt", "Stock Entry Draft/Material Issue"])
            summary = WarehouseService(session=session).get_local_stock_summary(
                company="COMP-A",
                warehouse="WH-FG",
                item_code="DEMO-TEE",
            )
            self.assertEqual(len(summary.items), 1)
            self.assertEqual(Decimal(str(summary.items[0].actual_qty)), Decimal("6.000000"))
            self.assertEqual(Decimal(str(summary.items[0].actual_qty)), Decimal(str(ledger.items[-1].qty_after_transaction)))
            self.assertEqual(Decimal(str(summary.items[0].actual_qty)), sum(Decimal(str(row.actual_qty)) for row in ledger.items))
            durable_rows = (
                session.query(LyWarehouseStockLedgerEntry)
                .filter(
                    LyWarehouseStockLedgerEntry.company == "COMP-A",
                    LyWarehouseStockLedgerEntry.warehouse == "WH-FG",
                    LyWarehouseStockLedgerEntry.item_code == "DEMO-TEE",
                )
                .order_by(LyWarehouseStockLedgerEntry.sort_at.asc(), LyWarehouseStockLedgerEntry.id.asc())
                .all()
            )
            self.assertEqual([Decimal(str(row.actual_qty)) for row in durable_rows], [Decimal("10.000000"), Decimal("-4.000000")])
            self.assertEqual([str(row.status) for row in durable_rows], ["active", "active"])
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("sales_inventory:write", audit_actions)

    def test_delivery_invoice_blocks_stock_shortage(self) -> None:
        response = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(delivered_qty=11, idempotency_key="idem-b4-delivery-shortage", source_ref="SRC-B4-SHORT"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SALES_DELIVERY_INVOICE_STOCK_SHORTAGE")

    def test_delivery_invoice_splits_same_item_lines_and_reports_quantity_status(self) -> None:
        with self.SessionLocal() as session:
            order = session.query(LySalesOrder).filter_by(sales_order_no="SO-B4-001").one()
            first_line = session.query(LySalesOrderItem).filter_by(sales_order_id=int(order.id), line_no=1).one()
            first_line.qty = Decimal("6")
            first_line.amount = Decimal("480")
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(order.id),
                    company="COMP-A",
                    line_no=2,
                    sales_order_item="SO-B4-001-002",
                    item_code="DEMO-TEE",
                    item_name="Demo Tee",
                    qty=Decimal("4"),
                    planned_qty=Decimal("4"),
                    delivered_qty=Decimal("0"),
                    rate=Decimal("80"),
                    amount=Decimal("320"),
                    uom="件",
                    warehouse="WH-FG",
                    delivery_date=date(2026, 6, 30),
                )
            )
            session.commit()

        first_delivery = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(
                delivered_qty=8,
                delivery_note="DN-B4-PARTIAL",
                sales_invoice="SI-B4-PARTIAL",
                source_ref="SRC-B4-PARTIAL",
                idempotency_key="idem-b4-delivery-partial",
            ),
        )
        self.assertEqual(first_delivery.status_code, 201, first_delivery.text)
        list_after_partial = self.client.get("/api/sales-inventory/sales-orders?company=COMP-A", headers=self._headers())
        self.assertEqual(list_after_partial.status_code, 200, list_after_partial.text)
        partial_order = list_after_partial.json()["data"]["items"][0]
        self.assertEqual(partial_order["delivery_status"], "partial")
        self.assertEqual(partial_order["delivery_status_name"], "部分发货")
        self.assertEqual(Decimal(str(partial_order["ordered_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(partial_order["delivered_qty"])), Decimal("8.000000"))

        second_delivery = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(
                delivered_qty=2,
                delivery_note="DN-B4-FULL",
                sales_invoice="SI-B4-FULL",
                source_ref="SRC-B4-FULL",
                idempotency_key="idem-b4-delivery-full",
            ),
        )
        self.assertEqual(second_delivery.status_code, 201, second_delivery.text)
        list_after_full = self.client.get("/api/sales-inventory/sales-orders?company=COMP-A", headers=self._headers())
        self.assertEqual(list_after_full.status_code, 200, list_after_full.text)
        full_order = list_after_full.json()["data"]["items"][0]
        self.assertEqual(full_order["delivery_status"], "fulfilled")
        self.assertEqual(full_order["delivery_status_name"], "已发货")
        self.assertEqual(Decimal(str(full_order["ordered_qty"])), Decimal("10.000000"))
        self.assertEqual(Decimal(str(full_order["delivered_qty"])), Decimal("10.000000"))

        with self.SessionLocal() as session:
            lines = session.query(LySalesOrderItem).order_by(LySalesOrderItem.line_no.asc()).all()
            self.assertEqual([Decimal(str(line.delivered_qty)) for line in lines], [Decimal("6.000000"), Decimal("4.000000")])

    def test_delivery_invoice_ignores_unprojected_stock_drafts(self) -> None:
        with self.SessionLocal() as session:
            session.query(LyWarehouseStockLedgerEntry).delete()
            session.commit()

        response = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(
                delivery_note="DN-B4-UNPROJECTED",
                sales_invoice="SI-B4-UNPROJECTED",
                source_ref="SRC-B4-UNPROJECTED",
                idempotency_key="idem-b4-delivery-unprojected",
            ),
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SALES_DELIVERY_INVOICE_STOCK_SHORTAGE")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyDeliveryInvoice).count(), 0)
            self.assertEqual(Decimal(str(session.query(LySalesOrderItem).one().delivered_qty)), Decimal("0.000000"))

    def test_delivery_invoice_cancel_denies_fastapi_resource_scope_and_does_not_reverse(self) -> None:
        created = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(created.status_code, 201, created.text)

        self._set_fastapi_scope(warehouses=["WH-OTHER"])
        response = self.client.post(
            f"/api/sales-inventory/delivery-invoices/{created.json()['data']['id']}/cancel",
            headers=self._headers(role="Sales Manager"),
            json=self._cancel_payload(
                idempotency_key="idem-b4-delivery-cancel-scope-deny",
                scenario_tag="B4-DELIVERY-CANCEL-SCOPE-DENY",
            ),
        )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")
        with self.SessionLocal() as session:
            invoice = session.query(LyDeliveryInvoice).one()
            order_item = session.query(LySalesOrderItem).one()
            self.assertEqual(str(invoice.status), "submitted")
            self.assertEqual(Decimal(str(order_item.delivered_qty)), Decimal("4.000000"))
            self.assertEqual(session.query(LyDeliveryInvoiceOperation).count(), 0)
            security = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(security)
            self.assertEqual(security.event_type, "RESOURCE_ACCESS_DENIED")
            self.assertEqual(security.resource_type, "DELIVERY_INVOICE")
            self.assertEqual(security.resource_no, "DN-B4-001")

    def test_delivery_invoice_requires_local_sales_order(self) -> None:
        response = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(
                sales_order="SO-B4-MISSING",
                delivery_note="DN-B4-MISSING",
                sales_invoice="SI-B4-MISSING",
                source_ref="SRC-B4-MISSING",
                idempotency_key="idem-b4-delivery-missing-order",
            ),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "SALES_DELIVERY_ORDER_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyDeliveryInvoice).count(), 0)

    def test_sales_return_create_replay_and_independent_receipt_readbacks(self) -> None:
        created_invoice = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)
        invoice_id = int(created_invoice.json()["data"]["id"])

        created_return = self.client.post(
            "/api/sales-inventory/sales-returns",
            headers=self._headers(),
            json=self._return_payload(invoice_id),
        )
        replay = self.client.post(
            "/api/sales-inventory/sales-returns",
            headers=self._headers(),
            json=self._return_payload(invoice_id),
        )
        conflict = self.client.post(
            "/api/sales-inventory/sales-returns",
            headers=self._headers(),
            json=self._return_payload(invoice_id, return_qty=1),
        )
        listed = self.client.get(
            "/api/sales-inventory/sales-returns?keyword=SR-B4-001",
            headers=self._headers(),
        )

        self.assertEqual(created_return.status_code, 201, created_return.text)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(created_return.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(conflict.json()["code"], "SALES_RETURN_CONFLICT")
        data = created_return.json()["data"]
        self.assertEqual(data["return_no"], "SR-B4-001")
        self.assertEqual(data["warehouse"], "WH-RETURNS")
        self.assertEqual(data["warehouse_draft_source_type"], "customer_sales_return")
        self.assertEqual(data["receivable_adjustment_status"], "pending_confirmation")
        self.assertEqual(Decimal(str(data["delivered_qty"])), Decimal("4.000000"))
        self.assertEqual(Decimal(str(data["return_qty"])), Decimal("2.000000"))
        self.assertEqual(Decimal(str(data["return_amount"])), Decimal("160.000000"))
        self.assertEqual(Decimal(str(data["receivable_adjustment_suggestion"])), Decimal("160.000000"))
        self.assertEqual(Decimal(str(data["returned_qty_before"])), Decimal("0"))
        self.assertEqual(Decimal(str(data["returned_qty_after"])), Decimal("2.000000"))
        self.assertEqual(Decimal(str(data["remaining_returnable_qty"])), Decimal("2.000000"))
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["data"]["total"], 1)
        self.assertEqual(listed.json()["data"]["items"][0]["return_no"], "SR-B4-001")

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySalesReturn).count(), 1)
            order_item = session.query(LySalesOrderItem).one()
            self.assertEqual(Decimal(str(order_item.delivered_qty)), Decimal("4.000000"))
            draft = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == "customer_sales_return")
                .one()
            )
            self.assertEqual(draft.purpose, "Material Receipt")
            self.assertEqual(draft.source_id, "SR-B4-001")
            self.assertEqual(draft.target_warehouse, "WH-RETURNS")
            event = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == int(draft.id))
                .one()
            )
            self.assertEqual(event.event_type, "customer_sales_return_receipt_sync")
            normal_ledger = WarehouseService(session=session).list_local_stock_ledger(
                company="COMP-A",
                warehouse="WH-FG",
                item_code="DEMO-TEE",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            self.assertEqual([Decimal(str(row.actual_qty)) for row in normal_ledger.items], [Decimal("10.000000"), Decimal("-4.000000")])
            return_ledger = WarehouseService(session=session).list_local_stock_ledger(
                company="COMP-A",
                warehouse="WH-RETURNS",
                item_code="DEMO-TEE",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            self.assertEqual([Decimal(str(row.actual_qty)) for row in return_ledger.items], [Decimal("2.000000")])

    def test_sales_return_blocks_over_return_quantity_before_stock_draft(self) -> None:
        created_invoice = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)

        response = self.client.post(
            "/api/sales-inventory/sales-returns",
            headers=self._headers(),
            json=self._return_payload(
                int(created_invoice.json()["data"]["id"]),
                return_qty=5,
                idempotency_key="idem-b4-sales-return-over",
                source_ref="SRC-B4-RETURN-OVER",
                return_no="SR-B4-OVER",
            ),
        )

        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(response.json()["code"], "SALES_RETURN_QTY_EXCEEDED")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySalesReturn).count(), 0)
            self.assertEqual(
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == "customer_sales_return")
                .count(),
                0,
            )

    def test_sales_return_cancel_reverses_pending_receipt_without_touching_delivery(self) -> None:
        created_invoice = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)
        created_return = self.client.post(
            "/api/sales-inventory/sales-returns",
            headers=self._headers(),
            json=self._return_payload(int(created_invoice.json()["data"]["id"])),
        )
        self.assertEqual(created_return.status_code, 201, created_return.text)
        return_id = int(created_return.json()["data"]["id"])

        cancelled = self.client.post(
            f"/api/sales-inventory/sales-returns/{return_id}/cancel",
            headers=self._headers(),
            json=self._return_cancel_payload(),
        )
        replay = self.client.post(
            f"/api/sales-inventory/sales-returns/{return_id}/cancel",
            headers=self._headers(),
            json=self._return_cancel_payload(),
        )

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(Decimal(str(cancelled.json()["data"]["receivable_adjustment_suggestion"])), Decimal("0"))
        with self.SessionLocal() as session:
            return_row = session.query(LySalesReturn).one()
            invoice_row = session.query(LyDeliveryInvoice).one()
            order_item = session.query(LySalesOrderItem).one()
            self.assertEqual(return_row.status, "cancelled")
            self.assertEqual(invoice_row.status, "submitted")
            self.assertEqual(Decimal(str(order_item.delivered_qty)), Decimal("4.000000"))
            draft = (
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == "customer_sales_return")
                .one()
            )
            self.assertEqual(draft.status, "cancelled")
            events = (
                session.query(LyWarehouseStockEntryOutboxEvent)
                .filter(LyWarehouseStockEntryOutboxEvent.draft_id == int(draft.id))
                .all()
            )
            self.assertEqual({event.status for event in events}, {"cancelled"})
            return_ledger = WarehouseService(session=session).list_local_stock_ledger(
                company="COMP-A",
                warehouse="WH-RETURNS",
                item_code="DEMO-TEE",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            self.assertEqual(return_ledger.items, [])

    def test_sales_return_create_denies_fastapi_resource_scope_and_does_not_write(self) -> None:
        created_invoice = self.client.post(
            "/api/sales-inventory/delivery-invoices",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(created_invoice.status_code, 201, created_invoice.text)

        self._set_fastapi_scope(warehouses=["WH-OTHER"])
        response = self.client.post(
            "/api/sales-inventory/sales-returns",
            headers=self._headers(role="Sales Manager"),
            json=self._return_payload(int(created_invoice.json()["data"]["id"])),
        )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], "RESOURCE_ACCESS_DENIED")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySalesReturn).count(), 0)
            self.assertEqual(
                session.query(LyWarehouseStockEntryDraft)
                .filter(LyWarehouseStockEntryDraft.source_type == "customer_sales_return")
                .count(),
                0,
            )
            security = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(security)
            self.assertEqual(security.event_type, "RESOURCE_ACCESS_DENIED")


if __name__ == "__main__":
    unittest.main()
