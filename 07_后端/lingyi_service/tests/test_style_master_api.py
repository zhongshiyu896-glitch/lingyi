"""API tests for FastAPI-native style master data."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
import os
import unittest

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
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.recycle_bin import Base as RecycleBinBase
from app.models.recycle_bin import LyRecycleBinItem
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleDictionary
from app.models.style_master import LyStyleGallery
from app.models.style_master import LyStyleMaster
from app.models.style_master import LyStyleMasterIdempotency
from app.models.style_master import LyStyleSku
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.recycle_bin import get_db_session as recycle_bin_db_dep
from app.routers.style_master import get_db_session as style_master_db_dep


class StyleMasterApiTest(unittest.TestCase):
    """Validate style master true DB writes, auth, audit and idempotency."""

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
        RecycleBinBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)
        BomBase.metadata.create_all(bind=cls.engine)
        MasterDataBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[recycle_bin_db_dep] = _override_db
        app.dependency_overrides[style_master_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(recycle_bin_db_dep, None)
        app.dependency_overrides.pop(style_master_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyRecycleBinItem).delete()
            session.query(LyApparelBomWriteOperation).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.query(LyMasterDataRecord).delete()
            session.query(LyStyleMasterIdempotency).delete()
            session.query(LyStyleSku).delete()
            session.query(LyStyleGallery).delete()
            session.query(LyStyleMaster).delete()
            session.query(LyStyleDictionary).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "System Manager", request_id: str = "STYLE-MASTER-REQ-001") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "style.master.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _dictionary_payload(dict_type: str, code: str, name: str, idempotency_key: str) -> dict:
        return {
            "operation": "create",
            "company": "COMP-A",
            "dict_type": dict_type,
            "code": code,
            "name": name,
            "sort_no": 10,
            "idempotency_key": idempotency_key,
        }

    @staticmethod
    def _style_payload(style_no: str = "ST-A3-001", idempotency_key: str = "IDEMP-ST-A3-001-C") -> dict:
        return {
            "operation": "create",
            "company": "COMP-A",
            "ys_style_no": style_no,
            "ys_style_name_cn": "A3 最小款式",
            "ys_season": "SPRING",
            "ys_year": "2026",
            "ys_brand": "LY",
            "ys_style_status": "draft",
            "colors": [
                {"ys_color_code": "BLK", "ys_color_name": "黑"},
                {"ys_color_code": "WHT", "ys_color_name": "白"},
            ],
            "sizes": [
                {"ys_size_code": "S", "ys_size_name": "S"},
                {"ys_size_code": "M", "ys_size_name": "M"},
            ],
            "idempotency_key": idempotency_key,
        }

    def _seed_style_dictionaries(self) -> None:
        for index, (dict_type, code, name) in enumerate(
            [
                ("season", "SPRING", "春季"),
                ("year", "2026", "2026"),
                ("brand", "LY", "领意"),
                ("color", "BLK", "黑色"),
                ("color", "WHT", "白色"),
                ("size", "S", "S"),
                ("size", "M", "M"),
            ],
            start=1,
        ):
            response = self.client.post(
                "/api/style-master/dictionaries",
                headers=self._headers(request_id=f"STYLE-DICT-SEED-{index}"),
                json=self._dictionary_payload(dict_type, code, name, f"IDEMP-DICT-{dict_type}-{code}"),
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["code"], "0")

    def _seed_material_records(self) -> None:
        material_rows = [
            ("ACC-POCKET-ZIP", "口袋拉链", "拉链"),
            ("ACC-FRONT-PLACKET", "华丰门襟", "门襟"),
            ("ACC-HORN-BUTTON", "牛角扣", "纽扣"),
            ("ACC-HANGTAG", "吊牌", "吊牌"),
        ]
        with self.SessionLocal() as session:
            for code, name, part in material_rows:
                session.add(
                    LyMasterDataRecord(
                        entity_type="material",
                        company="COMP-A",
                        code=code,
                        name=name,
                        status="active",
                        payload={"material_kind": "accessory", "default_part": part, "uom": "个"},
                        created_by="style.master.user",
                    )
                )
            session.commit()

    def test_dictionary_and_style_create_update_deactivate_with_audit(self) -> None:
        self._seed_style_dictionaries()

        dictionaries = self.client.get(
            "/api/style-master/dictionaries?company=COMP-A&dict_type=season",
            headers=self._headers(request_id="STYLE-DICT-LIST-001"),
        )
        self.assertEqual(dictionaries.status_code, 200)
        self.assertEqual(dictionaries.json()["data"]["total"], 1)

        created = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-CREATE-001"),
            json=self._style_payload(),
        )
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["ys_style_no"], "ST-A3-001")
        self.assertEqual(body["data"]["ys_brand"], "LY")
        self.assertEqual(body["data"]["colors"][0]["ys_color_code"], "BLK")
        self.assertEqual(body["data"]["colors"][0]["ys_color_name"], "黑色")
        style_id = int(body["data"]["id"])

        listed = self.client.get(
            "/api/style-master/styles?company=COMP-A&keyword=ST-A3",
            headers=self._headers(request_id="STYLE-LIST-001"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)

        updated = self.client.patch(
            f"/api/style-master/styles/{style_id}",
            headers=self._headers(request_id="STYLE-UPDATE-001"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "ys_style_name_cn": "A3 最小款式修改",
                "ys_style_status": "enabled",
                "idempotency_key": "IDEMP-ST-A3-001-U",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["ys_style_name_cn"], "A3 最小款式修改")
        self.assertEqual(updated.json()["data"]["ys_style_status"], "enabled")

        deactivated = self.client.post(
            f"/api/style-master/styles/{style_id}/deactivate",
            headers=self._headers(request_id="STYLE-DEACTIVATE-001"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "reason": "A3 测试停用",
                "idempotency_key": "IDEMP-ST-A3-001-D",
            },
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertEqual(deactivated.json()["data"]["ys_style_status"], "disabled")

        with self.SessionLocal() as session:
            row = session.query(LyStyleMaster).one()
            self.assertEqual(row.ys_style_status, "disabled")
            self.assertEqual(row.ys_brand, "LY")
            self.assertEqual(session.query(LyStyleDictionary).count(), 7)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "style_master").count(), 10)

    def test_style_list_can_filter_by_style_id_for_gallery_deep_link(self) -> None:
        self._seed_style_dictionaries()

        first = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-ID-FILTER-CREATE-001"),
            json=self._style_payload(style_no="ST-ID-FILTER-001", idempotency_key="IDEMP-ST-ID-FILTER-001-C"),
        )
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-ID-FILTER-CREATE-002"),
            json=self._style_payload(style_no="ST-ID-FILTER-002", idempotency_key="IDEMP-ST-ID-FILTER-002-C"),
        )
        self.assertEqual(second.status_code, 201)
        second_id = int(second.json()["data"]["id"])

        listed = self.client.get(
            f"/api/style-master/styles?company=COMP-A&style_id={second_id}&status=all",
            headers=self._headers(request_id="STYLE-ID-FILTER-LIST-001"),
        )
        self.assertEqual(listed.status_code, 200)
        body = listed.json()["data"]
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["id"], second_id)
        self.assertEqual(body["items"][0]["ys_style_no"], "ST-ID-FILTER-002")

    def test_style_material_bom_items_persist_sequence_order(self) -> None:
        self._seed_style_dictionaries()
        self._seed_material_records()

        created = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-BOM-SORT-CREATE"),
            json=self._style_payload(style_no="ST-BOM-SORT-001", idempotency_key="IDEMP-ST-BOM-SORT-001-C"),
        )
        self.assertEqual(created.status_code, 201)
        style_id = int(created.json()["data"]["id"])

        sorted_items = [
            ("ACC-FRONT-PLACKET", "M", "门襟", 10),
            ("ACC-FRONT-PLACKET", "L", "门襟", 11),
            ("ACC-POCKET-ZIP", "M", "口袋", 20),
            ("ACC-HORN-BUTTON", "M", "纽扣", 30),
            ("ACC-HANGTAG", "M", "吊牌", 40),
        ]
        payload = {
            "operation": "upsert",
            "company": "COMP-A",
            "idempotency_key": "IDEMP-ST-BOM-SORT-001-U",
            "version_no": "V1",
            "items": [
                {
                    "sequence_no": sequence_no,
                    "material_item_code": material_code,
                    "color": "通用",
                    "size": size,
                    "part": part,
                    "qty_per_piece": "1",
                    "usage_count": "1",
                    "spec_by_size": {size: "1"},
                    "loss_rate": "0",
                    "uom": "个",
                    "remark": None,
                }
                for material_code, size, part, sequence_no in sorted_items
            ],
        }
        saved = self.client.put(
            f"/api/style-master/styles/{style_id}/material-bom",
            headers=self._headers(request_id="STYLE-BOM-SORT-SAVE"),
            json=payload,
        )
        self.assertEqual(saved.status_code, 200)
        saved_items = saved.json()["data"]["items"]
        self.assertEqual([item["material_item_code"] for item in saved_items], [item[0] for item in sorted_items])
        self.assertEqual([item["sequence_no"] for item in saved_items], [item[3] for item in sorted_items])

        persisted = self.client.get(
            f"/api/style-master/styles/{style_id}/material-bom?company=COMP-A",
            headers=self._headers(request_id="STYLE-BOM-SORT-GET"),
        )
        self.assertEqual(persisted.status_code, 200)
        persisted_items = persisted.json()["data"]["items"]
        self.assertEqual([item["material_name"] for item in persisted_items[:4]], ["华丰门襟", "华丰门襟", "口袋拉链", "牛角扣"])
        self.assertEqual([item["material_item_code"] for item in persisted_items], [item[0] for item in sorted_items])
        self.assertEqual([item["sequence_no"] for item in persisted_items], [10, 11, 20, 30, 40])

    def test_style_size_chart_persists_syncs_columns_and_copies_with_style(self) -> None:
        self._seed_style_dictionaries()

        created = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-SIZE-CHART-CREATE"),
            json=self._style_payload(style_no="ST-SIZE-001", idempotency_key="IDEMP-ST-SIZE-001-C"),
        )
        self.assertEqual(created.status_code, 201)
        style_id = int(created.json()["data"]["id"])

        empty = self.client.get(
            f"/api/style-master/styles/{style_id}/size-chart?company=COMP-A",
            headers=self._headers(request_id="STYLE-SIZE-CHART-GET-EMPTY"),
        )
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["data"]["sizes"], ["S", "M"])
        self.assertFalse(empty.json()["data"]["has_size_chart"])

        size_chart_payload = {
            "unit": "CM",
            "sizes": ["S", "M"],
            "rows": [
                {"part": "后中", "values": {"S": "62.1", "M": "64.1"}, "sort_no": 10},
                {"part": "肩宽", "values": {"S": "45", "M": "46.5"}, "sort_no": 20},
            ],
        }
        saved = self.client.put(
            f"/api/style-master/styles/{style_id}/size-chart?company=COMP-A",
            headers=self._headers(request_id="STYLE-SIZE-CHART-SAVE"),
            json=size_chart_payload,
        )
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.json()["data"]["has_size_chart"])
        self.assertEqual(saved.json()["data"]["rows"][0]["values"]["S"], "62.1")

        persisted = self.client.get(
            f"/api/style-master/styles/{style_id}/size-chart?company=COMP-A",
            headers=self._headers(request_id="STYLE-SIZE-CHART-GET-PERSISTED"),
        )
        self.assertEqual(persisted.status_code, 200)
        persisted_chart = persisted.json()["data"]
        self.assertEqual(persisted_chart["rows"][1]["part"], "肩宽")

        listed = self.client.get(
            "/api/style-master/styles?company=COMP-A&keyword=ST-SIZE-001",
            headers=self._headers(request_id="STYLE-SIZE-CHART-LIST"),
        )
        self.assertEqual(listed.status_code, 200)
        summary = listed.json()["data"]["items"][0]["size_chart_summary"]
        self.assertTrue(summary["has_size_chart"])
        self.assertEqual(summary["row_count"], 2)

        copy_payload = self._style_payload(style_no="ST-SIZE-COPY", idempotency_key="IDEMP-ST-SIZE-COPY-C")
        copy_payload["size_chart"] = persisted_chart
        copied = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-SIZE-CHART-COPY"),
            json=copy_payload,
        )
        self.assertEqual(copied.status_code, 201)
        copied_id = int(copied.json()["data"]["id"])
        copied_chart = self.client.get(
            f"/api/style-master/styles/{copied_id}/size-chart?company=COMP-A",
            headers=self._headers(request_id="STYLE-SIZE-CHART-COPY-GET"),
        )
        self.assertEqual(copied_chart.status_code, 200)
        self.assertEqual(copied_chart.json()["data"]["rows"][0]["values"]["M"], "64.1")

        size_l = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(request_id="STYLE-SIZE-CHART-SIZE-L"),
            json=self._dictionary_payload("size", "L", "L", "IDEMP-DICT-size-L"),
        )
        self.assertEqual(size_l.status_code, 201)
        resized = self.client.patch(
            f"/api/style-master/styles/{copied_id}",
            headers=self._headers(request_id="STYLE-SIZE-CHART-RESIZE"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-SIZE-COPY-RESIZE",
                "sizes": [
                    {"ys_size_code": "M", "ys_size_name": "M"},
                    {"ys_size_code": "L", "ys_size_name": "L"},
                ],
            },
        )
        self.assertEqual(resized.status_code, 200)
        synced = self.client.get(
            f"/api/style-master/styles/{copied_id}/size-chart?company=COMP-A",
            headers=self._headers(request_id="STYLE-SIZE-CHART-SYNCED"),
        )
        self.assertEqual(synced.status_code, 200)
        synced_chart = synced.json()["data"]
        self.assertEqual(synced_chart["sizes"], ["M", "L"])
        self.assertEqual(synced_chart["rows"][0]["values"]["M"], "64.1")
        self.assertNotIn("S", synced_chart["rows"][0]["values"])

        disabled = self.client.post(
            f"/api/style-master/styles/{style_id}/deactivate",
            headers=self._headers(request_id="STYLE-SIZE-CHART-DISABLE"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-SIZE-001-D",
                "reason": "测试停用",
            },
        )
        self.assertEqual(disabled.status_code, 200)
        readonly = self.client.get(
            f"/api/style-master/styles/{style_id}/size-chart?company=COMP-A",
            headers=self._headers(request_id="STYLE-SIZE-CHART-DISABLED-READ"),
        )
        self.assertEqual(readonly.status_code, 200)
        rejected = self.client.put(
            f"/api/style-master/styles/{style_id}/size-chart?company=COMP-A",
            headers=self._headers(request_id="STYLE-SIZE-CHART-DISABLED-WRITE"),
            json=size_chart_payload,
        )
        self.assertEqual(rejected.status_code, 409)

    def test_style_list_orders_by_latest_created_not_latest_updated(self) -> None:
        self._seed_style_dictionaries()

        first = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-SORT-CREATE-001"),
            json=self._style_payload(style_no="ST-SORT-001", idempotency_key="IDEMP-ST-SORT-001-C"),
        )
        self.assertEqual(first.status_code, 201, first.text)
        first_id = int(first.json()["data"]["id"])

        second = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-SORT-CREATE-002"),
            json=self._style_payload(style_no="ST-SORT-002", idempotency_key="IDEMP-ST-SORT-002-C"),
        )
        self.assertEqual(second.status_code, 201, second.text)
        second_id = int(second.json()["data"]["id"])

        third = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-SORT-CREATE-003"),
            json=self._style_payload(style_no="ST-SORT-003", idempotency_key="IDEMP-ST-SORT-003-C"),
        )
        self.assertEqual(third.status_code, 201, third.text)
        third_id = int(third.json()["data"]["id"])

        updated_first = self.client.patch(
            f"/api/style-master/styles/{first_id}",
            headers=self._headers(request_id="STYLE-SORT-UPDATE-001"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "ys_style_name_cn": "旧款式被编辑",
                "idempotency_key": "IDEMP-ST-SORT-001-U",
            },
        )
        self.assertEqual(updated_first.status_code, 200, updated_first.text)

        with self.SessionLocal() as session:
            rows = session.query(LyStyleMaster).filter(LyStyleMaster.id.in_([first_id, second_id, third_id])).all()
            for row in rows:
                if int(row.id) == first_id:
                    row.created_at = datetime(2026, 6, 20, 8, 0, tzinfo=UTC)
                    row.updated_at = datetime(2026, 6, 22, 8, 0, tzinfo=UTC)
                else:
                    row.created_at = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
                    row.updated_at = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
            session.commit()

        listed = self.client.get(
            "/api/style-master/styles?company=COMP-A",
            headers=self._headers(request_id="STYLE-SORT-LIST-001"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        style_nos = [item["ys_style_no"] for item in listed.json()["data"]["items"]]
        self.assertEqual(style_nos[:3], ["ST-SORT-003", "ST-SORT-002", "ST-SORT-001"])

    def test_style_dictionary_list_orders_by_latest_created_not_latest_updated(self) -> None:
        first = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(request_id="STYLE-DICT-SORT-CREATE-001"),
            json=self._dictionary_payload("brand", "SORT-BRAND-001", "先建品牌", "IDEMP-DICT-SORT-001"),
        )
        self.assertEqual(first.status_code, 201, first.text)
        second = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(request_id="STYLE-DICT-SORT-CREATE-002"),
            json=self._dictionary_payload("brand", "SORT-BRAND-002", "后建品牌", "IDEMP-DICT-SORT-002"),
        )
        self.assertEqual(second.status_code, 201, second.text)
        third = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(request_id="STYLE-DICT-SORT-CREATE-003"),
            json=self._dictionary_payload("brand", "SORT-BRAND-003", "同时新建品牌", "IDEMP-DICT-SORT-003"),
        )
        self.assertEqual(third.status_code, 201, third.text)
        first_id = int(first.json()["data"]["id"])
        second_id = int(second.json()["data"]["id"])
        third_id = int(third.json()["data"]["id"])

        with self.SessionLocal() as session:
            rows = session.query(LyStyleDictionary).filter(LyStyleDictionary.id.in_([first_id, second_id, third_id])).all()
            for row in rows:
                if int(row.id) == first_id:
                    row.created_at = datetime(2026, 6, 20, 8, 0, tzinfo=UTC)
                    row.updated_at = datetime(2026, 6, 22, 8, 0, tzinfo=UTC)
                else:
                    row.created_at = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
                    row.updated_at = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
            session.commit()

        listed = self.client.get(
            "/api/style-master/dictionaries?company=COMP-A&dict_type=brand",
            headers=self._headers(request_id="STYLE-DICT-SORT-LIST-001"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        codes = [item["code"] for item in listed.json()["data"]["items"]]
        self.assertEqual(codes[:3], ["SORT-BRAND-003", "SORT-BRAND-002", "SORT-BRAND-001"])

    def test_style_dictionary_create_auto_generates_code_when_missing(self) -> None:
        payload = {
            "operation": "create",
            "company": "COMP-A",
            "dict_type": "brand",
            "name": "自动编码品牌",
            "sort_no": 10,
            "idempotency_key": "IDEMP-DICT-AUTO-CODE",
        }
        created = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(request_id="STYLE-DICT-AUTO-CREATE-001"),
            json=payload,
        )
        self.assertEqual(created.status_code, 201, created.text)
        body = created.json()["data"]
        self.assertEqual(body["code"], "BRAND-000001")
        self.assertEqual(body["name"], "自动编码品牌")

        replayed = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(request_id="STYLE-DICT-AUTO-CREATE-002"),
            json=payload,
        )
        self.assertEqual(replayed.status_code, 201, replayed.text)
        self.assertEqual(replayed.json()["data"]["code"], "BRAND-000001")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyStyleDictionary).count(), 1)

    def test_style_dictionary_delete_moves_to_recycle_bin_and_blocks_referenced(self) -> None:
        created = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(request_id="STYLE-DICT-DELETE-CREATE"),
            json=self._dictionary_payload("brand", "DEL-BRAND-001", "待删除品牌", "IDEMP-DICT-DELETE-CREATE"),
        )
        self.assertEqual(created.status_code, 201, created.text)
        dictionary_id = int(created.json()["data"]["id"])

        deleted = self.client.delete(
            f"/api/style-master/dictionaries/{dictionary_id}?company=COMP-A",
            headers=self._headers(request_id="STYLE-DICT-DELETE-OK"),
        )
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertTrue(deleted.json()["data"]["deleted"])
        self.assertEqual(deleted.json()["data"]["id"], dictionary_id)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyStyleDictionary).filter_by(code="DEL-BRAND-001").count(), 0)
            trash = session.query(LyRecycleBinItem).filter_by(module="style_master", entity_type="style_dictionary", code="DEL-BRAND-001").one()
            trash_id = int(trash.id)
            self.assertEqual(trash.status, "deleted")
            self.assertEqual(trash.original_id, dictionary_id)

        restored = self.client.post(
            f"/api/recycle-bin/{trash_id}/restore",
            headers=self._headers(request_id="STYLE-DICT-RESTORE-OK"),
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertEqual(restored.json()["data"]["status"], "restored")
        with self.SessionLocal() as session:
            restored_row = session.query(LyStyleDictionary).filter_by(company="COMP-A", dict_type="brand", code="DEL-BRAND-001").one()
            self.assertEqual(int(restored_row.id), dictionary_id)

        deleted_again = self.client.delete(
            f"/api/style-master/dictionaries/{dictionary_id}?company=COMP-A",
            headers=self._headers(request_id="STYLE-DICT-DELETE-AGAIN"),
        )
        self.assertEqual(deleted_again.status_code, 200, deleted_again.text)
        with self.SessionLocal() as session:
            purge_id = int(
                session.query(LyRecycleBinItem)
                .filter_by(module="style_master", entity_type="style_dictionary", code="DEL-BRAND-001", status="deleted")
                .one()
                .id
            )
        purged = self.client.delete(
            f"/api/recycle-bin/{purge_id}",
            headers=self._headers(request_id="STYLE-DICT-PURGE-OK"),
        )
        self.assertEqual(purged.status_code, 200, purged.text)
        self.assertTrue(purged.json()["data"]["purged"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyRecycleBinItem).filter_by(id=purge_id).count(), 0)

        self._seed_style_dictionaries()
        style = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-DICT-DELETE-STYLE"),
            json=self._style_payload(style_no="ST-DICT-REF-001", idempotency_key="IDEMP-ST-DICT-REF-001"),
        )
        self.assertEqual(style.status_code, 201, style.text)
        with self.SessionLocal() as session:
            brand_id = int(session.query(LyStyleDictionary).filter_by(company="COMP-A", dict_type="brand", code="LY").one().id)
        blocked = self.client.delete(
            f"/api/style-master/dictionaries/{brand_id}?company=COMP-A",
            headers=self._headers(request_id="STYLE-DICT-DELETE-BLOCK"),
        )
        self.assertEqual(blocked.status_code, 409, blocked.text)
        self.assertEqual(blocked.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyStyleDictionary).filter_by(company="COMP-A", dict_type="brand", code="LY").count(), 1)

    def test_style_idempotency_conflict_and_invalid_reference(self) -> None:
        self._seed_style_dictionaries()

        first = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-IDEM-001"),
            json=self._style_payload(style_no="ST-A3-IDEM", idempotency_key="IDEMP-ST-A3-IDEM"),
        )
        retry = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-IDEM-002"),
            json=self._style_payload(style_no="ST-A3-IDEM", idempotency_key="IDEMP-ST-A3-IDEM"),
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 201)
        self.assertEqual(first.json()["data"]["id"], retry.json()["data"]["id"])

        changed = self._style_payload(style_no="ST-A3-IDEM", idempotency_key="IDEMP-ST-A3-IDEM")
        changed["ys_style_name_cn"] = "changed"
        conflict = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-IDEM-003"),
            json=changed,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "STYLE_MASTER_IDEMPOTENCY_CONFLICT")

        invalid = self._style_payload(style_no="ST-A3-NO-REF", idempotency_key="IDEMP-ST-A3-NO-REF")
        invalid["ys_brand"] = "MISSING"
        invalid_ref = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-REF-001"),
            json=invalid,
        )
        self.assertEqual(invalid_ref.status_code, 409)
        self.assertEqual(invalid_ref.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

        invalid_color = self._style_payload(style_no="ST-A3-NO-COLOR", idempotency_key="IDEMP-ST-A3-NO-COLOR")
        invalid_color["colors"] = [{"ys_color_code": "NAVY", "ys_color_name": "藏青"}]
        invalid_color_ref = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-REF-002"),
            json=invalid_color,
        )
        self.assertEqual(invalid_color_ref.status_code, 409)
        self.assertEqual(invalid_color_ref.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

        invalid_size = self._style_payload(style_no="ST-A3-NO-SIZE", idempotency_key="IDEMP-ST-A3-NO-SIZE")
        invalid_size["sizes"] = [{"ys_size_code": "XL", "ys_size_name": "XL"}]
        invalid_size_ref = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-REF-003"),
            json=invalid_size,
        )
        self.assertEqual(invalid_size_ref.status_code, 409)
        self.assertEqual(invalid_size_ref.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

    def test_style_sku_matrix_upsert_validates_pairs_and_syncs_style_no(self) -> None:
        self._seed_style_dictionaries()
        created = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-SKU-STYLE-001"),
            json=self._style_payload(style_no="ST-SKU-001", idempotency_key="IDEMP-ST-SKU-001-C"),
        )
        self.assertEqual(created.status_code, 201)
        style_id = int(created.json()["data"]["id"])

        empty = self.client.get(
            f"/api/style-master/styles/{style_id}/skus?company=COMP-A",
            headers=self._headers(request_id="STYLE-SKU-LIST-000"),
        )
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.json()["data"]["total"], 0)

        payload = {
            "operation": "upsert",
            "company": "COMP-A",
            "idempotency_key": "IDEMP-ST-SKU-001-U",
            "items": [
                {"color_code": "BLK", "size_code": "S", "sku_code": "ST-SKU-001-BLK-S", "barcode": "BC-BLK-S", "sort_no": 10},
                {"color_code": "BLK", "size_code": "M", "sku_code": "ST-SKU-001-BLK-M", "sort_no": 20},
                {"color_code": "WHT", "size_code": "S", "sku_code": "ST-SKU-001-WHT-S", "sort_no": 30},
                {"color_code": "WHT", "size_code": "M", "sku_code": "ST-SKU-001-WHT-M", "sort_no": 40},
            ],
        }
        upserted = self.client.put(
            f"/api/style-master/styles/{style_id}/skus",
            headers=self._headers(request_id="STYLE-SKU-UPSERT-001"),
            json=payload,
        )
        self.assertEqual(upserted.status_code, 200)
        body = upserted.json()["data"]
        self.assertEqual(body["total"], 4)
        self.assertEqual(body["items"][0]["color_name"], "黑色")
        self.assertEqual(body["items"][0]["size_name"], "S")
        self.assertEqual(body["items"][0]["barcode"], "BC-BLK-S")

        retry = self.client.put(
            f"/api/style-master/styles/{style_id}/skus",
            headers=self._headers(request_id="STYLE-SKU-UPSERT-001-R"),
            json=payload,
        )
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json()["data"]["total"], 4)

        conflict_payload = {**payload, "items": [{**payload["items"][0], "sku_code": "CHANGED-SKU"}]}
        conflict = self.client.put(
            f"/api/style-master/styles/{style_id}/skus",
            headers=self._headers(request_id="STYLE-SKU-UPSERT-001-C"),
            json=conflict_payload,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "STYLE_MASTER_IDEMPOTENCY_CONFLICT")

        invalid_color = {**payload, "idempotency_key": "IDEMP-ST-SKU-INVALID", "items": [{**payload["items"][0], "color_code": "NAVY"}]}
        invalid = self.client.put(
            f"/api/style-master/styles/{style_id}/skus",
            headers=self._headers(request_id="STYLE-SKU-INVALID-001"),
            json=invalid_color,
        )
        self.assertEqual(invalid.status_code, 409)
        self.assertEqual(invalid.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

        reduced_payload = {
            **payload,
            "idempotency_key": "IDEMP-ST-SKU-001-U2",
            "items": payload["items"][:3],
        }
        reduced = self.client.put(
            f"/api/style-master/styles/{style_id}/skus",
            headers=self._headers(request_id="STYLE-SKU-UPSERT-002"),
            json=reduced_payload,
        )
        self.assertEqual(reduced.status_code, 200)
        self.assertEqual(reduced.json()["data"]["total"], 4)
        self.assertEqual(sum(1 for item in reduced.json()["data"]["items"] if item["status"] == "active"), 3)

        styles = self.client.get(
            "/api/style-master/styles?company=COMP-A&keyword=ST-SKU-001",
            headers=self._headers(request_id="STYLE-SKU-STYLES-001"),
        )
        self.assertEqual(styles.status_code, 200)
        self.assertEqual(styles.json()["data"]["items"][0]["sku_count"], 3)

        renamed = self.client.patch(
            f"/api/style-master/styles/{style_id}",
            headers=self._headers(request_id="STYLE-SKU-STYLE-RENAME"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "ys_style_no": "ST-SKU-RENAMED",
                "idempotency_key": "IDEMP-ST-SKU-RENAME",
            },
        )
        self.assertEqual(renamed.status_code, 200)
        listed = self.client.get(
            f"/api/style-master/styles/{style_id}/skus?company=COMP-A",
            headers=self._headers(request_id="STYLE-SKU-LIST-001"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertTrue(all(item["ys_style_no"] == "ST-SKU-RENAMED" for item in listed.json()["data"]["items"]))

    def test_style_gallery_linked_to_style_and_visible_on_style_list(self) -> None:
        self._seed_style_dictionaries()
        created = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-GALLERY-STYLE-001"),
            json=self._style_payload(style_no="ST-GAL-001", idempotency_key="IDEMP-ST-GAL-001-C"),
        )
        self.assertEqual(created.status_code, 201)
        style_id = int(created.json()["data"]["id"])

        external_gallery = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-CREATE-EXTERNAL-REJECT"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-EXT",
                "style_master_id": style_id,
                "image_url": "https://example.test/style-main.jpg",
                "thumbnail_url": "https://example.test/style-main-thumb.jpg",
                "image_name": "外链主图",
                "image_type": "main",
                "is_primary": True,
            },
        )
        self.assertEqual(external_gallery.status_code, 409)
        self.assertEqual(external_gallery.json()["code"], "STYLE_MASTER_INVALID_REFERENCE")

        gallery = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-CREATE-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-C",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/style-main.jpg",
                "thumbnail_url": "/uploads/images/style_gallery/style-main-thumb.jpg",
                "image_name": "主图",
                "image_type": "main",
                "is_primary": True,
            },
        )
        self.assertEqual(gallery.status_code, 201)
        gallery_body = gallery.json()["data"]
        self.assertEqual(gallery_body["ys_style_no"], "ST-GAL-001")
        self.assertEqual(gallery_body["ys_style_name_cn"], "A3 最小款式")
        self.assertTrue(gallery_body["is_primary"])
        gallery_id = int(gallery_body["id"])

        gallery_retry = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-CREATE-001-R"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-C",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/style-main.jpg",
                "thumbnail_url": "/uploads/images/style_gallery/style-main-thumb.jpg",
                "image_name": "主图",
                "image_type": "main",
                "is_primary": True,
            },
        )
        self.assertEqual(gallery_retry.status_code, 201)
        self.assertEqual(int(gallery_retry.json()["data"]["id"]), gallery_id)

        gallery_conflict = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-CREATE-001-C"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-C",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/style-other.jpg",
                "image_type": "main",
                "is_primary": True,
            },
        )
        self.assertEqual(gallery_conflict.status_code, 409)
        self.assertEqual(gallery_conflict.json()["code"], "STYLE_MASTER_IDEMPOTENCY_CONFLICT")

        listed_gallery = self.client.get(
            f"/api/style-master/style-gallery?company=COMP-A&style_id={style_id}",
            headers=self._headers(request_id="STYLE-GALLERY-LIST-001"),
        )
        self.assertEqual(listed_gallery.status_code, 200)
        self.assertEqual(listed_gallery.json()["data"]["total"], 1)
        self.assertEqual(listed_gallery.json()["data"]["items"][0]["ys_style_no"], "ST-GAL-001")

        styles = self.client.get(
            "/api/style-master/styles?company=COMP-A&keyword=ST-GAL-001",
            headers=self._headers(request_id="STYLE-GALLERY-STYLES-001"),
        )
        self.assertEqual(styles.status_code, 200)
        style_item = styles.json()["data"]["items"][0]
        self.assertEqual(style_item["primary_thumbnail_url"], "/uploads/images/style_gallery/style-main-thumb.jpg")
        self.assertEqual(style_item["primary_image_url"], "/uploads/images/style_gallery/style-main.jpg")
        self.assertEqual(style_item["gallery_count"], 1)

        second_primary = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-CREATE-PRIMARY-002"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-C-2",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/style-main-2.jpg",
                "thumbnail_url": "/uploads/images/style_gallery/style-main-2-thumb.jpg",
                "image_name": "主图2",
                "image_type": "main",
                "is_primary": True,
            },
        )
        self.assertEqual(second_primary.status_code, 201, second_primary.text)
        self.assertTrue(second_primary.json()["data"]["is_primary"])

        primary_replaced_gallery = self.client.get(
            f"/api/style-master/style-gallery?company=COMP-A&style_id={style_id}",
            headers=self._headers(request_id="STYLE-GALLERY-LIST-PRIMARY-002"),
        )
        self.assertEqual(primary_replaced_gallery.status_code, 200)
        self.assertEqual(primary_replaced_gallery.json()["data"]["total"], 2)
        gallery_by_id = {int(row["id"]): row for row in primary_replaced_gallery.json()["data"]["items"]}
        self.assertFalse(gallery_by_id[gallery_id]["is_primary"])
        self.assertTrue(gallery_by_id[int(second_primary.json()["data"]["id"])]["is_primary"])

        styles_after_primary_replace = self.client.get(
            "/api/style-master/styles?company=COMP-A&keyword=ST-GAL-001",
            headers=self._headers(request_id="STYLE-GALLERY-STYLES-PRIMARY-002"),
        )
        self.assertEqual(styles_after_primary_replace.status_code, 200)
        style_after_primary_replace = styles_after_primary_replace.json()["data"]["items"][0]
        self.assertEqual(style_after_primary_replace["primary_thumbnail_url"], "/uploads/images/style_gallery/style-main-2-thumb.jpg")
        self.assertEqual(style_after_primary_replace["primary_image_url"], "/uploads/images/style_gallery/style-main-2.jpg")
        self.assertEqual(style_after_primary_replace["gallery_count"], 2)

        updated_gallery = self.client.patch(
            f"/api/style-master/style-gallery/{gallery_id}",
            headers=self._headers(request_id="STYLE-GALLERY-UPDATE-001"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-U",
                "image_url": "/uploads/images/style_gallery/style-main-updated.jpg",
                "thumbnail_url": "/uploads/images/style_gallery/style-main-updated-thumb.jpg",
                "image_name": "主图更新",
                "image_type": "detail",
                "is_primary": True,
            },
        )
        self.assertEqual(updated_gallery.status_code, 200)
        self.assertEqual(updated_gallery.json()["data"]["image_url"], "/uploads/images/style_gallery/style-main-updated.jpg")
        update_retry = self.client.patch(
            f"/api/style-master/style-gallery/{gallery_id}",
            headers=self._headers(request_id="STYLE-GALLERY-UPDATE-001-R"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-U",
                "image_url": "/uploads/images/style_gallery/style-main-updated.jpg",
                "thumbnail_url": "/uploads/images/style_gallery/style-main-updated-thumb.jpg",
                "image_name": "主图更新",
                "image_type": "detail",
                "is_primary": True,
            },
        )
        self.assertEqual(update_retry.status_code, 200)
        self.assertEqual(int(update_retry.json()["data"]["id"]), gallery_id)

        deactivated = self.client.post(
            f"/api/style-master/style-gallery/{gallery_id}/deactivate",
            headers=self._headers(request_id="STYLE-GALLERY-DEACTIVATE-001"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-D",
                "reason": "测试停用图库",
            },
        )
        self.assertEqual(deactivated.status_code, 200)
        deactivate_retry = self.client.post(
            f"/api/style-master/style-gallery/{gallery_id}/deactivate",
            headers=self._headers(request_id="STYLE-GALLERY-DEACTIVATE-001-R"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-D",
                "reason": "测试停用图库",
            },
        )
        self.assertEqual(deactivate_retry.status_code, 200)
        self.assertEqual(int(deactivate_retry.json()["data"]["id"]), gallery_id)

        second_deactivated = self.client.post(
            f"/api/style-master/style-gallery/{int(second_primary.json()['data']['id'])}/deactivate",
            headers=self._headers(request_id="STYLE-GALLERY-DEACTIVATE-002"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-D-2",
                "reason": "测试停用第二张图库",
            },
        )
        self.assertEqual(second_deactivated.status_code, 200)

        listed_after = self.client.get(
            f"/api/style-master/style-gallery?company=COMP-A&style_id={style_id}",
            headers=self._headers(request_id="STYLE-GALLERY-LIST-002"),
        )
        self.assertEqual(listed_after.status_code, 200)
        self.assertEqual(listed_after.json()["data"]["total"], 0)

        styles_after = self.client.get(
            "/api/style-master/styles?company=COMP-A&keyword=ST-GAL-001",
            headers=self._headers(request_id="STYLE-GALLERY-STYLES-002"),
        )
        self.assertEqual(styles_after.status_code, 200)
        style_after = styles_after.json()["data"]["items"][0]
        self.assertIsNone(style_after["primary_thumbnail_url"])
        self.assertEqual(style_after["gallery_count"], 0)

    def test_style_gallery_list_orders_by_latest_created_not_latest_updated(self) -> None:
        self._seed_style_dictionaries()
        created = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-GALLERY-SORT-STYLE"),
            json=self._style_payload(style_no="ST-GAL-SORT", idempotency_key="IDEMP-ST-GAL-SORT-C"),
        )
        self.assertEqual(created.status_code, 201)
        style_id = int(created.json()["data"]["id"])

        first = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-SORT-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-SORT-001",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/sort-first.jpg",
                "image_name": "先建图库",
                "image_type": "detail",
                "is_primary": False,
            },
        )
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-SORT-002"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-SORT-002",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/sort-second.jpg",
                "image_name": "后建图库",
                "image_type": "other",
                "is_primary": False,
            },
        )
        self.assertEqual(second.status_code, 201)
        third = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-SORT-003"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-SORT-003",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/sort-third.jpg",
                "image_name": "同时间图库",
                "image_type": "other",
                "is_primary": False,
            },
        )
        self.assertEqual(third.status_code, 201)
        first_id = int(first.json()["data"]["id"])
        second_id = int(second.json()["data"]["id"])
        third_id = int(third.json()["data"]["id"])
        with self.SessionLocal() as session:
            rows = session.query(LyStyleGallery).filter(LyStyleGallery.id.in_([first_id, second_id, third_id])).all()
            for row in rows:
                if int(row.id) == first_id:
                    row.created_at = datetime(2026, 6, 20, 8, 0, tzinfo=UTC)
                    row.updated_at = datetime(2026, 6, 22, 8, 0, tzinfo=UTC)
                else:
                    row.created_at = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
                    row.updated_at = datetime(2026, 6, 21, 8, 0, tzinfo=UTC)
            session.commit()

        listed = self.client.get(
            f"/api/style-master/style-gallery?company=COMP-A&style_id={style_id}",
            headers=self._headers(request_id="STYLE-GALLERY-SORT-LIST"),
        )
        self.assertEqual(listed.status_code, 200)
        listed_ids = [int(item["id"]) for item in listed.json()["data"]["items"]]
        self.assertEqual(listed_ids[:3], [third_id, second_id, first_id])

    def test_style_gallery_supports_wash_label_image_type(self) -> None:
        self._seed_style_dictionaries()
        created = self.client.post(
            "/api/style-master/styles",
            headers=self._headers(request_id="STYLE-GALLERY-WASH-STYLE"),
            json=self._style_payload(style_no="ST-GAL-WASH", idempotency_key="IDEMP-ST-GAL-WASH-C"),
        )
        self.assertEqual(created.status_code, 201)
        style_id = int(created.json()["data"]["id"])

        wash_label = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-WASH-CREATE"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-WASH-001",
                "style_master_id": style_id,
                "image_url": "/uploads/images/style_gallery/wash-label-1.jpg",
                "thumbnail_url": "/uploads/images/style_gallery/wash-label-1-thumb.jpg",
                "image_name": "水洗标 1",
                "image_type": "wash_label",
                "is_primary": False,
            },
        )
        self.assertEqual(wash_label.status_code, 201)
        self.assertEqual(wash_label.json()["data"]["image_type"], "wash_label")

        listed = self.client.get(
            f"/api/style-master/style-gallery?company=COMP-A&style_id={style_id}&image_type=wash_label",
            headers=self._headers(request_id="STYLE-GALLERY-WASH-LIST"),
        )
        self.assertEqual(listed.status_code, 200)
        body = listed.json()["data"]
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["image_name"], "水洗标 1")

    def test_style_manage_permission_fail_closed(self) -> None:
        denied = self.client.post(
            "/api/style-master/dictionaries",
            headers=self._headers(role="Sales Manager", request_id="STYLE-DENY-001"),
            json=self._dictionary_payload("brand", "DENY", "无权品牌", "IDEMP-DICT-DENY"),
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "AUTH_FORBIDDEN")


if __name__ == "__main__":
    unittest.main()
