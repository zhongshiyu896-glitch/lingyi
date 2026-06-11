"""Local sales inventory reference draft write-closure tests."""

from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "development"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

import app.main as app_main_module
import app.routers.auth as auth_router_module
import app.routers.sales_inventory as sales_inventory_router_module
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.models.audit import Base as AuditBase
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


class SalesInventoryReferenceWriteClosureTest(unittest.TestCase):
    SCENARIO_TAG = "Z003-SALES-INV-REF-20260611-001"
    TABLE_NAME = "ly_sales_inventory_reference_draft"

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        cls.sales_inventory_router_module = importlib.reload(sales_inventory_router_module)
        cls.main_module = importlib.reload(app_main_module)
        cls.app = cls.main_module.app
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        cls.app.dependency_overrides[auth_router_module.get_db_session] = _override_db
        cls.app.dependency_overrides[cls.sales_inventory_router_module.get_db_session] = _override_db
        cls._old_main_session_local = cls.main_module.SessionLocal
        cls.main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(cls.app)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.main_module.SessionLocal = cls._old_main_session_local
        cls.app.dependency_overrides.pop(auth_router_module.get_db_session, None)
        cls.app.dependency_overrides.pop(cls.sales_inventory_router_module.get_db_session, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        self._ensure_table()
        with self.SessionLocal() as session:
            session.execute(text(f"DELETE FROM {self.TABLE_NAME}"))
            session.commit()

    def tearDown(self) -> None:
        with self.SessionLocal() as session:
            session.execute(text(f"DELETE FROM {self.TABLE_NAME}"))
            session.commit()

    def _ensure_table(self) -> None:
        with self.SessionLocal() as session:
            session.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
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
            session.commit()

    @staticmethod
    def _headers(request_id: str, role: str = "Sales Manager") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "sales.reference.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _request_id(scenario_tag: str, operation_code: str, type_code: str) -> str:
        return f"{scenario_tag}-RW-{operation_code}-{type_code}-AAA-BBB-CCC"

    @classmethod
    def _create_payload(cls, reference_type: str, reference_no: str) -> dict:
        return {
            "operation": "create_draft",
            "scenario_tag": cls.SCENARIO_TAG,
            "company": "COMP-A",
            "reference_no": reference_no,
            "reference_name": f"{reference_no}-NAME",
            "idempotency_key": f"IDEMP-{cls.SCENARIO_TAG}-{reference_type}-{reference_no}",
        }

    @classmethod
    def _deactivate_payload(cls, reference_type: str, reference_no: str) -> dict:
        return {
            "operation": "deactivate_draft",
            "scenario_tag": cls.SCENARIO_TAG,
            "company": "COMP-A",
            "idempotency_key": f"IDEMP-{cls.SCENARIO_TAG}-{reference_type}-{reference_no}-X",
            "reason": "cleanup",
        }

    def _draft_count(self) -> int:
        with self.SessionLocal() as session:
            return int(session.execute(text(f"SELECT COUNT(*) FROM {self.TABLE_NAME}")).scalar_one())

    def test_create_customer_draft_and_customer_readback(self) -> None:
        payload = self._create_payload("customer", "CUST-LOCAL-001")
        create_response = self.client.post(
            "/api/sales-inventory/reference-drafts/customers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "C", "CUS")),
            json=payload,
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["data"]["reference_no"], "CUST-LOCAL-001")

        drafts_response = self.client.get(
            "/api/sales-inventory/reference-drafts/customers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "R", "CUS")),
        )
        self.assertEqual(drafts_response.status_code, 200)
        self.assertEqual(drafts_response.json()["data"]["items"][0]["reference_no"], "CUST-LOCAL-001")

        with patch.object(
            ERPNextSalesInventoryAdapter,
            "list_customers",
            side_effect=ERPNextAdapterException(
                error_code=EXTERNAL_SERVICE_UNAVAILABLE,
                http_status=503,
                safe_message="erpnext disabled",
            ),
        ):
            customers_response = self.client.get(
                "/api/sales-inventory/customers",
                headers=self._headers(self._request_id(self.SCENARIO_TAG, "R", "CUS")),
            )
        self.assertEqual(customers_response.status_code, 200)
        self.assertEqual(customers_response.json()["data"]["items"][0]["name"], "CUST-LOCAL-001")

    def test_create_supplier_draft_and_supplier_readback(self) -> None:
        payload = self._create_payload("supplier", "SUP-LOCAL-001")
        create_response = self.client.post(
            "/api/sales-inventory/reference-drafts/suppliers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "C", "SUP")),
            json=payload,
        )
        self.assertEqual(create_response.status_code, 201)

        drafts_response = self.client.get(
            "/api/sales-inventory/reference-drafts/suppliers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "R", "SUP")),
        )
        self.assertEqual(drafts_response.status_code, 200)
        self.assertEqual(drafts_response.json()["data"]["items"][0]["reference_no"], "SUP-LOCAL-001")

        suppliers_response = self.client.get(
            "/api/sales-inventory/suppliers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "R", "SUP")),
        )
        self.assertEqual(suppliers_response.status_code, 200)
        self.assertEqual(suppliers_response.json()["data"]["items"][0]["name"], "SUP-LOCAL-001")

    def test_deactivate_customer_draft(self) -> None:
        payload = self._create_payload("customer", "CUST-LOCAL-002")
        create_response = self.client.post(
            "/api/sales-inventory/reference-drafts/customers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "C", "CUS")),
            json=payload,
        )
        draft_id = create_response.json()["data"]["id"]
        deactivate_response = self.client.post(
            f"/api/sales-inventory/reference-drafts/customers/{draft_id}/deactivate",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "X", "CUS")),
            json=self._deactivate_payload("customer", "CUST-LOCAL-002"),
        )
        self.assertEqual(deactivate_response.status_code, 200)
        self.assertEqual(deactivate_response.json()["data"]["status"], "inactive")

    def test_deactivate_supplier_draft(self) -> None:
        payload = self._create_payload("supplier", "SUP-LOCAL-002")
        create_response = self.client.post(
            "/api/sales-inventory/reference-drafts/suppliers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "C", "SUP")),
            json=payload,
        )
        draft_id = create_response.json()["data"]["id"]
        deactivate_response = self.client.post(
            f"/api/sales-inventory/reference-drafts/suppliers/{draft_id}/deactivate",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "X", "SUP")),
            json=self._deactivate_payload("supplier", "SUP-LOCAL-002"),
        )
        self.assertEqual(deactivate_response.status_code, 200)
        self.assertEqual(deactivate_response.json()["data"]["status"], "inactive")

    def test_invalid_request_id_fail_closed(self) -> None:
        response = self.client.post(
            "/api/sales-inventory/reference-drafts/customers",
            headers=self._headers("bad request id"),
            json=self._create_payload("customer", "CUST-LOCAL-003"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SALES_INVENTORY_REFERENCE_CONFLICT")
        self.assertEqual(self._draft_count(), 0)

    def test_non_local_dev_fail_closed(self) -> None:
        os.environ["APP_ENV"] = "test"
        response = self.client.post(
            "/api/sales-inventory/reference-drafts/suppliers",
            headers=self._headers(self._request_id(self.SCENARIO_TAG, "C", "SUP")),
            json=self._create_payload("supplier", "SUP-LOCAL-003"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SALES_INVENTORY_REFERENCE_CONFLICT")
        self.assertEqual(self._draft_count(), 0)
