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
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleDictionary
from app.models.style_master import LyStyleGallery
from app.models.style_master import LyStyleMaster
from app.models.style_master import LyStyleMasterIdempotency
from app.models.style_master import LyStyleSku
from app.routers.auth import get_db_session as auth_db_dep
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
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[style_master_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
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

        listed = self.client.get(
            "/api/style-master/styles?company=COMP-A",
            headers=self._headers(request_id="STYLE-SORT-LIST-001"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        style_nos = [item["ys_style_no"] for item in listed.json()["data"]["items"]]
        self.assertEqual(style_nos[:2], ["ST-SORT-002", "ST-SORT-001"])

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
        first_id = int(first.json()["data"]["id"])
        second_id = int(second.json()["data"]["id"])

        with self.SessionLocal() as session:
            rows = session.query(LyStyleDictionary).filter(LyStyleDictionary.id.in_([first_id, second_id])).all()
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
        self.assertEqual(codes[:2], ["SORT-BRAND-002", "SORT-BRAND-001"])

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

        gallery = self.client.post(
            "/api/style-master/style-gallery",
            headers=self._headers(request_id="STYLE-GALLERY-CREATE-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-C",
                "style_master_id": style_id,
                "image_url": "https://example.test/style-main.jpg",
                "thumbnail_url": "https://example.test/style-main-thumb.jpg",
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
                "image_url": "https://example.test/style-main.jpg",
                "thumbnail_url": "https://example.test/style-main-thumb.jpg",
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
                "image_url": "https://example.test/style-other.jpg",
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
        self.assertEqual(style_item["primary_thumbnail_url"], "https://example.test/style-main-thumb.jpg")
        self.assertEqual(style_item["primary_image_url"], "https://example.test/style-main.jpg")
        self.assertEqual(style_item["gallery_count"], 1)

        updated_gallery = self.client.patch(
            f"/api/style-master/style-gallery/{gallery_id}",
            headers=self._headers(request_id="STYLE-GALLERY-UPDATE-001"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-U",
                "image_url": "https://example.test/style-main-updated.jpg",
                "thumbnail_url": "https://example.test/style-main-updated-thumb.jpg",
                "image_name": "主图更新",
                "image_type": "detail",
                "is_primary": True,
            },
        )
        self.assertEqual(updated_gallery.status_code, 200)
        self.assertEqual(updated_gallery.json()["data"]["image_url"], "https://example.test/style-main-updated.jpg")
        update_retry = self.client.patch(
            f"/api/style-master/style-gallery/{gallery_id}",
            headers=self._headers(request_id="STYLE-GALLERY-UPDATE-001-R"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-ST-GAL-001-G-U",
                "image_url": "https://example.test/style-main-updated.jpg",
                "thumbnail_url": "https://example.test/style-main-updated-thumb.jpg",
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
                "image_url": "https://example.test/sort-first.jpg",
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
                "image_url": "https://example.test/sort-second.jpg",
                "image_name": "后建图库",
                "image_type": "other",
                "is_primary": False,
            },
        )
        self.assertEqual(second.status_code, 201)
        first_id = int(first.json()["data"]["id"])
        second_id = int(second.json()["data"]["id"])
        with self.SessionLocal() as session:
            rows = session.query(LyStyleGallery).filter(LyStyleGallery.id.in_([first_id, second_id])).all()
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
        self.assertEqual(listed_ids[:2], [second_id, first_id])

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
