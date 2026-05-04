<template>
  <div class="production-followup-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">大货跟进</span>
            <span class="sub-title">大货管理 / 大货跟进</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="订单">
          <el-input
            v-model="query.sales_order"
            clearable
            placeholder="订单"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="款号/款名">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="请输入"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="翻单号">
          <el-input
            v-model="query.turnover_no"
            clearable
            placeholder="翻单号"
            @keyup.enter="onSearch"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 160px">
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
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canRead" @click="onSearch">搜索</el-button>
          <el-button :disabled="!canRead" @click="onReset">重置</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-row">
        <el-button :disabled="!canRead" @click="onSearch">筛选</el-button>
        <el-button :disabled="!canRead" @click="onClearFilters">清空</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('确定', true)">确定</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('标志已读', true)">标志已读</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('删除消息', true)">删除消息</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('新增消息', true)">新增消息</el-button>
        <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('保存', true)">保存</el-button>
      </div>

      <el-alert
        v-if="lastError"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`大货跟进数据加载失败：${lastError}`"
      />

      <el-empty v-if="!canRead" description="无大货跟进查看权限" />
      <template v-else>
        <el-table
          :data="rows"
          border
          v-loading="loading"
          empty-text="暂无大货跟进数据，请调整筛选条件后重试"
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
              <el-button link type="primary" @click="goDetail(scope.row.id)">跟进</el-button>
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
          </div>

          <el-form :inline="true" :model="quoteQuery" class="query-form">
            <el-form-item label="报价单号">
              <el-input
                v-model="quoteQuery.quote_no"
                clearable
                placeholder="报价单号"
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="订单">
              <el-input
                v-model="quoteQuery.sales_order"
                clearable
                placeholder="订单"
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
                @keyup.enter="onQuoteSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="quoteQuery.status" clearable placeholder="全部状态" style="width: 160px">
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
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="quoteQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onQuoteSearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onQuoteReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onQuoteRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onQuoteSearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onQuoteClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出报价单', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('报价单列设置', false)">列设置</el-button>
            <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('报价确认', true)">
              确认
            </el-button>
            <el-button :disabled="!canWriteGuarded" data-action-type="write" @click="onGuardedAction('报价取消', true)">
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
          </div>

          <el-form :inline="true" :model="followupTemplateQuery" class="query-form">
            <el-form-item label="模板编号">
              <el-input
                v-model="followupTemplateQuery.template_no"
                clearable
                placeholder="模板编号"
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="模板名称">
              <el-input
                v-model="followupTemplateQuery.template_name"
                clearable
                placeholder="模板名称"
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="模板类型">
              <el-select
                v-model="followupTemplateQuery.template_type"
                clearable
                placeholder="全部类型"
                style="width: 160px"
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
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="关键字">
              <el-input
                v-model="followupTemplateQuery.keyword"
                clearable
                placeholder="模板号/模板名/制单号"
                @keyup.enter="onFollowupTemplateSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="followupTemplateQuery.status" clearable placeholder="全部状态" style="width: 160px">
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
              />
            </el-form-item>
            <el-form-item label="结束时间">
              <el-date-picker
                v-model="followupTemplateQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束时间"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :disabled="!canRead" @click="onFollowupTemplateSearch">搜索</el-button>
              <el-button :disabled="!canRead" @click="onFollowupTemplateReset">重置</el-button>
              <el-button :disabled="!canRead" @click="onFollowupTemplateRefresh">刷新</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onFollowupTemplateSearch">筛选</el-button>
            <el-button :disabled="!canRead" @click="onFollowupTemplateClearFilters">清空</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('导出跟进模板', false)">导出</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('跟进模板列设置', false)">列设置</el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              @click="onGuardedAction('新增跟进模板', true)"
            >
              新增
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
              @click="onGuardedAction('启用跟进模板', true)"
            >
              启用
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
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
          />

          <el-table
            :data="followupTemplateRows"
            border
            v-loading="followupTemplateLoading"
            empty-text="暂无跟进模板数据，请调整筛选条件后重试"
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
                <el-button link @click="onGuardedAction('编辑跟进模板', true)">编辑</el-button>
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
              @click="onGuardedAction('刷新业绩分析', true)"
            >
              刷新分析
            </el-button>
            <el-button
              :disabled="!canWriteGuarded"
              data-action-type="write"
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
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
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
const permissionStore = usePermissionStore()

const loading = ref<boolean>(false)
const rows = ref<ProductionPlanListItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')
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
const canWriteGuarded = computed<boolean>(() => {
  return permissionStore.state.buttonPermissions.plan_create || permissionStore.state.actions.includes('production:plan_create')
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
