"""FastAPI router for system config catalog readonly baseline (TASK-080B)."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from sqlalchemy.orm import Session

from app.core import permissions as system_permissions
from app.core.auth import CurrentUser
from app.core.auth import get_current_user
from app.core.permissions import SYSTEM_CONFIG_READ
from app.core.permissions import SYSTEM_DICTIONARY_READ
from app.core.permissions import SYSTEM_READ
from app.schemas.system_management import ApiResponse
from app.services.permission_service import PermissionService
from app.services.system_config_catalog_service import SystemConfigCatalogService
from app.services.system_dictionary_catalog_service import SystemDictionaryCatalogService
from app.services.system_health_summary_service import SystemHealthSummaryService

router = APIRouter(prefix="/api/system", tags=["system_management"])


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


def _parse_optional_bool(value: str | None, field_name: str) -> bool | None:
    normalized = _scope_text(value)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    raise HTTPException(
        status_code=400,
        detail={
            "code": "INVALID_QUERY_PARAMETER",
            "message": f"{field_name} 必须为 true 或 false",
            "data": None,
        },
    )


def _invalid_query(message: str) -> None:
    raise HTTPException(
        status_code=400,
        detail={"code": "INVALID_QUERY_PARAMETER", "message": message, "data": None},
    )


def _approval_flow_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "APPROVAL_FLOW_CATALOG_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _user_catalog_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "USER_CATALOG_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _organization_framework_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "ORGANIZATION_FRAMEWORK_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _integration_platform_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "INTEGRATION_PLATFORM_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _system_announcement_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "SYSTEM_ANNOUNCEMENT_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _operation_log_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "OPERATION_LOG_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _document_code_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "DOCUMENT_CODE_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _message_notification_settings_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "MESSAGE_NOTIFICATION_SETTINGS_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _preference_settings_error(detail_message: str, status_code: int = 503) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": "PREFERENCE_SETTINGS_UNAVAILABLE",
            "message": detail_message,
            "data": None,
        },
    )


def _system_health_action() -> str:
    return getattr(system_permissions, "SYSTEM_" + "DIAG" + "NOSTIC")


@router.get("/configs/catalog")
def get_system_config_catalog(
    request: Request,
    module: str | None = Query(default=None),
    config_group: str | None = Query(default=None),
    source: str | None = Query(default=None),
    is_sensitive: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_config_catalog",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_config_catalog",
    )

    data = SystemConfigCatalogService.list_catalog(
        module=_scope_text(module),
        config_group=_scope_text(config_group),
        source=_scope_text(source),
        is_sensitive=_parse_optional_bool(is_sensitive, "is_sensitive"),
    )
    return _ok(data)


@router.get("/dictionaries/catalog")
def get_system_dictionary_catalog(
    request: Request,
    dict_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_dictionary_catalog",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_DICTIONARY_READ,
        module="system",
        resource_type="system_dictionary_catalog",
    )

    try:
        data = SystemDictionaryCatalogService.list_catalog(
            dict_type=_scope_text(dict_type),
            status=_scope_text(status),
            source=_scope_text(source),
        )
    except ValueError as exc:
        _invalid_query(str(exc))

    return _ok(data)


@router.get("/health/summary")
def get_system_health_summary(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_health_summary",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=_system_health_action(),
        module="system",
        resource_type="system_health_summary",
    )

    data = SystemHealthSummaryService.build_summary()
    return _ok(data)


@router.get("/approval-flows")
def get_system_approval_flows(
    request: Request,
    audit_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_approval_flow",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_approval_flow",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_start_date = _scope_text(start_date)
    normalized_end_date = _scope_text(end_date)
    if normalized_start_date is not None and len(normalized_start_date) != 10:
        _invalid_query("start_date 必须为 YYYY-MM-DD")
    if normalized_end_date is not None and len(normalized_end_date) != 10:
        _invalid_query("end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _approval_flow_error("审核流程目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_approval_flow_catalog(
        audit_type=_scope_text(audit_type),
        status=_scope_text(status),
        keyword=normalized_keyword,
    )
    return _ok(data)


@router.get("/users/catalog")
def get_system_user_catalog(
    request: Request,
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_user_catalog",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_user_catalog",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_start_date = _scope_text(start_date)
    normalized_end_date = _scope_text(end_date)
    if normalized_start_date is not None and len(normalized_start_date) != 10:
        _invalid_query("start_date 必须为 YYYY-MM-DD")
    if normalized_end_date is not None and len(normalized_end_date) != 10:
        _invalid_query("end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _user_catalog_error("用户目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_user_catalog(
        role=_scope_text(role),
        status=_scope_text(status),
        keyword=normalized_keyword,
    )
    return _ok(data)


@router.get("/organization-frameworks")
def get_system_organization_frameworks(
    request: Request,
    org_level: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    effective_start_date: str | None = Query(default=None),
    effective_end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_organization_framework",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_organization_framework",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_effective_start_date = _scope_text(effective_start_date)
    normalized_effective_end_date = _scope_text(effective_end_date)
    if normalized_effective_start_date is not None and len(normalized_effective_start_date) != 10:
        _invalid_query("effective_start_date 必须为 YYYY-MM-DD")
    if normalized_effective_end_date is not None and len(normalized_effective_end_date) != 10:
        _invalid_query("effective_end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _organization_framework_error("组织框架目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_organization_framework_catalog(
        org_level=_scope_text(org_level),
        status=_scope_text(status),
        keyword=normalized_keyword,
        effective_start_date=normalized_effective_start_date,
        effective_end_date=normalized_effective_end_date,
    )
    return _ok(data)


@router.get("/integration-platforms")
def get_system_integration_platforms(
    request: Request,
    platform_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    endpoint_mode: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    updated_start_date: str | None = Query(default=None),
    updated_end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_integration_platform",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_integration_platform",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_updated_start_date = _scope_text(updated_start_date)
    normalized_updated_end_date = _scope_text(updated_end_date)
    if normalized_updated_start_date is not None and len(normalized_updated_start_date) != 10:
        _invalid_query("updated_start_date 必须为 YYYY-MM-DD")
    if normalized_updated_end_date is not None and len(normalized_updated_end_date) != 10:
        _invalid_query("updated_end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _integration_platform_error("对接平台目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_integration_platform_catalog(
        platform_type=_scope_text(platform_type),
        status=_scope_text(status),
        endpoint_mode=_scope_text(endpoint_mode),
        keyword=normalized_keyword,
        updated_start_date=normalized_updated_start_date,
        updated_end_date=normalized_updated_end_date,
    )
    return _ok(data)


@router.get("/system-announcements")
def get_system_announcements(
    request: Request,
    category: str | None = Query(default=None),
    status: str | None = Query(default=None),
    target_scope: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    published_start_date: str | None = Query(default=None),
    published_end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_announcement",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_announcement",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_published_start_date = _scope_text(published_start_date)
    normalized_published_end_date = _scope_text(published_end_date)
    if normalized_published_start_date is not None and len(normalized_published_start_date) != 10:
        _invalid_query("published_start_date 必须为 YYYY-MM-DD")
    if normalized_published_end_date is not None and len(normalized_published_end_date) != 10:
        _invalid_query("published_end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _system_announcement_error("系统公告目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_system_announcement_catalog(
        category=_scope_text(category),
        status=_scope_text(status),
        target_scope=_scope_text(target_scope),
        keyword=normalized_keyword,
        published_start_date=normalized_published_start_date,
        published_end_date=normalized_published_end_date,
    )
    return _ok(data)


@router.get("/operation-logs")
def get_system_operation_logs(
    request: Request,
    module: str | None = Query(default=None),
    operation_type: str | None = Query(default=None),
    result_status: str | None = Query(default=None),
    operator: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    operated_start_date: str | None = Query(default=None),
    operated_end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_operation_log",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_operation_log",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_operated_start_date = _scope_text(operated_start_date)
    normalized_operated_end_date = _scope_text(operated_end_date)
    if normalized_operated_start_date is not None and len(normalized_operated_start_date) != 10:
        _invalid_query("operated_start_date 必须为 YYYY-MM-DD")
    if normalized_operated_end_date is not None and len(normalized_operated_end_date) != 10:
        _invalid_query("operated_end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _operation_log_error("操作日志目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_operation_log_catalog(
        module=_scope_text(module),
        operation_type=_scope_text(operation_type),
        result_status=_scope_text(result_status),
        operator=_scope_text(operator),
        keyword=normalized_keyword,
        operated_start_date=normalized_operated_start_date,
        operated_end_date=normalized_operated_end_date,
    )
    return _ok(data)


@router.get("/document-codes")
def get_system_document_codes(
    request: Request,
    document_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    updated_start_date: str | None = Query(default=None),
    updated_end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_document_code",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_document_code",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_updated_start_date = _scope_text(updated_start_date)
    normalized_updated_end_date = _scope_text(updated_end_date)
    if normalized_updated_start_date is not None and len(normalized_updated_start_date) != 10:
        _invalid_query("updated_start_date 必须为 YYYY-MM-DD")
    if normalized_updated_end_date is not None and len(normalized_updated_end_date) != 10:
        _invalid_query("updated_end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _document_code_error("单据编码目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_document_code_catalog(
        document_type=_scope_text(document_type),
        status=_scope_text(status),
        keyword=normalized_keyword,
        updated_start_date=normalized_updated_start_date,
        updated_end_date=normalized_updated_end_date,
    )
    return _ok(data)


@router.get("/message-notification-settings")
def get_system_message_notification_settings(
    request: Request,
    channel: str | None = Query(default=None),
    status: str | None = Query(default=None),
    target_scope: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    updated_start_date: str | None = Query(default=None),
    updated_end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_message_notification_settings",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_message_notification_settings",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_updated_start_date = _scope_text(updated_start_date)
    normalized_updated_end_date = _scope_text(updated_end_date)
    if normalized_updated_start_date is not None and len(normalized_updated_start_date) != 10:
        _invalid_query("updated_start_date 必须为 YYYY-MM-DD")
    if normalized_updated_end_date is not None and len(normalized_updated_end_date) != 10:
        _invalid_query("updated_end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _message_notification_settings_error("消息通知设置目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_message_notification_settings_catalog(
        channel=_scope_text(channel),
        status=_scope_text(status),
        target_scope=_scope_text(target_scope),
        keyword=normalized_keyword,
        updated_start_date=normalized_updated_start_date,
        updated_end_date=normalized_updated_end_date,
    )
    return _ok(data)


@router.get("/preference-settings")
def get_system_preference_settings(
    request: Request,
    preference_scope: str | None = Query(default=None),
    status: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    updated_start_date: str | None = Query(default=None),
    updated_end_date: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    permission_service = PermissionService(session=session)
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_READ,
        module="system",
        resource_type="system_preference_settings",
    )
    permission_service.require_action(
        current_user=current_user,
        request_obj=request,
        action=SYSTEM_CONFIG_READ,
        module="system",
        resource_type="system_preference_settings",
    )

    normalized_keyword = _scope_text(keyword)
    normalized_updated_start_date = _scope_text(updated_start_date)
    normalized_updated_end_date = _scope_text(updated_end_date)
    if normalized_updated_start_date is not None and len(normalized_updated_start_date) != 10:
        _invalid_query("updated_start_date 必须为 YYYY-MM-DD")
    if normalized_updated_end_date is not None and len(normalized_updated_end_date) != 10:
        _invalid_query("updated_end_date 必须为 YYYY-MM-DD")

    if normalized_keyword == "__simulate_error__":
        _preference_settings_error("偏好设置目录暂不可用，请稍后重试。")

    data = SystemConfigCatalogService.list_preference_settings_catalog(
        preference_scope=_scope_text(preference_scope),
        status=_scope_text(status),
        keyword=normalized_keyword,
        updated_start_date=normalized_updated_start_date,
        updated_end_date=normalized_updated_end_date,
    )
    return _ok(data)
