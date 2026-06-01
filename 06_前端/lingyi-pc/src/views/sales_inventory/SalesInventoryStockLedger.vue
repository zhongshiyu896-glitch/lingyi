<template>
  <div class="sales-inventory-page" data-testid="mvp-cand006-stock-ledger-page" data-legacy-testid="stock-ledger-page">
    <el-card shadow="never" data-testid="yisuan-1to1-stock-ledger-shell">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">{{ stockLedgerTitle }}</span>
            <span class="sub-title">{{ stockLedgerSubTitle }}</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <section class="stock-ledger-section" data-testid="stock-ledger-section">
          <el-form
            :inline="true"
            :model="query"
            class="query-form"
            data-testid="mvp-cand006-stock-query-panel"
            data-legacy-testid="stock-ledger-filter-form"
          >
          <el-form-item label="款号">
            <el-input
              v-model="query.item_code"
              clearable
              placeholder="必填：请输入款号"
              data-testid="mvp-cand006-stock-material-filter"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item label="公司">
            <el-input
              v-model="query.company"
              clearable
              placeholder="公司"
              data-testid="stock-ledger-company-input"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="query.warehouse"
              clearable
              placeholder="仓库"
              data-testid="mvp-cand006-stock-warehouse-filter"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item label="关键词">
            <el-input
              v-model="query.keyword"
              clearable
              placeholder="凭证号/凭证类型/仓库（本地过滤）"
              data-testid="stock-ledger-keyword-input"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item label="状态">
            <el-input
              v-model="query.status"
              clearable
              placeholder="正常/低库存/缺货（本地过滤）"
              data-testid="stock-ledger-status-input"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item label="流水类型">
            <el-input
              v-model="query.flow_type"
              clearable
              placeholder="Sales Order / Material Transfer / Inventory Count"
              data-testid="stock-ledger-flow-type-input"
              @keyup.enter="onSearch"
            />
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="query.from_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="开始日期"
              clearable
              data-testid="stock-ledger-from-date-input"
            />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker
              v-model="query.to_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="结束日期"
              clearable
              data-testid="stock-ledger-to-date-input"
            />
          </el-form-item>
          <el-form-item>
            <el-button :disabled="!canRead && !isMaterialStockParity" data-testid="stock-ledger-reset-button" @click="onReset">
              重置
            </el-button>
            <el-button
              type="primary"
              :disabled="!canRead && !isMaterialStockParity"
              data-testid="stock-ledger-query-button"
              @click="onSearch"
            >
              查询
            </el-button>
          </el-form-item>
        </el-form>

        <el-alert
          v-if="isMaterialStockParity"
          type="info"
          :closable="false"
          data-testid="material-stock-parity-hint"
          title="衣算云 / 物料进销存 / 物料库存（只读交互）"
          description="当前为 parity=material-stock，本地仅开放读取、筛选、分页、空态/错误态验证。"
        />
        <el-alert
          type="info"
          :closable="false"
          class="scope-alert"
          data-testid="yisuan-1to1-ui-source-readback"
          title="UI source readback: B034 boundary（A001/A002/A003 库存/仓库契约壳层）"
        />
        <section class="contract-merge-panel" data-testid="contract-cand005-source-readback">
          <div class="contract-merge-title">A001/A002/A003 契约合并回读（库存流水 / 仓库）</div>
          <div class="contract-tag-row">
            <span class="contract-inline-label">covered_contract_ids:</span>
            <el-tag
              v-for="contractId in contractCoveredIds"
              :key="contractId"
              size="small"
              effect="plain"
              type="success"
            >
              {{ contractId }}
            </el-tag>
            <el-tag size="small" effect="plain" type="warning">partial/unknown/blocked preserved=true</el-tag>
            <el-tag size="small" effect="plain" type="warning">claimed_as_confirmed=false</el-tag>
            <el-tag size="small" effect="plain" type="info">disabled_only/readback_only</el-tag>
            <el-tag size="small" effect="plain" type="info">not_claimed_as_business_action=true</el-tag>
          </div>
          <div class="contract-readback-grid">
            <el-card shadow="never" class="contract-readback-card" data-testid="contract-source-files-readback">
              <template #header>contract source files</template>
              <ul>
                <li v-for="sourceFile in contractSourceFiles" :key="sourceFile">{{ sourceFile }}</li>
              </ul>
            </el-card>
            <el-card shadow="never" class="contract-readback-card" data-testid="contract-key-validation-status-readback">
              <template #header>key_fields / validation_rules / status_rules</template>
              <ul>
                <li v-for="item in contractFieldRuleReadback" :key="item">{{ item }}</li>
              </ul>
            </el-card>
            <el-card shadow="never" class="contract-readback-card" data-testid="contract-readonly-readback-requirements">
              <template #header>readonly / readback requirements</template>
              <ul>
                <li v-for="item in contractReadonlyReadbackRequirements" :key="item">{{ item }}</li>
              </ul>
            </el-card>
          </div>
        </section>

        <div class="toolbar-row" data-testid="stock-ledger-guarded-actions">
          <el-tag type="info" effect="plain" data-testid="stock-ledger-readonly-state">
            local-dev 测试写入入口已启用（scenario_tag + rollback + zero_residual）
          </el-tag>
          <el-button
            type="primary"
            :disabled="!canRead || localWriteLoading || stockLedgerWriteGuarded"
            data-write-guard="guarded:readonly-dev-only"
            data-testid="stock-ledger-local-draft-open-button"
            @click="onOpenLocalDraftGuarded"
          >
            保存草稿（本地）
          </el-button>
          <el-button
            :disabled="!canRead || !localDraft || localWriteLoading || stockLedgerWriteGuarded"
            data-write-guard="guarded:readonly-dev-only"
            data-testid="stock-ledger-local-draft-void-button"
            @click="onVoidLocalDraftGuarded"
          >
            回滚草稿
          </el-button>
          <el-button :disabled="!canRead" data-write-guard="true" @click="onGuardedAction('对账提示')">对账</el-button>
          <el-button :disabled="!canExport" data-write-guard="true" @click="onGuardedAction('导出台账')">导出</el-button>
          <el-button :disabled="!canExport" data-write-guard="true" @click="onGuardedAction('打印台账')">打印</el-button>
        </div>

        <el-form :inline="true" :model="localWriteForm" class="local-write-form" data-testid="stock-ledger-local-write-form">
          <el-form-item label="scenario_tag">
            <el-input
              v-model="localWriteForm.scenario_tag"
              :disabled="stockLedgerWriteGuarded"
              clearable
              placeholder="Z003-WAREHOUSE-YYYYMMDD-NNN"
              data-testid="stock-ledger-local-scenario-tag-input"
            />
          </el-form-item>
          <el-form-item label="来源仓">
            <el-input
              v-model="localWriteForm.source_warehouse"
              :disabled="stockLedgerWriteGuarded"
              clearable
              placeholder="样衣仓"
              data-testid="stock-ledger-local-company-input"
            />
          </el-form-item>
          <el-form-item label="目标仓">
            <el-input
              v-model="localWriteForm.target_warehouse"
              :disabled="stockLedgerWriteGuarded"
              clearable
              placeholder="成品仓"
              data-testid="stock-ledger-local-customer-input"
            />
          </el-form-item>
          <el-form-item label="款号">
            <el-input
              v-model="localWriteForm.item_code"
              :disabled="stockLedgerWriteGuarded"
              clearable
              placeholder="MAT-LOCAL-001"
              data-testid="stock-ledger-local-item-code-input"
            />
          </el-form-item>
          <el-form-item label="仓库">
            <el-input
              v-model="localWriteForm.warehouse"
              :disabled="stockLedgerWriteGuarded"
              clearable
              placeholder="样衣仓"
              data-testid="stock-ledger-local-warehouse-input"
            />
          </el-form-item>
          <el-form-item label="调拨数量">
            <el-input
              v-model="localWriteForm.qty"
              :disabled="stockLedgerWriteGuarded"
              clearable
              placeholder="1"
              data-testid="stock-ledger-local-qty-input"
            />
          </el-form-item>
        </el-form>

        <el-alert
          v-if="localWriteFeedback"
          class="error-alert"
          :type="localWriteFeedbackType"
          :closable="false"
          data-testid="stock-ledger-local-write-feedback"
          :title="localWriteFeedback"
        />

        <el-descriptions
          v-if="localDraft"
          border
          :column="2"
          size="small"
          class="local-draft-descriptions"
          data-testid="stock-ledger-local-draft-readback"
        >
          <el-descriptions-item label="草稿ID">{{ localDraft.id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ localDraft.status }}</el-descriptions-item>
          <el-descriptions-item label="草稿号">{{ localDraft.draft_no }}</el-descriptions-item>
          <el-descriptions-item label="业务引用">{{ localDraft.business_ref }}</el-descriptions-item>
          <el-descriptions-item label="scenario_tag">{{ localDraft.scenario_tag }}</el-descriptions-item>
          <el-descriptions-item label="操作类型">{{ localDraft.operation_type }}</el-descriptions-item>
          <el-descriptions-item label="物料">{{ localDraft.material_code }}</el-descriptions-item>
          <el-descriptions-item label="created_at">{{ localDraft.created_at }}</el-descriptions-item>
          <el-descriptions-item label="updated_at">{{ localDraft.updated_at }}</el-descriptions-item>
          <el-descriptions-item label="回读操作" :span="2">
            <el-button link type="primary" @click="refreshLocalInventoryReadback">刷新库存回读</el-button>
          </el-descriptions-item>
        </el-descriptions>
        <el-descriptions
          v-if="localInventoryReadback"
          border
          :column="2"
          size="small"
          class="local-draft-descriptions"
          data-testid="mvp-cand006-stock-readback-panel"
        >
          <el-descriptions-item label="库存草稿ID">{{ localInventoryReadback.draft_id }}</el-descriptions-item>
          <el-descriptions-item label="scenario_tag">{{ localInventoryReadback.scenario_tag }}</el-descriptions-item>
          <el-descriptions-item label="操作类型">{{ localInventoryReadback.operation_type }}</el-descriptions-item>
          <el-descriptions-item label="流水类型">{{ localInventoryReadback.flow_type }}</el-descriptions-item>
          <el-descriptions-item label="物料">{{ localInventoryReadback.material_code }}</el-descriptions-item>
          <el-descriptions-item label="仓库">{{ localInventoryReadback.warehouse }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ localInventoryReadback.state }}</el-descriptions-item>
          <el-descriptions-item label="回读操作" :span="2">
            <el-button link type="primary" @click="refreshLocalInventoryReadback">刷新库存回读</el-button>
          </el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-else-if="localInventoryReadbackMessage"
          class="scope-alert"
          type="info"
          :closable="false"
          :title="localInventoryReadbackMessage"
          data-testid="mvp-cand006-stock-readback-panel"
        />

        <el-alert
          v-if="requiredItemCodeGuarded"
          class="error-alert"
          type="warning"
          :closable="false"
          data-testid="stock-ledger-required-item-code-guard"
          title="请先输入款号后再查询库存台账"
        />

        <el-alert
          v-if="lastError"
          class="error-alert"
          type="error"
          :closable="false"
          data-testid="stock-ledger-error-state"
          :title="stockLedgerErrorTitle"
        />

        <el-empty
          v-if="!canRead && !isMaterialStockParity"
          data-testid="stock-ledger-permission-state"
          :description="stockLedgerPermissionDescription"
        />
        <template v-else>
          <el-alert
            v-if="!canRead && isMaterialStockParity"
            class="error-alert"
            type="warning"
            :closable="false"
            data-testid="stock-ledger-parity-readonly-shell-state"
            title="当前账号无物料库存读取权限，页面仅保留本地只读交互壳层用于验证。"
          />
          <div class="summary-row" data-testid="stock-ledger-summary-row">
            <el-tag type="info" effect="plain">台账记录：{{ total }}</el-tag>
            <el-tag type="primary" effect="plain" data-testid="stock-ledger-filtered-count">
              当前筛选结果：{{ stockLedgerFilteredRows.length }}
            </el-tag>
            <el-tag type="success" effect="plain">变动数量合计：{{ totalQty }}</el-tag>
            <el-tag type="warning" effect="plain">在库结存合计：{{ stockSummaryBalanceQty }}</el-tag>
            <el-tag type="primary" effect="plain" data-testid="stock-ledger-aggregation-count">
              聚合项：{{ inventoryAggregationTotal }}
            </el-tag>
            <el-tag type="danger" effect="plain" data-testid="stock-ledger-aggregation-below-safety">
              低于安全库存：{{ inventoryAggregationBelowSafety }}
            </el-tag>
            <el-tag v-if="stockSummaryDroppedCount > 0" type="danger" effect="plain">
              过滤丢弃：{{ stockSummaryDroppedCount }}
            </el-tag>
          </div>

          <el-table
            :data="stockLedgerFilteredRows"
            border
            v-loading="loading"
            data-testid="mvp-cand006-stock-flow-table"
            :empty-text="stockLedgerEmptyText"
          >
            <el-table-column prop="posting_date" label="过账日期" min-width="120" />
            <el-table-column prop="posting_time" label="过账时间" min-width="110" />
            <el-table-column prop="company" label="公司" min-width="140" />
            <el-table-column prop="item_code" label="款号" min-width="120" />
            <el-table-column prop="warehouse" label="仓库" min-width="130" />
            <el-table-column prop="voucher_type" label="凭证类型" min-width="120" />
            <el-table-column prop="voucher_no" label="凭证号" min-width="160" />
            <el-table-column label="状态" min-width="100">
              <template #default="scope">
                <el-tag :type="stockLedgerStatusTagType(scope.row)" effect="plain">
                  {{ stockLedgerStatusLabel(scope.row) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="变动数量" min-width="110">
              <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
            </el-table-column>
            <el-table-column label="结存数量" min-width="110">
              <template #default="scope">{{ formatAmount(scope.row.qty_after_transaction) }}</template>
            </el-table-column>
            <el-table-column label="操作" min-width="100" fixed="right">
              <template #default="scope">
                <el-button
                  link
                  type="primary"
                  data-testid="stock-ledger-row-detail-button"
                  @click="onOpenLedgerDetail(scope.row)"
                >
                  明细
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager" data-testid="stock-ledger-pagination">
            <el-pagination
              background
              layout="prev, pager, next, total, sizes"
              :current-page="query.page"
              :page-size="query.page_size"
              :total="total"
              :page-sizes="[10, 20, 50, 100]"
              :hide-on-single-page="!isMaterialStockParity"
              @current-change="onPageChange"
              @size-change="onSizeChange"
            />
          </div>
        </template>

        <el-drawer
          v-model="ledgerDetailVisible"
          title="库存台账明细"
          size="460px"
          append-to-body
          data-testid="stock-ledger-detail-drawer"
        >
          <template v-if="ledgerDetailRow">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="公司">{{ ledgerDetailRow.company }}</el-descriptions-item>
              <el-descriptions-item label="款号">{{ ledgerDetailRow.item_code }}</el-descriptions-item>
              <el-descriptions-item label="仓库">{{ ledgerDetailRow.warehouse }}</el-descriptions-item>
              <el-descriptions-item label="过账日期">{{ ledgerDetailRow.posting_date }}</el-descriptions-item>
              <el-descriptions-item label="过账时间">
                {{ ledgerDetailRow.posting_time || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="凭证类型">
                {{ ledgerDetailRow.voucher_type || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="凭证号">
                {{ ledgerDetailRow.voucher_no || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="变动数量">
                {{ formatAmount(ledgerDetailRow.actual_qty) }}
              </el-descriptions-item>
              <el-descriptions-item label="结存数量">
                {{ formatAmount(ledgerDetailRow.qty_after_transaction) }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
          <el-empty v-else description="暂无台账明细" />
        </el-drawer>
      </section>

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

        <el-divider />

        <section
          class="customer-return-application-section"
          data-testid="customer-return-application-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">客户退货申请</span>
              <span class="sub-title">TASK-Y54B-P1-01 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="customerReturnApplicationQuery" class="query-form">
            <el-form-item label="申请单号">
              <el-input
                v-model="customerReturnApplicationQuery.application_no"
                clearable
                placeholder="申请单号"
                @keyup.enter="onCustomerReturnApplicationSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="customerReturnApplicationQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onCustomerReturnApplicationSearch"
              />
            </el-form-item>
            <el-form-item label="退货仓库">
              <el-input
                v-model="customerReturnApplicationQuery.warehouse"
                clearable
                placeholder="退货仓库"
                @keyup.enter="onCustomerReturnApplicationSearch"
              />
            </el-form-item>
            <el-form-item label="申请状态">
              <el-select
                v-model="customerReturnApplicationQuery.application_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="已受理" value="已受理" />
                <el-option label="已确认" value="已确认" />
              </el-select>
            </el-form-item>
            <el-form-item label="复核状态">
              <el-select
                v-model="customerReturnApplicationQuery.approval_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待复核" value="待复核" />
                <el-option label="复核中" value="复核中" />
                <el-option label="已通过" value="已通过" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="customerReturnApplicationQuery.keyword"
                clearable
                placeholder="申请单号/成品/仓库/来源单号"
                @keyup.enter="onCustomerReturnApplicationSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="customerReturnApplicationQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="customerReturnApplicationQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onCustomerReturnApplicationReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onCustomerReturnApplicationSearch">
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('退货申请确认提示')"
            >
              退货申请确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('退货申请复核提示')"
            >
              退货申请复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('客户退货申请校验')"
            >
              校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出客户退货申请')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印客户退货申请')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="customerReturnApplicationError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`客户退货申请加载失败：${customerReturnApplicationError}`"
          />

          <el-empty v-if="!canRead" description="无客户退货申请查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">申请记录：{{ customerReturnApplicationTotal }}</el-tag>
              <el-tag type="success" effect="plain">
                申请退货总量：{{ customerReturnApplicationRequestedTotal }}
              </el-tag>
              <el-tag type="warning" effect="plain">
                复核通过总量：{{ customerReturnApplicationConfirmedTotal }}
              </el-tag>
              <el-tag type="danger" effect="plain">
                待处理总量：{{ customerReturnApplicationPendingTotal }}
              </el-tag>
            </div>

            <el-table
              :data="customerReturnApplicationRows"
              border
              v-loading="customerReturnApplicationLoading"
              empty-text="暂无客户退货申请数据，请调整筛选条件后重试"
            >
              <el-table-column prop="application_no" label="申请单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="退货仓库" min-width="120" />
              <el-table-column label="申请退货" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.requested_return_qty) }}</template>
              </el-table-column>
              <el-table-column label="复核通过" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.confirmed_return_qty) }}</template>
              </el-table-column>
              <el-table-column label="待处理" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.pending_return_qty) }}</template>
              </el-table-column>
              <el-table-column label="申请状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="customerReturnApplicationStatusType(scope.row.application_status)" effect="light">
                    {{ scope.row.application_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="customerReturnApprovalStatusType(scope.row.approval_status)" effect="light">
                    {{ scope.row.approval_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="application_date" label="申请日期" min-width="120" />
              <el-table-column prop="source_doc_no" label="来源单号" min-width="140" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看客户退货申请')"
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
                :current-page="customerReturnApplicationQuery.page"
                :page-size="customerReturnApplicationQuery.page_size"
                :total="customerReturnApplicationTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onCustomerReturnApplicationPageChange"
                @size-change="onCustomerReturnApplicationSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="customer-return-inbound-section"
          data-testid="customer-return-inbound-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">客户退货入仓</span>
              <span class="sub-title">TASK-Y54B-P1-02 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="customerReturnInboundQuery" class="query-form">
            <el-form-item label="入仓单号">
              <el-input
                v-model="customerReturnInboundQuery.inbound_no"
                clearable
                placeholder="入仓单号"
                @keyup.enter="onCustomerReturnInboundSearch"
              />
            </el-form-item>
            <el-form-item label="申请单号">
              <el-input
                v-model="customerReturnInboundQuery.application_no"
                clearable
                placeholder="申请单号"
                @keyup.enter="onCustomerReturnInboundSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="customerReturnInboundQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onCustomerReturnInboundSearch"
              />
            </el-form-item>
            <el-form-item label="入仓仓库">
              <el-input
                v-model="customerReturnInboundQuery.warehouse"
                clearable
                placeholder="入仓仓库"
                @keyup.enter="onCustomerReturnInboundSearch"
              />
            </el-form-item>
            <el-form-item label="入仓状态">
              <el-select
                v-model="customerReturnInboundQuery.inbound_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="待入仓" value="待入仓" />
                <el-option label="入仓中" value="入仓中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="复核状态">
              <el-select
                v-model="customerReturnInboundQuery.review_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待复核" value="待复核" />
                <el-option label="复核中" value="复核中" />
                <el-option label="已通过" value="已通过" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="customerReturnInboundQuery.keyword"
                clearable
                placeholder="入仓单号/申请单号/成品/仓库"
                @keyup.enter="onCustomerReturnInboundSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="customerReturnInboundQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="customerReturnInboundQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onCustomerReturnInboundReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onCustomerReturnInboundSearch">查询</el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('退货入仓确认提示')"
            >
              退货入仓确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('退货入仓复核提示')"
            >
              退货入仓复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('客户退货入仓校验')"
            >
              校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出客户退货入仓')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印客户退货入仓')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="customerReturnInboundError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`客户退货入仓加载失败：${customerReturnInboundError}`"
          />

          <el-empty v-if="!canRead" description="无客户退货入仓查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">入仓记录：{{ customerReturnInboundTotal }}</el-tag>
              <el-tag type="success" effect="plain">
                计划入仓总量：{{ customerReturnInboundPlannedTotal }}
              </el-tag>
              <el-tag type="warning" effect="plain">
                已入仓总量：{{ customerReturnInboundActualTotal }}
              </el-tag>
              <el-tag type="danger" effect="plain">
                待入仓总量：{{ customerReturnInboundPendingTotal }}
              </el-tag>
            </div>

            <el-table
              :data="customerReturnInboundRows"
              border
              v-loading="customerReturnInboundLoading"
              empty-text="暂无客户退货入仓数据，请调整筛选条件后重试"
            >
              <el-table-column prop="inbound_no" label="入仓单号" min-width="150" />
              <el-table-column prop="application_no" label="申请单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="入仓仓库" min-width="120" />
              <el-table-column label="计划入仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.planned_inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="已入仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.actual_inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="待入仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.pending_inbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="入仓状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="customerReturnInboundStatusType(scope.row.inbound_status)" effect="light">
                    {{ scope.row.inbound_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="customerReturnInboundReviewStatusType(scope.row.review_status)" effect="light">
                    {{ scope.row.review_status }}
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
                    @click="onGuardedAction('查看客户退货入仓')"
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
                :current-page="customerReturnInboundQuery.page"
                :page-size="customerReturnInboundQuery.page_size"
                :total="customerReturnInboundTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onCustomerReturnInboundPageChange"
                @size-change="onCustomerReturnInboundSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="finished-goods-other-outbound-section"
          data-testid="finished-goods-other-outbound-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">成品其他出仓</span>
              <span class="sub-title">TASK-Y54B-P1-03 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="finishedGoodsOtherOutboundQuery" class="query-form">
            <el-form-item label="出仓单号">
              <el-input
                v-model="finishedGoodsOtherOutboundQuery.outbound_no"
                clearable
                placeholder="出仓单号"
                @keyup.enter="onFinishedGoodsOtherOutboundSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="finishedGoodsOtherOutboundQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onFinishedGoodsOtherOutboundSearch"
              />
            </el-form-item>
            <el-form-item label="出仓仓库">
              <el-input
                v-model="finishedGoodsOtherOutboundQuery.warehouse"
                clearable
                placeholder="出仓仓库"
                @keyup.enter="onFinishedGoodsOtherOutboundSearch"
              />
            </el-form-item>
            <el-form-item label="出仓状态">
              <el-select
                v-model="finishedGoodsOtherOutboundQuery.outbound_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="待出仓" value="待出仓" />
                <el-option label="出仓中" value="出仓中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="复核状态">
              <el-select
                v-model="finishedGoodsOtherOutboundQuery.review_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待复核" value="待复核" />
                <el-option label="复核中" value="复核中" />
                <el-option label="已通过" value="已通过" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="finishedGoodsOtherOutboundQuery.keyword"
                clearable
                placeholder="出仓单号/成品/仓库/来源单号"
                @keyup.enter="onFinishedGoodsOtherOutboundSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="finishedGoodsOtherOutboundQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="finishedGoodsOtherOutboundQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onFinishedGoodsOtherOutboundReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onFinishedGoodsOtherOutboundSearch">
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品其他出仓确认提示')"
            >
              成品其他出仓确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品其他出仓复核提示')"
            >
              成品其他出仓复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品其他出仓校验')"
            >
              校验
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出成品其他出仓')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印成品其他出仓')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="finishedGoodsOtherOutboundError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成品其他出仓加载失败：${finishedGoodsOtherOutboundError}`"
          />

          <el-empty v-if="!canRead" description="无成品其他出仓查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">出仓记录：{{ finishedGoodsOtherOutboundTotal }}</el-tag>
              <el-tag type="success" effect="plain">
                计划出仓总量：{{ finishedGoodsOtherOutboundPlannedTotal }}
              </el-tag>
              <el-tag type="warning" effect="plain">
                已出仓总量：{{ finishedGoodsOtherOutboundActualTotal }}
              </el-tag>
              <el-tag type="danger" effect="plain">
                待出仓总量：{{ finishedGoodsOtherOutboundPendingTotal }}
              </el-tag>
            </div>

            <el-table
              :data="finishedGoodsOtherOutboundRows"
              border
              v-loading="finishedGoodsOtherOutboundLoading"
              empty-text="暂无成品其他出仓数据，请调整筛选条件后重试"
            >
              <el-table-column prop="outbound_no" label="出仓单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="出仓仓库" min-width="120" />
              <el-table-column label="计划出仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.planned_outbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="已出仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.actual_outbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="待出仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.pending_outbound_qty) }}</template>
              </el-table-column>
              <el-table-column label="出仓状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsOtherOutboundStatusType(scope.row.outbound_status)" effect="light">
                    {{ scope.row.outbound_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsOtherOutboundReviewStatusType(scope.row.review_status)" effect="light">
                    {{ scope.row.review_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="outbound_date" label="出仓日期" min-width="120" />
              <el-table-column prop="source_doc_no" label="来源单号" min-width="140" />
              <el-table-column prop="owner" label="经办人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看成品其他出仓')"
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
                :current-page="finishedGoodsOtherOutboundQuery.page"
                :page-size="finishedGoodsOtherOutboundQuery.page_size"
                :total="finishedGoodsOtherOutboundTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onFinishedGoodsOtherOutboundPageChange"
                @size-change="onFinishedGoodsOtherOutboundSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section class="finished-goods-count-section" data-testid="finished-goods-count-section">
          <div class="section-header">
            <div class="title-group">
              <span class="title">成品盘点</span>
              <span class="sub-title">TASK-Y54B-P1-04 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="finishedGoodsCountQuery" class="query-form">
            <el-form-item label="盘点单号">
              <el-input
                v-model="finishedGoodsCountQuery.count_no"
                clearable
                placeholder="盘点单号"
                @keyup.enter="onFinishedGoodsCountSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="finishedGoodsCountQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onFinishedGoodsCountSearch"
              />
            </el-form-item>
            <el-form-item label="盘点仓库">
              <el-input
                v-model="finishedGoodsCountQuery.warehouse"
                clearable
                placeholder="盘点仓库"
                @keyup.enter="onFinishedGoodsCountSearch"
              />
            </el-form-item>
            <el-form-item label="盘点状态">
              <el-select
                v-model="finishedGoodsCountQuery.count_status"
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
                v-model="finishedGoodsCountQuery.review_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待复核" value="待复核" />
                <el-option label="复核中" value="复核中" />
                <el-option label="已通过" value="已通过" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="finishedGoodsCountQuery.keyword"
                clearable
                placeholder="盘点单号/成品/仓库/盘点人"
                @keyup.enter="onFinishedGoodsCountSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="finishedGoodsCountQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="finishedGoodsCountQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onFinishedGoodsCountReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onFinishedGoodsCountSearch">
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品盘点确认提示')"
            >
              盘点确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品盘点复核提示')"
            >
              复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品盘点差异处理提示')"
            >
              差异处理提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出成品盘点')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印成品盘点')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="finishedGoodsCountError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成品盘点加载失败：${finishedGoodsCountError}`"
          />

          <el-empty v-if="!canRead" description="无成品盘点查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">盘点记录：{{ finishedGoodsCountTotal }}</el-tag>
              <el-tag type="success" effect="plain">账面总量：{{ finishedGoodsCountBookTotal }}</el-tag>
              <el-tag type="warning" effect="plain">差异总量：{{ finishedGoodsCountDiffTotal }}</el-tag>
            </div>

            <el-table
              :data="finishedGoodsCountRows"
              border
              v-loading="finishedGoodsCountLoading"
              empty-text="暂无成品盘点数据，请调整筛选条件后重试"
            >
              <el-table-column prop="count_no" label="盘点单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="盘点仓库" min-width="120" />
              <el-table-column label="账面数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.book_qty) }}</template>
              </el-table-column>
              <el-table-column label="实盘数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.counted_qty) }}</template>
              </el-table-column>
              <el-table-column label="差异数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.diff_qty) }}</template>
              </el-table-column>
              <el-table-column label="盘点状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsCountStatusType(scope.row.count_status)" effect="light">
                    {{ scope.row.count_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsCountReviewStatusType(scope.row.review_status)" effect="light">
                    {{ scope.row.review_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="count_date" label="盘点日期" min-width="120" />
              <el-table-column prop="owner" label="盘点人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看成品盘点')"
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
                :current-page="finishedGoodsCountQuery.page"
                :page-size="finishedGoodsCountQuery.page_size"
                :total="finishedGoodsCountTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onFinishedGoodsCountPageChange"
                @size-change="onFinishedGoodsCountSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="finished-goods-adjustment-section"
          data-testid="finished-goods-adjustment-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">成品调整</span>
              <span class="sub-title">TASK-Y54B-P1-05 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="finishedGoodsAdjustmentQuery" class="query-form">
            <el-form-item label="调整单号">
              <el-input
                v-model="finishedGoodsAdjustmentQuery.adjustment_no"
                clearable
                placeholder="调整单号"
                @keyup.enter="onFinishedGoodsAdjustmentSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="finishedGoodsAdjustmentQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onFinishedGoodsAdjustmentSearch"
              />
            </el-form-item>
            <el-form-item label="调整仓库">
              <el-input
                v-model="finishedGoodsAdjustmentQuery.warehouse"
                clearable
                placeholder="调整仓库"
                @keyup.enter="onFinishedGoodsAdjustmentSearch"
              />
            </el-form-item>
            <el-form-item label="调整状态">
              <el-select
                v-model="finishedGoodsAdjustmentQuery.adjustment_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="待确认" value="待确认" />
                <el-option label="调整中" value="调整中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="复核状态">
              <el-select
                v-model="finishedGoodsAdjustmentQuery.review_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待复核" value="待复核" />
                <el-option label="复核中" value="复核中" />
                <el-option label="已通过" value="已通过" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="finishedGoodsAdjustmentQuery.keyword"
                clearable
                placeholder="调整单号/成品/仓库/调整人"
                @keyup.enter="onFinishedGoodsAdjustmentSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="finishedGoodsAdjustmentQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="finishedGoodsAdjustmentQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onFinishedGoodsAdjustmentReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onFinishedGoodsAdjustmentSearch">
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品调整确认提示')"
            >
              调整确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品调整复核提示')"
            >
              复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品调整差异处理提示')"
            >
              差异处理提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出成品调整')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印成品调整')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="finishedGoodsAdjustmentError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成品调整加载失败：${finishedGoodsAdjustmentError}`"
          />

          <el-empty v-if="!canRead" description="无成品调整查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">调整记录：{{ finishedGoodsAdjustmentTotal }}</el-tag>
              <el-tag type="success" effect="plain">账面总量：{{ finishedGoodsAdjustmentBeforeTotal }}</el-tag>
              <el-tag type="warning" effect="plain">差异总量：{{ finishedGoodsAdjustmentDiffTotal }}</el-tag>
            </div>

            <el-table
              :data="finishedGoodsAdjustmentRows"
              border
              v-loading="finishedGoodsAdjustmentLoading"
              empty-text="暂无成品调整数据，请调整筛选条件后重试"
            >
              <el-table-column prop="adjustment_no" label="调整单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="warehouse" label="调整仓库" min-width="120" />
              <el-table-column label="调整前数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.before_qty) }}</template>
              </el-table-column>
              <el-table-column label="调整后数量" min-width="110">
                <template #default="scope">{{ formatAmount(scope.row.adjusted_qty) }}</template>
              </el-table-column>
              <el-table-column label="差异数量" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.diff_qty) }}</template>
              </el-table-column>
              <el-table-column label="调整状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsAdjustmentStatusType(scope.row.adjustment_status)" effect="light">
                    {{ scope.row.adjustment_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsAdjustmentReviewStatusType(scope.row.review_status)" effect="light">
                    {{ scope.row.review_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="adjustment_date" label="调整日期" min-width="120" />
              <el-table-column prop="adjust_reason" label="调整原因" min-width="140" />
              <el-table-column prop="owner" label="调整人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看成品调整')"
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
                :current-page="finishedGoodsAdjustmentQuery.page"
                :page-size="finishedGoodsAdjustmentQuery.page_size"
                :total="finishedGoodsAdjustmentTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onFinishedGoodsAdjustmentPageChange"
                @size-change="onFinishedGoodsAdjustmentSizeChange"
              />
            </div>
          </template>
        </section>

        <el-divider />

        <section
          class="finished-goods-transfer-section"
          data-testid="finished-goods-transfer-section"
        >
          <div class="section-header">
            <div class="title-group">
              <span class="title">成品调仓</span>
              <span class="sub-title">TASK-Y59B-P1-01 / 只读语义</span>
            </div>
            <el-tag type="danger" effect="plain">共享路由高风险增量区块</el-tag>
          </div>

          <el-form :inline="true" :model="finishedGoodsTransferQuery" class="query-form">
            <el-form-item label="调仓单号">
              <el-input
                v-model="finishedGoodsTransferQuery.transfer_no"
                clearable
                placeholder="调仓单号"
                @keyup.enter="onFinishedGoodsTransferSearch"
              />
            </el-form-item>
            <el-form-item label="成品编码">
              <el-input
                v-model="finishedGoodsTransferQuery.item_code"
                clearable
                placeholder="成品编码"
                @keyup.enter="onFinishedGoodsTransferSearch"
              />
            </el-form-item>
            <el-form-item label="调出仓库">
              <el-input
                v-model="finishedGoodsTransferQuery.source_warehouse"
                clearable
                placeholder="调出仓库"
                @keyup.enter="onFinishedGoodsTransferSearch"
              />
            </el-form-item>
            <el-form-item label="调入仓库">
              <el-input
                v-model="finishedGoodsTransferQuery.target_warehouse"
                clearable
                placeholder="调入仓库"
                @keyup.enter="onFinishedGoodsTransferSearch"
              />
            </el-form-item>
            <el-form-item label="调仓状态">
              <el-select
                v-model="finishedGoodsTransferQuery.transfer_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="草稿" value="草稿" />
                <el-option label="待确认" value="待确认" />
                <el-option label="调仓中" value="调仓中" />
                <el-option label="已完成" value="已完成" />
              </el-select>
            </el-form-item>
            <el-form-item label="复核状态">
              <el-select
                v-model="finishedGoodsTransferQuery.review_status"
                clearable
                placeholder="全部状态"
                style="width: 140px"
              >
                <el-option label="未开始" value="未开始" />
                <el-option label="待复核" value="待复核" />
                <el-option label="复核中" value="复核中" />
                <el-option label="已通过" value="已通过" />
              </el-select>
            </el-form-item>
            <el-form-item label="关键词">
              <el-input
                v-model="finishedGoodsTransferQuery.keyword"
                clearable
                placeholder="调仓单号/成品/仓库/调仓人"
                @keyup.enter="onFinishedGoodsTransferSearch"
              />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker
                v-model="finishedGoodsTransferQuery.from_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="开始日期"
                clearable
              />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker
                v-model="finishedGoodsTransferQuery.to_date"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="结束日期"
                clearable
              />
            </el-form-item>
            <el-form-item>
              <el-button :disabled="!canRead" @click="onFinishedGoodsTransferReset">重置</el-button>
              <el-button type="primary" :disabled="!canRead" @click="onFinishedGoodsTransferSearch">
                查询
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row">
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品调仓确认提示')"
            >
              调仓确认提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品调仓复核提示')"
            >
              复核提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canRead"
              @click="onGuardedAction('成品调仓差异处理提示')"
            >
              差异处理提示
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('导出成品调仓')"
            >
              导出
            </el-button>
            <el-button
              data-write-guard="true"
              :disabled="!canExport"
              @click="onGuardedAction('打印成品调仓')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="finishedGoodsTransferError"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`成品调仓加载失败：${finishedGoodsTransferError}`"
          />

          <el-empty v-if="!canRead" description="无成品调仓查看权限" />
          <template v-else>
            <div class="summary-row">
              <el-tag type="info" effect="plain">调仓记录：{{ finishedGoodsTransferTotal }}</el-tag>
              <el-tag type="success" effect="plain">计划调仓总量：{{ finishedGoodsTransferPlannedTotal }}</el-tag>
              <el-tag type="warning" effect="plain">已调仓总量：{{ finishedGoodsTransferActualTotal }}</el-tag>
              <el-tag type="danger" effect="plain">待调仓总量：{{ finishedGoodsTransferPendingTotal }}</el-tag>
            </div>

            <el-table
              :data="finishedGoodsTransferRows"
              border
              v-loading="finishedGoodsTransferLoading"
              empty-text="暂无成品调仓数据，请调整筛选条件后重试"
            >
              <el-table-column prop="transfer_no" label="调仓单号" min-width="150" />
              <el-table-column prop="item_code" label="成品编码" min-width="130" />
              <el-table-column prop="item_name" label="成品名称" min-width="150" />
              <el-table-column prop="source_warehouse" label="调出仓库" min-width="120" />
              <el-table-column prop="target_warehouse" label="调入仓库" min-width="120" />
              <el-table-column label="计划调仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.planned_transfer_qty) }}</template>
              </el-table-column>
              <el-table-column label="已调仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.actual_transfer_qty) }}</template>
              </el-table-column>
              <el-table-column label="待调仓" min-width="100">
                <template #default="scope">{{ formatAmount(scope.row.pending_transfer_qty) }}</template>
              </el-table-column>
              <el-table-column label="调仓状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsTransferStatusType(scope.row.transfer_status)" effect="light">
                    {{ scope.row.transfer_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="复核状态" min-width="100">
                <template #default="scope">
                  <el-tag :type="finishedGoodsTransferReviewStatusType(scope.row.review_status)" effect="light">
                    {{ scope.row.review_status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="transfer_date" label="调仓日期" min-width="120" />
              <el-table-column prop="transfer_reason" label="调仓原因" min-width="140" />
              <el-table-column prop="owner" label="调仓人" min-width="100" />
              <el-table-column prop="ref_no" label="关联单据" min-width="140" />
              <el-table-column label="操作" min-width="110" fixed="right">
                <template #default>
                  <el-button
                    data-write-guard="true"
                    link
                    type="primary"
                    @click="onGuardedAction('查看成品调仓')"
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
                :current-page="finishedGoodsTransferQuery.page"
                :page-size="finishedGoodsTransferQuery.page_size"
                :total="finishedGoodsTransferTotal"
                :page-sizes="[10, 20, 50, 100]"
                @current-change="onFinishedGoodsTransferPageChange"
                @size-change="onFinishedGoodsTransferSizeChange"
              />
            </div>
          </template>
        </section>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventoryCustomerReturnInbound,
  fetchSalesInventoryCustomerReturnApplications,
  fetchSalesInventoryFinishedGoodsAdjustment,
  fetchSalesInventoryFinishedGoodsTransfer,
  fetchSalesInventoryFinishedGoodsCount,
  fetchSalesInventoryFinishedGoodsOtherOutbound,
  fetchSalesInventoryFinishedGoodsOtherInbound,
  fetchSalesInventoryFinishedGoodsReservedInbound,
  fetchSalesInventoryFinishedGoodsShippingNotices,
  fetchSalesInventoryAggregation,
  fetchSalesInventoryInventoryMaterialRetentionReport,
  fetchSalesInventoryMaterialCounts,
  fetchSalesInventoryMaterialInventoryReport,
  fetchSalesInventoryMaterialTransfers,
  fetchSalesInventorySemiFinishedInventory,
  fetchSalesInventoryStockLedger,
  fetchSalesInventoryStockSummary,
  type CustomerReturnInboundItem,
  type CustomerReturnApplicationItem,
  type FinishedGoodsAdjustmentItem,
  type FinishedGoodsTransferItem,
  type FinishedGoodsCountItem,
  type FinishedGoodsOtherOutboundItem,
  type FinishedGoodsOtherInboundItem,
  type FinishedGoodsReservedInboundItem,
  type FinishedGoodsShippingNoticeItem,
  type SalesInventoryAggregationItem,
  type InventoryMaterialRetentionReportItem,
  type MaterialCountItem,
  type MaterialInventoryReportItem,
  type MaterialTransferItem,
  type SemiFinishedInventoryItem,
  type StockLedgerItem,
  type StockSummaryItem,
} from '@/api/sales_inventory'
import { request, type ApiResponse } from '@/api/request'
import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const route = useRoute()
const loading = ref<boolean>(false)
const rows = ref<StockLedgerItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')
const requiredItemCodeGuarded = ref<boolean>(false)
const stockSummaryRows = ref<StockSummaryItem[]>([])
const stockSummaryDroppedCount = ref<number>(0)
const inventoryAggregationRows = ref<SalesInventoryAggregationItem[]>([])
const ledgerDetailVisible = ref<boolean>(false)
const ledgerDetailRow = ref<StockLedgerItem | null>(null)
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
const customerReturnApplicationLoading = ref<boolean>(false)
const customerReturnApplicationRows = ref<CustomerReturnApplicationItem[]>([])
const customerReturnApplicationTotal = ref<number>(0)
const customerReturnApplicationError = ref<string>('')
const customerReturnInboundLoading = ref<boolean>(false)
const customerReturnInboundRows = ref<CustomerReturnInboundItem[]>([])
const customerReturnInboundTotal = ref<number>(0)
const customerReturnInboundError = ref<string>('')
const finishedGoodsOtherOutboundLoading = ref<boolean>(false)
const finishedGoodsOtherOutboundRows = ref<FinishedGoodsOtherOutboundItem[]>([])
const finishedGoodsOtherOutboundTotal = ref<number>(0)
const finishedGoodsOtherOutboundError = ref<string>('')
const finishedGoodsCountLoading = ref<boolean>(false)
const finishedGoodsCountRows = ref<FinishedGoodsCountItem[]>([])
const finishedGoodsCountTotal = ref<number>(0)
const finishedGoodsCountError = ref<string>('')
const finishedGoodsAdjustmentLoading = ref<boolean>(false)
const finishedGoodsAdjustmentRows = ref<FinishedGoodsAdjustmentItem[]>([])
const finishedGoodsAdjustmentTotal = ref<number>(0)
const finishedGoodsAdjustmentError = ref<string>('')
const finishedGoodsTransferLoading = ref<boolean>(false)
const finishedGoodsTransferRows = ref<FinishedGoodsTransferItem[]>([])
const finishedGoodsTransferTotal = ref<number>(0)
const finishedGoodsTransferError = ref<string>('')
type LocalInventoryReadback = {
  id: number
  draft_id: number
  draft_no?: string
  scenario_tag: string
  operation_type: 'transfer' | 'counting'
  flow_type: 'transfer' | 'counting'
  material_code: string
  business_ref: string
  operation_qty: number
  source_warehouse: string
  target_warehouse: string
  warehouse: string
  state: string
  status: string
  created_at: string
  updated_at: string
}
const localInventoryReadback = ref<LocalInventoryReadback | null>(null)
const localInventoryReadbackMessage = ref<string>('未检测到库存草稿回读数据')

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

const stockLedgerParity = computed<string>(() => {
  return typeof route.query.parity === 'string' ? route.query.parity.trim() : ''
})

const isMaterialStockParity = computed<boolean>(() => stockLedgerParity.value === 'material-stock')
const stockLedgerReadbackOnly = computed<boolean>(() => false)
const stockLedgerWriteGuarded = computed<boolean>(() => stockLedgerReadbackOnly.value)
const contractCoveredIds: string[] = ['A001', 'A002', 'A003']
const contractSourceFiles: string[] = [
  '04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A001_evidence_coverage_matrix_20260520/evidence_coverage_matrix.json',
  '04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A002_business_contract_merge_20260520/yisuan_development_contract_input.json',
  '04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A003_ui_route_field_button_readonly_contract_20260520/ui_contract_development_input.json',
]
const contractFieldRuleReadback: string[] = [
  'key_fields: 库存流水主字段、仓库摘要、状态标签与跨模块回读提示',
  'validation_rules: can_support_development=true 仅代表开发输入，不代表真实动作已验证',
  'validation_rules: unknown/blocked/partial 必须 preserved，不得升级 confirmed',
  'status_rules: VERIFIED / PARTIAL / UNKNOWN / NO-GO / BLOCKED',
]
const contractReadonlyReadbackRequirements: string[] = [
  'readonly/readback: disabled_only/readback_only 只允许壳层表达',
  'readonly/readback: 不创建真实业务对象，不启用联动计算',
  'readonly/readback: contract source readback present=true',
  'readonly/readback: not_claimed_as_business_action=true',
]

const stockLedgerTitle = computed<string>(() => {
  return isMaterialStockParity.value ? '物料库存台账' : '库存台账'
})

const stockLedgerSubTitle = computed<string>(() => {
  return isMaterialStockParity.value
    ? '衣算云 / 物料进销存 / 物料库存（local-dev 本地闭环）'
    : '库存流水 / 仓库本地真实对象闭环（local-dev/sqlite/test_data）'
})

const stockLedgerErrorTitle = computed<string>(() => {
  if (!lastError.value) {
    return ''
  }
  return isMaterialStockParity.value ? `物料库存加载失败：${lastError.value}` : `库存台账加载失败：${lastError.value}`
})

const stockLedgerEmptyText = computed<string>(() => {
  return isMaterialStockParity.value
    ? '暂无物料库存台账数据，请调整筛选条件后重试'
    : '暂无库存台账数据，请调整筛选条件后重试'
})

const stockLedgerPermissionDescription = computed<string>(() => {
  return isMaterialStockParity.value ? '无物料库存台账查看权限' : '无库存台账查看权限'
})

const stockLedgerStatusLabel = (row: StockLedgerItem): '缺货' | '低库存' | '正常' => {
  const balanceQty = Number(row.qty_after_transaction ?? 0)
  if (balanceQty <= 0) {
    return '缺货'
  }
  if (balanceQty < 20) {
    return '低库存'
  }
  return '正常'
}

const stockLedgerStatusTagType = (row: StockLedgerItem): 'danger' | 'warning' | 'success' => {
  const status = stockLedgerStatusLabel(row)
  if (status === '缺货') {
    return 'danger'
  }
  if (status === '低库存') {
    return 'warning'
  }
  return 'success'
}

const localWriteLoading = ref<boolean>(false)
const localWriteFeedback = ref<string>('')
const localWriteFeedbackType = ref<'success' | 'warning' | 'error'>('success')
const localDraft = ref<LocalInventoryReadback | null>(null)

function buildDefaultWarehouseScenarioTag(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `Z003-WAREHOUSE-${y}${m}${d}-001`
}

function extractWarehouseScenarioTag(value: string): string | null {
  const matched = value.match(/^(Z003-WAREHOUSE-\d{8}-\d{3})$/)
  return matched?.[1] || null
}

const localWriteForm = reactive({
  scenario_tag: buildDefaultWarehouseScenarioTag(),
  source_warehouse: '样衣仓',
  target_warehouse: '成品仓',
  item_code: 'MAT-LOCAL-001',
  warehouse: '样衣仓',
  qty: '2',
})

const totalQty = computed<string>(() => {
  const qty = rows.value.reduce((sum, row) => {
    const current = Number(row.actual_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const stockSummaryBalanceQty = computed<string>(() => {
  const qty = stockSummaryRows.value.reduce((sum, row) => {
    const current = Number(row.balance_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const inventoryAggregationTotal = computed<number>(() => inventoryAggregationRows.value.length)

const inventoryAggregationBelowSafety = computed<number>(() => {
  return inventoryAggregationRows.value.filter((row) => row.is_below_safety).length
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

const customerReturnApplicationRequestedTotal = computed<string>(() => {
  const qty = customerReturnApplicationRows.value.reduce((sum, row) => {
    const current = Number(row.requested_return_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const customerReturnApplicationConfirmedTotal = computed<string>(() => {
  const qty = customerReturnApplicationRows.value.reduce((sum, row) => {
    const current = Number(row.confirmed_return_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const customerReturnApplicationPendingTotal = computed<string>(() => {
  const qty = customerReturnApplicationRows.value.reduce((sum, row) => {
    const current = Number(row.pending_return_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const customerReturnInboundPlannedTotal = computed<string>(() => {
  const qty = customerReturnInboundRows.value.reduce((sum, row) => {
    const current = Number(row.planned_inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const customerReturnInboundActualTotal = computed<string>(() => {
  const qty = customerReturnInboundRows.value.reduce((sum, row) => {
    const current = Number(row.actual_inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const customerReturnInboundPendingTotal = computed<string>(() => {
  const qty = customerReturnInboundRows.value.reduce((sum, row) => {
    const current = Number(row.pending_inbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsOtherOutboundPlannedTotal = computed<string>(() => {
  const qty = finishedGoodsOtherOutboundRows.value.reduce((sum, row) => {
    const current = Number(row.planned_outbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsOtherOutboundActualTotal = computed<string>(() => {
  const qty = finishedGoodsOtherOutboundRows.value.reduce((sum, row) => {
    const current = Number(row.actual_outbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsOtherOutboundPendingTotal = computed<string>(() => {
  const qty = finishedGoodsOtherOutboundRows.value.reduce((sum, row) => {
    const current = Number(row.pending_outbound_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsCountBookTotal = computed<string>(() => {
  const qty = finishedGoodsCountRows.value.reduce((sum, row) => {
    const current = Number(row.book_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsCountDiffTotal = computed<string>(() => {
  const qty = finishedGoodsCountRows.value.reduce((sum, row) => {
    const current = Number(row.diff_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsAdjustmentBeforeTotal = computed<string>(() => {
  const qty = finishedGoodsAdjustmentRows.value.reduce((sum, row) => {
    const current = Number(row.before_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsAdjustmentDiffTotal = computed<string>(() => {
  const qty = finishedGoodsAdjustmentRows.value.reduce((sum, row) => {
    const current = Number(row.diff_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsTransferPlannedTotal = computed<string>(() => {
  const qty = finishedGoodsTransferRows.value.reduce((sum, row) => {
    const current = Number(row.planned_transfer_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsTransferActualTotal = computed<string>(() => {
  const qty = finishedGoodsTransferRows.value.reduce((sum, row) => {
    const current = Number(row.actual_transfer_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const finishedGoodsTransferPendingTotal = computed<string>(() => {
  const qty = finishedGoodsTransferRows.value.reduce((sum, row) => {
    const current = Number(row.pending_transfer_qty ?? 0)
    return Number.isFinite(current) ? sum + current : sum
  }, 0)
  return qty.toFixed(2)
})

const query = reactive({
  item_code: '',
  company: '',
  warehouse: '',
  keyword: '',
  status: '',
  flow_type: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const applyRoutePrefill = (): void => {
  const itemCode = typeof route.query.item_code === 'string' ? route.query.item_code.trim() : ''
  const company = typeof route.query.company === 'string' ? route.query.company.trim() : ''
  const warehouse = typeof route.query.warehouse === 'string' ? route.query.warehouse.trim() : ''
  const keyword = typeof route.query.keyword === 'string' ? route.query.keyword.trim() : ''
  const status = typeof route.query.status === 'string' ? route.query.status.trim() : ''
  const flowType = typeof route.query.flow_type === 'string' ? route.query.flow_type.trim() : ''
  if (itemCode) {
    query.item_code = itemCode
  }
  if (company) {
    query.company = company
  }
  if (warehouse) {
    query.warehouse = warehouse
  }
  if (keyword) {
    query.keyword = keyword
  }
  if (status) {
    query.status = status
  }
  if (flowType) {
    query.flow_type = flowType
  }
}

const stockLedgerFilteredRows = computed<StockLedgerItem[]>(() => {
  const keyword = query.keyword.trim().toLowerCase()
  const status = query.status.trim()
  const flowType = query.flow_type.trim().toLowerCase()
  return rows.value.filter((row) => {
    if (status && stockLedgerStatusLabel(row) !== status) {
      return false
    }
    if (flowType) {
      const voucherType = String(row.voucher_type || '').toLowerCase()
      if (!voucherType.includes(flowType)) {
        return false
      }
    }
    if (!keyword) {
      return true
    }
    const searchable = [row.item_code, row.company, row.warehouse, row.voucher_no, row.voucher_type]
      .map((value) => String(value || '').toLowerCase())
      .join(' ')
    return searchable.includes(keyword)
  })
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

const customerReturnApplicationQuery = reactive({
  application_no: '',
  item_code: '',
  warehouse: '',
  application_status: '',
  approval_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const customerReturnInboundQuery = reactive({
  inbound_no: '',
  application_no: '',
  item_code: '',
  warehouse: '',
  inbound_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const finishedGoodsOtherOutboundQuery = reactive({
  outbound_no: '',
  item_code: '',
  warehouse: '',
  outbound_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const finishedGoodsCountQuery = reactive({
  count_no: '',
  item_code: '',
  warehouse: '',
  count_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const finishedGoodsAdjustmentQuery = reactive({
  adjustment_no: '',
  item_code: '',
  warehouse: '',
  adjustment_status: '',
  review_status: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const finishedGoodsTransferQuery = reactive({
  transfer_no: '',
  item_code: '',
  source_warehouse: '',
  target_warehouse: '',
  transfer_status: '',
  review_status: '',
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
  stockSummaryRows.value = []
  stockSummaryDroppedCount.value = 0
  inventoryAggregationRows.value = []
  ledgerDetailVisible.value = false
  ledgerDetailRow.value = null
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

const resetCustomerReturnApplicationRows = (): void => {
  customerReturnApplicationRows.value = []
  customerReturnApplicationTotal.value = 0
}

const resetCustomerReturnInboundRows = (): void => {
  customerReturnInboundRows.value = []
  customerReturnInboundTotal.value = 0
}

const resetFinishedGoodsOtherOutboundRows = (): void => {
  finishedGoodsOtherOutboundRows.value = []
  finishedGoodsOtherOutboundTotal.value = 0
}

const resetFinishedGoodsCountRows = (): void => {
  finishedGoodsCountRows.value = []
  finishedGoodsCountTotal.value = 0
}

const resetFinishedGoodsAdjustmentRows = (): void => {
  finishedGoodsAdjustmentRows.value = []
  finishedGoodsAdjustmentTotal.value = 0
}

const resetFinishedGoodsTransferRows = (): void => {
  finishedGoodsTransferRows.value = []
  finishedGoodsTransferTotal.value = 0
}

const loadRows = async ({ silentGuard = false }: { silentGuard?: boolean } = {}): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    requiredItemCodeGuarded.value = false
    lastError.value = ''
    return
  }
  const itemCode = query.item_code.trim()
  if (!itemCode) {
    resetRows()
    lastError.value = ''
    requiredItemCodeGuarded.value = true
    if (!silentGuard) {
      ElMessage.warning('请先输入款号后再查询库存台账')
    }
    return
  }

  requiredItemCodeGuarded.value = false
  loading.value = true
  lastError.value = ''
  try {
    const [summaryResult, ledgerResult, aggregationResult] = await Promise.all([
      fetchSalesInventoryStockSummary(itemCode, {
        company: query.company.trim() || undefined,
        warehouse: query.warehouse.trim() || undefined,
      }),
      fetchSalesInventoryStockLedger(itemCode, {
        company: query.company.trim() || undefined,
        warehouse: query.warehouse.trim() || undefined,
        from_date: query.from_date || undefined,
        to_date: query.to_date || undefined,
        page: query.page,
        page_size: query.page_size,
      }),
      fetchSalesInventoryAggregation({
        company: query.company.trim() || undefined,
        item_code: itemCode,
        warehouse: query.warehouse.trim() || undefined,
      }),
    ])
    stockSummaryRows.value = summaryResult.data.items
    stockSummaryDroppedCount.value = summaryResult.data.dropped_count
    rows.value = ledgerResult.data.items
    total.value = ledgerResult.data.total
    inventoryAggregationRows.value = aggregationResult.data.items
    if (ledgerDetailRow.value) {
      const latest = ledgerResult.data.items.find((item) => item.name === ledgerDetailRow.value?.name)
      if (latest) {
        ledgerDetailRow.value = latest
      }
    }
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

const loadCustomerReturnApplications = async (): Promise<void> => {
  if (!canRead.value) {
    resetCustomerReturnApplicationRows()
    customerReturnApplicationError.value = ''
    return
  }
  customerReturnApplicationLoading.value = true
  customerReturnApplicationError.value = ''
  try {
    if (customerReturnApplicationQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('客户退货申请区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryCustomerReturnApplications({
      application_no: customerReturnApplicationQuery.application_no.trim() || undefined,
      item_code: customerReturnApplicationQuery.item_code.trim() || undefined,
      warehouse: customerReturnApplicationQuery.warehouse.trim() || undefined,
      application_status: customerReturnApplicationQuery.application_status || undefined,
      approval_status: customerReturnApplicationQuery.approval_status || undefined,
      keyword: customerReturnApplicationQuery.keyword.trim() || undefined,
      from_date: customerReturnApplicationQuery.from_date || undefined,
      to_date: customerReturnApplicationQuery.to_date || undefined,
      page: customerReturnApplicationQuery.page,
      page_size: customerReturnApplicationQuery.page_size,
    })
    customerReturnApplicationRows.value = result.data.items
    customerReturnApplicationTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    customerReturnApplicationError.value = message
    resetCustomerReturnApplicationRows()
    ElMessage.error(message)
  } finally {
    customerReturnApplicationLoading.value = false
  }
}

const loadCustomerReturnInbound = async (): Promise<void> => {
  if (!canRead.value) {
    resetCustomerReturnInboundRows()
    customerReturnInboundError.value = ''
    return
  }
  customerReturnInboundLoading.value = true
  customerReturnInboundError.value = ''
  try {
    if (customerReturnInboundQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('客户退货入仓区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryCustomerReturnInbound({
      inbound_no: customerReturnInboundQuery.inbound_no.trim() || undefined,
      application_no: customerReturnInboundQuery.application_no.trim() || undefined,
      item_code: customerReturnInboundQuery.item_code.trim() || undefined,
      warehouse: customerReturnInboundQuery.warehouse.trim() || undefined,
      inbound_status: customerReturnInboundQuery.inbound_status || undefined,
      review_status: customerReturnInboundQuery.review_status || undefined,
      keyword: customerReturnInboundQuery.keyword.trim() || undefined,
      from_date: customerReturnInboundQuery.from_date || undefined,
      to_date: customerReturnInboundQuery.to_date || undefined,
      page: customerReturnInboundQuery.page,
      page_size: customerReturnInboundQuery.page_size,
    })
    customerReturnInboundRows.value = result.data.items
    customerReturnInboundTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    customerReturnInboundError.value = message
    resetCustomerReturnInboundRows()
    ElMessage.error(message)
  } finally {
    customerReturnInboundLoading.value = false
  }
}

const loadFinishedGoodsOtherOutbound = async (): Promise<void> => {
  if (!canRead.value) {
    resetFinishedGoodsOtherOutboundRows()
    finishedGoodsOtherOutboundError.value = ''
    return
  }
  finishedGoodsOtherOutboundLoading.value = true
  finishedGoodsOtherOutboundError.value = ''
  try {
    if (finishedGoodsOtherOutboundQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('成品其他出仓区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryFinishedGoodsOtherOutbound({
      outbound_no: finishedGoodsOtherOutboundQuery.outbound_no.trim() || undefined,
      item_code: finishedGoodsOtherOutboundQuery.item_code.trim() || undefined,
      warehouse: finishedGoodsOtherOutboundQuery.warehouse.trim() || undefined,
      outbound_status: finishedGoodsOtherOutboundQuery.outbound_status || undefined,
      review_status: finishedGoodsOtherOutboundQuery.review_status || undefined,
      keyword: finishedGoodsOtherOutboundQuery.keyword.trim() || undefined,
      from_date: finishedGoodsOtherOutboundQuery.from_date || undefined,
      to_date: finishedGoodsOtherOutboundQuery.to_date || undefined,
      page: finishedGoodsOtherOutboundQuery.page,
      page_size: finishedGoodsOtherOutboundQuery.page_size,
    })
    finishedGoodsOtherOutboundRows.value = result.data.items
    finishedGoodsOtherOutboundTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    finishedGoodsOtherOutboundError.value = message
    resetFinishedGoodsOtherOutboundRows()
    ElMessage.error(message)
  } finally {
    finishedGoodsOtherOutboundLoading.value = false
  }
}

const loadFinishedGoodsCount = async (): Promise<void> => {
  if (!canRead.value) {
    resetFinishedGoodsCountRows()
    finishedGoodsCountError.value = ''
    return
  }
  finishedGoodsCountLoading.value = true
  finishedGoodsCountError.value = ''
  try {
    if (finishedGoodsCountQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('成品盘点区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryFinishedGoodsCount({
      count_no: finishedGoodsCountQuery.count_no.trim() || undefined,
      item_code: finishedGoodsCountQuery.item_code.trim() || undefined,
      warehouse: finishedGoodsCountQuery.warehouse.trim() || undefined,
      count_status: finishedGoodsCountQuery.count_status || undefined,
      review_status: finishedGoodsCountQuery.review_status || undefined,
      keyword: finishedGoodsCountQuery.keyword.trim() || undefined,
      from_date: finishedGoodsCountQuery.from_date || undefined,
      to_date: finishedGoodsCountQuery.to_date || undefined,
      page: finishedGoodsCountQuery.page,
      page_size: finishedGoodsCountQuery.page_size,
    })
    finishedGoodsCountRows.value = result.data.items
    finishedGoodsCountTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    finishedGoodsCountError.value = message
    resetFinishedGoodsCountRows()
    ElMessage.error(message)
  } finally {
    finishedGoodsCountLoading.value = false
  }
}

const loadFinishedGoodsAdjustment = async (): Promise<void> => {
  if (!canRead.value) {
    resetFinishedGoodsAdjustmentRows()
    finishedGoodsAdjustmentError.value = ''
    return
  }
  finishedGoodsAdjustmentLoading.value = true
  finishedGoodsAdjustmentError.value = ''
  try {
    if (finishedGoodsAdjustmentQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('成品调整区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryFinishedGoodsAdjustment({
      adjustment_no: finishedGoodsAdjustmentQuery.adjustment_no.trim() || undefined,
      item_code: finishedGoodsAdjustmentQuery.item_code.trim() || undefined,
      warehouse: finishedGoodsAdjustmentQuery.warehouse.trim() || undefined,
      adjustment_status: finishedGoodsAdjustmentQuery.adjustment_status || undefined,
      review_status: finishedGoodsAdjustmentQuery.review_status || undefined,
      keyword: finishedGoodsAdjustmentQuery.keyword.trim() || undefined,
      from_date: finishedGoodsAdjustmentQuery.from_date || undefined,
      to_date: finishedGoodsAdjustmentQuery.to_date || undefined,
      page: finishedGoodsAdjustmentQuery.page,
      page_size: finishedGoodsAdjustmentQuery.page_size,
    })
    finishedGoodsAdjustmentRows.value = result.data.items
    finishedGoodsAdjustmentTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    finishedGoodsAdjustmentError.value = message
    resetFinishedGoodsAdjustmentRows()
    ElMessage.error(message)
  } finally {
    finishedGoodsAdjustmentLoading.value = false
  }
}

const loadFinishedGoodsTransfer = async (): Promise<void> => {
  if (!canRead.value) {
    resetFinishedGoodsTransferRows()
    finishedGoodsTransferError.value = ''
    return
  }
  finishedGoodsTransferLoading.value = true
  finishedGoodsTransferError.value = ''
  try {
    if (finishedGoodsTransferQuery.keyword.trim().toUpperCase() === '__ERROR__') {
      throw new Error('成品调仓区块本地模拟错误态')
    }
    const result = await fetchSalesInventoryFinishedGoodsTransfer({
      transfer_no: finishedGoodsTransferQuery.transfer_no.trim() || undefined,
      item_code: finishedGoodsTransferQuery.item_code.trim() || undefined,
      source_warehouse: finishedGoodsTransferQuery.source_warehouse.trim() || undefined,
      target_warehouse: finishedGoodsTransferQuery.target_warehouse.trim() || undefined,
      transfer_status: finishedGoodsTransferQuery.transfer_status || undefined,
      review_status: finishedGoodsTransferQuery.review_status || undefined,
      keyword: finishedGoodsTransferQuery.keyword.trim() || undefined,
      from_date: finishedGoodsTransferQuery.from_date || undefined,
      to_date: finishedGoodsTransferQuery.to_date || undefined,
      page: finishedGoodsTransferQuery.page,
      page_size: finishedGoodsTransferQuery.page_size,
    })
    finishedGoodsTransferRows.value = result.data.items
    finishedGoodsTransferTotal.value = result.data.total
  } catch (error) {
    const message = (error as Error).message
    finishedGoodsTransferError.value = message
    resetFinishedGoodsTransferRows()
    ElMessage.error(message)
  } finally {
    finishedGoodsTransferLoading.value = false
  }
}

const onSearch = (): void => {
  query.page = 1
  void loadRows()
  void refreshLocalInventoryReadback()
}

const onReset = (): void => {
  query.item_code = ''
  query.company = ''
  query.warehouse = ''
  query.keyword = ''
  query.status = ''
  query.flow_type = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = 20
  localInventoryReadback.value = null
  localInventoryReadbackMessage.value = '未检测到库存草稿回读数据'
  requiredItemCodeGuarded.value = false
  lastError.value = ''
  resetRows()
}

const onOpenLedgerDetail = (row: StockLedgerItem): void => {
  ledgerDetailRow.value = row
  ledgerDetailVisible.value = true
}

const LOCAL_STOCK_LEDGER_ENDPOINT = '/api/local-dev/stock-ledger'
const LOCAL_STOCK_LEDGER_DRAFT_ENDPOINT = '/api/local-dev/stock-ledger/draft'

const upsertLocalStockLedgerDraft = async (
  payload: Record<string, unknown>,
  draftId?: number,
): Promise<ApiResponse<LocalInventoryReadback>> => {
  const isUpdate = typeof draftId === 'number' && draftId > 0
  return request<LocalInventoryReadback>(
    isUpdate ? `${LOCAL_STOCK_LEDGER_DRAFT_ENDPOINT}/${draftId}` : LOCAL_STOCK_LEDGER_DRAFT_ENDPOINT,
    {
      method: isUpdate ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  )
}

const rollbackLocalStockLedgerDraft = async (
  draftId: number,
  scenarioTag: string,
): Promise<ApiResponse<{ rollback_success: boolean; zero_residual_success: boolean; residual_records_after_rollback: number }>> => {
  return request<{ rollback_success: boolean; zero_residual_success: boolean; residual_records_after_rollback: number }>(
    `${LOCAL_STOCK_LEDGER_DRAFT_ENDPOINT}/${draftId}/rollback`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_tag: scenarioTag }),
    },
  )
}

const detectInventoryScenarioTag = (): string => {
  const localScenario = extractWarehouseScenarioTag(localWriteForm.scenario_tag.trim())
  if (localScenario) return localScenario
  const draftScenario = extractWarehouseScenarioTag(localDraft.value?.scenario_tag || '')
  if (draftScenario) return draftScenario
  const keywordScenario = extractWarehouseScenarioTag(query.keyword.trim())
  if (keywordScenario) return keywordScenario
  const routeScenario = typeof route.query.keyword === 'string' ? extractWarehouseScenarioTag(route.query.keyword) : null
  if (routeScenario) return routeScenario
  const statusScenario = extractWarehouseScenarioTag(query.status.trim())
  if (statusScenario) return statusScenario
  const routeStatusScenario = typeof route.query.status === 'string' ? extractWarehouseScenarioTag(route.query.status) : null
  if (routeStatusScenario) return routeStatusScenario
  return ''
}

const refreshLocalInventoryReadback = async (): Promise<void> => {
  const scenarioTag = detectInventoryScenarioTag()
  if (!scenarioTag) {
    localInventoryReadback.value = null
    localInventoryReadbackMessage.value = '未提供库存 scenario_tag，回读面板待命。'
    return
  }
  try {
    const params = new URLSearchParams({
      scenario_tag: scenarioTag,
      page: '1',
      page_size: '1',
    }).toString()
    const response = await request<{ records: LocalInventoryReadback[]; total: number }>(
      `${LOCAL_STOCK_LEDGER_ENDPOINT}?${params}`,
    )
    const latest = response.data.records[0] || null
    localInventoryReadback.value = latest
    localInventoryReadbackMessage.value = latest
      ? `inventory_readback: ${latest.draft_no || latest.draft_id}`
      : `scenario_tag=${scenarioTag} 未找到库存草稿`
  } catch (error) {
    localInventoryReadback.value = null
    localInventoryReadbackMessage.value = `库存回读失败：${(error as Error).message}`
  }
}

const applyLocalStockLedgerDraft = async (): Promise<void> => {
  if (!canRead.value) {
    return
  }
  if (stockLedgerWriteGuarded.value) {
    onGuardedAction('库存流水草稿写入（readback-only）')
    return
  }
  const scenarioTag = extractWarehouseScenarioTag(localWriteForm.scenario_tag.trim())
  if (!scenarioTag) {
    localWriteFeedbackType.value = 'warning'
    localWriteFeedback.value = 'scenario_tag 缺失或格式非法，请使用 Z003-WAREHOUSE-YYYYMMDD-NNN。'
    ElMessage.warning(localWriteFeedback.value)
    return
  }

  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const transferQty = Number(localWriteForm.qty)
    const payload = {
      scenario_tag: scenarioTag,
      operation_type: 'transfer',
      flow_type: 'transfer',
      material_code: localWriteForm.item_code.trim() || 'MAT-LOCAL-001',
      material_name: localWriteForm.item_code.trim() || 'MAT-LOCAL-001',
      warehouse: localWriteForm.warehouse.trim() || '样衣仓',
      source_warehouse: localWriteForm.source_warehouse.trim() || localWriteForm.warehouse.trim() || '样衣仓',
      target_warehouse: localWriteForm.target_warehouse.trim() || localWriteForm.warehouse.trim() || '成品仓',
      current_qty: 100,
      transfer_qty: Number.isFinite(transferQty) && transferQty > 0 ? transferQty : 1,
      counting_qty: 100,
      status: 'draft',
      business_ref: `SL-${scenarioTag}`,
      business_time: new Date().toISOString().slice(0, 10),
      note: `${scenarioTag}-stock-ledger`,
      uom: 'Nos',
    }
    const draftResult = await upsertLocalStockLedgerDraft(payload, localDraft.value?.id)
    localDraft.value = draftResult.data
    query.item_code = payload.material_code
    if (!query.warehouse.trim()) {
      query.warehouse = payload.warehouse
    }
    query.keyword = scenarioTag
    query.status = scenarioTag
    await loadRows({ silentGuard: true })
    await refreshLocalInventoryReadback()
    localWriteFeedbackType.value = 'success'
    localWriteFeedback.value = `库存草稿已保存：draft_id=${draftResult.data.id}`
    ElMessage.success(localWriteFeedback.value)
  } catch (error) {
    const message = (error as Error).message || '本地草稿写入失败'
    localWriteFeedbackType.value = 'error'
    localWriteFeedback.value = message
    ElMessage.error(message)
  } finally {
    localWriteLoading.value = false
  }
}

const onOpenLocalDraftGuarded = (): void => {
  if (stockLedgerWriteGuarded.value) {
    onGuardedAction('库存流水草稿写入（readback-only）')
    return
  }
  void applyLocalStockLedgerDraft()
}

const voidLocalStockLedgerDraft = async (): Promise<void> => {
  if (!canRead.value || !localDraft.value) {
    return
  }
  if (stockLedgerWriteGuarded.value) {
    onGuardedAction('库存流水草稿作废（readback-only）')
    return
  }
  const scenarioTag =
    extractWarehouseScenarioTag(localWriteForm.scenario_tag.trim()) ||
    extractWarehouseScenarioTag(localDraft.value.scenario_tag || '')
  if (!scenarioTag) {
    localWriteFeedbackType.value = 'warning'
    localWriteFeedback.value = 'scenario_tag 缺失或格式非法，无法执行回滚。'
    ElMessage.warning(localWriteFeedback.value)
    return
  }

  localWriteLoading.value = true
  try {
    const rollbackResult = await rollbackLocalStockLedgerDraft(localDraft.value.id, scenarioTag)
    localDraft.value = null
    await loadRows({ silentGuard: true })
    await refreshLocalInventoryReadback()
    localWriteFeedbackType.value = 'success'
    localWriteFeedback.value =
      `库存草稿已回滚：residual=${rollbackResult.data.residual_records_after_rollback}`
    ElMessage.success(localWriteFeedback.value)
  } catch (error) {
    const message = (error as Error).message || '本地草稿回滚失败'
    localWriteFeedbackType.value = 'error'
    localWriteFeedback.value = message
    ElMessage.error(message)
  } finally {
    localWriteLoading.value = false
  }
}

const onVoidLocalDraftGuarded = (): void => {
  if (stockLedgerWriteGuarded.value) {
    onGuardedAction('库存流水草稿回滚（readback-only）')
    return
  }
  void voidLocalStockLedgerDraft()
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

const customerReturnApplicationStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已确认') {
    return 'success'
  }
  if (normalized === '已受理' || normalized === '草稿') {
    return 'warning'
  }
  return 'info'
}

const customerReturnApprovalStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已通过') {
    return 'success'
  }
  if (normalized === '待复核' || normalized === '复核中') {
    return 'warning'
  }
  return 'info'
}

const customerReturnInboundStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '待入仓' || normalized === '入仓中' || normalized === '草稿') {
    return 'warning'
  }
  return 'info'
}

const customerReturnInboundReviewStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已通过') {
    return 'success'
  }
  if (normalized === '待复核' || normalized === '复核中') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsOtherOutboundStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '待出仓' || normalized === '出仓中' || normalized === '草稿') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsOtherOutboundReviewStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已通过') {
    return 'success'
  }
  if (normalized === '待复核' || normalized === '复核中') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsCountStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '待盘点' || normalized === '盘点中' || normalized === '草稿') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsCountReviewStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已通过') {
    return 'success'
  }
  if (normalized === '待复核' || normalized === '复核中') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsAdjustmentStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '待确认' || normalized === '调整中' || normalized === '草稿') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsAdjustmentReviewStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已通过') {
    return 'success'
  }
  if (normalized === '待复核' || normalized === '复核中') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsTransferStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已完成') {
    return 'success'
  }
  if (normalized === '待确认' || normalized === '调仓中' || normalized === '草稿') {
    return 'warning'
  }
  return 'info'
}

const finishedGoodsTransferReviewStatusType = (
  status: string | null | undefined,
): 'success' | 'warning' | 'info' => {
  const normalized = (status || '').trim()
  if (normalized === '已通过') {
    return 'success'
  }
  if (normalized === '待复核' || normalized === '复核中') {
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

const onCustomerReturnApplicationSearch = (): void => {
  customerReturnApplicationQuery.page = 1
  void loadCustomerReturnApplications()
}

const onCustomerReturnApplicationReset = (): void => {
  customerReturnApplicationQuery.application_no = ''
  customerReturnApplicationQuery.item_code = ''
  customerReturnApplicationQuery.warehouse = ''
  customerReturnApplicationQuery.application_status = ''
  customerReturnApplicationQuery.approval_status = ''
  customerReturnApplicationQuery.keyword = ''
  customerReturnApplicationQuery.from_date = ''
  customerReturnApplicationQuery.to_date = ''
  customerReturnApplicationQuery.page = 1
  customerReturnApplicationQuery.page_size = 20
  void loadCustomerReturnApplications()
}

const onCustomerReturnApplicationPageChange = (page: number): void => {
  customerReturnApplicationQuery.page = page
  void loadCustomerReturnApplications()
}

const onCustomerReturnApplicationSizeChange = (size: number): void => {
  customerReturnApplicationQuery.page_size = size
  customerReturnApplicationQuery.page = 1
  void loadCustomerReturnApplications()
}

const onCustomerReturnInboundSearch = (): void => {
  customerReturnInboundQuery.page = 1
  void loadCustomerReturnInbound()
}

const onCustomerReturnInboundReset = (): void => {
  customerReturnInboundQuery.inbound_no = ''
  customerReturnInboundQuery.application_no = ''
  customerReturnInboundQuery.item_code = ''
  customerReturnInboundQuery.warehouse = ''
  customerReturnInboundQuery.inbound_status = ''
  customerReturnInboundQuery.review_status = ''
  customerReturnInboundQuery.keyword = ''
  customerReturnInboundQuery.from_date = ''
  customerReturnInboundQuery.to_date = ''
  customerReturnInboundQuery.page = 1
  customerReturnInboundQuery.page_size = 20
  void loadCustomerReturnInbound()
}

const onCustomerReturnInboundPageChange = (page: number): void => {
  customerReturnInboundQuery.page = page
  void loadCustomerReturnInbound()
}

const onCustomerReturnInboundSizeChange = (size: number): void => {
  customerReturnInboundQuery.page_size = size
  customerReturnInboundQuery.page = 1
  void loadCustomerReturnInbound()
}

const onFinishedGoodsOtherOutboundSearch = (): void => {
  finishedGoodsOtherOutboundQuery.page = 1
  void loadFinishedGoodsOtherOutbound()
}

const onFinishedGoodsOtherOutboundReset = (): void => {
  finishedGoodsOtherOutboundQuery.outbound_no = ''
  finishedGoodsOtherOutboundQuery.item_code = ''
  finishedGoodsOtherOutboundQuery.warehouse = ''
  finishedGoodsOtherOutboundQuery.outbound_status = ''
  finishedGoodsOtherOutboundQuery.review_status = ''
  finishedGoodsOtherOutboundQuery.keyword = ''
  finishedGoodsOtherOutboundQuery.from_date = ''
  finishedGoodsOtherOutboundQuery.to_date = ''
  finishedGoodsOtherOutboundQuery.page = 1
  finishedGoodsOtherOutboundQuery.page_size = 20
  void loadFinishedGoodsOtherOutbound()
}

const onFinishedGoodsOtherOutboundPageChange = (page: number): void => {
  finishedGoodsOtherOutboundQuery.page = page
  void loadFinishedGoodsOtherOutbound()
}

const onFinishedGoodsOtherOutboundSizeChange = (size: number): void => {
  finishedGoodsOtherOutboundQuery.page_size = size
  finishedGoodsOtherOutboundQuery.page = 1
  void loadFinishedGoodsOtherOutbound()
}

const onFinishedGoodsCountSearch = (): void => {
  finishedGoodsCountQuery.page = 1
  void loadFinishedGoodsCount()
}

const onFinishedGoodsCountReset = (): void => {
  finishedGoodsCountQuery.count_no = ''
  finishedGoodsCountQuery.item_code = ''
  finishedGoodsCountQuery.warehouse = ''
  finishedGoodsCountQuery.count_status = ''
  finishedGoodsCountQuery.review_status = ''
  finishedGoodsCountQuery.keyword = ''
  finishedGoodsCountQuery.from_date = ''
  finishedGoodsCountQuery.to_date = ''
  finishedGoodsCountQuery.page = 1
  finishedGoodsCountQuery.page_size = 20
  void loadFinishedGoodsCount()
}

const onFinishedGoodsCountPageChange = (page: number): void => {
  finishedGoodsCountQuery.page = page
  void loadFinishedGoodsCount()
}

const onFinishedGoodsCountSizeChange = (size: number): void => {
  finishedGoodsCountQuery.page_size = size
  finishedGoodsCountQuery.page = 1
  void loadFinishedGoodsCount()
}

const onFinishedGoodsAdjustmentSearch = (): void => {
  finishedGoodsAdjustmentQuery.page = 1
  void loadFinishedGoodsAdjustment()
}

const onFinishedGoodsAdjustmentReset = (): void => {
  finishedGoodsAdjustmentQuery.adjustment_no = ''
  finishedGoodsAdjustmentQuery.item_code = ''
  finishedGoodsAdjustmentQuery.warehouse = ''
  finishedGoodsAdjustmentQuery.adjustment_status = ''
  finishedGoodsAdjustmentQuery.review_status = ''
  finishedGoodsAdjustmentQuery.keyword = ''
  finishedGoodsAdjustmentQuery.from_date = ''
  finishedGoodsAdjustmentQuery.to_date = ''
  finishedGoodsAdjustmentQuery.page = 1
  finishedGoodsAdjustmentQuery.page_size = 20
  void loadFinishedGoodsAdjustment()
}

const onFinishedGoodsAdjustmentPageChange = (page: number): void => {
  finishedGoodsAdjustmentQuery.page = page
  void loadFinishedGoodsAdjustment()
}

const onFinishedGoodsAdjustmentSizeChange = (size: number): void => {
  finishedGoodsAdjustmentQuery.page_size = size
  finishedGoodsAdjustmentQuery.page = 1
  void loadFinishedGoodsAdjustment()
}

const onFinishedGoodsTransferSearch = (): void => {
  finishedGoodsTransferQuery.page = 1
  void loadFinishedGoodsTransfer()
}

const onFinishedGoodsTransferReset = (): void => {
  finishedGoodsTransferQuery.transfer_no = ''
  finishedGoodsTransferQuery.item_code = ''
  finishedGoodsTransferQuery.source_warehouse = ''
  finishedGoodsTransferQuery.target_warehouse = ''
  finishedGoodsTransferQuery.transfer_status = ''
  finishedGoodsTransferQuery.review_status = ''
  finishedGoodsTransferQuery.keyword = ''
  finishedGoodsTransferQuery.from_date = ''
  finishedGoodsTransferQuery.to_date = ''
  finishedGoodsTransferQuery.page = 1
  finishedGoodsTransferQuery.page_size = 20
  void loadFinishedGoodsTransfer()
}

const onFinishedGoodsTransferPageChange = (page: number): void => {
  finishedGoodsTransferQuery.page = page
  void loadFinishedGoodsTransfer()
}

const onFinishedGoodsTransferSizeChange = (size: number): void => {
  finishedGoodsTransferQuery.page_size = size
  finishedGoodsTransferQuery.page = 1
  void loadFinishedGoodsTransfer()
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
    applyRoutePrefill()
    await loadRows({ silentGuard: true })
    await loadMaterialTransfers()
    await refreshLocalInventoryReadback()
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

.local-write-form {
  margin-bottom: 12px;
}

.local-draft-descriptions {
  margin-bottom: 12px;
}

.error-alert {
  margin-bottom: 12px;
}

.scope-alert {
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
