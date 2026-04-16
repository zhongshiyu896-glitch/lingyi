import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { tmpdir } from 'node:os'
import {
  FRONTEND_WRITE_GUARD_COMMON_RULES,
  runFrontendContractEngine,
  validateCsvFormulaGuardContent,
} from './frontend-contract-engine.mjs'

const ensureDir = (targetPath) => {
  mkdirSync(targetPath, { recursive: true })
}

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
    'src/api/sample.ts',
    `import { request } from '@/api/request'

export const fetchReadonlyData = async () => request('/api/demo/readonly')
`,
  )

  write(
    root,
    'src/views/demo/DemoReadonly.vue',
    `<template>
  <div>只读展示</div>
</template>
<script setup lang="ts">
const title = 'readonly'
</script>
`,
  )

  write(
    root,
    'src/router/index.ts',
    `export default [{ path: '/demo/readonly' }]
`,
  )

  write(
    root,
    'src/stores/permission.ts',
    `export const readonly = true
`,
  )

  write(
    root,
    'src/components/DemoBlock.vue',
    `<template><div>component</div></template>
`,
  )

  write(
    root,
    'src/utils/demo.ts',
    `export const safe = () => 'ok'
`,
  )

  write(
    root,
    'src/App.vue',
    `<template><router-view /></template>
`,
  )

  write(
    root,
    'src/utils/exportGuard.ts',
    `const FORMULA_INJECTION_PREFIX = /^[=+\\-@\\t\\r\\n]/

const toText = (value: unknown): string => {
  if (value === null || value === undefined) return ''
  return String(value)
}

const neutralizeCsvFormula = (value: string): string => {
  if (FORMULA_INJECTION_PREFIX.test(value)) {
    return '\\'' + value
  }
  return value
}

export const escapeCsvCell = (value: unknown) => neutralizeCsvFormula(toText(value))
`,
  )
}

const createModuleConfig = () => ({
  module: 'frontend_contract_engine',
  surface: {
    moduleKey: 'frontend_contract_engine',
    scanScopes: ['api', 'views', 'router', 'stores', 'components', 'utils'],
    entryGlobs: ['src/**'],
    extraPaths: ['src/App.vue'],
  },
  fixture: {
    positive: ['fixtures/frontend-contract-engine/positive/minimal-legal.fixture.ts'],
    negative: ['fixtures/frontend-contract-engine/negative/bare-fetch.fixture.ts'],
  },
  allowedApis: ['fetchReadonlyData'],
  forbiddenApis: ['/api/resource', '/internal/'],
  forbiddenActions: ['create', 'update', 'delete', 'confirm', 'cancel', 'generate', 'recalculate', 'sync', 'submit'],
  allowedReadOnlyActions: ['read', 'list', 'detail', 'query'],
  allowedHttpMethods: ['GET'],
  rules: FRONTEND_WRITE_GUARD_COMMON_RULES,
  enforceHttpMethodPolicy: true,
  enforceForbiddenActions: true,
})

const runSuccessCase = () => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'frontend-contract-engine-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    const result = runFrontendContractEngine(fixtureRoot, createModuleConfig())
    assertTrue(result.ok, `合法 fixture 预期通过，实际失败:\n${result.failures.join('\n')}`)
    const csvFailures = validateCsvFormulaGuardContent(read(fixtureRoot, 'src/utils/exportGuard.ts'))
    assertTrue(csvFailures.length === 0, `CSV 公式注入防护合法 fixture 预期通过，实际失败:\n${csvFailures.join('\n')}`)
    console.log('PASS: minimal legal fixture')
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const runFailureCase = (caseName, mutateFixture, expectedKeyword) => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'frontend-contract-engine-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    mutateFixture(fixtureRoot)
    const result = runFrontendContractEngine(fixtureRoot, createModuleConfig())
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

const runCsvFailureCase = (caseName, mutateFixture, expectedKeyword) => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'frontend-contract-engine-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    mutateFixture(fixtureRoot)
    const failures = validateCsvFormulaGuardContent(read(fixtureRoot, 'src/utils/exportGuard.ts'))
    assertTrue(failures.length > 0, `[${caseName}] 预期 CSV 防护失败，但返回成功`)
    assertTrue(
      failures.some((item) => item.includes(expectedKeyword)),
      `[${caseName}] 失败关键词不匹配，期望包含: ${expectedKeyword}\n实际输出:\n${failures.join('\n')}`,
    )
    console.log(`PASS: ${caseName}`)
  } finally {
    rmSync(fixtureRoot, { recursive: true, force: true })
  }
}

