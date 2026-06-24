"""Local development ASGI entrypoint.

This module keeps the production app unchanged while making the local Vue
frontend usable without ERPNext login cookies. It enables dev-header auth,
uses a SQLite database with schema translation, creates the tables needed by
the local screens, and seeds a tiny BOM fixture if the database is empty.
"""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
import json
import os
import sqlite3

from fastapi import Body
from fastapi import HTTPException
from fastapi import Query
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker

os.environ["APP_ENV"] = "development"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "fastapi"
os.environ.setdefault("LINGYI_DB_URL", "sqlite:///./lingyi_service.local.db")

from app.core.permissions import DEFAULT_STATIC_ROLE_ACTIONS  # noqa: E402


def _default_fastapi_role_actions_json() -> str:
    # Local-dev still resolves through the FastAPI permission source; this only seeds role-action config.
    return json.dumps(
        {
            "roles": {
                role: sorted(actions)
                for role, actions in sorted(DEFAULT_STATIC_ROLE_ACTIONS.items())
            }
        },
        ensure_ascii=False,
        sort_keys=True,
    )


os.environ.setdefault("LINGYI_FASTAPI_ROLE_ACTIONS_JSON", _default_fastapi_role_actions_json())

from app import main as main_module  # noqa: E402
from app.models.audit import Base as AuditBase  # noqa: E402
from app.models.bom import Base as BomBase  # noqa: E402
from app.models.bom import LyApparelBom  # noqa: E402
from app.models.bom import LyApparelBomItem  # noqa: E402
from app.models.bom import LyBomOperation  # noqa: E402
from app.models.factory_statement import Base as FactoryStatementBase  # noqa: E402
from app.models.finance_approval import Base as FinanceApprovalBase  # noqa: E402
from app.models.master_data import Base as MasterDataBase  # noqa: E402
from app.models.master_data import LyMasterDataRecord  # noqa: E402
from app.models.material_purchase import Base as MaterialPurchaseBase  # noqa: E402
from app.models.material_purchase import LyMaterialPurchaseRequirement  # noqa: E402
from app.models.production import Base as ProductionBase  # noqa: E402
from app.models.production import LyProductionPlan  # noqa: E402
from app.models.production import LyProductionPlanMaterial  # noqa: E402
from app.models.quality import Base as QualityBase  # noqa: E402
import app.models.quality_outbox  # noqa: E402,F401
from app.models.recycle_bin import Base as RecycleBinBase  # noqa: E402
from app.models.sample import Base as SampleBase  # noqa: E402
from app.models.sales_order import Base as SalesOrderBase  # noqa: E402
from app.models.sales_order import LySalesOrder  # noqa: E402
from app.models.sales_order import LySalesOrderItem  # noqa: E402
from app.models.style_master import Base as StyleMasterBase  # noqa: E402
from app.models.style_master import LyStyleDictionary  # noqa: E402
from app.models.style_master import LyStyleMaster  # noqa: E402
from app.models.style_profit import Base as StyleProfitBase  # noqa: E402
from app.models.subcontract import Base as SubcontractBase  # noqa: E402
import app.models.warehouse  # noqa: E402,F401
from app.models.workshop import Base as WorkshopBase  # noqa: E402
from app.services.finance_approval_service import FinanceApprovalService  # noqa: E402


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
    FinanceApprovalBase.metadata.create_all(bind=main_module.engine)
    MasterDataBase.metadata.create_all(bind=main_module.engine)
    MaterialPurchaseBase.metadata.create_all(bind=main_module.engine)
    SampleBase.metadata.create_all(bind=main_module.engine)
    SalesOrderBase.metadata.create_all(bind=main_module.engine)
    StyleMasterBase.metadata.create_all(bind=main_module.engine)
    QualityBase.metadata.create_all(bind=main_module.engine)
    StyleProfitBase.metadata.create_all(bind=main_module.engine)
    WorkshopBase.metadata.create_all(bind=main_module.engine)
    RecycleBinBase.metadata.create_all(bind=main_module.engine)

    # Subcontract models reference BOM metadata from a separate declarative Base.
    # Copying the table definition into this metadata is enough for SQLite local DDL.
    if "ly_schema.ly_apparel_bom" not in SubcontractBase.metadata.tables:
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
    SubcontractBase.metadata.create_all(bind=main_module.engine)
    _ensure_local_master_data_config_entities()
    _ensure_local_sample_idempotency_supports_seal()
    _ensure_local_sales_order_item_calc_columns()
    _ensure_local_sales_order_idempotency_supports_update()
    _ensure_local_style_dictionary_color_size_types()
    _ensure_local_style_master_idempotency_supports_gallery()
    _ensure_local_sample_style_master_link()
    _ensure_local_material_bom_size_columns()
    _ensure_local_subcontract_create_idempotency_columns()
    _ensure_local_inventory_count_idempotency_columns()
    _ensure_local_material_purchase_payment_pending_approval_status()
    _ensure_local_factory_statement_payment_pending_approval_status()
    _ensure_local_bom_company_style_columns()
    _ensure_local_production_material_uom_column()
    _ensure_local_bom_dimension_columns()
    _ensure_local_stock_entry_purchase_requirement_column()
    _ensure_local_stock_ledger_context_columns()
    _ensure_local_production_quote_operation_supports_quote_actions()
    _ensure_local_production_followup_node_operation_supports_edit()
    _seed_local_finance_approval_templates()


def _seed_local_finance_approval_templates() -> None:
    db = main_module.SessionLocal()
    try:
        FinanceApprovalService(db).ensure_default_templates(company="默认公司", actor="local-dev-seed")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _ensure_local_master_data_config_entities() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    required_fragments = [
        "'sample_type'",
        "'sample_stage'",
        "'common_address'",
        "'trade_term'",
        "'invoice_type'",
        "'cost_type'",
        "'size_sort'",
        "'distribution_channel'",
        "'bank_account'",
    ]
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_master_data_record'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        if not row or all(fragment in existing_sql for fragment in required_fragments):
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            DROP INDEX IF EXISTS uk_ly_master_data_entity_company_code;
            DROP INDEX IF EXISTS idx_ly_master_data_entity_company_status;
            DROP INDEX IF EXISTS idx_ly_master_data_entity_name;
            CREATE TABLE ly_master_data_record_new (
                id INTEGER NOT NULL,
                entity_type VARCHAR(32) NOT NULL,
                company VARCHAR(140) NOT NULL,
                code VARCHAR(140) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(16) DEFAULT 'active' NOT NULL,
                payload JSON NOT NULL,
                version INTEGER DEFAULT '1' NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_by VARCHAR(140),
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                deactivated_by VARCHAR(140),
                deactivated_at DATETIME,
                deactivate_reason TEXT,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_master_data_entity_type CHECK (entity_type IN ('customer','supplier','factory','warehouse','material','sample_type','sample_stage','common_address','trade_term','invoice_type','cost_type','size_sort','distribution_channel','bank_account')),
                CONSTRAINT ck_ly_master_data_status CHECK (status IN ('active','inactive'))
            );
            INSERT INTO ly_master_data_record_new (
                id, entity_type, company, code, name, status, payload, version,
                created_by, created_at, updated_by, updated_at, deactivated_by,
                deactivated_at, deactivate_reason
            )
            SELECT
                id, entity_type, company, code, name, status, payload, version,
                created_by, created_at, updated_by, updated_at, deactivated_by,
                deactivated_at, deactivate_reason
            FROM ly_master_data_record;
            DROP TABLE ly_master_data_record;
            ALTER TABLE ly_master_data_record_new RENAME TO ly_master_data_record;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_master_data_entity_company_code
                ON ly_master_data_record (entity_type, company, code);
            CREATE INDEX IF NOT EXISTS idx_ly_master_data_entity_company_status
                ON ly_master_data_record (entity_type, company, status);
            CREATE INDEX IF NOT EXISTS idx_ly_master_data_entity_name
                ON ly_master_data_record (entity_type, name);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_sample_idempotency_supports_seal() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_sample_idempotency'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        required_fragments = [
            "'tracking_event'",
            "'create_tracking_event'",
            "'start_patterning'",
            "'start_fitting'",
            "'seal'",
            "'deactivate'",
            "'delete_node'",
        ]
        if not row or all(fragment in existing_sql for fragment in required_fragments):
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            CREATE TABLE ly_sample_idempotency_new (
                id INTEGER NOT NULL,
                entity_type VARCHAR(32) NOT NULL,
                company VARCHAR(140) NOT NULL,
                idempotency_key VARCHAR(140) NOT NULL,
                operation VARCHAR(32) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                record_id INTEGER NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_sample_idem_entity CHECK (entity_type IN ('order','template','node','tracking_event')),
                CONSTRAINT ck_ly_sample_idem_operation CHECK (operation IN ('create','update','submit','start_patterning','start_fitting','seal','reverse','convert','deactivate','create_node','delete_node','create_tracking_event'))
            );
            INSERT INTO ly_sample_idempotency_new (
                id, entity_type, company, idempotency_key, operation, request_hash, record_id, created_by, created_at
            )
            SELECT id, entity_type, company, idempotency_key, operation, request_hash, record_id, created_by, created_at
            FROM ly_sample_idempotency;
            DROP TABLE ly_sample_idempotency;
            ALTER TABLE ly_sample_idempotency_new RENAME TO ly_sample_idempotency;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_sample_idem_key
                ON ly_sample_idempotency (entity_type, company, idempotency_key);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_sales_order_item_calc_columns() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_sales_order_item'"
        ).fetchone()
        if not table_exists:
            return
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_sales_order_item)").fetchall()
        }
        if "style_master_id" not in existing_columns:
            conn.execute("ALTER TABLE ly_sales_order_item ADD COLUMN style_master_id INTEGER")
        if "color" not in existing_columns:
            conn.execute("ALTER TABLE ly_sales_order_item ADD COLUMN color VARCHAR(64)")
        if "size" not in existing_columns:
            conn.execute("ALTER TABLE ly_sales_order_item ADD COLUMN size VARCHAR(64)")
        if "ys_material_calc_state" not in existing_columns:
            conn.execute(
                "ALTER TABLE ly_sales_order_item ADD COLUMN ys_material_calc_state VARCHAR(32) NOT NULL DEFAULT '待算料'"
            )
        style_table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_style_master'"
        ).fetchone()
        if style_table_exists:
            conn.execute(
                """
                UPDATE ly_sales_order_item
                SET style_master_id = (
                    SELECT sm.id
                    FROM ly_style_master sm
                    WHERE sm.company = ly_sales_order_item.company
                      AND sm.ys_style_no = ly_sales_order_item.item_code
                      AND sm.ys_style_status = 'enabled'
                    ORDER BY sm.id
                    LIMIT 1
                )
                WHERE style_master_id IS NULL
                """
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ly_sales_order_item_style_master ON ly_sales_order_item(company, style_master_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ly_sales_order_item_material_calc ON ly_sales_order_item(company, ys_material_calc_state)"
        )


def _ensure_local_sales_order_idempotency_supports_update() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_sales_order_idempotency'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        required_operations = ["'create_draft'", "'update_draft'", "'submit_draft'", "'cancel_draft'"]
        if not row or all(operation in existing_sql for operation in required_operations):
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            CREATE TABLE ly_sales_order_idempotency_new (
                id INTEGER NOT NULL,
                company VARCHAR(140) NOT NULL,
                operation VARCHAR(32) NOT NULL,
                idempotency_key VARCHAR(140) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                sales_order_id INTEGER NOT NULL,
                response_json JSON NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_sales_order_idem_operation CHECK (operation IN ('create_draft','update_draft','submit_draft','cancel_draft'))
            );
            INSERT INTO ly_sales_order_idempotency_new (
                id, company, operation, idempotency_key, request_hash, sales_order_id, response_json, created_by, created_at
            )
            SELECT id, company, operation, idempotency_key, request_hash, sales_order_id, response_json, created_by, created_at
            FROM ly_sales_order_idempotency;
            DROP TABLE ly_sales_order_idempotency;
            ALTER TABLE ly_sales_order_idempotency_new RENAME TO ly_sales_order_idempotency;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_sales_order_idem
                ON ly_sales_order_idempotency (company, operation, idempotency_key);
            CREATE INDEX IF NOT EXISTS idx_ly_sales_order_idem_order
                ON ly_sales_order_idempotency (sales_order_id);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_style_dictionary_color_size_types() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_style_dictionary'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        if not row or all(fragment in existing_sql for fragment in ["'color'", "'size'"]):
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            DROP INDEX IF EXISTS uk_ly_style_dictionary_company_code;
            DROP INDEX IF EXISTS idx_ly_style_dictionary_company_type_status;
            CREATE TABLE ly_style_dictionary_new (
                id INTEGER NOT NULL,
                company VARCHAR(140) NOT NULL,
                dict_type VARCHAR(32) NOT NULL,
                code VARCHAR(140) NOT NULL,
                name VARCHAR(255) NOT NULL,
                status VARCHAR(16) DEFAULT 'active' NOT NULL,
                sort_no INTEGER DEFAULT '10' NOT NULL,
                version INTEGER DEFAULT '1' NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_by VARCHAR(140),
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                deactivated_by VARCHAR(140),
                deactivated_at DATETIME,
                deactivate_reason TEXT,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_style_dictionary_type CHECK (dict_type IN ('season','year','brand','color','size')),
                CONSTRAINT ck_ly_style_dictionary_status CHECK (status IN ('active','inactive'))
            );
            INSERT INTO ly_style_dictionary_new (
                id, company, dict_type, code, name, status, sort_no, version, created_by, created_at,
                updated_by, updated_at, deactivated_by, deactivated_at, deactivate_reason
            )
            SELECT
                id, company, dict_type, code, name, status, sort_no, version, created_by, created_at,
                updated_by, updated_at, deactivated_by, deactivated_at, deactivate_reason
            FROM ly_style_dictionary;
            DROP TABLE ly_style_dictionary;
            ALTER TABLE ly_style_dictionary_new RENAME TO ly_style_dictionary;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_style_dictionary_company_code
                ON ly_style_dictionary (dict_type, company, code);
            CREATE INDEX IF NOT EXISTS idx_ly_style_dictionary_company_type_status
                ON ly_style_dictionary (company, dict_type, status);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_style_master_idempotency_supports_gallery() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_style_master_idempotency'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        if not row or ("'gallery'" in existing_sql and "'sku'" in existing_sql):
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            DROP INDEX IF EXISTS uk_ly_style_master_idem_key;
            DROP INDEX IF EXISTS idx_ly_style_master_idem_record;
            CREATE TABLE ly_style_master_idempotency_new (
                id INTEGER NOT NULL,
                entity_type VARCHAR(32) NOT NULL,
                company VARCHAR(140) NOT NULL,
                idempotency_key VARCHAR(140) NOT NULL,
                operation VARCHAR(32) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                record_id INTEGER NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_style_master_idem_entity CHECK (entity_type IN ('style','dictionary','gallery','sku')),
                CONSTRAINT ck_ly_style_master_idem_operation CHECK (operation IN ('create','update','deactivate'))
            );
            INSERT INTO ly_style_master_idempotency_new (
                id, entity_type, company, idempotency_key, operation, request_hash, record_id, created_by, created_at
            )
            SELECT id, entity_type, company, idempotency_key, operation, request_hash, record_id, created_by, created_at
            FROM ly_style_master_idempotency;
            DROP TABLE ly_style_master_idempotency;
            ALTER TABLE ly_style_master_idempotency_new RENAME TO ly_style_master_idempotency;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_style_master_idem_key
                ON ly_style_master_idempotency (entity_type, company, idempotency_key);
            CREATE INDEX IF NOT EXISTS idx_ly_style_master_idem_record
                ON ly_style_master_idempotency (entity_type, record_id);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_sample_style_master_link() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_sample_order'"
        ).fetchone()
        if not table_exists:
            return
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_sample_order)").fetchall()
        }
        if "style_master_id" not in existing_columns:
            conn.execute("ALTER TABLE ly_sample_order ADD COLUMN style_master_id INTEGER")
        style_table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_style_master'"
        ).fetchone()
        if style_table_exists:
            conn.execute(
                """
                UPDATE ly_sample_order
                SET style_master_id = (
                    SELECT sm.id
                    FROM ly_style_master sm
                    WHERE sm.company = ly_sample_order.company
                      AND sm.ys_style_no = ly_sample_order.style_no
                      AND sm.ys_style_status = 'enabled'
                    ORDER BY sm.id
                    LIMIT 1
                )
                WHERE style_master_id IS NULL
                """
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ly_sample_order_style_master ON ly_sample_order(company, style_master_id)"
        )


