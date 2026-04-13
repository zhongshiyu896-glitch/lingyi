"""Tests for subcontract settlement export endpoints (TASK-002H)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import PermissionSourceUnavailable
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractSettlementOperation
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.subcontract_settlement_service import SettlementOperationDuplicateKeyError


class SubcontractSettlementExportTest(unittest.TestCase):
    """Validate settlement candidate/preview/lock/release behavior."""

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
            session.add_all(
                [
                    LyApparelBom(
                        id=1,
                        bom_no="BOM-SETTLE-001",
                        item_code="ITEM-A",
                        version_no="v1",
                        is_default=True,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
                    ),
                    LyApparelBom(
                        id=2,
                        bom_no="BOM-SETTLE-002",
                        item_code="ITEM-B",
                        version_no="v1",
                        is_default=True,
                        status="active",
                        created_by="seed",
                        updated_by="seed",
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
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LySubcontractSettlementOperation).delete()
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()
            self._seed_orders(session)
            self._seed_receipts(session)
            self._seed_inspections(session)
            session.commit()

    @staticmethod
    def _headers(role: str = "Subcontract Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "settlement.user", "X-LY-Dev-Roles": role}

    @staticmethod
    def _seed_orders(session) -> None:
        session.add_all(
            [
                LySubcontractOrder(
                    id=10,
                    subcontract_no="SC-SETTLE-A",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="waiting_receive",
                    resource_scope_status="ready",
                ),
                LySubcontractOrder(
                    id=11,
                    subcontract_no="SC-SETTLE-BLOCK",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="waiting_receive",
                    resource_scope_status="blocked_scope",
                ),
                LySubcontractOrder(
                    id=12,
                    subcontract_no="SC-SETTLE-CAN",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="cancelled",
                    resource_scope_status="ready",
                ),
                LySubcontractOrder(
                    id=13,
                    subcontract_no="SC-SETTLE-B",
                    supplier="SUP-B",
                    item_code="ITEM-B",
                    company="COMP-B",
                    bom_id=2,
                    process_name="外发裁剪",
                    planned_qty=Decimal("80"),
                    status="processing",
                    resource_scope_status="ready",
                ),
            ]
        )

    @staticmethod
    def _seed_receipts(session) -> None:
        session.add_all(
            [
                LySubcontractReceipt(
                    id=1000,
                    subcontract_id=10,
                    company="COMP-A",
                    receipt_batch_no="RB-ELIG",
                    receipt_warehouse="WH-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("50"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-1000",
                    idempotency_key="idem-rb-elig",
                ),
                LySubcontractReceipt(
                    id=1001,
                    subcontract_id=10,
                    company="COMP-A",
                    receipt_batch_no="RB-UNSYNC",
                    receipt_warehouse="WH-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("20"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="failed",
                    stock_entry_name=None,
                    idempotency_key="idem-rb-unsync",
                ),
                LySubcontractReceipt(
                    id=1002,
                    subcontract_id=11,
                    company="COMP-A",
                    receipt_batch_no="RB-BLOCK",
                    receipt_warehouse="WH-A",
                    item_code="ITEM-A",
                    received_qty=Decimal("20"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-1002",
                    idempotency_key="idem-rb-block",
                ),
                LySubcontractReceipt(
                    id=1003,
                    subcontract_id=13,
                    company="COMP-B",
                    receipt_batch_no="RB-B",
                    receipt_warehouse="WH-B",
                    item_code="ITEM-B",
                    received_qty=Decimal("30"),
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    sync_status="succeeded",
                    stock_entry_name="STE-REAL-1003",
                    idempotency_key="idem-rb-b",
                ),
            ]
        )

    @staticmethod
    def _seed_inspections(session) -> None:
        session.add_all(
            [
                LySubcontractInspection(
                    id=100,
                    subcontract_id=10,
                    company="COMP-A",
                    inspection_no="SIN-100",
                    receipt_batch_no="RB-ELIG",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("20"),
                    accepted_qty=Decimal("19"),
                    rejected_qty=Decimal("1"),
                    rejected_rate=Decimal("0.05"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("200"),
                    deduction_amount_per_piece=Decimal("5"),
                    deduction_amount=Decimal("5"),
                    net_amount=Decimal("195"),
                    settlement_status="unsettled",
                    settlement_line_key="subcontract_inspection:100",
                    status="inspected",
                    inspected_by="u1",
                    inspected_at=datetime(2026, 4, 10, 10, 0, 0),
                ),
                LySubcontractInspection(
                    id=101,
                    subcontract_id=10,
                    company="COMP-A",
                    inspection_no="SIN-101",
                    receipt_batch_no="RB-UNSYNC",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("10"),
                    accepted_qty=Decimal("10"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("100"),
                    deduction_amount_per_piece=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("100"),
                    settlement_status="unsettled",
                    settlement_line_key="subcontract_inspection:101",
                    status="inspected",
                    inspected_by="u1",
                    inspected_at=datetime(2026, 4, 10, 11, 0, 0),
                ),
                LySubcontractInspection(
                    id=102,
                    subcontract_id=10,
                    company="COMP-A",
                    inspection_no="SIN-102",
                    receipt_batch_no="RB-ELIG",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("8"),
                    accepted_qty=Decimal("8"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("80"),
                    deduction_amount_per_piece=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("80"),
                    settlement_status="statement_locked",
                    statement_id=900,
                    statement_no="ST-900",
                    settlement_line_key="subcontract_inspection:102",
                    status="inspected",
                    inspected_by="u2",
                    inspected_at=datetime(2026, 4, 10, 12, 0, 0),
                ),
                LySubcontractInspection(
                    id=103,
                    subcontract_id=10,
                    company="COMP-A",
                    inspection_no="SIN-103",
                    receipt_batch_no="RB-ELIG",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("7"),
                    accepted_qty=Decimal("7"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("70"),
                    deduction_amount_per_piece=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("70"),
                    settlement_status="settled",
                    statement_id=901,
                    statement_no="ST-901",
                    settlement_line_key="subcontract_inspection:103",
                    status="inspected",
                    inspected_by="u2",
                    inspected_at=datetime(2026, 4, 10, 13, 0, 0),
                ),
                LySubcontractInspection(
                    id=104,
                    subcontract_id=11,
                    company="COMP-A",
                    inspection_no="SIN-104",
                    receipt_batch_no="RB-BLOCK",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("5"),
                    accepted_qty=Decimal("5"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("50"),
                    deduction_amount_per_piece=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("50"),
                    settlement_status="unsettled",
                    settlement_line_key="subcontract_inspection:104",
                    status="inspected",
                    inspected_by="u3",
                    inspected_at=datetime(2026, 4, 10, 14, 0, 0),
                ),
                LySubcontractInspection(
                    id=105,
                    subcontract_id=13,
                    company="COMP-B",
                    inspection_no="SIN-105",
                    receipt_batch_no="RB-B",
                    item_code="ITEM-B",
                    inspected_qty=Decimal("9"),
                    accepted_qty=Decimal("9"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("12"),
                    gross_amount=Decimal("108"),
                    deduction_amount_per_piece=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("108"),
                    settlement_status="unsettled",
                    settlement_line_key="subcontract_inspection:105",
                    status="inspected",
                    inspected_by="u4",
                    inspected_at=datetime(2026, 4, 11, 9, 0, 0),
                ),
                LySubcontractInspection(
                    id=106,
                    subcontract_id=12,
                    company="COMP-A",
                    inspection_no="SIN-106",
                    receipt_batch_no="RB-ELIG",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("3"),
                    accepted_qty=Decimal("3"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("30"),
                    deduction_amount_per_piece=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("30"),
                    settlement_status="unsettled",
                    settlement_line_key="subcontract_inspection:106",
                    status="inspected",
                    inspected_by="u4",
                    inspected_at=datetime(2026, 4, 11, 10, 0, 0),
                ),
            ]
        )

    def _candidate_ids(self, **params) -> list[int]:
        response = self.client.get("/api/subcontract/settlement-candidates", headers=self._headers(), params=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        return [int(item["inspection_id"]) for item in response.json()["data"]["items"]]

    def test_settlement_candidates_return_only_eligible_inspections(self) -> None:
        ids = set(self._candidate_ids(page=1, page_size=50))
        self.assertIn(100, ids)
        self.assertIn(105, ids)
        self.assertNotIn(101, ids)
        self.assertNotIn(102, ids)
        self.assertNotIn(103, ids)
        self.assertNotIn(104, ids)
        self.assertNotIn(106, ids)

    def test_settlement_candidates_filter_by_company_supplier_date_and_permission(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
                allowed_suppliers={"SUP-A"},
                allowed_warehouses=set(),
            ),
        ):
            os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
            response = self.client.get(
                "/api/subcontract/settlement-candidates",
                headers=self._headers(),
                params={
                    "company": "COMP-A",
                    "supplier": "SUP-A",
                    "from_date": "2026-04-10",
                    "to_date": "2026-04-10",
                    "page": 1,
                    "page_size": 50,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        ids = [int(item["inspection_id"]) for item in response.json()["data"]["items"]]
        self.assertEqual(ids, [100])

    def test_settlement_candidates_exclude_unsynced_receipt(self) -> None:
        ids = set(self._candidate_ids(page=1, page_size=50))
        self.assertNotIn(101, ids)

    def test_settlement_candidates_exclude_locked_and_settled_inspections(self) -> None:
        ids = set(self._candidate_ids(page=1, page_size=50))
        self.assertNotIn(102, ids)
        self.assertNotIn(103, ids)

    def test_settlement_preview_sums_inspection_amount_facts(self) -> None:
        response = self.client.post(
            "/api/subcontract/settlement-preview",
            headers=self._headers(),
            json={"inspection_ids": [100, 105]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["line_count"], 2)
        self.assertEqual(Decimal(str(data["total_qty"])), Decimal("29.000000"))
        self.assertEqual(Decimal(str(data["gross_amount"])), Decimal("308.00"))
        self.assertEqual(Decimal(str(data["deduction_amount"])), Decimal("5.00"))
        self.assertEqual(Decimal(str(data["net_amount"])), Decimal("303.00"))

    def test_settlement_preview_does_not_use_old_amount_formula(self) -> None:
        response = self.client.post(
            "/api/subcontract/settlement-preview",
            headers=self._headers(),
            json={"inspection_ids": [100]},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        # old wrong formula: 20 - 5 = 15
        self.assertEqual(Decimal(str(data["net_amount"])), Decimal("195.00"))
        self.assertNotEqual(Decimal(str(data["net_amount"])), Decimal("15.00"))

    def test_settlement_lock_marks_inspections_statement_locked(self) -> None:
        response = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 500,
                "statement_no": "ST-500",
                "inspection_ids": [100],
                "idempotency_key": "idem-lock-500",
                "remark": "lock",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")

        with self.SessionLocal() as session:
            row = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(row.settlement_status), "statement_locked")
            self.assertEqual(int(row.statement_id), 500)
            self.assertEqual(str(row.statement_no), "ST-500")

    def test_settlement_lock_is_idempotent_for_same_statement(self) -> None:
        payload = {
            "statement_id": 501,
            "statement_no": "ST-501",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-501",
            "remark": "same",
        }
        first = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)
        second = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["code"], "0")
        self.assertEqual(second.json()["data"]["locked_count"], 1)

    def test_settlement_lock_conflicts_for_other_statement(self) -> None:
        self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 510,
                "statement_no": "ST-510",
                "inspection_ids": [100],
                "idempotency_key": "idem-lock-510",
                "remark": "first",
            },
        )
        response = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 511,
                "statement_no": "ST-511",
                "inspection_ids": [100],
                "idempotency_key": "idem-lock-511",
                "remark": "second",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED")

    def test_settlement_lock_rolls_back_all_rows_on_failure(self) -> None:
        response = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 520,
                "statement_no": "ST-520",
                "inspection_ids": [100, 102],
                "idempotency_key": "idem-lock-520",
                "remark": "rollback",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED")

        with self.SessionLocal() as session:
            row_100 = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(row_100.settlement_status), "unsettled")
            self.assertIsNone(row_100.statement_id)

    def test_settlement_release_unlocks_statement_locked_rows(self) -> None:
        lock_resp = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 530,
                "statement_no": "ST-530",
                "inspection_ids": [100],
                "idempotency_key": "idem-lock-530",
                "remark": "lock",
            },
        )
        self.assertEqual(lock_resp.status_code, 200)

        release_resp = self.client.post(
            "/api/subcontract/settlement-locks/release",
            headers=self._headers(),
            json={
                "statement_id": 530,
                "statement_no": "ST-530",
                "inspection_ids": [100],
                "idempotency_key": "idem-release-530",
                "reason": "reopen",
            },
        )
        self.assertEqual(release_resp.status_code, 200)
        self.assertEqual(release_resp.json()["code"], "0")

        with self.SessionLocal() as session:
            row = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(row.settlement_status), "unsettled")
            self.assertIsNone(row.statement_id)
            self.assertIsNone(row.statement_no)

    def test_settlement_release_rejects_settled_rows(self) -> None:
        response = self.client.post(
            "/api/subcontract/settlement-locks/release",
            headers=self._headers(),
            json={
                "statement_id": 901,
                "statement_no": "ST-901",
                "inspection_ids": [103],
                "idempotency_key": "idem-release-901",
                "reason": "reopen",
            },
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SETTLEMENT_STATUS_INVALID")

    def test_settlement_lock_duplicate_unique_conflict_replays_first_response(self) -> None:
        payload = {
            "statement_id": 710,
            "statement_no": "ST-710",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-710",
            "remark": "lock",
        }
        first = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)
        self.assertEqual(first.status_code, 200)

        with self.SessionLocal() as session:
            existing_op = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "lock",
                    LySubcontractSettlementOperation.idempotency_key == "idem-lock-710",
                )
                .order_by(LySubcontractSettlementOperation.id.desc())
                .first()
            )
            self.assertIsNotNone(existing_op)

        with patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._load_operation",
            side_effect=[None, None, existing_op],
        ), patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._record_operation_success",
            side_effect=SettlementOperationDuplicateKeyError(),
        ):
            replay = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)

        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["code"], "0")
        self.assertEqual(replay.json()["data"]["idempotent_replay"], True)
        self.assertEqual(replay.json()["data"]["idempotency_key"], "idem-lock-710")
        self.assertIsNotNone(replay.json()["data"]["operation_id"])

    def test_settlement_release_duplicate_unique_conflict_replays_first_response(self) -> None:
        lock_payload = {
            "statement_id": 711,
            "statement_no": "ST-711",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-711",
            "remark": "lock",
        }
        release_payload = {
            "statement_id": 711,
            "statement_no": "ST-711",
            "inspection_ids": [100],
            "idempotency_key": "idem-release-711",
            "reason": "release",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=lock_payload).status_code,
            200,
        )
        first_release = self.client.post(
            "/api/subcontract/settlement-locks/release",
            headers=self._headers(),
            json=release_payload,
        )
        self.assertEqual(first_release.status_code, 200)

        with self.SessionLocal() as session:
            existing_op = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "release",
                    LySubcontractSettlementOperation.idempotency_key == "idem-release-711",
                )
                .order_by(LySubcontractSettlementOperation.id.desc())
                .first()
            )
            self.assertIsNotNone(existing_op)

        with patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._load_operation",
            side_effect=[None, None, existing_op],
        ), patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._record_operation_success",
            side_effect=SettlementOperationDuplicateKeyError(),
        ):
            replay = self.client.post(
                "/api/subcontract/settlement-locks/release",
                headers=self._headers(),
                json=release_payload,
            )

        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["code"], "0")
        self.assertEqual(replay.json()["data"]["idempotent_replay"], True)
        self.assertEqual(replay.json()["data"]["idempotency_key"], "idem-release-711")
        self.assertIsNotNone(replay.json()["data"]["operation_id"])

    def test_settlement_lock_replay_sets_idempotent_replay_true(self) -> None:
        payload = {
            "statement_id": 712,
            "statement_no": "ST-712",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-712",
            "remark": "lock",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload).status_code,
            200,
        )
        replay = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["data"]["idempotent_replay"], True)

    def test_settlement_release_replay_sets_idempotent_replay_true(self) -> None:
        lock_payload = {
            "statement_id": 713,
            "statement_no": "ST-713",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-713",
            "remark": "lock",
        }
        release_payload = {
            "statement_id": 713,
            "statement_no": "ST-713",
            "inspection_ids": [100],
            "idempotency_key": "idem-release-713",
            "reason": "release",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=lock_payload).status_code,
            200,
        )
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks/release", headers=self._headers(), json=release_payload).status_code,
            200,
        )
        replay = self.client.post("/api/subcontract/settlement-locks/release", headers=self._headers(), json=release_payload)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["data"]["idempotent_replay"], True)

    def test_settlement_first_lock_sets_idempotent_replay_false(self) -> None:
        payload = {
            "statement_id": 714,
            "statement_no": "ST-714",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-714",
            "remark": "lock",
        }
        first = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["data"]["idempotent_replay"], False)

    def test_settlement_first_release_sets_idempotent_replay_false(self) -> None:
        lock_payload = {
            "statement_id": 715,
            "statement_no": "ST-715",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-715",
            "remark": "lock",
        }
        release_payload = {
            "statement_id": 715,
            "statement_no": "ST-715",
            "inspection_ids": [100],
            "idempotency_key": "idem-release-715",
            "reason": "release",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=lock_payload).status_code,
            200,
        )
        first = self.client.post("/api/subcontract/settlement-locks/release", headers=self._headers(), json=release_payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["data"]["idempotent_replay"], False)

    def test_settlement_duplicate_unique_conflict_different_hash_returns_conflict(self) -> None:
        first_payload = {
            "statement_id": 716,
            "statement_no": "ST-716",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-716",
            "remark": "first",
        }
        second_payload = {
            "statement_id": 716,
            "statement_no": "ST-716",
            "inspection_ids": [105],
            "idempotency_key": "idem-lock-716",
            "remark": "second",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=first_payload).status_code,
            200,
        )

        with self.SessionLocal() as session:
            existing_op = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "lock",
                    LySubcontractSettlementOperation.idempotency_key == "idem-lock-716",
                )
                .order_by(LySubcontractSettlementOperation.id.desc())
                .first()
            )
            self.assertIsNotNone(existing_op)

        with patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._load_operation",
            side_effect=[None, None, existing_op],
        ), patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._record_operation_success",
            side_effect=SettlementOperationDuplicateKeyError(),
        ):
            conflict = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=second_payload)

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT")

    def test_settlement_duplicate_unique_conflict_does_not_create_second_operation(self) -> None:
        payload = {
            "statement_id": 717,
            "statement_no": "ST-717",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-717",
            "remark": "lock",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload).status_code,
            200,
        )
        with self.SessionLocal() as session:
            existing_op = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "lock",
                    LySubcontractSettlementOperation.idempotency_key == "idem-lock-717",
                )
                .order_by(LySubcontractSettlementOperation.id.desc())
                .first()
            )
            self.assertIsNotNone(existing_op)

        with patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._load_operation",
            side_effect=[None, None, existing_op],
        ), patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._record_operation_success",
            side_effect=SettlementOperationDuplicateKeyError(),
        ):
            replay = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["code"], "0")

        with self.SessionLocal() as session:
            op_count = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "lock",
                    LySubcontractSettlementOperation.idempotency_key == "idem-lock-717",
                )
                .count()
            )
            self.assertEqual(op_count, 1)

    def test_settlement_duplicate_unique_conflict_does_not_mutate_inspection_again(self) -> None:
        payload = {
            "statement_id": 718,
            "statement_no": "ST-718",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-718",
            "remark": "lock",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload).status_code,
            200,
        )
        with self.SessionLocal() as session:
            inspection_before = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            locked_at_before = inspection_before.settlement_locked_at
            existing_op = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "lock",
                    LySubcontractSettlementOperation.idempotency_key == "idem-lock-718",
                )
                .order_by(LySubcontractSettlementOperation.id.desc())
                .first()
            )
            self.assertIsNotNone(existing_op)

        with patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._load_operation",
            side_effect=[None, None, existing_op],
        ), patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._record_operation_success",
            side_effect=SettlementOperationDuplicateKeyError(),
        ):
            replay = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=payload)
        self.assertEqual(replay.status_code, 200)

        with self.SessionLocal() as session:
            inspection_after = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(inspection_after.settlement_status), "statement_locked")
            self.assertEqual(int(inspection_after.statement_id), 718)
            self.assertEqual(str(inspection_after.statement_no), "ST-718")
            self.assertEqual(inspection_after.settlement_locked_at, locked_at_before)

    def test_settlement_request_id_is_not_used_as_idempotency_history(self) -> None:
        payload = {
            "statement_id": 719,
            "statement_no": "ST-719",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-719",
            "remark": "lock",
        }
        first = self.client.post(
            "/api/subcontract/settlement-locks",
            headers={**self._headers(), "X-Request-ID": "req-1"},
            json=payload,
        )
        second = self.client.post(
            "/api/subcontract/settlement-locks",
            headers={**self._headers(), "X-Request-ID": "req-2"},
            json=payload,
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["data"]["idempotent_replay"], True)

        with self.SessionLocal() as session:
            op_count = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "lock",
                    LySubcontractSettlementOperation.idempotency_key == "idem-lock-719",
                )
                .count()
            )
            self.assertEqual(op_count, 1)

    def test_settlement_lock_release_then_old_lock_retry_does_not_relock(self) -> None:
        lock_payload = {
            "statement_id": 610,
            "statement_no": "ST-610",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-610",
            "remark": "lock",
        }
        release_payload = {
            "statement_id": 610,
            "statement_no": "ST-610",
            "inspection_ids": [100],
            "idempotency_key": "idem-release-610",
            "reason": "release",
        }
        first_lock = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=lock_payload)
        self.assertEqual(first_lock.status_code, 200)
        release = self.client.post("/api/subcontract/settlement-locks/release", headers=self._headers(), json=release_payload)
        self.assertEqual(release.status_code, 200)

        replay_lock = self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=lock_payload)
        self.assertEqual(replay_lock.status_code, 200)
        self.assertEqual(replay_lock.json()["code"], "0")

        with self.SessionLocal() as session:
            inspection = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(inspection.settlement_status), "unsettled")
            self.assertIsNone(inspection.statement_id)
            self.assertIsNone(inspection.statement_no)
            lock_ops = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "lock",
                    LySubcontractSettlementOperation.idempotency_key == "idem-lock-610",
                )
                .all()
            )
            self.assertEqual(len(lock_ops), 1)

    def test_settlement_release_retry_returns_first_result_without_mutation(self) -> None:
        lock_payload = {
            "statement_id": 620,
            "statement_no": "ST-620",
            "inspection_ids": [100],
            "idempotency_key": "idem-lock-620",
            "remark": "lock",
        }
        release_payload = {
            "statement_id": 620,
            "statement_no": "ST-620",
            "inspection_ids": [100],
            "idempotency_key": "idem-release-620",
            "reason": "release",
        }
        self.assertEqual(
            self.client.post("/api/subcontract/settlement-locks", headers=self._headers(), json=lock_payload).status_code,
            200,
        )
        first_release = self.client.post(
            "/api/subcontract/settlement-locks/release",
            headers=self._headers(),
            json=release_payload,
        )
        second_release = self.client.post(
            "/api/subcontract/settlement-locks/release",
            headers=self._headers(),
            json=release_payload,
        )
        self.assertEqual(first_release.status_code, 200)
        self.assertEqual(second_release.status_code, 200)
        self.assertEqual(second_release.json()["data"]["released_count"], 1)

        with self.SessionLocal() as session:
            inspection = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(inspection.settlement_status), "unsettled")
            self.assertIsNone(inspection.statement_id)
            release_ops = (
                session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == "release",
                    LySubcontractSettlementOperation.idempotency_key == "idem-release-620",
                )
                .all()
            )
            self.assertEqual(len(release_ops), 1)

    def test_settlement_same_idempotency_key_different_payload_conflicts(self) -> None:
        first = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 630,
                "statement_no": "ST-630",
                "inspection_ids": [100],
                "idempotency_key": "idem-lock-630",
                "remark": "first",
            },
        )
        second = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 630,
                "statement_no": "ST-630",
                "inspection_ids": [105],
                "idempotency_key": "idem-lock-630",
                "remark": "second",
            },
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT")

    def test_settlement_operation_record_is_append_only(self) -> None:
        self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 640,
                "statement_no": "ST-640",
                "inspection_ids": [100],
                "idempotency_key": "idem-lock-640",
                "remark": "lock",
            },
        )
        self.client.post(
            "/api/subcontract/settlement-locks/release",
            headers=self._headers(),
            json={
                "statement_id": 640,
                "statement_no": "ST-640",
                "inspection_ids": [100],
                "idempotency_key": "idem-release-640",
                "reason": "release",
            },
        )
        self.client.post(
            "/api/subcontract/settlement-locks/release",
            headers=self._headers(),
            json={
                "statement_id": 640,
                "statement_no": "ST-640",
                "inspection_ids": [100],
                "idempotency_key": "idem-release-640",
                "reason": "release",
            },
        )

        with self.SessionLocal() as session:
            ops = (
                session.query(LySubcontractSettlementOperation)
                .order_by(LySubcontractSettlementOperation.id.asc())
                .all()
            )
            self.assertEqual(len(ops), 2)
            self.assertEqual(str(ops[0].operation_type), "lock")
            self.assertEqual(str(ops[1].operation_type), "release")

    def test_settlement_operation_write_failure_rolls_back_lock(self) -> None:
        with patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._record_operation_success",
            side_effect=DatabaseWriteFailed(),
        ):
            response = self.client.post(
                "/api/subcontract/settlement-locks",
                headers=self._headers(),
                json={
                    "statement_id": 650,
                    "statement_no": "ST-650",
                    "inspection_ids": [100],
                    "idempotency_key": "idem-lock-650",
                    "remark": "lock",
                },
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

        with self.SessionLocal() as session:
            inspection = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(inspection.settlement_status), "unsettled")
            self.assertIsNone(inspection.statement_id)
            op_count = session.query(LySubcontractSettlementOperation).count()
            self.assertEqual(op_count, 0)

    def test_settlement_operation_write_failure_rolls_back_release(self) -> None:
        self.assertEqual(
            self.client.post(
                "/api/subcontract/settlement-locks",
                headers=self._headers(),
                json={
                    "statement_id": 660,
                    "statement_no": "ST-660",
                    "inspection_ids": [100],
                    "idempotency_key": "idem-lock-660",
                    "remark": "lock",
                },
            ).status_code,
            200,
        )
        with patch(
            "app.services.subcontract_settlement_service.SubcontractSettlementService._record_operation_success",
            side_effect=DatabaseWriteFailed(),
        ):
            response = self.client.post(
                "/api/subcontract/settlement-locks/release",
                headers=self._headers(),
                json={
                    "statement_id": 660,
                    "statement_no": "ST-660",
                    "inspection_ids": [100],
                    "idempotency_key": "idem-release-660",
                    "reason": "release",
                },
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_WRITE_FAILED")

        with self.SessionLocal() as session:
            inspection = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
            self.assertEqual(str(inspection.settlement_status), "statement_locked")
            self.assertEqual(int(inspection.statement_id), 660)
            release_count = (
                session.query(LySubcontractSettlementOperation)
                .filter(LySubcontractSettlementOperation.operation_type == "release")
                .count()
            )
            self.assertEqual(release_count, 0)

    def test_settlement_idempotency_key_accepts_128_chars(self) -> None:
        response = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 670,
                "statement_no": "ST-670",
                "inspection_ids": [100],
                "idempotency_key": "k" * 128,
                "remark": "lock",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")

    def test_settlement_idempotency_key_rejects_over_128_chars(self) -> None:
        response = self.client.post(
            "/api/subcontract/settlement-locks",
            headers=self._headers(),
            json={
                "statement_id": 671,
                "statement_no": "ST-671",
                "inspection_ids": [100],
                "idempotency_key": "k" * 129,
                "remark": "lock",
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_settlement_summary_is_filter_total_not_page_total(self) -> None:
        response = self.client.get(
            "/api/subcontract/settlement-candidates",
            headers=self._headers(),
            params={"page": 1, "page_size": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(int(data["summary"]["line_count"]), 2)
        self.assertEqual(Decimal(str(data["summary"]["gross_amount"])), Decimal("308.00"))
        self.assertEqual(Decimal(str(data["summary"]["deduction_amount"])), Decimal("5.00"))
        self.assertEqual(Decimal(str(data["summary"]["net_amount"])), Decimal("303.00"))

    def test_settlement_summary_uses_same_resource_filter_as_candidates(self) -> None:
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
                allowed_suppliers={"SUP-A"},
                allowed_warehouses=set(),
            ),
        ):
            os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
            response = self.client.get(
                "/api/subcontract/settlement-candidates",
                headers=self._headers(),
                params={"page": 1, "page_size": 1},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["total"], 1)
        self.assertEqual(int(data["summary"]["line_count"]), 1)
        self.assertEqual(Decimal(str(data["summary"]["gross_amount"])), Decimal("200.00"))
        self.assertEqual(Decimal(str(data["summary"]["net_amount"])), Decimal("195.00"))

    def test_settlement_permission_source_fail_closed(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch(
            "app.services.erpnext_permission_adapter.ERPNextPermissionAdapter.get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="upstream down",
                exception_type="PermissionSourceUnavailable",
                exception_message="timeout",
            ),
        ):
            response = self.client.get(
                "/api/subcontract/settlement-candidates",
                headers=self._headers(),
                params={"page": 1, "page_size": 20},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")

    def test_settlement_security_audit_on_forbidden(self) -> None:
        response = self.client.get(
            "/api/subcontract/settlement-candidates",
            headers=self._headers(role="Subcontract Viewer"),
            params={"page": 1, "page_size": 20},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

        with self.SessionLocal() as session:
            row = (
                session.query(LySecurityAuditLog)
                .filter(LySecurityAuditLog.module == "subcontract")
                .order_by(LySecurityAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)
            self.assertEqual(str(row.action), "subcontract:settlement_read")

    def test_no_erpnext_write_called_by_settlement_export_or_lock(self) -> None:
        with patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_material_issue"
        ) as mock_create, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.create_material_receipt"
        ) as mock_create_receipt, patch(
            "app.services.erpnext_stock_entry_service.ERPNextStockEntryService.submit_stock_entry"
        ) as mock_submit:
            candidate_resp = self.client.get(
                "/api/subcontract/settlement-candidates",
                headers=self._headers(),
                params={"page": 1, "page_size": 20},
            )
            self.assertEqual(candidate_resp.status_code, 200)

            lock_resp = self.client.post(
                "/api/subcontract/settlement-locks",
                headers=self._headers(),
                json={
                    "statement_id": 540,
                    "statement_no": "ST-540",
                    "inspection_ids": [100],
                    "idempotency_key": "idem-lock-540",
                    "remark": "no erpnext write",
                },
            )
            self.assertEqual(lock_resp.status_code, 200)

            self.assertEqual(mock_create.call_count, 0)
            self.assertEqual(mock_create_receipt.call_count, 0)
            self.assertEqual(mock_submit.call_count, 0)
