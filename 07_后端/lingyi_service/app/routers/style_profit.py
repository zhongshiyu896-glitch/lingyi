"""FastAPI router for style-profit report APIs (TASK-005E1)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.error_codes import AUDIT_WRITE_FAILED
from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN
from app.core.error_codes import STYLE_PROFIT_INTERNAL_ERROR
from app.core.error_codes import STYLE_PROFIT_INVALID_FORMULA_VERSION
from app.core.error_codes import STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY
from app.core.error_codes import STYLE_PROFIT_INVALID_PERIOD
from app.core.error_codes import STYLE_PROFIT_INVALID_REVENUE_MODE
from app.core.error_codes import STYLE_PROFIT_REVENUE_SOURCE_REQUIRED
from app.core.error_codes import STYLE_PROFIT_NOT_FOUND
from app.core.error_codes import STYLE_PROFIT_SALES_ORDER_REQUIRED
from app.core.error_codes import STYLE_PROFIT_SOURCE_UNAVAILABLE
from app.core.error_codes import message_of
from app.core.error_codes import status_of
from app.core.exceptions import AppException
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.core.permissions import STYLE_PROFIT_READ
from app.core.permissions import STYLE_PROFIT_SNAPSHOT_CREATE
from app.models.style_profit import LyStyleProfitDetail
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap
from app.schemas.style_profit import StyleProfitDetailItem
from app.schemas.style_profit import StyleProfitSnapshotCreateRequest
from app.schemas.style_profit import StyleProfitSnapshotDetailData
from app.schemas.style_profit import StyleProfitSnapshotListData
from app.schemas.style_profit import StyleProfitSnapshotListItem
from app.schemas.style_profit import StyleProfitSnapshotResult
from app.schemas.style_profit import StyleProfitSnapshotSelectorRequest
from app.schemas.style_profit import StyleProfitSourceMapItem
from app.services.audit_service import AuditContext
from app.services.audit_service import AuditService
from app.services.permission_service import PermissionService
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector
from app.services.style_profit_service import STYLE_PROFIT_SOURCE_READ_FAILED
from app.services.style_profit_service import StyleProfitService

router = APIRouter(prefix="/api/reports/style-profit", tags=["style_profit"])


_FORBIDDEN_CLIENT_SOURCE_FIELDS = {
    "sales_invoice_rows",
    "sales_order_rows",
    "bom_material_rows",
    "bom_operation_rows",
    "stock_ledger_rows",
    "purchase_receipt_rows",
    "workshop_ticket_rows",
    "subcontract_rows",
    "allowed_material_item_codes",
}


def get_db_session() -> Generator[Session, None, None]:
    """Yield SQLAlchemy session. Overridden in app.main."""
    raise RuntimeError("DB session dependency is not wired")
    yield  # pragma: no cover


def _ok(data: Any) -> dict[str, Any]:
    return {"code": "0", "message": "success", "data": data}


def _err(code: str, message: str, status_code: int | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code or status_of(code, 400),
        content={"code": code, "message": message, "data": {}},
    )


def _app_err(exc: AppException) -> JSONResponse:
    return _err(exc.code, exc.message, status_code=exc.status_code)


def _http_exc_err(exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or "HTTP_ERROR")
        message = str(detail.get("message") or "请求失败")
        return _err(code, message, status_code=exc.status_code)
    if isinstance(detail, str):
        return _err("HTTP_ERROR", detail, status_code=exc.status_code)
    return _err("HTTP_ERROR", "请求失败", status_code=exc.status_code)


def _commit_or_raise_write_error(session: Session) -> None:
    try:
        session.commit()
    except (IntegrityError, OperationalError, DBAPIError, SQLAlchemyError) as exc:
        session.rollback()
        raise DatabaseWriteFailed() from exc


def _to_snapshot_result(snapshot: LyStyleProfitSnapshot, *, idempotent_replay: bool = False) -> StyleProfitSnapshotResult:
    return StyleProfitSnapshotResult(
        snapshot_id=int(snapshot.id),
        snapshot_no=str(snapshot.snapshot_no),
        company=str(snapshot.company),
        item_code=str(snapshot.item_code),
        sales_order=str(snapshot.sales_order) if snapshot.sales_order else None,
        revenue_status=str(snapshot.revenue_status),
        revenue_amount=Decimal(str(snapshot.revenue_amount)),
        actual_total_cost=Decimal(str(snapshot.actual_total_cost)),
        standard_total_cost=Decimal(str(snapshot.standard_total_cost)),
        profit_amount=Decimal(str(snapshot.profit_amount)),
        profit_rate=Decimal(str(snapshot.profit_rate)) if snapshot.profit_rate is not None else None,
        snapshot_status=str(snapshot.snapshot_status),
        unresolved_count=int(snapshot.unresolved_count or 0),
        idempotency_key=str(snapshot.idempotency_key),
        request_hash=str(snapshot.request_hash),
        idempotent_replay=idempotent_replay,
    )


def _to_list_item(row: LyStyleProfitSnapshot) -> StyleProfitSnapshotListItem:
    return StyleProfitSnapshotListItem(
        id=int(row.id),
        snapshot_no=str(row.snapshot_no),
        company=str(row.company),
        item_code=str(row.item_code),
        sales_order=str(row.sales_order) if row.sales_order else None,
        from_date=row.from_date,
        to_date=row.to_date,
        revenue_status=str(row.revenue_status),
        revenue_amount=Decimal(str(row.revenue_amount)),
        actual_total_cost=Decimal(str(row.actual_total_cost)),
        profit_amount=Decimal(str(row.profit_amount)),
        profit_rate=Decimal(str(row.profit_rate)) if row.profit_rate is not None else None,
        snapshot_status=str(row.snapshot_status),
        formula_version=str(row.formula_version),
        unresolved_count=int(row.unresolved_count or 0),
        created_at=row.created_at if isinstance(row.created_at, datetime) else datetime.utcnow(),
    )


def _to_detail_item(row: LyStyleProfitDetail) -> StyleProfitDetailItem:
    return StyleProfitDetailItem(
        id=int(row.id),
        line_no=int(row.line_no),
        cost_type=str(row.cost_type),
        source_type=str(row.source_type),
        source_name=str(row.source_name),
        item_code=str(row.item_code) if row.item_code else None,
        qty=Decimal(str(row.qty)) if row.qty is not None else None,
        unit_rate=Decimal(str(row.unit_rate)) if row.unit_rate is not None else None,
        amount=Decimal(str(row.amount)),
        formula_code=str(row.formula_code) if row.formula_code else None,
        is_unresolved=bool(row.is_unresolved),
        unresolved_reason=str(row.unresolved_reason) if row.unresolved_reason else None,
        raw_ref=row.raw_ref if isinstance(row.raw_ref, dict) else None,
        created_at=row.created_at if isinstance(row.created_at, datetime) else datetime.utcnow(),
    )


def _to_source_map_item(row: LyStyleProfitSourceMap) -> StyleProfitSourceMapItem:
    return StyleProfitSourceMapItem(
        id=int(row.id),
        detail_id=int(row.detail_id) if row.detail_id is not None else None,
        company=str(row.company),
        sales_order=str(row.sales_order) if row.sales_order else None,
        style_item_code=str(row.style_item_code),
        source_item_code=str(row.source_item_code) if row.source_item_code else None,
        source_system=str(row.source_system),
        source_doctype=str(row.source_doctype),
        source_status=str(row.source_status),
        source_name=str(row.source_name),
        source_line_no=str(row.source_line_no),
        qty=Decimal(str(row.qty)) if row.qty is not None else None,
        unit_rate=Decimal(str(row.unit_rate)) if row.unit_rate is not None else None,
        amount=Decimal(str(row.amount)),
        currency=str(row.currency) if row.currency else None,
        warehouse=str(row.warehouse) if row.warehouse else None,
        posting_date=row.posting_date,
        include_in_profit=bool(row.include_in_profit),
        mapping_status=str(row.mapping_status),
        unresolved_reason=str(row.unresolved_reason) if row.unresolved_reason else None,
        raw_ref=row.raw_ref if isinstance(row.raw_ref, dict) else None,
        created_at=row.created_at if isinstance(row.created_at, datetime) else datetime.utcnow(),
    )


def _record_failure_safely(
    *,
    session: Session,
    audit: AuditService,
    context: AuditContext,
    request: Request,
    action: str,
    current_user: CurrentUser,
    resource_id: int | None,
    resource_no: str | None,
    error_code: str,
) -> None:
    try:
        audit.record_failure(
            module="style_profit",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="STYLE_PROFIT_SNAPSHOT",
            resource_id=resource_id,
            resource_no=resource_no,
            before_data=None,
            after_data=None,
            error_code=error_code,
            context=context,
        )
        session.commit()
    except Exception as exc:  # pragma: no cover - rare path
        session.rollback()
        raise AuditWriteFailed() from exc


@router.get("/snapshots")
def list_snapshots(
    request: Request,
    company: str | None = Query(default=None),
    item_code: str | None = Query(default=None),
    sales_order: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    snapshot_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = STYLE_PROFIT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    resource_no = str(sales_order).strip() if sales_order and str(sales_order).strip() else None

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="style_profit",
            resource_type="style_profit_snapshot",
            resource_id=None,
        )
        normalized_company = str(company or "").strip()
        normalized_item_code = str(item_code or "").strip()
        if not normalized_company or not normalized_item_code:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=STYLE_PROFIT_SOURCE_READ_FAILED,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(STYLE_PROFIT_SOURCE_READ_FAILED, "company 与 item_code 不能为空")

        permission_service.ensure_style_profit_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=normalized_company,
            item_code=normalized_item_code,
            resource_type="style_profit_snapshot",
            resource_id=None,
            resource_no=resource_no,
            enforce_action=False,
        )

        query = session.query(LyStyleProfitSnapshot).filter(
            LyStyleProfitSnapshot.company == normalized_company,
            LyStyleProfitSnapshot.item_code == normalized_item_code,
        )
        if sales_order and str(sales_order).strip():
            query = query.filter(LyStyleProfitSnapshot.sales_order == str(sales_order).strip())
        if snapshot_status and str(snapshot_status).strip():
            query = query.filter(LyStyleProfitSnapshot.snapshot_status == str(snapshot_status).strip())
        if from_date is not None:
            query = query.filter(LyStyleProfitSnapshot.from_date >= from_date.date())
        if to_date is not None:
            query = query.filter(LyStyleProfitSnapshot.to_date <= to_date.date())

        total = query.count()
        rows = (
            query.order_by(LyStyleProfitSnapshot.created_at.desc(), LyStyleProfitSnapshot.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        data = StyleProfitSnapshotListData(
            items=[_to_list_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
        return _ok(data.model_dump(mode="json"))
    except HTTPException as exc:
        session.rollback()
        return _http_exc_err(exc)
    except DatabaseReadFailed as exc:
        session.rollback()
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except SQLAlchemyError:
        session.rollback()
        db_exc = DatabaseReadFailed()
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=db_exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(db_exc)
    except AppException as exc:
        session.rollback()
        if exc.code != AUDIT_WRITE_FAILED:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=exc.code,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
        return _app_err(exc)
    except Exception:
        session.rollback()
        code = STYLE_PROFIT_INTERNAL_ERROR
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _err(code, message_of(code), status_of(code))


@router.get("/snapshots/{snapshot_id}")
def get_snapshot_detail(
    snapshot_id: int,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = STYLE_PROFIT_READ
    permission_service = PermissionService(session=session)
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="style_profit",
            resource_type="style_profit_snapshot",
            resource_id=snapshot_id,
        )

        snapshot = (
            session.query(LyStyleProfitSnapshot)
            .filter(LyStyleProfitSnapshot.id == snapshot_id)
            .one_or_none()
        )
        if snapshot is None:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=snapshot_id,
                resource_no=None,
                error_code=STYLE_PROFIT_NOT_FOUND,
            )
            return _err(STYLE_PROFIT_NOT_FOUND, message_of(STYLE_PROFIT_NOT_FOUND), status_of(STYLE_PROFIT_NOT_FOUND))

        permission_service.ensure_style_profit_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=str(snapshot.company),
            item_code=str(snapshot.item_code),
            resource_type="style_profit_snapshot",
            resource_id=snapshot_id,
            resource_no=str(snapshot.snapshot_no),
            enforce_action=False,
        )

        details = (
            session.query(LyStyleProfitDetail)
            .filter(LyStyleProfitDetail.snapshot_id == snapshot_id)
            .order_by(LyStyleProfitDetail.line_no.asc(), LyStyleProfitDetail.id.asc())
            .all()
        )
        source_maps = (
            session.query(LyStyleProfitSourceMap)
            .filter(LyStyleProfitSourceMap.snapshot_id == snapshot_id)
            .order_by(LyStyleProfitSourceMap.id.asc())
            .all()
        )

        data = StyleProfitSnapshotDetailData(
            snapshot=_to_snapshot_result(snapshot),
            details=[_to_detail_item(row) for row in details],
            source_maps=[_to_source_map_item(row) for row in source_maps],
        )

        audit.record_success(
            module="style_profit",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="STYLE_PROFIT_SNAPSHOT",
            resource_id=int(snapshot.id),
            resource_no=str(snapshot.snapshot_no),
            before_data=None,
            after_data={"snapshot_id": int(snapshot.id), "snapshot_no": str(snapshot.snapshot_no)},
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(data.model_dump(mode="json"))
    except HTTPException as exc:
        session.rollback()
        return _http_exc_err(exc)
    except AuditWriteFailed as exc:
        session.rollback()
        return _app_err(exc)
    except AppException as exc:
        session.rollback()
        if exc.code != AUDIT_WRITE_FAILED:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=snapshot_id,
                    resource_no=None,
                    error_code=exc.code,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
        return _app_err(exc)
    except SQLAlchemyError:
        session.rollback()
        db_exc = DatabaseReadFailed()
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=snapshot_id,
                resource_no=None,
                error_code=db_exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(db_exc)
    except Exception:
        session.rollback()
        code = STYLE_PROFIT_INTERNAL_ERROR
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=snapshot_id,
                resource_no=None,
                error_code=code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _err(code, message_of(code), status_of(code))


@router.post("/snapshots")
def create_snapshot(
    request: Request,
    payload: dict[str, Any] = Body(...),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    action = STYLE_PROFIT_SNAPSHOT_CREATE
    permission_service = PermissionService(session=session)
    collector = StyleProfitApiSourceCollector(session=session, request_obj=request)
    service = StyleProfitService()
    audit = AuditService(session=session)
    context = AuditContext.from_request(request)
    normalized_payload = dict(payload)
    for key in (
        "company",
        "item_code",
        "sales_order",
        "revenue_mode",
        "formula_version",
        "idempotency_key",
        "work_order",
    ):
        value = normalized_payload.get(key)
        if isinstance(value, str):
            normalized_payload[key] = value.strip()
    resource_no = str(normalized_payload.get("sales_order") or "").strip() or None

    try:
        permission_service.require_action(
            current_user=current_user,
            request_obj=request,
            action=action,
            module="style_profit",
            resource_type="style_profit_snapshot",
            resource_id=None,
        )
        company_scope = str(normalized_payload.get("company") or "").strip()
        item_scope = str(normalized_payload.get("item_code") or "").strip()
        if not company_scope or not item_scope:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=STYLE_PROFIT_SOURCE_READ_FAILED,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(STYLE_PROFIT_SOURCE_READ_FAILED, "company 与 item_code 不能为空")

        permission_service.ensure_style_profit_resource_permission(
            current_user=current_user,
            request_obj=request,
            action=action,
            company=company_scope,
            item_code=item_scope,
            resource_type="style_profit_snapshot",
            resource_id=None,
            resource_no=resource_no,
            enforce_action=False,
        )

        forbidden_fields = sorted(_FORBIDDEN_CLIENT_SOURCE_FIELDS & set(normalized_payload.keys()))
        if forbidden_fields:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(
                STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN,
                "客户端不得提交利润来源明细",
                status_of(STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN),
            )

        try:
            selector = StyleProfitSnapshotSelectorRequest.model_validate(normalized_payload)
        except ValidationError as exc:
            err_text = str(exc)
            err_code = STYLE_PROFIT_SOURCE_READ_FAILED
            err_message = "请求参数非法"
            if "idempotency_key" in err_text:
                err_code = STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY
                err_message = message_of(STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY)
            elif "sales_order" in err_text:
                err_code = STYLE_PROFIT_SALES_ORDER_REQUIRED
                err_message = message_of(STYLE_PROFIT_SALES_ORDER_REQUIRED)
            elif "revenue_mode" in err_text:
                err_code = STYLE_PROFIT_INVALID_REVENUE_MODE
                err_message = message_of(STYLE_PROFIT_INVALID_REVENUE_MODE)
            elif "formula_version" in err_text:
                err_code = STYLE_PROFIT_INVALID_FORMULA_VERSION
                err_message = message_of(STYLE_PROFIT_INVALID_FORMULA_VERSION)
            elif "from_date" in err_text or "to_date" in err_text:
                err_code = STYLE_PROFIT_INVALID_PERIOD
                err_message = message_of(STYLE_PROFIT_INVALID_PERIOD)
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=err_code,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(err_code, err_message, status_of(err_code))

        if selector.revenue_mode not in {"actual_first", "actual_only", "estimated_only"}:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=STYLE_PROFIT_INVALID_REVENUE_MODE,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(
                STYLE_PROFIT_INVALID_REVENUE_MODE,
                message_of(STYLE_PROFIT_INVALID_REVENUE_MODE),
                status_of(STYLE_PROFIT_INVALID_REVENUE_MODE),
            )

        if selector.from_date > selector.to_date:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=STYLE_PROFIT_INVALID_PERIOD,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(
                STYLE_PROFIT_INVALID_PERIOD,
                message_of(STYLE_PROFIT_INVALID_PERIOD),
                status_of(STYLE_PROFIT_INVALID_PERIOD),
            )

        if selector.formula_version != "STYLE_PROFIT_V1":
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=STYLE_PROFIT_INVALID_FORMULA_VERSION,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(
                STYLE_PROFIT_INVALID_FORMULA_VERSION,
                message_of(STYLE_PROFIT_INVALID_FORMULA_VERSION),
                status_of(STYLE_PROFIT_INVALID_FORMULA_VERSION),
            )

        resource_no = selector.sales_order
        create_request: StyleProfitSnapshotCreateRequest = collector.collect(selector)
        if not create_request.sales_invoice_rows and not create_request.sales_order_rows:
            try:
                _record_failure_safely(
                    session=session,
                    audit=audit,
                    context=context,
                    request=request,
                    action=action,
                    current_user=current_user,
                    resource_id=None,
                    resource_no=resource_no,
                    error_code=STYLE_PROFIT_REVENUE_SOURCE_REQUIRED,
                )
            except AuditWriteFailed as audit_exc:
                return _app_err(audit_exc)
            return _err(
                STYLE_PROFIT_REVENUE_SOURCE_REQUIRED,
                message_of(STYLE_PROFIT_REVENUE_SOURCE_REQUIRED),
                status_of(STYLE_PROFIT_REVENUE_SOURCE_REQUIRED),
            )

        result = service.create_snapshot(
            session=session,
            request=create_request,
            operator=current_user.username,
        )

        audit.record_success(
            module="style_profit",
            action=action,
            operator=current_user.username,
            operator_roles=current_user.roles,
            resource_type="STYLE_PROFIT_SNAPSHOT",
            resource_id=result.snapshot_id,
            resource_no=result.snapshot_no,
            before_data=None,
            after_data=result.model_dump(mode="json"),
            context=context,
        )
        _commit_or_raise_write_error(session)
        return _ok(result.model_dump(mode="json"))
    except HTTPException as exc:
        session.rollback()
        return _http_exc_err(exc)
    except AuditWriteFailed as exc:
        session.rollback()
        return _app_err(exc)
    except AppException as exc:
        session.rollback()
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(exc)
    except SQLAlchemyError:
        session.rollback()
        db_exc = DatabaseWriteFailed()
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=db_exc.code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _app_err(db_exc)
    except Exception:
        session.rollback()
        code = STYLE_PROFIT_INTERNAL_ERROR
        try:
            _record_failure_safely(
                session=session,
                audit=audit,
                context=context,
                request=request,
                action=action,
                current_user=current_user,
                resource_id=None,
                resource_no=resource_no,
                error_code=code,
            )
        except AuditWriteFailed as audit_exc:
            return _app_err(audit_exc)
        return _err(code, message_of(code), status_of(code))
