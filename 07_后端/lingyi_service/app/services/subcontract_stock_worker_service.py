"""Internal worker for subcontract Stock Entry outbox (TASK-002D/TASK-002E)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from app.core.error_codes import ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN
from app.core.error_codes import ERPNEXT_SERVICE_UNAVAILABLE
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_CANCELLED
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_CREATE_FAILED
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_STATUS_INVALID
from app.core.error_codes import ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_CONFLICT
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError
from app.core.logging import REDACTED_MESSAGE
from app.core.logging import sanitize_log_message
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStockOutbox
from app.models.subcontract import LySubcontractStockSyncLog
from app.services.erpnext_stock_entry_service import ERPNextStockEntryService
from app.services.subcontract_stock_outbox_service import SubcontractStockOutboxService
from app.services.subcontract_stock_outbox_service import SubcontractWorkerScope


@dataclass(frozen=True)
class SubcontractStockWorkerRunResult:
    """Run-once summary for subcontract stock worker."""

    dry_run: bool
    batch_size: int
    would_process_count: int
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int


@dataclass(frozen=True)
class _ClaimedOutboxSnapshot:
    outbox_id: int
    subcontract_id: int
    company: str | None
    stock_action: str
    request_id: str
    event_key: str
    payload_json: dict[str, Any]


class SubcontractStockWorkerService:
    """Consume subcontract outbox and sync ERPNext Stock Entry."""

    def __init__(self, *, session, erp_service: ERPNextStockEntryService, worker_id: str = "subcontract-stock-worker"):
        self.session = session
        self.erp_service = erp_service
        self.worker_id = worker_id
        self.outbox_service = SubcontractStockOutboxService(session=session)

    @property
    def _is_sqlite(self) -> bool:
        bind = self.session.get_bind()
        return bool(bind and bind.dialect.name == "sqlite")

    def _next_sync_log_id(self) -> int:
        try:
            current = self.session.query(LySubcontractStockSyncLog.id).order_by(LySubcontractStockSyncLog.id.desc()).first()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return int(current[0]) + 1 if current and current[0] is not None else 1

    def preview_once(
        self,
        *,
        limit: int,
        scope: SubcontractWorkerScope,
        stock_action: str | None = None,
    ) -> SubcontractStockWorkerRunResult:
        rows = self.outbox_service.list_due_for_scope(scope=scope, limit=limit, stock_action=stock_action)
        return SubcontractStockWorkerRunResult(
            dry_run=True,
            batch_size=limit,
            would_process_count=len(rows),
            processed_count=0,
            succeeded_count=0,
            failed_count=0,
            dead_count=0,
        )

    def run_once(
        self,
        *,
        limit: int,
        scope: SubcontractWorkerScope,
        stock_action: str | None = None,
    ) -> SubcontractStockWorkerRunResult:
        due_rows = self.outbox_service.list_due_for_scope(scope=scope, limit=limit, stock_action=stock_action)
        claimed_rows = self.outbox_service.claim_by_ids(
            row_ids=[int(row.id) for row in due_rows],
            worker_id=self.worker_id,
            stock_action=stock_action,
        )
        claimed_snapshots = [self._snapshot_claimed_row(row) for row in claimed_rows]
        self._commit_phase()

        processed = 0
        succeeded = 0
        failed = 0
        dead = 0

        for snapshot in claimed_snapshots:
            processed += 1
            try:
                stock_entry_name = self._sync_one(snapshot=snapshot)
                wrote = self._finalize_success(snapshot=snapshot, stock_entry_name=stock_entry_name)
                if wrote:
                    succeeded += 1
            except DatabaseWriteFailed:
                raise
            except ERPNextServiceAccountForbiddenError as exc:
                wrote, is_dead = self._finalize_failure(
                    snapshot=snapshot,
                    error_code=ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN,
                    error_message=self._safe_error(exc.message),
                )
                if wrote:
                    if is_dead:
                        dead += 1
                    else:
                        failed += 1
            except ERPNextServiceUnavailableError as exc:
                wrote, is_dead = self._finalize_failure(
                    snapshot=snapshot,
                    error_code=ERPNEXT_SERVICE_UNAVAILABLE,
                    error_message=self._safe_error(exc.message),
                )
                if wrote:
                    if is_dead:
                        dead += 1
                    else:
                        failed += 1
            except BusinessException as exc:
                error_code = exc.code
                if error_code not in {
                    ERPNEXT_STOCK_ENTRY_CREATE_FAILED,
                    ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED,
                    ERPNEXT_STOCK_ENTRY_CANCELLED,
                    ERPNEXT_STOCK_ENTRY_STATUS_INVALID,
                    ERPNEXT_STOCK_ENTRY_DUPLICATE_EVENT_KEY,
                }:
                    error_code = SUBCONTRACT_STOCK_OUTBOX_CONFLICT
                wrote, is_dead = self._finalize_failure(
                    snapshot=snapshot,
                    error_code=error_code,
                    error_message=self._safe_error(exc.message),
                )
                if wrote:
                    if is_dead:
                        dead += 1
                    else:
                        failed += 1
            except Exception:
                wrote, is_dead = self._finalize_failure(
                    snapshot=snapshot,
                    error_code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT,
                    error_message=REDACTED_MESSAGE,
                )
                if wrote:
                    if is_dead:
                        dead += 1
                    else:
                        failed += 1

        return SubcontractStockWorkerRunResult(
            dry_run=False,
            batch_size=limit,
            would_process_count=processed,
            processed_count=processed,
            succeeded_count=succeeded,
            failed_count=failed,
            dead_count=dead,
        )

    @staticmethod
    def _snapshot_claimed_row(row: LySubcontractStockOutbox) -> _ClaimedOutboxSnapshot:
        payload_json = row.payload_json if isinstance(row.payload_json, dict) else {}
        return _ClaimedOutboxSnapshot(
            outbox_id=int(row.id),
            subcontract_id=int(row.subcontract_id),
            company=row.company,
            stock_action=str(row.stock_action or SubcontractStockOutboxService.STOCK_ACTION_ISSUE),
            request_id=str(row.request_id or ""),
            event_key=str(row.event_key or ""),
            payload_json=dict(payload_json),
        )

    def _sync_one(self, *, snapshot: _ClaimedOutboxSnapshot) -> str:
        event_key = snapshot.event_key.strip()
        payload_json = snapshot.payload_json if isinstance(snapshot.payload_json, dict) else None
        if not event_key or payload_json is None:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="库存同步任务载荷缺失")

        existing = self.erp_service.find_by_event_key(event_key=event_key)
        if existing:
            if isinstance(existing, str):
                return existing
            if int(existing.docstatus) == 1:
                return existing.name
            if int(existing.docstatus) == 0:
                self.erp_service.submit_stock_entry(stock_entry_name=existing.name)
                confirmed = self.erp_service.find_by_event_key(event_key=event_key)
                if not confirmed:
                    raise BusinessException(
                        code=ERPNEXT_STOCK_ENTRY_SUBMIT_FAILED,
                        message="ERPNext Stock Entry 提交后未找到单据",
                    )
                if isinstance(confirmed, str):
                    return confirmed
                if int(confirmed.docstatus) != 1:
                    raise BusinessException(
                        code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID,
                        message="ERPNext Stock Entry 提交后状态异常",
                    )
                return confirmed.name
            if int(existing.docstatus) == 2:
                raise BusinessException(
                    code=ERPNEXT_STOCK_ENTRY_CANCELLED,
                    message="ERPNext Stock Entry 已取消，禁止视为同步成功",
                )
            raise BusinessException(
                code=ERPNEXT_STOCK_ENTRY_STATUS_INVALID,
                message="ERPNext Stock Entry 状态非法",
            )

        if snapshot.stock_action == SubcontractStockOutboxService.STOCK_ACTION_ISSUE:
            return self.erp_service.create_and_submit_material_issue(payload_json=payload_json)
        if snapshot.stock_action == SubcontractStockOutboxService.STOCK_ACTION_RECEIPT:
            return self.erp_service.create_and_submit_material_receipt(payload_json=payload_json)
        raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="不支持的库存动作")

    def _finalize_success(self, *, snapshot: _ClaimedOutboxSnapshot, stock_entry_name: str) -> bool:
        row = self.outbox_service.get_processing_for_worker(
            outbox_id=snapshot.outbox_id,
            worker_id=self.worker_id,
            stock_action=snapshot.stock_action,
        )
        if row is None:
            self.session.rollback()
            return False
        try:
            attempt_no = self.outbox_service.mark_succeeded(row=row, stock_entry_name=stock_entry_name)
            self._mark_rows_synced(
                outbox_id=snapshot.outbox_id,
                stock_entry_name=stock_entry_name,
                stock_action=snapshot.stock_action,
            )
            self._append_sync_log(
                outbox_id=snapshot.outbox_id,
                subcontract_id=snapshot.subcontract_id,
                company=snapshot.company,
                stock_action=snapshot.stock_action,
                attempt_no=attempt_no,
                stock_entry_name=stock_entry_name,
                sync_status="success",
                error_code=None,
                error_message=None,
                request_id=snapshot.request_id,
            )
            self._commit_phase()
            return True
        except DatabaseWriteFailed:
            self.session.rollback()
            raise

    def _finalize_failure(
        self,
        *,
        snapshot: _ClaimedOutboxSnapshot,
        error_code: str,
        error_message: str,
    ) -> tuple[bool, bool]:
        row = self.outbox_service.get_processing_for_worker(
            outbox_id=snapshot.outbox_id,
            worker_id=self.worker_id,
            stock_action=snapshot.stock_action,
        )
        if row is None:
            self.session.rollback()
            return False, False
        try:
            attempt_no = self.outbox_service.mark_failed(
                row=row,
                error_code=error_code,
                error_message=error_message,
            )
            self._mark_rows_failed(
                outbox_id=snapshot.outbox_id,
                stock_action=snapshot.stock_action,
                error_code=error_code,
            )
            self._append_sync_log(
                outbox_id=snapshot.outbox_id,
                subcontract_id=snapshot.subcontract_id,
                company=snapshot.company,
                stock_action=snapshot.stock_action,
                attempt_no=attempt_no,
                stock_entry_name=None,
                sync_status="failed",
                error_code=error_code,
                error_message=error_message,
                request_id=snapshot.request_id,
            )
            is_dead = row.status == SubcontractStockOutboxService.STATUS_DEAD
            self._commit_phase()
            return True, is_dead
        except DatabaseWriteFailed:
            self.session.rollback()
            raise

    def _mark_rows_synced(self, *, outbox_id: int, stock_entry_name: str, stock_action: str) -> None:
        try:
            if stock_action == SubcontractStockOutboxService.STOCK_ACTION_ISSUE:
                (
                    self.session.query(LySubcontractMaterial)
                    .filter(LySubcontractMaterial.stock_outbox_id == outbox_id)
                    .update(
                        {
                            "sync_status": "succeeded",
                            "stock_entry_name": stock_entry_name,
                        },
                        synchronize_session=False,
                    )
                )
            elif stock_action == SubcontractStockOutboxService.STOCK_ACTION_RECEIPT:
                (
                    self.session.query(LySubcontractReceipt)
                    .filter(LySubcontractReceipt.stock_outbox_id == outbox_id)
                    .update(
                        {
                            "sync_status": "succeeded",
                            "stock_entry_name": stock_entry_name,
                            "sync_error_code": None,
                        },
                        synchronize_session=False,
                    )
                )
            else:
                raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="不支持的库存动作")
            self.session.flush()
        except DatabaseWriteFailed:
            raise
        except Exception as exc:
            raise DatabaseWriteFailed() from exc

    def _mark_rows_failed(self, *, outbox_id: int, stock_action: str, error_code: str) -> None:
        failed_status = f"failed:{error_code}"[:32]
        try:
            if stock_action == SubcontractStockOutboxService.STOCK_ACTION_ISSUE:
                (
                    self.session.query(LySubcontractMaterial)
                    .filter(LySubcontractMaterial.stock_outbox_id == outbox_id)
                    .update(
                        {
                            "sync_status": failed_status,
                        },
                        synchronize_session=False,
                    )
                )
            elif stock_action == SubcontractStockOutboxService.STOCK_ACTION_RECEIPT:
                (
                    self.session.query(LySubcontractReceipt)
                    .filter(LySubcontractReceipt.stock_outbox_id == outbox_id)
                    .update(
                        {
                            "sync_status": failed_status,
                            "sync_error_code": error_code,
                        },
                        synchronize_session=False,
                    )
                )
            else:
                raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_CONFLICT, message="不支持的库存动作")
            self.session.flush()
        except DatabaseWriteFailed:
            raise
        except Exception as exc:
            raise DatabaseWriteFailed() from exc

    def _append_sync_log(
        self,
        *,
        outbox_id: int,
        subcontract_id: int,
        company: str | None,
        stock_action: str,
        attempt_no: int,
        stock_entry_name: str | None,
        sync_status: str,
        error_code: str | None,
        error_message: str | None,
        request_id: str,
    ) -> None:
        row = LySubcontractStockSyncLog(
            outbox_id=outbox_id,
            subcontract_id=subcontract_id,
            company=company,
            stock_action=stock_action,
            attempt_no=attempt_no,
            stock_entry_name=stock_entry_name,
            sync_status=sync_status,
            error_code=error_code,
            error_message=(error_message or "")[:255] or None,
            request_id=request_id,
        )
        if self._is_sqlite:
            row.id = self._next_sync_log_id()
        self.session.add(row)
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def _commit_phase(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseWriteFailed() from exc

    @staticmethod
    def _safe_error(message: str | None) -> str:
        text = sanitize_log_message(message or "")
        return text or REDACTED_MESSAGE
