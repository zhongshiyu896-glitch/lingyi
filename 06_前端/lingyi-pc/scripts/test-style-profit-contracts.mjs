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
const readonlyHelpCards = [
  { label: '利润计算说明', description: '只读帮助文案' },
  { label: '返回', onClick: goBack },
  { label: '查询', onClick: loadRows },
  { label: '查看详情', onClick: goDetail },
]
const readonlyHelp = {
  meta: {
    label: '利润计算说明',
  },
  description: '只读帮助文案',
}
const readonlyHelpJson = {
  "meta": {
    "label": "利润计算说明"
  },
  "description": "只读帮助文案"
}
const readonlyHelpComputed = {
  ['label']: '利润计算说明',
  description: '只读帮助文案',
}
const readonlyHelpComputedMultiline = {
  [
    'label'
  ]: '利润计算说明',
  description: '只读说明',
}
const readonlyActionsComputed = [
  {
    ['label']: '查看详情',
    ['onClick']: goDetail,
  },
  {
    ['label']: '查询',
    ['onClick']: loadRows,
  },
  {
    ['label']: '返回',
    ['onClick']: goBack,
  },
]
const readonlyActionsJson = [
  {
    "label": "查看详情",
    "onClick": goDetail,
  },
  {
    "label": "查询",
    "onClick": loadRows,
  },
  {
    "label": "返回",
    "onClick": goBack,
  },
]
const ACTION_KEY_READ = 'onClick'
const readonlyRuntimeAccess = { label: '查看详情', onClick: goDetail }
const readonlyAccessValue = readonlyRuntimeAccess[ACTION_KEY_READ]
if (readonlyRuntimeAccess[ACTION_KEY_READ]) {
  void readonlyAccessValue
}
const readonlyUiState = { disabled: false }
readonlyUiState.disabled = true
const readonlyUiStateNext = { ...readonlyUiState, disabled: true }
void readonlyUiStateNext
function refresh() {
  return true
}
setTimeout(() => refresh(), 100)
setInterval(refresh, 1000)
setTimeout.call(window, () => refresh(), 100)
setTimeout.apply(window, [() => refresh(), 100])
Reflect.apply(setTimeout, window, [refresh, 100])
setInterval.call(window, refresh, 1000)
setInterval.apply(window, [refresh, 1000])
const readonlyRecord = { constructor_name: 'safe-constructor-name' }
const readonlyConstructorName = readonlyRecord['constructor_name']
const readonlyConstructorText = 'constructor disabled'
const readonlyNow = new Date()
void readonlyConstructorName
void readonlyConstructorText
void readonlyNow
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
  <p>利润计算说明</p>
  <p>利润率计算规则</p>
  <p>实际成本计算口径说明</p>
  <p>标准成本计算口径说明</p>
  <p>款式利润报表查看说明</p>
  <p>利润快照来源说明</p>
  <p>利润金额展示规则</p>
  <p>未解析来源处理说明</p>
  <section>利润快照来源说明</section>
  <el-alert title="实际成本计算口径说明" />
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

  write(
    root,
    'src/App.vue',
    `<template><router-view /></template>
<script setup lang="ts">
import('@/views/style_profit/StyleProfitList.vue')
import('@/views/style_profit/StyleProfitDetail.vue')
import('./local-readonly-helper')
import('../readonly/formatter')
new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })
const W = Worker
new W(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })
const { Worker: DW } = globalThis
new DW(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })
const BW = Worker.bind(null)
new BW(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })
Reflect.construct(Worker, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])
Reflect.construct(Date, [])
const getWorker = () => Worker
new (getWorker())(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })
const spreadWorkerArgs = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
new Worker(...spreadWorkerArgs)
new W(...spreadWorkerArgs)
const spreadWorkerAlias = spreadWorkerArgs
new Worker(...spreadWorkerAlias)
const [spreadWorkerArrayDestructureAlias] = [spreadWorkerArgs]
new Worker(...spreadWorkerArrayDestructureAlias)
const { value: spreadWorkerObjectDestructureAlias } = { value: spreadWorkerArgs }
new Worker(...spreadWorkerObjectDestructureAlias)
function readonly(input: unknown) {
  return input
}
for (const loopAlias of [spreadWorkerArgs]) {
  noop(loopAlias)
}
function noopDestructure([paramAlias]: [unknown]) {}
noopDestructure([spreadWorkerArgs])
[[spreadWorkerArgs]].forEach(([callbackAlias]) => {
  readonly(callbackAlias)
})
[[spreadWorkerArgs]].findIndex(([callbackAlias]) => {
  readonly(callbackAlias)
  return false
})
[[spreadWorkerArgs]].findLast(([callbackAlias]) => {
  readonly(callbackAlias)
  return false
})
[[spreadWorkerArgs]].findLastIndex(([callbackAlias]) => {
  readonly(callbackAlias)
  return false
})
[[spreadWorkerArgs]].flatMap(([callbackAlias]) => {
  readonly(callbackAlias)
  return []
})
[[spreadWorkerArgs]].reduce((acc, [callbackAlias]) => {
  readonly(callbackAlias)
  return 0
}, 0)
[[spreadWorkerArgs]].reduceRight((acc, [callbackAlias]) => {
  readonly(callbackAlias)
  return 0
}, 0)
const nums = [[1]]
void nums.reduce((acc, [n]) => acc + n, 0)
Reflect.construct(Worker, spreadWorkerArgs)
function noop() {}
noop()
const noopArrow = () => {}
noopArrow()
const safeWorkerArgsAfterNoop = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
new Worker(...safeWorkerArgsAfterNoop)
const safeArgsUsedBeforePoison = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
new Worker(...safeArgsUsedBeforePoison)
function poisonAfterUse() {
  safeArgsUsedBeforePoison[0] = 'data:text/javascript,postMessage(1)'
}
poisonAfterUse()
const dateArgs = ['2026-04-15']
new Date(...dateArgs)
const [dateArgsAlias] = [dateArgs]
new Date(...dateArgsAlias)
const urlArgs = ['./readonly-worker.ts', import.meta.url]
new URL(...urlArgs)
new Date('2026-04-15')
new Error('readonly message')
new URL('./readonly-worker.ts', import.meta.url)
const asset = '/assets/logo.png'
const record = { Worker_name: 'readonly-worker' }
void record['Worker_name']
void asset
</script>
`,
  )
  write(root, 'src/readonly-worker.ts', `export {}\n`)
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

