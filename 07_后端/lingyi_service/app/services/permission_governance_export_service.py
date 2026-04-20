"""CSV export helpers for permission governance audit export baseline (TASK-070C)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
import csv
from io import StringIO
from typing import Any

from app.schemas.permission_governance import PermissionOperationAuditItemData
from app.schemas.permission_governance import PermissionSecurityAuditItemData


@dataclass(frozen=True)
class PermissionGovernanceCsvArtifact:
    """Binary artifact for permission governance CSV download."""

    content: bytes
    content_type: str
    filename: str


class PermissionGovernanceExportService:
    """Build safe CSV exports for security/operation permission audit logs."""

    SECURITY_HEADERS: tuple[str, ...] = (
        "id",
        "event_type",
        "module",
        "action",
        "resource_type",
        "resource_id",
        "resource_no",
        "user_id",
        "permission_source",
        "deny_reason",
        "request_method",
        "request_path",
        "request_id",
        "created_at",
    )

    OPERATION_HEADERS: tuple[str, ...] = (
        "id",
        "module",
        "action",
        "operator",
        "resource_type",
        "resource_id",
        "resource_no",
        "result",
        "error_code",
        "request_id",
        "has_before_data",
        "has_after_data",
        "before_keys",
        "after_keys",
        "created_at",
    )

    @classmethod
    def build_security_audit_csv(
        cls, *, items: list[PermissionSecurityAuditItemData]
    ) -> PermissionGovernanceCsvArtifact:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(cls.SECURITY_HEADERS)

        for item in items:
            row = {
                "id": item.id,
                "event_type": item.event_type,
                "module": item.module,
                "action": item.action,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "resource_no": item.resource_no,
                "user_id": item.user_id,
                "permission_source": item.permission_source,
                "deny_reason": item.deny_reason,
                "request_method": item.request_method,
                "request_path": item.request_path,
                "request_id": item.request_id,
                "created_at": item.created_at,
            }
            writer.writerow([cls._sanitize_csv_cell(row[key]) for key in cls.SECURITY_HEADERS])

        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return PermissionGovernanceCsvArtifact(
            content=output.getvalue().encode("utf-8"),
            content_type="text/csv; charset=utf-8",
            filename=f"permission_security_audit_export_{now}.csv",
        )

    @classmethod
    def build_operation_audit_csv(
        cls, *, items: list[PermissionOperationAuditItemData]
    ) -> PermissionGovernanceCsvArtifact:
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(cls.OPERATION_HEADERS)

        for item in items:
            row = {
                "id": item.id,
                "module": item.module,
                "action": item.action,
                "operator": item.operator,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "resource_no": item.resource_no,
                "result": item.result,
                "error_code": item.error_code,
                "request_id": item.request_id,
                "has_before_data": item.has_before_data,
                "has_after_data": item.has_after_data,
                "before_keys": "|".join(item.before_keys),
                "after_keys": "|".join(item.after_keys),
                "created_at": item.created_at,
            }
            writer.writerow([cls._sanitize_csv_cell(row[key]) for key in cls.OPERATION_HEADERS])

        now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return PermissionGovernanceCsvArtifact(
            content=output.getvalue().encode("utf-8"),
            content_type="text/csv; charset=utf-8",
            filename=f"permission_operation_audit_export_{now}.csv",
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
