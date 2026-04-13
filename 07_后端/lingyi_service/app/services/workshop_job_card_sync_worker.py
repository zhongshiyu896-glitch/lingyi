"""Workshop Job Card sync worker based on outbox (TASK-003D)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import ROUND_HALF_UP
import hashlib
import json
import os
from typing import Any

from fastapi import Request
from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.config import workshop_denial_audit_cooldown_seconds
from app.core.config import workshop_enable_forbidden_diagnostics
from app.core.config import workshop_forbidden_diagnostic_limit
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN
from app.core.error_codes import ERPNEXT_SERVICE_UNAVAILABLE
from app.core.error_codes import SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED
from app.core.error_codes import WORKSHOP_JOB_CARD_SYNC_FAILED
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError
from app.core.logging import REDACTED_MESSAGE
from app.core.logging import sanitize_log_message
from app.core.permissions import WORKSHOP_JOB_CARD_SYNC_WORKER
from app.core.permissions import get_permission_source
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.models.workshop import YsWorkshopJobCardSyncLog
from app.models.workshop import YsWorkshopTicket
from app.repositories.workshop_outbox_access_denial_repository import WorkshopOutboxAccessDenialRepository
from app.repositories.workshop_job_card_sync_outbox_repository import WorkshopJobCardSyncOutboxRepository
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.service_account_policy import ServiceAccountResourcePolicy
from app.services.workshop_outbox_service import WorkshopOutboxService


@dataclass(frozen=True)
class WorkshopSyncRunResult:
    """Run-once worker summary."""

    dry_run: bool
    would_process: int
    processed: int
    succeeded: int
    failed: int
    forbidden_diagnostic: int
    blocked_scope: int
    dead: int

    @property
    def skipped_forbidden(self) -> int:
        """Deprecated diagnostics-only alias of forbidden_diagnostic."""
        return self.forbidden_diagnostic


class WorkshopJobCardSyncWorker:
    """Consume pending outbox rows and sync Job Card final qty to ERPNext."""

    def __init__(
        self,
        *,
        session: Session,
        erp_adapter: ERPNextJobCardAdapter,
        worker_id: str = "workshop-sync-worker",
    ):
        self.session = session
        self.erp_adapter = erp_adapter
        self.worker_id = worker_id
        self.service_account_id = os.getenv("LINGYI_ERPNEXT_SERVICE_ACCOUNT_ID", "erpnext-service")
        self.outbox = WorkshopOutboxService(session=session)
        self.repository = WorkshopJobCardSyncOutboxRepository(session=session)
        self.denial_repository = WorkshopOutboxAccessDenialRepository(session=session)

    def run_once(
        self,
        *,
        limit: int = 20,
        service_account_policy: ServiceAccountResourcePolicy,
        include_forbidden_diagnostics: bool = False,
        request_obj: Request | None = None,
        current_user: CurrentUser | None = None,
        audit_service: AuditService | None = None,
    ) -> WorkshopSyncRunResult:
        """Run one polling cycle for due outbox tasks."""
        blocked_scope = 0
        for row in self.repository.list_due_missing_scope():
            blocked_scope += 1
            with self.session.begin_nested():
                self.outbox.mark_scope_required_dead(
                    row=row,
                    error_code=SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED,
                    error_message="同步任务缺少必要资源范围（company/item_code）",
                )
                self._record_denied_outbox(
                    row=row,
                    deny_code=SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED,
                    request_obj=request_obj,
                    current_user=current_user,
                    audit_service=audit_service,
                )

        forbidden_diagnostic = 0
        diagnostics_enabled = include_forbidden_diagnostics or workshop_enable_forbidden_diagnostics()
        if diagnostics_enabled:
            forbidden_diagnostic = self._run_forbidden_diagnostics(
                service_account_policy=service_account_policy,
                request_obj=request_obj,
                current_user=current_user,
                audit_service=audit_service,
            )

        due_rows = self.repository.list_due_for_service_account(
            policy=service_account_policy,
            limit=limit,
        )
        rows = self.outbox.claim_by_ids(
            row_ids=[int(row.id) for row in due_rows],
            worker_id=self.worker_id,
        )

        processed = 0
        succeeded = 0
        failed = 0
        dead = 0

        for row in rows:
            processed += 1
            with self.session.begin_nested():
                local_qty = self._calc_local_completed_qty(job_card=row.job_card)
                try:
                    response = self.erp_adapter.update_job_card_completed_qty(
                        job_card=row.job_card,
                        completed_qty=local_qty,
                        request_id=row.request_id,
                    )
                    attempt_no = self.outbox.mark_succeeded(row=row, local_completed_qty=local_qty)
                    self._mark_ticket_sync_status(
                        job_card=row.job_card,
                        sync_status="synced",
                        error_code=None,
                        error_message=None,
                    )
                    self._append_sync_log(
                        outbox_id=int(row.id),
                        attempt_no=attempt_no,
                        action="workshop:job_card_sync",
                        job_card=row.job_card,
                        sync_type=row.source_type,
                        local_completed_qty=local_qty,
                        erpnext_status="success",
                        erpnext_response=self._safe_sync_response(response),
                        error_code=None,
                        error_message=None,
                        request_id=row.request_id,
                    )
                    self._record_success_audit(
                        row=row,
                        local_completed_qty=local_qty,
                        request_obj=request_obj,
                        current_user=current_user,
                        audit_service=audit_service,
                    )
                    succeeded += 1
                except ERPNextServiceAccountForbiddenError as exc:
                    error_code = ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN
                    error_message = self._sanitize_error(exc.message)
                    attempt_no = self.outbox.mark_failed(row=row, error_code=error_code, error_message=error_message)
                    self._mark_ticket_sync_status(
                        job_card=row.job_card,
                        sync_status="failed",
                        error_code=error_code,
                        error_message=error_message,
                    )
                    self._append_sync_log(
                        outbox_id=int(row.id),
                        attempt_no=attempt_no,
                        action="workshop:job_card_sync",
                        job_card=row.job_card,
                        sync_type=row.source_type,
                        local_completed_qty=local_qty,
                        erpnext_status="failed",
                        erpnext_response=None,
                        error_code=error_code,
                        error_message=error_message,
                        request_id=row.request_id,
                    )
                    if row.status == WorkshopOutboxService.STATUS_DEAD:
                        dead += 1
                    else:
                        failed += 1
                except ERPNextServiceUnavailableError as exc:
                    lowered = (exc.message or "").lower()
                    error_code = ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN if ("403" in lowered or "forbidden" in lowered) else ERPNEXT_SERVICE_UNAVAILABLE
                    error_message = self._sanitize_error(exc.message)
                    attempt_no = self.outbox.mark_failed(row=row, error_code=error_code, error_message=error_message)
                    self._mark_ticket_sync_status(
                        job_card=row.job_card,
                        sync_status="failed",
                        error_code=error_code,
                        error_message=error_message,
                    )
                    self._append_sync_log(
                        outbox_id=int(row.id),
                        attempt_no=attempt_no,
                        action="workshop:job_card_sync",
                        job_card=row.job_card,
                        sync_type=row.source_type,
                        local_completed_qty=local_qty,
                        erpnext_status="failed",
                        erpnext_response=None,
                        error_code=error_code,
                        error_message=error_message,
                        request_id=row.request_id,
                    )
                    if row.status == WorkshopOutboxService.STATUS_DEAD:
                        dead += 1
                    else:
                        failed += 1
                except Exception:
                    error_code = WORKSHOP_JOB_CARD_SYNC_FAILED
                    error_message = REDACTED_MESSAGE
                    attempt_no = self.outbox.mark_failed(row=row, error_code=error_code, error_message=error_message)
                    self._mark_ticket_sync_status(
                        job_card=row.job_card,
                        sync_status="failed",
                        error_code=error_code,
                        error_message=error_message,
                    )
                    self._append_sync_log(
                        outbox_id=int(row.id),
                        attempt_no=attempt_no,
                        action="workshop:job_card_sync",
                        job_card=row.job_card,
                        sync_type=row.source_type,
                        local_completed_qty=local_qty,
                        erpnext_status="failed",
                        erpnext_response=None,
                        error_code=error_code,
                        error_message=error_message,
                        request_id=row.request_id,
                    )
                    if row.status == WorkshopOutboxService.STATUS_DEAD:
                        dead += 1
                    else:
                        failed += 1

        return WorkshopSyncRunResult(
            dry_run=False,
            would_process=processed,
            processed=processed,
            succeeded=succeeded,
            failed=failed,
            forbidden_diagnostic=forbidden_diagnostic,
            blocked_scope=blocked_scope,
            dead=dead,
        )

    def preview_once(
        self,
        *,
        limit: int = 20,
        service_account_policy: ServiceAccountResourcePolicy,
        include_forbidden_diagnostics: bool = False,
        request_obj: Request | None = None,
        current_user: CurrentUser | None = None,
        audit_service: AuditService | None = None,
    ) -> WorkshopSyncRunResult:
        """Read-only worker preview for dry-run path.

        Guarantees:
        - no outbox lock/status mutation;
        - no attempts/retry updates;
        - no ERPNext calls;
        - no sync-log success writes.
        """
        blocked_scope = self.repository.count_due_missing_scope()
        due_rows = self.repository.list_due_for_service_account(
            policy=service_account_policy,
            limit=limit,
        )
        would_process = len(due_rows)

        forbidden_diagnostic = 0
        diagnostics_enabled = include_forbidden_diagnostics or workshop_enable_forbidden_diagnostics()
        if diagnostics_enabled:
            forbidden_diagnostic = self._run_forbidden_diagnostics(
                service_account_policy=service_account_policy,
                request_obj=request_obj,
                current_user=current_user,
                audit_service=audit_service,
            )

        return WorkshopSyncRunResult(
            dry_run=True,
            would_process=would_process,
            processed=0,
            succeeded=0,
            failed=0,
            forbidden_diagnostic=forbidden_diagnostic,
            blocked_scope=blocked_scope,
            dead=0,
        )

    def _run_forbidden_diagnostics(
        self,
        *,
        service_account_policy: ServiceAccountResourcePolicy,
        request_obj: Request | None,
        current_user: CurrentUser | None,
        audit_service: AuditService | None,
    ) -> int:
        diagnostic_limit = workshop_forbidden_diagnostic_limit()
        cooldown_seconds = workshop_denial_audit_cooldown_seconds()
        rows = self.repository.list_due_forbidden_for_service_account(
            policy=service_account_policy,
            limit=diagnostic_limit,
        )
        diagnostic_count = 0
        for row in rows:
            diagnostic_count += 1
            scope_hash = service_account_policy.scope_hash_for_resource(
                company=row.company,
                item_code=row.item_code,
            )
            upsert = self.denial_repository.upsert_denial(
                outbox_id=int(row.id),
                principal=service_account_policy.username,
                reason_code=AUTH_FORBIDDEN,
                scope_hash=scope_hash,
                cooldown_seconds=cooldown_seconds,
            )
            if not upsert.should_write_audit:
                continue
            dedupe_key = self._build_denial_dedupe_key(
                principal=service_account_policy.username,
                outbox_id=int(row.id),
                reason_code=AUTH_FORBIDDEN,
                scope_hash=scope_hash,
            )
            self._record_denied_outbox(
                row=row,
                deny_code=AUTH_FORBIDDEN,
                request_obj=request_obj,
                current_user=current_user,
                audit_service=audit_service,
                dedupe_key=dedupe_key,
            )
        return diagnostic_count

    def _record_denied_outbox(
        self,
        *,
        row: YsWorkshopJobCardSyncOutbox,
        deny_code: str,
        request_obj: Request | None,
        current_user: CurrentUser | None,
        audit_service: AuditService | None,
        dedupe_key: str | None = None,
    ) -> None:
        if not request_obj or not current_user or not audit_service:
            return

        if deny_code == SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED:
            deny_reason = "同步任务缺少必要资源范围（company/item_code）"
        else:
            deny_reason = "服务账号无资源权限处理该同步任务"
        scope_hint = f"{row.company or '-'}:{row.item_code or '-'}"
        audit_service.record_security_audit(
            event_type=deny_code,
            module="workshop",
            action=WORKSHOP_JOB_CARD_SYNC_WORKER,
            resource_type="JobCard",
            resource_id=row.id,
            resource_no=row.job_card or scope_hint,
            user=current_user,
            deny_reason=f"{deny_reason} outbox_id={row.id} scope={scope_hint}",
            permission_source=get_permission_source(),
            request_obj=request_obj,
            dedupe_key=dedupe_key,
        )

    def _record_success_audit(
        self,
        *,
        row: YsWorkshopJobCardSyncOutbox,
        local_completed_qty: Decimal,
        request_obj: Request | None,
        current_user: CurrentUser | None,
        audit_service: AuditService | None,
    ) -> None:
        if not request_obj or not current_user or not audit_service:
            return
        context = AuditContext.from_request(request_obj)
        before_data = {
            "outbox_id": int(row.id),
            "job_card": row.job_card,
            "item_code": row.item_code,
            "company": row.company,
            "request_id": row.request_id,
            "source_type": row.source_type,
        }
        after_data = {
            "outbox_id": int(row.id),
            "job_card": row.job_card,
            "item_code": row.item_code,
            "company": row.company,
            "request_id": row.request_id,
            "local_completed_qty": str(self._round(local_completed_qty)),
            "status": "succeeded",
        }
        audit_service.record_success(
            module="workshop",
            action=WORKSHOP_JOB_CARD_SYNC_WORKER,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="job_card_sync_outbox",
            resource_id=int(row.id),
            resource_no=row.job_card,
            before_data=before_data,
            after_data=after_data,
            context=context,
        )

    def _calc_local_completed_qty(self, *, job_card: str) -> Decimal:
        try:
            register_qty = (
                self.session.query(func.coalesce(func.sum(YsWorkshopTicket.qty), 0))
                .filter(
                    and_(
                        YsWorkshopTicket.job_card == job_card,
                        YsWorkshopTicket.operation_type == "register",
                    )
                )
                .scalar()
                or 0
            )
            reversal_qty = (
                self.session.query(func.coalesce(func.sum(YsWorkshopTicket.qty), 0))
                .filter(
                    and_(
                        YsWorkshopTicket.job_card == job_card,
                        YsWorkshopTicket.operation_type == "reversal",
                    )
                )
                .scalar()
                or 0
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        qty = Decimal(register_qty) - Decimal(reversal_qty)
        return self._round(qty)

    def _mark_ticket_sync_status(
        self,
        *,
        job_card: str,
        sync_status: str,
        error_code: str | None,
        error_message: str | None,
    ) -> None:
        try:
            self.session.query(YsWorkshopTicket).filter(YsWorkshopTicket.job_card == job_card).update(
                {
                    "sync_status": sync_status,
                    "sync_error_code": error_code,
                    "sync_error_message": (error_message or "")[:255] or None,
                    "updated_at": datetime.utcnow(),
                },
                synchronize_session=False,
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def _append_sync_log(
        self,
        *,
        outbox_id: int,
        attempt_no: int,
        action: str,
        job_card: str,
        sync_type: str,
        local_completed_qty: Decimal,
        erpnext_status: str,
        erpnext_response: dict[str, Any] | None,
        error_code: str | None,
        error_message: str | None,
        request_id: str,
    ) -> None:
        response_payload = dict(erpnext_response or {})
        response_payload["service_account_id"] = self.service_account_id
        response_payload["action"] = action
        response_payload["outbox_id"] = outbox_id
        row = YsWorkshopJobCardSyncLog(
            outbox_id=outbox_id,
            attempt_no=attempt_no,
            job_card=job_card,
            sync_type=sync_type,
            local_completed_qty=self._round(local_completed_qty),
            erpnext_status=erpnext_status,
            erpnext_response=response_payload,
            error_code=error_code,
            error_message=(error_message or "")[:255] or None,
            request_id=request_id,
        )
        try:
            self.session.add(row)
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    @staticmethod
    def _safe_sync_response(payload: dict[str, Any] | None) -> dict[str, Any] | None:
        if not payload or not isinstance(payload, dict):
            return None
        safe: dict[str, Any] = {}
        for key in ["message", "status", "data", "exc_type"]:
            if key in payload:
                safe[key] = payload.get(key)
        return safe or None

    @staticmethod
    def _sanitize_error(message: str | None) -> str:
        sanitized = sanitize_log_message(message or "")
        return (sanitized or REDACTED_MESSAGE)[:255]

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _build_denial_dedupe_key(
        *,
        principal: str,
        outbox_id: int,
        reason_code: str,
        scope_hash: str,
    ) -> str:
        payload = {
            "principal": principal,
            "outbox_id": int(outbox_id),
            "reason_code": reason_code,
            "scope_hash": scope_hash,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
