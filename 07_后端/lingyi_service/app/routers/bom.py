"""FastAPI router for BOM module (TASK-001/TASK-001A)."""

from __future__ import annotations

from collections.abc import Generator
import logging
import os
import re
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
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
from app.core.error_codes import BOM_DEFAULT_CONFLICT
from app.core.error_codes import BOM_INTERNAL_ERROR
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import WORKSHOP_IDEMPOTENCY_CONFLICT
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BomInternalError
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseWriteFailed
from app.core.exceptions import is_default_bom_unique_conflict
from app.core.logging import log_safe_error
from app.core.request_id import get_request_id_from_request
from app.core.permissions import BOM_CREATE
from app.core.permissions import BOM_DEACTIVATE
from app.core.permissions import BOM_PUBLISH
from app.core.permissions import BOM_READ
from app.core.permissions import BOM_SET_DEFAULT
from app.core.permissions import BOM_UPDATE
from app.schemas.bom import BomActivateData
from app.schemas.bom import BomAccessoriesPackagingData
from app.schemas.bom import BomAccessoriesPackagingQuery
from app.schemas.bom import BomCarrierRequest
from app.schemas.bom import BomCreateRequest
from app.schemas.bom import BomDeactivateData
from app.schemas.bom import BomDeactivateRequest
from app.schemas.bom import BomDetailData
from app.schemas.bom import BomExplodeData
from app.schemas.bom import BomExplodeRequest
from app.schemas.bom import BomFabricData
from app.schemas.bom import BomFabricQuery
from app.schemas.bom import BomListData
from app.schemas.bom import BomMaterialGalleryData
from app.schemas.bom import BomMaterialGalleryQuery
from app.schemas.bom import BomMaterialProcessingData
from app.schemas.bom import BomMaterialDeductionData
from app.schemas.bom import BomMaterialDeductionQuery
from app.schemas.bom import BomMaterialSalesOutboundData
from app.schemas.bom import BomMaterialSalesOutboundQuery
from app.schemas.bom import BomMaterialProcessingInboundData
from app.schemas.bom import BomMaterialProcessingInboundQuery
from app.schemas.bom import BomMaterialProcessingQuery
from app.schemas.bom import BomMaterialTypeData
from app.schemas.bom import BomMaterialTypeQuery
from app.schemas.bom import BomMaterialUnitData
from app.schemas.bom import BomMaterialUnitQuery
from app.schemas.bom import BomPurchaseOrderData
from app.schemas.bom import BomPurchaseOrderQuery
from app.schemas.bom import BomProcessingTypeData
from app.schemas.bom import BomProcessingTypeQuery
from app.schemas.bom import BomListQuery
from app.schemas.bom import BomSetDefaultData
from app.schemas.bom import BomUpdateData
from app.schemas.bom import BomUpdateRequest
from app.schemas.bom import FoundationTemplateCreateRequest
from app.schemas.bom import FoundationTemplateDeactivateRequest
from app.schemas.bom import FoundationTemplateListData
from app.schemas.bom import FoundationTemplateNodeCreateRequest
from app.schemas.bom import FoundationTemplateNodeDeactivateRequest
from app.schemas.bom import FoundationTemplateNodeUpdateRequest
from app.schemas.bom import FoundationTemplateUpdateRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.bom_service import BomService
from app.services.foundation_template_service import FoundationTemplateMutationResult
from app.services.foundation_template_service import FoundationTemplateService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/bom", tags=["bom"])
logger = logging.getLogger(__name__)

BOM_ACTIVATE_ACTION = "bom:activate"
BOM_EXPLODE_ACTION = "bom:explode"
BOM_TEMPLATE_CREATE_ACTION = "bom:template_create"
BOM_TEMPLATE_UPDATE_ACTION = "bom:template_update"
BOM_TEMPLATE_DEACTIVATE_ACTION = "bom:template_deactivate"
BOM_TEMPLATE_NODE_CREATE_ACTION = "bom:template_node_create"
BOM_TEMPLATE_NODE_UPDATE_ACTION = "bom:template_node_update"
BOM_TEMPLATE_NODE_DEACTIVATE_ACTION = "bom:template_node_deactivate"
BOM_LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
BOM_LOCAL_SCENARIO_PATTERN = re.compile(r"(Z002-BOM-\d{8}-\d{3})")
BOM_LOCAL_REQUEST_PATTERN = re.compile(
    r"(Z002-BOM-\d{8}-\d{3})-RQ-I([0-9A-F]{4})-B([0-9A-F]{4})-R([0-9A-F]{4})"
)


def _is_local_bom_write_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    db_url = os.getenv("LINGYI_DB_URL", "").strip()
    return app_env == "development" and db_url == BOM_LOCAL_ALLOWED_DB_URL


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _match_bom_scenario_tag(value: str) -> str | None:
    matched = BOM_LOCAL_SCENARIO_PATTERN.search(value)
    if matched is None:
        return None
    return matched.group(1)


def _build_bom_carrier_code(value: Any) -> str | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    hash_value = 2166136261
    for byte in normalized.encode("utf-8"):
        hash_value ^= byte
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return f"{hash_value:08X}"[-4:]


