"""Task 4 first-batch readonly endpoints backed by existing local DB tables."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

_IMPORT_ENV_BACKUP = {
    "APP_ENV": os.environ.get("APP_ENV"),
    "LINGYI_DB_URL": os.environ.get("LINGYI_DB_URL"),
    "LINGYI_ALLOW_DEV_AUTH": os.environ.get("LINGYI_ALLOW_DEV_AUTH"),
    "LINGYI_ERPNEXT_BASE_URL": os.environ.get("LINGYI_ERPNEXT_BASE_URL"),
    "LINGYI_PERMISSION_SOURCE": os.environ.get("LINGYI_PERMISSION_SOURCE"),
}
os.environ["APP_ENV"] = "development"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.routers.auth as auth_router
import app.routers.bom as bom_router
import app.routers.production as production_router
import app.routers.sales_inventory as sales_inventory_router
import app.routers.warehouse as warehouse_router
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.quality import Base as QualityBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent


class Task4FirstReadonlyRealDbTest(unittest.TestCase):
    """Verify first-batch readonly APIs query existing DB tables in dev/local mode."""

    REFERENCE_TABLE = "ly_sales_inventory_reference_draft"
    DB_DEPENDENCY_MODULES = {
        "app.routers.auth",
        "app.routers.bom",
        "app.routers.production",
        "app.routers.sales_inventory",
        "app.routers.warehouse",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls._old_env = dict(_IMPORT_ENV_BACKUP)
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        AuditBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        QualityBase.metadata.create_all(bind=cls.engine)
        cls._ensure_reference_table()
        cls._old_main_session_local = main_module.SessionLocal
        cls._install_dependency_overrides()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_router.get_db_session, None)
        app.dependency_overrides.pop(sales_inventory_router.get_db_session, None)
        app.dependency_overrides.pop(warehouse_router.get_db_session, None)
        app.dependency_overrides.pop(bom_router.get_db_session, None)
        app.dependency_overrides.pop(production_router.get_db_session, None)
        cls.engine.dispose()
        for key, value in cls._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    @classmethod
    def _ensure_reference_table(cls) -> None:
        with cls.engine.begin() as connection:
            connection.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {cls.REFERENCE_TABLE} (
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

    @classmethod
    def _override_db(cls):
        db = cls.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    @classmethod
    def _install_dependency_overrides(cls) -> None:
        for dependency in cls._db_dependency_targets():
            app.dependency_overrides[dependency] = cls._override_db
        main_module.SessionLocal = cls.SessionLocal

    @classmethod
    def _db_dependency_targets(cls):
        static_targets = [
            auth_router.get_db_session,
            sales_inventory_router.get_db_session,
            warehouse_router.get_db_session,
            bom_router.get_db_session,
            production_router.get_db_session,
        ]
        seen: set[int] = set()
        for dependency in [*static_targets, *cls._route_db_dependency_targets()]:
            ident = id(dependency)
            if ident not in seen:
                seen.add(ident)
                yield dependency

    @classmethod
    def _route_db_dependency_targets(cls):
        for route in app.routes:
            dependant = getattr(route, "dependant", None)
            if dependant is None:
                continue
            for dependency in cls._iter_dependency_calls(dependant):
                if (
                    getattr(dependency, "__name__", None) == "get_db_session"
                    and getattr(dependency, "__module__", None) in cls.DB_DEPENDENCY_MODULES
                ):
                    yield dependency

    @classmethod
    def _iter_dependency_calls(cls, dependant):
        for dependency in getattr(dependant, "dependencies", ()):
            call = getattr(dependency, "call", None)
            if call is not None:
                yield call
            yield from cls._iter_dependency_calls(dependency)

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        self._install_dependency_overrides()
        self._reset_db()
        self._seed_real_readonly_rows()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "X-LY-Dev-User": "task4.readonly.user",
            "X-LY-Dev-Roles": "System Manager",
        }

    def _reset_db(self) -> None:
        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyProductionPlan).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.execute(text(f"DELETE FROM {self.REFERENCE_TABLE}"))
            session.commit()

    def _seed_real_readonly_rows(self) -> None:
        created_at = datetime(2026, 6, 1, 8, 0, tzinfo=timezone.utc)
        with self.SessionLocal() as session:
            session.execute(
                text(
                    f"""
                    INSERT INTO {self.REFERENCE_TABLE} (
                        reference_type, reference_no, reference_name, company, status,
                        scenario_tag, idempotency_key, created_by, created_at
                    ) VALUES
                        ('customer', 'CUST-T4-001', '任务四客户', 'COMP-T4', 'active',
                         'TASK4-READ-001', 'IDEMP-T4-CUST-001', 'seed', '2026-06-01T08:00:00+00:00'),
                        ('customer', 'CUST-T4-OFF', '停用客户', 'COMP-T4', 'inactive',
                         'TASK4-READ-002', 'IDEMP-T4-CUST-002', 'seed', '2026-06-01T08:00:00+00:00'),
                        ('supplier', 'SUP-T4-001', '任务四供应商', 'COMP-T4', 'active',
                         'TASK4-READ-003', 'IDEMP-T4-SUP-001', 'seed', '2026-06-01T08:00:00+00:00')
                    """
                )
            )
            sales_draft = LyWarehouseStockEntryDraft(
                id=1,
                company="COMP-T4",
                purpose="Material Issue",
                source_type="sales_order_local",
                source_id="SRC-SO-T4-001",
                source_warehouse="WH-FG",
                target_warehouse=None,
                status="pending_outbox",
                created_by="seed",
                created_at=created_at,
                idempotency_key="IDEMP-SO-T4-001",
                event_key="EVT-SO-T4-001",
            )
            stock_draft = LyWarehouseStockEntryDraft(
                id=2,
                company="COMP-T4",
                purpose="Material Receipt",
                source_type="warehouse_local_read_projection",
                source_id="STOCK-T4-001",
                source_warehouse=None,
                target_warehouse="WH-RAW",
                status="pending_outbox",
                created_by="seed",
                created_at=created_at,
                idempotency_key="IDEMP-STOCK-T4-001",
                event_key="EVT-STOCK-T4-001",
            )
            session.add_all([sales_draft, stock_draft])
            session.add_all(
                [
                    LyWarehouseStockEntryDraftItem(
                        id=1,
                        draft_id=1,
                        company="COMP-T4",
                        item_code="ITEM-T4",
                        qty=Decimal("5"),
                        uom="PCS",
                        source_warehouse="WH-FG",
                        target_warehouse=None,
                    ),
                    LyWarehouseStockEntryDraftItem(
                        id=2,
                        draft_id=2,
                        company="COMP-T4",
                        item_code="MAT-T4",
                        qty=Decimal("12"),
                        uom="M",
                        source_warehouse=None,
                        target_warehouse="WH-RAW",
                    ),
                ]
            )
            session.add(
                LyWarehouseStockEntryOutboxEvent(
                    id=1,
                    draft_id=1,
                    event_type="sales_order_write_sync",
                    event_key="OUT-SO-T4-001",
                    payload={
                        "scenario_tag": "TASK4-READ-ORDER",
                        "sales_order_no": "SO-T4-001",
                        "source_order_ref": "SRC-SO-T4-001",
                        "company": "COMP-T4",
                        "customer": "CUST-T4-001",
                        "transaction_date": "2026-06-01",
                        "delivery_date": "2026-06-08",
                        "grand_total": "100.00",
                        "currency": "CNY",
                        "items": [
                            {
                                "item_code": "ITEM-T4",
                                "qty": "5",
                                "rate": "20.00",
                                "amount": "100.00",
                                "uom": "PCS",
                                "warehouse": "WH-FG",
                            }
                        ],
                    },
                    status="in_pending",
                    retry_count=0,
                    created_at=created_at,
                )
            )
            session.add(
                LyApparelBom(
                    id=101,
                    bom_no="BOM-T4-001",
                    item_code="STYLE-T4",
                    version_no="V1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add_all(
                [
                    LyApparelBomItem(
                        id=1001,
                        bom_id=101,
                        material_item_code="FAB-T4-001",
                        color="BLACK",
                        size="150CM",
                        qty_per_piece=Decimal("2.5"),
                        loss_rate=Decimal("0.05"),
                        uom="M",
                        remark="面料棉布",
                    ),
                    LyApparelBomItem(
                        id=1002,
                        bom_id=101,
                        material_item_code="ACC-T4-001",
                        color=None,
                        size=None,
                        qty_per_piece=Decimal("1"),
                        loss_rate=Decimal("0"),
                        uom="PCS",
                        remark="辅料拉链",
                    ),
                ]
            )
            session.add(
                LyProductionPlan(
                    id=201,
                    plan_no="PLAN-T4-001",
                    company="COMP-T4",
                    sales_order="SO-T4-001",
                    sales_order_item="SO-T4-001-1",
                    customer="CUST-T4-001",
                    item_code="STYLE-T4",
                    bom_id=101,
                    bom_version="V1",
                    planned_qty=Decimal("10"),
                    status="planned",
                    idempotency_key="IDEMP-PLAN-T4-001",
                    request_hash="HASH-PLAN-T4-001",
                    created_by="seed",
                    created_at=created_at,
                )
            )
            session.commit()

    def test_sales_inventory_dev_local_reads_existing_tables_without_erpnext(self) -> None:
        with patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter.list_customers",
            side_effect=AssertionError("ERPNext customer adapter must not be called"),
        ), patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter.list_suppliers",
            side_effect=AssertionError("ERPNext supplier adapter must not be called"),
        ), patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter.list_warehouses",
            side_effect=AssertionError("ERPNext warehouse adapter must not be called"),
        ), patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter.list_sales_orders",
            side_effect=AssertionError("ERPNext sales order adapter must not be called"),
        ), patch(
            "app.services.erpnext_sales_inventory_adapter.ERPNextSalesInventoryAdapter.get_sales_order",
            side_effect=AssertionError("ERPNext sales order detail adapter must not be called"),
        ):
            customers = self.client.get(
                "/api/sales-inventory/customers?keyword=T4&disabled=false&page=1&page_size=2",
                headers=self._headers(),
            )
            suppliers = self.client.get(
                "/api/sales-inventory/suppliers?keyword=T4&page=1&page_size=2",
                headers=self._headers(),
            )
            warehouses = self.client.get(
                "/api/sales-inventory/warehouses?company=COMP-T4&keyword=WH&page=1&page_size=2",
                headers=self._headers(),
            )
            orders = self.client.get(
                "/api/sales-inventory/sales-orders?customer=CUST-T4-001&page=1&page_size=1",
                headers=self._headers(),
            )
            detail = self.client.get("/api/sales-inventory/sales-orders/SO-T4-001", headers=self._headers())
            fulfillment = self.client.get(
                "/api/sales-inventory/sales-order-fulfillment?item_code=ITEM-T4&page=1&page_size=1",
                headers=self._headers(),
            )

        self.assertEqual(customers.status_code, 200)
        self.assertEqual(customers.json()["data"]["items"][0]["name"], "CUST-T4-001")
        self.assertLessEqual(len(customers.json()["data"]["items"]), 2)
        self.assertEqual(suppliers.status_code, 200)
        self.assertEqual(suppliers.json()["data"]["items"][0]["name"], "SUP-T4-001")
        self.assertEqual(warehouses.status_code, 200)
        self.assertEqual({item["name"] for item in warehouses.json()["data"]["items"]}, {"WH-FG", "WH-RAW"})
        self.assertEqual(orders.status_code, 200)
        self.assertEqual(orders.json()["data"]["items"][0]["name"], "SO-T4-001")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["items"][0]["item_code"], "ITEM-T4")
        self.assertEqual(fulfillment.status_code, 200)
        self.assertEqual(fulfillment.json()["data"]["total"], 1)
        self.assertEqual(fulfillment.json()["data"]["items"][0]["actual_qty"], "0")

    def test_warehouse_stock_ledger_dev_local_projection_uses_existing_stock_drafts(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_ledger",
            side_effect=AssertionError("ERPNext stock ledger adapter must not be called"),
        ):
            response = self.client.get(
                "/api/warehouse/stock-ledger?company=COMP-T4&warehouse=WH-RAW&item_code=MAT-T4"
                "&from_date=2026-06-01&to_date=2026-06-01&page=1&page_size=1",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["total"], 1)
        self.assertEqual(payload["data"]["items"][0]["warehouse"], "WH-RAW")
        self.assertEqual(payload["data"]["items"][0]["posting_time"], "08:00:00")
        self.assertEqual(Decimal(payload["data"]["items"][0]["actual_qty"]), Decimal("12"))

    def test_bom_and_production_first_batch_read_existing_tables(self) -> None:
        endpoints = [
            ("/api/bom/?keyword=STYLE-T4&page=1&page_size=1", "bom_no", "BOM-T4-001"),
            ("/api/bom/fabrics?material_item_code=FAB-T4&page=1&page_size=1", "material_item_code", "FAB-T4-001"),
            (
                "/api/bom/accessories-packaging?material_item_code=ACC-T4&page=1&page_size=1",
                "material_item_code",
                "ACC-T4-001",
            ),
            ("/api/bom/material-types?material_item_code=FAB-T4&page=1&page_size=1", "material_type_name", "面料"),
            ("/api/bom/material-units?unit_name=M&page=1&page_size=1", "unit_name", "M"),
            ("/api/production/plans?keyword=PLAN-T4&page=1&page_size=1", "plan_no", "PLAN-T4-001"),
        ]
        for path, field, expected in endpoints:
            with self.subTest(path=path):
                response = self.client.get(path, headers=self._headers())
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["code"], "0")
                self.assertEqual(payload["data"]["total"], 1)
                self.assertEqual(payload["data"]["page_size"], 1)
                self.assertEqual(payload["data"]["items"][0][field], expected)

    def test_empty_page_and_unauthenticated_guard(self) -> None:
        empty_response = self.client.get(
            "/api/sales-inventory/customers?keyword=NOT-FOUND&page=1&page_size=2",
            headers=self._headers(),
        )
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.json()["data"], {"items": [], "total": 0, "page": 1, "page_size": 2})

        unauthorized = self.client.get("/api/sales-inventory/customers")
        self.assertEqual(unauthorized.status_code, 401)
