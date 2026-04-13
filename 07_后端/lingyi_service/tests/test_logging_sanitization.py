"""Log sanitization tests for TASK-001H."""

from __future__ import annotations

import os
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.exceptions import AuditWriteFailed
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep
from app.schemas.bom import BomNameData
from app.services.audit_service import AuditService
from app.services.bom_service import BomService


class LoggingSanitizationTest(unittest.TestCase):
    """Verify server-side error logs are redacted."""

    REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

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

        BomBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)
        with cls.engine.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE tabItem (name VARCHAR(140) PRIMARY KEY, item_code VARCHAR(140), disabled INTEGER DEFAULT 0)"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO tabItem(name, item_code, disabled) VALUES "
                    "('ITEM-A', 'ITEM-A', 0), ('MAT-A', 'MAT-A', 0)"
                )
            )
        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-OLD-1",
                    item_code="ITEM-A",
                    version_no="V1",
                    is_default=False,
                    status="draft",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.commit()

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

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        cls.engine.dispose()

    @staticmethod
    def _headers(role: str = "BOM Editor", request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "log.user", "X-LY-Dev-Roles": role}
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        return headers

    @staticmethod
    def _create_payload() -> dict:
        return {
            "item_code": "ITEM-A",
            "version_no": "V2",
            "bom_items": [
                {
                    "material_item_code": "MAT-A",
                    "qty_per_piece": "1",
                    "loss_rate": "0",
                    "uom": "PCS",
                }
            ],
            "operations": [
                {
                    "process_name": "sew",
                    "sequence_no": 1,
                    "is_subcontract": False,
                    "wage_rate": "1",
                }
            ],
        }

    @staticmethod
    def _assert_log_is_sanitized(log_text: str) -> None:
        lowered = log_text.lower()
        for forbidden in [
            "[sql:",
            "[parameters:",
            "update ly_schema.",
            "insert into ly_schema.",
            "delete from ly_schema.",
            "select ",
            "authorization",
            "cookie",
            "password",
            "passwd",
            "secret",
            "token",
        ]:
            if forbidden in lowered:
                raise AssertionError(f"forbidden log token found: {forbidden}\n{log_text}")

    def test_database_write_failure_log_is_sanitized(self) -> None:
        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-TEST")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-TEST"}}), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=SQLAlchemyError(
                "[SQL: UPDATE ly_schema.ly_apparel_bom SET x=1] [parameters: {'password':'123','token':'abc'}]"
            ),
        ), self.assertLogs("app.routers.bom", level="ERROR") as log_ctx:
            response = self.client.post("/api/bom/", headers=self._headers(), json=self._create_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self._assert_log_is_sanitized("\n".join(log_ctx.output))

    def test_rollback_failure_log_is_sanitized(self) -> None:
        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-TEST")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-TEST"}}), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=OperationalError(
                "commit failed",
                {},
                Exception("[SQL: UPDATE ly_schema.ly_apparel_bom] token=abc secret=def"),
            ),
        ), patch(
            "sqlalchemy.orm.session.Session.rollback",
            side_effect=DBAPIError(
                "rollback failed",
                {},
                Exception("[SQL: DELETE FROM ly_schema.ly_apparel_bom] password=123"),
            ),
        ), self.assertLogs("app.routers.bom", level="ERROR") as log_ctx:
            response = self.client.post("/api/bom/", headers=self._headers(), json=self._create_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self._assert_log_is_sanitized("\n".join(log_ctx.output))

    def test_audit_write_failure_log_is_sanitized(self) -> None:
        with patch.object(
            AuditService,
            "record_security_audit",
            side_effect=AuditWriteFailed(
                "[SQL: INSERT INTO ly_schema.ly_security_audit_log] Cookie=session=abc; Authorization=Bearer xxx"
            ),
        ), self.assertLogs("app.services.permission_service", level="ERROR") as log_ctx:
            response = self.client.get("/api/bom/", headers=self._headers(role="NoRole"))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json().get("code"), "AUTH_FORBIDDEN")
        self._assert_log_is_sanitized("\n".join(log_ctx.output))

    def test_semantic_sensitive_request_id_is_replaced_and_not_logged(self) -> None:
        malicious_request_id = "Bearer.abc123_token_secret"
        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-TEST")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-TEST"}}), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=SQLAlchemyError("[SQL: UPDATE ly_schema.ly_apparel_bom SET x=1]"),
        ), self.assertLogs("app.routers.bom", level="ERROR") as log_ctx:
            response = self.client.post(
                "/api/bom/",
                headers=self._headers(request_id=malicious_request_id),
                json=self._create_payload(),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json().get("code"), DATABASE_WRITE_FAILED)
        self.assertRegex(response.headers.get("X-Request-ID", ""), self.REQUEST_ID_PATTERN)
        self.assertNotEqual(response.headers.get("X-Request-ID"), malicious_request_id)
        log_text = "\n".join(log_ctx.output)
        self._assert_log_is_sanitized(log_text)
        self.assertNotIn(malicious_request_id, log_text)
        self.assertNotRegex(log_text, re.compile(r"bearer|token|secret", re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
