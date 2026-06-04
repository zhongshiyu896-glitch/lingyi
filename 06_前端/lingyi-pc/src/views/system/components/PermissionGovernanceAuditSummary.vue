<template>
  <div data-testid="permission-governance-audit-summary">
    <div class="summary-grid" data-testid="permission-governance-summary-grid">
      <el-card shadow="never" class="summary-tile">
        <div class="summary-label">角色矩阵</div>
        <div class="summary-value">{{ roleCount }}</div>
        <div class="summary-hint">只读角色覆盖</div>
      </el-card>
      <el-card shadow="never" class="summary-tile">
        <div class="summary-label">高危动作</div>
        <div class="summary-value">{{ highRiskCount }}</div>
        <div class="summary-hint">需 guarded / hidden</div>
      </el-card>
      <el-card shadow="never" class="summary-tile">
        <div class="summary-label">安全审计记录</div>
        <div class="summary-value">{{ securityAuditTotal }}</div>
        <div class="summary-hint">当前筛选命中</div>
      </el-card>
      <el-card shadow="never" class="summary-tile">
        <div class="summary-label">操作审计记录</div>
        <div class="summary-value">{{ operationAuditTotal }}</div>
        <div class="summary-hint">当前筛选命中</div>
      </el-card>
    </div>

    <div class="readonly-status-row" data-testid="permission-diagnostic-status-row">
      <el-tag :type="diagnosticStatus === 'ok' ? 'success' : 'warning'" effect="plain">
        diagnostic={{ diagnosticStatus || 'fallback' }}
      </el-tag>
      <el-tag type="info" effect="plain">catalog={{ catalogEnabled ? 'on' : 'off' }}</el-tag>
      <el-tag type="info" effect="plain">audit={{ auditReadEnabled ? 'on' : 'off' }}</el-tag>
      <el-tag type="warning" effect="plain">export guarded={{ canExport ? 'ui-only' : 'denied' }}</el-tag>
      <el-tag type="info" effect="plain">generated_at={{ generatedAt || '-' }}</el-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  roleCount: number
  highRiskCount: number
  securityAuditTotal: number
  operationAuditTotal: number
  diagnosticStatus: string
  catalogEnabled: boolean
  auditReadEnabled: boolean
  canExport: boolean
  generatedAt?: string
}>()
</script>

<style scoped>
.readonly-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.summary-tile {
  min-height: 116px;
}

.summary-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.summary-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 600;
  line-height: 1.1;
}

.summary-hint {
  margin-top: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
