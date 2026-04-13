"""Exception classification tests for subcontract module (TASK-002B)."""

from __future__ import annotations

from decimal import Decimal
import logging
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.routers.subcontract as subcontract_router
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyBomOperation
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.models.subcontract import LySubcontractStockOutbox
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.schemas.subcontract import SubcontractCreateRequest
from app.services.subcontract_service import SubcontractService


class SubcontractExceptionTest(unittest.TestCase):
    """Validate subcontract exception mapping and service transaction boundary."""

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
                    bom_no="BOM-EX-001",
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
                LySubcontractOrder(
                    id=50,
                    subcontract_no="SC-EX-50",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="waiting_inspection",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=51,
                    subcontract_no="SC-EX-51",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="processing",
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=5000,
                    subcontract_id=50,
                    company="COMP-A",
                    receipt_batch_no="SRB-EX-5000",
                    receipt_warehouse="WH-RECV-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("100"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-EX-5000",
                    idempotency_key="idem-seed-ex-5000",
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
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractStatusLog).delete()
            session.query(LySubcontractOrder).filter(LySubcontractOrder.id.in_([50, 51])).delete()
            session.add(
                LySubcontractOrder(
                    id=50,
                    subcontract_no="SC-EX-50",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="waiting_inspection",
                )
            )
            session.add(
                LySubcontractOrder(
                    id=51,
                    subcontract_no="SC-EX-51",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="processing",
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=5000,
                    subcontract_id=50,
                    company="COMP-A",
                    receipt_batch_no="SRB-EX-5000",
                    receipt_warehouse="WH-RECV-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("100"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-EX-5000",
                    idempotency_key="idem-seed-ex-5000",
                )
            )
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "exception.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _inspect_payload(
        *,
        idem: str = "idem-ex-inspect-1",
        inspected_qty: str = "100",
        rejected_qty: str = "0",
        deduction_amount_per_piece: str = "0",
    ) -> dict[str, str]:
        return {
            "receipt_batch_no": "SRB-EX-5000",
            "idempotency_key": idem,
            "inspected_qty": inspected_qty,
            "rejected_qty": rejected_qty,
            "deduction_amount_per_piece": deduction_amount_per_piece,
        }

    def test_database_read_failed_mapping(self) -> None:
        with patch.object(SubcontractService, "list_orders", side_effect=DatabaseReadFailed()):
            response = self.client.get("/api/subcontract/", headers=self._headers())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_READ_FAILED")

    def test_database_write_failed_mapping(self) -> None:
        payload = {
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "company": "COMP-A",
            "bom_id": 1,
            "planned_qty": "120",
            "process_name": "外发裁剪",
        }
        with patch.object(subcontract_router, "_commit_or_raise_write_error", side_effect=DatabaseWriteFailed()):
            response = self.client.post("/api/subcontract/", headers=self._headers(), json=payload)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

    def test_receive_database_write_failure_returns_database_write_failed(self) -> None:
        with patch.object(SubcontractService, "receive", side_effect=DatabaseWriteFailed()):
            response = self.client.post(
                "/api/subcontract/51/receive",
                headers=self._headers(),
                json={
                    "idempotency_key": "idem-ex-recv-1",
                    "receipt_warehouse": "WH-RECV-A",
                    "received_qty": "10",
                },
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

    def test_inspect_database_write_failure_returns_database_write_failed(self) -> None:
        with patch.object(SubcontractService, "inspect", side_effect=DatabaseWriteFailed()):
            response = self.client.post(
                "/api/subcontract/50/inspect",
                headers=self._headers(),
                json=self._inspect_payload(),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

    def test_unknown_exception_returns_subcontract_internal_error(self) -> None:
        with patch.object(SubcontractService, "inspect", side_effect=RuntimeError("unexpected boom")):
            response = self.client.post(
                "/api/subcontract/50/inspect",
                headers=self._headers(),
                json=self._inspect_payload(idem="idem-ex-inspect-unknown"),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_INTERNAL_ERROR")
        serialized = str(response.json())
        self.assertNotIn("RuntimeError", serialized)
        self.assertNotIn("traceback", serialized.lower())

    def test_subcontract_fail_closed_logs_are_sanitized(self) -> None:
        logger_name = "app.routers.subcontract"
        with patch.object(SubcontractService, "inspect", side_effect=RuntimeError("[SQL: UPDATE x] Authorization token")):
            with self.assertLogs(logger_name, level=logging.ERROR) as captured:
                response = self.client.post(
                    "/api/subcontract/50/inspect",
                    headers=self._headers(),
                    json=self._inspect_payload(idem="idem-ex-inspect-log"),
                )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_INTERNAL_ERROR")
        joined = "\n".join(captured.output)
        self.assertNotIn("[SQL:", joined)
        self.assertNotIn("Authorization", joined)
        self.assertNotIn("token", joined.lower())

    def test_subcontract_no_fake_stock_entry_name_after_task_002b1(self) -> None:
        response = self.client.post(
            "/api/subcontract/51/receive",
            headers=self._headers(),
            json={
                "idempotency_key": "idem-ex-recv-2",
                "receipt_warehouse": "WH-RECV-A",
                "received_qty": "10",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertIsNone(response.json()["data"]["stock_entry_name"])
        self.assertNotIn("STE-ISS", str(response.json()))
        self.assertNotIn("STE-REC", str(response.json()))

    def test_service_create_order_does_not_commit_in_service_layer(self) -> None:
        with self.SessionLocal() as session:
            service = SubcontractService(session=session)
            commit_called = False

            def _commit_guard():
                nonlocal commit_called
                commit_called = True
                raise AssertionError("service must not call commit")

            session.commit = _commit_guard  # type: ignore[method-assign]
            service.create_order(
                payload=SubcontractCreateRequest(
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    planned_qty=Decimal("10"),
                    process_name="外发裁剪",
                ),
                operator="unit.test",
            )
            self.assertFalse(commit_called)

    def test_create_subcontract_blank_company_returns_company_required_envelope(self) -> None:
        payload = {
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "company": "   ",
            "bom_id": 1,
            "planned_qty": "50",
            "process_name": "外发裁剪",
        }
        response = self.client.post("/api/subcontract/", headers=self._headers(), json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_COMPANY_REQUIRED")

    def test_create_subcontract_null_company_returns_company_required_envelope(self) -> None:
        payload = {
            "supplier": "SUP-A",
            "item_code": "ITEM-A",
            "company": None,
            "bom_id": 1,
            "planned_qty": "50",
            "process_name": "外发裁剪",
        }
        response = self.client.post("/api/subcontract/", headers=self._headers(), json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_COMPANY_REQUIRED")


if __name__ == "__main__":
    unittest.main()
