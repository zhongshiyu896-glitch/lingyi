<template>
  <section class="scope-bridge-shell" data-testid="realobj-subcontract-scope-bridge-readback">
    <div class="scope-bridge-header">
      <div>
        <h3>利润范围 / 物料桥接</h3>
        <p>仅回读利润范围、来源映射、物料标签和 scope guard，不释放收货、发料、结算、导出或库存写链路。</p>
      </div>
      <div class="scope-bridge-tags">
        <el-tag :type="summary.bridgeStatusType" effect="plain">{{ summary.bridgeStatusLabel }}</el-tag>
        <el-tag data-testid="realobj-subcontract-profit-scope-status" :type="summary.profitScopeType" effect="plain">
          {{ summary.profitScopeLabel }}
        </el-tag>
        <el-tag :type="summary.resourceScopeType" effect="plain">{{ summary.resourceScopeLabel }}</el-tag>
      </div>
    </div>

    <el-alert :closable="false" type="info" :title="summary.readonlyReason" />

    <el-descriptions border :column="2" class="scope-bridge-summary">
      <el-descriptions-item label="final_path">{{ finalPath }}</el-descriptions-item>
      <el-descriptions-item label="parity">{{ parityToken || '-' }}</el-descriptions-item>
      <el-descriptions-item label="数据来源">{{ summary.dataSource }}</el-descriptions-item>
      <el-descriptions-item label="桥接摘要">{{ summary.bridgeSummary }}</el-descriptions-item>
      <el-descriptions-item label="偏离提示">{{ summary.deviationHint }}</el-descriptions-item>
      <el-descriptions-item label="只读原因">{{ summary.readonlyReason }}</el-descriptions-item>
    </el-descriptions>

    <el-card shadow="never" data-testid="realobj-subcontract-material-bridge-tags">
      <template #header>
        <span>物料桥接标签</span>
      </template>
      <div class="material-tag-list">
        <div v-for="tag in summary.materialTags" :key="tag.key" class="material-tag-item">
          <div class="material-tag-head">
            <span class="material-tag-title">{{ tag.label }}</span>
            <el-tag :type="tag.type" effect="plain">{{ tag.value }}</el-tag>
          </div>
          <p class="material-tag-hint">{{ tag.hint }}</p>
        </div>
      </div>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <span>来源映射</span>
      </template>
      <div class="mapping-list">
        <div v-for="field in summary.mappingFields" :key="field.key" class="mapping-item">
          <div class="mapping-head">
            <span class="mapping-title">{{ field.label }}</span>
            <strong>{{ field.value }}</strong>
          </div>
          <p class="mapping-hint">{{ field.hint }}</p>
        </div>
      </div>
    </el-card>

    <el-card shadow="never" data-testid="realobj-subcontract-scope-guard-state">
      <template #header>
        <span>只读守卫</span>
      </template>
      <div class="guard-list">
        <div v-for="guard in guardStates" :key="guard.label" class="guard-item">
          <div class="mapping-head">
            <el-tag :type="guard.type">{{ guard.label }}</el-tag>
            <strong>{{ guard.reason }}</strong>
          </div>
        </div>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import type { SubcontractGuardState, SubcontractScopeBridgeReadonlyView } from '../composables/useSubcontractReadonly'

defineProps<{
  summary: SubcontractScopeBridgeReadonlyView
  guardStates: SubcontractGuardState[]
  finalPath: string
  parityToken?: string
}>()
</script>

<style scoped>
.scope-bridge-shell {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scope-bridge-header,
.scope-bridge-tags,
.mapping-head,
.material-tag-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.scope-bridge-header h3 {
  margin: 0;
  font-size: 16px;
}

.scope-bridge-header p,
.material-tag-hint,
.mapping-hint {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.scope-bridge-tags {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.material-tag-list,
.mapping-list,
.guard-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.material-tag-item,
.mapping-item,
.guard-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-blank);
}

.material-tag-title,
.mapping-title {
  font-weight: 600;
}
</style>
