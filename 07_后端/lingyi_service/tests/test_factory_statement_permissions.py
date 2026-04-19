"""Permission and scope tests for factory statement APIs (TASK-006B)."""

from __future__ import annotations

from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from app.core.exceptions import PermissionSourceUnavailable
from app.models.factory_statement import LyFactoryStatementOperation
from app.models.audit import LySecurityAuditLog
from app.models.factory_statement import LyFactoryStatement
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from app.models.factory_statement import LyFactoryStatementPayableOutbox
from tests.test_factory_statement_api import FactoryStatementApiBase


class FactoryStatementPermissionTest(FactoryStatementApiBase):
    """Validate authz, resource permission and fail-closed behavior."""

    def test_no_create_permission_returns_403_and_no_write(self) -> None:
        with self.SessionLocal() as session:
            before = session.query(LyFactoryStatement).count()

        response = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Viewer"),
            json=self._create_payload(idempotency_key="idem-no-create"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

        with self.SessionLocal() as session:
            after = session.query(LyFactoryStatement).count()
        self.assertEqual(before, after)

    def test_no_supplier_resource_permission_returns_403_and_no_write(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with self.SessionLocal() as session:
            before = session.query(LyFactoryStatement).count()

        with patch.object(ERPNextPermissionAdapter, "get_user_roles", return_value=["Finance Manager"]), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=set(),
                allowed_companies={"COMP-A"},
                allowed_suppliers={"SUP-B"},
                allowed_warehouses=set(),
            ),
        ):
            response = self.client.post(
                "/api/factory-statements/",
                headers=self._headers(role="Finance Manager"),
                json=self._create_payload(idempotency_key="idem-no-supplier-scope", supplier="SUP-A"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

        with self.SessionLocal() as session:
            after = session.query(LyFactoryStatement).count()
        self.assertEqual(before, after)

    def test_permission_source_unavailable_returns_503_and_no_write(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with self.SessionLocal() as session:
            before = session.query(LyFactoryStatement).count()

        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_roles",
            side_effect=PermissionSourceUnavailable(
                message="permission source unavailable",
                exception_type="TimeoutError",
                exception_message="authorization: Bearer secret-token cookie=session secret=abc token=xyz",
            ),
        ):
            response = self.client.post(
                "/api/factory-statements/",
                headers=self._headers(role="Finance Manager"),
                json=self._create_payload(idempotency_key="idem-perm-source-down"),
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE")

        with self.SessionLocal() as session:
            after = session.query(LyFactoryStatement).count()
            log_row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
        self.assertEqual(before, after)
        self.assertIsNotNone(log_row)
        lowered = str(log_row.deny_reason or "").lower()
        self.assertNotIn("authorization", lowered)
        self.assertNotIn("cookie", lowered)
        self.assertNotIn("token", lowered)
        self.assertNotIn("secret", lowered)

    def test_list_is_filtered_by_company_supplier_resource_scope(self) -> None:
        self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Finance Manager"),
            json=self._create_payload(idempotency_key="idem-list-scope-a", supplier="SUP-A"),
        )
        self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Finance Manager"),
            json=self._create_payload(idempotency_key="idem-list-scope-b", supplier="SUP-B"),
        )

        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(ERPNextPermissionAdapter, "get_user_roles", return_value=["Finance Manager"]), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items=set(),
                allowed_companies={"COMP-A"},
                allowed_suppliers={"SUP-A"},
                allowed_warehouses=set(),
            ),
        ):
            response = self.client.get(
                "/api/factory-statements/",
                headers=self._headers(role="Finance Manager"),
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "0")
        self.assertEqual(response.json()["data"]["total"], 1)
        self.assertEqual(response.json()["data"]["items"][0]["supplier"], "SUP-A")

    def test_detail_checks_permission_before_id_lookup(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Finance Manager"),
            json=self._create_payload(idempotency_key="idem-detail-auth-order"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        existing = self.client.get(
            f"/api/factory-statements/{statement_id}",
            headers=self._headers(role="Viewer"),
        )
        missing = self.client.get(
            "/api/factory-statements/999999",
            headers=self._headers(role="Viewer"),
        )

        self.assertEqual(existing.status_code, 403)
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(existing.json(), missing.json())
        self.assertEqual(existing.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

    def test_no_confirm_permission_returns_403_and_no_write(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Finance Manager"),
            json=self._create_payload(idempotency_key="idem-no-confirm-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        denied = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(role="Viewer"),
            json={"idempotency_key": "idem-no-confirm-op", "remark": "x"},
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            op_count = (
                session.query(LyFactoryStatementOperation)
                .filter(LyFactoryStatementOperation.statement_id == statement_id)
                .count()
            )
        self.assertEqual(str(statement.statement_status), "draft")
        self.assertEqual(op_count, 0)

    def test_no_cancel_permission_returns_403_and_no_write(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Finance Manager"),
            json=self._create_payload(idempotency_key="idem-no-cancel-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        denied = self.client.post(
            f"/api/factory-statements/{statement_id}/cancel",
            headers=self._headers(role="Viewer"),
            json={"idempotency_key": "idem-no-cancel-op", "reason": "x"},
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            op_count = (
                session.query(LyFactoryStatementOperation)
                .filter(LyFactoryStatementOperation.statement_id == statement_id)
                .count()
            )
        self.assertEqual(str(statement.statement_status), "draft")
        self.assertEqual(op_count, 0)

    def test_no_payable_draft_permission_returns_403_and_no_outbox(self) -> None:
        created = self.client.post(
            "/api/factory-statements/",
            headers=self._headers(role="Finance Manager"),
            json=self._create_payload(idempotency_key="idem-no-payable-create"),
        )
        self.assertEqual(created.status_code, 200)
        statement_id = int(created.json()["data"]["statement_id"])

        confirmed = self.client.post(
            f"/api/factory-statements/{statement_id}/confirm",
            headers=self._headers(role="Finance Manager"),
            json={"idempotency_key": "idem-no-payable-confirm", "remark": "ok"},
        )
        self.assertEqual(confirmed.status_code, 200)

        denied = self.client.post(
            f"/api/factory-statements/{statement_id}/payable-draft",
            headers=self._headers(role="Viewer"),
            json={
                "idempotency_key": "idem-no-payable-draft-op",
                "payable_account": "2202.01",
                "cost_center": "CC-01",
                "posting_date": "2026-04-30",
                "remark": "x",
            },
        )
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "FACTORY_STATEMENT_PERMISSION_DENIED")

        with self.SessionLocal() as session:
            statement = session.query(LyFactoryStatement).filter(LyFactoryStatement.id == statement_id).one()
            outbox_count = (
                session.query(LyFactoryStatementPayableOutbox)
                .filter(LyFactoryStatementPayableOutbox.statement_id == statement_id)
                .count()
            )
        self.assertEqual(str(statement.statement_status), "confirmed")
        self.assertEqual(outbox_count, 0)


if __name__ == "__main__":
    unittest.main()
