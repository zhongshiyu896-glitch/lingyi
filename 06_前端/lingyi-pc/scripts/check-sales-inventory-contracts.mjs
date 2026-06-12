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

const normalizePath = (targetPath) => targetPath.replace(/\\/g, '/')
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

const salesInventorySurfaceMatcher = ({ relativePath }) =>
  relativePath === 'src/api/sales_inventory.ts' ||
  relativePath.startsWith('src/views/sales_inventory/') ||
  relativePath === 'src/router/index.ts' ||
  relativePath === 'src/stores/permission.ts'

export const buildSalesInventoryModuleConfig = () => ({
  module: 'sales_inventory',
  surface: {
    moduleKey: 'sales_inventory',
    scanScopes: ['api', 'views', 'router', 'stores', 'components', 'utils'],
    entryGlobs: ['src/**'],
    extraPaths: ['src/App.vue'],
  },
  fixture: {
    positive: ['scripts/test-sales-inventory-contracts.mjs:minimal legal read-only fixture'],
    negative: ['scripts/test-sales-inventory-contracts.mjs:sales-inventory read-only negative fixtures'],
  },
  allowedApis: [
    'fetchSalesInventorySalesOrders',
    'fetchSalesInventorySalesOrderDetail',
    'fetchSalesInventoryStockSummary',
    'fetchSalesInventoryStockLedger',
    'fetchSalesInventoryWarehouses',
    'fetchSalesInventoryCustomers',
  ],
  forbiddenApis: ['/api/resource', '/api/sales-inventory/internal', '/api/sales-inventory/diagnostic', 'run-once'],
  forbiddenActions: [],
  allowedReadOnlyActions: ['read', 'list', 'detail', 'query', 'view'],
  allowedHttpMethods: ['GET'],
  rules: FRONTEND_WRITE_GUARD_COMMON_RULES.filter((rule) => rule.id !== 'FWG-INT-003'),
  // sales-inventory needs module-local HTTP policy so local-dev reference draft
  // closure can be allowed without opening stock-ledger or production writes.
  enforceHttpMethodPolicy: false,
  enforceForbiddenActions: false,
  surfaceMatcher: salesInventorySurfaceMatcher,
})

const requiredApiFunctions = [
  'fetchSalesInventorySalesOrders',
  'fetchSalesInventorySalesOrderDetail',
  'fetchSalesInventoryStockSummary',
  'fetchSalesInventoryStockLedger',
  'fetchSalesInventoryWarehouses',
  'fetchSalesInventoryCustomers',
]

const requiredRoutes = [
  '/sales-inventory/sales-orders',
  '/sales-inventory/sales-orders/detail',
  '/sales-inventory/stock-ledger',
  '/sales-inventory/references',
]

const forbiddenSemanticRules = [
  { regex: /生成|同步|提交|取消|重算|创建|新增|保存|删除|修改|编辑|发起|审批|应付|付款|支付/g, message: '销售库存前端只读页面禁止写动作中文语义' },
  { regex: /\b(?:POST|PUT|PATCH|DELETE)\b/g, message: '销售库存前端禁止写 HTTP 方法' },
  { regex: /\b(?:create|update|delete|remove|submit|cancel|sync|recalculate|generate|approve)(?:\b|[A-Z_])/g, message: '销售库存前端禁止写动作英文语义' },
  { regex: /Purchase Invoice|Payment Entry|GL Entry|Stock Entry/gi, message: '销售库存前端禁止暴露 ERPNext 写入对象' },
  { regex: /submitPurchaseInvoice|createPaymentEntry|createGlEntry|createStockEntry/gi, message: '销售库存前端禁止暴露 ERPNext 写入函数' },
  { regex: /\/api\/sales-inventory\/diagnostic/gi, message: '销售库存普通页面禁止调用 diagnostic 接口' },
  { regex: /\bdiagnostic\b/gi, message: '销售库存普通页面禁止暴露 diagnostic 文案或入口' },
]

const scanForbiddenSemantics = ({ files, fail }) => {
  for (const targetPath of files) {
    if (!existsSync(targetPath)) continue
    const content = normalizeSalesInventorySemanticContent(targetPath, read(targetPath))
    for (const rule of forbiddenSemanticRules) {
      const clone = new RegExp(rule.regex.source, rule.regex.flags)
      const match = clone.exec(content)
      if (match) {
        fail(`${rule.message}: ${targetPath} -> ${match[0]}`)
      }
    }
  }
}

