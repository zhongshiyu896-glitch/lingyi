<template>
  <section class="parity-shell" data-testid="production-order-parity-readonly">
    <div class="parity-header">
      <div class="title-group">
        <span class="title">生产订单 parity / 工序状态镜像</span>
        <span class="note">{{ summary.sourceLabel }}</span>
      </div>
      <div class="header-tags">
        <el-tag :type="summary.parityTone" effect="plain" data-testid="production-order-parity-tag">
          {{ summary.parityLabel }}
        </el-tag>
        <el-tag
          :type="summary.processStatusTone"
          effect="plain"
          data-testid="production-order-process-status"
        >
          {{ summary.processStatusLabel }}
        </el-tag>
        <el-tag
          :type="summary.downstreamGuardTone"
          effect="plain"
          data-testid="production-order-downstream-guard-tag"
        >
          {{ summary.downstreamGuardLabel }}
        </el-tag>
      </div>
    </div>

    <div class="summary-grid">
      <div v-for="field in PRODUCTION_ORDER_PARITY_METRIC_FIELDS" :key="field.key" class="summary-card">
        <span class="summary-label">{{ field.label }}</span>
        <strong class="summary-value">{{ summaryValue(field.key) }}</strong>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      :title="summary.readonlyGuardReason"
      data-testid="production-order-readonly-guard"
    />

    <el-alert
      type="info"
      :closable="false"
      :title="summary.remainingGap"
      data-testid="production-order-remaining-gap"
    />

    <el-descriptions border :column="3" class="parity-descriptions">
      <el-descriptions-item label="当前入口">{{ summary.parityScopeLabel }}</el-descriptions-item>
      <el-descriptions-item label="工序镜像">{{ summary.processStatusLabel }}</el-descriptions-item>
      <el-descriptions-item label="下游守卫">{{ summary.downstreamGuardLabel }}</el-descriptions-item>
      <el-descriptions-item label="CAND098">
        {{ summary.retainedCand098 ? '生产计划基础回读 retained' : '未保留' }}
      </el-descriptions-item>
      <el-descriptions-item label="CAND176">
        {{ summary.retainedCand176 ? '生产跟进 / 样衣 parity retained' : '未保留' }}
      </el-descriptions-item>
      <el-descriptions-item label="写入边界">
        dispatch / status-change / inventory-impact disabled
      </el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<script setup lang="ts">
import type { ProductionOrderParityReadonlySummary } from '@/views/production/composables/useProductionPlanReadback'
import {
  PRODUCTION_ORDER_PARITY_METRIC_FIELDS,
  type ProductionOrderParityMetricKey,
} from '@/views/production/constants/productionOrderParityFields'

const props = defineProps<{
  summary: ProductionOrderParityReadonlySummary
}>()

const summaryValue = (key: ProductionOrderParityMetricKey): string => {
  switch (key) {
    case 'mirroredOrderCount':
      return String(props.summary.mirroredOrderCount)
    case 'jobCardReadyCount':
      return String(props.summary.jobCardReadyCount)
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
.parity-shell {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.parity-header {
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
.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.header-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
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
</style>
