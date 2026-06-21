"""Warehouse read-only baseline tests (TASK-050A)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import WAREHOUSE_ALERT_READ
from app.core.permissions import WAREHOUSE_DIAGNOSTIC
from app.core.permissions import WAREHOUSE_EXPORT
from app.core.permissions import WAREHOUSE_READ
from app.core.permissions import WAREHOUSE_STOCK_HOLD_RELEASE
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.quality import Base as QualityBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.warehouse import get_db_session as warehouse_db_dep
from app.schemas.warehouse import WarehouseStockSummaryData
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.warehouse_service import WarehouseService


class WarehouseReadonlyApiBase(unittest.TestCase):
    """Shared in-memory app wiring for warehouse tests."""

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

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[warehouse_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(warehouse_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ.pop("LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON", None)
        os.environ["LINGYI_FASTAPI_ROLE_ACTIONS_JSON"] = json.dumps(
            {
                "roles": {
                    WAREHOUSE_READ: [WAREHOUSE_READ],
                    WAREHOUSE_ALERT_READ: [WAREHOUSE_ALERT_READ],
                    WAREHOUSE_EXPORT: [WAREHOUSE_EXPORT],
                    WAREHOUSE_DIAGNOSTIC: [WAREHOUSE_DIAGNOSTIC],
                    WAREHOUSE_STOCK_HOLD_RELEASE: [WAREHOUSE_STOCK_HOLD_RELEASE],
                }
            }
        )
        with self.SessionLocal() as session:
            session.query(LyWarehouseStockLedgerEntry).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LyMasterDataRecord).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers(read_only: bool = False) -> dict[str, str]:
        if read_only:
            roles = "warehouse:read"
        else:
            roles = "warehouse:read,warehouse:alert_read"
        return WarehouseReadonlyApiBase._headers_with_roles(roles)

    @staticmethod
    def _headers_with_roles(roles: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "warehouse.user",
            "X-LY-Dev-Roles": roles,
        }

    def _seed_stock_entry(
        self,
        *,
        company: str = "COMP-A",
        warehouse: str = "WH-A",
        item_code: str = "ITEM-A",
        qty: str = "2",
        purpose: str = "Material Receipt",
        status: str = "pending_outbox",
        event_key: str = "EVT-WH-READ-001",
        created_at: datetime | None = None,
        batch_no: str | None = None,
        serial_no: str | None = None,
    ) -> None:
        created = created_at or datetime(2026, 4, 20, tzinfo=timezone.utc)
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                company=company,
                purpose=purpose,
                source_type="test",
                source_id=event_key,
                source_warehouse=warehouse if purpose in {"Material Issue", "Material Transfer"} else None,
                target_warehouse=warehouse,
                status=status,
                created_by="seed",
                created_at=created,
                idempotency_key=f"{event_key}:idem",
                event_key=event_key,
            )
            session.add(draft)
            session.flush()
            session.add(
                LyWarehouseStockEntryDraftItem(
                    draft_id=int(draft.id),
                    company=company,
                    item_code=item_code,
                    qty=Decimal(qty),
                    uom="PCS",
                    batch_no=batch_no,
                    serial_no=serial_no,
                    source_warehouse=warehouse if purpose in {"Material Issue", "Material Transfer"} else None,
                    target_warehouse=warehouse,
                )
            )
            session.commit()

    def _seed_durable_ledger_entry(
        self,
        *,
        company: str = "COMP-A",
        warehouse: str = "WH-A",
        item_code: str = "ITEM-DURABLE",
        posting_date: date = date(2026, 4, 20),
        source_id: str = "DURABLE-001",
        voucher_no: str = "DURABLE-001",
        actual_qty: str = "2",
        status: str = "active",
    ) -> None:
        sort_at = datetime.combine(posting_date, datetime.min.time(), timezone.utc)
        with self.SessionLocal() as session:
            session.add(
                LyWarehouseStockLedgerEntry(
                    company=company,
                    warehouse=warehouse,
                    item_code=item_code,
                    uom="PCS",
                    posting_date=posting_date,
                    sort_at=sort_at,
                    source_type="durable_api_test",
                    source_id=source_id,
                    source_line_id="1",
                    sequence=1,
                    voucher_type="Durable/Test",
                    voucher_no=voucher_no,
                    actual_qty=Decimal(actual_qty),
                    valuation_rate=Decimal("1"),
                    status=status,
                    projected_at=sort_at,
                    voided_at=sort_at if status == "voided" else None,
                )
            )
            session.commit()

    def _seed_material_master(
        self,
        *,
        company: str = "COMP-A",
        item_code: str = "ITEM-A",
        payload: dict[str, object],
    ) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="material",
                    company=company,
                    code=item_code,
                    name=f"{item_code} 物料",
                    status="active",
                    payload=payload,
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()


class WarehouseReadonlyApiTest(WarehouseReadonlyApiBase):
    """Read-only API behavior and boundaries."""

    def test_stock_ledger_returns_rows(self) -> None:
        self._seed_stock_entry()
        response = self.client.get("/api/warehouse/stock-ledger?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["warehouse"], "WH-A")
        self.assertEqual(payload["items"][0]["voucher_type"], "Stock Entry Draft/Material Receipt")
        self.assertEqual(Decimal(str(payload["items"][0]["qty_after_transaction"])), Decimal("2.000000"))

    def test_stock_ledger_and_summary_read_durable_rows_without_drafts(self) -> None:
        self._seed_durable_ledger_entry(
            posting_date=date(2026, 4, 20),
            source_id="DURABLE-RCPT",
            voucher_no="D-RCPT",
            actual_qty="10",
        )
        self._seed_durable_ledger_entry(
            posting_date=date(2026, 4, 21),
            source_id="DURABLE-ISSUE",
            voucher_no="D-ISSUE",
            actual_qty="-3",
        )
        self._seed_durable_ledger_entry(
            posting_date=date(2026, 4, 21),
            source_id="DURABLE-VOID",
            voucher_no="D-VOID",
            actual_qty="99",
            status="voided",
        )

        ledger = self.client.get(
            "/api/warehouse/stock-ledger?company=COMP-A&warehouse=WH-A&item_code=ITEM-DURABLE&from_date=2026-04-21&to_date=2026-04-21&keyword=D-ISSUE",
            headers=self._headers(),
        )
        summary = self.client.get(
            "/api/warehouse/stock-summary?company=COMP-A&warehouse=WH-A&item_code=ITEM-DURABLE",
            headers=self._headers(),
        )

        self.assertEqual(ledger.status_code, 200, ledger.text)
        ledger_payload = ledger.json()["data"]
        self.assertEqual(ledger_payload["total"], 1)
        ledger_row = ledger_payload["items"][0]
        self.assertEqual(ledger_row["voucher_no"], "D-ISSUE")
        self.assertEqual(Decimal(str(ledger_row["actual_qty"])), Decimal("-3.000000"))
        self.assertEqual(Decimal(str(ledger_row["qty_after_transaction"])), Decimal("7.000000"))
        self.assertEqual(summary.status_code, 200, summary.text)
        summary_row = summary.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(summary_row["actual_qty"])), Decimal("7.000000"))

    def test_stock_ledger_keyword_filters_after_running_balance_recalculation(self) -> None:
        self._seed_stock_entry(qty="10", event_key="EVT-WH-KEYWORD-001", created_at=datetime(2026, 4, 20, tzinfo=timezone.utc))
        self._seed_stock_entry(
            qty="3",
            purpose="Material Issue",
            event_key="EVT-WH-KEYWORD-002",
            created_at=datetime(2026, 4, 21, tzinfo=timezone.utc),
        )
        all_response = self.client.get(
            "/api/warehouse/stock-ledger?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
            headers=self._headers(),
        )
        self.assertEqual(all_response.status_code, 200, all_response.text)
        all_items = all_response.json()["data"]["items"]
        issue_voucher_no = all_items[1]["voucher_no"]

        response = self.client.get(
            f"/api/warehouse/stock-ledger?company=COMP-A&warehouse=WH-A&keyword={issue_voucher_no}",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        row = payload["items"][0]
        self.assertEqual(row["voucher_no"], issue_voucher_no)
        self.assertEqual(Decimal(str(row["actual_qty"])), Decimal("-3.000000"))
        self.assertEqual(Decimal(str(row["qty_after_transaction"])), Decimal("7.000000"))

    def test_stock_summary_returns_aggregation(self) -> None:
        self._seed_stock_entry(qty="2", event_key="EVT-WH-READ-SUMMARY-001")
        self._seed_stock_entry(qty="5", event_key="EVT-WH-READ-SUMMARY-002")
        response = self.client.get("/api/warehouse/stock-summary?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        row = response.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(row["actual_qty"])), Decimal("7.000000"))
        self.assertEqual(Decimal(str(row["projected_qty"])), Decimal("7.000000"))
        self.assertFalse(row["is_below_reorder"])
        self.assertFalse(row["is_below_safety"])
        self.assertTrue(row["threshold_missing"])
        self.assertIsNone(row["reorder_level"])
        self.assertIsNone(row["safety_stock"])

    def test_stock_summary_reads_material_thresholds_from_master_payload(self) -> None:
        self._seed_material_master(payload={"reorder_level": "5", "safety_stock": "3"})
        self._seed_stock_entry(qty="2", event_key="EVT-WH-READ-THRESHOLD-001")

        response = self.client.get(
            "/api/warehouse/stock-summary?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(row["actual_qty"])), Decimal("2.000000"))
        self.assertEqual(Decimal(str(row["reorder_level"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(row["safety_stock"])), Decimal("3.000000"))
        self.assertFalse(row["threshold_missing"])
        self.assertTrue(row["is_below_reorder"])
        self.assertTrue(row["is_below_safety"])

    def test_stock_summary_uses_min_stock_as_safety_stock_alias(self) -> None:
        self._seed_material_master(item_code="ITEM-MIN", payload={"min_stock": "4"})
        self._seed_stock_entry(item_code="ITEM-MIN", qty="2", event_key="EVT-WH-READ-MIN-STOCK-001")

        response = self.client.get(
            "/api/warehouse/stock-summary?company=COMP-A&warehouse=WH-A&item_code=ITEM-MIN",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()["data"]["items"][0]
        self.assertIsNone(row["reorder_level"])
        self.assertEqual(Decimal(str(row["safety_stock"])), Decimal("4.000000"))
        self.assertTrue(row["threshold_missing"])
        self.assertFalse(row["is_below_reorder"])
        self.assertTrue(row["is_below_safety"])

    def test_fastapi_alerts_use_material_thresholds_from_master_payload(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "warehouse.user": {
                        "company": ["COMP-A"],
                        "warehouse": ["WH-A"],
                        "item_code": ["ITEM-A"],
                    }
                }
            }
        )
        self._seed_material_master(payload={"reorder_level": "5", "safety_stock": "3"})
        self._seed_stock_entry(qty="2", event_key="EVT-WH-READ-ALERT-THRESHOLD-001")

        response = self.client.get(
            "/api/warehouse/alerts?company=COMP-A&warehouse=WH-A&item_code=ITEM-A&alert_type=low_stock",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["alert_type"], "low_stock")
        self.assertEqual(Decimal(str(items[0]["current_qty"])), Decimal("2.000000"))
        self.assertEqual(Decimal(str(items[0]["threshold_qty"])), Decimal("5.000000"))
        self.assertEqual(Decimal(str(items[0]["gap_qty"])), Decimal("3.000000"))

    def test_alerts_returns_low_stock(self) -> None:
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_summary",
            return_value=[
                {
                    "company": "COMP-A",
                    "warehouse": "WH-A",
                    "item_code": "ITEM-A",
                    "actual_qty": "1",
                    "projected_qty": "1",
                    "reserved_qty": "0",
                    "ordered_qty": "0",
                    "reorder_level": "5",
                    "safety_stock": "3",
                }
            ],
        ), patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.latest_movement_by_item_warehouse",
            return_value={("ITEM-A", "WH-A"): date(2026, 4, 1)},
        ):
            response = self.client.get("/api/warehouse/alerts?alert_type=low_stock", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["alert_type"], "low_stock")

    def test_company_filter_passed_to_service(self) -> None:
        with patch.object(WarehouseService, "get_local_stock_summary") as mocked_summary:
            mocked_summary.return_value = WarehouseStockSummaryData(company="COMP-A", warehouse=None, item_code=None, items=[])
            response = self.client.get("/api/warehouse/stock-summary?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        mocked_summary.assert_called_once()
        self.assertEqual(mocked_summary.call_args.kwargs["company"], "COMP-A")

    def test_warehouse_permission_filter_effective(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        self._seed_stock_entry(warehouse="WH-A", qty="2", event_key="EVT-WH-SCOPE-A")
        self._seed_stock_entry(warehouse="WH-B", qty="2", event_key="EVT-WH-SCOPE-B")
        with patch(
            "app.services.permission_service.PermissionService.require_action",
            return_value=None,
        ), patch(
            "app.services.permission_service.PermissionService.get_sales_inventory_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_companies={"COMP-A"},
                allowed_warehouses={"WH-A"},
                allowed_items={"ITEM-A"},
            ),
        ):
            response = self.client.get("/api/warehouse/stock-summary?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["warehouse"], "WH-A")

    def test_warehouse_permission_filter_uses_fastapi_scope(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "warehouse.user": {
                        "company": ["COMP-A"],
                        "warehouse": ["WH-A"],
                        "item_code": ["ITEM-A"],
                    }
                }
            }
        )
        self._seed_stock_entry(warehouse="WH-A", item_code="ITEM-A", qty="2", event_key="EVT-WH-FASTAPI-SCOPE-A")
        self._seed_stock_entry(warehouse="WH-B", item_code="ITEM-A", qty="2", event_key="EVT-WH-FASTAPI-SCOPE-B")

        response = self.client.get("/api/warehouse/stock-summary?company=COMP-A", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        items = response.json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["warehouse"], "WH-A")

    def test_fastapi_alerts_and_batches_do_not_construct_erpnext_adapter(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "warehouse.user": {
                        "company": ["COMP-A"],
                        "warehouse": ["WH-A"],
                        "item_code": ["ITEM-A"],
                    }
                }
            }
        )
        self._seed_stock_entry(
            qty="5",
            purpose="Material Issue",
            event_key="EVT-WH-FASTAPI-ALERT-001",
            created_at=datetime(2026, 4, 20, tzinfo=timezone.utc),
        )
        self._seed_material_master(payload={"reorder_level": "5", "safety_stock": "3"})

        with patch("app.routers.warehouse.ERPNextWarehouseAdapter", side_effect=AssertionError("erpnext adapter")):
            alerts = self.client.get(
                "/api/warehouse/alerts?company=COMP-A&warehouse=WH-A&item_code=ITEM-A&alert_type=low_stock",
                headers=self._headers(),
            )
            batches = self.client.get(
                "/api/warehouse/batches?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
                headers=self._headers(),
            )
            batch_detail = self.client.get(
                "/api/warehouse/batches/BATCH-NOPE?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
                headers=self._headers(),
            )

        self.assertEqual(alerts.status_code, 200, alerts.text)
        self.assertEqual(alerts.json()["code"], "0")
        alert_items = alerts.json()["data"]["items"]
        self.assertEqual(len(alert_items), 1)
        self.assertEqual(alert_items[0]["alert_type"], "low_stock")
        self.assertEqual(alert_items[0]["current_qty"], "-5.000000")
        self.assertEqual(batches.status_code, 200, batches.text)
        self.assertEqual(batches.json()["code"], "0")
        self.assertEqual(batches.json()["data"]["total"], 0)
        self.assertEqual(batches.json()["data"]["items"], [])
        self.assertEqual(batch_detail.status_code, 404, batch_detail.text)
        self.assertEqual(batch_detail.json()["code"], "WAREHOUSE_BATCH_NOT_FOUND")

    def test_fastapi_consumed_projection_reads_do_not_construct_erpnext_adapter(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
        os.environ["LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"] = json.dumps(
            {
                "users": {
                    "warehouse.user": {
                        "company": ["COMP-A"],
                        "warehouse": ["WH-A"],
                        "item_code": ["ITEM-A"],
                    }
                }
            }
        )

        paths = [
            "/api/warehouse/other-inbound?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
            "/api/warehouse/purchase-return-outbound?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
            "/api/warehouse/semi-finished-outbound?company=COMP-A&warehouse=WH-A&item_code=ITEM-A",
            "/api/warehouse/finished-goods-inbound-candidates?company=COMP-A&item_code=ITEM-A",
        ]
        with patch("app.routers.warehouse.ERPNextWarehouseAdapter", side_effect=AssertionError("erpnext adapter")):
            responses = [self.client.get(path, headers=self._headers()) for path in paths]

        for response in responses:
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["code"], "0")
            self.assertEqual(response.json()["data"]["items"], [])

    def test_invalid_date_range_returns_400(self) -> None:
        response = self.client.get(
            "/api/warehouse/stock-ledger?from_date=2026-05-01&to_date=2026-04-01",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_QUERY_PARAMETER")

    def test_inventory_read_only_forbidden_on_stock_ledger(self) -> None:
        response = self.client.get(
            "/api/warehouse/stock-ledger",
            headers=self._headers_with_roles("inventory:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_inventory_read_only_forbidden_on_stock_summary(self) -> None:
        response = self.client.get(
            "/api/warehouse/stock-summary",
            headers=self._headers_with_roles("inventory:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_inventory_read_only_forbidden_on_alerts(self) -> None:
        response = self.client.get(
            "/api/warehouse/alerts",
            headers=self._headers_with_roles("inventory:read"),
        )
        self.assertEqual(response.status_code, 403)

    def test_stock_ledger_uses_fastapi_local_rows_even_when_erpnext_fails(self) -> None:
        self._seed_stock_entry(event_key="EVT-WH-READ-NO-ERP-001")
        with patch(
            "app.services.erpnext_warehouse_adapter.ERPNextWarehouseAdapter.list_stock_ledger",
            side_effect=ERPNextAdapterException(error_code="ERPNEXT_RESPONSE_INVALID", safe_message="invalid"),
        ):
            response = self.client.get("/api/warehouse/stock-ledger", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["warehouse"], "WH-A")

    def test_no_write_route_registered(self) -> None:
        warehouse_routes = [route for route in app.routes if str(getattr(route, "path", "")).startswith("/api/warehouse")]
        self.assertTrue(warehouse_routes)
        readonly_methods = {"GET", "HEAD", "OPTIONS"}
        allowed_write_routes = {
            ("POST", "/api/warehouse/stock-entry-drafts"),  # TASK-050B 审计意见书第383份
            ("POST", "/api/warehouse/stock-entry-drafts/{draft_id}/audit"),  # A期库存草稿本地审核确认
            ("POST", "/api/warehouse/stock-entry-drafts/{draft_id}/cancel"),  # TASK-050B 审计意见书第383份
            ("POST", "/api/warehouse/stock-entry-drafts/{draft_id}/release-hold"),  # A期物料扣仓释放
            ("POST", "/api/warehouse/internal/stock-entry-sync/run-once"),  # TASK-050D_FIX1 审计意见书第389份
            ("POST", "/api/warehouse/inventory-counts"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/submit"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/variance-review"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/confirm"),  # TASK-050C 审计意见书第385份
            ("POST", "/api/warehouse/inventory-counts/{count_id}/cancel"),  # TASK-050C 审计意见书第385份
            (
                "POST",
                "/api/warehouse/factory-return-material-report/{report_no}/return-draft",
            ),  # A期加工厂应退料退料草稿
        }
        discovered_write_routes: set[tuple[str, str]] = set()
        for route in warehouse_routes:
            path = str(getattr(route, "path", ""))
            methods = {method.upper() for method in getattr(route, "methods", set())}
            for method in methods:
                if method in readonly_methods:
                    continue
                self.assertNotIn(method, {"PUT", "PATCH", "DELETE"})
                discovered_write_routes.add((method, path))
        self.assertSetEqual(discovered_write_routes, allowed_write_routes)

    def test_no_erpnext_write_call_signature(self) -> None:
        from app.routers import warehouse as warehouse_router_module
        from app.services import erpnext_warehouse_adapter as adapter_module
        from app.services import warehouse_service as warehouse_service_module

        content = "\n".join(
            [
                open(warehouse_router_module.__file__, encoding="utf-8").read(),
                open(warehouse_service_module.__file__, encoding="utf-8").read(),
                open(adapter_module.__file__, encoding="utf-8").read(),
            ]
        )
        blocked_snippets = [
            "requests.post",
            "requests.put",
            "requests.patch",
            "requests.delete",
            "httpx.post",
            "httpx.put",
            "httpx.patch",
            "httpx.delete",
            "/api/resource/Stock Entry",
            "/api/resource/Stock Reconciliation",
            "/api/resource/Stock Ledger Entry",
        ]
        for snippet in blocked_snippets:
            self.assertNotIn(snippet, content)

    def test_warehouse_actions_registered(self) -> None:
        actions = MODULE_ACTION_REGISTRY.get("warehouse")
        self.assertIsNotNone(actions)
        expected = {WAREHOUSE_READ, WAREHOUSE_ALERT_READ, WAREHOUSE_EXPORT, WAREHOUSE_DIAGNOSTIC, WAREHOUSE_STOCK_HOLD_RELEASE}
        self.assertTrue(expected.issubset(actions or set()))


if __name__ == "__main__":
    unittest.main()
