"""BOM audit behavior tests (TASK-001F)."""

from __future__ import annotations

import os
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

# Ensure env-dependent app settings are stable before importing app modules.
os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.error_codes import AUDIT_WRITE_FAILED
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


class BomAuditBehaviorTest(unittest.TestCase):
    """Validate audit failure behavior for BOM APIs."""

    REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

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
                    "('ITEM-NEW', 'ITEM-NEW', 0), ('MAT-NEW', 'MAT-NEW', 0)"
                )
            )

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-OLD-1",
                    item_code="ITEM-OLD",
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

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(bom_db_dep, None)
        cls.engine.dispose()

    @staticmethod
    def _headers(role: str = "BOM Editor", request_id: str | None = None) -> dict[str, str]:
        headers = {"X-LY-Dev-User": "audit.user", "X-LY-Dev-Roles": role}
        if request_id is not None:
            headers["X-Request-ID"] = request_id
        return headers

    def _count_bom_rows(self) -> int:
        with self.SessionLocal() as session:
            return session.query(LyApparelBom).count()

    def test_operation_audit_failure_returns_audit_write_failed_and_rolls_back(self) -> None:
        before_count = self._count_bom_rows()
        payload = {
            "item_code": "ITEM-NEW",
            "version_no": "V1",
            "bom_items": [
                {
                    "material_item_code": "MAT-NEW",
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
        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-TEST")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-TEST"}}), patch.object(
            AuditService,
            "record_success",
            side_effect=AuditWriteFailed(),
        ):
            response = self.client.post("/api/bom/", headers=self._headers(), json=payload)

        payload_json = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload_json.get("code"), AUDIT_WRITE_FAILED)
        self.assertEqual(self._count_bom_rows(), before_count)
        self.assertRegex(response.headers.get("X-Request-ID", ""), self.REQUEST_ID_PATTERN)

    def test_security_audit_write_failure_does_not_allow_forbidden_request(self) -> None:
        sensitive_request_id = "token-password-secret-cookie-authorization"
        with patch.object(AuditService, "record_security_audit", side_effect=AuditWriteFailed()), self.assertLogs(
            "app.services.permission_service",
            level="ERROR",
        ) as log_ctx:
            response = self.client.get("/api/bom/", headers=self._headers(role="NoRole", request_id=sensitive_request_id))

        payload = response.json()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(payload.get("code"), "AUTH_FORBIDDEN")
        self.assertTrue(any("security_audit_write_failed" in message for message in log_ctx.output))
        response_request_id = response.headers.get("X-Request-ID", "")
        self.assertRegex(response_request_id, self.REQUEST_ID_PATTERN)
        self.assertNotEqual(response_request_id, sensitive_request_id)


if __name__ == "__main__":
    unittest.main()
