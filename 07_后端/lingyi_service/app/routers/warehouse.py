"""FastAPI router for warehouse read-only ledger/summary/alert APIs (TASK-050A)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
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
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.auth import is_internal_worker_api_enabled
from app.core.config import warehouse_enable_stock_entry_worker_sync
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.error_codes import RESOURCE_ACCESS_DENIED
from app.core.error_codes import AUTH_FORBIDDEN
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.permissions import WAREHOUSE_ALERT_READ
from app.core.permissions import WAREHOUSE_DIAGNOSTIC
from app.core.permissions import WAREHOUSE_EXPORT
from app.core.permissions import WAREHOUSE_INVENTORY_COUNT
from app.core.permissions import WAREHOUSE_READ
from app.core.permissions import WAREHOUSE_STOCK_ENTRY_CANCEL
from app.core.permissions import WAREHOUSE_STOCK_ENTRY_DRAFT
from app.core.permissions import WAREHOUSE_STOCK_HOLD_RELEASE
from app.core.permissions import WAREHOUSE_WORKER
from app.core.permissions import get_permission_source
from app.schemas.warehouse import ApiResponse
from app.schemas.warehouse import WarehouseAlertsData
from app.schemas.warehouse import WarehouseBatchDetailData
from app.schemas.warehouse import WarehouseBatchListData
from app.schemas.warehouse import WarehouseDiagnosticData
from app.schemas.warehouse import WarehouseFactoryReturnMaterialReportData
from app.schemas.warehouse import WarehouseFactoryReturnMaterialDraftData
from app.schemas.warehouse import WarehouseFactoryReturnMaterialDraftRequest
from app.schemas.warehouse import WarehouseFinishedGoodsInboundCandidatesData
from app.schemas.warehouse import WarehouseFinishedGoodsInboundListData
from app.schemas.warehouse import WarehouseInventoryCountCancelRequest
from app.schemas.warehouse import WarehouseInventoryCountCreateRequest
from app.schemas.warehouse import WarehouseInventoryCountVarianceReviewRequest
from app.schemas.warehouse import WarehouseInventoryBalanceReconciliationListData
from app.schemas.warehouse import WarehouseMaterialHoldReleaseRequest
from app.schemas.warehouse import WarehouseMaterialRetentionReportData
from app.schemas.warehouse import WarehouseOtherInboundData
from app.schemas.warehouse import WarehousePurchaseReceiptListData
from app.schemas.warehouse import WarehousePurchaseReturnOutboundData
from app.schemas.warehouse import WarehouseSemiFinishedOutboundData
from app.schemas.warehouse import WarehouseSerialNumberDetailData
from app.schemas.warehouse import WarehouseSerialNumberListData
from app.schemas.warehouse import WarehouseStockEntryDraftCancelRequest
from app.schemas.warehouse import WarehouseStockEntryDraftCreateRequest
from app.schemas.warehouse import WarehouseStockLedgerData
from app.schemas.warehouse import WarehouseStockSummaryData
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
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.core.request_id import get_request_id_from_request
from app.core.request_id import is_request_id_valid

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])
WAREHOUSE_LOCAL_ALLOWED_DB_URL = "sqlite:///./lingyi_service.local.db"
WAREHOUSE_LOCAL_STOCK_SCENARIO_PATTERN = re.compile(r"(Z003-WAREHOUSE-\d{8}-\d{3})")
WAREHOUSE_LOCAL_COUNT_SCENARIO_PATTERN = re.compile(r"(Z002-WAREHOUSE-COUNT-\d{8}-\d{3})")
WAREHOUSE_LOCAL_STOCK_REQUEST_PATTERN = re.compile(
    r"^(Z003-WAREHOUSE-\d{8}-\d{3})-RW-([CXR])-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})-([A-F0-9]{3})$",
)
WAREHOUSE_LOCAL_COUNT_REQUEST_PATTERN = re.compile(
    r"^(Z002-WAREHOUSE-COUNT-\d{8}-\d{3})-REQ-COUNT-W([A-F0-9]{8})-D(\d{8})$",
)


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


def _normalize_iso_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = _scope_text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _normalize_decimal_text(value: Any) -> str | None:
    if value is None:
        return None
    try:
        numeric = Decimal(str(value))
    except Exception:
        return None
    normalized = format(numeric.normalize(), "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _build_carrier_code(value: Any, *, length: int = 3) -> str | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    hash_value = 2166136261
    for byte in normalized.encode("utf-8"):
        hash_value ^= byte
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return f"{hash_value:08X}"[-length:]


def _stock_entry_operation_code(value: Any) -> str | None:
    normalized = _scope_text(value)
    if normalized == "create_stock_entry_draft":
        return "C"
    if normalized == "cancel_stock_entry_draft":
        return "X"
    if normalized == "release_material_hold":
        return "R"
    return None


def _stock_entry_status_action_code(value: Any) -> str | None:
    normalized = _scope_text(value)
    if normalized == "create":
        return "C"
    if normalized == "cancel":
        return "X"
    if normalized == "release":
        return "R"
    return None


def _extract_stock_entry_request_carriers(
    value: str,
) -> tuple[str | None, str | None, str | None, str | None, str | None, str | None, str | None, str | None, str | None]:
    normalized = _scope_text(value)
    if normalized is None:
        return None, None, None, None, None, None, None, None, None
    matched = WAREHOUSE_LOCAL_STOCK_REQUEST_PATTERN.fullmatch(normalized)
    if matched is None:
        return None, None, None, None, None, None, None, None, None
    return (
        _scope_text(matched.group(1)),
        _scope_text(matched.group(2)),
        _scope_text(matched.group(3)),
        _scope_text(matched.group(4)),
        _scope_text(matched.group(5)),
        _scope_text(matched.group(6)),
        _scope_text(matched.group(7)),
        _scope_text(matched.group(8)),
        _scope_text(matched.group(9)),
    )


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


def _is_local_warehouse_write_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    db_url = os.getenv("LINGYI_DB_URL", "").strip()
    return app_env == "development" and db_url == WAREHOUSE_LOCAL_ALLOWED_DB_URL


def _is_local_warehouse_read_enabled() -> bool:
    app_env = os.getenv("APP_ENV", "").strip().lower()
    db_url = os.getenv("LINGYI_DB_URL", "").strip()
    allow_dev_auth = os.getenv("LINGYI_ALLOW_DEV_AUTH", "").strip().lower()
    return (
        app_env in {"development", "dev", "local"}
        and db_url == WAREHOUSE_LOCAL_ALLOWED_DB_URL
        and allow_dev_auth == "true"
        and get_permission_source() == "static"
    )


def _local_warehouse_read_fallback_enabled(exc: ERPNextAdapterException) -> bool:
    if exc.error_code != EXTERNAL_SERVICE_UNAVAILABLE:
        return False
    return (_is_local_warehouse_read_enabled() or _is_local_warehouse_write_enabled()) and get_permission_source() == "static"


def _match_warehouse_stock_scenario_tag(value: str) -> str | None:
    matched = WAREHOUSE_LOCAL_STOCK_SCENARIO_PATTERN.search(value)
    if matched is None:
        return None
    return matched.group(1)


def _match_warehouse_count_scenario_tag(value: str) -> str | None:
    matched = WAREHOUSE_LOCAL_COUNT_SCENARIO_PATTERN.search(value)
    if matched is None:
        return None
    return matched.group(1)


def _raise_warehouse_idempotency_conflict(message: str) -> None:
    raise HTTPException(
        status_code=409,
        detail={
            "code": "WAREHOUSE_IDEMPOTENCY_CONFLICT",
            "message": message,
            "data": {},
        },
    )


def _normalize_inventory_count_date(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    text = _scope_text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def _build_inventory_count_warehouse_carrier_code(value: str) -> str | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    hash_value = 2166136261
    for byte in normalized.encode("utf-8"):
        hash_value ^= byte
        hash_value = (hash_value * 16777619) & 0xFFFFFFFF
    return f"{hash_value:08X}"


def _build_inventory_count_date_carrier_code(value: Any) -> str | None:
    normalized = _normalize_inventory_count_date(value)
    if normalized is None:
        return None
    return normalized.replace("-", "")


def _extract_inventory_count_request_carriers(value: str) -> tuple[str | None, str | None, str | None]:
    normalized = _scope_text(value)
    if normalized is None:
        return None, None, None
    matched = WAREHOUSE_LOCAL_COUNT_REQUEST_PATTERN.fullmatch(normalized)
    if matched is None:
        return None, None, None
    return matched.group(1), _scope_text(matched.group(2)), _scope_text(matched.group(3))


def _validate_local_warehouse_write_gate(
    *,
    request_obj: Request,
    request_id: str,
    scenario_tag: str,
    operation: str,
    idempotency_key: str,
    source_ref: str,
    warehouse: str,
    item_code: str,
    quantity: Any,
    business_date: Any,
    status_action: str,
    carriers: list[str | None],
) -> str:
    if not _is_local_warehouse_write_enabled():
        _raise_warehouse_idempotency_conflict("仅允许本地开发测试库执行仓库写入")

    request_id_header = (request_obj.headers.get("X-Request-ID") or "").strip()
    if not request_id_header:
        _raise_warehouse_idempotency_conflict("request_id 不能为空")
    if not is_request_id_valid(request_id_header):
        _raise_warehouse_idempotency_conflict("request_id_pattern_invalid")

    header_tag = _match_warehouse_stock_scenario_tag(request_id_header)
    if header_tag is None:
        _raise_warehouse_idempotency_conflict("request_id 未包含合法 scenario_tag")

    normalized_request_id = _scope_text(request_id)
    if normalized_request_id is None or _match_warehouse_stock_scenario_tag(normalized_request_id) is None:
        # Browser local-dev flow may normalize request.state.request_id to generated value.
        # Carrier gate must anchor on explicit X-Request-ID header.
        normalized_request_id = request_id_header
    request_tag = _match_warehouse_stock_scenario_tag((normalized_request_id or ""))
    if request_tag is None:
        _raise_warehouse_idempotency_conflict("request_id 未包含合法 scenario_tag")
    if request_tag != header_tag:
        _raise_warehouse_idempotency_conflict("request_id 与 scenario_tag 不一致")
    if normalized_request_id != request_id_header:
        _raise_warehouse_idempotency_conflict("request_id 与 Header 不一致")

    normalized_scenario_tag = _scope_text(scenario_tag)
    normalized_idempotency_key = _scope_text(idempotency_key)
    normalized_source_ref = _scope_text(source_ref)
    normalized_warehouse = _scope_text(warehouse)
    normalized_item_code = _scope_text(item_code)
    normalized_business_date = _normalize_iso_date(business_date)
    normalized_quantity = _normalize_decimal_text(quantity)
    normalized_operation = _scope_text(operation)
    normalized_status_action = _scope_text(status_action)

    if (
        normalized_scenario_tag is None
        or normalized_idempotency_key is None
        or normalized_source_ref is None
        or normalized_warehouse is None
        or normalized_item_code is None
        or normalized_business_date is None
        or normalized_quantity is None
        or normalized_operation is None
        or normalized_status_action is None
    ):
        _raise_warehouse_idempotency_conflict("scenario_tag 业务载体缺失")

    if normalized_scenario_tag != header_tag:
        _raise_warehouse_idempotency_conflict("scenario_tag 载体与 request_id 不一致")

    (
        header_carrier_tag,
        header_operation_code,
        header_idempotency_code,
        header_source_ref_code,
        header_warehouse_code,
        header_item_code,
        header_quantity_code,
        header_date_code,
        header_status_action_code,
    ) = _extract_stock_entry_request_carriers(request_id_header)
    (
        request_carrier_tag,
        request_operation_code,
        request_idempotency_code,
        request_source_ref_code,
        request_warehouse_code,
        request_item_code,
        request_quantity_code,
        request_date_code,
        request_status_action_code,
    ) = _extract_stock_entry_request_carriers(normalized_request_id)

    if (
        header_carrier_tag is None
        or header_operation_code is None
        or header_idempotency_code is None
        or header_source_ref_code is None
        or header_warehouse_code is None
        or header_item_code is None
        or header_quantity_code is None
        or header_date_code is None
        or header_status_action_code is None
        or request_carrier_tag is None
        or request_operation_code is None
        or request_idempotency_code is None
        or request_source_ref_code is None
        or request_warehouse_code is None
        or request_item_code is None
        or request_quantity_code is None
        or request_date_code is None
        or request_status_action_code is None
    ):
        _raise_warehouse_idempotency_conflict("request_id 载体缺失或格式非法")

    if header_carrier_tag != request_carrier_tag or header_carrier_tag != normalized_scenario_tag:
        _raise_warehouse_idempotency_conflict("request_id 与 scenario_tag 不一致")
    if (
        header_operation_code != request_operation_code
        or header_idempotency_code != request_idempotency_code
        or header_source_ref_code != request_source_ref_code
        or header_warehouse_code != request_warehouse_code
        or header_item_code != request_item_code
        or header_quantity_code != request_quantity_code
        or header_date_code != request_date_code
        or header_status_action_code != request_status_action_code
    ):
        _raise_warehouse_idempotency_conflict("request_id 载体不一致")

    expected_operation_code = _stock_entry_operation_code(normalized_operation)
    expected_status_action_code = _stock_entry_status_action_code(normalized_status_action)
    expected_idempotency_code = _build_carrier_code(normalized_idempotency_key)
    expected_source_ref_code = _build_carrier_code(normalized_source_ref)
    expected_warehouse_code = _build_carrier_code(normalized_warehouse)
    expected_item_code = _build_carrier_code(normalized_item_code)
    expected_quantity_code = _build_carrier_code(normalized_quantity)
    expected_date_code = _build_carrier_code(normalized_business_date)
    expected_status_code = _build_carrier_code(expected_status_action_code)

    if (
        expected_operation_code is None
        or expected_status_action_code is None
        or expected_idempotency_code is None
        or expected_source_ref_code is None
        or expected_warehouse_code is None
        or expected_item_code is None
        or expected_quantity_code is None
        or expected_date_code is None
        or expected_status_code is None
    ):
        _raise_warehouse_idempotency_conflict("scenario_tag 业务载体缺失")

    if header_operation_code != expected_operation_code:
        _raise_warehouse_idempotency_conflict("operation 载体与业务载体不一致")
    if header_idempotency_code != expected_idempotency_code:
        _raise_warehouse_idempotency_conflict("idempotency_key 载体与业务载体不一致")
    if header_source_ref_code != expected_source_ref_code:
        _raise_warehouse_idempotency_conflict("source_ref 载体与业务载体不一致")
    if header_warehouse_code != expected_warehouse_code:
        _raise_warehouse_idempotency_conflict("warehouse 载体与业务载体不一致")
    if header_item_code != expected_item_code:
        _raise_warehouse_idempotency_conflict("item_code 载体与业务载体不一致")
    if header_quantity_code != expected_quantity_code:
        _raise_warehouse_idempotency_conflict("quantity 载体与业务载体不一致")
    if header_date_code != expected_date_code:
        _raise_warehouse_idempotency_conflict("business_date 载体与业务载体不一致")
    if header_status_action_code != expected_status_code:
        _raise_warehouse_idempotency_conflict("status_action 载体与业务载体不一致")

    carrier_tags: list[str] = []
    for raw_value in carriers:
        normalized = _scope_text(raw_value)
        if normalized is None:
            _raise_warehouse_idempotency_conflict("scenario_tag 载体缺失")
        scenario_tag = _match_warehouse_stock_scenario_tag(normalized)
        if scenario_tag is None:
            _raise_warehouse_idempotency_conflict("scenario_tag 载体缺失或格式非法")
        carrier_tags.append(scenario_tag)

    if len(set(carrier_tags)) != 1:
        _raise_warehouse_idempotency_conflict("scenario_tag 载体不一致")
    if carrier_tags[0] != header_tag:
        _raise_warehouse_idempotency_conflict("scenario_tag 载体与 request_id 不一致")
    return normalized_scenario_tag


def _validate_local_warehouse_inventory_count_gate(
    *,
    request_obj: Request,
    carriers: list[str | None],
    expected_warehouse: str | None,
    expected_count_date: Any,
) -> str:
    if not _is_local_warehouse_write_enabled():
        raise HTTPException(
            status_code=403,
            detail={
                "code": AUTH_FORBIDDEN,
                "message": "仅允许本地开发测试库执行仓库写入",
                "data": {},
            },
        )

    request_id_header = (request_obj.headers.get("X-Request-ID") or "").strip()
    if not request_id_header:
        _raise_warehouse_idempotency_conflict("request_id 不能为空")

    header_tag = _match_warehouse_count_scenario_tag(request_id_header)
    if header_tag is None:
        _raise_warehouse_idempotency_conflict("request_id 未包含合法 scenario_tag")

    request_id = get_request_id_from_request(request_obj).strip()
    request_tag = _match_warehouse_count_scenario_tag(request_id)
    if request_tag is None:
        _raise_warehouse_idempotency_conflict("request_id 未包含合法 scenario_tag")
    if request_tag != header_tag:
        _raise_warehouse_idempotency_conflict("request_id 与 scenario_tag 不一致")

    header_carrier_tag, header_warehouse_code, header_count_date_code = _extract_inventory_count_request_carriers(
        request_id_header,
    )
    if header_warehouse_code is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失或格式非法")
    if header_count_date_code is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失或格式非法")
    if header_carrier_tag != header_tag:
        _raise_warehouse_idempotency_conflict("request_id 与 scenario_tag 不一致")

    request_carrier_tag, request_warehouse_code, request_count_date_code = _extract_inventory_count_request_carriers(
        request_id,
    )
    if request_warehouse_code is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失或格式非法")
    if request_count_date_code is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失或格式非法")
    if request_carrier_tag != header_carrier_tag:
        _raise_warehouse_idempotency_conflict("request_id 与 scenario_tag 不一致")
    if request_warehouse_code != header_warehouse_code:
        _raise_warehouse_idempotency_conflict("warehouse 载体与 request_id 不一致")
    if request_count_date_code != header_count_date_code:
        _raise_warehouse_idempotency_conflict("count_date 载体与 request_id 不一致")

    normalized_expected_warehouse = _scope_text(expected_warehouse)
    if normalized_expected_warehouse is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失")
    normalized_expected_warehouse_code = _build_inventory_count_warehouse_carrier_code(normalized_expected_warehouse)
    if normalized_expected_warehouse_code is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失")
    normalized_expected_count_date_code = _build_inventory_count_date_carrier_code(expected_count_date)
    if normalized_expected_count_date_code is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失")
    if header_warehouse_code != normalized_expected_warehouse_code:
        _raise_warehouse_idempotency_conflict("warehouse 载体与业务载体不一致")
    if header_count_date_code != normalized_expected_count_date_code:
        _raise_warehouse_idempotency_conflict("count_date 载体与业务载体不一致")

    carrier_tags: list[str] = []
    for raw_value in carriers:
        normalized = _scope_text(raw_value)
        if normalized is None:
            _raise_warehouse_idempotency_conflict("scenario_tag 载体缺失")
        scenario_tag = _match_warehouse_count_scenario_tag(normalized)
        if scenario_tag is None:
            _raise_warehouse_idempotency_conflict("scenario_tag 载体缺失或格式非法")
        carrier_tags.append(scenario_tag)

    if len(set(carrier_tags)) != 1:
        _raise_warehouse_idempotency_conflict("scenario_tag 载体不一致")
    if carrier_tags[0] != header_tag:
        _raise_warehouse_idempotency_conflict("scenario_tag 载体与 request_id 不一致")
    return header_tag


def _build_local_stock_ledger_fallback(
    *,
    session: Session,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    from_date: date | None = None,
    to_date: date | None = None,
    page: int,
    page_size: int,
) -> WarehouseStockLedgerData:
    return WarehouseService(session=session).list_local_stock_ledger(
        company=_scope_text(company),
        warehouse=_scope_text(warehouse),
        item_code=_scope_text(item_code),
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


def _build_local_stock_summary_fallback(
    *,
    session: Session,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
) -> WarehouseStockSummaryData:
    return WarehouseService(session=session).get_local_stock_summary(
        company=_scope_text(company),
        warehouse=_scope_text(warehouse),
        item_code=_scope_text(item_code),
    )


def _build_local_factory_return_material_report(
    *,
    session: Session,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    status: str | None,
) -> WarehouseFactoryReturnMaterialReportData:
    return WarehouseService(session=session).list_local_factory_return_material_report(
        company=_scope_text(company),
        warehouse=_scope_text(warehouse),
        item_code=_scope_text(item_code),
        status=_scope_text(status),
    )


def _build_local_material_retention_report(
    *,
    session: Session,
    company: str | None,
    warehouse: str | None,
    keyword: str | None,
    min_retention_days: int | None,
    as_of_date: date | None,
) -> WarehouseMaterialRetentionReportData:
    return WarehouseService(session=session).list_local_material_retention_report(
        company=_scope_text(company),
        warehouse=_scope_text(warehouse),
        keyword=_scope_text(keyword),
        min_retention_days=min_retention_days,
        as_of_date=as_of_date,
    )


def _normalize_alert_type_for_fallback(alert_type: str | None) -> str | None:
    normalized = _scope_text(alert_type)
    if normalized is None:
        return None
    normalized = normalized.lower()
    supported = {"low_stock", "below_safety", "overstock", "stale_stock"}
    if normalized not in supported:
        return None
    return normalized


def _build_local_alerts_fallback(
    *,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    alert_type: str | None,
) -> WarehouseAlertsData:
    return WarehouseAlertsData(
        company=_scope_text(company),
        warehouse=_scope_text(warehouse),
        item_code=_scope_text(item_code),
        alert_type=_normalize_alert_type_for_fallback(alert_type),
        items=[],
    )


def _build_local_batches_fallback(
    *,
    company: str | None,
    warehouse: str | None,
    item_code: str | None,
    batch_no: str | None,
) -> WarehouseBatchListData:
    return WarehouseBatchListData(
        company=_scope_text(company),
        warehouse=_scope_text(warehouse),
        item_code=_scope_text(item_code),
        batch_no=_scope_text(batch_no),
        total=0,
        items=[],
    )


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


def _record_inventory_count_success(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    data: Any,
    before_data: dict[str, Any] | None = None,
) -> None:
    AuditService(session).record_success(
        module="warehouse",
        action=WAREHOUSE_INVENTORY_COUNT,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type="warehouse_inventory_count",
        resource_id=int(data.id),
        resource_no=str(data.count_no),
        before_data=before_data,
        after_data=data.model_dump(mode="json"),
        context=AuditContext.from_request(request),
    )


def _record_inventory_count_failure(
    *,
    session: Session,
    request: Request,
    current_user: CurrentUser,
    error_code: str,
    before_data: dict[str, Any] | None = None,
    resource_id: int | None = None,
    resource_no: str | None = None,
) -> None:
    AuditService(session).record_failure(
        module="warehouse",
        action=WAREHOUSE_INVENTORY_COUNT,
        operator=current_user.username,
        operator_roles=current_user.roles,
        resource_type="warehouse_inventory_count",
        resource_id=resource_id,
        resource_no=resource_no,
        before_data=before_data,
        after_data=None,
        error_code=error_code,
        context=AuditContext.from_request(request),
    )


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


def _draft_scope_allowed(
    *,
    permission_service: PermissionService,
    current_user: CurrentUser,
    request: Request,
    action: str,
    draft_data: dict[str, Any],
    permissions: UserPermissionResult | None,
) -> bool:
    try:
        _check_draft_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            draft_data=draft_data,
            user_permissions=permissions,
        )
        return True
    except HTTPException:
        return False


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
    page_size: int = Query(default=20, ge=1, le=100),
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

    data = _build_local_stock_ledger_fallback(
        session=session,
        company=company,
        warehouse=warehouse,
        item_code=item_code,
        from_date=parsed_from_date,
        to_date=parsed_to_date,
        page=page,
        page_size=page_size,
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

    data = _build_local_stock_summary_fallback(
        session=session,
        company=company,
        warehouse=warehouse,
        item_code=item_code,
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


@router.get("/purchase-receipts")
def list_purchase_receipts(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    material_item_code: str | None = Query(default=None),
    purchase_no: str | None = Query(default=None),
    supplier_name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
        resource_type="warehouse_purchase_receipt",
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
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)
    try:
        data = _write_service(session).list_local_purchase_receipts(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            material_item_code=material_item_code,
            purchase_no=purchase_no,
            supplier_name=supplier_name,
            status=status,
            page=page,
            page_size=page_size,
        )
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
    data.items = [
        row
        for row in data.items
        if _scope_allowed(company=row.company, warehouse=row.warehouse, item_code=row.item_code, permissions=permissions)
    ]
    data.total = len(data.items)
    return _ok(data)


@router.get("/finished-goods-inbound")
def list_finished_goods_inbound(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    reserve_status: str | None = Query(default=None),
    inbound_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
            warehouse=warehouse,
            item_code=item_code,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)
    try:
        data = _write_service(session).list_local_finished_goods_inbound(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            reserve_status=reserve_status,
            inbound_status=inbound_status,
            page=page,
            page_size=page_size,
        )
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
    data.items = [
        row
        for row in data.items
        if _scope_allowed(company=row.company, warehouse=row.warehouse, item_code=row.item_code, permissions=permissions)
    ]
    data.total = len(data.items)
    return _ok(data)


@router.get("/inventory-balance-reconciliation")
def list_inventory_balance_reconciliation(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
        resource_type="warehouse_inventory_balance_reconciliation",
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
        data = _write_service(session).list_local_inventory_balance_reconciliation(
            company=company,
            warehouse=warehouse,
            item_code=item_code,
            status=status,
            page=page,
            page_size=page_size,
        )
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
    data.items = [
        row
        for row in data.items
        if _scope_allowed(company=row.company, warehouse=row.warehouse, item_code=row.item_code, permissions=permissions)
    ]
    data.total = len(data.items)
    return _ok(data)


@router.get("/other-inbound")
def list_other_inbound(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
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
        resource_type="warehouse_other_inbound",
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

    normalized_status = _scope_text(status)
    if normalized_status is not None and normalized_status not in {"pending", "received", "closed"}:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUERY_PARAMETER", "message": "status 参数非法", "data": None},
        )

    try:
        data: WarehouseOtherInboundData = _read_service(request).list_other_inbound(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            status=normalized_status,
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="WarehouseOtherInbound",
        )

    data.items = [
        row
        for row in data.items
        if _scope_allowed(
            company=data.company,
            warehouse=row.warehouse,
            item_code=row.material_code,
            permissions=permissions,
        )
    ]
    return _ok(data)


@router.get("/purchase-return-outbound")
def list_purchase_return_outbound(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
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
        resource_type="warehouse_purchase_return_outbound",
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

    normalized_status = _scope_text(status)
    if normalized_status is not None and normalized_status not in {"pending", "returned", "closed"}:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUERY_PARAMETER", "message": "status 参数非法", "data": None},
        )

    try:
        data: WarehousePurchaseReturnOutboundData = _read_service(request).list_purchase_return_outbound(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            status=normalized_status,
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="WarehousePurchaseReturnOutbound",
        )

    data.items = [
        row
        for row in data.items
        if _scope_allowed(
            company=data.company,
            warehouse=row.warehouse,
            item_code=row.material_code,
            permissions=permissions,
        )
    ]
    return _ok(data)


@router.get("/factory-return-material-report")
def list_factory_return_material_report(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
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
        resource_type="warehouse_factory_return_material_report",
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

    normalized_status = _scope_text(status)
    if normalized_status is not None and normalized_status not in {"pending", "confirmed", "closed"}:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUERY_PARAMETER", "message": "status 参数非法", "data": None},
        )

    data = _build_local_factory_return_material_report(
        session=session,
        company=company,
        warehouse=warehouse,
        item_code=item_code,
        status=normalized_status,
    )

    data.items = [
        row
        for row in data.items
        if _scope_allowed(
            company=data.company,
            warehouse=row.warehouse,
            item_code=row.material_code,
            permissions=permissions,
        )
    ]
    return _ok(data)


@router.post("/factory-return-material-report/{report_no}/return-draft")
def create_factory_return_material_draft(
    report_no: str,
    request: Request,
    payload: WarehouseFactoryReturnMaterialDraftRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_STOCK_ENTRY_DRAFT
    permission_service = PermissionService(session=session)
    audit = AuditService(session)
    _require_warehouse_action(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse_factory_return_material_report",
    )
    permissions = _get_user_permissions(
        permission_service=permission_service,
        current_user=current_user,
        request=request,
        action=action,
        resource_type="warehouse",
    )

    service = _write_service(session)
    try:
        current_report = service.list_local_factory_return_material_report(
            company=payload.company,
            warehouse=None,
            item_code=None,
            status=None,
        )
        before_item = next((item for item in current_report.items if item.report_no == report_no), None)
        if before_item is None:
            raise WarehouseServiceError(404, "WAREHOUSE_RETURN_REPORT_NOT_FOUND", "应退料报表记录不存在")
        return_qty = payload.quantity if payload.quantity is not None else before_item.pending_qty
        _validate_local_warehouse_write_gate(
            request_obj=request,
            request_id=get_request_id_from_request(request).strip(),
            scenario_tag=payload.scenario_tag,
            operation="create_stock_entry_draft",
            idempotency_key=payload.idempotency_key,
            source_ref=payload.source_ref,
            warehouse=before_item.warehouse,
            item_code=before_item.material_code,
            quantity=return_qty,
            business_date=payload.business_date,
            status_action="create",
            carriers=[payload.scenario_tag, payload.idempotency_key, payload.source_ref],
        )
        _ensure_stock_entry_scope(
            permission_service=permission_service,
            current_user=current_user,
            request=request,
            action=action,
            company=payload.company,
            warehouse=before_item.warehouse,
            item_code=before_item.material_code,
            user_permissions=permissions,
        )
        data: WarehouseFactoryReturnMaterialDraftData = service.create_factory_return_material_draft(
            report_no=report_no,
            payload=payload,
            current_user=current_user.username,
        )
        audit.record_success(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_factory_return_material_report",
            resource_id=int(data.draft.id),
            resource_no=report_no,
            before_data=before_item.model_dump(mode="json"),
            after_data=data.model_dump(mode="json"),
            context=AuditContext.from_request(request),
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        AuditService(session).record_failure(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_factory_return_material_report",
            resource_id=None,
            resource_no=report_no,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        _raise_service_error(exc)
    except HTTPException:
        session.rollback()
        raise
    return _created(data)


@router.get("/material-retention-report")
def list_material_retention_report(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    min_retention_days: int | None = Query(default=None, ge=0),
    to_date: str | None = Query(default=None),
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
        resource_type="warehouse_material_retention_report",
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
            item_code=None,
            user_permissions=permissions,
        )
    except HTTPException as exc:
        _raise_scope_denied_as_forbidden(exc)

    parsed_to_date = _parse_optional_date(to_date, "to_date")
    data = _build_local_material_retention_report(
        session=session,
        company=company,
        warehouse=warehouse,
        keyword=keyword,
        min_retention_days=min_retention_days,
        as_of_date=parsed_to_date,
    )

    data.items = [
        row
        for row in data.items
        if _scope_allowed(
            company=data.company,
            warehouse=row.warehouse,
            item_code=row.material_code,
            permissions=permissions,
        )
    ]
    return _ok(data)


@router.get("/semi-finished-outbound")
def list_semi_finished_outbound(
    request: Request,
    company: str | None = Query(default=None),
    warehouse: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
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
        resource_type="warehouse_semi_finished_outbound",
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

    normalized_status = _scope_text(status)
    if normalized_status is not None and normalized_status not in {"pending", "confirmed", "closed"}:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_QUERY_PARAMETER", "message": "status 参数非法", "data": None},
        )

    try:
        data: WarehouseSemiFinishedOutboundData = _read_service(request).list_semi_finished_outbound(
            company=_scope_text(company),
            warehouse=_scope_text(warehouse),
            item_code=_scope_text(item_code),
            status=normalized_status,
        )
    except ERPNextAdapterException as exc:
        _handle_erpnext_error(
            exc=exc,
            permission_service=permission_service,
            request=request,
            current_user=current_user,
            action=action,
            resource_type="WarehouseSemiFinishedOutbound",
        )

    data.items = [
        row
        for row in data.items
        if _scope_allowed(
            company=data.company,
            warehouse=row.warehouse,
            item_code=row.semi_finished_code,
            permissions=permissions,
        )
    ]
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
        if _local_warehouse_read_fallback_enabled(exc):
            data = _build_local_alerts_fallback(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                alert_type=alert_type,
            )
        else:
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
        if _local_warehouse_read_fallback_enabled(exc):
            data = _build_local_batches_fallback(
                company=company,
                warehouse=warehouse,
                item_code=item_code,
                batch_no=batch_no,
            )
        else:
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


@router.get("/stock-entry-drafts")
def list_stock_entry_drafts(
    request: Request,
    company: str | None = Query(default=None),
    purpose: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
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
        data = _write_service(session).list_stock_entry_drafts(
            company=company,
            purpose=purpose,
            source_type=source_type,
            status=status,
            keyword=keyword,
            page=page,
            page_size=page_size,
        )
        data.items = [
            row
            for row in data.items
            if _draft_scope_allowed(
                permission_service=permission_service,
                current_user=current_user,
                request=request,
                action=action,
                draft_data=row.model_dump(mode="json"),
                permissions=permissions,
            )
        ]
        data.total = len(data.items)
    except WarehouseServiceError as exc:
        _raise_service_error(exc)
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
    audit = AuditService(session)
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
    payload_purpose = _scope_text(payload.purpose)
    payload_warehouse = _scope_text(payload.warehouse)
    payload_source_warehouse = _scope_text(payload.source_warehouse)
    payload_target_warehouse = _scope_text(payload.target_warehouse)
    draft_warehouse = payload_warehouse or payload_source_warehouse or payload_target_warehouse
    first_item_code = _scope_text(payload.item_code) or _scope_text(payload.items[0].item_code)
    total_qty = sum(Decimal(str(item.qty)) for item in payload.items)
    if _scope_text(payload.source_ref) != _scope_text(payload.source_id):
        _raise_warehouse_idempotency_conflict("source_ref 载体与业务载体不一致")
    if payload_purpose == "Material Transfer":
        if not payload_warehouse or payload_warehouse not in {payload_source_warehouse, payload_target_warehouse}:
            _raise_warehouse_idempotency_conflict("warehouse 载体与调仓源/目标仓不一致")
    else:
        if payload_source_warehouse and payload_warehouse != payload_source_warehouse:
            _raise_warehouse_idempotency_conflict("warehouse 载体与业务载体不一致")
        if payload_target_warehouse and payload_warehouse != payload_target_warehouse:
            _raise_warehouse_idempotency_conflict("warehouse 载体与业务载体不一致")
    if _scope_text(payload.operation) != "create_stock_entry_draft":
        _raise_warehouse_idempotency_conflict("operation 载体与业务模式不一致")
    if _scope_text(payload.status_action) != "create":
        _raise_warehouse_idempotency_conflict("status_action 载体与业务模式不一致")
    _validate_local_warehouse_write_gate(
        request_obj=request,
        request_id=get_request_id_from_request(request).strip(),
        scenario_tag=payload.scenario_tag,
        operation=payload.operation,
        idempotency_key=payload.idempotency_key,
        source_ref=payload.source_ref,
        warehouse=draft_warehouse or "",
        item_code=first_item_code or "",
        quantity=payload.quantity,
        business_date=payload.business_date,
        status_action=payload.status_action,
        carriers=[payload.scenario_tag, payload.idempotency_key, payload.source_ref, payload.source_id],
    )
    if first_item_code is None or first_item_code != _scope_text(payload.items[0].item_code):
        _raise_warehouse_idempotency_conflict("item_code 载体与业务载体不一致")
    normalized_payload_qty = _normalize_decimal_text(payload.quantity)
    normalized_total_qty = _normalize_decimal_text(total_qty)
    if normalized_payload_qty is None or normalized_total_qty is None or normalized_payload_qty != normalized_total_qty:
        _raise_warehouse_idempotency_conflict("quantity 载体与业务载体不一致")
    normalized_payload_date = _normalize_iso_date(payload.business_date)
    if normalized_payload_date is None:
        _raise_warehouse_idempotency_conflict("business_date 载体缺失或格式非法")
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
        audit.record_success(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_stock_entry_draft",
            resource_id=int(data.id),
            resource_no=str(data.id),
            before_data=None,
            after_data=data.model_dump(mode="json"),
            context=AuditContext.from_request(request),
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        AuditService(session).record_failure(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_stock_entry_draft",
            resource_id=None,
            resource_no=payload.source_id,
            before_data=None,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
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
    audit = AuditService(session)
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

    _validate_local_warehouse_write_gate(
        request_obj=request,
        request_id=get_request_id_from_request(request).strip(),
        scenario_tag=payload.scenario_tag,
        operation=payload.operation,
        idempotency_key=payload.idempotency_key,
        source_ref=payload.source_ref,
        warehouse=payload.warehouse,
        item_code=payload.item_code,
        quantity=payload.quantity,
        business_date=payload.business_date,
        status_action=payload.status_action,
        carriers=[payload.scenario_tag, payload.idempotency_key, payload.source_ref],
    )
    if _scope_text(payload.operation) != "cancel_stock_entry_draft":
        _raise_warehouse_idempotency_conflict("operation 载体与业务模式不一致")
    if _scope_text(payload.status_action) != "cancel":
        _raise_warehouse_idempotency_conflict("status_action 载体与业务模式不一致")
    before_idempotency_key = _scope_text(before_data.get("idempotency_key"))
    before_source_ref = _scope_text(before_data.get("source_id"))
    before_warehouse = _scope_text(before_data.get("source_warehouse")) or _scope_text(before_data.get("target_warehouse"))
    before_items = before_data.get("items") or []
    if not isinstance(before_items, list) or len(before_items) == 0:
        _raise_warehouse_idempotency_conflict("item_code 载体缺失")
    before_item_code = _scope_text(before_items[0].get("item_code")) if isinstance(before_items[0], dict) else None
    before_total_qty = sum(Decimal(str(item.get("qty", 0))) for item in before_items if isinstance(item, dict))
    if before_idempotency_key is None or _scope_text(payload.idempotency_key) != before_idempotency_key:
        _raise_warehouse_idempotency_conflict("idempotency_key 载体与业务载体不一致")
    if before_source_ref is None or _scope_text(payload.source_ref) != before_source_ref:
        _raise_warehouse_idempotency_conflict("source_ref 载体与业务载体不一致")
    if before_warehouse is None or _scope_text(payload.warehouse) != before_warehouse:
        _raise_warehouse_idempotency_conflict("warehouse 载体与业务载体不一致")
    if before_item_code is None or _scope_text(payload.item_code) != before_item_code:
        _raise_warehouse_idempotency_conflict("item_code 载体与业务载体不一致")
    normalized_payload_qty = _normalize_decimal_text(payload.quantity)
    normalized_before_qty = _normalize_decimal_text(before_total_qty)
    if normalized_payload_qty is None or normalized_before_qty is None or normalized_payload_qty != normalized_before_qty:
        _raise_warehouse_idempotency_conflict("quantity 载体与业务载体不一致")
    if _normalize_iso_date(payload.business_date) is None:
        _raise_warehouse_idempotency_conflict("business_date 载体缺失或格式非法")

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
        audit.record_success(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_stock_entry_draft",
            resource_id=int(data.id),
            resource_no=str(data.id),
            before_data=before_data,
            after_data=data.model_dump(mode="json"),
            context=AuditContext.from_request(request),
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        AuditService(session).record_failure(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_stock_entry_draft",
            resource_id=draft_id,
            resource_no=str(draft_id),
            before_data=before_data,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
        _raise_service_error(exc)
    except Exception:
        session.rollback()
        raise
    return _ok(data)


@router.post("/stock-entry-drafts/{draft_id}/release-hold")
def release_material_hold_draft(
    draft_id: int,
    request: Request,
    payload: WarehouseMaterialHoldReleaseRequest = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = WAREHOUSE_STOCK_HOLD_RELEASE
    permission_service = PermissionService(session=session)
    audit = AuditService(session)
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

    _validate_local_warehouse_write_gate(
        request_obj=request,
        request_id=get_request_id_from_request(request).strip(),
        scenario_tag=payload.scenario_tag,
        operation=payload.operation,
        idempotency_key=payload.idempotency_key,
        source_ref=payload.source_ref,
        warehouse=payload.warehouse,
        item_code=payload.item_code,
        quantity=payload.quantity,
        business_date=payload.business_date,
        status_action=payload.status_action,
        carriers=[payload.scenario_tag, payload.idempotency_key, payload.source_ref],
    )
    before_idempotency_key = _scope_text(before_data.get("idempotency_key"))
    before_source_ref = _scope_text(before_data.get("source_id"))
    before_source_type = _scope_text(before_data.get("source_type"))
    before_purpose = _scope_text(before_data.get("purpose"))
    before_warehouse = _scope_text(before_data.get("source_warehouse")) or _scope_text(before_data.get("target_warehouse"))
    before_items = before_data.get("items") or []
    if not isinstance(before_items, list) or len(before_items) == 0:
        _raise_warehouse_idempotency_conflict("item_code 载体缺失")
    before_item_code = _scope_text(before_items[0].get("item_code")) if isinstance(before_items[0], dict) else None
    before_total_qty = sum(Decimal(str(item.get("qty", 0))) for item in before_items if isinstance(item, dict))
    if before_source_type != "material_hold" or before_purpose != "Material Issue":
        _raise_warehouse_idempotency_conflict("仅 material_hold 扣仓草稿允许释放")
    if before_idempotency_key is None or _scope_text(payload.idempotency_key) != before_idempotency_key:
        _raise_warehouse_idempotency_conflict("idempotency_key 载体与业务载体不一致")
    if before_source_ref is None or _scope_text(payload.source_ref) != before_source_ref:
        _raise_warehouse_idempotency_conflict("source_ref 载体与业务载体不一致")
    if before_warehouse is None or _scope_text(payload.warehouse) != before_warehouse:
        _raise_warehouse_idempotency_conflict("warehouse 载体与业务载体不一致")
    if before_item_code is None or _scope_text(payload.item_code) != before_item_code:
        _raise_warehouse_idempotency_conflict("item_code 载体与业务载体不一致")
    normalized_payload_qty = _normalize_decimal_text(payload.quantity)
    normalized_before_qty = _normalize_decimal_text(before_total_qty)
    if normalized_payload_qty is None or normalized_before_qty is None or normalized_payload_qty != normalized_before_qty:
        _raise_warehouse_idempotency_conflict("quantity 载体与业务载体不一致")
    if _normalize_iso_date(payload.business_date) is None:
        _raise_warehouse_idempotency_conflict("business_date 载体缺失或格式非法")

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
        data = _write_service(session).release_material_hold_draft(
            draft_id=draft_id,
            reason=payload.reason,
            released_by=current_user.username,
        )
        audit.record_success(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_stock_entry_draft",
            resource_id=int(data.id),
            resource_no=str(data.id),
            before_data=before_data,
            after_data=data.model_dump(mode="json"),
            context=AuditContext.from_request(request),
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        AuditService(session).record_failure(
            module="warehouse",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="warehouse_stock_entry_draft",
            resource_id=draft_id,
            resource_no=str(draft_id),
            before_data=before_data,
            after_data=None,
            error_code=exc.code,
            context=AuditContext.from_request(request),
        )
        session.commit()
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
    if not payload.dry_run and not warehouse_enable_stock_entry_worker_sync():
        permission_service.record_security_denial(
            request_obj=request,
            current_user=current_user,
            action=action,
            resource_type="warehouse_stock_entry_worker",
            resource_no="run-once",
            deny_reason="仓库 Stock Entry ERP 同步未启用",
            event_type=INTERNAL_API_DISABLED,
            module="warehouse",
        )
        raise HTTPException(
            status_code=status_of(INTERNAL_API_DISABLED),
            detail={"code": INTERNAL_API_DISABLED, "message": "仓库 Stock Entry ERP 同步未启用", "data": None},
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
    _validate_local_warehouse_inventory_count_gate(
        request_obj=request,
        carriers=[payload.idempotency_key, payload.source_ref],
        expected_warehouse=payload.warehouse,
        expected_count_date=payload.count_date,
    )
    if _scope_text(payload.warehouse) is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失")
    if payload.count_date is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失")
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
        _record_inventory_count_success(session=session, request=request, current_user=current_user, data=data)
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _record_inventory_count_failure(
            session=session,
            request=request,
            current_user=current_user,
            error_code=exc.code,
            resource_no=payload.source_ref,
        )
        session.commit()
        _raise_service_error(exc)
    except IntegrityError:
        session.rollback()
        try:
            data = _write_service(session).recover_inventory_count_create_replay(payload=payload)
            if data is None:
                raise WarehouseServiceError(500, "DATABASE_WRITE_FAILED", "盘点单写入冲突，且未找到可重放记录")
            _record_inventory_count_success(session=session, request=request, current_user=current_user, data=data)
            session.commit()
        except WarehouseServiceError as recovery_exc:
            session.rollback()
            _record_inventory_count_failure(
                session=session,
                request=request,
                current_user=current_user,
                error_code=recovery_exc.code,
                resource_no=payload.source_ref,
            )
            session.commit()
            _raise_service_error(recovery_exc)
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
    _validate_local_warehouse_inventory_count_gate(
        request_obj=request,
        carriers=[str(before_data.get("count_no") or "")],
        expected_warehouse=str(before_data.get("warehouse") or ""),
        expected_count_date=before_data.get("count_date"),
    )
    if _scope_text(str(before_data.get("warehouse") or "")) is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失")
    if _scope_text(str(before_data.get("count_date") or "")) is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失")

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
        _record_inventory_count_success(
            session=session,
            request=request,
            current_user=current_user,
            data=data,
            before_data=before_data,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _record_inventory_count_failure(
            session=session,
            request=request,
            current_user=current_user,
            error_code=exc.code,
            before_data=before_data,
            resource_id=count_id,
            resource_no=str(before_data.get("count_no") or ""),
        )
        session.commit()
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
    _validate_local_warehouse_inventory_count_gate(
        request_obj=request,
        carriers=[str(before_data.get("count_no") or "")],
        expected_warehouse=str(before_data.get("warehouse") or ""),
        expected_count_date=before_data.get("count_date"),
    )
    if _scope_text(str(before_data.get("warehouse") or "")) is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失")
    if _scope_text(str(before_data.get("count_date") or "")) is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失")

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
        _record_inventory_count_success(
            session=session,
            request=request,
            current_user=current_user,
            data=data,
            before_data=before_data,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _record_inventory_count_failure(
            session=session,
            request=request,
            current_user=current_user,
            error_code=exc.code,
            before_data=before_data,
            resource_id=count_id,
            resource_no=str(before_data.get("count_no") or ""),
        )
        session.commit()
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
    _validate_local_warehouse_inventory_count_gate(
        request_obj=request,
        carriers=[str(before_data.get("count_no") or "")],
        expected_warehouse=str(before_data.get("warehouse") or ""),
        expected_count_date=before_data.get("count_date"),
    )
    if _scope_text(str(before_data.get("warehouse") or "")) is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失")
    if _scope_text(str(before_data.get("count_date") or "")) is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失")

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
        _record_inventory_count_success(
            session=session,
            request=request,
            current_user=current_user,
            data=data,
            before_data=before_data,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _record_inventory_count_failure(
            session=session,
            request=request,
            current_user=current_user,
            error_code=exc.code,
            before_data=before_data,
            resource_id=count_id,
            resource_no=str(before_data.get("count_no") or ""),
        )
        session.commit()
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
    _validate_local_warehouse_inventory_count_gate(
        request_obj=request,
        carriers=[str(before_data.get("count_no") or ""), payload.reason],
        expected_warehouse=str(before_data.get("warehouse") or ""),
        expected_count_date=before_data.get("count_date"),
    )
    if _scope_text(str(before_data.get("warehouse") or "")) is None:
        _raise_warehouse_idempotency_conflict("warehouse 载体缺失")
    if _scope_text(str(before_data.get("count_date") or "")) is None:
        _raise_warehouse_idempotency_conflict("count_date 载体缺失")

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
        _record_inventory_count_success(
            session=session,
            request=request,
            current_user=current_user,
            data=data,
            before_data=before_data,
        )
        session.commit()
    except WarehouseServiceError as exc:
        session.rollback()
        _record_inventory_count_failure(
            session=session,
            request=request,
            current_user=current_user,
            error_code=exc.code,
            before_data=before_data,
            resource_id=count_id,
            resource_no=str(before_data.get("count_no") or ""),
        )
        session.commit()
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
