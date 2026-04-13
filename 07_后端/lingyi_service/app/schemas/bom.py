"""Pydantic schemas for BOM module (TASK-001)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from pydantic import BaseModel
from pydantic import Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Unified API response envelope."""

    code: str
    message: str
    data: T


class BomItemPayload(BaseModel):
    """BOM material item payload."""

    material_item_code: str = Field(..., min_length=1, max_length=140)
    color: Optional[str] = None
    size: Optional[str] = None
    qty_per_piece: Decimal = Field(..., gt=0)
    loss_rate: Decimal = Field(default=Decimal("0"), ge=0)
    uom: str = Field(..., min_length=1, max_length=32)
    remark: Optional[str] = None


class BomOperationPayload(BaseModel):
    """BOM operation payload."""

    process_name: str = Field(..., min_length=1, max_length=100)
    sequence_no: int = Field(..., ge=1)
    is_subcontract: bool = False
    wage_rate: Optional[Decimal] = None
    subcontract_cost_per_piece: Optional[Decimal] = None
    remark: Optional[str] = None


class BomCreateRequest(BaseModel):
    """Create BOM request payload."""

    item_code: str = Field(..., min_length=1, max_length=140)
    version_no: str = Field(..., min_length=1, max_length=32)
    bom_items: List[BomItemPayload] = Field(..., min_length=1)
    operations: List[BomOperationPayload] = Field(..., min_length=1)


class BomUpdateRequest(BaseModel):
    """Update draft BOM request payload."""

    version_no: str = Field(..., min_length=1, max_length=32)
    bom_items: List[BomItemPayload] = Field(..., min_length=1)
    operations: List[BomOperationPayload] = Field(..., min_length=1)


class BomDeactivateRequest(BaseModel):
    """Deactivate BOM request payload."""

    reason: str = Field(..., min_length=1, max_length=300)


class BomListQuery(BaseModel):
    """BOM list query params."""

    item_code: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomExplodeRequest(BaseModel):
    """BOM explode request payload."""

    order_qty: Decimal = Field(..., gt=0)
    size_ratio: Dict[str, Decimal] = Field(default_factory=dict)


class BomHeader(BaseModel):
    """BOM header payload."""

    id: int
    bom_no: str
    item_code: str
    version_no: str
    is_default: bool
    status: str
    effective_date: Optional[date]


class BomItemView(BaseModel):
    """BOM item output payload."""

    id: int
    material_item_code: str
    color: Optional[str]
    size: Optional[str]
    qty_per_piece: Decimal
    loss_rate: Decimal
    uom: str
    remark: Optional[str]


class BomOperationView(BaseModel):
    """BOM operation output payload."""

    id: int
    process_name: str
    sequence_no: int
    is_subcontract: bool
    wage_rate: Optional[Decimal]
    subcontract_cost_per_piece: Optional[Decimal]
    remark: Optional[str]


class BomListItem(BaseModel):
    """BOM list row payload."""

    id: int
    bom_no: str
    item_code: str
    version_no: str
    is_default: bool
    status: str
    effective_date: Optional[date]


class BomListData(BaseModel):
    """BOM list response data."""

    items: List[BomListItem]
    total: int
    page: int
    page_size: int


class BomDetailData(BaseModel):
    """BOM detail response data."""

    bom: BomHeader
    items: List[BomItemView]
    operations: List[BomOperationView]


class BomNameData(BaseModel):
    """Simple response containing BOM identifier."""

    name: str


class BomSetDefaultData(BaseModel):
    """Set default response data."""

    name: str
    item_code: str
    is_default: bool


class BomUpdateData(BaseModel):
    """BOM update response data."""

    name: str
    status: str
    updated_at: str


class BomActivateData(BaseModel):
    """BOM activate response data."""

    name: str
    status: str
    effective_date: Optional[date]


class BomDeactivateData(BaseModel):
    """BOM deactivate response data."""

    name: str
    status: str


class ExplodedMaterialItem(BaseModel):
    """Exploded material requirement row."""

    material_item_code: str
    color: Optional[str]
    size: Optional[str]
    uom: str
    qty: Decimal


class ExplodedOperationCost(BaseModel):
    """Exploded operation cost row."""

    process_name: str
    is_subcontract: bool
    unit_cost: Decimal
    total_cost: Decimal


class BomExplodeData(BaseModel):
    """BOM explode response data."""

    material_requirements: List[ExplodedMaterialItem]
    operation_costs: List[ExplodedOperationCost]
    total_material_qty: Decimal
    total_operation_cost: Decimal
