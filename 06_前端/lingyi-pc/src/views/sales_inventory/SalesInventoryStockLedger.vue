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
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventoryFinishedGoodsReport,
  fetchSalesInventoryInventoryMaterialRetentionReport,
  fetchSalesInventoryMaterialCounts,
  fetchSalesInventoryMaterialInventoryReport,
  fetchSalesInventoryMaterialTransfers,
  type FinishedGoodsReportItem,
  type InventoryMaterialRetentionReportItem,
  type MaterialCountItem,
  type MaterialInventoryReportItem,
  type MaterialTransferItem,
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
