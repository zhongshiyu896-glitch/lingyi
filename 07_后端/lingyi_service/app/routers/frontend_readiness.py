"""Development-only read endpoints that unblock frontend integration readiness."""

from __future__ import annotations

import os
from typing import Any
from typing import Callable

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi.encoders import jsonable_encoder

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.permissions import AUTH_UNAUTHORIZED_CODE
from app.data.frontend_readiness_seed import GAP_LIST_ROWS
from app.data.frontend_readiness_seed import WRITE_FLOW_ROWS

early_router = APIRouter(tags=["frontend_readiness"])
router = APIRouter(tags=["frontend_readiness"])

READINESS_ENVIRONMENTS = {"development", "dev", "local", "test"}
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

EARLY_READINESS_ENDPOINTS: dict[str, str] = {
    "/api/subcontract/factories": "factories",
    "/api/bom/colors": "colors",
    "/api/bom/sizes": "sizes",
    "/api/bom/sample-progress": "sample_progress",
    "/api/production/material-issues": "production_material_issues",
    "/api/bom/material-requests": "material_requests",
    "/api/subcontract/material-issues": "subcontract_material_issues",
    "/api/subcontract/receipts": "subcontract_receipts",
    "/api/subcontract/return-materials": "subcontract_return_materials",
    "/api/factory-statements/settlement-methods": "settlement_methods",
    "/api/factory-statements/invoice-types": "invoice_types",
    "/api/bom/sample-types": "sample_types",
    "/api/factory-statements/expense-types": "expense_types",
    "/api/bom/size-sortings": "size_sortings",
    "/api/factory-statements/cashier-accounts": "cashier_accounts",
    "/api/bom/size-chart-templates": "size_chart_templates",
    "/api/bom/sample-orders": "sample_orders",
}

READINESS_ENDPOINTS: dict[str, str] = {
    "/api/sales-inventory/delivery-addresses": "delivery_addresses",
    "/api/sales-inventory/sales-channels": "sales_channels",
}

WRITE_READINESS_ENDPOINTS: dict[str, str] = {
    "/api/production/readiness/work-order-flow": "sales_to_production_flow",
    "/api/bom/readiness/procurement-flow": "procurement_flow",
    "/api/subcontract/readiness/subcontract-flow": "subcontract_flow",
    "/api/production/readiness/inventory-finance-flow": "inventory_finance_flow",
    "/api/quality/readiness/quality-flow": "quality_flow",
    "/api/workshop/readiness/wage-flow": "workshop_wage_flow",
    "/api/style-profit/readiness/profit-flow": "style_profit_flow",
}

ALL_READINESS_ENDPOINTS: dict[str, str] = {
    **EARLY_READINESS_ENDPOINTS,
    **READINESS_ENDPOINTS,
}


def frontend_readiness_enabled() -> bool:
    """Return whether the development/test readiness router should be mounted."""
    env = os.getenv("APP_ENV", "development").strip().lower()
    enabled = os.getenv("LINGYI_FRONTEND_READINESS_ENABLED", "true").strip().lower()
    return env in READINESS_ENVIRONMENTS and enabled not in {"0", "false", "no"}


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": jsonable_encoder(data)}


def _parse_page(value: Any, *, default: int = DEFAULT_PAGE) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 1 else default


def _parse_page_size(value: Any, *, default: int = DEFAULT_PAGE_SIZE) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if parsed < 1 or parsed > MAX_PAGE_SIZE:
        return default
    return parsed


def _paginate_rows(rows: list[dict[str, Any]], *, page: Any, page_size: Any) -> dict[str, Any]:
    normalized_page = _parse_page(page)
    normalized_page_size = _parse_page_size(page_size)
    total = len(rows)
    start = (normalized_page - 1) * normalized_page_size
    end = start + normalized_page_size
    return {
        "items": rows[start:end],
        "total": total,
        "page": normalized_page,
        "page_size": normalized_page_size,
    }


def _require_dev_header_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.source != "dev_header":
        raise HTTPException(
            status_code=401,
            detail={
                "code": AUTH_UNAUTHORIZED_CODE,
                "message": "仅允许开发鉴权头访问前端预备只读端点",
                "data": {},
            },
        )
    return current_user


def _make_list_endpoint(seed_key: str) -> Callable[..., dict[str, Any]]:
    def list_frontend_readiness_rows(
        page: str | None = Query(default=str(DEFAULT_PAGE)),
        page_size: str | None = Query(default=str(DEFAULT_PAGE_SIZE)),
        _current_user: CurrentUser = Depends(_require_dev_header_user),
    ) -> dict[str, Any]:
        rows = GAP_LIST_ROWS.get(seed_key, [])
        return _ok(_paginate_rows(rows, page=page, page_size=page_size))

    list_frontend_readiness_rows.__name__ = f"list_frontend_readiness_{seed_key}"
    return list_frontend_readiness_rows


def _make_write_flow_endpoint(seed_key: str) -> Callable[..., dict[str, Any]]:
    def run_frontend_readiness_flow(
        payload: dict[str, Any] | None = Body(default=None),
        _current_user: CurrentUser = Depends(_require_dev_header_user),
    ) -> dict[str, Any]:
        data = dict(WRITE_FLOW_ROWS.get(seed_key, {}))
        carrier = payload if isinstance(payload, dict) else {}
        for field in ("scenario_tag", "idempotency_key", "request_id", "operation"):
            if carrier.get(field) is not None:
                data[field] = carrier[field]
        return _ok(data)

    run_frontend_readiness_flow.__name__ = f"run_frontend_readiness_{seed_key}"
    return run_frontend_readiness_flow


def _register_endpoints(target_router: APIRouter, endpoints: dict[str, str]) -> None:
    for path, seed_key in endpoints.items():
        target_router.add_api_route(
            path,
            _make_list_endpoint(seed_key),
            methods=["GET"],
            name=f"frontend_readiness_{seed_key}",
        )


def _register_write_endpoints(target_router: APIRouter, endpoints: dict[str, str]) -> None:
    for path, seed_key in endpoints.items():
        target_router.add_api_route(
            path,
            _make_write_flow_endpoint(seed_key),
            methods=["POST"],
            name=f"frontend_readiness_write_{seed_key}",
        )


_register_endpoints(early_router, EARLY_READINESS_ENDPOINTS)
_register_write_endpoints(early_router, WRITE_READINESS_ENDPOINTS)
_register_endpoints(router, READINESS_ENDPOINTS)
