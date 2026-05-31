"""Local development ASGI entrypoint.

This module keeps the production app unchanged while making the local Vue
frontend usable without ERPNext login cookies. It enables dev-header auth,
uses a SQLite database with schema translation, creates the tables needed by
the local screens, and seeds a tiny BOM fixture if the database is empty.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any
import os
import sqlite3

from fastapi import Body
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("LINGYI_ALLOW_DEV_AUTH", "true")
os.environ.setdefault("LINGYI_ERPNEXT_BASE_URL", "")
os.environ.setdefault("LINGYI_PERMISSION_SOURCE", "static")
os.environ.setdefault("LINGYI_DB_URL", "sqlite:///./lingyi_service.local.db")

from app import main as main_module  # noqa: E402
from app.models.audit import Base as AuditBase  # noqa: E402
from app.models.bom import Base as BomBase  # noqa: E402
from app.models.bom import LyApparelBom  # noqa: E402
from app.models.bom import LyApparelBomItem  # noqa: E402
from app.models.bom import LyBomOperation  # noqa: E402
from app.models.factory_statement import Base as FactoryStatementBase  # noqa: E402
from app.models.production import Base as ProductionBase  # noqa: E402
from app.models.quality import Base as QualityBase  # noqa: E402
import app.models.quality_outbox  # noqa: E402,F401
from app.models.style_profit import Base as StyleProfitBase  # noqa: E402
from app.models.subcontract import Base as SubcontractBase  # noqa: E402
import app.models.warehouse  # noqa: E402,F401
from app.models.workshop import Base as WorkshopBase  # noqa: E402


def _local_engine():
    return create_engine(
        os.environ["LINGYI_DB_URL"],
        future=True,
        execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
    )


main_module.engine = _local_engine()
main_module.SessionLocal = sessionmaker(
    bind=main_module.engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def _create_local_tables() -> None:
    BomBase.metadata.create_all(bind=main_module.engine)
    AuditBase.metadata.create_all(bind=main_module.engine)
    ProductionBase.metadata.create_all(bind=main_module.engine)
    FactoryStatementBase.metadata.create_all(bind=main_module.engine)
    QualityBase.metadata.create_all(bind=main_module.engine)
    StyleProfitBase.metadata.create_all(bind=main_module.engine)
    WorkshopBase.metadata.create_all(bind=main_module.engine)

    # Subcontract models reference BOM metadata from a separate declarative Base.
    # Copying the table definition into this metadata is enough for SQLite local DDL.
    if "ly_schema.ly_apparel_bom" not in SubcontractBase.metadata.tables:
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
    SubcontractBase.metadata.create_all(bind=main_module.engine)


def _seed_local_bom() -> None:
    with main_module.SessionLocal() as session:
        existing = session.query(LyApparelBom.id).first()
        if existing:
            return

        bom = LyApparelBom(
            id=1,
            bom_no="BOM-DEMO-TEE-V1",
            item_code="DEMO-TEE",
            version_no="V1",
            is_default=True,
            status="active",
            effective_date=date.today(),
            created_by="local.dev",
            updated_by="local.dev",
        )
        bom.items = [
            LyApparelBomItem(
                id=1,
                bom_id=1,
                material_item_code="FABRIC-COTTON",
                color="白色",
                size="M",
                qty_per_piece=1.2,
                loss_rate=0.03,
                uom="米",
                remark="本地开发演示物料",
            ),
            LyApparelBomItem(
                id=2,
                bom_id=1,
                material_item_code="TRIM-BUTTON",
                color="白色",
                size=None,
                qty_per_piece=5,
                loss_rate=0,
                uom="粒",
                remark="本地开发演示辅料",
            ),
        ]
        bom.operations = [
            LyBomOperation(
                id=1,
                bom_id=1,
                process_name="裁剪",
                sequence_no=10,
                is_subcontract=False,
                wage_rate=2.5,
                subcontract_cost_per_piece=None,
                remark="本地开发演示工序",
            ),
            LyBomOperation(
                id=2,
                bom_id=1,
                process_name="缝制",
                sequence_no=20,
                is_subcontract=False,
                wage_rate=6,
                subcontract_cost_per_piece=None,
                remark="本地开发演示工序",
            ),
        ]
        session.add(bom)
        session.commit()


_create_local_tables()
_seed_local_bom()

app = main_module.app


def _local_db_file_path() -> Path:
    db_path = main_module.engine.url.database
    if not db_path:
        raise RuntimeError("LINGYI_DB_URL database path is missing")
    raw = Path(db_path)
    if raw.is_absolute():
        return raw
    return (Path.cwd() / raw).resolve()


def _connect_local_sqlite() -> sqlite3.Connection:
    connection = sqlite3.connect(_local_db_file_path())
    connection.row_factory = sqlite3.Row
    return connection


def _create_basic_reference_draft_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ly_local_basic_reference_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            category TEXT NOT NULL,
            reference_code TEXT NOT NULL,
            reference_name TEXT NOT NULL,
            status TEXT NOT NULL,
            key_field TEXT NOT NULL,
            linkage_warehouse TEXT NOT NULL DEFAULT '',
            linkage_material TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'saved',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            cancelled_at TEXT,
            cancel_reason TEXT
        )
        """
    )
    connection.commit()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ok(data: Any, message: str = "ok") -> dict[str, Any]:
    return {"code": "0", "message": message, "data": data}


