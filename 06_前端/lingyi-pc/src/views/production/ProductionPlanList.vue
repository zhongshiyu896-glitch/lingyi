<template>
  <div class="production-followup-page" data-testid="production-plan-page">
    <el-card shadow="never" data-testid="production-plan-main-section">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">大货跟进</span>
            <span class="sub-title">大货管理 / 大货跟进</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form" data-testid="production-plan-query-form">
        <el-form-item label="订单">
          <el-input
            v-model="query.sales_order"
            clearable
            placeholder="订单"
            data-testid="production-plan-filter-sales-order"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="款号/款名">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="请输入"
            data-testid="production-plan-filter-keyword"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="翻单号">
          <el-input
            v-model="query.turnover_no"
            clearable
            placeholder="翻单号"
            data-testid="production-plan-filter-turnover-no"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="query.status"
            clearable
            placeholder="全部状态"
            style="width: 160px"
            data-testid="production-plan-filter-status"
          >
            <el-option label="草稿" value="draft" />
            <el-option label="已计划" value="planned" />
            <el-option label="已物料检查" value="material_checked" />
            <el-option label="工单待同步" value="work_order_pending" />
            <el-option label="已创建工单" value="work_order_created" />
            <el-option label="工序卡已同步" value="job_cards_synced" />
            <el-option label="已取消" value="cancelled" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始时间"
            clearable
            data-testid="production-plan-filter-from-date"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
            data-testid="production-plan-filter-to-date"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" data-testid="production-plan-search" @click="onSearch">搜索</el-button>
          <el-button :disabled="!canRead" data-testid="production-plan-reset" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <el-card shadow="never" class="create-plan-card" data-testid="production-plan-create-card">
        <template #header>
          <div class="header-row">
            <span>生产计划创建（本地闭环）</span>
            <el-tag type="warning" effect="plain">受控写入</el-tag>
          </div>
        </template>
        <el-alert
          v-if="createPlanFeedback"
          type="info"
          :closable="false"
          :title="createPlanFeedback"
          data-testid="production-plan-create-feedback"
          style="margin-bottom: 12px"
        />
        <el-form :model="createPlanForm" label-width="120px" data-testid="production-plan-create-form">
          <el-form-item label="Scenario Tag">
            <el-input v-model="createPlanForm.scenario_tag" readonly data-testid="production-plan-create-scenario-tag" />
          </el-form-item>
          <el-form-item label="销售单">
            <el-input v-model="createPlanForm.sales_order" data-testid="production-plan-create-sales-order" />
          </el-form-item>
          <el-form-item label="销售单行">
            <el-input v-model="createPlanForm.sales_order_item" data-testid="production-plan-create-sales-order-item" />
          </el-form-item>
          <el-form-item label="款号">
            <el-input v-model="createPlanForm.item_code" data-testid="production-plan-create-item-code" />
          </el-form-item>
          <el-form-item label="BOM ID">
            <el-input v-model="createPlanForm.bom_id" data-testid="production-plan-create-bom-id" />
          </el-form-item>
          <el-form-item label="计划数量">
            <el-input v-model="createPlanForm.planned_qty" data-testid="production-plan-create-planned-qty" />
          </el-form-item>
          <el-form-item label="计划开工日">
            <el-date-picker
              v-model="createPlanForm.planned_start_date"
              type="date"
              value-format="YYYY-MM-DD"
              format="YYYY-MM-DD"
              placeholder="选择开工日期"
              data-testid="production-plan-create-planned-start-date"
            />
          </el-form-item>
          <el-form-item label="幂等键">
            <el-input v-model="createPlanForm.idempotency_key" data-testid="production-plan-create-idempotency-key" />
          </el-form-item>
          <el-form-item label="Request ID">
            <el-input v-model="createPlanForm.request_id" data-testid="production-plan-create-request-id" />
          </el-form-item>
        </el-form>
        <div class="toolbar-row" data-testid="production-plan-create-actions">
          <el-button :disabled="creatingPlan" data-testid="production-plan-create-reset" @click="resetCreatePlanForm">取消/重置</el-button>
          <el-button
            type="primary"
            :loading="creatingPlan"
            :disabled="creatingPlan || !canWriteGuarded"
            data-action-type="write"
            data-write-guard="dev-cand-005:readonly-disabled"
            data-testid="production-plan-create-submit"
            @click="submitCreatePlan"
          >
            保存生产计划
          </el-button>
        </div>
      </el-card>

      <div class="toolbar-row" data-testid="production-plan-toolbar">
        <el-button :disabled="!canRead" data-testid="production-plan-filter" @click="onSearch">筛选</el-button>
        <el-button :disabled="!canRead" data-testid="production-plan-clear" @click="onClearFilters">清空</el-button>
        <el-button
          :disabled="!canWriteGuarded"
          data-action-type="write"
          data-write-guard="dev-cand-005:readonly-disabled"
          data-testid="production-plan-guarded-confirm"
          @click="onGuardedAction('确定', true)"
        >
          确定
        </el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" data-write-guard="dev-cand-005:readonly-disabled" @click="onGuardedAction('标志已读', true)">标志已读</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" data-write-guard="dev-cand-005:readonly-disabled" @click="onGuardedAction('删除消息', true)">删除消息</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" data-write-guard="dev-cand-005:readonly-disabled" @click="onGuardedAction('新增消息', true)">新增消息</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" data-write-guard="dev-cand-005:readonly-disabled" @click="onGuardedAction('保存', true)">保存</el-button>
      </div>

      <el-alert
        v-if="lastError"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`大货跟进数据加载失败：${lastError}`"
        data-testid="production-plan-error-alert"
      />

      <el-empty
        v-if="!canRead && !isProductionQuoteParity && !isProductionFollowupTemplateParity"
        description="无大货跟进查看权限"
        data-testid="production-plan-no-permission"
      />
      <template v-else>
        <el-table
          :data="rows"
          border
          v-loading="loading"
          empty-text="暂无大货跟进数据，请调整筛选条件后重试"
          data-testid="production-plan-table"
        >
          <el-table-column label="订单信息" min-width="260">
            <template #default="scope">
              <div class="cell-stack">
                <span class="primary-text">{{ scope.row.sales_order }}</span>
                <span class="secondary-text">款号：{{ scope.row.item_code || '-' }}</span>
                <span class="secondary-text">翻单号：{{ scope.row.sales_order_item || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="plan_no" label="生产制单" min-width="160" />
          <el-table-column label="客户信息" min-width="180">
            <template #default="scope">
              <div class="cell-stack">
                <span class="primary-text">{{ scope.row.customer || '-' }}</span>
                <span class="secondary-text">单位：{{ scope.row.company || '-' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="预计出货" min-width="120">
            <template #default="scope">{{ scope.row.planned_start_date || '-' }}</template>
          </el-table-column>
          <el-table-column label="面辅包进度" min-width="120">
            <template #default="scope">{{ materialProgressLabel(scope.row.status) }}</template>
          </el-table-column>
          <el-table-column label="生产排期" min-width="180">
            <template #default="scope">{{ scheduleText(scope.row) }}</template>
          </el-table-column>
          <el-table-column label="工厂进度" min-width="120">
            <template #default="scope">
              <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                {{ statusLabel(scope.row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="入库数" min-width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="出库数" min-width="100">
            <template #default>-</template>
          </el-table-column>
          <el-table-column label="操作" fixed="right" min-width="110">
            <template #default="scope">
              <el-button
                link
                type="primary"
                :data-testid="`production-plan-detail-${scope.row.id}`"
                @click="goDetail(scope.row.id)"
              >
                跟进
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pager" data-testid="production-plan-pager">
          <el-pagination
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            data-testid="production-plan-pagination"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>

        <el-divider />

        <div class="material-cost-section">
          <div class="title-group">
            <span class="title">大货成本物料明细表</span>
            <span class="sub-title">大货管理 / 大货成本物料明细（P1）</span>
          </div>

          <el-form :inline="true" :model="materialQuery" class="query-form">
            <el-form-item label="订单">
              <el-input
                v-model="materialQuery.sales_order"
                clearable
                placeholder="订单"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input
                v-model="materialQuery.material_item_code"
                clearable
                placeholder="物料编码"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="供应商">
              <el-input
                v-model="materialQuery.supplier"
                clearable
                placeholder="供应商"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="materialQuery.keyword"
                clearable
                placeholder="款号/客户/制单号"
                @keyup.enter="onMaterialSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="materialQuery.status" clearable placeholder="全部状态" style="width: 160px">
                <el-option label="草稿" value="draft" />
                <el-option label="已计划" value="planned" />
                <el-option label="已物料检查" value="material_checked" />
                <el-option label="工单待同步" value="work_order_pending" />
                <el-option label="已创建工单" value="work_order_created" />
                <el-option label="工序卡已同步" value="job_cards_synced" />
                <el-option label="已取消" value="cancelled" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="materialQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="materialQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onMaterialSearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onMaterialReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onMaterialRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onMaterialSearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onMaterialClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出明细', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('列设置', false)">列设置</el-button>
          </div>

          <el-alert
            v-if="materialError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成本物料明细加载失败：${materialError}`"
          />

          <el-table
            :data="materialRows"
            border
            v-loading="materialLoading"
            empty-text="暂无成本物料明细数据，请先完成物料检查或调整筛选条件"
          >
            <el-table-column prop="plan_no" label="生产制单" min-width="160" />
            <el-table-column label="订单信息" min-width="220">
              <template #default="scope">
                <div class="cell-stack">
                  <span class="primary-text">{{ scope.row.sales_order }}</span>
                  <span class="secondary-text">翻单号：{{ scope.row.sales_order_item || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="item_code" label="款号" min-width="140" />
            <el-table-column prop="material_item_code" label="物料编码" min-width="180" />
            <el-table-column label="供应商" min-width="140">
              <template #default="scope">{{ scope.row.supplier || '-' }}</template>
            </el-table-column>
            <el-table-column prop="qty_per_piece" label="单件用量" min-width="100" />
            <el-table-column prop="loss_rate" label="损耗率" min-width="90" />
            <el-table-column prop="required_qty" label="需求数量" min-width="100" />
            <el-table-column prop="estimated_unit_price" label="估算单价(元)" min-width="120" />
            <el-table-column prop="estimated_material_cost" label="估算成本(元)" min-width="120" />
            <el-table-column label="状态" min-width="120">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                  {{ statusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="检查时间" min-width="180">
              <template #default="scope">{{ scope.row.checked_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="170">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.plan_id)">查看</el-button>
                <el-button link @click="onGuardedAction('导出明细', false)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="materialQuery.page"
              :page-size="materialQuery.page_size"
              :total="materialTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onMaterialPageChange"
              @size-change="onMaterialSizeChange"
            />
          </div>
        </div>

        <el-divider />

        <div class="sales-forecast-section">
          <div class="title-group">
            <span class="title">大货销售预测明细表</span>
            <span class="sub-title">大货管理 / 大货销售预测明细（P1）</span>
          </div>

          <el-form :inline="true" :model="salesForecastQuery" class="query-form">
            <el-form-item label="订单">
              <el-input
                v-model="salesForecastQuery.sales_order"
                clearable
                placeholder="订单"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="款号">
              <el-input
                v-model="salesForecastQuery.item_code"
                clearable
                placeholder="款号"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="客户">
              <el-input
                v-model="salesForecastQuery.customer"
                clearable
                placeholder="客户"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="salesForecastQuery.keyword"
                clearable
                placeholder="制单号/翻单号/款号"
                @keyup.enter="onSalesForecastSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="salesForecastQuery.status" clearable placeholder="全部状态" style="width: 160px">
                <el-option label="草稿" value="draft" />
                <el-option label="已计划" value="planned" />
                <el-option label="已物料检查" value="material_checked" />
                <el-option label="工单待同步" value="work_order_pending" />
                <el-option label="已创建工单" value="work_order_created" />
                <el-option label="工序卡已同步" value="job_cards_synced" />
                <el-option label="已取消" value="cancelled" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="salesForecastQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="salesForecastQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onSalesForecastSearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onSalesForecastReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onSalesForecastRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onSalesForecastSearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onSalesForecastClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出销售预测', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('销售预测列设置', false)">列设置</el-button>
          </div>

          <el-alert
            v-if="salesForecastError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`销售预测明细加载失败：${salesForecastError}`"
          />

          <el-table
            :data="salesForecastRows"
            border
            v-loading="salesForecastLoading"
            empty-text="暂无销售预测明细数据，请调整筛选条件后重试"
          >
            <el-table-column prop="plan_no" label="生产制单" min-width="160" />
            <el-table-column label="订单信息" min-width="220">
              <template #default="scope">
                <div class="cell-stack">
                  <span class="primary-text">{{ scope.row.sales_order }}</span>
                  <span class="secondary-text">翻单号：{{ scope.row.sales_order_item || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="item_code" label="款号" min-width="140" />
            <el-table-column label="客户" min-width="160">
              <template #default="scope">{{ scope.row.customer || '-' }}</template>
            </el-table-column>
            <el-table-column prop="forecast_qty" label="预测数量" min-width="110" />
            <el-table-column prop="forecast_unit_price" label="预测单价(元)" min-width="120" />
            <el-table-column prop="forecast_amount" label="预测金额(元)" min-width="130" />
            <el-table-column label="交期" min-width="120">
              <template #default="scope">{{ scope.row.delivery_date || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                  {{ statusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="检查时间" min-width="180">
              <template #default="scope">{{ scope.row.checked_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="170">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.plan_id)">查看</el-button>
                <el-button link @click="onGuardedAction('导出销售预测', false)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="salesForecastQuery.page"
              :page-size="salesForecastQuery.page_size"
              :total="salesForecastTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onSalesForecastPageChange"
              @size-change="onSalesForecastSizeChange"
            />
          </div>
        </div>

        <el-divider />

        <div class="quote-section">
          <div class="title-group">
            <span class="title">报价单</span>
            <span class="sub-title">大货管理 / 报价单（P1）</span>
            <el-tag
              v-if="isProductionQuoteParity"
              type="success"
              effect="plain"
              data-testid="production-quote-parity-hint"
            >
              衣算云 / 大货管理 / 报价单
            </el-tag>
          </div>

          <el-form :inline="true" :model="quoteQuery" class="query-form">
            <el-form-item label="报价单号">
              <el-input
                v-model="quoteQuery.quote_no"
                clearable
                placeholder="报价单号"
                data-testid="production-quote-filter-quote-no"
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="订单号">
              <el-input
                v-model="quoteQuery.sales_order"
                clearable
                placeholder="订单号"
                data-testid="production-quote-filter-sales-order"
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="翻单号">
              <el-input
                v-model="quoteQuery.turnover_no"
                clearable
                placeholder="翻单号"
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="款号">
              <el-input
                v-model="quoteQuery.item_code"
                clearable
                placeholder="款号"
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="客户">
              <el-input
                v-model="quoteQuery.customer"
                clearable
                placeholder="客户"
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="quoteQuery.keyword"
                clearable
                placeholder="制单号/翻单号/款号"
                data-testid="production-quote-filter-keyword"
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="quoteQuery.status"
                clearable
                placeholder="全部状态"
                style="width: 160px"
                data-testid="production-quote-filter-status"
              >
                <el-option label="草稿" value="draft" />
                <el-option label="已计划" value="planned" />
                <el-option label="已物料检查" value="material_checked" />
                <el-option label="工单待同步" value="work_order_pending" />
                <el-option label="已创建工单" value="work_order_created" />
                <el-option label="工序卡已同步" value="job_cards_synced" />
                <el-option label="已取消" value="cancelled" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="quoteQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
                data-testid="production-quote-filter-from-date"
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="quoteQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
                data-testid="production-quote-filter-to-date"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :disabled="!canQuoteReadonlyInteractive"
                data-testid="production-quote-search"
                @click="onQuoteSearch"
              >
                搜索
              </el-button>
              <el-button :disabled="!canQuoteReadonlyInteractive" data-testid="production-quote-reset" @click="onQuoteReset">
                重置
              </el-button>
              <el-button :disabled="!canQuoteReadonlyInteractive" @click="onQuoteRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canQuoteReadonlyInteractive" data-testid="production-quote-apply-filters" @click="onQuoteSearch">
              筛选
            </el-button>
            <el-button :disabled="!canQuoteReadonlyInteractive" data-testid="production-quote-clear-filters" @click="onQuoteClearFilters">
              清空
            </el-button>
            <el-button :disabled="!canQuoteReadonlyInteractive" @click="onGuardedAction('导出报价单', false)">导出</el-button>
            <el-button :disabled="!canQuoteReadonlyInteractive" @click="onGuardedAction('报价单列设置', false)">列设置</el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="onGuardedAction('报价确认', true)"
            >
              确认
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="onGuardedAction('报价取消', true)"
            >
              取消
            </el-button>
          </div>

          <el-alert
            v-if="quoteError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`报价单加载失败：${quoteError}`"
          />

          <div class="quote-contract-shell" data-testid="production-quote-a004-contract-shell">
            <div class="quote-contract-header">
              <div class="cell-stack">
                <span class="primary-text">A004 报价草稿最小回读契约</span>
                <span class="secondary-text">
                  仅展示已验证的报价草稿字段、状态和详情回读；提交、审核、转订单和价格算法仍保持 blocked。
                </span>
              </div>
              <div class="quote-contract-tags">
                <el-tag type="success" effect="plain">VERIFIED_MINIMAL_DRAFT_SAVE_READBACK</el-tag>
                <el-tag type="warning" effect="plain">动作逻辑受限</el-tag>
              </div>
            </div>

            <div class="dev-cand-005-guard" data-testid="production-quote-dev-cand-005-guard">
              <div class="guard-status-row" aria-label="DEV-CAND-005 证据状态分层">
                <el-tag type="success" effect="plain">VERIFIED：字段/状态/最小回读</el-tag>
                <el-tag type="warning" effect="plain">PARTIAL：价格字段展示</el-tag>
                <el-tag type="info" effect="plain">UNKNOWN：算法口径</el-tag>
                <el-tag type="danger" effect="plain">BLOCKED：提交/审核/转订单</el-tag>
                <el-tag type="danger" effect="dark">NO-GO：生产/库存/财务</el-tag>
              </div>
              <p class="guard-note">
                DEV-CAND-005 仅统一 UI guard 表达；报价草稿仍只支持字段、状态和最小回读壳层，不提供写入动作；价格与收益口径仅作 blocked 说明。
              </p>
            </div>

            <div class="quote-contract-grid">
              <div
                v-for="field in quoteDraftReadbackFields"
                :key="field.key"
                class="quote-contract-field"
                :data-testid="`production-quote-contract-field-${field.key}`"
              >
                <span class="quote-contract-label">{{ field.label }}</span>
                <span class="quote-contract-value">{{ field.value || '-' }}</span>
                <el-tag class="quote-contract-source" size="small" effect="plain" :type="field.type">
                  {{ field.source }}
                </el-tag>
              </div>
            </div>

            <div class="quote-contract-boundary">
              <div class="cell-stack">
                <span class="primary-text">未知 / 阻断边界</span>
                <span class="secondary-text">这些内容只能做 UI 提示，不得实现为动作、算法或完整 1:1 流程。</span>
              </div>
              <div class="quote-boundary-tags">
                <el-tag
                  v-for="item in quoteDraftBlockedScopes"
                  :key="item"
                  type="danger"
                  effect="plain"
                  data-testid="production-quote-contract-blocked-scope"
                >
                  {{ item }}
                </el-tag>
              </div>
            </div>

            <div class="quote-contract-actions" data-testid="production-quote-contract-guarded-actions">
              <el-button
                v-for="action in quoteDraftGuardedActions"
                :key="action.label"
                disabled
                :type="action.type"
                data-action-type="write"
                data-write-guard="blocked:a004-contract"
              >
                {{ action.label }}（{{ action.state }}）
              </el-button>
            </div>
          </div>

          <el-table
            :data="quoteRows"
            border
            v-loading="quoteLoading"
            empty-text="暂无报价单数据，请调整筛选条件后重试"
          >
            <el-table-column prop="quote_no" label="报价单号" min-width="160" />
            <el-table-column prop="plan_no" label="生产制单" min-width="160" />
            <el-table-column label="订单信息" min-width="220">
              <template #default="scope">
                <div class="cell-stack">
                  <span class="primary-text">{{ scope.row.sales_order }}</span>
                  <span class="secondary-text">翻单号：{{ scope.row.sales_order_item || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="item_code" label="款号" min-width="140" />
            <el-table-column label="客户" min-width="160">
              <template #default="scope">{{ scope.row.customer || '-' }}</template>
            </el-table-column>
            <el-table-column prop="quote_qty" label="报价数量" min-width="110" />
            <el-table-column prop="quote_unit_price" label="报价单价(元)" min-width="130" />
            <el-table-column prop="quote_amount" label="报价金额(元)" min-width="130" />
            <el-table-column label="报价日期" min-width="170">
              <template #default="scope">{{ scope.row.quoted_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="交期" min-width="120">
              <template #default="scope">{{ scope.row.delivery_date || '-' }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                  {{ statusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="190">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.plan_id)">查看</el-button>
                <el-button link @click="onGuardedAction('打印报价单', false)">打印</el-button>
                <el-button link @click="onGuardedAction('导出报价单', false)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="quoteQuery.page"
              :page-size="quoteQuery.page_size"
              :total="quoteTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onQuotePageChange"
              @size-change="onQuoteSizeChange"
            />
          </div>
        </div>

        <el-divider />

        <div class="followup-template-section">
          <div class="title-group">
            <span class="title">跟进模板</span>
            <span class="sub-title">大货管理 / 跟进模板（P1）</span>
            <el-tag
              v-if="isProductionFollowupTemplateParity"
              type="success"
              effect="plain"
              data-testid="production-followup-template-parity-hint"
            >
              衣算云 / 大货管理 / 跟进模板
            </el-tag>
          </div>

          <el-form :inline="true" :model="followupTemplateQuery" class="query-form">
            <el-form-item label="模板编号">
              <el-input
                v-model="followupTemplateQuery.template_no"
                clearable
                placeholder="模板编号"
                data-testid="production-followup-template-filter-template-no"
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="模板名称">
              <el-input
                v-model="followupTemplateQuery.template_name"
                clearable
                placeholder="模板名称"
                data-testid="production-followup-template-filter-template-name"
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="模板类型">
              <el-select
                v-model="followupTemplateQuery.template_type"
                clearable
                placeholder="全部类型"
                style="width: 160px"
                data-testid="production-followup-template-filter-template-type"
              >
                <el-option label="基础跟进" value="基础跟进" />
                <el-option label="排期跟进" value="排期跟进" />
                <el-option label="物料跟进" value="物料跟进" />
                <el-option label="工单跟进" value="工单跟进" />
                <el-option label="生产跟进" value="生产跟进" />
                <el-option label="异常跟进" value="异常跟进" />
              </el-select>
            </el-form-item>
            <el-form-item label="款号">
              <el-input
                v-model="followupTemplateQuery.item_code"
                clearable
                placeholder="款号"
                data-testid="production-followup-template-filter-item-code"
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="followupTemplateQuery.keyword"
                clearable
                placeholder="模板号/模板名/制单号"
                data-testid="production-followup-template-filter-keyword"
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="followupTemplateQuery.status"
                clearable
                placeholder="全部状态"
                style="width: 160px"
                data-testid="production-followup-template-filter-status"
              >
                <el-option label="启用" value="enabled" />
                <el-option label="停用" value="disabled" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="followupTemplateQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
                data-testid="production-followup-template-filter-from-date"
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="followupTemplateQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
                data-testid="production-followup-template-filter-to-date"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :disabled="!canFollowupTemplateReadonlyInteractive"
                data-testid="production-followup-template-search"
                @click="onFollowupTemplateSearch"
              >
                搜索
              </el-button>
              <el-button
                :disabled="!canFollowupTemplateReadonlyInteractive"
                data-testid="production-followup-template-reset"
                @click="onFollowupTemplateReset"
              >
                重置
              </el-button>
              <el-button :disabled="!canFollowupTemplateReadonlyInteractive" @click="onFollowupTemplateRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              :disabled="!canFollowupTemplateReadonlyInteractive"
              data-testid="production-followup-template-apply-filters"
              @click="onFollowupTemplateSearch"
            >
              筛选
            </el-button>
            <el-button
              :disabled="!canFollowupTemplateReadonlyInteractive"
              data-testid="production-followup-template-clear-filters"
              @click="onFollowupTemplateClearFilters"
            >
              清空
            </el-button>
            <el-button :disabled="!canFollowupTemplateReadonlyInteractive" @click="onGuardedAction('导出跟进模板', false)">
              导出
            </el-button>
            <el-button :disabled="!canFollowupTemplateReadonlyInteractive" @click="onGuardedAction('跟进模板列设置', false)">
              列设置
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="onGuardedAction('新增跟进模板', true)"
            >
              新增
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="onGuardedAction('启用跟进模板', true)"
            >
              启用
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="onGuardedAction('停用跟进模板', true)"
            >
              停用
            </el-button>
          </div>

          <el-alert
            v-if="followupTemplateError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`跟进模板加载失败：${followupTemplateError}`"
            data-testid="production-followup-template-error-alert"
          />

          <el-table
            :data="followupTemplateRows"
            border
            v-loading="followupTemplateLoading"
            empty-text="暂无跟进模板数据，请调整筛选条件后重试"
            data-testid="production-followup-template-table"
          >
            <el-table-column prop="template_no" label="模板编号" min-width="160" />
            <el-table-column prop="template_name" label="模板名称" min-width="180" />
            <el-table-column prop="template_type" label="模板类型" min-width="120" />
            <el-table-column prop="trigger_node" label="触发节点" min-width="120" />
            <el-table-column prop="followup_role" label="跟进角色" min-width="120" />
            <el-table-column prop="followup_frequency" label="跟进频次" min-width="100" />
            <el-table-column prop="sla_hours" label="SLA(小时)" min-width="100" />
            <el-table-column prop="item_code" label="款号" min-width="130" />
            <el-table-column prop="company" label="公司" min-width="130" />
            <el-table-column label="状态" min-width="120">
              <template #default="scope">
                <el-tag :type="followupTemplateStatusTagType(scope.row.status)" effect="plain">
                  {{ followupTemplateStatusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="170">
              <template #default="scope">{{ scope.row.updated_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="240">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.template_id)">查看</el-button>
                <el-button
                  link
                  data-action-type="write"
                  data-write-guard="guarded:readonly"
                  @click="onGuardedAction('编辑跟进模板', true)"
                >
                  编辑
                </el-button>
                <el-button link @click="onGuardedAction('打印跟进模板', false)">打印</el-button>
                <el-button link @click="onGuardedAction('导出跟进模板', false)">导出</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="followupTemplateQuery.page"
              :page-size="followupTemplateQuery.page_size"
              :total="followupTemplateTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onFollowupTemplatePageChange"
              @size-change="onFollowupTemplateSizeChange"
            />
          </div>
        </div>

        <el-divider />

        <div class="order-io-quantity-section">
          <div class="title-group">
            <span class="title">下单进出数量明细表</span>
            <span class="sub-title">大货管理 / 下单进出数量明细（P1）</span>
          </div>

          <el-form :inline="true" :model="orderIOQuantityQuery" class="query-form">
            <el-form-item label="下单单号">
              <el-input
                v-model="orderIOQuantityQuery.sales_order"
                clearable
                placeholder="下单单号"
                @keyup.enter="onOrderIOQuantitySearch"
              />
            </el-form-item>
            <el-form-item label="订单行号">
              <el-input
                v-model="orderIOQuantityQuery.turnover_no"
                clearable
                placeholder="订单行号/翻单号"
                @keyup.enter="onOrderIOQuantitySearch"
              />
            </el-form-item>
            <el-form-item label="款号">
              <el-input
                v-model="orderIOQuantityQuery.item_code"
                clearable
                placeholder="款号"
                @keyup.enter="onOrderIOQuantitySearch"
              />
            </el-form-item>
            <el-form-item label="客户">
              <el-input
                v-model="orderIOQuantityQuery.customer"
                clearable
                placeholder="客户"
                @keyup.enter="onOrderIOQuantitySearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="orderIOQuantityQuery.keyword"
                clearable
                placeholder="制单号/下单号/款号"
                @keyup.enter="onOrderIOQuantitySearch"
              />
            </el-form-item>
            <el-form-item label="进出状态">
              <el-select
                v-model="orderIOQuantityQuery.io_status"
                clearable
                placeholder="全部状态"
                style="width: 160px"
              >
                <el-option label="待处理" value="pending" />
                <el-option label="进行中" value="in_progress" />
                <el-option label="已完成" value="done" />
                <el-option label="受阻" value="blocked" />
              </el-select>
            </el-form-item>
            <el-form-item label="生产状态">
              <el-select
                v-model="orderIOQuantityQuery.status"
                clearable
                placeholder="全部状态"
                style="width: 160px"
              >
                <el-option label="草稿" value="draft" />
                <el-option label="已计划" value="planned" />
                <el-option label="已物料检查" value="material_checked" />
                <el-option label="工单待同步" value="work_order_pending" />
                <el-option label="已创建工单" value="work_order_created" />
                <el-option label="工序卡已同步" value="job_cards_synced" />
                <el-option label="已取消" value="cancelled" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="orderIOQuantityQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="orderIOQuantityQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onOrderIOQuantitySearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onOrderIOQuantityReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onOrderIOQuantityRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onOrderIOQuantitySearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onOrderIOQuantityClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出进出数量明细', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('进出数量列设置', false)">列设置</el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="dev-cand-005:readonly-disabled"
              @click="onGuardedAction('同步进出数量', true)"
            >
              同步
            </el-button>
          </div>

          <el-alert
            v-if="orderIOQuantityError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`下单进出数量明细加载失败：${orderIOQuantityError}`"
          />

          <el-table
            :data="orderIOQuantityRows"
            border
            v-loading="orderIOQuantityLoading"
            empty-text="暂无下单进出数量明细，请调整筛选条件后重试"
          >
            <el-table-column prop="plan_no" label="制单号" min-width="160" />
            <el-table-column prop="sales_order" label="下单单号" min-width="160" />
            <el-table-column prop="sales_order_item" label="订单行号" min-width="160" />
            <el-table-column prop="customer" label="客户" min-width="140" />
            <el-table-column prop="item_code" label="款号" min-width="130" />
            <el-table-column prop="ordered_qty" label="下单数量" min-width="120" />
            <el-table-column prop="inbound_qty" label="入库数量" min-width="120" />
            <el-table-column prop="outbound_qty" label="出库数量" min-width="120" />
            <el-table-column prop="pending_inbound_qty" label="待入库" min-width="110" />
            <el-table-column prop="pending_outbound_qty" label="待出库" min-width="110" />
            <el-table-column prop="inbound_progress" label="入库进度(%)" min-width="120" />
            <el-table-column prop="outbound_progress" label="出库进度(%)" min-width="120" />
            <el-table-column label="进出状态" min-width="120">
              <template #default="scope">
                <el-tag :type="orderIOStatusTagType(scope.row.io_status)" effect="plain">
                  {{ orderIOStatusLabel(scope.row.io_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="生产状态" min-width="120">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                  {{ statusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="170">
              <template #default="scope">{{ scope.row.updated_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="220">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.plan_id)">查看</el-button>
                <el-button link @click="onGuardedAction('打印进出数量明细', false)">打印</el-button>
                <el-button link @click="onGuardedAction('导出进出数量明细', false)">导出</el-button>
                <el-button link @click="onGuardedAction('同步进出数量', true)">同步</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="orderIOQuantityQuery.page"
              :page-size="orderIOQuantityQuery.page_size"
              :total="orderIOQuantityTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onOrderIOQuantityPageChange"
              @size-change="onOrderIOQuantitySizeChange"
            />
          </div>
        </div>

        <el-divider />

        <div class="salesperson-performance-section">
          <div class="title-group">
            <span class="title">业务员业绩分析报表</span>
            <span class="sub-title">大货管理 / 业务员业绩分析（P1）</span>
          </div>

          <el-form :inline="true" :model="salespersonPerformanceQuery" class="query-form">
            <el-form-item label="业务员">
              <el-input
                v-model="salespersonPerformanceQuery.salesperson"
                clearable
                placeholder="业务员"
                @keyup.enter="onSalespersonPerformanceSearch"
              />
            </el-form-item>
            <el-form-item label="客户">
              <el-input
                v-model="salespersonPerformanceQuery.customer"
                clearable
                placeholder="客户"
                @keyup.enter="onSalespersonPerformanceSearch"
              />
            </el-form-item>
            <el-form-item label="款号">
              <el-input
                v-model="salespersonPerformanceQuery.item_code"
                clearable
                placeholder="款号"
                @keyup.enter="onSalespersonPerformanceSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="salespersonPerformanceQuery.keyword"
                clearable
                placeholder="制单号/订单号/业务员"
                @keyup.enter="onSalespersonPerformanceSearch"
              />
            </el-form-item>
            <el-form-item label="业绩状态">
              <el-select
                v-model="salespersonPerformanceQuery.performance_status"
                clearable
                placeholder="全部状态"
                style="width: 160px"
              >
                <el-option label="优秀" value="excellent" />
                <el-option label="达标" value="normal" />
                <el-option label="待提升" value="attention" />
                <el-option label="风险" value="risk" />
              </el-select>
            </el-form-item>
            <el-form-item label="生产状态">
              <el-select
                v-model="salespersonPerformanceQuery.status"
                clearable
                placeholder="全部状态"
                style="width: 160px"
              >
                <el-option label="草稿" value="draft" />
                <el-option label="已计划" value="planned" />
                <el-option label="已物料检查" value="material_checked" />
                <el-option label="工单待同步" value="work_order_pending" />
                <el-option label="已创建工单" value="work_order_created" />
                <el-option label="工序卡已同步" value="job_cards_synced" />
                <el-option label="已取消" value="cancelled" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始时间">
              <el-date-picker
                v-model="salespersonPerformanceQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始时间"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="salespersonPerformanceQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onSalespersonPerformanceSearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onSalespersonPerformanceReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onSalespersonPerformanceRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onSalespersonPerformanceSearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onSalespersonPerformanceClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出业绩分析报表', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('业绩分析列设置', false)">列设置</el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="dev-cand-005:readonly-disabled"
              @click="onGuardedAction('刷新业绩分析', true)"
            >
              刷新分析
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              data-write-guard="dev-cand-005:readonly-disabled"
              @click="onGuardedAction('同步业绩分析', true)"
            >
              同步
            </el-button>
          </div>

          <el-alert
            v-if="salespersonPerformanceError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`业务员业绩分析报表加载失败：${salespersonPerformanceError}`"
          />

          <el-table
            :data="salespersonPerformanceRows"
            border
            v-loading="salespersonPerformanceLoading"
            empty-text="暂无业务员业绩分析数据，请调整筛选条件后重试"
          >
            <el-table-column prop="salesperson" label="业务员" min-width="130" />
            <el-table-column prop="plan_no" label="制单号" min-width="150" />
            <el-table-column label="订单信息" min-width="220">
              <template #default="scope">
                <div class="cell-stack">
                  <span class="primary-text">{{ scope.row.sales_order }}</span>
                  <span class="secondary-text">订单行号：{{ scope.row.sales_order_item || '-' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="customer" label="客户" min-width="140" />
            <el-table-column prop="item_code" label="款号" min-width="130" />
            <el-table-column prop="ordered_qty" label="下单数量" min-width="120" />
            <el-table-column prop="completed_qty" label="完成数量" min-width="120" />
            <el-table-column label="完成率" min-width="110">
              <template #default="scope">{{ scope.row.completion_rate }}%</template>
            </el-table-column>
            <el-table-column prop="settled_amount" label="已结算金额(元)" min-width="140" />
            <el-table-column prop="pending_amount" label="待结算金额(元)" min-width="140" />
            <el-table-column label="业绩状态" min-width="120">
              <template #default="scope">
                <el-tag :type="salespersonPerformanceStatusTagType(scope.row.performance_status)" effect="plain">
                  {{ salespersonPerformanceStatusLabel(scope.row.performance_status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="生产状态" min-width="120">
              <template #default="scope">
                <el-tag :type="statusTagType(scope.row.status)" effect="plain">
                  {{ statusLabel(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" min-width="170">
              <template #default="scope">{{ scope.row.updated_at || '-' }}</template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="220">
              <template #default="scope">
                <el-button link type="primary" @click="goDetail(scope.row.plan_id)">查看</el-button>
                <el-button link @click="onGuardedAction('打印业绩分析报表', false)">打印</el-button>
                <el-button link @click="onGuardedAction('导出业绩分析报表', false)">导出</el-button>
                <el-button link @click="onGuardedAction('同步业绩分析', true)">同步</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="salespersonPerformanceQuery.page"
              :page-size="salespersonPerformanceQuery.page_size"
              :total="salespersonPerformanceTotal"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="onSalespersonPerformancePageChange"
              @size-change="onSalespersonPerformanceSizeChange"
            />
          </div>
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  createProductionPlan,
  fetchProductionFollowupTemplates,
  fetchProductionMaterialCostDetails,
  fetchProductionOrderIOQuantities,
  fetchProductionPlans,
  fetchProductionQuotes,
  fetchProductionSalespersonPerformance,
  type ProductionFollowupTemplateListItem,
  type ProductionMaterialCostListItem,
  type ProductionOrderIOQuantityListItem,
  type ProductionPlanListItem,
  type ProductionQuoteListItem,
  type ProductionSalespersonPerformanceListItem,
  fetchProductionSalesForecastDetails,
  type ProductionSalesForecastListItem,
} from '@/api/production'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const route = useRoute()
const permissionStore = usePermissionStore()

const currentParity = computed<string>(() => {
  const rawParity = route.query.parity
  if (Array.isArray(rawParity)) return String(rawParity[0] || '')
  if (typeof rawParity === 'string') return rawParity
  return ''
})

const isProductionQuoteParity = computed<boolean>(() => currentParity.value === 'production-quote')
const isProductionFollowupTemplateParity = computed<boolean>(() => currentParity.value === 'production-followup-template')

const loading = ref<boolean>(false)
const rows = ref<ProductionPlanListItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')
const creatingPlan = ref<boolean>(false)
const createPlanFeedback = ref<string>('')
const materialLoading = ref<boolean>(false)
const materialRows = ref<ProductionMaterialCostListItem[]>([])
const materialTotal = ref<number>(0)
const materialError = ref<string>('')
const salesForecastLoading = ref<boolean>(false)
const salesForecastRows = ref<ProductionSalesForecastListItem[]>([])
const salesForecastTotal = ref<number>(0)
const salesForecastError = ref<string>('')
const quoteLoading = ref<boolean>(false)
const quoteRows = ref<ProductionQuoteListItem[]>([])
const quoteTotal = ref<number>(0)
const quoteError = ref<string>('')
const followupTemplateLoading = ref<boolean>(false)
const followupTemplateRows = ref<ProductionFollowupTemplateListItem[]>([])
const followupTemplateTotal = ref<number>(0)
const followupTemplateError = ref<string>('')
const orderIOQuantityLoading = ref<boolean>(false)
const orderIOQuantityRows = ref<ProductionOrderIOQuantityListItem[]>([])
const orderIOQuantityTotal = ref<number>(0)
const orderIOQuantityError = ref<string>('')
const salespersonPerformanceLoading = ref<boolean>(false)
const salespersonPerformanceRows = ref<ProductionSalespersonPerformanceListItem[]>([])
const salespersonPerformanceTotal = ref<number>(0)
const salespersonPerformanceError = ref<string>('')

const canRead = computed<boolean>(() => {
  return permissionStore.state.buttonPermissions.read || permissionStore.state.actions.includes('production:read')
})
const canQuoteReadonlyInteractive = computed<boolean>(() => canRead.value || isProductionQuoteParity.value)
const canFollowupTemplateReadonlyInteractive = computed<boolean>(
  () => canRead.value || isProductionFollowupTemplateParity.value,
)
const canWriteGuarded = computed<boolean>(() => false)

const buildScenarioTag = (): string => {
  const now = new Date()
  const yyyy = String(now.getFullYear())
  const mm = String(now.getMonth() + 1).padStart(2, '0')
  const dd = String(now.getDate()).padStart(2, '0')
  const seq = String(Math.floor(Math.random() * 1000)).padStart(3, '0')
  return `Z003-PROD-PLAN-${yyyy}${mm}${dd}-${seq}`
}

const buildCarrierIdempotencyKey = (scenarioTag: string): string => {
  const random = Math.random().toString(36).slice(2, 10).toUpperCase()
  return `${scenarioTag}-ID-CR-${random}`.slice(0, 64)
}

const buildCarrierRequestId = (scenarioTag: string): string => {
  const random = Math.random().toString(36).slice(2, 8).toUpperCase()
  return `${scenarioTag}-RQ-CR-${random}`.slice(0, 64)
}

const createPlanForm = reactive({
  scenario_tag: buildScenarioTag(),
  sales_order: '',
  sales_order_item: '',
  item_code: '',
  bom_id: '',
  planned_qty: '1',
  planned_start_date: '',
  idempotency_key: '',
  request_id: '',
})

const resetCreatePlanForm = (): void => {
  createPlanForm.scenario_tag = buildScenarioTag()
  createPlanForm.sales_order = ''
  createPlanForm.sales_order_item = ''
  createPlanForm.item_code = ''
  createPlanForm.bom_id = ''
  createPlanForm.planned_qty = '1'
  createPlanForm.planned_start_date = ''
  createPlanForm.idempotency_key = buildCarrierIdempotencyKey(createPlanForm.scenario_tag)
  createPlanForm.request_id = buildCarrierRequestId(createPlanForm.scenario_tag)
}

const createPlanValidationError = computed<string | null>(() => {
  if (!createPlanForm.sales_order.trim()) return 'sales_order 不能为空'
  if (!createPlanForm.sales_order_item.trim()) return 'sales_order_item 不能为空'
  if (!createPlanForm.item_code.trim()) return 'item_code 不能为空'
  if (!createPlanForm.bom_id.trim() || Number.isNaN(Number(createPlanForm.bom_id)) || Number(createPlanForm.bom_id) <= 0) {
    return 'bom_id 必须为正整数'
  }
  if (!createPlanForm.planned_qty.trim() || Number.isNaN(Number(createPlanForm.planned_qty)) || Number(createPlanForm.planned_qty) <= 0) {
    return 'planned_qty 必须大于 0'
  }
  if (!createPlanForm.scenario_tag.trim()) return 'scenario_tag 不能为空'
  if (!createPlanForm.idempotency_key.trim()) return 'idempotency_key 不能为空'
  if (!createPlanForm.request_id.trim()) return 'request_id 不能为空'
  return null
})

const query = reactive({
  sales_order: '',
  keyword: '',
  turnover_no: '',
  from_date: '',
  to_date: '',
  status: '',
  page: 1,
  page_size: 20,
})

const materialQuery = reactive({
  sales_order: '',
  keyword: '',
  turnover_no: '',
  material_item_code: '',
  supplier: '',
  from_date: '',
  to_date: '',
  status: '',
  page: 1,
  page_size: 20,
})

const salesForecastQuery = reactive({
  sales_order: '',
  keyword: '',
  turnover_no: '',
  item_code: '',
  customer: '',
  from_date: '',
  to_date: '',
  status: '',
  page: 1,
  page_size: 20,
})

const quoteQuery = reactive({
  quote_no: '',
  sales_order: '',
  keyword: '',
  turnover_no: '',
  item_code: '',
  customer: '',
  from_date: '',
  to_date: '',
  status: '',
  page: 1,
  page_size: 20,
})

const followupTemplateQuery = reactive({
  template_no: '',
  template_name: '',
  template_type: '',
  item_code: '',
  keyword: '',
  from_date: '',
  to_date: '',
  status: '',
  page: 1,
  page_size: 20,
})

const orderIOQuantityQuery = reactive({
  sales_order: '',
  keyword: '',
  turnover_no: '',
  item_code: '',
  customer: '',
  from_date: '',
  to_date: '',
  status: '',
  io_status: '',
  page: 1,
  page_size: 20,
})

const salespersonPerformanceQuery = reactive({
  salesperson: '',
  keyword: '',
  item_code: '',
  customer: '',
  from_date: '',
  to_date: '',
  status: '',
  performance_status: '',
  page: 1,
  page_size: 20,
})

const quoteDraftReadbackFields = [
  { key: 'quoteNo', label: '报价单号', value: 'LY-APLUS-QUOTE-20260518-01', source: 'list/detail verified', type: 'success' },
  { key: 'status', label: '状态', value: '待提交', source: 'list/detail verified', type: 'success' },
  { key: 'customer', label: '客户', value: '测试123', source: 'list/detail verified', type: 'success' },
  { key: 'styleCode', label: '款号', value: 'LY-APLUS-STYLE-20260518-01', source: 'list/detail verified', type: 'success' },
  { key: 'styleName', label: '款名', value: 'LY-APLUS-STYLE-20260518-01', source: 'list/detail verified', type: 'success' },
  { key: 'quoteDate', label: '报价日期', value: '2026-05-18', source: 'detail verified', type: 'success' },
  { key: 'quotePerson', label: '报价人', value: '蓝小姐', source: 'list/detail verified', type: 'success' },
  { key: 'currency', label: '币种', value: 'RMB', source: 'detail verified', type: 'success' },
  { key: 'exchangeRate', label: '汇率', value: '1', source: 'detail verified', type: 'success' },
  { key: 'taxRate', label: '税率', value: '0%', source: 'field only / algorithm blocked', type: 'warning' },
  { key: 'color', label: '颜色', value: '已回读为空', source: 'detail verified empty', type: 'info' },
  { key: 'size', label: '尺码', value: '已回读为空', source: 'detail verified empty', type: 'info' },
  { key: 'taxIncludedPrice', label: '含税报价', value: '0', source: 'field only / algorithm blocked', type: 'warning' },
  { key: 'taxExcludedPrice', label: '不含税报价', value: '10', source: 'field only / algorithm blocked', type: 'warning' },
  { key: 'taxExcludedPriceRmb', label: '不含税报价RMB', value: '10', source: 'field only / algorithm blocked', type: 'warning' },
  { key: 'quoteCost', label: '报价成本', value: '0', source: 'field only / algorithm blocked', type: 'warning' },
  { key: 'grossProfit', label: '毛利', value: '10', source: 'field only / formula blocked', type: 'warning' },
  { key: 'remark', label: '备注', value: 'LY-APLUS-CAPTURE-20260518 / LY-APLUS-QUOTE-20260518-01', source: 'detail verified', type: 'success' },
  { key: 'createdBy', label: '创建人', value: '蓝小姐', source: 'system field / rule unknown', type: 'info' },
  { key: 'createdAt', label: '创建时间', value: '2026-05-18 17:34:47', source: 'system field / rule unknown', type: 'info' },
  { key: 'modifiedBy', label: '修改人', value: '蓝小姐', source: 'system field / rule unknown', type: 'info' },
  { key: 'modifiedAt', label: '修改时间', value: '2026-05-18 17:34:47', source: 'system field / rule unknown', type: 'info' },
] as const

const quoteDraftBlockedScopes = [
  '报价提交',
  '提交审核 / 审核 / 反审核',
  '删除 / 作废',
  '生成订单 / 转订单',
  '价格算法 / 利润公式 / 税价换算',
  '生产 / 库存 / 财务联动',
] as const

const quoteDraftGuardedActions = [
  { label: '保存并关闭', state: '仅 G2-FIX5 历史最小草稿验证，本页不执行', type: 'primary' },
  { label: '提交', state: 'blocked', type: 'danger' },
  { label: '审核', state: 'blocked', type: 'danger' },
  { label: '反审核', state: 'blocked', type: 'danger' },
  { label: '删除', state: 'blocked', type: 'danger' },
  { label: '作废', state: 'blocked', type: 'danger' },
  { label: '生成订单', state: 'blocked', type: 'danger' },
] as const

const statusLabel = (value: string): string => {
  const labels: Record<string, string> = {
    draft: '草稿',
    planned: '已计划',
    material_checked: '已物料检查',
    work_order_pending: '工单待同步',
    work_order_created: '已创建工单',
    job_cards_synced: '工序卡已同步',
    cancelled: '已取消',
    failed: '失败',
  }
  return labels[value] || value || '-'
}

const statusTagType = (value: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (value === 'job_cards_synced' || value === 'work_order_created') return 'success'
  if (value === 'failed' || value === 'cancelled') return 'danger'
  if (value === 'material_checked' || value === 'work_order_pending') return 'warning'
  return 'info'
}

const followupTemplateStatusLabel = (value: string): string => {
  if (value === 'enabled') return '启用'
  if (value === 'disabled') return '停用'
  return value || '-'
}

const followupTemplateStatusTagType = (value: string): 'success' | 'danger' | 'info' => {
  if (value === 'enabled') return 'success'
  if (value === 'disabled') return 'danger'
  return 'info'
}

const orderIOStatusLabel = (value: string): string => {
  if (value === 'pending') return '待处理'
  if (value === 'in_progress') return '进行中'
  if (value === 'done') return '已完成'
  if (value === 'blocked') return '受阻'
  return value || '-'
}

const orderIOStatusTagType = (value: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (value === 'done') return 'success'
  if (value === 'in_progress') return 'warning'
  if (value === 'blocked') return 'danger'
  return 'info'
}

const salespersonPerformanceStatusLabel = (value: string): string => {
  if (value === 'excellent') return '优秀'
  if (value === 'normal') return '达标'
  if (value === 'attention') return '待提升'
  if (value === 'risk') return '风险'
  return value || '-'
}

const salespersonPerformanceStatusTagType = (value: string): 'success' | 'warning' | 'danger' | 'info' => {
  if (value === 'excellent') return 'success'
  if (value === 'normal') return 'info'
  if (value === 'attention') return 'warning'
  if (value === 'risk') return 'danger'
  return 'info'
}

const materialProgressLabel = (status: string): string => {
  if (status === 'job_cards_synced' || status === 'work_order_created') return '已完成'
  if (status === 'material_checked' || status === 'work_order_pending') return '已检查'
  if (status === 'failed') return '异常待处理'
  return '待检查'
}

const scheduleText = (row: ProductionPlanListItem): string => {
  const qty = row.planned_qty ? String(row.planned_qty) : '-'
  const date = row.planned_start_date || '-'
  return `计划数 ${qty} / 开工 ${date}`
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const validateDateRange = (): boolean => {
  if (!query.from_date || !query.to_date) return true
  if (query.from_date <= query.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const validateMaterialDateRange = (): boolean => {
  if (!materialQuery.from_date || !materialQuery.to_date) return true
  if (materialQuery.from_date <= materialQuery.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const validateSalesForecastDateRange = (): boolean => {
  if (!salesForecastQuery.from_date || !salesForecastQuery.to_date) return true
  if (salesForecastQuery.from_date <= salesForecastQuery.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const validateQuoteDateRange = (): boolean => {
  if (!quoteQuery.from_date || !quoteQuery.to_date) return true
  if (quoteQuery.from_date <= quoteQuery.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const validateFollowupTemplateDateRange = (): boolean => {
  if (!followupTemplateQuery.from_date || !followupTemplateQuery.to_date) return true
  if (followupTemplateQuery.from_date <= followupTemplateQuery.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const validateOrderIOQuantityDateRange = (): boolean => {
  if (!orderIOQuantityQuery.from_date || !orderIOQuantityQuery.to_date) return true
  if (orderIOQuantityQuery.from_date <= orderIOQuantityQuery.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const validateSalespersonPerformanceDateRange = (): boolean => {
  if (!salespersonPerformanceQuery.from_date || !salespersonPerformanceQuery.to_date) return true
  if (salespersonPerformanceQuery.from_date <= salespersonPerformanceQuery.to_date) return true
  ElMessage.error('开始时间不能晚于结束时间')
  return false
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    lastError.value = ''
    return
  }

  loading.value = true
  lastError.value = ''
  try {
    const result = await fetchProductionPlans({
      sales_order: query.sales_order.trim() || undefined,
      keyword: query.keyword.trim() || undefined,
      turnover_no: query.turnover_no.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      status: query.status || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    rows.value = result.data.items
    total.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    lastError.value = message
    resetRows()
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const resetMaterialRows = (): void => {
  materialRows.value = []
  materialTotal.value = 0
}

const resetSalesForecastRows = (): void => {
  salesForecastRows.value = []
  salesForecastTotal.value = 0
}

const resetQuoteRows = (): void => {
  quoteRows.value = []
  quoteTotal.value = 0
}

const resetFollowupTemplateRows = (): void => {
  followupTemplateRows.value = []
  followupTemplateTotal.value = 0
}

const resetOrderIOQuantityRows = (): void => {
  orderIOQuantityRows.value = []
  orderIOQuantityTotal.value = 0
}

const resetSalespersonPerformanceRows = (): void => {
  salespersonPerformanceRows.value = []
  salespersonPerformanceTotal.value = 0
}

const loadMaterialRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetMaterialRows()
    materialError.value = ''
    return
  }

  materialLoading.value = true
  materialError.value = ''
  try {
    const result = await fetchProductionMaterialCostDetails({
      sales_order: materialQuery.sales_order.trim() || undefined,
      keyword: materialQuery.keyword.trim() || undefined,
      turnover_no: materialQuery.turnover_no.trim() || undefined,
      material_item_code: materialQuery.material_item_code.trim() || undefined,
      supplier: materialQuery.supplier.trim() || undefined,
      from_date: materialQuery.from_date || undefined,
      to_date: materialQuery.to_date || undefined,
      status: materialQuery.status || undefined,
      page: materialQuery.page,
      page_size: materialQuery.page_size,
    })
    materialRows.value = result.data.items
    materialTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    materialError.value = message
    resetMaterialRows()
    ElMessage.error(message)
  } finally {
    materialLoading.value = false
  }
}

const loadSalesForecastRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetSalesForecastRows()
    salesForecastError.value = ''
    return
  }

  salesForecastLoading.value = true
  salesForecastError.value = ''
  try {
    const result = await fetchProductionSalesForecastDetails({
      sales_order: salesForecastQuery.sales_order.trim() || undefined,
      keyword: salesForecastQuery.keyword.trim() || undefined,
      turnover_no: salesForecastQuery.turnover_no.trim() || undefined,
      item_code: salesForecastQuery.item_code.trim() || undefined,
      customer: salesForecastQuery.customer.trim() || undefined,
      from_date: salesForecastQuery.from_date || undefined,
      to_date: salesForecastQuery.to_date || undefined,
      status: salesForecastQuery.status || undefined,
      page: salesForecastQuery.page,
      page_size: salesForecastQuery.page_size,
    })
    salesForecastRows.value = result.data.items
    salesForecastTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    salesForecastError.value = message
    resetSalesForecastRows()
    ElMessage.error(message)
  } finally {
    salesForecastLoading.value = false
  }
}

const loadQuoteRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetQuoteRows()
    quoteError.value = ''
    return
  }

  quoteLoading.value = true
  quoteError.value = ''
  try {
    const result = await fetchProductionQuotes({
      quote_no: quoteQuery.quote_no.trim() || undefined,
      sales_order: quoteQuery.sales_order.trim() || undefined,
      keyword: quoteQuery.keyword.trim() || undefined,
      turnover_no: quoteQuery.turnover_no.trim() || undefined,
      item_code: quoteQuery.item_code.trim() || undefined,
      customer: quoteQuery.customer.trim() || undefined,
      from_date: quoteQuery.from_date || undefined,
      to_date: quoteQuery.to_date || undefined,
      status: quoteQuery.status || undefined,
      page: quoteQuery.page,
      page_size: quoteQuery.page_size,
    })
    quoteRows.value = result.data.items
    quoteTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    quoteError.value = message
    resetQuoteRows()
    ElMessage.error(message)
  } finally {
    quoteLoading.value = false
  }
}

const loadFollowupTemplateRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetFollowupTemplateRows()
    followupTemplateError.value = ''
    return
  }

  followupTemplateLoading.value = true
  followupTemplateError.value = ''
  try {
    const result = await fetchProductionFollowupTemplates({
      template_no: followupTemplateQuery.template_no.trim() || undefined,
      template_name: followupTemplateQuery.template_name.trim() || undefined,
      template_type: followupTemplateQuery.template_type.trim() || undefined,
      item_code: followupTemplateQuery.item_code.trim() || undefined,
      keyword: followupTemplateQuery.keyword.trim() || undefined,
      from_date: followupTemplateQuery.from_date || undefined,
      to_date: followupTemplateQuery.to_date || undefined,
      status: followupTemplateQuery.status || undefined,
      page: followupTemplateQuery.page,
      page_size: followupTemplateQuery.page_size,
    })
    followupTemplateRows.value = result.data.items
    followupTemplateTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    followupTemplateError.value = message
    resetFollowupTemplateRows()
    ElMessage.error(message)
  } finally {
    followupTemplateLoading.value = false
  }
}

const loadOrderIOQuantityRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetOrderIOQuantityRows()
    orderIOQuantityError.value = ''
    return
  }

  orderIOQuantityLoading.value = true
  orderIOQuantityError.value = ''
  try {
    const result = await fetchProductionOrderIOQuantities({
      sales_order: orderIOQuantityQuery.sales_order.trim() || undefined,
      keyword: orderIOQuantityQuery.keyword.trim() || undefined,
      turnover_no: orderIOQuantityQuery.turnover_no.trim() || undefined,
      item_code: orderIOQuantityQuery.item_code.trim() || undefined,
      customer: orderIOQuantityQuery.customer.trim() || undefined,
      from_date: orderIOQuantityQuery.from_date || undefined,
      to_date: orderIOQuantityQuery.to_date || undefined,
      status: orderIOQuantityQuery.status || undefined,
      io_status: orderIOQuantityQuery.io_status || undefined,
      page: orderIOQuantityQuery.page,
      page_size: orderIOQuantityQuery.page_size,
    })
    orderIOQuantityRows.value = result.data.items
    orderIOQuantityTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    orderIOQuantityError.value = message
    resetOrderIOQuantityRows()
    ElMessage.error(message)
  } finally {
    orderIOQuantityLoading.value = false
  }
}

const loadSalespersonPerformanceRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetSalespersonPerformanceRows()
    salespersonPerformanceError.value = ''
    return
  }

  salespersonPerformanceLoading.value = true
  salespersonPerformanceError.value = ''
  try {
    const result = await fetchProductionSalespersonPerformance({
      salesperson: salespersonPerformanceQuery.salesperson.trim() || undefined,
      keyword: salespersonPerformanceQuery.keyword.trim() || undefined,
      item_code: salespersonPerformanceQuery.item_code.trim() || undefined,
      customer: salespersonPerformanceQuery.customer.trim() || undefined,
      from_date: salespersonPerformanceQuery.from_date || undefined,
      to_date: salespersonPerformanceQuery.to_date || undefined,
      status: salespersonPerformanceQuery.status || undefined,
      performance_status: salespersonPerformanceQuery.performance_status || undefined,
      page: salespersonPerformanceQuery.page,
      page_size: salespersonPerformanceQuery.page_size,
    })
    salespersonPerformanceRows.value = result.data.items
    salespersonPerformanceTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    salespersonPerformanceError.value = message
    resetSalespersonPerformanceRows()
    ElMessage.error(message)
  } finally {
    salespersonPerformanceLoading.value = false
  }
}

const onSearch = (): void => {
  if (!validateDateRange()) return
  query.page = 1
  void loadRows()
}

const onReset = (): void => {
  query.sales_order = ''
  query.keyword = ''
  query.turnover_no = ''
  query.from_date = ''
  query.to_date = ''
  query.status = ''
  query.page = 1
  query.page_size = 20
  void loadRows()
}

const onClearFilters = (): void => {
  query.sales_order = ''
  query.keyword = ''
  query.turnover_no = ''
  query.from_date = ''
  query.to_date = ''
  query.status = ''
}

const onMaterialSearch = (): void => {
  if (!validateMaterialDateRange()) return
  materialQuery.page = 1
  void loadMaterialRows()
}

const onMaterialReset = (): void => {
  materialQuery.sales_order = ''
  materialQuery.keyword = ''
  materialQuery.turnover_no = ''
  materialQuery.material_item_code = ''
  materialQuery.supplier = ''
  materialQuery.from_date = ''
  materialQuery.to_date = ''
  materialQuery.status = ''
  materialQuery.page = 1
  materialQuery.page_size = 20
  void loadMaterialRows()
}

const onMaterialRefresh = (): void => {
  void loadMaterialRows()
}

const onMaterialClearFilters = (): void => {
  materialQuery.sales_order = ''
  materialQuery.keyword = ''
  materialQuery.turnover_no = ''
  materialQuery.material_item_code = ''
  materialQuery.supplier = ''
  materialQuery.from_date = ''
  materialQuery.to_date = ''
  materialQuery.status = ''
}

const onSalesForecastSearch = (): void => {
  if (!validateSalesForecastDateRange()) return
  salesForecastQuery.page = 1
  void loadSalesForecastRows()
}

const onSalesForecastReset = (): void => {
  salesForecastQuery.sales_order = ''
  salesForecastQuery.keyword = ''
  salesForecastQuery.turnover_no = ''
  salesForecastQuery.item_code = ''
  salesForecastQuery.customer = ''
  salesForecastQuery.from_date = ''
  salesForecastQuery.to_date = ''
  salesForecastQuery.status = ''
  salesForecastQuery.page = 1
  salesForecastQuery.page_size = 20
  void loadSalesForecastRows()
}

const onSalesForecastRefresh = (): void => {
  void loadSalesForecastRows()
}

const onSalesForecastClearFilters = (): void => {
  salesForecastQuery.sales_order = ''
  salesForecastQuery.keyword = ''
  salesForecastQuery.turnover_no = ''
  salesForecastQuery.item_code = ''
  salesForecastQuery.customer = ''
  salesForecastQuery.from_date = ''
  salesForecastQuery.to_date = ''
  salesForecastQuery.status = ''
}

const onQuoteSearch = (): void => {
  if (!validateQuoteDateRange()) return
  quoteQuery.page = 1
  void loadQuoteRows()
}

const onQuoteReset = (): void => {
  quoteQuery.quote_no = ''
  quoteQuery.sales_order = ''
  quoteQuery.keyword = ''
  quoteQuery.turnover_no = ''
  quoteQuery.item_code = ''
  quoteQuery.customer = ''
  quoteQuery.from_date = ''
  quoteQuery.to_date = ''
  quoteQuery.status = ''
  quoteQuery.page = 1
  quoteQuery.page_size = 20
  void loadQuoteRows()
}

const onQuoteRefresh = (): void => {
  void loadQuoteRows()
}

const onQuoteClearFilters = (): void => {
  quoteQuery.quote_no = ''
  quoteQuery.sales_order = ''
  quoteQuery.keyword = ''
  quoteQuery.turnover_no = ''
  quoteQuery.item_code = ''
  quoteQuery.customer = ''
  quoteQuery.from_date = ''
  quoteQuery.to_date = ''
  quoteQuery.status = ''
}

const onFollowupTemplateSearch = (): void => {
  if (!validateFollowupTemplateDateRange()) return
  followupTemplateQuery.page = 1
  void loadFollowupTemplateRows()
}

const onFollowupTemplateReset = (): void => {
  followupTemplateQuery.template_no = ''
  followupTemplateQuery.template_name = ''
  followupTemplateQuery.template_type = ''
  followupTemplateQuery.item_code = ''
  followupTemplateQuery.keyword = ''
  followupTemplateQuery.from_date = ''
  followupTemplateQuery.to_date = ''
  followupTemplateQuery.status = ''
  followupTemplateQuery.page = 1
  followupTemplateQuery.page_size = 20
  void loadFollowupTemplateRows()
}

const onFollowupTemplateRefresh = (): void => {
  void loadFollowupTemplateRows()
}

const onFollowupTemplateClearFilters = (): void => {
  followupTemplateQuery.template_no = ''
  followupTemplateQuery.template_name = ''
  followupTemplateQuery.template_type = ''
  followupTemplateQuery.item_code = ''
  followupTemplateQuery.keyword = ''
  followupTemplateQuery.from_date = ''
  followupTemplateQuery.to_date = ''
  followupTemplateQuery.status = ''
}

const onOrderIOQuantitySearch = (): void => {
  if (!validateOrderIOQuantityDateRange()) return
  orderIOQuantityQuery.page = 1
  void loadOrderIOQuantityRows()
}

const onOrderIOQuantityReset = (): void => {
  orderIOQuantityQuery.sales_order = ''
  orderIOQuantityQuery.keyword = ''
  orderIOQuantityQuery.turnover_no = ''
  orderIOQuantityQuery.item_code = ''
  orderIOQuantityQuery.customer = ''
  orderIOQuantityQuery.from_date = ''
  orderIOQuantityQuery.to_date = ''
  orderIOQuantityQuery.status = ''
  orderIOQuantityQuery.io_status = ''
  orderIOQuantityQuery.page = 1
  orderIOQuantityQuery.page_size = 20
  void loadOrderIOQuantityRows()
}

const onOrderIOQuantityRefresh = (): void => {
  void loadOrderIOQuantityRows()
}

const onOrderIOQuantityClearFilters = (): void => {
  orderIOQuantityQuery.sales_order = ''
  orderIOQuantityQuery.keyword = ''
  orderIOQuantityQuery.turnover_no = ''
  orderIOQuantityQuery.item_code = ''
  orderIOQuantityQuery.customer = ''
  orderIOQuantityQuery.from_date = ''
  orderIOQuantityQuery.to_date = ''
  orderIOQuantityQuery.status = ''
  orderIOQuantityQuery.io_status = ''
}

const onSalespersonPerformanceSearch = (): void => {
  if (!validateSalespersonPerformanceDateRange()) return
  salespersonPerformanceQuery.page = 1
  void loadSalespersonPerformanceRows()
}

const onSalespersonPerformanceReset = (): void => {
  salespersonPerformanceQuery.salesperson = ''
  salespersonPerformanceQuery.keyword = ''
  salespersonPerformanceQuery.item_code = ''
  salespersonPerformanceQuery.customer = ''
  salespersonPerformanceQuery.from_date = ''
  salespersonPerformanceQuery.to_date = ''
  salespersonPerformanceQuery.status = ''
  salespersonPerformanceQuery.performance_status = ''
  salespersonPerformanceQuery.page = 1
  salespersonPerformanceQuery.page_size = 20
  void loadSalespersonPerformanceRows()
}

const onSalespersonPerformanceRefresh = (): void => {
  void loadSalespersonPerformanceRows()
}

const onSalespersonPerformanceClearFilters = (): void => {
  salespersonPerformanceQuery.salesperson = ''
  salespersonPerformanceQuery.keyword = ''
  salespersonPerformanceQuery.item_code = ''
  salespersonPerformanceQuery.customer = ''
  salespersonPerformanceQuery.from_date = ''
  salespersonPerformanceQuery.to_date = ''
  salespersonPerformanceQuery.status = ''
  salespersonPerformanceQuery.performance_status = ''
}

const submitCreatePlan = async (): Promise<void> => {
  if (!canWriteGuarded.value) {
    ElMessage.warning('无新增生产计划权限')
    return
  }
  if (createPlanValidationError.value) {
    ElMessage.warning(createPlanValidationError.value)
    return
  }
  try {
    creatingPlan.value = true
    const result = await createProductionPlan(
      {
        sales_order: createPlanForm.sales_order.trim(),
        sales_order_item: createPlanForm.sales_order_item.trim(),
        item_code: createPlanForm.item_code.trim(),
        bom_id: Number(createPlanForm.bom_id),
        planned_qty: createPlanForm.planned_qty.trim(),
        planned_start_date: createPlanForm.planned_start_date || undefined,
        scenario_tag: createPlanForm.scenario_tag.trim(),
        operation: 'create',
        idempotency_key: createPlanForm.idempotency_key.trim(),
      },
      createPlanForm.request_id.trim(),
    )
    createPlanFeedback.value = `生产计划创建成功：${result.data.plan_no}`
    ElMessage.success(createPlanFeedback.value)
    query.page = 1
    await loadRows()
  } catch (error) {
    const message = (error as Error).message || '生产计划创建失败'
    createPlanFeedback.value = message
    ElMessage.error(message)
  } finally {
    creatingPlan.value = false
  }
}

const onGuardedAction = (actionName: string, isWrite: boolean): void => {
  if (isWrite && !canWriteGuarded.value) {
    ElMessage.warning(`无 ${actionName} 权限，当前保持禁用态`)
    return
  }
  if (isWrite) {
    ElMessage.warning(`${actionName}仅保留按钮对齐，当前本地首版未开放写入`)
    return
  }
  ElMessage.info(`${actionName}已保留入口，当前本地首版暂不执行`)
}

const goDetail = (planId: number): void => {
  router.push({ path: '/production/plans/detail', query: { id: String(planId) } })
}

const onPageChange = (page: number): void => {
  query.page = page
  void loadRows()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  void loadRows()
}

const onMaterialPageChange = (page: number): void => {
  materialQuery.page = page
  void loadMaterialRows()
}

const onMaterialSizeChange = (size: number): void => {
  materialQuery.page_size = size
  materialQuery.page = 1
  void loadMaterialRows()
}

const onSalesForecastPageChange = (page: number): void => {
  salesForecastQuery.page = page
  void loadSalesForecastRows()
}

const onSalesForecastSizeChange = (size: number): void => {
  salesForecastQuery.page_size = size
  salesForecastQuery.page = 1
  void loadSalesForecastRows()
}

const onQuotePageChange = (page: number): void => {
  quoteQuery.page = page
  void loadQuoteRows()
}

const onQuoteSizeChange = (size: number): void => {
  quoteQuery.page_size = size
  quoteQuery.page = 1
  void loadQuoteRows()
}

const onFollowupTemplatePageChange = (page: number): void => {
  followupTemplateQuery.page = page
  void loadFollowupTemplateRows()
}

const onFollowupTemplateSizeChange = (size: number): void => {
  followupTemplateQuery.page_size = size
  followupTemplateQuery.page = 1
  void loadFollowupTemplateRows()
}

const onOrderIOQuantityPageChange = (page: number): void => {
  orderIOQuantityQuery.page = page
  void loadOrderIOQuantityRows()
}

const onOrderIOQuantitySizeChange = (size: number): void => {
  orderIOQuantityQuery.page_size = size
  orderIOQuantityQuery.page = 1
  void loadOrderIOQuantityRows()
}

const onSalespersonPerformancePageChange = (page: number): void => {
  salespersonPerformanceQuery.page = page
  void loadSalespersonPerformanceRows()
}

const onSalespersonPerformanceSizeChange = (size: number): void => {
  salespersonPerformanceQuery.page_size = size
  salespersonPerformanceQuery.page = 1
  void loadSalespersonPerformanceRows()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('production')
  } catch (error) {
    const message = (error as Error).message
    lastError.value = message
    ElMessage.error(message)
    return
  }
  resetCreatePlanForm()
  if (canRead.value) {
    await loadRows()
    await loadMaterialRows()
    await loadSalesForecastRows()
    await loadQuoteRows()
    await loadFollowupTemplateRows()
    await loadOrderIOQuantityRows()
    await loadSalespersonPerformanceRows()
  }
})
</script>

<style scoped>
.production-followup-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-group {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.query-form {
  margin-bottom: 8px;
}

.toolbar-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.error-alert {
  margin-bottom: 12px;
}

.cell-stack {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.primary-text {
  font-weight: 500;
}

.secondary-text {
  color: var(--el-text-color-secondary);
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.material-cost-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.sales-forecast-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quote-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quote-contract-shell {
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-blank);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quote-contract-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.quote-contract-tags,
.quote-boundary-tags,
.quote-contract-actions,
.guard-status-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dev-cand-005-guard {
  border: 1px dashed var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-light);
  padding: 10px;
}

.guard-note {
  margin: 8px 0 0;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}

.quote-contract-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 8px;
}

.quote-contract-field {
  min-width: 0;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quote-contract-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.quote-contract-value {
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 600;
  overflow-wrap: anywhere;
}

.quote-contract-source {
  align-self: flex-start;
  max-width: 100%;
  white-space: normal;
  height: auto;
  line-height: 1.4;
  padding-top: 2px;
  padding-bottom: 2px;
}

.quote-contract-boundary {
  border-top: 1px dashed var(--el-border-color);
  padding-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

@media (max-width: 640px) {
  .quote-contract-header {
    flex-direction: column;
  }
}

.followup-template-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-io-quantity-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.salesperson-performance-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
