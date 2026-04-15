"""Audit and error-path tests for factory statement APIs (TASK-006B)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.core.error_codes import FACTORY_STATEMENT_DATABASE_WRITE_FAILED
from app.core.error_codes import FACTORY_STATEMENT_INTERNAL_ERROR
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from app.core.exceptions import BusinessException
from app.models.audit import LyOperationAuditLog
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementItem
from app.models.subcontract import LySubcontractInspection
from tests.test_factory_statement_api import FactoryStatementApiBase
import app.routers.factory_statement as factory_statement_router


class FactoryStatementAuditTest(FactoryStatementApiBase):
    """Validate write-failure classification and audit boundaries."""

    def test_commit_failure_is_classified_as_database_write_failed(self) -> None:
        payload = self._create_payload(idempotency_key="idem-db-write-fail")

        with patch.object(
            factory_statement_router,
            "_commit_or_raise_write_error",
            side_effect=BusinessException(code=FACTORY_STATEMENT_DATABASE_WRITE_FAILED),
        ):
            response = self.client.post(
                "/api/factory-statements/",
                headers=self._headers(),
                json=payload,
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_DATABASE_WRITE_FAILED")

    def test_operation_audit_failure_row_is_written_without_sensitive_tokens(self) -> None:
        response = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-audit-clean"),
        )
        self.assertEqual(response.status_code, 200)

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:create",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )

        self.assertIsNotNone(row)
        merged = " ".join(
            [
                str(row.resource_no or ""),
                str(row.error_code or ""),
                str(row.before_data or ""),
                str(row.after_data or ""),
            ]
        ).lower()
        self.assertNotIn("authorization", merged)
        self.assertNotIn("cookie", merged)
        self.assertNotIn("token", merged)
        self.assertNotIn("secret", merged)

    def test_active_scope_conflict_is_audited_with_business_error_code(self) -> None:
        first = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-audit-active-scope-1"),
        )
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-audit-active-scope-2"),
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "FACTORY_STATEMENT_ACTIVE_SCOPE_EXISTS",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(row)

    def test_create_runtime_error_returns_internal_error_envelope_without_partial_writes(self) -> None:
        with patch.object(
            factory_statement_router.FactoryStatementService,
            "create_draft",
            side_effect=RuntimeError("create draft boom"),
        ):
            response = self.client.post(
                "/api/factory-statements/",
                headers=self._headers(),
                json=self._create_payload(idempotency_key="idem-audit-runtime-error"),
            )

        self.assertEqual(response.status_code, 500)
        body = response.json()
        self.assertEqual(body["code"], FACTORY_STATEMENT_INTERNAL_ERROR)
        self.assertEqual(body["message"], "加工厂对账单处理失败")
        self.assertIsNone(body["data"])

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyFactoryStatement).count(), 0)
            self.assertEqual(session.query(LyFactoryStatementItem).count(), 0)

            inspections = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.id.in_([300, 301]))
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )
            self.assertEqual(len(inspections), 2)
            for row in inspections:
                self.assertEqual(str(row.settlement_status), "unsettled")
                self.assertIsNone(row.statement_id)
                self.assertIsNone(row.statement_no)

            audit_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == FACTORY_STATEMENT_INTERNAL_ERROR,
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )

        self.assertIsNotNone(audit_row)
        self.assertIsNone(audit_row.resource_id)

    def test_confirm_and_cancel_success_audit_rows_exist(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-audit-confirm-cancel-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-audit-confirm-op", "remark": "ok"},
        )
        self.assertEqual(confirmed.status_code, 200)

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-audit-cancel-op", "reason": "rollback"},
        )
        self.assertEqual(cancelled.status_code, 200)

        with self.SessionLocal() as session:
            confirm_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:confirm",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            cancel_row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:cancel",
                    LyOperationAuditLog.result == "success",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(confirm_row)
        self.assertIsNotNone(cancel_row)

    def test_payable_permission_denied_writes_failure_audit(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-audit-payable-denied-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-audit-payable-denied-confirm", "remark": "ok"},
        )
        self.assertEqual(confirmed.status_code, 200)

        denied = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(role="Viewer"),
            json={
                "idempotency_key": "idem-audit-payable-denied",
                "payable_account": "2202 - AP - C",
                "cost_center": "Main - C",
                "posting_date": "2026-04-15",
                "remark": "deny",
            },
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:payable_draft_create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "FACTORY_STATEMENT_PERMISSION_DENIED",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(row)

    def test_payable_idempotency_conflict_writes_failure_audit(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-audit-payable-conflict-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-audit-payable-conflict-confirm", "remark": "ok"},
        )
        self.assertEqual(confirmed.status_code, 200)

        with patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "validate_cost_center",
            return_value=True,
        ):
            first = self.client.post(
                f"/api/factory-statements/{statement_id}/payable-draft",
                headers=self._headers(),
                json={
                    "idempotency_key": "idem-audit-payable-conflict",
                    "payable_account": "2202 - AP - C",
                    "cost_center": "Main - C",
                    "posting_date": "2026-04-15",
                    "remark": "A",
                },
            )
            self.assertEqual(first.status_code, 200)

            conflict = self.client.post(
                f"/api/factory-statements/{statement_id}/payable-draft",
                headers=self._headers(),
                json={
                    "idempotency_key": "idem-audit-payable-conflict",
                    "payable_account": "2202 - AP - C",
                    "cost_center": "Main - C",
                    "posting_date": "2026-04-16",
                    "remark": "B",
                },
            )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:payable_draft_create",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
            outbox_count = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .count()
            )
        self.assertIsNotNone(row)
        self.assertEqual(outbox_count, 1)

    def test_cancel_blocked_by_active_payable_outbox_writes_failure_audit(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-audit-cancel-active-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": "idem-audit-cancel-active-confirm", "remark": "ok"},
        )
        self.assertEqual(confirmed.status_code, 200)

        with patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "validate_cost_center",
            return_value=True,
        ):
            payable = self.client.post(
                f"/api/factory-statements/{statement_id}/payable-draft",
                headers=self._headers(),
                json={
                    "idempotency_key": "idem-audit-cancel-active-payable",
                    "payable_account": "2202 - AP - C",
                    "cost_center": "Main - C",
                    "posting_date": "2026-04-15",
                    "remark": "pending outbox",
                },
            )
        self.assertEqual(payable.status_code, 200)

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-audit-cancel-active-cancel", "reason": "deny"},
        )
        self.assertEqual(cancelled.status_code, 409)
        self.assertEqual(cancelled.json()["code"], "FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE")

        with self.SessionLocal() as session:
            row = (
                session.query(LyOperationAuditLog)
                .filter(
                    LyOperationAuditLog.module == "factory_statement",
                    LyOperationAuditLog.action == "factory_statement:cancel",
                    LyOperationAuditLog.result == "failed",
                    LyOperationAuditLog.error_code == "FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE",
                )
                .order_by(LyOperationAuditLog.id.desc())
                .first()
            )
        self.assertIsNotNone(row)


if __name__ == "__main__":
    unittest.main()
