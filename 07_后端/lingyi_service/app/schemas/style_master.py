"""Pydantic schemas for FastAPI-native style master data."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

StyleStatus = Literal["draft", "enabled", "disabled"]
StyleDictionaryType = Literal["season", "year", "brand", "color", "size"]
StyleDictionaryStatus = Literal["active", "inactive"]
StyleGalleryImageType = Literal["main", "detail", "color", "process", "other"]
StyleSkuStatus = Literal["active", "inactive"]


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
    primary_image_url: str | None = None
    primary_thumbnail_url: str | None = None
    gallery_count: int = 0
    sku_count: int = 0
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


class StyleGalleryCreateRequest(BaseModel):
    """Create one uploaded-image-backed style gallery record."""

    operation: Literal["create"] = "create"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    style_master_id: int = Field(..., gt=0)
    image_url: str = Field(..., min_length=1, max_length=2048)
    thumbnail_url: str | None = Field(default=None, max_length=2048)
    image_name: str | None = Field(default=None, max_length=255)
    image_type: StyleGalleryImageType = "main"
    is_primary: bool = False


class StyleGalleryUpdateRequest(BaseModel):
    """Update one style gallery record."""

    operation: Literal["update"] = "update"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    image_url: str | None = Field(default=None, min_length=1, max_length=2048)
    thumbnail_url: str | None = Field(default=None, max_length=2048)
    image_name: str | None = Field(default=None, max_length=255)
    image_type: StyleGalleryImageType | None = None
    is_primary: bool | None = None


class StyleGalleryDeactivateRequest(BaseModel):
    """Deactivate one style gallery record."""

    operation: Literal["deactivate"] = "deactivate"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    reason: str = Field(default="前端款式图库页停用", min_length=1, max_length=255)


class StyleGalleryItem(BaseModel):
    """Style gallery card returned to frontend pages."""

    id: int
    company: str
    style_master_id: int
    ys_style_no: str
    ys_style_name_cn: str
    image_url: str
    thumbnail_url: str | None = None
    image_name: str | None = None
    image_type: StyleGalleryImageType
    is_primary: bool
    designer: str | None = None
    style_type: str | None = None
    created_by: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StyleGalleryListData(BaseModel):
    """Paginated style gallery response."""

    items: list[StyleGalleryItem]
    total: int
    page: int
    page_size: int


class StyleSkuPayload(BaseModel):
    """One style color-size SKU matrix row payload."""

    color_code: str = Field(..., min_length=1, max_length=64)
    color_name: str | None = Field(default=None, max_length=140)
    size_code: str = Field(..., min_length=1, max_length=64)
    size_name: str | None = Field(default=None, max_length=140)
    sku_code: str = Field(..., min_length=1, max_length=180)
    barcode: str | None = Field(default=None, max_length=180)
    status: StyleSkuStatus = "active"
    sort_no: int = Field(default=10, ge=0)


class StyleSkuUpsertRequest(BaseModel):
    """Replace the style color-size SKU matrix."""

    operation: Literal["upsert"] = "upsert"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    items: list[StyleSkuPayload] = Field(..., min_length=1)


class StyleSkuItem(BaseModel):
    """One style color-size SKU matrix row."""

    id: int
    company: str
    style_master_id: int
    ys_style_no: str
    color_code: str
    color_name: str
    size_code: str
    size_name: str
    sku_code: str
    barcode: str | None = None
    status: StyleSkuStatus
    sort_no: int
    created_by: str
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None


class StyleSkuListData(BaseModel):
    """Style color-size SKU matrix response."""

    style_master_id: int
    ys_style_no: str
    items: list[StyleSkuItem]
    total: int


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


class StyleMaterialBomItemPayload(BaseModel):
    """Style material BOM line payload."""

    material_item_code: str = Field(..., min_length=1, max_length=140)
    color: str | None = Field(default=None, max_length=64)
    size: str | None = Field(default=None, max_length=64)
    part: str | None = Field(default=None, max_length=100)
    qty_per_piece: Decimal = Field(..., gt=0)
    loss_rate: Decimal = Field(default=Decimal("0"), ge=0)
    uom: str = Field(..., min_length=1, max_length=32)
    remark: str | None = Field(default=None, max_length=500)


class StyleMaterialBomOperationPayload(BaseModel):
    """Style material BOM operation payload."""

    process_name: str = Field(..., min_length=1, max_length=100)
    sequence_no: int = Field(..., ge=1)
    is_subcontract: bool = False
    wage_rate: Decimal | None = None
    subcontract_cost_per_piece: Decimal | None = None
    remark: str | None = Field(default=None, max_length=500)


class StyleMaterialBomUpsertRequest(BaseModel):
    """Upsert style material BOM."""

    operation: Literal["upsert"] = "upsert"
    company: str = Field(default="默认公司", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    version_no: str = Field(default="V1", min_length=1, max_length=32)
    items: list[StyleMaterialBomItemPayload] = Field(...)
    operations: list[StyleMaterialBomOperationPayload] | None = None


class StyleMaterialBomExplodeRequest(BaseModel):
    """Explode style material BOM."""

    order_qty: Decimal = Field(..., gt=0)


class StyleMaterialBomHeader(BaseModel):
    """Style material BOM header."""

    id: int
    bom_no: str
    company: str
    style_master_id: int
    item_code: str
    version_no: str
    is_default: bool
    status: str
    updated_at: datetime | None = None


class StyleMaterialBomItem(BaseModel):
    """Style material BOM line."""

    id: int
    material_item_code: str
    material_name: str | None = None
    color: str | None = None
    size: str | None = None
    part: str | None = None
    qty_per_piece: Decimal
    loss_rate: Decimal
    uom: str
    remark: str | None = None


class StyleMaterialBomOperation(BaseModel):
    """Style material BOM operation."""

    id: int
    process_name: str
    sequence_no: int
    is_subcontract: bool
    wage_rate: Decimal | None = None
    subcontract_cost_per_piece: Decimal | None = None
    remark: str | None = None


class StyleMaterialBomData(BaseModel):
    """Style material BOM response."""

    bom: StyleMaterialBomHeader | None = None
    items: list[StyleMaterialBomItem] = Field(default_factory=list)
    operations: list[StyleMaterialBomOperation] = Field(default_factory=list)


class StyleMaterialBomRequirementItem(BaseModel):
    """Style material BOM explode row."""

    material_item_code: str
    color: str | None = None
    size: str | None = None
    part: str | None = None
    uom: str
    qty_per_piece: Decimal
    loss_rate: Decimal
    required_qty: Decimal


class StyleMaterialBomExplodeData(BaseModel):
    """Style material BOM explode response."""

    style_master_id: int
    item_code: str
    order_qty: Decimal
    items: list[StyleMaterialBomRequirementItem]
    total_required_qty: Decimal
