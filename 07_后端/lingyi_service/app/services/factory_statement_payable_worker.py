"""Internal worker for factory statement payable outbox (TASK-006D)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from decimal import InvalidOperation
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.error_codes import FACTORY_STATEMENT_DATABASE_READ_FAILED
from app.core.error_codes import FACTORY_STATEMENT_DATABASE_WRITE_FAILED
from app.core.error_codes import FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS
from app.core.error_codes import FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE
from app.core.error_codes import FACTORY_STATEMENT_INVALID_STATUS
from app.core.error_codes import FACTORY_STATEMENT_INTERNAL_ERROR
from app.core.exceptions import AppException
from app.core.exceptions import BusinessException
from app.core.exceptions import ERPNextServiceAccountForbiddenError
from app.core.exceptions import ERPNextServiceUnavailableError
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementLog
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceLookup
from app.services.factory_statement_payable_outbox_service import FactoryStatementPayableOutboxClaim
from app.services.factory_statement_payable_outbox_service import FactoryStatementPayableOutboxService


@dataclass(frozen=True)
class FactoryStatementPayableWorkerRunResult:
    """Run-once result summary."""

    dry_run: bool
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int


class FactoryStatementPayableWorker:
    """Consume payable outbox rows and create ERPNext Purchase Invoice drafts."""

    _STATUS_CONFIRMED = "confirmed"
    _STATUS_PAYABLE_DRAFT_CREATED = "payable_draft_created"

    def __init__(
        self,
        *,
        session: Session,
        adapter: ERPNextPurchaseInvoiceAdapter,
    ):
        self.session = session
        self.adapter = adapter
        self.outbox_service = FactoryStatementPayableOutboxService(session=session)

    def run_once(
        self,
        *,
        batch_size: int,
        worker_id: str,
        dry_run: bool = False,
        allowed_companies: set[str] | None = None,
        allowed_suppliers: set[str] | None = None,
    ) -> FactoryStatementPayableWorkerRunResult:
        if dry_run:
            due = self.outbox_service.list_due_ids(
                batch_size=batch_size,
                allowed_companies=allowed_companies,
                allowed_suppliers=allowed_suppliers,
            )
            return FactoryStatementPayableWorkerRunResult(
                dry_run=True,
                processed_count=len(due),
                succeeded_count=0,
                failed_count=0,
                dead_count=0,
            )

        claims = self.outbox_service.claim_due(
            batch_size=batch_size,
            worker_id=worker_id,
            allowed_companies=allowed_companies,
            allowed_suppliers=allowed_suppliers,
        )
        if claims:
            self._commit_or_raise_write_error()

        succeeded = 0
        failed = 0
        dead = 0

        for claim in claims:
            try:
                self._validate_statement_before_erp(claim=claim)
                invoice = self._resolve_or_create_purchase_invoice(claim=claim)
                self._ensure_docstatus_zero(invoice=invoice)
                self._persist_success(claim=claim, invoice=invoice)
                succeeded += 1
            except (ERPNextServiceUnavailableError, ERPNextServiceAccountForbiddenError) as exc:
                is_dead = self._persist_failure(
                    claim=claim,
                    error_code=FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE,
                    error_message=str(getattr(exc, "message", None) or str(exc) or "ERPNext 服务不可用"),
                )
                failed += 1
                if is_dead:
                    dead += 1
            except AppException as exc:
                is_dead = self._persist_failure(
                    claim=claim,
                    error_code=exc.code,
                    error_message=exc.message,
                )
                failed += 1
                if is_dead:
                    dead += 1
            except Exception:
                is_dead = self._persist_failure(
                    claim=claim,
                    error_code=FACTORY_STATEMENT_INTERNAL_ERROR,
                    error_message="应付草稿同步失败",
                )
                failed += 1
                if is_dead:
                    dead += 1

        return FactoryStatementPayableWorkerRunResult(
            dry_run=False,
            processed_count=len(claims),
            succeeded_count=succeeded,
            failed_count=failed,
            dead_count=dead,
        )

    def _validate_statement_before_erp(self, *, claim: FactoryStatementPayableOutboxClaim) -> None:
        statement = self._find_statement_or_none(statement_id=claim.statement_id)
        if statement is None:
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)
        if int(statement.id) != int(claim.statement_id):
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)

        if str(statement.statement_status) != self._STATUS_CONFIRMED:
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)

        if self._has_other_succeeded_outbox(statement_id=claim.statement_id, exclude_outbox_id=claim.outbox_id):
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)

        payload_amount = self._payload_amount(claim.payload_json)
        if payload_amount is None:
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)
        statement_amount = self._decimal_or_zero(statement.net_amount)
        if statement_amount != payload_amount:
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)

    def _resolve_or_create_purchase_invoice(
        self,
        *,
        claim: FactoryStatementPayableOutboxClaim,
    ) -> ERPNextPurchaseInvoiceLookup:
        existing = self.adapter.find_purchase_invoice_by_event_key(event_key=claim.event_key)
        if existing is not None:
            return existing
        return self.adapter.create_purchase_invoice_draft(payload_json=dict(claim.payload_json or {}))

    @staticmethod
    def _ensure_docstatus_zero(*, invoice: ERPNextPurchaseInvoiceLookup) -> None:
        if int(invoice.docstatus) != 0:
            raise BusinessException(code=FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS)

    def _persist_success(
        self,
        *,
        claim: FactoryStatementPayableOutboxClaim,
        invoice: ERPNextPurchaseInvoiceLookup,
    ) -> None:
        self.outbox_service.mark_succeeded(
            outbox_id=claim.outbox_id,
            purchase_invoice_name=invoice.name,
            erpnext_docstatus=int(invoice.docstatus),
            erpnext_status=invoice.status,
        )

        statement = self._must_get_statement(statement_id=claim.statement_id)
        before_status = str(statement.statement_status)
        if before_status != self._STATUS_CONFIRMED:
            raise BusinessException(code=FACTORY_STATEMENT_INVALID_STATUS)

        statement.statement_status = self._STATUS_PAYABLE_DRAFT_CREATED
        self.session.add(
            LyFactoryStatementLog(
                statement_id=int(statement.id),
                company=str(statement.company),
                supplier=str(statement.supplier),
                from_status=before_status,
                to_status=self._STATUS_PAYABLE_DRAFT_CREATED,
                action="factory_statement:payable_draft_worker",
                operator="system_worker",
                request_id=None,
                remark=f"outbox={claim.outbox_id};pi={invoice.name}",
            )
        )

        self._commit_or_raise_write_error()

    def _persist_failure(
        self,
        *,
        claim: FactoryStatementPayableOutboxClaim,
        error_code: str,
        error_message: str,
    ) -> bool:
        row = self.outbox_service.mark_failed(
            outbox_id=claim.outbox_id,
            error_code=error_code,
            error_message=error_message,
        )
        statement = self._find_statement_or_none(statement_id=claim.statement_id)
        if statement is not None:
            status_text = str(statement.statement_status)
            self.session.add(
                LyFactoryStatementLog(
                    statement_id=int(statement.id),
                    company=str(statement.company),
                    supplier=str(statement.supplier),
                    from_status=status_text,
                    to_status=status_text,
                    action="factory_statement:payable_draft_worker",
                    operator="system_worker",
                    request_id=None,
                    remark=f"outbox={claim.outbox_id};error={error_code}",
                )
            )
        self._commit_or_raise_write_error()
        return str(row.status) == FactoryStatementPayableOutboxService.STATUS_DEAD

    def _find_statement_or_none(self, *, statement_id: int) -> LyFactoryStatement | None:
        try:
            return (
                self.session.query(LyFactoryStatement)
                .filter(LyFactoryStatement.id == int(statement_id))
                .one_or_none()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc

    def _must_get_statement(self, *, statement_id: int) -> LyFactoryStatement:
        row = self._find_statement_or_none(statement_id=statement_id)
        if row is None:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED)
        return row

    def _commit_or_raise_write_error(self) -> None:
        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc

    def _has_other_succeeded_outbox(
        self,
        *,
        statement_id: int,
        exclude_outbox_id: int,
    ) -> bool:
        try:
            row = (
                self.session.query(LyFactoryStatementPayableOutbox.id)
                .filter(
                    LyFactoryStatementPayableOutbox.statement_id == int(statement_id),
                    LyFactoryStatementPayableOutbox.status == FactoryStatementPayableOutboxService.STATUS_SUCCEEDED,
                    LyFactoryStatementPayableOutbox.id != int(exclude_outbox_id),
                )
                .first()
            )
        except SQLAlchemyError as exc:
            raise BusinessException(code=FACTORY_STATEMENT_DATABASE_READ_FAILED) from exc
        return row is not None

    @staticmethod
    def _payload_amount(payload_json: dict[str, Any]) -> Decimal | None:
        raw = payload_json.get("amount")
        if raw is None:
            return None
        try:
            return FactoryStatementPayableWorker._decimal_or_zero(raw)
        except (ArithmeticError, InvalidOperation, ValueError):
            return None

    @staticmethod
    def _decimal_or_zero(value: Any) -> Decimal:
        quant = Decimal("0.000001")
        return Decimal(str(value if value is not None else "0")).quantize(quant)
