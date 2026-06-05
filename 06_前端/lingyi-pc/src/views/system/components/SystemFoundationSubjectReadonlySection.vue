<template>
  <el-card shadow="never" data-testid="system-foundation-subject-section">
    <template #header>
      <div class="header-row">
        <span>基础资料主体目录 readiness / parity（只读）</span>
        <div class="readonly-status-row">
          <el-tag effect="plain" data-testid="system-foundation-subject-get-only">GET-only</el-tag>
          <el-tag
            effect="plain"
            type="warning"
            data-testid="system-foundation-subject-readonly-guard"
            data-write-guard="readonly:system-foundation-subject"
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
      data-testid="system-foundation-subject-permission-guard"
      title="foundation-subjects 只读区缺少读取权限，仅保留 guard 与 route parity 说明。"
      style="margin-bottom: 12px"
    />

    <template v-else>
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 12px"
        data-testid="system-foundation-subject-parity-alert"
        :title="`owner/foundation parity：${routeParity || '/system/management'}｜当前 tab：${routeTab || 'default'}｜dictionary/config/report 写入、报表生成与导出均保持只读 guard。`"
      />

      <div class="meta-row" data-testid="system-foundation-subject-summary">
        <span data-testid="system-foundation-subject-readiness-summary">readiness：{{ readinessSummary }}</span>
        <span data-testid="system-foundation-subject-owner-parity">owner/foundation parity：{{ ownerParitySummary }}</span>
        <span data-testid="system-foundation-subject-source-status">source status：{{ sourceStatusSummary }}</span>
        <span data-testid="system-foundation-subject-blocked-reason">blocked reason：{{ blockedReason }}</span>
        <span data-testid="system-foundation-subject-overall-status">当前状态：{{ overallStatus }}</span>
      </div>

      <el-descriptions
        :column="1"
        border
        size="small"
        style="margin-bottom: 12px"
        data-testid="system-foundation-subject-route-scope"
      >
        <el-descriptions-item
          v-for="item in parityRoutes"
          :key="item.key"
          :label="item.label"
        >
          <span :data-testid="`system-foundation-subject-route-${item.key}`">{{ item.route }}</span>
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
        :data="subjectRows"
        border
        empty-text="暂无 foundation subject readiness 数据"
        data-testid="system-foundation-subject-table"
      >
        <el-table-column prop="label" label="只读核对项" min-width="220" />
        <el-table-column label="状态" width="120">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)" effect="plain">
              {{ scope.row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="source status / blocked reason" min-width="320" />
        <el-table-column prop="recommendation" label="只读建议" min-width="320" />
      </el-table>

      <div class="recommendation-list" data-testid="system-foundation-subject-recommendations">
        <div
          v-for="(recommendation, index) in readonlyRecommendations"
          :key="`${index}-${recommendation}`"
          class="recommendation-item"
        >
          {{ recommendation }}
        </div>
      </div>

      <div class="guard-grid" data-testid="system-foundation-subject-guard-grid">
        <div
          v-for="action in readonlyGuardActions"
          :key="action.key"
          class="guard-item"
          :data-testid="`system-foundation-subject-guard-${action.key}`"
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
        data-testid="system-foundation-subject-remaining-gap"
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
import { useSystemFoundationSubjectReadonly } from '../composables/useSystemFoundationSubjectReadonly'

const props = defineProps<{
  configItems: SystemConfigCatalogItem[]
  dictionaryItems: SystemDictionaryCatalogItem[]
  healthItems: SystemHealthSummaryItem[]
  routeParity: string
  routeTab: string
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
  canReadConfig,
  canReadDictionary,
  canReadHealthSummary,
} = toRefs(props)

const {
  blockedReason,
  overallStatus,
  ownerParitySummary,
  parityRoutes,
  readonlyGuardActions,
  readonlyRecommendations,
  readinessSummary,
  remainingGap,
  sourceStatusSummary,
  subjectRows,
} = useSystemFoundationSubjectReadonly({
  configItems,
  dictionaryItems,
  healthItems,
  routeParity,
  routeTab,
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
