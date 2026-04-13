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

export const checkProductionContracts = (projectRootInput = defaultProjectRoot) => {
  const projectRoot = path.resolve(projectRootInput)
  const apiProductionPath = path.join(projectRoot, 'src/api/production.ts')
  const productionViewsDir = path.join(projectRoot, 'src/views/production')
  const routerDir = path.join(projectRoot, 'src/router')
  const storesDir = path.join(projectRoot, 'src/stores')
  const permissionStorePath = path.join(projectRoot, 'src/stores/permission.ts')
  const detailViewPath = path.join(projectRoot, 'src/views/production/ProductionPlanDetail.vue')

  const failures = []
  const fail = (message) => failures.push(message)

  const requiredFiles = [apiProductionPath, permissionStorePath, detailViewPath]
  for (const requiredFile of requiredFiles) {
    if (!existsSync(requiredFile)) {
      fail(`缺少契约必需文件: ${requiredFile}`)
    }
  }
  for (const requiredDir of [productionViewsDir, routerDir, storesDir]) {
    if (!existsSync(requiredDir)) {
      fail(`缺少契约扫描目录: ${requiredDir}`)
    }
  }

  const INTERNAL_ACTION_WHITELIST = {
    paths: new Set([normalizePath(permissionStorePath)]),
    allowedTokens: [
      'production:work_order_worker',
      'subcontract:stock_sync_worker',
      'workshop:job_card_sync_worker',
    ],
    reason: '仅允许在 permission denylist/常量中声明内部动作，避免进入 UI。',
  }

  const scanFiles = [
    apiProductionPath,
    ...collectFiles(productionViewsDir),
    ...collectFiles(routerDir),
    ...collectFiles(storesDir),
  ]
  const uniqueScanFiles = [...new Set(scanFiles.map((targetPath) => normalizePath(targetPath)))].sort()
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
      regex: /\/api\/production\/internal/gi,
      message: '禁止调用生产计划内部 worker API',
    },
    {
      regex: /work-order-sync\/run-once/gi,
      message: '禁止出现 work-order-sync/run-once 调用路径',
    },
    {
      regex: /\/api\/resource/gi,
      message: '禁止 ERPNext /api/resource 直连',
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
    ({ targetPath }) => isTargetPath(targetPath, productionViewsDir) || isTargetPath(targetPath, routerDir),
  )
  for (const { targetPath, content } of uiFiles) {
    if (/production:work_order_worker/.test(content)) {
      fail(`禁止在 UI 视图/路由中出现 production:work_order_worker: ${targetPath}`)
    }
  }

  const storeFiles = fileContents.filter(({ targetPath }) => isTargetPath(targetPath, storesDir))
  for (const { targetPath, content } of storeFiles) {
    if (/production:work_order_worker/.test(content)) {
      const normalized = normalizePath(targetPath)
      if (!INTERNAL_ACTION_WHITELIST.paths.has(normalized)) {
        fail(`仅允许在白名单文件声明内部动作 production:work_order_worker: ${targetPath}`)
      }
    }
  }

  if (existsSync(permissionStorePath)) {
    const permissionStoreContent = read(permissionStorePath)
    for (const token of INTERNAL_ACTION_WHITELIST.allowedTokens) {
      if (!permissionStoreContent.includes(token)) {
        fail(`permission store 缺少内部动作 denylist 常量: ${token}`)
      }
    }
    if (!permissionStoreContent.includes('forceClearInternalButtonPermissions')) {
      fail('permission store 缺少内部按钮权限强制清零函数')
    }
    for (const internalKey of ['work_order_worker: false', 'stock_sync_worker: false', 'job_card_sync_worker: false']) {
      if (!permissionStoreContent.includes(internalKey)) {
        fail(`permission store 缺少内部按钮清零: ${internalKey}`)
      }
    }
  }

  if (existsSync(apiProductionPath)) {
    const apiProductionContent = read(apiProductionPath)
    if (!apiProductionContent.includes('planned_start_date')) {
      fail('src/api/production.ts 缺少 planned_start_date 契约字段')
    }
    for (const requiredField of ['fg_warehouse', 'wip_warehouse', 'start_date', 'idempotency_key']) {
      if (!apiProductionContent.includes(requiredField)) {
        fail(`src/api/production.ts 缺少 Work Order 字段: ${requiredField}`)
      }
    }

    const createPayloadBlockMatch = apiProductionContent.match(
      /export\s+interface\s+ProductionPlanCreatePayload\s*\{[\s\S]*?\n\}/,
    )
    if (!createPayloadBlockMatch) {
      fail('未找到 ProductionPlanCreatePayload 接口定义')
    } else if (/\bcompany\s*\??\s*:/.test(createPayloadBlockMatch[0])) {
      fail('ProductionPlanCreatePayload 不得包含 company 字段')
    }
  }

  if (existsSync(detailViewPath)) {
    const detailViewContent = read(detailViewPath)
    if (/latestJobCardSyncedAt/.test(detailViewContent)) {
      fail('详情页仍存在 latestJobCardSyncedAt 逻辑，疑似用 Job Card 冒充 Work Order 最近同步时间')
    }
    if (!/label="最近同步时间">\{\{\s*detail\?\.last_synced_at\s*\|\|\s*'-'\s*\}\}/.test(detailViewContent)) {
      fail('详情页最近同步时间必须展示 detail.last_synced_at')
    }
    if (/label="最近同步时间">\{\{\s*latestJobCardSyncedAt/.test(detailViewContent)) {
      fail('详情页最近同步时间仍使用 latestJobCardSyncedAt，违反契约')
    }
  }

  return {
    ok: failures.length === 0,
    failures,
    whitelistReason: INTERNAL_ACTION_WHITELIST.reason,
    scannedFiles: uniqueScanFiles.length,
  }
}

const runCli = () => {
  const { projectRoot } = parseCliArgs(process.argv.slice(2))
  const result = checkProductionContracts(projectRoot)
  if (!result.ok) {
    console.error('Production contract check failed:')
    for (const [idx, message] of result.failures.entries()) {
      console.error(`${idx + 1}. ${message}`)
    }
    console.error(`Whitelist: ${result.whitelistReason}`)
    process.exit(1)
  }
  console.log('Production contract check passed.')
  console.log(`Scanned files: ${result.scannedFiles}`)
  console.log(`Whitelist: ${result.whitelistReason}`)
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  runCli()
}
