import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export const defaultProjectRoot = path.resolve(__dirname, '..')

export const normalizePath = (targetPath) => targetPath.replace(/\\/g, '/')

export const readTextFile = (targetPath) => readFileSync(targetPath, 'utf8')

export const collectFiles = (dirPath) => {
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

export const parseCliArgs = (argv) => {
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

export const createViolation = ({ ruleId, message, targetPath, match = '' }) => ({
  ruleId,
  message,
  targetPath,
  match,
})

export const formatViolation = (violation) =>
  `[${violation.ruleId}] ${violation.message}: ${violation.targetPath}${violation.match ? ` -> ${violation.match}` : ''}`

const SURFACE_SCOPE_TO_PATH = {
  api: 'src/api',
  views: 'src/views',
  router: 'src/router',
  stores: 'src/stores',
  components: 'src/components',
  utils: 'src/utils',
}

const ALLOWED_SCAN_SCOPES = new Set(Object.keys(SURFACE_SCOPE_TO_PATH))
const DEFAULT_SCAN_FILE_REGEX = /\.(?:ts|tsx|js|jsx|vue|mjs|cjs|json)$/i

export const validateModuleContractConfig = (config) => {
  const failures = []
  if (!config || typeof config !== 'object') {
    failures.push('模块门禁配置必须为对象')
    return { ok: false, failures }
  }

  if (!config.module || typeof config.module !== 'string') {
    failures.push('模块门禁配置缺少 module')
  }

  if (!config.surface || typeof config.surface !== 'object') {
    failures.push('模块门禁配置缺少 surface')
  } else {
    if (!config.surface.moduleKey || typeof config.surface.moduleKey !== 'string') {
      failures.push('模块门禁配置缺少 surface.moduleKey')
    }
    if (!Array.isArray(config.surface.scanScopes) || config.surface.scanScopes.length === 0) {
      failures.push('模块门禁配置缺少 surface.scanScopes')
    } else {
      const unknownScopes = config.surface.scanScopes.filter((item) => !ALLOWED_SCAN_SCOPES.has(item))
      for (const unknownScope of unknownScopes) {
        failures.push(`模块门禁配置存在未知 scan scope: ${unknownScope}`)
      }
    }
  }

  for (const fieldName of [
    'allowedApis',
    'forbiddenApis',
    'forbiddenActions',
    'allowedReadOnlyActions',
    'allowedHttpMethods',
  ]) {
    if (!Array.isArray(config[fieldName])) {
      failures.push(`模块门禁配置缺少数组字段: ${fieldName}`)
    }
  }

  if (!Array.isArray(config.rules)) {
    failures.push('模块门禁配置缺少 rules 数组')
  }

  if (!config.fixture || typeof config.fixture !== 'object') {
    failures.push(`模块门禁配置缺少 fixture: ${config.module ?? '<unknown-module>'}`)
  } else {
    if (!Array.isArray(config.fixture.positive) || config.fixture.positive.length === 0) {
      failures.push(`模块门禁配置缺少非空 fixture.positive: ${config.module ?? '<unknown-module>'}`)
    }
    if (!Array.isArray(config.fixture.negative) || config.fixture.negative.length === 0) {
      failures.push(`模块门禁配置缺少非空 fixture.negative: ${config.module ?? '<unknown-module>'}`)
    }
  }

  return {
    ok: failures.length === 0,
    failures,
  }
}

const collectSurfaceFiles = (projectRoot, surface) => {
  const roots = []
  for (const scope of surface.scanScopes || []) {
    const relative = SURFACE_SCOPE_TO_PATH[scope]
    if (!relative) continue
    roots.push(path.join(projectRoot, relative))
  }

  if (Array.isArray(surface.extraPaths)) {
    for (const extraPath of surface.extraPaths) {
      roots.push(path.join(projectRoot, extraPath))
    }
  }

  const files = []
  for (const root of roots) {
    if (!existsSync(root)) continue
    const st = statSync(root)
    if (st.isDirectory()) {
      files.push(...collectFiles(root))
    } else if (st.isFile()) {
      files.push(root)
    }
  }

  return [...new Set(files.map((item) => normalizePath(item)))].sort()
}

const ruleMatches = (rule, content, context) => {
  if (typeof rule.matcher === 'function') {
    return rule.matcher(content, context)
  }

  if (rule.regex instanceof RegExp) {
    const clone = new RegExp(rule.regex.source, rule.regex.flags)
    const matches = []
    let found = clone.exec(content)
    while (found) {
      matches.push(found[0])
      if (!clone.global) break
      found = clone.exec(content)
    }
    return matches
  }

  return []
}

const checkHttpMethodPolicy = (content, allowedHttpMethods) => {
  const violations = []
  const normalizedAllowed = new Set((allowedHttpMethods || []).map((item) => String(item).toUpperCase()))
  for (const disallowed of ['POST', 'PUT', 'PATCH', 'DELETE']) {
    if (normalizedAllowed.has(disallowed)) continue
    const methodRegex = new RegExp(`method\\s*:\\s*['\"]${disallowed}['\"]`, 'g')
    if (methodRegex.test(content)) {
      violations.push({
        ruleId: 'FWG-API-HTTP',
        message: `禁止未授权 ${disallowed} 写入口`,
        match: disallowed,
      })
    }
  }
  return violations
}

const checkForbiddenActions = (content, forbiddenActions) => {
  const violations = []
  for (const action of forbiddenActions || []) {
    const escaped = action.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const asciiWord = /^[A-Za-z0-9_]+$/.test(action)
    const regex = asciiWord ? new RegExp(`\\b${escaped}\\b`, 'gi') : new RegExp(escaped, 'gi')
    if (regex.test(content)) {
      violations.push({
        ruleId: 'FWG-ACT-001',
        message: '禁止出现未授权写动作语义',
        match: action,
      })
    }
  }
  return violations
}

export const runFrontendContractEngine = (projectRootInput, moduleConfig) => {
  const projectRoot = path.resolve(projectRootInput || defaultProjectRoot)
  const validation = validateModuleContractConfig(moduleConfig)
  if (!validation.ok) {
    const failures = validation.failures.map((message) => `[FWG-CONFIG-001] ${message}`)
    return {
      ok: false,
      failures,
      scannedFiles: 0,
      violations: [],
    }
  }

  const scanFiles = collectSurfaceFiles(projectRoot, moduleConfig.surface)
  if ((moduleConfig.surface?.scanScopes?.length ?? 0) > 0 && scanFiles.length === 0) {
    return {
      ok: false,
      failures: [
        `[FWG-SCAN-001] 模块 ${moduleConfig.module} / surface ${moduleConfig.surface.moduleKey} 扫描结果为空，scanScopes=${JSON.stringify(moduleConfig.surface.scanScopes)}`,
      ],
      scannedFiles: 0,
      violations: [],
    }
  }
  const violations = []

  for (const targetPath of scanFiles) {
    if (!DEFAULT_SCAN_FILE_REGEX.test(targetPath)) continue
    if (!existsSync(targetPath)) continue
    const content = readTextFile(targetPath)
    const relativePath = normalizePath(path.relative(projectRoot, targetPath))

    const context = {
      projectRoot,
      targetPath,
      relativePath,
      moduleConfig,
    }

    const inSurface =
      typeof moduleConfig.surfaceMatcher === 'function'
        ? moduleConfig.surfaceMatcher({ targetPath, relativePath, content, projectRoot })
        : true

    if (!inSurface) continue

    for (const rule of moduleConfig.rules) {
      if (typeof rule.when === 'function' && !rule.when(context)) continue
      const matches = ruleMatches(rule, content, context)
      for (const match of matches) {
        violations.push(
          createViolation({
            ruleId: rule.id,
            message: rule.message,
            targetPath,
            match: typeof match === 'string' ? match : '',
          }),
        )
      }
    }

    if (moduleConfig.enforceHttpMethodPolicy) {
      for (const item of checkHttpMethodPolicy(content, moduleConfig.allowedHttpMethods)) {
        violations.push(createViolation({ ...item, targetPath }))
      }
    }

    if (moduleConfig.enforceForbiddenActions) {
      for (const item of checkForbiddenActions(content, moduleConfig.forbiddenActions)) {
        violations.push(createViolation({ ...item, targetPath }))
      }
    }
  }

  const deduped = []
  const seen = new Set()
  for (const violation of violations) {
    const key = `${violation.ruleId}|${violation.targetPath}|${violation.match}`
    if (seen.has(key)) continue
    seen.add(key)
    deduped.push(violation)
  }

  return {
    ok: deduped.length === 0,
    failures: deduped.map(formatViolation),
    scannedFiles: scanFiles.length,
    violations: deduped,
  }
}

export const validateCsvFormulaGuardContent = (content) => {
  const failures = []
  if (!content.includes('FORMULA_INJECTION_PREFIX')) {
    failures.push('CSV 公式注入防护缺少 FORMULA_INJECTION_PREFIX')
    return failures
  }
  if (!content.includes('neutralizeCsvFormula')) {
    failures.push('CSV 公式注入防护缺少 neutralizeCsvFormula')
  }

  const requiredTokens = [
    { regex: /FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*=/, label: '=' },
    { regex: /FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\+/, label: '+' },
    { regex: /FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\-/, label: '-' },
    { regex: /FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*@/, label: '@' },
    { regex: /FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\t/, label: 'tab' },
    { regex: /FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\r/, label: 'CR' },
    { regex: /FORMULA_INJECTION_PREFIX\s*=\s*\/\^\[[^\]]*\\n/, label: 'LF' },
  ]

  for (const item of requiredTokens) {
    if (!item.regex.test(content)) {
      failures.push(`CSV 公式注入前缀缺少 ${item.label} 覆盖`)
    }
  }

  if (!/neutralizeCsvFormula\s*\(\s*toText\(value\)\s*\)/.test(content)) {
    failures.push('escapeCsvCell 必须调用 neutralizeCsvFormula(toText(value))')
  }

  return failures
}

export const FRONTEND_WRITE_GUARD_COMMON_RULES = [
  {
    id: 'FWG-API-001',
    regex: /\bfetch\s*\(/g,
    message: '禁止裸 fetch()，必须走统一 request() 封装',
  },
  {
    id: 'FWG-API-002',
    regex: /\baxios\s*(?:\.|\()/g,
    message: '禁止裸 axios 调用，必须走统一 request() 封装',
  },
  {
    id: 'FWG-API-003',
    regex: /\/api\/resource/gi,
    message: '禁止 ERPNext /api/resource 直连',
  },
  {
    id: 'FWG-INT-001',
    regex: /\/internal\//gi,
    message: '禁止前端调用 internal 接口',
  },
  {
    id: 'FWG-INT-002',
    regex: /\brun-once\b/gi,
    message: '禁止在前端页面或路由暴露 run-once 动作',
  },
  {
    id: 'FWG-INT-003',
    regex: /\bdiagnostic\b/gi,
    message: '禁止在普通页面暴露 diagnostic 动作',
  },
  {
    id: 'FWG-RUN-001',
    regex: /\beval\s*\(/g,
    message: '禁止动态代码执行 eval',
  },
  {
    id: 'FWG-RUN-002',
    regex: /\bnew\s+Function\s*\(/g,
    message: '禁止动态代码执行 new Function',
  },
  {
    id: 'FWG-RUN-003',
    regex: /\bFunction\s*\(/g,
    message: '禁止动态代码执行 Function',
  },
  {
    id: 'FWG-RUN-004',
    regex: /\bset(?:Timeout|Interval)\s*\(\s*['"`]/g,
    message: '禁止字符串 setTimeout/setInterval 执行代码',
  },
  {
    id: 'FWG-RUN-005',
    regex: /\bimport\s*\(\s*['"`]\s*(?:data:|blob:|javascript:|https?:)/gi,
    message: '禁止 dynamic import 加载高危 URL',
  },
  {
    id: 'FWG-RUN-006',
    regex: /\bnew\s+(?:Worker|SharedWorker)\s*\(\s*['"`]\s*(?:data:|blob:|javascript:|https?:)/gi,
    message: '禁止 Worker/SharedWorker 使用高危 URL',
  },
  {
    id: 'FWG-RUN-007',
    regex: /URL\.createObjectURL\s*\(/g,
    message: '禁止 URL.createObjectURL 绕过动态加载门禁',
  },
]

export const runContractCli = ({ argv = process.argv.slice(2), check, passMessage, failTitle }) => {
  const { projectRoot } = parseCliArgs(argv)
  const result = check(projectRoot)
  if (!result.ok) {
    console.error(failTitle)
    for (const [idx, message] of result.failures.entries()) {
      console.error(`${idx + 1}. ${message}`)
    }
    process.exit(1)
  }
  console.log(passMessage)
  console.log(`Scanned files: ${result.scannedFiles}`)
}

export const isMainModule = (entryFile, cliEntry) =>
  Boolean(cliEntry) && path.resolve(cliEntry) === path.resolve(entryFile)
