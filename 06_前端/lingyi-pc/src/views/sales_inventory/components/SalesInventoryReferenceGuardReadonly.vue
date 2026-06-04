<template>
  <section class="guard-shell" data-testid="cand158-reference-guard-readonly">
    <div class="guard-header">
      <div class="title-group">
        <span class="title">来源校验 / parity 守卫</span>
        <span class="note">{{ summary.readonlySourceTag }}</span>
      </div>
      <div class="header-tags">
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
      :title="summary.readonlyGuardReason"
      data-testid="cand158-reference-readonly-guard"
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
        create / update / delete / export disabled
      </el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<script setup lang="ts">
import type { SalesInventoryReferenceGuardSummary } from '@/api/sales_inventory_references'
import {
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
    case 'verifiedCount':
      return String(props.summary.verifiedCount)
    case 'fallbackCount':
      return String(props.summary.fallbackCount)
    case 'missingCount':
      return String(props.summary.missingCount)
    case 'parityScopeLabel':
      return props.summary.parityScopeLabel
    default:
      return '-'
  }
}
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
</style>
