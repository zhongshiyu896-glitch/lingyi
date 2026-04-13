"""Pydantic schemas for workshop module (TASK-003)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""

    code: str
    message: str
    data: T


class WorkshopTicketRegisterRequest(BaseModel):
    """Register workshop ticket request."""

    ticket_key: str = Field(..., min_length=1, max_length=128)
    job_card: str = Field(..., min_length=1, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    employee: str = Field(..., min_length=1, max_length=140)
    process_name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(default=None, max_length=64)
    size: Optional[str] = Field(default=None, max_length=64)
    qty: Decimal
    work_date: date
    source: str = Field(default="manual", min_length=1, max_length=32)
    source_ref: Optional[str] = Field(default=None, max_length=140)


class WorkshopTicketReversalRequest(BaseModel):
    """Reverse workshop ticket request."""

    ticket_key: str = Field(..., min_length=1, max_length=128)
    job_card: str = Field(..., min_length=1, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    employee: str = Field(..., min_length=1, max_length=140)
    process_name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(default=None, max_length=64)
    size: Optional[str] = Field(default=None, max_length=64)
    qty: Decimal
    work_date: date
    original_ticket_id: Optional[int] = None
    reason: str = Field(..., min_length=1, max_length=255)


class WorkshopTicketBatchItem(BaseModel):
    """Batch ticket row."""

    operation_type: str = Field(default="register", max_length=16)
    ticket_key: str = Field(..., min_length=1, max_length=128)
    job_card: str = Field(..., min_length=1, max_length=140)
    item_code: Optional[str] = Field(default=None, max_length=140)
    employee: str = Field(..., min_length=1, max_length=140)
    process_name: str = Field(..., min_length=1, max_length=100)
    color: Optional[str] = Field(default=None, max_length=64)
    size: Optional[str] = Field(default=None, max_length=64)
    qty: Decimal
    work_date: date
    source: str = Field(default="import", min_length=1, max_length=32)
    source_ref: Optional[str] = Field(default=None, max_length=140)
    original_ticket_id: Optional[int] = None
    reason: Optional[str] = Field(default=None, max_length=255)


class WorkshopTicketBatchRequest(BaseModel):
    """Batch import request."""

    tickets: List[WorkshopTicketBatchItem] = Field(..., min_length=1, max_length=500)


class WorkshopTicketData(BaseModel):
    """Ticket operation result."""

    ticket_no: str
    ticket_id: int
    unit_wage: Decimal
    wage_amount: Decimal
    sync_status: str
    sync_outbox_id: int | None = None


class WorkshopTicketReversalData(BaseModel):
    """Ticket reversal result."""

    ticket_no: str
    ticket_id: int
    net_qty: Decimal
    wage_amount: Decimal
    sync_status: str
    sync_outbox_id: int | None = None


class WorkshopBatchFailedItem(BaseModel):
    """Failed row in batch import."""

    row_index: int
    index: int | None = None
    code: str
    error_code: str | None = None
    message: str
    ticket_key: str


class WorkshopBatchResult(BaseModel):
    """Batch import response payload."""

    success_count: int
    failed_count: int
    success_items: list[WorkshopTicketData]
    failed_items: list[WorkshopBatchFailedItem]


class WorkshopTicketRow(BaseModel):
    """Ticket list row."""

    id: int
    ticket_no: str
    ticket_key: str
    job_card: str
    work_order: Optional[str]
    bom_id: Optional[int]
    item_code: str
    employee: str
    process_name: str
    color: Optional[str]
    size: Optional[str]
    operation_type: str
    qty: Decimal
    unit_wage: Decimal
    wage_amount: Decimal
    work_date: date
    source: str
    source_ref: Optional[str]
    sync_status: str
    created_by: str
    created_at: datetime


class WorkshopTicketListData(BaseModel):
    """Ticket list response."""

    items: list[WorkshopTicketRow]
    total: int
    page: int
    page_size: int


class WorkshopDailyWageRow(BaseModel):
    """Daily wage row."""

    employee: str
    work_date: date
    process_name: str
    item_code: Optional[str]
    register_qty: Decimal
    reversal_qty: Decimal
    net_qty: Decimal
    wage_amount: Decimal


class WorkshopDailyWageListData(BaseModel):
    """Daily wage list response."""

    items: list[WorkshopDailyWageRow]
    total: int
    total_amount: Decimal
    page: int
    page_size: int


class WorkshopJobCardSummaryData(BaseModel):
    """Job Card summary response."""

    job_card: str
    register_qty: Decimal
    reversal_qty: Decimal
    net_qty: Decimal
    local_completed_qty: Decimal
    sync_status: str
    outbox_status: str
    last_sync_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


class WorkshopJobCardSyncData(BaseModel):
    """Manual sync response."""

    job_card: str
    local_completed_qty: Decimal
    sync_status: str
    sync_outbox_id: int | None = None


class WorkshopJobCardSyncRunOnceData(BaseModel):
    """Internal worker run-once response."""

    dry_run: bool = False
    forbidden_diagnostics_enabled: bool = Field(
        default=False,
        description="本次 run-once 是否执行了越权诊断扫描。",
    )
    would_process_count: int = 0
    processed_count: int
    succeeded_count: int
    failed_count: int
    forbidden_diagnostic_count: int = Field(
        default=0,
        description="越权诊断统计主字段（canonical）。仅在 diagnostics 模式下可能大于 0。",
    )
    skipped_forbidden_count: int = Field(
        default=0,
        description=(
            "历史兼容字段，仅 diagnostics-only，等同 forbidden_diagnostic_count。"
            " 不代表主处理跳过数。"
        ),
        deprecated=True,
        json_schema_extra={"deprecated": True},
    )
    blocked_scope_count: int = 0
    dead_count: int
    # Backward-compatible fields kept for existing callers.
    would_process: int = 0
    processed: int
    succeeded: int
    failed: int
    forbidden_diagnostic: int = Field(
        default=0,
        description="历史兼容短字段，等同 forbidden_diagnostic_count。",
    )
    skipped_forbidden: int = Field(
        default=0,
        description=(
            "历史兼容字段，仅 diagnostics-only，等同 forbidden_diagnostic_count。"
            " 不代表主处理跳过数。"
        ),
        deprecated=True,
        json_schema_extra={"deprecated": True},
    )
    blocked_scope: int = 0
    dead: int


class OperationWageRateCreateRequest(BaseModel):
    """Create wage rate request."""

    item_code: Optional[str] = Field(default=None, max_length=140)
    company: Optional[str] = Field(default=None, max_length=140)
    process_name: str = Field(..., min_length=1, max_length=100)
    wage_rate: Decimal = Field(..., ge=0)
    effective_from: date
    effective_to: Optional[date] = None


class OperationWageRateDeactivateRequest(BaseModel):
    """Deactivate wage rate request."""

    reason: str = Field(..., min_length=1, max_length=255)


class OperationWageRateRow(BaseModel):
    """Wage rate list row."""

    id: int
    item_code: Optional[str]
    company: Optional[str]
    is_global: bool
    process_name: str
    wage_rate: Decimal
    effective_from: date
    effective_to: Optional[date]
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class OperationWageRateListData(BaseModel):
    """Wage rate list response."""

    items: list[OperationWageRateRow]
    total: int
    page: int
    page_size: int


class OperationWageRateCreateData(BaseModel):
    """Create wage rate response."""

    id: int
    item_code: Optional[str] = None
    company: Optional[str] = None
    status: str


class OperationWageRateDeactivateData(BaseModel):
    """Deactivate wage rate response."""

    id: int
    status: str


class WorkshopTicketListQuery(BaseModel):
    """Ticket list query params."""

    employee: Optional[str] = None
    job_card: Optional[str] = None
    item_code: Optional[str] = None
    process_name: Optional[str] = None
    operation_type: Optional[str] = None
    work_date: Optional[date] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class WorkshopDailyWageQuery(BaseModel):
    """Daily wage list query params."""

    employee: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    process_name: Optional[str] = None
    item_code: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class OperationWageRateQuery(BaseModel):
    """Wage rate list query params."""

    item_code: Optional[str] = None
    company: Optional[str] = None
    is_global: Optional[bool] = None
    process_name: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)
