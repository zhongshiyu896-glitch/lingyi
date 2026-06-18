"""API tests for FastAPI-native style master data."""

from __future__ import annotations

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

        deactivated = self.client.post(
            f"/api/style-master/style-gallery/{gallery_id}/deactivate",
            headers=self._headers(request_id="STYLE-GALLERY-DEACTIVATE-001"),
            json={"operation": "deactivate", "company": "COMP-A", "reason": "测试停用图库"},
        )
        self.assertEqual(deactivated.status_code, 200)

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
