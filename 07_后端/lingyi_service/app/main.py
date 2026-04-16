"""FastAPI application entry for lingyi_service."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Generator

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.core.logging import log_safe_error
from app.core.error_codes import AUTH_UNAUTHENTICATED
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import INTERNAL_API_FORBIDDEN
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.error_codes import REQUEST_ID_REJECTED
from app.core.error_codes import RESOURCE_ACCESS_DENIED
from app.core.error_codes import WORKSHOP_DRY_RUN_DISABLED
from app.core.permissions import AUTH_FORBIDDEN_CODE
from app.core.permissions import AUTH_UNAUTHORIZED_CODE
from app.core.permissions import BOM_CREATE
from app.core.permissions import BOM_DEACTIVATE
from app.core.permissions import BOM_PUBLISH
from app.core.permissions import BOM_READ
from app.core.permissions import BOM_SET_DEFAULT
from app.core.permissions import BOM_UPDATE
from app.core.permissions import PERMISSION_SOURCE_UNAVAILABLE_CODE
from app.core.permissions import WORKSHOP_JOB_CARD_SYNC
from app.core.permissions import WORKSHOP_JOB_CARD_SYNC_WORKER
from app.core.permissions import WORKSHOP_READ
from app.core.permissions import WORKSHOP_TICKET_BATCH
from app.core.permissions import WORKSHOP_TICKET_REGISTER
from app.core.permissions import WORKSHOP_TICKET_REVERSAL
from app.core.permissions import WORKSHOP_WAGE_RATE_MANAGE
from app.core.permissions import WORKSHOP_WAGE_RATE_READ
from app.core.permissions import WORKSHOP_WAGE_READ
from app.core.permissions import SUBCONTRACT_CANCEL
from app.core.permissions import SUBCONTRACT_CREATE
from app.core.permissions import SUBCONTRACT_INSPECT
from app.core.permissions import SUBCONTRACT_ISSUE_MATERIAL
from app.core.permissions import SUBCONTRACT_READ
from app.core.permissions import SUBCONTRACT_RECEIVE
from app.core.permissions import SUBCONTRACT_STOCK_SYNC_RETRY
from app.core.permissions import SUBCONTRACT_STOCK_SYNC_WORKER
from app.core.permissions import PRODUCTION_JOB_CARD_SYNC
from app.core.permissions import PRODUCTION_MATERIAL_CHECK
from app.core.permissions import PRODUCTION_PLAN_CREATE
from app.core.permissions import PRODUCTION_READ
from app.core.permissions import PRODUCTION_WORK_ORDER_CREATE
from app.core.permissions import PRODUCTION_WORK_ORDER_WORKER
from app.core.permissions import STYLE_PROFIT_READ
from app.core.permissions import STYLE_PROFIT_SNAPSHOT_CREATE
from app.core.permissions import FACTORY_STATEMENT_CREATE
from app.core.permissions import FACTORY_STATEMENT_CONFIRM
from app.core.permissions import FACTORY_STATEMENT_CANCEL
from app.core.permissions import FACTORY_STATEMENT_READ
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE
from app.core.permissions import FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER
from app.core.permissions import SALES_INVENTORY_DIAGNOSTIC
from app.core.permissions import SALES_INVENTORY_READ
from app.core.permissions import QUALITY_CANCEL
from app.core.permissions import QUALITY_CONFIRM
from app.core.permissions import QUALITY_CREATE
from app.core.permissions import QUALITY_DIAGNOSTIC
from app.core.permissions import QUALITY_EXPORT
from app.core.permissions import QUALITY_READ
from app.core.permissions import QUALITY_UPDATE
from app.core.permissions import get_permission_source
from app.core.request_id import get_request_id_from_request
from app.core.request_id import normalize_request_id
from app.routers.auth import get_db_session as auth_router_session_dep
from app.routers.auth import router as auth_router
from app.routers.bom import get_db_session as bom_router_session_dep
from app.routers.bom import router as bom_router
from app.routers.subcontract import get_db_session as subcontract_router_session_dep
from app.routers.subcontract import router as subcontract_router
from app.routers.production import get_db_session as production_router_session_dep
from app.routers.production import router as production_router
from app.routers.workshop import get_db_session as workshop_router_session_dep
from app.routers.workshop import router as workshop_router
from app.routers.style_profit import get_db_session as style_profit_router_session_dep
from app.routers.style_profit import router as style_profit_router
from app.routers.factory_statement import get_db_session as factory_statement_router_session_dep
from app.routers.factory_statement import router as factory_statement_router
from app.routers.sales_inventory import get_db_session as sales_inventory_router_session_dep
from app.routers.sales_inventory import router as sales_inventory_router
from app.routers.quality import get_db_session as quality_router_session_dep
from app.routers.quality import router as quality_router
from app.services.audit_service import AuditService

DATABASE_URL = os.getenv("LINGYI_DB_URL", "sqlite:///./lingyi_service.db")
logger = logging.getLogger(__name__)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def _validate_permission_source_config() -> None:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    permission_source = get_permission_source()
    if app_env == "production" and permission_source != "erpnext":
        raise RuntimeError("APP_ENV=production 时 LINGYI_PERMISSION_SOURCE 必须为 erpnext")


def get_db_session() -> Generator[Session, None, None]:
    """Provide transactional DB session for request lifecycle."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="Lingyi Service", version="1.0.0")
