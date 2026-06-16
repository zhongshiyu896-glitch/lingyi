"""B6 FastAPI-native factory statement payable payment flow."""

from __future__ import annotations

from decimal import Decimal
import unittest

from app.models.audit import LyOperationAuditLog
from app.models.factory_statement import LyFactoryStatementPayment
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
        self.assertEqual(Decimal(str(created.json()["data"]["outstanding_before"])), Decimal("4700.000000"))
        self.assertEqual(Decimal(str(created.json()["data"]["outstanding_after"])), Decimal("3500.000000"))
        list_row = statement_list.json()["data"]["items"][0]
        self.assertEqual(Decimal(str(list_row["paid_amount"])), Decimal("1200.000000"))
        self.assertEqual(Decimal(str(list_row["outstanding_amount"])), Decimal("3500.000000"))
        self.assertEqual(list_row["payment_status"], "partly_paid")

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
        self.assertEqual(Decimal(str(closed.json()["data"]["outstanding_after"])), Decimal("0.000000"))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(Decimal(str(detail.json()["data"]["paid_amount"])), Decimal("4700.000000"))
        self.assertEqual(Decimal(str(detail.json()["data"]["outstanding_amount"])), Decimal("0.000000"))
        self.assertEqual(detail.json()["data"]["payment_status"], "paid")
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


if __name__ == "__main__":
    unittest.main()
