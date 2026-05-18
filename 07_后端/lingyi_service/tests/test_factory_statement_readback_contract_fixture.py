"""Factory-statement readback contract fixture tests (TASK-Z007B-37-IMPL)."""

from __future__ import annotations

import json
from pathlib import Path
import unittest

from app.routers import factory_statement as factory_statement_router
from app.schemas.factory_statement import FactoryStatementBankDepositItem
from app.schemas.factory_statement import FactoryStatementBankLedgerItem
from app.schemas.factory_statement import FactoryStatementBankWithdrawalItem
from app.schemas.factory_statement import FactoryStatementCustomerEvaluationItem
from app.schemas.factory_statement import FactoryStatementCustomerReceivableSummaryItem
from app.schemas.factory_statement import FactoryStatementCustomerReconciliationItem
from app.schemas.factory_statement import FactoryStatementCustomerUnpaidReportItem
from app.schemas.factory_statement import FactoryStatementDetailData
from app.schemas.factory_statement import FactoryStatementExpenseReimbursementPaymentItem
from app.schemas.factory_statement import FactoryStatementFactoryEvaluationItem
from app.schemas.factory_statement import FactoryStatementFactoryPayableSummaryItem
from app.schemas.factory_statement import FactoryStatementFactoryReconciliationItem
from app.schemas.factory_statement import FactoryStatementItemData
from app.schemas.factory_statement import FactoryStatementListData
from app.schemas.factory_statement import FactoryStatementListItem
from app.schemas.factory_statement import FactoryStatementLogData
from app.schemas.factory_statement import FactoryStatementPayableOutboxData
from app.schemas.factory_statement import FactoryStatementSupplierEvaluationItem
from app.schemas.factory_statement import FactoryStatementSupplierPayableSummaryItem
from app.schemas.factory_statement import FactoryStatementSupplierReconciliationItem


FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "factory_statement_readback_contract_fixture.json"
)
WAREHOUSE_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "warehouse_adapter_contract_fixture.json"


SCHEMA_REGISTRY = {
    "FactoryStatementExpenseReimbursementPaymentItem": FactoryStatementExpenseReimbursementPaymentItem,
    "FactoryStatementBankDepositItem": FactoryStatementBankDepositItem,
    "FactoryStatementBankWithdrawalItem": FactoryStatementBankWithdrawalItem,
    "FactoryStatementBankLedgerItem": FactoryStatementBankLedgerItem,
    "FactoryStatementCustomerEvaluationItem": FactoryStatementCustomerEvaluationItem,
    "FactoryStatementCustomerReconciliationItem": FactoryStatementCustomerReconciliationItem,
    "FactoryStatementCustomerUnpaidReportItem": FactoryStatementCustomerUnpaidReportItem,
    "FactoryStatementCustomerReceivableSummaryItem": FactoryStatementCustomerReceivableSummaryItem,
    "FactoryStatementFactoryEvaluationItem": FactoryStatementFactoryEvaluationItem,
    "FactoryStatementFactoryReconciliationItem": FactoryStatementFactoryReconciliationItem,
    "FactoryStatementFactoryPayableSummaryItem": FactoryStatementFactoryPayableSummaryItem,
    "FactoryStatementSupplierEvaluationItem": FactoryStatementSupplierEvaluationItem,
    "FactoryStatementSupplierReconciliationItem": FactoryStatementSupplierReconciliationItem,
    "FactoryStatementSupplierPayableSummaryItem": FactoryStatementSupplierPayableSummaryItem,
}


def _field_names(schema_cls: type) -> set[str]:
    return set(schema_cls.model_fields.keys())