_validate_permission_source_config()
app.dependency_overrides[auth_router_session_dep] = get_db_session
app.dependency_overrides[subcontract_router_session_dep] = get_db_session
app.dependency_overrides[production_router_session_dep] = get_db_session
app.dependency_overrides[bom_router_session_dep] = get_db_session
app.dependency_overrides[workshop_router_session_dep] = get_db_session
app.dependency_overrides[style_profit_router_session_dep] = get_db_session
app.dependency_overrides[factory_statement_router_session_dep] = get_db_session
app.dependency_overrides[sales_inventory_router_session_dep] = get_db_session
app.dependency_overrides[quality_router_session_dep] = get_db_session
app.include_router(auth_router)
app.include_router(subcontract_router)
app.include_router(production_router)
app.include_router(bom_router)
app.include_router(workshop_router)
app.include_router(style_profit_router)
app.include_router(factory_statement_router)
app.include_router(sales_inventory_router)
app.include_router(quality_router)


SECURITY_AUDIT_CODES = {
    AUTH_UNAUTHENTICATED,
    RESOURCE_ACCESS_DENIED,
    EXTERNAL_SERVICE_UNAVAILABLE,
    INTERNAL_API_FORBIDDEN,
    REQUEST_ID_REJECTED,
    AUTH_UNAUTHORIZED_CODE,
    AUTH_FORBIDDEN_CODE,
    PERMISSION_SOURCE_UNAVAILABLE_CODE,
    INTERNAL_API_DISABLED,
    WORKSHOP_DRY_RUN_DISABLED,
}


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach request id into request state and response headers."""
    request_id = normalize_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return unified error envelope for HTTPException."""
    if isinstance(exc.detail, dict) and "code" in exc.detail and "message" in exc.detail:
        payload = dict(exc.detail)
        payload.setdefault("data", {})
        _record_security_audit_fallback_if_needed(request=request, code=str(payload["code"]), message=str(payload["message"]))
        return JSONResponse(status_code=exc.status_code, content=payload)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": "HTTP_ERROR", "message": str(exc.detail), "data": {}},
    )


