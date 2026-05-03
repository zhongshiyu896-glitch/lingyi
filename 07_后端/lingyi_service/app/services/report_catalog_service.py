"""Readonly report catalog service (TASK-060B)."""

from __future__ import annotations

from app.core.permissions import REPORT_READ
from app.schemas.report import ReportCatalogDetailData
from app.schemas.report import ReportCatalogItemData
from app.schemas.report import ReportCatalogListData
from app.schemas.report import ReportCatalogRequestedScope


class ReportCatalogService:
    """Serve static report definitions without touching external sources."""

    _CATALOG: tuple[ReportCatalogItemData, ...] = (
        ReportCatalogItemData(
            report_key="factory_product_stock_report",
            name="加工成品库存",
            source_modules=["collaboration"],
            report_type="readonly",
            required_filters=["company", "style_keyword", "from_date", "to_date"],
            optional_filters=["delivery_cycle_days", "remark", "source_module", "report_type"],
            metric_summary=["协同可用数量", "计划供货单价(元)"],
            permission_action=REPORT_READ,
            status="active",
            ui_placeholders=["款式", "交货周期", "开始", "结束", "备注", "请输入", "开始时间", "结束时间"],
            ui_buttons=[
                "展开",
                "重置",
                "查询",
                "导出",
                "列设置",
                "清空",
                "确定",
                "标志已读",
                "删除消息",
                "新增消息",
                "搜索",
                "保存",
                "取消",
                "重置列",
            ],
            ui_table_headers=[
                "图片",
                "款号",
                "款式名称",
                "颜色",
                "尺码",
                "协同可用数量",
                "加工厂",
                "交货周期(天)",
                "计划供货单价(元)",
                "备注",
                "日",
                "一",
                "二",
                "三",
                "四",
                "五",
                "六",
                "标题",
                "发送时间",
                "状态",
                "发送人",
            ],
            status_tags=["正常", "预警", "冻结"],
            preview_rows=[
                {
                    "图片": "-",
                    "款号": "YSY-A2301",
                    "款式名称": "连帽卫衣",
                    "颜色": "黑色",
                    "尺码": "L",
                    "协同可用数量": "120",
                    "加工厂": "协同一厂",
                    "交货周期(天)": "14",
                    "计划供货单价(元)": "89.00",
                    "备注": "本地dev只读样例",
                    "日": "8",
                    "一": "12",
                    "二": "15",
                    "三": "19",
                    "四": "23",
                    "五": "18",
                    "六": "11",
                    "标题": "加工库存周报",
                    "发送时间": "2026-05-03 10:00",
                    "状态": "正常",
                    "发送人": "local.dev",
                }
            ],
        ),
        ReportCatalogItemData(
            report_key="finance_plan_report",
            name="资金计划报表",
            source_modules=["finance"],
            report_type="financial",
            required_filters=["company", "from_date", "to_date"],
            optional_filters=["customer_keyword", "source_module", "report_type"],
            metric_summary=["未使用预付总金额", "未收款金额", "应收金额"],
            permission_action=REPORT_READ,
            status="active",
            ui_placeholders=["请输入", "开始时间", "结束时间"],
            ui_buttons=[
                "重置",
                "查询",
                "导出",
                "列设置",
                "清空",
                "确定",
                "标志已读",
                "删除消息",
                "新增消息",
                "搜索",
                "保存",
                "取消",
                "重置列",
            ],
            ui_table_headers=[
                "客户",
                "未使用预付总金额",
                "未收款金额",
                "应收金额",
                "日",
                "一",
                "二",
                "三",
                "四",
                "五",
                "六",
                "标题",
                "发送时间",
                "状态",
                "发送人",
            ],
            status_tags=["正常", "预警", "冻结"],
            preview_rows=[
                {
                    "客户": "华南A客户",
                    "未使用预付总金额": "120000.00",
                    "未收款金额": "36000.00",
                    "应收金额": "98000.00",
                    "日": "8000",
                    "一": "12000",
                    "二": "15000",
                    "三": "9000",
                    "四": "14000",
                    "五": "22000",
                    "六": "18000",
                    "标题": "资金计划周报",
                    "发送时间": "2026-05-03 11:00",
                    "状态": "正常",
                    "发送人": "local.dev",
                }
            ],
        ),
        ReportCatalogItemData(
            report_key="production_progress",
            name="生产进度看板",
            source_modules=["production", "workshop"],
            report_type="readonly",
            required_filters=["company", "from_date", "to_date"],
            optional_filters=["work_order", "operation"],
            metric_summary=["planned_qty", "completed_qty", "completion_rate"],
            permission_action=REPORT_READ,
            status="designed",
        ),
        ReportCatalogItemData(
            report_key="inventory_trend",
            name="库存趋势",
            source_modules=["warehouse", "inventory"],
            report_type="readonly",
            required_filters=["company", "from_date", "to_date"],
            optional_filters=["item_code", "warehouse"],
            metric_summary=["opening_qty", "in_qty", "out_qty", "closing_qty"],
            permission_action=REPORT_READ,
            status="designed",
        ),
        ReportCatalogItemData(
            report_key="style_profit_trend",
            name="款式利润趋势",
            source_modules=["style_profit"],
            report_type="readonly_snapshot",
            required_filters=["company", "from_date", "to_date"],
            optional_filters=["item_code", "sales_order"],
            metric_summary=["revenue", "actual_cost", "profit_amount", "profit_rate"],
            permission_action=REPORT_READ,
            status="designed",
        ),
        ReportCatalogItemData(
            report_key="factory_statement_summary",
            name="加工厂对账统计",
            source_modules=["factory_statement"],
            report_type="readonly",
            required_filters=["company", "from_date", "to_date"],
            optional_filters=["supplier", "statement_no"],
            metric_summary=["statement_count", "payable_amount", "settled_amount"],
            permission_action=REPORT_READ,
            status="designed",
        ),
        ReportCatalogItemData(
            report_key="sales_inventory_view",
            name="销售库存视图",
            source_modules=["sales_inventory"],
            report_type="readonly",
            required_filters=["company"],
            optional_filters=["item_code", "warehouse", "customer"],
            metric_summary=["actual_qty", "ordered_qty", "fulfillment_rate"],
            permission_action=REPORT_READ,
            status="designed",
        ),
        ReportCatalogItemData(
            report_key="quality_statistics",
            name="质量统计",
            source_modules=["quality"],
            report_type="readonly",
            required_filters=["company", "from_date", "to_date"],
            optional_filters=["item_code", "warehouse", "supplier"],
            metric_summary=["inspection_count", "rejected_qty", "defect_rate"],
            permission_action=REPORT_READ,
            status="designed",
        ),
        ReportCatalogItemData(
            report_key="financial_summary",
            name="财务摘要",
            source_modules=["finance"],
            report_type="readonly",
            required_filters=["company", "from_date", "to_date"],
            optional_filters=["fiscal_year", "period"],
            metric_summary=["revenue", "expense", "gross_profit", "net_profit"],
            permission_action=REPORT_READ,
            status="designed",
        ),
    )

    @classmethod
    def list_catalog(
        cls,
        *,
        company: str | None,
        source_module: str | None,
        report_type: str | None,
    ) -> ReportCatalogListData:
        normalized_company = cls._norm(company)
        normalized_source_module = cls._norm(source_module)
        normalized_report_type = cls._norm(report_type)

        if normalized_source_module and normalized_source_module not in cls._allowed_source_modules():
            raise ValueError("source_module 不合法")
        if normalized_report_type and normalized_report_type not in cls._allowed_report_types():
            raise ValueError("report_type 不合法")

        items = [item.model_copy(deep=True) for item in cls._CATALOG]
        if normalized_source_module:
            items = [item for item in items if normalized_source_module in item.source_modules]
        if normalized_report_type:
            items = [item for item in items if item.report_type == normalized_report_type]

        return ReportCatalogListData(
            items=items,
            requested_scope=ReportCatalogRequestedScope(
                company=normalized_company,
                source_module=normalized_source_module,
                report_type=normalized_report_type,
            ),
        )

    @classmethod
    def get_catalog_item(
        cls,
        *,
        report_key: str,
        company: str | None,
    ) -> ReportCatalogDetailData:
        normalized_key = cls._norm(report_key)
        for item in cls._CATALOG:
            if item.report_key == normalized_key:
                return ReportCatalogDetailData(
                    item=item.model_copy(deep=True),
                    requested_scope=ReportCatalogRequestedScope(company=cls._norm(company)),
                )
        raise KeyError("report not found")

    @classmethod
    def _allowed_source_modules(cls) -> set[str]:
        values: set[str] = set()
        for item in cls._CATALOG:
            values.update(item.source_modules)
        return values

    @classmethod
    def _allowed_report_types(cls) -> set[str]:
        return {item.report_type for item in cls._CATALOG}

    @staticmethod
    def _norm(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None
