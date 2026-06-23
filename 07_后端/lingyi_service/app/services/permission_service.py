"""Permission aggregation service for module actions.

核心读动作：`bom:read`。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Any

from fastapi import HTTPException
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import is_internal_worker_principal
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import PermissionSourceUnavailable
from app.core.error_codes import RESOURCE_ACCESS_DENIED
from app.core.error_codes import RESOURCE_SCOPE_FIELD_UNKNOWN
from app.core.logging import REDACTED_MESSAGE
from app.core.logging import log_safe_error
from app.core.logging import sanitize_log_message
from app.core.permissions import AUTH_FORBIDDEN_CODE
from app.core.permissions import DEFAULT_STATIC_ROLE_ACTIONS
from app.core.permissions import BOM_CANCEL
from app.core.permissions import BOM_CREATE
from app.core.permissions import BOM_DEACTIVATE
from app.core.permissions import BOM_PUBLISH
from app.core.permissions import BOM_READ
from app.core.permissions import BOM_SET_DEFAULT
from app.core.permissions import BOM_SUBMIT
from app.core.permissions import BOM_UPDATE
from app.core.permissions import WORKSHOP_JOB_CARD_SYNC
from app.core.permissions import WORKSHOP_JOB_CARD_SYNC_WORKER
from app.core.permissions import WORKSHOP_READ
from app.core.permissions import WORKSHOP_TICKET_BATCH
from app.core.permissions import WORKSHOP_TICKET_REGISTER
from app.core.permissions import WORKSHOP_TICKET_REVERSAL
from app.core.permissions import WORKSHOP_WAGE_RATE_MANAGE_ALL
from app.core.permissions import WORKSHOP_WAGE_RATE_MANAGE
from app.core.permissions import WORKSHOP_WAGE_RATE_READ
from app.core.permissions import WORKSHOP_WAGE_RATE_READ_ALL
from app.core.permissions import WORKSHOP_WAGE_PAYMENT_CANCEL
from app.core.permissions import WORKSHOP_WAGE_PAYMENT_CREATE
from app.core.permissions import WORKSHOP_WAGE_READ
from app.core.permissions import SUBCONTRACT_CANCEL
from app.core.permissions import SUBCONTRACT_CREATE
from app.core.permissions import SUBCONTRACT_INSPECT
from app.core.permissions import SUBCONTRACT_ISSUE_MATERIAL
from app.core.permissions import SUBCONTRACT_READ
from app.core.permissions import SUBCONTRACT_RECEIVE
from app.core.permissions import SUBCONTRACT_SETTLEMENT_LOCK
from app.core.permissions import SUBCONTRACT_SETTLEMENT_READ
from app.core.permissions import SUBCONTRACT_SETTLEMENT_RELEASE
from app.core.permissions import SUBCONTRACT_STOCK_SYNC_RETRY
from app.core.permissions import SUBCONTRACT_STOCK_SYNC_WORKER
from app.core.permissions import PRODUCTION_READ
from app.core.permissions import PRODUCTION_PLAN_CREATE
from app.core.permissions import PRODUCTION_MATERIAL_CHECK
from app.core.permissions import PRODUCTION_MATERIAL_ISSUE
from app.core.permissions import PRODUCTION_TRACKING_NODE
from app.core.permissions import PRODUCTION_WORK_ORDER_CREATE
from app.core.permissions import PRODUCTION_JOB_CARD_SYNC
from app.core.permissions import PRODUCTION_WORK_ORDER_WORKER
from app.core.permissions import STYLE_PROFIT_READ
from app.core.permissions import STYLE_PROFIT_SNAPSHOT_CREATE
from app.core.permissions import FACTORY_STATEMENT_CREATE
from app.core.permissions import FACTORY_STATEMENT_CONFIRM
from app.core.permissions import FACTORY_STATEMENT_CANCEL
from app.core.permissions import FACTORY_STATEMENT_READ
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER
from app.core.permissions import FACTORY_STATEMENT_PAYMENT_CANCEL
from app.core.permissions import FACTORY_STATEMENT_PAYMENT_CREATE
from app.core.permissions import FINANCE_APPROVAL_MANAGE
from app.core.permissions import FINANCE_APPROVAL_READ
from app.core.permissions import MASTER_DATA_MANAGE
from app.core.permissions import MASTER_DATA_READ
from app.core.permissions import MATERIAL_PURCHASE_READ
from app.core.permissions import MATERIAL_PURCHASE_WRITE
from app.core.permissions import REPORT_DIAGNOSTIC
from app.core.permissions import REPORT_EXPORT
from app.core.permissions import REPORT_READ
from app.core.permissions import SAMPLE_MANAGE
from app.core.permissions import SAMPLE_READ
from app.core.permissions import SALES_INVENTORY_DIAGNOSTIC
from app.core.permissions import SALES_INVENTORY_EXPORT
from app.core.permissions import SALES_INVENTORY_READ
from app.core.permissions import SALES_INVENTORY_WRITE
from app.core.permissions import STYLE_MASTER_MANAGE
from app.core.permissions import STYLE_MASTER_READ
from app.core.permissions import SYSTEM_CONFIG_READ
from app.core.permissions import SYSTEM_DIAGNOSTIC
from app.core.permissions import SYSTEM_DICTIONARY_READ
from app.core.permissions import SYSTEM_READ
from app.core.permissions import QUALITY_CANCEL
from app.core.permissions import QUALITY_CONFIRM
from app.core.permissions import QUALITY_CREATE
from app.core.permissions import QUALITY_DIAGNOSTIC
from app.core.permissions import QUALITY_EXPORT
from app.core.permissions import QUALITY_READ
from app.core.permissions import QUALITY_RELEASE
from app.core.permissions import QUALITY_REWORK
from app.core.permissions import QUALITY_UPDATE
from app.core.permissions import WAREHOUSE_DIAGNOSTIC
from app.core.permissions import WAREHOUSE_EXPORT
from app.core.permissions import WAREHOUSE_INVENTORY_COUNT
from app.core.permissions import WAREHOUSE_READ
from app.core.permissions import WAREHOUSE_STOCK_ENTRY_CANCEL
from app.core.permissions import WAREHOUSE_STOCK_ENTRY_DRAFT
from app.core.permissions import WAREHOUSE_WORKER
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import PERMISSION_SOURCE_UNAVAILABLE_CODE
from app.core.permissions import get_permission_source
from app.core.permissions import get_static_actions_for_roles
from app.core.permissions import normalize_actions
from app.core.request_id import get_request_id_from_request
from app.models.bom import LyApparelBom
from app.services.audit_service import AuditService
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PermissionAggregation:
    """Aggregated permission result."""

    username: str
    module: str
    actions: list[str]
    button_permissions: dict[str, bool]
    resource_type: str | None = None
    resource_id: int | None = None
    status: str | None = None


RESOURCE_SCOPE_FIELD_NAMES = (
    "company",
    "item_code",
    "supplier",
    "warehouse",
    "customer",
    "work_order",
    "sales_order",
    "bom_id",
    "source_type",
    "source_id",
)

FASTAPI_RESOURCE_PERMISSIONS_ENV = "LINGYI_FASTAPI_RESOURCE_PERMISSIONS_JSON"
FASTAPI_ROLE_ACTIONS_ENV = "LINGYI_FASTAPI_ROLE_ACTIONS_JSON"
FASTAPI_SCOPE_FIELD_TO_ALLOWED_ATTR = {
    "company": "allowed_companies",
    "item_code": "allowed_items",
    "supplier": "allowed_suppliers",
    "warehouse": "allowed_warehouses",
    "customer": "allowed_customers",
}
FASTAPI_SCOPE_FIELD_CONFIG_KEYS = {
    "company": ("companies", "company", "allowed_companies"),
    "item_code": ("items", "item_codes", "item_code", "allowed_items"),
    "supplier": ("suppliers", "supplier", "allowed_suppliers"),
    "warehouse": ("warehouses", "warehouse", "allowed_warehouses"),
    "customer": ("customers", "customer", "allowed_customers"),
}
FASTAPI_UNSUPPORTED_SCOPE_FIELDS = ("work_order", "sales_order", "bom_id")


ERP_ROLE_ACTIONS: dict[str, set[str]] = {
    "System Manager": {
        BOM_READ,
        BOM_CREATE,
        BOM_UPDATE,
        BOM_PUBLISH,
        BOM_SUBMIT,
        BOM_DEACTIVATE,
        BOM_CANCEL,
        BOM_SET_DEFAULT,
        WORKSHOP_READ,
        WORKSHOP_TICKET_REGISTER,
        WORKSHOP_TICKET_REVERSAL,
        WORKSHOP_TICKET_BATCH,
        WORKSHOP_WAGE_READ,
        WORKSHOP_WAGE_RATE_READ,
        WORKSHOP_WAGE_RATE_READ_ALL,
        WORKSHOP_WAGE_RATE_MANAGE,
        WORKSHOP_WAGE_RATE_MANAGE_ALL,
        WORKSHOP_JOB_CARD_SYNC,
        WORKSHOP_JOB_CARD_SYNC_WORKER,
        SUBCONTRACT_READ,
        SUBCONTRACT_CREATE,
        SUBCONTRACT_ISSUE_MATERIAL,
        SUBCONTRACT_RECEIVE,
        SUBCONTRACT_INSPECT,
        SUBCONTRACT_CANCEL,
        SUBCONTRACT_STOCK_SYNC_RETRY,
        SUBCONTRACT_STOCK_SYNC_WORKER,
        SUBCONTRACT_SETTLEMENT_READ,
        SUBCONTRACT_SETTLEMENT_LOCK,
        SUBCONTRACT_SETTLEMENT_RELEASE,
        PRODUCTION_READ,
        PRODUCTION_PLAN_CREATE,
        PRODUCTION_MATERIAL_CHECK,
        PRODUCTION_MATERIAL_ISSUE,
        PRODUCTION_TRACKING_NODE,
        PRODUCTION_WORK_ORDER_CREATE,
        PRODUCTION_JOB_CARD_SYNC,
        PRODUCTION_WORK_ORDER_WORKER,
        STYLE_PROFIT_READ,
        STYLE_PROFIT_SNAPSHOT_CREATE,
        FACTORY_STATEMENT_READ,
        FACTORY_STATEMENT_CREATE,
        FACTORY_STATEMENT_CONFIRM,
        FACTORY_STATEMENT_CANCEL,
        FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE,
        FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER,
        FINANCE_APPROVAL_READ,
        FINANCE_APPROVAL_MANAGE,
        SALES_INVENTORY_READ,
        SALES_INVENTORY_EXPORT,
        SALES_INVENTORY_DIAGNOSTIC,
    },
    "LY Integration Service": {
        WORKSHOP_READ,
        WORKSHOP_JOB_CARD_SYNC,
        WORKSHOP_JOB_CARD_SYNC_WORKER,
        SUBCONTRACT_STOCK_SYNC_WORKER,
        PRODUCTION_WORK_ORDER_WORKER,
        PRODUCTION_READ,
        PRODUCTION_JOB_CARD_SYNC,
        FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER,
        SALES_INVENTORY_DIAGNOSTIC,
    },
    "BOM Manager": {BOM_READ, BOM_CREATE, BOM_UPDATE, BOM_PUBLISH, BOM_SUBMIT, BOM_DEACTIVATE, BOM_CANCEL, BOM_SET_DEFAULT},
    "BOM Editor": {BOM_READ, BOM_CREATE, BOM_UPDATE},
    "BOM Publisher": {BOM_READ, BOM_PUBLISH, BOM_SUBMIT, BOM_DEACTIVATE, BOM_CANCEL, BOM_SET_DEFAULT},
    "Workshop Manager": {
        WORKSHOP_READ,
        WORKSHOP_TICKET_REGISTER,
        WORKSHOP_TICKET_REVERSAL,
        WORKSHOP_TICKET_BATCH,
        WORKSHOP_WAGE_READ,
        WORKSHOP_WAGE_RATE_READ,
        WORKSHOP_WAGE_RATE_READ_ALL,
        WORKSHOP_WAGE_RATE_MANAGE,
        WORKSHOP_WAGE_RATE_MANAGE_ALL,
        WORKSHOP_WAGE_PAYMENT_CREATE,
        WORKSHOP_WAGE_PAYMENT_CANCEL,
        WORKSHOP_JOB_CARD_SYNC,
    },
    "Workshop Clerk": {
        WORKSHOP_READ,
        WORKSHOP_TICKET_REGISTER,
        WORKSHOP_TICKET_REVERSAL,
        WORKSHOP_TICKET_BATCH,
    },
    "Workshop Wage Clerk": {
        WORKSHOP_READ,
        WORKSHOP_WAGE_READ,
        WORKSHOP_WAGE_RATE_READ,
        WORKSHOP_WAGE_RATE_MANAGE,
        WORKSHOP_WAGE_PAYMENT_CREATE,
        WORKSHOP_WAGE_PAYMENT_CANCEL,
    },
    "Production Manager": {
        WORKSHOP_READ,
        WORKSHOP_TICKET_REGISTER,
        WORKSHOP_TICKET_REVERSAL,
        WORKSHOP_TICKET_BATCH,
        WORKSHOP_WAGE_READ,
        WORKSHOP_WAGE_RATE_READ,
        WORKSHOP_WAGE_RATE_READ_ALL,
        WORKSHOP_WAGE_RATE_MANAGE,
        WORKSHOP_WAGE_RATE_MANAGE_ALL,
        WORKSHOP_WAGE_PAYMENT_CREATE,
        WORKSHOP_WAGE_PAYMENT_CANCEL,
        WORKSHOP_JOB_CARD_SYNC,
        PRODUCTION_READ,
        PRODUCTION_PLAN_CREATE,
        PRODUCTION_MATERIAL_CHECK,
        PRODUCTION_TRACKING_NODE,
        PRODUCTION_WORK_ORDER_CREATE,
        PRODUCTION_JOB_CARD_SYNC,
        STYLE_PROFIT_READ,
        SALES_INVENTORY_READ,
    },
    "Finance Manager": {
        STYLE_PROFIT_READ,
        STYLE_PROFIT_SNAPSHOT_CREATE,
        FACTORY_STATEMENT_READ,
        FACTORY_STATEMENT_CREATE,
        FACTORY_STATEMENT_CONFIRM,
        FACTORY_STATEMENT_CANCEL,
        FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE,
        FINANCE_APPROVAL_READ,
        FINANCE_APPROVAL_MANAGE,
        SALES_INVENTORY_READ,
        SALES_INVENTORY_EXPORT,
    },
    "Sales Manager": {
        STYLE_PROFIT_READ,
        SALES_INVENTORY_READ,
        SALES_INVENTORY_WRITE,
        SALES_INVENTORY_EXPORT,
    },
    "Quality Manager": {
        QUALITY_READ,
        QUALITY_CREATE,
        QUALITY_UPDATE,
        QUALITY_CONFIRM,
        QUALITY_CANCEL,
        QUALITY_EXPORT,
        QUALITY_DIAGNOSTIC,
    },
    "Quality Inspector": {
        QUALITY_READ,
        QUALITY_CREATE,
        QUALITY_UPDATE,
        QUALITY_CONFIRM,
        QUALITY_CANCEL,
        QUALITY_EXPORT,
    },
    "Quality Viewer": {
        QUALITY_READ,
        QUALITY_EXPORT,
    },
    "Workshop Sync Operator": {
        WORKSHOP_READ,
        WORKSHOP_JOB_CARD_SYNC,
    },
    "Subcontract Manager": {
        SUBCONTRACT_READ,
        SUBCONTRACT_CREATE,
        SUBCONTRACT_ISSUE_MATERIAL,
        SUBCONTRACT_RECEIVE,
        SUBCONTRACT_INSPECT,
        SUBCONTRACT_CANCEL,
        SUBCONTRACT_STOCK_SYNC_RETRY,
        SUBCONTRACT_SETTLEMENT_READ,
        SUBCONTRACT_SETTLEMENT_LOCK,
        SUBCONTRACT_SETTLEMENT_RELEASE,
        FACTORY_STATEMENT_READ,
        FACTORY_STATEMENT_CREATE,
        FACTORY_STATEMENT_CONFIRM,
        FACTORY_STATEMENT_CANCEL,
        FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE,
        WAREHOUSE_READ,
        WAREHOUSE_STOCK_ENTRY_DRAFT,
    },
    "Subcontract Operator": {
        SUBCONTRACT_READ,
        SUBCONTRACT_CREATE,
        SUBCONTRACT_ISSUE_MATERIAL,
        SUBCONTRACT_RECEIVE,
    },
    "Subcontract Inspector": {
        SUBCONTRACT_READ,
        SUBCONTRACT_INSPECT,
    },
    "Subcontract Viewer": {
        SUBCONTRACT_READ,
    },
}

# 与 core.permissions 的 System Manager 动作保持一致，避免双份清单漂移。
ERP_ROLE_ACTIONS["System Manager"] = set(DEFAULT_STATIC_ROLE_ACTIONS.get("System Manager", set()))


class PermissionService:
    """Aggregate actions from static or ERPNext permission source."""

    _static_warning_emitted = False

    def __init__(self, session: Session):
        self.session = session

    def get_actions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        module: str = "bom",
        audit_module: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_item_code: str | None = None,
        action_context: str | None = None,
    ) -> PermissionAggregation:
        module_name = module or "bom"
        audit_module_name = audit_module or module_name
        source = get_permission_source()

        resolved_item_code = resource_item_code
        resource_status = None
        resource_no = None
        if resource_type == "bom" and resource_id:
            bom = self.session.query(LyApparelBom).filter(LyApparelBom.id == resource_id).first()
            if not bom:
                raise HTTPException(
                    status_code=404,
                    detail={"code": "BOM_NOT_FOUND", "message": "BOM 不存在", "data": None},
                )
            resolved_item_code = str(bom.item_code)
            resource_status = str(bom.status)
            resource_no = str(bom.bom_no)

        try:
            if source == "erpnext":
                action_set = self._actions_from_erpnext(
                    current_user=current_user,
                    request_obj=request_obj,
                    resource_item_code=resolved_item_code,
                    resource_status=resource_status,
                    resource_no=resource_no,
                )
            elif source == "fastapi":
                action_set = self._actions_from_fastapi(current_user=current_user)
            else:
                action_set = self._actions_from_static(current_user=current_user)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module=audit_module_name,
                action=action_context or "permission:aggregate",
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

        action_set = normalize_actions(action_set)
        action_set = self._filter_actions_by_module(action_set=action_set, module=module_name)
        button_permissions = self._button_permissions(module=module_name, actions=action_set, status=resource_status)
        return PermissionAggregation(
            username=current_user.username,
            module=module_name,
            actions=sorted(action_set),
            button_permissions=button_permissions,
            resource_type=resource_type,
            resource_id=resource_id,
            status=resource_status,
        )

    def require_action(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        module: str = "bom",
        audit_module: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_item_code: str | None = None,
        raise_on_audit_failure: bool = False,
    ) -> PermissionAggregation:
        agg = self.get_actions(
            current_user=current_user,
            request_obj=request_obj,
            module=module,
            audit_module=audit_module,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_item_code=resource_item_code,
            action_context=action,
        )
        if action not in set(agg.actions):
            deny_reason, resource_no = self._resolve_forbidden_reason(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module=audit_module or module,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module=audit_module or module,
                action=action,
                resource_type=resource_type.upper() if resource_type else None,
                resource_id=resource_id,
                resource_no=resource_no,
                user=current_user,
                deny_reason=deny_reason,
                request_obj=request_obj,
                raise_on_failure=raise_on_audit_failure,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )
        return agg

    def require_action_from_roles_only(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        module: str = "bom",
        audit_module: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        raise_on_audit_failure: bool = False,
    ) -> PermissionAggregation:
        """Require action using current roles only (no ERPNext permission-source lookup)."""
        module_name = module or "bom"
        action_set = self._actions_from_current_roles_only(current_user=current_user)
        action_set = normalize_actions(action_set)
        action_set = self._filter_actions_by_module(action_set=action_set, module=module_name)
        button_permissions = self._button_permissions(module=module_name, actions=action_set, status=None)
        agg = PermissionAggregation(
            username=current_user.username,
            module=module_name,
            actions=sorted(action_set),
            button_permissions=button_permissions,
            resource_type=resource_type,
            resource_id=resource_id,
            status=None,
        )
        if action not in set(agg.actions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module=audit_module or module,
                action=action,
                resource_type=resource_type.upper() if resource_type else None,
                resource_id=resource_id,
                resource_no=None,
                user=current_user,
                deny_reason=f"缺少动作权限: {action}",
                request_obj=request_obj,
                raise_on_failure=raise_on_audit_failure,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )
        return agg

    def require_item_access(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        module: str,
        action: str,
        item_code: str,
        resource_type: str = "item",
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> None:
        """Require item-level access under ERPNext User Permission constraints."""
        source = get_permission_source()
        if source == "fastapi":
            permissions = self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no or item_code,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope={"item_code": self._normalize_scope_value(item_code)},
                module=module,
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no or item_code,
            )
            return
        if source != "erpnext":
            return

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            user_permissions = adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no or item_code,
            )
        if adapter.is_item_permitted(item_code=item_code, user_permissions=user_permissions):
            return

        self._record_security_audit_safe(
            event_type=AUTH_FORBIDDEN_CODE,
            module=module,
            action=action,
            resource_type=resource_type.upper(),
            resource_id=resource_id,
            resource_no=resource_no or item_code,
            user=current_user,
            deny_reason="资源权限不足：无权访问该 item_code",
            request_obj=request_obj,
        )
        raise HTTPException(
            status_code=403,
            detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
        )

    @staticmethod
    def _normalize_scope_value(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _raise_fastapi_permission_config_unavailable(detail: str) -> None:
        raise PermissionSourceUnavailable(
            message="FastAPI 权限配置不可用",
            exception_type="PermissionSourceUnavailable",
            exception_message=detail,
        )

    def _load_fastapi_resource_permission_config(self) -> dict[str, Any]:
        raw = os.getenv(FASTAPI_RESOURCE_PERMISSIONS_ENV, "").strip()
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._raise_fastapi_permission_config_unavailable(
                f"{FASTAPI_RESOURCE_PERMISSIONS_ENV} json decode failed: {exc.msg}"
            )
        if not isinstance(payload, dict):
            self._raise_fastapi_permission_config_unavailable(
                f"{FASTAPI_RESOURCE_PERMISSIONS_ENV} must be a json object"
            )
        return payload

    def _fastapi_scope_entries_for_user(
        self,
        *,
        payload: dict[str, Any],
        current_user: CurrentUser,
    ) -> list[dict[str, Any]]:
        users = payload.get("users", {})
        roles = payload.get("roles", {})
        if users is None:
            users = {}
        if roles is None:
            roles = {}
        if not isinstance(users, dict):
            self._raise_fastapi_permission_config_unavailable("users must be an object")
        if not isinstance(roles, dict):
            self._raise_fastapi_permission_config_unavailable("roles must be an object")

        entries: list[dict[str, Any]] = []
        user_entry = users.get(current_user.username)
        if user_entry is not None:
            if not isinstance(user_entry, dict):
                self._raise_fastapi_permission_config_unavailable(
                    f"user scope for {current_user.username} must be an object"
                )
            entries.append(user_entry)

        for role in current_user.roles:
            role_entry = roles.get(role)
            if role_entry is None:
                continue
            if not isinstance(role_entry, dict):
                self._raise_fastapi_permission_config_unavailable(f"role scope for {role} must be an object")
            entries.append(role_entry)
        return entries

    def _parse_fastapi_scope_values(self, value: Any, *, key: str) -> set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            normalized = self._normalize_scope_value(value)
            return {normalized} if normalized else set()
        if not isinstance(value, list):
            self._raise_fastapi_permission_config_unavailable(f"{key} must be a string or list")

        values: set[str] = set()
        for item in value:
            normalized = self._normalize_scope_value(item)
            if normalized:
                values.add(normalized)
        return values

    def _merge_fastapi_scope_values(self, *, entries: list[dict[str, Any]], field_name: str) -> set[str]:
        values: set[str] = set()
        for entry in entries:
            for key in FASTAPI_SCOPE_FIELD_CONFIG_KEYS[field_name]:
                if key in entry:
                    values.update(self._parse_fastapi_scope_values(entry[key], key=key))
        return values

    def _fastapi_user_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        module: str,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult:
        try:
            if "System Manager" in current_user.roles:
                return UserPermissionResult(
                    source_available=True,
                    unrestricted=True,
                    allowed_items=set(),
                    allowed_companies=set(),
                    allowed_suppliers=set(),
                    allowed_warehouses=set(),
                    allowed_customers=set(),
                )

            payload = self._load_fastapi_resource_permission_config()
            entries = self._fastapi_scope_entries_for_user(payload=payload, current_user=current_user)
            if any(bool(entry.get("unrestricted")) for entry in entries):
                return UserPermissionResult(
                    source_available=True,
                    unrestricted=True,
                    allowed_items=set(),
                    allowed_companies=set(),
                    allowed_suppliers=set(),
                    allowed_warehouses=set(),
                    allowed_customers=set(),
                )
            return UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=self._merge_fastapi_scope_values(entries=entries, field_name="item_code"),
                allowed_companies=self._merge_fastapi_scope_values(entries=entries, field_name="company"),
                allowed_suppliers=self._merge_fastapi_scope_values(entries=entries, field_name="supplier"),
                allowed_warehouses=self._merge_fastapi_scope_values(entries=entries, field_name="warehouse"),
                allowed_customers=self._merge_fastapi_scope_values(entries=entries, field_name="customer"),
            )
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def _ensure_fastapi_resource_scope_allowed(
        self,
        *,
        permissions: UserPermissionResult,
        normalized_scope: dict[str, str | None],
        module: str,
        action: str,
        current_user: CurrentUser,
        request_obj: Request,
        resource_type: str | None,
        resource_id: int | None,
        resource_no: str | None,
    ) -> None:
        if permissions.unrestricted:
            return

        for field_name, allowed_attr in FASTAPI_SCOPE_FIELD_TO_ALLOWED_ATTR.items():
            field_value = normalized_scope.get(field_name)
            if not field_value:
                continue
            allowed_values: set[str] = getattr(permissions, allowed_attr)
            if field_value in allowed_values:
                continue
            deny_reason = (
                f"FastAPI 权限源未配置 {field_name} 资源范围"
                if not allowed_values
                else f"FastAPI 权限源无权访问该 {field_name}"
            )
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name=field_name,
                field_value=field_value,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason=deny_reason,
            )

        for unsupported_field in FASTAPI_UNSUPPORTED_SCOPE_FIELDS:
            field_value = normalized_scope.get(unsupported_field)
            if not field_value:
                continue
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name=unsupported_field,
                field_value=field_value,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason=f"FastAPI 权限源无法校验 {unsupported_field} 作用域",
            )

    def _raise_resource_access_denied(
        self,
        *,
        module: str,
        action: str,
        field_name: str,
        field_value: str | None,
        current_user: CurrentUser,
        request_obj: Request,
        resource_type: str | None,
        resource_id: int | None,
        resource_no: str | None,
        deny_reason: str,
    ) -> None:
        self._record_security_audit_safe(
            event_type="RESOURCE_ACCESS_DENIED",
            module=module,
            action=action,
            resource_type=(resource_type or field_name).upper(),
            resource_id=resource_id,
            resource_no=resource_no or field_value,
            user=current_user,
            deny_reason=deny_reason,
            request_obj=request_obj,
            reason_code=RESOURCE_ACCESS_DENIED,
            resource_scope={"field": field_name, "value": field_value},
        )
        raise HTTPException(
            status_code=403,
            detail={"code": RESOURCE_ACCESS_DENIED, "message": "资源权限不足，禁止访问", "data": None},
        )

    def ensure_resource_scope_permission(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        module: str,
        action: str,
        resource_scope: dict[str, Any] | None = None,
        required_fields: tuple[str, ...] = (),
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
        enforce_action: bool = True,
        user_permissions: UserPermissionResult | None = None,
    ) -> None:
        """Unified resource-scope guard for company/item/supplier/... fields.

        口径：
        - 先动作权限，再资源权限；
        - 缺关键字段 fail closed；
        - Company-only 不自动推导 Item 权限；
        - 无法静态验证的 scope 字段在 ERPNext 模式下 fail closed。
        """
        if enforce_action:
            self.require_action(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module=module,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_item_code=self._normalize_scope_value((resource_scope or {}).get("item_code")),
            )

        scope = resource_scope or {}
        normalized_scope: dict[str, str | None] = {}
        for name in RESOURCE_SCOPE_FIELD_NAMES:
            normalized_scope[name] = self._normalize_scope_value(scope.get(name))

        for field_name in required_fields:
            if field_name not in RESOURCE_SCOPE_FIELD_NAMES:
                self._record_security_audit_safe(
                    event_type="RESOURCE_ACCESS_DENIED",
                    module=module,
                    action=action,
                    resource_type=(resource_type or "RESOURCE_SCOPE").upper(),
                    resource_id=resource_id,
                    resource_no=resource_no,
                    user=current_user,
                    deny_reason=f"资源权限字段配置错误: {field_name}",
                    request_obj=request_obj,
                    reason_code=RESOURCE_SCOPE_FIELD_UNKNOWN,
                    resource_scope={"field": field_name, "value": None},
                )
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": RESOURCE_SCOPE_FIELD_UNKNOWN,
                        "message": "资源权限字段配置错误",
                        "data": None,
                    },
                )
            if not normalized_scope.get(field_name):
                self._raise_resource_access_denied(
                    module=module,
                    action=action,
                    field_name=field_name,
                    field_value=None,
                    current_user=current_user,
                    request_obj=request_obj,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_no=resource_no,
                    deny_reason=f"缺少关键资源范围字段: {field_name}",
                )

        source = get_permission_source()
        if source == "fastapi":
            permissions = user_permissions or self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope=normalized_scope,
                module=module,
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            return
        if source != "erpnext":
            return

        permissions = user_permissions
        if permissions is None:
            adapter = ERPNextPermissionAdapter(request_obj=request_obj)
            try:
                permissions = adapter.get_user_permissions(username=current_user.username)
            except PermissionSourceUnavailable as exc:
                self._raise_permission_source_unavailable(
                    exc=exc,
                    request_obj=request_obj,
                    current_user=current_user,
                    module=module,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    resource_no=resource_no,
                )
        if permissions is None:
            return

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        company = normalized_scope.get("company")
        item_code = normalized_scope.get("item_code")
        supplier = normalized_scope.get("supplier")
        warehouse = normalized_scope.get("warehouse")
        customer = normalized_scope.get("customer")

        if company and not adapter.is_company_permitted(company=company, user_permissions=permissions):
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name="company",
                field_value=company,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason="资源权限不足：无权访问该 company",
            )
        if item_code and not adapter.is_item_permitted(item_code=item_code, user_permissions=permissions):
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name="item_code",
                field_value=item_code,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason="资源权限不足：无权访问该 item_code",
            )
        if supplier and not adapter.is_supplier_permitted(supplier=supplier, user_permissions=permissions):
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name="supplier",
                field_value=supplier,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason="资源权限不足：无权访问该 supplier",
            )
        if warehouse and not adapter.is_warehouse_permitted(warehouse=warehouse, user_permissions=permissions):
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name="warehouse",
                field_value=warehouse,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason="资源权限不足：无权访问该 warehouse",
            )
        if customer and not adapter.is_customer_permitted(customer=customer, user_permissions=permissions):
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name="customer",
                field_value=customer,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason="资源权限不足：无权访问该 customer",
            )

        # 当前 ERPNext 权限源无 work_order/sales_order/bom_id 授权矩阵，保持 fail closed。
        for unsupported_field in ("work_order", "sales_order", "bom_id"):
            field_value = normalized_scope.get(unsupported_field)
            if not field_value:
                continue
            self._raise_resource_access_denied(
                module=module,
                action=action,
                field_name=unsupported_field,
                field_value=field_value,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                deny_reason=f"资源权限不足：无法校验 {unsupported_field} 作用域",
            )

    def require_internal_worker_principal(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str = WORKSHOP_JOB_CARD_SYNC_WORKER,
        module: str = "workshop",
        resource_type: str = "JOBCARDSYNCWORKER",
    ) -> None:
        """Require trusted service/system principal for internal worker API."""
        if is_internal_worker_principal(current_user):
            return
        self._record_security_audit_safe(
            event_type=AUTH_FORBIDDEN_CODE,
            module=module,
            action=action,
            resource_type=resource_type,
            resource_id=None,
            resource_no=None,
            user=current_user,
            deny_reason="内部 Worker 接口仅允许服务账号或系统级集成账号调用",
            request_obj=request_obj,
        )
        raise HTTPException(
            status_code=403,
            detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
        )

    def get_workshop_user_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult | None:
        """Prefetch ERPNext user permissions for workshop resource checks."""
        source = get_permission_source()
        if source == "fastapi":
            return self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="workshop",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            return adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module="workshop",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def ensure_workshop_resource_permission(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        item_code: str,
        company: str | None,
        job_card: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
        enforce_action: bool = True,
        user_permissions: UserPermissionResult | None = None,
    ) -> None:
        """Enforce workshop action + item/company resource permission."""
        if enforce_action:
            self.require_action(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module="workshop",
                resource_type=resource_type,
                resource_id=resource_id,
            )

        source = get_permission_source()
        if source == "fastapi":
            permissions = user_permissions or self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="workshop",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no or item_code,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope={
                    "item_code": self._normalize_scope_value(item_code),
                    "company": self._normalize_scope_value(company),
                },
                module="workshop",
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no or item_code,
            )
            return
        if source != "erpnext":
            return

        permissions = user_permissions or self.get_workshop_user_permissions(
            current_user=current_user,
            request_obj=request_obj,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no or item_code,
        )
        if permissions is None:
            return

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        if not adapter.is_item_permitted(item_code=item_code, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="workshop",
                action=action,
                resource_type="ITEM",
                resource_id=resource_id,
                resource_no=item_code,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 item_code",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if company and not ERPNextPermissionAdapter.is_company_permitted(company=company, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="workshop",
                action=action,
                resource_type="COMPANY",
                resource_id=resource_id,
                resource_no=company,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 company",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if job_card and resource_type and resource_type.upper() == "JOBCARD":
            # Job Card 资源本身可追踪，权限落点仍由 item/company 判定。
            return

    def ensure_workshop_company_permission(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        company: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
        enforce_action: bool = True,
        user_permissions: UserPermissionResult | None = None,
    ) -> None:
        """Enforce workshop action + company resource permission."""
        if enforce_action:
            self.require_action(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module="workshop",
                resource_type=resource_type,
                resource_id=resource_id,
            )

        source = get_permission_source()
        if source == "fastapi":
            permissions = user_permissions or self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="workshop",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no or company,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope={"company": self._normalize_scope_value(company)},
                module="workshop",
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no or company,
            )
            return
        if source != "erpnext":
            return

        permissions = user_permissions or self.get_workshop_user_permissions(
            current_user=current_user,
            request_obj=request_obj,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no or company,
        )
        if permissions is None:
            return

        if ERPNextPermissionAdapter.is_company_permitted(company=company, user_permissions=permissions):
            return

        self._record_security_audit_safe(
            event_type=AUTH_FORBIDDEN_CODE,
            module="workshop",
            action=action,
            resource_type="COMPANY",
            resource_id=resource_id,
            resource_no=company,
            user=current_user,
            deny_reason="资源权限不足：无权访问该 company",
            request_obj=request_obj,
        )
        raise HTTPException(
            status_code=403,
            detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
        )

    def get_sales_inventory_user_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult | None:
        """Prefetch ERPNext user permissions for sales/inventory read filtering."""
        source = get_permission_source()
        if source == "fastapi":
            return self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="sales_inventory",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            return adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module="sales_inventory",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def get_subcontract_user_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult | None:
        """Prefetch ERPNext user permissions for subcontract resource checks."""
        source = get_permission_source()
        if source == "fastapi":
            return self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="subcontract",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            return adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module="subcontract",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def ensure_subcontract_resource_permission(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        item_code: str | None = None,
        company: str | None = None,
        supplier: str | None = None,
        warehouse: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
        enforce_action: bool = True,
        user_permissions: UserPermissionResult | None = None,
    ) -> None:
        """Enforce subcontract action + item/company/supplier/warehouse resource permission."""
        if enforce_action:
            self.require_action(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module="subcontract",
                resource_type=resource_type,
                resource_id=resource_id,
                resource_item_code=item_code,
            )

        source = get_permission_source()
        if source == "fastapi":
            permissions = user_permissions or self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="subcontract",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope={
                    "item_code": self._normalize_scope_value(item_code),
                    "company": self._normalize_scope_value(company),
                    "supplier": self._normalize_scope_value(supplier),
                    "warehouse": self._normalize_scope_value(warehouse),
                },
                module="subcontract",
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            return
        if source != "erpnext":
            return

        permissions = user_permissions or self.get_subcontract_user_permissions(
            current_user=current_user,
            request_obj=request_obj,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
        )
        if permissions is None:
            return

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        if item_code and not adapter.is_item_permitted(item_code=item_code, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="subcontract",
                action=action,
                resource_type="ITEM",
                resource_id=resource_id,
                resource_no=item_code,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 item_code",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if company and not adapter.is_company_permitted(company=company, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="subcontract",
                action=action,
                resource_type="COMPANY",
                resource_id=resource_id,
                resource_no=company,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 company",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if supplier and not adapter.is_supplier_permitted(supplier=supplier, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="subcontract",
                action=action,
                resource_type="SUPPLIER",
                resource_id=resource_id,
                resource_no=supplier,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 supplier",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if warehouse and not adapter.is_warehouse_permitted(warehouse=warehouse, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="subcontract",
                action=action,
                resource_type="WAREHOUSE",
                resource_id=resource_id,
                resource_no=warehouse,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 warehouse",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

    def get_production_user_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult | None:
        """Prefetch ERPNext user permissions for production resource checks."""
        source = get_permission_source()
        if source == "fastapi":
            return self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="production",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            return adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module="production",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def ensure_production_resource_permission(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        item_code: str | None = None,
        company: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
        enforce_action: bool = True,
        user_permissions: UserPermissionResult | None = None,
    ) -> None:
        """Enforce production action + item/company resource permission."""
        if enforce_action:
            self.require_action(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module="production",
                resource_type=resource_type,
                resource_id=resource_id,
                resource_item_code=item_code,
            )

        source = get_permission_source()
        if source == "fastapi":
            permissions = user_permissions or self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="production",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope={
                    "item_code": self._normalize_scope_value(item_code),
                    "company": self._normalize_scope_value(company),
                },
                module="production",
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            return
        if source != "erpnext":
            return

        permissions = user_permissions or self.get_production_user_permissions(
            current_user=current_user,
            request_obj=request_obj,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
        )
        if permissions is None:
            return

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        if item_code and not adapter.is_item_permitted(item_code=item_code, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="production",
                action=action,
                resource_type="ITEM",
                resource_id=resource_id,
                resource_no=item_code,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 item_code",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if company and not adapter.is_company_permitted(company=company, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="production",
                action=action,
                resource_type="COMPANY",
                resource_id=resource_id,
                resource_no=company,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 company",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

    def get_style_profit_user_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult | None:
        """Prefetch ERPNext user permissions for style-profit resource checks."""
        source = get_permission_source()
        if source == "fastapi":
            return self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="style_profit",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            return adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module="style_profit",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def ensure_style_profit_resource_permission(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        item_code: str | None = None,
        company: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
        enforce_action: bool = True,
        user_permissions: UserPermissionResult | None = None,
    ) -> None:
        """Enforce style-profit action + item/company resource permission."""
        if enforce_action:
            self.require_action(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module="style_profit",
                resource_type=resource_type,
                resource_id=resource_id,
                resource_item_code=item_code,
            )

        source = get_permission_source()
        if source == "fastapi":
            permissions = user_permissions or self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="style_profit",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope={
                    "item_code": self._normalize_scope_value(item_code),
                    "company": self._normalize_scope_value(company),
                },
                module="style_profit",
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            return
        if source != "erpnext":
            return

        permissions = user_permissions or self.get_style_profit_user_permissions(
            current_user=current_user,
            request_obj=request_obj,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
        )
        if permissions is None:
            return

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        if item_code and not adapter.is_item_permitted(item_code=item_code, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="style_profit",
                action=action,
                resource_type="ITEM",
                resource_id=resource_id,
                resource_no=item_code,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 item_code",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if company and not adapter.is_company_permitted(company=company, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="style_profit",
                action=action,
                resource_type="COMPANY",
                resource_id=resource_id,
                resource_no=company,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 company",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

    def get_factory_statement_user_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult | None:
        """Prefetch ERPNext user permissions for factory-statement resource checks."""
        source = get_permission_source()
        if source == "fastapi":
            return self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="factory_statement",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            return adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module="factory_statement",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def ensure_factory_statement_resource_permission(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        company: str | None = None,
        supplier: str | None = None,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
        enforce_action: bool = True,
        user_permissions: UserPermissionResult | None = None,
    ) -> None:
        """Enforce factory-statement action + company/supplier resource permission."""
        if enforce_action:
            self.require_action(
                current_user=current_user,
                request_obj=request_obj,
                action=action,
                module="factory_statement",
                resource_type=resource_type,
                resource_id=resource_id,
            )

        source = get_permission_source()
        if source == "fastapi":
            permissions = user_permissions or self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module="factory_statement",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            self._ensure_fastapi_resource_scope_allowed(
                permissions=permissions,
                normalized_scope={
                    "company": self._normalize_scope_value(company),
                    "supplier": self._normalize_scope_value(supplier),
                },
                module="factory_statement",
                action=action,
                current_user=current_user,
                request_obj=request_obj,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
            return
        if source != "erpnext":
            return

        permissions = user_permissions or self.get_factory_statement_user_permissions(
            current_user=current_user,
            request_obj=request_obj,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
        )
        if permissions is None:
            return

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        if company and not adapter.is_company_permitted(company=company, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="factory_statement",
                action=action,
                resource_type="COMPANY",
                resource_id=resource_id,
                resource_no=company,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 company",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

        if supplier and not adapter.is_supplier_permitted(supplier=supplier, user_permissions=permissions):
            self._record_security_audit_safe(
                event_type=AUTH_FORBIDDEN_CODE,
                module="factory_statement",
                action=action,
                resource_type="SUPPLIER",
                resource_id=resource_id,
                resource_no=supplier,
                user=current_user,
                deny_reason="资源权限不足：无权访问该 supplier",
                request_obj=request_obj,
            )
            raise HTTPException(
                status_code=403,
                detail={"code": AUTH_FORBIDDEN_CODE, "message": "无权限访问该资源", "data": None},
            )

    def record_security_denial(
        self,
        *,
        request_obj: Request,
        current_user: CurrentUser | None,
        action: str,
        resource_type: str,
        resource_no: str | None,
        deny_reason: str,
        event_type: str = AUTH_FORBIDDEN_CODE,
        resource_id: int | None = None,
        module: str = "workshop",
    ) -> None:
        """Public helper for explicit security denial audit."""
        self._record_security_audit_safe(
            event_type=event_type,
            module=module,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
            user=current_user,
            deny_reason=deny_reason,
            request_obj=request_obj,
        )

    def get_resource_scope_permissions(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        module: str,
        action: str,
        resource_type: str | None = None,
        resource_id: int | None = None,
        resource_no: str | None = None,
    ) -> UserPermissionResult | None:
        """Return resource-scope permissions for list filtering and batch guards."""
        source = get_permission_source()
        if source == "fastapi":
            return self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            return adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )

    def get_readable_item_codes(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        module: str = "bom",
        action_context: str = BOM_READ,
        resource_type: str = "bom",
        resource_id: int | None = None,
    ) -> set[str] | None:
        """Return readable item_code scope from ERPNext User Permission.

        Returns:
            None: no item-level restriction, or static permission source.
            set[str]: restricted readable item_code collection.
        """
        source = get_permission_source()
        if source == "fastapi":
            user_permissions = self._fastapi_user_permissions(
                current_user=current_user,
                request_obj=request_obj,
                module=module,
                action=action_context,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=None,
            )
            if user_permissions.unrestricted:
                return None
            return set(user_permissions.allowed_items)
        if source != "erpnext":
            return None

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            user_permissions = adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module=module,
                action=action_context,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=None,
            )

        if user_permissions.unrestricted:
            return None
        if user_permissions.allowed_items:
            return set(user_permissions.allowed_items)
        # 仅 Company 限制时当前无映射条件，按 fail closed 拒绝。
        return set()

    def _actions_from_static(self, *, current_user: CurrentUser) -> set[str]:
        if get_permission_source() == "static" and not PermissionService._static_warning_emitted:
            # 仅用于本地/测试；生产使用 FastAPI 原生权限源。
            logger.warning("LINGYI_PERMISSION_SOURCE=static 临时权限来源，不可用于生产")
            PermissionService._static_warning_emitted = True
        return get_static_actions_for_roles(current_user.roles)

    def _load_fastapi_role_action_config(self) -> dict[str, Any]:
        raw = os.getenv(FASTAPI_ROLE_ACTIONS_ENV, "").strip()
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            self._raise_fastapi_permission_config_unavailable(
                f"{FASTAPI_ROLE_ACTIONS_ENV} json decode failed: {exc.msg}"
            )
        if not isinstance(payload, dict):
            self._raise_fastapi_permission_config_unavailable(
                f"{FASTAPI_ROLE_ACTIONS_ENV} must be a json object"
            )
        return payload

    def _all_registered_actions(self) -> set[str]:
        actions: set[str] = set()
        for module_actions in MODULE_ACTION_REGISTRY.values():
            actions.update(module_actions)
        return normalize_actions(actions)

    def _parse_fastapi_action_values(self, value: Any, *, key: str) -> set[str]:
        if value is None:
            return set()
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return set()
            if normalized == "*":
                return self._all_registered_actions()
            return {normalized}
        if not isinstance(value, list):
            self._raise_fastapi_permission_config_unavailable(f"{key} must be a string or list")

        actions: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                self._raise_fastapi_permission_config_unavailable(f"{key} must contain only strings")
            normalized = item.strip()
            if not normalized:
                continue
            if normalized == "*":
                actions.update(self._all_registered_actions())
            else:
                actions.add(normalized)
        return normalize_actions(actions)

    def _actions_from_fastapi_entry(self, entry: Any, *, key: str) -> set[str]:
        if entry is None:
            return set()
        if isinstance(entry, (str, list)):
            return self._parse_fastapi_action_values(entry, key=key)
        if not isinstance(entry, dict):
            self._raise_fastapi_permission_config_unavailable(f"{key} must be a string, list, or object")

        if bool(entry.get("all_actions")) or bool(entry.get("unrestricted")):
            return self._all_registered_actions()
        return self._parse_fastapi_action_values(entry.get("actions", []), key=f"{key}.actions")

    def _actions_from_fastapi(self, *, current_user: CurrentUser) -> set[str]:
        payload = self._load_fastapi_role_action_config()
        users = payload.get("users", {})
        roles = payload.get("roles", {})
        if users is None:
            users = {}
        if roles is None:
            roles = {}
        if not isinstance(users, dict):
            self._raise_fastapi_permission_config_unavailable("users must be an object")
        if not isinstance(roles, dict):
            self._raise_fastapi_permission_config_unavailable("roles must be an object")

        action_set: set[str] = set()
        action_set.update(
            self._actions_from_fastapi_entry(
                users.get(current_user.username),
                key=f"users.{current_user.username}",
            )
        )
        for role in current_user.roles:
            role_name = role.strip()
            if not role_name:
                continue
            if ":" in role_name:
                action_set.add(role_name)
                continue
            action_set.update(
                self._actions_from_fastapi_entry(
                    roles.get(role_name),
                    key=f"roles.{role_name}",
                )
            )
        return normalize_actions(action_set)

    def _actions_from_current_roles_only(self, *, current_user: CurrentUser) -> set[str]:
        """Resolve role actions without external permission-source dependency."""
        action_set = get_static_actions_for_roles(current_user.roles)
        for role in current_user.roles:
            action_set.update(ERP_ROLE_ACTIONS.get(role, set()))
        return action_set

    def _actions_from_erpnext(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        resource_item_code: str | None,
        resource_status: str | None,
        resource_no: str | None,
    ) -> set[str]:
        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        roles = adapter.get_user_roles(current_user=current_user)
        user_permissions = adapter.get_user_permissions(username=current_user.username)

        action_set: set[str] = set()
        for role in roles:
            action_set.update(ERP_ROLE_ACTIONS.get(role, set()))

        if resource_item_code and not adapter.is_item_permitted(item_code=resource_item_code, user_permissions=user_permissions):
            return set()

        if resource_status == "inactive":
            action_set.discard(BOM_DEACTIVATE)
            action_set.discard(BOM_CANCEL)

        # Workflow 动作适配（若工作流动作已接入 ERPNext）。
        # 通过动作名关键字宽松映射，不阻塞当前 Sprint 开发。
        workflow_actions = adapter.get_workflow_actions(doctype="BOM", docname=resource_no)
        mapped_from_workflow = self._map_workflow_actions(workflow_actions)
        action_set.update(mapped_from_workflow)

        return action_set

    def _raise_permission_source_unavailable(
        self,
        *,
        exc: PermissionSourceUnavailable,
        request_obj: Request,
        current_user: CurrentUser,
        module: str,
        action: str,
        resource_type: str | None,
        resource_id: int | None,
        resource_no: str | None,
    ) -> None:
        request_id = get_request_id_from_request(request_obj)
        safe_detail = exc.sanitized_detail()
        log_safe_error(
            logger,
            "permission_source_unavailable",
            exc,
            request_id=request_id,
            extra={
                "error_code": PERMISSION_SOURCE_UNAVAILABLE_CODE,
                "module": module,
                "action": action,
                "resource_type": resource_type or "",
                "resource_id": resource_id if resource_id is not None else "",
                "user_id": current_user.username,
            },
        )
        self._record_security_audit_safe(
            event_type=PERMISSION_SOURCE_UNAVAILABLE_CODE,
            module=module,
            action=action,
            resource_type=resource_type.upper() if resource_type else None,
            resource_id=resource_id,
            resource_no=resource_no,
            user=current_user,
            deny_reason=(sanitize_log_message(f"{exc.exception_type}: {safe_detail}") or REDACTED_MESSAGE)[:255],
            request_obj=request_obj,
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": PERMISSION_SOURCE_UNAVAILABLE_CODE,
                "message": "权限来源暂时不可用",
                "data": None,
            },
        ) from exc

    def _resolve_forbidden_reason(
        self,
        *,
        current_user: CurrentUser,
        request_obj: Request,
        action: str,
        module: str,
        resource_type: str | None,
        resource_id: int | None,
    ) -> tuple[str, str | None]:
        deny_reason = f"缺少动作权限: {action}"
        if resource_type != "bom" or resource_id is None:
            return deny_reason, None

        bom = self.session.query(LyApparelBom).filter(LyApparelBom.id == resource_id).first()
        if not bom:
            return deny_reason, None
        resource_no = str(bom.item_code)

        if get_permission_source() != "erpnext":
            return deny_reason, resource_no

        adapter = ERPNextPermissionAdapter(request_obj=request_obj)
        try:
            user_permissions = adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable as exc:
            self._raise_permission_source_unavailable(
                exc=exc,
                request_obj=request_obj,
                current_user=current_user,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
            )
        if not adapter.is_item_permitted(item_code=str(bom.item_code), user_permissions=user_permissions):
            return "资源权限不足：无权访问该 BOM 对应 item_code", resource_no
        return deny_reason, resource_no

    def _record_security_audit_safe(
        self,
        *,
        event_type: str,
        module: str,
        action: str | None,
        resource_type: str | None,
        resource_id: int | None,
        resource_no: str | None,
        user: CurrentUser | None,
        deny_reason: str,
        request_obj: Request,
        reason_code: str | None = None,
        resource_scope: dict[str, Any] | None = None,
        raise_on_failure: bool = False,
    ) -> None:
        try:
            AuditService(self.session).record_security_audit(
                event_type=event_type,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=resource_no,
                user=user,
                deny_reason=deny_reason,
                permission_source=get_permission_source(),
                request_obj=request_obj,
                reason_code=reason_code,
                resource_scope=resource_scope,
            )
            self.session.commit()
            request_obj.state.security_audit_recorded = True
        except Exception as exc:
            self.session.rollback()
            request_id = get_request_id_from_request(request_obj)
            log_safe_error(
                logger,
                "security_audit_write_failed",
                exc,
                request_id=request_id,
                extra={
                    "error_code": "AUDIT_WRITE_FAILED",
                    "module": module,
                    "action": action or "",
                    "resource_type": resource_type or "",
                    "resource_id": resource_id if resource_id is not None else "",
                    "user_id": user.username if user else "",
                },
            )
            if raise_on_failure:
                raise AuditWriteFailed() from exc

    @staticmethod
    def _map_workflow_actions(workflow_actions: list[str]) -> set[str]:
        action_set: set[str] = set()
        for action in workflow_actions:
            text = action.strip().lower()
            if "publish" in text or "发布" in text:
                action_set.add(BOM_PUBLISH)
            if "submit" in text or "提交" in text:
                action_set.add(BOM_SUBMIT)
            if "deactivate" in text or "停用" in text:
                action_set.add(BOM_DEACTIVATE)
            if "cancel" in text or "作废" in text:
                action_set.add(BOM_CANCEL)
            if "default" in text or "默认" in text:
                action_set.add(BOM_SET_DEFAULT)
            if "update" in text or "edit" in text or "更新" in text:
                action_set.add(BOM_UPDATE)
        return action_set

    @staticmethod
    def _filter_actions_by_module(*, action_set: set[str], module: str) -> set[str]:
        registered_actions = MODULE_ACTION_REGISTRY.get(module)
        if registered_actions is not None:
            return {action for action in action_set if action in registered_actions}
        if module:
            prefix = f"{module}:"
            return {action for action in action_set if action.startswith(prefix)}
        return action_set

    @staticmethod
    def _button_permissions(*, module: str, actions: set[str], status: str | None) -> dict[str, bool]:
        base = {
            "create": False,
            "update": False,
            "publish": False,
            "deactivate": False,
            "set_default": False,
            "read": False,
            "ticket_register": False,
            "ticket_reversal": False,
            "ticket_batch": False,
            "wage_read": False,
            "wage_rate_read": False,
            "wage_rate_read_all": False,
            "wage_rate_manage": False,
            "wage_rate_manage_all": False,
            "wage_payment_create": False,
            "wage_payment_cancel": False,
            "job_card_sync": False,
            "issue_material": False,
            "receive": False,
            "inspect": False,
            "cancel": False,
            "stock_sync_retry": False,
            "stock_sync_worker": False,
            "settlement_read": False,
            "settlement_lock": False,
            "settlement_release": False,
            "plan_create": False,
            "material_check": False,
            "material_issue": False,
            "work_order_create": False,
            "work_order_worker": False,
            "snapshot_create": False,
            "factory_statement_create": False,
            "factory_statement_read": False,
            "factory_statement_confirm": False,
            "factory_statement_cancel": False,
            "factory_statement_payable_draft_create": False,
            "factory_statement_payable_draft_worker": False,
            "factory_statement_payment_create": False,
            "finance_approval_read": False,
            "finance_approval_manage": False,
            "payment_create": False,
            "payment_cancel": False,
            "manage": False,
            "write": False,
            "retry": False,
            "dry_run": False,
            "diagnostic": False,
            "worker": False,
            "export": False,
            "confirm": False,
            "permission_audit_read": False,
            "permission_audit_manage": False,
            "permission_audit_diagnostic": False,
            "erpnext_adapter_read": False,
            "erpnext_adapter_dry_run": False,
            "erpnext_adapter_diagnostic": False,
            "outbox_read": False,
            "outbox_retry": False,
            "outbox_manage": False,
            "outbox_dry_run": False,
            "outbox_diagnostic": False,
            "outbox_worker": False,
            "frontend_contract_read": False,
            "frontend_contract_manage": False,
            "frontend_contract_diagnostic": False,
            "sales_read": False,
            "sales_export": False,
            "sales_inventory_read": False,
            "sales_inventory_write": False,
            "sales_inventory_export": False,
            "sales_inventory_diagnostic": False,
            "inventory_read": False,
            "inventory_export": False,
            "master_data_read": False,
            "master_data_manage": False,
            "sample_read": False,
            "sample_manage": False,
            "material_purchase_read": False,
            "material_purchase_write": False,
            "stock_entry_draft": False,
            "stock_entry_cancel": False,
            "inventory_count": False,
            "report_read": False,
            "report_export": False,
            "report_diagnostic": False,
            "system_read": False,
            "system_config_read": False,
            "system_dictionary_read": False,
            "system_diagnostic": False,
            "quality_read": False,
            "quality_create": False,
            "quality_update": False,
            "quality_confirm": False,
            "quality_release": False,
            "quality_rework": False,
            "quality_cancel": False,
            "quality_export": False,
            "quality_dry_run": False,
            "quality_diagnostic": False,
            "quality_worker": False,
            "dashboard_read": False,
        }

        if module == "workshop":
            base["read"] = WORKSHOP_READ in actions
            base["ticket_register"] = WORKSHOP_TICKET_REGISTER in actions
            base["ticket_reversal"] = WORKSHOP_TICKET_REVERSAL in actions
            base["ticket_batch"] = WORKSHOP_TICKET_BATCH in actions
            base["wage_read"] = WORKSHOP_WAGE_READ in actions
            base["wage_rate_read"] = WORKSHOP_WAGE_RATE_READ in actions
            base["wage_rate_read_all"] = WORKSHOP_WAGE_RATE_READ_ALL in actions
            base["wage_rate_manage"] = WORKSHOP_WAGE_RATE_MANAGE in actions
            base["wage_rate_manage_all"] = WORKSHOP_WAGE_RATE_MANAGE_ALL in actions
            base["wage_payment_create"] = WORKSHOP_WAGE_PAYMENT_CREATE in actions
            base["wage_payment_cancel"] = WORKSHOP_WAGE_PAYMENT_CANCEL in actions
            base["payment_create"] = WORKSHOP_WAGE_PAYMENT_CREATE in actions
            base["payment_cancel"] = WORKSHOP_WAGE_PAYMENT_CANCEL in actions
            base["job_card_sync"] = WORKSHOP_JOB_CARD_SYNC in actions
            return base
        if module == "subcontract":
            base["read"] = SUBCONTRACT_READ in actions
            base["create"] = SUBCONTRACT_CREATE in actions
            base["issue_material"] = SUBCONTRACT_ISSUE_MATERIAL in actions
            base["receive"] = SUBCONTRACT_RECEIVE in actions
            base["inspect"] = SUBCONTRACT_INSPECT in actions
            base["cancel"] = SUBCONTRACT_CANCEL in actions
            base["stock_sync_retry"] = SUBCONTRACT_STOCK_SYNC_RETRY in actions
            base["stock_sync_worker"] = SUBCONTRACT_STOCK_SYNC_WORKER in actions
            base["settlement_read"] = SUBCONTRACT_SETTLEMENT_READ in actions
            base["settlement_lock"] = SUBCONTRACT_SETTLEMENT_LOCK in actions
            base["settlement_release"] = SUBCONTRACT_SETTLEMENT_RELEASE in actions
            return base
        if module == "production":
            base["read"] = PRODUCTION_READ in actions
            base["plan_create"] = PRODUCTION_PLAN_CREATE in actions
            base["material_check"] = PRODUCTION_MATERIAL_CHECK in actions
            base["material_issue"] = PRODUCTION_MATERIAL_ISSUE in actions
            base["work_order_create"] = PRODUCTION_WORK_ORDER_CREATE in actions
            base["job_card_sync"] = PRODUCTION_JOB_CARD_SYNC in actions
            base["work_order_worker"] = PRODUCTION_WORK_ORDER_WORKER in actions
            return base
        if module == "warehouse":
            base["read"] = WAREHOUSE_READ in actions
            base["create"] = WAREHOUSE_STOCK_ENTRY_DRAFT in actions or WAREHOUSE_INVENTORY_COUNT in actions
            base["cancel"] = WAREHOUSE_STOCK_ENTRY_CANCEL in actions
            base["export"] = WAREHOUSE_EXPORT in actions
            base["diagnostic"] = WAREHOUSE_DIAGNOSTIC in actions
            base["worker"] = WAREHOUSE_WORKER in actions
            base["stock_entry_draft"] = WAREHOUSE_STOCK_ENTRY_DRAFT in actions
            base["stock_entry_cancel"] = WAREHOUSE_STOCK_ENTRY_CANCEL in actions
            base["inventory_count"] = WAREHOUSE_INVENTORY_COUNT in actions
            return base
        if module == "style_profit":
            base["read"] = STYLE_PROFIT_READ in actions
            base["snapshot_create"] = STYLE_PROFIT_SNAPSHOT_CREATE in actions
            return base
        if module == "factory_statement":
            base["read"] = FACTORY_STATEMENT_READ in actions
            base["create"] = FACTORY_STATEMENT_CREATE in actions
            base["confirm"] = FACTORY_STATEMENT_CONFIRM in actions
            base["cancel"] = FACTORY_STATEMENT_CANCEL in actions
            base["factory_statement_read"] = FACTORY_STATEMENT_READ in actions
            base["factory_statement_create"] = FACTORY_STATEMENT_CREATE in actions
            base["factory_statement_confirm"] = FACTORY_STATEMENT_CONFIRM in actions
            base["factory_statement_cancel"] = FACTORY_STATEMENT_CANCEL in actions
            base["factory_statement_payable_draft_create"] = FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE in actions
            base["factory_statement_payable_draft_worker"] = FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER in actions
            base["payment_create"] = FACTORY_STATEMENT_PAYMENT_CREATE in actions
            base["factory_statement_payment_create"] = FACTORY_STATEMENT_PAYMENT_CREATE in actions
            base["payment_cancel"] = FACTORY_STATEMENT_PAYMENT_CANCEL in actions
            base["factory_statement_payment_cancel"] = FACTORY_STATEMENT_PAYMENT_CANCEL in actions
            return base
        if module == "finance_approval":
            base["read"] = FINANCE_APPROVAL_READ in actions
            base["manage"] = FINANCE_APPROVAL_MANAGE in actions
            base["create"] = base["manage"]
            base["update"] = base["manage"]
            base["confirm"] = base["manage"]
            base["cancel"] = base["manage"]
            base["finance_approval_read"] = base["read"]
            base["finance_approval_manage"] = base["manage"]
            return base
        if module == "sales_inventory":
            base["read"] = SALES_INVENTORY_READ in actions
            base["write"] = SALES_INVENTORY_WRITE in actions
            base["create"] = base["write"]
            base["update"] = base["write"]
            base["export"] = SALES_INVENTORY_EXPORT in actions
            base["diagnostic"] = SALES_INVENTORY_DIAGNOSTIC in actions
            base["sales_inventory_read"] = base["read"]
            base["sales_inventory_write"] = base["write"]
            base["sales_inventory_export"] = base["export"]
            base["sales_inventory_diagnostic"] = base["diagnostic"]
            return base
        if module == "master_data":
            base["read"] = MASTER_DATA_READ in actions
            base["manage"] = MASTER_DATA_MANAGE in actions
            base["create"] = base["manage"]
            base["update"] = base["manage"]
            base["master_data_read"] = base["read"]
            base["master_data_manage"] = base["manage"]
            return base
        if module == "sample":
            base["read"] = SAMPLE_READ in actions
            base["manage"] = SAMPLE_MANAGE in actions
            base["create"] = base["manage"]
            base["update"] = base["manage"]
            base["sample_read"] = base["read"]
            base["sample_manage"] = base["manage"]
            return base
        if module == "style_master":
            base["read"] = STYLE_MASTER_READ in actions
            base["manage"] = STYLE_MASTER_MANAGE in actions
            base["create"] = base["manage"]
            base["update"] = base["manage"]
            base["deactivate"] = base["manage"]
            base["write"] = base["manage"]
            return base
        if module == "material_purchase":
            base["read"] = MATERIAL_PURCHASE_READ in actions
            base["write"] = MATERIAL_PURCHASE_WRITE in actions
            base["create"] = base["write"]
            base["update"] = base["write"]
            base["material_purchase_read"] = base["read"]
            base["material_purchase_write"] = base["write"]
            return base
        if module == "report":
            base["read"] = REPORT_READ in actions
            base["export"] = REPORT_EXPORT in actions
            base["diagnostic"] = REPORT_DIAGNOSTIC in actions
            base["report_read"] = base["read"]
            base["report_export"] = base["export"]
            base["report_diagnostic"] = base["diagnostic"]
            return base
        if module == "system":
            base["read"] = SYSTEM_READ in actions
            base["config_read"] = SYSTEM_CONFIG_READ in actions
            base["dictionary_read"] = SYSTEM_DICTIONARY_READ in actions
            base["diagnostic"] = SYSTEM_DIAGNOSTIC in actions
            base["system_read"] = base["read"]
            base["system_config_read"] = base["config_read"]
            base["system_dictionary_read"] = base["dictionary_read"]
            base["system_diagnostic"] = base["diagnostic"]
            return base
        if module == "permission_audit":
            base["read"] = "permission_audit:read" in actions
            base["manage"] = "permission_audit:manage" in actions
            base["diagnostic"] = "permission_audit:diagnostic" in actions
            base["permission_audit_read"] = base["read"]
            base["permission_audit_manage"] = base["manage"]
            base["permission_audit_diagnostic"] = base["diagnostic"]
            return base
        if module == "erpnext_adapter":
            base["read"] = "erpnext_adapter:read" in actions
            base["dry_run"] = "erpnext_adapter:dry_run" in actions
            base["diagnostic"] = "erpnext_adapter:diagnostic" in actions
            base["erpnext_adapter_read"] = base["read"]
            base["erpnext_adapter_dry_run"] = base["dry_run"]
            base["erpnext_adapter_diagnostic"] = base["diagnostic"]
            return base
        if module == "outbox":
            base["read"] = "outbox:read" in actions
            base["retry"] = "outbox:retry" in actions
            base["manage"] = "outbox:manage" in actions
            base["dry_run"] = "outbox:dry_run" in actions
            base["diagnostic"] = "outbox:diagnostic" in actions
            base["worker"] = "outbox:worker" in actions
            base["outbox_read"] = base["read"]
            base["outbox_retry"] = base["retry"]
            base["outbox_manage"] = base["manage"]
            base["outbox_dry_run"] = base["dry_run"]
            base["outbox_diagnostic"] = base["diagnostic"]
            base["outbox_worker"] = base["worker"]
            return base
        if module == "frontend_contract":
            base["read"] = "frontend_contract:read" in actions
            base["manage"] = "frontend_contract:manage" in actions
            base["diagnostic"] = "frontend_contract:diagnostic" in actions
            base["frontend_contract_read"] = base["read"]
            base["frontend_contract_manage"] = base["manage"]
            base["frontend_contract_diagnostic"] = base["diagnostic"]
            return base
        if module == "sales":
            base["read"] = "sales:read" in actions
            base["export"] = "sales:export" in actions
            base["sales_read"] = base["read"]
            base["sales_export"] = base["export"]
            return base
        if module == "inventory":
            base["read"] = "inventory:read" in actions
            base["export"] = "inventory:export" in actions
            base["inventory_read"] = base["read"]
            base["inventory_export"] = base["export"]
            return base
        if module == "quality":
            base["read"] = QUALITY_READ in actions
            base["create"] = QUALITY_CREATE in actions
            base["update"] = QUALITY_UPDATE in actions
            base["confirm"] = QUALITY_CONFIRM in actions
            base["release"] = QUALITY_RELEASE in actions
            base["rework"] = QUALITY_REWORK in actions
            base["cancel"] = QUALITY_CANCEL in actions
            base["export"] = QUALITY_EXPORT in actions
            base["dry_run"] = "quality:dry_run" in actions
            base["diagnostic"] = QUALITY_DIAGNOSTIC in actions
            base["worker"] = "quality:worker" in actions
            base["quality_read"] = base["read"]
            base["quality_create"] = base["create"]
            base["quality_update"] = base["update"]
            base["quality_confirm"] = base["confirm"]
            base["quality_release"] = base["release"]
            base["quality_rework"] = base["rework"]
            base["quality_cancel"] = base["cancel"]
            base["quality_export"] = base["export"]
            base["quality_dry_run"] = base["dry_run"]
            base["quality_diagnostic"] = base["diagnostic"]
            base["quality_worker"] = base["worker"]
            return base
        if module == "dashboard":
            base["read"] = "dashboard:read" in actions
            base["dashboard_read"] = base["read"]
            return base

        can_update = BOM_UPDATE in actions and status != "active"
        can_publish = BOM_PUBLISH in actions and status != "active"
        can_deactivate = BOM_DEACTIVATE in actions and status == "active"
        can_set_default = BOM_SET_DEFAULT in actions and status == "active"
        base["create"] = BOM_CREATE in actions
        base["update"] = can_update
        base["publish"] = can_publish
        base["deactivate"] = can_deactivate
        base["set_default"] = can_set_default
        base["read"] = BOM_READ in actions
        return base

    @staticmethod
    def to_dict(agg: PermissionAggregation) -> dict[str, Any]:
        return {
            "username": agg.username,
            "module": agg.module,
            "actions": agg.actions,
            "button_permissions": agg.button_permissions,
            "resource_type": agg.resource_type,
            "resource_id": agg.resource_id,
            "status": agg.status,
        }