const runConfigFailureCase = (caseName, mutateFixture, mutateConfig, expectedKeyword) => {
  const fixtureRoot = mkdtempSync(path.join(tmpdir(), 'frontend-contract-engine-fixture-'))
  try {
    createBaseFixture(fixtureRoot)
    if (typeof mutateFixture === 'function') {
      mutateFixture(fixtureRoot)
    }
    const config = createModuleConfig()
    mutateConfig(config)
    const result = runFrontendContractEngine(fixtureRoot, config)
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
    name: 'bare fetch should fail closed',
    expectedKeyword: '禁止裸 fetch()',
    mutate: (root) => {
      const content = read(root, 'src/api/sample.ts')
      write(root, 'src/api/sample.ts', `${content}\nconst bad = fetch('/forbidden')\n`)
    },
  },
  {
    name: 'bare axios should fail closed',
    expectedKeyword: '禁止裸 axios 调用',
    mutate: (root) => {
      const content = read(root, 'src/api/sample.ts')
      write(root, 'src/api/sample.ts', `${content}\nconst bad = axios.get('/forbidden')\n`)
    },
  },
  {
    name: 'erpnext direct resource should fail closed',
    expectedKeyword: '禁止 ERPNext /api/resource 直连',
    mutate: (root) => {
      const content = read(root, 'src/views/demo/DemoReadonly.vue')
      write(root, 'src/views/demo/DemoReadonly.vue', `${content}\nconst bad = '/api/resource/Sales Order'\n`)
    },
  },
  {
    name: 'internal endpoint should fail closed',
    expectedKeyword: '禁止前端调用 internal 接口',
    mutate: (root) => {
      const content = read(root, 'src/views/demo/DemoReadonly.vue')
      write(root, 'src/views/demo/DemoReadonly.vue', `${content}\nconst bad = '/api/demo/internal/run'\n`)
    },
  },
  {
    name: 'run-once exposure should fail closed',
    expectedKeyword: '禁止在前端页面或路由暴露 run-once 动作',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\n// run-once\n`)
    },
  },
  {
    name: 'diagnostic exposure should fail closed',
    expectedKeyword: '禁止在普通页面暴露 diagnostic 动作',
    mutate: (root) => {
      const content = read(root, 'src/router/index.ts')
      write(root, 'src/router/index.ts', `${content}\nconst bad = 'diagnostic'\n`)
    },
  },
  {
    name: 'eval should fail closed',
    expectedKeyword: '禁止动态代码执行 eval',
    mutate: (root) => {
      const content = read(root, 'src/utils/demo.ts')
      write(root, 'src/utils/demo.ts', `${content}\nconst bad = eval('1+1')\n`)
    },
  },
  {
    name: 'new Function should fail closed',
    expectedKeyword: '禁止动态代码执行 new Function',
    mutate: (root) => {
      const content = read(root, 'src/utils/demo.ts')
      write(root, 'src/utils/demo.ts', `${content}\nconst bad = new Function('return 1')\n`)
    },
  },
  {
    name: 'string timer should fail closed',
    expectedKeyword: '禁止字符串 setTimeout/setInterval 执行代码',
    mutate: (root) => {
      const content = read(root, 'src/utils/demo.ts')
      write(root, 'src/utils/demo.ts', `${content}\nsetTimeout('alert(1)', 100)\n`)
    },
  },
  {
    name: 'dynamic import data url should fail closed',
    expectedKeyword: '禁止 dynamic import 加载高危 URL',
    mutate: (root) => {
      const content = read(root, 'src/utils/demo.ts')
      write(root, 'src/utils/demo.ts', `${content}\nconst bad = import('data:text/javascript,console.log(1)')\n`)
    },
  },
  {
    name: 'worker high-risk url should fail closed',
    expectedKeyword: '禁止 Worker/SharedWorker 使用高危 URL',
    mutate: (root) => {
      const content = read(root, 'src/utils/demo.ts')
      write(root, 'src/utils/demo.ts', `${content}\nconst bad = new Worker('blob:123')\n`)
    },
  },
  {
    name: 'createObjectURL bypass should fail closed',
    expectedKeyword: '禁止 URL.createObjectURL 绕过动态加载门禁',
    mutate: (root) => {
      const content = read(root, 'src/utils/demo.ts')
      write(root, 'src/utils/demo.ts', `${content}\nconst bad = URL.createObjectURL(new Blob(['x']))\n`)
    },
  },
  {
    name: 'unauthorized post should fail closed',
    expectedKeyword: '禁止未授权 POST 写入口',
    mutate: (root) => {
      const content = read(root, 'src/api/sample.ts')
      write(root, 'src/api/sample.ts', `${content}\nconst bad = request('/api/demo', { method: 'POST' })\n`)
    },
  },
  {
    name: 'forbidden action should fail closed',
    expectedKeyword: '禁止出现未授权写动作语义',
    mutate: (root) => {
      const content = read(root, 'src/views/demo/DemoReadonly.vue')
      write(root, 'src/views/demo/DemoReadonly.vue', `${content}\n<template><button>create</button></template>\n`)
    },
  },
]

