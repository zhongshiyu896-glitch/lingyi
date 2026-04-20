"""Readonly permission governance service (TASK-070A/TASK-070B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta
import json

from sqlalchemy.orm import Session

from app.core.permissions import DEFAULT_STATIC_ROLE_ACTIONS
from app.core.permissions import MODULE_ACTION_REGISTRY
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.schemas.permission_governance import PermissionActionCatalogData
from app.schemas.permission_governance import PermissionActionCatalogEntry
from app.schemas.permission_governance import PermissionActionCatalogModule
from app.schemas.permission_governance import PermissionOperationAuditItemData
from app.schemas.permission_governance import PermissionOperationAuditListData
from app.schemas.permission_governance import PermissionRoleMatrixData
from app.schemas.permission_governance import PermissionRoleMatrixEntry
from app.schemas.permission_governance import PermissionSecurityAuditItemData
from app.schemas.permission_governance import PermissionSecurityAuditListData


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

_SENSITIVE_KEYWORDS = (
    "token",
    "password",
    "secret",
    "authorization",
    "cookie",
    "dsn",
    "database_url",
)


@dataclass(frozen=True)
class ActionClassification:
    """Derived catalog attributes for one action."""

    category: str
    is_high_risk: bool
    ui_exposed: bool


class PermissionGovernanceService:
    """Build static read-only views for permission governance."""

    @classmethod
    def get_actions_catalog(cls) -> PermissionActionCatalogData:
        modules: list[PermissionActionCatalogModule] = []
        for module in sorted(MODULE_ACTION_REGISTRY.keys()):
            module_actions = sorted(MODULE_ACTION_REGISTRY.get(module, set()))
            actions = [cls._to_catalog_entry(action=action) for action in module_actions]
            modules.append(PermissionActionCatalogModule(module=module, actions=actions))
        return PermissionActionCatalogData(modules=modules)

    @classmethod
    def get_roles_matrix(cls) -> PermissionRoleMatrixData:
        rows: list[PermissionRoleMatrixEntry] = []
        for role in sorted(DEFAULT_STATIC_ROLE_ACTIONS.keys()):
            actions = sorted(DEFAULT_STATIC_ROLE_ACTIONS.get(role, set()))
            modules = sorted({cls._module_of_action(action) for action in actions if cls._module_of_action(action)})
            high_risk_actions = sorted(
                action
                for action in actions
                if cls._classify_action(action=action).is_high_risk
            )
            ui_hidden_actions = sorted(
                action
                for action in actions
                if not cls._classify_action(action=action).ui_exposed
            )
            rows.append(
                PermissionRoleMatrixEntry(
                    role=role,
                    actions=actions,
                    modules=modules,
                    high_risk_actions=high_risk_actions,
                    ui_hidden_actions=ui_hidden_actions,
                )
            )
        return PermissionRoleMatrixData(roles=rows)

    @classmethod
    def list_security_audits(
        cls,
        *,
        session: Session,
        from_date: date | None,
        to_date: date | None,
        module: str | None,
        action: str | None,
        request_id: str | None,
        resource_type: str | None,
        resource_id: str | None,
        event_type: str | None,
        user_id: str | None,
        page: int,
        page_size: int,
    ) -> PermissionSecurityAuditListData:
        query = session.query(LySecurityAuditLog)

        if from_date is not None:
            query = query.filter(LySecurityAuditLog.created_at >= cls._day_start(from_date))
        if to_date is not None:
            query = query.filter(LySecurityAuditLog.created_at < cls._day_end_exclusive(to_date))
        if module is not None:
            query = query.filter(LySecurityAuditLog.module == module)
        if action is not None:
            query = query.filter(LySecurityAuditLog.action == action)
        if request_id is not None:
            query = query.filter(LySecurityAuditLog.request_id == request_id)
        if resource_type is not None:
            query = query.filter(LySecurityAuditLog.resource_type == resource_type)
        if resource_id is not None:
            query = query.filter(LySecurityAuditLog.resource_id == resource_id)
        if event_type is not None:
            query = query.filter(LySecurityAuditLog.event_type == event_type)
        if user_id is not None:
            query = query.filter(LySecurityAuditLog.user_id == user_id)

        total = query.count()
        rows = (
            query.order_by(LySecurityAuditLog.created_at.desc(), LySecurityAuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            PermissionSecurityAuditItemData(
                id=int(row.id),
                event_type=row.event_type,
                module=row.module,
                action=row.action,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                resource_no=row.resource_no,
                user_id=row.user_id,
                permission_source=row.permission_source,
                deny_reason=row.deny_reason,
                request_method=row.request_method,
                request_path=row.request_path,
                request_id=row.request_id,
                created_at=cls._iso_datetime(row.created_at),
            )
            for row in rows
        ]
        return PermissionSecurityAuditListData(items=items, total=total, page=page, page_size=page_size)

    @classmethod
    def list_operation_audits(
        cls,
        *,
        session: Session,
        from_date: date | None,
        to_date: date | None,
        module: str | None,
        action: str | None,
        request_id: str | None,
        resource_type: str | None,
        resource_id: int | None,
        operator: str | None,
        result: str | None,
        error_code: str | None,
        page: int,
        page_size: int,
    ) -> PermissionOperationAuditListData:
        query = session.query(LyOperationAuditLog)

        if from_date is not None:
            query = query.filter(LyOperationAuditLog.created_at >= cls._day_start(from_date))
        if to_date is not None:
            query = query.filter(LyOperationAuditLog.created_at < cls._day_end_exclusive(to_date))
        if module is not None:
            query = query.filter(LyOperationAuditLog.module == module)
        if action is not None:
            query = query.filter(LyOperationAuditLog.action == action)
        if request_id is not None:
            query = query.filter(LyOperationAuditLog.request_id == request_id)
        if resource_type is not None:
            query = query.filter(LyOperationAuditLog.resource_type == resource_type)
        if resource_id is not None:
            query = query.filter(LyOperationAuditLog.resource_id == resource_id)
        if operator is not None:
            query = query.filter(LyOperationAuditLog.operator == operator)
        if result is not None:
            query = query.filter(LyOperationAuditLog.result == result)
        if error_code is not None:
            query = query.filter(LyOperationAuditLog.error_code == error_code)

        total = query.count()
        rows = (
            query.order_by(LyOperationAuditLog.created_at.desc(), LyOperationAuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = [
            PermissionOperationAuditItemData(
                id=int(row.id),
                module=row.module,
                action=row.action,
                operator=row.operator,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                resource_no=row.resource_no,
                result=row.result,
                error_code=row.error_code,
                request_id=row.request_id,
                created_at=cls._iso_datetime(row.created_at),
                has_before_data=row.before_data is not None,
                has_after_data=row.after_data is not None,
                before_keys=cls._extract_json_keys(row.before_data),
                after_keys=cls._extract_json_keys(row.after_data),
            )
            for row in rows
        ]
        return PermissionOperationAuditListData(items=items, total=total, page=page, page_size=page_size)

    @classmethod
    def _to_catalog_entry(cls, *, action: str) -> PermissionActionCatalogEntry:
        classification = cls._classify_action(action=action)
        return PermissionActionCatalogEntry(
            action=action,
            category=classification.category,
            is_high_risk=classification.is_high_risk,
            ui_exposed=classification.ui_exposed,
            description=cls._describe_action(action=action, classification=classification),
        )

    @staticmethod
    def _module_of_action(action: str) -> str:
        if ":" not in action:
            return ""
        return action.split(":", 1)[0].strip()

    @classmethod
    def _classify_action(cls, *, action: str) -> ActionClassification:
        normalized = action.strip().lower()
        if "worker" in normalized or "internal" in normalized:
            return ActionClassification(category="internal", is_high_risk=True, ui_exposed=False)
        if normalized.endswith(":read"):
            return ActionClassification(category="read", is_high_risk=False, ui_exposed=True)
        if normalized.endswith(":export"):
            return ActionClassification(category="export", is_high_risk=False, ui_exposed=True)
        if normalized.endswith(":diagnostic"):
            return ActionClassification(category="diagnostic", is_high_risk=True, ui_exposed=False)
        if normalized.endswith(_WRITE_OR_MANAGE_SUFFIXES):
            return ActionClassification(category="write_or_manage", is_high_risk=True, ui_exposed=True)
        return ActionClassification(category="unknown", is_high_risk=True, ui_exposed=False)

    @staticmethod
    def _describe_action(*, action: str, classification: ActionClassification) -> str:
        if classification.category == "read":
            return f"{action} 只读动作"
        if classification.category == "export":
            return f"{action} 导出动作"
        if classification.category == "diagnostic":
            return f"{action} 高危诊断动作（非普通前端动作）"
        if classification.category == "internal":
            return f"{action} 内部/Worker 动作（非普通前端动作）"
        if classification.category == "write_or_manage":
            return f"{action} 写入或管理动作（高危）"
        return f"{action} 未知分类动作（高危）"

    @staticmethod
    def _day_start(target: date) -> datetime:
        return datetime.combine(target, time.min)

    @staticmethod
    def _day_end_exclusive(target: date) -> datetime:
        return datetime.combine(target + timedelta(days=1), time.min)

    @staticmethod
    def _iso_datetime(value: datetime | None) -> str:
        if value is None:
            return ""
        return value.isoformat()

    @staticmethod
    def _extract_json_keys(value: object) -> list[str]:
        def _is_sensitive(name: str) -> bool:
            lowered = name.lower()
            return any(keyword in lowered for keyword in _SENSITIVE_KEYWORDS)

        if value is None:
            return []
        if isinstance(value, dict):
            return sorted(str(key) for key in value.keys() if not _is_sensitive(str(key)))
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, dict):
                return sorted(str(key) for key in parsed.keys() if not _is_sensitive(str(key)))
        return []
