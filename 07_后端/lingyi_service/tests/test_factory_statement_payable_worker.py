"""Payable outbox worker API tests for factory statement module (TASK-006D)."""

from __future__ import annotations

from datetime import datetime
from datetime import timedelta
import os
import unittest
from unittest.mock import patch

from app.core.exceptions import ERPNextServiceUnavailableError
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementLog
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceLookup
from app.services.factory_statement_payable_outbox_service import FactoryStatementPayableOutboxService
from tests.test_factory_statement_api import FactoryStatementApiBase


class FactoryStatementPayableWorkerTest(FactoryStatementApiBase):
    """Validate internal payable worker endpoint behavior."""

    def setUp(self) -> None:
        super().setUp()
        os.environ["LINGYI_SERVICE_ACCOUNT_USERS"] = "svc.payable"

    @staticmethod
    def _payable_payload(*, idempotency_key: str) -> dict[str, str]:
        return {
            "idempotency_key": idempotency_key,
            "payable_account": "2202 - AP - C",
            "cost_center": "Main - C",
            "posting_date": "2026-04-15",
            "remark": "worker",
        }

    def _create_confirmed_statement(self, *, create_key: str) -> int:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Finance Manager"),
            json=self._create_payload(idempotency_key=create_key),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(role="Finance Manager"),
            json={"idempotency_key": f"{create_key}-confirm", "remark": "confirm"},
        )
        self.assertEqual(confirmed.status_code, 200)
        return statement_id

    def _create_payable_outbox(self, *, statement_id: int, idem_key: str) -> None:
        with patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "validate_cost_center",
            return_value=True,
        ):
            created = self.client.post(
                f"/api/factory-statements/{statement_id}/payable-draft",
                headers=self._headers(role="Finance Manager"),
                json=self._payable_payload(idempotency_key=idem_key),
            )
        self.assertEqual(created.status_code, 200)

    def _run_worker_once(self, *, dry_run: bool = False) -> dict:
        response = self.client.post(
            "/api/factory-statements/internal/payable-draft-sync/run-once",
            headers=self._headers(role="LY Integration Service", user="svc.payable"),
            json={"batch_size": 20, "dry_run": dry_run},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        return response.json()["data"]

    def test_worker_requires_service_account_even_with_worker_role(self) -> None:
        response = self.client.post(
            "/api/factory-statements/internal/payable-draft-sync/run-once",
            headers=self._headers(role="LY Integration Service", user="worker.normal"),
            json={"batch_size": 20, "dry_run": False},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

    def test_worker_rejects_user_without_worker_action(self) -> None:
        response = self.client.post(
            "/api/factory-statements/internal/payable-draft-sync/run-once",
            headers=self._headers(role="Finance Manager", user="svc.payable"),
            json={"batch_size": 20, "dry_run": False},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

    def test_worker_processes_outbox_and_updates_statement_status(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-success-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-success-outbox")

        with patch.object(ERPNextPurchaseInvoiceAdapter, "find_purchase_invoice_by_event_key", return_value=None), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "create_purchase_invoice_draft",
            return_value=ERPNextPurchaseInvoiceLookup(name="PINV-0001", docstatus=0, status="Draft"),
        ):
            response = self.client.post(
                "/api/factory-statements/internal/payable-draft-sync/run-once",
                headers=self._headers(role="LY Integration Service", user="svc.payable"),
                json={"batch_size": 20, "dry_run": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        data = response.json()["data"]
        self.assertEqual(data["processed_count"], 1)
        self.assertEqual(data["succeeded_count"], 1)
        self.assertEqual(data["failed_count"], 0)

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            outbox = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .one()
            )
        self.assertEqual(str(statement.statement_status), "payable_draft_created")
        self.assertEqual(str(outbox.status), "succeeded")
        self.assertEqual(str(outbox.erpnext_purchase_invoice), "PINV-0001")
        self.assertEqual(int(outbox.erpnext_docstatus), 0)

    def test_worker_fails_when_erpnext_returns_non_draft_docstatus(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-invalid-docstatus-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-invalid-docstatus-outbox")

        with patch.object(ERPNextPurchaseInvoiceAdapter, "find_purchase_invoice_by_event_key", return_value=None), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "create_purchase_invoice_draft",
            return_value=ERPNextPurchaseInvoiceLookup(name="PINV-0002", docstatus=1, status="Submitted"),
        ):
            response = self.client.post(
                "/api/factory-statements/internal/payable-draft-sync/run-once",
                headers=self._headers(role="LY Integration Service", user="svc.payable"),
                json={"batch_size": 20, "dry_run": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["failed_count"], 1)

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            outbox = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .one()
            )
        self.assertEqual(str(statement.statement_status), "confirmed")
        self.assertEqual(str(outbox.status), "failed")
        self.assertEqual(str(outbox.last_error_code), "FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS")

    def test_worker_dry_run_does_not_call_erpnext_or_mutate_outbox(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-dryrun-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-dryrun-outbox")

        with patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "create_purchase_invoice_draft",
            side_effect=AssertionError("dry_run should not call erpnext"),
        ), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "find_purchase_invoice_by_event_key",
            side_effect=AssertionError("dry_run should not call erpnext"),
        ):
            response = self.client.post(
                "/api/factory-statements/internal/payable-draft-sync/run-once",
                headers=self._headers(role="LY Integration Service", user="svc.payable"),
                json={"batch_size": 20, "dry_run": True},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertTrue(bool(response.json()["data"]["dry_run"]))
        self.assertEqual(response.json()["data"]["processed_count"], 1)
        self.assertEqual(response.json()["data"]["succeeded_count"], 0)
        self.assertEqual(response.json()["data"]["failed_count"], 0)

        with self.SessionLocal() as session:
            outbox = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .one()
            )
        self.assertEqual(str(outbox.status), "pending")

    def test_worker_failed_outbox_reaches_dead_after_max_attempts(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-dead-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-dead-outbox")

        with self.SessionLocal() as session:
            outbox = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .one()
            )
            outbox.attempts = 1
            outbox.max_attempts = 1
            session.commit()

        with patch.object(ERPNextPurchaseInvoiceAdapter, "find_purchase_invoice_by_event_key", return_value=None), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "create_purchase_invoice_draft",
            side_effect=ERPNextServiceUnavailableError("timeout"),
        ):
            response = self.client.post(
                "/api/factory-statements/internal/payable-draft-sync/run-once",
                headers=self._headers(role="LY Integration Service", user="svc.payable"),
                json={"batch_size": 20, "dry_run": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["failed_count"], 1)
        self.assertEqual(response.json()["data"]["dead_count"], 1)

        with self.SessionLocal() as session:
            outbox = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .one()
            )
        self.assertEqual(str(outbox.status), "dead")

    def test_worker_skips_erp_calls_when_statement_cancelled(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-cancelled-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-cancelled-outbox")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            statement.statement_status = "cancelled"
            session.commit()

        with patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "find_purchase_invoice_by_event_key",
            side_effect=AssertionError("cancelled statement should not query erpnext"),
        ), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "create_purchase_invoice_draft",
            side_effect=AssertionError("cancelled statement should not create erpnext draft"),
        ):
            data = self._run_worker_once(dry_run=False)

        self.assertEqual(int(data["failed_count"]), 1)
        with self.SessionLocal() as session:
            outbox = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
            failure_log = (
                session.query(LyFactoryStatementLog)
                .filter(
                    LyFactoryStatementLog.statement_id == statement_id,
                    LyFactoryStatementLog.action == "factory_statement:payable_draft_worker",
                    LyFactoryStatementLog.remark.like("%FACTORY_STATEMENT_INVALID_STATUS%"),
                )
                .order_by(LyFactoryStatementLog.id.desc())
                .first()
            )
        self.assertEqual(str(outbox.status), "failed")
        self.assertEqual(str(outbox.last_error_code), "FACTORY_STATEMENT_INVALID_STATUS")
        self.assertIsNotNone(failure_log)

    def test_worker_skips_erp_calls_when_statement_draft(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-draft-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-draft-outbox")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            statement.statement_status = "draft"
            session.commit()

        with patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "find_purchase_invoice_by_event_key",
            side_effect=AssertionError("draft statement should not query erpnext"),
        ), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "create_purchase_invoice_draft",
            side_effect=AssertionError("draft statement should not create erpnext draft"),
        ):
            data = self._run_worker_once(dry_run=False)

        self.assertEqual(int(data["failed_count"]), 1)
        with self.SessionLocal() as session:
            outbox = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
        self.assertEqual(str(outbox.status), "failed")
        self.assertEqual(str(outbox.last_error_code), "FACTORY_STATEMENT_INVALID_STATUS")

    def test_worker_skips_erp_calls_when_statement_already_payable_draft_created(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-created-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-created-outbox")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            statement.statement_status = "payable_draft_created"
            session.commit()

        with patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "find_purchase_invoice_by_event_key",
            side_effect=AssertionError("payable_draft_created should not query erpnext"),
        ), patch.object(
            ERPNextPurchaseInvoiceAdapter,
            "create_purchase_invoice_draft",
            side_effect=AssertionError("payable_draft_created should not create erpnext draft"),
        ):
            data = self._run_worker_once(dry_run=False)

        self.assertEqual(int(data["failed_count"]), 1)
        with self.SessionLocal() as session:
            outbox = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
        self.assertEqual(str(outbox.status), "failed")
        self.assertEqual(str(outbox.last_error_code), "FACTORY_STATEMENT_INVALID_STATUS")

    def test_stale_id_with_unexpired_processing_lease_is_not_claimed(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-lease-unexpired-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-lease-unexpired-outbox")

        with self.SessionLocal() as session:
            row = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
            row.status = "processing"
            row.locked_by = "another-worker"
            row.locked_until = datetime.utcnow() + timedelta(minutes=5)
            row.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.commit()

            service = FactoryStatementPayableOutboxService(session=session)
            claims = service.claim_due(batch_size=20, worker_id="worker-a")
            session.rollback()

        self.assertEqual(claims, [])

    def test_stale_id_with_expired_processing_lease_can_be_claimed(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-lease-expired-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-lease-expired-outbox")

        with self.SessionLocal() as session:
            row = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
            row.status = "processing"
            row.locked_by = "another-worker"
            row.locked_until = datetime.utcnow() - timedelta(minutes=1)
            row.next_retry_at = datetime.utcnow() - timedelta(minutes=1)
            session.commit()

            service = FactoryStatementPayableOutboxService(session=session)
            claims = service.claim_due(batch_size=20, worker_id="worker-b")
            session.rollback()

        self.assertEqual(len(claims), 1)
        self.assertEqual(int(claims[0].statement_id), statement_id)

    def test_pending_or_failed_with_future_retry_is_not_claimed(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-future-retry-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-future-retry-outbox")

        with self.SessionLocal() as session:
            row = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
            row.status = "pending"
            row.next_retry_at = datetime.utcnow() + timedelta(minutes=30)
            row.locked_by = None
            row.locked_until = None
            session.commit()

            service = FactoryStatementPayableOutboxService(session=session)
            claims = service.claim_due(batch_size=20, worker_id="worker-c")
            session.rollback()

        self.assertEqual(claims, [])

    def test_failed_with_future_retry_is_not_claimed(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-future-failed-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-future-failed-outbox")

        with self.SessionLocal() as session:
            row = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
            row.status = "failed"
            row.next_retry_at = datetime.utcnow() + timedelta(minutes=30)
            row.locked_by = None
            row.locked_until = None
            session.commit()

            service = FactoryStatementPayableOutboxService(session=session)
            claims = service.claim_due(batch_size=20, worker_id="worker-c2")
            session.rollback()

        self.assertEqual(claims, [])

    def test_pending_or_failed_due_can_be_claimed(self) -> None:
        statement_id = self._create_confirmed_statement(create_key="idem-worker-due-retry-create")
        self._create_payable_outbox(statement_id=statement_id, idem_key="idem-worker-due-retry-outbox")

        with self.SessionLocal() as session:
            row = session.query(LyFactoryStatementPayableOutbox).filter(
                LyFactoryStatementPayableOutbox.statement_id == statement_id
            ).one()
            row.status = "failed"
            row.next_retry_at = datetime.utcnow() - timedelta(minutes=2)
            row.locked_by = None
            row.locked_until = None
            session.commit()

            service = FactoryStatementPayableOutboxService(session=session)
            claims = service.claim_due(batch_size=20, worker_id="worker-d")
            session.rollback()

        self.assertEqual(len(claims), 1)
        self.assertEqual(int(claims[0].statement_id), statement_id)


if __name__ == "__main__":
    unittest.main()
