<template>
  <div class="report-catalog-page" data-testid="report-catalog-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <span>报表中心 / 资金计划报表（TASK-Y3B-08）</span>
          <div class="header-actions">
            <el-button
              type="primary"
              :loading="queryLoading"
              data-testid="report-catalog-query-button"
              @click="loadCatalog"
            >
              查询
            </el-button>
            <el-button
              plain
              :disabled="queryLoading"
              data-testid="report-catalog-reset-button"
              @click="resetCatalog"
            >
              重置
            </el-button>
            <el-button
              type="success"
              plain
              :disabled="queryLoading || financeItems.length === 0"
              data-testid="report-catalog-export-guarded-button"
              data-write-guard="guarded:readonly-report-export"
              @click="handleExport"
            >
              导出（只读）
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form" data-testid="report-catalog-query-form">
        <el-form-item label="公司">
          <el-input v-model="query.company" clearable placeholder="请输入" data-testid="report-catalog-company-input" />
        </el-form-item>
        <el-form-item label="客户">
          <el-input
            v-model="query.customer_keyword"
            clearable
            placeholder="请输入"
            data-testid="report-catalog-customer-input"
          />
        </el-form-item>
        <el-form-item label="来源模块">
          <el-select
            v-model="query.source_module"
            clearable
            placeholder="全部"
            style="width: 180px"
            data-testid="report-catalog-source-module-select"
          >
            <el-option v-for="item in sourceModuleOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="报表类型">
          <el-select
            v-model="query.report_type"
            clearable
            placeholder="全部"
            style="width: 180px"
            data-testid="report-catalog-report-type-select"
          >
            <el-option v-for="item in reportTypeOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="员工">
          <el-input
            v-model="query.employee_keyword"
            clearable
            placeholder="请输入员工姓名/编号/任务单号"
            data-testid="report-catalog-employee-keyword-input"
          />
        </el-form-item>
        <el-form-item label="审批人">
          <el-input
            v-model="query.approver_keyword"
            clearable
            placeholder="请输入审批人/申请人/审批单号"
            data-testid="report-catalog-approver-keyword-input"
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-select
            v-model="query.department"
            clearable
            placeholder="全部"
            style="width: 180px"
            data-testid="report-catalog-department-select"
          >
            <el-option v-for="item in departmentOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务状态">
          <el-select
            v-model="query.task_status"
            clearable
            placeholder="全部"
            style="width: 180px"
            data-testid="report-catalog-task-status-select"
          >
            <el-option v-for="item in employeeTaskStatusOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="审批状态">
          <el-select
            v-model="query.approval_status"
            clearable
            placeholder="全部"
            style="width: 180px"
            data-testid="report-catalog-approval-status-select"
          >
            <el-option v-for="item in approvalStatusOptions" :key="item" :label="item" :value="item" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-input
            v-model="query.from_date"
            clearable
            placeholder="开始时间"
            data-testid="report-catalog-from-date-input"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-input
            v-model="query.to_date"
            clearable
            placeholder="结束时间"
            data-testid="report-catalog-to-date-input"
          />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无 report:read 权限"
        data-testid="report-catalog-permission-state"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="!canExport"
        type="warning"
        :closable="false"
        title="当前账号无 report:export 权限，导出按钮保持禁用。"
        data-testid="report-catalog-export-permission-state"
        style="margin-bottom: 12px"
      />
      <el-alert
        type="info"
        :closable="false"
        title="共享路由边界：本页保留资金计划报表语义，并新增员工任务统计表只读区块。"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="parityHint"
        type="info"
        :closable="false"
        :title="parityHint"
        data-testid="report-catalog-parity-hint"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="scopeExpandedToOtherReports"
        type="warning"
        :closable="false"
        title="检测到同路由下存在其他报表项，本页按任务边界仅处理资金计划报表、员工任务统计表与审批报表。"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="!taskY3B07EntryPreserved"
        type="error"
        :closable="false"
        :title="preserveCheckMessage || '加工成品库存条目校验失败。'"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="financeErrorMessage"
        type="error"
        :closable="false"
        :title="financeErrorMessage"
        data-testid="report-catalog-error-state"
        style="margin-bottom: 12px"
      />
      <el-alert
        v-if="exportGuardMessage"
        type="warning"
        :closable="false"
        :title="exportGuardMessage"
        data-testid="report-catalog-export-guarded-state"
        style="margin-bottom: 12px"
      />

      <el-table
        v-if="financeItems.length > 0"
        :data="financeItems"
        border
        data-testid="report-catalog-table"
        empty-text="暂无资金计划报表目录数据"
        @row-click="onFinanceRowClick"
      >
        <el-table-column prop="report_key" label="report_key" min-width="220" />
        <el-table-column prop="name" label="报表名称" min-width="180" />
        <el-table-column label="来源模块" min-width="180">
          <template #default="scope">
            <el-tag
              v-for="module in scope.row.source_modules"
              :key="module"
              type="info"
              effect="plain"
              style="margin-right: 6px"
            >
              {{ module }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="report_type" label="类型" width="150" />
        <el-table-column prop="status" label="状态" width="120" />
      </el-table>

      <el-empty v-else description="暂无资金计划报表目录数据" data-testid="report-catalog-empty-state" />

      <el-card
        v-if="selectedFinanceItem"
        shadow="never"
        class="detail-card"
        data-testid="report-catalog-detail-preview"
      >
        <template #header>
          <div class="header-row">
            <span>报表详情：{{ selectedFinanceItem.name }}</span>
            <span>{{ selectedFinanceItem.report_key }}</span>
          </div>
        </template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="来源模块">{{ selectedFinanceItem.source_modules.join(', ') }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedFinanceItem.report_type }}</el-descriptions-item>
          <el-descriptions-item label="必填过滤">{{ selectedFinanceItem.required_filters.join(', ') || '-' }}</el-descriptions-item>
          <el-descriptions-item label="可选过滤">{{ selectedFinanceItem.optional_filters.join(', ') || '-' }}</el-descriptions-item>
          <el-descriptions-item label="指标摘要" :span="2">{{
            selectedFinanceItem.metric_summary.join(', ') || '-'
          }}</el-descriptions-item>
          <el-descriptions-item label="状态标签" :span="2">
            <el-tag
              v-for="tag in selectedFinanceItem.status_tags || []"
              :key="tag"
              effect="plain"
              style="margin-right: 6px"
            >
              {{ tag }}
            </el-tag>
            <span v-if="!(selectedFinanceItem.status_tags || []).length">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="占位词映射" :span="2">
            <el-tag
              v-for="placeholder in selectedFinanceItem.ui_placeholders || []"
              :key="placeholder"
              effect="plain"
              style="margin-right: 6px"
            >
              {{ placeholder }}
            </el-tag>
            <span v-if="!(selectedFinanceItem.ui_placeholders || []).length">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="按钮映射" :span="2">
            <el-tag
              v-for="buttonText in selectedFinanceItem.ui_buttons || []"
              :key="buttonText"
              effect="plain"
              style="margin-right: 6px; margin-bottom: 6px"
            >
              {{ buttonText }}
            </el-tag>
            <span v-if="!(selectedFinanceItem.ui_buttons || []).length">-</span>
          </el-descriptions-item>
        </el-descriptions>

        <el-table
          v-if="financePreviewRows.length > 0 && financePreviewHeaders.length > 0"
          :data="financePreviewRows"
          border
          class="preview-table"
          empty-text="暂无资金计划报表预览数据"
        >
          <el-table-column
            v-for="header in financePreviewHeaders"
            :key="header"
            :prop="header"
            :label="header"
            min-width="120"
          />
        </el-table>
      </el-card>

      <el-divider />

      <el-card shadow="never" class="employee-task-card" data-testid="employee-task-statistics-section">
        <template #header>
          <div class="header-row">
            <span>员工任务统计表（TASK-Y74B-P1-01）</span>
            <div class="header-actions">
              <el-button
                type="primary"
                plain
                data-testid="employee-task-guarded-confirm-button"
                data-write-guard="guarded:readonly-report-action"
                @click="showGuardedMessage('确认')"
              >
                确认（guarded）
              </el-button>
              <el-button
                type="warning"
                plain
                data-testid="employee-task-guarded-review-button"
                data-write-guard="guarded:readonly-report-action"
                @click="showGuardedMessage('审核')"
              >
                审核（guarded）
              </el-button>
              <el-button
                type="success"
                plain
                disabled
                data-testid="employee-task-export-disabled-button"
                data-write-guard="guarded:readonly-report-export"
              >
                导出（disabled）
              </el-button>
              <el-button
                type="info"
                plain
                disabled
                data-testid="employee-task-print-disabled-button"
                data-write-guard="guarded:readonly-report-print"
              >
                打印（disabled）
              </el-button>
              <el-button
                type="info"
                plain
                disabled
                data-testid="employee-task-upload-disabled-button"
                data-write-guard="guarded:readonly-report-upload"
              >
                上传（disabled）
              </el-button>
            </div>
          </div>
        </template>

        <el-alert
          type="info"
          :closable="false"
          title="本区块为只读首版，确认/审核/导出/打印/上传均为 guarded 或 disabled，不触发写请求。"
          style="margin-bottom: 12px"
        />
        <el-alert
          v-if="employeeTaskErrorMessage"
          type="error"
          :closable="false"
          :title="employeeTaskErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          v-if="employeeTaskItems.length > 0"
          :data="employeeTaskItems"
          border
          data-testid="employee-task-statistics-table"
          empty-text="暂无员工任务统计数据"
          @row-click="onEmployeeTaskRowClick"
        >
          <el-table-column prop="employee_id" label="员工编号" min-width="120" />
          <el-table-column prop="employee_name" label="员工姓名" min-width="120" />
          <el-table-column prop="department" label="部门" min-width="120" />
          <el-table-column prop="pending_tasks" label="待办任务" min-width="100" />
          <el-table-column prop="in_progress_tasks" label="进行中任务" min-width="110" />
          <el-table-column prop="completed_tasks" label="已完成任务" min-width="110" />
          <el-table-column prop="overdue_tasks" label="逾期任务" min-width="100" />
          <el-table-column prop="completion_rate" label="完成率" min-width="90" />
          <el-table-column prop="latest_task_no" label="最近任务单号" min-width="170" />
          <el-table-column prop="latest_task_title" label="最近任务标题" min-width="180" />
          <el-table-column prop="latest_due_date" label="最近截止日期" min-width="130" />
          <el-table-column prop="updated_at" label="更新时间" min-width="150" />
          <el-table-column label="状态" min-width="90">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)" effect="plain">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="210" fixed="right">
            <template #default="scope">
              <el-button type="primary" link @click.stop="onEmployeeTaskRowClick(scope.row)">查看</el-button>
              <el-button type="warning" link @click.stop="showGuardedMessage('确认')">确认</el-button>
              <el-button type="warning" link @click.stop="showGuardedMessage('审核')">审核</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty
          v-else
          description="暂无员工任务统计数据"
          data-testid="employee-task-statistics-empty-state"
        />

        <el-card
          v-if="selectedEmployeeTaskItem"
          shadow="never"
          class="detail-card"
          data-testid="employee-task-detail-preview"
        >
          <template #header>
            <div class="header-row">
              <span>统计详情：{{ selectedEmployeeTaskItem.employee_name }}</span>
              <span>{{ selectedEmployeeTaskItem.employee_id }}</span>
            </div>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="部门">{{ selectedEmployeeTaskItem.department }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="statusTagType(selectedEmployeeTaskItem.status)" effect="plain">
                {{ selectedEmployeeTaskItem.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="待办任务">{{ selectedEmployeeTaskItem.pending_tasks }}</el-descriptions-item>
            <el-descriptions-item label="进行中任务">{{ selectedEmployeeTaskItem.in_progress_tasks }}</el-descriptions-item>
            <el-descriptions-item label="已完成任务">{{ selectedEmployeeTaskItem.completed_tasks }}</el-descriptions-item>
            <el-descriptions-item label="逾期任务">{{ selectedEmployeeTaskItem.overdue_tasks }}</el-descriptions-item>
            <el-descriptions-item label="完成率">{{ selectedEmployeeTaskItem.completion_rate }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ selectedEmployeeTaskItem.updated_at }}</el-descriptions-item>
            <el-descriptions-item label="最近任务单号">{{ selectedEmployeeTaskItem.latest_task_no }}</el-descriptions-item>
            <el-descriptions-item label="最近截止日期">{{ selectedEmployeeTaskItem.latest_due_date }}</el-descriptions-item>
            <el-descriptions-item label="最近任务标题" :span="2">
              {{ selectedEmployeeTaskItem.latest_task_title }}
            </el-descriptions-item>
            <el-descriptions-item label="状态标签映射" :span="2">
              <el-tag v-for="tag in employeeTaskStatusTags" :key="tag" effect="plain" style="margin-right: 6px">
                {{ tag }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="按钮映射" :span="2">
              <el-tag v-for="button in employeeTaskButtons" :key="button" effect="plain" style="margin-right: 6px">
                {{ button }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="表头映射" :span="2">
              <el-tag
                v-for="header in employeeTaskTableHeaders"
                :key="header"
                effect="plain"
                style="margin-right: 6px; margin-bottom: 6px"
              >
                {{ header }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-card>

      <el-divider />

      <el-card shadow="never" class="approval-report-card" data-testid="approval-report-section">
        <template #header>
          <div class="header-row">
            <span>审批报表（TASK-Y74B-P1-02）</span>
            <div class="header-actions">
              <el-button
                type="primary"
                plain
                data-testid="approval-report-guarded-confirm-button"
                data-write-guard="guarded:readonly-report-action"
                @click="showGuardedMessage('确认')"
              >
                确认（guarded）
              </el-button>
              <el-button
                type="warning"
                plain
                data-testid="approval-report-guarded-review-button"
                data-write-guard="guarded:readonly-report-action"
                @click="showGuardedMessage('审核')"
              >
                审核（guarded）
              </el-button>
              <el-button
                type="success"
                plain
                disabled
                data-testid="approval-report-export-disabled-button"
                data-write-guard="guarded:readonly-report-export"
              >
                导出（disabled）
              </el-button>
              <el-button
                type="info"
                plain
                disabled
                data-testid="approval-report-print-disabled-button"
                data-write-guard="guarded:readonly-report-print"
              >
                打印（disabled）
              </el-button>
              <el-button
                type="info"
                plain
                disabled
                data-testid="approval-report-upload-disabled-button"
                data-write-guard="guarded:readonly-report-upload"
              >
                上传（disabled）
              </el-button>
            </div>
          </div>
        </template>

        <el-alert
          type="info"
          :closable="false"
          title="本区块为只读首版，确认/审核/导出/打印/上传均为 guarded 或 disabled，不触发写请求。"
          style="margin-bottom: 12px"
        />
        <el-alert
          v-if="approvalErrorMessage"
          type="error"
          :closable="false"
          :title="approvalErrorMessage"
          style="margin-bottom: 12px"
        />

        <el-table
          v-if="approvalItems.length > 0"
          :data="approvalItems"
          border
          data-testid="approval-report-table"
          empty-text="暂无审批报表数据"
          @row-click="onApprovalRowClick"
        >
          <el-table-column prop="approval_no" label="审批单号" min-width="160" />
          <el-table-column prop="approval_type" label="审批类型" min-width="120" />
          <el-table-column prop="related_doc_no" label="关联单据" min-width="150" />
          <el-table-column prop="applicant" label="申请人" min-width="110" />
          <el-table-column prop="approver" label="审批人" min-width="110" />
          <el-table-column prop="department" label="部门" min-width="120" />
          <el-table-column prop="amount" label="金额" min-width="100" />
          <el-table-column prop="priority" label="优先级" min-width="90" />
          <el-table-column prop="submitted_at" label="提交时间" min-width="150" />
          <el-table-column prop="completed_at" label="完成时间" min-width="150" />
          <el-table-column label="状态" min-width="100">
            <template #default="scope">
              <el-tag :type="approvalStatusTagType(scope.row.status)" effect="plain">{{ scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="remark" label="备注" min-width="180" />
          <el-table-column label="操作" min-width="210" fixed="right">
            <template #default="scope">
              <el-button type="primary" link @click.stop="onApprovalRowClick(scope.row)">查看</el-button>
              <el-button type="warning" link @click.stop="showGuardedMessage('确认')">确认</el-button>
              <el-button type="warning" link @click.stop="showGuardedMessage('审核')">审核</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-else description="暂无审批报表数据" data-testid="approval-report-empty-state" />

        <el-card v-if="selectedApprovalItem" shadow="never" class="detail-card" data-testid="approval-report-detail-preview">
          <template #header>
            <div class="header-row">
              <span>审批详情：{{ selectedApprovalItem.approval_no }}</span>
              <span>{{ selectedApprovalItem.approval_type }}</span>
            </div>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="审批单号">{{ selectedApprovalItem.approval_no }}</el-descriptions-item>
            <el-descriptions-item label="审批类型">{{ selectedApprovalItem.approval_type }}</el-descriptions-item>
            <el-descriptions-item label="关联单据">{{ selectedApprovalItem.related_doc_no }}</el-descriptions-item>
            <el-descriptions-item label="优先级">{{ selectedApprovalItem.priority }}</el-descriptions-item>
            <el-descriptions-item label="申请人">{{ selectedApprovalItem.applicant }}</el-descriptions-item>
            <el-descriptions-item label="审批人">{{ selectedApprovalItem.approver }}</el-descriptions-item>
            <el-descriptions-item label="部门">{{ selectedApprovalItem.department }}</el-descriptions-item>
            <el-descriptions-item label="金额">{{ selectedApprovalItem.amount }}</el-descriptions-item>
            <el-descriptions-item label="提交时间">{{ selectedApprovalItem.submitted_at }}</el-descriptions-item>
            <el-descriptions-item label="完成时间">{{ selectedApprovalItem.completed_at }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="approvalStatusTagType(selectedApprovalItem.status)" effect="plain">
                {{ selectedApprovalItem.status }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="备注">{{ selectedApprovalItem.remark }}</el-descriptions-item>
            <el-descriptions-item label="状态标签映射" :span="2">
              <el-tag v-for="tag in approvalStatusTags" :key="tag" effect="plain" style="margin-right: 6px">
                {{ tag }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="按钮映射" :span="2">
              <el-tag v-for="button in approvalButtons" :key="button" effect="plain" style="margin-right: 6px">
                {{ button }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="表头映射" :span="2">
              <el-tag
                v-for="header in approvalTableHeaders"
                :key="header"
                effect="plain"
                style="margin-right: 6px; margin-bottom: 6px"
              >
                {{ header }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-card>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import reportApi from '@/api/report'
import { usePermissionStore } from '@/stores/permission'

interface ReportCatalogItem {
  report_key: string
  name: string
  source_modules: string[]
  report_type: string
  required_filters: string[]
  optional_filters: string[]
  metric_summary: string[]
  permission_action: string
  status: string
  ui_placeholders?: string[]
  ui_buttons?: string[]
  ui_table_headers?: string[]
  status_tags?: string[]
  preview_rows?: Array<Record<string, string>>
}

interface EmployeeTaskStatisticsItem {
  employee_id: string
  employee_name: string
  department: string
  pending_tasks: number
  in_progress_tasks: number
  completed_tasks: number
  overdue_tasks: number
  completion_rate: string
  latest_task_no: string
  latest_task_title: string
  latest_due_date: string
  updated_at: string
  status: string
}

interface ApprovalReportItem {
  approval_no: string
  approval_type: string
  related_doc_no: string
  applicant: string
  approver: string
  department: string
  amount: string
  priority: string
  submitted_at: string
  completed_at: string
  status: string
  remark: string
}

const TASK_SCOPE_REPORT_KEY = 'finance_plan_report'
const PRESERVED_REPORT_KEY = 'factory_product_stock_report'
const TASK_SCOPE_REPORT_KEYS = new Set([TASK_SCOPE_REPORT_KEY, PRESERVED_REPORT_KEY])
const READONLY_LOCAL_PARITY_SET = new Set(['customer-reconciliation', 'factory-product-stock'])

const LOCAL_FINANCE_CATALOG_ITEMS: ReportCatalogItem[] = [
  {
    report_key: TASK_SCOPE_REPORT_KEY,
    name: '资金计划报表',
    source_modules: ['finance'],
    report_type: 'financial',
    required_filters: ['company', 'from_date', 'to_date'],
    optional_filters: ['customer_keyword', 'employee_keyword', 'department'],
    metric_summary: ['回款计划', '账龄分布', '预警金额'],
    permission_action: 'report:read',
    status: 'active',
    ui_placeholders: ['请输入', '全部', '开始时间', '结束时间'],
    ui_buttons: ['查询', '重置', '查看'],
    ui_table_headers: ['标题', '客户', '账期', '发送时间'],
    status_tags: ['active'],
    preview_rows: [
      {
        标题: '资金计划报表-本月计划',
        客户: '华南服饰',
        账期: '30天',
        发送时间: '2026-05-18 10:20:00',
      },
      {
        标题: '资金计划报表-重点客户',
        客户: '领意服装',
        账期: '45天',
        发送时间: '2026-05-20 09:35:00',
      },
    ],
  },
]

const LOCAL_EMPLOYEE_TASK_ITEMS: EmployeeTaskStatisticsItem[] = [
  {
    employee_id: 'E-001',
    employee_name: '李青',
    department: '财务对账',
    pending_tasks: 3,
    in_progress_tasks: 2,
    completed_tasks: 12,
    overdue_tasks: 0,
    completion_rate: '85%',
    latest_task_no: 'TASK-20260520-01',
    latest_task_title: '客户回款核对',
    latest_due_date: '2026-05-22',
    updated_at: '2026-05-20 10:12:00',
    status: '正常',
  },
]

const LOCAL_APPROVAL_ITEMS: ApprovalReportItem[] = [
  {
    approval_no: 'APR-20260520-01',
    approval_type: '费用审批',
    related_doc_no: 'DOC-20260520-08',
    applicant: '王敏',
    approver: '赵晨',
    department: '财务对账',
    amount: '12000',
    priority: '中',
    submitted_at: '2026-05-20 09:20:00',
    completed_at: '-',
    status: '待审批',
    remark: '只读演示数据',
  },
]

const permissionStore = usePermissionStore()
const route = useRoute()
const loading = ref<boolean>(false)
const employeeTaskLoading = ref<boolean>(false)
const approvalLoading = ref<boolean>(false)
const financeItems = ref<ReportCatalogItem[]>([])
const selectedFinanceItem = ref<ReportCatalogItem | null>(null)
const financeErrorMessage = ref<string>('')
const exportGuardMessage = ref<string>('')
const employeeTaskErrorMessage = ref<string>('')
const approvalErrorMessage = ref<string>('')
const scopeExpandedToOtherReports = ref<boolean>(false)
const taskY3B07EntryPreserved = ref<boolean>(true)
const preserveCheckMessage = ref<string>('')
const parityHint = ref<string>('')
const parityQuery = computed<string>(() => (typeof route.query.parity === 'string' ? route.query.parity.trim() : ''))
const readonlyProbe = computed<boolean>(() => route.query.readonly_probe === '1')
const readonlyLocalParityMode = computed<boolean>(() => READONLY_LOCAL_PARITY_SET.has(parityQuery.value))

const employeeTaskItems = ref<EmployeeTaskStatisticsItem[]>([])
const selectedEmployeeTaskItem = ref<EmployeeTaskStatisticsItem | null>(null)
const employeeTaskStatusTags = ref<string[]>([])
const employeeTaskButtons = ref<string[]>([])
const employeeTaskTableHeaders = ref<string[]>([])
const approvalItems = ref<ApprovalReportItem[]>([])
const selectedApprovalItem = ref<ApprovalReportItem | null>(null)
const approvalStatusTags = ref<string[]>([])
const approvalButtons = ref<string[]>([])
const approvalTableHeaders = ref<string[]>([])

const query = reactive({
  company: '',
  customer_keyword: '',
  source_module: 'finance',
  report_type: 'financial',
  employee_keyword: '',
  approver_keyword: '',
  department: '',
  task_status: '',
  approval_status: '',
  from_date: '',
  to_date: '',
})

const sourceModuleOptions = ['finance']
const reportTypeOptions = ['financial']
const departmentOptions = ['生产计划', '仓储协同', '财务对账', '质检中心']
const employeeTaskStatusOptions = ['正常', '预警', '冻结']
const approvalStatusOptions = ['待审批', '已通过', '已驳回']

const canRead = computed<boolean>(() => permissionStore.state.actions.includes('report:read'))
const canExport = computed<boolean>(() => permissionStore.state.actions.includes('report:export'))
const queryLoading = computed<boolean>(() => loading.value || employeeTaskLoading.value || approvalLoading.value)
const financePreviewHeaders = computed<string[]>(() => selectedFinanceItem.value?.ui_table_headers || [])

const financePreviewRows = computed<Array<Record<string, string>>>(() => {
  const rows = selectedFinanceItem.value?.preview_rows || []
  return rows.filter((row) => {
    const customerKeyword = query.customer_keyword.trim()
    if (customerKeyword && !(`${row['客户'] || ''}${row['标题'] || ''}`.includes(customerKeyword))) {
      return false
    }
    const fromDate = query.from_date.trim()
    if (fromDate && (row['发送时间'] || '').slice(0, 10) < fromDate) {
      return false
    }
    const toDate = query.to_date.trim()
    if (toDate && (row['发送时间'] || '').slice(0, 10) > toDate) {
      return false
    }
    return true
  })
})

const statusTagType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === '正常') {
    return 'success'
  }
  if (status === '预警') {
    return 'warning'
  }
  if (status === '冻结') {
    return 'danger'
  }
  return 'info'
}

const approvalStatusTagType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (status === '已通过') {
    return 'success'
  }
  if (status === '待审批') {
    return 'warning'
  }
  if (status === '已驳回') {
    return 'danger'
  }
  return 'info'
}

const showGuardedMessage = (action: string): void => {
  ElMessage.info(`${action}入口已guarded，仅支持只读浏览`)
}

const matchKeyword = (rawValue: string, keyword: string): boolean => {
  const value = rawValue.trim()
  if (!value) {
    return true
  }
  return keyword.includes(value)
}

const loadLocalReadonlyFinanceCatalog = (): Promise<void> => {
  loading.value = true
  selectedFinanceItem.value = null
  financeErrorMessage.value = ''
  exportGuardMessage.value = ''
  scopeExpandedToOtherReports.value = false
  taskY3B07EntryPreserved.value = true
  preserveCheckMessage.value = ''

  const customerKeyword = query.customer_keyword.trim()
  const fromDate = query.from_date.trim()
  const toDate = query.to_date.trim()

  const list = LOCAL_FINANCE_CATALOG_ITEMS.filter((item) => {
    if (query.source_module && !item.source_modules.includes(query.source_module)) {
      return false
    }
    if (query.report_type && item.report_type !== query.report_type) {
      return false
    }
    const rows = item.preview_rows || []
    if (customerKeyword && !rows.some((row) => `${row['标题'] || ''}${row['客户'] || ''}`.includes(customerKeyword))) {
      return false
    }
    if (fromDate && !rows.some((row) => String(row['发送时间'] || '').slice(0, 10) >= fromDate)) {
      return false
    }
    if (toDate && !rows.some((row) => String(row['发送时间'] || '').slice(0, 10) <= toDate)) {
      return false
    }
    return true
  })

  financeItems.value = list
  selectedFinanceItem.value = list[0] || null
  if (financeItems.value.length === 0) {
    financeErrorMessage.value = '暂无资金计划报表目录数据（本地只读样例）'
  }

  loading.value = false
  return Promise.resolve()
}

const loadLocalReadonlyEmployeeTaskStatistics = (): Promise<void> => {
  employeeTaskLoading.value = true
  employeeTaskErrorMessage.value = ''
  selectedEmployeeTaskItem.value = null

  const list = LOCAL_EMPLOYEE_TASK_ITEMS.filter((item) => {
    if (query.department && item.department !== query.department) {
      return false
    }
    if (query.task_status && item.status !== query.task_status) {
      return false
    }
    if (!matchKeyword(query.employee_keyword, `${item.employee_id}${item.employee_name}${item.latest_task_no}`)) {
      return false
    }
    if (query.from_date && item.latest_due_date < query.from_date) {
      return false
    }
    if (query.to_date && item.latest_due_date > query.to_date) {
      return false
    }
    return true
  })

  employeeTaskItems.value = list
  employeeTaskStatusTags.value = ['正常', '预警', '冻结']
  employeeTaskButtons.value = ['查看', '确认', '审核', '导出', '打印', '上传']
  employeeTaskTableHeaders.value = ['员工编号', '员工姓名', '部门', '待办任务', '进行中任务', '已完成任务']
  selectedEmployeeTaskItem.value = employeeTaskItems.value[0] || null
  if (!employeeTaskItems.value.length) {
    employeeTaskErrorMessage.value = '暂无员工任务统计数据（本地只读样例）'
  }

  employeeTaskLoading.value = false
  return Promise.resolve()
}

const loadLocalReadonlyApprovalReports = (): Promise<void> => {
  approvalLoading.value = true
  approvalErrorMessage.value = ''
  selectedApprovalItem.value = null

  const list = LOCAL_APPROVAL_ITEMS.filter((item) => {
    if (query.approval_status && item.status !== query.approval_status) {
      return false
    }
    if (!matchKeyword(query.approver_keyword, `${item.approver}${item.applicant}${item.approval_no}`)) {
      return false
    }
    if (query.from_date && item.submitted_at.slice(0, 10) < query.from_date) {
      return false
    }
    if (query.to_date && item.submitted_at.slice(0, 10) > query.to_date) {
      return false
    }
    return true
  })

  approvalItems.value = list
  approvalStatusTags.value = ['待审批', '已通过', '已驳回']
  approvalButtons.value = ['查看', '确认', '审核', '导出', '打印', '上传']
  approvalTableHeaders.value = ['审批单号', '审批类型', '申请人', '审批人', '金额', '状态']
  selectedApprovalItem.value = approvalItems.value[0] || null
  if (!approvalItems.value.length) {
    approvalErrorMessage.value = '暂无审批报表数据（本地只读样例）'
  }

  approvalLoading.value = false
  return Promise.resolve()
}

const resetCatalog = (): Promise<void> => {
  query.company = ''
  query.customer_keyword = ''
  query.source_module = 'finance'
  query.report_type = 'financial'
  query.employee_keyword = ''
  query.approver_keyword = ''
  query.department = ''
  query.task_status = ''
  query.approval_status = ''
  query.from_date = ''
  query.to_date = ''
  return loadCatalog()
}

const checkTaskY3B07Entry = (): Promise<void> => {
  if (readonlyLocalParityMode.value) {
    taskY3B07EntryPreserved.value = true
    preserveCheckMessage.value = ''
    return Promise.resolve()
  }
  return reportApi
    .fetchReportCatalogDetail(PRESERVED_REPORT_KEY, query.company.trim() || undefined)
    .then(() => {
      taskY3B07EntryPreserved.value = true
      preserveCheckMessage.value = ''
    })
    .catch((error: unknown) => {
      taskY3B07EntryPreserved.value = false
      preserveCheckMessage.value = `TASK-Y3B-07 条目校验失败：${(error as Error).message || 'unknown'}`
    })
}

const loadFinanceCatalog = (): Promise<void> => {
  if (readonlyLocalParityMode.value) {
    return loadLocalReadonlyFinanceCatalog()
  }
  loading.value = true
  selectedFinanceItem.value = null
  financeErrorMessage.value = ''
  exportGuardMessage.value = ''
  scopeExpandedToOtherReports.value = false
  return reportApi
    .fetchReportCatalog({
      company: query.company.trim() || undefined,
      source_module: query.source_module || undefined,
      report_type: query.report_type || undefined,
    })
    .then((result) => {
      const apiItems = result.data.items
      scopeExpandedToOtherReports.value = apiItems.some((item) => !TASK_SCOPE_REPORT_KEYS.has(item.report_key))
      financeItems.value = apiItems.filter((item) => item.report_key === TASK_SCOPE_REPORT_KEY)
      selectedFinanceItem.value = financeItems.value[0] || null
      if (financeItems.value.length === 0) {
        financeErrorMessage.value = '未命中资金计划报表目录条目，请检查筛选条件。'
      }
      return checkTaskY3B07Entry()
    })
    .catch((error: unknown) => {
      const message = (error as Error).message || '目录加载失败'
      return loadLocalReadonlyFinanceCatalog().then(() => {
        financeErrorMessage.value = `目录接口不可用，已切换本地只读样例：${message}`
        exportGuardMessage.value = '当前为只读 fallback 模式，导出/下载/同步动作保持 guarded。'
        ElMessage.warning(financeErrorMessage.value)
      })
    })
    .finally(() => {
      loading.value = false
    })
}

const loadEmployeeTaskStatistics = (): Promise<void> => {
  if (readonlyLocalParityMode.value) {
    return loadLocalReadonlyEmployeeTaskStatistics()
  }
  employeeTaskLoading.value = true
  employeeTaskErrorMessage.value = ''
  selectedEmployeeTaskItem.value = null
  return reportApi
    .fetchReportEmployeeTaskStatistics({
      company: query.company.trim() || undefined,
      department: query.department || undefined,
      task_status: query.task_status || undefined,
      employee_keyword: query.employee_keyword.trim() || undefined,
      from_date: query.from_date.trim() || undefined,
      to_date: query.to_date.trim() || undefined,
    })
    .then((result) => {
      employeeTaskItems.value = result.data.items
      employeeTaskStatusTags.value = result.data.status_tags || []
      employeeTaskButtons.value = result.data.ui_buttons || []
      employeeTaskTableHeaders.value = result.data.ui_table_headers || []
      if (employeeTaskItems.value.length > 0) {
        selectedEmployeeTaskItem.value = employeeTaskItems.value[0]
      }
    })
    .catch((error: unknown) => {
      const message = (error as Error).message || '员工任务统计加载失败'
      return loadLocalReadonlyEmployeeTaskStatistics().then(() => {
        employeeTaskErrorMessage.value = `员工任务统计接口不可用，已切换本地只读样例：${message}`
        ElMessage.warning(employeeTaskErrorMessage.value)
      })
    })
    .finally(() => {
      employeeTaskLoading.value = false
    })
}

const loadApprovalReports = (): Promise<void> => {
  if (readonlyLocalParityMode.value) {
    return loadLocalReadonlyApprovalReports()
  }
  approvalLoading.value = true
  approvalErrorMessage.value = ''
  selectedApprovalItem.value = null
  return reportApi
    .fetchReportApprovalReports({
      company: query.company.trim() || undefined,
      approver_keyword: query.approver_keyword.trim() || undefined,
      approval_status: query.approval_status || undefined,
      from_date: query.from_date.trim() || undefined,
      to_date: query.to_date.trim() || undefined,
    })
    .then((result) => {
      approvalItems.value = result.data.items
      approvalStatusTags.value = result.data.status_tags || []
      approvalButtons.value = result.data.ui_buttons || []
      approvalTableHeaders.value = result.data.ui_table_headers || []
      if (approvalItems.value.length > 0) {
        selectedApprovalItem.value = approvalItems.value[0]
      }
    })
    .catch((error: unknown) => {
      const message = (error as Error).message || '审批报表加载失败'
      return loadLocalReadonlyApprovalReports().then(() => {
        approvalErrorMessage.value = `审批报表接口不可用，已切换本地只读样例：${message}`
        ElMessage.warning(approvalErrorMessage.value)
      })
    })
    .finally(() => {
      approvalLoading.value = false
    })
}

const loadCatalog = (): Promise<void> => {
  return Promise.all([loadFinanceCatalog(), loadEmployeeTaskStatistics(), loadApprovalReports()]).then(() => undefined)
}

const loadCatalogReadonlyFallback = (): Promise<void> => {
  return Promise.all([
    loadLocalReadonlyFinanceCatalog(),
    loadLocalReadonlyEmployeeTaskStatistics(),
    loadLocalReadonlyApprovalReports(),
  ]).then(() => {
    financeErrorMessage.value = '当前运行态使用本地只读 fallback，报表目录、员工任务与审批统计均可见。'
    exportGuardMessage.value = '导出/下载/同步动作保持 guarded，不触发真实写链路。'
  })
}

const onFinanceRowClick = (row: ReportCatalogItem): Promise<void> => {
  if (readonlyLocalParityMode.value) {
    selectedFinanceItem.value = row
    return Promise.resolve()
  }
  return reportApi
    .fetchReportCatalogDetail(row.report_key, query.company.trim() || undefined)
    .then((result) => {
      selectedFinanceItem.value = result.data.item
    })
    .catch((error: unknown) => {
      selectedFinanceItem.value = null
      const message = (error as Error).message || '详情加载失败'
      financeErrorMessage.value = `详情加载失败：${message}`
      ElMessage.error(message)
    })
}

const onEmployeeTaskRowClick = (row: EmployeeTaskStatisticsItem): void => {
  selectedEmployeeTaskItem.value = row
}

const onApprovalRowClick = (row: ApprovalReportItem): void => {
  selectedApprovalItem.value = row
}

const handleExport = (): Promise<void> => {
  exportGuardMessage.value = ''
  if (!canExport.value) {
    ElMessage.warning('当前账号无 report:export 权限')
    exportGuardMessage.value = '当前账号无 report:export 权限，导出动作已拦截。'
    return Promise.resolve()
  }
  if (!financeItems.value.length) {
    ElMessage.info('无可导出的资金计划报表目录数据')
    exportGuardMessage.value = '无可导出的资金计划报表目录数据，导出动作已拦截。'
    return Promise.resolve()
  }
  exportGuardMessage.value = '导出属于副作用动作，当前为只读演示模式，已执行 guarded 拦截。'
  ElMessage.warning(exportGuardMessage.value)
  return Promise.resolve()
}

const resolveParityHint = (): void => {
  const parity = parityQuery.value
  if (!parity) {
    parityHint.value = ''
    return
  }
  if (parity === 'customer-reconciliation') {
    parityHint.value = '衣算云 / 报表中心 / 资金计划报表（customer-reconciliation）只读 parity 对照。'
    return
  }
  if (parity === 'factory-product-stock') {
    parityHint.value = '衣算云 / 报表中心 / 加工成品库存报表（factory-product-stock）只读 parity 对照。'
    return
  }
  parityHint.value = `当前路径由衣算云入口映射进入（${parity}），仅做本地只读 parity 对照。`
}

onMounted(() => {
  resolveParityHint()
  if (readonlyProbe.value || readonlyLocalParityMode.value) {
    loadCatalog().catch((error: unknown) => {
      ElMessage.error((error as Error).message || '只读样例加载失败')
    })
    return
  }
  permissionStore
    .loadCurrentUser()
    .then(() => permissionStore.loadModuleActions('report'))
    .then(() => loadCatalog())
    .catch((error: unknown) => {
      const message = (error as Error).message || '权限或目录加载失败'
      ElMessage.warning(`${message}，已切换本地只读 fallback`)
      loadCatalogReadonlyFallback().catch((fallbackError: unknown) => {
        ElMessage.error((fallbackError as Error).message || '只读 fallback 加载失败')
      })
    })
})
</script>

<style scoped>
.report-catalog-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.header-row > .el-button {
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.query-form {
  margin-bottom: 12px;
}

.query-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

.query-form :deep(.el-input),
.query-form :deep(.el-select),
.query-form :deep(.el-date-editor) {
  max-width: 260px;
}

.detail-card {
  margin-top: 12px;
}

.preview-table {
  margin-top: 12px;
}

.employee-task-card {
  margin-top: 12px;
}

.approval-report-card {
  margin-top: 12px;
}

:deep(.el-card__header) {
  padding: 14px 16px;
}

:deep(.el-card__body) {
  padding: 14px 16px;
}

@media (max-width: 768px) {
  .header-row {
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .query-form :deep(.el-form-item) {
    margin-right: 0;
    width: 100%;
  }

  .query-form :deep(.el-input),
  .query-form :deep(.el-select),
  .query-form :deep(.el-date-editor) {
    width: 100% !important;
    max-width: 100%;
  }
}
</style>
