"""Pydantic schemas for factory statement APIs (TASK-006B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from pydantic import Field


class FactoryStatementCreateRequest(BaseModel):
    """Create draft statement request."""

    company: str = Field(..., min_length=1, max_length=140)
    supplier: str = Field(..., min_length=1, max_length=140)
    from_date: date
    to_date: date
    idempotency_key: str = Field(..., min_length=1, max_length=128)
    scenario_tag: str | None = Field(default=None, max_length=64)


class FactoryStatementCreateData(BaseModel):
    """Create draft statement response."""

    statement_id: int
    statement_no: str
    statement_status: str
    company: str
    supplier: str
    from_date: date
    to_date: date
    source_count: int
    inspected_qty: Decimal
    rejected_qty: Decimal
    accepted_qty: Decimal
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    rejected_rate: Decimal
    idempotency_key: str
    request_hash: str
    idempotent_replay: bool = False


class FactoryStatementListItem(BaseModel):
    """Statement list row."""

    id: int
    statement_no: str
    company: str
    supplier: str
    from_date: date
    to_date: date
    source_count: int
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    rejected_rate: Decimal
    statement_status: str
    payable_outbox_id: int | None = None
    payable_outbox_status: str | None = None
    purchase_invoice_name: str | None = None
    payable_error_code: str | None = None
    payable_error_message: str | None = None
    created_by: str
    created_at: datetime


class FactoryStatementListData(BaseModel):
    """Statement list response payload."""

    items: list[FactoryStatementListItem]
    total: int
    page: int
    page_size: int


class FactoryStatementPurchaseInvoiceItem(BaseModel):
    """Read-only purchase invoice/payable projection."""

    purchase_invoice_name: str
    company: str
    supplier: str
    supplier_name: str
    currency: str
    grand_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: str
    posting_date: date


class FactoryStatementPurchaseInvoiceListData(BaseModel):
    """Paginated purchase invoice/payable response."""

    items: list[FactoryStatementPurchaseInvoiceItem]
    total: int
    page: int
    page_size: int


class FactoryStatementExpenseReimbursementPaymentItem(BaseModel):
    """Read-only expense reimbursement payment row."""

    payment_no: str
    reimbursement_no: str
    statement_no: str
    company: str
    supplier: str
    expense_type: str
    payable_amount: Decimal
    paid_amount: Decimal
    pending_amount: Decimal
    payment_status: str
    review_status: str
    payment_date: date
    payable_account: str
    cost_center: str
    owner: str
    ref_no: str


class FactoryStatementExpenseReimbursementPaymentData(BaseModel):
    """Read-only expense reimbursement payment response."""

    items: list[FactoryStatementExpenseReimbursementPaymentItem]
    total: int
    page: int
    page_size: int


class FactoryStatementBankDepositItem(BaseModel):
    """Read-only bank deposit row."""

    deposit_no: str
    statement_no: str
    company: str
    bank_name: str
    account_name: str
    account_no: str
    currency: str
    deposit_amount: Decimal
    confirmed_amount: Decimal
    pending_amount: Decimal
    deposit_status: str
    review_status: str
    deposit_date: date
    voucher_no: str
    owner: str
    remark: str


class FactoryStatementBankDepositData(BaseModel):
    """Read-only bank deposit response."""

    items: list[FactoryStatementBankDepositItem]
    total: int
    page: int
    page_size: int


class FactoryStatementBankWithdrawalItem(BaseModel):
    """Read-only bank withdrawal row."""

    withdrawal_no: str
    statement_no: str
    company: str
    bank_name: str
    account_name: str
    account_no: str
    currency: str
    withdrawal_amount: Decimal
    transferred_amount: Decimal
    pending_amount: Decimal
    withdrawal_status: str
    review_status: str
    withdrawal_date: date
    voucher_no: str
    owner: str
    remark: str


class FactoryStatementBankWithdrawalData(BaseModel):
    """Read-only bank withdrawal response."""

    items: list[FactoryStatementBankWithdrawalItem]
    total: int
    page: int
    page_size: int


class FactoryStatementBankLedgerItem(BaseModel):
    """Read-only bank ledger row."""

    ledger_no: str
    statement_no: str
    company: str
    bank_name: str
    account_name: str
    account_no: str
    currency: str
    transaction_type: str
    debit_amount: Decimal
    credit_amount: Decimal
    balance_after: Decimal
    ledger_status: str
    review_status: str
    ledger_date: date
    voucher_no: str
    owner: str
    remark: str


class FactoryStatementBankLedgerData(BaseModel):
    """Read-only bank ledger response."""

    items: list[FactoryStatementBankLedgerItem]
    total: int
    page: int
    page_size: int


class FactoryStatementCustomerEvaluationItem(BaseModel):
    """Read-only customer evaluation row."""

    evaluation_no: str
    statement_no: str
    company: str
    customer_name: str
    customer_code: str
    assessor: str
    score: Decimal
    score_level: str
    review_status: str
    follow_up_status: str
    evaluation_date: date
    expiry_date: date
    owner: str
    remark: str


class FactoryStatementCustomerEvaluationData(BaseModel):
    """Read-only customer evaluation response."""

    items: list[FactoryStatementCustomerEvaluationItem]
    total: int
    page: int
    page_size: int


class FactoryStatementCustomerReconciliationItem(BaseModel):
    """Read-only customer reconciliation row."""

    reconciliation_no: str
    statement_no: str
    company: str
    customer_name: str
    customer_code: str
    currency: str
    receivable_amount: Decimal
    settled_amount: Decimal
    pending_amount: Decimal
    settlement_status: str
    review_status: str
    due_date: date
    reconciled_at: date
    owner: str
    remark: str


class FactoryStatementCustomerReconciliationData(BaseModel):
    """Read-only customer reconciliation response."""

    items: list[FactoryStatementCustomerReconciliationItem]
    total: int
    page: int
    page_size: int


class FactoryStatementCustomerUnpaidReportItem(BaseModel):
    """Read-only customer unpaid report row."""

    report_no: str
    statement_no: str
    company: str
    customer_name: str
    customer_code: str
    currency: str
    receivable_amount: Decimal
    received_amount: Decimal
    unpaid_amount: Decimal
    overdue_days: int
    collection_status: str
    review_status: str
    due_date: date
    last_collection_at: date
    owner: str
    remark: str


class FactoryStatementCustomerUnpaidReportData(BaseModel):
    """Read-only customer unpaid report response."""

    items: list[FactoryStatementCustomerUnpaidReportItem]
    total: int
    page: int
    page_size: int


class FactoryStatementCustomerReceivableSummaryItem(BaseModel):
    """Read-only customer receivable summary row."""

    summary_no: str
    statement_no: str
    company: str
    customer_name: str
    customer_code: str
    currency: str
    opening_receivable: Decimal
    current_receivable: Decimal
    received_amount: Decimal
    ending_receivable: Decimal
    aging_30: Decimal
    aging_60: Decimal
    aging_90_plus: Decimal
    risk_level: str
    review_status: str
    summary_date: date
    owner: str
    remark: str


class FactoryStatementCustomerReceivableSummaryData(BaseModel):
    """Read-only customer receivable summary response."""

    items: list[FactoryStatementCustomerReceivableSummaryItem]
    total: int
    page: int
    page_size: int


class FactoryStatementFactoryEvaluationItem(BaseModel):
    """Read-only factory evaluation row."""

    evaluation_no: str
    statement_no: str
    company: str
    supplier: str
    factory_name: str
    factory_code: str
    assessor: str
    score: Decimal
    score_level: str
    review_status: str
    follow_up_status: str
    evaluation_date: date
    expiry_date: date
    owner: str
    remark: str


class FactoryStatementFactoryEvaluationData(BaseModel):
    """Read-only factory evaluation response."""

    items: list[FactoryStatementFactoryEvaluationItem]
    total: int
    page: int
    page_size: int


class FactoryStatementFactoryReconciliationItem(BaseModel):
    """Read-only factory reconciliation row."""

    reconciliation_no: str
    statement_no: str
    company: str
    supplier: str
    factory_name: str
    factory_code: str
    currency: str
    reconciliation_amount: Decimal
    settled_amount: Decimal
    pending_amount: Decimal
    settlement_status: str
    review_status: str
    follow_up_status: str
    reconciled_at: date
    due_date: date
    owner: str
    remark: str


class FactoryStatementFactoryReconciliationData(BaseModel):
    """Read-only factory reconciliation response."""

    items: list[FactoryStatementFactoryReconciliationItem]
    total: int
    page: int
    page_size: int


class FactoryStatementFactoryPayableSummaryItem(BaseModel):
    """Read-only factory payable summary row."""

    summary_no: str
    statement_no: str
    company: str
    supplier: str
    factory_name: str
    factory_code: str
    currency: str
    opening_payable: Decimal
    current_payable: Decimal
    paid_amount: Decimal
    ending_payable: Decimal
    aging_30: Decimal
    aging_60: Decimal
    aging_90_plus: Decimal
    risk_level: str
    review_status: str
    summary_date: date
    owner: str
    remark: str


class FactoryStatementFactoryPayableSummaryData(BaseModel):
    """Read-only factory payable summary response."""

    items: list[FactoryStatementFactoryPayableSummaryItem]
    total: int
    page: int
    page_size: int


class FactoryStatementSupplierEvaluationItem(BaseModel):
    """Read-only supplier evaluation row."""

    evaluation_no: str
    statement_no: str
    company: str
    supplier: str
    supplier_code: str
    assessor: str
    score: Decimal
    score_level: str
    review_status: str
    follow_up_status: str
    evaluation_date: date
    expiry_date: date
    owner: str
    remark: str


class FactoryStatementSupplierEvaluationData(BaseModel):
    """Read-only supplier evaluation response."""

    items: list[FactoryStatementSupplierEvaluationItem]
    total: int
    page: int
    page_size: int


class FactoryStatementSupplierReconciliationItem(BaseModel):
    """Read-only supplier reconciliation row."""

    reconciliation_no: str
    statement_no: str
    company: str
    supplier: str
    supplier_code: str
    currency: str
    reconciliation_amount: Decimal
    settled_amount: Decimal
    pending_amount: Decimal
    settlement_status: str
    review_status: str
    follow_up_status: str
    reconciled_at: date
    due_date: date
    owner: str
    remark: str


class FactoryStatementSupplierReconciliationData(BaseModel):
    """Read-only supplier reconciliation response."""

    items: list[FactoryStatementSupplierReconciliationItem]
    total: int
    page: int
    page_size: int


class FactoryStatementSupplierPayableSummaryItem(BaseModel):
    """Read-only supplier payable summary row."""

    summary_no: str
    statement_no: str
    company: str
    supplier: str
    supplier_code: str
    currency: str
    opening_payable: Decimal
    current_payable: Decimal
    paid_amount: Decimal
    ending_payable: Decimal
    aging_30: Decimal
    aging_60: Decimal
    aging_90_plus: Decimal
    risk_level: str
    review_status: str
    follow_up_status: str
    summary_date: date
    owner: str
    remark: str


class FactoryStatementSupplierPayableSummaryData(BaseModel):
    """Read-only supplier payable summary response."""

    items: list[FactoryStatementSupplierPayableSummaryItem]
    total: int
    page: int
    page_size: int


class FactoryStatementItemData(BaseModel):
    """Statement detail item snapshot row."""

    id: int
    line_no: int
    inspection_id: int
    inspection_no: str | None = None
    subcontract_id: int
    subcontract_no: str
    company: str
    supplier: str
    item_code: str | None = None
    style_code: str | None = None
    inspected_at: datetime | None = None
    inspected_qty: Decimal
    rejected_qty: Decimal
    accepted_qty: Decimal
    subcontract_rate: Decimal
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    rejected_rate: Decimal


class FactoryStatementLogData(BaseModel):
    """Statement operation log row."""

    action: str
    operator: str
    operated_at: datetime
    remark: str | None = None
    from_status: str | None = None
    to_status: str | None = None


class FactoryStatementPayableOutboxData(BaseModel):
    """Statement payable outbox snapshot row."""

    id: int
    status: str
    erpnext_purchase_invoice: str | None = None
    erpnext_docstatus: int | None = None
    erpnext_status: str | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class FactoryStatementDetailData(BaseModel):
    """Statement detail payload."""

    statement_id: int
    statement_no: str
    statement_status: str
    company: str
    supplier: str
    from_date: date
    to_date: date
    source_count: int
    inspected_qty: Decimal
    rejected_qty: Decimal
    accepted_qty: Decimal
    gross_amount: Decimal
    deduction_amount: Decimal
    net_amount: Decimal
    rejected_rate: Decimal
    idempotency_key: str
    created_by: str
    created_at: datetime
    payable_outbox_id: int | None = None
    payable_outbox_status: str | None = None
    purchase_invoice_name: str | None = None
    payable_error_code: str | None = None
    payable_error_message: str | None = None
    items: list[FactoryStatementItemData]
    logs: list[FactoryStatementLogData] = Field(default_factory=list)
    payable_outboxes: list[FactoryStatementPayableOutboxData] = Field(default_factory=list)


class FactoryStatementConfirmRequest(BaseModel):
    """Confirm statement request."""

    idempotency_key: str = Field(..., min_length=1, max_length=128)
    remark: str | None = Field(default=None, max_length=200)
    scenario_tag: str | None = Field(default=None, max_length=64)
    company: str | None = Field(default=None, max_length=140)
    supplier: str | None = Field(default=None, max_length=140)
    statement_no: str | None = Field(default=None, max_length=140)


class FactoryStatementCancelRequest(BaseModel):
    """Cancel statement request."""

    idempotency_key: str = Field(..., min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=200)
    scenario_tag: str | None = Field(default=None, max_length=64)
    company: str | None = Field(default=None, max_length=140)
    supplier: str | None = Field(default=None, max_length=140)
    statement_no: str | None = Field(default=None, max_length=140)


class FactoryStatementConfirmData(BaseModel):
    """Confirm statement response payload."""

    id: int
    statement_no: str
    status: str
    confirmed_by: str
    confirmed_at: datetime
    idempotent_replay: bool = False


class FactoryStatementCancelData(BaseModel):
    """Cancel statement response payload."""

    id: int
    statement_no: str
    status: str
    cancelled_by: str
    cancelled_at: datetime
    idempotent_replay: bool = False


class FactoryStatementPayableDraftRequest(BaseModel):
    """Create payable-draft outbox request."""

    idempotency_key: str = Field(..., min_length=1, max_length=128)
    scenario_tag: str | None = Field(default=None, max_length=64)
    company: str | None = Field(default=None, max_length=140)
    supplier: str | None = Field(default=None, max_length=140)
    statement_no: str | None = Field(default=None, max_length=140)
    source_type: str | None = Field(default=None, max_length=64)
    status_action: str | None = Field(default=None, max_length=64)
    source_ref: str | None = Field(default=None, max_length=140)
    payable_account: str = Field(..., min_length=1, max_length=140)
    cost_center: str = Field(..., min_length=1, max_length=140)
    posting_date: date
    remark: str | None = Field(default=None, max_length=200)


class FactoryStatementPayableDraftData(BaseModel):
    """Create payable-draft outbox response payload."""

    statement_id: int
    statement_no: str
    status: str
    payable_outbox_id: int
    payable_outbox_status: str
    purchase_invoice_name: str | None = None
    net_amount: Decimal
    idempotent_replay: bool = False


class FactoryStatementPayableWorkerRunOnceRequest(BaseModel):
    """Run-once payload for payable worker."""

    batch_size: int = Field(default=20, ge=1, le=200)
    dry_run: bool = False


class FactoryStatementPayableWorkerRunOnceData(BaseModel):
    """Run-once result summary for payable worker."""

    dry_run: bool
    processed_count: int
    succeeded_count: int
    failed_count: int
    dead_count: int
