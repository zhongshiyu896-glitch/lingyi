"""Payable-draft API tests for factory statement module (TASK-006D)."""

from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal
import unittest
from unittest.mock import patch

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ERPNextServiceUnavailableError
from app.models.factory_statement import LyFactoryStatement
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from app.services.erpnext_purchase_invoice_adapter import ERPNextPurchaseInvoiceAdapter
from app.services.factory_statement_payable_outbox_service import FactoryStatementPayableOutboxService
from tests.test_factory_statement_api import FactoryStatementApiBase


class FactoryStatementPayableApiTest(FactoryStatementApiBase):
    """Validate payable-draft outbox create API behavior."""

    @staticmethod
    def _active_statuses() -> tuple[str, ...]:
        return (
            FactoryStatementPayableOutboxService.STATUS_PENDING,
            FactoryStatementPayableOutboxService.STATUS_PROCESSING,
            FactoryStatementPayableOutboxService.STATUS_SUCCEEDED,
        )

    @staticmethod
    def _payable_payload(*, idempotency_key: str, posting_date: str = "2026-04-15", remark: str = "") -> dict[str, str]:
        return {
            "idempotency_key": idempotency_key,
            "payable_account": "2202 - AP - C",
            "cost_center": "Main - C",
            "posting_date": posting_date,
            "remark": remark,
        }

    def _create_and_confirm_statement(self, *, idempotency_key: str) -> int:
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
            json={"idempotency_key": f"{idempotency_key}-confirm", "remark": "confirm"},
        )
        self.assertEqual(confirmed.status_code, 200)
        return statement_id

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_confirmed_statement_can_create_payable_outbox(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-create")

        response = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-op-1", remark="create outbox"),
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], "0")
        data = body["data"]
        self.assertEqual(data["statement_id"], statement_id)
        self.assertEqual(data["status"], "confirmed")
        self.assertEqual(data["payable_outbox_status"], "pending")
        self.assertIsNone(data["purchase_invoice_name"])
        self.assertEqual(Decimal(data["net_amount"]), Decimal("4700"))

        with self.SessionLocal() as session:
            row = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .one_or_none()
            )
        self.assertIsNotNone(row)
        self.assertEqual(str(row.status), "pending")

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_list_and_detail_expose_payable_outbox_summary(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-summary")
        create_outbox = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-summary-op"),
        )
        self.assertEqual(create_outbox.status_code, 200)
        outbox_id = int(create_outbox.json()["data"]["payable_outbox_id"])

        list_response = self.client.get(
            "/api/factory-statements/",
            headers=self._headers(),
            params={"company": "COMP-A", "supplier": "SUP-A"},
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["code"], "0")
        list_item = next(item for item in list_response.json()["data"]["items"] if int(item["id"]) == statement_id)
        self.assertEqual(int(list_item["payable_outbox_id"]), outbox_id)
        self.assertEqual(list_item["payable_outbox_status"], "pending")
        self.assertIsNone(list_item["purchase_invoice_name"])
        self.assertIsNone(list_item["payable_error_code"])
        self.assertIsNone(list_item["payable_error_message"])

        detail_response = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["code"], "0")
        detail_data = detail_response.json()["data"]
        self.assertEqual(int(detail_data["payable_outbox_id"]), outbox_id)
        self.assertEqual(detail_data["payable_outbox_status"], "pending")
        self.assertIsNone(detail_data["purchase_invoice_name"])
        self.assertIn("payable_outboxes", detail_data)
        self.assertGreaterEqual(len(detail_data["payable_outboxes"]), 1)
        first_outbox = detail_data["payable_outboxes"][0]
        self.assertEqual(int(first_outbox["id"]), outbox_id)
        self.assertEqual(first_outbox["status"], "pending")

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_same_key_same_hash_replays_same_payable_outbox(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-replay-create")
        payload = self._payable_payload(idempotency_key="idem-payable-replay", remark="same")

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=payload,
        )
        self.assertEqual(first.status_code, 200)

        replay = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=payload,
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["code"], "0")
        self.assertTrue(bool(replay.json()["data"]["idempotent_replay"]))
        self.assertEqual(
            first.json()["data"]["payable_outbox_id"],
            replay.json()["data"]["payable_outbox_id"],
        )

        with self.SessionLocal() as session:
            total = session.query(LyFactoryStatementPayableOutbox).count()
        self.assertEqual(total, 1)

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_different_key_cannot_create_second_active_outbox(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-active-create")

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="manual-pay-1", posting_date="2026-04-15"),
        )
        self.assertEqual(first.status_code, 200)
        first_outbox_id = int(first.json()["data"]["payable_outbox_id"])

        second = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="manual-pay-2", posting_date="2026-04-15"),
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE")
        self.assertEqual(int(second.json()["data"]["existing_outbox_id"]), first_outbox_id)
        self.assertEqual(second.json()["data"]["existing_status"], "pending")

        with self.SessionLocal() as session:
            total = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .count()
            )
            active = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(
                    LyFactoryStatementPayableOutbox.statement_id == statement_id,
                    LyFactoryStatementPayableOutbox.status.in_(self._active_statuses()),
                )
                .count()
            )
        self.assertEqual(total, 1)
        self.assertEqual(active, 1)

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_same_key_different_hash_returns_conflict(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-conflict-create")

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-conflict", posting_date="2026-04-15"),
        )
        self.assertEqual(first.status_code, 200)

        conflict = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-conflict", posting_date="2026-04-16"),
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT")

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_failed_outbox_allows_new_request_with_new_business_payload(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-failed-retry-create")

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-failed-retry-1", posting_date="2026-04-15"),
        )
        self.assertEqual(first.status_code, 200)
        first_outbox_id = int(first.json()["data"]["payable_outbox_id"])

        with self.SessionLocal() as session:
            row = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.id == first_outbox_id)
                .one()
            )
            row.status = FactoryStatementPayableOutboxService.STATUS_FAILED
            row.next_retry_at = datetime.utcnow()
            session.commit()

        second = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-failed-retry-2", posting_date="2026-04-16"),
        )
        self.assertEqual(second.status_code, 200)
        second_outbox_id = int(second.json()["data"]["payable_outbox_id"])
        self.assertNotEqual(second_outbox_id, first_outbox_id)

        with self.SessionLocal() as session:
            rows = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .order_by(LyFactoryStatementPayableOutbox.id.asc())
                .all()
            )
        self.assertEqual(len(rows), 2)
        self.assertEqual(str(rows[0].status), FactoryStatementPayableOutboxService.STATUS_FAILED)
        self.assertEqual(str(rows[1].status), FactoryStatementPayableOutboxService.STATUS_PENDING)

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_event_key_is_stable_and_excludes_idempotency(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-event-create")

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="manual-pay-1", posting_date="2026-04-15"),
        )
        self.assertEqual(first.status_code, 200)
        first_outbox_id = int(first.json()["data"]["payable_outbox_id"])

        second = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="manual-pay-2", posting_date="2026-04-15"),
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            row = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.id == first_outbox_id)
                .one()
            )
            outbox_service = FactoryStatementPayableOutboxService(session=session)
            expected_event_key = outbox_service.build_event_key(
                company=str(statement.company),
                statement_id=int(statement.id),
                statement_no=str(statement.statement_no),
                supplier=str(statement.supplier),
                net_amount=Decimal(statement.net_amount),
                payable_account="2202 - AP - C",
                cost_center="Main - C",
                posting_date=date.fromisoformat("2026-04-15"),
            )

        self.assertEqual(str(row.event_key), expected_event_key)
        self.assertNotIn("manual-pay-1", str(row.event_key))
        self.assertNotIn("manual-pay-2", str(row.event_key))

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_integrity_conflict_reloads_existing_active_outbox(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-race-create")

        first = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-race-1", posting_date="2026-04-15"),
        )
        self.assertEqual(first.status_code, 200)
        first_outbox_id = int(first.json()["data"]["payable_outbox_id"])

        original_find_active = FactoryStatementPayableOutboxService.find_active_by_statement
        call_count = {"n": 0}

        def _fake_find_active(self, *, statement_id: int):  # type: ignore[override]
            call_count["n"] += 1
            if call_count["n"] == 1:
                return None
            return original_find_active(self, statement_id=statement_id)

        with patch.object(
            FactoryStatementPayableOutboxService,
            "find_active_by_statement",
            new=_fake_find_active,
        ), patch.object(
            FactoryStatementPayableOutboxService,
            "create_outbox",
            side_effect=IntegrityError("simulated", params=None, orig=Exception("uk_ly_factory_statement_payable_one_active")),
        ):
            conflict = self.client.post(
                f"/api/factory-statements/{statement_id}/payable-draft",
                headers=self._headers(),
                json=self._payable_payload(idempotency_key="idem-payable-race-2", posting_date="2026-04-15"),
            )

        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE")
        self.assertEqual(int(conflict.json()["data"]["existing_outbox_id"]), first_outbox_id)
        self.assertNotEqual(conflict.json()["code"], "FACTORY_STATEMENT_DATABASE_WRITE_FAILED")

    def test_draft_statement_cannot_create_payable_outbox(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-payable-draft-denied-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        response = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-draft-denied"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_INVALID_STATUS")

    def test_cancelled_statement_cannot_create_payable_outbox(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-payable-cancel-denied-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(),
            json={"idempotency_key": "idem-payable-cancel-denied-op", "reason": "cancel"},
        )
        self.assertEqual(cancelled.status_code, 200)

        response = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-cancel-denied"),
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_INVALID_STATUS")

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=False)
    def test_invalid_payable_account_fail_closed(self, _mock_account) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-account-invalid")

        response = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-account-invalid-op"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_PAYABLE_ACCOUNT_INVALID")

        with self.SessionLocal() as session:
            total = session.query(LyFactoryStatementPayableOutbox).count()
        self.assertEqual(total, 0)

    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=False)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_invalid_cost_center_fail_closed(self, _mock_account, _mock_center) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-cost-invalid")

        response = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-cost-invalid-op"),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_COST_CENTER_INVALID")

        with self.SessionLocal() as session:
            total = session.query(LyFactoryStatementPayableOutbox).count()
        self.assertEqual(total, 0)

    @patch.object(
        ERPNextPurchaseInvoiceAdapter,
        "validate_payable_account",
        side_effect=ERPNextServiceUnavailableError("erp unavailable"),
    )
    def test_erpnext_unavailable_fail_closed(self, _mock_account) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-erp-down")

        response = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-erp-down-op"),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE")

        with self.SessionLocal() as session:
            total = session.query(LyFactoryStatementPayableOutbox).count()
        self.assertEqual(total, 0)

    @patch.object(ERPNextPurchaseInvoiceAdapter, "create_purchase_invoice_draft", side_effect=AssertionError("must not call"))
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_cost_center", return_value=True)
    @patch.object(ERPNextPurchaseInvoiceAdapter, "validate_payable_account", return_value=True)
    def test_payable_draft_endpoint_never_creates_purchase_invoice_directly(
        self,
        _mock_account,
        _mock_center,
        _mock_create,
    ) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-no-direct-pi")

        response = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(),
            json=self._payable_payload(idempotency_key="idem-payable-no-direct-pi-op"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")

    def test_no_payable_create_permission_returns_403(self) -> None:
        statement_id = self._create_and_confirm_statement(idempotency_key="idem-payable-perm-denied")

        denied = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(role="Viewer"),
            json=self._payable_payload(idempotency_key="idem-payable-perm-denied-op"),
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")


if __name__ == "__main__":
    unittest.main()
