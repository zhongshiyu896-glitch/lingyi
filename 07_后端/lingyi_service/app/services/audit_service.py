"""Audit service for sensitive operation logging."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.error_codes import BOM_NOT_FOUND
from app.core.logging import REDACTED_MESSAGE
from app.core.logging import sanitize_log_message
from app.core.request_id import get_request_id_from_request
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BomInternalError
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.workshop import LyOperationWageRate
from app.models.workshop import YsWorkshopTicket


@dataclass(frozen=True)
class AuditContext:
    """Request scoped audit context."""

    request_id: str
    ip_address: str | None
    user_agent: str | None

    @staticmethod
    def from_request(request_obj: Request) -> "AuditContext":
        request_id = get_request_id_from_request(request_obj)
        client_host = request_obj.client.host if request_obj.client else None
        return AuditContext(
            request_id=request_id,
            ip_address=client_host,
            user_agent=request_obj.headers.get("User-Agent"),
        )


class AuditService:
    """Write and snapshot operation audit records."""

    def __init__(self, session: Session):
        self.session = session

    def snapshot_resource(self, resource_type: str, resource_id: int | None) -> dict[str, Any] | None:
        if resource_id is None:
            return None
        if resource_type == "workshop_ticket":
            return self._snapshot_workshop_ticket(resource_id=resource_id)
        if resource_type == "wage_rate":
            return self._snapshot_wage_rate(resource_id=resource_id)
        if resource_type != "bom":
            return None

        try:
            bom = self.session.query(LyApparelBom).filter(LyApparelBom.id == resource_id).first()
            if not bom:
                raise BusinessException(code=BOM_NOT_FOUND, message="BOM 不存在")

            items = (
                self.session.query(LyApparelBomItem)
                .filter(LyApparelBomItem.bom_id == bom.id)
                .order_by(LyApparelBomItem.id.asc())
                .all()
            )
            operations = (
                self.session.query(LyBomOperation)
                .filter(LyBomOperation.bom_id == bom.id)
                .order_by(LyBomOperation.sequence_no.asc(), LyBomOperation.id.asc())
                .all()
            )
        except BusinessException:
            raise
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        except Exception as exc:
            raise BomInternalError() from exc

        payload = {
            "bom": {
                "id": bom.id,
                "bom_no": bom.bom_no,
                "item_code": bom.item_code,
                "version_no": bom.version_no,
                "is_default": bom.is_default,
                "status": bom.status,
                "effective_date": bom.effective_date,
                "created_by": bom.created_by,
                "updated_by": bom.updated_by,
                "updated_at": bom.updated_at,
            },
            "items": [
                {
                    "id": row.id,
                    "material_item_code": row.material_item_code,
                    "color": row.color,
                    "size": row.size,
                    "qty_per_piece": row.qty_per_piece,
                    "loss_rate": row.loss_rate,
                    "uom": row.uom,
                    "remark": row.remark,
                }
                for row in items
            ],
            "operations": [
                {
                    "id": row.id,
                    "process_name": row.process_name,
                    "sequence_no": row.sequence_no,
                    "is_subcontract": row.is_subcontract,
                    "wage_rate": row.wage_rate,
                    "subcontract_cost_per_piece": row.subcontract_cost_per_piece,
                    "remark": row.remark,
                }
                for row in operations
            ],
        }
        try:
            return self._normalize(payload)
        except Exception as exc:
            raise BomInternalError() from exc

    def _snapshot_workshop_ticket(self, resource_id: int) -> dict[str, Any] | None:
        try:
            row = self.session.query(YsWorkshopTicket).filter(YsWorkshopTicket.id == resource_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            return None
        return self._normalize(
            {
                "id": row.id,
                "ticket_no": row.ticket_no,
                "ticket_key": row.ticket_key,
                "job_card": row.job_card,
                "item_code": row.item_code,
                "employee": row.employee,
                "process_name": row.process_name,
                "operation_type": row.operation_type,
                "qty": row.qty,
                "unit_wage": row.unit_wage,
                "wage_amount": row.wage_amount,
                "work_date": row.work_date,
                "sync_status": row.sync_status,
            }
        )

    def _snapshot_wage_rate(self, resource_id: int) -> dict[str, Any] | None:
        try:
            row = self.session.query(LyOperationWageRate).filter(LyOperationWageRate.id == resource_id).first()
        except SQLAlchemyError as exc:
            raise DatabaseReadFailed() from exc
        if not row:
            return None
        return self._normalize(
            {
                "id": row.id,
                "item_code": row.item_code,
                "company": row.company,
                "is_global": bool(row.is_global),
                "process_name": row.process_name,
                "wage_rate": row.wage_rate,
                "effective_from": row.effective_from,
                "effective_to": row.effective_to,
                "status": row.status,
            }
        )

    def record_success(
        self,
        *,
        module: str,
        action: str,
        operator: str,
        operator_roles: list[str],
        resource_type: str,
        resource_id: int | None,
        resource_no: str | None,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
        context: AuditContext,
    ) -> None:
        self._insert_log(
            module=module,
            action=action,
            operator=operator,
            operator_roles=operator_roles,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
            before_data=before_data,
            after_data=after_data,
            result="success",
            error_code=None,
            context=context,
        )

    def record_failure(
        self,
        *,
        module: str,
        action: str,
        operator: str,
        operator_roles: list[str],
        resource_type: str,
        resource_id: int | None,
        resource_no: str | None,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
        error_code: str,
        context: AuditContext,
    ) -> None:
        self._insert_log(
            module=module,
            action=action,
            operator=operator,
            operator_roles=operator_roles,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=resource_no,
            before_data=before_data,
            after_data=after_data,
            result="failed",
            error_code=error_code,
            context=context,
        )

    def record_security_audit(
        self,
        *,
        event_type: str,
        module: str,
        action: str | None,
        resource_type: str | None,
        resource_id: str | int | None,
        resource_no: str | None,
        user: CurrentUser | None,
        deny_reason: str,
        permission_source: str | None,
        request_obj: Request,
        dedupe_key: str | None = None,
    ) -> None:
        """Record security denial/permission-source-unavailable audit."""
        context = AuditContext.from_request(request_obj)
        safe_deny_reason = sanitize_log_message(deny_reason) or REDACTED_MESSAGE
        safe_dedupe_key = (dedupe_key or "")[:64] or None
        safe_resource_no = sanitize_log_message(resource_no) if resource_no else None
        if safe_resource_no == REDACTED_MESSAGE:
            safe_resource_no = None
        try:
            row = LySecurityAuditLog(
                event_type=event_type,
                module=module,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id is not None else None,
                resource_no=safe_resource_no,
                user_id=user.username if user else None,
                user_roles=user.roles if user else None,
                permission_source=permission_source,
                deny_reason=safe_deny_reason[:255],
                dedupe_key=safe_dedupe_key,
                request_method=(request_obj.method or "").upper()[:16] or "GET",
                request_path=(request_obj.url.path or "")[:255] or "/",
                request_id=context.request_id,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
            )
            self.session.add(row)
            self.session.flush()
        except Exception as exc:
            raise AuditWriteFailed() from exc

    def _insert_log(
        self,
        *,
        module: str,
        action: str,
        operator: str,
        operator_roles: list[str],
        resource_type: str,
        resource_id: int | None,
        resource_no: str | None,
        before_data: dict[str, Any] | None,
        after_data: dict[str, Any] | None,
        result: str,
        error_code: str | None,
        context: AuditContext,
    ) -> None:
        try:
            safe_resource_no = sanitize_log_message(resource_no) if resource_no else None
            if safe_resource_no == REDACTED_MESSAGE:
                safe_resource_no = None
            row = LyOperationAuditLog(
                module=module,
                action=action,
                operator=operator,
                operator_roles=operator_roles,
                resource_type=resource_type,
                resource_id=resource_id,
                resource_no=safe_resource_no,
                before_data=self._normalize(before_data),
                after_data=self._normalize(after_data),
                result=result,
                error_code=error_code,
                request_id=context.request_id,
                ip_address=context.ip_address,
                user_agent=context.user_agent,
            )
            self.session.add(row)
            self.session.flush()
        except Exception as exc:
            raise AuditWriteFailed() from exc

    @classmethod
    def _normalize(cls, payload: Any) -> Any:
        if payload is None:
            return None
        if isinstance(payload, Decimal):
            return str(payload)
        if isinstance(payload, (datetime, date)):
            return payload.isoformat()
        if isinstance(payload, dict):
            return {str(k): cls._normalize(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [cls._normalize(item) for item in payload]
        return payload
