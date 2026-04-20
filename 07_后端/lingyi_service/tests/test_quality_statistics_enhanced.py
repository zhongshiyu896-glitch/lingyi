"""Enhanced quality statistics tests for TASK-030E."""

from __future__ import annotations

from datetime import date
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
from app.models.audit import LyOperationAuditLog
from app.models.audit import LySecurityAuditLog
from app.models.quality import Base as QualityBase
from app.models.quality import LyQualityDefect
from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityInspectionItem
from app.models.quality import LyQualityOperationLog
from app.routers.auth import get_db_session as auth_db_dep
from app.routers.quality import get_db_session as quality_db_dep


class QualityStatisticsEnhancedTest(unittest.TestCase):
    """Validate enhanced statistics aggregation behavior."""

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
        AuditBase.metadata.create_all(bind=cls.engine)

        def _override_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[auth_db_dep] = _override_db
        app.dependency_overrides[quality_db_dep] = _override_db
        cls._old_main_session_local = main_module.SessionLocal
        main_module.SessionLocal = cls.SessionLocal
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        main_module.SessionLocal = cls._old_main_session_local
        app.dependency_overrides.pop(auth_db_dep, None)
        app.dependency_overrides.pop(quality_db_dep, None)
        cls.engine.dispose()

    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["LINGYI_ALLOW_DEV_AUTH"] = "true"
        os.environ["LINGYI_PERMISSION_SOURCE"] = "static"
        with self.SessionLocal() as session:
            session.query(LyOperationAuditLog).delete()
            session.query(LySecurityAuditLog).delete()
            session.query(LyQualityOperationLog).delete()
            session.query(LyQualityDefect).delete()
            session.query(LyQualityInspectionItem).delete()
            session.query(LyQualityInspection).delete()
            session.commit()

    @staticmethod
    def _headers() -> dict[str, str]:
        return {"X-LY-Dev-User": "quality.user", "X-LY-Dev-Roles": "Quality Manager"}

    def _seed_inspection(
        self,
        *,
        inspection_no: str,
        company: str,
        supplier: str,
        item_code: str,
        warehouse: str,
        source_type: str,
        status: str,
        inspection_date: date,
        inspected_qty: Decimal,
        accepted_qty: Decimal,
        rejected_qty: Decimal,
        defect_qty: Decimal,
    ) -> None:
        with self.SessionLocal() as session:
            inspection = LyQualityInspection(
                inspection_no=inspection_no,
                company=company,
                source_type=source_type,
                source_id=None,
                item_code=item_code,
                supplier=supplier,
                warehouse=warehouse,
                inspection_date=inspection_date,
                inspected_qty=inspected_qty,
                accepted_qty=accepted_qty,
                rejected_qty=rejected_qty,
                defect_qty=defect_qty,
                defect_rate=Decimal("0") if inspected_qty == Decimal("0") else (defect_qty / inspected_qty).quantize(Decimal("0.000001")),
                rejected_rate=Decimal("0") if inspected_qty == Decimal("0") else (rejected_qty / inspected_qty).quantize(Decimal("0.000001")),
                result="partial" if rejected_qty > Decimal("0") else "pass",
                status=status,
                created_by="quality.user",
                updated_by="quality.user",
            )
            session.add(inspection)
            session.flush()
            session.add(
                LyQualityInspectionItem(
                    inspection_id=int(inspection.id),
                    line_no=1,
                    item_code=item_code,
                    sample_qty=inspected_qty,
                    accepted_qty=accepted_qty,
                    rejected_qty=rejected_qty,
                    defect_qty=defect_qty,
                    result="partial" if rejected_qty > Decimal("0") else "pass",
                )
            )
            session.add(
                LyQualityOperationLog(
                    inspection_id=int(inspection.id),
                    company=company,
                    from_status=None,
                    to_status=status,
                    action="create",
                    operator="quality.user",
                    request_id="req-seed",
                )
            )
            session.commit()

    def test_statistics_returns_enhanced_dimensions_and_topn(self) -> None:
        self._seed_inspection(
            inspection_no="QI-STAT-001",
            company="COMP-A",
            supplier="SUP-A",
            item_code="ITEM-A",
            warehouse="WH-A",
            source_type="manual",
            status="confirmed",
            inspection_date=date(2026, 4, 1),
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("8"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("2"),
        )
        self._seed_inspection(
            inspection_no="QI-STAT-002",
            company="COMP-A",
            supplier="SUP-A",
            item_code="ITEM-B",
            warehouse="WH-A",
            source_type="incoming_material",
            status="confirmed",
            inspection_date=date(2026, 4, 8),
            inspected_qty=Decimal("20"),
            accepted_qty=Decimal("18"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("3"),
        )
        self._seed_inspection(
            inspection_no="QI-STAT-003",
            company="COMP-A",
            supplier="SUP-B",
            item_code="ITEM-B",
            warehouse="WH-B",
            source_type="manual",
            status="confirmed",
            inspection_date=date(2026, 4, 16),
            inspected_qty=Decimal("8"),
            accepted_qty=Decimal("7"),
            rejected_qty=Decimal("1"),
            defect_qty=Decimal("1"),
        )
        # cancelled 记录必须继续排除在统计之外
        self._seed_inspection(
            inspection_no="QI-STAT-004",
            company="COMP-A",
            supplier="SUP-X",
            item_code="ITEM-X",
            warehouse="WH-X",
            source_type="manual",
            status="cancelled",
            inspection_date=date(2026, 4, 20),
            inspected_qty=Decimal("99"),
            accepted_qty=Decimal("0"),
            rejected_qty=Decimal("99"),
            defect_qty=Decimal("99"),
        )

        response = self.client.get("/api/quality/statistics?company=COMP-A", headers=self._headers())
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]

        self.assertEqual(data["total_count"], 3)
        self.assertEqual(Decimal(str(data["total_inspected_qty"])), Decimal("38"))
        self.assertEqual(Decimal(str(data["total_rejected_qty"])), Decimal("5"))

        supplier_labels = [row["label"] for row in data["by_supplier"]]
        self.assertIn("SUP-A", supplier_labels)
        self.assertIn("SUP-B", supplier_labels)
        self.assertNotIn("SUP-X", supplier_labels)
        supplier_row = next(row for row in data["by_supplier"] if row["label"] == "SUP-A")
        self.assertEqual(supplier_row["count"], 2)
        self.assertIn("defect_rate", supplier_row)

        source_keys = [row["key"] for row in data["by_source_type"]]
        self.assertIn("manual", source_keys)
        self.assertIn("incoming_material", source_keys)

        self.assertGreaterEqual(len(data["top_defective_suppliers"]), 1)
        self.assertEqual(data["top_defective_suppliers"][0]["label"], "SUP-A")

    def test_statistics_company_filter_keeps_scope(self) -> None:
        self._seed_inspection(
            inspection_no="QI-SCOPE-A",
            company="COMP-A",
            supplier="SUP-A",
            item_code="ITEM-A",
            warehouse="WH-A",
            source_type="manual",
            status="confirmed",
            inspection_date=date(2026, 4, 3),
            inspected_qty=Decimal("5"),
            accepted_qty=Decimal("4"),
            rejected_qty=Decimal("1"),
            defect_qty=Decimal("1"),
        )
        self._seed_inspection(
            inspection_no="QI-SCOPE-B",
            company="COMP-B",
            supplier="SUP-B",
            item_code="ITEM-B",
            warehouse="WH-B",
            source_type="manual",
            status="confirmed",
            inspection_date=date(2026, 4, 3),
            inspected_qty=Decimal("40"),
            accepted_qty=Decimal("20"),
            rejected_qty=Decimal("20"),
            defect_qty=Decimal("20"),
        )

        response = self.client.get("/api/quality/statistics?company=COMP-A", headers=self._headers())
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]

        self.assertEqual(data["total_count"], 1)
        self.assertEqual(Decimal(str(data["total_inspected_qty"])), Decimal("5"))
        self.assertEqual(len(data["by_supplier"]), 1)
        self.assertEqual(data["by_supplier"][0]["label"], "SUP-A")

    def test_statistics_trend_supports_monthly_and_weekly(self) -> None:
        self._seed_inspection(
            inspection_no="QI-TREND-001",
            company="COMP-A",
            supplier="SUP-A",
            item_code="ITEM-A",
            warehouse="WH-A",
            source_type="manual",
            status="confirmed",
            inspection_date=date(2026, 4, 1),
            inspected_qty=Decimal("10"),
            accepted_qty=Decimal("9"),
            rejected_qty=Decimal("1"),
            defect_qty=Decimal("1"),
        )
        self._seed_inspection(
            inspection_no="QI-TREND-002",
            company="COMP-A",
            supplier="SUP-A",
            item_code="ITEM-A",
            warehouse="WH-A",
            source_type="manual",
            status="confirmed",
            inspection_date=date(2026, 5, 5),
            inspected_qty=Decimal("12"),
            accepted_qty=Decimal("10"),
            rejected_qty=Decimal("2"),
            defect_qty=Decimal("2"),
        )

        monthly = self.client.get(
            "/api/quality/statistics/trend?period=monthly&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(monthly.status_code, 200, monthly.text)
        monthly_data = monthly.json()["data"]
        periods = [row["period"] for row in monthly_data["points"]]
        self.assertIn("2026-04", periods)
        self.assertIn("2026-05", periods)
        first_month_point = monthly_data["points"][0]
        self.assertIn("period_key", first_month_point)
        self.assertIn("inspection_count", first_month_point)
        self.assertIn("defect_rate", first_month_point)
        self.assertIn("rejected_rate", first_month_point)

        weekly = self.client.get(
            "/api/quality/statistics/trend?period=weekly&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(weekly.status_code, 200, weekly.text)
        weekly_data = weekly.json()["data"]
        self.assertTrue(all("-W" in row["period"] for row in weekly_data["points"]))


if __name__ == "__main__":
    unittest.main()
