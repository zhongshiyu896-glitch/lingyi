"""Model and service tests for quality management baseline (TASK-012B)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import BusinessException
from app.core.error_codes import QUALITY_INVALID_SOURCE
from app.models.quality import Base as QualityBase
from app.models.quality import LyQualityDefect
from app.models.quality import LyQualityInspection
from app.models.quality import LyQualityInspectionItem
from app.models.quality import LyQualityOperationLog
from app.schemas.quality import QualityInspectionCreateRequest
from app.services.quality_service import QualityService
from app.services.quality_service import QualitySourceValidationSnapshot
from app.services.quality_service import QualitySourceValidator


class _FakeSourceValidator:
    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def validate_for_payload(self, **kwargs):
        self.calls += 1
        if self.fail:
            raise BusinessException(code="QUALITY_SOURCE_UNAVAILABLE")
        return QualitySourceValidationSnapshot(master_data={"item": {"name": kwargs["item_code"]}}, source=None)


class _OwnershipSourceValidator(QualitySourceValidator):
    def __init__(self, docs: dict[tuple[str, str], dict]):
        self.docs = docs

    def _require_resource(self, doctype: str, name: str, *, require_submitted: bool) -> dict:
        return dict(self.docs[(doctype, name)])


class QualityModelServiceTest(unittest.TestCase):
    """Validate table constraints and service calculations."""

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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        with self.SessionLocal() as session:
            session.query(LyQualityOperationLog).delete()
            session.query(LyQualityDefect).delete()
            session.query(LyQualityInspectionItem).delete()
            session.query(LyQualityInspection).delete()
            session.commit()

    @staticmethod
    def _request(**overrides) -> QualityInspectionCreateRequest:
        payload = {
            "company": "COMP-A",
            "source_type": "manual",
            "item_code": "ITEM-A",
            "inspection_date": date(2026, 4, 16),
            "inspected_qty": Decimal("5"),
            "accepted_qty": Decimal("4"),
            "rejected_qty": Decimal("1"),
            "defect_qty": Decimal("1"),
            "result": "partial",
        }
        payload.update(overrides)
        return QualityInspectionCreateRequest(**payload)

    def test_rates_are_zero_when_inspected_qty_is_zero(self) -> None:
        with self.SessionLocal() as session:
            service = QualityService(session=session, source_validator=_FakeSourceValidator())
            data = service.create_inspection(
                payload=self._request(inspected_qty=Decimal("0"), accepted_qty=Decimal("0"), rejected_qty=Decimal("0"), defect_qty=Decimal("0")),
                operator="quality.user",
                request_id="req-zero",
            )
            self.assertEqual(data.defect_rate, Decimal("0"))
            self.assertEqual(data.rejected_rate, Decimal("0"))

    def test_qty_mismatch_fails_before_insert(self) -> None:
        with self.SessionLocal() as session:
            service = QualityService(session=session, source_validator=_FakeSourceValidator())
            with self.assertRaises(BusinessException) as ctx:
                service.create_inspection(
                    payload=self._request(accepted_qty=Decimal("3"), rejected_qty=Decimal("1")),
                    operator="quality.user",
                    request_id="req-mismatch",
                )
            self.assertEqual(ctx.exception.code, "QUALITY_QTY_MISMATCH")
            self.assertEqual(session.query(LyQualityInspection).count(), 0)

    def test_invalid_result_fails_closed(self) -> None:
        with self.SessionLocal() as session:
            service = QualityService(session=session, source_validator=_FakeSourceValidator())
            with self.assertRaises(BusinessException) as ctx:
                service.create_inspection(
                    payload=self._request(result="approved"),
                    operator="quality.user",
                    request_id="req-result",
                )
            self.assertEqual(ctx.exception.code, "QUALITY_INVALID_RESULT")

    def test_source_unavailable_fails_closed(self) -> None:
        with self.SessionLocal() as session:
            validator = _FakeSourceValidator(fail=True)
            service = QualityService(session=session, source_validator=validator)
            with self.assertRaises(BusinessException) as ctx:
                service.create_inspection(
                    payload=self._request(),
                    operator="quality.user",
                    request_id="req-source",
                )
            self.assertEqual(ctx.exception.code, "QUALITY_SOURCE_UNAVAILABLE")
            self.assertEqual(validator.calls, 1)

    def test_db_constraint_rejects_invalid_status(self) -> None:
        with self.SessionLocal() as session:
            session.add(
                LyQualityInspection(
                    inspection_no="QI-BAD-STATUS",
                    company="COMP-A",
                    source_type="manual",
                    item_code="ITEM-A",
                    inspection_date=date(2026, 4, 16),
                    inspected_qty=Decimal("1"),
                    accepted_qty=Decimal("1"),
                    rejected_qty=Decimal("0"),
                    defect_qty=Decimal("0"),
                    defect_rate=Decimal("0"),
                    rejected_rate=Decimal("0"),
                    result="pass",
                    status="deleted",
                    created_by="quality.user",
                )
            )
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_quality_inspection_has_supplier_date_index(self) -> None:
        indexes = {index.name: [column.name for column in index.columns] for index in LyQualityInspection.__table__.indexes}
        self.assertEqual(indexes["idx_ly_quality_inspection_supplier_date"], ["supplier", "inspection_date"])

    def test_incoming_material_source_requires_company_and_item_ownership(self) -> None:
        docs = {
            ("Company", "COMP-A"): {"name": "COMP-A"},
            ("Item", "ITEM-A"): {"name": "ITEM-A"},
            ("Supplier", "SUP-A"): {"name": "SUP-A"},
            ("Purchase Receipt", "PR-1"): {
                "name": "PR-1",
                "company": "COMP-A",
                "supplier": "SUP-A",
                "docstatus": 1,
                "items": [{"item_code": "ITEM-A"}],
            },
        }
        snapshot = _OwnershipSourceValidator(docs).validate_for_payload(
            company="COMP-A",
            item_code="ITEM-A",
            supplier="SUP-A",
            warehouse=None,
            source_type="incoming_material",
            source_id="PR-1",
        )
        self.assertEqual(snapshot.source["name"], "PR-1")

        docs[("Purchase Receipt", "PR-1")] = {**docs[("Purchase Receipt", "PR-1")], "company": "COMP-B"}
        with self.assertRaises(BusinessException) as ctx:
            _OwnershipSourceValidator(docs).validate_for_payload(
                company="COMP-A",
                item_code="ITEM-A",
                supplier="SUP-A",
                warehouse=None,
                source_type="incoming_material",
                source_id="PR-1",
            )
        self.assertEqual(ctx.exception.code, QUALITY_INVALID_SOURCE)

    def test_finished_goods_source_requires_item_evidence(self) -> None:
        docs = {
            ("Company", "COMP-A"): {"name": "COMP-A"},
            ("Item", "ITEM-A"): {"name": "ITEM-A"},
            ("Stock Entry", "SE-1"): {
                "name": "SE-1",
                "company": "COMP-A",
                "docstatus": 1,
                "items": [{"item_code": "ITEM-B"}],
            },
        }
        with self.assertRaises(BusinessException) as ctx:
            _OwnershipSourceValidator(docs).validate_for_payload(
                company="COMP-A",
                item_code="ITEM-A",
                supplier=None,
                warehouse=None,
                source_type="finished_goods",
                source_id="SE-1",
            )
        self.assertEqual(ctx.exception.code, QUALITY_INVALID_SOURCE)


if __name__ == "__main__":
    unittest.main()
