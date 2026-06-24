"""FastAPI router for quality management APIs (TASK-012B)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
import logging
import os
import re
from typing import Any

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.auth import is_internal_worker_api_enabled
from app.core.config import DEFAULT_LOCAL_DEV_DATABASE_URL
from app.core.config import is_allowed_local_dev_database
from app.core.config import quality_enable_outbox_worker_sync
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import ERPNEXT_RESOURCE_NOT_FOUND
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import QUALITY_DATABASE_WRITE_FAILED
from app.core.error_codes import QUALITY_INTERNAL_ERROR
from app.core.error_codes import QUALITY_INVALID_SOURCE
from app.core.error_codes import QUALITY_INVALID_STATUS
from app.core.error_codes import QUALITY_NOT_FOUND
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.logging import log_safe_error
from app.core.permissions import QUALITY_CANCEL
from app.core.permissions import QUALITY_CONFIRM
from app.core.permissions import QUALITY_CREATE
from app.core.permissions import QUALITY_DIAGNOSTIC
from app.core.permissions import QUALITY_EXPORT
from app.core.permissions import QUALITY_READ
from app.core.permissions import QUALITY_RELEASE
from app.core.permissions import QUALITY_REWORK
from app.core.permissions import QUALITY_UPDATE
from app.core.permissions import QUALITY_WORKER
from app.core.request_id import get_request_id_from_request
from app.core.request_id import is_request_id_valid
from app.models.quality import LyQualityInspection
from app.schemas.quality import QualityInspectionCancelRequest
from app.schemas.quality import QualityInspectionConfirmRequest
from app.schemas.quality import QualityInspectionCreateRequest
from app.schemas.quality import QualityInspectionDefectCreateRequest
from app.schemas.quality import QualityInspectionUpdateRequest
from app.schemas.quality import QualityStatisticsTrendData
from app.schemas.quality_outbox import QualityOutboxStatusData
from app.schemas.quality_outbox import QualityOutboxWorkerRunOnceData
from app.schemas.quality_outbox import QualityOutboxWorkerRunOnceRequest
from app.services.quality_export_service import QualityExportService
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_quality_outbox_adapter import ERPNextQualityOutboxAdapter
from app.services.quality_outbox_worker import QualityOutboxWorker
from app.services.quality_service import QualityService
from app.services.quality_service import QualitySourceValidator
from app.services.quality_service import _text as _scope_text
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/quality", tags=["quality"])
logger = logging.getLogger(__name__)
QUALITY_WRITE_FROZEN_CODE = "QUALITY_WRITE_FROZEN"
QUALITY_WRITE_FROZEN_MESSAGE = "质量写操作已冻结（Phase 1 只读基线）"
QUALITY_GATE_ERROR_PREFIX = "LOCAL_GATE_FAIL_CLOSED:"
QUALITY_SCENARIO_TAG_PATTERN = re.compile(r"Z003-QUALITY-INSPECTION-\d{8}-\d{3}")
QUALITY_REQUEST_ID_CARRIER_PATTERN = re.compile(
    r"^(Z003-QUALITY-INSPECTION-\d{8}-\d{3})-QI-([A-Z])-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})$"
)
QUALITY_LOCAL_DB_URL = DEFAULT_LOCAL_DEV_DATABASE_URL
QUALITY_OPERATION_CODE_BY_NAME = {
    "create": "C",
    "update": "U",
    "confirm": "F",
    "release": "R",
    "rework": "W",
    "cancel": "X",
    "defects": "D",
}


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _created(data: Any) -> JSONResponse:
    return JSONResponse(status_code=201, content=_ok(data))


def _err(code: str, message: str | None = None, status_code: int | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or status_of(code, 400),
        content={"code": code, "message": message or message_of(code), "data": None},
    )


def _app_err(exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "data": getattr(exc, "data", None)},
    )


def _rollback_safely(session: Session) -> None:
    try:
        session.rollback()
    except Exception:  # pragma: no cover
        return


def _commit_or_raise_write_error(session: Session) -> None:
    try:
        session.commit()
    except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
        _rollback_safely(session)
        raise BusinessException(code=QUALITY_DATABASE_WRITE_FAILED) from exc


def _permission_error_code(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        if code == AUTH_FORBIDDEN:
            return AUTH_FORBIDDEN
        if code == PERMISSION_SOURCE_UNAVAILABLE:
            return PERMISSION_SOURCE_UNAVAILABLE
        return code
    return "HTTP_ERROR"


def _map_permission_error(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        return _err(str(detail.get("code") or "HTTP_ERROR"), str(detail.get("message") or "请求失败"), exc.status_code)
    return _err("HTTP_ERROR", str(detail), exc.status_code)


def _record_failure_safely(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    error_code: str,
) -> None:
    try:
        audit.record_failure(
            module="quality",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="QUALITY_INSPECTION",
            resource_id=resource_id,
            resource_no=resource_no,
            before_data=None,
            after_data=None,
            error_code=error_code,
            context=context,
        )
        session.commit()
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        raise AuditWriteFailed() from exc


def _record_success(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    after_data: dict[str, Any] | None,
) -> None:
    audit.record_success(
        module="quality",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type="QUALITY_INSPECTION",
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=None,
        after_data=after_data,
        context=context,
    )
    _commit_or_raise_write_error(session)


def _ensure_quality_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    row_or_scope: LyQualityInspection | dict[str, Any],
    resource_id: int | None = None,
    resource_no: str | None = None,
    enforce_action: bool = False,
) -> None:
    if isinstance(row_or_scope, LyQualityInspection):
        scope = {
            "company": row_or_scope.company,
            "item_code": row_or_scope.item_code,
            "supplier": row_or_scope.supplier,
            "warehouse": row_or_scope.warehouse,
            "work_order": row_or_scope.work_order,
            "sales_order": row_or_scope.sales_order,
            "source_type": row_or_scope.source_type,
            "source_id": row_or_scope.source_id,
        }
    else:
        scope = row_or_scope
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="quality",
        action=action,
        resource_scope=scope,
        required_fields=("company", "item_code"),
        resource_type="quality_inspection",
        resource_id=resource_id,
        resource_no=resource_no,
        enforce_action=enforce_action,
    )


def _quality_service(session: Session, request: Request) -> QualityService:
    return QualityService(session=session, source_validator=QualitySourceValidator(request_obj=request))


def _quality_outbox_worker(session: Session) -> QualityOutboxWorker:
    return QualityOutboxWorker(
        session=session,
        adapter=ERPNextQualityOutboxAdapter(),
    )


def _handle_write_exception(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    exc: Exception,
    request: Request,
) -> JSONResponse:
    _rollback_safely(session)
    if isinstance(exc, HTTPException):
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=resource_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _map_permission_error(exc)
    if isinstance(exc, AppException):
        if _is_local_gate_failure(exc):
            return _app_err(exc)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=resource_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    log_safe_error(
        logger_obj=logger,
        message="quality_internal_error",
        exc=exc,
        request_id=get_request_id_from_request(request),
        extra={"module": "quality", "action": action, "error_code": QUALITY_INTERNAL_ERROR},
    )
    error = BusinessException(code=QUALITY_INTERNAL_ERROR)
    try:
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=resource_id,
            resource_no=resource_no,
            error_code=error.code,
        )
    except AuditWriteFailed as audit_exc:
        return _app_err(audit_exc)
    return _app_err(error)


def _is_local_gate_failure(exc: AppException) -> bool:
    return exc.code == QUALITY_INVALID_SOURCE and str(exc.message).startswith(QUALITY_GATE_ERROR_PREFIX)


def _raise_quality_gate_error(reason: str) -> None:
    raise BusinessException(code=QUALITY_INVALID_SOURCE, message=f"{QUALITY_GATE_ERROR_PREFIX}{reason}")


def _ensure_local_dev_write_gate() -> None:
    permission_source = os.getenv("LINGYI_PERMISSION_SOURCE", "").strip().lower()
    if permission_source == "fastapi":
        return
    if not is_allowed_local_dev_database():
        _raise_quality_gate_error("non_local_dev")


def _match_quality_scenario_tag(value: str) -> str | None:
    matched = QUALITY_SCENARIO_TAG_PATTERN.search((value or "").strip())
    return matched.group(0) if matched else None


def _fnv_carrier_code(value: str) -> str:
    normalized = value.strip()
    hash_value = 2166136261
    for byte in normalized.encode("utf-8"):
        hash_value ^= byte
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return f"{hash_value:08X}"[-3:]


def _extract_quality_request_carriers(request_id: str) -> tuple[str, str, str, str, str, str, str] | None:
    matched = QUALITY_REQUEST_ID_CARRIER_PATTERN.fullmatch(request_id.strip())
    if matched is None:
        return None
    return (
        matched.group(1),
        matched.group(2),
        matched.group(3),
        matched.group(4),
        matched.group(5),
        matched.group(6),
        matched.group(7),
    )


def _require_non_blank_carrier(value: str | None, reason: str) -> str:
    normalized = _scope_text(value)
    if normalized is None:
        _raise_quality_gate_error(reason)
    return normalized


def _validate_quality_request_id_gate(
    *,
    request_obj: Request,
    request_id: str,
    scenario_tag: str,
    operation: str,
    idempotency_key: str,
    source_ref: str,
    inspection_ref: str,
    item_code: str,
    result: str,
) -> None:
    request_id_header = (request_obj.headers.get("X-Request-ID") or "").strip()
    if not request_id_header:
        _raise_quality_gate_error("missing_request_id")
    if not is_request_id_valid(request_id_header):
        _raise_quality_gate_error("invalid_request_id_pattern")
    if not request_id:
        _raise_quality_gate_error("missing_request_id")
    if not is_request_id_valid(request_id):
        _raise_quality_gate_error("invalid_request_id_pattern")
    if request_id_header != request_id:
        _raise_quality_gate_error("mismatched_request_id")

    expected_operation_code = QUALITY_OPERATION_CODE_BY_NAME.get(operation)
    if expected_operation_code is None:
        _raise_quality_gate_error("mismatched_operation")

    header_carrier = _extract_quality_request_carriers(request_id_header)
    request_carrier = _extract_quality_request_carriers(request_id)
    if header_carrier is None or request_carrier is None:
        _raise_quality_gate_error("mismatched_request_id")
    if header_carrier != request_carrier:
        _raise_quality_gate_error("mismatched_request_id")
    (
        request_tag,
        request_operation_code,
        request_idempotency_code,
        request_source_ref_code,
        request_inspection_ref_code,
        request_item_code,
        request_result_code,
    ) = request_carrier

    if request_tag != scenario_tag:
        _raise_quality_gate_error("mismatched_request_id")
    if request_operation_code != expected_operation_code:
        _raise_quality_gate_error("mismatched_operation")
    if request_idempotency_code != _fnv_carrier_code(idempotency_key):
        _raise_quality_gate_error("missing_idempotency_key")
    if request_source_ref_code != _fnv_carrier_code(source_ref):
        _raise_quality_gate_error("mismatched_source_ref")
    if request_inspection_ref_code != _fnv_carrier_code(inspection_ref):
        _raise_quality_gate_error("mismatched_inspection_ref")
    if request_item_code != _fnv_carrier_code(item_code):
        _raise_quality_gate_error("mismatched_item_code")
    if request_result_code != _fnv_carrier_code(result):
        _raise_quality_gate_error("mismatched_result")


def _validate_quality_gate_common(
    *,
    request_obj: Request,
    request_id: str,
    operation: str,
    payload_operation: str | None,
    scenario_tag: str | None,
    idempotency_key: str | None,
    source_ref: str | None,
    inspection_ref: str | None,
    source_type: str | None,
    source_doc: str | None,
    item_code: str | None,
    result: str | None,
) -> tuple[str, str, str, str, str]:
    _ensure_local_dev_write_gate()

    normalized_scenario_tag = _require_non_blank_carrier(scenario_tag, "missing_scenario_tag")
    if QUALITY_SCENARIO_TAG_PATTERN.fullmatch(normalized_scenario_tag) is None:
        _raise_quality_gate_error("invalid_scenario_tag")

    normalized_idempotency_key = _require_non_blank_carrier(idempotency_key, "missing_idempotency_key")
    normalized_source_ref = _require_non_blank_carrier(source_ref, "mismatched_source_ref")
    normalized_inspection_ref = _require_non_blank_carrier(inspection_ref, "mismatched_inspection_ref")
    normalized_source_type = _require_non_blank_carrier(source_type, "mismatched_source_type")
    normalized_item_code = _require_non_blank_carrier(item_code, "mismatched_item_code")
    normalized_result = _require_non_blank_carrier(result, "mismatched_result")
    normalized_payload_operation = _require_non_blank_carrier(payload_operation, "mismatched_operation")
    normalized_operation = _require_non_blank_carrier(operation, "mismatched_operation")
    normalized_source_doc = _require_non_blank_carrier(source_doc, "missing_source_doc")

    if normalized_operation != operation:
        _raise_quality_gate_error("mismatched_operation")
    if normalized_payload_operation != operation:
        _raise_quality_gate_error("mismatched_payload_operation")
    if normalized_source_doc != normalized_source_ref:
        _raise_quality_gate_error("mismatched_source_doc")

    carrier_tags = [normalized_scenario_tag]
    source_ref_tag = _match_quality_scenario_tag(normalized_source_ref)
    if source_ref_tag is None:
        _raise_quality_gate_error("mismatched_source_ref")
    carrier_tags.append(source_ref_tag)
    source_doc_tag = _match_quality_scenario_tag(normalized_source_doc)
    if source_doc_tag is None:
        _raise_quality_gate_error("mismatched_source_doc")
    carrier_tags.append(source_doc_tag)
    if len(set(carrier_tags)) != 1:
        _raise_quality_gate_error("mismatched_source_ref")

    _validate_quality_request_id_gate(
        request_obj=request_obj,
        request_id=request_id,
        scenario_tag=normalized_scenario_tag,
        operation=operation,
        idempotency_key=normalized_idempotency_key,
        source_ref=normalized_source_ref,
        inspection_ref=normalized_inspection_ref,
        item_code=normalized_item_code,
        result=normalized_result,
    )

    return (
        normalized_source_ref,
        normalized_inspection_ref,
        normalized_source_type,
        normalized_item_code,
        normalized_result,
    )


def _validate_quality_create_gate(
    *,
    request_obj: Request,
    request_id: str,
    payload: QualityInspectionCreateRequest,
) -> None:
    _validate_quality_gate_common(
        request_obj=request_obj,
        request_id=request_id,
        operation="create",
        payload_operation=payload.operation,
        scenario_tag=payload.scenario_tag,
        idempotency_key=payload.idempotency_key,
        source_ref=payload.source_ref,
        inspection_ref=payload.inspection_ref,
        source_type=payload.source_type,
        source_doc=payload.source_doc,
        item_code=payload.item_code,
        result=payload.result,
    )


def _validate_quality_existing_gate(
    *,
    request_obj: Request,
    request_id: str,
    payload: Any,
    operation: str,
    inspection_row: LyQualityInspection,
) -> None:
    normalized_source_ref, normalized_inspection_ref, normalized_source_type, normalized_item_code, normalized_result = _validate_quality_gate_common(
        request_obj=request_obj,
        request_id=request_id,
        operation=operation,
        payload_operation=getattr(payload, "operation", None),
        scenario_tag=getattr(payload, "scenario_tag", None),
        idempotency_key=getattr(payload, "idempotency_key", None),
        source_ref=getattr(payload, "source_ref", None),
        inspection_ref=getattr(payload, "inspection_ref", None),
        source_type=getattr(payload, "source_type", None),
        source_doc=getattr(payload, "source_doc", None),
        item_code=getattr(payload, "item_code", None),
        result=getattr(payload, "result", None),
    )

    expected_ref_values = {str(inspection_row.id), str(inspection_row.inspection_no)}
    if normalized_inspection_ref not in expected_ref_values:
        _raise_quality_gate_error("mismatched_inspection_ref")
    row_source_type = _scope_text(inspection_row.source_type)
    if row_source_type is not None and normalized_source_type != row_source_type:
        _raise_quality_gate_error("mismatched_source_type")
    row_source_id = _scope_text(inspection_row.source_id)
    if row_source_id is not None and normalized_source_ref != row_source_id:
        _raise_quality_gate_error("mismatched_source_ref")
    row_item_code = _scope_text(inspection_row.item_code)
    if row_item_code is not None and normalized_item_code != row_item_code:
        _raise_quality_gate_error("mismatched_item_code")
    if operation in {"confirm", "release", "rework", "cancel", "defects"}:
        row_result = _scope_text(inspection_row.result)
        if row_result is not None and normalized_result != row_result:
            _raise_quality_gate_error("mismatched_result")


def _hide_not_found() -> None:
    raise HTTPException(
        status_code=404,
        detail={"code": ERPNEXT_RESOURCE_NOT_FOUND, "message": message_of(ERPNEXT_RESOURCE_NOT_FOUND), "data": None},
    )


def _write_frozen_response() -> JSONResponse:
    return _err(
        QUALITY_WRITE_FROZEN_CODE,
        QUALITY_WRITE_FROZEN_MESSAGE,
        status_code=409,
    )


@router.post("/inspections")
def create_quality_inspection(
    request: Request,
    payload: QualityInspectionCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_inspection",
        )
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope=payload.model_dump(),
            enforce_action=False,
        )
        _validate_quality_create_gate(
            request_obj=request,
            request_id=payload.request_id,
            payload=payload,
        )
        data = _quality_service(session, request).create_inspection(
            payload=payload,
            operator=current_user.username,
            request_id=payload.request_id,
        )
        _record_success(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=data.id,
            resource_no=data.inspection_no,
            after_data={"inspection_id": data.id, "inspection_no": data.inspection_no, "status": data.status},
        )
        return _created(data.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            exc=exc,
            request=request,
        )


@router.get("/inspections")
def list_quality_inspections(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_inspection",
    )
    _ensure_quality_scope(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        row_or_scope={
            "company": company,
            "item_code": item_code,
            "supplier": supplier,
            "warehouse": warehouse,
            "source_type": source_type,
            "source_id": source_id,
        },
        enforce_action=False,
    ) if company and item_code else None
    data = QualityService(session=session).list_inspections(
        company=company,
        item_code=item_code,
        supplier=supplier,
        warehouse=warehouse,
        source_type=source_type,
        source_id=source_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    filtered = []
    for row in data.items:
        db_row = session.query(LyQualityInspection).filter(LyQualityInspection.id == row.id).one()
        try:
            _ensure_quality_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                row_or_scope=db_row,
                resource_id=row.id,
                resource_no=row.inspection_no,
                enforce_action=False,
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            if detail.get("code") == "RESOURCE_ACCESS_DENIED":
                continue
            raise
        filtered.append(row)
    data.items = filtered
    data.total = len(filtered)
    return _ok(data.model_dump(mode="json"))


@router.get("/inspections/{inspection_id}")
def get_quality_inspection(
    inspection_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_inspection",
        resource_id=inspection_id,
    )
    row = session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one_or_none()
    if row is None:
        return _err(QUALITY_NOT_FOUND, status_code=status_of(QUALITY_NOT_FOUND))
    try:
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope=row,
            resource_id=inspection_id,
            resource_no=str(row.inspection_no),
            enforce_action=False,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == "RESOURCE_ACCESS_DENIED":
            _hide_not_found()
        raise
    data = QualityService(session=session).get_detail_data(inspection_id)
    return _ok(data.model_dump(mode="json"))


@router.patch("/inspections/{inspection_id}")
def update_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionUpdateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_UPDATE,
        operation="update",
    )


@router.post("/inspections/{inspection_id}/confirm")
def confirm_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionConfirmRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_CONFIRM,
        operation="confirm",
    )


@router.post("/inspections/{inspection_id}/release")
def release_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionConfirmRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_RELEASE,
        operation="release",
    )


@router.post("/inspections/{inspection_id}/rework")
def rework_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionConfirmRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_REWORK,
        operation="rework",
    )


@router.post("/inspections/{inspection_id}/cancel")
def cancel_quality_inspection(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_CANCEL,
        operation="cancel",
    )


@router.post("/inspections/{inspection_id}/defects")
def add_quality_inspection_defects(
    inspection_id: int,
    request: Request,
    payload: QualityInspectionDefectCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _write_existing(
        inspection_id=inspection_id,
        request=request,
        payload=payload,
        current_user=current_user,
        session=session,
        action=QUALITY_UPDATE,
        operation="defects",
    )


def _write_existing(
    *,
    inspection_id: int,
    request: Request,
    payload: Any,
    current_user: CurrentUser,
    session: Session,
    action: str,
    operation: str,
):
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_inspection",
            resource_id=inspection_id,
        )
        row = session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one_or_none()
        if row is None:
            raise BusinessException(code=QUALITY_NOT_FOUND)
        resource_no = str(row.inspection_no)
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope=row,
            resource_id=inspection_id,
            resource_no=resource_no,
            enforce_action=False,
        )
        _validate_quality_existing_gate(
            request_obj=request,
            request_id=payload.request_id,
            payload=payload,
            operation=operation,
            inspection_row=row,
        )
        service = _quality_service(session, request)
        if operation == "update":
            replay_data = service.replay_write_idempotency(
                company=str(row.company),
                operation="update",
                idempotency_key=payload.idempotency_key,
                request_hash=service.build_write_request_hash(
                    operation="update",
                    inspection_id=inspection_id,
                    payload=payload.model_dump(mode="json"),
                ),
            )
            if replay_data is not None:
                after_data = {
                    "inspection_id": replay_data.get("id"),
                    "inspection_no": replay_data.get("inspection_no"),
                    "status": replay_data.get("status"),
                }
                _record_success(
                    session=session,
                    audit=audit,
                    context=context,
                    action=action,
                    current_user=current_user,
                    resource_id=inspection_id,
                    resource_no=resource_no,
                    after_data=after_data,
                )
                return _ok(replay_data)
            if row.status == "confirmed":
                return _err(QUALITY_INVALID_STATUS, "已确认状态不可修改", status_code=403)
            if row.status == "cancelled":
                return _err(QUALITY_INVALID_STATUS, "已取消状态不可修改", status_code=409)
            if row.status != "draft":
                return _err(QUALITY_INVALID_STATUS, "当前状态不允许修改", status_code=409)
            data = service.update_inspection(
                inspection_id=inspection_id,
                payload=payload,
                operator=current_user.username,
                request_id=payload.request_id,
            )
            after_data = {"inspection_id": data.id, "inspection_no": data.inspection_no, "status": data.status}
            _record_success(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=inspection_id,
                resource_no=resource_no,
                after_data=after_data,
            )
            return _ok(data.model_dump(mode="json"))
        if operation == "defects":
            replay_data = service.replay_write_idempotency(
                company=str(row.company),
                operation="defects",
                idempotency_key=payload.idempotency_key,
                request_hash=service.build_write_request_hash(
                    operation="defects",
                    inspection_id=inspection_id,
                    payload=payload.model_dump(mode="json"),
                ),
            )
            if replay_data is not None:
                after_data = {
                    "inspection_id": replay_data.get("id"),
                    "inspection_no": replay_data.get("inspection_no"),
                    "status": replay_data.get("status"),
                }
                _record_success(
                    session=session,
                    audit=audit,
                    context=context,
                    action=action,
                    current_user=current_user,
                    resource_id=inspection_id,
                    resource_no=resource_no,
                    after_data=after_data,
                )
                return _created(replay_data)
            if row.status == "confirmed":
                return _err(QUALITY_INVALID_STATUS, "已确认状态不可录入缺陷", status_code=403)
            if row.status == "cancelled":
                return _err(QUALITY_INVALID_STATUS, "已取消状态不可录入缺陷", status_code=409)
            if row.status != "draft":
                return _err(QUALITY_INVALID_STATUS, "当前状态不允许录入缺陷", status_code=409)
            data = service.add_defects(
                inspection_id=inspection_id,
                payload=payload,
                operator=current_user.username,
                request_id=payload.request_id,
            )
            after_data = {"inspection_id": data.id, "inspection_no": data.inspection_no, "status": data.status}
            _record_success(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=inspection_id,
                resource_no=resource_no,
                after_data=after_data,
            )
            return _created(data.model_dump(mode="json"))
        if operation == "confirm":
            service.confirm_inspection(
                inspection_id=inspection_id,
                operator=current_user.username,
                request_id=payload.request_id,
                idempotency_key=payload.idempotency_key,
                request_payload=payload.model_dump(mode="json"),
                remark=getattr(payload, "remark", None),
            )
            data = service.get_detail_data(inspection_id)
            after_data = {"inspection_id": data.id, "inspection_no": data.inspection_no, "status": data.status}
            _record_success(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=inspection_id,
                resource_no=resource_no,
                after_data=after_data,
            )
            return _ok(data.model_dump(mode="json"))
        if operation in {"release", "rework"}:
            data = service.dispose_inspection(
                inspection_id=inspection_id,
                action=operation,
                operator=current_user.username,
                request_id=payload.request_id,
                idempotency_key=payload.idempotency_key,
                remark=getattr(payload, "remark", None),
            )
            after_data = {
                "inspection_id": data.id,
                "inspection_no": data.inspection_no,
                "status": data.status,
                "disposition": data.action,
                "qty": str(data.qty),
            }
            if data.downstream_type:
                after_data.update(
                    {
                        "downstream_type": data.downstream_type,
                        "warehouse_draft_id": data.warehouse_draft_id,
                        "warehouse_source_id": data.warehouse_source_id,
                    }
                )
            _record_success(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=inspection_id,
                resource_no=resource_no,
                after_data=after_data,
            )
            return _ok(data.model_dump(mode="json"))
        if operation == "cancel":
            service.cancel_inspection(
                inspection_id=inspection_id,
                operator=current_user.username,
                request_id=payload.request_id,
                idempotency_key=payload.idempotency_key,
                request_payload=payload.model_dump(mode="json"),
                reason=getattr(payload, "reason", None),
            )
            data = service.get_detail_data(inspection_id)
            after_data = {"inspection_id": data.id, "inspection_no": data.inspection_no, "status": data.status}
            _record_success(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=inspection_id,
                resource_no=resource_no,
                after_data=after_data,
            )
            return _ok(data.model_dump(mode="json"))
        return _write_frozen_response()
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=inspection_id,
            resource_no=resource_no,
            exc=exc,
            request=request,
        )


@router.post("/internal/outbox-sync/run-once")
def run_quality_outbox_sync_once(
    request: Request,
    payload: QualityOutboxWorkerRunOnceRequest = Body(default=QualityOutboxWorkerRunOnceRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_WORKER
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    if not is_internal_worker_api_enabled():
        permission_service.record_security_denial(
            request_obj=request,
            current_user=current_user,
            action=action,
            resource_type="QualityOutboxWorker",
            resource_no=None,
            deny_reason="质量 outbox 内部接口未启用",
            event_type=INTERNAL_API_DISABLED,
            module="quality",
        )
        return _err(
            INTERNAL_API_DISABLED,
            "内部接口未启用",
            status_code=status_of(INTERNAL_API_DISABLED),
        )
    if not payload.dry_run and not quality_enable_outbox_worker_sync():
        permission_service.record_security_denial(
            request_obj=request,
            current_user=current_user,
            action=action,
            resource_type="QualityOutboxWorker",
            resource_no=None,
            deny_reason="质量 Outbox ERP 同步未启用",
            event_type=INTERNAL_API_DISABLED,
            module="quality",
        )
        return _err(
            INTERNAL_API_DISABLED,
            "质量 Outbox ERP 同步未启用",
            status_code=status_of(INTERNAL_API_DISABLED),
        )

    try:
        permission_service.require_action_from_roles_only(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_outbox_worker",
        )
        permission_service.require_internal_worker_principal(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="QUALITYOUTBOXWORKER",
        )

        result = _quality_outbox_worker(session=session).run_once(
            batch_size=payload.batch_size,
            worker_id=f"quality-worker:{current_user.username}",
            dry_run=payload.dry_run,
        )
        data = QualityOutboxWorkerRunOnceData(
            dry_run=result.dry_run,
            processed_count=result.processed_count,
            succeeded_count=result.succeeded_count,
            failed_count=result.failed_count,
            dead_count=result.dead_count,
        )
        audit.record_success(
            module="quality",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="quality_outbox_worker",
            resource_id=None,
            resource_no="run-once",
            before_data={"batch_size": payload.batch_size, "dry_run": payload.dry_run},
            after_data=data.model_dump(),
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(data.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no="run-once",
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # noqa: BLE001 - unified error envelope
        _rollback_safely(session)
        error = BusinessException(code=QUALITY_INTERNAL_ERROR)
        log_safe_error(
            logger_obj=logger,
            message="quality_outbox_worker_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "quality", "action": action, "error_code": QUALITY_INTERNAL_ERROR},
        )
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no="run-once",
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/inspections/{inspection_id}/outbox-status")
def get_quality_inspection_outbox_status(
    inspection_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_inspection",
        resource_id=inspection_id,
    )
    row = session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one_or_none()
    if row is None:
        return _err(QUALITY_NOT_FOUND, status_code=status_of(QUALITY_NOT_FOUND))
    try:
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope=row,
            resource_id=inspection_id,
            resource_no=str(row.inspection_no),
            enforce_action=False,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == "RESOURCE_ACCESS_DENIED":
            _hide_not_found()
        raise
    data: QualityOutboxStatusData = _quality_service(session, request).get_outbox_status(inspection_id)
    return _ok(data.model_dump(mode="json"))


@router.get("/statistics")
def get_quality_statistics(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_statistics",
    )
    if company and item_code:
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope={
                "company": company,
                "item_code": item_code,
                "supplier": supplier,
                "warehouse": warehouse,
                "source_type": source_type,
                "source_id": source_id,
            },
            enforce_action=False,
        )
    data = QualityService(session=session).statistics(
        company=company,
        item_code=item_code,
        supplier=supplier,
        warehouse=warehouse,
        source_type=source_type,
        source_id=source_id,
        from_date=from_date,
        to_date=to_date,
    )
    return _ok(data.model_dump(mode="json"))


@router.get("/statistics/trend")
def get_quality_statistics_trend(
    request: Request,
    period: str = Query(default="monthly", pattern="^(monthly|weekly)$"),
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="quality",
        resource_type="quality_statistics",
    )
    if company and item_code:
        _ensure_quality_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            row_or_scope={
                "company": company,
                "item_code": item_code,
                "supplier": supplier,
                "warehouse": warehouse,
                "source_type": source_type,
                "source_id": source_id,
            },
            enforce_action=False,
        )
    data: QualityStatisticsTrendData = QualityService(session=session).statistics_trend(
        period=period,
        company=company,
        item_code=item_code,
        supplier=supplier,
        warehouse=warehouse,
        source_type=source_type,
        source_id=source_id,
        from_date=from_date,
        to_date=to_date,
    )
    return _ok(data.model_dump(mode="json"))


@router.get("/export")
def export_quality_inspections(
    request: Request,
    format: str | None = Query(default=None, pattern="^(csv|xlsx|pdf)$"),
    inspection_id: int | None = Query(default=None, ge=1),
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_EXPORT
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_export",
        )
        if company and item_code:
            _ensure_quality_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                row_or_scope={
                    "company": company,
                    "item_code": item_code,
                    "supplier": supplier,
                    "warehouse": warehouse,
                    "source_type": source_type,
                    "source_id": source_id,
                },
                enforce_action=False,
            )
        service = QualityService(session=session)
        if format:
            if inspection_id is not None:
                row = session.query(LyQualityInspection).filter(LyQualityInspection.id == inspection_id).one_or_none()
                if row is None:
                    return _err(QUALITY_NOT_FOUND, status_code=status_of(QUALITY_NOT_FOUND))
                _ensure_quality_scope(
                    permission_service=permission_service,
                    current_user=current_user,
                    request=request,
                    action=action,
                    row_or_scope=row,
                    resource_id=inspection_id,
                    resource_no=str(row.inspection_no),
                    enforce_action=False,
                )
            details = service.export_details(
                company=company,
                item_code=item_code,
                supplier=supplier,
                warehouse=warehouse,
                source_type=source_type,
                source_id=source_id,
                status=status,
                from_date=from_date,
                to_date=to_date,
                inspection_id=inspection_id,
            )
            if inspection_id is not None and not details:
                return _err(QUALITY_NOT_FOUND, status_code=status_of(QUALITY_NOT_FOUND))
            export_artifact = QualityExportService().build(
                export_format=format,
                details=details,
                inspection_id=inspection_id,
            )
            _record_success(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=inspection_id,
                resource_no=str(inspection_id) if inspection_id is not None else None,
                after_data={"format": format, "inspection_id": inspection_id, "count": len(details)},
            )
            headers = {"Content-Disposition": f'attachment; filename=\"{export_artifact.filename}\"'}
            return StreamingResponse(
                iter([export_artifact.content]),
                media_type=export_artifact.content_type,
                headers=headers,
            )

        data = service.export_rows(
            company=company,
            item_code=item_code,
            supplier=supplier,
            warehouse=warehouse,
            source_type=source_type,
            source_id=source_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
        )
        _record_success(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            after_data={"total": data.total},
        )
        return _ok(data.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            exc=exc,
            request=request,
        )


@router.get("/diagnostic")
def diagnostic_quality_inspections(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    source_id: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = QUALITY_DIAGNOSTIC
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="quality",
            resource_type="quality_diagnostic",
        )
        if company and item_code:
            _ensure_quality_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                row_or_scope={
                    "company": company,
                    "item_code": item_code,
                    "supplier": supplier,
                    "warehouse": warehouse,
                    "source_type": source_type,
                    "source_id": source_id,
                },
                enforce_action=False,
            )
        data = QualityService(session=session).diagnostic(
            company=company,
            item_code=item_code,
            supplier=supplier,
            warehouse=warehouse,
            source_type=source_type,
            source_id=source_id,
            from_date=from_date,
            to_date=to_date,
        )
        _record_success(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            after_data=data.model_dump(mode="json"),
        )
        return _ok(data.model_dump(mode="json"))
    except Exception as exc:  # noqa: BLE001 - mapped to unified envelope.
        return _handle_write_exception(
            session=session,
            audit=audit,
            context=context,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=None,
            exc=exc,
            request=request,
        )
