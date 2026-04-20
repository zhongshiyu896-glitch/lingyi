"""API tests for cross-module read-only trail views (TASK-040C)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

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
from app.models.quality import LyQualityInspection
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.cross_module_view import get_db_session as cross_module_db_dep
from app.services.erpnext_job_card_adapter import WorkOrderInfo


class CrossModuleViewApiTest(unittest.TestCase):
    """Validate cross-module read-only trail APIs."""

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
        QualityBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[cross_module_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(cross_module_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyQualityInspection).delete()
            session.commit()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"X-LY-Dev-User": "cross.module.user", "X-LY-Dev-Roles": "System Manager"}

    def _seed_inspection(
        self,
        *,
        company: str,
        item_code: str,
        work_order: str | None = None,
        sales_order: str | None = None,
        status: str = "confirmed",
        accepted_qty: Decimal = Decimal("8"),
        rejected_qty: Decimal = Decimal("2"),
        defect_qty: Decimal = Decimal("1"),
    ) -> None:
        with self.SessionLocal() as session:
            inspection = LyQualityInspection(
                inspection_no=f"QI-{company}-{work_order or sales_order or 'N'}-{status}",
                company=company,
                source_type="manual",
                source_id=None,
                item_code=item_code,
                supplier="SUP-A",
                warehouse="WH-A",
                work_order=work_order,
                sales_order=sales_order,
                inspection_date=date(2026, 4, 20),
                inspected_qty=accepted_qty + rejected_qty,
                accepted_qty=accepted_qty,
                rejected_qty=rejected_qty,
                defect_qty=defect_qty,
                defect_rate=Decimal("0.1"),
                rejected_rate=Decimal("0.2"),
                result="partial",
                status=status,
                created_by="tester",
                updated_by="tester",
            )
            session.add(inspection)
            session.commit()

    def test_work_order_trail_returns_stock_and_quality_chain(self) -> None:
        self._seed_inspection(company="COMP-A", item_code="ITEM-A", work_order="WO-001")

        def _list_resource_side_effect(*, doctype, fields, filters, page, page_size, order_by):  # noqa: ARG001
            if doctype == "Stock Entry":
                return [{"name": "STE-001"}]
            if doctype == "Stock Ledger Entry":
                return [
                    {
                        "name": "SLE-001",
                        "company": "COMP-A",
                        "item_code": "ITEM-A",
                        "warehouse": "WH-A",
                        "posting_date": "2026-04-20",
                        "posting_time": "08:30:00",
                        "actual_qty": "-2",
                        "qty_after_transaction": "18",
                        "voucher_type": "Stock Entry",
                        "voucher_no": "STE-001",
                    }
                ]
            return []

        with patch(
            "app.services.erpnext_job_card_adapter.ERPNextJobCardAdapter.get_work_order",
            return_value=WorkOrderInfo(name="WO-001", production_item="ITEM-A", company="COMP-A"),
        ), patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter._list_resource",
            side_effect=_list_resource_side_effect,
        ):
            response = self.client.get(
                "/api/cross-module/work-order-trail/WO-001?company=COMP-A",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["work_order"]["work_order_id"], "WO-001")
        self.assertEqual(len(payload["stock_entries"]), 1)
        self.assertEqual(len(payload["quality_inspections"]), 1)
        self.assertEqual(payload["summary"]["stock_entry_count"], 1)
        self.assertEqual(payload["summary"]["quality_inspection_count"], 1)

    def test_sales_order_trail_returns_delivery_and_quality_chain(self) -> None:
        self._seed_inspection(company="COMP-A", item_code="ITEM-A", sales_order="SO-001")
        self._seed_inspection(company="COMP-A", item_code="ITEM-A", sales_order="SO-001", status="cancelled")

        def _list_resource_side_effect(*, doctype, fields, filters, page, page_size, order_by):  # noqa: ARG001
            if doctype == "Delivery Note":
                return [{"name": "DN-001"}]
            if doctype == "Stock Ledger Entry":
                return [
                    {
                        "name": "SLE-002",
                        "company": "COMP-A",
                        "item_code": "ITEM-A",
                        "warehouse": "WH-A",
                        "posting_date": "2026-04-20",
                        "posting_time": "09:10:00",
                        "actual_qty": "-3",
                        "qty_after_transaction": "15",
                        "voucher_type": "Delivery Note",
                        "voucher_no": "DN-001",
                    }
                ]
            return []

        with patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter.get_sales_order",
            return_value={
                "name": "SO-001",
                "company": "COMP-A",
                "customer": "CUST-A",
                "transaction_date": "2026-04-18",
                "delivery_date": "2026-04-25",
                "status": "To Deliver",
                "docstatus": 1,
                "items": [{"item_code": "ITEM-A", "qty": "10"}],
            },
        ), patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter._list_resource",
            side_effect=_list_resource_side_effect,
        ):
            response = self.client.get(
                "/api/cross-module/sales-order-trail/SO-001?company=COMP-A",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["sales_order"]["sales_order_id"], "SO-001")
        self.assertEqual(len(payload["delivery_notes"]), 1)
        self.assertEqual(len(payload["quality_inspections"]), 1)
        self.assertEqual(payload["summary"]["ordered_qty"], "10")
        self.assertEqual(payload["summary"]["delivered_qty"], "3")

    def test_company_filter_mismatch_returns_hidden_not_found(self) -> None:
        with patch(
            "app.services.erpnext_job_card_adapter.ERPNextJobCardAdapter.get_work_order",
            return_value=WorkOrderInfo(name="WO-009", production_item="ITEM-A", company="COMP-A"),
        ):
            response = self.client.get(
                "/api/cross-module/work-order-trail/WO-009?company=COMP-B",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "ERPNEXT_RESOURCE_NOT_FOUND")