def _extract_bom_request_carriers(value: str) -> tuple[str | None, str | None, str | None, str | None]:
    normalized = _scope_text(value)
    if normalized is None:
        return None, None, None, None
    matched = BOM_LOCAL_REQUEST_PATTERN.fullmatch(normalized)
    if matched is None:
        return None, None, None, None
    return (
        _scope_text(matched.group(1)),
        _scope_text(matched.group(2)),
        _scope_text(matched.group(3)),
        _scope_text(matched.group(4)),
    )


def _raise_bom_idempotency_conflict(message: str) -> None:
    raise BusinessException(code=WORKSHOP_IDEMPOTENCY_CONFLICT, message=message)


def _validate_local_bom_request_gate(
    *,
    request_obj: Request,
    request_id: str,
    carriers: list[str | None],
    expected_item_code: Any,
    expected_bom_ref: Any,
    expected_reason: Any = None,
) -> str:
    if not _is_local_bom_write_enabled():
        _raise_bom_idempotency_conflict("仅允许本地开发测试库执行 BOM 写入")

    request_id_header = (request_obj.headers.get("X-Request-ID") or "").strip()
    if not request_id_header:
        _raise_bom_idempotency_conflict("request_id 不能为空")

    header_tag = _match_bom_scenario_tag(request_id_header)
    if header_tag is None:
        _raise_bom_idempotency_conflict("request_id 未包含合法 scenario_tag")

    normalized_request_id = (request_id or "").strip()
    request_tag = _match_bom_scenario_tag(normalized_request_id)
    if request_tag is None:
        _raise_bom_idempotency_conflict("request_id 未包含合法 scenario_tag")
    if request_tag != header_tag:
        _raise_bom_idempotency_conflict("request_id 与 scenario_tag 不一致")

    header_carrier_tag, header_item_code, header_bom_ref_code, header_reason_code = _extract_bom_request_carriers(
        request_id_header,
    )
    if (
        header_carrier_tag is None
        or header_item_code is None
        or header_bom_ref_code is None
        or header_reason_code is None
    ):
        _raise_bom_idempotency_conflict("request_id 载体缺失或格式非法")
    if header_carrier_tag != header_tag:
        _raise_bom_idempotency_conflict("request_id 与 scenario_tag 不一致")

    (
        request_carrier_tag,
        request_item_code,
        request_bom_ref_code,
        request_reason_code,
    ) = _extract_bom_request_carriers(normalized_request_id)
    if (
        request_carrier_tag is None
        or request_item_code is None
        or request_bom_ref_code is None
        or request_reason_code is None
    ):
        _raise_bom_idempotency_conflict("request_id 载体缺失或格式非法")
    if request_carrier_tag != header_carrier_tag:
        _raise_bom_idempotency_conflict("request_id 与 scenario_tag 不一致")
    if request_item_code != header_item_code or request_bom_ref_code != header_bom_ref_code:
        _raise_bom_idempotency_conflict("request_id 载体不一致")
    if request_reason_code != header_reason_code:
        _raise_bom_idempotency_conflict("request_id 载体不一致")

    expected_item_code_hash = _build_bom_carrier_code(expected_item_code)
    expected_bom_ref_hash = _build_bom_carrier_code(expected_bom_ref)
    expected_reason_hash = _build_bom_carrier_code(_scope_text(expected_reason) or "NONE")
    if expected_item_code_hash is None:
        _raise_bom_idempotency_conflict("item_code 载体缺失")
    if expected_bom_ref_hash is None:
        _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体缺失")
    if expected_reason_hash is None:
        _raise_bom_idempotency_conflict("reason 载体缺失")

    if header_item_code != expected_item_code_hash:
        _raise_bom_idempotency_conflict("item_code 载体与业务载体不一致")
    if header_bom_ref_code != expected_bom_ref_hash:
        _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
    if header_reason_code != expected_reason_hash:
        _raise_bom_idempotency_conflict("reason 载体与业务载体不一致")

    carrier_tags: list[str] = []
    for raw_value in carriers:
        normalized = _scope_text(raw_value)
        if normalized is None:
            _raise_bom_idempotency_conflict("scenario_tag 载体缺失")
        scenario_tag = _match_bom_scenario_tag(normalized)
        if scenario_tag is None:
            _raise_bom_idempotency_conflict("scenario_tag 载体缺失或格式非法")
        carrier_tags.append(scenario_tag)

    if len(set(carrier_tags)) != 1:
        _raise_bom_idempotency_conflict("scenario_tag 载体不一致")
    if carrier_tags[0] != header_tag:
        _raise_bom_idempotency_conflict("scenario_tag 载体与 request_id 不一致")
    return header_tag


