"""Readonly static config catalog service for system management (TASK-080B)."""

from __future__ import annotations

from app.schemas.system_management import SystemConfigCatalogData
from app.schemas.system_management import SystemConfigCatalogItemData
from app.schemas.system_management import SystemApprovalFlowActionData
from app.schemas.system_management import SystemApprovalFlowCatalogData
from app.schemas.system_management import SystemApprovalFlowCatalogItemData
from app.schemas.system_management import SystemApprovalFlowNodeData
from app.schemas.system_management import SystemUserCatalogActionData
from app.schemas.system_management import SystemUserCatalogData
from app.schemas.system_management import SystemUserCatalogItemData


class SystemConfigCatalogService:
    """Serve local static system config metadata only."""

    _CATALOG: tuple[SystemConfigCatalogItemData, ...] = (
        SystemConfigCatalogItemData(
            module="system",
            config_key="ui.locale.default",
            config_group="ui",
            description="默认界面语言",
            source="static_registry",
            is_sensitive=False,
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemConfigCatalogItemData(
            module="system",
            config_key="ui.theme.default",
            config_group="ui",
            description="默认主题",
            source="static_registry",
            is_sensitive=False,
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemConfigCatalogItemData(
            module="system",
            config_key="security.auth.min_length",
            config_group="security",
            description="登录口令长度策略",
            source="policy_registry",
            is_sensitive=False,
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemConfigCatalogItemData(
            module="system",
            config_key="security.session.signing_key",
            config_group="security",
            description="会话签名密钥元数据",
            source="env_registry",
            is_sensitive=True,
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemConfigCatalogItemData(
            module="system",
            config_key="audit.retention.days",
            config_group="audit",
            description="审计日志留存天数策略",
            source="policy_registry",
            is_sensitive=False,
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemConfigCatalogItemData(
            module="system",
            config_key="integration.webhook.timeout_seconds",
            config_group="integration",
            description="外部回调超时策略",
            source="env_registry",
            is_sensitive=False,
            updated_at="2026-04-21T00:00:00Z",
        ),
    )

    _APPROVAL_FLOW_CATALOG: tuple[SystemApprovalFlowCatalogItemData, ...] = (
        SystemApprovalFlowCatalogItemData(
            flow_key="sample_order_default",
            title="样板单审核流程",
            audit_type="样板单",
            status="启用",
            sender="蓝总",
            created_by="蓝总",
            created_at="2026-04-04T18:00:00Z",
            sent_at="2026-04-04T18:01:00Z",
            last_modified_by="蓝总",
            last_modified_at="2026-04-04T18:01:00Z",
            nodes=[
                SystemApprovalFlowNodeData(
                    node_key="start",
                    node_name="开始",
                    approver_rule="系统发起",
                    status="done",
                ),
                SystemApprovalFlowNodeData(
                    node_key="auto_review",
                    node_name="流程自动测漏审",
                    approver_rule="系统自动审核",
                    status="done",
                ),
                SystemApprovalFlowNodeData(
                    node_key="end",
                    node_name="结束",
                    approver_rule="自动归档",
                    status="done",
                ),
            ],
            actions=[
                SystemApprovalFlowActionData(
                    action_key="diagram",
                    label="示意图",
                    guarded=True,
                    disabled_reason="只读模式：本地仅允许查看流程示意图。",
                ),
                SystemApprovalFlowActionData(
                    action_key="log",
                    label="操作日志记录",
                    guarded=True,
                    disabled_reason="只读模式：仅展示审计日志摘要。",
                ),
                SystemApprovalFlowActionData(
                    action_key="save",
                    label="保存",
                    guarded=True,
                    disabled_reason="只读模式：不允许提交审核流程写入。",
                ),
                SystemApprovalFlowActionData(
                    action_key="search",
                    label="搜索",
                    guarded=True,
                    disabled_reason="只读模式：使用上方筛选触发查询。",
                ),
                SystemApprovalFlowActionData(
                    action_key="reset",
                    label="重置",
                    guarded=True,
                    disabled_reason="只读模式：使用上方重置按钮。",
                ),
            ],
        ),
        SystemApprovalFlowCatalogItemData(
            flow_key="bulk_order_backup",
            title="大货单备选流程",
            audit_type="大货单",
            status="草稿",
            sender="系统管理员",
            created_by="系统管理员",
            created_at="2026-04-02T10:00:00Z",
            sent_at="2026-04-02T10:30:00Z",
            last_modified_by="系统管理员",
            last_modified_at="2026-04-03T08:00:00Z",
            nodes=[
                SystemApprovalFlowNodeData(
                    node_key="start",
                    node_name="开始",
                    approver_rule="系统发起",
                    status="done",
                ),
                SystemApprovalFlowNodeData(
                    node_key="manager_review",
                    node_name="经理复核",
                    approver_rule="销售部经理",
                    status="todo",
                ),
                SystemApprovalFlowNodeData(
                    node_key="end",
                    node_name="结束",
                    approver_rule="归档",
                    status="todo",
                ),
            ],
            actions=[
                SystemApprovalFlowActionData(
                    action_key="diagram",
                    label="示意图",
                    guarded=True,
                    disabled_reason="只读模式：本地仅允许查看流程示意图。",
                ),
                SystemApprovalFlowActionData(
                    action_key="log",
                    label="操作日志记录",
                    guarded=True,
                    disabled_reason="只读模式：仅展示审计日志摘要。",
                ),
                SystemApprovalFlowActionData(
                    action_key="save",
                    label="保存",
                    guarded=True,
                    disabled_reason="只读模式：不允许提交审核流程写入。",
                ),
            ],
        ),
    )

    _USER_CATALOG: tuple[SystemUserCatalogItemData, ...] = (
        SystemUserCatalogItemData(
            user_id="USR-001",
            username="lanzong",
            display_name="蓝总",
            role="系统管理员",
            status="启用",
            department="管理中心",
            last_login_at="2026-05-03T19:55:00Z",
            updated_at="2026-05-03T19:55:00Z",
            actions=[
                SystemUserCatalogActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看用户目录信息。",
                ),
                SystemUserCatalogActionData(
                    action_key="create",
                    label="新增",
                    guarded=True,
                    disabled_reason="只读模式：不允许新增用户。",
                ),
                SystemUserCatalogActionData(
                    action_key="edit",
                    label="编辑",
                    guarded=True,
                    disabled_reason="只读模式：不允许编辑用户。",
                ),
                SystemUserCatalogActionData(
                    action_key="disable",
                    label="禁用",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更用户状态。",
                ),
                SystemUserCatalogActionData(
                    action_key="reset_password",
                    label="重置密码",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发重置密码。",
                ),
            ],
        ),
        SystemUserCatalogItemData(
            user_id="USR-002",
            username="finance.qa",
            display_name="财务测试员",
            role="财务主管",
            status="启用",
            department="财务中心",
            last_login_at="2026-05-02T15:20:00Z",
            updated_at="2026-05-02T15:20:00Z",
            actions=[
                SystemUserCatalogActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看用户目录信息。",
                ),
                SystemUserCatalogActionData(
                    action_key="create",
                    label="新增",
                    guarded=True,
                    disabled_reason="只读模式：不允许新增用户。",
                ),
                SystemUserCatalogActionData(
                    action_key="edit",
                    label="编辑",
                    guarded=True,
                    disabled_reason="只读模式：不允许编辑用户。",
                ),
                SystemUserCatalogActionData(
                    action_key="disable",
                    label="禁用",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更用户状态。",
                ),
                SystemUserCatalogActionData(
                    action_key="reset_password",
                    label="重置密码",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发重置密码。",
                ),
            ],
        ),
        SystemUserCatalogItemData(
            user_id="USR-003",
            username="ops.locked",
            display_name="运维锁定账户",
            role="审计员",
            status="锁定",
            department="运维中心",
            last_login_at="2026-04-20T08:30:00Z",
            updated_at="2026-04-22T09:10:00Z",
            actions=[
                SystemUserCatalogActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看用户目录信息。",
                ),
                SystemUserCatalogActionData(
                    action_key="create",
                    label="新增",
                    guarded=True,
                    disabled_reason="只读模式：不允许新增用户。",
                ),
                SystemUserCatalogActionData(
                    action_key="edit",
                    label="编辑",
                    guarded=True,
                    disabled_reason="只读模式：不允许编辑用户。",
                ),
                SystemUserCatalogActionData(
                    action_key="disable",
                    label="禁用",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更用户状态。",
                ),
                SystemUserCatalogActionData(
                    action_key="reset_password",
                    label="重置密码",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发重置密码。",
                ),
            ],
        ),
    )

    @classmethod
    def list_catalog(
        cls,
        *,
        module: str | None,
        config_group: str | None,
        source: str | None,
        is_sensitive: bool | None,
    ) -> SystemConfigCatalogData:
        normalized_module = cls._norm(module)
        normalized_group = cls._norm(config_group)
        normalized_source = cls._norm(source)

        items = [item.model_copy(deep=True) for item in cls._CATALOG]

        if normalized_module is not None:
            items = [item for item in items if item.module == normalized_module]
        if normalized_group is not None:
            items = [item for item in items if item.config_group == normalized_group]
        if normalized_source is not None:
            items = [item for item in items if item.source == normalized_source]
        if is_sensitive is not None:
            items = [item for item in items if item.is_sensitive == is_sensitive]

        return SystemConfigCatalogData(items=items, total=len(items))

    @classmethod
    def list_approval_flow_catalog(
        cls,
        *,
        audit_type: str | None,
        status: str | None,
        keyword: str | None,
    ) -> SystemApprovalFlowCatalogData:
        normalized_audit_type = cls._norm(audit_type)
        normalized_status = cls._norm(status)
        normalized_keyword = cls._norm(keyword)

        items = [item.model_copy(deep=True) for item in cls._APPROVAL_FLOW_CATALOG]

        if normalized_audit_type is not None:
            items = [item for item in items if item.audit_type == normalized_audit_type]
        if normalized_status is not None:
            items = [item for item in items if item.status == normalized_status]
        if normalized_keyword is not None:
            lowered_keyword = normalized_keyword.lower()
            items = [
                item
                for item in items
                if lowered_keyword in item.title.lower() or lowered_keyword in item.flow_key.lower()
            ]

        audit_type_options = sorted({item.audit_type for item in cls._APPROVAL_FLOW_CATALOG})
        return SystemApprovalFlowCatalogData(items=items, total=len(items), audit_type_options=audit_type_options)

    @classmethod
    def list_user_catalog(
        cls,
        *,
        role: str | None,
        status: str | None,
        keyword: str | None,
    ) -> SystemUserCatalogData:
        normalized_role = cls._norm(role)
        normalized_status = cls._norm(status)
        normalized_keyword = cls._norm(keyword)

        items = [item.model_copy(deep=True) for item in cls._USER_CATALOG]

        if normalized_role is not None:
            items = [item for item in items if item.role == normalized_role]
        if normalized_status is not None:
            items = [item for item in items if item.status == normalized_status]
        if normalized_keyword is not None:
            lowered_keyword = normalized_keyword.lower()
            items = [
                item
                for item in items
                if lowered_keyword in item.username.lower()
                or lowered_keyword in item.display_name.lower()
                or lowered_keyword in item.department.lower()
            ]

        role_options = sorted({item.role for item in cls._USER_CATALOG})
        status_options = sorted({item.status for item in cls._USER_CATALOG})
        return SystemUserCatalogData(
            items=items,
            total=len(items),
            role_options=role_options,
            status_options=status_options,
        )

    @staticmethod
    def _norm(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