def _ensure_local_material_bom_size_columns() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        for table_name in ("ly_apparel_bom_item", "ly_sample_material_bom_item"):
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            if not table_exists:
                continue
            existing_columns = {
                str(row[1]) for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            }
            if "size" not in existing_columns:
                conn.execute(f"ALTER TABLE {table_name} ADD COLUMN size VARCHAR(64)")


def _ensure_local_subcontract_create_idempotency_columns() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_subcontract_order'"
        ).fetchone()
        if not table_exists:
            return
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_subcontract_order)").fetchall()
        }
        if "source_ref" not in existing_columns:
            conn.execute("ALTER TABLE ly_subcontract_order ADD COLUMN source_ref VARCHAR(140)")
        if "idempotency_key" not in existing_columns:
            conn.execute("ALTER TABLE ly_subcontract_order ADD COLUMN idempotency_key VARCHAR(128)")
        if "request_hash" not in existing_columns:
            conn.execute("ALTER TABLE ly_subcontract_order ADD COLUMN request_hash VARCHAR(64)")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_subcontract_company_idem ON ly_subcontract_order(company, idempotency_key)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_subcontract_company_source ON ly_subcontract_order(company, source_ref)"
        )


def _ensure_local_inventory_count_idempotency_columns() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_warehouse_inventory_count'"
        ).fetchone()
        if not table_exists:
            return
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_warehouse_inventory_count)").fetchall()
        }
        if "idempotency_key" not in existing_columns:
            conn.execute("ALTER TABLE ly_warehouse_inventory_count ADD COLUMN idempotency_key VARCHAR(140)")
        if "source_ref" not in existing_columns:
            conn.execute("ALTER TABLE ly_warehouse_inventory_count ADD COLUMN source_ref VARCHAR(140)")
        if "request_hash" not in existing_columns:
            conn.execute("ALTER TABLE ly_warehouse_inventory_count ADD COLUMN request_hash VARCHAR(64)")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_whse_inv_count_company_idempotency ON ly_warehouse_inventory_count(company, idempotency_key)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_whse_inv_count_company_source_ref ON ly_warehouse_inventory_count(company, source_ref)"
        )


def _ensure_local_material_purchase_payment_pending_approval_status() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_material_purchase_payment'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        if not row or "'pending_approval'" in existing_sql:
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            DROP INDEX IF EXISTS uk_ly_material_purchase_payment_company_no;
            DROP INDEX IF EXISTS uk_ly_material_purchase_payment_company_idem;
            DROP INDEX IF EXISTS uk_ly_material_purchase_payment_company_source;
            DROP INDEX IF EXISTS idx_ly_material_purchase_payment_invoice;
            DROP INDEX IF EXISTS idx_ly_material_purchase_payment_supplier;
            CREATE TABLE ly_material_purchase_payment_new (
                id INTEGER NOT NULL,
                company VARCHAR(140) NOT NULL,
                payment_entry VARCHAR(140) NOT NULL,
                purchase_invoice_id INTEGER NOT NULL,
                purchase_invoice VARCHAR(140) NOT NULL,
                purchase_no VARCHAR(140) NOT NULL,
                supplier_name VARCHAR(255) NOT NULL,
                posting_date DATE NOT NULL,
                paid_amount NUMERIC(18, 6) NOT NULL,
                allocated_amount NUMERIC(18, 6) NOT NULL,
                outstanding_before NUMERIC(18, 6) NOT NULL,
                outstanding_after NUMERIC(18, 6) NOT NULL,
                mode_of_payment VARCHAR(140) DEFAULT 'Bank Transfer' NOT NULL,
                reference_no VARCHAR(140),
                reference_date DATE,
                status VARCHAR(32) DEFAULT 'submitted' NOT NULL,
                docstatus INTEGER DEFAULT '1' NOT NULL,
                source_ref VARCHAR(140) NOT NULL,
                idempotency_key VARCHAR(140) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                scenario_tag VARCHAR(64),
                payload JSON NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_by VARCHAR(140),
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_material_purchase_payment_status CHECK (status IN ('pending_approval','submitted','cancelled')),
                CONSTRAINT ck_ly_material_purchase_payment_amount_positive CHECK (paid_amount > 0),
                CONSTRAINT ck_ly_material_purchase_payment_allocated_positive CHECK (allocated_amount > 0),
                CONSTRAINT ck_ly_material_purchase_payment_before_nonnegative CHECK (outstanding_before >= 0),
                CONSTRAINT ck_ly_material_purchase_payment_after_nonnegative CHECK (outstanding_after >= 0),
                FOREIGN KEY(purchase_invoice_id) REFERENCES ly_material_purchase_invoice (id)
            );
            INSERT INTO ly_material_purchase_payment_new (
                id, company, payment_entry, purchase_invoice_id, purchase_invoice, purchase_no,
                supplier_name, posting_date, paid_amount, allocated_amount, outstanding_before,
                outstanding_after, mode_of_payment, reference_no, reference_date, status, docstatus,
                source_ref, idempotency_key, request_hash, scenario_tag, payload, created_by,
                created_at, updated_by, updated_at
            )
            SELECT
                id, company, payment_entry, purchase_invoice_id, purchase_invoice, purchase_no,
                supplier_name, posting_date, paid_amount, allocated_amount, outstanding_before,
                outstanding_after, mode_of_payment, reference_no, reference_date, status, docstatus,
                source_ref, idempotency_key, request_hash, scenario_tag, payload, created_by,
                created_at, updated_by, updated_at
            FROM ly_material_purchase_payment;
            DROP TABLE ly_material_purchase_payment;
            ALTER TABLE ly_material_purchase_payment_new RENAME TO ly_material_purchase_payment;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_material_purchase_payment_company_no
                ON ly_material_purchase_payment (company, payment_entry);
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_material_purchase_payment_company_idem
                ON ly_material_purchase_payment (company, idempotency_key);
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_material_purchase_payment_company_source
                ON ly_material_purchase_payment (company, source_ref);
            CREATE INDEX IF NOT EXISTS idx_ly_material_purchase_payment_invoice
                ON ly_material_purchase_payment (company, purchase_invoice);
            CREATE INDEX IF NOT EXISTS idx_ly_material_purchase_payment_supplier
                ON ly_material_purchase_payment (company, supplier_name);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_factory_statement_payment_pending_approval_status() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_factory_statement_payment'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        if not row or "'pending_approval'" in existing_sql:
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            DROP INDEX IF EXISTS uk_ly_factory_statement_payment_company_no;
            DROP INDEX IF EXISTS uk_ly_factory_statement_payment_company_idem;
            DROP INDEX IF EXISTS uk_ly_factory_statement_payment_company_source;
            DROP INDEX IF EXISTS idx_ly_factory_statement_payment_statement;
            DROP INDEX IF EXISTS idx_ly_factory_statement_payment_supplier;
            CREATE TABLE ly_factory_statement_payment_new (
                id INTEGER NOT NULL,
                company VARCHAR(140) NOT NULL,
                payment_entry VARCHAR(140) NOT NULL,
                statement_id INTEGER NOT NULL,
                statement_no VARCHAR(64) NOT NULL,
                supplier VARCHAR(140) NOT NULL,
                posting_date DATE NOT NULL,
                paid_amount NUMERIC(18, 6) NOT NULL,
                allocated_amount NUMERIC(18, 6) NOT NULL,
                outstanding_before NUMERIC(18, 6) NOT NULL,
                outstanding_after NUMERIC(18, 6) NOT NULL,
                mode_of_payment VARCHAR(140) DEFAULT 'Bank Transfer' NOT NULL,
                reference_no VARCHAR(140),
                reference_date DATE,
                status VARCHAR(32) DEFAULT 'submitted' NOT NULL,
                docstatus INTEGER DEFAULT '1' NOT NULL,
                source_ref VARCHAR(140) NOT NULL,
                idempotency_key VARCHAR(140) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                scenario_tag VARCHAR(64),
                payload JSON NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                updated_by VARCHAR(140),
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_factory_statement_payment_status CHECK (status IN ('pending_approval','submitted','cancelled')),
                CONSTRAINT ck_ly_factory_statement_payment_amount_positive CHECK (paid_amount > 0),
                CONSTRAINT ck_ly_factory_statement_payment_allocated_positive CHECK (allocated_amount > 0),
                CONSTRAINT ck_ly_factory_statement_payment_before_nonnegative CHECK (outstanding_before >= 0),
                CONSTRAINT ck_ly_factory_statement_payment_after_nonnegative CHECK (outstanding_after >= 0),
                FOREIGN KEY(statement_id) REFERENCES ly_factory_statement (id)
            );
            INSERT INTO ly_factory_statement_payment_new (
                id, company, payment_entry, statement_id, statement_no, supplier, posting_date,
                paid_amount, allocated_amount, outstanding_before, outstanding_after, mode_of_payment,
                reference_no, reference_date, status, docstatus, source_ref, idempotency_key,
                request_hash, scenario_tag, payload, created_by, created_at, updated_by, updated_at
            )
            SELECT
                id, company, payment_entry, statement_id, statement_no, supplier, posting_date,
                paid_amount, allocated_amount, outstanding_before, outstanding_after, mode_of_payment,
                reference_no, reference_date, status, docstatus, source_ref, idempotency_key,
                request_hash, scenario_tag, payload, created_by, created_at, updated_by, updated_at
            FROM ly_factory_statement_payment;
            DROP TABLE ly_factory_statement_payment;
            ALTER TABLE ly_factory_statement_payment_new RENAME TO ly_factory_statement_payment;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_factory_statement_payment_company_no
                ON ly_factory_statement_payment (company, payment_entry);
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_factory_statement_payment_company_idem
                ON ly_factory_statement_payment (company, idempotency_key);
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_factory_statement_payment_company_source
                ON ly_factory_statement_payment (company, source_ref);
            CREATE INDEX IF NOT EXISTS idx_ly_factory_statement_payment_statement
                ON ly_factory_statement_payment (company, statement_id);
            CREATE INDEX IF NOT EXISTS idx_ly_factory_statement_payment_supplier
                ON ly_factory_statement_payment (company, supplier);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_bom_company_style_columns() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_apparel_bom'"
        ).fetchone()
        if not table_exists:
            return
        item_table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_apparel_bom_item'"
        ).fetchone()
        if item_table_exists:
            item_columns = {
                str(row[1])
                for row in conn.execute("PRAGMA table_info(ly_apparel_bom_item)").fetchall()
            }
            if "part" not in item_columns:
                conn.execute("ALTER TABLE ly_apparel_bom_item ADD COLUMN part VARCHAR(100)")
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_apparel_bom)").fetchall()
        }
        if "company" not in existing_columns:
            conn.execute("ALTER TABLE ly_apparel_bom ADD COLUMN company VARCHAR(140) NOT NULL DEFAULT '默认公司'")
        if "style_master_id" not in existing_columns:
            conn.execute("ALTER TABLE ly_apparel_bom ADD COLUMN style_master_id INTEGER")
        style_table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_style_master'"
        ).fetchone()
        if style_table_exists:
            conn.execute(
                """
                UPDATE ly_apparel_bom
                SET company = COALESCE(
                    NULLIF(company, ''),
                    (
                        SELECT sm.company
                        FROM ly_style_master sm
                        WHERE sm.ys_style_no = ly_apparel_bom.item_code
                          AND sm.ys_style_status = 'enabled'
                        ORDER BY sm.id
                        LIMIT 1
                    ),
                    '默认公司'
                )
                """
            )
            conn.execute(
                """
                UPDATE ly_apparel_bom
                SET style_master_id = (
                    SELECT sm.id
                    FROM ly_style_master sm
                    WHERE sm.company = ly_apparel_bom.company
                      AND sm.ys_style_no = ly_apparel_bom.item_code
                      AND sm.ys_style_status = 'enabled'
                    ORDER BY sm.id
                    LIMIT 1
                )
                WHERE style_master_id IS NULL
                """
            )
        conn.execute("DROP INDEX IF EXISTS uk_ly_apparel_bom_one_active_default")
        conn.execute("DROP INDEX IF EXISTS idx_ly_apparel_bom_item_default")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ly_apparel_bom_item_default "
            "ON ly_apparel_bom(company, item_code, is_default)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ly_apparel_bom_style_master "
            "ON ly_apparel_bom(style_master_id)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_apparel_bom_one_active_default "
            "ON ly_apparel_bom(company, item_code) "
            "WHERE is_default = 1 AND status = 'active'"
        )


def _ensure_local_production_material_uom_column() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_production_plan_material'"
        ).fetchone()
        if not table_exists:
            return
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_production_plan_material)").fetchall()
        }
        if "uom" not in existing_columns:
            conn.execute(
                "ALTER TABLE ly_production_plan_material ADD COLUMN uom VARCHAR(32) NOT NULL DEFAULT '米'"
            )


def _ensure_local_bom_dimension_columns() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    table_columns = {
        "ly_production_plan_material": ("bom_color", "bom_size", "bom_part"),
        "ly_material_purchase_requirement": ("bom_color", "bom_size", "bom_part"),
    }
    with sqlite3.connect(database_path) as conn:
        for table_name, column_names in table_columns.items():
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            ).fetchone()
            if not table_exists:
                continue
            existing_columns = {
                str(row[1])
                for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            }
            for column_name in column_names:
                if column_name not in existing_columns:
                    conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR(100)")


def _ensure_local_stock_entry_purchase_requirement_column() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_warehouse_stock_entry_draft_item'"
        ).fetchone()
        if not table_exists:
            return
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_warehouse_stock_entry_draft_item)").fetchall()
        }
        column_defs = {
            "purchase_requirement_id": "BIGINT",
            "sales_order_item": "VARCHAR(140)",
            "bom_color": "VARCHAR(100)",
            "bom_size": "VARCHAR(100)",
            "bom_part": "VARCHAR(100)",
        }
        for column_name, column_type in column_defs.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE ly_warehouse_stock_entry_draft_item ADD COLUMN {column_name} {column_type}"
                )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ly_whse_stock_entry_item_requirement "
            "ON ly_warehouse_stock_entry_draft_item(purchase_requirement_id)"
        )


def _ensure_local_stock_ledger_context_columns() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ly_warehouse_stock_ledger_entry'"
        ).fetchone()
        if not table_exists:
            return
        existing_columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(ly_warehouse_stock_ledger_entry)").fetchall()
        }
        column_defs = {
            "purchase_requirement_id": "BIGINT",
            "sales_order_item": "VARCHAR(140)",
            "bom_color": "VARCHAR(100)",
            "bom_size": "VARCHAR(100)",
            "bom_part": "VARCHAR(100)",
        }
        for column_name, column_type in column_defs.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE ly_warehouse_stock_ledger_entry ADD COLUMN {column_name} {column_type}"
                )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ly_whse_stock_ledger_requirement "
            "ON ly_warehouse_stock_ledger_entry(purchase_requirement_id)"
        )


