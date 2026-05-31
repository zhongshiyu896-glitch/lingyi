"""Local development ASGI entrypoint.

This module keeps the production app unchanged while making the local Vue
frontend usable without ERPNext login cookies. It enables dev-header auth,
uses a SQLite database with schema translation, creates the tables needed by
the local screens, and seeds a tiny BOM fixture if the database is empty.
"""

from __future__ import annotations

from datetime import date
import os

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
