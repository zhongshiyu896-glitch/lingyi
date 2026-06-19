"""Material BOM vertical API tests."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyApparelBomWriteOperation
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseRequirement
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.production import Base as ProductionBase
from app.models.production import LyProductionPlan
from app.models.production import LyProductionPlanMaterial
from app.models.production import LyProductionPlanOperation
from app.models.sample import Base as SampleBase
from app.models.sample import LySampleIdempotency
from app.models.sample import LySampleMaterialBom
from app.models.sample import LySampleMaterialBomItem
from app.models.sample import LySampleMaterialBomOperation
from app.models.sample import LySampleOrder
from app.models.sales_order import Base as SalesOrderBase
from app.models.sales_order import LySalesOrder
from app.models.sales_order import LySalesOrderIdempotency
from app.models.sales_order import LySalesOrderItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleDictionary
from app.models.style_master import LyStyleMaster
from app.models.style_master import LyStyleMasterIdempotency
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.production import get_db_session as production_db_dep
from app.routers.sales_inventory import get_db_session as sales_inventory_db_dep
from app.routers.sample import get_db_session as sample_db_dep
from app.routers.style_master import get_db_session as style_master_db_dep
from app.services.erpnext_production_adapter import ERPNextProductionAdapter


class MaterialBomApiTest(unittest.TestCase):
    """Validate style/sample material BOM and production material calculation."""

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
        SampleBase.metadata.create_all(bind=cls.engine)
        SalesOrderBase.metadata.create_all(bind=cls.engine)
        ProductionBase.metadata.create_all(bind=cls.engine)
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        MasterDataBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[style_master_db_dep] = _override_db
        app.dependency_overrides[sales_inventory_db_dep] = _override_db
        app.dependency_overrides[sample_db_dep] = _override_db
        app.dependency_overrides[production_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(style_master_db_dep, None)
        app.dependency_overrides.pop(sales_inventory_db_dep, None)
        app.dependency_overrides.pop(sample_db_dep, None)
        app.dependency_overrides.pop(production_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyMaterialPurchaseRequirement).delete()
            session.query(LyProductionPlanOperation).delete()
            session.query(LyProductionPlanMaterial).delete()
            session.query(LyProductionPlan).delete()
            session.query(LySampleIdempotency).delete()
            session.query(LySampleMaterialBomOperation).delete()
            session.query(LySampleMaterialBomItem).delete()
            session.query(LySampleMaterialBom).delete()
            session.query(LySampleOrder).delete()
            session.query(LyApparelBomWriteOperation).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.query(LyMasterDataRecord).delete()
            session.query(LySalesOrderItem).delete()
            session.query(LySalesOrderIdempotency).delete()
            session.query(LySalesOrder).delete()
            session.query(LyStyleMasterIdempotency).delete()
            session.query(LyStyleMaster).delete()
            session.query(LyStyleDictionary).delete()
            self._seed_style_dictionaries(session)
            self._seed_material_master(session)
            self._seed_sales_order(session)
            session.commit()

    @staticmethod
    def _headers(role: str = "System Manager", request_id: str = "MATERIAL-BOM-REQ") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "material.bom.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _seed_style_dictionaries(session) -> None:
        for index, (dict_type, code, name) in enumerate(
            [
                ("season", "SS", "春夏"),
                ("year", "2026", "2026"),
                ("brand", "LY", "领意"),
                ("color", "BLK", "黑色"),
                ("size", "M", "M"),
            ],
            start=1,
        ):
            session.add(
                LyStyleDictionary(
                    id=index,
                    company="COMP-MB",
                    dict_type=dict_type,
                    code=code,
                    name=name,
                    status="active",
                    sort_no=index,
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )

    @staticmethod
    def _seed_material_master(session) -> None:
        for index, (code, name, status) in enumerate(
            [
                ("FAB-BLK-001", "黑色主面料", "active"),
                ("FAB-ALT-001", "可替代面料", "active"),
                ("FAB-ALT-XL", "可替代 XL 面料", "active"),
                ("FAB-OFF-001", "停用面料", "inactive"),
            ],
            start=1,
        ):
            session.add(
                LyMasterDataRecord(
                    id=index,
                    entity_type="material",
                    company="COMP-MB",
                    code=code,
                    name=name,
                    status=status,
                    payload={
                        "material_kind": "fabric",
                        "material_item_code": code,
                        "fabric_name": name,
                        "uom": "米",
                    },
                    version=1,
                    created_by="seed",
                    updated_by="seed",
                )
            )

    @staticmethod
    def _seed_sales_order(session) -> None:
        order = LySalesOrder(
            company="COMP-MB",
            sales_order_no="SO-MB-001",
            customer="BOM 客户",
            status="draft",
            docstatus=0,
            currency="CNY",
            grand_total=Decimal("0"),
            idempotency_key="seed-SO-MB-001",
            request_hash="seed-SO-MB-001",
            payload={},
            created_by="seed",
            updated_by="seed",
        )
        session.add(order)
        session.flush()
        session.add(
            LySalesOrderItem(
                sales_order_id=int(order.id),
                company="COMP-MB",
                line_no=1,
                sales_order_item="SOI-MB-001",
                item_code="ST-MB-001",
                item_name="BOM 测试款",
                qty=Decimal("50"),
                planned_qty=Decimal("0"),
                delivered_qty=Decimal("0"),
                ys_material_calc_state="待算料",
                uom="Nos",
            )
        )

    def _seed_style(self, *, style_no: str = "ST-MB-001") -> int:
        with self.SessionLocal() as session:
            row = LyStyleMaster(
                company="COMP-MB",
                ys_style_no=style_no,
                ys_style_name_cn="BOM 测试款",
                ys_season="SS",
                ys_year="2026",
                ys_brand="LY",
                ys_style_status="enabled",
                colors=[{"ys_color_code": "BLK", "ys_color_name": "黑色"}],
                sizes=[{"ys_size_code": "M", "ys_size_name": "M"}],
                version=1,
                created_by="seed",
                updated_by="seed",
            )
            session.add(row)
            session.commit()
            return int(row.id)

    def _style_bom_payload(self, *, idempotency_key: str = "IDEMP-STYLE-MB-UPSERT") -> dict:
        return {
            "operation": "upsert",
            "company": "COMP-MB",
            "idempotency_key": idempotency_key,
            "version_no": "V1",
            "items": [
                {
                    "material_item_code": "FAB-BLK-001",
                    "color": "黑",
                    "size": "M",
                    "part": "前片",
                    "qty_per_piece": "2",
                    "loss_rate": "0.05",
                    "uom": "米",
                    "remark": "面料",
                }
            ],
        }

    def test_style_material_bom_rejects_missing_or_inactive_material(self) -> None:
        style_id = self._seed_style()
        missing_payload = self._style_bom_payload(idempotency_key="IDEMP-STYLE-MB-MISSING")
        missing_payload["items"][0]["material_item_code"] = "FAB-MISSING-001"
        missing = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="STYLE-MB-MISSING-MATERIAL"),
            json=missing_payload,
        )
        self.assertEqual(missing.status_code, 409, missing.text)
        self.assertEqual(missing.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")
        self.assertIn("FAB-MISSING-001", missing.json()["message"])

        inactive_payload = self._style_bom_payload(idempotency_key="IDEMP-STYLE-MB-INACTIVE")
        inactive_payload["items"][0]["material_item_code"] = "FAB-OFF-001"
        inactive = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="STYLE-MB-INACTIVE-MATERIAL"),
            json=inactive_payload,
        )
        self.assertEqual(inactive.status_code, 409, inactive.text)
        self.assertEqual(inactive.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")
        self.assertIn("FAB-OFF-001", inactive.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyApparelBom).count(), 0)
            self.assertEqual(session.query(LyApparelBomItem).count(), 0)
            self.assertEqual(session.query(LyApparelBomWriteOperation).count(), 0)

    def test_style_material_bom_upsert_explode_and_style_no_sync(self) -> None:
        style_id = self._seed_style()
        upserted = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="STYLE-MB-UPSERT"),
            json=self._style_bom_payload(),
        )
        self.assertEqual(upserted.status_code, 200, upserted.text)
        self.assertEqual(upserted.json()["data"]["bom"]["item_code"], "ST-MB-001")
        self.assertEqual(upserted.json()["data"]["items"][0]["part"], "前片")
        self.assertEqual(upserted.json()["data"]["items"][0]["size"], "M")

        exploded = self.client.post(
            f"/api/style-master/styles/{style_id}/material-bom/explode?company=COMP-MB",
            headers=self._headers(request_id="STYLE-MB-EXPLODE"),
            json={"order_qty": "10"},
        )
        self.assertEqual(exploded.status_code, 200, exploded.text)
        self.assertEqual(exploded.json()["data"]["items"][0]["required_qty"], "21.000000")
        self.assertEqual(exploded.json()["data"]["items"][0]["size"], "M")

        updated_style = self.client.patch(
            f"/api/style-master/styles/{style_id}",
            headers=self._headers(request_id="STYLE-MB-STYLE-NO-SYNC"),
            json={
                "operation": "update",
                "company": "COMP-MB",
                "ys_style_no": "ST-MB-001-R",
                "idempotency_key": "IDEMP-STYLE-MB-NO-SYNC",
            },
        )
        self.assertEqual(updated_style.status_code, 200, updated_style.text)
        with self.SessionLocal() as session:
            bom = session.query(LyApparelBom).one()
            self.assertEqual(bom.style_master_id, style_id)
            self.assertEqual(bom.item_code, "ST-MB-001-R")
            self.assertEqual(session.query(LyApparelBomWriteOperation).count(), 1)

    def test_empty_style_material_bom_explode_returns_explicit_error(self) -> None:
        style_id = self._seed_style()
        with self.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    company="COMP-MB",
                    style_master_id=style_id,
                    bom_no="BOM-STYLE-EMPTY",
                    item_code="ST-MB-001",
                    version_no="V1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        exploded = self.client.post(
            f"/api/style-master/styles/{style_id}/material-bom/explode?company=COMP-MB",
            headers=self._headers(request_id="STYLE-MB-EMPTY-EXPLODE"),
            json={"order_qty": "10"},
        )
        self.assertEqual(exploded.status_code, 404, exploded.text)
        self.assertEqual(exploded.json()["code"], "BOM_NOT_FOUND")
        self.assertIn("未维护明细", exploded.json()["message"])

    def test_sample_material_bom_copies_style_snapshot_and_can_be_edited(self) -> None:
        style_id = self._seed_style()
        self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-SEED-STYLE"),
            json=self._style_bom_payload(idempotency_key="IDEMP-SAMPLE-MB-SEED-STYLE"),
        )
        with self.SessionLocal() as session:
            order = LySampleOrder(
                company="COMP-MB",
                sample_no="SMP-MB-001",
                style_no="ST-MB-001",
                style_name="BOM 测试款",
                style_master_id=style_id,
                customer="BOM 客户",
                factory="样衣组",
                sample_type="初样",
                stage="建档",
                progress=0,
                status="draft",
                image_tone="blue",
                owner_note="",
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            session.commit()
            order_id = int(order.id)

        copied = self.client.post(
            f"/api/sample/orders/{order_id}/material-bom/copy-from-style",
            headers=self._headers(request_id="SAMPLE-MB-COPY"),
            json={
                "operation": "copy_from_style",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-COPY",
            },
        )
        self.assertEqual(copied.status_code, 200, copied.text)
        self.assertEqual(copied.json()["data"]["items"][0]["material_item_code"], "FAB-BLK-001")
        self.assertEqual(copied.json()["data"]["items"][0]["size"], "M")
        copied_source_item_id = copied.json()["data"]["items"][0]["source_bom_item_id"]
        self.assertIsNotNone(copied_source_item_id)

        edited = self.client.put(
            f"/api/sample/orders/{order_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-EDIT"),
            json={
                "operation": "upsert",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-EDIT",
                "version_no": "S2",
                "items": [
                    {
                        "source_bom_item_id": copied_source_item_id,
                        "material_item_code": "FAB-ALT-001",
                        "color": "黑",
                        "size": "M",
                        "part": "袖口",
                        "qty_per_piece": "1.5",
                        "loss_rate": "0.10",
                        "uom": "米",
                        "is_alternative": True,
                        "replace_group": "FAB-01",
                        "remark": "替代料",
                    }
                ],
            },
        )
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertTrue(edited.json()["data"]["items"][0]["is_alternative"])
        self.assertEqual(edited.json()["data"]["items"][0]["size"], "M")
        self.assertEqual(edited.json()["data"]["items"][0]["source_bom_item_id"], copied_source_item_id)

        invalid_source = self.client.put(
            f"/api/sample/orders/{order_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-EDIT-BAD-SOURCE"),
            json={
                "operation": "upsert",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-EDIT-BAD-SOURCE",
                "version_no": "S2",
                "items": [
                    {
                        "source_bom_item_id": 999999,
                        "material_item_code": "FAB-ALT-001",
                        "qty_per_piece": "1.5",
                        "loss_rate": "0.10",
                        "uom": "米",
                    }
                ],
            },
        )
        self.assertEqual(invalid_source.status_code, 409, invalid_source.text)
        self.assertEqual(invalid_source.json()["code"], "SAMPLE_CONFLICT")
        self.assertIn("来源行不属于当前款 BOM", invalid_source.json()["message"])

        exploded = self.client.post(
            f"/api/sample/orders/{order_id}/material-bom/explode?company=COMP-MB",
            headers=self._headers(request_id="SAMPLE-MB-EXPLODE"),
            json={"order_qty": "20"},
        )
        self.assertEqual(exploded.status_code, 200, exploded.text)
        self.assertEqual(exploded.json()["data"]["items"][0]["required_qty"], "33.000000")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySampleMaterialBom).count(), 1)
            self.assertEqual(session.query(LySampleMaterialBomOperation).count(), 2)
            self.assertEqual(session.query(LyApparelBomItem).one().material_item_code, "FAB-BLK-001")

    def test_sample_material_bom_copy_from_style_rechecks_active_material_snapshot(self) -> None:
        style_id = self._seed_style()
        seeded = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-COPY-INACTIVE-SEED"),
            json=self._style_bom_payload(idempotency_key="IDEMP-SAMPLE-MB-COPY-INACTIVE-SEED"),
        )
        self.assertEqual(seeded.status_code, 200, seeded.text)

        with self.SessionLocal() as session:
            material = (
                session.query(LyMasterDataRecord)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == "COMP-MB",
                    LyMasterDataRecord.code == "FAB-BLK-001",
                )
                .one()
            )
            material.status = "inactive"
            material.updated_by = "test"
            order = LySampleOrder(
                company="COMP-MB",
                sample_no="SMP-MB-COPY-INACTIVE",
                style_no="ST-MB-001",
                style_name="BOM 测试款",
                style_master_id=style_id,
                customer="BOM 客户",
                factory="样衣组",
                sample_type="初样",
                stage="建档",
                progress=0,
                status="draft",
                image_tone="blue",
                owner_note="",
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            session.commit()
            order_id = int(order.id)

        copied = self.client.post(
            f"/api/sample/orders/{order_id}/material-bom/copy-from-style",
            headers=self._headers(request_id="SAMPLE-MB-COPY-INACTIVE"),
            json={
                "operation": "copy_from_style",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-COPY-INACTIVE",
            },
        )
        self.assertEqual(copied.status_code, 409, copied.text)
        self.assertEqual(copied.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")
        self.assertIn("FAB-BLK-001", copied.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySampleMaterialBom).count(), 0)
            self.assertEqual(session.query(LySampleMaterialBomItem).count(), 0)
            self.assertEqual(session.query(LySampleMaterialBomOperation).count(), 0)

    def test_sample_style_change_resets_existing_sample_material_bom_snapshot(self) -> None:
        style_id = self._seed_style()
        seeded = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-STYLE-CHANGE-SEED"),
            json=self._style_bom_payload(idempotency_key="IDEMP-SAMPLE-MB-STYLE-CHANGE-SEED"),
        )
        self.assertEqual(seeded.status_code, 200, seeded.text)
        next_style_id = self._seed_style(style_no="ST-MB-002")

        with self.SessionLocal() as session:
            order = LySampleOrder(
                company="COMP-MB",
                sample_no="SMP-MB-STYLE-CHANGE",
                style_no="ST-MB-001",
                style_name="BOM 测试款",
                style_master_id=style_id,
                customer="BOM 客户",
                factory="样衣组",
                sample_type="初样",
                stage="建档",
                progress=0,
                status="draft",
                image_tone="blue",
                owner_note="",
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            session.commit()
            order_id = int(order.id)

        copied = self.client.post(
            f"/api/sample/orders/{order_id}/material-bom/copy-from-style",
            headers=self._headers(request_id="SAMPLE-MB-STYLE-CHANGE-COPY"),
            json={
                "operation": "copy_from_style",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-STYLE-CHANGE-COPY",
            },
        )
        self.assertEqual(copied.status_code, 200, copied.text)
        self.assertEqual(copied.json()["data"]["items"][0]["material_item_code"], "FAB-BLK-001")
        self.assertEqual(copied.json()["data"]["items"][0]["size"], "M")

        updated = self.client.patch(
            f"/api/sample/orders/{order_id}",
            headers=self._headers(request_id="SAMPLE-MB-STYLE-CHANGE-UPDATE"),
            json={
                "operation": "update",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-STYLE-CHANGE-UPDATE",
                "style_master_id": next_style_id,
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["data"]["style_master_id"], next_style_id)
        self.assertEqual(updated.json()["data"]["style_no"], "ST-MB-002")

        bom_after = self.client.get(
            f"/api/sample/orders/{order_id}/material-bom?company=COMP-MB",
            headers=self._headers(request_id="SAMPLE-MB-STYLE-CHANGE-GET"),
        )
        self.assertEqual(bom_after.status_code, 200, bom_after.text)
        self.assertEqual(bom_after.json()["data"]["items"], [])
        self.assertEqual(bom_after.json()["data"]["bom"]["style_master_id"], next_style_id)
        self.assertEqual(bom_after.json()["data"]["bom"]["item_code"], "ST-MB-002")
        self.assertIsNone(bom_after.json()["data"]["bom"]["source_bom_id"])

        exploded = self.client.post(
            f"/api/sample/orders/{order_id}/material-bom/explode?company=COMP-MB",
            headers=self._headers(request_id="SAMPLE-MB-STYLE-CHANGE-EXPLODE"),
            json={"order_qty": "5"},
        )
        self.assertEqual(exploded.status_code, 404, exploded.text)
        self.assertEqual(exploded.json()["code"], "BOM_NOT_FOUND")
        self.assertIn("明细为空", exploded.json()["message"])
        with self.SessionLocal() as session:
            bom = session.query(LySampleMaterialBom).one()
            self.assertEqual(bom.style_master_id, next_style_id)
            self.assertEqual(bom.item_code, "ST-MB-002")
            self.assertEqual(session.query(LySampleMaterialBomItem).count(), 0)

    def test_sample_material_bom_copy_edit_feeds_converted_bulk_material_check(self) -> None:
        style_id = self._seed_style()
        seeded = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-BULK-SEED-STYLE"),
            json=self._style_bom_payload(idempotency_key="IDEMP-SAMPLE-MB-BULK-SEED"),
        )
        self.assertEqual(seeded.status_code, 200, seeded.text)
        style_bom_id = int(seeded.json()["data"]["bom"]["id"])

        with self.SessionLocal() as session:
            order = LySampleOrder(
                company="COMP-MB",
                sample_no="SMP-MB-BULK-001",
                style_no="ST-MB-001",
                style_name="BOM 测试款",
                style_master_id=style_id,
                customer="BOM 客户",
                factory="样衣组",
                sample_type="初样",
                stage="建档",
                progress=0,
                status="draft",
                image_tone="blue",
                owner_note="",
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            session.commit()
            order_id = int(order.id)

        copied = self.client.post(
            f"/api/sample/orders/{order_id}/material-bom/copy-from-style",
            headers=self._headers(request_id="SAMPLE-MB-BULK-COPY"),
            json={
                "operation": "copy_from_style",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-BULK-COPY",
            },
        )
        self.assertEqual(copied.status_code, 200, copied.text)
        self.assertEqual(copied.json()["data"]["items"][0]["material_item_code"], "FAB-BLK-001")

        edited = self.client.put(
            f"/api/sample/orders/{order_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-BULK-EDIT"),
            json={
                "operation": "upsert",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-BULK-EDIT",
                "version_no": "S2",
                "items": [
                    {
                        "material_item_code": "FAB-ALT-001",
                        "color": "黑",
                        "size": "M",
                        "part": "样板改料",
                        "qty_per_piece": "3",
                        "loss_rate": "0.10",
                        "uom": "码",
                        "is_alternative": True,
                        "replace_group": "FAB-01",
                        "remark": "样板替代料",
                    },
                    {
                        "material_item_code": "FAB-ALT-XL",
                        "color": "黑",
                        "size": "XL",
                        "part": "样板改料",
                        "qty_per_piece": "99",
                        "loss_rate": "0",
                        "uom": "码",
                        "is_alternative": True,
                        "replace_group": "FAB-01",
                        "remark": "尺码不匹配时不可进入大货算料",
                    }
                ],
            },
        )
        self.assertEqual(edited.status_code, 200, edited.text)
        self.assertEqual(edited.json()["data"]["items"][0]["material_item_code"], "FAB-ALT-001")
        self.assertEqual(edited.json()["data"]["items"][0]["size"], "M")
        self.assertEqual(edited.json()["data"]["items"][1]["size"], "XL")

        submitted = self.client.post(
            f"/api/sample/orders/{order_id}/submit",
            headers=self._headers(request_id="SAMPLE-MB-BULK-SUBMIT"),
            json={"company": "COMP-MB", "idempotency_key": "IDEMP-SAMPLE-MB-BULK-SUBMIT"},
        )
        sealed = self.client.post(
            f"/api/sample/orders/{order_id}/seal",
            headers=self._headers(request_id="SAMPLE-MB-BULK-SEAL"),
            json={"company": "COMP-MB", "idempotency_key": "IDEMP-SAMPLE-MB-BULK-SEAL"},
        )
        converted = self.client.post(
            f"/api/sample/orders/{order_id}/convert-to-bulk",
            headers=self._headers(request_id="SAMPLE-MB-BULK-CONVERT"),
            json={
                "operation": "convert",
                "company": "COMP-MB",
                "idempotency_key": "IDEMP-SAMPLE-MB-BULK-CONVERT",
            },
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(sealed.status_code, 200, sealed.text)
        self.assertEqual(converted.status_code, 200, converted.text)
        bulk_no = converted.json()["data"]["bulk_handoff_no"]

        detail = self.client.get(
            f"/api/sales-inventory/sales-orders/{bulk_no}",
            headers=self._headers(request_id="SAMPLE-MB-BULK-DETAIL"),
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        sales_order_item = detail.json()["data"]["items"][0]["name"]
        with self.SessionLocal() as session:
            line = session.query(LySalesOrderItem).filter_by(sales_order_item=sales_order_item).one()
            line.size = "M"
            session.commit()

        created_plan = self.client.post(
            "/api/production/plans",
            headers=self._headers(role="Production Manager", request_id="SAMPLE-MB-BULK-PLAN"),
            json={
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": "ST-MB-001",
                "bom_id": style_bom_id,
                "planned_qty": "1",
                "operation": "create_plan",
                "idempotency_key": "IDEMP-SAMPLE-MB-BULK-PLAN",
                "company": "COMP-MB",
            },
        )
        self.assertEqual(created_plan.status_code, 200, created_plan.text)
        plan_id = int(created_plan.json()["data"]["plan_id"])

        material_check_scenario = "Z003-PROD-PLAN-DETAIL-20260618-703"
        checked = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(role="Production Manager", request_id=f"req-{material_check_scenario}"),
            json={
                "operation": "material_check",
                "idempotency_key": f"{material_check_scenario}-check",
                "scenario_tag": material_check_scenario,
                "plan_id": plan_id,
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": "ST-MB-001",
                "bom_id": style_bom_id,
                "warehouse": "WH-MB",
                "request_id": f"req-{material_check_scenario}",
            },
        )
        self.assertEqual(checked.status_code, 200, checked.text)
        material_row = checked.json()["data"]["items"][0]
        self.assertEqual(material_row["material_item_code"], "FAB-ALT-001")
        self.assertEqual(material_row["bom_item_id"], None)
        self.assertEqual(material_row["uom"], "码")
        self.assertEqual(material_row["required_qty"], "3.300000")
        self.assertEqual(len(checked.json()["data"]["items"]), 1)

        with self.SessionLocal() as session:
            snapshot = session.query(LyProductionPlanMaterial).one()
            requirement = session.query(LyMaterialPurchaseRequirement).one()
            self.assertIsNone(snapshot.bom_item_id)
            self.assertEqual(snapshot.material_item_code, "FAB-ALT-001")
            self.assertEqual(snapshot.uom, "码")
            self.assertEqual(str(snapshot.required_qty), "3.300000")
            self.assertEqual(requirement.sales_order, bulk_no)
            self.assertEqual(requirement.material_item_code, "FAB-ALT-001")
            self.assertEqual(requirement.uom, "码")
            self.assertEqual(str(requirement.net_required_qty), "3.300000")

    def test_empty_sample_material_bom_does_not_fallback_to_style_bom(self) -> None:
        style_id = self._seed_style()
        seeded = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-EMPTY-FALLBACK-SEED"),
            json=self._style_bom_payload(idempotency_key="IDEMP-SAMPLE-MB-EMPTY-FALLBACK-SEED"),
        )
        self.assertEqual(seeded.status_code, 200, seeded.text)
        style_bom_id = int(seeded.json()["data"]["bom"]["id"])

        sample_no = "SMP-MB-EMPTY-BOM-001"
        bulk_no = "SO-MB-EMPTY-SAMPLE"
        sales_order_item = "SOI-MB-EMPTY-SAMPLE"
        with self.SessionLocal() as session:
            sample = LySampleOrder(
                company="COMP-MB",
                sample_no=sample_no,
                style_no="ST-MB-001",
                style_name="BOM 测试款",
                style_master_id=style_id,
                customer="BOM 客户",
                factory="样衣组",
                sample_type="初样",
                stage="封样",
                progress=100,
                status="converted",
                bulk_handoff_no=bulk_no,
                image_tone="blue",
                owner_note="",
                created_by="seed",
                updated_by="seed",
            )
            session.add(sample)
            session.flush()
            session.add(
                LySampleMaterialBom(
                    company="COMP-MB",
                    sample_order_id=int(sample.id),
                    style_master_id=style_id,
                    item_code="ST-MB-001",
                    source_bom_id=style_bom_id,
                    version_no="S-EMPTY",
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            sales_order = LySalesOrder(
                company="COMP-MB",
                sales_order_no=bulk_no,
                source_order_ref=f"SAMPLE-{sample_no}",
                customer="BOM 客户",
                status="draft",
                docstatus=0,
                currency="CNY",
                grand_total=Decimal("0"),
                idempotency_key=f"seed-{bulk_no}",
                request_hash=f"seed-{bulk_no}",
                payload={},
                created_by="seed",
                updated_by="seed",
            )
            session.add(sales_order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(sales_order.id),
                    company="COMP-MB",
                    line_no=1,
                    sales_order_item=sales_order_item,
                    item_code="ST-MB-001",
                    item_name="BOM 测试款",
                    qty=Decimal("1"),
                    planned_qty=Decimal("0"),
                    delivered_qty=Decimal("0"),
                    ys_material_calc_state="待算料",
                    uom="件",
                )
            )
            plan = LyProductionPlan(
                plan_no="PP-MB-EMPTY-SAMPLE",
                company="COMP-MB",
                sales_order=bulk_no,
                sales_order_item=sales_order_item,
                item_code="ST-MB-001",
                bom_id=style_bom_id,
                bom_version="V1",
                planned_qty=Decimal("1"),
                status="planned",
                idempotency_key="EMPTY-SAMPLE-PLAN",
                request_hash="EMPTY-SAMPLE-HASH",
                created_by="seed",
            )
            session.add(plan)
            session.commit()
            plan_id = int(plan.id)

        scenario = "Z003-PROD-PLAN-DETAIL-20260618-705"
        checked = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(role="Production Manager", request_id=f"req-{scenario}"),
            json={
                "operation": "material_check",
                "idempotency_key": f"{scenario}-check",
                "scenario_tag": scenario,
                "plan_id": plan_id,
                "sales_order": bulk_no,
                "sales_order_item": sales_order_item,
                "item_code": "ST-MB-001",
                "bom_id": style_bom_id,
                "warehouse": "WH-MB",
                "request_id": f"req-{scenario}",
            },
        )
        self.assertEqual(checked.status_code, 404, checked.text)
        self.assertEqual(checked.json()["code"], "PRODUCTION_BOM_NOT_FOUND")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlanMaterial).count(), 0)
            self.assertEqual(session.query(LyMaterialPurchaseRequirement).count(), 0)

    def test_sample_material_bom_rejects_missing_or_inactive_material(self) -> None:
        style_id = self._seed_style()
        with self.SessionLocal() as session:
            order = LySampleOrder(
                company="COMP-MB",
                sample_no="SMP-MB-INVALID",
                style_no="ST-MB-001",
                style_name="BOM 测试款",
                style_master_id=style_id,
                customer="BOM 客户",
                factory="样衣组",
                sample_type="初样",
                stage="建档",
                progress=0,
                status="draft",
                image_tone="blue",
                owner_note="",
                created_by="seed",
                updated_by="seed",
            )
            session.add(order)
            session.commit()
            order_id = int(order.id)

        payload = {
            "operation": "upsert",
            "company": "COMP-MB",
            "idempotency_key": "IDEMP-SAMPLE-MB-MISSING",
            "version_no": "S1",
            "items": [
                {
                    "material_item_code": "FAB-MISSING-001",
                    "color": "黑",
                    "part": "前片",
                    "qty_per_piece": "1.5",
                    "loss_rate": "0.10",
                    "uom": "米",
                    "is_alternative": False,
                    "replace_group": None,
                    "remark": "缺失料",
                }
            ],
        }
        missing = self.client.put(
            f"/api/sample/orders/{order_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-MISSING-MATERIAL"),
            json=payload,
        )
        self.assertEqual(missing.status_code, 409, missing.text)
        self.assertEqual(missing.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")
        self.assertIn("FAB-MISSING-001", missing.json()["message"])

        payload["idempotency_key"] = "IDEMP-SAMPLE-MB-INACTIVE"
        payload["items"][0]["material_item_code"] = "FAB-OFF-001"
        inactive = self.client.put(
            f"/api/sample/orders/{order_id}/material-bom",
            headers=self._headers(request_id="SAMPLE-MB-INACTIVE-MATERIAL"),
            json=payload,
        )
        self.assertEqual(inactive.status_code, 409, inactive.text)
        self.assertEqual(inactive.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")
        self.assertIn("FAB-OFF-001", inactive.json()["message"])

    def _production_payload(self, *, item_code: str = "ST-MB-001", idempotency_key: str = "idem") -> dict:
        scenario = "Z003-PROD-PLAN-20260618-701"
        return {
            "sales_order": "SO-MB-001",
            "sales_order_item": "SOI-MB-001",
            "item_code": item_code,
            "planned_qty": "10",
            "scenario_tag": scenario,
            "operation": "create",
            "idempotency_key": f"{scenario}-{idempotency_key}",
            "company": "COMP-MB",
        }

    def test_production_plan_defaults_bom_and_material_check_rejects_empty_bom(self) -> None:
        style_id = self._seed_style()
        self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="PROD-MB-SEED-STYLE"),
            json=self._style_bom_payload(idempotency_key="IDEMP-PROD-MB-SEED"),
        )
        scenario = "Z003-PROD-PLAN-20260618-701"
        with patch.object(ERPNextProductionAdapter, "get_sales_order", side_effect=AssertionError("ERP adapter must not be called")) as adapter_lookup:
            created = self.client.post(
                "/api/production/plans",
                headers=self._headers(role="Production Manager", request_id=f"req-{scenario}"),
                json=self._production_payload(idempotency_key="default-bom"),
            )
            adapter_lookup.assert_not_called()
        self.assertEqual(created.status_code, 200, created.text)
        plan_id = int(created.json()["data"]["plan_id"])
        with self.SessionLocal() as session:
            plan = session.query(LyProductionPlan).filter(LyProductionPlan.id == plan_id).one()
            self.assertGreater(int(plan.bom_id), 0)
            bom_id = int(plan.bom_id)

        detail_scenario = "Z003-PROD-PLAN-DETAIL-20260618-701"
        checked = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(role="Production Manager", request_id=f"req-{detail_scenario}"),
            json={
                "operation": "material_check",
                "idempotency_key": f"{detail_scenario}-check",
                "scenario_tag": detail_scenario,
                "plan_id": plan_id,
                "sales_order": "SO-MB-001",
                "sales_order_item": "SOI-MB-001",
                "item_code": "ST-MB-001",
                "bom_id": bom_id,
                "warehouse": "WH-MB",
                "request_id": f"req-{detail_scenario}",
            },
        )
        self.assertEqual(checked.status_code, 200, checked.text)
        self.assertEqual(checked.json()["data"]["items"][0]["required_qty"], "21.000000")

        with self.SessionLocal() as session:
            material = (
                session.query(LyMasterDataRecord)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == "COMP-MB",
                    LyMasterDataRecord.code == "FAB-BLK-001",
                )
                .one()
            )
            material.status = "inactive"
            session.commit()

        inactive_detail_scenario = "Z003-PROD-PLAN-DETAIL-20260618-704"
        inactive_checked = self.client.post(
            f"/api/production/plans/{plan_id}/material-check",
            headers=self._headers(role="Production Manager", request_id=f"req-{inactive_detail_scenario}"),
            json={
                "operation": "material_check",
                "idempotency_key": f"{inactive_detail_scenario}-check",
                "scenario_tag": inactive_detail_scenario,
                "plan_id": plan_id,
                "sales_order": "SO-MB-001",
                "sales_order_item": "SOI-MB-001",
                "item_code": "ST-MB-001",
                "bom_id": bom_id,
                "warehouse": "WH-MB",
                "request_id": f"req-{inactive_detail_scenario}",
            },
        )
        self.assertEqual(inactive_checked.status_code, 409, inactive_checked.text)
        self.assertEqual(inactive_checked.json()["code"], "PRODUCTION_BOM_NOT_ACTIVE")
        self.assertIn("FAB-BLK-001", inactive_checked.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyProductionPlanMaterial).count(), 1)
            self.assertEqual(session.query(LyMaterialPurchaseRequirement).count(), 1)
            material = (
                session.query(LyMasterDataRecord)
                .filter(
                    LyMasterDataRecord.entity_type == "material",
                    LyMasterDataRecord.company == "COMP-MB",
                    LyMasterDataRecord.code == "FAB-BLK-001",
                )
                .one()
            )
            material.status = "active"
            session.commit()

        with self.SessionLocal() as session:
            empty_bom = LyApparelBom(
                id=9001,
                bom_no="BOM-ST-MB-EMPTY",
                company="COMP-MB",
                item_code="ST-MB-EMPTY",
                version_no="V1",
                is_default=True,
                status="active",
                created_by="seed",
                updated_by="seed",
            )
            session.add(empty_bom)
            session.commit()
            empty_order = LySalesOrder(
                company="COMP-MB",
                sales_order_no="SO-MB-EMPTY",
                customer="BOM 客户",
                status="draft",
                docstatus=0,
                currency="CNY",
                grand_total=Decimal("0"),
                idempotency_key="seed-SO-MB-EMPTY",
                request_hash="seed-SO-MB-EMPTY",
                payload={},
                created_by="seed",
                updated_by="seed",
            )
            session.add(empty_order)
            session.flush()
            session.add(
                LySalesOrderItem(
                    sales_order_id=int(empty_order.id),
                    company="COMP-MB",
                    line_no=1,
                    sales_order_item="SOI-MB-EMPTY",
                    item_code="ST-MB-EMPTY",
                    item_name="BOM 空款",
                    qty=Decimal("10"),
                    planned_qty=Decimal("0"),
                    delivered_qty=Decimal("0"),
                    ys_material_calc_state="待算料",
                    uom="Nos",
                )
            )
            empty_plan = LyProductionPlan(
                plan_no="PP-MB-EMPTY",
                company="COMP-MB",
                sales_order="SO-MB-EMPTY",
                sales_order_item="SOI-MB-EMPTY",
                item_code="ST-MB-EMPTY",
                bom_id=9001,
                bom_version="V1",
                planned_qty=Decimal("10"),
                status="planned",
                idempotency_key="EMPTY-PLAN",
                request_hash="EMPTY-HASH",
                created_by="seed",
            )
            session.add(empty_plan)
            session.commit()
            empty_plan_id = int(empty_plan.id)

        empty_detail_scenario = "Z003-PROD-PLAN-DETAIL-20260618-702"
        empty_checked = self.client.post(
            f"/api/production/plans/{empty_plan_id}/material-check",
            headers=self._headers(role="Production Manager", request_id=f"req-{empty_detail_scenario}"),
            json={
                "operation": "material_check",
                "idempotency_key": f"{empty_detail_scenario}-check",
                "scenario_tag": empty_detail_scenario,
                "plan_id": empty_plan_id,
                "sales_order": "SO-MB-EMPTY",
                "sales_order_item": "SOI-MB-EMPTY",
                "item_code": "ST-MB-EMPTY",
                "bom_id": 9001,
                "warehouse": "WH-MB",
                "request_id": f"req-{empty_detail_scenario}",
            },
        )
        self.assertEqual(empty_checked.status_code, 404)
        self.assertEqual(empty_checked.json()["code"], "PRODUCTION_BOM_NOT_FOUND")
