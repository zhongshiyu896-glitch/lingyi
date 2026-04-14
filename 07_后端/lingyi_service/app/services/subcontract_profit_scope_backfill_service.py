"""Backfill subcontract profit-scope bridge fields (TASK-005F2)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.production import LyProductionPlan
from app.models.production import LyProductionWorkOrderLink
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService


@dataclass(frozen=True)
class SubcontractProfitScopeBackfillPlanRow:
    """Single subcontract order scope backfill plan row."""

    order_id: int
    subcontract_no: str
    planned_status: str
    planned_reason_code: str | None
    planned_sales_order: str | None
    planned_sales_order_item: str | None
    planned_production_plan_id: int | None
    planned_work_order: str | None


@dataclass(frozen=True)
class SubcontractProfitScopeBackfillReport:
    """Backfill execution report."""

    total_scanned: int
    ready_count: int
    unresolved_count: int
    ambiguous_count: int
    untrusted_count: int
    updated_count: int


class SubcontractProfitScopeBackfillService:
    """Backfill historical subcontract profit-scope bridge fields safely."""

    def __init__(self, session: Session):
        self.session = session

    def backfill(
        self,
        *,
        dry_run: bool = True,
        operator: str = "migration",
        limit: int | None = None,
        request_id: str | None = None,
        company: str | None = None,
        item_code: str | None = None,
    ) -> SubcontractProfitScopeBackfillReport:
        """Build+apply backfill plan.

        dry_run=True must stay read-only even if caller commits later.
        """
        try:
            with self.session.no_autoflush:
                plan = self.build_plan(limit=limit)
                if dry_run:
                    return self._summarize(plan=plan, updated_count=0)
                with self.session.begin_nested():
                    updated_count = self._apply_plan(plan=plan)
                    self.session.flush()
                    report = self._summarize(plan=plan, updated_count=updated_count)
                    self._record_execute_audit(
                        operator=operator,
                        report=report,
                        request_id=request_id,
                        limit=limit,
                        company=company,
                        item_code=item_code,
                    )
                return report
        except AuditWriteFailed:
            self._rollback_safely()
            raise
        except DatabaseReadFailed:
            self._rollback_safely()
            raise
        except SQLAlchemyError as exc:
            self._rollback_safely()
            raise DatabaseWriteFailed() from exc

    def execute(
        self,
        *,
        operator: str = "migration",
        limit: int | None = None,
        request_id: str | None = None,
        company: str | None = None,
        item_code: str | None = None,
    ) -> SubcontractProfitScopeBackfillReport:
        """Execute write mode with operation-audit guarantee."""
        return self.backfill(
            dry_run=False,
            operator=operator,
            limit=limit,
            request_id=request_id,
            company=company,
            item_code=item_code,
        )

    def build_plan(self, *, limit: int | None = None) -> list[SubcontractProfitScopeBackfillPlanRow]:
        """Build read-only backfill plan for unresolved/empty bridge rows."""
        try:
            query = (
                self.session.query(LySubcontractOrder)
                .filter(
                    or_(
                        LySubcontractOrder.profit_scope_status != "ready",
                        LySubcontractOrder.sales_order.is_(None),
                        func.trim(LySubcontractOrder.sales_order) == "",
                    )
                )
                .order_by(LySubcontractOrder.id.asc())
            )
            if isinstance(limit, int) and limit > 0:
                query = query.limit(limit)
            rows = query.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        plan_rows: list[SubcontractProfitScopeBackfillPlanRow] = []
        for row in rows:
            planned_status, reason_code, sales_order, sales_order_item, plan_id, work_order = self._resolve_scope(row)
            plan_rows.append(
                SubcontractProfitScopeBackfillPlanRow(
                    order_id=int(row.id),
                    subcontract_no=str(row.subcontract_no),
                    planned_status=planned_status,
                    planned_reason_code=reason_code,
                    planned_sales_order=sales_order,
                    planned_sales_order_item=sales_order_item,
                    planned_production_plan_id=plan_id,
                    planned_work_order=work_order,
                )
            )
        return plan_rows

    def _resolve_scope(
        self,
        row: LySubcontractOrder,
    ) -> tuple[str, str | None, str | None, str | None, int | None, str | None]:
        try:
            plan_rows = (
                self.session.query(LyProductionPlan)
                .filter(
                    LyProductionPlan.company == self._normalize_text(row.company),
                    LyProductionPlan.item_code == self._normalize_text(row.item_code),
                    LyProductionPlan.bom_id == int(row.bom_id),
                )
                .order_by(LyProductionPlan.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if len(plan_rows) == 0:
            return "unresolved", "SUBCONTRACT_SCOPE_UNTRUSTED", None, None, None, None
        if len(plan_rows) > 1:
            return "unresolved", "SUBCONTRACT_SCOPE_AMBIGUOUS", None, None, None, None

        plan = plan_rows[0]
        try:
            work_links = (
                self.session.query(LyProductionWorkOrderLink)
                .filter(LyProductionWorkOrderLink.plan_id == int(plan.id))
                .order_by(LyProductionWorkOrderLink.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        if len(work_links) == 0:
            return (
                "unresolved",
                "SUBCONTRACT_SCOPE_UNTRUSTED",
                self._normalize_text(plan.sales_order) or None,
                self._normalize_text(plan.sales_order_item) or None,
                int(plan.id),
                None,
            )
        if len(work_links) > 1:
            return (
                "unresolved",
                "SUBCONTRACT_SCOPE_AMBIGUOUS",
                self._normalize_text(plan.sales_order) or None,
                self._normalize_text(plan.sales_order_item) or None,
                int(plan.id),
                None,
            )

        return (
            "ready",
            None,
            self._normalize_text(plan.sales_order) or None,
            self._normalize_text(plan.sales_order_item) or None,
            int(plan.id),
            self._normalize_text(work_links[0].work_order) or None,
        )

    def _apply_plan(self, *, plan: list[SubcontractProfitScopeBackfillPlanRow]) -> int:
        updated_count = 0
        now = datetime.utcnow()
        for plan_row in plan:
            try:
                order = (
                    self.session.query(LySubcontractOrder)
                    .filter(LySubcontractOrder.id == plan_row.order_id)
                    .first()
                )
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc
            if order is None:
                continue

            before_state = (
                self._normalize_text(order.sales_order),
                self._normalize_text(order.sales_order_item),
                int(order.production_plan_id) if order.production_plan_id is not None else None,
                self._normalize_text(order.work_order),
                self._normalize_text(order.profit_scope_status),
                self._normalize_text(order.profit_scope_error_code),
            )
            if plan_row.planned_status == "ready":
                order.sales_order = plan_row.planned_sales_order
                order.sales_order_item = plan_row.planned_sales_order_item
                order.production_plan_id = plan_row.planned_production_plan_id
                order.work_order = plan_row.planned_work_order
                order.profit_scope_status = "ready"
                order.profit_scope_error_code = None
                order.profit_scope_resolved_at = now
            else:
                order.profit_scope_status = "unresolved"
                order.profit_scope_error_code = plan_row.planned_reason_code or "SUBCONTRACT_SCOPE_UNTRUSTED"
                order.profit_scope_resolved_at = None

            after_state = (
                self._normalize_text(order.sales_order),
                self._normalize_text(order.sales_order_item),
                int(order.production_plan_id) if order.production_plan_id is not None else None,
                self._normalize_text(order.work_order),
                self._normalize_text(order.profit_scope_status),
                self._normalize_text(order.profit_scope_error_code),
            )
            if before_state != after_state:
                updated_count += 1

            updated_count += self._apply_inspection_snapshot_backfill(order=order, plan_row=plan_row)
        return updated_count

    def _apply_inspection_snapshot_backfill(
        self,
        *,
        order: LySubcontractOrder,
        plan_row: SubcontractProfitScopeBackfillPlanRow,
    ) -> int:
        try:
            inspection_rows = (
                self.session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.subcontract_id == int(order.id))
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        changed_count = 0
        for inspection in inspection_rows:
            has_scope = self._has_scope_snapshot(inspection)
            if has_scope:
                continue

            inspection.sales_order = plan_row.planned_sales_order
            inspection.sales_order_item = plan_row.planned_sales_order_item
            inspection.production_plan_id = plan_row.planned_production_plan_id
            inspection.work_order = plan_row.planned_work_order
            inspection.job_card = self._normalize_text(order.job_card) or None
            inspection.profit_scope_status = plan_row.planned_status
            inspection.profit_scope_error_code = (
                None if plan_row.planned_status == "ready" else plan_row.planned_reason_code
            )
            changed_count += 1
        return changed_count

    @staticmethod
    def _has_scope_snapshot(inspection: LySubcontractInspection) -> bool:
        return any(
            (
                SubcontractProfitScopeBackfillService._normalize_text(inspection.sales_order),
                SubcontractProfitScopeBackfillService._normalize_text(inspection.work_order),
                inspection.production_plan_id is not None,
            )
        )

    @staticmethod
    def _normalize_text(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _summarize(
        *,
        plan: list[SubcontractProfitScopeBackfillPlanRow],
        updated_count: int,
    ) -> SubcontractProfitScopeBackfillReport:
        ready_count = sum(1 for row in plan if row.planned_status == "ready")
        unresolved_count = sum(1 for row in plan if row.planned_status != "ready")
        ambiguous_count = sum(1 for row in plan if row.planned_reason_code == "SUBCONTRACT_SCOPE_AMBIGUOUS")
        untrusted_count = sum(1 for row in plan if row.planned_reason_code == "SUBCONTRACT_SCOPE_UNTRUSTED")
        return SubcontractProfitScopeBackfillReport(
            total_scanned=len(plan),
            ready_count=ready_count,
            unresolved_count=unresolved_count,
            ambiguous_count=ambiguous_count,
            untrusted_count=untrusted_count,
            updated_count=updated_count,
        )

    def _record_execute_audit(
        self,
        *,
        operator: str,
        report: SubcontractProfitScopeBackfillReport,
        request_id: str | None,
        limit: int | None,
        company: str | None,
        item_code: str | None,
    ) -> None:
        context = AuditContext(
            request_id=(request_id or f"subcontract-profit-scope-backfill-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}")[
                :64
            ],
            ip_address=None,
            user_agent="subcontract_profit_scope_backfill_service",
        )
        AuditService(self.session).record_success(
            module="subcontract",
            action="subcontract:profit_scope_backfill",
            operator=self._normalize_text(operator) or "migration",
            operator_roles=["system"],
            resource_type="SUBCONTRACT_PROFIT_SCOPE_BACKFILL",
            resource_id=None,
            resource_no=None,
            before_data={
                "dry_run": False,
                "limit": limit,
                "company": self._normalize_text(company) or None,
                "item_code": self._normalize_text(item_code) or None,
            },
            after_data={
                "dry_run": False,
                "total_scanned": report.total_scanned,
                "ready_count": report.ready_count,
                "unresolved_count": report.unresolved_count,
                "ambiguous_count": report.ambiguous_count,
                "untrusted_count": report.untrusted_count,
                "updated_count": report.updated_count,
            },
            context=context,
        )

    def _rollback_safely(self) -> None:
        try:
            self.session.rollback()
        except Exception:  # pragma: no cover
            return
