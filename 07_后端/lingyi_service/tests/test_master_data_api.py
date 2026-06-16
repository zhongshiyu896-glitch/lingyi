"""API tests for FastAPI-native master data writes."""

from __future__ import annotations

import os
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
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataIdempotency
from app.models.master_data import LyMasterDataRecord
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.master_data import get_db_session as master_data_db_dep


class MasterDataApiTest(unittest.TestCase):
    """Validate true DB writes, auth, audit, idempotency and conflicts."""

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
        MasterDataBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[master_data_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(master_data_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyMasterDataIdempotency).delete()
            session.query(LyMasterDataRecord).delete()
            session.commit()

    @staticmethod
    def _headers(role: str = "System Manager", request_id: str = "MASTER-DATA-REQ-001") -> dict[str, str]:
        return {
            "X-LY-Dev-User": "master.data.user",
            "X-LY-Dev-Roles": role,
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _payload(code: str = "CUST-A2-001", idempotency_key: str = "IDEMP-CUST-A2-001") -> dict:
        return {
            "operation": "create",
            "company": "COMP-A",
            "code": code,
            "name": f"{code}-NAME",
            "idempotency_key": idempotency_key,
            "payload": {"owner": "sales", "level": "A"},
        }

    def test_create_customer_persists_and_lists_with_audit(self) -> None:
        response = self.client.post(
            "/api/master-data/customers",
            headers=self._headers(),
            json=self._payload(),
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(body["data"]["code"], "CUST-A2-001")
        record_id = int(body["data"]["id"])

        list_response = self.client.get(
            "/api/master-data/customers?company=COMP-A&keyword=CUST-A2",
            headers=self._headers(request_id="MASTER-DATA-REQ-002"),
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"]["total"], 1)
        self.assertEqual(list_response.json()["data"]["items"][0]["id"], record_id)

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMasterDataRecord).count(), 1)
            audit = session.query(LyOperationAuditLog).one()
            self.assertEqual(audit.module, "master_data")
            self.assertEqual(audit.action, "create")
            self.assertEqual(audit.result, "success")

    def test_create_idempotency_retry_returns_same_record(self) -> None:
        first = self.client.post(
            "/api/master-data/suppliers",
            headers=self._headers(request_id="MASTER-DATA-IDEM-001"),
            json=self._payload(code="SUP-A2-001", idempotency_key="IDEMP-SUP-A2-001"),
        )
        retry = self.client.post(
            "/api/master-data/suppliers",
            headers=self._headers(request_id="MASTER-DATA-IDEM-002"),
            json=self._payload(code="SUP-A2-001", idempotency_key="IDEMP-SUP-A2-001"),
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 201)
        self.assertEqual(first.json()["data"]["id"], retry.json()["data"]["id"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMasterDataRecord).count(), 1)
            self.assertEqual(session.query(LyMasterDataIdempotency).count(), 1)

    def test_idempotency_key_conflict_is_409_and_audited(self) -> None:
        payload = self._payload(code="FAC-A2-001", idempotency_key="IDEMP-FAC-A2-001")
        response = self.client.post(
            "/api/master-data/factories",
            headers=self._headers(request_id="MASTER-DATA-CONFLICT-001"),
            json=payload,
        )
        self.assertEqual(response.status_code, 201)

        changed = dict(payload)
        changed["name"] = "changed-name"
        conflict = self.client.post(
            "/api/master-data/factories",
            headers=self._headers(request_id="MASTER-DATA-CONFLICT-002"),
            json=changed,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "MASTER_DATA_IDEMPOTENCY_CONFLICT")
        with self.SessionLocal() as session:
            failed = (
                session.query(LyOperationAuditLog)
                .filter(LyOperationAuditLog.result == "failed")
                .one()
            )
            self.assertEqual(failed.error_code, "MASTER_DATA_IDEMPOTENCY_CONFLICT")

    def test_duplicate_active_code_is_409(self) -> None:
        first = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-DUP-001"),
            json=self._payload(code="WH-A2-001", idempotency_key="IDEMP-WH-A2-001"),
        )
        duplicate = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-DUP-002"),
            json=self._payload(code="WH-A2-001", idempotency_key="IDEMP-WH-A2-002"),
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.json()["code"], "MASTER_DATA_CONFLICT")

    def test_update_and_deactivate_customer(self) -> None:
        created = self.client.post(
            "/api/master-data/customers",
            headers=self._headers(request_id="MASTER-DATA-MUT-001"),
            json=self._payload(code="CUST-A2-002", idempotency_key="IDEMP-CUST-A2-002-C"),
        )
        record_id = int(created.json()["data"]["id"])

        update = self.client.patch(
            f"/api/master-data/customers/{record_id}",
            headers=self._headers(request_id="MASTER-DATA-MUT-002"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "name": "客户 A2 修改",
                "payload": {"owner": "sales", "level": "B"},
                "idempotency_key": "IDEMP-CUST-A2-002-U",
            },
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json()["data"]["name"], "客户 A2 修改")
        self.assertEqual(update.json()["data"]["payload"]["level"], "B")

        deactivated = self.client.post(
            f"/api/master-data/customers/{record_id}/deactivate",
            headers=self._headers(request_id="MASTER-DATA-MUT-003"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "reason": "停用测试",
                "idempotency_key": "IDEMP-CUST-A2-002-X",
            },
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertTrue(deactivated.json()["data"]["disabled"])
        self.assertEqual(deactivated.json()["data"]["status"], "inactive")

    def test_manage_permission_fails_closed(self) -> None:
        response = self.client.post(
            "/api/master-data/customers",
            headers=self._headers(role="Sales Manager", request_id="MASTER-DATA-DENY-001"),
            json=self._payload(code="CUST-DENY-001", idempotency_key="IDEMP-CUST-DENY-001"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMasterDataRecord).count(), 0)


if __name__ == "__main__":
    unittest.main()
