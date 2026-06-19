"""FastAPI router for factory statement APIs (TASK-006D)."""

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
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import FACTORY_STATEMENT_DATABASE_WRITE_FAILED
from app.core.error_codes import FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT
from app.core.error_codes import FACTORY_STATEMENT_INTERNAL_ERROR
from app.core.error_codes import FACTORY_STATEMENT_PERMISSION_DENIED
from app.core.error_codes import FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import FACTORY_STATEMENT_SOURCE_NOT_FOUND
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.logging import log_safe_error
from app.core.permissions import FACTORY_STATEMENT_CANCEL
from app.core.permissions import FACTORY_STATEMENT_CONFIRM
from app.core.permissions import FACTORY_STATEMENT_CREATE
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE
from app.core.permissions import FACTORY_STATEMENT_PAYMENT_CREATE
from app.core.permissions import FACTORY_STATEMENT_PAYMENT_CANCEL
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER
from app.core.permissions import FACTORY_STATEMENT_READ
from app.core.permissions import get_permission_source
from app.core.request_id import get_request_id_from_request
from app.models.factory_statement import LyFactoryStatement
from app.schemas.factory_statement import FactoryStatementCancelRequest
from app.schemas.factory_statement import FactoryStatementBankDepositData
from app.schemas.factory_statement import FactoryStatementBankLedgerData
from app.schemas.factory_statement import FactoryStatementBankWithdrawalData
from app.schemas.factory_statement import FactoryStatementConfirmRequest
from app.schemas.factory_statement import FactoryStatementCreateRequest
from app.schemas.factory_statement import FactoryStatementCustomerEvaluationData
from app.schemas.factory_statement import FactoryStatementCustomerReconciliationData
from app.schemas.factory_statement import FactoryStatementCustomerReceivableSummaryData
from app.schemas.factory_statement import FactoryStatementCustomerUnpaidReportData
from app.schemas.factory_statement import FactoryStatementFactoryEvaluationData
from app.schemas.factory_statement import FactoryStatementFactoryPayableSummaryData
from app.schemas.factory_statement import FactoryStatementFactoryReconciliationData
from app.schemas.factory_statement import FactoryStatementSupplierEvaluationData
from app.schemas.factory_statement import FactoryStatementSupplierPayableSummaryData
from app.schemas.factory_statement import FactoryStatementSupplierReconciliationData
from app.schemas.factory_statement import FactoryStatementPayableDraftRequest
from app.schemas.factory_statement import FactoryStatementExpenseReimbursementPaymentData
from app.schemas.factory_statement import FactoryStatementPaymentCancelRequest
from app.schemas.factory_statement import FactoryStatementPaymentCreateRequest
from app.schemas.factory_statement import FactoryStatementPaymentListData
from app.schemas.factory_statement import FactoryStatementPayableWorkerRunOnceRequest
from app.schemas.factory_statement import FactoryStatementPayableWorkerRunOnceData
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from app.services.factory_statement_payable_worker import FactoryStatementPayableWorker
from app.services.factory_statement_service import FactoryStatementService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/factory-statements", tags=["factory_statement"])
logger = logging.getLogger(__name__)
FACTORY_STATEMENT_LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
FACTORY_STATEMENT_SCENARIO_PATTERN = re.compile(r"((?:Z003-FACTORY-STMT|Z005-READBACK-PRECONDITION)-\d{8}-\d{3})")


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _err(code: str, message: str, status_code: int | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or status_of(code, 400),
        content={"code": code, "message": message, "data": {}},
    )


def _app_err(exc: AppException) -> JSONResponse:
    data = getattr(exc, "data", {}) or {}
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": data,
        },
    )


def _map_permission_error(exc: HTTPException) -> JSONResponse:
    code = _permission_error_code(exc)
    detail = exc.detail
    if isinstance(detail, dict):
        if code == FACTORY_STATEMENT_PERMISSION_DENIED:
            return _err(
                FACTORY_STATEMENT_PERMISSION_DENIED,
                message_of(FACTORY_STATEMENT_PERMISSION_DENIED),
                status_of(FACTORY_STATEMENT_PERMISSION_DENIED),
            )
        if code == FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE:
            return _err(
                FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE,
                message_of(FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE),
                status_of(FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE),
            )
        return _err(code, str(detail.get("message") or "请求失败"), exc.status_code)
    if isinstance(detail, str):
        return _err("HTTP_ERROR", detail, exc.status_code)
    return _err("HTTP_ERROR", "请求失败", exc.status_code)


