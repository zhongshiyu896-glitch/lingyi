"""Pydantic schemas for FastAPI-native finance approval tasks."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

FinanceApprovalSourceType = Literal["purchase_invoice", "purchase_payment", "factory_statement_payment"]
FinanceApprovalStatus = Literal["pending", "approved", "rejected", "cancelled"]


class FinanceApprovalTaskCreateRequest(BaseModel):
    """Create an approval task from an existing payable/payment source."""

    operation: Literal["create_task"] = "create_task"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    source_type: FinanceApprovalSourceType
    source_id: int = Field(..., gt=0)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    scenario_tag: str | None = Field(default=None, max_length=64)


class FinanceApprovalDecisionRequest(BaseModel):
    """Approve or reject a finance approval task."""

    operation: Literal["approve_task", "reject_task"]
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    reason: str | None = Field(default=None, max_length=500)


class FinanceApprovalTaskItem(BaseModel):
    """Approval task row returned to the frontend."""

    id: int
    company: str
    approval_no: str
    source_type: FinanceApprovalSourceType
    source_id: str
    source_no: str
    source_status: str
    partner_name: str
    amount: Decimal
    currency: str
    status: FinanceApprovalStatus
    scenario_tag: str | None = None
    submitted_by: str
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    reject_reason: str | None = None
    created_by: str
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None


class FinanceApprovalTaskListData(BaseModel):
    """Paginated approval task rows."""

    items: list[FinanceApprovalTaskItem]
    total: int
    page: int
    page_size: int


class FinanceApprovalTaskCreateData(FinanceApprovalTaskItem):
    """Create response."""


class FinanceApprovalDecisionData(FinanceApprovalTaskItem):
    """Approve/reject response."""
