"""FastAPI router for warehouse read-only ledger/summary/alert APIs (TASK-050A)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import Any

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.auth import is_internal_worker_api_enabled
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.error_codes import RESOURCE_ACCESS_DENIED
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.permissions import WAREHOUSE_ALERT_READ
from app.core.permissions import WAREHOUSE_DIAGNOSTIC
from app.core.permissions import WAREHOUSE_EXPORT
from app.core.permissions import WAREHOUSE_INVENTORY_COUNT
from app.core.permissions import WAREHOUSE_READ
from app.core.permissions import WAREHOUSE_STOCK_ENTRY_CANCEL
from app.core.permissions import WAREHOUSE_STOCK_ENTRY_DRAFT
from app.core.permissions import WAREHOUSE_WORKER
from app.core.permissions import get_permission_source
from app.schemas.warehouse import ApiResponse
from app.schemas.warehouse import WarehouseBatchDetailData
from app.schemas.warehouse import WarehouseBatchListData
from app.schemas.warehouse import WarehouseDiagnosticData
from app.schemas.warehouse import WarehouseFinishedGoodsInboundCandidatesData
from app.schemas.warehouse import WarehouseInventoryCountCancelRequest
from app.schemas.warehouse import WarehouseInventoryCountCreateRequest
from app.schemas.warehouse import WarehouseInventoryCountVarianceReviewRequest
from app.schemas.warehouse import WarehouseSerialNumberDetailData
from app.schemas.warehouse import WarehouseSerialNumberListData
from app.schemas.warehouse import WarehouseStockEntryDraftCancelRequest
from app.schemas.warehouse import WarehouseStockEntryDraftCreateRequest
from app.schemas.warehouse import WarehouseStockEntryWorkerRunOnceData
from app.schemas.warehouse import WarehouseStockEntryWorkerRunOnceRequest
from app.schemas.warehouse import WarehouseTraceabilityData
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.erpnext_warehouse_adapter import ERPNextWarehouseAdapter
from app.services.permission_service import PermissionService
from app.services.warehouse_export_service import SUPPORTED_DATASETS
from app.services.warehouse_export_service import WarehouseExportService
from app.services.warehouse_service import WarehouseService
from app.services.warehouse_service import WarehouseServiceError

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return ApiResponse(code="0", message="success", data=data).model_dump(mode="json")


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


def _read_service(request: Request) -> WarehouseService:
    return WarehouseService(adapter=ERPNextWarehouseAdapter(request_obj=request))


def _write_service(session: Session, request: Request | None = None) -> WarehouseService:
    adapter = ERPNextWarehouseAdapter(request_obj=request) if request is not None else None
    return WarehouseService(session=session, adapter=adapter)


def _handle_erpnext_error(
    *,
    exc: ERPNextAdapterException,
    permission_service: PermissionService,
    request: Request,
    current_user: CurrentUser,
    action: str,
    resource_type: str,
) -> None:
    permission_service._record_security_audit_safe(  # noqa: SLF001 - keep shared security audit baseline.
        event_type=EXTERNAL_SERVICE_UNAVAILABLE,
        module="warehouse",
        action=action,
        resource_type=resource_type,
        resource_id=None,
        resource_no=None,
        user=current_user,
        deny_reason=exc.safe_message or message_of(EXTERNAL_SERVICE_UNAVAILABLE),
        request_obj=request,
        reason_code=exc.error_code,
    )
    raise HTTPException(status_code=int(exc.http_status or 503), detail=exc.to_http_detail()) from exc


def _require_warehouse_action(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    resource_type: str,
) -> None:
    """Require warehouse actions strictly with no inventory fallback."""
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="warehouse",
        resource_type=resource_type,
    )


def _get_user_permissions(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    resource_type: str,
) -> UserPermissionResult | None:
    if get_permission_source() != "erpnext":
        return None
    return permission_service.get_sales_inventory_user_permissions(
        current_user=current_user,
        request_obj=request,
        action=action,
        resource_type=resource_type,
        resource_id=None,
        resource_no=None,
    )


def _scope_allowed(
    *,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    permissions: UserPermissionResult | None,
) -> bool:
    if get_permission_source() != "erpnext" or permissions is None or permissions.unrestricted:
        return True

    normalized_company = _scope_text(company)
    normalized_warehouse = _scope_text(warehouse)
    normalized_item_code = _scope_text(item_code)

    if normalized_company and not ERPNextPermissionAdapter.is_company_permitted(
        company=normalized_company,
        user_permissions=permissions,
    ):
        return False
    if normalized_warehouse and not ERPNextPermissionAdapter.is_warehouse_permitted(
        warehouse=normalized_warehouse,
        user_permissions=permissions,
    ):
        return False
    if normalized_item_code and permissions.allowed_items and normalized_item_code not in permissions.allowed_items:
        return False
    if normalized_item_code and not permissions.allowed_items and (
        permissions.allowed_companies or permissions.allowed_warehouses or permissions.allowed_customers
    ):
        return False
    return True


def _serial_match(serial_value: str | None, expected_serial: str | None) -> bool:
    normalized_expected = _scope_text(expected_serial)
    if normalized_expected is None:
        return True
    text = _scope_text(serial_value)
    if text is None:
        return False
    normalized = text.replace("\n", ",").replace(";", ",")
    values = [part.strip() for part in normalized.split(",")]
    return normalized_expected in {value for value in values if value}


def _ensure_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    user_permissions: UserPermissionResult | None,
) -> None:
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="warehouse",
        action=action,
        resource_scope={
            "company": company,
            "warehouse": warehouse,
            "item_code": item_code,
        },
        required_fields=(),
        resource_type="warehouse",
        enforce_action=False,
        user_permissions=user_permissions,
    )


def _raise_scope_denied_as_forbidden(exc: HTTPException) -> None:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    if detail.get("code") == RESOURCE_ACCESS_DENIED:
        raise HTTPException(status_code=403, detail=detail) from exc
    raise exc


def _created(data: Any) -> JSONResponse:
    return JSONResponse(status_code=201, content=_ok(data))


def _raise_service_error(exc: WarehouseServiceError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message, "data": None},
    ) from exc


def _ensure_scope_required_text(value: str | None, field_name: str) -> str:
    text = _scope_text(value)
    if text is None:
        raise HTTPException(
            status_code=400,
            detail={"code": "WAREHOUSE_INVALID_PAYLOAD", "message": f"{field_name} 不能为空", "data": None},
        )
    return text


def _ensure_stock_entry_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    company: str,
    warehouse: str,
    item_code: str,
    user_permissions: UserPermissionResult | None,
) -> None:
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="warehouse",
        action=action,
        resource_scope={"company": company, "warehouse": warehouse, "item_code": item_code},
        required_fields=("company", "warehouse", "item_code"),
        resource_type="warehouse_stock_entry_draft",
        enforce_action=False,
        user_permissions=user_permissions,
    )


def _check_create_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    payload: WarehouseStockEntryDraftCreateRequest,
    user_permissions: UserPermissionResult | None,
) -> None:
    company = _ensure_scope_required_text(payload.company, "company")
    if not payload.items:
        raise HTTPException(
            status_code=400,
            detail={"code": "WAREHOUSE_INVALID_PAYLOAD", "message": "items 不能为空", "data": None},
        )
    for idx, item in enumerate(payload.items, start=1):
        item_code = _ensure_scope_required_text(item.item_code, f"items[{idx}].item_code")
        warehouses = {
            _scope_text(payload.source_warehouse),
            _scope_text(payload.target_warehouse),
            _scope_text(item.source_warehouse),
            _scope_text(item.target_warehouse),
        }
        for warehouse in sorted(filter(None, warehouses)):
            _ensure_stock_entry_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                user_permissions=user_permissions,
            )


def _check_draft_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    draft_data: dict[str, Any],
    user_permissions: UserPermissionResult | None,
) -> None:
    company = _ensure_scope_required_text(str(draft_data.get("company") or ""), "company")
    draft_source_warehouse = _scope_text(str(draft_data.get("source_warehouse") or ""))
    draft_target_warehouse = _scope_text(str(draft_data.get("target_warehouse") or ""))
    items = draft_data.get("items") or []
    for idx, item in enumerate(items, start=1):
        item_code = _ensure_scope_required_text(str(item.get("item_code") or ""), f"items[{idx}].item_code")
        warehouses = {
            draft_source_warehouse,
            draft_target_warehouse,
            _scope_text(str(item.get("source_warehouse") or "")),
            _scope_text(str(item.get("target_warehouse") or "")),
        }
        for warehouse in sorted(filter(None, warehouses)):
            _ensure_stock_entry_scope(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                user_permissions=user_permissions,
            )


def _ensure_inventory_count_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    company: str,
    warehouse: str,
    item_code: str,
    user_permissions: UserPermissionResult | None,
) -> None:
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="warehouse",
        action=action,
        resource_scope={"company": company, "warehouse": warehouse, "item_code": item_code},
        required_fields=("company", "warehouse", "item_code"),
        resource_type="warehouse_inventory_count",
        enforce_action=False,
        user_permissions=user_permissions,
    )


def _check_inventory_count_create_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    payload: WarehouseInventoryCountCreateRequest,
    user_permissions: UserPermissionResult | None,
) -> None:
    company = _ensure_scope_required_text(payload.company, "company")
    warehouse = _ensure_scope_required_text(payload.warehouse, "warehouse")
    if not payload.items:
        raise HTTPException(
            status_code=400,
            detail={"code": "WAREHOUSE_INVALID_PAYLOAD", "message": "items 不能为空", "data": None},
        )
    for idx, item in enumerate(payload.items, start=1):
        item_code = _ensure_scope_required_text(item.item_code, f"items[{idx}].item_code")
        _ensure_inventory_count_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=user_permissions,
        )


def _check_inventory_count_scope(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    count_data: dict[str, Any],
    user_permissions: UserPermissionResult | None,
) -> None:
    company = _ensure_scope_required_text(str(count_data.get("company") or ""), "company")
    warehouse = _ensure_scope_required_text(str(count_data.get("warehouse") or ""), "warehouse")
    items = count_data.get("items") or []
    for idx, item in enumerate(items, start=1):
        item_code = _ensure_scope_required_text(str(item.get("item_code") or ""), f"items[{idx}].item_code")
        _ensure_inventory_count_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=user_permissions,
        )


def _to_export_rows(items: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "model_dump"):
            rows.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            rows.append(dict(item))
        else:
            rows.append({})
    return rows


def _collect_export_dataset_rows(
    *,
    request: Request,
    dataset: str,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    batch_no: str | None,
    serial_no: str | None,
    from_date: date | None,
    to_date: date | None,
    alert_type: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    read_service = _read_service(request)
    if dataset == "stock_ledger":
        data = read_service.list_stock_ledger(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            from_date=from_date,
            to_date=to_date,
            page=1,
            page_size=limit,
        )
        return _to_export_rows(data.items)
    if dataset == "stock_summary":
        data = read_service.get_stock_summary(company=company, warehouse=warehouse, item_code=item_code)
        return _to_export_rows(data.items)[:limit]
    if dataset == "alerts":
        data = read_service.get_alerts(company=company, warehouse=warehouse, item_code=item_code, alert_type=alert_type)
        return _to_export_rows(data.items)[:limit]
    if dataset == "batches":
        data = read_service.list_batches(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            page=1,
            page_size=limit,
        )
        return _to_export_rows(data.items)
    if dataset == "serial_numbers":
        data = read_service.list_serial_numbers(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            serial_no=serial_no,
            page=1,
            page_size=limit,
        )
        return _to_export_rows(data.items)
    if dataset == "traceability":
        data = read_service.list_traceability(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            batch_no=batch_no,
            serial_no=serial_no,
            from_date=from_date,
            to_date=to_date,
            page=1,
            page_size=limit,
        )
        return _to_export_rows(data.items)
    raise HTTPException(
        status_code=400,
        detail={"code": "INVALID_QUERY_PARAMETER", "message": "dataset 非法", "data": None},
    )


def _filter_export_rows(
    *,
    rows: list[dict[str, Any]],
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    batch_no: str | None,
    serial_no: str | None,
    permissions: UserPermissionResult | None,
) -> list[dict[str, Any]]:
    normalized_company = _scope_text(company)
    normalized_warehouse = _scope_text(warehouse)
    normalized_item_code = _scope_text(item_code)
    normalized_batch = _scope_text(batch_no)
    normalized_serial = _scope_text(serial_no)

    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_company = _scope_text(row.get("company"))
        row_warehouse = _scope_text(row.get("warehouse"))
        row_item = _scope_text(row.get("item_code"))
        row_batch = _scope_text(row.get("batch_no"))
        row_serial = _scope_text(row.get("serial_no"))
        if normalized_company is not None and row_company != normalized_company:
            continue
        if normalized_warehouse is not None and row_warehouse != normalized_warehouse:
            continue
        if normalized_item_code is not None and row_item != normalized_item_code:
            continue
        if normalized_batch is not None and row_batch != normalized_batch:
            continue
        if normalized_serial is not None and not _serial_match(row_serial, normalized_serial):
            continue
        if not _scope_allowed(
            company=row_company,
            warehouse=row_warehouse,
            item_code=row_item,
            permissions=permissions,
        ):
            continue
        filtered.append(row)
    return filtered


@router.get("/stock-ledger")
def list_stock_ledger(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )

    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)

    try:
        data = _read_service(request).list_stock_ledger(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
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
        )

    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
    ]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/stock-summary")
def get_stock_summary(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )

    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _read_service(request).get_stock_summary(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Bin",
        )

    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
    ]
    data.items = filtered
    return _ok(data)


@router.get("/finished-goods-inbound-candidates")
def list_finished_goods_inbound_candidates(
    request: Request,
    company: str = Query(...),
    item_code: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_finished_goods_inbound",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=None,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    normalized_company = _scope_text(company)
    normalized_item_code = _scope_text(item_code)
    try:
        data: WarehouseFinishedGoodsInboundCandidatesData = _read_service(request).list_finished_goods_inbound_candidates(
            company=normalized_company
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="ProductInWarehouseOption",
        )

    data.items = [
        row
        for row in data.items
        if (normalized_item_code is None or row.item_code == normalized_item_code)
        and _scope_allowed(
            company=normalized_company,
            warehouse=None,
            item_code=row.item_code,
            permissions=permissions,
        )
    ]
    return _ok(data)


@router.get("/alerts")
def get_stock_alerts(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_ALERT_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_alert",
    )

    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _read_service(request).get_alerts(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            alert_type=_scope_text(alert_type),
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="WarehouseAlert",
        )

    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
    ]
    data.items = filtered
    return _ok(data)


@router.get("/batches")
def list_batches(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    batch_no: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_batch",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _read_service(request).list_batches(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            batch_no=_scope_text(batch_no),
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
            resource_type="Batch",
        )

    normalized_batch = _scope_text(batch_no)
    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
        and (normalized_batch is None or row.batch_no == normalized_batch)
    ]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/batches/{batch_no}")
def get_batch_detail(
    batch_no: str,
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_batch",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _read_service(request).get_batch_detail(
            batch_no=batch_no,
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Batch",
        )

    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
    ]
    if not filtered:
        raise HTTPException(
            status_code=404,
            detail={"code": "WAREHOUSE_BATCH_NOT_FOUND", "message": "批次不存在或无权限访问", "data": None},
        )
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/serial-numbers")
def list_serial_numbers(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    batch_no: str | None = Query(default=None),
    serial_no: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_serial_no",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _read_service(request).list_serial_numbers(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            batch_no=_scope_text(batch_no),
            serial_no=_scope_text(serial_no),
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
            resource_type="SerialNo",
        )

    normalized_batch = _scope_text(batch_no)
    normalized_serial = _scope_text(serial_no)
    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
        and (normalized_batch is None or row.batch_no == normalized_batch)
        and (normalized_serial is None or row.serial_no == normalized_serial)
    ]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/serial-numbers/{serial_no}")
def get_serial_number_detail(
    serial_no: str,
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_serial_no",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _read_service(request).get_serial_number_detail(
            serial_no=serial_no,
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SerialNo",
        )

    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
        and row.serial_no == _scope_text(serial_no)
    ]
    if not filtered:
        raise HTTPException(
            status_code=404,
            detail={"code": "WAREHOUSE_SERIAL_NOT_FOUND", "message": "序列号不存在或无权限访问", "data": None},
        )
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/traceability")
def list_traceability(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    batch_no: str | None = Query(default=None),
    serial_no: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_traceability",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)

    try:
        data = _read_service(request).list_traceability(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            batch_no=_scope_text(batch_no),
            serial_no=_scope_text(serial_no),
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
        )

    normalized_batch = _scope_text(batch_no)
    normalized_serial = _scope_text(serial_no)
    filtered = [
        row
        for row in data.items
        if _scope_allowed(
            company=row.company,
            warehouse=row.warehouse,
            item_code=row.item_code,
            permissions=permissions,
        )
        and (normalized_batch is None or _scope_text(row.batch_no) == normalized_batch)
        and _serial_match(row.serial_no, normalized_serial)
    ]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@router.get("/export")
def export_warehouse_readonly_csv(
    request: Request,
    dataset: str = Query(default="stock_summary"),
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    batch_no: str | None = Query(default=None),
    serial_no: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_EXPORT
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_export",
    )
    normalized_dataset = _scope_text(dataset) or "stock_summary"
    if normalized_dataset not in SUPPORTED_DATASETS:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUERY_PARAMETER", "message": "dataset 非法", "data": None},
        )

    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)

    try:
        rows = _collect_export_dataset_rows(
            request=request,
            dataset=normalized_dataset,
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            batch_no=_scope_text(batch_no),
            serial_no=_scope_text(serial_no),
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            alert_type=_scope_text(alert_type),
            limit=limit,
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="WarehouseExport",
        )

    filtered = _filter_export_rows(
        rows=rows,
        company=company,
        warehouse=warehouse,
        item_code=item_code,
        batch_no=batch_no,
        serial_no=serial_no,
        permissions=permissions,
    )[:limit]
    artifact = WarehouseExportService.build_csv(dataset=normalized_dataset, rows=filtered)
    headers = {"Content-Disposition": f'attachment; filename="{artifact.filename}"'}
    return StreamingResponse(iter([artifact.content]), media_type=artifact.content_type, headers=headers)


@router.get("/diagnostic")
def get_warehouse_diagnostic(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_DIAGNOSTIC
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_diagnostic",
    )
    adapter_configured = bool(ERPNextWarehouseAdapter(request_obj=request).base_url)
    data: WarehouseDiagnosticData = WarehouseExportService.build_diagnostic_snapshot(
        adapter_configured=adapter_configured
    )
    return _ok(data)


@router.post("/stock-entry-drafts")
def create_stock_entry_draft(
    request: Request,
    payload: WarehouseStockEntryDraftCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_STOCK_ENTRY_DRAFT
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_stock_entry_draft",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _check_create_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            payload=payload,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _write_service(session, request=request).create_stock_entry_draft(
            payload=payload,
            current_user=current_user.username,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _created(data)


@router.post("/stock-entry-drafts/{draft_id}/cancel")
def cancel_stock_entry_draft(
    draft_id: int,
    request: Request,
    payload: WarehouseStockEntryDraftCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_STOCK_ENTRY_CANCEL
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_stock_entry_draft",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )

    try:
        before_data = _write_service(session).get_stock_entry_draft(draft_id=draft_id).model_dump(mode="json")
    except WarehouseServiceError as exc:
        _raise_service_error(exc)

    try:
        _check_draft_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            draft_data=before_data,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _write_service(session).cancel_stock_entry_draft(
            draft_id=draft_id,
            reason=payload.reason,
            cancelled_by=current_user.username,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@router.get("/stock-entry-drafts/{draft_id}")
def get_stock_entry_draft(
    draft_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_stock_entry_draft",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        data = _write_service(session).get_stock_entry_draft(draft_id=draft_id)
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
    try:
        _check_draft_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            draft_data=data.model_dump(mode="json"),
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)
    return _ok(data)


@router.get("/stock-entry-drafts/{draft_id}/outbox-status")
def get_stock_entry_outbox_status(
    draft_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_stock_entry_outbox",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        draft_data = _write_service(session).get_stock_entry_draft(draft_id=draft_id)
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
    try:
        _check_draft_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            draft_data=draft_data.model_dump(mode="json"),
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        outbox_data = _write_service(session).get_stock_entry_outbox_status(draft_id=draft_id)
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
    return _ok(outbox_data)


@router.post("/internal/stock-entry-sync/run-once")
def run_warehouse_stock_entry_sync_once(
    request: Request,
    payload: WarehouseStockEntryWorkerRunOnceRequest = Body(default=WarehouseStockEntryWorkerRunOnceRequest()),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_WORKER
    permission_service = PermissionService(session=session)

    if not is_internal_worker_api_enabled():
        permission_service.record_security_denial(
            request_obj=request,
            current_user=current_user,
            action=action,
            resource_type="warehouse_stock_entry_worker",
            resource_no="run-once",
            deny_reason="仓库 stock entry worker 内部接口未启用",
            event_type=INTERNAL_API_DISABLED,
            module="warehouse",
        )
        raise HTTPException(
            status_code=status_of(INTERNAL_API_DISABLED),
            detail={"code": INTERNAL_API_DISABLED, "message": "内部接口未启用", "data": None},
        )

    permission_service.require_action_from_roles_only(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="warehouse",
        resource_type="warehouse_stock_entry_worker",
    )
    permission_service.require_internal_worker_principal(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="warehouse",
        resource_type="WAREHOUSESTOCKENTRYWORKER",
    )

    try:
        data = _write_service(session).run_stock_entry_outbox_once(
            batch_size=payload.batch_size,
            dry_run=payload.dry_run,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(WarehouseStockEntryWorkerRunOnceData(**data.model_dump(mode="json")))


@router.post("/inventory-counts")
def create_inventory_count(
    request: Request,
    payload: WarehouseInventoryCountCreateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_INVENTORY_COUNT
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_inventory_count",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _check_inventory_count_create_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            payload=payload,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _write_service(session).create_inventory_count(payload=payload, current_user=current_user.username)
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _created(data)


@router.post("/inventory-counts/{count_id}/submit")
def submit_inventory_count(
    count_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_INVENTORY_COUNT
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_inventory_count",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        before_data = _write_service(session).get_inventory_count(count_id=count_id).model_dump(mode="json")
    except WarehouseServiceError as exc:
        _raise_service_error(exc)

    try:
        _check_inventory_count_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            count_data=before_data,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _write_service(session).submit_inventory_count(count_id=count_id, submitted_by=current_user.username)
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@router.post("/inventory-counts/{count_id}/variance-review")
def variance_review_inventory_count(
    count_id: int,
    request: Request,
    payload: WarehouseInventoryCountVarianceReviewRequest | None = Body(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_INVENTORY_COUNT
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_inventory_count",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        before_data = _write_service(session).get_inventory_count(count_id=count_id).model_dump(mode="json")
    except WarehouseServiceError as exc:
        _raise_service_error(exc)

    try:
        _check_inventory_count_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            count_data=before_data,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _write_service(session).variance_review_inventory_count(
            count_id=count_id,
            payload=payload,
            reviewed_by=current_user.username,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@router.post("/inventory-counts/{count_id}/confirm")
def confirm_inventory_count(
    count_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_INVENTORY_COUNT
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_inventory_count",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        before_data = _write_service(session).get_inventory_count(count_id=count_id).model_dump(mode="json")
    except WarehouseServiceError as exc:
        _raise_service_error(exc)

    try:
        _check_inventory_count_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            count_data=before_data,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _write_service(session).confirm_inventory_count(count_id=count_id, confirmed_by=current_user.username)
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@router.post("/inventory-counts/{count_id}/cancel")
def cancel_inventory_count(
    count_id: int,
    request: Request,
    payload: WarehouseInventoryCountCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_INVENTORY_COUNT
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_inventory_count",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        before_data = _write_service(session).get_inventory_count(count_id=count_id).model_dump(mode="json")
    except WarehouseServiceError as exc:
        _raise_service_error(exc)

    try:
        _check_inventory_count_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            count_data=before_data,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    try:
        data = _write_service(session).cancel_inventory_count(
            count_id=count_id,
            reason=payload.reason,
            cancelled_by=current_user.username,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@router.get("/inventory-counts/{count_id}")
def get_inventory_count(
    count_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_inventory_count",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        data = _write_service(session).get_inventory_count(count_id=count_id)
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
    try:
        _check_inventory_count_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            count_data=data.model_dump(mode="json"),
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)
    return _ok(data)


@router.get("/inventory-counts")
def list_inventory_counts(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    status: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_READ
    permission_service = PermissionService(session=session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_inventory_count",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )
    try:
        _ensure_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    parsed_from_date = _parse_optional_date(from_date, "from_date")
    parsed_to_date = _parse_optional_date(to_date, "to_date")
    _validate_date_range(from_date=parsed_from_date, to_date=parsed_to_date)

    try:
        data = _write_service(session).list_inventory_counts(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            status=_scope_text(status),
            from_date=parsed_from_date,
            to_date=parsed_to_date,
            item_code=_scope_text(item_code),
        )
    except WarehouseServiceError as exc:
        _raise_service_error(exc)

    filtered = []
    for row in data.items:
        if not _scope_allowed(company=row.company, warehouse=row.warehouse, item_code=None, permissions=permissions):
            continue
        denied = False
        for item in row.items:
            if not _scope_allowed(
                company=row.company,
                warehouse=row.warehouse,
                item_code=item.item_code,
                permissions=permissions,
            ):
                denied = True
                break
        if not denied:
            filtered.append(row)
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)
