"""PostgreSQL integration tests for subcontract settlement idempotency replay (TASK-002H3)."""

from __future__ import annotations

import os
import re
import threading
from decimal import Decimal
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractSettlementOperation
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep
from migrations.versions import task_001_create_bom_tables as migration_001
from migrations.versions import task_002c_subcontract_company_and_schema as migration_002c
from migrations.versions import task_002f_inspection_detail_and_idempotency as migration_002f
from migrations.versions import task_002h_subcontract_settlement_export as migration_002h
from migrations.versions import task_002h1_subcontract_settlement_operation_idempotency as migration_002h1


SCHEMA = "ly_schema"
DESTRUCTIVE_FLAG_ENV = "POSTGRES_TEST_ALLOW_DESTRUCTIVE"
_TEST_DB_PATTERNS = (
    re.compile(r".*_test$", re.IGNORECASE),
    re.compile(r"test_.*", re.IGNORECASE),
    re.compile(r"lingyi_test_.*", re.IGNORECASE),
    re.compile(r"tmp_lingyi_.*", re.IGNORECASE),
)


class PostgresDestructiveGateError(RuntimeError):
    """Raised when destructive PostgreSQL test precondition is not satisfied."""


def _redact_dsn(dsn: str) -> str:
    try:
        from sqlalchemy.engine import make_url

        parsed = make_url(dsn)
        host = parsed.host or "unknown-host"
        port = f":{parsed.port}" if parsed.port else ""
        database = parsed.database or "unknown-db"
        return f"{parsed.drivername}://***@{host}{port}/{database}"
    except Exception:
        return "invalid-dsn"


def _is_allowed_test_database_name(database_name: str | None) -> bool:
    name = str(database_name or "").strip()
    if not name:
        return False
    return any(pattern.fullmatch(name) for pattern in _TEST_DB_PATTERNS)


def _load_current_database_name(engine) -> str:
    with engine.connect() as conn:
        value = conn.execute(text("SELECT current_database()")).scalar_one()
    return str(value or "").strip()


def _ensure_destructive_pg_test_gate(*, engine, dsn: str) -> str:
    allow_destructive = str(os.getenv(DESTRUCTIVE_FLAG_ENV, "") or "").strip().lower() == "true"
    redacted_dsn = _redact_dsn(dsn)
    if not allow_destructive:
        raise PostgresDestructiveGateError(
            f"destructive PostgreSQL test is blocked: set {DESTRUCTIVE_FLAG_ENV}=true "
            f"(target={redacted_dsn})"
        )

    current_database = _load_current_database_name(engine)
    if not _is_allowed_test_database_name(current_database):
        raise PostgresDestructiveGateError(
            "destructive PostgreSQL test is blocked: current_database() is not in test allowlist "
            f"(db={current_database}, target={redacted_dsn})"
        )
    return current_database


def _reset_test_schema(*, engine, dsn: str) -> None:
    _ensure_destructive_pg_test_gate(engine=engine, dsn=dsn)
    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))


def _create_pg_engine_or_skip(dsn: str):
    try:
        return create_engine(dsn, future=True, pool_pre_ping=True)
    except ModuleNotFoundError as exc:
        if str(getattr(exc, "name", "")).startswith("psycopg"):
            pytest.skip("PostgreSQL driver is not installed in this environment; skipping postgresql integration tests")
        raise


def _run_migration_upgrade(engine, module) -> None:
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    with engine.begin() as conn:
        context = MigrationContext.configure(conn)
        operations = Operations(context)
        previous_op = module.op
        module.op = operations
        try:
            module.upgrade()
        finally:
            module.op = previous_op


def _run_settlement_chain(engine) -> None:
    _run_migration_upgrade(engine, migration_001)
    _run_migration_upgrade(engine, migration_002c)
    _run_migration_upgrade(engine, migration_002f)
    _run_migration_upgrade(engine, migration_002h)
    _run_migration_upgrade(engine, migration_002h1)
    _ensure_settlement_runtime_columns(engine)


def _ensure_settlement_runtime_columns(engine) -> None:
    inspector = inspect(engine)
    existing = {str(col.get("name")) for col in inspector.get_columns("ly_subcontract_order", schema=SCHEMA)}
    if "settlement_status" in existing:
        return
    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE ly_schema.ly_subcontract_order "
                "ADD COLUMN settlement_status VARCHAR(32) NOT NULL DEFAULT 'unsettled'"
            )
        )


@pytest.fixture(scope="module")
def postgres_dsn() -> str:
    dsn = str(os.getenv("POSTGRES_TEST_DSN", "") or "").strip()
    # Treat placeholder env strings as unset.
    if not dsn or dsn.startswith("${") or dsn.startswith("$("):
        pytest.skip("POSTGRES_TEST_DSN is not set; skipping PostgreSQL settlement integration tests")
    return dsn


