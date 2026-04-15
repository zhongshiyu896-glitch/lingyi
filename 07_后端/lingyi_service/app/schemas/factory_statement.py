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


class FactoryStatementCancelRequest(BaseModel):
    """Cancel statement request."""

    idempotency_key: str = Field(..., min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=200)


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
