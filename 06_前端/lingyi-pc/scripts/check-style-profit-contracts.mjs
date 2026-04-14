import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

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

const isStyleProfitSurface = (targetPath, content, projectRoot) => {
  const normalized = normalizePath(path.relative(projectRoot, targetPath))
  if (normalized.includes('/style_profit/')) return true
  if (normalized.endsWith('/api/style_profit.ts')) return true
  if (normalized === 'src/App.vue') return true
  if (normalized === 'src/main.ts') return true
  if (normalized.startsWith('src/components/')) return true
  if (/(style-profit|style_profit)/i.test(content)) return true
  return false
}

export const checkStyleProfitContracts = (projectRootInput = defaultProjectRoot) => {
  const projectRoot = path.resolve(projectRootInput)
  const srcRoot = path.join(projectRoot, 'src')
  const apiRoot = path.join(srcRoot, 'api')
  const viewsRoot = path.join(srcRoot, 'views')
  const routerRoot = path.join(srcRoot, 'router')
  const storesRoot = path.join(srcRoot, 'stores')
  const componentsRoot = path.join(srcRoot, 'components')

  const requiredFiles = [
    path.join(projectRoot, 'src/api/style_profit.ts'),
    path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotList.vue'),
    path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotDetail.vue'),
    path.join(projectRoot, 'src/router/index.ts'),
    path.join(projectRoot, 'src/stores/permission.ts'),
  ]

  const failures = []
  const fail = (message) => failures.push(message)

  if (!existsSync(srcRoot)) {
    fail(`缺少目录: ${srcRoot}`)
    return { ok: false, failures, scannedFiles: 0 }
  }

  for (const targetFile of requiredFiles) {
    if (!existsSync(targetFile)) {
      fail(`缺少契约必需文件: ${targetFile}`)
    }
  }
  if (failures.length > 0) {
    return { ok: false, failures, scannedFiles: 0 }
  }

  const targetFiles = [
    ...collectFiles(apiRoot),
    ...collectFiles(viewsRoot),
    ...collectFiles(routerRoot),
    ...collectFiles(storesRoot),
    ...collectFiles(componentsRoot),
    path.join(srcRoot, 'App.vue'),
    path.join(srcRoot, 'main.ts'),
  ]
    .filter((targetPath, idx, arr) => existsSync(targetPath) && arr.indexOf(targetPath) === idx)
    .sort()

  const requestFile = path.join(projectRoot, 'src/api/request.ts')
  const authFile = path.join(projectRoot, 'src/api/auth.ts')
  const fetchWhitelist = new Set([normalizePath(requestFile), normalizePath(authFile)])

  for (const targetPath of targetFiles) {
    const content = read(targetPath)
    const normalized = normalizePath(targetPath)
    const styleProfitSurface = isStyleProfitSurface(targetPath, content, projectRoot)

    if (/\bfetch\s*\(/g.test(content) && styleProfitSurface && !fetchWhitelist.has(normalized)) {
      fail(`禁止裸 fetch()，必须走统一 request() 封装: ${targetPath}`)
    }

    if (/\/api\/resource/gi.test(content) && styleProfitSurface) {
      fail(`禁止 ERPNext /api/resource 直连: ${targetPath}`)
    }

    const globalForbiddenRules = [
      {
        regex: /\bstyle_profit:snapshot_create\b/g,
        message: '禁止前端业务文件出现 style_profit:snapshot_create',
      },
      {
        regex: /\bsnapshot_create\b/g,
        message: '禁止前端业务文件出现 snapshot_create',
      },
      {
        regex: /\bcreateStyleProfitSnapshot\b/g,
        message: '禁止前端业务文件出现 createStyleProfitSnapshot',
      },
      {
        regex: /(新建快照|创建快照|生成快照|创建利润快照|生成利润快照|重算利润)/g,
        message: '禁止前端出现创建/生成/重算利润快照文案',
      },
    ]

    for (const rule of globalForbiddenRules) {
      if (rule.regex.test(content)) {
        fail(`${rule.message}: ${targetPath}`)
      }
      rule.regex.lastIndex = 0
    }

    if (styleProfitSurface) {
      if (/\bidempotency_key\b/g.test(content)) {
        fail(`禁止 style-profit 业务面出现 idempotency_key: ${targetPath}`)
      }
      if (/method\s*:\s*['\"]POST['\"]/g.test(content)) {
        fail(`禁止 style-profit 业务面出现 POST 写接口: ${targetPath}`)
      }
    }
  }

  const listViewContent = read(path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotList.vue'))
  if (!listViewContent.includes("loadModuleActions('style_profit')")) {
    fail('列表页必须加载 style_profit 模块权限')
  }
  if (!listViewContent.includes('if (!canRead.value)')) {
    fail('列表页缺少 canRead 前置阻断')
  }
  if (!listViewContent.includes('if (!hasRequiredScope())')) {
    fail('列表页必须在 company/item_code 为空时阻断请求')
  }

  const detailViewContent = read(path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotDetail.vue'))
  if (!detailViewContent.includes("loadModuleActions('style_profit')")) {
    fail('详情页必须加载 style_profit 模块权限')
  }
  if (!detailViewContent.includes('if (!canRead.value)')) {
    fail('详情页缺少 canRead 前置阻断')
  }
  if (!detailViewContent.includes('存在未解析来源，请财务复核后使用')) {
    fail('详情页缺少 unresolved_count 风险提示')
  }
  if (!detailViewContent.includes('审计信息（仅供审计复核）')) {
    fail('详情页必须提供审计信息折叠区')
  }

  const permissionStoreContent = read(path.join(projectRoot, 'src/stores/permission.ts'))
  if (/snapshot_create\s*:/g.test(permissionStoreContent)) {
    fail('permission store 禁止映射 snapshot_create 按钮权限')
  }

  const routerContent = read(path.join(projectRoot, 'src/router/index.ts'))
  if (!routerContent.includes("path: '/reports/style-profit'")) {
    fail('路由缺少 /reports/style-profit')
  }
  if (!routerContent.includes("path: '/reports/style-profit/detail'")) {
    fail('路由缺少 /reports/style-profit/detail')
  }
  if (/path:\s*['\"]\/reports\/style-profit\/create['\"]/g.test(routerContent)) {
    fail('路由禁止出现 /reports/style-profit/create')
  }

  const requestContent = read(requestFile)
  if (!/const response = await fetch\(/.test(requestContent)) {
    fail('src/api/request.ts 必须保留统一 fetch 封装')
  }
  if (!requestContent.includes("result.set('Authorization'")) {
    fail('src/api/request.ts 必须保留 Authorization 组装')
  }

  const apiContent = read(path.join(projectRoot, 'src/api/style_profit.ts'))
  if (!apiContent.includes('fetchStyleProfitSnapshots')) {
    fail('src/api/style_profit.ts 缺少 fetchStyleProfitSnapshots')
  }
  if (!apiContent.includes('fetchStyleProfitSnapshotDetail')) {
    fail('src/api/style_profit.ts 缺少 fetchStyleProfitSnapshotDetail')
  }

  return {
    ok: failures.length === 0,
    failures,
    scannedFiles: targetFiles.length,
  }
}

const runCli = () => {
  const { projectRoot } = parseCliArgs(process.argv.slice(2))
  const result = checkStyleProfitContracts(projectRoot)
  if (!result.ok) {
    console.error('Style-profit contract check failed:')
    for (const [idx, message] of result.failures.entries()) {
      console.error(`${idx + 1}. ${message}`)
    }
    process.exit(1)
  }
  console.log('Style-profit contract check passed.')
  console.log(`Scanned files: ${result.scannedFiles}`)
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  runCli()
}
