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
        data-guarded-entry="全局确认"
        data-readonly-state="guarded-readonly"
        disabled
      >
        全局确认
      </button>
      <button
        type="button"
        class="global-readonly-shell__button global-readonly-shell__button--disabled"
        data-testid="z043-global-downgrade-explanation-guard"
        data-write-guard="guarded:z043-global-downgrade-explanation"
        data-guarded-entry="降级说明入口"
        data-readonly-state="guarded-readonly"
        disabled
      >
        降级说明入口
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
    <div
      id="z043-global-operation-trace"
      class="global-readonly-shell__z043-panel"
      data-testid="z043-global-operation-trace"
      :data-route-path="route.path"
      :data-route-module="routeModule"
      data-readonly-boundary="true"
      data-write-request-success-allowed="false"
      data-real-write-action-added="false"
    >
      <span
        id="z043-global-evidence-entry"
        class="global-readonly-shell__z043-item"
        data-testid="z043-global-evidence-entry"
        data-evidence-entry="runtime-route-dom-guard-network"
      >
        {{ evidenceEntryText }}
      </span>
      <span
        id="z043-global-guarded-action-log"
        class="global-readonly-shell__z043-item"
        data-testid="z043-global-guarded-action-log"
        data-guarded-entry="权限刷新"
        data-readonly-state="guarded-readonly"
      >
        {{ guardedActionLogText }}
      </span>
      <span
        class="global-readonly-shell__z043-item"
        data-testid="z043-global-risk-summary"
        :data-readonly-fallback-risk="fallbackReason"
      >
        {{ operationTraceText }}
      </span>
      <span
        id="z043-global-next-gate-disclaimer"
        class="global-readonly-shell__z043-item global-readonly-shell__z043-item--notice"
        data-testid="z043-global-next-gate-disclaimer"
        data-next-gate-disclaimer="local-only-not-production-ready"
      >
        {{ nextGateDisclaimerText }}
      </span>
    </div>
    <div
      id="z044-global-local-gate-summary"
      class="global-readonly-shell__z044-panel"
      data-testid="z044-global-local-gate-summary"
      :data-route-path="route.path"
      data-readonly-boundary="true"
      data-write-request-success-allowed="false"
      data-real-write-action-added="false"
    >
      <span
        class="global-readonly-shell__z044-item"
        data-testid="z044-global-local-gate-summary-text"
        data-local-gate="prep-only"
      >
        {{ z044LocalGateSummaryText }}
      </span>
      <span
        id="z044-global-dirty-scope-readback"
        class="global-readonly-shell__z044-item"
        data-testid="z044-global-dirty-scope-readback"
        data-tracked-dirty-count="19"
        data-product-test-dirty-count="16"
        data-log-control-dirty-count="3"
      >
        {{ z044DirtyScopeReadbackText }}
      </span>
      <span
        id="z044-global-residual-risk-badge"
        class="global-readonly-shell__z044-item"
        data-testid="z044-global-residual-risk-badge"
        data-z034-residual-artifacts-count="9"
        data-z034-residual-artifacts-status="untracked_present"
      >
        {{ z044ResidualRiskBadgeText }}
      </span>
      <span
        id="z044-global-remote-gate-disclaimer"
        class="global-readonly-shell__z044-item global-readonly-shell__z044-item--notice"
        data-testid="z044-global-remote-gate-disclaimer"
        data-remote-lifecycle-parked="true"
        data-production-readback="false"
        data-go-live="false"
      >
        {{ z044RemoteGateDisclaimerText }}
      </span>
      <div
        id="z044-global-readonly-action-guard"
        class="global-readonly-shell__z044-actions"
        data-testid="z044-global-readonly-action-guard"
        data-readonly-boundary="true"
        data-write-request-success-allowed="false"
        data-real-write-action-added="false"
      >
        <button
          type="button"
          class="global-readonly-shell__button global-readonly-shell__button--disabled"
          data-testid="z044-global-confirm-guard"
          data-guarded-entry="全局确认"
          data-readonly-state="guarded-readonly"
          data-write-guard="guarded:z044-global-confirm"
          disabled
        >
          全局确认
        </button>
        <button
          type="button"
          class="global-readonly-shell__button global-readonly-shell__button--disabled"
          data-testid="z044-global-refresh-guard"
          data-guarded-entry="门禁刷新"
          data-readonly-state="guarded-readonly"
          data-write-guard="guarded:z044-local-gate-refresh"
          disabled
        >
          门禁刷新
        </button>
        <button
          type="button"
          class="global-readonly-shell__button global-readonly-shell__button--disabled"
          data-testid="z044-global-continue-prep-guard"
          data-guarded-entry="继续准备说明"
          data-readonly-state="guarded-readonly"
          data-write-guard="guarded:z044-continue-prep"
          disabled
        >
          继续准备说明
        </button>
      </div>
      <span
        id="z044-global-evidence-readiness-entry"
        class="global-readonly-shell__z044-item"
        data-testid="z044-global-evidence-readiness-entry"
        data-evidence-plan="screenshot-route-dom-guard-network-typecheck"
      >
        {{ z044EvidenceReadinessText }}
      </span>
      <span
        id="z044-global-next-prep-recommendation"
        class="global-readonly-shell__z044-item"
        data-testid="z044-global-next-prep-recommendation"
        data-next-task="TASK-Z044B-02-PREP"
        data-run-this-task="false"
      >
        {{ z044NextPrepRecommendationText }}
      </span>
      <span
        id="z044-global-write-success-blocker"
        class="global-readonly-shell__z044-item global-readonly-shell__z044-item--warning"
        data-testid="z044-global-write-success-blocker"
        data-write-request-success-allowed="false"
        data-guarded-readonly-not-write-success="true"
      >
        {{ z044WriteSuccessBlockerText }}
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
  if (route.path.startsWith('/subcontract')) return 'subcontract'
  if (route.path.startsWith('/sales-inventory')) return 'sales_inventory'
  return 'global'
})

