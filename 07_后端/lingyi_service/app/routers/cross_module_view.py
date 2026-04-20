"""FastAPI router for cross-module read-only trail views (TASK-040C)."""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import ERPNEXT_RESOURCE_NOT_FOUND
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import RESOURCE_ACCESS_DENIED
from app.core.error_codes import message_of
from app.core.exceptions import AppException
from app.core.permissions import QUALITY_READ
from app.core.permissions import SALES_INVENTORY_READ
from app.core.permissions import get_permission_source
from app.schemas.cross_module_view import ApiResponse
from app.schemas.cross_module_view import CrossModuleQualityInspectionData
from app.schemas.cross_module_view import CrossModuleSalesOrderTrailData
from app.schemas.cross_module_view import CrossModuleSalesOrderTrailSummary
from app.schemas.cross_module_view import CrossModuleStockEntryData
from app.schemas.cross_module_view import CrossModuleWorkOrderTrailData
from app.schemas.cross_module_view import CrossModuleWorkOrderTrailSummary
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.permission_service import PermissionService
from app.services.cross_module_view_service import CrossModuleViewService

router = APIRouter(prefix="/api/cross-module", tags=["cross_module_view"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    payload = ApiResponse(code="0", message="success", data=data)
    return payload.model_dump(mode="json")


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _raise_hidden_not_found() -> None:
    raise HTTPException(
        status_code=404,
        detail={
            "code": ERPNEXT_RESOURCE_NOT_FOUND,
            "message": message_of(ERPNEXT_RESOURCE_NOT_FOUND),
            "data": None,
        },
    )


def _map_app_exception(exc: AppException) -> HTTPException:
    return HTTPException(
        status_code=int(exc.status_code),
        detail={"code": exc.code, "message": exc.message, "data": None},
    )


def _handle_erpnext_error(
    *,
    exc: ERPNextAdapterException,
    permission_service: PermissionService,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
    resource_no: str | None = None,
) -> None:
    permission_service._record_security_audit_safe(  # noqa: SLF001 - keep unified security audit baseline.
        event_type=EXTERNAL_SERVICE_UNAVAILABLE,
        module="sales_inventory",
        action=action,
        resource_type=resource_type,
        resource_id=None,
        resource_no=resource_no,
        user=current_user,
        deny_reason=exc.safe_message or "ERPNext 只读依赖不可用",
        request_obj=request,
        reason_code=exc.error_code,
    )
    raise HTTPException(status_code=int(exc.http_status or 503), detail=exc.to_http_detail()) from exc


def _scope_allowed(
    *,
    company: str | None,
    item_code: str | None,
    warehouse: str | None,
    permissions: UserPermissionResult | None,
) -> bool:
    if get_permission_source() != "erpnext" or permissions is None or permissions.unrestricted:
        return True

    normalized_company = _scope_text(company)
    normalized_item_code = _scope_text(item_code)
    normalized_warehouse = _scope_text(warehouse)

    if normalized_company and not ERPNextPermissionAdapter.is_company_permitted(
        company=normalized_company,
        user_permissions=permissions,
    ):
        return False
    if normalized_item_code and permissions.allowed_items and normalized_item_code not in permissions.allowed_items:
        return False
    if normalized_item_code and not permissions.allowed_items and (
        permissions.allowed_companies or permissions.allowed_warehouses or permissions.allowed_customers
    ):
        return False
    if normalized_warehouse and not ERPNextPermissionAdapter.is_warehouse_permitted(
        warehouse=normalized_warehouse,
        user_permissions=permissions,
    ):
        return False
    return True


def _sales_inventory_permissions(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    resource_type: str,
    resource_no: str | None = None,
) -> UserPermissionResult | None:
    return permission_service.get_sales_inventory_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=SALES_INVENTORY_READ,
        resource_type=resource_type,
        resource_id=None,
        resource_no=resource_no,
    )


def _ensure_scope_or_hidden_not_found(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    module: str,
    action: str,
    resource_scope: dict[str, Any],
    required_fields: tuple[str, ...],
    resource_type: str,
    resource_no: str | None,
    user_permissions: UserPermissionResult | None = None,
) -> None:
    try:
        permission_service.ensure_resource_scope_permission(
            current_user=current_user,
            request_obj=request,
            module=module,
            action=action,
            resource_scope=resource_scope,
            required_fields=required_fields,
            resource_type=resource_type,
            resource_no=resource_no,
            enforce_action=False,
            user_permissions=user_permissions,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == RESOURCE_ACCESS_DENIED:
            _raise_hidden_not_found()
        raise


def _build_work_order_summary(
    *,
    stock_entries: list[CrossModuleStockEntryData],
    quality_inspections: list[CrossModuleQualityInspectionData],
) -> CrossModuleWorkOrderTrailSummary:
    return CrossModuleWorkOrderTrailSummary(
        material_issue_qty=sum((abs(row.actual_qty) for row in stock_entries if row.actual_qty < 0), Decimal("0")),
        output_qty=sum((row.actual_qty for row in stock_entries if row.actual_qty > 0), Decimal("0")),
        accepted_qty=sum((row.accepted_qty for row in quality_inspections), Decimal("0")),
        rejected_qty=sum((row.rejected_qty for row in quality_inspections), Decimal("0")),
        defect_qty=sum((row.defect_qty for row in quality_inspections), Decimal("0")),
        stock_entry_count=len(stock_entries),
        quality_inspection_count=len(quality_inspections),
    )


def _build_sales_order_summary(
    *,
    ordered_qty: Decimal,
    delivery_notes: list[Any],
    quality_inspections: list[CrossModuleQualityInspectionData],
) -> CrossModuleSalesOrderTrailSummary:
    return CrossModuleSalesOrderTrailSummary(
        ordered_qty=ordered_qty,
        delivered_qty=sum((_decimal(row.delivered_qty) for row in delivery_notes), Decimal("0")),
        quality_inspection_count=len(quality_inspections),
        defect_qty=sum((row.defect_qty for row in quality_inspections), Decimal("0")),
    )


@router.get("/work-order-trail/{work_order_id}")
def get_work_order_trail(
    work_order_id: str,
    request: Request,
    company: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SALES_INVENTORY_READ,
        module="sales_inventory",
        resource_type="item",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=QUALITY_READ,
        module="quality",
        resource_type="quality_inspection",
    )
    sales_permissions = _sales_inventory_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="item",
        resource_no=work_order_id,
    )

    service = CrossModuleViewService(session=session, request_obj=request)
    try:
        data = service.get_work_order_trail(work_order_id=work_order_id, company=_scope_text(company))
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=SALES_INVENTORY_READ,
            resource_type="WorkOrder",
            resource_no=work_order_id,
        )
    except AppException as exc:
        raise _map_app_exception(exc) from exc

    if data is None:
        _raise_hidden_not_found()

    _ensure_scope_or_hidden_not_found(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        module="sales_inventory",
        action=SALES_INVENTORY_READ,
        resource_scope={
            "company": data.work_order.company,
            "item_code": data.work_order.production_item,
        },
        required_fields=("company",),
        resource_type="item",
        resource_no=work_order_id,
        user_permissions=sales_permissions,
    )
    _ensure_scope_or_hidden_not_found(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        module="quality",
        action=QUALITY_READ,
        resource_scope={
            "company": data.work_order.company,
            "item_code": data.work_order.production_item,
        },
        required_fields=("company", "item_code"),
        resource_type="quality_inspection",
        resource_no=work_order_id,
    )

    before_total = len(data.stock_entries) + len(data.quality_inspections)
    data.stock_entries = [
        row
        for row in data.stock_entries
        if _scope_allowed(
            company=row.company,
            item_code=row.item_code,
            warehouse=row.warehouse,
            permissions=sales_permissions,
        )
    ]
    data.quality_inspections = [
        row
        for row in data.quality_inspections
        if _scope_allowed(
            company=row.company,
            item_code=row.item_code,
            warehouse=row.warehouse,
            permissions=sales_permissions,
        )
    ]
    if before_total > 0 and not data.stock_entries and not data.quality_inspections:
        _raise_hidden_not_found()
    data.summary = _build_work_order_summary(
        stock_entries=data.stock_entries,
        quality_inspections=data.quality_inspections,
    )
    return _ok(data)


