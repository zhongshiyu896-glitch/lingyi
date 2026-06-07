<template>
  <section class="followup-shell" data-testid="cand458-production-followup-readonly-section">
    <div class="followup-header">
      <div class="title-group">
        <span class="title">生产跟进模板 source readonly 回读</span>
        <span class="note" data-testid="cand458-production-followup-query-state">
          {{ summary.queryStateLabel }}
        </span>
      </div>
      <div class="header-tags">
        <el-tag
          :type="summary.parityTone"
          effect="plain"
          data-testid="cand458-production-followup-marker-parity"
        >
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag
          :type="summary.focusTone"
          effect="plain"
          data-testid="cand458-production-followup-marker-focus"
        >
          {{ summary.focusLabel }}
        </el-tag>
        <el-tag
          :type="summary.templateStatusTone"
          effect="plain"
          data-testid="cand458-production-followup-template-status"
        >
          {{ summary.templateStatusLabel }}
        </el-tag>
        <el-tag
          :type="summary.sourceStatusTone"
          effect="plain"
          data-testid="cand458-production-followup-source-status"
        >
          {{ summary.sourceStatusLabel }}
        </el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div v-for="card in summary.cards" :key="card.key" class="summary-card">
        <span class="summary-label">{{ card.label }}</span>
        <strong class="summary-value">{{ card.value }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.blockedReason"
      data-testid="cand458-production-followup-blocked-reason"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="cand458-production-followup-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="cand458-production-followup-remaining-gap"
    />

    <el-descriptions border :column="2" class="followup-descriptions">
      <el-descriptions-item label="写入边界">
        <span data-testid="cand458-production-followup-write-boundary">
          {{ summary.writeBoundary }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="来源状态">
        <span data-testid="cand458-production-followup-source-status-text">
          {{ summary.sourceStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="条目/状态">
        <span data-testid="cand458-production-followup-item-status">
          {{ summary.itemStatusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="聚焦来源">
        <span data-testid="cand458-production-followup-focus-text">
          {{ summary.focusLabel }}
        </span>
      </el-descriptions-item>
      <el-descriptions-item label="模板状态">{{ summary.templateStatusLabel }}</el-descriptions-item>
      <el-descriptions-item label="异常快照">{{ summary.progressStatusLabel }}</el-descriptions-item>
    </el-descriptions>

    <div class="guarded-actions" data-testid="cand458-production-followup-guarded-actions">
      <el-button
        v-for="action in summary.disabledActions"
        :key="action.label"
        disabled
        type="info"
        plain
        data-action-type="write"
        data-guard-state="disabled"
        :title="action.reason"
      >
        {{ action.label }}
      </el-button>
    </div>

    <el-table
      :data="summary.items"
      border
      size="small"
      empty-text="暂无生产跟进只读条目"
      data-testid="cand458-production-followup-item-table"
    >
      <el-table-column prop="subjectLabel" label="条目" min-width="180" />
      <el-table-column prop="statusLabel" label="状态" min-width="160" />
      <el-table-column prop="sourceLabel" label="来源" min-width="200" />
      <el-table-column prop="blockedReason" label="阻断原因" min-width="240" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import type { ProductionFollowupReadonlySummary } from '@/views/production/composables/useProductionFollowupReadonly'

defineProps<{
  summary: ProductionFollowupReadonlySummary
}>()
</script>

<style scoped>
.followup-shell {
  margin: 12px 0 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.followup-header {
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
.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags,
.guarded-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
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

.followup-descriptions :deep(.el-descriptions__label) {
  width: 120px;
}
</style>
