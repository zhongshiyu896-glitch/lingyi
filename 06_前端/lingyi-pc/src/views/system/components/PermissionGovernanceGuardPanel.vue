<template>
  <el-card shadow="never" data-testid="permission-governance-guard-panel">
    <template #header>
      <div class="header-row">
        <span>权限守卫状态</span>
        <div class="readonly-status-row">
          <el-tag type="success" effect="plain">{{ modeLabel }}</el-tag>
          <el-tag type="info" effect="plain">{{ routeLabel }}</el-tag>
          <el-tag type="warning" effect="plain">export guarded</el-tag>
        </div>
      </div>
    </template>

    <div class="guard-grid">
      <div
        v-for="item in guardItems"
        :key="item.key"
        class="guard-item"
        :data-testid="`permission-guard-${item.key}`"
      >
        <div class="guard-label">{{ item.label }}</div>
        <el-tag :type="item.enabled ? 'success' : 'warning'" effect="plain">
          {{ item.enabled ? 'enabled' : 'guarded' }}
        </el-tag>
        <div class="guard-hint">{{ item.hint }}</div>
      </div>
    </div>

    <div
      class="guarded-summary"
      data-testid="permission-governance-export-guard-summary"
      data-guard-state="guarded_readonly"
    >
      <span>guarded 按钮：{{ guardedButtonsText }}</span>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  canRead: boolean
  canAuditRead: boolean
  canDiagnostic: boolean
  canExport: boolean
  guardedButtons: string[]
  routeLabel?: string
  modeLabel?: string
}>()

const guardItems = computed(() => [
  {
    key: 'read',
    label: 'permission:read',
    enabled: props.canRead,
    hint: '权限矩阵 / 菜单管理只读回读',
  },
  {
    key: 'audit',
    label: 'permission:audit_read',
    enabled: props.canAuditRead,
    hint: '审计摘要 / 查询只读回读',
  },
  {
    key: 'diagnostic',
    label: 'permission:diagnostic',
    enabled: props.canDiagnostic,
    hint: '治理诊断状态回读',
  },
  {
    key: 'export',
    label: 'permission:export',
    enabled: props.canExport,
    hint: '仅展示 guarded 入口，不触发真实下载',
  },
])

const guardedButtonsText = computed(() => props.guardedButtons.join(' / ') || '-')
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.readonly-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.guard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.guard-item {
  min-height: 102px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.guard-label {
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.guard-hint {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-secondary);
}

.guarded-summary {
  margin-top: 12px;
  line-height: 1.5;
}
</style>
