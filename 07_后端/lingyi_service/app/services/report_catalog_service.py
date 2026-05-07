"""Readonly report catalog service (TASK-060B)."""

from __future__ import annotations

from app.core.permissions import REPORT_READ
from app.schemas.report import ReportCatalogDetailData
from app.schemas.report import ReportCatalogItemData
from app.schemas.report import ReportCatalogListData
from app.schemas.report import ReportCatalogRequestedScope
from app.schemas.report import ReportApprovalReportData
from app.schemas.report import ReportApprovalReportItemData
from app.schemas.report import ReportApprovalReportScope
from app.schemas.report import ReportEmployeeTaskStatisticsData
from app.schemas.report import ReportEmployeeTaskStatisticsItemData
from app.schemas.report import ReportEmployeeTaskStatisticsScope


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
    _EMPLOYEE_TASK_STATUS_TAGS: tuple[str, ...] = ("正常", "预警", "冻结")
    _EMPLOYEE_TASK_UI_BUTTONS: tuple[str, ...] = ("查看", "确认", "审核", "导出", "打印", "上传")
    _EMPLOYEE_TASK_UI_TABLE_HEADERS: tuple[str, ...] = (
        "员工编号",
        "员工姓名",
        "部门",
        "待办任务",
        "进行中任务",
        "已完成任务",
        "逾期任务",
        "完成率",
        "最近任务单号",
        "最近任务标题",
        "最近截止日期",
        "更新时间",
        "状态",
    )
    _EMPLOYEE_TASK_STATISTICS: tuple[ReportEmployeeTaskStatisticsItemData, ...] = (
        ReportEmployeeTaskStatisticsItemData(
            employee_id="E-1001",
            employee_name="陈晓敏",
            department="生产计划",
            pending_tasks=3,
            in_progress_tasks=6,
            completed_tasks=18,
            overdue_tasks=1,
            completion_rate="75%",
            latest_task_no="TASK-PLN-20260507-001",
            latest_task_title="夏季卫衣排产校核",
            latest_due_date="2026-05-09",
            updated_at="2026-05-07 10:30",
            status="正常",
        ),
        ReportEmployeeTaskStatisticsItemData(
            employee_id="E-1002",
            employee_name="李志远",
            department="仓储协同",
            pending_tasks=5,
            in_progress_tasks=8,
            completed_tasks=21,
            overdue_tasks=2,
            completion_rate="72%",
            latest_task_no="TASK-WHS-20260507-014",
            latest_task_title="成品收发差异复核",
            latest_due_date="2026-05-08",
            updated_at="2026-05-07 11:05",
            status="预警",
        ),
        ReportEmployeeTaskStatisticsItemData(
            employee_id="E-1003",
            employee_name="王嘉宁",
            department="财务对账",
            pending_tasks=2,
            in_progress_tasks=4,
            completed_tasks=26,
            overdue_tasks=0,
            completion_rate="84%",
            latest_task_no="TASK-FIN-20260507-006",
            latest_task_title="供应商票据核销",
            latest_due_date="2026-05-10",
            updated_at="2026-05-07 09:55",
            status="正常",
        ),
        ReportEmployeeTaskStatisticsItemData(
            employee_id="E-1004",
            employee_name="赵文涛",
            department="质检中心",
            pending_tasks=7,
            in_progress_tasks=5,
            completed_tasks=15,
            overdue_tasks=4,
            completion_rate="58%",
            latest_task_no="TASK-QA-20260507-009",
            latest_task_title="批次抽检异常闭环",
            latest_due_date="2026-05-07",
            updated_at="2026-05-07 12:10",
            status="冻结",
        ),
    )
    _APPROVAL_REPORT_STATUS_TAGS: tuple[str, ...] = ("待审批", "已通过", "已驳回")
    _APPROVAL_REPORT_UI_BUTTONS: tuple[str, ...] = ("查看", "确认", "审核", "导出", "打印", "上传")
    _APPROVAL_REPORT_UI_TABLE_HEADERS: tuple[str, ...] = (
        "审批单号",
        "审批类型",
        "关联单据",
        "申请人",
        "审批人",
        "部门",
        "金额",
        "优先级",
        "提交时间",
        "完成时间",
        "状态",
        "备注",
    )
    _APPROVAL_REPORTS: tuple[ReportApprovalReportItemData, ...] = (
        ReportApprovalReportItemData(
            approval_no="APR-20260507-001",
            approval_type="费用报销",
            related_doc_no="EXP-20260507-011",
            applicant="陈晓敏",
            approver="刘主管",
            department="财务对账",
            amount="1280.00",
            priority="高",
            submitted_at="2026-05-07 09:10",
            completed_at="-",
            status="待审批",
            remark="差旅报销待一审",
        ),
        ReportApprovalReportItemData(
            approval_no="APR-20260506-021",
            approval_type="付款申请",
            related_doc_no="PAY-20260506-088",
            applicant="李志远",
            approver="王经理",
            department="仓储协同",
            amount="5600.00",
            priority="中",
            submitted_at="2026-05-06 14:22",
            completed_at="2026-05-06 15:05",
            status="已通过",
            remark="供应商运费付款",
        ),
        ReportApprovalReportItemData(
            approval_no="APR-20260505-037",
            approval_type="采购补单",
            related_doc_no="PO-20260505-133",
            applicant="赵文涛",
            approver="王经理",
            department="生产计划",
            amount="9200.00",
            priority="高",
            submitted_at="2026-05-05 16:18",
            completed_at="2026-05-05 17:40",
            status="已驳回",
            remark="资料不完整驳回补充",
        ),
        ReportApprovalReportItemData(
            approval_no="APR-20260504-019",
            approval_type="预算调整",
            related_doc_no="BDG-20260504-009",
            applicant="王嘉宁",
            approver="刘主管",
            department="财务对账",
            amount="3000.00",
            priority="低",
            submitted_at="2026-05-04 11:03",
            completed_at="2026-05-04 11:36",
            status="已通过",
            remark="月度预算微调",
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
    def get_employee_task_statistics(
        cls,
        *,
        company: str | None,
        department: str | None,
        task_status: str | None,
        employee_keyword: str | None,
        from_date: str | None,
        to_date: str | None,
    ) -> ReportEmployeeTaskStatisticsData:
        normalized_company = cls._norm(company)
        normalized_department = cls._norm(department)
        normalized_status = cls._norm(task_status)
        normalized_employee_keyword = cls._norm(employee_keyword)
        normalized_from_date = cls._norm(from_date)
        normalized_to_date = cls._norm(to_date)

        if normalized_status and normalized_status not in cls._EMPLOYEE_TASK_STATUS_TAGS:
            raise ValueError("task_status 不合法")
        if normalized_from_date and normalized_to_date and normalized_from_date > normalized_to_date:
            raise ValueError("from_date 不能大于 to_date")

        items = [item.model_copy(deep=True) for item in cls._EMPLOYEE_TASK_STATISTICS]

        if normalized_department:
            items = [item for item in items if normalized_department in item.department]
        if normalized_status:
            items = [item for item in items if item.status == normalized_status]
        if normalized_employee_keyword:
            items = [
                item
                for item in items
                if normalized_employee_keyword in item.employee_name
                or normalized_employee_keyword in item.employee_id
                or normalized_employee_keyword in item.latest_task_no
                or normalized_employee_keyword in item.latest_task_title
            ]
        if normalized_from_date:
            items = [item for item in items if item.latest_due_date >= normalized_from_date]
        if normalized_to_date:
            items = [item for item in items if item.latest_due_date <= normalized_to_date]

        return ReportEmployeeTaskStatisticsData(
            items=items,
            status_tags=list(cls._EMPLOYEE_TASK_STATUS_TAGS),
            ui_buttons=list(cls._EMPLOYEE_TASK_UI_BUTTONS),
            ui_table_headers=list(cls._EMPLOYEE_TASK_UI_TABLE_HEADERS),
            requested_scope=ReportEmployeeTaskStatisticsScope(
                company=normalized_company,
                department=normalized_department,
                task_status=normalized_status,
                employee_keyword=normalized_employee_keyword,
                from_date=normalized_from_date,
                to_date=normalized_to_date,
            ),
        )

    @classmethod
    def get_approval_reports(
        cls,
        *,
        company: str | None,
        approver_keyword: str | None,
        approval_status: str | None,
        from_date: str | None,
        to_date: str | None,
    ) -> ReportApprovalReportData:
        normalized_company = cls._norm(company)
        normalized_approver_keyword = cls._norm(approver_keyword)
        normalized_approval_status = cls._norm(approval_status)
        normalized_from_date = cls._norm(from_date)
        normalized_to_date = cls._norm(to_date)

        if normalized_approval_status and normalized_approval_status not in cls._APPROVAL_REPORT_STATUS_TAGS:
            raise ValueError("approval_status 不合法")
        if normalized_from_date and normalized_to_date and normalized_from_date > normalized_to_date:
            raise ValueError("from_date 不能大于 to_date")

        items = [item.model_copy(deep=True) for item in cls._APPROVAL_REPORTS]

        if normalized_approver_keyword:
            items = [
                item
                for item in items
                if normalized_approver_keyword in item.approver
                or normalized_approver_keyword in item.applicant
                or normalized_approver_keyword in item.approval_no
                or normalized_approver_keyword in item.related_doc_no
                or normalized_approver_keyword in item.approval_type
            ]
        if normalized_approval_status:
            items = [item for item in items if item.status == normalized_approval_status]
        if normalized_from_date:
            items = [item for item in items if item.submitted_at[:10] >= normalized_from_date]
        if normalized_to_date:
            items = [item for item in items if item.submitted_at[:10] <= normalized_to_date]

        return ReportApprovalReportData(
            items=items,
            status_tags=list(cls._APPROVAL_REPORT_STATUS_TAGS),
            ui_buttons=list(cls._APPROVAL_REPORT_UI_BUTTONS),
            ui_table_headers=list(cls._APPROVAL_REPORT_UI_TABLE_HEADERS),
            requested_scope=ReportApprovalReportScope(
                company=normalized_company,
                approver_keyword=normalized_approver_keyword,
                approval_status=normalized_approval_status,
                from_date=normalized_from_date,
                to_date=normalized_to_date,
            ),
        )

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