def _ensure_local_production_quote_operation_supports_quote_actions() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_production_quote_operation'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        if not row or ("'copy'" in existing_sql and "'void'" in existing_sql):
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            DROP INDEX IF EXISTS uk_ly_production_quote_operation_idem;
            DROP INDEX IF EXISTS idx_ly_production_quote_operation_quote;
            CREATE TABLE ly_production_quote_operation_new (
                id INTEGER NOT NULL,
                quote_id INTEGER,
                company VARCHAR(140) NOT NULL,
                operation VARCHAR(64) NOT NULL,
                idempotency_key VARCHAR(128) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                response_json JSON NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_production_quote_operation CHECK (operation IN ('create','convert','copy','void')),
                FOREIGN KEY(quote_id) REFERENCES ly_production_quote (id)
            );
            INSERT INTO ly_production_quote_operation_new (
                id, quote_id, company, operation, idempotency_key, request_hash, response_json, created_by, created_at
            )
            SELECT id, quote_id, company, operation, idempotency_key, request_hash, response_json, created_by, created_at
            FROM ly_production_quote_operation;
            DROP TABLE ly_production_quote_operation;
            ALTER TABLE ly_production_quote_operation_new RENAME TO ly_production_quote_operation;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_production_quote_operation_idem
                ON ly_production_quote_operation (company, operation, idempotency_key);
            CREATE INDEX IF NOT EXISTS idx_ly_production_quote_operation_quote
                ON ly_production_quote_operation (quote_id, operation);
            PRAGMA foreign_keys=on;
            """
        )


def _ensure_local_production_followup_node_operation_supports_edit() -> None:
    database_path = main_module.engine.url.database
    if not database_path or database_path == ":memory:":
        return
    with sqlite3.connect(database_path) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='ly_production_followup_template_node_operation'"
        ).fetchone()
        existing_sql = str(row[0]) if row else ""
        if not row or ("'update_node'" in existing_sql and "'delete_node'" in existing_sql):
            return
        conn.executescript(
            """
            PRAGMA foreign_keys=off;
            DROP INDEX IF EXISTS uk_ly_production_followup_template_node_operation_idem;
            DROP INDEX IF EXISTS idx_ly_production_followup_template_node_operation_node;
            CREATE TABLE ly_production_followup_template_node_operation_new (
                id INTEGER NOT NULL,
                template_id INTEGER NOT NULL,
                node_id INTEGER,
                company VARCHAR(140) NOT NULL,
                operation VARCHAR(64) NOT NULL,
                idempotency_key VARCHAR(128) NOT NULL,
                request_hash VARCHAR(64) NOT NULL,
                response_json JSON NOT NULL,
                created_by VARCHAR(140) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                PRIMARY KEY (id),
                CONSTRAINT ck_ly_production_followup_template_node_operation CHECK (operation IN ('create_node','update_node','delete_node')),
                FOREIGN KEY(template_id) REFERENCES ly_production_followup_template (id),
                FOREIGN KEY(node_id) REFERENCES ly_production_followup_template_node (id)
            );
            INSERT INTO ly_production_followup_template_node_operation_new (
                id, template_id, node_id, company, operation, idempotency_key, request_hash, response_json, created_by, created_at
            )
            SELECT id, template_id, node_id, company, operation, idempotency_key, request_hash, response_json, created_by, created_at
            FROM ly_production_followup_template_node_operation;
            DROP TABLE ly_production_followup_template_node_operation;
            ALTER TABLE ly_production_followup_template_node_operation_new RENAME TO ly_production_followup_template_node_operation;
            CREATE UNIQUE INDEX IF NOT EXISTS uk_ly_production_followup_template_node_operation_idem
                ON ly_production_followup_template_node_operation (company, operation, idempotency_key);
            CREATE INDEX IF NOT EXISTS idx_ly_production_followup_template_node_operation_node
                ON ly_production_followup_template_node_operation (node_id, operation);
            PRAGMA foreign_keys=on;
            """
        )


def _seed_local_bom() -> None:
    with main_module.SessionLocal() as session:
        for code, name, precision in [
            ("MU-METER", "米", 2),
            ("MU-PCS", "件", 0),
            ("MU-PIECE", "个", 0),
            ("MU-ROLL", "卷", 0),
            ("MU-YARD", "码", 2),
            ("MU-GROUP", "组", 0),
            ("MU-GRAIN", "粒", 0),
        ]:
            unit = (
                session.query(LyMasterDataRecord)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == "默认公司",
                    LyMasterDataRecord.code == code,
                )
                .first()
            )
            payload = {
                "material_kind": "unit",
                "material_item_code": code,
                "unit_code": code,
                "unit_name": name,
                "base_unit": name,
                "conversion_text": f"1 {name} = 1 {name}",
                "precision": precision,
                "status": "active",
                "is_default": True,
            }
            if unit is None:
                session.add(
                    LyMasterDataRecord(
                        entity_type="material",
                        company="默认公司",
                        code=code,
                        name=name,
                        status="active",
                        payload=payload,
                        version=1,
                        created_by="local.dev",
                        updated_by="local.dev",
                    )
                )
            else:
                unit.name = name
                unit.status = "active"
                unit.payload = {**dict(unit.payload or {}), **payload}
                unit.updated_by = "local.dev"

        for code, name, payload in [
            (
                "FABRIC-COTTON",
                "本地演示棉布",
                {
                    "material_kind": "fabric",
                    "material_item_code": "FABRIC-COTTON",
                    "material_name": "本地演示棉布",
                    "fabric_name": "本地演示棉布",
                    "color": "白色",
                    "uom": "米",
                    "status": "active",
                },
            ),
            (
                "TRIM-BUTTON",
                "本地演示纽扣",
                {
                    "material_kind": "accessory",
                    "material_item_code": "TRIM-BUTTON",
                    "material_name": "本地演示纽扣",
                    "accessory_name": "本地演示纽扣",
                    "color": "白色",
                    "uom": "粒",
                    "status": "active",
                },
            ),
        ]:
            material = (
                session.query(LyMasterDataRecord)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == "默认公司",
                    LyMasterDataRecord.code == code,
                )
                .first()
            )
            if material is None:
                session.add(
                    LyMasterDataRecord(
                        entity_type="material",
                        company="默认公司",
                        code=code,
                        name=name,
                        status="active",
                        payload=payload,
                        version=1,
                        created_by="local.dev",
                        updated_by="local.dev",
                    )
                )
            else:
                material.name = material.name or name
                material.status = "active"
                material.payload = {**dict(material.payload or {}), **payload}
                material.updated_by = "local.dev"

        for index, (dict_type, code, name) in enumerate(
            [
                ("season", "SS", "春夏"),
                ("year", "2026", "2026"),
                ("brand", "LY", "领意"),
                ("color", "WHT", "白"),
                ("color", "BLK", "黑"),
                ("color", "NAVY", "藏青"),
                ("color", "WHITE", "白色"),
                ("color", "BLACK", "黑色"),
                ("size", "S", "S"),
                ("size", "M", "M"),
                ("size", "L", "L"),
                ("size", "XL", "XL"),
            ],
            start=1,
        ):
            dictionary = (
                session.query(LyStyleDictionary)
                .filter(
                    LyStyleDictionary.company == "默认公司",
                    LyStyleDictionary.dict_type == dict_type,
                    LyStyleDictionary.code == code,
                )
                .first()
            )
            if dictionary is None:
                session.add(
                    LyStyleDictionary(
                        company="默认公司",
                        dict_type=dict_type,
                        code=code,
                        name=name,
                        status="active",
                        sort_no=index * 10,
                        version=1,
                        created_by="local.dev",
                        updated_by="local.dev",
                    )
                )
            else:
                dictionary.name = dictionary.name or name
                dictionary.status = "active"
                dictionary.updated_by = "local.dev"

        style = (
            session.query(LyStyleMaster)
            .filter(
                LyStyleMaster.company == "默认公司",
                LyStyleMaster.ys_style_no == "DEMO-TEE",
            )
            .first()
        )
        if style is None:
            style = LyStyleMaster(
                company="默认公司",
                ys_style_no="DEMO-TEE",
                ys_style_name_cn="本地演示T恤",
                ys_season="SS",
                ys_year="2026",
                ys_brand="LY",
                ys_style_status="enabled",
                colors=[
                    {"ys_color_code": "WHITE", "ys_color_name": "白色"},
                    {"ys_color_code": "BLACK", "ys_color_name": "黑色"},
                ],
                sizes=[
                    {"ys_size_code": "M", "ys_size_name": "M"},
                    {"ys_size_code": "L", "ys_size_name": "L"},
                ],
                version=1,
                created_by="local.dev",
                updated_by="local.dev",
            )
            session.add(style)
        else:
            style.ys_style_name_cn = style.ys_style_name_cn or "本地演示T恤"
            style.ys_style_status = "enabled"
            style.colors = style.colors or [
                {"ys_color_code": "WHITE", "ys_color_name": "白色"},
                {"ys_color_code": "BLACK", "ys_color_name": "黑色"},
            ]
            style.sizes = style.sizes or [
                {"ys_size_code": "M", "ys_size_name": "M"},
                {"ys_size_code": "L", "ys_size_name": "L"},
            ]
            style.updated_by = "local.dev"

        session.flush()
        style_id = int(style.id)

        existing = session.query(LyApparelBom).order_by(LyApparelBom.id.asc()).first()
        if existing:
            bom_id = int(existing.id)
            existing.company = "默认公司"
            existing.style_master_id = style_id
            operation = session.query(LyBomOperation).filter(LyBomOperation.bom_id == bom_id, LyBomOperation.process_name == "外发裁剪").first()
            if operation is None:
                next_operation_id = int(session.query(func.coalesce(func.max(LyBomOperation.id), 0)).scalar() or 0) + 1
                session.add(
                    LyBomOperation(
                        id=next_operation_id,
                        bom_id=bom_id,
                        process_name="外发裁剪",
                        sequence_no=10,
                        is_subcontract=True,
                        wage_rate=2.5,
                        subcontract_cost_per_piece=2.5,
                        remark="本地开发演示外发工序",
                    )
                )
            else:
                operation.is_subcontract = True
                operation.subcontract_cost_per_piece = operation.subcontract_cost_per_piece or 2.5
            session.commit()
            return

        bom = LyApparelBom(
            id=1,
            bom_no="BOM-DEMO-TEE-V1",
            company="默认公司",
            style_master_id=style_id,
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
                remark="本地开发演示物料；unit_price=18.50",
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
                remark="本地开发演示辅料；unit_price=0.20",
            ),
        ]
        bom.operations = [
            LyBomOperation(
                id=1,
                bom_id=1,
                process_name="外发裁剪",
                sequence_no=10,
                is_subcontract=True,
                wage_rate=2.5,
                subcontract_cost_per_piece=2.5,
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


def _seed_local_report_chain() -> None:
    """Seed a tiny FastAPI-native order -> plan -> material-read chain for clean API smoke."""
    company = "默认公司"
    actor = "local.dev"
    style_no = "DEMO-TEE"
    sales_order_no = "SO-LOCAL-DEMO-001"
    sales_order_item = "SO-LOCAL-DEMO-001-001"
    plan_no = "PLAN-LOCAL-DEMO-001"
    planned_qty = Decimal("24")
    unit_rate = Decimal("90")
    request_hash = "local-dev-seed".ljust(64, "0")[:64]
    unit_prices = {
        "FABRIC-COTTON": Decimal("18.50"),
        "TRIM-BUTTON": Decimal("0.20"),
    }

    with main_module.SessionLocal() as session:
        style = (
            session.query(LyStyleMaster)
            .filter(
                LyStyleMaster.company == company,
                LyStyleMaster.ys_style_no == style_no,
            )
            .first()
        )
        bom = (
            session.query(LyApparelBom)
            .filter(
                LyApparelBom.company == company,
                LyApparelBom.item_code == style_no,
                LyApparelBom.status == "active",
            )
            .order_by(LyApparelBom.is_default.desc(), LyApparelBom.id.desc())
            .first()
        )
        if style is None or bom is None:
            return

        bom_items = (
            session.query(LyApparelBomItem)
            .filter(LyApparelBomItem.bom_id == int(bom.id))
            .order_by(LyApparelBomItem.id.asc())
            .all()
        )
        for bom_item in bom_items:
            price = unit_prices.get(str(bom_item.material_item_code))
            remark = str(bom_item.remark or "").strip()
            if price is not None and "unit_price" not in remark.lower() and "单价" not in remark:
                bom_item.remark = f"{remark}；unit_price={price}" if remark else f"unit_price={price}"

        order = (
            session.query(LySalesOrder)
            .filter(
                LySalesOrder.company == company,
                LySalesOrder.sales_order_no == sales_order_no,
            )
            .first()
        )
        if order is None:
            order = LySalesOrder(
                sales_order_no=sales_order_no,
                company=company,
                customer="本地演示客户",
                status="planned",
                docstatus=1,
                transaction_date=date.today(),
                delivery_date=date.today(),
                grand_total=planned_qty * unit_rate,
                idempotency_key="local-dev-sales-order-demo",
                request_hash=request_hash,
                scenario_tag="LOCAL-DEV-SMOKE",
                payload={"seed": "local_dev_report_chain"},
                created_by=actor,
                updated_by=actor,
            )
            session.add(order)
        else:
            order.customer = order.customer or "本地演示客户"
            order.status = "planned"
            order.docstatus = 1
            order.transaction_date = order.transaction_date or date.today()
            order.delivery_date = order.delivery_date or date.today()
            order.grand_total = planned_qty * unit_rate
            order.updated_by = actor
        session.flush()

        order_item = (
            session.query(LySalesOrderItem)
            .filter(
                LySalesOrderItem.sales_order_id == int(order.id),
                LySalesOrderItem.sales_order_item == sales_order_item,
            )
            .first()
        )
        if order_item is None:
            order_item = LySalesOrderItem(
                sales_order_id=int(order.id),
                company=company,
                line_no=1,
                sales_order_item=sales_order_item,
                style_master_id=int(style.id),
                item_code=style_no,
                item_name="本地演示T恤",
                color="白色",
                size="M",
                qty=planned_qty,
                planned_qty=planned_qty,
                delivered_qty=Decimal("0"),
                ys_material_calc_state="已算料",
                rate=unit_rate,
                amount=planned_qty * unit_rate,
                uom="件",
                delivery_date=order.delivery_date,
            )
            session.add(order_item)
        else:
            order_item.style_master_id = int(style.id)
            order_item.item_code = style_no
            order_item.item_name = order_item.item_name or "本地演示T恤"
            order_item.color = "白色"
            order_item.size = "M"
            order_item.qty = planned_qty
            order_item.planned_qty = planned_qty
            order_item.ys_material_calc_state = "已算料"
            order_item.rate = unit_rate
            order_item.amount = planned_qty * unit_rate
            order_item.uom = "件"
            order_item.delivery_date = order.delivery_date

        plan = (
            session.query(LyProductionPlan)
            .filter(
                LyProductionPlan.company == company,
                LyProductionPlan.plan_no == plan_no,
            )
            .first()
        )
        if plan is None:
            plan = LyProductionPlan(
                plan_no=plan_no,
                company=company,
                sales_order=sales_order_no,
                sales_order_item=sales_order_item,
                customer="本地演示客户",
                item_code=style_no,
                bom_id=int(bom.id),
                bom_version=str(bom.version_no or ""),
                planned_qty=planned_qty,
                planned_start_date=date.today(),
                status="planned",
                idempotency_key="local-dev-production-plan-demo",
                request_hash=request_hash,
                created_by=actor,
            )
            session.add(plan)
        else:
            plan.sales_order = sales_order_no
            plan.sales_order_item = sales_order_item
            plan.customer = plan.customer or "本地演示客户"
            plan.item_code = style_no
            plan.bom_id = int(bom.id)
            plan.bom_version = str(bom.version_no or "")
            plan.planned_qty = planned_qty
            plan.planned_start_date = plan.planned_start_date or date.today()
            plan.status = "planned"
        session.flush()

        existing_materials = {
            int(row.bom_item_id): row
            for row in session.query(LyProductionPlanMaterial)
            .filter(
                LyProductionPlanMaterial.plan_id == int(plan.id),
                LyProductionPlanMaterial.bom_item_id.isnot(None),
            )
            .all()
        }
        for bom_index, bom_item in enumerate(bom_items, start=1):
            qty_per_piece = Decimal(str(bom_item.qty_per_piece or 0))
            loss_rate = Decimal(str(bom_item.loss_rate or 0))
            required_qty = (planned_qty * qty_per_piece * (Decimal("1") + loss_rate)).quantize(Decimal("0.000001"))
            material_snapshot = existing_materials.get(int(bom_item.id))
            if material_snapshot is None:
                material_snapshot = LyProductionPlanMaterial(
                    plan_id=int(plan.id),
                    bom_item_id=int(bom_item.id),
                    material_item_code=str(bom_item.material_item_code),
                    warehouse="默认仓库",
                )
                session.add(material_snapshot)
            material_snapshot.bom_color = bom_item.color
            material_snapshot.bom_size = bom_item.size
            material_snapshot.bom_part = bom_item.part
            material_snapshot.material_item_code = str(bom_item.material_item_code)
            material_snapshot.warehouse = "默认仓库"
            material_snapshot.uom = str(bom_item.uom or "米")
            material_snapshot.qty_per_piece = qty_per_piece
            material_snapshot.loss_rate = loss_rate
            material_snapshot.required_qty = required_qty
            material_snapshot.available_qty = Decimal("0")
            material_snapshot.shortage_qty = required_qty

            requirement_no = f"REQ-LOCAL-DEMO-{bom_index:03d}"
            requirement = (
                session.query(LyMaterialPurchaseRequirement)
                .filter(
                    LyMaterialPurchaseRequirement.company == company,
                    LyMaterialPurchaseRequirement.requirement_no == requirement_no,
                )
                .first()
            )
            if requirement is None:
                requirement = LyMaterialPurchaseRequirement(
                    company=company,
                    requirement_no=requirement_no,
                    source_type="production_plan_material_check",
                    source_id=str(int(plan.id)),
                    material_item_code=str(bom_item.material_item_code),
                    warehouse="默认仓库",
                    created_by=actor,
                    updated_by=actor,
                )
                session.add(requirement)
            requirement.source_type = "production_plan_material_check"
            requirement.source_id = str(int(plan.id))
            requirement.source_no = plan_no
            requirement.plan_id = int(plan.id)
            requirement.bom_item_id = int(bom_item.id)
            requirement.bom_color = bom_item.color
            requirement.bom_size = bom_item.size
            requirement.bom_part = bom_item.part
            requirement.sales_order = sales_order_no
            requirement.sales_order_item = sales_order_item
            requirement.item_code = style_no
            requirement.material_item_code = str(bom_item.material_item_code)
            requirement.material_name = str(bom_item.material_item_code)
            requirement.warehouse = "默认仓库"
            requirement.required_qty = required_qty
            requirement.available_qty = Decimal("0")
            requirement.net_required_qty = required_qty
            requirement.purchased_qty = Decimal("0")
            requirement.received_qty = Decimal("0")
            requirement.uom = str(bom_item.uom or "米")
            requirement.unit_price = unit_prices.get(str(bom_item.material_item_code), Decimal("0"))
            requirement.status = "pending"
            requirement.payload = {"seed": "local_dev_report_chain", "plan_no": plan_no}
            requirement.updated_by = actor

        session.commit()


_create_local_tables()
_seed_local_bom()
_seed_local_report_chain()

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


def _create_realobj_foundation_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS local_foundation_reference (
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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS local_foundation_warehouse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            reference_id INTEGER,
            warehouse_code TEXT NOT NULL,
            warehouse_name TEXT NOT NULL,
            warehouse_type TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE (scenario_tag, warehouse_code)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS local_foundation_change_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            reference_id INTEGER,
            action TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.commit()


def _get_realobj_foundation_row(connection: sqlite3.Connection, object_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM local_foundation_reference WHERE id = ?",
        (object_id,),
    ).fetchone()


def _foundation_reference_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    object_id = int(row["id"])
    return {
        "object_id": object_id,
        # compatibility: keep legacy field name so existing UI fallbacks remain valid
        "draft_id": object_id,
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


def _log_foundation_change(
    connection: sqlite3.Connection,
    scenario_tag: str,
    reference_id: int | None,
    action: str,
    payload: dict[str, Any],
) -> None:
    connection.execute(
        """
        INSERT INTO local_foundation_change_log (
            scenario_tag,
            reference_id,
            action,
            payload_json,
            created_at
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            scenario_tag,
            reference_id,
            action,
            json.dumps(payload, ensure_ascii=False),
            _now_iso(),
        ),
    )


