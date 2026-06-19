"""FastAPI-native sample workflow routes for existing sample pages."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import INTERNAL_ERROR
from app.core.error_codes import message_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.permissions import SAMPLE_MANAGE
from app.core.permissions import SAMPLE_READ
from app.schemas.sample import SampleOrderConvertRequest
from app.schemas.sample import SampleOrderCreateRequest
from app.schemas.sample import SampleOrderStatusRequest
from app.schemas.sample import SampleOrderUpdateRequest
from app.schemas.sample import SampleCostUpsertRequest
from app.schemas.sample import SampleMaterialBomCopyRequest
from app.schemas.sample import SampleMaterialBomExplodeRequest
from app.schemas.sample import SampleMaterialBomUpsertRequest
from app.schemas.sample import SampleTrackingActionRequest
from app.schemas.sample import SampleTrackingEventCreateRequest
from app.schemas.sample import SampleTrackingNodeCreateRequest
from app.schemas.sample import SampleTrackingNodeUpdateRequest
from app.schemas.sample import SampleTrackingTemplateCreateRequest
from app.schemas.sample import SampleTrackingTemplateUpdateRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService
from app.services.sample_service import SampleMutationResult
from app.services.sample_service import SampleService

router = APIRouter(prefix="/api/sample", tags=["sample"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": jsonable_encoder(data)}


def _created(data: Any) -> JSONResponse:
    return JSONResponse(status_code=201, content=_ok(data))


def _err(exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code, "message": exc.message, "data": None})


def _require_action(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: int | None = None,
) -> None:
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sample",
        resource_type=resource_type,
        resource_id=resource_id,
    )


def _commit_success(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    result: SampleMutationResult,
) -> None:
    AuditService(session).record_success(
        module="sample",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=result.resource_type,
        resource_id=result.resource_id,
        resource_no=result.resource_no,
        before_data=result.before,
        after_data=result.after,
        context=AuditContext.from_request(request),
    )
    session.commit()


def _record_failure_and_commit(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: int | None,
    resource_no: str | None,
    error_code: str,
) -> None:
    try:
        session.rollback()
    except Exception:
        pass
    AuditService(session).record_failure(
        module="sample",
        action=action,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=None,
        after_data=None,
        error_code=error_code,
        context=AuditContext.from_request(request),
    )
    session.commit()


def _handle_internal_error(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_id: int | None,
    resource_no: str | None,
    exc: Exception,
) -> None:
    error = BusinessException(code=INTERNAL_ERROR, message=message_of(INTERNAL_ERROR))
    _record_failure_and_commit(
        session=session,
        request=request,
        current_user=current_user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        resource_no=resource_no,
        error_code=error.code,
    )
    raise HTTPException(status_code=error.status_code, detail={"code": error.code, "message": error.message, "data": None}) from exc


@router.get("/orders")
def list_sample_orders(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_READ,
        resource_type="SAMPLE_ORDER",
    )
    try:
        data = SampleService(session).list_orders(
            company=company,
            keyword=keyword,
            status=status,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.get("/orders/{order_id}/tracking-events")
def list_sample_order_tracking_events(
    order_id: int,
    request: Request,
    company: str = Query(default="默认公司"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_READ,
        resource_type="SAMPLE_ORDER",
        resource_id=order_id,
    )
    try:
        data = SampleService(session).list_order_tracking_events(
            order_id=order_id,
            company=company,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/orders")
def create_sample_order(
    payload: SampleOrderCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = "create"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_ORDER",
    )
    try:
        result = SampleService(session).create_order(payload=payload, actor=current_user.username)
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_ORDER",
            resource_id=None,
            resource_no=payload.sample_no,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_ORDER",
            resource_id=None,
            resource_no=payload.sample_no,
            exc=exc,
        )
    return _created(result.item)


@router.post("/orders/{order_id}/tracking-events")
def create_sample_order_tracking_event(
    order_id: int,
    payload: SampleTrackingEventCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = "create_tracking_event"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_ORDER",
        resource_id=order_id,
    )
    try:
        result = SampleService(session).create_order_tracking_event(
            order_id=order_id,
            payload=payload,
            actor=current_user.username,
        )
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_EVENT",
            resource_id=order_id,
            resource_no=None,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_EVENT",
            resource_id=order_id,
            resource_no=None,
            exc=exc,
        )
    return _created(result.item)


@router.get("/orders/{order_id}/material-bom")
def get_sample_material_bom(
    order_id: int,
    request: Request,
    company: str = Query(default="默认公司"),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_READ,
        resource_type="SAMPLE_MATERIAL_BOM",
        resource_id=order_id,
    )
    try:
        data = SampleService(session).get_material_bom(order_id=order_id, company=company)
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/orders/{order_id}/material-bom/copy-from-style")
def copy_sample_material_bom_from_style(
    order_id: int,
    payload: SampleMaterialBomCopyRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_material_bom(
        order_id=order_id,
        request=request,
        current_user=current_user,
        session=session,
        action="copy_material_bom_from_style",
        mutate=lambda service: service.copy_material_bom_from_style(
            order_id=order_id,
            payload=payload,
            actor=current_user.username,
        ),
    )
    return _ok(result.item)


@router.put("/orders/{order_id}/material-bom")
def upsert_sample_material_bom(
    order_id: int,
    payload: SampleMaterialBomUpsertRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_material_bom(
        order_id=order_id,
        request=request,
        current_user=current_user,
        session=session,
        action="upsert_material_bom",
        mutate=lambda service: service.upsert_material_bom(
            order_id=order_id,
            payload=payload,
            actor=current_user.username,
        ),
    )
    return _ok(result.item)


@router.post("/orders/{order_id}/material-bom/explode")
def explode_sample_material_bom(
    order_id: int,
    payload: SampleMaterialBomExplodeRequest,
    request: Request,
    company: str = Query(default="默认公司"),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_READ,
        resource_type="SAMPLE_MATERIAL_BOM",
        resource_id=order_id,
    )
    try:
        data = SampleService(session).explode_material_bom(
            order_id=order_id,
            company=company,
            order_qty=payload.order_qty,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.get("/orders/{order_id}/costs")
def get_sample_costs(
    order_id: int,
    request: Request,
    company: str = Query(default="默认公司"),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_READ,
        resource_type="SAMPLE_COST",
        resource_id=order_id,
    )
    try:
        data = SampleService(session).get_costs(order_id=order_id, company=company)
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.put("/orders/{order_id}/costs")
def upsert_sample_costs(
    order_id: int,
    payload: SampleCostUpsertRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_sample_costs(
        order_id=order_id,
        request=request,
        current_user=current_user,
        session=session,
        action="upsert_costs",
        mutate=lambda service: service.upsert_costs(
            order_id=order_id,
            payload=payload,
            actor=current_user.username,
        ),
    )
    return _ok(result.item)


@router.patch("/orders/{order_id}")
def update_sample_order(
    order_id: int,
    payload: SampleOrderUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_order(
        order_id=order_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="update",
        mutate=lambda service: service.update_order(order_id=order_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/orders/{order_id}/submit")
def submit_sample_order(
    order_id: int,
    payload: SampleOrderStatusRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_order(
        order_id=order_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="submit",
        mutate=lambda service: service.submit_order(order_id=order_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/orders/{order_id}/reverse")
def reverse_sample_order(
    order_id: int,
    payload: SampleOrderStatusRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_order(
        order_id=order_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="reverse",
        mutate=lambda service: service.reverse_order(order_id=order_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/orders/{order_id}/start-patterning")
def start_sample_order_patterning(
    order_id: int,
    payload: SampleOrderStatusRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_order(
        order_id=order_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="start_patterning",
        mutate=lambda service: service.start_patterning_order(order_id=order_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/orders/{order_id}/start-fitting")
def start_sample_order_fitting(
    order_id: int,
    payload: SampleOrderStatusRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_order(
        order_id=order_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="start_fitting",
        mutate=lambda service: service.start_fitting_order(order_id=order_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/orders/{order_id}/seal")
def seal_sample_order(
    order_id: int,
    payload: SampleOrderStatusRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_order(
        order_id=order_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="seal",
        mutate=lambda service: service.seal_order(order_id=order_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/orders/{order_id}/convert-to-bulk")
def convert_sample_order_to_bulk(
    order_id: int,
    payload: SampleOrderConvertRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_order(
        order_id=order_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="convert",
        mutate=lambda service: service.convert_order(order_id=order_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


def _mutate_order(
    *,
    order_id: int,
    payload: Any,
    request: Request,
    current_user: CurrentUser,
    session: Session,
    action: str,
    mutate: Any,
) -> SampleMutationResult:
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_ORDER",
        resource_id=order_id,
    )
    try:
        result = mutate(SampleService(session))
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_ORDER",
            resource_id=order_id,
            resource_no=None,
            error_code=exc.code,
        )
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_ORDER",
            resource_id=order_id,
            resource_no=None,
            exc=exc,
        )
    return result


def _mutate_material_bom(
    *,
    order_id: int,
    request: Request,
    current_user: CurrentUser,
    session: Session,
    action: str,
    mutate: Any,
) -> SampleMutationResult:
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_MATERIAL_BOM",
        resource_id=order_id,
    )
    try:
        result = mutate(SampleService(session))
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_MATERIAL_BOM",
            resource_id=order_id,
            resource_no=None,
            error_code=exc.code,
        )
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_MATERIAL_BOM",
            resource_id=order_id,
            resource_no=None,
            exc=exc,
        )
    return result


def _mutate_sample_costs(
    *,
    order_id: int,
    request: Request,
    current_user: CurrentUser,
    session: Session,
    action: str,
    mutate: Any,
) -> SampleMutationResult:
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_COST",
        resource_id=order_id,
    )
    try:
        result = mutate(SampleService(session))
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_COST",
            resource_id=order_id,
            resource_no=None,
            error_code=exc.code,
        )
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_COST",
            resource_id=order_id,
            resource_no=None,
            exc=exc,
        )
    return result


@router.get("/tracking-templates")
def list_tracking_templates(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_READ,
        resource_type="SAMPLE_TRACKING_TEMPLATE",
    )
    try:
        data = SampleService(session).list_templates(
            company=company,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/tracking-templates")
def create_tracking_template(
    payload: SampleTrackingTemplateCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = "create"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_TRACKING_TEMPLATE",
    )
    try:
        result = SampleService(session).create_template(payload=payload, actor=current_user.username)
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_TEMPLATE",
            resource_id=None,
            resource_no=payload.template_code,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_TEMPLATE",
            resource_id=None,
            resource_no=payload.template_code,
            exc=exc,
        )
    return _created(result.item)


@router.patch("/tracking-templates/{template_id}")
def update_tracking_template(
    template_id: int,
    payload: SampleTrackingTemplateUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_template(
        template_id=template_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="update",
        mutate=lambda service: service.update_template(template_id=template_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/tracking-templates/{template_id}/deactivate")
def deactivate_tracking_template(
    template_id: int,
    payload: SampleTrackingActionRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_template(
        template_id=template_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="deactivate",
        mutate=lambda service: service.deactivate_template(template_id=template_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


def _mutate_template(
    *,
    template_id: int,
    payload: Any,
    request: Request,
    current_user: CurrentUser,
    session: Session,
    action: str,
    mutate: Any,
) -> SampleMutationResult:
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_TRACKING_TEMPLATE",
        resource_id=template_id,
    )
    try:
        result = mutate(SampleService(session))
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_TEMPLATE",
            resource_id=template_id,
            resource_no=None,
            error_code=exc.code,
        )
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_TEMPLATE",
            resource_id=template_id,
            resource_no=None,
            exc=exc,
        )
    return result


@router.post("/tracking-templates/{template_id}/nodes")
def create_tracking_node(
    template_id: int,
    payload: SampleTrackingNodeCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = "create_node"
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_TRACKING_TEMPLATE",
        resource_id=template_id,
    )
    try:
        result = SampleService(session).create_node(template_id=template_id, payload=payload, actor=current_user.username)
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_NODE",
            resource_id=template_id,
            resource_no=None,
            error_code=exc.code,
        )
        return _err(exc)
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_NODE",
            resource_id=template_id,
            resource_no=None,
            exc=exc,
        )
    return _created(result.item)


@router.patch("/tracking-templates/{template_id}/nodes/{node_id}")
def update_tracking_node(
    template_id: int,
    node_id: int,
    payload: SampleTrackingNodeUpdateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_node(
        template_id=template_id,
        node_id=node_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="update_node",
        mutate=lambda service: service.update_node(template_id=template_id, node_id=node_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


@router.post("/tracking-templates/{template_id}/nodes/{node_id}/delete")
def delete_tracking_node(
    template_id: int,
    node_id: int,
    payload: SampleTrackingActionRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    result = _mutate_node(
        template_id=template_id,
        node_id=node_id,
        payload=payload,
        request=request,
        current_user=current_user,
        session=session,
        action="delete_node",
        mutate=lambda service: service.delete_node(template_id=template_id, node_id=node_id, payload=payload, actor=current_user.username),
    )
    return _ok(result.item)


def _mutate_node(
    *,
    template_id: int,
    node_id: int,
    payload: Any,
    request: Request,
    current_user: CurrentUser,
    session: Session,
    action: str,
    mutate: Any,
) -> SampleMutationResult:
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=SAMPLE_MANAGE,
        resource_type="SAMPLE_TRACKING_NODE",
        resource_id=node_id,
    )
    try:
        result = mutate(SampleService(session))
        _commit_success(session=session, request=request, current_user=current_user, action=action, result=result)
    except AuditWriteFailed as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except AppException as exc:
        _record_failure_and_commit(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_NODE",
            resource_id=node_id,
            resource_no=str(template_id),
            error_code=exc.code,
        )
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message, "data": None}) from exc
    except Exception as exc:
        _handle_internal_error(
            session=session,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SAMPLE_TRACKING_NODE",
            resource_id=node_id,
            resource_no=str(template_id),
            exc=exc,
        )
    return result
