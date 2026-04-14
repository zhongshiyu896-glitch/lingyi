"""Operation/security audit behavior tests for style-profit APIs (TASK-005E1)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.core.exceptions import AuditWriteFailed
from app.models.audit import LyOperationAuditLog
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector
from app.services.audit_service import AuditService
from sqlalchemy.exc import SQLAlchemyError
import app.routers.style_profit as style_profit_router
from tests.test_style_profit_api import StyleProfitApiBase


class StyleProfitApiAuditTest(StyleProfitApiBase):
    """Validate operation audit success/failure paths."""

    def test_create_success_writes_operation_audit(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-AUD-CREATE-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-aud-create-success",
        }
        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=lambda *args, **kwargs: self._trusted_request(args[-1]),
        ):
            response = self.client.post(
                "/api/reports/style-profit/snapshots",
                json=payload,
                headers=self._headers(),
            )
        self.assertEqual(response.status_code, 200)

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:snapshot_create",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_list_missing_scope_writes_operation_audit_failure(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots",
            headers=self._headers(role="Finance Manager"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_SOURCE_READ_FAILED")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:read",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "STYLE_PROFIT_SOURCE_READ_FAILED",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_list_missing_scope_audit_failure_returns_audit_write_failed(self) -> None:
        with patch.object(AuditService, "record_failure", side_effect=AuditWriteFailed()):
            response = self.client.get(
                "/api/reports/style-profit/snapshots",
                headers=self._headers(role="Finance Manager"),
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")

    def test_list_database_read_failure_writes_operation_audit_failure(self) -> None:
        with patch.object(style_profit_router.Session, "query", side_effect=SQLAlchemyError("db down")):
            response = self.client.get(
                "/api/reports/style-profit/snapshots",
                params={"company": "COMP-A", "item_code": "STYLE-A"},
                headers=self._headers(role="Finance Manager"),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "DATABASE_READ_FAILED")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:read",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "DATABASE_READ_FAILED",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_create_rejected_client_source_rows_writes_operation_audit_failure(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-AUD-CREATE-FORBIDDEN-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-aud-create-forbidden",
            "sales_order_rows": [{"name": "HACK"}],
        }
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(role="Finance Manager"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:snapshot_create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_create_collector_fail_closed_writes_operation_audit_failure(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-AUD-CREATE-COLLECTOR-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-aud-create-collector-fail-closed",
        }
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(role="Finance Manager"),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_SOURCE_UNAVAILABLE")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:snapshot_create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "STYLE_PROFIT_SOURCE_UNAVAILABLE",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_create_failure_writes_operation_audit_failure(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-AUD-CREATE-002",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V2",
            "idempotency_key": "idem-aud-create-failed",
        }
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_INVALID_FORMULA_VERSION")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:snapshot_create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "STYLE_PROFIT_INVALID_FORMULA_VERSION",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_detail_success_writes_operation_audit(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots/1",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:read",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_detail_failure_writes_operation_audit(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots/999999",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_NOT_FOUND")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "style_profit",
                    LyOperationAuditLog.action == "style_profit:read",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "STYLE_PROFIT_NOT_FOUND",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            self.assertIsNotNone(row)

    def test_detail_audit_write_failure_returns_audit_write_failed(self) -> None:
        with patch.object(AuditService, "record_success", side_effect=AuditWriteFailed()):
            response = self.client.get(
                "/api/reports/style-profit/snapshots/1",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "AUDIT_WRITE_FAILED")


if __name__ == "__main__":
    unittest.main()
