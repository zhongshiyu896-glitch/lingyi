"""FastAPI-native material purchase routes for existing purchase pages."""

from __future__ import annotations

from collections.abc import Generator
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
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.permissions import MATERIAL_PURCHASE_READ
from app.core.permissions import MATERIAL_PURCHASE_WRITE
from app.schemas.material_purchase import MaterialPurchaseInvoiceCreateRequest
from app.schemas.material_purchase import MaterialPurchaseOrderCancelRequest
from app.schemas.material_purchase import MaterialPurchaseOrderCreateRequest
from app.schemas.material_purchase import MaterialPurchasePaymentCancelRequest
from app.schemas.material_purchase import MaterialPurchasePaymentCreateRequest
from app.schemas.material_purchase import MaterialPurchaseRequirementToOrderRequest
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.material_purchase_service import PurchaseRequirementOrderMutationResult
from app.services.material_purchase_service import PurchaseOrderCancelMutationResult
from app.services.material_purchase_service import MaterialPurchaseService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/material-purchase", tags=["material_purchase"])


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
        module="material_purchase",
        resource_type=resource_type,
        resource_id=resource_id,
    )


def _material_purchase_scope_filters(permissions) -> dict[str, set[str] | None]:
    if permissions is None or permissions.unrestricted:
        return {
            "allowed_companies": None,
            "allowed_materials": None,
            "allowed_suppliers": None,
            "allowed_warehouses": None,
        }
    return {
        "allowed_companies": set(permissions.allowed_companies),
        "allowed_materials": set(permissions.allowed_items),
        "allowed_suppliers": set(permissions.allowed_suppliers),
        "allowed_warehouses": set(permissions.allowed_warehouses),
    }


def _requirement_scope_filters(permissions) -> dict[str, set[str] | None]:
    return _material_purchase_scope_filters(permissions)


def _ensure_requirement_resource_scope(
    *,
    service: MaterialPurchaseService,
    permission_service: PermissionService,
    request: Request,
    current_user: CurrentUser,
    payload: MaterialPurchaseRequirementToOrderRequest,
) -> None:
    requirements = service.get_requirements_for_permission(
        company=payload.company,
        requirement_ids=[int(row_id) for row_id in payload.requirement_ids],
    )
    user_permissions = permission_service.get_resource_scope_permissions(
        current_user=current_user,
        request_obj=request,
        module="material_purchase",
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_REQUIREMENT",
    )
    for requirement in requirements:
        supplier_name = payload.supplier_name or requirement.supplier_name
        permission_service.ensure_resource_scope_permission(
            current_user=current_user,
            request_obj=request,
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            resource_scope={
                "company": requirement.company,
                "item_code": requirement.material_item_code,
                "supplier": supplier_name,
                "warehouse": requirement.warehouse,
            },
            required_fields=("company", "item_code", "warehouse"),
            resource_type="MATERIAL_PURCHASE_REQUIREMENT",
            resource_id=int(requirement.id),
            resource_no=str(requirement.requirement_no),
            enforce_action=False,
            user_permissions=user_permissions,
        )


