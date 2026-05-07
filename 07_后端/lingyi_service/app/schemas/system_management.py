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


class SystemOrganizationFrameworkActionData(BaseModel):
    """One readonly action descriptor for organization framework row."""

    action_key: str
    label: str
    guarded: bool
    disabled_reason: str


class SystemOrganizationFrameworkItemData(BaseModel):
    """One readonly organization framework row."""

    org_code: str
    org_name: str
    parent_org_name: str
    manager_name: str
    org_level: str
    headcount_planned: int
    headcount_on_duty: int
    status: str
    effective_date: str
    updated_at: str
    remark: str
    actions: list[SystemOrganizationFrameworkActionData] = Field(default_factory=list)


class SystemOrganizationFrameworkData(BaseModel):
    """Payload for organization framework query."""

    items: list[SystemOrganizationFrameworkItemData] = Field(default_factory=list)
    total: int
    org_level_options: list[str] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)


class SystemIntegrationPlatformActionData(BaseModel):
    """One readonly action descriptor for integration platform row."""

    action_key: str
    label: str
    guarded: bool
    disabled_reason: str


class SystemIntegrationPlatformItemData(BaseModel):
    """One readonly integration platform row."""

    platform_code: str
    platform_name: str
    platform_type: str
    endpoint_mode: str
    connector: str
    webhook_url_masked: str
    sync_direction: str
    status: str
    last_sync_at: str
    retry_policy: str
    updated_at: str
    remark: str
    actions: list[SystemIntegrationPlatformActionData] = Field(default_factory=list)


class SystemIntegrationPlatformData(BaseModel):
    """Payload for integration platform query."""

    items: list[SystemIntegrationPlatformItemData] = Field(default_factory=list)
    total: int
    platform_type_options: list[str] = Field(default_factory=list)
    endpoint_mode_options: list[str] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)


class SystemAnnouncementActionData(BaseModel):
    """One readonly action descriptor for system announcement row."""

    action_key: str
    label: str
    guarded: bool
    disabled_reason: str


class SystemAnnouncementItemData(BaseModel):
    """One readonly system announcement row."""

    announcement_code: str
    title: str
    category: str
    target_scope: str
    publish_status: str
    published_at: str
    expires_at: str
    priority: str
    owner: str
    updated_at: str
    remark: str
    actions: list[SystemAnnouncementActionData] = Field(default_factory=list)


class SystemAnnouncementData(BaseModel):
    """Payload for system announcement query."""

    items: list[SystemAnnouncementItemData] = Field(default_factory=list)
    total: int
    category_options: list[str] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)


class SystemOperationLogActionData(BaseModel):
    """One readonly action descriptor for operation log row."""

    action_key: str
    label: str
    guarded: bool
    disabled_reason: str


class SystemOperationLogItemData(BaseModel):
    """One readonly system operation log row."""

    log_id: str
    module: str
    operation_type: str
    operation_name: str
    info: str
    operator: str
    result_status: str
    operated_at: str
    client_ip: str
    trace_id: str
    remark: str
    actions: list[SystemOperationLogActionData] = Field(default_factory=list)


class SystemOperationLogData(BaseModel):
    """Payload for system operation log query."""

    items: list[SystemOperationLogItemData] = Field(default_factory=list)
    total: int
    module_options: list[str] = Field(default_factory=list)
    operation_type_options: list[str] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)


class SystemDocumentCodeActionData(BaseModel):
    """One readonly action descriptor for document code row."""

    action_key: str
    label: str
    guarded: bool
    disabled_reason: str


class SystemDocumentCodeItemData(BaseModel):
    """One readonly system document code row."""

    document_code_id: str
    document_name: str
    document_type: str
    prefix: str
    serial_rule: str
    current_sequence: int
    status: str
    reset_cycle: str
    owner: str
    updated_at: str
    remark: str
    actions: list[SystemDocumentCodeActionData] = Field(default_factory=list)


class SystemDocumentCodeData(BaseModel):
    """Payload for system document code query."""

    items: list[SystemDocumentCodeItemData] = Field(default_factory=list)
    total: int
    document_type_options: list[str] = Field(default_factory=list)
    status_tags: list[str] = Field(default_factory=list)
    ui_buttons: list[str] = Field(default_factory=list)
    ui_table_headers: list[str] = Field(default_factory=list)
