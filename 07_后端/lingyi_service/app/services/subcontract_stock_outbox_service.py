"""Subcontract stock sync outbox service (TASK-002D/TASK-002E)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from decimal import InvalidOperation
import hashlib
import json
from typing import Any

from sqlalchemy import and_
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import SUBCONTRACT_IDEMPOTENCY_CONFLICT
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_ACTION_MISMATCH
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_IDEMPOTENCY_MISMATCH
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_NOT_FOUND
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE
from app.core.error_codes import SUBCONTRACT_STOCK_OUTBOX_ORDER_MISMATCH
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.subcontract import LySubcontractStockOutbox


@dataclass(frozen=True)
class SubcontractWorkerScope:
    """Service-account scoped resources for subcontract stock worker."""

    companies: set[str]
    items: set[str]
    suppliers: set[str]
    warehouses: set[str]


class SubcontractStockOutboxService:
    """Enqueue, claim and state transitions for subcontract stock outbox."""

    EVENT_KEY_PREFIX = "sio:"
    STOCK_ACTION_ISSUE = "issue"
    STOCK_ACTION_RECEIPT = "receipt"

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_DEAD = "dead"

    RETRY_MINUTES = (1, 5, 15, 60)
    _VOLATILE_PAYLOAD_KEYS = {
        "custom_ly_subcontract_outbox_id",
        "custom_ly_outbox_event_key",
        "custom_ly_request_id",
        "issue_batch_no",
        "receipt_batch_no",
    }
    _DECIMAL_SEMANTIC_KEYS = {
        "qty",
        "required_qty",
        "issued_qty",
        "received_qty",
        "planned_qty",
        "inspected_qty",
        "rejected_qty",
        "accepted_qty",
        "rejected_rate",
        "subcontract_rate",
        "deduction_amount_per_piece",
        "gross_amount",
        "deduction_amount",
        "net_amount",
    }

    def __init__(self, session: Session):
        self.session = session

    @property
    def _is_sqlite(self) -> bool:
        bind = self.session.get_bind()
        return bool(bind and bind.dialect.name == "sqlite")

    def _next_id(self) -> int:
        try:
            current = self.session.query(LySubcontractStockOutbox.id).order_by(LySubcontractStockOutbox.id.desc()).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return int(current[0]) + 1 if current and current[0] is not None else 1

    @classmethod
    def build_payload_hash(cls, payload_json: dict[str, Any]) -> str:
        canonical_payload = cls._canonicalize_payload(payload_json)
        canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def _canonicalize_payload(cls, payload_json: dict[str, Any]) -> dict[str, Any]:
        payload = cls._canonicalize_value(payload_json)
        if not isinstance(payload, dict):
            return {}

        items = payload.get("items")
        if isinstance(items, list):
            normalized_items: list[dict[str, Any]] = []
            for item in items:
                if isinstance(item, dict):
                    normalized_items.append(dict(item))
            payload["items"] = sorted(
                normalized_items,
                key=lambda row: (
                    str(row.get("item_code", "")),
                    str(row.get("s_warehouse", "")),
                    str(row.get("t_warehouse", "")),
                    str(row.get("batch_no", "")),
                    str(row.get("qty", "")),
                    str(row.get("uom", "")),
                ),
            )

        return payload

    @classmethod
    def _canonicalize_value(cls, value: Any, *, key: str | None = None) -> Any:
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for child_key, child_value in value.items():
                if child_key in cls._VOLATILE_PAYLOAD_KEYS:
                    continue
                normalized[child_key] = cls._canonicalize_value(child_value, key=child_key)
            return normalized
        if isinstance(value, list):
            return [cls._canonicalize_value(item) for item in value]
        if key in cls._DECIMAL_SEMANTIC_KEYS:
            return cls._normalize_decimal_text(value)
        return value

    @staticmethod
    def _normalize_decimal_text(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, Decimal):
            decimal_value = value
        elif isinstance(value, (int, float)):
            decimal_value = Decimal(str(value))
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return raw
            try:
                decimal_value = Decimal(raw)
            except (InvalidOperation, ValueError):
                return value
        else:
            return value

        normalized = format(decimal_value, "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        if normalized in {"-0", ""}:
            normalized = "0"
        return normalized

    @classmethod
    def build_event_key(
        cls,
        *,
        subcontract_id: int,
        stock_action: str,
        idempotency_key: str,
        payload_hash: str,
    ) -> str:
        body = {
            "subcontract_id": int(subcontract_id),
            "stock_action": stock_action,
            "idempotency_key": idempotency_key,
            "payload_hash": payload_hash,
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        return f"{cls.EVENT_KEY_PREFIX}{digest}"

    def enqueue(
        self,
        *,
        subcontract_id: int,
        stock_action: str,
        company: str,
        supplier: str,
        item_code: str,
        warehouse: str,
        idempotency_key: str,
        payload_json: dict[str, Any],
        idempotency_payload_hash: str | None = None,
        request_id: str,
        created_by: str,
        max_attempts: int = 5,
    ) -> tuple[LySubcontractStockOutbox, bool]:
        """Create outbox row with idempotency check."""
        payload_hash = idempotency_payload_hash or self.build_payload_hash(payload_json)
        event_key = self.build_event_key(
            subcontract_id=subcontract_id,
            stock_action=stock_action,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
        )

        existing = self.find_by_idempotency(
            subcontract_id=subcontract_id,
            stock_action=stock_action,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            if (existing.payload_hash or "") == payload_hash:
                return existing, False
            raise BusinessException(
                code=SUBCONTRACT_IDEMPOTENCY_CONFLICT,
                message="幂等键冲突，且请求内容不一致",
            )

        row = LySubcontractStockOutbox(
            subcontract_id=subcontract_id,
            event_key=event_key,
            stock_action=stock_action,
            idempotency_key=idempotency_key,
            payload_hash=payload_hash,
            payload_json=payload_json,
            company=company,
            supplier=supplier,
            item_code=item_code,
            warehouse=warehouse,
            action=stock_action,
            payload=payload_json,
            status=self.STATUS_PENDING,
            attempts=0,
            max_attempts=max_attempts,
            next_retry_at=datetime.utcnow(),
            locked_by=None,
            locked_at=None,
            lease_until=None,
            stock_entry_name=None,
            last_error_code=None,
            last_error_message=None,
            request_id=request_id,
            created_by=created_by,
        )
        if self._is_sqlite:
            row.id = self._next_id()
        try:
            self.session.add(row)
            self.session.flush()
            return row, True
        except IntegrityError as exc:
            self.session.rollback()
            retry_existing = self.find_by_idempotency(
                subcontract_id=subcontract_id,
                stock_action=stock_action,
                idempotency_key=idempotency_key,
            )
            if retry_existing is not None:
                if (retry_existing.payload_hash or "") == payload_hash:
                    return retry_existing, False
                raise BusinessException(
                    code=SUBCONTRACT_IDEMPOTENCY_CONFLICT,
                    message="幂等键冲突，且请求内容不一致",
                ) from exc
            raise DatabaseWriteFailed() from exc
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def enqueue_issue(self, **kwargs) -> tuple[LySubcontractStockOutbox, bool]:
        return self.enqueue(stock_action=self.STOCK_ACTION_ISSUE, **kwargs)

    def enqueue_receipt(self, **kwargs) -> tuple[LySubcontractStockOutbox, bool]:
        return self.enqueue(stock_action=self.STOCK_ACTION_RECEIPT, **kwargs)

    def find_by_idempotency(
        self,
        *,
        subcontract_id: int,
        stock_action: str,
        idempotency_key: str,
    ) -> LySubcontractStockOutbox | None:
        try:
            return (
                self.session.query(LySubcontractStockOutbox)
                .filter(
                    LySubcontractStockOutbox.subcontract_id == subcontract_id,
                    LySubcontractStockOutbox.stock_action == stock_action,
                    LySubcontractStockOutbox.idempotency_key == idempotency_key,
                )
                .order_by(LySubcontractStockOutbox.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def get_by_id(self, *, outbox_id: int) -> LySubcontractStockOutbox:
        try:
            row = (
                self.session.query(LySubcontractStockOutbox)
                .filter(LySubcontractStockOutbox.id == outbox_id)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise BusinessException(code=SUBCONTRACT_STOCK_OUTBOX_NOT_FOUND, message="外发库存同步任务不存在")
        return row

    def latest_for_subcontract(
        self,
        *,
        subcontract_id: int,
        stock_action: str | None = None,
    ) -> LySubcontractStockOutbox | None:
        try:
            query = self.session.query(LySubcontractStockOutbox).filter(
                LySubcontractStockOutbox.subcontract_id == subcontract_id,
            )
            if stock_action is not None:
                query = query.filter(LySubcontractStockOutbox.stock_action == stock_action)
            return query.order_by(LySubcontractStockOutbox.id.desc()).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def latest_issue_for_subcontract(self, *, subcontract_id: int) -> LySubcontractStockOutbox | None:
        return self.latest_for_subcontract(subcontract_id=subcontract_id, stock_action=self.STOCK_ACTION_ISSUE)

    def latest_receipt_for_subcontract(self, *, subcontract_id: int) -> LySubcontractStockOutbox | None:
        return self.latest_for_subcontract(subcontract_id=subcontract_id, stock_action=self.STOCK_ACTION_RECEIPT)

    def ensure_retry_target_matches(
        self,
        *,
        row: LySubcontractStockOutbox,
        subcontract_id: int,
        stock_action: str,
        idempotency_key: str,
    ) -> None:
        if int(row.subcontract_id) != int(subcontract_id):
            raise BusinessException(
                code=SUBCONTRACT_STOCK_OUTBOX_ORDER_MISMATCH,
                message="库存同步任务不属于该外发单",
            )
        if str(row.stock_action or "").strip().lower() != stock_action.strip().lower():
            raise BusinessException(
                code=SUBCONTRACT_STOCK_OUTBOX_ACTION_MISMATCH,
                message="库存同步任务动作与请求不一致",
            )
        if str(row.idempotency_key or "") != idempotency_key:
            raise BusinessException(
                code=SUBCONTRACT_STOCK_OUTBOX_IDEMPOTENCY_MISMATCH,
                message="库存同步任务幂等键与请求不一致",
            )

    def ensure_retryable_status(self, *, row: LySubcontractStockOutbox) -> None:
        status_value = str(row.status or "").strip().lower()
        if status_value not in {self.STATUS_FAILED, self.STATUS_DEAD}:
            raise BusinessException(
                code=SUBCONTRACT_STOCK_OUTBOX_NOT_RETRYABLE,
                message="该库存同步任务状态不允许重试",
            )

    def reset_for_retry(
        self,
        *,
        row: LySubcontractStockOutbox,
        request_id: str,
        reset_attempts: bool = False,
    ) -> None:
        row.status = self.STATUS_PENDING
        if reset_attempts:
            row.attempts = 0
        row.locked_by = None
        row.locked_at = None
        row.lease_until = None
        row.next_retry_at = datetime.utcnow()
        row.last_error_code = None
        row.last_error_message = None
        row.request_id = request_id
        row.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def list_due_for_scope(
        self,
        *,
        scope: SubcontractWorkerScope,
        limit: int,
        now: datetime | None = None,
        stock_action: str | None = None,
    ) -> list[LySubcontractStockOutbox]:
        if limit <= 0:
            return []
        if not scope.companies or not scope.items or not scope.suppliers or not scope.warehouses:
            return []

        moment = now or datetime.utcnow()
        query = self.session.query(LySubcontractStockOutbox).filter(
            or_(
                LySubcontractStockOutbox.status.in_([self.STATUS_PENDING, self.STATUS_FAILED]),
                and_(
                    LySubcontractStockOutbox.status == self.STATUS_PROCESSING,
                    LySubcontractStockOutbox.lease_until.isnot(None),
                    LySubcontractStockOutbox.lease_until <= moment,
                ),
            ),
            LySubcontractStockOutbox.next_retry_at <= moment,
            LySubcontractStockOutbox.attempts < LySubcontractStockOutbox.max_attempts,
            LySubcontractStockOutbox.company.in_(sorted(scope.companies)),
            LySubcontractStockOutbox.item_code.in_(sorted(scope.items)),
            LySubcontractStockOutbox.supplier.in_(sorted(scope.suppliers)),
            LySubcontractStockOutbox.warehouse.in_(sorted(scope.warehouses)),
        )
        if stock_action is not None:
            query = query.filter(LySubcontractStockOutbox.stock_action == stock_action)
        return self._run_due_query(query=query, limit=limit)

    def _run_due_query(self, *, query, limit: int) -> list[LySubcontractStockOutbox]:
        try:
            return query.order_by(LySubcontractStockOutbox.id.asc()).limit(limit).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def list_due_issue_for_scope(
        self,
        *,
        scope: SubcontractWorkerScope,
        limit: int,
        now: datetime | None = None,
    ) -> list[LySubcontractStockOutbox]:
        return self.list_due_for_scope(
            scope=scope,
            limit=limit,
            now=now,
            stock_action=self.STOCK_ACTION_ISSUE,
        )

    def claim_by_ids(
        self,
        *,
        row_ids: list[int],
        worker_id: str,
        lease_seconds: int = 300,
        stock_action: str | None = None,
    ) -> list[LySubcontractStockOutbox]:
        if not row_ids:
            return []
        now = datetime.utcnow()
        query = self.session.query(LySubcontractStockOutbox).filter(
            LySubcontractStockOutbox.id.in_(row_ids),
            or_(
                LySubcontractStockOutbox.status.in_([self.STATUS_PENDING, self.STATUS_FAILED]),
                and_(
                    LySubcontractStockOutbox.status == self.STATUS_PROCESSING,
                    LySubcontractStockOutbox.lease_until.isnot(None),
                    LySubcontractStockOutbox.lease_until <= now,
                ),
            ),
            LySubcontractStockOutbox.next_retry_at <= now,
            LySubcontractStockOutbox.attempts < LySubcontractStockOutbox.max_attempts,
        )
        if stock_action is not None:
            query = query.filter(LySubcontractStockOutbox.stock_action == stock_action)
        query = query.order_by(LySubcontractStockOutbox.id.asc())

        try:
            rows = query.with_for_update(skip_locked=True).all()
        except Exception:
            try:
                rows = query.all()
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc

        lease_until = now + timedelta(seconds=max(30, lease_seconds))
        for row in rows:
            row.status = self.STATUS_PROCESSING
            row.locked_by = worker_id
            row.locked_at = now
            row.lease_until = lease_until
            row.updated_at = now

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return rows

    def claim_issue_by_ids(
        self,
        *,
        row_ids: list[int],
        worker_id: str,
        lease_seconds: int = 300,
    ) -> list[LySubcontractStockOutbox]:
        return self.claim_by_ids(
            row_ids=row_ids,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
            stock_action=self.STOCK_ACTION_ISSUE,
        )

    def get_processing_for_worker(
        self,
        *,
        outbox_id: int,
        worker_id: str,
        now: datetime | None = None,
        stock_action: str | None = None,
    ) -> LySubcontractStockOutbox | None:
        moment = now or datetime.utcnow()
        query = self.session.query(LySubcontractStockOutbox).filter(
            LySubcontractStockOutbox.id == outbox_id,
            LySubcontractStockOutbox.status == self.STATUS_PROCESSING,
            LySubcontractStockOutbox.locked_by == worker_id,
            or_(
                LySubcontractStockOutbox.lease_until.is_(None),
                LySubcontractStockOutbox.lease_until >= moment,
            ),
        )
        if stock_action is not None:
            query = query.filter(LySubcontractStockOutbox.stock_action == stock_action)
        query = query.order_by(LySubcontractStockOutbox.id.asc())
        try:
            try:
                return query.with_for_update(skip_locked=True).first()
            except Exception:
                return query.first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def get_processing_issue_for_worker(
        self,
        *,
        outbox_id: int,
        worker_id: str,
        now: datetime | None = None,
    ) -> LySubcontractStockOutbox | None:
        return self.get_processing_for_worker(
            outbox_id=outbox_id,
            worker_id=worker_id,
            now=now,
            stock_action=self.STOCK_ACTION_ISSUE,
        )

    def mark_succeeded(self, *, row: LySubcontractStockOutbox, stock_entry_name: str) -> int:
        attempt_no = int(row.attempts or 0) + 1
        row.status = self.STATUS_SUCCEEDED
        row.attempts = attempt_no
        row.stock_entry_name = stock_entry_name
        row.locked_by = None
        row.locked_at = None
        row.lease_until = None
        row.last_error_code = None
        row.last_error_message = None
        row.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return attempt_no

    def mark_failed(self, *, row: LySubcontractStockOutbox, error_code: str, error_message: str | None) -> int:
        attempt_no = int(row.attempts or 0) + 1
        row.attempts = attempt_no
        row.last_error_code = error_code
        row.last_error_message = (error_message or "")[:255] or None
        row.locked_by = None
        row.locked_at = None
        row.lease_until = None

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

    @classmethod
    def _backoff_minutes(cls, attempt_no: int) -> int:
        idx = max(0, attempt_no - 1)
        if idx >= len(cls.RETRY_MINUTES):
            return cls.RETRY_MINUTES[-1]
        return cls.RETRY_MINUTES[idx]
