"""API tests for FastAPI-native image uploads."""

from __future__ import annotations

import base64
import os
from pathlib import Path
import tempfile
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
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.upload import get_db_session as upload_db_dep


class UploadApiTest(unittest.TestCase):
    """Validate image upload persistence, auth and audit."""

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
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[upload_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(upload_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        self.upload_tmp = tempfile.TemporaryDirectory()
        os.environ["LINGYI_UPLOAD_DIR"] = self.upload_tmp.name
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.commit()

    def tearDown(self) -> None:
        self.upload_tmp.cleanup()

    @staticmethod
    def _headers(role: str = "System Manager", request_id: str = "UPLOAD-REQ-001") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "upload.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _png_bytes() -> bytes:
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
            "AAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
        )

    def test_material_image_upload_persists_file_and_audit(self) -> None:
        png_bytes = self._png_bytes()
        response = self.client.post(
            "/api/uploads/images",
            headers=self._headers(),
            data={"scope": "material"},
            files={"file": ("fabric.png", png_bytes, "image/png")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        data = body["data"]
        self.assertEqual(data["scope"], "material")
        self.assertEqual(data["original_filename"], "fabric.png")
        self.assertEqual(data["content_type"], "image/png")
        self.assertEqual(data["size"], len(png_bytes))
        self.assertTrue(data["url"].startswith("/uploads/images/material/"))
        self.assertEqual(data["thumbnail_url"], data["url"])

        stored_path = Path(self.upload_tmp.name) / data["url"].removeprefix("/uploads/")
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_bytes(), png_bytes)

        with self.SessionLocal() as session:
            audit = session.query(LyOperationAuditLog).one()
            self.assertEqual(audit.module, "uploads")
            self.assertEqual(audit.action, "upload_image")
            self.assertEqual(audit.result, "success")
            self.assertEqual(audit.resource_type, "MATERIAL")

    def test_style_gallery_image_upload_persists_file_and_audit(self) -> None:
        png_bytes = self._png_bytes()
        response = self.client.post(
            "/api/uploads/images",
            headers=self._headers(request_id="UPLOAD-REQ-GALLERY"),
            data={"scope": "style_gallery"},
            files={"file": ("style.png", png_bytes, "image/png")},
        )
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["scope"], "style_gallery")
        self.assertTrue(data["url"].startswith("/uploads/images/style_gallery/"))
        stored_path = Path(self.upload_tmp.name) / data["url"].removeprefix("/uploads/")
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.read_bytes(), png_bytes)

        with self.SessionLocal() as session:
            audit = session.query(LyOperationAuditLog).one()
            self.assertEqual(audit.result, "success")
            self.assertEqual(audit.resource_type, "STYLE_GALLERY")

    def test_upload_rejects_non_image_and_audits_failure(self) -> None:
        response = self.client.post(
            "/api/uploads/images",
            headers=self._headers(request_id="UPLOAD-REQ-002"),
            data={"scope": "material"},
            files={"file": ("not-image.txt", b"plain text", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "UPLOAD_INVALID_FILE")

        with self.SessionLocal() as session:
            audit = session.query(LyOperationAuditLog).one()
            self.assertEqual(audit.module, "uploads")
            self.assertEqual(audit.action, "upload_image")
            self.assertEqual(audit.result, "failed")
            self.assertEqual(audit.error_code, "UPLOAD_INVALID_FILE")

    def test_upload_rejects_fake_image_payload_and_does_not_store_file(self) -> None:
        response = self.client.post(
            "/api/uploads/images",
            headers=self._headers(request_id="UPLOAD-REQ-FAKE"),
            data={"scope": "material"},
            files={"file": ("fake.png", b"not a real png", "image/png")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "UPLOAD_INVALID_FILE")
        self.assertFalse(any(Path(self.upload_tmp.name).rglob("*.*")))

        with self.SessionLocal() as session:
            audit = session.query(LyOperationAuditLog).one()
            self.assertEqual(audit.result, "failed")
            self.assertEqual(audit.error_code, "UPLOAD_INVALID_FILE")
