"""Pydantic schemas for report catalog readonly baseline (TASK-060B)."""

from __future__ import annotations

from typing import Generic
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API envelope."""

    code: str
    message: str
    data: T


class ReportCatalogItemData(BaseModel):
    """Catalog row for one report definition."""

    report_key: str
    name: str
    source_modules: list[str] = Field(default_factory=list)
    report_type: str
    required_filters: list[str] = Field(default_factory=list)
    optional_filters: list[str] = Field(default_factory=list)
    metric_summary: list[str] = Field(default_factory=list)
    permission_action: str
    status: str


class ReportCatalogRequestedScope(BaseModel):
    """Echoed query scope for list/detail responses."""

    company: str | None = None
    source_module: str | None = None
    report_type: str | None = None


class ReportCatalogListData(BaseModel):
    """Catalog list payload."""

    items: list[ReportCatalogItemData] = Field(default_factory=list)
    requested_scope: ReportCatalogRequestedScope


class ReportCatalogDetailData(BaseModel):
    """Catalog detail payload."""

    item: ReportCatalogItemData
    requested_scope: ReportCatalogRequestedScope