def _draft_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "draft_id": int(row["id"]),
        "scenario_tag": row["scenario_tag"],
        "category": row["category"],
        "reference_code": row["reference_code"],
        "reference_name": row["reference_name"],
        "status": row["status"],
        "key_field": row["key_field"],
        "linkage_warehouse": row["linkage_warehouse"],
        "linkage_material": row["linkage_material"],
        "note": row["note"],
        "state": row["state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cancelled_at": row["cancelled_at"],
        "cancel_reason": row["cancel_reason"],
    }


def _get_draft_row(connection: sqlite3.Connection, draft_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM ly_local_basic_reference_drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()


@app.post("/api/local-dev/basic-reference-drafts")
def upsert_local_basic_reference_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    category = str(payload.get("category", "")).strip()
    reference_code = str(payload.get("reference_code", "")).strip()
    reference_name = str(payload.get("reference_name", "")).strip()
    status = str(payload.get("status", "")).strip() or "draft"
    key_field = str(payload.get("key_field", "")).strip() or "-"
    linkage_warehouse = str(payload.get("linkage_warehouse", "")).strip()
    linkage_material = str(payload.get("linkage_material", "")).strip()
    note = str(payload.get("note", "")).strip()
    draft_id = payload.get("draft_id")

    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    if category not in {"customer", "warehouse", "supplier", "factory", "material"}:
        raise HTTPException(status_code=400, detail="category is invalid")
    if not reference_code or not reference_name:
        raise HTTPException(status_code=400, detail="reference_code and reference_name are required")

    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_basic_reference_draft_table(connection)
        if isinstance(draft_id, int) and draft_id > 0:
            exists = _get_draft_row(connection, draft_id)
            if not exists:
                raise HTTPException(status_code=404, detail="draft not found")
            connection.execute(
                """
                UPDATE ly_local_basic_reference_drafts
                SET scenario_tag = ?,
                    category = ?,
                    reference_code = ?,
                    reference_name = ?,
                    status = ?,
                    key_field = ?,
                    linkage_warehouse = ?,
                    linkage_material = ?,
                    note = ?,
                    state = 'saved',
                    updated_at = ?,
                    cancelled_at = NULL,
                    cancel_reason = NULL
                WHERE id = ?
                """,
                (
                    scenario_tag,
                    category,
                    reference_code,
                    reference_name,
                    status,
                    key_field,
                    linkage_warehouse,
                    linkage_material,
                    note,
                    now_iso,
                    draft_id,
                ),
            )
            connection.commit()
            row = _get_draft_row(connection, draft_id)
        else:
            cursor = connection.execute(
                """
                INSERT INTO ly_local_basic_reference_drafts (
                    scenario_tag,
                    category,
                    reference_code,
                    reference_name,
                    status,
                    key_field,
                    linkage_warehouse,
                    linkage_material,
                    note,
                    state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
                """,
                (
                    scenario_tag,
                    category,
                    reference_code,
                    reference_name,
                    status,
                    key_field,
                    linkage_warehouse,
                    linkage_material,
                    note,
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()
            row = _get_draft_row(connection, int(cursor.lastrowid))

    if row is None:
        raise HTTPException(status_code=500, detail="draft persistence failed")
    return _ok(_draft_row_to_dict(row))


@app.get("/api/local-dev/basic-reference-drafts/residual-count")
def get_local_basic_reference_residual_count(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_basic_reference_draft_table(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_basic_reference_drafts WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.post("/api/local-dev/basic-reference-drafts/rollback-by-scenario")
def rollback_local_basic_reference_drafts(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    with _connect_local_sqlite() as connection:
        _create_basic_reference_draft_table(connection)
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_basic_reference_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
        deleted_count = int(before["total"]) if before else 0
        connection.execute(
            "DELETE FROM ly_local_basic_reference_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        )
        connection.commit()
        after = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_basic_reference_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
    residual = int(after["total"]) if after else 0
    data = {
        "scenario_tag": scenario_tag,
        "deleted_count": deleted_count,
        "residual_records_after_rollback": residual,
        "rollback_success": residual == 0,
        "zero_residual_success": residual == 0,
    }
    return _ok(data)


@app.get("/api/local-dev/basic-reference-drafts/{draft_id}")
def get_local_basic_reference_draft(draft_id: int) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_basic_reference_draft_table(connection)
        row = _get_draft_row(connection, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return _ok(_draft_row_to_dict(row))


@app.post("/api/local-dev/basic-reference-drafts/{draft_id}/cancel")
def cancel_local_basic_reference_draft(draft_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    reason = str(payload.get("reason", "")).strip() or f"CANCEL-{scenario_tag or draft_id}"
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_basic_reference_draft_table(connection)
        row = _get_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        if row["scenario_tag"] != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")
        connection.execute(
            """
            UPDATE ly_local_basic_reference_drafts
            SET state = 'cancelled',
                updated_at = ?,
                cancelled_at = ?,
                cancel_reason = ?
            WHERE id = ?
            """,
            (now_iso, now_iso, reason, draft_id),
        )
        connection.commit()
        cancelled = _get_draft_row(connection, draft_id)
    if cancelled is None:
        raise HTTPException(status_code=500, detail="draft cancel failed")
    return _ok(_draft_row_to_dict(cancelled))
