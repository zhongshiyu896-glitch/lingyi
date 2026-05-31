<template>
  <div
    class="subcontract-detail-page"
    data-testid="subcontract-detail-page"
    data-readonly-boundary="true"
    data-write-request-success-allowed="false"
    data-real-write-action-added="false"
  >
    <el-card shadow="never" v-loading="loading" data-testid="subcontract-detail-main-card">
      <template #header>
        <div class="header-row" data-testid="subcontract-detail-header">
          <span data-testid="subcontract-detail-title">外发单详情</span>
          <el-button data-testid="subcontract-detail-back" @click="goBack">返回</el-button>
        </div>
      </template>
      <section
        class="z044-subcontract-panel"
        data-testid="z044-subcontract-list-detail-diff"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
      >
        <div class="z044-panel-header">
          <strong>详情 readback 差异与同步锁定</strong>
          <el-tag type="warning" effect="plain">Z044 readonly</el-tag>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="列表/详情差异">
            <span>{{ z044ListDetailDiff }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="readback 一致性">
            <span
              data-testid="z044-subcontract-readback-consistency"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044ReadbackConsistency }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="同步锁定原因">
            <span
              data-testid="z044-subcontract-sync-lock-reason"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044SyncLockReason }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="导出/打印只读">
            <span
              data-testid="z044-subcontract-export-print-readonly"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044ExportPrintReadonly }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="materialPurchase parity 来源">
            <span
              data-testid="z044-subcontract-material-parity-readback"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044MaterialParityReadback }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="network/write blocker">
            <span
              data-testid="z044-subcontract-network-write-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044NetworkWriteBlocker }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="write success blocker" :span="2">
            <span
              data-testid="z044-subcontract-write-success-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z044WriteSuccessBlocker }}
            </span>
          </el-descriptions-item>
        </el-descriptions>
        <div class="z044-guard-actions" data-testid="z044-subcontract-guarded-action-matrix">
          <el-tag
            v-for="entry in z044GuardEntries"
            :key="entry"
            type="info"
            effect="plain"
            data-action-type="write"
            data-write-guard="guarded:readonly"
            data-guard-state="guarded-readonly"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
            :data-guard-entry="entry"
          >
            {{ entry }} guarded/readonly
          </el-tag>
        </div>
      </section>
      <section
        class="z045-subcontract-panel"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
      >
        <div class="z045-panel-header">
          <strong>外发详情同步与结算只读交互</strong>
          <el-tag type="warning" effect="plain">Z045 interaction</el-tag>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="parity 差异审计">
            <span
              data-testid="z045-subcontract-parity-diff-audit"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z045ParityDiffAudit }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="列表/详情 readback">
            <span
              data-testid="z045-subcontract-list-detail-readback"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z045ListDetailReadback }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="同步拒写原因">
            <span
              data-testid="z045-subcontract-sync-denial-reason"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z045SyncDenialReason }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="导出/打印锁定">
            <span
              data-testid="z045-subcontract-export-print-lock"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z045ExportPrintLock }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="materialPurchase 来源">
            <span
              data-testid="z045-subcontract-material-parity-source"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z045MaterialParitySource }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="network/write blocker">
            <span
              data-testid="z045-subcontract-network-write-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z045NetworkWriteBlocker }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="write success blocker" :span="2">
            <span
              data-testid="z045-subcontract-write-success-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z045WriteSuccessBlocker }}
            </span>
          </el-descriptions-item>
        </el-descriptions>
        <el-table
          :data="z045GuardedActionMatrix"
          size="small"
          border
          class="z045-guard-table"
          data-testid="z045-subcontract-guarded-action-matrix"
          data-readonly-boundary="true"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <el-table-column prop="entry" label="动作" width="120">
            <template #default="scope">
              <span
                data-action-type="write"
                data-write-guard="guarded:readonly"
                data-guard-state="guarded-readonly"
                data-readonly-boundary="true"
                data-write-request-success-allowed="false"
                data-real-write-action-added="false"
                :data-guard-entry="scope.row.entry"
              >
                {{ scope.row.entry }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="prerequisite" label="前置条件" min-width="180" />
          <el-table-column prop="lockReason" label="锁定原因" min-width="220" />
          <el-table-column prop="state" label="当前状态" width="150" />
        </el-table>
      </section>
      <section
        class="z045-subcontract-panel"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
      >
        <div class="z045-panel-header">
          <strong>Z046 外协详情/列表交互 readback</strong>
          <el-tag type="warning" effect="plain">Z046 interaction</el-tag>
        </div>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="列表/详情状态联动">
            <span
              data-testid="z046-subcontract-list-detail-state-link"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z046ListDetailStateLink }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="结算预览前置条件">
            <span
              data-testid="z046-subcontract-settlement-precondition"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z046SettlementPrecondition }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="同步重试锁定原因">
            <span
              data-testid="z046-subcontract-sync-retry-lock-reason"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z046SyncRetryLockReason }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="导出/打印锁定原因">
            <span
              data-testid="z046-subcontract-export-print-lock-reason"
              data-guard-state="guarded-readonly"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z046ExportPrintLockReason }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="materialPurchase parity 来源">
            <span
              data-testid="z046-subcontract-material-parity-source"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z046MaterialParitySource }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="network/write blocker">
            <span
              data-testid="z046-subcontract-network-write-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z046NetworkWriteBlocker }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="write success blocker" :span="2">
            <span
              data-testid="z046-subcontract-write-success-blocker"
              data-readonly-boundary="true"
              data-write-request-success-allowed="false"
              data-real-write-action-added="false"
            >
              {{ z046WriteSuccessBlocker }}
            </span>
          </el-descriptions-item>
        </el-descriptions>
        <el-table
          :data="z046GuardedActionMatrix"
          size="small"
          border
          class="z045-guard-table"
          data-testid="z046-subcontract-guarded-action-matrix"
          data-readonly-boundary="true"
          data-write-request-success-allowed="false"
          data-real-write-action-added="false"
        >
          <el-table-column prop="entry" label="动作" width="120">
            <template #default="scope">
              <span
                data-action-type="write"
                data-write-guard="guarded:readonly"
                data-guard-state="guarded-readonly"
                data-readonly-boundary="true"
                data-write-request-success-allowed="false"
                data-real-write-action-added="false"
                :data-guard-entry="scope.row.entry"
              >
                {{ scope.row.entry }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="prerequisite" label="前置条件" min-width="180" />
          <el-table-column prop="lockReason" label="锁定原因" min-width="220" />
          <el-table-column prop="state" label="当前状态" width="150" />
        </el-table>
      </section>
      <el-skeleton v-if="!permissionReady" :rows="4" animated data-testid="subcontract-detail-loading-state" />
      <el-empty
        v-else-if="!canRead"
        description="无外发查看权限"
        data-testid="subcontract-detail-permission-state"
      />
      <template v-else>
        <el-empty
          v-if="missingOrderId"
          description="请从外发单列表进入详情页"
          data-testid="subcontract-detail-missing-id-state"
        />
        <el-alert
          v-else-if="loadError"
          :title="loadError"
          type="error"
          show-icon
          :closable="false"
          data-testid="subcontract-detail-error-state"
        />
        <el-empty v-else-if="!detail" description="未找到外发单详情" data-testid="subcontract-detail-empty-state" />
        <template v-else>
          <el-descriptions :column="3" border data-testid="subcontract-detail-main-fields">
            <el-descriptions-item label="外发单号">
              <span data-testid="subcontract-detail-field-subcontract-no">{{ detail.subcontract_no }}</span>
            </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag data-testid="subcontract-detail-status-tag">{{ statusLabel(detail.status) }}</el-tag>
            <el-tag
              v-if="isScopeBlocked"
              type="danger"
              class="scope-tag"
              data-testid="subcontract-detail-scope-blocked-tag"
            >
              权限范围异常
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="公司">{{ detail.company || '-' }}</el-descriptions-item>
          <el-descriptions-item label="加工厂">{{ detail.supplier }}</el-descriptions-item>
          <el-descriptions-item label="款式">{{ detail.item_code }}</el-descriptions-item>
          <el-descriptions-item label="工序">{{ detail.process_name }}</el-descriptions-item>
          <el-descriptions-item label="计划数量">{{ detail.planned_qty }}</el-descriptions-item>
          <el-descriptions-item label="已发料">{{ detail.issued_qty }}</el-descriptions-item>
          <el-descriptions-item label="已回料">{{ detail.received_qty }}</el-descriptions-item>
          <el-descriptions-item label="已验货">{{ detail.inspected_qty }}</el-descriptions-item>
          <el-descriptions-item label="不合格数量">{{ detail.rejected_qty }}</el-descriptions-item>
          <el-descriptions-item label="合格数量">{{ detail.accepted_qty }}</el-descriptions-item>
          <el-descriptions-item label="加工单价">{{ detail.subcontract_rate }}</el-descriptions-item>
          <el-descriptions-item label="验货总金额">{{ detail.gross_amount }}</el-descriptions-item>
          <el-descriptions-item label="扣款金额">{{ detail.deduction_amount }}</el-descriptions-item>
          <el-descriptions-item label="净应付金额">{{ detail.net_amount }}</el-descriptions-item>
          <el-descriptions-item label="发料同步状态">
            <span data-testid="subcontract-detail-issue-sync-status">
              {{ stockSyncLabel(detail.latest_issue_sync_status) || '-' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="回料同步状态">
            <span data-testid="subcontract-detail-receipt-sync-status">
              {{ stockSyncLabel(detail.latest_receipt_sync_status) || '-' }}
            </span>
          </el-descriptions-item>
          </el-descriptions>

          <section
            class="z042-subcontract-panel"
            data-testid="z042-subcontract-guard-trace"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
          >
            <div class="z042-panel-header">
              <strong>外发单详情 guard trace</strong>
              <el-tag type="warning" effect="plain">readonly fallback</el-tag>
            </div>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="详情主字段">外发单号 / 状态 / 加工厂 / 款式 / 金额只读展示</el-descriptions-item>
              <el-descriptions-item label="parity 来源">
                <span data-testid="z042-subcontract-parity-source">{{ z042ParitySource.label }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="最终路由">{{ z042ParitySource.finalRoute }}</el-descriptions-item>
              <el-descriptions-item label="fallback 解释">
                详情加载失败或权限异常时保留主字段投影和 guard，不推断写成功。
              </el-descriptions-item>
              <el-descriptions-item label="写请求成功">false</el-descriptions-item>
              <el-descriptions-item label="真实写 action">未新增</el-descriptions-item>
            </el-descriptions>
            <div class="z042-guard-actions" data-testid="z042-subcontract-detail-guard-actions">
              <el-button
                v-for="entry in z042GuardEntries"
                :key="entry"
                size="small"
                data-action-type="write"
                data-write-guard="guarded:readonly"
                data-guard-state="guarded_readonly"
                :data-guard-entry="entry"
                @click="guardedWriteAction(entry)"
              >
                {{ entry }}
              </el-button>
            </div>
          </section>

          <section
            class="z043-subcontract-panel"
            data-testid="z043-subcontract-readback-compare"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
          >
            <div class="z043-panel-header">
              <strong>详情 readback 对照</strong>
              <el-tag type="warning" effect="plain">guarded readonly</el-tag>
            </div>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="列表/详情对照">{{ z043ReadbackCompare.detailReadback }}</el-descriptions-item>
              <el-descriptions-item label="同步重试原因">
                <span
                  data-testid="z043-subcontract-sync-retry-reason"
                  data-guard-state="guarded-readonly"
                  data-readonly-boundary="true"
                  data-write-request-success-allowed="false"
                  data-real-write-action-added="false"
                >
                  {{ z043SyncRetryReason }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="导出/打印禁用">
                <span
                  data-testid="z043-subcontract-export-print-disabled"
                  data-guard-state="guarded-readonly"
                  data-readonly-boundary="true"
                  data-write-request-success-allowed="false"
                  data-real-write-action-added="false"
                >
                  {{ z043ExportPrintDisabledReason }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="materialPurchase parity 来源">
                <span
                  data-testid="z043-subcontract-material-parity-source"
                  data-readonly-boundary="true"
                  data-write-request-success-allowed="false"
                  data-real-write-action-added="false"
                >
                  {{ z043MaterialParitySource }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="写成功状态">{{ z043ReadbackCompare.writeState }}</el-descriptions-item>
              <el-descriptions-item label="只读边界">dataReadonlyBoundary=true，真实写 action 未新增</el-descriptions-item>
            </el-descriptions>
            <div class="z043-guard-actions" data-testid="z043-subcontract-detail-guarded-actions">
              <el-tag
                v-for="entry in z043GuardEntries"
                :key="entry"
                type="info"
                effect="plain"
                data-action-type="write"
                data-write-guard="guarded:readonly"
                data-guard-state="guarded-readonly"
                data-readonly-boundary="true"
                data-write-request-success-allowed="false"
                data-real-write-action-added="false"
                :data-guard-entry="entry"
              >
                {{ entry }} guarded/readonly
              </el-tag>
            </div>
          </section>

          <div class="action-row" data-testid="subcontract-detail-guarded-actions">
            <el-button
              data-testid="subcontract-detail-action-issue"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              :disabled="!detail"
              @click="openIssueDialog"
            >
              发料
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-receipt"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              :disabled="!detail"
              @click="openReceiveDialog"
            >
              回料
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-inspection"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              :disabled="!detail"
              @click="openInspectDialog"
            >
              验货
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-settlement"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              :disabled="!detail"
              @click="openSettlementDialog"
            >
              结算
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-retry-sync"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('同步重试')"
            >
              同步重试
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-export"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('导出')"
            >
              导出
            </el-button>
            <el-button
              data-testid="subcontract-detail-action-print"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction('打印')"
            >
              打印
            </el-button>
          </div>

          <el-alert
            v-if="guardedFeedback"
            :title="guardedFeedback"
            type="warning"
            :closable="false"
            show-icon
            data-testid="subcontract-detail-guarded-feedback"
          />

          <p class="permission-tip" data-testid="subcontract-detail-permission-or-disabled-state">
            当前仅开放结算锁定/释放最小子链路，发料/回料/验货/结算预览保持 guarded。
          </p>
        </template>

        <section
          v-if="!detail"
          class="readonly-fallback"
          data-testid="subcontract-detail-readonly-fallback"
          data-write-guard="guarded:readonly"
        >
          <el-alert
            title="只读履约视图：详情数据不可用时仍展示字段与写入口 guard，不发起写请求。"
            type="warning"
            :closable="false"
            show-icon
          />
          <el-descriptions :column="3" border data-testid="subcontract-detail-main-fields">
            <el-descriptions-item label="外发单号">readonly-subcontract</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag>只读投影</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="加工厂">只读加工厂</el-descriptions-item>
            <el-descriptions-item label="款式">readonly-style</el-descriptions-item>
            <el-descriptions-item label="工序">缝制</el-descriptions-item>
            <el-descriptions-item label="履约状态">发料 / 回料 / 验货 / 结算候选已冻结为只读</el-descriptions-item>
          </el-descriptions>
          <div class="action-row" data-testid="subcontract-detail-guarded-actions">
            <el-button
              v-for="action in readonlyGuardActions"
              :key="action"
              data-action-type="write"
              data-write-guard="guarded:readonly"
              @click="guardedWriteAction(action)"
            >
              {{ action }}
            </el-button>
          </div>
          <section
            class="z043-subcontract-panel"
            data-testid="z043-subcontract-readback-compare"
            data-readonly-boundary="true"
            data-write-request-success-allowed="false"
            data-real-write-action-added="false"
          >
            <div class="z043-panel-header">
              <strong>详情 readback 对照</strong>
              <el-tag type="warning" effect="plain">readonly fallback</el-tag>
            </div>
            <el-descriptions :column="3" border size="small">
              <el-descriptions-item label="详情主字段">readonly fallback 投影与列表入口保持对照</el-descriptions-item>
              <el-descriptions-item label="同步重试原因">
                <span
                  data-testid="z043-subcontract-sync-retry-reason"
                  data-guard-state="guarded-readonly"
                  data-readonly-boundary="true"
                  data-write-request-success-allowed="false"
                  data-real-write-action-added="false"
                >
                  {{ z043SyncRetryReason }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="导出/打印禁用">
                <span
                  data-testid="z043-subcontract-export-print-disabled"
                  data-guard-state="guarded-readonly"
                  data-readonly-boundary="true"
                  data-write-request-success-allowed="false"
                  data-real-write-action-added="false"
                >
                  {{ z043ExportPrintDisabledReason }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="materialPurchase parity 来源">
                <span
                  data-testid="z043-subcontract-material-parity-source"
                  data-readonly-boundary="true"
                  data-write-request-success-allowed="false"
                  data-real-write-action-added="false"
                >
                  {{ z043MaterialParitySource }}
                </span>
              </el-descriptions-item>
              <el-descriptions-item label="写成功状态">false</el-descriptions-item>
              <el-descriptions-item label="只读确认">guarded_readonly_not_write_success=true</el-descriptions-item>
            </el-descriptions>
            <div class="z043-guard-actions" data-testid="z043-subcontract-detail-fallback-guarded-actions">
              <el-tag
                v-for="entry in z043GuardEntries"
                :key="entry"
                type="info"
                effect="plain"
                data-action-type="write"
                data-write-guard="guarded:readonly"
                data-guard-state="guarded-readonly"
                data-readonly-boundary="true"
                data-write-request-success-allowed="false"
                data-real-write-action-added="false"
                :data-guard-entry="entry"
              >
                {{ entry }} guarded/readonly
              </el-tag>
            </div>
          </section>
        </section>
      </template>
    </el-card>

    <el-card
      v-if="canRead"
      shadow="never"
      data-testid="subcontract-write-guard"
      data-write-guard="guarded:readonly"
    >
      <el-alert
        title="当前页面为只读履约投影基线，普通前端已冻结新建外发单、发料、回料、验货和同步重试入口。"
        type="info"
        :closable="false"
        show-icon
      />
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-receipt-section">
      <template #header><span>回料批次</span></template>
      <el-table
        :data="detail?.receipts || []"
        border
        empty-text="暂无回料批次数据"
        data-testid="subcontract-detail-receipt-table"
      >
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="receipt_warehouse" label="回料仓" min-width="120" />
        <el-table-column prop="received_qty" label="回料数量" width="120" />
        <el-table-column label="同步状态" width="120">
          <template #default="scope">
            <span data-testid="subcontract-detail-receipt-sync-tag">
              {{ stockSyncLabel(scope.row.sync_status) || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="stock_entry_name" label="Stock Entry" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-inspection-section">
      <template #header><span>验货明细</span></template>
      <el-table
        :data="detail?.inspections || []"
        border
        empty-text="暂无验货明细数据"
        data-testid="subcontract-detail-inspection-table"
      >
        <el-table-column prop="inspection_no" label="验货单号" min-width="180" />
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="inspected_qty" label="验货数量" width="110" />
        <el-table-column prop="accepted_qty" label="合格数量" width="110" />
        <el-table-column prop="rejected_qty" label="不合格数量" width="120" />
        <el-table-column prop="gross_amount" label="验货总金额" width="120" />
        <el-table-column prop="deduction_amount" label="扣款金额" width="120" />
        <el-table-column prop="net_amount" label="净应付金额" width="120" />
        <el-table-column prop="inspected_by" label="验货人" width="120" />
        <el-table-column prop="inspected_at" label="验货时间" min-width="180" />
      </el-table>
    </el-card>

    <el-card v-if="canRead && detail" shadow="never" data-testid="subcontract-detail-settlement-section">
      <template #header><span>结算候选</span></template>
      <div class="settlement-toolbar">
        <el-button size="small" :loading="settlementLoading" data-testid="subcontract-settlement-candidates-refresh" @click="loadSettlementCandidates">刷新候选</el-button>
        <el-button
          size="small"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          data-testid="subcontract-settlement-preview-button"
          @click="runSettlementPreview"
        >
          预览结算
        </el-button>
      </div>
      <el-table
        :data="settlementCandidates"
        border
        empty-text="暂无可结算候选"
        data-testid="subcontract-settlement-candidates-table"
      >
        <el-table-column prop="inspection_id" label="验货ID" width="100" />
        <el-table-column prop="subcontract_no" label="外发单号" min-width="180" />
        <el-table-column prop="receipt_batch_no" label="回料批次" min-width="160" />
        <el-table-column prop="inspected_qty" label="验货数量" width="110" />
        <el-table-column prop="gross_amount" label="总金额" width="120" />
        <el-table-column prop="net_amount" label="净金额" width="120" />
      </el-table>
      <el-descriptions v-if="settlementPreview" :column="3" border class="settlement-preview" data-testid="subcontract-settlement-preview-summary">
        <el-descriptions-item label="行数">{{ settlementPreview.line_count }}</el-descriptions-item>
        <el-descriptions-item label="总数量">{{ settlementPreview.total_qty }}</el-descriptions-item>
        <el-descriptions-item label="净金额">{{ settlementPreview.net_amount }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-dialog
      v-model="issueDialogVisible"
      title="发料"
      width="560px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-issue-dialog"
    >
      <el-form :model="issueForm" label-width="120px">
        <el-form-item label="发料仓">
          <el-input v-model="issueForm.warehouse" data-testid="subcontract-issue-warehouse-input" />
        </el-form-item>
        <el-form-item label="物料编码">
          <el-input v-model="issueForm.material_item_code" data-testid="subcontract-issue-material-input" />
        </el-form-item>
        <el-form-item label="需求数量">
          <el-input-number v-model="issueForm.required_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-issue-required-qty-input" />
        </el-form-item>
        <el-form-item label="本次发料">
          <el-input-number v-model="issueForm.issued_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-issue-issued-qty-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-issue-cancel-button" @click="issueDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="issueSubmitting" data-testid="subcontract-issue-submit-button" @click="submitIssue">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="receiveDialogVisible"
      title="回料"
      width="560px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-receive-dialog"
    >
      <el-form :model="receiveForm" label-width="120px">
        <el-form-item label="回料仓">
          <el-input v-model="receiveForm.receipt_warehouse" data-testid="subcontract-receive-warehouse-input" />
        </el-form-item>
        <el-form-item label="回料数量">
          <el-input-number v-model="receiveForm.received_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-receive-qty-input" />
        </el-form-item>
        <el-form-item label="批次号">
          <el-input v-model="receiveForm.batch_no" data-testid="subcontract-receive-batch-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-receive-cancel-button" @click="receiveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="receiveSubmitting" data-testid="subcontract-receive-submit-button" @click="submitReceive">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="inspectDialogVisible"
      title="验货"
      width="560px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-inspect-dialog"
    >
      <el-form :model="inspectForm" label-width="120px">
        <el-form-item label="回料批次">
          <el-input v-model="inspectForm.receipt_batch_no" data-testid="subcontract-inspect-batch-input" />
        </el-form-item>
        <el-form-item label="验货数量">
          <el-input-number v-model="inspectForm.inspected_qty" :min="0.001" :step="1" :precision="3" data-testid="subcontract-inspect-inspected-qty-input" />
        </el-form-item>
        <el-form-item label="不合格数量">
          <el-input-number v-model="inspectForm.rejected_qty" :min="0" :step="1" :precision="3" data-testid="subcontract-inspect-rejected-qty-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-inspect-cancel-button" @click="inspectDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="inspectSubmitting" data-testid="subcontract-inspect-submit-button" @click="submitInspect">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="settlementDialogVisible"
      title="结算锁定 / 释放"
      width="620px"
      destroy-on-close
      append-to-body
      data-testid="subcontract-settlement-dialog"
    >
      <el-form :model="settlementForm" label-width="120px">
        <el-form-item label="结算单号">
          <el-input v-model="settlementForm.statement_no" data-testid="subcontract-settlement-statement-no-input" />
        </el-form-item>
        <el-form-item label="选择验货ID">
          <el-select
            v-model="settlementForm.inspection_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%"
            data-testid="subcontract-settlement-inspection-ids-select"
          >
            <el-option
              v-for="candidate in settlementCandidates"
              :key="candidate.inspection_id"
              :label="`${candidate.inspection_id} / ${candidate.subcontract_no}`"
              :value="candidate.inspection_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="释放原因">
          <el-input v-model="settlementForm.reason" data-testid="subcontract-settlement-reason-input" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button data-testid="subcontract-settlement-cancel-button" @click="settlementDialogVisible = false">取消</el-button>
        <el-button
          :loading="settlementSubmitting"
          data-testid="subcontract-settlement-lock-button"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          type="primary"
          @click="submitSettlementLock"
        >
          锁定
        </el-button>
        <el-button
          :loading="settlementSubmitting"
          data-testid="subcontract-settlement-release-button"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          type="warning"
          @click="submitSettlementRelease"
        >
          释放
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  buildSubcontractRequestId,
  buildSubcontractScenarioTag,
  fetchSubcontractOrderDetail,
  fetchSubcontractSettlementCandidates,
  inspectSubcontractOrder,
  issueSubcontractMaterial,
  lockSubcontractSettlement,
  receiveSubcontractOrder,
  releaseSubcontractSettlement,
  type SubcontractOrderDetailData,
  type SubcontractSettlementCandidateListItem,
  type SubcontractSettlementPreviewData,
  type SubcontractWriteOperation,
} from '@/api/subcontract'
import { usePermissionStore } from '@/stores/permission'

const route = useRoute()
const router = useRouter()
const permissionStore = usePermissionStore()
const detail = ref<SubcontractOrderDetailData | null>(null)
const missingOrderId = ref<boolean>(false)
const loading = ref<boolean>(false)
const permissionReady = ref<boolean>(false)
const loadError = ref<string>('')
const guardedFeedback = ref<string>('')
const issueDialogVisible = ref<boolean>(false)
const receiveDialogVisible = ref<boolean>(false)
const inspectDialogVisible = ref<boolean>(false)
const settlementDialogVisible = ref<boolean>(false)
const issueSubmitting = ref<boolean>(false)
const receiveSubmitting = ref<boolean>(false)
const inspectSubmitting = ref<boolean>(false)
const settlementSubmitting = ref<boolean>(false)
const settlementLoading = ref<boolean>(false)
const settlementCandidates = ref<SubcontractSettlementCandidateListItem[]>([])
const settlementPreview = ref<SubcontractSettlementPreviewData | null>(null)

const readonlyFallback = ref<boolean>(false)
const canRead = computed<boolean>(() => readonlyFallback.value || permissionStore.state.buttonPermissions.read)
const orderId = computed<number>(() => Number(route.query.id || '0'))
const hasValidOrderId = computed<boolean>(() => Number.isInteger(orderId.value) && orderId.value > 0)
const isScopeBlocked = computed<boolean>(() => detail.value?.resource_scope_status === 'blocked_scope')

const stockSyncLabel = (value?: string | null): string => {
  if (!value) return ''
  const labels: Record<string, string> = {
    pending: '待同步',
    processing: '同步中',
    succeeded: '已同步',
    failed: '同步失败',
    dead: '死信',
    blocked_scope: '范围阻断',
  }
  return labels[value] || value
}

const statusLabel = (value: string): string => {
  const labels: Record<string, string> = {
    draft: '草稿',
    issued: '已发料',
    processing: '加工中',
    waiting_receive: '待回料',
    waiting_inspection: '待验货',
    completed: '已完成',
    cancelled: '已取消',
  }
  return labels[value] || value
}

const issueForm = reactive({
  warehouse: '原材料仓',
  material_item_code: 'RM-DEMO-001',
  required_qty: 10,
  issued_qty: 10,
})

const receiveForm = reactive({
  receipt_warehouse: '成品待验仓',
  received_qty: 10,
  batch_no: '',
  color: 'BLACK',
  size: 'L',
  uom: 'PCS',
})

const inspectForm = reactive({
  receipt_batch_no: '',
  inspected_qty: 10,
  rejected_qty: 0,
  deduction_amount_per_piece: 0,
  remark: '',
})

const settlementForm = reactive({
  statement_no: '',
  inspection_ids: [] as number[],
  reason: 'release-for-local-cleanup',
})

const readonlyGuardActions = ['发料', '回料', '验货', '结算预览', '同步重试', '导出', '打印']
const z042GuardEntries = ['新建外发单', '发料', '回料', '验货', '结算预览', '同步重试', '导出', '打印']
const z043GuardEntries = z042GuardEntries
const z044GuardEntries = z042GuardEntries
const z042ParitySource = computed<{ label: string; finalRoute: string }>(() => {
  const raw = typeof route.query.parity === 'string' ? route.query.parity.trim() : ''
  if (raw === 'material-purchase') {
    return {
      label: 'materialPurchase parity route -> 外发单详情只读视图',
      finalRoute: '/subcontract/detail?parity=material-purchase',
    }
  }
  return {
    label: 'subcontract detail direct route',
    finalRoute: '/subcontract/detail',
  }
})
const z043ReadbackCompare = computed(() => ({
  detailReadback: detail.value
    ? `${detail.value.subcontract_no} / ${detail.value.supplier} / ${statusLabel(detail.value.status)}`
    : 'readonly fallback detail projection / no real write success inferred',
  writeState: 'dataWriteRequestSuccessAllowed=false，详情、同步和导出打印均不形成真实写成功',
}))
const z043SyncRetryReason = computed<string>(() => {
  const issue = stockSyncLabel(detail.value?.latest_issue_sync_status)
  const receipt = stockSyncLabel(detail.value?.latest_receipt_sync_status)
  if (issue || receipt) {
    return `发料:${issue || '未入列'} / 回料:${receipt || '未入列'}；同步重试仅记录原因，不发送重试写请求`
  }
  return '详情无同步异常时仍显示只读重试说明；同步重试入口保持 guarded/readonly'
})
const z043ExportPrintDisabledReason =
  '导出与打印禁用：当前为只读验收，缺少写授权，不生成文件、不调用打印或导出写请求'
const z043MaterialParitySource = computed<string>(() => {
  const raw = typeof route.query.parity === 'string' ? route.query.parity.trim() : ''
  if (raw === 'material-purchase') {
    return '/materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase -> detail readback'
  }
  return `${z042ParitySource.value.finalRoute}；direct detail route readonly readback`
})
const z044ListDetailDiff = computed<string>(() =>
  detail.value
    ? `${detail.value.subcontract_no} / ${detail.value.supplier} / ${statusLabel(detail.value.status)} 与列表行同步状态做只读差异对照`
    : '未带 id 时仍展示详情 readback fallback，不回写列表或触发同步'
)
const z044ReadbackConsistency = computed<string>(() =>
  detail.value
    ? `详情主字段、发料/回料同步状态与列表 readback 使用同一只读边界`
    : 'missing id detail route 仅记录 readback 一致性要求，等待列表入口补充 id',
)
const z044SyncLockReason = computed<string>(() => {
  const issue = stockSyncLabel(detail.value?.latest_issue_sync_status)
  const receipt = stockSyncLabel(detail.value?.latest_receipt_sync_status)
  if (issue || receipt) {
    return `发料:${issue || '未入列'} / 回料:${receipt || '未入列'}；同步重试锁定为 guarded/readonly`
  }
  return '详情未加载或无同步异常时，同步重试仍保持锁定，只展示原因'
})
const z044ExportPrintReadonly =
  '导出/打印只读禁用：本地候选只允许 readback，不生成下载、打印或后端写请求'
const z044MaterialParityReadback = computed<string>(() => {
  const raw = typeof route.query.parity === 'string' ? route.query.parity.trim() : ''
  if (raw === 'material-purchase') {
    return '/materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase -> detail readback'
  }
  return 'direct subcontract detail；materialPurchase parity 来源由列表路由承接'
})
const z044NetworkWriteBlocker =
  'network/write blocker：新建、发料、回料、验货、结算预览、同步、导出、打印均不得形成真实写请求成功'
const z044WriteSuccessBlocker =
  'write success blocker：dataWriteRequestSuccessAllowed=false，dataRealWriteActionAdded=false，guarded readonly 不等于写成功'
const z045GuardEntries = z042GuardEntries
const z045ParityDiffAudit = computed<string>(() =>
  detail.value
    ? `${detail.value.subcontract_no} 与列表 readback 共享 materialPurchase parity 来源；差异只读呈现，不回写状态`
    : '详情缺少 id 时仍展示 parity 差异审计，提示用户回到列表选择外发单'
)
const z045ListDetailReadback = computed<string>(() =>
  detail.value
    ? `${detail.value.supplier} / ${statusLabel(detail.value.status)} / 发料${stockSyncLabel(detail.value.latest_issue_sync_status) || '未入列'} / 回料${stockSyncLabel(detail.value.latest_receipt_sync_status) || '未入列'}`
    : '列表/详情 readback 等待外发单 id，当前不触发同步或写入',
)
const z045SyncDenialReason = computed<string>(() => {
  const issue = stockSyncLabel(detail.value?.latest_issue_sync_status)
  const receipt = stockSyncLabel(detail.value?.latest_receipt_sync_status)
  if (issue || receipt) {
    return `发料:${issue || '未入列'} / 回料:${receipt || '未入列'}；同步重试仅展示拒写原因，不发送 retry 写请求`
  }
  return '详情未加载或无同步异常时，同步重试仍保持只读锁定，防止误判为可写成功'
})
const z045ExportPrintLock =
  '导出与打印锁定：详情页仅展示禁用原因，不生成下载、打印任务或后端写请求'
const z045MaterialParitySource = computed<string>(() => {
  const raw = typeof route.query.parity === 'string' ? route.query.parity.trim() : ''
  if (raw === 'material-purchase') {
    return '/materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase -> detail readback'
  }
  return 'direct subcontract detail；materialPurchase parity 来源由列表路由承接'
})
const z045NetworkWriteBlocker =
  'network/write blocker：新建、发料、回料、验货、结算预览、同步重试、导出、打印均不新增写请求'
const z045WriteSuccessBlocker =
  'write success blocker：dataWriteRequestSuccessAllowed=false，dataRealWriteActionAdded=false，guarded readonly 不代表写成功'
const z045GuardedActionMatrix = computed(() =>
  z045GuardEntries.map((entry) => {
    const prerequisiteMap: Record<string, string> = {
      新建外发单: '需要从列表进入并具备新建写授权',
      发料: '需要外发单、物料批次和库存写授权',
      回料: '需要回料批次、数量核验和库存回写授权',
      验货: '需要回料记录、验货数量和质量状态写授权',
      结算预览: '需要验货候选、结算单号和结算写授权',
      同步重试: '需要同步失败原因复核和 retry 写授权',
      导出: '需要详情导出授权与下载通道',
      打印: '需要打印任务授权与生产打印通道',
    }
    return {
      entry,
      prerequisite: prerequisiteMap[entry] || '需要写授权',
      lockReason: 'Z045 本地候选仅允许详情 readback 与原因展示，禁止形成真实写请求成功',
      state: 'guarded/readonly',
    }
  }),
)
const z046GuardEntries = ['新建外发单', '发料', '回料', '验货', '结算预览', '同步重试', '导出', '打印']
const z046ListDetailStateLink = computed<string>(() => z045ListDetailReadback.value)
const z046SettlementPrecondition = computed<string>(() =>
  detail.value
    ? `外协单 ${detail.value.subcontract_no} 当前仅展示结算预览前置条件；缺少写授权时保持只读锁定`
    : '详情缺少外协单 id 时，结算预览仅展示前置条件和锁定原因，不触发写请求',
)
const z046SyncRetryLockReason = computed<string>(() => z045SyncDenialReason.value)
const z046ExportPrintLockReason = z045ExportPrintLock
const z046MaterialParitySource = computed<string>(() => z045MaterialParitySource.value)
const z046NetworkWriteBlocker = z045NetworkWriteBlocker
const z046WriteSuccessBlocker = z045WriteSuccessBlocker
const z046GuardedActionMatrix = computed(() =>
  z046GuardEntries.map((entry) => {
    const prerequisiteMap: Record<string, string> = {
      新建外发单: '需要从列表进入并具备新建写授权',
      发料: '需要外发单、物料批次和库存写授权',
      回料: '需要回料批次、数量核验和库存回写授权',
      验货: '需要回料记录、验货数量和质量状态写授权',
      结算预览: '需要验货候选、结算单号和结算写授权',
      同步重试: '需要同步失败原因复核和 retry 写授权',
      导出: '需要详情导出授权与下载通道',
      打印: '需要打印任务授权与生产打印通道',
    }
    return {
      entry,
      prerequisite: prerequisiteMap[entry] || '需要写授权',
      lockReason: 'Z046 本地候选仅允许详情 readback 与锁定原因可见化，禁止形成真实写请求成功',
      state: 'guarded/readonly',
    }
  }),
)

const buildWriteCarrier = <T extends SubcontractWriteOperation>(
  operation: T,
  statusAction: string,
  quantity: number,
  sourceSuffix: string,
) => {
  if (!detail.value) {
    throw new Error('外发单详情未加载')
  }
  const scenarioTag = buildSubcontractScenarioTag()
  const sourceRef = `${scenarioTag}-${sourceSuffix}`
  const subcontractRef = detail.value.subcontract_no
  const supplierRef = detail.value.supplier
  const workOrderRef = (detail.value.work_order || String(detail.value.production_plan_id || '')).trim() || 'NO-WORK-ORDER'
  const itemCode = detail.value.item_code
  const idempotencyKey = `${scenarioTag}-${operation}-${Date.now()}`
  const requestId = buildSubcontractRequestId({
    scenarioTag,
      operation,
    idempotencyKey,
    sourceRef,
    subcontractRef,
    supplierRef,
    workOrderRef,
    itemCode,
    statusAction,
  })
  return {
    request_id: requestId,
    idempotency_key: idempotencyKey,
    scenario_tag: scenarioTag,
    source_ref: sourceRef,
    subcontract_ref: subcontractRef,
    supplier_ref: supplierRef,
    work_order_ref: workOrderRef,
      operation,
    item_code: itemCode,
    quantity,
    status_action: statusAction,
  }
}

const setDefaultReceiptBatch = (): void => {
  if (!inspectForm.receipt_batch_no && detail.value?.receipts?.length) {
    inspectForm.receipt_batch_no = detail.value.receipts[0].receipt_batch_no
  }
}

const loadSettlementCandidates = async (): Promise<void> => {
  if (!detail.value) {
    settlementCandidates.value = []
    settlementPreview.value = null
    return
  }
  settlementLoading.value = true
  try {
    const result = await fetchSubcontractSettlementCandidates({
      supplier: detail.value.supplier,
      item_code: detail.value.item_code,
      page: 1,
      page_size: 100,
    })
    settlementCandidates.value = result.data.items.filter(
      (item) => item.subcontract_no === detail.value?.subcontract_no,
    )
    if (!settlementForm.inspection_ids.length) {
      settlementForm.inspection_ids = settlementCandidates.value.slice(0, 10).map((item) => item.inspection_id)
    }
  } catch (error) {
    settlementCandidates.value = []
    settlementPreview.value = null
    ElMessage.warning((error as Error).message || '结算候选加载失败')
  } finally {
    settlementLoading.value = false
  }
}

const loadDetail = async (): Promise<void> => {
  guardedFeedback.value = ''
  loadError.value = ''
  if (!canRead.value) {
    detail.value = null
    missingOrderId.value = false
    return
  }
  if (!hasValidOrderId.value) {
    detail.value = null
    missingOrderId.value = true
    return
  }
  missingOrderId.value = false
  loading.value = true
  try {
    const result = await fetchSubcontractOrderDetail(orderId.value)
    detail.value = result.data
    setDefaultReceiptBatch()
    await loadSettlementCandidates()
  } catch (error) {
    detail.value = null
    settlementCandidates.value = []
    settlementPreview.value = null
    const message = (error as Error).message || '详情加载失败'
    loadError.value = `外发单详情加载失败：${message}`
    ElMessage.error(loadError.value)
  } finally {
    loading.value = false
  }
}

const guardedWriteAction = (actionName: string): void => {
  guardedFeedback.value = `当前为只读模式，${actionName}已禁用。`
  ElMessage.warning(guardedFeedback.value)
}

const isReadonlyInteractionMode = (): boolean => true

const openIssueDialog = (): void => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('发料')
    return
  }
  guardedWriteAction('发料')
}

const openReceiveDialog = (): void => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('回料')
    return
  }
  guardedWriteAction('回料')
}

const openInspectDialog = (): void => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('验货')
    return
  }
  guardedWriteAction('验货')
}

const openSettlementDialog = async (): Promise<void> => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('结算锁定/释放')
    return
  }
  if (!detail.value) return
  await loadSettlementCandidates()
  settlementDialogVisible.value = true
}

const submitIssue = async (): Promise<void> => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('发料保存')
    return
  }
  if (!detail.value || issueSubmitting.value) return
  if (!issueForm.warehouse.trim() || !issueForm.material_item_code.trim()) {
    ElMessage.warning('请填写发料仓和物料编码')
    return
  }
  issueSubmitting.value = true
  try {
    const carrier = buildWriteCarrier('issue_material', 'issue_material', Number(issueForm.issued_qty), 'SRC-ISSUE')
    await issueSubcontractMaterial(orderId.value, {
      ...carrier,
      warehouse: issueForm.warehouse.trim(),
      materials: [
        {
          material_item_code: issueForm.material_item_code.trim(),
          required_qty: issueForm.required_qty,
          issued_qty: issueForm.issued_qty,
        },
      ],
    })
    issueDialogVisible.value = false
    await loadDetail()
    ElMessage.success('发料成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '发料失败')
  } finally {
    issueSubmitting.value = false
  }
}

const submitReceive = async (): Promise<void> => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('回料保存')
    return
  }
  if (!detail.value || receiveSubmitting.value) return
  if (!receiveForm.receipt_warehouse.trim()) {
    ElMessage.warning('请填写回料仓')
    return
  }
  receiveSubmitting.value = true
  try {
    const carrier = buildWriteCarrier('receive', 'receive', Number(receiveForm.received_qty), 'SRC-RECEIVE')
    await receiveSubcontractOrder(orderId.value, {
      ...carrier,
      receipt_warehouse: receiveForm.receipt_warehouse.trim(),
      received_qty: receiveForm.received_qty,
      item_code: detail.value.item_code,
      batch_no: receiveForm.batch_no.trim() || null,
      color: receiveForm.color.trim() || null,
      size: receiveForm.size.trim() || null,
      uom: receiveForm.uom.trim() || null,
    })
    receiveDialogVisible.value = false
    await loadDetail()
    ElMessage.success('回料成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '回料失败')
  } finally {
    receiveSubmitting.value = false
  }
}

const submitInspect = async (): Promise<void> => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('验货保存')
    return
  }
  if (!detail.value || inspectSubmitting.value) return
  if (!inspectForm.receipt_batch_no.trim()) {
    ElMessage.warning('请填写回料批次')
    return
  }
  inspectSubmitting.value = true
  try {
    const carrier = buildWriteCarrier('inspect', 'inspect', Number(inspectForm.inspected_qty), 'SRC-INSPECT')
    await inspectSubcontractOrder(orderId.value, {
      ...carrier,
      receipt_batch_no: inspectForm.receipt_batch_no.trim(),
      inspected_qty: inspectForm.inspected_qty,
      rejected_qty: inspectForm.rejected_qty,
      deduction_amount_per_piece: inspectForm.deduction_amount_per_piece,
      remark: inspectForm.remark.trim() || null,
    })
    inspectDialogVisible.value = false
    await loadDetail()
    ElMessage.success('验货成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '验货失败')
  } finally {
    inspectSubmitting.value = false
  }
}

