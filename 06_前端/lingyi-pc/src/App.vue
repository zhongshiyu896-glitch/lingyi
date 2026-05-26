<template>
  <section
    id="global-readonly-shell"
    class="global-readonly-shell"
    data-testid="global-readonly-shell"
    data-readonly-boundary="true"
    data-write-request-success-allowed="false"
    data-real-write-action-added="false"
  >
    <div class="global-readonly-shell__identity">
      <strong>{{ sessionTitle }}</strong>
      <span
        id="global-auth-fallback-state"
        data-testid="global-auth-fallback-state"
        :data-auth-status="authStatus"
      >
        {{ authFallbackText }}
      </span>
    </div>
    <div
      id="global-permission-state"
      class="global-readonly-shell__state"
      data-testid="global-permission-state"
      :data-module="routeModule"
      :data-permission-status="permissionStatus"
    >
      <span>模块权限：{{ permissionStateText }}</span>
      <span
        id="z042-global-route-context"
        class="global-readonly-shell__context"
        data-testid="z042-global-route-context"
        :data-route-category="routeCategory"
        :data-route-path="route.path"
      >
        {{ routeContextText }}
      </span>
      <span
        id="global-route-readonly-badge"
        class="global-readonly-shell__badge"
        data-testid="global-route-readonly-badge"
        :data-route="route.path"
      >
        {{ routeBadgeText }}
      </span>
    </div>
    <div
      id="global-permission-actions-preview"
      class="global-readonly-shell__actions"
      data-testid="global-permission-actions-preview"
    >
      <button
        id="global-auth-refresh-guard"
        type="button"
        class="global-readonly-shell__button"
        data-testid="global-auth-refresh-guard"
        data-write-guard="guarded:global-readonly-shell"
        data-readonly-action="fetchCurrentUser"
        :disabled="permissionStore.state.loading"
        @click="refreshReadonlySession"
      >
        <span
          id="z042-global-guarded-refresh"
          data-testid="z042-global-guarded-refresh"
          data-write-guard="guarded:z042-global-route-context-readonly"
        >
          刷新权限
        </span>
      </button>
      <button
        type="button"
        class="global-readonly-shell__button"
        data-write-guard="guarded:global-module-actions-readonly"
        data-readonly-action="fetchModuleActions"
        :disabled="permissionStore.state.loading"
        @click="reloadReadonlyModuleActions"
      >
        重载模块动作
      </button>
      <button
        id="global-readonly-write-guard"
        type="button"
        class="global-readonly-shell__button global-readonly-shell__button--disabled"
        data-testid="global-readonly-write-guard"
        data-write-guard="guarded:global-readonly-confirm"
        disabled
      >
        只读确认
      </button>
      <span
        id="global-remote-lifecycle-parked"
        class="global-readonly-shell__parked"
        data-testid="global-remote-lifecycle-parked"
      >
        remote lifecycle parked
      </span>
      <span
        id="z042-global-fallback-explanation"
        class="global-readonly-shell__fallback"
        data-testid="z042-global-fallback-explanation"
        :data-readonly-fallback-reason="fallbackReason"
      >
        {{ fallbackExplanationText }}
      </span>
    </div>
  </section>
  <router-view />
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

import { usePermissionStore } from '@/stores/permission'

const permissionStore = usePermissionStore()
const route = useRoute()

const routeModule = computed(() => {
  if (route.path.startsWith('/permissions')) return 'permission_governance'
  if (route.path.startsWith('/reports')) return 'report'
  if (route.path.startsWith('/workshop')) return 'workshop'
  if (route.path.startsWith('/sales-inventory')) return 'sales_inventory'
  return 'global'
})

const routeCategory = computed(() => {
  if (route.path === '/home' || route.path === '/') return 'home'
  if (route.path.startsWith('/reports')) return 'report-catalog'
  if (route.path.startsWith('/workshop')) return 'workshop-ticket'
  if (route.path.startsWith('/permissions')) return 'permission-governance'
  return 'global-readonly'
})

const authStatus = computed(() => {
  if (permissionStore.state.status === 'guest' || !permissionStore.state.username) return 'readonly-fallback'
  return permissionStore.state.username ? 'authenticated-readonly' : 'pending-readonly'
})

const sessionTitle = computed(() => {
  if (permissionStore.state.username) return `会话：${permissionStore.state.username}`
  return '会话：Guest'
})

