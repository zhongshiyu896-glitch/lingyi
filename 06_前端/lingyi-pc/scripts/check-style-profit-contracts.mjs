import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const defaultProjectRoot = path.resolve(__dirname, '..')

const read = (targetPath) => readFileSync(targetPath, 'utf8')

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

export const checkStyleProfitContracts = (projectRootInput = defaultProjectRoot) => {
  const projectRoot = path.resolve(projectRootInput)
  const apiFile = path.join(projectRoot, 'src/api/style_profit.ts')
  const listViewFile = path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotList.vue')
  const detailViewFile = path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotDetail.vue')
  const routerFile = path.join(projectRoot, 'src/router/index.ts')
  const targetFiles = [apiFile, listViewFile, detailViewFile, routerFile]

  const failures = []
  const fail = (message) => failures.push(message)

  for (const targetFile of targetFiles) {
    if (!existsSync(targetFile)) {
      fail(`缺少契约必需文件: ${targetFile}`)
    }
  }
  if (failures.length > 0) {
    return { ok: false, failures, scannedFiles: 0 }
  }

  const fileContents = targetFiles.map((targetFile) => ({
    targetFile,
    content: read(targetFile),
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
      regex: /\bstyle_profit:snapshot_create\b/g,
      message: '禁止前端暴露 style_profit:snapshot_create',
    },
    {
      regex: /\bsnapshot_create\b/g,
      message: '禁止前端出现 snapshot_create',
    },
    {
      regex: /\bidempotency_key\b/g,
      message: '禁止前端出现 idempotency_key',
    },
    {
      regex: /\bcreateStyleProfitSnapshot\b/g,
      message: '禁止前端实现利润快照写接口',
    },
    {
      regex: /(创建|生成|重算)利润快照/g,
      message: '禁止前端出现利润快照写入口文案',
    },
  ]

  for (const { targetFile, content } of fileContents) {
    for (const rule of forbiddenRules) {
      if (rule.regex.test(content)) {
        fail(`${rule.message}: ${targetFile}`)
      }
      rule.regex.lastIndex = 0
    }
  }

  const apiContent = read(apiFile)
  if (!apiContent.includes('fetchStyleProfitSnapshots')) {
    fail('src/api/style_profit.ts 缺少 fetchStyleProfitSnapshots')
  }
  if (!apiContent.includes('fetchStyleProfitSnapshotDetail')) {
    fail('src/api/style_profit.ts 缺少 fetchStyleProfitSnapshotDetail')
  }
  if (/method\s*:\s*['"]POST['"]/.test(apiContent)) {
    fail('src/api/style_profit.ts 禁止出现 POST 请求')
  }

  const listViewContent = read(listViewFile)
  if (!listViewContent.includes("loadModuleActions('style_profit')")) {
    fail('列表页必须加载 style_profit 模块权限')
  }
  if (!listViewContent.includes('company 与 item_code 不能为空')) {
    fail('列表页缺少 company + item_code 前置校验')
  }
  if (!listViewContent.includes('if (!hasRequiredScope())')) {
    fail('列表页必须在 company/item_code 为空时阻断请求')
  }

  const detailViewContent = read(detailViewFile)
  if (!detailViewContent.includes("loadModuleActions('style_profit')")) {
    fail('详情页必须加载 style_profit 模块权限')
  }
  if (!detailViewContent.includes('存在未解析来源，请财务复核后使用')) {
    fail('详情页缺少 unresolved_count 风险提示')
  }

  const routerContent = read(routerFile)
  if (!routerContent.includes("path: '/reports/style-profit'")) {
    fail('路由缺少 /reports/style-profit')
  }
  if (!routerContent.includes("path: '/reports/style-profit/detail'")) {
    fail('路由缺少 /reports/style-profit/detail')
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
