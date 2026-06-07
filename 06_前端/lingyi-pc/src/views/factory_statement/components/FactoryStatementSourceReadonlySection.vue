<template>
  <section class="source-shell" data-testid="factory-statement-source-readonly-section">
    <div class="source-header">
      <div class="title-group">
        <span class="title">工厂对账来源链断点（只读）</span>
        <span class="note">{{ summary.sourceScopeLabel }}</span>
      </div>
      <div class="header-tags">
        <el-tag effect="plain" data-testid="factory-statement-source-get-only">GET-only</el-tag>
        <el-tag
          type="info"
          effect="plain"
          data-testid="factory-statement-source-query-state"
        >
          {{ summary.queryStateLabel }}
        </el-tag>
        <el-tag
          :type="summary.parityTone"
          effect="plain"
          data-testid="factory-statement-source-parity-tag"
        >
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag
          type="success"
          effect="plain"
          data-testid="factory-statement-source-focus-tag"
        >
          {{ summary.focusLabel }}
        </el-tag>
        <el-tag
          type="warning"
          effect="plain"
          data-testid="factory-statement-source-readonly-guard"
          data-write-guard="readonly:factory-statement-source-parity"
          data-guard-state="guarded_readonly"
        >
          readonly guard
        </el-tag>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      :title="summary.sourceBreakpointSummary"
      data-testid="factory-statement-source-breakpoint-summary"
    />

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.billDriftSummary"
      data-testid="factory-statement-bill-drift-summary"
    />

    <el-descriptions border :column="1" class="route-scope" data-testid="factory-statement-source-route-scope">
      <el-descriptions-item
        v-for="item in summary.routeItems"
        :key="item.key"
        :label="item.label"
      >
        <span :data-testid="`factory-statement-source-route-${item.key}`">{{ item.route }}</span>
        <el-tag
          size="small"
          effect="plain"
          :type="item.active ? 'success' : 'info'"
          style="margin-left: 8px"
        >
          {{ item.active ? 'active' : 'readonly' }}
        </el-tag>
        <span class="route-note">{{ item.note }}</span>
      </el-descriptions-item>
    </el-descriptions>

    <div class="summary-grid" data-testid="factory-statement-source-cards">
      <div v-for="field in cardFields" :key="field.key" class="summary-card">
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summary.cardValues[field.key] }}</strong>
      </div>
    </div>

    <el-table
      :data="summary.driftRows"
      border
      empty-text="暂无来源链断点数据"
      data-testid="factory-statement-source-drift-table"
    >
      <el-table-column prop="label" label="来源链项" min-width="220" />
      <el-table-column label="状态" width="120">
        <template #default="scope">
          <el-tag :type="statusTagType(scope.row.status)" effect="plain">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="summary" label="摘要" min-width="280" />
      <el-table-column prop="recommendation" label="只读建议" min-width="320" />
    </el-table>

    <div class="guard-grid" data-testid="factory-statement-source-guard-grid">
      <div
        v-for="action in guardActions"
        :key="action.key"
        class="guard-item"
        :data-testid="`factory-statement-source-guard-${action.key}`"
      >
        <div class="guard-label">{{ action.label }}</div>
        <el-button size="small" disabled>{{ action.label }}</el-button>
        <div class="guard-hint">{{ action.reason }}</div>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="factory-statement-source-guard-reason"
    />

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="factory-statement-source-remaining-gap"
    />

  </section>
</template>

<script setup lang="ts">
import type { FactoryStatementSourceReadonlySummary } from '@/views/factory_statement/composables/useFactoryStatementSourceReadonly'
import {
  FACTORY_STATEMENT_SOURCE_CARD_FIELDS,
  FACTORY_STATEMENT_SOURCE_GUARD_ACTIONS,
  type FactoryStatementSourceReadonlyStatus,
} from '@/views/factory_statement/constants/factoryStatementSourceFields'

defineProps<{
  summary: FactoryStatementSourceReadonlySummary
}>()

const cardFields = FACTORY_STATEMENT_SOURCE_CARD_FIELDS
const guardActions = FACTORY_STATEMENT_SOURCE_GUARD_ACTIONS

const statusTagType = (status: FactoryStatementSourceReadonlyStatus): 'success' | 'warning' | 'danger' => {
  if (status === 'ok') {
    return 'success'
  }
  if (status === 'warn') {
    return 'warning'
  }
  return 'danger'
}
</script>

<style scoped>
.source-shell {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 15px;
  font-weight: 600;
}

.note,
.summary-label,
.guard-hint,
.route-note {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.route-scope {
  margin-top: 4px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.summary-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--el-fill-color-blank);
}

.summary-value {
  font-size: 16px;
  line-height: 1.2;
  color: var(--el-text-color-primary);
}

.guard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.guard-item {
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guard-label {
  font-size: 13px;
  font-weight: 600;
}
</style>
