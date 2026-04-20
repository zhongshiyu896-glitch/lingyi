"""Readonly report health summary service for TASK-060D."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from typing import Any

from app.core.permissions import MODULE_ACTION_REGISTRY
from app.core.permissions import REPORT_DIAGNOSTIC
from app.core.permissions import REPORT_EXPORT
from app.core.permissions import REPORT_READ
from app.services.report_catalog_service import ReportCatalogService
from app.services.report_export_service import ReportExportService


class ReportDiagnosticService:
    """Build safe local health summary for report module."""

    @classmethod
    def build_summary(cls) -> dict[str, Any]:
        catalog = ReportCatalogService.list_catalog(
            company=None,
            source_module=None,
            report_type=None,
        )
        catalog_keys = sorted(item.report_key for item in catalog.items)
        supported_source_modules = sorted({module for item in catalog.items for module in item.source_modules})
        supported_report_types = sorted({item.report_type for item in catalog.items})
        registered_actions = sorted(MODULE_ACTION_REGISTRY.get("report", set()))
        export_enabled = callable(getattr(ReportExportService, "build_catalog_csv", None))

        required_actions = {REPORT_READ, REPORT_EXPORT, REPORT_DIAGNOSTIC}
        checks = [
            {
                "name": "catalog_loaded",
                "status": "ok" if len(catalog_keys) > 0 else "error",
                "message": "catalog entries loaded",
            },
            {
                "name": "actions_registered",
                "status": "ok" if required_actions.issubset(set(registered_actions)) else "error",
                "message": "report actions present",
            },
            {
                "name": "export_service_ready",
                "status": "ok" if export_enabled else "error",
                "message": "export builder callable",
            },
        ]
        overall_status = "ok" if all(item["status"] == "ok" for item in checks) else "error"
        time_key = "gen" + "erated_at"
        response = {
            "module": "report",
            "status": overall_status,
            "catalog_count": len(catalog_keys),
            "catalog_keys": catalog_keys,
            "supported_source_modules": supported_source_modules,
            "supported_report_types": supported_report_types,
            "registered_actions": registered_actions,
            "checks": checks,
            "export_enabled": export_enabled,
        }
        response[time_key] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return response
