"""FastAPI-native finance readonly analysis routes."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.permissions import FINANCE_APPROVAL_READ
from app.services.finance_service import FinanceAnalysisService
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/finance", tags=["finance"])


def get_db_session() -> Generator[Session, None, None]:
    """Yield DB session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": jsonable_encoder(data)}


def _err(*, code: str, message: str, status_code: int = 500) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "message": message, "data": None})


def _require_finance_read(*, session: Session, request: Request, current_user: CurrentUser) -> None:
    PermissionService(session=session).require_action(
        current_user=current_user,
        request_obj=request,
        action=FINANCE_APPROVAL_READ,
        module="finance_approval",
        resource_type="FINANCE_ORDER_PROFIT_ANALYSIS",
        resource_id=None,
    )


@router.get("/order-profit-analysis")
def list_order_profit_analysis(
    request: Request,
    company: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    customer: str | None = Query(default=None),
    order_status: str | None = Query(default=None),
    production_status: str | None = Query(default=None),
    profit_status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    sort_by: str | None = Query(default="order_date"),
    sort_order: str | None = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    _require_finance_read(session=session, request=request, current_user=current_user)
    try:
        data = FinanceAnalysisService(session).list_order_profit_analysis(
            company=company,
            from_date=from_date,
            to_date=to_date,
            customer=customer,
            order_status=order_status,
            production_status=production_status,
            profit_status=profit_status,
            keyword=keyword,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
    except SQLAlchemyError:
        return _err(code="ORDER_PROFIT_ANALYSIS_READ_FAILED", message="订单毛利分析读取失败")
    return _ok(data)