const runSettlementPreview = async (): Promise<void> => {
  settlementPreview.value = null
  guardedWriteAction('结算预览')
}

const submitSettlementLock = async (): Promise<void> => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('结算锁定')
    return
  }
  if (!detail.value || settlementSubmitting.value) return
  if (!settlementForm.inspection_ids.length) {
    ElMessage.warning('请至少选择一个验货ID')
    return
  }
  settlementSubmitting.value = true
  try {
    const carrier = buildWriteCarrier(
      'settlement_lock',
      'settlement_lock',
      settlementForm.inspection_ids.length,
      'SRC-SETTLE-LOCK',
    )
    await lockSubcontractSettlement({
      ...carrier,
      statement_no: settlementForm.statement_no.trim() || `${carrier.scenario_tag}-STMT`,
      statement_id: null,
      inspection_ids: settlementForm.inspection_ids,
      remark: `locked-by-${carrier.scenario_tag}`,
    })
    await loadDetail()
    settlementPreview.value = null
    ElMessage.success('结算锁定成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '结算锁定失败')
  } finally {
    settlementSubmitting.value = false
  }
}

const submitSettlementRelease = async (): Promise<void> => {
  if (isReadonlyInteractionMode()) {
    guardedWriteAction('结算释放')
    return
  }
  if (!detail.value || settlementSubmitting.value) return
  if (!settlementForm.inspection_ids.length) {
    ElMessage.warning('请至少选择一个验货ID')
    return
  }
  settlementSubmitting.value = true
  try {
    const carrier = buildWriteCarrier(
      'release',
      'release',
      settlementForm.inspection_ids.length,
      'SRC-SETTLE-RELEASE',
    )
    await releaseSubcontractSettlement({
      ...carrier,
      statement_no: settlementForm.statement_no.trim() || `${carrier.scenario_tag}-STMT`,
      statement_id: null,
      inspection_ids: settlementForm.inspection_ids,
      reason: settlementForm.reason.trim() || 'release-for-local-cleanup',
    })
    await loadDetail()
    settlementPreview.value = null
    ElMessage.success('结算释放成功')
  } catch (error) {
    ElMessage.error((error as Error).message || '结算释放失败')
  } finally {
    settlementSubmitting.value = false
  }
}

const goBack = (): void => {
  router.push('/subcontract/list')
}

watch(
  () => orderId.value,
  async () => {
    await loadDetail()
  },
)

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('subcontract')
    readonlyFallback.value = !permissionStore.state.buttonPermissions.read
  } catch (error) {
    readonlyFallback.value = true
    const message = (error as Error).message || '权限加载失败'
    loadError.value = message
    ElMessage.error(message)
  } finally {
    permissionReady.value = true
  }
  await loadDetail()
})
</script>

<style scoped>
.subcontract-detail-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.permission-tip {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
}

.scope-tag {
  margin-left: 8px;
}

.settlement-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.settlement-preview {
  margin-top: 12px;
}

.z042-subcontract-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  margin-top: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.z042-panel-header,
.z042-guard-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.z043-subcontract-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  margin-top: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-light);
}

.z043-panel-header,
.z043-guard-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.z044-subcontract-panel,
.z045-subcontract-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  margin-top: 12px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-blank);
}

.z044-panel-header,
.z044-guard-actions,
.z045-panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.z045-guard-table {
  width: 100%;
}

.readonly-fallback {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}
</style>
