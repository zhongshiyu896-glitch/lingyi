"""Outbox persistence and lifecycle service for quality Stock Entry sync (TASK-030D)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any

from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.quality_outbox import LyQualityOutbox
from app.services.outbox_state_machine import OUTBOX_STATUS_DEAD
from app.services.outbox_state_machine import OUTBOX_STATUS_FAILED
from app.services.outbox_state_machine import OUTBOX_STATUS_PENDING
from app.services.outbox_state_machine import OUTBOX_STATUS_PROCESSING
from app.services.outbox_state_machine import OUTBOX_STATUS_SUCCEEDED
from app.services.outbox_state_machine import build_event_key as build_stable_event_key
from app.services.outbox_state_machine import build_payload_hash as build_stable_payload_hash
from app.services.outbox_state_machine import decide_retry_transition


@dataclass(frozen=True)
class QualityOutboxClaim:
    """Claimed quality outbox snapshot for worker processing."""

    outbox_id: int
    inspection_id: int
    company: str
    event_type: str
    event_key: str
    payload_json: dict[str, Any]
    attempts: int
    max_attempts: int


class QualityOutboxService:
    """Quality outbox create/query/claim/finalize service."""

    EVENT_TYPE_STOCK_ENTRY_SYNC = "quality_stock_entry_sync"

    def __init__(self, *, session: Session):
        self.session = session

    def build_payload_hash(self, payload_json: dict[str, Any]) -> str:
        return build_stable_payload_hash(payload_json)

    def build_event_key(
        self,
        *,
        inspection_id: int,
        event_type: str,
        payload_hash: str,
    ) -> str:
        return build_stable_event_key(
            {
                "inspection_id": int(inspection_id),
                "event_type": str(event_type),
                "payload_hash": str(payload_hash),
            },
            prefix="qo",
        )

    def find_latest_by_inspection(self, *, inspection_id: int) -> LyQualityOutbox | None:
        try:
            return (
                self.session.query(LyQualityOutbox)
                .filter(LyQualityOutbox.inspection_id == int(inspection_id))
                .order_by(LyQualityOutbox.created_at.desc(), LyQualityOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def create_outbox(
        self,
        *,
        inspection_id: int,
        company: str,
        payload_json: dict[str, Any],
        created_by: str,
        event_type: str = EVENT_TYPE_STOCK_ENTRY_SYNC,
        max_attempts: int = 3,
    ) -> LyQualityOutbox:
        existing = self._find_by_inspection_event(inspection_id=inspection_id, event_type=event_type)
        if existing is not None:
            return existing

        payload_hash = self.build_payload_hash(payload_json)
        event_key = self.build_event_key(
            inspection_id=inspection_id,
            event_type=event_type,
            payload_hash=payload_hash,
        )
        existing_by_event = self._find_by_event_key(event_key=event_key)
        if existing_by_event is not None:
            return existing_by_event

        row = LyQualityOutbox(
            inspection_id=int(inspection_id),
            company=str(company),
            event_type=str(event_type),
            event_key=event_key,
            payload_json=dict(payload_json),
            payload_hash=payload_hash,
            status=OUTBOX_STATUS_PENDING,
            attempts=0,
            max_attempts=max(1, int(max_attempts)),
            next_retry_at=datetime.utcnow(),
            created_by=str(created_by),
        )
        self.session.add(row)
        try:
            self.session.flush()
        except IntegrityError:
            existing = self._find_by_inspection_event(inspection_id=inspection_id, event_type=event_type)
            if existing is not None:
                return existing
            raise DatabaseWriteFailed()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return row

    def list_due_ids(self, *, batch_size: int) -> list[int]:
        now = datetime.utcnow()
        due_condition = self._due_or_expired_lease_condition(now=now)
        try:
            rows = (
                self.session.query(LyQualityOutbox.id)
                .filter(due_condition)
                .order_by(LyQualityOutbox.id.asc())
                .limit(int(batch_size))
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return [int(row[0]) for row in rows]

    def claim_due(
        self,
        *,
        batch_size: int,
        worker_id: str,
        lease_seconds: int = 120,
    ) -> list[QualityOutboxClaim]:
        claim_ids = self.list_due_ids(batch_size=batch_size)
        if not claim_ids:
            return []

        now = datetime.utcnow()
        lease_until = now + timedelta(seconds=max(30, int(lease_seconds)))
        due_condition = self._due_or_expired_lease_condition(now=now)

        for outbox_id in claim_ids:
            try:
                updated = (
                    self.session.query(LyQualityOutbox)
                    .filter(
                        LyQualityOutbox.id == int(outbox_id),
                        due_condition,
                    )
                    .update(
                        {
                            LyQualityOutbox.status: OUTBOX_STATUS_PROCESSING,
                            LyQualityOutbox.attempts: LyQualityOutbox.attempts + 1,
                            LyQualityOutbox.locked_by: str(worker_id),
                            LyQualityOutbox.locked_at: now,
                            LyQualityOutbox.locked_until: lease_until,
                        },
                        synchronize_session=False,
                    )
                )
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc
            if not updated:
                continue

        try:
            rows = (
                self.session.query(LyQualityOutbox)
                .filter(
                    LyQualityOutbox.id.in_(claim_ids),
                    LyQualityOutbox.status == OUTBOX_STATUS_PROCESSING,
                    LyQualityOutbox.locked_by == str(worker_id),
                )
                .order_by(LyQualityOutbox.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        claims: list[QualityOutboxClaim] = []
        for row in rows:
            claims.append(
                QualityOutboxClaim(
                    outbox_id=int(row.id),
                    inspection_id=int(row.inspection_id),
                    company=str(row.company),
                    event_type=str(row.event_type),
                    event_key=str(row.event_key),
                    payload_json=dict(row.payload_json or {}),
                    attempts=int(row.attempts or 0),
                    max_attempts=int(row.max_attempts or 3),
                )
            )
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return claims

    def mark_succeeded(
        self,
        *,
        outbox_id: int,
        stock_entry_name: str | None,
    ) -> LyQualityOutbox:
        row = self._must_get_outbox(outbox_id=outbox_id)
        now = datetime.utcnow()
        row.status = OUTBOX_STATUS_SUCCEEDED
        row.stock_entry_name = str(stock_entry_name or "").strip() or None
        row.last_error_code = None
        row.last_error_message = None
        row.locked_by = None
        row.locked_at = None
        row.locked_until = None
        row.next_retry_at = None
        row.succeeded_at = now
        row.dead_at = None
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return row

    def mark_failed(
        self,
        *,
        outbox_id: int,
        error_code: str,
        error_message: str,
    ) -> LyQualityOutbox:
        row = self._must_get_outbox(outbox_id=outbox_id)
        now = datetime.utcnow()
        attempts = int(row.attempts or 0)
        max_attempts = int(row.max_attempts or 3)
        decision = decide_retry_transition(
            error_code=str(error_code or "").strip(),
            attempts=max(1, attempts),
            max_attempts=max(1, max_attempts),
            now=now,
            base_backoff_seconds=60,
            max_backoff_seconds=3600,
        )

        row.status = decision.next_status
        row.last_error_code = str(error_code or "").strip()[:64] or None
        row.last_error_message = str(error_message or "").strip()[:255] or None
        row.next_retry_at = decision.next_retry_at
        row.locked_by = None
        row.locked_at = None
        row.locked_until = None
        row.failed_at = now
        if decision.next_status == OUTBOX_STATUS_DEAD:
            row.dead_at = now
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return row

    def _find_by_event_key(self, *, event_key: str) -> LyQualityOutbox | None:
        try:
            return (
                self.session.query(LyQualityOutbox)
                .filter(LyQualityOutbox.event_key == str(event_key))
                .order_by(LyQualityOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _find_by_inspection_event(
        self,
        *,
        inspection_id: int,
        event_type: str,
    ) -> LyQualityOutbox | None:
        try:
            return (
                self.session.query(LyQualityOutbox)
                .filter(
                    LyQualityOutbox.inspection_id == int(inspection_id),
                    LyQualityOutbox.event_type == str(event_type),
                )
                .order_by(LyQualityOutbox.created_at.desc(), LyQualityOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _must_get_outbox(self, *, outbox_id: int) -> LyQualityOutbox:
        try:
            row = self.session.query(LyQualityOutbox).filter(LyQualityOutbox.id == int(outbox_id)).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise DatabaseReadFailed()
        return row

    @staticmethod
    def _due_or_expired_lease_condition(*, now: datetime):
        return or_(
            and_(
                LyQualityOutbox.status.in_([OUTBOX_STATUS_PENDING, OUTBOX_STATUS_FAILED]),
                or_(
                    LyQualityOutbox.next_retry_at.is_(None),
                    LyQualityOutbox.next_retry_at <= now,
                ),
            ),
            and_(
                LyQualityOutbox.status == OUTBOX_STATUS_PROCESSING,
                LyQualityOutbox.locked_until.is_not(None),
                LyQualityOutbox.locked_until < now,
            ),
        )
