"""B6 FastAPI-native factory statement payable payment flow."""

from __future__ import annotations

from decimal import Decimal
import unittest

from app.models.audit import LyOperationAuditLog
from app.models.factory_statement import LyFactoryStatementPayment
from app.models.factory_statement import LyFactoryStatementPaymentOperation
from tests.test_factory_statement_api import FactoryStatementApiBase


class FactoryStatementPaymentFlowTest(FactoryStatementApiBase):
    """Validate payments reduce local factory statement payables."""

    @classmethod
    def _payment_payload(
        cls,
        statement_data: dict[str, object],
        *,
        paid_amount: Decimal | int | str,
        payment_entry: str,
        source_ref: str,
        idempotency_key: str,
        reference_no: str,
    ) -> dict[str, object]:
        payload = cls._statement_chain_payload(statement_data)
        payload.update(
            {
                "posting_date": "2026-05-19",
                "paid_amount": str(paid_amount),
                "mode_of_payment": "Bank Transfer",
                "reference_no": cls._scoped_value(reference_no),
                "reference_date": "2026-05-19",
                "payment_entry": payment_entry,
                "source_ref": cls._scoped_value(source_ref),
                "idempotency_key": cls._scoped_value(idempotency_key),
                "operation": "create_payment_entry",
            }
        )
        return payload

    @classmethod
    def _payment_cancel_payload(
        cls,
        statement_data: dict[str, object],
        *,
        idempotency_key: str,
        reason: str = "cancel test payment",
    ) -> dict[str, object]:
        payload = cls._statement_chain_payload(statement_data)
        payload.update(
            {
                "idempotency_key": cls._scoped_value(idempotency_key),
                "reason": reason,
                "operation": "cancel_payment_entry",
            }
        )
        return payload

    def _create_confirmed_statement(self) -> dict[str, object]:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(idempotency_key="idem-b6-payment-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_data = created.json()["data"]
        statement_id = int(statement_data["statement_id"])
        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(),
            json=self._confirm_payload(
                statement_data,
                idempotency_key="idem-b6-payment-confirm",
                remark="confirm for payment",
            ),
        )
        self.assertEqual(confirmed.status_code, 200)
        return statement_data

    def _approve_payment(self, payment_id: int, *, suffix: str) -> dict[str, object]:
        created = self.client.post(
            "/api/finance/approval-tasks",
            headers=self._headers(role="System Manager", user="factory.statement.approver"),
            json={
                "operation": "create_task",
                "company": "COMP-A",
                "source_type": "factory_statement_payment",
                "source_id": payment_id,
                "idempotency_key": self._scoped_value(f"idem-b6-fsp-approval-create-{suffix}"),
                "scenario_tag": self._SCENARIO_TAG,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        task = created.json()["data"]
        approved = self.client.post(
            f"/api/finance/approval-tasks/{task['id']}/approve",
            headers=self._headers(role="System Manager", user="factory.statement.approver"),
            json={
                "operation": "approve_task",
                "company": "COMP-A",
                "idempotency_key": self._scoped_value(f"idem-b6-fsp-approval-approve-{suffix}"),
                "reason": "加工厂付款审批通过",
            },
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        data = approved.json()["data"]
        self.assertEqual(data["status"], "approved")
        self.assertEqual(data["source_status"], "submitted")
        return data

    def test_payment_replay_and_payable_readbacks(self) -> None:
        statement_data = self._create_confirmed_statement()
        statement_id = int(statement_data["statement_id"])

        first_payload = self._payment_payload(
            statement_data,
            paid_amount=1200,
            payment_entry="FSP-B6-001",
            source_ref="SRC-B6-FSP-001",
            idempotency_key="idem-b6-fsp-001",
            reference_no="BANK-B6-001",
        )
        created = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=first_payload,
        )
        replay = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=first_payload,
        )
        conflict_payload = dict(first_payload)
        conflict_payload["paid_amount"] = "1300"
        conflict = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=conflict_payload,
        )
        payment_list = self.client.get(
            "/api/factory-statements/payments",
            headers=self._headers(),
            params={"statement_no": statement_data["statement_no"]},
        )
        statement_list = self.client.get(
            "/api/factory-statements/",
            headers=self._headers(),
            params={"company": "COMP-A", "supplier": "SUP-A"},
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(created.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_PAYMENT_CONFLICT")
        self.assertEqual(payment_list.status_code, 200)
        self.assertEqual(payment_list.json()["data"]["items"][0]["payment_entry"], "FSP-B6-001")
        self.assertEqual(payment_list.json()["data"]["items"][0]["status"], "pending_approval")
        self.assertEqual(Decimal(str(created.json()["data"]["outstanding_before"])), Decimal("4700.000000"))
        self.assertEqual(Decimal(str(created.json()["data"]["outstanding_after"])), Decimal("3500.000000"))
        self.assertEqual(created.json()["data"]["financial_ledger_status"], "pending")
        self.assertEqual(created.json()["data"]["financial_ledger_status_name"], "待送审")
        self.assertEqual(Decimal(str(created.json()["data"]["financial_ledger_cash_out_amount"])), Decimal("0"))
        list_row = statement_list.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(list_row["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(list_row["outstanding_amount"])), Decimal("4700.000000"))
        self.assertEqual(list_row["payment_status"], "unpaid")
        self.assertEqual(list_row["financial_ledger_status"], "posted")
        self.assertEqual(Decimal(str(list_row["financial_ledger_payable_amount"])), Decimal("4700.000000"))

        self._approve_payment(int(created.json()["data"]["id"]), suffix="001")
        approved_list = self.client.get(
            "/api/factory-statements/",
            headers=self._headers(),
            params={"company": "COMP-A", "supplier": "SUP-A"},
        )
        approved_row = approved_list.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(approved_row["paid_amount"])), Decimal("1200.000000"))
        self.assertEqual(Decimal(str(approved_row["outstanding_amount"])), Decimal("3500.000000"))
        self.assertEqual(approved_row["payment_status"], "partly_paid")
        self.assertEqual(approved_row["financial_ledger_status"], "partial")
        self.assertEqual(Decimal(str(approved_row["financial_ledger_cash_out_amount"])), Decimal("1200.000000"))
        self.assertEqual(Decimal(str(approved_row["financial_ledger_outstanding_amount"])), Decimal("3500.000000"))

        closed = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=self._payment_payload(
                statement_data,
                paid_amount=3500,
                payment_entry="FSP-B6-002",
                source_ref="SRC-B6-FSP-002",
                idempotency_key="idem-b6-fsp-002",
                reference_no="BANK-B6-002",
            ),
        )
        detail = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )

        self.assertEqual(closed.status_code, 201)
        self.assertEqual(closed.json()["data"]["status"], "pending_approval")
        self.assertEqual(Decimal(str(closed.json()["data"]["outstanding_after"])), Decimal("0.000000"))
        self.assertEqual(closed.json()["data"]["financial_ledger_status"], "pending")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(Decimal(str(detail.json()["data"]["paid_amount"])), Decimal("1200.000000"))
        self.assertEqual(Decimal(str(detail.json()["data"]["outstanding_amount"])), Decimal("3500.000000"))
        self.assertEqual(detail.json()["data"]["payment_status"], "partly_paid")

        self._approve_payment(int(closed.json()["data"]["id"]), suffix="002")
        detail = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(Decimal(str(detail.json()["data"]["paid_amount"])), Decimal("4700.000000"))
        self.assertEqual(Decimal(str(detail.json()["data"]["outstanding_amount"])), Decimal("0.000000"))
        self.assertEqual(detail.json()["data"]["payment_status"], "paid")
        self.assertEqual(detail.json()["data"]["financial_ledger_status"], "closed")
        self.assertEqual(detail.json()["data"]["financial_ledger_status_name"], "总账已闭合")
        self.assertTrue(detail.json()["data"]["financial_ledger_closed"])
        self.assertEqual(len(detail.json()["data"]["payments"]), 2)

        with self.SessionLocal() as session:
            self.assertEqual(session.query(LyFactoryStatementPayment).count(), 2)
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("factory_statement:payment_create", audit_actions)

    def test_payment_blocks_overpayment_and_draft_status(self) -> None:
        statement_data = self._create_confirmed_statement()
        statement_id = int(statement_data["statement_id"])
        overpaid = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=self._payment_payload(
                statement_data,
                paid_amount=4701,
                payment_entry="FSP-B6-OVER",
                source_ref="SRC-B6-FSP-OVER",
                idempotency_key="idem-b6-fsp-over",
                reference_no="BANK-B6-OVER",
            ),
        )
        self.assertEqual(overpaid.status_code, 409)
        self.assertEqual(overpaid.json()["code"], "FACTORY_STATEMENT_PAYMENT_AMOUNT_EXCEEDED")

        draft = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(),
            json=self._create_payload(
                supplier="SUP-B",
                idempotency_key="idem-b6-payment-draft",
            ),
        )
        self.assertEqual(draft.status_code, 200)
        draft_data = draft.json()["data"]
        blocked = self.client.post(
            f"/api/factory-statements/{int(draft_data['statement_id'])}/payments",
            headers=self._headers(),
            json=self._payment_payload(
                draft_data,
                paid_amount=1,
                payment_entry="FSP-B6-DRAFT",
                source_ref="SRC-B6-FSP-DRAFT",
                idempotency_key="idem-b6-fsp-draft",
                reference_no="BANK-B6-DRAFT",
            ),
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["code"], "FACTORY_STATEMENT_STATUS_INVALID")

    def test_payment_cancel_reopens_payable_and_is_idempotent(self) -> None:
        statement_data = self._create_confirmed_statement()
        statement_id = int(statement_data["statement_id"])
        created = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=self._payment_payload(
                statement_data,
                paid_amount=1200,
                payment_entry="FSP-B6-CANCEL",
                source_ref="SRC-B6-FSP-CANCEL",
                idempotency_key="idem-b6-fsp-cancel-create",
                reference_no="BANK-B6-CANCEL",
            ),
        )
        self.assertEqual(created.status_code, 201)
        payment_id = int(created.json()["data"]["id"])
        self._approve_payment(payment_id, suffix="cancel")
        cancel_payload = self._payment_cancel_payload(
            statement_data,
            idempotency_key="idem-b6-fsp-cancel",
            reason="operator voids duplicate bank entry",
        )

        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/payments/{payment_id}/cancel",
            headers=self._headers(),
            json=cancel_payload,
        )
        replay = self.client.post(
            f"/api/factory-statements/{statement_id}/payments/{payment_id}/cancel",
            headers=self._headers(),
            json=cancel_payload,
        )
        mismatch_payload = dict(cancel_payload)
        mismatch_payload["reason"] = "different reason"
        conflict = self.client.post(
            f"/api/factory-statements/{statement_id}/payments/{payment_id}/cancel",
            headers=self._headers(),
            json=mismatch_payload,
        )
        statement_detail = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )
        statement_list = self.client.get(
            "/api/factory-statements/",
            headers=self._headers(),
            params={"company": "COMP-A", "supplier": "SUP-A"},
        )
        submitted_payments = self.client.get(
            "/api/factory-statements/payments",
            headers=self._headers(),
            params={"statement_no": statement_data["statement_no"], "status": "submitted"},
        )
        cancelled_payments = self.client.get(
            "/api/factory-statements/payments",
            headers=self._headers(),
            params={"statement_no": statement_data["statement_no"], "status": "cancelled"},
        )

        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled.json()["data"]["docstatus"], 2)
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["data"]["id"], payment_id)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "FACTORY_STATEMENT_PAYMENT_CONFLICT")
        self.assertEqual(statement_detail.status_code, 200)
        self.assertEqual(Decimal(str(statement_detail.json()["data"]["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(statement_detail.json()["data"]["outstanding_amount"])), Decimal("4700.000000"))
        self.assertEqual(statement_detail.json()["data"]["payment_status"], "unpaid")
        list_row = statement_list.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(list_row["paid_amount"])), Decimal("0.000000"))
        self.assertEqual(Decimal(str(list_row["outstanding_amount"])), Decimal("4700.000000"))
        self.assertEqual(list_row["payment_status"], "unpaid")
        self.assertEqual(submitted_payments.json()["data"]["total"], 0)
        self.assertEqual(cancelled_payments.json()["data"]["total"], 1)

        with self.SessionLocal() as session:
            payment = session.query(LyFactoryStatementPayment).one()
            self.assertEqual(payment.status, "cancelled")
            self.assertEqual(payment.docstatus, 2)
            self.assertEqual(session.query(LyFactoryStatementPaymentOperation).count(), 1)
            audit_actions = {row.action for row in session.query(LyOperationAuditLog).all()}
            self.assertIn("factory_statement:payment_cancel", audit_actions)

    def test_cancel_second_payment_reopens_paid_statement_to_partly_paid(self) -> None:
        statement_data = self._create_confirmed_statement()
        statement_id = int(statement_data["statement_id"])
        first_payment = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=self._payment_payload(
                statement_data,
                paid_amount=1200,
                payment_entry="FSP-B6-CLOSE-A",
                source_ref="SRC-B6-FSP-CLOSE-A",
                idempotency_key="idem-b6-fsp-close-a",
                reference_no="BANK-B6-CLOSE-A",
            ),
        )
        second_payment = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=self._payment_payload(
                statement_data,
                paid_amount=3500,
                payment_entry="FSP-B6-CLOSE-B",
                source_ref="SRC-B6-FSP-CLOSE-B",
                idempotency_key="idem-b6-fsp-close-b",
                reference_no="BANK-B6-CLOSE-B",
            ),
        )
        closed_detail = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )

        self.assertEqual(first_payment.status_code, 201, first_payment.text)
        self._approve_payment(int(first_payment.json()["data"]["id"]), suffix="close-a")
        self.assertEqual(second_payment.status_code, 201, second_payment.text)
        self.assertEqual(Decimal(str(second_payment.json()["data"]["outstanding_before"])), Decimal("3500.000000"))
        self.assertEqual(Decimal(str(second_payment.json()["data"]["outstanding_after"])), Decimal("0.000000"))
        self._approve_payment(int(second_payment.json()["data"]["id"]), suffix="close-b")
        closed_detail = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )
        self.assertEqual(closed_detail.status_code, 200, closed_detail.text)
        self.assertEqual(closed_detail.json()["data"]["payment_status"], "paid")
        self.assertEqual(Decimal(str(closed_detail.json()["data"]["paid_amount"])), Decimal("4700.000000"))
        self.assertEqual(Decimal(str(closed_detail.json()["data"]["outstanding_amount"])), Decimal("0.000000"))
        self.assertEqual(closed_detail.json()["data"]["financial_ledger_status"], "closed")

        second_payment_id = int(second_payment.json()["data"]["id"])
        cancel_payload = self._payment_cancel_payload(
            statement_data,
            idempotency_key="idem-b6-fsp-close-b-cancel",
            reason="operator voids close payment",
        )
        cancelled = self.client.post(
            f"/api/factory-statements/{statement_id}/payments/{second_payment_id}/cancel",
            headers=self._headers(),
            json=cancel_payload,
        )
        replay = self.client.post(
            f"/api/factory-statements/{statement_id}/payments/{second_payment_id}/cancel",
            headers=self._headers(),
            json=cancel_payload,
        )
        reopened_detail = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(),
        )
        statement_list = self.client.get(
            "/api/factory-statements/",
            headers=self._headers(),
            params={"company": "COMP-A", "supplier": "SUP-A"},
        )
        submitted_payments = self.client.get(
            "/api/factory-statements/payments",
            headers=self._headers(),
            params={"statement_no": statement_data["statement_no"], "status": "submitted"},
        )
        cancelled_payments = self.client.get(
            "/api/factory-statements/payments",
            headers=self._headers(),
            params={"statement_no": statement_data["statement_no"], "status": "cancelled"},
        )

        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(cancelled.json()["data"]["id"], replay.json()["data"]["id"])
        self.assertEqual(cancelled.json()["data"]["payment_entry"], "FSP-B6-CLOSE-B")
        self.assertEqual(cancelled.json()["data"]["status"], "cancelled")
        self.assertEqual(cancelled.json()["data"]["financial_ledger_status"], "cancelled")
        self.assertEqual(Decimal(str(cancelled.json()["data"]["financial_ledger_cash_out_amount"])), Decimal("0"))
        self.assertEqual(reopened_detail.status_code, 200, reopened_detail.text)
        self.assertEqual(reopened_detail.json()["data"]["payment_status"], "partly_paid")
        self.assertEqual(Decimal(str(reopened_detail.json()["data"]["paid_amount"])), Decimal("1200.000000"))
        self.assertEqual(Decimal(str(reopened_detail.json()["data"]["outstanding_amount"])), Decimal("3500.000000"))
        self.assertEqual(reopened_detail.json()["data"]["financial_ledger_status"], "partial")
        list_row = statement_list.json()["data"]["items"][0]
        self.assertEqual(list_row["payment_status"], "partly_paid")
        self.assertEqual(Decimal(str(list_row["paid_amount"])), Decimal("1200.000000"))
        self.assertEqual(Decimal(str(list_row["outstanding_amount"])), Decimal("3500.000000"))
        self.assertEqual(list_row["financial_ledger_status"], "partial")
        self.assertEqual(submitted_payments.json()["data"]["total"], 1)
        self.assertEqual(submitted_payments.json()["data"]["items"][0]["payment_entry"], "FSP-B6-CLOSE-A")
        self.assertEqual(cancelled_payments.json()["data"]["total"], 1)
        self.assertEqual(cancelled_payments.json()["data"]["items"][0]["payment_entry"], "FSP-B6-CLOSE-B")

        with self.SessionLocal() as session:
            payments = {
                row.payment_entry: row
                for row in session.query(LyFactoryStatementPayment).order_by(LyFactoryStatementPayment.payment_entry).all()
            }
            self.assertEqual(str(payments["FSP-B6-CLOSE-A"].status), "submitted")
            self.assertEqual(str(payments["FSP-B6-CLOSE-B"].status), "cancelled")
            self.assertEqual(session.query(LyFactoryStatementPaymentOperation).count(), 1)

    def test_payment_cancel_requires_permission_and_does_not_mutate(self) -> None:
        statement_data = self._create_confirmed_statement()
        statement_id = int(statement_data["statement_id"])
        created = self.client.post(
            f"/api/factory-statements/{statement_id}/payments",
            headers=self._headers(),
            json=self._payment_payload(
                statement_data,
                paid_amount=1200,
                payment_entry="FSP-B6-CANCEL-PERM",
                source_ref="SRC-B6-FSP-CANCEL-PERM",
                idempotency_key="idem-b6-fsp-cancel-perm-create",
                reference_no="BANK-B6-CANCEL-PERM",
            ),
        )
        self.assertEqual(created.status_code, 201)
        payment_id = int(created.json()["data"]["id"])
        self._approve_payment(payment_id, suffix="cancel-perm")

        denied = self.client.post(
            f"/api/factory-statements/{statement_id}/payments/{payment_id}/cancel",
            headers=self._headers(role="Viewer"),
            json=self._payment_cancel_payload(
                statement_data,
                idempotency_key="idem-b6-fsp-cancel-perm",
            ),
        )

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")
        with self.SessionLocal() as session:
            payment = session.query(LyFactoryStatementPayment).one()
            self.assertEqual(payment.status, "submitted")
            self.assertEqual(session.query(LyFactoryStatementPaymentOperation).count(), 0)


if __name__ == "__main__":
    unittest.main()
