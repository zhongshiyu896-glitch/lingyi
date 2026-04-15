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
})

const INTERNAL_NON_UI_ACTIONS = new Set<string>([
  'workshop:job_card_sync_worker',
  'subcontract:stock_sync_worker',
  'production:work_order_worker',
  'factory_statement:payable_draft_worker',
])

const forceClearInternalButtonPermissions = (buttons: ButtonPermissions): ButtonPermissions => ({
  ...buttons,
  stock_sync_worker: false,
  work_order_worker: false,
  job_card_sync_worker: false,
  factory_statement_payable_draft_worker: false,
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
  const loadCurrentUser = async (): Promise<void> => {
    const result = await fetchCurrentUser()
    state.username = result.data.username
    state.roles = result.data.roles
  }

  const loadModuleActions = async (module = 'bom'): Promise<void> => {
    state.loading = true
    try {
      const result = await fetchModuleActions({ module })
      applyActionPayload(result.data)
    } finally {
      state.loading = false
    }
  }

  const loadBomActions = async (bomId: number): Promise<void> => {
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
    loadModuleActions,
    loadBomActions,
  }
}