class FactoryStatementReadbackContractFixtureTest(unittest.TestCase):
    """Validate fixture-driven factory-statement readback field contracts."""

    @classmethod
    def setUpClass(cls) -> None:
        with FIXTURE_PATH.open("r", encoding="utf-8") as fp:
            cls.fixture = json.load(fp)
        with WAREHOUSE_FIXTURE_PATH.open("r", encoding="utf-8") as fp:
            cls.warehouse_fixture = json.load(fp)

        cls.get_routes = {
            route.path: route
            for route in factory_statement_router.router.routes
            if "GET" in getattr(route, "methods", set())
        }
        cls.factory_field_pool = (
            _field_names(FactoryStatementListItem)
            | _field_names(FactoryStatementDetailData)
            | _field_names(FactoryStatementItemData)
            | _field_names(FactoryStatementLogData)
            | _field_names(FactoryStatementPayableOutboxData)
            | _field_names(FactoryStatementSupplierEvaluationItem)
            | _field_names(FactoryStatementFactoryEvaluationItem)
            | _field_names(FactoryStatementCustomerEvaluationItem)
        )
        cls.warehouse_field_pool = set(
            cls.warehouse_fixture["alerts_contract_expected"]["first_item_required_fields"]
            + cls.warehouse_fixture["batches_contract_expected"]["first_item_required_fields"]
            + cls.warehouse_fixture["alerts_contract_expected"]["response_fields"]
            + cls.warehouse_fixture["batches_contract_expected"]["response_fields"]
        )

    def test_fixture_file_exists_and_json_parseable(self) -> None:
        self.assertTrue(FIXTURE_PATH.exists(), str(FIXTURE_PATH))
        self.assertIn("list_contract_expected", self.fixture)
        self.assertIn("detail_contract_expected", self.fixture)
        self.assertIn("readonly_sub_routes_contract_expected", self.fixture)
        self.assertIn("cross_module_canonical_mapping", self.fixture)

    def test_list_contract_fields_match_schema(self) -> None:
        expected = self.fixture["list_contract_expected"]
        list_data_fields = _field_names(FactoryStatementListData)
        list_item_fields = _field_names(FactoryStatementListItem)

        for field in expected["response_fields"]:
            self.assertIn(field, list_data_fields)
        for field in expected["item_required_fields"]:
            self.assertIn(field, list_item_fields)
        for field in expected["item_optional_fields"]:
            self.assertIn(field, list_item_fields)

    def test_list_detail_routes_exist_with_get_method(self) -> None:
        for path in ["/api/factory-statements/", "/api/factory-statements/{statement_id}"]:
            self.assertIn(path, self.get_routes)
            self.assertIn("GET", self.get_routes[path].methods)

    def test_detail_contract_fields_match_schema(self) -> None:
        expected = self.fixture["detail_contract_expected"]
        detail_fields = _field_names(FactoryStatementDetailData)
        item_fields = _field_names(FactoryStatementItemData)
        log_fields = _field_names(FactoryStatementLogData)
        payable_outbox_fields = _field_names(FactoryStatementPayableOutboxData)

        for field in expected["header_required_fields"]:
            self.assertIn(field, detail_fields)
        for field in expected["header_optional_fields"]:
            self.assertIn(field, detail_fields)
        for field in expected["item_required_fields"]:
            self.assertIn(field, item_fields)
        for field in expected["item_optional_fields"]:
            self.assertIn(field, item_fields)
        for field in expected["log_required_fields"]:
            self.assertIn(field, log_fields)
        for field in expected["log_optional_fields"]:
            self.assertIn(field, log_fields)
        for field in expected["payable_outbox_required_fields"]:
            self.assertIn(field, payable_outbox_fields)
        for field in expected["payable_outbox_optional_fields"]:
            self.assertIn(field, payable_outbox_fields)

    def test_readonly_sub_routes_runtime_and_schema_contract(self) -> None:
        expected = self.fixture["readonly_sub_routes_contract_expected"]
        runtime_mapping = {
            "/api/factory-statements/supplier-evaluations": FactoryStatementSupplierEvaluationItem,
            "/api/factory-statements/factory-evaluations": FactoryStatementFactoryEvaluationItem,
            "/api/factory-statements/customer-evaluations": FactoryStatementCustomerEvaluationItem,
        }

        for row in expected["runtime_routes"]:
            path = row["path"]
            self.assertIn(path, self.get_routes)
            self.assertIn("GET", self.get_routes[path].methods)
            schema_fields = _field_names(runtime_mapping[path])
            for field in row["item_required_fields"]:
                self.assertIn(field, schema_fields)

        for row in expected["schema_only_routes"]:
            path = row["path"]
            schema_name = row["item_schema"]
            self.assertIn(path, self.get_routes)
            self.assertIn("GET", self.get_routes[path].methods)
            self.assertIn(schema_name, SCHEMA_REGISTRY)
            schema_fields = _field_names(SCHEMA_REGISTRY[schema_name])
            for field in row["item_required_fields"]:
                self.assertIn(field, schema_fields)

    def test_cross_module_canonical_mapping(self) -> None:
        for row in self.fixture["cross_module_canonical_mapping"]:
            anchor = row["anchor"]
            warehouse_fields = row["warehouse_contract_fields"]
            factory_fields = row["factory_statement_contract_fields"]
            status = row["status"]

            if status.startswith("mapped"):
                for field in warehouse_fields:
                    self.assertIn(field, self.warehouse_field_pool, f"{anchor}:{field}")
                for field in factory_fields:
                    self.assertIn(field, self.factory_field_pool, f"{anchor}:{field}")
                if anchor == "style":
                    self.assertEqual(row.get("derived_from"), "item_code")
                    self.assertIn("style_code", factory_fields)
