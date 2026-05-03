"""Pydantic schemas for system config catalog readonly baseline (TASK-080B)."""

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


class SystemConfigCatalogItemData(BaseModel):
    """One static config catalog row."""

    module: str
    config_key: str
    config_group: str
    description: str
    source: str
    is_sensitive: bool
    updated_at: str


class SystemConfigCatalogData(BaseModel):
    """Payload for config catalog query."""

    items: list[SystemConfigCatalogItemData] = Field(default_factory=list)
    total: int


class SystemDictionaryCatalogItemData(BaseModel):
    """One static dictionary catalog row."""

    dict_type: str
    dict_code: str
    dict_name: str
    status: str
    source: str
    updated_at: str


class SystemDictionaryCatalogData(BaseModel):
    """Payload for dictionary catalog query."""

    items: list[SystemDictionaryCatalogItemData] = Field(default_factory=list)
    total: int


class SystemHealthSummaryItemData(BaseModel):
    """One readonly health-check row."""

    module: str
    status: str
    check_name: str
    check_result: str
    generated_at: str


class SystemHealthSummaryData(BaseModel):
    """Payload for system health summary query."""

    items: list[SystemHealthSummaryItemData] = Field(default_factory=list)
    total: int
    generated_at: str


class SystemApprovalFlowActionData(BaseModel):
    """One readonly action descriptor for approval flow card."""

    action_key: str
    label: str
    guarded: bool
    disabled_reason: str


class SystemApprovalFlowNodeData(BaseModel):
    """One node preview row for approval flow diagram."""

    node_key: str
    node_name: str
    approver_rule: str
    status: str


class SystemApprovalFlowCatalogItemData(BaseModel):
    """One readonly approval-flow list row."""

    flow_key: str
    title: str
    audit_type: str
    status: str
    sender: str
    created_by: str
    created_at: str
    sent_at: str
    last_modified_by: str
    last_modified_at: str
    nodes: list[SystemApprovalFlowNodeData] = Field(default_factory=list)
    actions: list[SystemApprovalFlowActionData] = Field(default_factory=list)


class SystemApprovalFlowCatalogData(BaseModel):
    """Payload for approval-flow catalog query."""

    items: list[SystemApprovalFlowCatalogItemData] = Field(default_factory=list)
    total: int
    audit_type_options: list[str] = Field(default_factory=list)


class SystemUserCatalogActionData(BaseModel):
    """One readonly action descriptor for user catalog row."""

    action_key: str
    label: str
    guarded: bool
    disabled_reason: str


class SystemUserCatalogItemData(BaseModel):
    """One readonly user catalog row."""

    user_id: str
    username: str
    display_name: str
    role: str
    status: str
    department: str
    last_login_at: str
    updated_at: str
    actions: list[SystemUserCatalogActionData] = Field(default_factory=list)


class SystemUserCatalogData(BaseModel):
    """Payload for user catalog query."""

    items: list[SystemUserCatalogItemData] = Field(default_factory=list)
    total: int
    role_options: list[str] = Field(default_factory=list)
    status_options: list[str] = Field(default_factory=list)
