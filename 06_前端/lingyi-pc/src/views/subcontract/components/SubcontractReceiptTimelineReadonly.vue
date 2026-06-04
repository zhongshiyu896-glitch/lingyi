<template>
  <section class="timeline-shell" data-testid="realobj-subcontract-timeline-readback">
    <div class="timeline-header">
      <div>
        <h3>发料 / 收货 / 验货时间线</h3>
        <p>仅回读里程碑、异常节点、责任角色、时间与当前状态，不释放收发、验货、结算、导出或库存动作。</p>
      </div>
      <el-tag type="warning" effect="plain">readonly timeline</el-tag>
    </div>

    <div class="timeline-grid">
      <div v-for="milestone in milestones" :key="milestone.key" class="timeline-item">
        <div class="timeline-item-head">
          <span class="timeline-item-title">{{ milestone.label }}</span>
          <el-tag :type="milestone.statusType" effect="plain">{{ milestone.statusLabel }}</el-tag>
        </div>
        <div class="timeline-item-meta">
          <span>责任角色：{{ milestone.ownerRole }}</span>
          <span>时间：{{ milestone.occurredAt }}</span>
        </div>
        <strong class="timeline-item-summary">{{ milestone.summary }}</strong>
        <p class="timeline-item-hint">{{ milestone.guardHint }}</p>
      </div>
    </div>

    <el-card shadow="never" class="settlement-card" data-testid="realobj-subcontract-settlement-readonly-state">
      <template #header>
        <div class="settlement-header">
          <span>结算只读状态</span>
          <el-tag :type="settlementState.type">{{ settlementState.label }}</el-tag>
        </div>
      </template>
      <el-descriptions border :column="2">
        <el-descriptions-item label="阻断节点">{{ settlementState.blockedNode || '-' }}</el-descriptions-item>
        <el-descriptions-item label="已验收数量">{{ settlementState.acceptedQtyLabel }}</el-descriptions-item>
        <el-descriptions-item label="净额">{{ settlementState.netAmountLabel }}</el-descriptions-item>
        <el-descriptions-item label="状态说明">{{ settlementState.reason }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="never" class="abnormal-card" data-testid="realobj-subcontract-abnormal-node-readback">
      <template #header>
        <span>异常节点回读</span>
      </template>
      <div class="abnormal-list">
        <div v-for="node in abnormalNodes" :key="node.key" class="abnormal-item">
          <div class="timeline-item-head">
            <div class="timeline-item-title-group">
              <span class="timeline-item-title">{{ node.label }}</span>
              <span class="timeline-item-role">{{ node.ownerRole }}</span>
            </div>
            <el-tag :type="node.statusType" effect="plain">{{ node.statusLabel }}</el-tag>
          </div>
          <div class="timeline-item-meta">
            <span>时间：{{ node.occurredAt }}</span>
          </div>
          <strong class="timeline-item-summary">{{ node.reason }}</strong>
          <p class="timeline-item-hint">{{ node.actionHint }}</p>
        </div>
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import type {
  SubcontractAbnormalNodeView,
  SubcontractSettlementReadonlyView,
  SubcontractTimelineMilestoneView,
} from '../composables/useSubcontractReadonly'

defineProps<{
  milestones: SubcontractTimelineMilestoneView[]
  settlementState: SubcontractSettlementReadonlyView
  abnormalNodes: SubcontractAbnormalNodeView[]
}>()
</script>

<style scoped>
.timeline-shell {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-header,
.timeline-item-head,
.settlement-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.timeline-header h3 {
  margin: 0;
  font-size: 16px;
}

.timeline-header p {
  margin: 4px 0 0;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.timeline-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.timeline-item,
.abnormal-item {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-blank);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-item-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-item-title {
  font-weight: 600;
}

.timeline-item-role,
.timeline-item-meta,
.timeline-item-hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.timeline-item-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-item-summary {
  color: var(--el-text-color-primary);
}

.abnormal-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settlement-card,
.abnormal-card {
  width: 100%;
}
</style>