const authFallbackText = computed(() => {
  if (permissionStore.state.status === 'guest' || !permissionStore.state.username) return 'guest/readonly fallback'
  if (permissionStore.state.loading) return '权限读取中'
  return 'readonly session'
})

const permissionStatus = computed(() => permissionStore.state.status || 'readonly')

const permissionStateText = computed(() => {
  if (permissionStore.state.status === 'guest') return 'guest fallback, no write privileges'
  const actionCount = permissionStore.state.actions.length
  return `${routeModule.value} / ${actionCount} readonly actions`
})

const routeBadgeText = computed(() => `${route.path || '/'} readonly boundary`)

const routeContextText = computed(() => {
  const categoryText: Record<string, string> = {
    home: '首页上下文',
    'report-catalog': '报表目录上下文',
    'workshop-ticket': '车间工票上下文',
    'permission-governance': '权限治理上下文',
    'global-readonly': '全局只读上下文',
  }
  return `路由分类：${categoryText[routeCategory.value]}`
})

const fallbackReason = computed(() => {
  if (permissionStore.state.status === 'guest' || !permissionStore.state.username) return 'guest-readonly-fallback'
  if (permissionStore.state.loading) return 'permission-loading-readonly'
  return 'authenticated-readonly-boundary'
})

const fallbackExplanationText = computed(() => {
  const explanations: Record<string, string> = {
    'guest-readonly-fallback': 'fallback 原因：未取得写权限，会话保持只读',
    'permission-loading-readonly': 'fallback 原因：权限读取中，写入口继续 guarded',
    'authenticated-readonly-boundary': 'fallback 原因：当前会话仍受只读边界保护',
  }
  return explanations[fallbackReason.value]
})

const loadReadonlyState = async (): Promise<void> => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions(routeModule.value)
  } catch {
    // Keep the shell usable as readonly fallback when auth services are unavailable.
  }
}

const refreshReadonlySession = async (): Promise<void> => {
  try {
    await permissionStore.refreshCurrentUser()
    await permissionStore.loadModuleActions(routeModule.value)
  } catch {
    // Readonly guard keeps failures visible without escalating into write semantics.
  }
}

const reloadReadonlyModuleActions = async (): Promise<void> => {
  try {
    await permissionStore.loadModuleActions(routeModule.value)
  } catch {
    // Module action reload is read-only and guarded.
  }
}

onMounted(() => {
  void loadReadonlyState()
})

watch(
  () => route.path,
  () => {
    void reloadReadonlyModuleActions()
  },
)
</script>

<style scoped>
.global-readonly-shell {
  position: sticky;
  top: 0;
  z-index: 20;
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(220px, 1.4fr) auto;
  gap: 12px;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #d7dce5;
  background: #f8fafc;
  color: #182233;
  font-size: 13px;
  letter-spacing: 0;
  box-sizing: border-box;
}

.global-readonly-shell__identity,
.global-readonly-shell__state,
.global-readonly-shell__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.global-readonly-shell__identity,
.global-readonly-shell__state {
  flex-wrap: wrap;
}

.global-readonly-shell__actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}

.global-readonly-shell__badge,
.global-readonly-shell__parked,
.global-readonly-shell__context,
.global-readonly-shell__fallback {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 8px;
  border: 1px solid #c8d2df;
  background: #ffffff;
  color: #405168;
  border-radius: 6px;
  white-space: nowrap;
}

.global-readonly-shell__context {
  border-color: #b8c7d9;
  background: #eef5ff;
  color: #25456b;
}

.global-readonly-shell__fallback {
  border-color: #d2c3a7;
  background: #fff8eb;
  color: #5f4723;
}

.global-readonly-shell__button {
  min-height: 28px;
  padding: 0 10px;
  border: 1px solid #b7c4d4;
  background: #ffffff;
  color: #223047;
  border-radius: 6px;
  cursor: pointer;
}

.global-readonly-shell__button:disabled,
.global-readonly-shell__button--disabled {
  color: #6b778a;
  background: #eef2f7;
  cursor: not-allowed;
}

@media (max-width: 920px) {
  .global-readonly-shell {
    grid-template-columns: 1fr;
  }

  .global-readonly-shell__actions {
    justify-content: flex-start;
  }
}
</style>
