"""Business service for workshop ticket module (TASK-003)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from decimal import ROUND_HALF_UP
import logging
from typing import Any

from sqlalchemy import and_
from sqlalchemy import asc
from sqlalchemy import desc
from sqlalchemy import false
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import ERPNEXT_SERVICE_UNAVAILABLE
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import WORKSHOP_EMPLOYEE_NOT_FOUND
from app.core.error_codes import WORKSHOP_IDEMPOTENCY_CONFLICT
from app.core.error_codes import WORKSHOP_ITEM_MISMATCH
from app.core.error_codes import WORKSHOP_INVALID_QTY
from app.core.error_codes import WORKSHOP_JOB_CARD_COMPANY_NOT_FOUND
from app.core.error_codes import WORKSHOP_JOB_CARD_ITEM_NOT_FOUND
from app.core.error_codes import WORKSHOP_JOB_CARD_NOT_FOUND
from app.core.error_codes import WORKSHOP_JOB_CARD_STATUS_INVALID
from app.core.error_codes import WORKSHOP_INTERNAL_ERROR
from app.core.error_codes import WORKSHOP_PROCESS_MISMATCH
from app.core.error_codes import WORKSHOP_REVERSAL_EXCEEDS_REGISTERED
from app.core.error_codes import WORKSHOP_TICKET_NOT_FOUND
from app.core.error_codes import WORKSHOP_WAGE_RATE_COMPANY_REQUIRED
from app.core.error_codes import WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS
from app.core.error_codes import WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED
from app.core.error_codes import WORKSHOP_WAGE_RATE_NOT_FOUND
from app.core.error_codes import WORKSHOP_WAGE_RATE_OVERLAP
from app.core.error_codes import WORKSHOP_WAGE_RATE_SCOPE_REQUIRED
from app.core.error_codes import DATABASE_READ_FAILED
from app.core.exceptions import AppException
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import ERPNextServiceUnavailableError
from app.core.logging import log_safe_error
from app.models.workshop import LyOperationWageRate
from app.models.workshop import LyOperationWageRateCompanyBackfillLog
from app.models.workshop import YsWorkshopDailyWage
from app.models.workshop import YsWorkshopJobCardSyncLog
from app.models.workshop import YsWorkshopJobCardSyncOutbox
from app.models.workshop import YsWorkshopTicket
from app.schemas.workshop import OperationWageRateCreateData
from app.schemas.workshop import OperationWageRateCreateRequest
from app.schemas.workshop import OperationWageRateDeactivateData
from app.schemas.workshop import OperationWageRateQuery
from app.schemas.workshop import OperationWageRateListData
from app.schemas.workshop import OperationWageRateRow
from app.schemas.workshop import WorkshopBatchFailedItem
from app.schemas.workshop import WorkshopBatchResult
from app.schemas.workshop import WorkshopDailyWageListData
from app.schemas.workshop import WorkshopDailyWageQuery
from app.schemas.workshop import WorkshopDailyWageRow
from app.schemas.workshop import WorkshopJobCardSummaryData
from app.schemas.workshop import WorkshopJobCardSyncData
from app.schemas.workshop import WorkshopTicketBatchItem
from app.schemas.workshop import WorkshopTicketBatchRequest
from app.schemas.workshop import WorkshopTicketData
from app.schemas.workshop import WorkshopTicketListData
from app.schemas.workshop import WorkshopTicketListQuery
from app.schemas.workshop import WorkshopTicketRegisterRequest
from app.schemas.workshop import WorkshopTicketReversalData
from app.schemas.workshop import WorkshopTicketReversalRequest
from app.schemas.workshop import WorkshopTicketRow
from app.services.erpnext_job_card_adapter import ERPNextJobCardAdapter
from app.services.erpnext_job_card_adapter import CompanyInfo
from app.services.erpnext_job_card_adapter import ItemInfo
from app.services.erpnext_job_card_adapter import JobCardInfo
from app.services.erpnext_job_card_adapter import WorkOrderInfo
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.workshop_outbox_service import WorkshopOutboxService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkshopResourceContext:
    """Resolved workshop resource for permission checks and write operations."""

    job_card: str
    work_order: str | None
    item_code: str
    company: str


@dataclass(frozen=True)
class WageRateResource:
    """Resolved wage-rate resource for permission checks and writes."""

    item_code: str | None
    company: str | None
    is_global: bool


@dataclass(frozen=True)
class WageRateCompanyBackfillReport:
    """历史 item 工价 company 补数报告。"""

    total_scanned: int
    backfilled_count: int
    blocked_count: int
    ambiguous_count: int
    unresolved_count: int
    unchanged_count: int


@dataclass(frozen=True)
class WageRateCompanyBackfillPlanRow:
    """历史工价 company 补数计划行（只读 DTO）。"""

    wage_rate_id: int
    item_code: str
    old_company: str | None
    normalized_company: str | None
    planned_company: str | None
    planned_action: str
    reason_code: str


class WorkshopService:
    """Workshop service that handles ticket and wage workflows."""

    OP_REGISTER = "register"
    OP_REVERSAL = "reversal"

    SYNC_PENDING = "pending"
    SYNC_SYNCED = "synced"
    SYNC_FAILED = "failed"
    ROW_LEVEL_BATCH_CODES = {
        WORKSHOP_INVALID_QTY,
        WORKSHOP_JOB_CARD_NOT_FOUND,
        WORKSHOP_EMPLOYEE_NOT_FOUND,
        WORKSHOP_JOB_CARD_STATUS_INVALID,
        WORKSHOP_PROCESS_MISMATCH,
        WORKSHOP_ITEM_MISMATCH,
        WORKSHOP_WAGE_RATE_NOT_FOUND,
        WORKSHOP_WAGE_RATE_SCOPE_REQUIRED,
        WORKSHOP_IDEMPOTENCY_CONFLICT,
        WORKSHOP_REVERSAL_EXCEEDS_REGISTERED,
        AUTH_FORBIDDEN,
    }

    def __init__(self, session: Session, erp_adapter: ERPNextJobCardAdapter):
        self.session = session
        self.erp_adapter = erp_adapter
        self.outbox_service = WorkshopOutboxService(session=session)

    def resolve_job_card_resource(
        self,
        *,
        job_card: str,
        process_name: str | None,
        request_item_code: str | None = None,
        enforce_status: bool = True,
    ) -> WorkshopResourceContext:
        """Resolve item/company from Job Card + Work Order and validate consistency."""
        job_card_info = self._get_job_card_or_raise(job_card=job_card)
        if process_name:
            self._validate_job_card(job_card_info=job_card_info, process_name=process_name, enforce_status=enforce_status)

        work_order_info = self._get_work_order_safe(job_card_info.work_order)

        item_code = self._derive_item_code(job_card_info=job_card_info, work_order_info=work_order_info)
        req_item = (request_item_code or "").strip()
        if req_item and req_item != item_code:
            raise BusinessException(code=WORKSHOP_ITEM_MISMATCH, message="请求 item_code 与 Job Card 派生 item_code 不一致")

        company = self._derive_company(job_card_info=job_card_info, work_order_info=work_order_info)
        return WorkshopResourceContext(
            job_card=job_card_info.name,
            work_order=job_card_info.work_order,
            item_code=item_code,
            company=company,
        )

    def get_ticket_resource_context(self, ticket_id: int) -> WorkshopResourceContext:
        """Resolve resource context from existing ticket."""
        try:
            row = self.session.query(YsWorkshopTicket).filter(YsWorkshopTicket.id == ticket_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            raise BusinessException(code=WORKSHOP_TICKET_NOT_FOUND, message="工票不存在")

        resolved = self.resolve_job_card_resource(
            job_card=row.job_card,
            process_name=row.process_name,
            request_item_code=row.item_code,
            enforce_status=False,
        )
        return WorkshopResourceContext(
            job_card=row.job_card,
            work_order=row.work_order or resolved.work_order,
            item_code=row.item_code,
            company=resolved.company,
        )

    def resolve_wage_rate_resource(self, *, item_code: str | None, company: str | None) -> WageRateResource:
        """Resolve wage-rate item/company scope from ERPNext facts."""
        normalized_item_code = self._normalize_text(item_code)
        requested_company = self._normalize_company(company)

        if not normalized_item_code:
            if requested_company:
                self._require_company_exists(requested_company)
            return WageRateResource(item_code=None, company=requested_company, is_global=True)

        if not requested_company:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_COMPANY_REQUIRED, message="item 工价必须提供 company")

        item_info = self._get_item_or_raise(item_code=normalized_item_code)
        candidate_companies = set(item_info.companies)
        self._require_company_exists(requested_company)
        if candidate_companies and requested_company not in candidate_companies:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_COMPANY_REQUIRED, message="item_code 与 company 不匹配")

        return WageRateResource(item_code=normalized_item_code, company=requested_company, is_global=False)

    def register_ticket(
        self,
        payload: WorkshopTicketRegisterRequest,
        operator: str,
        request_id: str,
        resolved_resource: WorkshopResourceContext | None = None,
    ) -> WorkshopTicketData:
        """Create a register ticket with idempotency and sync."""
        if payload.qty <= 0:
            raise BusinessException(code=WORKSHOP_INVALID_QTY, message="数量必须大于 0")

        resolved = resolved_resource or self.resolve_job_card_resource(
            job_card=payload.job_card,
            process_name=payload.process_name,
            request_item_code=payload.item_code,
            enforce_status=True,
        )
        item_code = resolved.item_code
        self._require_employee(payload.employee)

        existing = self._get_by_idempotent(
            ticket_key=payload.ticket_key,
            process_name=payload.process_name,
            color=payload.color,
            size=payload.size,
            operation_type=self.OP_REGISTER,
            work_date=payload.work_date,
        )
        if existing:
            if self._is_same_register_payload(existing, payload=payload, item_code=item_code, work_order=resolved.work_order):
                return self._to_ticket_data(existing)
            raise BusinessException(code=WORKSHOP_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

        unit_wage = self._resolve_unit_wage(
            item_code=item_code,
            company=resolved.company,
            process_name=payload.process_name,
            work_date=payload.work_date,
        )
        wage_amount = self._round(payload.qty * unit_wage)
        ticket = YsWorkshopTicket(
            ticket_no=self._build_ticket_no(),
            ticket_key=payload.ticket_key,
            job_card=payload.job_card,
            work_order=resolved.work_order,
            bom_id=None,
            item_code=item_code,
            employee=payload.employee,
            process_name=payload.process_name,
            color=payload.color,
            size=payload.size,
            operation_type=self.OP_REGISTER,
            qty=self._round(payload.qty),
            unit_wage=unit_wage,
            wage_amount=wage_amount,
            work_date=payload.work_date,
            source=payload.source,
            source_ref=payload.source_ref,
            original_ticket_id=None,
            sync_status=self.SYNC_PENDING,
            created_by=operator,
            updated_at=datetime.utcnow(),
        )
        try:
            self.session.add(ticket)
            self.session.flush()
        except IntegrityError as exc:
            self._raise_write_error(exc)
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        self._refresh_daily_wage(
            employee=ticket.employee,
            work_date=ticket.work_date,
            process_name=ticket.process_name,
            item_code=ticket.item_code,
        )
        outbox_row = self._enqueue_sync_outbox(
            ticket=ticket,
            company=resolved.company,
            request_id=request_id,
            source_type="ticket_register",
            source_ids=[int(ticket.id)],
            created_by=operator,
        )
        ticket.sync_status = self.SYNC_PENDING
        ticket.sync_error_code = None
        ticket.sync_error_message = None
        ticket.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return self._to_ticket_data(ticket, sync_outbox_id=int(outbox_row.id))

    def reverse_ticket(
        self,
        payload: WorkshopTicketReversalRequest,
        operator: str,
        request_id: str,
        resolved_resource: WorkshopResourceContext | None = None,
    ) -> WorkshopTicketReversalData:
        """Create a reversal ticket."""
        if payload.qty <= 0:
            raise BusinessException(code=WORKSHOP_INVALID_QTY, message="数量必须大于 0")

        resolved = resolved_resource or self.resolve_job_card_resource(
            job_card=payload.job_card,
            process_name=payload.process_name,
            request_item_code=payload.item_code,
            enforce_status=True,
        )
        item_code = resolved.item_code
        self._require_employee(payload.employee)
        if payload.original_ticket_id:
            self._validate_original_ticket_for_reversal(payload=payload)

        available_qty = self._available_reversal_qty(
            job_card=payload.job_card,
            employee=payload.employee,
            process_name=payload.process_name,
            color=payload.color,
            size=payload.size,
            work_date=payload.work_date,
        )
        if payload.qty > available_qty:
            raise BusinessException(code=WORKSHOP_REVERSAL_EXCEEDS_REGISTERED, message="撤销数量超过可撤销数量")

        existing = self._get_by_idempotent(
            ticket_key=payload.ticket_key,
            process_name=payload.process_name,
            color=payload.color,
            size=payload.size,
            operation_type=self.OP_REVERSAL,
            work_date=payload.work_date,
        )
        if existing:
            if self._is_same_reversal_payload(existing, payload=payload, item_code=item_code, work_order=resolved.work_order):
                net_qty = self._available_reversal_qty(
                    job_card=payload.job_card,
                    employee=payload.employee,
                    process_name=payload.process_name,
                    color=payload.color,
                    size=payload.size,
                    work_date=payload.work_date,
                )
                return WorkshopTicketReversalData(
                    ticket_no=existing.ticket_no,
                    ticket_id=int(existing.id),
                    net_qty=self._round(net_qty),
                    wage_amount=self._round(Decimal(existing.wage_amount)),
                    sync_status=existing.sync_status,
                    sync_outbox_id=None,
                )
            raise BusinessException(code=WORKSHOP_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致")

        unit_wage = self._resolve_reversal_wage(payload=payload, item_code=item_code, company=resolved.company)
        wage_amount = self._round(payload.qty * unit_wage)
        ticket = YsWorkshopTicket(
            ticket_no=self._build_ticket_no(),
            ticket_key=payload.ticket_key,
            job_card=payload.job_card,
            work_order=resolved.work_order,
            bom_id=None,
            item_code=item_code,
            employee=payload.employee,
            process_name=payload.process_name,
            color=payload.color,
            size=payload.size,
            operation_type=self.OP_REVERSAL,
            qty=self._round(payload.qty),
            unit_wage=unit_wage,
            wage_amount=wage_amount,
            work_date=payload.work_date,
            source="manual",
            source_ref=payload.reason,
            original_ticket_id=payload.original_ticket_id,
            sync_status=self.SYNC_PENDING,
            created_by=operator,
            updated_at=datetime.utcnow(),
        )
        try:
            self.session.add(ticket)
            self.session.flush()
        except IntegrityError as exc:
            self._raise_write_error(exc)
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        self._refresh_daily_wage(
            employee=ticket.employee,
            work_date=ticket.work_date,
            process_name=ticket.process_name,
            item_code=ticket.item_code,
        )
        outbox_row = self._enqueue_sync_outbox(
            ticket=ticket,
            company=resolved.company,
            request_id=request_id,
            source_type="ticket_reversal",
            source_ids=[int(ticket.id)],
            created_by=operator,
        )
        ticket.sync_status = self.SYNC_PENDING
        ticket.sync_error_code = None
        ticket.sync_error_message = None
        ticket.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        net_qty = self._available_reversal_qty(
            job_card=payload.job_card,
            employee=payload.employee,
            process_name=payload.process_name,
            color=payload.color,
            size=payload.size,
            work_date=payload.work_date,
        )
        return WorkshopTicketReversalData(
            ticket_no=ticket.ticket_no,
            ticket_id=int(ticket.id),
            net_qty=self._round(net_qty),
            wage_amount=self._round(Decimal(ticket.wage_amount)),
            sync_status=ticket.sync_status,
            sync_outbox_id=int(outbox_row.id),
        )

    def batch_import(
        self,
        payload: WorkshopTicketBatchRequest,
        operator: str,
        request_id: str,
        row_guard: Any | None = None,
    ) -> WorkshopBatchResult:
        """Import ticket rows in batch with per-row result."""
        success_items: list[WorkshopTicketData] = []
        failed_items: list[WorkshopBatchFailedItem] = []

        for index, row in enumerate(payload.tickets, start=1):
            try:
                with self.session.begin_nested():
                    result = self._handle_batch_row(
                        row=row,
                        operator=operator,
                        request_id=request_id,
                        row_guard=row_guard,
                    )
                    success_items.append(result)
            except BusinessException as exc:
                if exc.code not in self.ROW_LEVEL_BATCH_CODES:
                    raise
                failed_items.append(
                    WorkshopBatchFailedItem(
                        row_index=index,
                        index=index,
                        code=exc.code,
                        error_code=exc.code,
                        message=exc.message,
                        ticket_key=row.ticket_key,
                    )
                )
            except AppException:
                raise
            except Exception as exc:
                raise BusinessException(code=WORKSHOP_INTERNAL_ERROR, message="车间模块内部错误") from exc

        return WorkshopBatchResult(
            success_count=len(success_items),
            failed_count=len(failed_items),
            success_items=success_items,
            failed_items=failed_items,
        )

    def process_batch_row(
        self,
        *,
        row: WorkshopTicketBatchItem,
        operator: str,
        request_id: str,
        resolved_resource: WorkshopResourceContext | None = None,
    ) -> WorkshopTicketData:
        """Public wrapper for processing one batch row."""
        return self._handle_batch_row(
            row=row,
            operator=operator,
            request_id=request_id,
            resolved_resource=resolved_resource,
            row_guard=None,
        )

    def list_tickets(
        self,
        query: WorkshopTicketListQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> WorkshopTicketListData:
        """List workshop tickets."""
        try:
            sql = self.session.query(YsWorkshopTicket)
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return WorkshopTicketListData(items=[], total=0, page=query.page, page_size=query.page_size)
                sql = sql.filter(YsWorkshopTicket.item_code.in_(sorted(allowed_item_codes)))
            if query.employee:
                sql = sql.filter(YsWorkshopTicket.employee == query.employee)
            if query.job_card:
                sql = sql.filter(YsWorkshopTicket.job_card == query.job_card)
            if query.item_code:
                sql = sql.filter(YsWorkshopTicket.item_code == query.item_code)
            if query.process_name:
                sql = sql.filter(YsWorkshopTicket.process_name == query.process_name)
            if query.operation_type:
                sql = sql.filter(YsWorkshopTicket.operation_type == query.operation_type)
            if query.work_date:
                sql = sql.filter(YsWorkshopTicket.work_date == query.work_date)
            if query.from_date:
                sql = sql.filter(YsWorkshopTicket.work_date >= query.from_date)
            if query.to_date:
                sql = sql.filter(YsWorkshopTicket.work_date <= query.to_date)

            total = sql.with_entities(func.count(YsWorkshopTicket.id)).scalar() or 0
            rows = (
                sql.order_by(YsWorkshopTicket.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return WorkshopTicketListData(
            items=[
                WorkshopTicketRow(
                    id=int(row.id),
                    ticket_no=str(row.ticket_no),
                    ticket_key=str(row.ticket_key),
                    job_card=str(row.job_card),
                    work_order=row.work_order,
                    bom_id=int(row.bom_id) if row.bom_id is not None else None,
                    item_code=str(row.item_code),
                    employee=str(row.employee),
                    process_name=str(row.process_name),
                    color=row.color,
                    size=row.size,
                    operation_type=str(row.operation_type),
                    qty=self._round(Decimal(row.qty)),
                    unit_wage=self._round(Decimal(row.unit_wage)),
                    wage_amount=self._round(Decimal(row.wage_amount)),
                    work_date=row.work_date,
                    source=str(row.source),
                    source_ref=row.source_ref,
                    sync_status=str(row.sync_status),
                    created_by=str(row.created_by),
                    created_at=row.created_at,
                )
                for row in rows
            ],
            total=int(total),
            page=query.page,
            page_size=query.page_size,
        )

    def list_daily_wages(
        self,
        query: WorkshopDailyWageQuery,
        allowed_item_codes: set[str] | None = None,
    ) -> WorkshopDailyWageListData:
        """List daily wage aggregates."""
        try:
            sql = self.session.query(YsWorkshopDailyWage)
            if allowed_item_codes is not None:
                if not allowed_item_codes:
                    return WorkshopDailyWageListData(items=[], total=0, total_amount=Decimal("0"), page=query.page, page_size=query.page_size)
                sql = sql.filter(
                    or_(YsWorkshopDailyWage.item_code.is_(None), YsWorkshopDailyWage.item_code.in_(sorted(allowed_item_codes)))
                )
            if query.employee:
                sql = sql.filter(YsWorkshopDailyWage.employee == query.employee)
            if query.process_name:
                sql = sql.filter(YsWorkshopDailyWage.process_name == query.process_name)
            if query.item_code:
                sql = sql.filter(YsWorkshopDailyWage.item_code == query.item_code)
            if query.from_date:
                sql = sql.filter(YsWorkshopDailyWage.work_date >= query.from_date)
            if query.to_date:
                sql = sql.filter(YsWorkshopDailyWage.work_date <= query.to_date)

            total = sql.with_entities(func.count(YsWorkshopDailyWage.id)).scalar() or 0
            total_amount = sql.with_entities(func.coalesce(func.sum(YsWorkshopDailyWage.wage_amount), 0)).scalar() or 0
            rows = (
                sql.order_by(YsWorkshopDailyWage.work_date.desc(), YsWorkshopDailyWage.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return WorkshopDailyWageListData(
            items=[
                WorkshopDailyWageRow(
                    employee=str(row.employee),
                    work_date=row.work_date,
                    process_name=str(row.process_name),
                    item_code=row.item_code,
                    register_qty=self._round(Decimal(row.register_qty)),
                    reversal_qty=self._round(Decimal(row.reversal_qty)),
                    net_qty=self._round(Decimal(row.net_qty)),
                    wage_amount=self._round(Decimal(row.wage_amount)),
                )
                for row in rows
            ],
            total=int(total),
            total_amount=self._round(Decimal(total_amount)),
            page=query.page,
            page_size=query.page_size,
        )

    def get_job_card_summary(
        self,
        job_card: str,
        allowed_item_codes: set[str] | None = None,
    ) -> WorkshopJobCardSummaryData:
        """Get local summary for Job Card."""
        register_qty, reversal_qty, net_qty, ticket_sync_status, item_code = self._calc_job_card_totals(job_card=job_card)
        if allowed_item_codes is not None and item_code and item_code not in allowed_item_codes:
            raise BusinessException(code="AUTH_FORBIDDEN", message="无权限访问该资源")

        outbox_row = self.outbox_service.latest_by_job_card(job_card=job_card)
        outbox_status = self.SYNC_PENDING
        last_error_code = None
        last_error_message = None
        sync_status = ticket_sync_status
        if outbox_row is not None:
            outbox_status = str(outbox_row.status)
            if outbox_status == WorkshopOutboxService.STATUS_SUCCEEDED:
                sync_status = self.SYNC_SYNCED
            elif outbox_status in {WorkshopOutboxService.STATUS_FAILED, WorkshopOutboxService.STATUS_DEAD}:
                sync_status = self.SYNC_FAILED
            else:
                sync_status = self.SYNC_PENDING
            last_error_code = outbox_row.last_error_code
            last_error_message = outbox_row.last_error_message

        try:
            last_log = (
                self.session.query(YsWorkshopJobCardSyncLog)
                .filter(YsWorkshopJobCardSyncLog.job_card == job_card)
                .order_by(YsWorkshopJobCardSyncLog.id.desc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return WorkshopJobCardSummaryData(
            job_card=job_card,
            register_qty=register_qty,
            reversal_qty=reversal_qty,
            net_qty=net_qty,
            local_completed_qty=net_qty,
            sync_status=sync_status,
            outbox_status=outbox_status,
            last_sync_at=last_log.created_at if last_log else None,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )

    def retry_job_card_sync(self, job_card: str, request_id: str, operator: str) -> WorkshopJobCardSyncData:
        """Manual retry for Job Card sync via outbox."""
        _, _, net_qty, _, _ = self._calc_job_card_totals(job_card=job_card)
        resource = self.resolve_job_card_resource(
            job_card=job_card,
            process_name=None,
            request_item_code=None,
            enforce_status=False,
        )
        outbox_row = self.outbox_service.requeue(
            job_card=resource.job_card,
            work_order=resource.work_order,
            item_code=resource.item_code,
            company=resource.company,
            local_completed_qty=net_qty,
            source_type="manual_retry",
            source_ids=[],
            request_id=request_id,
            operator=operator,
            max_attempts=5,
        )
        try:
            self.session.query(YsWorkshopTicket).filter(YsWorkshopTicket.job_card == job_card).update(
                {
                    "sync_status": self.SYNC_PENDING,
                    "sync_error_code": None,
                    "sync_error_message": None,
                    "updated_at": datetime.utcnow(),
                }
            )
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

        return WorkshopJobCardSyncData(
            job_card=job_card,
            local_completed_qty=net_qty,
            sync_status=self.SYNC_PENDING,
            sync_outbox_id=int(outbox_row.id),
        )

    def list_wage_rates(
        self,
        query: OperationWageRateQuery,
        *,
        user_permissions: UserPermissionResult | None = None,
        allow_global_read: bool = False,
    ) -> OperationWageRateListData:
        """List wage rate records with DB-level resource filtering."""
        normalized_item_code = self._normalize_text(query.item_code)
        normalized_company = self._normalize_company(query.company)
        if query.company is not None and normalized_company is None:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_COMPANY_REQUIRED, message="company 不能为空")
        try:
            sql = self.session.query(LyOperationWageRate)

            if normalized_item_code:
                sql = sql.filter(LyOperationWageRate.item_code == normalized_item_code)
            if normalized_company:
                sql = sql.filter(LyOperationWageRate.company == normalized_company)
            if query.is_global is not None:
                sql = sql.filter(LyOperationWageRate.is_global.is_(query.is_global))
            if query.process_name:
                sql = sql.filter(LyOperationWageRate.process_name == query.process_name)
            if query.status:
                sql = sql.filter(LyOperationWageRate.status == query.status)
            # Historical dirty data guard: active item-specific rates must bind company.
            sql = sql.filter(
                or_(
                    LyOperationWageRate.item_code.is_(None),
                    self._has_company_scope_expr(LyOperationWageRate.company),
                    LyOperationWageRate.status != "active",
                )
            )

            if user_permissions is not None:
                allowed_companies = sorted({c.strip() for c in user_permissions.allowed_companies if c and c.strip()})
                if user_permissions.unrestricted:
                    specific_scope = [LyOperationWageRate.item_code.isnot(None)]
                    if allowed_companies:
                        specific_scope.append(func.trim(LyOperationWageRate.company).in_(allowed_companies))
                    specific_filter = and_(*specific_scope)
                elif user_permissions.allowed_items:
                    specific_scope = [LyOperationWageRate.item_code.in_(sorted(user_permissions.allowed_items))]
                    if allowed_companies:
                        specific_scope.append(func.trim(LyOperationWageRate.company).in_(allowed_companies))
                    specific_filter = and_(*specific_scope)
                else:
                    # Company-only permissions do not imply Item permissions.
                    specific_filter = None

                global_filter = None
                if allow_global_read:
                    global_scope = [LyOperationWageRate.is_global.is_(True)]
                    if allowed_companies:
                        global_scope.append(func.trim(LyOperationWageRate.company).in_(allowed_companies))
                    global_filter = and_(*global_scope)

                if specific_filter is not None and global_filter is not None:
                    sql = sql.filter(or_(specific_filter, global_filter))
                elif specific_filter is not None:
                    sql = sql.filter(specific_filter)
                elif global_filter is not None:
                    sql = sql.filter(global_filter)
                else:
                    sql = sql.filter(false())
            elif not allow_global_read:
                sql = sql.filter(LyOperationWageRate.is_global.is_(False))

            total = sql.with_entities(func.count(LyOperationWageRate.id)).scalar() or 0
            rows = (
                sql.order_by(LyOperationWageRate.id.desc())
                .offset((query.page - 1) * query.page_size)
                .limit(query.page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        return OperationWageRateListData(
            items=[
                OperationWageRateRow(
                    id=int(row.id),
                    item_code=row.item_code,
                    company=row.company,
                    is_global=bool(row.is_global),
                    process_name=str(row.process_name),
                    wage_rate=self._round(Decimal(row.wage_rate)),
                    effective_from=row.effective_from,
                    effective_to=row.effective_to,
                    status=str(row.status),
                    created_by=str(row.created_by),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in rows
            ],
            total=int(total),
            page=query.page,
            page_size=query.page_size,
        )

    def create_wage_rate(
        self,
        payload: OperationWageRateCreateRequest,
        operator: str,
        resolved_resource: WageRateResource,
    ) -> OperationWageRateCreateData:
        """Create wage rate record with overlap check."""
        if payload.effective_to and payload.effective_to < payload.effective_from:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_OVERLAP, message="工价生效区间重叠")
        self._ensure_wage_rate_no_overlap(
            item_code=resolved_resource.item_code,
            company=resolved_resource.company,
            is_global=resolved_resource.is_global,
            process_name=payload.process_name,
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            exclude_id=None,
        )
        row = LyOperationWageRate(
            item_code=resolved_resource.item_code,
            company=resolved_resource.company,
            is_global=resolved_resource.is_global,
            process_name=payload.process_name,
            wage_rate=self._round(payload.wage_rate),
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            status="active",
            created_by=operator,
            updated_at=datetime.utcnow(),
        )
        try:
            self.session.add(row)
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return OperationWageRateCreateData(
            id=int(row.id),
            item_code=row.item_code,
            company=row.company,
            status=str(row.status),
        )

    def deactivate_wage_rate(self, rate_id: int, operator: str, reason: str) -> OperationWageRateDeactivateData:
        """Deactivate wage rate record."""
        if not reason.strip():
            raise BusinessException(code=WORKSHOP_WAGE_RATE_OVERLAP, message="停用原因不能为空")
        try:
            row = self.session.query(LyOperationWageRate).filter(LyOperationWageRate.id == rate_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_NOT_FOUND, message="未找到生效工价")

        row.status = "inactive"
        row.updated_at = datetime.utcnow()
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return OperationWageRateDeactivateData(id=int(row.id), status=str(row.status))

    def get_ticket_snapshot(self, ticket_id: int) -> dict[str, Any]:
        """Get lightweight ticket snapshot for audit."""
        try:
            row = self.session.query(YsWorkshopTicket).filter(YsWorkshopTicket.id == ticket_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            raise BusinessException(code=WORKSHOP_TICKET_NOT_FOUND, message="工票不存在")
        return {
            "id": int(row.id),
            "ticket_no": row.ticket_no,
            "job_card": row.job_card,
            "employee": row.employee,
            "process_name": row.process_name,
            "operation_type": row.operation_type,
            "qty": str(row.qty),
            "unit_wage": str(row.unit_wage),
            "wage_amount": str(row.wage_amount),
            "sync_status": row.sync_status,
        }

    def get_wage_rate_snapshot(self, rate_id: int) -> dict[str, Any]:
        """Get wage rate snapshot for audit."""
        try:
            row = self.session.query(LyOperationWageRate).filter(LyOperationWageRate.id == rate_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_NOT_FOUND, message="未找到生效工价")
        return {
            "id": int(row.id),
            "item_code": row.item_code,
            "company": row.company,
            "is_global": bool(row.is_global),
            "process_name": row.process_name,
            "wage_rate": str(row.wage_rate),
            "effective_from": row.effective_from.isoformat(),
            "effective_to": row.effective_to.isoformat() if row.effective_to else None,
            "status": row.status,
        }

    def backfill_wage_rate_company_scope(
        self,
        *,
        dry_run: bool = True,
        operator: str = "migration",
    ) -> WageRateCompanyBackfillReport:
        """Backfill legacy item-specific wage rates that miss company scope.

        `dry_run=True` must be strictly read-only:
        - no ORM add/merge/delete
        - no ORM field mutation
        - no flush/commit side effects
        """
        try:
            with self.session.no_autoflush:
                plan = self.build_wage_rate_company_backfill_plan()
                report = self._summarize_backfill_plan(plan)

                if dry_run:
                    return report

                self._apply_wage_rate_company_backfill_plan(plan=plan, operator=operator)
        except (DatabaseReadFailed, ERPNextServiceUnavailableError) as read_exc:
            if not dry_run:
                try:
                    self.session.rollback()
                except Exception as rollback_exc:  # pragma: no cover - rare rollback failure
                    rollback_code = read_exc.code if isinstance(read_exc, AppException) else DATABASE_READ_FAILED
                    log_safe_error(
                        logger,
                        "workshop_backfill_rollback_failed",
                        rollback_exc,
                        extra={
                            "error_code": rollback_code,
                            "module": "workshop",
                            "action": "workshop:wage_rate_backfill",
                        },
                    )
            raise

        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc
        return report

    def build_wage_rate_company_backfill_plan(self) -> list[WageRateCompanyBackfillPlanRow]:
        """Build pure read-only backfill plan rows."""
        try:
            db_rows = (
                self.session.query(LyOperationWageRate)
                .filter(
                    and_(
                        LyOperationWageRate.item_code.isnot(None),
                        self._is_missing_company_expr(LyOperationWageRate.company),
                        LyOperationWageRate.status == "active",
                    )
                )
                .order_by(LyOperationWageRate.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        legacy_by_id: dict[int, LyOperationWageRate] = {}
        for row in db_rows:
            if row.id is None:
                continue
            legacy_by_id[int(row.id)] = row

        for obj in self.session.new:
            if not isinstance(obj, LyOperationWageRate):
                continue
            if obj.id is None:
                continue
            if obj.item_code is None:
                continue
            if obj.status != "active":
                continue
            if not self._is_missing_company(obj.company):
                continue
            legacy_by_id[int(obj.id)] = obj

        legacy_rows = [legacy_by_id[k] for k in sorted(legacy_by_id.keys())]
        plan: list[WageRateCompanyBackfillPlanRow] = []
        for row in legacy_rows:
            item_code = str(row.item_code or "").strip()
            old_company = row.company
            normalized_company = self._normalize_company(old_company)
            candidates = self._resolve_backfill_companies(item_code=item_code)
            if len(candidates) == 1:
                plan.append(
                    WageRateCompanyBackfillPlanRow(
                        wage_rate_id=int(row.id),
                        item_code=item_code,
                        old_company=old_company,
                        normalized_company=normalized_company,
                        planned_company=sorted(candidates)[0],
                        planned_action="backfilled",
                        reason_code="unique_company",
                    )
                )
            elif len(candidates) > 1:
                plan.append(
                    WageRateCompanyBackfillPlanRow(
                        wage_rate_id=int(row.id),
                        item_code=item_code,
                        old_company=old_company,
                        normalized_company=normalized_company,
                        planned_company=None,
                        planned_action="blocked",
                        reason_code=WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS,
                    )
                )
            else:
                plan.append(
                    WageRateCompanyBackfillPlanRow(
                        wage_rate_id=int(row.id),
                        item_code=item_code,
                        old_company=old_company,
                        normalized_company=normalized_company,
                        planned_company=None,
                        planned_action="blocked",
                        reason_code=WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED,
                    )
                )
        return plan

    @staticmethod
    def _summarize_backfill_plan(plan: list[WageRateCompanyBackfillPlanRow]) -> WageRateCompanyBackfillReport:
        total_scanned = len(plan)
        backfilled_count = sum(1 for row in plan if row.planned_action == "backfilled")
        blocked_count = sum(1 for row in plan if row.planned_action == "blocked")
        ambiguous_count = sum(1 for row in plan if row.reason_code == WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS)
        unresolved_count = sum(1 for row in plan if row.reason_code == WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED)
        unchanged_count = sum(1 for row in plan if row.planned_action == "unchanged")
        return WageRateCompanyBackfillReport(
            total_scanned=total_scanned,
            backfilled_count=backfilled_count,
            blocked_count=blocked_count,
            ambiguous_count=ambiguous_count,
            unresolved_count=unresolved_count,
            unchanged_count=unchanged_count,
        )

    def _apply_wage_rate_company_backfill_plan(
        self,
        *,
        plan: list[WageRateCompanyBackfillPlanRow],
        operator: str,
    ) -> None:
        """Apply backfill plan in execute mode only."""
        del operator  # reserved for future audit extension
        for row_plan in plan:
            row = self._find_wage_rate_for_backfill_apply(row_plan.wage_rate_id)
            if row is None:
                continue
            if row.item_code is None or row.status != "active" or not self._is_missing_company(row.company):
                continue

            old_company_raw = row.company
            normalized_old_company = self._normalize_company(old_company_raw)
            if old_company_raw is not None and normalized_old_company is None:
                row.company = None
                row.updated_at = datetime.utcnow()
                self._record_wage_rate_backfill_log(
                    wage_rate_id=int(row.id),
                    item_code=str(row.item_code or ""),
                    old_company=old_company_raw,
                    new_company=None,
                    result="normalized_blank_company",
                    reason="normalized_blank_company",
                )

            if row_plan.planned_action == "backfilled":
                row.company = row_plan.planned_company
                row.updated_at = datetime.utcnow()
                self._record_wage_rate_backfill_log(
                    wage_rate_id=int(row.id),
                    item_code=str(row.item_code or ""),
                    old_company=normalized_old_company,
                    new_company=row_plan.planned_company,
                    result="backfilled",
                    reason=row_plan.reason_code,
                )
                continue

            if row_plan.planned_action == "blocked":
                row.status = "inactive"
                row.updated_at = datetime.utcnow()
                self._record_wage_rate_backfill_log(
                    wage_rate_id=int(row.id),
                    item_code=str(row.item_code or ""),
                    old_company=normalized_old_company,
                    new_company=None,
                    result="blocked",
                    reason=row_plan.reason_code,
                )

    def _find_wage_rate_for_backfill_apply(self, wage_rate_id: int) -> LyOperationWageRate | None:
        for obj in self.session.new:
            if isinstance(obj, LyOperationWageRate) and obj.id is not None and int(obj.id) == wage_rate_id:
                return obj
        try:
            return (
                self.session.query(LyOperationWageRate)
                .filter(LyOperationWageRate.id == wage_rate_id)
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _handle_batch_row(
        self,
        *,
        row: WorkshopTicketBatchItem,
        operator: str,
        request_id: str,
        resolved_resource: WorkshopResourceContext | None = None,
        row_guard: Any | None = None,
    ) -> WorkshopTicketData:
        row_resource = resolved_resource or self.resolve_job_card_resource(
            job_card=row.job_card,
            process_name=row.process_name,
            request_item_code=row.item_code,
            enforce_status=True,
        )
        if callable(row_guard):
            row_guard(row, row_resource)

        operation_type = row.operation_type.strip().lower()
        if operation_type == self.OP_REGISTER:
            return self.register_ticket(
                payload=WorkshopTicketRegisterRequest(
                    ticket_key=row.ticket_key,
                    job_card=row.job_card,
                    item_code=row.item_code,
                    employee=row.employee,
                    process_name=row.process_name,
                    color=row.color,
                    size=row.size,
                    qty=row.qty,
                    work_date=row.work_date,
                    source=row.source,
                    source_ref=row.source_ref,
                ),
                operator=operator,
                request_id=request_id,
                resolved_resource=row_resource,
            )
        if operation_type == self.OP_REVERSAL:
            reversal_result = self.reverse_ticket(
                payload=WorkshopTicketReversalRequest(
                    ticket_key=row.ticket_key,
                    job_card=row.job_card,
                    item_code=row.item_code,
                    employee=row.employee,
                    process_name=row.process_name,
                    color=row.color,
                    size=row.size,
                    qty=row.qty,
                    work_date=row.work_date,
                    original_ticket_id=row.original_ticket_id,
                    reason=row.reason or "batch reversal",
                ),
                operator=operator,
                request_id=request_id,
                resolved_resource=row_resource,
            )
            return WorkshopTicketData(
                ticket_no=reversal_result.ticket_no,
                ticket_id=reversal_result.ticket_id,
                unit_wage=self._round(reversal_result.wage_amount / row.qty),
                wage_amount=reversal_result.wage_amount,
                sync_status=reversal_result.sync_status,
                sync_outbox_id=reversal_result.sync_outbox_id,
            )
        raise BusinessException(code=WORKSHOP_IDEMPOTENCY_CONFLICT, message="operation_type 非法")

    def _get_job_card_or_raise(self, *, job_card: str) -> JobCardInfo:
        try:
            data = self.erp_adapter.get_job_card(job_card=job_card)
        except ERPNextServiceUnavailableError as exc:
            raise BusinessException(code=ERPNEXT_SERVICE_UNAVAILABLE, message=exc.message) from exc
        if not data:
            raise BusinessException(code=WORKSHOP_JOB_CARD_NOT_FOUND, message="Job Card 不存在")
        return data

    @staticmethod
    def _validate_job_card(*, job_card_info: JobCardInfo, process_name: str, enforce_status: bool) -> None:
        if enforce_status and job_card_info.status.strip().lower() in {"cancelled", "closed"}:
            raise BusinessException(code=WORKSHOP_JOB_CARD_STATUS_INVALID, message="Job Card 状态不允许登记工票")
        if job_card_info.operation and job_card_info.operation.strip().lower() != process_name.strip().lower():
            raise BusinessException(code=WORKSHOP_PROCESS_MISMATCH, message="工票工序与 Job Card 工序不一致")

    def _get_work_order_safe(self, work_order: str | None) -> WorkOrderInfo | None:
        if not work_order:
            return None
        try:
            return self.erp_adapter.get_work_order(work_order=work_order)
        except ERPNextServiceUnavailableError as exc:
            raise BusinessException(code=ERPNEXT_SERVICE_UNAVAILABLE, message=exc.message) from exc

    @staticmethod
    def _derive_item_code(*, job_card_info: JobCardInfo, work_order_info: WorkOrderInfo | None) -> str:
        item_code = ""
        if work_order_info and work_order_info.production_item:
            item_code = work_order_info.production_item.strip()
        if not item_code and job_card_info.item_code:
            item_code = job_card_info.item_code.strip()
        if not item_code:
            raise BusinessException(code=WORKSHOP_JOB_CARD_ITEM_NOT_FOUND, message="无法从 Job Card / Work Order 派生 item_code")
        return item_code

    @staticmethod
    def _derive_company(*, job_card_info: JobCardInfo, work_order_info: WorkOrderInfo | None) -> str:
        company = ""
        if work_order_info and work_order_info.company:
            company = work_order_info.company.strip()
        if not company and job_card_info.company:
            company = job_card_info.company.strip()
        if not company:
            raise BusinessException(code=WORKSHOP_JOB_CARD_COMPANY_NOT_FOUND, message="无法从 Job Card / Work Order 派生 company")
        return company

    def _require_employee(self, employee: str):
        try:
            data = self.erp_adapter.get_employee(employee=employee)
        except ERPNextServiceUnavailableError as exc:
            raise BusinessException(code=ERPNEXT_SERVICE_UNAVAILABLE, message=exc.message) from exc
        if not data or not data.is_active:
            raise BusinessException(code=WORKSHOP_EMPLOYEE_NOT_FOUND, message="员工不存在或无效")
        return data

    def _get_item_or_raise(self, *, item_code: str) -> ItemInfo:
        try:
            item_info = self.erp_adapter.get_item(item_code=item_code)
        except ERPNextServiceUnavailableError as exc:
            raise BusinessException(code=ERPNEXT_SERVICE_UNAVAILABLE, message=exc.message) from exc
        if not item_info or not item_info.is_active:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_NOT_FOUND, message="款式不存在或已禁用")
        return item_info

    def _require_company_exists(self, company: str) -> None:
        try:
            company_info = self.erp_adapter.get_company(company=company)
        except ERPNextServiceUnavailableError as exc:
            raise BusinessException(code=ERPNEXT_SERVICE_UNAVAILABLE, message=exc.message) from exc
        if not company_info or not company_info.is_active:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_COMPANY_REQUIRED, message="company 不存在或无效")

    def _resolve_company_for_item(self, *, item_info: ItemInfo) -> str:
        if len(item_info.companies) == 1:
            return item_info.companies[0]
        if len(item_info.companies) > 1:
            raise BusinessException(code=WORKSHOP_WAGE_RATE_COMPANY_REQUIRED, message="item_code 命中多个 company，请指定 company")

        try:
            active_companies: list[CompanyInfo] = self.erp_adapter.list_active_companies()
        except ERPNextServiceUnavailableError as exc:
            raise BusinessException(code=ERPNEXT_SERVICE_UNAVAILABLE, message=exc.message) from exc
        if len(active_companies) == 1:
            return active_companies[0].name
        raise BusinessException(code=WORKSHOP_WAGE_RATE_COMPANY_REQUIRED, message="无法从 Item 解析 company，请指定 company")

    def _resolve_unit_wage(self, *, item_code: str, company: str, process_name: str, work_date: date) -> Decimal:
        try:
            specific_rows = (
                self.session.query(LyOperationWageRate)
                .filter(
                    and_(
                        LyOperationWageRate.status == "active",
                        LyOperationWageRate.is_global.is_(False),
                        LyOperationWageRate.item_code == item_code,
                        LyOperationWageRate.company == company,
                        LyOperationWageRate.process_name == process_name,
                        LyOperationWageRate.effective_from <= work_date,
                        or_(LyOperationWageRate.effective_to.is_(None), LyOperationWageRate.effective_to >= work_date),
                    )
                )
                .order_by(desc(LyOperationWageRate.effective_from), desc(LyOperationWageRate.id))
                .all()
            )
            if specific_rows:
                return self._round(Decimal(specific_rows[0].wage_rate))

            legacy_specific_without_scope = (
                self.session.query(LyOperationWageRate.id)
                .filter(
                    and_(
                        LyOperationWageRate.status == "active",
                        LyOperationWageRate.is_global.is_(False),
                        LyOperationWageRate.item_code == item_code,
                        self._is_missing_company_expr(LyOperationWageRate.company),
                        LyOperationWageRate.process_name == process_name,
                        LyOperationWageRate.effective_from <= work_date,
                        or_(LyOperationWageRate.effective_to.is_(None), LyOperationWageRate.effective_to >= work_date),
                    )
                )
                .first()
            )
            if legacy_specific_without_scope:
                raise BusinessException(
                    code=WORKSHOP_WAGE_RATE_SCOPE_REQUIRED,
                    message="历史工价缺少 company 作用域，禁止参与计薪",
                )

            common_rows = (
                self.session.query(LyOperationWageRate)
                .filter(
                    and_(
                        LyOperationWageRate.status == "active",
                        LyOperationWageRate.is_global.is_(True),
                        LyOperationWageRate.item_code.is_(None),
                        LyOperationWageRate.company == company,
                        LyOperationWageRate.process_name == process_name,
                        LyOperationWageRate.effective_from <= work_date,
                        or_(LyOperationWageRate.effective_to.is_(None), LyOperationWageRate.effective_to >= work_date),
                    )
                )
                .order_by(desc(LyOperationWageRate.effective_from), desc(LyOperationWageRate.id))
                .all()
            )
            if not common_rows:
                legacy_global_without_scope = (
                    self.session.query(LyOperationWageRate.id)
                    .filter(
                        and_(
                            LyOperationWageRate.status == "active",
                            LyOperationWageRate.is_global.is_(True),
                            LyOperationWageRate.item_code.is_(None),
                            self._is_missing_company_expr(LyOperationWageRate.company),
                            LyOperationWageRate.process_name == process_name,
                            LyOperationWageRate.effective_from <= work_date,
                            or_(LyOperationWageRate.effective_to.is_(None), LyOperationWageRate.effective_to >= work_date),
                        )
                    )
                    .first()
                )
                if legacy_global_without_scope:
                    raise BusinessException(
                        code=WORKSHOP_WAGE_RATE_SCOPE_REQUIRED,
                        message="历史工价缺少 company 作用域，禁止参与计薪",
                    )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if common_rows:
            return self._round(Decimal(common_rows[0].wage_rate))
        raise BusinessException(code=WORKSHOP_WAGE_RATE_NOT_FOUND, message="未找到生效工价")

    def _resolve_reversal_wage(self, *, payload: WorkshopTicketReversalRequest, item_code: str, company: str) -> Decimal:
        if payload.original_ticket_id:
            try:
                original = (
                    self.session.query(YsWorkshopTicket)
                    .filter(YsWorkshopTicket.id == payload.original_ticket_id)
                    .first()
                )
            except SQLAlchemyError as exc:
                raise DatabaseReadFailed() from exc
            if original:
                return self._round(Decimal(original.unit_wage))
        return self._resolve_unit_wage(
            item_code=item_code,
            company=company,
            process_name=payload.process_name,
            work_date=payload.work_date,
        )

    def _validate_original_ticket_for_reversal(self, *, payload: WorkshopTicketReversalRequest) -> None:
        if payload.original_ticket_id is None:
            return
        try:
            original = self.session.query(YsWorkshopTicket).filter(YsWorkshopTicket.id == payload.original_ticket_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not original:
            raise BusinessException(code=WORKSHOP_TICKET_NOT_FOUND, message="工票不存在")

        if (
            original.operation_type != self.OP_REGISTER
            or original.job_card != payload.job_card
            or original.work_date != payload.work_date
            or original.employee != payload.employee
            or original.process_name != payload.process_name
            or (original.color or "") != (payload.color or "")
            or (original.size or "") != (payload.size or "")
        ):
            raise BusinessException(code=WORKSHOP_IDEMPOTENCY_CONFLICT, message="original_ticket_id 与撤销维度不一致")

    def _get_by_idempotent(
        self,
        *,
        ticket_key: str,
        process_name: str,
        color: str | None,
        size: str | None,
        operation_type: str,
        work_date: date,
    ) -> YsWorkshopTicket | None:
        try:
            return (
                self.session.query(YsWorkshopTicket)
                .filter(
                    and_(
                        YsWorkshopTicket.ticket_key == ticket_key,
                        YsWorkshopTicket.process_name == process_name,
                        YsWorkshopTicket.color.is_(color) if color is None else YsWorkshopTicket.color == color,
                        YsWorkshopTicket.size.is_(size) if size is None else YsWorkshopTicket.size == size,
                        YsWorkshopTicket.operation_type == operation_type,
                        YsWorkshopTicket.work_date == work_date,
                    )
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

    def _is_same_register_payload(self, row: YsWorkshopTicket, *, payload: WorkshopTicketRegisterRequest, item_code: str, work_order: str | None) -> bool:
        return (
            row.job_card == payload.job_card
            and row.work_order == work_order
            and row.item_code == item_code
            and row.employee == payload.employee
            and row.process_name == payload.process_name
            and (row.color or "") == (payload.color or "")
            and (row.size or "") == (payload.size or "")
            and self._round(Decimal(row.qty)) == self._round(payload.qty)
            and row.work_date == payload.work_date
            and row.source == payload.source
            and (row.source_ref or "") == (payload.source_ref or "")
            and row.operation_type == self.OP_REGISTER
        )

    def _is_same_reversal_payload(self, row: YsWorkshopTicket, *, payload: WorkshopTicketReversalRequest, item_code: str, work_order: str | None) -> bool:
        return (
            row.job_card == payload.job_card
            and row.work_order == work_order
            and row.item_code == item_code
            and row.employee == payload.employee
            and row.process_name == payload.process_name
            and (row.color or "") == (payload.color or "")
            and (row.size or "") == (payload.size or "")
            and self._round(Decimal(row.qty)) == self._round(payload.qty)
            and row.work_date == payload.work_date
            and row.operation_type == self.OP_REVERSAL
            and (row.original_ticket_id or 0) == (payload.original_ticket_id or 0)
        )

    def _available_reversal_qty(
        self,
        *,
        job_card: str,
        employee: str,
        process_name: str,
        color: str | None,
        size: str | None,
        work_date: date,
    ) -> Decimal:
        try:
            rows = (
                self.session.query(YsWorkshopTicket)
                .filter(
                    and_(
                        YsWorkshopTicket.job_card == job_card,
                        YsWorkshopTicket.employee == employee,
                        YsWorkshopTicket.process_name == process_name,
                        YsWorkshopTicket.color.is_(color) if color is None else YsWorkshopTicket.color == color,
                        YsWorkshopTicket.size.is_(size) if size is None else YsWorkshopTicket.size == size,
                        YsWorkshopTicket.work_date == work_date,
                    )
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        register_qty = Decimal("0")
        reversal_qty = Decimal("0")
        for row in rows:
            if row.operation_type == self.OP_REGISTER:
                register_qty += Decimal(row.qty)
            elif row.operation_type == self.OP_REVERSAL:
                reversal_qty += Decimal(row.qty)
        return self._round(register_qty - reversal_qty)

    def _refresh_daily_wage(self, *, employee: str, work_date: date, process_name: str, item_code: str) -> None:
        try:
            rows = (
                self.session.query(YsWorkshopTicket)
                .filter(
                    and_(
                        YsWorkshopTicket.employee == employee,
                        YsWorkshopTicket.work_date == work_date,
                        YsWorkshopTicket.process_name == process_name,
                        YsWorkshopTicket.item_code == item_code,
                    )
                )
                .order_by(asc(YsWorkshopTicket.id))
                .all()
            )
            daily = (
                self.session.query(YsWorkshopDailyWage)
                .filter(
                    and_(
                        YsWorkshopDailyWage.employee == employee,
                        YsWorkshopDailyWage.work_date == work_date,
                        YsWorkshopDailyWage.process_name == process_name,
                        YsWorkshopDailyWage.item_code == item_code,
                    )
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        register_qty = Decimal("0")
        reversal_qty = Decimal("0")
        register_amount = Decimal("0")
        reversal_amount = Decimal("0")
        last_ticket_at = None

        for row in rows:
            qty = Decimal(row.qty)
            amount = Decimal(row.wage_amount)
            if row.operation_type == self.OP_REGISTER:
                register_qty += qty
                register_amount += amount
            else:
                reversal_qty += qty
                reversal_amount += amount
            if last_ticket_at is None or (row.created_at and row.created_at > last_ticket_at):
                last_ticket_at = row.created_at

        net_qty = register_qty - reversal_qty
        wage_amount = register_amount - reversal_amount
        now = datetime.utcnow()

        if daily is None:
            daily = YsWorkshopDailyWage(
                employee=employee,
                work_date=work_date,
                process_name=process_name,
                item_code=item_code,
                register_qty=self._round(register_qty),
                reversal_qty=self._round(reversal_qty),
                net_qty=self._round(net_qty),
                wage_amount=self._round(wage_amount),
                last_ticket_at=last_ticket_at,
                updated_at=now,
            )
            self.session.add(daily)
        else:
            daily.register_qty = self._round(register_qty)
            daily.reversal_qty = self._round(reversal_qty)
            daily.net_qty = self._round(net_qty)
            daily.wage_amount = self._round(wage_amount)
            daily.last_ticket_at = last_ticket_at
            daily.updated_at = now
        try:
            self.session.flush()
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def _enqueue_sync_outbox(
        self,
        *,
        ticket: YsWorkshopTicket,
        company: str,
        request_id: str,
        source_type: str,
        source_ids: list[int],
        created_by: str,
    ) -> YsWorkshopJobCardSyncOutbox:
        _, _, net_qty, _, _ = self._calc_job_card_totals(job_card=ticket.job_card)
        return self.outbox_service.enqueue(
            job_card=ticket.job_card,
            work_order=ticket.work_order,
            item_code=ticket.item_code,
            company=company,
            local_completed_qty=net_qty,
            source_type=source_type,
            source_ids=source_ids,
            request_id=request_id,
            created_by=created_by,
            max_attempts=5,
        )

    def _calc_job_card_totals(self, *, job_card: str) -> tuple[Decimal, Decimal, Decimal, str, str | None]:
        try:
            rows = (
                self.session.query(YsWorkshopTicket)
                .filter(YsWorkshopTicket.job_card == job_card)
                .order_by(YsWorkshopTicket.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        register_qty = Decimal("0")
        reversal_qty = Decimal("0")
        latest_sync_status = self.SYNC_PENDING
        item_code: str | None = None
        for row in rows:
            item_code = item_code or row.item_code
            if row.operation_type == self.OP_REGISTER:
                register_qty += Decimal(row.qty)
            elif row.operation_type == self.OP_REVERSAL:
                reversal_qty += Decimal(row.qty)
            latest_sync_status = row.sync_status

        return self._round(register_qty), self._round(reversal_qty), self._round(register_qty - reversal_qty), latest_sync_status, item_code

    def _resolve_backfill_companies(self, *, item_code: str) -> set[str]:
        candidates: set[str] = set()
        if not item_code:
            return candidates
        try:
            rows = (
                self.session.query(LyOperationWageRate.company)
                .filter(
                    and_(
                        LyOperationWageRate.item_code == item_code,
                        self._has_company_scope_expr(LyOperationWageRate.company),
                    )
                )
                .all()
            )
        except SQLAlchemyError as exc:
            log_safe_error(
                logger,
                "workshop_backfill_company_candidates_read_failed",
                exc,
                extra={
                    "error_code": DATABASE_READ_FAILED,
                    "module": "workshop",
                    "action": "workshop:wage_rate_backfill_resolve_company",
                    "resource_type": "WageRate",
                    "resource_no": item_code,
                },
            )
            raise DatabaseReadFailed() from exc
        for (company_value,) in rows:
            if isinstance(company_value, str) and company_value.strip():
                candidates.add(company_value.strip())
        for obj in self.session.new:
            if not isinstance(obj, LyOperationWageRate):
                continue
            if obj.item_code != item_code:
                continue
            normalized_company = self._normalize_company(obj.company)
            if normalized_company is not None:
                candidates.add(normalized_company)
        if candidates:
            return candidates

        try:
            item_info = self.erp_adapter.get_item(item_code=item_code)
        except ERPNextServiceUnavailableError as exc:
            log_safe_error(
                logger,
                "workshop_backfill_item_lookup_unavailable",
                exc,
                extra={
                    "error_code": ERPNEXT_SERVICE_UNAVAILABLE,
                    "module": "workshop",
                    "action": "workshop:wage_rate_backfill_resolve_company",
                    "resource_type": "Item",
                    "resource_no": item_code,
                },
            )
            raise
        if item_info and item_info.is_active:
            for company in item_info.companies:
                if company and company.strip():
                    candidates.add(company.strip())
        return candidates

    def _record_wage_rate_backfill_log(
        self,
        *,
        wage_rate_id: int,
        item_code: str,
        old_company: str | None,
        new_company: str | None,
        result: str,
        reason: str,
    ) -> None:
        try:
            exists = (
                self.session.query(LyOperationWageRateCompanyBackfillLog.id)
                .filter(
                    and_(
                        LyOperationWageRateCompanyBackfillLog.wage_rate_id == wage_rate_id,
                        LyOperationWageRateCompanyBackfillLog.result == result,
                        LyOperationWageRateCompanyBackfillLog.new_company.is_(new_company)
                        if new_company is None
                        else LyOperationWageRateCompanyBackfillLog.new_company == new_company,
                        LyOperationWageRateCompanyBackfillLog.reason == reason,
                    )
                )
                .first()
            )
            if exists:
                return
            self.session.add(
                LyOperationWageRateCompanyBackfillLog(
                    wage_rate_id=wage_rate_id,
                    item_code=item_code,
                    old_company=old_company,
                    new_company=new_company,
                    result=result,
                    reason=reason,
                )
            )
        except SQLAlchemyError as exc:
            raise DatabaseWriteFailed() from exc

    def _ensure_wage_rate_no_overlap(
        self,
        *,
        item_code: str | None,
        company: str | None,
        is_global: bool,
        process_name: str,
        effective_from: date,
        effective_to: date | None,
        exclude_id: int | None,
    ) -> None:
        far_future = date(2999, 12, 31)
        end_date = effective_to or far_future
        try:
            filters = [
                LyOperationWageRate.status == "active",
                LyOperationWageRate.process_name == process_name,
                self._is_missing_company_expr(LyOperationWageRate.company)
                if company is None
                else LyOperationWageRate.company == company,
                LyOperationWageRate.is_global.is_(is_global),
            ]
            if is_global:
                filters.append(LyOperationWageRate.item_code.is_(None))
            else:
                filters.append(LyOperationWageRate.item_code == item_code)

            sql = self.session.query(LyOperationWageRate).filter(and_(*filters))
            if exclude_id:
                sql = sql.filter(LyOperationWageRate.id != exclude_id)
            rows = sql.all()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc

        for row in rows:
            row_start = row.effective_from
            row_end = row.effective_to or far_future
            if effective_from <= row_end and row_start <= end_date:
                raise BusinessException(code=WORKSHOP_WAGE_RATE_OVERLAP, message="工价生效区间重叠")

    @staticmethod
    def _raise_write_error(exc: IntegrityError) -> None:
        text = str(exc).lower()
        if "uk_ys_workshop_ticket_idempotent" in text:
            raise BusinessException(code=WORKSHOP_IDEMPOTENCY_CONFLICT, message="幂等键冲突，且请求内容不一致") from exc
        raise DatabaseWriteFailed() from exc

    @staticmethod
    def _to_ticket_data(ticket: YsWorkshopTicket, sync_outbox_id: int | None = None) -> WorkshopTicketData:
        return WorkshopTicketData(
            ticket_no=ticket.ticket_no,
            ticket_id=int(ticket.id),
            unit_wage=WorkshopService._round(Decimal(ticket.unit_wage)),
            wage_amount=WorkshopService._round(Decimal(ticket.wage_amount)),
            sync_status=ticket.sync_status,
            sync_outbox_id=sync_outbox_id,
        )

    @staticmethod
    def _build_ticket_no() -> str:
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        return f"TICKET-{ts}"

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        return Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @staticmethod
    def _normalize_company(value: str | None) -> str | None:
        return WorkshopService._normalize_text(value)

    @staticmethod
    def _is_missing_company(value: str | None) -> bool:
        return WorkshopService._normalize_company(value) is None

    @staticmethod
    def _is_missing_company_expr(column: Any):
        return or_(column.is_(None), func.trim(column) == "")

    @staticmethod
    def _has_company_scope_expr(column: Any):
        return and_(column.isnot(None), func.trim(column) != "")
