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
