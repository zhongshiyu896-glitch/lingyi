<template>
  <section class="trend-readonly-board" data-testid="cand248-dashboard-trend-readonly">
    <header>
      <div>
        <h2>经营趋势时窗与来源新鲜度</h2>
        <p>只读钻取趋势时窗、来源新鲜度与刷新说明，不改写主工作台卡区或告警来源审计子区。</p>
      </div>
      <div class="trend-header-tags">
        <el-tag effect="plain" type="info">source_layer={{ sourceLayer }}</el-tag>
        <el-tag effect="plain" type="success">final_path={{ finalPath }}</el-tag>
      </div>
    </header>

    <div class="trend-window-grid" data-testid="cand248-trend-window-summary">
      <article v-for="item in windowItems" :key="item.key" class="trend-window-card">
        <span class="trend-window-label">{{ item.label }}</span>
        <strong class="trend-window-value">{{ item.value }}</strong>
        <small class="trend-window-note">{{ item.note }}</small>
      </article>
    </div>

    <section class="freshness-board" data-testid="cand248-source-freshness">
      <header>
        <h3>来源新鲜度</h3>
        <el-tag effect="plain" type="warning">readonly freshness</el-tag>
      </header>
      <div class="freshness-grid">
        <article v-for="item in freshnessItems" :key="item.key" class="freshness-card">
          <div class="freshness-top">
            <strong>{{ item.label }}</strong>
            <el-tag effect="plain" :type="item.statusTone">{{ item.statusLabel }}</el-tag>
          </div>
          <span>latest_refresh={{ item.latestRefresh }}</span>
          <span>{{ item.staleIndicator }}</span>
          <small>{{ item.note }}</small>
          <small>{{ item.freshnessExplanation }}</small>
        </article>
      </div>
    </section>

    <section class="refresh-explanation-board" data-testid="cand248-refresh-explanation">
      <el-tag effect="plain" type="info">refresh explanation</el-tag>
      <p>{{ refreshExplanation }}</p>
    </section>

    <section class="trend-action-guard-board" data-testid="cand248-trend-readonly-actions">
      <header>
        <h3>只读动作守卫</h3>
      </header>
      <div class="trend-action-list">
        <article v-for="item in readonlyActions" :key="item.key" class="trend-action-item">
          <el-button size="small" disabled>{{ item.label }}</el-button>
          <small>{{ item.reason }}</small>
        </article>
      </div>
    </section>

    <div class="trend-remaining-gap" data-testid="cand248-trend-remaining-gap">
      <el-tag effect="plain" type="danger">remaining_gap</el-tag>
      <span>{{ remainingGap }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type {
  DashboardTrendFreshnessItem,
  DashboardTrendReadonlyActionItem,
  DashboardTrendWindowItem,
} from '../composables/useDashboardTrendReadonly'

defineProps({
  windowItems: {
    type: Array as PropType<DashboardTrendWindowItem[]>,
    required: true,
  },
  freshnessItems: {
    type: Array as PropType<DashboardTrendFreshnessItem[]>,
    required: true,
  },
  refreshExplanation: {
    type: String,
    required: true,
  },
  readonlyActions: {
    type: Array as PropType<DashboardTrendReadonlyActionItem[]>,
    required: true,
  },
  remainingGap: {
    type: String,
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
.trend-readonly-board,
.freshness-board,
.refresh-explanation-board,
.trend-action-guard-board {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.trend-readonly-board,
.freshness-board,
.refresh-explanation-board,
.trend-action-guard-board {
  padding: 14px;
}

.trend-readonly-board {
  display: grid;
  gap: 12px;
}

.trend-readonly-board > header,
.freshness-board > header,
.trend-action-guard-board > header,
.freshness-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.trend-readonly-board h2,
.freshness-board h3,
.trend-action-guard-board h3 {
  margin: 0;
}

.trend-readonly-board > header p,
.trend-window-note,
.freshness-card small,
.refresh-explanation-board p,
.trend-action-item small {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.trend-header-tags,
.trend-remaining-gap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.trend-window-grid,
.freshness-grid {
  display: grid;
  gap: 10px;
}

.trend-window-grid {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}

.freshness-grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.trend-window-card,
.freshness-card,
.trend-action-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}

.trend-window-card,
.freshness-card {
  display: grid;
  gap: 8px;
}

.trend-window-label {
  color: #6b7280;
  font-size: 12px;
}

.trend-window-value {
  font-size: 18px;
}

.freshness-card span {
  color: #4b5563;
  font-size: 12px;
}

.refresh-explanation-board {
  display: grid;
  gap: 8px;
}

.trend-action-list {
  display: grid;
  gap: 10px;
}

.trend-action-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.trend-remaining-gap {
  color: #4b5563;
  font-size: 12px;
}
</style>
