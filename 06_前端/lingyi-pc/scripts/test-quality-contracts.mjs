import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { checkQualityContracts } from './check-quality-contracts.mjs'

const ensureDir = (targetPath) => mkdirSync(targetPath, { recursive: true })

const write = (root, relativePath, content) => {
  const full = path.join(root, relativePath)
  ensureDir(path.dirname(full))
  writeFileSync(full, content, 'utf8')
}

const read = (root, relativePath) => readFileSync(path.join(root, relativePath), 'utf8')

const assertTrue = (condition, message) => {
  if (!condition) {
    throw new Error(message)
  }
}

const createBaseFixture = (root) => {
  write(
    root,
    'src/api/quality.ts',
    `import { request } from '@/api/request'

export const fetchQualityInspections = async () => request('/api/quality/inspections')
export const fetchQualityInspectionDetail = async (id: number) => request('/api/quality/inspections/' + id)
export const createQualityInspection = async (payload: unknown) => request('/api/quality/inspections', { method: 'POST', body: JSON.stringify(payload) })
export const updateQualityInspection = async (id: number, payload: unknown) => request('/api/quality/inspections/' + id, { method: 'PATCH', body: JSON.stringify(payload) })
export const confirmQualityInspection = async (id: number) => request('/api/quality/inspections/' + id + '/confirm', { method: 'POST' })
export const cancelQualityInspection = async (id: number) => request('/api/quality/inspections/' + id + '/cancel', { method: 'POST' })
export const fetchQualityStatistics = async () => request('/api/quality/statistics')
export const exportQualityInspections = async () => request('/api/quality/export')
`,
  )

  write(
    root,
    'src/views/quality/QualityInspectionList.vue',
    `<template>
  <el-button v-if="canCreate" :disabled="!canCreate" @click="submitCreate">创建检验单</el-button>
  <el-button v-if="canExport" @click="submitExport">导出快照</el-button>
</template>
<script setup lang="ts">
import { createQualityInspection, exportQualityInspections, fetchQualityInspections } from '@/api/quality'
const canRead = true
const canCreate = true
const canExport = true
const loadRows = () => canRead && fetchQualityInspections()
const submitCreate = () => canCreate && createQualityInspection({ company: 'COMP-A' })
const submitExport = () => canExport && exportQualityInspections()
</script>
`,
  )

  write(
    root,
    'src/views/quality/QualityInspectionDetail.vue',
    `<template>
  <el-button v-if="canUpdate" :disabled="!canUpdate" @click="submitUpdate">更新检验结果</el-button>
  <el-button v-if="canConfirm" :disabled="!canConfirm" @click="submitConfirm">确认检验单</el-button>
  <el-button v-if="canCancel" :disabled="!canCancel" @click="submitCancel">取消检验单</el-button>
</template>
<script setup lang="ts">
import { cancelQualityInspection, confirmQualityInspection, fetchQualityInspectionDetail, updateQualityInspection } from '@/api/quality'
const canRead = true
const canUpdate = true
const canConfirm = true
const canCancel = true
const loadDetail = () => canRead && fetchQualityInspectionDetail(1)
const submitUpdate = () => canUpdate && updateQualityInspection(1, {})
const submitConfirm = () => canConfirm && confirmQualityInspection(1)
const submitCancel = () => canCancel && cancelQualityInspection(1)
</script>
`,
  )

  write(
    root,
    'src/router/index.ts',
    `export default [
  { path: '/quality/inspections', meta: { module: 'quality' } },
  { path: '/quality/inspections/detail', meta: { module: 'quality' } },
]
`,
  )

  write(
    root,
    'src/stores/permission.ts',
    `interface ButtonPermissions {
  quality_read: boolean
  quality_create: boolean
  quality_update: boolean
  quality_confirm: boolean
  quality_cancel: boolean
  quality_export: boolean
  quality_diagnostic: boolean
}
const emptyButtonPermissions = (): ButtonPermissions => ({
  quality_read: false,
  quality_create: false,
  quality_update: false,
  quality_confirm: false,
  quality_cancel: false,
  quality_export: false,
  quality_diagnostic: false,
})
const INTERNAL_NON_UI_ACTIONS = new Set<string>(['quality:diagnostic'])
const forceClearInternalButtonPermissions = (buttons: ButtonPermissions): ButtonPermissions => ({
  ...buttons,
  quality_diagnostic: false,
})
export { emptyButtonPermissions, forceClearInternalButtonPermissions, INTERNAL_NON_UI_ACTIONS }
`,
  )

  write(root, 'src/App.vue', '<template><router-view /></template>\n')
}

