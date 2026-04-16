"""Pydantic schemas for quality management APIs (TASK-012B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class QualityInspectionItemInput(BaseModel):
    """Quality inspection item input row."""

    item_code: str = Field(..., min_length=1, max_length=140)
    sample_qty: Decimal = Field(default=Decimal("0"), ge=0)
    accepted_qty: Decimal = Field(default=Decimal("0"), ge=0)
    rejected_qty: Decimal = Field(default=Decimal("0"), ge=0)
    defect_qty: Decimal = Field(default=Decimal("0"), ge=0)
    result: str = Field(default="pending", max_length=32)
    remark: str | None = Field(default=None, max_length=255)


class QualityDefectInput(BaseModel):
    """Quality defect input row."""

    defect_code: str = Field(..., min_length=1, max_length=64)
    defect_name: str = Field(..., min_length=1, max_length=140)
    defect_qty: Decimal = Field(..., ge=0)
    severity: str = Field(default="minor", max_length=32)
    item_line_no: int | None = Field(default=None, ge=1)
    remark: str | None = Field(default=None, max_length=255)


class QualityInspectionCreateRequest(BaseModel):
    """Create draft quality inspection request."""

    company: str = Field(..., min_length=1, max_length=140)
    source_type: str = Field(..., min_length=1, max_length=64)
    source_id: str | None = Field(default=None, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)
    supplier: str | None = Field(default=None, max_length=140)
    warehouse: str | None = Field(default=None, max_length=140)
    work_order: str | None = Field(default=None, max_length=140)
    sales_order: str | None = Field(default=None, max_length=140)
    inspection_date: date
    inspected_qty: Decimal = Field(..., ge=0)
    accepted_qty: Decimal = Field(..., ge=0)
    rejected_qty: Decimal = Field(..., ge=0)
    defect_qty: Decimal = Field(default=Decimal("0"), ge=0)
    result: str = Field(default="pending", max_length=32)
    remark: str | None = Field(default=None, max_length=255)
    items: list[QualityInspectionItemInput] = Field(default_factory=list)
    defects: list[QualityDefectInput] = Field(default_factory=list)


class QualityInspectionUpdateRequest(BaseModel):
    """Update draft quality inspection request."""

    supplier: str | None = Field(default=None, max_length=140)
    warehouse: str | None = Field(default=None, max_length=140)
    work_order: str | None = Field(default=None, max_length=140)
    sales_order: str | None = Field(default=None, max_length=140)
    inspection_date: date | None = None
    inspected_qty: Decimal | None = Field(default=None, ge=0)
    accepted_qty: Decimal | None = Field(default=None, ge=0)
    rejected_qty: Decimal | None = Field(default=None, ge=0)
    defect_qty: Decimal | None = Field(default=None, ge=0)
    result: str | None = Field(default=None, max_length=32)
    remark: str | None = Field(default=None, max_length=255)
    items: list[QualityInspectionItemInput] | None = None
    defects: list[QualityDefectInput] | None = None


class QualityInspectionConfirmRequest(BaseModel):
    """Confirm quality inspection request."""

    remark: str | None = Field(default=None, max_length=200)


class QualityInspectionCancelRequest(BaseModel):
    """Cancel quality inspection request."""

    reason: str | None = Field(default=None, max_length=200)


class QualityInspectionItemData(BaseModel):
    """Quality inspection item response row."""

    id: int
    line_no: int
    item_code: str
    sample_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    defect_qty: Decimal
    result: str
    remark: str | None = None


class QualityDefectData(BaseModel):
    """Quality defect response row."""

    id: int
    item_id: int | None = None
    defect_code: str
    defect_name: str
    defect_qty: Decimal
    severity: str
    remark: str | None = None


class QualityOperationLogData(BaseModel):
    """Quality operation log response row."""

    action: str
    operator: str
    operated_at: datetime
    from_status: str | None = None
    to_status: str
    remark: str | None = None


class QualityInspectionListItem(BaseModel):
    """Quality inspection list row."""

    id: int
    inspection_no: str
    company: str
    source_type: str
    source_id: str | None = None
    item_code: str
    supplier: str | None = None
    warehouse: str | None = None
    inspection_date: date
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    defect_qty: Decimal
    defect_rate: Decimal
    rejected_rate: Decimal
    result: str
    status: str
    created_by: str
    created_at: datetime


class QualityInspectionListData(BaseModel):
    """Quality inspection list response payload."""

    items: list[QualityInspectionListItem]
    total: int
    page: int
    page_size: int


class QualityInspectionDetailData(QualityInspectionListItem):
    """Quality inspection detail payload."""

    work_order: str | None = None
    sales_order: str | None = None
    remark: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None
    cancelled_by: str | None = None
    cancelled_at: datetime | None = None
    source_snapshot: dict[str, Any] | None = None
    items: list[QualityInspectionItemData] = Field(default_factory=list)
    defects: list[QualityDefectData] = Field(default_factory=list)
    logs: list[QualityOperationLogData] = Field(default_factory=list)


class QualityInspectionActionData(BaseModel):
    """Quality state transition response."""

    id: int
    inspection_no: str
    status: str
    operator: str
    operated_at: datetime


class QualityStatisticsData(BaseModel):
    """Quality statistics response payload."""

    total_count: int
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    defect_qty: Decimal
    defect_rate: Decimal
    rejected_rate: Decimal
    by_result: dict[str, int]


class QualityDiagnosticData(BaseModel):
    """Quality diagnostic response payload."""

    total_count: int
    draft_count: int
    confirmed_count: int
    cancelled_count: int
    missing_source_count: int
    by_source_type: dict[str, int]


class QualityExportRow(BaseModel):
    """Quality export row snapshot."""

    inspection_no: str
    company: str
    source_type: str
    source_id: str | None = None
    item_code: str
    supplier: str | None = None
    warehouse: str | None = None
    inspection_date: date
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    defect_qty: Decimal
    defect_rate: Decimal
    rejected_rate: Decimal
    result: str
    status: str


class QualityExportData(BaseModel):
    """Quality export response payload."""

    rows: list[QualityExportRow]
    total: int
