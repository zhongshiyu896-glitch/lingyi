"""Sales/inventory read-only aggregation service (TASK-011B)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.schemas.sales_inventory import CustomerItem
from app.schemas.sales_inventory import InventoryAggregationData
from app.schemas.sales_inventory import InventoryAggregationItem
from app.schemas.sales_inventory import SalesInventoryListData
from app.schemas.sales_inventory import SalesOrderDetailData
from app.schemas.sales_inventory import SalesOrderFulfillmentData
from app.schemas.sales_inventory import SalesOrderFulfillmentItem
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

    BIN_FIELDS = [
        "item_code",
        "warehouse",
        "actual_qty",
        "ordered_qty",
        "indented_qty",
        "safety_stock",
        "reorder_level",
    ]

    def __init__(self, adapter: ERPNextSalesInventoryAdapter):
        self.adapter = adapter

    def list_sales_orders(
        self,
        *,
        company: str | None,
        customer: str | None,
        item_code: str | None,
        item_name: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[SalesOrderListItem]:
        rows, total = self.adapter.list_sales_orders(
            company=company,
            customer=customer,
            item_code=item_code,
            item_name=item_name,
            from_date=from_date,
            to_date=to_date,
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
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> StockLedgerData:
        rows, total, dropped_count = self.adapter.list_stock_ledger(
            item_code=item_code,
            company=company,
            warehouse=warehouse,
            from_date=from_date,
            to_date=to_date,
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

    def get_inventory_aggregation(
        self,
        *,
        company: str | None,
        item_code: str | None,
        warehouse: str | None,
    ) -> InventoryAggregationData:
        allowed_warehouses = self._allowed_warehouses(company=company)
        rows = self._list_bin_rows(item_code=item_code, warehouse=warehouse)
        items: list[InventoryAggregationItem] = []
        for row in rows:
            row_item_code = self._text(row.get("item_code"))
            row_warehouse = self._text(row.get("warehouse"))
            if row_item_code is None or row_warehouse is None:
                continue
            if allowed_warehouses is not None and row_warehouse not in allowed_warehouses:
                continue
            actual_qty = self._decimal_or_zero(row.get("actual_qty"))
            ordered_qty = self._decimal_or_zero(row.get("ordered_qty"))
            indented_qty = self._decimal_or_zero(row.get("indented_qty"))
            safety_stock = self._decimal_or_zero(row.get("safety_stock"))
            reorder_level = self._decimal_or_zero(row.get("reorder_level"))
            items.append(
                InventoryAggregationItem(
                    item_code=row_item_code,
                    warehouse=row_warehouse,
                    actual_qty=actual_qty,
                    ordered_qty=ordered_qty,
                    indented_qty=indented_qty,
                    safety_stock=safety_stock,
                    reorder_level=reorder_level,
                    is_below_safety=safety_stock > Decimal("0") and actual_qty < safety_stock,
                    is_below_reorder=reorder_level > Decimal("0") and actual_qty < reorder_level,
                )
            )
        items.sort(key=lambda row: (row.item_code, row.warehouse))
        return InventoryAggregationData(
            company=company,
            item_code=item_code,
            warehouse=warehouse,
            items=items,
        )

    def get_sales_order_fulfillment(
        self,
        *,
        company: str | None,
        item_code: str | None,
        warehouse: str | None,
        item_name: str | None,
    ) -> SalesOrderFulfillmentData:
        aggregation = self.get_inventory_aggregation(company=company, item_code=item_code, warehouse=warehouse)
        actual_map = {
            (item.item_code, item.warehouse): item.actual_qty
            for item in aggregation.items
        }
        rows: list[SalesOrderFulfillmentItem] = []
        for order in self._list_sales_orders_all(company=company):
            sales_order = str(order.get("name") or "").strip()
            if not sales_order:
                continue
            detail = self.adapter.get_sales_order(name=sales_order)
            detail_company = self._text(detail.get("company"))
            for line in self._list_or_empty(detail.get("items")):
                line_item_code = self._text(line.get("item_code"))
                if line_item_code is None:
                    continue
                if item_code and line_item_code != item_code:
                    continue
                line_warehouse = self._text(line.get("warehouse"))
                if warehouse and line_warehouse != warehouse:
                    continue
                line_item_name = self._text(line.get("item_name"))
                if item_name and not self._contains_like(line_item_name, item_name):
                    continue
                ordered_qty = self._decimal_or_zero(line.get("qty"))
                actual_qty = actual_map.get((line_item_code, line_warehouse or ""), Decimal("0"))
                rows.append(
                    SalesOrderFulfillmentItem(
                        company=detail_company,
                        sales_order=sales_order,
                        item_code=line_item_code,
                        warehouse=line_warehouse,
                        ordered_qty=ordered_qty,
                        actual_qty=actual_qty,
                        fulfillment_rate=self._fulfillment_rate(actual_qty=actual_qty, ordered_qty=ordered_qty),
                    )
                )
        rows.sort(key=lambda row: (row.sales_order, row.item_code, row.warehouse or ""))
        return SalesOrderFulfillmentData(company=company, items=rows)

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

    def _allowed_warehouses(self, *, company: str | None) -> set[str] | None:
        if not company:
            return None
        rows: list[dict[str, Any]] = []
        page = 1
        page_size = 200
        while True:
            chunk, _ = self.adapter.list_warehouses(company=company, page=page, page_size=page_size)
            if not chunk:
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
            if page > 100:
                break
        return {
            warehouse_name
            for row in rows
            if (warehouse_name := self._text(row.get("name"))) is not None
        }

    def _list_bin_rows(self, *, item_code: str | None, warehouse: str | None) -> list[dict[str, Any]]:
        filters: list[list[Any]] = []
        if item_code:
            filters.append(["item_code", "=", item_code])
        if warehouse:
            filters.append(["warehouse", "=", warehouse])
        rows: list[dict[str, Any]] = []
        page = 1
        page_size = 500
        while True:
            chunk = self.adapter._list_resource(  # noqa: SLF001 - read-only adapter pagination reuse.
                doctype="Bin",
                fields=self.BIN_FIELDS,
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="item_code asc, warehouse asc",
            )
            if not chunk:
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
            if page > 100:
                break
        return rows

    def _list_sales_orders_all(self, *, company: str | None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page = 1
        page_size = 200
        while True:
            chunk, _ = self.adapter.list_sales_orders(
                company=company,
                customer=None,
                item_code=None,
                item_name=None,
                from_date=None,
                to_date=None,
                page=page,
                page_size=page_size,
            )
            if not chunk:
                break
            rows.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
            if page > 100:
                break
        return rows

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
    def _decimal_or_zero(value: Any) -> Decimal:
        if value is None or str(value).strip() == "":
            return Decimal("0")
        return Decimal(str(value))

    @staticmethod
    def _fulfillment_rate(*, actual_qty: Decimal, ordered_qty: Decimal) -> Decimal:
        if ordered_qty <= Decimal("0"):
            return Decimal("0")
        rate = actual_qty / ordered_qty
        if rate < Decimal("0"):
            return Decimal("0")
        return rate if rate <= Decimal("1") else Decimal("1")

    @staticmethod
    def _contains_like(value: str | None, keyword: str) -> bool:
        if value is None:
            return False
        return keyword.lower() in value.lower()

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
