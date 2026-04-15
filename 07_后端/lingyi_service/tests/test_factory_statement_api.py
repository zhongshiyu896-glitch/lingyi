"""API baseline tests for factory statement router (TASK-006B)."""

from __future__ import annotations

from datetime import datetime
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
from app.models.factory_statement import Base as FactoryStatementBase
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementItem
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from app.models.subcontract import Base as SubcontractBase
from app.models.factory_statement import LyFactoryStatementOperation
from app.models.subcontract import LySubcontractInspection
from app.models.subcontract import LySubcontractOrder
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.factory_statement import get_db_session as factory_statement_db_dep


class FactoryStatementApiBase(unittest.TestCase):
    """Shared in-memory app wiring for factory-statement API tests."""

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
        FactoryStatementBase.metadata.create_all(bind=cls.engine)
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-FS-001",
                    item_code="ITEM-A",
                    version_no="v1",
                    is_default=True,
                    status="active",
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
        app.dependency_overrides[factory_statement_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(factory_statement_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        os.environ["LINGYI_ERPNEXT_BASE_URL"] = ""

        with self.SessionLocal() as session:
            session.query(LyFactoryStatementPayableOutbox).delete()
            session.query(LyFactoryStatementOperation).delete()
            session.query(LyFactoryStatementItem).delete()
            session.query(LyFactoryStatement).delete()
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()
            self._seed_default_sources(session)
            session.commit()

    @staticmethod
    def _headers(role: str = "Finance Manager", user: str = "factory.statement.user") -> dict[str, str]:
        return {
            "X-LY-Dev-User": user,
            "X-LY-Dev-Roles": role,
        }

    @staticmethod
    def _create_payload(
        *,
        company: str = "COMP-A",
        supplier: str = "SUP-A",
        from_date: str = "2026-04-01",
        to_date: str = "2026-04-30",
        idempotency_key: str = "idem-fs-001",
    ) -> dict[str, str]:
        return {
            "company": company,
            "supplier": supplier,
            "from_date": from_date,
            "to_date": to_date,
            "idempotency_key": idempotency_key,
        }

    @staticmethod
    def _seed_default_sources(session) -> None:
        session.add(
            LySubcontractOrder(
                id=200,
                subcontract_no="SC-FS-200",
                supplier="SUP-A",
                item_code="ITEM-A",
                company="COMP-A",
                bom_id=1,
                process_name="外发裁剪",
                planned_qty=Decimal("100"),
                status="processing",
            )
        )
        session.add(
            LySubcontractOrder(
                id=201,
                subcontract_no="SC-FS-201",
                supplier="SUP-B",
                item_code="ITEM-A",
                company="COMP-A",
                bom_id=1,
                process_name="外发裁剪",
                planned_qty=Decimal("100"),
                status="processing",
            )
        )
        session.flush()

        session.add_all(
            [
                LySubcontractInspection(
                    id=300,
                    subcontract_id=200,
                    company="COMP-A",
                    inspection_no="SIN-FS-300",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("200"),
                    rejected_qty=Decimal("10"),
                    accepted_qty=Decimal("190"),
                    rejected_rate=Decimal("0.05"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("2000"),
                    deduction_amount=Decimal("100"),
                    net_amount=Decimal("1900"),
                    settlement_status="unsettled",
                    status="inspected",
                    inspected_by="seed",
                    inspected_at=datetime(2026, 4, 10, 10, 0, 0),
                    settlement_line_key="subcontract_inspection:300",
                ),
                LySubcontractInspection(
                    id=301,
                    subcontract_id=200,
                    company="COMP-A",
                    inspection_no="SIN-FS-301",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("300"),
                    rejected_qty=Decimal("0"),
                    accepted_qty=Decimal("300"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("3000"),
                    deduction_amount=Decimal("200"),
                    net_amount=Decimal("2800"),
                    settlement_status="unsettled",
                    status="inspected",
                    inspected_by="seed",
                    inspected_at=datetime(2026, 4, 11, 10, 0, 0),
                    settlement_line_key="subcontract_inspection:301",
                ),
                LySubcontractInspection(
                    id=302,
                    subcontract_id=201,
                    company="COMP-A",
                    inspection_no="SIN-FS-302",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("8"),
                    rejected_qty=Decimal("0"),
                    accepted_qty=Decimal("8"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("80"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("80"),
                    settlement_status="unsettled",
                    status="inspected",
                    inspected_by="seed",
                    inspected_at=datetime(2026, 4, 12, 10, 0, 0),
                    settlement_line_key="subcontract_inspection:302",
                ),
            ]
        )


class FactoryStatementApiTest(FactoryStatementApiBase):
    """Core API behavior tests for draft generation/list/detail."""

    def test_create_draft_from_two_inspections_and_lock_sources(self) -> None:
        response = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-create-001"),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")

        data = payload["data"]
        self.assertEqual(data["source_count"], 2)
        self.assertEqual(Decimal(data["gross_amount"]), Decimal("5000"))
        self.assertEqual(Decimal(data["deduction_amount"]), Decimal("300"))
        self.assertEqual(Decimal(data["net_amount"]), Decimal("4700"))

        with self.SessionLocal() as session:
            inspections = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.id.in_([300, 301]))
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )
            self.assertEqual(len(inspections), 2)
            for row in inspections:
                self.assertEqual(str(row.settlement_status), "statement_locked")
                self.assertIsNotNone(row.statement_id)
                self.assertIsNotNone(row.statement_no)
                self.assertEqual(str(row.settlement_locked_by), "factory.statement.user")
                self.assertIsNotNone(row.settlement_locked_at)

    def test_rejected_rate_is_zero_when_total_inspected_qty_is_zero(self) -> None:
        with self.SessionLocal() as session:
            session.query(LySubcontractInspection).delete()
            session.query(LySubcontractOrder).delete()
            session.add(
                LySubcontractOrder(
                    id=210,
                    subcontract_no="SC-FS-210",
                    supplier="SUP-Z",
                    item_code="ITEM-A",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("10"),
                    status="processing",
                )
            )
            session.flush()
            session.add(
                LySubcontractInspection(
                    id=310,
                    subcontract_id=210,
                    company="COMP-A",
                    inspection_no="SIN-FS-310",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    accepted_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("100"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("100"),
                    settlement_status="unsettled",
                    status="inspected",
                    inspected_by="seed",
                    inspected_at=datetime(2026, 4, 15, 10, 0, 0),
                    settlement_line_key="subcontract_inspection:310",
                )
            )
            session.commit()

        response = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(
                supplier="SUP-Z",
                from_date="2026-04-15",
                to_date="2026-04-15",
                idempotency_key="idem-zero-inspected",
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(Decimal(response.json()["data"]["rejected_rate"]), Decimal("0"))

    def test_detail_reads_snapshot_items_not_live_inspection_recompute(self) -> None:
        create = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-detail-snapshot"),
        )
        self.assertEqual(create.status_code, 200)
        statement_id = int(create.json()["data"]["statement_id"])

        with self.SessionLocal() as session:
            inspection = session.query(LySubcontractInspection).filter(LySubcontractInspection.id == 300).first()
            self.assertIsNotNone(inspection)
            inspection.gross_amount = Decimal("999999")
            inspection.deduction_amount = Decimal("888888")
            inspection.net_amount = Decimal("111111")
            session.commit()

        detail = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail.status_code, 200)
        body = detail.json()
        self.assertEqual(body["code"], "0")
        self.assertEqual(len(body["data"]["items"]), 2)
        first = body["data"]["items"][0]
        self.assertEqual(Decimal(first["gross_amount"]), Decimal("2000"))
        self.assertEqual(Decimal(first["deduction_amount"]), Decimal("100"))
        self.assertEqual(Decimal(first["net_amount"]), Decimal("1900"))

    def test_locked_source_in_different_scope_returns_source_locked(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(
                idempotency_key="idem-locked-first",
                from_date="2026-04-10",
                to_date="2026-04-10",
            ),
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(
                idempotency_key="idem-locked-second",
                from_date="2026-04-09",
                to_date="2026-04-10",
            ),
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED")

        with self.SessionLocal() as session:
            total = session.query(LyFactoryStatement).count()
        self.assertEqual(total, 1)

    def test_list_and_detail_success(self) -> None:
        create = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-list-detail"),
        )
        self.assertEqual(create.status_code, 200)
        statement_id = int(create.json()["data"]["statement_id"])

        list_response = self.client.get(
            "/api/factory-statements/",
            headers=self._headers(),
            params={"company": "COMP-A", "supplier": "SUP-A"},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["code"], "0")
        self.assertEqual(list_response.json()["data"]["total"], 1)
        list_item = list_response.json()["data"]["items"][0]
        self.assertIn("payable_outbox_id", list_item)
        self.assertIn("payable_outbox_status", list_item)
        self.assertIn("purchase_invoice_name", list_item)
        self.assertIn("payable_error_code", list_item)
        self.assertIn("payable_error_message", list_item)
        self.assertIsNone(list_item["payable_outbox_status"])
        self.assertIsNone(list_item["purchase_invoice_name"])

        detail_response = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["code"], "0")
        detail_data = detail_response.json()["data"]
        self.assertIn("payable_outbox_id", detail_data)
        self.assertIn("payable_outbox_status", detail_data)
        self.assertIn("purchase_invoice_name", detail_data)
        self.assertIn("payable_error_code", detail_data)
        self.assertIn("payable_error_message", detail_data)
        self.assertIn("logs", detail_data)
        self.assertIn("payable_outboxes", detail_data)
        self.assertIsInstance(detail_data["logs"], list)
        self.assertIsInstance(detail_data["payable_outboxes"], list)
        self.assertGreaterEqual(len(detail_data["logs"]), 1)
        first_log = detail_data["logs"][0]
        self.assertIn("action", first_log)
        self.assertIn("operator", first_log)
        self.assertIn("operated_at", first_log)
        self.assertIn("remark", first_log)

    def test_confirm_changes_status_to_confirmed(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-confirm-success"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-confirm-op", "remark": "confirm now"},
        )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["code"], "0")
        self.assertEqual(confirmed.json()["data"]["status"], "confirmed")
        self.assertEqual(confirmed.json()["data"]["confirmed_by"], "factory.statement.user")
        self.assertIsNotNone(confirmed.json()["data"]["confirmed_at"])

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            self.assertEqual(str(statement.statement_status), "confirmed")

    def test_cancel_draft_releases_inspections(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-cancel-draft"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-draft-op", "reason": "mistake"},
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["code"], "0")
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled.json()["data"]["cancelled_by"], "factory.statement.user")
        self.assertIsNotNone(cancelled.json()["data"]["cancelled_at"])

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            self.assertEqual(str(statement.statement_status), "cancelled")
            inspections = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.id.in_([300, 301]))
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )
            self.assertEqual(len(inspections), 2)
            for row in inspections:
                self.assertEqual(str(row.settlement_status), "unsettled")
                self.assertIsNone(row.statement_id)
                self.assertIsNone(row.statement_no)

    def test_cancel_confirmed_releases_inspections(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-cancel-confirmed"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-confirm-before-cancel", "remark": "ok"},
        )
        self.assertEqual(confirmed.status_code, 200)

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-after-confirm", "reason": "reopen"},
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["code"], "0")
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")

        with self.SessionLocal() as session:
            inspections = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.id.in_([300, 301]))
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )
            self.assertEqual(len(inspections), 2)
            self.assertTrue(all(str(row.settlement_status) == "unsettled" for row in inspections))

    def test_cancelled_statement_source_can_rebuild_new_statement(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-cancel-rebuild-1"),
        )
        self.assertEqual(first.status_code, 200)
        first_statement_id = int(first.json()["data"]["statement_id"])

        cancelled = self.client.post(
            f"/api/factory-statements/{first_statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-rebuild-op", "reason": "cancel for rebuild"},
        )
        self.assertEqual(cancelled.status_code, 200)

        rebuilt = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-cancel-rebuild-2"),
        )
        self.assertEqual(rebuilt.status_code, 200)
        rebuilt_statement_id = int(rebuilt.json()["data"]["statement_id"])
        self.assertNotEqual(first_statement_id, rebuilt_statement_id)

    def test_payable_draft_created_statement_cannot_cancel(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-payable-cannot-cancel"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            statement.statement_status = "payable_draft_created"
            session.commit()

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-payable-cancel-op", "reason": "should fail"},
        )
        self.assertEqual(cancelled.status_code, 409)
        self.assertEqual(cancelled.json()["code"], "FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED")


if __name__ == "__main__":
    unittest.main()
