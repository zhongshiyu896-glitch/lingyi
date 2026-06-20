"""Finance approval task service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import FINANCE_APPROVAL_CONFLICT
from app.core.error_codes import FINANCE_APPROVAL_IDEMPOTENCY_CONFLICT
from app.core.error_codes import FINANCE_APPROVAL_INVALID_STATUS
from app.core.error_codes import FINANCE_APPROVAL_NOT_FOUND
from app.core.error_codes import MATERIAL_PURCHASE_NOT_FOUND
from app.core.error_codes import FACTORY_STATEMENT_SOURCE_NOT_FOUND
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.models.factory_statement import LyFactoryStatementPayment
from app.models.finance_approval import LyFinanceApprovalOperation
from app.models.finance_approval import LyFinanceApprovalTask
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchasePayment
from app.schemas.finance_approval import FinanceApprovalDecisionRequest
from app.schemas.finance_approval import FinanceApprovalTaskCreateRequest
from app.schemas.finance_approval import FinanceApprovalTaskCreateData
from app.schemas.finance_approval import FinanceApprovalTaskItem
from app.schemas.finance_approval import FinanceApprovalTaskListData


@dataclass(frozen=True)
class FinanceApprovalMutationResult:
    """Result wrapper for audited approval mutations."""

    item: FinanceApprovalTaskItem
    resource_id: int
    resource_no: str
    before: dict[str, Any] | None
    after: dict[str, Any]


@dataclass(frozen=True)
class _ApprovalSource:
    source_type: str
    source_id: str
    source_no: str
    source_status: str
    partner_name: str
    amount: Decimal
    currency: str
    payload: dict[str, Any]


class FinanceApprovalService:
    """Create, list and decide finance approval tasks."""

    def __init__(self, session: Session):
        self.session = session

    def list_tasks(
        self,
        *,
        company: str | None,
        keyword: str | None,
        source_type: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> FinanceApprovalTaskListData:
        try:
            query = self.session.query(LyFinanceApprovalTask)
            if company:
                query = query.filter(LyFinanceApprovalTask.company == company)
            if source_type:
                query = query.filter(LyFinanceApprovalTask.source_type == source_type)
            if status:
                query = query.filter(LyFinanceApprovalTask.status == status)
            if keyword:
                like = f"%{keyword.strip()}%"
                query = query.filter(
                    or_(
                        LyFinanceApprovalTask.approval_no.like(like),
                        LyFinanceApprovalTask.source_no.like(like),
                        LyFinanceApprovalTask.partner_name.like(like),
                        LyFinanceApprovalTask.submitted_by.like(like),
                    )
                )
            total = query.count()
            rows = (
                query.order_by(LyFinanceApprovalTask.created_at.desc(), LyFinanceApprovalTask.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return FinanceApprovalTaskListData(
            items=[self._to_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def create_task(self, *, payload: FinanceApprovalTaskCreateRequest, actor: str) -> FinanceApprovalMutationResult:
        source = self._load_source(company=payload.company, source_type=payload.source_type, source_id=payload.source_id)
        request_hash = self._hash_payload(
            {
                "operation": payload.operation,
                "company": payload.company,
                "source_type": payload.source_type,
                "source_id": str(payload.source_id),
            }
        )
        existing_by_key = self._find_task_by_idempotency(company=payload.company, idempotency_key=payload.idempotency_key)
        if existing_by_key:
            if existing_by_key.request_hash != request_hash:
                raise BusinessException(code=FINANCE_APPROVAL_IDEMPOTENCY_CONFLICT)
            item = self._to_item(existing_by_key)
            return FinanceApprovalMutationResult(
                item=item,
                resource_id=existing_by_key.id,
                resource_no=existing_by_key.approval_no,
                before=None,
                after=self._task_snapshot(existing_by_key),
            )

        existing_by_source = self._find_task_by_source(
            company=payload.company,
            source_type=payload.source_type,
            source_id=str(payload.source_id),
        )
        if existing_by_source:
            item = self._to_item(existing_by_source)
            return FinanceApprovalMutationResult(
                item=item,
                resource_id=existing_by_source.id,
                resource_no=existing_by_source.approval_no,
                before=None,
                after=self._task_snapshot(existing_by_source),
            )

        now = datetime.now(UTC)
        task = LyFinanceApprovalTask(
            company=payload.company,
            approval_no=self._next_approval_no(company=payload.company, now=now),
            source_type=source.source_type,
            source_id=source.source_id,
            source_no=source.source_no,
            source_status=source.source_status,
            partner_name=source.partner_name,
            amount=source.amount,
            currency=source.currency,
            status="pending",
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            scenario_tag=payload.scenario_tag,
            payload=source.payload,
            submitted_by=actor,
            submitted_at=now,
            created_by=actor,
            updated_by=actor,
        )
        try:
            self.session.add(task)
            self.session.flush()
            self._apply_source_approval_state(task=task, approval_status="pending", actor=actor, when=now)
        except IntegrityError as exc:
            raise BusinessException(code=FINANCE_APPROVAL_CONFLICT) from exc
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        return FinanceApprovalMutationResult(
            item=self._to_item(task),
            resource_id=task.id,
            resource_no=task.approval_no,
            before=None,
            after=self._task_snapshot(task),
        )

    def approve_task(
        self,
        *,
        task_id: int,
        payload: FinanceApprovalDecisionRequest,
        actor: str,
    ) -> FinanceApprovalMutationResult:
        return self._decide_task(task_id=task_id, payload=payload, actor=actor, decision="approved")

    def reject_task(
        self,
        *,
        task_id: int,
        payload: FinanceApprovalDecisionRequest,
        actor: str,
    ) -> FinanceApprovalMutationResult:
        return self._decide_task(task_id=task_id, payload=payload, actor=actor, decision="rejected")

    def _decide_task(
        self,
        *,
        task_id: int,
        payload: FinanceApprovalDecisionRequest,
        actor: str,
        decision: str,
    ) -> FinanceApprovalMutationResult:
        if decision == "approved" and payload.operation != "approve_task":
            raise BusinessException(code=FINANCE_APPROVAL_CONFLICT)
        if decision == "rejected" and payload.operation != "reject_task":
            raise BusinessException(code=FINANCE_APPROVAL_CONFLICT)

        task = self._get_task(company=payload.company, task_id=task_id)
        operation_type = payload.operation
        request_hash = self._hash_payload(
            {
                "operation": payload.operation,
                "company": payload.company,
                "task_id": task_id,
                "reason": payload.reason or "",
            }
        )
        existing_operation = self._find_operation(
            company=payload.company,
            operation_type=operation_type,
            idempotency_key=payload.idempotency_key,
        )
        if existing_operation:
            if existing_operation.request_hash != request_hash:
                raise BusinessException(code=FINANCE_APPROVAL_IDEMPOTENCY_CONFLICT)
            item = self._to_item(task)
            return FinanceApprovalMutationResult(
                item=item,
                resource_id=task.id,
                resource_no=task.approval_no,
                before=None,
                after=self._task_snapshot(task),
            )

        if task.status != "pending":
            raise BusinessException(code=FINANCE_APPROVAL_INVALID_STATUS)

        before = self._task_snapshot(task)
        now = datetime.now(UTC)
        task.status = decision
        task.updated_by = actor
        task.updated_at = now
        if decision == "approved":
            task.approved_by = actor
            task.approved_at = now
            task.rejected_by = None
            task.rejected_at = None
            task.reject_reason = None
        else:
            task.rejected_by = actor
            task.rejected_at = now
            task.reject_reason = payload.reason or "审批驳回"

        operation = LyFinanceApprovalOperation(
            company=payload.company,
            task_id=task.id,
            operation_type=operation_type,
            idempotency_key=payload.idempotency_key,
            request_hash=request_hash,
            result_status=task.status,
            result_user=actor,
            result_at=now,
            reason=payload.reason,
        )
        try:
            self.session.add(operation)
            self._apply_source_approval_state(
                task=task,
                approval_status=decision,
                actor=actor,
                when=now,
                reason=payload.reason,
            )
            self.session.flush()
        except IntegrityError as exc:
            raise BusinessException(code=FINANCE_APPROVAL_CONFLICT) from exc
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        return FinanceApprovalMutationResult(
            item=self._to_item(task),
            resource_id=task.id,
            resource_no=task.approval_no,
            before=before,
            after=self._task_snapshot(task),
        )

    def _load_source(self, *, company: str, source_type: str, source_id: int) -> _ApprovalSource:
        try:
            if source_type == "purchase_invoice":
                row = (
                    self.session.query(LyMaterialPurchaseInvoice)
                    .filter(LyMaterialPurchaseInvoice.company == company, LyMaterialPurchaseInvoice.id == source_id)
                    .first()
                )
                if not row or row.status == "cancelled":
                    raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND)
                return _ApprovalSource(
                    source_type=source_type,
                    source_id=str(row.id),
                    source_no=row.purchase_invoice,
                    source_status=row.status,
                    partner_name=row.supplier_name,
                    amount=Decimal(row.outstanding_amount or row.grand_total or 0),
                    currency="CNY",
                    payload={
                        "purchase_invoice": row.purchase_invoice,
                        "purchase_no": row.purchase_no,
                        "supplier_name": row.supplier_name,
                        "grand_total": str(row.grand_total),
                        "outstanding_amount": str(row.outstanding_amount),
                    },
                )
            if source_type == "purchase_payment":
                row = (
                    self.session.query(LyMaterialPurchasePayment)
                    .filter(LyMaterialPurchasePayment.company == company, LyMaterialPurchasePayment.id == source_id)
                    .first()
                )
                if not row or row.status == "cancelled":
                    raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND)
                return _ApprovalSource(
                    source_type=source_type,
                    source_id=str(row.id),
                    source_no=row.payment_entry,
                    source_status=row.status,
                    partner_name=row.supplier_name,
                    amount=Decimal(row.paid_amount or 0),
                    currency="CNY",
                    payload={
                        "payment_entry": row.payment_entry,
                        "purchase_invoice": row.purchase_invoice,
                        "purchase_no": row.purchase_no,
                        "supplier_name": row.supplier_name,
                        "paid_amount": str(row.paid_amount),
                    },
                )
            if source_type == "factory_statement_payment":
                row = (
                    self.session.query(LyFactoryStatementPayment)
                    .filter(LyFactoryStatementPayment.company == company, LyFactoryStatementPayment.id == source_id)
                    .first()
                )
                if not row or row.status == "cancelled":
                    raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
                return _ApprovalSource(
                    source_type=source_type,
                    source_id=str(row.id),
                    source_no=row.payment_entry,
                    source_status=row.status,
                    partner_name=row.supplier,
                    amount=Decimal(row.paid_amount or 0),
                    currency="CNY",
                    payload={
                        "payment_entry": row.payment_entry,
                        "statement_no": row.statement_no,
                        "supplier": row.supplier,
                        "paid_amount": str(row.paid_amount),
                    },
                )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        raise BusinessException(code=FINANCE_APPROVAL_NOT_FOUND)

    def _apply_source_approval_state(
        self,
        *,
        task: LyFinanceApprovalTask,
        approval_status: str,
        actor: str,
        when: datetime,
        reason: str | None = None,
    ) -> None:
        row = self._get_source_row_for_task(task)
        existing_payload = row.payload if isinstance(row.payload, dict) else {}
        payload = dict(existing_payload)
        approval_payload = {
            "status": approval_status,
            "approval_no": task.approval_no,
            "approval_task_id": int(task.id),
            "source_type": task.source_type,
            "source_id": str(task.source_id),
            "updated_by": actor,
            "updated_at": when.isoformat(),
        }
        if approval_status == "pending":
            approval_payload["submitted_by"] = task.submitted_by or actor
            approval_payload["submitted_at"] = (task.submitted_at or when).isoformat()
        if approval_status == "approved":
            approval_payload["approved_by"] = actor
            approval_payload["approved_at"] = when.isoformat()
        if approval_status == "rejected":
            approval_payload["rejected_by"] = actor
            approval_payload["rejected_at"] = when.isoformat()
            approval_payload["reject_reason"] = reason or task.reject_reason or "审批驳回"
        payload["finance_approval"] = approval_payload
        row.payload = payload
        if hasattr(row, "updated_by"):
            row.updated_by = actor
        if hasattr(row, "updated_at"):
            row.updated_at = when
        task.source_status = str(row.status or "")

    def _get_source_row_for_task(self, task: LyFinanceApprovalTask) -> Any:
        try:
            source_id = int(task.source_id)
        except (TypeError, ValueError) as exc:
            raise BusinessException(code=FINANCE_APPROVAL_NOT_FOUND) from exc

        try:
            if task.source_type == "purchase_invoice":
                row = (
                    self.session.query(LyMaterialPurchaseInvoice)
                    .filter(LyMaterialPurchaseInvoice.company == task.company, LyMaterialPurchaseInvoice.id == source_id)
                    .first()
                )
                if row:
                    return row
                raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND)
            if task.source_type == "purchase_payment":
                row = (
                    self.session.query(LyMaterialPurchasePayment)
                    .filter(LyMaterialPurchasePayment.company == task.company, LyMaterialPurchasePayment.id == source_id)
                    .first()
                )
                if row:
                    return row
                raise BusinessException(code=MATERIAL_PURCHASE_NOT_FOUND)
            if task.source_type == "factory_statement_payment":
                row = (
                    self.session.query(LyFactoryStatementPayment)
                    .filter(LyFactoryStatementPayment.company == task.company, LyFactoryStatementPayment.id == source_id)
                    .first()
                )
                if row:
                    return row
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        raise BusinessException(code=FINANCE_APPROVAL_NOT_FOUND)

    def _get_task(self, *, company: str, task_id: int) -> LyFinanceApprovalTask:
        try:
            row = (
                self.session.query(LyFinanceApprovalTask)
                .filter(LyFinanceApprovalTask.company == company, LyFinanceApprovalTask.id == task_id)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            raise BusinessException(code=FINANCE_APPROVAL_NOT_FOUND)
        return row

    def _find_task_by_idempotency(self, *, company: str, idempotency_key: str) -> LyFinanceApprovalTask | None:
        try:
            return (
                self.session.query(LyFinanceApprovalTask)
                .filter(LyFinanceApprovalTask.company == company, LyFinanceApprovalTask.idempotency_key == idempotency_key)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _find_task_by_source(self, *, company: str, source_type: str, source_id: str) -> LyFinanceApprovalTask | None:
        try:
            return (
                self.session.query(LyFinanceApprovalTask)
                .filter(
                    LyFinanceApprovalTask.company == company,
                    LyFinanceApprovalTask.source_type == source_type,
                    LyFinanceApprovalTask.source_id == source_id,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _find_operation(
        self,
        *,
        company: str,
        operation_type: str,
        idempotency_key: str,
    ) -> LyFinanceApprovalOperation | None:
        try:
            return (
                self.session.query(LyFinanceApprovalOperation)
                .filter(
                    LyFinanceApprovalOperation.company == company,
                    LyFinanceApprovalOperation.operation_type == operation_type,
                    LyFinanceApprovalOperation.idempotency_key == idempotency_key,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _next_approval_no(self, *, company: str, now: datetime) -> str:
        prefix = f"FAP-{now.strftime('%Y%m%d')}"
        try:
            count = (
                self.session.query(LyFinanceApprovalTask)
                .filter(LyFinanceApprovalTask.company == company, LyFinanceApprovalTask.approval_no.like(f"{prefix}-%"))
                .count()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        return f"{prefix}-{count + 1:04d}"

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _task_snapshot(row: LyFinanceApprovalTask) -> dict[str, Any]:
        return {
            "id": row.id,
            "company": row.company,
            "approval_no": row.approval_no,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "source_no": row.source_no,
            "source_status": row.source_status,
            "partner_name": row.partner_name,
            "amount": str(row.amount),
            "currency": row.currency,
            "status": row.status,
            "scenario_tag": row.scenario_tag,
            "submitted_by": row.submitted_by,
            "approved_by": row.approved_by,
            "rejected_by": row.rejected_by,
            "reject_reason": row.reject_reason,
        }

    @staticmethod
    def _to_item(row: LyFinanceApprovalTask) -> FinanceApprovalTaskItem:
        return FinanceApprovalTaskItem(
            id=row.id,
            company=row.company,
            approval_no=row.approval_no,
            source_type=row.source_type,
            source_id=row.source_id,
            source_no=row.source_no,
            source_status=row.source_status,
            partner_name=row.partner_name,
            amount=Decimal(row.amount or 0),
            currency=row.currency,
            status=row.status,
            scenario_tag=row.scenario_tag,
            submitted_by=row.submitted_by,
            submitted_at=row.submitted_at,
            approved_by=row.approved_by,
            approved_at=row.approved_at,
            rejected_by=row.rejected_by,
            rejected_at=row.rejected_at,
            reject_reason=row.reject_reason,
            created_by=row.created_by,
            created_at=row.created_at,
            updated_by=row.updated_by,
            updated_at=row.updated_at,
        )
