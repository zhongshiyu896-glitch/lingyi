"""Outbox forbidden diagnostics throttling tests (TASK-003I)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
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
from app.models.audit import LySecurityAuditLog
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopJobCardSyncLog
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.models.workshop import YsWorkshopOutboxAccessDenial
from app.models.workshop import YsWorkshopTicket
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.workshop_outbox_service import WorkshopOutboxService


class WorkshopOutboxAuditThrottleTest(unittest.TestCase):
    """Validate forbidden diagnostics throttle/dedupe and no-blocking behavior."""

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
        WorkshopBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyOperationWageRate(
                    id=1,
                    item_code="ITEM-A",
                    company="COMP-A",
                    is_global=False,
                    process_name="sew",
                    wage_rate="0.5",
                    effective_from=date(2026, 1, 1),
                    effective_to=None,
                    status="active",
                    created_by="seed",
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
        app.dependency_overrides[workshop_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(workshop_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        os.environ["WORKSHOP_ENABLE_FORBIDDEN_DIAGNOSTICS"] = "false"
        os.environ["WORKSHOP_FORBIDDEN_DIAGNOSTIC_LIMIT"] = "50"
        os.environ["WORKSHOP_OUTBOX_DENIAL_AUDIT_COOLDOWN_SECONDS"] = "21600"

        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(YsWorkshopJobCardSyncLog).delete()
            session.query(YsWorkshopOutboxAccessDenial).delete()
            session.query(YsWorkshopJobCardSyncOutbox).delete()
            session.query(YsWorkshopTicket).delete()
            session.commit()

    @staticmethod
    def _headers(user: str = "svc.worker", role: str = "LY Integration Service") -> dict[str, str]:
        return {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}

    @staticmethod
    def _perm(*, items: set[str], companies: set[str], unrestricted: bool = False) -> UserPermissionResult:
        return UserPermissionResult(
            source_available=True,
            unrestricted=unrestricted,
            allowed_items=items,
            allowed_companies=companies,
        )

    def _seed_outbox(
        self,
        *,
        job_card: str,
        item_code: str,
        company: str,
    ) -> int:
        with self.SessionLocal() as session:
            ticket = YsWorkshopTicket(
                ticket_no=f"TICKET-{job_card}",
                ticket_key=f"KEY-{job_card}",
                job_card=job_card,
                work_order="WO-001",
                bom_id=None,
                item_code=item_code or "",
                employee="EMP-001",
                process_name="sew",
                color="black",
                size="M",
                operation_type="register",
                qty=Decimal("10"),
                unit_wage=Decimal("0.5"),
                wage_amount=Decimal("5"),
                work_date=date(2026, 4, 12),
                source="manual",
                source_ref="REF",
                original_ticket_id=None,
                sync_status="pending",
                created_by="seed",
            )
            session.add(ticket)
            session.flush()
            outbox = WorkshopOutboxService(session=session).enqueue(
                job_card=job_card,
                work_order="WO-001",
                item_code=item_code,
                company=company,
                local_completed_qty=Decimal("10"),
                source_type="ticket_register",
                source_ids=[int(ticket.id)],
                request_id="rid-seed",
                created_by="seed",
            )
            outbox.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.commit()
            return int(outbox.id)

    def _security_count(self, *, event_type: str = "AUTH_FORBIDDEN") -> int:
        with self.SessionLocal() as session:
            return (
                session.query(LySecurityAuditLog)
                .filter(
                    LySecurityAuditLog.module == "workshop",
                    LySecurityAuditLog.action == "workshop:job_card_sync_worker",
                    LySecurityAuditLog.event_type == event_type,
                )
                .count()
            )

    def test_default_run_once_does_not_scan_forbidden_outbox(self) -> None:
        self._seed_outbox(job_card="JC-DIAG-DEFAULT-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["forbidden_diagnostics_enabled"], False)
        self.assertEqual(data["forbidden_diagnostic_count"], 0)
        self.assertEqual(data.get("skipped_forbidden_count", 0), 0)
        self.assertEqual(data.get("skipped_forbidden", 0), 0)
        self.assertEqual(data["processed_count"], 0)
        with self.SessionLocal() as session:
            denial_count = session.query(YsWorkshopOutboxAccessDenial).count()
        self.assertEqual(denial_count, 0)

    def test_default_run_once_does_not_write_repeated_forbidden_security_audit(self) -> None:
        self._seed_outbox(job_card="JC-DIAG-DEFAULT-002", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())
            self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())
            self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(self._security_count(event_type="AUTH_FORBIDDEN"), 0)

    def test_forbidden_diagnostics_requires_internal_permission(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true",
                headers=self._headers(user="normal.user", role="Workshop Manager"),
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_forbidden_diagnostics_first_seen_writes_one_security_audit(self) -> None:
        self._seed_outbox(job_card="JC-DIAG-FIRST-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true",
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["forbidden_diagnostics_enabled"], True)
        self.assertEqual(data["forbidden_diagnostic_count"], 1)
        self.assertEqual(data.get("skipped_forbidden_count", 1), data["forbidden_diagnostic_count"])
        self.assertEqual(data.get("skipped_forbidden", 1), data["forbidden_diagnostic_count"])
        self.assertEqual(self._security_count(event_type="AUTH_FORBIDDEN"), 1)

    def test_forbidden_diagnostics_repeated_within_cooldown_dedupes_audit(self) -> None:
        self._seed_outbox(job_card="JC-DIAG-COOL-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())
        self.assertEqual(self._security_count(event_type="AUTH_FORBIDDEN"), 1)

    def test_forbidden_diagnostics_updates_seen_count_within_cooldown(self) -> None:
        outbox_id = self._seed_outbox(job_card="JC-DIAG-SEEN-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())
        with self.SessionLocal() as session:
            denial = (
                session.query(YsWorkshopOutboxAccessDenial)
                .filter(
                    YsWorkshopOutboxAccessDenial.outbox_id == outbox_id,
                    YsWorkshopOutboxAccessDenial.principal == "svc.worker",
                )
                .first()
            )
        self.assertIsNotNone(denial)
        self.assertEqual(int(denial.seen_count), 3)

    def test_forbidden_diagnostics_after_cooldown_writes_one_more_audit(self) -> None:
        outbox_id = self._seed_outbox(job_card="JC-DIAG-COOL-EXPIRE-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())

        with self.SessionLocal() as session:
            denial = (
                session.query(YsWorkshopOutboxAccessDenial)
                .filter(YsWorkshopOutboxAccessDenial.outbox_id == outbox_id)
                .first()
            )
            self.assertIsNotNone(denial)
            denial.next_audit_at = datetime.utcnow() - timedelta(seconds=1)
            session.commit()

        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())

        self.assertEqual(self._security_count(event_type="AUTH_FORBIDDEN"), 2)

    def test_denial_dedupe_key_has_no_sensitive_plaintext(self) -> None:
        self._seed_outbox(job_card="JC-DIAG-DEDUPE-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true",
                headers={
                    **self._headers(),
                    "Authorization": "Bearer token.secret.password",
                    "Cookie": "sid=secret-cookie",
                },
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            row = (
                session.query(LySecurityAuditLog)
                .filter(
                    LySecurityAuditLog.module == "workshop",
                    LySecurityAuditLog.action == "workshop:job_card_sync_worker",
                    LySecurityAuditLog.event_type == "AUTH_FORBIDDEN",
                )
                .order_by(LySecurityAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(row)
        self.assertTrue(row.dedupe_key)
        text = " ".join([row.dedupe_key or "", row.deny_reason or ""]).lower()
        for forbidden in ("authorization", "cookie", "token", "secret", "password"):
            self.assertNotIn(forbidden, text)

    def test_forbidden_diagnostics_does_not_lock_attempt_or_retry_outbox(self) -> None:
        outbox_id = self._seed_outbox(job_card="JC-DIAG-NO-MUTATE-001", item_code="ITEM-A", company="COMP-A")
        with self.SessionLocal() as session:
            before = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            before_snapshot = (
                before.status,
                int(before.attempts),
                before.locked_by,
                before.locked_at,
                before.next_retry_at,
            )

        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            after = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            after_snapshot = (
                after.status,
                int(after.attempts),
                after.locked_by,
                after.locked_at,
                after.next_retry_at,
            )
        self.assertEqual(before_snapshot, after_snapshot)

    def test_blocked_scope_outbox_is_excluded_from_forbidden_diagnostics(self) -> None:
        outbox_id = self._seed_outbox(job_card="JC-DIAG-BLOCKED-001", item_code="", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["blocked_scope_count"], 1)
        self.assertEqual(data["forbidden_diagnostic_count"], 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            denial_count = (
                session.query(YsWorkshopOutboxAccessDenial)
                .filter(YsWorkshopOutboxAccessDenial.outbox_id == outbox_id)
                .count()
            )
        self.assertEqual(outbox.status, "dead")
        self.assertEqual(denial_count, 0)

    def test_head_of_line_fix_still_processes_authorized_second_row(self) -> None:
        self._seed_outbox(job_card="JC-DIAG-HOL-FORBIDDEN-001", item_code="ITEM-A", company="COMP-A")
        self._seed_outbox(job_card="JC-DIAG-HOL-ALLOWED-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(sync_mock.call_count, 1)
        kwargs = sync_mock.call_args.kwargs if sync_mock.call_args else {}
        self.assertEqual(kwargs.get("job_card"), "JC-DIAG-HOL-ALLOWED-001")

    def test_diagnostic_limit_bounds_scan_size(self) -> None:
        os.environ["WORKSHOP_FORBIDDEN_DIAGNOSTIC_LIMIT"] = "1"
        self._seed_outbox(job_card="JC-DIAG-LIMIT-001", item_code="ITEM-A", company="COMP-A")
        self._seed_outbox(job_card="JC-DIAG-LIMIT-002", item_code="ITEM-A", company="COMP-A")
        self._seed_outbox(job_card="JC-DIAG-LIMIT-003", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["forbidden_diagnostic_count"], 1)
        with self.SessionLocal() as session:
            denial_count = session.query(YsWorkshopOutboxAccessDenial).count()
        self.assertEqual(denial_count, 1)


if __name__ == "__main__":
    unittest.main()