@pytest.fixture()
def pg_app_env(postgres_dsn: str):
    engine = _create_pg_engine_or_skip(postgres_dsn)

    try:
        _reset_test_schema(engine=engine, dsn=postgres_dsn)
    except PostgresDestructiveGateError as exc:
        engine.dispose()
        pytest.skip(str(exc))

    _run_settlement_chain(engine)

    # Ensure all runtime-dependent tables exist for API calls.
    BomBase.metadata.create_all(bind=engine)
    if "ly_schema.ly_apparel_bom" not in SubcontractBase.metadata.tables:
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
    SubcontractBase.metadata.create_all(bind=engine)
    AuditBase.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def _override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[auth_db_dep] = _override_db
    app.dependency_overrides[subcontract_db_dep] = _override_db
    old_main_session_local = main_module.SessionLocal
    main_module.SessionLocal = SessionLocal

    old_app_env = os.environ.get("APP_ENV")
    old_dev_auth = os.environ.get("LINGYI_ALLOW_DEV_AUTH")
    old_perm_source = os.environ.get("LINGYI_PERMISSION_SOURCE")
    os.environ["APP_ENV"] = "test"
    os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
    os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

    try:
        yield engine, SessionLocal
    finally:
        if old_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = old_app_env

        if old_dev_auth is None:
            os.environ.pop("LINGYI_ALLOW_DEV_AUTH", None)
        else:
            os.environ["LINGYI_ALLOW_DEV_AUTH"] = old_dev_auth

        if old_perm_source is None:
            os.environ.pop("LINGYI_PERMISSION_SOURCE", None)
        else:
            os.environ["LINGYI_PERMISSION_SOURCE"] = old_perm_source

        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        main_module.SessionLocal = old_main_session_local
        engine.dispose()



def _headers() -> dict[str, str]:
    return {"X-LY-Dev-User": "pg.settlement.user", "X-LY-Dev-Roles": "Subcontract Manager"}



