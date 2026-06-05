<template>
  <section class="workbench-board" data-testid="cand230-dashboard-workbench-readonly">
    <header>
      <div>
        <h2>主工作台只读联动</h2>
        <p>工作台业务卡片、跨模块异常摘要与守卫状态均来自 dashboard readonly 层。</p>
      </div>
      <div class="header-tags">
        <el-tag effect="plain" type="info">source={{ sourceLayer }}</el-tag>
        <el-tag effect="plain" type="warning">final_path={{ finalPath }}</el-tag>
      </div>
    </header>

    <div class="workbench-grid">
      <article v-for="item in cards" :key="item.key" class="workbench-card">
        <div class="workbench-card-top">
          <div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.sourceLabel }}</p>
          </div>
          <el-tag effect="plain" :type="item.guardTone">{{ item.guardLabel }}</el-tag>
        </div>
        <strong class="workbench-metric">{{ item.metricValue }}</strong>
        <span class="workbench-metric-label">{{ item.metricLabel }}</span>
        <p class="workbench-detail">{{ item.detail }}</p>
        <small class="workbench-note">{{ item.disabledReason }}</small>
        <div class="workbench-actions">
          <el-button size="small" type="primary" plain :disabled="item.entryDisabled" @click="emitNavigate(item.path)">
            只读进入
          </el-button>
          <el-button size="small" disabled>{{ item.writeGuardLabel }}</el-button>
        </div>
      </article>
    </div>

    <div class="cross-module-grid" data-testid="cand230-dashboard-cross-module-summary">
      <article v-for="item in crossModuleItems" :key="item.key" class="cross-module-card">
        <div class="cross-module-top">
          <strong>{{ item.label }}</strong>
          <div class="cross-module-tags">
            <el-tag effect="plain" type="info">{{ item.sourceTag }}</el-tag>
            <el-tag effect="plain" :type="item.statusTone">{{ item.statusLabel }}</el-tag>
            <el-tag effect="plain" :type="item.guardTone">{{ item.guardLabel }}</el-tag>
          </div>
        </div>
        <p class="cross-module-summary">{{ item.summary }}</p>
        <small class="cross-module-route">route={{ item.routeLabel }}</small>
      </article>
    </div>

    <div class="remaining-gap" data-testid="cand230-dashboard-remaining-gap">
      <el-tag effect="plain" type="danger">remaining_gap</el-tag>
      <span>{{ remainingGap }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { DashboardCrossModuleReadonlyItem } from '../composables/useDashboardCrossModuleReadonly'
import type { DashboardWorkbenchCard } from '../composables/useDashboardWorkbenchReadonly'

defineProps<{
  cards: DashboardWorkbenchCard[]
  crossModuleItems: DashboardCrossModuleReadonlyItem[]
  sourceLayer: string
  finalPath: string
  remainingGap: string
}>()

const emit = defineEmits<{
  navigate: [path: string]
}>()

const emitNavigate = (path: string): void => {
  emit('navigate', path)
}
</script>

<style scoped>
.workbench-board {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
  display: grid;
  gap: 12px;
}

.workbench-board > header,
.cross-module-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.workbench-board h2,
.workbench-card-top h3,
.cross-module-top strong {
  margin: 0;
}

.workbench-board > header p,
.workbench-card-top p,
.workbench-detail,
.workbench-note,
.cross-module-summary,
.cross-module-route {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
}

.header-tags,
.cross-module-tags,
.workbench-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.workbench-grid,
.cross-module-grid {
  display: grid;
  gap: 10px;
}

.workbench-grid {
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
}

.cross-module-grid {
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.workbench-card,
.cross-module-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}

.workbench-card {
  display: grid;
  gap: 8px;
}

.workbench-card-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.workbench-metric {
  display: block;
  font-size: 20px;
}

.workbench-metric-label {
  color: #6b7280;
  font-size: 12px;
}

.cross-module-card {
  display: grid;
  gap: 8px;
}

.remaining-gap {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  color: #4b5563;
  font-size: 12px;
}
</style>