const csvFailureCases = [
  {
    name: 'csv formula prefix missing plus token should fail',
    expectedKeyword: 'CSV 公式注入前缀缺少 + 覆盖',
    mutate: (root) => {
      const content = read(root, 'src/utils/exportGuard.ts')
      write(root, 'src/utils/exportGuard.ts', content.replace('/^[=+\\-@\\t\\r\\n]/', '/^[=\\-@\\t\\r\\n]/'))
    },
  },
  {
    name: 'csv formula neutralize call missing should fail',
    expectedKeyword: 'escapeCsvCell 必须调用 neutralizeCsvFormula(toText(value))',
    mutate: (root) => {
      const content = read(root, 'src/utils/exportGuard.ts')
      write(root, 'src/utils/exportGuard.ts', content.replace('neutralizeCsvFormula(toText(value))', 'toText(value)'))
    },
  },
]

const configFailureCases = [
  {
    name: 'unknown scan scope should fail closed',
    expectedKeyword: '未知 scan scope: apix',
    mutateFixture: null,
    mutateConfig: (config) => {
      config.surface.scanScopes = ['apix']
    },
  },
  {
    name: 'scan scope typo should fail before scan-zero false green',
    expectedKeyword: '未知 scan scope: apix',
    mutateFixture: (root) => {
      const content = read(root, 'src/api/sample.ts')
      write(root, 'src/api/sample.ts', `${content}\nconst bad = fetch('/forbidden')\n`)
    },
    mutateConfig: (config) => {
      config.surface.scanScopes = ['apix']
    },
  },
  {
    name: 'valid scope but no matched files should fail closed',
    expectedKeyword: '[FWG-SCAN-001]',
    mutateFixture: (root) => {
      rmSync(path.join(root, 'src/api'), { recursive: true, force: true })
    },
    mutateConfig: (config) => {
      config.surface.scanScopes = ['api']
      config.surface.extraPaths = []
    },
  },
  {
    name: 'missing fixture should fail closed',
    expectedKeyword: '模块门禁配置缺少 fixture',
    mutateFixture: null,
    mutateConfig: (config) => {
      delete config.fixture
    },
  },
  {
    name: 'empty fixture positive should fail closed',
    expectedKeyword: '模块门禁配置缺少非空 fixture.positive',
    mutateFixture: null,
    mutateConfig: (config) => {
      config.fixture.positive = []
    },
  },
  {
    name: 'empty fixture negative should fail closed',
    expectedKeyword: '模块门禁配置缺少非空 fixture.negative',
    mutateFixture: null,
    mutateConfig: (config) => {
      config.fixture.negative = []
    },
  },
]

let passedCount = 0
runSuccessCase()
passedCount += 1

for (const failureCase of failureCases) {
  runFailureCase(failureCase.name, failureCase.mutate, failureCase.expectedKeyword)
  passedCount += 1
}

for (const failureCase of csvFailureCases) {
  runCsvFailureCase(failureCase.name, failureCase.mutate, failureCase.expectedKeyword)
  passedCount += 1
}

for (const failureCase of configFailureCases) {
  runConfigFailureCase(
    failureCase.name,
    failureCase.mutateFixture,
    failureCase.mutateConfig,
    failureCase.expectedKeyword,
  )
  passedCount += 1
}

console.log(`All frontend contract engine fixture tests passed. scenarios=${passedCount}`)
