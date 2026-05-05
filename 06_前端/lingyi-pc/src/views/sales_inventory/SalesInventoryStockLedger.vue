<template>
  <div class="sales-inventory-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">成品进销存报表</span>
            <span class="sub-title">成品进销存 / 成品进销存报表</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="单号">
          <el-input v-model="query.no" clearable placeholder="单号" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="款式">
          <el-input v-model="query.style" clearable placeholder="款式" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="仓库">
          <el-input v-model="query.warehouse" clearable placeholder="请输入" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束日期"
            clearable
          />
        </el-form-item>
        <el-form-item label="搜索">
          <el-input v-model="query.keyword" clearable placeholder="请输入" @keyup.enter="onSearch" />
        </el-form-item>
        <el-form-item>
          <el-button :disabled="!canRead" @click="onReset">重置</el-button>
          <el-button type="primary" :disabled="!canRead" @click="onSearch">查询</el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-row">
        <el-button :disabled="!canRead" @click="onGuardedAction('质检')">质检</el-button>
        <el-button :disabled="!canRead" @click="onReset">清空</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('确定')">确定</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('标志已读')">标志已读</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('消息移除态')">消息移除态</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('消息待补态')">消息待补态</el-button>
        <el-button :disabled="!canRead" @click="onSearch">搜索</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('留档态')">留档态</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('回退态')">回退态</el-button>
        <el-button :disabled="!canRead" @click="onGuardedAction('重置列')">重置列</el-button>
        <el-button :disabled="!canRead" @click="loadRows">刷新</el-button>
        <el-button :disabled="!canExport" @click="onGuardedAction('导出')">导出</el-button>
        <el-button :disabled="!canExport" @click="onGuardedAction('打印')">打印</el-button>
      </div>

      <el-alert
        v-if="lastError"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`成品进销存报表加载失败：${lastError}`"
      />

      <el-empty v-if="!canRead" description="无成品进销存查看权限" />
      <template v-else>
        <div class="summary-row">
          <el-tag type="info" effect="plain">记录数：{{ total }}</el-tag>
          <el-tag type="success" effect="plain">数量合计：{{ totalQty }}</el-tag>
        </div>

        <el-table
          :data="rows"
          border
          v-loading="loading"
          empty-text="暂无成品进销存报表数据，请调整筛选条件后重试"
        >
          <el-table-column label="图片" width="80">
            <template #default="scope">
              <el-avatar v-if="scope.row.image_url" :src="scope.row.image_url" :size="32" />
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="processing_no" label="加工单号" min-width="130" />
          <el-table-column prop="production_order" label="生产制单" min-width="130" />
          <el-table-column prop="order_no" label="订单号" min-width="140" />
          <el-table-column prop="item_code" label="款号" min-width="120" />
          <el-table-column prop="item_name" label="款名" min-width="140" />
          <el-table-column prop="warehouse" label="仓库" min-width="120" />
          <el-table-column prop="season" label="季节" min-width="100" />
          <el-table-column prop="style_type" label="款式类型" min-width="120" />
          <el-table-column label="数量" width="110">
            <template #default="scope">{{ formatAmount(scope.row.qty) }}</template>
          </el-table-column>
          <el-table-column prop="receipt_date" label="收货日期" min-width="120" />
          <el-table-column label="操作" min-width="90" fixed="right">
            <template #default>
              <el-button link type="primary" @click="onGuardedAction('质检')">质检</el-button>
            </template>
          </el-table-column>
          <el-table-column prop="week_day_0" label="日" width="70" />
          <el-table-column prop="week_day_1" label="一" width="70" />
          <el-table-column prop="week_day_2" label="二" width="70" />
          <el-table-column prop="week_day_3" label="三" width="70" />
          <el-table-column prop="week_day_4" label="四" width="70" />
          <el-table-column prop="week_day_5" label="五" width="70" />
          <el-table-column prop="week_day_6" label="六" width="70" />
          <el-table-column prop="message_title" label="标题" min-width="120" />
          <el-table-column prop="sent_at" label="发送时间" min-width="130" />
          <el-table-column prop="message_status" label="状态" min-width="100" />
          <el-table-column prop="sender" label="发送人" min-width="110" />
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

        <section class="material-transfer-section" data-testid="material-transfer-section">
          <div class="section-header">
            <div class="title-group">
              <span class="title">物料调仓</span>
              <span class="sub-title">TASK-Y44B-P1-01 / 只读语义</span>
            </div>
            <el-tag type="warning" effect="plain">共享路由增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="materialTransferQuery" class="query-form">
            <el-form-item label="物料编码">
              <el-input
                v-model="materialTransferQuery.item_code"
                clearable
                placeholder="物料编码"
                @keyup.enter="onMaterialTransferSearch"
              />
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="materialTransferQuery.keyword"
                clearable
                placeholder="单号/物料/经办人"
                @keyup.enter="onMaterialTransferSearch"
              />
            </el-form-item>
            <el-form-item label="来源仓">
              <el-input
                v-model="materialTransferQuery.source_warehouse"
                clearable
                placeholder="来源仓"
                @keyup.enter="onMaterialTransferSearch"
              />
            </el-form-item>
            <el-form-item label="目标仓">
              <el-input
                v-model="materialTransferQuery.target_warehouse"
                clearable
                placeholder="目标仓"
                @keyup.enter="onMaterialTransferSearch"
              />
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="materialTransferQuery.status" clearable placeholder="全部状态" style="width: 140px">
                <el-option label="待确认" value="待确认" />
                <el-option label="调拨中" value="调拨中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="materialTransferQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="materialTransferQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onMaterialTransferReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onMaterialTransferSearch">查询</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button :disabled="!canRead" @click="onGuardedAction('新建调仓')">新建调仓</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('审核提示')">审核提示</el-button>
            <el-button :disabled="!canRead" @click="onGuardedAction('校验提示')">校验提示</el-button>
            <el-button :disabled="!canExport" @click="onGuardedAction('导出调仓')">导出</el-button>
            <el-button :disabled="!canExport" @click="onGuardedAction('打印调仓')">打印</el-button>
          </div>

          <el-alert
            v-if="materialTransferError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`物料调仓加载失败：${materialTransferError}`"
          />

          <el-empty v-if="!canRead" description="无物料调仓查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">调仓记录：{{ materialTransferTotal }}</el-tag>
              <el-tag type="success" effect="plain">调拨总量：{{ materialTransferQtyTotal }}</el-tag>
              <el-tag type="warning" effect="plain">差异总量：{{ materialTransferDiffTotal }}</el-tag>
            </div>

            <el-table
              :data="materialTransferRows"
              border
              v-loading="materialTransferLoading"
              empty-text="暂无物料调仓数据，请调整筛选条件后重试"
            >
              <el-table-column prop="transfer_no" label="调仓单号" min-width="150" />
              <el-table-column prop="material_code" label="物料编码" min-width="130" />
              <el-table-column prop="material_name" label="物料名称" min-width="140" />
              <el-table-column prop="source_warehouse" label="来源仓" min-width="130" />
              <el-table-column prop="target_warehouse" label="目标仓" min-width="130" />
              <el-table-column label="调拨数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.transfer_qty) }}</template>
              </el-table-column>
              <el-table-column label="已入库数量" min-width="120">
                <template #default="scope">{{ formatAmount(scope.row.inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="差异数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.diff_qty) }}</template>
              </el-table-column>
              <el-table-column prop="operator" label="经办人" min-width="100" />
              <el-table-column prop="transfer_date" label="单据日期" min-width="120" />
              <el-table-column label="状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="materialTransferStatusType(scope.row.status)" effect="light">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button link type="primary" @click="onGuardedAction('查看调仓')">查看</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="materialTransferQuery.page"
                :page-size="materialTransferQuery.page_size"
                :total="materialTransferTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onMaterialTransferPageChange"
                @size-change="onMaterialTransferSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section class="material-count-section" data-testid="material-count-section">
          <div class="section-header">
            <div class="title-group">
              <span class="title">物料盘点</span>
              <span class="sub-title">TASK-Y44B-P1-02 / 只读语义</span>
            </div>
            <el-tag type="warning" effect="plain">共享路由增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="materialCountQuery" class="query-form">
            <el-form-item label="物料编码">
              <el-input
                v-model="materialCountQuery.item_code"
                clearable
                placeholder="物料编码"
                @keyup.enter="onMaterialCountSearch"
              />
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="materialCountQuery.keyword"
                clearable
                placeholder="盘点单/物料/盘点人"
                @keyup.enter="onMaterialCountSearch"
              />
            </el-form-item>
            <el-form-item label="盘点仓库">
              <el-input
                v-model="materialCountQuery.warehouse"
                clearable
                placeholder="盘点仓库"
                @keyup.enter="onMaterialCountSearch"
              />
            </el-form-item>
            <el-form-item label="盘点状态">
              <el-select
                v-model="materialCountQuery.count_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="待盘点" value="待盘点" />
                <el-option label="盘点中" value="盘点中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="复核状态">
              <el-select
                v-model="materialCountQuery.review_status"
                clearable
                placeholder="全部复核"
                style="width: 140px"
              >
                <el-option label="待送审" value="待送审" />
                <el-option label="待复核" value="待复核" />
                <el-option label="已复核" value="已复核" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="materialCountQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="materialCountQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onMaterialCountReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onMaterialCountSearch">查询</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button data-write-guard="true" :disabled="!canRead" @click="onGuardedAction('盘点提示')">
              盘点提示
            </el-button>
            <el-button data-write-guard="true" :disabled="!canRead" @click="onGuardedAction('复核提示')">
              复核提示
            </el-button>
            <el-button data-write-guard="true" :disabled="!canRead" @click="onGuardedAction('盘点校验')">
              盘点校验
            </el-button>
            <el-button data-write-guard="true" :disabled="!canExport" @click="onGuardedAction('导出盘点')">
              导出
            </el-button>
            <el-button data-write-guard="true" :disabled="!canExport" @click="onGuardedAction('打印盘点')">
              打印
            </el-button>
          </div>

          <el-alert
            v-if="materialCountError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`物料盘点加载失败：${materialCountError}`"
          />

          <el-empty v-if="!canRead" description="无物料盘点查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">盘点记录：{{ materialCountTotal }}</el-tag>
              <el-tag type="success" effect="plain">账面总量：{{ materialCountBookTotal }}</el-tag>
              <el-tag type="warning" effect="plain">差异总量：{{ materialCountDiffTotal }}</el-tag>
            </div>

            <el-table
              :data="materialCountRows"
              border
              v-loading="materialCountLoading"
              empty-text="暂无物料盘点数据，请调整筛选条件后重试"
            >
              <el-table-column prop="count_no" label="盘点单号" min-width="150" />
              <el-table-column prop="material_code" label="物料编码" min-width="130" />
              <el-table-column prop="material_name" label="物料名称" min-width="140" />
              <el-table-column prop="warehouse" label="盘点仓库" min-width="130" />
              <el-table-column label="账面数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.book_qty) }}</template>
              </el-table-column>
              <el-table-column label="实盘数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.counted_qty) }}</template>
              </el-table-column>
              <el-table-column label="差异数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.diff_qty) }}</template>
              </el-table-column>
              <el-table-column label="盘点状态" min-width="110">
                <template #default="scope">
                  <el-tag :type="materialCountStatusType(scope.row.count_status)" effect="light">
                    {{ scope.row.count_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核状态" min-width="110">
                <template #default="scope">
                  <el-tag :type="materialCountReviewStatusType(scope.row.review_status)" effect="light">
                    {{ scope.row.review_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="count_date" label="盘点日期" min-width="120" />
              <el-table-column prop="owner" label="盘点人" min-width="100" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看盘点')"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="materialCountQuery.page"
                :page-size="materialCountQuery.page_size"
                :total="materialCountTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onMaterialCountPageChange"
                @size-change="onMaterialCountSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="material-inventory-report-section"
          data-testid="material-inventory-report-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">物料进销存报表</span>
              <span class="sub-title">TASK-Y44B-P1-03 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="materialInventoryReportQuery" class="query-form">
            <el-form-item label="报表单号">
              <el-input
                v-model="materialInventoryReportQuery.report_no"
                clearable
                placeholder="报表单号"
                @keyup.enter="onMaterialInventoryReportSearch"
              />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input
                v-model="materialInventoryReportQuery.item_code"
                clearable
                placeholder="物料编码"
                @keyup.enter="onMaterialInventoryReportSearch"
              />
            </el-form-item>
            <el-form-item label="仓库">
              <el-input
                v-model="materialInventoryReportQuery.warehouse"
                clearable
                placeholder="仓库"
                @keyup.enter="onMaterialInventoryReportSearch"
              />
            </el-form-item>
            <el-form-item label="业务类型">
              <el-select
                v-model="materialInventoryReportQuery.business_type"
                clearable
                placeholder="全部业务"
                style="width: 150px"
              >
                <el-option label="采购入仓" value="采购入仓" />
                <el-option label="销售出仓" value="销售出仓" />
                <el-option label="调仓入仓" value="调仓入仓" />
                <el-option label="盘点调整" value="盘点调整" />
              </el-select>
            </el-form-item>
            <el-form-item label="单据状态">
              <el-select
                v-model="materialInventoryReportQuery.status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="待复核" value="待复核" />
                <el-option label="执行中" value="执行中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="materialInventoryReportQuery.keyword"
                clearable
                placeholder="单号/物料/单据/经办人"
                @keyup.enter="onMaterialInventoryReportSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="materialInventoryReportQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="materialInventoryReportQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onMaterialInventoryReportReset">重置</el-button>
              <el-button
                type="primary"
                :disabled="!canRead"
                @click="onMaterialInventoryReportSearch"
              >
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('物料进销存报表提示')"
            >
              报表提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('物料进销存报表校验')"
            >
              报表校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出物料进销存报表')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印物料进销存报表')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="materialInventoryReportError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`物料进销存报表加载失败：${materialInventoryReportError}`"
          />

          <el-empty v-if="!canRead" description="无物料进销存报表查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">
                报表记录：{{ materialInventoryReportTotal }}
              </el-tag>
              <el-tag type="success" effect="plain">
                入库总量：{{ materialInventoryReportInTotal }}
              </el-tag>
              <el-tag type="warning" effect="plain">
                出库总量：{{ materialInventoryReportOutTotal }}
              </el-tag>
              <el-tag type="danger" effect="plain">
                结余总量：{{ materialInventoryReportBalanceTotal }}
              </el-tag>
            </div>

            <el-table
              :data="materialInventoryReportRows"
              border
              v-loading="materialInventoryReportLoading"
              empty-text="暂无物料进销存报表数据，请调整筛选条件后重试"
            >
              <el-table-column prop="report_no" label="报表单号" min-width="150" />
              <el-table-column prop="material_code" label="物料编码" min-width="130" />
              <el-table-column prop="material_name" label="物料名称" min-width="140" />
              <el-table-column prop="warehouse" label="仓库" min-width="130" />
              <el-table-column prop="business_type" label="业务类型" min-width="120" />
              <el-table-column label="入库数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.in_qty) }}</template>
              </el-table-column>
              <el-table-column label="出库数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.out_qty) }}</template>
              </el-table-column>
              <el-table-column label="结余数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.balance_qty) }}</template>
              </el-table-column>
              <el-table-column label="状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="materialInventoryReportStatusType(scope.row.status)" effect="light">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="biz_date" label="业务日期" min-width="120" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看物料进销存报表')"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="materialInventoryReportQuery.page"
                :page-size="materialInventoryReportQuery.page_size"
                :total="materialInventoryReportTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onMaterialInventoryReportPageChange"
                @size-change="onMaterialInventoryReportSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="inventory-material-retention-report-section"
          data-testid="inventory-material-retention-report-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">库存物料滞留报表</span>
              <span class="sub-title">TASK-Y44B-P1-05 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="inventoryMaterialRetentionReportQuery" class="query-form">
            <el-form-item label="报表单号">
              <el-input
                v-model="inventoryMaterialRetentionReportQuery.report_no"
                clearable
                placeholder="报表单号"
                @keyup.enter="onInventoryMaterialRetentionReportSearch"
              />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input
                v-model="inventoryMaterialRetentionReportQuery.item_code"
                clearable
                placeholder="物料编码"
                @keyup.enter="onInventoryMaterialRetentionReportSearch"
              />
            </el-form-item>
            <el-form-item label="仓库">
              <el-input
                v-model="inventoryMaterialRetentionReportQuery.warehouse"
                clearable
                placeholder="仓库"
                @keyup.enter="onInventoryMaterialRetentionReportSearch"
              />
            </el-form-item>
            <el-form-item label="滞留等级">
              <el-select
                v-model="inventoryMaterialRetentionReportQuery.retention_level"
                clearable
                placeholder="全部等级"
                style="width: 140px"
              >
                <el-option label="高滞留" value="高滞留" />
                <el-option label="中滞留" value="中滞留" />
                <el-option label="低滞留" value="低滞留" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="inventoryMaterialRetentionReportQuery.status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="待处理" value="待处理" />
                <el-option label="跟进中" value="跟进中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="inventoryMaterialRetentionReportQuery.keyword"
                clearable
                placeholder="报表单号/物料/单据/经办人"
                @keyup.enter="onInventoryMaterialRetentionReportSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="inventoryMaterialRetentionReportQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="inventoryMaterialRetentionReportQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onInventoryMaterialRetentionReportReset">重置</el-button>
              <el-button
                type="primary"
                :disabled="!canRead"
                @click="onInventoryMaterialRetentionReportSearch"
              >
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('滞留处理提示')"
            >
              处理提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('滞留校验')"
            >
              滞留校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出滞留报表')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印滞留报表')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="inventoryMaterialRetentionReportError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`库存物料滞留报表加载失败：${inventoryMaterialRetentionReportError}`"
          />

          <el-empty v-if="!canRead" description="无库存物料滞留报表查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">
                滞留记录：{{ inventoryMaterialRetentionReportTotal }}
              </el-tag>
              <el-tag type="warning" effect="plain">
                滞留总量：{{ inventoryMaterialRetentionStagnantTotal }}
              </el-tag>
              <el-tag type="danger" effect="plain">
                平均滞留天数：{{ inventoryMaterialRetentionDaysAverage }}
              </el-tag>
            </div>

            <el-table
              :data="inventoryMaterialRetentionReportRows"
              border
              v-loading="inventoryMaterialRetentionReportLoading"
              empty-text="暂无库存物料滞留报表数据，请调整筛选条件后重试"
            >
              <el-table-column prop="report_no" label="报表单号" min-width="150" />
              <el-table-column prop="material_code" label="物料编码" min-width="130" />
              <el-table-column prop="material_name" label="物料名称" min-width="140" />
              <el-table-column prop="warehouse" label="仓库" min-width="120" />
              <el-table-column prop="retention_level" label="滞留等级" min-width="100" />
              <el-table-column label="滞留天数" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.retention_days) }}</template>
              </el-table-column>
              <el-table-column label="当前库存" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.current_qty) }}</template>
              </el-table-column>
              <el-table-column label="滞留数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.stagnant_qty) }}</template>
              </el-table-column>
              <el-table-column label="周转天数" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.turnover_days) }}</template>
              </el-table-column>
              <el-table-column label="状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="inventoryMaterialRetentionStatusType(scope.row.status)" effect="light">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="biz_date" label="统计日期" min-width="120" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看库存滞留报表')"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="inventoryMaterialRetentionReportQuery.page"
                :page-size="inventoryMaterialRetentionReportQuery.page_size"
                :total="inventoryMaterialRetentionReportTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onInventoryMaterialRetentionReportPageChange"
                @size-change="onInventoryMaterialRetentionReportSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section class="semi-finished-inventory-section" data-testid="semi-finished-inventory-section">
          <div class="section-header">
            <div class="title-group">
              <span class="title">半成品库存</span>
              <span class="sub-title">TASK-Y49B-P1-01 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="semiFinishedInventoryQuery" class="query-form">
            <el-form-item label="记录单号">
              <el-input
                v-model="semiFinishedInventoryQuery.record_no"
                clearable
                placeholder="记录单号"
                @keyup.enter="onSemiFinishedInventorySearch"
              />
            </el-form-item>
            <el-form-item label="物料编码">
              <el-input
                v-model="semiFinishedInventoryQuery.item_code"
                clearable
                placeholder="物料编码"
                @keyup.enter="onSemiFinishedInventorySearch"
              />
            </el-form-item>
            <el-form-item label="仓库">
              <el-input
                v-model="semiFinishedInventoryQuery.warehouse"
                clearable
                placeholder="仓库"
                @keyup.enter="onSemiFinishedInventorySearch"
              />
            </el-form-item>
            <el-form-item label="工序阶段">
              <el-select
                v-model="semiFinishedInventoryQuery.process_stage"
                clearable
                placeholder="全部阶段"
                style="width: 150px"
              >
                <el-option label="车缝完成" value="车缝完成" />
                <el-option label="锁边完成" value="锁边完成" />
                <el-option label="整烫待检" value="整烫待检" />
                <el-option label="返修处理中" value="返修处理中" />
              </el-select>
            </el-form-item>
            <el-form-item label="库存状态">
              <el-select
                v-model="semiFinishedInventoryQuery.status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="在库" value="在库" />
                <el-option label="待质检" value="待质检" />
                <el-option label="返修中" value="返修中" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="semiFinishedInventoryQuery.keyword"
                clearable
                placeholder="单号/物料/工序/经办人"
                @keyup.enter="onSemiFinishedInventorySearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="semiFinishedInventoryQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="semiFinishedInventoryQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onSemiFinishedInventoryReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onSemiFinishedInventorySearch">查询</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('半成品锁定提示')"
            >
              锁定提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('半成品复核提示')"
            >
              复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('半成品校验')"
            >
              校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出半成品库存')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印半成品库存')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="semiFinishedInventoryError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`半成品库存加载失败：${semiFinishedInventoryError}`"
          />

          <el-empty v-if="!canRead" description="无半成品库存查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">半成品记录：{{ semiFinishedInventoryTotal }}</el-tag>
              <el-tag type="success" effect="plain">入库总量：{{ semiFinishedInventoryInTotal }}</el-tag>
              <el-tag type="warning" effect="plain">出库总量：{{ semiFinishedInventoryOutTotal }}</el-tag>
              <el-tag type="danger" effect="plain">结余总量：{{ semiFinishedInventoryClosingTotal }}</el-tag>
            </div>

            <el-table
              :data="semiFinishedInventoryRows"
              border
              v-loading="semiFinishedInventoryLoading"
              empty-text="暂无半成品库存数据，请调整筛选条件后重试"
            >
              <el-table-column prop="record_no" label="记录单号" min-width="150" />
              <el-table-column prop="material_code" label="物料编码" min-width="130" />
              <el-table-column prop="material_name" label="物料名称" min-width="140" />
              <el-table-column prop="warehouse" label="仓库" min-width="120" />
              <el-table-column prop="process_stage" label="工序阶段" min-width="120" />
              <el-table-column label="期初数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.opening_qty) }}</template>
              </el-table-column>
              <el-table-column label="入库数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.in_qty) }}</template>
              </el-table-column>
              <el-table-column label="出库数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.out_qty) }}</template>
              </el-table-column>
              <el-table-column label="结余数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.closing_qty) }}</template>
              </el-table-column>
              <el-table-column label="状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="semiFinishedInventoryStatusType(scope.row.status)" effect="light">
                    {{ scope.row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="biz_date" label="统计日期" min-width="120" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看半成品库存')"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="semiFinishedInventoryQuery.page"
                :page-size="semiFinishedInventoryQuery.page_size"
                :total="semiFinishedInventoryTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onSemiFinishedInventoryPageChange"
                @size-change="onSemiFinishedInventorySizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="finished-goods-reserved-inbound-section"
          data-testid="finished-goods-reserved-inbound-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">成品预约入仓</span>
              <span class="sub-title">TASK-Y49B-P1-03 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="finishedGoodsReservedInboundQuery" class="query-form">
            <el-form-item label="预约单号">
              <el-input
                v-model="finishedGoodsReservedInboundQuery.reservation_no"
                clearable
                placeholder="预约单号"
                @keyup.enter="onFinishedGoodsReservedInboundSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="finishedGoodsReservedInboundQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onFinishedGoodsReservedInboundSearch"
              />
            </el-form-item>
            <el-form-item label="预约仓库">
              <el-input
                v-model="finishedGoodsReservedInboundQuery.warehouse"
                clearable
                placeholder="预约仓库"
                @keyup.enter="onFinishedGoodsReservedInboundSearch"
              />
            </el-form-item>
            <el-form-item label="预约状态">
              <el-select
                v-model="finishedGoodsReservedInboundQuery.reserve_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="待确认" value="待确认" />
                <el-option label="已预约" value="已预约" />
                <el-option label="部分入仓" value="部分入仓" />
                <el-option label="已入仓" value="已入仓" />
              </el-select>
            </el-form-item>
            <el-form-item label="入仓状态">
              <el-select
                v-model="finishedGoodsReservedInboundQuery.inbound_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待入仓" value="待入仓" />
                <el-option label="入仓中" value="入仓中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="finishedGoodsReservedInboundQuery.keyword"
                clearable
                placeholder="预约单号/成品/仓库/经办人"
                @keyup.enter="onFinishedGoodsReservedInboundSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="finishedGoodsReservedInboundQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="finishedGoodsReservedInboundQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onFinishedGoodsReservedInboundReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onFinishedGoodsReservedInboundSearch">
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('预约确认提示')"
            >
              预约确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('预约排程提示')"
            >
              预约排程提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品预约入仓校验')"
            >
              校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出成品预约入仓')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印成品预约入仓')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="finishedGoodsReservedInboundError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成品预约入仓加载失败：${finishedGoodsReservedInboundError}`"
          />

          <el-empty v-if="!canRead" description="无成品预约入仓查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">预约记录：{{ finishedGoodsReservedInboundTotal }}</el-tag>
              <el-tag type="success" effect="plain">预约总量：{{ finishedGoodsReservedInboundReserveTotal }}</el-tag>
              <el-tag type="warning" effect="plain">已入总量：{{ finishedGoodsReservedInboundInTotal }}</el-tag>
              <el-tag type="danger" effect="plain">待入总量：{{ finishedGoodsReservedInboundPendingTotal }}</el-tag>
            </div>

            <el-table
              :data="finishedGoodsReservedInboundRows"
              border
              v-loading="finishedGoodsReservedInboundLoading"
              empty-text="暂无成品预约入仓数据，请调整筛选条件后重试"
            >
              <el-table-column prop="reservation_no" label="预约单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="预约仓库" min-width="120" />
              <el-table-column label="预约数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.reserve_qty) }}</template>
              </el-table-column>
              <el-table-column label="已入数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="待入数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.pending_inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="预约状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsReservedInboundReserveStatusType(scope.row.reserve_status)" effect="light">
                    {{ scope.row.reserve_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="入仓状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsReservedInboundInboundStatusType(scope.row.inbound_status)" effect="light">
                    {{ scope.row.inbound_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="reserved_date" label="预约日期" min-width="120" />
              <el-table-column prop="expected_inbound_date" label="预计入仓日期" min-width="130" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看成品预约入仓')"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="finishedGoodsReservedInboundQuery.page"
                :page-size="finishedGoodsReservedInboundQuery.page_size"
                :total="finishedGoodsReservedInboundTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onFinishedGoodsReservedInboundPageChange"
                @size-change="onFinishedGoodsReservedInboundSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="finished-goods-shipping-notice-section"
          data-testid="finished-goods-shipping-notice-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">成品发货通知单</span>
              <span class="sub-title">TASK-Y49B-P1-04 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="finishedGoodsShippingNoticeQuery" class="query-form">
            <el-form-item label="通知单号">
              <el-input
                v-model="finishedGoodsShippingNoticeQuery.notice_no"
                clearable
                placeholder="通知单号"
                @keyup.enter="onFinishedGoodsShippingNoticeSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="finishedGoodsShippingNoticeQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onFinishedGoodsShippingNoticeSearch"
              />
            </el-form-item>
            <el-form-item label="发货仓库">
              <el-input
                v-model="finishedGoodsShippingNoticeQuery.warehouse"
                clearable
                placeholder="发货仓库"
                @keyup.enter="onFinishedGoodsShippingNoticeSearch"
              />
            </el-form-item>
            <el-form-item label="通知状态">
              <el-select
                v-model="finishedGoodsShippingNoticeQuery.notice_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="待确认" value="待确认" />
                <el-option label="已下发" value="已下发" />
                <el-option label="部分发货" value="部分发货" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="物流状态">
              <el-select
                v-model="finishedGoodsShippingNoticeQuery.logistics_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待揽收" value="待揽收" />
                <el-option label="运输中" value="运输中" />
                <el-option label="已签收" value="已签收" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="finishedGoodsShippingNoticeQuery.keyword"
                clearable
                placeholder="通知单号/成品/仓库/经办人"
                @keyup.enter="onFinishedGoodsShippingNoticeSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="finishedGoodsShippingNoticeQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="finishedGoodsShippingNoticeQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onFinishedGoodsShippingNoticeReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onFinishedGoodsShippingNoticeSearch">
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('发货下发提示')"
            >
              发货下发提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('发货复核提示')"
            >
              发货复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('发货校验')"
            >
              校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出成品发货通知单')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印成品发货通知单')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="finishedGoodsShippingNoticeError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成品发货通知单加载失败：${finishedGoodsShippingNoticeError}`"
          />

          <el-empty v-if="!canRead" description="无成品发货通知单查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">通知记录：{{ finishedGoodsShippingNoticeTotal }}</el-tag>
              <el-tag type="success" effect="plain">计划发货总量：{{ finishedGoodsShippingNoticePlannedTotal }}</el-tag>
              <el-tag type="warning" effect="plain">已发货总量：{{ finishedGoodsShippingNoticeShippedTotal }}</el-tag>
              <el-tag type="danger" effect="plain">待发货总量：{{ finishedGoodsShippingNoticePendingTotal }}</el-tag>
            </div>

            <el-table
              :data="finishedGoodsShippingNoticeRows"
              border
              v-loading="finishedGoodsShippingNoticeLoading"
              empty-text="暂无成品发货通知单数据，请调整筛选条件后重试"
            >
              <el-table-column prop="notice_no" label="通知单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="发货仓库" min-width="120" />
              <el-table-column label="计划发货" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.planned_ship_qty) }}</template>
              </el-table-column>
              <el-table-column label="已发货" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.shipped_qty) }}</template>
              </el-table-column>
              <el-table-column label="待发货" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.pending_ship_qty) }}</template>
              </el-table-column>
              <el-table-column label="通知状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsShippingNoticeStatusType(scope.row.notice_status)" effect="light">
                    {{ scope.row.notice_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="物流状态" min-width="100">
                <template #default="scope">
                  <el-tag
                    :type="finishedGoodsShippingNoticeLogisticsStatusType(scope.row.logistics_status)"
                    effect="light"
                  >
                    {{ scope.row.logistics_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="notice_date" label="通知日期" min-width="120" />
              <el-table-column prop="expected_delivery_date" label="预计送达日期" min-width="130" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看成品发货通知单')"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="finishedGoodsShippingNoticeQuery.page"
                :page-size="finishedGoodsShippingNoticeQuery.page_size"
                :total="finishedGoodsShippingNoticeTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onFinishedGoodsShippingNoticePageChange"
                @size-change="onFinishedGoodsShippingNoticeSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section class="finished-goods-other-inbound-section" data-testid="finished-goods-other-inbound-section">
          <div class="section-header">
            <div class="title-group">
              <span class="title">成品其他入仓</span>
              <span class="sub-title">TASK-Y49B-P1-05 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="finishedGoodsOtherInboundQuery" class="query-form">
            <el-form-item label="入仓单号">
              <el-input
                v-model="finishedGoodsOtherInboundQuery.inbound_no"
                clearable
                placeholder="入仓单号"
                @keyup.enter="onFinishedGoodsOtherInboundSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="finishedGoodsOtherInboundQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onFinishedGoodsOtherInboundSearch"
              />
            </el-form-item>
            <el-form-item label="入仓仓库">
              <el-input
                v-model="finishedGoodsOtherInboundQuery.warehouse"
                clearable
                placeholder="入仓仓库"
                @keyup.enter="onFinishedGoodsOtherInboundSearch"
              />
            </el-form-item>
            <el-form-item label="入仓状态">
              <el-select
                v-model="finishedGoodsOtherInboundQuery.inbound_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="待确认" value="待确认" />
                <el-option label="入仓中" value="入仓中" />
                <el-option label="部分入仓" value="部分入仓" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="核销状态">
              <el-select
                v-model="finishedGoodsOtherInboundQuery.settlement_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待核销" value="待核销" />
                <el-option label="核销中" value="核销中" />
                <el-option label="已核销" value="已核销" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="finishedGoodsOtherInboundQuery.keyword"
                clearable
                placeholder="入仓单号/成品/仓库/来源单号"
                @keyup.enter="onFinishedGoodsOtherInboundSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="finishedGoodsOtherInboundQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="finishedGoodsOtherInboundQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onFinishedGoodsOtherInboundReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onFinishedGoodsOtherInboundSearch">查询</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('其他入仓确认提示')"
            >
              其他入仓确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('其他入仓核销提示')"
            >
              其他入仓核销提示
            </el-button>
            <el-button data-write-guard="true" :disabled="!canRead" @click="onGuardedAction('成品其他入仓校验')">
              校验
            </el-button>
            <el-button data-write-guard="true" :disabled="!canExport" @click="onGuardedAction('导出成品其他入仓')">
              导出
            </el-button>
            <el-button data-write-guard="true" :disabled="!canExport" @click="onGuardedAction('打印成品其他入仓')">
              打印
            </el-button>
          </div>

          <el-alert
            v-if="finishedGoodsOtherInboundError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成品其他入仓加载失败：${finishedGoodsOtherInboundError}`"
          />

          <el-empty v-if="!canRead" description="无成品其他入仓查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">入仓记录：{{ finishedGoodsOtherInboundTotal }}</el-tag>
              <el-tag type="success" effect="plain">计划入仓总量：{{ finishedGoodsOtherInboundPlannedTotal }}</el-tag>
              <el-tag type="warning" effect="plain">已入仓总量：{{ finishedGoodsOtherInboundActualTotal }}</el-tag>
              <el-tag type="danger" effect="plain">待入仓总量：{{ finishedGoodsOtherInboundPendingTotal }}</el-tag>
            </div>

            <el-table
              :data="finishedGoodsOtherInboundRows"
              border
              v-loading="finishedGoodsOtherInboundLoading"
              empty-text="暂无成品其他入仓数据，请调整筛选条件后重试"
            >
              <el-table-column prop="inbound_no" label="入仓单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="入仓仓库" min-width="120" />
              <el-table-column label="计划入仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.planned_inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="实际入仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.actual_inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="待入仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.pending_inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="入仓状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsOtherInboundStatusType(scope.row.inbound_status)" effect="light">
                    {{ scope.row.inbound_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="核销状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsOtherInboundSettlementStatusType(scope.row.settlement_status)" effect="light">
                    {{ scope.row.settlement_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="inbound_date" label="入仓日期" min-width="120" />
              <el-table-column prop="source_doc_no" label="来源单号" min-width="140" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看成品其他入仓')"
                  >
                    查看
                  </el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pager">
              <el-pagination
                background
                layout="prev, pager, next, total, sizes"
                :current-page="finishedGoodsOtherInboundQuery.page"
                :page-size="finishedGoodsOtherInboundQuery.page_size"
                :total="finishedGoodsOtherInboundTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onFinishedGoodsOtherInboundPageChange"
                @size-change="onFinishedGoodsOtherInboundSizeChange"
              />
            </div>
          </template>
        </section>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventoryFinishedGoodsOtherInbound,
  fetchSalesInventoryFinishedGoodsReservedInbound,
  fetchSalesInventoryFinishedGoodsShippingNotices,
  fetchSalesInventoryFinishedGoodsReport,
  fetchSalesInventoryInventoryMaterialRetentionReport,
  fetchSalesInventoryMaterialCounts,
  fetchSalesInventoryMaterialInventoryReport,
  fetchSalesInventoryMaterialTransfers,
  fetchSalesInventorySemiFinishedInventory,
  type FinishedGoodsOtherInboundItem,
  type FinishedGoodsReservedInboundItem,
  type FinishedGoodsShippingNoticeItem,
  type FinishedGoodsReportItem,
  type InventoryMaterialRetentionReportItem,
  type MaterialCountItem,
  type MaterialInventoryReportItem,
  type MaterialTransferItem,
  type SemiFinishedInventoryItem,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<FinishedGoodsReportItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')
const materialTransferLoading = ref<boolean>(false)
const materialTransferRows = ref<MaterialTransferItem[]>([])
const materialTransferTotal = ref<number>(0)
const materialTransferError = ref<string>('')
const materialCountLoading = ref<boolean>(false)
const materialCountRows = ref<MaterialCountItem[]>([])
const materialCountTotal = ref<number>(0)
const materialCountError = ref<string>('')
const materialInventoryReportLoading = ref<boolean>(false)
const materialInventoryReportRows = ref<MaterialInventoryReportItem[]>([])
const materialInventoryReportTotal = ref<number>(0)
const materialInventoryReportError = ref<string>('')
const inventoryMaterialRetentionReportLoading = ref<boolean>(false)
const inventoryMaterialRetentionReportRows = ref<InventoryMaterialRetentionReportItem[]>([])
const inventoryMaterialRetentionReportTotal = ref<number>(0)
const inventoryMaterialRetentionReportError = ref<string>('')
const semiFinishedInventoryLoading = ref<boolean>(false)
const semiFinishedInventoryRows = ref<SemiFinishedInventoryItem[]>([])
const semiFinishedInventoryTotal = ref<number>(0)
const semiFinishedInventoryError = ref<string>('')
const finishedGoodsReservedInboundLoading = ref<boolean>(false)
const finishedGoodsReservedInboundRows = ref<FinishedGoodsReservedInboundItem[]>([])
const finishedGoodsReservedInboundTotal = ref<number>(0)
const finishedGoodsReservedInboundError = ref<string>('')
const finishedGoodsShippingNoticeLoading = ref<boolean>(false)
const finishedGoodsShippingNoticeRows = ref<FinishedGoodsShippingNoticeItem[]>([])
const finishedGoodsShippingNoticeTotal = ref<number>(0)
const finishedGoodsShippingNoticeError = ref<string>('')
const finishedGoodsOtherInboundLoading = ref<boolean>(false)
const finishedGoodsOtherInboundRows = ref<FinishedGoodsOtherInboundItem[]>([])
const finishedGoodsOtherInboundTotal = ref<number>(0)
const finishedGoodsOtherInboundError = ref<string>('')

const canRead = computed<boolean>(() => {
  return (
    permissionStore.state.buttonPermissions.sales_inventory_read ||
    permissionStore.state.actions.includes('sales_inventory:read')
  )
})
const canExport = computed<boolean>(() => {
  return (
    canRead.value &&
    (permissionStore.state.buttonPermissions.sales_inventory_export ||
      permissionStore.state.actions.includes('sales_inventory:export'))
  )
})

const totalQty = computed<string>(() => {
  const qty = rows.value.reduce((sum, row) => {
    const current = Number(row.qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const materialTransferQtyTotal = computed<string>(() => {
  const qty = materialTransferRows.value.reduce((sum, row) => {
    const current = Number(row.transfer_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const materialTransferDiffTotal = computed<string>(() => {
  const qty = materialTransferRows.value.reduce((sum, row) => {
    const current = Number(row.diff_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const materialCountBookTotal = computed<string>(() => {
  const qty = materialCountRows.value.reduce((sum, row) => {
    const current = Number(row.book_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const materialCountDiffTotal = computed<string>(() => {
  const qty = materialCountRows.value.reduce((sum, row) => {
    const current = Number(row.diff_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const materialInventoryReportInTotal = computed<string>(() => {
  const qty = materialInventoryReportRows.value.reduce((sum, row) => {
    const current = Number(row.in_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const materialInventoryReportOutTotal = computed<string>(() => {
  const qty = materialInventoryReportRows.value.reduce((sum, row) => {
    const current = Number(row.out_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const materialInventoryReportBalanceTotal = computed<string>(() => {
  const qty = materialInventoryReportRows.value.reduce((sum, row) => {
    const current = Number(row.balance_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const inventoryMaterialRetentionStagnantTotal = computed<string>(() => {
  const qty = inventoryMaterialRetentionReportRows.value.reduce((sum, row) => {
    const current = Number(row.stagnant_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const inventoryMaterialRetentionDaysAverage = computed<string>(() => {
  if (!inventoryMaterialRetentionReportRows.value.length) {
    return '0.00'
  }
  const totalDays = inventoryMaterialRetentionReportRows.value.reduce((sum, row) => {
    const current = Number(row.retention_days ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return (totalDays / inventoryMaterialRetentionReportRows.value.length).toFixed(2)
})

const semiFinishedInventoryInTotal = computed<string>(() => {
  const qty = semiFinishedInventoryRows.value.reduce((sum, row) => {
    const current = Number(row.in_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const semiFinishedInventoryOutTotal = computed<string>(() => {
  const qty = semiFinishedInventoryRows.value.reduce((sum, row) => {
    const current = Number(row.out_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const semiFinishedInventoryClosingTotal = computed<string>(() => {
  const qty = semiFinishedInventoryRows.value.reduce((sum, row) => {
    const current = Number(row.closing_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsReservedInboundReserveTotal = computed<string>(() => {
  const qty = finishedGoodsReservedInboundRows.value.reduce((sum, row) => {
    const current = Number(row.reserve_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsReservedInboundInTotal = computed<string>(() => {
  const qty = finishedGoodsReservedInboundRows.value.reduce((sum, row) => {
    const current = Number(row.inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsReservedInboundPendingTotal = computed<string>(() => {
  const qty = finishedGoodsReservedInboundRows.value.reduce((sum, row) => {
    const current = Number(row.pending_inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsShippingNoticePlannedTotal = computed<string>(() => {
  const qty = finishedGoodsShippingNoticeRows.value.reduce((sum, row) => {
    const current = Number(row.planned_ship_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsShippingNoticeShippedTotal = computed<string>(() => {
  const qty = finishedGoodsShippingNoticeRows.value.reduce((sum, row) => {
    const current = Number(row.shipped_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsShippingNoticePendingTotal = computed<string>(() => {
  const qty = finishedGoodsShippingNoticeRows.value.reduce((sum, row) => {
    const current = Number(row.pending_ship_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsOtherInboundPlannedTotal = computed<string>(() => {
  const qty = finishedGoodsOtherInboundRows.value.reduce((sum, row) => {
    const current = Number(row.planned_inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsOtherInboundActualTotal = computed<string>(() => {
  const qty = finishedGoodsOtherInboundRows.value.reduce((sum, row) => {
    const current = Number(row.actual_inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsOtherInboundPendingTotal = computed<string>(() => {
  const qty = finishedGoodsOtherInboundRows.value.reduce((sum, row) => {
    const current = Number(row.pending_inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const query = reactive({
  no: '',
  style: '',
  warehouse: '',
  from_date: '',
  to_date: '',
  keyword: '',
  page: 1,
  page_size: 20,
})

const materialTransferQuery = reactive({
  item_code: '',
  keyword: '',
  source_warehouse: '',
  target_warehouse: '',
  status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const materialCountQuery = reactive({
  item_code: '',
  keyword: '',
  warehouse: '',
  count_status: '',
  review_status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const materialInventoryReportQuery = reactive({
  report_no: '',
  item_code: '',
  warehouse: '',
  business_type: '',
  status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const inventoryMaterialRetentionReportQuery = reactive({
  report_no: '',
  item_code: '',
  warehouse: '',
  retention_level: '',
  status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const semiFinishedInventoryQuery = reactive({
  record_no: '',
  item_code: '',
  warehouse: '',
  process_stage: '',
  status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const finishedGoodsReservedInboundQuery = reactive({
  reservation_no: '',
  item_code: '',
  warehouse: '',
  reserve_status: '',
  inbound_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const finishedGoodsShippingNoticeQuery = reactive({
  notice_no: '',
  item_code: '',
  warehouse: '',
  notice_status: '',
  logistics_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const finishedGoodsOtherInboundQuery = reactive({
  inbound_no: '',
  item_code: '',
  warehouse: '',
  inbound_status: '',
  settlement_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const resetMaterialTransferRows = (): void => {
  materialTransferRows.value = []
  materialTransferTotal.value = 0
}

const resetMaterialCountRows = (): void => {
  materialCountRows.value = []
  materialCountTotal.value = 0
}

const resetMaterialInventoryReportRows = (): void => {
  materialInventoryReportRows.value = []
  materialInventoryReportTotal.value = 0
}

const resetInventoryMaterialRetentionReportRows = (): void => {
  inventoryMaterialRetentionReportRows.value = []
  inventoryMaterialRetentionReportTotal.value = 0
}

const resetSemiFinishedInventoryRows = (): void => {
  semiFinishedInventoryRows.value = []
  semiFinishedInventoryTotal.value = 0
}

const resetFinishedGoodsReservedInboundRows = (): void => {
  finishedGoodsReservedInboundRows.value = []
  finishedGoodsReservedInboundTotal.value = 0
}

const resetFinishedGoodsShippingNoticeRows = (): void => {
  finishedGoodsShippingNoticeRows.value = []
  finishedGoodsShippingNoticeTotal.value = 0
}

const resetFinishedGoodsOtherInboundRows = (): void => {
  finishedGoodsOtherInboundRows.value = []
  finishedGoodsOtherInboundTotal.value = 0
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
    const result = await fetchSalesInventoryFinishedGoodsReport({
      no: query.no.trim() || undefined,
      style: query.style.trim() || undefined,
      warehouse: query.warehouse.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      keyword: query.keyword.trim() || undefined,
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

const loadMaterialTransfers = async (): Promise<void> => {
  if (!canRead.value) {
    resetMaterialTransferRows()
    materialTransferError.value = ''
    return
  }
  materialTransferLoading.value = true
  materialTransferError.value = ''
  try {
    if (materialTransferQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('物料调仓区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryMaterialTransfers({
      item_code: materialTransferQuery.item_code.trim() || undefined,
      keyword: materialTransferQuery.keyword.trim() || undefined,
      source_warehouse: materialTransferQuery.source_warehouse.trim() || undefined,
      target_warehouse: materialTransferQuery.target_warehouse.trim() || undefined,
      status: materialTransferQuery.status || undefined,
      from_date: materialTransferQuery.from_date || undefined,
      to_date: materialTransferQuery.to_date || undefined,
      page: materialTransferQuery.page,
      page_size: materialTransferQuery.page_size,
    })
    materialTransferRows.value = result.data.items
    materialTransferTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    materialTransferError.value = message
    resetMaterialTransferRows()
    ElMessage.error(message)
  } finally {
    materialTransferLoading.value = false
  }
}

const loadMaterialCounts = async (): Promise<void> => {
  if (!canRead.value) {
    resetMaterialCountRows()
    materialCountError.value = ''
    return
  }
  materialCountLoading.value = true
  materialCountError.value = ''
  try {
    if (materialCountQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('物料盘点区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryMaterialCounts({
      item_code: materialCountQuery.item_code.trim() || undefined,
      keyword: materialCountQuery.keyword.trim() || undefined,
      warehouse: materialCountQuery.warehouse.trim() || undefined,
      count_status: materialCountQuery.count_status || undefined,
      review_status: materialCountQuery.review_status || undefined,
      from_date: materialCountQuery.from_date || undefined,
      to_date: materialCountQuery.to_date || undefined,
      page: materialCountQuery.page,
      page_size: materialCountQuery.page_size,
    })
    materialCountRows.value = result.data.items
    materialCountTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    materialCountError.value = message
    resetMaterialCountRows()
    ElMessage.error(message)
  } finally {
    materialCountLoading.value = false
  }
}

const loadMaterialInventoryReport = async (): Promise<void> => {
  if (!canRead.value) {
    resetMaterialInventoryReportRows()
    materialInventoryReportError.value = ''
    return
  }
  materialInventoryReportLoading.value = true
  materialInventoryReportError.value = ''
  try {
    if (materialInventoryReportQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('物料进销存报表区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryMaterialInventoryReport({
      report_no: materialInventoryReportQuery.report_no.trim() || undefined,
      item_code: materialInventoryReportQuery.item_code.trim() || undefined,
      warehouse: materialInventoryReportQuery.warehouse.trim() || undefined,
      business_type: materialInventoryReportQuery.business_type || undefined,
      status: materialInventoryReportQuery.status || undefined,
      keyword: materialInventoryReportQuery.keyword.trim() || undefined,
      from_date: materialInventoryReportQuery.from_date || undefined,
      to_date: materialInventoryReportQuery.to_date || undefined,
      page: materialInventoryReportQuery.page,
      page_size: materialInventoryReportQuery.page_size,
    })
    materialInventoryReportRows.value = result.data.items
    materialInventoryReportTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    materialInventoryReportError.value = message
    resetMaterialInventoryReportRows()
    ElMessage.error(message)
  } finally {
    materialInventoryReportLoading.value = false
  }
}

const loadInventoryMaterialRetentionReport = async (): Promise<void> => {
  if (!canRead.value) {
    resetInventoryMaterialRetentionReportRows()
    inventoryMaterialRetentionReportError.value = ''
    return
  }
  inventoryMaterialRetentionReportLoading.value = true
  inventoryMaterialRetentionReportError.value = ''
  try {
    if (inventoryMaterialRetentionReportQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('库存物料滞留报表区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryInventoryMaterialRetentionReport({
      report_no: inventoryMaterialRetentionReportQuery.report_no.trim() || undefined,
      item_code: inventoryMaterialRetentionReportQuery.item_code.trim() || undefined,
      warehouse: inventoryMaterialRetentionReportQuery.warehouse.trim() || undefined,
      retention_level: inventoryMaterialRetentionReportQuery.retention_level || undefined,
      status: inventoryMaterialRetentionReportQuery.status || undefined,
      keyword: inventoryMaterialRetentionReportQuery.keyword.trim() || undefined,
      from_date: inventoryMaterialRetentionReportQuery.from_date || undefined,
      to_date: inventoryMaterialRetentionReportQuery.to_date || undefined,
      page: inventoryMaterialRetentionReportQuery.page,
      page_size: inventoryMaterialRetentionReportQuery.page_size,
    })
    inventoryMaterialRetentionReportRows.value = result.data.items
    inventoryMaterialRetentionReportTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    inventoryMaterialRetentionReportError.value = message
    resetInventoryMaterialRetentionReportRows()
    ElMessage.error(message)
  } finally {
    inventoryMaterialRetentionReportLoading.value = false
  }
}

const loadSemiFinishedInventory = async (): Promise<void> => {
  if (!canRead.value) {
    resetSemiFinishedInventoryRows()
    semiFinishedInventoryError.value = ''
    return
  }
  semiFinishedInventoryLoading.value = true
  semiFinishedInventoryError.value = ''
  try {
    if (semiFinishedInventoryQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('半成品库存区块本地模拟错误态')
    }
    const result = await fetchSalesInventorySemiFinishedInventory({
      record_no: semiFinishedInventoryQuery.record_no.trim() || undefined,
      item_code: semiFinishedInventoryQuery.item_code.trim() || undefined,
      warehouse: semiFinishedInventoryQuery.warehouse.trim() || undefined,
      process_stage: semiFinishedInventoryQuery.process_stage || undefined,
      status: semiFinishedInventoryQuery.status || undefined,
      keyword: semiFinishedInventoryQuery.keyword.trim() || undefined,
      from_date: semiFinishedInventoryQuery.from_date || undefined,
      to_date: semiFinishedInventoryQuery.to_date || undefined,
      page: semiFinishedInventoryQuery.page,
      page_size: semiFinishedInventoryQuery.page_size,
    })
    semiFinishedInventoryRows.value = result.data.items
    semiFinishedInventoryTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    semiFinishedInventoryError.value = message
    resetSemiFinishedInventoryRows()
    ElMessage.error(message)
  } finally {
    semiFinishedInventoryLoading.value = false
  }
}

const loadFinishedGoodsReservedInbound = async (): Promise<void> => {
  if (!canRead.value) {
    resetFinishedGoodsReservedInboundRows()
    finishedGoodsReservedInboundError.value = ''
    return
  }
  finishedGoodsReservedInboundLoading.value = true
  finishedGoodsReservedInboundError.value = ''
  try {
    if (finishedGoodsReservedInboundQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('成品预约入仓区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryFinishedGoodsReservedInbound({
      reservation_no: finishedGoodsReservedInboundQuery.reservation_no.trim() || undefined,
      item_code: finishedGoodsReservedInboundQuery.item_code.trim() || undefined,
      warehouse: finishedGoodsReservedInboundQuery.warehouse.trim() || undefined,
      reserve_status: finishedGoodsReservedInboundQuery.reserve_status || undefined,
      inbound_status: finishedGoodsReservedInboundQuery.inbound_status || undefined,
      keyword: finishedGoodsReservedInboundQuery.keyword.trim() || undefined,
      from_date: finishedGoodsReservedInboundQuery.from_date || undefined,
      to_date: finishedGoodsReservedInboundQuery.to_date || undefined,
      page: finishedGoodsReservedInboundQuery.page,
      page_size: finishedGoodsReservedInboundQuery.page_size,
    })
    finishedGoodsReservedInboundRows.value = result.data.items
    finishedGoodsReservedInboundTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    finishedGoodsReservedInboundError.value = message
    resetFinishedGoodsReservedInboundRows()
    ElMessage.error(message)
  } finally {
    finishedGoodsReservedInboundLoading.value = false
  }
}

const loadFinishedGoodsShippingNotices = async (): Promise<void> => {
  if (!canRead.value) {
    resetFinishedGoodsShippingNoticeRows()
    finishedGoodsShippingNoticeError.value = ''
    return
  }
  finishedGoodsShippingNoticeLoading.value = true
  finishedGoodsShippingNoticeError.value = ''
  try {
    if (finishedGoodsShippingNoticeQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('成品发货通知单区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryFinishedGoodsShippingNotices({
      notice_no: finishedGoodsShippingNoticeQuery.notice_no.trim() || undefined,
      item_code: finishedGoodsShippingNoticeQuery.item_code.trim() || undefined,
      warehouse: finishedGoodsShippingNoticeQuery.warehouse.trim() || undefined,
      notice_status: finishedGoodsShippingNoticeQuery.notice_status || undefined,
      logistics_status: finishedGoodsShippingNoticeQuery.logistics_status || undefined,
      keyword: finishedGoodsShippingNoticeQuery.keyword.trim() || undefined,
      from_date: finishedGoodsShippingNoticeQuery.from_date || undefined,
      to_date: finishedGoodsShippingNoticeQuery.to_date || undefined,
      page: finishedGoodsShippingNoticeQuery.page,
      page_size: finishedGoodsShippingNoticeQuery.page_size,
    })
    finishedGoodsShippingNoticeRows.value = result.data.items
    finishedGoodsShippingNoticeTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    finishedGoodsShippingNoticeError.value = message
    resetFinishedGoodsShippingNoticeRows()
    ElMessage.error(message)
  } finally {
    finishedGoodsShippingNoticeLoading.value = false
  }
}

const loadFinishedGoodsOtherInbound = async (): Promise<void> => {
  if (!canRead.value) {
    resetFinishedGoodsOtherInboundRows()
    finishedGoodsOtherInboundError.value = ''
    return
  }
  finishedGoodsOtherInboundLoading.value = true
  finishedGoodsOtherInboundError.value = ''
  try {
    if (finishedGoodsOtherInboundQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('成品其他入仓区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryFinishedGoodsOtherInbound({
      inbound_no: finishedGoodsOtherInboundQuery.inbound_no.trim() || undefined,
      item_code: finishedGoodsOtherInboundQuery.item_code.trim() || undefined,
      warehouse: finishedGoodsOtherInboundQuery.warehouse.trim() || undefined,
      inbound_status: finishedGoodsOtherInboundQuery.inbound_status || undefined,
      settlement_status: finishedGoodsOtherInboundQuery.settlement_status || undefined,
      keyword: finishedGoodsOtherInboundQuery.keyword.trim() || undefined,
      from_date: finishedGoodsOtherInboundQuery.from_date || undefined,
      to_date: finishedGoodsOtherInboundQuery.to_date || undefined,
      page: finishedGoodsOtherInboundQuery.page,
      page_size: finishedGoodsOtherInboundQuery.page_size,
    })
    finishedGoodsOtherInboundRows.value = result.data.items
    finishedGoodsOtherInboundTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    finishedGoodsOtherInboundError.value = message
    resetFinishedGoodsOtherInboundRows()
    ElMessage.error(message)
  } finally {
    finishedGoodsOtherInboundLoading.value = false
  }
}

const onSearch = (): void => {
  query.page = 1
  void loadRows()
}

const onReset = (): void => {
  query.no = ''
  query.style = ''
  query.warehouse = ''
  query.from_date = ''
  query.to_date = ''
  query.keyword = ''
  query.page = 1
  query.page_size = 20
  void loadRows()
}

const onGuardedAction = (actionName: string): void => {
  ElMessage.warning(`${actionName}功能在本地首版保持只读，未接入真实业务副作用`)
}

const materialTransferStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '调拨中') {
    return 'warning'
  }
  return 'info'
}

const materialCountStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '盘点中') {
    return 'warning'
  }
  return 'info'
}

const materialCountReviewStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已复核') {
    return 'success'
  }
  if (normalized === '待复核') {
    return 'warning'
  }
  return 'info'
}

const materialInventoryReportStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '执行中') {
    return 'warning'
  }
  return 'info'
}

const inventoryMaterialRetentionStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '跟进中') {
    return 'warning'
  }
  return 'info'
}

const semiFinishedInventoryStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '在库') {
    return 'success'
  }
  if (normalized === '返修中') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsReservedInboundReserveStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已入仓' || normalized === '已预约') {
    return 'success'
  }
  if (normalized === '待确认' || normalized === '部分入仓') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsReservedInboundInboundStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '待入仓' || normalized === '入仓中') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsShippingNoticeStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成' || normalized === '已下发') {
    return 'success'
  }
  if (normalized === '待确认' || normalized === '部分发货') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsShippingNoticeLogisticsStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已签收') {
    return 'success'
  }
  if (normalized === '待揽收' || normalized === '运输中') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsOtherInboundStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '待确认' || normalized === '入仓中' || normalized === '部分入仓') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsOtherInboundSettlementStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已核销') {
    return 'success'
  }
  if (normalized === '待核销' || normalized === '核销中') {
    return 'warning'
  }
  return 'info'
}

const onMaterialTransferSearch = (): void => {
  materialTransferQuery.page = 1
  void loadMaterialTransfers()
}

const onMaterialTransferReset = (): void => {
  materialTransferQuery.item_code = ''
  materialTransferQuery.keyword = ''
  materialTransferQuery.source_warehouse = ''
  materialTransferQuery.target_warehouse = ''
  materialTransferQuery.status = ''
  materialTransferQuery.from_date = ''
  materialTransferQuery.to_date = ''
  materialTransferQuery.page = 1
  materialTransferQuery.page_size = 20
  void loadMaterialTransfers()
}

const onMaterialTransferPageChange = (page: number): void => {
  materialTransferQuery.page = page
  void loadMaterialTransfers()
}

const onMaterialTransferSizeChange = (size: number): void => {
  materialTransferQuery.page_size = size
  materialTransferQuery.page = 1
  void loadMaterialTransfers()
}

const onMaterialCountSearch = (): void => {
  materialCountQuery.page = 1
  void loadMaterialCounts()
}

const onMaterialCountReset = (): void => {
  materialCountQuery.item_code = ''
  materialCountQuery.keyword = ''
  materialCountQuery.warehouse = ''
  materialCountQuery.count_status = ''
  materialCountQuery.review_status = ''
  materialCountQuery.from_date = ''
  materialCountQuery.to_date = ''
  materialCountQuery.page = 1
  materialCountQuery.page_size = 20
  void loadMaterialCounts()
}

const onMaterialCountPageChange = (page: number): void => {
  materialCountQuery.page = page
  void loadMaterialCounts()
}

const onMaterialCountSizeChange = (size: number): void => {
  materialCountQuery.page_size = size
  materialCountQuery.page = 1
  void loadMaterialCounts()
}

const onMaterialInventoryReportSearch = (): void => {
  materialInventoryReportQuery.page = 1
  void loadMaterialInventoryReport()
}

const onMaterialInventoryReportReset = (): void => {
  materialInventoryReportQuery.report_no = ''
  materialInventoryReportQuery.item_code = ''
  materialInventoryReportQuery.warehouse = ''
  materialInventoryReportQuery.business_type = ''
  materialInventoryReportQuery.status = ''
  materialInventoryReportQuery.keyword = ''
  materialInventoryReportQuery.from_date = ''
  materialInventoryReportQuery.to_date = ''
  materialInventoryReportQuery.page = 1
  materialInventoryReportQuery.page_size = 20
  void loadMaterialInventoryReport()
}

const onMaterialInventoryReportPageChange = (page: number): void => {
  materialInventoryReportQuery.page = page
  void loadMaterialInventoryReport()
}

const onMaterialInventoryReportSizeChange = (size: number): void => {
  materialInventoryReportQuery.page_size = size
  materialInventoryReportQuery.page = 1
  void loadMaterialInventoryReport()
}

const onInventoryMaterialRetentionReportSearch = (): void => {
  inventoryMaterialRetentionReportQuery.page = 1
  void loadInventoryMaterialRetentionReport()
}

const onInventoryMaterialRetentionReportReset = (): void => {
  inventoryMaterialRetentionReportQuery.report_no = ''
  inventoryMaterialRetentionReportQuery.item_code = ''
  inventoryMaterialRetentionReportQuery.warehouse = ''
  inventoryMaterialRetentionReportQuery.retention_level = ''
  inventoryMaterialRetentionReportQuery.status = ''
  inventoryMaterialRetentionReportQuery.keyword = ''
  inventoryMaterialRetentionReportQuery.from_date = ''
  inventoryMaterialRetentionReportQuery.to_date = ''
  inventoryMaterialRetentionReportQuery.page = 1
  inventoryMaterialRetentionReportQuery.page_size = 20
  void loadInventoryMaterialRetentionReport()
}

const onInventoryMaterialRetentionReportPageChange = (page: number): void => {
  inventoryMaterialRetentionReportQuery.page = page
  void loadInventoryMaterialRetentionReport()
}

const onInventoryMaterialRetentionReportSizeChange = (size: number): void => {
  inventoryMaterialRetentionReportQuery.page_size = size
  inventoryMaterialRetentionReportQuery.page = 1
  void loadInventoryMaterialRetentionReport()
}

const onSemiFinishedInventorySearch = (): void => {
  semiFinishedInventoryQuery.page = 1
  void loadSemiFinishedInventory()
}

const onSemiFinishedInventoryReset = (): void => {
  semiFinishedInventoryQuery.record_no = ''
  semiFinishedInventoryQuery.item_code = ''
  semiFinishedInventoryQuery.warehouse = ''
  semiFinishedInventoryQuery.process_stage = ''
  semiFinishedInventoryQuery.status = ''
  semiFinishedInventoryQuery.keyword = ''
  semiFinishedInventoryQuery.from_date = ''
  semiFinishedInventoryQuery.to_date = ''
  semiFinishedInventoryQuery.page = 1
  semiFinishedInventoryQuery.page_size = 20
  void loadSemiFinishedInventory()
}

const onSemiFinishedInventoryPageChange = (page: number): void => {
  semiFinishedInventoryQuery.page = page
  void loadSemiFinishedInventory()
}

const onSemiFinishedInventorySizeChange = (size: number): void => {
  semiFinishedInventoryQuery.page_size = size
  semiFinishedInventoryQuery.page = 1
  void loadSemiFinishedInventory()
}

const onFinishedGoodsReservedInboundSearch = (): void => {
  finishedGoodsReservedInboundQuery.page = 1
  void loadFinishedGoodsReservedInbound()
}

const onFinishedGoodsReservedInboundReset = (): void => {
  finishedGoodsReservedInboundQuery.reservation_no = ''
  finishedGoodsReservedInboundQuery.item_code = ''
  finishedGoodsReservedInboundQuery.warehouse = ''
  finishedGoodsReservedInboundQuery.reserve_status = ''
  finishedGoodsReservedInboundQuery.inbound_status = ''
  finishedGoodsReservedInboundQuery.keyword = ''
  finishedGoodsReservedInboundQuery.from_date = ''
  finishedGoodsReservedInboundQuery.to_date = ''
  finishedGoodsReservedInboundQuery.page = 1
  finishedGoodsReservedInboundQuery.page_size = 20
  void loadFinishedGoodsReservedInbound()
}

const onFinishedGoodsReservedInboundPageChange = (page: number): void => {
  finishedGoodsReservedInboundQuery.page = page
  void loadFinishedGoodsReservedInbound()
}

const onFinishedGoodsReservedInboundSizeChange = (size: number): void => {
  finishedGoodsReservedInboundQuery.page_size = size
  finishedGoodsReservedInboundQuery.page = 1
  void loadFinishedGoodsReservedInbound()
}

const onFinishedGoodsShippingNoticeSearch = (): void => {
  finishedGoodsShippingNoticeQuery.page = 1
  void loadFinishedGoodsShippingNotices()
}

const onFinishedGoodsShippingNoticeReset = (): void => {
  finishedGoodsShippingNoticeQuery.notice_no = ''
  finishedGoodsShippingNoticeQuery.item_code = ''
  finishedGoodsShippingNoticeQuery.warehouse = ''
  finishedGoodsShippingNoticeQuery.notice_status = ''
  finishedGoodsShippingNoticeQuery.logistics_status = ''
  finishedGoodsShippingNoticeQuery.keyword = ''
  finishedGoodsShippingNoticeQuery.from_date = ''
  finishedGoodsShippingNoticeQuery.to_date = ''
  finishedGoodsShippingNoticeQuery.page = 1
  finishedGoodsShippingNoticeQuery.page_size = 20
  void loadFinishedGoodsShippingNotices()
}

const onFinishedGoodsShippingNoticePageChange = (page: number): void => {
  finishedGoodsShippingNoticeQuery.page = page
  void loadFinishedGoodsShippingNotices()
}

const onFinishedGoodsShippingNoticeSizeChange = (size: number): void => {
  finishedGoodsShippingNoticeQuery.page_size = size
  finishedGoodsShippingNoticeQuery.page = 1
  void loadFinishedGoodsShippingNotices()
}

const onFinishedGoodsOtherInboundSearch = (): void => {
  finishedGoodsOtherInboundQuery.page = 1
  void loadFinishedGoodsOtherInbound()
}

const onFinishedGoodsOtherInboundReset = (): void => {
  finishedGoodsOtherInboundQuery.inbound_no = ''
  finishedGoodsOtherInboundQuery.item_code = ''
  finishedGoodsOtherInboundQuery.warehouse = ''
  finishedGoodsOtherInboundQuery.inbound_status = ''
  finishedGoodsOtherInboundQuery.settlement_status = ''
  finishedGoodsOtherInboundQuery.keyword = ''
  finishedGoodsOtherInboundQuery.from_date = ''
  finishedGoodsOtherInboundQuery.to_date = ''
  finishedGoodsOtherInboundQuery.page = 1
  finishedGoodsOtherInboundQuery.page_size = 20
  void loadFinishedGoodsOtherInbound()
}

const onFinishedGoodsOtherInboundPageChange = (page: number): void => {
  finishedGoodsOtherInboundQuery.page = page
  void loadFinishedGoodsOtherInbound()
}

const onFinishedGoodsOtherInboundSizeChange = (size: number): void => {
  finishedGoodsOtherInboundQuery.page_size = size
  finishedGoodsOtherInboundQuery.page = 1
  void loadFinishedGoodsOtherInbound()
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

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('sales_inventory')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value) {
    await loadRows()
    await loadMaterialTransfers()
    await loadMaterialCounts()
    await loadMaterialInventoryReport()
    await loadInventoryMaterialRetentionReport()
    await loadSemiFinishedInventory()
    await loadFinishedGoodsReservedInbound()
    await loadFinishedGoodsShippingNotices()
    await loadFinishedGoodsOtherInbound()
  }
})
</script>

<style scoped>
.sales-inventory-page {
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

.summary-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
