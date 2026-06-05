<template>
  <section class="guard-shell" data-testid="cand158-reference-guard-readonly">
    <div class="guard-header">
      <div class="title-group">
        <span class="title">销售库存引用桥与 parity 守卫</span>
        <span class="note">{{ summary.readonlySourceTag }}</span>
      </div>
      <div class="header-tags">
        <el-tag effect="plain">GET-only</el-tag>
        <el-tag
          :type="SALES_INVENTORY_REFERENCE_SOURCE_TAGS[summary.sourceValidationState]"
          effect="plain"
        >
          {{ summary.sourceValidationLabel }}
        </el-tag>
        <el-tag
          :type="SALES_INVENTORY_REFERENCE_PARITY_TAGS[summary.parityGuardState]"
          effect="plain"
        >
          {{ summary.parityGuardLabel }}
        </el-tag>
        <el-tag type="warning" effect="plain">readonly guard</el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div
        v-for="field in SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS"
        :key="field.key"
        class="summary-card"
      >
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      :title="summary.bridgeRows[0]?.summary || summary.readonlyGuardReason"
      data-testid="sales-inventory-reference-bridge-summary"
    />

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.blockedReason"
      data-testid="sales-inventory-reference-blocked-reason"
    />

    <el-alert
      v-if="summary.missingSourcePrompt"
      type="warning"
      :closable="false"
      :title="summary.missingSourcePrompt"
      data-testid="cand158-reference-missing-source-prompt"
    />

    <el-descriptions
      border
      :column="1"
      class="guard-descriptions"
      data-testid="sales-inventory-reference-route-scope"
    >
      <el-descriptions-item
        v-for="item in summary.routeItems"
        :key="item.key"
        :label="item.label"
      >
        <span>{{ item.route }}</span>
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

    <el-table
      :data="summary.bridgeRows"
      border
      empty-text="暂无引用桥摘要"
      data-testid="sales-inventory-reference-bridge-rows"
    >
      <el-table-column prop="label" label="引用桥项" min-width="180" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="bridgeStatusTagType(row.status)" effect="plain">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="summary" label="摘要" min-width="280" />
      <el-table-column prop="recommendation" label="只读建议" min-width="280" />
    </el-table>

    <el-descriptions
      border
      :column="3"
      class="guard-descriptions"
      data-testid="cand158-reference-guard-summary"
    >
      <el-descriptions-item label="active_tab">
        {{ summary.activeTab === 'customers' ? 'customers' : 'suppliers' }}
      </el-descriptions-item>
      <el-descriptions-item label="parity_guard">{{ summary.parityGuardLabel }}</el-descriptions-item>
      <el-descriptions-item label="source_state">{{ summary.sourceValidationLabel }}</el-descriptions-item>
      <el-descriptions-item label="readonly_tag">{{ summary.readonlySourceTag }}</el-descriptions-item>
      <el-descriptions-item label="missing_prompt">
        {{ summary.missingSourcePrompt || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="write_boundary">
        order write / inventory adjust / export disabled
      </el-descriptions-item>
    </el-descriptions>

    <div class="guard-grid" data-testid="sales-inventory-reference-guard-actions">
      <div
        v-for="action in SALES_INVENTORY_REFERENCE_GUARD_ACTIONS"
        :key="action.key"
        class="guard-item"
      >
        <div class="guard-label">{{ action.label }}</div>
        <el-button size="small" disabled data-action-type="write" data-guard-state="disabled">
          {{ action.label }}
        </el-button>
        <div class="guard-hint">{{ action.reason }}</div>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="cand158-reference-readonly-guard"
    />

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="sales-inventory-reference-remaining-gap"
    />
  </section>
</template>

<script setup lang="ts">
import type {
  SalesInventoryReferenceBridgeStatus,
  SalesInventoryReferenceGuardSummary,
} from '@/api/sales_inventory_references'
import {
  SALES_INVENTORY_REFERENCE_BRIDGE_TAGS,
  SALES_INVENTORY_REFERENCE_GUARD_ACTIONS,
  SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS,
  SALES_INVENTORY_REFERENCE_PARITY_TAGS,
  SALES_INVENTORY_REFERENCE_SOURCE_TAGS,
} from '@/views/sales_inventory/constants/salesInventoryReferenceGuardFields'

const props = defineProps<{
  summary: SalesInventoryReferenceGuardSummary
}>()

const summaryValue = (
  key: (typeof SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS)[number]['key'],
): string => {
  switch (key) {
    case 'queryScope':
      return props.summary.cardValues.queryScope
    case 'bridgeNodes':
      return props.summary.cardValues.bridgeNodes
    case 'blockedCount':
      return props.summary.cardValues.blockedCount
    case 'sourceState':
      return props.summary.cardValues.sourceState
    default:
      return '-'
  }
}

const bridgeStatusTagType = (status: SalesInventoryReferenceBridgeStatus) =>
  SALES_INVENTORY_REFERENCE_BRIDGE_TAGS[status]
</script>

<style scoped>
.guard-shell {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.guard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.note,
.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.route-note,
.guard-hint,
.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
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
  font-size: 18px;
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
