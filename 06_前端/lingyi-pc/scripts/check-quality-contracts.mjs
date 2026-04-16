import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  FRONTEND_WRITE_GUARD_COMMON_RULES,
  runContractCli,
  runFrontendContractEngine,
  validateModuleContractConfig,
} from './frontend-contract-engine.mjs'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const defaultProjectRoot = path.resolve(__dirname, '..')

const read = (targetPath) => readFileSync(targetPath, 'utf8')

const collectFiles = (dirPath) => {
  if (!existsSync(dirPath)) return []
  const files = []
  const walk = (current) => {
    for (const name of readdirSync(current)) {
      const full = path.join(current, name)
      const st = statSync(full)
      if (st.isDirectory()) {
        walk(full)
      } else if (st.isFile()) {
        files.push(full)
      }
    }
  }
  walk(dirPath)
  return files
}

const qualitySurfaceMatcher = ({ relativePath }) =>
  relativePath === 'src/api/quality.ts' ||
  relativePath.startsWith('src/views/quality/') ||
  relativePath === 'src/router/index.ts' ||
  relativePath === 'src/stores/permission.ts'

export const buildQualityModuleConfig = () => ({
  module: 'quality',
  surface: {
    moduleKey: 'quality',
    scanScopes: ['api', 'views', 'router', 'stores', 'components', 'utils'],
    entryGlobs: ['src/**'],
    extraPaths: ['src/App.vue'],
  },
  fixture: {
    positive: ['scripts/test-quality-contracts.mjs:minimal legal quality fixture'],
    negative: ['scripts/test-quality-contracts.mjs:quality write-entry negative fixtures'],
  },
  allowedApis: [
    'fetchQualityInspections',
    'fetchQualityInspectionDetail',
    'createQualityInspection',
    'updateQualityInspection',
    'confirmQualityInspection',
    'cancelQualityInspection',
    'fetchQualityStatistics',
    'exportQualityInspections',
  ],
  forbiddenApis: ['/api/resource', '/api/quality/internal', '/api/quality/diagnostic', 'run-once'],
  forbiddenActions: [],
  allowedReadOnlyActions: ['read', 'list', 'detail', 'query', 'view', 'export'],
  allowedHttpMethods: ['GET', 'POST', 'PATCH'],
  rules: FRONTEND_WRITE_GUARD_COMMON_RULES.filter((rule) => rule.id !== 'FWG-INT-003'),
  enforceHttpMethodPolicy: true,
  enforceForbiddenActions: false,
  surfaceMatcher: qualitySurfaceMatcher,
})

const requiredApiFunctions = [
  'fetchQualityInspections',
  'fetchQualityInspectionDetail',
  'createQualityInspection',
  'updateQualityInspection',
  'confirmQualityInspection',
  'cancelQualityInspection',
  'fetchQualityStatistics',
  'exportQualityInspections',
]

const requiredRoutes = ['/quality/inspections', '/quality/inspections/detail']

const forbiddenSurfaceRules = [
  { regex: /\/api\/resource/gi, message: '质量前端禁止 ERPNext /api/resource 直连' },
  { regex: /\/api\/quality\/diagnostic/gi, message: '质量普通前端禁止调用 diagnostic 接口' },
  { regex: /factory-statements\/internal|quality\/internal|run-once/gi, message: '质量普通前端禁止 internal/run-once 入口' },
  { regex: /\b(?:Payment Entry|GL Entry|Purchase Invoice|Stock Entry|Purchase Receipt|Delivery Note)\b/gi, message: '质量前端禁止暴露 ERPNext 写入对象' },
  { regex: /\b(?:submitPurchaseInvoice|createPaymentEntry|createGlEntry|createStockEntry|createPurchaseReceipt|createDeliveryNote)\b/gi, message: '质量前端禁止暴露 ERPNext 写入函数' },
]

const scanForbiddenSurface = ({ files, fail }) => {
  for (const targetPath of files) {
    if (!existsSync(targetPath)) continue
    const content = read(targetPath)
    for (const rule of forbiddenSurfaceRules) {
      const clone = new RegExp(rule.regex.source, rule.regex.flags)
      const match = clone.exec(content)
      if (match) {
        fail(`${rule.message}: ${targetPath} -> ${match[0]}`)
      }
    }
  }
}

const checkPermissionBoundActions = ({ listContent, detailContent, fail }) => {
  if (!/v-if="canCreate"[\s\S]*submitCreate/.test(listContent) || !/:disabled="!canCreate"/.test(listContent)) {
    fail('质量创建按钮必须绑定 quality_create 权限并在提交按钮 fail closed')
  }
  for (const item of [
    { name: '更新', guard: 'canUpdate', submit: 'submitUpdate' },
    { name: '确认', guard: 'canConfirm', submit: 'submitConfirm' },
    { name: '取消', guard: 'canCancel', submit: 'submitCancel' },
  ]) {
    const guardRegex = new RegExp(`v-if="${item.guard}"[\\s\\S]*${item.submit}`)
    const disabledRegex = new RegExp(`:disabled="!${item.guard}"`)
    if (!guardRegex.test(detailContent) || !disabledRegex.test(detailContent)) {
      fail(`质量${item.name}按钮必须绑定 ${item.guard} 权限并 fail closed`)
    }
  }
}

