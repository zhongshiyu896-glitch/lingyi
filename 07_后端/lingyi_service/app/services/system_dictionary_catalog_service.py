"""Readonly static dictionary catalog service for system management (TASK-080C)."""

from __future__ import annotations

from app.schemas.system_management import SystemDictionaryCatalogData
from app.schemas.system_management import SystemDictionaryCatalogItemData


_ALLOWED_STATUS = {"active", "inactive", "deprecated"}


class SystemDictionaryCatalogService:
    """Serve local static dictionary catalog metadata only."""

    _CATALOG: tuple[SystemDictionaryCatalogItemData, ...] = (
        SystemDictionaryCatalogItemData(
            dict_type="system_region",
            dict_code="CN-ZJ-HZ",
            dict_name="杭州",
            status="active",
            source="static_registry",
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemDictionaryCatalogItemData(
            dict_type="system_region",
            dict_code="CN-SH-PD",
            dict_name="上海浦东",
            status="active",
            source="static_registry",
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemDictionaryCatalogItemData(
            dict_type="currency",
            dict_code="CNY",
            dict_name="人民币",
            status="active",
            source="policy_registry",
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemDictionaryCatalogItemData(
            dict_type="currency",
            dict_code="USD",
            dict_name="美元",
            status="inactive",
            source="policy_registry",
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemDictionaryCatalogItemData(
            dict_type="size_group",
            dict_code="APPAREL_ADULT",
            dict_name="成人尺码组",
            status="active",
            source="static_registry",
            updated_at="2026-04-21T00:00:00Z",
        ),
        SystemDictionaryCatalogItemData(
            dict_type="size_group",
            dict_code="APPAREL_CHILD",
            dict_name="儿童尺码组",
            status="deprecated",
            source="policy_registry",
            updated_at="2026-04-21T00:00:00Z",
        ),
    )

    @classmethod
    def list_catalog(
        cls,
        *,
        dict_type: str | None,
        status: str | None,
        source: str | None,
    ) -> SystemDictionaryCatalogData:
        normalized_type = cls._norm(dict_type)
        normalized_status = cls._norm(status)
        normalized_source = cls._norm(source)

        if normalized_status is not None and normalized_status not in _ALLOWED_STATUS:
            raise ValueError("status 不合法")

        items = [item.model_copy(deep=True) for item in cls._CATALOG]

        if normalized_type is not None:
            items = [item for item in items if item.dict_type == normalized_type]
        if normalized_status is not None:
            items = [item for item in items if item.status == normalized_status]
        if normalized_source is not None:
            items = [item for item in items if item.source == normalized_source]

        return SystemDictionaryCatalogData(items=items, total=len(items))

    @staticmethod
    def _norm(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
