"""Runtime config helpers for workshop worker diagnostics."""

from __future__ import annotations

import os


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, *, default: int, minimum: int = 0, maximum: int = 1_000_000) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def workshop_forbidden_diagnostic_limit() -> int:
    """Max rows scanned in one forbidden diagnostics run."""
    return _env_int("WORKSHOP_FORBIDDEN_DIAGNOSTIC_LIMIT", default=50, minimum=1, maximum=10_000)


def workshop_denial_audit_cooldown_seconds() -> int:
    """Cooldown seconds for repeated forbidden diagnostics security audit."""
    return _env_int("WORKSHOP_OUTBOX_DENIAL_AUDIT_COOLDOWN_SECONDS", default=21600, minimum=1, maximum=604800)


def workshop_enable_forbidden_diagnostics() -> bool:
    """Whether worker is allowed to run forbidden diagnostics scan."""
    return _env_flag("WORKSHOP_ENABLE_FORBIDDEN_DIAGNOSTICS", default=False)


def workshop_enable_worker_dry_run() -> bool:
    """Whether internal worker dry-run is enabled for current environment.

    Production default is disabled unless explicitly enabled.
    Non-production default is enabled for diagnostics.
    """
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return _env_flag("WORKSHOP_ENABLE_WORKER_DRY_RUN", default=False)
    return _env_flag("WORKSHOP_ENABLE_WORKER_DRY_RUN", default=True)


def production_enable_work_order_worker_sync() -> bool:
    """Whether production Work Order worker may execute non-dry-run ERP sync."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return _env_flag("PRODUCTION_ENABLE_WORK_ORDER_WORKER_SYNC", default=False)
    return _env_flag("PRODUCTION_ENABLE_WORK_ORDER_WORKER_SYNC", default=True)


def warehouse_enable_stock_entry_worker_sync() -> bool:
    """Whether warehouse Stock Entry worker may execute non-dry-run ERP sync."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return _env_flag("WAREHOUSE_ENABLE_STOCK_ENTRY_WORKER_SYNC", default=False)
    return _env_flag("WAREHOUSE_ENABLE_STOCK_ENTRY_WORKER_SYNC", default=True)


def workshop_enable_job_card_worker_sync() -> bool:
    """Whether workshop Job Card worker may execute non-dry-run ERP sync."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return _env_flag("WORKSHOP_ENABLE_JOB_CARD_WORKER_SYNC", default=False)
    return _env_flag("WORKSHOP_ENABLE_JOB_CARD_WORKER_SYNC", default=True)


def factory_statement_enable_payable_worker_sync() -> bool:
    """Whether factory statement payable worker may execute non-dry-run ERP sync."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return _env_flag("FACTORY_STATEMENT_ENABLE_PAYABLE_WORKER_SYNC", default=False)
    return _env_flag("FACTORY_STATEMENT_ENABLE_PAYABLE_WORKER_SYNC", default=True)


def quality_enable_outbox_worker_sync() -> bool:
    """Whether quality outbox worker may execute non-dry-run ERP sync."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return _env_flag("QUALITY_ENABLE_OUTBOX_WORKER_SYNC", default=False)
    return _env_flag("QUALITY_ENABLE_OUTBOX_WORKER_SYNC", default=True)


def workshop_dry_run_audit_required() -> bool:
    """Whether dry-run path must write operation audit.

    In production this cannot be disabled.
    """
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env == "production":
        return True
    return _env_flag("WORKSHOP_DRY_RUN_AUDIT_REQUIRED", default=True)


def subcontract_enable_internal_stock_worker_api() -> bool:
    """Whether subcontract internal stock worker API is enabled.

    Production defaults to disabled unless explicitly enabled.
    """
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env != "production":
        return _env_flag("ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API", default=True)
    return _env_flag("ENABLE_SUBCONTRACT_INTERNAL_STOCK_WORKER_API", default=False)


def subcontract_enable_stock_worker_dry_run() -> bool:
    """Whether subcontract internal stock worker dry-run is enabled."""
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env != "production":
        return _env_flag("SUBCONTRACT_ENABLE_STOCK_WORKER_DRY_RUN", default=True)
    return _env_flag("SUBCONTRACT_ENABLE_STOCK_WORKER_DRY_RUN", default=False)
