"""BOM exception classification tests (TASK-001F)."""

from __future__ import annotations

import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

# Ensure env-dependent app settings are stable before importing app modules.
os.environ["APP_ENV"] = "test"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"

from fastapi.testclient import TestClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.error_codes import AUDIT_WRITE_FAILED
from app.core.error_codes import BOM_DEFAULT_CONFLICT
from app.core.error_codes import BOM_INTERNAL_ERROR
from app.core.error_codes import BOM_PUBLISHED_LOCKED
from app.core.error_codes import DATABASE_READ_FAILED
from app.core.error_codes import DATABASE_WRITE_FAILED
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.core.exceptions import DatabaseReadFailed
from app.core.exceptions import DatabaseWriteFailed
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep
from app.schemas.bom import BomNameData
from app.schemas.bom import BomSetDefaultData
from app.schemas.bom import BomUpdateData
from app.schemas.bom import BomActivateData
from app.schemas.bom import BomDeactivateData
from app.services.audit_service import AuditService
from app.services.bom_service import BomService


class BomExceptionHandlingTest(unittest.TestCase):
    """Validate BOM API exception code classification."""

    BOM_SCENARIO_TAG = "Z002-BOM-20260412-001"
    ITEM_CODE = "ITEM-A"
    BOM_NO = f"{BOM_SCENARIO_TAG}-BOM-ITEM-A-V1"
    CREATE_ITEM_CODE = "ITEM-NEW"

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"

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

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no=cls.BOM_NO,
                    item_code=cls.ITEM_CODE,
                    version_no="V1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyApparelBomItem(
                    id=1,
                    bom_id=1,
                    material_item_code="MAT-A",
                    color=None,
                    size=None,
                    qty_per_piece=1,
                    loss_rate=0,
                    uom="PCS",
                    remark=None,
                )
            )
            session.add(
                LyBomOperation(
                    id=1,
                    bom_id=1,
                    process_name="cut",
                    sequence_no=1,
                    is_subcontract=False,
                    wage_rate=1,
                    subcontract_cost_per_piece=None,
                    remark=None,
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
    def _carrier_code(value: str) -> str:
        hash_value = 2166136261
        for byte in value.strip().encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-4:]

    @classmethod
    def _create_source_ref(cls) -> str:
        return f"{cls.BOM_SCENARIO_TAG}-SRC-{cls.CREATE_ITEM_CODE}"

    @classmethod
    def _request_id(cls, *, item_code: str, bom_ref: str, reason: str | None = None) -> str:
        reason_scope = reason or "NONE"
        return (
            f"{cls.BOM_SCENARIO_TAG}-RQ-"
            f"I{cls._carrier_code(item_code)}-"
            f"B{cls._carrier_code(bom_ref)}-"
            f"R{cls._carrier_code(reason_scope)}"
        )

    @classmethod
    def _headers(
        cls,
        role: str = "BOM Editor",
        *,
        item_code: str | None = None,
        bom_ref: str | None = None,
        reason: str | None = None,
    ) -> dict[str, str]:
        resolved_item_code = item_code or cls.ITEM_CODE
        resolved_bom_ref = bom_ref or cls.BOM_NO
        return {
            "X-LY-Dev-User": "tester",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": cls._request_id(
                item_code=resolved_item_code,
                bom_ref=resolved_bom_ref,
                reason=reason,
            ),
        }

    @classmethod
    def _create_headers(cls, role: str = "BOM Editor") -> dict[str, str]:
        return cls._headers(role=role, item_code=cls.CREATE_ITEM_CODE, bom_ref=cls._create_source_ref())

    @classmethod
    def _bom_snapshot(cls) -> dict:
        return {"bom": {"bom_no": cls.BOM_NO, "item_code": cls.ITEM_CODE}}

    @classmethod
    def _create_payload(cls) -> dict:
        return {
            "scenario_tag": cls.BOM_SCENARIO_TAG,
            "idempotency_key": f"{cls.BOM_SCENARIO_TAG}-IDEMP-CREATE",
            "source_ref": cls._create_source_ref(),
            "item_code": cls.CREATE_ITEM_CODE,
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
                    "wage_rate": "1.2",
                }
            ],
        }

    @classmethod
    def _update_payload(cls) -> dict:
        return {
            "scenario_tag": cls.BOM_SCENARIO_TAG,
            "idempotency_key": f"{cls.BOM_SCENARIO_TAG}-IDEMP-UPDATE",
            "source_ref": cls.BOM_NO,
            "bom_no": cls.BOM_NO,
            "item_code": cls.ITEM_CODE,
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
                    "process_name": "cut",
                    "sequence_no": 1,
                    "is_subcontract": False,
                    "wage_rate": "1",
                }
            ],
        }

    @classmethod
    def _carrier_payload(cls, *, reason: str | None = None) -> dict:
        payload = {
            "scenario_tag": cls.BOM_SCENARIO_TAG,
            "idempotency_key": f"{cls.BOM_SCENARIO_TAG}-IDEMP-CARRIER",
            "source_ref": cls.BOM_NO,
            "bom_no": cls.BOM_NO,
            "item_code": cls.ITEM_CODE,
        }
        if reason is not None:
            payload["reason"] = reason
        return payload

    def test_create_bom_returns_audit_write_failed_when_operation_audit_fails(self) -> None:
        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-TEST")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-TEST"}}), patch.object(
            AuditService,
            "record_success",
            side_effect=AuditWriteFailed(),
        ):
            response = self.client.post("/api/bom/", headers=self._create_headers(), json=self._create_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), AUDIT_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_create_bom_returns_database_write_failed_when_business_write_fails(self) -> None:
        with patch.object(BomService, "create_bom", side_effect=DatabaseWriteFailed()):
            response = self.client.post("/api/bom/", headers=self._create_headers(), json=self._create_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_create_bom_returns_database_write_failed_when_commit_raises(self) -> None:
        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-TEST")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-TEST"}}), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=SQLAlchemyError("commit failed"),
        ):
            response = self.client.post("/api/bom/", headers=self._create_headers(), json=self._create_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_update_bom_returns_database_write_failed_when_commit_raises(self) -> None:
        with patch.object(
            BomService,
            "update_bom_draft",
            return_value=BomUpdateData(name=self.BOM_NO, status="draft", updated_at="2026-04-12T00:00:00"),
        ), patch.object(
            AuditService,
            "snapshot_resource",
            return_value=self._bom_snapshot(),
        ), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=SQLAlchemyError("commit failed"),
        ):
            response = self.client.put("/api/bom/1", headers=self._headers(), json=self._update_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_activate_bom_returns_database_write_failed_when_commit_raises(self) -> None:
        with patch.object(
            BomService,
            "activate",
            return_value=BomActivateData(name=self.BOM_NO, status="active", effective_date="2026-04-12"),
        ), patch.object(
            AuditService,
            "snapshot_resource",
            return_value=self._bom_snapshot(),
        ), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=SQLAlchemyError("commit failed"),
        ):
            response = self.client.post(
                "/api/bom/1/activate",
                headers=self._headers(role="BOM Publisher"),
                json=self._carrier_payload(),
            )

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_deactivate_bom_returns_database_write_failed_when_commit_raises(self) -> None:
        with patch.object(
            BomService,
            "deactivate",
            return_value=BomDeactivateData(name=self.BOM_NO, status="inactive"),
        ), patch.object(
            AuditService,
            "snapshot_resource",
            return_value=self._bom_snapshot(),
        ), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=SQLAlchemyError("commit failed"),
        ):
            reason = f"{self.BOM_SCENARIO_TAG}-manual-off"
            response = self.client.post(
                "/api/bom/1/deactivate",
                headers=self._headers(role="BOM Publisher", reason=reason),
                json=self._carrier_payload(reason=reason),
            )

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_set_default_returns_database_write_failed_when_commit_raises(self) -> None:
        with patch.object(
            BomService,
            "set_default",
            return_value=BomSetDefaultData(name=self.BOM_NO, item_code=self.ITEM_CODE, is_default=True),
        ), patch.object(
            AuditService,
            "snapshot_resource",
            return_value=self._bom_snapshot(),
        ), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=SQLAlchemyError("commit failed"),
        ):
            response = self.client.post(
                "/api/bom/1/set-default",
                headers=self._headers(role="BOM Publisher"),
                json=self._carrier_payload(),
            )

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_set_default_returns_default_conflict_when_commit_integrity_hits_partial_unique_index(self) -> None:
        integrity_exc = IntegrityError(
            statement="UPDATE ly_schema.ly_apparel_bom ...",
            params={},
            orig=Exception('duplicate key value violates unique constraint "uk_ly_apparel_bom_one_active_default"'),
        )
        with patch.object(
            BomService,
            "set_default",
            return_value=BomSetDefaultData(name=self.BOM_NO, item_code=self.ITEM_CODE, is_default=True),
        ), patch.object(
            AuditService,
            "snapshot_resource",
            return_value=self._bom_snapshot(),
        ), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=integrity_exc,
        ):
            response = self.client.post(
                "/api/bom/1/set-default",
                headers=self._headers(role="BOM Publisher"),
                json=self._carrier_payload(),
            )

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload.get("code"), BOM_DEFAULT_CONFLICT)
        self.assertIsNone(payload.get("data"))

    def test_commit_failure_rollback_failure_does_not_override_database_write_failed(self) -> None:
        with patch.object(BomService, "create_bom", return_value=BomNameData(name="BOM-TEST")), patch.object(
            BomService,
            "get_bom_by_no",
            return_value=SimpleNamespace(id=1),
        ), patch.object(AuditService, "snapshot_resource", return_value={"bom": {"bom_no": "BOM-TEST"}}), patch(
            "sqlalchemy.orm.session.Session.commit",
            side_effect=OperationalError("commit failed", {}, Exception("db down")),
        ), patch(
            "sqlalchemy.orm.session.Session.rollback",
            side_effect=DBAPIError("rollback failed", {}, Exception("rollback error")),
        ):
            response = self.client.post("/api/bom/", headers=self._create_headers(), json=self._create_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_WRITE_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_snapshot_resource_database_read_failed_returns_database_read_failed(self) -> None:
        with patch.object(AuditService, "snapshot_resource", side_effect=DatabaseReadFailed()):
            response = self.client.put("/api/bom/1", headers=self._headers(), json=self._update_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_READ_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_snapshot_resource_unknown_error_returns_internal_error(self) -> None:
        with patch.object(AuditService, "snapshot_resource", side_effect=RuntimeError("snapshot boom")):
            response = self.client.put("/api/bom/1", headers=self._headers(), json=self._update_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), BOM_INTERNAL_ERROR)
        self.assertIsNone(payload.get("data"))

    def test_create_bom_returns_internal_error_when_unknown_runtime_error_occurs(self) -> None:
        with patch.object(BomService, "create_bom", side_effect=RuntimeError("boom")):
            response = self.client.post("/api/bom/", headers=self._create_headers(), json=self._create_payload())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), BOM_INTERNAL_ERROR)
        self.assertIsNone(payload.get("data"))

    def test_get_bom_detail_returns_database_read_failed_when_read_raises(self) -> None:
        with patch.object(BomService, "get_bom_detail", side_effect=DatabaseReadFailed()):
            response = self.client.get("/api/bom/1", headers=self._headers())

        payload = response.json()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(payload.get("code"), DATABASE_READ_FAILED)
        self.assertIsNone(payload.get("data"))

    def test_update_active_bom_returns_published_locked(self) -> None:
        response = self.client.put("/api/bom/1", headers=self._headers(), json=self._update_payload())
        payload_json = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload_json.get("code"), BOM_PUBLISHED_LOCKED)
        self.assertIsNone(payload_json.get("data"))

    def test_set_default_conflict_returns_bom_default_conflict(self) -> None:
        with patch.object(
            BomService,
            "set_default",
            side_effect=BusinessException(code=BOM_DEFAULT_CONFLICT, message="默认 BOM 冲突，请重试"),
        ):
            response = self.client.post(
                "/api/bom/1/set-default",
                headers=self._headers(role="BOM Publisher"),
                json=self._carrier_payload(),
            )

        payload = response.json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(payload.get("code"), BOM_DEFAULT_CONFLICT)
        self.assertIsNone(payload.get("data"))


if __name__ == "__main__":
    unittest.main()
