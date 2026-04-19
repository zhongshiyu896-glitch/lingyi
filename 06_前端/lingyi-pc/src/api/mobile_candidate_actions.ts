export type MobileCandidateActionName =
  | 'message_ack'
  | 'notification_read_receipt'
  | 'collaboration_confirm'
  | 'scan_request'
  | 'upload_request'
  | 'sync_queued'
  | 'sync_completed'
  | 'sync_failed'
  | 'push_bind'
  | 'push_unbind'

export type MobileCandidateActionState = 'frozen'

export type MobileCandidateActionCode = 'disabled_by_design' | 'pending_design' | 'not_enabled'

export interface MobileCandidateActionContext {
  request_id: string
  device_id: string
  user_id: string
  company: string
}

export interface MobileCandidateActionContextInput {
  request_id?: string | null
  device_id?: string | null
  user_id?: string | null
  company?: string | null
}

export interface MobileCandidateActionResult {
  action: MobileCandidateActionName
  state: MobileCandidateActionState
  code: MobileCandidateActionCode
  message: string
  request_id: string
  device_id: string
  user_id: string
  company: string
  missing_fields: string[]
  timestamp: string
}

export interface MobileCandidateActionDispatchInput {
  action: MobileCandidateActionName
  context: MobileCandidateActionContextInput
  preferred_code?: MobileCandidateActionCode
}

const REQUIRED_CONTEXT_FIELDS: Array<keyof MobileCandidateActionContext> = [
  'request_id',
  'device_id',
  'user_id',
  'company',
]

export const MOBILE_CANDIDATE_ACTIONS: MobileCandidateActionName[] = [
  'message_ack',
  'notification_read_receipt',
  'collaboration_confirm',
  'scan_request',
  'upload_request',
  'sync_queued',
  'sync_completed',
  'sync_failed',
  'push_bind',
  'push_unbind',
]

const toNonEmptyString = (value?: string | null): string => {
  if (value === undefined || value === null) {
    return ''
  }
  return String(value).trim()
}

const resolveContext = (
  input: MobileCandidateActionContextInput,
): { context: MobileCandidateActionContext; missingFields: string[] } => {
  const context: MobileCandidateActionContext = {
    request_id: toNonEmptyString(input.request_id),
    device_id: toNonEmptyString(input.device_id),
    user_id: toNonEmptyString(input.user_id),
    company: toNonEmptyString(input.company),
  }

  const missingFields = REQUIRED_CONTEXT_FIELDS.filter((field) => !context[field])

  return {
    context,
    missingFields,
  }
}

const buildFrozenResult = (
  action: MobileCandidateActionName,
  context: MobileCandidateActionContext,
  code: MobileCandidateActionCode,
  message: string,
  missingFields: string[] = [],
): MobileCandidateActionResult => {
  return {
    action,
    state: 'frozen',
    code,
    message,
    request_id: context.request_id,
    device_id: context.device_id,
    user_id: context.user_id,
    company: context.company,
    missing_fields: missingFields,
    timestamp: new Date().toISOString(),
  }
}

export const runMobileCandidateAction = async (
  input: MobileCandidateActionDispatchInput,
): Promise<MobileCandidateActionResult> => {
  const { context, missingFields } = resolveContext(input.context)

  if (missingFields.length > 0) {
    return buildFrozenResult(
      input.action,
      context,
      'not_enabled',
      'candidate action is not enabled because required context is missing',
      missingFields,
    )
  }

  const code = input.preferred_code ?? 'disabled_by_design'

  return buildFrozenResult(
    input.action,
    context,
    code,
    'candidate action is frozen by design and cannot execute write semantics',
  )
}

export const candidateMessageAck = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> => runMobileCandidateAction({ action: 'message_ack', context })

export const candidateNotificationReadReceipt = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> =>
  runMobileCandidateAction({ action: 'notification_read_receipt', context })

export const candidateCollaborationConfirm = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> =>
  runMobileCandidateAction({ action: 'collaboration_confirm', context })

export const candidateScanRequest = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> => runMobileCandidateAction({ action: 'scan_request', context })

export const candidateUploadRequest = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> => runMobileCandidateAction({ action: 'upload_request', context })

export const candidateSyncQueued = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> =>
  runMobileCandidateAction({ action: 'sync_queued', context, preferred_code: 'pending_design' })

export const candidateSyncCompleted = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> =>
  runMobileCandidateAction({ action: 'sync_completed', context, preferred_code: 'pending_design' })

export const candidateSyncFailed = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> =>
  runMobileCandidateAction({ action: 'sync_failed', context, preferred_code: 'pending_design' })

export const candidatePushBind = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> => runMobileCandidateAction({ action: 'push_bind', context })

export const candidatePushUnbind = async (
  context: MobileCandidateActionContextInput,
): Promise<MobileCandidateActionResult> => runMobileCandidateAction({ action: 'push_unbind', context })
