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

from app.models.material_purchase import Base as MaterialPurchaseBase
from app.models.material_purchase import LyMaterialPurchaseOrder
from app.models.material_purchase import LyMaterialPurchaseOrderItem
from app.models.quality import Base as QualityBase
from app.models.quality import LyQualityInspection
from app.models.quality_outbox import LyQualityOutbox
from app.models.subcontract import Base as SubcontractBase
from app.models.subcontract import LySubcontractMaterial
from app.models.subcontract import LySubcontractOrder
from app.models.subcontract import LySubcontractReceipt
from app.models.subcontract import LySubcontractStockOutbox
from app.models.warehouse import LyWarehouseStockEntryDraft
from app.models.warehouse import LyWarehouseStockEntryDraftItem
from app.models.warehouse import LyWarehouseStockEntryOutboxEvent
from app.models.warehouse import LyWarehouseStockLedgerEntry
from app.models.warehouse import LyWarehouseInventoryCount
from app.models.warehouse import LyWarehouseInventoryCountItem
from app.schemas.warehouse import WarehouseFactoryReturnMaterialDraftRequest
from app.schemas.warehouse import WarehouseStockEntryDraftCreateRequest
from app.schemas.warehouse import WarehouseStockEntryDraftItemCreateRequest
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
        MaterialPurchaseBase.metadata.create_all(bind=cls.engine)
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
            session.query(LyQualityOutbox).delete()
            session.query(LyQualityInspection).delete()
            session.query(LySubcontractReceipt).delete()
            session.query(LySubcontractMaterial).delete()
            session.query(LySubcontractStockOutbox).delete()
            session.query(LySubcontractOrder).delete()
            session.query(LyMaterialPurchaseOrderItem).delete()
            session.query(LyMaterialPurchaseOrder).delete()
            session.query(LyWarehouseInventoryCountItem).delete()
            session.query(LyWarehouseInventoryCount).delete()
            session.query(LyWarehouseStockLedgerEntry).delete()
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
        item_code: str = "FAB-A",
        source_type: str = "manual",
        status: str = "pending_outbox",
    ) -> None:
        created_at = datetime.combine(business_date, datetime.min.time(), timezone.utc)
        draft = LyWarehouseStockEntryDraft(
            company="COMP-A",
            purpose=purpose,
            source_type=source_type,
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
                item_code=item_code,
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

    def _projected_ledger_rows(
        self,
        session,
        *,
        item_code: str = "FAB-A",
        warehouse: str | None = None,
        status: str | None = None,
    ) -> list[LyWarehouseStockLedgerEntry]:
        query = session.query(LyWarehouseStockLedgerEntry).filter(
            LyWarehouseStockLedgerEntry.company == "COMP-A",
            LyWarehouseStockLedgerEntry.item_code == item_code,
        )
        if warehouse is not None:
            query = query.filter(LyWarehouseStockLedgerEntry.warehouse == warehouse)
        if status is not None:
            query = query.filter(LyWarehouseStockLedgerEntry.status == status)
        return (
            query.order_by(
                LyWarehouseStockLedgerEntry.sort_at.asc(),
                LyWarehouseStockLedgerEntry.source_id.asc(),
                LyWarehouseStockLedgerEntry.source_line_id.asc(),
                LyWarehouseStockLedgerEntry.sequence.asc(),
                LyWarehouseStockLedgerEntry.warehouse.asc(),
            )
            .all()
        )

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
        self.assertTrue(all(row.threshold_missing for row in summary.items))

    def test_stock_entry_create_projects_counted_draft_into_durable_ledger(self) -> None:
        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            service.create_stock_entry_draft(
                payload=WarehouseStockEntryDraftCreateRequest(
                    company="COMP-A",
                    purpose="Material Issue",
                    source_type="manual_issue",
                    source_id="CREATE-PROJECT-001",
                    source_ref="CREATE-PROJECT-001",
                    warehouse="WH-A",
                    item_code="FAB-A",
                    operation="create_stock_entry_draft",
                    quantity=Decimal("3"),
                    business_date=date(2026, 6, 5),
                    status_action="create",
                    scenario_tag="TEST",
                    source_warehouse="WH-A",
                    target_warehouse=None,
                    idempotency_key="idem-create-project-001",
                    items=[
                        WarehouseStockEntryDraftItemCreateRequest(
                            item_code="FAB-A",
                            qty=Decimal("3"),
                            uom="米",
                            source_warehouse="WH-A",
                        )
                    ],
                ),
                current_user="warehouse.test",
            )
            projected_rows = self._projected_ledger_rows(session, warehouse="WH-A", status="active")

        self.assertEqual(len(projected_rows), 1)
        self.assertEqual(projected_rows[0].voucher_type, "Stock Entry Draft/Material Issue")
        self.assertEqual(Decimal(str(projected_rows[0].actual_qty)), Decimal("-3.000000"))

    def test_stock_entry_audit_projects_draft_receipt_into_durable_ledger(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="AUDIT-PROJECT-001",
                purpose="Material Receipt",
                target_warehouse="WH-A",
                qty="5",
                business_date=date(2026, 6, 6),
                status="draft",
            )
            session.flush()
            draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_id="AUDIT-PROJECT-001").one()

            service = WarehouseService(session=session)
            service.audit_stock_entry_draft(draft_id=int(draft.id))
            projected_rows = self._projected_ledger_rows(session, warehouse="WH-A", status="active")

        self.assertEqual(len(projected_rows), 1)
        self.assertEqual(projected_rows[0].voucher_type, "Stock Entry Draft/Material Receipt")
        self.assertEqual(Decimal(str(projected_rows[0].actual_qty)), Decimal("5.000000"))

    def test_stock_entry_cancel_voids_projected_durable_ledger_rows(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="CANCEL-PROJECT-001",
                purpose="Material Issue",
                source_warehouse="WH-A",
                qty="4",
                business_date=date(2026, 6, 7),
            )
            session.flush()
            draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_id="CANCEL-PROJECT-001").one()
            service = WarehouseService(session=session)
            service.project_local_stock_ledger_entries(company="COMP-A", warehouse="WH-A", item_code="FAB-A")

            service.cancel_stock_entry_draft(
                draft_id=int(draft.id),
                reason="cancel projected issue",
                cancelled_by="warehouse.test",
            )
            active_rows = self._projected_ledger_rows(session, warehouse="WH-A", status="active")
            voided_rows = self._projected_ledger_rows(session, warehouse="WH-A", status="voided")

        self.assertEqual(active_rows, [])
        self.assertEqual(len(voided_rows), 1)
        self.assertEqual(Decimal(str(voided_rows[0].actual_qty)), Decimal("-4.000000"))

    def test_material_hold_release_voids_projected_durable_ledger_rows(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="HOLD-PROJECT-001",
                purpose="Material Issue",
                source_warehouse="WH-A",
                qty="2",
                business_date=date(2026, 6, 8),
                source_type="material_hold",
            )
            session.flush()
            draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_id="HOLD-PROJECT-001").one()
            service = WarehouseService(session=session)
            service.project_local_stock_ledger_entries(company="COMP-A", warehouse="WH-A", item_code="FAB-A")

            service.release_material_hold_draft(
                draft_id=int(draft.id),
                reason="release projected hold",
                released_by="warehouse.test",
            )
            active_rows = self._projected_ledger_rows(session, warehouse="WH-A", status="active")
            voided_rows = self._projected_ledger_rows(session, warehouse="WH-A", status="voided")

        self.assertEqual(active_rows, [])
        self.assertEqual(len(voided_rows), 1)
        self.assertEqual(Decimal(str(voided_rows[0].actual_qty)), Decimal("-2.000000"))

    def test_stock_ledger_projector_persists_dynamic_movements_idempotently(self) -> None:
        self._seed_movements()
        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            first = service.project_local_stock_ledger_entries(company="COMP-A", warehouse=None, item_code="FAB-A")
            second = service.project_local_stock_ledger_entries(company="COMP-A", warehouse=None, item_code="FAB-A")
            dynamic_ledger = service.list_stock_ledger(
                company="COMP-A",
                warehouse=None,
                item_code="FAB-A",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            projected_rows = (
                session.query(LyWarehouseStockLedgerEntry)
                .filter(
                    LyWarehouseStockLedgerEntry.company == "COMP-A",
                    LyWarehouseStockLedgerEntry.item_code == "FAB-A",
                )
                .order_by(
                    LyWarehouseStockLedgerEntry.sort_at.asc(),
                    LyWarehouseStockLedgerEntry.source_id.asc(),
                    LyWarehouseStockLedgerEntry.source_line_id.asc(),
                    LyWarehouseStockLedgerEntry.sequence.asc(),
                    LyWarehouseStockLedgerEntry.warehouse.asc(),
                )
                .all()
            )

        self.assertEqual(first, {"inserted": 4, "updated": 0, "voided": 0})
        self.assertEqual(second, {"inserted": 0, "updated": 0, "voided": 0})
        self.assertEqual(len(projected_rows), dynamic_ledger.total)
        self.assertEqual(
            [
                (row.warehouse, row.posting_date.isoformat(), Decimal(str(row.actual_qty)), row.status)
                for row in projected_rows
            ],
            [
                (row.warehouse, row.posting_date.isoformat(), Decimal(str(row.actual_qty)), "active")
                for row in dynamic_ledger.items
            ],
        )

    def test_stock_ledger_projector_voids_cancelled_dynamic_movements(self) -> None:
        self._seed_movements()
        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            service.project_local_stock_ledger_entries(company="COMP-A", warehouse=None, item_code="FAB-A")
            draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_id="ISSUE-001").one()
            draft.status = "cancelled"
            session.flush()

            result = service.project_local_stock_ledger_entries(company="COMP-A", warehouse=None, item_code="FAB-A")
            active_rows = (
                session.query(LyWarehouseStockLedgerEntry)
                .filter(
                    LyWarehouseStockLedgerEntry.company == "COMP-A",
                    LyWarehouseStockLedgerEntry.item_code == "FAB-A",
                    LyWarehouseStockLedgerEntry.status == "active",
                )
                .order_by(LyWarehouseStockLedgerEntry.sort_at.asc(), LyWarehouseStockLedgerEntry.sequence.asc())
                .all()
            )
            voided_rows = (
                session.query(LyWarehouseStockLedgerEntry)
                .filter(
                    LyWarehouseStockLedgerEntry.company == "COMP-A",
                    LyWarehouseStockLedgerEntry.item_code == "FAB-A",
                    LyWarehouseStockLedgerEntry.status == "voided",
                )
                .all()
            )

        self.assertEqual(result, {"inserted": 0, "updated": 0, "voided": 1})
        self.assertEqual([Decimal(str(row.actual_qty)) for row in active_rows], [Decimal("10.000000"), Decimal("-2.000000"), Decimal("2.000000")])
        self.assertEqual(len(voided_rows), 1)
        self.assertEqual(Decimal(str(voided_rows[0].actual_qty)), Decimal("-3.000000"))

    def test_material_purchase_receipt_draft_waits_for_audit_before_stock_readback(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="PO-DRAFT-001",
                purpose="Material Receipt",
                target_warehouse="WH-A",
                qty="10",
                business_date=date(2026, 6, 1),
                source_type="material_purchase_order",
                status="draft",
            )
            session.commit()

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
            receipts = service.list_local_purchase_receipts(
                company="COMP-A",
                warehouse="WH-A",
                item_code=None,
                material_item_code="FAB-A",
                purchase_no=None,
                supplier_name=None,
                status=None,
                page=1,
                page_size=20,
            )

            self.assertEqual(ledger.total, 0)
            self.assertEqual(summary.items, [])
            self.assertEqual(receipts.total, 0)

            draft = session.query(LyWarehouseStockEntryDraft).filter_by(source_id="PO-DRAFT-001").one()
            draft.status = "pending_outbox"
            session.commit()

            ledger_after_audit = service.list_stock_ledger(
                company="COMP-A",
                warehouse="WH-A",
                item_code="FAB-A",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            summary_after_audit = service.get_stock_summary(company="COMP-A", warehouse="WH-A", item_code="FAB-A")
            receipts_after_audit = service.list_local_purchase_receipts(
                company="COMP-A",
                warehouse="WH-A",
                item_code=None,
                material_item_code="FAB-A",
                purchase_no=None,
                supplier_name=None,
                status=None,
                page=1,
                page_size=20,
            )

        self.assertEqual(ledger_after_audit.total, 1)
        self.assertEqual(Decimal(str(ledger_after_audit.items[0].actual_qty)), Decimal("10.000000"))
        self.assertEqual(len(summary_after_audit.items), 1)
        self.assertEqual(Decimal(str(summary_after_audit.items[0].actual_qty)), Decimal("10.000000"))
        self.assertEqual(receipts_after_audit.total, 1)
        self.assertEqual(Decimal(str(receipts_after_audit.items[0].received_qty)), Decimal("10.000000"))

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
            session.add_all(
                [
                    LyWarehouseInventoryCount(
                        id=901,
                        company="COMP-A",
                        warehouse="WH-A",
                        status="counted",
                        count_no="INV-SUB-MAT-BAL-001",
                        count_date=date(2026, 6, 4),
                        created_by="warehouse.test",
                    ),
                    LyWarehouseInventoryCountItem(
                        id=901,
                        count_id=901,
                        company="COMP-A",
                        warehouse="WH-A",
                        item_code="FAB-A",
                        system_qty=Decimal("999"),
                        counted_qty=Decimal("6"),
                        variance_qty=Decimal("-993"),
                        review_status="pending",
                    ),
                    LyWarehouseInventoryCount(
                        id=902,
                        company="COMP-A",
                        warehouse="WH-FG",
                        status="counted",
                        count_no="INV-SUB-FG-BAL-001",
                        count_date=date(2026, 6, 4),
                        created_by="warehouse.test",
                    ),
                    LyWarehouseInventoryCountItem(
                        id=902,
                        count_id=902,
                        company="COMP-A",
                        warehouse="WH-FG",
                        item_code="STYLE-BAL",
                        system_qty=Decimal("0"),
                        counted_qty=Decimal("3"),
                        variance_qty=Decimal("3"),
                        review_status="pending",
                    ),
                ]
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
            reconciliation = service.list_local_inventory_balance_reconciliation(
                company="COMP-A",
                warehouse=None,
                item_code=None,
                status=None,
                page=1,
                page_size=20,
            )

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
        reconciliation_by_key = {(row.warehouse, row.item_code): row for row in reconciliation.items}
        self.assertEqual(Decimal(str(reconciliation_by_key[("WH-A", "FAB-A")].book_qty)), Decimal("6.000000"))
        self.assertEqual(Decimal(str(reconciliation_by_key[("WH-A", "FAB-A")].actual_qty)), Decimal("6.000000"))
        self.assertEqual(Decimal(str(reconciliation_by_key[("WH-A", "FAB-A")].diff_qty)), Decimal("0.000000"))
        self.assertEqual(reconciliation_by_key[("WH-A", "FAB-A")].status, "balanced")
        self.assertEqual(Decimal(str(reconciliation_by_key[("WH-FG", "STYLE-BAL")].book_qty)), Decimal("3.000000"))
        self.assertEqual(Decimal(str(reconciliation_by_key[("WH-FG", "STYLE-BAL")].actual_qty)), Decimal("3.000000"))
        self.assertEqual(reconciliation_by_key[("WH-FG", "STYLE-BAL")].status, "balanced")

    def test_factory_return_material_draft_returns_to_unified_stock_balance(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LySubcontractOrder(
                    id=902,
                    subcontract_no="SC-RET-001",
                    supplier="RET-FAC",
                    item_code="STYLE-RET",
                    company="COMP-A",
                    bom_id=1,
                    process_name="外发裁剪",
                    planned_qty=Decimal("10"),
                    issued_qty=Decimal("8"),
                    received_qty=Decimal("5"),
                    inspected_qty=Decimal("0"),
                    accepted_qty=Decimal("0"),
                    status="waiting_inspection",
                    settlement_status="unsettled",
                )
            )
            session.add(
                LySubcontractStockOutbox(
                    id=903,
                    subcontract_id=902,
                    event_key="ret-issue-outbox",
                    stock_action="issue",
                    idempotency_key="ret-issue-idem",
                    payload_hash="ret-issue-hash",
                    company="COMP-A",
                    supplier="RET-FAC",
                    item_code="STYLE-RET",
                    warehouse="WH-RET",
                    action="issue",
                    status="succeeded",
                    stock_entry_name="LOCAL-ISSUE-RET-001",
                    request_id="ret-issue-request",
                    created_by="warehouse.test",
                    created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
            )
            session.add(
                LySubcontractMaterial(
                    id=903,
                    subcontract_id=902,
                    stock_outbox_id=903,
                    company="COMP-A",
                    issue_batch_no="SIB-RET-001",
                    material_item_code="FAB-RET",
                    required_qty=Decimal("8"),
                    issued_qty=Decimal("8"),
                    sync_status="succeeded",
                    stock_entry_name="LOCAL-ISSUE-RET-001",
                    created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
                )
            )
            session.commit()

        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            report = service.list_local_factory_return_material_report(
                company="COMP-A",
                warehouse="WH-RET",
                item_code="FAB-RET",
                status=None,
            )
            self.assertEqual(len(report.items), 1)
            report_row = report.items[0]
            self.assertEqual(report_row.subcontract_no, "SC-RET-001")
            self.assertEqual(Decimal(str(report_row.issued_qty)), Decimal("8.00"))
            self.assertEqual(Decimal(str(report_row.theoretical_usage_qty)), Decimal("4.00"))
            self.assertEqual(Decimal(str(report_row.pending_qty)), Decimal("4.00"))

            payload = WarehouseFactoryReturnMaterialDraftRequest(
                company="COMP-A",
                scenario_tag="factory-return-material",
                source_ref=f"{report_row.report_no}:return:001",
                quantity=Decimal("2"),
                uom="米",
                business_date=date(2026, 6, 4),
                idempotency_key="idem-factory-return-ret-001",
            )
            created = service.create_factory_return_material_draft(
                report_no=report_row.report_no,
                payload=payload,
                current_user="warehouse.test",
            )
            replayed = service.create_factory_return_material_draft(
                report_no=report_row.report_no,
                payload=payload,
                current_user="warehouse.test",
            )
            session.commit()
            ledger = service.list_stock_ledger(
                company="COMP-A",
                warehouse="WH-RET",
                item_code="FAB-RET",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            summary = service.get_stock_summary(company="COMP-A", warehouse="WH-RET", item_code="FAB-RET")
            refreshed = service.list_local_factory_return_material_report(
                company="COMP-A",
                warehouse="WH-RET",
                item_code="FAB-RET",
                status=None,
            )

        self.assertEqual(created.draft.id, replayed.draft.id)
        self.assertEqual(created.draft.source_type, "factory_return_material")
        self.assertEqual(created.draft.purpose, "Material Receipt")
        self.assertEqual(Decimal(str(created.report_item.returned_qty)), Decimal("0.00"))
        self.assertEqual(Decimal(str(created.report_item.posted_returned_qty)), Decimal("0.00"))
        self.assertEqual(Decimal(str(created.report_item.pending_outbox_qty)), Decimal("2.00"))
        self.assertEqual(Decimal(str(created.report_item.pending_qty)), Decimal("2.00"))
        self.assertEqual(created.report_item.status, "confirmed")
        self.assertEqual(
            [(row.voucher_type, row.voucher_no, Decimal(str(row.actual_qty)), Decimal(str(row.qty_after_transaction))) for row in ledger.items],
            [
                ("Subcontract/Material Issue", "SIB-RET-001", Decimal("-8.000000"), Decimal("-8.000000")),
                ("Stock Entry Draft/Material Receipt", f"DRAFT-{created.draft.id}", Decimal("2.000000"), Decimal("-6.000000")),
            ],
        )
        self.assertEqual(
            [(row.company, row.warehouse, row.item_code, Decimal(str(row.actual_qty))) for row in summary.items],
            [("COMP-A", "WH-RET", "FAB-RET", Decimal("-6.000000"))],
        )
        self.assertEqual(Decimal(str(refreshed.items[0].returned_qty)), Decimal("0.00"))
        self.assertEqual(Decimal(str(refreshed.items[0].posted_returned_qty)), Decimal("0.00"))
        self.assertEqual(Decimal(str(refreshed.items[0].pending_outbox_qty)), Decimal("2.00"))
        self.assertEqual(Decimal(str(refreshed.items[0].pending_qty)), Decimal("2.00"))

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

    def test_quality_succeeded_outbox_enters_unified_stock_balance(self) -> None:
        with self.SessionLocal() as session:
            self._add_draft(
                session,
                source_id="RCPT-QC-BASE",
                purpose="Material Receipt",
                target_warehouse="WH-QC",
                qty="10",
                business_date=date(2026, 6, 1),
                item_code="FAB-QC",
            )
            session.add_all(
                [
                    LyQualityInspection(
                        id=701,
                        inspection_no="QI-BAL-001",
                        company="COMP-A",
                        source_type="incoming_material",
                        source_id="PR-QC-001",
                        item_code="FAB-QC",
                        supplier="SUP-QC",
                        warehouse="WH-QC",
                        inspection_date=date(2026, 6, 2),
                        inspected_qty=Decimal("10"),
                        accepted_qty=Decimal("8"),
                        rejected_qty=Decimal("2"),
                        defect_qty=Decimal("2"),
                        defect_rate=Decimal("0.2"),
                        rejected_rate=Decimal("0.2"),
                        result="partial",
                        status="confirmed",
                        created_by="quality.test",
                        updated_by="quality.test",
                        confirmed_by="quality.test",
                        confirmed_at=datetime(2026, 6, 2, 9, tzinfo=timezone.utc),
                    ),
                    LyQualityInspection(
                        id=702,
                        inspection_no="QI-BAL-PENDING",
                        company="COMP-A",
                        source_type="incoming_material",
                        source_id="PR-QC-002",
                        item_code="FAB-QC",
                        supplier="SUP-QC",
                        warehouse="WH-QC",
                        inspection_date=date(2026, 6, 2),
                        inspected_qty=Decimal("5"),
                        accepted_qty=Decimal("5"),
                        rejected_qty=Decimal("0"),
                        defect_qty=Decimal("0"),
                        defect_rate=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        result="pass",
                        status="confirmed",
                        created_by="quality.test",
                        updated_by="quality.test",
                        confirmed_by="quality.test",
                        confirmed_at=datetime(2026, 6, 2, 10, tzinfo=timezone.utc),
                    ),
                    LyQualityInspection(
                        id=703,
                        inspection_no="QI-BAL-NO-ENTRY",
                        company="COMP-A",
                        source_type="incoming_material",
                        source_id="PR-QC-003",
                        item_code="FAB-QC",
                        supplier="SUP-QC",
                        warehouse="WH-QC",
                        inspection_date=date(2026, 6, 2),
                        inspected_qty=Decimal("3"),
                        accepted_qty=Decimal("3"),
                        rejected_qty=Decimal("0"),
                        defect_qty=Decimal("0"),
                        defect_rate=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        result="pass",
                        status="confirmed",
                        created_by="quality.test",
                        updated_by="quality.test",
                        confirmed_by="quality.test",
                        confirmed_at=datetime(2026, 6, 2, 11, tzinfo=timezone.utc),
                    ),
                    LyQualityInspection(
                        id=704,
                        inspection_no="QI-BAL-OTHER-EVENT",
                        company="COMP-A",
                        source_type="incoming_material",
                        source_id="PR-QC-004",
                        item_code="FAB-QC",
                        supplier="SUP-QC",
                        warehouse="WH-QC",
                        inspection_date=date(2026, 6, 2),
                        inspected_qty=Decimal("4"),
                        accepted_qty=Decimal("4"),
                        rejected_qty=Decimal("0"),
                        defect_qty=Decimal("0"),
                        defect_rate=Decimal("0"),
                        rejected_rate=Decimal("0"),
                        result="pass",
                        status="confirmed",
                        created_by="quality.test",
                        updated_by="quality.test",
                        confirmed_by="quality.test",
                        confirmed_at=datetime(2026, 6, 2, 12, tzinfo=timezone.utc),
                    ),
                ]
            )
            session.add_all(
                [
                    LyQualityOutbox(
                        id=701,
                        inspection_id=701,
                        company="COMP-A",
                        event_type="quality_stock_entry_sync",
                        event_key="quality-balance-succeeded",
                        payload_json={
                            "inspection_id": 701,
                            "inspection_no": "QI-BAL-001",
                            "company": "COMP-A",
                            "source_type": "incoming_material",
                            "source_id": "PR-QC-001",
                            "item_code": "FAB-QC",
                            "supplier": "SUP-QC",
                            "warehouse": "WH-QC",
                            "accepted_qty": "8",
                            "rejected_qty": "2",
                            "accepted_warehouse": "WH-PASS",
                            "rejected_warehouse": "WH-REJECT",
                            "confirmed_at": "2026-06-02T09:00:00+00:00",
                        },
                        payload_hash="quality-balance-succeeded-hash",
                        status="succeeded",
                        stock_entry_name="STE-QUALITY-STOCK-001",
                        created_by="quality.test",
                        created_at=datetime(2026, 6, 2, 9, tzinfo=timezone.utc),
                        succeeded_at=datetime(2026, 6, 2, 9, 1, tzinfo=timezone.utc),
                    ),
                    LyQualityOutbox(
                        id=702,
                        inspection_id=702,
                        company="COMP-A",
                        event_type="quality_stock_entry_sync",
                        event_key="quality-balance-pending",
                        payload_json={
                            "inspection_id": 702,
                            "inspection_no": "QI-BAL-PENDING",
                            "company": "COMP-A",
                            "item_code": "FAB-QC",
                            "warehouse": "WH-QC",
                            "accepted_qty": "5",
                            "rejected_qty": "0",
                            "accepted_warehouse": "WH-PASS",
                            "confirmed_at": "2026-06-02T10:00:00+00:00",
                        },
                        payload_hash="quality-balance-pending-hash",
                        status="pending",
                        stock_entry_name=None,
                        created_by="quality.test",
                        created_at=datetime(2026, 6, 2, 10, tzinfo=timezone.utc),
                    ),
                    LyQualityOutbox(
                        id=703,
                        inspection_id=703,
                        company="COMP-A",
                        event_type="quality_stock_entry_sync",
                        event_key="quality-balance-no-entry",
                        payload_json={
                            "inspection_id": 703,
                            "inspection_no": "QI-BAL-NO-ENTRY",
                            "company": "COMP-A",
                            "item_code": "FAB-QC",
                            "warehouse": "WH-QC",
                            "accepted_qty": "3",
                            "rejected_qty": "0",
                            "accepted_warehouse": "WH-PASS",
                            "confirmed_at": "2026-06-02T11:00:00+00:00",
                        },
                        payload_hash="quality-balance-no-entry-hash",
                        status="succeeded",
                        stock_entry_name=None,
                        created_by="quality.test",
                        created_at=datetime(2026, 6, 2, 11, tzinfo=timezone.utc),
                    ),
                    LyQualityOutbox(
                        id=704,
                        inspection_id=704,
                        company="COMP-A",
                        event_type="quality_other_event",
                        event_key="quality-balance-other-event",
                        payload_json={
                            "inspection_id": 704,
                            "inspection_no": "QI-BAL-OTHER-EVENT",
                            "company": "COMP-A",
                            "item_code": "FAB-QC",
                            "warehouse": "WH-QC",
                            "accepted_qty": "4",
                            "rejected_qty": "0",
                            "accepted_warehouse": "WH-PASS",
                            "confirmed_at": "2026-06-02T12:00:00+00:00",
                        },
                        payload_hash="quality-balance-other-event-hash",
                        status="succeeded",
                        stock_entry_name="STE-QUALITY-OTHER-001",
                        created_by="quality.test",
                        created_at=datetime(2026, 6, 2, 12, tzinfo=timezone.utc),
                        succeeded_at=datetime(2026, 6, 2, 12, 1, tzinfo=timezone.utc),
                    ),
                ]
            )
            session.add_all(
                [
                    LyWarehouseInventoryCount(
                        id=701,
                        company="COMP-A",
                        warehouse="WH-PASS",
                        status="counted",
                        count_no="INV-QC-PASS-BAL-001",
                        count_date=date(2026, 6, 4),
                        created_by="quality.test",
                    ),
                    LyWarehouseInventoryCountItem(
                        id=701,
                        count_id=701,
                        company="COMP-A",
                        warehouse="WH-PASS",
                        item_code="FAB-QC",
                        system_qty=Decimal("0"),
                        counted_qty=Decimal("8"),
                        variance_qty=Decimal("8"),
                        review_status="pending",
                    ),
                ]
            )
            session.commit()

        with self.SessionLocal() as session:
            service = WarehouseService(session=session)
            ledger = service.list_stock_ledger(
                company="COMP-A",
                warehouse=None,
                item_code="FAB-QC",
                from_date=None,
                to_date=None,
                page=1,
                page_size=20,
            )
            summary = service.get_stock_summary(company="COMP-A", warehouse=None, item_code="FAB-QC")
            reconciliation = service.list_local_inventory_balance_reconciliation(
                company="COMP-A",
                warehouse="WH-PASS",
                item_code="FAB-QC",
                status=None,
                page=1,
                page_size=20,
            )

        self.assertEqual(
            [
                (row.warehouse, row.voucher_type, row.voucher_no, Decimal(str(row.actual_qty)), Decimal(str(row.qty_after_transaction)))
                for row in ledger.items
            ],
            [
                ("WH-QC", "Stock Entry Draft/Material Receipt", "DRAFT-1", Decimal("10.000000"), Decimal("10.000000")),
                ("WH-QC", "Quality/Material Transfer", "STE-QUALITY-STOCK-001", Decimal("-8.000000"), Decimal("2.000000")),
                ("WH-PASS", "Quality/Material Transfer", "STE-QUALITY-STOCK-001", Decimal("8.000000"), Decimal("8.000000")),
                ("WH-QC", "Quality/Material Transfer", "STE-QUALITY-STOCK-001", Decimal("-2.000000"), Decimal("0.000000")),
                ("WH-REJECT", "Quality/Material Transfer", "STE-QUALITY-STOCK-001", Decimal("2.000000"), Decimal("2.000000")),
            ],
        )
        summary_by_warehouse = {row.warehouse: Decimal(str(row.actual_qty)) for row in summary.items}
        self.assertEqual(
            summary_by_warehouse,
            {
                "WH-PASS": Decimal("8.000000"),
                "WH-QC": Decimal("0.000000"),
                "WH-REJECT": Decimal("2.000000"),
            },
        )
        self.assertEqual(reconciliation.total, 1)
        self.assertEqual(Decimal(str(reconciliation.items[0].book_qty)), Decimal("8.000000"))
        self.assertEqual(Decimal(str(reconciliation.items[0].actual_qty)), Decimal("8.000000"))
        self.assertEqual(Decimal(str(reconciliation.items[0].diff_qty)), Decimal("0.000000"))
        self.assertEqual(reconciliation.items[0].status, "balanced")


if __name__ == "__main__":
    unittest.main()
