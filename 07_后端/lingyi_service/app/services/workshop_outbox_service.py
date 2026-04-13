"""Workshop Job Card sync outbox service (TASK-003D)."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from typing import Iterable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import WORKSHOP_OUTBOX_ALREADY_SUCCEEDED
from app.core.error_codes import WORKSHOP_OUTBOX_LOCKED
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.workshop import YsWorkshopJobCardSyncOutbox


class WorkshopOutboxService:
    """Encapsulate outbox enqueue/claim/retry state transitions."""

    EVENT_KEY_PREFIX = "wjc:"
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_DEAD = "dead"

    RETRY_MINUTES = (1, 5, 15, 60)

    def __init__(self, session: Session):
        self.session = session

    @classmethod
    def build_event_key(
        cls,
        *,
        job_card: str,
        local_completed_qty: Decimal,
        source_type: str,
        source_ids: Iterable[int] | None,
    ) -> str:
        """Build deterministic event key for outbox idempotency.

        Format is fixed and safe from truncation collisions:
        `wjc:{sha256_hex}` (always 68 chars).
        """
        ids = cls._canonical_source_ids(source_ids)
        raw = {
            "job_card": job_card,
            "local_completed_qty": cls._canonical_decimal(local_completed_qty),
            "source_type": source_type,
            "source_ids": ids,
        }
        digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return f"{cls.EVENT_KEY_PREFIX}{digest}"

    def enqueue(
        self,
        *,
        job_card: str,
        work_order: str | None,
        item_code: str,
        company: str,
        local_completed_qty: Decimal,
        source_type: str,
        source_ids: Iterable[int] | None,
        request_id: str,
        created_by: str,
        max_attempts: int = 5,
    ) -> YsWorkshopJobCardSyncOutbox:
        """Create pending outbox row; return existing row when event key matches."""
        event_key = self.build_event_key(
            job_card=job_card,
            local_completed_qty=local_completed_qty,
            source_type=source_type,
            source_ids=source_ids,
        )
        source_id_list = self._canonical_source_ids(source_ids)

        try:
            existing = (
                self.session.query(YsWorkshopJobCardSyncOutbox)
                .filter(YsWorkshopJobCardSyncOutbox.event_key == event_key)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if existing:
            return existing
        legacy_equivalent = self._find_legacy_equivalent(
            job_card=job_card,
            event_key=event_key,
        )
        if legacy_equivalent:
            return legacy_equivalent

        row = YsWorkshopJobCardSyncOutbox(
            event_key=event_key,
            job_card=job_card,
            work_order=work_order,
            item_code=item_code,
            company=company,
            local_completed_qty=local_completed_qty,
            source_type=source_type,
            source_ids=source_id_list,
            status=self.STATUS_PENDING,
            attempts=0,
            max_attempts=max_attempts,
            next_retry_at=datetime.utcnow(),
            locked_by=None,
            locked_at=None,
            last_error_code=None,
            last_error_message=None,
            request_id=request_id,
            created_by=created_by,
            updated_at=datetime.utcnow(),
        )
        try:
            self.session.add(row)
            self.session.flush()
            return row
        except IntegrityError:
            # Concurrent insert by another transaction.
            existing = (
                self.session.query(YsWorkshopJobCardSyncOutbox)
                .filter(YsWorkshopJobCardSyncOutbox.event_key == event_key)
                .first()
            )
            if existing:
                return existing
            legacy_equivalent = self._find_legacy_equivalent(
                job_card=job_card,
                event_key=event_key,
            )
            if legacy_equivalent:
                return legacy_equivalent
            raise DatabaseWriteFailed()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def requeue(
        self,
        *,
        job_card: str,
        work_order: str | None,
        item_code: str,
        company: str,
        local_completed_qty: Decimal,
        source_type: str,
        source_ids: Iterable[int] | None,
        request_id: str,
        operator: str,
        max_attempts: int = 5,
    ) -> YsWorkshopJobCardSyncOutbox:
        """Create or requeue an outbox row for manual retry."""
        row = self.enqueue(
            job_card=job_card,
            work_order=work_order,
            item_code=item_code,
            company=company,
            local_completed_qty=local_completed_qty,
            source_type=source_type,
            source_ids=source_ids,
            request_id=request_id,
            created_by=operator,
            max_attempts=max_attempts,
        )

        if row.status == self.STATUS_SUCCEEDED:
            raise BusinessException(code=WORKSHOP_OUTBOX_ALREADY_SUCCEEDED, message="同步任务已成功，无需重试")
        if row.status == self.STATUS_PROCESSING:
            raise BusinessException(code=WORKSHOP_OUTBOX_LOCKED, message="同步任务正在处理中，请稍后重试")

        row.status = self.STATUS_PENDING
        row.next_retry_at = datetime.utcnow()
        row.locked_by = None
        row.locked_at = None
        row.last_error_code = None
        row.last_error_message = None
        row.request_id = request_id
        row.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return row

    def claim_due(self, *, limit: int, worker_id: str) -> list[YsWorkshopJobCardSyncOutbox]:
        """Claim due outbox rows for processing."""
        due_rows = self.list_due(limit=limit)
        row_ids = [int(row.id) for row in due_rows]
        return self.claim_by_ids(row_ids=row_ids, worker_id=worker_id)

    def list_due(self, *, limit: int) -> list[YsWorkshopJobCardSyncOutbox]:
        """List due rows without mutating lock/status."""
        now = datetime.utcnow()
        query = (
            self.session.query(YsWorkshopJobCardSyncOutbox)
            .filter(
                YsWorkshopJobCardSyncOutbox.status.in_([self.STATUS_PENDING, self.STATUS_FAILED]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= now,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
            )
            .order_by(YsWorkshopJobCardSyncOutbox.id.asc())
            .limit(limit)
        )
        try:
            return query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def claim_by_ids(self, *, row_ids: Iterable[int], worker_id: str) -> list[YsWorkshopJobCardSyncOutbox]:
        """Claim specific outbox rows by id (with due-status guard)."""
        unique_ids = sorted({int(v) for v in row_ids if v is not None})
        if not unique_ids:
            return []
        now = datetime.utcnow()
        query = (
            self.session.query(YsWorkshopJobCardSyncOutbox)
            .filter(
                YsWorkshopJobCardSyncOutbox.id.in_(unique_ids),
                YsWorkshopJobCardSyncOutbox.status.in_([self.STATUS_PENDING, self.STATUS_FAILED]),
                YsWorkshopJobCardSyncOutbox.next_retry_at <= now,
                YsWorkshopJobCardSyncOutbox.attempts < YsWorkshopJobCardSyncOutbox.max_attempts,
            )
            .order_by(YsWorkshopJobCardSyncOutbox.id.asc())
        )
        try:
            rows = query.with_for_update(skip_locked=True).all()
        except Exception:
            try:
                rows = query.all()
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc

        for row in rows:
            row.status = self.STATUS_PROCESSING
            row.locked_by = worker_id
            row.locked_at = now
            row.updated_at = now

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return rows

    def mark_succeeded(
        self,
        *,
        row: YsWorkshopJobCardSyncOutbox,
        local_completed_qty: Decimal,
    ) -> int:
        """Mark processing row as succeeded; returns attempt number."""
        attempt_no = int(row.attempts or 0) + 1
        row.status = self.STATUS_SUCCEEDED
        row.attempts = attempt_no
        row.local_completed_qty = local_completed_qty
        row.locked_by = None
        row.locked_at = None
        row.last_error_code = None
        row.last_error_message = None
        row.next_retry_at = datetime.utcnow()
        row.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return attempt_no

    def mark_failed(
        self,
        *,
        row: YsWorkshopJobCardSyncOutbox,
        error_code: str,
        error_message: str | None,
    ) -> int:
        """Mark processing row as failed/dead using exponential backoff; returns attempt number."""
        attempt_no = int(row.attempts or 0) + 1
        row.attempts = attempt_no
        row.last_error_code = error_code
        row.last_error_message = (error_message or "")[:255] or None
        row.locked_by = None
        row.locked_at = None

        if attempt_no >= int(row.max_attempts or 5):
            row.status = self.STATUS_DEAD
            row.next_retry_at = datetime.utcnow()
        else:
            row.status = self.STATUS_FAILED
            row.next_retry_at = datetime.utcnow() + timedelta(minutes=self._backoff_minutes(attempt_no))

        row.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return attempt_no

    def mark_scope_required_dead(
        self,
        *,
        row: YsWorkshopJobCardSyncOutbox,
        error_code: str,
        error_message: str | None,
    ) -> None:
        """Move malformed scope row out of due queue without consuming retry attempts."""
        row.status = self.STATUS_DEAD
        row.last_error_code = error_code
        row.last_error_message = (error_message or "")[:255] or None
        row.locked_by = None
        row.locked_at = None
        row.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def latest_by_job_card(self, job_card: str) -> YsWorkshopJobCardSyncOutbox | None:
        """Read latest outbox row by job card."""
        try:
            return (
                self.session.query(YsWorkshopJobCardSyncOutbox)
                .filter(YsWorkshopJobCardSyncOutbox.job_card == job_card)
                .order_by(YsWorkshopJobCardSyncOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    @classmethod
    def _backoff_minutes(cls, attempt_no: int) -> int:
        index = max(0, attempt_no - 1)
        if index >= len(cls.RETRY_MINUTES):
            return cls.RETRY_MINUTES[-1]
        return cls.RETRY_MINUTES[index]

    def _find_legacy_equivalent(
        self,
        *,
        job_card: str,
        event_key: str,
    ) -> YsWorkshopJobCardSyncOutbox | None:
        """Compatibility path for legacy pre-TASK-003E outbox keys.

        Legacy keys used a long job-card prefix with truncation, which could
        collide when job_card was long. We do semantic matching by canonical
        payload hash to avoid creating duplicate rows for the same event.
        """
        try:
            candidates = (
                self.session.query(YsWorkshopJobCardSyncOutbox)
                .filter(YsWorkshopJobCardSyncOutbox.job_card == job_card)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        for row in candidates:
            if str(row.event_key or "").startswith(self.EVENT_KEY_PREFIX):
                continue
            candidate_key = self.build_event_key(
                job_card=str(row.job_card or ""),
                local_completed_qty=Decimal(str(row.local_completed_qty or "0")),
                source_type=str(row.source_type or ""),
                source_ids=row.source_ids or [],
            )
            if candidate_key == event_key:
                return row
        return None

    @staticmethod
    def _canonical_source_ids(source_ids: Iterable[int] | None) -> list[int]:
        return sorted({int(v) for v in (source_ids or [])})

    @staticmethod
    def _canonical_decimal(value: Decimal) -> str:
        decimal_value = Decimal(str(value))
        normalized = decimal_value.normalize()
        text = format(normalized, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if text in {"", "-0"}:
            return "0"
        return text
