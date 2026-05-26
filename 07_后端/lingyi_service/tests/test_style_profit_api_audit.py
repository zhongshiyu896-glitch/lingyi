"""Operation/security audit behavior tests for style-profit APIs (TASK-005E1)."""

from __future__ import annotations

import unittest
import os
from unittest.mock import patch

from app.core.error_codes import STYLE_PROFIT_SOURCE_UNAVAILABLE
from app.core.exceptions import AuditWriteFailed
from app.core.exceptions import BusinessException
from app.models.audit import LyOperationAuditLog
from app.services.style_profit_api_source_collector import StyleProfitApiSourceCollector
from app.services.audit_service import AuditService
from sqlalchemy.exc import SQLAlchemyError
import app.routers.style_profit as style_profit_router
from tests.test_style_profit_api import StyleProfitApiBase


class StyleProfitApiAuditTest(StyleProfitApiBase):
    """Validate operation audit success/failure paths."""

    _scenario_tag = "Z003-STYLE-PROFIT-20260526-034"

    def setUp(self) -> None:
        super().setUp()
        self._old_app_env = os.environ.get("APP_ENV")
        self._old_lingyi_db_url = os.environ.get("LINGYI_DB_URL")
        os.environ["APP_ENV"] = "development"
        os.environ["LINGYI_DB_URL"] = style_profit_router.STYLE_PROFIT_LOCAL_ALLOWED_DB_URL

    def tearDown(self) -> None:
        if self._old_app_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = self._old_app_env
        if self._old_lingyi_db_url is None:
            os.environ.pop("LINGYI_DB_URL", None)
        else:
            os.environ["LINGYI_DB_URL"] = self._old_lingyi_db_url

    def _headers(self, role: str = "Finance Manager") -> dict[str, str]:
        headers = super()._headers(role=role)
        headers["X-Request-ID"] = self._scenario_tag
        return headers

    def _source_ref(self, *, sales_order: str, formula_version: str, status_action: str) -> str:
        return "|".join(
            [
                self._scenario_tag,
                "COMP-A",
                "STYLE-A",
                sales_order,
                "actual_first",
                formula_version,
                status_action,
            ]
        )

    def _create_payload(
        self,
        *,
        sales_order: str,
        idem: str,
        formula_version: str = "STYLE_PROFIT_V1",
        status_action: str = "create",
    ) -> dict[str, object]:
        return {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": sales_order,
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": formula_version,
            "idempotency_key": f"{self._scenario_tag}-{idem}",
            "scenario_tag": self._scenario_tag,
            "source_ref": self._source_ref(
                sales_order=sales_order,
                formula_version=formula_version,
                status_action=status_action,
            ),
            "status_action": status_action,
        }

    def test_create_success_writes_operation_audit(self) -> None:
        payload = self._create_payload(
            sales_order="SO-AUD-CREATE-001",
            idem="idem-aud-create-success",
        )
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
        payload = self._create_payload(
            sales_order="SO-AUD-CREATE-FORBIDDEN-001",
            idem="idem-aud-create-forbidden",
        )
        payload["sales_order_rows"] = [{"name": "HACK"}]
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
        payload = self._create_payload(
            sales_order="SO-AUD-CREATE-COLLECTOR-001",
            idem="idem-aud-create-collector-fail-closed",
        )
        source_unavailable = BusinessException(
            code=STYLE_PROFIT_SOURCE_UNAVAILABLE,
            message="利润来源服务暂时不可用",
        )
        with patch.object(
            StyleProfitApiSourceCollector,
            "collect",
            side_effect=source_unavailable,
        ), patch.object(
            style_profit_router,
            "_build_local_style_profit_fallback_request",
            side_effect=source_unavailable,
        ):
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
        payload = self._create_payload(
            sales_order="SO-AUD-CREATE-002",
            idem="idem-aud-create-failed",
            formula_version="STYLE_PROFIT_V2",
        )
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
