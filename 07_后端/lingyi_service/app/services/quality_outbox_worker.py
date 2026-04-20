"""Worker service for quality outbox processing (TASK-030D)."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import QUALITY_INTERNAL_ERROR
from app.core.exceptions import AppException
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.services.erpnext_quality_outbox_adapter import ERPNextQualityOutboxAdapter
from app.services.quality_outbox_service import QualityOutboxClaim
from app.services.quality_outbox_service import QualityOutboxService


@dataclass(frozen=True)
class QualityOutboxWorkerRunResult:
    """Run-once worker result summary."""

    dry_run: bool
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int


class QualityOutboxWorker:
    """Consume quality outbox and sync ERPNext Stock Entry asynchronously."""

    def __init__(
        self,
        *,
        session: Session,
        adapter: ERPNextQualityOutboxAdapter,
    ):
        self.session = session
        self.adapter = adapter
        self.outbox_service = QualityOutboxService(session=session)

    def run_once(
        self,
        *,
        batch_size: int,
        worker_id: str,
        dry_run: bool = False,
    ) -> QualityOutboxWorkerRunResult:
        if dry_run:
            due_ids = self.outbox_service.list_due_ids(batch_size=batch_size)
            return QualityOutboxWorkerRunResult(
                dry_run=True,
                processed_count=len(due_ids),
                succeeded_count=0,
                failed_count=0,
                dead_count=0,
            )

        claims = self.outbox_service.claim_due(
            batch_size=batch_size,
            worker_id=worker_id,
        )
        if claims:
            try:
                self.session.commit()
            except SQLAlchemyError as exc:
                self.session.rollback()
                raise DatabaseWriteFailed() from exc

        succeeded = 0
        failed = 0
        dead = 0

        for claim in claims:
            try:
                stock_entry_name = self.adapter.sync_stock_entry(
                    event_key=claim.event_key,
                    payload_json=claim.payload_json,
                )
                self._persist_success(claim=claim, stock_entry_name=stock_entry_name)
                succeeded += 1
            except AppException as exc:
                is_dead = self._persist_failure(claim=claim, exc=exc)
                failed += 1
                if is_dead:
                    dead += 1
            except Exception as exc:  # pragma: no cover - defensive path
                wrapped = BusinessException(code=QUALITY_INTERNAL_ERROR, message="质量 Outbox 同步失败")
                is_dead = self._persist_failure(claim=claim, exc=wrapped, raw_exc=exc)
                failed += 1
                if is_dead:
                    dead += 1

        return QualityOutboxWorkerRunResult(
            dry_run=False,
            processed_count=len(claims),
            succeeded_count=succeeded,
            failed_count=failed,
            dead_count=dead,
        )

    def _persist_success(
        self,
        *,
        claim: QualityOutboxClaim,
        stock_entry_name: str | None,
    ) -> None:
        self.outbox_service.mark_succeeded(
            outbox_id=claim.outbox_id,
            stock_entry_name=stock_entry_name,
        )
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseWriteFailed() from exc

    def _persist_failure(
        self,
        *,
        claim: QualityOutboxClaim,
        exc: AppException,
        raw_exc: Exception | None = None,
    ) -> bool:
        row = self.outbox_service.mark_failed(
            outbox_id=claim.outbox_id,
            error_code=exc.code,
            error_message=exc.message,
        )
        try:
            self.session.commit()
        except SQLAlchemyError as commit_exc:
            self.session.rollback()
            raise DatabaseWriteFailed() from commit_exc
        del raw_exc
        return str(row.status) == "dead"
