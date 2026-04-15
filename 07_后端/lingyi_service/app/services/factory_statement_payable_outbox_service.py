"""Factory statement payable draft outbox service (TASK-006D)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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

from app.core.error_codes import FACTORY_STATEMENT_DATABASE_READ_FAILED
from app.core.error_codes import FACTORY_STATEMENT_DATABASE_WRITE_FAILED
from app.core.error_codes import FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT
from app.core.exceptions import BusinessException
from app.models.factory_statement import LyFactoryStatementPayableOutbox


@dataclass(frozen=True)
class FactoryStatementPayableOutboxClaim:
    """Claimed payable outbox snapshot for worker processing."""

    outbox_id: int
    statement_id: int
    statement_no: str
    company: str
    supplier: str
    event_key: str
    attempts: int
    max_attempts: int
    payload_json: dict[str, Any]


class FactoryStatementPayableOutboxService:
    """Outbox persistence and claim/finalize lifecycle."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_DEAD = "dead"
    ACTIVE_STATUSES = (
        STATUS_PENDING,
        STATUS_PROCESSING,
        STATUS_SUCCEEDED,
    )

    def __init__(self, *, session: Session):
        self.session = session

    def build_request_hash(
        self,
        *,
        statement_id: int,
        statement_no: str,
        supplier: str,
        net_amount: Decimal,
        payable_account: str,
        cost_center: str,
        posting_date: date,
        remark: str | None,
    ) -> str:
        payload = {
            "statement_id": int(statement_id),
            "statement_no": str(statement_no or "").strip(),
            "supplier": str(supplier or "").strip(),
            "net_amount": self._canonicalize(net_amount),
            "payable_account": str(payable_account or "").strip(),
            "cost_center": str(cost_center or "").strip(),
            "posting_date": posting_date.isoformat(),
            "remark": str(remark or "").strip(),
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def build_payload_hash(self, payload_json: dict[str, Any]) -> str:
        canonical = self._canonicalize(payload_json)
        encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def build_event_key(
        self,
        *,
        company: str,
        statement_id: int,
        statement_no: str,
        supplier: str,
        net_amount: Decimal,
        payable_account: str,
        cost_center: str,
        posting_date: date,
    ) -> str:
        payload = {
            "company": str(company or "").strip(),
            "statement_id": int(statement_id),
            "statement_no": str(statement_no or "").strip(),
            "supplier": str(supplier or "").strip(),
            "net_amount": self._canonicalize(net_amount),
            "payable_account": str(payable_account or "").strip(),
            "cost_center": str(cost_center or "").strip(),
            "posting_date": posting_date.isoformat(),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return f"fspi:{hashlib.sha256(encoded).hexdigest()}"

    def find_by_idempotency(
        self,
        *,
        company: str,
        statement_id: int,
        idempotency_key: str,
    ) -> LyFactoryStatementPayableOutbox | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayableOutbox)
                .filter(
                    LyFactoryStatementPayableOutbox.company == str(company),
                    LyFactoryStatementPayableOutbox.statement_id == int(statement_id),
                    LyFactoryStatementPayableOutbox.idempotency_key == str(idempotency_key),
                )
                .order_by(LyFactoryStatementPayableOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def find_by_event_key(self, *, event_key: str) -> LyFactoryStatementPayableOutbox | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.event_key == str(event_key))
                .order_by(LyFactoryStatementPayableOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def find_active_by_statement(self, *, statement_id: int) -> LyFactoryStatementPayableOutbox | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayableOutbox)
                .filter(
                    LyFactoryStatementPayableOutbox.statement_id == int(statement_id),
                    LyFactoryStatementPayableOutbox.status.in_(self.ACTIVE_STATUSES),
                )
                .order_by(
                    LyFactoryStatementPayableOutbox.created_at.desc(),
                    LyFactoryStatementPayableOutbox.id.desc(),
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def create_outbox(
        self,
        *,
        company: str,
        supplier: str,
        statement_id: int,
        statement_no: str,
        idempotency_key: str,
        request_hash: str,
        posting_date: date,
        payable_account: str,
        cost_center: str,
        net_amount: Decimal,
        payload_json: dict[str, Any],
        created_by: str,
        max_attempts: int = 5,
    ) -> LyFactoryStatementPayableOutbox:
        payload_hash = self.build_payload_hash(payload_json)
        event_key = self.build_event_key(
            company=company,
            statement_id=statement_id,
            statement_no=statement_no,
            supplier=supplier,
            net_amount=net_amount,
            payable_account=payable_account,
            cost_center=cost_center,
            posting_date=posting_date,
        )
        row = LyFactoryStatementPayableOutbox(
            company=str(company),
            supplier=str(supplier),
            statement_id=int(statement_id),
            statement_no=str(statement_no),
            idempotency_key=str(idempotency_key),
            request_hash=str(request_hash),
            event_key=event_key,
            payload_json=payload_json,
            payload_hash=payload_hash,
            status=self.STATUS_PENDING,
            attempts=0,
            max_attempts=max(1, int(max_attempts)),
            next_retry_at=datetime.utcnow(),
            created_by=str(created_by),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def ensure_idempotency(
        self,
        *,
        existing: LyFactoryStatementPayableOutbox,
        request_hash: str,
    ) -> LyFactoryStatementPayableOutbox:
        if str(existing.request_hash or "") != str(request_hash or ""):
            raise BusinessException(code=FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT)
        return existing

    def list_due_ids(
        self,
        *,
        batch_size: int,
        allowed_companies: set[str] | None = None,
        allowed_suppliers: set[str] | None = None,
    ) -> list[int]:
        now = datetime.utcnow()
        try:
            query = self.session.query(LyFactoryStatementPayableOutbox.id).filter(self._due_or_expired_lease_condition(now=now))
            if allowed_companies is not None:
                if not allowed_companies:
                    return []
                query = query.filter(LyFactoryStatementPayableOutbox.company.in_(sorted(allowed_companies)))
            if allowed_suppliers is not None:
                if not allowed_suppliers:
                    return []
                query = query.filter(LyFactoryStatementPayableOutbox.supplier.in_(sorted(allowed_suppliers)))

            rows = query.order_by(LyFactoryStatementPayableOutbox.id.asc()).limit(int(batch_size)).all()
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        return [int(row[0]) for row in rows]

    def claim_due(
        self,
        *,
        batch_size: int,
        worker_id: str,
        lease_seconds: int = 120,
        allowed_companies: set[str] | None = None,
        allowed_suppliers: set[str] | None = None,
    ) -> list[FactoryStatementPayableOutboxClaim]:
        claim_ids = self.list_due_ids(
            batch_size=batch_size,
            allowed_companies=allowed_companies,
            allowed_suppliers=allowed_suppliers,
        )
        if not claim_ids:
            return []

        now = datetime.utcnow()
        lease_until = now + timedelta(seconds=max(30, int(lease_seconds)))
        claims: list[FactoryStatementPayableOutboxClaim] = []

        for outbox_id in claim_ids:
            try:
                updated = (
                    self.session.query(LyFactoryStatementPayableOutbox)
                    .filter(
                        LyFactoryStatementPayableOutbox.id == int(outbox_id),
                        self._due_or_expired_lease_condition(now=now),
                    )
                    .update(
                        {
                            LyFactoryStatementPayableOutbox.status: self.STATUS_PROCESSING,
                            LyFactoryStatementPayableOutbox.attempts: LyFactoryStatementPayableOutbox.attempts + 1,
                            LyFactoryStatementPayableOutbox.locked_by: str(worker_id),
                            LyFactoryStatementPayableOutbox.locked_until: lease_until,
                        },
                        synchronize_session=False,
                    )
                )
            except SQLAlchemyError as exc:
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
            if not updated:
                continue

        try:
            rows = (
                self.session.query(LyFactoryStatementPayableOutbox)
                .filter(
                    LyFactoryStatementPayableOutbox.id.in_(claim_ids),
                    LyFactoryStatementPayableOutbox.status == self.STATUS_PROCESSING,
                    LyFactoryStatementPayableOutbox.locked_by == str(worker_id),
                )
                .order_by(LyFactoryStatementPayableOutbox.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

        for row in rows:
            claims.append(
                FactoryStatementPayableOutboxClaim(
                    outbox_id=int(row.id),
                    statement_id=int(row.statement_id),
                    statement_no=str(row.statement_no),
                    company=str(row.company),
                    supplier=str(row.supplier),
                    event_key=str(row.event_key),
                    attempts=int(row.attempts or 0),
                    max_attempts=int(row.max_attempts or 5),
                    payload_json=dict(row.payload_json or {}),
                )
            )

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
        return claims

    def _due_or_expired_lease_condition(self, *, now: datetime):
        return or_(
            and_(
                LyFactoryStatementPayableOutbox.status.in_([self.STATUS_PENDING, self.STATUS_FAILED]),
                or_(
                    LyFactoryStatementPayableOutbox.next_retry_at.is_(None),
                    LyFactoryStatementPayableOutbox.next_retry_at <= now,
                ),
            ),
            and_(
                LyFactoryStatementPayableOutbox.status == self.STATUS_PROCESSING,
                LyFactoryStatementPayableOutbox.locked_until.is_not(None),
                LyFactoryStatementPayableOutbox.locked_until < now,
            ),
        )

    def mark_succeeded(
        self,
        *,
        outbox_id: int,
        purchase_invoice_name: str,
        erpnext_docstatus: int,
        erpnext_status: str | None,
    ) -> LyFactoryStatementPayableOutbox:
        row = self._must_get_outbox(outbox_id=outbox_id)
        row.status = self.STATUS_SUCCEEDED
        row.erpnext_purchase_invoice = str(purchase_invoice_name)
        row.erpnext_docstatus = int(erpnext_docstatus)
        row.erpnext_status = str(erpnext_status or "").strip() or None
        row.last_error_code = None
        row.last_error_message = None
        row.locked_by = None
        row.locked_until = None
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
        return row

    def mark_failed(
        self,
        *,
        outbox_id: int,
        error_code: str,
        error_message: str,
    ) -> LyFactoryStatementPayableOutbox:
        row = self._must_get_outbox(outbox_id=outbox_id)
        attempts = int(row.attempts or 0)
        max_attempts = int(row.max_attempts or 5)
        is_dead = attempts >= max_attempts

        row.status = self.STATUS_DEAD if is_dead else self.STATUS_FAILED
        row.last_error_code = (str(error_code or "")[:64] or None)
        row.last_error_message = (str(error_message or "")[:255] or None)
        row.locked_by = None
        row.locked_until = None
        row.next_retry_at = datetime.utcnow() + timedelta(minutes=self._backoff_minutes(attempts))

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
        return row

    def _must_get_outbox(self, *, outbox_id: int) -> LyFactoryStatementPayableOutbox:
        try:
            row = (
                self.session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.id == int(outbox_id))
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        if row is None:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED)
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
            return FactoryStatementPayableOutboxService._canonicalize(Decimal(str(value)))
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return {
                str(k): FactoryStatementPayableOutboxService._canonicalize(v)
                for k, v in sorted(value.items(), key=lambda item: str(item[0]))
            }
        if isinstance(value, (list, tuple, set)):
            return [FactoryStatementPayableOutboxService._canonicalize(v) for v in value]
        return str(value)

    @staticmethod
    def _backoff_minutes(attempt_no: int) -> int:
        safe = max(1, int(attempt_no))
        return min(60, 2 ** min(safe, 6))
