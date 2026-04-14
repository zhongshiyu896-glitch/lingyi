import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const defaultProjectRoot = path.resolve(__dirname, '..')

const normalizePath = (targetPath) => targetPath.replace(/\\/g, '/')

const read = (targetPath) => readFileSync(targetPath, 'utf8')

const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

const collectFiles = (dirPath) => {
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

const parseCliArgs = (argv) => {
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

const isStyleProfitSurface = (targetPath, content, projectRoot) => {
  const normalized = normalizePath(path.relative(projectRoot, targetPath))
  if (normalized.includes('/style_profit/')) return true
  if (normalized.endsWith('/api/style_profit.ts')) return true
  if (normalized === 'src/App.vue') return true
  if (normalized === 'src/main.ts') return true
  if (normalized.startsWith('src/components/')) return true
  if (/(style-profit|style_profit)/i.test(content)) return true
  return false
}

const readonlyPhrases = [
  '款式利润报表',
  '利润快照列表',
  '利润快照详情',
  '查看详情',
  '查询',
  '筛选',
  '搜索',
  '返回',
  '审计信息',
  '利润明细',
  '来源追溯',
  '利润率',
  '利润金额',
]

const semanticDomainWords = ['款式利润', '利润快照', '利润报表', '毛利', '净利', '利润核算', '利润']
const semanticWriteActions = ['新建', '创建', '生成', '重算', '重新计算', '计算', '核算', '提交', '保存', '一键生成']

const domainAlternation = semanticDomainWords.map(escapeRegex).join('|')
const actionAlternation = semanticWriteActions.map(escapeRegex).join('|')
const semanticWriteEntryRegex = new RegExp(
  `(${domainAlternation}).{0,16}(${actionAlternation})|(${actionAlternation}).{0,16}(${domainAlternation})`,
  'g',
)

const semanticIdentifierRegexes = [
  /\bcreateProfit\b/gi,
  /\bgenerateProfit\b/gi,
  /\brecalculateProfit\b/gi,
  /\bcreateSnapshot\b/gi,
  /\bgenerateSnapshot\b/gi,
  /\brecalculateSnapshot\b/gi,
  /\bprofitCreate\b/gi,
  /\bprofitGenerate\b/gi,
  /\bprofitRecalculate\b/gi,
  /\bgenerateProfitSnapshot\b/gi,
  /\bopenProfitCalculateDialog\b/gi,
]

const semanticRouteRegexes = [
  /path\s*:\s*['"]\/reports\/style-profit\/create['"]/gi,
  /path\s*:\s*['"]\/reports\/style-profit\/new['"]/gi,
  /path\s*:\s*['"]\/reports\/style-profit\/generate['"]/gi,
  /path\s*:\s*['"]\/reports\/style-profit\/recalculate['"]/gi,
  /path\s*:\s*['"]\/reports\/style-profit\/calculate['"]/gi,
]

const readonlyExplanationPhrases = [
  '利润计算说明',
  '利润率计算规则',
  '实际成本计算口径说明',
  '标准成本计算口径说明',
  '款式利润报表查看说明',
  '利润快照来源说明',
  '利润金额展示规则',
  '未解析来源处理说明',
]

const interactiveContextWindowRegexes = [/@click\b/i, /\bonClick\b/i, /\brouter\.push\b/i, /\bpath\s*:/i, /\bname\s*:/i]

const interactiveTagPairs = [
  {
    open: /<\s*el-button\b[^>]*>/gi,
    close: /<\s*\/\s*el-button\s*>/gi,
  },
  {
    open: /<\s*button\b[^>]*>/gi,
    close: /<\s*\/\s*button\s*>/gi,
  },
  {
    open: /<\s*el-menu-item\b[^>]*>/gi,
    close: /<\s*\/\s*el-menu-item\s*>/gi,
  },
  {
    open: /<\s*menu-item\b[^>]*>/gi,
    close: /<\s*\/\s*menu-item\s*>/gi,
  },
]

const actionInteractiveKeys = [
  'onClick',
  'handler',
  'action',
  'command',
  'onSelect',
  'onCommand',
  'callback',
  'execute',
  'submit',
  'onConfirm',
  'onSubmit',
  'click',
  'open',
]
const actionInteractiveKeySet = new Set(actionInteractiveKeys.map((value) => value.toLowerCase()))
const explanationFieldNameSet = new Set(['label', 'title', 'text', 'name', 'tooltip', 'description'])
const dottedExplanationFieldNameSet = new Set(['meta.label', 'meta.title', 'props.label', 'extra.label', 'payload.label'])
const actionInteractiveKeyAlternation = actionInteractiveKeys.map(escapeRegex).join('|')
const actionInteractiveAssignmentPattern = `(?:['"\`]\\s*)?(?:${actionInteractiveKeyAlternation})(?:\\s*['"\`])?\\s*:`
const actionInteractiveMethodPattern = `(?:\\basync\\s+)?(?:['"\`]\\s*)?(?:${actionInteractiveKeyAlternation})(?:\\s*['"\`])?\\s*\\([^)]*\\)\\s*\\{`
const actionInteractiveComputedAssignmentPattern = `\\[\\s*['"\`]\\s*(?:${actionInteractiveKeyAlternation})\\s*['"\`]\\s*\\]\\s*:`
const actionInteractiveComputedMethodPattern = `(?:\\basync\\s+)?\\[\\s*['"\`]\\s*(?:${actionInteractiveKeyAlternation})\\s*['"\`]\\s*\\]\\s*\\([^)]*\\)\\s*\\{`
const actionInteractiveMemberRegex = new RegExp(
  `(?:${actionInteractiveAssignmentPattern})|(?:${actionInteractiveMethodPattern})|(?:${actionInteractiveComputedAssignmentPattern})|(?:${actionInteractiveComputedMethodPattern})`,
  'i',
)
const explanationFieldNames = ['label', 'title', 'text', 'name', 'tooltip', 'description']
const dottedExplanationFieldNames = ['meta.label', 'meta.title', 'props.label', 'extra.label', 'payload.label']

const collectObjectBlocks = (content) => {
  const blocks = []
  const stack = []

  let inSingleQuote = false
  let inDoubleQuote = false
  let inTemplate = false
  let inLineComment = false
  let inBlockComment = false
  let escaped = false

  for (let idx = 0; idx < content.length; idx += 1) {
    const ch = content[idx]
    const next = content[idx + 1]

    if (inLineComment) {
      if (ch === '\n') inLineComment = false
      continue
    }
    if (inBlockComment) {
      if (ch === '*' && next === '/') {
        inBlockComment = false
        idx += 1
      }
      continue
    }

    if (inSingleQuote || inDoubleQuote || inTemplate) {
      if (escaped) {
        escaped = false
        continue
      }
      if (ch === '\\') {
        escaped = true
        continue
      }
      if (inSingleQuote && ch === "'") {
        inSingleQuote = false
        continue
      }
      if (inDoubleQuote && ch === '"') {
        inDoubleQuote = false
        continue
      }
      if (inTemplate && ch === '`') {
        inTemplate = false
        continue
      }
      continue
    }

    if (ch === '/' && next === '/') {
      inLineComment = true
      idx += 1
      continue
    }
    if (ch === '/' && next === '*') {
      inBlockComment = true
      idx += 1
      continue
    }

    if (ch === "'") {
      inSingleQuote = true
      continue
    }
    if (ch === '"') {
      inDoubleQuote = true
      continue
    }
    if (ch === '`') {
      inTemplate = true
      continue
    }

    if (ch === '{') {
      stack.push(idx)
      continue
    }
    if (ch === '}') {
      const start = stack.pop()
      if (start !== undefined) {
        blocks.push({ start, end: idx + 1 })
      }
    }
  }

  return blocks.sort((a, b) => (a.end - a.start) - (b.end - b.start))
}

const getContextWindow = (content, index, matchLength, radius = 300) => {
  const start = Math.max(0, index - radius)
  const end = Math.min(content.length, index + matchLength + radius)
  return content.slice(start, end)
}

const matchCount = (content, regex) => {
  const cloned = new RegExp(regex.source, regex.flags)
  const matches = content.match(cloned)
  return matches ? matches.length : 0
}

const isInsideUnclosedInteractiveTag = (content, index) => {
  const prefix = content.slice(0, index)
  return interactiveTagPairs.some((pair) => matchCount(prefix, pair.open) > matchCount(prefix, pair.close))
}

const hasInteractiveContextInWindow = (content, index, matchLength) => {
  const window = getContextWindow(content, index, matchLength)
  return interactiveContextWindowRegexes.some((regex) => regex.test(window))
}

const hasIdentifierContextForPhrase = (content, phrase) => {
  const escaped = escapeRegex(phrase)
  const identifierRegexes = [
    new RegExp(`\\bfunction\\s+[^\\s(]*${escaped}[^\\s(]*`, 'i'),
    new RegExp(`\\b(const|let|var)\\s+[^=\\n]*${escaped}[^=\\n]*=`, 'i'),
  ]
  return identifierRegexes.some((regex) => regex.test(content))
}

const collectExplanationRanges = (content) => {
  const ranges = []
  for (const phrase of readonlyExplanationPhrases) {
    let index = content.indexOf(phrase)
    while (index !== -1) {
      ranges.push({ start: index, end: index + phrase.length, phrase })
      index = content.indexOf(phrase, index + phrase.length)
    }
  }
  return ranges
}

const matchExplanationRange = (ranges, start, end) =>
  ranges.find((range) => start >= range.start && end <= range.end)

const findContainingObjectBlock = (blocks, start, end) =>
  blocks.find((block) => block.start <= start && end <= block.end)

const hasExplanationFieldForPhraseInSegment = (segment, phrase) => {
  const escaped = escapeRegex(phrase)
  const plainFieldRegex = new RegExp(
    `(?:['"\`]\\s*)?(?:${explanationFieldNames.map(escapeRegex).join('|')})(?:\\s*['"\`])?\\s*:\\s*['"\`]\\s*${escaped}\\s*['"\`]`,
    'i',
  )
  const computedFieldRegex = new RegExp(
    `\\[\\s*['"\`]\\s*(?:${explanationFieldNames.map(escapeRegex).join('|')})\\s*['"\`]\\s*\\]\\s*:\\s*['"\`]\\s*${escaped}\\s*['"\`]`,
    'i',
  )
  if (plainFieldRegex.test(segment) || computedFieldRegex.test(segment)) return true
  return dottedExplanationFieldNames.some((fieldName) => {
    const dottedFieldRegex = new RegExp(
      `['"\`]?${escapeRegex(fieldName)}['"\`]?\\s*:\\s*['"\`]\\s*${escaped}\\s*['"\`]`,
      'i',
    )
    return dottedFieldRegex.test(segment)
  })
}

const collectAncestorObjectBlocks = (blocks, targetBlock) =>
  blocks
    .filter((block) => block.start <= targetBlock.start && targetBlock.end <= block.end)
    .sort((a, b) => (a.end - a.start) - (b.end - b.start))

const normalizeComputedKeyExpr = (computedExpr) => computedExpr.replace(/\s+/g, ' ').trim()

const getScriptKindByPath = (targetPath) => {
  if (targetPath.endsWith('.tsx')) return ts.ScriptKind.TSX
  if (targetPath.endsWith('.jsx')) return ts.ScriptKind.JSX
  if (targetPath.endsWith('.js')) return ts.ScriptKind.JS
  return ts.ScriptKind.TS
}

const getVueScriptKindByAttrs = (attrsRaw) => {
  const attrs = attrsRaw || ''
  const langMatch = attrs.match(/\blang\s*=\s*['"]([^'"]+)['"]/i)
  const lang = (langMatch?.[1] || '').toLowerCase()
  if (lang === 'tsx') return ts.ScriptKind.TSX
  if (lang === 'jsx') return ts.ScriptKind.JSX
  if (lang === 'js' || lang === 'javascript') return ts.ScriptKind.JS
  return ts.ScriptKind.TS
}

const extractScriptBlocksForAst = (targetPath, content) => {
  if (!targetPath.endsWith('.vue')) {
    return [
      {
        label: 'script',
        content,
        scriptKind: getScriptKindByPath(targetPath),
      },
    ]
  }

  const blocks = []
  const scriptRegex = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi
  let matched = scriptRegex.exec(content)
  while (matched) {
    const attrs = matched[1] || ''
    const scriptContent = matched[2] || ''
    if (scriptContent.trim()) {
      blocks.push({
        label: /\bsetup\b/i.test(attrs) ? 'script setup' : 'script',
        content: scriptContent,
        scriptKind: getVueScriptKindByAttrs(attrs),
      })
    }
    matched = scriptRegex.exec(content)
  }
  return blocks
}

const classifyPropertyNameNode = (nameNode) => {
  if (!nameNode) {
    return { keyClass: 'unknown_key', keyText: '', expressionText: '' }
  }

  if (ts.isComputedPropertyName(nameNode)) {
    const expr = nameNode.expression
    const expressionText = expr.getText()
    if (
      ts.isStringLiteral(expr) ||
      ts.isNoSubstitutionTemplateLiteral(expr) ||
      ts.isNumericLiteral(expr)
    ) {
      return {
        keyClass: 'literal_key',
        keyText: `${expr.text}`.toLowerCase(),
        expressionText,
      }
    }
    return {
      keyClass: 'dynamic_computed_key',
      keyText: '',
      expressionText,
    }
  }

  if (ts.isIdentifier(nameNode)) {
    return {
      keyClass: 'literal_key',
      keyText: nameNode.text.toLowerCase(),
      expressionText: nameNode.text,
    }
  }
  if (ts.isStringLiteral(nameNode) || ts.isNumericLiteral(nameNode)) {
    return {
      keyClass: 'literal_key',
      keyText: `${nameNode.text}`.toLowerCase(),
      expressionText: nameNode.text,
    }
  }

  return {
    keyClass: 'unknown_key',
    keyText: '',
    expressionText: '',
  }
}

const getStringLiteralValue = (node) => {
  if (!node) return null
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text
  return null
}

const collectObjectLiteralsFromSourceFile = (sourceFile) => {
  const objectNodes = []
  const visit = (node) => {
    if (ts.isObjectLiteralExpression(node)) {
      objectNodes.push(node)
    }
    ts.forEachChild(node, visit)
  }
  visit(sourceFile)
  return objectNodes
}

const findSmallestContainingObjectNode = (objectNodes, start, end) =>
  objectNodes
    .filter((node) => node.getStart() <= start && end <= node.end)
    .sort((a, b) => (a.end - a.getStart()) - (b.end - b.getStart()))[0] || null

const collectAstObjectChain = (node) => {
  const chain = []
  let cursor = node
  while (cursor) {
    if (ts.isObjectLiteralExpression(cursor)) {
      chain.push(cursor)
    }
    cursor = cursor.parent || null
  }
  return chain
}

const memberHasInteractiveLiteralKey = (member) => {
  if (ts.isSpreadAssignment(member)) return false
  if (ts.isShorthandPropertyAssignment(member)) {
    return actionInteractiveKeySet.has(member.name.text.toLowerCase())
  }
  if (!('name' in member) || !member.name) return false
  const keyInfo = classifyPropertyNameNode(member.name)
  return keyInfo.keyClass === 'literal_key' && actionInteractiveKeySet.has(keyInfo.keyText)
}

const memberDynamicComputedKeyInfo = (member) => {
  if (ts.isSpreadAssignment(member)) return null
  if (!('name' in member) || !member.name) return null
  const keyInfo = classifyPropertyNameNode(member.name)
  if (keyInfo.keyClass === 'dynamic_computed_key') return keyInfo
  if (keyInfo.keyClass === 'unknown_key') return keyInfo
  return null
}

const objectHasInteractiveMemberAst = (objectNode) =>
  objectNode.properties.some((member) => memberHasInteractiveLiteralKey(member))

const objectHasExplanationFieldPhraseAst = (objectNode, phrase) => {
  for (const member of objectNode.properties) {
    if (!ts.isPropertyAssignment(member)) continue
    if (!member.name) continue
    const keyInfo = classifyPropertyNameNode(member.name)
    if (keyInfo.keyClass !== 'literal_key') continue
    if (!explanationFieldNameSet.has(keyInfo.keyText) && !dottedExplanationFieldNameSet.has(keyInfo.keyText)) {
      continue
    }
    const literalValue = getStringLiteralValue(member.initializer)
    if (literalValue === phrase) return true
  }
  return false
}

const collectDynamicComputedKeyInfos = (objectNode) => {
  const findings = []
  for (const member of objectNode.properties) {
    const dynamicInfo = memberDynamicComputedKeyInfo(member)
    if (dynamicInfo) findings.push(dynamicInfo)
  }
  return findings
}

const classifyExpressionKeyNode = (expressionNode) => {
  if (!expressionNode) {
    return { keyClass: 'unknown_key', keyText: '', expressionText: '' }
  }

  if (
    ts.isStringLiteral(expressionNode) ||
    ts.isNoSubstitutionTemplateLiteral(expressionNode) ||
    ts.isNumericLiteral(expressionNode)
  ) {
    return {
      keyClass: 'literal_key',
      keyText: `${expressionNode.text}`.toLowerCase(),
      expressionText: expressionNode.getText(),
    }
  }

  return {
    keyClass: 'dynamic_computed_key',
    keyText: '',
    expressionText: expressionNode.getText(),
  }
}

const runtimeWriteOperatorKinds = new Set([
  ts.SyntaxKind.EqualsToken,
  ts.SyntaxKind.PlusEqualsToken,
  ts.SyntaxKind.MinusEqualsToken,
  ts.SyntaxKind.AsteriskEqualsToken,
  ts.SyntaxKind.AsteriskAsteriskEqualsToken,
  ts.SyntaxKind.SlashEqualsToken,
  ts.SyntaxKind.PercentEqualsToken,
  ts.SyntaxKind.LessThanLessThanEqualsToken,
  ts.SyntaxKind.GreaterThanGreaterThanEqualsToken,
  ts.SyntaxKind.GreaterThanGreaterThanGreaterThanEqualsToken,
  ts.SyntaxKind.AmpersandEqualsToken,
  ts.SyntaxKind.BarEqualsToken,
  ts.SyntaxKind.CaretEqualsToken,
  ts.SyntaxKind.BarBarEqualsToken,
  ts.SyntaxKind.AmpersandAmpersandEqualsToken,
  ts.SyntaxKind.QuestionQuestionEqualsToken,
])

const isRuntimeWriteOperator = (operatorKind) => runtimeWriteOperatorKinds.has(operatorKind)

const unwrapExpression = (node) => {
  let current = node
  while (current && ts.isParenthesizedExpression(current)) {
    current = current.expression
  }
  return current
}

const getStaticLiteralText = (node) => {
  if (!node) return null
  const target = unwrapExpression(node)
  if (ts.isStringLiteral(target) || ts.isNoSubstitutionTemplateLiteral(target) || ts.isNumericLiteral(target)) {
    return `${target.text}`
  }
  return null
}

const getStaticMemberName = (node) => {
  const target = unwrapExpression(node)
  if (!target) return null
  if (ts.isPropertyAccessExpression(target)) return target.name.text
  if (ts.isElementAccessExpression(target)) return getStaticLiteralText(target.argumentExpression || null)
  return null
}

const classifyRuntimeMethodName = (objectName, methodName) => {
  if (objectName === 'Object' && methodName === 'defineProperty') return 'Object.defineProperty'
  if (objectName === 'Object' && methodName === 'defineProperties') return 'Object.defineProperties'
  if (objectName === 'Object' && methodName === 'assign') return 'Object.assign'
  if (objectName === 'Reflect' && methodName === 'set') return 'Reflect.set'
  return null
}

const resolveRuntimeNamespaceFromExpression = (expression, runtimeNamespaceAliasMap = new Map()) => {
  const target = unwrapExpression(expression)
  if (!target) return null

  if (ts.isIdentifier(target)) {
    if (target.text === 'Object' || target.text === 'Reflect') return target.text
    return runtimeNamespaceAliasMap.get(target.text) || null
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const namespaceName = getStaticMemberName(target)
    if (namespaceName !== 'Object' && namespaceName !== 'Reflect') return null
    const baseExpr = target.expression
    const base = unwrapExpression(baseExpr)
    if (ts.isIdentifier(base) && (base.text === 'globalThis' || base.text === 'window')) {
      return namespaceName
    }
  }

  return null
}

const getBindingElementSourceKey = (bindingElement) => {
  if (!bindingElement) return null
  const propertyName = bindingElement.propertyName
  if (!propertyName) {
    return ts.isIdentifier(bindingElement.name) ? bindingElement.name.text : null
  }
  if (ts.isIdentifier(propertyName) || ts.isStringLiteral(propertyName) || ts.isNumericLiteral(propertyName)) {
    return `${propertyName.text}`
  }
  if (ts.isComputedPropertyName(propertyName)) {
    return getStaticLiteralText(propertyName.expression)
  }
  return null
}

const resolveRuntimeMethodFromExpression = (
  expression,
  runtimeMethodAliasMap = new Map(),
  runtimeNamespaceAliasMap = new Map(),
) => {
  const target = unwrapExpression(expression)
  if (!target) return null

  if (ts.isIdentifier(target)) {
    return runtimeMethodAliasMap.get(target.text) || null
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (!memberName) return null
    const namespaceName = resolveRuntimeNamespaceFromExpression(target.expression, runtimeNamespaceAliasMap)
    if (!namespaceName) return null
    return classifyRuntimeMethodName(namespaceName, memberName)
  }

  if (ts.isCallExpression(target)) {
    const bindMemberName = getStaticMemberName(target.expression)
    if (bindMemberName !== 'bind') return null
    const bindBaseExpr =
      ts.isPropertyAccessExpression(target.expression) || ts.isElementAccessExpression(target.expression)
        ? target.expression.expression
        : null
    if (!bindBaseExpr) return null
    return resolveRuntimeMethodFromExpression(bindBaseExpr, runtimeMethodAliasMap, runtimeNamespaceAliasMap)
  }

  return null
}

const resolveRuntimeCallDescriptor = (calleeExpression, runtimeMethodAliasMap = new Map(), runtimeNamespaceAliasMap = new Map()) => {
  const target = unwrapExpression(calleeExpression)
  if (!target) return null

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (memberName === 'call' || memberName === 'apply') {
      const baseMethod = resolveRuntimeMethodFromExpression(
        target.expression,
        runtimeMethodAliasMap,
        runtimeNamespaceAliasMap,
      )
      if (baseMethod) {
        return { method: baseMethod, invoke: memberName }
      }
    }
  }

  const directMethod = resolveRuntimeMethodFromExpression(target, runtimeMethodAliasMap, runtimeNamespaceAliasMap)
  if (directMethod) {
    return { method: directMethod, invoke: 'direct' }
  }
  return null
}

const normalizeRuntimeCallArguments = (callNode, callDescriptor) => {
  const args = Array.from(callNode.arguments)
  if (callDescriptor.invoke === 'direct') {
    return { unresolved: false, args }
  }
  if (callDescriptor.invoke === 'call') {
    return { unresolved: false, args: args.slice(1) }
  }
  if (callDescriptor.invoke === 'apply') {
    if (args.length < 2) return { unresolved: true, args: [] }
    const applyArg = unwrapExpression(args[1])
    if (!ts.isArrayLiteralExpression(applyArg)) {
      return { unresolved: true, args: [] }
    }
    const normalized = []
    for (const element of applyArg.elements) {
      if (ts.isSpreadElement(element) || ts.isOmittedExpression(element)) {
        return { unresolved: true, args: [] }
      }
      normalized.push(element)
    }
    return { unresolved: false, args: normalized }
  }
  return { unresolved: true, args: [] }
}

const extractObjectDestructureRuntimeAliases = (leftNode, namespaceName) => {
  const aliases = []
  const left = unwrapExpression(leftNode)
  if (!ts.isObjectLiteralExpression(left)) return aliases

  for (const prop of left.properties) {
    if (ts.isShorthandPropertyAssignment(prop)) {
      const sourceKey = prop.name.text
      aliases.push({ localName: sourceKey, sourceKey })
      continue
    }
    if (!ts.isPropertyAssignment(prop)) continue
    const sourceKey = getStaticMemberName(prop.name) || (ts.isIdentifier(prop.name) ? prop.name.text : null)
    if (!sourceKey) continue
    const initializer = unwrapExpression(prop.initializer)
    if (!ts.isIdentifier(initializer)) continue
    aliases.push({ localName: initializer.text, sourceKey })
  }
  return aliases
}

const collectRuntimeAnalysisContext = (sourceFile) => {
  const runtimeMethodAliasMap = new Map()
  const runtimeNamespaceAliasMap = new Map()
  const objectLiteralVariableMap = new Map()
  runtimeNamespaceAliasMap.set('Object', 'Object')
  runtimeNamespaceAliasMap.set('Reflect', 'Reflect')

  const visit = (node) => {
    if (ts.isVariableDeclaration(node) && node.initializer) {
      const initializer = unwrapExpression(node.initializer)
      if (ts.isIdentifier(node.name)) {
        const varName = node.name.text
        const namespaceName = resolveRuntimeNamespaceFromExpression(initializer, runtimeNamespaceAliasMap)
        if (namespaceName) {
          runtimeNamespaceAliasMap.set(varName, namespaceName)
        }

        if (ts.isObjectLiteralExpression(initializer)) {
          objectLiteralVariableMap.set(varName, initializer)
        } else if (ts.isIdentifier(initializer) && objectLiteralVariableMap.has(initializer.text)) {
          objectLiteralVariableMap.set(varName, objectLiteralVariableMap.get(initializer.text))
        }

        const runtimeMethod = resolveRuntimeMethodFromExpression(
          initializer,
          runtimeMethodAliasMap,
          runtimeNamespaceAliasMap,
        )
        if (runtimeMethod) {
          runtimeMethodAliasMap.set(varName, runtimeMethod)
        }
      } else if (ts.isObjectBindingPattern(node.name)) {
        const namespaceName = resolveRuntimeNamespaceFromExpression(initializer, runtimeNamespaceAliasMap)
        if (namespaceName) {
          for (const element of node.name.elements) {
            if (!ts.isIdentifier(element.name)) continue
            const localName = element.name.text
            const sourceKey = getBindingElementSourceKey(element)
            if (!sourceKey) continue
            const runtimeMethod = classifyRuntimeMethodName(namespaceName, sourceKey)
            if (runtimeMethod) {
              runtimeMethodAliasMap.set(localName, runtimeMethod)
            }
          }
        }
      }
    } else if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      const rhs = unwrapExpression(node.right)
      const leftExpr = unwrapExpression(node.left)

      if (ts.isIdentifier(leftExpr)) {
        const targetName = leftExpr.text
        const namespaceName = resolveRuntimeNamespaceFromExpression(rhs, runtimeNamespaceAliasMap)
        if (namespaceName) {
          runtimeNamespaceAliasMap.set(targetName, namespaceName)
        }

        if (ts.isObjectLiteralExpression(rhs)) {
          objectLiteralVariableMap.set(targetName, rhs)
        } else if (ts.isIdentifier(rhs) && objectLiteralVariableMap.has(rhs.text)) {
          objectLiteralVariableMap.set(targetName, objectLiteralVariableMap.get(rhs.text))
        }

        const runtimeMethod = resolveRuntimeMethodFromExpression(
          rhs,
          runtimeMethodAliasMap,
          runtimeNamespaceAliasMap,
        )
        if (runtimeMethod) {
          runtimeMethodAliasMap.set(targetName, runtimeMethod)
        }
      } else {
        const namespaceName = resolveRuntimeNamespaceFromExpression(rhs, runtimeNamespaceAliasMap)
        if (namespaceName) {
          const aliases = extractObjectDestructureRuntimeAliases(leftExpr, namespaceName)
          for (const alias of aliases) {
            const runtimeMethod = classifyRuntimeMethodName(namespaceName, alias.sourceKey)
            if (runtimeMethod) {
              runtimeMethodAliasMap.set(alias.localName, runtimeMethod)
            }
          }
        }
      }
    }

    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return { runtimeMethodAliasMap, runtimeNamespaceAliasMap, objectLiteralVariableMap }
}

const analyzeRuntimeObjectLiteralMembers = (objectNode) => {
  const explicitActionInfos = []
  const dynamicInfos = []
  let hasSpread = false

  for (const member of objectNode.properties) {
    if (ts.isSpreadAssignment(member)) {
      hasSpread = true
      continue
    }
    const keyInfo = classifyMemberNameForRuntime(member)
    if (keyInfo.keyClass === 'literal_key') {
      if (actionInteractiveKeySet.has(keyInfo.keyText)) {
        explicitActionInfos.push(keyInfo)
      }
      continue
    }
    dynamicInfos.push(keyInfo)
  }

  return { explicitActionInfos, dynamicInfos, hasSpread }
}

const resolveAssignSourceAnalysis = (sourceArg, sourceFile, runtimeContext) => {
  const source = unwrapExpression(sourceArg)
  if (ts.isObjectLiteralExpression(source)) {
    return {
      ...analyzeRuntimeObjectLiteralMembers(source),
      unresolved: false,
      expressionText: source.getText(sourceFile),
    }
  }

  if (ts.isIdentifier(source)) {
    const mappedObject = runtimeContext.objectLiteralVariableMap.get(source.text) || null
    if (mappedObject) {
      return {
        ...analyzeRuntimeObjectLiteralMembers(mappedObject),
        unresolved: false,
        expressionText: source.text,
      }
    }
    return {
      explicitActionInfos: [],
      dynamicInfos: [],
      hasSpread: false,
      unresolved: true,
      expressionText: source.text,
    }
  }

  return {
    explicitActionInfos: [],
    dynamicInfos: [],
    hasSpread: false,
    unresolved: true,
    expressionText: source ? source.getText(sourceFile) : '',
  }
}

const collectRuntimeDynamicInjectionFindings = (sourceFile, runtimeContext) => {
  const findings = []

  const pushFinding = (type, expressionText) => {
    findings.push({
      type,
      expressionText: normalizeComputedKeyExpr(expressionText || ''),
    })
  }

  const visit = (node) => {
    if (ts.isBinaryExpression(node)) {
      if (isRuntimeWriteOperator(node.operatorToken.kind) && ts.isElementAccessExpression(node.left)) {
        const keyInfo = classifyExpressionKeyNode(node.left.argumentExpression || null)
        if (keyInfo.keyClass !== 'literal_key') {
          pushFinding('ElementAccessExpression-write', keyInfo.expressionText || node.left.getText(sourceFile))
        }
      }
    } else if (ts.isCallExpression(node)) {
      const callDescriptor = resolveRuntimeCallDescriptor(
        node.expression,
        runtimeContext.runtimeMethodAliasMap,
        runtimeContext.runtimeNamespaceAliasMap,
      )
      if (!callDescriptor) {
        ts.forEachChild(node, visit)
        return
      }
      const normalizedCall = normalizeRuntimeCallArguments(node, callDescriptor)

      if (callDescriptor.invoke === 'apply' && normalizedCall.unresolved) {
        pushFinding(`${callDescriptor.method}.apply`, node.getText(sourceFile))
        ts.forEachChild(node, visit)
        return
      }

      if (callDescriptor.method === 'Object.defineProperty') {
        const keyExpr = normalizedCall.args[1] || null
        const keyInfo = classifyExpressionKeyNode(keyExpr)
        if (keyInfo.keyClass !== 'literal_key') {
          pushFinding('Object.defineProperty', keyInfo.expressionText || keyExpr?.getText(sourceFile) || '')
        }
      } else if (callDescriptor.method === 'Object.defineProperties') {
        const descriptorArg = normalizedCall.args[1]
        if (descriptorArg && ts.isObjectLiteralExpression(descriptorArg)) {
          const analysis = analyzeRuntimeObjectLiteralMembers(descriptorArg)
          for (const dynamicInfo of analysis.dynamicInfos) {
            pushFinding('Object.defineProperties', dynamicInfo.expressionText || descriptorArg.getText(sourceFile))
          }
          if (analysis.hasSpread) {
            pushFinding('Object.defineProperties', descriptorArg.getText(sourceFile))
          }
        } else if (descriptorArg) {
          pushFinding('Object.defineProperties', descriptorArg.getText(sourceFile))
        }
      } else if (callDescriptor.method === 'Reflect.set') {
        const keyExpr = normalizedCall.args[1] || null
        const keyInfo = classifyExpressionKeyNode(keyExpr)
        if (keyInfo.keyClass !== 'literal_key') {
          pushFinding('Reflect.set', keyInfo.expressionText || keyExpr?.getText(sourceFile) || '')
        }
      } else if (callDescriptor.method === 'Object.assign') {
        const sourceArgs = normalizedCall.args.slice(1)
        for (const sourceArg of sourceArgs) {
          const analysis = resolveAssignSourceAnalysis(sourceArg, sourceFile, runtimeContext)
          for (const dynamicInfo of analysis.dynamicInfos) {
            pushFinding('Object.assign', dynamicInfo.expressionText || analysis.expressionText)
          }
          if (analysis.hasSpread || analysis.unresolved) {
            pushFinding('Object.assign', analysis.expressionText)
          }
        }
      }
    }

    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return findings
}

const classifyMemberNameForRuntime = (member) => {
  if (ts.isSpreadAssignment(member)) {
    return { keyClass: 'unknown_key', keyText: '', expressionText: member.expression.getText() }
  }

  if (ts.isShorthandPropertyAssignment(member)) {
    return {
      keyClass: 'literal_key',
      keyText: member.name.text.toLowerCase(),
      expressionText: member.name.text,
    }
  }

  if ('name' in member && member.name) {
    return classifyPropertyNameNode(member.name)
  }

  return { keyClass: 'unknown_key', keyText: '', expressionText: '' }
}

const collectRuntimeExplicitActionInjectionFindings = (sourceFile, runtimeContext) => {
  const findings = []

  const pushFinding = (type, expressionText) => {
    findings.push({
      type,
      expressionText: normalizeComputedKeyExpr(expressionText || ''),
    })
  }

  const visit = (node) => {
    if (ts.isBinaryExpression(node) && isRuntimeWriteOperator(node.operatorToken.kind)) {
      if (ts.isElementAccessExpression(node.left)) {
        const keyInfo = classifyExpressionKeyNode(node.left.argumentExpression || null)
        if (keyInfo.keyClass === 'literal_key' && actionInteractiveKeySet.has(keyInfo.keyText)) {
          pushFinding('ElementAccessExpression-explicit-action-write', keyInfo.expressionText || node.left.getText(sourceFile))
        }
      } else if (ts.isPropertyAccessExpression(node.left)) {
        const keyText = node.left.name.text.toLowerCase()
        if (actionInteractiveKeySet.has(keyText)) {
          pushFinding('PropertyAccessExpression-explicit-action-write', node.left.getText(sourceFile))
        }
      }
    } else if (ts.isCallExpression(node)) {
      const callDescriptor = resolveRuntimeCallDescriptor(
        node.expression,
        runtimeContext.runtimeMethodAliasMap,
        runtimeContext.runtimeNamespaceAliasMap,
      )
      if (!callDescriptor) {
        ts.forEachChild(node, visit)
        return
      }
      const normalizedCall = normalizeRuntimeCallArguments(node, callDescriptor)

      if (callDescriptor.invoke === 'apply' && normalizedCall.unresolved) {
        pushFinding(`${callDescriptor.method}.apply-explicit-action`, node.getText(sourceFile))
        ts.forEachChild(node, visit)
        return
      }

      if (callDescriptor.method === 'Object.defineProperty') {
        const keyExpr = normalizedCall.args[1] || null
        const keyInfo = classifyExpressionKeyNode(keyExpr)
        if (keyInfo.keyClass === 'literal_key' && actionInteractiveKeySet.has(keyInfo.keyText)) {
          pushFinding('Object.defineProperty-explicit-action', keyInfo.expressionText || keyExpr?.getText(sourceFile) || '')
        }
      } else if (callDescriptor.method === 'Object.defineProperties') {
        const descriptorArg = normalizedCall.args[1]
        const resolvedDescriptor = ts.isObjectLiteralExpression(descriptorArg)
          ? descriptorArg
          : ts.isIdentifier(descriptorArg)
            ? runtimeContext.objectLiteralVariableMap.get(descriptorArg.text) || null
            : null
        if (resolvedDescriptor) {
          const analysis = analyzeRuntimeObjectLiteralMembers(resolvedDescriptor)
          for (const keyInfo of analysis.explicitActionInfos) {
            pushFinding('Object.defineProperties-explicit-action', keyInfo.expressionText || resolvedDescriptor.getText(sourceFile))
          }
        }
      } else if (callDescriptor.method === 'Reflect.set') {
        const keyExpr = normalizedCall.args[1] || null
        const keyInfo = classifyExpressionKeyNode(keyExpr)
        if (keyInfo.keyClass === 'literal_key' && actionInteractiveKeySet.has(keyInfo.keyText)) {
          pushFinding('Reflect.set-explicit-action', keyInfo.expressionText || keyExpr?.getText(sourceFile) || '')
        }
      } else if (callDescriptor.method === 'Object.assign') {
        const sourceArgs = normalizedCall.args.slice(1)
        for (const sourceArg of sourceArgs) {
          const analysis = resolveAssignSourceAnalysis(sourceArg, sourceFile, runtimeContext)
          for (const keyInfo of analysis.explicitActionInfos) {
            pushFinding('Object.assign-explicit-action', keyInfo.expressionText || analysis.expressionText)
          }
        }
      }
    }

    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return findings
}

const hasSpreadRiskInExplanationChain = (chain) => {
  for (const objectNode of chain) {
    for (const member of objectNode.properties) {
      if (!ts.isSpreadAssignment(member)) continue
      return true
    }
  }
  return false
}

const analyzeStyleProfitAstContracts = (targetPath, content) => {
  const failures = []
  const scriptBlocks = extractScriptBlocksForAst(targetPath, content)
  for (const block of scriptBlocks) {
    const sourceFile = ts.createSourceFile(
      `${path.basename(targetPath)}#${block.label}`,
      block.content,
      ts.ScriptTarget.Latest,
      true,
      block.scriptKind,
    )
    const runtimeContext = collectRuntimeAnalysisContext(sourceFile)
    const objectNodes = collectObjectLiteralsFromSourceFile(sourceFile)

    for (const objectNode of objectNodes) {
      const dynamicKeys = collectDynamicComputedKeyInfos(objectNode)
      if (dynamicKeys.length === 0) continue
      for (const keyInfo of dynamicKeys) {
        const normalizedExpression = normalizeComputedKeyExpr(keyInfo.expressionText || '')
        failures.push(
          `style-profit forbids dynamic or unknown computed keys in object literals; use explicit literal keys（款式利润前端禁止动态或无法静态确认的计算属性键，请使用显式字面量键）: ${targetPath} -> [${normalizedExpression}]`,
        )
      }
    }

    const runtimeDynamicFindings = collectRuntimeDynamicInjectionFindings(sourceFile, runtimeContext)
    for (const finding of runtimeDynamicFindings) {
      failures.push(
        `style-profit forbids runtime dynamic property injection; use explicit literal keys（款式利润前端禁止运行时动态属性注入，请使用显式字面量键）: ${targetPath} -> ${finding.type} [${finding.expressionText}]`,
      )
    }

    const runtimeExplicitActionFindings = collectRuntimeExplicitActionInjectionFindings(sourceFile, runtimeContext)
    for (const finding of runtimeExplicitActionFindings) {
      failures.push(
        `style-profit forbids runtime explicit action-key injection; use object-literal readonly actions only（款式利润前端禁止运行时显式 action key 注入）: ${targetPath} -> ${finding.type} [${finding.expressionText}]`,
      )
    }

    const explanationRanges = collectExplanationRanges(block.content)
    for (const range of explanationRanges) {
      const targetObject = findSmallestContainingObjectNode(objectNodes, range.start, range.end)
      if (!targetObject) continue
      const chain = collectAstObjectChain(targetObject)
      const hasExplanationField = chain.some((node) => objectHasExplanationFieldPhraseAst(node, range.phrase))
      if (!hasExplanationField) continue

      const hasDynamicOrUnknownKey = chain.some((node) => collectDynamicComputedKeyInfos(node).length > 0)
      const hasInteractiveMember = chain.some((node) => objectHasInteractiveMemberAst(node))
      const hasSpreadRisk = hasSpreadRiskInExplanationChain(chain)
      if (hasDynamicOrUnknownKey || hasInteractiveMember || hasSpreadRisk) {
        failures.push(`只读说明文案不得出现在交互入口上下文: ${targetPath} -> ${range.phrase}`)
      }
    }
  }
  return failures
}

const resolveExplanationObjectChain = (content, phrase, range, objectBlocks) => {
  const block = findContainingObjectBlock(objectBlocks, range.start, range.end)
  if (!block) return null
  const chain = collectAncestorObjectBlocks(objectBlocks, block)
  if (chain.length === 0) return null
  const hasExplanationField = chain.some((chainBlock) =>
    hasExplanationFieldForPhraseInSegment(content.slice(chainBlock.start, chainBlock.end), phrase),
  )
  if (!hasExplanationField) return null
  return chain
}

const isReadonlyExplanationObjectContext = (content, phrase, range, objectBlocks) => {
  const chain = resolveExplanationObjectChain(content, phrase, range, objectBlocks)
  if (!chain) return false
  return chain.every((block) => !actionInteractiveMemberRegex.test(content.slice(block.start, block.end)))
}

const hasInteractiveActionObjectForPhrase = (content, phrase, range, objectBlocks) => {
  const chain = resolveExplanationObjectChain(content, phrase, range, objectBlocks)
  if (!chain) return false
  return chain.some((block) => actionInteractiveMemberRegex.test(content.slice(block.start, block.end)))
}

const shouldAllowReadonlyExplanation = (content, matchIndex, matchLength, ranges, objectBlocks) => {
  const start = matchIndex
  const end = matchIndex + matchLength
  const explanationRange = matchExplanationRange(ranges, start, end)
  if (!explanationRange) return false
  if (isReadonlyExplanationObjectContext(content, explanationRange.phrase, explanationRange, objectBlocks)) return true
  if (isInsideUnclosedInteractiveTag(content, start)) return false
  if (hasInteractiveContextInWindow(content, start, matchLength)) return false
  if (hasIdentifierContextForPhrase(content, explanationRange.phrase)) return false
  if (hasInteractiveActionObjectForPhrase(content, explanationRange.phrase, explanationRange, objectBlocks)) return false
  return true
}

export const checkStyleProfitContracts = (projectRootInput = defaultProjectRoot) => {
  const projectRoot = path.resolve(projectRootInput)
  const srcRoot = path.join(projectRoot, 'src')
  const apiRoot = path.join(srcRoot, 'api')
  const viewsRoot = path.join(srcRoot, 'views')
  const routerRoot = path.join(srcRoot, 'router')
  const storesRoot = path.join(srcRoot, 'stores')
  const componentsRoot = path.join(srcRoot, 'components')

  const requiredFiles = [
    path.join(projectRoot, 'src/api/style_profit.ts'),
    path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotList.vue'),
    path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotDetail.vue'),
    path.join(projectRoot, 'src/router/index.ts'),
    path.join(projectRoot, 'src/stores/permission.ts'),
  ]

  const failures = []
  const fail = (message) => failures.push(message)

  if (!existsSync(srcRoot)) {
    fail(`缺少目录: ${srcRoot}`)
    return { ok: false, failures, scannedFiles: 0 }
  }

  for (const targetFile of requiredFiles) {
    if (!existsSync(targetFile)) {
      fail(`缺少契约必需文件: ${targetFile}`)
    }
  }
  if (failures.length > 0) {
    return { ok: false, failures, scannedFiles: 0 }
  }

  const targetFiles = [
    ...collectFiles(apiRoot),
    ...collectFiles(viewsRoot),
    ...collectFiles(routerRoot),
    ...collectFiles(storesRoot),
    ...collectFiles(componentsRoot),
    path.join(srcRoot, 'App.vue'),
    path.join(srcRoot, 'main.ts'),
  ]
    .filter((targetPath, idx, arr) => existsSync(targetPath) && arr.indexOf(targetPath) === idx)
    .sort()

  const requestFile = path.join(projectRoot, 'src/api/request.ts')
  const authFile = path.join(projectRoot, 'src/api/auth.ts')
  const fetchWhitelist = new Set([normalizePath(requestFile), normalizePath(authFile)])

  for (const targetPath of targetFiles) {
    const content = read(targetPath)
    const normalized = normalizePath(targetPath)
    const styleProfitSurface = isStyleProfitSurface(targetPath, content, projectRoot)
    const explanationRanges = collectExplanationRanges(content)
    const objectBlocks = collectObjectBlocks(content)

    if (styleProfitSurface) {
      const astFailures = analyzeStyleProfitAstContracts(targetPath, content)
      for (const message of astFailures) {
        fail(message)
      }
    }

    if (/\bfetch\s*\(/g.test(content) && styleProfitSurface && !fetchWhitelist.has(normalized)) {
      fail(`禁止裸 fetch()，必须走统一 request() 封装: ${targetPath}`)
    }

    if (/\/api\/resource/gi.test(content) && styleProfitSurface) {
      fail(`禁止 ERPNext /api/resource 直连: ${targetPath}`)
    }

    const globalForbiddenRules = [
      {
        regex: /\bstyle_profit:snapshot_create\b/g,
        message: '禁止前端业务文件出现 style_profit:snapshot_create',
      },
      {
        regex: /\bsnapshot_create\b/g,
        message: '禁止前端业务文件出现 snapshot_create',
      },
      {
        regex: /\bcreateStyleProfitSnapshot\b/g,
        message: '禁止前端业务文件出现 createStyleProfitSnapshot',
      },
      {
        regex: /(新建快照|创建快照|生成快照|创建利润快照|生成利润快照|重算利润)/g,
        message: '禁止前端出现创建/生成/重算利润快照文案',
      },
    ]

    for (const rule of globalForbiddenRules) {
      if (rule.regex.test(content)) {
        fail(`${rule.message}: ${targetPath}`)
      }
      rule.regex.lastIndex = 0
    }

    let semanticMatch = semanticWriteEntryRegex.exec(content)
    while (semanticMatch) {
      const matched = semanticMatch[0]
      const index = semanticMatch.index ?? 0
      if (!shouldAllowReadonlyExplanation(content, index, matched.length, explanationRanges, objectBlocks)) {
        fail(`禁止前端出现款式利润中文泛化写入口语义: ${targetPath} -> ${matched}`)
        break
      }
      semanticMatch = semanticWriteEntryRegex.exec(content)
    }
    semanticWriteEntryRegex.lastIndex = 0

    for (const range of explanationRanges) {
      if (isReadonlyExplanationObjectContext(content, range.phrase, range, objectBlocks)) {
        continue
      }
      if (
        isInsideUnclosedInteractiveTag(content, range.start) ||
        hasInteractiveContextInWindow(content, range.start, range.end - range.start) ||
        hasIdentifierContextForPhrase(content, range.phrase) ||
        hasInteractiveActionObjectForPhrase(content, range.phrase, range, objectBlocks)
      ) {
        fail(`只读说明文案不得出现在交互入口上下文: ${targetPath} -> ${range.phrase}`)
        break
      }
    }

    for (const rule of semanticIdentifierRegexes) {
      if (rule.test(content)) {
        fail(`禁止前端出现款式利润写入口函数/标识符: ${targetPath}`)
      }
      rule.lastIndex = 0
    }

    for (const rule of semanticRouteRegexes) {
      if (rule.test(content)) {
        fail(`禁止前端出现款式利润写入口路由: ${targetPath}`)
      }
      rule.lastIndex = 0
    }

    if (styleProfitSurface) {
      if (/\bidempotency_key\b/g.test(content)) {
        fail(`禁止 style-profit 业务面出现 idempotency_key: ${targetPath}`)
      }
      if (/method\s*:\s*['\"]POST['\"]/g.test(content)) {
        fail(`禁止 style-profit 业务面出现 POST 写接口: ${targetPath}`)
      }
    }
  }

  const listViewContent = read(path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotList.vue'))
  if (!listViewContent.includes("loadModuleActions('style_profit')")) {
    fail('列表页必须加载 style_profit 模块权限')
  }
  if (!listViewContent.includes('if (!canRead.value)')) {
    fail('列表页缺少 canRead 前置阻断')
  }
  if (!listViewContent.includes('if (!hasRequiredScope())')) {
    fail('列表页必须在 company/item_code 为空时阻断请求')
  }

  const detailViewContent = read(path.join(projectRoot, 'src/views/style_profit/StyleProfitSnapshotDetail.vue'))
  if (!detailViewContent.includes("loadModuleActions('style_profit')")) {
    fail('详情页必须加载 style_profit 模块权限')
  }
  if (!detailViewContent.includes('if (!canRead.value)')) {
    fail('详情页缺少 canRead 前置阻断')
  }
  if (!detailViewContent.includes('存在未解析来源，请财务复核后使用')) {
    fail('详情页缺少 unresolved_count 风险提示')
  }
  if (!detailViewContent.includes('审计信息（仅供审计复核）')) {
    fail('详情页必须提供审计信息折叠区')
  }

  const permissionStoreContent = read(path.join(projectRoot, 'src/stores/permission.ts'))
  if (/snapshot_create\s*:/g.test(permissionStoreContent)) {
    fail('permission store 禁止映射 snapshot_create 按钮权限')
  }

  const routerContent = read(path.join(projectRoot, 'src/router/index.ts'))
  if (!routerContent.includes("path: '/reports/style-profit'")) {
    fail('路由缺少 /reports/style-profit')
  }
  if (!routerContent.includes("path: '/reports/style-profit/detail'")) {
    fail('路由缺少 /reports/style-profit/detail')
  }
  if (/path:\s*['\"]\/reports\/style-profit\/create['\"]/g.test(routerContent)) {
    fail('路由禁止出现 /reports/style-profit/create')
  }

  const requestContent = read(requestFile)
  if (!/const response = await fetch\(/.test(requestContent)) {
    fail('src/api/request.ts 必须保留统一 fetch 封装')
  }
  if (!requestContent.includes("result.set('Authorization'")) {
    fail('src/api/request.ts 必须保留 Authorization 组装')
  }

  const apiContent = read(path.join(projectRoot, 'src/api/style_profit.ts'))
  if (!apiContent.includes('fetchStyleProfitSnapshots')) {
    fail('src/api/style_profit.ts 缺少 fetchStyleProfitSnapshots')
  }
  if (!apiContent.includes('fetchStyleProfitSnapshotDetail')) {
    fail('src/api/style_profit.ts 缺少 fetchStyleProfitSnapshotDetail')
  }

  return {
    ok: failures.length === 0,
    failures,
    scannedFiles: targetFiles.length,
  }
}

const runCli = () => {
  const { projectRoot } = parseCliArgs(process.argv.slice(2))
  const result = checkStyleProfitContracts(projectRoot)
  if (!result.ok) {
    console.error('Style-profit contract check failed:')
    for (const [idx, message] of result.failures.entries()) {
      console.error(`${idx + 1}. ${message}`)
    }
    process.exit(1)
  }
  console.log('Style-profit contract check passed.')
  console.log(`Scanned files: ${result.scannedFiles}`)
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  runCli()
}
