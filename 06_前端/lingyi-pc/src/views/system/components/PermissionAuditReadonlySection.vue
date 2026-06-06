<template>
  <el-card shadow="never" data-testid="permission-audit-readonly-section">
    <template #header>
      <div class="header-row">
        <span>权限治理审计准备度（只读）</span>
        <div class="header-tags">
          <el-tag :type="isAuditReadinessTab ? 'success' : 'info'" effect="plain">
            {{ isAuditReadinessTab ? 'audit-readiness active' : 'governance baseline' }}
          </el-tag>
          <el-tag type="info" effect="plain">owner/source parity</el-tag>
          <el-tag type="warning" effect="plain">export guarded</el-tag>
        </div>
      </div>
    </template>

    <el-alert
      type="info"
      :closable="false"
      title="audit-readiness query state"
      :description="`active=${permissionAuditReadonlyRouteContracts.active} / alias=${permissionAuditReadonlyRouteContracts.parityAlias}`"
      data-testid="permission-audit-query-state"
      style="margin-bottom: 12px"
    />

    <div class="summary-grid" data-testid="permission-audit-readiness-summary-grid">
      <div
        v-for="card in summaryCards"
        :key="card.key"
        class="summary-item"
        :data-testid="`permission-audit-summary-${card.key}`"
      >
        <div class="summary-label">{{ card.label }}</div>
        <el-tag :type="card.tone" effect="plain">{{ card.value }}</el-tag>
        <div class="summary-hint">{{ card.hint }}</div>
      </div>
    </div>

    <div class="parity-grid" data-testid="permission-audit-parity-grid">
      <div
        v-for="line in parityLines"
        :key="line.key"
        class="parity-item"
        :data-testid="`permission-audit-parity-${line.key}`"
      >
        <span class="parity-label">{{ line.label }}</span>
        <el-tag :type="line.tone" effect="plain">{{ line.value }}</el-tag>
      </div>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      title="blocked reason"
      :description="blockedReasons.join('；')"
      data-testid="permission-audit-blocked-reason"
      style="margin-top: 12px"
    />

    <el-alert
      type="info"
      :closable="false"
      title="readonly guard"
      :description="readonlyGuardText"
      data-testid="permission-audit-readonly-guard"
      style="margin-top: 12px"
    />

    <el-collapse class="audit-collapse" data-testid="permission-audit-readiness-items">
      <el-collapse-item
        v-for="item in auditItems"
        :key="item.key"
        :name="item.key"
        :title="item.title"
        :data-testid="`permission-audit-item-${item.key}`"
      >
        <div class="item-meta">
          <el-tag :type="item.tone" effect="plain">{{ item.status }}</el-tag>
          <el-tag type="info" effect="plain">owner={{ item.owner }}</el-tag>
          <el-tag type="info" effect="plain">source={{ item.source }}</el-tag>
        </div>
        <div class="item-summary">{{ item.summary }}</div>
        <ul class="item-details">
          <li v-for="detail in item.details" :key="detail">{{ detail }}</li>
        </ul>
      </el-collapse-item>
    </el-collapse>

    <div class="disabled-actions" data-testid="permission-audit-disabled-actions">
      <div class="disabled-title">disabled / non-executable actions</div>
      <div class="disabled-grid">
        <div v-for="action in disabledActions" :key="action.key" class="disabled-item">
          <el-button disabled type="warning" plain>{{ action.label }}</el-button>
          <div class="disabled-reason">{{ action.reason }}</div>
        </div>
      </div>
    </div>

    <el-alert
      type="info"
      :closable="false"
      title="remaining_gap"
      :description="remainingGap"
      data-testid="permission-audit-remaining-gap"
      style="margin-top: 12px"
    />
  </el-card>
</template>

<script setup lang="ts">
import {
  permissionAuditReadonlyRouteContracts,
  type PermissionAuditReadonlyDisabledAction,
  type PermissionAuditReadonlyEntry,
  type PermissionAuditReadonlyLineItem,
  type PermissionAuditReadonlySummaryCard,
} from '@/views/system/constants/permissionAuditFields'

defineProps<{
  isAuditReadinessTab: boolean
  summaryCards: PermissionAuditReadonlySummaryCard[]
  parityLines: PermissionAuditReadonlyLineItem[]
  blockedReasons: string[]
  readonlyGuardText: string
  auditItems: PermissionAuditReadonlyEntry[]
  disabledActions: PermissionAuditReadonlyDisabledAction[]
  remainingGap: string
}>()
</script>

<style scoped>
.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.header-tags,
.item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-grid,
.parity-grid,
.disabled-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.summary-item,
.parity-item,
.disabled-item {
  min-height: 96px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.summary-label,
.parity-label,
.disabled-title {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.summary-hint,
.disabled-reason,
.item-summary,
.item-details {
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-text-color-regular);
}

.parity-item {
  min-height: 72px;
}

.audit-collapse,
.disabled-actions {
  margin-top: 12px;
}

.item-details {
  padding-left: 18px;
}

@media (max-width: 768px) {
  .summary-grid,
  .parity-grid,
  .disabled-grid {
    grid-template-columns: 1fr;
  }
}
</style>
