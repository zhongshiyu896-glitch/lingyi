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
import json
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


def _create_bom_draft_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ly_local_bom_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            bom_no TEXT NOT NULL,
            item_code TEXT NOT NULL,
            version_no TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            is_default INTEGER NOT NULL DEFAULT 0,
            bom_items_json TEXT NOT NULL,
            operations_json TEXT NOT NULL,
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


def _get_bom_draft_row(connection: sqlite3.Connection, draft_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM ly_local_bom_drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()


def _parse_json_payload(value: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _is_fabric_line(item: dict[str, Any]) -> bool:
    token = f"{item.get('material_item_code', '')} {item.get('remark', '')}".upper()
    return "FABRIC" in token or "FAB" in token or "面料" in token


def _is_trim_line(item: dict[str, Any]) -> bool:
    token = f"{item.get('material_item_code', '')} {item.get('remark', '')}".upper()
    return "TRIM" in token or "BUTTON" in token or "辅料" in token or "包材" in token


def _bom_draft_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    bom_items = _parse_json_payload(row["bom_items_json"])
    operations = _parse_json_payload(row["operations_json"])
    return {
        "draft_id": int(row["id"]),
        "scenario_tag": row["scenario_tag"],
        "bom_no": row["bom_no"],
        "item_code": row["item_code"],
        "version_no": row["version_no"],
        "status": row["status"],
        "is_default": bool(row["is_default"]),
        "bom_items": bom_items,
        "operations": operations,
        "note": row["note"],
        "state": row["state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cancelled_at": row["cancelled_at"],
        "cancel_reason": row["cancel_reason"],
        "fabric_line_saved": any(_is_fabric_line(item) for item in bom_items),
        "trim_line_saved": any(_is_trim_line(item) for item in bom_items),
    }


@app.post("/api/local-dev/bom-drafts")
def upsert_local_bom_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    bom_no = str(payload.get("bom_no", "")).strip()
    item_code = str(payload.get("item_code", "")).strip()
    version_no = str(payload.get("version_no", "")).strip() or "V1"
    status = str(payload.get("status", "")).strip() or "draft"
    note = str(payload.get("note", "")).strip()
    draft_id = payload.get("draft_id")
    is_default = bool(payload.get("is_default", False))
    bom_items = payload.get("bom_items", [])
    operations = payload.get("operations", [])

    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    if not bom_no:
        raise HTTPException(status_code=400, detail="bom_no is required")
    if not item_code:
        raise HTTPException(status_code=400, detail="item_code is required")
    if not isinstance(bom_items, list) or len(bom_items) == 0:
        raise HTTPException(status_code=400, detail="bom_items is required")
    if not isinstance(operations, list) or len(operations) == 0:
        raise HTTPException(status_code=400, detail="operations is required")

    bom_items_json = json.dumps(bom_items, ensure_ascii=False)
    operations_json = json.dumps(operations, ensure_ascii=False)
    now_iso = _now_iso()

    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        if isinstance(draft_id, int) and draft_id > 0:
            exists = _get_bom_draft_row(connection, draft_id)
            if not exists:
                raise HTTPException(status_code=404, detail="draft not found")
            connection.execute(
                """
                UPDATE ly_local_bom_drafts
                SET scenario_tag = ?,
                    bom_no = ?,
                    item_code = ?,
                    version_no = ?,
                    status = ?,
                    is_default = ?,
                    bom_items_json = ?,
                    operations_json = ?,
                    note = ?,
                    state = 'saved',
                    updated_at = ?,
                    cancelled_at = NULL,
                    cancel_reason = NULL
                WHERE id = ?
                """,
                (
                    scenario_tag,
                    bom_no,
                    item_code,
                    version_no,
                    status,
                    1 if is_default else 0,
                    bom_items_json,
                    operations_json,
                    note,
                    now_iso,
                    draft_id,
                ),
            )
            connection.commit()
            row = _get_bom_draft_row(connection, draft_id)
        else:
            cursor = connection.execute(
                """
                INSERT INTO ly_local_bom_drafts (
                    scenario_tag,
                    bom_no,
                    item_code,
                    version_no,
                    status,
                    is_default,
                    bom_items_json,
                    operations_json,
                    note,
                    state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
                """,
                (
                    scenario_tag,
                    bom_no,
                    item_code,
                    version_no,
                    status,
                    1 if is_default else 0,
                    bom_items_json,
                    operations_json,
                    note,
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()
            row = _get_bom_draft_row(connection, int(cursor.lastrowid))

    if row is None:
        raise HTTPException(status_code=500, detail="draft persistence failed")
    return _ok(_bom_draft_row_to_dict(row))


@app.get("/api/local-dev/bom-drafts/residual-count")
def get_local_bom_draft_residual_count(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_bom_drafts WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.post("/api/local-dev/bom-drafts/rollback-by-scenario")
def rollback_local_bom_drafts(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_bom_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
        deleted_count = int(before["total"]) if before else 0
        connection.execute(
            "DELETE FROM ly_local_bom_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        )
        connection.commit()
        after = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_bom_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
    residual = int(after["total"]) if after else 0
    return _ok(
        {
            "scenario_tag": scenario_tag,
            "deleted_count": deleted_count,
            "residual_records_after_rollback": residual,
            "rollback_success": residual == 0,
            "zero_residual_success": residual == 0,
        }
    )


@app.get("/api/local-dev/bom-drafts/{draft_id}")
def get_local_bom_draft(draft_id: int) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        row = _get_bom_draft_row(connection, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return _ok(_bom_draft_row_to_dict(row))


@app.post("/api/local-dev/bom-drafts/{draft_id}/cancel")
def cancel_local_bom_draft(draft_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    reason = str(payload.get("reason", "")).strip() or f"CANCEL-{scenario_tag or draft_id}"
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        row = _get_bom_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        if row["scenario_tag"] != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")
        connection.execute(
            """
            UPDATE ly_local_bom_drafts
            SET state = 'cancelled',
                updated_at = ?,
                cancelled_at = ?,
                cancel_reason = ?
            WHERE id = ?
            """,
            (now_iso, now_iso, reason, draft_id),
        )
        connection.commit()
        cancelled = _get_bom_draft_row(connection, draft_id)
    if cancelled is None:
        raise HTTPException(status_code=500, detail="draft cancel failed")
    return _ok(_bom_draft_row_to_dict(cancelled))


def _create_sales_order_draft_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ly_local_sales_order_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            order_no TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            style_code TEXT NOT NULL,
            delivery_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            quantity_matrix_json TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'saved',
            linked_plan_draft_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            cancelled_at TEXT,
            cancel_reason TEXT
        )
        """
    )
    connection.commit()


def _create_production_plan_draft_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ly_local_production_plan_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            order_draft_id INTEGER,
            order_no TEXT NOT NULL,
            style_code TEXT NOT NULL,
            plan_no TEXT NOT NULL,
            planned_qty REAL NOT NULL,
            plan_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
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


def _get_sales_order_draft_row(connection: sqlite3.Connection, draft_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM ly_local_sales_order_drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()


def _get_production_plan_draft_row(connection: sqlite3.Connection, draft_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM ly_local_production_plan_drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()


def _to_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_sales_order_matrix(raw_matrix: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_matrix, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw_matrix:
        if not isinstance(item, dict):
            continue
        color = str(item.get("color", "")).strip()
        size = str(item.get("size", "")).strip()
        if not color or not size:
            continue
        ordered_qty = _to_float(item.get("ordered_qty"), 0.0)
        planned_qty = _to_float(item.get("planned_qty"), 0.0)
        delta_qty = ordered_qty - planned_qty
        normalized.append(
            {
                "color": color,
                "size": size,
                "ordered_qty": ordered_qty,
                "planned_qty": planned_qty,
                "delta_qty": delta_qty,
            }
        )
    return normalized


def _matrix_saved(matrix: list[dict[str, Any]]) -> bool:
    if len(matrix) < 2:
        return False
    return any(_to_float(cell.get("ordered_qty"), 0) > 0 for cell in matrix)


def _sales_order_draft_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    matrix = _normalize_sales_order_matrix(_parse_json_payload(row["quantity_matrix_json"]))
    return {
        "draft_id": int(row["id"]),
        "scenario_tag": row["scenario_tag"],
        "order_no": row["order_no"],
        "customer_name": row["customer_name"],
        "style_code": row["style_code"],
        "delivery_date": row["delivery_date"],
        "status": row["status"],
        "quantity_matrix": matrix,
        "note": row["note"],
        "state": row["state"],
        "linked_plan_draft_id": row["linked_plan_draft_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cancelled_at": row["cancelled_at"],
        "cancel_reason": row["cancel_reason"],
        "quantity_matrix_saved": _matrix_saved(matrix),
        "production_plan_draft_created": row["linked_plan_draft_id"] is not None,
    }


def _production_plan_draft_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "draft_id": int(row["id"]),
        "scenario_tag": row["scenario_tag"],
        "order_draft_id": row["order_draft_id"],
        "order_no": row["order_no"],
        "style_code": row["style_code"],
        "plan_no": row["plan_no"],
        "planned_qty": _to_float(row["planned_qty"], 0.0),
        "plan_date": row["plan_date"],
        "status": row["status"],
        "note": row["note"],
        "state": row["state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cancelled_at": row["cancelled_at"],
        "cancel_reason": row["cancel_reason"],
    }


@app.post("/api/local-dev/sales-order-drafts")
def upsert_local_sales_order_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    order_no = str(payload.get("order_no", "")).strip()
    customer_name = str(payload.get("customer_name", "")).strip()
    style_code = str(payload.get("style_code", "")).strip()
    delivery_date = str(payload.get("delivery_date", "")).strip() or date.today().isoformat()
    status = str(payload.get("status", "")).strip() or "draft"
    note = str(payload.get("note", "")).strip()
    draft_id = payload.get("draft_id")
    linked_plan_draft_id_raw = payload.get("linked_plan_draft_id")
    linked_plan_draft_id = linked_plan_draft_id_raw if isinstance(linked_plan_draft_id_raw, int) else None
    matrix = _normalize_sales_order_matrix(payload.get("quantity_matrix", []))

    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    if not order_no:
        raise HTTPException(status_code=400, detail="order_no is required")
    if not customer_name:
        raise HTTPException(status_code=400, detail="customer_name is required")
    if not style_code:
        raise HTTPException(status_code=400, detail="style_code is required")
    if len(matrix) < 2:
        raise HTTPException(status_code=400, detail="quantity_matrix requires at least 2 cells")

    now_iso = _now_iso()
    matrix_json = json.dumps(matrix, ensure_ascii=False)
    with _connect_local_sqlite() as connection:
        _create_sales_order_draft_table(connection)
        if isinstance(draft_id, int) and draft_id > 0:
            exists = _get_sales_order_draft_row(connection, draft_id)
            if not exists:
                raise HTTPException(status_code=404, detail="draft not found")
            connection.execute(
                """
                UPDATE ly_local_sales_order_drafts
                SET scenario_tag = ?,
                    order_no = ?,
                    customer_name = ?,
                    style_code = ?,
                    delivery_date = ?,
                    status = ?,
                    quantity_matrix_json = ?,
                    note = ?,
                    linked_plan_draft_id = ?,
                    state = 'saved',
                    updated_at = ?,
                    cancelled_at = NULL,
                    cancel_reason = NULL
                WHERE id = ?
                """,
                (
                    scenario_tag,
                    order_no,
                    customer_name,
                    style_code,
                    delivery_date,
                    status,
                    matrix_json,
                    note,
                    linked_plan_draft_id,
                    now_iso,
                    draft_id,
                ),
            )
            connection.commit()
            row = _get_sales_order_draft_row(connection, draft_id)
        else:
            cursor = connection.execute(
                """
                INSERT INTO ly_local_sales_order_drafts (
                    scenario_tag,
                    order_no,
                    customer_name,
                    style_code,
                    delivery_date,
                    status,
                    quantity_matrix_json,
                    note,
                    linked_plan_draft_id,
                    state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
                """,
                (
                    scenario_tag,
                    order_no,
                    customer_name,
                    style_code,
                    delivery_date,
                    status,
                    matrix_json,
                    note,
                    linked_plan_draft_id,
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()
            row = _get_sales_order_draft_row(connection, int(cursor.lastrowid))
    if row is None:
        raise HTTPException(status_code=500, detail="draft persistence failed")
    return _ok(_sales_order_draft_row_to_dict(row))


@app.get("/api/local-dev/sales-order-drafts")
def list_local_sales_order_drafts(
    keyword: str | None = None,
    customer_name: str | None = None,
    status: str | None = None,
    style_code: str | None = None,
    scenario_tag: str | None = None,
) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_sales_order_draft_table(connection)
        rows = connection.execute(
            "SELECT * FROM ly_local_sales_order_drafts ORDER BY id DESC",
        ).fetchall()
    items = [_sales_order_draft_row_to_dict(row) for row in rows]
    keyword_token = (keyword or "").strip().lower()
    customer_token = (customer_name or "").strip().lower()
    status_token = (status or "").strip().lower()
    style_token = (style_code or "").strip().lower()
    scenario_token = (scenario_tag or "").strip()

    def _match(item: dict[str, Any]) -> bool:
        if keyword_token and keyword_token not in (
            f"{item['order_no']} {item['customer_name']} {item['style_code']}".lower()
        ):
            return False
        if customer_token and customer_token not in item["customer_name"].lower():
            return False
        if status_token and status_token != str(item["status"]).lower():
            return False
        if style_token and style_token not in str(item["style_code"]).lower():
            return False
        if scenario_token and scenario_token != str(item["scenario_tag"]):
            return False
        return True

    filtered = [item for item in items if _match(item)]
    return _ok({"items": filtered, "total": len(filtered)})


@app.get("/api/local-dev/sales-order-drafts/residual-count")
def get_local_sales_order_residual_count(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_sales_order_draft_table(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_sales_order_drafts WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.post("/api/local-dev/sales-order-drafts/rollback-by-scenario")
def rollback_local_sales_order_drafts(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_sales_order_draft_table(connection)
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_sales_order_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
        deleted_count = int(before["total"]) if before else 0
        connection.execute(
            "DELETE FROM ly_local_sales_order_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        )
        connection.commit()
        after = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_sales_order_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
    residual = int(after["total"]) if after else 0
    return _ok(
        {
            "scenario_tag": scenario_tag,
            "deleted_count": deleted_count,
            "residual_records_after_rollback": residual,
            "rollback_success": residual == 0,
            "zero_residual_success": residual == 0,
        }
    )


@app.get("/api/local-dev/sales-order-drafts/{draft_id}")
def get_local_sales_order_draft(draft_id: int) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_sales_order_draft_table(connection)
        row = _get_sales_order_draft_row(connection, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return _ok(_sales_order_draft_row_to_dict(row))


@app.post("/api/local-dev/sales-order-drafts/{draft_id}/cancel")
def cancel_local_sales_order_draft(draft_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    reason = str(payload.get("reason", "")).strip() or f"CANCEL-{scenario_tag or draft_id}"
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_sales_order_draft_table(connection)
        row = _get_sales_order_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        if row["scenario_tag"] != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")
        connection.execute(
            """
            UPDATE ly_local_sales_order_drafts
            SET state = 'cancelled',
                updated_at = ?,
                cancelled_at = ?,
                cancel_reason = ?
            WHERE id = ?
            """,
            (now_iso, now_iso, reason, draft_id),
        )
        connection.commit()
        cancelled = _get_sales_order_draft_row(connection, draft_id)
    if cancelled is None:
        raise HTTPException(status_code=500, detail="draft cancel failed")
    return _ok(_sales_order_draft_row_to_dict(cancelled))


@app.post("/api/local-dev/production-plan-drafts")
def upsert_local_production_plan_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    order_draft_id_raw = payload.get("order_draft_id")
    order_draft_id = order_draft_id_raw if isinstance(order_draft_id_raw, int) else None
    order_no = str(payload.get("order_no", "")).strip()
    style_code = str(payload.get("style_code", "")).strip()
    plan_no = str(payload.get("plan_no", "")).strip() or f"PLAN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    plan_date = str(payload.get("plan_date", "")).strip() or date.today().isoformat()
    status = str(payload.get("status", "")).strip() or "draft"
    note = str(payload.get("note", "")).strip()
    draft_id = payload.get("draft_id")
    planned_qty = _to_float(payload.get("planned_qty"), 0.0)

    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    if not order_no:
        raise HTTPException(status_code=400, detail="order_no is required")
    if not style_code:
        raise HTTPException(status_code=400, detail="style_code is required")
    if planned_qty <= 0:
        raise HTTPException(status_code=400, detail="planned_qty must be greater than 0")

    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_sales_order_draft_table(connection)
        _create_production_plan_draft_table(connection)
        if isinstance(draft_id, int) and draft_id > 0:
            exists = _get_production_plan_draft_row(connection, draft_id)
            if not exists:
                raise HTTPException(status_code=404, detail="plan draft not found")
            connection.execute(
                """
                UPDATE ly_local_production_plan_drafts
                SET scenario_tag = ?,
                    order_draft_id = ?,
                    order_no = ?,
                    style_code = ?,
                    plan_no = ?,
                    planned_qty = ?,
                    plan_date = ?,
                    status = ?,
                    note = ?,
                    state = 'saved',
                    updated_at = ?,
                    cancelled_at = NULL,
                    cancel_reason = NULL
                WHERE id = ?
                """,
                (
                    scenario_tag,
                    order_draft_id,
                    order_no,
                    style_code,
                    plan_no,
                    planned_qty,
                    plan_date,
                    status,
                    note,
                    now_iso,
                    draft_id,
                ),
            )
            connection.commit()
            row = _get_production_plan_draft_row(connection, draft_id)
            created_plan_id = draft_id
        else:
            cursor = connection.execute(
                """
                INSERT INTO ly_local_production_plan_drafts (
                    scenario_tag,
                    order_draft_id,
                    order_no,
                    style_code,
                    plan_no,
                    planned_qty,
                    plan_date,
                    status,
                    note,
                    state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
                """,
                (
                    scenario_tag,
                    order_draft_id,
                    order_no,
                    style_code,
                    plan_no,
                    planned_qty,
                    plan_date,
                    status,
                    note,
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()
            created_plan_id = int(cursor.lastrowid)
            row = _get_production_plan_draft_row(connection, created_plan_id)

        if order_draft_id is not None:
            connection.execute(
                """
                UPDATE ly_local_sales_order_drafts
                SET linked_plan_draft_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (created_plan_id, now_iso, order_draft_id),
            )
            connection.commit()

    if row is None:
        raise HTTPException(status_code=500, detail="plan draft persistence failed")
    return _ok(_production_plan_draft_row_to_dict(row))


@app.get("/api/local-dev/production-plan-drafts")
def list_local_production_plan_drafts(
    scenario_tag: str | None = None,
    order_no: str | None = None,
    style_code: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_production_plan_draft_table(connection)
        rows = connection.execute(
            "SELECT * FROM ly_local_production_plan_drafts ORDER BY id DESC",
        ).fetchall()
    items = [_production_plan_draft_row_to_dict(row) for row in rows]
    scenario_token = (scenario_tag or "").strip()
    order_token = (order_no or "").strip().lower()
    style_token = (style_code or "").strip().lower()
    status_token = (status or "").strip().lower()
    keyword_token = (keyword or "").strip().lower()

    def _match(item: dict[str, Any]) -> bool:
        if scenario_token and scenario_token != str(item["scenario_tag"]):
            return False
        if order_token and order_token not in str(item["order_no"]).lower():
            return False
        if style_token and style_token not in str(item["style_code"]).lower():
            return False
        if status_token and status_token != str(item["status"]).lower():
            return False
        if keyword_token and keyword_token not in (
            f"{item['plan_no']} {item['order_no']} {item['style_code']}".lower()
        ):
            return False
        return True

    filtered = [item for item in items if _match(item)]
    return _ok({"items": filtered, "total": len(filtered)})


@app.get("/api/local-dev/production-plan-drafts/residual-count")
def get_local_production_plan_residual_count(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_production_plan_draft_table(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_production_plan_drafts WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.post("/api/local-dev/production-plan-drafts/rollback-by-scenario")
def rollback_local_production_plan_drafts(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_production_plan_draft_table(connection)
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_production_plan_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
        deleted_count = int(before["total"]) if before else 0
        connection.execute(
            "DELETE FROM ly_local_production_plan_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        )
        connection.commit()
        after = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_production_plan_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
    residual = int(after["total"]) if after else 0
    return _ok(
        {
            "scenario_tag": scenario_tag,
            "deleted_count": deleted_count,
            "residual_records_after_rollback": residual,
            "rollback_success": residual == 0,
            "zero_residual_success": residual == 0,
        }
    )
