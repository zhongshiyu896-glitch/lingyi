"""PostgreSQL integration tests for style-profit subcontract source pushdown (TASK-005F4)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import os
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.schemas.style_profit import StyleProfitSnapshotSelectorRequest
from app.services.erpnext_style_profit_adapter import ERPNextStyleProfitAdapter


SCHEMA = "ly_schema"
DESTRUCTIVE_FLAG_ENV = "POSTGRES_TEST_ALLOW_DESTRUCTIVE"
_TEST_DB_PATTERNS = (
    re.compile(r".*_test$", re.IGNORECASE),
    re.compile(r"lingyi_test_.*", re.IGNORECASE),
)


def _redact_dsn(dsn: str) -> str:
    try:
        parsed = make_url(dsn)
        host = parsed.host or "unknown-host"
        port = f":{parsed.port}" if parsed.port else ""
        database = parsed.database or "unknown-db"
        return f"{parsed.drivername}://***@{host}{port}/{database}"
    except Exception:
        return "invalid-dsn"


def _dsn_or_skip() -> str:
    dsn = str(os.getenv("POSTGRES_TEST_DSN", "") or "").strip()
    if not dsn or dsn.startswith("${") or dsn.startswith("$("):
        pytest.skip("POSTGRES_TEST_DSN is not set; skipping style-profit subcontract PostgreSQL tests")
    return dsn


def _ensure_destructive_gate(*, engine, dsn: str) -> None:
    if str(os.getenv(DESTRUCTIVE_FLAG_ENV, "") or "").strip().lower() != "true":
        pytest.skip(f"{DESTRUCTIVE_FLAG_ENV} is not true; skipping destructive PostgreSQL tests")

    parsed = make_url(dsn)
    db_name = str(parsed.database or "").strip()
    if not db_name or not any(pattern.fullmatch(db_name) for pattern in _TEST_DB_PATTERNS):
        redacted = _redact_dsn(dsn)
        pytest.skip(f"POSTGRES_TEST_DSN database is not allowed for destructive tests: {redacted}")

    with engine.connect() as conn:
        current_db = str(conn.execute(text("SELECT current_database()")).scalar_one() or "").strip()
    if current_db != db_name:
        pytest.skip("current_database mismatch; skipping destructive PostgreSQL tests")


@pytest.fixture(scope="module")
def pg_env():
    dsn = _dsn_or_skip()
    engine = create_engine(dsn, future=True, pool_pre_ping=True)
    _ensure_destructive_gate(engine=engine, dsn=dsn)

    with engine.begin() as conn:
        conn.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))

    BomBase.metadata.create_all(bind=engine)
    if "ly_schema.ly_apparel_bom" not in SubcontractBase.metadata.tables:
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
    SubcontractBase.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    try:
        yield SessionLocal, engine
    finally:
        engine.dispose()


def _selector(*, work_order: str | None = "WO-001") -> StyleProfitSnapshotSelectorRequest:
    return StyleProfitSnapshotSelectorRequest(
        company="COMP-A",
        item_code="STYLE-A",
        sales_order="SO-001",
        from_date=date(2026, 4, 1),
        to_date=date(2026, 4, 30),
        revenue_mode="actual_first",
        include_provisional_subcontract=False,
        formula_version="STYLE_PROFIT_V1",
        idempotency_key="idem-subcontract-pg",
        work_order=work_order,
    )


def _reset_seed_base(session_factory) -> None:
    with session_factory() as session:
        session.query(LySubcontractInspection).delete()
        session.query(LySubcontractOrder).delete()
        session.query(LyApparelBom).delete()
        session.add(
            LyApparelBom(
                id=1,
                bom_no="BOM-PG-STYLE-001",
                item_code="STYLE-A",
                version_no="V1",
                is_default=True,
                status="active",
                created_by="tester",
                updated_by="tester",
            )
        )
        session.commit()


@pytest.mark.postgresql
def test_postgresql_subcontract_profit_filters_by_inspected_at(pg_env) -> None:
    session_factory, _engine = pg_env
    _reset_seed_base(session_factory)
    with session_factory() as session:
        order = LySubcontractOrder(
            id=1,
            subcontract_no="SUB-PG-001",
            supplier="SUP-A",
            item_code="STYLE-A",
            company="COMP-A",
            bom_id=1,
            process_name="OUT",
            planned_qty=Decimal("10"),
            subcontract_rate=Decimal("2"),
            status="submitted",
            settlement_status="unsettled",
            sales_order="SO-001",
            work_order="WO-001",
            profit_scope_status="ready",
        )
        session.add(order)
        session.flush()
        session.add_all(
            [
                LySubcontractInspection(
                    subcontract_id=1,
                    company="COMP-A",
                    inspection_no="INSP-IN",
                    item_code="STYLE-A",
                    sales_order="SO-001",
                    work_order="WO-001",
                    inspected_at=datetime(2026, 4, 12, 9, 0, 0),
                    created_at=datetime(2026, 3, 1, 9, 0, 0),
                    net_amount=Decimal("8"),
                    settlement_status="unsettled",
                    status="submitted",
                    profit_scope_status="ready",
                ),
                LySubcontractInspection(
                    subcontract_id=1,
                    company="COMP-A",
                    inspection_no="INSP-OUT",
                    item_code="STYLE-A",
                    sales_order="SO-001",
                    work_order="WO-001",
                    inspected_at=datetime(2026, 3, 31, 9, 0, 0),
                    created_at=datetime(2026, 4, 10, 9, 0, 0),
                    net_amount=Decimal("8"),
                    settlement_status="unsettled",
                    status="submitted",
                    profit_scope_status="ready",
                ),
                LySubcontractInspection(
                    subcontract_id=1,
                    company="COMP-A",
                    inspection_no="INSP-NO-TIME",
                    item_code="STYLE-A",
                    sales_order="SO-001",
                    work_order="WO-001",
                    inspected_at=None,
                    created_at=datetime(2026, 4, 15, 9, 0, 0),
                    net_amount=Decimal("8"),
                    settlement_status="unsettled",
                    status="submitted",
                    profit_scope_status="ready",
                ),
            ]
        )
        session.commit()

        rows = ERPNextStyleProfitAdapter(session=session).load_subcontract_rows(_selector())

    names = {str(row.get("inspection_no") or row.get("name") or "") for row in rows}
    assert "INSP-IN" in names
    assert "INSP-OUT" not in names
    unresolved_missing_time = [row for row in rows if row.get("inspection_no") == "INSP-NO-TIME"]
    assert len(unresolved_missing_time) == 1
    assert unresolved_missing_time[0]["profit_scope_error_code"] == "SUBCONTRACT_INSPECTED_AT_REQUIRED"


@pytest.mark.postgresql
def test_postgresql_subcontract_profit_filters_work_order_in_database(pg_env) -> None:
    session_factory, _engine = pg_env
    _reset_seed_base(session_factory)
    with session_factory() as session:
        order = LySubcontractOrder(
            id=1,
            subcontract_no="SUB-PG-002",
            supplier="SUP-A",
            item_code="STYLE-A",
            company="COMP-A",
            bom_id=1,
            process_name="OUT",
            planned_qty=Decimal("10"),
            subcontract_rate=Decimal("2"),
            status="submitted",
            settlement_status="unsettled",
            sales_order="SO-001",
            profit_scope_status="ready",
        )
        session.add(order)
        session.flush()
        session.add_all(
            [
                LySubcontractInspection(
                    subcontract_id=1,
                    company="COMP-A",
                    inspection_no="INSP-WO-1",
                    item_code="STYLE-A",
                    sales_order="SO-001",
                    work_order="WO-001",
                    inspected_at=datetime(2026, 4, 10, 9, 0, 0),
                    net_amount=Decimal("8"),
                    settlement_status="unsettled",
                    status="submitted",
                    profit_scope_status="ready",
                ),
                LySubcontractInspection(
                    subcontract_id=1,
                    company="COMP-A",
                    inspection_no="INSP-WO-2",
                    item_code="STYLE-A",
                    sales_order="SO-001",
                    work_order="WO-002",
                    inspected_at=datetime(2026, 4, 10, 10, 0, 0),
                    net_amount=Decimal("8"),
                    settlement_status="unsettled",
                    status="submitted",
                    profit_scope_status="ready",
                ),
            ]
        )
        session.commit()

        rows = ERPNextStyleProfitAdapter(session=session).load_subcontract_rows(_selector(work_order="WO-001"))

    assert [row["inspection_no"] for row in rows] == ["INSP-WO-1"]
    assert rows[0]["work_order"] == "WO-001"


@pytest.mark.postgresql
def test_postgresql_subcontract_profit_uses_indexed_period_query(pg_env) -> None:
    session_factory, engine = pg_env
    _reset_seed_base(session_factory)
    with session_factory() as session:
        order = LySubcontractOrder(
            id=1,
            subcontract_no="SUB-PG-003",
            supplier="SUP-A",
            item_code="STYLE-A",
            company="COMP-A",
            bom_id=1,
            process_name="OUT",
            planned_qty=Decimal("10"),
            subcontract_rate=Decimal("2"),
            status="submitted",
            settlement_status="unsettled",
            sales_order="SO-001",
            work_order="WO-001",
            profit_scope_status="ready",
        )
        session.add(order)
        session.flush()
        session.add(
            LySubcontractInspection(
                subcontract_id=1,
                company="COMP-A",
                inspection_no="INSP-SQL",
                item_code="STYLE-A",
                sales_order="SO-001",
                work_order="WO-001",
                inspected_at=datetime(2026, 4, 18, 8, 0, 0),
                net_amount=Decimal("8"),
                settlement_status="unsettled",
                status="submitted",
                profit_scope_status="ready",
            )
        )
        session.commit()

        captured_sql: list[str] = []

        @event.listens_for(engine, "before_cursor_execute")
        def _capture(_conn, _cursor, statement, _parameters, _context, _executemany):
            captured_sql.append(str(statement))

        try:
            _ = ERPNextStyleProfitAdapter(session=session).load_subcontract_rows(_selector(work_order="WO-001"))
        finally:
            event.remove(engine, "before_cursor_execute", _capture)

    lower_sql = "\n".join(captured_sql).lower()
    assert "ly_subcontract_inspection" in lower_sql
    assert "inspected_at" in lower_sql
    assert "company" in lower_sql
    assert "item_code" in lower_sql
    assert "sales_order" in lower_sql
    assert "work_order" in lower_sql


@pytest.mark.postgresql
def test_postgresql_subcontract_profit_missing_inspected_at_is_limited_diagnostic(pg_env, monkeypatch) -> None:
    session_factory, engine = pg_env
    _reset_seed_base(session_factory)
    with session_factory() as session:
        order = LySubcontractOrder(
            id=1,
            subcontract_no="SUB-PG-004",
            supplier="SUP-A",
            item_code="STYLE-A",
            company="COMP-A",
            bom_id=1,
            process_name="OUT",
            planned_qty=Decimal("10"),
            subcontract_rate=Decimal("2"),
            status="submitted",
            settlement_status="unsettled",
            sales_order="SO-001",
            work_order="WO-001",
            profit_scope_status="ready",
        )
        session.add(order)
        session.flush()
        session.add_all(
            [
                LySubcontractInspection(
                    subcontract_id=1,
                    company="COMP-A",
                    inspection_no=f"INSP-MISS-{idx}",
                    item_code="STYLE-A",
                    sales_order="SO-001",
                    work_order="WO-001",
                    inspected_at=None,
                    net_amount=Decimal("1"),
                    settlement_status="unsettled",
                    status="submitted",
                    profit_scope_status="ready",
                )
                for idx in range(1, 251)
            ]
        )
        session.commit()

        monkeypatch.setenv("STYLE_PROFIT_SUBCONTRACT_DIAGNOSTIC_LIMIT", "10")
        captured_sql: list[str] = []

        @event.listens_for(engine, "before_cursor_execute")
        def _capture(_conn, _cursor, statement, _parameters, _context, _executemany):
            captured_sql.append(str(statement))

        try:
            rows = ERPNextStyleProfitAdapter(session=session).load_subcontract_rows(_selector(work_order="WO-001"))
        finally:
            event.remove(engine, "before_cursor_execute", _capture)

    assert len(rows) == 11
    aggregate_rows = [row for row in rows if row.get("bridge_source") == "diagnostic_aggregate"]
    assert len(aggregate_rows) == 1
    aggregate = aggregate_rows[0]
    assert aggregate["profit_scope_error_code"] == "SUBCONTRACT_INSPECTED_AT_REQUIRED"
    assert aggregate["diagnostic_total_missing_inspected_at"] == "250"
    assert aggregate["diagnostic_truncated_count"] == "240"

    lower_sql = "\n".join(captured_sql).lower()
    assert "limit" in lower_sql
