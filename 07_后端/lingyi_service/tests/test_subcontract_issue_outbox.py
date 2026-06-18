"""Tests for subcontract issue-material outbox flow (TASK-002D)."""

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
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractStatusLog
from app.models.subcontract import LySubcontractStockOutbox
from app.routers import subcontract as subcontract_router
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.erpnext_stock_entry_service import ERPNextStockEntryService


class SubcontractIssueOutboxTest(unittest.TestCase):
    """Validate issue-material local facts and pending outbox behavior."""

    SCENARIO_TAG = "Z003-SUBCONTRACT-20260525-005"

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
                    bom_no="BOM-ISSUE-001",
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
            session.add_all(
                [
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
                    ),
                    LyApparelBomItem(
                        id=2,
                        bom_id=1,
                        material_item_code="MAT-B",
                        color=None,
                        size=None,
                        qty_per_piece=Decimal("0.5"),
                        loss_rate=Decimal("0"),
                        uom="Nos",
                        remark=None,
                    ),
                ]
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
        os.environ["ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API"] = "true"
        with self.SessionLocal() as session:
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractStatusLog).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()
            session.add(
                LySubcontractOrder(
                    id=1,
                    subcontract_no="SC-ISSUE-001",
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
            session.add(
                LySubcontractOrder(
                    id=2,
                    subcontract_no="SC-ISSUE-BLOCKED",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("50"),
                    status="draft",
                    settlement_status="unsettled",
                    resource_scope_status="blocked_scope",
                    scope_error_code="SUBCONTRACT_COMPANY_UNRESOLVED",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=3,
                    subcontract_no="SC-ISSUE-SETTLED",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("20"),
                    status="processing",
                    settlement_status="settled",
                )
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager", request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "issue.user", "X-LY-Dev-Roles": role}
        if request_id:
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

    def _payload(
        self,
        *,
        idem: str = "idem-1",
        qty: str = "10",
        subcontract_ref: str = "1",
        materials: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        status_action = "issue_material"
        source_ref = f"{self.SCENARIO_TAG}:issue_material:{subcontract_ref}:{idem}"
        payload: dict[str, object] = {
            "request_id": self._request_id(
                idempotency_key=idem,
                source_ref=source_ref,
                subcontract_ref=subcontract_ref,
                supplier_ref="SUP-A",
                work_order_ref="NO-WORK-ORDER",
                item_code="ITEM-A",
                status_action=status_action,
            ),
            "idempotency_key": idem,
            "scenario_tag": self.SCENARIO_TAG,
            "source_ref": source_ref,
            "subcontract_ref": subcontract_ref,
            "supplier_ref": "SUP-A",
            "work_order_ref": "NO-WORK-ORDER",
            "operation": "issue_material",
            "item_code": "ITEM-A",
            "quantity": qty,
            "status_action": status_action,
            "warehouse": "WH-A",
            "materials": materials
            if materials is not None
            else [
                {
                    "material_item_code": "MAT-A",
                    "required_qty": "100",
                    "issued_qty": qty,
                }
            ],
        }
        return payload

    def _post_issue_material(self, *, order_id: int, payload: dict[str, object]):
        return self.client.post(
            f"/api/subcontract/{order_id}/issue-material",
            headers=self._headers(request_id=str(payload["request_id"])),
            json=payload,
        )

    def test_issue_material_creates_material_rows_and_local_dev_outbox(self) -> None:
        response = self._post_issue_material(order_id=1, payload=self._payload(idem="idem-create"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["sync_status"], "succeeded")
        self.assertTrue(str(response.json()["data"]["stock_entry_name"]).startswith("LOCAL-ISSUE-"))

        with self.SessionLocal() as session:
            materials = (
                session.query(LySubcontractMaterial)
                .filter(LySubcontractMaterial.subcontract_id == 1)
                .order_by(LySubcontractMaterial.id.asc())
                .all()
            )
            outbox = (
                session.query(LySubcontractStockOutbox)
                .filter(LySubcontractStockOutbox.subcontract_id == 1)
                .order_by(LySubcontractStockOutbox.id.desc())
                .first()
            )
            order = session.query(LySubcontractOrder).filter(LySubcontractOrder.id == 1).first()

        self.assertEqual(len(materials), 1)
        self.assertIsNotNone(outbox)
        self.assertEqual(outbox.stock_action, "issue")
        self.assertEqual(outbox.status, "succeeded")
        self.assertTrue(str(outbox.stock_entry_name).startswith("LOCAL-ISSUE-"))
        self.assertEqual(materials[0].sync_status, "succeeded")
        self.assertEqual(materials[0].stock_entry_name, outbox.stock_entry_name)
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "issued")

    def test_issue_material_does_not_call_erpnext_before_commit(self) -> None:
        with patch.object(ERPNextStockEntryService, "create_and_submit_material_issue") as create_mock, patch.object(
            ERPNextStockEntryService,
            "find_by_event_key",
        ) as find_mock:
            payload = self._payload(idem="idem-no-erp")
            response = self._post_issue_material(order_id=1, payload=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(create_mock.call_count, 0)
        self.assertEqual(find_mock.call_count, 0)

    def test_issue_material_returns_local_dev_stock_entry_name(self) -> None:
        response = self._post_issue_material(order_id=1, payload=self._payload(idem="idem-no-fake"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("outbox_id", payload)
        self.assertTrue(str(payload["stock_entry_name"]).startswith("LOCAL-ISSUE-"))
        self.assertNotIn("STE-ISS", str(payload))

    def test_issue_material_rejects_material_not_in_bom(self) -> None:
        response = self._post_issue_material(
            order_id=1,
            payload=self._payload(
                idem="idem-not-in-bom",
                materials=[
                    {
                        "material_item_code": "MAT-Z",
                        "required_qty": "100",
                        "issued_qty": "10",
                    }
                ],
            ),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_MATERIAL_NOT_IN_BOM")

    def test_issue_material_rejects_qty_exceeding_remaining_required_qty(self) -> None:
        response = self._post_issue_material(order_id=1, payload=self._payload(idem="idem-qty-over", qty="1000"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_MATERIAL_QTY_EXCEEDED")

    def test_issue_material_blocked_scope_order_rejected(self) -> None:
        response = self._post_issue_material(
            order_id=2,
            payload=self._payload(idem="idem-blocked", subcontract_ref="2"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SCOPE_BLOCKED")

    def test_issue_material_settled_order_rejected(self) -> None:
        response = self._post_issue_material(
            order_id=3,
            payload=self._payload(idem="idem-settled", subcontract_ref="3"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SETTLEMENT_LOCKED")

    def test_issue_material_full_issue_idempotent_retry_returns_existing_outbox(self) -> None:
        full_payload = self._payload(idem="idem-full-001", materials=[])
        first = self._post_issue_material(order_id=1, payload=full_payload)
        second = self._post_issue_material(order_id=1, payload=full_payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["code"], "0")
        self.assertEqual(second.json()["code"], "0")
        self.assertEqual(first.json()["data"]["outbox_id"], second.json()["data"]["outbox_id"])

        with self.SessionLocal() as session:
            material_count = session.query(LySubcontractMaterial).count()
            outbox_count = session.query(LySubcontractStockOutbox).count()
        self.assertEqual(material_count, 2)
        self.assertEqual(outbox_count, 1)

    def test_issue_material_full_issue_idempotent_retry_does_not_check_remaining_qty_first(self) -> None:
        full_payload = self._payload(idem="idem-full-remaining", materials=[])
        first = self._post_issue_material(order_id=1, payload=full_payload)
        self.assertEqual(first.status_code, 200)

        second = self._post_issue_material(order_id=1, payload=full_payload)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(second.json()["code"], "SUBCONTRACT_MATERIAL_QTY_EXCEEDED")


if __name__ == "__main__":
    unittest.main()
