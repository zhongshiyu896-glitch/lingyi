<template>
  <section class="module-entry-board" data-testid="cand260-dashboard-module-entry-readonly">
    <header>
      <div>
        <h2>六大模块入口可达性与守卫矩阵</h2>
        <p>只服务六大模块入口、导航、可达性与只读守卫，不回到非模块入口说明或 dashboard 弱联动子区。</p>
      </div>
      <div class="module-entry-tags">
        <el-tag effect="plain" type="info">source_layer={{ sourceLayer }}</el-tag>
        <el-tag effect="plain" type="success">final_path={{ finalPath }}</el-tag>
      </div>
    </header>

    <div class="module-entry-grid">
      <article v-for="item in items" :key="item.key" class="module-entry-card">
        <div class="module-entry-top">
          <div>
            <h3>{{ item.label }}</h3>
            <p>{{ item.sourceDescription }}</p>
          </div>
          <div class="module-entry-status">
            <el-tag effect="plain" :type="item.reachabilityTone">{{ item.reachabilityLabel }}</el-tag>
            <el-tag effect="plain" :type="item.guardTone">{{ item.guardLabel }}</el-tag>
          </div>
        </div>
        <div class="module-entry-meta">
          <span>path={{ item.path }}</span>
          <span>source_module={{ item.sourceModule }}</span>
          <span>source_route={{ item.sourceRoute }}</span>
        </div>
        <div class="module-entry-meta">
          <span>reachability={{ item.reachabilityLabel }}</span>
          <span>guard_state={{ item.guardLabel }}</span>
        </div>
        <div class="module-entry-meta">
          <span>entry_semantic={{ item.entrySemantic }}</span>
        </div>
        <small>{{ item.blockedReason }}</small>
        <small>{{ item.note }}</small>
        <div class="module-entry-actions">
          <el-button size="small" type="primary" plain :disabled="item.entryDisabled" @click="emitNavigate(item.path)">
            只读进入
          </el-button>
          <el-button size="small" disabled>{{ item.guardLabel }}</el-button>
        </div>
      </article>
    </div>

    <section class="module-action-guard-board" data-testid="cand260-dashboard-module-entry-actions">
      <header>
        <h3>入口守卫动作</h3>
      </header>
      <div class="module-action-list">
        <article v-for="item in readonlyActions" :key="item.key" class="module-action-item">
          <el-button size="small" disabled>{{ item.label }}</el-button>
          <small>{{ item.reason }}</small>
        </article>
      </div>
    </section>

    <div class="module-entry-remaining-gap" data-testid="cand260-dashboard-module-entry-remaining-gap">
      <el-tag effect="plain" type="danger">remaining_gap</el-tag>
      <span>{{ remainingGap }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type {
  DashboardModuleEntryReadonlyActionItem,
  DashboardModuleEntryReadonlyItem,
} from '../composables/useDashboardModuleEntryReadonly'

defineProps({
  items: {
    type: Array as PropType<DashboardModuleEntryReadonlyItem[]>,
    required: true,
  },
  readonlyActions: {
    type: Array as PropType<DashboardModuleEntryReadonlyActionItem[]>,
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

const emit = defineEmits<{
  navigate: [path: string]
}>()

const emitNavigate = (path: string): void => {
  emit('navigate', path)
}
</script>

<style scoped>
.module-entry-board,
.module-action-guard-board {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.module-entry-board,
.module-action-guard-board {
  padding: 14px;
}

.module-entry-board {
  display: grid;
  gap: 12px;
}

.module-entry-board > header,
.module-action-guard-board > header,
.module-entry-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.module-entry-board h2,
.module-action-guard-board h3,
.module-entry-card h3 {
  margin: 0;
}

.module-entry-board > header p,
.module-entry-card p,
.module-entry-card small,
.module-action-item small {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.module-entry-tags,
.module-entry-status,
.module-entry-meta,
.module-entry-remaining-gap,
.module-entry-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.module-entry-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}

.module-entry-card,
.module-action-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}

.module-entry-card {
  display: grid;
  gap: 8px;
}

.module-entry-meta {
  color: #4b5563;
  font-size: 12px;
}

.module-action-list {
  display: grid;
  gap: 10px;
}

.module-action-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.module-entry-remaining-gap {
  color: #4b5563;
  font-size: 12px;
}
</style>
