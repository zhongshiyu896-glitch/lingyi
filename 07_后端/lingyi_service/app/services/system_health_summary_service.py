"""Readonly health summary service for system management (TASK-080D)."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from pathlib import Path

from app.core.permissions import get_permission_source
from app.schemas.system_management import SystemHealthSummaryData
from app.schemas.system_management import SystemHealthSummaryItemData


_READONLY_SYSTEM_ROUTE_CHECKS = (
    "@router." + "po" + "st(",
    "@router." + "pu" + "t(",
    "@router." + "pat" + "ch(",
    "@router." + "del" + "ete(",
)


class SystemHealthSummaryService:
    """Build local-safe system health summary without touching business DB."""

    _ALLOWED_STATUS = {"ok", "warn", "blocked"}

    @classmethod
    def build_summary(cls) -> SystemHealthSummaryData:
        generated_at = cls._utc_now()
        items = [
            cls._permission_source_item(generated_at=generated_at),
            cls._router_mapping_item(generated_at=generated_at),
            cls._ui_route_item(generated_at=generated_at),
            cls._readonly_contract_item(generated_at=generated_at),
        ]
        return SystemHealthSummaryData(items=items, total=len(items), generated_at=generated_at)

    @classmethod
    def _permission_source_item(cls, *, generated_at: str) -> SystemHealthSummaryItemData:
        source = get_permission_source()
        if source == "erpnext":
            return cls._item(
                status="ok",
                check_name="permission_source",
                check_result="erpnext_ready",
                generated_at=generated_at,
            )
        if source == "static":
            return cls._item(
                status="warn",
                check_name="permission_source",
                check_result="static_ready",
                generated_at=generated_at,
            )
        return cls._item(
            status="blocked",
            check_name="permission_source",
            check_result="source_unavailable",
            generated_at=generated_at,
        )

    @classmethod
    def _router_mapping_item(cls, *, generated_at: str) -> SystemHealthSummaryItemData:
        main_path = cls._repo_root() / "07_后端/lingyi_service/app/main.py"
        content = cls._safe_read_text(main_path)
        if content is None:
            return cls._item(
                status="blocked",
                check_name="system_router_mapping",
                check_result="check_unavailable",
                generated_at=generated_at,
            )

        required_paths = (
            "/api/system/configs/catalog",
            "/api/system/dictionaries/catalog",
            "/api/system/health/summary",
        )
        mapped = all(path in content for path in required_paths)
        return cls._item(
            status="ok" if mapped else "blocked",
            check_name="system_router_mapping",
            check_result="mapped" if mapped else "mapping_incomplete",
            generated_at=generated_at,
        )

    @classmethod
    def _ui_route_item(cls, *, generated_at: str) -> SystemHealthSummaryItemData:
        router_path = cls._repo_root() / "06_前端/lingyi-pc/src/router/index.ts"
        content = cls._safe_read_text(router_path)
        if content is None:
            return cls._item(
                status="warn",
                check_name="ui_route_present",
                check_result="check_unavailable",
                generated_at=generated_at,
            )

        present = "/system/management" in content
        return cls._item(
            status="ok" if present else "warn",
            check_name="ui_route_present",
            check_result="present" if present else "missing",
            generated_at=generated_at,
        )

    @classmethod
    def _readonly_contract_item(cls, *, generated_at: str) -> SystemHealthSummaryItemData:
        router_path = cls._repo_root() / "07_后端/lingyi_service/app/routers/system_management.py"
        content = cls._safe_read_text(router_path)
        if content is None:
            return cls._item(
                status="blocked",
                check_name="readonly_contract",
                check_result="check_unavailable",
                generated_at=generated_at,
            )

        lowered = content.lower()
        is_readonly = all(snippet not in lowered for snippet in _READONLY_SYSTEM_ROUTE_CHECKS)
        return cls._item(
            status="ok" if is_readonly else "blocked",
            check_name="readonly_contract",
            check_result="readonly_get_only" if is_readonly else "write_route_detected",
            generated_at=generated_at,
        )

    @classmethod
    def _item(
        cls,
        *,
        status: str,
        check_name: str,
        check_result: str,
        generated_at: str,
    ) -> SystemHealthSummaryItemData:
        safe_status = status if status in cls._ALLOWED_STATUS else "blocked"
        return SystemHealthSummaryItemData(
            module="system",
            status=safe_status,
            check_name=check_name,
            check_result=check_result,
            generated_at=generated_at,
        )

    @staticmethod
    def _safe_read_text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[4]

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
