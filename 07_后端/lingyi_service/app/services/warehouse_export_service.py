"""Warehouse read-only export and diagnostic helpers (TASK-050F)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
import csv
from io import StringIO
import re
from typing import Any

from app.schemas.warehouse import WarehouseDiagnosticData

SUPPORTED_DATASETS = (
    "stock_ledger",
    "stock_summary",
    "alerts",
    "batches",
    "serial_numbers",
    "traceability",
)

DATASET_HEADERS: dict[str, list[str]] = {
    "stock_ledger": [
        "company",
        "warehouse",
        "item_code",
        "posting_date",
        "voucher_type",
        "voucher_no",
        "actual_qty",
        "qty_after_transaction",
        "valuation_rate",
    ],
    "stock_summary": [
        "company",
        "warehouse",
        "item_code",
        "actual_qty",
        "projected_qty",
        "reserved_qty",
        "ordered_qty",
        "reorder_level",
        "safety_stock",
        "threshold_missing",
        "is_below_reorder",
        "is_below_safety",
    ],
    "alerts": [
        "company",
        "warehouse",
        "item_code",
        "alert_type",
        "current_qty",
        "threshold_qty",
        "gap_qty",
        "last_movement_date",
        "severity",
    ],
    "batches": [
        "company",
        "batch_no",
        "item_code",
        "warehouse",
        "manufacturing_date",
        "expiry_date",
        "disabled",
        "qty",
    ],
    "serial_numbers": [
        "company",
        "serial_no",
        "item_code",
        "warehouse",
        "batch_no",
        "status",
        "delivery_document_no",
        "purchase_document_no",
    ],
    "traceability": [
        "company",
        "warehouse",
        "item_code",
        "posting_date",
        "voucher_type",
        "voucher_no",
        "actual_qty",
        "qty_after_transaction",
        "batch_no",
        "serial_no",
    ],
}


@dataclass(frozen=True)
class WarehouseCsvArtifact:
    """Binary artifact for CSV download."""

    content: bytes
    content_type: str
    filename: str


class WarehouseExportService:
    """Build CSV artifacts and read-only diagnostic snapshots."""

    @staticmethod
    def build_csv(*, dataset: str, rows: list[dict[str, Any]]) -> WarehouseCsvArtifact:
        if dataset not in DATASET_HEADERS:
            raise ValueError("Unsupported dataset")
        headers = DATASET_HEADERS[dataset]
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([WarehouseExportService._sanitize_csv_cell(row.get(key)) for key in headers])
        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        safe_dataset = re.sub(r"[^A-Za-z0-9_.-]", "_", dataset)
        return WarehouseCsvArtifact(
            content=output.getvalue().encode("utf-8"),
            content_type="text/csv; charset=utf-8",
            filename=f"warehouse_export_{safe_dataset}_{now}.csv",
        )

    @staticmethod
    def build_diagnostic_snapshot(*, adapter_configured: bool) -> WarehouseDiagnosticData:
        return WarehouseDiagnosticData(
            adapter_configured=adapter_configured,
            supported_datasets=list(SUPPORTED_DATASETS),
            export_supported_formats=["csv"],
            write_boundary="no_erpnext_write,no_submit,no_stock_reconciliation",
            last_checked_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _sanitize_csv_cell(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            text = value.isoformat()
        else:
            text = str(value)
        if text and text[0] in {"=", "+", "-", "@", "\t", "\r"}:
            return "'" + text
        return text
