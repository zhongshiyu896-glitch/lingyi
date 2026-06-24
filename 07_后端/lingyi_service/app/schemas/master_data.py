"""Pydantic schemas for FastAPI-native master data."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

MasterDataEntityType = Literal[
    "customer",
    "supplier",
    "factory",
    "warehouse",
    "material",
    "sample_type",
    "sample_stage",
    "common_address",
    "trade_term",
    "invoice_type",
    "cost_type",
    "size_sort",
    "distribution_channel",
    "bank_account",
]
MasterDataEntityPath = Literal[
    "customers",
    "suppliers",
    "factories",
    "warehouses",
    "materials",
    "sample-types",
    "sample-stages",
    "common-addresses",
    "trade-terms",
    "invoice-types",
    "cost-types",
    "size-sorts",
    "distribution-channels",
    "bank-accounts",
]


class MasterDataCreateRequest(BaseModel):
    """Create one master data record."""

    model_config = ConfigDict(populate_by_name=True)

    operation: Literal["create"] = "create"
    company: str = Field(..., min_length=1, max_length=140)
    code: str | None = Field(default=None, max_length=140)
    name: str = Field(..., min_length=1, max_length=255)
    status: str | None = Field(default=None, max_length=16)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    payload: dict[str, Any] = Field(default_factory=dict)


class MasterDataUpdateRequest(BaseModel):
    """Update mutable master data fields."""

    model_config = ConfigDict(populate_by_name=True)

    operation: Literal["update"] = "update"
    company: str = Field(..., min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    code: str | None = Field(default=None, min_length=1, max_length=140)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, max_length=16)
    payload: dict[str, Any] | None = None


class MasterDataDeactivateRequest(BaseModel):
    """Deactivate one master data record."""

    operation: Literal["deactivate"] = "deactivate"
    company: str = Field(..., min_length=1, max_length=140)
    idempotency_key: str = Field(..., min_length=1, max_length=140)
    reason: str = Field(..., min_length=1, max_length=255)


class MasterDataItem(BaseModel):
    """Master data row returned to frontend pages."""

    id: int
    entity_type: MasterDataEntityType
    code: str
    name: str
    company: str
    status: Literal["active", "inactive"]
    disabled: bool
    source: Literal["fastapi_master_data"] = "fastapi_master_data"
    payload: dict[str, Any] = Field(default_factory=dict)
    version: int
    created_by: str
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None
    deactivated_by: str | None = None
    deactivated_at: datetime | None = None
    deactivate_reason: str | None = None


class MasterDataListData(BaseModel):
    """Paginated master data response."""

    items: list[MasterDataItem]
    total: int
    page: int
    page_size: int