def get_db_session() -> Generator[Session, None, None]:
    """Yield SQLAlchemy session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _err(code: str, message: str, status_code: int | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or status_of(code, 400),
        content={"code": code, "message": message, "data": None},
    )


def _app_err(exc: AppException) -> JSONResponse:
    return _err(exc.code, exc.message, status_code=exc.status_code)


def _unknown_to_internal_error(request: Request, action: str, exc: Exception) -> BomInternalError:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "bom_internal_error",
        exc,
        request_id=request_id,
        extra={
            "error_code": BOM_INTERNAL_ERROR,
            "module": "bom",
            "action": action,
        },
    )
    return BomInternalError()


def _rollback_safely(session: Session, request: Request, action: str, origin: BaseException) -> None:
    try:
        session.rollback()
    except Exception as rollback_exc:  # pragma: no cover - hard to reproduce with sqlite
        request_id = get_request_id_from_request(request)
        error_code = origin.code if isinstance(origin, AppException) else ""
        log_safe_error(
            logger,
            "bom_rollback_failed",
            rollback_exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "bom",
                "action": action,
            },
        )


def _map_write_db_exception(request: Request, action: str, exc: BaseException) -> AppException:
    request_id = get_request_id_from_request(request)
    log_safe_error(
        logger,
        "bom_database_write_failed",
        exc,
        request_id=request_id,
        extra={
            "error_code": DATABASE_WRITE_FAILED,
            "module": "bom",
            "action": action,
        },
    )
    if isinstance(exc, IntegrityError) and is_default_bom_unique_conflict(exc):
        return BusinessException(code=BOM_DEFAULT_CONFLICT, message="默认 BOM 冲突，请重试")
    return DatabaseWriteFailed()


def _commit_or_raise_write_error(session: Session, request: Request, action: str) -> None:
    try:
        session.commit()
    except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        raise _map_write_db_exception(request=request, action=action, exc=exc) from exc


def _resource_no(snapshot: dict[str, Any] | None) -> str | None:
    if not snapshot:
        return None
    bom_info = snapshot.get("bom", {})
    if not isinstance(bom_info, dict):
        return None
    value = bom_info.get("bom_no")
    return str(value) if value else None


def _snapshot_bom_carriers(snapshot: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not snapshot:
        return None, None
    bom_info = snapshot.get("bom", {})
    if not isinstance(bom_info, dict):
        return None, None
    return _scope_text(bom_info.get("item_code")), _scope_text(bom_info.get("bom_no"))


def _record_failure_safely(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    request: Request,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
    error_code: str,
) -> None:
    try:
        audit.record_failure(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=resource_id,
            resource_no=resource_no,
            before_data=before_data,
            after_data=after_data,
            error_code=error_code,
            context=context,
        )
        session.commit()
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        request_id = get_request_id_from_request(request)
        log_safe_error(
            logger,
            "operation_audit_write_failed",
            exc,
            request_id=request_id,
            extra={
                "error_code": error_code,
                "module": "bom",
                "action": action,
                "resource_type": "bom",
                "resource_id": resource_id if resource_id is not None else "",
                "resource_no": resource_no or "",
                "user_id": current_user.username,
            },
        )


def _is_local_bom_gate_failure(exc: AppException) -> bool:
    return exc.code == WORKSHOP_IDEMPOTENCY_CONFLICT


def _require_any_action(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request_obj: Request,
    actions: tuple[str, ...],
    module: str = "bom",
    resource_type: str | None = None,
    resource_id: int | None = None,
    resource_item_code: str | None = None,
) -> None:
    """Require one action from a primary+fallback set.

    Notes:
    - `actions[0]` is the canonical action frozen by design.
    - subsequent actions are compatibility aliases kept for historical role sets.
    """
    if not actions:
        raise ValueError("actions must not be empty")

    agg = permission_service.get_actions(
        current_user=current_user,
        request_obj=request_obj,
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_item_code=resource_item_code,
        action_context=actions[0],
    )
    if any(action in set(agg.actions) for action in actions):
        return

    # Reuse baseline denied-path auditing and response envelope.
    permission_service.require_action(
        current_user=current_user,
        request_obj=request_obj,
        action=actions[0],
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_item_code=resource_item_code,
    )


def _require_bom_explode_permission(
    bom_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> None:
    permission_service = PermissionService(session=session)
    _require_any_action(
        permission_service=permission_service,
        current_user=current_user,
        request_obj=request,
        actions=(BOM_EXPLODE_ACTION, BOM_READ),
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )


@router.post("/")
def create_bom(
    payload: BomCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """创建 BOM。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_CREATE,
        module="bom",
        resource_type="bom",
        resource_id=None,
        resource_item_code=payload.item_code,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_CREATE
    request_id = get_request_id_from_request(request)
    result = None
    after_data = None

    try:
        _validate_local_bom_request_gate(
            request_obj=request,
            request_id=request_id,
            carriers=[payload.idempotency_key, payload.source_ref, payload.scenario_tag],
            expected_item_code=payload.item_code,
            expected_bom_ref=payload.source_ref,
            expected_reason=None,
        )
        result = service.create_bom(payload=payload, operator=current_user.username)
        created_bom = service.get_bom_by_no(result.name)
        resource_id = int(created_bom.id) if created_bom else None
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=resource_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=resource_id,
            resource_no=result.name,
            before_data=None,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(result.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        if _is_local_bom_gate_failure(exc):
            return _app_err(exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=f"{payload.item_code}:{payload.version_no}",
            before_data=None,
            after_data=after_data,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=None,
            resource_no=f"{payload.item_code}:{payload.version_no}",
            before_data=None,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.get("/styles")
@router.get("/")
def list_bom(
    request: Request,
    company: str | None = None,
    item_code: str | None = None,
    keyword: str | None = Query(default=None, max_length=140),
    status: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 列表。"""
    # 读权限动作：bom:read
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )
    service = BomService(session=session)
    query = BomListQuery(
        company=company,
        item_code=item_code,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
    )
    try:
        data: BomListData = service.list_bom(query=query, allowed_item_codes=allowed_item_codes)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/material-gallery")
def list_bom_material_gallery(
    request: Request,
    item_code: str | None = None,
    material_item_code: str | None = None,
    color: str | None = None,
    size: str | None = None,
    category: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料图库（只读）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomMaterialGalleryQuery(
        item_code=item_code,
        material_item_code=material_item_code,
        color=color,
        size=size,
        category=category,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomMaterialGalleryData = service.list_material_gallery(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/fabrics")
def list_bom_fabrics(
    request: Request,
    item_code: str | None = None,
    material_item_code: str | None = None,
    fabric_name: str | None = None,
    color: str | None = None,
    specification: str | None = None,
    supplier_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 面料（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomFabricQuery(
        item_code=item_code,
        material_item_code=material_item_code,
        fabric_name=fabric_name,
        color=color,
        specification=specification,
        supplier_name=supplier_name,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomFabricData = service.list_fabrics(query=query, allowed_item_codes=allowed_item_codes)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/accessories-packaging")
def list_bom_accessories_packaging(
    request: Request,
    item_code: str | None = None,
    material_item_code: str | None = None,
    material_name: str | None = None,
    category: str | None = None,
    supplier_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 辅料/包材（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomAccessoriesPackagingQuery(
        item_code=item_code,
        material_item_code=material_item_code,
        material_name=material_name,
        category=category,
        supplier_name=supplier_name,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomAccessoriesPackagingData = service.list_accessories_packaging(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/purchase-orders")
def list_bom_purchase_orders(
    request: Request,
    purchase_no: str | None = None,
    supplier_name: str | None = None,
    material_keyword: str | None = None,
    status: str | None = None,
    delivery_date_from: str | None = None,
    delivery_date_to: str | None = None,
    min_qty: float | None = None,
    max_qty: float | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料采购单（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomPurchaseOrderQuery(
        purchase_no=purchase_no,
        supplier_name=supplier_name,
        material_keyword=material_keyword,
        status=status,
        delivery_date_from=delivery_date_from,
        delivery_date_to=delivery_date_to,
        min_qty=min_qty,
        max_qty=max_qty,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomPurchaseOrderData = service.list_purchase_orders(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


def _template_resource_type(template_type: str) -> str:
    return "workmanship_template" if template_type == "workmanship" else "size_spec_template"


def _commit_template_success(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    template_type: str,
    result: FoundationTemplateMutationResult,
) -> None:
    audit = AuditService(session=session)
    audit.record_success(
        module="bom",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=_template_resource_type(template_type),
        resource_id=int(result.item.id),
        resource_no=getattr(result.item, "template_code", None) or getattr(result.item, "code", None),
        before_data=result.before,
        after_data=result.after,
        context=AuditContext.from_request(request),
    )
    _commit_or_raise_write_error(session=session, request=request, action=action)


def _record_template_failure(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    template_type: str,
    resource_id: int | None,
    resource_no: str | None,
    error_code: str,
) -> None:
    try:
        session.rollback()
    except Exception:
        pass
    audit = AuditService(session=session)
    audit.record_failure(
        module="bom",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=_template_resource_type(template_type),
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=None,
        after_data=None,
        error_code=error_code,
        context=AuditContext.from_request(request),
    )
    _commit_or_raise_write_error(session=session, request=request, action=action)


def _require_template_action(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    template_type: str,
    resource_id: int | None = None,
) -> None:
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="bom",
        resource_type=_template_resource_type(template_type),
        resource_id=resource_id,
    )


def _list_foundation_templates(
    *,
    request: Request,
    template_type: str,
    company: str | None,
    keyword: str | None,
    status: str | None,
    page: int,
    page_size: int,
    current_user: CurrentUser,
    session: Session,
):
    _require_template_action(
        session=session,
        request=request,
        current_user=current_user,
        action=BOM_READ,
        template_type=template_type,
    )
    try:
        data: FoundationTemplateListData = FoundationTemplateService(session).list_templates(
            template_type=template_type,
            company=company,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


def _create_foundation_template(
    *,
    request: Request,
    template_type: str,
    payload: FoundationTemplateCreateRequest,
    current_user: CurrentUser,
    session: Session,
):
    action = BOM_TEMPLATE_CREATE_ACTION
    _require_template_action(
        session=session,
        request=request,
        current_user=current_user,
        action=BOM_UPDATE,
        template_type=template_type,
    )
    try:
        result = FoundationTemplateService(session).create_template(
            template_type=template_type,
            payload=payload,
            actor=current_user.username,
        )
        _commit_template_success(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            result=result,
        )
        return JSONResponse(status_code=201, content=_ok(result.item.model_dump()))
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=None,
            resource_no=payload.template_code,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=None,
            resource_no=payload.template_code,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


def _update_foundation_template(
    *,
    request: Request,
    template_type: str,
    template_id: int,
    payload: FoundationTemplateUpdateRequest,
    current_user: CurrentUser,
    session: Session,
):
    action = BOM_TEMPLATE_UPDATE_ACTION
    _require_template_action(
        session=session,
        request=request,
        current_user=current_user,
        action=BOM_UPDATE,
        template_type=template_type,
        resource_id=template_id,
    )
    try:
        result = FoundationTemplateService(session).update_template(
            template_type=template_type,
            template_id=template_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_template_success(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            result=result,
        )
        return _ok(result.item.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=template_id,
            resource_no=payload.template_code,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=template_id,
            resource_no=payload.template_code,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


def _deactivate_foundation_template(
    *,
    request: Request,
    template_type: str,
    template_id: int,
    payload: FoundationTemplateDeactivateRequest,
    current_user: CurrentUser,
    session: Session,
):
    action = BOM_TEMPLATE_DEACTIVATE_ACTION
    _require_template_action(
        session=session,
        request=request,
        current_user=current_user,
        action=BOM_DEACTIVATE,
        template_type=template_type,
        resource_id=template_id,
    )
    try:
        result = FoundationTemplateService(session).deactivate_template(
            template_type=template_type,
            template_id=template_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_template_success(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            result=result,
        )
        return _ok(result.item.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=template_id,
            resource_no=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=template_id,
            resource_no=None,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


def _create_foundation_template_node(
    *,
    request: Request,
    template_type: str,
    template_id: int,
    payload: FoundationTemplateNodeCreateRequest,
    current_user: CurrentUser,
    session: Session,
):
    action = BOM_TEMPLATE_NODE_CREATE_ACTION
    _require_template_action(
        session=session,
        request=request,
        current_user=current_user,
        action=BOM_UPDATE,
        template_type=template_type,
        resource_id=template_id,
    )
    try:
        result = FoundationTemplateService(session).create_node(
            template_type=template_type,
            template_id=template_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_template_success(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            result=result,
        )
        return JSONResponse(status_code=201, content=_ok(result.item.model_dump()))
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=template_id,
            resource_no=payload.code,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=template_id,
            resource_no=payload.code,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


def _update_foundation_template_node(
    *,
    request: Request,
    template_type: str,
    template_id: int,
    node_id: int,
    payload: FoundationTemplateNodeUpdateRequest,
    current_user: CurrentUser,
    session: Session,
):
    action = BOM_TEMPLATE_NODE_UPDATE_ACTION
    _require_template_action(
        session=session,
        request=request,
        current_user=current_user,
        action=BOM_UPDATE,
        template_type=template_type,
        resource_id=template_id,
    )
    try:
        result = FoundationTemplateService(session).update_node(
            template_type=template_type,
            template_id=template_id,
            node_id=node_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_template_success(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            result=result,
        )
        return _ok(result.item.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=node_id,
            resource_no=payload.code,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=node_id,
            resource_no=payload.code,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


def _deactivate_foundation_template_node(
    *,
    request: Request,
    template_type: str,
    template_id: int,
    node_id: int,
    payload: FoundationTemplateNodeDeactivateRequest,
    current_user: CurrentUser,
    session: Session,
):
    action = BOM_TEMPLATE_NODE_DEACTIVATE_ACTION
    _require_template_action(
        session=session,
        request=request,
        current_user=current_user,
        action=BOM_DEACTIVATE,
        template_type=template_type,
        resource_id=template_id,
    )
    try:
        result = FoundationTemplateService(session).deactivate_node(
            template_type=template_type,
            template_id=template_id,
            node_id=node_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_template_success(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            result=result,
        )
        return _ok(result.item.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=node_id,
            resource_no=None,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _record_template_failure(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            template_type=template_type,
            resource_id=node_id,
            resource_no=None,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.get("/process-requirement-templates")
def list_process_requirement_templates(
    request: Request,
    company: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _list_foundation_templates(
        request=request,
        template_type="workmanship",
        company=company,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
        current_user=current_user,
        session=session,
    )


@router.post("/process-requirement-templates")
def create_process_requirement_template(
    payload: FoundationTemplateCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _create_foundation_template(
        request=request,
        template_type="workmanship",
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.patch("/process-requirement-templates/{template_id}")
def update_process_requirement_template(
    template_id: int,
    payload: FoundationTemplateUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _update_foundation_template(
        request=request,
        template_type="workmanship",
        template_id=template_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.post("/process-requirement-templates/{template_id}/deactivate")
def deactivate_process_requirement_template(
    template_id: int,
    payload: FoundationTemplateDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _deactivate_foundation_template(
        request=request,
        template_type="workmanship",
        template_id=template_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.post("/process-requirement-templates/{template_id}/nodes")
def create_process_requirement_template_node(
    template_id: int,
    payload: FoundationTemplateNodeCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _create_foundation_template_node(
        request=request,
        template_type="workmanship",
        template_id=template_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.patch("/process-requirement-templates/{template_id}/nodes/{node_id}")
def update_process_requirement_template_node(
    template_id: int,
    node_id: int,
    payload: FoundationTemplateNodeUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _update_foundation_template_node(
        request=request,
        template_type="workmanship",
        template_id=template_id,
        node_id=node_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.post("/process-requirement-templates/{template_id}/nodes/{node_id}/deactivate")
def deactivate_process_requirement_template_node(
    template_id: int,
    node_id: int,
    payload: FoundationTemplateNodeDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _deactivate_foundation_template_node(
        request=request,
        template_type="workmanship",
        template_id=template_id,
        node_id=node_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.get("/size-chart-templates")
def list_size_chart_templates(
    request: Request,
    company: str | None = None,
    keyword: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _list_foundation_templates(
        request=request,
        template_type="size_spec",
        company=company,
        keyword=keyword,
        status=status,
        page=page,
        page_size=page_size,
        current_user=current_user,
        session=session,
    )


@router.post("/size-chart-templates")
def create_size_chart_template(
    payload: FoundationTemplateCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _create_foundation_template(
        request=request,
        template_type="size_spec",
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.patch("/size-chart-templates/{template_id}")
def update_size_chart_template(
    template_id: int,
    payload: FoundationTemplateUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _update_foundation_template(
        request=request,
        template_type="size_spec",
        template_id=template_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.post("/size-chart-templates/{template_id}/deactivate")
def deactivate_size_chart_template(
    template_id: int,
    payload: FoundationTemplateDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _deactivate_foundation_template(
        request=request,
        template_type="size_spec",
        template_id=template_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.post("/size-chart-templates/{template_id}/nodes")
def create_size_chart_template_node(
    template_id: int,
    payload: FoundationTemplateNodeCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _create_foundation_template_node(
        request=request,
        template_type="size_spec",
        template_id=template_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.patch("/size-chart-templates/{template_id}/nodes/{node_id}")
def update_size_chart_template_node(
    template_id: int,
    node_id: int,
    payload: FoundationTemplateNodeUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _update_foundation_template_node(
        request=request,
        template_type="size_spec",
        template_id=template_id,
        node_id=node_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.post("/size-chart-templates/{template_id}/nodes/{node_id}/deactivate")
def deactivate_size_chart_template_node(
    template_id: int,
    node_id: int,
    payload: FoundationTemplateNodeDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    return _deactivate_foundation_template_node(
        request=request,
        template_type="size_spec",
        template_id=template_id,
        node_id=node_id,
        payload=payload,
        current_user=current_user,
        session=session,
    )


@router.get("/style-bom-process")
@router.get("/processing-types")
def list_bom_processing_types(
    request: Request,
    item_code: str | None = None,
    process_type_name: str | None = None,
    process_name: str | None = None,
    subcontract_mode: str | None = None,
    pricing_mode: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料加工类型（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomProcessingTypeQuery(
        item_code=item_code,
        process_type_name=process_type_name,
        process_name=process_name,
        subcontract_mode=subcontract_mode,
        pricing_mode=pricing_mode,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomProcessingTypeData = service.list_processing_types(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/material-processing")
def list_bom_material_processing(
    request: Request,
    item_code: str | None = None,
    process_no: str | None = None,
    process_name: str | None = None,
    processing_supplier: str | None = None,
    processing_mode: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料加工（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomMaterialProcessingQuery(
        item_code=item_code,
        process_no=process_no,
        process_name=process_name,
        processing_supplier=processing_supplier,
        processing_mode=processing_mode,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomMaterialProcessingData = service.list_material_processing(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/material-processing-inbound")
def list_bom_material_processing_inbound(
    request: Request,
    item_code: str | None = None,
    inbound_no: str | None = None,
    material_item_code: str | None = None,
    processing_supplier: str | None = None,
    warehouse_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料加工入仓（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomMaterialProcessingInboundQuery(
        item_code=item_code,
        inbound_no=inbound_no,
        material_item_code=material_item_code,
        processing_supplier=processing_supplier,
        warehouse_name=warehouse_name,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomMaterialProcessingInboundData = service.list_material_processing_inbound(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/material-deduction")
def list_bom_material_deduction(
    request: Request,
    item_code: str | None = None,
    deduction_no: str | None = None,
    material_item_code: str | None = None,
    warehouse_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料扣仓（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomMaterialDeductionQuery(
        item_code=item_code,
        deduction_no=deduction_no,
        material_item_code=material_item_code,
        warehouse_name=warehouse_name,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomMaterialDeductionData = service.list_material_deduction(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/material-sales-outbound")
def list_bom_material_sales_outbound(
    request: Request,
    item_code: str | None = None,
    outbound_no: str | None = None,
    sales_order_no: str | None = None,
    customer_name: str | None = None,
    warehouse_name: str | None = None,
    material_item_code: str | None = None,
    status: str | None = None,
    audit_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料销售出仓（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomMaterialSalesOutboundQuery(
        item_code=item_code,
        outbound_no=outbound_no,
        sales_order_no=sales_order_no,
        customer_name=customer_name,
        warehouse_name=warehouse_name,
        material_item_code=material_item_code,
        status=status,
        audit_status=audit_status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomMaterialSalesOutboundData = service.list_material_sales_outbound(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/material-categories")
@router.get("/materials")
@router.get("/material-types")
def list_bom_material_types(
    request: Request,
    item_code: str | None = None,
    material_item_code: str | None = None,
    material_type_name: str | None = None,
    material_group: str | None = None,
    applicable_scene: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料类型（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomMaterialTypeQuery(
        item_code=item_code,
        material_item_code=material_item_code,
        material_type_name=material_type_name,
        material_group=material_group,
        applicable_scene=applicable_scene,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomMaterialTypeData = service.list_material_types(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/units")
@router.get("/material-units")
def list_bom_material_units(
    request: Request,
    item_code: str | None = None,
    material_item_code: str | None = None,
    unit_name: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """查询 BOM 物料单位（只读语义）。"""
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
    )
    allowed_item_codes = permission_service.get_readable_item_codes(
        current_user=current_user,
        request_obj=request,
        module="bom",
        action_context=BOM_READ,
        resource_type="bom",
    )

    query = BomMaterialUnitQuery(
        item_code=item_code,
        material_item_code=material_item_code,
        unit_name=unit_name,
        status=status,
        page=page,
        page_size=page_size,
    )
    service = BomService(session=session)
    try:
        data: BomMaterialUnitData = service.list_material_units(
            query=query,
            allowed_item_codes=allowed_item_codes,
        )
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.get("/{bom_id}")
def get_bom_detail(
    bom_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """获取 BOM 详情。"""
    # 读权限动作：bom:read（含资源级校验）
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_READ,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )
    service = BomService(session=session)
    try:
        data: BomDetailData = service.get_bom_detail(bom_id=bom_id)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_READ, exc))


@router.put("/{bom_id}")
def update_bom_draft(
    bom_id: int,
    payload: BomUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """更新 BOM 草稿。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_UPDATE,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_UPDATE
    request_id = get_request_id_from_request(request)
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        snapshot_item_code, snapshot_bom_no = _snapshot_bom_carriers(before_data)
        if snapshot_item_code is None or snapshot_bom_no is None:
            _raise_bom_idempotency_conflict("业务载体缺失")
        if payload.item_code != snapshot_item_code:
            _raise_bom_idempotency_conflict("item_code 载体与业务载体不一致")
        if payload.bom_no != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        if payload.source_ref != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        _validate_local_bom_request_gate(
            request_obj=request,
            request_id=request_id,
            carriers=[payload.idempotency_key, payload.source_ref, payload.scenario_tag, payload.bom_no],
            expected_item_code=snapshot_item_code,
            expected_bom_ref=snapshot_bom_no,
            expected_reason=None,
        )
        data: BomUpdateData = service.update_bom_draft(
            bom_id=bom_id,
            payload=payload,
            operator=current_user.username,
        )
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        if _is_local_bom_gate_failure(exc):
            return _app_err(exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/set-default")
def set_default_bom(
    bom_id: int,
    payload: BomCarrierRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """设置默认 BOM。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_SET_DEFAULT,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_SET_DEFAULT
    request_id = get_request_id_from_request(request)
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        snapshot_item_code, snapshot_bom_no = _snapshot_bom_carriers(before_data)
        if snapshot_item_code is None or snapshot_bom_no is None:
            _raise_bom_idempotency_conflict("业务载体缺失")
        if payload.item_code != snapshot_item_code:
            _raise_bom_idempotency_conflict("item_code 载体与业务载体不一致")
        if payload.bom_no != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        if payload.source_ref != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        _validate_local_bom_request_gate(
            request_obj=request,
            request_id=request_id,
            carriers=[payload.idempotency_key, payload.source_ref, payload.scenario_tag, payload.bom_no],
            expected_item_code=snapshot_item_code,
            expected_bom_ref=snapshot_bom_no,
            expected_reason=None,
        )
        data: BomSetDefaultData = service.set_default(bom_id=bom_id, operator=current_user.username)
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        if _is_local_bom_gate_failure(exc):
            return _app_err(exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/activate")
def activate_bom(
    bom_id: int,
    payload: BomCarrierRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """发布 BOM。"""
    permission_service = PermissionService(session=session)
    _require_any_action(
        permission_service=permission_service,
        current_user=current_user,
        request_obj=request,
        actions=(BOM_ACTIVATE_ACTION, BOM_PUBLISH),
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_ACTIVATE_ACTION
    request_id = get_request_id_from_request(request)
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        snapshot_item_code, snapshot_bom_no = _snapshot_bom_carriers(before_data)
        if snapshot_item_code is None or snapshot_bom_no is None:
            _raise_bom_idempotency_conflict("业务载体缺失")
        if payload.item_code != snapshot_item_code:
            _raise_bom_idempotency_conflict("item_code 载体与业务载体不一致")
        if payload.bom_no != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        if payload.source_ref != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        _validate_local_bom_request_gate(
            request_obj=request,
            request_id=request_id,
            carriers=[payload.idempotency_key, payload.source_ref, payload.scenario_tag, payload.bom_no],
            expected_item_code=snapshot_item_code,
            expected_bom_ref=snapshot_bom_no,
            expected_reason=None,
        )
        data: BomActivateData = service.activate(bom_id=bom_id, operator=current_user.username)
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        if _is_local_bom_gate_failure(exc):
            return _app_err(exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/deactivate")
def deactivate_bom(
    bom_id: int,
    payload: BomDeactivateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """停用 BOM。"""
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=BOM_DEACTIVATE,
        module="bom",
        resource_type="bom",
        resource_id=bom_id,
    )

    service = BomService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    action = BOM_DEACTIVATE
    request_id = get_request_id_from_request(request)
    before_data = None
    after_data = None

    try:
        before_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        snapshot_item_code, snapshot_bom_no = _snapshot_bom_carriers(before_data)
        if snapshot_item_code is None or snapshot_bom_no is None:
            _raise_bom_idempotency_conflict("业务载体缺失")
        if payload.item_code != snapshot_item_code:
            _raise_bom_idempotency_conflict("item_code 载体与业务载体不一致")
        if payload.bom_no != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        if payload.source_ref != snapshot_bom_no:
            _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
        _validate_local_bom_request_gate(
            request_obj=request,
            request_id=request_id,
            carriers=[payload.idempotency_key, payload.source_ref, payload.scenario_tag, payload.bom_no, payload.reason],
            expected_item_code=snapshot_item_code,
            expected_bom_ref=snapshot_bom_no,
            expected_reason=payload.reason,
        )
        data: BomDeactivateData = service.deactivate(
            bom_id=bom_id,
            reason=payload.reason,
            operator=current_user.username,
        )
        after_data = audit.snapshot_resource(resource_type="bom", resource_id=bom_id)
        audit.record_success(
            module="bom",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="bom",
            resource_id=bom_id,
            resource_no=_resource_no(after_data) or _resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            context=context,
        )
        _commit_or_raise_write_error(session=session, request=request, action=action)
        return _ok(data.model_dump())
    except AuditWriteFailed as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        return _app_err(exc)
    except AppException as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        if _is_local_bom_gate_failure(exc):
            return _app_err(exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=exc.code,
        )
        return _app_err(exc)
    except Exception as exc:
        _rollback_safely(session=session, request=request, action=action, origin=exc)
        _record_failure_safely(
            session=session,
            audit=audit,
            context=context,
            request=request,
            action=action,
            current_user=current_user,
            resource_id=bom_id,
            resource_no=_resource_no(before_data),
            before_data=before_data,
            after_data=after_data,
            error_code=BOM_INTERNAL_ERROR,
        )
        return _app_err(_unknown_to_internal_error(request, action, exc))


@router.post("/{bom_id}/explode")
def explode_bom(
    bom_id: int,
    payload: BomExplodeRequest,
    request: Request,
    _permission: None = Depends(_require_bom_explode_permission),
    session: Session = Depends(get_db_session),
):
    """展开 BOM。"""
    service = BomService(session=session)
    request_id = get_request_id_from_request(request)
    try:
        detail = service.get_bom_detail(bom_id=bom_id)
        request_has_local_gate = _match_bom_scenario_tag(request_id) is not None
        if _is_local_bom_write_enabled() and request_has_local_gate:
            snapshot_item_code = _scope_text(detail.bom.item_code)
            snapshot_bom_no = _scope_text(detail.bom.bom_no)
            if snapshot_item_code is None or snapshot_bom_no is None:
                _raise_bom_idempotency_conflict("业务载体缺失")
            if payload.item_code != snapshot_item_code:
                _raise_bom_idempotency_conflict("item_code 载体与业务载体不一致")
            if payload.bom_no != snapshot_bom_no:
                _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
            if payload.source_ref != snapshot_bom_no:
                _raise_bom_idempotency_conflict("bom_no_or_source_ref 载体与业务载体不一致")
            _validate_local_bom_request_gate(
                request_obj=request,
                request_id=request_id,
                carriers=[payload.idempotency_key, payload.source_ref, payload.scenario_tag, payload.bom_no],
                expected_item_code=snapshot_item_code,
                expected_bom_ref=snapshot_bom_no,
                expected_reason=None,
            )
        data: BomExplodeData = service.explode(bom_id=bom_id, payload=payload)
        return _ok(data.model_dump())
    except AppException as exc:
        return _app_err(exc)
    except Exception as exc:
        return _app_err(_unknown_to_internal_error(request, BOM_EXPLODE_ACTION, exc))
