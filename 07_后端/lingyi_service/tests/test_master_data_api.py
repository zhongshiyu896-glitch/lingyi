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

    def _seed_supplier(self, *, code: str, name: str, status: str = "active", company: str = "COMP-A") -> None:
        with self.SessionLocal() as session:
            session.add(
                LyMasterDataRecord(
                    entity_type="supplier",
                    company=company,
                    code=code,
                    name=name,
                    status=status,
                    payload={"supplier_name": name, "status": status},
                    version=1,
                    created_by="test.seed",
                    updated_by="test.seed",
                )
            )
            session.commit()

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

    def test_list_records_orders_by_latest_created_not_latest_updated(self) -> None:
        first = self.client.post(
            "/api/master-data/suppliers",
            headers=self._headers(request_id="MASTER-DATA-SORT-001"),
            json=self._payload(code="SUP-SORT-001", idempotency_key="IDEMP-SUP-SORT-001-C"),
        )
        self.assertEqual(first.status_code, 201, first.text)
        first_id = int(first.json()["data"]["id"])

        second = self.client.post(
            "/api/master-data/suppliers",
            headers=self._headers(request_id="MASTER-DATA-SORT-002"),
            json=self._payload(code="SUP-SORT-002", idempotency_key="IDEMP-SUP-SORT-002-C"),
        )
        self.assertEqual(second.status_code, 201, second.text)

        updated_first = self.client.patch(
            f"/api/master-data/suppliers/{first_id}",
            headers=self._headers(request_id="MASTER-DATA-SORT-003"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "name": "旧供应商被编辑",
                "idempotency_key": "IDEMP-SUP-SORT-001-U",
                "payload": {"owner": "purchase", "level": "updated"},
            },
        )
        self.assertEqual(updated_first.status_code, 200, updated_first.text)

        listed = self.client.get(
            "/api/master-data/suppliers?company=COMP-A",
            headers=self._headers(request_id="MASTER-DATA-SORT-004"),
        )
        self.assertEqual(listed.status_code, 200, listed.text)
        codes = [item["code"] for item in listed.json()["data"]["items"]]
        self.assertEqual(codes[:2], ["SUP-SORT-002", "SUP-SORT-001"])

    def test_create_supplier_without_code_auto_generates_and_replays(self) -> None:
        payload = {
            "operation": "create",
            "company": "COMP-A",
            "name": "自动编码供应商",
            "idempotency_key": "IDEMP-SUP-AUTO-001",
            "payload": {"owner": "purchase"},
        }
        response = self.client.post(
            "/api/master-data/suppliers",
            headers=self._headers(request_id="MASTER-DATA-SUP-AUTO-001"),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        self.assertEqual(body["code"], "0")
        self.assertRegex(body["data"]["code"], r"^SUP-\d{6}$")
        generated_code = body["data"]["code"]

        replay = self.client.post(
            "/api/master-data/suppliers",
            headers=self._headers(request_id="MASTER-DATA-SUP-AUTO-002"),
            json=payload,
        )
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json()["data"]["code"], generated_code)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMasterDataRecord).filter_by(entity_type="supplier").count(), 1)

    def test_create_material_without_code_syncs_generated_code_to_payload(self) -> None:
        self._seed_supplier(code="SUP-MAT-AUTO", name="自动物料供应商")
        payload = {
            "operation": "create",
            "company": "COMP-A",
            "code": "",
            "name": "自动编码辅料",
            "idempotency_key": "IDEMP-MAT-AUTO-001",
            "payload": {
                "material_kind": "accessory",
                "material_item_code": "",
                "supplier_code": "SUP-MAT-AUTO",
                "uom": "米",
            },
        }
        response = self.client.post(
            "/api/master-data/materials",
            headers=self._headers(request_id="MASTER-DATA-MAT-AUTO-001"),
            json=payload,
        )
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()["data"]
        self.assertRegex(data["code"], r"^ACC-\d{6}$")
        self.assertEqual(data["payload"]["material_item_code"], data["code"])
        self.assertEqual(data["payload"]["supplier_code"], "SUP-MAT-AUTO")

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

    def test_warehouse_child_payload_persists_and_tracks_parent_rename(self) -> None:
        parent = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-WH-TREE-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "WH-TREE-P",
                "name": "仓库父级",
                "idempotency_key": "IDEMP-WH-TREE-P-C",
                "payload": {"location_kind": "warehouse", "manager": "王仓管"},
            },
        )
        self.assertEqual(parent.status_code, 201, parent.text)
        parent_id = int(parent.json()["data"]["id"])

        child = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-WH-TREE-002"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "WH-TREE-A01",
                "name": "A01 库位",
                "idempotency_key": "IDEMP-WH-TREE-A01-C",
                "payload": {"parent_code": "WH-TREE-P", "location_kind": "area", "manager": "李库位"},
            },
        )
        self.assertEqual(child.status_code, 201, child.text)
        self.assertEqual(child.json()["data"]["payload"]["parent_code"], "WH-TREE-P")
        self.assertEqual(child.json()["data"]["payload"]["location_kind"], "area")

        renamed = self.client.patch(
            f"/api/master-data/warehouses/{parent_id}",
            headers=self._headers(request_id="MASTER-DATA-WH-TREE-003"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "code": "WH-TREE-P2",
                "name": "仓库父级改",
                "idempotency_key": "IDEMP-WH-TREE-P-U",
                "payload": {"location_kind": "warehouse", "manager": "王仓管"},
            },
        )
        self.assertEqual(renamed.status_code, 200, renamed.text)

        listed = self.client.get(
            "/api/master-data/warehouses?company=COMP-A&keyword=WH-TREE-A01",
            headers=self._headers(request_id="MASTER-DATA-WH-TREE-004"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["items"][0]["payload"]["parent_code"], "WH-TREE-P2")

        blocked = self.client.post(
            f"/api/master-data/warehouses/{parent_id}/deactivate",
            headers=self._headers(request_id="MASTER-DATA-WH-TREE-005"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "reason": "父级仍有子级",
                "idempotency_key": "IDEMP-WH-TREE-P-X",
            },
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["code"], "MASTER_DATA_CONFLICT")

    def test_warehouse_parent_payload_rejects_missing_inactive_and_cycle(self) -> None:
        parent = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-WH-VALID-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "WH-VALID-P",
                "name": "有效父级",
                "idempotency_key": "IDEMP-WH-VALID-P-C",
                "payload": {"location_kind": "warehouse"},
            },
        )
        self.assertEqual(parent.status_code, 201, parent.text)
        parent_id = int(parent.json()["data"]["id"])

        child = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-WH-VALID-002"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "WH-VALID-C",
                "name": "有效子级",
                "idempotency_key": "IDEMP-WH-VALID-C-C",
                "payload": {"parent_code": "WH-VALID-P", "location_kind": "area"},
            },
        )
        self.assertEqual(child.status_code, 201, child.text)

        missing_parent = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-WH-VALID-003"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "WH-VALID-MISSING",
                "name": "无父级子级",
                "idempotency_key": "IDEMP-WH-VALID-MISSING-C",
                "payload": {"parent_code": "WH-NOT-EXIST", "location_kind": "area"},
            },
        )
        self.assertEqual(missing_parent.status_code, 409)
        self.assertEqual(missing_parent.json()["code"], "MASTER_DATA_CONFLICT")

        cycle = self.client.patch(
            f"/api/master-data/warehouses/{parent_id}",
            headers=self._headers(request_id="MASTER-DATA-WH-VALID-004"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "idempotency_key": "IDEMP-WH-VALID-P-CYCLE",
                "payload": {"parent_code": "WH-VALID-C", "location_kind": "warehouse"},
            },
        )
        self.assertEqual(cycle.status_code, 409)
        self.assertEqual(cycle.json()["code"], "MASTER_DATA_CONFLICT")

        inactive_parent = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-WH-VALID-005"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "WH-INACTIVE-P",
                "name": "停用父级",
                "idempotency_key": "IDEMP-WH-INACTIVE-P-C",
                "payload": {"location_kind": "warehouse"},
            },
        )
        self.assertEqual(inactive_parent.status_code, 201, inactive_parent.text)
        inactive_parent_id = int(inactive_parent.json()["data"]["id"])
        deactivated = self.client.post(
            f"/api/master-data/warehouses/{inactive_parent_id}/deactivate",
            headers=self._headers(request_id="MASTER-DATA-WH-VALID-006"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "reason": "停用父级",
                "idempotency_key": "IDEMP-WH-INACTIVE-P-X",
            },
        )
        self.assertEqual(deactivated.status_code, 200)
        inactive_child = self.client.post(
            "/api/master-data/warehouses",
            headers=self._headers(request_id="MASTER-DATA-WH-VALID-007"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "WH-INACTIVE-C",
                "name": "停用父级子级",
                "idempotency_key": "IDEMP-WH-INACTIVE-C-C",
                "payload": {"parent_code": "WH-INACTIVE-P", "location_kind": "area"},
            },
        )
        self.assertEqual(inactive_child.status_code, 409)
        self.assertEqual(inactive_child.json()["code"], "MASTER_DATA_CONFLICT")

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

    def test_material_payload_update_and_deactivate(self) -> None:
        self._seed_supplier(code="SUP-QH", name="青禾面辅料")
        self._seed_supplier(code="SUP-JC", name="锦程纺织")

        created = self.client.post(
            "/api/master-data/materials",
            headers=self._headers(request_id="MASTER-DATA-MAT-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "FAB-A2-001",
                "name": "A2 面料",
                "idempotency_key": "IDEMP-MAT-A2-001-C",
                "payload": {
                    "material_kind": "fabric",
                    "material_item_code": "FAB-A2-001",
                    "fabric_name": "A2 面料",
                    "colors": ["黑色", "白色"],
                    "part": "主身",
                    "supplier_name": "青禾面辅料",
                    "uom": "米",
                    "qty_per_piece": 1.25,
                    "loss_rate": 0.03,
                    "status": "active",
                },
            },
        )
        self.assertEqual(created.status_code, 201)
        record_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["payload"]["material_kind"], "fabric")
        self.assertEqual(created.json()["data"]["payload"]["colors"], ["黑色", "白色"])
        self.assertEqual(created.json()["data"]["payload"]["part"], "主身")
        self.assertEqual(created.json()["data"]["payload"]["supplier_name"], "青禾面辅料")
        self.assertEqual(created.json()["data"]["payload"]["supplier_code"], "SUP-QH")

        updated = self.client.patch(
            f"/api/master-data/materials/{record_id}",
            headers=self._headers(request_id="MASTER-DATA-MAT-002"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "code": "FAB-A2-001",
                "name": "A2 面料修改",
                "idempotency_key": "IDEMP-MAT-A2-001-U",
                "payload": {
                    "material_kind": "fabric",
                    "material_item_code": "FAB-A2-001",
                    "fabric_name": "A2 面料修改",
                    "colors": ["藏青"],
                    "part": "袖片",
                    "supplier_name": "锦程纺织",
                    "uom": "米",
                    "qty_per_piece": 1.5,
                    "loss_rate": 0.04,
                    "status": "active",
                },
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["name"], "A2 面料修改")
        self.assertEqual(updated.json()["data"]["payload"]["colors"], ["藏青"])
        self.assertEqual(updated.json()["data"]["payload"]["part"], "袖片")
        self.assertEqual(updated.json()["data"]["payload"]["supplier_name"], "锦程纺织")
        self.assertEqual(updated.json()["data"]["payload"]["supplier_code"], "SUP-JC")

        listed = self.client.get(
            "/api/master-data/materials?company=COMP-A&keyword=FAB-A2-001",
            headers=self._headers(request_id="MASTER-DATA-MAT-003"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)
        listed_payload = listed.json()["data"]["items"][0]["payload"]
        self.assertEqual(listed_payload["colors"], ["藏青"])
        self.assertEqual(listed_payload["part"], "袖片")

        deactivated = self.client.post(
            f"/api/master-data/materials/{record_id}/deactivate",
            headers=self._headers(request_id="MASTER-DATA-MAT-004"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "reason": "物料停用测试",
                "idempotency_key": "IDEMP-MAT-A2-001-X",
            },
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertTrue(deactivated.json()["data"]["disabled"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMasterDataRecord).filter(LyMasterDataRecord.entity_type == "material").count(), 1)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "master_data").count(), 3)

    def test_material_supplier_payload_rejects_missing_or_inactive_supplier(self) -> None:
        self._seed_supplier(code="SUP-INACTIVE", name="停用供应商", status="inactive")

        for request_no, supplier_name in (
            ("MASTER-DATA-MAT-SUP-001", "不存在供应商"),
            ("MASTER-DATA-MAT-SUP-002", "停用供应商"),
        ):
            response = self.client.post(
                "/api/master-data/materials",
                headers=self._headers(request_id=request_no),
                json={
                    "operation": "create",
                    "company": "COMP-A",
                    "code": f"FAB-{request_no[-3:]}",
                    "name": "校验面料",
                    "idempotency_key": f"IDEMP-{request_no}-C",
                    "payload": {
                        "material_kind": "fabric",
                        "material_item_code": f"FAB-{request_no[-3:]}",
                        "fabric_name": "校验面料",
                        "supplier_name": supplier_name,
                        "uom": "米",
                        "qty_per_piece": 1,
                        "loss_rate": 0,
                        "status": "active",
                    },
                },
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json()["code"], "MASTER_DATA_CONFLICT")
            self.assertIn("供应商主数据未启用或不存在", response.json()["message"])

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMasterDataRecord).filter(LyMasterDataRecord.entity_type == "material").count(), 0)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.result == "failed").count(), 2)

    def test_sample_type_dictionary_crud_uses_master_data(self) -> None:
        created = self.client.post(
            "/api/master-data/sample-types",
            headers=self._headers(request_id="MASTER-DATA-SAMPLE-TYPE-001"),
            json={
                "operation": "create",
                "company": "COMP-A",
                "code": "SMP-FIRST",
                "name": "初样",
                "idempotency_key": "IDEMP-SMP-TYPE-001-C",
                "payload": {"displayName": "初样", "usage": "设计打样", "sort": 10},
            },
        )
        self.assertEqual(created.status_code, 201)
        record_id = int(created.json()["data"]["id"])
        self.assertEqual(created.json()["data"]["entity_type"], "sample_type")

        listed = self.client.get(
            "/api/master-data/sample-types?company=COMP-A&keyword=SMP-FIRST",
            headers=self._headers(request_id="MASTER-DATA-SAMPLE-TYPE-002"),
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)
        self.assertEqual(listed.json()["data"]["items"][0]["name"], "初样")

        updated = self.client.patch(
            f"/api/master-data/sample-types/{record_id}",
            headers=self._headers(request_id="MASTER-DATA-SAMPLE-TYPE-003"),
            json={
                "operation": "update",
                "company": "COMP-A",
                "name": "头样",
                "idempotency_key": "IDEMP-SMP-TYPE-001-U",
                "payload": {"displayName": "头样", "usage": "设计打样", "sort": 20},
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["name"], "头样")
        self.assertEqual(updated.json()["data"]["payload"]["sort"], 20)

        deactivated = self.client.post(
            f"/api/master-data/sample-types/{record_id}/deactivate",
            headers=self._headers(request_id="MASTER-DATA-SAMPLE-TYPE-004"),
            json={
                "operation": "deactivate",
                "company": "COMP-A",
                "reason": "样板类型停用测试",
                "idempotency_key": "IDEMP-SMP-TYPE-001-X",
            },
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertTrue(deactivated.json()["data"]["disabled"])

        active_only = self.client.get(
            "/api/master-data/sample-types?company=COMP-A&disabled=false",
            headers=self._headers(request_id="MASTER-DATA-SAMPLE-TYPE-005"),
        )
        self.assertEqual(active_only.status_code, 200)
        self.assertEqual(active_only.json()["data"]["total"], 0)
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyMasterDataRecord).filter(LyMasterDataRecord.entity_type == "sample_type").count(), 1)
            self.assertEqual(session.query(LyOperationAuditLog).filter(LyOperationAuditLog.module == "master_data").count(), 3)

    def test_foundation_config_dictionaries_crud_use_master_data(self) -> None:
        cases = [
            ("common-addresses", "common_address", "ADDR-A2-001", {"receiver": "王收货", "phone": "13800000000"}),
            ("trade-terms", "trade_term", "TERM-A2-001", {"usage": "采购/销售"}),
            ("invoice-types", "invoice_type", "INV-A2-001", {"tax_rate": "13%"}),
            ("cost-types", "cost_type", "COST-A2-001", {"usage": "成本归集"}),
            ("size-sorts", "size_sort", "SIZE-A2-001", {"sizeGroup": "成人", "sort": 10}),
            ("distribution-channels", "distribution_channel", "CH-A2-001", {"usage": "销售订单"}),
            ("bank-accounts", "bank_account", "BANK-A2-001", {"bankName": "招商银行", "accountNo": "0001"}),
        ]
        for index, (path, entity_type, code, payload) in enumerate(cases, start=1):
            with self.subTest(path=path):
                created = self.client.post(
                    f"/api/master-data/{path}",
                    headers=self._headers(request_id=f"MASTER-DATA-CONFIG-{index}-C"),
                    json={
                        "operation": "create",
                        "company": "COMP-A",
                        "code": code,
                        "name": f"{code}-名称",
                        "idempotency_key": f"IDEMP-{code}-C",
                        "payload": {"displayName": f"{code}-显示", **payload},
                    },
                )
                self.assertEqual(created.status_code, 201)
                record_id = int(created.json()["data"]["id"])
                self.assertEqual(created.json()["data"]["entity_type"], entity_type)

                listed = self.client.get(
                    f"/api/master-data/{path}?company=COMP-A&keyword={code}",
                    headers=self._headers(request_id=f"MASTER-DATA-CONFIG-{index}-L"),
                )
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(listed.json()["data"]["total"], 1)

                updated = self.client.patch(
                    f"/api/master-data/{path}/{record_id}",
                    headers=self._headers(request_id=f"MASTER-DATA-CONFIG-{index}-U"),
                    json={
                        "operation": "update",
                        "company": "COMP-A",
                        "name": f"{code}-名称-改",
                        "idempotency_key": f"IDEMP-{code}-U",
                        "payload": {"displayName": f"{code}-显示-改", **payload},
                    },
                )
                self.assertEqual(updated.status_code, 200)
                self.assertEqual(updated.json()["data"]["name"], f"{code}-名称-改")

                deactivated = self.client.post(
                    f"/api/master-data/{path}/{record_id}/deactivate",
                    headers=self._headers(request_id=f"MASTER-DATA-CONFIG-{index}-D"),
                    json={
                        "operation": "deactivate",
                        "company": "COMP-A",
                        "reason": "基础配置停用测试",
                        "idempotency_key": f"IDEMP-{code}-D",
                    },
                )
                self.assertEqual(deactivated.status_code, 200)
                self.assertTrue(deactivated.json()["data"]["disabled"])

        with self.SessionLocal() as session:
            for _, entity_type, _, _ in cases:
                self.assertEqual(session.query(LyMasterDataRecord).filter(LyMasterDataRecord.entity_type == entity_type).count(), 1)

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
