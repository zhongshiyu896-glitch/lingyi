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
import os
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
from app.core.error_codes import FACTORY_STATEMENT_PAYMENT_ALREADY_PAID
from app.core.error_codes import FACTORY_STATEMENT_PAYMENT_AMOUNT_EXCEEDED
from app.core.error_codes import FACTORY_STATEMENT_PAYMENT_CONFLICT
from app.core.error_codes import FACTORY_STATEMENT_PAYMENT_INVALID_PAYLOAD
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
from app.models.factory_statement import LyFactoryStatementPayment
from app.models.factory_statement import LyFactoryStatementPaymentOperation
from app.models.material_purchase import LyMaterialPurchaseInvoice
from app.models.material_purchase import LyMaterialPurchasePayment
from app.models.sales_order import LyDeliveryInvoice
from app.models.sales_order import LySalesPaymentEntry
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.schemas.factory_statement import FactoryStatementCancelData
from app.schemas.factory_statement import FactoryStatementCancelRequest
from app.schemas.factory_statement import FactoryStatementBankDepositData
from app.schemas.factory_statement import FactoryStatementBankDepositItem
from app.schemas.factory_statement import FactoryStatementBankLedgerData
from app.schemas.factory_statement import FactoryStatementBankLedgerItem
from app.schemas.factory_statement import FactoryStatementBankWithdrawalData
from app.schemas.factory_statement import FactoryStatementBankWithdrawalItem
from app.schemas.factory_statement import FactoryStatementConfirmData
from app.schemas.factory_statement import FactoryStatementConfirmRequest
from app.schemas.factory_statement import FactoryStatementCreateData
from app.schemas.factory_statement import FactoryStatementCreateRequest
from app.schemas.factory_statement import FactoryStatementCustomerEvaluationData
from app.schemas.factory_statement import FactoryStatementCustomerEvaluationItem
from app.schemas.factory_statement import FactoryStatementCustomerReconciliationData
from app.schemas.factory_statement import FactoryStatementCustomerReconciliationItem
from app.schemas.factory_statement import FactoryStatementCustomerReceivableSummaryData
from app.schemas.factory_statement import FactoryStatementCustomerReceivableSummaryItem
from app.schemas.factory_statement import FactoryStatementCustomerUnpaidReportData
from app.schemas.factory_statement import FactoryStatementCustomerUnpaidReportItem
from app.schemas.factory_statement import FactoryStatementFactoryEvaluationData
from app.schemas.factory_statement import FactoryStatementFactoryEvaluationItem
from app.schemas.factory_statement import FactoryStatementFactoryReconciliationData
from app.schemas.factory_statement import FactoryStatementFactoryReconciliationItem
from app.schemas.factory_statement import FactoryStatementFactoryPayableSummaryData
from app.schemas.factory_statement import FactoryStatementFactoryPayableSummaryItem
from app.schemas.factory_statement import FactoryStatementSupplierEvaluationData
from app.schemas.factory_statement import FactoryStatementSupplierEvaluationItem
from app.schemas.factory_statement import FactoryStatementSupplierPayableSummaryData
from app.schemas.factory_statement import FactoryStatementSupplierPayableSummaryItem
from app.schemas.factory_statement import FactoryStatementSupplierReconciliationData
from app.schemas.factory_statement import FactoryStatementSupplierReconciliationItem
from app.schemas.factory_statement import FactoryStatementDetailData
from app.schemas.factory_statement import FactoryStatementExpenseReimbursementPaymentData
from app.schemas.factory_statement import FactoryStatementExpenseReimbursementPaymentItem
from app.schemas.factory_statement import FactoryStatementItemData
from app.schemas.factory_statement import FactoryStatementListData
from app.schemas.factory_statement import FactoryStatementListItem
from app.schemas.factory_statement import FactoryStatementLogData
from app.schemas.factory_statement import FactoryStatementPayableDraftData
from app.schemas.factory_statement import FactoryStatementPayableOutboxData
from app.schemas.factory_statement import FactoryStatementPayableDraftRequest
from app.schemas.factory_statement import FactoryStatementPaymentCancelRequest
from app.schemas.factory_statement import FactoryStatementPaymentCreateRequest
from app.schemas.factory_statement import FactoryStatementPaymentData
from app.schemas.factory_statement import FactoryStatementPaymentListData
from app.schemas.factory_statement import FactoryStatementPurchaseInvoiceItem
from app.schemas.factory_statement import FactoryStatementPurchaseInvoiceListData
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
    _OP_PAYMENT_CREATE = "create_payment_entry"
    _OP_PAYMENT_CANCEL = "cancel_payment_entry"
    _LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"

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
            scenario_tag = self._normalize_text(payload.scenario_tag)
            if scenario_tag:
                try:
                    statement = LyFactoryStatement(
                        statement_no=self._build_statement_no(),
                        company=company,
                        supplier=supplier,
                        from_date=from_date,
                        to_date=to_date,
                        source_type=self._SOURCE_TYPE,
                        source_count=0,
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
                            remark=f"create_draft_local_synthetic:{scenario_tag}",
                        )
                    )
                    self.session.flush()
                    return self._to_create_data(statement, idempotent_replay=False)
                except BusinessException:
                    raise
                except SQLAlchemyError as exc:
                    raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
                except Exception as exc:
                    raise BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR) from exc

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
        paid_amount_map = self._fetch_paid_amount_map(statement_ids=statement_ids)

        return FactoryStatementListData(
            items=[
                self._to_list_item(
                    row=row,
                    latest_payable=latest_payable_map.get(int(row.id)),
                    paid_amount=paid_amount_map.get(int(row.id), Decimal("0")),
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
            payments = (
                self.session.query(LyFactoryStatementPayment)
                .filter(LyFactoryStatementPayment.statement_id == statement_id)
                .order_by(LyFactoryStatementPayment.created_at.desc(), LyFactoryStatementPayment.id.desc())
                .all()
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        except Exception as exc:
            raise BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR) from exc

        latest_payable = payable_outboxes[0] if payable_outboxes else None
        paid_amount = sum((self._to_decimal(row.paid_amount) for row in payments if str(row.status) == "submitted"), Decimal("0"))
        outstanding_amount = self._compute_outstanding_amount(net_amount=self._to_decimal(statement.net_amount), paid_amount=paid_amount)

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
            paid_amount=paid_amount,
            outstanding_amount=outstanding_amount,
            payment_status=self._payment_status(net_amount=self._to_decimal(statement.net_amount), paid_amount=paid_amount),
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
                    style_code=self._normalize_text(row.item_code),
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
            payments=[self._to_payment_data(row) for row in payments],
        )

    def get_expense_reimbursement_payments(
        self,
        *,
        payment_no: str | None,
        reimbursement_no: str | None,
        statement_no: str | None,
        supplier: str | None,
        payment_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementExpenseReimbursementPaymentData:
        """Read-only expense reimbursement payment rows for `/factory-statements/list`."""
        normalized_payment_no = self._normalize_text(payment_no)
        normalized_reimbursement_no = self._normalize_text(reimbursement_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_supplier = self._normalize_text(supplier)
        normalized_payment_status = self._normalize_text(payment_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "payment_no": "ERP-REPAY-2026-0501",
                "reimbursement_no": "RB-2026-0501",
                "statement_no": "FS-202605010915-8A31C2",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "expense_type": "加工费报销",
                "payable_amount": Decimal("12540.00"),
                "paid_amount": Decimal("8000.00"),
                "pending_amount": Decimal("4540.00"),
                "payment_status": "部分支付",
                "review_status": "待复核",
                "payment_date": date(2026, 5, 1),
                "payable_account": "2202-应付账款-加工厂",
                "cost_center": "CC-FACTORY-01",
                "owner": "李佳琳",
                "ref_no": "PAY-REQ-2026-0501",
            },
            {
                "payment_no": "ERP-REPAY-2026-0502",
                "reimbursement_no": "RB-2026-0502",
                "statement_no": "FS-202605021030-4B29D1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "expense_type": "辅料报销",
                "payable_amount": Decimal("8960.00"),
                "paid_amount": Decimal("8960.00"),
                "pending_amount": Decimal("0.00"),
                "payment_status": "已支付",
                "review_status": "已通过",
                "payment_date": date(2026, 5, 2),
                "payable_account": "2202-应付账款-辅料",
                "cost_center": "CC-MATERIAL-02",
                "owner": "周晨",
                "ref_no": "PAY-REQ-2026-0502",
            },
            {
                "payment_no": "ERP-REPAY-2026-0503",
                "reimbursement_no": "RB-2026-0503",
                "statement_no": "FS-202605031405-7E11F9",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "expense_type": "返修报销",
                "payable_amount": Decimal("6420.00"),
                "paid_amount": Decimal("0.00"),
                "pending_amount": Decimal("6420.00"),
                "payment_status": "待支付",
                "review_status": "未开始",
                "payment_date": date(2026, 5, 3),
                "payable_account": "2202-应付账款-返修",
                "cost_center": "CC-REWORK-01",
                "owner": "吴静怡",
                "ref_no": "PAY-REQ-2026-0503",
            },
            {
                "payment_no": "ERP-REPAY-2026-0504",
                "reimbursement_no": "RB-2026-0504",
                "statement_no": "FS-202605041220-3F88A6",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "expense_type": "样衣报销",
                "payable_amount": Decimal("7340.00"),
                "paid_amount": Decimal("3200.00"),
                "pending_amount": Decimal("4140.00"),
                "payment_status": "审批中",
                "review_status": "复核中",
                "payment_date": date(2026, 5, 4),
                "payable_account": "2202-应付账款-样衣",
                "cost_center": "CC-SAMPLE-01",
                "owner": "邵伟",
                "ref_no": "PAY-REQ-2026-0504",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_payment_no and row["payment_no"] != normalized_payment_no:
                continue
            if normalized_reimbursement_no and row["reimbursement_no"] != normalized_reimbursement_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_supplier and row["supplier"] != normalized_supplier:
                continue
            if normalized_payment_status and row["payment_status"] != normalized_payment_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["payment_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["payment_no"]),
                        str(row["reimbursement_no"]),
                        str(row["statement_no"]),
                        row_company,
                        row_supplier,
                        str(row["expense_type"]),
                        str(row["owner"]),
                        str(row["ref_no"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["payment_date"], entry["payment_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementExpenseReimbursementPaymentData(
            items=[
                FactoryStatementExpenseReimbursementPaymentItem(
                    payment_no=str(row["payment_no"]),
                    reimbursement_no=str(row["reimbursement_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    supplier=str(row["supplier"]),
                    expense_type=str(row["expense_type"]),
                    payable_amount=self._to_decimal(row["payable_amount"]),  # type: ignore[arg-type]
                    paid_amount=self._to_decimal(row["paid_amount"]),  # type: ignore[arg-type]
                    pending_amount=self._to_decimal(row["pending_amount"]),  # type: ignore[arg-type]
                    payment_status=str(row["payment_status"]),
                    review_status=str(row["review_status"]),
                    payment_date=row["payment_date"],  # type: ignore[arg-type]
                    payable_account=str(row["payable_account"]),
                    cost_center=str(row["cost_center"]),
                    owner=str(row["owner"]),
                    ref_no=str(row["ref_no"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_bank_deposits(
        self,
        *,
        deposit_no: str | None,
        statement_no: str | None,
        bank_name: str | None,
        account_name: str | None,
        deposit_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementBankDepositData:
        """Read-only bank deposit rows for `/factory-statements/list`."""
        normalized_deposit_no = self._normalize_text(deposit_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_bank_name = self._normalize_text(bank_name)
        normalized_account_name = self._normalize_text(account_name)
        normalized_deposit_status = self._normalize_text(deposit_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "deposit_no": "BD-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "bank_name": "招商银行东莞分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62148301****2031",
                "currency": "CNY",
                "deposit_amount": Decimal("15200.00"),
                "confirmed_amount": Decimal("15200.00"),
                "pending_amount": Decimal("0.00"),
                "deposit_status": "已入账",
                "review_status": "已通过",
                "deposit_date": date(2026, 5, 1),
                "voucher_no": "VCH-260501-001",
                "owner": "李佳琳",
                "remark": "客户货款存款",
            },
            {
                "deposit_no": "BD-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "bank_name": "中国银行广州分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62166101****8842",
                "currency": "CNY",
                "deposit_amount": Decimal("9800.00"),
                "confirmed_amount": Decimal("6000.00"),
                "pending_amount": Decimal("3800.00"),
                "deposit_status": "待入账",
                "review_status": "待复核",
                "deposit_date": date(2026, 5, 2),
                "voucher_no": "VCH-260502-003",
                "owner": "周晨",
                "remark": "分批到账",
            },
            {
                "deposit_no": "BD-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "bank_name": "工商银行深圳分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62220001****5517",
                "currency": "CNY",
                "deposit_amount": Decimal("12450.00"),
                "confirmed_amount": Decimal("0.00"),
                "pending_amount": Decimal("12450.00"),
                "deposit_status": "处理中",
                "review_status": "复核中",
                "deposit_date": date(2026, 5, 3),
                "voucher_no": "VCH-260503-002",
                "owner": "吴静怡",
                "remark": "银行回单待核验",
            },
            {
                "deposit_no": "BD-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "bank_name": "建设银行杭州分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62170001****1120",
                "currency": "CNY",
                "deposit_amount": Decimal("7600.00"),
                "confirmed_amount": Decimal("0.00"),
                "pending_amount": Decimal("7600.00"),
                "deposit_status": "已作废",
                "review_status": "未开始",
                "deposit_date": date(2026, 5, 4),
                "voucher_no": "VCH-260504-005",
                "owner": "邵伟",
                "remark": "重复提交作废",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_deposit_no and row["deposit_no"] != normalized_deposit_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_bank_name and row["bank_name"] != normalized_bank_name:
                continue
            if normalized_account_name and row["account_name"] != normalized_account_name:
                continue
            if normalized_deposit_status and row["deposit_status"] != normalized_deposit_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["deposit_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["deposit_no"]),
                        str(row["statement_no"]),
                        str(row["bank_name"]),
                        str(row["account_name"]),
                        str(row["owner"]),
                        str(row["voucher_no"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["deposit_date"], entry["deposit_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementBankDepositData(
            items=[
                FactoryStatementBankDepositItem(
                    deposit_no=str(row["deposit_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    bank_name=str(row["bank_name"]),
                    account_name=str(row["account_name"]),
                    account_no=str(row["account_no"]),
                    currency=str(row["currency"]),
                    deposit_amount=self._to_decimal(row["deposit_amount"]),  # type: ignore[arg-type]
                    confirmed_amount=self._to_decimal(row["confirmed_amount"]),  # type: ignore[arg-type]
                    pending_amount=self._to_decimal(row["pending_amount"]),  # type: ignore[arg-type]
                    deposit_status=str(row["deposit_status"]),
                    review_status=str(row["review_status"]),
                    deposit_date=row["deposit_date"],  # type: ignore[arg-type]
                    voucher_no=str(row["voucher_no"]),
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_bank_withdrawals(
        self,
        *,
        withdrawal_no: str | None,
        statement_no: str | None,
        bank_name: str | None,
        account_name: str | None,
        withdrawal_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementBankWithdrawalData:
        """Read-only bank withdrawal rows for `/factory-statements/list`."""
        normalized_withdrawal_no = self._normalize_text(withdrawal_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_bank_name = self._normalize_text(bank_name)
        normalized_account_name = self._normalize_text(account_name)
        normalized_withdrawal_status = self._normalize_text(withdrawal_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "withdrawal_no": "BW-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "bank_name": "招商银行东莞分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62148301****2031",
                "currency": "CNY",
                "withdrawal_amount": Decimal("11800.00"),
                "transferred_amount": Decimal("11800.00"),
                "pending_amount": Decimal("0.00"),
                "withdrawal_status": "已出账",
                "review_status": "已通过",
                "withdrawal_date": date(2026, 5, 1),
                "voucher_no": "VCH-260501-011",
                "owner": "李佳琳",
                "remark": "加工费批次结算出账",
            },
            {
                "withdrawal_no": "BW-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "bank_name": "中国银行广州分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62166101****8842",
                "currency": "CNY",
                "withdrawal_amount": Decimal("9200.00"),
                "transferred_amount": Decimal("5400.00"),
                "pending_amount": Decimal("3800.00"),
                "withdrawal_status": "待出账",
                "review_status": "待复核",
                "withdrawal_date": date(2026, 5, 2),
                "voucher_no": "VCH-260502-017",
                "owner": "周晨",
                "remark": "供应商预付款分批处理",
            },
            {
                "withdrawal_no": "BW-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "bank_name": "工商银行深圳分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62220001****5517",
                "currency": "CNY",
                "withdrawal_amount": Decimal("13450.00"),
                "transferred_amount": Decimal("0.00"),
                "pending_amount": Decimal("13450.00"),
                "withdrawal_status": "处理中",
                "review_status": "复核中",
                "withdrawal_date": date(2026, 5, 3),
                "voucher_no": "VCH-260503-009",
                "owner": "吴静怡",
                "remark": "银行出账回执待确认",
            },
            {
                "withdrawal_no": "BW-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "bank_name": "建设银行杭州分行",
                "account_name": "凌云服饰有限公司",
                "account_no": "62170001****1120",
                "currency": "CNY",
                "withdrawal_amount": Decimal("7600.00"),
                "transferred_amount": Decimal("0.00"),
                "pending_amount": Decimal("7600.00"),
                "withdrawal_status": "已作废",
                "review_status": "未开始",
                "withdrawal_date": date(2026, 5, 4),
                "voucher_no": "VCH-260504-013",
                "owner": "邵伟",
                "remark": "重复申请撤销",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_withdrawal_no and row["withdrawal_no"] != normalized_withdrawal_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_bank_name and row["bank_name"] != normalized_bank_name:
                continue
            if normalized_account_name and row["account_name"] != normalized_account_name:
                continue
            if normalized_withdrawal_status and row["withdrawal_status"] != normalized_withdrawal_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["withdrawal_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["withdrawal_no"]),
                        str(row["statement_no"]),
                        str(row["bank_name"]),
                        str(row["account_name"]),
                        str(row["owner"]),
                        str(row["voucher_no"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["withdrawal_date"], entry["withdrawal_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementBankWithdrawalData(
            items=[
                FactoryStatementBankWithdrawalItem(
                    withdrawal_no=str(row["withdrawal_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    bank_name=str(row["bank_name"]),
                    account_name=str(row["account_name"]),
                    account_no=str(row["account_no"]),
                    currency=str(row["currency"]),
                    withdrawal_amount=self._to_decimal(row["withdrawal_amount"]),  # type: ignore[arg-type]
                    transferred_amount=self._to_decimal(row["transferred_amount"]),  # type: ignore[arg-type]
                    pending_amount=self._to_decimal(row["pending_amount"]),  # type: ignore[arg-type]
                    withdrawal_status=str(row["withdrawal_status"]),
                    review_status=str(row["review_status"]),
                    withdrawal_date=row["withdrawal_date"],  # type: ignore[arg-type]
                    voucher_no=str(row["voucher_no"]),
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_customer_evaluations(
        self,
        *,
        evaluation_no: str | None,
        statement_no: str | None,
        customer_name: str | None,
        assessor: str | None,
        score_level: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementCustomerEvaluationData:
        """Read-only customer evaluation rows for `/factory-statements/list`."""
        normalized_evaluation_no = self._normalize_text(evaluation_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_customer_name = self._normalize_text(customer_name)
        normalized_assessor = self._normalize_text(assessor)
        normalized_score_level = self._normalize_text(score_level)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "evaluation_no": "CE-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "customer_name": "广州艺帛贸易",
                "customer_code": "CUS-0132",
                "assessor": "李佳琳",
                "score": Decimal("92.0"),
                "score_level": "A",
                "review_status": "已通过",
                "follow_up_status": "已完成",
                "evaluation_date": date(2026, 5, 1),
                "expiry_date": date(2026, 11, 1),
                "owner": "李佳琳",
                "remark": "交付稳定、回款及时",
            },
            {
                "evaluation_no": "CE-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "customer_name": "深圳雅尚服饰",
                "customer_code": "CUS-0218",
                "assessor": "周晨",
                "score": Decimal("84.0"),
                "score_level": "B",
                "review_status": "待复核",
                "follow_up_status": "待跟进",
                "evaluation_date": date(2026, 5, 2),
                "expiry_date": date(2026, 11, 2),
                "owner": "周晨",
                "remark": "报价敏感，需加强账期管理",
            },
            {
                "evaluation_no": "CE-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "customer_name": "杭州新禾服装",
                "customer_code": "CUS-0305",
                "assessor": "吴静怡",
                "score": Decimal("76.5"),
                "score_level": "C",
                "review_status": "复核中",
                "follow_up_status": "跟进中",
                "evaluation_date": date(2026, 5, 3),
                "expiry_date": date(2026, 11, 3),
                "owner": "吴静怡",
                "remark": "退货频次偏高，建议压缩信用额度",
            },
            {
                "evaluation_no": "CE-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "customer_name": "苏州织远商贸",
                "customer_code": "CUS-0440",
                "assessor": "邵伟",
                "score": Decimal("68.0"),
                "score_level": "D",
                "review_status": "未开始",
                "follow_up_status": "已作废",
                "evaluation_date": date(2026, 5, 4),
                "expiry_date": date(2026, 11, 4),
                "owner": "邵伟",
                "remark": "客户资料不完整，评估单作废",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_evaluation_no and row["evaluation_no"] != normalized_evaluation_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_customer_name and row["customer_name"] != normalized_customer_name:
                continue
            if normalized_assessor and row["assessor"] != normalized_assessor:
                continue
            if normalized_score_level and row["score_level"] != normalized_score_level:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["evaluation_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["evaluation_no"]),
                        str(row["statement_no"]),
                        str(row["customer_name"]),
                        str(row["customer_code"]),
                        str(row["assessor"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["evaluation_date"], entry["evaluation_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementCustomerEvaluationData(
            items=[
                FactoryStatementCustomerEvaluationItem(
                    evaluation_no=str(row["evaluation_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    customer_name=str(row["customer_name"]),
                    customer_code=str(row["customer_code"]),
                    assessor=str(row["assessor"]),
                    score=self._to_decimal(row["score"]),  # type: ignore[arg-type]
                    score_level=str(row["score_level"]),
                    review_status=str(row["review_status"]),
                    follow_up_status=str(row["follow_up_status"]),
                    evaluation_date=row["evaluation_date"],  # type: ignore[arg-type]
                    expiry_date=row["expiry_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_customer_reconciliations(
        self,
        *,
        reconciliation_no: str | None,
        statement_no: str | None,
        customer_name: str | None,
        settlement_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementCustomerReconciliationData:
        """Read-only customer reconciliation rows for `/factory-statements/list`."""
        normalized_reconciliation_no = self._normalize_text(reconciliation_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_customer_name = self._normalize_text(customer_name)
        normalized_settlement_status = self._normalize_text(settlement_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "reconciliation_no": "CR-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "customer_name": "广州艺帛贸易",
                "customer_code": "CUS-0132",
                "currency": "CNY",
                "receivable_amount": Decimal("23500.00"),
                "settled_amount": Decimal("23500.00"),
                "pending_amount": Decimal("0.00"),
                "settlement_status": "已结算",
                "review_status": "已通过",
                "due_date": date(2026, 5, 1),
                "reconciled_at": date(2026, 5, 3),
                "owner": "李佳琳",
                "remark": "已完成回款核销",
            },
            {
                "reconciliation_no": "CR-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "customer_name": "深圳雅尚服饰",
                "customer_code": "CUS-0218",
                "currency": "CNY",
                "receivable_amount": Decimal("18200.00"),
                "settled_amount": Decimal("9600.00"),
                "pending_amount": Decimal("8600.00"),
                "settlement_status": "待结算",
                "review_status": "待复核",
                "due_date": date(2026, 5, 2),
                "reconciled_at": date(2026, 5, 2),
                "owner": "周晨",
                "remark": "客户申请分期结算",
            },
            {
                "reconciliation_no": "CR-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "customer_name": "杭州新禾服装",
                "customer_code": "CUS-0305",
                "currency": "CNY",
                "receivable_amount": Decimal("16740.00"),
                "settled_amount": Decimal("0.00"),
                "pending_amount": Decimal("16740.00"),
                "settlement_status": "结算中",
                "review_status": "复核中",
                "due_date": date(2026, 5, 3),
                "reconciled_at": date(2026, 5, 3),
                "owner": "吴静怡",
                "remark": "回款凭证待财务复核",
            },
            {
                "reconciliation_no": "CR-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "customer_name": "苏州织远商贸",
                "customer_code": "CUS-0440",
                "currency": "CNY",
                "receivable_amount": Decimal("14320.00"),
                "settled_amount": Decimal("0.00"),
                "pending_amount": Decimal("14320.00"),
                "settlement_status": "已作废",
                "review_status": "未开始",
                "due_date": date(2026, 5, 4),
                "reconciled_at": date(2026, 5, 4),
                "owner": "邵伟",
                "remark": "单据资料缺失作废重开",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_reconciliation_no and row["reconciliation_no"] != normalized_reconciliation_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_customer_name and row["customer_name"] != normalized_customer_name:
                continue
            if normalized_settlement_status and row["settlement_status"] != normalized_settlement_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["due_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["reconciliation_no"]),
                        str(row["statement_no"]),
                        str(row["customer_name"]),
                        str(row["customer_code"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["due_date"], entry["reconciliation_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementCustomerReconciliationData(
            items=[
                FactoryStatementCustomerReconciliationItem(
                    reconciliation_no=str(row["reconciliation_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    customer_name=str(row["customer_name"]),
                    customer_code=str(row["customer_code"]),
                    currency=str(row["currency"]),
                    receivable_amount=self._to_decimal(row["receivable_amount"]),  # type: ignore[arg-type]
                    settled_amount=self._to_decimal(row["settled_amount"]),  # type: ignore[arg-type]
                    pending_amount=self._to_decimal(row["pending_amount"]),  # type: ignore[arg-type]
                    settlement_status=str(row["settlement_status"]),
                    review_status=str(row["review_status"]),
                    due_date=row["due_date"],  # type: ignore[arg-type]
                    reconciled_at=row["reconciled_at"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_customer_unpaid_reports(
        self,
        *,
        report_no: str | None,
        statement_no: str | None,
        customer_name: str | None,
        collection_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementCustomerUnpaidReportData:
        """Read-only customer unpaid report rows for `/factory-statements/list`."""
        normalized_report_no = self._normalize_text(report_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_customer_name = self._normalize_text(customer_name)
        normalized_collection_status = self._normalize_text(collection_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "report_no": "CUR-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "customer_name": "广州艺帛贸易",
                "customer_code": "CUS-0132",
                "currency": "CNY",
                "receivable_amount": Decimal("25200.00"),
                "received_amount": Decimal("12000.00"),
                "unpaid_amount": Decimal("13200.00"),
                "overdue_days": 7,
                "collection_status": "催收中",
                "review_status": "待复核",
                "due_date": date(2026, 5, 1),
                "last_collection_at": date(2026, 5, 5),
                "owner": "李佳琳",
                "remark": "客户承诺本周补齐尾款",
            },
            {
                "report_no": "CUR-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "customer_name": "深圳雅尚服饰",
                "customer_code": "CUS-0218",
                "currency": "CNY",
                "receivable_amount": Decimal("18450.00"),
                "received_amount": Decimal("18450.00"),
                "unpaid_amount": Decimal("0.00"),
                "overdue_days": 0,
                "collection_status": "已收款",
                "review_status": "已通过",
                "due_date": date(2026, 5, 2),
                "last_collection_at": date(2026, 5, 2),
                "owner": "周晨",
                "remark": "已完成收款核销",
            },
            {
                "report_no": "CUR-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "customer_name": "杭州新禾服装",
                "customer_code": "CUS-0305",
                "currency": "CNY",
                "receivable_amount": Decimal("16980.00"),
                "received_amount": Decimal("5300.00"),
                "unpaid_amount": Decimal("11680.00"),
                "overdue_days": 3,
                "collection_status": "待催收",
                "review_status": "复核中",
                "due_date": date(2026, 5, 3),
                "last_collection_at": date(2026, 5, 4),
                "owner": "吴静怡",
                "remark": "客户反馈货损，待商务确认差额",
            },
            {
                "report_no": "CUR-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "customer_name": "苏州织远商贸",
                "customer_code": "CUS-0440",
                "currency": "CNY",
                "receivable_amount": Decimal("14320.00"),
                "received_amount": Decimal("0.00"),
                "unpaid_amount": Decimal("14320.00"),
                "overdue_days": 0,
                "collection_status": "已作废",
                "review_status": "未开始",
                "due_date": date(2026, 5, 4),
                "last_collection_at": date(2026, 5, 4),
                "owner": "邵伟",
                "remark": "单据作废，待重开后重新催收",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_report_no and row["report_no"] != normalized_report_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_customer_name and row["customer_name"] != normalized_customer_name:
                continue
            if normalized_collection_status and row["collection_status"] != normalized_collection_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["due_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["report_no"]),
                        str(row["statement_no"]),
                        str(row["customer_name"]),
                        str(row["customer_code"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["due_date"], entry["report_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementCustomerUnpaidReportData(
            items=[
                FactoryStatementCustomerUnpaidReportItem(
                    report_no=str(row["report_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    customer_name=str(row["customer_name"]),
                    customer_code=str(row["customer_code"]),
                    currency=str(row["currency"]),
                    receivable_amount=self._to_decimal(row["receivable_amount"]),  # type: ignore[arg-type]
                    received_amount=self._to_decimal(row["received_amount"]),  # type: ignore[arg-type]
                    unpaid_amount=self._to_decimal(row["unpaid_amount"]),  # type: ignore[arg-type]
                    overdue_days=int(row["overdue_days"]),
                    collection_status=str(row["collection_status"]),
                    review_status=str(row["review_status"]),
                    due_date=row["due_date"],  # type: ignore[arg-type]
                    last_collection_at=row["last_collection_at"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_customer_receivable_summaries(
        self,
        *,
        summary_no: str | None,
        statement_no: str | None,
        customer_name: str | None,
        risk_level: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementCustomerReceivableSummaryData:
        """Read-only customer receivable summary rows for `/factory-statements/list`."""
        normalized_summary_no = self._normalize_text(summary_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_customer_name = self._normalize_text(customer_name)
        normalized_risk_level = self._normalize_text(risk_level)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        source_rows = self._build_customer_receivable_summary_rows(
            from_date=from_date,
            to_date=to_date,
            readable_companies=readable_companies,
        )

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in source_rows:
            if normalized_summary_no and row["summary_no"] != normalized_summary_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_customer_name and row["customer_name"] != normalized_customer_name:
                continue
            if normalized_risk_level and row["risk_level"] != normalized_risk_level:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and not readable_suppliers:
                continue

            row_date = row["summary_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["summary_no"]),
                        str(row["statement_no"]),
                        str(row["customer_name"]),
                        str(row["customer_code"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["summary_date"], entry["summary_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementCustomerReceivableSummaryData(
            items=[
                FactoryStatementCustomerReceivableSummaryItem(
                    summary_no=str(row["summary_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    customer_name=str(row["customer_name"]),
                    customer_code=str(row["customer_code"]),
                    currency=str(row["currency"]),
                    opening_receivable=self._to_decimal(row["opening_receivable"]),  # type: ignore[arg-type]
                    current_receivable=self._to_decimal(row["current_receivable"]),  # type: ignore[arg-type]
                    received_amount=self._to_decimal(row["received_amount"]),  # type: ignore[arg-type]
                    ending_receivable=self._to_decimal(row["ending_receivable"]),  # type: ignore[arg-type]
                    aging_30=self._to_decimal(row["aging_30"]),  # type: ignore[arg-type]
                    aging_60=self._to_decimal(row["aging_60"]),  # type: ignore[arg-type]
                    aging_90_plus=self._to_decimal(row["aging_90_plus"]),  # type: ignore[arg-type]
                    risk_level=str(row["risk_level"]),
                    review_status=str(row["review_status"]),
                    summary_date=row["summary_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_factory_evaluations(
        self,
        *,
        evaluation_no: str | None,
        statement_no: str | None,
        factory_name: str | None,
        assessor: str | None,
        score_level: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementFactoryEvaluationData:
        """Read-only factory evaluation rows for `/factory-statements/list`."""
        normalized_evaluation_no = self._normalize_text(evaluation_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_factory_name = self._normalize_text(factory_name)
        normalized_assessor = self._normalize_text(assessor)
        normalized_score_level = self._normalize_text(score_level)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "evaluation_no": "FE-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "factory_name": "东莞卓越制衣厂",
                "factory_code": "FAC-0018",
                "assessor": "李佳琳",
                "score": Decimal("91.0"),
                "score_level": "A",
                "review_status": "已通过",
                "follow_up_status": "已完成",
                "evaluation_date": date(2026, 5, 1),
                "expiry_date": date(2026, 11, 1),
                "owner": "李佳琳",
                "remark": "交期稳定、返修率低",
            },
            {
                "evaluation_no": "FE-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "factory_name": "广州星河辅料厂",
                "factory_code": "FAC-0033",
                "assessor": "周晨",
                "score": Decimal("84.5"),
                "score_level": "B",
                "review_status": "待复核",
                "follow_up_status": "待跟进",
                "evaluation_date": date(2026, 5, 2),
                "expiry_date": date(2026, 11, 2),
                "owner": "周晨",
                "remark": "价格波动可控，交付偶发延期",
            },
            {
                "evaluation_no": "FE-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "factory_name": "深圳远航加工厂",
                "factory_code": "FAC-0046",
                "assessor": "吴静怡",
                "score": Decimal("76.0"),
                "score_level": "C",
                "review_status": "复核中",
                "follow_up_status": "跟进中",
                "evaluation_date": date(2026, 5, 3),
                "expiry_date": date(2026, 11, 3),
                "owner": "吴静怡",
                "remark": "品质波动偏高，需加强驻厂巡检",
            },
            {
                "evaluation_no": "FE-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "factory_name": "杭州匠心制衣厂",
                "factory_code": "FAC-0061",
                "assessor": "邵伟",
                "score": Decimal("68.0"),
                "score_level": "D",
                "review_status": "未开始",
                "follow_up_status": "已作废",
                "evaluation_date": date(2026, 5, 4),
                "expiry_date": date(2026, 11, 4),
                "owner": "邵伟",
                "remark": "资质文件待补充，本次评估作废",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_evaluation_no and row["evaluation_no"] != normalized_evaluation_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_factory_name and row["factory_name"] != normalized_factory_name:
                continue
            if normalized_assessor and row["assessor"] != normalized_assessor:
                continue
            if normalized_score_level and row["score_level"] != normalized_score_level:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["evaluation_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["evaluation_no"]),
                        str(row["statement_no"]),
                        str(row["factory_name"]),
                        str(row["factory_code"]),
                        str(row["assessor"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["evaluation_date"], entry["evaluation_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementFactoryEvaluationData(
            items=[
                FactoryStatementFactoryEvaluationItem(
                    evaluation_no=str(row["evaluation_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    supplier=str(row["supplier"]),
                    factory_name=str(row["factory_name"]),
                    factory_code=str(row["factory_code"]),
                    assessor=str(row["assessor"]),
                    score=self._to_decimal(row["score"]),  # type: ignore[arg-type]
                    score_level=str(row["score_level"]),
                    review_status=str(row["review_status"]),
                    follow_up_status=str(row["follow_up_status"]),
                    evaluation_date=row["evaluation_date"],  # type: ignore[arg-type]
                    expiry_date=row["expiry_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_factory_reconciliations(
        self,
        *,
        reconciliation_no: str | None,
        statement_no: str | None,
        supplier: str | None,
        factory_name: str | None,
        settlement_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementFactoryReconciliationData:
        """Read-only factory reconciliation rows for `/factory-statements/list`."""
        normalized_reconciliation_no = self._normalize_text(reconciliation_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_supplier = self._normalize_text(supplier)
        normalized_factory_name = self._normalize_text(factory_name)
        normalized_settlement_status = self._normalize_text(settlement_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "reconciliation_no": "FR-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "factory_name": "东莞卓越制衣厂",
                "factory_code": "FAC-0018",
                "currency": "CNY",
                "reconciliation_amount": Decimal("26800.00"),
                "settled_amount": Decimal("26800.00"),
                "pending_amount": Decimal("0.00"),
                "settlement_status": "已对账",
                "review_status": "已通过",
                "follow_up_status": "已完成",
                "reconciled_at": date(2026, 5, 1),
                "due_date": date(2026, 5, 3),
                "owner": "李佳琳",
                "remark": "批次加工费核对完成",
            },
            {
                "reconciliation_no": "FR-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "factory_name": "广州星河辅料厂",
                "factory_code": "FAC-0033",
                "currency": "CNY",
                "reconciliation_amount": Decimal("21450.00"),
                "settled_amount": Decimal("12000.00"),
                "pending_amount": Decimal("9450.00"),
                "settlement_status": "待对账",
                "review_status": "待复核",
                "follow_up_status": "待跟进",
                "reconciled_at": date(2026, 5, 2),
                "due_date": date(2026, 5, 5),
                "owner": "周晨",
                "remark": "辅料损耗争议待处理",
            },
            {
                "reconciliation_no": "FR-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "factory_name": "深圳远航加工厂",
                "factory_code": "FAC-0046",
                "currency": "CNY",
                "reconciliation_amount": Decimal("18730.00"),
                "settled_amount": Decimal("6000.00"),
                "pending_amount": Decimal("12730.00"),
                "settlement_status": "对账中",
                "review_status": "复核中",
                "follow_up_status": "跟进中",
                "reconciled_at": date(2026, 5, 3),
                "due_date": date(2026, 5, 6),
                "owner": "吴静怡",
                "remark": "返工费用凭证待补充",
            },
            {
                "reconciliation_no": "FR-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "factory_name": "杭州匠心制衣厂",
                "factory_code": "FAC-0061",
                "currency": "CNY",
                "reconciliation_amount": Decimal("13200.00"),
                "settled_amount": Decimal("0.00"),
                "pending_amount": Decimal("13200.00"),
                "settlement_status": "已作废",
                "review_status": "未开始",
                "follow_up_status": "已作废",
                "reconciled_at": date(2026, 5, 4),
                "due_date": date(2026, 5, 7),
                "owner": "邵伟",
                "remark": "单据重复提交，作废重建",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_reconciliation_no and row["reconciliation_no"] != normalized_reconciliation_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_supplier and row["supplier"] != normalized_supplier:
                continue
            if normalized_factory_name and row["factory_name"] != normalized_factory_name:
                continue
            if normalized_settlement_status and row["settlement_status"] != normalized_settlement_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["reconciled_at"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["reconciliation_no"]),
                        str(row["statement_no"]),
                        str(row["supplier"]),
                        str(row["factory_name"]),
                        str(row["factory_code"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["reconciled_at"], entry["reconciliation_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementFactoryReconciliationData(
            items=[
                FactoryStatementFactoryReconciliationItem(
                    reconciliation_no=str(row["reconciliation_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    supplier=str(row["supplier"]),
                    factory_name=str(row["factory_name"]),
                    factory_code=str(row["factory_code"]),
                    currency=str(row["currency"]),
                    reconciliation_amount=self._to_decimal(row["reconciliation_amount"]),  # type: ignore[arg-type]
                    settled_amount=self._to_decimal(row["settled_amount"]),  # type: ignore[arg-type]
                    pending_amount=self._to_decimal(row["pending_amount"]),  # type: ignore[arg-type]
                    settlement_status=str(row["settlement_status"]),
                    review_status=str(row["review_status"]),
                    follow_up_status=str(row["follow_up_status"]),
                    reconciled_at=row["reconciled_at"],  # type: ignore[arg-type]
                    due_date=row["due_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_factory_payable_summaries(
        self,
        *,
        summary_no: str | None,
        statement_no: str | None,
        supplier: str | None,
        factory_name: str | None,
        risk_level: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementFactoryPayableSummaryData:
        """Read-only factory payable summary rows for `/factory-statements/list`."""
        normalized_summary_no = self._normalize_text(summary_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_supplier = self._normalize_text(supplier)
        normalized_factory_name = self._normalize_text(factory_name)
        normalized_risk_level = self._normalize_text(risk_level)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        source_rows = self._build_factory_payable_summary_rows(
            from_date=from_date,
            to_date=to_date,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in source_rows:
            if normalized_summary_no and row["summary_no"] != normalized_summary_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_supplier and row["supplier"] != normalized_supplier:
                continue
            if normalized_factory_name and row["factory_name"] != normalized_factory_name:
                continue
            if normalized_risk_level and row["risk_level"] != normalized_risk_level:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["summary_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["summary_no"]),
                        str(row["statement_no"]),
                        str(row["supplier"]),
                        str(row["factory_name"]),
                        str(row["factory_code"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["summary_date"], entry["summary_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementFactoryPayableSummaryData(
            items=[
                FactoryStatementFactoryPayableSummaryItem(
                    summary_no=str(row["summary_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    supplier=str(row["supplier"]),
                    factory_name=str(row["factory_name"]),
                    factory_code=str(row["factory_code"]),
                    currency=str(row["currency"]),
                    opening_payable=self._to_decimal(row["opening_payable"]),  # type: ignore[arg-type]
                    current_payable=self._to_decimal(row["current_payable"]),  # type: ignore[arg-type]
                    paid_amount=self._to_decimal(row["paid_amount"]),  # type: ignore[arg-type]
                    ending_payable=self._to_decimal(row["ending_payable"]),  # type: ignore[arg-type]
                    aging_30=self._to_decimal(row["aging_30"]),  # type: ignore[arg-type]
                    aging_60=self._to_decimal(row["aging_60"]),  # type: ignore[arg-type]
                    aging_90_plus=self._to_decimal(row["aging_90_plus"]),  # type: ignore[arg-type]
                    risk_level=str(row["risk_level"]),
                    review_status=str(row["review_status"]),
                    summary_date=row["summary_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_supplier_evaluations(
        self,
        *,
        evaluation_no: str | None,
        statement_no: str | None,
        supplier: str | None,
        assessor: str | None,
        score_level: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementSupplierEvaluationData:
        """Read-only supplier evaluation rows for `/factory-statements/list`."""
        normalized_evaluation_no = self._normalize_text(evaluation_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_supplier = self._normalize_text(supplier)
        normalized_assessor = self._normalize_text(assessor)
        normalized_score_level = self._normalize_text(score_level)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "evaluation_no": "SE-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "supplier_code": "SUP-0018",
                "assessor": "李佳琳",
                "score": Decimal("90.0"),
                "score_level": "A",
                "review_status": "已通过",
                "follow_up_status": "已完成",
                "evaluation_date": date(2026, 5, 1),
                "expiry_date": date(2026, 11, 1),
                "owner": "李佳琳",
                "remark": "履约稳定、质量达标，维持核心合作级别。",
            },
            {
                "evaluation_no": "SE-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "supplier_code": "SUP-0033",
                "assessor": "周晨",
                "score": Decimal("83.0"),
                "score_level": "B",
                "review_status": "待复核",
                "follow_up_status": "待跟进",
                "evaluation_date": date(2026, 5, 2),
                "expiry_date": date(2026, 11, 2),
                "owner": "周晨",
                "remark": "交付及时性轻微波动，需跟踪改善。",
            },
            {
                "evaluation_no": "SE-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "supplier_code": "SUP-0046",
                "assessor": "吴静怡",
                "score": Decimal("75.5"),
                "score_level": "C",
                "review_status": "复核中",
                "follow_up_status": "跟进中",
                "evaluation_date": date(2026, 5, 3),
                "expiry_date": date(2026, 11, 3),
                "owner": "吴静怡",
                "remark": "成本控制偏弱，需落实降本计划。",
            },
            {
                "evaluation_no": "SE-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "supplier_code": "SUP-0061",
                "assessor": "邵伟",
                "score": Decimal("68.5"),
                "score_level": "D",
                "review_status": "未开始",
                "follow_up_status": "已作废",
                "evaluation_date": date(2026, 5, 4),
                "expiry_date": date(2026, 11, 4),
                "owner": "邵伟",
                "remark": "资质复核未完成，本次评估作废待重评。",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_evaluation_no and row["evaluation_no"] != normalized_evaluation_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_supplier and row["supplier"] != normalized_supplier:
                continue
            if normalized_assessor and row["assessor"] != normalized_assessor:
                continue
            if normalized_score_level and row["score_level"] != normalized_score_level:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["evaluation_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["evaluation_no"]),
                        str(row["statement_no"]),
                        str(row["supplier"]),
                        str(row["supplier_code"]),
                        str(row["assessor"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["evaluation_date"], entry["evaluation_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementSupplierEvaluationData(
            items=[
                FactoryStatementSupplierEvaluationItem(
                    evaluation_no=str(row["evaluation_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    supplier=str(row["supplier"]),
                    supplier_code=str(row["supplier_code"]),
                    assessor=str(row["assessor"]),
                    score=self._to_decimal(row["score"]),  # type: ignore[arg-type]
                    score_level=str(row["score_level"]),
                    review_status=str(row["review_status"]),
                    follow_up_status=str(row["follow_up_status"]),
                    evaluation_date=row["evaluation_date"],  # type: ignore[arg-type]
                    expiry_date=row["expiry_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_supplier_reconciliations(
        self,
        *,
        reconciliation_no: str | None,
        statement_no: str | None,
        supplier: str | None,
        supplier_code: str | None,
        settlement_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementSupplierReconciliationData:
        """Read-only supplier reconciliation rows for `/factory-statements/list`."""
        normalized_reconciliation_no = self._normalize_text(reconciliation_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_supplier = self._normalize_text(supplier)
        normalized_supplier_code = self._normalize_text(supplier_code)
        normalized_settlement_status = self._normalize_text(settlement_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "reconciliation_no": "SR-2026-0501",
                "statement_no": "FS-202605011140-9C12A8",
                "company": "凌云服饰",
                "supplier": "东莞卓越制衣厂",
                "supplier_code": "SUP-0018",
                "currency": "CNY",
                "reconciliation_amount": Decimal("23150.00"),
                "settled_amount": Decimal("18000.00"),
                "pending_amount": Decimal("5150.00"),
                "settlement_status": "部分结算",
                "review_status": "已通过",
                "follow_up_status": "已完成",
                "reconciled_at": date(2026, 5, 1),
                "due_date": date(2026, 5, 20),
                "owner": "李佳琳",
                "remark": "账差已确认，剩余尾款按账期结清。",
            },
            {
                "reconciliation_no": "SR-2026-0502",
                "statement_no": "FS-202605021255-6D77B1",
                "company": "凌云服饰",
                "supplier": "广州星河辅料厂",
                "supplier_code": "SUP-0033",
                "currency": "CNY",
                "reconciliation_amount": Decimal("19840.00"),
                "settled_amount": Decimal("10200.00"),
                "pending_amount": Decimal("9640.00"),
                "settlement_status": "部分结算",
                "review_status": "待复核",
                "follow_up_status": "待跟进",
                "reconciled_at": date(2026, 5, 2),
                "due_date": date(2026, 5, 22),
                "owner": "周晨",
                "remark": "存在辅料损耗争议，待复核后结算。",
            },
            {
                "reconciliation_no": "SR-2026-0503",
                "statement_no": "FS-202605031420-1F39E6",
                "company": "凌云服饰",
                "supplier": "深圳远航加工厂",
                "supplier_code": "SUP-0046",
                "currency": "CNY",
                "reconciliation_amount": Decimal("17420.00"),
                "settled_amount": Decimal("0.00"),
                "pending_amount": Decimal("17420.00"),
                "settlement_status": "未结算",
                "review_status": "复核中",
                "follow_up_status": "跟进中",
                "reconciled_at": date(2026, 5, 3),
                "due_date": date(2026, 5, 24),
                "owner": "吴静怡",
                "remark": "批次退补料未闭环，暂缓出账。",
            },
            {
                "reconciliation_no": "SR-2026-0504",
                "statement_no": "FS-202605041605-8B65C4",
                "company": "凌云服饰",
                "supplier": "杭州匠心制衣厂",
                "supplier_code": "SUP-0061",
                "currency": "CNY",
                "reconciliation_amount": Decimal("12600.00"),
                "settled_amount": Decimal("12600.00"),
                "pending_amount": Decimal("0.00"),
                "settlement_status": "已结算",
                "review_status": "未开始",
                "follow_up_status": "已作废",
                "reconciled_at": date(2026, 5, 4),
                "due_date": date(2026, 5, 18),
                "owner": "邵伟",
                "remark": "结算完成，复核单据待补传，当前条目作废重开。",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_reconciliation_no and row["reconciliation_no"] != normalized_reconciliation_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_supplier and row["supplier"] != normalized_supplier:
                continue
            if normalized_supplier_code and row["supplier_code"] != normalized_supplier_code:
                continue
            if normalized_settlement_status and row["settlement_status"] != normalized_settlement_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["reconciled_at"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["reconciliation_no"]),
                        str(row["statement_no"]),
                        str(row["supplier"]),
                        str(row["supplier_code"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["reconciled_at"], entry["reconciliation_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementSupplierReconciliationData(
            items=[
                FactoryStatementSupplierReconciliationItem(
                    reconciliation_no=str(row["reconciliation_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    supplier=str(row["supplier"]),
                    supplier_code=str(row["supplier_code"]),
                    currency=str(row["currency"]),
                    reconciliation_amount=self._to_decimal(row["reconciliation_amount"]),  # type: ignore[arg-type]
                    settled_amount=self._to_decimal(row["settled_amount"]),  # type: ignore[arg-type]
                    pending_amount=self._to_decimal(row["pending_amount"]),  # type: ignore[arg-type]
                    settlement_status=str(row["settlement_status"]),
                    review_status=str(row["review_status"]),
                    follow_up_status=str(row["follow_up_status"]),
                    reconciled_at=row["reconciled_at"],  # type: ignore[arg-type]
                    due_date=row["due_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_supplier_payable_summaries(
        self,
        *,
        summary_no: str | None,
        statement_no: str | None,
        supplier: str | None,
        supplier_code: str | None,
        risk_level: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementSupplierPayableSummaryData:
        """Read-only supplier payable summary rows for `/factory-statements/list`."""
        normalized_summary_no = self._normalize_text(summary_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_supplier = self._normalize_text(supplier)
        normalized_supplier_code = self._normalize_text(supplier_code)
        normalized_risk_level = self._normalize_text(risk_level)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        source_rows = self._build_supplier_payable_summary_rows(
            from_date=from_date,
            to_date=to_date,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in source_rows:
            if normalized_summary_no and row["summary_no"] != normalized_summary_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_supplier and row["supplier"] != normalized_supplier:
                continue
            if normalized_supplier_code and row["supplier_code"] != normalized_supplier_code:
                continue
            if normalized_risk_level and row["risk_level"] != normalized_risk_level:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["summary_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["summary_no"]),
                        str(row["statement_no"]),
                        str(row["supplier"]),
                        str(row["supplier_code"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["summary_date"], entry["summary_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementSupplierPayableSummaryData(
            items=[
                FactoryStatementSupplierPayableSummaryItem(
                    summary_no=str(row["summary_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    supplier=str(row["supplier"]),
                    supplier_code=str(row["supplier_code"]),
                    currency=str(row["currency"]),
                    opening_payable=self._to_decimal(row["opening_payable"]),  # type: ignore[arg-type]
                    current_payable=self._to_decimal(row["current_payable"]),  # type: ignore[arg-type]
                    paid_amount=self._to_decimal(row["paid_amount"]),  # type: ignore[arg-type]
                    ending_payable=self._to_decimal(row["ending_payable"]),  # type: ignore[arg-type]
                    aging_30=self._to_decimal(row["aging_30"]),  # type: ignore[arg-type]
                    aging_60=self._to_decimal(row["aging_60"]),  # type: ignore[arg-type]
                    aging_90_plus=self._to_decimal(row["aging_90_plus"]),  # type: ignore[arg-type]
                    risk_level=str(row["risk_level"]),
                    review_status=str(row["review_status"]),
                    follow_up_status=str(row["follow_up_status"]),
                    summary_date=row["summary_date"],  # type: ignore[arg-type]
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_bank_ledgers(
        self,
        *,
        ledger_no: str | None,
        statement_no: str | None,
        bank_name: str | None,
        account_name: str | None,
        transaction_type: str | None,
        ledger_status: str | None,
        review_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementBankLedgerData:
        """Read-only bank ledger rows for `/factory-statements/list`."""
        normalized_ledger_no = self._normalize_text(ledger_no)
        normalized_statement_no = self._normalize_text(statement_no)
        normalized_bank_name = self._normalize_text(bank_name)
        normalized_account_name = self._normalize_text(account_name)
        normalized_transaction_type = self._normalize_text(transaction_type)
        normalized_ledger_status = self._normalize_text(ledger_status)
        normalized_review_status = self._normalize_text(review_status)
        normalized_keyword = self._normalize_text(keyword)

        if from_date and to_date and from_date > to_date:
            raise BusinessException(code=FACTORY_STATEMENT_PERIOD_INVALID)

        seed_rows: list[dict[str, object]] = [
            {
                "ledger_no": "BL-2026-0601",
                "statement_no": "FS-202606011035-1A92CD",
                "company": "凌云服饰",
                "supplier": "绍兴华绣制衣厂",
                "bank_name": "招商银行东莞分行",
                "account_name": "凌云服饰主结算户",
                "account_no": "6214****1832",
                "currency": "CNY",
                "transaction_type": "收入",
                "debit_amount": Decimal("0.00"),
                "credit_amount": Decimal("12600.00"),
                "balance_after": Decimal("468210.32"),
                "ledger_status": "待登记",
                "review_status": "未开始",
                "ledger_date": date(2026, 6, 1),
                "voucher_no": "VCH-260601-01",
                "owner": "周敏",
                "remark": "客户回款入账，待财务登记。",
            },
            {
                "ledger_no": "BL-2026-0602",
                "statement_no": "FS-202606021130-6B14EF",
                "company": "凌云服饰",
                "supplier": "嘉兴瑞泰辅料厂",
                "bank_name": "中国银行广州分行",
                "account_name": "凌云服饰运营户",
                "account_no": "6216****9021",
                "currency": "CNY",
                "transaction_type": "支出",
                "debit_amount": Decimal("18960.00"),
                "credit_amount": Decimal("0.00"),
                "balance_after": Decimal("329402.15"),
                "ledger_status": "复核中",
                "review_status": "复核中",
                "ledger_date": date(2026, 6, 2),
                "voucher_no": "VCH-260602-02",
                "owner": "刘晨",
                "remark": "供应商货款支付，需二次复核。",
            },
            {
                "ledger_no": "BL-2026-0603",
                "statement_no": "FS-202606031455-9D77AC",
                "company": "凌云服饰",
                "supplier": "湖州恒远加工厂",
                "bank_name": "工商银行深圳分行",
                "account_name": "凌云服饰资金池账户",
                "account_no": "6222****6678",
                "currency": "CNY",
                "transaction_type": "手续费",
                "debit_amount": Decimal("86.00"),
                "credit_amount": Decimal("0.00"),
                "balance_after": Decimal("329316.15"),
                "ledger_status": "已对账",
                "review_status": "已通过",
                "ledger_date": date(2026, 6, 3),
                "voucher_no": "VCH-260603-03",
                "owner": "吴静",
                "remark": "月度银行手续费，已完成对账。",
            },
            {
                "ledger_no": "BL-2026-0604",
                "statement_no": "FS-202606041210-5C11BE",
                "company": "凌云服饰",
                "supplier": "宁波雅诚服装厂",
                "bank_name": "建设银行杭州分行",
                "account_name": "凌云服饰主结算户",
                "account_no": "6214****1832",
                "currency": "CNY",
                "transaction_type": "收入",
                "debit_amount": Decimal("0.00"),
                "credit_amount": Decimal("8400.00"),
                "balance_after": Decimal("337716.15"),
                "ledger_status": "已归档",
                "review_status": "已通过",
                "ledger_date": date(2026, 6, 4),
                "voucher_no": "VCH-260604-04",
                "owner": "邵伟",
                "remark": "对账周期闭环，流水归档。",
            },
        ]

        filtered_rows: list[dict[str, object]] = []
        keyword_lc = (normalized_keyword or "").lower()
        for row in seed_rows:
            if normalized_ledger_no and row["ledger_no"] != normalized_ledger_no:
                continue
            if normalized_statement_no and row["statement_no"] != normalized_statement_no:
                continue
            if normalized_bank_name and row["bank_name"] != normalized_bank_name:
                continue
            if normalized_account_name and row["account_name"] != normalized_account_name:
                continue
            if normalized_transaction_type and row["transaction_type"] != normalized_transaction_type:
                continue
            if normalized_ledger_status and row["ledger_status"] != normalized_ledger_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue

            row_company = str(row["company"])
            row_supplier = str(row["supplier"])
            if readable_companies is not None and row_company not in readable_companies:
                continue
            if readable_suppliers is not None and row_supplier not in readable_suppliers:
                continue

            row_date = row["ledger_date"]
            if from_date and isinstance(row_date, date) and row_date < from_date:
                continue
            if to_date and isinstance(row_date, date) and row_date > to_date:
                continue

            if keyword_lc:
                haystack = " ".join(
                    [
                        str(row["ledger_no"]),
                        str(row["statement_no"]),
                        str(row["bank_name"]),
                        str(row["account_name"]),
                        str(row["voucher_no"]),
                        str(row["owner"]),
                        str(row["remark"]),
                    ]
                ).lower()
                if keyword_lc not in haystack:
                    continue

            filtered_rows.append(row)

        filtered_rows.sort(
            key=lambda entry: (entry["ledger_date"], entry["ledger_no"]),  # type: ignore[index]
            reverse=True,
        )

        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FactoryStatementBankLedgerData(
            items=[
                FactoryStatementBankLedgerItem(
                    ledger_no=str(row["ledger_no"]),
                    statement_no=str(row["statement_no"]),
                    company=str(row["company"]),
                    bank_name=str(row["bank_name"]),
                    account_name=str(row["account_name"]),
                    account_no=str(row["account_no"]),
                    currency=str(row["currency"]),
                    transaction_type=str(row["transaction_type"]),
                    debit_amount=self._to_decimal(row["debit_amount"]),  # type: ignore[arg-type]
                    credit_amount=self._to_decimal(row["credit_amount"]),  # type: ignore[arg-type]
                    balance_after=self._to_decimal(row["balance_after"]),  # type: ignore[arg-type]
                    ledger_status=str(row["ledger_status"]),
                    review_status=str(row["review_status"]),
                    ledger_date=row["ledger_date"],  # type: ignore[arg-type]
                    voucher_no=str(row["voucher_no"]),
                    owner=str(row["owner"]),
                    remark=str(row["remark"]),
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
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
        erp_adapter: ERPNextPurchaseInvoiceAdapter | None,
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

        if erp_adapter is None:
            self._validate_fastapi_payable_draft_fields(
                payable_account=payable_account,
                cost_center=cost_center,
            )
        else:
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
                if not self._is_local_dev_sqlite_mode():
                    raise BusinessException(code=FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE, message=str(exc.message)) from exc
            except Exception as exc:
                if not self._is_local_dev_sqlite_mode():
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

    @classmethod
    def _validate_fastapi_payable_draft_fields(
        cls,
        *,
        payable_account: str | None,
        cost_center: str | None,
    ) -> None:
        account = (payable_account or "").strip()
        account_upper = account.upper()
        if not account or not (account.startswith("2202") or "AP" in account_upper or "应付" in account):
            raise BusinessException(code=FACTORY_STATEMENT_PAYABLE_ACCOUNT_INVALID)

        center = (cost_center or "").strip()
        center_upper = center.upper()
        if not center or ("-" not in center and not center_upper.startswith("CC")):
            raise BusinessException(code=FACTORY_STATEMENT_COST_CENTER_INVALID)

    def create_payment_entry(
        self,
        *,
        statement_id: int,
        payload: FactoryStatementPaymentCreateRequest,
        operator: str,
        request_id: str,
    ) -> FactoryStatementPaymentData:
        """Create FastAPI-native payment entry allocated to one factory statement."""
        company = self._normalize_text(payload.company)
        supplier = self._normalize_text(payload.supplier)
        statement_no = self._normalize_text(payload.statement_no)
        idempotency_key = self._normalize_text(payload.idempotency_key)
        operation = self._normalize_text(payload.operation) or self._OP_PAYMENT_CREATE

        if not company:
            raise BusinessException(code=FACTORY_STATEMENT_COMPANY_REQUIRED)
        if not idempotency_key:
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="idempotency_key 不能为空")
        if operation != self._OP_PAYMENT_CREATE:
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="operation 非法")

        paid_amount = self._to_decimal(payload.paid_amount)
        if paid_amount <= Decimal("0"):
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_INVALID_PAYLOAD, message="paid_amount 必须大于 0")

        mode_of_payment = self._normalize_text(payload.mode_of_payment) or "Bank Transfer"
        reference_no = self._normalize_text(payload.reference_no)

        try:
            statement = (
                self.session.query(LyFactoryStatement)
                .filter(LyFactoryStatement.id == statement_id)
                .with_for_update()
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

        if statement is None:
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
        if company != str(statement.company):
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="company 与对账单不一致")
        if supplier is not None and supplier != str(statement.supplier):
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="supplier 与对账单不一致")
        if statement_no is not None and statement_no != str(statement.statement_no):
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="statement_no 与对账单不一致")
        if str(statement.statement_status) not in {self._STATUS_CONFIRMED, self._STATUS_PAYABLE_DRAFT_CREATED}:
            raise BusinessException(code=FACTORY_STATEMENT_STATUS_INVALID)

        source_ref = self._normalize_text(payload.source_ref) or f"{statement.statement_no}:{idempotency_key}"
        requested_payment_entry = self._normalize_text(payload.payment_entry)
        request_hash = self._build_payment_request_hash(
            {
                "company": company,
                "statement_id": int(statement.id),
                "statement_no": str(statement.statement_no),
                "supplier": str(statement.supplier),
                "posting_date": payload.posting_date.isoformat(),
                "paid_amount": str(paid_amount),
                "mode_of_payment": mode_of_payment,
                "reference_no": reference_no,
                "reference_date": payload.reference_date.isoformat() if payload.reference_date else None,
                "requested_payment_entry": requested_payment_entry,
                "source_ref": source_ref,
            }
        )

        existing_idem = self._find_payment_by_idempotency(company=company, idempotency_key=idempotency_key)
        if existing_idem is not None:
            if str(existing_idem.request_hash) != request_hash:
                raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="幂等键冲突且请求内容不一致")
            return self._to_payment_data(existing_idem)

        existing_source = self._find_payment_by_source_ref(company=company, source_ref=source_ref)
        if existing_source is not None:
            if str(existing_source.request_hash) != request_hash:
                raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="source_ref 已存在且请求内容不一致")
            return self._to_payment_data(existing_source)

        outstanding_before = self._compute_outstanding_amount(
            net_amount=self._to_decimal(statement.net_amount),
            paid_amount=self._paid_amount_for_statement(statement_id=int(statement.id)),
        )
        if outstanding_before <= Decimal("0"):
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_ALREADY_PAID)
        if paid_amount > outstanding_before:
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_AMOUNT_EXCEEDED)

        payment_entry = requested_payment_entry or self._next_factory_statement_payment_entry(
            company=company,
            posting_date=payload.posting_date,
        )
        existing_payment = self._find_payment_by_no(company=company, payment_entry=payment_entry)
        if existing_payment is not None:
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="payment_entry 已存在")

        outstanding_after = outstanding_before - paid_amount
        row = LyFactoryStatementPayment(
            company=company,
            payment_entry=payment_entry,
            statement_id=int(statement.id),
            statement_no=str(statement.statement_no),
            supplier=str(statement.supplier),
            posting_date=payload.posting_date,
            paid_amount=paid_amount,
            allocated_amount=paid_amount,
            outstanding_before=outstanding_before,
            outstanding_after=outstanding_after,
            mode_of_payment=mode_of_payment,
            reference_no=reference_no,
            reference_date=payload.reference_date,
            status="submitted",
            docstatus=1,
            source_ref=source_ref,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            scenario_tag=self._normalize_text(payload.scenario_tag),
            payload={
                "operation": operation,
                "scenario_tag": self._normalize_text(payload.scenario_tag),
                "statement_no": str(statement.statement_no),
            },
            created_by=self._normalize_text(operator) or "system",
        )
        self.session.add(row)
        self.session.add(
            LyFactoryStatementLog(
                statement_id=int(statement.id),
                company=str(statement.company),
                supplier=str(statement.supplier),
                from_status=str(statement.statement_status),
                to_status=str(statement.statement_status),
                action="factory_statement:payment_create",
                operator=self._normalize_text(operator) or "system",
                request_id=self._normalize_text(request_id),
                remark=f"payment:{payment_entry}",
            )
        )
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT) from exc
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
        return self._to_payment_data(row)

    def cancel_payment_entry(
        self,
        *,
        statement_id: int,
        payment_id: int,
        payload: FactoryStatementPaymentCancelRequest,
        operator: str,
        request_id: str,
    ) -> FactoryStatementPaymentData:
        """Cancel a submitted local payment entry and reopen statement payable balance."""
        company = self._normalize_text(payload.company)
        statement_no = self._normalize_text(payload.statement_no)
        idempotency_key = self._normalize_text(payload.idempotency_key)
        reason = self._normalize_text(payload.reason)
        operation = self._normalize_text(payload.operation) or self._OP_PAYMENT_CANCEL

        if not company:
            raise BusinessException(code=FACTORY_STATEMENT_COMPANY_REQUIRED)
        if not idempotency_key:
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="idempotency_key 不能为空")
        if operation != self._OP_PAYMENT_CANCEL:
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="operation 非法")

        try:
            statement = (
                self.session.query(LyFactoryStatement)
                .filter(LyFactoryStatement.id == statement_id)
                .with_for_update()
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

        if statement is None:
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
        if company != str(statement.company):
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="company 与对账单不一致")
        if statement_no is not None and statement_no != str(statement.statement_no):
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="statement_no 与对账单不一致")

        row = self._find_payment_by_id_for_update(
            company=company,
            statement_id=statement_id,
            payment_id=payment_id,
        )
        if row is None:
            raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)

        request_hash = self._build_payment_request_hash(
            {
                "company": company,
                "statement_id": int(statement.id),
                "statement_no": str(statement.statement_no),
                "payment_id": int(row.id),
                "payment_entry": str(row.payment_entry),
                "operation": operation,
                "reason": reason,
            }
        )

        existing_operation = self._find_payment_operation_by_idempotency(
            company=company,
            operation_type=operation,
            idempotency_key=idempotency_key,
        )
        if existing_operation is not None:
            if str(existing_operation.request_hash or "") != request_hash:
                raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="幂等键冲突且请求内容不一致")
            replay_payment = self._find_payment_by_id(
                company=company,
                statement_id=int(existing_operation.statement_id),
                payment_id=int(existing_operation.payment_id),
            )
            if replay_payment is None:
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
            return self._to_payment_data(replay_payment)

        if str(row.status) != "submitted":
            raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="付款已作废")

        now = datetime.utcnow()
        row.status = "cancelled"
        row.docstatus = 2
        row.updated_by = self._normalize_text(operator) or "system"
        row.updated_at = now

        payment_operation = LyFactoryStatementPaymentOperation(
            company=company,
            statement_id=int(statement.id),
            payment_id=int(row.id),
            operation_type=operation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            result_status="cancelled",
            result_user=self._normalize_text(operator) or "system",
            result_at=now,
            reason=reason,
        )
        self.session.add(payment_operation)
        self.session.add(
            LyFactoryStatementLog(
                statement_id=int(statement.id),
                company=str(statement.company),
                supplier=str(statement.supplier),
                from_status="submitted",
                to_status="cancelled",
                action="factory_statement:payment_cancel",
                operator=self._normalize_text(operator) or "system",
                request_id=self._normalize_text(request_id),
                remark=f"payment:{row.payment_entry}",
            )
        )

        replay_operation = self._flush_payment_operation_or_resolve_replay(
            company=company,
            operation_type=operation,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        if replay_operation is not None:
            replay_payment = self._find_payment_by_id(
                company=company,
                statement_id=int(replay_operation.statement_id),
                payment_id=int(replay_operation.payment_id),
            )
            if replay_payment is None:
                raise BusinessException(code=FACTORY_STATEMENT_SOURCE_NOT_FOUND)
            return self._to_payment_data(replay_payment)

        return self._to_payment_data(row)

    def list_payment_entries(
        self,
        *,
        company: str | None,
        statement_id: int | None,
        statement_no: str | None,
        supplier: str | None,
        status: str | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> FactoryStatementPaymentListData:
        rows = self._query_payment_entries(
            company=company,
            statement_id=statement_id,
            statement_no=statement_no,
            supplier=supplier,
            status=status,
            keyword=keyword,
        )
        total = len(rows)
        start = max((page - 1) * page_size, 0)
        return FactoryStatementPaymentListData(
            items=[self._to_payment_data(row) for row in rows[start : start + page_size]],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_purchase_invoices(
        self,
        *,
        company: str | None,
        supplier: str | None,
        supplier_name: str | None,
        status: str | None,
        page: int,
        page_size: int,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> FactoryStatementPurchaseInvoiceListData:
        """List payable outbox / purchase invoice readback from local facts."""
        normalized_company = self._normalize_text(company)
        normalized_supplier = self._normalize_text(supplier) or self._normalize_text(supplier_name)
        normalized_status = self._normalize_text(status)

        try:
            query = (
                self.session.query(LyFactoryStatementPayableOutbox, LyFactoryStatement)
                .join(LyFactoryStatement, LyFactoryStatement.id == LyFactoryStatementPayableOutbox.statement_id)
            )
            if normalized_company:
                query = query.filter(LyFactoryStatementPayableOutbox.company == normalized_company)
            if normalized_supplier:
                query = query.filter(LyFactoryStatementPayableOutbox.supplier == normalized_supplier)

            if readable_companies is not None:
                if not readable_companies:
                    return FactoryStatementPurchaseInvoiceListData(items=[], total=0, page=page, page_size=page_size)
                query = query.filter(LyFactoryStatementPayableOutbox.company.in_(sorted(readable_companies)))
            if readable_suppliers is not None:
                if not readable_suppliers:
                    return FactoryStatementPurchaseInvoiceListData(items=[], total=0, page=page, page_size=page_size)
                query = query.filter(LyFactoryStatementPayableOutbox.supplier.in_(sorted(readable_suppliers)))

            rows = (
                query.order_by(
                    LyFactoryStatementPayableOutbox.created_at.desc(),
                    LyFactoryStatementPayableOutbox.id.desc(),
                )
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        except Exception as exc:
            raise BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR) from exc

        statement_ids = [int(statement.id) for _, statement in rows]
        paid_amount_map = self._fetch_paid_amount_map(statement_ids=statement_ids)
        items: list[FactoryStatementPurchaseInvoiceItem] = []
        for outbox, statement in rows:
            item = self._to_purchase_invoice_item(
                outbox=outbox,
                statement=statement,
                paid_amount=paid_amount_map.get(int(statement.id), Decimal("0")),
            )
            if normalized_status and item.status != normalized_status:
                continue
            items.append(item)

        total = len(items)
        start = max((page - 1) * page_size, 0)
        return FactoryStatementPurchaseInvoiceListData(
            items=items[start : start + page_size],
            total=total,
            page=page,
            page_size=page_size,
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

    def _fetch_paid_amount_map(self, *, statement_ids: list[int]) -> dict[int, Decimal]:
        if not statement_ids:
            return {}
        try:
            rows = (
                self.session.query(
                    LyFactoryStatementPayment.statement_id,
                    func.coalesce(func.sum(LyFactoryStatementPayment.paid_amount), 0),
                )
                .filter(
                    LyFactoryStatementPayment.statement_id.in_(statement_ids),
                    LyFactoryStatementPayment.status == "submitted",
                )
                .group_by(LyFactoryStatementPayment.statement_id)
                .all()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        return {int(statement_id): self._to_decimal(amount) for statement_id, amount in rows}

    def _paid_amount_for_statement(self, *, statement_id: int) -> Decimal:
        try:
            amount = (
                self.session.query(func.coalesce(func.sum(LyFactoryStatementPayment.paid_amount), 0))
                .filter(
                    LyFactoryStatementPayment.statement_id == statement_id,
                    LyFactoryStatementPayment.status == "submitted",
                )
                .scalar()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        return self._to_decimal(amount)

    def _find_payment_by_idempotency(
        self,
        *,
        company: str,
        idempotency_key: str,
    ) -> LyFactoryStatementPayment | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayment)
                .filter(
                    LyFactoryStatementPayment.company == company,
                    LyFactoryStatementPayment.idempotency_key == idempotency_key,
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _find_payment_by_source_ref(
        self,
        *,
        company: str,
        source_ref: str,
    ) -> LyFactoryStatementPayment | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayment)
                .filter(
                    LyFactoryStatementPayment.company == company,
                    LyFactoryStatementPayment.source_ref == source_ref,
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _find_payment_by_no(
        self,
        *,
        company: str,
        payment_entry: str,
    ) -> LyFactoryStatementPayment | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayment)
                .filter(
                    LyFactoryStatementPayment.company == company,
                    LyFactoryStatementPayment.payment_entry == payment_entry,
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _find_payment_by_id(
        self,
        *,
        company: str,
        statement_id: int,
        payment_id: int,
    ) -> LyFactoryStatementPayment | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayment)
                .filter(
                    LyFactoryStatementPayment.company == company,
                    LyFactoryStatementPayment.statement_id == int(statement_id),
                    LyFactoryStatementPayment.id == int(payment_id),
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _find_payment_by_id_for_update(
        self,
        *,
        company: str,
        statement_id: int,
        payment_id: int,
    ) -> LyFactoryStatementPayment | None:
        try:
            return (
                self.session.query(LyFactoryStatementPayment)
                .filter(
                    LyFactoryStatementPayment.company == company,
                    LyFactoryStatementPayment.statement_id == int(statement_id),
                    LyFactoryStatementPayment.id == int(payment_id),
                )
                .with_for_update()
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _find_payment_operation_by_idempotency(
        self,
        *,
        company: str,
        operation_type: str,
        idempotency_key: str | None,
    ) -> LyFactoryStatementPaymentOperation | None:
        try:
            return (
                self.session.query(LyFactoryStatementPaymentOperation)
                .filter(
                    LyFactoryStatementPaymentOperation.company == company,
                    LyFactoryStatementPaymentOperation.operation_type == operation_type,
                    LyFactoryStatementPaymentOperation.idempotency_key == idempotency_key,
                )
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _query_payment_entries(
        self,
        *,
        company: str | None,
        statement_id: int | None,
        statement_no: str | None,
        supplier: str | None,
        status: str | None,
        keyword: str | None,
    ) -> list[LyFactoryStatementPayment]:
        try:
            query = self.session.query(LyFactoryStatementPayment)
            normalized_company = self._normalize_text(company)
            normalized_statement_no = self._normalize_text(statement_no)
            normalized_supplier = self._normalize_text(supplier)
            normalized_status = self._normalize_text(status)
            if normalized_company:
                query = query.filter(LyFactoryStatementPayment.company == normalized_company)
            if statement_id is not None:
                query = query.filter(LyFactoryStatementPayment.statement_id == int(statement_id))
            if normalized_statement_no:
                query = query.filter(LyFactoryStatementPayment.statement_no == normalized_statement_no)
            if normalized_supplier:
                query = query.filter(LyFactoryStatementPayment.supplier == normalized_supplier)
            if normalized_status:
                query = query.filter(LyFactoryStatementPayment.status == normalized_status)
            rows = query.order_by(LyFactoryStatementPayment.created_at.desc(), LyFactoryStatementPayment.id.desc()).all()
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

        normalized_keyword = self._normalize_text(keyword)
        if normalized_keyword:
            rows = [
                row
                for row in rows
                if self._contains_like(
                    " ".join(
                        [
                            str(row.payment_entry),
                            str(row.statement_no),
                            str(row.supplier),
                            str(row.mode_of_payment),
                            self._normalize_text(row.reference_no) or "",
                        ]
                    ),
                    normalized_keyword,
                )
            ]
        return rows

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

    def _flush_payment_operation_or_resolve_replay(
        self,
        *,
        company: str,
        operation_type: str,
        idempotency_key: str | None,
        request_hash: str,
    ) -> LyFactoryStatementPaymentOperation | None:
        try:
            self.session.flush()
            return None
        except IntegrityError as exc:
            try:
                self.session.rollback()
            except SQLAlchemyError as rollback_exc:
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from rollback_exc
            existing = self._find_payment_operation_by_idempotency(
                company=company,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
            )
            if existing is None:
                raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc
            if str(existing.request_hash or "") != request_hash:
                raise BusinessException(code=FACTORY_STATEMENT_PAYMENT_CONFLICT, message="幂等键冲突且请求内容不一致")
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
    def _is_local_dev_sqlite_mode() -> bool:
        app_env = os.getenv("APP_ENV", "").strip().lower()
        db_url = os.getenv("LINGYI_DB_URL", "").strip()
        return app_env == "development" and db_url == FactoryStatementService._LOCAL_ALLOWED_DB_URL

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
    def _build_payment_request_hash(payload: dict[str, object]) -> str:
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_statement_no() -> str:
        now = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        suffix = uuid.uuid4().hex[:6].upper()
        return f"FS-{now}-{suffix}"

    def _next_factory_statement_payment_entry(self, *, company: str, posting_date: date) -> str:
        prefix = f"FSP-{posting_date.strftime('%Y%m%d')}-"
        latest = (
            self.session.query(LyFactoryStatementPayment)
            .filter(
                LyFactoryStatementPayment.company == company,
                LyFactoryStatementPayment.payment_entry.like(f"{prefix}%"),
            )
            .order_by(LyFactoryStatementPayment.id.desc())
            .first()
        )
        return f"{prefix}{self._next_numeric_tail(latest.payment_entry if latest is not None else None, prefix):03d}"

    @staticmethod
    def _next_numeric_tail(value: object | None, prefix: str) -> int:
        if value is None:
            return 1
        tail = str(value).replace(prefix, "", 1)
        if tail.isdigit():
            return int(tail) + 1
        return 1

    @staticmethod
    def _compute_rejected_rate(*, inspected_qty: Decimal, rejected_qty: Decimal) -> Decimal:
        if inspected_qty <= 0:
            return Decimal("0")
        return (rejected_qty / inspected_qty).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

    @staticmethod
    def _compute_outstanding_amount(*, net_amount: Decimal, paid_amount: Decimal) -> Decimal:
        outstanding = net_amount - paid_amount
        return outstanding if outstanding > Decimal("0") else Decimal("0")

    @staticmethod
    def _payment_status(*, net_amount: Decimal, paid_amount: Decimal) -> str:
        if net_amount <= Decimal("0"):
            return "paid"
        if paid_amount <= Decimal("0"):
            return "unpaid"
        if paid_amount >= net_amount:
            return "paid"
        return "partly_paid"

    @staticmethod
    def _contains_like(value: str, keyword: str) -> bool:
        return keyword.lower() in value.lower()

    def _build_customer_receivable_summary_rows(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        readable_companies: set[str] | None,
    ) -> list[dict[str, object]]:
        query = self.session.query(LyDeliveryInvoice).filter(
            LyDeliveryInvoice.status != "cancelled",
            LyDeliveryInvoice.docstatus != 2,
        )
        if readable_companies is not None:
            if not readable_companies:
                return []
            query = query.filter(LyDeliveryInvoice.company.in_(sorted(readable_companies)))
        if from_date:
            query = query.filter(LyDeliveryInvoice.posting_date >= from_date)
        if to_date:
            query = query.filter(LyDeliveryInvoice.posting_date <= to_date)

        invoices = query.order_by(LyDeliveryInvoice.posting_date.desc(), LyDeliveryInvoice.id.desc()).all()
        grouped: dict[tuple[str, str], dict[str, object]] = {}
        for invoice in invoices:
            company = str(invoice.company)
            customer = self._normalize_text(invoice.customer) or "未填写客户"
            key = (company, customer)
            row = grouped.setdefault(
                key,
                {
                    "summary_no": f"CRS-{self._stable_code(company)}-{self._stable_code(customer)}",
                    "statement_no": f"AR-{self._stable_code(company)}-{self._stable_code(customer)}",
                    "company": company,
                    "customer_name": customer,
                    "customer_code": customer,
                    "currency": "CNY",
                    "opening_receivable": Decimal("0"),
                    "current_receivable": Decimal("0"),
                    "received_amount": Decimal("0"),
                    "ending_receivable": Decimal("0"),
                    "aging_30": Decimal("0"),
                    "aging_60": Decimal("0"),
                    "aging_90_plus": Decimal("0"),
                    "risk_level": "低风险",
                    "review_status": "已通过",
                    "summary_date": invoice.posting_date,
                    "owner": str(invoice.created_by),
                    "remark": "FastAPI 本地发货开票与回款汇总",
                },
            )
            row["current_receivable"] = self._to_decimal(row["current_receivable"]) + self._to_decimal(invoice.grand_total)
            row["ending_receivable"] = self._to_decimal(row["ending_receivable"]) + self._to_decimal(invoice.outstanding_amount)
            row["summary_date"] = max(row["summary_date"], invoice.posting_date)  # type: ignore[arg-type]
            if self._to_decimal(invoice.outstanding_amount) > Decimal("0"):
                bucket = self._aging_bucket(due_date=invoice.due_date or invoice.posting_date, as_of=to_date)
                row[bucket] = self._to_decimal(row[bucket]) + self._to_decimal(invoice.outstanding_amount)

        if not grouped:
            return []

        payment_query = self.session.query(LySalesPaymentEntry).filter(
            LySalesPaymentEntry.status == "submitted",
            LySalesPaymentEntry.docstatus == 1,
        )
        if readable_companies is not None:
            payment_query = payment_query.filter(LySalesPaymentEntry.company.in_(sorted(readable_companies)))
        if from_date:
            payment_query = payment_query.filter(LySalesPaymentEntry.posting_date >= from_date)
        if to_date:
            payment_query = payment_query.filter(LySalesPaymentEntry.posting_date <= to_date)
        for payment in payment_query.all():
            customer = self._normalize_text(payment.customer) or "未填写客户"
            row = grouped.get((str(payment.company), customer))
            if row is None:
                continue
            row["received_amount"] = self._to_decimal(row["received_amount"]) + self._to_decimal(payment.paid_amount)
            row["summary_date"] = max(row["summary_date"], payment.posting_date)  # type: ignore[arg-type]

        for row in grouped.values():
            self._apply_financial_summary_status(row=row, ending_key="ending_receivable")
        return list(grouped.values())

    def _build_supplier_payable_summary_rows(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> list[dict[str, object]]:
        query = self.session.query(LyMaterialPurchaseInvoice).filter(
            LyMaterialPurchaseInvoice.status != "cancelled",
            LyMaterialPurchaseInvoice.docstatus != 2,
        )
        if readable_companies is not None:
            if not readable_companies:
                return []
            query = query.filter(LyMaterialPurchaseInvoice.company.in_(sorted(readable_companies)))
        if readable_suppliers is not None:
            if not readable_suppliers:
                return []
            query = query.filter(LyMaterialPurchaseInvoice.supplier_name.in_(sorted(readable_suppliers)))
        if from_date:
            query = query.filter(LyMaterialPurchaseInvoice.posting_date >= from_date)
        if to_date:
            query = query.filter(LyMaterialPurchaseInvoice.posting_date <= to_date)

        invoices = query.order_by(LyMaterialPurchaseInvoice.posting_date.desc(), LyMaterialPurchaseInvoice.id.desc()).all()
        grouped: dict[tuple[str, str], dict[str, object]] = {}
        for invoice in invoices:
            company = str(invoice.company)
            supplier = str(invoice.supplier_name)
            key = (company, supplier)
            row = grouped.setdefault(
                key,
                {
                    "summary_no": f"SPS-{self._stable_code(company)}-{self._stable_code(supplier)}",
                    "statement_no": str(invoice.purchase_invoice),
                    "company": company,
                    "supplier": supplier,
                    "supplier_code": supplier,
                    "currency": "CNY",
                    "opening_payable": Decimal("0"),
                    "current_payable": Decimal("0"),
                    "paid_amount": Decimal("0"),
                    "ending_payable": Decimal("0"),
                    "aging_30": Decimal("0"),
                    "aging_60": Decimal("0"),
                    "aging_90_plus": Decimal("0"),
                    "risk_level": "低风险",
                    "review_status": "已通过",
                    "follow_up_status": "已完成",
                    "summary_date": invoice.posting_date,
                    "owner": str(invoice.created_by),
                    "remark": "FastAPI 本地采购发票与供应商付款汇总",
                },
            )
            row["current_payable"] = self._to_decimal(row["current_payable"]) + self._to_decimal(invoice.grand_total)
            row["ending_payable"] = self._to_decimal(row["ending_payable"]) + self._to_decimal(invoice.outstanding_amount)
            row["summary_date"] = max(row["summary_date"], invoice.posting_date)  # type: ignore[arg-type]
            if self._to_decimal(invoice.outstanding_amount) > Decimal("0"):
                bucket = self._aging_bucket(due_date=invoice.due_date or invoice.posting_date, as_of=to_date)
                row[bucket] = self._to_decimal(row[bucket]) + self._to_decimal(invoice.outstanding_amount)

        if not grouped:
            return []

        payment_query = self.session.query(LyMaterialPurchasePayment).filter(
            LyMaterialPurchasePayment.status == "submitted",
            LyMaterialPurchasePayment.docstatus == 1,
        )
        if readable_companies is not None:
            payment_query = payment_query.filter(LyMaterialPurchasePayment.company.in_(sorted(readable_companies)))
        if readable_suppliers is not None:
            payment_query = payment_query.filter(LyMaterialPurchasePayment.supplier_name.in_(sorted(readable_suppliers)))
        if from_date:
            payment_query = payment_query.filter(LyMaterialPurchasePayment.posting_date >= from_date)
        if to_date:
            payment_query = payment_query.filter(LyMaterialPurchasePayment.posting_date <= to_date)
        for payment in payment_query.all():
            row = grouped.get((str(payment.company), str(payment.supplier_name)))
            if row is None:
                continue
            row["paid_amount"] = self._to_decimal(row["paid_amount"]) + self._to_decimal(payment.paid_amount)
            row["summary_date"] = max(row["summary_date"], payment.posting_date)  # type: ignore[arg-type]

        for row in grouped.values():
            self._apply_financial_summary_status(row=row, ending_key="ending_payable")
        return list(grouped.values())

    def _build_factory_payable_summary_rows(
        self,
        *,
        from_date: date | None,
        to_date: date | None,
        readable_companies: set[str] | None,
        readable_suppliers: set[str] | None,
    ) -> list[dict[str, object]]:
        query = self.session.query(LyFactoryStatement).filter(
            LyFactoryStatement.statement_status.in_(
                [self._STATUS_CONFIRMED, self._STATUS_PAYABLE_DRAFT_CREATED]
            )
        )
        if readable_companies is not None:
            if not readable_companies:
                return []
            query = query.filter(LyFactoryStatement.company.in_(sorted(readable_companies)))
        if readable_suppliers is not None:
            if not readable_suppliers:
                return []
            query = query.filter(LyFactoryStatement.supplier.in_(sorted(readable_suppliers)))
        if from_date:
            query = query.filter(LyFactoryStatement.to_date >= from_date)
        if to_date:
            query = query.filter(LyFactoryStatement.to_date <= to_date)

        statements = query.order_by(LyFactoryStatement.to_date.desc(), LyFactoryStatement.id.desc()).all()
        grouped: dict[tuple[str, str], dict[str, object]] = {}
        statement_ids: list[int] = []
        for statement in statements:
            company = str(statement.company)
            supplier = str(statement.supplier)
            key = (company, supplier)
            statement_ids.append(int(statement.id))
            row = grouped.setdefault(
                key,
                {
                    "summary_no": f"FPS-{self._stable_code(company)}-{self._stable_code(supplier)}",
                    "statement_no": str(statement.statement_no),
                    "company": company,
                    "supplier": supplier,
                    "factory_name": supplier,
                    "factory_code": supplier,
                    "currency": "CNY",
                    "opening_payable": Decimal("0"),
                    "current_payable": Decimal("0"),
                    "paid_amount": Decimal("0"),
                    "ending_payable": Decimal("0"),
                    "aging_30": Decimal("0"),
                    "aging_60": Decimal("0"),
                    "aging_90_plus": Decimal("0"),
                    "risk_level": "低风险",
                    "review_status": "已通过",
                    "summary_date": statement.to_date,
                    "owner": str(statement.created_by),
                    "remark": "FastAPI 本地加工厂对账单与付款汇总",
                },
            )
            row["current_payable"] = self._to_decimal(row["current_payable"]) + self._to_decimal(statement.net_amount)
            row["summary_date"] = max(row["summary_date"], statement.to_date)  # type: ignore[arg-type]

        if not grouped:
            return []

        paid_by_statement = self._fetch_paid_amount_map(statement_ids=statement_ids)
        for statement in statements:
            row = grouped[(str(statement.company), str(statement.supplier))]
            paid = paid_by_statement.get(int(statement.id), Decimal("0"))
            outstanding = self._compute_outstanding_amount(net_amount=self._to_decimal(statement.net_amount), paid_amount=paid)
            row["paid_amount"] = self._to_decimal(row["paid_amount"]) + paid
            row["ending_payable"] = self._to_decimal(row["ending_payable"]) + outstanding
            if outstanding > Decimal("0"):
                bucket = self._aging_bucket(due_date=statement.to_date, as_of=to_date)
                row[bucket] = self._to_decimal(row[bucket]) + outstanding

        for row in grouped.values():
            self._apply_financial_summary_status(row=row, ending_key="ending_payable")
        return list(grouped.values())

    @staticmethod
    def _stable_code(value: object) -> str:
        raw = str(value or "").strip() or "UNKNOWN"
        normalized = "".join(ch if ch.isalnum() else "-" for ch in raw.upper())
        normalized = "-".join(part for part in normalized.split("-") if part)
        return normalized[:40] or "UNKNOWN"

    @staticmethod
    def _aging_bucket(*, due_date: date, as_of: date | None) -> str:
        reference_date = as_of or date.today()
        days = max((reference_date - due_date).days, 0)
        if days <= 30:
            return "aging_30"
        if days <= 60:
            return "aging_60"
        return "aging_90_plus"

    def _apply_financial_summary_status(self, *, row: dict[str, object], ending_key: str) -> None:
        ending = self._to_decimal(row[ending_key])
        if ending <= Decimal("0"):
            row["risk_level"] = "低风险"
            row["review_status"] = "已通过"
            if "follow_up_status" in row:
                row["follow_up_status"] = "已完成"
            return

        aging_90_plus = self._to_decimal(row["aging_90_plus"])
        aging_60 = self._to_decimal(row["aging_60"])
        if aging_90_plus > Decimal("0"):
            row["risk_level"] = "高风险"
            row["review_status"] = "待复核"
            if "follow_up_status" in row:
                row["follow_up_status"] = "待跟进"
        elif aging_60 > Decimal("0"):
            row["risk_level"] = "中风险"
            row["review_status"] = "复核中"
            if "follow_up_status" in row:
                row["follow_up_status"] = "跟进中"
        else:
            row["risk_level"] = "低风险"
            row["review_status"] = "待复核"
            if "follow_up_status" in row:
                row["follow_up_status"] = "待跟进"

    def _to_list_item(
        self,
        *,
        row: LyFactoryStatement,
        latest_payable: LyFactoryStatementPayableOutbox | None,
        paid_amount: Decimal,
    ) -> FactoryStatementListItem:
        net_amount = self._to_decimal(row.net_amount)
        outstanding_amount = self._compute_outstanding_amount(net_amount=net_amount, paid_amount=paid_amount)
        return FactoryStatementListItem(
            id=int(row.id),
            statement_no=str(row.statement_no),
            company=str(row.company),
            supplier=str(row.supplier),
            from_date=row.from_date,
            to_date=row.to_date,
            source_count=int(row.source_count or 0),
            gross_amount=self._to_decimal(row.gross_amount),
            deduction_amount=self._to_decimal(row.deduction_amount),
            net_amount=net_amount,
            paid_amount=paid_amount,
            outstanding_amount=outstanding_amount,
            payment_status=self._payment_status(net_amount=net_amount, paid_amount=paid_amount),
            rejected_rate=self._to_decimal(row.rejected_rate),
            statement_status=str(row.statement_status),
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
            created_by=str(row.created_by),
            created_at=row.created_at,
        )

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

    def _to_purchase_invoice_item(
        self,
        *,
        outbox: LyFactoryStatementPayableOutbox,
        statement: LyFactoryStatement,
        paid_amount: Decimal,
    ) -> FactoryStatementPurchaseInvoiceItem:
        grand_total = self._to_decimal(statement.net_amount)
        paid = self._to_decimal(paid_amount)
        outstanding = self._compute_outstanding_amount(net_amount=grand_total, paid_amount=paid)
        payload = outbox.payload_json if isinstance(outbox.payload_json, dict) else {}
        return FactoryStatementPurchaseInvoiceItem(
            purchase_invoice_name=(
                self._normalize_text(outbox.erpnext_purchase_invoice) or f"LY-FS-PAYABLE-{int(outbox.id)}"
            ),
            company=str(outbox.company),
            supplier=str(outbox.supplier),
            supplier_name=str(outbox.supplier),
            currency=str(payload.get("currency") or "CNY"),
            grand_total=grand_total,
            paid_amount=paid,
            outstanding_amount=outstanding,
            status=self._purchase_invoice_readback_status(
                outbox=outbox,
                grand_total=grand_total,
                paid_amount=paid,
            ),
            posting_date=self._purchase_invoice_posting_date(outbox=outbox, statement=statement),
        )

    def _purchase_invoice_readback_status(
        self,
        *,
        outbox: LyFactoryStatementPayableOutbox,
        grand_total: Decimal,
        paid_amount: Decimal,
    ) -> str:
        outbox_status = self._normalize_text(outbox.status) or "unknown"
        if outbox_status in {"pending", "processing", "failed", "dead"}:
            return f"outbox_{outbox_status}"
        erp_status = self._normalize_text(outbox.erpnext_status)
        if erp_status:
            return erp_status
        return self._payment_status(net_amount=grand_total, paid_amount=paid_amount)

    @staticmethod
    def _purchase_invoice_posting_date(
        *,
        outbox: LyFactoryStatementPayableOutbox,
        statement: LyFactoryStatement,
    ) -> date:
        payload = outbox.payload_json if isinstance(outbox.payload_json, dict) else {}
        raw_posting_date = payload.get("posting_date")
        if isinstance(raw_posting_date, date):
            return raw_posting_date
        if isinstance(raw_posting_date, str):
            try:
                return date.fromisoformat(raw_posting_date)
            except ValueError:
                pass
        return statement.to_date

    def _to_payment_data(self, row: LyFactoryStatementPayment) -> FactoryStatementPaymentData:
        return FactoryStatementPaymentData(
            id=int(row.id),
            company=str(row.company),
            payment_entry=str(row.payment_entry),
            statement_id=int(row.statement_id),
            statement_no=str(row.statement_no),
            supplier=str(row.supplier),
            posting_date=row.posting_date,
            paid_amount=self._to_decimal(row.paid_amount),
            allocated_amount=self._to_decimal(row.allocated_amount),
            outstanding_before=self._to_decimal(row.outstanding_before),
            outstanding_after=self._to_decimal(row.outstanding_after),
            mode_of_payment=str(row.mode_of_payment),
            reference_no=self._normalize_text(row.reference_no),
            reference_date=row.reference_date,
            status=str(row.status),
            docstatus=int(row.docstatus or 0),
            source_ref=str(row.source_ref),
            idempotency_key=str(row.idempotency_key),
            scenario_tag=self._normalize_text(row.scenario_tag),
            created_by=str(row.created_by),
            created_at=row.created_at,
        )
