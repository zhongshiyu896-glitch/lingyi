"""HTTP write coverage for legacy `/api/bom` routes."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from decimal import Decimal
import os
import unittest

os.environ["APP_ENV"] = "development"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.error_codes import WORKSHOP_IDEMPOTENCY_CONFLICT
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyApparelBomWriteOperation
from app.models.bom import LyBomOperation
from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep


class BomApiWriteFlowTest(unittest.TestCase):
    """Validate BOM writes through FastAPI envelopes, auth, audit and carrier gate."""

    COMPANY = "COMP-BOM-API"
    SCENARIO = "Z002-BOM-20260620-001"

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
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[bom_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyApparelBomWriteOperation).delete()
            session.query(LyBomOperation).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.query(LyStyleMaster).delete()
            session.commit()

    @staticmethod
    def _carrier_code(value: object) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-4:]

    @classmethod
    def _request_id(cls, *, item_code: str, bom_ref: str, reason: str | None = None) -> str:
        reason_ref = reason or "NONE"
        return (
            f"{cls.SCENARIO}-RQ-"
            f"I{cls._carrier_code(item_code)}-"
            f"B{cls._carrier_code(bom_ref)}-"
            f"R{cls._carrier_code(reason_ref)}"
        )

    @classmethod
    def _headers(
        cls,
        *,
        item_code: str,
        bom_ref: str,
        reason: str | None = None,
        role: str = "BOM Editor",
    ) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "bom.api.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": cls._request_id(item_code=item_code, bom_ref=bom_ref, reason=reason),
        }

    @classmethod
    def _style(cls, style_no: str) -> LyStyleMaster:
        return LyStyleMaster(
            company=cls.COMPANY,
            ys_style_no=style_no,
            ys_style_name_cn=f"{style_no} 款式",
            ys_season="SS",
            ys_year="2026",
            ys_brand="LY",
            ys_style_status="enabled",
            colors=[{"ys_color_code": "BLK", "ys_color_name": "黑"}],
            sizes=[{"ys_size_code": "M", "ys_size_name": "M"}],
            version=1,
            created_by="seed",
            updated_by="seed",
        )

    @classmethod
    def _create_payload(cls, *, item_code: str, source_ref: str, idem: str = "create") -> dict[str, object]:
        return {
            "scenario_tag": cls.SCENARIO,
            "idempotency_key": f"{cls.SCENARIO}:{idem}:{item_code}",
            "source_ref": source_ref,
            "company": cls.COMPANY,
            "item_code": item_code,
            "version_no": "V1",
            "bom_items": [
                {
                    "material_item_code": "MAT-BOM-API",
                    "qty_per_piece": "1.25",
                    "loss_rate": "0.05",
                    "uom": "米",
                }
            ],
            "operations": [
                {
                    "process_name": "车缝",
                    "sequence_no": 1,
                    "is_subcontract": False,
                    "wage_rate": "1.20",
                }
            ],
        }

    @classmethod
    def _carrier_payload(cls, *, item_code: str, bom_no: str, idem: str, reason: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "scenario_tag": cls.SCENARIO,
            "idempotency_key": f"{cls.SCENARIO}:{idem}:{item_code}",
            "source_ref": bom_no,
            "bom_no": bom_no,
            "company": cls.COMPANY,
            "item_code": item_code,
        }
        if reason is not None:
            payload["reason"] = reason
        return payload

    def _seed_style(self, style_no: str) -> None:
        with self.SessionLocal() as session:
            session.add(self._style(style_no))
            session.commit()

    def test_list_bom_orders_by_newest_created_not_largest_id(self) -> None:
        newer_item_code = "STYLE-BOM-LIST-NEWER"
        newer_tie_item_code = "STYLE-BOM-LIST-NEWER-TIE"
        older_item_code = "STYLE-BOM-LIST-OLDER"
        with self.SessionLocal() as session:
            session.add_all([self._style(newer_item_code), self._style(newer_tie_item_code), self._style(older_item_code)])
            session.add(
                LyApparelBom(
                    bom_no="BOM-LIST-NEWER-CREATED",
                    company=self.COMPANY,
                    item_code=newer_item_code,
                    version_no="V1",
                    is_default=False,
                    status="draft",
                    created_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.flush()
            session.add(
                LyApparelBom(
                    bom_no="BOM-LIST-NEWER-CREATED-HIGHER-ID",
                    company=self.COMPANY,
                    item_code=newer_tie_item_code,
                    version_no="V1",
                    is_default=False,
                    status="draft",
                    created_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.flush()
            session.add(
                LyApparelBom(
                    bom_no="BOM-LIST-OLDER-CREATED-LARGER-ID",
                    company=self.COMPANY,
                    item_code=older_item_code,
                    version_no="V1",
                    is_default=False,
                    status="draft",
                    created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

        response = self.client.get(
            f"/api/bom/?company={self.COMPANY}",
            headers=self._headers(item_code=newer_item_code, bom_ref="BOM-LIST", role="System Manager"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 3)
        self.assertEqual(
            [item["bom_no"] for item in payload["items"]],
            ["BOM-LIST-NEWER-CREATED-HIGHER-ID", "BOM-LIST-NEWER-CREATED", "BOM-LIST-OLDER-CREATED-LARGER-ID"],
        )

    def test_explode_uses_size_ratio_for_size_rows_and_order_qty_for_common_rows(self) -> None:
        style_no = "STYLE-BOM-EXPLODE-SIZE"
        bom_no = f"{self.SCENARIO}:BOM-EXPLODE-SIZE-RATIO"
        with self.SessionLocal() as session:
            session.add(self._style(style_no))
            bom = LyApparelBom(
                bom_no=bom_no,
                company=self.COMPANY,
                item_code=style_no,
                version_no="V1",
                is_default=True,
                status="active",
                created_by="seed",
                updated_by="seed",
            )
            session.add(bom)
            session.flush()
            session.add_all(
                [
                    LyApparelBomItem(
                        bom_id=int(bom.id),
                        material_item_code="MAT-SIZE-S",
                        color="黑",
                        part="面料主身",
                        size="S",
                        qty_per_piece=Decimal("1.0"),
                        loss_rate=Decimal("0.1"),
                        uom="米",
                    ),
                    LyApparelBomItem(
                        bom_id=int(bom.id),
                        material_item_code="MAT-SIZE-M",
                        color="黑",
                        part="面料主身",
                        size="M",
                        qty_per_piece=Decimal("2.0"),
                        loss_rate=Decimal("0"),
                        uom="米",
                    ),
                    LyApparelBomItem(
                        bom_id=int(bom.id),
                        material_item_code="MAT-COMMON",
                        qty_per_piece=Decimal("0.5"),
                        loss_rate=Decimal("0"),
                        uom="个",
                    ),
                ]
            )
            session.commit()
            bom_id = int(bom.id)

        response = self.client.post(
            f"/api/bom/{bom_id}/explode",
            headers=self._headers(item_code=style_no, bom_ref=bom_no, role="System Manager"),
            json={
                "scenario_tag": self.SCENARIO,
                "idempotency_key": f"{self.SCENARIO}:explode-size-ratio:{style_no}",
                "source_ref": bom_no,
                "bom_no": bom_no,
                "item_code": style_no,
                "order_qty": "10",
                "size_ratio": {"S": "3", "M": "7"},
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        rows = {
            (row["material_item_code"], row["size"], row["part"]): Decimal(str(row["qty"]))
            for row in response.json()["data"]["material_requirements"]
        }
        self.assertEqual(rows[("MAT-SIZE-S", "S", "面料主身")], Decimal("3.300000"))
        self.assertEqual(rows[("MAT-SIZE-M", "M", "面料主身")], Decimal("14.000000"))
        self.assertEqual(rows[("MAT-COMMON", None, None)], Decimal("5.000000"))
        self.assertEqual(Decimal(str(response.json()["data"]["total_material_qty"])), Decimal("22.300000"))

    def test_material_gallery_orders_by_parent_bom_created_time(self) -> None:
        newer_item_code = "STYLE-BOM-GALLERY-NEWER"
        older_item_code = "STYLE-BOM-GALLERY-OLDER"
        with self.SessionLocal() as session:
            session.add_all([self._style(newer_item_code), self._style(older_item_code)])
            newer_bom = LyApparelBom(
                bom_no="BOM-GALLERY-NEWER-CREATED",
                company=self.COMPANY,
                item_code=newer_item_code,
                version_no="V1",
                is_default=False,
                status="draft",
                created_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(newer_bom)
            session.flush()
            session.add(
                LyApparelBomItem(
                    bom_id=int(newer_bom.id),
                    material_item_code="FAB-GALLERY-NEWER",
                    color="黑",
                    size="M",
                    qty_per_piece=Decimal("1.00"),
                    loss_rate=Decimal("0.00"),
                    uom="米",
                    remark="面料",
                )
            )
            older_bom = LyApparelBom(
                bom_no="BOM-GALLERY-OLDER-CREATED-LARGER-ID",
                company=self.COMPANY,
                item_code=older_item_code,
                version_no="V1",
                is_default=False,
                status="draft",
                created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(older_bom)
            session.flush()
            session.add(
                LyApparelBomItem(
                    bom_id=int(older_bom.id),
                    material_item_code="FAB-GALLERY-OLDER",
                    color="白",
                    size="M",
                    qty_per_piece=Decimal("1.00"),
                    loss_rate=Decimal("0.00"),
                    uom="米",
                    remark="面料",
                )
            )
            session.commit()

        response = self.client.get(
            "/api/bom/material-gallery?page=1&page_size=20",
            headers=self._headers(item_code=newer_item_code, bom_ref="BOM-GALLERY", role="System Manager"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 2)
        self.assertEqual(
            [item["bom_no"] for item in payload["items"]],
            ["BOM-GALLERY-NEWER-CREATED", "BOM-GALLERY-OLDER-CREATED-LARGER-ID"],
        )

    def test_processing_types_order_by_parent_bom_created_time(self) -> None:
        newer_item_code = "STYLE-BOM-PROC-NEWER"
        older_item_code = "STYLE-BOM-PROC-OLDER"
        with self.SessionLocal() as session:
            session.add_all([self._style(newer_item_code), self._style(older_item_code)])
            newer_bom = LyApparelBom(
                bom_no="BOM-PROC-NEWER-CREATED",
                company=self.COMPANY,
                item_code=newer_item_code,
                version_no="V1",
                is_default=False,
                status="draft",
                created_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(newer_bom)
            session.flush()
            session.add(
                LyBomOperation(
                    bom_id=int(newer_bom.id),
                    process_name="新 BOM 工序",
                    sequence_no=10,
                    is_subcontract=False,
                    wage_rate=Decimal("1.00"),
                )
            )
            older_bom = LyApparelBom(
                bom_no="BOM-PROC-OLDER-CREATED-LARGER-ID",
                company=self.COMPANY,
                item_code=older_item_code,
                version_no="V1",
                is_default=False,
                status="draft",
                created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(older_bom)
            session.flush()
            session.add(
                LyBomOperation(
                    bom_id=int(older_bom.id),
                    process_name="旧 BOM 工序",
                    sequence_no=1,
                    is_subcontract=False,
                    wage_rate=Decimal("1.00"),
                )
            )
            session.commit()

        response = self.client.get(
            "/api/bom/processing-types?page=1&page_size=20",
            headers=self._headers(item_code=newer_item_code, bom_ref="BOM-PROC", role="System Manager"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 2)
        self.assertEqual(
            [item["bom_no"] for item in payload["items"]],
            ["BOM-PROC-NEWER-CREATED", "BOM-PROC-OLDER-CREATED-LARGER-ID"],
        )

    def test_material_units_order_by_parent_bom_created_time(self) -> None:
        newer_item_code = "STYLE-BOM-UNIT-NEWER"
        older_item_code = "STYLE-BOM-UNIT-OLDER"
        with self.SessionLocal() as session:
            session.add_all([self._style(newer_item_code), self._style(older_item_code)])
            newer_bom = LyApparelBom(
                bom_no="BOM-UNIT-NEWER-CREATED",
                company=self.COMPANY,
                item_code=newer_item_code,
                version_no="V1",
                is_default=False,
                status="draft",
                created_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(newer_bom)
            session.flush()
            session.add(
                LyApparelBomItem(
                    bom_id=int(newer_bom.id),
                    material_item_code="MAT-UNIT-NEWER",
                    qty_per_piece=Decimal("1.00"),
                    loss_rate=Decimal("0.00"),
                    uom="米",
                )
            )
            older_bom = LyApparelBom(
                bom_no="BOM-UNIT-OLDER-CREATED-LARGER-ID",
                company=self.COMPANY,
                item_code=older_item_code,
                version_no="V1",
                is_default=False,
                status="draft",
                created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(older_bom)
            session.flush()
            session.add(
                LyApparelBomItem(
                    bom_id=int(older_bom.id),
                    material_item_code="MAT-UNIT-OLDER",
                    qty_per_piece=Decimal("1.00"),
                    loss_rate=Decimal("0.00"),
                    uom="个",
                )
            )
            session.commit()

        response = self.client.get(
            "/api/bom/material-units?page=1&page_size=20",
            headers=self._headers(item_code=newer_item_code, bom_ref="BOM-UNIT", role="System Manager"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 2)
        self.assertEqual(
            [item["bom_no"] for item in payload["items"]],
            ["BOM-UNIT-NEWER-CREATED", "BOM-UNIT-OLDER-CREATED-LARGER-ID"],
        )

    def test_purchase_orders_order_by_purchase_created_time(self) -> None:
        with self.SessionLocal() as session:
            newer_order = LyMaterialPurchaseOrder(
                company=self.COMPANY,
                purchase_no="PO-BOM-NEWER-CREATED",
                supplier_name="新采购供应商",
                status="draft",
                total_qty=Decimal("2"),
                received_qty=Decimal("0"),
                total_amount=Decimal("20"),
                created_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
                updated_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(newer_order)
            session.flush()
            session.add(
                LyMaterialPurchaseOrderItem(
                    order_id=int(newer_order.id),
                    company=self.COMPANY,
                    item_code="STYLE-PO-NEWER",
                    material_item_code="MAT-PO-NEWER",
                    material_name="新采购物料",
                    qty=Decimal("2"),
                    received_qty=Decimal("0"),
                    uom="米",
                    unit_price=Decimal("10"),
                    amount=Decimal("20"),
                )
            )
            older_order = LyMaterialPurchaseOrder(
                company=self.COMPANY,
                purchase_no="PO-BOM-OLDER-CREATED-LARGER-ID",
                supplier_name="旧采购供应商",
                status="draft",
                total_qty=Decimal("1"),
                received_qty=Decimal("0"),
                total_amount=Decimal("9"),
                created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
                created_by="seed",
                updated_by="seed",
            )
            session.add(older_order)
            session.flush()
            session.add(
                LyMaterialPurchaseOrderItem(
                    order_id=int(older_order.id),
                    company=self.COMPANY,
                    item_code="STYLE-PO-OLDER",
                    material_item_code="MAT-PO-OLDER",
                    material_name="旧采购物料",
                    qty=Decimal("1"),
                    received_qty=Decimal("0"),
                    uom="个",
                    unit_price=Decimal("9"),
                    amount=Decimal("9"),
                )
            )
            session.commit()

        response = self.client.get(
            "/api/bom/purchase-orders?page=1&page_size=20",
            headers=self._headers(item_code="STYLE-PO-NEWER", bom_ref="PO-BOM", role="System Manager"),
        )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 2)
        self.assertEqual(
            [item["purchase_no"] for item in payload["items"]],
            ["PO-BOM-NEWER-CREATED", "PO-BOM-OLDER-CREATED-LARGER-ID"],
        )

    def test_create_bom_http_success_and_idempotent_replay(self) -> None:
        item_code = "STYLE-BOM-API-001"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        self._seed_style(item_code)
        payload = self._create_payload(item_code=item_code, source_ref=source_ref)

        created = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=payload,
        )
        duplicate = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=payload,
        )

        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["code"], "0")
        self.assertTrue(created.json()["data"]["name"].startswith("BOM-STYLE-BOM-API-001-V1-"))
        self.assertEqual(duplicate.status_code, 200, duplicate.text)
        self.assertEqual(duplicate.json()["data"], created.json()["data"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyApparelBom).count(), 1)
            self.assertEqual(session.query(LyApparelBomItem).count(), 1)
            self.assertEqual(session.query(LyBomOperation).count(), 1)
            self.assertEqual(session.query(LyApparelBomWriteOperation).count(), 1)
            self.assertIn("bom:create", {row.action for row in session.query(LyOperationAuditLog).all()})

    def test_create_bom_rejects_same_idempotency_key_with_different_payload(self) -> None:
        item_code = "STYLE-BOM-API-IDEM-CONFLICT"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        self._seed_style(item_code)
        payload = self._create_payload(item_code=item_code, source_ref=source_ref)
        created = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=payload,
        )
        changed_payload = {
            **payload,
            "bom_items": [{**payload["bom_items"][0], "qty_per_piece": "2.00"}],
        }
        rejected = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=changed_payload,
        )

        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()["code"], WORKSHOP_IDEMPOTENCY_CONFLICT)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyApparelBom).count(), 1)
            self.assertEqual(session.query(LyApparelBomWriteOperation).count(), 1)

    def test_create_bom_rejects_carrier_mismatch_without_writing(self) -> None:
        item_code = "STYLE-BOM-API-GATE"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        self._seed_style(item_code)
        payload = self._create_payload(item_code=item_code, source_ref=source_ref)

        rejected = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=f"{source_ref}:WRONG"),
            json=payload,
        )

        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()["code"], WORKSHOP_IDEMPOTENCY_CONFLICT)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyApparelBom).count(), 0)
            self.assertEqual(session.query(LyOperationAuditLog).count(), 0)

    def test_update_bom_draft_is_idempotent_and_conflicts_on_payload_change(self) -> None:
        item_code = f"STYLE-{self.SCENARIO}-UPDATE"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        self._seed_style(item_code)
        created = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=self._create_payload(item_code=item_code, source_ref=source_ref),
        )
        self.assertEqual(created.status_code, 200, created.text)
        bom_no = str(created.json()["data"]["name"])
        with self.SessionLocal() as session:
            bom_id = int(session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).one().id)

        update_payload = {
            **self._create_payload(item_code=item_code, source_ref=bom_no, idem="update"),
            "bom_no": bom_no,
            "version_no": "V2",
        }
        updated = self.client.put(
            f"/api/bom/{bom_id}",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=update_payload,
        )
        replayed = self.client.put(
            f"/api/bom/{bom_id}",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=update_payload,
        )
        changed_payload = {
            **update_payload,
            "bom_items": [{**update_payload["bom_items"][0], "qty_per_piece": "2.50"}],
        }
        rejected = self.client.put(
            f"/api/bom/{bom_id}",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=changed_payload,
        )

        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(replayed.status_code, 200, replayed.text)
        self.assertEqual(replayed.json()["data"], updated.json()["data"])
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()["code"], WORKSHOP_IDEMPOTENCY_CONFLICT)
        with self.SessionLocal() as session:
            bom = session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).one()
            self.assertEqual(str(bom.version_no), "V2")
            self.assertEqual(session.query(LyApparelBomWriteOperation).count(), 2)

    def test_activate_and_deactivate_http_success_then_idempotent_replay(self) -> None:
        item_code = f"STYLE-{self.SCENARIO}-ACT"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        reason = f"{self.SCENARIO}:retire api bom"
        self._seed_style(item_code)
        created = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=self._create_payload(item_code=item_code, source_ref=source_ref),
        )
        self.assertEqual(created.status_code, 200, created.text)
        bom_no = str(created.json()["data"]["name"])
        with self.SessionLocal() as session:
            bom_id = int(session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).one().id)

        activate_payload = self._carrier_payload(item_code=item_code, bom_no=bom_no, idem="activate")
        activated = self.client.post(
            f"/api/bom/{bom_id}/activate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=activate_payload,
        )
        activate_again = self.client.post(
            f"/api/bom/{bom_id}/activate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=activate_payload,
        )
        set_default_payload = self._carrier_payload(item_code=item_code, bom_no=bom_no, idem="set-default")
        set_default = self.client.post(
            f"/api/bom/{bom_id}/set-default",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=set_default_payload,
        )
        set_default_again = self.client.post(
            f"/api/bom/{bom_id}/set-default",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=set_default_payload,
        )
        deactivate_payload = self._carrier_payload(
            item_code=item_code,
            bom_no=bom_no,
            idem="deactivate",
            reason=reason,
        )
        deactivated = self.client.post(
            f"/api/bom/{bom_id}/deactivate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, reason=reason, role="System Manager"),
            json=deactivate_payload,
        )
        deactivate_again = self.client.post(
            f"/api/bom/{bom_id}/deactivate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, reason=reason, role="System Manager"),
            json=deactivate_payload,
        )

        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertEqual(activated.json()["data"]["status"], "active")
        self.assertEqual(activate_again.status_code, 200, activate_again.text)
        self.assertEqual(activate_again.json()["data"], activated.json()["data"])
        self.assertEqual(set_default.status_code, 200, set_default.text)
        self.assertTrue(set_default.json()["data"]["is_default"])
        self.assertEqual(set_default_again.status_code, 200, set_default_again.text)
        self.assertEqual(set_default_again.json()["data"], set_default.json()["data"])
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertEqual(deactivated.json()["data"]["status"], "inactive")
        self.assertEqual(deactivate_again.status_code, 200, deactivate_again.text)
        self.assertEqual(deactivate_again.json()["data"], deactivated.json()["data"])
        with self.SessionLocal() as session:
            bom = session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).one()
            self.assertEqual(str(bom.status), "inactive")
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("bom:create", audit_actions)
            self.assertIn("bom:activate", audit_actions)
            self.assertIn("bom:deactivate", audit_actions)
            self.assertIn("bom:set_default", audit_actions)
            self.assertEqual(session.query(LyApparelBomWriteOperation).count(), 4)


if __name__ == "__main__":
    unittest.main()
