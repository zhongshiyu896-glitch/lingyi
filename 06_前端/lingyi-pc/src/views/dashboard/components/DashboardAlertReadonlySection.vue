<template>
  <section class="alert-readonly-board" data-testid="cand243-dashboard-alert-readonly">
    <header>
      <div>
        <h2>经营告警明细与来源审计</h2>
        <p>只读钻取告警来源、证据摘要与入口守卫，不回写主工作台卡区。</p>
      </div>
      <div class="alert-header-tags">
        <el-tag effect="plain" type="info">source_layer={{ sourceLayer }}</el-tag>
        <el-tag effect="plain" type="success">final_path={{ finalPath }}</el-tag>
      </div>
    </header>

    <div class="alert-grid">
      <article v-for="item in alertItems" :key="item.key" class="alert-card">
        <div class="alert-card-top">
          <div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.sourceDescription }}</p>
          </div>
          <el-tag effect="plain" :type="item.statusTone">{{ item.statusLabel }}</el-tag>
        </div>
        <div class="alert-meta">
          <span>source_module={{ item.sourceModule }}</span>
          <span>source_route={{ item.sourceRoute }}</span>
        </div>
        <p class="alert-evidence">{{ item.evidenceSummary }}</p>
        <div class="alert-guard-row">
          <el-tag effect="plain" :type="item.processingTone">{{ item.processingStatus }}</el-tag>
          <small>{{ item.auditSummary }}</small>
        </div>
        <small class="alert-gap">{{ item.remainingGap }}</small>
      </article>
    </div>

    <section class="audit-board" data-testid="cand243-dashboard-alert-audit">
      <header>
        <h3>来源审计</h3>
        <el-tag effect="plain" type="warning">readonly guard</el-tag>
      </header>
      <div class="audit-grid">
        <article v-for="item in auditItems" :key="item.key" class="audit-card">
          <div class="audit-card-top">
            <strong>{{ item.label }}</strong>
            <el-tag effect="plain" :type="item.statusTone">{{ item.statusLabel }}</el-tag>
          </div>
          <span>{{ item.sourceTag }}</span>
          <span>{{ item.sourceRoute }}</span>
          <small>{{ item.note }}</small>
        </article>
      </div>
    </section>

    <section class="action-guard-board" data-testid="cand243-dashboard-alert-actions">
      <header>
        <h3>只读动作守卫</h3>
      </header>
      <div class="action-guard-list">
        <article v-for="item in readonlyActions" :key="item.key" class="action-guard-item">
          <el-button size="small" disabled>{{ item.label }}</el-button>
          <small>{{ item.reason }}</small>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type {
  DashboardAlertAuditItem,
  DashboardAlertReadonlyActionItem,
  DashboardAlertReadonlyItem,
} from '../composables/useDashboardAlertReadonly'

defineProps({
  alertItems: {
    type: Array as PropType<DashboardAlertReadonlyItem[]>,
    required: true,
  },
  auditItems: {
    type: Array as PropType<DashboardAlertAuditItem[]>,
    required: true,
  },
  readonlyActions: {
    type: Array as PropType<DashboardAlertReadonlyActionItem[]>,
    required: true,
  },
  sourceLayer: {
    type: String,
    required: true,
  },
  finalPath: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.alert-readonly-board,
.audit-board,
.action-guard-board {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.alert-readonly-board,
.audit-board,
.action-guard-board {
  padding: 14px;
}

.alert-readonly-board {
  display: grid;
  gap: 12px;
}

.alert-readonly-board > header,
.audit-board > header,
.action-guard-board > header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.alert-readonly-board h2,
.audit-board h3,
.action-guard-board h3,
.alert-card h3 {
  margin: 0;
}

.alert-readonly-board > header p,
.alert-card-top p,
.audit-card small,
.action-guard-item small,
.alert-gap {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 12px;
}

.alert-header-tags,
.alert-meta,
.alert-guard-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.alert-grid,
.audit-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.alert-card,
.audit-card,
.action-guard-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}

.alert-card {
  display: grid;
  gap: 8px;
}

.alert-card-top,
.audit-card-top {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: flex-start;
}

.alert-meta,
.audit-card span {
  color: #4b5563;
  font-size: 12px;
}

.alert-evidence {
  margin: 0;
  color: #1f2937;
  font-size: 13px;
  line-height: 1.5;
}

.action-guard-list {
  display: grid;
  gap: 10px;
}

.action-guard-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
