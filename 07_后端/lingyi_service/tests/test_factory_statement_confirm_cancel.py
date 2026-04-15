"""Confirm/cancel boundary tests for factory statement module (TASK-006D1)."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from app.models.subcontract import LySubcontractInspection
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from tests.test_factory_statement_api import FactoryStatementApiBase


class FactoryStatementConfirmCancelTest(FactoryStatementApiBase):
    """Validate cancel vs payable outbox mutual exclusion."""

    @staticmethod
    def _payable_payload(*, idempotency_key: str) -> dict[str, str]:
        return {
            "idempotency_key": idempotency_key,
            "payable_account": "2202 - AP - C",
            "cost_center": "Main - C",
            "posting_date": "2026-04-15",
            "remark": "task-006d1",
        }

    def _create_confirmed_statement(self, *, idempotency_key: str) -> int:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key=idempotency_key),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json={"idempotency_key": f"{idempotency_key}-confirm", "remark": "ok"},
        )
        self.assertEqual(confirmed.status_code, 200)
        return statement_id

    def _create_pending_outbox(self, *, statement_id: int, idempotency_key: str) -> int:
        with patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "validate_cost_center",
            return_value=True,
        ):
            response = self.client.post(
                f"/api/factory-statements/{statement_id}/payable-draft",
                headers=self._headers(),
                json=self._payable_payload(idempotency_key=idempotency_key),
            )
        self.assertEqual(response.status_code, 200)
        return int(response.json()["data"]["payable_outbox_id"])

    def test_cancel_blocked_when_pending_payable_outbox_exists(self) -> None:
        statement_id = self._create_confirmed_statement(idempotency_key="idem-cancel-blocked-pending")
        self._create_pending_outbox(statement_id=statement_id, idempotency_key="idem-cancel-blocked-pending-outbox")

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-blocked-pending-op", "reason": "must deny"},
        )
        self.assertEqual(cancelled.status_code, 409)
        self.assertEqual(cancelled.json()["code"], "FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            inspections = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.id.in_([300, 301]))
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )

        self.assertEqual(str(statement.statement_status), "confirmed")
        self.assertEqual(len(inspections), 2)
        self.assertTrue(all(str(row.settlement_status) == "statement_locked" for row in inspections))
        self.assertTrue(all(int(row.statement_id) == statement_id for row in inspections))

    def test_cancel_allowed_when_only_failed_or_dead_outbox_exists(self) -> None:
        statement_id = self._create_confirmed_statement(idempotency_key="idem-cancel-allow-failed")
        outbox_id = self._create_pending_outbox(statement_id=statement_id, idempotency_key="idem-cancel-allow-failed-outbox")

        with self.SessionLocal() as session:
            row = session.query(LyFactoryStatementPayableOutbox).filter(LyFactoryStatementPayableOutbox.id == outbox_id).one()
            row.status = "failed"
            session.commit()

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-cancel-allow-failed-op", "reason": "allow"},
        )
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["code"], "0")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            inspections = (
                session.query(LySubcontractInspection)
                .filter(LySubcontractInspection.id.in_([300, 301]))
                .order_by(LySubcontractInspection.id.asc())
                .all()
            )

        self.assertEqual(str(statement.statement_status), "cancelled")
        self.assertTrue(all(str(row.settlement_status) == "unsettled" for row in inspections))


if __name__ == "__main__":
    unittest.main()
