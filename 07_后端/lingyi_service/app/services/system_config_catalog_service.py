"""Readonly static config catalog service for system management (TASK-080B)."""

from __future__ import annotations

from app.schemas.system_management import SystemConfigCatalogData
from app.schemas.system_management import SystemConfigCatalogItemData
from app.schemas.system_management import SystemDocumentCodeActionData
from app.schemas.system_management import SystemDocumentCodeData
from app.schemas.system_management import SystemDocumentCodeItemData
from app.schemas.system_management import SystemApprovalFlowActionData
from app.schemas.system_management import SystemApprovalFlowCatalogData
from app.schemas.system_management import SystemApprovalFlowCatalogItemData
from app.schemas.system_management import SystemApprovalFlowNodeData
from app.schemas.system_management import SystemAnnouncementActionData
from app.schemas.system_management import SystemAnnouncementData
from app.schemas.system_management import SystemAnnouncementItemData
from app.schemas.system_management import SystemIntegrationPlatformActionData
from app.schemas.system_management import SystemIntegrationPlatformData
from app.schemas.system_management import SystemIntegrationPlatformItemData
from app.schemas.system_management import SystemOperationLogActionData
from app.schemas.system_management import SystemOperationLogData
from app.schemas.system_management import SystemOperationLogItemData
from app.schemas.system_management import SystemOrganizationFrameworkActionData
from app.schemas.system_management import SystemOrganizationFrameworkData
from app.schemas.system_management import SystemOrganizationFrameworkItemData
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

    _ORGANIZATION_FRAMEWORK_CATALOG: tuple[SystemOrganizationFrameworkItemData, ...] = (
        SystemOrganizationFrameworkItemData(
            org_code="ORG-HQ-001",
            org_name="总部运营中心",
            parent_org_name="-",
            manager_name="蓝总",
            org_level="总部",
            headcount_planned=28,
            headcount_on_duty=24,
            status="生效",
            effective_date="2026-01-01",
            updated_at="2026-05-03T09:12:00Z",
            remark="统筹采购、计划与财务协同。",
            actions=[
                SystemOrganizationFrameworkActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看组织框架。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="confirm",
                    label="确认（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许执行组织框架确认。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="review",
                    label="复核（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许执行组织框架复核。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="upload",
                    label="上传（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：上传入口禁用。",
                ),
            ],
        ),
        SystemOrganizationFrameworkItemData(
            org_code="ORG-SALES-011",
            org_name="销售与客服部",
            parent_org_name="总部运营中心",
            manager_name="陈晓敏",
            org_level="部门",
            headcount_planned=15,
            headcount_on_duty=13,
            status="生效",
            effective_date="2026-02-15",
            updated_at="2026-04-30T16:20:00Z",
            remark="负责客户订单、对账与售后协同。",
            actions=[
                SystemOrganizationFrameworkActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看组织框架。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="confirm",
                    label="确认（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许执行组织框架确认。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="review",
                    label="复核（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许执行组织框架复核。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="upload",
                    label="上传（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：上传入口禁用。",
                ),
            ],
        ),
        SystemOrganizationFrameworkItemData(
            org_code="ORG-OPS-023",
            org_name="仓配运营组",
            parent_org_name="总部运营中心",
            manager_name="赵文涛",
            org_level="小组",
            headcount_planned=12,
            headcount_on_duty=10,
            status="待生效",
            effective_date="2026-06-01",
            updated_at="2026-05-05T11:40:00Z",
            remark="待并入统一仓配流程，当前观察期。",
            actions=[
                SystemOrganizationFrameworkActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看组织框架。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="confirm",
                    label="确认（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许执行组织框架确认。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="review",
                    label="复核（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许执行组织框架复核。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
                SystemOrganizationFrameworkActionData(
                    action_key="upload",
                    label="上传（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：上传入口禁用。",
                ),
            ],
        ),
    )

    _INTEGRATION_PLATFORM_CATALOG: tuple[SystemIntegrationPlatformItemData, ...] = (
        SystemIntegrationPlatformItemData(
            platform_code="INT-ERP-001",
            platform_name="ERPNext 主数据桥",
            platform_type="ERP",
            endpoint_mode="webhook",
            connector="ERPNext",
            webhook_url_masked="https://erpnext.example.com/***/events",
            sync_direction="双向",
            status="运行中",
            last_sync_at="2026-05-07T10:42:00Z",
            retry_policy="指数退避 x3",
            updated_at="2026-05-07T10:45:00Z",
            remark="同步款式、订单与库存摘要。",
            actions=[
                SystemIntegrationPlatformActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看对接平台信息。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="test_connection",
                    label="测试连接（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发真实连通性测试。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="sync_now",
                    label="同步（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发同步写请求。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="toggle",
                    label="启停（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更平台启停状态。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
        SystemIntegrationPlatformItemData(
            platform_code="INT-SCM-011",
            platform_name="供应链协同网关",
            platform_type="SCM",
            endpoint_mode="api",
            connector="SCM-Gateway",
            webhook_url_masked="https://scm-gateway.example.com/***/push",
            sync_direction="入站",
            status="告警",
            last_sync_at="2026-05-06T21:18:00Z",
            retry_policy="固定间隔 5m x12",
            updated_at="2026-05-07T08:12:00Z",
            remark="待处理重试队列堆积。",
            actions=[
                SystemIntegrationPlatformActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看对接平台信息。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="test_connection",
                    label="测试连接（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发真实连通性测试。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="sync_now",
                    label="同步（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发同步写请求。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="toggle",
                    label="启停（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更平台启停状态。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
        SystemIntegrationPlatformItemData(
            platform_code="INT-CRM-020",
            platform_name="客户关系集成桥",
            platform_type="CRM",
            endpoint_mode="event_bus",
            connector="CRM-Bridge",
            webhook_url_masked="https://crm-bridge.example.com/***/events",
            sync_direction="出站",
            status="停用",
            last_sync_at="2026-04-30T16:00:00Z",
            retry_policy="停用状态不重试",
            updated_at="2026-05-05T14:31:00Z",
            remark="历史渠道迁移完成，当前停用保留。",
            actions=[
                SystemIntegrationPlatformActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看对接平台信息。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="test_connection",
                    label="测试连接（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发真实连通性测试。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="sync_now",
                    label="同步（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发同步写请求。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="toggle",
                    label="启停（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更平台启停状态。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemIntegrationPlatformActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
    )

    _SYSTEM_ANNOUNCEMENT_CATALOG: tuple[SystemAnnouncementItemData, ...] = (
        SystemAnnouncementItemData(
            announcement_code="ANN-2026-001",
            title="五一后排产节奏调整通知",
            category="生产协同",
            target_scope="全员",
            publish_status="已发布",
            published_at="2026-05-07T09:00:00Z",
            expires_at="2026-05-31T23:59:59Z",
            priority="高",
            owner="运营中心",
            updated_at="2026-05-07T09:10:00Z",
            remark="仅供只读查看，发布与撤回操作受控。",
            actions=[
                SystemAnnouncementActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看系统公告。",
                ),
                SystemAnnouncementActionData(
                    action_key="publish",
                    label="发布（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发公告发布。",
                ),
                SystemAnnouncementActionData(
                    action_key="withdraw",
                    label="撤回（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发公告撤回。",
                ),
                SystemAnnouncementActionData(
                    action_key="pin",
                    label="置顶（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更公告置顶状态。",
                ),
                SystemAnnouncementActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemAnnouncementActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
        SystemAnnouncementItemData(
            announcement_code="ANN-2026-002",
            title="权限治理窗口维护公告（草稿）",
            category="权限治理",
            target_scope="管理员",
            publish_status="草稿",
            published_at="2026-05-06T14:30:00Z",
            expires_at="2026-06-15T23:59:59Z",
            priority="中",
            owner="信息安全组",
            updated_at="2026-05-07T08:20:00Z",
            remark="草稿态仅展示，不允许写操作。",
            actions=[
                SystemAnnouncementActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看系统公告。",
                ),
                SystemAnnouncementActionData(
                    action_key="publish",
                    label="发布（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发公告发布。",
                ),
                SystemAnnouncementActionData(
                    action_key="withdraw",
                    label="撤回（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发公告撤回。",
                ),
                SystemAnnouncementActionData(
                    action_key="pin",
                    label="置顶（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更公告置顶状态。",
                ),
                SystemAnnouncementActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemAnnouncementActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
        SystemAnnouncementItemData(
            announcement_code="ANN-2026-003",
            title="历史接口切换提醒（已撤回）",
            category="系统运维",
            target_scope="运维组",
            publish_status="已撤回",
            published_at="2026-05-05T11:00:00Z",
            expires_at="2026-05-20T23:59:59Z",
            priority="低",
            owner="平台运维组",
            updated_at="2026-05-07T07:45:00Z",
            remark="撤回后仅保留审计可见性。",
            actions=[
                SystemAnnouncementActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看系统公告。",
                ),
                SystemAnnouncementActionData(
                    action_key="publish",
                    label="发布（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发公告发布。",
                ),
                SystemAnnouncementActionData(
                    action_key="withdraw",
                    label="撤回（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发公告撤回。",
                ),
                SystemAnnouncementActionData(
                    action_key="pin",
                    label="置顶（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许变更公告置顶状态。",
                ),
                SystemAnnouncementActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemAnnouncementActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
    )

    _OPERATION_LOG_CATALOG: tuple[SystemOperationLogItemData, ...] = (
        SystemOperationLogItemData(
            log_id="OPL-2026-0001",
            module="system_management",
            operation_type="查询",
            operation_name="系统配置目录检索",
            info="筛选模块=system，命中 6 条配置目录元数据。",
            operator="系统管理员",
            result_status="成功",
            operated_at="2026-05-08T09:20:31Z",
            client_ip="10.10.5.21",
            trace_id="trace-sm-5f7a0a31",
            remark="仅展示只读日志，不允许写入与归档。",
            actions=[
                SystemOperationLogActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看日志详情。",
                ),
                SystemOperationLogActionData(
                    action_key="export",
                    label="导出（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发导出。",
                ),
                SystemOperationLogActionData(
                    action_key="print",
                    label="打印（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发打印。",
                ),
                SystemOperationLogActionData(
                    action_key="archive",
                    label="归档（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发日志归档。",
                ),
                SystemOperationLogActionData(
                    action_key="cleanup",
                    label="清理（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发日志清理。",
                ),
            ],
        ),
        SystemOperationLogItemData(
            log_id="OPL-2026-0002",
            module="integration_platform",
            operation_type="同步检查",
            operation_name="对接平台状态诊断",
            info="对接平台 connector=ERPNextBridge 触发只读连通性检查。",
            operator="平台运维",
            result_status="部分成功",
            operated_at="2026-05-08T08:46:09Z",
            client_ip="10.10.8.33",
            trace_id="trace-ip-7bc21d09",
            remark="告警已记录，后续人工处理。",
            actions=[
                SystemOperationLogActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看日志详情。",
                ),
                SystemOperationLogActionData(
                    action_key="export",
                    label="导出（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发导出。",
                ),
                SystemOperationLogActionData(
                    action_key="print",
                    label="打印（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发打印。",
                ),
                SystemOperationLogActionData(
                    action_key="archive",
                    label="归档（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发日志归档。",
                ),
                SystemOperationLogActionData(
                    action_key="cleanup",
                    label="清理（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发日志清理。",
                ),
            ],
        ),
        SystemOperationLogItemData(
            log_id="OPL-2026-0003",
            module="permission_governance",
            operation_type="权限校验",
            operation_name="角色矩阵读取失败告警",
            info="关键字 role_matrix 触发权限缺失告警，建议复核角色动作映射。",
            operator="审计员",
            result_status="失败",
            operated_at="2026-05-07T17:32:44Z",
            client_ip="10.10.9.18",
            trace_id="trace-pg-1de9344f",
            remark="失败记录仅用于只读审计分析。",
            actions=[
                SystemOperationLogActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看日志详情。",
                ),
                SystemOperationLogActionData(
                    action_key="export",
                    label="导出（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发导出。",
                ),
                SystemOperationLogActionData(
                    action_key="print",
                    label="打印（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发打印。",
                ),
                SystemOperationLogActionData(
                    action_key="archive",
                    label="归档（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发日志归档。",
                ),
                SystemOperationLogActionData(
                    action_key="cleanup",
                    label="清理（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发日志清理。",
                ),
            ],
        ),
    )

    _DOCUMENT_CODE_CATALOG: tuple[SystemDocumentCodeItemData, ...] = (
        SystemDocumentCodeItemData(
            document_code_id="DOC-CODE-001",
            document_name="采购入库单编码",
            document_type="采购入库",
            prefix="PI",
            serial_rule="YYYYMM + 4位流水",
            current_sequence=1247,
            status="启用",
            reset_cycle="按月重置",
            owner="供应链中心",
            updated_at="2026-05-08T10:12:00Z",
            remark="只读模式：不允许重置流水或变更编码规则。",
            actions=[
                SystemDocumentCodeActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看编码配置。",
                ),
                SystemDocumentCodeActionData(
                    action_key="create",
                    label="新增（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许新增单据编码。",
                ),
                SystemDocumentCodeActionData(
                    action_key="edit",
                    label="编辑（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许编辑单据编码。",
                ),
                SystemDocumentCodeActionData(
                    action_key="toggle",
                    label="启停（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许切换编码启停状态。",
                ),
                SystemDocumentCodeActionData(
                    action_key="preview",
                    label="预览（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发编码预览生成。",
                ),
                SystemDocumentCodeActionData(
                    action_key="reset",
                    label="重置（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许重置流水号。",
                ),
                SystemDocumentCodeActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemDocumentCodeActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
        SystemDocumentCodeItemData(
            document_code_id="DOC-CODE-002",
            document_name="生产领料单编码",
            document_type="生产领料",
            prefix="LL",
            serial_rule="YY + 6位流水",
            current_sequence=90831,
            status="草稿",
            reset_cycle="不自动重置",
            owner="生产计划组",
            updated_at="2026-05-07T16:40:00Z",
            remark="草稿态仅可查看，禁止提交与启用。",
            actions=[
                SystemDocumentCodeActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看编码配置。",
                ),
                SystemDocumentCodeActionData(
                    action_key="create",
                    label="新增（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许新增单据编码。",
                ),
                SystemDocumentCodeActionData(
                    action_key="edit",
                    label="编辑（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许编辑单据编码。",
                ),
                SystemDocumentCodeActionData(
                    action_key="toggle",
                    label="启停（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许切换编码启停状态。",
                ),
                SystemDocumentCodeActionData(
                    action_key="preview",
                    label="预览（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发编码预览生成。",
                ),
                SystemDocumentCodeActionData(
                    action_key="reset",
                    label="重置（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许重置流水号。",
                ),
                SystemDocumentCodeActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemDocumentCodeActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
                ),
            ],
        ),
        SystemDocumentCodeItemData(
            document_code_id="DOC-CODE-003",
            document_name="调拨出库单编码",
            document_type="调拨出库",
            prefix="DB",
            serial_rule="YYYY + 5位流水",
            current_sequence=32608,
            status="停用",
            reset_cycle="按年重置",
            owner="仓储运营组",
            updated_at="2026-05-06T21:05:00Z",
            remark="停用记录保留审计可见性，禁止写操作。",
            actions=[
                SystemDocumentCodeActionData(
                    action_key="view",
                    label="查看",
                    guarded=False,
                    disabled_reason="只读模式：仅允许查看编码配置。",
                ),
                SystemDocumentCodeActionData(
                    action_key="create",
                    label="新增（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许新增单据编码。",
                ),
                SystemDocumentCodeActionData(
                    action_key="edit",
                    label="编辑（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许编辑单据编码。",
                ),
                SystemDocumentCodeActionData(
                    action_key="toggle",
                    label="启停（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许切换编码启停状态。",
                ),
                SystemDocumentCodeActionData(
                    action_key="preview",
                    label="预览（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许触发编码预览生成。",
                ),
                SystemDocumentCodeActionData(
                    action_key="reset",
                    label="重置（guarded）",
                    guarded=True,
                    disabled_reason="只读模式：不允许重置流水号。",
                ),
                SystemDocumentCodeActionData(
                    action_key="export",
                    label="导出（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：导出入口禁用。",
                ),
                SystemDocumentCodeActionData(
                    action_key="print",
                    label="打印（disabled）",
                    guarded=True,
                    disabled_reason="只读模式：打印入口禁用。",
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

    @classmethod
    def list_organization_framework_catalog(
        cls,
        *,
        org_level: str | None,
        status: str | None,
        keyword: str | None,
        effective_start_date: str | None,
        effective_end_date: str | None,
    ) -> SystemOrganizationFrameworkData:
        normalized_org_level = cls._norm(org_level)
        normalized_status = cls._norm(status)
        normalized_keyword = cls._norm(keyword)
        normalized_effective_start_date = cls._norm(effective_start_date)
        normalized_effective_end_date = cls._norm(effective_end_date)

        items = [item.model_copy(deep=True) for item in cls._ORGANIZATION_FRAMEWORK_CATALOG]

        if normalized_org_level is not None:
            items = [item for item in items if item.org_level == normalized_org_level]
        if normalized_status is not None:
            items = [item for item in items if item.status == normalized_status]
        if normalized_keyword is not None:
            lowered_keyword = normalized_keyword.lower()
            items = [
                item
                for item in items
                if lowered_keyword in item.org_code.lower()
                or lowered_keyword in item.org_name.lower()
                or lowered_keyword in item.parent_org_name.lower()
                or lowered_keyword in item.manager_name.lower()
            ]
        if normalized_effective_start_date is not None:
            items = [item for item in items if item.effective_date >= normalized_effective_start_date]
        if normalized_effective_end_date is not None:
            items = [item for item in items if item.effective_date <= normalized_effective_end_date]

        org_level_options = sorted({item.org_level for item in cls._ORGANIZATION_FRAMEWORK_CATALOG})
        status_tags = sorted({item.status for item in cls._ORGANIZATION_FRAMEWORK_CATALOG})
        ui_buttons = ["查看", "确认（guarded）", "复核（guarded）", "导出（disabled）", "打印（disabled）", "上传（disabled）"]
        ui_table_headers = [
            "组织编码",
            "组织名称",
            "上级组织",
            "负责人",
            "组织层级",
            "编制人数",
            "在岗人数",
            "状态",
            "生效日期",
            "更新时间",
            "备注",
        ]
        return SystemOrganizationFrameworkData(
            items=items,
            total=len(items),
            org_level_options=org_level_options,
            status_tags=status_tags,
            ui_buttons=ui_buttons,
            ui_table_headers=ui_table_headers,
        )

    @classmethod
    def list_integration_platform_catalog(
        cls,
        *,
        platform_type: str | None,
        status: str | None,
        endpoint_mode: str | None,
        keyword: str | None,
        updated_start_date: str | None,
        updated_end_date: str | None,
    ) -> SystemIntegrationPlatformData:
        normalized_platform_type = cls._norm(platform_type)
        normalized_status = cls._norm(status)
        normalized_endpoint_mode = cls._norm(endpoint_mode)
        normalized_keyword = cls._norm(keyword)
        normalized_updated_start_date = cls._norm(updated_start_date)
        normalized_updated_end_date = cls._norm(updated_end_date)

        items = [item.model_copy(deep=True) for item in cls._INTEGRATION_PLATFORM_CATALOG]

        if normalized_platform_type is not None:
            items = [item for item in items if item.platform_type == normalized_platform_type]
        if normalized_status is not None:
            items = [item for item in items if item.status == normalized_status]
        if normalized_endpoint_mode is not None:
            items = [item for item in items if item.endpoint_mode == normalized_endpoint_mode]
        if normalized_keyword is not None:
            lowered_keyword = normalized_keyword.lower()
            items = [
                item
                for item in items
                if lowered_keyword in item.platform_code.lower()
                or lowered_keyword in item.platform_name.lower()
                or lowered_keyword in item.connector.lower()
                or lowered_keyword in item.sync_direction.lower()
            ]
        if normalized_updated_start_date is not None:
            items = [item for item in items if item.updated_at[:10] >= normalized_updated_start_date]
        if normalized_updated_end_date is not None:
            items = [item for item in items if item.updated_at[:10] <= normalized_updated_end_date]

        platform_type_options = sorted({item.platform_type for item in cls._INTEGRATION_PLATFORM_CATALOG})
        endpoint_mode_options = sorted({item.endpoint_mode for item in cls._INTEGRATION_PLATFORM_CATALOG})
        status_tags = sorted({item.status for item in cls._INTEGRATION_PLATFORM_CATALOG})
        ui_buttons = [
            "查看",
            "测试连接（guarded）",
            "同步（guarded）",
            "启停（guarded）",
            "导出（disabled）",
            "打印（disabled）",
        ]
        ui_table_headers = [
            "平台编码",
            "平台名称",
            "平台类型",
            "接入模式",
            "连接器",
            "Webhook（脱敏）",
            "同步方向",
            "状态",
            "最近同步",
            "重试策略",
            "更新时间",
            "备注",
        ]
        return SystemIntegrationPlatformData(
            items=items,
            total=len(items),
            platform_type_options=platform_type_options,
            endpoint_mode_options=endpoint_mode_options,
            status_tags=status_tags,
            ui_buttons=ui_buttons,
            ui_table_headers=ui_table_headers,
        )

    @classmethod
    def list_system_announcement_catalog(
        cls,
        *,
        category: str | None,
        status: str | None,
        target_scope: str | None,
        keyword: str | None,
        published_start_date: str | None,
        published_end_date: str | None,
    ) -> SystemAnnouncementData:
        normalized_category = cls._norm(category)
        normalized_status = cls._norm(status)
        normalized_target_scope = cls._norm(target_scope)
        normalized_keyword = cls._norm(keyword)
        normalized_published_start_date = cls._norm(published_start_date)
        normalized_published_end_date = cls._norm(published_end_date)

        items = [item.model_copy(deep=True) for item in cls._SYSTEM_ANNOUNCEMENT_CATALOG]

        if normalized_category is not None:
            items = [item for item in items if item.category == normalized_category]
        if normalized_status is not None:
            items = [item for item in items if item.publish_status == normalized_status]
        if normalized_target_scope is not None:
            items = [item for item in items if item.target_scope == normalized_target_scope]
        if normalized_keyword is not None:
            lowered_keyword = normalized_keyword.lower()
            items = [
                item
                for item in items
                if lowered_keyword in item.announcement_code.lower()
                or lowered_keyword in item.title.lower()
                or lowered_keyword in item.owner.lower()
            ]
        if normalized_published_start_date is not None:
            items = [item for item in items if item.published_at[:10] >= normalized_published_start_date]
        if normalized_published_end_date is not None:
            items = [item for item in items if item.published_at[:10] <= normalized_published_end_date]

        category_options = sorted({item.category for item in cls._SYSTEM_ANNOUNCEMENT_CATALOG})
        status_tags = sorted({item.publish_status for item in cls._SYSTEM_ANNOUNCEMENT_CATALOG})
        ui_buttons = ["查看", "发布（guarded）", "撤回（guarded）", "置顶（guarded）", "导出（disabled）", "打印（disabled）"]
        ui_table_headers = [
            "公告编号",
            "标题",
            "分类",
            "目标范围",
            "发布状态",
            "发布时间",
            "失效时间",
            "优先级",
            "负责人",
            "更新时间",
            "备注",
        ]

        return SystemAnnouncementData(
            items=items,
            total=len(items),
            category_options=category_options,
            status_tags=status_tags,
            ui_buttons=ui_buttons,
            ui_table_headers=ui_table_headers,
        )

    @classmethod
    def list_operation_log_catalog(
        cls,
        *,
        module: str | None,
        operation_type: str | None,
        result_status: str | None,
        operator: str | None,
        keyword: str | None,
        operated_start_date: str | None,
        operated_end_date: str | None,
    ) -> SystemOperationLogData:
        normalized_module = cls._norm(module)
        normalized_operation_type = cls._norm(operation_type)
        normalized_result_status = cls._norm(result_status)
        normalized_operator = cls._norm(operator)
        normalized_keyword = cls._norm(keyword)
        normalized_operated_start_date = cls._norm(operated_start_date)
        normalized_operated_end_date = cls._norm(operated_end_date)

        items = [item.model_copy(deep=True) for item in cls._OPERATION_LOG_CATALOG]

        if normalized_module is not None:
            items = [item for item in items if item.module == normalized_module]
        if normalized_operation_type is not None:
            items = [item for item in items if item.operation_type == normalized_operation_type]
        if normalized_result_status is not None:
            items = [item for item in items if item.result_status == normalized_result_status]
        if normalized_operator is not None:
            items = [item for item in items if normalized_operator in item.operator]
        if normalized_keyword is not None:
            lowered_keyword = normalized_keyword.lower()
            items = [
                item
                for item in items
                if lowered_keyword in item.log_id.lower()
                or lowered_keyword in item.operation_name.lower()
                or lowered_keyword in item.info.lower()
                or lowered_keyword in item.trace_id.lower()
            ]
        if normalized_operated_start_date is not None:
            items = [item for item in items if item.operated_at[:10] >= normalized_operated_start_date]
        if normalized_operated_end_date is not None:
            items = [item for item in items if item.operated_at[:10] <= normalized_operated_end_date]

        module_options = sorted({item.module for item in cls._OPERATION_LOG_CATALOG})
        operation_type_options = sorted({item.operation_type for item in cls._OPERATION_LOG_CATALOG})
        status_tags = sorted({item.result_status for item in cls._OPERATION_LOG_CATALOG})
        ui_buttons = ["查看", "导出（guarded）", "打印（guarded）", "归档（guarded）", "清理（guarded）"]
        ui_table_headers = [
            "日志编号",
            "模块",
            "操作类型",
            "操作名称",
            "详情摘要",
            "操作人",
            "结果状态",
            "操作时间",
            "客户端IP",
            "追踪ID",
            "备注",
        ]
        return SystemOperationLogData(
            items=items,
            total=len(items),
            module_options=module_options,
            operation_type_options=operation_type_options,
            status_tags=status_tags,
            ui_buttons=ui_buttons,
            ui_table_headers=ui_table_headers,
        )

    @classmethod
    def list_document_code_catalog(
        cls,
        *,
        document_type: str | None,
        status: str | None,
        keyword: str | None,
        updated_start_date: str | None,
        updated_end_date: str | None,
    ) -> SystemDocumentCodeData:
        normalized_document_type = cls._norm(document_type)
        normalized_status = cls._norm(status)
        normalized_keyword = cls._norm(keyword)
        normalized_updated_start_date = cls._norm(updated_start_date)
        normalized_updated_end_date = cls._norm(updated_end_date)

        items = [item.model_copy(deep=True) for item in cls._DOCUMENT_CODE_CATALOG]

        if normalized_document_type is not None:
            items = [item for item in items if item.document_type == normalized_document_type]
        if normalized_status is not None:
            items = [item for item in items if item.status == normalized_status]
        if normalized_keyword is not None:
            lowered_keyword = normalized_keyword.lower()
            items = [
                item
                for item in items
                if lowered_keyword in item.document_code_id.lower()
                or lowered_keyword in item.document_name.lower()
                or lowered_keyword in item.prefix.lower()
                or lowered_keyword in item.serial_rule.lower()
                or lowered_keyword in item.owner.lower()
            ]
        if normalized_updated_start_date is not None:
            items = [item for item in items if item.updated_at[:10] >= normalized_updated_start_date]
        if normalized_updated_end_date is not None:
            items = [item for item in items if item.updated_at[:10] <= normalized_updated_end_date]

        document_type_options = sorted({item.document_type for item in cls._DOCUMENT_CODE_CATALOG})
        status_tags = sorted({item.status for item in cls._DOCUMENT_CODE_CATALOG})
        ui_buttons = [
            "查看",
            "新增（guarded）",
            "编辑（guarded）",
            "启停（guarded）",
            "预览（guarded）",
            "重置（guarded）",
            "导出（disabled）",
            "打印（disabled）",
        ]
        ui_table_headers = [
            "编码编号",
            "单据名称",
            "单据类型",
            "编码前缀",
            "流水规则",
            "当前流水号",
            "状态",
            "重置周期",
            "负责人",
            "更新时间",
            "备注",
        ]

        return SystemDocumentCodeData(
            items=items,
            total=len(items),
            document_type_options=document_type_options,
            status_tags=status_tags,
            ui_buttons=ui_buttons,
            ui_table_headers=ui_table_headers,
        )

    @staticmethod
    def _norm(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
