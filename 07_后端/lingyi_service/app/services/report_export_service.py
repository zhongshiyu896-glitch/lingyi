"""CSV export helpers for report catalog readonly baseline (TASK-060C)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
import csv
from io import StringIO
from typing import Any

from app.schemas.report import ReportCatalogItemData


@dataclass(frozen=True)
class ReportCatalogCsvArtifact:
    """Binary artifact for report catalog CSV download."""

    content: bytes
    content_type: str
    filename: str


class ReportExportService:
    """Build safe CSV files for readonly report catalog export."""

    HEADERS: tuple[str, ...] = (
        "report_key",
        "name",
        "source_modules",
        "report_type",
        "required_filters",
        "optional_filters",
        "metric_summary",
        "permission_action",
        "status",
    )

    @classmethod
    def build_catalog_csv(cls, *, items: list[ReportCatalogItemData]) -> ReportCatalogCsvArtifact:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(cls.HEADERS)

        for item in items:
            row = {
                "report_key": item.report_key,
                "name": item.name,
                "source_modules": "|".join(item.source_modules),
                "report_type": item.report_type,
                "required_filters": "|".join(item.required_filters),
                "optional_filters": "|".join(item.optional_filters),
                "metric_summary": "|".join(item.metric_summary),
                "permission_action": item.permission_action,
                "status": item.status,
            }
            writer.writerow([cls._sanitize_csv_cell(row[key]) for key in cls.HEADERS])

        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return ReportCatalogCsvArtifact(
            content=output.getvalue().encode("utf-8"),
            content_type="text/csv; charset=utf-8",
            filename=f"report_catalog_export_{now}.csv",
        )

    @staticmethod
    def _sanitize_csv_cell(value: Any) -> str:
        if value is None:
            return ""
        text = str(value)
        stripped = text.lstrip()
        if text[:1] in {"\t", "\r", "\n"}:
            return "'" + text
        if stripped[:1] in {"=", "+", "-", "@"}:
            return "'" + text
        return text
