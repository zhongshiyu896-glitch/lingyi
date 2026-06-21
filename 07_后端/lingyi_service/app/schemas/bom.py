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
    part: Optional[str] = Field(default=None, max_length=100)
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

    scenario_tag: str = Field(..., min_length=1, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    source_ref: str = Field(..., min_length=1, max_length=140)
    company: Optional[str] = Field(default=None, min_length=1, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)
    version_no: str = Field(..., min_length=1, max_length=32)
    bom_items: List[BomItemPayload] = Field(..., min_length=1)
    operations: List[BomOperationPayload] = Field(..., min_length=1)


class BomUpdateRequest(BaseModel):
    """Update draft BOM request payload."""

    scenario_tag: str = Field(..., min_length=1, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    source_ref: str = Field(..., min_length=1, max_length=140)
    bom_no: str = Field(..., min_length=1, max_length=180)
    company: Optional[str] = Field(default=None, min_length=1, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)
    version_no: str = Field(..., min_length=1, max_length=32)
    bom_items: List[BomItemPayload] = Field(..., min_length=1)
    operations: List[BomOperationPayload] = Field(..., min_length=1)


class BomDeactivateRequest(BaseModel):
    """Deactivate BOM request payload."""

    scenario_tag: str = Field(..., min_length=1, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    source_ref: str = Field(..., min_length=1, max_length=140)
    bom_no: str = Field(..., min_length=1, max_length=180)
    company: Optional[str] = Field(default=None, min_length=1, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)
    reason: str = Field(..., min_length=1, max_length=300)


class BomCarrierRequest(BaseModel):
    """BOM write carrier payload for action endpoints."""

    scenario_tag: str = Field(..., min_length=1, max_length=64)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    source_ref: str = Field(..., min_length=1, max_length=140)
    bom_no: str = Field(..., min_length=1, max_length=180)
    company: Optional[str] = Field(default=None, min_length=1, max_length=140)
    item_code: str = Field(..., min_length=1, max_length=140)


class BomListQuery(BaseModel):
    """BOM list query params."""

    company: Optional[str] = None
    item_code: Optional[str] = None
    keyword: Optional[str] = Field(default=None, max_length=140)
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class BomMaterialGalleryQuery(BaseModel):
    """BOM material gallery query params."""

    item_code: Optional[str] = None
    material_item_code: Optional[str] = None
    color: Optional[str] = None
    size: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomFabricQuery(BaseModel):
    """BOM fabric query params."""

    item_code: Optional[str] = None
    material_item_code: Optional[str] = None
    fabric_name: Optional[str] = None
    color: Optional[str] = None
    specification: Optional[str] = None
    supplier_name: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class BomAccessoriesPackagingQuery(BaseModel):
    """BOM accessories/packaging query params."""

    item_code: Optional[str] = None
    material_item_code: Optional[str] = None
    material_name: Optional[str] = None
    category: Optional[str] = None
    supplier_name: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class BomPurchaseOrderQuery(BaseModel):
    """BOM purchase order query params."""

    purchase_no: Optional[str] = None
    supplier_name: Optional[str] = None
    material_keyword: Optional[str] = None
    status: Optional[str] = None
    delivery_date_from: Optional[date] = None
    delivery_date_to: Optional[date] = None
    min_qty: Optional[Decimal] = Field(default=None, ge=0)
    max_qty: Optional[Decimal] = Field(default=None, ge=0)
    min_amount: Optional[Decimal] = Field(default=None, ge=0)
    max_amount: Optional[Decimal] = Field(default=None, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomMaterialRequestItem(BaseModel):
    """Material request projection backed by FastAPI purchase requirements."""

    request_no: str
    company: str
    item_code: str
    material_item_code: str
    supplier_name: str
    qty: Decimal
    uom: str
    expected_delivery_date: Optional[date] = None
    status: str
    bom_no: str


class BomMaterialRequestData(BaseModel):
    """Paginated material request payload."""

    items: List[BomMaterialRequestItem]
    total: int
    page: int
    page_size: int


class BomProcessingTypeQuery(BaseModel):
    """BOM processing-type query params."""

    item_code: Optional[str] = None
    process_type_name: Optional[str] = None
    process_name: Optional[str] = None
    subcontract_mode: Optional[str] = None
    pricing_mode: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomMaterialProcessingQuery(BaseModel):
    """BOM material-processing query params."""

    item_code: Optional[str] = None
    process_no: Optional[str] = None
    process_name: Optional[str] = None
    processing_supplier: Optional[str] = None
    processing_mode: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomMaterialProcessingInboundQuery(BaseModel):
    """BOM material-processing inbound query params."""

    item_code: Optional[str] = None
    inbound_no: Optional[str] = None
    material_item_code: Optional[str] = None
    processing_supplier: Optional[str] = None
    warehouse_name: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomMaterialDeductionQuery(BaseModel):
    """BOM material-deduction query params."""

    item_code: Optional[str] = None
    deduction_no: Optional[str] = None
    material_item_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomMaterialSalesOutboundQuery(BaseModel):
    """BOM material-sales-outbound query params."""

    item_code: Optional[str] = None
    outbound_no: Optional[str] = None
    sales_order_no: Optional[str] = None
    customer_name: Optional[str] = None
    warehouse_name: Optional[str] = None
    material_item_code: Optional[str] = None
    status: Optional[str] = None
    audit_status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)


class BomMaterialTypeQuery(BaseModel):
    """BOM material-type query params."""

    item_code: Optional[str] = None
    material_item_code: Optional[str] = None
    material_type_name: Optional[str] = None
    material_group: Optional[str] = None
    applicable_scene: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class BomMaterialUnitQuery(BaseModel):
    """BOM material-unit query params."""

    item_code: Optional[str] = None
    material_item_code: Optional[str] = None
    unit_name: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class BomExplodeRequest(BaseModel):
    """BOM explode request payload."""

    scenario_tag: Optional[str] = Field(default=None, min_length=1, max_length=64)
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=140)
    source_ref: Optional[str] = Field(default=None, min_length=1, max_length=140)
    bom_no: Optional[str] = Field(default=None, min_length=1, max_length=180)
    item_code: Optional[str] = Field(default=None, min_length=1, max_length=140)
    order_qty: Decimal = Field(..., gt=0)
    size_ratio: Dict[str, Decimal] = Field(default_factory=dict)


class BomHeader(BaseModel):
    """BOM header payload."""

    id: int
    bom_no: str
    company: str
    style_master_id: Optional[int] = None
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
    part: Optional[str] = None
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
    company: str
    style_master_id: Optional[int] = None
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


class BomMaterialGalleryItem(BaseModel):
    """Material gallery list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    material_item_code: str
    category: str
    color: Optional[str]
    size: Optional[str]
    uom: str
    qty_per_piece: Decimal
    loss_rate: Decimal
    status: str
    is_default: bool
    thumbnail_url: Optional[str]


class BomMaterialGalleryData(BaseModel):
    """Material gallery response data."""

    items: List[BomMaterialGalleryItem]
    total: int
    page: int
    page_size: int


class BomFabricItem(BaseModel):
    """Fabric list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    material_item_code: str
    fabric_name: str
    color: Optional[str]
    specification: Optional[str]
    supplier_name: str
    uom: str
    qty_per_piece: Decimal
    loss_rate: Decimal
    status: str
    is_default: bool


class BomFabricData(BaseModel):
    """Fabric response data."""

    items: List[BomFabricItem]
    total: int
    page: int
    page_size: int


class BomAccessoriesPackagingItem(BaseModel):
    """Accessories/packaging list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    material_item_code: str
    material_name: str
    category: str
    color: Optional[str]
    specification: Optional[str]
    supplier_name: str
    uom: str
    qty_per_piece: Decimal
    loss_rate: Decimal
    status: str
    is_default: bool


class BomAccessoriesPackagingData(BaseModel):
    """Accessories/packaging response data."""

    items: List[BomAccessoriesPackagingItem]
    total: int
    page: int
    page_size: int


class BomPurchaseOrderItem(BaseModel):
    """Purchase order list row payload."""

    id: int
    bom_id: int
    purchase_no: str
    supplier_name: str
    item_code: str
    material_item_code: str
    material_name: str
    qty: Decimal
    uom: str
    unit_price: Decimal
    total_amount: Decimal
    expected_delivery_date: Optional[date]
    status: str
    bom_no: str


class BomPurchaseOrderData(BaseModel):
    """Purchase order response data."""

    items: List[BomPurchaseOrderItem]
    total: int
    page: int
    page_size: int


class BomProcessingTypeItem(BaseModel):
    """Processing-type list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    process_type_code: str
    process_type_name: str
    process_name: str
    sequence_no: int
    subcontract_mode: str
    pricing_mode: str
    unit_rate: Decimal
    status: str
    is_default: bool


class BomProcessingTypeData(BaseModel):
    """Processing-type response data."""

    items: List[BomProcessingTypeItem]
    total: int
    page: int
    page_size: int


class FoundationTemplateNodeItem(BaseModel):
    """Foundation template node payload."""

    id: int
    template_id: int
    code: str
    name: str
    node_type: str
    required: bool
    status: str
    sort_no: int
    owner: str
    created_by: str
    created_at: str
    updated_at: str | None = None


class FoundationTemplateItem(BaseModel):
    """Foundation template payload for workmanship and size spec templates."""

    id: int
    company: str
    template_type: str
    template_code: str
    name: str
    scene: str
    status: str
    version: int
    created_by: str
    created_at: str
    updated_at: str | None = None
    nodes: List[FoundationTemplateNodeItem] = Field(default_factory=list)


class FoundationTemplateListData(BaseModel):
    """Foundation template paginated data."""

    items: List[FoundationTemplateItem]
    total: int
    page: int
    page_size: int


class FoundationTemplateCreateRequest(BaseModel):
    """Create a foundation template."""

    operation: str = Field(default="create")
    company: str = Field(..., min_length=1, max_length=140)
    template_code: Optional[str] = Field(default=None, max_length=140)
    name: str = Field(..., min_length=1, max_length=255)
    scene: str = Field(default="业务配置", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class FoundationTemplateUpdateRequest(BaseModel):
    """Update a foundation template."""

    operation: str = Field(default="update")
    company: str = Field(..., min_length=1, max_length=140)
    template_code: Optional[str] = Field(default=None, min_length=1, max_length=140)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    scene: Optional[str] = Field(default=None, min_length=1, max_length=140)
    status: Optional[str] = Field(default=None, min_length=1, max_length=16)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class FoundationTemplateDeactivateRequest(BaseModel):
    """Deactivate a foundation template."""

    operation: str = Field(default="deactivate")
    company: str = Field(..., min_length=1, max_length=140)
    reason: str = Field(..., min_length=1, max_length=300)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class FoundationTemplateNodeCreateRequest(BaseModel):
    """Create a template node."""

    operation: str = Field(default="create_node")
    company: str = Field(..., min_length=1, max_length=140)
    code: Optional[str] = Field(default=None, max_length=140)
    name: str = Field(..., min_length=1, max_length=255)
    node_type: str = Field(..., min_length=1, max_length=100)
    required: bool = False
    sort_no: int = Field(default=10, ge=0)
    owner: str = Field(default="业务", min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class FoundationTemplateNodeUpdateRequest(BaseModel):
    """Update a template node."""

    operation: str = Field(default="update_node")
    company: str = Field(..., min_length=1, max_length=140)
    code: Optional[str] = Field(default=None, min_length=1, max_length=140)
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    node_type: Optional[str] = Field(default=None, min_length=1, max_length=100)
    required: Optional[bool] = None
    status: Optional[str] = Field(default=None, min_length=1, max_length=16)
    sort_no: Optional[int] = Field(default=None, ge=0)
    owner: Optional[str] = Field(default=None, min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class FoundationTemplateNodeDeactivateRequest(BaseModel):
    """Deactivate a template node."""

    operation: str = Field(default="deactivate_node")
    company: str = Field(..., min_length=1, max_length=140)
    reason: str = Field(default="停用节点", min_length=1, max_length=300)
    idempotency_key: str = Field(..., min_length=1, max_length=140)


class BomMaterialProcessingItem(BaseModel):
    """Material-processing list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    process_no: str
    process_name: str
    processing_supplier: str
    processing_mode: str
    planned_qty: Decimal
    completed_qty: Decimal
    pending_qty: Decimal
    scrap_qty: Decimal
    uom: str
    due_date: Optional[date]
    status: str
    is_default: bool


class BomMaterialProcessingData(BaseModel):
    """Material-processing response data."""

    items: List[BomMaterialProcessingItem]
    total: int
    page: int
    page_size: int


class BomMaterialProcessingInboundItem(BaseModel):
    """Material-processing inbound list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    inbound_no: str
    process_no: str
    material_item_code: str
    processing_supplier: str
    warehouse_name: str
    inbound_qty: Decimal
    inspected_qty: Decimal
    pending_inspection_qty: Decimal
    inbound_date: Optional[date]
    status: str
    is_default: bool


class BomMaterialProcessingInboundData(BaseModel):
    """Material-processing inbound response data."""

    items: List[BomMaterialProcessingInboundItem]
    total: int
    page: int
    page_size: int


class BomMaterialDeductionItem(BaseModel):
    """Material-deduction list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    deduction_no: str
    process_no: str
    material_item_code: str
    warehouse_name: str
    deduction_qty: Decimal
    deducted_qty: Decimal
    pending_deduction_qty: Decimal
    deduction_date: Optional[date]
    status: str
    is_default: bool


class BomMaterialDeductionData(BaseModel):
    """Material-deduction response data."""

    items: List[BomMaterialDeductionItem]
    total: int
    page: int
    page_size: int


class BomMaterialSalesOutboundItem(BaseModel):
    """Material-sales-outbound list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    outbound_no: str
    sales_order_no: str
    customer_name: str
    warehouse_name: str
    material_item_code: str
    material_name: str
    color: Optional[str] = None
    size: Optional[str] = None
    batch_no: str
    planned_outbound_qty: Decimal
    outbound_qty: Decimal
    pending_outbound_qty: Decimal
    outbound_date: Optional[date]
    status: str
    audit_status: str
    applicant_name: str
    updated_at: Optional[str] = None
    is_default: bool


class BomMaterialSalesOutboundData(BaseModel):
    """Material-sales-outbound response data."""

    items: List[BomMaterialSalesOutboundItem]
    total: int
    page: int
    page_size: int


class BomMaterialTypeItem(BaseModel):
    """Material-type list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    material_item_code: str
    material_type_code: str
    material_type_name: str
    material_group: str
    applicable_scene: str
    supplier_name: str
    status: str
    is_default: bool


class BomMaterialTypeData(BaseModel):
    """Material-type response data."""

    items: List[BomMaterialTypeItem]
    total: int
    page: int
    page_size: int


class BomMaterialUnitItem(BaseModel):
    """Material-unit list row payload."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    material_item_code: str
    unit_code: str
    unit_name: str
    base_unit: str
    conversion_text: str
    precision: int
    status: str
    is_default: bool


class BomMaterialUnitData(BaseModel):
    """Material-unit response data."""

    items: List[BomMaterialUnitItem]
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
    part: Optional[str] = None
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
