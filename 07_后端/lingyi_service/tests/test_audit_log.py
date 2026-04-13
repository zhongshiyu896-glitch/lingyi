"""Operation audit coverage for internal worker dry-run path (TASK-003J)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timedelta
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
from app.core.exceptions import AuditWriteFailed
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopJobCardSyncLog
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.models.workshop import YsWorkshopOutboxAccessDenial
from app.models.workshop import YsWorkshopTicket
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.audit_service import AuditService
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.workshop_outbox_service import WorkshopOutboxService


class WorkshopDryRunAuditLogTest(unittest.TestCase):
    """Validate dry-run operation audit closure and data safety."""

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
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "true"
        os.environ["WORKSHOP_DRY_RUN_AUDIT_REQUIRED"] = "true"
        os.environ["WORKSHOP_ENABLE_FORBIDDEN_DIAGNOSTICS"] = "false"
        os.environ["WORKSHOP_OUTBOX_DENIAL_AUDIT_COOLDOWN_SECONDS"] = "21600"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"

        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
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

    def _latest_operation_audit(self) -> LyOperationAuditLog:
        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "workshop",
                    LyOperationAuditLog.action == "workshop:job_card_sync_worker",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(row)
        return row  # type: ignore[return-value]

    def test_dry_run_allowed_writes_operation_audit(self) -> None:
        self._seed_outbox(job_card="JC-DRY-AUDIT-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true&batch_size=10",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        row = self._latest_operation_audit()
        self.assertEqual(row.operator, "svc.worker")
        self.assertTrue(row.request_id)

    def test_dry_run_operation_audit_contains_safe_summary_fields(self) -> None:
        self._seed_outbox(job_card="JC-DRY-AUDIT-002", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true&batch_size=3&include_forbidden_diagnostics=false",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        row = self._latest_operation_audit()
        before_data = row.before_data or {}
        after_data = row.after_data or {}
        self.assertEqual(before_data.get("dry_run"), True)
        self.assertEqual(before_data.get("batch_size"), 3)
        self.assertEqual(before_data.get("include_forbidden_diagnostics"), False)
        self.assertEqual(before_data.get("forbidden_diagnostics_enabled"), False)
        self.assertEqual(after_data.get("dry_run"), True)
        self.assertEqual(after_data.get("forbidden_diagnostics_enabled"), False)
        self.assertEqual(after_data.get("would_process_count"), 1)
        self.assertEqual(after_data.get("processed_count"), 0)
        self.assertEqual(after_data.get("forbidden_diagnostic_count"), 0)

    def test_worker_audit_after_data_does_not_require_skipped_forbidden_for_business_judgement(self) -> None:
        self._seed_outbox(job_card="JC-DRY-AUDIT-002A", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true&batch_size=1",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 200)
        row = self._latest_operation_audit()
        after_data = row.after_data or {}
        # Canonical diagnostics field must always exist for audit judgement.
        self.assertIn("forbidden_diagnostic_count", after_data)
        canonical = int(after_data.get("forbidden_diagnostic_count", 0))
        compat = int(after_data.get("skipped_forbidden_count", canonical))
        self.assertEqual(canonical, compat)

    def test_dry_run_operation_audit_has_no_sensitive_plaintext(self) -> None:
        self._seed_outbox(job_card="JC-DRY-AUDIT-003", item_code="ITEM-A", company="COMP-A")
        sensitive_auth = "Bearer super-secret-token-003j"
        sensitive_cookie = "sid=super-secret-cookie-003j"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers={
                    **self._headers(),
                    "Authorization": sensitive_auth,
                    "Cookie": sensitive_cookie,
                },
            )
        self.assertEqual(response.status_code, 200)
        row = self._latest_operation_audit()
        text = json.dumps(
            {
                "before_data": row.before_data,
                "after_data": row.after_data,
                "operator": row.operator,
                "request_id": row.request_id,
            },
            ensure_ascii=False,
        ).lower()
        self.assertNotIn(sensitive_auth.lower(), text)
        self.assertNotIn(sensitive_cookie.lower(), text)

    def test_dry_run_audit_write_failure_returns_audit_write_failed(self) -> None:
        self._seed_outbox(job_card="JC-DRY-AUDIT-004", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ), patch.object(
            AuditService,
            "record_success",
            side_effect=AuditWriteFailed(),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ) as sync_mock:
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            count = session.query(LyOperationAuditLog).filter(
                LyOperationAuditLog.module == "workshop",
                LyOperationAuditLog.action == "workshop:job_card_sync_worker",
                LyOperationAuditLog.result == "success",
            ).count()
        self.assertEqual(count, 0)

    def test_dry_run_does_not_mutate_outbox_state_or_attempts(self) -> None:
        outbox_id = self._seed_outbox(job_card="JC-DRY-AUDIT-005", item_code="ITEM-A", company="COMP-A")
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
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 200)
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

    def test_dry_run_does_not_create_success_sync_log(self) -> None:
        self._seed_outbox(job_card="JC-DRY-AUDIT-006", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            success_count = (
                session.query(YsWorkshopJobCardSyncLog)
                .filter(YsWorkshopJobCardSyncLog.erpnext_status == "success")
                .count()
            )
        self.assertEqual(success_count, 0)

    def test_dry_run_does_not_call_erpnext_job_card_write(self) -> None:
        self._seed_outbox(job_card="JC-DRY-AUDIT-007", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ), patch.object(
            ERPNextJobCardAdapter,
            "update_job_card_completed_qty",
            return_value={"message": "ok"},
        ) as sync_mock:
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sync_mock.call_count, 0)

    def test_dry_run_with_forbidden_diagnostics_keeps_dedupe_cooldown(self) -> None:
        outbox_id = self._seed_outbox(job_card="JC-DRY-AUDIT-008", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            resp1 = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true&include_forbidden_diagnostics=true",
                headers=self._headers(),
            )
            resp2 = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true&include_forbidden_diagnostics=true",
                headers=self._headers(),
            )
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        with self.SessionLocal() as session:
            denial = (
                session.query(YsWorkshopOutboxAccessDenial)
                .filter(
                    YsWorkshopOutboxAccessDenial.outbox_id == outbox_id,
                    YsWorkshopOutboxAccessDenial.principal == "svc.worker",
                )
                .first()
            )
            security_count = (
                session.query(LySecurityAuditLog)
                .filter(
                    LySecurityAuditLog.module == "workshop",
                    LySecurityAuditLog.action == "workshop:job_card_sync_worker",
                    LySecurityAuditLog.event_type == "AUTH_FORBIDDEN",
                )
                .count()
            )
        self.assertIsNotNone(denial)
        self.assertEqual(int(denial.seen_count), 2)
        self.assertEqual(security_count, 1)

    def test_dry_run_empty_candidate_still_writes_operation_audit(self) -> None:
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-A"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 200)
        row = self._latest_operation_audit()
        after_data = row.after_data or {}
        self.assertEqual(after_data.get("dry_run"), True)
        self.assertEqual(after_data.get("would_process_count"), 0)


if __name__ == "__main__":
    unittest.main()