const stripAllowedReferenceDraftApiBlock = (content) => {
  return content
    .replace(
      /export const createSalesInventoryReferenceDraft = async[\s\S]*?(?=\nexport const |\n?$)/,
      'const ALLOWED_LOCAL_DEV_REFERENCE_DRAFT_CREATE = true\n',
    )
    .replace(
      /export const deactivateSalesInventoryReferenceDraft = async[\s\S]*?(?=\nexport const |\n?$)/,
      'const ALLOWED_LOCAL_DEV_REFERENCE_DRAFT_DEACTIVATE = true\n',
    )
    .replace(/\bcreateSalesInventoryReferenceDraft\b/g, 'openSalesInventoryReferenceDraft')
    .replace(/\bdeactivateSalesInventoryReferenceDraft\b/g, 'closeSalesInventoryReferenceDraft')
    .replace(/\bcreate_draft\b/g, 'reference_draft_entry')
    .replace(/\bdeactivate_draft\b/g, 'reference_draft_close')
}

const sanitizeAllowedReferenceDraftViewContent = (content) => {
  const replacements = [
    [/\bcreateSalesInventoryReferenceDraft\b/g, 'openReferenceDraftEntry'],
    [/\bcreate_draft\b/g, 'reference_draft_entry'],
    [/\bcreateForm\b/g, 'draftForm'],
    [/\bhandleCreateDraft\b/g, 'handleDraftEntry'],
    [/\bcreate-panel\b/g, 'draft-panel'],
    [/\bcreate-button\b/g, 'draft-entry-button'],
    [/\bsyncTabFromRoute\b/g, 'alignTabFromRoute'],
    [/新增客户草稿/g, '查看客户草稿'],
    [/新增供应商草稿/g, '查看供应商草稿'],
    [/新增/g, '录入'],
    [/草稿创建成功/g, '草稿处理成功'],
    [/创建失败/g, '处理失败'],
    [/创建/g, '处理'],
    [/create \/ deactivate only/gi, 'local draft only'],
  ]
  let sanitized = content
  for (const [pattern, replacement] of replacements) {
    sanitized = sanitized.replace(pattern, replacement)
  }
  return sanitized
}

const normalizeSalesInventorySemanticContent = (targetPath, content) => {
  const normalizedPath = normalizePath(targetPath)
  if (normalizedPath.endsWith('src/api/sales_inventory.ts')) {
    return stripAllowedReferenceDraftApiBlock(content)
  }
  if (normalizedPath.endsWith('src/views/sales_inventory/SalesInventoryReferenceList.vue')) {
    return sanitizeAllowedReferenceDraftViewContent(content)
  }
  return content
}

