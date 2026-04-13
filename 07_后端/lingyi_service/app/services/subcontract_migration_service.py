"""Subcontract company migration/backfill service (TASK-002C)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from sqlalchemy import and_
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import ERPNEXT_SERVICE_UNAVAILABLE
from app.core.error_codes import SUBCONTRACT_COMPANY_AMBIGUOUS
from app.core.error_codes import SUBCONTRACT_COMPANY_UNRESOLVED
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ERPNextServiceUnavailableError
from app.core.logging import log_safe_error
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.models.subcontract import LySubcontractStockOutbox
from app.models.subcontract import LySubcontractStockSyncLog
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubcontractCompanyBackfillPlanRow:
    """Single backfill plan row for subcontract order company scope."""

    order_id: int
    subcontract_no: str
    item_code: str
    old_company: str | None
    normalized_company: str | None
    planned_company: str | None
    planned_action: str
    reason_code: str


@dataclass(frozen=True)
class SubcontractCompanyBackfillReport:
    """Backfill report summary."""

    total_scanned: int
    backfilled_count: int
    blocked_count: int
    ambiguous_count: int
    unresolved_count: int
    unchanged_count: int


class SubcontractMigrationService:
    """Backfill local subcontract company facts from deterministic candidates."""

    def __init__(self, session: Session, erp_adapter: ERPNextJobCardAdapter | None = None):
        self.session = session
        self.erp_adapter = erp_adapter or ERPNextJobCardAdapter(use_service_account=True)

    def backfill_subcontract_company_scope(
        self,
        *,
        dry_run: bool = True,
        operator: str = "migration",
        limit: int | None = None,
    ) -> SubcontractCompanyBackfillReport:
        """Build+apply backfill plan.

        dry_run=True must remain read-only: no ORM mutations/add/delete.
        """
        try:
            with self.session.no_autoflush:
                plan = self.build_subcontract_company_backfill_plan(limit=limit)
                report = self._summarize(plan)
                if dry_run:
                    return report
                self._apply_plan(plan=plan, operator=operator)
        except (DatabaseReadFailed, ERPNextServiceUnavailableError):
            if not dry_run:
                self._rollback_safely(error_code=DATABASE_READ_FAILED)
            raise
        except DatabaseWriteFailed:
            if not dry_run:
                self._rollback_safely(error_code=DATABASE_WRITE_FAILED)
            raise
        except SQLAlchemyError as exc:
            if not dry_run:
                self._rollback_safely(error_code=DATABASE_WRITE_FAILED)
            raise DatabaseWriteFailed() from exc

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            if not dry_run:
                self._rollback_safely(error_code=DATABASE_WRITE_FAILED)
            raise DatabaseWriteFailed() from exc
        return report

    def build_subcontract_company_backfill_plan(
        self,
        *,
        limit: int | None = None,
    ) -> list[SubcontractCompanyBackfillPlanRow]:
        """Build read-only backfill plan rows."""
        try:
            query = (
                self.session.query(LySubcontractOrder)
                .filter(self._is_missing_company_expr(LySubcontractOrder.company))
                .order_by(LySubcontractOrder.id.asc())
            )
            if isinstance(limit, int) and limit > 0:
                query = query.limit(limit)
            rows = query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        plan: list[SubcontractCompanyBackfillPlanRow] = []
        for row in rows:
            item_code = str(row.item_code or "").strip()
            candidates = self._resolve_company_candidates(item_code=item_code)
            if len(candidates) == 1:
                plan.append(
                    SubcontractCompanyBackfillPlanRow(
                        order_id=int(row.id),
                        subcontract_no=str(row.subcontract_no),
                        item_code=item_code,
                        old_company=row.company,
                        normalized_company=self._normalize_company(row.company),
                        planned_company=sorted(candidates)[0],
                        planned_action="backfilled",
                        reason_code="unique_company",
                    )
                )
            elif len(candidates) > 1:
                plan.append(
                    SubcontractCompanyBackfillPlanRow(
                        order_id=int(row.id),
                        subcontract_no=str(row.subcontract_no),
                        item_code=item_code,
                        old_company=row.company,
                        normalized_company=self._normalize_company(row.company),
                        planned_company=None,
                        planned_action="blocked",
                        reason_code=SUBCONTRACT_COMPANY_AMBIGUOUS,
                    )
                )
            else:
                plan.append(
                    SubcontractCompanyBackfillPlanRow(
                        order_id=int(row.id),
                        subcontract_no=str(row.subcontract_no),
                        item_code=item_code,
                        old_company=row.company,
                        normalized_company=self._normalize_company(row.company),
                        planned_company=None,
                        planned_action="blocked",
                        reason_code=SUBCONTRACT_COMPANY_UNRESOLVED,
                    )
                )
        return plan

    def _resolve_company_candidates(self, *, item_code: str) -> set[str]:
        if not item_code:
            return set()

        candidates: set[str] = set()
        try:
            scoped_rows = (
                self.session.query(LySubcontractOrder.company)
                .filter(
                    and_(
                        LySubcontractOrder.item_code == item_code,
                        self._has_company_scope_expr(LySubcontractOrder.company),
                    )
                )
                .all()
            )
        except SQLAlchemyError as exc:
            log_safe_error(
                logger,
                "subcontract_company_candidates_read_failed",
                exc,
                extra={
                    "error_code": DATABASE_READ_FAILED,
                    "module": "subcontract",
                    "action": "subcontract:company_backfill",
                    "resource_type": "SubcontractOrder",
                    "resource_no": item_code,
                },
            )
            raise DatabaseReadFailed() from exc
        for (company_value,) in scoped_rows:
            if isinstance(company_value, str) and company_value.strip():
                candidates.add(company_value.strip())
        if candidates:
            return candidates

        try:
            item_info = self.erp_adapter.get_item(item_code=item_code)
        except ERPNextServiceUnavailableError as exc:
            log_safe_error(
                logger,
                "subcontract_company_candidates_erpnext_unavailable",
                exc,
                extra={
                    "error_code": ERPNEXT_SERVICE_UNAVAILABLE,
                    "module": "subcontract",
                    "action": "subcontract:company_backfill",
                    "resource_type": "Item",
                    "resource_no": item_code,
                },
            )
            raise

        if item_info and item_info.is_active:
            for value in item_info.companies:
                if value and value.strip():
                    candidates.add(value.strip())
        return candidates

    def _apply_plan(self, *, plan: list[SubcontractCompanyBackfillPlanRow], operator: str) -> None:
        del operator  # reserved for later operation-audit extension
        now = datetime.utcnow()

        for row_plan in plan:
            try:
                order = (
                    self.session.query(LySubcontractOrder)
                    .filter(LySubcontractOrder.id == row_plan.order_id)
                    .first()
                )
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc
            if order is None:
                continue
            if not self._is_missing_company(order.company):
                continue

            if row_plan.planned_action == "backfilled":
                order.company = row_plan.planned_company
                order.resource_scope_status = "ready"
                order.scope_error_code = None
                order.updated_at = now
                if row_plan.planned_company:
                    self._propagate_company_to_children(
                        subcontract_id=row_plan.order_id,
                        company=row_plan.planned_company,
                    )
                continue

            order.resource_scope_status = "blocked_scope"
            order.scope_error_code = row_plan.reason_code
            order.updated_at = now

    def _propagate_company_to_children(self, *, subcontract_id: int, company: str) -> None:
        """Fill missing company on child/outbox rows from parent order fact."""
        updates: list[Any] = [
            LySubcontractMaterial,
            LySubcontractReceipt,
            LySubcontractInspection,
            LySubcontractStatusLog,
            LySubcontractStockOutbox,
            LySubcontractStockSyncLog,
        ]
        for model in updates:
            filters = [model.subcontract_id == subcontract_id, self._is_missing_company_expr(model.company)]
            try:
                self.session.query(model).filter(and_(*filters)).update(
                    {"company": company},
                    synchronize_session=False,
                )
            except SQLAlchemyError as exc:
                raise DatabaseWriteFailed() from exc

    @staticmethod
    def _summarize(plan: list[SubcontractCompanyBackfillPlanRow]) -> SubcontractCompanyBackfillReport:
        return SubcontractCompanyBackfillReport(
            total_scanned=len(plan),
            backfilled_count=sum(1 for row in plan if row.planned_action == "backfilled"),
            blocked_count=sum(1 for row in plan if row.planned_action == "blocked"),
            ambiguous_count=sum(1 for row in plan if row.reason_code == SUBCONTRACT_COMPANY_AMBIGUOUS),
            unresolved_count=sum(1 for row in plan if row.reason_code == SUBCONTRACT_COMPANY_UNRESOLVED),
            unchanged_count=sum(1 for row in plan if row.planned_action == "unchanged"),
        )

    def _rollback_safely(self, *, error_code: str) -> None:
        try:
            self.session.rollback()
        except Exception as rollback_exc:  # pragma: no cover
            log_safe_error(
                logger,
                "subcontract_company_backfill_rollback_failed",
                rollback_exc,
                extra={
                    "error_code": error_code,
                    "module": "subcontract",
                    "action": "subcontract:company_backfill",
                },
            )

    @staticmethod
    def _normalize_company(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None

    @staticmethod
    def _is_missing_company(value: str | None) -> bool:
        return SubcontractMigrationService._normalize_company(value) is None

    @staticmethod
    def _is_missing_company_expr(column: Any):
        return or_(column.is_(None), func.trim(column) == "")

    @staticmethod
    def _has_company_scope_expr(column: Any):
        return and_(column.isnot(None), func.trim(column) != "")