def _record_security_audit_fallback_if_needed(*, request: Request, code: str, message: str) -> None:
    if code not in SECURITY_AUDIT_CODES:
        return
    if getattr(request.state, "security_audit_recorded", False):
        return

    module, action, resource_type, resource_id = _infer_security_target(request)
    current_user = getattr(request.state, "current_user", None)

    db = SessionLocal()
    try:
        AuditService(db).record_security_audit(
            event_type=code,
            module=module,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_no=None,
            user=current_user,
            deny_reason=message,
            permission_source=get_permission_source(),
            request_obj=request,
        )
        db.commit()
        request.state.security_audit_recorded = True
    except Exception as audit_exc:
        db.rollback()
        request_id = get_request_id_from_request(request)
        log_safe_error(
            logger,
            "security_audit_write_failed",
            audit_exc,
            request_id=request_id,
            extra={
                "error_code": "AUDIT_WRITE_FAILED",
                "module": module,
                "action": action or "",
                "resource_type": resource_type or "",
                "resource_id": resource_id or "",
                "user_id": current_user.username if current_user else "",
            },
        )
    finally:
        db.close()


def _infer_security_target(request: Request) -> tuple[str, str | None, str | None, str | None]:
    path = request.url.path or ""
    method = (request.method or "GET").upper()

    if path.startswith("/api/auth/actions"):
        bom_id = _extract_bom_id(path)
        if bom_id:
            return "auth", "auth:actions", "BOM", bom_id
        return "auth", "auth:actions", "AuthAction", None

    if path.startswith("/api/bom"):
        bom_id = _extract_bom_id(path)
        if path in {"/api/bom", "/api/bom/"}:
            if method == "POST":
                return "bom", BOM_CREATE, "BOM", None
            return "bom", BOM_READ, "BOM", None
        if path.endswith("/activate"):
            return "bom", BOM_PUBLISH, "BOM", bom_id
        if path.endswith("/deactivate"):
            return "bom", BOM_DEACTIVATE, "BOM", bom_id
        if path.endswith("/set-default"):
            return "bom", BOM_SET_DEFAULT, "BOM", bom_id
        if path.endswith("/explode"):
            return "bom", BOM_READ, "BOM", bom_id
        if bom_id:
            if method == "PUT":
                return "bom", BOM_UPDATE, "BOM", bom_id
            return "bom", BOM_READ, "BOM", bom_id
        return "bom", BOM_READ, "BOM", None

    if path.startswith("/api/workshop"):
        if path.endswith("/tickets/register"):
            return "workshop", WORKSHOP_TICKET_REGISTER, "WorkshopTicket", None
        if path.endswith("/tickets/reversal"):
            return "workshop", WORKSHOP_TICKET_REVERSAL, "WorkshopTicket", None
        if path.endswith("/tickets/batch"):
            return "workshop", WORKSHOP_TICKET_BATCH, "WorkshopTicket", None
        if "/job-cards/" in path and path.endswith("/summary"):
            job_card = _extract_job_card(path)
            return "workshop", WORKSHOP_READ, "JobCard", job_card
        if "/job-cards/" in path and path.endswith("/sync"):
            job_card = _extract_job_card(path)
            return "workshop", WORKSHOP_JOB_CARD_SYNC, "JobCard", job_card
        if path.endswith("/internal/job-card-sync/run-once"):
            return "workshop", WORKSHOP_JOB_CARD_SYNC_WORKER, "JobCardSyncWorker", None
        if path.endswith("/tickets"):
            return "workshop", WORKSHOP_READ, "WorkshopTicket", None
        if path.endswith("/daily-wages"):
            return "workshop", WORKSHOP_WAGE_READ, "WorkshopDailyWage", None
        if path.endswith("/wage-rates"):
            if method == "POST":
                return "workshop", WORKSHOP_WAGE_RATE_MANAGE, "WageRate", None
            return "workshop", WORKSHOP_WAGE_RATE_READ, "WageRate", None
        if "/wage-rates/" in path and path.endswith("/deactivate"):
            return "workshop", WORKSHOP_WAGE_RATE_MANAGE, "WageRate", _extract_wage_rate_id(path)
        return "workshop", WORKSHOP_READ, "Workshop", None

    if path.startswith("/api/subcontract"):
        if path in {"/api/subcontract", "/api/subcontract/"}:
            if method == "POST":
                return "subcontract", SUBCONTRACT_CREATE, "SubcontractOrder", None
            return "subcontract", SUBCONTRACT_READ, "SubcontractOrder", None
        subcontract_id = _extract_subcontract_id(path)
        if path.endswith("/issue-material"):
            return "subcontract", SUBCONTRACT_ISSUE_MATERIAL, "SubcontractOrder", subcontract_id
        if path.endswith("/receive"):
            return "subcontract", SUBCONTRACT_RECEIVE, "SubcontractOrder", subcontract_id
        if path.endswith("/inspect"):
            return "subcontract", SUBCONTRACT_INSPECT, "SubcontractOrder", subcontract_id
        if path.endswith("/cancel"):
            return "subcontract", SUBCONTRACT_CANCEL, "SubcontractOrder", subcontract_id
        if path.endswith("/stock-sync/retry"):
            return "subcontract", SUBCONTRACT_STOCK_SYNC_RETRY, "SubcontractOrder", subcontract_id
        if path.endswith("/internal/stock-sync/run-once"):
            return "subcontract", SUBCONTRACT_STOCK_SYNC_WORKER, "SubcontractStockSyncWorker", None
        return "subcontract", SUBCONTRACT_READ, "SubcontractOrder", subcontract_id

    if path.startswith("/api/production"):
        if path in {"/api/production/plans", "/api/production/plans/"}:
            if method == "POST":
                return "production", PRODUCTION_PLAN_CREATE, "ProductionPlan", None
            return "production", PRODUCTION_READ, "ProductionPlan", None
        if path.endswith("/material-check"):
            plan_id = _extract_production_plan_id(path)
            return "production", PRODUCTION_MATERIAL_CHECK, "ProductionPlan", plan_id
        if path.endswith("/create-work-order"):
            plan_id = _extract_production_plan_id(path)
            return "production", PRODUCTION_WORK_ORDER_CREATE, "ProductionPlan", plan_id
        if "/work-orders/" in path and path.endswith("/sync-job-cards"):
            work_order = _extract_work_order(path)
            return "production", PRODUCTION_JOB_CARD_SYNC, "ProductionWorkOrder", work_order
        if path.endswith("/internal/work-order-sync/run-once"):
            return "production", PRODUCTION_WORK_ORDER_WORKER, "ProductionWorkOrderWorker", None
        plan_id = _extract_production_plan_id(path)
        return "production", PRODUCTION_READ, "ProductionPlan", plan_id

    if path.startswith("/api/reports/style-profit"):
        if path in {"/api/reports/style-profit/snapshots", "/api/reports/style-profit/snapshots/"}:
            if method == "POST":
                return "style_profit", STYLE_PROFIT_SNAPSHOT_CREATE, "StyleProfitSnapshot", None
            return "style_profit", STYLE_PROFIT_READ, "StyleProfitSnapshot", None
        snapshot_id = _extract_style_profit_snapshot_id(path)
        return "style_profit", STYLE_PROFIT_READ, "StyleProfitSnapshot", snapshot_id

    if path.startswith("/api/factory-statements"):
        if path in {"/api/factory-statements", "/api/factory-statements/"}:
            if method == "POST":
                return "factory_statement", FACTORY_STATEMENT_CREATE, "FactoryStatement", None
            return "factory_statement", FACTORY_STATEMENT_READ, "FactoryStatement", None
        if path.endswith("/internal/payable-draft-sync/run-once"):
            return (
                "factory_statement",
                FACTORY_STATEMENT_PAYABLE_DRAFT_WORKER,
                "FactoryStatementPayableWorker",
                None,
            )
        statement_id = _extract_factory_statement_id(path)
        if path.endswith("/confirm"):
            return "factory_statement", FACTORY_STATEMENT_CONFIRM, "FactoryStatement", statement_id
        if path.endswith("/cancel"):
            return "factory_statement", FACTORY_STATEMENT_CANCEL, "FactoryStatement", statement_id
        if path.endswith("/payable-draft"):
            return (
                "factory_statement",
                FACTORY_STATEMENT_PAYABLE_DRAFT_CREATE,
                "FactoryStatement",
                statement_id,
            )
        return "factory_statement", FACTORY_STATEMENT_READ, "FactoryStatement", statement_id

    if path.startswith("/api/sales-inventory"):
        if path.endswith("/diagnostic"):
            return "sales_inventory", SALES_INVENTORY_DIAGNOSTIC, "SalesInventoryDiagnostic", None
        if "/sales-orders/" in path:
            return "sales_inventory", SALES_INVENTORY_READ, "SalesOrder", _extract_sales_order_name(path)
        if path.startswith("/api/sales-inventory/items/"):
            return "sales_inventory", SALES_INVENTORY_READ, "Item", _extract_sales_inventory_item(path)
        if path.endswith("/warehouses"):
            return "sales_inventory", SALES_INVENTORY_READ, "Warehouse", None
        if path.endswith("/customers"):
            return "sales_inventory", SALES_INVENTORY_READ, "Customer", None
        return "sales_inventory", SALES_INVENTORY_READ, "SalesInventory", None

    if path.startswith("/api/quality"):
        if path.endswith("/statistics"):
            return "quality", QUALITY_READ, "QualityStatistics", None
        if path.endswith("/diagnostic"):
            return "quality", QUALITY_DIAGNOSTIC, "QualityDiagnostic", None
        if path.endswith("/export"):
            return "quality", QUALITY_EXPORT, "QualityInspection", None
        inspection_id = _extract_quality_inspection_id(path)
        if path in {"/api/quality/inspections", "/api/quality/inspections/"}:
            if method == "POST":
                return "quality", QUALITY_CREATE, "QualityInspection", None
            return "quality", QUALITY_READ, "QualityInspection", None
        if path.endswith("/confirm"):
            return "quality", QUALITY_CONFIRM, "QualityInspection", inspection_id
        if path.endswith("/cancel"):
            return "quality", QUALITY_CANCEL, "QualityInspection", inspection_id
        if method == "PATCH":
            return "quality", QUALITY_UPDATE, "QualityInspection", inspection_id
        return "quality", QUALITY_READ, "QualityInspection", inspection_id

    return "unknown", None, None, None