@router.get("/sales-order-trail/{sales_order_id}")
def get_sales_order_trail(
    sales_order_id: str,
    request: Request,
    company: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SALES_INVENTORY_READ,
        module="sales_inventory",
        resource_type="sales_order",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=QUALITY_READ,
        module="quality",
        resource_type="quality_inspection",
    )
    sales_permissions = _sales_inventory_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="sales_order",
        resource_no=sales_order_id,
    )

    service = CrossModuleViewService(session=session, request_obj=request)
    try:
        data = service.get_sales_order_trail(sales_order_id=sales_order_id, company=_scope_text(company))
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=SALES_INVENTORY_READ,
            resource_type="SalesOrder",
            resource_no=sales_order_id,
        )
    except AppException as exc:
        raise _map_app_exception(exc) from exc

    if data is None:
        _raise_hidden_not_found()

    _ensure_scope_or_hidden_not_found(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        module="sales_inventory",
        action=SALES_INVENTORY_READ,
        resource_scope={
            "company": data.sales_order.company,
            "customer": data.sales_order.customer,
        },
        required_fields=("company",),
        resource_type="sales_order",
        resource_no=sales_order_id,
        user_permissions=sales_permissions,
    )
    _ensure_scope_or_hidden_not_found(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        module="quality",
        action=QUALITY_READ,
        resource_scope={
            "company": data.sales_order.company,
        },
        required_fields=("company",),
        resource_type="quality_inspection",
        resource_no=sales_order_id,
    )

    before_total = len(data.delivery_notes) + len(data.quality_inspections)
    data.delivery_notes = [
        row
        for row in data.delivery_notes
        if _scope_allowed(
            company=row.company,
            item_code=row.item_code,
            warehouse=row.warehouse,
            permissions=sales_permissions,
        )
    ]
    data.quality_inspections = [
        row
        for row in data.quality_inspections
        if _scope_allowed(
            company=row.company,
            item_code=row.item_code,
            warehouse=row.warehouse,
            permissions=sales_permissions,
        )
    ]
    if before_total > 0 and not data.delivery_notes and not data.quality_inspections:
        _raise_hidden_not_found()
    data.summary = _build_sales_order_summary(
        ordered_qty=_decimal(data.summary.ordered_qty),
        delivery_notes=data.delivery_notes,
        quality_inspections=data.quality_inspections,
    )
    return _ok(data)
