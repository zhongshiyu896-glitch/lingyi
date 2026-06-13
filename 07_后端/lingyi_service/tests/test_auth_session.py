"""Local auth session coverage for W003A M1 entry flow."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LINGYI_ALLOW_DEV_AUTH", "true")
os.environ.setdefault("LINGYI_ERPNEXT_BASE_URL", "")
os.environ.setdefault("LINGYI_PERMISSION_SOURCE", "static")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.routers.auth import get_db_session as auth_db_dep


class AuthSessionTest(unittest.TestCase):
    """Validate guarded local login, logout, and protected entry behavior."""

    MODULE_SCAN = [
        "dashboard",
        "bom",
        "production",
        "subcontract",
        "warehouse",
        "quality",
        "sales_inventory",
        "factory_statement",
        "report",
        "system",
    ]

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
        self.client.cookies.clear()
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

    def _login(self, *, username: str = "w003a.local", profile: str = "system_manager"):
        response = self.client.post(
            "/api/auth/login",
            json={"username": username, "profile": profile},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("lingyi_local_session", response.headers.get("set-cookie", ""))
        return response

    def test_local_login_sets_cookie_and_me_reads_session(self) -> None:
        login_response = self._login()
        payload = login_response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(payload["data"]["username"], "w003a.local")
        self.assertEqual(payload["data"]["source"], "dev_session")

        me_response = self.client.get("/api/auth/me")
        self.assertEqual(me_response.status_code, 200)
        me_payload = me_response.json()
        self.assertEqual(me_payload["code"], "0")
        self.assertEqual(me_payload["data"]["username"], "w003a.local")
        self.assertEqual(me_payload["data"]["roles"], ["System Manager"])
        self.assertEqual(me_payload["data"]["source"], "dev_session")

    def test_logout_clears_cookie_and_invalidates_session(self) -> None:
        self._login()
        logout_response = self.client.post("/api/auth/logout")
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(logout_response.json()["code"], "0")

        me_response = self.client.get("/api/auth/me")
        self.assertEqual(me_response.status_code, 401)
        self.assertEqual(me_response.json()["code"], "AUTH_UNAUTHORIZED")

    def test_invalid_session_cookie_is_fail_closed(self) -> None:
        self.client.cookies.set("lingyi_local_session", "invalid.session.token")
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")

    def test_login_is_blocked_when_local_auth_is_disabled(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "LINGYI_ALLOW_DEV_AUTH": "true", "LINGYI_ERPNEXT_BASE_URL": ""},
            clear=False,
        ):
            response = self.client.post(
                "/api/auth/login",
                json={"username": "blocked.user", "profile": "system_manager"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "INTERNAL_API_DISABLED")

    def test_module_action_scan_is_unauthorized_without_session(self) -> None:
        for module in self.MODULE_SCAN:
            response = self.client.get(f"/api/auth/actions?module={module}")
            self.assertEqual(response.status_code, 401, msg=module)
            self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")

    def test_module_action_scan_is_available_after_login(self) -> None:
        self._login()
        for module in self.MODULE_SCAN:
            response = self.client.get(f"/api/auth/actions?module={module}")
            self.assertEqual(response.status_code, 200, msg=module)
            payload = response.json()
            self.assertEqual(payload["code"], "0")
            self.assertEqual(payload["data"]["module"], module)


if __name__ == "__main__":
    unittest.main()
