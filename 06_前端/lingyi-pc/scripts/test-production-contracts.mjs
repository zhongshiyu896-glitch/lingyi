import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const checkScriptPath = path.resolve(__dirname, 'check-production-contracts.mjs')

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
    'src/api/production.ts',
    `export interface ProductionPlanCreatePayload {
  sales_order: string
  planned_qty: number
  planned_start_date?: string | null
  idempotency_key: string
}

export interface ProductionWorkOrderCreatePayload {
  fg_warehouse: string
  wip_warehouse: string
  start_date: string
  idempotency_key: string
}
`,
  )

  write(
    root,
    'src/views/production/ProductionPlanDetail.vue',
    `<template>
  <div>
    <el-descriptions-item label="最近同步时间">{{ detail?.last_synced_at || '-' }}</el-descriptions-item>
  </div>
</template>
`,
  )

  write(
    root,
    'src/views/production/ProductionPlanList.vue',
    `<template>
  <div>production-list</div>
</template>
`,
  )

  write(
    root,
    'src/router/index.ts',
    `export default []
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

export function forceClearInternalButtonPermissions() {
  return {
    work_order_worker: false,
    stock_sync_worker: false,
    job_card_sync_worker: false,
  }
}

export { INTERNAL_ACTION_DENYLIST }
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

const runFailureCase = (caseName, mutateFixture, expectedKeyword, expectedAbsentKeywords = []) => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'production-contracts-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    mutateFixture(fixtureRoot)
    const result = runCheck(fixtureRoot)
    assertTrue(result.status !== 0, `[${caseName}] 预期失败，但返回了成功`)
    assertTrue(
      result.output.includes(expectedKeyword),
      `[${caseName}] 失败关键词不匹配，期望包含: ${expectedKeyword}\n实际输出:\n${result.output}`,
    )
    for (const absentKeyword of expectedAbsentKeywords) {
      assertTrue(
        !result.output.includes(absentKeyword),
        `[${caseName}] 不应命中关键词: ${absentKeyword}\n实际输出:\n${result.output}`,
      )
    }
    console.log(`PASS: ${caseName}`)
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const runSuccessCase = () => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'production-contracts-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    const result = runCheck(fixtureRoot)
    assertTrue(result.status === 0, `合法 fixture 预期通过，实际失败:\n${result.output}`)
    assertTrue(result.output.includes('Production contract check passed.'), '合法 fixture 未输出通过标识')
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
      const content = read(root, 'src/api/production.ts')
      write(root, 'src/api/production.ts', `${content}\nconst invalidProbe = fetch('/forbidden')\n`)
    },
  },
  {
    name: 'view contains /api/resource',
    expectedKeyword: '禁止 ERPNext /api/resource 直连',
    mutate: (root) => {
      const content = read(root, 'src/views/production/ProductionPlanList.vue')
      write(root, 'src/views/production/ProductionPlanList.vue', `${content}\n<!-- /api/resource -->\n`)
    },
  },
  {
    name: 'router contains internal run-once path',
    expectedKeyword: '禁止调用生产计划内部 worker API',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\nconst invalidPath = '/api/production/internal/work-order-sync/run-once'\n`)
    },
  },
  {
    name: 'router contains standalone work-order-sync/run-once path only',
    expectedKeyword: '禁止出现 work-order-sync/run-once 调用路径',
    expectedAbsentKeywords: ['禁止调用生产计划内部 worker API', '禁止裸 fetch()', '禁止 ERPNext /api/resource 直连'],
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\nconst invalidPath = 'work-order-sync/run-once'\n`)
    },
  },
  {
    name: 'store contains unwhitelisted internal action',
    expectedKeyword: '仅允许在白名单文件声明内部动作',
    mutate: (root) => {
      write(root, 'src/stores/ui-shortcuts.ts', `export const hiddenAction = 'production:work_order_worker'\n`)
    },
  },
  {
    name: 'create payload contains company field',
    expectedKeyword: 'ProductionPlanCreatePayload 不得包含 company 字段',
    mutate: (root) => {
      const content = read(root, 'src/api/production.ts')
      const replaced = replaceOrThrow(
        content,
        '  idempotency_key: string\n}',
        '  idempotency_key: string\n  company?: string\n}',
        'ProductionPlanCreatePayload',
      )
      write(root, 'src/api/production.ts', replaced)
    },
  },
  {
    name: 'api missing planned_start_date',
    expectedKeyword: 'src/api/production.ts 缺少 planned_start_date 契约字段',
    mutate: (root) => {
      const content = read(root, 'src/api/production.ts')
      const replaced = replaceOrThrow(content, '  planned_start_date?: string | null\n', '', 'planned_start_date')
      write(root, 'src/api/production.ts', replaced)
    },
  },
  {
    name: 'api missing required work-order field',
    expectedKeyword: 'src/api/production.ts 缺少 Work Order 字段: wip_warehouse',
    mutate: (root) => {
      const content = read(root, 'src/api/production.ts')
      const replaced = replaceOrThrow(content, '  wip_warehouse: string\n', '', 'wip_warehouse')
      write(root, 'src/api/production.ts', replaced)
    },
  },
  {
    name: 'detail view uses latestJobCardSyncedAt',
    expectedKeyword: '详情页仍存在 latestJobCardSyncedAt 逻辑',
    mutate: (root) => {
      const content = read(root, 'src/views/production/ProductionPlanDetail.vue')
      write(root, 'src/views/production/ProductionPlanDetail.vue', `${content}\n{{ latestJobCardSyncedAt }}\n`)
    },
  },
  {
    name: 'router contains sensitive keyword only',
    expectedKeyword: '禁止业务文件出现敏感关键字硬编码',
    expectedAbsentKeywords: ['禁止调用生产计划内部 worker API', '禁止出现 work-order-sync/run-once 调用路径', '禁止 ERPNext /api/resource 直连', '禁止裸 fetch()'],
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\nconst sensitiveHeader = 'Authorization'\n`)
    },
  },
  {
    name: 'permission store misses work_order_worker clear',
    expectedKeyword: 'permission store 缺少内部按钮清零: work_order_worker: false',
    mutate: (root) => {
      const content = read(root, 'src/stores/permission.ts')
      const replaced = replaceOrThrow(content, '    work_order_worker: false,\n', '', 'work_order_worker clear')
      write(root, 'src/stores/permission.ts', replaced)
    },
  },
]

let passedCount = 0

try {
  runSuccessCase()
  passedCount += 1

  for (const failureCase of failureCases) {
    runFailureCase(
      failureCase.name,
      failureCase.mutate,
      failureCase.expectedKeyword,
      failureCase.expectedAbsentKeywords ?? [],
    )
    passedCount += 1
  }

  console.log(`All production contract fixture tests passed. scenarios=${passedCount}`)
} catch (error) {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`Production contract fixture tests failed: ${message}`)
  process.exit(1)
}
