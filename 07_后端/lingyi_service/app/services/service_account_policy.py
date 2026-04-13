"""Service-account scoped resource policy for workshop worker (TASK-003G)."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from fastapi import Request

from app.core.auth import CurrentUser
from app.core.exceptions import PermissionSourceUnavailable
from app.core.exceptions import ServiceAccountResourceForbiddenError
from app.core.permissions import get_permission_source
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult


@dataclass(frozen=True)
class ServiceAccountResourcePolicy:
    """Resolved service-account resource scope."""

    username: str
    allowed_companies: set[str]
    allowed_items: set[str]

    def can_access(self, *, company: str, item_code: str) -> bool:
        return company in self.allowed_companies and item_code in self.allowed_items

    def scope_version_hash(self) -> str:
        """Stable hash for current service-account scope snapshot."""
        payload = {
            "allowed_companies": sorted(self.allowed_companies),
            "allowed_items": sorted(self.allowed_items),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def scope_hash_for_resource(self, *, company: str | None, item_code: str | None) -> str:
        """Build resource+scope hash used for denial dedupe."""
        payload = {
            "company": (company or "").strip(),
            "item_code": (item_code or "").strip(),
            "scope_version": self.scope_version_hash(),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ServiceAccountPolicyService:
    """Resolve ERPNext-driven minimal resource scope for service-account worker."""

    def __init__(self, request_obj: Request):
        self.request_obj = request_obj
        self.adapter = ERPNextPermissionAdapter(request_obj=request_obj)

    def get_worker_policy(self, *, current_user: CurrentUser) -> ServiceAccountResourcePolicy:
        """Load strict worker scope from ERPNext User Permission.

        Fail-closed rules:
        - permission source must be ERPNext;
        - unrestricted permissions are not accepted for service account;
        - explicit company and item scopes are both required.
        """
        if not current_user.is_service_account:
            raise ServiceAccountResourceForbiddenError("仅服务账号允许执行内部 Worker")

        if get_permission_source() != "erpnext":
            raise ServiceAccountResourceForbiddenError("服务账号资源权限必须由 ERPNext User Permission 提供")

        user_permissions = self._load_permissions(current_user=current_user)
        if user_permissions.unrestricted:
            raise ServiceAccountResourceForbiddenError("服务账号必须显式配置 Company 与 Item 资源权限")

        allowed_companies = {item.strip() for item in user_permissions.allowed_companies if item and item.strip()}
        allowed_items = {item.strip() for item in user_permissions.allowed_items if item and item.strip()}
        if not allowed_companies or not allowed_items:
            raise ServiceAccountResourceForbiddenError("服务账号缺少 Company 或 Item 资源权限")

        return ServiceAccountResourcePolicy(
            username=current_user.username,
            allowed_companies=allowed_companies,
            allowed_items=allowed_items,
        )

    def _load_permissions(self, *, current_user: CurrentUser) -> UserPermissionResult:
        try:
            return self.adapter.get_user_permissions(username=current_user.username)
        except PermissionSourceUnavailable:
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise PermissionSourceUnavailable(
                message="ERPNext User Permission 查询失败",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
            ) from exc
