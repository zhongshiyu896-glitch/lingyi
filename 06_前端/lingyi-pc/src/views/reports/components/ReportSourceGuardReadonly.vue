<template>
  <el-card shadow="never" class="source-guard-shell" data-testid="report-source-guard-readonly-section">
    <template #header>
      <div class="header-row">
        <span>报表目录 source-guard（只读）</span>
        <div class="header-tags">
          <el-tag :type="summary.routeStateTone" effect="plain">{{ summary.routeStateLabel }}</el-tag>
          <el-tag :type="summary.parityTagTone" effect="plain">{{ summary.parityTagLabel }}</el-tag>
          <el-tag type="info" effect="plain">{{ summary.sourceEntryLabel }}</el-tag>
        </div>
      </div>
    </template>

    <el-alert
      type="info"
      :closable="false"
      title="source-guard query state"
      :description="`route=${summary.routeLabel} / source_entry=${summary.sourceEntryLabel}`"
      data-testid="report-source-guard-query-state"
      style="margin-bottom: 12px"
    />

    <div class="summary-grid" data-testid="report-source-guard-summary-grid">
      <div v-for="card in summary.summaryCards" :key="card.key" class="summary-card">
        <span class="summary-label">{{ card.label }}</span>
        <el-tag :type="card.tone" effect="plain">{{ card.value }}</el-tag>
        <div class="summary-hint">{{ card.hint }}</div>
      </div>
    </div>

    <div class="parity-grid" data-testid="report-source-guard-parity-grid">
      <div v-for="line in summary.parityLines" :key="line.key" class="parity-item">
        <span class="parity-label">{{ line.label }}</span>
        <el-tag :type="line.tone" effect="plain">{{ line.value }}</el-tag>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      title="blocked reason"
      :description="summary.blockedReasons.join('；')"
      data-testid="report-source-guard-blocked-reason"
      style="margin-top: 12px"
    />

    <el-alert
      type="info"
      :closable="false"
      title="readonly guard"
      :description="summary.readonlyGuardText"
      data-testid="report-source-guard-readonly-guard"
      style="margin-top: 12px"
    />

    <el-collapse class="source-items" data-testid="report-source-guard-source-items">
      <el-collapse-item
        v-for="item in summary.sourceItems"
        :key="item.key"
        :name="item.key"
        :title="item.title"
        :data-testid="`report-source-guard-item-${item.key}`"
      >
        <div class="item-meta">
          <el-tag :type="item.tone" effect="plain">{{ item.status }}</el-tag>
          <el-tag type="info" effect="plain">source={{ item.source }}</el-tag>
        </div>
        <div class="item-summary">{{ item.summary }}</div>
        <ul class="item-details">
          <li v-for="detail in item.details" :key="detail">{{ detail }}</li>
        </ul>
      </el-collapse-item>
    </el-collapse>

    <div class="disabled-actions" data-testid="report-source-guard-disabled-actions">
      <div class="disabled-title">disabled / non-executable actions</div>
      <div class="disabled-grid">
        <div v-for="action in summary.disabledActions" :key="action.key" class="disabled-item">
          <el-button disabled type="warning" plain>{{ action.label }}</el-button>
          <div class="disabled-reason">{{ action.reason }}</div>
        </div>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      title="remaining_gap"
      :description="summary.remainingGap"
      data-testid="report-source-guard-remaining-gap"
      style="margin-top: 12px"
    />
  </el-card>
</template>

<script setup lang="ts">
import type { ReportSourceGuardReadonlyModel } from '../composables/useReportSourceGuardReadonly'

defineProps<{
  summary: ReportSourceGuardReadonlyModel
}>()
</script>

<style scoped>
.source-guard-shell {
  margin-bottom: 12px;
}

.header-row,
.header-tags,
.item-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-grid,
.parity-grid,
.disabled-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.summary-card,
.parity-item,
.disabled-item {
  min-height: 88px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.summary-label,
.parity-label,
.disabled-title {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.summary-hint,
.disabled-reason,
.item-summary,
.item-details {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.source-items,
.disabled-actions {
  margin-top: 12px;
}

.item-details {
  padding-left: 18px;
}

@media (max-width: 768px) {
  .summary-grid,
  .parity-grid,
  .disabled-grid {
    grid-template-columns: 1fr;
  }
}
</style>
