"""Business service for factory statement draft APIs (TASK-006B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
from decimal import Decimal
from decimal import ROUND_HALF_UP
import hashlib
import json
import uuid

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import FACTORY_STATEMENT_COMPANY_REQUIRED
from app.core.error_codes import FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS
from app.core.error_codes import FACTORY_STATEMENT_COST_CENTER_INVALID
from app.core.error_codes import FACTORY_STATEMENT_DATABASE_READ_FAILED
from app.core.error_codes import FACTORY_STATEMENT_DATABASE_WRITE_FAILED
from app.core.error_codes import FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE
from app.core.error_codes import FACTORY_STATEMENT_INVALID_STATUS
from app.core.error_codes import FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT
from app.core.error_codes import FACTORY_STATEMENT_INTERNAL_ERROR
from app.core.error_codes import FACTORY_STATEMENT_PAYABLE_ACCOUNT_INVALID
from app.core.error_codes import FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED
from app.core.error_codes import FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE
from app.core.error_codes import FACTORY_STATEMENT_PERIOD_INVALID
from app.core.error_codes import FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED
from app.core.error_codes import FACTORY_STATEMENT_SOURCE_NOT_FOUND
from app.core.error_codes import FACTORY_STATEMENT_STATUS_INVALID
from app.core.error_codes import FACTORY_STATEMENT_SUPPLIER_REQUIRED
from app.core.exceptions import BusinessException
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementItem
from app.models.factory_statement import LyFactoryStatementLog
from app.models.factory_statement import LyFactoryStatementOperation
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.schemas.factory_statement import FactoryStatementCancelData
from app.schemas.factory_statement import FactoryStatementCancelRequest
from app.schemas.factory_statement import FactoryStatementConfirmData
from app.schemas.factory_statement import FactoryStatementConfirmRequest
from app.schemas.factory_statement import FactoryStatementCreateData
from app.schemas.factory_statement import FactoryStatementCreateRequest
from app.schemas.factory_statement import FactoryStatementDetailData
from app.schemas.factory_statement import FactoryStatementItemData
from app.schemas.factory_statement import FactoryStatementListData
from app.schemas.factory_statement import FactoryStatementListItem
from app.schemas.factory_statement import FactoryStatementLogData
from app.schemas.factory_statement import FactoryStatementPayableDraftData
from app.schemas.factory_statement import FactoryStatementPayableOutboxData
from app.schemas.factory_statement import FactoryStatementPayableDraftRequest
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from app.services.factory_statement_payable_outbox_service import FactoryStatementPayableOutboxService


class FactoryStatementBusinessException(BusinessException):
    """Business exception with optional response data payload."""

    def __init__(self, *, code: str, data: dict[str, object] | None = None):
        super().__init__(code=code)
        self.data = data or {}


class FactoryStatementService:
    """Factory statement draft generation from inspection facts."""

    _SOURCE_TYPE = "subcontract_inspection"
    _STATUS_DRAFT = "draft"
    _STATUS_CONFIRMED = "confirmed"
    _STATUS_CANCELLED = "cancelled"
    _STATUS_PAYABLE_DRAFT_CREATED = "payable_draft_created"
    _SETTLEMENT_UNSETTLED = "unsettled"
    _SETTLEMENT_LOCKED = "statement_locked"
    _INSPECTION_STATUS = "inspected"
    _OP_CONFIRM = "confirm"
    _OP_CANCEL = "cancel"
    _OP_PAYABLE_DRAFT_CREATE = "payable_draft_create"

    def __init__(self, session: Session):
        self.session = session

    def create_draft(
        self,
        *,
        payload: FactoryStatementCreateRequest,
        operator: str,
        request_id: str,
    ) -> FactoryStatementCreateData:
        """Create statement draft and lock source inspections (no commit)."""
        company = self._normalize_text(payload.company)
        supplier = self._normalize_text(payload.supplier)
        idempotency_key = self._normalize_text(payload.idempotency_key)
        from_date = payload.from_date
        to_date = payload.to_date

        if not company:
            raise BusinessException(code=FACTORY_STATEMENT_COMPANY_REQUIRED)
        if not supplier:
            raise BusinessException(code=FACTORY_STATEMENT_SUPPLIER_REQUIRED)
        if from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        request_hash = self._build_request_hash(
            company=company,
            supplier=supplier,
            from_date=from_date,
            to_date=to_date,
        )

        existing = self._find_statement_by_idempotency(
            company=company,
            idempotency_key=idempotency_key,
        )

        if existing is not None:
            if str(existing.request_hash or "") == request_hash:
                return self._to_create_data(existing, idempotent_replay=True)
            raise BusinessException(code=FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT)

        from_dt = datetime.combine(from_date, time.min)
        to_dt_exclusive = datetime.combine(to_date + timedelta(days=1), time.min)

        try:
            source_rows = (
                self.session.query(LySubcontractInspection, LySubcontractOrder)
                .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractInspection.subcontract_id)
                .filter(
                    LySubcontractInspection.company == company,
                    LySubcontractOrder.company == company,
                    LySubcontractOrder.supplier == supplier,
                    LySubcontractInspection.status == self._INSPECTION_STATUS,
                    LySubcontractInspection.settlement_status == self._SETTLEMENT_UNSETTLED,
                    LySubcontractInspection.inspected_at >= from_dt,
                    LySubcontractInspection.inspected_at < to_dt_exclusive,
                    LySubcontractInspection.net_amount >= 0,
                )
                .order_by(LySubcontractInspection.inspected_at.asc(), LySubcontractInspection.id.asc())
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

        active_scope_existing = self._find_active_scope_statement(
            company=company,
            supplier=supplier,
            from_date=from_date,
            to_date=to_date,
            request_hash=request_hash,
        )
        if active_scope_existing is not None:
            raise self._active_scope_exists_error(active_scope_existing)

        if not source_rows:
            if self._has_locked_source(
                company=company,
                supplier=supplier,
                from_dt=from_dt,
                to_dt_exclusive=to_dt_exclusive,
            ):
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED)
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)

        try:
            statement = LyFactoryStatement(
                statement_no=self._build_statement_no(),
                company=company,
                supplier=supplier,
                from_date=from_date,
                to_date=to_date,
                source_type=self._SOURCE_TYPE,
                source_count=len(source_rows),
                inspected_qty=Decimal("0"),
                rejected_qty=Decimal("0"),
                accepted_qty=Decimal("0"),
                gross_amount=Decimal("0"),
                deduction_amount=Decimal("0"),
                net_amount=Decimal("0"),
                rejected_rate=Decimal("0"),
                statement_status=self._STATUS_DRAFT,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                created_by=self._normalize_text(operator) or "system",
            )
            self.session.add(statement)
            replay_data = self._flush_statement_or_resolve_replay(
                company=company,
                supplier=supplier,
                from_date=from_date,
                to_date=to_date,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if replay_data is not None:
                return replay_data

            inspected_qty = Decimal("0")
            rejected_qty = Decimal("0")
            accepted_qty = Decimal("0")
            gross_amount = Decimal("0")
            deduction_amount = Decimal("0")
            net_amount = Decimal("0")
            inspection_ids: list[int] = []

            for line_no, (inspection, order) in enumerate(source_rows, start=1):
                inspection_ids.append(int(inspection.id))
                inspected_qty += self._to_decimal(inspection.inspected_qty)
                rejected_qty += self._to_decimal(inspection.rejected_qty)
                accepted_qty += self._to_decimal(inspection.accepted_qty)
                gross_amount += self._to_decimal(inspection.gross_amount)
                deduction_amount += self._to_decimal(inspection.deduction_amount)
                net_amount += self._to_decimal(inspection.net_amount)

                source_snapshot = {
                    "inspection_id": int(inspection.id),
                    "inspection_no": self._normalize_text(inspection.inspection_no),
                    "subcontract_id": int(order.id),
                    "subcontract_no": str(order.subcontract_no),
                    "company": self._normalize_text(inspection.company),
                    "supplier": self._normalize_text(order.supplier),
                    "item_code": self._normalize_text(inspection.item_code),
                    "inspected_at": inspection.inspected_at.isoformat() if inspection.inspected_at else None,
                    "inspected_qty": str(self._to_decimal(inspection.inspected_qty)),
                    "rejected_qty": str(self._to_decimal(inspection.rejected_qty)),
                    "accepted_qty": str(self._to_decimal(inspection.accepted_qty)),
                    "subcontract_rate": str(self._to_decimal(inspection.subcontract_rate)),
                    "gross_amount": str(self._to_decimal(inspection.gross_amount)),
                    "deduction_amount": str(self._to_decimal(inspection.deduction_amount)),
                    "net_amount": str(self._to_decimal(inspection.net_amount)),
                    "rejected_rate": str(self._to_decimal(inspection.rejected_rate)),
                }

                self.session.add(
                    LyFactoryStatementItem(
                        statement_id=int(statement.id),
                        line_no=line_no,
                        inspection_id=int(inspection.id),
                        inspection_no=self._normalize_text(inspection.inspection_no),
                        subcontract_id=int(order.id),
                        subcontract_no=str(order.subcontract_no),
                        company=self._normalize_text(inspection.company) or company,
                        supplier=self._normalize_text(order.supplier) or supplier,
                        item_code=self._normalize_text(inspection.item_code),
                        inspected_at=inspection.inspected_at,
                        inspected_qty=self._to_decimal(inspection.inspected_qty),
                        rejected_qty=self._to_decimal(inspection.rejected_qty),
                        accepted_qty=self._to_decimal(inspection.accepted_qty),
                        subcontract_rate=self._to_decimal(inspection.subcontract_rate),
                        gross_amount=self._to_decimal(inspection.gross_amount),
                        deduction_amount=self._to_decimal(inspection.deduction_amount),
                        net_amount=self._to_decimal(inspection.net_amount),
                        rejected_rate=self._to_decimal(inspection.rejected_rate),
                        source_snapshot=source_snapshot,
                    )
                )

            rejected_rate = self._compute_rejected_rate(
                inspected_qty=inspected_qty,
                rejected_qty=rejected_qty,
            )

            statement.inspected_qty = inspected_qty
            statement.rejected_qty = rejected_qty
            statement.accepted_qty = accepted_qty
            statement.gross_amount = gross_amount
            statement.deduction_amount = deduction_amount
            statement.net_amount = net_amount
            statement.rejected_rate = rejected_rate

            lock_count = (
                self.session.query(LySubcontractInspection)
                .filter(
                    LySubcontractInspection.id.in_(inspection_ids),
                    LySubcontractInspection.settlement_status == self._SETTLEMENT_UNSETTLED,
                )
                .update(
                    {
                        LySubcontractInspection.settlement_status: self._SETTLEMENT_LOCKED,
                        LySubcontractInspection.statement_id: int(statement.id),
                        LySubcontractInspection.statement_no: str(statement.statement_no),
                        LySubcontractInspection.settlement_locked_by: self._normalize_text(operator),
                        LySubcontractInspection.settlement_locked_at: datetime.utcnow(),
                    },
                    synchronize_session=False,
                )
            )
            if lock_count != len(inspection_ids):
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED)

            self.session.add(
                LyFactoryStatementLog(
                    statement_id=int(statement.id),
                    company=company,
                    supplier=supplier,
                    from_status=self._STATUS_DRAFT,
                    to_status=self._STATUS_DRAFT,
                    action="factory_statement:create",
                    operator=self._normalize_text(operator) or "system",
                    request_id=self._normalize_text(request_id),
                    remark="create_draft",
                )
            )
            self.session.flush()
            return self._to_create_data(statement, idempotent_replay=False)
        except BusinessException:
            raise
        except IntegrityError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED) from exc
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
        except Exception as exc:
            raise BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR) from exc

    def list_statements(
        self,
        *,
        company: str | None,
        supplier: str | None,
        from_date: date | None,
        to_date: date | None,
        statement_status: str | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementListData:
        """List statement drafts with permission-scoped filters."""
        normalized_company = self._normalize_text(company)
        normalized_supplier = self._normalize_text(supplier)
        normalized_status = self._normalize_text(statement_status)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        try:
            query = self.session.query(LyFactoryStatement)
            if normalized_company:
                query = query.filter(LyFactoryStatement.company == normalized_company)
            if normalized_supplier:
                query = query.filter(LyFactoryStatement.supplier == normalized_supplier)
            if normalized_status:
                query = query.filter(LyFactoryStatement.statement_status == normalized_status)
            if from_date is not None:
                query = query.filter(LyFactoryStatement.from_date >= from_date)
            if to_date is not None:
                query = query.filter(LyFactoryStatement.to_date <= to_date)

            if readable_companies is not None:
                if not readable_companies:
                    return FactoryStatementListData(items=[], total=0, page=page, page_size=page_size)
                query = query.filter(LyFactoryStatement.company.in_(sorted(readable_companies)))
            if readable_suppliers is not None:
                if not readable_suppliers:
                    return FactoryStatementListData(items=[], total=0, page=page, page_size=page_size)
                query = query.filter(LyFactoryStatement.supplier.in_(sorted(readable_suppliers)))

            total = query.with_entities(func.count(LyFactoryStatement.id)).scalar() or 0
            rows = (
                query.order_by(LyFactoryStatement.created_at.desc(), LyFactoryStatement.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        except Exception as exc:
            raise BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR) from exc

        statement_ids = [int(row.id) for row in rows]
        latest_payable_map = self._fetch_latest_payable_outbox_map(statement_ids=statement_ids)

        return FactoryStatementListData(
            items=[
                FactoryStatementListItem(
                    id=int(row.id),
                    statement_no=str(row.statement_no),
                    company=str(row.company),
                    supplier=str(row.supplier),
                    from_date=row.from_date,
                    to_date=row.to_date,
                    source_count=int(row.source_count or 0),
                    gross_amount=self._to_decimal(row.gross_amount),
                    deduction_amount=self._to_decimal(row.deduction_amount),
                    net_amount=self._to_decimal(row.net_amount),
                    rejected_rate=self._to_decimal(row.rejected_rate),
                    statement_status=str(row.statement_status),
                    payable_outbox_id=(
                        int(latest_payable_map[int(row.id)].id)
                        if latest_payable_map.get(int(row.id)) is not None
                        else None
                    ),
                    payable_outbox_status=(
                        str(latest_payable_map[int(row.id)].status)
                        if latest_payable_map.get(int(row.id)) is not None
                        else None
                    ),
                    purchase_invoice_name=(
                        self._normalize_text(latest_payable_map[int(row.id)].erpnext_purchase_invoice)
                        if latest_payable_map.get(int(row.id)) is not None
                        else None
                    ),
                    payable_error_code=(
                        self._normalize_text(latest_payable_map[int(row.id)].last_error_code)
                        if latest_payable_map.get(int(row.id)) is not None
                        else None
                    ),
                    payable_error_message=(
                        self._normalize_text(latest_payable_map[int(row.id)].last_error_message)
                        if latest_payable_map.get(int(row.id)) is not None
                        else None
                    ),
                    created_by=str(row.created_by),
                    created_at=row.created_at,
                )
                for row in rows
            ],
            total=int(total),
            page=page,
            page_size=page_size,
        )

    def get_statement_detail(self, *, statement_id: int) -> FactoryStatementDetailData:
        """Read statement header and immutable item snapshots."""
        try:
            statement = (
                self.session.query(LyFactoryStatement)
                .filter(LyFactoryStatement.id == statement_id)
                .one_or_none()
            )
            if statement is None:
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)

            items = (
                self.session.query(LyFactoryStatementItem)
                .filter(LyFactoryStatementItem.statement_id == statement_id)
                .order_by(LyFactoryStatementItem.line_no.asc(), LyFactoryStatementItem.id.asc())
                .all()
            )
            logs = (
                self.session.query(LyFactoryStatementLog)
                .filter(LyFactoryStatementLog.statement_id == statement_id)
                .order_by(LyFactoryStatementLog.operated_at.desc(), LyFactoryStatementLog.id.desc())
                .all()
            )
            payable_outboxes = (
                self.session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .order_by(LyFactoryStatementPayableOutbox.created_at.desc(), LyFactoryStatementPayableOutbox.id.desc())
                .all()
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        except Exception as exc:
            raise BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR) from exc

        latest_payable = payable_outboxes[0] if payable_outboxes else None

        return FactoryStatementDetailData(
            statement_id=int(statement.id),
            statement_no=str(statement.statement_no),
            statement_status=str(statement.statement_status),
            company=str(statement.company),
            supplier=str(statement.supplier),
            from_date=statement.from_date,
            to_date=statement.to_date,
            source_count=int(statement.source_count or 0),
            inspected_qty=self._to_decimal(statement.inspected_qty),
            rejected_qty=self._to_decimal(statement.rejected_qty),
            accepted_qty=self._to_decimal(statement.accepted_qty),
            gross_amount=self._to_decimal(statement.gross_amount),
            deduction_amount=self._to_decimal(statement.deduction_amount),
            net_amount=self._to_decimal(statement.net_amount),
            rejected_rate=self._to_decimal(statement.rejected_rate),
            idempotency_key=str(statement.idempotency_key),
            created_by=str(statement.created_by),
            created_at=statement.created_at,
            payable_outbox_id=int(latest_payable.id) if latest_payable is not None else None,
            payable_outbox_status=str(latest_payable.status) if latest_payable is not None else None,
            purchase_invoice_name=(
                self._normalize_text(latest_payable.erpnext_purchase_invoice) if latest_payable is not None else None
            ),
            payable_error_code=(
                self._normalize_text(latest_payable.last_error_code) if latest_payable is not None else None
            ),
            payable_error_message=(
                self._normalize_text(latest_payable.last_error_message) if latest_payable is not None else None
            ),
            items=[
                FactoryStatementItemData(
                    id=int(row.id),
                    line_no=int(row.line_no),
                    inspection_id=int(row.inspection_id),
                    inspection_no=self._normalize_text(row.inspection_no),
                    subcontract_id=int(row.subcontract_id),
                    subcontract_no=str(row.subcontract_no),
                    company=str(row.company),
                    supplier=str(row.supplier),
                    item_code=self._normalize_text(row.item_code),
                    inspected_at=row.inspected_at,
                    inspected_qty=self._to_decimal(row.inspected_qty),
                    rejected_qty=self._to_decimal(row.rejected_qty),
                    accepted_qty=self._to_decimal(row.accepted_qty),
                    subcontract_rate=self._to_decimal(row.subcontract_rate),
                    gross_amount=self._to_decimal(row.gross_amount),
                    deduction_amount=self._to_decimal(row.deduction_amount),
                    net_amount=self._to_decimal(row.net_amount),
                    rejected_rate=self._to_decimal(row.rejected_rate),
                )
                for row in items
            ],
            logs=[
                FactoryStatementLogData(
                    action=str(log.action),
                    operator=str(log.operator),
                    operated_at=log.operated_at,
                    remark=self._normalize_text(log.remark),
                    from_status=self._normalize_text(log.from_status),
                    to_status=self._normalize_text(log.to_status),
                )
                for log in logs
            ],
            payable_outboxes=[
                FactoryStatementPayableOutboxData(
                    id=int(row.id),
                    status=str(row.status),
                    erpnext_purchase_invoice=self._normalize_text(row.erpnext_purchase_invoice),
                    erpnext_docstatus=int(row.erpnext_docstatus) if row.erpnext_docstatus is not None else None,
                    erpnext_status=self._normalize_text(row.erpnext_status),
                    last_error_code=self._normalize_text(row.last_error_code),
                    last_error_message=self._normalize_text(row.last_error_message),
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
                for row in payable_outboxes
            ],
        )

    def confirm_statement(
        self,
        *,
        statement_id: int,
        payload: FactoryStatementConfirmRequest,
        operator: str,
        request_id: str,
    ) -> FactoryStatementConfirmData:
        """Confirm factory statement in local system only."""
        idempotency_key = self._normalize_text(payload.idempotency_key)
        remark = self._normalize_text(payload.remark)

        statement = self._find_statement_by_id(statement_id=statement_id)
        if statement is None:
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)

        request_hash = self._build_operation_hash(
            statement_id=statement_id,
            operation_type=self._OP_CONFIRM,
            remark=remark,
        )

        existing = self._find_operation_by_idempotency(
            company=str(statement.company),
            statement_id=statement_id,
            operation_type=self._OP_CONFIRM,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            if str(existing.request_hash or "") != request_hash:
                raise BusinessException(code=FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT)
            return self._to_confirm_data(
                statement=statement,
                operation=existing,
                idempotent_replay=True,
            )

        if str(statement.statement_status) == self._STATUS_CANCELLED:
            raise BusinessException(code=FACTORY_STATEMENT_STATUS_INVALID)
        if str(statement.statement_status) != self._STATUS_DRAFT:
            raise BusinessException(code=FACTORY_STATEMENT_STATUS_INVALID)

        now = datetime.utcnow()
        from_status = str(statement.statement_status)
        statement.statement_status = self._STATUS_CONFIRMED
        statement.confirmed_by = self._normalize_text(operator) or "system"
        statement.confirmed_at = now

        operation = LyFactoryStatementOperation(
            company=str(statement.company),
            statement_id=int(statement.id),
            operation_type=self._OP_CONFIRM,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_status=self._STATUS_CONFIRMED,
            result_user=self._normalize_text(operator) or "system",
            result_at=now,
            remark=remark,
        )
        self.session.add(operation)
        self.session.add(
            LyFactoryStatementLog(
                statement_id=int(statement.id),
                company=str(statement.company),
                supplier=str(statement.supplier),
                from_status=from_status,
                to_status=self._STATUS_CONFIRMED,
                action="factory_statement:confirm",
                operator=self._normalize_text(operator) or "system",
                request_id=self._normalize_text(request_id),
                remark=remark or "confirm",
            )
        )

        replay_op = self._flush_operation_or_resolve_replay(
            company=str(statement.company),
            statement_id=int(statement.id),
            operation_type=self._OP_CONFIRM,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_op is not None:
            replay_statement = self._find_statement_by_id(statement_id=statement_id)
            if replay_statement is None:
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
            return self._to_confirm_data(
                statement=replay_statement,
                operation=replay_op,
                idempotent_replay=True,
            )

        return self._to_confirm_data(
            statement=statement,
            operation=operation,
            idempotent_replay=False,
        )

    def cancel_statement(
        self,
        *,
        statement_id: int,
        payload: FactoryStatementCancelRequest,
        operator: str,
        request_id: str,
    ) -> FactoryStatementCancelData:
        """Cancel factory statement and release locked inspections."""
        idempotency_key = self._normalize_text(payload.idempotency_key)
        reason = self._normalize_text(payload.reason)

        statement = self._find_statement_by_id(statement_id=statement_id)
        if statement is None:
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)

        request_hash = self._build_operation_hash(
            statement_id=statement_id,
            operation_type=self._OP_CANCEL,
            remark=reason,
        )
        existing = self._find_operation_by_idempotency(
            company=str(statement.company),
            statement_id=statement_id,
            operation_type=self._OP_CANCEL,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            if str(existing.request_hash or "") != request_hash:
                raise BusinessException(code=FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT)
            return self._to_cancel_data(
                statement=statement,
                operation=existing,
                idempotent_replay=True,
            )

        current_status = str(statement.statement_status)
        if current_status == self._STATUS_PAYABLE_DRAFT_CREATED:
            raise BusinessException(code=FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED)
        if current_status == self._STATUS_CANCELLED:
            raise BusinessException(code=FACTORY_STATEMENT_STATUS_INVALID)
        if current_status not in {self._STATUS_DRAFT, self._STATUS_CONFIRMED}:
            raise BusinessException(code=FACTORY_STATEMENT_STATUS_INVALID)
        if self._has_active_payable_outbox(statement_id=int(statement.id)):
            raise BusinessException(code=FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE)

        now = datetime.utcnow()
        statement.statement_status = self._STATUS_CANCELLED
        statement.cancelled_by = self._normalize_text(operator) or "system"
        statement.cancelled_at = now

        inspection_ids = [
            int(row.inspection_id)
            for row in (
                self.session.query(LyFactoryStatementItem.inspection_id)
                .filter(LyFactoryStatementItem.statement_id == int(statement.id))
                .all()
            )
        ]
        if inspection_ids:
            released_count = (
                self.session.query(LySubcontractInspection)
                .filter(
                    LySubcontractInspection.id.in_(inspection_ids),
                    LySubcontractInspection.statement_id == int(statement.id),
                )
                .update(
                    {
                        LySubcontractInspection.settlement_status: self._SETTLEMENT_UNSETTLED,
                        LySubcontractInspection.statement_id: None,
                        LySubcontractInspection.statement_no: None,
                        LySubcontractInspection.settlement_locked_by: None,
                        LySubcontractInspection.settlement_locked_at: None,
                    },
                    synchronize_session=False,
                )
            )
            if released_count != len(inspection_ids):
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED)

        operation = LyFactoryStatementOperation(
            company=str(statement.company),
            statement_id=int(statement.id),
            operation_type=self._OP_CANCEL,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_status=self._STATUS_CANCELLED,
            result_user=self._normalize_text(operator) or "system",
            result_at=now,
            remark=reason,
        )
        self.session.add(operation)
        self.session.add(
            LyFactoryStatementLog(
                statement_id=int(statement.id),
                company=str(statement.company),
                supplier=str(statement.supplier),
                from_status=current_status,
                to_status=self._STATUS_CANCELLED,
                action="factory_statement:cancel",
                operator=self._normalize_text(operator) or "system",
                request_id=self._normalize_text(request_id),
                remark=reason or "cancel",
            )
        )

        replay_op = self._flush_operation_or_resolve_replay(
            company=str(statement.company),
            statement_id=int(statement.id),
            operation_type=self._OP_CANCEL,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_op is not None:
            replay_statement = self._find_statement_by_id(statement_id=statement_id)
            if replay_statement is None:
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
            return self._to_cancel_data(
                statement=replay_statement,
                operation=replay_op,
                idempotent_replay=True,
            )

        return self._to_cancel_data(
            statement=statement,
            operation=operation,
            idempotent_replay=False,
        )

    def create_payable_draft_outbox(
        self,
        *,
        statement_id: int,
        payload: FactoryStatementPayableDraftRequest,
        operator: str,
        request_id: str,
        erp_adapter: ERPNextPurchaseInvoiceAdapter,
    ) -> FactoryStatementPayableDraftData:
        """Create local payable outbox only. No ERPNext PI write in request path."""
        statement = self._find_statement_by_id(statement_id=statement_id)
        if statement is None:
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)

        idempotency_key = self._normalize_text(payload.idempotency_key)
        payable_account = self._normalize_text(payload.payable_account)
        cost_center = self._normalize_text(payload.cost_center)
        remark = self._normalize_text(payload.remark)

        outbox_service = FactoryStatementPayableOutboxService(session=self.session)
        request_hash = outbox_service.build_request_hash(
            statement_id=statement_id,
            statement_no=str(statement.statement_no),
            supplier=str(statement.supplier),
            net_amount=self._to_decimal(statement.net_amount),
            payable_account=payable_account or "",
            cost_center=cost_center or "",
            posting_date=payload.posting_date,
            remark=remark,
        )

        existing = outbox_service.find_by_idempotency(
            company=str(statement.company),
            statement_id=statement_id,
            idempotency_key=idempotency_key or "",
        )
        if existing is not None:
            row = outbox_service.ensure_idempotency(existing=existing, request_hash=request_hash)
            return self._to_payable_draft_data(
                statement=statement,
                row=row,
                idempotent_replay=True,
            )

        current_status = str(statement.statement_status)
        if current_status == self._STATUS_PAYABLE_DRAFT_CREATED:
            raise BusinessException(code=FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED)
        if current_status != self._STATUS_CONFIRMED:
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)

        active_existing = outbox_service.find_active_by_statement(statement_id=int(statement.id))
        if active_existing is not None:
            raise self._payable_outbox_active_error(active_existing)

        event_key = outbox_service.build_event_key(
            company=str(statement.company),
            statement_id=int(statement.id),
            statement_no=str(statement.statement_no),
            supplier=str(statement.supplier),
            net_amount=self._to_decimal(statement.net_amount),
            payable_account=payable_account or "",
            cost_center=cost_center or "",
            posting_date=payload.posting_date,
        )

        try:
            account_ok = erp_adapter.validate_payable_account(
                company=str(statement.company),
                payable_account=payable_account or "",
            )
            if not account_ok:
                raise BusinessException(code=FACTORY_STATEMENT_PAYABLE_ACCOUNT_INVALID)

            center_ok = erp_adapter.validate_cost_center(
                company=str(statement.company),
                cost_center=cost_center or "",
            )
            if not center_ok:
                raise BusinessException(code=FACTORY_STATEMENT_COST_CENTER_INVALID)
        except BusinessException:
            raise
        except (ERPNextServiceUnavailableError, ERPNextServiceAccountForbiddenError) as exc:
            raise BusinessException(code=FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE, message=str(exc.message)) from exc
        except Exception as exc:
            raise BusinessException(code=FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE) from exc

        payload_json = {
            "doctype": "Purchase Invoice",
            "docstatus": 0,
            "supplier": str(statement.supplier),
            "company": str(statement.company),
            "posting_date": payload.posting_date.isoformat(),
            "credit_to": payable_account,
            "payable_account": payable_account,
            "cost_center": cost_center,
            "custom_ly_factory_statement_id": int(statement.id),
            "custom_ly_factory_statement_no": str(statement.statement_no),
            "custom_ly_payable_outbox_id": 0,
            "custom_ly_outbox_event_key": "",
            "amount": str(self._to_decimal(statement.net_amount)),
            "remark": remark or "",
        }

        row: LyFactoryStatementPayableOutbox
        try:
            row = outbox_service.create_outbox(
                company=str(statement.company),
                supplier=str(statement.supplier),
                statement_id=int(statement.id),
                statement_no=str(statement.statement_no),
                idempotency_key=idempotency_key or "",
                request_hash=request_hash,
                posting_date=payload.posting_date,
                payable_account=payable_account or "",
                cost_center=cost_center or "",
                net_amount=self._to_decimal(statement.net_amount),
                payload_json=payload_json,
                created_by=self._normalize_text(operator) or "system",
            )
            # Keep payload snapshot aligned with real row identity/event key.
            row.payload_json = {
                **payload_json,
                "custom_ly_payable_outbox_id": int(row.id),
                "custom_ly_outbox_event_key": str(row.event_key),
            }

            self.session.add(
                LyFactoryStatementLog(
                    statement_id=int(statement.id),
                    company=str(statement.company),
                    supplier=str(statement.supplier),
                    from_status=current_status,
                    to_status=current_status,
                    action="factory_statement:payable_draft_create",
                    operator=self._normalize_text(operator) or "system",
                    request_id=self._normalize_text(request_id),
                    remark=remark or "payable_draft_create",
                )
            )
            self.session.flush()
        except IntegrityError as exc:
            try:
                self.session.rollback()
            except SQLAlchemyError as rollback_exc:
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from rollback_exc
            replay_or_error = self._resolve_payable_outbox_after_integrity_conflict(
                outbox_service=outbox_service,
                statement=statement,
                idempotency_key=idempotency_key or "",
                request_hash=request_hash,
                event_key=event_key,
            )
            if replay_or_error is not None:
                return replay_or_error
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc

        return self._to_payable_draft_data(
            statement=statement,
            row=row,
            idempotent_replay=False,
        )

    def _has_locked_source(
        self,
        *,
        company: str,
        supplier: str,
        from_dt: datetime,
        to_dt_exclusive: datetime,
    ) -> bool:
        """Return whether scope has candidate facts but already locked/settled."""
        try:
            row = (
                self.session.query(LySubcontractInspection.id)
                .join(LySubcontractOrder, LySubcontractOrder.id == LySubcontractInspection.subcontract_id)
                .filter(
                    LySubcontractInspection.company == company,
                    LySubcontractOrder.company == company,
                    LySubcontractOrder.supplier == supplier,
                    LySubcontractInspection.status == self._INSPECTION_STATUS,
                    LySubcontractInspection.inspected_at >= from_dt,
                    LySubcontractInspection.inspected_at < to_dt_exclusive,
                    LySubcontractInspection.net_amount >= 0,
                    LySubcontractInspection.settlement_status != self._SETTLEMENT_UNSETTLED,
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        return row is not None

    def _find_statement_by_idempotency(
        self,
        *,
        company: str,
        idempotency_key: str | None,
    ) -> LyFactoryStatement | None:
        try:
            return (
                self.session.query(LyFactoryStatement)
                .filter(
                    LyFactoryStatement.company == company,
                    LyFactoryStatement.idempotency_key == idempotency_key,
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _find_active_scope_statement(
        self,
        *,
        company: str,
        supplier: str,
        from_date: date,
        to_date: date,
        request_hash: str,
    ) -> LyFactoryStatement | None:
        try:
            return (
                self.session.query(LyFactoryStatement)
                .filter(
                    LyFactoryStatement.company == company,
                    LyFactoryStatement.supplier == supplier,
                    LyFactoryStatement.from_date == from_date,
                    LyFactoryStatement.to_date == to_date,
                    LyFactoryStatement.request_hash == request_hash,
                    LyFactoryStatement.statement_status != self._STATUS_CANCELLED,
                )
                .order_by(LyFactoryStatement.id.asc())
                .first()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _find_statement_by_id(self, *, statement_id: int) -> LyFactoryStatement | None:
        try:
            return (
                self.session.query(LyFactoryStatement)
                .filter(LyFactoryStatement.id == statement_id)
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _has_active_payable_outbox(self, *, statement_id: int) -> bool:
        """Return whether statement has an active payable outbox row."""
        outbox_service = FactoryStatementPayableOutboxService(session=self.session)
        row = outbox_service.find_active_by_statement(statement_id=int(statement_id))
        return row is not None

    def _resolve_payable_outbox_after_integrity_conflict(
        self,
        *,
        outbox_service: FactoryStatementPayableOutboxService,
        statement: LyFactoryStatement,
        idempotency_key: str,
        request_hash: str,
        event_key: str,
    ) -> FactoryStatementPayableDraftData | None:
        existing = outbox_service.find_by_idempotency(
            company=str(statement.company),
            statement_id=int(statement.id),
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            row = outbox_service.ensure_idempotency(existing=existing, request_hash=request_hash)
            return self._to_payable_draft_data(
                statement=statement,
                row=row,
                idempotent_replay=True,
            )

        active_existing = outbox_service.find_active_by_statement(statement_id=int(statement.id))
        if active_existing is not None:
            raise self._payable_outbox_active_error(active_existing)

        same_event = outbox_service.find_by_event_key(event_key=event_key)
        if same_event is not None:
            raise self._payable_outbox_active_error(same_event)

        return None

    @staticmethod
    def _payable_outbox_active_error(row: LyFactoryStatementPayableOutbox) -> FactoryStatementBusinessException:
        error = FactoryStatementBusinessException(
            code=FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE,
            data={
                "existing_outbox_id": int(row.id),
                "existing_status": str(row.status),
            },
        )
        error.message = "当前对账单已有应付草稿任务，不能重复生成"
        return error

    def _fetch_latest_payable_outbox_map(
        self,
        *,
        statement_ids: list[int],
    ) -> dict[int, LyFactoryStatementPayableOutbox]:
        """Batch fetch latest payable outbox per statement (created_at desc, id desc)."""
        if not statement_ids:
            return {}
        try:
            rows = (
                self.session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id.in_(statement_ids))
                .order_by(
                    LyFactoryStatementPayableOutbox.statement_id.asc(),
                    LyFactoryStatementPayableOutbox.created_at.desc(),
                    LyFactoryStatementPayableOutbox.id.desc(),
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

        latest_map: dict[int, LyFactoryStatementPayableOutbox] = {}
        for row in rows:
            statement_id = int(row.statement_id)
            if statement_id not in latest_map:
                latest_map[statement_id] = row
        return latest_map

    def _find_operation_by_idempotency(
        self,
        *,
        company: str,
        statement_id: int,
        operation_type: str,
        idempotency_key: str | None,
    ) -> LyFactoryStatementOperation | None:
        try:
            return (
                self.session.query(LyFactoryStatementOperation)
                .filter(
                    LyFactoryStatementOperation.company == company,
                    LyFactoryStatementOperation.statement_id == statement_id,
                    LyFactoryStatementOperation.operation_type == operation_type,
                    LyFactoryStatementOperation.idempotency_key == idempotency_key,
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _flush_statement_once(self) -> None:
        self.session.flush()

    def _resolve_replay_after_integrity_conflict(
        self,
        *,
        company: str,
        supplier: str,
        from_date: date,
        to_date: date,
        idempotency_key: str | None,
        request_hash: str,
    ) -> FactoryStatementCreateData | None:
        try:
            by_idem = self._find_statement_by_idempotency(
                company=company,
                idempotency_key=idempotency_key,
            )
            if by_idem is not None:
                if str(by_idem.request_hash or "") == request_hash:
                    return self._to_create_data(by_idem, idempotent_replay=True)
                raise BusinessException(code=FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT)

            by_scope = self._find_active_scope_statement(
                company=company,
                supplier=supplier,
                from_date=from_date,
                to_date=to_date,
                request_hash=request_hash,
            )
            if by_scope is not None:
                raise self._active_scope_exists_error(by_scope)
            return None
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc

    def _flush_statement_or_resolve_replay(
        self,
        *,
        company: str,
        supplier: str,
        from_date: date,
        to_date: date,
        idempotency_key: str | None,
        request_hash: str,
    ) -> FactoryStatementCreateData | None:
        try:
            self._flush_statement_once()
            return None
        except IntegrityError as exc:
            try:
                self.session.rollback()
            except SQLAlchemyError as rollback_exc:
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from rollback_exc
            replay = self._resolve_replay_after_integrity_conflict(
                company=company,
                supplier=supplier,
                from_date=from_date,
                to_date=to_date,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
            if replay is not None:
                return replay
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc

    def _flush_operation_once(self) -> None:
        self.session.flush()

    def _flush_operation_or_resolve_replay(
        self,
        *,
        company: str,
        statement_id: int,
        operation_type: str,
        idempotency_key: str | None,
        request_hash: str,
    ) -> LyFactoryStatementOperation | None:
        try:
            self._flush_operation_once()
            return None
        except IntegrityError as exc:
            try:
                self.session.rollback()
            except SQLAlchemyError as rollback_exc:
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from rollback_exc
            existing = self._find_operation_by_idempotency(
                company=company,
                statement_id=statement_id,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
            if str(existing.request_hash or "") != request_hash:
                raise BusinessException(code=FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT)
            return existing
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @staticmethod
    def _to_decimal(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0")
        return Decimal(str(value))

    def _build_request_hash(self, *, company: str, supplier: str, from_date: date, to_date: date) -> str:
        payload = {
            "company": company,
            "supplier": supplier,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "source_type": self._SOURCE_TYPE,
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def _build_operation_hash(
        self,
        *,
        statement_id: int,
        operation_type: str,
        remark: str | None,
    ) -> str:
        payload = {
            "statement_id": int(statement_id),
            "operation_type": operation_type,
            "remark": remark or "",
        }
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_statement_no() -> str:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        suffix = uuid.uuid4().hex[:6].upper()
        return f"FS-{now}-{suffix}"

    @staticmethod
    def _compute_rejected_rate(*, inspected_qty: Decimal, rejected_qty: Decimal) -> Decimal:
        if inspected_qty <= 0:
            return Decimal("0")
        return (rejected_qty / inspected_qty).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    def _to_create_data(self, row: LyFactoryStatement, *, idempotent_replay: bool) -> FactoryStatementCreateData:
        return FactoryStatementCreateData(
            statement_id=int(row.id),
            statement_no=str(row.statement_no),
            statement_status=str(row.statement_status),
            company=str(row.company),
            supplier=str(row.supplier),
            from_date=row.from_date,
            to_date=row.to_date,
            source_count=int(row.source_count or 0),
            inspected_qty=self._to_decimal(row.inspected_qty),
            rejected_qty=self._to_decimal(row.rejected_qty),
            accepted_qty=self._to_decimal(row.accepted_qty),
            gross_amount=self._to_decimal(row.gross_amount),
            deduction_amount=self._to_decimal(row.deduction_amount),
            net_amount=self._to_decimal(row.net_amount),
            rejected_rate=self._to_decimal(row.rejected_rate),
            idempotency_key=str(row.idempotency_key),
            request_hash=str(row.request_hash),
            idempotent_replay=idempotent_replay,
        )

    @staticmethod
    def _active_scope_exists_error(statement: LyFactoryStatement) -> FactoryStatementBusinessException:
        return FactoryStatementBusinessException(
            code=FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS,
            data={
                "statement_id": int(statement.id),
                "statement_no": str(statement.statement_no),
            },
        )

    def _to_confirm_data(
        self,
        *,
        statement: LyFactoryStatement,
        operation: LyFactoryStatementOperation,
        idempotent_replay: bool,
    ) -> FactoryStatementConfirmData:
        return FactoryStatementConfirmData(
            id=int(statement.id),
            statement_no=str(statement.statement_no),
            status=str(operation.result_status),
            confirmed_by=str(operation.result_user),
            confirmed_at=operation.result_at,
            idempotent_replay=idempotent_replay,
        )

    def _to_cancel_data(
        self,
        *,
        statement: LyFactoryStatement,
        operation: LyFactoryStatementOperation,
        idempotent_replay: bool,
    ) -> FactoryStatementCancelData:
        return FactoryStatementCancelData(
            id=int(statement.id),
            statement_no=str(statement.statement_no),
            status=str(operation.result_status),
            cancelled_by=str(operation.result_user),
            cancelled_at=operation.result_at,
            idempotent_replay=idempotent_replay,
        )

    def _to_payable_draft_data(
        self,
        *,
        statement: LyFactoryStatement,
        row: LyFactoryStatementPayableOutbox,
        idempotent_replay: bool,
    ) -> FactoryStatementPayableDraftData:
        return FactoryStatementPayableDraftData(
            statement_id=int(statement.id),
            statement_no=str(statement.statement_no),
            status=str(statement.statement_status),
            payable_outbox_id=int(row.id),
            payable_outbox_status=str(row.status),
            purchase_invoice_name=self._normalize_text(row.erpnext_purchase_invoice),
            net_amount=self._to_decimal(statement.net_amount),
            idempotent_replay=idempotent_replay,
        )
