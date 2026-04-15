"""Idempotency tests for factory statement APIs (TASK-006B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementOperation
from app.services.factory_statement_service import FactoryStatementService
from tests.test_factory_statement_api import FactoryStatementApiBase


class FactoryStatementIdempotencyTest(FactoryStatementApiBase):
    """Validate replay/conflict behavior for company + idempotency_key + request_hash."""

    def test_same_key_same_hash_replays_same_statement(self) -> None:
        payload = self._create_payload(idempotency_key="idem-replay-001")

        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=payload,
        )
        self.assertEqual(first.status_code, 200)
        first_data = first.json()["data"]

        replay = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=payload,
        )
        self.assertEqual(replay.status_code, 200)
        replay_data = replay.json()["data"]

        self.assertEqual(first_data["statement_id"], replay_data["statement_id"])
        self.assertEqual(first_data["statement_no"], replay_data["statement_no"])
        self.assertTrue(bool(replay_data["idempotent_replay"]))

        with self.SessionLocal() as session:
            total = session.query(LyFactoryStatement).count()
        self.assertEqual(total, 1)

    def test_same_key_different_hash_returns_conflict(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-conflict-001", to_date="2026-04-30"),
        )
        self.assertEqual(first.status_code, 200)

        conflict = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-conflict-001", to_date="2026-04-29"),
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT")

        with self.SessionLocal() as session:
            rows = session.query(LyFactoryStatement).all()
            self.assertEqual(len(rows), 1)
            self.assertEqual(Decimal(str(rows[0].net_amount)), Decimal("4700"))

    def test_active_scope_prevents_second_draft_with_new_idempotency_key(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-active-prevent-1"),
        )
        self.assertEqual(first.status_code, 200)
        first_data = first.json()["data"]

        second = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-active-prevent-2"),
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS")
        second_data = second.json()["data"]
        self.assertEqual(first_data["statement_id"], second_data["statement_id"])
        self.assertEqual(first_data["statement_no"], second_data["statement_no"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyFactoryStatement).count(), 1)

    def test_active_scope_returns_existing_statement_reference(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-active-replay-1"),
        )
        self.assertEqual(first.status_code, 200)
        first_data = first.json()["data"]

        conflict = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-active-replay-2"),
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS")
        conflict_data = conflict.json()["data"]
        self.assertEqual(first_data["statement_id"], conflict_data["statement_id"])
        self.assertEqual(first_data["statement_no"], conflict_data["statement_no"])

    def test_active_scope_unique_conflict_reloads_existing_statement(self) -> None:
        with self.SessionLocal() as session:
            service = FactoryStatementService(session)
            request_hash = service._build_request_hash(
                company="COMP-A",
                supplier="SUP-A",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 30),
            )
            existing = LyFactoryStatement(
                statement_no="FS-RACE-EXISTING",
                company="COMP-A",
                supplier="SUP-A",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 30),
                source_type="subcontract_inspection",
                source_count=2,
                inspected_qty=Decimal("500"),
                rejected_qty=Decimal("10"),
                accepted_qty=Decimal("490"),
                gross_amount=Decimal("5000"),
                deduction_amount=Decimal("300"),
                net_amount=Decimal("4700"),
                rejected_rate=Decimal("0.02"),
                statement_status="draft",
                idempotency_key="idem-active-race-existing",
                request_hash=request_hash,
                created_by="tester",
            )
            session.add(existing)
            session.commit()
            first_data = {
                "statement_id": int(existing.id),
                "statement_no": str(existing.statement_no),
            }

        original_find = FactoryStatementService._find_active_scope_statement
        calls = {"count": 0}

        def _simulate_race(self, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                return None
            return original_find(self, **kwargs)

        with patch.object(FactoryStatementService, "_find_active_scope_statement", new=_simulate_race), patch.object(
            FactoryStatementService,
            "_flush_statement_once",
            side_effect=IntegrityError("insert", {}, Exception("duplicate active scope")),
        ):
            conflict = self.client.post(
                "/api/factory-statements/",
                headers=self._headers(),
                json=self._create_payload(idempotency_key="idem-active-race-2"),
            )

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS")
        conflict_data = conflict.json()["data"]
        self.assertEqual(first_data["statement_id"], conflict_data["statement_id"])
        self.assertEqual(first_data["statement_no"], conflict_data["statement_no"])

    def test_different_period_allows_new_statement(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(
                idempotency_key="idem-period-1",
                from_date="2026-04-10",
                to_date="2026-04-10",
            ),
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(
                idempotency_key="idem-period-2",
                from_date="2026-04-11",
                to_date="2026-04-11",
            ),
        )
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(
            first.json()["data"]["statement_id"],
            second.json()["data"]["statement_id"],
        )

    def test_different_supplier_allows_new_statement(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-supplier-1", supplier="SUP-A"),
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-supplier-2", supplier="SUP-B"),
        )
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(
            first.json()["data"]["statement_id"],
            second.json()["data"]["statement_id"],
        )

    def test_confirm_same_key_same_hash_replays_same_operation(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-confirm-replay-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-confirm-replay", "remark": "ok"},
        )
        self.assertEqual(first.status_code, 200)

        replay = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-confirm-replay", "remark": "ok"},
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["code"], "0")
        self.assertTrue(bool(replay.json()["data"]["idempotent_replay"]))

        with self.SessionLocal() as session:
            rows = (
                session.query(LyFactoryStatementOperation)
                .filter(
                    LyFactoryStatementOperation.statement_id == statement_id,
                    LyFactoryStatementOperation.operation_type == "confirm",
                )
                .all()
            )
            self.assertEqual(len(rows), 1)

    def test_confirm_same_key_different_payload_conflict(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-confirm-conflict-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-confirm-conflict", "remark": "A"},
        )
        self.assertEqual(first.status_code, 200)

        conflict = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-confirm-conflict", "remark": "B"},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT")

    def test_cancel_same_key_same_hash_replays_same_operation(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-cancel-replay-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-replay", "reason": "manual cancel"},
        )
        self.assertEqual(first.status_code, 200)

        replay = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-replay", "reason": "manual cancel"},
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["code"], "0")
        self.assertTrue(bool(replay.json()["data"]["idempotent_replay"]))

    def test_cancel_same_key_different_payload_conflict(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-cancel-conflict-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-conflict", "reason": "A"},
        )
        self.assertEqual(first.status_code, 200)

        conflict = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-conflict", "reason": "B"},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT")

    def test_confirm_concurrent_same_idempotency_key_replays_without_duplicate_operation(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-confirm-race-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        with self.SessionLocal() as session:
            service = FactoryStatementService(session)
            request_hash = service._build_operation_hash(
                statement_id=statement_id,
                operation_type="confirm",
                remark="race",
            )
            existing = LyFactoryStatementOperation(
                company="COMP-A",
                statement_id=statement_id,
                operation_type="confirm",
                idempotency_key="idem-confirm-race-op",
                request_hash=request_hash,
                result_status="confirmed",
                result_user="factory.statement.user",
                result_at=datetime.utcnow(),
                remark="race",
            )
            session.add(existing)
            session.commit()

        original_find = FactoryStatementService._find_operation_by_idempotency
        calls = {"count": 0}

        def _simulate_race(self, **kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                return None
            return original_find(self, **kwargs)

        with patch.object(FactoryStatementService, "_find_operation_by_idempotency", new=_simulate_race), patch.object(
            FactoryStatementService,
            "_flush_operation_once",
            side_effect=IntegrityError("insert", {}, Exception("duplicate operation key")),
        ):
            replay = self.client.post(
                f"/api/factory-statements/{statement_id}/confirm",
                headers=self._headers(),
                json={"idempotency_key": "idem-confirm-race-op", "remark": "race"},
            )

        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["code"], "0")
        self.assertTrue(bool(replay.json()["data"]["idempotent_replay"]))
        self.assertNotEqual(replay.json()["code"], "FACTORY_STATEMENT_DATABASE_WRITE_FAILED")

        with self.SessionLocal() as session:
            total = (
                session.query(LyFactoryStatementOperation)
                .filter(
                    LyFactoryStatementOperation.statement_id == statement_id,
                    LyFactoryStatementOperation.operation_type == "confirm",
                    LyFactoryStatementOperation.idempotency_key == "idem-confirm-race-op",
                )
                .count()
            )
        self.assertEqual(total, 1)


if __name__ == "__main__":
    unittest.main()
