"""Adapter for querying ERPNext permission facts."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import json
import os
from typing import Any
from urllib import error
from urllib import parse
from urllib import request

from fastapi import Request

from app.core.auth import CurrentUser
from app.core.exceptions import PermissionSourceUnavailable


@dataclass(frozen=True)
class UserPermissionResult:
    """Structured ERPNext user permission facts."""

    source_available: bool
    unrestricted: bool
    allowed_items: set[str]
    allowed_companies: set[str]
    allowed_suppliers: set[str] = field(default_factory=set)
    allowed_warehouses: set[str] = field(default_factory=set)
    allowed_customers: set[str] = field(default_factory=set)


class ERPNextPermissionAdapter:
    """Read ERPNext role, user permission and workflow action facts."""

    def __init__(self, request_obj: Request):
        self.request_obj = request_obj
        self.base_url = os.getenv("LINGYI_ERPNEXT_BASE_URL", "").strip().rstrip("/")

    def get_user_roles(self, current_user: CurrentUser) -> list[str]:
        """Fetch user's ERPNext roles from ERPNext authority."""
        if not self.base_url:
            return list(current_user.roles)

        username = parse.quote(current_user.username, safe="")
        fields = parse.quote('["name","roles"]', safe="")
        payload = self._get_json(f"/api/resource/User/{username}?fields={fields}")
        if not payload:
            return list(current_user.roles)

        data = payload.get("data", {})
        if not isinstance(data, dict):
            return list(current_user.roles)
        roles_raw = data.get("roles", [])
        if not isinstance(roles_raw, list):
            return list(current_user.roles)

        roles: set[str] = set()
        for role_item in roles_raw:
            if isinstance(role_item, dict):
                role_name = role_item.get("role") or role_item.get("name")
                if isinstance(role_name, str) and role_name.strip():
                    roles.add(role_name.strip())
            elif isinstance(role_item, str) and role_item.strip():
                roles.add(role_item.strip())
        return sorted(roles) or list(current_user.roles)

    def get_user_permissions(self, username: str) -> UserPermissionResult:
        """Fetch structured ERPNext User Permission facts.

        Raises:
            PermissionSourceUnavailable: ERPNext unavailable or returns invalid structure.
        """
        if not self.base_url:
            raise PermissionSourceUnavailable(
                message="ERPNext 权限来源未配置",
                exception_type="PermissionSourceUnavailable",
                exception_message="LINGYI_ERPNEXT_BASE_URL is empty",
            )

        filters = parse.quote(
            json.dumps(
                [["user", "=", username], ["applicable_for", "in", ["Item", "Company", "Supplier", "Warehouse", "Customer"]]]
            ),
            safe="",
        )
        fields = parse.quote('["allow","for_value","applicable_for"]', safe="")
        payload = self._get_json(
            f"/api/resource/User%20Permission?filters={filters}&fields={fields}&limit_page_length=200",
            strict=True,
            operation="get_user_permissions",
        )
        if not payload:
            raise PermissionSourceUnavailable(
                message="ERPNext User Permission 查询失败",
                exception_type="PermissionSourceUnavailable",
                exception_message="empty payload",
            )
        rows = payload.get("data", [])
        if not isinstance(rows, list):
            raise PermissionSourceUnavailable(
                message="ERPNext User Permission 返回结构异常",
                exception_type="PermissionSourceUnavailable",
                exception_message="payload.data is not list",
            )
        if len(rows) == 0:
            return UserPermissionResult(
                source_available=True,
                unrestricted=True,
                allowed_items=set(),
                allowed_companies=set(),
                allowed_suppliers=set(),
                allowed_warehouses=set(),
                allowed_customers=set(),
            )

        allowed_items: set[str] = set()
        allowed_companies: set[str] = set()
        allowed_suppliers: set[str] = set()
        allowed_warehouses: set[str] = set()
        allowed_customers: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                raise PermissionSourceUnavailable(
                    message="ERPNext User Permission 返回结构异常",
                    exception_type="PermissionSourceUnavailable",
                    exception_message="row is not dict",
                )
            allow = row.get("allow")
            for_value = row.get("for_value")
            if not isinstance(allow, str) or not isinstance(for_value, str):
                raise PermissionSourceUnavailable(
                    message="ERPNext User Permission 返回结构异常",
                    exception_type="PermissionSourceUnavailable",
                    exception_message="allow/for_value is invalid",
                )
            allow_name = allow.strip()
            target_value = for_value.strip()
            if not allow_name or not target_value:
                raise PermissionSourceUnavailable(
                    message="ERPNext User Permission 返回结构异常",
                    exception_type="PermissionSourceUnavailable",
                    exception_message="allow/for_value is empty",
                )
            if allow_name == "Item":
                allowed_items.add(target_value)
            elif allow_name == "Company":
                allowed_companies.add(target_value)
            elif allow_name == "Supplier":
                allowed_suppliers.add(target_value)
            elif allow_name == "Warehouse":
                allowed_warehouses.add(target_value)
            elif allow_name == "Customer":
                allowed_customers.add(target_value)

        return UserPermissionResult(
            source_available=True,
            unrestricted=False,
            allowed_items=allowed_items,
            allowed_companies=allowed_companies,
            allowed_suppliers=allowed_suppliers,
            allowed_warehouses=allowed_warehouses,
            allowed_customers=allowed_customers,
        )

    def get_workflow_actions(self, *, doctype: str, docname: str | None = None) -> list[str]:
        """Fetch workflow transitions currently executable by user."""
        if not self.base_url or not docname:
            return list()
        path = f"/api/method/frappe.model.workflow.get_transitions?doctype={parse.quote(doctype)}&docname={parse.quote(docname)}"
        payload = self._get_json(path)
        if not payload:
            return list()
        message = payload.get("message")
        if not isinstance(message, list):
            return list()
        actions: list[str] = []
        for row in message:
            if not isinstance(row, dict):
                continue
            action_name = row.get("action")
            if isinstance(action_name, str) and action_name.strip():
                actions.append(action_name.strip())
        return actions

    def is_item_permitted(self, *, item_code: str, user_permissions: UserPermissionResult) -> bool:
        """Check if target item_code is allowed by ERPNext user permissions."""
        if user_permissions.unrestricted:
            return True
        if user_permissions.allowed_items:
            return item_code in user_permissions.allowed_items
        # 仅存在 Company 级别限制但当前资源无 company 维度时，按 fail closed 拒绝。
        return False

    @staticmethod
    def is_company_permitted(*, company: str, user_permissions: UserPermissionResult) -> bool:
        """Check company-level access under ERPNext User Permission constraints."""
        if user_permissions.unrestricted:
            return True
        if user_permissions.allowed_companies:
            return company in user_permissions.allowed_companies
        return True

    @staticmethod
    def is_supplier_permitted(*, supplier: str, user_permissions: UserPermissionResult) -> bool:
        """Check supplier-level access under ERPNext User Permission constraints."""
        if user_permissions.unrestricted:
            return True
        if user_permissions.allowed_suppliers:
            return supplier in user_permissions.allowed_suppliers
        return True

    @staticmethod
    def is_warehouse_permitted(*, warehouse: str, user_permissions: UserPermissionResult) -> bool:
        """Check warehouse-level access under ERPNext User Permission constraints."""
        if user_permissions.unrestricted:
            return True
        if user_permissions.allowed_warehouses:
            return warehouse in user_permissions.allowed_warehouses
        return True

    @staticmethod
    def is_customer_permitted(*, customer: str, user_permissions: UserPermissionResult) -> bool:
        """Check customer-level access under ERPNext User Permission constraints."""
        if user_permissions.unrestricted:
            return True
        if user_permissions.allowed_customers:
            return customer in user_permissions.allowed_customers
        # Customer is a TASK-011 resource boundary. Empty customer facts under a
        # restricted permission set must not degrade into "all customers".
        return False

    def _get_json(self, path: str, *, strict: bool = False, operation: str = "") -> dict[str, Any] | None:
        headers = self._build_headers()
        if not headers:
            if strict:
                raise PermissionSourceUnavailable(
                    message="ERPNext 权限查询缺少鉴权上下文",
                    exception_type="PermissionSourceUnavailable",
                    exception_message="missing Authorization/Cookie",
                )
            return None

        req = request.Request(
            url=f"{self.base_url}{path}",
            method="GET",
            headers=headers,
        )
        try:
            with request.urlopen(req, timeout=5) as response:
                body = response.read().decode("utf-8")
        except (error.URLError, TimeoutError) as exc:
            if strict:
                raise PermissionSourceUnavailable(
                    message=f"ERPNext 权限查询失败: {operation or 'unknown'}",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                ) from exc
            return None
        except Exception as exc:
            if strict:
                raise PermissionSourceUnavailable(
                    message=f"ERPNext 权限查询失败: {operation or 'unknown'}",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                ) from exc
            return None

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            if strict:
                raise PermissionSourceUnavailable(
                    message=f"ERPNext 权限查询返回非 JSON: {operation or 'unknown'}",
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                ) from exc
            return None
        if not isinstance(payload, dict):
            if strict:
                raise PermissionSourceUnavailable(
                    message=f"ERPNext 权限查询返回结构异常: {operation or 'unknown'}",
                    exception_type="TypeError",
                    exception_message=f"payload type={type(payload)!r}",
                )
            return None
        return payload

    def _build_headers(self) -> dict[str, str] | None:
        headers: dict[str, str] = {"Accept": "application/json"}
        authorization = self.request_obj.headers.get("Authorization")
        cookie = self.request_obj.headers.get("Cookie")
        if authorization:
            headers["Authorization"] = authorization
        if cookie:
            headers["Cookie"] = cookie
        if "Authorization" not in headers and "Cookie" not in headers:
            return None
        return headers
