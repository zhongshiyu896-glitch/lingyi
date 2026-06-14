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
        os.environ["LINGYI_ERPNEXT_API_KEY"] = ""
        os.environ["LINGYI_ERPNEXT_API_SECRET"] = ""

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
                self.assertEqual(req.headers.get("Authorization"), "token service-key:service-secret")
                self.assertIsNone(req.headers.get("Cookie"))
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
                "LINGYI_ERPNEXT_API_KEY": "service-key",
                "LINGYI_ERPNEXT_API_SECRET": "service-secret",
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

    def test_erpnext_limited_user_roles_are_loaded_with_service_credentials(self) -> None:
        service_role_calls: list[str] = []
        service_permission_calls: list[str] = []
        unexpected_session_metadata_calls: list[str] = []

        def _fake_urlopen(req, timeout=0):
            self.assertEqual(timeout, 5)
            url = req.full_url
            if url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=limited-user-sid")
                return _FakeERPNextResponse({"message": "limited.user@example.com"})
            if "/api/resource/User/limited.user%40example.com" in url:
                if req.headers.get("Authorization") == "token service-key:service-secret":
                    service_role_calls.append(url)
                    self.assertIsNone(req.headers.get("Cookie"))
                    return _FakeERPNextResponse(
                        {
                            "data": {
                                "name": "limited.user@example.com",
                                "roles": [{"role": "BOM Editor", "parent": "limited.user@example.com"}],
                            }
                        }
                    )
                if req.headers.get("Cookie") == "sid=limited-user-sid":
                    unexpected_session_metadata_calls.append(url)
                    return _FakeERPNextResponse({"data": {"name": "limited.user@example.com", "roles": []}})
            if "/api/resource/User%20Permission" in url:
                service_permission_calls.append(url)
                self.assertEqual(req.headers.get("Authorization"), "token service-key:service-secret")
                self.assertIsNone(req.headers.get("Cookie"))
                return _FakeERPNextResponse({"data": []})
            raise AssertionError(f"unexpected ERPNext URL: {url}")

        self.client.cookies.set("sid", "limited-user-sid")
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
                "LINGYI_AUTH_CACHE_TTL_SECONDS": "45",
                "LINGYI_ERPNEXT_API_KEY": "service-key",
                "LINGYI_ERPNEXT_API_SECRET": "service-secret",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            me_response = self.client.get("/api/auth/me")
            actions_response = self.client.get("/api/auth/actions?module=bom")

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()["data"]["roles"], ["BOM Editor"])
        self.assertEqual(actions_response.status_code, 200)
        actions_payload = actions_response.json()["data"]
        self.assertIn("bom:read", actions_payload["actions"])
        self.assertIn("bom:create", actions_payload["actions"])
        self.assertIn("bom:update", actions_payload["actions"])
        self.assertNotIn("bom:publish", actions_payload["actions"])
        button_permissions = actions_payload["button_permissions"]
        self.assertIs(button_permissions["create"], True)
        self.assertIs(button_permissions["update"], True)
        self.assertIs(button_permissions["read"], True)
        self.assertIs(button_permissions["publish"], False)
        self.assertIs(button_permissions["deactivate"], False)
        self.assertIs(button_permissions["set_default"], False)
        self.assertEqual(len(service_role_calls), 2)
        self.assertEqual(len(service_permission_calls), 1)
        self.assertEqual(unexpected_session_metadata_calls, [])

    def test_erpnext_service_credentials_missing_fails_closed(self) -> None:
        def _fake_urlopen(req, timeout=0):
            self.assertEqual(timeout, 5)
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=missing-service-credentials")
                return _FakeERPNextResponse({"message": "limited.user@example.com"})
            raise AssertionError(f"unexpected ERPNext URL: {req.full_url}")

        self.client.cookies.set("sid", "missing-service-credentials")
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
                "LINGYI_ERPNEXT_API_KEY": "",
                "LINGYI_ERPNEXT_API_SECRET": "",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "ERPNEXT_SERVICE_UNAVAILABLE")

    def test_erpnext_actions_missing_service_credentials_fails_closed(self) -> None:
        role_calls: list[str] = []

        def _fake_urlopen(req, timeout=0):
            self.assertEqual(timeout, 5)
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=actions-missing-service-credentials")
                return _FakeERPNextResponse({"message": "limited.user@example.com"})
            if "/api/resource/User/limited.user%40example.com" in req.full_url:
                self.assertEqual(req.headers.get("Authorization"), "token service-key:service-secret")
                role_calls.append(req.full_url)
                return _FakeERPNextResponse({"data": {"roles": [{"role": "BOM Editor"}]}})
            raise AssertionError(f"unexpected ERPNext URL: {req.full_url}")

        self.client.cookies.set("sid", "actions-missing-service-credentials")
        with patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            with patch.dict(
                os.environ,
                {
                    "APP_ENV": "production",
                    "LINGYI_ALLOW_DEV_AUTH": "false",
                    "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                    "LINGYI_PERMISSION_SOURCE": "erpnext",
                    "LINGYI_AUTH_CACHE_TTL_SECONDS": "45",
                    "LINGYI_ERPNEXT_API_KEY": "service-key",
                    "LINGYI_ERPNEXT_API_SECRET": "service-secret",
                },
                clear=False,
            ):
                me_response = self.client.get("/api/auth/me")
            with patch.dict(
                os.environ,
                {
                    "APP_ENV": "production",
                    "LINGYI_ALLOW_DEV_AUTH": "false",
                    "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                    "LINGYI_PERMISSION_SOURCE": "erpnext",
                    "LINGYI_AUTH_CACHE_TTL_SECONDS": "45",
                    "LINGYI_ERPNEXT_API_KEY": "",
                    "LINGYI_ERPNEXT_API_SECRET": "",
                },
                clear=False,
            ):
                response = self.client.get("/api/auth/actions?module=bom")

        self.assertEqual(me_response.status_code, 200)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertEqual(len(role_calls), 1)

    def test_erpnext_service_credentials_invalid_fails_closed(self) -> None:
        def _fake_urlopen(req, timeout=0):
            self.assertEqual(timeout, 5)
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=invalid-service-credentials")
                return _FakeERPNextResponse({"message": "limited.user@example.com"})
            if "/api/resource/User/limited.user%40example.com" in req.full_url:
                self.assertEqual(req.headers.get("Authorization"), "token bad-key:bad-secret")
                raise url_error.HTTPError(req.full_url, 403, "Forbidden", hdrs=None, fp=None)
            raise AssertionError(f"unexpected ERPNext URL: {req.full_url}")

        self.client.cookies.set("sid", "invalid-service-credentials")
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "LINGYI_ALLOW_DEV_AUTH": "false",
                "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                "LINGYI_PERMISSION_SOURCE": "erpnext",
                "LINGYI_ERPNEXT_API_KEY": "bad-key",
                "LINGYI_ERPNEXT_API_SECRET": "bad-secret",
            },
            clear=False,
        ), patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            response = self.client.get("/api/auth/me")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "ERPNEXT_SERVICE_UNAVAILABLE")

    def test_erpnext_actions_invalid_service_credentials_fails_closed(self) -> None:
        role_calls: list[str] = []

        def _fake_urlopen(req, timeout=0):
            self.assertEqual(timeout, 5)
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=actions-invalid-service-credentials")
                return _FakeERPNextResponse({"message": "limited.user@example.com"})
            if "/api/resource/User/limited.user%40example.com" in req.full_url:
                role_calls.append(req.full_url)
                if req.headers.get("Authorization") == "token service-key:service-secret":
                    return _FakeERPNextResponse({"data": {"roles": [{"role": "BOM Editor"}]}})
                self.assertEqual(req.headers.get("Authorization"), "token bad-key:bad-secret")
                raise url_error.HTTPError(req.full_url, 403, "Forbidden", hdrs=None, fp=None)
            raise AssertionError(f"unexpected ERPNext URL: {req.full_url}")

        self.client.cookies.set("sid", "actions-invalid-service-credentials")
        with patch("app.core.auth.request.urlopen", side_effect=_fake_urlopen):
            with patch.dict(
                os.environ,
                {
                    "APP_ENV": "production",
                    "LINGYI_ALLOW_DEV_AUTH": "false",
                    "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                    "LINGYI_PERMISSION_SOURCE": "erpnext",
                    "LINGYI_AUTH_CACHE_TTL_SECONDS": "45",
                    "LINGYI_ERPNEXT_API_KEY": "service-key",
                    "LINGYI_ERPNEXT_API_SECRET": "service-secret",
                },
                clear=False,
            ):
                me_response = self.client.get("/api/auth/me")
            with patch.dict(
                os.environ,
                {
                    "APP_ENV": "production",
                    "LINGYI_ALLOW_DEV_AUTH": "false",
                    "LINGYI_ERPNEXT_BASE_URL": "https://erpnext.example.test",
                    "LINGYI_PERMISSION_SOURCE": "erpnext",
                    "LINGYI_AUTH_CACHE_TTL_SECONDS": "45",
                    "LINGYI_ERPNEXT_API_KEY": "bad-key",
                    "LINGYI_ERPNEXT_API_SECRET": "bad-secret",
                },
                clear=False,
            ):
                response = self.client.get("/api/auth/actions?module=bom")

        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")
        self.assertEqual(len(role_calls), 2)

    def test_extract_roles_accepts_frappe_roles_child_table_shape(self) -> None:
        roles = auth_core._extract_roles(
            {
                "data": {
                    "name": "limited.user@example.com",
                    "roles": [
                        {
                            "name": "row-0001",
                            "parent": "limited.user@example.com",
                            "parentfield": "roles",
                            "parenttype": "User",
                            "role": "BOM Editor",
                        }
                    ],
                }
            }
        )
        self.assertEqual(roles, ["BOM Editor"])

    def test_erpnext_session_cache_reuses_successful_sid_within_ttl(self) -> None:
        network_calls: list[str] = []

        def _fake_urlopen(req, timeout=0):
            network_calls.append(req.full_url)
            self.assertEqual(timeout, 5)
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-cache-sid")
                return _FakeERPNextResponse({"message": "cached.user@example.com"})
            if "/api/resource/User/cached.user%40example.com" in req.full_url:
                self.assertEqual(req.headers.get("Authorization"), "token service-key:service-secret")
                self.assertIsNone(req.headers.get("Cookie"))
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
                "LINGYI_ERPNEXT_API_KEY": "service-key",
                "LINGYI_ERPNEXT_API_SECRET": "service-secret",
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
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-expiring-sid")
                return _FakeERPNextResponse({"message": "expiring.user@example.com"})
            if "/api/resource/User/expiring.user%40example.com" in req.full_url:
                self.assertEqual(req.headers.get("Authorization"), "token service-key:service-secret")
                self.assertIsNone(req.headers.get("Cookie"))
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
                "LINGYI_ERPNEXT_API_KEY": "service-key",
                "LINGYI_ERPNEXT_API_SECRET": "service-secret",
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
            if req.full_url.endswith("/api/method/frappe.auth.get_logged_user"):
                self.assertEqual(req.headers.get("Cookie"), "sid=erpnext-logout-sid")
                return _FakeERPNextResponse({"message": "logout.user@example.com"})
            if "/api/resource/User/logout.user%40example.com" in req.full_url:
                self.assertEqual(req.headers.get("Authorization"), "token service-key:service-secret")
                self.assertIsNone(req.headers.get("Cookie"))
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
                "LINGYI_ERPNEXT_API_KEY": "service-key",
                "LINGYI_ERPNEXT_API_SECRET": "service-secret",
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