def _permission_error_code(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        if code == AUTH_FORBIDDEN:
            return FACTORY_STATEMENT_PERMISSION_DENIED
        if code == PERMISSION_SOURCE_UNAVAILABLE:
            return FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE
        return code
    return "HTTP_ERROR"


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_local_factory_statement_write_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    db_url = os.getenv("LINGYI_DB_URL", "").strip()
    return app_env == "development" and db_url == FACTORY_STATEMENT_LOCAL_ALLOWED_DB_URL


def _match_factory_statement_scenario_tag(value: str) -> str | None:
    matched = FACTORY_STATEMENT_SCENARIO_PATTERN.search(value)
    if matched is None:
        return None
    return matched.group(1)


def _raise_factory_statement_idempotency_conflict(message: str) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "code": FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT,
            "message": message,
            "data": {},
        },
    )


def _ensure_chain_match(*, label: str, payload_value: str | None, header_value: str | None) -> None:
    normalized_payload = _scope_text(payload_value)
    normalized_header = _scope_text(header_value)
    if normalized_payload is None or normalized_header is None:
        _raise_factory_statement_idempotency_conflict(f"{label} 载体缺失")
    if normalized_payload != normalized_header:
        _raise_factory_statement_idempotency_conflict(f"{label} 载体不一致")


def _validate_local_factory_statement_write_gate(
    *,
    request_obj: Request,
    scenario_carriers: list[str | None],
) -> str:
    if not _is_local_factory_statement_write_enabled():
        _raise_factory_statement_idempotency_conflict("仅允许本地开发测试库执行加工厂对账写入")

    request_id_header = (request_obj.headers.get("X-Request-ID") or "").strip()
    if not request_id_header:
        _raise_factory_statement_idempotency_conflict("request_id 不能为空")

    header_tag = _match_factory_statement_scenario_tag(request_id_header)
    if header_tag is None:
        _raise_factory_statement_idempotency_conflict("request_id 未包含合法 scenario_tag")

    request_id = get_request_id_from_request(request_obj).strip()
    request_tag = _match_factory_statement_scenario_tag(request_id)
    if request_tag is None:
        _raise_factory_statement_idempotency_conflict("request_id 未包含合法 scenario_tag")
    if request_tag != header_tag:
        _raise_factory_statement_idempotency_conflict("request_id 与 scenario_tag 不一致")

    carrier_tags: list[str] = []
    for raw_value in scenario_carriers:
        normalized = _scope_text(raw_value)
        if normalized is None:
            _raise_factory_statement_idempotency_conflict("scenario_tag 载体缺失")
        scenario_tag = _match_factory_statement_scenario_tag(normalized)
        if scenario_tag is None:
            _raise_factory_statement_idempotency_conflict("scenario_tag 载体缺失或格式非法")
        carrier_tags.append(scenario_tag)

    if len(set(carrier_tags)) != 1:
        _raise_factory_statement_idempotency_conflict("scenario_tag 载体不一致")
    if carrier_tags[0] != header_tag:
        _raise_factory_statement_idempotency_conflict("scenario_tag 载体与 request_id 不一致")
    return header_tag


def _rollback_safely(session: Session) -> None:
    try:
        session.rollback()
    except Exception:  # pragma: no cover
        return


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
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
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


def _commit_or_raise_write_error(session: Session) -> None:
    try:
        session.commit()
    except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
        _rollback_safely(session)
        raise BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED) from exc


