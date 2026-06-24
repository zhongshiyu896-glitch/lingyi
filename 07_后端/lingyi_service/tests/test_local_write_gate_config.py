"""Local write-gate config must support isolated dev/b databases."""

from __future__ import annotations

import pytest

from app.core.config import DEFAULT_DEV_B_DATABASE_URL
from app.core.config import DEFAULT_LOCAL_DEV_DATABASE_URL
from app.core.config import allowed_local_database_urls
from app.core.config import configured_database_url
from app.core.config import is_allowed_local_dev_database
from app.routers import bom
from app.routers import factory_statement
from app.routers import quality
from app.routers import sales_inventory
from app.routers import style_profit
from app.routers import subcontract
from app.routers import warehouse
from app.routers import workshop
from app.services.cross_module_view_service import CrossModuleViewService
from app.services.factory_statement_service import FactoryStatementService
from app.services.production_service import ProductionService
from app.services.quality_service import QualitySourceValidator
from app.services.subcontract_service import SubcontractService
from app.services.warehouse_service import WarehouseService
from app.services.workshop_service import WorkshopService


def _set_runtime(monkeypatch: pytest.MonkeyPatch, db_url: str, *, app_env: str = "development") -> None:
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("LINGYI_DB_URL", db_url)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("LINGYI_ALLOW_DEV_AUTH", "true")
    monkeypatch.setenv("LINGYI_PERMISSION_SOURCE", "static")
    monkeypatch.delenv("LINGYI_ALLOWED_LOCAL_DB_URLS", raising=False)


def test_default_local_write_gate_allowlist_includes_a_and_dev_b() -> None:
    assert allowed_local_database_urls() == {DEFAULT_LOCAL_DEV_DATABASE_URL, DEFAULT_DEV_B_DATABASE_URL}


def test_configured_database_url_falls_back_to_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LINGYI_DB_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", DEFAULT_DEV_B_DATABASE_URL)

    assert configured_database_url() == DEFAULT_DEV_B_DATABASE_URL


@pytest.mark.parametrize("db_url", [DEFAULT_LOCAL_DEV_DATABASE_URL, DEFAULT_DEV_B_DATABASE_URL])
def test_core_write_gates_allow_default_local_databases(monkeypatch: pytest.MonkeyPatch, db_url: str) -> None:
    _set_runtime(monkeypatch, db_url)

    assert is_allowed_local_dev_database()
    assert warehouse._is_local_warehouse_write_enabled()
    assert warehouse._is_local_warehouse_read_enabled()
    assert sales_inventory._is_local_sales_order_write_enabled()
    assert sales_inventory._is_local_reference_write_enabled()
    assert sales_inventory._is_local_sales_inventory_read_enabled()
    assert bom._is_local_bom_write_enabled()
    assert factory_statement._is_local_factory_statement_write_enabled()
    assert workshop._is_local_workshop_write_enabled()
    assert style_profit._is_local_style_profit_write_enabled()

    quality._ensure_local_dev_write_gate()
    subcontract._ensure_local_dev_write_gate()
    ProductionService._ensure_local_dev_write_gate()

    assert ProductionService._is_local_scenario_context_enabled()
    assert CrossModuleViewService._is_local_dev_sqlite_mode()
    assert FactoryStatementService._is_local_dev_sqlite_mode()
    assert WorkshopService._is_local_synthetic_context_enabled()
    assert QualitySourceValidator().local_dev_mode
    assert WarehouseService(session=object())._local_read_fallback_enabled()

    subcontract_service = SubcontractService.__new__(SubcontractService)
    subcontract_service._is_sqlite = True
    assert subcontract_service._local_dev_sync_substitute_enabled()


def test_local_write_gate_rejects_production_even_for_allowed_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_runtime(monkeypatch, DEFAULT_DEV_B_DATABASE_URL, app_env="production")

    assert not is_allowed_local_dev_database()
    assert not warehouse._is_local_warehouse_write_enabled()
    with pytest.raises(Exception):
        ProductionService._ensure_local_dev_write_gate()


def test_local_write_gate_supports_operator_allowlist_override(monkeypatch: pytest.MonkeyPatch) -> None:
    custom_url = "sqlite:///./lingyi_service.custom.db"
    _set_runtime(monkeypatch, custom_url)
    monkeypatch.setenv("LINGYI_ALLOWED_LOCAL_DB_URLS", f"{custom_url};sqlite:///./another.db")

    assert is_allowed_local_dev_database()
    assert allowed_local_database_urls() == {custom_url, "sqlite:///./another.db"}
