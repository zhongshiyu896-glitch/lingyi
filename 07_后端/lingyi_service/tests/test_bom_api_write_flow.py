"""HTTP write coverage for legacy `/api/bom` routes."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest

os.environ["APP_ENV"] = "development"
os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.core.error_codes import BOM_DEFAULT_CONFLICT
from app.core.error_codes import BOM_PUBLISHED_LOCKED
from app.core.error_codes import BOM_STATUS_INVALID
from app.core.error_codes import WORKSHOP_IDEMPOTENCY_CONFLICT
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.audit import LyOperationAuditLog
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.style_master import Base as StyleMasterBase
from app.models.style_master import LyStyleMaster
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.bom import get_db_session as bom_db_dep


class BomApiWriteFlowTest(unittest.TestCase):
    """Validate BOM writes through FastAPI envelopes, auth, audit and carrier gate."""

    COMPANY = "COMP-BOM-API"
    SCENARIO = "Z002-BOM-20260620-001"

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
        BomBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

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
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LyBomOperation).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.query(LyStyleMaster).delete()
            session.commit()

    @staticmethod
    def _carrier_code(value: object) -> str:
        normalized = str(value).strip()
        hash_value = 2166136261
        for byte in normalized.encode("utf-8"):
            hash_value ^= byte
            hash_value = (hash_value * 16777619) & 0xFFFFFFFF
        return f"{hash_value:08X}"[-4:]

    @classmethod
    def _request_id(cls, *, item_code: str, bom_ref: str, reason: str | None = None) -> str:
        reason_ref = reason or "NONE"
        return (
            f"{cls.SCENARIO}-RQ-"
            f"I{cls._carrier_code(item_code)}-"
            f"B{cls._carrier_code(bom_ref)}-"
            f"R{cls._carrier_code(reason_ref)}"
        )

    @classmethod
    def _headers(
        cls,
        *,
        item_code: str,
        bom_ref: str,
        reason: str | None = None,
        role: str = "BOM Editor",
    ) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "bom.api.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": cls._request_id(item_code=item_code, bom_ref=bom_ref, reason=reason),
        }

    @classmethod
    def _style(cls, style_no: str) -> LyStyleMaster:
        return LyStyleMaster(
            company=cls.COMPANY,
            ys_style_no=style_no,
            ys_style_name_cn=f"{style_no} 款式",
            ys_season="SS",
            ys_year="2026",
            ys_brand="LY",
            ys_style_status="enabled",
            colors=[{"ys_color_code": "BLK", "ys_color_name": "黑"}],
            sizes=[{"ys_size_code": "M", "ys_size_name": "M"}],
            version=1,
            created_by="seed",
            updated_by="seed",
        )

    @classmethod
    def _create_payload(cls, *, item_code: str, source_ref: str, idem: str = "create") -> dict[str, object]:
        return {
            "scenario_tag": cls.SCENARIO,
            "idempotency_key": f"{cls.SCENARIO}:{idem}:{item_code}",
            "source_ref": source_ref,
            "company": cls.COMPANY,
            "item_code": item_code,
            "version_no": "V1",
            "bom_items": [
                {
                    "material_item_code": "MAT-BOM-API",
                    "qty_per_piece": "1.25",
                    "loss_rate": "0.05",
                    "uom": "米",
                }
            ],
            "operations": [
                {
                    "process_name": "车缝",
                    "sequence_no": 1,
                    "is_subcontract": False,
                    "wage_rate": "1.20",
                }
            ],
        }

    @classmethod
    def _carrier_payload(cls, *, item_code: str, bom_no: str, idem: str, reason: str | None = None) -> dict[str, object]:
        payload: dict[str, object] = {
            "scenario_tag": cls.SCENARIO,
            "idempotency_key": f"{cls.SCENARIO}:{idem}:{item_code}",
            "source_ref": bom_no,
            "bom_no": bom_no,
            "company": cls.COMPANY,
            "item_code": item_code,
        }
        if reason is not None:
            payload["reason"] = reason
        return payload

    def _seed_style(self, style_no: str) -> None:
        with self.SessionLocal() as session:
            session.add(self._style(style_no))
            session.commit()

    def test_create_bom_http_success_and_duplicate_conflict(self) -> None:
        item_code = "STYLE-BOM-API-001"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        self._seed_style(item_code)
        payload = self._create_payload(item_code=item_code, source_ref=source_ref)

        created = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=payload,
        )
        duplicate = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=payload,
        )

        self.assertEqual(created.status_code, 200, created.text)
        self.assertEqual(created.json()["code"], "0")
        self.assertTrue(created.json()["data"]["name"].startswith("BOM-STYLE-BOM-API-001-V1-"))
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["code"], BOM_DEFAULT_CONFLICT)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyApparelBom).count(), 1)
            self.assertEqual(session.query(LyApparelBomItem).count(), 1)
            self.assertEqual(session.query(LyBomOperation).count(), 1)
            self.assertIn("bom:create", {row.action for row in session.query(LyOperationAuditLog).all()})

    def test_create_bom_rejects_carrier_mismatch_without_writing(self) -> None:
        item_code = "STYLE-BOM-API-GATE"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        self._seed_style(item_code)
        payload = self._create_payload(item_code=item_code, source_ref=source_ref)

        rejected = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=f"{source_ref}:WRONG"),
            json=payload,
        )

        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()["code"], WORKSHOP_IDEMPOTENCY_CONFLICT)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyApparelBom).count(), 0)
            self.assertEqual(session.query(LyOperationAuditLog).count(), 0)

    def test_activate_and_deactivate_http_success_then_state_conflicts(self) -> None:
        item_code = f"STYLE-{self.SCENARIO}-ACT"
        source_ref = f"{self.SCENARIO}:SRC:{item_code}"
        reason = f"{self.SCENARIO}:retire api bom"
        self._seed_style(item_code)
        created = self.client.post(
            "/api/bom/",
            headers=self._headers(item_code=item_code, bom_ref=source_ref),
            json=self._create_payload(item_code=item_code, source_ref=source_ref),
        )
        self.assertEqual(created.status_code, 200, created.text)
        bom_no = str(created.json()["data"]["name"])
        with self.SessionLocal() as session:
            bom_id = int(session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).one().id)

        activate_payload = self._carrier_payload(item_code=item_code, bom_no=bom_no, idem="activate")
        activated = self.client.post(
            f"/api/bom/{bom_id}/activate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=activate_payload,
        )
        activate_again = self.client.post(
            f"/api/bom/{bom_id}/activate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, role="System Manager"),
            json=activate_payload,
        )
        deactivate_payload = self._carrier_payload(
            item_code=item_code,
            bom_no=bom_no,
            idem="deactivate",
            reason=reason,
        )
        deactivated = self.client.post(
            f"/api/bom/{bom_id}/deactivate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, reason=reason, role="System Manager"),
            json=deactivate_payload,
        )
        deactivate_again = self.client.post(
            f"/api/bom/{bom_id}/deactivate",
            headers=self._headers(item_code=item_code, bom_ref=bom_no, reason=reason, role="System Manager"),
            json=deactivate_payload,
        )

        self.assertEqual(activated.status_code, 200, activated.text)
        self.assertEqual(activated.json()["data"]["status"], "active")
        self.assertEqual(activate_again.status_code, 409)
        self.assertEqual(activate_again.json()["code"], BOM_PUBLISHED_LOCKED)
        self.assertEqual(deactivated.status_code, 200, deactivated.text)
        self.assertEqual(deactivated.json()["data"]["status"], "inactive")
        self.assertEqual(deactivate_again.status_code, 409)
        self.assertEqual(deactivate_again.json()["code"], BOM_STATUS_INVALID)
        with self.SessionLocal() as session:
            bom = session.query(LyApparelBom).filter(LyApparelBom.bom_no == bom_no).one()
            self.assertEqual(str(bom.status), "inactive")
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("bom:create", audit_actions)
            self.assertIn("bom:activate", audit_actions)
            self.assertIn("bom:deactivate", audit_actions)


if __name__ == "__main__":
    unittest.main()
