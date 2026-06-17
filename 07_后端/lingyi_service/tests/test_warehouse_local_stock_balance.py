"""A6 local warehouse ledger and balance recomputation tests."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.quality import Base as QualityBase
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStockOutbox
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.services.warehouse_service import WarehouseService


class WarehouseLocalStockBalanceTest(unittest.TestCase):
    """Validate local stock ledger and summary use the same movement source."""

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
        QualityBase.metadata.create_all(bind=cls.engine)
        SubcontractBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_DB_URL"] = "sqlite:///./lingyi_service.local.db"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyWarehouseStockEntryOutboxEvent).delete()
            session.query(LyWarehouseStockEntryDraftItem).delete()
            session.query(LyWarehouseStockEntryDraft).delete()
            session.commit()

    @staticmethod
    def _add_draft(
        session,
        *,
        source_id: str,
        purpose: str,
        qty: str,
        business_date: date,
        source_warehouse: str | None = None,
        target_warehouse: str | None = None,
        status: str = "pending_outbox",
    ) -> None:
        created_at = datetime.combine(business_date, datetime.min.time(), timezone.utc)
        draft = LyWarehouseStockEntryDraft(
            company="COMP-A",
            purpose=purpose,
            source_type="manual",
            source_id=source_id,
            source_warehouse=source_warehouse,
            target_warehouse=target_warehouse,
            status=status,
            created_by="warehouse.test",
            created_at=created_at,
            idempotency_key=f"idem-{source_id}",
            event_key=f"event-{source_id}",
        )
        session.add(draft)
        session.flush()
        session.add(
            LyWarehouseStockEntryDraftItem(
                draft_id=draft.id,
                company="COMP-A",
                item_code="FAB-A",
                qty=Decimal(qty),
                uom="米",
                source_warehouse=source_warehouse,
                target_warehouse=target_warehouse,
            )
        )
        session.add(
            LyWarehouseStockEntryOutboxEvent(
                draft_id=draft.id,
                event_type="warehouse_stock_entry_sync",
                event_key=f"event-{source_id}",
                payload={"business_date": business_date.isoformat()},
                status="in_pending",
                retry_count=0,
                created_at=created_at,
            )
        )

    def _seed_movements(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="RCPT-001",
                purpose="Material Receipt",
                target_warehouse="WH-A",
                qty="10",
                business_date=date(2026, 6, 1),
            )
            self._add_draft(
                session,
                source_id="ISSUE-001",
                purpose="Material Issue",
                source_warehouse="WH-A",
                qty="3",
                business_date=date(2026, 6, 2),
            )
            self._add_draft(
                session,
                source_id="TRANSFER-001",
                purpose="Material Transfer",
                source_warehouse="WH-A",
                target_warehouse="WH-B",
                qty="2",
                business_date=date(2026, 6, 3),
            )
            self._add_draft(
                session,
                source_id="CANCELLED-001",
                purpose="Material Receipt",
                target_warehouse="WH-A",
                qty="99",
                business_date=date(2026, 6, 4),
                status="cancelled",
            )
            session.commit()

    def test_ledger_and_summary_recompute_balance_from_draft_movements(self) -> None:
        self._seed_movements()
        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            ledger = service.list_stock_ledger(
                company="COMP-A",
                warehouse=None,
                item_code="FAB-A",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            summary = service.get_stock_summary(company="COMP-A", warehouse=None, item_code="FAB-A")

        self.assertEqual(ledger.total, 4)
        movement_rows = [
            (row.warehouse, row.posting_date.isoformat(), Decimal(str(row.actual_qty)), Decimal(str(row.qty_after_transaction)))
            for row in ledger.items
        ]
        self.assertEqual(
            movement_rows,
            [
                ("WH-A", "2026-06-01", Decimal("10.000000"), Decimal("10.000000")),
                ("WH-A", "2026-06-02", Decimal("-3.000000"), Decimal("7.000000")),
                ("WH-A", "2026-06-03", Decimal("-2.000000"), Decimal("5.000000")),
                ("WH-B", "2026-06-03", Decimal("2.000000"), Decimal("2.000000")),
            ],
        )
        summary_by_warehouse = {row.warehouse: Decimal(str(row.actual_qty)) for row in summary.items}
        self.assertEqual(summary_by_warehouse, {"WH-A": Decimal("5.000000"), "WH-B": Decimal("2.000000")})
        self.assertTrue(all(not row.threshold_missing for row in summary.items))

    def test_date_filter_keeps_running_balance_from_prior_movements(self) -> None:
        self._seed_movements()
        with self.SessionLocal() as session:
            ledger = WarehouseService(session=session).list_stock_ledger(
                company="COMP-A",
                warehouse="WH-A",
                item_code="FAB-A",
                from_date=date(2026, 6, 2),
                to_date=date(2026, 6, 3),
                page=1,
                page_size=20,
            )

        self.assertEqual(ledger.total, 2)
        self.assertEqual([Decimal(str(row.qty_after_transaction)) for row in ledger.items], [Decimal("7.000000"), Decimal("5.000000")])

    def test_pagination_reports_total_after_movement_filter(self) -> None:
        self._seed_movements()
        with self.SessionLocal() as session:
            ledger = WarehouseService(session=session).list_stock_ledger(
                company="COMP-A",
                warehouse=None,
                item_code="FAB-A",
                from_date=None,
                to_date=None,
                page=2,
                page_size=2,
            )

        self.assertEqual(ledger.total, 4)
        self.assertEqual(len(ledger.items), 2)
        self.assertEqual(ledger.items[0].warehouse, "WH-A")
        self.assertEqual(Decimal(str(ledger.items[0].qty_after_transaction)), Decimal("5.000000"))

    def test_subcontract_issue_and_receipt_join_unified_stock_balance(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="RCPT-SUB-BASE",
                purpose="Material Receipt",
                target_warehouse="WH-A",
                qty="10",
                business_date=date(2026, 6, 1),
            )
            session.add(
                LySubcontractOrder(
                    id=901,
                    subcontract_no="SC-BAL-001",
                    supplier="BAL-FAC",
                    item_code="STYLE-BAL",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("5"),
                    issued_qty=Decimal("4"),
                    received_qty=Decimal("3"),
                    inspected_qty=Decimal("0"),
                    accepted_qty=Decimal("0"),
                    status="waiting_inspection",
                    settlement_status="unsettled",
                )
            )
            session.add_all(
                [
                    LySubcontractStockOutbox(
                        id=901,
                        subcontract_id=901,
                        event_key="bal-issue-outbox",
                        stock_action="issue",
                        idempotency_key="bal-issue-idem",
                        payload_hash="bal-issue-hash",
                        company="COMP-A",
                        supplier="BAL-FAC",
                        item_code="STYLE-BAL",
                        warehouse="WH-A",
                        action="issue",
                        status="succeeded",
                        stock_entry_name="LOCAL-ISSUE-BAL-001",
                        request_id="bal-issue-request",
                        created_by="warehouse.test",
                        created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                    ),
                    LySubcontractStockOutbox(
                        id=902,
                        subcontract_id=901,
                        event_key="bal-receipt-outbox",
                        stock_action="receipt",
                        idempotency_key="bal-receipt-idem",
                        payload_hash="bal-receipt-hash",
                        company="COMP-A",
                        supplier="BAL-FAC",
                        item_code="STYLE-BAL",
                        warehouse="WH-FG",
                        action="receipt",
                        status="succeeded",
                        stock_entry_name="LOCAL-RECEIPT-BAL-001",
                        request_id="bal-receipt-request",
                        created_by="warehouse.test",
                        created_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
                    ),
                ]
            )
            session.add(
                LySubcontractMaterial(
                    id=901,
                    subcontract_id=901,
                    stock_outbox_id=901,
                    company="COMP-A",
                    issue_batch_no="SIB-BAL-001",
                    material_item_code="FAB-A",
                    required_qty=Decimal("5"),
                    issued_qty=Decimal("4"),
                    sync_status="succeeded",
                    stock_entry_name="LOCAL-ISSUE-BAL-001",
                    created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
            )
            session.add(
                LySubcontractReceipt(
                    id=901,
                    subcontract_id=901,
                    stock_outbox_id=902,
                    company="COMP-A",
                    receipt_batch_no="SRB-BAL-001",
                    receipt_warehouse="WH-FG",
                    item_code="STYLE-BAL",
                    uom="件",
                    received_qty=Decimal("3"),
                    sync_status="succeeded",
                    idempotency_key="bal-receipt-idem",
                    payload_hash="bal-receipt-hash",
                    received_by="warehouse.test",
                    received_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
                    stock_entry_name="LOCAL-RECEIPT-BAL-001",
                    inspected_qty=Decimal("0"),
                    rejected_qty=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("0"),
                    inspect_status="pending",
                    created_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
                )
            )
            session.commit()

        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            material_ledger = service.list_stock_ledger(
                company="COMP-A",
                warehouse="WH-A",
                item_code="FAB-A",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            output_ledger = service.list_stock_ledger(
                company="COMP-A",
                warehouse="WH-FG",
                item_code="STYLE-BAL",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            material_summary = service.get_stock_summary(company="COMP-A", warehouse="WH-A", item_code="FAB-A")
            output_summary = service.get_stock_summary(company="COMP-A", warehouse="WH-FG", item_code="STYLE-BAL")

        self.assertEqual(
            [(row.voucher_type, row.voucher_no, Decimal(str(row.actual_qty)), Decimal(str(row.qty_after_transaction))) for row in material_ledger.items],
            [
                ("Stock Entry Draft/Material Receipt", "DRAFT-1", Decimal("10.000000"), Decimal("10.000000")),
                ("Subcontract/Material Issue", "SIB-BAL-001", Decimal("-4.000000"), Decimal("6.000000")),
            ],
        )
        self.assertEqual(output_ledger.total, 1)
        self.assertEqual(output_ledger.items[0].voucher_type, "Subcontract/Material Receipt")
        self.assertEqual(output_ledger.items[0].voucher_no, "SRB-BAL-001")
        self.assertEqual(Decimal(str(output_ledger.items[0].qty_after_transaction)), Decimal("3.000000"))
        self.assertEqual(Decimal(str(material_summary.items[0].actual_qty)), Decimal("6.000000"))
        self.assertEqual(Decimal(str(output_summary.items[0].actual_qty)), Decimal("3.000000"))

    def test_pending_subcontract_outbox_is_excluded_from_unified_stock_balance(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="RCPT-PENDING-SUB-BASE",
                purpose="Material Receipt",
                target_warehouse="WH-A",
                qty="10",
                business_date=date(2026, 6, 1),
            )
            session.add(
                LySubcontractOrder(
                    id=951,
                    subcontract_no="SC-BAL-PENDING",
                    supplier="BAL-FAC",
                    item_code="STYLE-BAL-PENDING",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("5"),
                    issued_qty=Decimal("4"),
                    received_qty=Decimal("0"),
                    inspected_qty=Decimal("0"),
                    accepted_qty=Decimal("0"),
                    status="issued",
                    settlement_status="unsettled",
                )
            )
            session.add(
                LySubcontractStockOutbox(
                    id=951,
                    subcontract_id=951,
                    event_key="bal-pending-issue-outbox",
                    stock_action="issue",
                    idempotency_key="bal-pending-issue-idem",
                    payload_hash="bal-pending-issue-hash",
                    company="COMP-A",
                    supplier="BAL-FAC",
                    item_code="STYLE-BAL-PENDING",
                    warehouse="WH-A",
                    action="issue",
                    status="pending",
                    request_id="bal-pending-issue-request",
                    created_by="warehouse.test",
                    created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
            )
            session.add(
                LySubcontractMaterial(
                    id=951,
                    subcontract_id=951,
                    stock_outbox_id=951,
                    company="COMP-A",
                    issue_batch_no="SIB-BAL-PENDING",
                    material_item_code="FAB-A",
                    required_qty=Decimal("5"),
                    issued_qty=Decimal("4"),
                    sync_status="pending",
                    stock_entry_name=None,
                    created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
            )
            session.commit()

        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            ledger = service.list_stock_ledger(
                company="COMP-A",
                warehouse="WH-A",
                item_code="FAB-A",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            summary = service.get_stock_summary(company="COMP-A", warehouse="WH-A", item_code="FAB-A")

        self.assertEqual(ledger.total, 1)
        self.assertEqual(ledger.items[0].voucher_type, "Stock Entry Draft/Material Receipt")
        self.assertEqual(Decimal(str(ledger.items[0].qty_after_transaction)), Decimal("10.000000"))
        self.assertEqual(Decimal(str(summary.items[0].actual_qty)), Decimal("10.000000"))


if __name__ == "__main__":
    unittest.main()
