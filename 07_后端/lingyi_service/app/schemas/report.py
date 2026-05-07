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
    ui_placeholders: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    preview_rows: list[dict[str, str]] = Field(default_factory=list)


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


class ReportEmployeeTaskStatisticsItemData(BaseModel):
    """Readonly row for employee task statistics."""

    employee_id: str
    employee_name: str
    department: str
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    overdue_tasks: int
    completion_rate: str
    latest_task_no: str
    latest_task_title: str
    latest_due_date: str
    updated_at: str
    status: str


class ReportEmployeeTaskStatisticsScope(BaseModel):
    """Echoed query scope for employee task statistics."""

    company: str | None = None
    department: str | None = None
    task_status: str | None = None
    employee_keyword: str | None = None
    from_date: str | None = None
    to_date: str | None = None


class ReportEmployeeTaskStatisticsData(BaseModel):
    """Employee task statistics payload."""

    items: list[ReportEmployeeTaskStatisticsItemData] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)
    requested_scope: ReportEmployeeTaskStatisticsScope


class ReportApprovalReportItemData(BaseModel):
    """Readonly row for approval report."""

    approval_no: str
    approval_type: str
    related_doc_no: str
    applicant: str
    approver: str
    department: str
    amount: str
    priority: str
    submitted_at: str
    completed_at: str
    status: str
    remark: str


class ReportApprovalReportScope(BaseModel):
    """Echoed query scope for approval report."""

    company: str | None = None
    approver_keyword: str | None = None
    approval_status: str | None = None
    from_date: str | None = None
    to_date: str | None = None


class ReportApprovalReportData(BaseModel):
    """Approval report payload."""

    items: list[ReportApprovalReportItemData] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)
    requested_scope: ReportApprovalReportScope
