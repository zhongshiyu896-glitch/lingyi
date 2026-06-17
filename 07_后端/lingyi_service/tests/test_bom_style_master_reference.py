"""BOM style-master reference tests."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.error_codes import STYLE_MASTER_INVALID_REFERENCE
from app.core.exceptions import BusinessException
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.schemas.bom import BomCreateRequest
from app.schemas.bom import BomUpdateRequest
from app.services.bom_service import BomService


class BomStyleMasterReferenceTest(unittest.TestCase):
    """Validate BOM header item_code links to enabled FastAPI style master."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine(
            "sqlite+pysqlite://",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            execution_options={"schema_translate_map": {"ly_schema": None, "public": None}},
        )
        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        StyleMasterBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        with self.SessionLocal() as session:
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.query(LyStyleMaster).delete()
            session.commit()

    @staticmethod
    def _style(style_no: str, *, status: str = "enabled") -> LyStyleMaster:
        return LyStyleMaster(
            company="COMP-BOM",
            ys_style_no=style_no,
            ys_style_name_cn=f"{style_no} 款式",
            ys_season="SS",
            ys_year="2026",
            ys_brand="LY",
            ys_style_status=status,
            colors=[{"ys_color_code": "BLK", "ys_color_name": "黑"}],
            sizes=[{"ys_size_code": "M", "ys_size_name": "M"}],
            version=1,
            created_by="seed",
            updated_by="seed",
        )

    @staticmethod
    def _create_payload(*, item_code: str, material_item_code: str = "MAT-FREE-001") -> BomCreateRequest:
        return BomCreateRequest(
            scenario_tag="Z002-BOM-20260618-001",
            idempotency_key=f"IDEMP-{item_code}-CREATE",
            source_ref=f"SRC-{item_code}",
            item_code=item_code,
            version_no="V1",
            bom_items=[
                {
                    "material_item_code": material_item_code,
                    "qty_per_piece": Decimal("1.25"),
                    "loss_rate": Decimal("0.05"),
                    "uom": "米",
                }
            ],
            operations=[
                {
                    "process_name": "车缝",
                    "sequence_no": 1,
                    "is_subcontract": False,
                    "wage_rate": Decimal("1.20"),
                }
            ],
        )

    @staticmethod
    def _update_payload(*, bom_no: str, item_code: str) -> BomUpdateRequest:
        return BomUpdateRequest(
            scenario_tag="Z002-BOM-20260618-001",
            idempotency_key=f"IDEMP-{item_code}-UPDATE",
            source_ref=bom_no,
            bom_no=bom_no,
            item_code=item_code,
            version_no="V2",
            bom_items=[
                {
                    "material_item_code": "MAT-FREE-UPDATE",
                    "qty_per_piece": Decimal("1.50"),
                    "loss_rate": Decimal("0"),
                    "uom": "米",
                }
            ],
            operations=[
                {
                    "process_name": "整烫",
                    "sequence_no": 1,
                    "is_subcontract": False,
                    "wage_rate": Decimal("0.80"),
                }
            ],
        )

    def test_create_bom_requires_enabled_style_master_header(self) -> None:
        with self.SessionLocal() as session:
            session.add(self._style("STYLE-BOM-001", status="enabled"))
            session.commit()

            created = BomService(session).create_bom(
                payload=self._create_payload(item_code="STYLE-BOM-001", material_item_code="MAT-NO-STYLE"),
                operator="bom.user",
            )
            self.assertTrue(created.name.startswith("BOM-STYLE-BOM-001-V1-"))
            bom = session.query(LyApparelBom).one()
            item = session.query(LyApparelBomItem).one()
            self.assertEqual(bom.item_code, "STYLE-BOM-001")
            self.assertEqual(item.material_item_code, "MAT-NO-STYLE")
            self.assertIsNone(
                session.query(LyStyleMaster)
                .filter(LyStyleMaster.ys_style_no == "MAT-NO-STYLE")
                .first()
            )

    def test_create_bom_rejects_missing_or_disabled_style_master_header(self) -> None:
        with self.SessionLocal() as session:
            session.add(self._style("STYLE-BOM-DISABLED", status="disabled"))
            session.commit()
            service = BomService(session)

            with self.assertRaises(BusinessException) as missing_ctx:
                service.create_bom(payload=self._create_payload(item_code="STYLE-BOM-MISSING"), operator="bom.user")
            self.assertEqual(missing_ctx.exception.code, STYLE_MASTER_INVALID_REFERENCE)

            with self.assertRaises(BusinessException) as disabled_ctx:
                service.create_bom(payload=self._create_payload(item_code="STYLE-BOM-DISABLED"), operator="bom.user")
            self.assertEqual(disabled_ctx.exception.code, STYLE_MASTER_INVALID_REFERENCE)
            self.assertEqual(session.query(LyApparelBom).count(), 0)

    def test_update_bom_rechecks_enabled_style_master_header(self) -> None:
        with self.SessionLocal() as session:
            style = self._style("STYLE-BOM-UPDATE", status="enabled")
            session.add(style)
            session.commit()
            service = BomService(session)
            created = service.create_bom(payload=self._create_payload(item_code="STYLE-BOM-UPDATE"), operator="bom.user")
            bom = session.query(LyApparelBom).filter(LyApparelBom.bom_no == created.name).one()

            updated = service.update_bom_draft(
                bom_id=int(bom.id),
                payload=self._update_payload(bom_no=created.name, item_code="STYLE-BOM-UPDATE"),
                operator="bom.user",
            )
            self.assertEqual(updated.name, created.name)

            style.ys_style_status = "disabled"
            session.flush()
            with self.assertRaises(BusinessException) as disabled_ctx:
                service.update_bom_draft(
                    bom_id=int(bom.id),
                    payload=self._update_payload(bom_no=created.name, item_code="STYLE-BOM-UPDATE"),
                    operator="bom.user",
                )
            self.assertEqual(disabled_ctx.exception.code, STYLE_MASTER_INVALID_REFERENCE)


if __name__ == "__main__":
    unittest.main()