def _resolve_readable_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
) -> tuple[set[str] | None, set[str] | None]:
    source = get_permission_source()
    if source not in {"erpnext", "fastapi"}:
        return None, None

    permissions = permission_service.get_factory_statement_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=FACTORY_STATEMENT_READ,
        resource_type="factory_statement",
        resource_id=None,
        resource_no=None,
    )
    if permissions is None or permissions.unrestricted:
        return None, None

    readable_companies = {item.strip() for item in permissions.allowed_companies if item and item.strip()}
    readable_suppliers = {item.strip() for item in permissions.allowed_suppliers if item and item.strip()}
    if source == "erpnext":
        return readable_companies or None, readable_suppliers or None
    return readable_companies, readable_suppliers


def _resolve_worker_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
) -> tuple[set[str] | None, set[str] | None]:
    if get_permission_source() not in {"erpnext", "fastapi"}:
        return None, None

    permissions = permission_service.get_factory_statement_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER,
        resource_type="factory_statement_payable_worker",
        resource_id=None,
        resource_no=current_user.username,
    )
    if permissions is None:
        raise BusinessException(code=FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE)
    # Worker must run under explicit supplier+company scope, never unrestricted.
    if permissions.unrestricted:
        raise BusinessException(code=FACTORY_STATEMENT_PERMISSION_DENIED)

    allowed_companies = {item.strip() for item in permissions.allowed_companies if item and item.strip()}
    allowed_suppliers = {item.strip() for item in permissions.allowed_suppliers if item and item.strip()}
    if not allowed_companies or not allowed_suppliers:
        raise BusinessException(code=FACTORY_STATEMENT_PERMISSION_DENIED)
    return allowed_companies, allowed_suppliers


@router.post("/")
def create_factory_statement(
    request: Request,
    payload: FactoryStatementCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        _validate_local_factory_statement_write_gate(
            request_obj=request,
            scenario_carriers=[payload.idempotency_key, payload.scenario_tag],
        )

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(payload.company or "").strip() or None,
            supplier=str(payload.supplier or "").strip() or None,
            resource_type="factory_statement",
            resource_id=None,
            resource_no=None,
            enforce_action=True,
        )

        result = service.create_draft(
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )
        resource_no = result.statement_no

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=result.statement_id,
            resource_no=result.statement_no,
            before_data=None,
            after_data={
                "statement_id": result.statement_id,
                "statement_no": result.statement_no,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        if _permission_error_code(exc) == FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            message = str(detail.get("message") or message_of(FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT))
            return _err(
                FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT,
                message,
                status_of(FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT),
            )
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _map_permission_error(exc)
    except AppException as exc:
        _rollback_safely(session)
        exc_data = getattr(exc, "data", {}) or {}
        conflict_statement_no = str(exc_data.get("statement_no") or "").strip() or None
        conflict_statement_id = exc_data.get("statement_id")
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=int(conflict_statement_id) if conflict_statement_id is not None else None,
                resource_no=resource_no or conflict_statement_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR, message="加工厂对账单处理失败")
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return JSONResponse(
            status_code=error.status_code,
            content={
                "code": error.code,
                "message": error.message,
                "data": None,
            },
        )


