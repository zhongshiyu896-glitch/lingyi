"""Real subcontract return-material read API."""

from __future__ import annotations

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
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractStockOutbox
from app.models.warehouse import Base as WarehouseBase
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult


class SubcontractReturnMaterialsTest(unittest.TestCase):
    """Validate return-material rows are inferred from real subcontract issue facts."""

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
        BomBase.metadata.create_all(bind=cls.engine)
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)
        WarehouseBase.metadata.create_all(bind=cls.engine)
        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-RETURN-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[subcontract_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_FRONTEND_READINESS_ENABLED"] = "true"
        with self.SessionLocal() as session:
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "subcontract.return.user", "X-LY-Dev-Roles": role}

    def _seed_issue_fact(self) -> None:
        with self.SessionLocal() as session:
            order = LySubcontractOrder(
                id=1,
                subcontract_no="SC-RETURN-001",
                supplier="SUP-A",
                item_code="ITEM-A",
                company="COMP-A",
                bom_id=1,
                process_name="外发裁剪",
                planned_qty=Decimal("100"),
                issued_qty=Decimal("50"),
                received_qty=Decimal("40"),
                accepted_qty=Decimal("30"),
                status="received",
            )
            outbox = LySubcontractStockOutbox(
                id=10,
                subcontract_id=1,
                event_key="EVT-RETURN-001",
                stock_action="issue",
                idempotency_key="idem-return-issue-001",
                company="COMP-A",
                supplier="SUP-A",
                item_code="ITEM-A",
                warehouse="WH-ISSUE-A",
                status="succeeded",
                stock_entry_name="STE-RETURN-001",
                request_id="req-return-001",
                created_by="seed",
            )
            material = LySubcontractMaterial(
                id=20,
                subcontract_id=1,
                stock_outbox_id=10,
                company="COMP-A",
                issue_batch_no="ISS-RETURN-001",
                material_item_code="MAT-A",
                required_qty=Decimal("80"),
                issued_qty=Decimal("50"),
                sync_status="succeeded",
                stock_entry_name="STE-RETURN-001",
            )
            session.add_all([order, outbox, material])
            session.commit()

    def _seed_return_draft(self, *, report_no: str, qty: Decimal) -> None:
        with self.SessionLocal() as session:
            draft = LyWarehouseStockEntryDraft(
                id=100,
                company="COMP-A",
                purpose="Material Receipt",
                source_type="factory_return_material",
                source_id=f"{report_no}:return:001",
                target_warehouse="WH-ISSUE-A",
                status="draft",
                created_by="seed",
                idempotency_key="idem-return-material-001",
                event_key="event-return-material-001",
            )
            item = LyWarehouseStockEntryDraftItem(
                id=101,
                draft_id=100,
                company="COMP-A",
                item_code="MAT-A",
                qty=qty,
                uom="米",
                target_warehouse="WH-ISSUE-A",
            )
            session.add_all([draft, item])
            session.commit()

    def test_return_materials_are_inferred_from_real_issue_facts(self) -> None:
        self._seed_issue_fact()

        response = self.client.get(
            "/api/subcontract/return-materials?company=COMP-A&warehouse=WH-ISSUE-A&item_code=MAT-A",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["total"], 1)
        row = payload["data"]["items"][0]
        self.assertEqual(row["subcontract_no"], "SC-RETURN-001")
        self.assertEqual(row["company"], "COMP-A")
        self.assertEqual(row["supplier"], "SUP-A")
        self.assertEqual(row["item_code"], "ITEM-A")
        self.assertEqual(row["material_item_code"], "MAT-A")
        self.assertEqual(row["warehouse"], "WH-ISSUE-A")
        self.assertEqual(Decimal(str(row["issued_qty"])), Decimal("50.00"))
        self.assertEqual(Decimal(str(row["theoretical_usage_qty"])), Decimal("24.00"))
        self.assertEqual(Decimal(str(row["planned_return_qty"])), Decimal("26.00"))
        self.assertEqual(Decimal(str(row["returned_qty"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(row["pending_qty"])), Decimal("26.00"))
        self.assertEqual(row["status"], "pending")
        self.assertTrue(str(row["report_no"]).startswith("FRR-1-"))

    def test_return_materials_keep_pending_drafts_out_of_returned_qty(self) -> None:
        self._seed_issue_fact()
        initial = self.client.get(
            "/api/subcontract/return-materials?company=COMP-A&warehouse=WH-ISSUE-A&item_code=MAT-A",
            headers=self._headers(),
        )
        self.assertEqual(initial.status_code, 200, initial.text)
        report_no = initial.json()["data"]["items"][0]["report_no"]

        self._seed_return_draft(report_no=report_no, qty=Decimal("10"))
        response = self.client.get(
            "/api/subcontract/return-materials?company=COMP-A&warehouse=WH-ISSUE-A&item_code=MAT-A&status=confirmed",
            headers=self._headers(),
        )

        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()["data"]["items"][0]
        self.assertEqual(row["report_no"], report_no)
        self.assertEqual(Decimal(str(row["planned_return_qty"])), Decimal("26.00"))
        self.assertEqual(Decimal(str(row["returned_qty"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(row["pending_qty"])), Decimal("16.00"))
        self.assertEqual(row["status"], "confirmed")

    def test_empty_real_table_does_not_fall_back_to_readiness_seed(self) -> None:
        response = self.client.get("/api/subcontract/return-materials", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["total"], 0)
        self.assertEqual(payload["data"]["items"], [])
        self.assertNotIn("SUB-FR-001", response.text)

    def test_erpnext_item_scope_filters_return_materials_fail_closed(self) -> None:
        self._seed_issue_fact()
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"OTHER-ITEM"},
                allowed_companies={"COMP-A"},
                allowed_suppliers={"SUP-A"},
                allowed_warehouses={"WH-ISSUE-A"},
            ),
        ):
            response = self.client.get("/api/subcontract/return-materials", headers=self._headers())

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["total"], 0)
        self.assertEqual(payload["data"]["items"], [])


if __name__ == "__main__":
    unittest.main()
