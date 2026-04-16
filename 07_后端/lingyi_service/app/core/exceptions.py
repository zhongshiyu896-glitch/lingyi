"""Core business exceptions."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.error_codes import AUDIT_WRITE_FAILED
from app.core.error_codes import AUTH_UNAUTHENTICATED
from app.core.error_codes import BOM_INTERNAL_ERROR
from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.error_codes import ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN
from app.core.error_codes import EXTERNAL_SERVICE_UNAVAILABLE
from app.core.error_codes import ERPNEXT_SERVICE_UNAVAILABLE
from app.core.error_codes import ERPNEXT_TIMEOUT
from app.core.error_codes import ERPNEXT_AUTH_FAILED
from app.core.error_codes import ERPNEXT_RESOURCE_NOT_FOUND
from app.core.error_codes import ERPNEXT_RESPONSE_INVALID
from app.core.error_codes import ERPNEXT_DOCSTATUS_REQUIRED
from app.core.error_codes import ERPNEXT_DOCSTATUS_INVALID
from app.core.error_codes import INTERNAL_ERROR
from app.core.error_codes import INTERNAL_API_DISABLED
from app.core.error_codes import PERMISSION_SOURCE_UNAVAILABLE
from app.core.error_codes import RESOURCE_ACCESS_DENIED
from app.core.error_codes import RESOURCE_NOT_FOUND
from app.core.error_codes import SERVICE_ACCOUNT_RESOURCE_FORBIDDEN
from app.core.error_codes import SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED
from app.core.error_codes import SUBCONTRACT_COMPANY_AMBIGUOUS
from app.core.error_codes import SUBCONTRACT_COMPANY_REQUIRED
from app.core.error_codes import SUBCONTRACT_COMPANY_UNRESOLVED
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_CANDIDATE_NOT_FOUND
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_STATEMENT_REQUIRED
from app.core.error_codes import SUBCONTRACT_SETTLEMENT_STATUS_INVALID
from app.core.error_codes import SUBCONTRACT_INSPECTION_NOT_IMPLEMENTED
from app.core.error_codes import SUBCONTRACT_OUTBOX_REQUIRED
from app.core.error_codes import SUBCONTRACT_SCOPE_BLOCKED
from app.core.error_codes import WORKSHOP_INTERNAL_ERROR
from app.core.error_codes import WORKSHOP_DRY_RUN_DISABLED
from app.core.error_codes import SUBCONTRACT_INTERNAL_ERROR
from app.core.error_codes import PRODUCTION_INTERNAL_ERROR
from app.core.logging import REDACTED_MESSAGE
from app.core.logging import sanitize_log_message
from app.core.error_codes import message_of
from app.core.error_codes import status_of


class AppException(Exception):
    """Base app exception with standardized code/status/message."""

    def __init__(self, code: str, message: str | None = None, status_code: int | None = None):
        self.code = code
        self.message = message or message_of(code)
        self.status_code = status_code or status_of(code)
        super().__init__(self.message)


class BusinessException(AppException):
    """Business rule exception."""


class PermissionException(AppException):
    """Permission exception."""


class AuthUnauthenticatedError(AppException):
    """Raised when request is unauthenticated."""

    def __init__(self, message: str | None = None):
        super().__init__(code=AUTH_UNAUTHENTICATED, message=message)


class ResourceAccessDeniedError(AppException):
    """Raised when authenticated principal has no resource scope."""

    def __init__(self, message: str | None = None):
        super().__init__(code=RESOURCE_ACCESS_DENIED, message=message)


class ResourceNotFoundError(AppException):
    """Raised when target resource does not exist."""

    def __init__(self, message: str | None = None):
        super().__init__(code=RESOURCE_NOT_FOUND, message=message)


@dataclass
class PermissionSourceUnavailable(Exception):
    """Raised when ERPNext permission source is unavailable."""

    message: str
    exception_type: str = "PermissionSourceUnavailable"
    exception_message: str = ""

    def sanitized_detail(self) -> str:
        """Return redacted safe detail for logs/audit."""
        detail = sanitize_log_message(self.exception_message or self.message)
        return detail or REDACTED_MESSAGE


class AuditWriteFailed(AppException):
    """Raised when operation/security audit persistence fails."""

    def __init__(self, message: str | None = None):
        super().__init__(code=AUDIT_WRITE_FAILED, message=message)


class DatabaseReadFailed(AppException):
    """Raised when business database read fails."""

    def __init__(self, message: str | None = None):
        super().__init__(code=DATABASE_READ_FAILED, message=message)


class DatabaseWriteFailed(AppException):
    """Raised when business database write fails."""

    def __init__(self, message: str | None = None):
        super().__init__(code=DATABASE_WRITE_FAILED, message=message)


class BomInternalError(AppException):
    """Raised for unknown internal failures."""

    def __init__(self, message: str | None = None):
        super().__init__(code=BOM_INTERNAL_ERROR, message=message)


class WorkshopInternalError(AppException):
    """Raised for unknown workshop failures."""

    def __init__(self, message: str | None = None):
        super().__init__(code=WORKSHOP_INTERNAL_ERROR, message=message)


class SubcontractInternalError(AppException):
    """Raised for unknown subcontract failures."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_INTERNAL_ERROR, message=message)


