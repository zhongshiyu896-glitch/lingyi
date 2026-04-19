"""Worker service for production Work Order outbox (TASK-004A)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import PRODUCTION_WORK_ORDER_SYNC_FAILED
from app.core.exceptions import AppException
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.production import LyProductionPlan
from app.models.production import LyProductionStatusLog
from app.models.production import LyProductionWorkOrderLink
from app.services.erpnext_production_adapter import ERPNextProductionAdapter
from app.services.erpnext_production_adapter import ERPNextWorkOrder
from app.services.production_work_order_outbox_service import ProductionOutboxClaim
from app.services.production_work_order_outbox_service import ProductionWorkOrderOutboxService


@dataclass(frozen=True)
class ProductionWorkerRunResult:
    """Run-once worker result."""

    dry_run: bool
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int


class ProductionWorkOrderWorker:
    """Process production Work Order outbox rows."""

    def __init__(
        self,
        *,
        session: Session,
        adapter: ERPNextProductionAdapter,
    ):
        self.session = session
        self.adapter = adapter
        self.outbox_service = ProductionWorkOrderOutboxService(session=session)

    def run_once(
        self,
        *,
        batch_size: int,
        worker_id: str,
        dry_run: bool = False,
        allowed_companies: set[str] | None = None,
        allowed_items: set[str] | None = None,
    ) -> ProductionWorkerRunResult:
        if dry_run:
            claims = self._load_due_candidates(
                batch_size=batch_size,
                allowed_companies=allowed_companies,
                allowed_items=allowed_items,
            )
            return ProductionWorkerRunResult(
                dry_run=True,
                processed_count=len(claims),
                succeeded_count=0,
                failed_count=0,
                dead_count=0,
            )

        claims = self.outbox_service.claim_due(
            batch_size=batch_size,
            worker_id=worker_id,
            allowed_companies=allowed_companies,
            allowed_items=allowed_items,
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
                work_order = self._resolve_or_create_work_order(claim=claim)
                self._persist_success(claim=claim, work_order=work_order)
                succeeded += 1
            except AppException as exc:
                is_dead = self._persist_failure(claim=claim, exc=exc)
                failed += 1
                if is_dead:
                    dead += 1
            except Exception as exc:  # pragma: no cover - defensive path
                wrapped = BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="Work Order 同步失败")
                is_dead = self._persist_failure(claim=claim, exc=wrapped, raw_exc=exc)
                failed += 1
                if is_dead:
                    dead += 1

        return ProductionWorkerRunResult(
            dry_run=False,
            processed_count=len(claims),
            succeeded_count=succeeded,
            failed_count=failed,
            dead_count=dead,
        )

    def _load_due_candidates(
        self,
        *,
        batch_size: int,
        allowed_companies: set[str] | None,
        allowed_items: set[str] | None,
    ) -> list[int]:
        now = datetime.utcnow()
        try:
            from app.models.production import LyProductionWorkOrderOutbox

            query = self.session.query(LyProductionWorkOrderOutbox.id).filter(
                LyProductionWorkOrderOutbox.action == ProductionWorkOrderOutboxService.ACTION_CREATE_WORK_ORDER,
                (
                    (
                        LyProductionWorkOrderOutbox.status.in_(["pending", "failed"])
                        & (
                            LyProductionWorkOrderOutbox.next_retry_at.is_(None)
                            | (LyProductionWorkOrderOutbox.next_retry_at <= now)
                        )
                    )
                    | (
                        (LyProductionWorkOrderOutbox.status == "processing")
                        & LyProductionWorkOrderOutbox.lease_until.is_not(None)
                        & (LyProductionWorkOrderOutbox.lease_until < now)
                    )
                ),
            )
            if allowed_companies is not None:
                if not allowed_companies:
                    return []
                query = query.filter(LyProductionWorkOrderOutbox.company.in_(sorted(allowed_companies)))
            if allowed_items is not None:
                if not allowed_items:
                    return []
                query = query.filter(LyProductionWorkOrderOutbox.item_code.in_(sorted(allowed_items)))
            rows = query.order_by(LyProductionWorkOrderOutbox.id.asc()).limit(int(batch_size)).all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return [int(row[0]) for row in rows]

    def _resolve_or_create_work_order(self, *, claim: ProductionOutboxClaim) -> str:
        plan = self._must_get_plan(plan_id=claim.plan_id)

        existing = self.adapter.find_work_order_by_plan(plan_id=plan.id, plan_no=plan.plan_no)
        if existing is not None:
            return self._ensure_submitted(existing)

        payload = dict(claim.payload_json)
        payload.setdefault("custom_ly_plan_id", str(plan.id))
        payload.setdefault("custom_ly_plan_no", str(plan.plan_no))

        created_name = self.adapter.create_work_order(payload_json=payload)
        self.adapter.submit_work_order(work_order=created_name)
        check = self.adapter.get_work_order(work_order=created_name)
        if check is None:
            raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="ERPNext Work Order 提交后查询失败")
        if int(check.docstatus) != 1:
            raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="ERPNext Work Order 未提交成功")
        return check.name

    def _ensure_submitted(self, existing: ERPNextWorkOrder) -> str:
        docstatus = int(existing.docstatus)
        if docstatus == 1:
            return existing.name
        if docstatus == 0:
            self.adapter.submit_work_order(work_order=existing.name)
            refreshed = self.adapter.get_work_order(work_order=existing.name)
            if refreshed is None or int(refreshed.docstatus) != 1:
                raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="ERPNext Work Order draft 提交失败")
            return refreshed.name
        raise BusinessException(code=PRODUCTION_WORK_ORDER_SYNC_FAILED, message="ERPNext Work Order 状态不允许同步成功")

    def _persist_success(self, *, claim: ProductionOutboxClaim, work_order: str) -> None:
        self.outbox_service.mark_succeeded(outbox_id=claim.outbox_id, work_order=work_order)

        link = (
            self.session.query(LyProductionWorkOrderLink)
            .filter(LyProductionWorkOrderLink.plan_id == claim.plan_id)
            .first()
        )
        if link is None:
            link = LyProductionWorkOrderLink(
                plan_id=claim.plan_id,
                work_order=work_order,
                erpnext_docstatus=1,
                erpnext_status="Submitted",
                sync_status="succeeded",
                last_synced_at=datetime.utcnow(),
                created_by="system_worker",
            )
            self.session.add(link)
        else:
            link.work_order = work_order
            link.erpnext_docstatus = 1
            link.erpnext_status = "Submitted"
            link.sync_status = "succeeded"
            link.last_synced_at = datetime.utcnow()
            if not (link.created_by or "").strip():
                link.created_by = "system_worker"

        plan = self._must_get_plan(plan_id=claim.plan_id)
        previous = str(plan.status)
        if previous != "work_order_created":
            plan.status = "work_order_created"
            self.session.add(
                LyProductionStatusLog(
                    plan_id=plan.id,
                    from_status=previous,
                    to_status="work_order_created",
                    action="work_order_sync_success",
                    operator="system_worker",
                )
            )

        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseWriteFailed() from exc

    def _persist_failure(self, *, claim: ProductionOutboxClaim, exc: AppException, raw_exc: Exception | None = None) -> bool:
        message = exc.message if isinstance(exc, AppException) else "Work Order 同步失败"
        row = self.outbox_service.mark_failed(
            outbox_id=claim.outbox_id,
            error_code=exc.code,
            error_message=message,
        )

        plan = self._must_get_plan(plan_id=claim.plan_id)
        self.session.add(
            LyProductionStatusLog(
                plan_id=plan.id,
                from_status=str(plan.status),
                to_status=str(plan.status),
                action="work_order_sync_failed",
                operator="system_worker",
                request_id=None,
            )
        )

        try:
            self.session.commit()
        except SQLAlchemyError as commit_exc:
            self.session.rollback()
            raise DatabaseWriteFailed() from commit_exc

        del raw_exc
        return str(row.status) == "dead"

    def _must_get_plan(self, *, plan_id: int) -> LyProductionPlan:
        try:
            row = self.session.query(LyProductionPlan).filter(LyProductionPlan.id == int(plan_id)).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if row is None:
            raise DatabaseReadFailed()
        return row
