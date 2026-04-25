import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
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

export const FRONTEND_SYNC_ARRAY_ITERATION_METHOD_DESCRIPTOR_MAP = new Map([
  ['forEach', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['map', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['some', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['every', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['filter', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['find', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['findIndex', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['findLast', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['findLastIndex', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['flatMap', { callbackArgumentIndex: 0, currentItemParameterIndex: 0 }],
  ['reduce', { callbackArgumentIndex: 0, currentItemParameterIndex: 1 }],
  ['reduceRight', { callbackArgumentIndex: 0, currentItemParameterIndex: 1 }],
])

const getTsScriptKind = (targetPath) => {
  const normalized = String(targetPath || '').toLowerCase()
  if (normalized.endsWith('.tsx')) return ts.ScriptKind.TSX
  if (normalized.endsWith('.jsx')) return ts.ScriptKind.JSX
  if (normalized.endsWith('.js') || normalized.endsWith('.mjs') || normalized.endsWith('.cjs')) {
    return ts.ScriptKind.JS
  }
  return ts.ScriptKind.TS
}

const createAnalysisSourceFile = (sourceText, targetPath) =>
  ts.createSourceFile(targetPath, sourceText, ts.ScriptTarget.Latest, true, getTsScriptKind(targetPath))

const unwrapTsExpression = (node) => {
  let current = node
  while (current) {
    if (ts.isParenthesizedExpression(current)) {
      current = current.expression
      continue
    }
    if (ts.isAsExpression(current) || ts.isTypeAssertionExpression(current)) {
      current = current.expression
      continue
    }
    if (ts.isSatisfiesExpression(current)) {
      current = current.expression
      continue
    }
    if (ts.isNonNullExpression(current)) {
      current = current.expression
      continue
    }
    break
  }
  return current
}

const getStaticLiteralText = (node) => {
  const target = unwrapTsExpression(node)
  if (!target) return null
  if (ts.isStringLiteral(target) || ts.isNoSubstitutionTemplateLiteral(target)) return target.text
  if (ts.isNumericLiteral(target)) return target.text
  return null
}

const getStaticMemberName = (node) => {
  const target = unwrapTsExpression(node)
  if (!target) return null
  if (ts.isPropertyAccessExpression(target)) return target.name.text
  if (ts.isElementAccessExpression(target)) return getStaticLiteralText(target.argumentExpression || null)
  return null
}

const isStaticArrayNamespaceExpression = (expression, depth = 0) => {
  if (!expression || depth > 8) return false
  const target = unwrapTsExpression(expression)
  if (!target) return false
  if (ts.isIdentifier(target)) return target.text === 'Array'
  if (ts.isConditionalExpression(target)) {
    return (
      isStaticArrayNamespaceExpression(target.whenTrue, depth + 1) &&
      isStaticArrayNamespaceExpression(target.whenFalse, depth + 1)
    )
  }
  return false
}

const isStaticArrayPrototypeExpression = (expression, depth = 0) => {
  if (!expression || depth > 8) return false
  const target = unwrapTsExpression(expression)
  if (!target) return false
  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (memberName !== 'prototype') return false
    return isStaticArrayNamespaceExpression(target.expression, depth + 1)
  }
  if (ts.isConditionalExpression(target)) {
    return (
      isStaticArrayPrototypeExpression(target.whenTrue, depth + 1) &&
      isStaticArrayPrototypeExpression(target.whenFalse, depth + 1)
    )
  }
  return false
}

const resolveStaticArrayPrototypeIterationMethodName = (expression, depth = 0) => {
  if (!expression || depth > 8) return null
  const target = unwrapTsExpression(expression)
  if (!target) return null
  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (!memberName || !FRONTEND_SYNC_ARRAY_ITERATION_METHOD_DESCRIPTOR_MAP.has(memberName)) return null
    if (!isStaticArrayPrototypeExpression(target.expression, depth + 1)) return null
    return memberName
  }
  if (ts.isConditionalExpression(target)) {
    const whenTrue = resolveStaticArrayPrototypeIterationMethodName(target.whenTrue, depth + 1)
    const whenFalse = resolveStaticArrayPrototypeIterationMethodName(target.whenFalse, depth + 1)
    if (whenTrue && whenFalse && whenTrue === whenFalse) return whenTrue
  }
  return null
}

const resolveArrayLiteralElements = (expression, arrayLiteralAliasMap, depth = 0) => {
  if (!expression || depth > 8) return null
  const target = unwrapTsExpression(expression)
  if (!target) return null
  if (ts.isArrayLiteralExpression(target)) {
    return target.elements.map((element) => unwrapTsExpression(element))
  }
  if (ts.isIdentifier(target)) {
    const alias = arrayLiteralAliasMap.get(target.text) || null
    if (!alias) return null
    return resolveArrayLiteralElements(alias, arrayLiteralAliasMap, depth + 1)
  }
  if (ts.isConditionalExpression(target)) {
    const whenTrue = resolveArrayLiteralElements(target.whenTrue, arrayLiteralAliasMap, depth + 1)
    const whenFalse = resolveArrayLiteralElements(target.whenFalse, arrayLiteralAliasMap, depth + 1)
    if (!whenTrue || !whenFalse || whenTrue.length !== whenFalse.length) return null
    return whenTrue.every((item, index) => item?.getText() === whenFalse[index]?.getText()) ? whenTrue : null
  }
  return null
}

const buildIterationDescriptor = ({
  callNode,
  methodName,
  argumentMode,
  iterableExpression,
  callbackExpression,
  initialValueExpression = null,
}) => {
  const methodDescriptor = FRONTEND_SYNC_ARRAY_ITERATION_METHOD_DESCRIPTOR_MAP.get(methodName) || null
  if (!methodDescriptor) return null
  return {
    methodName,
    argumentMode,
    iterableExpression: unwrapTsExpression(iterableExpression),
    callbackExpression: unwrapTsExpression(callbackExpression),
    initialValueExpression: unwrapTsExpression(initialValueExpression),
    callbackArgumentIndex: methodDescriptor.callbackArgumentIndex,
    currentItemParameterIndex: methodDescriptor.currentItemParameterIndex,
    callExpressionText: callNode.getText(),
  }
}

const resolveBindIterationDescriptor = (expression) => {
  const target = unwrapTsExpression(expression)
  if (!target || !ts.isCallExpression(target)) return null
  const bindCallee = unwrapTsExpression(target.expression)
  if (!(bindCallee && (ts.isPropertyAccessExpression(bindCallee) || ts.isElementAccessExpression(bindCallee)))) {
    return null
  }
  if (getStaticMemberName(bindCallee) !== 'bind') return null
  const methodName = resolveStaticArrayPrototypeIterationMethodName(bindCallee.expression)
  if (!methodName) return null
  const iterableExpression = unwrapTsExpression(target.arguments[0] || null)
  const boundArgs = target.arguments.slice(1).map((item) => unwrapTsExpression(item))
  return {
    methodName,
    iterableExpression,
    boundArgs,
  }
}

const resolveIterationCallDescriptor = (callNode, bindAliasMap, arrayLiteralAliasMap) => {
  const calleeExpression = unwrapTsExpression(callNode.expression)
  if (!calleeExpression) return null

  if (ts.isIdentifier(calleeExpression)) {
    const bindAlias = bindAliasMap.get(calleeExpression.text) || null
    if (bindAlias) {
      return buildIterationDescriptor({
        callNode,
        methodName: bindAlias.methodName,
        argumentMode: 'bind',
        iterableExpression: bindAlias.iterableExpression,
        callbackExpression: bindAlias.boundArgs[0] || callNode.arguments[0] || null,
        initialValueExpression: bindAlias.boundArgs[1] || callNode.arguments[1] || null,
      })
    }
  }

  if (ts.isCallExpression(calleeExpression)) {
    const inlineBind = resolveBindIterationDescriptor(calleeExpression)
    if (inlineBind) {
      return buildIterationDescriptor({
        callNode,
        methodName: inlineBind.methodName,
        argumentMode: 'bind',
        iterableExpression: inlineBind.iterableExpression,
        callbackExpression: inlineBind.boundArgs[0] || callNode.arguments[0] || null,
        initialValueExpression: inlineBind.boundArgs[1] || callNode.arguments[1] || null,
      })
    }
  }

  if (ts.isPropertyAccessExpression(calleeExpression) || ts.isElementAccessExpression(calleeExpression)) {
    const memberName = getStaticMemberName(calleeExpression)

    if (memberName && FRONTEND_SYNC_ARRAY_ITERATION_METHOD_DESCRIPTOR_MAP.has(memberName)) {
      return buildIterationDescriptor({
        callNode,
        methodName: memberName,
        argumentMode: 'direct',
        iterableExpression: calleeExpression.expression,
        callbackExpression: callNode.arguments[0] || null,
        initialValueExpression: callNode.arguments[1] || null,
      })
    }

    if (memberName === 'call') {
      const methodName = resolveStaticArrayPrototypeIterationMethodName(calleeExpression.expression)
      if (methodName) {
        return buildIterationDescriptor({
          callNode,
          methodName,
          argumentMode: 'call',
          iterableExpression: callNode.arguments[0] || null,
          callbackExpression: callNode.arguments[1] || null,
          initialValueExpression: callNode.arguments[2] || null,
        })
      }
    }

    if (memberName === 'apply') {
      const methodName = resolveStaticArrayPrototypeIterationMethodName(calleeExpression.expression)
      if (methodName) {
        const applyArgs = resolveArrayLiteralElements(callNode.arguments[1] || null, arrayLiteralAliasMap)
        if (!applyArgs) return null
        return buildIterationDescriptor({
          callNode,
          methodName,
          argumentMode: 'apply',
          iterableExpression: callNode.arguments[0] || null,
          callbackExpression: applyArgs[0] || null,
          initialValueExpression: applyArgs[1] || null,
        })
      }
    }
  }

  if (
    (ts.isPropertyAccessExpression(calleeExpression) || ts.isElementAccessExpression(calleeExpression)) &&
    getStaticMemberName(calleeExpression) === 'apply'
  ) {
    const reflectBase = unwrapTsExpression(calleeExpression.expression)
    if (reflectBase && ts.isIdentifier(reflectBase) && reflectBase.text === 'Reflect') {
      const methodName = resolveStaticArrayPrototypeIterationMethodName(callNode.arguments[0] || null)
      const reflectArgs = resolveArrayLiteralElements(callNode.arguments[2] || null, arrayLiteralAliasMap)
      if (methodName && reflectArgs) {
        return buildIterationDescriptor({
          callNode,
          methodName,
          argumentMode: 'reflect_apply',
          iterableExpression: callNode.arguments[1] || null,
          callbackExpression: reflectArgs[0] || null,
          initialValueExpression: reflectArgs[1] || null,
        })
      }
    }
  }

  return null
}

const collectFunctionLikeBindings = (sourceFile) => {
  const functionBindingMap = new Map()
  const arrayLiteralAliasMap = new Map()
  const bindAliasMap = new Map()

  const visit = (node) => {
    if (ts.isFunctionDeclaration(node) && node.name) {
      functionBindingMap.set(node.name.text, node)
    } else if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
      const initializer = unwrapTsExpression(node.initializer)
      if (initializer && (ts.isArrowFunction(initializer) || ts.isFunctionExpression(initializer))) {
        functionBindingMap.set(node.name.text, initializer)
      } else if (initializer && ts.isArrayLiteralExpression(initializer)) {
        arrayLiteralAliasMap.set(node.name.text, initializer)
      } else {
        const bindAlias = resolveBindIterationDescriptor(initializer)
        if (bindAlias) {
          bindAliasMap.set(node.name.text, bindAlias)
        }
      }
    }
    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return {
    functionBindingMap,
    arrayLiteralAliasMap,
    bindAliasMap,
  }
}

const resolveCallbackFunctionNode = (callbackExpression, functionBindingMap) => {
  const target = unwrapTsExpression(callbackExpression)
  if (!target) return null
  if (ts.isArrowFunction(target) || ts.isFunctionExpression(target)) return target
  if (ts.isIdentifier(target)) return functionBindingMap.get(target.text) || null
  return null
}

const expressionContainsIdentifier = (expression, identifierName) => {
  let found = false
  const visit = (node) => {
    if (found) return
    if (
      ts.isFunctionDeclaration(node) ||
      ts.isFunctionExpression(node) ||
      ts.isArrowFunction(node) ||
      ts.isMethodDeclaration(node)
    ) {
      return
    }
    if (ts.isIdentifier(node) && node.text === identifierName) {
      found = true
      return
    }
    ts.forEachChild(node, visit)
  }
  visit(expression)
  return found
}

const collectCallbackSinkExpressions = (callbackNode, currentItemParameterIndex, sourceFile) => {
  const parameterNode = callbackNode.parameters[currentItemParameterIndex] || null
  if (!(parameterNode && ts.isIdentifier(parameterNode.name))) {
    return {
      currentItemParameterName: null,
      sinkExpressions: [],
      unresolved: true,
    }
  }

  const parameterName = parameterNode.name.text
  const sinkExpressions = []
  const seen = new Set()
  const bodyNode = ts.isBlock(callbackNode.body)
    ? callbackNode.body
    : unwrapTsExpression(callbackNode.body)

  const visit = (node) => {
    if (
      ts.isFunctionDeclaration(node) ||
      ts.isFunctionExpression(node) ||
      ts.isArrowFunction(node) ||
      ts.isMethodDeclaration(node)
    ) {
      if (node === callbackNode) {
        ts.forEachChild(node, visit)
      }
      return
    }

    if (ts.isCallExpression(node)) {
      const hasSinkArg = node.arguments.some((argNode) => expressionContainsIdentifier(argNode, parameterName))
      if (hasSinkArg) {
        const sinkText = node.getText(sourceFile)
        if (!seen.has(sinkText)) {
          seen.add(sinkText)
          sinkExpressions.push(sinkText)
        }
      }
    }

    ts.forEachChild(node, visit)
  }

  if (bodyNode) {
    visit(bodyNode)
  }

  return {
    currentItemParameterName: parameterName,
    sinkExpressions,
    unresolved: false,
  }
}

export const analyzeSynchronousArrayIterationCallbackSinks = (
  sourceText,
  { targetPath = 'inline.ts' } = {},
) => {
  const sourceFile = createAnalysisSourceFile(sourceText, targetPath)
  const { functionBindingMap, arrayLiteralAliasMap, bindAliasMap } = collectFunctionLikeBindings(sourceFile)
  const descriptors = []

  const visit = (node) => {
    if (ts.isCallExpression(node)) {
      const descriptor = resolveIterationCallDescriptor(node, bindAliasMap, arrayLiteralAliasMap)
      if (descriptor) {
        const callbackNode = resolveCallbackFunctionNode(descriptor.callbackExpression, functionBindingMap)
        const callbackSinkResult = callbackNode
          ? collectCallbackSinkExpressions(callbackNode, descriptor.currentItemParameterIndex, sourceFile)
          : {
              currentItemParameterName: null,
              sinkExpressions: [],
              unresolved: true,
            }
        descriptors.push({
          methodName: descriptor.methodName,
          argumentMode: descriptor.argumentMode,
          callExpressionText: descriptor.callExpressionText,
          callbackExpressionText: descriptor.callbackExpression?.getText(sourceFile) || '',
          currentItemParameterName: callbackSinkResult.currentItemParameterName,
          sinkExpressions: callbackSinkResult.sinkExpressions,
          unresolvedCallback: callbackSinkResult.unresolved,
        })
      }
    }
    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return descriptors
}

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
