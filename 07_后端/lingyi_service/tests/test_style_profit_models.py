"""Model and constraint tests for style profit tables (TASK-005C1)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.style_profit import Base as StyleProfitBase
from app.models.style_profit import LyCostAllocationRule
from app.models.style_profit import LyStyleProfitDetail
from app.models.style_profit import LyStyleProfitSnapshot
from app.models.style_profit import LyStyleProfitSourceMap


class StyleProfitModelTest(unittest.TestCase):
    """Validate style profit table structure and uniqueness constraints."""

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
        StyleProfitBase.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.SessionLocal() as session:
            session.query(LyStyleProfitSourceMap).delete()
            session.query(LyStyleProfitDetail).delete()
            session.query(LyCostAllocationRule).delete()
            session.query(LyStyleProfitSnapshot).delete()
            session.commit()

    def _build_snapshot(
        self,
        *,
        snapshot_no: str,
        company: str = "COMP-A",
        idempotency_key: str = "idem-style-profit-001",
    ) -> LyStyleProfitSnapshot:
        return LyStyleProfitSnapshot(
            snapshot_no=snapshot_no,
            company=company,
            sales_order="SO-STYLE-001",
            item_code="STYLE-A",
            revenue_status="estimated",
            estimated_revenue_amount=Decimal("100"),
            actual_revenue_amount=Decimal("0"),
            revenue_amount=Decimal("100"),
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 30),
            revenue_mode="actual_first",
            standard_material_cost=Decimal("30"),
            standard_operation_cost=Decimal("10"),
            standard_total_cost=Decimal("40"),
            actual_material_cost=Decimal("22"),
            actual_workshop_cost=Decimal("8"),
            actual_subcontract_cost=Decimal("5"),
            allocated_overhead_amount=Decimal("0"),
            actual_total_cost=Decimal("35"),
            profit_amount=Decimal("65"),
            profit_rate=Decimal("0.65"),
            snapshot_status="complete",
            allocation_status="not_enabled",
            formula_version="STYLE_PROFIT_V1",
            include_provisional_subcontract=False,
            unresolved_count=0,
            idempotency_key=idempotency_key,
            request_hash="h-style-profit-001",
            created_by="tester",
        )

    def _build_detail(self, *, snapshot_id: int, line_no: int = 1) -> LyStyleProfitDetail:
        return LyStyleProfitDetail(
            snapshot_id=snapshot_id,
            line_no=line_no,
            cost_type="actual_material",
            source_type="Stock Ledger Entry",
            source_name="STE-001",
            item_code="MAT-A",
            qty=Decimal("5"),
            unit_rate=Decimal("10"),
            amount=Decimal("50"),
            formula_code="MAT_V1",
            is_unresolved=False,
            raw_ref={"voucher_no": "STE-001"},
        )

    def _build_source_map(
        self,
        *,
        snapshot_id: int,
        detail_id: int | None = None,
        source_name: str = "STE-001",
        source_line_no: str = "SLE-ROW-1",
        source_system: str = "erpnext",
        source_doctype: str = "Stock Ledger Entry",
        source_status: str = "submitted",
        mapping_status: str = "mapped",
        include_in_profit: bool = True,
    ) -> LyStyleProfitSourceMap:
        return LyStyleProfitSourceMap(
            snapshot_id=snapshot_id,
            detail_id=detail_id,
            company="COMP-A",
            sales_order="SO-STYLE-001",
            style_item_code="STYLE-A",
            source_item_code="MAT-A",
            source_system=source_system,
            source_doctype=source_doctype,
            source_status=source_status,
            source_name=source_name,
            source_line_no=source_line_no,
            qty=Decimal("5"),
            unit_rate=Decimal("10"),
            amount=Decimal("50"),
            currency="CNY",
            warehouse="WIP-A",
            posting_date=date(2026, 4, 13),
            raw_ref={"voucher_no": "STE-001"},
            include_in_profit=include_in_profit,
            mapping_status=mapping_status,
        )

    def test_snapshot_model_fields_exist(self) -> None:
        inspector = inspect(self.engine)
        columns = {col["name"] for col in inspector.get_columns("ly_style_profit_snapshot")}
        expected = {
            "snapshot_no",
            "company",
            "sales_order",
            "item_code",
            "from_date",
            "to_date",
            "revenue_mode",
            "revenue_status",
            "estimated_revenue_amount",
            "actual_revenue_amount",
            "revenue_amount",
            "standard_material_cost",
            "standard_operation_cost",
            "standard_total_cost",
            "actual_material_cost",
            "actual_workshop_cost",
            "actual_subcontract_cost",
            "allocated_overhead_amount",
            "actual_total_cost",
            "profit_amount",
            "profit_rate",
            "snapshot_status",
            "allocation_status",
            "formula_version",
            "include_provisional_subcontract",
            "unresolved_count",
            "idempotency_key",
            "request_hash",
            "created_by",
            "created_at",
        }
        self.assertTrue(expected.issubset(columns))

    def test_snapshot_period_index_exists_and_order_is_correct(self) -> None:
        index = next(
            (
                idx
                for idx in LyStyleProfitSnapshot.__table__.indexes
                if idx.name == "idx_ly_style_profit_snapshot_company_item_period"
            ),
            None,
        )
        self.assertIsNotNone(index)
        self.assertEqual(
            [column.name for column in index.columns],
            ["company", "item_code", "from_date", "to_date"],
        )

    def test_snapshot_no_unique_constraint(self) -> None:
        with self.SessionLocal() as session:
            session.add(self._build_snapshot(snapshot_no="SP-20260414-0001", idempotency_key="idem-unique-1"))
            session.commit()
            session.add(self._build_snapshot(snapshot_no="SP-20260414-0001", idempotency_key="idem-unique-2"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_snapshot_company_idempotency_unique_constraint(self) -> None:
        with self.SessionLocal() as session:
            session.add(self._build_snapshot(snapshot_no="SP-20260414-0002", idempotency_key="idem-company-1"))
            session.commit()
            session.add(self._build_snapshot(snapshot_no="SP-20260414-0003", idempotency_key="idem-company-1"))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_detail_can_associate_snapshot(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0004", idempotency_key="idem-detail")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id))
            session.add(detail)
            session.commit()

            row = session.query(LyStyleProfitDetail).filter(LyStyleProfitDetail.snapshot_id == int(snapshot.id)).first()
            self.assertIsNotNone(row)
            self.assertEqual(int(row.snapshot_id), int(snapshot.id))

    def test_source_map_contains_required_audit_fields(self) -> None:
        inspector = inspect(self.engine)
        columns = {col["name"] for col in inspector.get_columns("ly_style_profit_source_map")}
        expected = {
            "snapshot_id",
            "detail_id",
            "source_system",
            "source_doctype",
            "source_status",
            "source_name",
            "source_line_no",
            "style_item_code",
            "source_item_code",
            "qty",
            "unit_rate",
            "amount",
            "currency",
            "warehouse",
            "posting_date",
            "raw_ref",
            "mapping_status",
            "include_in_profit",
            "unresolved_reason",
        }
        self.assertTrue(expected.issubset(columns))

    def test_source_map_unique_constraint_is_snapshot_scoped(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0005", idempotency_key="idem-srcmap-1")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id))
            session.add(detail)
            session.flush()
            session.add(
                self._build_source_map(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                )
            )
            session.commit()

            session.add(
                self._build_source_map(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_same_source_row_allowed_in_different_snapshots(self) -> None:
        with self.SessionLocal() as session:
            snapshot_1 = self._build_snapshot(snapshot_no="SP-20260414-0006", idempotency_key="idem-srcmap-a")
            snapshot_2 = self._build_snapshot(snapshot_no="SP-20260414-0007", idempotency_key="idem-srcmap-b")
            session.add(snapshot_1)
            session.add(snapshot_2)
            session.flush()
            detail_1 = self._build_detail(snapshot_id=int(snapshot_1.id), line_no=1)
            detail_2 = self._build_detail(snapshot_id=int(snapshot_2.id), line_no=1)
            session.add(detail_1)
            session.add(detail_2)
            session.flush()

            session.add(
                self._build_source_map(snapshot_id=int(snapshot_1.id), detail_id=int(detail_1.id))
            )
            session.add(
                self._build_source_map(snapshot_id=int(snapshot_2.id), detail_id=int(detail_2.id))
            )
            session.commit()

            count = (
                session.query(LyStyleProfitSourceMap)
                .filter(
                    LyStyleProfitSourceMap.source_name == "STE-001",
                    LyStyleProfitSourceMap.source_line_no == "SLE-ROW-1",
                )
                .count()
            )
            self.assertEqual(count, 2)

    def test_source_map_default_include_in_profit_is_false(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0008", idempotency_key="idem-default-include")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id), line_no=2)
            session.add(detail)
            session.flush()

            row = LyStyleProfitSourceMap(
                snapshot_id=int(snapshot.id),
                detail_id=int(detail.id),
                company="COMP-A",
                sales_order="SO-STYLE-001",
                style_item_code="STYLE-A",
                source_item_code="MAT-A",
                source_system="erpnext",
                source_doctype="Stock Ledger Entry",
                source_status="submitted",
                source_name="STE-001",
                source_line_no="SLE-ROW-1",
                qty=Decimal("5"),
                unit_rate=Decimal("10"),
                amount=Decimal("50"),
                currency="CNY",
                warehouse="WIP-A",
                posting_date=date(2026, 4, 13),
                raw_ref={"voucher_no": "STE-001"},
            )
            session.add(row)
            session.commit()

            refreshed = session.query(LyStyleProfitSourceMap).filter(LyStyleProfitSourceMap.id == row.id).first()
            self.assertIsNotNone(refreshed)
            self.assertFalse(bool(refreshed.include_in_profit))
            self.assertEqual(str(refreshed.mapping_status), "unresolved")

    def test_source_map_source_status_default_unknown(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0009", idempotency_key="idem-status-default")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id), line_no=2)
            session.add(detail)
            session.flush()
            row = LyStyleProfitSourceMap(
                snapshot_id=int(snapshot.id),
                detail_id=int(detail.id),
                company="COMP-A",
                sales_order="SO-STYLE-001",
                style_item_code="STYLE-A",
                source_item_code="MAT-A",
                source_system="erpnext",
                source_doctype="Stock Ledger Entry",
                source_name="STE-001",
                source_line_no="SLE-ROW-1",
                qty=Decimal("5"),
                unit_rate=Decimal("10"),
                amount=Decimal("50"),
                currency="CNY",
                warehouse="WIP-A",
                posting_date=date(2026, 4, 13),
                raw_ref={"voucher_no": "STE-001"},
            )
            session.add(row)
            session.commit()
            refreshed = session.query(LyStyleProfitSourceMap).filter(LyStyleProfitSourceMap.id == row.id).first()
            self.assertIsNotNone(refreshed)
            self.assertEqual(str(refreshed.source_status), "unknown")

    def test_source_map_status_non_empty_constraint(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0010", idempotency_key="idem-status-empty")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id), line_no=2)
            session.add(detail)
            session.flush()
            session.add(
                self._build_source_map(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    source_status="",
                    mapping_status="unresolved",
                    include_in_profit=False,
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_source_map_source_system_enum_constraint(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0011", idempotency_key="idem-source-system")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id), line_no=2)
            session.add(detail)
            session.flush()
            session.add(
                self._build_source_map(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    source_system="legacy",
                    mapping_status="unresolved",
                    include_in_profit=False,
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_source_map_source_system_non_null_constraint(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0011A", idempotency_key="idem-source-system-null")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id), line_no=2)
            session.add(detail)
            session.flush()
            row = self._build_source_map(
                snapshot_id=int(snapshot.id),
                detail_id=int(detail.id),
                source_system="erpnext",
                mapping_status="unresolved",
                include_in_profit=False,
            )
            row.source_system = None  # type: ignore[assignment]
            session.add(row)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_source_map_source_doctype_non_null_constraint(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0011B", idempotency_key="idem-source-doctype-null")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id), line_no=2)
            session.add(detail)
            session.flush()
            row = self._build_source_map(
                snapshot_id=int(snapshot.id),
                detail_id=int(detail.id),
                mapping_status="unresolved",
                include_in_profit=False,
            )
            row.source_doctype = None  # type: ignore[assignment]
            session.add(row)
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_source_map_include_requires_mapped_constraint(self) -> None:
        with self.SessionLocal() as session:
            snapshot = self._build_snapshot(snapshot_no="SP-20260414-0012", idempotency_key="idem-map-constraint")
            session.add(snapshot)
            session.flush()
            detail = self._build_detail(snapshot_id=int(snapshot.id), line_no=2)
            session.add(detail)
            session.flush()
            session.add(
                self._build_source_map(
                    snapshot_id=int(snapshot.id),
                    detail_id=int(detail.id),
                    mapping_status="excluded",
                    include_in_profit=True,
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_source_map_required_indexes_exist(self) -> None:
        inspector = inspect(self.engine)
        names = {index["name"] for index in inspector.get_indexes("ly_style_profit_source_map")}
        expected = {
            "idx_ly_style_profit_source_map_snapshot_status",
            "idx_ly_style_profit_source_map_scope",
            "idx_ly_style_profit_source_map_source_lookup",
            "idx_ly_style_profit_source_map_detail",
            "uk_ly_style_profit_source_map_snapshot_source",
        }
        self.assertTrue(expected.issubset(names))

    def test_cost_allocation_rule_default_status_disabled(self) -> None:
        with self.SessionLocal() as session:
            rule = LyCostAllocationRule(
                company="COMP-A",
                rule_name="RULE-DISABLED-BY-DEFAULT",
                cost_type="manufacturing_overhead",
                allocation_basis="manual",
                created_by="tester",
            )
            session.add(rule)
            session.commit()
            refreshed = session.query(LyCostAllocationRule).filter(LyCostAllocationRule.id == rule.id).first()
            self.assertIsNotNone(refreshed)
            self.assertEqual(str(refreshed.status), "disabled")


if __name__ == "__main__":
    unittest.main()
