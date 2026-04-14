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
    'src/api/request.ts',
    `const buildAuthHeaders = (headers?: HeadersInit): Headers => {
  const result = new Headers(headers)
  result.set('Authorization', 'Bearer token')
  return result
}

export const request = async <T>(url: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(url, { ...init, headers: buildAuthHeaders(init?.headers) })
  return (await response.json()) as T
}
`,
  )

  write(
    root,
    'src/api/auth.ts',
    `export const fetchModuleActions = async () => {
  const response = await fetch('/api/auth/actions')
  return response.json()
}
`,
  )

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
const canRead = { value: true }
const hasRequiredScope = () => true
async function loadRows(permissionStore: { loadModuleActions: (module: string) => Promise<void> }) {
  await permissionStore.loadModuleActions('style_profit')
  if (!canRead.value) {
    return
  }
  if (!hasRequiredScope()) {
    return
  }
}
const pageTitle = '款式利润报表'
const listTitle = '利润快照列表'
const searchTip = '查询'
const tip = 'company 与 item_code 不能为空'
</script>
`,
  )

  write(
    root,
    'src/views/style_profit/StyleProfitSnapshotDetail.vue',
    `<template>
  <el-empty v-if="!canRead" description="无款式利润查看权限" />
  <el-collapse>
    <el-collapse-item title="审计信息（仅供审计复核）" name="audit" />
  </el-collapse>
  <div>查看详情</div>
  <div>利润明细</div>
  <div>来源追溯</div>
  <div>利润金额</div>
  <div>利润率</div>
</template>
<script setup lang="ts">
const canRead = { value: true }
async function loadDetail(permissionStore: { loadModuleActions: (module: string) => Promise<void> }) {
  await permissionStore.loadModuleActions('style_profit')
  if (!canRead.value) {
    return
  }
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

  write(
    root,
    'src/stores/permission.ts',
    `const INTERNAL_ACTION_DENYLIST = [
  'production:work_order_worker',
  'subcontract:stock_sync_worker',
  'workshop:job_card_sync_worker',
]
export { INTERNAL_ACTION_DENYLIST }
`,
  )

  write(root, 'src/App.vue', `<template><router-view /></template>\n`)
  write(root, 'src/main.ts', `import './style.css'\n`)
  write(root, 'src/views/production/ProductionPlanList.vue', `<template>production</template>\n`)
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
    name: 'app exposes generate snapshot button copy',
    expectedKeyword: '禁止前端出现创建/生成/重算利润快照文案',
    mutate: (root) => {
      write(root, 'src/App.vue', `<template><button>生成利润快照</button></template>\n`)
    },
  },
  {
    name: 'other view exposes style_profit snapshot_create action',
    expectedKeyword: '禁止前端业务文件出现 style_profit:snapshot_create',
    mutate: (root) => {
      write(root, 'src/views/production/ProductionPlanList.vue', `<template>style_profit:snapshot_create</template>\n`)
    },
  },
  {
    name: 'permission store maps snapshot_create true',
    expectedKeyword: 'permission store 禁止映射 snapshot_create 按钮权限',
    mutate: (root) => {
      const content = read(root, 'src/stores/permission.ts')
      write(root, 'src/stores/permission.ts', `${content}\nconst buttonPermissions = { snapshot_create: true }\n`)
    },
  },
  {
    name: 'router has create route',
    expectedKeyword: '路由禁止出现 /reports/style-profit/create',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\n{ path: '/reports/style-profit/create' }\n`)
    },
  },
  {
    name: 'detail misses canRead pre-check',
    expectedKeyword: '详情页缺少 canRead 前置阻断',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotDetail.vue')
      const replaced = replaceOrThrow(content, 'if (!canRead.value) {', 'if (false) {', 'detail canRead guard')
      write(root, 'src/views/style_profit/StyleProfitSnapshotDetail.vue', replaced)
    },
  },
  {
    name: 'style-profit api contains POST',
    expectedKeyword: '禁止 style-profit 业务面出现 POST 写接口',
    mutate: (root) => {
      const content = read(root, 'src/api/style_profit.ts')
      write(root, 'src/api/style_profit.ts', `${content}\nconst invalid = { method: 'POST' }\n`)
    },
  },
  {
    name: 'style-profit api contains idempotency_key',
    expectedKeyword: '禁止 style-profit 业务面出现 idempotency_key',
    mutate: (root) => {
      const content = read(root, 'src/api/style_profit.ts')
      write(root, 'src/api/style_profit.ts', `${content}\nconst invalid = 'idempotency_key'\n`)
    },
  },
  {
    name: 'button contains 款式利润计算',
    expectedKeyword: '禁止前端出现款式利润中文泛化写入口语义',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><el-button>款式利润计算</el-button></template>\n`)
    },
  },
  {
    name: 'button contains 利润报表重算',
    expectedKeyword: '禁止前端出现款式利润中文泛化写入口语义',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><el-button>利润报表重算</el-button></template>\n`)
    },
  },
  {
    name: 'button contains 毛利核算',
    expectedKeyword: '禁止前端出现款式利润中文泛化写入口语义',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><el-button>毛利核算</el-button></template>\n`)
    },
  },
  {
    name: 'button contains 利润一键生成',
    expectedKeyword: '禁止前端出现款式利润中文泛化写入口语义',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><el-button>利润一键生成</el-button></template>\n`)
    },
  },
  {
    name: 'button contains 款式利润报表计算',
    expectedKeyword: '禁止前端出现款式利润中文泛化写入口语义',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><button>款式利润报表计算</button></template>\n`)
    },
  },
  {
    name: 'button contains 利润快照列表生成',
    expectedKeyword: '禁止前端出现款式利润中文泛化写入口语义',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><button>利润快照列表生成</button></template>\n`)
    },
  },
  {
    name: 'button contains 利润金额重新计算',
    expectedKeyword: '禁止前端出现款式利润中文泛化写入口语义',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><button>利润金额重新计算</button></template>\n`)
    },
  },
  {
    name: 'function openProfitCalculateDialog appears',
    expectedKeyword: '禁止前端出现款式利润写入口函数/标识符',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotList.vue')
      write(root, 'src/views/style_profit/StyleProfitSnapshotList.vue', `${content}\nfunction openProfitCalculateDialog() {}\n`)
    },
  },
  {
    name: 'router has /reports/style-profit/calculate route',
    expectedKeyword: '禁止前端出现款式利润写入口路由',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\n{ path: '/reports/style-profit/calculate' }\n`)
    },
  },
  {
    name: 'identifier generateProfitSnapshot appears',
    expectedKeyword: '禁止前端出现款式利润写入口函数/标识符',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotDetail.vue')
      write(root, 'src/views/style_profit/StyleProfitSnapshotDetail.vue', `${content}\nconst generateProfitSnapshot = () => {}\n`)
    },
  },
  {
    name: 'non-whitelist file contains bare fetch',
    expectedKeyword: '禁止裸 fetch()，必须走统一 request() 封装',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">const probe = fetch('/forbidden')</script>\n`)
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
