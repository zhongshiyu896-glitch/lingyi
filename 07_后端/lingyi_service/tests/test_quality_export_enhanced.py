"""Enhanced export tests for quality module (TASK-030F)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO
import os
import unittest
from zipfile import ZipFile

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


class QualityExportEnhancedTest(unittest.TestCase):
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
    def _headers(role: str = "Quality Manager") -> dict[str, str]:
        return {"X-LY-Dev-User": "quality.user", "X-LY-Dev-Roles": role}

    def _seed_inspection(
        self,
        *,
        inspection_no: str,
        company: str,
        status: str,
        supplier: str,
        warehouse: str,
        item_code: str,
        defect_code: str = "DEF-001",
        action: str = "create",
    ) -> int:
        with self.SessionLocal() as session:
            inspection = LyQualityInspection(
                inspection_no=inspection_no,
                company=company,
                source_type="manual",
                source_id=None,
                item_code=item_code,
                supplier=supplier,
                warehouse=warehouse,
                inspection_date=date(2026, 4, 20),
                inspected_qty=Decimal("10"),
                accepted_qty=Decimal("8"),
                rejected_qty=Decimal("2"),
                defect_qty=Decimal("2"),
                defect_rate=Decimal("0.200000"),
                rejected_rate=Decimal("0.200000"),
                result="partial",
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
                    sample_qty=Decimal("10"),
                    accepted_qty=Decimal("8"),
                    rejected_qty=Decimal("2"),
                    defect_qty=Decimal("2"),
                    result="partial",
                    remark="item-remark",
                )
            )
            session.flush()

            session.add(
                LyQualityDefect(
                    inspection_id=int(inspection.id),
                    item_id=None,
                    defect_code=defect_code,
                    defect_name="线头",
                    defect_qty=Decimal("2"),
                    severity="major",
                    remark="defect-remark",
                )
            )
            session.add(
                LyQualityOperationLog(
                    inspection_id=int(inspection.id),
                    company=company,
                    from_status=None,
                    to_status=status,
                    action=action,
                    operator="quality.user",
                    request_id="req-seed",
                    remark="log-remark",
                )
            )
            session.commit()
            return int(inspection.id)

    def test_export_xlsx_contains_required_sheets(self) -> None:
        self._seed_inspection(
            inspection_no="QI-XLSX-OK",
            company="COMP-A",
            status="confirmed",
            supplier="SUP-A",
            warehouse="WH-A",
            item_code="ITEM-A",
        )
        self._seed_inspection(
            inspection_no="QI-XLSX-CANCEL",
            company="COMP-A",
            status="cancelled",
            supplier="SUP-A",
            warehouse="WH-A",
            item_code="ITEM-A",
        )

        response = self.client.get(
            "/api/quality/export?format=xlsx&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            response.headers.get("content-type", ""),
        )

        with ZipFile(BytesIO(response.content), "r") as zf:
            workbook_xml = zf.read("xl/workbook.xml").decode("utf-8")
            self.assertIn("检验单", workbook_xml)
            self.assertIn("检验明细", workbook_xml)
            self.assertIn("缺陷记录", workbook_xml)
            sheet1 = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
            self.assertIn("QI-XLSX-OK", sheet1)
            self.assertNotIn("QI-XLSX-CANCEL", sheet1)

    def test_export_pdf_single_contains_detail_defect_log(self) -> None:
        inspection_id = self._seed_inspection(
            inspection_no="QI-PDF-ONE",
            company="COMP-A",
            status="confirmed",
            supplier="SUP-A",
            warehouse="WH-A",
            item_code="ITEM-A",
            defect_code="DEF-PDF-1",
            action="confirm",
        )

        response = self.client.get(
            f"/api/quality/export?format=pdf&inspection_id={inspection_id}",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("application/pdf", response.headers.get("content-type", ""))
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn(b"QI-PDF-ONE", response.content)
        self.assertIn(b"Defects", response.content)
        self.assertIn(b"DEF-PDF-1", response.content)
        self.assertIn(b"Logs", response.content)

    def test_export_pdf_batch_zip_and_company_filter(self) -> None:
        self._seed_inspection(
            inspection_no="QI-PDF-A",
            company="COMP-A",
            status="confirmed",
            supplier="SUP-A",
            warehouse="WH-A",
            item_code="ITEM-A",
        )
        self._seed_inspection(
            inspection_no="QI-PDF-B",
            company="COMP-B",
            status="confirmed",
            supplier="SUP-B",
            warehouse="WH-B",
            item_code="ITEM-B",
        )
        self._seed_inspection(
            inspection_no="QI-PDF-CANCEL",
            company="COMP-A",
            status="cancelled",
            supplier="SUP-A",
            warehouse="WH-A",
            item_code="ITEM-A",
        )

        response = self.client.get(
            "/api/quality/export?format=pdf&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("application/zip", response.headers.get("content-type", ""))

        with ZipFile(BytesIO(response.content), "r") as zf:
            names = zf.namelist()
            joined = "\n".join(names)
            self.assertIn("QI-PDF-A", joined)
            self.assertNotIn("QI-PDF-B", joined)
            self.assertNotIn("QI-PDF-CANCEL", joined)

    def test_export_csv_excludes_cancelled_and_keeps_company_filter(self) -> None:
        self._seed_inspection(
            inspection_no="QI-CSV-A",
            company="COMP-A",
            status="confirmed",
            supplier="SUP-A",
            warehouse="WH-A",
            item_code="ITEM-A",
        )
        self._seed_inspection(
            inspection_no="QI-CSV-CANCEL",
            company="COMP-A",
            status="cancelled",
            supplier="SUP-A",
            warehouse="WH-A",
            item_code="ITEM-A",
        )
        self._seed_inspection(
            inspection_no="QI-CSV-B",
            company="COMP-B",
            status="confirmed",
            supplier="SUP-B",
            warehouse="WH-B",
            item_code="ITEM-B",
        )

        response = self.client.get(
            "/api/quality/export?format=csv&company=COMP-A",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/csv", response.headers.get("content-type", ""))
        text = response.content.decode("utf-8-sig")
        self.assertIn("QI-CSV-A", text)
        self.assertNotIn("QI-CSV-CANCEL", text)
        self.assertNotIn("QI-CSV-B", text)


if __name__ == "__main__":
    unittest.main()
