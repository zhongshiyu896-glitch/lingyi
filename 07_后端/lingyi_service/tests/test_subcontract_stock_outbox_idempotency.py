"""Idempotency and event-key tests for subcontract stock outbox (TASK-002D)."""

from __future__ import annotations

from decimal import Decimal
import os
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractStockOutbox
from app.routers import subcontract as subcontract_router
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.subcontract_stock_outbox_service import SubcontractStockOutboxService


class SubcontractStockOutboxIdempotencyTest(unittest.TestCase):
    """Validate issue-material idempotency and outbox key stability."""

    SCENARIO_TAG = "Z003-SUBCONTRACT-20260619-002"

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
        BomBase.metadata.create_all(bind=cls.engine)
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-IDEM-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyBomOperation(
                    id=1,
                    bom_id=1,
                    process_name="外发裁剪",
                    sequence_no=1,
                    is_subcontract=True,
                    subcontract_cost_per_piece=Decimal("1"),
                )
            )
            session.add(
                LyApparelBomItem(
                    id=1,
                    bom_id=1,
                    material_item_code="MAT-A",
                    color=None,
                    size=None,
                    qty_per_piece=Decimal("1"),
                    loss_rate=Decimal("0"),
                    uom="Nos",
                    remark=None,
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
        with self.SessionLocal() as session:
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()
            session.add(
                LySubcontractOrder(
                    id=1,
                    subcontract_no="SC-IDEM-001",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="draft",
                    settlement_status="unsettled",
                )
            )
            session.commit()

    @staticmethod
    def _headers(request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "idem.user", "X-LY-Dev-Roles": "Subcontract Manager"}
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        return headers

    @staticmethod
    def _carrier_code(value: str) -> str:
        return subcontract_router._fnv_carrier_code(value)

    def _request_id(
        self,
        *,
        idempotency_key: str,
        source_ref: str,
        subcontract_ref: str,
        supplier_ref: str,
        work_order_ref: str,
        item_code: str,
        status_action: str,
    ) -> str:
        operation_code = subcontract_router.SUBCONTRACT_OPERATION_CODE_BY_NAME["issue_material"]
        return (
            f"{self.SCENARIO_TAG}-SC-{operation_code}-"
            f"{self._carrier_code(idempotency_key)}-"
            f"{self._carrier_code(source_ref)}-"
            f"{self._carrier_code(subcontract_ref)}-"
            f"{self._carrier_code(supplier_ref)}-"
            f"{self._carrier_code(work_order_ref)}-"
            f"{self._carrier_code(item_code)}-"
            f"{self._carrier_code(status_action)}"
        )

    def _issue_payload(
        self,
        *,
        idem: str,
        issued_qty: str,
        materials: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        status_action = "issue_material"
        source_ref = f"{self.SCENARIO_TAG}:issue_material:1:{idem}"
        return {
            "request_id": self._request_id(
                idempotency_key=idem,
                source_ref=source_ref,
                subcontract_ref="1",
                supplier_ref="SUP-A",
                work_order_ref="NO-WORK-ORDER",
                item_code="ITEM-A",
                status_action=status_action,
            ),
            "idempotency_key": idem,
            "scenario_tag": self.SCENARIO_TAG,
            "source_ref": source_ref,
            "subcontract_ref": "1",
            "supplier_ref": "SUP-A",
            "work_order_ref": "NO-WORK-ORDER",
            "operation": "issue_material",
            "item_code": "ITEM-A",
            "quantity": issued_qty,
            "status_action": status_action,
            "warehouse": "WH-A",
            "materials": materials
            if materials is not None
            else [
                {
                    "material_item_code": "MAT-A",
                    "required_qty": "100",
                    "issued_qty": issued_qty,
                }
            ],
        }

    def _post_issue_material(self, payload: dict[str, object]):
        return self.client.post(
            "/api/subcontract/1/issue-material",
            headers=self._headers(request_id=str(payload["request_id"])),
            json=payload,
        )

    def test_issue_material_idempotent_same_payload_returns_existing_result(self) -> None:
        first_payload = self._issue_payload(idem="idem-same", issued_qty="10")
        second_payload = self._issue_payload(idem="idem-same", issued_qty="10")
        first = self._post_issue_material(first_payload)
        second = self._post_issue_material(second_payload)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_data = first.json()["data"]
        second_data = second.json()["data"]
        self.assertEqual(first_data["outbox_id"], second_data["outbox_id"])
        self.assertEqual(first_data["issue_batch_no"], second_data["issue_batch_no"])

        with self.SessionLocal() as session:
            outbox_count = session.query(LySubcontractStockOutbox).count()
            material_count = session.query(LySubcontractMaterial).count()
        self.assertEqual(outbox_count, 1)
        self.assertEqual(material_count, 1)

    def test_issue_material_idempotency_key_different_payload_returns_conflict(self) -> None:
        first = self._post_issue_material(self._issue_payload(idem="idem-conflict", issued_qty="10"))
        second = self._post_issue_material(self._issue_payload(idem="idem-conflict", issued_qty="12"))

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_IDEMPOTENCY_CONFLICT")

    def test_issue_material_event_key_uses_full_hash_without_truncation_collision(self) -> None:
        long_payload_a = {
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "warehouse": "WH-A",
            "items": [{"item_code": "MAT-A", "qty": "1"}],
            "noise": "A" * 500,
        }
        long_payload_b = {
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "warehouse": "WH-A",
            "items": [{"item_code": "MAT-A", "qty": "1"}],
            "noise": "B" * 500,
        }
        hash_a = SubcontractStockOutboxService.build_payload_hash(long_payload_a)
        hash_b = SubcontractStockOutboxService.build_payload_hash(long_payload_b)
        key_a = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="issue",
            idempotency_key="idem-long",
            payload_hash=hash_a,
        )
        key_b = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="issue",
            idempotency_key="idem-long",
            payload_hash=hash_b,
        )
        self.assertTrue(key_a.startswith("sio:"))
        self.assertTrue(key_b.startswith("sio:"))
        self.assertLessEqual(len(key_a), 140)
        self.assertLessEqual(len(key_b), 140)
        self.assertNotEqual(key_a, key_b)

    def test_issue_material_empty_items_payload_hash_stable_after_issue(self) -> None:
        payload = self._issue_payload(idem="idem-auto-empty", issued_qty="100", materials=[])
        first = self._post_issue_material(payload)
        second = self._post_issue_material(payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["data"]["outbox_id"], second.json()["data"]["outbox_id"])

    def test_issue_material_event_key_excludes_issue_batch_no(self) -> None:
        stable_payload_a = {
            "stock_action": "issue",
            "subcontract_id": 1,
            "subcontract_no": "SC-IDEM-001",
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "warehouse": "WH-A",
            "materials_auto": False,
            "materials": [{"material_item_code": "MAT-A", "required_qty": "100", "issued_qty": "10"}],
            "issue_batch_no": "SIB-1",
        }
        stable_payload_b = {
            "stock_action": "issue",
            "subcontract_id": 1,
            "subcontract_no": "SC-IDEM-001",
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "warehouse": "WH-A",
            "materials_auto": False,
            "materials": [{"material_item_code": "MAT-A", "required_qty": "100", "issued_qty": "10"}],
            "issue_batch_no": "SIB-2",
        }
        hash_a = SubcontractStockOutboxService.build_payload_hash(stable_payload_a)
        hash_b = SubcontractStockOutboxService.build_payload_hash(stable_payload_b)
        self.assertEqual(hash_a, hash_b)

        key_a = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="issue",
            idempotency_key="idem-event-key",
            payload_hash=hash_a,
        )
        key_b = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="issue",
            idempotency_key="idem-event-key",
            payload_hash=hash_b,
        )
        self.assertEqual(key_a, key_b)

    def test_receive_event_key_excludes_receipt_batch_no(self) -> None:
        stable_payload_a = {
            "stock_action": "receipt",
            "subcontract_id": 1,
            "subcontract_no": "SC-IDEM-001",
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "receipt_warehouse": "WH-A",
            "received_qty": "10",
            "receipt_batch_no": "SRB-1",
        }
        stable_payload_b = dict(stable_payload_a)
        stable_payload_b["receipt_batch_no"] = "SRB-2"
        hash_a = SubcontractStockOutboxService.build_payload_hash(stable_payload_a)
        hash_b = SubcontractStockOutboxService.build_payload_hash(stable_payload_b)
        self.assertEqual(hash_a, hash_b)

        key_a = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="receipt",
            idempotency_key="idem-receipt-event-key",
            payload_hash=hash_a,
        )
        key_b = SubcontractStockOutboxService.build_event_key(
            subcontract_id=1,
            stock_action="receipt",
            idempotency_key="idem-receipt-event-key",
            payload_hash=hash_b,
        )
        self.assertEqual(key_a, key_b)

    def test_receive_payload_hash_normalizes_decimal_qty_equivalents(self) -> None:
        payload_1 = {
            "stock_action": "receipt",
            "subcontract_id": 1,
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "receipt_warehouse": "WH-A",
            "received_qty": "10",
            "items": [{"item_code": "ITEM-A", "qty": "10.000000", "uom": "Nos", "t_warehouse": "WH-A"}],
        }
        payload_2 = {
            "stock_action": "receipt",
            "subcontract_id": 1,
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "receipt_warehouse": "WH-A",
            "received_qty": "10.0",
            "items": [{"item_code": "ITEM-A", "qty": "10", "uom": "Nos", "t_warehouse": "WH-A"}],
        }
        self.assertEqual(
            SubcontractStockOutboxService.build_payload_hash(payload_1),
            SubcontractStockOutboxService.build_payload_hash(payload_2),
        )

    def test_issue_payload_hash_normalizes_decimal_qty_equivalents(self) -> None:
        payload_1 = {
            "stock_action": "issue",
            "subcontract_id": 1,
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "warehouse": "WH-A",
            "items": [
                {
                    "item_code": "MAT-A",
                    "qty": "10.000000",
                    "required_qty": "100.0",
                    "issued_qty": "10",
                    "uom": "Nos",
                    "s_warehouse": "WH-A",
                }
            ],
        }
        payload_2 = {
            "stock_action": "issue",
            "subcontract_id": 1,
            "company": "COMP-A",
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "warehouse": "WH-A",
            "items": [
                {
                    "item_code": "MAT-A",
                    "qty": "10",
                    "required_qty": "100.000000",
                    "issued_qty": "10.0",
                    "uom": "Nos",
                    "s_warehouse": "WH-A",
                }
            ],
        }
        self.assertEqual(
            SubcontractStockOutboxService.build_payload_hash(payload_1),
            SubcontractStockOutboxService.build_payload_hash(payload_2),
        )

    def test_deprecated_get_retry_target_not_used_by_retry_endpoint(self) -> None:
        outbox_source = Path(
            "/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_stock_outbox_service.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("def get_retry_target", outbox_source)

    def test_no_latest_outbox_retry_selector_in_production_path(self) -> None:
        service_source = Path(
            "/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py"
        ).read_text(encoding="utf-8")
        router_source = Path(
            "/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py"
        ).read_text(encoding="utf-8")
        self.assertIn("get_stock_outbox_for_retry", service_source)
        self.assertIn("get_by_id(outbox_id=outbox_id)", service_source)
        self.assertIn("outbox_id=retry_payload.outbox_id", router_source)
        self.assertNotIn("latest_outbox", router_source)


if __name__ == "__main__":
    unittest.main()
