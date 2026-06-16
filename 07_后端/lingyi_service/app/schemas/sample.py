"""Pydantic schemas for FastAPI-native sample workflow."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

SampleStatus = Literal["draft", "pending", "patterning", "fitting", "sealed", "reversed", "converted"]
SampleType = Literal["初样", "复样", "产前样", "确认样", "封样"]
SampleImageTone = Literal["blue", "green", "pink", "amber", "gray", "cyan"]


class SampleOrderWriteBase(BaseModel):
    """Mutable sample order fields."""

    company: str = Field(default="默认公司", min_length=1, max_length=140)
    sample_no: str | None = Field(default=None, max_length=140)
    style_no: str = Field(..., min_length=1, max_length=140)
    style_name: str = Field(..., min_length=1, max_length=255)
    customer: str = Field(..., min_length=1, max_length=255)
    factory: str = Field(default="", max_length=255)
    sample_type: SampleType = "初样"
    stage: str = Field(default="建档", min_length=1, max_length=140)
    progress: int = Field(default=0, ge=0, le=100)
    pattern_maker: str = Field(default="", max_length=140)
    sample_maker: str = Field(default="", max_length=140)
    due_date: date | None = None
    status: SampleStatus = "draft"
    image_tone: SampleImageTone = "blue"
    owner_note: str = Field(default="", max_length=1000)


class SampleOrderCreateRequest(SampleOrderWriteBase):
    """Create sample order."""

    operation: Literal["create"] = "create"
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class SampleOrderUpdateRequest(BaseModel):
    """Update sample order draft fields."""

    operation: Literal["update"] = "update"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    style_no: str | None = Field(default=None, min_length=1, max_length=140)
    style_name: str | None = Field(default=None, min_length=1, max_length=255)
    customer: str | None = Field(default=None, min_length=1, max_length=255)
    factory: str | None = Field(default=None, max_length=255)
    sample_type: SampleType | None = None
    stage: str | None = Field(default=None, min_length=1, max_length=140)
    progress: int | None = Field(default=None, ge=0, le=100)
    pattern_maker: str | None = Field(default=None, max_length=140)
    sample_maker: str | None = Field(default=None, max_length=140)
    due_date: date | None = None
    status: SampleStatus | None = None
    image_tone: SampleImageTone | None = None
    owner_note: str | None = Field(default=None, max_length=1000)


class SampleOrderStatusRequest(BaseModel):
    """Status transition request."""

    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    reason: str | None = Field(default=None, max_length=255)


class SampleOrderConvertRequest(BaseModel):
    """Convert a sealed sample order into a local sales-order draft."""

    operation: Literal["convert"] = "convert"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    target_sales_order: str | None = Field(default=None, max_length=140)


class SampleOrderItem(BaseModel):
    """Sample order row returned to frontend."""

    id: int
    company: str
    sample_no: str
    style_no: str
    style_name: str
    customer: str
    factory: str
    sample_type: SampleType
    stage: str
    progress: int
    pattern_maker: str
    sample_maker: str
    due_date: date | None
    created_at: datetime | None
    status: SampleStatus
    image_tone: SampleImageTone
    owner_note: str
    bulk_handoff_no: str | None = None
    bulk_handoff_status: str | None = None
    version: int


class SampleOrderListData(BaseModel):
    """Paginated sample order data."""

    items: list[SampleOrderItem]
    total: int
    page: int
    page_size: int


TrackingTemplateStatus = Literal["enabled", "disabled"]
TrackingNodeStatus = Literal["required", "optional", "locked"]


class SampleTrackingNodeItem(BaseModel):
    """Sample tracking node row."""

    id: int
    template_id: int
    name: str
    role: str
    lead_time: str
    status: TrackingNodeStatus
    gate: str
    output: str
    reminder: str
    sequence_no: int


class SampleTrackingTemplateItem(BaseModel):
    """Sample tracking template row."""

    id: int
    company: str
    template_code: str
    name: str
    category: str
    group: str
    status: TrackingTemplateStatus
    owner: str
    version: str
    updated_at: datetime | None
    summary: str
    nodes: list[SampleTrackingNodeItem] = Field(default_factory=list)


class SampleTrackingTemplateListData(BaseModel):
    """Template list payload."""

    items: list[SampleTrackingTemplateItem]
    total: int
    page: int
    page_size: int


class SampleTrackingTemplateCreateRequest(BaseModel):
    """Create tracking template."""

    operation: Literal["create"] = "create"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    template_code: str | None = Field(default=None, max_length=140)
    name: str = Field(..., min_length=1, max_length=255)
    category: str = Field(default="通用", max_length=140)
    group: str = Field(default="默认分组", max_length=140)
    status: TrackingTemplateStatus = "enabled"
    owner: str = Field(default="", max_length=140)
    version: str = Field(default="V1", max_length=64)
    summary: str = Field(default="", max_length=1000)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class SampleTrackingNodeCreateRequest(BaseModel):
    """Create one tracking node."""

    operation: Literal["create_node"] = "create_node"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="", max_length=140)
    lead_time: str = Field(default="", max_length=64)
    status: TrackingNodeStatus = "required"
    gate: str = Field(default="", max_length=1000)
    output: str = Field(default="", max_length=1000)
    reminder: str = Field(default="", max_length=1000)
    sequence_no: int = Field(default=10, ge=0)