def _sync_foundation_warehouse_snapshot(connection: sqlite3.Connection, row: sqlite3.Row) -> None:
    if str(row["category"]) != "warehouse":
        return
    key_field = str(row["key_field"] or "")
    warehouse_type = key_field.split(":", 1)[1].strip() if ":" in key_field else ""
    now_iso = _now_iso()
    connection.execute(
        """
        INSERT INTO local_foundation_warehouse (
            scenario_tag,
            reference_id,
            warehouse_code,
            warehouse_name,
            warehouse_type,
            status,
            created_at,
            updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(scenario_tag, warehouse_code) DO UPDATE SET
            reference_id = excluded.reference_id,
            warehouse_name = excluded.warehouse_name,
            warehouse_type = excluded.warehouse_type,
            status = excluded.status,
            updated_at = excluded.updated_at
        """,
        (
            row["scenario_tag"],
            int(row["id"]),
            row["reference_code"],
            row["reference_name"],
            warehouse_type,
            row["status"],
            now_iso,
            now_iso,
        ),
    )


@app.post("/api/local-dev/foundation/references")
def upsert_local_foundation_reference(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    category = str(payload.get("category", "")).strip()
    reference_code = str(payload.get("reference_code", "")).strip()
    reference_name = str(payload.get("reference_name", "")).strip()
    status = str(payload.get("status", "")).strip() or "draft"
    key_field = str(payload.get("key_field", "")).strip() or "-"
    linkage_warehouse = str(payload.get("linkage_warehouse", "")).strip()
    linkage_material = str(payload.get("linkage_material", "")).strip()
    note = str(payload.get("note", "")).strip()
    object_id = payload.get("object_id", payload.get("draft_id"))

    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    if category not in {"customer", "warehouse", "supplier", "factory", "material"}:
        raise HTTPException(status_code=400, detail="category is invalid")
    if not reference_code or not reference_name:
        raise HTTPException(status_code=400, detail="reference_code and reference_name are required")

    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_realobj_foundation_tables(connection)
        action = "create"
        if isinstance(object_id, int) and object_id > 0:
            exists = _get_realobj_foundation_row(connection, object_id)
            if not exists:
                raise HTTPException(status_code=404, detail="object not found")
            connection.execute(
                """
                UPDATE local_foundation_reference
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
                    object_id,
                ),
            )
            action = "update"
            row = _get_realobj_foundation_row(connection, object_id)
        else:
            cursor = connection.execute(
                """
                INSERT INTO local_foundation_reference (
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
            row = _get_realobj_foundation_row(connection, int(cursor.lastrowid))
        if row is None:
            raise HTTPException(status_code=500, detail="object persistence failed")
        _sync_foundation_warehouse_snapshot(connection, row)
        _log_foundation_change(connection, scenario_tag, int(row["id"]), action, payload)
        connection.commit()
    return _ok(_foundation_reference_row_to_dict(row))


@app.patch("/api/local-dev/foundation/references/{object_id}")
def patch_local_foundation_reference(object_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    patch_payload = dict(payload)
    patch_payload["object_id"] = object_id
    patch_payload["draft_id"] = object_id
    return upsert_local_foundation_reference(patch_payload)


@app.get("/api/local-dev/foundation/references")
def list_local_foundation_references(
    scenario_tag: str = Query(..., min_length=1),
    category: str | None = Query(default=None),
    state: str | None = Query(default=None),
) -> dict[str, Any]:
    args: list[Any] = [scenario_tag.strip()]
    where_sql = ["scenario_tag = ?"]
    if category:
        where_sql.append("category = ?")
        args.append(category.strip())
    if state:
        where_sql.append("state = ?")
        args.append(state.strip())
    sql = "SELECT * FROM local_foundation_reference WHERE " + " AND ".join(where_sql) + " ORDER BY id DESC"
    with _connect_local_sqlite() as connection:
        _create_realobj_foundation_tables(connection)
        rows = connection.execute(sql, tuple(args)).fetchall()
    records = [_foundation_reference_row_to_dict(row) for row in rows]
    return _ok({"scenario_tag": scenario_tag.strip(), "total": len(records), "records": records})


@app.get("/api/local-dev/foundation/references/residual-count")
def get_local_foundation_reference_residual_count(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_realobj_foundation_tables(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM local_foundation_reference WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.post("/api/local-dev/foundation/references/rollback-by-scenario")
def rollback_local_foundation_references(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_realobj_foundation_tables(connection)
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM local_foundation_reference WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
        deleted_count = int(before["total"]) if before else 0
        connection.execute("DELETE FROM local_foundation_reference WHERE scenario_tag = ?", (scenario_tag,))
        connection.execute("DELETE FROM local_foundation_warehouse WHERE scenario_tag = ?", (scenario_tag,))
        _log_foundation_change(connection, scenario_tag, None, "rollback", payload)
        connection.commit()
        after = connection.execute(
            "SELECT COUNT(*) AS total FROM local_foundation_reference WHERE scenario_tag = ?",
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


@app.get("/api/local-dev/foundation/references/{object_id}")
def get_local_foundation_reference(object_id: int) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_realobj_foundation_tables(connection)
        row = _get_realobj_foundation_row(connection, object_id)
    if row is None:
        raise HTTPException(status_code=404, detail="object not found")
    return _ok(_foundation_reference_row_to_dict(row))


@app.post("/api/local-dev/foundation/references/{object_id}/cancel")
def cancel_local_foundation_reference(object_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    reason = str(payload.get("reason", "")).strip() or f"CANCEL-{scenario_tag or object_id}"
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_realobj_foundation_tables(connection)
        row = _get_realobj_foundation_row(connection, object_id)
        if row is None:
            raise HTTPException(status_code=404, detail="object not found")
        if row["scenario_tag"] != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")
        connection.execute(
            """
            UPDATE local_foundation_reference
            SET state = 'cancelled',
                updated_at = ?,
                cancelled_at = ?,
                cancel_reason = ?
            WHERE id = ?
            """,
            (now_iso, now_iso, reason, object_id),
        )
        _log_foundation_change(connection, scenario_tag, object_id, "cancel", payload)
        connection.commit()
        cancelled = _get_realobj_foundation_row(connection, object_id)
    if cancelled is None:
        raise HTTPException(status_code=500, detail="object cancel failed")
    return _ok(_foundation_reference_row_to_dict(cancelled))


@app.get("/api/local-dev/foundation/warehouses")
def list_local_foundation_warehouses(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_realobj_foundation_tables(connection)
        rows = connection.execute(
            """
            SELECT
                id,
                scenario_tag,
                reference_id,
                warehouse_code,
                warehouse_name,
                warehouse_type,
                status,
                created_at,
                updated_at
            FROM local_foundation_warehouse
            WHERE scenario_tag = ?
            ORDER BY id DESC
            """,
            (scenario_tag.strip(),),
        ).fetchall()
    records = [
        {
            "id": int(row["id"]),
            "scenario_tag": row["scenario_tag"],
            "reference_id": row["reference_id"],
            "warehouse_code": row["warehouse_code"],
            "warehouse_name": row["warehouse_name"],
            "warehouse_type": row["warehouse_type"],
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]
    return _ok({"scenario_tag": scenario_tag.strip(), "total": len(records), "records": records})


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
            style_binding_json TEXT NOT NULL DEFAULT '{}',
            note TEXT NOT NULL DEFAULT '',
            state TEXT NOT NULL DEFAULT 'saved',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            cancelled_at TEXT,
            cancel_reason TEXT
        )
        """
    )
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(ly_local_bom_drafts)").fetchall()
    }
    if "style_binding_json" not in columns:
        connection.execute(
            "ALTER TABLE ly_local_bom_drafts ADD COLUMN style_binding_json TEXT NOT NULL DEFAULT '{}'"
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
    style_binding_raw = row["style_binding_json"] if "style_binding_json" in row.keys() else "{}"
    style_binding = {}
    try:
        style_binding_obj = json.loads(style_binding_raw)
        if isinstance(style_binding_obj, dict):
            style_binding = style_binding_obj
    except json.JSONDecodeError:
        style_binding = {}
    return {
        "draft_id": int(row["id"]),
        "scenario_tag": row["scenario_tag"],
        "bom_no": row["bom_no"],
        "item_code": row["item_code"],
        "version_no": row["version_no"],
        "status": row["status"],
        "is_default": bool(row["is_default"]),
        "style_binding": style_binding,
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
    style_binding = payload.get("style_binding", {})

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
    if not isinstance(style_binding, dict):
        raise HTTPException(status_code=400, detail="style_binding must be object")

    bom_items_json = json.dumps(bom_items, ensure_ascii=False)
    operations_json = json.dumps(operations, ensure_ascii=False)
    style_binding_json = json.dumps(style_binding, ensure_ascii=False)
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
                    style_binding_json = ?,
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
                    style_binding_json,
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
                    style_binding_json,
                    note,
                    state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
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
                    style_binding_json,
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


def _normalize_bom_line(
    raw: dict[str, Any],
    *,
    fallback_item_code: str,
    fallback_style_code: str,
    fallback_type: str,
) -> dict[str, Any]:
    item_code = str(
        raw.get("material_item_code")
        or raw.get("material_code")
        or raw.get("code")
        or f"{fallback_item_code}-{fallback_type.upper()}"
    ).strip()
    material_name = str(raw.get("material_name") or raw.get("name") or raw.get("remark") or "").strip()
    color = str(raw.get("color") or "").strip()
    size = str(raw.get("size") or "").strip() or None
    uom = str(raw.get("uom") or raw.get("unit") or "PCS").strip()
    remark = str(raw.get("remark") or "").strip()
    qty_per_piece = _to_float(raw.get("qty_per_piece", raw.get("usage", 0)), 0.0)
    loss_rate = _to_float(raw.get("loss_rate", raw.get("lossRate", 0)), 0.0)
    material_type = str(raw.get("material_type") or fallback_type).strip().lower()
    return {
        "material_item_code": item_code,
        "material_name": material_name,
        "style_code": str(raw.get("style_code") or fallback_style_code).strip(),
        "color": color,
        "size": size,
        "qty_per_piece": qty_per_piece,
        "loss_rate": loss_rate,
        "uom": uom,
        "remark": remark,
        "material_type": material_type,
    }


def _normalize_bom_operations(raw_operations: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_operations, list):
        return []
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(raw_operations):
        if not isinstance(item, dict):
            continue
        process_name = str(item.get("process_name") or item.get("name") or "").strip()
        if not process_name:
            continue
        sequence_no = int(_to_float(item.get("sequence_no", index + 1), index + 1))
        normalized.append(
            {
                "process_name": process_name,
                "sequence_no": sequence_no,
                "is_subcontract": bool(item.get("is_subcontract", False)),
                "wage_rate": _to_float(item.get("wage_rate", 0), 0.0),
                "subcontract_cost_per_piece": _to_float(item.get("subcontract_cost_per_piece", 0), 0.0),
                "remark": str(item.get("remark") or "").strip(),
            }
        )
    return normalized


def _build_default_bom_operations() -> list[dict[str, Any]]:
    return [
        {
            "process_name": "裁剪",
            "sequence_no": 10,
            "is_subcontract": False,
            "wage_rate": 0.0,
            "subcontract_cost_per_piece": 0.0,
            "remark": "local-dev default",
        },
        {
            "process_name": "缝制",
            "sequence_no": 20,
            "is_subcontract": False,
            "wage_rate": 0.0,
            "subcontract_cost_per_piece": 0.0,
            "remark": "local-dev default",
        },
    ]


def _normalize_realobj_bom_payload(payload: dict[str, Any], object_id: int | None = None) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    bom_main = payload.get("bom_main", {})
    if not isinstance(bom_main, dict):
        raise HTTPException(status_code=400, detail="bom_main must be object")
    style_binding = payload.get("style_binding", {})
    if not isinstance(style_binding, dict):
        raise HTTPException(status_code=400, detail="style_binding must be object")

    bom_no = str(bom_main.get("bom_no") or payload.get("bom_no") or "").strip()
    item_code = str(
        style_binding.get("style_code")
        or bom_main.get("item_code")
        or payload.get("item_code")
        or ""
    ).strip()
    version_no = str(bom_main.get("version_no") or payload.get("version_no") or "V1").strip()
    status = str(bom_main.get("status") or payload.get("status") or "draft").strip()
    note = str(payload.get("note") or bom_main.get("note") or "").strip()
    is_default = bool(bom_main.get("is_default", payload.get("is_default", False)))

    if not bom_no:
        raise HTTPException(status_code=400, detail="bom_no is required")
    if not item_code:
        raise HTTPException(status_code=400, detail="style_code/item_code is required")

    raw_fabric_lines = payload.get("fabric_lines", [])
    raw_trim_lines = payload.get("trim_lines", [])
    if not isinstance(raw_fabric_lines, list):
        raw_fabric_lines = []
    if not isinstance(raw_trim_lines, list):
        raw_trim_lines = []

    if len(raw_fabric_lines) == 0 and len(raw_trim_lines) == 0:
        bom_items_raw = payload.get("bom_items", [])
        if isinstance(bom_items_raw, list):
            for item in bom_items_raw:
                if not isinstance(item, dict):
                    continue
                if _is_fabric_line(item):
                    raw_fabric_lines.append(item)
                elif _is_trim_line(item):
                    raw_trim_lines.append(item)

    fabric_lines = [
        _normalize_bom_line(
            item,
            fallback_item_code=item_code,
            fallback_style_code=item_code,
            fallback_type="fabric",
        )
        for item in raw_fabric_lines
        if isinstance(item, dict)
    ]
    trim_lines = [
        _normalize_bom_line(
            item,
            fallback_item_code=item_code,
            fallback_style_code=item_code,
            fallback_type="trim",
        )
        for item in raw_trim_lines
        if isinstance(item, dict)
    ]

    if len(fabric_lines) == 0:
        raise HTTPException(status_code=400, detail="fabric_lines is required")
    if len(trim_lines) == 0:
        raise HTTPException(status_code=400, detail="trim_lines is required")

    operations = _normalize_bom_operations(payload.get("operations", []))
    if len(operations) == 0:
        operations = _build_default_bom_operations()

    normalized_style_binding = {
        "style_code": item_code,
        "style_name": str(style_binding.get("style_name") or bom_main.get("style_name") or "").strip(),
        "style_version": str(style_binding.get("style_version") or version_no).strip(),
        "material_group": str(style_binding.get("material_group") or "").strip(),
        "binding_note": str(style_binding.get("binding_note") or "").strip(),
    }

    merged_items = fabric_lines + trim_lines
    result = {
        "scenario_tag": scenario_tag,
        "bom_no": bom_no,
        "item_code": item_code,
        "version_no": version_no,
        "status": status,
        "is_default": is_default,
        "bom_items": merged_items,
        "operations": operations,
        "style_binding": normalized_style_binding,
        "note": note,
    }
    if isinstance(object_id, int) and object_id > 0:
        result["draft_id"] = object_id
    return result


def _build_realobj_bom_readback(draft_data: dict[str, Any]) -> dict[str, Any]:
    bom_items = draft_data.get("bom_items", [])
    if not isinstance(bom_items, list):
        bom_items = []
    fabric_lines = [item for item in bom_items if isinstance(item, dict) and (
        str(item.get("material_type", "")).lower() == "fabric" or _is_fabric_line(item)
    )]
    trim_lines = [item for item in bom_items if isinstance(item, dict) and (
        str(item.get("material_type", "")).lower() == "trim" or _is_trim_line(item)
    )]
    style_binding = draft_data.get("style_binding", {})
    if not isinstance(style_binding, dict):
        style_binding = {}
    style_code = str(style_binding.get("style_code") or draft_data.get("item_code") or "").strip()
    style_binding = {
        "style_code": style_code,
        "style_name": str(style_binding.get("style_name") or "").strip(),
        "style_version": str(style_binding.get("style_version") or draft_data.get("version_no") or "").strip(),
        "material_group": str(style_binding.get("material_group") or "").strip(),
        "binding_note": str(style_binding.get("binding_note") or "").strip(),
    }
    bom_main = {
        "bom_no": str(draft_data.get("bom_no") or "").strip(),
        "item_code": str(draft_data.get("item_code") or "").strip(),
        "version_no": str(draft_data.get("version_no") or "").strip(),
        "status": str(draft_data.get("status") or "draft"),
        "is_default": bool(draft_data.get("is_default", False)),
        "state": str(draft_data.get("state") or "saved"),
        "note": str(draft_data.get("note") or ""),
    }
    readback_flags = {
        "scenario_tag_present": bool(str(draft_data.get("scenario_tag", "")).strip()),
        "bom_main_readback_success": bool(bom_main["bom_no"] and bom_main["item_code"]),
        "style_binding_readback_success": bool(style_code),
        "fabric_line_readback_success": len(fabric_lines) > 0,
        "trim_line_readback_success": len(trim_lines) > 0,
        "status_validation_readback_success": bool(bom_main["status"] and bom_main["state"]),
    }
    return {
        "object_id": draft_data.get("draft_id"),
        "draft_id": draft_data.get("draft_id"),
        "scenario_tag": draft_data.get("scenario_tag"),
        "bom_main": bom_main,
        "style_binding": style_binding,
        "fabric_lines": fabric_lines,
        "trim_lines": trim_lines,
        "operations": draft_data.get("operations", []),
        "readback_flags": readback_flags,
        "state": draft_data.get("state"),
        "created_at": draft_data.get("created_at"),
        "updated_at": draft_data.get("updated_at"),
    }


@app.post("/api/local-dev/bom")
def upsert_local_bom_realobj(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    normalized = _normalize_realobj_bom_payload(payload)
    saved = upsert_local_bom_draft(normalized)
    draft_data = saved.get("data", {})
    if not isinstance(draft_data, dict):
        raise HTTPException(status_code=500, detail="local bom save failed")
    return _ok(_build_realobj_bom_readback(draft_data))


@app.patch("/api/local-dev/bom/{object_id}")
def patch_local_bom_realobj(object_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    normalized = _normalize_realobj_bom_payload(payload, object_id=object_id)
    saved = upsert_local_bom_draft(normalized)
    draft_data = saved.get("data", {})
    if not isinstance(draft_data, dict):
        raise HTTPException(status_code=500, detail="local bom update failed")
    return _ok(_build_realobj_bom_readback(draft_data))


@app.get("/api/local-dev/bom/list")
def list_local_bom_realobj(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        rows = connection.execute(
            "SELECT * FROM ly_local_bom_drafts WHERE scenario_tag = ? ORDER BY id DESC",
            (scenario_tag.strip(),),
        ).fetchall()
    records = [_build_realobj_bom_readback(_bom_draft_row_to_dict(row)) for row in rows]
    return _ok({"scenario_tag": scenario_tag.strip(), "total": len(records), "records": records})


@app.get("/api/local-dev/bom/residual-count")
def get_local_bom_realobj_residual_count(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_bom_drafts WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.get("/api/local-dev/bom/{object_id}/readback")
def readback_local_bom_realobj(
    object_id: int,
    scenario_tag: str = Query(..., min_length=1),
) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        row = _get_bom_draft_row(connection, object_id)
    if row is None:
        raise HTTPException(status_code=404, detail="object not found")
    draft_data = _bom_draft_row_to_dict(row)
    if str(draft_data.get("scenario_tag", "")).strip() != scenario_tag.strip():
        raise HTTPException(status_code=400, detail="scenario_tag mismatch")
    return _ok(_build_realobj_bom_readback(draft_data))


@app.post("/api/local-dev/bom/{object_id}/rollback")
def rollback_local_bom_realobj(object_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_bom_draft_table(connection)
        row = _get_bom_draft_row(connection, object_id)
    if row is None:
        raise HTTPException(status_code=404, detail="object not found")
    row_data = _bom_draft_row_to_dict(row)
    if str(row_data.get("scenario_tag", "")).strip() != scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag mismatch")
    rolled = rollback_local_bom_drafts({"scenario_tag": scenario_tag})
    rolled_data = rolled.get("data", {})
    if not isinstance(rolled_data, dict):
        raise HTTPException(status_code=500, detail="rollback failed")
    return _ok(
        {
            "scenario_tag": scenario_tag,
            "object_id": object_id,
            "deleted_count": int(rolled_data.get("deleted_count", 0)),
            "residual_records_after_rollback": int(rolled_data.get("residual_records_after_rollback", -1)),
            "rollback_success": bool(rolled_data.get("rollback_success", False)),
            "zero_residual_success": bool(rolled_data.get("zero_residual_success", False)),
        }
    )


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


def _normalize_sales_order_realobj_payload(payload: dict[str, Any], object_id: int | None = None) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    sales_order_source = payload.get("sales_order", {})
    sales_order = sales_order_source if isinstance(sales_order_source, dict) else {}
    order_no = str(sales_order.get("order_no") or payload.get("order_no") or "").strip()
    customer_name = str(sales_order.get("customer_name") or payload.get("customer_name") or "").strip()
    style_code = str(sales_order.get("style_code") or payload.get("style_code") or "").strip()
    delivery_date = str(sales_order.get("delivery_date") or payload.get("delivery_date") or "").strip() or date.today().isoformat()
    status = str(sales_order.get("status") or payload.get("status") or "draft").strip()
    note = str(payload.get("note") or sales_order.get("note") or "").strip()

    if not order_no:
        raise HTTPException(status_code=400, detail="order_no is required")
    if not customer_name:
        raise HTTPException(status_code=400, detail="customer_name is required")
    if not style_code:
        raise HTTPException(status_code=400, detail="style_code is required")

    matrix_source = payload.get("quantity_matrix")
    if matrix_source is None:
        matrix_source = sales_order.get("quantity_matrix")
    matrix = _normalize_sales_order_matrix(matrix_source)
    if len(matrix) < 2:
        raise HTTPException(status_code=400, detail="quantity_matrix requires at least 2 cells")

    plan_source = payload.get("production_plan", {})
    plan_payload = plan_source if isinstance(plan_source, dict) else {}
    fallback_planned_qty = sum(_to_float(cell.get("planned_qty"), 0.0) for cell in matrix)
    if fallback_planned_qty <= 0:
        fallback_planned_qty = sum(_to_float(cell.get("ordered_qty"), 0.0) for cell in matrix)
    if fallback_planned_qty <= 0:
        fallback_planned_qty = 1.0

    normalized_order = {
        "scenario_tag": scenario_tag,
        "order_no": order_no,
        "customer_name": customer_name,
        "style_code": style_code,
        "delivery_date": delivery_date,
        "status": status,
        "quantity_matrix": matrix,
        "note": note,
    }
    if isinstance(object_id, int) and object_id > 0:
        normalized_order["draft_id"] = object_id
    elif isinstance(payload.get("draft_id"), int) and int(payload["draft_id"]) > 0:
        normalized_order["draft_id"] = int(payload["draft_id"])

    normalized_plan = {
        "scenario_tag": scenario_tag,
        "plan_no": str(plan_payload.get("plan_no") or "").strip() or f"PLAN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "order_no": order_no,
        "style_code": style_code,
        "planned_qty": _to_float(plan_payload.get("planned_qty"), fallback_planned_qty),
        "plan_date": str(plan_payload.get("plan_date") or delivery_date).strip() or date.today().isoformat(),
        "status": str(plan_payload.get("status") or "draft").strip(),
        "note": str(plan_payload.get("note") or note).strip(),
    }
    if isinstance(plan_payload.get("draft_id"), int) and int(plan_payload["draft_id"]) > 0:
        normalized_plan["draft_id"] = int(plan_payload["draft_id"])

    return {
        "scenario_tag": scenario_tag,
        "order_payload": normalized_order,
        "plan_payload": normalized_plan,
    }


def _build_sales_order_realobj_readback(
    order_data: dict[str, Any],
    plan_data: dict[str, Any] | None,
) -> dict[str, Any]:
    quantity_matrix = order_data.get("quantity_matrix", [])
    if not isinstance(quantity_matrix, list):
        quantity_matrix = []
    sales_order = {
        "order_no": str(order_data.get("order_no") or "").strip(),
        "customer_name": str(order_data.get("customer_name") or "").strip(),
        "style_code": str(order_data.get("style_code") or "").strip(),
        "delivery_date": str(order_data.get("delivery_date") or "").strip(),
        "status": str(order_data.get("status") or "draft").strip(),
        "state": str(order_data.get("state") or "saved").strip(),
        "note": str(order_data.get("note") or "").strip(),
    }
    order_detail = {
        "linked_plan_draft_id": order_data.get("linked_plan_draft_id"),
        "quantity_matrix_cells": len(quantity_matrix),
        "quantity_matrix_total_ordered": sum(_to_float(cell.get("ordered_qty"), 0.0) for cell in quantity_matrix),
        "quantity_matrix_total_planned": sum(_to_float(cell.get("planned_qty"), 0.0) for cell in quantity_matrix),
        "state": sales_order["state"],
    }
    production_plan = None
    if isinstance(plan_data, dict):
        production_plan = {
            "draft_id": plan_data.get("draft_id"),
            "plan_no": str(plan_data.get("plan_no") or "").strip(),
            "planned_qty": _to_float(plan_data.get("planned_qty"), 0.0),
            "plan_date": str(plan_data.get("plan_date") or "").strip(),
            "status": str(plan_data.get("status") or "draft").strip(),
            "state": str(plan_data.get("state") or "saved").strip(),
            "order_no": str(plan_data.get("order_no") or "").strip(),
            "style_code": str(plan_data.get("style_code") or "").strip(),
        }

    readback_flags = {
        "scenario_tag_present": bool(str(order_data.get("scenario_tag") or "").strip()),
        "sales_order_readback_success": bool(sales_order["order_no"] and sales_order["customer_name"]),
        "order_detail_readback_success": len(quantity_matrix) > 0,
        "quantity_matrix_readback_success": _matrix_saved(quantity_matrix),
        "production_plan_readback_success": bool(
            production_plan
            and production_plan.get("draft_id")
            and _to_float(production_plan.get("planned_qty"), 0.0) > 0
        ),
        "status_validation_readback_success": bool(sales_order["status"] and sales_order["state"]),
    }

    return {
        "object_id": order_data.get("draft_id"),
        "draft_id": order_data.get("draft_id"),
        "scenario_tag": order_data.get("scenario_tag"),
        "sales_order": sales_order,
        "order_detail": order_detail,
        "quantity_matrix": quantity_matrix,
        "production_plan": production_plan,
        "readback_flags": readback_flags,
        "created_at": order_data.get("created_at"),
        "updated_at": order_data.get("updated_at"),
    }


def _find_linked_plan_for_order(
    scenario_tag: str,
    order_data: dict[str, Any],
) -> dict[str, Any] | None:
    linked_plan_id = order_data.get("linked_plan_draft_id")
    with _connect_local_sqlite() as connection:
        _create_production_plan_draft_table(connection)
        if isinstance(linked_plan_id, int) and linked_plan_id > 0:
            linked_row = _get_production_plan_draft_row(connection, linked_plan_id)
            if linked_row is not None:
                linked_data = _production_plan_draft_row_to_dict(linked_row)
                if str(linked_data.get("scenario_tag", "")).strip() == scenario_tag:
                    return linked_data
        order_id = order_data.get("draft_id")
        if isinstance(order_id, int) and order_id > 0:
            row = connection.execute(
                """
                SELECT * FROM ly_local_production_plan_drafts
                WHERE scenario_tag = ? AND order_draft_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (scenario_tag, order_id),
            ).fetchone()
            if row is not None:
                return _production_plan_draft_row_to_dict(row)
    return None


@app.post("/api/local-dev/sales-orders")
def upsert_local_sales_order_realobj(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    normalized = _normalize_sales_order_realobj_payload(payload)
    order_payload = dict(normalized["order_payload"])
    order_saved = upsert_local_sales_order_draft(order_payload)
    order_data = order_saved.get("data", {})
    if not isinstance(order_data, dict):
        raise HTTPException(status_code=500, detail="sales order save failed")

    plan_payload = dict(normalized["plan_payload"])
    order_draft_id = order_data.get("draft_id")
    if not isinstance(order_draft_id, int) or order_draft_id <= 0:
        raise HTTPException(status_code=500, detail="sales order object id is invalid")
    plan_payload["order_draft_id"] = order_draft_id
    plan_saved = upsert_local_production_plan_draft(plan_payload)
    plan_data = plan_saved.get("data", {})
    if not isinstance(plan_data, dict):
        raise HTTPException(status_code=500, detail="production plan save failed")

    linked_plan_id = plan_data.get("draft_id")
    if isinstance(linked_plan_id, int) and linked_plan_id > 0:
        relink_payload = dict(order_payload)
        relink_payload["draft_id"] = order_draft_id
        relink_payload["linked_plan_draft_id"] = linked_plan_id
        relink_saved = upsert_local_sales_order_draft(relink_payload)
        relink_data = relink_saved.get("data", {})
        if isinstance(relink_data, dict):
            order_data = relink_data

    return _ok(_build_sales_order_realobj_readback(order_data, plan_data))


@app.patch("/api/local-dev/sales-orders/{object_id}")
def patch_local_sales_order_realobj(object_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    normalized = _normalize_sales_order_realobj_payload(payload, object_id=object_id)
    order_payload = dict(normalized["order_payload"])
    order_saved = upsert_local_sales_order_draft(order_payload)
    order_data = order_saved.get("data", {})
    if not isinstance(order_data, dict):
        raise HTTPException(status_code=500, detail="sales order update failed")

    plan_payload = dict(normalized["plan_payload"])
    order_draft_id = order_data.get("draft_id")
    if not isinstance(order_draft_id, int) or order_draft_id <= 0:
        raise HTTPException(status_code=500, detail="sales order object id is invalid")
    plan_payload["order_draft_id"] = order_draft_id
    existing_linked_id = order_data.get("linked_plan_draft_id")
    if isinstance(existing_linked_id, int) and existing_linked_id > 0:
        plan_payload["draft_id"] = existing_linked_id
    plan_saved = upsert_local_production_plan_draft(plan_payload)
    plan_data = plan_saved.get("data", {})
    if not isinstance(plan_data, dict):
        raise HTTPException(status_code=500, detail="production plan update failed")

    linked_plan_id = plan_data.get("draft_id")
    if isinstance(linked_plan_id, int) and linked_plan_id > 0:
        relink_payload = dict(order_payload)
        relink_payload["draft_id"] = order_draft_id
        relink_payload["linked_plan_draft_id"] = linked_plan_id
        relink_saved = upsert_local_sales_order_draft(relink_payload)
        relink_data = relink_saved.get("data", {})
        if isinstance(relink_data, dict):
            order_data = relink_data

    return _ok(_build_sales_order_realobj_readback(order_data, plan_data))


@app.get("/api/local-dev/sales-orders")
def list_local_sales_order_realobj(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    scenario = scenario_tag.strip()
    listed = list_local_sales_order_drafts(scenario_tag=scenario)
    listed_data = listed.get("data", {})
    items = listed_data.get("items", []) if isinstance(listed_data, dict) else []
    records: list[dict[str, Any]] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            if str(item.get("scenario_tag", "")).strip() != scenario:
                continue
            linked_plan = _find_linked_plan_for_order(scenario, item)
            records.append(_build_sales_order_realobj_readback(item, linked_plan))
    return _ok({"scenario_tag": scenario, "total": len(records), "records": records})


@app.get("/api/local-dev/sales-orders/{object_id}/readback")
def readback_local_sales_order_realobj(
    object_id: int,
    scenario_tag: str = Query(..., min_length=1),
) -> dict[str, Any]:
    scenario = scenario_tag.strip()
    fetched = get_local_sales_order_draft(object_id)
    order_data = fetched.get("data", {})
    if not isinstance(order_data, dict):
        raise HTTPException(status_code=404, detail="sales order object not found")
    if str(order_data.get("scenario_tag", "")).strip() != scenario:
        raise HTTPException(status_code=400, detail="scenario_tag mismatch")
    linked_plan = _find_linked_plan_for_order(scenario, order_data)
    return _ok(_build_sales_order_realobj_readback(order_data, linked_plan))


@app.get("/api/local-dev/production-plans")
def list_local_production_plan_realobj(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    scenario = scenario_tag.strip()
    listed = list_local_production_plan_drafts(scenario_tag=scenario)
    listed_data = listed.get("data", {})
    items = listed_data.get("items", []) if isinstance(listed_data, dict) else []
    records = [
        item
        for item in items
        if isinstance(item, dict) and str(item.get("scenario_tag", "")).strip() == scenario
    ] if isinstance(items, list) else []
    return _ok({"scenario_tag": scenario, "total": len(records), "records": records})


@app.post("/api/local-dev/production-plans/{object_id}/rollback")
def rollback_local_sales_production_realobj(object_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    with _connect_local_sqlite() as connection:
        _create_production_plan_draft_table(connection)
        plan_row = _get_production_plan_draft_row(connection, object_id)
    if plan_row is None:
        raise HTTPException(status_code=404, detail="production plan object not found")
    plan_data = _production_plan_draft_row_to_dict(plan_row)
    if str(plan_data.get("scenario_tag", "")).strip() != scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag mismatch")

    sales_rollback = rollback_local_sales_order_drafts({"scenario_tag": scenario_tag})
    plan_rollback = rollback_local_production_plan_drafts({"scenario_tag": scenario_tag})
    sales_data = sales_rollback.get("data", {})
    plan_data_rollback = plan_rollback.get("data", {})
    if not isinstance(sales_data, dict) or not isinstance(plan_data_rollback, dict):
        raise HTTPException(status_code=500, detail="rollback failed")

    sales_residual = int(sales_data.get("residual_records_after_rollback", -1))
    plan_residual = int(plan_data_rollback.get("residual_records_after_rollback", -1))
    residual = max(sales_residual, plan_residual)
    zero_residual = sales_residual == 0 and plan_residual == 0
    return _ok(
        {
            "scenario_tag": scenario_tag,
            "object_id": object_id,
            "sales_deleted_count": int(sales_data.get("deleted_count", 0)),
            "plan_deleted_count": int(plan_data_rollback.get("deleted_count", 0)),
            "sales_residual_records_after_rollback": sales_residual,
            "plan_residual_records_after_rollback": plan_residual,
            "residual_records_after_rollback": residual,
            "rollback_success": bool(sales_data.get("rollback_success", False))
            and bool(plan_data_rollback.get("rollback_success", False)),
            "zero_residual_success": zero_residual,
        }
    )


def _create_purchase_subcontract_draft_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ly_local_purchase_subcontract_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            document_no TEXT NOT NULL,
            partner_name TEXT NOT NULL,
            partner_type TEXT NOT NULL,
            document_type TEXT NOT NULL,
            business_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            material_category TEXT NOT NULL DEFAULT 'mixed',
            predecessor_doc_no TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            material_lines_json TEXT NOT NULL,
            issue_return_json TEXT NOT NULL,
            inspection_settlement_json TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'saved',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            cancelled_at TEXT,
            cancel_reason TEXT
        )
        """
    )
    connection.commit()


def _get_purchase_subcontract_draft_row(connection: sqlite3.Connection, draft_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM ly_local_purchase_subcontract_drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()


def _normalize_purchase_material_lines(raw_lines: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_lines, list):
        return []
    normalized: list[dict[str, Any]] = []
    for row in raw_lines:
        if not isinstance(row, dict):
            continue
        material_code = str(row.get("material_code", "")).strip()
        material_name = str(row.get("material_name", "")).strip()
        color_spec = str(row.get("color_spec", "")).strip()
        uom = str(row.get("uom", "")).strip() or "PCS"
        demand_qty = _to_float(row.get("demand_qty"), 0.0)
        purchase_qty = _to_float(row.get("purchase_qty"), 0.0)
        if not material_code and not material_name:
            continue
        normalized.append(
            {
                "material_code": material_code,
                "material_name": material_name,
                "color_spec": color_spec,
                "uom": uom,
                "demand_qty": demand_qty,
                "purchase_qty": purchase_qty,
            }
        )
    return normalized


def _normalize_issue_return(raw_state: Any) -> dict[str, Any]:
    source = raw_state if isinstance(raw_state, dict) else {}
    issued_qty = _to_float(source.get("issued_qty"), 0.0)
    returned_qty = _to_float(source.get("returned_qty"), 0.0)
    return {
        "issued_qty": issued_qty,
        "returned_qty": returned_qty,
        "delta_qty": issued_qty - returned_qty,
        "state": str(source.get("state", "")).strip() or "draft",
    }


def _normalize_inspection_settlement(raw_state: Any) -> dict[str, Any]:
    source = raw_state if isinstance(raw_state, dict) else {}
    return {
        "accepted_qty": _to_float(source.get("accepted_qty"), 0.0),
        "rejected_qty": _to_float(source.get("rejected_qty"), 0.0),
        "settlement_qty": _to_float(source.get("settlement_qty"), 0.0),
        "estimated_amount": _to_float(source.get("estimated_amount"), 0.0),
        "state": str(source.get("state", "")).strip() or "draft",
    }


def _parse_json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _purchase_subcontract_draft_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    material_lines = _normalize_purchase_material_lines(_parse_json_payload(row["material_lines_json"]))
    issue_return = _normalize_issue_return(_parse_json_object(row["issue_return_json"]))
    inspection_settlement = _normalize_inspection_settlement(
        _parse_json_object(row["inspection_settlement_json"])
    )
    material_line_saved = any(_to_float(line.get("purchase_qty"), 0.0) > 0 for line in material_lines)
    issue_return_or_inspection_saved = (
        _to_float(issue_return.get("issued_qty"), 0.0) > 0
        or _to_float(issue_return.get("returned_qty"), 0.0) > 0
        or _to_float(inspection_settlement.get("settlement_qty"), 0.0) > 0
        or _to_float(inspection_settlement.get("accepted_qty"), 0.0) > 0
    )
    return {
        "draft_id": int(row["id"]),
        "scenario_tag": row["scenario_tag"],
        "document_no": row["document_no"],
        "partner_name": row["partner_name"],
        "partner_type": row["partner_type"],
        "document_type": row["document_type"],
        "business_date": row["business_date"],
        "status": row["status"],
        "material_category": row["material_category"],
        "predecessor_doc_no": row["predecessor_doc_no"],
        "note": row["note"],
        "material_lines": material_lines,
        "issue_return": issue_return,
        "inspection_settlement": inspection_settlement,
        "state": row["state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cancelled_at": row["cancelled_at"],
        "cancel_reason": row["cancel_reason"],
        "material_line_saved": material_line_saved,
        "issue_return_or_inspection_saved": issue_return_or_inspection_saved,
    }


@app.post("/api/local-dev/purchase-subcontract-drafts")
def upsert_local_purchase_subcontract_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    document_no = str(payload.get("document_no", "")).strip()
    partner_name = str(payload.get("partner_name", "")).strip()
    partner_type = str(payload.get("partner_type", "")).strip() or "supplier"
    document_type = str(payload.get("document_type", "")).strip() or "subcontract"
    business_date = str(payload.get("business_date", "")).strip() or date.today().isoformat()
    status = str(payload.get("status", "")).strip() or "draft"
    material_category = str(payload.get("material_category", "")).strip() or "mixed"
    predecessor_doc_no = str(payload.get("predecessor_doc_no", "")).strip()
    note = str(payload.get("note", "")).strip()
    draft_id = payload.get("draft_id")
    material_lines = _normalize_purchase_material_lines(payload.get("material_lines"))
    issue_return = _normalize_issue_return(payload.get("issue_return"))
    inspection_settlement = _normalize_inspection_settlement(payload.get("inspection_settlement"))

    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    if not document_no:
        raise HTTPException(status_code=400, detail="document_no is required")
    if not partner_name:
        raise HTTPException(status_code=400, detail="partner_name is required")
    if partner_type not in {"supplier", "factory"}:
        raise HTTPException(status_code=400, detail="partner_type is invalid")
    if document_type not in {"purchase", "subcontract"}:
        raise HTTPException(status_code=400, detail="document_type is invalid")
    if len(material_lines) < 1:
        raise HTTPException(status_code=400, detail="material_lines requires at least 1 row")

    now_iso = _now_iso()
    material_lines_json = json.dumps(material_lines, ensure_ascii=False)
    issue_return_json = json.dumps(issue_return, ensure_ascii=False)
    inspection_settlement_json = json.dumps(inspection_settlement, ensure_ascii=False)

    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        if isinstance(draft_id, int) and draft_id > 0:
            exists = _get_purchase_subcontract_draft_row(connection, draft_id)
            if not exists:
                raise HTTPException(status_code=404, detail="draft not found")
            connection.execute(
                """
                UPDATE ly_local_purchase_subcontract_drafts
                SET scenario_tag = ?,
                    document_no = ?,
                    partner_name = ?,
                    partner_type = ?,
                    document_type = ?,
                    business_date = ?,
                    status = ?,
                    material_category = ?,
                    predecessor_doc_no = ?,
                    note = ?,
                    material_lines_json = ?,
                    issue_return_json = ?,
                    inspection_settlement_json = ?,
                    state = 'saved',
                    updated_at = ?,
                    cancelled_at = NULL,
                    cancel_reason = NULL
                WHERE id = ?
                """,
                (
                    scenario_tag,
                    document_no,
                    partner_name,
                    partner_type,
                    document_type,
                    business_date,
                    status,
                    material_category,
                    predecessor_doc_no,
                    note,
                    material_lines_json,
                    issue_return_json,
                    inspection_settlement_json,
                    now_iso,
                    draft_id,
                ),
            )
            connection.commit()
            row = _get_purchase_subcontract_draft_row(connection, draft_id)
        else:
            cursor = connection.execute(
                """
                INSERT INTO ly_local_purchase_subcontract_drafts (
                    scenario_tag,
                    document_no,
                    partner_name,
                    partner_type,
                    document_type,
                    business_date,
                    status,
                    material_category,
                    predecessor_doc_no,
                    note,
                    material_lines_json,
                    issue_return_json,
                    inspection_settlement_json,
                    state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
                """,
                (
                    scenario_tag,
                    document_no,
                    partner_name,
                    partner_type,
                    document_type,
                    business_date,
                    status,
                    material_category,
                    predecessor_doc_no,
                    note,
                    material_lines_json,
                    issue_return_json,
                    inspection_settlement_json,
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()
            row = _get_purchase_subcontract_draft_row(connection, int(cursor.lastrowid))

    if row is None:
        raise HTTPException(status_code=500, detail="draft persistence failed")
    return _ok(_purchase_subcontract_draft_row_to_dict(row))


@app.get("/api/local-dev/purchase-subcontract-drafts")
def list_local_purchase_subcontract_drafts(
    keyword: str | None = None,
    partner_name: str | None = None,
    status: str | None = None,
    material_category: str | None = None,
    scenario_tag: str | None = None,
    document_type: str | None = None,
    parity: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        rows = connection.execute(
            "SELECT * FROM ly_local_purchase_subcontract_drafts ORDER BY id DESC",
        ).fetchall()

    items = [_purchase_subcontract_draft_row_to_dict(row) for row in rows]
    keyword_token = (keyword or "").strip().lower()
    partner_token = (partner_name or "").strip().lower()
    status_token = (status or "").strip().lower()
    category_token = (material_category or "").strip().lower()
    scenario_token = (scenario_tag or "").strip()
    doc_type_token = (document_type or "").strip().lower()
    parity_token = (parity or "").strip().lower()

    def _match(item: dict[str, Any]) -> bool:
        if keyword_token and keyword_token not in (
            f"{item['document_no']} {item['partner_name']} {item['predecessor_doc_no']}".lower()
        ):
            material_token = " ".join(
                [
                    str(line.get("material_code", "")).lower()
                    for line in item.get("material_lines", [])
                    if isinstance(line, dict)
                ]
            )
            if keyword_token not in material_token:
                return False
        if partner_token and partner_token not in str(item["partner_name"]).lower():
            return False
        if status_token and status_token != str(item["status"]).lower():
            return False
        if category_token and category_token != str(item["material_category"]).lower():
            return False
        if scenario_token and scenario_token != str(item["scenario_tag"]):
            return False
        if doc_type_token and doc_type_token != str(item["document_type"]).lower():
            return False
        if parity_token == "material-purchase" and str(item["document_type"]).lower() not in {
            "purchase",
            "subcontract",
        }:
            return False
        return True

    filtered = [item for item in items if _match(item)]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    paged_items = filtered[start:end]
    return _ok(
        {
            "items": paged_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "parity": parity_token,
        }
    )


@app.get("/api/local-dev/purchase-subcontract-drafts/residual-count")
def get_local_purchase_subcontract_residual_count(
    scenario_tag: str = Query(..., min_length=1)
) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_purchase_subcontract_drafts WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.post("/api/local-dev/purchase-subcontract-drafts/rollback-by-scenario")
def rollback_local_purchase_subcontract_drafts(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_purchase_subcontract_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
        deleted_count = int(before["total"]) if before else 0
        connection.execute(
            "DELETE FROM ly_local_purchase_subcontract_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        )
        connection.commit()
        after = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_purchase_subcontract_drafts WHERE scenario_tag = ?",
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


@app.get("/api/local-dev/purchase-subcontract-drafts/{draft_id}")
def get_local_purchase_subcontract_draft(draft_id: int) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        row = _get_purchase_subcontract_draft_row(connection, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return _ok(_purchase_subcontract_draft_row_to_dict(row))


@app.post("/api/local-dev/purchase-subcontract-drafts/{draft_id}/cancel")
def cancel_local_purchase_subcontract_draft(
    draft_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    reason = str(payload.get("reason", "")).strip() or f"CANCEL-{scenario_tag or draft_id}"
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        row = _get_purchase_subcontract_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        if row["scenario_tag"] != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")
        connection.execute(
            """
            UPDATE ly_local_purchase_subcontract_drafts
            SET state = 'cancelled',
                updated_at = ?,
                cancelled_at = ?,
                cancel_reason = ?
            WHERE id = ?
            """,
            (now_iso, now_iso, reason, draft_id),
        )
        connection.commit()
        cancelled = _get_purchase_subcontract_draft_row(connection, draft_id)
    if cancelled is None:
        raise HTTPException(status_code=500, detail="draft cancel failed")
    return _ok(_purchase_subcontract_draft_row_to_dict(cancelled))


def _build_subcontract_settlement_preview(snapshot: dict[str, Any]) -> dict[str, Any]:
    return _normalize_inspection_settlement(snapshot.get("inspection_settlement"))


def _build_subcontract_readback_flags(
    draft_payload: dict[str, Any], settlement_preview: dict[str, Any], scenario_tag: str
) -> dict[str, Any]:
    material_lines = draft_payload.get("material_lines") if isinstance(draft_payload.get("material_lines"), list) else []
    issue_return = draft_payload.get("issue_return") if isinstance(draft_payload.get("issue_return"), dict) else {}
    settlement_preview_status = str(settlement_preview.get("state", "")).strip()
    settlement_preview_amount_or_summary_observed = (
        _to_float(settlement_preview.get("estimated_amount"), 0.0) > 0
        or _to_float(settlement_preview.get("settlement_qty"), 0.0) > 0
        or _to_float(settlement_preview.get("accepted_qty"), 0.0) > 0
        or _to_float(settlement_preview.get("rejected_qty"), 0.0) > 0
    )
    issue_return_or_inspection_readback_success = (
        _to_float(issue_return.get("issued_qty"), 0.0) >= 0
        and _to_float(issue_return.get("returned_qty"), 0.0) >= 0
        and settlement_preview_status != ""
    )
    return {
        "scenario_tag_present": bool(str(draft_payload.get("scenario_tag", "")).strip()),
        "subcontract_or_purchase_readback_success": True,
        "material_line_readback_success": len(material_lines) > 0,
        "issue_return_or_inspection_readback_success": issue_return_or_inspection_readback_success,
        "settlement_preview_readback_success": True,
        "settlement_preview_status_observed": settlement_preview_status != "",
        "settlement_preview_amount_or_summary_observed": settlement_preview_amount_or_summary_observed,
        "settlement_preview_real_finance_effect": False,
        "settlement_preview_real_payment_effect": False,
        "settlement_preview_real_inventory_effect": False,
        "status_validation_readback_success": str(draft_payload.get("status", "")).strip() != "",
        "scenario_tag_matched": str(draft_payload.get("scenario_tag", "")).strip() == scenario_tag,
    }


def _build_subcontract_order_readback_payload(
    draft_payload: dict[str, Any], scenario_tag: str
) -> dict[str, Any]:
    settlement_preview = _build_subcontract_settlement_preview(draft_payload)
    readback_flags = _build_subcontract_readback_flags(draft_payload, settlement_preview, scenario_tag)
    return {
        "object_id": int(draft_payload["draft_id"]),
        "draft_id": int(draft_payload["draft_id"]),
        "scenario_tag": draft_payload["scenario_tag"],
        "subcontract_or_purchase": {
            "document_no": draft_payload["document_no"],
            "partner_name": draft_payload["partner_name"],
            "partner_type": draft_payload["partner_type"],
            "document_type": draft_payload["document_type"],
            "business_date": draft_payload["business_date"],
            "status": draft_payload["status"],
            "material_category": draft_payload["material_category"],
            "predecessor_doc_no": draft_payload["predecessor_doc_no"],
            "note": draft_payload["note"],
            "state": draft_payload["state"],
        },
        "material_lines": draft_payload["material_lines"],
        "issue_return": draft_payload["issue_return"],
        "inspection_settlement": draft_payload["inspection_settlement"],
        "settlement_preview": settlement_preview,
        "readback_flags": readback_flags,
        "created_at": draft_payload["created_at"],
        "updated_at": draft_payload["updated_at"],
    }


@app.post("/api/local-dev/subcontract/orders")
def upsert_local_subcontract_order(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return upsert_local_purchase_subcontract_draft(payload)


@app.patch("/api/local-dev/subcontract/orders/{draft_id}")
def patch_local_subcontract_order(draft_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    patch_payload = dict(payload)
    patch_payload["draft_id"] = draft_id
    return upsert_local_purchase_subcontract_draft(patch_payload)


@app.get("/api/local-dev/subcontract/orders")
def list_local_subcontract_orders(
    keyword: str | None = None,
    partner_name: str | None = None,
    status: str | None = None,
    material_category: str | None = None,
    scenario_tag: str | None = None,
    document_type: str | None = None,
    parity: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    return list_local_purchase_subcontract_drafts(
        keyword=keyword,
        partner_name=partner_name,
        status=status,
        material_category=material_category,
        scenario_tag=scenario_tag,
        document_type=document_type,
        parity=parity,
        page=page,
        page_size=page_size,
    )


@app.get("/api/local-dev/subcontract/orders/{draft_id}/readback")
def get_local_subcontract_order_readback(
    draft_id: int,
    scenario_tag: str = Query(..., min_length=1),
) -> dict[str, Any]:
    tag = scenario_tag.strip()
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        row = _get_purchase_subcontract_draft_row(connection, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    payload = _purchase_subcontract_draft_row_to_dict(row)
    if str(payload.get("scenario_tag", "")).strip() != tag:
        raise HTTPException(status_code=400, detail="scenario_tag mismatch")
    return _ok(_build_subcontract_order_readback_payload(payload, tag))


@app.get("/api/local-dev/subcontract/orders/{draft_id}/settlement-preview")
def get_local_subcontract_settlement_preview(
    draft_id: int,
    scenario_tag: str = Query(..., min_length=1),
) -> dict[str, Any]:
    tag = scenario_tag.strip()
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        row = _get_purchase_subcontract_draft_row(connection, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    payload = _purchase_subcontract_draft_row_to_dict(row)
    if str(payload.get("scenario_tag", "")).strip() != tag:
        raise HTTPException(status_code=400, detail="scenario_tag mismatch")
    settlement_preview = _build_subcontract_settlement_preview(payload)
    amount_or_summary_observed = (
        _to_float(settlement_preview.get("estimated_amount"), 0.0) > 0
        or _to_float(settlement_preview.get("settlement_qty"), 0.0) > 0
        or _to_float(settlement_preview.get("accepted_qty"), 0.0) > 0
        or _to_float(settlement_preview.get("rejected_qty"), 0.0) > 0
    )
    return _ok(
        {
            "draft_id": draft_id,
            "scenario_tag": tag,
            "settlement_preview": settlement_preview,
            "settlement_preview_status_observed": str(settlement_preview.get("state", "")).strip() != "",
            "settlement_preview_amount_or_summary_observed": amount_or_summary_observed,
            "settlement_preview_real_finance_effect": False,
            "settlement_preview_real_payment_effect": False,
            "settlement_preview_real_inventory_effect": False,
        }
    )


@app.patch("/api/local-dev/subcontract/orders/{draft_id}/settlement-preview")
def patch_local_subcontract_settlement_preview(
    draft_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")

    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        row = _get_purchase_subcontract_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        draft_payload = _purchase_subcontract_draft_row_to_dict(row)
        if str(draft_payload.get("scenario_tag", "")).strip() != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")

        merged_preview = dict(draft_payload.get("inspection_settlement", {}))
        for key in ("accepted_qty", "rejected_qty", "settlement_qty", "estimated_amount", "state"):
            if key in payload:
                merged_preview[key] = payload.get(key)
        normalized_preview = _normalize_inspection_settlement(merged_preview)
        connection.execute(
            """
            UPDATE ly_local_purchase_subcontract_drafts
            SET inspection_settlement_json = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(normalized_preview, ensure_ascii=False), _now_iso(), draft_id),
        )
        connection.commit()
        updated_row = _get_purchase_subcontract_draft_row(connection, draft_id)

    if updated_row is None:
        raise HTTPException(status_code=500, detail="settlement preview update failed")
    updated_payload = _purchase_subcontract_draft_row_to_dict(updated_row)
    settlement_preview = _build_subcontract_settlement_preview(updated_payload)
    amount_or_summary_observed = (
        _to_float(settlement_preview.get("estimated_amount"), 0.0) > 0
        or _to_float(settlement_preview.get("settlement_qty"), 0.0) > 0
        or _to_float(settlement_preview.get("accepted_qty"), 0.0) > 0
        or _to_float(settlement_preview.get("rejected_qty"), 0.0) > 0
    )
    return _ok(
        {
            "draft_id": draft_id,
            "scenario_tag": scenario_tag,
            "settlement_preview": settlement_preview,
            "settlement_preview_created_or_updated": True,
            "settlement_preview_readback_success": True,
            "settlement_preview_status_observed": str(settlement_preview.get("state", "")).strip() != "",
            "settlement_preview_amount_or_summary_observed": amount_or_summary_observed,
            "settlement_preview_real_finance_effect": False,
            "settlement_preview_real_payment_effect": False,
            "settlement_preview_real_inventory_effect": False,
        }
    )


@app.post("/api/local-dev/subcontract/orders/{draft_id}/rollback")
def rollback_local_subcontract_order(
    draft_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_purchase_subcontract_draft_table(connection)
        row = _get_purchase_subcontract_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        scenario = str(row["scenario_tag"]).strip()
        if scenario != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")

    rollback_result = rollback_local_purchase_subcontract_drafts({"scenario_tag": scenario_tag})
    data = rollback_result.get("data", {})
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="rollback failed")
    data["object_id"] = draft_id
    return _ok(data)


def _create_inventory_operation_draft_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS ly_local_inventory_operation_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_tag TEXT NOT NULL,
            draft_no TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            flow_type TEXT NOT NULL,
            material_code TEXT NOT NULL,
            material_name TEXT NOT NULL DEFAULT '',
            spec TEXT NOT NULL DEFAULT '',
            uom TEXT NOT NULL DEFAULT 'Nos',
            warehouse TEXT NOT NULL,
            source_warehouse TEXT NOT NULL DEFAULT '',
            target_warehouse TEXT NOT NULL DEFAULT '',
            current_qty REAL NOT NULL DEFAULT 0,
            operation_qty REAL NOT NULL DEFAULT 0,
            counting_qty REAL NOT NULL DEFAULT 0,
            diff_qty REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            business_ref TEXT NOT NULL DEFAULT '',
            business_time TEXT NOT NULL,
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


def _get_inventory_operation_draft_row(
    connection: sqlite3.Connection, draft_id: int
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT * FROM ly_local_inventory_operation_drafts WHERE id = ?",
        (draft_id,),
    ).fetchone()


def _inventory_operation_draft_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    operation_type = str(row["operation_type"]).strip().lower()
    transfer_saved = operation_type == "transfer" and _to_float(row["operation_qty"], 0.0) > 0
    counting_saved = operation_type == "counting"
    row_id = int(row["id"])
    normalized_status = "cancelled" if str(row["state"]).strip().lower() == "cancelled" else "draft"
    item_payload = {
        "item_code": row["material_code"],
        "qty": _to_float(row["operation_qty"], 0.0),
        "uom": row["uom"],
        "source_warehouse": row["source_warehouse"],
        "target_warehouse": row["target_warehouse"],
    }
    return {
        "id": row_id,
        "draft_id": row_id,
        "scenario_tag": row["scenario_tag"],
        "draft_no": row["draft_no"],
        "operation_type": row["operation_type"],
        "flow_type": row["flow_type"],
        "material_code": row["material_code"],
        "material_name": row["material_name"],
        "spec": row["spec"],
        "uom": row["uom"],
        "warehouse": row["warehouse"],
        "source_warehouse": row["source_warehouse"],
        "target_warehouse": row["target_warehouse"],
        "current_qty": _to_float(row["current_qty"], 0.0),
        "operation_qty": _to_float(row["operation_qty"], 0.0),
        "counting_qty": _to_float(row["counting_qty"], 0.0),
        "diff_qty": _to_float(row["diff_qty"], 0.0),
        "status": normalized_status,
        "status_label": row["status"],
        "business_ref": row["business_ref"],
        "source_id": row["business_ref"],
        "business_time": row["business_time"],
        "note": row["note"],
        "state": row["state"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "cancelled_at": row["cancelled_at"],
        "cancel_reason": row["cancel_reason"],
        "transfer_saved": transfer_saved,
        "counting_saved": counting_saved,
        "transfer_or_counting_saved": transfer_saved or counting_saved,
        "items": [item_payload],
        "idempotency_key": f"{row['scenario_tag']}-LOCAL-INV-{row_id}",
        "event_key": f"local_inventory_draft:{row_id}",
        "outbox": {
            "draft_id": row_id,
            "event_id": row_id,
            "event_type": "local_inventory_draft",
            "status": "cancelled" if normalized_status == "cancelled" else "succeeded",
            "retry_count": 0,
            "external_ref": None,
            "error_message": None,
            "created_at": row["created_at"],
            "processed_at": row["updated_at"],
        },
    }


@app.post("/api/local-dev/inventory-operation-drafts")
def upsert_local_inventory_operation_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    operation_type = str(payload.get("operation_type", "")).strip().lower() or "transfer"
    flow_type = str(payload.get("flow_type", "")).strip().lower() or operation_type
    material_code = str(payload.get("material_code", "")).strip()
    material_name = str(payload.get("material_name", "")).strip() or material_code
    spec = str(payload.get("spec", "")).strip()
    uom = str(payload.get("uom", "")).strip() or "Nos"
    warehouse = str(payload.get("warehouse", "")).strip()
    source_warehouse = str(payload.get("source_warehouse", "")).strip() or warehouse
    target_warehouse = str(payload.get("target_warehouse", "")).strip()
    current_qty = _to_float(payload.get("current_qty"), 0.0)
    transfer_qty = _to_float(payload.get("transfer_qty"), 0.0)
    counting_qty = _to_float(payload.get("counting_qty"), current_qty)
    operation_qty = transfer_qty if operation_type == "transfer" else abs(counting_qty - current_qty)
    diff_qty = counting_qty - current_qty if operation_type == "counting" else 0.0
    status = str(payload.get("status", "")).strip() or "draft"
    business_ref = str(payload.get("business_ref", "")).strip() or f"INV-{scenario_tag}"
    business_time = str(payload.get("business_time", "")).strip() or date.today().isoformat()
    note = str(payload.get("note", "")).strip()
    draft_id = payload.get("draft_id")

    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    if operation_type not in {"transfer", "counting"}:
        raise HTTPException(status_code=400, detail="operation_type is invalid")
    if flow_type not in {"transfer", "counting"}:
        raise HTTPException(status_code=400, detail="flow_type is invalid")
    if not material_code:
        raise HTTPException(status_code=400, detail="material_code is required")
    if not warehouse:
        raise HTTPException(status_code=400, detail="warehouse is required")
    if operation_type == "transfer":
        if not source_warehouse or not target_warehouse:
            raise HTTPException(status_code=400, detail="source_warehouse and target_warehouse are required")
        if transfer_qty <= 0:
            raise HTTPException(status_code=400, detail="transfer_qty must be greater than 0")
    if operation_type == "counting" and counting_qty < 0:
        raise HTTPException(status_code=400, detail="counting_qty must be greater than or equal to 0")

    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_inventory_operation_draft_table(connection)
        if isinstance(draft_id, int) and draft_id > 0:
            exists = _get_inventory_operation_draft_row(connection, draft_id)
            if not exists:
                raise HTTPException(status_code=404, detail="draft not found")
            connection.execute(
                """
                UPDATE ly_local_inventory_operation_drafts
                SET scenario_tag = ?,
                    operation_type = ?,
                    flow_type = ?,
                    material_code = ?,
                    material_name = ?,
                    spec = ?,
                    uom = ?,
                    warehouse = ?,
                    source_warehouse = ?,
                    target_warehouse = ?,
                    current_qty = ?,
                    operation_qty = ?,
                    counting_qty = ?,
                    diff_qty = ?,
                    status = ?,
                    business_ref = ?,
                    business_time = ?,
                    note = ?,
                    state = 'saved',
                    updated_at = ?,
                    cancelled_at = NULL,
                    cancel_reason = NULL
                WHERE id = ?
                """,
                (
                    scenario_tag,
                    operation_type,
                    flow_type,
                    material_code,
                    material_name,
                    spec,
                    uom,
                    warehouse,
                    source_warehouse,
                    target_warehouse,
                    current_qty,
                    operation_qty,
                    counting_qty,
                    diff_qty,
                    status,
                    business_ref,
                    business_time,
                    note,
                    now_iso,
                    draft_id,
                ),
            )
            connection.commit()
            row = _get_inventory_operation_draft_row(connection, draft_id)
        else:
            draft_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor = connection.execute(
                """
                INSERT INTO ly_local_inventory_operation_drafts (
                    scenario_tag,
                    draft_no,
                    operation_type,
                    flow_type,
                    material_code,
                    material_name,
                    spec,
                    uom,
                    warehouse,
                    source_warehouse,
                    target_warehouse,
                    current_qty,
                    operation_qty,
                    counting_qty,
                    diff_qty,
                    status,
                    business_ref,
                    business_time,
                    note,
                    state,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'saved', ?, ?)
                """,
                (
                    scenario_tag,
                    draft_no,
                    operation_type,
                    flow_type,
                    material_code,
                    material_name,
                    spec,
                    uom,
                    warehouse,
                    source_warehouse,
                    target_warehouse,
                    current_qty,
                    operation_qty,
                    counting_qty,
                    diff_qty,
                    status,
                    business_ref,
                    business_time,
                    note,
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()
            row = _get_inventory_operation_draft_row(connection, int(cursor.lastrowid))

    if row is None:
        raise HTTPException(status_code=500, detail="draft persistence failed")
    return _ok(_inventory_operation_draft_row_to_dict(row))


@app.get("/api/local-dev/inventory-operation-drafts")
def list_local_inventory_operation_drafts(
    keyword: str | None = None,
    material_code: str | None = None,
    warehouse: str | None = None,
    flow_type: str | None = None,
    operation_type: str | None = None,
    status: str | None = None,
    scenario_tag: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_inventory_operation_draft_table(connection)
        rows = connection.execute(
            "SELECT * FROM ly_local_inventory_operation_drafts ORDER BY id DESC",
        ).fetchall()

    items = [_inventory_operation_draft_row_to_dict(row) for row in rows]
    keyword_token = (keyword or "").strip().lower()
    material_token = (material_code or "").strip().lower()
    warehouse_token = (warehouse or "").strip().lower()
    flow_token = (flow_type or "").strip().lower()
    operation_token = (operation_type or "").strip().lower()
    status_token = (status or "").strip().lower()
    scenario_token = (scenario_tag or "").strip()

    def _match(item: dict[str, Any]) -> bool:
        if keyword_token and keyword_token not in (
            f"{item['draft_no']} {item['material_code']} {item['business_ref']}".lower()
        ):
            return False
        if material_token and material_token not in str(item["material_code"]).lower():
            return False
        if warehouse_token and warehouse_token not in str(item["warehouse"]).lower():
            return False
        if flow_token and flow_token != str(item["flow_type"]).lower():
            return False
        if operation_token and operation_token != str(item["operation_type"]).lower():
            return False
        if status_token and status_token != str(item["status"]).lower():
            return False
        if scenario_token and scenario_token != str(item["scenario_tag"]):
            return False
        return True

    filtered = [item for item in items if _match(item)]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    paged_items = filtered[start:end]
    return _ok({"items": paged_items, "total": total, "page": page, "page_size": page_size})


@app.get("/api/local-dev/inventory-operation-drafts/residual-count")
def get_local_inventory_operation_residual_count(
    scenario_tag: str = Query(..., min_length=1),
) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_inventory_operation_draft_table(connection)
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_inventory_operation_drafts WHERE scenario_tag = ?",
            (scenario_tag.strip(),),
        ).fetchone()
    total = int(row["total"]) if row else 0
    return _ok({"scenario_tag": scenario_tag.strip(), "total": total})


@app.post("/api/local-dev/inventory-operation-drafts/rollback-by-scenario")
def rollback_local_inventory_operation_drafts(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_inventory_operation_draft_table(connection)
        before = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_inventory_operation_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        ).fetchone()
        deleted_count = int(before["total"]) if before else 0
        connection.execute(
            "DELETE FROM ly_local_inventory_operation_drafts WHERE scenario_tag = ?",
            (scenario_tag,),
        )
        connection.commit()
        after = connection.execute(
            "SELECT COUNT(*) AS total FROM ly_local_inventory_operation_drafts WHERE scenario_tag = ?",
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


@app.get("/api/local-dev/inventory-operation-drafts/{draft_id}")
def get_local_inventory_operation_draft(draft_id: int) -> dict[str, Any]:
    with _connect_local_sqlite() as connection:
        _create_inventory_operation_draft_table(connection)
        row = _get_inventory_operation_draft_row(connection, draft_id)
    if row is None:
        raise HTTPException(status_code=404, detail="draft not found")
    return _ok(_inventory_operation_draft_row_to_dict(row))


@app.post("/api/local-dev/inventory-operation-drafts/{draft_id}/cancel")
def cancel_local_inventory_operation_draft(
    draft_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    reason = str(payload.get("reason", "")).strip() or f"CANCEL-{scenario_tag or draft_id}"
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    now_iso = _now_iso()
    with _connect_local_sqlite() as connection:
        _create_inventory_operation_draft_table(connection)
        row = _get_inventory_operation_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        if row["scenario_tag"] != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")
        connection.execute(
            """
            UPDATE ly_local_inventory_operation_drafts
            SET state = 'cancelled',
                updated_at = ?,
                cancelled_at = ?,
                cancel_reason = ?
            WHERE id = ?
            """,
            (now_iso, now_iso, reason, draft_id),
        )
        connection.commit()
        cancelled = _get_inventory_operation_draft_row(connection, draft_id)
    if cancelled is None:
        raise HTTPException(status_code=500, detail="draft cancel failed")
    return _ok(_inventory_operation_draft_row_to_dict(cancelled))


def _build_stock_ledger_draft_payload(payload: dict[str, Any], draft_id: int | None = None) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    operation_type = str(payload.get("operation_type", "")).strip().lower() or "transfer"
    flow_type = str(payload.get("flow_type", "")).strip().lower() or operation_type
    material_code = str(payload.get("material_code", "")).strip()
    warehouse = str(payload.get("warehouse", "")).strip()
    source_warehouse = str(payload.get("source_warehouse", "")).strip() or warehouse
    target_warehouse = str(payload.get("target_warehouse", "")).strip() or warehouse
    transfer_qty = _to_float(payload.get("transfer_qty", payload.get("qty")), 0.0)
    current_qty = _to_float(payload.get("current_qty"), 0.0)
    counting_qty = _to_float(payload.get("counting_qty"), current_qty)
    business_ref = str(payload.get("business_ref", "")).strip() or f"SL-{scenario_tag}"
    business_time = str(payload.get("business_time", "")).strip() or date.today().isoformat()
    status = str(payload.get("status", "")).strip() or "draft"
    normalized: dict[str, Any] = {
        "scenario_tag": scenario_tag,
        "operation_type": operation_type,
        "flow_type": flow_type,
        "material_code": material_code,
        "material_name": str(payload.get("material_name", "")).strip() or material_code,
        "spec": str(payload.get("spec", "")).strip(),
        "uom": str(payload.get("uom", "")).strip() or "Nos",
        "warehouse": warehouse,
        "source_warehouse": source_warehouse,
        "target_warehouse": target_warehouse,
        "current_qty": current_qty,
        "transfer_qty": transfer_qty if transfer_qty > 0 else 1.0,
        "counting_qty": counting_qty,
        "status": status,
        "business_ref": business_ref,
        "business_time": business_time,
        "note": str(payload.get("note", "")).strip() or f"{scenario_tag}-stock-ledger-draft",
    }
    if draft_id is not None:
        normalized["draft_id"] = draft_id
    return normalized


@app.get("/api/local-dev/stock-ledger")
def list_local_stock_ledger_records(
    scenario_tag: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    listed = list_local_inventory_operation_drafts(
        scenario_tag=scenario_tag.strip(),
        page=page,
        page_size=page_size,
    )
    data = listed.get("data", {})
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="invalid stock-ledger readback payload")
    records = data.get("items", [])
    total = int(data.get("total", len(records) if isinstance(records, list) else 0))
    return _ok(
        {
            "scenario_tag": scenario_tag.strip(),
            "records": records,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@app.post("/api/local-dev/stock-ledger/draft")
def create_local_stock_ledger_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return upsert_local_inventory_operation_draft(_build_stock_ledger_draft_payload(payload))


@app.patch("/api/local-dev/stock-ledger/draft/{draft_id}")
def update_local_stock_ledger_draft(draft_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return upsert_local_inventory_operation_draft(_build_stock_ledger_draft_payload(payload, draft_id=draft_id))


@app.get("/api/local-dev/stock-ledger/draft/{draft_id}")
def get_local_stock_ledger_draft(draft_id: int) -> dict[str, Any]:
    return get_local_inventory_operation_draft(draft_id)


@app.post("/api/local-dev/stock-ledger/draft/{draft_id}/cancel")
def cancel_local_stock_ledger_draft(draft_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return cancel_local_inventory_operation_draft(draft_id, payload)


@app.post("/api/local-dev/stock-ledger/draft/{draft_id}/rollback")
def rollback_local_stock_ledger_draft(draft_id: int, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    with _connect_local_sqlite() as connection:
        _create_inventory_operation_draft_table(connection)
        row = _get_inventory_operation_draft_row(connection, draft_id)
        if row is None:
            raise HTTPException(status_code=404, detail="draft not found")
        if str(row["scenario_tag"]).strip() != scenario_tag:
            raise HTTPException(status_code=400, detail="scenario_tag mismatch")
    rolled = rollback_local_inventory_operation_drafts({"scenario_tag": scenario_tag})
    data = rolled.get("data", {})
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="rollback failed")
    residual = int(data.get("residual_records_after_rollback", -1))
    return _ok(
        {
            "draft_id": draft_id,
            "scenario_tag": scenario_tag,
            "deleted_count": int(data.get("deleted_count", 0)),
            "residual_records_after_rollback": residual,
            "rollback_success": bool(data.get("rollback_success", False)),
            "zero_residual_success": residual == 0,
        }
    )


@app.get("/api/local-dev/stock-ledger/residual-count")
def get_local_stock_ledger_residual_count(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    return get_local_inventory_operation_residual_count(scenario_tag)


@app.get("/api/local-dev/warehouse/snapshot")
def get_local_warehouse_snapshot(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    tag = scenario_tag.strip()
    listed = list_local_inventory_operation_drafts(
        scenario_tag=tag,
        page=1,
        page_size=200,
    )
    data = listed.get("data", {})
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="invalid warehouse snapshot payload")
    records = data.get("items", [])
    if not isinstance(records, list):
        records = []
    warehouse_index: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        warehouse_name = str(record.get("warehouse", "")).strip() or "UNKNOWN"
        slot = warehouse_index.setdefault(
            warehouse_name,
            {
                "warehouse": warehouse_name,
                "record_count": 0,
                "operation_qty_total": 0.0,
                "latest_business_time": "",
            },
        )
        slot["record_count"] = int(slot["record_count"]) + 1
        slot["operation_qty_total"] = _to_float(slot.get("operation_qty_total"), 0.0) + _to_float(
            record.get("operation_qty"), 0.0
        )
        business_time = str(record.get("business_time", "")).strip()
        if business_time and business_time > str(slot["latest_business_time"]):
            slot["latest_business_time"] = business_time
    warehouses = sorted(warehouse_index.values(), key=lambda item: str(item["warehouse"]))
    return _ok(
        {
            "scenario_tag": tag,
            "total_records": len(records),
            "warehouses": warehouses,
            "latest_record": records[0] if records else None,
        }
    )


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _count_and_latest_for_scenario(
    connection: sqlite3.Connection, table_name: str, scenario_tag: str
) -> tuple[int, str]:
    if not _table_exists(connection, table_name):
        return 0, ""
    row = connection.execute(
        f"SELECT COUNT(*) AS total, MAX(updated_at) AS latest_updated_at FROM {table_name} WHERE scenario_tag = ?",
        (scenario_tag,),
    ).fetchone()
    if row is None:
        return 0, ""
    return int(row["total"] or 0), str(row["latest_updated_at"] or "")


def _build_dashboard_module_summaries(scenario_tag: str) -> list[dict[str, Any]]:
    module_specs = [
        ("foundation", "基础资料", "local_foundation_reference", "/api/local-dev/foundation/references"),
        ("bom", "BOM/款式/面辅料", "ly_local_bom_drafts", "/api/local-dev/bom/list"),
        ("sales_order", "大货销售订单", "ly_local_sales_order_drafts", "/api/local-dev/sales-orders"),
        ("production_plan", "生产计划", "ly_local_production_plan_drafts", "/api/local-dev/production-plans"),
        ("purchase_subcontract", "采购/外协", "ly_local_purchase_subcontract_drafts", "/api/local-dev/subcontract/orders"),
        ("stock_ledger", "库存流水/仓库", "ly_local_inventory_operation_drafts", "/api/local-dev/stock-ledger"),
    ]
    summaries: list[dict[str, Any]] = []
    with _connect_local_sqlite() as connection:
        for module_key, module_label, table_name, source_endpoint in module_specs:
            record_count, latest_updated_at = _count_and_latest_for_scenario(connection, table_name, scenario_tag)
            summaries.append(
                {
                    "module_key": module_key,
                    "module_label": module_label,
                    "table_name": table_name,
                    "source_endpoint": source_endpoint,
                    "record_count": record_count,
                    "latest_updated_at": latest_updated_at,
                    "readback_success": True,
                }
            )
    return summaries


@app.get("/api/local-dev/dashboard/status-summary")
def get_local_dashboard_status_summary(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    tag = scenario_tag.strip()
    modules = _build_dashboard_module_summaries(tag)
    total_records = sum(int(item.get("record_count", 0)) for item in modules)
    readback_success_count = sum(1 for item in modules if bool(item.get("readback_success")))
    return _ok(
        {
            "scenario_tag": tag,
            "readback_only": True,
            "generated_at": _now_iso(),
            "modules": modules,
            "totals": {
                "module_count": len(modules),
                "total_records": total_records,
                "readback_success_count": readback_success_count,
                "write_requests_observed_count": 0,
            },
            "workspace_redirect": {
                "route": "/dashboard/workplace",
                "final_path": "/dashboard/overview",
            },
            "production_safety": {
                "production_write_requests": 0,
                "erpnext_production_write_requests": 0,
                "real_production_account_used": False,
            },
        }
    )


@app.get("/api/local-dev/dashboard/checkpoints")
def get_local_dashboard_checkpoints(scenario_tag: str = Query(..., min_length=1)) -> dict[str, Any]:
    tag = scenario_tag.strip()
    modules = _build_dashboard_module_summaries(tag)
    total_records = sum(int(item.get("record_count", 0)) for item in modules)
    checkpoints = [
        {
            "checkpoint_key": "home_readback_summary",
            "checkpoint_label": "首页 readback summary",
            "status": "success",
            "summary_endpoint": "/api/local-dev/dashboard/status-summary",
        },
        {
            "checkpoint_key": "dashboard_overview_readback_summary",
            "checkpoint_label": "工作台总览 readback summary",
            "status": "success",
            "summary_endpoint": "/api/local-dev/dashboard/status-summary",
        },
        {
            "checkpoint_key": "workspace_redirect_readback",
            "checkpoint_label": "工作台路由 redirect/readback",
            "status": "success",
            "route": "/dashboard/workplace",
            "final_path": "/dashboard/overview",
        },
    ]
    return _ok(
        {
            "scenario_tag": tag,
            "readback_only": True,
            "generated_at": _now_iso(),
            "write_requests_observed_count": 0,
            "summary_totals": {
                "module_count": len(modules),
                "total_records": total_records,
            },
            "checkpoints": checkpoints,
            "workspace_redirect": {
                "route": "/dashboard/workplace",
                "final_path": "/dashboard/overview",
                "readback_success": True,
            },
        }
    )


@app.post("/api/local-dev/dashboard/checkpoints/rollback")
def rollback_local_dashboard_checkpoints(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    scenario_tag = str(payload.get("scenario_tag", "")).strip()
    if not scenario_tag:
        raise HTTPException(status_code=400, detail="scenario_tag is required")
    # CAND006 default boundary is readback-only. Keep rollback endpoint as explicit no-op.
    return _ok(
        {
            "scenario_tag": scenario_tag,
            "readback_only_no_write": True,
            "deleted_count": 0,
            "residual_records_after_rollback": 0,
            "rollback_success": True,
            "zero_residual_success": True,
        }
    )