@router.get("/orders")
def list_material_purchase_orders(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    supplier_name: str | None = Query(default=None),
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
        action=MATERIAL_PURCHASE_READ,
        resource_type="MATERIAL_PURCHASE_ORDER",
    )
    permission_service = PermissionService(session=session)
    permissions = permission_service.get_resource_scope_permissions(
        current_user=current_user,
        request_obj=request,
        module="material_purchase",
        action=MATERIAL_PURCHASE_READ,
        resource_type="MATERIAL_PURCHASE_ORDER",
    )
    try:
        data = MaterialPurchaseService(session).list_orders(
            company=company,
            keyword=keyword,
            supplier_name=supplier_name,
            status=status,
            page=page,
            page_size=page_size,
            **_material_purchase_scope_filters(permissions),
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.get("/requirements")
def list_material_purchase_requirements(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    material_item_code: str | None = Query(default=None),
    supplier_name: str | None = Query(default=None),
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
        action=MATERIAL_PURCHASE_READ,
        resource_type="MATERIAL_PURCHASE_REQUIREMENT",
    )
    permission_service = PermissionService(session=session)
    permissions = permission_service.get_resource_scope_permissions(
        current_user=current_user,
        request_obj=request,
        module="material_purchase",
        action=MATERIAL_PURCHASE_READ,
        resource_type="MATERIAL_PURCHASE_REQUIREMENT",
    )
    try:
        data = MaterialPurchaseService(session).list_requirements(
            company=company,
            keyword=keyword,
            material_item_code=material_item_code,
            supplier_name=supplier_name,
            status=status,
            page=page,
            page_size=page_size,
            **_requirement_scope_filters(permissions),
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/orders")
def create_material_purchase_order(
    payload: MaterialPurchaseOrderCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_ORDER",
    )
    audit = AuditService(session)
    try:
        result = MaterialPurchaseService(session).create_order(payload=payload, actor=current_user.username)
        audit.record_success(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=None,
            resource_no=payload.purchase_no,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _created(result.item)


@router.post("/orders/from-requirements")
def create_material_purchase_order_from_requirements(
    payload: MaterialPurchaseRequirementToOrderRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_REQUIREMENT",
    )
    audit = AuditService(session)
    service = MaterialPurchaseService(session)
    try:
        _ensure_requirement_resource_scope(
            service=service,
            permission_service=PermissionService(session=session),
            request=request,
            current_user=current_user,
            payload=payload,
        )
        result: PurchaseRequirementOrderMutationResult = service.create_order_from_requirements(
            payload=payload,
            actor=current_user.username,
        )
        audit.record_success(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except HTTPException:
        session.rollback()
        raise
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=None,
            resource_no=payload.purchase_no,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _created(result.item)


@router.post("/orders/{order_id}/cancel")
def cancel_material_purchase_order(
    order_id: int,
    payload: MaterialPurchaseOrderCancelRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_ORDER",
        resource_id=order_id,
    )
    audit = AuditService(session)
    try:
        result: PurchaseOrderCancelMutationResult = MaterialPurchaseService(session).cancel_order(
            order_id=order_id,
            payload=payload,
            actor=current_user.username,
        )
        audit.record_success(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_ORDER",
            resource_id=order_id,
            resource_no=str(order_id),
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _ok(result.item)


@router.get("/purchase-invoices")
def list_purchase_invoices(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    supplier_name: str | None = Query(default=None),
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
        action=MATERIAL_PURCHASE_READ,
        resource_type="MATERIAL_PURCHASE_INVOICE",
    )
    try:
        data = MaterialPurchaseService(session).list_purchase_invoices(
            company=company,
            keyword=keyword,
            supplier_name=supplier_name,
            status=status,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/purchase-invoices")
def create_purchase_invoice(
    payload: MaterialPurchaseInvoiceCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_INVOICE",
    )
    audit = AuditService(session)
    try:
        result = MaterialPurchaseService(session).create_purchase_invoice(payload=payload, actor=current_user.username)
        audit.record_success(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_INVOICE",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_INVOICE",
            resource_id=None,
            resource_no=payload.purchase_invoice or payload.purchase_no,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _created(result.item)


@router.get("/purchase-payments")
def list_purchase_payments(
    request: Request,
    company: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    supplier_name: str | None = Query(default=None),
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
        action=MATERIAL_PURCHASE_READ,
        resource_type="MATERIAL_PURCHASE_PAYMENT",
    )
    try:
        data = MaterialPurchaseService(session).list_purchase_payments(
            company=company,
            keyword=keyword,
            supplier_name=supplier_name,
            status=status,
            page=page,
            page_size=page_size,
        )
    except AppException as exc:
        return _err(exc)
    return _ok(data)


@router.post("/purchase-payments")
def create_purchase_payment(
    payload: MaterialPurchasePaymentCreateRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_PAYMENT",
    )
    audit = AuditService(session)
    try:
        result = MaterialPurchaseService(session).create_purchase_payment(payload=payload, actor=current_user.username)
        audit.record_success(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_PAYMENT",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_PAYMENT",
            resource_id=None,
            resource_no=payload.payment_entry or payload.purchase_invoice,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _created(result.item)


@router.post("/purchase-payments/{payment_id}/cancel")
def cancel_purchase_payment(
    payment_id: int,
    payload: MaterialPurchasePaymentCancelRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_action(
        session=session,
        request=request,
        current_user=current_user,
        action=MATERIAL_PURCHASE_WRITE,
        resource_type="MATERIAL_PURCHASE_PAYMENT",
        resource_id=payment_id,
    )
    audit = AuditService(session)
    try:
        result = MaterialPurchaseService(session).cancel_purchase_payment(
            payment_id=payment_id,
            payload=payload,
            actor=current_user.username,
        )
        audit.record_success(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_PAYMENT",
            resource_id=result.resource_id,
            resource_no=result.resource_no,
            before_data=result.before,
            after_data=result.after,
            context=AuditContext.from_request(request),
        )
        session.commit()
    except AuditWriteFailed as exc:
        session.rollback()
        return _err(exc)
    except AppException as exc:
        session.rollback()
        audit.record_failure(
            module="material_purchase",
            action=MATERIAL_PURCHASE_WRITE,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="MATERIAL_PURCHASE_PAYMENT",
            resource_id=payment_id,
            resource_no=payload.purchase_invoice,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        return _err(exc)
    return _ok(result.item)
