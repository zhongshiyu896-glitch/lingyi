import { reactive } from 'vue'
import { fetchBomActions, fetchCurrentUser, fetchModuleActions } from '@/api/auth'

// Action codes from /api/auth/actions
export const ACTION_BOM_CREATE = 'bom:create'
export const ACTION_BOM_PUBLISH = 'bom:publish'
export const ACTION_BOM_SET_DEFAULT = 'bom:set_default'

interface ButtonPermissions {
  create: boolean
  update: boolean
  publish: boolean
  deactivate: boolean
  set_default: boolean
  read: boolean
  plan_create: boolean
  material_check: boolean
  work_order_create: boolean
  ticket_register: boolean
  ticket_reversal: boolean
  ticket_batch: boolean
  wage_read: boolean
  wage_rate_read: boolean
  wage_rate_read_all: boolean
  wage_rate_manage: boolean
  wage_rate_manage_all: boolean
  job_card_sync: boolean
  issue_material: boolean
  receive: boolean
  inspect: boolean
  cancel: boolean
  stock_sync_retry: boolean
  stock_sync_worker: boolean
  work_order_worker: boolean
  job_card_sync_worker: boolean
  factory_statement_read: boolean
  factory_statement_create: boolean
  factory_statement_confirm: boolean
  factory_statement_cancel: boolean
  factory_statement_payable_draft_create: boolean
  factory_statement_payable_draft_worker: boolean
  sales_inventory_read: boolean
  sales_inventory_export: boolean
  sales_inventory_diagnostic: boolean
  quality_read: boolean
  quality_create: boolean
  quality_update: boolean
  quality_confirm: boolean
  quality_cancel: boolean
  quality_export: boolean
  quality_diagnostic: boolean
}

interface PermissionState {
  username: string
  roles: string[]
  module: string
  actions: string[]
  status: string
  loading: boolean
  buttonPermissions: ButtonPermissions
}

const emptyButtonPermissions = (): ButtonPermissions => ({
  create: false,
  update: false,
  publish: false,
  deactivate: false,
  set_default: false,
  read: false,
  plan_create: false,
  material_check: false,
  work_order_create: false,
  ticket_register: false,
  ticket_reversal: false,
  ticket_batch: false,
  wage_read: false,
  wage_rate_read: false,
  wage_rate_read_all: false,
  wage_rate_manage: false,
  wage_rate_manage_all: false,
  job_card_sync: false,
  issue_material: false,
  receive: false,
  inspect: false,
  cancel: false,
  stock_sync_retry: false,
  stock_sync_worker: false,
  work_order_worker: false,
  job_card_sync_worker: false,
  factory_statement_read: false,
  factory_statement_create: false,
  factory_statement_confirm: false,
  factory_statement_cancel: false,
  factory_statement_payable_draft_create: false,
  factory_statement_payable_draft_worker: false,
  sales_inventory_read: false,
  sales_inventory_export: false,
  sales_inventory_diagnostic: false,
  quality_read: false,
  quality_create: false,
  quality_update: false,
  quality_confirm: false,
  quality_cancel: false,
  quality_export: false,
  quality_diagnostic: false,
})

const INTERNAL_NON_UI_ACTIONS = new Set<string>([
  'workshop:job_card_sync_worker',
  'subcontract:stock_sync_worker',
  'production:work_order_worker',
  'factory_statement:payable_draft_worker',
  'sales_inventory:diagnostic',
  'quality:diagnostic',
])

const forceClearInternalButtonPermissions = (buttons: ButtonPermissions): ButtonPermissions => ({
  ...buttons,
  stock_sync_worker: false,
  work_order_worker: false,
  job_card_sync_worker: false,
  factory_statement_payable_draft_worker: false,
  sales_inventory_diagnostic: false,
  quality_diagnostic: false,
})

const state = reactive<PermissionState>({
  username: '',
  roles: [],
  module: 'bom',
  actions: [],
  status: '',
  loading: false,
  buttonPermissions: emptyButtonPermissions(),
})