def _extract_bom_id(path: str) -> str | None:
    match = re.match(r"^/api/bom/(\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    match = re.match(r"^/api/auth/actions/bom/(\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_job_card(path: str) -> str | None:
    match = re.match(r"^/api/workshop/job-cards/([^/]+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_wage_rate_id(path: str) -> str | None:
    match = re.match(r"^/api/workshop/wage-rates/(\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_subcontract_id(path: str) -> str | None:
    match = re.match(r"^/api/subcontract/(\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_production_plan_id(path: str) -> str | None:
    match = re.match(r"^/api/production/plans/(\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_work_order(path: str) -> str | None:
    match = re.match(r"^/api/production/work-orders/([^/]+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_style_profit_snapshot_id(path: str) -> str | None:
    match = re.match(r"^/api/reports/style-profit/snapshots/(\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_factory_statement_id(path: str) -> str | None:
    match = re.match(r"^/api/factory-statements/(\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_sales_order_name(path: str) -> str | None:
    match = re.match(r"^/api/sales-inventory/sales-orders/([^/]+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_sales_inventory_item(path: str) -> str | None:
    match = re.match(r"^/api/sales-inventory/items/([^/]+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None


def _extract_quality_inspection_id(path: str) -> str | None:
    match = re.match(r"^/api/quality/inspections/(\\d+)(?:$|/)", path)
    if match:
        return match.group(1)
    return None
