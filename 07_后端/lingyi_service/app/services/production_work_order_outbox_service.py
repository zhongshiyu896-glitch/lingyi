"""Production Work Order outbox service (TASK-004A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.production import LyProductionWorkOrderOutbox


@dataclass(frozen=True)
class ProductionOutboxClaim:
    """Claimed outbox snapshot for worker processing."""

    outbox_id: int
    plan_id: int
    company: str
    item_code: str
    action: str
    payload_json: dict[str, Any]
    event_key: str
    max_attempts: int
    attempts: int


class ProductionWorkOrderOutboxService:
    """Outbox service for Work Order sync."""

    ACTION_CREATE_WORK_ORDER = "create_work_order"

    def __init__(self, session: Session):
        self.session = session

    def build_payload_hash(self, payload: dict[str, Any]) -> str:
        canonical = self._canonicalize(payload)
        encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def build_event_key(
        self,
        *,
        action: str,
        plan_id: int,
        idempotency_key: str,
        payload_hash: str,
    ) -> str:
        payload = {
            "action": str(action),
            "plan_id": int(plan_id),
            "idempotency_key": str(idempotency_key),
            "payload_hash": str(payload_hash),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return f"pwo:{digest}"

    def find_existing(
        self,
        *,
        plan_id: int,
        action: str,
        statuses: list[str] | None = None,
    ) -> LyProductionWorkOrderOutbox | None:
        try:
            query = self.session.query(LyProductionWorkOrderOutbox).filter(
                LyProductionWorkOrderOutbox.plan_id == int(plan_id),
                LyProductionWorkOrderOutbox.action == action,
            )
            if statuses:
                query = query.filter(LyProductionWorkOrderOutbox.status.in_(statuses))
            return query.order_by(LyProductionWorkOrderOutbox.id.desc()).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def find_existing_by_idempotency(
        self,
        *,
        plan_id: int,
        action: str,
        idempotency_key: str,
    ) -> LyProductionWorkOrderOutbox | None:
        try:
            return (
                self.session.query(LyProductionWorkOrderOutbox)
                .filter(
                    LyProductionWorkOrderOutbox.plan_id == int(plan_id),
                    LyProductionWorkOrderOutbox.action == action,
                    LyProductionWorkOrderOutbox.idempotency_key == idempotency_key,
                )
                .order_by(LyProductionWorkOrderOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def create_outbox(
        self,
        *,
        plan_id: int,
        company: str,
        item_code: str,
        idempotency_key: str,
        payload_json: dict[str, Any],
        payload_hash: str | None,
        request_id: str,
        operator: str,
        max_attempts: int = 5,
    ) -> LyProductionWorkOrderOutbox:
        if payload_hash is None:
            payload_hash = self.build_payload_hash(payload_json)
        event_key = self.build_event_key(
            action=self.ACTION_CREATE_WORK_ORDER,
            plan_id=plan_id,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )

        row = LyProductionWorkOrderOutbox(
            plan_id=plan_id,
            company=company,
            item_code=item_code,
            action=self.ACTION_CREATE_WORK_ORDER,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            payload_json=payload_json,
            event_key=event_key,
            status="pending",
            attempts=0,
            max_attempts=max_attempts,
            request_id=request_id,
            created_by=operator,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return row

    def latest_by_plan_ids(self, *, plan_ids: list[int]) -> dict[int, LyProductionWorkOrderOutbox]:
        if not plan_ids:
            return {}
        try:
            rows = (
                self.session.query(LyProductionWorkOrderOutbox)
                .filter(LyProductionWorkOrderOutbox.plan_id.in_(sorted({int(i) for i in plan_ids})))
                .order_by(
                    LyProductionWorkOrderOutbox.plan_id.asc(),
                    LyProductionWorkOrderOutbox.created_at.desc(),
                    LyProductionWorkOrderOutbox.id.desc(),
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        latest: dict[int, LyProductionWorkOrderOutbox] = {}
        for row in rows:
            pid = int(row.plan_id)
            if pid not in latest:
                latest[pid] = row
        return latest

    def claim_due(
        self,
        *,
        batch_size: int,
        worker_id: str,
        lease_seconds: int = 120,
        allowed_companies: set[str] | None = None,
        allowed_items: set[str] | None = None,
    ) -> list[ProductionOutboxClaim]:
        now = datetime.utcnow()
        lease_until = now + timedelta(seconds=max(30, lease_seconds))
        try:
            claimable = and_(
                LyProductionWorkOrderOutbox.action == self.ACTION_CREATE_WORK_ORDER,
                or_(
                    and_(
                        LyProductionWorkOrderOutbox.status.in_(["pending", "failed"]),
                        LyProductionWorkOrderOutbox.next_retry_at <= now,
                    ),
                    and_(
                        LyProductionWorkOrderOutbox.status == "processing",
                        LyProductionWorkOrderOutbox.lease_until.is_not(None),
                        LyProductionWorkOrderOutbox.lease_until < now,
                    ),
                ),
            )
            sql = self.session.query(LyProductionWorkOrderOutbox).filter(claimable)
            if allowed_companies is not None:
                if not allowed_companies:
                    return []
                sql = sql.filter(LyProductionWorkOrderOutbox.company.in_(sorted(allowed_companies)))
            if allowed_items is not None:
                if not allowed_items:
                    return []
                sql = sql.filter(LyProductionWorkOrderOutbox.item_code.in_(sorted(allowed_items)))
            sql = sql.order_by(LyProductionWorkOrderOutbox.id.asc()).limit(int(batch_size))
            if self.session.bind is not None and self.session.bind.dialect.name == "postgresql":
                sql = sql.with_for_update(skip_locked=True)
            rows = sql.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        claimed_ids: list[int] = []
        for row in rows:
            try:
                updated = (
                    self.session.query(LyProductionWorkOrderOutbox)
                    .filter(
                        LyProductionWorkOrderOutbox.id == int(row.id),
                        claimable,
                    )
                    .update(
                        {
                            LyProductionWorkOrderOutbox.status: "processing",
                            LyProductionWorkOrderOutbox.attempts: int(row.attempts or 0) + 1,
                            LyProductionWorkOrderOutbox.locked_by: worker_id,
                            LyProductionWorkOrderOutbox.locked_at: now,
                            LyProductionWorkOrderOutbox.lease_until: lease_until,
                        },
                        synchronize_session=False,
                    )
                )
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc
            if updated:
                claimed_ids.append(int(row.id))

        if not claimed_ids:
            return []

        claims: list[ProductionOutboxClaim] = []
        try:
            claimed_rows = (
                self.session.query(LyProductionWorkOrderOutbox)
                .filter(LyProductionWorkOrderOutbox.id.in_(claimed_ids))
                .order_by(LyProductionWorkOrderOutbox.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        for row in claimed_rows:
            claims.append(
                ProductionOutboxClaim(
                    outbox_id=int(row.id),
                    plan_id=int(row.plan_id),
                    company=str(row.company),
                    item_code=str(row.item_code),
                    action=str(row.action),
                    payload_json=dict(row.payload_json or {}),
                    event_key=str(row.event_key),
                    max_attempts=int(row.max_attempts or 5),
                    attempts=int(row.attempts or 0),
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
        work_order: str,
    ) -> LyProductionWorkOrderOutbox:
        row = self._must_get_outbox(outbox_id)
        row.status = "succeeded"
        row.erpnext_work_order = work_order
        row.last_error_code = None
        row.last_error_message = None
        row.locked_by = None
        row.locked_at = None
        row.lease_until = None
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
    ) -> LyProductionWorkOrderOutbox:
        row = self._must_get_outbox(outbox_id)
        attempts = int(row.attempts or 0)
        max_attempts = int(row.max_attempts or 5)
        is_dead = attempts >= max_attempts

        row.status = "dead" if is_dead else "failed"
        row.last_error_code = (error_code or "")[:64] or None
        row.last_error_message = (error_message or "")[:255] or None
        row.locked_by = None
        row.locked_at = None
        row.lease_until = None
        row.next_retry_at = datetime.utcnow() + timedelta(minutes=self._backoff_minutes(attempts))

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return row

    def _must_get_outbox(self, outbox_id: int) -> LyProductionWorkOrderOutbox:
        try:
            row = (
                self.session.query(LyProductionWorkOrderOutbox)
                .filter(LyProductionWorkOrderOutbox.id == int(outbox_id))
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise DatabaseReadFailed()
        return row

    @staticmethod
    def _canonicalize(value: Any) -> Any:
        if isinstance(value, Decimal):
            normalized = value.normalize()
            text = format(normalized, "f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            return text or "0"
        if isinstance(value, bool) or value is None:
            return value
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return ProductionWorkOrderOutboxService._canonicalize(Decimal(str(value)))
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return {str(k): ProductionWorkOrderOutboxService._canonicalize(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
        if isinstance(value, (list, tuple, set)):
            return [ProductionWorkOrderOutboxService._canonicalize(v) for v in value]
        return str(value)

    @staticmethod
    def _backoff_minutes(attempt_no: int) -> int:
        safe = max(1, int(attempt_no))
        return min(60, 2 ** min(safe, 6))
