"""Readonly static config catalog service for system management (TASK-080B)."""

from __future__ import annotations

from app.schemas.system_management import SystemConfigCatalogData
from app.schemas.system_management import SystemConfigCatalogItemData


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

    @staticmethod
    def _norm(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
