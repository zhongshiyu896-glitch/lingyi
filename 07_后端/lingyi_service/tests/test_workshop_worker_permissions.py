"""Permission hardening tests for internal workshop worker API (TASK-003F)."""

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
from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.exceptions import PermissionSourceUnavailable
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.workshop import Base as WorkshopBase
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopJobCardSyncLog
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.models.workshop import YsWorkshopTicket
from app.repositories.workshop_job_card_sync_outbox_repository import WorkshopJobCardSyncOutboxRepository
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.workshop import get_db_session as workshop_db_dep
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.workshop_job_card_sync_worker import WorkshopSyncRunResult
from app.services.service_account_policy import ServiceAccountPolicyService
from app.services.workshop_outbox_service import WorkshopOutboxService


class WorkshopWorkerPermissionTest(unittest.TestCase):
    """Cover internal worker API auth, permission, and audit behavior."""

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
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "true"
        os.environ["WORKSHOP_DRY_RUN_AUDIT_REQUIRED"] = "true"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = ""
        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(YsWorkshopJobCardSyncLog).delete()
            session.query(YsWorkshopJobCardSyncOutbox).delete()
            session.query(YsWorkshopTicket).delete()
            session.commit()

    @staticmethod
    def _headers(user: str = "worker.user", role: str = "Workshop Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}

    def _seed_pending_outbox(self, *, job_card: str = "JC-WORKER-001") -> int:
        with self.SessionLocal() as session:
            ticket = YsWorkshopTicket(
                ticket_no=f"TICKET-{job_card}",
                ticket_key=f"KEY-{job_card}",
                job_card=job_card,
                work_order="WO-001",
                bom_id=None,
                item_code="ITEM-A",
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
                item_code="ITEM-A",
                company="COMP-A",
                local_completed_qty=Decimal("10"),
                source_type="ticket_register",
                source_ids=[int(ticket.id)],
                request_id="rid-seed",
                created_by="seed",
            )
            outbox.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.commit()
            return int(outbox.id)

    def _latest_security_audit(self) -> LySecurityAuditLog:
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
        self.assertIsNotNone(row)
        return row  # type: ignore[return-value]

    def test_internal_worker_requires_authentication(self) -> None:
        response = self.client.post("/api/workshop/internal/job-card-sync/run-once")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "AUTH_UNAUTHORIZED")

    def test_internal_worker_denies_workshop_manager(self) -> None:
        response = self.client.post(
            "/api/workshop/internal/job-card-sync/run-once",
            headers=self._headers(role="Workshop Manager"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:job_card_sync_worker")

    def test_internal_worker_denies_job_card_sync_only_permission(self) -> None:
        response = self.client.post(
            "/api/workshop/internal/job-card-sync/run-once",
            headers=self._headers(role="Workshop Sync Operator"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        self.assertEqual(row.action, "workshop:job_card_sync_worker")

    def test_internal_worker_denies_when_permission_source_unavailable(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once",
                headers=self._headers(user="svc.worker", role="LY Integration Service"),
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "PERMISSION_SOURCE_UNAVAILABLE")

    def test_internal_worker_disabled_in_production_without_flag(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "false"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="prod.user",
            roles=["System Manager"],
            is_service_account=False,
            source="test_override",
        )
        try:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "INTERNAL_API_DISABLED")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "INTERNAL_API_DISABLED")

    def test_internal_worker_service_account_can_process_outbox(self) -> None:
        self._seed_pending_outbox(job_card="JC-WORKER-SVC-001")
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"ITEM-A"},
                allowed_companies={"COMP-A"},
            ),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?batch_size=10",
                headers=self._headers(user="svc.worker", role="LY Integration Service"),
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertGreaterEqual(payload["data"]["processed_count"], 1)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).order_by(YsWorkshopJobCardSyncOutbox.id.desc()).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "succeeded")
            logs = session.query(YsWorkshopJobCardSyncLog).all()
            self.assertGreaterEqual(len(logs), 1)
            op_audit = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "workshop",
                    LyOperationAuditLog.action == "workshop:job_card_sync_worker",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(op_audit)
            self.assertIn("processed_count", (op_audit.after_data or {}))

    def test_internal_worker_denied_does_not_mutate_outbox_or_call_erpnext(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-WORKER-DENY-001")
        with self.SessionLocal() as session:
            before = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertIsNotNone(before)
            before_snapshot = (before.status, int(before.attempts), before.locked_by, before.locked_at)

        with patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once",
                headers=self._headers(role="Workshop Manager"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            after = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertIsNotNone(after)
            after_snapshot = (after.status, int(after.attempts), after.locked_by, after.locked_at)
            sync_log_count = session.query(YsWorkshopJobCardSyncLog).count()
        self.assertEqual(before_snapshot, after_snapshot)
        self.assertEqual(sync_log_count, 0)

    def test_internal_worker_denied_writes_security_audit_without_secrets(self) -> None:
        response = self.client.post(
            "/api/workshop/internal/job-card-sync/run-once",
            headers={
                **self._headers(role="Workshop Manager"),
                "Authorization": "Bearer very-secret-token-123",
                "Cookie": "sid=super-secret-cookie",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")
        text = " ".join(
            [
                row.deny_reason or "",
                row.request_path or "",
                row.request_method or "",
                row.user_agent or "",
            ]
        ).lower()
        for forbidden in ("authorization", "cookie", "token", "secret", "password"):
            self.assertNotIn(forbidden, text)

    def test_workshop_manager_cannot_call_dry_run(self) -> None:
        response = self.client.post(
            "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
            headers=self._headers(role="Workshop Manager"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "AUTH_FORBIDDEN")

    def test_production_dry_run_disabled_returns_disabled_before_permission_source_lookup(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.worker",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            with patch.object(
                ERPNextPermissionAdapter,
                "get_user_permissions",
                side_effect=PermissionSourceUnavailable(
                    message="timeout",
                    exception_type="TimeoutError",
                    exception_message="timeout",
                ),
            ) as permissions_mock:
                response = self.client.post(
                    "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                    headers=self._headers(user="svc.worker", role="LY Integration Service"),
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "WORKSHOP_DRY_RUN_DISABLED")
        self.assertEqual(permissions_mock.call_count, 0)
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "WORKSHOP_DRY_RUN_DISABLED")

    def test_production_dry_run_disabled_does_not_load_service_account_policy(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.worker",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            with patch.object(
                ServiceAccountPolicyService,
                "get_worker_policy",
                wraps=ServiceAccountPolicyService.get_worker_policy,
            ) as policy_mock:
                response = self.client.post(
                    "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                    headers=self._headers(user="svc.worker", role="LY Integration Service"),
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "WORKSHOP_DRY_RUN_DISABLED")
        self.assertEqual(policy_mock.call_count, 0)

    def test_production_dry_run_disabled_does_not_query_outbox(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-WORKER-DRY-DISABLED-001")
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.worker",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            with patch.object(
                ERPNextPermissionAdapter,
                "get_user_permissions",
                return_value=UserPermissionResult(
                    source_available=True,
                    unrestricted=False,
                    allowed_items={"ITEM-A"},
                    allowed_companies={"COMP-A"},
                ),
            ), patch.object(
                WorkshopJobCardSyncOutboxRepository,
                "list_due_for_service_account",
                wraps=WorkshopJobCardSyncOutboxRepository.list_due_for_service_account,
            ) as due_query_mock, patch.object(
                ERPNextJobCardAdapter,
                "update_job_card_completed_qty",
                return_value={"message": "ok"},
            ) as sync_mock:
                response = self.client.post(
                    "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                    headers=self._headers(user="svc.worker", role="LY Integration Service"),
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "WORKSHOP_DRY_RUN_DISABLED")
        self.assertEqual(due_query_mock.call_count, 0)
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "pending")
            op_count = session.query(LyOperationAuditLog).filter(
                LyOperationAuditLog.module == "workshop",
                LyOperationAuditLog.action == "workshop:job_card_sync_worker",
            ).count()
        self.assertEqual(op_count, 0)

    def test_production_dry_run_disabled_writes_security_audit_only(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.worker",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers=self._headers(user="svc.worker", role="LY Integration Service"),
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "WORKSHOP_DRY_RUN_DISABLED")
        with self.SessionLocal() as session:
            sec_count = session.query(LySecurityAuditLog).count()
            op_count = session.query(LyOperationAuditLog).filter(
                LyOperationAuditLog.module == "workshop",
                LyOperationAuditLog.action == "workshop:job_card_sync_worker",
            ).count()
        self.assertEqual(sec_count, 1)
        self.assertEqual(op_count, 0)

    def test_production_dry_run_disabled_does_not_write_operation_audit(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.worker",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                headers=self._headers(user="svc.worker", role="LY Integration Service"),
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "WORKSHOP_DRY_RUN_DISABLED")
        with self.SessionLocal() as session:
            op_count = session.query(LyOperationAuditLog).filter(
                LyOperationAuditLog.module == "workshop",
                LyOperationAuditLog.action == "workshop:job_card_sync_worker",
            ).count()
        self.assertEqual(op_count, 0)

    def test_dry_run_disabled_does_not_leak_permission_source_timeout(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.worker",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            with patch.object(
                ERPNextPermissionAdapter,
                "get_user_permissions",
                side_effect=PermissionSourceUnavailable(
                    message="permission source timeout",
                    exception_type="TimeoutError",
                    exception_message="timeout-secret-detail",
                ),
            ):
                response = self.client.post(
                    "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                    headers=self._headers(user="svc.worker", role="LY Integration Service"),
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        payload = response.json()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload["code"], "WORKSHOP_DRY_RUN_DISABLED")
        self.assertNotIn("timeout", payload.get("message", "").lower())
        row = self._latest_security_audit()
        self.assertNotIn("timeout", (row.deny_reason or "").lower())

    def test_unauthenticated_dry_run_still_returns_auth_unauthorized_before_disabled(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        response = self.client.post("/api/workshop/internal/job-card-sync/run-once?dry_run=true")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")

    def test_non_worker_permission_dry_run_still_returns_auth_forbidden_before_disabled(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="normal.manager",
            roles=["Workshop Manager"],
            is_service_account=False,
            source="test_override",
        )
        try:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?dry_run=true")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_non_service_account_dry_run_still_returns_auth_forbidden_before_disabled(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "false"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="no-trust-user",
            roles=["workshop:job_card_sync_worker"],
            is_service_account=False,
            source="test_override",
        )
        try:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?dry_run=true")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_dry_run_enabled_still_loads_permission_source_and_fails_closed_when_unavailable(self) -> None:
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"
        os.environ["WORKSHOP_ENABLE_WORKER_DRY_RUN"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.worker"
        app.dependency_overrides[get_current_user] = lambda: CurrentUser(
            username="svc.worker",
            roles=["LY Integration Service"],
            is_service_account=True,
            source="test_override",
        )
        try:
            with patch.object(
                ERPNextPermissionAdapter,
                "get_user_permissions",
                side_effect=PermissionSourceUnavailable(
                    message="timeout",
                    exception_type="TimeoutError",
                    exception_message="timeout",
                ),
            ) as permissions_mock:
                response = self.client.post(
                    "/api/workshop/internal/job-card-sync/run-once?dry_run=true",
                    headers=self._headers(user="svc.worker", role="LY Integration Service"),
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertGreaterEqual(permissions_mock.call_count, 1)

    def test_worker_response_skipped_forbidden_fields_are_deprecated_or_removed_in_openapi(self) -> None:
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        schema = None
        for component in payload.get("components", {}).get("schemas", {}).values():
            properties = component.get("properties", {})
            if "forbidden_diagnostic_count" in properties:
                schema = properties
                break

        self.assertIsNotNone(schema, msg="WorkshopJobCardSyncRunOnceData schema not found in OpenAPI components")
        schema = schema or {}

        for field_name in ("skipped_forbidden_count", "skipped_forbidden"):
            if field_name not in schema:
                continue
            self.assertTrue(schema[field_name].get("deprecated", False))
            description = (schema[field_name].get("description") or "").lower()
            self.assertIn("diagnostics", description)
            self.assertIn("不代表主处理跳过数", schema[field_name].get("description") or "")

    def test_worker_response_documents_skipped_forbidden_as_diagnostics_only_alias(self) -> None:
        doc = WorkshopSyncRunResult.skipped_forbidden.__doc__ or ""
        self.assertIn("Deprecated", doc)
        self.assertIn("diagnostics-only alias", doc)


if __name__ == "__main__":
    unittest.main()
