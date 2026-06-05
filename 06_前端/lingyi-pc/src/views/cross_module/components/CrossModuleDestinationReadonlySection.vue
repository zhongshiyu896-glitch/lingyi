<template>
  <section class="readonly-section" data-testid="cand314-cross-module-destination-readonly-section">
    <div class="readonly-header">
      <div>
        <h3 data-testid="cand314-cross-module-destination-title">跨模块去向矩阵</h3>
        <p data-testid="cand314-cross-module-destination-subtitle">
          当前仅核对 CrossModuleView 的去向矩阵、module-availability 查询态与 readonly guard，不开放真实执行。
        </p>
      </div>
      <div class="tag-list" data-testid="cand314-cross-module-destination-tags">
        <el-tag
          v-for="tag in summary.tags"
          :key="tag.key"
          :type="tag.type"
          effect="plain"
          :data-testid="`cand314-cross-module-destination-tag-${tag.key}`"
        >
          {{ tag.label }}
        </el-tag>
      </div>
    </div>

    <div class="matrix-grid" data-testid="cand314-cross-module-destination-matrix">
      <article
        v-for="row in summary.matrixRows"
        :key="row.key"
        class="matrix-card"
        :data-testid="`cand314-cross-module-destination-row-${row.key}`"
      >
        <div class="matrix-card-header">
          <div>
            <h4>{{ row.title }}</h4>
            <p>{{ row.sourceDescription }}</p>
          </div>
          <el-tag :type="row.statusTone" effect="plain">{{ row.statusLabel }}</el-tag>
        </div>
        <div class="tag-list" :data-testid="`cand314-cross-module-destination-modules-${row.key}`">
          <el-tag
            v-for="moduleLabel in row.modules"
            :key="moduleLabel"
            effect="plain"
            size="small"
            type="info"
          >
            {{ moduleLabel }}
          </el-tag>
        </div>
        <small>{{ row.routeLabel }}</small>
        <small>query_state={{ row.queryStateLabel }}</small>
        <small>{{ row.blockedReason }}</small>
        <small>{{ row.note }}</small>
      </article>
    </div>

    <el-descriptions
      :column="2"
      border
      size="small"
      class="readonly-descriptions"
      data-testid="cand314-cross-module-destination-summary"
    >
      <el-descriptions-item label="readonly source">{{ summary.readonlySourceLabel }}</el-descriptions-item>
      <el-descriptions-item label="readonly mode">{{ summary.readonlyModeLabel }}</el-descriptions-item>
      <el-descriptions-item label="query state">{{ summary.queryStateLabel }}</el-descriptions-item>
      <el-descriptions-item label="active tab">{{ summary.activeTabLabel }}</el-descriptions-item>
      <el-descriptions-item label="blocked reason">{{ summary.blockedReason }}</el-descriptions-item>
      <el-descriptions-item label="guard 说明">{{ summary.blockedReasonDetail }}</el-descriptions-item>
    </el-descriptions>

    <div class="guarded-action-list" data-testid="cand314-cross-module-destination-guarded-actions">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guarded-action-card"
        :data-testid="`cand314-cross-module-destination-guarded-action-${action.key}`"
      >
        <el-button size="small" disabled data-write-guard>{{ action.label }}</el-button>
        <span>{{ action.reason }}</span>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      :title="summary.guardMessage"
      data-testid="cand314-cross-module-destination-readonly-guard"
    />
    <el-alert
      type="info"
      :closable="false"
      show-icon
      :title="summary.remainingGap"
      data-testid="cand314-cross-module-destination-remaining-gap"
    />
  </section>
</template>

<script setup lang="ts">
import type { CrossModuleDestinationReadonlySummary } from '../composables/useCrossModuleDestinationReadonly'

defineProps<{
  summary: CrossModuleDestinationReadonlySummary
}>()
</script>

<style scoped>
.readonly-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
}

.readonly-header,
.matrix-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.readonly-header h3,
.matrix-card h4 {
  margin: 0 0 4px;
}

.readonly-header p,
.matrix-card p,
.matrix-card small {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.matrix-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.matrix-card,
.guarded-action-card {
  padding: 10px 12px;
  border-radius: 6px;
  background: var(--el-bg-color);
}

.matrix-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border: 1px solid var(--el-border-color-lighter);
}

.readonly-descriptions {
  background: var(--el-bg-color);
}

.guarded-action-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.guarded-action-card {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px dashed var(--el-border-color);
  color: var(--el-text-color-regular);
  font-size: 13px;
}

@media (max-width: 960px) {
  .readonly-header,
  .matrix-card-header {
    flex-direction: column;
  }

  .matrix-grid,
  .guarded-action-list {
    grid-template-columns: 1fr;
  }
}
</style>
