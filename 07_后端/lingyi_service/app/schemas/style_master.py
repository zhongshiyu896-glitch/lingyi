"""Pydantic schemas for FastAPI-native style master data."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

StyleStatus = Literal["draft", "enabled", "disabled"]
StyleDictionaryType = Literal["season", "year", "brand", "color", "size"]
StyleDictionaryStatus = Literal["active", "inactive"]


class ApiResponse(BaseModel):
    """Standard API envelope."""

    code: str
    message: str
    data: object | None = None


class StyleColorItem(BaseModel):
    """Color option on a style."""

    ys_color_code: str = Field(..., min_length=1, max_length=64)
    ys_color_name: str = Field(..., min_length=1, max_length=140)


class StyleSizeItem(BaseModel):
    """Size option on a style."""

    ys_size_code: str = Field(..., min_length=1, max_length=64)
    ys_size_name: str = Field(..., min_length=1, max_length=140)


class StyleMasterWriteBase(BaseModel):
    """Mutable style master fields."""

    company: str = Field(default="默认公司", min_length=1, max_length=140)
    ys_style_no: str = Field(..., min_length=1, max_length=140)
    ys_style_name_cn: str = Field(..., min_length=1, max_length=255)
    ys_season: str = Field(..., min_length=1, max_length=140)
    ys_year: str = Field(..., min_length=1, max_length=32)
    ys_brand: str = Field(..., min_length=1, max_length=140)
    ys_style_status: StyleStatus = "draft"
    colors: list[StyleColorItem] = Field(default_factory=list)
    sizes: list[StyleSizeItem] = Field(default_factory=list)


class StyleMasterCreateRequest(StyleMasterWriteBase):
    """Create style master."""

    operation: Literal["create"] = "create"
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class StyleMasterUpdateRequest(BaseModel):
    """Update style master."""

    operation: Literal["update"] = "update"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    ys_style_no: str | None = Field(default=None, min_length=1, max_length=140)
    ys_style_name_cn: str | None = Field(default=None, min_length=1, max_length=255)
    ys_season: str | None = Field(default=None, min_length=1, max_length=140)
    ys_year: str | None = Field(default=None, min_length=1, max_length=32)
    ys_brand: str | None = Field(default=None, min_length=1, max_length=140)
    ys_style_status: StyleStatus | None = None
    colors: list[StyleColorItem] | None = None
    sizes: list[StyleSizeItem] | None = None


class StyleMasterDeactivateRequest(BaseModel):
    """Disable style master."""

    operation: Literal["deactivate"] = "deactivate"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    reason: str = Field(..., min_length=1, max_length=255)


class StyleMasterItem(BaseModel):
    """Style master row returned to frontend pages."""

    id: int
    company: str
    ys_style_no: str
    ys_style_name_cn: str
    ys_season: str
    ys_year: str
    ys_brand: str
    ys_style_status: StyleStatus
    colors: list[StyleColorItem]
    sizes: list[StyleSizeItem]
    source: Literal["fastapi_style_master"] = "fastapi_style_master"
    version: int
    created_by: str
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None
    disabled_by: str | None = None
    disabled_at: datetime | None = None
    disable_reason: str | None = None


class StyleMasterListData(BaseModel):
    """Paginated style master response."""

    items: list[StyleMasterItem]
    total: int
    page: int
    page_size: int


class StyleDictionaryCreateRequest(BaseModel):
    """Create one minimal style dictionary entry."""

    operation: Literal["create"] = "create"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    dict_type: StyleDictionaryType
    code: str = Field(..., min_length=1, max_length=140)
    name: str = Field(..., min_length=1, max_length=255)
    sort_no: int = Field(default=10, ge=0)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class StyleDictionaryUpdateRequest(BaseModel):
    """Update one minimal style dictionary entry."""

    operation: Literal["update"] = "update"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    code: str | None = Field(default=None, min_length=1, max_length=140)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sort_no: int | None = Field(default=None, ge=0)
    status: StyleDictionaryStatus | None = None


class StyleDictionaryDeactivateRequest(BaseModel):
    """Deactivate one dictionary entry."""

    operation: Literal["deactivate"] = "deactivate"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    reason: str = Field(..., min_length=1, max_length=255)


class StyleDictionaryItem(BaseModel):
    """Dictionary row returned to frontend pages."""

    id: int
    company: str
    dict_type: StyleDictionaryType
    code: str
    name: str
    status: StyleDictionaryStatus
    disabled: bool
    sort_no: int
    source: Literal["fastapi_style_dictionary"] = "fastapi_style_dictionary"
    version: int
    created_by: str
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None
    deactivated_by: str | None = None
    deactivated_at: datetime | None = None
    deactivate_reason: str | None = None


class StyleDictionaryListData(BaseModel):
    """Paginated style dictionary response."""

    items: list[StyleDictionaryItem]
    total: int
    page: int
    page_size: int
