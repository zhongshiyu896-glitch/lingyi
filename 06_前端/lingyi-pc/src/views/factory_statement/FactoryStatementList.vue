<template>
  <div class="factory-statement-list-page" data-testid="factory-statement-list-page">
    <el-card shadow="never" data-testid="factory-statement-main-section">
      <template #header>
        <div class="header-row">
          <span>加工厂对账单列表</span>
          <el-button
            type="primary"
            :disabled="!canCreateAction"
            data-action-type="write"
            data-write-guard="permission:factory_statement_create+handler"
            :data-guard-state="canCreateAction ? 'enabled' : 'disabled'"
            @click="openCreateDialog"
          >
            创建对账单
          </el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="款式打板下单对账表（TASK-Y22B-P1-02）"
        description="本页补齐只读语义映射；创建/确认/取消/应付草稿/导出等写动作仅保留 guarded 语义，不触发真实写请求。"
        class="reconciliation-alert"
        data-testid="factory-statement-main-alert"
      />

      <el-form :inline="true" :model="query" data-testid="factory-statement-query-form">
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="请输入供应商" data-testid="factory-statement-filter-supplier" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.statement_status"
            clearable
            placeholder="请选择状态"
            style="width: 160px"
            data-testid="factory-statement-filter-status"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="应付草稿已生成" value="payable_draft_created" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
            data-testid="factory-statement-filter-from-date"
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
            data-testid="factory-statement-filter-to-date"
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" data-testid="factory-statement-query-button" @click="applyPrimaryQuery">
            查询
          </el-button>
          <el-button :disabled="!canRead" data-testid="factory-statement-reset-button" @click="resetPrimaryFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-form :inline="true" :model="sampleQuery" class="sample-filter-form">
        <el-form-item label="打板单号">
          <el-input v-model="sampleQuery.sample_order_no" clearable placeholder="请输入打板单号" />
        </el-form-item>
        <el-form-item label="款号">
          <el-input v-model="sampleQuery.style_code" clearable placeholder="请输入款号" />
        </el-form-item>
        <el-form-item label="工厂">
          <el-input v-model="sampleQuery.factory_name" clearable placeholder="请输入工厂" />
        </el-form-item>
        <el-form-item label="下单时间">
          <el-date-picker
            v-model="sampleQuery.ordered_date_range"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="金额区间">
          <el-input-number
            v-model="sampleQuery.min_amount"
            :precision="2"
            :controls="false"
            placeholder="最小金额"
            style="width: 130px"
          />
          <span class="range-sep">~</span>
          <el-input-number
            v-model="sampleQuery.max_amount"
            :precision="2"
            :controls="false"
            placeholder="最大金额"
            style="width: 130px"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="sampleQuery.status" clearable placeholder="请选择状态" style="width: 160px">
            <el-option label="草稿" value="draft" />
            <el-option label="已确认" value="confirmed" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="应付草稿已生成" value="payable_draft_created" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="applySampleFilters">筛选</el-button>
          <el-button :disabled="!canRead" @click="resetSampleFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="readError"
        type="error"
        :closable="false"
        show-icon
        :title="readError"
        class="error-alert"
        data-testid="factory-statement-error-alert"
      />
      <el-empty v-if="!canRead" description="无加工厂对账单查看权限" data-testid="factory-statement-no-permission" />
      <template v-else>
        <el-table
          :data="displayRows"
          border
          v-loading="loading"
          empty-text="暂无款式打板下单对账数据"
          data-testid="factory-statement-main-table"
        >
          <el-table-column prop="sample_order_no" label="打板单号" min-width="180" />
          <el-table-column prop="style_code" label="款号" min-width="140" />
          <el-table-column prop="factory_name" label="工厂" min-width="140" />
          <el-table-column prop="ordered_at" label="下单时间" min-width="180" />
          <el-table-column label="下单金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.order_amount) }}</template>
          </el-table-column>
          <el-table-column prop="statement_no" label="对账单号" min-width="180" />
          <el-table-column prop="company" label="公司" min-width="140" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column label="期间" min-width="200">
            <template #default="scope">
              {{ scope.row.from_date }} ~ {{ scope.row.to_date }}
            </template>
          </el-table-column>
          <el-table-column label="数量" width="110">
            <template #default="scope">{{ scope.row.source_count }}</template>
          </el-table-column>
          <el-table-column label="加工费" width="130">
            <template #default="scope">{{ formatAmount(scope.row.gross_amount) }}</template>
          </el-table-column>
          <el-table-column label="扣款" width="130">
            <template #default="scope">{{ formatAmount(scope.row.deduction_amount) }}</template>
          </el-table-column>
          <el-table-column label="实付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.net_amount) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="150">
            <template #default="scope">
              <el-tag :type="statusTag(scope.row.statement_status)" data-testid="factory-statement-status-tag">
                {{ statementStatusLabel(scope.row.statement_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="应付草稿同步" min-width="140">
            <template #default="scope">
              {{ outboxStatusLabel(scope.row.payable_outbox_status) }}
            </template>
          </el-table-column>
          <el-table-column label="ERP 发票草稿" min-width="180">
            <template #default="scope">
              {{ scope.row.purchase_invoice_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
          <el-table-column label="操作" fixed="right" width="340">
            <template #default="scope">
              <el-button link type="primary" data-testid="factory-statement-detail-button" @click="goDetail(scope.row.id)">
                查看
              </el-button>
              <el-button link type="primary" @click="goPrint(scope.row.id)">打印</el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:payable-draft"
                data-guard-state="disabled"
                @click="showGuardedAction('生成应付')"
              >
                生成应付
              </el-button>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('确认')"
              >
                确认
              </el-button>
              <el-button
                link
                type="danger"
                data-action-type="write"
                data-write-guard="readonly:cancel"
                data-guard-state="disabled"
                @click="showGuardedAction('取消')"
              >
                取消
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            data-testid="factory-statement-pagination"
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="expense-reimbursement-payment-section">
      <template #header>
        <div class="header-row">
          <span>费用(报销)支付（TASK-Y59B-P1-02）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读费用(报销)支付语义映射"
        description="支付确认、复核、付款、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="expense-reimbursement-alert"
      />

      <el-form :inline="true" :model="expensePaymentQuery" class="expense-filter-form">
        <el-form-item label="支付单号">
          <el-input v-model="expensePaymentQuery.payment_no" clearable placeholder="请输入支付单号" />
        </el-form-item>
        <el-form-item label="报销单号">
          <el-input v-model="expensePaymentQuery.reimbursement_no" clearable placeholder="请输入报销单号" />
        </el-form-item>
        <el-form-item label="对账单号">
          <el-input v-model="expensePaymentQuery.statement_no" clearable placeholder="请输入对账单号" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="expensePaymentQuery.supplier" clearable placeholder="请输入供应商" />
        </el-form-item>
        <el-form-item label="支付状态">
          <el-select v-model="expensePaymentQuery.payment_status" clearable placeholder="请选择支付状态" style="width: 170px">
            <el-option label="待支付" value="待支付" />
            <el-option label="审批中" value="审批中" />
            <el-option label="部分支付" value="部分支付" />
            <el-option label="已支付" value="已支付" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select v-model="expensePaymentQuery.review_status" clearable placeholder="请选择复核状态" style="width: 170px">
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="expensePaymentQuery.keyword"
            clearable
            placeholder="支付单号/报销单号/供应商/经办人"
            style="width: 280px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="expensePaymentQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="expensePaymentQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadExpenseReimbursementPayments">查询</el-button>
          <el-button :disabled="!canRead" @click="resetExpensePaymentFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="expensePaymentError"
        type="error"
        :closable="false"
        show-icon
        :title="expensePaymentError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无费用(报销)支付查看权限" />
      <template v-else>
        <el-table
          :data="expensePaymentRows"
          border
          v-loading="expensePaymentLoading"
          empty-text="暂无费用(报销)支付数据"
        >
          <el-table-column prop="payment_no" label="支付单号" min-width="180" />
          <el-table-column prop="reimbursement_no" label="报销单号" min-width="160" />
          <el-table-column prop="statement_no" label="对账单号" min-width="180" />
          <el-table-column prop="supplier" label="供应商" min-width="150" />
          <el-table-column prop="expense_type" label="费用类型" min-width="140" />
          <el-table-column label="应付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.payable_amount) }}</template>
          </el-table-column>
          <el-table-column label="已付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.paid_amount) }}</template>
          </el-table-column>
          <el-table-column label="待付金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.pending_amount) }}</template>
          </el-table-column>
          <el-table-column label="支付状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentStatusTag(scope.row.payment_status)">
                {{ scope.row.payment_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="payment_date" label="支付日期" min-width="120" />
          <el-table-column prop="payable_account" label="应付科目" min-width="180" />
          <el-table-column prop="cost_center" label="成本中心" min-width="140" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="ref_no" label="关联单据" min-width="150" />
          <el-table-column label="操作" fixed="right" width="300">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:expense-payment-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('支付确认提示')"
              >
                支付确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:expense-payment-review"
                data-guard-state="disabled"
                @click="showGuardedAction('退费复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:expense-payment-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('付款校验')"
              >
                付款校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:expense-payment-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:expense-payment-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="expensePaymentQuery.page"
            :page-size="expensePaymentQuery.page_size"
            :total="expensePaymentTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onExpensePaymentPageChange"
            @size-change="onExpensePaymentSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="bank-deposit-section">
      <template #header>
        <div class="header-row">
          <span>银行存款（TASK-Y59B-P1-03）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读银行存款语义映射"
        description="存款确认、复核、入账、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="bank-deposit-alert"
      />

      <el-form :inline="true" :model="bankDepositQuery" class="bank-deposit-filter-form">
        <el-form-item label="存款单号">
          <el-input v-model="bankDepositQuery.deposit_no" clearable placeholder="请输入存款单号" />
        </el-form-item>
        <el-form-item label="对账单号">
          <el-input v-model="bankDepositQuery.statement_no" clearable placeholder="请输入对账单号" />
        </el-form-item>
        <el-form-item label="开户行">
          <el-input v-model="bankDepositQuery.bank_name" clearable placeholder="请输入开户行" />
        </el-form-item>
        <el-form-item label="账户名称">
          <el-input v-model="bankDepositQuery.account_name" clearable placeholder="请输入账户名称" />
        </el-form-item>
        <el-form-item label="存款状态">
          <el-select v-model="bankDepositQuery.deposit_status" clearable placeholder="请选择存款状态" style="width: 170px">
            <el-option label="待入账" value="待入账" />
            <el-option label="处理中" value="处理中" />
            <el-option label="已入账" value="已入账" />
            <el-option label="已作废" value="已作废" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select v-model="bankDepositQuery.review_status" clearable placeholder="请选择复核状态" style="width: 170px">
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="bankDepositQuery.keyword"
            clearable
            placeholder="存款单号/开户行/账户名称/经办人"
            style="width: 280px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="bankDepositQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="bankDepositQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadBankDeposits">查询</el-button>
          <el-button :disabled="!canRead" @click="resetBankDepositFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="bankDepositError"
        type="error"
        :closable="false"
        show-icon
        :title="bankDepositError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无银行存款查看权限" />
      <template v-else>
        <el-table
          :data="bankDepositRows"
          border
          v-loading="bankDepositLoading"
          empty-text="暂无银行存款数据"
        >
          <el-table-column prop="deposit_no" label="存款单号" min-width="170" />
          <el-table-column prop="statement_no" label="对账单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="bank_name" label="开户行" min-width="160" />
          <el-table-column prop="account_name" label="账户名称" min-width="140" />
          <el-table-column prop="account_no" label="账号" min-width="150" />
          <el-table-column prop="currency" label="币种" width="80" />
          <el-table-column label="存款金额" width="120">
            <template #default="scope">{{ formatAmount(scope.row.deposit_amount) }}</template>
          </el-table-column>
          <el-table-column label="已确认金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.confirmed_amount) }}</template>
          </el-table-column>
          <el-table-column label="待确认金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.pending_amount) }}</template>
          </el-table-column>
          <el-table-column label="存款状态" min-width="120">
            <template #default="scope">
              <el-tag :type="bankDepositStatusTag(scope.row.deposit_status)">
                {{ scope.row.deposit_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="deposit_date" label="存款日期" min-width="120" />
          <el-table-column prop="voucher_no" label="凭证号" min-width="140" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="160" />
          <el-table-column label="操作" fixed="right" width="300">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:bank-deposit-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('存款确认提示')"
              >
                存款确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:bank-deposit-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:bank-deposit-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('入账校验')"
              >
                入账校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:bank-deposit-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:bank-deposit-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="bankDepositQuery.page"
            :page-size="bankDepositQuery.page_size"
            :total="bankDepositTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onBankDepositPageChange"
            @size-change="onBankDepositSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="bank-withdrawal-section">
      <template #header>
        <div class="header-row">
          <span>银行取款（TASK-Y59B-P1-04）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读银行取款语义映射"
        description="取款确认、复核、出账、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="bank-withdrawal-alert"
      />

      <el-form :inline="true" :model="bankWithdrawalQuery" class="bank-withdrawal-filter-form">
        <el-form-item label="取款单号">
          <el-input v-model="bankWithdrawalQuery.withdrawal_no" clearable placeholder="请输入取款单号" />
        </el-form-item>
        <el-form-item label="对账单号">
          <el-input v-model="bankWithdrawalQuery.statement_no" clearable placeholder="请输入对账单号" />
        </el-form-item>
        <el-form-item label="开户行">
          <el-input v-model="bankWithdrawalQuery.bank_name" clearable placeholder="请输入开户行" />
        </el-form-item>
        <el-form-item label="账户名称">
          <el-input v-model="bankWithdrawalQuery.account_name" clearable placeholder="请输入账户名称" />
        </el-form-item>
        <el-form-item label="取款状态">
          <el-select
            v-model="bankWithdrawalQuery.withdrawal_status"
            clearable
            placeholder="请选择取款状态"
            style="width: 170px"
          >
            <el-option label="待出账" value="待出账" />
            <el-option label="处理中" value="处理中" />
            <el-option label="已出账" value="已出账" />
            <el-option label="已作废" value="已作废" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="bankWithdrawalQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="bankWithdrawalQuery.keyword"
            clearable
            placeholder="取款单号/开户行/账户名称/经办人"
            style="width: 280px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="bankWithdrawalQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="bankWithdrawalQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadBankWithdrawals">查询</el-button>
          <el-button :disabled="!canRead" @click="resetBankWithdrawalFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="bankWithdrawalError"
        type="error"
        :closable="false"
        show-icon
        :title="bankWithdrawalError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无银行取款查看权限" />
      <template v-else>
        <el-table
          :data="bankWithdrawalRows"
          border
          v-loading="bankWithdrawalLoading"
          empty-text="暂无银行取款数据"
        >
          <el-table-column prop="withdrawal_no" label="取款单号" min-width="170" />
          <el-table-column prop="statement_no" label="对账单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="bank_name" label="开户行" min-width="160" />
          <el-table-column prop="account_name" label="账户名称" min-width="140" />
          <el-table-column prop="account_no" label="账号" min-width="150" />
          <el-table-column prop="currency" label="币种" width="80" />
          <el-table-column label="取款金额" width="120">
            <template #default="scope">{{ formatAmount(scope.row.withdrawal_amount) }}</template>
          </el-table-column>
          <el-table-column label="已出账金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.transferred_amount) }}</template>
          </el-table-column>
          <el-table-column label="待出账金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.pending_amount) }}</template>
          </el-table-column>
          <el-table-column label="取款状态" min-width="120">
            <template #default="scope">
              <el-tag :type="bankWithdrawalStatusTag(scope.row.withdrawal_status)">
                {{ scope.row.withdrawal_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="withdrawal_date" label="取款日期" min-width="120" />
          <el-table-column prop="voucher_no" label="凭证号" min-width="140" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="160" />
          <el-table-column label="操作" fixed="right" width="300">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:bank-withdrawal-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('取款确认提示')"
              >
                取款确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:bank-withdrawal-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:bank-withdrawal-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('出账校验')"
              >
                出账校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:bank-withdrawal-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:bank-withdrawal-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="bankWithdrawalQuery.page"
            :page-size="bankWithdrawalQuery.page_size"
            :total="bankWithdrawalTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onBankWithdrawalPageChange"
            @size-change="onBankWithdrawalSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="customer-evaluation-section">
      <template #header>
        <div class="header-row">
          <span>客户评估表（TASK-Y59B-P1-05）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读客户评估表语义映射"
        description="评估确认、复核、评分调整、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="customer-evaluation-alert"
      />

      <el-form :inline="true" :model="customerEvaluationQuery" class="customer-evaluation-filter-form">
        <el-form-item label="评估单号">
          <el-input v-model="customerEvaluationQuery.evaluation_no" clearable placeholder="请输入评估单号" />
        </el-form-item>
        <el-form-item label="对账单号">
          <el-input v-model="customerEvaluationQuery.statement_no" clearable placeholder="请输入对账单号" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="customerEvaluationQuery.customer_name" clearable placeholder="请输入客户名称" />
        </el-form-item>
        <el-form-item label="评估人">
          <el-input v-model="customerEvaluationQuery.assessor" clearable placeholder="请输入评估人" />
        </el-form-item>
        <el-form-item label="评分等级">
          <el-select v-model="customerEvaluationQuery.score_level" clearable placeholder="请选择评分等级" style="width: 170px">
            <el-option label="A" value="A" />
            <el-option label="B" value="B" />
            <el-option label="C" value="C" />
            <el-option label="D" value="D" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="customerEvaluationQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="customerEvaluationQuery.keyword"
            clearable
            placeholder="评估单号/客户名称/客户编码/评估人"
            style="width: 300px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="customerEvaluationQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="customerEvaluationQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadCustomerEvaluations">查询</el-button>
          <el-button :disabled="!canRead" @click="resetCustomerEvaluationFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="customerEvaluationError"
        type="error"
        :closable="false"
        show-icon
        :title="customerEvaluationError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无客户评估表查看权限" />
      <template v-else>
        <el-table
          :data="customerEvaluationRows"
          border
          v-loading="customerEvaluationLoading"
          empty-text="暂无客户评估表数据"
        >
          <el-table-column prop="evaluation_no" label="评估单号" min-width="170" />
          <el-table-column prop="statement_no" label="对账单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="customer_name" label="客户名称" min-width="160" />
          <el-table-column prop="customer_code" label="客户编码" min-width="130" />
          <el-table-column prop="assessor" label="评估人" min-width="110" />
          <el-table-column label="评分" width="100">
            <template #default="scope">{{ formatAmount(scope.row.score) }}</template>
          </el-table-column>
          <el-table-column label="评分等级" min-width="110">
            <template #default="scope">
              <el-tag :type="customerEvaluationScoreTag(scope.row.score_level)">
                {{ scope.row.score_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="跟进状态" min-width="120">
            <template #default="scope">
              <el-tag :type="followUpStatusTag(scope.row.follow_up_status)">
                {{ scope.row.follow_up_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="evaluation_date" label="评估日期" min-width="120" />
          <el-table-column prop="expiry_date" label="到期日期" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="180" />
          <el-table-column label="操作" fixed="right" width="320">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:customer-evaluation-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('评估确认提示')"
              >
                评估确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:customer-evaluation-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:customer-evaluation-adjust"
                data-guard-state="disabled"
                @click="showGuardedAction('评分校验')"
              >
                评分校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-evaluation-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-evaluation-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="customerEvaluationQuery.page"
            :page-size="customerEvaluationQuery.page_size"
            :total="customerEvaluationTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onCustomerEvaluationPageChange"
            @size-change="onCustomerEvaluationSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="customer-reconciliation-section">
      <template #header>
        <div class="header-row">
          <span>客户对账表（TASK-Y64B-P1-01）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读客户对账表语义映射"
        description="对账确认、复核、结算、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="customer-reconciliation-alert"
      />

      <el-form :inline="true" :model="customerReconciliationQuery" class="customer-reconciliation-filter-form">
        <el-form-item label="对账单号">
          <el-input
            v-model="customerReconciliationQuery.reconciliation_no"
            clearable
            placeholder="请输入客户对账单号"
          />
        </el-form-item>
        <el-form-item label="业务单号">
          <el-input
            v-model="customerReconciliationQuery.statement_no"
            clearable
            placeholder="请输入关联业务单号"
          />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input
            v-model="customerReconciliationQuery.customer_name"
            clearable
            placeholder="请输入客户名称"
          />
        </el-form-item>
        <el-form-item label="结算状态">
          <el-select
            v-model="customerReconciliationQuery.settlement_status"
            clearable
            placeholder="请选择结算状态"
            style="width: 170px"
          >
            <el-option label="待结算" value="待结算" />
            <el-option label="结算中" value="结算中" />
            <el-option label="已结算" value="已结算" />
            <el-option label="已作废" value="已作废" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="customerReconciliationQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="customerReconciliationQuery.keyword"
            clearable
            placeholder="对账单号/客户名称/客户编码/经办人"
            style="width: 300px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="customerReconciliationQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="customerReconciliationQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadCustomerReconciliations">查询</el-button>
          <el-button :disabled="!canRead" @click="resetCustomerReconciliationFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="customerReconciliationError"
        type="error"
        :closable="false"
        show-icon
        :title="customerReconciliationError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无客户对账表查看权限" />
      <template v-else>
        <el-table
          :data="customerReconciliationRows"
          border
          v-loading="customerReconciliationLoading"
          empty-text="暂无客户对账表数据"
        >
          <el-table-column prop="reconciliation_no" label="对账单号" min-width="180" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="customer_name" label="客户名称" min-width="160" />
          <el-table-column prop="customer_code" label="客户编码" min-width="130" />
          <el-table-column prop="currency" label="币种" width="90" />
          <el-table-column label="应收金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.receivable_amount) }}</template>
          </el-table-column>
          <el-table-column label="已结金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.settled_amount) }}</template>
          </el-table-column>
          <el-table-column label="待结金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.pending_amount) }}</template>
          </el-table-column>
          <el-table-column label="结算状态" min-width="120">
            <template #default="scope">
              <el-tag :type="customerReconciliationSettlementTag(scope.row.settlement_status)">
                {{ scope.row.settlement_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="due_date" label="应收日期" min-width="120" />
          <el-table-column prop="reconciled_at" label="对账日期" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="180" />
          <el-table-column label="操作" fixed="right" width="320">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:customer-reconciliation-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('对账确认提示')"
              >
                对账确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:customer-reconciliation-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:customer-reconciliation-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('结算校验')"
              >
                结算校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-reconciliation-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-reconciliation-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="customerReconciliationQuery.page"
            :page-size="customerReconciliationQuery.page_size"
            :total="customerReconciliationTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onCustomerReconciliationPageChange"
            @size-change="onCustomerReconciliationSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="customer-unpaid-report-section">
      <template #header>
        <div class="header-row">
          <span>客户未收款报表（TASK-Y64B-P1-02）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读客户未收款报表语义映射"
        description="催收、确认收款、复核、结算、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="customer-unpaid-report-alert"
      />

      <el-form :inline="true" :model="customerUnpaidReportQuery" class="customer-unpaid-report-filter-form">
        <el-form-item label="报表单号">
          <el-input
            v-model="customerUnpaidReportQuery.report_no"
            clearable
            placeholder="请输入未收款报表单号"
          />
        </el-form-item>
        <el-form-item label="业务单号">
          <el-input
            v-model="customerUnpaidReportQuery.statement_no"
            clearable
            placeholder="请输入关联业务单号"
          />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input
            v-model="customerUnpaidReportQuery.customer_name"
            clearable
            placeholder="请输入客户名称"
          />
        </el-form-item>
        <el-form-item label="催收状态">
          <el-select
            v-model="customerUnpaidReportQuery.collection_status"
            clearable
            placeholder="请选择催收状态"
            style="width: 170px"
          >
            <el-option label="待催收" value="待催收" />
            <el-option label="催收中" value="催收中" />
            <el-option label="已收款" value="已收款" />
            <el-option label="已作废" value="已作废" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="customerUnpaidReportQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="customerUnpaidReportQuery.keyword"
            clearable
            placeholder="报表单号/客户名称/客户编码/经办人"
            style="width: 300px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="customerUnpaidReportQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="customerUnpaidReportQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadCustomerUnpaidReports">查询</el-button>
          <el-button :disabled="!canRead" @click="resetCustomerUnpaidReportFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="customerUnpaidReportError"
        type="error"
        :closable="false"
        show-icon
        :title="customerUnpaidReportError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无客户未收款报表查看权限" />
      <template v-else>
        <el-table
          :data="customerUnpaidReportRows"
          border
          v-loading="customerUnpaidReportLoading"
          empty-text="暂无客户未收款报表数据"
        >
          <el-table-column prop="report_no" label="报表单号" min-width="180" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="customer_name" label="客户名称" min-width="160" />
          <el-table-column prop="customer_code" label="客户编码" min-width="130" />
          <el-table-column prop="currency" label="币种" width="90" />
          <el-table-column label="应收金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.receivable_amount) }}</template>
          </el-table-column>
          <el-table-column label="已收金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.received_amount) }}</template>
          </el-table-column>
          <el-table-column label="未收金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.unpaid_amount) }}</template>
          </el-table-column>
          <el-table-column prop="overdue_days" label="逾期天数" width="110" />
          <el-table-column label="催收状态" min-width="120">
            <template #default="scope">
              <el-tag :type="customerUnpaidCollectionTag(scope.row.collection_status)">
                {{ scope.row.collection_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="due_date" label="应收日期" min-width="120" />
          <el-table-column prop="last_collection_at" label="最近催收日期" min-width="130" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="180" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:customer-unpaid-report-collect"
                data-guard-state="disabled"
                @click="showGuardedAction('催收提示')"
              >
                催收提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:customer-unpaid-report-receive"
                data-guard-state="disabled"
                @click="showGuardedAction('确认收款提示')"
              >
                确认收款提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:customer-unpaid-report-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:customer-unpaid-report-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('结算校验')"
              >
                结算校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-unpaid-report-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-unpaid-report-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="customerUnpaidReportQuery.page"
            :page-size="customerUnpaidReportQuery.page_size"
            :total="customerUnpaidReportTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onCustomerUnpaidReportPageChange"
            @size-change="onCustomerUnpaidReportSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card
      shadow="never"
      class="customer-receivable-summary-section"
      data-testid="customer-receivable-summary-section"
    >
      <template #header>
        <div class="header-row">
          <span>客户应收账款汇总表（TASK-Y64B-P1-03）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读客户应收账款汇总表语义映射"
        description="对账确认、复核、结算、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="customer-receivable-summary-alert"
      />

      <el-form :inline="true" :model="customerReceivableSummaryQuery" class="customer-receivable-summary-filter-form">
        <el-form-item label="汇总单号">
          <el-input
            v-model="customerReceivableSummaryQuery.summary_no"
            clearable
            placeholder="请输入汇总单号"
          />
        </el-form-item>
        <el-form-item label="业务单号">
          <el-input
            v-model="customerReceivableSummaryQuery.statement_no"
            clearable
            placeholder="请输入关联业务单号"
          />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input
            v-model="customerReceivableSummaryQuery.customer_name"
            clearable
            placeholder="请输入客户名称"
          />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select
            v-model="customerReceivableSummaryQuery.risk_level"
            clearable
            placeholder="请选择风险等级"
            style="width: 170px"
          >
            <el-option label="低风险" value="低风险" />
            <el-option label="中风险" value="中风险" />
            <el-option label="高风险" value="高风险" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="customerReceivableSummaryQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="customerReceivableSummaryQuery.keyword"
            clearable
            placeholder="汇总单号/客户名称/客户编码/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="customerReceivableSummaryQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="customerReceivableSummaryQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadCustomerReceivableSummaries">查询</el-button>
          <el-button :disabled="!canRead" @click="resetCustomerReceivableSummaryFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="customerReceivableSummaryError"
        type="error"
        :closable="false"
        show-icon
        :title="customerReceivableSummaryError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无客户应收账款汇总表查看权限" />
      <template v-else>
        <el-table
          :data="customerReceivableSummaryRows"
          border
          v-loading="customerReceivableSummaryLoading"
          empty-text="暂无客户应收账款汇总表数据"
        >
          <el-table-column prop="summary_no" label="汇总单号" min-width="180" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="customer_name" label="客户名称" min-width="160" />
          <el-table-column prop="customer_code" label="客户编码" min-width="130" />
          <el-table-column prop="currency" label="币种" width="90" />
          <el-table-column label="期初应收" width="130">
            <template #default="scope">{{ formatAmount(scope.row.opening_receivable) }}</template>
          </el-table-column>
          <el-table-column label="本期应收" width="130">
            <template #default="scope">{{ formatAmount(scope.row.current_receivable) }}</template>
          </el-table-column>
          <el-table-column label="本期已收" width="130">
            <template #default="scope">{{ formatAmount(scope.row.received_amount) }}</template>
          </el-table-column>
          <el-table-column label="期末应收" width="130">
            <template #default="scope">{{ formatAmount(scope.row.ending_receivable) }}</template>
          </el-table-column>
          <el-table-column label="账龄30天内" width="140">
            <template #default="scope">{{ formatAmount(scope.row.aging_30) }}</template>
          </el-table-column>
          <el-table-column label="账龄31-60天" width="140">
            <template #default="scope">{{ formatAmount(scope.row.aging_60) }}</template>
          </el-table-column>
          <el-table-column label="账龄90天以上" width="150">
            <template #default="scope">{{ formatAmount(scope.row.aging_90_plus) }}</template>
          </el-table-column>
          <el-table-column label="风险等级" min-width="120">
            <template #default="scope">
              <el-tag :type="customerReceivableRiskTag(scope.row.risk_level)">
                {{ scope.row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="summary_date" label="汇总日期" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="200" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:customer-receivable-summary-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('对账确认提示')"
              >
                对账确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:customer-receivable-summary-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:customer-receivable-summary-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('结算校验')"
              >
                结算校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-receivable-summary-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:customer-receivable-summary-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="customerReceivableSummaryQuery.page"
            :page-size="customerReceivableSummaryQuery.page_size"
            :total="customerReceivableSummaryTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onCustomerReceivableSummaryPageChange"
            @size-change="onCustomerReceivableSummarySizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="factory-evaluation-section" data-testid="factory-evaluation-section">
      <template #header>
        <div class="header-row">
          <span>加工厂评估表（TASK-Y64B-P1-04）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读加工厂评估表语义映射"
        description="评估确认、复核、评级调整、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="factory-evaluation-alert"
      />

      <el-form :inline="true" :model="factoryEvaluationQuery" class="factory-evaluation-filter-form">
        <el-form-item label="评估单号">
          <el-input v-model="factoryEvaluationQuery.evaluation_no" clearable placeholder="请输入评估单号" />
        </el-form-item>
        <el-form-item label="关联业务单号">
          <el-input v-model="factoryEvaluationQuery.statement_no" clearable placeholder="请输入关联业务单号" />
        </el-form-item>
        <el-form-item label="加工厂名称">
          <el-input v-model="factoryEvaluationQuery.factory_name" clearable placeholder="请输入加工厂名称" />
        </el-form-item>
        <el-form-item label="评估人">
          <el-input v-model="factoryEvaluationQuery.assessor" clearable placeholder="请输入评估人" />
        </el-form-item>
        <el-form-item label="评分等级">
          <el-select v-model="factoryEvaluationQuery.score_level" clearable placeholder="请选择评分等级" style="width: 170px">
            <el-option label="A" value="A" />
            <el-option label="B" value="B" />
            <el-option label="C" value="C" />
            <el-option label="D" value="D" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select v-model="factoryEvaluationQuery.review_status" clearable placeholder="请选择复核状态" style="width: 170px">
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="factoryEvaluationQuery.keyword"
            clearable
            placeholder="评估单号/加工厂名称/加工厂编码/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="factoryEvaluationQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="factoryEvaluationQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadFactoryEvaluations">查询</el-button>
          <el-button :disabled="!canRead" @click="resetFactoryEvaluationFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="factoryEvaluationError"
        type="error"
        :closable="false"
        show-icon
        :title="factoryEvaluationError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无加工厂评估表查看权限" />
      <template v-else>
        <el-table :data="factoryEvaluationRows" border v-loading="factoryEvaluationLoading" empty-text="暂无加工厂评估表数据">
          <el-table-column prop="evaluation_no" label="评估单号" min-width="170" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column prop="factory_name" label="加工厂名称" min-width="170" />
          <el-table-column prop="factory_code" label="加工厂编码" min-width="130" />
          <el-table-column prop="assessor" label="评估人" min-width="110" />
          <el-table-column label="评分" width="100">
            <template #default="scope">{{ scope.row.score }}</template>
          </el-table-column>
          <el-table-column label="评分等级" min-width="110">
            <template #default="scope">
              <el-tag :type="customerEvaluationScoreTag(scope.row.score_level)">
                {{ scope.row.score_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="跟进状态" min-width="120">
            <template #default="scope">
              <el-tag :type="followUpStatusTag(scope.row.follow_up_status)">
                {{ scope.row.follow_up_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="evaluation_date" label="评估日期" min-width="120" />
          <el-table-column prop="expiry_date" label="有效截止" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:factory-evaluation-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('评估确认提示')"
              >
                评估确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:factory-evaluation-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:factory-evaluation-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('评级校验')"
              >
                评级校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:factory-evaluation-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:factory-evaluation-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="factoryEvaluationQuery.page"
            :page-size="factoryEvaluationQuery.page_size"
            :total="factoryEvaluationTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onFactoryEvaluationPageChange"
            @size-change="onFactoryEvaluationSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card
      shadow="never"
      class="factory-reconciliation-section"
      data-testid="factory-reconciliation-section"
    >
      <template #header>
        <div class="header-row">
          <span>加工厂对账表（TASK-Y64B-P1-05）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读加工厂对账表语义映射"
        description="对账确认、复核、结算、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="factory-reconciliation-alert"
      />

      <el-form :inline="true" :model="factoryReconciliationQuery" class="factory-reconciliation-filter-form">
        <el-form-item label="对账单号">
          <el-input v-model="factoryReconciliationQuery.reconciliation_no" clearable placeholder="请输入加工厂对账单号" />
        </el-form-item>
        <el-form-item label="关联业务单号">
          <el-input v-model="factoryReconciliationQuery.statement_no" clearable placeholder="请输入关联业务单号" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="factoryReconciliationQuery.supplier" clearable placeholder="请输入供应商名称" />
        </el-form-item>
        <el-form-item label="加工厂名称">
          <el-input v-model="factoryReconciliationQuery.factory_name" clearable placeholder="请输入加工厂名称" />
        </el-form-item>
        <el-form-item label="对账状态">
          <el-select
            v-model="factoryReconciliationQuery.settlement_status"
            clearable
            placeholder="请选择对账状态"
            style="width: 170px"
          >
            <el-option label="待对账" value="待对账" />
            <el-option label="对账中" value="对账中" />
            <el-option label="已对账" value="已对账" />
            <el-option label="已作废" value="已作废" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="factoryReconciliationQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="factoryReconciliationQuery.keyword"
            clearable
            placeholder="对账单号/供应商/加工厂编码/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="factoryReconciliationQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="factoryReconciliationQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadFactoryReconciliations">查询</el-button>
          <el-button :disabled="!canRead" @click="resetFactoryReconciliationFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="factoryReconciliationError"
        type="error"
        :closable="false"
        show-icon
        :title="factoryReconciliationError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无加工厂对账表查看权限" />
      <template v-else>
        <el-table
          :data="factoryReconciliationRows"
          border
          v-loading="factoryReconciliationLoading"
          empty-text="暂无加工厂对账表数据"
        >
          <el-table-column prop="reconciliation_no" label="对账单号" min-width="170" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column prop="factory_name" label="加工厂名称" min-width="170" />
          <el-table-column prop="factory_code" label="加工厂编码" min-width="130" />
          <el-table-column prop="currency" label="币种" width="90" />
          <el-table-column label="对账金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.reconciliation_amount) }}</template>
          </el-table-column>
          <el-table-column label="已结金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.settled_amount) }}</template>
          </el-table-column>
          <el-table-column label="待结金额" width="130">
            <template #default="scope">{{ formatAmount(scope.row.pending_amount) }}</template>
          </el-table-column>
          <el-table-column label="对账状态" min-width="120">
            <template #default="scope">
              <el-tag :type="factoryReconciliationSettlementTag(scope.row.settlement_status)">
                {{ scope.row.settlement_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="跟进状态" min-width="120">
            <template #default="scope">
              <el-tag :type="followUpStatusTag(scope.row.follow_up_status)">
                {{ scope.row.follow_up_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reconciled_at" label="对账日期" min-width="120" />
          <el-table-column prop="due_date" label="到期日期" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:factory-reconciliation-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('对账确认提示')"
              >
                对账确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:factory-reconciliation-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:factory-reconciliation-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('结算校验')"
              >
                结算校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:factory-reconciliation-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:factory-reconciliation-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="factoryReconciliationQuery.page"
            :page-size="factoryReconciliationQuery.page_size"
            :total="factoryReconciliationTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onFactoryReconciliationPageChange"
            @size-change="onFactoryReconciliationSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card
      shadow="never"
      class="factory-payable-summary-section"
      data-testid="factory-payable-summary-section"
    >
      <template #header>
        <div class="header-row">
          <span>加工厂应付账款汇总表（TASK-Y69B-P1-01）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读加工厂应付账款汇总表语义映射"
        description="付款确认、复核、付款校验、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="factory-payable-summary-alert"
      />

      <el-form :inline="true" :model="factoryPayableSummaryQuery" class="factory-payable-summary-filter-form">
        <el-form-item label="汇总单号">
          <el-input v-model="factoryPayableSummaryQuery.summary_no" clearable placeholder="请输入汇总单号" />
        </el-form-item>
        <el-form-item label="关联业务单号">
          <el-input v-model="factoryPayableSummaryQuery.statement_no" clearable placeholder="请输入关联业务单号" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="factoryPayableSummaryQuery.supplier" clearable placeholder="请输入供应商名称" />
        </el-form-item>
        <el-form-item label="加工厂名称">
          <el-input v-model="factoryPayableSummaryQuery.factory_name" clearable placeholder="请输入加工厂名称" />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select
            v-model="factoryPayableSummaryQuery.risk_level"
            clearable
            placeholder="请选择风险等级"
            style="width: 170px"
          >
            <el-option label="低风险" value="低风险" />
            <el-option label="中风险" value="中风险" />
            <el-option label="高风险" value="高风险" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="factoryPayableSummaryQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="factoryPayableSummaryQuery.keyword"
            clearable
            placeholder="汇总单号/供应商/加工厂编码/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="factoryPayableSummaryQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="factoryPayableSummaryQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadFactoryPayableSummaries">查询</el-button>
          <el-button :disabled="!canRead" @click="resetFactoryPayableSummaryFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="factoryPayableSummaryError"
        type="error"
        :closable="false"
        show-icon
        :title="factoryPayableSummaryError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无加工厂应付账款汇总表查看权限" />
      <template v-else>
        <el-table
          :data="factoryPayableSummaryRows"
          border
          v-loading="factoryPayableSummaryLoading"
          empty-text="暂无加工厂应付账款汇总表数据"
        >
          <el-table-column prop="summary_no" label="汇总单号" min-width="170" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column prop="factory_name" label="加工厂名称" min-width="170" />
          <el-table-column prop="factory_code" label="加工厂编码" min-width="130" />
          <el-table-column prop="currency" label="币种" width="90" />
          <el-table-column label="期初应付" width="130">
            <template #default="scope">{{ formatAmount(scope.row.opening_payable) }}</template>
          </el-table-column>
          <el-table-column label="本期应付" width="130">
            <template #default="scope">{{ formatAmount(scope.row.current_payable) }}</template>
          </el-table-column>
          <el-table-column label="本期已付" width="130">
            <template #default="scope">{{ formatAmount(scope.row.paid_amount) }}</template>
          </el-table-column>
          <el-table-column label="期末应付" width="130">
            <template #default="scope">{{ formatAmount(scope.row.ending_payable) }}</template>
          </el-table-column>
          <el-table-column label="账龄30天内" width="140">
            <template #default="scope">{{ formatAmount(scope.row.aging_30) }}</template>
          </el-table-column>
          <el-table-column label="账龄31-60天" width="140">
            <template #default="scope">{{ formatAmount(scope.row.aging_60) }}</template>
          </el-table-column>
          <el-table-column label="账龄90天以上" width="150">
            <template #default="scope">{{ formatAmount(scope.row.aging_90_plus) }}</template>
          </el-table-column>
          <el-table-column label="风险等级" min-width="120">
            <template #default="scope">
              <el-tag :type="customerReceivableRiskTag(scope.row.risk_level)">
                {{ scope.row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="summary_date" label="汇总日期" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:factory-payable-summary-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('付款确认提示')"
              >
                付款确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:factory-payable-summary-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:factory-payable-summary-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('付款校验')"
              >
                付款校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:factory-payable-summary-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:factory-payable-summary-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="factoryPayableSummaryQuery.page"
            :page-size="factoryPayableSummaryQuery.page_size"
            :total="factoryPayableSummaryTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onFactoryPayableSummaryPageChange"
            @size-change="onFactoryPayableSummarySizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="supplier-evaluation-section" data-testid="supplier-evaluation-section">
      <template #header>
        <div class="header-row">
          <span>供应商评估表（TASK-Y69B-P1-02）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读供应商评估表语义映射"
        description="评估确认、复核、评级校验、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="supplier-evaluation-alert"
      />

      <el-form :inline="true" :model="supplierEvaluationQuery" class="supplier-evaluation-filter-form">
        <el-form-item label="评估单号">
          <el-input v-model="supplierEvaluationQuery.evaluation_no" clearable placeholder="请输入评估单号" />
        </el-form-item>
        <el-form-item label="关联业务单号">
          <el-input v-model="supplierEvaluationQuery.statement_no" clearable placeholder="请输入关联业务单号" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="supplierEvaluationQuery.supplier" clearable placeholder="请输入供应商名称" />
        </el-form-item>
        <el-form-item label="评估人">
          <el-input v-model="supplierEvaluationQuery.assessor" clearable placeholder="请输入评估人" />
        </el-form-item>
        <el-form-item label="评分等级">
          <el-select v-model="supplierEvaluationQuery.score_level" clearable placeholder="请选择评分等级" style="width: 170px">
            <el-option label="A" value="A" />
            <el-option label="B" value="B" />
            <el-option label="C" value="C" />
            <el-option label="D" value="D" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="supplierEvaluationQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="supplierEvaluationQuery.keyword"
            clearable
            placeholder="评估单号/供应商名称/供应商编码/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="supplierEvaluationQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="supplierEvaluationQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadSupplierEvaluations">查询</el-button>
          <el-button :disabled="!canRead" @click="resetSupplierEvaluationFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="supplierEvaluationError"
        type="error"
        :closable="false"
        show-icon
        :title="supplierEvaluationError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无供应商评估表查看权限" />
      <template v-else>
        <el-table :data="supplierEvaluationRows" border v-loading="supplierEvaluationLoading" empty-text="暂无供应商评估表数据">
          <el-table-column prop="evaluation_no" label="评估单号" min-width="170" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="130" />
          <el-table-column prop="supplier" label="供应商" min-width="150" />
          <el-table-column prop="supplier_code" label="供应商编码" min-width="130" />
          <el-table-column prop="assessor" label="评估人" min-width="110" />
          <el-table-column label="评分" width="100">
            <template #default="scope">{{ scope.row.score }}</template>
          </el-table-column>
          <el-table-column label="评分等级" min-width="110">
            <template #default="scope">
              <el-tag :type="customerEvaluationScoreTag(scope.row.score_level)">
                {{ scope.row.score_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="120">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="跟进状态" min-width="120">
            <template #default="scope">
              <el-tag :type="followUpStatusTag(scope.row.follow_up_status)">
                {{ scope.row.follow_up_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="evaluation_date" label="评估日期" min-width="120" />
          <el-table-column prop="expiry_date" label="有效截止" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:supplier-evaluation-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('评估确认提示')"
              >
                评估确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:supplier-evaluation-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:supplier-evaluation-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('评级校验')"
              >
                评级校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:supplier-evaluation-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:supplier-evaluation-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="supplierEvaluationQuery.page"
            :page-size="supplierEvaluationQuery.page_size"
            :total="supplierEvaluationTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onSupplierEvaluationPageChange"
            @size-change="onSupplierEvaluationSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card
      shadow="never"
      class="supplier-reconciliation-section"
      data-testid="supplier-reconciliation-section"
    >
      <template #header>
        <div class="header-row">
          <span>供应商对账表（TASK-Y69B-P1-03）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读供应商对账表语义映射"
        description="对账确认、复核、对账校验、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="supplier-reconciliation-alert"
      />

      <el-form :inline="true" :model="supplierReconciliationQuery" class="supplier-reconciliation-filter-form">
        <el-form-item label="对账单号">
          <el-input v-model="supplierReconciliationQuery.reconciliation_no" clearable placeholder="请输入对账单号" />
        </el-form-item>
        <el-form-item label="关联业务单号">
          <el-input v-model="supplierReconciliationQuery.statement_no" clearable placeholder="请输入关联业务单号" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="supplierReconciliationQuery.supplier" clearable placeholder="请输入供应商名称" />
        </el-form-item>
        <el-form-item label="供应商编码">
          <el-input v-model="supplierReconciliationQuery.supplier_code" clearable placeholder="请输入供应商编码" />
        </el-form-item>
        <el-form-item label="结算状态">
          <el-select
            v-model="supplierReconciliationQuery.settlement_status"
            clearable
            placeholder="请选择结算状态"
            style="width: 170px"
          >
            <el-option label="未结算" value="未结算" />
            <el-option label="部分结算" value="部分结算" />
            <el-option label="已结算" value="已结算" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="supplierReconciliationQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="supplierReconciliationQuery.keyword"
            clearable
            placeholder="对账单号/供应商/供应商编码/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="supplierReconciliationQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="supplierReconciliationQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadSupplierReconciliations">查询</el-button>
          <el-button :disabled="!canRead" @click="resetSupplierReconciliationFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="supplierReconciliationError"
        type="error"
        :closable="false"
        show-icon
        :title="supplierReconciliationError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无供应商对账表查看权限" />
      <template v-else>
        <el-table
          :data="supplierReconciliationRows"
          border
          v-loading="supplierReconciliationLoading"
          empty-text="暂无供应商对账表数据"
        >
          <el-table-column prop="reconciliation_no" label="对账单号" min-width="170" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="120" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column prop="supplier_code" label="供应商编码" min-width="130" />
          <el-table-column prop="currency" label="币种" width="80" />
          <el-table-column label="对账金额" min-width="120">
            <template #default="scope">{{ formatAmount(scope.row.reconciliation_amount) }}</template>
          </el-table-column>
          <el-table-column label="已结算金额" min-width="120">
            <template #default="scope">{{ formatAmount(scope.row.settled_amount) }}</template>
          </el-table-column>
          <el-table-column label="待结算金额" min-width="120">
            <template #default="scope">{{ formatAmount(scope.row.pending_amount) }}</template>
          </el-table-column>
          <el-table-column label="结算状态" min-width="110">
            <template #default="scope">
              <el-tag :type="factoryReconciliationSettlementTag(scope.row.settlement_status)">
                {{ scope.row.settlement_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="110">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="跟进状态" min-width="110">
            <template #default="scope">
              <el-tag :type="followUpStatusTag(scope.row.follow_up_status)">
                {{ scope.row.follow_up_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="reconciled_at" label="对账日期" min-width="120" />
          <el-table-column prop="due_date" label="到期日期" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:supplier-reconciliation-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('对账确认提示')"
              >
                对账确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:supplier-reconciliation-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:supplier-reconciliation-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('对账校验')"
              >
                对账校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:supplier-reconciliation-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:supplier-reconciliation-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="supplierReconciliationQuery.page"
            :page-size="supplierReconciliationQuery.page_size"
            :total="supplierReconciliationTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onSupplierReconciliationPageChange"
            @size-change="onSupplierReconciliationSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card
      shadow="never"
      class="supplier-payable-summary-section"
      data-testid="supplier-payable-summary-section"
    >
      <template #header>
        <div class="header-row">
          <span>供应商应付账款汇总表（TASK-Y69B-P1-04）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读供应商应付账款汇总表语义映射"
        description="汇总确认、复核、风险校验、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="supplier-payable-summary-alert"
      />

      <el-form :inline="true" :model="supplierPayableSummaryQuery" class="supplier-payable-summary-filter-form">
        <el-form-item label="汇总单号">
          <el-input v-model="supplierPayableSummaryQuery.summary_no" clearable placeholder="请输入汇总单号" />
        </el-form-item>
        <el-form-item label="关联业务单号">
          <el-input v-model="supplierPayableSummaryQuery.statement_no" clearable placeholder="请输入关联业务单号" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="supplierPayableSummaryQuery.supplier" clearable placeholder="请输入供应商名称" />
        </el-form-item>
        <el-form-item label="供应商编码">
          <el-input v-model="supplierPayableSummaryQuery.supplier_code" clearable placeholder="请输入供应商编码" />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select
            v-model="supplierPayableSummaryQuery.risk_level"
            clearable
            placeholder="请选择风险等级"
            style="width: 170px"
          >
            <el-option label="高风险" value="高风险" />
            <el-option label="中风险" value="中风险" />
            <el-option label="低风险" value="低风险" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="supplierPayableSummaryQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="待复核" value="待复核" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="supplierPayableSummaryQuery.keyword"
            clearable
            placeholder="汇总单号/供应商/供应商编码/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="supplierPayableSummaryQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="supplierPayableSummaryQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadSupplierPayableSummaries">查询</el-button>
          <el-button :disabled="!canRead" @click="resetSupplierPayableSummaryFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="supplierPayableSummaryError"
        type="error"
        :closable="false"
        show-icon
        :title="supplierPayableSummaryError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无供应商应付账款汇总表查看权限" />
      <template v-else>
        <el-table
          :data="supplierPayableSummaryRows"
          border
          v-loading="supplierPayableSummaryLoading"
          empty-text="暂无供应商应付账款汇总表数据"
        >
          <el-table-column prop="summary_no" label="汇总单号" min-width="170" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="120" />
          <el-table-column prop="supplier" label="供应商" min-width="140" />
          <el-table-column prop="supplier_code" label="供应商编码" min-width="130" />
          <el-table-column prop="currency" label="币种" width="80" />
          <el-table-column label="期初应付" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.opening_payable) }}</template>
          </el-table-column>
          <el-table-column label="本期新增应付" min-width="120">
            <template #default="scope">{{ formatAmount(scope.row.current_payable) }}</template>
          </el-table-column>
          <el-table-column label="本期已付" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.paid_amount) }}</template>
          </el-table-column>
          <el-table-column label="期末应付" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.ending_payable) }}</template>
          </el-table-column>
          <el-table-column label="账龄30天" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.aging_30) }}</template>
          </el-table-column>
          <el-table-column label="账龄60天" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.aging_60) }}</template>
          </el-table-column>
          <el-table-column label="账龄90天+" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.aging_90_plus) }}</template>
          </el-table-column>
          <el-table-column label="风险等级" min-width="110">
            <template #default="scope">
              <el-tag :type="customerReceivableRiskTag(scope.row.risk_level)">
                {{ scope.row.risk_level }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="110">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="跟进状态" min-width="110">
            <template #default="scope">
              <el-tag :type="followUpStatusTag(scope.row.follow_up_status)">
                {{ scope.row.follow_up_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="summary_date" label="汇总日期" min-width="120" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:supplier-payable-summary-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('汇总确认提示')"
              >
                汇总确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:supplier-payable-summary-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:supplier-payable-summary-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('风险校验')"
              >
                风险校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:supplier-payable-summary-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:supplier-payable-summary-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="supplierPayableSummaryQuery.page"
            :page-size="supplierPayableSummaryQuery.page_size"
            :total="supplierPayableSummaryTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onSupplierPayableSummaryPageChange"
            @size-change="onSupplierPayableSummarySizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="bank-ledger-section" data-testid="bank-ledger-section">
      <template #header>
        <div class="header-row">
          <span>银行流水（TASK-Y69B-P1-05）</span>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="只读银行流水语义映射"
        description="入账确认、复核、流水校验、导出、打印等动作保持 guarded 提示，不触发真实写请求。"
        class="bank-ledger-alert"
      />

      <el-form :inline="true" :model="bankLedgerQuery" class="bank-ledger-filter-form">
        <el-form-item label="流水单号">
          <el-input v-model="bankLedgerQuery.ledger_no" clearable placeholder="请输入流水单号" />
        </el-form-item>
        <el-form-item label="关联业务单号">
          <el-input v-model="bankLedgerQuery.statement_no" clearable placeholder="请输入关联业务单号" />
        </el-form-item>
        <el-form-item label="银行">
          <el-input v-model="bankLedgerQuery.bank_name" clearable placeholder="请输入银行名称" />
        </el-form-item>
        <el-form-item label="账户名称">
          <el-input v-model="bankLedgerQuery.account_name" clearable placeholder="请输入账户名称" />
        </el-form-item>
        <el-form-item label="交易类型">
          <el-select
            v-model="bankLedgerQuery.transaction_type"
            clearable
            placeholder="请选择交易类型"
            style="width: 170px"
          >
            <el-option label="收入" value="收入" />
            <el-option label="支出" value="支出" />
            <el-option label="手续费" value="手续费" />
          </el-select>
        </el-form-item>
        <el-form-item label="流水状态">
          <el-select
            v-model="bankLedgerQuery.ledger_status"
            clearable
            placeholder="请选择流水状态"
            style="width: 170px"
          >
            <el-option label="待登记" value="待登记" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已对账" value="已对账" />
            <el-option label="已归档" value="已归档" />
          </el-select>
        </el-form-item>
        <el-form-item label="复核状态">
          <el-select
            v-model="bankLedgerQuery.review_status"
            clearable
            placeholder="请选择复核状态"
            style="width: 170px"
          >
            <el-option label="未开始" value="未开始" />
            <el-option label="复核中" value="复核中" />
            <el-option label="已通过" value="已通过" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="bankLedgerQuery.keyword"
            clearable
            placeholder="流水单号/关联业务单号/银行/凭证号/经办人"
            style="width: 320px"
          />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="bankLedgerQuery.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="bankLedgerQuery.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadBankLedgers">查询</el-button>
          <el-button :disabled="!canRead" @click="resetBankLedgerFilters">重置</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="bankLedgerError"
        type="error"
        :closable="false"
        show-icon
        :title="bankLedgerError"
        class="error-alert"
      />
      <el-empty v-if="!canRead" description="无银行流水查看权限" />
      <template v-else>
        <el-table :data="bankLedgerRows" border v-loading="bankLedgerLoading" empty-text="暂无银行流水数据">
          <el-table-column prop="ledger_no" label="流水单号" min-width="170" />
          <el-table-column prop="statement_no" label="关联业务单号" min-width="170" />
          <el-table-column prop="company" label="公司" min-width="120" />
          <el-table-column prop="bank_name" label="银行" min-width="150" />
          <el-table-column prop="account_name" label="账户名称" min-width="160" />
          <el-table-column prop="account_no" label="账号" min-width="130" />
          <el-table-column prop="currency" label="币种" width="80" />
          <el-table-column prop="transaction_type" label="交易类型" min-width="100" />
          <el-table-column label="借方金额" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.debit_amount) }}</template>
          </el-table-column>
          <el-table-column label="贷方金额" min-width="110">
            <template #default="scope">{{ formatAmount(scope.row.credit_amount) }}</template>
          </el-table-column>
          <el-table-column label="交易后余额" min-width="120">
            <template #default="scope">{{ formatAmount(scope.row.balance_after) }}</template>
          </el-table-column>
          <el-table-column label="流水状态" min-width="100">
            <template #default="scope">
              <el-tag :type="bankLedgerStatusTag(scope.row.ledger_status)">
                {{ scope.row.ledger_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="复核状态" min-width="100">
            <template #default="scope">
              <el-tag :type="paymentReviewTag(scope.row.review_status)">
                {{ scope.row.review_status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="ledger_date" label="流水日期" min-width="120" />
          <el-table-column prop="voucher_no" label="凭证号" min-width="140" />
          <el-table-column prop="owner" label="经办人" min-width="100" />
          <el-table-column prop="remark" label="备注" min-width="220" />
          <el-table-column label="操作" fixed="right" width="380">
            <template #default>
              <el-button
                link
                type="success"
                data-action-type="write"
                data-write-guard="readonly:bank-ledger-confirm"
                data-guard-state="disabled"
                @click="showGuardedAction('入账确认提示')"
              >
                入账确认提示
              </el-button>
              <el-button
                link
                type="warning"
                data-action-type="write"
                data-write-guard="readonly:bank-ledger-review"
                data-guard-state="disabled"
                @click="showGuardedAction('复核提示')"
              >
                复核提示
              </el-button>
              <el-button
                link
                type="primary"
                data-action-type="write"
                data-write-guard="readonly:bank-ledger-verify"
                data-guard-state="disabled"
                @click="showGuardedAction('流水校验')"
              >
                流水校验
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:bank-ledger-export"
                data-guard-state="disabled"
                @click="showGuardedAction('导出')"
              >
                导出
              </el-button>
              <el-button
                link
                type="info"
                data-action-type="write"
                data-write-guard="readonly:bank-ledger-print"
                data-guard-state="disabled"
                @click="showGuardedAction('打印')"
              >
                打印
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="bankLedgerQuery.page"
            :page-size="bankLedgerQuery.page_size"
            :total="bankLedgerTotal"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onBankLedgerPageChange"
            @size-change="onBankLedgerSizeChange"
          />
        </div>
      </template>
    </el-card>

    <el-dialog v-model="createVisible" title="创建加工厂对账单" width="680px">
        <el-form :model="createForm" label-width="120px">
          <el-form-item label="公司">
          <el-input v-model="createForm.company" placeholder="请输入公司名称" />
          </el-form-item>
          <el-form-item label="供应商">
          <el-input v-model="createForm.supplier" placeholder="请输入供应商名称" />
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="createForm.from_date"
              type="date"
              value-format="YYYY-MM-DD"
            placeholder="请选择开始日期"
              style="width: 100%"
            />
          </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
              v-model="createForm.to_date"
              type="date"
              value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="幂等键">
          <el-input v-model="createForm.idempotency_key" placeholder="请输入幂等键" />
          </el-form-item>
        </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" :disabled="!canSubmitCreate" @click="submitCreateStatement">
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createFactoryStatement,
  fetchFactoryStatementBankDeposits,
  fetchFactoryStatementBankLedgers,
  fetchFactoryStatementBankWithdrawals,
  fetchFactoryStatementCustomerEvaluations,
  fetchFactoryStatementFactoryEvaluations,
  fetchFactoryStatementFactoryPayableSummaries,
  fetchFactoryStatementFactoryReconciliations,
  fetchFactoryStatementSupplierPayableSummaries,
  fetchFactoryStatementSupplierReconciliations,
  fetchFactoryStatementSupplierEvaluations,
  fetchFactoryStatementCustomerReceivableSummaries,
  fetchFactoryStatementCustomerReconciliations,
  fetchFactoryStatementCustomerUnpaidReports,
  fetchFactoryStatementExpenseReimbursementPayments,
  fetchFactoryStatements,
  type FactoryStatementBankLedgerItem,
  type FactoryStatementBankDepositItem,
  type FactoryStatementBankWithdrawalItem,
  type FactoryStatementCustomerEvaluationItem,
  type FactoryStatementFactoryEvaluationItem,
  type FactoryStatementFactoryPayableSummaryItem,
  type FactoryStatementFactoryReconciliationItem,
  type FactoryStatementSupplierPayableSummaryItem,
  type FactoryStatementSupplierReconciliationItem,
  type FactoryStatementSupplierEvaluationItem,
  type FactoryStatementCustomerReceivableSummaryItem,
  type FactoryStatementCustomerReconciliationItem,
  type FactoryStatementCustomerUnpaidReportItem,
  type FactoryStatementCreatePayload,
  type FactoryStatementExpenseReimbursementPaymentItem,
  type FactoryStatementListItem,
} from '@/api/factory_statement'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const creating = ref<boolean>(false)
const createVisible = ref<boolean>(false)
const readError = ref<string>('')
const rows = ref<FactoryStatementListItem[]>([])
const total = ref<number>(0)
const expensePaymentLoading = ref<boolean>(false)
const expensePaymentError = ref<string>('')
const expensePaymentRows = ref<FactoryStatementExpenseReimbursementPaymentItem[]>([])
const expensePaymentTotal = ref<number>(0)
const bankDepositLoading = ref<boolean>(false)
const bankDepositError = ref<string>('')
const bankDepositRows = ref<FactoryStatementBankDepositItem[]>([])
const bankDepositTotal = ref<number>(0)
const bankWithdrawalLoading = ref<boolean>(false)
const bankWithdrawalError = ref<string>('')
const bankWithdrawalRows = ref<FactoryStatementBankWithdrawalItem[]>([])
const bankWithdrawalTotal = ref<number>(0)
const bankLedgerLoading = ref<boolean>(false)
const bankLedgerError = ref<string>('')
const bankLedgerRows = ref<FactoryStatementBankLedgerItem[]>([])
const bankLedgerTotal = ref<number>(0)
const customerEvaluationLoading = ref<boolean>(false)
const customerEvaluationError = ref<string>('')
const customerEvaluationRows = ref<FactoryStatementCustomerEvaluationItem[]>([])
const customerEvaluationTotal = ref<number>(0)
const customerReconciliationLoading = ref<boolean>(false)
const customerReconciliationError = ref<string>('')
const customerReconciliationRows = ref<FactoryStatementCustomerReconciliationItem[]>([])
const customerReconciliationTotal = ref<number>(0)
const customerUnpaidReportLoading = ref<boolean>(false)
const customerUnpaidReportError = ref<string>('')
const customerUnpaidReportRows = ref<FactoryStatementCustomerUnpaidReportItem[]>([])
const customerUnpaidReportTotal = ref<number>(0)
const customerReceivableSummaryLoading = ref<boolean>(false)
const customerReceivableSummaryError = ref<string>('')
const customerReceivableSummaryRows = ref<FactoryStatementCustomerReceivableSummaryItem[]>([])
const customerReceivableSummaryTotal = ref<number>(0)
const factoryEvaluationLoading = ref<boolean>(false)
const factoryEvaluationError = ref<string>('')
const factoryEvaluationRows = ref<FactoryStatementFactoryEvaluationItem[]>([])
const factoryEvaluationTotal = ref<number>(0)
const factoryReconciliationLoading = ref<boolean>(false)
const factoryReconciliationError = ref<string>('')
const factoryReconciliationRows = ref<FactoryStatementFactoryReconciliationItem[]>([])
const factoryReconciliationTotal = ref<number>(0)
const factoryPayableSummaryLoading = ref<boolean>(false)
const factoryPayableSummaryError = ref<string>('')
const factoryPayableSummaryRows = ref<FactoryStatementFactoryPayableSummaryItem[]>([])
const factoryPayableSummaryTotal = ref<number>(0)
const supplierEvaluationLoading = ref<boolean>(false)
const supplierEvaluationError = ref<string>('')
const supplierEvaluationRows = ref<FactoryStatementSupplierEvaluationItem[]>([])
const supplierEvaluationTotal = ref<number>(0)
const supplierReconciliationLoading = ref<boolean>(false)
const supplierReconciliationError = ref<string>('')
const supplierReconciliationRows = ref<FactoryStatementSupplierReconciliationItem[]>([])
const supplierReconciliationTotal = ref<number>(0)
const supplierPayableSummaryLoading = ref<boolean>(false)
const supplierPayableSummaryError = ref<string>('')
const supplierPayableSummaryRows = ref<FactoryStatementSupplierPayableSummaryItem[]>([])
const supplierPayableSummaryTotal = ref<number>(0)

const P1_READONLY_MODE = true
const readonlyWriteHint = '当前为只读对账视图，已禁用写动作'

interface SampleOrderReconciliationRow extends FactoryStatementListItem {
  sample_order_no: string
  style_code: string
  factory_name: string
  ordered_at: string
  order_amount: number | null
}

const canRead = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_read)
const canCreate = computed<boolean>(() => permissionStore.state.buttonPermissions.factory_statement_create)
const canCreateAction = computed<boolean>(() => canCreate.value && !P1_READONLY_MODE)

const query = reactive({
  supplier: '',
  statement_status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const expensePaymentQuery = reactive({
  payment_no: '',
  reimbursement_no: '',
  statement_no: '',
  supplier: '',
  payment_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const bankDepositQuery = reactive({
  deposit_no: '',
  statement_no: '',
  bank_name: '',
  account_name: '',
  deposit_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const bankWithdrawalQuery = reactive({
  withdrawal_no: '',
  statement_no: '',
  bank_name: '',
  account_name: '',
  withdrawal_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const bankLedgerQuery = reactive({
  ledger_no: '',
  statement_no: '',
  bank_name: '',
  account_name: '',
  transaction_type: '',
  ledger_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const customerEvaluationQuery = reactive({
  evaluation_no: '',
  statement_no: '',
  customer_name: '',
  assessor: '',
  score_level: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const customerReconciliationQuery = reactive({
  reconciliation_no: '',
  statement_no: '',
  customer_name: '',
  settlement_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const customerUnpaidReportQuery = reactive({
  report_no: '',
  statement_no: '',
  customer_name: '',
  collection_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const customerReceivableSummaryQuery = reactive({
  summary_no: '',
  statement_no: '',
  customer_name: '',
  risk_level: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const factoryEvaluationQuery = reactive({
  evaluation_no: '',
  statement_no: '',
  factory_name: '',
  assessor: '',
  score_level: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const factoryReconciliationQuery = reactive({
  reconciliation_no: '',
  statement_no: '',
  supplier: '',
  factory_name: '',
  settlement_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const factoryPayableSummaryQuery = reactive({
  summary_no: '',
  statement_no: '',
  supplier: '',
  factory_name: '',
  risk_level: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const supplierEvaluationQuery = reactive({
  evaluation_no: '',
  statement_no: '',
  supplier: '',
  assessor: '',
  score_level: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const supplierReconciliationQuery = reactive({
  reconciliation_no: '',
  statement_no: '',
  supplier: '',
  supplier_code: '',
  settlement_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const supplierPayableSummaryQuery = reactive({
  summary_no: '',
  statement_no: '',
  supplier: '',
  supplier_code: '',
  risk_level: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const sampleQuery = reactive({
  sample_order_no: '',
  style_code: '',
  factory_name: '',
  ordered_date_range: [] as string[],
  min_amount: undefined as number | undefined,
  max_amount: undefined as number | undefined,
  status: '',
})

const createForm = reactive({
  company: '',
  supplier: '',
  from_date: '',
  to_date: '',
  idempotency_key: '',
})

const normalizedCreateForm = computed(() => ({
  company: createForm.company.trim(),
  supplier: createForm.supplier.trim(),
  from_date: createForm.from_date || '',
  to_date: createForm.to_date || '',
  idempotency_key: createForm.idempotency_key.trim(),
}))

const createFormValidationError = computed<string | null>(() => {
  if (!normalizedCreateForm.value.company) {
    return '公司不能为空'
  }
  if (!normalizedCreateForm.value.supplier) {
    return '供应商不能为空'
  }
  if (!normalizedCreateForm.value.from_date) {
    return '开始日期不能为空'
  }
  if (!normalizedCreateForm.value.to_date) {
    return '结束日期不能为空'
  }
  if (normalizedCreateForm.value.from_date > normalizedCreateForm.value.to_date) {
    return '开始日期不能晚于结束日期'
  }
  if (!normalizedCreateForm.value.idempotency_key) {
    return '幂等键不能为空'
  }
  return null
})

const canSubmitCreate = computed<boolean>(() => canCreate.value && !createFormValidationError.value)

const normalizeText = (value: string | null | undefined): string => (value || '').trim().toLowerCase()

const normalizeDate = (value: string | null | undefined): string => {
  if (!value) {
    return ''
  }
  const raw = String(value)
  if (raw.includes('T')) {
    return raw.slice(0, 10)
  }
  if (raw.includes(' ')) {
    return raw.slice(0, 10)
  }
  return raw.slice(0, 10)
}

const toNumeric = (value: string | number | null | undefined): number | null => {
  if (value === null || value === undefined || value === '') {
    return null
  }
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

const toSampleRow = (row: FactoryStatementListItem): SampleOrderReconciliationRow => ({
  ...row,
  sample_order_no: row.statement_no || '-',
  style_code: row.purchase_invoice_name || '-',
  factory_name: row.supplier || '-',
  ordered_at: normalizeDate(row.created_at) || '-',
  order_amount: toNumeric(row.net_amount),
})

const withinRange = (value: string, from: string, to: string): boolean => {
  if (!value) {
    return false
  }
  if (from && value < from) {
    return false
  }
  if (to && value > to) {
    return false
  }
  return true
}

const displayRows = computed<SampleOrderReconciliationRow[]>(() => {
  const sampleOrderNeedle = normalizeText(sampleQuery.sample_order_no)
  const styleNeedle = normalizeText(sampleQuery.style_code)
  const factoryNeedle = normalizeText(sampleQuery.factory_name)
  const statusNeedle = normalizeText(sampleQuery.status)
  const from = sampleQuery.ordered_date_range[0] || ''
  const to = sampleQuery.ordered_date_range[1] || ''

  return rows.value
    .map((row) => toSampleRow(row))
    .filter((row) => {
      if (sampleOrderNeedle && !normalizeText(row.sample_order_no).includes(sampleOrderNeedle)) {
        return false
      }
      if (styleNeedle && !normalizeText(row.style_code).includes(styleNeedle)) {
        return false
      }
      if (factoryNeedle && !normalizeText(row.factory_name).includes(factoryNeedle)) {
        return false
      }
      if (statusNeedle && normalizeText(row.statement_status) !== statusNeedle) {
        return false
      }
      if ((from || to) && !withinRange(normalizeDate(row.ordered_at), from, to)) {
        return false
      }

      const amount = row.order_amount
      if (sampleQuery.min_amount !== undefined && sampleQuery.min_amount !== null) {
        if (amount === null || amount < sampleQuery.min_amount) {
          return false
        }
      }
      if (sampleQuery.max_amount !== undefined && sampleQuery.max_amount !== null) {
        if (amount === null || amount > sampleQuery.max_amount) {
          return false
        }
      }
      return true
    })
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const statementStatusLabel = (status: string | null | undefined): string => {
  if (status === 'draft') {
    return '草稿'
  }
  if (status === 'confirmed') {
    return '已确认'
  }
  if (status === 'cancelled') {
    return '已取消'
  }
  if (status === 'payable_draft_created') {
    return '应付草稿已生成'
  }
  return status || '-'
}

const outboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') {
    return '待同步'
  }
  if (status === 'processing') {
    return '同步中'
  }
  if (status === 'succeeded') {
    return '已生成草稿'
  }
  if (status === 'failed') {
    return '同步失败'
  }
  if (status === 'dead') {
    return '同步死信'
  }
  return '-'
}

const statusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === 'draft') {
    return 'warning'
  }
  if (status === 'confirmed') {
    return 'success'
  }
  if (status === 'cancelled') {
    return 'danger'
  }
  return 'info'
}

const paymentStatusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待支付' || status === '审批中') {
    return 'warning'
  }
  if (status === '部分支付') {
    return 'info'
  }
  if (status === '已支付') {
    return 'success'
  }
  return 'info'
}

const paymentReviewTag = (status: string | null | undefined): 'warning' | 'success' | 'info' => {
  if (status === '已通过') {
    return 'success'
  }
  if (status === '复核中') {
    return 'info'
  }
  return 'warning'
}

const bankDepositStatusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待入账') {
    return 'warning'
  }
  if (status === '处理中') {
    return 'info'
  }
  if (status === '已入账') {
    return 'success'
  }
  if (status === '已作废') {
    return 'danger'
  }
  return 'info'
}

const bankWithdrawalStatusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待出账') {
    return 'warning'
  }
  if (status === '处理中') {
    return 'info'
  }
  if (status === '已出账') {
    return 'success'
  }
  if (status === '已作废') {
    return 'danger'
  }
  return 'info'
}

const bankLedgerStatusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待登记') {
    return 'warning'
  }
  if (status === '复核中') {
    return 'info'
  }
  if (status === '已对账') {
    return 'success'
  }
  if (status === '已归档') {
    return 'danger'
  }
  return 'info'
}

const followUpStatusTag = (status: string | null | undefined): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待跟进') {
    return 'warning'
  }
  if (status === '跟进中') {
    return 'info'
  }
  if (status === '已完成') {
    return 'success'
  }
  if (status === '已作废') {
    return 'danger'
  }
  return 'info'
}

const customerEvaluationScoreTag = (level: string | null | undefined): 'success' | 'warning' | 'danger' | 'info' => {
  if (level === 'A') {
    return 'success'
  }
  if (level === 'B') {
    return 'warning'
  }
  if (level === 'C' || level === 'D') {
    return 'danger'
  }
  return 'info'
}

const customerReconciliationSettlementTag = (
  status: string | null | undefined,
): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待结算') {
    return 'warning'
  }
  if (status === '结算中') {
    return 'info'
  }
  if (status === '已结算') {
    return 'success'
  }
  if (status === '已作废') {
    return 'danger'
  }
  return 'info'
}

const customerUnpaidCollectionTag = (
  status: string | null | undefined,
): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待催收') {
    return 'warning'
  }
  if (status === '催收中') {
    return 'info'
  }
  if (status === '已收款') {
    return 'success'
  }
  if (status === '已作废') {
    return 'danger'
  }
  return 'info'
}

const factoryReconciliationSettlementTag = (
  status: string | null | undefined,
): 'warning' | 'success' | 'danger' | 'info' => {
  if (status === '待对账') {
    return 'warning'
  }
  if (status === '对账中') {
    return 'info'
  }
  if (status === '已对账') {
    return 'success'
  }
  if (status === '已作废') {
    return 'danger'
  }
  return 'info'
}

const customerReceivableRiskTag = (
  riskLevel: string | null | undefined,
): 'warning' | 'success' | 'danger' | 'info' => {
  if (riskLevel === '高风险') {
    return 'danger'
  }
  if (riskLevel === '中风险') {
    return 'warning'
  }
  if (riskLevel === '低风险') {
    return 'success'
  }
  return 'info'
}

const buildIdempotencyKey = (prefix: string): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

const openCreateDialog = (): void => {
  if (P1_READONLY_MODE) {
    ElMessage.warning(readonlyWriteHint)
    return
  }
  if (!canCreate.value) {
    ElMessage.error('无创建对账单权限')
    return
  }
  createForm.company = ''
  createForm.supplier = query.supplier.trim()
  createForm.from_date = query.from_date || ''
  createForm.to_date = query.to_date || ''
  createForm.idempotency_key = buildIdempotencyKey('factory-statement-create')
  createVisible.value = true
}

const submitCreateStatement = async (): Promise<void> => {
  if (P1_READONLY_MODE) {
    ElMessage.warning(readonlyWriteHint)
    return
  }
  if (!canCreate.value) {
    ElMessage.error('无创建对账单权限')
    return
  }
  const validationError = createFormValidationError.value
  if (validationError) {
    ElMessage.error(validationError)
    return
  }

  const payload: FactoryStatementCreatePayload = {
    company: normalizedCreateForm.value.company,
    supplier: normalizedCreateForm.value.supplier,
    from_date: normalizedCreateForm.value.from_date,
    to_date: normalizedCreateForm.value.to_date,
    idempotency_key: normalizedCreateForm.value.idempotency_key,
  }

  creating.value = true
  try {
    const result = await createFactoryStatement(payload)
    ElMessage.success(`创建成功：${result.data.statement_no}`)
    createVisible.value = false
    createForm.idempotency_key = buildIdempotencyKey('factory-statement-create')
    await loadRows()
  } catch (error) {
    ElMessage.error((error as Error).message)
  } finally {
    creating.value = false
  }
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
  readError.value = ''
}

const resetExpensePaymentRows = (): void => {
  expensePaymentRows.value = []
  expensePaymentTotal.value = 0
  expensePaymentError.value = ''
}

const resetBankDepositRows = (): void => {
  bankDepositRows.value = []
  bankDepositTotal.value = 0
  bankDepositError.value = ''
}

const resetBankWithdrawalRows = (): void => {
  bankWithdrawalRows.value = []
  bankWithdrawalTotal.value = 0
  bankWithdrawalError.value = ''
}

const resetBankLedgerRows = (): void => {
  bankLedgerRows.value = []
  bankLedgerTotal.value = 0
  bankLedgerError.value = ''
}

const resetCustomerEvaluationRows = (): void => {
  customerEvaluationRows.value = []
  customerEvaluationTotal.value = 0
  customerEvaluationError.value = ''
}

const resetCustomerReconciliationRows = (): void => {
  customerReconciliationRows.value = []
  customerReconciliationTotal.value = 0
  customerReconciliationError.value = ''
}

const resetCustomerUnpaidReportRows = (): void => {
  customerUnpaidReportRows.value = []
  customerUnpaidReportTotal.value = 0
  customerUnpaidReportError.value = ''
}

const resetCustomerReceivableSummaryRows = (): void => {
  customerReceivableSummaryRows.value = []
  customerReceivableSummaryTotal.value = 0
  customerReceivableSummaryError.value = ''
}

const resetFactoryEvaluationRows = (): void => {
  factoryEvaluationRows.value = []
  factoryEvaluationTotal.value = 0
  factoryEvaluationError.value = ''
}

const resetFactoryReconciliationRows = (): void => {
  factoryReconciliationRows.value = []
  factoryReconciliationTotal.value = 0
  factoryReconciliationError.value = ''
}

const resetFactoryPayableSummaryRows = (): void => {
  factoryPayableSummaryRows.value = []
  factoryPayableSummaryTotal.value = 0
  factoryPayableSummaryError.value = ''
}

const resetSupplierEvaluationRows = (): void => {
  supplierEvaluationRows.value = []
  supplierEvaluationTotal.value = 0
  supplierEvaluationError.value = ''
}

const resetSupplierReconciliationRows = (): void => {
  supplierReconciliationRows.value = []
  supplierReconciliationTotal.value = 0
  supplierReconciliationError.value = ''
}

const resetSupplierPayableSummaryRows = (): void => {
  supplierPayableSummaryRows.value = []
  supplierPayableSummaryTotal.value = 0
  supplierPayableSummaryError.value = ''
}

const applySampleFilters = (): void => {
  if (!canRead.value) {
    return
  }
}

const resetSampleFilters = (): void => {
  sampleQuery.sample_order_no = ''
  sampleQuery.style_code = ''
  sampleQuery.factory_name = ''
  sampleQuery.ordered_date_range = []
  sampleQuery.min_amount = undefined
  sampleQuery.max_amount = undefined
  sampleQuery.status = ''
}

const applyPrimaryQuery = async (): Promise<void> => {
  if (!canRead.value) {
    return
  }
  query.page = 1
  await loadRows()
}

const resetPrimaryFilters = async (): Promise<void> => {
  query.supplier = ''
  query.statement_status = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = 20
  await loadRows()
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    return
  }

  loading.value = true
  readError.value = ''
  try {
    const result = await fetchFactoryStatements({
      supplier: query.supplier.trim() || undefined,
      statement_status: query.statement_status || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    readError.value = message
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const loadExpenseReimbursementPayments = async (): Promise<void> => {
  if (!canRead.value) {
    resetExpensePaymentRows()
    return
  }

  expensePaymentLoading.value = true
  expensePaymentError.value = ''
  try {
    const result = await fetchFactoryStatementExpenseReimbursementPayments({
      payment_no: expensePaymentQuery.payment_no.trim() || undefined,
      reimbursement_no: expensePaymentQuery.reimbursement_no.trim() || undefined,
      statement_no: expensePaymentQuery.statement_no.trim() || undefined,
      supplier: expensePaymentQuery.supplier.trim() || undefined,
      payment_status: expensePaymentQuery.payment_status || undefined,
      review_status: expensePaymentQuery.review_status || undefined,
      keyword: expensePaymentQuery.keyword.trim() || undefined,
      from_date: expensePaymentQuery.from_date || undefined,
      to_date: expensePaymentQuery.to_date || undefined,
      page: expensePaymentQuery.page,
      page_size: expensePaymentQuery.page_size,
    })
    expensePaymentRows.value = result.data.items
    expensePaymentTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    expensePaymentError.value = `费用(报销)支付加载失败：${message}`
    ElMessage.error(expensePaymentError.value)
  } finally {
    expensePaymentLoading.value = false
  }
}

const loadBankDeposits = async (): Promise<void> => {
  if (!canRead.value) {
    resetBankDepositRows()
    return
  }

  bankDepositLoading.value = true
  bankDepositError.value = ''
  try {
    const result = await fetchFactoryStatementBankDeposits({
      deposit_no: bankDepositQuery.deposit_no.trim() || undefined,
      statement_no: bankDepositQuery.statement_no.trim() || undefined,
      bank_name: bankDepositQuery.bank_name.trim() || undefined,
      account_name: bankDepositQuery.account_name.trim() || undefined,
      deposit_status: bankDepositQuery.deposit_status || undefined,
      review_status: bankDepositQuery.review_status || undefined,
      keyword: bankDepositQuery.keyword.trim() || undefined,
      from_date: bankDepositQuery.from_date || undefined,
      to_date: bankDepositQuery.to_date || undefined,
      page: bankDepositQuery.page,
      page_size: bankDepositQuery.page_size,
    })
    bankDepositRows.value = result.data.items
    bankDepositTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    bankDepositError.value = `银行存款加载失败：${message}`
    ElMessage.error(bankDepositError.value)
  } finally {
    bankDepositLoading.value = false
  }
}

const loadBankWithdrawals = async (): Promise<void> => {
  if (!canRead.value) {
    resetBankWithdrawalRows()
    return
  }

  bankWithdrawalLoading.value = true
  bankWithdrawalError.value = ''
  try {
    const result = await fetchFactoryStatementBankWithdrawals({
      withdrawal_no: bankWithdrawalQuery.withdrawal_no.trim() || undefined,
      statement_no: bankWithdrawalQuery.statement_no.trim() || undefined,
      bank_name: bankWithdrawalQuery.bank_name.trim() || undefined,
      account_name: bankWithdrawalQuery.account_name.trim() || undefined,
      withdrawal_status: bankWithdrawalQuery.withdrawal_status || undefined,
      review_status: bankWithdrawalQuery.review_status || undefined,
      keyword: bankWithdrawalQuery.keyword.trim() || undefined,
      from_date: bankWithdrawalQuery.from_date || undefined,
      to_date: bankWithdrawalQuery.to_date || undefined,
      page: bankWithdrawalQuery.page,
      page_size: bankWithdrawalQuery.page_size,
    })
    bankWithdrawalRows.value = result.data.items
    bankWithdrawalTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    bankWithdrawalError.value = `银行取款加载失败：${message}`
    ElMessage.error(bankWithdrawalError.value)
  } finally {
    bankWithdrawalLoading.value = false
  }
}

const loadBankLedgers = async (): Promise<void> => {
  if (!canRead.value) {
    resetBankLedgerRows()
    return
  }

  bankLedgerLoading.value = true
  bankLedgerError.value = ''
  try {
    const result = await fetchFactoryStatementBankLedgers({
      ledger_no: bankLedgerQuery.ledger_no.trim() || undefined,
      statement_no: bankLedgerQuery.statement_no.trim() || undefined,
      bank_name: bankLedgerQuery.bank_name.trim() || undefined,
      account_name: bankLedgerQuery.account_name.trim() || undefined,
      transaction_type: bankLedgerQuery.transaction_type || undefined,
      ledger_status: bankLedgerQuery.ledger_status || undefined,
      review_status: bankLedgerQuery.review_status || undefined,
      keyword: bankLedgerQuery.keyword.trim() || undefined,
      from_date: bankLedgerQuery.from_date || undefined,
      to_date: bankLedgerQuery.to_date || undefined,
      page: bankLedgerQuery.page,
      page_size: bankLedgerQuery.page_size,
    })
    bankLedgerRows.value = result.data.items
    bankLedgerTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    bankLedgerError.value = `银行流水加载失败：${message}`
    ElMessage.error(bankLedgerError.value)
  } finally {
    bankLedgerLoading.value = false
  }
}

const loadCustomerEvaluations = async (): Promise<void> => {
  if (!canRead.value) {
    resetCustomerEvaluationRows()
    return
  }

  customerEvaluationLoading.value = true
  customerEvaluationError.value = ''
  try {
    const result = await fetchFactoryStatementCustomerEvaluations({
      evaluation_no: customerEvaluationQuery.evaluation_no.trim() || undefined,
      statement_no: customerEvaluationQuery.statement_no.trim() || undefined,
      customer_name: customerEvaluationQuery.customer_name.trim() || undefined,
      assessor: customerEvaluationQuery.assessor.trim() || undefined,
      score_level: customerEvaluationQuery.score_level || undefined,
      review_status: customerEvaluationQuery.review_status || undefined,
      keyword: customerEvaluationQuery.keyword.trim() || undefined,
      from_date: customerEvaluationQuery.from_date || undefined,
      to_date: customerEvaluationQuery.to_date || undefined,
      page: customerEvaluationQuery.page,
      page_size: customerEvaluationQuery.page_size,
    })
    customerEvaluationRows.value = result.data.items
    customerEvaluationTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    customerEvaluationError.value = `客户评估表加载失败：${message}`
    ElMessage.error(customerEvaluationError.value)
  } finally {
    customerEvaluationLoading.value = false
  }
}

const loadCustomerReconciliations = async (): Promise<void> => {
  if (!canRead.value) {
    resetCustomerReconciliationRows()
    return
  }

  customerReconciliationLoading.value = true
  customerReconciliationError.value = ''
  try {
    const result = await fetchFactoryStatementCustomerReconciliations({
      reconciliation_no: customerReconciliationQuery.reconciliation_no.trim() || undefined,
      statement_no: customerReconciliationQuery.statement_no.trim() || undefined,
      customer_name: customerReconciliationQuery.customer_name.trim() || undefined,
      settlement_status: customerReconciliationQuery.settlement_status || undefined,
      review_status: customerReconciliationQuery.review_status || undefined,
      keyword: customerReconciliationQuery.keyword.trim() || undefined,
      from_date: customerReconciliationQuery.from_date || undefined,
      to_date: customerReconciliationQuery.to_date || undefined,
      page: customerReconciliationQuery.page,
      page_size: customerReconciliationQuery.page_size,
    })
    customerReconciliationRows.value = result.data.items
    customerReconciliationTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    customerReconciliationError.value = `客户对账表加载失败：${message}`
    ElMessage.error(customerReconciliationError.value)
  } finally {
    customerReconciliationLoading.value = false
  }
}

const loadCustomerUnpaidReports = async (): Promise<void> => {
  if (!canRead.value) {
    resetCustomerUnpaidReportRows()
    return
  }

  customerUnpaidReportLoading.value = true
  customerUnpaidReportError.value = ''
  try {
    const result = await fetchFactoryStatementCustomerUnpaidReports({
      report_no: customerUnpaidReportQuery.report_no.trim() || undefined,
      statement_no: customerUnpaidReportQuery.statement_no.trim() || undefined,
      customer_name: customerUnpaidReportQuery.customer_name.trim() || undefined,
      collection_status: customerUnpaidReportQuery.collection_status || undefined,
      review_status: customerUnpaidReportQuery.review_status || undefined,
      keyword: customerUnpaidReportQuery.keyword.trim() || undefined,
      from_date: customerUnpaidReportQuery.from_date || undefined,
      to_date: customerUnpaidReportQuery.to_date || undefined,
      page: customerUnpaidReportQuery.page,
      page_size: customerUnpaidReportQuery.page_size,
    })
    customerUnpaidReportRows.value = result.data.items
    customerUnpaidReportTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    customerUnpaidReportError.value = `客户未收款报表加载失败：${message}`
    ElMessage.error(customerUnpaidReportError.value)
  } finally {
    customerUnpaidReportLoading.value = false
  }
}

const loadCustomerReceivableSummaries = async (): Promise<void> => {
  if (!canRead.value) {
    resetCustomerReceivableSummaryRows()
    return
  }

  customerReceivableSummaryLoading.value = true
  customerReceivableSummaryError.value = ''
  try {
    const result = await fetchFactoryStatementCustomerReceivableSummaries({
      summary_no: customerReceivableSummaryQuery.summary_no.trim() || undefined,
      statement_no: customerReceivableSummaryQuery.statement_no.trim() || undefined,
      customer_name: customerReceivableSummaryQuery.customer_name.trim() || undefined,
      risk_level: customerReceivableSummaryQuery.risk_level || undefined,
      review_status: customerReceivableSummaryQuery.review_status || undefined,
      keyword: customerReceivableSummaryQuery.keyword.trim() || undefined,
      from_date: customerReceivableSummaryQuery.from_date || undefined,
      to_date: customerReceivableSummaryQuery.to_date || undefined,
      page: customerReceivableSummaryQuery.page,
      page_size: customerReceivableSummaryQuery.page_size,
    })
    customerReceivableSummaryRows.value = result.data.items
    customerReceivableSummaryTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    customerReceivableSummaryError.value = `客户应收账款汇总表加载失败：${message}`
    ElMessage.error(customerReceivableSummaryError.value)
  } finally {
    customerReceivableSummaryLoading.value = false
  }
}

const loadFactoryEvaluations = async (): Promise<void> => {
  if (!canRead.value) {
    resetFactoryEvaluationRows()
    return
  }

  factoryEvaluationLoading.value = true
  factoryEvaluationError.value = ''
  try {
    const result = await fetchFactoryStatementFactoryEvaluations({
      evaluation_no: factoryEvaluationQuery.evaluation_no.trim() || undefined,
      statement_no: factoryEvaluationQuery.statement_no.trim() || undefined,
      factory_name: factoryEvaluationQuery.factory_name.trim() || undefined,
      assessor: factoryEvaluationQuery.assessor.trim() || undefined,
      score_level: factoryEvaluationQuery.score_level || undefined,
      review_status: factoryEvaluationQuery.review_status || undefined,
      keyword: factoryEvaluationQuery.keyword.trim() || undefined,
      from_date: factoryEvaluationQuery.from_date || undefined,
      to_date: factoryEvaluationQuery.to_date || undefined,
      page: factoryEvaluationQuery.page,
      page_size: factoryEvaluationQuery.page_size,
    })
    factoryEvaluationRows.value = result.data.items
    factoryEvaluationTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    factoryEvaluationError.value = `加工厂评估表加载失败：${message}`
    ElMessage.error(factoryEvaluationError.value)
  } finally {
    factoryEvaluationLoading.value = false
  }
}

const loadFactoryReconciliations = async (): Promise<void> => {
  if (!canRead.value) {
    resetFactoryReconciliationRows()
    return
  }

  factoryReconciliationLoading.value = true
  factoryReconciliationError.value = ''
  try {
    const result = await fetchFactoryStatementFactoryReconciliations({
      reconciliation_no: factoryReconciliationQuery.reconciliation_no.trim() || undefined,
      statement_no: factoryReconciliationQuery.statement_no.trim() || undefined,
      supplier: factoryReconciliationQuery.supplier.trim() || undefined,
      factory_name: factoryReconciliationQuery.factory_name.trim() || undefined,
      settlement_status: factoryReconciliationQuery.settlement_status || undefined,
      review_status: factoryReconciliationQuery.review_status || undefined,
      keyword: factoryReconciliationQuery.keyword.trim() || undefined,
      from_date: factoryReconciliationQuery.from_date || undefined,
      to_date: factoryReconciliationQuery.to_date || undefined,
      page: factoryReconciliationQuery.page,
      page_size: factoryReconciliationQuery.page_size,
    })
    factoryReconciliationRows.value = result.data.items
    factoryReconciliationTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    factoryReconciliationError.value = `加工厂对账表加载失败：${message}`
    ElMessage.error(factoryReconciliationError.value)
  } finally {
    factoryReconciliationLoading.value = false
  }
}

const loadFactoryPayableSummaries = async (): Promise<void> => {
  if (!canRead.value) {
    resetFactoryPayableSummaryRows()
    return
  }

  factoryPayableSummaryLoading.value = true
  factoryPayableSummaryError.value = ''
  try {
    const result = await fetchFactoryStatementFactoryPayableSummaries({
      summary_no: factoryPayableSummaryQuery.summary_no.trim() || undefined,
      statement_no: factoryPayableSummaryQuery.statement_no.trim() || undefined,
      supplier: factoryPayableSummaryQuery.supplier.trim() || undefined,
      factory_name: factoryPayableSummaryQuery.factory_name.trim() || undefined,
      risk_level: factoryPayableSummaryQuery.risk_level || undefined,
      review_status: factoryPayableSummaryQuery.review_status || undefined,
      keyword: factoryPayableSummaryQuery.keyword.trim() || undefined,
      from_date: factoryPayableSummaryQuery.from_date || undefined,
      to_date: factoryPayableSummaryQuery.to_date || undefined,
      page: factoryPayableSummaryQuery.page,
      page_size: factoryPayableSummaryQuery.page_size,
    })
    factoryPayableSummaryRows.value = result.data.items
    factoryPayableSummaryTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    factoryPayableSummaryError.value = `加工厂应付账款汇总表加载失败：${message}`
    ElMessage.error(factoryPayableSummaryError.value)
  } finally {
    factoryPayableSummaryLoading.value = false
  }
}

const loadSupplierEvaluations = async (): Promise<void> => {
  if (!canRead.value) {
    resetSupplierEvaluationRows()
    return
  }

  supplierEvaluationLoading.value = true
  supplierEvaluationError.value = ''
  try {
    const result = await fetchFactoryStatementSupplierEvaluations({
      evaluation_no: supplierEvaluationQuery.evaluation_no.trim() || undefined,
      statement_no: supplierEvaluationQuery.statement_no.trim() || undefined,
      supplier: supplierEvaluationQuery.supplier.trim() || undefined,
      assessor: supplierEvaluationQuery.assessor.trim() || undefined,
      score_level: supplierEvaluationQuery.score_level || undefined,
      review_status: supplierEvaluationQuery.review_status || undefined,
      keyword: supplierEvaluationQuery.keyword.trim() || undefined,
      from_date: supplierEvaluationQuery.from_date || undefined,
      to_date: supplierEvaluationQuery.to_date || undefined,
      page: supplierEvaluationQuery.page,
      page_size: supplierEvaluationQuery.page_size,
    })
    supplierEvaluationRows.value = result.data.items
    supplierEvaluationTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    supplierEvaluationError.value = `供应商评估表加载失败：${message}`
    ElMessage.error(supplierEvaluationError.value)
  } finally {
    supplierEvaluationLoading.value = false
  }
}

const loadSupplierReconciliations = async (): Promise<void> => {
  if (!canRead.value) {
    resetSupplierReconciliationRows()
    return
  }

  supplierReconciliationLoading.value = true
  supplierReconciliationError.value = ''
  try {
    const result = await fetchFactoryStatementSupplierReconciliations({
      reconciliation_no: supplierReconciliationQuery.reconciliation_no.trim() || undefined,
      statement_no: supplierReconciliationQuery.statement_no.trim() || undefined,
      supplier: supplierReconciliationQuery.supplier.trim() || undefined,
      supplier_code: supplierReconciliationQuery.supplier_code.trim() || undefined,
      settlement_status: supplierReconciliationQuery.settlement_status || undefined,
      review_status: supplierReconciliationQuery.review_status || undefined,
      keyword: supplierReconciliationQuery.keyword.trim() || undefined,
      from_date: supplierReconciliationQuery.from_date || undefined,
      to_date: supplierReconciliationQuery.to_date || undefined,
      page: supplierReconciliationQuery.page,
      page_size: supplierReconciliationQuery.page_size,
    })
    supplierReconciliationRows.value = result.data.items
    supplierReconciliationTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    supplierReconciliationError.value = `供应商对账表加载失败：${message}`
    ElMessage.error(supplierReconciliationError.value)
  } finally {
    supplierReconciliationLoading.value = false
  }
}

const loadSupplierPayableSummaries = async (): Promise<void> => {
  if (!canRead.value) {
    resetSupplierPayableSummaryRows()
    return
  }

  supplierPayableSummaryLoading.value = true
  supplierPayableSummaryError.value = ''
  try {
    const result = await fetchFactoryStatementSupplierPayableSummaries({
      summary_no: supplierPayableSummaryQuery.summary_no.trim() || undefined,
      statement_no: supplierPayableSummaryQuery.statement_no.trim() || undefined,
      supplier: supplierPayableSummaryQuery.supplier.trim() || undefined,
      supplier_code: supplierPayableSummaryQuery.supplier_code.trim() || undefined,
      risk_level: supplierPayableSummaryQuery.risk_level || undefined,
      review_status: supplierPayableSummaryQuery.review_status || undefined,
      keyword: supplierPayableSummaryQuery.keyword.trim() || undefined,
      from_date: supplierPayableSummaryQuery.from_date || undefined,
      to_date: supplierPayableSummaryQuery.to_date || undefined,
      page: supplierPayableSummaryQuery.page,
      page_size: supplierPayableSummaryQuery.page_size,
    })
    supplierPayableSummaryRows.value = result.data.items
    supplierPayableSummaryTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    supplierPayableSummaryError.value = `供应商应付账款汇总表加载失败：${message}`
    ElMessage.error(supplierPayableSummaryError.value)
  } finally {
    supplierPayableSummaryLoading.value = false
  }
}

const goDetail = (statementId: number): void => {
  router.push({ path: '/factory-statements/detail', query: { id: String(statementId) } })
}

const goPrint = (statementId: number): void => {
  router.push({ path: '/factory-statements/print', query: { id: String(statementId) } })
}

const showGuardedAction = (actionLabel: string): void => {
  ElMessage.warning(`${actionLabel}已禁用：${readonlyWriteHint}`)
}

const onPageChange = (page: number): void => {
  query.page = page
  loadRows()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadRows()
}

const resetExpensePaymentFilters = async (): Promise<void> => {
  expensePaymentQuery.payment_no = ''
  expensePaymentQuery.reimbursement_no = ''
  expensePaymentQuery.statement_no = ''
  expensePaymentQuery.supplier = ''
  expensePaymentQuery.payment_status = ''
  expensePaymentQuery.review_status = ''
  expensePaymentQuery.keyword = ''
  expensePaymentQuery.from_date = ''
  expensePaymentQuery.to_date = ''
  expensePaymentQuery.page = 1
  await loadExpenseReimbursementPayments()
}

const resetBankDepositFilters = async (): Promise<void> => {
  bankDepositQuery.deposit_no = ''
  bankDepositQuery.statement_no = ''
  bankDepositQuery.bank_name = ''
  bankDepositQuery.account_name = ''
  bankDepositQuery.deposit_status = ''
  bankDepositQuery.review_status = ''
  bankDepositQuery.keyword = ''
  bankDepositQuery.from_date = ''
  bankDepositQuery.to_date = ''
  bankDepositQuery.page = 1
  await loadBankDeposits()
}

const resetBankWithdrawalFilters = async (): Promise<void> => {
  bankWithdrawalQuery.withdrawal_no = ''
  bankWithdrawalQuery.statement_no = ''
  bankWithdrawalQuery.bank_name = ''
  bankWithdrawalQuery.account_name = ''
  bankWithdrawalQuery.withdrawal_status = ''
  bankWithdrawalQuery.review_status = ''
  bankWithdrawalQuery.keyword = ''
  bankWithdrawalQuery.from_date = ''
  bankWithdrawalQuery.to_date = ''
  bankWithdrawalQuery.page = 1
  await loadBankWithdrawals()
}

const resetBankLedgerFilters = async (): Promise<void> => {
  bankLedgerQuery.ledger_no = ''
  bankLedgerQuery.statement_no = ''
  bankLedgerQuery.bank_name = ''
  bankLedgerQuery.account_name = ''
  bankLedgerQuery.transaction_type = ''
  bankLedgerQuery.ledger_status = ''
  bankLedgerQuery.review_status = ''
  bankLedgerQuery.keyword = ''
  bankLedgerQuery.from_date = ''
  bankLedgerQuery.to_date = ''
  bankLedgerQuery.page = 1
  await loadBankLedgers()
}

const resetCustomerEvaluationFilters = async (): Promise<void> => {
  customerEvaluationQuery.evaluation_no = ''
  customerEvaluationQuery.statement_no = ''
  customerEvaluationQuery.customer_name = ''
  customerEvaluationQuery.assessor = ''
  customerEvaluationQuery.score_level = ''
  customerEvaluationQuery.review_status = ''
  customerEvaluationQuery.keyword = ''
  customerEvaluationQuery.from_date = ''
  customerEvaluationQuery.to_date = ''
  customerEvaluationQuery.page = 1
  await loadCustomerEvaluations()
}

const resetCustomerReconciliationFilters = async (): Promise<void> => {
  customerReconciliationQuery.reconciliation_no = ''
  customerReconciliationQuery.statement_no = ''
  customerReconciliationQuery.customer_name = ''
  customerReconciliationQuery.settlement_status = ''
  customerReconciliationQuery.review_status = ''
  customerReconciliationQuery.keyword = ''
  customerReconciliationQuery.from_date = ''
  customerReconciliationQuery.to_date = ''
  customerReconciliationQuery.page = 1
  await loadCustomerReconciliations()
}

const resetCustomerUnpaidReportFilters = async (): Promise<void> => {
  customerUnpaidReportQuery.report_no = ''
  customerUnpaidReportQuery.statement_no = ''
  customerUnpaidReportQuery.customer_name = ''
  customerUnpaidReportQuery.collection_status = ''
  customerUnpaidReportQuery.review_status = ''
  customerUnpaidReportQuery.keyword = ''
  customerUnpaidReportQuery.from_date = ''
  customerUnpaidReportQuery.to_date = ''
  customerUnpaidReportQuery.page = 1
  await loadCustomerUnpaidReports()
}

const resetCustomerReceivableSummaryFilters = async (): Promise<void> => {
  customerReceivableSummaryQuery.summary_no = ''
  customerReceivableSummaryQuery.statement_no = ''
  customerReceivableSummaryQuery.customer_name = ''
  customerReceivableSummaryQuery.risk_level = ''
  customerReceivableSummaryQuery.review_status = ''
  customerReceivableSummaryQuery.keyword = ''
  customerReceivableSummaryQuery.from_date = ''
  customerReceivableSummaryQuery.to_date = ''
  customerReceivableSummaryQuery.page = 1
  await loadCustomerReceivableSummaries()
}

const resetFactoryEvaluationFilters = async (): Promise<void> => {
  factoryEvaluationQuery.evaluation_no = ''
  factoryEvaluationQuery.statement_no = ''
  factoryEvaluationQuery.factory_name = ''
  factoryEvaluationQuery.assessor = ''
  factoryEvaluationQuery.score_level = ''
  factoryEvaluationQuery.review_status = ''
  factoryEvaluationQuery.keyword = ''
  factoryEvaluationQuery.from_date = ''
  factoryEvaluationQuery.to_date = ''
  factoryEvaluationQuery.page = 1
  await loadFactoryEvaluations()
}

const resetFactoryReconciliationFilters = async (): Promise<void> => {
  factoryReconciliationQuery.reconciliation_no = ''
  factoryReconciliationQuery.statement_no = ''
  factoryReconciliationQuery.supplier = ''
  factoryReconciliationQuery.factory_name = ''
  factoryReconciliationQuery.settlement_status = ''
  factoryReconciliationQuery.review_status = ''
  factoryReconciliationQuery.keyword = ''
  factoryReconciliationQuery.from_date = ''
  factoryReconciliationQuery.to_date = ''
  factoryReconciliationQuery.page = 1
  await loadFactoryReconciliations()
}

const resetFactoryPayableSummaryFilters = async (): Promise<void> => {
  factoryPayableSummaryQuery.summary_no = ''
  factoryPayableSummaryQuery.statement_no = ''
  factoryPayableSummaryQuery.supplier = ''
  factoryPayableSummaryQuery.factory_name = ''
  factoryPayableSummaryQuery.risk_level = ''
  factoryPayableSummaryQuery.review_status = ''
  factoryPayableSummaryQuery.keyword = ''
  factoryPayableSummaryQuery.from_date = ''
  factoryPayableSummaryQuery.to_date = ''
  factoryPayableSummaryQuery.page = 1
  await loadFactoryPayableSummaries()
}

const resetSupplierEvaluationFilters = async (): Promise<void> => {
  supplierEvaluationQuery.evaluation_no = ''
  supplierEvaluationQuery.statement_no = ''
  supplierEvaluationQuery.supplier = ''
  supplierEvaluationQuery.assessor = ''
  supplierEvaluationQuery.score_level = ''
  supplierEvaluationQuery.review_status = ''
  supplierEvaluationQuery.keyword = ''
  supplierEvaluationQuery.from_date = ''
  supplierEvaluationQuery.to_date = ''
  supplierEvaluationQuery.page = 1
  await loadSupplierEvaluations()
}

const resetSupplierReconciliationFilters = async (): Promise<void> => {
  supplierReconciliationQuery.reconciliation_no = ''
  supplierReconciliationQuery.statement_no = ''
  supplierReconciliationQuery.supplier = ''
  supplierReconciliationQuery.supplier_code = ''
  supplierReconciliationQuery.settlement_status = ''
  supplierReconciliationQuery.review_status = ''
  supplierReconciliationQuery.keyword = ''
  supplierReconciliationQuery.from_date = ''
  supplierReconciliationQuery.to_date = ''
  supplierReconciliationQuery.page = 1
  await loadSupplierReconciliations()
}

const resetSupplierPayableSummaryFilters = async (): Promise<void> => {
  supplierPayableSummaryQuery.summary_no = ''
  supplierPayableSummaryQuery.statement_no = ''
  supplierPayableSummaryQuery.supplier = ''
  supplierPayableSummaryQuery.supplier_code = ''
  supplierPayableSummaryQuery.risk_level = ''
  supplierPayableSummaryQuery.review_status = ''
  supplierPayableSummaryQuery.keyword = ''
  supplierPayableSummaryQuery.from_date = ''
  supplierPayableSummaryQuery.to_date = ''
  supplierPayableSummaryQuery.page = 1
  await loadSupplierPayableSummaries()
}

const onExpensePaymentPageChange = (page: number): void => {
  expensePaymentQuery.page = page
  loadExpenseReimbursementPayments()
}

const onExpensePaymentSizeChange = (size: number): void => {
  expensePaymentQuery.page_size = size
  expensePaymentQuery.page = 1
  loadExpenseReimbursementPayments()
}

const onBankDepositPageChange = (page: number): void => {
  bankDepositQuery.page = page
  loadBankDeposits()
}

const onBankDepositSizeChange = (size: number): void => {
  bankDepositQuery.page_size = size
  bankDepositQuery.page = 1
  loadBankDeposits()
}

const onBankWithdrawalPageChange = (page: number): void => {
  bankWithdrawalQuery.page = page
  loadBankWithdrawals()
}

const onBankWithdrawalSizeChange = (size: number): void => {
  bankWithdrawalQuery.page_size = size
  bankWithdrawalQuery.page = 1
  loadBankWithdrawals()
}

const onBankLedgerPageChange = (page: number): void => {
  bankLedgerQuery.page = page
  loadBankLedgers()
}

const onBankLedgerSizeChange = (size: number): void => {
  bankLedgerQuery.page_size = size
  bankLedgerQuery.page = 1
  loadBankLedgers()
}

const onCustomerEvaluationPageChange = (page: number): void => {
  customerEvaluationQuery.page = page
  loadCustomerEvaluations()
}

const onCustomerEvaluationSizeChange = (size: number): void => {
  customerEvaluationQuery.page_size = size
  customerEvaluationQuery.page = 1
  loadCustomerEvaluations()
}

const onCustomerReconciliationPageChange = (page: number): void => {
  customerReconciliationQuery.page = page
  loadCustomerReconciliations()
}

const onCustomerReconciliationSizeChange = (size: number): void => {
  customerReconciliationQuery.page_size = size
  customerReconciliationQuery.page = 1
  loadCustomerReconciliations()
}

const onCustomerUnpaidReportPageChange = (page: number): void => {
  customerUnpaidReportQuery.page = page
  loadCustomerUnpaidReports()
}

const onCustomerUnpaidReportSizeChange = (size: number): void => {
  customerUnpaidReportQuery.page_size = size
  customerUnpaidReportQuery.page = 1
  loadCustomerUnpaidReports()
}

const onCustomerReceivableSummaryPageChange = (page: number): void => {
  customerReceivableSummaryQuery.page = page
  loadCustomerReceivableSummaries()
}

const onCustomerReceivableSummarySizeChange = (size: number): void => {
  customerReceivableSummaryQuery.page_size = size
  customerReceivableSummaryQuery.page = 1
  loadCustomerReceivableSummaries()
}

const onFactoryEvaluationPageChange = (page: number): void => {
  factoryEvaluationQuery.page = page
  loadFactoryEvaluations()
}

const onFactoryEvaluationSizeChange = (size: number): void => {
  factoryEvaluationQuery.page_size = size
  factoryEvaluationQuery.page = 1
  loadFactoryEvaluations()
}

const onFactoryReconciliationPageChange = (page: number): void => {
  factoryReconciliationQuery.page = page
  loadFactoryReconciliations()
}

const onFactoryReconciliationSizeChange = (size: number): void => {
  factoryReconciliationQuery.page_size = size
  factoryReconciliationQuery.page = 1
  loadFactoryReconciliations()
}

const onFactoryPayableSummaryPageChange = (page: number): void => {
  factoryPayableSummaryQuery.page = page
  loadFactoryPayableSummaries()
}

const onFactoryPayableSummarySizeChange = (size: number): void => {
  factoryPayableSummaryQuery.page_size = size
  factoryPayableSummaryQuery.page = 1
  loadFactoryPayableSummaries()
}

const onSupplierEvaluationPageChange = (page: number): void => {
  supplierEvaluationQuery.page = page
  loadSupplierEvaluations()
}

const onSupplierEvaluationSizeChange = (size: number): void => {
  supplierEvaluationQuery.page_size = size
  supplierEvaluationQuery.page = 1
  loadSupplierEvaluations()
}

const onSupplierReconciliationPageChange = (page: number): void => {
  supplierReconciliationQuery.page = page
  loadSupplierReconciliations()
}

const onSupplierReconciliationSizeChange = (size: number): void => {
  supplierReconciliationQuery.page_size = size
  supplierReconciliationQuery.page = 1
  loadSupplierReconciliations()
}

const onSupplierPayableSummaryPageChange = (page: number): void => {
  supplierPayableSummaryQuery.page = page
  loadSupplierPayableSummaries()
}

const onSupplierPayableSummarySizeChange = (size: number): void => {
  supplierPayableSummaryQuery.page_size = size
  supplierPayableSummaryQuery.page = 1
  loadSupplierPayableSummaries()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('factory_statement')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value) {
    await loadRows()
    await loadExpenseReimbursementPayments()
    await loadBankDeposits()
    await loadBankWithdrawals()
    await loadBankLedgers()
    await loadCustomerEvaluations()
    await loadCustomerReconciliations()
    await loadCustomerUnpaidReports()
    await loadCustomerReceivableSummaries()
    await loadFactoryEvaluations()
    await loadFactoryReconciliations()
    await loadFactoryPayableSummaries()
    await loadSupplierEvaluations()
    await loadSupplierReconciliations()
    await loadSupplierPayableSummaries()
  }
})
</script>

<style scoped>
.factory-statement-list-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.reconciliation-alert {
  margin-bottom: 12px;
}

.sample-filter-form {
  margin-top: 8px;
}

.expense-filter-form {
  margin-top: 8px;
}

.expense-reimbursement-alert {
  margin-bottom: 12px;
}

.bank-deposit-filter-form {
  margin-top: 8px;
}

.bank-deposit-alert {
  margin-bottom: 12px;
}

.bank-withdrawal-filter-form {
  margin-top: 8px;
}

.bank-withdrawal-alert {
  margin-bottom: 12px;
}

.customer-evaluation-filter-form {
  margin-top: 8px;
}

.customer-evaluation-alert {
  margin-bottom: 12px;
}

.customer-reconciliation-filter-form {
  margin-top: 8px;
}

.customer-reconciliation-alert {
  margin-bottom: 12px;
}

.customer-unpaid-report-filter-form {
  margin-top: 8px;
}

.customer-unpaid-report-alert {
  margin-bottom: 12px;
}

.customer-receivable-summary-filter-form {
  margin-top: 8px;
}

.customer-receivable-summary-alert {
  margin-bottom: 12px;
}

.factory-evaluation-filter-form {
  margin-top: 8px;
}

.factory-evaluation-alert {
  margin-bottom: 12px;
}

.factory-reconciliation-filter-form {
  margin-top: 8px;
}

.factory-reconciliation-alert {
  margin-bottom: 12px;
}

.factory-payable-summary-filter-form {
  margin-top: 8px;
}

.factory-payable-summary-alert {
  margin-bottom: 12px;
}

.supplier-evaluation-filter-form {
  margin-top: 8px;
}

.supplier-evaluation-alert {
  margin-bottom: 12px;
}

.supplier-reconciliation-filter-form {
  margin-top: 8px;
}

.supplier-reconciliation-alert {
  margin-bottom: 12px;
}

.supplier-payable-summary-filter-form {
  margin-top: 8px;
}

.supplier-payable-summary-alert {
  margin-bottom: 12px;
}

.bank-ledger-filter-form {
  margin-top: 8px;
}

.bank-ledger-alert {
  margin-bottom: 12px;
}

.range-sep {
  margin: 0 8px;
  color: #6b7280;
}

.error-alert {
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
