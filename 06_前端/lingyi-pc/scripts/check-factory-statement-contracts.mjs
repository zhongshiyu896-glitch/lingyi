import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const defaultProjectRoot = path.resolve(__dirname, '..')

const normalizePath = (targetPath) => targetPath.replace(/\\/g, '/')
const isTargetPath = (targetPath, rootDir) => normalizePath(targetPath).startsWith(normalizePath(rootDir) + '/')

const read = (targetPath) => readFileSync(targetPath, 'utf8')

const collectFiles = (dirPath) => {
  if (!existsSync(dirPath)) {
    return []
  }
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

const parseCliArgs = (argv) => {
  let projectRoot = defaultProjectRoot
  for (let idx = 0; idx < argv.length; idx += 1) {
    if (argv[idx] === '--project-root') {
      const next = argv[idx + 1]
      if (!next) {
        throw new Error('参数错误：--project-root 需要路径值')
      }
      projectRoot = path.resolve(next)
      idx += 1
    }
  }
  return { projectRoot }
}

export const checkFactoryStatementContracts = (projectRootInput = defaultProjectRoot) => {
  const projectRoot = path.resolve(projectRootInput)

  const apiPath = path.join(projectRoot, 'src/api/factory_statement.ts')
  const listViewPath = path.join(projectRoot, 'src/views/factory_statement/FactoryStatementList.vue')
  const detailViewPath = path.join(projectRoot, 'src/views/factory_statement/FactoryStatementDetail.vue')
  const printViewPath = path.join(projectRoot, 'src/views/factory_statement/FactoryStatementPrint.vue')
  const exportUtilPath = path.join(projectRoot, 'src/utils/factoryStatementExport.ts')
  const factoryStatementViewsDir = path.join(projectRoot, 'src/views/factory_statement')
  const routerDir = path.join(projectRoot, 'src/router')
  const storesDir = path.join(projectRoot, 'src/stores')
  const appPath = path.join(projectRoot, 'src/App.vue')
  const componentsDir = path.join(projectRoot, 'src/components')
  const utilsDir = path.join(projectRoot, 'src/utils')
  const permissionStorePath = path.join(projectRoot, 'src/stores/permission.ts')

  const failures = []
  const fail = (message) => failures.push(message)

  const requiredFiles = [apiPath, listViewPath, detailViewPath, printViewPath, exportUtilPath, permissionStorePath, appPath]
  for (const requiredFile of requiredFiles) {
    if (!existsSync(requiredFile)) {
      fail(`缺少契约必需文件: ${requiredFile}`)
    }
  }

  const scanRoots = [apiPath, factoryStatementViewsDir, routerDir, storesDir, utilsDir, appPath, componentsDir]
  const scanFiles = []
  for (const root of scanRoots) {
    if (!existsSync(root)) {
      continue
    }
    const st = statSync(root)
    if (st.isDirectory()) {
      scanFiles.push(...collectFiles(root))
    } else if (st.isFile()) {
      scanFiles.push(root)
    }
  }

  const uniqueScanFiles = [...new Set(scanFiles.map((item) => normalizePath(item)))].sort()
  const fileContents = uniqueScanFiles
    .filter((targetPath) => existsSync(targetPath))
    .map((targetPath) => ({
      targetPath,
      content: read(targetPath),
    }))

  const forbiddenRules = [
    {
      regex: /\bfetch\s*\(/g,
      message: '禁止裸 fetch()，必须走统一 request() 封装',
    },
    {
      regex: /\/api\/resource/gi,
      message: '禁止 ERPNext /api/resource 直连',
    },
    {
      regex: /\/api\/factory-statements\/internal/gi,
      message: '禁止前端调用加工厂对账单 internal 接口',
    },
    {
      regex: /payable-draft-sync\/run-once/gi,
      message: '禁止出现 payable-draft-sync/run-once 调用路径',
    },
    {
      regex: /\brun-once\b/gi,
      message: '禁止在前端页面或路由暴露 run-once 动作',
    },
    {
      regex: /\bsubmitPurchaseInvoice\b/g,
      message: '禁止出现 submitPurchaseInvoice 调用',
    },
    {
      regex: /\bcreatePaymentEntry\b/g,
      message: '禁止出现 createPaymentEntry 调用',
    },
    {
      regex: /\bcreateGlEntry\b/g,
      message: '禁止出现 createGlEntry 调用',
    },
    {
      regex: /Payment Entry/gi,
      message: '禁止出现 Payment Entry 创建入口',
    },
    {
      regex: /GL Entry/gi,
      message: '禁止出现 GL Entry 创建入口',
    },
    {
      regex: /\b(Authorization|Cookie|token|secret|password)\b/gi,
      message: '禁止业务文件出现敏感关键字硬编码',
    },
  ]

  for (const { targetPath, content } of fileContents) {
    for (const rule of forbiddenRules) {
      if (rule.regex.test(content)) {
        fail(`${rule.message}: ${targetPath}`)
      }
      rule.regex.lastIndex = 0
    }
  }

  const uiFiles = fileContents.filter(
    ({ targetPath }) => isTargetPath(targetPath, factoryStatementViewsDir) || isTargetPath(targetPath, routerDir),
  )
  for (const { targetPath, content } of uiFiles) {
    if (/factory_statement:payable_draft_worker/.test(content)) {
      fail(`禁止在 UI 视图/路由中出现 factory_statement:payable_draft_worker: ${targetPath}`)
    }
  }

  const storeFiles = fileContents.filter(({ targetPath }) => isTargetPath(targetPath, storesDir))
  for (const { targetPath, content } of storeFiles) {
    if (
      /factory_statement:payable_draft_worker/.test(content) &&
      normalizePath(targetPath) !== normalizePath(permissionStorePath)
    ) {
      fail(`仅允许在 permission store 声明内部动作 factory_statement:payable_draft_worker: ${targetPath}`)
    }
  }

  if (existsSync(apiPath)) {
    const apiContent = read(apiPath)

    if (!/import\s*\{\s*request\s*,\s*type\s+ApiResponse\s*\}\s*from\s*['"]@\/api\/request['"]/.test(apiContent)) {
      fail('src/api/factory_statement.ts 必须统一导入 request 与 ApiResponse')
    }

    for (const requiredFn of [
      'fetchFactoryStatements',
      'fetchFactoryStatementDetail',
      'createFactoryStatement',
      'confirmFactoryStatement',
      'cancelFactoryStatement',
      'createFactoryStatementPayableDraft',
    ]) {
      if (!apiContent.includes(`export const ${requiredFn}`)) {
        fail(`src/api/factory_statement.ts 缺少 API 方法: ${requiredFn}`)
      }
    }

    for (const forbiddenFn of [
      'runFactoryStatementPayableWorker',
      'payableDraftSyncRunOnce',
      'submitPurchaseInvoice',
      'createPaymentEntry',
      'createGlEntry',
    ]) {
      if (apiContent.includes(forbiddenFn)) {
        fail(`src/api/factory_statement.ts 禁止封装方法: ${forbiddenFn}`)
      }
    }

    const createPayloadMatch = apiContent.match(/export\s+interface\s+FactoryStatementCreatePayload\s*\{[\s\S]*?\n\}/)
    if (!createPayloadMatch) {
      fail('src/api/factory_statement.ts 缺少 FactoryStatementCreatePayload 定义')
    } else {
      const block = createPayloadMatch[0]
      if (!/\bcompany\s*:\s*string\b/.test(block)) {
        fail('FactoryStatementCreatePayload.company 必须为必填 string')
      }
      if (/\bcompany\s*\?:/.test(block)) {
        fail('FactoryStatementCreatePayload 禁止 company? 可选字段')
      }
    }

    for (const requiredTypeField of [
      'payable_outbox_status: string | null',
      'purchase_invoice_name: string | null',
      'payable_outbox_id: number | null',
      'payable_error_code: string | null',
      'payable_error_message: string | null',
    ]) {
      if (!apiContent.includes(requiredTypeField)) {
        fail(`src/api/factory_statement.ts 缺少 payable 摘要字段契约: ${requiredTypeField}`)
      }
    }
  }

  if (existsSync(listViewPath)) {
    const listViewContent = read(listViewPath)
    if (!listViewContent.includes('label="公司"')) {
      fail('FactoryStatementList.vue 创建表单缺少 company 字段')
    }
    if (!listViewContent.includes('createForm.company')) {
      fail('FactoryStatementList.vue 缺少 createForm.company 绑定')
    }
    if (!/company:\s*createForm\.company\.trim\(\)/.test(listViewContent)) {
      fail('FactoryStatementList.vue submitCreate 必须提交 company')
    }
  }

  if (existsSync(detailViewPath)) {
    const detailViewContent = read(detailViewPath)
    for (const requiredFragment of [
      'const hasPayableSummary',
      'const summaryMissing',
      'summaryMissing',
      'hasPayableSummary.value',
      "return '__unknown__'",
      '!hasPayableSummary.value || ACTIVE_PAYABLE_OUTBOX_STATUS.has',
      '导出明细 CSV',
      'exportFactoryStatementDetailCsv',
      '/factory-statements/print',
    ]) {
      if (!detailViewContent.includes(requiredFragment)) {
        fail(`FactoryStatementDetail.vue 缺少 fail-closed 片段: ${requiredFragment}`)
      }
    }
  }

  if (existsSync(printViewPath)) {
    const printViewContent = read(printViewPath)

    if (!printViewContent.includes('fetchFactoryStatementDetail')) {
      fail('FactoryStatementPrint.vue 必须调用 fetchFactoryStatementDetail 或同等业务 API 封装')
    }
    if (!/window\.print\s*\(/.test(printViewContent)) {
      fail('FactoryStatementPrint.vue 缺少用户触发打印入口 window.print()')
    }
    if (/onMounted\s*\([\s\S]*window\.print\s*\(/.test(printViewContent)) {
      fail('FactoryStatementPrint.vue 禁止 onMounted 自动触发 window.print()')
    }
    if (!printViewContent.includes('领意服装管理系统')) {
      fail('FactoryStatementPrint.vue 缺少系统名称展示：领意服装管理系统')
    }
  }

  if (existsSync(exportUtilPath)) {
    const exportUtilContent = read(exportUtilPath)
    if (!exportUtilContent.includes('exportFactoryStatementDetailCsv')) {
      fail('factoryStatementExport.ts 缺少 exportFactoryStatementDetailCsv 导出方法')
    }
    if (/\baxios\b/.test(exportUtilContent)) {
      fail('导出工具禁止使用 axios，应仅处理已加载详情快照')
    }
    if (/\bfetch\s*\(/.test(exportUtilContent)) {
      fail('导出工具禁止 fetch()，应仅处理已加载详情快照')
    }
    if (/parseFloat\s*\(/.test(exportUtilContent) || /Number\s*\(/.test(exportUtilContent)) {
      fail('导出工具禁止 Number/parseFloat 对金额字段重算')
    }
    if (!exportUtilContent.includes('FORMULA_INJECTION_PREFIX')) {
      fail('CSV 公式注入防护缺少 FORMULA_INJECTION_PREFIX')
    }
    if (!exportUtilContent.includes('neutralizeCsvFormula')) {
      fail('CSV 公式注入防护缺少 neutralizeCsvFormula')
    }
    if (!/FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*=/.test(exportUtilContent)) {
      fail('CSV 公式注入前缀缺少 = 覆盖')
    }
    if (!/FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\+/.test(exportUtilContent)) {
      fail('CSV 公式注入前缀缺少 + 覆盖')
    }
    if (!/FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\-/.test(exportUtilContent)) {
      fail('CSV 公式注入前缀缺少 - 覆盖')
    }
    if (!/FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*@/.test(exportUtilContent)) {
      fail('CSV 公式注入前缀缺少 @ 覆盖')
    }
    if (!/FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\t/.test(exportUtilContent)) {
      fail('CSV 公式注入前缀缺少 tab 覆盖')
    }
    if (!/FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\r/.test(exportUtilContent)) {
      fail('CSV 公式注入前缀缺少 CR 覆盖')
    }
    if (!/FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\n/.test(exportUtilContent)) {
      fail('CSV 公式注入前缀缺少 LF 覆盖')
    }
    if (!/neutralizeCsvFormula\s*\(\s*toText\(value\)\s*\)/.test(exportUtilContent)) {
      fail('escapeCsvCell 必须调用 neutralizeCsvFormula(toText(value))')
    }
  }

  if (existsSync(permissionStorePath)) {
    const permissionStoreContent = read(permissionStorePath)
    for (const requiredKey of [
      'factory_statement_read: false',
      'factory_statement_create: false',
      'factory_statement_confirm: false',
      'factory_statement_cancel: false',
      'factory_statement_payable_draft_create: false',
      'factory_statement_payable_draft_worker: false',
    ]) {
      if (!permissionStoreContent.includes(requiredKey)) {
        fail(`permission store 缺少权限字段默认值: ${requiredKey}`)
      }
    }

    if (!permissionStoreContent.includes('factory_statement:payable_draft_worker')) {
      fail('permission store 缺少 internal worker denylist: factory_statement:payable_draft_worker')
    }

    if (!permissionStoreContent.includes('forceClearInternalButtonPermissions')) {
      fail('permission store 缺少内部按钮权限强制清零函数')
    }
  }

  if (existsSync(routerDir)) {
    const routerFiles = collectFiles(routerDir)
    const routerContent = routerFiles.map((file) => read(file)).join('\n')
    if (!routerContent.includes('/factory-statements/list')) {
      fail('路由缺少 /factory-statements/list')
    }
    if (!routerContent.includes('/factory-statements/detail')) {
      fail('路由缺少 /factory-statements/detail')
    }
    if (!routerContent.includes('/factory-statements/print')) {
      fail('路由缺少 /factory-statements/print')
    }
  }

  return {
    ok: failures.length === 0,
    failures,
    scannedFiles: uniqueScanFiles.length,
  }
}

const runCli = () => {
  const { projectRoot } = parseCliArgs(process.argv.slice(2))
  const result = checkFactoryStatementContracts(projectRoot)
  if (!result.ok) {
    console.error('Factory statement contract check failed:')
    for (const [idx, message] of result.failures.entries()) {
      console.error(`${idx + 1}. ${message}`)
    }
    process.exit(1)
  }
  console.log('Factory statement contract check passed.')
  console.log(`Scanned files: ${result.scannedFiles}`)
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  runCli()
}
