"""Sales/inventory read-only aggregation service (TASK-011B)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.schemas.sales_inventory import CustomerItem
from app.schemas.sales_inventory import SalesInventoryListData
from app.schemas.sales_inventory import SalesOrderDetailData
from app.schemas.sales_inventory import SalesOrderLineItem
from app.schemas.sales_inventory import SalesOrderListItem
from app.schemas.sales_inventory import StockLedgerData
from app.schemas.sales_inventory import StockLedgerItem
from app.schemas.sales_inventory import StockSummaryData
from app.schemas.sales_inventory import StockSummaryItem
from app.schemas.sales_inventory import WarehouseItem
from app.services.erpnext_sales_inventory_adapter import ERPNextSalesInventoryAdapter


class SalesInventoryService:
    """Build API DTOs from ERPNext read-only adapter facts."""

    def __init__(self, adapter: ERPNextSalesInventoryAdapter):
        self.adapter = adapter

    def list_sales_orders(
        self,
        *,
        company: str | None,
        customer: str | None,
        item_code: str | None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[SalesOrderListItem]:
        rows, total = self.adapter.list_sales_orders(
            company=company,
            customer=customer,
            item_code=item_code,
            page=page,
            page_size=page_size,
        )
        return SalesInventoryListData[SalesOrderListItem](
            items=[self._sales_order_list_item(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_sales_order(self, *, name: str) -> SalesOrderDetailData:
        row = self.adapter.get_sales_order(name=name)
        return SalesOrderDetailData(
            name=str(row.get("name") or name),
            company=str(row.get("company") or ""),
            customer=self._text(row.get("customer")),
            transaction_date=row.get("transaction_date"),
            delivery_date=row.get("delivery_date"),
            status=self._text(row.get("status")),
            docstatus=int(row.get("docstatus")),
            grand_total=self._decimal_or_none(row.get("grand_total")),
            currency=self._text(row.get("currency")),
            items=[self._sales_order_line_item(item) for item in self._list_or_empty(row.get("items"))],
        )

    def get_stock_summary(
        self,
        *,
        item_code: str,
        company: str | None,
        warehouse: str | None,
    ) -> StockSummaryData:
        rows, dropped_count = self.adapter.get_stock_summary(item_code=item_code, company=company, warehouse=warehouse)
        return StockSummaryData(
            item_code=item_code,
            company=company,
            warehouse=warehouse,
            items=[
                StockSummaryItem(
                    company=str(row["company"]),
                    item_code=str(row["item_code"]),
                    warehouse=str(row["warehouse"]),
                    balance_qty=Decimal(str(row["balance_qty"])),
                    latest_posting_date=row.get("latest_posting_date"),
                    latest_posting_time=self._text(row.get("latest_posting_time")),
                )
                for row in rows
            ],
            dropped_count=dropped_count,
        )

    def list_stock_ledger(
        self,
        *,
        item_code: str,
        company: str | None,
        warehouse: str | None,
        page: int,
        page_size: int,
    ) -> StockLedgerData:
        rows, total, dropped_count = self.adapter.list_stock_ledger(
            item_code=item_code,
            company=company,
            warehouse=warehouse,
            page=page,
            page_size=page_size,
        )
        return StockLedgerData(
            items=[
                StockLedgerItem(
                    name=self._text(row.get("name")),
                    company=str(row["company"]),
                    item_code=str(row["item_code"]),
                    warehouse=str(row["warehouse"]),
                    posting_date=row["posting_date"],
                    posting_time=self._text(row.get("posting_time")),
                    actual_qty=Decimal(str(row["actual_qty"])),
                    qty_after_transaction=Decimal(str(row["qty_after_transaction"])),
                    voucher_type=self._text(row.get("voucher_type")),
                    voucher_no=self._text(row.get("voucher_no")),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
            dropped_count=dropped_count,
        )

    def list_warehouses(
        self,
        *,
        company: str | None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[WarehouseItem]:
        rows, total = self.adapter.list_warehouses(company=company, page=page, page_size=page_size)
        return SalesInventoryListData[WarehouseItem](
            items=[
                WarehouseItem(
                    name=str(row.get("name") or ""),
                    company=self._text(row.get("company")),
                    warehouse_name=self._text(row.get("warehouse_name")),
                    disabled=self._bool_or_none(row.get("disabled")),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def list_customers(self, *, page: int, page_size: int) -> SalesInventoryListData[CustomerItem]:
        rows, total = self.adapter.list_customers(page=page, page_size=page_size)
        return SalesInventoryListData[CustomerItem](
            items=[
                CustomerItem(
                    name=str(row.get("name") or ""),
                    customer_name=self._text(row.get("customer_name")),
                    disabled=self._bool_or_none(row.get("disabled")),
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    @classmethod
    def _sales_order_list_item(cls, row: dict[str, Any]) -> SalesOrderListItem:
        return SalesOrderListItem(
            name=str(row.get("name") or ""),
            company=str(row.get("company") or ""),
            customer=cls._text(row.get("customer")),
            transaction_date=row.get("transaction_date"),
            delivery_date=row.get("delivery_date"),
            status=cls._text(row.get("status")),
            docstatus=int(row.get("docstatus")),
            grand_total=cls._decimal_or_none(row.get("grand_total")),
            currency=cls._text(row.get("currency")),
        )

    @classmethod
    def _sales_order_line_item(cls, row: dict[str, Any]) -> SalesOrderLineItem:
        return SalesOrderLineItem(
            name=cls._text(row.get("name")),
            item_code=str(row.get("item_code") or ""),
            item_name=cls._text(row.get("item_name")),
            qty=Decimal(str(row.get("qty") or "0")),
            delivered_qty=cls._decimal_or_none(row.get("delivered_qty")),
            rate=cls._decimal_or_none(row.get("rate")),
            amount=cls._decimal_or_none(row.get("amount")),
            warehouse=cls._text(row.get("warehouse")),
            delivery_date=row.get("delivery_date"),
        )

    @staticmethod
    def _list_or_empty(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [dict(item) for item in value if isinstance(item, dict)]

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _decimal_or_none(value: Any) -> Decimal | None:
        if value is None or str(value).strip() == "":
            return None
        return Decimal(str(value))

    @staticmethod
    def _bool_or_none(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        text = str(value).strip().lower()
        if text in {"1", "true", "yes"}:
            return True
        if text in {"0", "false", "no"}:
            return False
        return None