const AUTH_ME_GUEST_CACHE_KEY = 'lingyi.auth_me_guest_until'
const AUTH_ME_GUEST_CACHE_TTL_MS = 15000

const readGuestCacheUntil = (): number => {
  if (typeof window === 'undefined') return 0
  const raw = window.sessionStorage.getItem(AUTH_ME_GUEST_CACHE_KEY)
  if (!raw) return 0
  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : 0
}

const writeGuestCacheUntil = (untilMs: number): void => {
  if (typeof window === 'undefined') return
  window.sessionStorage.setItem(AUTH_ME_GUEST_CACHE_KEY, String(untilMs))
}

const clearGuestCache = (): void => {
  if (typeof window === 'undefined') return
  window.sessionStorage.removeItem(AUTH_ME_GUEST_CACHE_KEY)
}

const applyGuestState = (): void => {
  state.username = ''
  state.roles = []
  state.actions = []
  state.status = 'guest'
  state.buttonPermissions = emptyButtonPermissions()
}

let currentUserLoadPromise: Promise<void> | null = null

const isUnauthorizedError = (error: unknown): boolean =>
  error instanceof Error && (error.message.includes('未登录') || error.message.includes('登录已失效'))

const applyActionPayload = (payload: {
  actions: string[]
  button_permissions: Partial<ButtonPermissions>
  module?: string
  status?: string | null
}): void => {
  state.actions = (payload.actions || []).filter((action) => !INTERNAL_NON_UI_ACTIONS.has(action))
  state.buttonPermissions = forceClearInternalButtonPermissions({
    ...emptyButtonPermissions(),
    ...(payload.button_permissions || {}),
  })
  if (payload.module) {
    state.module = payload.module
  }
  state.status = payload.status || ''
}

export const usePermissionStore = () => {
  const loadCurrentUser = async (options?: { force?: boolean }): Promise<void> => {
    const force = Boolean(options?.force)
    if (!force && readGuestCacheUntil() > Date.now()) {
      applyGuestState()
      return
    }
    if (!force && currentUserLoadPromise) {
      await currentUserLoadPromise
      return
    }

    const run = async (): Promise<void> => {
      try {
        const result = await fetchCurrentUser()
        state.username = result.data.username
        state.roles = result.data.roles
        state.status = ''
        clearGuestCache()
      } catch (error) {
        if (isUnauthorizedError(error)) {
          applyGuestState()
          writeGuestCacheUntil(Date.now() + AUTH_ME_GUEST_CACHE_TTL_MS)
          return
        }
        throw error
      }
    }

    if (force) {
      await run()
      return
    }

    currentUserLoadPromise = run()
    try {
      await currentUserLoadPromise
    } finally {
      currentUserLoadPromise = null
    }
  }

  const refreshCurrentUser = async (): Promise<void> => {
    await loadCurrentUser({ force: true })
  }

  const loadModuleActions = async (module = 'bom'): Promise<void> => {
    if (!state.username || state.status === 'guest') {
      state.module = module
      state.actions = []
      state.status = 'guest'
      state.buttonPermissions = emptyButtonPermissions()
      return
    }
    state.loading = true
    try {
      const result = await fetchModuleActions({ module })
      applyActionPayload(result.data)
    } finally {
      state.loading = false
    }
  }

  const loadBomActions = async (bomId: number): Promise<void> => {
    if (!state.username || state.status === 'guest') {
      state.actions = []
      state.status = 'guest'
      state.buttonPermissions = emptyButtonPermissions()
      return
    }
    state.loading = true
    try {
      const result = await fetchBomActions(bomId)
      applyActionPayload(result.data)
    } finally {
      state.loading = false
    }
  }

  return {
    state,
    loadCurrentUser,
    refreshCurrentUser,
    loadModuleActions,
    loadBomActions,
  }
}
