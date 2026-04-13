"""Request ID sanitization tests for TASK-001J."""

from __future__ import annotations

import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_env import configure_test_env

configure_test_env()

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.request_id import REQUEST_ID_PATTERN
from app.core.request_id import normalize_request_id
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.bom import Base as BomBase
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep
from app.schemas.bom import BomNameData
from app.services.audit_service import AuditService
from app.services.bom_service import BomService


class RequestIdSanitizationTest(unittest.TestCase):
    """Validate request-id normalization and safe propagation."""

    SENSITIVE_PATTERN = re.compile(
        r"(authorization|bearer|token|cookie|set-cookie|password|passwd|secret|session|sessionid|api[-_]?key|access[-_]?key|access[-_]?token|refresh[-_]?token)",
        re.IGNORECASE,
    )

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
                    "('ITEM-RID', 'ITEM-RID', 0), ('MAT-RID', 'MAT-RID', 0)"
                )
            )

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
        configure_test_env()
        with self.SessionLocal() as session:
            session.query(LySecurityAuditLog).delete()
            session.query(LyOperationAuditLog).delete()
            session.commit()

    @staticmethod
    def _headers(*, request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "rid.user", "X-LY-Dev-Roles": "NoRole"}
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        return headers

    def _latest_security_log(self) -> LySecurityAuditLog:
        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            if not row:
                self.fail("expected security audit row")
            return row

    def test_normalize_request_id_keeps_valid_value(self) -> None:
        raw = "req-20260412.ABC_001"
        self.assertEqual(normalize_request_id(raw), raw)
        self.assertRegex(raw, REQUEST_ID_PATTERN)

    def test_normalize_request_id_replaces_invalid_values(self) -> None:
        invalid_values = [
            "abc\n[SQL: UPDATE ly_schema.ly_apparel_bom SET status='active']",
            "Bearer abc.def.ghi",
            "cookie=sessionid=abc123",
            "password=123456",
            "<script>alert(1)</script>",
            "x" * 80,
        ]
        for raw in invalid_values:
            normalized = normalize_request_id(raw)
            self.assertRegex(normalized, REQUEST_ID_PATTERN)
            self.assertNotEqual(normalized, raw)
            self.assertLessEqual(len(normalized), 64)

    def test_normalize_request_id_replaces_semantic_sensitive_values(self) -> None:
        sensitive_values = [
            "token-password-secret-cookie-authorization",
            "Bearer.abc123_token_secret",
            "sessionid.cookie.abc123",
            "passwd.password.123456",
        ]
        for raw in sensitive_values:
            normalized = normalize_request_id(raw)
            self.assertRegex(normalized, REQUEST_ID_PATTERN)
            self.assertNotEqual(normalized, raw)
            self.assertIsNone(self.SENSITIVE_PATTERN.search(normalized))

    def test_valid_request_id_is_preserved_in_response_and_audit(self) -> None:
        request_id = "req-20260412.ABC_001"
        response = self.client.get("/api/bom/", headers=self._headers(request_id=request_id))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers.get("X-Request-ID"), request_id)

        row = self._latest_security_log()
        self.assertEqual(row.request_id, request_id)

    def test_missing_request_id_is_generated(self) -> None:
        response = self.client.get("/api/bom/", headers=self._headers())
        self.assertEqual(response.status_code, 403)
        generated = response.headers.get("X-Request-ID", "")
        self.assertRegex(generated, REQUEST_ID_PATTERN)
        self.assertIsNone(self.SENSITIVE_PATTERN.search(generated))

        row = self._latest_security_log()
        self.assertEqual(row.request_id, generated)

    def test_sensitive_request_id_header_is_replaced_and_not_written_raw(self) -> None:
        sensitive_values = [
            "token-password-secret-cookie-authorization",
            "Bearer.abc123_token_secret",
            "sessionid.cookie.abc123",
            "passwd.password.123456",
            "abc[SQL:UPDATE_ly_schema.ly_apparel_bom]",
            "x" * 80,
        ]
        for raw in sensitive_values:
            response = self.client.get("/api/bom/", headers=self._headers(request_id=raw))
            self.assertEqual(response.status_code, 403)
            normalized = response.headers.get("X-Request-ID", "")
            self.assertRegex(normalized, REQUEST_ID_PATTERN)
            self.assertNotEqual(normalized, raw)
            self.assertIsNone(self.SENSITIVE_PATTERN.search(normalized))

            row = self._latest_security_log()
            self.assertEqual(row.request_id, normalized)
            self.assertNotIn(raw, row.request_id)
            self.assertIsNone(self.SENSITIVE_PATTERN.search(row.request_id))
            self.assertNotIn("[SQL:", row.request_id)

    def test_sensitive_request_id_is_not_written_raw_into_operation_audit(self) -> None:
        raw_request_id = "Bearer.abc123_token_secret"
        payload = {
            "item_code": "ITEM-RID",
            "version_no": "V1",
            "bom_items": [
                {
                    "material_item_code": "MAT-RID",
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

        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-RID")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1, bom_no="BOM-RID"),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-RID"}}):
            response = self.client.post(
                "/api/bom/",
                headers={"X-LY-Dev-User": "rid.editor", "X-LY-Dev-Roles": "BOM Editor", "X-Request-ID": raw_request_id},
                json=payload,
            )

        self.assertEqual(response.status_code, 200)
        normalized = response.headers.get("X-Request-ID", "")
        self.assertRegex(normalized, REQUEST_ID_PATTERN)
        self.assertNotEqual(normalized, raw_request_id)

        with self.SessionLocal() as session:
            row = session.query(LyOperationAuditLog).order_by(LyOperationAuditLog.id.desc()).first()
            if not row:
                self.fail("expected operation audit row")
            self.assertEqual(row.request_id, normalized)
            self.assertNotIn(raw_request_id, row.request_id)
            self.assertIsNone(self.SENSITIVE_PATTERN.search(row.request_id))


if __name__ == "__main__":
    unittest.main()
