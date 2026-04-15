import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const checkScriptPath = path.resolve(__dirname, 'check-factory-statement-contracts.mjs')

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
    'src/api/factory_statement.ts',
    `import { request, type ApiResponse } from '@/api/request'

export interface FactoryStatementCreatePayload {
  company: string
  supplier: string
  from_date: string
  to_date: string
  idempotency_key: string
}

export interface FactoryStatementListItem {
  payable_outbox_id: number | null
  payable_outbox_status: string | null
  purchase_invoice_name: string | null
  payable_error_code: string | null
  payable_error_message: string | null
}

export interface FactoryStatementDetailData {
  payable_outbox_id: number | null
  payable_outbox_status: string | null
  purchase_invoice_name: string | null
  payable_error_code: string | null
  payable_error_message: string | null
}

export const fetchFactoryStatements = async (): Promise<ApiResponse<{ items: FactoryStatementListItem[] }>> =>
  request('/api/factory-statements/')
export const fetchFactoryStatementDetail = async (statementId: number): Promise<ApiResponse<FactoryStatementDetailData>> =>
  request('/api/factory-statements/' + statementId)
export const createFactoryStatement = async (payload: FactoryStatementCreatePayload): Promise<ApiResponse<{ id: number }>> =>
  request('/api/factory-statements/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
export const confirmFactoryStatement = async (statementId: number, payload: unknown): Promise<ApiResponse<{ id: number }>> =>
  request('/api/factory-statements/' + statementId + '/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
export const cancelFactoryStatement = async (statementId: number, payload: unknown): Promise<ApiResponse<{ id: number }>> =>
  request('/api/factory-statements/' + statementId + '/cancel', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
export const createFactoryStatementPayableDraft = async (statementId: number, payload: unknown): Promise<ApiResponse<{ id: number }>> =>
  request('/api/factory-statements/' + statementId + '/payable-draft', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
`,
  )

  write(
    root,
    'src/views/factory_statement/FactoryStatementList.vue',
    `<template>
  <div>
    <el-form-item label="公司">
      <el-input v-model="createForm.company" />
    </el-form-item>
    <el-button>生成对账单草稿</el-button>
  </div>
</template>
<script setup lang="ts">
const createForm = {
  company: '',
}
const submitCreate = () => {
  return {
    company: createForm.company.trim(),
  }
}
</script>
`,
  )

  write(
    root,
    'src/views/factory_statement/FactoryStatementDetail.vue',
    `<template>
  <div>
    <div v-if="summaryMissing">摘要缺失</div>
    <el-button>确认对账单</el-button>
    <el-button>取消对账单</el-button>
    <el-button>生成应付草稿</el-button>
    <el-button @click="openPrint">打印</el-button>
    <el-button @click="exportCsv">导出明细 CSV</el-button>
  </div>
</template>
<script setup lang="ts">
import { exportFactoryStatementDetailCsv } from '@/utils/factoryStatementExport'
const ACTIVE_PAYABLE_OUTBOX_STATUS = new Set(['pending', 'processing', 'succeeded'])
const hasPayableSummary = { value: true }
const summaryMissing = false
const effectiveOutboxStatus = () => {
  if (!hasPayableSummary.value) {
    return '__unknown__'
  }
  return ''
}
const hasActivePayableOutbox = () => !hasPayableSummary.value || ACTIVE_PAYABLE_OUTBOX_STATUS.has(effectiveOutboxStatus())
const openPrint = () => '/factory-statements/print'
const exportCsv = () => exportFactoryStatementDetailCsv({} as never)
</script>
`,
  )

  write(
    root,
    'src/views/factory_statement/FactoryStatementPrint.vue',
    `<template>
  <div>
    <h1>领意服装管理系统</h1>
    <el-button @click="printNow">打印</el-button>
  </div>
</template>
<script setup lang="ts">
import { onMounted } from 'vue'
import { fetchFactoryStatementDetail } from '@/api/factory_statement'

const printNow = () => {
  window.print()
}

onMounted(async () => {
  await fetchFactoryStatementDetail(1)
})
</script>
`,
  )

  write(
    root,
    'src/utils/factoryStatementExport.ts',
    `import type { FactoryStatementDetailData } from '@/api/factory_statement'

const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/

const toText = (value: unknown): string => {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value)
}

const neutralizeCsvFormula = (value: string): string => {
  if (FORMULA_INJECTION_PREFIX.test(value)) {
    return '\\'' + value
  }
  return value
}

const escapeCsvCell = (value: unknown): string => {
  const text = neutralizeCsvFormula(toText(value))
  if (text.includes('"')) {
    return '"' + text.replace(/"/g, '""') + '"'
  }
  if (text.includes(',') || text.includes('\\n') || text.includes('\\r')) {
    return '"' + text + '"'
  }
  return text
}

export const exportFactoryStatementDetailCsv = (detail: FactoryStatementDetailData): string => {
  return escapeCsvCell(detail.statement_no || 'file.csv')
}
`,
  )

  write(
    root,
    'src/router/index.ts',
    `export default [
  { path: '/factory-statements/list' },
  { path: '/factory-statements/detail' },
  { path: '/factory-statements/print' },
]
`,
  )

  write(
    root,
    'src/stores/permission.ts',
    `const INTERNAL_NON_UI_ACTIONS = new Set<string>([
  'factory_statement:payable_draft_worker',
])

interface ButtonPermissions {
  factory_statement_read: boolean
  factory_statement_create: boolean
  factory_statement_confirm: boolean
  factory_statement_cancel: boolean
  factory_statement_payable_draft_create: boolean
  factory_statement_payable_draft_worker: boolean
}

const forceClearInternalButtonPermissions = () => ({
  factory_statement_read: false,
  factory_statement_create: false,
  factory_statement_confirm: false,
  factory_statement_cancel: false,
  factory_statement_payable_draft_create: false,
  factory_statement_payable_draft_worker: false,
})

export { INTERNAL_NON_UI_ACTIONS, forceClearInternalButtonPermissions }
`,
  )

  write(
    root,
    'src/App.vue',
    `<template>
  <router-view />
</template>
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
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'factory-statement-contracts-fixture-'))
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
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'factory-statement-contracts-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    const result = runCheck(fixtureRoot)
    assertTrue(result.status === 0, `合法 fixture 预期通过，实际失败:\n${result.output}`)
    assertTrue(result.output.includes('Factory statement contract check passed.'), '合法 fixture 未输出通过标识')
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
      const content = read(root, 'src/api/factory_statement.ts')
      write(root, 'src/api/factory_statement.ts', `${content}\nconst invalidProbe = fetch('/forbidden')\n`)
    },
  },
  {
    name: 'api contains /api/resource',
    expectedKeyword: '禁止 ERPNext /api/resource 直连',
    mutate: (root) => {
      const content = read(root, 'src/api/factory_statement.ts')
      write(root, 'src/api/factory_statement.ts', `${content}\nconst direct = '/api/resource/Purchase Invoice'\n`)
    },
  },
  {
    name: 'view calls internal run-once endpoint',
    expectedKeyword: '禁止前端调用加工厂对账单 internal 接口',
    mutate: (root) => {
      const content = read(root, 'src/views/factory_statement/FactoryStatementDetail.vue')
      write(
        root,
        'src/views/factory_statement/FactoryStatementDetail.vue',
        `${content}\n<script setup lang="ts">const bad = '/api/factory-statements/internal/payable-draft-sync/run-once'</script>\n`,
      )
    },
  },
  {
    name: 'view contains run-once button text',
    expectedKeyword: '禁止在前端页面或路由暴露 run-once 动作',
    expectedAbsentKeywords: ['禁止前端调用加工厂对账单 internal 接口'],
    mutate: (root) => {
      const content = read(root, 'src/views/factory_statement/FactoryStatementDetail.vue')
      write(root, 'src/views/factory_statement/FactoryStatementDetail.vue', `${content}\n<!-- run-once -->\n`)
    },
  },
  {
    name: 'print view calls /api/resource',
    expectedKeyword: '禁止 ERPNext /api/resource 直连',
    mutate: (root) => {
      const content = read(root, 'src/views/factory_statement/FactoryStatementPrint.vue')
      write(root, 'src/views/factory_statement/FactoryStatementPrint.vue', `${content}\nconst bad = '/api/resource/Purchase Invoice'\n`)
    },
  },
  {
    name: 'print view calls internal run-once',
    expectedKeyword: '禁止前端调用加工厂对账单 internal 接口',
    mutate: (root) => {
      const content = read(root, 'src/views/factory_statement/FactoryStatementPrint.vue')
      write(root, 'src/views/factory_statement/FactoryStatementPrint.vue', `${content}\nconst bad = '/api/factory-statements/internal/payable-draft-sync/run-once'\n`)
    },
  },
  {
    name: 'print view contains submit Purchase Invoice action',
    expectedKeyword: '禁止出现 submitPurchaseInvoice 调用',
    mutate: (root) => {
      const content = read(root, 'src/views/factory_statement/FactoryStatementPrint.vue')
      write(root, 'src/views/factory_statement/FactoryStatementPrint.vue', `${content}\nsubmitPurchaseInvoice()\n`)
    },
  },
  {
    name: 'print view contains Payment Entry keyword',
    expectedKeyword: '禁止出现 Payment Entry 创建入口',
    mutate: (root) => {
      const content = read(root, 'src/views/factory_statement/FactoryStatementPrint.vue')
      write(root, 'src/views/factory_statement/FactoryStatementPrint.vue', `${content}\n<!-- Payment Entry -->\n`)
    },
  },
  {
    name: 'export util contains bare fetch',
    expectedKeyword: '禁止裸 fetch()',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      write(root, 'src/utils/factoryStatementExport.ts', `${content}\nconst bad = fetch('/forbidden')\n`)
    },
  },
  {
    name: 'export util parseFloat net_amount',
    expectedKeyword: '导出工具禁止 Number/parseFloat 对金额字段重算',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      write(root, 'src/utils/factoryStatementExport.ts', `${content}\nconst bad = parseFloat('net_amount')\n`)
    },
  },
  {
    name: 'export util formula prefix missing equals',
    expectedKeyword: 'CSV 公式注入前缀缺少 = 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      const replaced = replaceOrThrow(
        content,
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/',
        'const FORMULA_INJECTION_PREFIX = /^[+\\-@\\t\\r\\n]/',
        'formula prefix missing equals',
      )
      write(root, 'src/utils/factoryStatementExport.ts', replaced)
    },
  },
  {
    name: 'export util formula prefix missing plus',
    expectedKeyword: 'CSV 公式注入前缀缺少 + 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      const replaced = replaceOrThrow(
        content,
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/',
        'const FORMULA_INJECTION_PREFIX = /^[=\\-@\\t\\r\\n]/',
        'formula prefix missing plus',
      )
      write(root, 'src/utils/factoryStatementExport.ts', replaced)
    },
  },
  {
    name: 'export util formula prefix missing minus',
    expectedKeyword: 'CSV 公式注入前缀缺少 - 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      const replaced = replaceOrThrow(
        content,
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/',
        'const FORMULA_INJECTION_PREFIX = /^[=+@\\t\\r\\n]/',
        'formula prefix missing minus',
      )
      write(root, 'src/utils/factoryStatementExport.ts', replaced)
    },
  },
  {
    name: 'export util formula prefix missing at',
    expectedKeyword: 'CSV 公式注入前缀缺少 @ 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      const replaced = replaceOrThrow(
        content,
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/',
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-\\t\\r\\n]/',
        'formula prefix missing at',
      )
      write(root, 'src/utils/factoryStatementExport.ts', replaced)
    },
  },
  {
    name: 'export util formula prefix missing tab',
    expectedKeyword: 'CSV 公式注入前缀缺少 tab 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      const replaced = replaceOrThrow(
        content,
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/',
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\r\\n]/',
        'formula prefix missing tab',
      )
      write(root, 'src/utils/factoryStatementExport.ts', replaced)
    },
  },
  {
    name: 'export util formula prefix missing cr',
    expectedKeyword: 'CSV 公式注入前缀缺少 CR 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      const replaced = replaceOrThrow(
        content,
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/',
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\n]/',
        'formula prefix missing cr',
      )
      write(root, 'src/utils/factoryStatementExport.ts', replaced)
    },
  },
  {
    name: 'export util formula prefix missing lf',
    expectedKeyword: 'CSV 公式注入前缀缺少 LF 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/factoryStatementExport.ts')
      const replaced = replaceOrThrow(
        content,
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/',
        'const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r]/',
        'formula prefix missing lf',
      )
      write(root, 'src/utils/factoryStatementExport.ts', replaced)
    },
  },
  {
    name: 'ui contains internal worker permission action',
    expectedKeyword: '禁止在 UI 视图/路由中出现 factory_statement:payable_draft_worker',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\nconst internal = 'factory_statement:payable_draft_worker'\n`)
    },
  },
  {
    name: 'permission store misses internal worker clear',
    expectedKeyword: 'permission store 缺少权限字段默认值: factory_statement_payable_draft_worker: false',
    mutate: (root) => {
      const content = read(root, 'src/stores/permission.ts')
      const replaced = replaceOrThrow(
        content,
        "  factory_statement_payable_draft_worker: false,\n",
        '',
        'factory_statement_payable_draft_worker clear',
      )
      write(root, 'src/stores/permission.ts', replaced)
    },
  },
  {
    name: 'create payload company is optional',
    expectedKeyword: 'FactoryStatementCreatePayload 禁止 company? 可选字段',
    mutate: (root) => {
      const content = read(root, 'src/api/factory_statement.ts')
      const replaced = replaceOrThrow(content, '  company: string\n', '  company?: string\n', 'payload company optional')
      write(root, 'src/api/factory_statement.ts', replaced)
    },
  },
  {
    name: 'create payload missing company',
    expectedKeyword: 'FactoryStatementCreatePayload.company 必须为必填 string',
    mutate: (root) => {
      const content = read(root, 'src/api/factory_statement.ts')
      const replaced = replaceOrThrow(content, '  company: string\n', '', 'payload company required')
      write(root, 'src/api/factory_statement.ts', replaced)
    },
  },
  {
    name: 'create dialog missing company field',
    expectedKeyword: 'FactoryStatementList.vue 创建表单缺少 company 字段',
    mutate: (root) => {
      const content = read(root, 'src/views/factory_statement/FactoryStatementList.vue')
      const replaced = replaceOrThrow(content, '<el-form-item label="公司">\n      <el-input v-model="createForm.company" />\n    </el-form-item>\n', '', 'list company form item')
      write(root, 'src/views/factory_statement/FactoryStatementList.vue', replaced)
    },
  },
  {
    name: 'detail type missing payable_outbox_status',
    expectedKeyword: 'src/api/factory_statement.ts 缺少 payable 摘要字段契约: payable_outbox_status: string | null',
    mutate: (root) => {
      const content = read(root, 'src/api/factory_statement.ts')
      const replaced = content.split('  payable_outbox_status: string | null\n').join('')
      if (replaced === content) {
        throw new Error('替换失败：detail missing outbox status 未找到目标片段')
      }
      write(root, 'src/api/factory_statement.ts', replaced)
    },
  },
  {
    name: 'detail type missing purchase_invoice_name',
    expectedKeyword: 'src/api/factory_statement.ts 缺少 payable 摘要字段契约: purchase_invoice_name: string | null',
    mutate: (root) => {
      const content = read(root, 'src/api/factory_statement.ts')
      const replaced = content.split('  purchase_invoice_name: string | null\n').join('')
      if (replaced === content) {
        throw new Error('替换失败：detail missing purchase invoice name 未找到目标片段')
      }
      write(root, 'src/api/factory_statement.ts', replaced)
    },
  },
  {
    name: 'detail page missing summary fail-closed guard',
    expectedKeyword: 'FactoryStatementDetail.vue 缺少 fail-closed 片段: const hasPayableSummary',
    mutate: (root) => {
      write(
        root,
        'src/views/factory_statement/FactoryStatementDetail.vue',
        `<template><div>detail</div></template>\n<script setup lang="ts"></script>\n`,
      )
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

  console.log(`All factory statement contract fixture tests passed. scenarios=${passedCount}`)
} catch (error) {
  const message = error instanceof Error ? error.message : String(error)
  console.error(`Factory statement contract fixture tests failed: ${message}`)
  process.exit(1)
}
