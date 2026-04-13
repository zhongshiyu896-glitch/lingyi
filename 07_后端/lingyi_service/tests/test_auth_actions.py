"""Auth action aggregation and frontend exposure guard tests (TASK-003F)."""

from __future__ import annotations

import os
from pathlib import Path
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.routers.auth import get_db_session as auth_db_dep


class AuthActionsTest(unittest.TestCase):
    """Validate workshop action response and frontend internal-entry guard."""

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
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"

    @staticmethod
    def _headers(user: str = "auth.user", role: str = "Workshop Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": user, "X-LY-Dev-Roles": role}

    def test_auth_actions_hide_job_card_sync_worker_for_normal_user(self) -> None:
        response = self.client.get("/api/auth/actions?module=workshop", headers=self._headers(role="Workshop Manager"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        actions = set(payload["data"]["actions"])
        self.assertNotIn("workshop:job_card_sync_worker", actions)

    def test_auth_actions_hide_subcontract_stock_sync_worker_for_normal_user(self) -> None:
        response = self.client.get("/api/auth/actions?module=subcontract", headers=self._headers(role="Subcontract Manager"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        actions = set(payload["data"]["actions"])
        self.assertIn("subcontract:create", actions)
        self.assertNotIn("subcontract:stock_sync_worker", actions)

    def test_frontend_has_no_internal_worker_business_entry(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        frontend_src = project_root / "06_前端" / "lingyi-pc" / "src"
        self.assertTrue(frontend_src.exists())

        forbidden_api = "/api/workshop/internal/job-card-sync/run-once"
        check_dirs = [frontend_src / "views", frontend_src / "router", frontend_src / "stores"]
        for target in check_dirs:
            if not target.exists():
                continue
            for file_path in target.rglob("*"):
                if file_path.suffix not in {".ts", ".vue", ".js"}:
                    continue
                content = file_path.read_text(encoding="utf-8")
                self.assertNotIn(forbidden_api, content, msg=f"unexpected internal worker entry: {file_path}")

    def test_frontend_src_does_not_reference_skipped_forbidden_count(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        frontend_src = project_root / "06_前端" / "lingyi-pc" / "src"
        self.assertTrue(frontend_src.exists())

        for file_path in frontend_src.rglob("*"):
            if file_path.suffix not in {".ts", ".vue", ".js"}:
                continue
            content = file_path.read_text(encoding="utf-8")
            self.assertNotIn("skipped_forbidden_count", content, msg=f"unexpected legacy field use: {file_path}")
            self.assertNotIn("skippedForbiddenCount", content, msg=f"unexpected legacy field use: {file_path}")

    def test_frontend_src_does_not_reference_skipped_forbidden(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        frontend_src = project_root / "06_前端" / "lingyi-pc" / "src"
        self.assertTrue(frontend_src.exists())

        for file_path in frontend_src.rglob("*"):
            if file_path.suffix not in {".ts", ".vue", ".js"}:
                continue
            content = file_path.read_text(encoding="utf-8")
            self.assertNotIn("skipped_forbidden", content, msg=f"unexpected legacy field use: {file_path}")
            self.assertNotIn("skippedForbidden", content, msg=f"unexpected legacy field use: {file_path}")


if __name__ == "__main__":
    unittest.main()
