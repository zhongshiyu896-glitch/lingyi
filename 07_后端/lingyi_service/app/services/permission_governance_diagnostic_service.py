"""Readonly health diagnostic service for permission governance (TASK-070D)."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone

from app.core.permissions import DEFAULT_STATIC_ROLE_ACTIONS
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import PERMISSION_AUDIT_DIAGNOSTIC
from app.core.permissions import PERMISSION_GOVERNANCE_AUDIT_READ
from app.core.permissions import PERMISSION_GOVERNANCE_DIAGNOSTIC
from app.core.permissions import PERMISSION_GOVERNANCE_EXPORT
from app.core.permissions import PERMISSION_READ
from app.schemas.permission_governance import PermissionGovernanceDiagnosticCheck
from app.schemas.permission_governance import PermissionGovernanceDiagnosticData

_WRITE_OR_MANAGE_SUFFIXES = (
    ":create",
    ":update",
    ":confirm",
    ":cancel",
    ":submit",
    ":manage",
    ":rollback",
    ":approval",
)


class PermissionGovernanceDiagnosticService:
    """Build static diagnostic summary without DB/ERP access."""

    @classmethod
    def get_diagnostic_summary(cls) -> PermissionGovernanceDiagnosticData:
        permission_actions = sorted(MODULE_ACTION_REGISTRY.get("permission", set()))
        legacy_actions = sorted(MODULE_ACTION_REGISTRY.get("permission_audit", set()))
        high_risk_actions = sorted(action for action in permission_actions if cls._is_high_risk(action))
        ui_hidden_actions = sorted(action for action in permission_actions if not cls._is_ui_exposed(action))
        roles_with_permission_actions_count = sum(
            1
            for actions in DEFAULT_STATIC_ROLE_ACTIONS.values()
            if any(cls._is_permission_action(action) for action in actions)
        )

        checks = cls._build_checks(
            permission_actions=permission_actions,
            legacy_actions=legacy_actions,
            high_risk_actions=high_risk_actions,
            ui_hidden_actions=ui_hidden_actions,
        )
        status = "ok" if all(check.status == "pass" for check in checks) else "degraded"

        return PermissionGovernanceDiagnosticData(
            module="permission",
            status=status,
            registered_actions=permission_actions,
            legacy_permission_audit_actions=legacy_actions,
            high_risk_actions=high_risk_actions,
            ui_hidden_actions=ui_hidden_actions,
            roles_with_permission_actions_count=roles_with_permission_actions_count,
            checks=checks,
            catalog_enabled=True,
            roles_matrix_enabled=True,
            audit_read_enabled=True,
            export_enabled=True,
            diagnostic_enabled=True,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    @classmethod
    def _build_checks(
        cls,
        *,
        permission_actions: list[str],
        legacy_actions: list[str],
        high_risk_actions: list[str],
        ui_hidden_actions: list[str],
    ) -> list[PermissionGovernanceDiagnosticCheck]:
        def _check(name: str, passed: bool, failed_message: str) -> PermissionGovernanceDiagnosticCheck:
            if passed:
                return PermissionGovernanceDiagnosticCheck(name=name, status="pass")
            return PermissionGovernanceDiagnosticCheck(name=name, status="fail", message=failed_message)

        has_wildcard = any(action.startswith("permission:*") or "*" in action for action in permission_actions)

        return [
            _check(
                "permission:read_registered",
                PERMISSION_READ in permission_actions,
                "permission:read 未注册",
            ),
            _check(
                "permission:audit_read_registered",
                PERMISSION_GOVERNANCE_AUDIT_READ in permission_actions,
                "permission:audit_read 未注册",
            ),
            _check(
                "permission:export_registered",
                PERMISSION_GOVERNANCE_EXPORT in permission_actions,
                "permission:export 未注册",
            ),
            _check(
                "permission:diagnostic_registered",
                PERMISSION_GOVERNANCE_DIAGNOSTIC in permission_actions,
                "permission:diagnostic 未注册",
            ),
            _check(
                "permission_diagnostic_hidden",
                PERMISSION_GOVERNANCE_DIAGNOSTIC in ui_hidden_actions,
                "permission:diagnostic 应为前端隐藏动作",
            ),
            _check(
                "permission_diagnostic_high_risk",
                PERMISSION_GOVERNANCE_DIAGNOSTIC in high_risk_actions,
                "permission:diagnostic 应为高危动作",
            ),
            _check(
                "permission_audit_legacy_kept",
                PERMISSION_AUDIT_DIAGNOSTIC in legacy_actions,
                "permission_audit:diagnostic 兼容动作缺失",
            ),
            _check(
                "no_wildcard_permission_action",
                not has_wildcard,
                "permission 模块不允许通配符动作",
            ),
        ]

    @staticmethod
    def _is_permission_action(action: str) -> bool:
        return action.strip().lower().startswith("permission:")

    @staticmethod
    def _is_high_risk(action: str) -> bool:
        normalized = action.strip().lower()
        if "worker" in normalized or "internal" in normalized:
            return True
        if normalized.endswith(":read"):
            return False
        if normalized.endswith(":export"):
            return False
        if normalized.endswith(":diagnostic"):
            return True
        if normalized.endswith(_WRITE_OR_MANAGE_SUFFIXES):
            return True
        return True

    @staticmethod
    def _is_ui_exposed(action: str) -> bool:
        normalized = action.strip().lower()
        if "worker" in normalized or "internal" in normalized:
            return False
        if normalized.endswith(":diagnostic"):
            return False
        if normalized.endswith(":read"):
            return True
        if normalized.endswith(":export"):
            return True
        if normalized.endswith(_WRITE_OR_MANAGE_SUFFIXES):
            return True
        return False
