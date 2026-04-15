"""Model and migration-structure tests for factory statement tables (TASK-006B)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import pathlib
import unittest

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.factory_statement import Base as FactoryStatementBase
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementItem
from app.models.factory_statement import LyFactoryStatementLog
from app.models.factory_statement import LyFactoryStatementOperation
from app.models.factory_statement import LyFactoryStatementPayableOutbox


class FactoryStatementModelTest(unittest.TestCase):
    """Validate table fields and key constraints for TASK-006B."""

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
        FactoryStatementBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.SessionLocal() as session:
            session.query(LyFactoryStatementPayableOutbox).delete()
            session.query(LyFactoryStatementOperation).delete()
            session.query(LyFactoryStatementLog).delete()
            session.query(LyFactoryStatementItem).delete()
            session.query(LyFactoryStatement).delete()
            session.commit()

    @staticmethod
    def _build_statement(*, statement_no: str, idempotency_key: str) -> LyFactoryStatement:
        return LyFactoryStatement(
            statement_no=statement_no,
            company="COMP-A",
            supplier="SUP-A",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            source_type="subcontract_inspection",
            source_count=1,
            inspected_qty=Decimal("10"),
            rejected_qty=Decimal("0"),
            accepted_qty=Decimal("10"),
            gross_amount=Decimal("100"),
            deduction_amount=Decimal("5"),
            net_amount=Decimal("95"),
            rejected_rate=Decimal("0"),
            statement_status="draft",
            idempotency_key=idempotency_key,
            request_hash=f"hash-{statement_no}",
            created_by="tester",
        )

    @staticmethod
    def _build_outbox(
        *,
        statement_id: int,
        idem_key: str,
        event_key: str,
        status: str,
    ) -> LyFactoryStatementPayableOutbox:
        return LyFactoryStatementPayableOutbox(
            company="COMP-A",
            statement_id=statement_id,
            statement_no="FS-OUTBOX-001",
            supplier="SUP-A",
            idempotency_key=idem_key,
            request_hash=f"hash-{idem_key}",
            event_key=event_key,
            payload_json={"amount": "95"},
            payload_hash=f"payload-{idem_key}",
            status=status,
            attempts=0,
            max_attempts=5,
            created_by="tester",
        )

    def test_three_tables_and_core_columns_exist(self) -> None:
        inspector = inspect(self.engine)
        self.assertIn("ly_factory_statement", inspector.get_table_names())
        self.assertIn("ly_factory_statement_item", inspector.get_table_names())
        self.assertIn("ly_factory_statement_log", inspector.get_table_names())
        self.assertIn("ly_factory_statement_operation", inspector.get_table_names())
        self.assertIn("ly_factory_statement_payable_outbox", inspector.get_table_names())

        statement_columns = {col["name"] for col in inspector.get_columns("ly_factory_statement")}
        self.assertTrue(
            {
                "statement_no",
                "company",
                "supplier",
                "from_date",
                "to_date",
                "source_type",
                "source_count",
                "gross_amount",
                "deduction_amount",
                "net_amount",
                "rejected_rate",
                "statement_status",
                "idempotency_key",
                "request_hash",
            }.issubset(statement_columns)
        )

        item_columns = {col["name"] for col in inspector.get_columns("ly_factory_statement_item")}
        self.assertTrue(
            {
                "statement_id",
                "inspection_id",
                "subcontract_id",
                "subcontract_no",
                "gross_amount",
                "deduction_amount",
                "net_amount",
            }.issubset(item_columns)
        )

        log_columns = {col["name"] for col in inspector.get_columns("ly_factory_statement_log")}
        self.assertTrue({"statement_id", "from_status", "to_status", "action", "operator"}.issubset(log_columns))

        operation_columns = {col["name"] for col in inspector.get_columns("ly_factory_statement_operation")}
        self.assertTrue(
            {
                "company",
                "statement_id",
                "operation_type",
                "idempotency_key",
                "request_hash",
                "result_status",
                "result_user",
                "result_at",
            }.issubset(operation_columns)
        )

        outbox_columns = {col["name"] for col in inspector.get_columns("ly_factory_statement_payable_outbox")}
        self.assertTrue(
            {
                "company",
                "statement_id",
                "statement_no",
                "supplier",
                "idempotency_key",
                "request_hash",
                "event_key",
                "payload_json",
                "payload_hash",
                "status",
                "attempts",
                "max_attempts",
                "next_retry_at",
                "erpnext_purchase_invoice",
                "erpnext_docstatus",
                "last_error_code",
                "last_error_message",
            }.issubset(outbox_columns)
        )

    def test_company_idempotency_unique_constraint(self) -> None:
        with self.SessionLocal() as session:
            session.add(self._build_statement(statement_no="FS-001", idempotency_key="idem-1"))
            session.commit()

            session.add(self._build_statement(statement_no="FS-002", idempotency_key="idem-1"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_active_scope_unique_constraint_for_non_cancelled_statement(self) -> None:
        with self.SessionLocal() as session:
            first = self._build_statement(statement_no="FS-100", idempotency_key="idem-active-1")
            first.request_hash = "same-active-scope-hash"
            session.add(first)
            session.commit()

            second = self._build_statement(statement_no="FS-101", idempotency_key="idem-active-2")
            second.request_hash = "same-active-scope-hash"
            session.add(second)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_unconditional_inspection_id_unique_constraint_removed(self) -> None:
        inspector = inspect(self.engine)
        indexes = inspector.get_indexes("ly_factory_statement_item")

        unique_inspection_indexes = [
            index
            for index in indexes
            if bool(index.get("unique")) and list(index.get("column_names") or []) == ["inspection_id"]
        ]
        self.assertEqual(unique_inspection_indexes, [])

    def test_statement_item_allows_rebuild_after_cancel_contract(self) -> None:
        with self.SessionLocal() as session:
            statement_1 = self._build_statement(statement_no="FS-010", idempotency_key="idem-10")
            statement_1.statement_status = "cancelled"
            statement_2 = self._build_statement(statement_no="FS-011", idempotency_key="idem-11")
            session.add(statement_1)
            session.add(statement_2)
            session.flush()

            session.add(
                LyFactoryStatementItem(
                    statement_id=int(statement_1.id),
                    line_no=1,
                    inspection_id=9001,
                    inspection_no="SIN-9001",
                    subcontract_id=5001,
                    subcontract_no="SC-5001",
                    company="COMP-A",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("10"),
                    rejected_qty=Decimal("0"),
                    accepted_qty=Decimal("10"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("100"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("100"),
                    rejected_rate=Decimal("0"),
                )
            )
            session.commit()

            session.add(
                LyFactoryStatementItem(
                    statement_id=int(statement_2.id),
                    line_no=1,
                    inspection_id=9001,
                    inspection_no="SIN-9001",
                    subcontract_id=5001,
                    subcontract_no="SC-5001",
                    company="COMP-A",
                    supplier="SUP-A",
                    item_code="ITEM-A",
                    inspected_qty=Decimal("10"),
                    rejected_qty=Decimal("0"),
                    accepted_qty=Decimal("10"),
                    subcontract_rate=Decimal("10"),
                    gross_amount=Decimal("100"),
                    deduction_amount=Decimal("0"),
                    net_amount=Decimal("100"),
                    rejected_rate=Decimal("0"),
                )
            )
            session.commit()

            rows = (
                session.query(LyFactoryStatementItem)
                .filter(LyFactoryStatementItem.inspection_id == 9001)
                .order_by(LyFactoryStatementItem.statement_id.asc())
                .all()
            )
            self.assertEqual(len(rows), 2)

    def test_operation_idempotency_unique_constraint(self) -> None:
        with self.SessionLocal() as session:
            statement = self._build_statement(statement_no="FS-OP-001", idempotency_key="idem-op-1")
            session.add(statement)
            session.flush()

            operation = LyFactoryStatementOperation(
                company="COMP-A",
                statement_id=int(statement.id),
                operation_type="confirm",
                idempotency_key="same-op-key",
                request_hash="hash-op-a",
                result_status="confirmed",
                result_user="tester",
                result_at=datetime.utcnow(),
                remark="ok",
            )
            session.add(operation)
            session.commit()

            duplicate = LyFactoryStatementOperation(
                company="COMP-A",
                statement_id=int(statement.id),
                operation_type="confirm",
                idempotency_key="same-op-key",
                request_hash="hash-op-b",
                result_status="confirmed",
                result_user="tester",
                result_at=datetime.utcnow(),
                remark="dup",
            )
            session.add(duplicate)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_payable_outbox_one_active_unique_constraint(self) -> None:
        with self.SessionLocal() as session:
            statement = self._build_statement(statement_no="FS-PO-001", idempotency_key="idem-po-1")
            statement.statement_status = "confirmed"
            session.add(statement)
            session.flush()

            first = self._build_outbox(
                statement_id=int(statement.id),
                idem_key="pay-1",
                event_key="fspi:event-1",
                status="pending",
            )
            session.add(first)
            session.commit()

            second = self._build_outbox(
                statement_id=int(statement.id),
                idem_key="pay-2",
                event_key="fspi:event-2",
                status="processing",
            )
            session.add(second)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_payable_outbox_failed_status_allows_new_pending_row(self) -> None:
        with self.SessionLocal() as session:
            statement = self._build_statement(statement_no="FS-PO-002", idempotency_key="idem-po-2")
            statement.statement_status = "confirmed"
            session.add(statement)
            session.flush()

            failed = self._build_outbox(
                statement_id=int(statement.id),
                idem_key="pay-failed",
                event_key="fspi:event-failed",
                status="failed",
            )
            session.add(failed)
            session.commit()

            pending = self._build_outbox(
                statement_id=int(statement.id),
                idem_key="pay-pending",
                event_key="fspi:event-pending",
                status="pending",
            )
            session.add(pending)
            session.commit()

    def test_migration_file_contains_tables_and_indexes(self) -> None:
        migration_path = pathlib.Path(__file__).resolve().parents[1] / "migrations" / "versions" / "task_006b_create_factory_statement_tables.py"
        content = migration_path.read_text(encoding="utf-8")
        self.assertIn("ly_factory_statement", content)
        self.assertIn("ly_factory_statement_item", content)
        self.assertIn("ly_factory_statement_log", content)
        self.assertIn("uk_ly_factory_statement_company_idempotency", content)
        self.assertIn("uk_ly_factory_statement_active_scope", content)
        self.assertNotIn("uk_ly_factory_statement_item_inspection", content)

        b1_migration = (
            pathlib.Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "task_006b1_factory_statement_active_scope_constraints.py"
        )
        b1_content = b1_migration.read_text(encoding="utf-8")
        self.assertIn("uk_ly_factory_statement_active_scope", b1_content)
        self.assertNotIn("uk_ly_factory_statement_item_inspection", b1_content)

        c_migration = (
            pathlib.Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "task_006c_factory_statement_operation_table.py"
        )
        c_content = c_migration.read_text(encoding="utf-8")
        self.assertIn("ly_factory_statement_operation", c_content)
        self.assertIn("uk_ly_factory_statement_operation_idempotency", c_content)

        d_migration = (
            pathlib.Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "task_006d_factory_statement_payable_outbox.py"
        )
        d_content = d_migration.read_text(encoding="utf-8")
        self.assertIn("ly_factory_statement_payable_outbox", d_content)
        self.assertIn("uk_ly_factory_statement_payable_event_key", d_content)
        self.assertIn("uk_ly_factory_statement_payable_idem", d_content)

        e2_migration = (
            pathlib.Path(__file__).resolve().parents[1]
            / "migrations"
            / "versions"
            / "task_006e2_factory_statement_payable_active_scope.py"
        )
        e2_content = e2_migration.read_text(encoding="utf-8")
        self.assertIn("uk_ly_factory_statement_payable_one_active", e2_content)
        self.assertIn("status IN ('pending','processing','succeeded')", e2_content)


if __name__ == "__main__":
    unittest.main()
