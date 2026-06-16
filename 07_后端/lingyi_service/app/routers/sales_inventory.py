"""FastAPI router for sales/inventory read-only APIs (TASK-011B)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
import os
import re
from typing import Any

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
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
from app.core.request_id import get_request_id_from_request
from app.core.request_id import is_request_id_valid
from app.schemas.sales_inventory import DiagnosticData
from app.schemas.sales_inventory import DeliveryNoteListData
from app.schemas.sales_inventory import InventoryAggregationData
from app.schemas.sales_inventory import ReferenceDraftCreateRequest
from app.schemas.sales_inventory import ReferenceDraftDeactivateRequest
from app.schemas.sales_inventory import SupplierItem
from app.schemas.sales_inventory import SalesOrderDraftCancelRequest
from app.schemas.sales_inventory import SalesOrderDraftCreateRequest
from app.schemas.sales_inventory import SalesInvoiceListData
from app.schemas.sales_inventory import StockLedgerData
from app.schemas.sales_inventory import StockLedgerItem
from app.schemas.sales_inventory import StockSummaryData
from app.schemas.sales_inventory import StockSummaryItem
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.services.erpnext_fail_closed_adapter import ERPNextAdapterException
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter
from app.services.frontend_readiness_seed_reader import dev_seed_page_for_user
from app.services.permission_service import PermissionService
from app.services.sales_inventory_service import SalesInventoryService
from app.services.sales_inventory_service import SalesInventoryServiceError

router = APIRouter(prefix="/api/sales-inventory", tags=["sales_inventory"])
reference_local_router = APIRouter(tags=["sales_inventory"])
SALES_ORDER_LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
SALES_ORDER_SCENARIO_FULL_PATTERN = re.compile(r"^Z003-SALES-ORDER-\d{8}-\d{3}$")
SALES_ORDER_REQUEST_TAG_PATTERN = re.compile(r"^(Z003-SALES-ORDER-\d{8}-\d{3})(?:$|[-_.].*)$")
SALES_ORDER_IDEMPOTENCY_PATTERN = re.compile(r"^IDEMP-(Z003-SALES-ORDER-\d{8}-\d{3})$")
SALES_ORDER_SOURCE_REF_PATTERN = re.compile(r"^SRC-(Z003-SALES-ORDER-\d{8}-\d{3})$")
SALES_ORDER_NO_PATTERN = re.compile(r"^SO-(Z003-SALES-ORDER-\d{8}-\d{3})$")
SALES_ORDER_CANCEL_REASON_PATTERN = re.compile(r"^VOID-(Z003-SALES-ORDER-\d{8}-\d{3})$")
REFERENCE_LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
REFERENCE_SCENARIO_FULL_PATTERN = re.compile(r"^Z003-SALES-INV-REF-\d{8}-\d{3}$")
REFERENCE_REQUEST_TAG_PATTERN = re.compile(r"^(Z003-SALES-INV-REF-\d{8}-\d{3})(?:$|[-_.].*)$")
REFERENCE_IDEMPOTENCY_PATTERN = re.compile(r"^IDEMP-(Z003-SALES-INV-REF-\d{8}-\d{3})(?:[-_.].*)?$")
REFERENCE_ALLOWED_TYPES = {"customer", "supplier"}


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": jsonable_encoder(data)}


def _created(data: Any) -> JSONResponse:
    return JSONResponse(status_code=201, content=_ok(data))


def _is_local_sales_order_write_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    db_url = os.getenv("LINGYI_DB_URL", "").strip()
    return app_env == "development" and db_url == SALES_ORDER_LOCAL_ALLOWED_DB_URL


def _is_local_reference_write_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    db_url = os.getenv("LINGYI_DB_URL", "").strip()
    return app_env in {"development", "dev", "local"} and db_url == REFERENCE_LOCAL_ALLOWED_DB_URL


def _is_local_reference_route_enabled() -> bool:
    return _is_local_reference_write_enabled()


def _extract_sales_order_request_tag(value: str) -> str | None:
    matched = SALES_ORDER_REQUEST_TAG_PATTERN.fullmatch(value)
    if matched is None:
        return None
    return matched.group(1)


def _extract_reference_request_tag(value: str) -> str | None:
    matched = REFERENCE_REQUEST_TAG_PATTERN.fullmatch(value)
    if matched is None:
        return None
    return matched.group(1)


def _match_sales_order_prefixed_carrier(value: str | None, pattern: re.Pattern[str]) -> str | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    matched = pattern.fullmatch(normalized)
    if matched is None:
        return None
    return matched.group(1)


def _raise_sales_order_idempotency_conflict(message: str) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "code": "SALES_ORDER_IDEMPOTENCY_CONFLICT",
            "message": message,
            "data": {},
        },
    )


def _raise_reference_idempotency_conflict(message: str) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "code": "SALES_INVENTORY_REFERENCE_CONFLICT",
            "message": message,
            "data": {},
        },
    )


def _validate_local_sales_order_write_gate(
    *,
    request_obj: Request,
    scenario_tag: str | None,
    idempotency_key: str | None,
    source_order_ref: str | None,
    sales_order_no: str | None,
    company: str | None,
    operation: str | None,
    expected_operation: str,
    draft_id: int | None = None,
    cancel_reason: str | None = None,
) -> str:
    if not _is_local_sales_order_write_enabled():
        _raise_sales_order_idempotency_conflict("仅允许本地开发测试库执行销售订单写入")

    request_id_header = (request_obj.headers.get("X-Request-ID") or "").strip()
    if not request_id_header:
        _raise_sales_order_idempotency_conflict("request_id 不能为空")
    if not is_request_id_valid(request_id_header):
        _raise_sales_order_idempotency_conflict("request_id_pattern_invalid")
    header_tag = _extract_sales_order_request_tag(request_id_header)
    if header_tag is None or SALES_ORDER_SCENARIO_FULL_PATTERN.fullmatch(header_tag) is None:
        _raise_sales_order_idempotency_conflict("request_id 未包含合法 scenario_tag")

    request_id = get_request_id_from_request(request_obj).strip()
    if not request_id:
        _raise_sales_order_idempotency_conflict("request_id 不能为空")
    if not is_request_id_valid(request_id):
        _raise_sales_order_idempotency_conflict("request_id_pattern_invalid")
    request_tag = _extract_sales_order_request_tag(request_id)
    if request_tag is None:
        _raise_sales_order_idempotency_conflict("request_id 未包含合法 scenario_tag")
    if request_tag != header_tag:
        _raise_sales_order_idempotency_conflict("request_id 与 scenario_tag 不一致")
    if request_id != request_id_header:
        _raise_sales_order_idempotency_conflict("request_id 与 Header 不一致")

    normalized_scenario_tag = _scope_text(scenario_tag)
    if normalized_scenario_tag is None:
        _raise_sales_order_idempotency_conflict("scenario_tag 载体缺失")
    if SALES_ORDER_SCENARIO_FULL_PATTERN.fullmatch(normalized_scenario_tag) is None:
        _raise_sales_order_idempotency_conflict("scenario_tag 载体缺失或格式非法")
    if normalized_scenario_tag != header_tag:
        _raise_sales_order_idempotency_conflict("scenario_tag 载体与 request_id 不一致")

    idempotency_tag = _match_sales_order_prefixed_carrier(idempotency_key, SALES_ORDER_IDEMPOTENCY_PATTERN)
    if idempotency_tag is None:
        _raise_sales_order_idempotency_conflict("idempotency_key 载体缺失或格式非法")
    if idempotency_tag != normalized_scenario_tag:
        _raise_sales_order_idempotency_conflict("idempotency_key 载体与 scenario_tag 不一致")

    source_tag = _match_sales_order_prefixed_carrier(source_order_ref, SALES_ORDER_SOURCE_REF_PATTERN)
    if source_tag is None:
        _raise_sales_order_idempotency_conflict("source_order_ref 载体缺失或格式非法")
    if source_tag != normalized_scenario_tag:
        _raise_sales_order_idempotency_conflict("source_order_ref 载体与 scenario_tag 不一致")

    order_tag = _match_sales_order_prefixed_carrier(sales_order_no, SALES_ORDER_NO_PATTERN)
    if order_tag is None:
        _raise_sales_order_idempotency_conflict("sales_order_no 载体缺失或格式非法")
    if order_tag != normalized_scenario_tag:
        _raise_sales_order_idempotency_conflict("sales_order_no 载体与 scenario_tag 不一致")

    normalized_company = _scope_text(company)
    if normalized_company is None:
        _raise_sales_order_idempotency_conflict("company 载体缺失")

    normalized_operation = _scope_text(operation)
    if normalized_operation is None:
        _raise_sales_order_idempotency_conflict("operation 载体缺失")
    if normalized_operation not in {"create_draft", "cancel_draft"}:
        _raise_sales_order_idempotency_conflict("operation 载体缺失或格式非法")
    if normalized_operation != expected_operation:
        _raise_sales_order_idempotency_conflict("operation 载体与路由动作不一致")

    if expected_operation == "cancel_draft":
        if draft_id is None or draft_id <= 0:
            _raise_sales_order_idempotency_conflict("draft_id 载体缺失或格式非法")
        cancel_reason_tag = _match_sales_order_prefixed_carrier(cancel_reason, SALES_ORDER_CANCEL_REASON_PATTERN)
        if cancel_reason_tag is None:
            _raise_sales_order_idempotency_conflict("operation 载体与路由动作不一致")
        if cancel_reason_tag != normalized_scenario_tag:
            _raise_sales_order_idempotency_conflict("operation 载体与 scenario_tag 不一致")

    return normalized_scenario_tag


def _validate_local_reference_write_gate(
    *,
    request_obj: Request,
    scenario_tag: str | None,
    idempotency_key: str | None,
    company: str | None,
    reference_type: str,
    operation: str | None,
    expected_operation: str,
    draft_id: int | None = None,
) -> str:
    if not _is_local_reference_write_enabled():
        _raise_reference_idempotency_conflict("仅允许本地开发测试库执行基础资料本地草稿写入")

    request_id_header = (request_obj.headers.get("X-Request-ID") or "").strip()
    if not request_id_header:
        _raise_reference_idempotency_conflict("request_id 不能为空")
    if not is_request_id_valid(request_id_header):
        _raise_reference_idempotency_conflict("request_id_pattern_invalid")
    header_tag = _extract_reference_request_tag(request_id_header)
    if header_tag is None or REFERENCE_SCENARIO_FULL_PATTERN.fullmatch(header_tag) is None:
        _raise_reference_idempotency_conflict("request_id 未包含合法 scenario_tag")

    request_id = get_request_id_from_request(request_obj).strip()
    if not request_id or request_id != request_id_header:
        _raise_reference_idempotency_conflict("request_id 与 Header 不一致")

    normalized_scenario_tag = _scope_text(scenario_tag)
    if normalized_scenario_tag is None or REFERENCE_SCENARIO_FULL_PATTERN.fullmatch(normalized_scenario_tag) is None:
        _raise_reference_idempotency_conflict("scenario_tag 载体缺失或格式非法")
    if normalized_scenario_tag != header_tag:
        _raise_reference_idempotency_conflict("scenario_tag 载体与 request_id 不一致")

    idempotency_tag = _match_sales_order_prefixed_carrier(idempotency_key, REFERENCE_IDEMPOTENCY_PATTERN)
    if idempotency_tag is None:
        _raise_reference_idempotency_conflict("idempotency_key 载体缺失或格式非法")
    if idempotency_tag != normalized_scenario_tag:
        _raise_reference_idempotency_conflict("idempotency_key 载体与 scenario_tag 不一致")

    normalized_company = _scope_text(company)
    if normalized_company is None:
        _raise_reference_idempotency_conflict("company 载体缺失")

    normalized_reference_type = _scope_text(reference_type)
    if normalized_reference_type not in REFERENCE_ALLOWED_TYPES:
        _raise_reference_idempotency_conflict("reference_type 非法")

    normalized_operation = _scope_text(operation)
    if normalized_operation != expected_operation:
        _raise_reference_idempotency_conflict("operation 载体与路由动作不一致")

    if expected_operation == "deactivate_draft" and (draft_id is None or draft_id <= 0):
        _raise_reference_idempotency_conflict("draft_id 载体缺失或格式非法")

    return normalized_scenario_tag


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
        and env in {"development", "dev", "local", "test"}
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


def _write_service(session: Session, request: Request | None = None) -> SalesInventoryService:
    adapter = ERPNextSalesInventoryAdapter(request_obj=request) if request is not None else None
    return SalesInventoryService(adapter=adapter, session=session)


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


def _paginate_list_items(items: list[Any], *, page: int, page_size: int) -> tuple[list[Any], int]:
    total = len(items)
    start = max((page - 1) * page_size, 0)
    end = start + page_size
    return items[start:end], total


def _build_local_stock_summary_fallback(
    *,
    session: Session,
    item_code: str,
    company: str | None,
    warehouse: str | None,
) -> StockSummaryData:
    normalized_company = _scope_text(company)
    normalized_warehouse = _scope_text(warehouse)
    query = (
        session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
        .join(
            LyWarehouseStockEntryDraftItem,
            LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id,
        )
        .filter(
            LyWarehouseStockEntryDraft.status != "cancelled",
            LyWarehouseStockEntryDraftItem.item_code == item_code,
        )
    )
    if normalized_company is not None:
        query = query.filter(LyWarehouseStockEntryDraft.company == normalized_company)
    if normalized_warehouse is not None:
        query = query.filter(LyWarehouseStockEntryDraft.target_warehouse == normalized_warehouse)

    grouped: dict[tuple[str, str], Decimal] = {}
    latest_posting: dict[tuple[str, str], datetime | None] = {}
    for draft_row, item_row in query.all():
        company_key = str(draft_row.company)
        warehouse_key = str(item_row.target_warehouse or draft_row.target_warehouse or "")
        key = (company_key, warehouse_key)
        grouped[key] = grouped.get(key, Decimal("0")) + Decimal(str(item_row.qty))
        current_latest = latest_posting.get(key)
        if current_latest is None or ((draft_row.created_at or datetime.min.replace(tzinfo=UTC)) > current_latest):
            latest_posting[key] = draft_row.created_at

    items: list[StockSummaryItem] = []
    for (company_key, warehouse_key), qty in sorted(grouped.items()):
        latest = latest_posting.get((company_key, warehouse_key))
        items.append(
            StockSummaryItem(
                company=company_key,
                item_code=item_code,
                warehouse=warehouse_key,
                balance_qty=qty,
                latest_posting_date=(latest.date() if latest else None),
                latest_posting_time=(latest.time().isoformat(timespec="seconds") if latest else None),
            )
        )

    return StockSummaryData(
        item_code=item_code,
        company=normalized_company,
        warehouse=normalized_warehouse,
        items=items,
        dropped_count=0,
    )


def _build_local_stock_ledger_fallback(
    *,
    session: Session,
    item_code: str,
    company: str | None,
    warehouse: str | None,
    page: int,
    page_size: int,
) -> StockLedgerData:
    normalized_company = _scope_text(company)
    normalized_warehouse = _scope_text(warehouse)
    query = (
        session.query(LyWarehouseStockEntryDraft, LyWarehouseStockEntryDraftItem)
        .join(
            LyWarehouseStockEntryDraftItem,
            LyWarehouseStockEntryDraftItem.draft_id == LyWarehouseStockEntryDraft.id,
        )
        .filter(
            LyWarehouseStockEntryDraft.status != "cancelled",
            LyWarehouseStockEntryDraftItem.item_code == item_code,
        )
        .order_by(LyWarehouseStockEntryDraft.created_at.asc(), LyWarehouseStockEntryDraft.id.asc())
    )
    if normalized_company is not None:
        query = query.filter(LyWarehouseStockEntryDraft.company == normalized_company)
    if normalized_warehouse is not None:
        query = query.filter(LyWarehouseStockEntryDraft.target_warehouse == normalized_warehouse)

    running_qty = Decimal("0")
    ledger_items: list[StockLedgerItem] = []
    for draft_row, item_row in query.all():
        qty = Decimal(str(item_row.qty))
        running_qty += qty
        created_at = draft_row.created_at or datetime.now(UTC)
        ledger_items.append(
            StockLedgerItem(
                name=f"DRAFT-{draft_row.id}-{item_row.id}",
                company=str(draft_row.company),
                item_code=item_code,
                warehouse=str(item_row.target_warehouse or draft_row.target_warehouse or ""),
                posting_date=created_at.date(),
                posting_time=created_at.time().isoformat(timespec="seconds"),
                actual_qty=qty,
                qty_after_transaction=running_qty,
                voucher_type="Stock Entry Draft",
                voucher_no=f"DRAFT-{draft_row.id}",
            )
        )

    total = len(ledger_items)
    start = max((page - 1) * page_size, 0)
    end = start + page_size
    return StockLedgerData(items=ledger_items[start:end], total=total, page=page, page_size=page_size, dropped_count=0)


def _build_local_list_fallback(*, page: int, page_size: int) -> dict[str, Any]:
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
    }


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


def _raise_sales_inventory_service_error(exc: SalesInventoryServiceError) -> None:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message, "data": None},
    ) from exc


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
    local_items: list[Any] = []
    if _is_local_sales_order_write_enabled():
        local_items = _write_service(session).list_local_sales_orders(
            order_no=_scope_text(order_no),
            keyword=_scope_text(keyword),
            company=company,
            customer=customer,
            item_code=item_code,
            item_name=_scope_text(item_name),
            from_date=parsed_from_date,
            to_date=parsed_to_date,
        )
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
        if (_local_read_fallback_enabled(exc) or _is_local_sales_order_write_enabled()) and local_items:
            fallback_items = [item for item in local_items if _scope_allowed(item, permissions)]
            paged_items, total = _paginate_list_items(fallback_items, page=page, page_size=page_size)
            return _ok({"items": paged_items, "total": total, "page": page, "page_size": page_size})
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SalesOrder",
        )
    if local_items:
        merged: dict[str, Any] = {str(item.name): item for item in data.items}
        for local_item in local_items:
            merged[str(local_item.name)] = local_item
        data.items = list(merged.values())
        data.total = len(data.items)
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    paged_items, total = _paginate_list_items(filtered, page=page, page_size=page_size)
    data.items = paged_items
    data.total = total
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
        if _is_local_sales_order_write_enabled():
            local_detail = _write_service(session).get_local_sales_order(name=name)
            if local_detail is not None:
                return _ok(local_detail)
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


@router.get("/delivery-notes")
def list_delivery_notes(
    request: Request,
    company: str | None = Query(default=None),
    sales_order: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: Any = Query(default=1),
    page_size: Any = Query(default=20),
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
        resource_type="delivery_note",
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="delivery_note",
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "company": company,
            "customer": customer,
            "item_code": item_code,
            "warehouse": warehouse,
        },
        required_fields=(),
        resource_type="delivery_note",
        enforce_action=False,
        user_permissions=permissions,
    )
    data = DeliveryNoteListData(
        **dev_seed_page_for_user(
            seed_key="delivery_notes",
            current_user=current_user,
            page=page,
            page_size=page_size,
            filters={
                "company": company,
                "sales_order": sales_order,
                "customer": customer,
                "item_code": item_code,
                "warehouse": warehouse,
                "status": status,
            },
        )
    )
    return _ok(data)


@router.get("/sales-invoices")
def list_sales_invoices(
    request: Request,
    company: str | None = Query(default=None),
    sales_order: str | None = Query(default=None),
    customer: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: Any = Query(default=1),
    page_size: Any = Query(default=20),
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
        resource_type="sales_invoice",
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="sales_invoice",
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={
            "company": company,
            "customer": customer,
        },
        required_fields=(),
        resource_type="sales_invoice",
        enforce_action=False,
        user_permissions=permissions,
    )
    data = SalesInvoiceListData(
        **dev_seed_page_for_user(
            seed_key="sales_invoices",
            current_user=current_user,
            page=page,
            page_size=page_size,
            filters={
                "company": company,
                "sales_order": sales_order,
                "customer": customer,
                "status": status,
            },
        )
    )
    return _ok(data)


@router.post("/sales-orders/drafts")
def create_sales_order_draft(
    request: Request,
    payload: SalesOrderDraftCreateRequest = Body(...),
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
    scenario_tag = _validate_local_sales_order_write_gate(
        request_obj=request,
        scenario_tag=payload.scenario_tag,
        idempotency_key=payload.idempotency_key,
        source_order_ref=payload.source_order_ref,
        sales_order_no=payload.sales_order_no,
        company=payload.company,
        operation=payload.operation,
        expected_operation="create_draft",
    )
    try:
        data = _write_service(session).create_sales_order_draft(
            payload=payload,
            current_user=current_user.username,
            scenario_tag=scenario_tag,
        )
        session.commit()
    except SalesInventoryServiceError as exc:
        session.rollback()
        _raise_sales_inventory_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _created(data)


@router.post("/sales-orders/drafts/{draft_id}/cancel")
def cancel_sales_order_draft(
    draft_id: int,
    request: Request,
    payload: SalesOrderDraftCancelRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    if draft_id <= 0:
        _raise_sales_order_idempotency_conflict("draft_id 载体缺失或格式非法")
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
        gate_fields = _write_service(session).get_sales_order_draft_gate_carriers(draft_id=draft_id)
    except SalesInventoryServiceError as exc:
        _raise_sales_inventory_service_error(exc)
    _validate_local_sales_order_write_gate(
        request_obj=request,
        scenario_tag=payload.scenario_tag,
        idempotency_key=payload.idempotency_key,
        source_order_ref=gate_fields.get("source_order_ref"),
        sales_order_no=gate_fields.get("sales_order_no"),
        company=payload.company,
        operation=payload.operation,
        expected_operation="cancel_draft",
        draft_id=draft_id,
        cancel_reason=payload.reason,
    )
    if payload.company.strip() != gate_fields.get("company", ""):
        _raise_sales_order_idempotency_conflict("company 载体与草稿上下文不一致")
    if payload.scenario_tag.strip() != gate_fields.get("scenario_tag", ""):
        _raise_sales_order_idempotency_conflict("scenario_tag 载体与草稿上下文不一致")
    if payload.sales_order_no_or_source_order_ref.strip() not in {
        gate_fields.get("sales_order_no", ""),
        gate_fields.get("source_order_ref", ""),
    }:
        _raise_sales_order_idempotency_conflict("sales_order_no_or_source_order_ref 载体与草稿上下文不一致")
    try:
        data = _write_service(session).cancel_sales_order_draft(
            draft_id=draft_id,
            reason=payload.reason,
            cancelled_by=current_user.username,
        )
        session.commit()
    except SalesInventoryServiceError as exc:
        session.rollback()
        _raise_sales_inventory_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@router.get("/suppliers")
def list_suppliers(
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
        resource_type="supplier",
    )
    data = _write_service(session).list_local_suppliers(page=page, page_size=page_size)
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="supplier",
    )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    paged_items, total = _paginate_list_items(filtered, page=page, page_size=page_size)
    data.items = paged_items
    data.total = total
    return _ok(data)


@reference_local_router.get("/reference-drafts/customers")
def list_customer_reference_drafts(
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
    data = _write_service(session).list_reference_drafts(reference_type="customer", page=page, page_size=page_size)
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="customer",
    )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@reference_local_router.get("/reference-drafts/suppliers")
def list_supplier_reference_drafts(
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
        resource_type="supplier",
    )
    data = _write_service(session).list_reference_drafts(reference_type="supplier", page=page, page_size=page_size)
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="supplier",
    )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    data.items = filtered
    data.total = len(filtered)
    return _ok(data)


@reference_local_router.post("/reference-drafts/customers")
def create_customer_reference_draft(
    request: Request,
    payload: ReferenceDraftCreateRequest = Body(...),
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
    _validate_local_reference_write_gate(
        request_obj=request,
        scenario_tag=payload.scenario_tag,
        idempotency_key=payload.idempotency_key,
        company=payload.company,
        reference_type="customer",
        operation=payload.operation,
        expected_operation="create_draft",
    )
    try:
        data = _write_service(session).create_reference_draft(
            reference_type="customer",
            payload=payload,
            created_by=current_user.username,
        )
    except SalesInventoryServiceError as exc:
        session.rollback()
        _raise_sales_inventory_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _created(data)


@reference_local_router.post("/reference-drafts/suppliers")
def create_supplier_reference_draft(
    request: Request,
    payload: ReferenceDraftCreateRequest = Body(...),
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
        resource_type="supplier",
    )
    _validate_local_reference_write_gate(
        request_obj=request,
        scenario_tag=payload.scenario_tag,
        idempotency_key=payload.idempotency_key,
        company=payload.company,
        reference_type="supplier",
        operation=payload.operation,
        expected_operation="create_draft",
    )
    try:
        data = _write_service(session).create_reference_draft(
            reference_type="supplier",
            payload=payload,
            created_by=current_user.username,
        )
    except SalesInventoryServiceError as exc:
        session.rollback()
        _raise_sales_inventory_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _created(data)


@reference_local_router.post("/reference-drafts/customers/{draft_id}/deactivate")
def deactivate_customer_reference_draft(
    draft_id: int,
    request: Request,
    payload: ReferenceDraftDeactivateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _validate_local_reference_write_gate(
        request_obj=request,
        scenario_tag=payload.scenario_tag,
        idempotency_key=payload.idempotency_key,
        company=payload.company,
        reference_type="customer",
        operation=payload.operation,
        expected_operation="deactivate_draft",
        draft_id=draft_id,
    )
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="customer",
    )
    try:
        data = _write_service(session).deactivate_reference_draft(
            reference_type="customer",
            draft_id=draft_id,
            payload=payload,
            deactivated_by=current_user.username,
        )
    except SalesInventoryServiceError as exc:
        session.rollback()
        _raise_sales_inventory_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@reference_local_router.post("/reference-drafts/suppliers/{draft_id}/deactivate")
def deactivate_supplier_reference_draft(
    draft_id: int,
    request: Request,
    payload: ReferenceDraftDeactivateRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _validate_local_reference_write_gate(
        request_obj=request,
        scenario_tag=payload.scenario_tag,
        idempotency_key=payload.idempotency_key,
        company=payload.company,
        reference_type="supplier",
        operation=payload.operation,
        expected_operation="deactivate_draft",
        draft_id=draft_id,
    )
    action = SALES_INVENTORY_READ
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=action,
        module="sales_inventory",
        resource_type="supplier",
    )
    try:
        data = _write_service(session).deactivate_reference_draft(
            reference_type="supplier",
            draft_id=draft_id,
            payload=payload,
            deactivated_by=current_user.username,
        )
    except SalesInventoryServiceError as exc:
        session.rollback()
        _raise_sales_inventory_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


if _is_local_reference_route_enabled():
    router.include_router(reference_local_router)


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


@router.get("/customer-return-applications")
def get_customer_return_applications(
    request: Request,
    application_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    application_status: str | None = Query(default=None),
    approval_status: str | None = Query(default=None),
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
    data = _service(request).get_customer_return_applications(
        application_no=_scope_text(application_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        application_status=_scope_text(application_status),
        approval_status=_scope_text(approval_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/customer-return-inbound")
def get_customer_return_inbound(
    request: Request,
    inbound_no: str | None = Query(default=None),
    application_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    inbound_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
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
    data = _service(request).get_customer_return_inbound(
        inbound_no=_scope_text(inbound_no),
        application_no=_scope_text(application_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        inbound_status=_scope_text(inbound_status),
        review_status=_scope_text(review_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-other-outbound")
def get_finished_goods_other_outbound(
    request: Request,
    outbound_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    outbound_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
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
    data = _service(request).get_finished_goods_other_outbound(
        outbound_no=_scope_text(outbound_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        outbound_status=_scope_text(outbound_status),
        review_status=_scope_text(review_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-count")
def get_finished_goods_count(
    request: Request,
    count_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    count_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
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
    data = _service(request).get_finished_goods_count(
        count_no=_scope_text(count_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        count_status=_scope_text(count_status),
        review_status=_scope_text(review_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-adjustment")
def get_finished_goods_adjustment(
    request: Request,
    adjustment_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    adjustment_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
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
    data = _service(request).get_finished_goods_adjustment(
        adjustment_no=_scope_text(adjustment_no),
        item_code=_scope_text(item_code),
        warehouse=_scope_text(warehouse),
        adjustment_status=_scope_text(adjustment_status),
        review_status=_scope_text(review_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-transfer")
def get_finished_goods_transfer(
    request: Request,
    transfer_no: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    source_warehouse: str | None = Query(default=None),
    target_warehouse: str | None = Query(default=None),
    transfer_status: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
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
    data = _service(request).get_finished_goods_transfer(
        transfer_no=_scope_text(transfer_no),
        item_code=_scope_text(item_code),
        source_warehouse=_scope_text(source_warehouse),
        target_warehouse=_scope_text(target_warehouse),
        transfer_status=_scope_text(transfer_status),
        review_status=_scope_text(review_status),
        keyword=_scope_text(keyword),
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
    )
    data.items = [item for item in data.items if _scope_allowed(item, permissions)]
    data.total = len(data.items)
    return _ok(data)


@router.get("/stock-ledger")
def list_stock_ledger_catalog(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
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
    )
    permissions = _get_read_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        resource_type="stock_ledger_entry",
    )
    permission_service.ensure_resource_scope_permission(
        current_user=current_user,
        request_obj=request,
        module="sales_inventory",
        action=action,
        resource_scope={"company": company, "warehouse": warehouse},
        required_fields=(),
        resource_type="stock_ledger_entry",
        enforce_action=False,
        user_permissions=permissions,
    )
    # Route-parity readonly probe entrypoint. Keep GET-only and side-effect free.
    return _ok({"items": [], "total": 0, "page": page, "page_size": page_size, "dropped_count": 0})


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
        if _local_read_fallback_enabled(exc):
            data = _build_local_stock_summary_fallback(
                session=session,
                item_code=item_code,
                company=company,
                warehouse=warehouse,
            )
        else:
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
        if _local_read_fallback_enabled(exc):
            data = _build_local_stock_ledger_fallback(
                session=session,
                item_code=item_code,
                company=company,
                warehouse=warehouse,
                page=page,
                page_size=page_size,
            )
        else:
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
        if _local_read_fallback_enabled(exc):
            return _ok(_build_local_list_fallback(page=page, page_size=page_size))
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
        if _local_read_fallback_enabled(exc):
            data = _write_service(session).list_local_customers(page=page, page_size=page_size)
            filtered = [item for item in data.items if _scope_allowed(item, permissions)]
            paged_items, total = _paginate_list_items(filtered, page=page, page_size=page_size)
            data.items = paged_items
            data.total = total
            return _ok(data)
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="Customer",
        )
    filtered = [item for item in data.items if _scope_allowed(item, permissions)]
    paged_items, total = _paginate_list_items(filtered, page=page, page_size=page_size)
    data.items = paged_items
    data.total = total
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
        if _local_read_fallback_enabled(exc):
            data = InventoryAggregationData(
                company=company,
                item_code=item_code,
                warehouse=warehouse,
                items=[],
            )
        else:
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
    local_fulfillment = (
        _write_service(session).get_local_sales_order_fulfillment(
            company=company,
            item_code=_scope_text(item_code),
            warehouse=_scope_text(warehouse),
            item_name=_scope_text(item_name),
        )
        if _is_local_sales_order_write_enabled()
        else None
    )
    try:
        data = _service(request).get_sales_order_fulfillment(
            company=company,
            item_code=_scope_text(item_code),
            warehouse=_scope_text(warehouse),
            item_name=_scope_text(item_name),
        )
    except ERPNextAdapterException as exc:
        if (_local_read_fallback_enabled(exc) or _is_local_sales_order_write_enabled()) and local_fulfillment is not None:
            local_fulfillment.items = [item for item in local_fulfillment.items if _scope_allowed(item, permissions)]
            return _ok(local_fulfillment)
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="SalesOrder",
        )
    if local_fulfillment is not None and local_fulfillment.items:
        existing_keys = {(item.sales_order, item.item_code, item.warehouse or "") for item in data.items}
        for local_item in local_fulfillment.items:
            key = (local_item.sales_order, local_item.item_code, local_item.warehouse or "")
            if key not in existing_keys:
                data.items.append(local_item)
                existing_keys.add(key)
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