const runSuccessCase = () => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'quality-contract-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    const result = checkQualityContracts(fixtureRoot)
    assertTrue(result.ok, `合法 fixture 预期通过，实际失败:\n${result.failures.join('\n')}`)
    console.log('PASS: minimal legal quality fixture')
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const runFailureCase = (caseName, mutateFixture, expectedKeyword) => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'quality-contract-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    mutateFixture(fixtureRoot)
    const result = checkQualityContracts(fixtureRoot)
    assertTrue(!result.ok, `[${caseName}] 预期失败，但返回成功`)
    const output = result.failures.join('\n')
    assertTrue(
      output.includes(expectedKeyword),
      `[${caseName}] 失败关键词不匹配，期望包含: ${expectedKeyword}\n实际输出:\n${output}`,
    )
    console.log(`PASS: ${caseName}`)
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const failureCases = [
  {
    name: 'ERPNext direct resource should fail closed',
    expectedKeyword: '禁止 ERPNext /api/resource 直连',
    mutate: (root) => {
      const content = read(root, 'src/api/quality.ts')
      write(root, 'src/api/quality.ts', `${content}\nconst bad = '/api/resource/Stock Entry'\n`)
    },
  },
  {
    name: 'diagnostic API should fail closed',
    expectedKeyword: '禁止暴露 diagnostic 方法或端点',
    mutate: (root) => {
      const content = read(root, 'src/api/quality.ts')
      write(root, 'src/api/quality.ts', `${content}\nexport const fetchQualityDiagnostic = () => request('/api/quality/diagnostic')\n`)
    },
  },
  {
    name: 'diagnostic view should fail closed',
    expectedKeyword: '禁止调用 diagnostic 接口',
    mutate: (root) => {
      const content = read(root, 'src/views/quality/QualityInspectionList.vue')
      write(root, 'src/views/quality/QualityInspectionList.vue', `${content}\nconst bad = '/api/quality/diagnostic'\n`)
    },
  },
  {
    name: 'internal route should fail closed',
    expectedKeyword: '禁止暴露诊断或内部路径',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\nexport const bad = '/quality/internal/run-once'\n`)
    },
  },
  {
    name: 'run-once should fail closed',
    expectedKeyword: '禁止在前端页面或路由暴露 run-once 动作',
    mutate: (root) => {
      const content = read(root, 'src/views/quality/QualityInspectionDetail.vue')
      write(root, 'src/views/quality/QualityInspectionDetail.vue', `${content}\n// run-once\n`)
    },
  },
  {
    name: 'missing create API should fail closed',
    expectedKeyword: 'quality API 缺少方法: createQualityInspection',
    mutate: (root) => {
      const content = read(root, 'src/api/quality.ts')
      write(root, 'src/api/quality.ts', content.replace('createQualityInspection', 'makeQualityInspection'))
    },
  },
  {
    name: 'missing quality route should fail closed',
    expectedKeyword: '路由缺少质量管理路径: /quality/inspections/detail',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', content.replace("  { path: '/quality/inspections/detail', meta: { module: 'quality' } },\n", ''))
    },
  },
  {
    name: 'missing create permission binding should fail closed',
    expectedKeyword: '质量创建按钮必须绑定 quality_create 权限',
    mutate: (root) => {
      const content = read(root, 'src/views/quality/QualityInspectionList.vue')
      write(root, 'src/views/quality/QualityInspectionList.vue', content.replace('v-if="canCreate" :disabled="!canCreate"', ''))
    },
  },
  {
    name: 'missing confirm permission binding should fail closed',
    expectedKeyword: '质量确认按钮必须绑定 canConfirm 权限',
    mutate: (root) => {
      const content = read(root, 'src/views/quality/QualityInspectionDetail.vue')
      write(root, 'src/views/quality/QualityInspectionDetail.vue', content.replace('v-if="canConfirm" :disabled="!canConfirm"', ''))
    },
  },
  {
    name: 'missing diagnostic denylist should fail closed',
    expectedKeyword: '缺少质量 diagnostic denylist',
    mutate: (root) => {
      const content = read(root, 'src/stores/permission.ts')
      write(root, 'src/stores/permission.ts', content.replace("'quality:diagnostic'", "'quality:read'"))
    },
  },
  {
    name: 'missing diagnostic force clear should fail closed',
    expectedKeyword: '强制清零 quality_diagnostic',
    mutate: (root) => {
      const content = read(root, 'src/stores/permission.ts')
      write(root, 'src/stores/permission.ts', content.replace('  quality_diagnostic: false,\n})\nexport {', '})\nexport {'))
    },
  },
  {
    name: 'ERPNext write object wording should fail closed',
    expectedKeyword: '禁止 ERPNext /api/resource 直连',
    mutate: (root) => {
      const content = read(root, 'src/views/quality/QualityInspectionDetail.vue')
      write(root, 'src/views/quality/QualityInspectionDetail.vue', `${content}\nconst bad = '/api/resource/Purchase Invoice'\n`)
    },
  },
  {
    name: 'ERPNext write function should fail closed',
    expectedKeyword: '质量前端禁止暴露 ERPNext 写入函数',
    mutate: (root) => {
      const content = read(root, 'src/views/quality/QualityInspectionDetail.vue')
      write(root, 'src/views/quality/QualityInspectionDetail.vue', `${content}\nconst createGlEntry = () => undefined\n`)
    },
  },
]

runSuccessCase()
for (const item of failureCases) {
  runFailureCase(item.name, item.mutate, item.expectedKeyword)
}

console.log(`Quality contract reverse tests passed. scenarios=${failureCases.length + 1}`)
