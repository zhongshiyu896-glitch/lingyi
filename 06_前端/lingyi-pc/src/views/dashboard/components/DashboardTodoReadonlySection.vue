<template>
  <section class="todo-readonly-board" data-testid="cand254-dashboard-todo-readonly">
    <header>
      <div>
        <h2>待办老化与入口来源</h2>
        <p>只读钻取待办老化、入口来源与逾期桶，不改写主工作台、告警来源审计或趋势新鲜度子区。</p>
      </div>
      <div class="todo-header-tags">
        <el-tag effect="plain" type="info">source_layer={{ sourceLayer }}</el-tag>
        <el-tag effect="plain" type="success">final_path={{ finalPath }}</el-tag>
      </div>
    </header>

    <div class="todo-aging-grid" data-testid="cand254-todo-aging-summary">
      <article v-for="item in agingItems" :key="item.key" class="todo-aging-card">
        <div class="todo-aging-top">
          <div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.sourceDescription }}</p>
          </div>
          <el-tag effect="plain" :type="item.statusTone">{{ item.statusLabel }}</el-tag>
        </div>
        <strong class="todo-aging-count">{{ item.count }} 项</strong>
        <div class="todo-aging-meta">
          <span>entry_source={{ item.entrySource }}</span>
          <span>source_module={{ item.sourceModule }}</span>
          <span>source_route={{ item.sourceRoute }}</span>
        </div>
        <div class="todo-aging-meta">
          <span>overdue_bucket={{ item.overdueBucket }}</span>
          <span>aging_status={{ item.agingStatus }}</span>
        </div>
        <small>{{ item.blockedReason }}</small>
        <small>{{ item.note }}</small>
      </article>
    </div>

    <section class="todo-action-guard-board" data-testid="cand254-todo-readonly-actions">
      <header>
        <h3>只读动作守卫</h3>
      </header>
      <div class="todo-action-list">
        <article v-for="item in readonlyActions" :key="item.key" class="todo-action-item">
          <el-button size="small" disabled>{{ item.label }}</el-button>
          <small>{{ item.reason }}</small>
        </article>
      </div>
    </section>

    <div class="todo-remaining-gap" data-testid="cand254-todo-remaining-gap">
      <el-tag effect="plain" type="danger">remaining_gap</el-tag>
      <span>{{ remainingGap }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { PropType } from 'vue'
import type {
  DashboardTodoReadonlyActionItem,
  DashboardTodoReadonlyItem,
} from '../composables/useDashboardTodoReadonly'

defineProps({
  agingItems: {
    type: Array as PropType<DashboardTodoReadonlyItem[]>,
    required: true,
  },
  readonlyActions: {
    type: Array as PropType<DashboardTodoReadonlyActionItem[]>,
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
.todo-readonly-board,
.todo-action-guard-board {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.todo-readonly-board,
.todo-action-guard-board {
  padding: 14px;
}

.todo-readonly-board {
  display: grid;
  gap: 12px;
}

.todo-readonly-board > header,
.todo-action-guard-board > header,
.todo-aging-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.todo-readonly-board h2,
.todo-action-guard-board h3,
.todo-aging-card h3 {
  margin: 0;
}

.todo-readonly-board > header p,
.todo-aging-card p,
.todo-aging-card small,
.todo-action-item small {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.todo-header-tags,
.todo-aging-meta,
.todo-remaining-gap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.todo-aging-grid {
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.todo-aging-card,
.todo-action-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  padding: 10px;
}

.todo-aging-card {
  display: grid;
  gap: 8px;
}

.todo-aging-count {
  font-size: 18px;
}

.todo-aging-meta,
.todo-aging-count {
  color: #4b5563;
}

.todo-aging-meta {
  font-size: 12px;
}

.todo-action-list {
  display: grid;
  gap: 10px;
}

.todo-action-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.todo-remaining-gap {
  color: #4b5563;
  font-size: 12px;
}
</style>