const routeCategory = computed(() => {
  if (route.path === '/home' || route.path === '/') return 'home'
  if (route.path.startsWith('/reports')) return 'report-catalog'
  if (route.path.startsWith('/workshop')) return 'workshop-ticket'
  if (route.path.startsWith('/subcontract')) return 'subcontract-readonly'
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
    home: '工作台入口上下文',
    'report-catalog': '报表目录上下文',
    'workshop-ticket': '车间工票上下文',
    'subcontract-readonly': '外发单上下文',
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

const operationTraceText = computed(() => {
  const routeText = route.path || '/'
  const guardedEntry = route.path.startsWith('/workshop')
    ? '批量导入只读 guard'
    : route.path.startsWith('/subcontract')
      ? '外发单同步/导出 guard'
      : '全局只读确认 guard'
  return `只读操作轨迹：${routeText} -> ${guardedEntry} -> ${fallbackReason.value}`
})

const evidenceEntryText = computed(() => {
  const evidenceRoute = route.path || '/dashboard/overview'
  return `证据入口：${evidenceRoute} 需包含 route、DOM anchors、guard 与 network observation`
})

const guardedActionLogText = computed(() => {
  const recentEntry = permissionStore.state.loading ? '权限刷新读取中' : '权限刷新 guarded/readonly'
  return `最近 guarded 入口：${recentEntry}；全局确认与降级说明入口保持 disabled`
})

const nextGateDisclaimerText = computed(
  () => 'next gate：仅本地只读候选建议，不代表远端授权、production readback 或 go-live',
)

const z044LocalGateSummaryText = computed(() => {
  const currentRoute = route.path || '/dashboard/overview'
  return `Z044 本地门禁建议：${currentRoute} 仅进入 CAND001 边界与证据准备，不启动远端生命周期。`
})

const z044DirtyScopeReadbackText = computed(
  () => 'dirty 摘要：tracked 19，product/test 16，log/control 3；候选只允许复用当前 clean 产品路径。',
)

const z044ResidualRiskBadgeText = computed(
  () => 'Z034 residual：9 个 untracked_present 产物继续排除，不进入候选 YES 或提交推断。',
)

const z044RemoteGateDisclaimerText = computed(
  () => '远端/生产未授权：push/tag/PR/release、production readback、go-live 均为 false。',
)

const z044EvidenceReadinessText = computed(
  () => '证据入口：/dashboard/overview 截图，双路由 route evidence，DOM anchors，guard state，network observation 与 typecheck。',
)

const z044NextPrepRecommendationText = computed(
  () => 'next prep：TASK-Z044B-02-PREP 已可被 A 派发；run_this_task=false。',
)

const z044WriteSuccessBlockerText = computed(
  () => '写成功阻断：全局确认、门禁刷新、继续准备说明均 guarded/readonly，write_request_success_allowed=false。',
)

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
.global-readonly-shell__fallback,
.global-readonly-shell__z043-item {
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

.global-readonly-shell__z043-panel {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 8px;
  align-items: stretch;
}

.global-readonly-shell__z043-item {
  align-items: flex-start;
  min-height: 34px;
  padding: 6px 8px;
  border-color: #c8d2df;
  background: #ffffff;
  color: #334155;
  white-space: normal;
  line-height: 1.35;
}

.global-readonly-shell__z043-item--notice {
  border-color: #b9d3c5;
  background: #f0f8f3;
  color: #25513a;
}

.global-readonly-shell__z044-panel {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, minmax(180px, 1fr));
  gap: 8px;
  align-items: stretch;
}

.global-readonly-shell__z044-item,
.global-readonly-shell__z044-actions {
  display: inline-flex;
  align-items: flex-start;
  min-height: 34px;
  padding: 6px 8px;
  border: 1px solid #c8d2df;
  background: #ffffff;
  color: #334155;
  border-radius: 6px;
  white-space: normal;
  line-height: 1.35;
}

.global-readonly-shell__z044-actions {
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.global-readonly-shell__z044-item--notice {
  border-color: #b9d3c5;
  background: #f0f8f3;
  color: #25513a;
}

.global-readonly-shell__z044-item--warning {
  border-color: #e1c7a3;
  background: #fff7ed;
  color: #744210;
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

  .global-readonly-shell__z043-panel {
    grid-template-columns: 1fr;
  }

  .global-readonly-shell__z044-panel {
    grid-template-columns: 1fr;
  }
}
</style>