@router.post("/{statement_id}/confirm")
def confirm_factory_statement(
    statement_id: int,
    request: Request,
    payload: FactoryStatementConfirmRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_CONFIRM
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        _validate_local_factory_statement_write_gate(
            request_obj=request,
            scenario_carriers=[payload.idempotency_key, payload.scenario_tag],
        )
        _ensure_chain_match(label="company", payload_value=payload.company, header_value=str(header.company))
        _ensure_chain_match(label="supplier", payload_value=payload.supplier, header_value=str(header.supplier))
        _ensure_chain_match(label="statement_no", payload_value=payload.statement_no, header_value=str(header.statement_no))

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        result = service.confirm_statement(
            statement_id=statement_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=resource_no,
            before_data={"status": str(header.statement_status)},
            after_data={
                "statement_id": result.id,
                "statement_no": result.statement_no,
                "status": result.status,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        if _permission_error_code(exc) == FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            message = str(detail.get("message") or message_of(FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT))
            return _err(
                FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT,
                message,
                status_of(FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT),
            )
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
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
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/{statement_id}/cancel")
def cancel_factory_statement(
    statement_id: int,
    request: Request,
    payload: FactoryStatementCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_CANCEL
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        _validate_local_factory_statement_write_gate(
            request_obj=request,
            scenario_carriers=[payload.idempotency_key, payload.scenario_tag, payload.reason],
        )
        _ensure_chain_match(label="company", payload_value=payload.company, header_value=str(header.company))
        _ensure_chain_match(label="supplier", payload_value=payload.supplier, header_value=str(header.supplier))
        _ensure_chain_match(label="statement_no", payload_value=payload.statement_no, header_value=str(header.statement_no))

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        result = service.cancel_statement(
            statement_id=statement_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=resource_no,
            before_data={"status": str(header.statement_status)},
            after_data={
                "statement_id": result.id,
                "statement_no": result.statement_no,
                "status": result.status,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        if _permission_error_code(exc) == FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            message = str(detail.get("message") or message_of(FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT))
            return _err(
                FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT,
                message,
                status_of(FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT),
            )
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
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
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/{statement_id}/payable-draft")
def create_factory_statement_payable_draft(
    statement_id: int,
    request: Request,
    payload: FactoryStatementPayableDraftRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        _validate_local_factory_statement_write_gate(
            request_obj=request,
            scenario_carriers=[payload.idempotency_key, payload.scenario_tag],
        )
        _ensure_chain_match(label="company", payload_value=payload.company, header_value=str(header.company))
        _ensure_chain_match(label="supplier", payload_value=payload.supplier, header_value=str(header.supplier))
        _ensure_chain_match(label="statement_no", payload_value=payload.statement_no, header_value=str(header.statement_no))
        _ensure_chain_match(label="source_ref_or_source_doc", payload_value=payload.source_ref, header_value=str(header.statement_no))
        _ensure_chain_match(label="source_type", payload_value=payload.source_type, header_value=str(header.source_type))
        _ensure_chain_match(label="status_action", payload_value=payload.status_action, header_value="payable_draft")

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        result = service.create_payable_draft_outbox(
            statement_id=statement_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
            erp_adapter=None,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=resource_no,
            before_data={"status": str(header.statement_status)},
            after_data={
                "statement_id": result.statement_id,
                "statement_no": result.statement_no,
                "status": result.status,
                "payable_outbox_id": result.payable_outbox_id,
                "payable_outbox_status": result.payable_outbox_status,
                "idempotent_replay": result.idempotent_replay,
            },
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
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
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/internal/payable-draft-sync/run-once")
def run_factory_statement_payable_worker_once(
    request: Request,
    payload: FactoryStatementPayableWorkerRunOnceRequest = Body(default=FactoryStatementPayableWorkerRunOnceRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    try:
        permission_service.require_action_from_roles_only(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement_payable_worker",
            resource_id=None,
        )
        if not current_user.is_service_account:
            permission_service.record_security_denial(
                request_obj=request,
                current_user=current_user,
                action=action,
                resource_type="FactoryStatementPayableWorker",
                resource_no=current_user.username,
                deny_reason="内部 payable worker 仅允许服务账号调用",
                module="factory_statement",
            )
            return _err(
                FACTORY_STATEMENT_PERMISSION_DENIED,
                message_of(FACTORY_STATEMENT_PERMISSION_DENIED),
                status_of(FACTORY_STATEMENT_PERMISSION_DENIED),
            )

        allowed_companies, allowed_suppliers = _resolve_worker_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        worker = FactoryStatementPayableWorker(
            session=session,
            adapter=ERPNextPurchaseInvoiceAdapter(request_obj=None, use_service_account=True),
        )
        result = worker.run_once(
            batch_size=payload.batch_size,
            worker_id=f"factory-statement-payable-worker:{current_user.username}",
            dry_run=payload.dry_run,
            allowed_companies=allowed_companies,
            allowed_suppliers=allowed_suppliers,
        )
        data = FactoryStatementPayableWorkerRunOnceData(
            dry_run=result.dry_run,
            processed_count=result.processed_count,
            succeeded_count=result.succeeded_count,
            failed_count=result.failed_count,
            dead_count=result.dead_count,
        )
        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT_PAYABLE_WORKER",
            resource_id=None,
            resource_no=current_user.username,
            before_data={"dry_run": payload.dry_run, "batch_size": payload.batch_size},
            after_data=data.model_dump(mode="json"),
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
                resource_no=current_user.username,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=current_user.username,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/")
def list_factory_statements(
    request: Request,
    company: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    statement_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data = service.list_statements(
            company=company,
            supplier=supplier,
            from_date=from_date,
            to_date=to_date,
            statement_status=statement_status,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/payments")
def list_factory_statement_payments(
    request: Request,
    company: str | None = Query(default=None),
    statement_id: int | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement_payment",
            resource_id=statement_id,
        )
        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=company,
            supplier=supplier,
            resource_type="factory_statement_payment",
            resource_id=statement_id,
            resource_no=statement_no,
            enforce_action=False,
        )
        data: FactoryStatementPaymentListData = service.list_payment_entries(
            company=company,
            statement_id=statement_id,
            statement_no=statement_no,
            supplier=supplier,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT_PAYMENT",
            resource_id=statement_id,
            resource_no=statement_no,
            before_data=None,
            after_data={"total": data.total, "page": data.page, "page_size": data.page_size},
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
                resource_id=statement_id,
                resource_no=statement_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_payment_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=statement_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/{statement_id}/payments")
def create_factory_statement_payment(
    statement_id: int,
    request: Request,
    payload: FactoryStatementPaymentCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_PAYMENT_CREATE
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement_payment",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        _validate_local_factory_statement_write_gate(
            request_obj=request,
            scenario_carriers=[payload.idempotency_key, payload.scenario_tag],
        )
        _ensure_chain_match(label="company", payload_value=payload.company, header_value=str(header.company))
        _ensure_chain_match(label="supplier", payload_value=payload.supplier, header_value=str(header.supplier))
        _ensure_chain_match(label="statement_no", payload_value=payload.statement_no, header_value=str(header.statement_no))

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement_payment",
            resource_id=statement_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        data = service.create_payment_entry(
            statement_id=statement_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT_PAYMENT",
            resource_id=int(data.id),
            resource_no=str(data.payment_entry),
            before_data={"statement_id": statement_id, "statement_status": str(header.statement_status)},
            after_data=data.model_dump(mode="json"),
            context=context,
        )
        _commit_or_raise_write_error(session)
        return JSONResponse(status_code=201, content=_ok(data.model_dump(mode="json")))
    except HTTPException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
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
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_payment_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.post("/{statement_id}/payments/{payment_id}/cancel")
def cancel_factory_statement_payment(
    statement_id: int,
    payment_id: int,
    request: Request,
    payload: FactoryStatementPaymentCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_PAYMENT_CANCEL
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    resource_no: str | None = None
    before_data: dict[str, Any] | None = None
    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement_payment",
            resource_id=payment_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=payment_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )
        resource_no = str(header.statement_no)

        _validate_local_factory_statement_write_gate(
            request_obj=request,
            scenario_carriers=[payload.idempotency_key, payload.scenario_tag],
        )
        _ensure_chain_match(label="company", payload_value=payload.company, header_value=str(header.company))
        _ensure_chain_match(label="statement_no", payload_value=payload.statement_no, header_value=str(header.statement_no))

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement_payment",
            resource_id=payment_id,
            resource_no=resource_no,
            enforce_action=False,
        )

        data = service.cancel_payment_entry(
            statement_id=statement_id,
            payment_id=payment_id,
            payload=payload,
            operator=current_user.username,
            request_id=get_request_id_from_request(request),
        )
        before_data = {"statement_id": statement_id, "payment_status": "submitted"}

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT_PAYMENT",
            resource_id=int(data.id),
            resource_no=str(data.payment_entry),
            before_data=before_data,
            after_data=data.model_dump(mode="json"),
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(data.model_dump(mode="json"))
    except HTTPException as exc:
        _rollback_safely(session)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=payment_id,
                resource_no=resource_no,
                error_code=_permission_error_code(exc),
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
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
                resource_id=payment_id,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_payment_cancel_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=payment_id,
                resource_no=resource_no,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/purchase-invoices")
def list_purchase_invoices(
    request: Request,
    company: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    supplier_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    service = FactoryStatementService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="factory_statement",
        resource_type="purchase_invoice",
        resource_id=None,
    )
    readable_companies, readable_suppliers = _resolve_readable_scope(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
    )
    data = service.list_purchase_invoices(
        company=company,
        supplier=supplier,
        supplier_name=supplier_name,
        status=status,
        page=page,
        page_size=page_size,
        readable_companies=readable_companies,
        readable_suppliers=readable_suppliers,
    )
    return _ok(data)


@router.get("/expense-reimbursement-payments")
def list_expense_reimbursement_payments(
    request: Request,
    payment_no: str | None = Query(default=None),
    reimbursement_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    payment_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementExpenseReimbursementPaymentData = service.get_expense_reimbursement_payments(
            payment_no=payment_no,
            reimbursement_no=reimbursement_no,
            statement_no=statement_no,
            supplier=supplier,
            payment_status=payment_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/bank-deposits")
def list_bank_deposits(
    request: Request,
    deposit_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    bank_name: str | None = Query(default=None),
    account_name: str | None = Query(default=None),
    deposit_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementBankDepositData = service.get_bank_deposits(
            deposit_no=deposit_no,
            statement_no=statement_no,
            bank_name=bank_name,
            account_name=account_name,
            deposit_status=deposit_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/bank-withdrawals")
def list_bank_withdrawals(
    request: Request,
    withdrawal_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    bank_name: str | None = Query(default=None),
    account_name: str | None = Query(default=None),
    withdrawal_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementBankWithdrawalData = service.get_bank_withdrawals(
            withdrawal_no=withdrawal_no,
            statement_no=statement_no,
            bank_name=bank_name,
            account_name=account_name,
            withdrawal_status=withdrawal_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/customer-evaluations")
def list_customer_evaluations(
    request: Request,
    evaluation_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    assessor: str | None = Query(default=None),
    score_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementCustomerEvaluationData = service.get_customer_evaluations(
            evaluation_no=evaluation_no,
            statement_no=statement_no,
            customer_name=customer_name,
            assessor=assessor,
            score_level=score_level,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/customer-reconciliations")
def list_customer_reconciliations(
    request: Request,
    reconciliation_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    settlement_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementCustomerReconciliationData = service.get_customer_reconciliations(
            reconciliation_no=reconciliation_no,
            statement_no=statement_no,
            customer_name=customer_name,
            settlement_status=settlement_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/customer-unpaid-reports")
def list_customer_unpaid_reports(
    request: Request,
    report_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    collection_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementCustomerUnpaidReportData = service.get_customer_unpaid_reports(
            report_no=report_no,
            statement_no=statement_no,
            customer_name=customer_name,
            collection_status=collection_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/customer-receivables")
@router.get("/customer-receivable-summaries")
def list_customer_receivable_summaries(
    request: Request,
    summary_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    customer_name: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementCustomerReceivableSummaryData = service.get_customer_receivable_summaries(
            summary_no=summary_no,
            statement_no=statement_no,
            customer_name=customer_name,
            risk_level=risk_level,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/factory-evaluations")
def list_factory_evaluations(
    request: Request,
    evaluation_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    factory_name: str | None = Query(default=None),
    assessor: str | None = Query(default=None),
    score_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementFactoryEvaluationData = service.get_factory_evaluations(
            evaluation_no=evaluation_no,
            statement_no=statement_no,
            factory_name=factory_name,
            assessor=assessor,
            score_level=score_level,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/factory-reconciliations")
def list_factory_reconciliations(
    request: Request,
    reconciliation_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    factory_name: str | None = Query(default=None),
    settlement_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementFactoryReconciliationData = service.get_factory_reconciliations(
            reconciliation_no=reconciliation_no,
            statement_no=statement_no,
            supplier=supplier,
            factory_name=factory_name,
            settlement_status=settlement_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/factory-payable-summaries")
def list_factory_payable_summaries(
    request: Request,
    summary_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    factory_name: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementFactoryPayableSummaryData = service.get_factory_payable_summaries(
            summary_no=summary_no,
            statement_no=statement_no,
            supplier=supplier,
            factory_name=factory_name,
            risk_level=risk_level,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/supplier-evaluations")
def list_supplier_evaluations(
    request: Request,
    evaluation_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    assessor: str | None = Query(default=None),
    score_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementSupplierEvaluationData = service.get_supplier_evaluations(
            evaluation_no=evaluation_no,
            statement_no=statement_no,
            supplier=supplier,
            assessor=assessor,
            score_level=score_level,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/supplier-reconciliations")
def list_supplier_reconciliations(
    request: Request,
    reconciliation_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    supplier_code: str | None = Query(default=None),
    settlement_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementSupplierReconciliationData = service.get_supplier_reconciliations(
            reconciliation_no=reconciliation_no,
            statement_no=statement_no,
            supplier=supplier,
            supplier_code=supplier_code,
            settlement_status=settlement_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/supplier-payable-summaries")
def list_supplier_payable_summaries(
    request: Request,
    summary_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    supplier: str | None = Query(default=None),
    supplier_code: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementSupplierPayableSummaryData = service.get_supplier_payable_summaries(
            summary_no=summary_no,
            statement_no=statement_no,
            supplier=supplier,
            supplier_code=supplier_code,
            risk_level=risk_level,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/bank-ledgers")
def list_bank_ledgers(
    request: Request,
    ledger_no: str | None = Query(default=None),
    statement_no: str | None = Query(default=None),
    bank_name: str | None = Query(default=None),
    account_name: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    ledger_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=None,
        )
        readable_companies, readable_suppliers = _resolve_readable_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
        )

        data: FactoryStatementBankLedgerData = service.get_bank_ledgers(
            ledger_no=ledger_no,
            statement_no=statement_no,
            bank_name=bank_name,
            account_name=account_name,
            transaction_type=transaction_type,
            ledger_status=ledger_status,
            review_status=review_status,
            keyword=keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
            readable_companies=readable_companies,
            readable_suppliers=readable_suppliers,
        )

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=None,
            resource_no=None,
            before_data=None,
            after_data={
                "total": data.total,
                "page": data.page,
                "page_size": data.page_size,
            },
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
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)


@router.get("/{statement_id}")
def get_factory_statement_detail(
    statement_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = FACTORY_STATEMENT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    service = FactoryStatementService(session=session)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="factory_statement",
            resource_type="factory_statement",
            resource_id=statement_id,
        )

        header = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one_or_none()
        if header is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=FACTORY_STATEMENT_SOURCE_NOT_FOUND,
            )
            return _err(
                FACTORY_STATEMENT_SOURCE_NOT_FOUND,
                message_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
                status_of(FACTORY_STATEMENT_SOURCE_NOT_FOUND),
            )

        permission_service.ensure_factory_statement_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(header.company),
            supplier=str(header.supplier),
            resource_type="factory_statement",
            resource_id=statement_id,
            resource_no=str(header.statement_no),
            enforce_action=False,
        )

        data = service.get_statement_detail(statement_id=statement_id)

        audit.record_success(
            module="factory_statement",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="FACTORY_STATEMENT",
            resource_id=statement_id,
            resource_no=str(header.statement_no),
            before_data=None,
            after_data={"statement_id": statement_id, "statement_no": str(header.statement_no)},
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
                resource_id=statement_id,
                resource_no=None,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except Exception as exc:  # pragma: no cover
        _rollback_safely(session)
        log_safe_error(
            logger_obj=logger,
            message="factory_statement_internal_error",
            exc=exc,
            request_id=get_request_id_from_request(request),
            extra={"module": "factory_statement", "action": action, "error_code": FACTORY_STATEMENT_INTERNAL_ERROR},
        )
        error = BusinessException(code=FACTORY_STATEMENT_INTERNAL_ERROR)
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                action=action,
                current_user=current_user,
                resource_id=statement_id,
                resource_no=None,
                error_code=error.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(error)
