<template>
  <el-card shadow="never" data-testid="system-catalog-drift-section">
    <template #header>
      <div class="header-row">
        <span>系统目录漂移与健康差异（只读）</span>
        <div class="readonly-status-row">
          <el-tag effect="plain" data-testid="system-catalog-drift-get-only">GET-only</el-tag>
          <el-tag
            effect="plain"
            type="warning"
            data-testid="system-catalog-drift-readonly-guard"
            data-write-guard="readonly:system-catalog-drift"
            data-guard-state="guarded_readonly"
            data-side-effect-guard="write-disabled"
          >
            readonly guard
          </el-tag>
        </div>
      </div>
    </template>

    <el-alert
      v-if="!canReadConfig || !canReadDictionary || !canReadHealthSummary"
      type="warning"
      :closable="false"
      data-testid="system-catalog-drift-permission-guard"
      title="系统目录漂移只读区缺少读取权限，仅保留 guard 与 route parity 说明。"
      style="margin-bottom: 12px"
    />

    <template v-else>
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 12px"
        data-testid="system-catalog-drift-parity-alert"
        :title="`基础资料 parity：${effectiveParity}｜当前 tab：${effectiveTab}｜当前 focus：${effectiveFocus}｜目录维护/系统配置写入/报表生成/导出均保持只读 guard。`"
      />

      <div class="meta-row" data-testid="system-catalog-drift-summary">
        <span>漂移摘要：{{ driftStatusSummary }}</span>
        <span>当前状态：{{ overallStatus }}</span>
        <span data-testid="system-catalog-drift-parity">基础资料 parity：{{ effectiveParity }}</span>
        <span data-testid="system-catalog-drift-focus">focus：{{ effectiveFocus }}</span>
      </div>

      <div class="meta-row" data-testid="system-catalog-drift-query-state">
        <span>route：{{ effectiveRoute }}</span>
        <span>tab：{{ effectiveTab }}</span>
        <span>focus：{{ effectiveFocus }}</span>
      </div>

      <el-alert
        type="warning"
        :closable="false"
        style="margin-bottom: 12px"
        data-testid="system-catalog-drift-blocked-reason"
        :title="blockedReason"
      />

      <div class="meta-row" data-testid="system-catalog-drift-legacy-aliases">
        <span>legacy aliases：{{ legacyRouteAliases.join(' ｜ ') }}</span>
      </div>

      <el-descriptions
        :column="1"
        border
        size="small"
        style="margin-bottom: 12px"
        data-testid="system-catalog-drift-route-scope"
      >
        <el-descriptions-item
          v-for="item in parityRoutes"
          :key="item.key"
          :label="item.label"
        >
          <span :data-testid="`system-catalog-drift-route-${item.key}`">{{ item.route }}</span>
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

      <el-table
        :data="driftRows"
        border
        empty-text="暂无系统目录漂移数据"
        data-testid="system-catalog-drift-table"
      >
        <el-table-column prop="label" label="漂移项" min-width="220" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" effect="plain">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="健康差异 / 缺项原因" min-width="320" />
        <el-table-column prop="recommendation" label="只读修复建议" min-width="320" />
      </el-table>

      <div class="recommendation-list" data-testid="system-catalog-drift-recommendations">
        <div
          v-for="(recommendation, index) in readonlyRecommendations"
          :key="`${index}-${recommendation}`"
          class="recommendation-item"
        >
          {{ recommendation }}
        </div>
      </div>

      <div class="guard-grid" data-testid="system-catalog-drift-guard-grid">
        <div
          v-for="action in readonlyGuardActions"
          :key="action.key"
          class="guard-item"
          :data-testid="`system-catalog-drift-guard-${action.key}`"
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
        data-testid="system-catalog-drift-remaining-gap"
        :title="remainingGap"
      />
    </template>
  </el-card>
</template>

<script setup lang="ts">
import { toRefs } from 'vue'
import type {
  SystemConfigCatalogItem,
  SystemDictionaryCatalogItem,
  SystemHealthSummaryItem,
} from '@/api/system_management'
import { useSystemCatalogDriftReadonly } from '../composables/useSystemCatalogDriftReadonly'

const props = defineProps<{
  configItems: SystemConfigCatalogItem[]
  dictionaryItems: SystemDictionaryCatalogItem[]
  healthItems: SystemHealthSummaryItem[]
  routeParity: string
  routeTab: string
  routeFocus: string
  canReadConfig: boolean
  canReadDictionary: boolean
  canReadHealthSummary: boolean
}>()

const {
  configItems,
  dictionaryItems,
  healthItems,
  routeParity,
  routeTab,
  routeFocus,
  canReadConfig,
  canReadDictionary,
  canReadHealthSummary,
} = toRefs(props)

const {
  driftRows,
  driftStatusSummary,
  overallStatus,
  effectiveFocus,
  effectiveParity,
  effectiveRoute,
  effectiveTab,
  blockedReason,
  legacyRouteAliases,
  parityRoutes,
  readonlyRecommendations,
  readonlyGuardActions,
  remainingGap,
} = useSystemCatalogDriftReadonly({
  configItems,
  dictionaryItems,
  healthItems,
  routeParity,
  routeTab,
  routeFocus,
  canReadConfig,
  canReadDictionary,
  canReadHealthSummary,
})

const statusTagType = (status: 'ok' | 'warn' | 'blocked'): 'success' | 'warning' | 'danger' => {
  if (status === 'ok') {
    return 'success'
  }
  if (status === 'warn') {
    return 'warning'
  }
  return 'danger'
}
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.readonly-status-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.route-note {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
}

.recommendation-list {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}

.recommendation-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 10px 12px;
  color: var(--el-text-color-regular);
  background: var(--el-fill-color-blank);
}

.guard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.guard-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px;
  display: grid;
  gap: 8px;
}

.guard-label {
  font-weight: 600;
}

.guard-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}
</style>
