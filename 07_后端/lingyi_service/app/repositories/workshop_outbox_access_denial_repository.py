"""Repository for outbox forbidden diagnostics dedupe and throttling."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.workshop import YsWorkshopOutboxAccessDenial


@dataclass(frozen=True)
class DenialUpsertResult:
    """Result of one denial upsert."""

    should_write_audit: bool
    seen_count: int


class WorkshopOutboxAccessDenialRepository:
    """Persist per-principal denial dedupe state."""

    def __init__(self, session: Session):
        self.session = session

    def upsert_denial(
        self,
        *,
        outbox_id: int,
        principal: str,
        reason_code: str,
        scope_hash: str,
        cooldown_seconds: int,
        now: datetime | None = None,
    ) -> DenialUpsertResult:
        """Upsert denial row and decide whether security audit should be emitted."""
        moment = now or datetime.utcnow()
        row = self._get_row(
            outbox_id=outbox_id,
            principal=principal,
            reason_code=reason_code,
            scope_hash=scope_hash,
        )
        if row is None:
            return self._insert_first_seen(
                outbox_id=outbox_id,
                principal=principal,
                reason_code=reason_code,
                scope_hash=scope_hash,
                cooldown_seconds=cooldown_seconds,
                now=moment,
            )
        return self._update_existing(
            row=row,
            cooldown_seconds=cooldown_seconds,
            now=moment,
        )

    def _insert_first_seen(
        self,
        *,
        outbox_id: int,
        principal: str,
        reason_code: str,
        scope_hash: str,
        cooldown_seconds: int,
        now: datetime,
    ) -> DenialUpsertResult:
        row = YsWorkshopOutboxAccessDenial(
            outbox_id=outbox_id,
            principal=principal,
            reason_code=reason_code,
            scope_hash=scope_hash,
            first_seen_at=now,
            last_seen_at=now,
            last_audit_at=now,
            next_audit_at=now + timedelta(seconds=max(1, cooldown_seconds)),
            seen_count=1,
            updated_at=now,
        )
        try:
            self.session.add(row)
            self.session.flush()
            return DenialUpsertResult(should_write_audit=True, seen_count=1)
        except IntegrityError:
            existing = self._get_row(
                outbox_id=outbox_id,
                principal=principal,
                reason_code=reason_code,
                scope_hash=scope_hash,
            )
            if existing is None:
                raise DatabaseWriteFailed()
            return self._update_existing(
                row=existing,
                cooldown_seconds=cooldown_seconds,
                now=now,
            )
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def _update_existing(
        self,
        *,
        row: YsWorkshopOutboxAccessDenial,
        cooldown_seconds: int,
        now: datetime,
    ) -> DenialUpsertResult:
        seen_count = int(row.seen_count or 0) + 1
        row.seen_count = seen_count
        row.last_seen_at = now

        should_write_audit = row.next_audit_at is None or row.next_audit_at <= now
        if should_write_audit:
            row.last_audit_at = now
            row.next_audit_at = now + timedelta(seconds=max(1, cooldown_seconds))
        row.updated_at = now

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return DenialUpsertResult(should_write_audit=should_write_audit, seen_count=seen_count)

    def _get_row(
        self,
        *,
        outbox_id: int,
        principal: str,
        reason_code: str,
        scope_hash: str,
    ) -> YsWorkshopOutboxAccessDenial | None:
        try:
            return (
                self.session.query(YsWorkshopOutboxAccessDenial)
                .filter(
                    YsWorkshopOutboxAccessDenial.outbox_id == outbox_id,
                    YsWorkshopOutboxAccessDenial.principal == principal,
                    YsWorkshopOutboxAccessDenial.reason_code == reason_code,
                    YsWorkshopOutboxAccessDenial.scope_hash == scope_hash,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
