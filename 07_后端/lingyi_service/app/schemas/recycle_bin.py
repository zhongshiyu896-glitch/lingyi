"""Schemas for the unified recycle bin."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field


class ApiResponse(BaseModel):
    """Standard API envelope."""

    code: str
    message: str
    data: object | None = None


class RecycleBinItem(BaseModel):
    """One recoverable deletion snapshot."""

    id: int
    module: str
    entity_type: str
    entity_path: str | None = None
    original_id: int
    company: str | None = None
    code: str | None = None
    name: str | None = None
    status: Literal["deleted", "restored"]
    snapshot: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    deleted_by: str
    deleted_at: datetime | None = None
    restored_by: str | None = None
    restored_at: datetime | None = None


class RecycleBinListData(BaseModel):
    """Paginated recycle-bin list."""

    items: list[RecycleBinItem]
    total: int
    page: int
    page_size: int