class ProductionInternalError(AppException):
    """Raised for unknown production failures."""

    def __init__(self, message: str | None = None):
        super().__init__(code=PRODUCTION_INTERNAL_ERROR, message=message)


class SubcontractOutboxRequiredError(AppException):
    """Raised when subcontract action is gated by outbox stage boundary."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_OUTBOX_REQUIRED, message=message)


class SubcontractInspectionNotImplementedError(AppException):
    """Raised when subcontract inspection pricing contract is not implemented."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_INSPECTION_NOT_IMPLEMENTED, message=message)


class SubcontractCompanyRequiredError(AppException):
    """Raised when subcontract company fact is missing."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_COMPANY_REQUIRED, message=message)


class SubcontractCompanyUnresolvedError(AppException):
    """Raised when subcontract company cannot be uniquely resolved."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_COMPANY_UNRESOLVED, message=message)


class SubcontractCompanyAmbiguousError(AppException):
    """Raised when subcontract company has multiple candidates."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_COMPANY_AMBIGUOUS, message=message)


class SubcontractScopeBlockedError(AppException):
    """Raised when subcontract order scope is blocked."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_SCOPE_BLOCKED, message=message)


class SubcontractSettlementCandidateNotFoundError(AppException):
    """Raised when settlement candidate row cannot be found."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_SETTLEMENT_CANDIDATE_NOT_FOUND, message=message)


class SubcontractSettlementAlreadyLockedError(AppException):
    """Raised when settlement row has been locked by another statement."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED, message=message)


class SubcontractSettlementStatusInvalidError(AppException):
    """Raised when settlement row status does not allow current operation."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_SETTLEMENT_STATUS_INVALID, message=message)


class SubcontractSettlementIdempotencyConflictError(AppException):
    """Raised when settlement lock/release idempotency key conflicts."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT, message=message)


class SubcontractSettlementStatementRequiredError(AppException):
    """Raised when settlement statement identifier is missing."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SUBCONTRACT_SETTLEMENT_STATEMENT_REQUIRED, message=message)


class ERPNextServiceUnavailableError(AppException):
    """Raised when ERPNext service is unavailable."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_SERVICE_UNAVAILABLE, message=message)


class ERPNextServiceAccountForbiddenError(AppException):
    """Raised when ERPNext service account lacks required scope."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_SERVICE_ACCOUNT_FORBIDDEN, message=message)


class ERPNextTimeoutError(AppException):
    """Raised when ERPNext request times out."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_TIMEOUT, message=message)


class ERPNextAuthFailedError(AppException):
    """Raised when ERPNext returns 401/403 for integration calls."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_AUTH_FAILED, message=message)


class ERPNextResourceNotFoundError(AppException):
    """Raised when ERPNext returns 404 for required resource."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_RESOURCE_NOT_FOUND, message=message)


class ERPNextResponseInvalidError(AppException):
    """Raised when ERPNext response schema is malformed."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_RESPONSE_INVALID, message=message)


class ERPNextDocstatusRequiredError(AppException):
    """Raised when ERPNext response omits required docstatus."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_DOCSTATUS_REQUIRED, message=message)


class ERPNextDocstatusInvalidError(AppException):
    """Raised when ERPNext docstatus/status violates fail-closed policy."""

    def __init__(self, message: str | None = None):
        super().__init__(code=ERPNEXT_DOCSTATUS_INVALID, message=message)


class InternalApiDisabledError(AppException):
    """Raised when internal API endpoint is disabled by runtime config."""

    def __init__(self, message: str | None = None):
        super().__init__(code=INTERNAL_API_DISABLED, message=message)


class ServiceAccountResourceForbiddenError(AppException):
    """Raised when service account lacks required item/company scope."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SERVICE_ACCOUNT_RESOURCE_FORBIDDEN, message=message)


class ServiceAccountResourceScopeRequiredError(AppException):
    """Raised when outbox row lacks required scope fields."""

    def __init__(self, message: str | None = None):
        super().__init__(code=SERVICE_ACCOUNT_RESOURCE_SCOPE_REQUIRED, message=message)


class WorkshopDryRunDisabledError(AppException):
    """Raised when worker dry-run is disabled by runtime config."""

    def __init__(self, message: str | None = None):
        super().__init__(code=WORKSHOP_DRY_RUN_DISABLED, message=message)


class SecurityAuditWriteError(AuditWriteFailed):
    """Backward-compatible alias for security audit write failures."""


class PermissionSourceUnavailableError(AppException):
    """Optional adapter exception with standard code mapping."""

    def __init__(self, message: str | None = None):
        super().__init__(code=PERMISSION_SOURCE_UNAVAILABLE, message=message)


class ExternalServiceUnavailableError(AppException):
    """Raised when downstream external service is unavailable."""

    def __init__(self, message: str | None = None):
        super().__init__(code=EXTERNAL_SERVICE_UNAVAILABLE, message=message)


class InternalError(AppException):
    """Raised for generic internal failures."""

    def __init__(self, message: str | None = None):
        super().__init__(code=INTERNAL_ERROR, message=message)


def is_default_bom_unique_conflict(exc: BaseException) -> bool:
    """Return whether DB integrity error points to default-BOM partial unique index."""
    target = "uk_ly_apparel_bom_one_active_default"
    raw = f"{exc}"
    orig = getattr(exc, "orig", None)
    if orig is not None:
        raw = f"{raw} {orig}"
    return target in raw.lower()
