export const LIVE_MODULES = ['bom'] as const

const LIVE_MODULE_SET: ReadonlySet<string> = new Set(LIVE_MODULES)

export const isLiveModule = (module: string | null | undefined): boolean => {
  if (!module) return false
  return LIVE_MODULE_SET.has(module)
}
