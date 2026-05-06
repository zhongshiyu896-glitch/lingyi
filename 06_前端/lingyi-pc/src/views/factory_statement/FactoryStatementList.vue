<template>
  <div class="factory-statement-list-page">
    <el-card shadow="never">
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
      />

      <el-form :inline="true" :model="query">
        <el-form-item label="供应商">
          <el-input v-model="query.supplier" clearable placeholder="请输入供应商" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.statement_status" clearable placeholder="请选择状态" style="width: 160px">
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
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="操作">
          <el-button type="primary" :disabled="!canRead" @click="loadRows">查询</el-button>
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

      <el-alert v-if="readError" type="error" :closable="false" show-icon :title="readError" class="error-alert" />
      <el-empty v-if="!canRead" description="无加工厂对账单查看权限" />
      <template v-else>
        <el-table :data="displayRows" border v-loading="loading" empty-text="暂无款式打板下单对账数据">
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
              <el-tag :type="statusTag(scope.row.statement_status)">
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
              <el-button link type="primary" @click="goDetail(scope.row.id)">查看</el-button>
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
  fetchFactoryStatementBankWithdrawals,
  fetchFactoryStatementCustomerEvaluations,
  fetchFactoryStatementExpenseReimbursementPayments,
  fetchFactoryStatements,
  type FactoryStatementBankDepositItem,
  type FactoryStatementBankWithdrawalItem,
  type FactoryStatementCustomerEvaluationItem,
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
const customerEvaluationLoading = ref<boolean>(false)
const customerEvaluationError = ref<string>('')
const customerEvaluationRows = ref<FactoryStatementCustomerEvaluationItem[]>([])
const customerEvaluationTotal = ref<number>(0)

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

const resetCustomerEvaluationRows = (): void => {
  customerEvaluationRows.value = []
  customerEvaluationTotal.value = 0
  customerEvaluationError.value = ''
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

const onCustomerEvaluationPageChange = (page: number): void => {
  customerEvaluationQuery.page = page
  loadCustomerEvaluations()
}

const onCustomerEvaluationSizeChange = (size: number): void => {
  customerEvaluationQuery.page_size = size
  customerEvaluationQuery.page = 1
  loadCustomerEvaluations()
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
    await loadCustomerEvaluations()
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
