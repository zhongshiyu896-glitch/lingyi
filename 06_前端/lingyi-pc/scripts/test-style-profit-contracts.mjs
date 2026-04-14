import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const checkScriptPath = path.resolve(__dirname, 'check-style-profit-contracts.mjs')

const ensureDir = (targetPath) => {
  mkdirSync(targetPath, { recursive: true })
}

const write = (root, relativePath, content) => {
  const full = path.join(root, relativePath)
  ensureDir(path.dirname(full))
  writeFileSync(full, content, 'utf8')
}

const read = (root, relativePath) => readFileSync(path.join(root, relativePath), 'utf8')

const replaceOrThrow = (input, searchValue, replaceValue, contextName) => {
  if (!input.includes(searchValue)) {
    throw new Error(`替换失败：${contextName} 未找到目标片段`)
  }
  return input.replace(searchValue, replaceValue)
}

const createBaseFixture = (root) => {
  write(
    root,
    'src/api/style_profit.ts',
    `import { request } from '@/api/request'

export const fetchStyleProfitSnapshots = async () => request('/api/reports/style-profit/snapshots')
export const fetchStyleProfitSnapshotDetail = async (snapshotId: number) =>
  request('/api/reports/style-profit/snapshots/' + snapshotId)
`,
  )

  write(
    root,
    'src/views/style_profit/StyleProfitSnapshotList.vue',
    `<script setup lang="ts">
const hasRequiredScope = () => true
async function loadRows() {
  if (!hasRequiredScope()) {
    return
  }
}
async function onMountedLoad(permissionStore: { loadModuleActions: (module: string) => Promise<void> }) {
  await permissionStore.loadModuleActions('style_profit')
}
const tip = 'company 与 item_code 不能为空'
</script>
`,
  )

  write(
    root,
    'src/views/style_profit/StyleProfitSnapshotDetail.vue',
    `<script setup lang="ts">
async function onMountedLoad(permissionStore: { loadModuleActions: (module: string) => Promise<void> }) {
  await permissionStore.loadModuleActions('style_profit')
}
const warning = '存在未解析来源，请财务复核后使用'
</script>
`,
  )

  write(
    root,
    'src/router/index.ts',
    `export default [
  { path: '/reports/style-profit' },
  { path: '/reports/style-profit/detail' },
]
`,
  )
}

const runCheck = (fixtureRoot) => {
  const result = spawnSync(process.execPath, [checkScriptPath, '--project-root', fixtureRoot], {
    encoding: 'utf8',
  })
  const output = `${result.stdout || ''}${result.stderr || ''}`
  return {
    status: result.status ?? 1,
    output,
  }
}

const assertTrue = (condition, message) => {
  if (!condition) {
    throw new Error(message)
  }
}

const runFailureCase = (caseName, mutateFixture, expectedKeyword) => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'style-profit-contracts-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    mutateFixture(fixtureRoot)
    const result = runCheck(fixtureRoot)
    assertTrue(result.status !== 0, `[${caseName}] 预期失败，但返回成功`)
    assertTrue(
      result.output.includes(expectedKeyword),
      `[${caseName}] 失败关键词不匹配，期望包含: ${expectedKeyword}\n实际输出:\n${result.output}`,
    )
    console.log(`PASS: ${caseName}`)
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const runSuccessCase = () => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'style-profit-contracts-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    const result = runCheck(fixtureRoot)
    assertTrue(result.status === 0, `合法 fixture 预期通过，实际失败:\n${result.output}`)
    assertTrue(result.output.includes('Style-profit contract check passed.'), '合法 fixture 未输出通过标识')
    console.log('PASS: minimal legal fixture')
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const failureCases = [
  {
    name: 'api contains bare fetch',
    expectedKeyword: '禁止裸 fetch()',
    mutate: (root) => {
      const content = read(root, 'src/api/style_profit.ts')
      write(root, 'src/api/style_profit.ts', `${content}\nconst invalid = fetch('/forbidden')\n`)
    },
  },
  {
    name: 'api contains snapshot_create',
    expectedKeyword: '禁止前端出现 snapshot_create',
    mutate: (root) => {
      const content = read(root, 'src/api/style_profit.ts')
      write(root, 'src/api/style_profit.ts', `${content}\nconst invalid = 'snapshot_create'\n`)
    },
  },
  {
    name: 'api contains idempotency_key',
    expectedKeyword: '禁止前端出现 idempotency_key',
    mutate: (root) => {
      const content = read(root, 'src/api/style_profit.ts')
      write(root, 'src/api/style_profit.ts', `${content}\nconst invalid = 'idempotency_key'\n`)
    },
  },
  {
    name: 'api contains POST',
    expectedKeyword: '禁止出现 POST 请求',
    mutate: (root) => {
      const content = read(root, 'src/api/style_profit.ts')
      write(root, 'src/api/style_profit.ts', `${content}\nconst invalid = { method: 'POST' }\n`)
    },
  },
  {
    name: 'list misses permission loading',
    expectedKeyword: '列表页必须加载 style_profit 模块权限',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotList.vue')
      const replaced = replaceOrThrow(
        content,
        "await permissionStore.loadModuleActions('style_profit')",
        "await permissionStore.loadModuleActions('production')",
        'loadModuleActions style_profit',
      )
      write(root, 'src/views/style_profit/StyleProfitSnapshotList.vue', replaced)
    },
  },
  {
    name: 'list misses required scope guard',
    expectedKeyword: '列表页必须在 company/item_code 为空时阻断请求',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotList.vue')
      const replaced = replaceOrThrow(content, 'if (!hasRequiredScope()) {', 'if (false) {', 'required scope guard')
      write(root, 'src/views/style_profit/StyleProfitSnapshotList.vue', replaced)
    },
  },
  {
    name: 'detail misses unresolved warning',
    expectedKeyword: '详情页缺少 unresolved_count 风险提示',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotDetail.vue')
      const replaced = replaceOrThrow(
        content,
        '存在未解析来源，请财务复核后使用',
        '无提示',
        'unresolved warning',
      )
      write(root, 'src/views/style_profit/StyleProfitSnapshotDetail.vue', replaced)
    },
  },
  {
    name: 'router misses list path',
    expectedKeyword: '路由缺少 /reports/style-profit',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      const replaced = replaceOrThrow(content, "{ path: '/reports/style-profit' },\n", '', 'list route')
      write(root, 'src/router/index.ts', replaced)
    },
  },
]

let passedCount = 0

try {
  runSuccessCase()
  passedCount += 1

  for (const failureCase of failureCases) {
    runFailureCase(failureCase.name, failureCase.mutate, failureCase.expectedKeyword)
    passedCount += 1
  }

  console.log(`All style-profit contract fixture tests passed. scenarios=${passedCount}`)
} catch (error) {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`Style-profit contract fixture tests failed: ${message}`)
  process.exit(1)
}
