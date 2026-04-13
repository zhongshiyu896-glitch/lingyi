"""Service-account minimal resource policy tests for workshop sync worker (TASK-003G)."""

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
from app.services.workshop_outbox_service import WorkshopOutboxService


class ServiceAccountPolicyTest(unittest.TestCase):
    """Validate worker service-account resource scope hardening."""

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

        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyOperationAuditLog).delete()
            session.query(YsWorkshopJobCardSyncLog).delete()
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

    def _seed_pending_outbox(
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

    def _latest_security_audit(self) -> LySecurityAuditLog:
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(row)
            return row  # type: ignore[return-value]

    def test_service_account_policy_has_no_implicit_global_scope(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-GLOBAL-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items=set(), companies=set(), unrestricted=True),
        ), patch.object(
            WorkshopJobCardSyncOutboxRepository,
            "list_due_for_service_account",
            wraps=WorkshopJobCardSyncOutboxRepository.list_due_for_service_account,
        ) as due_query_mock, patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?batch_size=10",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "SERVICE_ACCOUNT_RESOURCE_FORBIDDEN")
        self.assertEqual(sync_mock.call_count, 0)
        self.assertEqual(due_query_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertIsNotNone(outbox)
            self.assertEqual(outbox.status, "pending")

    def test_service_account_without_company_permission_cannot_process_outbox(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-NO-COMP-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies=set()),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "SERVICE_ACCOUNT_RESOURCE_FORBIDDEN")
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "pending")

    def test_service_account_without_item_permission_cannot_process_outbox(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-NO-ITEM-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items=set(), companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "SERVICE_ACCOUNT_RESOURCE_FORBIDDEN")
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "pending")

    def test_service_account_with_company_a_item_b_skips_company_a_item_a(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-SKIP-ITEM-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["forbidden_diagnostic_count"], 0)
        self.assertEqual(payload["data"]["skipped_forbidden_count"], 0)
        self.assertEqual(payload["data"]["succeeded_count"], 0)
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "pending")

    def test_service_account_with_company_a_item_b_skips_company_b_item_b(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-SKIP-COMP-001", item_code="ITEM-B", company="COMP-B")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["forbidden_diagnostic_count"], 0)
        self.assertEqual(payload["data"]["skipped_forbidden_count"], 0)
        self.assertEqual(payload["data"]["succeeded_count"], 0)
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "pending")

    def test_service_account_with_company_a_item_b_processes_matching_outbox(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-PASS-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertGreaterEqual(payload["data"]["processed_count"], 1)
        self.assertGreaterEqual(payload["data"]["succeeded_count"], 1)
        self.assertEqual(payload["data"]["skipped_forbidden_count"], 0)
        self.assertGreaterEqual(sync_mock.call_count, 1)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "succeeded")

    def test_service_account_permission_source_unavailable_fails_closed(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-PSU-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ), patch.object(
            WorkshopJobCardSyncOutboxRepository,
            "list_due_for_service_account",
            wraps=WorkshopJobCardSyncOutboxRepository.list_due_for_service_account,
        ) as due_query_mock, patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertEqual(sync_mock.call_count, 0)
        self.assertEqual(due_query_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "pending")

    def test_outbox_missing_company_or_item_is_not_synced_to_erpnext(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-MISSING-SCOPE-001", item_code="", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["blocked_scope_count"], 1)
        self.assertEqual(payload["data"]["processed_count"], 0)
        self.assertEqual(sync_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "dead")
            self.assertEqual(outbox.last_error_code, "SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED")
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED")

    def test_missing_scope_outbox_is_moved_out_of_due_pending_queue(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-MISSING-SCOPE-QUEUE-001", item_code="", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["blocked_scope_count"], 1)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "dead")
            self.assertEqual(outbox.last_error_code, "SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED")

    def test_missing_scope_outbox_writes_security_audit(self) -> None:
        self._seed_pending_outbox(job_card="JC-SVC-MISSING-SCOPE-AUDIT-001", item_code="", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())
        self.assertEqual(response.status_code, 200)
        row = self._latest_security_audit()
        self.assertEqual(row.event_type, "SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED")

    def test_resource_forbidden_outbox_does_not_create_success_sync_log(self) -> None:
        self._seed_pending_outbox(job_card="JC-SVC-NO-LOG-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            success_count = (
                session.query(YsWorkshopJobCardSyncLog)
                .filter(YsWorkshopJobCardSyncLog.erpnext_status == "success")
                .count()
            )
        self.assertEqual(success_count, 0)

    def test_service_account_resource_denial_writes_sanitized_security_audit(self) -> None:
        self._seed_pending_outbox(job_card="JC-SVC-AUDIT-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ):
            response = self.client.post(
                "/api/workshop/internal/job-card-sync/run-once?include_forbidden_diagnostics=true",
                headers={
                    **self._headers(),
                    "Authorization": "Bearer very-secret-token",
                    "Cookie": "sid=super-secret-cookie",
                },
            )

        self.assertEqual(response.status_code, 200)
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

    def test_successful_service_account_sync_writes_operation_audit_with_resource_scope(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-OP-AUDIT-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            op_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "workshop",
                    LyOperationAuditLog.action == "workshop:job_card_sync_worker",
                    LyOperationAuditLog.result == "success",
                    LyOperationAuditLog.resource_type == "job_card_sync_outbox",
                    LyOperationAuditLog.resource_id == outbox_id,
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(op_row)
            before_data = op_row.before_data or {}
            after_data = op_row.after_data or {}
            self.assertEqual(before_data.get("outbox_id"), outbox_id)
            self.assertEqual(before_data.get("job_card"), "JC-SVC-OP-AUDIT-001")
            self.assertEqual(before_data.get("item_code"), "ITEM-B")
            self.assertEqual(before_data.get("company"), "COMP-A")
            self.assertTrue(before_data.get("request_id"))
            self.assertEqual(after_data.get("outbox_id"), outbox_id)
            self.assertEqual(after_data.get("status"), "succeeded")

    def test_no_hardcoded_service_account_all_resource_policy_in_production(self) -> None:
        old_env = {
            "APP_ENV": os.environ.get("APP_ENV"),
            "ENABLE_INTERNAL_WORKER_API": os.environ.get("ENABLE_INTERNAL_WORKER_API"),
        }
        os.environ["APP_ENV"] = "production"
        os.environ["ENABLE_INTERNAL_WORKER_API"] = "true"

        outbox_allowed = self._seed_pending_outbox(job_card="JC-SVC-PROD-ALLOW-001", item_code="ITEM-B", company="COMP-A")
        outbox_denied = self._seed_pending_outbox(job_card="JC-SVC-PROD-DENY-001", item_code="ITEM-A", company="COMP-A")

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
                return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
            ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}):
                response = self.client.post("/api/workshop/internal/job-card-sync/run-once")
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            if old_env["APP_ENV"] is None:
                os.environ.pop("APP_ENV", None)
            else:
                os.environ["APP_ENV"] = old_env["APP_ENV"]
            if old_env["ENABLE_INTERNAL_WORKER_API"] is None:
                os.environ.pop("ENABLE_INTERNAL_WORKER_API", None)
            else:
                os.environ["ENABLE_INTERNAL_WORKER_API"] = old_env["ENABLE_INTERNAL_WORKER_API"]

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["succeeded_count"], 1)
        self.assertEqual(payload["data"]["forbidden_diagnostic_count"], 0)
        self.assertEqual(payload["data"]["skipped_forbidden_count"], 0)

        with self.SessionLocal() as session:
            allowed_row = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_allowed).first()
            denied_row = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_denied).first()
            self.assertEqual(allowed_row.status, "succeeded")
            self.assertEqual(denied_row.status, "pending")

    def test_worker_limit_applies_after_service_account_scope_filter(self) -> None:
        forbidden_id = self._seed_pending_outbox(job_card="JC-SVC-LIMIT-FORBIDDEN-001", item_code="ITEM-A", company="COMP-A")
        allowed_id = self._seed_pending_outbox(job_card="JC-SVC-LIMIT-ALLOWED-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["processed_count"], 1)
        self.assertEqual(data["succeeded_count"], 1)
        self.assertEqual(data["forbidden_diagnostic_count"], 0)
        self.assertEqual(data["skipped_forbidden_count"], 0)
        self.assertGreaterEqual(sync_mock.call_count, 1)
        with self.SessionLocal() as session:
            forbidden = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == forbidden_id).first()
            allowed = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == allowed_id).first()
            self.assertEqual(forbidden.status, "pending")
            self.assertEqual(allowed.status, "succeeded")

    def test_forbidden_head_row_does_not_block_authorized_second_row_with_limit_one(self) -> None:
        self._seed_pending_outbox(job_card="JC-SVC-HEAD-FORBIDDEN-001", item_code="ITEM-A", company="COMP-A")
        self._seed_pending_outbox(job_card="JC-SVC-HEAD-ALLOWED-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(sync_mock.call_count, 1)
        kwargs = sync_mock.call_args.kwargs if sync_mock.call_args else {}
        self.assertEqual(kwargs.get("job_card"), "JC-SVC-HEAD-ALLOWED-001")

    def test_repeated_worker_runs_do_not_revisit_same_forbidden_head_for_same_account(self) -> None:
        forbidden_id = self._seed_pending_outbox(job_card="JC-SVC-RUNS-FORBIDDEN-001", item_code="ITEM-A", company="COMP-A")
        allowed_1 = self._seed_pending_outbox(job_card="JC-SVC-RUNS-ALLOWED-001", item_code="ITEM-B", company="COMP-A")
        allowed_2 = self._seed_pending_outbox(job_card="JC-SVC-RUNS-ALLOWED-002", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            resp1 = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())
            resp2 = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(sync_mock.call_count, 2)
        with self.SessionLocal() as session:
            forbidden = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == forbidden_id).first()
            row1 = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == allowed_1).first()
            row2 = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == allowed_2).first()
            self.assertEqual(forbidden.status, "pending")
            self.assertEqual(row1.status, "succeeded")
            self.assertEqual(row2.status, "succeeded")

    def test_forbidden_outbox_is_not_locked_or_attempted_by_unauthorized_service_account(self) -> None:
        forbidden_id = self._seed_pending_outbox(job_card="JC-SVC-NO-LOCK-001", item_code="ITEM-A", company="COMP-A")
        with self.SessionLocal() as session:
            before = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == forbidden_id).first()
            before_snapshot = (before.status, int(before.attempts), before.locked_by, before.locked_at)

        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}):
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        with self.SessionLocal() as session:
            after = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == forbidden_id).first()
            after_snapshot = (after.status, int(after.attempts), after.locked_by, after.locked_at)
        self.assertEqual(before_snapshot, after_snapshot)

    def test_authorized_outbox_after_forbidden_rows_calls_erpnext(self) -> None:
        self._seed_pending_outbox(job_card="JC-SVC-CALL-FORBIDDEN-001", item_code="ITEM-A", company="COMP-A")
        self._seed_pending_outbox(job_card="JC-SVC-CALL-ALLOWED-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items={"ITEM-B"}, companies={"COMP-A"}),
        ), patch.object(ERPNextJobCardAdapter, "update_job_card_completed_qty", return_value={"message": "ok"}) as sync_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once?batch_size=1", headers=self._headers())

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(sync_mock.call_count, 1)

    def test_empty_service_account_scope_does_not_query_all_outbox(self) -> None:
        self._seed_pending_outbox(job_card="JC-SVC-EMPTY-SCOPE-001", item_code="ITEM-A", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=self._perm(items=set(), companies=set()),
        ), patch.object(
            WorkshopJobCardSyncOutboxRepository,
            "list_due_for_service_account",
            wraps=WorkshopJobCardSyncOutboxRepository.list_due_for_service_account,
        ) as due_query_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "SERVICE_ACCOUNT_RESOURCE_FORBIDDEN")
        self.assertEqual(due_query_mock.call_count, 0)

    def test_permission_source_unavailable_does_not_lock_or_query_candidates(self) -> None:
        outbox_id = self._seed_pending_outbox(job_card="JC-SVC-PSU-NO-QUERY-001", item_code="ITEM-B", company="COMP-A")
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            side_effect=PermissionSourceUnavailable(
                message="timeout",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ), patch.object(
            WorkshopJobCardSyncOutboxRepository,
            "list_due_for_service_account",
            wraps=WorkshopJobCardSyncOutboxRepository.list_due_for_service_account,
        ) as due_query_mock:
            response = self.client.post("/api/workshop/internal/job-card-sync/run-once", headers=self._headers())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertEqual(due_query_mock.call_count, 0)
        with self.SessionLocal() as session:
            outbox = session.query(YsWorkshopJobCardSyncOutbox).filter(YsWorkshopJobCardSyncOutbox.id == outbox_id).first()
            self.assertEqual(outbox.status, "pending")


if __name__ == "__main__":
    unittest.main()
