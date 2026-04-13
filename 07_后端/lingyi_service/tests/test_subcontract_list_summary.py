"""Tests for subcontract list lightweight sync summary fields (TASK-002G3)."""

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
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractStockOutbox
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.subcontract import get_db_session as subcontract_db_dep


class SubcontractListSummaryTest(unittest.TestCase):
    """Ensure list endpoint returns lightweight latest outbox summary correctly."""

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
        AuditBase.metadata.create_all(bind=cls.engine)

        with cls.SessionLocal() as session:
            session.add(
                LyApparelBom(
                    id=1,
                    bom_no="BOM-LIST-001",
                    item_code="ITEM-LIST-A",
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
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"

        with self.SessionLocal() as session:
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.commit()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"X-LY-Dev-User": "list.user", "X-LY-Dev-Roles": "Subcontract Manager"}

    def _seed_order(self, *, order_id: int, no: str, supplier: str, item_code: str, company: str) -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractOrder(
                    id=order_id,
                    subcontract_no=no,
                    supplier=supplier,
                    item_code=item_code,
                    company=company,
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("100"),
                    status="processing",
                    resource_scope_status="ready",
                )
            )
            session.commit()

    def _seed_outbox(
        self,
        *,
        outbox_id: int,
        subcontract_id: int,
        stock_action: str,
        idempotency_key: str,
        status: str,
        created_at: datetime,
        stock_entry_name: str | None = None,
        last_error_code: str | None = None,
    ) -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractStockOutbox(
                    id=outbox_id,
                    subcontract_id=subcontract_id,
                    event_key=f"evt-{stock_action}-{outbox_id}",
                    stock_action=stock_action,
                    idempotency_key=idempotency_key,
                    payload_hash=f"hash-{outbox_id}",
                    payload_json={"stub": outbox_id},
                    company="COMP-LIST",
                    supplier="SUP-LIST",
                    item_code="ITEM-LIST-A",
                    warehouse="WH-LIST",
                    status=status,
                    attempts=0,
                    max_attempts=5,
                    stock_entry_name=stock_entry_name,
                    last_error_code=last_error_code,
                    request_id=f"rid-{outbox_id}",
                    created_by="seed",
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            session.commit()

    def test_list_returns_latest_issue_and_receipt_summary_fields(self) -> None:
        self._seed_order(
            order_id=201,
            no="SC-LIST-SUMMARY-001",
            supplier="SUP-LIST-ONE",
            item_code="ITEM-LIST-A",
            company="COMP-LIST",
        )
        self._seed_outbox(
            outbox_id=5001,
            subcontract_id=201,
            stock_action="issue",
            idempotency_key="idem-issue-5001",
            status="failed",
            created_at=datetime(2026, 1, 1, 10, 0, 0),
            stock_entry_name=None,
            last_error_code="ERPNEXT_SERVICE_UNAVAILABLE",
        )
        self._seed_outbox(
            outbox_id=6001,
            subcontract_id=201,
            stock_action="receipt",
            idempotency_key="idem-receipt-6001",
            status="succeeded",
            created_at=datetime(2026, 1, 1, 11, 0, 0),
            stock_entry_name="STE-REAL-6001",
            last_error_code=None,
        )

        response = self.client.get(
            "/api/subcontract/?supplier=SUP-LIST-ONE&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(len(payload["data"]["items"]), 1)

        row = payload["data"]["items"][0]
        expected_fields = {
            "latest_issue_outbox_id",
            "latest_issue_sync_status",
            "latest_issue_stock_entry_name",
            "latest_issue_idempotency_key",
            "latest_issue_error_code",
            "latest_receipt_outbox_id",
            "latest_receipt_sync_status",
            "latest_receipt_stock_entry_name",
            "latest_receipt_idempotency_key",
            "latest_receipt_error_code",
        }
        self.assertTrue(expected_fields.issubset(set(row.keys())))
        self.assertEqual(row["latest_issue_outbox_id"], 5001)
        self.assertEqual(row["latest_issue_sync_status"], "failed")
        self.assertIsNone(row["latest_issue_stock_entry_name"])
        self.assertEqual(row["latest_issue_idempotency_key"], "idem-issue-5001")
        self.assertEqual(row["latest_issue_error_code"], "ERPNEXT_SERVICE_UNAVAILABLE")
        self.assertEqual(row["latest_receipt_outbox_id"], 6001)
        self.assertEqual(row["latest_receipt_sync_status"], "succeeded")
        self.assertEqual(row["latest_receipt_stock_entry_name"], "STE-REAL-6001")
        self.assertEqual(row["latest_receipt_idempotency_key"], "idem-receipt-6001")
        self.assertIsNone(row["latest_receipt_error_code"])

    def test_list_selects_latest_issue_and_receipt_independently_without_cross_talk(self) -> None:
        self._seed_order(
            order_id=202,
            no="SC-LIST-SUMMARY-002",
            supplier="SUP-LIST-TWO",
            item_code="ITEM-LIST-A",
            company="COMP-LIST",
        )

        same_time = datetime(2026, 2, 1, 10, 0, 0)
        self._seed_outbox(
            outbox_id=7001,
            subcontract_id=202,
            stock_action="issue",
            idempotency_key="idem-issue-old",
            status="pending",
            created_at=same_time,
            stock_entry_name=None,
            last_error_code="E-ISSUE-OLD",
        )
        self._seed_outbox(
            outbox_id=7002,
            subcontract_id=202,
            stock_action="issue",
            idempotency_key="idem-issue-new",
            status="failed",
            created_at=same_time,
            stock_entry_name=None,
            last_error_code="E-ISSUE-NEW",
        )
        self._seed_outbox(
            outbox_id=8001,
            subcontract_id=202,
            stock_action="receipt",
            idempotency_key="idem-receipt-latest",
            status="succeeded",
            created_at=datetime(2026, 2, 1, 11, 0, 0),
            stock_entry_name="STE-REAL-8001",
            last_error_code=None,
        )
        self._seed_outbox(
            outbox_id=8002,
            subcontract_id=202,
            stock_action="receipt",
            idempotency_key="idem-receipt-old",
            status="failed",
            created_at=datetime(2026, 2, 1, 9, 0, 0),
            stock_entry_name=None,
            last_error_code="E-RECEIPT-OLD",
        )

        response = self.client.get(
            "/api/subcontract/?supplier=SUP-LIST-TWO&page=1&page_size=20",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "0")
        self.assertEqual(len(payload["data"]["items"]), 1)
        row = payload["data"]["items"][0]

        # issue: created_at tie -> id desc wins
        self.assertEqual(row["latest_issue_outbox_id"], 7002)
        self.assertEqual(row["latest_issue_sync_status"], "failed")
        self.assertEqual(row["latest_issue_idempotency_key"], "idem-issue-new")
        self.assertEqual(row["latest_issue_error_code"], "E-ISSUE-NEW")

        # receipt: created_at desc has priority over id desc
        self.assertEqual(row["latest_receipt_outbox_id"], 8001)
        self.assertEqual(row["latest_receipt_sync_status"], "succeeded")
        self.assertEqual(row["latest_receipt_stock_entry_name"], "STE-REAL-8001")
        self.assertEqual(row["latest_receipt_idempotency_key"], "idem-receipt-latest")
        self.assertIsNone(row["latest_receipt_error_code"])


if __name__ == "__main__":
    unittest.main()
