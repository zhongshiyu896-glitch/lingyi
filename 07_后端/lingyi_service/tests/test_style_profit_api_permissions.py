"""Permission and security-audit tests for style-profit APIs (TASK-005E1)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.core.exceptions import PermissionSourceUnavailable
from app.models.audit import LySecurityAuditLog
from app.services.erpnext_permission_adapter import ERPNextPermissionAdapter
from app.services.erpnext_permission_adapter import UserPermissionResult
from tests.test_style_profit_api import StyleProfitApiBase


class StyleProfitApiPermissionTest(StyleProfitApiBase):
    """Validate authn/authz and fail-closed permission behavior."""

    def test_style_profit_actions_matrix_excludes_cost_gate_actions(self) -> None:
        forbidden_actions = {
            "cost:diagnostic",
            "cost:dry_run",
            "cost:adjustment_draft",
            "style_profit:diagnostic",
            "style_profit:dry_run",
            "style_profit:adjustment_draft",
        }
        for role in ("System Manager", "Finance Manager", "Production Manager", "Sales Manager", "Viewer"):
            with self.subTest(role=role):
                response = self.client.get(
                    "/api/auth/actions",
                    params={"module": "style_profit"},
                    headers=self._headers(role=role),
                )
                self.assertEqual(response.status_code, 200)
                actions = set(response.json()["data"]["actions"])
                self.assertTrue(forbidden_actions.isdisjoint(actions))

    def test_style_profit_actions_matrix_static(self) -> None:
        expected = {
            "System Manager": {"style_profit:read", "style_profit:snapshot_create"},
            "Finance Manager": {"style_profit:read", "style_profit:snapshot_create"},
            "Production Manager": {"style_profit:read"},
            "Sales Manager": {"style_profit:read"},
            "Viewer": set(),
        }
        for role, expected_actions in expected.items():
            with self.subTest(role=role):
                response = self.client.get(
                    "/api/auth/actions",
                    params={"module": "style_profit"},
                    headers=self._headers(role=role),
                )
                self.assertEqual(response.status_code, 200)
                data = response.json()["data"]
                self.assertEqual(set(data["actions"]), expected_actions)
                self.assertEqual(bool(data["button_permissions"]["read"]), "style_profit:read" in expected_actions)
                self.assertEqual(
                    bool(data["button_permissions"]["snapshot_create"]),
                    "style_profit:snapshot_create" in expected_actions,
                )

    def test_style_profit_actions_matrix_erp_role_aggregation(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        expected = {
            "System Manager": {"style_profit:read", "style_profit:snapshot_create"},
            "Finance Manager": {"style_profit:read", "style_profit:snapshot_create"},
            "Production Manager": {"style_profit:read"},
            "Sales Manager": {"style_profit:read"},
            "Viewer": set(),
        }
        for role, expected_actions in expected.items():
            with self.subTest(role=role), patch.object(ERPNextPermissionAdapter, "get_user_roles", return_value=[role]), patch.object(
                ERPNextPermissionAdapter,
                "get_user_permissions",
                return_value=UserPermissionResult(
                    source_available=True,
                    unrestricted=True,
                    allowed_items=set(),
                    allowed_companies=set(),
                ),
            ):
                response = self.client.get(
                    "/api/auth/actions",
                    params={"module": "style_profit"},
                    headers=self._headers(role=role),
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.json()["data"]["actions"]), expected_actions)

    def test_unauthorized_returns_401_and_security_audit(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots",
            params={"company": "COMP-A", "item_code": "STYLE-A"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "AUTH_UNAUTHORIZED")

        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.module, "style_profit")
            self.assertEqual(row.event_type, "AUTH_UNAUTHORIZED")

    def test_forbidden_action_returns_403_and_security_audit(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots",
            params={"company": "COMP-A", "item_code": "STYLE-A"},
            headers=self._headers(role="Viewer"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

        with self.SessionLocal() as session:
            row = session.query(LySecurityAuditLog).order_by(LySecurityAuditLog.id.desc()).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.module, "style_profit")
            self.assertEqual(row.event_type, "AUTH_FORBIDDEN")

    def test_forbidden_read_takes_precedence_over_list_validation(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots",
            headers=self._headers(role="Viewer"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_forbidden_create_takes_precedence_over_client_source_forbidden(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-PERM-001",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "idem-perm-create-forbidden",
            "sales_order_rows": [{"name": "hack"}],
        }
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(role="Production Manager"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_forbidden_create_takes_precedence_over_invalid_idempotency(self) -> None:
        payload = {
            "company": "COMP-A",
            "item_code": "STYLE-A",
            "sales_order": "SO-PERM-002",
            "from_date": "2026-04-01",
            "to_date": "2026-04-30",
            "revenue_mode": "actual_first",
            "include_provisional_subcontract": False,
            "formula_version": "STYLE_PROFIT_V1",
            "idempotency_key": "x" * 129,
        }
        response = self.client.post(
            "/api/reports/style-profit/snapshots",
            json=payload,
            headers=self._headers(role="Sales Manager"),
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_detail_forbidden_hides_snapshot_existence(self) -> None:
        existing_response = self.client.get(
            "/api/reports/style-profit/snapshots/1",
            headers=self._headers(role="Viewer"),
        )
        missing_response = self.client.get(
            "/api/reports/style-profit/snapshots/999999",
            headers=self._headers(role="Viewer"),
        )

        self.assertEqual(existing_response.status_code, 403)
        self.assertEqual(missing_response.status_code, 403)
        self.assertEqual(existing_response.json(), missing_response.json())
        self.assertEqual(existing_response.json()["code"], "AUTH_FORBIDDEN")

        with self.SessionLocal() as session:
            rows = (
                session.query(LySecurityAuditLog)
                .filter(
                    LySecurityAuditLog.module == "style_profit",
                    LySecurityAuditLog.event_type == "AUTH_FORBIDDEN",
                    LySecurityAuditLog.action == "style_profit:read",
                )
                .order_by(LySecurityAuditLog.id.desc())
                .limit(2)
                .all()
            )
            self.assertEqual(len(rows), 2)

    def test_detail_not_found_for_authorized_reader(self) -> None:
        response = self.client.get(
            "/api/reports/style-profit/snapshots/999999",
            headers=self._headers(role="Finance Manager"),
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "STYLE_PROFIT_NOT_FOUND")

    def test_resource_scope_forbidden_returns_403(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(ERPNextPermissionAdapter, "get_user_roles", return_value=["System Manager"]), patch.object(
            ERPNextPermissionAdapter,
            "get_user_permissions",
            return_value=UserPermissionResult(
                source_available=True,
                unrestricted=False,
                allowed_items={"STYLE-B"},
                allowed_companies={"COMP-B"},
            ),
        ):
            response = self.client.get(
                "/api/reports/style-profit/snapshots",
                params={"company": "COMP-A", "item_code": "STYLE-A"},
                headers=self._headers(role="System Manager"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "AUTH_FORBIDDEN")

    def test_permission_source_unavailable_returns_503(self) -> None:
        os.environ["LINGYI_PERMISSION_SOURCE"] = "erpnext"
        with patch.object(
            ERPNextPermissionAdapter,
            "get_user_roles",
            side_effect=PermissionSourceUnavailable(
                message="permission source unavailable",
                exception_type="TimeoutError",
                exception_message="timeout",
            ),
        ):
            response = self.client.get(
                "/api/reports/style-profit/snapshots",
                params={"company": "COMP-A", "item_code": "STYLE-A"},
                headers=self._headers(role="System Manager"),
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "PERMISSION_SOURCE_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
