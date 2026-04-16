"""Permission aggregation service for module actions.

核心读动作：`bom:read`。
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
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
from app.core.permissions import SALES_INVENTORY_DIAGNOSTIC
from app.core.permissions import SALES_INVENTORY_EXPORT
from app.core.permissions import SALES_INVENTORY_READ
from app.core.permissions import QUALITY_CANCEL
from app.core.permissions import QUALITY_CONFIRM
from app.core.permissions import QUALITY_CREATE
from app.core.permissions import QUALITY_DIAGNOSTIC
from app.core.permissions import QUALITY_EXPORT
from app.core.permissions import QUALITY_READ
from app.core.permissions import QUALITY_UPDATE
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
        WORKSHOP_JOB_CARD_SYNC,
        PRODUCTION_READ,
        PRODUCTION_PLAN_CREATE,
        PRODUCTION_MATERIAL_CHECK,
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
        SALES_INVENTORY_READ,
        SALES_INVENTORY_EXPORT,
    },
    "Sales Manager": {
        STYLE_PROFIT_READ,
        SALES_INVENTORY_READ,
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
        if get_permission_source() != "erpnext":
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

        if get_permission_source() != "erpnext":
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
        if get_permission_source() != "erpnext":
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

        if get_permission_source() != "erpnext":
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

        if get_permission_source() != "erpnext":
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
        if get_permission_source() != "erpnext":
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
        if get_permission_source() != "erpnext":
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

        if get_permission_source() != "erpnext":
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
        if get_permission_source() != "erpnext":
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

        if get_permission_source() != "erpnext":
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
        if get_permission_source() != "erpnext":
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

        if get_permission_source() != "erpnext":
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
        if get_permission_source() != "erpnext":
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

        if get_permission_source() != "erpnext":
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
        if get_permission_source() != "erpnext":
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
        if not PermissionService._static_warning_emitted:
            # 临时方案，生产前替换为 ERPNext 权限来源。
            logger.warning("LINGYI_PERMISSION_SOURCE=static 临时权限来源，不可用于生产")
            PermissionService._static_warning_emitted = True
        return get_static_actions_for_roles(current_user.roles)

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
            "work_order_create": False,
            "work_order_worker": False,
            "snapshot_create": False,
            "factory_statement_create": False,
            "factory_statement_read": False,
            "factory_statement_confirm": False,
            "factory_statement_cancel": False,
            "factory_statement_payable_draft_create": False,
            "factory_statement_payable_draft_worker": False,
            "manage": False,
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
            "inventory_read": False,
            "inventory_export": False,
            "quality_read": False,
            "quality_create": False,
            "quality_update": False,
            "quality_confirm": False,
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
            base["work_order_create"] = PRODUCTION_WORK_ORDER_CREATE in actions
            base["job_card_sync"] = PRODUCTION_JOB_CARD_SYNC in actions
            base["work_order_worker"] = PRODUCTION_WORK_ORDER_WORKER in actions
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
            base["read"] = "quality:read" in actions
            base["create"] = "quality:create" in actions
            base["update"] = "quality:update" in actions
            base["confirm"] = "quality:confirm" in actions
            base["cancel"] = "quality:cancel" in actions
            base["export"] = "quality:export" in actions
            base["dry_run"] = "quality:dry_run" in actions
            base["diagnostic"] = "quality:diagnostic" in actions
            base["worker"] = "quality:worker" in actions
            base["quality_read"] = base["read"]
            base["quality_create"] = base["create"]
            base["quality_update"] = base["update"]
            base["quality_confirm"] = base["confirm"]
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
