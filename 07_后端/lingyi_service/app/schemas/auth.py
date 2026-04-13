"""Schemas for auth and action permission APIs."""

from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class ApiResponse(BaseModel):
    """Unified API response envelope."""

    code: str = "0"
    message: str = "success"
    data: dict


class CurrentUserData(BaseModel):
    """Current user payload."""

    username: str
    roles: List[str]
    is_service_account: bool
    source: str


class ActionPermissionData(BaseModel):
    """Aggregated action permission payload."""

    username: str
    module: str
    actions: List[str]
    button_permissions: Dict[str, bool]
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    status: Optional[str] = None


class ActionQuery(BaseModel):
    """Permission action query params."""

    module: str = Field(default="bom", min_length=1)
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