const assertDistanceGreaterThan = (content, leftToken, rightToken, minDistance, caseName) => {
  const leftIndex = content.indexOf(leftToken)
  const rightIndex = content.indexOf(rightToken)
  assertTrue(leftIndex >= 0, `[${caseName}] 未找到左侧 token: ${leftToken}`)
  assertTrue(rightIndex >= 0, `[${caseName}] 未找到右侧 token: ${rightToken}`)
  const distance = Math.abs(rightIndex - leftIndex)
  assertTrue(
    distance > minDistance,
    `[${caseName}] token 距离不足，实际=${distance}，要求>${minDistance}，left=${leftToken}，right=${rightToken}`,
  )
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
    name: 'el-button contains 利润计算说明',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><el-button>利润计算说明</el-button></template>\n`)
    },
  },
  {
    name: 'button contains 利润率计算规则',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><button>利润率计算规则</button></template>\n`)
    },
  },
  {
    name: 'menu item with click contains 利润快照来源说明',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<template><el-menu-item @click=\"openHelp\">利润快照来源说明</el-menu-item></template>\n`,
      )
    },
  },
  {
    name: 'multiline el-button contains 利润计算说明',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><el-button>\n  利润计算说明\n</el-button></template>\n`)
    },
  },
  {
    name: 'multiline button contains 利润率计算规则',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<template><button>\n  利润率计算规则\n</button></template>\n`)
    },
  },
  {
    name: 'multiline el-menu-item click contains 利润快照来源说明',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<template><el-menu-item @click=\"openHelp\">\n  利润快照来源说明\n</el-menu-item></template>\n`,
      )
    },
  },
  {
    name: 'multiline action config contains 利润计算说明 with onClick',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    onClick: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'action label before onClick with repeat 400',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    description: 'x'.repeat(400),\n    onClick: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'action onClick before label with repeat 400',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    onClick: openHelp,\n    description: 'x'.repeat(400),\n    label: '利润计算说明',\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'action label 利润率计算规则 with handler',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润率计算规则',\n    handler: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'action label 利润快照来源说明 with command',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润快照来源说明',\n    command: 'open-help',\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'children action node label 利润计算说明 with onSelect',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '父级菜单',\n    children: [\n      {\n        label: '利润计算说明',\n        onSelect: openHelp,\n      },\n    ],\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'action label and handler gap repeat 500',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    description: 'x'.repeat(500),\n    handler: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'action label and onSelect gap repeat 1000',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    description: 'x'.repeat(1000),\n    onSelect: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'ancestor onClick with child meta label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    key: 'profit-help',\n    onClick: openHelp,\n    meta: {\n      label: '利润计算说明',\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'single-quoted handler with single-quoted props label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    'handler': showRule,\n    'props': {\n      'label': '利润率计算规则',\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'mixed quoted command with extra quoted label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst menus = [\n  {\n    \"command\": 'open-profit-source-help',\n    extra: {\n      \"label\": '利润快照来源说明',\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'quoted onClick and quoted meta.label with real 1200 filler',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    \"onClick\": openHelp,\n    \"filler\": \"${longFiller}\",\n    \"meta\": {\n      \"label\": \"利润计算说明\",\n    },\n  },\n]\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf('"label"') - content.indexOf('"onClick"')) > 1200,
        '[quoted onClick long-distance fixture] onClick 与 label 真实距离必须超过 1200 字符',
      )
      assertDistanceGreaterThan(content, '"onClick"', '"label"', 1200, 'quoted onClick long-distance fixture')
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: 'computed onClick assignment with real 1200 filler',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    filler: \"${longFiller}\",\n    ['onClick']: openHelp,\n  },\n]\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf("['onClick']") - content.indexOf('利润计算说明')) > 1200,
        "[computed onClick assignment long-distance fixture] label 与 ['onClick'] 真实距离必须超过 1200 字符",
      )
      assertDistanceGreaterThan(
        content,
        "['onClick']",
        '利润计算说明',
        1200,
        'computed onClick assignment long-distance fixture',
      )
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: 'method shorthand onClick with real 1200 filler',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    filler: \"${longFiller}\",\n    onClick() {\n      openHelp()\n    },\n  },\n]\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf('onClick()') - content.indexOf('利润计算说明')) > 1200,
        '[method shorthand onClick long-distance fixture] label 与 onClick() 真实距离必须超过 1200 字符',
      )
      assertDistanceGreaterThan(content, 'onClick()', '利润计算说明', 1200, 'method shorthand onClick long-distance fixture')
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: 'double-quoted label with double-quoted onClick method name',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    \"label\": \"利润计算说明\",\n    \"onClick\"() {\n      openHelp()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'double-quoted label with computed handler method',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    \"label\": \"利润率计算规则\",\n    [\"handler\"]() {\n      showRule()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'single-quoted label with single-quoted handler method name',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    'label': '利润率计算规则',\n    'handler'() {\n      showRule()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'async computed submit method with descendant meta label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    meta: {\n      label: '利润快照来源说明',\n    },\n    async ['submit']() {\n      await submitProfit()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'computed onClick with computed meta label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    [\"onClick\"]: openHelp,\n    [\"meta\"]: {\n      [\"label\"]: \"利润计算说明\",\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'double-quoted children tree ancestor onSelect',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst menu = [\n  {\n    \"onSelect\": selectMenu,\n    \"children\": [\n      {\n        \"meta\": {\n          \"label\": \"利润计算说明\",\n        },\n      },\n    ],\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'children descendant label with computed onSelect method',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst menu = [\n  {\n    ['onSelect']() {\n      selectMenu()\n    },\n    children: [\n      {\n        meta: {\n          label: '利润计算说明',\n        },\n      },\n    ],\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal computed key [ACTION_KEY] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst actions = [\n  {\n    label: '利润计算说明',\n    [ACTION_KEY]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal computed key [actionMap.onClick] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [actionMap.onClick]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal computed key [getActionKey()] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [getActionKey()]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal computed method shorthand [ACTION_KEY]()',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst actions = [\n  {\n    label: '利润计算说明',\n    [ACTION_KEY]() {\n      openHelp()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal async computed method shorthand [ACTION_KEY]()',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'submit'\nconst actions = [\n  {\n    meta: {\n      label: '利润快照来源说明',\n    },\n    async [ACTION_KEY]() {\n      await submitProfit()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal computed label key [labelKey] with ancestor interaction',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst labelKey = 'label'\nconst actions = [\n  {\n    onClick: openHelp,\n    [labelKey]: '利润计算说明',\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'multiline non-literal computed key [actionMap . onClick] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [actionMap\n      .onClick]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'multiline non-literal computed key [ ACTION_KEY ] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst actions = [\n  {\n    label: '利润计算说明',\n    [\n      ACTION_KEY\n    ]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'multiline non-literal computed key [getActionKey()] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [getActionKey(\n      'profit'\n    )]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'multiline non-literal computed method shorthand [actionMap . onClick]()',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [actionMap\n      .onClick]() {\n      openHelp()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'multiline non-literal async computed method [ACTION_KEY]() with descendant label',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'submit'\nconst actions = [\n  {\n    meta: {\n      label: '利润快照来源说明',\n    },\n    async [\n      ACTION_KEY\n    ]() {\n      await submitProfit()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'multiline non-literal computed key with real 1200 filler',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    filler: \"${longFiller}\",\n    [actionMap\n      .onClick]: openHelp,\n  },\n]\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf('[actionMap') - content.indexOf('利润计算说明')) > 1200,
        '[multiline non-literal computed assignment long-distance fixture] label 与 [actionMap 真实距离必须超过 1200 字符',
      )
      assertDistanceGreaterThan(
        content,
        '[actionMap',
        '利润计算说明',
        1200,
        'multiline non-literal computed assignment long-distance fixture',
      )
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: "non-literal computed key [actionMap['onClick']] assignment",
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [actionMap['onClick']]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal computed key [actionMap[\"onClick\"]] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [actionMap[\"onClick\"]]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: "non-literal computed key [getActionKey(actionMap['onClick'])] assignment",
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    [getActionKey(actionMap['onClick'])]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'non-literal computed key template literal assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst prefix = 'on'\nconst actions = [\n  {\n    label: '利润计算说明',\n    [\`\${prefix}Click\`]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: "long-distance computed key [actionMap['onClick']] assignment",
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    filler: \"${longFiller}\",\n    [actionMap['onClick']]: openHelp,\n  },\n]\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf('[actionMap') - content.indexOf('利润计算说明')) > 1200,
        '[long-distance computed key with nested bracket fixture] label 与 [actionMap 真实距离必须超过 1200 字符',
      )
      assertDistanceGreaterThan(
        content,
        '[actionMap',
        '利润计算说明',
        1200,
        'long-distance computed key with nested bracket fixture',
      )
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: 'neutral items container with [ACTION_KEY] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst items = [\n  {\n    label: '查看详情',\n    [ACTION_KEY]: goDetail,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: "neutral rows container with [actionMap['onClick']] assignment",
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst rows = [\n  {\n    label: '查询',\n    [actionMap['onClick']]: loadRows,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'neutral configs container with [getActionKey()] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst configs = [\n  {\n    label: '返回',\n    [getActionKey()]: goBack,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'neutral columns container with dynamic [labelKey]',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst labelKey = 'label'\nconst columns = [\n  {\n    [labelKey]: '利润计算说明',\n    description: '只读说明',\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'unknown computed key factory should fail closed',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst items = [\n  {\n    label: '查看详情',\n    [unknownKeyFactory()]: goDetail,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'vue script setup neutral items container with [ACTION_KEY]',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotList.vue')
      const injected = replaceOrThrow(
        content,
        '</script>\n',
        `const ACTION_KEY = 'onClick'\nconst items = [\n  {\n    label: '查看详情',\n    [ACTION_KEY]: goDetail,\n  },\n]\n</script>\n`,
        'list vue script setup dynamic key',
      )
      write(root, 'src/views/style_profit/StyleProfitSnapshotList.vue', injected)
    },
  },
  {
    name: 'long-distance neutral items with [ACTION_KEY] assignment',
    expectedKeyword: 'style-profit forbids dynamic or unknown computed keys in object literals',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst items = [\n  {\n    label: '查看详情',\n    filler: \"${longFiller}\",\n    [ACTION_KEY]: goDetail,\n  },\n]\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf('[ACTION_KEY]') - content.indexOf('查看详情')) > 1200,
        '[long-distance neutral items dynamic key fixture] label 与 [ACTION_KEY] 真实距离必须超过 1200 字符',
      )
      assertDistanceGreaterThan(
        content,
        '[ACTION_KEY]',
        '查看详情',
        1200,
        'long-distance neutral items dynamic key fixture',
      )
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: 'runtime injection via item[ACTION_KEY] assignment',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst item = { label: '查看详情' }\nitem[ACTION_KEY] = goDetail\n</script>\n`,
      )
    },
  },
  {
    name: "runtime injection via item[actionMap['onClick']] assignment",
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '查看详情' }\nitem[actionMap['onClick']] = goDetail\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime injection via Object.defineProperty dynamic key',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst item = { label: '查看详情' }\nObject.defineProperty(item, ACTION_KEY, { value: goDetail })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime injection via Reflect.set dynamic key',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst item = { label: '查看详情' }\nReflect.set(item, ACTION_KEY, goDetail)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime injection via Object.defineProperties dynamic key',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst item = { label: '查看详情' }\nObject.defineProperties(item, {\n  [ACTION_KEY]: { value: goDetail },\n})\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime injection via Object.assign dynamic source key',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst item = { label: '查看详情' }\nObject.assign(item, {\n  [ACTION_KEY]: goDetail,\n})\n</script>\n`,
      )
    },
  },
  {
    name: 'vue script setup runtime injection via item[ACTION_KEY] assignment',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotList.vue')
      const injected = replaceOrThrow(
        content,
        '</script>\n',
        `const ACTION_KEY = 'onClick'\nconst item = { label: '查看详情' }\nitem[ACTION_KEY] = goDetail\n</script>\n`,
        'list vue script setup runtime dynamic injection',
      )
      write(root, 'src/views/style_profit/StyleProfitSnapshotList.vue', injected)
    },
  },
  {
    name: 'long-distance runtime injection via item[ACTION_KEY] assignment',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'onClick'\nconst item = {\n  label: '查看详情',\n  filler: \"${longFiller}\",\n}\nitem[ACTION_KEY] = goDetail\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf('item[ACTION_KEY]') - content.indexOf('查看详情')) > 1200,
        '[long-distance runtime injection fixture] label 与 item[ACTION_KEY] 真实距离必须超过 1200 字符',
      )
      assertDistanceGreaterThan(
        content,
        'item[ACTION_KEY]',
        '查看详情',
        1200,
        'long-distance runtime injection fixture',
      )
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: "runtime explicit action key injection via item['onClick'] assignment",
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nitem['onClick'] = openHelp\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via item.onClick assignment',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nitem.onClick = openHelp\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.defineProperty literal key',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.defineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.assign literal key',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.assign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect.set literal key',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.set(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.defineProperties literal key',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.defineProperties(item, {\n  onClick: { value: openHelp },\n})\n</script>\n`,
      )
    },
  },
  {
    name: "runtime explicit action key injection with readonly label '查看详情'",
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '查看详情' }\nitem['onClick'] = goDetail\n</script>\n`,
      )
    },
  },
  {
    name: 'vue script setup runtime explicit action key injection via Object.assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/views/style_profit/StyleProfitSnapshotList.vue')
      const injected = replaceOrThrow(
        content,
        '</script>\n',
        `const item = { label: '利润计算说明' }\nObject.assign(item, { onClick: openHelp })\n</script>\n`,
        'list vue script setup explicit runtime action injection',
      )
      write(root, 'src/views/style_profit/StyleProfitSnapshotList.vue', injected)
    },
  },
  {
    name: 'long-distance runtime explicit action key injection via Object.defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const base = read(root, 'src/App.vue')
      const longFiller = 'x'.repeat(1200)
      const appended = `\n<script setup lang=\"ts\">\nconst item = {\n  label: '利润计算说明',\n  filler: \"${longFiller}\",\n}\nObject.defineProperty(item, 'onClick', { value: openHelp })\n</script>\n`
      const content = `${base}${appended}`
      assertTrue(
        Math.abs(content.indexOf("Object.defineProperty") - content.indexOf('利润计算说明')) > 1200,
        '[long-distance runtime explicit action injection fixture] label 与 Object.defineProperty 真实距离必须超过 1200 字符',
      )
      assertDistanceGreaterThan(
        content,
        'Object.defineProperty',
        '利润计算说明',
        1200,
        'long-distance runtime explicit action injection fixture',
      )
      write(root, 'src/App.vue', content)
    },
  },
  {
    name: "runtime explicit action key injection via Object['defineProperty'] literal key",
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject['defineProperty'](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime explicit action key injection via Reflect['set'] literal key",
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect['set'](item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime explicit action key injection via Object['assign'] literal source",
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject['assign'](item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via defineProperty alias call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst defineProperty = Object.defineProperty\nconst item = { label: '利润计算说明' }\ndefineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assign alias call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst assign = Object.assign\nconst item = { label: '利润计算说明' }\nassign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via set alias call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst set = Reflect.set\nconst item = { label: '利润计算说明' }\nset(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.assign variable source',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst action = { onClick: openHelp }\nconst item = { label: '利润计算说明' }\nObject.assign(item, action)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime explicit action key injection via Object['assign'] variable source",
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst action = { handler: openHelp }\nconst item = { label: '利润计算说明' }\nObject['assign'](item, action)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.assign multi-source variable',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst base = { disabled: false }\nconst action = { onClick: openHelp }\nconst extra = { tooltip: '说明' }\nconst item = { label: '利润计算说明' }\nObject.assign(item, base, action, extra)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic source merge fail closed when source unresolved',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.assign(item, actionSource)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object-destructure defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { defineProperty } = Object\nconst item = { label: '利润计算说明' }\ndefineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object-destructure rename defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { defineProperty: dp } = Object\nconst item = { label: '利润计算说明' }\ndp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object-destructure defineProperties',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { defineProperties } = Object\nconst item = { label: '利润计算说明' }\ndefineProperties(item, { onClick: { value: openHelp } })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object-destructure assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { assign } = Object\nconst item = { label: '利润计算说明' }\nassign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object-destructure rename assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { assign: merge } = Object\nconst item = { label: '利润计算说明' }\nmerge(item, { handler: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via reflect-destructure set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { set } = Reflect\nconst item = { label: '利润计算说明' }\nset(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via reflect-destructure rename set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { set: reflectSet } = Reflect\nconst item = { label: '利润计算说明' }\nreflectSet(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object namespace alias property call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst Obj = Object\nconst item = { label: '利润计算说明' }\nObj.defineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object namespace alias bracket call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst Obj = Object\nconst item = { label: '利润计算说明' }\nObj['assign'](item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via reflect namespace alias property call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst R = Reflect\nconst item = { label: '利润计算说明' }\nR.set(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via reflect namespace alias bracket call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst R = Reflect\nconst item = { label: '利润计算说明' }\nR['set'](item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet defineProperty\n;({ defineProperty } = Object)\nconst item = { label: '利润计算说明' }\ndefineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure rename defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet dp\n;({ defineProperty: dp } = Object)\nconst item = { label: '利润计算说明' }\ndp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet assign\n;({ assign } = Object)\nconst item = { label: '利润计算说明' }\nassign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure reflect set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet set\n;({ set } = Reflect)\nconst item = { label: '利润计算说明' }\nset(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via bind alias defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst defineProperty = Object.defineProperty.bind(Object)\nconst item = { label: '利润计算说明' }\ndefineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via bind alias assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst assign = Object.assign.bind(Object)\nconst item = { label: '利润计算说明' }\nassign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via bind alias reflect set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst set = Reflect.set.bind(Reflect)\nconst item = { label: '利润计算说明' }\nset(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.defineProperty.call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.defineProperty.call(Object, item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.defineProperty.apply',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.defineProperty.apply(Object, [item, 'onClick', { value: openHelp }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.assign.call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.assign.call(Object, item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Object.assign.apply',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.assign.apply(Object, [item, { onClick: openHelp }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect.set.call',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.set.call(Reflect, item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect.set.apply',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.set.apply(Reflect, [item, 'onClick', openHelp])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via globalThis.Object namespace alias',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst Obj = globalThis.Object\nconst item = { label: '利润计算说明' }\nObj.defineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via window.Reflect namespace alias',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst R = window.Reflect\nconst item = { label: '利润计算说明' }\nR.set(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via globalThis.Object.assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nglobalThis.Object.assign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via window.Reflect.set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nwindow.Reflect.set(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime apply with non-array args fail closed',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nconst argsTuple = [item, 'onClick', { value: openHelp }]\nObject.defineProperty.apply(Object, argsTuple)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect.apply Object.defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.apply(Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect.apply Object.defineProperties',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.apply(Object.defineProperties, Object, [item, { onClick: { value: openHelp } }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect.apply Object.assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.apply(Object.assign, Object, [item, { onClick: openHelp }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect.apply Reflect.set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.apply(Reflect.set, Reflect, [item, 'onClick', openHelp])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime explicit action key injection via Reflect['apply']",
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect['apply'](Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via Reflect alias apply',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst R = Reflect\nconst item = { label: '利润计算说明' }\nR.apply(Object.assign, Object, [item, { onClick: openHelp }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure string defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet dp\n;({ 'defineProperty': dp } = Object)\nconst item = { label: '利润计算说明' }\ndp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure string assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet merge\n;({ \"assign\": merge } = Object)\nconst item = { label: '利润计算说明' }\nmerge(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure computed literal defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet dp\n;({ ['defineProperty']: dp } = Object)\nconst item = { label: '利润计算说明' }\ndp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via assignment-destructure computed literal set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet set\n;({ ['set']: set } = Reflect)\nconst item = { label: '利润计算说明' }\nset(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via globalThis Object destructure alias',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { Object: Obj } = globalThis\nconst item = { label: '利润计算说明' }\nObj.defineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via window Reflect destructure alias',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { Reflect: R } = window\nconst item = { label: '利润计算说明' }\nR.set(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime Reflect.apply with non-array literal args fail closed',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nconst args = [item, 'onClick', { value: openHelp }]\nReflect.apply(Object.defineProperty, Object, args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime non-literal computed mutator source in assignment-destructure fail closed',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ACTION_KEY = 'defineProperty'\nlet dp\n;({ [ACTION_KEY]: dp } = Object)\nconst item = { label: '利润计算说明' }\ndp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via comma callee Object.defineProperty',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;(0, Object.defineProperty)(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via comma callee Object.assign',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;(0, Object.assign)(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via comma callee Reflect.set',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;(0, Reflect.set)(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via conditional Object namespace alias',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst Obj = true ? Object : Object\nconst item = { label: '利润计算说明' }\nObj.defineProperty(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via conditional Reflect namespace alias',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst R = condition ? Reflect : Reflect\nconst item = { label: '利润计算说明' }\nR.set(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via conditional globalThis/window Object namespace alias',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst Obj = condition ? globalThis.Object : window.Object\nconst item = { label: '利润计算说明' }\nObj.assign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via array mutator container index 0',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst mutators = [Object.defineProperty]\nconst item = { label: '利润计算说明' }\nmutators[0](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via array mutator container index 1',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst mutators = [Object.assign, Reflect.set]\nconst item = { label: '利润计算说明' }\nmutators[1](item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic property injection via array mutator container dynamic index fail closed',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst mutators = [Object.defineProperty]\nconst index = 0\nconst item = { label: '利润计算说明' }\nmutators[index](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic property injection via array mutator container spread fail closed',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst extra = []\nconst mutators = [Object.defineProperty, ...extra]\nconst item = { label: '利润计算说明' }\nmutators[0](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object mutator container property access',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst mutators = { dp: Object.defineProperty }\nconst item = { label: '利润计算说明' }\nmutators.dp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime explicit action key injection via object mutator container literal element access',
    expectedKeyword: 'style-profit forbids runtime explicit action-key injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst mutators = { assign: Object.assign }\nconst item = { label: '利润计算说明' }\nmutators['assign'](item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic property injection via object mutator container dynamic key fail closed',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst mutators = { set: Reflect.set }\nconst key = 'set'\nconst item = { label: '利润计算说明' }\nmutators[key](item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic property injection via object mutator container spread fail closed',
    expectedKeyword: 'style-profit forbids runtime dynamic property injection',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst extra = {}\nconst mutators = { dp: Object.defineProperty, ...extra }\nconst item = { label: '利润计算说明' }\nmutators.dp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "descendant meta label with ancestor [actionMap['onClick']] assignment",
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    meta: {\n      label: '利润快照来源说明',\n    },\n    [actionMap['onClick']]: openHelp,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'spread profitAction with explanation label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    label: '利润计算说明',\n    ...profitAction,\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'async submit method shorthand with descendant meta label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    meta: {\n      label: '利润快照来源说明',\n    },\n    async submit() {\n      await submitProfit()\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'children descendant label with ancestor onSelect method shorthand',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst menu = [\n  {\n    onSelect() {\n      selectMenu()\n    },\n    children: [\n      {\n        meta: {\n          label: '利润计算说明',\n        },\n      },\n    ],\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'ancestor execute with payload label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    execute: runHelp,\n    payload: {\n      label: '利润计算说明',\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'ancestor onCommand with child meta title',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst menu = [\n  {\n    onCommand: openHelp,\n    meta: {\n      title: '利润计算说明',\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'ancestor callback with child payload label',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    callback: openHelp,\n    payload: {\n      label: '利润快照来源说明',\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'ancestor submit with child extra description',
    expectedKeyword: '只读说明文案不得出现在交互入口上下文',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst actions = [\n  {\n    submit: submitHelp,\n    extra: {\n      description: '利润率计算规则',\n    },\n  },\n]\n</script>\n`,
      )
    },
  },
  {
    name: 'multiline route config has /reports/style-profit/calculate',
    expectedKeyword: '禁止前端出现款式利润写入口路由',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(
        root,
        'src/router/index.ts',
        `${content}\n{\n  path: '/reports/style-profit/calculate',\n  name: 'ProfitCalculationHelp',\n}\n`,
      )
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
    name: 'runtime mutator source via function return Object.defineProperty',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nfunction getMutator() {\n  return Object.defineProperty\n}\nconst item = { label: '利润计算说明' }\ngetMutator()(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via arrow function return Object.assign',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getMutator = () => Object.assign\nconst item = { label: '利润计算说明' }\ngetMutator()(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via iife return Object.defineProperty',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;(() => Object.defineProperty)()(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via inline array relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;[Object.defineProperty][0](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via inline object relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;({ dp: Object.defineProperty }).dp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via nested array relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst nested = [[Object.defineProperty]]\nconst item = { label: '利润计算说明' }\nnested[0][0](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via Object.freeze wrapper relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst frozen = Object.freeze({ dp: Object.defineProperty })\nconst item = { label: '利润计算说明' }\nfrozen.dp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via Object.seal wrapper relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst sealed = Object.seal({ assign: Object.assign })\nconst item = { label: '利润计算说明' }\nsealed.assign(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via conditional array relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst mutators = condition ? [Object.defineProperty] : [Object.defineProperty]\nconst item = { label: '利润计算说明' }\nmutators[0](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via conditional object relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst mutators = condition ? { dp: Object.defineProperty } : { dp: Object.defineProperty }\nconst item = { label: '利润计算说明' }\nmutators.dp(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via globalThis Object.assign return relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getMutator = () => globalThis.Object.assign\nconst item = { label: '利润计算说明' }\ngetMutator()(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via window Reflect.set return relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getMutator = () => window.Reflect.set\nconst item = { label: '利润计算说明' }\ngetMutator()(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via holder function property relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst holder = { make: () => Object.defineProperty }\nconst item = { label: '利润计算说明' }\nholder.make()(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via holder array function relay',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst holder = [() => Object.assign]\nconst item = { label: '利润计算说明' }\nholder[0]()(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source reference without call should fail',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst dangerous = Object.defineProperty\n</script>\n`)
    },
  },
  {
    name: 'runtime mutator source object container without call should fail',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst dangerous = { dp: Object.defineProperty }\n</script>\n`)
    },
  },
  {
    name: "runtime mutator source via Object['define' + 'Property']",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject['define' + 'Property'](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via Object['ass' + 'ign']",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject['ass' + 'ign'](item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via Reflect['s' + 'et']",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect['s' + 'et'](item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via Reflect['ap' + 'ply']",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect['ap' + 'ply'](Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via template literal member key',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject[\`define\${'Property'}\`](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via globalThis['Object']['assign']",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nglobalThis['Object']['assign'](item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via window['Reflect']['set']",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nwindow['Reflect']['set'](item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via globalThis template element chain',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nglobalThis[\`Reflect\`][\`set\`](item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via Reflect.get(Object, 'defineProperty')",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.get(Object, 'defineProperty')(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via Reflect.get(Object, 'ass' + 'ign')",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect.get(Object, 'ass' + 'ign')(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via Reflect['get'](Reflect, 'set')",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect['get'](Reflect, 'set')(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via Reflect.get unresolved key fail closed',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst dynamicKey = getMutatorName()\nconst item = { label: '利润计算说明' }\nReflect.get(Object, dynamicKey)(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via optional call Object.defineProperty?.',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject.defineProperty?.(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via optional chain Object?.defineProperty?.',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject?.defineProperty?.(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via optional chain Object?.['assign']?.",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nObject?.['assign']?.(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime mutator source via optional chain Reflect?.['set']?.",
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nReflect?.['set']?.(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via Object[key] unresolved member fail closed',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst key = getMutatorName()\nconst item = { label: '利润计算说明' }\nObject[key](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime mutator source via globalThis[objKey][methodKey] unresolved chain fail closed',
    expectedKeyword: 'style-profit forbids runtime mutator source references',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst objKey = getObjectKey()\nconst methodKey = getMethodKey()\nconst item = { label: '利润计算说明' }\nglobalThis[objKey][methodKey](item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via Function('return Object.assign')()",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nFunction('return Object.assign')()(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via new Function('return Object.defineProperty')()",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nnew Function('return Object.defineProperty')()(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via eval('Reflect.set')",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\neval('Reflect.set')(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via globalThis.Function('return Object.assign')()",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nglobalThis.Function('return Object.assign')()(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via window.Function('return Reflect.set')()",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nwindow.Function('return Reflect.set')()(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via globalThis.eval('Object.assign')",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nglobalThis.eval('Object.assign')(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via window.eval('Object.defineProperty')",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nwindow.eval('Object.defineProperty')(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via indirect eval (0, eval)('Object.assign')",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;(0, eval)('Object.assign')(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via alias const make = Function',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst make = Function\nmake('return Object.assign')()\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via alias const run = eval',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst run = eval\nrun('Reflect.set')\n</script>\n`)
    },
  },
  {
    name: 'runtime codegen via destructure const { Function: Fn } = globalThis',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { Function: Fn } = globalThis\nFn('return Object.assign')()\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via destructure const { eval: run } = window',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { eval: run } = window\nrun('Object.defineProperty')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via globalThis['Function']",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nglobalThis['Function']('return Object.assign')()\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via window['eval']",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nwindow['eval']('Object.assign')\n</script>\n`)
    },
  },
  {
    name: "runtime codegen via globalThis['Func' + 'tion']",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nglobalThis['Func' + 'tion']('return Reflect.set')()\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via window[`ev${'al'}`]",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nwindow[\`ev\${'al'}\`]('Object.defineProperty')\n</script>\n`)
    },
  },
  {
    name: 'runtime codegen source reference const dangerous = Function',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst dangerous = Function\n</script>\n`)
    },
  },
  {
    name: 'runtime codegen source container const holder = { make: Function }',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst holder = { make: Function }\n</script>\n`)
    },
  },
  {
    name: 'runtime codegen source function return const getFn = () => Function',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst getFn = () => Function\n</script>\n`)
    },
  },
  {
    name: 'runtime codegen source conditional const maker = condition ? Function : Function',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst maker = condition ? Function : Function\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout string argument',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nsetTimeout(\"Object.assign(item, { onClick: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setInterval string argument',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nsetInterval(\"Reflect.set(item, 'onClick', openHelp)\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via window.setTimeout string argument',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nwindow.setTimeout(\"Object.defineProperty(item, 'onClick', { value: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via globalThis.setInterval string argument',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nglobalThis.setInterval(\"Object.assign(item, { onClick: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout template literal argument',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nsetTimeout(\`Object.assign(item, { onClick: openHelp })\`)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout concatenated string argument',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\nsetTimeout('Object.' + 'assign(item, { onClick: openHelp })')\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout unresolved variable argument',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst code = \"Object.assign(item, { onClick: openHelp })\"\nsetTimeout(code)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via alias const delay = setTimeout',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst delay = setTimeout\ndelay(\"Object.assign(item, { onClick: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via destructured delay from window.setTimeout',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { setTimeout: delay } = window\ndelay(\"Object.defineProperty(item, 'onClick', { value: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via indirect (0, setTimeout) call',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\n;(0, setTimeout)(\"Reflect.set(item, 'onClick', openHelp)\")\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via window['set' + 'Timeout'] dynamic member",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nwindow['set' + 'Timeout'](\"Object.assign(item, { onClick: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout.call string callback',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nsetTimeout.call(window, \"Object.assign(item, { onClick: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setInterval.call string callback',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nsetInterval.call(globalThis, \"Reflect.set(item, 'onClick', openHelp)\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via window.setTimeout.call string callback',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nwindow.setTimeout.call(window, \"Object.defineProperty(item, 'onClick', { value: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via globalThis.setInterval.call string callback',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nglobalThis.setInterval.call(globalThis, \"Reflect.set(item, 'onClick', openHelp)\")\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via setTimeout['call'] string callback",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nsetTimeout['call'](window, \"Object.assign(item, { onClick: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout.apply string callback array',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nsetTimeout.apply(window, [\"Object.assign(item, { onClick: openHelp })\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setInterval.apply string callback array',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nsetInterval.apply(globalThis, [\"Reflect.set(item, 'onClick', openHelp)\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via window.setTimeout.apply string callback array',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nwindow.setTimeout.apply(window, [\"Object.defineProperty(item, 'onClick', { value: openHelp })\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via globalThis.setInterval.apply string callback array',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nglobalThis.setInterval.apply(globalThis, [\"Reflect.set(item, 'onClick', openHelp)\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via setTimeout['apply'] string callback array",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nsetTimeout['apply'](window, [\"Object.assign(item, { onClick: openHelp })\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout.apply unresolved args variable',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [\"Object.assign(item, { onClick: openHelp })\", 0]\nsetTimeout.apply(window, args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via setTimeout.apply unresolved code identifier in args',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst code = \"Object.assign(item, { onClick: openHelp })\"\nsetTimeout.apply(window, [code, 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via Reflect.apply(setTimeout, ...string callback...)',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nReflect.apply(setTimeout, window, [\"Object.assign(item, { onClick: openHelp })\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via Reflect.apply(window.setTimeout, ...string callback...)',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nReflect.apply(window.setTimeout, window, [\"Object.defineProperty(item, 'onClick', { value: openHelp })\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via Reflect.apply(globalThis.setInterval, ...string callback...)',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nReflect.apply(globalThis.setInterval, globalThis, [\"Reflect.set(item, 'onClick', openHelp)\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via Reflect['apply'](setTimeout, ...string callback...)",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nReflect['apply'](setTimeout, window, [\"Object.assign(item, { onClick: openHelp })\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via alias const delay = setTimeout then delay.call string callback',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst delay = setTimeout\ndelay.call(window, \"Object.assign(item, { onClick: openHelp })\")\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via alias const delay = setTimeout then delay.apply string callback',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst delay = setTimeout\ndelay.apply(window, [\"Object.assign(item, { onClick: openHelp })\", 0])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via import('data:text/javascript,export default Object.assign')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nimport('data:text/javascript,export default Object.assign')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via import('data:text/javascript,export default Reflect.set')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nimport('data:text/javascript,export default Reflect.set')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via import('blob:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nimport('blob:https://example.local/module')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via import('javascript:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nimport('javascript:alert(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via import('https://...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nimport('https://cdn.example.com/mod.js')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via import('data:' + ...)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nimport('data:' + 'text/javascript,export default Object.assign')\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via template literal folded to data protocol',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nimport(\`data:text/javascript,export default \${'Object.assign'}\`)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via import(url) with data literal variable',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst url = 'data:text/javascript,export default Object.assign'\nimport(url)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via import(getModuleUrl())',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst safeMaybe = getModuleUrl()\nimport(safeMaybe)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via import(moduleMap[key])',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst moduleMap = { a: '@/views/style_profit/StyleProfitList.vue' }\nconst key = 'a'\nimport(moduleMap[key])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via import(/* @vite-ignore */ url)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst url = '@/views/style_profit/StyleProfitList.vue'\nimport(/* @vite-ignore */ url)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via blob url variable then import(blobUrl)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst blobUrl = URL.createObjectURL(new Blob(['export default Object.assign'], { type: 'text/javascript' }))\nimport(blobUrl)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via import(URL.createObjectURL(new Blob(...)))',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nimport(URL.createObjectURL(new Blob(['export default Reflect.set'], { type: 'text/javascript' })))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via window.URL.createObjectURL script mime',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nwindow.URL.createObjectURL(new Blob(['export default Object.assign'], { type: 'application/javascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via globalThis.URL.createObjectURL script mime',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nglobalThis.URL.createObjectURL(new Blob(['export default Reflect.set'], { type: 'text/ecmascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function return blob url and import(makeUrl())',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst makeUrl = () => URL.createObjectURL(new Blob(['export default Object.assign']))\nimport(makeUrl())\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new Worker(URL.createObjectURL(new Blob(...)))',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nnew Worker(URL.createObjectURL(new Blob(['postMessage(1)'], { type: 'text/javascript' })))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via script.src = URL.createObjectURL(new Blob(...))',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst script = document.createElement('script')\nscript.src = URL.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via URL.createObjectURL.call(URL, new Blob(...))',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nURL.createObjectURL.call(URL, new Blob(['export default Object.assign'], { type: 'text/javascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via URL.createObjectURL.apply(URL, [new Blob(...)])',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nURL.createObjectURL.apply(URL, [new Blob(['export default Reflect.set'], { type: 'text/javascript' })])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via window.URL.createObjectURL.call(window.URL, new Blob(...))',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nwindow.URL.createObjectURL.call(window.URL, new Blob(['console.log(1)'], { type: 'text/javascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via globalThis.URL.createObjectURL.apply(globalThis.URL, [new Blob(...)])',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nglobalThis.URL.createObjectURL.apply(globalThis.URL, [new Blob(['console.log(1)'], { type: 'application/javascript' })])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via alias const make = URL.createObjectURL',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst make = URL.createObjectURL\nconst blobUrl = make(new Blob(['export default Object.assign'], { type: 'text/javascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via destructured createObjectURL alias',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { createObjectURL } = URL\ncreateObjectURL(new Blob(['export default Reflect.set'], { type: 'text/javascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via namespace alias U.createObjectURL',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst U = URL\nU.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' }))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via blobUrl variable then import(blobUrl) from alias createObjectURL',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst make = URL.createObjectURL\nconst blobUrl = make(new Blob(['export default Object.assign'], { type: 'text/javascript' }))\nimport(blobUrl)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via blobUrl variable then new Worker(blobUrl)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst blobUrl = URL.createObjectURL(new Blob(['postMessage(1)'], { type: 'text/javascript' }))\nnew Worker(blobUrl)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via blobUrl variable then script.src = blobUrl',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst script = document.createElement('script')\nconst blobUrl = URL.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' }))\nscript.src = blobUrl\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new Worker('data:text/javascript,...', { type: 'module' })",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nnew Worker('data:text/javascript,postMessage(1)', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new Worker('./readonly-worker.ts', { type: 'module' }) non-canonical literal",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nnew Worker('./readonly-worker.ts', { type: 'module' })\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via new Worker('/runtime/style-profit-worker.js', { type: 'module' }) non-canonical literal",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nnew Worker('/runtime/style-profit-worker.js', { type: 'module' })\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via new Worker('blob:https://example.local/worker')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nnew Worker('blob:https://example.local/worker')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via new Worker('https://cdn.example.com/worker.js')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nnew Worker('https://cdn.example.com/worker.js')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via new SharedWorker('data:text/javascript,postMessage(1)')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nnew SharedWorker('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new Worker(workerUrl) unresolved identifier',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst workerUrl = getWorkerUrl()\nnew Worker(workerUrl)\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via script.src = 'data:text/javascript,console.log(1)'",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst script = document.createElement('script')\nscript.src = 'data:text/javascript,console.log(1)'\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via script.src = 'https://cdn.example.com/a.js'",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst script = document.createElement('script')\nscript.src = 'https://cdn.example.com/a.js'\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via script.setAttribute('src', blobUrl)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst script = document.createElement('script')\nconst blobUrl = URL.createObjectURL(new Blob(['console.log(1)'], { type: 'text/javascript' }))\nscript.setAttribute('src', blobUrl)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const W = Worker; new W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst W = Worker\nnew W('data:text/javascript,postMessage(1)', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const SW = SharedWorker; new SW('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst SW = SharedWorker\nnew SW('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const G = globalThis; new G.Worker('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst G = globalThis\nnew G.Worker('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const Win = window; new Win.SharedWorker('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst Win = window\nnew Win.SharedWorker('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const G = globalThis; new G['Worker']('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst G = globalThis\nnew G['Worker']('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const G = globalThis; new G['Work' + 'er']('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst G = globalThis\nnew G['Work' + 'er']('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const { Worker: W } = globalThis; new W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst { Worker: W } = globalThis\nnew W('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const { SharedWorker: SW } = window; new SW('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst { SharedWorker: SW } = window\nnew SW('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via assignment destructure Worker alias then new W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nlet W\n;({ Worker: W } = globalThis)\nnew W('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via conditional alias Worker/Worker then new W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst W = condition ? Worker : Worker\nnew W('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via conditional alias globalThis.Worker/window.Worker then new W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst W = condition ? globalThis.Worker : window.Worker\nnew W('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via conditional alias Worker/unknownCtor then new W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst unknownCtor = Date\nconst W = condition ? Worker : unknownCtor\nnew W('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via array container [Worker] then new constructors[0]('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst constructors = [Worker]\nnew constructors[0]('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via object container { W: Worker } then new constructors.W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst constructors = { W: Worker }\nnew constructors.W('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via array container [Worker, ...extra] then new constructors[0]('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst extra = []\nconst constructors = [Worker, ...extra]\nnew constructors[0]('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via object container { W: Worker, ...extra } then new constructors.W('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst extra = {}\nconst constructors = { W: Worker, ...extra }\nnew constructors.W('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via alias Worker with unresolved workerUrl source",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst W = Worker\nconst workerUrl = getWorkerUrl()\nnew W(workerUrl)\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via new (Worker.bind(null))('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nnew (Worker.bind(null))('data:text/javascript,postMessage(1)', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new (SharedWorker.bind(null))('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nnew (SharedWorker.bind(null))('data:text/javascript,postMessage(1)')\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const BW = Worker.bind(null); new BW('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst BW = Worker.bind(null)\nnew BW('data:text/javascript,postMessage(1)', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const BSW = SharedWorker.bind(null); new BSW('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst BSW = SharedWorker.bind(null)\nnew BSW('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const BW = Worker.bind(null, 'data:...'); new BW(...)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst BW = Worker.bind(null, 'data:text/javascript,postMessage(1)')\nnew BW({ type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(Worker, ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nReflect.construct(Worker, ['data:text/javascript,postMessage(1)', { type: 'module' }])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(SharedWorker, ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nReflect.construct(SharedWorker, ['data:text/javascript,postMessage(1)'])\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const rc = Reflect.construct; rc(Worker, ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst rc = Reflect.construct\nrc(Worker, ['data:text/javascript,postMessage(1)'])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const { construct } = Reflect; construct(Worker, ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst { construct } = Reflect\nconstruct(Worker, ['data:text/javascript,postMessage(1)'])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect['construct'](Worker, ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nReflect['construct'](Worker, ['data:text/javascript,postMessage(1)'])\n</script>\n`)
    },
  },
  {
    name: 'runtime dynamic module loading via Reflect.construct(Worker, [workerUrl]) unresolved identifier',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst workerUrl = getWorkerUrl()\nReflect.construct(Worker, [workerUrl])\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via const args = ['data:...']; Reflect.construct(Worker, args)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = ['data:text/javascript,postMessage(1)']\nReflect.construct(Worker, args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via const args = [workerUrl]; Reflect.construct(Worker, args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst workerUrl = getWorkerUrl()\nconst args = [workerUrl]\nReflect.construct(Worker, args)\n</script>\n`)
    },
  },
  {
    name: 'runtime dynamic module loading via Reflect.construct(Worker, [...args]) spread args',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst args = ['data:text/javascript,postMessage(1)']\nReflect.construct(Worker, [...args])\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(unknownCtor, ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = Date\nReflect.construct(unknownCtor, ['data:text/javascript,postMessage(1)'])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(Worker, ['data:...'], SafeCtor)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nclass SafeCtor {}\nReflect.construct(Worker, ['data:text/javascript,postMessage(1)'], SafeCtor)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getWorker = () => Worker; new (getWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getWorker = () => Worker\nnew (getWorker())('data:text/javascript,postMessage(1)', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via function getWorker(){return Worker}; new (getWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nfunction getWorker() { return Worker }\nnew (getWorker())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getSharedWorker = () => SharedWorker; new (getSharedWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getSharedWorker = () => SharedWorker\nnew (getSharedWorker())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getWorker = () => globalThis.Worker; new (getWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getWorker = () => globalThis.Worker\nnew (getWorker())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const W = Worker; const getWorker = () => W; new (getWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst W = Worker\nconst getWorker = () => W\nnew (getWorker())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new ((() => Worker)())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nnew ((() => Worker)())('data:text/javascript,postMessage(1)', { type: 'module' })\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via new ((function(){return SharedWorker})())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nnew ((function () { return SharedWorker })())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getWorker = () => condition ? Worker : Worker; new (getWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst getWorker = () => condition ? Worker : Worker\nnew (getWorker())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getWorker = () => condition ? Worker : unknownCtor; new (getWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst unknownCtor = Date\nconst getWorker = () => condition ? Worker : unknownCtor\nnew (getWorker())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getWorker = () => condition ? Worker : unknownCtor; new (getWorker())('/runtime/style-profit-worker.js')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst unknownCtor = Date\nconst getWorker = () => condition ? Worker : unknownCtor\nnew (getWorker())('/runtime/style-profit-worker.js', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getWorker = () => unknownCtor; new (getWorker())('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = Date\nconst getWorker = () => unknownCtor\nnew (getWorker())('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via function getWorker(){if(ready)return Worker;return Worker}; new (getWorker())('/runtime/style-profit-worker.js')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ready = true\nfunction getWorker() {\n  if (ready) return Worker\n  return Worker\n}\nnew (getWorker())('/runtime/style-profit-worker.js', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via function getWorker(){if(ready)return Worker;return Worker}; new (getWorker())('./readonly-worker.ts')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst ready = true\nfunction getWorker() {\n  if (ready) return Worker\n  return Worker\n}\nnew (getWorker())('./readonly-worker.ts', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const getWorker = () => Worker; Reflect.construct(getWorker(), ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getWorker = () => Worker\nReflect.construct(getWorker(), ['data:text/javascript,postMessage(1)', { type: 'module' }])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct((() => Worker)(), ['data:...'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nReflect.construct((() => Worker)(), ['data:text/javascript,postMessage(1)'])\n</script>\n`)
    },
  },
  {
    name: "runtime dynamic module loading via new unknownCtor('data:...')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nnew unknownCtor('data:text/javascript,postMessage(1)')\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new unknownCtor('/runtime/style-profit-worker.js')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nnew unknownCtor('/runtime/style-profit-worker.js', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new unknownCtor('./readonly-worker.ts')",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nnew unknownCtor('./readonly-worker.ts', { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(workerUrl) unresolved workerUrl',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst workerUrl = getWorkerUrl()\nnew unknownCtor(workerUrl)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new unknownCtor(`/runtime/${name}.js`) template worker path",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst name = 'style-profit-worker'\nnew unknownCtor(\`/runtime/\${name}.js\`, { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(getWorkerUrl()) unresolved return url',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nnew unknownCtor(getWorkerUrl(), { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(blobWorkerUrl) blob url marker variable',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst blobWorkerUrl = URL.createObjectURL(new Blob(['postMessage(1)'], { type: 'text/javascript' }))\nnew unknownCtor(blobWorkerUrl, { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(unknownCtor, ['/runtime/style-profit-worker.js'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nReflect.construct(unknownCtor, ['/runtime/style-profit-worker.js', { type: 'module' }])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(getWorker(), ['/runtime/style-profit-worker.js'])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nfunction getWorker() {\n  if (Math.random() > -1) return Worker\n  return Worker\n}\nReflect.construct(getWorker(), ['/runtime/style-profit-worker.js', { type: 'module' }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via Reflect.construct(unknownCtor, [workerUrl]) unresolved workerUrl',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst workerUrl = getWorkerUrl()\nReflect.construct(unknownCtor, [workerUrl])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(unknownCtor, [new URL('./readonly-worker.ts', import.meta.url)])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nReflect.construct(unknownCtor, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(unknownCtor, ['/runtime/style-profit-worker.js'], SafeCtor)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nclass SafeCtor {}\nReflect.construct(unknownCtor, ['/runtime/style-profit-worker.js'], SafeCtor)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const args=['/runtime/style-profit-worker.js', {type:'module'}]; new unknownCtor(...args)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = ['/runtime/style-profit-worker.js', { type: 'module' }]\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const args=['./readonly-worker.ts', {type:'module'}]; new unknownCtor(...args)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = ['./readonly-worker.ts', { type: 'module' }]\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via const args=[workerUrl, {type}] ; new unknownCtor(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst workerUrl = getWorkerUrl()\nconst args = [workerUrl, { type: 'module' }]\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via const args=[blobWorkerUrl, {type}] ; new unknownCtor(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst blobWorkerUrl = URL.createObjectURL(new Blob(['postMessage(1)'], { type: 'text/javascript' }))\nconst args = [blobWorkerUrl, { type: 'module' }]\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via const args=[new URL('./readonly-worker.ts', import.meta.url), {type}] ; new unknownCtor(...args)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new unknownCtor(...['/runtime/style-profit-worker.js', { type: 'module' }])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nnew unknownCtor(...['/runtime/style-profit-worker.js', { type: 'module' }])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new unknownCtor('/runtime/style-profit-worker.js', ...rest)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst rest = [{ type: 'module' }]\nnew unknownCtor('/runtime/style-profit-worker.js', ...rest)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(...args, { type: module }) unresolved args',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = getArgs()\nnew unknownCtor(...args, { type: 'module' })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(...getArgs())',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nnew unknownCtor(...getArgs())\n</script>\n`)
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(...(condition ? safeArgs : unsafeArgs))',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst condition = true\nconst safeArgs = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nconst unsafeArgs = ['/runtime/style-profit-worker.js', { type: 'module' }]\nnew unknownCtor(...(condition ? safeArgs : unsafeArgs))\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(...[...args])',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = ['/runtime/style-profit-worker.js', { type: 'module' }]\nnew unknownCtor(...[...args])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via new (getWorker())(...['/runtime/style-profit-worker.js', { type: 'module' }])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getWorker = () => Worker\nnew (getWorker())(...['/runtime/style-profit-worker.js', { type: 'module' }])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via Reflect.construct(unknownCtor, [...args]) unresolved args',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = getArgs()\nReflect.construct(unknownCtor, [...args])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(unknownCtor, [['/runtime/style-profit-worker.js'][0]])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nReflect.construct(unknownCtor, [['/runtime/style-profit-worker.js'][0]])\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via Reflect.construct(getWorker(), [...['/runtime/style-profit-worker.js', { type: 'module' }]])",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst getWorker = () => Worker\nReflect.construct(getWorker(), [...['/runtime/style-profit-worker.js', { type: 'module' }]])\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args[0] mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via args['0'] mutation then new Worker(...args)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs['0'] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via alias[0] mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nconst alias = args\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via alias.splice mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nconst alias = args\nalias.splice(0, 1, 'data:text/javascript,postMessage(1)')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args.splice mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs.splice(0, 1, 'data:text/javascript,postMessage(1)')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args.unshift mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs.unshift('data:text/javascript,postMessage(1)')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args.push mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs.push('extra')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args.reverse mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs.reverse()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args.fill mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs.fill('data:text/javascript,postMessage(1)')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via mutate(args) escape then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nmutate(args)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via store.args escape then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nconst store = {}\nstore.args = args\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via Array.prototype.splice.call(args) then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nArray.prototype.splice.call(args, 0, 1, 'data:text/javascript,postMessage(1)')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args[methodName](...) then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst methodName = getMethod()\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs[methodName]('data:text/javascript,postMessage(1)')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args[0] mutation then Reflect.construct(Worker, args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs[0] = 'data:text/javascript,postMessage(1)'\nReflect.construct(Worker, args)\n</script>\n`,
      )
    },
  },
  {
    name: "runtime dynamic module loading via alias mutation then new unknownCtor(...args)",
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = ['./readonly-worker.ts', { type: 'module' }]\nconst alias = args\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via args re-assigned from getArgs then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nlet args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nargs = getArgs()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via new unknownCtor(...[]) should fail closed',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nnew unknownCtor(...[])\n</script>\n`)
    },
  },
  {
    name: 'runtime dynamic module loading via hoisted poison() mutates args before new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\npoison()\nnew Worker(...args)\nfunction poison() {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via hoisted poison() splice mutates args before new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\npoison()\nnew Worker(...args)\nfunction poison() {\n  args.splice(0, 1, 'data:text/javascript,postMessage(1)')\n}\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via hoisted poison() alias mutation before new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\npoison()\nnew Worker(...args)\nfunction poison() {\n  const alias = args\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via arrow poison() mutates args before new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nconst poison = () => {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\npoison()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function expression poison() mutates args before new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nconst poison = function () {\n  args.unshift('data:text/javascript,postMessage(1)')\n}\npoison()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function alias run() then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nfunction poison() {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\nconst run = poison\nrun()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via poison.call(null) then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nfunction poison() {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\npoison.call(null)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via poison.apply(null) then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nfunction poison() {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\npoison.apply(null)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via bound poison() then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nfunction poison() {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\nconst bound = poison.bind(null)\nbound()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via closure-return poison() then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nconst poison = (() => () => {\n  args[0] = 'data:text/javascript,postMessage(1)'\n})()\npoison()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via IIFE mutates args then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\n(() => {\n  args[0] = 'data:text/javascript,postMessage(1)'\n})()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via maybePoison() unknown no-arg call then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nmaybePoison()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via unknown(args) escape then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nunknown(args)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via hoisted poison() then Reflect.construct(Worker, args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\npoison()\nReflect.construct(Worker, args)\nfunction poison() {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via hoisted poison() then new unknownCtor(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\npoison()\nnew unknownCtor(...args)\nfunction poison() {\n  args[0] = '/runtime/style-profit-worker.js'\n}\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function array container fns[0]() then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]\nfunction poison() {\n  args[0] = 'data:text/javascript,postMessage(1)'\n}\nconst fns = [poison]\nfns[0]()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via const [alias] = [args] then alias[0] mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst [alias] = [args]\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via const [[alias]] = [[args]] then alias[0] mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst [[alias]] = [[args]]\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via assignment-array destructure [alias] = [args] then alias[0] mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nlet alias\n[alias] = [args]\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via object destructure { value: alias } then alias[0] mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst { value: alias } = { value: args }\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via nested object destructure then alias[0] mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst { nested: { value: alias } } = { nested: { value: args } }\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via assignment-object destructure then alias[0] mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nlet alias\n({ value: alias } = { value: args })\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via destructure alias.splice mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst [alias] = [args]\nalias.splice(0, 1, 'data:text/javascript,postMessage(1)')\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via mutate(alias) after destructure alias then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst [alias] = [args]\nmutate(alias)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via hoisted poison() with destructure alias mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\npoison()\nnew Worker(...args)\nfunction poison() {\n  const [alias] = [args]\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via arrow poison() with destructure alias mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst poison = () => {\n  const [alias] = [args]\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\npoison()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function poison() object-destructure alias mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfunction poison() {\n  const { value: alias } = { value: args }\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\npoison()\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via rest destructure alias then aliases[0][0] mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst [...aliases] = [args]\naliases[0][0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via default destructure alias then alias[0] mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst [alias = args] = []\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via computed object destructure alias then alias[0] mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst key = getKey()\nconst holder = { value: args }\nconst { [key]: alias } = holder\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via destructure alias mutation then Reflect.construct(Worker, args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst [alias] = [args]\nalias[0] = 'data:text/javascript,postMessage(1)'\nReflect.construct(Worker, args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via destructure alias mutation then new unknownCtor(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = ['./readonly-worker.ts']\nconst [alias] = [args]\nalias[0] = 'data:text/javascript,postMessage(1)'\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via for...of alias mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfor (const alias of [args]) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via for...of nested array destructure alias mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfor (const [alias] of [[args]]) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via for...of object destructure alias mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfor (const { value: alias } of [{ value: args }]) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via for...of unresolved iterable should fail closed',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst iterable = getIterable()\nfor (const alias of iterable) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function parameter array destructure mutation then new Worker(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfunction poison([alias]) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\npoison([args])\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via tuple arg function parameter destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst tuple = [args]\nfunction poison([alias]) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\npoison(tuple)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function parameter object destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfunction poison({ value: alias }) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\npoison({ value: args })\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via arrow function parameter destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst poison = ([alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\npoison([args])\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via function expression parameter destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst poison = function ([alias]) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\npoison([args])\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via forEach callback parameter destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].forEach(([alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via forEach callback object parameter destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[{ value: args }].forEach(({ value: alias }) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via unresolved collection callback destructure should fail closed',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst collection = getCollection()\ncollection.forEach(([alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via for...of alias mutation then Reflect.construct(Worker, args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfor (const alias of [args]) {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n}\nReflect.construct(Worker, args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via parameter destructure mutation then new unknownCtor(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nfunction poison([alias]) {\n  alias[0] = '/runtime/style-profit-worker.js'\n}\npoison([args])\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via findIndex callback destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].findIndex(([alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return false\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via findLast callback destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].findLast(([alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return false\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via findLastIndex callback destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].findLastIndex(([alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return false\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via flatMap callback destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].flatMap(([alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return []\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via reduce callback second parameter destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].reduce((acc, [alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return acc\n}, 0)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via reduceRight callback second parameter destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].reduceRight((acc, [alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return acc\n}, 0)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via reduce callback second parameter object destructure mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[{ value: args }].reduce((acc, { value: alias }) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return acc\n}, 0)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via unresolved collection reduce callback destructure should fail closed',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\nconst collection = getCollection()\ncollection.reduce((acc, [alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return acc\n}, 0)\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via flatMap callback splice mutation',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].flatMap(([alias]) => {\n  alias.splice(0, 1, 'data:text/javascript,postMessage(1)')\n  return []\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via findIndex callback escape alias should fail closed',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].findIndex(([alias]) => {\n  escape(alias)\n  return false\n})\nnew Worker(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via reduce callback mutation then new unknownCtor(...args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst unknownCtor = getCtor()\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].reduce((acc, [alias]) => {\n  alias[0] = '/runtime/style-profit-worker.js'\n  return acc\n}, 0)\nnew unknownCtor(...args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime dynamic module loading via reduce callback mutation then Reflect.construct(Worker, args)',
    expectedKeyword: 'style-profit forbids dynamic module loading entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst args = [new URL('./readonly-worker.ts', import.meta.url)]\n[[args]].reduce((acc, [alias]) => {\n  alias[0] = 'data:text/javascript,postMessage(1)'\n  return acc\n}, 0)\nReflect.construct(Worker, args)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via (() => {}).constructor(...)',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;(() => {}).constructor('return Object.assign')()(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via []['filter']['constructor'](...)",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;[]['filter']['constructor']('return Reflect.set')()(item, 'onClick', openHelp)\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen via ({}).constructor.constructor(...)',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;({}).constructor.constructor('return Object.defineProperty')()(item, 'onClick', { value: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: "runtime codegen via ({})['constructor']['constructor'](...)",
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst item = { label: '利润计算说明' }\n;({})['constructor']['constructor']('return Object.assign')()(item, { onClick: openHelp })\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen source const Ctor = (() => {}).constructor',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst Ctor = (() => {}).constructor\n</script>\n`)
    },
  },
  {
    name: 'runtime codegen source container const holder = { make: ({}).constructor.constructor }',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst holder = { make: ({}).constructor.constructor }\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen source array const holder = [Function.prototype.constructor]',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(root, 'src/App.vue', `${content}\n<script setup lang=\"ts\">\nconst holder = [Function.prototype.constructor]\n</script>\n`)
    },
  },
  {
    name: 'runtime codegen source conditional constructor vs Function',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nconst condition = true\nconst make = condition ? ({}).constructor.constructor : Function\n</script>\n`,
      )
    },
  },
  {
    name: 'runtime codegen source Object.freeze constructor container',
    expectedKeyword: 'style-profit forbids runtime code generation entry points',
    mutate: (root) => {
      const content = read(root, 'src/App.vue')
      write(
        root,
        'src/App.vue',
        `${content}\n<script setup lang=\"ts\">\nObject.freeze({ make: ({}).constructor.constructor })\n</script>\n`,
      )
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
