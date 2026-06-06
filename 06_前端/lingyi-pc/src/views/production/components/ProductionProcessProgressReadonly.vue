<template>
  <section class="process-shell" data-testid="production-process-progress-readonly">
    <div class="process-header">
      <div class="title-group">
        <span class="title">工序进度 / Job Card 状态镜像</span>
        <span class="note">{{ summary.sourceLabel }}</span>
      </div>
      <div class="header-tags">
        <el-tag :type="summary.processProgressTone" effect="plain" data-testid="production-process-parity-tag">
          {{ summary.processProgressLabel }}
        </el-tag>
        <el-tag :type="summary.jobCardMirrorTone" effect="plain" data-testid="production-process-mirror-tag">
          {{ summary.jobCardMirrorLabel }}
        </el-tag>
        <el-tag :type="summary.blockedReasonTone" effect="plain" data-testid="production-process-blocked-tag">
          {{ summary.blockedReasonLabel }}
        </el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div v-for="field in PRODUCTION_PROCESS_PROGRESS_METRIC_FIELDS" :key="field.key" class="summary-card">
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="production-process-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="production-process-remaining-gap"
    />

    <el-descriptions border :column="3" class="process-descriptions">
      <el-descriptions-item label="当前入口">{{ summary.parityScopeLabel }}</el-descriptions-item>
      <el-descriptions-item label="production-process parity">{{ summary.processProgressLabel }}</el-descriptions-item>
      <el-descriptions-item label="工序状态镜像">{{ summary.jobCardMirrorLabel }}</el-descriptions-item>
      <el-descriptions-item label="阻断提示">{{ summary.blockedReasonLabel }}</el-descriptions-item>
      <el-descriptions-item label="只读 guard">job-card sync / export / worker disabled</el-descriptions-item>
      <el-descriptions-item label="remaining_gap">{{ summary.remainingGap }}</el-descriptions-item>
    </el-descriptions>

    <div class="blocked-actions" data-testid="production-process-blocked-actions">
      <div
        v-for="action in PRODUCTION_PROCESS_PROGRESS_BLOCKED_ACTIONS"
        :key="action.label"
        class="blocked-action"
      >
        <el-button disabled>{{ action.label }}</el-button>
        <span class="blocked-reason">{{ action.reason }}</span>
      </div>
    </div>

    <el-table
      :data="summary.items"
      border
      size="small"
      empty-text="暂无工序进度只读快照"
      data-testid="production-process-progress-readonly-table"
    >
      <el-table-column prop="subjectLabel" label="主体" min-width="220" />
      <el-table-column prop="statusLabel" label="状态" min-width="130" />
      <el-table-column prop="progressLabel" label="进度" min-width="120" />
      <el-table-column prop="mirrorLabel" label="镜像状态" min-width="160" />
      <el-table-column prop="blockedReason" label="阻断原因" min-width="220" />
    </el-table>
  </section>
</template>

<script setup lang="ts">
import type { ProductionProcessProgressReadonlySummary } from '@/views/production/composables/useProductionProcessProgressReadonly'
import {
  PRODUCTION_PROCESS_PROGRESS_BLOCKED_ACTIONS,
  PRODUCTION_PROCESS_PROGRESS_METRIC_FIELDS,
  type ProductionProcessProgressMetricKey,
} from '@/views/production/constants/productionProcessProgressFields'

const props = defineProps<{
  summary: ProductionProcessProgressReadonlySummary
}>()

const summaryValue = (key: ProductionProcessProgressMetricKey): string => {
  switch (key) {
    case 'mirroredJobCardCount':
      return String(props.summary.mirroredJobCardCount)
    case 'syncPendingCount':
      return String(props.summary.syncPendingCount)
    case 'blockedCount':
      return String(props.summary.blockedCount)
    case 'statusSnapshot':
      return props.summary.statusSnapshot
    default:
      return '-'
  }
}
</script>

<style scoped>
.process-shell {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.process-header {
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
  font-size: 16px;
  font-weight: 600;
}

.note,
.summary-label,
.blocked-reason {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags,
.blocked-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
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
  font-size: 18px;
}

.blocked-action {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
</style>
