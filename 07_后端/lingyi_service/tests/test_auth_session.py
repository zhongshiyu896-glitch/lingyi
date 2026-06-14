"""Local auth session coverage for W003A M1 entry flow."""

from __future__ import annotations

import os
import unittest
from urllib import error as url_error
from unittest.mock import patch

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LINGYI_ALLOW_DEV_AUTH", "true")
os.environ.setdefault("LINGYI_ERPNEXT_BASE_URL", "")
os.environ.setdefault("LINGYI_PERMISSION_SOURCE", "static")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.core.auth as auth_core
import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.routers.auth import get_db_session as auth_db_dep


class _FakeERPNextHeaders:
    def __init__(self, set_cookie_headers: list[str] | None = None) -> None:
        self._set_cookie_headers = set_cookie_headers or []

    def get_all(self, name: str, default=None):
        if name.lower() == "set-cookie":
            return list(self._set_cookie_headers)
        return default


class _FakeERPNextResponse:
    def __init__(self, payload: dict, set_cookie_headers: list[str] | None = None) -> None:
        self._payload = payload
        self._headers = _FakeERPNextHeaders(set_cookie_headers)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        import json

        return json.dumps(self._payload).encode("utf-8")

    def info(self) -> _FakeERPNextHeaders:
        return self._headers


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
        auth_core._reset_auth_session_cache_for_tests()
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_AUTH_CACHE_TTL_SECONDS"] = "45"

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

    def test_production_login_without_erpnext_base_url_fails_closed(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_ENV": "production", "LINGYI_ALLOW_DEV_AUTH": "true", "LINGYI_ERPNEXT_BASE_URL": ""},
            clear=False,
        ):
            response = self.client.post(
                "/api/auth/login",
                json={"username": "blocked.user", "password": "secret-pass"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "ERPNEXT_SERVICE_UNAVAILABLE")

    def test_production_login_proxies_erpnext_and_sets_sid_cookie(self) -> None:
        captured_login_body = b""

        def _fake_urlopen(req, timeout=0):
            nonlocal captured_login_body
            self.assertEqual(timeout, 5)
            url = req.full_url
            if url.endswith("/api/method/login"):
                captured_login_body = req.data or b""
                return _FakeERPNextResponse(
                    {"message": "Logged In"},
                    ["sid=erpnext-session-123; Path=/; HttpOnly; SameSite=Lax"],
                )
            if url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-session-123")
                return _FakeERPNextResponse({"message": "erp.user@example.com"})
            if "/api/resource/User/erp.user%40example.com" in url:
                self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-session-123")
                return _FakeERPNextResponse(
                    {"data": {"roles": [{"role": "System Manager"}, {"role": "BOM Editor"}]}}
                )
            raise AssertionError(f"unexpected ERPNext URL: {url}")

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            response = self.client.post(
                "/api/auth/login",
                json={"username": "erp.user@example.com", "password": "secret-pass"},
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"usr=erp.user%40example.com", captured_login_body)
            self.assertIn(b"pwd=secret-pass", captured_login_body)
            self.assertIn("sid=erpnext-session-123", response.headers.get("set-cookie", ""))
            payload = response.json()
            self.assertEqual(payload["code"], "0")
            self.assertEqual(payload["data"]["username"], "erp.user@example.com")
            self.assertEqual(payload["data"]["roles"], ["BOM Editor", "System Manager"])
            self.assertEqual(payload["data"]["source"], "erpnext_session")

            me_response = self.client.get("/api/auth/me")
            self.assertEqual(me_response.status_code, 200)
            self.assertEqual(me_response.json()["data"]["source"], "erpnext_session")

    def test_production_login_fail_closed_on_erpnext_unauthorized(self) -> None:
        def _fake_urlopen(req, timeout=0):
            raise url_error.HTTPError(req.full_url, 401, "Unauthorized", hdrs=None, fp=None)

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            response = self.client.post(
                "/api/auth/login",
                json={"username": "erp.user@example.com", "password": "bad-pass"},
            )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")
        self.assertNotIn("sid=", response.headers.get("set-cookie", ""))

    def test_erpnext_session_cache_reuses_successful_sid_within_ttl(self) -> None:
        network_calls: list[str] = []

        def _fake_urlopen(req, timeout=0):
            network_calls.append(req.full_url)
            self.assertEqual(timeout, 5)
            self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-cache-sid")
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                return _FakeERPNextResponse({"message": "cached.user@example.com"})
            if "/api/resource/User/cached.user%40example.com" in req.full_url:
                return _FakeERPNextResponse({"data": {"roles": [{"role": "BOM Editor"}]}})
            raise AssertionError(f"unexpected ERPNext URL: {req.full_url}")

        self.client.cookies.set("sid", "erpnext-cache-sid")
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
                "LINGYI_AUTH_CACHE_TTL_SECONDS": "45",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            first_response = self.client.get("/api/auth/me")
            second_response = self.client.get("/api/auth/me")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()["data"]["username"], "cached.user@example.com")
        self.assertEqual(len(network_calls), 2)
        self.assertEqual(
            [url.rsplit("/", maxsplit=1)[-1].split("?", maxsplit=1)[0] for url in network_calls],
            ["frappe.auth.get_logged_user", "cached.user%40example.com"],
        )

    def test_erpnext_session_cache_expires_and_revalidates(self) -> None:
        network_calls: list[str] = []

        def _fake_urlopen(req, timeout=0):
            network_calls.append(req.full_url)
            self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-expiring-sid")
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                return _FakeERPNextResponse({"message": "expiring.user@example.com"})
            if "/api/resource/User/expiring.user%40example.com" in req.full_url:
                return _FakeERPNextResponse({"data": {"roles": [{"role": "System Manager"}]}})
            raise AssertionError(f"unexpected ERPNext URL: {req.full_url}")

        self.client.cookies.set("sid", "erpnext-expiring-sid")
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
                "LINGYI_AUTH_CACHE_TTL_SECONDS": "1",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen), patch(
            "app.core.auth._auth_cache_now",
            side_effect=[100.0, 100.0, 101.1, 101.1],
        ):
            first_response = self.client.get("/api/auth/me")
            second_response = self.client.get("/api/auth/me")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(network_calls), 4)

    def test_logout_clears_erpnext_session_cache(self) -> None:
        network_calls: list[str] = []

        def _fake_urlopen(req, timeout=0):
            network_calls.append(req.full_url)
            self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-logout-sid")
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                return _FakeERPNextResponse({"message": "logout.user@example.com"})
            if "/api/resource/User/logout.user%40example.com" in req.full_url:
                return _FakeERPNextResponse({"data": {"roles": [{"role": "BOM Editor"}]}})
            raise AssertionError(f"unexpected ERPNext URL: {req.full_url}")

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
                "LINGYI_AUTH_CACHE_TTL_SECONDS": "45",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            self.client.cookies.set("sid", "erpnext-logout-sid")
            first_response = self.client.get("/api/auth/me")
            logout_response = self.client.post("/api/auth/logout")
            self.client.cookies.set("sid", "erpnext-logout-sid")
            second_response = self.client.get("/api/auth/me")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(logout_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(network_calls), 4)

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
