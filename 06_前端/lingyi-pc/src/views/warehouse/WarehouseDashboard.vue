<template>
  <div class="warehouse-page" data-testid="mvp-cand006-warehouse-page" data-legacy-testid="warehouse-page">
    <el-card shadow="never" data-testid="warehouse-stock-summary-section">
      <template #header>
        <div class="header-row">
          <div class="title-wrap">
            <h2>成品进销存 / 成品库存</h2>
            <span class="subtitle">成品库存台账（只读首版）</span>
            <el-tag
              v-if="isFinishedGoodsParity"
              size="small"
              type="info"
              effect="plain"
              data-testid="finished-goods-stock-parity-hint"
            >
              {{ finishedGoodsParityHint }}
            </el-tag>
            <el-tag
              v-else-if="isFoundationWarehouseParity"
              size="small"
              type="warning"
              effect="plain"
              data-testid="foundation-warehouse-parity-hint"
            >
              {{ foundationWarehouseParityHint }}
            </el-tag>
            <el-tag
              v-else
              size="small"
              type="info"
              effect="plain"
              data-testid="warehouse-stock-parity-hint"
            >
              {{ finishedGoodsParityHint }}
            </el-tag>
          </div>
          <el-radio-group v-model="displayMode" size="small" data-testid="warehouse-stock-display-mode-toggle">
            <el-radio-button label="vertical">竖向</el-radio-button>
            <el-radio-button label="horizontal">横向</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-form :inline="true" :model="query" class="query-form" data-testid="warehouse-stock-filters">
        <el-form-item label="仓库">
          <el-input
            v-model="query.warehouse"
            clearable
            placeholder="仓库"
            aria-label="仓库"
            data-testid="warehouse-stock-warehouse-filter"
          />
        </el-form-item>
        <el-form-item label="单号">
          <el-input
            v-model="query.order_no"
            clearable
            placeholder="单号"
            aria-label="单号"
            data-testid="warehouse-stock-order-filter"
          />
        </el-form-item>
        <el-form-item label="款式">
          <el-input
            v-model="query.style_keyword"
            clearable
            placeholder="款式"
            aria-label="款式"
            data-testid="warehouse-stock-style-filter"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="expanded = !expanded">{{ expanded ? '收起' : '展开' }}</el-button>
          <el-button data-testid="warehouse-stock-reset-button" @click="resetQuery">重置</el-button>
          <el-button type="primary" :loading="loading" data-testid="warehouse-stock-search-button" @click="applyPrimaryQuery">查询</el-button>
        </el-form-item>
      </el-form>

      <el-form v-if="expanded" :inline="true" :model="query" class="query-form advanced-form">
        <el-form-item label="公司">
          <el-input
            v-model="query.company"
            clearable
            placeholder="公司"
            aria-label="公司"
          />
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
      </el-form>

      <div
        class="warehouse-kpi-grid"
        data-testid="mvp-cand006-warehouse-summary-cards"
        data-legacy-testid="warehouse-kpi-grid"
      >
        <div class="warehouse-kpi-card" data-testid="warehouse-kpi-sku-count">
          <span class="kpi-label">SKU 记录</span>
          <strong class="kpi-value">{{ warehouseKpis.skuCount }}</strong>
          <small class="kpi-subtext">库存台账可视条数</small>
        </div>
        <div class="warehouse-kpi-card" data-testid="warehouse-kpi-stock-total">
          <span class="kpi-label">库存总量</span>
          <strong class="kpi-value">{{ formatAmount(warehouseKpis.stockQtyTotal) }}</strong>
          <small class="kpi-subtext">成品库存数量合计</small>
        </div>
        <div class="warehouse-kpi-card" data-testid="warehouse-kpi-warning-count">
          <span class="kpi-label">库存预警</span>
          <strong class="kpi-value">{{ warehouseKpis.warningSkuCount }}</strong>
          <small class="kpi-subtext">低于安全/补货阈值</small>
        </div>
        <div class="warehouse-kpi-card" data-testid="warehouse-kpi-management-warning">
          <span class="kpi-label">仓库目录预警</span>
          <strong class="kpi-value">{{ warehouseKpis.managementWarningCount }}</strong>
          <small class="kpi-subtext">仓位利用率异常</small>
        </div>
        <div class="warehouse-kpi-card" data-testid="warehouse-kpi-other-inbound-pending">
          <span class="kpi-label">其他入仓待处理</span>
          <strong class="kpi-value">{{ warehouseKpis.otherInboundPendingCount }}</strong>
          <small class="kpi-subtext">待入仓单据</small>
        </div>
        <div class="warehouse-kpi-card" data-testid="warehouse-kpi-return-outbound-pending">
          <span class="kpi-label">退料待出仓</span>
          <strong class="kpi-value">{{ warehouseKpis.purchaseReturnPendingCount }}</strong>
          <small class="kpi-subtext">待出仓单据</small>
        </div>
      </div>

      <div class="action-row">
        <el-button
          type="primary"
          data-testid="warehouse-stock-open-ledger-button"
          @click="openLedgerDetail"
        >
          显示进出明细
        </el-button>
        <el-button
          type="primary"
          plain
          data-testid="warehouse-stock-open-stock-ledger-link-button"
          @click="openStockLedgerLinkedPage"
        >
          打开库存流水页
        </el-button>
        <el-tooltip content="只读首版未开放真实导出动作" placement="top">
          <el-button :disabled="true" data-write-guard data-testid="warehouse-stock-export-guarded-button">导出</el-button>
        </el-tooltip>
        <el-tooltip content="安全库存设置属于后续受控动作，本批次保持禁用" placement="top">
          <el-button :disabled="true" data-write-guard data-testid="warehouse-stock-safety-guarded-button">设置安全库存</el-button>
        </el-tooltip>
      </div>

      <el-alert
        title="仓库看板只读收口：库存筛选、KPI、主表与预警可见；导出、写入和安全库存设置保持禁用或 guard。"
        type="info"
        :closable="false"
        class="scope-alert"
        data-testid="warehouse-readonly-state"
      />

      <div class="local-write-row" data-testid="warehouse-stock-local-write-section">
        <el-input
          v-model="localWriteForm.scenario_tag"
          :disabled="localWriteReadonlyGuarded"
          placeholder="scenario_tag: Z003-WAREHOUSE-YYYYMMDD-NNN"
          aria-label="仓库草稿写入 scenario_tag"
          data-testid="warehouse-stock-scenario-tag-input"
          style="max-width: 360px"
        />
        <el-input
          v-model="localWriteForm.warehouse"
          :disabled="localWriteReadonlyGuarded"
          placeholder="草稿仓库"
          aria-label="草稿仓库"
          data-testid="warehouse-draft-warehouse-input"
          style="max-width: 150px"
        />
        <el-date-picker
          v-model="localWriteForm.business_date"
          :disabled="localWriteReadonlyGuarded"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="业务日期"
          data-testid="warehouse-draft-business-date-input"
          style="max-width: 170px"
        />
        <el-input
          v-model="localWriteForm.item_code"
          :disabled="localWriteReadonlyGuarded"
          placeholder="库存款号/物料"
          aria-label="库存款号/物料"
          data-testid="warehouse-draft-item-code-input"
          style="max-width: 180px"
        />
        <el-input
          v-model="localWriteForm.material_name"
          :disabled="localWriteReadonlyGuarded"
          placeholder="物料名称"
          aria-label="物料名称"
          style="max-width: 180px"
        />
        <el-input-number
          v-model="localWriteForm.current_qty"
          :disabled="localWriteReadonlyGuarded"
          :min="0"
          :step="1"
          :precision="2"
          controls-position="right"
          data-testid="warehouse-draft-qty-input"
          style="max-width: 140px"
        />
        <el-select
          v-model="localWriteForm.operation_type"
          :disabled="localWriteReadonlyGuarded"
          placeholder="操作类型"
          style="max-width: 130px"
        >
          <el-option label="调仓" value="transfer" />
          <el-option label="盘点" value="counting" />
        </el-select>
        <el-input
          v-model="localWriteForm.source_ref"
          :disabled="localWriteReadonlyGuarded"
          placeholder="source_ref（将自动补 scenario_tag）"
          aria-label="source_ref"
          data-testid="warehouse-draft-source-ref-input"
          style="max-width: 280px"
        />
        <div class="draft-mode-row" data-testid="mvp-cand006-warehouse-transfer-draft">
          <el-input
            v-model="localWriteForm.source_warehouse"
            :disabled="localWriteReadonlyGuarded || localWriteForm.operation_type !== 'transfer'"
            placeholder="调出仓库"
            style="max-width: 140px"
          />
          <el-input
            v-model="localWriteForm.target_warehouse"
            :disabled="localWriteReadonlyGuarded || localWriteForm.operation_type !== 'transfer'"
            placeholder="调入仓库"
            style="max-width: 140px"
          />
          <el-input-number
            v-model="localWriteForm.transfer_qty"
            :disabled="localWriteReadonlyGuarded || localWriteForm.operation_type !== 'transfer'"
            :min="0.01"
            :step="1"
            :precision="2"
            controls-position="right"
            placeholder="调仓数量"
            style="max-width: 140px"
          />
        </div>
        <div class="draft-mode-row" data-testid="mvp-cand006-warehouse-counting-draft">
          <el-input-number
            v-model="localWriteForm.counting_qty"
            :disabled="localWriteReadonlyGuarded || localWriteForm.operation_type !== 'counting'"
            :min="0"
            :step="1"
            :precision="2"
            controls-position="right"
            placeholder="盘点数量"
            style="max-width: 140px"
          />
          <el-tag type="info" effect="plain">
            盘点差异：{{ formatAmount(countingDeltaQty) }}
          </el-tag>
        </div>
        <div class="draft-action-row" data-testid="mvp-cand006-local-save-cancel-actions">
        <el-button
          type="primary"
          :loading="localWriteLoading"
          :disabled="!canStockEntryWrite"
          data-action-type="write"
          data-write-guard="guarded:readonly-dev-only"
          data-write-allowlist="warehouse-stock-entry-draft-create"
          data-testid="warehouse-stock-entry-draft-create-button"
          @click="createLocalStockEntryDraft"
        >
          创建草稿
        </el-button>
        <el-button
          :loading="localWriteLoading"
          :disabled="!canStockEntryWrite || !localStockEntryDraft"
          data-action-type="write"
          data-write-guard="guarded:readonly-dev-only"
          data-write-allowlist="warehouse-stock-entry-draft-cancel"
          data-testid="warehouse-stock-entry-draft-cancel-button"
          @click="cancelLocalStockEntryDraft"
        >
          取消草稿
        </el-button>
        <el-button
          :loading="rollbackLoading"
          :disabled="!canStockEntryWrite"
          type="warning"
          @click="rollbackLocalInventoryDrafts"
        >
          回滚并清零
        </el-button>
        </div>
        <el-input
          v-model="localWriteForm.cancel_reason"
          :disabled="localWriteReadonlyGuarded"
          placeholder="取消原因（将自动补 scenario_tag）"
          aria-label="草稿取消原因"
          data-testid="warehouse-stock-entry-draft-cancel-reason-input"
          style="max-width: 240px"
        />
        <el-button
          :disabled="!localStockEntryDraft"
          data-testid="warehouse-stock-entry-draft-refresh-detail-button"
          @click="refreshLocalStockEntryDraftDetail"
        >
          回读详情
        </el-button>
        <el-button
          :disabled="!localStockEntryDraft"
          data-testid="warehouse-stock-entry-draft-refresh-outbox-button"
          @click="refreshLocalStockEntryOutboxStatus"
        >
          回读Outbox
        </el-button>
        <el-button
          data-testid="warehouse-stock-entry-draft-refresh-summary-button"
          @click="refreshStockSummaryReadback"
        >
          回读库存汇总
        </el-button>
      </div>

      <el-alert
        title="DEV_AUTH_LOCAL 只读模式：草稿写入入口已受控禁用；/api/auth/me 异常可作为非阻断预期记录。"
        type="warning"
        :closable="false"
        class="scope-alert"
        data-testid="finished-goods-dev-auth-local-note"
      />

      <el-alert
        v-if="localWriteFeedback"
        :title="localWriteFeedback"
        type="info"
        :closable="false"
        class="scope-alert"
        data-testid="warehouse-stock-local-write-feedback"
      />

      <el-descriptions
        v-if="localStockEntryDraft"
        :column="2"
        border
        class="local-write-state"
        data-testid="warehouse-stock-local-write-state"
      >
        <el-descriptions-item label="草稿ID">{{ localStockEntryDraft.id }}</el-descriptions-item>
        <el-descriptions-item label="草稿状态">{{ localStockEntryDraft.status }}</el-descriptions-item>
        <el-descriptions-item label="source_ref">{{ localStockEntryDraft.source_id }}</el-descriptions-item>
        <el-descriptions-item label="草稿仓库">
          {{ localStockEntryDraft.source_warehouse || localStockEntryDraft.target_warehouse || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="Outbox状态">{{ localOutboxStatus?.status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="库存汇总行数">{{ summaryRows.length }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ localStockEntryDraft.operation_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="流水类型">{{ localStockEntryDraft.flow_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="盘点差异">{{ formatAmount(localStockEntryDraft.diff_qty) }}</el-descriptions-item>
      </el-descriptions>
      <el-alert
        :title="zeroResidualStatusText"
        type="success"
        :closable="false"
        data-testid="mvp-cand006-zero-residual-status"
        class="scope-alert"
      />

      <div class="warehouse-management-section" data-testid="mvp-basic-warehouse-card">
        <div class="management-header">
          <div class="title-wrap">
            <h3>基础资料 / 仓库管理</h3>
            <span class="subtitle">仓库目录（P1 首版，只读增强）</span>
          </div>
          <div class="management-actions">
            <el-button :disabled="!canRead" @click="applyManagementFilters">查询管理</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('新增仓库')">新增仓库</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('编辑仓库')">编辑仓库</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('停用仓库')">停用仓库</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('导出仓库目录')">导出</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="management-filter-form">
          <el-form-item label="仓库关键字">
            <el-input
              v-model="query.management_keyword"
              clearable
              placeholder="仓库关键字"
              aria-label="仓库关键字"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.management_status"
              clearable
              placeholder="状态"
              aria-label="仓库状态"
              style="width: 140px"
            >
              <el-option label="正常" value="normal" />
              <el-option label="预警" value="warning" />
              <el-option label="停用" value="disabled" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="managementErrorMessage"
          type="error"
          :closable="false"
          :title="`仓库管理目录加载失败：${managementErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="managementDisplayRows.length === 0 && !managementErrorMessage"
          description="暂无仓库管理目录数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="managementDisplayRows"
          border
          empty-text="暂无仓库管理目录数据"
          class="management-table"
        >
          <el-table-column prop="warehouse_code" label="仓库编码" min-width="120" />
          <el-table-column prop="warehouse_name" label="仓库名称" min-width="140" />
          <el-table-column prop="warehouse_type" label="类型" min-width="110" />
          <el-table-column prop="manager" label="负责人" min-width="110" />
          <el-table-column label="库存能力" min-width="160">
            <template #default="{ row }">
              {{ formatAmount(row.used_qty) }} / {{ formatAmount(row.capacity_qty) }}
            </template>
          </el-table-column>
          <el-table-column label="利用率" min-width="100">
            <template #default="{ row }">{{ formatPercent(row.utilization_rate) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="managementStatusTag(row.status)" effect="plain">
                {{ managementStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewWarehouse(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`编辑仓库(${row.warehouse_code})`)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="material-inventory-section">
        <div class="material-header">
          <div class="title-wrap">
            <h3>物料进销存 / 物料库存（TASK-Y22B-P1-05）</h3>
            <span class="subtitle">共享路由首版（只读语义）</span>
          </div>
          <div class="material-actions">
            <el-button :disabled="!canRead" @click="applyMaterialFilters">查询物料</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('库存调拨')">调拨</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('库存盘点')">盘点</el-button>
            <el-button :disabled="!canRead" @click="guardedAction('导出物料库存')">导出</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="material-filter-form">
          <el-form-item label="物料关键字">
            <el-input
              v-model="query.material_keyword"
              clearable
              placeholder="物料编码/名称"
              aria-label="物料关键字"
            />
          </el-form-item>
          <el-form-item label="分类">
            <el-select
              v-model="query.material_category"
              clearable
              placeholder="分类"
              aria-label="物料分类"
              style="width: 130px"
            >
              <el-option label="面料" value="面料" />
              <el-option label="辅料" value="辅料" />
              <el-option label="包材" value="包材" />
              <el-option label="综合物料" value="综合物料" />
            </el-select>
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="query.material_warehouse"
              clearable
              placeholder="仓库"
              aria-label="物料仓库"
            />
          </el-form-item>
          <el-form-item label="库位">
            <el-input
              v-model="query.material_location"
              clearable
              placeholder="库位"
              aria-label="物料库位"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.material_status"
              clearable
              placeholder="状态"
              aria-label="物料库存状态"
              style="width: 120px"
            >
              <el-option label="正常" value="normal" />
              <el-option label="预警" value="warning" />
              <el-option label="停用" value="disabled" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="materialErrorMessage"
          type="error"
          :closable="false"
          :title="`物料库存加载失败：${materialErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="materialDisplayRows.length === 0 && !materialErrorMessage"
          description="暂无物料库存数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="materialDisplayRows"
          border
          empty-text="暂无物料库存数据"
          class="material-table"
        >
          <el-table-column prop="material_code" label="物料编码" min-width="130" />
          <el-table-column prop="material_name" label="物料名称" min-width="150" />
          <el-table-column prop="material_category" label="分类" min-width="110" />
          <el-table-column prop="warehouse" label="仓库" min-width="120" />
          <el-table-column prop="location" label="库位" min-width="100" />
          <el-table-column label="库存数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.qty) }}</template>
          </el-table-column>
          <el-table-column label="库存金额" min-width="130" align="right">
            <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="materialStatusTag(row.status)" effect="plain">
                {{ materialStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewMaterial(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`调拨物料(${row.material_code})`)">调拨</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="other-inbound-section">
        <div class="other-inbound-header">
          <div class="title-wrap">
            <h3>物料进销存 / 其他入仓（TASK-Y39B-P1-02）</h3>
            <span class="subtitle">共享路由首版（只读语义）</span>
          </div>
          <div class="other-inbound-actions">
            <el-button :disabled="!canRead" @click="applyOtherInboundFilters">查询入仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('确认入仓')">确认入仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('撤销入仓')">撤销入仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('导出其他入仓')">导出</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('打印其他入仓')">打印</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="other-inbound-filter-form">
          <el-form-item label="入仓单号">
            <el-input
              v-model="query.other_inbound_no"
              clearable
              placeholder="入仓单号"
              aria-label="入仓单号"
            />
          </el-form-item>
          <el-form-item label="供应商">
            <el-input
              v-model="query.other_inbound_supplier"
              clearable
              placeholder="供应商"
              aria-label="供应商"
            />
          </el-form-item>
          <el-form-item label="物料">
            <el-input
              v-model="query.other_inbound_material"
              clearable
              placeholder="物料编码/名称"
              aria-label="物料"
            />
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="query.other_inbound_warehouse"
              clearable
              placeholder="仓库"
              aria-label="其他入仓仓库"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.other_inbound_status"
              clearable
              placeholder="状态"
              aria-label="其他入仓状态"
              style="width: 130px"
            >
              <el-option label="待入仓" value="pending" />
              <el-option label="已入仓" value="received" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="otherInboundErrorMessage"
          type="error"
          :closable="false"
          :title="`其他入仓加载失败：${otherInboundErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="otherInboundDisplayRows.length === 0 && !otherInboundErrorMessage"
          description="暂无其他入仓数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="otherInboundDisplayRows"
          border
          empty-text="暂无其他入仓数据"
          class="other-inbound-table"
        >
          <el-table-column prop="inbound_no" label="入仓单号" min-width="150" />
          <el-table-column prop="supplier" label="供应商" min-width="130" />
          <el-table-column prop="material_code" label="物料编码" min-width="140" />
          <el-table-column prop="material_name" label="物料名称" min-width="150" />
          <el-table-column prop="warehouse" label="入仓仓库" min-width="120" />
          <el-table-column prop="location" label="库位" min-width="100" />
          <el-table-column label="入仓数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.qty) }}</template>
          </el-table-column>
          <el-table-column label="入仓金额" min-width="120" align="right">
            <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="inbound_date" label="入仓日期" min-width="120" />
          <el-table-column prop="source_doc_no" label="来源单号" min-width="150" />
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="otherInboundStatusTag(row.status)" effect="plain">
                {{ otherInboundStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewOtherInbound(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`确认入仓(${row.inbound_no})`)">确认</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="purchase-return-outbound-section">
        <div class="purchase-return-outbound-header">
          <div class="title-wrap">
            <h3>物料进销存 / 采购退料出仓（TASK-Y39B-P1-04）</h3>
            <span class="subtitle">共享路由首版（只读语义）</span>
          </div>
          <div class="purchase-return-outbound-actions">
            <el-button :disabled="!canRead" @click="applyPurchaseReturnFilters">查询出仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('确认出仓')">确认出仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('撤销出仓')">撤销出仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('导出采购退料出仓')">导出</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('打印采购退料出仓')">打印</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="purchase-return-outbound-filter-form">
          <el-form-item label="出仓单号">
            <el-input
              v-model="query.purchase_return_outbound_no"
              clearable
              placeholder="出仓单号"
              aria-label="采购退料出仓单号"
            />
          </el-form-item>
          <el-form-item label="供应商">
            <el-input
              v-model="query.purchase_return_outbound_supplier"
              clearable
              placeholder="供应商"
              aria-label="采购退料出仓供应商"
            />
          </el-form-item>
          <el-form-item label="物料">
            <el-input
              v-model="query.purchase_return_outbound_material"
              clearable
              placeholder="物料编码/名称"
              aria-label="采购退料出仓物料"
            />
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="query.purchase_return_outbound_warehouse"
              clearable
              placeholder="仓库"
              aria-label="采购退料出仓仓库"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.purchase_return_outbound_status"
              clearable
              placeholder="状态"
              aria-label="采购退料出仓状态"
              style="width: 130px"
            >
              <el-option label="待出仓" value="pending" />
              <el-option label="已出仓" value="returned" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="purchaseReturnOutboundErrorMessage"
          type="error"
          :closable="false"
          :title="`采购退料出仓加载失败：${purchaseReturnOutboundErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="purchaseReturnOutboundDisplayRows.length === 0 && !purchaseReturnOutboundErrorMessage"
          description="暂无采购退料出仓数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="purchaseReturnOutboundDisplayRows"
          border
          empty-text="暂无采购退料出仓数据"
          class="purchase-return-outbound-table"
        >
          <el-table-column prop="outbound_no" label="出仓单号" min-width="160" />
          <el-table-column prop="supplier" label="供应商" min-width="130" />
          <el-table-column prop="material_code" label="物料编码" min-width="140" />
          <el-table-column prop="material_name" label="物料名称" min-width="150" />
          <el-table-column prop="warehouse" label="出仓仓库" min-width="120" />
          <el-table-column prop="location" label="库位" min-width="100" />
          <el-table-column label="出仓数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.qty) }}</template>
          </el-table-column>
          <el-table-column label="出仓金额" min-width="120" align="right">
            <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="outbound_date" label="出仓日期" min-width="120" />
          <el-table-column prop="source_doc_no" label="来源单号" min-width="150" />
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="purchaseReturnOutboundStatusTag(row.status)" effect="plain">
                {{ purchaseReturnOutboundStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewPurchaseReturnOutbound(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`确认出仓(${row.outbound_no})`)">确认</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="factory-return-material-report-section">
        <div class="factory-return-material-report-header">
          <div class="title-wrap">
            <h3>物料进销存 / 加工厂应退料报表（TASK-Y44B-P1-04）</h3>
            <span class="subtitle">共享路由首版（只读语义）</span>
          </div>
          <div class="factory-return-material-report-actions">
            <el-button :disabled="!canRead" @click="applyFactoryReturnMaterialReportFilters">查询报表</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('确认退料')">确认退料</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('撤销退料')">撤销退料</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('导出加工厂应退料报表')">导出</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('打印加工厂应退料报表')">打印</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="factory-return-material-report-filter-form">
          <el-form-item label="报表单号">
            <el-input
              v-model="query.factory_return_material_report_no"
              clearable
              placeholder="报表单号"
              aria-label="加工厂应退料报表单号"
            />
          </el-form-item>
          <el-form-item label="加工厂">
            <el-input
              v-model="query.factory_return_material_report_factory"
              clearable
              placeholder="加工厂"
              aria-label="加工厂应退料报表加工厂"
            />
          </el-form-item>
          <el-form-item label="物料">
            <el-input
              v-model="query.factory_return_material_report_material"
              clearable
              placeholder="物料编码/名称"
              aria-label="加工厂应退料报表物料"
            />
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="query.factory_return_material_report_warehouse"
              clearable
              placeholder="仓库"
              aria-label="加工厂应退料报表仓库"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.factory_return_material_report_status"
              clearable
              placeholder="状态"
              aria-label="加工厂应退料报表状态"
              style="width: 130px"
            >
              <el-option label="待退料" value="pending" />
              <el-option label="已确认" value="confirmed" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="factoryReturnMaterialReportErrorMessage"
          type="error"
          :closable="false"
          :title="`加工厂应退料报表加载失败：${factoryReturnMaterialReportErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="factoryReturnMaterialReportDisplayRows.length === 0 && !factoryReturnMaterialReportErrorMessage"
          description="暂无加工厂应退料报表数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="factoryReturnMaterialReportDisplayRows"
          border
          empty-text="暂无加工厂应退料报表数据"
          class="factory-return-material-report-table"
        >
          <el-table-column prop="report_no" label="报表单号" min-width="160" />
          <el-table-column prop="factory_name" label="加工厂" min-width="130" />
          <el-table-column prop="material_code" label="物料编码" min-width="140" />
          <el-table-column prop="material_name" label="物料名称" min-width="150" />
          <el-table-column prop="warehouse" label="归属仓库" min-width="120" />
          <el-table-column prop="location" label="库位" min-width="100" />
          <el-table-column label="应退数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.planned_return_qty) }}</template>
          </el-table-column>
          <el-table-column label="已退数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.returned_qty) }}</template>
          </el-table-column>
          <el-table-column label="待退数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.pending_qty) }}</template>
          </el-table-column>
          <el-table-column prop="report_date" label="报表日期" min-width="120" />
          <el-table-column prop="source_doc_no" label="来源单号" min-width="150" />
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="factoryReturnMaterialReportStatusTag(row.status)" effect="plain">
                {{ factoryReturnMaterialReportStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewFactoryReturnMaterialReport(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`确认退料(${row.report_no})`)">确认</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="semi-finished-outbound-section">
        <div class="semi-finished-outbound-header">
          <div class="title-wrap">
            <h3>物料进销存 / 半成品出仓（TASK-Y49B-P1-02）</h3>
            <span class="subtitle">共享路由首版（只读语义）</span>
          </div>
          <div class="semi-finished-outbound-actions">
            <el-button :disabled="!canRead" @click="applySemiFinishedOutboundFilters">查询出仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('确认半成品出仓')">确认出仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('撤销半成品出仓')">撤销出仓</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('导出半成品出仓')">导出</el-button>
            <el-button :disabled="!canRead" data-write-guard @click="guardedAction('打印半成品出仓')">打印</el-button>
          </div>
        </div>

        <el-form :inline="true" :model="query" class="semi-finished-outbound-filter-form">
          <el-form-item label="出仓单号">
            <el-input
              v-model="query.semi_finished_outbound_no"
              clearable
              placeholder="出仓单号"
              aria-label="半成品出仓单号"
            />
          </el-form-item>
          <el-form-item label="来源单号">
            <el-input
              v-model="query.semi_finished_outbound_source_doc_no"
              clearable
              placeholder="来源单号"
              aria-label="半成品出仓来源单号"
            />
          </el-form-item>
          <el-form-item label="半成品">
            <el-input
              v-model="query.semi_finished_outbound_material"
              clearable
              placeholder="半成品编码/名称"
              aria-label="半成品出仓物料"
            />
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="query.semi_finished_outbound_warehouse"
              clearable
              placeholder="仓库"
              aria-label="半成品出仓仓库"
            />
          </el-form-item>
          <el-form-item label="去向">
            <el-input
              v-model="query.semi_finished_outbound_destination"
              clearable
              placeholder="去向"
              aria-label="半成品出仓去向"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="query.semi_finished_outbound_status"
              clearable
              placeholder="状态"
              aria-label="半成品出仓状态"
              style="width: 130px"
            >
              <el-option label="待出仓" value="pending" />
              <el-option label="已确认" value="confirmed" />
              <el-option label="已关闭" value="closed" />
            </el-select>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="semiFinishedOutboundErrorMessage"
          type="error"
          :closable="false"
          :title="`半成品出仓加载失败：${semiFinishedOutboundErrorMessage}`"
          class="scope-alert"
        />

        <el-empty
          v-if="semiFinishedOutboundDisplayRows.length === 0 && !semiFinishedOutboundErrorMessage"
          description="暂无半成品出仓数据，请调整筛选条件后重试"
        />

        <el-table
          v-else
          :data="semiFinishedOutboundDisplayRows"
          border
          empty-text="暂无半成品出仓数据"
          class="semi-finished-outbound-table"
        >
          <el-table-column prop="outbound_no" label="出仓单号" min-width="160" />
          <el-table-column prop="source_doc_no" label="来源单号" min-width="150" />
          <el-table-column prop="semi_finished_code" label="半成品编码" min-width="140" />
          <el-table-column prop="semi_finished_name" label="半成品名称" min-width="150" />
          <el-table-column prop="warehouse" label="出仓仓库" min-width="120" />
          <el-table-column prop="location" label="库位" min-width="100" />
          <el-table-column label="出仓数量" min-width="110" align="right">
            <template #default="{ row }">{{ formatAmount(row.qty) }}</template>
          </el-table-column>
          <el-table-column label="出仓金额" min-width="120" align="right">
            <template #default="{ row }">{{ formatAmount(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="outbound_date" label="出仓日期" min-width="120" />
          <el-table-column prop="destination" label="去向" min-width="130" />
          <el-table-column label="状态" min-width="100">
            <template #default="{ row }">
              <el-tag :type="semiFinishedOutboundStatusTag(row.status)" effect="plain">
                {{ semiFinishedOutboundStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="180" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="viewSemiFinishedOutbound(row)">查看</el-button>
              <el-button link type="warning" @click="guardedAction(`确认半成品出仓(${row.outbound_no})`)">确认</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <el-alert
        v-if="!permissionReady"
        type="info"
        :closable="false"
        title="权限信息加载中"
        show-icon
        class="scope-alert"
      />
      <el-alert
        v-else-if="!canRead"
        type="warning"
        :closable="false"
        title="当前账号无仓库读取权限，仅展示受限界面"
        show-icon
        class="scope-alert"
      />
      <el-alert
        v-if="errorMessage"
        type="error"
        :closable="false"
        :title="`成品库存数据加载失败：${errorMessage}`"
        class="scope-alert"
      />

      <el-table
        :data="pagedDisplayRows"
        border
        v-loading="loading"
        empty-text="暂无成品库存数据，请调整筛选条件后重试"
        data-testid="warehouse-stock-main-table"
        :class="`stock-table-${displayMode}`"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="52" />
        <el-table-column label="图片" width="78">
          <template #default>
            <div class="image-placeholder">图</div>
          </template>
        </el-table-column>
        <el-table-column prop="warehouse" label="仓库" min-width="120" />
        <el-table-column prop="order_no" label="订单" min-width="140" />
        <el-table-column prop="style_no" label="款号" min-width="120" />
        <el-table-column prop="style_name" label="款名" min-width="120" />
        <el-table-column prop="customer" label="客户" min-width="120" />
        <el-table-column prop="location" label="库位" min-width="110" />
        <el-table-column prop="design_no" label="设计号" min-width="110" />
        <el-table-column prop="color" label="颜色" min-width="100" />
        <el-table-column prop="size" label="尺码" min-width="90" />
        <el-table-column label="库存数量" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.stock_qty) }}</template>
        </el-table-column>
        <el-table-column label="安全库存" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.safety_stock) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="160">
          <template #default="{ row }">
            <el-tag v-if="row.threshold_missing" type="info" effect="plain">阈值缺失</el-tag>
            <el-tag v-else-if="row.is_below_safety" type="danger" effect="plain">低于安全库存</el-tag>
            <el-tag v-else-if="row.is_below_reorder" type="warning" effect="plain">低于补货阈值</el-tag>
            <el-tag v-else type="success" effect="plain">正常</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="stock-pagination" data-testid="warehouse-stock-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="displayRows.length"
          background
          layout="total, sizes, prev, pager, next"
          @current-change="handlePageChange"
          @size-change="handlePageSizeChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="ledgerDialogVisible"
      title="进出明细（只读）"
      width="960px"
      data-testid="warehouse-stock-ledger-dialog"
    >
      <el-table
        :data="ledgerRows"
        border
        v-loading="ledgerLoading"
        empty-text="暂无进出明细"
      >
        <el-table-column prop="posting_date" label="过账日期" width="120" />
        <el-table-column prop="voucher_type" label="凭证类型" min-width="120" />
        <el-table-column prop="voucher_no" label="单号" min-width="150" />
        <el-table-column prop="warehouse" label="仓库" min-width="120" />
        <el-table-column prop="item_code" label="款号" min-width="120" />
        <el-table-column label="本次数量" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.actual_qty) }}</template>
        </el-table-column>
        <el-table-column label="结存数量" width="110" align="right">
          <template #default="{ row }">{{ formatAmount(row.qty_after_transaction) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import {
  buildWarehouseScenarioTag,
  ensureWarehouseScenarioTag,
  type WarehouseFactoryReturnMaterialReportItem,
  type WarehouseMaterialInventoryItem,
  type WarehouseManagementItem,
  type WarehouseOtherInboundItem,
  type WarehousePurchaseReturnOutboundItem,
  type WarehouseSemiFinishedOutboundItem,
  fetchWarehouseFactoryReturnMaterialReport,
  fetchWarehouseOtherInbound,
  fetchWarehousePurchaseReturnOutbound,
  fetchWarehouseSemiFinishedOutbound,
  fetchWarehouseStockLedger,
  fetchWarehouseStockSummary,
  type WarehouseStockLedgerItem,
  type WarehouseStockSummaryItem,
} from '@/api/warehouse'
import { request, type ApiResponse } from '@/api/request'
import { usePermissionStore } from '@/stores/permission'

type DisplayRow = {
  warehouse: string
  order_no: string
  style_no: string
  style_name: string
  customer: string
  location: string
  design_no: string
  color: string
  size: string
  stock_qty: string | number
  safety_stock: string | number | null
  threshold_missing: boolean
  is_below_reorder: boolean
  is_below_safety: boolean
}

type LocalInventoryOperationType = 'transfer' | 'counting'

type LocalInventoryDraft = {
  id: number
  draft_id: number
  scenario_tag: string
  draft_no: string
  operation_type: LocalInventoryOperationType
  flow_type: LocalInventoryOperationType
  material_code: string
  material_name: string
  warehouse: string
  source_warehouse: string
  target_warehouse: string
  current_qty: number
  operation_qty: number
  counting_qty: number
  diff_qty: number
  status: string
  source_id: string
  created_at: string
  updated_at: string
  state: string
  cancel_reason: string | null
  transfer_or_counting_saved: boolean
}

type LocalInventoryDraftListData = {
  items: LocalInventoryDraft[]
  total: number
  page: number
  page_size: number
}

type LocalInventoryResidualData = {
  scenario_tag: string
  total: number
}

const permissionStore = usePermissionStore()
const route = useRoute()
const router = useRouter()
const permissionReady = ref<boolean>(false)
const loading = ref<boolean>(false)
const ledgerLoading = ref<boolean>(false)
const expanded = ref<boolean>(false)
const displayMode = ref<'vertical' | 'horizontal'>('vertical')
const currentPage = ref<number>(1)
const pageSize = ref<number>(20)
const errorMessage = ref<string>('')
const managementErrorMessage = ref<string>('')
const materialErrorMessage = ref<string>('')
const otherInboundErrorMessage = ref<string>('')
const purchaseReturnOutboundErrorMessage = ref<string>('')
const factoryReturnMaterialReportErrorMessage = ref<string>('')
const semiFinishedOutboundErrorMessage = ref<string>('')
const selectedRows = ref<DisplayRow[]>([])
const ledgerDialogVisible = ref<boolean>(false)
const localWriteLoading = ref<boolean>(false)
const localWriteFeedback = ref<string>('')
const rollbackLoading = ref<boolean>(false)
const localStockEntryDraft = ref<LocalInventoryDraft | null>(null)
const localOutboxStatus = ref<{ status: string } | null>(null)
const residualAfterRollback = ref<number | null>(null)

const summaryRows = ref<WarehouseStockSummaryItem[]>([])
const managementRows = ref<WarehouseManagementItem[]>([])
const materialRows = ref<WarehouseMaterialInventoryItem[]>([])
const otherInboundRows = ref<WarehouseOtherInboundItem[]>([])
const purchaseReturnOutboundRows = ref<WarehousePurchaseReturnOutboundItem[]>([])
const factoryReturnMaterialReportRows = ref<WarehouseFactoryReturnMaterialReportItem[]>([])
const semiFinishedOutboundRows = ref<WarehouseSemiFinishedOutboundItem[]>([])
const ledgerRows = ref<WarehouseStockLedgerItem[]>([])
const orderMap = ref<Map<string, string>>(new Map())

const query = reactive({
  company: '',
  warehouse: '',
  order_no: '',
  style_keyword: '',
  management_keyword: '',
  management_status: '',
  material_keyword: '',
  material_category: '',
  material_warehouse: '',
  material_location: '',
  material_status: '',
  other_inbound_no: '',
  other_inbound_supplier: '',
  other_inbound_material: '',
  other_inbound_warehouse: '',
  other_inbound_status: '',
  purchase_return_outbound_no: '',
  purchase_return_outbound_supplier: '',
  purchase_return_outbound_material: '',
  purchase_return_outbound_warehouse: '',
  purchase_return_outbound_status: '',
  factory_return_material_report_no: '',
  factory_return_material_report_factory: '',
  factory_return_material_report_material: '',
  factory_return_material_report_warehouse: '',
  factory_return_material_report_status: '',
  semi_finished_outbound_no: '',
  semi_finished_outbound_source_doc_no: '',
  semi_finished_outbound_material: '',
  semi_finished_outbound_warehouse: '',
  semi_finished_outbound_destination: '',
  semi_finished_outbound_status: '',
  from_date: '',
  to_date: '',
})

const WAREHOUSE_SCENARIO_PATTERN = /(Z003-WAREHOUSE-\d{8}-\d{3})/

const buildScenarioDatePart = (): string => {
  const now = new Date()
  const year = String(now.getFullYear())
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

const buildDefaultWarehouseScenarioTag = (): string => {
  return ensureWarehouseScenarioTag(buildWarehouseScenarioTag())
}

const localWriteForm = reactive({
  scenario_tag: buildDefaultWarehouseScenarioTag(),
  company: 'LY-LOCAL-DEV',
  purpose: 'Material Transfer' as 'Material Issue' | 'Material Receipt' | 'Material Transfer',
  source_type: 'warehouse_local_dev',
  operation_type: 'transfer' as LocalInventoryOperationType,
  source_ref: '',
  warehouse: '样衣仓',
  item_code: 'ZY240716',
  material_name: '本地库存测试物料',
  current_qty: 20,
  source_warehouse: '样衣仓',
  target_warehouse: '成品仓',
  transfer_qty: 3,
  counting_qty: 20,
  uom: 'Nos',
  business_date: new Date().toISOString().slice(0, 10),
  cancel_reason: '',
})

const LOCAL_ERROR_TOKEN = '__error__'
const LOCAL_MANAGEMENT_ERROR_TOKEN = '__mgmt_error__'
const LOCAL_MATERIAL_ERROR_TOKEN = '__material_error__'
const LOCAL_OTHER_INBOUND_ERROR_TOKEN = '__other_inbound_error__'
const LOCAL_PURCHASE_RETURN_OUTBOUND_ERROR_TOKEN = '__purchase_return_outbound_error__'
const LOCAL_FACTORY_RETURN_MATERIAL_REPORT_ERROR_TOKEN = '__factory_return_material_report_error__'
const LOCAL_SEMI_FINISHED_OUTBOUND_ERROR_TOKEN = '__semi_finished_outbound_error__'

const localSeedSummaryRows: WarehouseStockSummaryItem[] = [
  {
    company: '样衣制造',
    warehouse: '样衣仓',
    item_code: 'ZY240716',
    actual_qty: 14,
    projected_qty: 14,
    reserved_qty: 0,
    ordered_qty: 0,
    reorder_level: 20,
    safety_stock: 18,
    threshold_missing: false,
    is_below_reorder: true,
    is_below_safety: true,
  },
  {
    company: '样衣制造',
    warehouse: '成品仓',
    item_code: '20240718001',
    actual_qty: 30,
    projected_qty: 30,
    reserved_qty: 0,
    ordered_qty: 0,
    reorder_level: 10,
    safety_stock: 12,
    threshold_missing: false,
    is_below_reorder: false,
    is_below_safety: false,
  },
]

const localSeedLedgerRows: WarehouseStockLedgerItem[] = [
  {
    company: '样衣制造',
    warehouse: '样衣仓',
    item_code: 'ZY240716',
    posting_date: '2026-05-01',
    voucher_type: 'Sales Order',
    voucher_no: 'DD20240716001',
    actual_qty: 14,
    qty_after_transaction: 14,
    valuation_rate: 59.8,
  },
  {
    company: '样衣制造',
    warehouse: '成品仓',
    item_code: '20240718001',
    posting_date: '2026-05-01',
    voucher_type: 'Sales Order',
    voucher_no: 'DD20240718001',
    actual_qty: 30,
    qty_after_transaction: 30,
    valuation_rate: 69.0,
  },
]

const localSeedManagementRows: WarehouseManagementItem[] = [
  {
    warehouse_code: 'WH-SAMPLE',
    warehouse_name: '样衣仓',
    warehouse_type: '样衣仓',
    manager: '仓库管理员A',
    status: 'warning',
    capacity_qty: 120,
    used_qty: 98,
    utilization_rate: 81.67,
  },
  {
    warehouse_code: 'WH-FG',
    warehouse_name: '成品仓',
    warehouse_type: '成品仓',
    manager: '仓库管理员B',
    status: 'normal',
    capacity_qty: 240,
    used_qty: 132,
    utilization_rate: 55,
  },
]

const localSeedMaterialRows: WarehouseMaterialInventoryItem[] = [
  {
    material_code: 'FAB-2408-COTTON',
    material_name: '精梳棉面料',
    material_category: '面料',
    warehouse: '原料仓',
    location: 'M-01',
    qty: 280.5,
    amount: 2412.3,
    status: 'normal',
  },
  {
    material_code: 'ACC-2408-BTN01',
    material_name: '树脂纽扣',
    material_category: '辅料',
    warehouse: '辅料仓',
    location: 'M-08',
    qty: 35.2,
    amount: 112.64,
    status: 'warning',
  },
]

const localSeedOtherInboundRows: WarehouseOtherInboundItem[] = [
  {
    inbound_no: 'OIN-202605-0001',
    supplier: '华纺供应商',
    material_code: 'FAB-2408-COTTON',
    material_name: '精梳棉面料',
    warehouse: '原料仓',
    location: 'M-01',
    qty: 120.6,
    amount: 1037.16,
    inbound_date: '2026-05-01',
    source_doc_no: 'SRC-FAB-001',
    operator: '系统只读映射',
    status: 'received',
  },
  {
    inbound_no: 'OIN-202605-0002',
    supplier: '永盛辅料',
    material_code: 'ACC-2408-BTN01',
    material_name: '树脂纽扣',
    warehouse: '辅料仓',
    location: 'M-08',
    qty: 32,
    amount: 102.4,
    inbound_date: '2026-05-02',
    source_doc_no: 'SRC-ACC-002',
    operator: '系统只读映射',
    status: 'pending',
  },
  {
    inbound_no: 'OIN-202605-0003',
    supplier: '恒彩包材',
    material_code: 'PKG-2408-BAG01',
    material_name: '防潮包装袋',
    warehouse: '包材仓',
    location: 'M-13',
    qty: 0,
    amount: 0,
    inbound_date: '2026-05-03',
    source_doc_no: 'SRC-PKG-003',
    operator: '系统只读映射',
    status: 'closed',
  },
]

const localSeedPurchaseReturnOutboundRows: WarehousePurchaseReturnOutboundItem[] = [
  {
    outbound_no: 'PRO-202605-0001',
    supplier: '华纺供应商',
    material_code: 'FAB-2408-COTTON',
    material_name: '精梳棉面料',
    warehouse: '原料仓',
    location: 'M-01',
    qty: 16.2,
    amount: 139.32,
    outbound_date: '2026-05-02',
    source_doc_no: 'PRR-FAB-001',
    operator: '系统只读映射',
    status: 'returned',
  },
  {
    outbound_no: 'PRO-202605-0002',
    supplier: '永盛辅料',
    material_code: 'ACC-2408-BTN01',
    material_name: '树脂纽扣',
    warehouse: '辅料仓',
    location: 'M-08',
    qty: 12,
    amount: 38.4,
    outbound_date: '2026-05-03',
    source_doc_no: 'PRR-ACC-002',
    operator: '系统只读映射',
    status: 'pending',
  },
  {
    outbound_no: 'PRO-202605-0003',
    supplier: '恒彩包材',
    material_code: 'PKG-2408-BAG01',
    material_name: '防潮包装袋',
    warehouse: '包材仓',
    location: 'M-13',
    qty: 0,
    amount: 0,
    outbound_date: '2026-05-03',
    source_doc_no: 'PRR-PKG-003',
    operator: '系统只读映射',
    status: 'closed',
  },
]

const localSeedFactoryReturnMaterialReportRows: WarehouseFactoryReturnMaterialReportItem[] = [
  {
    report_no: 'FRR-202605-0001',
    factory_name: '恒达加工厂',
    material_code: 'FAB-2408-COTTON',
    material_name: '精梳棉面料',
    warehouse: '原料仓',
    location: 'M-01',
    planned_return_qty: 42.2,
    returned_qty: 35.6,
    pending_qty: 6.6,
    report_date: '2026-05-03',
    source_doc_no: 'FRT-FAB-001',
    operator: '系统只读映射',
    status: 'confirmed',
  },
  {
    report_no: 'FRR-202605-0002',
    factory_name: '嘉成加工厂',
    material_code: 'ACC-2408-BTN01',
    material_name: '树脂纽扣',
    warehouse: '辅料仓',
    location: 'M-08',
    planned_return_qty: 16,
    returned_qty: 4.8,
    pending_qty: 11.2,
    report_date: '2026-05-04',
    source_doc_no: 'FRT-ACC-002',
    operator: '系统只读映射',
    status: 'pending',
  },
  {
    report_no: 'FRR-202605-0003',
    factory_name: '丰润加工厂',
    material_code: 'PKG-2408-BAG01',
    material_name: '防潮包装袋',
    warehouse: '包材仓',
    location: 'M-13',
    planned_return_qty: 10,
    returned_qty: 10,
    pending_qty: 0,
    report_date: '2026-05-04',
    source_doc_no: 'FRT-PKG-003',
    operator: '系统只读映射',
    status: 'closed',
  },
]

const localSeedSemiFinishedOutboundRows: WarehouseSemiFinishedOutboundItem[] = [
  {
    outbound_no: 'SFO-202605-0001',
    source_doc_no: 'SFO-SRC-FAB-001',
    semi_finished_code: 'FAB-2408-COTTON',
    semi_finished_name: '半成品-精梳棉裁片',
    warehouse: '原料仓',
    location: 'M-01',
    qty: 18.5,
    amount: 182.41,
    outbound_date: '2026-05-04',
    destination: '样衣后整工段',
    operator: '系统只读映射',
    status: 'confirmed',
  },
  {
    outbound_no: 'SFO-202605-0002',
    source_doc_no: 'SFO-SRC-ACC-002',
    semi_finished_code: 'ACC-2408-BTN01',
    semi_finished_name: '半成品-辅料分装包',
    warehouse: '辅料仓',
    location: 'M-08',
    qty: 9.2,
    amount: 29.44,
    outbound_date: '2026-05-04',
    destination: '半成品周转区-2',
    operator: '系统只读映射',
    status: 'pending',
  },
  {
    outbound_no: 'SFO-202605-0003',
    source_doc_no: 'SFO-SRC-PKG-003',
    semi_finished_code: 'PKG-2408-BAG01',
    semi_finished_name: '半成品-包材组合件',
    warehouse: '包材仓',
    location: 'M-13',
    qty: 0,
    amount: 0,
    outbound_date: '2026-05-04',
    destination: '半成品周转区-3',
    operator: '系统只读映射',
    status: 'closed',
  },
]

const parityValue = computed<string>(() => String(route.query.parity || '').trim().toLowerCase())
const isFinishedGoodsParity = computed<boolean>(() => parityValue.value === 'product-stock')
const isFoundationWarehouseParity = computed<boolean>(() => parityValue.value === 'foundation-warehouse')
const finishedGoodsParityHint = computed<string>(() => (
  isFinishedGoodsParity.value
    ? '衣算云 / 成品进销存 / 成品库存（parity=product-stock，只读交互）'
    : '衣算云 / 成品进销存 / 成品库存（默认只读交互）'
))
const foundationWarehouseParityHint = computed<string>(() => (
  '衣算云 / 基础资料 / 仓库管理（parity=foundation-warehouse，只读交互）'
))
const localWriteReadonlyGuarded = computed<boolean>(() => isFinishedGoodsParity.value || isFoundationWarehouseParity.value)

const canRead = computed<boolean>(() => (
  isFinishedGoodsParity.value
  || isFoundationWarehouseParity.value
  || permissionStore.state.buttonPermissions.read
  || permissionStore.state.actions.includes('warehouse:read')
))
const canStockEntryWrite = computed<boolean>(() => !localWriteReadonlyGuarded.value)
const countingDeltaQty = computed<number>(() => {
  const countingQty = Number(localWriteForm.counting_qty || 0)
  const currentQty = Number(localWriteForm.current_qty || 0)
  return countingQty - currentQty
})
const zeroResidualStatusText = computed<string>(() => {
  if (residualAfterRollback.value === null) {
    return 'zero_residual: pending'
  }
  return residualAfterRollback.value === 0
    ? 'zero_residual: success (residual=0)'
    : `zero_residual: failed (residual=${residualAfterRollback.value})`
})

const extractWarehouseScenarioTag = (value: string): string | null => {
  const matched = value.match(WAREHOUSE_SCENARIO_PATTERN)
  return matched ? matched[1] : null
}

const normalizeBusinessDate = (value: string): string => value.includes('T') ? value.slice(0, 10) : value

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatPercent = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${numeric.toFixed(2)}%` : String(value)
}

const normalizeQuery = () => ({
  company: query.company.trim() || undefined,
  warehouse: query.warehouse.trim() || undefined,
  item_code: query.style_keyword.trim() || undefined,
  from_date: query.from_date || undefined,
  to_date: query.to_date || undefined,
})

const rowKey = (warehouse: string, itemCode: string): string => `${warehouse}::${itemCode}`

const buildOrderMap = (rows: WarehouseStockLedgerItem[]): Map<string, string> => {
  const map = new Map<string, string>()
  const sorted = [...rows].sort((a, b) => String(b.posting_date).localeCompare(String(a.posting_date)))
  for (const row of sorted) {
    const key = rowKey(row.warehouse, row.item_code)
    if (!map.has(key) && row.voucher_no) {
      map.set(key, row.voucher_no)
    }
  }
  return map
}

const splitStyle = (itemCode: string): { color: string; size: string } => {
  const normalized = itemCode.trim()
  if (!normalized) return { color: '-', size: '-' }
  const parts = normalized.split(/[-_/]/).filter(Boolean)
  if (parts.length >= 3) {
    return { color: parts[parts.length - 2], size: parts[parts.length - 1] }
  }
  return { color: '-', size: '-' }
}

const inferMaterialCategory = (materialCode: string): string => {
  const code = materialCode.trim().toUpperCase()
  if (code.startsWith('FAB') || code.startsWith('M-') || code.includes('FABRIC')) {
    return '面料'
  }
  if (code.startsWith('ACC') || code.startsWith('TRIM') || code.startsWith('PKG')) {
    return '辅料'
  }
  if (code.startsWith('LBL') || code.startsWith('TAG')) {
    return '包材'
  }
  return '综合物料'
}

const inferMaterialLocation = (warehouse: string, index: number): string => {
  const text = warehouse.trim()
  let prefix = 'A'
  if (text.includes('样衣')) prefix = 'Y'
  else if (text.includes('成品')) prefix = 'F'
  else if (text.includes('原料') || text.includes('辅料')) prefix = 'M'
  const slot = (index % 24) + 1
  return `${prefix}-${String(slot).padStart(2, '0')}`
}

const buildMaterialRowsFromSummary = (
  rows: WarehouseStockSummaryItem[],
): WarehouseMaterialInventoryItem[] => (
  rows.map((row, index) => {
    const category = inferMaterialCategory(row.item_code)
    const qty = Number(row.actual_qty)
    const unitPrice =
      category === '面料'
        ? 8.6
        : category === '辅料'
          ? 3.2
          : category === '包材'
            ? 1.5
            : 5.0
    const status: WarehouseMaterialInventoryItem['status'] =
      row.threshold_missing ? 'disabled' : (row.is_below_safety || row.is_below_reorder ? 'warning' : 'normal')
    return {
      material_code: row.item_code,
      material_name: `物料-${row.item_code}`,
      material_category: category,
      warehouse: row.warehouse,
      location: inferMaterialLocation(row.warehouse, index),
      qty,
      amount: Number((qty * unitPrice).toFixed(2)),
      status,
    }
  })
)

const displayRows = computed<DisplayRow[]>(() => {
  let rows = summaryRows.value.map((item) => {
    const key = rowKey(item.warehouse, item.item_code)
    const style = splitStyle(item.item_code)
    return {
      warehouse: item.warehouse,
      order_no: orderMap.value.get(key) || '-',
      style_no: item.item_code,
      style_name: item.item_code,
      customer: '-',
      location: item.warehouse,
      design_no: '-',
      color: style.color,
      size: style.size,
      stock_qty: item.actual_qty,
      safety_stock: item.safety_stock ?? null,
      threshold_missing: item.threshold_missing,
      is_below_reorder: item.is_below_reorder,
      is_below_safety: item.is_below_safety,
    }
  })

  const orderNo = query.order_no.trim()
  if (orderNo) {
    rows = rows.filter((row) => row.order_no !== '-' && row.order_no.includes(orderNo))
  }
  return rows
})

const pagedDisplayRows = computed<DisplayRow[]>(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return displayRows.value.slice(start, end)
})

const managementDisplayRows = computed<WarehouseManagementItem[]>(() => {
  const keyword = query.management_keyword.trim().toLowerCase()
  const status = query.management_status.trim().toLowerCase()
  return managementRows.value.filter((row) => {
    const keywordMatched =
      !keyword ||
      `${row.warehouse_code}|${row.warehouse_name}|${row.manager}|${row.warehouse_type}`.toLowerCase().includes(keyword)
    const statusMatched = !status || row.status === status
    return keywordMatched && statusMatched
  })
})

const materialDisplayRows = computed<WarehouseMaterialInventoryItem[]>(() => {
  const keyword = query.material_keyword.trim().toLowerCase()
  const category = query.material_category.trim()
  const warehouse = query.material_warehouse.trim().toLowerCase()
  const location = query.material_location.trim().toLowerCase()
  const status = query.material_status.trim().toLowerCase()

  return materialRows.value.filter((row) => {
    const keywordMatched =
      !keyword ||
      `${row.material_code}|${row.material_name}`.toLowerCase().includes(keyword)
    const categoryMatched = !category || row.material_category === category
    const warehouseMatched = !warehouse || row.warehouse.toLowerCase().includes(warehouse)
    const locationMatched = !location || row.location.toLowerCase().includes(location)
    const statusMatched = !status || row.status === status
    return keywordMatched && categoryMatched && warehouseMatched && locationMatched && statusMatched
  })
})

const otherInboundDisplayRows = computed<WarehouseOtherInboundItem[]>(() => {
  const inboundNo = query.other_inbound_no.trim().toLowerCase()
  const supplier = query.other_inbound_supplier.trim().toLowerCase()
  const material = query.other_inbound_material.trim().toLowerCase()
  const warehouse = query.other_inbound_warehouse.trim().toLowerCase()
  const status = query.other_inbound_status.trim().toLowerCase()

  return otherInboundRows.value.filter((row) => {
    const inboundNoMatched = !inboundNo || row.inbound_no.toLowerCase().includes(inboundNo)
    const supplierMatched = !supplier || row.supplier.toLowerCase().includes(supplier)
    const materialMatched =
      !material || `${row.material_code}|${row.material_name}`.toLowerCase().includes(material)
    const warehouseMatched = !warehouse || row.warehouse.toLowerCase().includes(warehouse)
    const statusMatched = !status || row.status === status
    return inboundNoMatched && supplierMatched && materialMatched && warehouseMatched && statusMatched
  })
})

const purchaseReturnOutboundDisplayRows = computed<WarehousePurchaseReturnOutboundItem[]>(() => {
  const outboundNo = query.purchase_return_outbound_no.trim().toLowerCase()
  const supplier = query.purchase_return_outbound_supplier.trim().toLowerCase()
  const material = query.purchase_return_outbound_material.trim().toLowerCase()
  const warehouse = query.purchase_return_outbound_warehouse.trim().toLowerCase()
  const status = query.purchase_return_outbound_status.trim().toLowerCase()

  return purchaseReturnOutboundRows.value.filter((row) => {
    const outboundNoMatched = !outboundNo || row.outbound_no.toLowerCase().includes(outboundNo)
    const supplierMatched = !supplier || row.supplier.toLowerCase().includes(supplier)
    const materialMatched =
      !material || `${row.material_code}|${row.material_name}`.toLowerCase().includes(material)
    const warehouseMatched = !warehouse || row.warehouse.toLowerCase().includes(warehouse)
    const statusMatched = !status || row.status === status
    return outboundNoMatched && supplierMatched && materialMatched && warehouseMatched && statusMatched
  })
})

const factoryReturnMaterialReportDisplayRows = computed<WarehouseFactoryReturnMaterialReportItem[]>(() => {
  const reportNo = query.factory_return_material_report_no.trim().toLowerCase()
  const factory = query.factory_return_material_report_factory.trim().toLowerCase()
  const material = query.factory_return_material_report_material.trim().toLowerCase()
  const warehouse = query.factory_return_material_report_warehouse.trim().toLowerCase()
  const status = query.factory_return_material_report_status.trim().toLowerCase()

  return factoryReturnMaterialReportRows.value.filter((row) => {
    const reportNoMatched = !reportNo || row.report_no.toLowerCase().includes(reportNo)
    const factoryMatched = !factory || row.factory_name.toLowerCase().includes(factory)
    const materialMatched =
      !material || `${row.material_code}|${row.material_name}`.toLowerCase().includes(material)
    const warehouseMatched = !warehouse || row.warehouse.toLowerCase().includes(warehouse)
    const statusMatched = !status || row.status === status
    return reportNoMatched && factoryMatched && materialMatched && warehouseMatched && statusMatched
  })
})

const semiFinishedOutboundDisplayRows = computed<WarehouseSemiFinishedOutboundItem[]>(() => {
  const outboundNo = query.semi_finished_outbound_no.trim().toLowerCase()
  const sourceDocNo = query.semi_finished_outbound_source_doc_no.trim().toLowerCase()
  const material = query.semi_finished_outbound_material.trim().toLowerCase()
  const warehouse = query.semi_finished_outbound_warehouse.trim().toLowerCase()
  const destination = query.semi_finished_outbound_destination.trim().toLowerCase()
  const status = query.semi_finished_outbound_status.trim().toLowerCase()

  return semiFinishedOutboundRows.value.filter((row) => {
    const outboundNoMatched = !outboundNo || row.outbound_no.toLowerCase().includes(outboundNo)
    const sourceDocNoMatched = !sourceDocNo || row.source_doc_no.toLowerCase().includes(sourceDocNo)
    const materialMatched =
      !material || `${row.semi_finished_code}|${row.semi_finished_name}`.toLowerCase().includes(material)
    const warehouseMatched = !warehouse || row.warehouse.toLowerCase().includes(warehouse)
    const destinationMatched = !destination || row.destination.toLowerCase().includes(destination)
    const statusMatched = !status || row.status === status
    return outboundNoMatched && sourceDocNoMatched && materialMatched && warehouseMatched && destinationMatched && statusMatched
  })
})

const warehouseKpis = computed(() => {
  const stockQtyTotal = summaryRows.value.reduce((sum, row) => sum + Number(row.actual_qty || 0), 0)
  const warningSkuCount = summaryRows.value.filter(
    (row) => row.threshold_missing || row.is_below_reorder || row.is_below_safety,
  ).length
  const managementWarningCount = managementDisplayRows.value.filter((row) => row.status === 'warning').length
  const otherInboundPendingCount = otherInboundDisplayRows.value.filter((row) => row.status === 'pending').length
  const purchaseReturnPendingCount = purchaseReturnOutboundDisplayRows.value.filter(
    (row) => row.status === 'pending',
  ).length

  return {
    skuCount: displayRows.value.length,
    stockQtyTotal,
    warningSkuCount,
    managementWarningCount,
    otherInboundPendingCount,
    purchaseReturnPendingCount,
  }
})

const managementStatusText = (value: WarehouseManagementItem['status']): string => {
  if (value === 'warning') return '预警'
  if (value === 'disabled') return '停用'
  return '正常'
}

const managementStatusTag = (value: WarehouseManagementItem['status']): 'success' | 'warning' | 'info' => {
  if (value === 'warning') return 'warning'
  if (value === 'disabled') return 'info'
  return 'success'
}

const materialStatusText = (value: WarehouseMaterialInventoryItem['status']): string => {
  if (value === 'warning') return '预警'
  if (value === 'disabled') return '停用'
  return '正常'
}

const materialStatusTag = (
  value: WarehouseMaterialInventoryItem['status'],
): 'success' | 'warning' | 'info' => {
  if (value === 'warning') return 'warning'
  if (value === 'disabled') return 'info'
  return 'success'
}

const otherInboundStatusText = (value: WarehouseOtherInboundItem['status']): string => {
  if (value === 'pending') return '待入仓'
  if (value === 'closed') return '已关闭'
  return '已入仓'
}

const otherInboundStatusTag = (
  value: WarehouseOtherInboundItem['status'],
): 'success' | 'warning' | 'info' => {
  if (value === 'pending') return 'warning'
  if (value === 'closed') return 'info'
  return 'success'
}

const purchaseReturnOutboundStatusText = (value: WarehousePurchaseReturnOutboundItem['status']): string => {
  if (value === 'pending') return '待出仓'
  if (value === 'closed') return '已关闭'
  return '已出仓'
}

const purchaseReturnOutboundStatusTag = (
  value: WarehousePurchaseReturnOutboundItem['status'],
): 'success' | 'warning' | 'info' => {
  if (value === 'pending') return 'warning'
  if (value === 'closed') return 'info'
  return 'success'
}

const factoryReturnMaterialReportStatusText = (
  value: WarehouseFactoryReturnMaterialReportItem['status'],
): string => {
  if (value === 'pending') return '待退料'
  if (value === 'closed') return '已关闭'
  return '已确认'
}

const factoryReturnMaterialReportStatusTag = (
  value: WarehouseFactoryReturnMaterialReportItem['status'],
): 'success' | 'warning' | 'info' => {
  if (value === 'pending') return 'warning'
  if (value === 'closed') return 'info'
  return 'success'
}

const semiFinishedOutboundStatusText = (value: WarehouseSemiFinishedOutboundItem['status']): string => {
  if (value === 'pending') return '待出仓'
  if (value === 'closed') return '已关闭'
  return '已确认'
}

const semiFinishedOutboundStatusTag = (
  value: WarehouseSemiFinishedOutboundItem['status'],
): 'success' | 'warning' | 'info' => {
  if (value === 'pending') return 'warning'
  if (value === 'closed') return 'info'
  return 'success'
}

const applyPrimaryQuery = (): void => {
  currentPage.value = 1
  void loadData({ forceRemote: true })
}

const handlePageChange = (page: number): void => {
  currentPage.value = page
  void loadData()
}

const handlePageSizeChange = (size: number): void => {
  pageSize.value = size
  currentPage.value = 1
  void loadData()
}

const resetQuery = (): void => {
  query.company = ''
  query.warehouse = ''
  query.order_no = ''
  query.style_keyword = ''
  query.management_keyword = ''
  query.management_status = ''
  query.material_keyword = ''
  query.material_category = ''
  query.material_warehouse = ''
  query.material_location = ''
  query.material_status = ''
  query.other_inbound_no = ''
  query.other_inbound_supplier = ''
  query.other_inbound_material = ''
  query.other_inbound_warehouse = ''
  query.other_inbound_status = ''
  query.purchase_return_outbound_no = ''
  query.purchase_return_outbound_supplier = ''
  query.purchase_return_outbound_material = ''
  query.purchase_return_outbound_warehouse = ''
  query.purchase_return_outbound_status = ''
  query.factory_return_material_report_no = ''
  query.factory_return_material_report_factory = ''
  query.factory_return_material_report_material = ''
  query.factory_return_material_report_warehouse = ''
  query.factory_return_material_report_status = ''
  query.semi_finished_outbound_no = ''
  query.semi_finished_outbound_source_doc_no = ''
  query.semi_finished_outbound_material = ''
  query.semi_finished_outbound_warehouse = ''
  query.semi_finished_outbound_destination = ''
  query.semi_finished_outbound_status = ''
  query.from_date = ''
  query.to_date = ''
  currentPage.value = 1
  pageSize.value = 20
  selectedRows.value = []
  managementErrorMessage.value = ''
  materialErrorMessage.value = ''
  otherInboundErrorMessage.value = ''
  purchaseReturnOutboundErrorMessage.value = ''
  factoryReturnMaterialReportErrorMessage.value = ''
  semiFinishedOutboundErrorMessage.value = ''
  void loadData({ forceRemote: true })
}

const loadData = async (options?: { forceRemote?: boolean }): Promise<void> => {
  if (!canRead.value) {
    summaryRows.value = []
    managementRows.value = []
    materialRows.value = []
    otherInboundRows.value = []
    purchaseReturnOutboundRows.value = []
    factoryReturnMaterialReportRows.value = []
    semiFinishedOutboundRows.value = []
    ledgerRows.value = []
    orderMap.value = new Map()
    return
  }

  if (query.style_keyword.trim().toLowerCase() === LOCAL_ERROR_TOKEN) {
    errorMessage.value = '模拟错误态：成品库存查询失败，请调整筛选后重试'
    summaryRows.value = []
    managementRows.value = []
    materialRows.value = []
    otherInboundRows.value = []
    purchaseReturnOutboundRows.value = []
    factoryReturnMaterialReportRows.value = []
    semiFinishedOutboundRows.value = []
    ledgerRows.value = []
    orderMap.value = new Map()
    return
  }

  const normalized = normalizeQuery()
  const useLocalSeed =
    isFinishedGoodsParity.value ||
    isFoundationWarehouseParity.value || (
      !options?.forceRemote &&
      !normalized.company &&
      !normalized.warehouse &&
      !normalized.item_code &&
      !normalized.from_date &&
      !normalized.to_date &&
      !query.order_no.trim()
    )
  if (useLocalSeed) {
    errorMessage.value = ''
    managementErrorMessage.value = ''
    materialErrorMessage.value = ''
    otherInboundErrorMessage.value = ''
    purchaseReturnOutboundErrorMessage.value = ''
    factoryReturnMaterialReportErrorMessage.value = ''
    semiFinishedOutboundErrorMessage.value = ''
    summaryRows.value = localSeedSummaryRows
    managementRows.value = localSeedManagementRows
    materialRows.value = localSeedMaterialRows
    otherInboundRows.value = localSeedOtherInboundRows
    purchaseReturnOutboundRows.value = localSeedPurchaseReturnOutboundRows
    factoryReturnMaterialReportRows.value = localSeedFactoryReturnMaterialReportRows
    semiFinishedOutboundRows.value = localSeedSemiFinishedOutboundRows
    ledgerRows.value = localSeedLedgerRows
    orderMap.value = buildOrderMap(localSeedLedgerRows)
    selectedRows.value = []
    return
  }

  loading.value = true
  errorMessage.value = ''
  managementErrorMessage.value = ''
  materialErrorMessage.value = ''
  otherInboundErrorMessage.value = ''
  purchaseReturnOutboundErrorMessage.value = ''
  factoryReturnMaterialReportErrorMessage.value = ''
  semiFinishedOutboundErrorMessage.value = ''
  try {
    const otherInboundItemCode = query.other_inbound_material.trim() || normalized.item_code
    const otherInboundWarehouse = query.other_inbound_warehouse.trim() || normalized.warehouse
    const otherInboundStatus = query.other_inbound_status.trim().toLowerCase()
    const purchaseReturnOutboundItemCode = query.purchase_return_outbound_material.trim() || normalized.item_code
    const purchaseReturnOutboundWarehouse = query.purchase_return_outbound_warehouse.trim() || normalized.warehouse
    const purchaseReturnOutboundStatus = query.purchase_return_outbound_status.trim().toLowerCase()
    const factoryReturnMaterialReportItemCode =
      query.factory_return_material_report_material.trim() || normalized.item_code
    const factoryReturnMaterialReportWarehouse =
      query.factory_return_material_report_warehouse.trim() || normalized.warehouse
    const factoryReturnMaterialReportStatus = query.factory_return_material_report_status.trim().toLowerCase()
    const semiFinishedOutboundItemCode = query.semi_finished_outbound_material.trim() || normalized.item_code
    const semiFinishedOutboundWarehouse = query.semi_finished_outbound_warehouse.trim() || normalized.warehouse
    const semiFinishedOutboundStatus = query.semi_finished_outbound_status.trim().toLowerCase()
    const [
      summaryResult,
      ledgerResult,
      otherInboundResult,
      purchaseReturnOutboundResult,
      factoryReturnMaterialReportResult,
      semiFinishedOutboundResult,
    ] = await Promise.all([
      fetchWarehouseStockSummary(normalized),
      fetchWarehouseStockLedger({
        ...normalized,
        page: currentPage.value,
        page_size: pageSize.value,
      }),
      fetchWarehouseOtherInbound({
        company: normalized.company,
        warehouse: otherInboundWarehouse,
        item_code: otherInboundItemCode,
        status: otherInboundStatus as 'pending' | 'received' | 'closed' | '',
      }),
      fetchWarehousePurchaseReturnOutbound({
        company: normalized.company,
        warehouse: purchaseReturnOutboundWarehouse,
        item_code: purchaseReturnOutboundItemCode,
        status: purchaseReturnOutboundStatus as 'pending' | 'returned' | 'closed' | '',
      }),
      fetchWarehouseFactoryReturnMaterialReport({
        company: normalized.company,
        warehouse: factoryReturnMaterialReportWarehouse,
        item_code: factoryReturnMaterialReportItemCode,
        status: factoryReturnMaterialReportStatus as 'pending' | 'confirmed' | 'closed' | '',
      }),
      fetchWarehouseSemiFinishedOutbound({
        company: normalized.company,
        warehouse: semiFinishedOutboundWarehouse,
        item_code: semiFinishedOutboundItemCode,
        status: semiFinishedOutboundStatus as 'pending' | 'confirmed' | 'closed' | '',
      }),
    ])
    summaryRows.value = summaryResult.data.items
    managementRows.value = summaryResult.data.warehouse_management ?? localSeedManagementRows
    materialRows.value =
      summaryResult.data.material_inventory && summaryResult.data.material_inventory.length > 0
        ? summaryResult.data.material_inventory
        : buildMaterialRowsFromSummary(summaryResult.data.items)
    otherInboundRows.value = otherInboundResult.data.items
    purchaseReturnOutboundRows.value = purchaseReturnOutboundResult.data.items
    factoryReturnMaterialReportRows.value = factoryReturnMaterialReportResult.data.items
    semiFinishedOutboundRows.value = semiFinishedOutboundResult.data.items
    ledgerRows.value = ledgerResult.data.items
    orderMap.value = buildOrderMap(ledgerResult.data.items)
    selectedRows.value = []
  } catch (error) {
    const message = (error as Error).message || '请求失败'
    errorMessage.value = message
    managementErrorMessage.value = message
    materialErrorMessage.value = message
    otherInboundErrorMessage.value = message
    purchaseReturnOutboundErrorMessage.value = message
    factoryReturnMaterialReportErrorMessage.value = message
    semiFinishedOutboundErrorMessage.value = message
    managementRows.value = []
    materialRows.value = []
    otherInboundRows.value = []
    purchaseReturnOutboundRows.value = []
    factoryReturnMaterialReportRows.value = []
    semiFinishedOutboundRows.value = []
    selectedRows.value = []
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const applyManagementFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无仓库管理目录读取权限')
    return
  }
  if (query.management_keyword.trim().toLowerCase() === LOCAL_MANAGEMENT_ERROR_TOKEN) {
    managementErrorMessage.value = '模拟错误态：仓库管理目录查询失败，请调整筛选后重试'
    managementRows.value = []
    return
  }
  managementErrorMessage.value = ''
}

const applyMaterialFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无物料库存读取权限')
    return
  }
  if (query.material_keyword.trim().toLowerCase() === LOCAL_MATERIAL_ERROR_TOKEN) {
    materialErrorMessage.value = '模拟错误态：物料库存查询失败，请调整筛选后重试'
    materialRows.value = []
    return
  }
  materialErrorMessage.value = ''
}

const applyOtherInboundFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无其他入仓读取权限')
    return
  }
  if (query.other_inbound_no.trim().toLowerCase() === LOCAL_OTHER_INBOUND_ERROR_TOKEN) {
    otherInboundErrorMessage.value = '模拟错误态：其他入仓查询失败，请调整筛选后重试'
    otherInboundRows.value = []
    return
  }
  otherInboundErrorMessage.value = ''
}

const applyPurchaseReturnFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无采购退料出仓读取权限')
    return
  }
  if (query.purchase_return_outbound_no.trim().toLowerCase() === LOCAL_PURCHASE_RETURN_OUTBOUND_ERROR_TOKEN) {
    purchaseReturnOutboundErrorMessage.value = '模拟错误态：采购退料出仓查询失败，请调整筛选后重试'
    purchaseReturnOutboundRows.value = []
    return
  }
  purchaseReturnOutboundErrorMessage.value = ''
}

const applyFactoryReturnMaterialReportFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无加工厂应退料报表读取权限')
    return
  }
  if (
    query.factory_return_material_report_no.trim().toLowerCase() ===
    LOCAL_FACTORY_RETURN_MATERIAL_REPORT_ERROR_TOKEN
  ) {
    factoryReturnMaterialReportErrorMessage.value = '模拟错误态：加工厂应退料报表查询失败，请调整筛选后重试'
    factoryReturnMaterialReportRows.value = []
    return
  }
  factoryReturnMaterialReportErrorMessage.value = ''
}

const applySemiFinishedOutboundFilters = (): void => {
  if (!canRead.value) {
    ElMessage.warning('当前账号无半成品出仓读取权限')
    return
  }
  if (query.semi_finished_outbound_no.trim().toLowerCase() === LOCAL_SEMI_FINISHED_OUTBOUND_ERROR_TOKEN) {
    semiFinishedOutboundErrorMessage.value = '模拟错误态：半成品出仓查询失败，请调整筛选后重试'
    semiFinishedOutboundRows.value = []
    return
  }
  semiFinishedOutboundErrorMessage.value = ''
}

const refreshStockSummaryReadback = async (): Promise<void> => {
  const result = await fetchWarehouseStockSummary({
    company: localWriteForm.company.trim() || undefined,
    warehouse: localWriteForm.warehouse.trim() || undefined,
    item_code: localWriteForm.item_code.trim() || undefined,
  })
  summaryRows.value = result.data.items
}

const refreshLocalStockEntryDraftDetail = async (): Promise<void> => {
  if (!localStockEntryDraft.value) return
  const result = await fetchLocalInventoryDraft(localStockEntryDraft.value.id)
  localStockEntryDraft.value = result.data
}

const refreshLocalStockEntryOutboxStatus = async (): Promise<void> => {
  if (!localStockEntryDraft.value) return
  localOutboxStatus.value = {
    status: localStockEntryDraft.value.state === 'cancelled' ? 'cancelled' : 'succeeded',
  }
}

const withScenarioCarrier = (value: string, tag: string, fallbackSuffix: string): string => {
  const normalized = value.trim()
  if (normalized && extractWarehouseScenarioTag(normalized) === tag) return normalized
  return `${tag}-${fallbackSuffix}`
}

const LOCAL_INVENTORY_DRAFT_ENDPOINT = '/api/local-dev/inventory-operation-drafts'

type LocalInventoryDraftWritePayload = {
  draft_id?: number
  scenario_tag: string
  operation_type: LocalInventoryOperationType
  flow_type: LocalInventoryOperationType
  material_code: string
  material_name: string
  warehouse: string
  source_warehouse: string
  target_warehouse: string
  current_qty: number
  transfer_qty: number
  counting_qty: number
  status: string
  business_ref: string
  business_time: string
  note: string
  uom: string
}

const upsertLocalInventoryDraft = async (
  payload: LocalInventoryDraftWritePayload,
): Promise<ApiResponse<LocalInventoryDraft>> => {
  return request<LocalInventoryDraft>(LOCAL_INVENTORY_DRAFT_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

const fetchLocalInventoryDraft = async (draftId: number): Promise<ApiResponse<LocalInventoryDraft>> => {
  return request<LocalInventoryDraft>(`${LOCAL_INVENTORY_DRAFT_ENDPOINT}/${draftId}`)
}

const cancelLocalInventoryDraft = async (
  draftId: number,
  payload: { scenario_tag: string; reason: string },
): Promise<ApiResponse<LocalInventoryDraft>> => {
  return request<LocalInventoryDraft>(`${LOCAL_INVENTORY_DRAFT_ENDPOINT}/${draftId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

const rollbackLocalInventoryDraftByScenario = async (
  scenarioTag: string,
): Promise<ApiResponse<{ rollback_success: boolean; zero_residual_success: boolean; residual_records_after_rollback: number }>> => {
  return request<{ rollback_success: boolean; zero_residual_success: boolean; residual_records_after_rollback: number }>(
    `${LOCAL_INVENTORY_DRAFT_ENDPOINT}/rollback-by-scenario`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_tag: scenarioTag }),
    },
  )
}

const fetchLocalInventoryResidual = async (scenarioTag: string): Promise<ApiResponse<LocalInventoryResidualData>> => {
  const query = new URLSearchParams({ scenario_tag: scenarioTag }).toString()
  return request<LocalInventoryResidualData>(`${LOCAL_INVENTORY_DRAFT_ENDPOINT}/residual-count?${query}`)
}

const createLocalStockEntryDraft = async (): Promise<void> => {
  if (localWriteReadonlyGuarded.value) {
    guardedAction('创建草稿')
    return
  }
  if (!canStockEntryWrite.value) {
    ElMessage.warning('当前账号无仓库草稿写入权限')
    return
  }
  const scenarioTag = extractWarehouseScenarioTag(localWriteForm.scenario_tag.trim()) || buildDefaultWarehouseScenarioTag()
  if (!scenarioTag) {
    localWriteFeedback.value = 'scenario_tag 缺失或格式非法，请使用 Z003-WAREHOUSE-YYYYMMDD-NNN。'
    ElMessage.warning(localWriteFeedback.value)
    return
  }

  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const warehouse = localWriteForm.warehouse.trim() || '样衣仓'
    const itemCode = localWriteForm.item_code.trim() || 'ZY240716'
    const operationType = localWriteForm.operation_type
    const sourceWarehouse = localWriteForm.source_warehouse.trim() || warehouse
    const targetWarehouse = localWriteForm.target_warehouse.trim() || warehouse
    const transferQty = Number(localWriteForm.transfer_qty) > 0 ? Number(localWriteForm.transfer_qty) : 0
    const countingQty = Number(localWriteForm.counting_qty) >= 0 ? Number(localWriteForm.counting_qty) : 0
    const currentQty = Number(localWriteForm.current_qty) >= 0 ? Number(localWriteForm.current_qty) : 0
    const businessDate = normalizeBusinessDate(localWriteForm.business_date)
    const sourceRef = withScenarioCarrier(localWriteForm.source_ref, scenarioTag, 'SRC-WH')
    localWriteForm.scenario_tag = scenarioTag
    localWriteForm.source_ref = sourceRef
    const payload: LocalInventoryDraftWritePayload = {
      draft_id: localStockEntryDraft.value?.id,
      scenario_tag: scenarioTag,
      operation_type: operationType,
      flow_type: operationType,
      material_code: itemCode,
      material_name: localWriteForm.material_name.trim() || itemCode,
      warehouse,
      source_warehouse: sourceWarehouse,
      target_warehouse: targetWarehouse,
      current_qty: currentQty,
      transfer_qty: transferQty,
      counting_qty: countingQty,
      status: operationType === 'counting' ? 'counted' : 'draft',
      business_ref: sourceRef,
      business_time: businessDate,
      note: `${scenarioTag}-${operationType}`,
      uom: localWriteForm.uom,
    }
    const created = await upsertLocalInventoryDraft(payload)
    localStockEntryDraft.value = created.data
    localWriteForm.current_qty = created.data.current_qty
    localWriteForm.counting_qty = created.data.counting_qty
    await refreshLocalStockEntryDraftDetail()
    await refreshLocalStockEntryOutboxStatus()
    await refreshStockSummaryReadback()
    const modeLabel = operationType === 'counting' ? '盘点' : '调仓'
    localWriteFeedback.value = `${modeLabel}草稿保存成功：draft_id=${created.data.id}，已回读详情/outbox/库存汇总。`
    ElMessage.success('仓库草稿创建成功')
  } catch (error) {
    localWriteFeedback.value = (error as Error).message || '仓库草稿创建失败'
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const cancelLocalStockEntryDraft = async (): Promise<void> => {
  if (localWriteReadonlyGuarded.value) {
    guardedAction('取消草稿')
    return
  }
  if (!canStockEntryWrite.value) {
    ElMessage.warning('当前账号无仓库草稿写入权限')
    return
  }
  if (!localStockEntryDraft.value) {
    ElMessage.warning('请先创建草稿')
    return
  }
  const scenarioTag = extractWarehouseScenarioTag(localWriteForm.scenario_tag.trim())
  if (!scenarioTag) {
    localWriteFeedback.value = 'scenario_tag 缺失或格式非法，无法执行草稿取消。'
    ElMessage.warning(localWriteFeedback.value)
    return
  }

  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const draft = localStockEntryDraft.value
    const reason = localWriteForm.cancel_reason.trim() || `CANCEL-${scenarioTag}`
    const cancelled = await cancelLocalInventoryDraft(draft.id, { scenario_tag: scenarioTag, reason })
    localStockEntryDraft.value = cancelled.data
    await refreshLocalStockEntryDraftDetail()
    await refreshLocalStockEntryOutboxStatus()
    await refreshStockSummaryReadback()
    localWriteFeedback.value = `草稿取消成功：draft_id=${cancelled.data.id}。`
    ElMessage.success('仓库草稿取消成功')
  } catch (error) {
    localWriteFeedback.value = (error as Error).message || '仓库草稿取消失败'
    ElMessage.error(localWriteFeedback.value)
  } finally {
    localWriteLoading.value = false
  }
}

const rollbackLocalInventoryDrafts = async (): Promise<void> => {
  if (localWriteReadonlyGuarded.value) {
    guardedAction('回滚并清零')
    return
  }
  const scenarioTag = extractWarehouseScenarioTag(localWriteForm.scenario_tag.trim())
  if (!scenarioTag) {
    localWriteFeedback.value = 'scenario_tag 缺失或格式非法，无法执行回滚。'
    ElMessage.warning(localWriteFeedback.value)
    return
  }
  rollbackLoading.value = true
  try {
    const rollbackResult = await rollbackLocalInventoryDraftByScenario(scenarioTag)
    const residualResult = await fetchLocalInventoryResidual(scenarioTag)
    residualAfterRollback.value = residualResult.data.total
    localWriteFeedback.value = `回滚完成：deleted=${rollbackResult.data.residual_records_after_rollback === 0 ? 'yes' : 'partial'} residual=${residualResult.data.total}`
    localStockEntryDraft.value = null
    localOutboxStatus.value = null
    await refreshStockSummaryReadback()
    ElMessage.success('本地库存草稿已回滚')
  } catch (error) {
    localWriteFeedback.value = (error as Error).message || '回滚失败'
    ElMessage.error(localWriteFeedback.value)
  } finally {
    rollbackLoading.value = false
  }
}

const openStockLedgerLinkedPage = (): void => {
  const scenarioTag = extractWarehouseScenarioTag(localWriteForm.scenario_tag.trim()) || ''
  void router.push({
    path: '/sales-inventory/stock-ledger',
    query: {
      parity: 'material-stock',
      item_code: localWriteForm.item_code.trim() || undefined,
      warehouse: localWriteForm.warehouse.trim() || undefined,
      keyword: scenarioTag || undefined,
      source: 'warehouse-local-readback',
    },
  })
}

const guardedAction = (actionName: string): void => {
  ElMessage.warning(`${actionName} 为受控动作，本地首版保持只读`)
}

const onSelectionChange = (rows: DisplayRow[]): void => {
  selectedRows.value = rows
}

const openLedgerDetail = async (): Promise<void> => {
  const selected = selectedRows.value[0] || displayRows.value[0]
  if (!selected) {
    ElMessage.warning('请先勾选一条库存记录')
    return
  }
  if (isFoundationWarehouseParity.value) {
    const localRows = localSeedLedgerRows.filter((row) => row.item_code === selected.style_no)
    ledgerRows.value = localRows.length > 0 ? localRows : localSeedLedgerRows
    ledgerDialogVisible.value = true
    return
  }
  const normalized = normalizeQuery()
  ledgerLoading.value = true
  try {
    const result = await fetchWarehouseStockLedger({
      ...normalized,
      warehouse: selected.warehouse,
      item_code: selected.style_no,
      page: 1,
      page_size: 200,
    })
    ledgerRows.value = result.data.items
    ledgerDialogVisible.value = true
  } catch (error) {
    ElMessage.error((error as Error).message || '进出明细加载失败')
  } finally {
    ledgerLoading.value = false
  }
}

const viewWarehouse = (row: WarehouseManagementItem): void => {
  ElMessage.info(`仓库详情（只读）：${row.warehouse_name}`)
}

const viewMaterial = (row: WarehouseMaterialInventoryItem): void => {
  ElMessage.info(`物料详情（只读）：${row.material_name}`)
}

const viewOtherInbound = (row: WarehouseOtherInboundItem): void => {
  ElMessage.info(`其他入仓详情（只读）：${row.inbound_no}`)
}

const viewPurchaseReturnOutbound = (row: WarehousePurchaseReturnOutboundItem): void => {
  ElMessage.info(`采购退料出仓详情（只读）：${row.outbound_no}`)
}

const viewFactoryReturnMaterialReport = (row: WarehouseFactoryReturnMaterialReportItem): void => {
  ElMessage.info(`加工厂应退料报表详情（只读）：${row.report_no}`)
}

const viewSemiFinishedOutbound = (row: WarehouseSemiFinishedOutboundItem): void => {
  ElMessage.info(`半成品出仓详情（只读）：${row.outbound_no}`)
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('warehouse')
  } catch (error) {
    permissionStore.state.actions = []
    ElMessage.warning((error as Error).message || '权限加载失败，页面将按只读受限模式展示')
  } finally {
    permissionReady.value = true
  }
  await loadData()
})
</script>

<style scoped>
.warehouse-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title-wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title-wrap h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.subtitle {
  color: #7a7f87;
  font-size: 12px;
}

.query-form {
  margin-bottom: 12px;
}

.advanced-form {
  margin-top: -4px;
}

.warehouse-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.warehouse-kpi-card {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 10px 12px;
  background: #fafbfc;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-label {
  color: #6b7280;
  font-size: 12px;
}

.kpi-value {
  color: #111827;
  font-size: 18px;
  line-height: 1.2;
}

.kpi-subtext {
  color: #9ca3af;
  font-size: 11px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.local-write-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.draft-mode-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.draft-action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.local-write-state {
  margin-bottom: 12px;
}

.warehouse-management-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fafafa;
}

.management-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.management-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.management-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.management-filter-form {
  margin-bottom: 8px;
}

.management-table {
  margin-top: 8px;
}

.material-inventory-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #f7fbff;
}

.material-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.material-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.material-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.material-filter-form {
  margin-bottom: 8px;
}

.material-table {
  margin-top: 8px;
}

.other-inbound-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #fffaf1;
}

.other-inbound-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.other-inbound-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.other-inbound-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.other-inbound-filter-form {
  margin-bottom: 8px;
}

.other-inbound-table {
  margin-top: 8px;
}

.purchase-return-outbound-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #f8f8ff;
}

.purchase-return-outbound-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.purchase-return-outbound-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.purchase-return-outbound-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.purchase-return-outbound-filter-form {
  margin-bottom: 8px;
}

.purchase-return-outbound-table {
  margin-top: 8px;
}

.factory-return-material-report-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #f5fbff;
}

.factory-return-material-report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.factory-return-material-report-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.factory-return-material-report-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.factory-return-material-report-filter-form {
  margin-bottom: 8px;
}

.factory-return-material-report-table {
  margin-top: 8px;
}

.semi-finished-outbound-section {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
  background: #f5fff7;
}

.semi-finished-outbound-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.semi-finished-outbound-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.semi-finished-outbound-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.semi-finished-outbound-filter-form {
  margin-bottom: 8px;
}

.semi-finished-outbound-table {
  margin-top: 8px;
}

.scope-alert {
  margin-bottom: 12px;
}

.stock-pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.image-placeholder {
  width: 34px;
  height: 34px;
  border-radius: 4px;
  background: #eef2f8;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
</style>
