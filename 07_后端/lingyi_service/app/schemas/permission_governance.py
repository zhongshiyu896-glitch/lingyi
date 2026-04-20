"""Schemas for permission governance readonly baseline (TASK-070A/TASK-070B)."""

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


class PermissionActionCatalogEntry(BaseModel):
    """One action row under a module catalog."""

    action: str
    category: str
    is_high_risk: bool
    ui_exposed: bool
    description: str


class PermissionActionCatalogModule(BaseModel):
    """Action catalog rows grouped by module."""

    module: str
    actions: list[PermissionActionCatalogEntry] = Field(default_factory=list)


class PermissionActionCatalogData(BaseModel):
    """Payload for action catalog endpoint."""

    modules: list[PermissionActionCatalogModule] = Field(default_factory=list)


class PermissionRoleMatrixEntry(BaseModel):
    """Static role -> actions matrix row."""

    role: str
    actions: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    high_risk_actions: list[str] = Field(default_factory=list)
    ui_hidden_actions: list[str] = Field(default_factory=list)


class PermissionRoleMatrixData(BaseModel):
    """Payload for role matrix endpoint."""

    roles: list[PermissionRoleMatrixEntry] = Field(default_factory=list)


class PermissionGovernanceDiagnosticCheck(BaseModel):
    """One diagnostic check result row."""

    name: str
    status: str
    message: str | None = None


class PermissionGovernanceDiagnosticData(BaseModel):
    """Payload for governance diagnostic endpoint."""

    module: str
    status: str
    registered_actions: list[str] = Field(default_factory=list)
    legacy_permission_audit_actions: list[str] = Field(default_factory=list)
    high_risk_actions: list[str] = Field(default_factory=list)
    ui_hidden_actions: list[str] = Field(default_factory=list)
    roles_with_permission_actions_count: int
    checks: list[PermissionGovernanceDiagnosticCheck] = Field(default_factory=list)
    catalog_enabled: bool
    roles_matrix_enabled: bool
    audit_read_enabled: bool
    export_enabled: bool
    diagnostic_enabled: bool
    generated_at: str


class PermissionSecurityAuditItemData(BaseModel):
    """One row in security audit readonly response."""

    id: int
    event_type: str
    module: str
    action: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    resource_no: str | None = None
    user_id: str | None = None
    permission_source: str | None = None
    deny_reason: str
    request_method: str
    request_path: str
    request_id: str
    created_at: str


class PermissionOperationAuditItemData(BaseModel):
    """One row in operation audit readonly response."""

    id: int
    module: str
    action: str
    operator: str
    resource_type: str
    resource_id: int | None = None
    resource_no: str | None = None
    result: str
    error_code: str | None = None
    request_id: str | None = None
    created_at: str
    has_before_data: bool = False
    has_after_data: bool = False
    before_keys: list[str] = Field(default_factory=list)
    after_keys: list[str] = Field(default_factory=list)


class PermissionSecurityAuditListData(BaseModel):
    """Paged payload for security audit query."""

    items: list[PermissionSecurityAuditItemData] = Field(default_factory=list)
    total: int
    page: int
    page_size: int


class PermissionOperationAuditListData(BaseModel):
    """Paged payload for operation audit query."""

    items: list[PermissionOperationAuditItemData] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
