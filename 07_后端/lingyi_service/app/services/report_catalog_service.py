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
