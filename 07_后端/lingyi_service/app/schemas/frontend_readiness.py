"""Schemas for development-only frontend readiness read endpoints."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Generic
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class FrontendReadinessListData(BaseModel, Generic[T]):
    """Standard paginated list payload."""

    items: list[T]
    total: int
    page: int
    page_size: int


class FrontendFactoryItem(BaseModel):
    """Factory fields already used by factory statement read schemas."""

    company: str
    supplier: str
    factory_name: str
    factory_code: str
    review_status: str
    follow_up_status: str


class FrontendCashierAccountItem(BaseModel):
    """Cashier account fields already used by factory statement bank rows."""

    bank_name: str
    account_name: str
    account_no: str
    currency: str
    owner: str
    remark: str


class FrontendProcessRequirementTemplateItem(BaseModel):
    """Process requirement template fields from BOM processing type rows."""

    process_type_code: str
    process_type_name: str
    process_name: str
    sequence_no: int
    subcontract_mode: str
    pricing_mode: str
    unit_rate: Decimal
    status: str
    is_default: bool


class FrontendFollowupTemplateItem(BaseModel):
    """Production follow-up template fields."""

    template_id: int
    template_no: str
    template_name: str
    template_type: str
    trigger_node: str
    followup_role: str
    followup_frequency: str
    sla_hours: int
    item_code: str
    company: str
    status: str
    updated_at: datetime


class FrontendMaterialItem(BaseModel):
    """Material master projection based on BOM material-type fields."""

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


class FrontendStyleItem(BaseModel):
    """Style master projection reusing BOM list fields."""

    id: int
    bom_no: str
    item_code: str
    version_no: str
    is_default: bool
    status: str
    effective_date: date | None


class FrontendDictionaryItem(BaseModel):
    """Development dictionary row used by BOM and finance reference lists."""

    dict_type: str
    dict_code: str
    dict_name: str
    status: str
    source: str
    updated_at: str


class FrontendStyleBomProcessItem(BaseModel):
    """Style, BOM and process association projection."""

    id: int
    bom_id: int
    bom_no: str
    item_code: str
    version_no: str
    process_type_code: str
    process_type_name: str
    process_name: str
    sequence_no: int
    subcontract_mode: str
    pricing_mode: str
    unit_rate: Decimal
    status: str
    is_default: bool


class FrontendSampleProgressItem(BaseModel):
    """Sample progress list projection."""

    id: int
    sample_order_no: str
    sample_type: str
    item_code: str
    status: str
    owner: str
    updated_at: datetime


class FrontendWorkOrderItem(BaseModel):
    """Production work-order list projection."""

    plan_id: int
    plan_no: str
    company: str
    sales_order: str
    sales_order_item: str
    item_code: str
    work_order: str
    planned_qty: Decimal
    produced_qty: Decimal
    status: str
    created_at: datetime


class FrontendProductionMaterialIssueItem(BaseModel):
    """Production material issue status projection."""

    plan_id: int
    plan_no: str
    work_order: str
    company: str
    item_code: str
    material_item_code: str
    warehouse: str
    required_qty: Decimal
    available_qty: Decimal
    issued_qty: Decimal
    shortage_qty: Decimal
    status: str


class FrontendMaterialRequestItem(BaseModel):
    """Material request projection for procurement readiness."""

    request_no: str
    company: str
    item_code: str
    material_item_code: str
    supplier_name: str
    qty: Decimal
    uom: str
    expected_delivery_date: date | None
    status: str
    bom_no: str


class FrontendPurchaseReceiptItem(BaseModel):
    """Purchase receipt projection."""

    receipt_no: str
    purchase_no: str
    company: str
    supplier_name: str
    item_code: str
    material_item_code: str
    warehouse: str
    received_qty: Decimal
    accepted_qty: Decimal
    posting_date: date
    status: str


class FrontendPurchaseInvoiceItem(BaseModel):
    """Purchase invoice/payable projection."""

    purchase_invoice_name: str
    company: str
    supplier: str
    supplier_name: str
    currency: str
    grand_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    status: str
    posting_date: date


class FrontendSubcontractMaterialIssueItem(BaseModel):
    """Subcontract material issue projection."""

    subcontract_no: str
    company: str
    supplier: str
    item_code: str
    material_item_code: str
    warehouse: str
    required_qty: Decimal
    issued_qty: Decimal
    pending_qty: Decimal
    status: str


class FrontendSubcontractReceiptItem(BaseModel):
    """Subcontract receipt projection."""

    subcontract_no: str
    company: str
    supplier: str
    item_code: str
    receipt_batch_no: str
    received_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    receipt_warehouse: str
    status: str


class FrontendSubcontractReturnMaterialItem(BaseModel):
    """Subcontract return-material projection."""

    subcontract_no: str
    company: str
    supplier: str
    item_code: str
    material_item_code: str
    planned_return_qty: Decimal
    returned_qty: Decimal
    pending_qty: Decimal
    status: str


class FrontendFinishedGoodsInboundItem(BaseModel):
    """Finished-goods inbound projection based on warehouse reserved inbound fields."""

    reservation_no: str
    item_code: str
    item_name: str
    warehouse: str
    reserve_qty: Decimal
    inbound_qty: Decimal
    pending_inbound_qty: Decimal
    reserve_status: str
    inbound_status: str
    reserved_date: date
    expected_inbound_date: date
    owner: str
    ref_no: str
    company: str | None = None


class FrontendDeliveryNoteItem(BaseModel):
    """Delivery note projection."""

    delivery_note: str
    company: str
    sales_order: str
    customer: str
    item_code: str
    warehouse: str
    delivered_qty: Decimal
    posting_date: date
    status: str


class FrontendSalesInvoiceItem(BaseModel):
    """Sales invoice/receivable projection."""

    sales_invoice: str
    company: str
    sales_order: str
    customer: str
    grand_total: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    posting_date: date
    status: str


class FrontendCustomerReceivableItem(BaseModel):
    """Customer receivable summary projection."""

    summary_no: str
    statement_no: str
    company: str
    customer_name: str
    customer_code: str
    currency: str
    opening_receivable: Decimal
    current_receivable: Decimal
    received_amount: Decimal
    ending_receivable: Decimal
    aging_30: Decimal
    aging_60: Decimal
    aging_90_plus: Decimal
    risk_level: str
    review_status: str
    summary_date: date
    owner: str
    remark: str


class FrontendInventoryBalanceReconciliationItem(BaseModel):
    """Inventory balance reconciliation projection."""

    company: str
    warehouse: str
    item_code: str
    book_qty: Decimal
    actual_qty: Decimal
    diff_qty: Decimal
    status: str
    biz_date: date
    owner: str
    ref_no: str


class FrontendStyleCostItem(BaseModel):
    """Style cost/profit projection based on style-profit snapshot fields."""

    snapshot_no: str
    company: str
    item_code: str
    sales_order: str
    from_date: date
    to_date: date
    revenue_amount: Decimal
    actual_total_cost: Decimal
    standard_total_cost: Decimal
    profit_amount: Decimal
    profit_rate: Decimal
    snapshot_status: str
    allocation_status: str
    formula_version: str


class FrontendSalesToProductionFlowData(BaseModel):
    """Development flow receipt for sales order to work order readiness."""

    plan_id: int
    plan_no: str
    outbox_id: int
    event_key: str
    sync_status: str
    work_order: str
    sales_order: str
    sales_order_item: str
    item_code: str
    planned_qty: Decimal
    status: str


class FrontendProcurementFlowData(BaseModel):
    """Development flow receipt for requisition, purchase receipt and payable readiness."""

    request_no: str
    purchase_no: str
    receipt_no: str
    purchase_invoice_name: str
    supplier: str
    supplier_name: str
    item_code: str
    material_item_code: str
    received_qty: Decimal
    grand_total: Decimal
    outstanding_amount: Decimal
    status: str


class FrontendSubcontractFlowData(BaseModel):
    """Development flow receipt for subcontract issue, receipt and reconciliation readiness."""

    subcontract_no: str
    supplier: str
    item_code: str
    material_item_code: str
    issued_qty: Decimal
    received_qty: Decimal
    accepted_qty: Decimal
    planned_return_qty: Decimal
    returned_qty: Decimal
    statement_no: str
    ending_payable: Decimal
    status: str


class FrontendInventoryFinanceFlowData(BaseModel):
    """Development flow receipt for inbound, delivery, invoice, receivable and balance readiness."""

    reservation_no: str
    delivery_note: str
    sales_invoice: str
    summary_no: str
    warehouse: str
    item_code: str
    inbound_qty: Decimal
    delivered_qty: Decimal
    book_qty: Decimal
    actual_qty: Decimal
    diff_qty: Decimal
    outstanding_amount: Decimal
    status: str


class FrontendQualityFlowData(BaseModel):
    """Development flow receipt for quality inspection readiness."""

    inspection_no: str
    work_order: str
    subcontract_no: str
    item_code: str
    inspected_qty: Decimal
    accepted_qty: Decimal
    rejected_qty: Decimal
    status: str


class FrontendWorkshopWageFlowData(BaseModel):
    """Development flow receipt for job card and piece-rate wage readiness."""

    work_order: str
    job_card: str
    process_name: str
    item_code: str
    completed_qty: Decimal
    unit_rate: Decimal
    wage_amount: Decimal
    status: str


class FrontendStyleProfitFlowData(BaseModel):
    """Development flow receipt for style cost and order profit readiness."""

    snapshot_no: str
    company: str
    sales_order: str
    item_code: str
    revenue_amount: Decimal
    actual_total_cost: Decimal
    standard_total_cost: Decimal
    profit_amount: Decimal
    profit_rate: Decimal
    snapshot_status: str
    allocation_status: str
    formula_version: str
