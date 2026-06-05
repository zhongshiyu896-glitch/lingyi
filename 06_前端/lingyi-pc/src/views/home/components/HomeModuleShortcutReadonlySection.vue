<template>
  <el-card shadow="never" data-testid="cand326-home-module-shortcuts-section">
    <template #header>
      <div class="header-row">
        <div>
          <span class="title">首页模块快捷只读区</span>
          <p class="subtitle">直接服务六模块本地可用性，不复用 dashboard guard 或 cross-module matrix。</p>
        </div>
        <div class="tag-row">
          <el-tag effect="plain" data-testid="cand326-home-module-shortcuts-get-only">GET-only</el-tag>
          <el-tag effect="plain" type="warning" data-testid="cand326-home-module-shortcuts-tab">
            tab={{ summary.activeTabLabel }}
          </el-tag>
        </div>
      </div>
    </template>

    <el-alert
      type="info"
      :closable="false"
      data-testid="cand326-home-module-shortcuts-route-alias"
      :title="`/home?tab=module-shortcuts 与 /dashboard/workplace alias 仅承接首页只读快捷语义。`"
      style="margin-bottom: 12px"
    />

    <div class="meta-row" data-testid="cand326-home-module-shortcuts-meta">
      <span data-testid="cand326-home-module-shortcuts-readiness">readiness：{{ summary.readinessSummary }}</span>
      <span data-testid="cand326-home-module-shortcuts-source-badges">source badges：{{ summary.sourceBadgeSummary }}</span>
      <span data-testid="cand326-home-module-shortcuts-owner-source">owner/source：{{ summary.ownerSourceReadonlyLine }}</span>
      <span data-testid="cand326-home-module-shortcuts-blocked-reason">blocked reason：{{ summary.blockedReason }}</span>
    </div>

    <el-descriptions
      :column="1"
      border
      size="small"
      style="margin-bottom: 12px"
      data-testid="cand326-home-module-shortcuts-route-scope"
    >
      <el-descriptions-item
        v-for="item in summary.routeItems"
        :key="item.key"
        :label="item.label"
      >
        <span :data-testid="`cand326-home-route-${item.key}`">{{ item.route }}</span>
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

    <div class="shortcut-grid" data-testid="cand326-home-module-shortcuts-strip">
      <article
        v-for="(item, index) in summary.shortcutItems"
        :key="item.key"
        class="shortcut-card"
        :data-testid="`cand326-home-module-shortcut-${index}`"
      >
        <div class="shortcut-header">
          <div>
            <strong>{{ item.label }}</strong>
            <p>{{ item.note }}</p>
          </div>
          <div class="shortcut-tags">
            <el-tag effect="plain" :type="item.statusTone">{{ item.statusLabel }}</el-tag>
            <el-tag effect="plain" type="info">{{ item.sourceBadge }}</el-tag>
          </div>
        </div>
        <p class="route-line">{{ item.route }}</p>
        <p class="owner-line">{{ item.ownerSourceLine }}</p>
        <p class="reason-line">{{ item.blockedReason }}</p>
        <div class="action-row">
          <el-button size="small" disabled data-write-guard>打开</el-button>
          <el-button size="small" disabled data-write-guard>执行</el-button>
        </div>
        <small>{{ item.actionReason }}</small>
      </article>
    </div>

    <div class="guard-grid" data-testid="cand326-home-module-shortcuts-guard-grid">
      <div
        v-for="action in summary.guardedActions"
        :key="action.key"
        class="guard-item"
        :data-testid="`cand326-home-module-shortcuts-guard-${action.key}`"
      >
        <div class="guard-label">{{ action.label }}</div>
        <el-button size="small" disabled>{{ action.label }}</el-button>
        <div class="guard-hint">{{ action.reason }}</div>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      style="margin-top: 12px"
      data-testid="cand326-home-module-shortcuts-readonly-guard"
      :title="summary.guardMessage"
    />
    <el-alert
      type="info"
      :closable="false"
      style="margin-top: 12px"
      data-testid="cand326-home-module-shortcuts-remaining-gap"
      :title="summary.remainingGap"
    />
  </el-card>
</template>

<script setup lang="ts">
import type { HomeModuleShortcutReadonlySummary } from '../composables/useHomeModuleShortcutReadonly'

defineProps<{
  summary: HomeModuleShortcutReadonlySummary
}>()
</script>

<style scoped>
.header-row,
.shortcut-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.title {
  font-weight: 600;
}

.subtitle,
.shortcut-header p,
.route-line,
.owner-line,
.reason-line,
.guard-hint,
.route-note {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.tag-row,
.shortcut-tags,
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-row {
  margin-bottom: 12px;
}

.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.shortcut-card,
.guard-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-blank);
}

.shortcut-card {
  display: grid;
  gap: 10px;
}

.action-row {
  display: flex;
  gap: 8px;
}

.guard-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.guard-item {
  display: grid;
  gap: 8px;
}

.guard-label {
  font-weight: 600;
}

@media (max-width: 960px) {
  .header-row,
  .shortcut-header {
    flex-direction: column;
  }

  .shortcut-grid,
  .guard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