export const checkQualityContracts = (projectRootInput = defaultProjectRoot) => {
  const projectRoot = path.resolve(projectRootInput)
  const apiPath = path.join(projectRoot, 'src/api/quality.ts')
  const viewsDir = path.join(projectRoot, 'src/views/quality')
  const routerPath = path.join(projectRoot, 'src/router/index.ts')
  const permissionStorePath = path.join(projectRoot, 'src/stores/permission.ts')
  const appPath = path.join(projectRoot, 'src/App.vue')
  const listViewPath = path.join(viewsDir, 'QualityInspectionList.vue')
  const detailViewPath = path.join(viewsDir, 'QualityInspectionDetail.vue')

  const failures = []
  const fail = (message) => failures.push(message)

  const moduleConfig = buildQualityModuleConfig()
  const configValidation = validateModuleContractConfig(moduleConfig)
  if (!configValidation.ok) {
    for (const message of configValidation.failures) {
      fail(`[FWG-CONFIG-001] ${message}`)
    }
  }

  const requiredFiles = [apiPath, listViewPath, detailViewPath, routerPath, permissionStorePath, appPath]
  for (const requiredFile of requiredFiles) {
    if (!existsSync(requiredFile)) {
      fail(`缺少质量管理契约必需文件: ${requiredFile}`)
    }
  }

  if (configValidation.ok) {
    const engineResult = runFrontendContractEngine(projectRoot, moduleConfig)
    if (!engineResult.ok) {
      for (const message of engineResult.failures) {
        fail(message)
      }
    }
  }

  if (existsSync(apiPath)) {
    const apiContent = read(apiPath)
    for (const functionName of requiredApiFunctions) {
      if (!apiContent.includes(functionName)) {
        fail(`quality API 缺少方法: ${functionName}`)
      }
    }
    for (const endpoint of [
      '/api/quality/inspections',
      '/api/quality/statistics',
      '/api/quality/export',
      '/confirm',
      '/cancel',
    ]) {
      if (!apiContent.includes(endpoint)) {
        fail(`quality API 缺少端点片段: ${endpoint}`)
      }
    }
    if (/fetchQualityDiagnostic|\/api\/quality\/diagnostic/.test(apiContent)) {
      fail('quality API 禁止暴露 diagnostic 方法或端点')
    }
    if (/method\s*:\s*['"](?:PUT|DELETE)['"]/.test(apiContent)) {
      fail('quality API 禁止声明 PUT/DELETE')
    }
    if (/\bfetch\s*\(/.test(apiContent) || /\baxios\b/.test(apiContent)) {
      fail('quality API 必须走统一 request()，禁止裸 fetch/axios')
    }
  }

  const qualityViewFiles = existsSync(viewsDir) ? collectFiles(viewsDir) : []
  scanForbiddenSurface({ files: [apiPath, ...qualityViewFiles, routerPath], fail })

  if (existsSync(listViewPath) && existsSync(detailViewPath)) {
    checkPermissionBoundActions({ listContent: read(listViewPath), detailContent: read(detailViewPath), fail })
  }

  if (existsSync(routerPath)) {
    const routerContent = read(routerPath)
    for (const routePath of requiredRoutes) {
      if (!routerContent.includes(routePath)) {
        fail(`路由缺少质量管理路径: ${routePath}`)
      }
    }
    if (!routerContent.includes("meta: { module: 'quality' }")) {
      fail('质量管理路由缺少 meta.module=quality')
    }
    const forbiddenRouteMatch = /\/quality\/[A-Za-z0-9/_-]*(?:diagnostic|internal|run-once|worker)/i.exec(routerContent)
    if (forbiddenRouteMatch) {
      fail(`质量管理路由禁止暴露诊断或内部路径: ${forbiddenRouteMatch[0]}`)
    }
  }

  if (existsSync(permissionStorePath)) {
    const permissionContent = read(permissionStorePath)
    for (const requiredKey of [
      'quality_read: false',
      'quality_create: false',
      'quality_update: false',
      'quality_confirm: false',
      'quality_cancel: false',
      'quality_export: false',
      'quality_diagnostic: false',
    ]) {
      if (!permissionContent.includes(requiredKey)) {
        fail(`permission store 缺少质量管理权限默认值: ${requiredKey}`)
      }
    }
    if (!permissionContent.includes('quality:diagnostic')) {
      fail('permission store 缺少质量 diagnostic denylist: quality:diagnostic')
    }
    if (!/forceClearInternalButtonPermissions[\s\S]*quality_diagnostic\s*:\s*false/.test(permissionContent)) {
      fail('permission store 必须强制清零 quality_diagnostic')
    }
  }

  return {
    ok: failures.length === 0,
    failures,
    scannedFiles: requiredFiles.length + qualityViewFiles.length,
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(__filename)) {
  runContractCli({
    check: checkQualityContracts,
    passMessage: 'Quality frontend contracts passed.',
    failTitle: 'Quality frontend contracts failed:',
  })
}
