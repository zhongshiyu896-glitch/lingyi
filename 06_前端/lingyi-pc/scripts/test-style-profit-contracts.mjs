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
    expectedKeyword: 'style-profit forbids non-literal computed action keys',
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
    expectedKeyword: 'style-profit forbids non-literal computed action keys',
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
    expectedKeyword: 'style-profit forbids non-literal computed action keys',
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
    expectedKeyword: 'style-profit forbids non-literal computed action keys',
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
    expectedKeyword: 'style-profit forbids non-literal computed action keys',
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
    expectedKeyword: 'style-profit forbids non-literal computed action keys',
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
