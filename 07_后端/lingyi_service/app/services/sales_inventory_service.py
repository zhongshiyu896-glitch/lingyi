"""Sales/inventory read-only aggregation service (TASK-011B)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from app.schemas.sales_inventory import CustomerItem
from app.schemas.sales_inventory import FinishedGoodsReservedInboundData
from app.schemas.sales_inventory import FinishedGoodsReservedInboundItem
from app.schemas.sales_inventory import FinishedGoodsOtherInboundData
from app.schemas.sales_inventory import FinishedGoodsOtherInboundItem
from app.schemas.sales_inventory import FinishedGoodsShippingNoticeData
from app.schemas.sales_inventory import FinishedGoodsShippingNoticeItem
from app.schemas.sales_inventory import FinishedGoodsReportData
from app.schemas.sales_inventory import FinishedGoodsReportItem
from app.schemas.sales_inventory import InventoryMaterialRetentionReportData
from app.schemas.sales_inventory import InventoryMaterialRetentionReportItem
from app.schemas.sales_inventory import InventoryAggregationData
from app.schemas.sales_inventory import InventoryAggregationItem
from app.schemas.sales_inventory import MaterialCountData
from app.schemas.sales_inventory import MaterialCountItem
from app.schemas.sales_inventory import MaterialInventoryReportData
from app.schemas.sales_inventory import MaterialInventoryReportItem
from app.schemas.sales_inventory import MaterialTransferData
from app.schemas.sales_inventory import MaterialTransferItem
from app.schemas.sales_inventory import SalesInventoryListData
from app.schemas.sales_inventory import SalesOrderDetailData
from app.schemas.sales_inventory import SalesOrderFulfillmentData
from app.schemas.sales_inventory import SalesOrderFulfillmentItem
from app.schemas.sales_inventory import SalesOrderLineItem
from app.schemas.sales_inventory import SalesOrderListItem
from app.schemas.sales_inventory import SemiFinishedInventoryData
from app.schemas.sales_inventory import SemiFinishedInventoryItem
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
        order_no: str | None,
        keyword: str | None,
        company: str | None,
        customer: str | None,
        item_code: str | None,
        item_name: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> SalesInventoryListData[SalesOrderListItem]:
        normalized_keyword = self._text(keyword)
        normalized_order_no = self._text(order_no)
        normalized_item_name = self._text(item_name)
        adapter_item_name = normalized_item_name or normalized_keyword
        rows, total = self.adapter.list_sales_orders(
            company=company,
            customer=customer,
            item_code=item_code,
            item_name=adapter_item_name,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        filtered_rows = rows
        if normalized_order_no:
            needle = normalized_order_no.lower()
            filtered_rows = [
                row
                for row in filtered_rows
                if needle in str(row.get("name") or "").lower()
            ]
        if normalized_keyword:
            keyword_needle = normalized_keyword.lower()
            filtered_rows = [
                row
                for row in filtered_rows
                if keyword_needle in " ".join(
                    (
                        str(row.get("name") or ""),
                        str(row.get("customer") or ""),
                        str(row.get("company") or ""),
                        str(row.get("status") or ""),
                    )
                ).lower()
            ]
        return SalesInventoryListData[SalesOrderListItem](
            items=[self._sales_order_list_item(row) for row in filtered_rows],
            total=min(total, len(filtered_rows)),
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

    def get_material_transfers(
        self,
        *,
        item_code: str | None,
        keyword: str | None,
        source_warehouse: str | None,
        target_warehouse: str | None,
        status: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> MaterialTransferData:
        normalized_item_code = self._text(item_code)
        normalized_keyword = self._text(keyword)
        normalized_source_warehouse = self._text(source_warehouse)
        normalized_target_warehouse = self._text(target_warehouse)
        normalized_status = self._text(status)

        seed_rows = [
            {
                "transfer_no": "MT-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "source_warehouse": "面料主仓",
                "target_warehouse": "成品前置仓",
                "transfer_qty": Decimal("360"),
                "inbound_qty": Decimal("360"),
                "diff_qty": Decimal("0"),
                "operator": "陈晓敏",
                "status": "已完成",
                "transfer_date": date(2026, 5, 1),
                "company": "凌云服饰",
            },
            {
                "transfer_no": "MT-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "source_warehouse": "辅料主仓",
                "target_warehouse": "车缝线边仓",
                "transfer_qty": Decimal("820"),
                "inbound_qty": Decimal("780"),
                "diff_qty": Decimal("40"),
                "operator": "刘俊伟",
                "status": "调拨中",
                "transfer_date": date(2026, 5, 2),
                "company": "凌云服饰",
            },
            {
                "transfer_no": "MT-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "source_warehouse": "包材仓",
                "target_warehouse": "发货备料仓",
                "transfer_qty": Decimal("1200"),
                "inbound_qty": Decimal("0"),
                "diff_qty": Decimal("1200"),
                "operator": "张瑞",
                "status": "待确认",
                "transfer_date": date(2026, 5, 3),
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_source_warehouse and row["source_warehouse"] != normalized_source_warehouse:
                continue
            if normalized_target_warehouse and row["target_warehouse"] != normalized_target_warehouse:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["transfer_date"] < from_date:
                continue
            if to_date and row["transfer_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["transfer_no"],
                        row["material_code"],
                        row["material_name"],
                        row["source_warehouse"],
                        row["target_warehouse"],
                        row["operator"],
                        row["status"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["transfer_date"], entry["transfer_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return MaterialTransferData(
            items=[
                MaterialTransferItem(
                    transfer_no=row["transfer_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    source_warehouse=row["source_warehouse"],
                    target_warehouse=row["target_warehouse"],
                    transfer_qty=row["transfer_qty"],
                    inbound_qty=row["inbound_qty"],
                    diff_qty=row["diff_qty"],
                    operator=row["operator"],
                    status=row["status"],
                    transfer_date=row["transfer_date"],
                    warehouse=row["source_warehouse"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_material_counts(
        self,
        *,
        item_code: str | None,
        keyword: str | None,
        warehouse: str | None,
        count_status: str | None,
        review_status: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> MaterialCountData:
        normalized_item_code = self._text(item_code)
        normalized_keyword = self._text(keyword)
        normalized_warehouse = self._text(warehouse)
        normalized_count_status = self._text(count_status)
        normalized_review_status = self._text(review_status)

        seed_rows = [
            {
                "count_no": "MC-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "warehouse": "面料主仓",
                "book_qty": Decimal("1280"),
                "counted_qty": Decimal("1280"),
                "diff_qty": Decimal("0"),
                "count_status": "已完成",
                "review_status": "已复核",
                "count_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "company": "凌云服饰",
            },
            {
                "count_no": "MC-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "warehouse": "辅料主仓",
                "book_qty": Decimal("2400"),
                "counted_qty": Decimal("2386"),
                "diff_qty": Decimal("-14"),
                "count_status": "盘点中",
                "review_status": "待复核",
                "count_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "company": "凌云服饰",
            },
            {
                "count_no": "MC-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "warehouse": "包材仓",
                "book_qty": Decimal("5300"),
                "counted_qty": Decimal("0"),
                "diff_qty": Decimal("-5300"),
                "count_status": "待盘点",
                "review_status": "待送审",
                "count_date": date(2026, 5, 3),
                "owner": "张瑞",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_count_status and row["count_status"] != normalized_count_status:
                continue
            if normalized_review_status and row["review_status"] != normalized_review_status:
                continue
            if from_date and row["count_date"] < from_date:
                continue
            if to_date and row["count_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["count_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["owner"],
                        row["count_status"],
                        row["review_status"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["count_date"], entry["count_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return MaterialCountData(
            items=[
                MaterialCountItem(
                    count_no=row["count_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    book_qty=row["book_qty"],
                    counted_qty=row["counted_qty"],
                    diff_qty=row["diff_qty"],
                    count_status=row["count_status"],
                    review_status=row["review_status"],
                    count_date=row["count_date"],
                    owner=row["owner"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_material_inventory_report(
        self,
        *,
        report_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        business_type: str | None,
        status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> MaterialInventoryReportData:
        normalized_report_no = self._text(report_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_business_type = self._text(business_type)
        normalized_status = self._text(status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "report_no": "MIR-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "warehouse": "面料主仓",
                "business_type": "采购入仓",
                "in_qty": Decimal("820"),
                "out_qty": Decimal("120"),
                "balance_qty": Decimal("700"),
                "status": "已完成",
                "biz_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "ref_no": "PR-2026-0501",
                "company": "凌云服饰",
            },
            {
                "report_no": "MIR-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "warehouse": "辅料主仓",
                "business_type": "销售出仓",
                "in_qty": Decimal("0"),
                "out_qty": Decimal("460"),
                "balance_qty": Decimal("1940"),
                "status": "执行中",
                "biz_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "ref_no": "SO-2026-0418",
                "company": "凌云服饰",
            },
            {
                "report_no": "MIR-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "warehouse": "包材仓",
                "business_type": "盘点调整",
                "in_qty": Decimal("110"),
                "out_qty": Decimal("0"),
                "balance_qty": Decimal("5410"),
                "status": "待复核",
                "biz_date": date(2026, 5, 3),
                "owner": "张瑞",
                "ref_no": "MC-2026-0503",
                "company": "凌云服饰",
            },
            {
                "report_no": "MIR-2026-0504",
                "material_code": "MAT-PRO-088",
                "material_name": "压胶衬条",
                "warehouse": "加工备料仓",
                "business_type": "调仓入仓",
                "in_qty": Decimal("300"),
                "out_qty": Decimal("40"),
                "balance_qty": Decimal("260"),
                "status": "已完成",
                "biz_date": date(2026, 5, 4),
                "owner": "邓雅琪",
                "ref_no": "MT-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_report_no and row["report_no"] != normalized_report_no:
                continue
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_business_type and row["business_type"] != normalized_business_type:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["biz_date"] < from_date:
                continue
            if to_date and row["biz_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["report_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["business_type"],
                        row["status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["biz_date"], entry["report_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return MaterialInventoryReportData(
            items=[
                MaterialInventoryReportItem(
                    report_no=row["report_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    business_type=row["business_type"],
                    in_qty=row["in_qty"],
                    out_qty=row["out_qty"],
                    balance_qty=row["balance_qty"],
                    status=row["status"],
                    biz_date=row["biz_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_inventory_material_retention_report(
        self,
        *,
        report_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        retention_level: str | None,
        status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> InventoryMaterialRetentionReportData:
        normalized_report_no = self._text(report_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_retention_level = self._text(retention_level)
        normalized_status = self._text(status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "report_no": "IMR-2026-0501",
                "material_code": "MAT-COT-001",
                "material_name": "精梳棉布",
                "warehouse": "面料主仓",
                "retention_level": "高滞留",
                "retention_days": Decimal("95"),
                "current_qty": Decimal("1260"),
                "stagnant_qty": Decimal("420"),
                "turnover_days": Decimal("58"),
                "status": "待处理",
                "biz_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "ref_no": "STL-2026-0501",
                "company": "凌云服饰",
            },
            {
                "report_no": "IMR-2026-0502",
                "material_code": "MAT-ACC-014",
                "material_name": "隐形拉链",
                "warehouse": "辅料主仓",
                "retention_level": "中滞留",
                "retention_days": Decimal("61"),
                "current_qty": Decimal("2386"),
                "stagnant_qty": Decimal("310"),
                "turnover_days": Decimal("37"),
                "status": "跟进中",
                "biz_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "ref_no": "STL-2026-0502",
                "company": "凌云服饰",
            },
            {
                "report_no": "IMR-2026-0503",
                "material_code": "MAT-PKG-031",
                "material_name": "吊牌纸卡",
                "warehouse": "包材仓",
                "retention_level": "低滞留",
                "retention_days": Decimal("32"),
                "current_qty": Decimal("5410"),
                "stagnant_qty": Decimal("160"),
                "turnover_days": Decimal("22"),
                "status": "已完成",
                "biz_date": date(2026, 5, 3),
                "owner": "张瑞",
                "ref_no": "STL-2026-0503",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_report_no and row["report_no"] != normalized_report_no:
                continue
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_retention_level and row["retention_level"] != normalized_retention_level:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["biz_date"] < from_date:
                continue
            if to_date and row["biz_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["report_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["retention_level"],
                        row["status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["biz_date"], entry["report_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return InventoryMaterialRetentionReportData(
            items=[
                InventoryMaterialRetentionReportItem(
                    report_no=row["report_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    retention_level=row["retention_level"],
                    retention_days=row["retention_days"],
                    current_qty=row["current_qty"],
                    stagnant_qty=row["stagnant_qty"],
                    turnover_days=row["turnover_days"],
                    status=row["status"],
                    biz_date=row["biz_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_semi_finished_inventory(
        self,
        *,
        record_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        process_stage: str | None,
        status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> SemiFinishedInventoryData:
        normalized_record_no = self._text(record_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_process_stage = self._text(process_stage)
        normalized_status = self._text(status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "record_no": "SFI-2026-0501",
                "material_code": "SF-TSHIRT-001",
                "material_name": "半成品T恤衣身",
                "warehouse": "半成品A仓",
                "process_stage": "车缝完成",
                "opening_qty": Decimal("260"),
                "in_qty": Decimal("140"),
                "out_qty": Decimal("120"),
                "closing_qty": Decimal("280"),
                "status": "在库",
                "biz_date": date(2026, 5, 1),
                "owner": "陈晓敏",
                "ref_no": "WIP-2026-0501",
                "company": "凌云服饰",
            },
            {
                "record_no": "SFI-2026-0502",
                "material_code": "SF-JACKET-014",
                "material_name": "半成品夹克前片",
                "warehouse": "半成品B仓",
                "process_stage": "锁边完成",
                "opening_qty": Decimal("180"),
                "in_qty": Decimal("90"),
                "out_qty": Decimal("70"),
                "closing_qty": Decimal("200"),
                "status": "在库",
                "biz_date": date(2026, 5, 2),
                "owner": "刘俊伟",
                "ref_no": "WIP-2026-0502",
                "company": "凌云服饰",
            },
            {
                "record_no": "SFI-2026-0503",
                "material_code": "SF-DRESS-031",
                "material_name": "半成品连衣裙裙摆",
                "warehouse": "半成品A仓",
                "process_stage": "整烫待检",
                "opening_qty": Decimal("120"),
                "in_qty": Decimal("60"),
                "out_qty": Decimal("30"),
                "closing_qty": Decimal("150"),
                "status": "待质检",
                "biz_date": date(2026, 5, 3),
                "owner": "张瑞",
                "ref_no": "WIP-2026-0503",
                "company": "凌云服饰",
            },
            {
                "record_no": "SFI-2026-0504",
                "material_code": "SF-PANTS-052",
                "material_name": "半成品休闲裤裤腿",
                "warehouse": "半成品C仓",
                "process_stage": "返修处理中",
                "opening_qty": Decimal("96"),
                "in_qty": Decimal("20"),
                "out_qty": Decimal("18"),
                "closing_qty": Decimal("98"),
                "status": "返修中",
                "biz_date": date(2026, 5, 4),
                "owner": "邓雅琪",
                "ref_no": "WIP-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_record_no and row["record_no"] != normalized_record_no:
                continue
            if normalized_item_code and row["material_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_process_stage and row["process_stage"] != normalized_process_stage:
                continue
            if normalized_status and row["status"] != normalized_status:
                continue
            if from_date and row["biz_date"] < from_date:
                continue
            if to_date and row["biz_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["record_no"],
                        row["material_code"],
                        row["material_name"],
                        row["warehouse"],
                        row["process_stage"],
                        row["status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["biz_date"], entry["record_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return SemiFinishedInventoryData(
            items=[
                SemiFinishedInventoryItem(
                    record_no=row["record_no"],
                    material_code=row["material_code"],
                    material_name=row["material_name"],
                    warehouse=row["warehouse"],
                    process_stage=row["process_stage"],
                    opening_qty=row["opening_qty"],
                    in_qty=row["in_qty"],
                    out_qty=row["out_qty"],
                    closing_qty=row["closing_qty"],
                    status=row["status"],
                    biz_date=row["biz_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_reserved_inbound(
        self,
        *,
        reservation_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        reserve_status: str | None,
        inbound_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsReservedInboundData:
        normalized_reservation_no = self._text(reservation_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_reserve_status = self._text(reserve_status)
        normalized_inbound_status = self._text(inbound_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "reservation_no": "FGRI-2026-0501",
                "item_code": "FG-TSHIRT-001",
                "item_name": "圆领短袖T恤成品",
                "warehouse": "成品预约A仓",
                "reserve_qty": Decimal("360"),
                "inbound_qty": Decimal("0"),
                "pending_inbound_qty": Decimal("360"),
                "reserve_status": "已预约",
                "inbound_status": "待入仓",
                "reserved_date": date(2026, 5, 1),
                "expected_inbound_date": date(2026, 5, 6),
                "owner": "李佳琳",
                "ref_no": "RSV-2026-0501",
                "company": "凌云服饰",
            },
            {
                "reservation_no": "FGRI-2026-0502",
                "item_code": "FG-JACKET-014",
                "item_name": "机能夹克成品",
                "warehouse": "成品预约B仓",
                "reserve_qty": Decimal("180"),
                "inbound_qty": Decimal("60"),
                "pending_inbound_qty": Decimal("120"),
                "reserve_status": "部分入仓",
                "inbound_status": "入仓中",
                "reserved_date": date(2026, 5, 2),
                "expected_inbound_date": date(2026, 5, 8),
                "owner": "周晨",
                "ref_no": "RSV-2026-0502",
                "company": "凌云服饰",
            },
            {
                "reservation_no": "FGRI-2026-0503",
                "item_code": "FG-DRESS-031",
                "item_name": "碎花连衣裙成品",
                "warehouse": "成品预约A仓",
                "reserve_qty": Decimal("240"),
                "inbound_qty": Decimal("240"),
                "pending_inbound_qty": Decimal("0"),
                "reserve_status": "已入仓",
                "inbound_status": "已完成",
                "reserved_date": date(2026, 5, 3),
                "expected_inbound_date": date(2026, 5, 9),
                "owner": "吴静怡",
                "ref_no": "RSV-2026-0503",
                "company": "凌云服饰",
            },
            {
                "reservation_no": "FGRI-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品预约C仓",
                "reserve_qty": Decimal("150"),
                "inbound_qty": Decimal("0"),
                "pending_inbound_qty": Decimal("150"),
                "reserve_status": "待确认",
                "inbound_status": "未开始",
                "reserved_date": date(2026, 5, 4),
                "expected_inbound_date": date(2026, 5, 12),
                "owner": "邵伟",
                "ref_no": "RSV-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_reservation_no and row["reservation_no"] != normalized_reservation_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_reserve_status and row["reserve_status"] != normalized_reserve_status:
                continue
            if normalized_inbound_status and row["inbound_status"] != normalized_inbound_status:
                continue
            if from_date and row["reserved_date"] < from_date:
                continue
            if to_date and row["reserved_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["reservation_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["reserve_status"],
                        row["inbound_status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["reserved_date"], entry["reservation_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsReservedInboundData(
            items=[
                FinishedGoodsReservedInboundItem(
                    reservation_no=row["reservation_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    reserve_qty=row["reserve_qty"],
                    inbound_qty=row["inbound_qty"],
                    pending_inbound_qty=row["pending_inbound_qty"],
                    reserve_status=row["reserve_status"],
                    inbound_status=row["inbound_status"],
                    reserved_date=row["reserved_date"],
                    expected_inbound_date=row["expected_inbound_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_shipping_notices(
        self,
        *,
        notice_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        notice_status: str | None,
        logistics_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsShippingNoticeData:
        normalized_notice_no = self._text(notice_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_notice_status = self._text(notice_status)
        normalized_logistics_status = self._text(logistics_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "notice_no": "FGSN-2026-0501",
                "item_code": "FG-TSHIRT-001",
                "item_name": "圆领短袖T恤成品",
                "warehouse": "成品主仓",
                "planned_ship_qty": Decimal("360"),
                "shipped_qty": Decimal("120"),
                "pending_ship_qty": Decimal("240"),
                "notice_status": "已下发",
                "logistics_status": "待揽收",
                "notice_date": date(2026, 5, 1),
                "expected_delivery_date": date(2026, 5, 6),
                "owner": "李佳琳",
                "ref_no": "SO-2026-0401",
                "company": "凌云服饰",
            },
            {
                "notice_no": "FGSN-2026-0502",
                "item_code": "FG-JACKET-014",
                "item_name": "机能夹克成品",
                "warehouse": "成品发货A仓",
                "planned_ship_qty": Decimal("180"),
                "shipped_qty": Decimal("180"),
                "pending_ship_qty": Decimal("0"),
                "notice_status": "已完成",
                "logistics_status": "运输中",
                "notice_date": date(2026, 5, 2),
                "expected_delivery_date": date(2026, 5, 7),
                "owner": "周晨",
                "ref_no": "SO-2026-0402",
                "company": "凌云服饰",
            },
            {
                "notice_no": "FGSN-2026-0503",
                "item_code": "FG-DRESS-031",
                "item_name": "碎花连衣裙成品",
                "warehouse": "成品发货B仓",
                "planned_ship_qty": Decimal("240"),
                "shipped_qty": Decimal("0"),
                "pending_ship_qty": Decimal("240"),
                "notice_status": "待确认",
                "logistics_status": "未开始",
                "notice_date": date(2026, 5, 3),
                "expected_delivery_date": date(2026, 5, 9),
                "owner": "吴静怡",
                "ref_no": "SO-2026-0403",
                "company": "凌云服饰",
            },
            {
                "notice_no": "FGSN-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品主仓",
                "planned_ship_qty": Decimal("150"),
                "shipped_qty": Decimal("60"),
                "pending_ship_qty": Decimal("90"),
                "notice_status": "部分发货",
                "logistics_status": "待揽收",
                "notice_date": date(2026, 5, 4),
                "expected_delivery_date": date(2026, 5, 10),
                "owner": "邵伟",
                "ref_no": "SO-2026-0404",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_notice_no and row["notice_no"] != normalized_notice_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_notice_status and row["notice_status"] != normalized_notice_status:
                continue
            if normalized_logistics_status and row["logistics_status"] != normalized_logistics_status:
                continue
            if from_date and row["notice_date"] < from_date:
                continue
            if to_date and row["notice_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["notice_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["notice_status"],
                        row["logistics_status"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["notice_date"], entry["notice_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsShippingNoticeData(
            items=[
                FinishedGoodsShippingNoticeItem(
                    notice_no=row["notice_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    planned_ship_qty=row["planned_ship_qty"],
                    shipped_qty=row["shipped_qty"],
                    pending_ship_qty=row["pending_ship_qty"],
                    notice_status=row["notice_status"],
                    logistics_status=row["logistics_status"],
                    notice_date=row["notice_date"],
                    expected_delivery_date=row["expected_delivery_date"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_other_inbound(
        self,
        *,
        inbound_no: str | None,
        item_code: str | None,
        warehouse: str | None,
        inbound_status: str | None,
        settlement_status: str | None,
        keyword: str | None,
        from_date: date | None,
        to_date: date | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsOtherInboundData:
        normalized_inbound_no = self._text(inbound_no)
        normalized_item_code = self._text(item_code)
        normalized_warehouse = self._text(warehouse)
        normalized_inbound_status = self._text(inbound_status)
        normalized_settlement_status = self._text(settlement_status)
        normalized_keyword = self._text(keyword)

        seed_rows = [
            {
                "inbound_no": "FGOI-2026-0501",
                "item_code": "FG-HOODIE-101",
                "item_name": "连帽卫衣成品",
                "warehouse": "成品其他入仓A仓",
                "planned_inbound_qty": Decimal("320"),
                "actual_inbound_qty": Decimal("200"),
                "pending_inbound_qty": Decimal("120"),
                "inbound_status": "入仓中",
                "settlement_status": "待核销",
                "inbound_date": date(2026, 5, 1),
                "source_doc_no": "OI-SRC-2026-0501",
                "owner": "李佳琳",
                "ref_no": "STK-OTH-2026-0501",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "FGOI-2026-0502",
                "item_code": "FG-TRENCH-205",
                "item_name": "风衣成品",
                "warehouse": "成品其他入仓B仓",
                "planned_inbound_qty": Decimal("180"),
                "actual_inbound_qty": Decimal("180"),
                "pending_inbound_qty": Decimal("0"),
                "inbound_status": "已完成",
                "settlement_status": "已核销",
                "inbound_date": date(2026, 5, 2),
                "source_doc_no": "OI-SRC-2026-0502",
                "owner": "周晨",
                "ref_no": "STK-OTH-2026-0502",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "FGOI-2026-0503",
                "item_code": "FG-SKIRT-318",
                "item_name": "百褶半裙成品",
                "warehouse": "成品其他入仓A仓",
                "planned_inbound_qty": Decimal("260"),
                "actual_inbound_qty": Decimal("0"),
                "pending_inbound_qty": Decimal("260"),
                "inbound_status": "待确认",
                "settlement_status": "未开始",
                "inbound_date": date(2026, 5, 3),
                "source_doc_no": "OI-SRC-2026-0503",
                "owner": "吴静怡",
                "ref_no": "STK-OTH-2026-0503",
                "company": "凌云服饰",
            },
            {
                "inbound_no": "FGOI-2026-0504",
                "item_code": "FG-PANTS-052",
                "item_name": "休闲长裤成品",
                "warehouse": "成品其他入仓C仓",
                "planned_inbound_qty": Decimal("150"),
                "actual_inbound_qty": Decimal("60"),
                "pending_inbound_qty": Decimal("90"),
                "inbound_status": "部分入仓",
                "settlement_status": "核销中",
                "inbound_date": date(2026, 5, 4),
                "source_doc_no": "OI-SRC-2026-0504",
                "owner": "邵伟",
                "ref_no": "STK-OTH-2026-0504",
                "company": "凌云服饰",
            },
        ]

        filtered_rows = []
        for row in seed_rows:
            if normalized_inbound_no and row["inbound_no"] != normalized_inbound_no:
                continue
            if normalized_item_code and row["item_code"] != normalized_item_code:
                continue
            if normalized_warehouse and row["warehouse"] != normalized_warehouse:
                continue
            if normalized_inbound_status and row["inbound_status"] != normalized_inbound_status:
                continue
            if normalized_settlement_status and row["settlement_status"] != normalized_settlement_status:
                continue
            if from_date and row["inbound_date"] < from_date:
                continue
            if to_date and row["inbound_date"] > to_date:
                continue
            if normalized_keyword:
                haystack = " ".join(
                    [
                        row["inbound_no"],
                        row["item_code"],
                        row["item_name"],
                        row["warehouse"],
                        row["inbound_status"],
                        row["settlement_status"],
                        row["source_doc_no"],
                        row["owner"],
                        row["ref_no"],
                    ]
                )
                if not self._contains_like(haystack, normalized_keyword):
                    continue
            filtered_rows.append(row)

        filtered_rows.sort(key=lambda entry: (entry["inbound_date"], entry["inbound_no"]), reverse=True)
        total = len(filtered_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_rows = filtered_rows[start:end]

        return FinishedGoodsOtherInboundData(
            items=[
                FinishedGoodsOtherInboundItem(
                    inbound_no=row["inbound_no"],
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    warehouse=row["warehouse"],
                    planned_inbound_qty=row["planned_inbound_qty"],
                    actual_inbound_qty=row["actual_inbound_qty"],
                    pending_inbound_qty=row["pending_inbound_qty"],
                    inbound_status=row["inbound_status"],
                    settlement_status=row["settlement_status"],
                    inbound_date=row["inbound_date"],
                    source_doc_no=row["source_doc_no"],
                    owner=row["owner"],
                    ref_no=row["ref_no"],
                    company=row["company"],
                )
                for row in paged_rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_finished_goods_report(
        self,
        *,
        no: str | None,
        style: str | None,
        warehouse: str | None,
        from_date: date | None,
        to_date: date | None,
        keyword: str | None,
        page: int,
        page_size: int,
    ) -> FinishedGoodsReportData:
        normalized_no = self._text(no)
        normalized_style = self._text(style)
        normalized_keyword = self._text(keyword)
        rows, _ = self.adapter.list_sales_orders(
            company=None,
            customer=None,
            item_code=None,
            item_name=normalized_style or normalized_keyword,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        report_rows: list[FinishedGoodsReportItem] = []
        for order in rows:
            order_no = str(order.get("name") or "").strip()
            if not order_no:
                continue
            order_company = self._text(order.get("company"))
            order_customer = self._text(order.get("customer"))
            detail = self.adapter.get_sales_order(name=order_no)
            for line in self._list_or_empty(detail.get("items")):
                line_item_code = self._text(line.get("item_code")) or "-"
                line_item_name = self._text(line.get("item_name"))
                line_warehouse = self._text(line.get("warehouse"))
                processing_no = self._text(line.get("name"))
                style_type = self._text(line.get("custom_style_type")) or self._text(line.get("category"))
                season = self._text(line.get("custom_season")) or self._text(order.get("custom_season"))
                if normalized_no and not self._contains_like(order_no, normalized_no):
                    continue
                if normalized_style:
                    in_style = self._contains_like(line_item_code, normalized_style) or self._contains_like(
                        line_item_name, normalized_style
                    )
                    if not in_style:
                        continue
                if warehouse and line_warehouse != warehouse:
                    continue
                if normalized_keyword:
                    keyword_text = " ".join(
                        (
                            order_no,
                            line_item_code,
                            line_item_name or "",
                            order_customer or "",
                        )
                    )
                    if not self._contains_like(keyword_text, normalized_keyword):
                        continue
                report_rows.append(
                    FinishedGoodsReportItem(
                        image_url=None,
                        processing_no=processing_no,
                        production_order=None,
                        order_no=order_no,
                        item_code=line_item_code,
                        item_name=line_item_name,
                        warehouse=line_warehouse,
                        season=season,
                        style_type=style_type,
                        qty=self._decimal_or_zero(line.get("qty")),
                        receipt_date=detail.get("transaction_date"),
                        company=order_company,
                        customer=order_customer,
                        week_day_0="-",
                        week_day_1="-",
                        week_day_2="-",
                        week_day_3="-",
                        week_day_4="-",
                        week_day_5="-",
                        week_day_6="-",
                        message_title="-",
                        sent_at="-",
                        message_status=self._text(order.get("status")) or "-",
                        sender="-",
                    )
                )
        report_rows.sort(key=lambda row: (row.order_no, row.item_code, row.processing_no or ""))
        total = len(report_rows)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        paged_items = report_rows[start:end]
        return FinishedGoodsReportData(
            items=paged_items,
            total=total,
            page=page,
            page_size=page_size,
            dropped_count=0,
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