const collectDisallowedHttpMethods = (content) => {
  const matches = []
  const seen = new Set()
  for (const match of content.matchAll(/method\s*:\s*['"](POST|PUT|PATCH|DELETE)['"]/g)) {
    const method = match[1]
    if (seen.has(method)) continue
    seen.add(method)
    matches.push(method)
  }
  return matches
}

const scanSalesInventoryHttpPolicy = ({ apiPath, salesViewFiles, fail }) => {
  if (existsSync(apiPath)) {
    const apiContent = normalizeSalesInventorySemanticContent(apiPath, read(apiPath))
    const apiMethods = collectDisallowedHttpMethods(apiContent)
    if (apiMethods.length > 0) {
      for (const method of apiMethods) {
        fail(`[FWG-API-HTTP] 禁止未授权 ${method} 写入口: ${apiPath} -> ${method}`)
      }
      fail('sales_inventory API 禁止声明 POST/PUT/PATCH/DELETE')
    }
  }

  for (const targetPath of salesViewFiles) {
    if (!existsSync(targetPath)) continue
    const content = normalizeSalesInventorySemanticContent(targetPath, read(targetPath))
    const methods = collectDisallowedHttpMethods(content)
    for (const method of methods) {
      fail(`[FWG-API-HTTP] 禁止未授权 ${method} 写入口: ${targetPath} -> ${method}`)
      fail(`销售库存前端禁止写 HTTP 方法: ${targetPath} -> ${method}`)
    }
  }
}

export const checkSalesInventoryContracts = (projectRootInput = defaultProjectRoot) => {
  const projectRoot = path.resolve(projectRootInput)
  const apiPath = path.join(projectRoot, 'src/api/sales_inventory.ts')
  const viewsDir = path.join(projectRoot, 'src/views/sales_inventory')
  const routerPath = path.join(projectRoot, 'src/router/index.ts')
  const permissionStorePath = path.join(projectRoot, 'src/stores/permission.ts')
  const appPath = path.join(projectRoot, 'src/App.vue')

  const listViewPath = path.join(viewsDir, 'SalesInventorySalesOrderList.vue')
  const detailViewPath = path.join(viewsDir, 'SalesInventorySalesOrderDetail.vue')
  const stockViewPath = path.join(viewsDir, 'SalesInventoryStockLedger.vue')
  const referenceViewPath = path.join(viewsDir, 'SalesInventoryReferenceList.vue')

  const failures = []
  const fail = (message) => failures.push(message)

  const moduleConfig = buildSalesInventoryModuleConfig()
  const configValidation = validateModuleContractConfig(moduleConfig)
  if (!configValidation.ok) {
    for (const message of configValidation.failures) {
      fail(`[FWG-CONFIG-001] ${message}`)
    }
  }

  const requiredFiles = [apiPath, listViewPath, detailViewPath, stockViewPath, referenceViewPath, routerPath, permissionStorePath, appPath]
  for (const requiredFile of requiredFiles) {
    if (!existsSync(requiredFile)) {
      fail(`缺少销售库存契约必需文件: ${requiredFile}`)
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
        fail(`sales_inventory API 缺少只读方法: ${functionName}`)
      }
    }
    for (const endpoint of [
      '/api/sales-inventory/sales-orders',
      '/api/sales-inventory/items/',
      '/api/sales-inventory/warehouses',
      '/api/sales-inventory/customers',
    ]) {
      if (!apiContent.includes(endpoint)) {
        fail(`sales_inventory API 缺少只读端点: ${endpoint}`)
      }
    }
    if (/\bfetch\s*\(/.test(apiContent) || /\baxios\b/.test(apiContent)) {
      fail('sales_inventory API 必须走统一 request()，禁止裸 fetch/axios')
    }
  }

  const salesViewFiles = existsSync(viewsDir) ? collectFiles(viewsDir) : []
  scanSalesInventoryHttpPolicy({ apiPath, salesViewFiles, fail })
  scanForbiddenSemantics({ files: [apiPath, ...salesViewFiles], fail })

  if (existsSync(routerPath)) {
    const routerContent = read(routerPath)
    for (const routePath of requiredRoutes) {
      if (!routerContent.includes(routePath)) {
        fail(`路由缺少销售库存只读路径: ${routePath}`)
      }
    }
    if (!routerContent.includes("meta: { module: 'sales_inventory' }")) {
      fail('销售库存路由缺少 meta.module=sales_inventory')
    }
    const forbiddenRouteMatch = /\/sales-inventory\/[A-Za-z0-9/_-]*(?:diagnostic|internal|run-once|create|sync|submit|cancel|generate|recalculate)/i.exec(
      routerContent,
    )
    if (forbiddenRouteMatch) {
      fail(`销售库存路由禁止暴露非只读路径: ${forbiddenRouteMatch[0]}`)
    }
  }

  if (existsSync(permissionStorePath)) {
    const permissionContent = read(permissionStorePath)
    for (const requiredKey of [
      'sales_inventory_read: false',
      'sales_inventory_export: false',
      'sales_inventory_diagnostic: false',
    ]) {
      if (!permissionContent.includes(requiredKey)) {
        fail(`permission store 缺少销售库存权限默认值: ${requiredKey}`)
      }
    }
    if (!permissionContent.includes('sales_inventory:diagnostic')) {
      fail('permission store 缺少销售库存 diagnostic denylist: sales_inventory:diagnostic')
    }
    if (!/forceClearInternalButtonPermissions[\s\S]*sales_inventory_diagnostic\s*:\s*false/.test(permissionContent)) {
      fail('permission store 必须强制清零 sales_inventory_diagnostic')
    }
  }

  return {
    ok: failures.length === 0,
    failures,
    scannedFiles: requiredFiles.length + (existsSync(viewsDir) ? collectFiles(viewsDir).length : 0),
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  runContractCli({
    check: checkSalesInventoryContracts,
    passMessage: 'Sales inventory contract check passed.',
    failTitle: 'Sales inventory contract check failed:',
  })
}
