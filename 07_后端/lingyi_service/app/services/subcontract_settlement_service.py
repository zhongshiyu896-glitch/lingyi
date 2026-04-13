"""Settlement export service for subcontract inspections (TASK-002H)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
import hashlib
import json
from decimal import Decimal
from decimal import ROUND_HALF_UP
from typing import Any
from typing import Iterable
from typing import TypeVar

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import SUBCONTRACT_SETTLEMENT_CANDIDATE_NOT_FOUND
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_LOCKED
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_STATUS_INVALID
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import SubcontractSettlementAlreadyLockedError
from app.core.exceptions import SubcontractSettlementCandidateNotFoundError
from app.core.exceptions import SubcontractSettlementIdempotencyConflictError
from app.core.exceptions import SubcontractSettlementStatementRequiredError
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractSettlementOperation
from app.schemas.subcontract import SubcontractSettlementCandidateItem
from app.schemas.subcontract import SubcontractSettlementCandidatesData
from app.schemas.subcontract import SubcontractSettlementLockData
from app.schemas.subcontract import SubcontractSettlementPreviewData
from app.schemas.subcontract import SubcontractSettlementReleaseData
from app.schemas.subcontract import SubcontractSettlementSummary

TSettlementResponse = TypeVar("TSettlementResponse", SubcontractSettlementLockData, SubcontractSettlementReleaseData)


@dataclass(frozen=True)
class SettlementScopeRow:
    """Resource scope row for explicit inspection operations."""

    inspection_id: int
    subcontract_id: int
    subcontract_no: str
    company: str
    supplier: str
    item_code: str


class SettlementOperationDuplicateKeyError(Exception):
    """Raised when settlement operation unique(operation_type, idempotency_key) conflicts."""


class SubcontractSettlementService:
    """Settlement candidate/preview/lock/release service."""

    _SETTLEMENT_UNSETTLED = "unsettled"
    _SETTLEMENT_LOCKED = "statement_locked"
    _SETTLEMENT_SETTLED = "settled"
    _OPERATION_LOCK = "lock"
    _OPERATION_RELEASE = "release"

    def __init__(self, session: Session):
        self.session = session
        bind = getattr(session, "bind", None)
        self._is_sqlite = bool(bind and bind.dialect.name == "sqlite")

    def list_candidates(
        self,
        *,
        company: str | None,
        supplier: str | None,
        from_date: str | None,
        to_date: str | None,
        item_code: str | None,
        process_name: str | None,
        page: int,
        page_size: int,
        readable_item_codes: set[str] | None,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> SubcontractSettlementCandidatesData:
        """List eligible settlement candidates from inspection facts."""
        normalized_company = self._normalize_text(company)
        normalized_supplier = self._normalize_text(supplier)
        normalized_item_code = self._normalize_text(item_code)
        normalized_process = self._normalize_text(process_name)
        from_dt, to_dt = self._parse_date_range(from_date=from_date, to_date=to_date)

        query = self._eligible_candidates_query(
            settlement_status=self._SETTLEMENT_UNSETTLED,
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        if normalized_company:
            query = query.filter(LySubcontractOrder.company == normalized_company)
        if normalized_supplier:
            query = query.filter(LySubcontractOrder.supplier == normalized_supplier)
        if normalized_item_code:
            query = query.filter(LySubcontractOrder.item_code == normalized_item_code)
        if normalized_process:
            query = query.filter(LySubcontractOrder.process_name == normalized_process)
        if from_dt is not None:
            query = query.filter(LySubcontractInspection.inspected_at >= from_dt)
        if to_dt is not None:
            query = query.filter(LySubcontractInspection.inspected_at <= to_dt)

        try:
            summary = self._build_summary_from_query(query)
            total = summary.line_count
            rows = (
                query.order_by(LySubcontractInspection.inspected_at.desc(), LySubcontractInspection.id.desc())
                .offset(max(0, (page - 1) * page_size))
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        items = [self._to_candidate_item(inspection=inspection, order=order) for inspection, order in rows]
        return SubcontractSettlementCandidatesData(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            summary=summary,
        )

    def preview(
        self,
        *,
        inspection_ids: list[int] | None,
        company: str | None,
        supplier: str | None,
        from_date: str | None,
        to_date: str | None,
        item_code: str | None,
        process_name: str | None,
        readable_item_codes: set[str] | None,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> SubcontractSettlementPreviewData:
        """Preview settlement totals using inspection amount facts."""
        normalized_company = self._normalize_text(company)
        normalized_supplier = self._normalize_text(supplier)
        normalized_item_code = self._normalize_text(item_code)
        normalized_process = self._normalize_text(process_name)
        from_dt, to_dt = self._parse_date_range(from_date=from_date, to_date=to_date)

        query = self._eligible_candidates_query(
            settlement_status=self._SETTLEMENT_UNSETTLED,
            readable_item_codes=readable_item_codes,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        normalized_ids = self._normalize_ids(inspection_ids)
        if normalized_ids:
            query = query.filter(LySubcontractInspection.id.in_(normalized_ids))
        if normalized_company:
            query = query.filter(LySubcontractOrder.company == normalized_company)
        if normalized_supplier:
            query = query.filter(LySubcontractOrder.supplier == normalized_supplier)
        if normalized_item_code:
            query = query.filter(LySubcontractOrder.item_code == normalized_item_code)
        if normalized_process:
            query = query.filter(LySubcontractOrder.process_name == normalized_process)
        if from_dt is not None:
            query = query.filter(LySubcontractInspection.inspected_at >= from_dt)
        if to_dt is not None:
            query = query.filter(LySubcontractInspection.inspected_at <= to_dt)

        try:
            rows = query.order_by(LySubcontractInspection.inspected_at.asc(), LySubcontractInspection.id.asc()).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if normalized_ids and len(rows) != len(normalized_ids):
            raise SubcontractSettlementCandidateNotFoundError()

        items = [self._to_candidate_item(inspection=inspection, order=order) for inspection, order in rows]
        summary = self._build_summary(items)
        return SubcontractSettlementPreviewData(
            company=normalized_company,
            supplier=normalized_supplier,
            line_count=summary.line_count,
            total_qty=summary.total_qty,
            gross_amount=summary.gross_amount,
            deduction_amount=summary.deduction_amount,
            net_amount=summary.net_amount,
            items=items,
        )

    def list_scope_rows(self, *, inspection_ids: Iterable[int]) -> list[SettlementScopeRow]:
        """Load scope rows for explicit permission checks in router."""
        normalized_ids = self._normalize_ids(list(inspection_ids))
        if not normalized_ids:
            raise SubcontractSettlementCandidateNotFoundError()
        try:
            rows = (
                self.session.query(LySubcontractInspection, LySubcontractOrder)
                .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractInspection.subcontract_id)
                .filter(LySubcontractInspection.id.in_(normalized_ids))
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if len(rows) != len(normalized_ids):
            raise SubcontractSettlementCandidateNotFoundError()

        result: list[SettlementScopeRow] = []
        for inspection, order in rows:
            result.append(
                SettlementScopeRow(
                    inspection_id=int(inspection.id),
                    subcontract_id=int(order.id),
                    subcontract_no=str(order.subcontract_no),
                    company=str(order.company or "").strip(),
                    supplier=str(order.supplier or "").strip(),
                    item_code=str(order.item_code or "").strip(),
                )
            )
        return result

    def lock_inspections(
        self,
        *,
        statement_id: int | None,
        statement_no: str | None,
        inspection_ids: list[int],
        idempotency_key: str,
        operator: str,
        request_id: str,
    ) -> SubcontractSettlementLockData:
        """Lock settlement lines for a statement draft."""
        normalized_statement_no = self._normalize_text(statement_no)
        if statement_id is None and not normalized_statement_no:
            raise SubcontractSettlementStatementRequiredError()

        normalized_ids = self._normalize_ids(inspection_ids)
        if not normalized_ids:
            raise SubcontractSettlementCandidateNotFoundError()

        normalized_key = self._normalize_text(idempotency_key)
        if not normalized_key:
            raise SubcontractSettlementIdempotencyConflictError()
        request_hash = self._build_operation_request_hash(
            operation_type=self._OPERATION_LOCK,
            statement_id=statement_id,
            statement_no=normalized_statement_no,
            inspection_ids=normalized_ids,
            extra=None,
        )
        existing = self._load_operation(
            operation_type=self._OPERATION_LOCK,
            idempotency_key=normalized_key,
        )
        replay = self._try_build_idempotent_replay(
            existing=existing,
            request_hash=request_hash,
            operation_type=self._OPERATION_LOCK,
            idempotency_key=normalized_key,
            model_type=SubcontractSettlementLockData,
        )
        if replay is not None:
            return replay

        rows = self._load_inspection_rows_for_update(inspection_ids=normalized_ids)
        self._ensure_rows_found(rows=rows, expected_ids=normalized_ids)
        # Re-check after row lock to close concurrent race window.
        existing_after_lock = self._load_operation(
            operation_type=self._OPERATION_LOCK,
            idempotency_key=normalized_key,
        )
        replay_after_lock = self._try_build_idempotent_replay(
            existing=existing_after_lock,
            request_hash=request_hash,
            operation_type=self._OPERATION_LOCK,
            idempotency_key=normalized_key,
            model_type=SubcontractSettlementLockData,
        )
        if replay_after_lock is not None:
            return replay_after_lock

        now = datetime.utcnow()
        changed = False
        for inspection, order in rows:
            self._ensure_row_eligible_for_settlement(inspection=inspection, order=order)
            status = str(inspection.settlement_status or "").strip().lower()
            if status == self._SETTLEMENT_UNSETTLED:
                inspection.settlement_status = self._SETTLEMENT_LOCKED
                inspection.statement_id = statement_id
                inspection.statement_no = normalized_statement_no
                inspection.settlement_locked_by = operator
                inspection.settlement_locked_at = now
                inspection.settlement_request_id = normalized_key
                inspection.settled_by = None
                inspection.settled_at = None
                if not str(inspection.settlement_line_key or "").strip() and inspection.id is not None:
                    inspection.settlement_line_key = f"subcontract_inspection:{int(inspection.id)}"
                changed = True
                continue

            if status == self._SETTLEMENT_LOCKED:
                if self._same_statement(
                    inspection=inspection,
                    statement_id=statement_id,
                    statement_no=normalized_statement_no,
                ):
                    continue
                raise SubcontractSettlementAlreadyLockedError()

            if status in {self._SETTLEMENT_SETTLED, "adjusted", "cancelled"}:
                raise SubcontractSettlementAlreadyLockedError()

            raise BusinessException(
                code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                message="结算明细状态不允许锁定",
            )

        if changed:
            try:
                self.session.flush()
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc

        items = [self._to_candidate_item(inspection=inspection, order=order) for inspection, order in rows]
        summary = self._build_summary(items)
        base_result = SubcontractSettlementLockData(
            operation_id=0,
            idempotency_key=normalized_key,
            idempotent_replay=False,
            locked_count=summary.line_count,
            gross_amount=summary.gross_amount,
            deduction_amount=summary.deduction_amount,
            net_amount=summary.net_amount,
            locked_items=items,
        )
        try:
            operation = self._record_operation_success(
                operation_type=self._OPERATION_LOCK,
                idempotency_key=normalized_key,
                request_hash=request_hash,
                statement_id=statement_id,
                statement_no=normalized_statement_no,
                inspection_ids=normalized_ids,
                affected_inspection_ids=[int(item.inspection_id) for item in base_result.locked_items],
                response_data=base_result.model_dump(mode="json"),
                operator=operator,
                request_id=request_id,
            )
        except SettlementOperationDuplicateKeyError:
            # Another request committed first with same unique key.
            self.session.rollback()
            existing_after_conflict = self._load_operation(
                operation_type=self._OPERATION_LOCK,
                idempotency_key=normalized_key,
            )
            replay_after_conflict = self._try_build_idempotent_replay(
                existing=existing_after_conflict,
                request_hash=request_hash,
                operation_type=self._OPERATION_LOCK,
                idempotency_key=normalized_key,
                model_type=SubcontractSettlementLockData,
            )
            if replay_after_conflict is not None:
                return replay_after_conflict
            raise SubcontractSettlementIdempotencyConflictError()

        return base_result.model_copy(
            update={
                "operation_id": int(operation.id),
                "idempotency_key": normalized_key,
                "idempotent_replay": False,
            }
        )

    def release_locks(
        self,
        *,
        statement_id: int | None,
        statement_no: str | None,
        inspection_ids: list[int],
        idempotency_key: str,
        reason: str | None,
        operator: str,
        request_id: str,
    ) -> SubcontractSettlementReleaseData:
        """Release statement locks from unsettled lines."""
        normalized_statement_no = self._normalize_text(statement_no)
        if statement_id is None and not normalized_statement_no:
            raise SubcontractSettlementStatementRequiredError()

        normalized_ids = self._normalize_ids(inspection_ids)
        if not normalized_ids:
            raise SubcontractSettlementCandidateNotFoundError()

        normalized_key = self._normalize_text(idempotency_key)
        if not normalized_key:
            raise SubcontractSettlementIdempotencyConflictError()
        request_hash = self._build_operation_request_hash(
            operation_type=self._OPERATION_RELEASE,
            statement_id=statement_id,
            statement_no=normalized_statement_no,
            inspection_ids=normalized_ids,
            extra={"reason": self._normalize_text(reason)},
        )
        existing = self._load_operation(
            operation_type=self._OPERATION_RELEASE,
            idempotency_key=normalized_key,
        )
        replay = self._try_build_idempotent_replay(
            existing=existing,
            request_hash=request_hash,
            operation_type=self._OPERATION_RELEASE,
            idempotency_key=normalized_key,
            model_type=SubcontractSettlementReleaseData,
        )
        if replay is not None:
            return replay

        rows = self._load_inspection_rows_for_update(inspection_ids=normalized_ids)
        self._ensure_rows_found(rows=rows, expected_ids=normalized_ids)
        # Re-check after row lock to close concurrent race window.
        existing_after_lock = self._load_operation(
            operation_type=self._OPERATION_RELEASE,
            idempotency_key=normalized_key,
        )
        replay_after_lock = self._try_build_idempotent_replay(
            existing=existing_after_lock,
            request_hash=request_hash,
            operation_type=self._OPERATION_RELEASE,
            idempotency_key=normalized_key,
            model_type=SubcontractSettlementReleaseData,
        )
        if replay_after_lock is not None:
            return replay_after_lock
        changed = False
        for inspection, order in rows:
            self._ensure_row_eligible_for_settlement(inspection=inspection, order=order)
            status = str(inspection.settlement_status or "").strip().lower()

            if status == self._SETTLEMENT_SETTLED:
                raise BusinessException(
                    code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                    message="已结算明细不允许释放锁定",
                )

            if status == self._SETTLEMENT_UNSETTLED:
                # idempotent release retry: already unlocked and statement refs cleared.
                if inspection.statement_id is None and self._normalize_text(inspection.statement_no) is None:
                    continue
                raise BusinessException(
                    code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                    message="结算明细状态不允许释放",
                )

            if status != self._SETTLEMENT_LOCKED:
                raise BusinessException(
                    code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                    message="结算明细状态不允许释放",
                )

            if not self._same_statement(
                inspection=inspection,
                statement_id=statement_id,
                statement_no=normalized_statement_no,
            ):
                raise BusinessException(
                    code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                    message="结算明细不属于当前对账单",
                )

            inspection.settlement_status = self._SETTLEMENT_UNSETTLED
            inspection.statement_id = None
            inspection.statement_no = None
            inspection.settlement_locked_by = None
            inspection.settlement_locked_at = None
            inspection.settlement_request_id = normalized_key
            inspection.settled_by = None
            inspection.settled_at = None
            if not str(inspection.settlement_line_key or "").strip() and inspection.id is not None:
                inspection.settlement_line_key = f"subcontract_inspection:{int(inspection.id)}"
            changed = True

        if changed:
            try:
                self.session.flush()
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc

        items = [self._to_candidate_item(inspection=inspection, order=order) for inspection, order in rows]
        base_result = SubcontractSettlementReleaseData(
            operation_id=0,
            idempotency_key=normalized_key,
            idempotent_replay=False,
            released_count=len(items),
            released_items=items,
        )
        try:
            operation = self._record_operation_success(
                operation_type=self._OPERATION_RELEASE,
                idempotency_key=normalized_key,
                request_hash=request_hash,
                statement_id=statement_id,
                statement_no=normalized_statement_no,
                inspection_ids=normalized_ids,
                affected_inspection_ids=[int(item.inspection_id) for item in base_result.released_items],
                response_data=base_result.model_dump(mode="json"),
                operator=operator,
                request_id=request_id,
            )
        except SettlementOperationDuplicateKeyError:
            self.session.rollback()
            existing_after_conflict = self._load_operation(
                operation_type=self._OPERATION_RELEASE,
                idempotency_key=normalized_key,
            )
            replay_after_conflict = self._try_build_idempotent_replay(
                existing=existing_after_conflict,
                request_hash=request_hash,
                operation_type=self._OPERATION_RELEASE,
                idempotency_key=normalized_key,
                model_type=SubcontractSettlementReleaseData,
            )
            if replay_after_conflict is not None:
                return replay_after_conflict
            raise SubcontractSettlementIdempotencyConflictError()

        return base_result.model_copy(
            update={
                "operation_id": int(operation.id),
                "idempotency_key": normalized_key,
                "idempotent_replay": False,
            }
        )

    def _eligible_candidates_query(
        self,
        *,
        settlement_status: str,
        readable_item_codes: set[str] | None,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ):
        receipt_synced = self._receipt_synced_exists_condition()
        receipt_unsynced = self._receipt_unsynced_exists_condition()

        query = (
            self.session.query(LySubcontractInspection, LySubcontractOrder)
            .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractInspection.subcontract_id)
            .filter(func.lower(func.coalesce(LySubcontractInspection.status, "")) == "inspected")
            .filter(func.lower(func.coalesce(LySubcontractInspection.settlement_status, "")) == settlement_status)
            .filter(func.coalesce(LySubcontractInspection.net_amount, 0) >= 0)
            .filter(func.lower(func.coalesce(LySubcontractOrder.status, "")).notin_(["draft", "cancelled"]))
            .filter(func.lower(func.coalesce(LySubcontractOrder.resource_scope_status, "")) == "ready")
            .filter(LySubcontractOrder.company.isnot(None))
            .filter(self._trim_expr(LySubcontractOrder.company) != "")
            .filter(receipt_synced)
            .filter(~receipt_unsynced)
        )

        if readable_item_codes is not None:
            if not readable_item_codes:
                return query.filter(False)
            query = query.filter(LySubcontractOrder.item_code.in_(sorted(readable_item_codes)))
        if readable_companies is not None:
            if not readable_companies:
                return query.filter(False)
            query = query.filter(LySubcontractOrder.company.in_(sorted(readable_companies)))
        if readable_suppliers is not None:
            if not readable_suppliers:
                return query.filter(False)
            query = query.filter(LySubcontractOrder.supplier.in_(sorted(readable_suppliers)))

        return query

    def _receipt_synced_exists_condition(self):
        return self.session.query(LySubcontractReceipt.id).filter(
            LySubcontractReceipt.subcontract_id == LySubcontractInspection.subcontract_id,
            LySubcontractReceipt.receipt_batch_no == LySubcontractInspection.receipt_batch_no,
            func.lower(func.coalesce(LySubcontractReceipt.sync_status, "")) == "succeeded",
            LySubcontractReceipt.stock_entry_name.isnot(None),
            self._trim_expr(LySubcontractReceipt.stock_entry_name) != "",
        ).exists()

    def _receipt_unsynced_exists_condition(self):
        return self.session.query(LySubcontractReceipt.id).filter(
            LySubcontractReceipt.subcontract_id == LySubcontractInspection.subcontract_id,
            LySubcontractReceipt.receipt_batch_no == LySubcontractInspection.receipt_batch_no,
            or_(
                func.lower(func.coalesce(LySubcontractReceipt.sync_status, "")) != "succeeded",
                LySubcontractReceipt.stock_entry_name.is_(None),
                self._trim_expr(LySubcontractReceipt.stock_entry_name) == "",
            ),
        ).exists()

    def _load_inspection_rows_for_update(self, *, inspection_ids: list[int]):
        try:
            query = (
                self.session.query(LySubcontractInspection, LySubcontractOrder)
                .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractInspection.subcontract_id)
                .filter(LySubcontractInspection.id.in_(inspection_ids))
                .order_by(LySubcontractInspection.id.asc())
            )
            if not self._is_sqlite:
                query = query.with_for_update()
            return query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    @staticmethod
    def _ensure_rows_found(*, rows, expected_ids: list[int]) -> None:
        found_ids = {int(inspection.id) for inspection, _ in rows}
        if found_ids == set(expected_ids):
            return
        raise SubcontractSettlementCandidateNotFoundError()

    def _load_operation(
        self,
        *,
        operation_type: str,
        idempotency_key: str,
    ) -> LySubcontractSettlementOperation | None:
        try:
            return (
                self.session.query(LySubcontractSettlementOperation)
                .filter(
                    LySubcontractSettlementOperation.operation_type == operation_type,
                    LySubcontractSettlementOperation.idempotency_key == idempotency_key,
                )
                .order_by(LySubcontractSettlementOperation.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _try_build_idempotent_replay(
        self,
        *,
        existing: LySubcontractSettlementOperation | None,
        request_hash: str,
        operation_type: str,
        idempotency_key: str,
        model_type: type[TSettlementResponse],
    ) -> TSettlementResponse | None:
        if existing is None:
            return None

        if str(existing.operation_type or "") != operation_type:
            raise SubcontractSettlementIdempotencyConflictError()

        if str(existing.idempotency_key or "") != idempotency_key:
            raise SubcontractSettlementIdempotencyConflictError()

        if str(existing.request_hash or "") != request_hash:
            raise SubcontractSettlementIdempotencyConflictError()

        payload = existing.response_json
        if not isinstance(payload, dict):
            raise SubcontractSettlementIdempotencyConflictError()

        replay_payload = dict(payload)
        replay_payload["operation_id"] = int(existing.id)
        replay_payload["idempotency_key"] = idempotency_key
        replay_payload["idempotent_replay"] = True

        try:
            return model_type.model_validate(replay_payload)
        except Exception as exc:  # pragma: no cover - defensive branch
            raise SubcontractSettlementIdempotencyConflictError() from exc

    def _record_operation_success(
        self,
        *,
        operation_type: str,
        idempotency_key: str,
        request_hash: str,
        statement_id: int | None,
        statement_no: str | None,
        inspection_ids: list[int],
        affected_inspection_ids: list[int],
        response_data: dict[str, Any],
        operator: str,
        request_id: str,
    ) -> LySubcontractSettlementOperation:
        row = LySubcontractSettlementOperation(
            operation_type=operation_type,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            statement_id=statement_id,
            statement_no=statement_no,
            inspection_ids_json=self._to_json_safe(inspection_ids),
            result_status="succeeded",
            affected_inspection_ids_json=self._to_json_safe(affected_inspection_ids),
            response_json=self._to_json_safe(response_data),
            operator=operator,
            request_id=request_id,
        )
        self.session.add(row)
        try:
            self.session.flush()
        except IntegrityError as exc:
            if self._is_operation_unique_conflict(exc):
                raise SettlementOperationDuplicateKeyError() from exc
            raise DatabaseWriteFailed() from exc
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return row

    def _ensure_row_eligible_for_settlement(
        self,
        *,
        inspection: LySubcontractInspection,
        order: LySubcontractOrder,
    ) -> None:
        inspection_status = str(inspection.status or "").strip().lower()
        if inspection_status != "inspected":
            raise BusinessException(
                code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                message="仅已验货明细可进入对账",
            )

        if Decimal(str(inspection.net_amount or "0")) < Decimal("0"):
            raise BusinessException(
                code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                message="净应付金额非法，不能进入结算",
            )

        order_status = str(order.status or "").strip().lower()
        if order_status in {"draft", "cancelled"}:
            raise BusinessException(
                code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                message="外发单状态不允许结算",
            )

        scope_status = str(order.resource_scope_status or "").strip().lower()
        if scope_status != "ready":
            raise BusinessException(
                code=SUBCONTRACT_SCOPE_BLOCKED,
                message="外发单资源范围异常，禁止结算",
            )

        if self._normalize_text(order.company) is None:
            raise BusinessException(
                code=SUBCONTRACT_SCOPE_BLOCKED,
                message="外发单缺少 company 资源范围",
            )

        if not self._is_receipt_batch_synced(
            subcontract_id=int(inspection.subcontract_id),
            receipt_batch_no=str(inspection.receipt_batch_no or ""),
        ):
            raise BusinessException(
                code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                message="回料批次尚未同步成功，不能进入结算",
            )

    def _is_receipt_batch_synced(self, *, subcontract_id: int, receipt_batch_no: str) -> bool:
        normalized_batch = self._normalize_text(receipt_batch_no)
        if not normalized_batch:
            return False

        try:
            rows = (
                self.session.query(LySubcontractReceipt)
                .filter(
                    LySubcontractReceipt.subcontract_id == subcontract_id,
                    LySubcontractReceipt.receipt_batch_no == normalized_batch,
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if not rows:
            return False

        for row in rows:
            status = str(row.sync_status or "").strip().lower()
            stock_entry_name = self._normalize_text(row.stock_entry_name)
            if status != "succeeded" or stock_entry_name is None:
                return False
        return True

    def _to_candidate_item(
        self,
        *,
        inspection: LySubcontractInspection,
        order: LySubcontractOrder,
    ) -> SubcontractSettlementCandidateItem:
        return SubcontractSettlementCandidateItem(
            inspection_id=int(inspection.id),
            settlement_line_key=self._normalize_text(inspection.settlement_line_key),
            subcontract_id=int(order.id),
            subcontract_no=str(order.subcontract_no),
            company=str(order.company),
            supplier=str(order.supplier),
            item_code=str(order.item_code),
            process_name=str(order.process_name),
            receipt_batch_no=str(inspection.receipt_batch_no or ""),
            inspected_at=inspection.inspected_at,
            inspected_by=(self._normalize_text(inspection.inspected_by)),
            inspected_qty=Decimal(str(inspection.inspected_qty or "0")),
            accepted_qty=Decimal(str(inspection.accepted_qty or "0")),
            rejected_qty=Decimal(str(inspection.rejected_qty or "0")),
            rejected_rate=Decimal(str(inspection.rejected_rate or "0")),
            subcontract_rate=Decimal(str(inspection.subcontract_rate or "0")),
            gross_amount=Decimal(str(inspection.gross_amount or "0")),
            deduction_amount=Decimal(str(inspection.deduction_amount or "0")),
            net_amount=Decimal(str(inspection.net_amount or "0")),
            settlement_status=str(inspection.settlement_status or ""),
            statement_id=(int(inspection.statement_id) if inspection.statement_id is not None else None),
            statement_no=self._normalize_text(inspection.statement_no),
        )

    @staticmethod
    def _normalize_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_ids(values: list[int] | None) -> list[int]:
        if not values:
            return []
        normalized = sorted({int(value) for value in values if int(value) > 0})
        return normalized

    @classmethod
    def _parse_date_range(cls, *, from_date: str | None, to_date: str | None) -> tuple[datetime | None, datetime | None]:
        return cls._parse_from_date(from_date), cls._parse_to_date(to_date)

    @classmethod
    def _parse_from_date(cls, value: str | None) -> datetime | None:
        normalized = cls._normalize_text(value)
        if not normalized:
            return None
        try:
            if "T" in normalized:
                return datetime.fromisoformat(normalized)
            parsed = date.fromisoformat(normalized)
            return datetime(parsed.year, parsed.month, parsed.day, 0, 0, 0)
        except ValueError as exc:
            raise BusinessException(
                code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                message="from_date 格式非法",
            ) from exc

    @classmethod
    def _parse_to_date(cls, value: str | None) -> datetime | None:
        normalized = cls._normalize_text(value)
        if not normalized:
            return None
        try:
            if "T" in normalized:
                return datetime.fromisoformat(normalized)
            parsed = date.fromisoformat(normalized)
            return datetime(parsed.year, parsed.month, parsed.day, 23, 59, 59)
        except ValueError as exc:
            raise BusinessException(
                code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID,
                message="to_date 格式非法",
            ) from exc

    @staticmethod
    def _same_statement(
        *,
        inspection: LySubcontractInspection,
        statement_id: int | None,
        statement_no: str | None,
    ) -> bool:
        row_statement_id = int(inspection.statement_id) if inspection.statement_id is not None else None
        row_statement_no = str(inspection.statement_no).strip() if inspection.statement_no else None

        if statement_id is not None and row_statement_id != int(statement_id):
            return False
        if statement_no is not None and row_statement_no != statement_no:
            return False
        if statement_id is None and statement_no is None:
            return row_statement_id is None and row_statement_no is None
        return True

    @classmethod
    def _build_summary(cls, items: list[SubcontractSettlementCandidateItem]) -> SubcontractSettlementSummary:
        total_qty = Decimal("0")
        gross_amount = Decimal("0")
        deduction_amount = Decimal("0")
        net_amount = Decimal("0")

        for item in items:
            total_qty += Decimal(str(item.inspected_qty))
            gross_amount += Decimal(str(item.gross_amount))
            deduction_amount += Decimal(str(item.deduction_amount))
            net_amount += Decimal(str(item.net_amount))

        return SubcontractSettlementSummary(
            line_count=len(items),
            total_qty=cls._quantize_qty(total_qty),
            gross_amount=cls._quantize_money(gross_amount),
            deduction_amount=cls._quantize_money(deduction_amount),
            net_amount=cls._quantize_money(net_amount),
        )

    @classmethod
    def _build_summary_from_query(cls, query) -> SubcontractSettlementSummary:
        aggregate_query = query.with_entities(
            func.count(LySubcontractInspection.id),
            func.coalesce(func.sum(LySubcontractInspection.inspected_qty), 0),
            func.coalesce(func.sum(LySubcontractInspection.gross_amount), 0),
            func.coalesce(func.sum(LySubcontractInspection.deduction_amount), 0),
            func.coalesce(func.sum(LySubcontractInspection.net_amount), 0),
        )
        line_count, total_qty, gross_amount, deduction_amount, net_amount = aggregate_query.one()
        return SubcontractSettlementSummary(
            line_count=int(line_count or 0),
            total_qty=cls._quantize_qty(Decimal(str(total_qty or "0"))),
            gross_amount=cls._quantize_money(Decimal(str(gross_amount or "0"))),
            deduction_amount=cls._quantize_money(Decimal(str(deduction_amount or "0"))),
            net_amount=cls._quantize_money(Decimal(str(net_amount or "0"))),
        )

    @classmethod
    def _build_operation_request_hash(
        cls,
        *,
        operation_type: str,
        statement_id: int | None,
        statement_no: str | None,
        inspection_ids: list[int],
        extra: dict[str, Any] | None,
    ) -> str:
        normalized_ids = sorted({int(value) for value in inspection_ids if int(value) > 0})
        payload: dict[str, Any] = {
            "operation_type": operation_type,
            "statement_id": int(statement_id) if statement_id is not None else None,
            "statement_no": cls._normalize_text(statement_no),
            "inspection_ids": normalized_ids,
        }
        if extra:
            payload["extra"] = extra
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _to_json_safe(value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))

    @staticmethod
    def _is_operation_unique_conflict(exc: IntegrityError) -> bool:
        raw = f"{exc}"
        orig = getattr(exc, "orig", None)
        if orig is not None:
            raw = f"{raw} {orig}"
        lowered = raw.lower()
        return "uk_ly_subcontract_settlement_operation_idem" in lowered or (
            "ly_subcontract_settlement_operation.operation_type" in lowered
            and "ly_subcontract_settlement_operation.idempotency_key" in lowered
        )

    @staticmethod
    def _quantize_money(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _quantize_qty(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def _trim_expr(self, column):
        if self._is_sqlite:
            return func.trim(column)
        return func.btrim(column)