def _seed_settlement_rows(session_factory: Callable[[], object]) -> None:
    with session_factory() as session:
        session.add(
            LyApparelBom(
                id=1,
                bom_no="BOM-PG-001",
                item_code="ITEM-A",
                version_no="v1",
                is_default=True,
                status="active",
                created_by="seed",
                updated_by="seed",
            )
        )
        session.add(
            LySubcontractOrder(
                id=10,
                subcontract_no="SC-PG-001",
                supplier="SUP-A",
                item_code="ITEM-A",
                company="COMP-A",
                bom_id=1,
                process_name="外发裁剪",
                planned_qty=Decimal("100"),
                status="waiting_receive",
                resource_scope_status="ready",
            )
        )
        session.add(
            LySubcontractReceipt(
                id=1000,
                subcontract_id=10,
                company="COMP-A",
                receipt_batch_no="RB-PG-001",
                receipt_warehouse="WH-A",
                item_code="ITEM-A",
                received_qty=Decimal("100"),
                inspected_qty=Decimal("0"),
                rejected_qty=Decimal("0"),
                rejected_rate=Decimal("0"),
                deduction_amount=Decimal("0"),
                net_amount=Decimal("0"),
                inspect_status="pending",
                sync_status="succeeded",
                stock_entry_name="STE-REAL-PG-001",
                idempotency_key="idem-receipt-pg-001",
            )
        )
        # PostgreSQL enforces FK strictly; make sure parent rows are visible
        # before inserting inspections that reference subcontract_id=10.
        session.flush()
        session.add_all(
            [
                LySubcontractInspection(
                    id=100,
                    subcontract_id=10,
                    company="COMP-A",
                    inspection_no="SIN-PG-100",
                    receipt_batch_no="RB-PG-001",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("20"),
                    accepted_qty=Decimal("19"),
                    rejected_qty=Decimal("1"),
                    rejected_rate=Decimal("0.05"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("200"),
                    deduction_amount_per_piece=Decimal("5"),
                    deduction_amount=Decimal("5"),
                    net_amount=Decimal("195"),
                    settlement_status="unsettled",
                    settlement_line_key="subcontract_inspection:100",
                    status="inspected",
                    inspected_by="u1",
                ),
                LySubcontractInspection(
                    id=101,
                    subcontract_id=10,
                    company="COMP-A",
                    inspection_no="SIN-PG-101",
                    receipt_batch_no="RB-PG-001",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("10"),
                    accepted_qty=Decimal("10"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("100"),
                    deduction_amount_per_piece=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("100"),
                    settlement_status="unsettled",
                    settlement_line_key="subcontract_inspection:101",
                    status="inspected",
                    inspected_by="u2",
                ),
            ]
        )
        session.commit()



def _run_concurrent_posts(path: str, payload: dict, headers: dict[str, str], count: int = 2):
    barrier = threading.Barrier(count)
    responses: list[object] = []
    errors: list[Exception] = []

    def _worker() -> None:
        try:
            with TestClient(app) as client:
                barrier.wait(timeout=5)
                responses.append(client.post(path, headers=headers, json=payload))
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    threads = [threading.Thread(target=_worker, daemon=True) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors
    assert len(responses) == count
    return responses


@pytest.mark.postgresql
def test_postgresql_settlement_same_key_concurrent_lock_replays(pg_app_env) -> None:
    _engine, session_factory = pg_app_env
    _seed_settlement_rows(session_factory)

    payload = {
        "statement_id": 9001,
        "statement_no": "ST-PG-9001",
        "inspection_ids": [100],
        "idempotency_key": "idem-lock-pg-concurrent",
        "remark": "lock",
    }
    responses = _run_concurrent_posts("/api/subcontract/settlement-locks", payload, _headers(), count=2)

    flags: list[bool] = []
    for resp in responses:
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "0"
        flags.append(bool(body["data"]["idempotent_replay"]))

    assert sorted(flags) == [False, True]

    with session_factory() as session:
        op_count = (
            session.query(LySubcontractSettlementOperation)
            .filter(
                LySubcontractSettlementOperation.operation_type == "lock",
                LySubcontractSettlementOperation.idempotency_key == "idem-lock-pg-concurrent",
            )
            .count()
        )
        assert op_count == 1

        inspection = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
        assert str(inspection.settlement_status) == "statement_locked"
        assert int(inspection.statement_id) == 9001
        assert str(inspection.statement_no) == "ST-PG-9001"


@pytest.mark.postgresql
def test_postgresql_settlement_same_key_concurrent_release_replays(pg_app_env) -> None:
    _engine, session_factory = pg_app_env
    _seed_settlement_rows(session_factory)

    lock_payload = {
        "statement_id": 9002,
        "statement_no": "ST-PG-9002",
        "inspection_ids": [100],
        "idempotency_key": "idem-lock-pg-release",
        "remark": "lock",
    }
    with TestClient(app) as client:
        first_lock = client.post("/api/subcontract/settlement-locks", headers=_headers(), json=lock_payload)
    assert first_lock.status_code == 200

    release_payload = {
        "statement_id": 9002,
        "statement_no": "ST-PG-9002",
        "inspection_ids": [100],
        "idempotency_key": "idem-release-pg-concurrent",
        "reason": "reopen",
    }
    responses = _run_concurrent_posts("/api/subcontract/settlement-locks/release", release_payload, _headers(), count=2)

    flags: list[bool] = []
    for resp in responses:
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == "0"
        flags.append(bool(body["data"]["idempotent_replay"]))

    assert sorted(flags) == [False, True]

    with session_factory() as session:
        op_count = (
            session.query(LySubcontractSettlementOperation)
            .filter(
                LySubcontractSettlementOperation.operation_type == "release",
                LySubcontractSettlementOperation.idempotency_key == "idem-release-pg-concurrent",
            )
            .count()
        )
        assert op_count == 1

        inspection = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
        assert str(inspection.settlement_status) == "unsettled"
        assert inspection.statement_id is None
        assert inspection.statement_no is None


@pytest.mark.postgresql
def test_postgresql_settlement_same_key_different_payload_conflicts(pg_app_env) -> None:
    _engine, session_factory = pg_app_env
    _seed_settlement_rows(session_factory)

    with TestClient(app) as client:
        first = client.post(
            "/api/subcontract/settlement-locks",
            headers=_headers(),
            json={
                "statement_id": 9003,
                "statement_no": "ST-PG-9003",
                "inspection_ids": [100],
                "idempotency_key": "idem-lock-pg-conflict",
                "remark": "first",
            },
        )
        second = client.post(
            "/api/subcontract/settlement-locks",
            headers=_headers(),
            json={
                "statement_id": 9003,
                "statement_no": "ST-PG-9003",
                "inspection_ids": [101],
                "idempotency_key": "idem-lock-pg-conflict",
                "remark": "second",
            },
        )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["code"] == "SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT"

    with session_factory() as session:
        op_count = (
            session.query(LySubcontractSettlementOperation)
            .filter(
                LySubcontractSettlementOperation.operation_type == "lock",
                LySubcontractSettlementOperation.idempotency_key == "idem-lock-pg-conflict",
            )
            .count()
        )
        assert op_count == 1

        row_100 = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 100).one()
        row_101 = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 101).one()
        assert str(row_100.settlement_status) == "statement_locked"
        assert str(row_101.settlement_status) == "unsettled"


@pytest.mark.postgresql
def test_postgresql_settlement_operation_unique_constraint_exists(postgres_dsn: str) -> None:
    engine = _create_pg_engine_or_skip(postgres_dsn)
    try:
        _reset_test_schema(engine=engine, dsn=postgres_dsn)

        _run_settlement_chain(engine)

        inspector = inspect(engine)
        tables = set(inspector.get_table_names(schema=SCHEMA))
        assert "ly_subcontract_settlement_operation" in tables

        unique_constraints = inspector.get_unique_constraints(
            "ly_subcontract_settlement_operation",
            schema=SCHEMA,
        )
        found = False
        for uc in unique_constraints:
            cols = set(uc.get("column_names") or [])
            if cols == {"operation_type", "idempotency_key"}:
                found = True
                break
        assert found, "missing unique(operation_type, idempotency_key) on settlement operation table"
    finally:
        engine.dispose()


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


class _FakeConn:
    def __init__(self, *, database_name: str, statements: list[str]):
        self.database_name = database_name
        self.statements = statements

    def execute(self, statement):
        sql = str(statement)
        if "current_database()" in sql.lower():
            return _FakeScalarResult(self.database_name)
        self.statements.append(sql)
        return _FakeScalarResult(None)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeEngine:
    def __init__(self, database_name: str):
        self.database_name = database_name
        self.statements: list[str] = []

    def connect(self):
        return _FakeConn(database_name=self.database_name, statements=self.statements)

    def begin(self):
        return _FakeConn(database_name=self.database_name, statements=self.statements)


def test_postgresql_destructive_gate_requires_allow_env(monkeypatch) -> None:
    monkeypatch.delenv(DESTRUCTIVE_FLAG_ENV, raising=False)
    fake_engine = _FakeEngine("lingyi_test_ci")
    with pytest.raises(PostgresDestructiveGateError) as exc_info:
        _ensure_destructive_pg_test_gate(engine=fake_engine, dsn="postgresql+psycopg://u:p@127.0.0.1/lingyi_test_ci")

    message = str(exc_info.value)
    assert DESTRUCTIVE_FLAG_ENV in message
    assert "blocked" in message


def test_postgresql_destructive_gate_rejects_non_test_database_name(monkeypatch) -> None:
    monkeypatch.setenv(DESTRUCTIVE_FLAG_ENV, "true")
    fake_engine = _FakeEngine("lingyi_prod")
    with pytest.raises(PostgresDestructiveGateError) as exc_info:
        _ensure_destructive_pg_test_gate(engine=fake_engine, dsn="postgresql+psycopg://u:p@127.0.0.1/lingyi_prod")

    message = str(exc_info.value)
    assert "not in test allowlist" in message
    assert "lingyi_prod" in message


def test_postgresql_destructive_gate_accepts_test_database_name(monkeypatch) -> None:
    monkeypatch.setenv(DESTRUCTIVE_FLAG_ENV, "true")
    fake_engine = _FakeEngine("lingyi_test_ci")
    database_name = _ensure_destructive_pg_test_gate(
        engine=fake_engine,
        dsn="postgresql+psycopg://u:p@127.0.0.1/lingyi_test_ci",
    )
    assert database_name == "lingyi_test_ci"


def test_postgresql_destructive_gate_message_redacts_dsn(monkeypatch) -> None:
    monkeypatch.delenv(DESTRUCTIVE_FLAG_ENV, raising=False)
    dsn = "postgresql+psycopg://user_name:super_secret@127.0.0.1:5432/lingyi_test_ci"
    fake_engine = _FakeEngine("lingyi_test_ci")
    with pytest.raises(PostgresDestructiveGateError) as exc_info:
        _ensure_destructive_pg_test_gate(engine=fake_engine, dsn=dsn)

    message = str(exc_info.value)
    assert "super_secret" not in message
    assert "user_name" not in message
    assert "postgresql+psycopg://***@127.0.0.1:5432/lingyi_test_ci" in message


def test_postgresql_drop_schema_only_after_gate_passes(monkeypatch) -> None:
    dsn = "postgresql+psycopg://user:pass@127.0.0.1:5432/lingyi_test_ci"

    blocked_engine = _FakeEngine("lingyi_test_ci")
    monkeypatch.delenv(DESTRUCTIVE_FLAG_ENV, raising=False)
    with pytest.raises(PostgresDestructiveGateError):
        _reset_test_schema(engine=blocked_engine, dsn=dsn)
    assert not any("DROP SCHEMA IF EXISTS ly_schema CASCADE" in sql for sql in blocked_engine.statements)

    allowed_engine = _FakeEngine("lingyi_test_ci")
    monkeypatch.setenv(DESTRUCTIVE_FLAG_ENV, "true")
    _reset_test_schema(engine=allowed_engine, dsn=dsn)
    assert any("DROP SCHEMA IF EXISTS ly_schema CASCADE" in sql for sql in allowed_engine.statements)
    assert any("CREATE SCHEMA IF NOT EXISTS ly_schema" in sql for sql in allowed_engine.statements)
