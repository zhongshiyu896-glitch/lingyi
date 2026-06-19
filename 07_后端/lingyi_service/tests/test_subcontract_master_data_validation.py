"""Subcontract master-data validation for current frontend write paths."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.main import app
from app.models.audit import Base as AuditBase
from app.models.bom import Base as BomBase
from app.models.bom import LyApparelBom
from app.models.bom import LyApparelBomItem
from app.models.bom import LyBomOperation
from app.models.master_data import Base as MasterDataBase
from app.models.master_data import LyMasterDataRecord
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStatusLog
from app.models.subcontract import LySubcontractStockOutbox
from app.routers import subcontract as subcontract_router
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep


class SubcontractMasterDataValidationTest(unittest.TestCase):
    """Validate subcontract write paths fail closed against FastAPI master data."""

    COMPANY = "COMP-SCMD"
    ITEM_CODE = "ITEM-SCMD"
    FACTORY = "FAC-SCMD"
    WAREHOUSE = "WH-SCMD"
    SCENARIO_TAG = "Z003-SUBCONTRACT-20260619-501"

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
        LyApparelBom.__table__.to_metadata(SubcontractBase.metadata)
        SubcontractBase.metadata.create_all(bind=cls.engine)
        MasterDataBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[subcontract_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(subcontract_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractStatusLog).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyMasterDataRecord).delete()
            session.query(LyBomOperation).delete()
            session.query(LyApparelBomItem).delete()
            session.query(LyApparelBom).delete()
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-SCMD-001",
                    company=self.COMPANY,
                    item_code=self.ITEM_CODE,
                    version_no="V1",
                    is_default=True,
                    status="active",
                    created_by="seed",
                    updated_by="seed",
                )
            )
            session.add(
                LyBomOperation(
                    id=1,
                    bom_id=1,
                    process_name="外发裁剪",
                    sequence_no=1,
                    is_subcontract=True,
                    subcontract_cost_per_piece=Decimal("1"),
                )
            )
            session.add(
                LyApparelBomItem(
                    id=1,
                    bom_id=1,
                    material_item_code="MAT-SCMD",
                    qty_per_piece=Decimal("1"),
                    loss_rate=Decimal("0"),
                    uom="米",
                )
            )
            self._seed_master_record(session=session, entity_type="factory", code=self.FACTORY, name=self.FACTORY)
            self._seed_master_record(session=session, entity_type="warehouse", code=self.WAREHOUSE, name=self.WAREHOUSE)
            session.commit()

    @staticmethod
    def _headers(request_id: str) -> dict[str, str]:
        return {
            "X-LY-Dev-User": "subcontract.master.user",
            "X-LY-Dev-Roles": "Subcontract Manager",
            "X-Request-ID": request_id,
        }

    @staticmethod
    def _carrier_code(value: str) -> str:
        return subcontract_router._fnv_carrier_code(value)

    @classmethod
    def _carrier(
        cls,
        *,
        operation: str,
        idempotency_key: str,
        source_suffix: str,
        subcontract_ref: str,
        supplier_ref: str,
        item_code: str,
        quantity: str,
        status_action: str,
    ) -> dict[str, str]:
        operation_code = subcontract_router.SUBCONTRACT_OPERATION_CODE_BY_NAME[operation]
        source_ref = f"{cls.SCENARIO_TAG}:source:{source_suffix}"
        request_id = (
            f"{cls.SCENARIO_TAG}-SC-{operation_code}-"
            f"{cls._carrier_code(idempotency_key)}-"
            f"{cls._carrier_code(source_ref)}-"
            f"{cls._carrier_code(subcontract_ref)}-"
            f"{cls._carrier_code(supplier_ref)}-"
            f"{cls._carrier_code('NO-WORK-ORDER')}-"
            f"{cls._carrier_code(item_code)}-"
            f"{cls._carrier_code(status_action)}"
        )
        return {
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "scenario_tag": cls.SCENARIO_TAG,
            "source_ref": source_ref,
            "subcontract_ref": subcontract_ref,
            "supplier_ref": supplier_ref,
            "work_order_ref": "NO-WORK-ORDER",
            "operation": operation,
            "item_code": item_code,
            "quantity": quantity,
            "status_action": status_action,
        }

    def _seed_master_record(
        self,
        *,
        session,
        entity_type: str,
        code: str,
        name: str,
        status: str = "active",
    ) -> None:
        session.add(
            LyMasterDataRecord(
                entity_type=entity_type,
                company=self.COMPANY,
                code=code,
                name=name,
                status=status,
                payload={},
                created_by="seed",
                updated_by="seed",
            )
        )

    def _seed_order(self, *, order_id: int = 1, status: str = "draft") -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractOrder(
                    id=order_id,
                    subcontract_no=f"SC-SCMD-{order_id}",
                    supplier=self.FACTORY,
                    item_code=self.ITEM_CODE,
                    company=self.COMPANY,
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("20"),
                    status=status,
                    settlement_status="unsettled",
                    resource_scope_status="ready",
                )
            )
            session.commit()

    def _create_payload(self, *, supplier: str, idem: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "supplier": supplier,
            "item_code": self.ITEM_CODE,
            "company": self.COMPANY,
            "bom_id": 1,
            "planned_qty": "20",
            "process_name": "外发裁剪",
        }
        payload.update(
            self._carrier(
                operation="create",
                idempotency_key=idem,
                source_suffix=f"create:{idem}",
                subcontract_ref="NEW",
                supplier_ref=supplier,
                item_code=self.ITEM_CODE,
                quantity="20",
                status_action="create",
            )
        )
        return payload

    def _issue_payload(self, *, warehouse: str, idem: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "warehouse": warehouse,
            "materials": [{"material_item_code": "MAT-SCMD", "required_qty": "20", "issued_qty": "5"}],
        }
        payload.update(
            self._carrier(
                operation="issue_material",
                idempotency_key=idem,
                source_suffix=f"issue:{idem}",
                subcontract_ref="1",
                supplier_ref=self.FACTORY,
                item_code=self.ITEM_CODE,
                quantity="5",
                status_action="issue_material",
            )
        )
        return payload

    def _receive_payload(self, *, warehouse: str, idem: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "receipt_warehouse": warehouse,
            "received_qty": "5",
            "uom": "件",
        }
        payload.update(
            self._carrier(
                operation="receive",
                idempotency_key=idem,
                source_suffix=f"receive:{idem}",
                subcontract_ref="1",
                supplier_ref=self.FACTORY,
                item_code=self.ITEM_CODE,
                quantity="5",
                status_action="receive",
            )
        )
        return payload

    def test_create_order_rejects_inactive_factory_master(self) -> None:
        factory = "FAC-SCMD-OFF"
        with self.SessionLocal() as session:
            self._seed_master_record(session=session, entity_type="factory", code=factory, name=factory, status="inactive")
            session.commit()

        payload = self._create_payload(supplier=factory, idem="idem-scmd-create-factory-off")
        response = self.client.post("/api/subcontract/", headers=self._headers(str(payload["request_id"])), json=payload)

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_SUPPLIER_INVALID")
        self.assertIn("加工厂不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySubcontractOrder).count(), 0)

    def test_create_order_idempotent_replay_ignores_later_factory_deactivation(self) -> None:
        payload = self._create_payload(supplier=self.FACTORY, idem="idem-scmd-create-replay")
        first = self.client.post("/api/subcontract/", headers=self._headers(str(payload["request_id"])), json=payload)
        self.assertEqual(first.status_code, 200, first.text)

        with self.SessionLocal() as session:
            factory = session.query(LyMasterDataRecord).filter_by(entity_type="factory", code=self.FACTORY).one()
            factory.status = "inactive"
            session.commit()

        replay = self.client.post("/api/subcontract/", headers=self._headers(str(payload["request_id"])), json=payload)

        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["data"]["name"], first.json()["data"]["name"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySubcontractOrder).count(), 1)

    def test_issue_material_rejects_inactive_warehouse_master(self) -> None:
        self._seed_order(status="draft")
        warehouse = "WH-SCMD-OFF"
        with self.SessionLocal() as session:
            self._seed_master_record(
                session=session,
                entity_type="warehouse",
                code=warehouse,
                name=warehouse,
                status="inactive",
            )
            session.commit()

        payload = self._issue_payload(warehouse=warehouse, idem="idem-scmd-issue-wh-off")
        response = self.client.post("/api/subcontract/1/issue-material", headers=self._headers(str(payload["request_id"])), json=payload)

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_WAREHOUSE_INVALID")
        self.assertIn("发料仓库不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            order = session.query(LySubcontractOrder).one()
            self.assertEqual(str(order.status), "draft")
            self.assertEqual(session.query(LySubcontractStockOutbox).count(), 0)

    def test_issue_material_idempotent_replay_ignores_later_warehouse_deactivation(self) -> None:
        self._seed_order(status="draft")
        payload = self._issue_payload(warehouse=self.WAREHOUSE, idem="idem-scmd-issue-replay")
        first = self.client.post("/api/subcontract/1/issue-material", headers=self._headers(str(payload["request_id"])), json=payload)
        self.assertEqual(first.status_code, 200, first.text)

        with self.SessionLocal() as session:
            warehouse = session.query(LyMasterDataRecord).filter_by(entity_type="warehouse", code=self.WAREHOUSE).one()
            warehouse.status = "inactive"
            session.commit()

        replay = self.client.post("/api/subcontract/1/issue-material", headers=self._headers(str(payload["request_id"])), json=payload)

        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["data"]["outbox_id"], first.json()["data"]["outbox_id"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySubcontractStockOutbox).count(), 1)
            self.assertEqual(session.query(LySubcontractMaterial).count(), 1)

    def test_receive_rejects_inactive_warehouse_master(self) -> None:
        self._seed_order(status="issued")
        warehouse = "WH-SCMD-OFF"
        with self.SessionLocal() as session:
            self._seed_master_record(
                session=session,
                entity_type="warehouse",
                code=warehouse,
                name=warehouse,
                status="inactive",
            )
            session.commit()

        payload = self._receive_payload(warehouse=warehouse, idem="idem-scmd-receive-wh-off")
        response = self.client.post("/api/subcontract/1/receive", headers=self._headers(str(payload["request_id"])), json=payload)

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json()["code"], "SUBCONTRACT_WAREHOUSE_INVALID")
        self.assertIn("收货仓库不存在或已停用", response.json()["message"])
        with self.SessionLocal() as session:
            order = session.query(LySubcontractOrder).one()
            self.assertEqual(str(order.status), "issued")
            self.assertEqual(session.query(LySubcontractReceipt).count(), 0)
            self.assertEqual(session.query(LySubcontractStockOutbox).count(), 0)

    def test_receive_idempotent_replay_ignores_later_warehouse_deactivation(self) -> None:
        self._seed_order(status="issued")
        payload = self._receive_payload(warehouse=self.WAREHOUSE, idem="idem-scmd-receive-replay")
        first = self.client.post("/api/subcontract/1/receive", headers=self._headers(str(payload["request_id"])), json=payload)
        self.assertEqual(first.status_code, 200, first.text)

        with self.SessionLocal() as session:
            warehouse = session.query(LyMasterDataRecord).filter_by(entity_type="warehouse", code=self.WAREHOUSE).one()
            warehouse.status = "inactive"
            session.commit()

        replay = self.client.post("/api/subcontract/1/receive", headers=self._headers(str(payload["request_id"])), json=payload)

        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["data"]["outbox_id"], first.json()["data"]["outbox_id"])
        with self.SessionLocal() as session:
            self.assertEqual(session.query(LySubcontractStockOutbox).count(), 1)
            self.assertEqual(session.query(LySubcontractReceipt).count(), 1)


if __name__ == "__main__":
    unittest.main()
