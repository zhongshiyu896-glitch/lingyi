"""FastAPI router for sales/inventory read-only APIs (TASK-011B)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC
from datetime import date
from datetime import datetime
import os
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
from app.core.permissions import SALES_INVENTORY_DIAGNOSTIC
from app.core.permissions import SALES_INVENTORY_READ
from app.core.permissions import get_permission_source
from app.schemas.sales_inventory import DiagnosticData
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter
from app.services.permission_service import PermissionService
from app.services.sales_inventory_service import SalesInventoryService

router = APIRouter(prefix="/api/sales-inventory", tags=["sales_inventory"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


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
    """Record dependency security audit and raise unified HTTPException."""
    permission_service._record_security_audit_safe(  # noqa: SLF001 - shared security audit baseline.
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


def _local_read_fallback_enabled(exc: ERPNextAdapterException) -> bool:
    """Allow dev-only readonly fallback when ERPNext base URL is intentionally absent."""
    env = os.getenv("APP_ENV", "").strip().lower()
    allow_dev_auth = os.getenv("LINGYI_ALLOW_DEV_AUTH", "").strip().lower()
    return (
        exc.error_code == EXTERNAL_SERVICE_UNAVAILABLE
        and env in {"development", "dev", "local"}
        and allow_dev_auth == "true"
        and get_permission_source() == "static"
    )


def _raise_hidden_sales_order_not_found() -> None:
    """Return the same not-found envelope for absent and out-of-scope details."""
    raise HTTPException(
        status_code=404,
        detail={
            "code": ERPNEXT_RESOURCE_NOT_FOUND,
            "message": message_of(ERPNEXT_RESOURCE_NOT_FOUND),
            "data": None,
        },
    )


def _service(request: Request) -> SalesInventoryService:
    return SalesInventoryService(adapter=ERPNextSalesInventoryAdapter(request_obj=request))


def _get_read_permissions(
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


def _scope_allowed(row: Any, permissions: UserPermissionResult | None) -> bool:
    if get_permission_source() != "erpnext" or permissions is None or permissions.unrestricted:
        return True
    company = _scope_text(getattr(row, "company", None))
    item_code = _scope_text(getattr(row, "item_code", None))
    if item_code is None:
        item_code = _scope_text(getattr(row, "material_code", None))
    warehouse = _scope_text(getattr(row, "warehouse", None))
    customer = _scope_text(getattr(row, "customer", None))
    if warehouse is None and row.__class__.__name__ == "WarehouseItem":
        warehouse = _scope_text(getattr(row, "name", None))
    if customer is None and row.__class__.__name__ == "CustomerItem":
        customer = _scope_text(getattr(row, "name", None))
    if company and not ERPNextPermissionAdapter.is_company_permitted(company=company, user_permissions=permissions):
        return False
    if item_code and item_code not in permissions.allowed_items and permissions.allowed_items:
        return False
    if item_code and not permissions.allowed_items and (permissions.allowed_companies or permissions.allowed_warehouses or permissions.allowed_customers):
        return False
    if warehouse and not ERPNextPermissionAdapter.is_warehouse_permitted(warehouse=warehouse, user_permissions=permissions):
        return False
    if customer and not ERPNextPermissionAdapter.is_customer_permitted(customer=customer, user_permissions=permissions):
        return False
    return True


def _scope_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_optional_date(value: str | None, field_name: str) -> date | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_QUERY_PARAMETER",
                "message": f"{field_name} 日期格式非法，应为 YYYY-MM-DD",
                "data": None,
            },
        ) from exc


def _validate_date_range(*, from_date: date | None, to_date: date | None) -> None:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_QUERY_PARAMETER",
                "message": "from_date 不得晚于 to_date",
                "data": None,
            },
        )


@router.get("/sales-orders")
def list_sales_orders(
    request: Request,
    order_no: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    company: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    item_name: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="sales_order",
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="sales_order",
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"company": company, "customer": customer, "item_code": item_code},
        required_fields=(),
        resource_type="sales_order",
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    try:
        data = _service(request).list_sales_orders(
            order_no=_scope_text(order_no),
            keyword=_scope_text(keyword),
            company=company,
            customer=customer,
            item_code=item_code,
            item_name=_scope_text(item_name),
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            page=page,
            page_size=page_size,
        )
    except ERPNextAdapterException as exc:
        if _local_read_fallback_enabled(exc):
            return _ok({"items": [], "total": 0, "page": page, "page_size": page_size})
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SalesOrder",
        )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/sales-orders/{name}")
def get_sales_order_detail(
    name: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="sales_order",
    )
    try:
        data = _service(request).get_sales_order(name=name)
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SalesOrder",
            resource_no=name,
        )
    try:
        permission_service.ensure_resource_scope_permission(
            current_user=current_user,
            request_obj=request,
            module="sales_inventory",
            action=action,
            resource_scope={
                "company": data.company,
                "customer": data.customer,
            },
            required_fields=("company",),
            resource_type="sales_order",
            resource_no=name,
            enforce_action=False,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == RESOURCE_ACCESS_DENIED:
            _raise_hidden_sales_order_not_found()
        raise
    return _ok(data)


@router.get("/material-transfers")
def get_material_transfers(
    request: Request,
    item_code: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    source_warehouse: str | None = Query(default=None),
    target_warehouse: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": source_warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_material_transfers(
        item_code=_scope_text(item_code),
        keyword=_scope_text(keyword),
        source_warehouse=_scope_text(source_warehouse),
        target_warehouse=_scope_text(target_warehouse),
        status=_scope_text(status),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/material-counts")
def get_material_counts(
    request: Request,
    item_code: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    count_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_material_counts(
        item_code=_scope_text(item_code),
        keyword=_scope_text(keyword),
        warehouse=_scope_text(warehouse),
        count_status=_scope_text(count_status),
        review_status=_scope_text(review_status),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/material-inventory-report")
def get_material_inventory_report(
    request: Request,
    report_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    business_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_material_inventory_report(
        report_no=_scope_text(report_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        business_type=_scope_text(business_type),
        status=_scope_text(status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/inventory-material-retention-report")
def get_inventory_material_retention_report(
    request: Request,
    report_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    retention_level: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_inventory_material_retention_report(
        report_no=_scope_text(report_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        retention_level=_scope_text(retention_level),
        status=_scope_text(status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/semi-finished-inventory")
def get_semi_finished_inventory(
    request: Request,
    record_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    process_stage: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_semi_finished_inventory(
        record_no=_scope_text(record_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        process_stage=_scope_text(process_stage),
        status=_scope_text(status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-reserved-inbound")
def get_finished_goods_reserved_inbound(
    request: Request,
    reservation_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    reserve_status: str | None = Query(default=None),
    inbound_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_finished_goods_reserved_inbound(
        reservation_no=_scope_text(reservation_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        reserve_status=_scope_text(reserve_status),
        inbound_status=_scope_text(inbound_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-shipping-notices")
def get_finished_goods_shipping_notices(
    request: Request,
    notice_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    notice_status: str | None = Query(default=None),
    logistics_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_finished_goods_shipping_notices(
        notice_no=_scope_text(notice_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        notice_status=_scope_text(notice_status),
        logistics_status=_scope_text(logistics_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-other-inbound")
def get_finished_goods_other_inbound(
    request: Request,
    inbound_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    inbound_status: str | None = Query(default=None),
    settlement_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    data = _service(request).get_finished_goods_other_inbound(
        inbound_no=_scope_text(inbound_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        inbound_status=_scope_text(inbound_status),
        settlement_status=_scope_text(settlement_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/items/{item_code}/stock-summary")
def get_stock_summary(
    item_code: str,
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="item",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="item",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"company": company, "item_code": item_code, "warehouse": warehouse},
        required_fields=("item_code",),
        resource_type="item",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    try:
        data = _service(request).get_stock_summary(item_code=item_code, company=company, warehouse=warehouse)
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Item",
            resource_no=item_code,
        )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    return _ok(data)


@router.get("/items/{item_code}/stock-ledger")
def list_stock_ledger(
    item_code: str,
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="stock_ledger_entry",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"company": company, "item_code": item_code, "warehouse": warehouse},
        required_fields=("item_code",),
        resource_type="stock_ledger_entry",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    try:
        data = _service(request).list_stock_ledger(
            item_code=item_code,
            company=company,
            warehouse=warehouse,
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            page=page,
            page_size=page_size,
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="StockLedgerEntry",
            resource_no=item_code,
        )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/warehouses")
def list_warehouses(
    request: Request,
    company: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="warehouse",
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="warehouse",
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"company": company},
        required_fields=(),
        resource_type="warehouse",
        enforce_action=False,
        user_permissions=permissions,
    )
    try:
        data = _service(request).list_warehouses(company=company, page=page, page_size=page_size)
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Warehouse",
        )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/customers")
def list_customers(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="customer",
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="customer",
    )
    try:
        data = _service(request).list_customers(page=page, page_size=page_size)
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Customer",
        )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/aggregation")
def get_inventory_aggregation(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="item",
        resource_item_code=item_code,
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="item",
        resource_no=item_code,
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"company": company, "item_code": item_code, "warehouse": warehouse},
        required_fields=(),
        resource_type="item",
        resource_no=item_code,
        enforce_action=False,
        user_permissions=permissions,
    )
    try:
        data = _service(request).get_inventory_aggregation(company=company, item_code=item_code, warehouse=warehouse)
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Bin",
            resource_no=item_code,
        )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    return _ok(data)


@router.get("/sales-order-fulfillment")
def get_sales_order_fulfillment(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_name: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="sales_order",
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="sales_order",
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"company": company, "item_code": item_code, "warehouse": warehouse},
        required_fields=(),
        resource_type="sales_order",
        enforce_action=False,
        user_permissions=permissions,
    )
    try:
        data = _service(request).get_sales_order_fulfillment(
            company=company,
            item_code=_scope_text(item_code),
            warehouse=_scope_text(warehouse),
            item_name=_scope_text(item_name),
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SalesOrder",
        )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    return _ok(data)


@router.get("/finished-goods-report")
def get_finished_goods_report(
    request: Request,
    no: str | None = Query(default=None),
    style: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="sales_order",
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="sales_order",
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"warehouse": warehouse},
        required_fields=(),
        resource_type="sales_order",
        enforce_action=False,
        user_permissions=permissions,
    )
    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)
    try:
        data = _service(request).get_finished_goods_report(
            no=_scope_text(no),
            style=_scope_text(style),
            warehouse=_scope_text(warehouse),
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            keyword=_scope_text(keyword),
            page=page,
            page_size=page_size,
        )
    except ERPNextAdapterException as exc:
        if _local_read_fallback_enabled(exc):
            return _ok({"items": [], "total": 0, "page": page, "page_size": page_size, "dropped_count": 0})
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SalesOrder",
        )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/diagnostic")
def read_diagnostic(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = SALES_INVENTORY_DIAGNOSTIC
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="diagnostic",
    )
    try:
        ERPNextSalesInventoryAdapter(request_obj=request).ping()
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Diagnostic",
        )
    return _ok(DiagnosticData(status="ok", checked_at=datetime.now(UTC)))
