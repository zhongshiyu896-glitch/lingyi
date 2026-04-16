import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'
import {
  FRONTEND_WRITE_GUARD_COMMON_RULES,
  runContractCli,
  runFrontendContractEngine,
  validateModuleContractConfig,
} from './frontend-contract-engine.mjs'

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
    const literalText = resolveStaticStringValue(expr)
    if (literalText !== null) {
      return {
        keyClass: 'literal_key',
        keyText: `${literalText}`.toLowerCase(),
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

const resolveStaticStringValue = (node) => {
  const target = unwrapExpression(node)
  if (!target) return null

  if (
    ts.isStringLiteral(target) ||
    ts.isNoSubstitutionTemplateLiteral(target) ||
    ts.isNumericLiteral(target)
  ) {
    return `${target.text}`
  }

  if (ts.isTemplateExpression(target)) {
    let text = target.head.text
    for (const span of target.templateSpans) {
      const exprValue = resolveStaticStringValue(span.expression)
      if (exprValue === null) return null
      text += `${exprValue}${span.literal.text}`
    }
    return text
  }

  if (ts.isBinaryExpression(target) && target.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    const left = resolveStaticStringValue(target.left)
    const right = resolveStaticStringValue(target.right)
    if (left === null || right === null) return null
    return `${left}${right}`
  }

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

  const literalText = resolveStaticStringValue(expressionNode)
  if (literalText !== null) {
    return {
      keyClass: 'literal_key',
      keyText: literalText.toLowerCase(),
      expressionText: expressionNode.getText ? expressionNode.getText() : `${literalText}`,
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

const runtimeArrayMutatingMethodNameSet = new Set([
  'push',
  'pop',
  'shift',
  'unshift',
  'splice',
  'sort',
  'reverse',
  'fill',
  'copyWithin',
])

const runtimeArrayIterationMethodDescriptorMap = new Map([
  ['forEach', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['map', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['some', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['every', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['filter', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['find', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['findIndex', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['findLast', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['findLastIndex', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['flatMap', { callback_argument_index: 0, current_item_parameter_index: 0 }],
  ['reduce', { callback_argument_index: 0, current_item_parameter_index: 1 }],
  ['reduceRight', { callback_argument_index: 0, current_item_parameter_index: 1 }],
])

const runtimeArrayStatusRank = {
  clean: 0,
  tainted: 1,
  escaped: 2,
  unknown: 3,
}

const unwrapExpression = (node) => {
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
    if (ts.isPartiallyEmittedExpression(current)) {
      current = current.expression
      continue
    }
    break
  }
  return current
}

const normalizeRuntimeCalleeExpression = (node) => {
  let current = unwrapExpression(node)
  while (current && ts.isBinaryExpression(current) && current.operatorToken.kind === ts.SyntaxKind.CommaToken) {
    current = unwrapExpression(current.right)
  }
  return current
}

const getStaticLiteralText = (node) => {
  if (!node) return null
  return resolveStaticStringValue(node)
}

const getStaticMemberName = (node) => {
  const target = unwrapExpression(node)
  if (!target) return null
  if (ts.isPropertyAccessExpression(target)) return target.name.text
  if (ts.isElementAccessExpression(target)) return getStaticLiteralText(target.argumentExpression || null)
  return null
}

const isStaticArrayNamespaceExpression = (expression, depth = 0) => {
  if (!expression || depth > 8) return false
  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target) return false

  if (ts.isIdentifier(target)) {
    return target.text === 'Array'
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (memberName !== 'Array') return false
    const baseExpr = unwrapExpression(target.expression)
    return Boolean(ts.isIdentifier(baseExpr) && (baseExpr.text === 'globalThis' || baseExpr.text === 'window'))
  }

  if (ts.isConditionalExpression(target)) {
    const whenTrue = isStaticArrayNamespaceExpression(target.whenTrue, depth + 1)
    const whenFalse = isStaticArrayNamespaceExpression(target.whenFalse, depth + 1)
    return whenTrue && whenFalse
  }

  return false
}

const isStaticArrayPrototypeExpression = (expression, depth = 0) => {
  if (!expression || depth > 8) return false
  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target) return false

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (memberName !== 'prototype') return false
    return isStaticArrayNamespaceExpression(target.expression, depth + 1)
  }

  if (ts.isConditionalExpression(target)) {
    const whenTrue = isStaticArrayPrototypeExpression(target.whenTrue, depth + 1)
    const whenFalse = isStaticArrayPrototypeExpression(target.whenFalse, depth + 1)
    return whenTrue && whenFalse
  }

  return false
}

const resolveStaticArrayPrototypeIterationMethodName = (expression, depth = 0) => {
  if (!expression || depth > 8) return null
  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target) return null

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (!memberName || !runtimeArrayIterationMethodDescriptorMap.has(memberName)) return null
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

const classifyRuntimeMethodName = (objectName, methodName) => {
  if (objectName === 'Object' && methodName === 'defineProperty') return 'Object.defineProperty'
  if (objectName === 'Object' && methodName === 'defineProperties') return 'Object.defineProperties'
  if (objectName === 'Object' && methodName === 'assign') return 'Object.assign'
  if (objectName === 'URL' && methodName === 'createObjectURL') return 'URL.createObjectURL'
  if (objectName === 'Reflect' && methodName === 'set') return 'Reflect.set'
  if (objectName === 'Reflect' && methodName === 'apply') return 'Reflect.apply'
  if (objectName === 'Reflect' && methodName === 'construct') return 'Reflect.construct'
  if (objectName === 'Reflect' && methodName === 'get') return 'Reflect.get'
  return null
}

const resolveRuntimeNamespaceFromExpression = (expression, runtimeNamespaceAliasMap = new Map()) => {
  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target) return null

  if (ts.isIdentifier(target)) {
    if (target.text === 'Object' || target.text === 'Reflect' || target.text === 'URL') return target.text
    return runtimeNamespaceAliasMap.get(target.text) || null
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const namespaceName = getStaticMemberName(target)
    if (namespaceName !== 'Object' && namespaceName !== 'Reflect' && namespaceName !== 'URL') return null
    const baseExpr = target.expression
    const base = unwrapExpression(baseExpr)
    if (ts.isIdentifier(base) && (base.text === 'globalThis' || base.text === 'window')) {
      return namespaceName
    }
  }

  if (ts.isConditionalExpression(target)) {
    const whenTrue = resolveRuntimeNamespaceFromExpression(target.whenTrue, runtimeNamespaceAliasMap)
    const whenFalse = resolveRuntimeNamespaceFromExpression(target.whenFalse, runtimeNamespaceAliasMap)
    if (whenTrue && whenFalse && whenTrue === whenFalse) {
      return whenTrue
    }
  }

  return null
}

const resolveGlobalContainerFromExpression = (expression, runtimeGlobalContainerAliasMap = new Map()) => {
  const target = unwrapExpression(expression)
  if (!target) return null
  if (ts.isIdentifier(target)) {
    if (target.text === 'globalThis' || target.text === 'window') return target.text
    return runtimeGlobalContainerAliasMap.get(target.text) || null
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

const classifyDestructureSourceKeyNode = (nameNode) => {
  if (!nameNode) {
    return { keyClass: 'unknown_key', keyText: '', expressionText: '' }
  }

  if (ts.isComputedPropertyName(nameNode)) {
    const literalText = getStaticLiteralText(nameNode.expression)
    if (literalText !== null) {
      return {
        keyClass: 'literal_key',
        keyText: literalText,
        expressionText: nameNode.expression.getText(),
      }
    }
    return {
      keyClass: 'dynamic_computed_key',
      keyText: '',
      expressionText: nameNode.expression.getText(),
    }
  }

  if (ts.isIdentifier(nameNode) || ts.isStringLiteral(nameNode) || ts.isNumericLiteral(nameNode)) {
    return {
      keyClass: 'literal_key',
      keyText: `${nameNode.text}`,
      expressionText: nameNode.getText(),
    }
  }

  return {
    keyClass: 'unknown_key',
    keyText: '',
    expressionText: nameNode.getText ? nameNode.getText() : '',
  }
}

const getStaticArrayIndex = (expressionNode) => {
  const target = unwrapExpression(expressionNode)
  if (!target) return null
  if (ts.isNumericLiteral(target)) {
    const parsed = Number(target.text)
    return Number.isInteger(parsed) && parsed >= 0 ? parsed : null
  }
  if (ts.isStringLiteral(target) || ts.isNoSubstitutionTemplateLiteral(target)) {
    if (/^\d+$/.test(target.text)) return Number(target.text)
  }
  return null
}

const resolveRuntimeWorkerConstructorFromExpression = (
  expression,
  runtimeConstructorAliasMap = new Map(),
  runtimeUnknownConstructorAliasMap = new Map(),
  runtimeConstructorFactoryAliasMap = new Map(),
  runtimeUnknownConstructorFactoryAliasMap = new Map(),
  runtimeNamespaceAliasMap = new Map(),
  runtimeArrayConstructorContainerMap = new Map(),
  runtimeObjectConstructorContainerMap = new Map(),
  runtimeGlobalContainerAliasMap = new Map(),
  depth = 0,
) => {
  const buildResolved = (constructorName, boundArgs = []) => ({
    constructorName,
    boundArgs,
    unresolved: false,
  })
  if (depth > 12) {
    return {
      constructorName: null,
      boundArgs: [],
      unresolved: true,
      expressionText: expression?.getText ? expression.getText() : '',
    }
  }

  const resolveCtorFromFunctionLike = (functionLikeNode) => {
    const targetFunction = unwrapExpression(functionLikeNode)
    if (!targetFunction) return null
    if (!ts.isFunctionExpression(targetFunction) && !ts.isArrowFunction(targetFunction)) return null

    let returnExpr = null
    if (ts.isArrowFunction(targetFunction) && !ts.isBlock(targetFunction.body)) {
      returnExpr = targetFunction.body
    } else if (ts.isBlock(targetFunction.body)) {
      let found = null
      for (const statement of targetFunction.body.statements) {
        if (ts.isEmptyStatement(statement)) continue
        if (ts.isReturnStatement(statement)) {
          if (!statement.expression || found) {
            return {
              constructorName: null,
              boundArgs: [],
              unresolved: true,
              expressionText: targetFunction.getText ? targetFunction.getText() : '',
            }
          }
          found = statement.expression
          continue
        }
        return null
      }
      returnExpr = found
    }

    if (!returnExpr) return null
    return resolveRuntimeWorkerConstructorFromExpression(
      returnExpr,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
      depth + 1,
    )
  }

  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target) return null

  if (ts.isIdentifier(target)) {
    const direct = classifyRuntimeWorkerConstructorName(target.text)
    if (direct) return buildResolved(direct, [])
    const aliasResolved = runtimeConstructorAliasMap.get(target.text)
    if (aliasResolved?.constructorName) return buildResolved(aliasResolved.constructorName, aliasResolved.boundArgs || [])
    const factoryResolved = runtimeConstructorFactoryAliasMap.get(target.text)
    if (factoryResolved?.constructorName) {
      return buildResolved(factoryResolved.constructorName, factoryResolved.boundArgs || [])
    }
    if (runtimeUnknownConstructorAliasMap.has(target.text)) {
      return {
        constructorName: null,
        boundArgs: [],
        unresolved: true,
        expressionText: runtimeUnknownConstructorAliasMap.get(target.text) || target.text,
      }
    }
    if (runtimeUnknownConstructorFactoryAliasMap.has(target.text)) {
      return {
        constructorName: null,
        boundArgs: [],
        unresolved: true,
        expressionText: runtimeUnknownConstructorFactoryAliasMap.get(target.text) || target.text,
      }
    }
    return null
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    const baseExpr = unwrapExpression(target.expression)

    if (memberName) {
      const workerName = classifyRuntimeWorkerConstructorName(memberName)
      if (workerName) {
        const globalContainer = resolveGlobalContainerFromExpression(baseExpr, runtimeGlobalContainerAliasMap)
        if (globalContainer) {
          return buildResolved(workerName, [])
        }
      }
    } else {
      const globalContainer = resolveGlobalContainerFromExpression(baseExpr, runtimeGlobalContainerAliasMap)
      if (globalContainer) {
        return {
          constructorName: null,
          boundArgs: [],
          unresolved: true,
          expressionText: target.getText ? target.getText() : '',
        }
      }
    }

    if (ts.isIdentifier(baseExpr)) {
      const baseName = baseExpr.text
      const arrayContainer = runtimeArrayConstructorContainerMap.get(baseName) || null
      if (arrayContainer) {
        if (arrayContainer.unresolved) {
          return {
            constructorName: null,
            boundArgs: [],
            unresolved: true,
            expressionText: target.getText ? target.getText() : '',
          }
        }
        if (ts.isElementAccessExpression(target)) {
          const index = getStaticArrayIndex(target.argumentExpression || null)
          if (index === null || index < 0 || index >= arrayContainer.constructors.length) {
            return {
              constructorName: null,
              boundArgs: [],
              unresolved: true,
              expressionText: target.getText ? target.getText() : '',
            }
          }
          const resolvedCtor = arrayContainer.constructors[index] || null
          if (resolvedCtor) {
            return buildResolved(resolvedCtor.constructorName, resolvedCtor.boundArgs || [])
          }
          return {
            constructorName: null,
            boundArgs: [],
            unresolved: true,
            expressionText: target.getText ? target.getText() : '',
          }
        }
      }

      const objectContainer = runtimeObjectConstructorContainerMap.get(baseName) || null
      if (objectContainer) {
        if (objectContainer.unresolved) {
          return {
            constructorName: null,
            boundArgs: [],
            unresolved: true,
            expressionText: target.getText ? target.getText() : '',
          }
        }
        const normalizedMemberName = memberName ? memberName.toLowerCase() : null
        if (!normalizedMemberName || !objectContainer.constructorsByKey.has(normalizedMemberName)) {
          return {
            constructorName: null,
            boundArgs: [],
            unresolved: true,
            expressionText: target.getText ? target.getText() : '',
          }
        }
        const resolvedCtor = objectContainer.constructorsByKey.get(normalizedMemberName) || null
        if (resolvedCtor) {
          return buildResolved(resolvedCtor.constructorName, resolvedCtor.boundArgs || [])
        }
        return {
          constructorName: null,
          boundArgs: [],
          unresolved: true,
          expressionText: target.getText ? target.getText() : '',
        }
      }
    }

    return null
  }

  if (ts.isCallExpression(target)) {
    const callee = normalizeRuntimeCalleeExpression(target.expression)
    if (callee && (ts.isPropertyAccessExpression(callee) || ts.isElementAccessExpression(callee))) {
      const memberName = getStaticMemberName(callee)
      if (memberName === 'bind') {
        const baseCtor = resolveRuntimeWorkerConstructorFromExpression(
          callee.expression,
          runtimeConstructorAliasMap,
          runtimeUnknownConstructorAliasMap,
          runtimeConstructorFactoryAliasMap,
          runtimeUnknownConstructorFactoryAliasMap,
          runtimeNamespaceAliasMap,
          runtimeArrayConstructorContainerMap,
          runtimeObjectConstructorContainerMap,
          runtimeGlobalContainerAliasMap,
          depth + 1,
        )
        if (baseCtor?.constructorName && !baseCtor.unresolved) {
          const bindArgs = target.arguments.slice(1)
          return buildResolved(baseCtor.constructorName, [...(baseCtor.boundArgs || []), ...bindArgs])
        }
        if (baseCtor?.unresolved) {
          return {
            constructorName: null,
            boundArgs: [],
            unresolved: true,
            expressionText: target.getText ? target.getText() : '',
          }
        }
      }
    }

    const calleeResolvedByFactory = resolveRuntimeWorkerConstructorFromExpression(
      target.expression,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
      depth + 1,
    )
    if (calleeResolvedByFactory?.constructorName && !calleeResolvedByFactory.unresolved) {
      return buildResolved(calleeResolvedByFactory.constructorName, calleeResolvedByFactory.boundArgs || [])
    }
    if (calleeResolvedByFactory?.unresolved) {
      return {
        constructorName: null,
        boundArgs: [],
        unresolved: true,
        expressionText: calleeResolvedByFactory.expressionText || (target.getText ? target.getText() : ''),
      }
    }

    const functionLikeResolved = resolveCtorFromFunctionLike(target.expression)
    if (functionLikeResolved?.constructorName && !functionLikeResolved.unresolved) {
      return buildResolved(functionLikeResolved.constructorName, functionLikeResolved.boundArgs || [])
    }
    if (functionLikeResolved?.unresolved) {
      return functionLikeResolved
    }
  }

  if (ts.isConditionalExpression(target)) {
    const whenTrue = resolveRuntimeWorkerConstructorFromExpression(
      target.whenTrue,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
      depth + 1,
    )
    const whenFalse = resolveRuntimeWorkerConstructorFromExpression(
      target.whenFalse,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
      depth + 1,
    )
    if (
      whenTrue &&
      whenFalse &&
      !whenTrue.unresolved &&
      !whenFalse.unresolved &&
      whenTrue.constructorName &&
      whenTrue.constructorName === whenFalse.constructorName &&
      (whenTrue.boundArgs?.length || 0) === 0 &&
      (whenFalse.boundArgs?.length || 0) === 0
    ) {
      return whenTrue
    }
    if (whenTrue || whenFalse) {
      return {
        constructorName: null,
        boundArgs: [],
        unresolved: true,
        expressionText: target.getText ? target.getText() : '',
      }
    }
  }

  return null
}

const resolveRuntimeMethodFromExpression = (
  expression,
  runtimeMethodAliasMap = new Map(),
  runtimeNamespaceAliasMap = new Map(),
  runtimeArrayMethodContainerMap = new Map(),
  runtimeObjectMethodContainerMap = new Map(),
  runtimeGlobalContainerAliasMap = new Map(),
) => {
  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target) return null

  if (ts.isIdentifier(target)) {
    const aliasResolved = runtimeMethodAliasMap.get(target.text)
    if (aliasResolved) return aliasResolved
    return classifyRuntimeCodegenGlobalName(target.text)
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const baseExpr = unwrapExpression(target.expression)
    if (ts.isIdentifier(baseExpr)) {
      const containerName = baseExpr.text
      const objectContainer = runtimeObjectMethodContainerMap.get(containerName) || null
      if (objectContainer && !objectContainer.unresolved) {
        const keyName = getStaticMemberName(target)
        const normalizedKeyName = keyName ? keyName.toLowerCase() : null
        if (normalizedKeyName && objectContainer.methodsByKey.has(normalizedKeyName)) {
          return objectContainer.methodsByKey.get(normalizedKeyName) || null
        }
      }

      if (ts.isElementAccessExpression(target)) {
        const arrayContainer = runtimeArrayMethodContainerMap.get(containerName) || null
        if (arrayContainer && !arrayContainer.unresolved) {
          const index = getStaticArrayIndex(target.argumentExpression || null)
          if (index !== null && index >= 0 && index < arrayContainer.methods.length) {
            return arrayContainer.methods[index] || null
          }
        }
      }
    }

    const memberName = getStaticMemberName(target)
    if (!memberName) return null
    if (memberName === 'constructor') return 'Global.Function'
    const namespaceName = resolveRuntimeNamespaceFromExpression(baseExpr, runtimeNamespaceAliasMap)
    if (namespaceName) {
      return classifyRuntimeMethodName(namespaceName, memberName)
    }
    const globalContainer = resolveGlobalContainerFromExpression(baseExpr, runtimeGlobalContainerAliasMap)
    if (globalContainer) {
      return classifyRuntimeCodegenGlobalName(memberName)
    }
    return null
  }

  if (ts.isCallExpression(target)) {
    const runtimeContext = {
      runtimeMethodAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayMethodContainerMap,
      runtimeObjectMethodContainerMap,
      runtimeGlobalContainerAliasMap,
    }
    const reflectGetResolved = resolveRuntimeReflectGetCall(target, runtimeContext)
    if (reflectGetResolved?.method) {
      return reflectGetResolved.method
    }

    const bindMemberName = getStaticMemberName(target.expression)
    if (bindMemberName !== 'bind') return null
    const bindBaseExpr =
      ts.isPropertyAccessExpression(target.expression) || ts.isElementAccessExpression(target.expression)
        ? target.expression.expression
        : null
    if (!bindBaseExpr) return null
    return resolveRuntimeMethodFromExpression(
      bindBaseExpr,
      runtimeMethodAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayMethodContainerMap,
      runtimeObjectMethodContainerMap,
      runtimeGlobalContainerAliasMap,
    )
  }

  if (ts.isConditionalExpression(target)) {
    const whenTrue = resolveRuntimeMethodFromExpression(
      target.whenTrue,
      runtimeMethodAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayMethodContainerMap,
      runtimeObjectMethodContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    const whenFalse = resolveRuntimeMethodFromExpression(
      target.whenFalse,
      runtimeMethodAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayMethodContainerMap,
      runtimeObjectMethodContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    if (whenTrue && whenFalse && whenTrue === whenFalse) return whenTrue
  }

  return null
}

const runtimeMutatorMethodSet = new Set([
  'Object.defineProperty',
  'Object.defineProperties',
  'Object.assign',
  'Reflect.set',
])
const runtimeWorkerConstructorNameSet = new Set(['Worker', 'SharedWorker'])
const runtimeKnownSafeConstructorNameSet = new Set([
  'Date',
  'URL',
  'Error',
  'RegExp',
  'Map',
  'Set',
  'TypeError',
  'RangeError',
  'ReferenceError',
  'SyntaxError',
])
const runtimeBlobUrlMethodSet = new Set(['URL.createObjectURL'])
const runtimeWorkerConstructorMethodSet = new Set(['Reflect.construct'])
const runtimeMutatorSourceMethodSet = new Set([
  'Object.defineProperty',
  'Object.defineProperties',
  'Object.assign',
  'Reflect.set',
  'Reflect.apply',
])
const runtimeCodegenSourceMethodSet = new Set(['Global.eval', 'Global.Function'])
const runtimeTimerMethodSet = new Set(['Global.setTimeout', 'Global.setInterval'])

const runtimeMutatorMemberNameSet = new Set([
  'defineProperty',
  'defineProperties',
  'assign',
  'createObjectURL',
  'set',
  'apply',
  'construct',
  'get',
])

const classifyRuntimeWorkerConstructorName = (name) => {
  if (!name) return null
  if (runtimeWorkerConstructorNameSet.has(name)) return name
  return null
}

const resolveKnownSafeConstructorFromExpression = (expression, runtimeGlobalContainerAliasMap = new Map()) => {
  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target) return null

  if (ts.isIdentifier(target) && runtimeKnownSafeConstructorNameSet.has(target.text)) {
    return target.text
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (!memberName || !runtimeKnownSafeConstructorNameSet.has(memberName)) return null
    const globalContainer = resolveGlobalContainerFromExpression(target.expression, runtimeGlobalContainerAliasMap)
    if (globalContainer) return memberName
    return null
  }

  if (ts.isConditionalExpression(target)) {
    const whenTrue = resolveKnownSafeConstructorFromExpression(target.whenTrue, runtimeGlobalContainerAliasMap)
    const whenFalse = resolveKnownSafeConstructorFromExpression(target.whenFalse, runtimeGlobalContainerAliasMap)
    if (whenTrue && whenFalse && whenTrue === whenFalse) return whenTrue
  }

  return null
}

const canRuntimeMemberHitMethodSet = (memberName, methodSet = runtimeMutatorMethodSet) => {
  if (!memberName) return false
  const globalMethod = classifyRuntimeCodegenGlobalName(memberName)
  if (globalMethod && methodSet.has(globalMethod)) return true
  return ['Object', 'Reflect', 'URL'].some((namespaceName) => {
    const method = classifyRuntimeMethodName(namespaceName, memberName)
    return Boolean(method && methodSet.has(method))
  })
}

const classifyRuntimeCodegenGlobalName = (name) => {
  if (name === 'eval') return 'Global.eval'
  if (name === 'Function') return 'Global.Function'
  if (name === 'setTimeout') return 'Global.setTimeout'
  if (name === 'setInterval') return 'Global.setInterval'
  return null
}

const resolveRuntimeReflectGetCall = (callNode, runtimeContext) => {
  const runtimeMethodAliasMap = runtimeContext.runtimeMethodAliasMap || new Map()
  const runtimeNamespaceAliasMap = runtimeContext.runtimeNamespaceAliasMap || new Map()
  const runtimeGlobalContainerAliasMap = runtimeContext.runtimeGlobalContainerAliasMap || new Map()
  const runtimeArrayMethodContainerMap = runtimeContext.runtimeArrayMethodContainerMap || new Map()
  const runtimeObjectMethodContainerMap = runtimeContext.runtimeObjectMethodContainerMap || new Map()

  const callTarget = normalizeRuntimeCalleeExpression(callNode.expression)
  if (!callTarget) return null
  const callMethod = resolveRuntimeMethodFromExpression(
    callTarget,
    runtimeMethodAliasMap,
    runtimeNamespaceAliasMap,
    runtimeArrayMethodContainerMap,
    runtimeObjectMethodContainerMap,
    runtimeGlobalContainerAliasMap,
  )
  if (callMethod !== 'Reflect.get') return null

  const targetExpr = callNode.arguments[0] || null
  const keyExpr = callNode.arguments[1] || null
  const namespaceName = resolveRuntimeNamespaceFromExpression(targetExpr, runtimeNamespaceAliasMap)
  const keyText = getStaticLiteralText(keyExpr)

  if (!namespaceName) {
    return {
      method: null,
      unresolved: true,
      expressionText: keyExpr?.getText?.() || callNode.getText(),
    }
  }

  if (keyText === null) {
    return {
      method: null,
      unresolved: true,
      expressionText: keyExpr?.getText?.() || callNode.getText(),
    }
  }

  const runtimeMethod = classifyRuntimeMethodName(namespaceName, keyText)
  if (runtimeMethod) {
    return {
      method: runtimeMethod,
      unresolved: false,
      expressionText: `${namespaceName}.${keyText}`,
    }
  }

  return {
    method: null,
    unresolved: true,
    expressionText: `${namespaceName}[${keyText}]`,
  }
}

const resolveRuntimeCallDescriptor = (callNode, runtimeContext, methodSet = runtimeMutatorMethodSet) => {
  const runtimeMethodAliasMap = runtimeContext.runtimeMethodAliasMap || new Map()
  const runtimeNamespaceAliasMap = runtimeContext.runtimeNamespaceAliasMap || new Map()
  const runtimeGlobalContainerAliasMap = runtimeContext.runtimeGlobalContainerAliasMap || new Map()
  const runtimeArrayMethodContainerMap = runtimeContext.runtimeArrayMethodContainerMap || new Map()
  const runtimeObjectMethodContainerMap = runtimeContext.runtimeObjectMethodContainerMap || new Map()
  const runtimeUnknownNamespaceAliasMap = runtimeContext.runtimeUnknownNamespaceAliasMap || new Map()
  const target = normalizeRuntimeCalleeExpression(callNode.expression)
  if (!target) return null

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    if (memberName === 'call' || memberName === 'apply') {
      const baseMethod = resolveRuntimeMethodFromExpression(
        target.expression,
        runtimeMethodAliasMap,
        runtimeNamespaceAliasMap,
        runtimeArrayMethodContainerMap,
        runtimeObjectMethodContainerMap,
        runtimeGlobalContainerAliasMap,
      )
      if (baseMethod && methodSet.has(baseMethod)) {
        return { method: baseMethod, invoke: memberName }
      }
    }
  }

  const directMethod = resolveRuntimeMethodFromExpression(
    target,
    runtimeMethodAliasMap,
    runtimeNamespaceAliasMap,
    runtimeArrayMethodContainerMap,
    runtimeObjectMethodContainerMap,
    runtimeGlobalContainerAliasMap,
  )
  if (directMethod === 'Reflect.apply') {
    const reflectApplyTarget = callNode.arguments[0] || null
    const reflectApplyMethod = reflectApplyTarget
      ? resolveRuntimeMethodFromExpression(
          reflectApplyTarget,
          runtimeMethodAliasMap,
          runtimeNamespaceAliasMap,
          runtimeArrayMethodContainerMap,
          runtimeObjectMethodContainerMap,
          runtimeGlobalContainerAliasMap,
        )
      : null
    if (reflectApplyMethod && methodSet.has(reflectApplyMethod)) {
      return { method: reflectApplyMethod, invoke: 'reflect_apply' }
    }
    if (reflectApplyMethod) return null
    if (reflectApplyTarget && resolveStaticArrayPrototypeIterationMethodName(reflectApplyTarget)) {
      return null
    }
    return { method: null, invoke: 'reflect_apply', unresolvedTarget: true }
  }
  if (directMethod === 'Reflect.get') {
    const reflectGetResolved = resolveRuntimeReflectGetCall(callNode, runtimeContext)
    if (reflectGetResolved?.method && methodSet.has(reflectGetResolved.method)) {
      return { method: reflectGetResolved.method, invoke: 'reflect_get' }
    }
    if (reflectGetResolved?.unresolved) {
      return { method: null, invoke: 'reflect_get', unresolvedTarget: true }
    }
  }

  if (directMethod && methodSet.has(directMethod)) {
    return { method: directMethod, invoke: 'direct' }
  }

  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const memberName = getStaticMemberName(target)
    const baseExpr = unwrapExpression(target.expression)
    const namespaceName = resolveRuntimeNamespaceFromExpression(baseExpr, runtimeNamespaceAliasMap)
    if (namespaceName && !memberName) {
      return { method: null, invoke: 'unknown_namespace_member', unresolvedTarget: true }
    }
    const globalContainer = resolveGlobalContainerFromExpression(baseExpr, runtimeGlobalContainerAliasMap)
    if (globalContainer && !memberName) {
      return { method: null, invoke: 'unknown_global_namespace_member', unresolvedTarget: true }
    }

    if (ts.isIdentifier(baseExpr)) {
      const baseName = baseExpr.text
      if (memberName && runtimeUnknownNamespaceAliasMap.has(baseName) && runtimeMutatorMemberNameSet.has(memberName)) {
        if (!canRuntimeMemberHitMethodSet(memberName, methodSet)) {
          return null
        }
        return { method: null, invoke: 'unknown_namespace_alias', unresolvedTarget: true }
      }

      const objectContainer = runtimeObjectMethodContainerMap.get(baseName) || null
      if (objectContainer) {
        if (objectContainer.unresolved) {
          return { method: null, invoke: 'object_container_unresolved', unresolvedTarget: true }
        }
        const normalizedMemberName = memberName ? memberName.toLowerCase() : null
        if (!normalizedMemberName || !objectContainer.methodsByKey.has(normalizedMemberName)) {
          return { method: null, invoke: 'object_container_unknown_member', unresolvedTarget: true }
        }
      }

      if (ts.isElementAccessExpression(target)) {
        const arrayContainer = runtimeArrayMethodContainerMap.get(baseName) || null
        if (arrayContainer) {
          if (arrayContainer.unresolved) {
            return { method: null, invoke: 'array_container_unresolved', unresolvedTarget: true }
          }
          const index = getStaticArrayIndex(target.argumentExpression || null)
          if (index === null || index < 0 || index >= arrayContainer.methods.length) {
            return { method: null, invoke: 'array_container_unknown_index', unresolvedTarget: true }
          }
          if (!arrayContainer.methods[index]) {
            return { method: null, invoke: 'array_container_unknown_method', unresolvedTarget: true }
          }
        }
      }
    }
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
  if (callDescriptor.invoke === 'reflect_apply') {
    if (callDescriptor.unresolvedTarget) return { unresolved: true, args: [] }
    if (args.length < 3) return { unresolved: true, args: [] }
    const applyArg = unwrapExpression(args[2])
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
  const unresolved = []
  const left = unwrapExpression(leftNode)
  if (!ts.isObjectLiteralExpression(left)) return { aliases, unresolved }

  for (const prop of left.properties) {
    if (ts.isShorthandPropertyAssignment(prop)) {
      const sourceKey = prop.name.text
      aliases.push({ localName: sourceKey, sourceKey, expressionText: prop.getText() })
      continue
    }
    if (ts.isSpreadAssignment(prop)) {
      unresolved.push(prop.expression.getText())
      continue
    }
    if (!ts.isPropertyAssignment(prop)) {
      unresolved.push(prop.getText())
      continue
    }
    const sourceKeyInfo = classifyDestructureSourceKeyNode(prop.name)
    if (sourceKeyInfo.keyClass !== 'literal_key') {
      unresolved.push(sourceKeyInfo.expressionText || prop.getText())
      continue
    }
    const initializer = unwrapExpression(prop.initializer)
    if (!ts.isIdentifier(initializer)) {
      unresolved.push(prop.getText())
      continue
    }
    aliases.push({ localName: initializer.text, sourceKey: sourceKeyInfo.keyText, expressionText: prop.getText() })
  }
  return { aliases, unresolved }
}

const isPotentialRuntimeNamespaceConditional = (expression, runtimeNamespaceAliasMap = new Map()) => {
  const target = normalizeRuntimeCalleeExpression(expression)
  if (!target || !ts.isConditionalExpression(target)) return false
  const whenTrue = resolveRuntimeNamespaceFromExpression(target.whenTrue, runtimeNamespaceAliasMap)
  const whenFalse = resolveRuntimeNamespaceFromExpression(target.whenFalse, runtimeNamespaceAliasMap)
  return Boolean(whenTrue || whenFalse)
}

const analyzeRuntimeMutatorArrayLiteral = (
  arrayLiteral,
  runtimeMethodAliasMap = new Map(),
  runtimeNamespaceAliasMap = new Map(),
  runtimeArrayMethodContainerMap = new Map(),
  runtimeObjectMethodContainerMap = new Map(),
  runtimeGlobalContainerAliasMap = new Map(),
) => {
  const methods = []
  let unresolved = false
  let hasMutator = false

  for (const element of arrayLiteral.elements) {
    if (ts.isSpreadElement(element) || ts.isOmittedExpression(element)) {
      methods.push(null)
      unresolved = true
      continue
    }
    const method = resolveRuntimeMethodFromExpression(
      element,
      runtimeMethodAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayMethodContainerMap,
      runtimeObjectMethodContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    if (method && runtimeMutatorMethodSet.has(method)) {
      methods.push(method)
      hasMutator = true
    } else {
      methods.push(null)
    }
  }

  if (!hasMutator && !unresolved) return null
  return { methods, unresolved }
}

const analyzeRuntimeMutatorObjectLiteral = (
  objectLiteral,
  runtimeMethodAliasMap = new Map(),
  runtimeNamespaceAliasMap = new Map(),
  runtimeArrayMethodContainerMap = new Map(),
  runtimeObjectMethodContainerMap = new Map(),
  runtimeGlobalContainerAliasMap = new Map(),
) => {
  const methodsByKey = new Map()
  let unresolved = false
  let hasMutator = false

  for (const property of objectLiteral.properties) {
    if (ts.isSpreadAssignment(property)) {
      unresolved = true
      continue
    }
    if (ts.isMethodDeclaration(property)) {
      unresolved = true
      continue
    }
    if (!ts.isPropertyAssignment(property)) {
      unresolved = true
      continue
    }
    const keyInfo = classifyMemberNameForRuntime(property)
    if (keyInfo.keyClass !== 'literal_key') {
      unresolved = true
      continue
    }

    const valueExpression = property.initializer
    const method = resolveRuntimeMethodFromExpression(
      valueExpression,
      runtimeMethodAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayMethodContainerMap,
      runtimeObjectMethodContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    if (method && runtimeMutatorMethodSet.has(method)) {
      methodsByKey.set(keyInfo.keyText, method)
      hasMutator = true
    }
  }

  if (!hasMutator && !unresolved) return null
  return { methodsByKey, unresolved }
}

const analyzeRuntimeWorkerArrayLiteral = (
  arrayLiteral,
  runtimeConstructorAliasMap = new Map(),
  runtimeUnknownConstructorAliasMap = new Map(),
  runtimeConstructorFactoryAliasMap = new Map(),
  runtimeUnknownConstructorFactoryAliasMap = new Map(),
  runtimeNamespaceAliasMap = new Map(),
  runtimeArrayConstructorContainerMap = new Map(),
  runtimeObjectConstructorContainerMap = new Map(),
  runtimeGlobalContainerAliasMap = new Map(),
) => {
  const constructors = []
  let unresolved = false
  let hasCtor = false

  for (const element of arrayLiteral.elements) {
    if (ts.isSpreadElement(element) || ts.isOmittedExpression(element)) {
      constructors.push(null)
      unresolved = true
      continue
    }
    const ctorResolved = resolveRuntimeWorkerConstructorFromExpression(
      element,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    if (ctorResolved?.constructorName && !ctorResolved.unresolved) {
      constructors.push({ constructorName: ctorResolved.constructorName, boundArgs: ctorResolved.boundArgs || [] })
      hasCtor = true
      continue
    }
    if (ctorResolved?.unresolved) {
      constructors.push(null)
      unresolved = true
      continue
    }
    constructors.push(null)
  }

  if (!hasCtor) return null
  return { constructors, unresolved }
}

const analyzeRuntimeWorkerObjectLiteral = (
  objectLiteral,
  runtimeConstructorAliasMap = new Map(),
  runtimeUnknownConstructorAliasMap = new Map(),
  runtimeConstructorFactoryAliasMap = new Map(),
  runtimeUnknownConstructorFactoryAliasMap = new Map(),
  runtimeNamespaceAliasMap = new Map(),
  runtimeArrayConstructorContainerMap = new Map(),
  runtimeObjectConstructorContainerMap = new Map(),
  runtimeGlobalContainerAliasMap = new Map(),
) => {
  const constructorsByKey = new Map()
  let unresolved = false
  let hasCtor = false

  for (const property of objectLiteral.properties) {
    if (ts.isSpreadAssignment(property)) {
      unresolved = true
      continue
    }
    if (ts.isMethodDeclaration(property)) {
      unresolved = true
      continue
    }
    if (!ts.isPropertyAssignment(property)) {
      unresolved = true
      continue
    }
    const keyInfo = classifyMemberNameForRuntime(property)
    if (keyInfo.keyClass !== 'literal_key') {
      unresolved = true
      continue
    }

    const ctorResolved = resolveRuntimeWorkerConstructorFromExpression(
      property.initializer,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    if (ctorResolved?.constructorName && !ctorResolved.unresolved) {
      constructorsByKey.set(keyInfo.keyText, {
        constructorName: ctorResolved.constructorName,
        boundArgs: ctorResolved.boundArgs || [],
      })
      hasCtor = true
      continue
    }
    if (ctorResolved?.unresolved) {
      unresolved = true
    }
  }

  if (!hasCtor) return null
  return { constructorsByKey, unresolved }
}

const collectRuntimeAnalysisContext = (sourceFile) => {
  const runtimeMethodAliasMap = new Map()
  const runtimeConstructorAliasMap = new Map()
  const runtimeUnknownConstructorAliasMap = new Map()
  const runtimeConstructorFactoryAliasMap = new Map()
  const runtimeUnknownConstructorFactoryAliasMap = new Map()
  const runtimeNamespaceAliasMap = new Map()
  const runtimeUnknownNamespaceAliasMap = new Map()
  const runtimeGlobalContainerAliasMap = new Map()
  const runtimeArrayMethodContainerMap = new Map()
  const runtimeObjectMethodContainerMap = new Map()
  const runtimeArrayConstructorContainerMap = new Map()
  const runtimeObjectConstructorContainerMap = new Map()
  const objectLiteralVariableMap = new Map()
  const arrayLiteralVariableMap = new Map()
  const runtimeArrayStateMap = new Map()
  const runtimeArrayAliasMap = new Map()
  const runtimeIterationInvocationAliasMap = new Map()
  const runtimeIterationCallCallAliasMap = new Map()
  let runtimeArrayStateIdCounter = 0
  const runtimeAliasRiskFindings = []
  const runtimeMutatorSourceFindings = []
  const runtimeCodegenSourceFindings = []
  const timerCallbackIdentifierSet = new Set()
  const timerStringIdentifierSet = new Set()
  runtimeNamespaceAliasMap.set('Object', 'Object')
  runtimeNamespaceAliasMap.set('Reflect', 'Reflect')
  runtimeNamespaceAliasMap.set('URL', 'URL')
  runtimeGlobalContainerAliasMap.set('globalThis', 'globalThis')
  runtimeGlobalContainerAliasMap.set('window', 'window')

  const setRuntimeNamespaceAlias = (aliasName, namespaceName) => {
    runtimeNamespaceAliasMap.set(aliasName, namespaceName)
    runtimeUnknownNamespaceAliasMap.delete(aliasName)
  }

  const markRuntimeNamespaceAliasUnknown = (aliasName, expressionText) => {
    runtimeUnknownNamespaceAliasMap.set(aliasName, expressionText || aliasName)
  }

  const getRuntimeArrayStateByAlias = (aliasName) => {
    const arrayId = runtimeArrayAliasMap.get(aliasName)
    if (!arrayId) return null
    return runtimeArrayStateMap.get(arrayId) || null
  }

  const unbindRuntimeArrayAlias = (aliasName) => {
    const previousState = getRuntimeArrayStateByAlias(aliasName)
    if (previousState) {
      previousState.aliases.delete(aliasName)
    }
    runtimeArrayAliasMap.delete(aliasName)
  }

  const bindRuntimeArrayAlias = (aliasName, arrayId) => {
    unbindRuntimeArrayAlias(aliasName)
    runtimeArrayAliasMap.set(aliasName, arrayId)
    const state = runtimeArrayStateMap.get(arrayId)
    if (state) {
      state.aliases.add(aliasName)
    }
  }

  const registerRuntimeArrayState = (aliasName, arrayLiteral, declarationPosition) => {
    const arrayId = `array_${runtimeArrayStateIdCounter += 1}`
    const state = {
      array_id: arrayId,
      initial_elements: Array.from(arrayLiteral.elements),
      aliases: new Set(),
      status: 'clean',
      mutation_reasons: [],
      mutation_events: [],
      declaration_position: declarationPosition,
      last_safe_position: Number.MAX_SAFE_INTEGER,
    }
    runtimeArrayStateMap.set(arrayId, state)
    bindRuntimeArrayAlias(aliasName, arrayId)
    return state
  }

  const markRuntimeArrayState = (arrayId, status, reason, position) => {
    const state = runtimeArrayStateMap.get(arrayId)
    if (!state) return
    const normalizedStatus = runtimeArrayStatusRank[status] !== undefined ? status : 'unknown'
    const normalizedPosition = Number.isFinite(position) ? position : Number.MAX_SAFE_INTEGER
    state.mutation_events.push({
      status: normalizedStatus,
      reason,
      position: normalizedPosition,
    })
    if ((runtimeArrayStatusRank[normalizedStatus] || 0) > (runtimeArrayStatusRank[state.status] || 0)) {
      state.status = normalizedStatus
    }
    state.mutation_reasons.push(reason)
    if (Number.isFinite(normalizedPosition)) {
      state.last_safe_position = Math.min(state.last_safe_position, normalizedPosition - 1)
    }
  }

  const markRuntimeArrayAliasState = (aliasName, status, reason, position) => {
    const state = getRuntimeArrayStateByAlias(aliasName)
    if (!state) return
    markRuntimeArrayState(state.array_id, status, reason, position)
  }

  const bindRuntimeArrayAliasFromInitializer = (aliasName, initializer, declarationPosition) => {
    if (ts.isArrayLiteralExpression(initializer)) {
      registerRuntimeArrayState(aliasName, initializer, declarationPosition)
      return
    }
    if (ts.isIdentifier(initializer) && runtimeArrayAliasMap.has(initializer.text)) {
      const sourceArrayId = runtimeArrayAliasMap.get(initializer.text)
      if (sourceArrayId) {
        bindRuntimeArrayAlias(aliasName, sourceArrayId)
        return
      }
    }
    unbindRuntimeArrayAlias(aliasName)
  }

  const collectArrayAliasIdentifiersInExpression = (node, collected = new Set()) => {
    const target = unwrapExpression(node)
    if (!target) return collected

    const visitExpression = (expr) => {
      const current = unwrapExpression(expr)
      if (!current) return
      if (ts.isIdentifier(current) && runtimeArrayAliasMap.has(current.text)) {
        collected.add(current.text)
      }
      ts.forEachChild(current, visitExpression)
    }

    visitExpression(target)
    return collected
  }

  const markArrayAliasesEscapedInExpression = (node, reason, position) => {
    const aliases = collectArrayAliasIdentifiersInExpression(node)
    for (const aliasName of aliases) {
      markRuntimeArrayAliasState(aliasName, 'escaped', reason, position)
    }
  }

  const resolveRuntimeStaticArrayLiteral = (expression, depth = 0) => {
    if (!expression || depth > 8) return null
    const target = unwrapExpression(expression)
    if (!target) return null
    if (ts.isArrayLiteralExpression(target)) return target
    if (ts.isIdentifier(target)) {
      return arrayLiteralVariableMap.get(target.text) || null
    }
    if (ts.isConditionalExpression(target)) {
      const whenTrue = resolveRuntimeStaticArrayLiteral(target.whenTrue, depth + 1)
      const whenFalse = resolveRuntimeStaticArrayLiteral(target.whenFalse, depth + 1)
      if (whenTrue && whenFalse && whenTrue.getText() === whenFalse.getText()) return whenTrue
    }
    return null
  }

  const resolveRuntimeStaticObjectLiteral = (expression, depth = 0) => {
    if (!expression || depth > 8) return null
    const target = unwrapExpression(expression)
    if (!target) return null
    if (ts.isObjectLiteralExpression(target)) return target
    if (ts.isIdentifier(target)) {
      return objectLiteralVariableMap.get(target.text) || null
    }
    if (ts.isConditionalExpression(target)) {
      const whenTrue = resolveRuntimeStaticObjectLiteral(target.whenTrue, depth + 1)
      const whenFalse = resolveRuntimeStaticObjectLiteral(target.whenFalse, depth + 1)
      if (whenTrue && whenFalse && whenTrue.getText() === whenFalse.getText()) return whenTrue
    }
    return null
  }

  const resolveRuntimeObjectPropertyExpressionByKey = (objectLiteral, keyText) => {
    if (!objectLiteral || !keyText) return { expression: null, unresolved: true }
    let matchedExpression = null
    let unresolved = false
    for (const property of objectLiteral.properties) {
      if (ts.isSpreadAssignment(property)) {
        unresolved = true
        continue
      }
      if (ts.isMethodDeclaration(property)) {
        const keyInfo = classifyMemberNameForRuntime(property)
        if (keyInfo.keyClass === 'literal_key' && keyInfo.keyText === keyText.toLowerCase()) {
          matchedExpression = property
        }
        continue
      }
      if (ts.isShorthandPropertyAssignment(property)) {
        const keyInfo = classifyMemberNameForRuntime(property)
        if (keyInfo.keyClass === 'literal_key' && keyInfo.keyText === keyText.toLowerCase()) {
          matchedExpression = property.name
        }
        continue
      }
      if (!ts.isPropertyAssignment(property)) {
        unresolved = true
        continue
      }
      const keyInfo = classifyMemberNameForRuntime(property)
      if (keyInfo.keyClass !== 'literal_key') {
        unresolved = true
        continue
      }
      if (keyInfo.keyText === keyText.toLowerCase()) {
        matchedExpression = property.initializer
      }
    }
    return { expression: matchedExpression, unresolved }
  }

  const resolveRuntimeArrayAliasNameFromExpression = (expression, depth = 0) => {
    if (!expression || depth > 8) return null
    const target = unwrapExpression(expression)
    if (!target) return null
    if (ts.isIdentifier(target) && runtimeArrayAliasMap.has(target.text)) {
      return target.text
    }
    if (ts.isConditionalExpression(target)) {
      const whenTrue = resolveRuntimeArrayAliasNameFromExpression(target.whenTrue, depth + 1)
      const whenFalse = resolveRuntimeArrayAliasNameFromExpression(target.whenFalse, depth + 1)
      if (whenTrue && whenFalse && whenTrue === whenFalse) return whenTrue
    }
    return null
  }

  const resolveRuntimeArrayAliasExpressionAtPosition = (aliasName, usagePosition) => {
    if (!aliasName) return null
    const state = getRuntimeArrayStateByAlias(aliasName)
    if (!state) return null
    let effectiveStatus = 'clean'
    for (const event of state.mutation_events || []) {
      if (Number.isFinite(usagePosition) && event.position > usagePosition) continue
      if ((runtimeArrayStatusRank[event.status] || 0) > (runtimeArrayStatusRank[effectiveStatus] || 0)) {
        effectiveStatus = event.status
      }
    }
    if (effectiveStatus !== 'clean') return null
    return state.initial_elements || null
  }

  const resolveRuntimeStaticArrayElementsAtPosition = (expression, usagePosition, depth = 0) => {
    if (!expression || depth > 8) return null
    const target = unwrapExpression(expression)
    if (!target) return null
    if (ts.isArrayLiteralExpression(target)) return Array.from(target.elements)
    if (ts.isIdentifier(target)) {
      const cleanArrayElements = resolveRuntimeArrayAliasExpressionAtPosition(target.text, usagePosition)
      if (cleanArrayElements) {
        return Array.from(cleanArrayElements)
      }
      const mapped = arrayLiteralVariableMap.get(target.text) || null
      return mapped ? Array.from(mapped.elements) : null
    }
    if (ts.isConditionalExpression(target)) {
      const whenTrue = resolveRuntimeStaticArrayElementsAtPosition(target.whenTrue, usagePosition, depth + 1)
      const whenFalse = resolveRuntimeStaticArrayElementsAtPosition(target.whenFalse, usagePosition, depth + 1)
      if (whenTrue && whenFalse && whenTrue.length === whenFalse.length) {
        const same = whenTrue.every((node, idx) => node.getText() === whenFalse[idx]?.getText())
        if (same) return whenTrue
      }
    }
    return null
  }

  const resolveRuntimeIterationElementExpression = (iterableExpression, usagePosition) => {
    const sourceArrayElements = resolveRuntimeStaticArrayElementsAtPosition(iterableExpression, usagePosition)
    if (!sourceArrayElements) {
      return { expression: null, unresolved: true }
    }
    return {
      expression: sourceArrayElements[0] || null,
      unresolved: sourceArrayElements.length === 0,
    }
  }

  const markRuntimeTrackedArraysUnknownForDestructure = (sourceExpression, reason, position) => {
    const aliases = collectArrayAliasIdentifiersInExpression(sourceExpression)
    if (aliases.size > 0) {
      for (const aliasName of aliases) {
        markRuntimeArrayAliasState(aliasName, 'unknown', reason, position)
      }
      return
    }
    for (const aliasName of runtimeArrayAliasMap.keys()) {
      markRuntimeArrayAliasState(aliasName, 'unknown', reason, position)
    }
  }

  const bindRuntimeArrayAliasFromSourceExpression = (aliasName, sourceExpression, position, reasonPrefix) => {
    if (!aliasName) return { bound: false, unresolved: false }
    if (!sourceExpression) {
      unbindRuntimeArrayAlias(aliasName)
      return { bound: false, unresolved: false }
    }
    const sourceAliasName = resolveRuntimeArrayAliasNameFromExpression(sourceExpression)
    if (sourceAliasName) {
      const sourceArrayId = runtimeArrayAliasMap.get(sourceAliasName)
      if (sourceArrayId) {
        bindRuntimeArrayAlias(aliasName, sourceArrayId)
        return { bound: true, unresolved: false }
      }
    }
    unbindRuntimeArrayAlias(aliasName)
    const referencedAliases = collectArrayAliasIdentifiersInExpression(sourceExpression)
    for (const referencedAlias of referencedAliases) {
      markRuntimeArrayAliasState(referencedAlias, 'unknown', `${reasonPrefix}.UnresolvedSource`, position)
    }
    return { bound: false, unresolved: true }
  }

  const bindRuntimeArrayAliasesFromBindingPattern = (bindingPattern, sourceExpression, position, reasonPrefix) => {
    let unresolved = false
    let bound = false

    const markUnresolved = () => {
      unresolved = true
    }

    const bindPattern = (patternNode, valueExpression) => {
      const pattern = unwrapExpression(patternNode)
      if (!pattern) {
        markUnresolved()
        return
      }

      if (ts.isIdentifier(pattern)) {
        const result = bindRuntimeArrayAliasFromSourceExpression(pattern.text, valueExpression, position, reasonPrefix)
        if (result.bound) bound = true
        if (result.unresolved) markUnresolved()
        return
      }

      if (ts.isArrayBindingPattern(pattern)) {
        const sourceArrayLiteral = resolveRuntimeStaticArrayLiteral(valueExpression)
        if (!sourceArrayLiteral && valueExpression) {
          markUnresolved()
        }
        pattern.elements.forEach((element, index) => {
          if (ts.isOmittedExpression(element)) return
          if (!ts.isBindingElement(element)) {
            markUnresolved()
            return
          }
          if (element.dotDotDotToken) {
            markUnresolved()
            bindPattern(element.name, null)
            return
          }
          let elementValueExpression = sourceArrayLiteral ? sourceArrayLiteral.elements[index] || null : null
          if (!elementValueExpression && element.initializer) {
            elementValueExpression = element.initializer
            markUnresolved()
          }
          bindPattern(element.name, elementValueExpression)
        })
        return
      }

      if (ts.isObjectBindingPattern(pattern)) {
        const sourceObjectLiteral = resolveRuntimeStaticObjectLiteral(valueExpression)
        if (!sourceObjectLiteral && valueExpression) {
          markUnresolved()
        }
        pattern.elements.forEach((element) => {
          if (!ts.isBindingElement(element)) {
            markUnresolved()
            return
          }
          if (element.dotDotDotToken) {
            markUnresolved()
            bindPattern(element.name, null)
            return
          }
          const sourceKey = getBindingElementSourceKey(element)
          if (!sourceKey) {
            markUnresolved()
            bindPattern(element.name, element.initializer || null)
            return
          }
          const propertyResult = sourceObjectLiteral
            ? resolveRuntimeObjectPropertyExpressionByKey(sourceObjectLiteral, sourceKey)
            : { expression: null, unresolved: true }
          if (propertyResult.unresolved) markUnresolved()
          let propertyValueExpression = propertyResult.expression
          if (!propertyValueExpression && element.initializer) {
            propertyValueExpression = element.initializer
            markUnresolved()
          }
          bindPattern(element.name, propertyValueExpression)
        })
        return
      }

      markUnresolved()
    }

    bindPattern(bindingPattern, sourceExpression)
    if (unresolved && runtimeArrayAliasMap.size > 0) {
      markRuntimeTrackedArraysUnknownForDestructure(sourceExpression, `${reasonPrefix}.UnresolvedBindingPattern`, position)
    }
    return { unresolved, bound }
  }

  const bindRuntimeArrayAliasesFromAssignmentPattern = (leftPatternExpression, sourceExpression, position, reasonPrefix) => {
    let unresolved = false
    let bound = false

    const markUnresolved = () => {
      unresolved = true
    }

    const bindAssignmentTarget = (targetExpression, valueExpression) => {
      const target = unwrapExpression(targetExpression)
      if (!target) {
        markUnresolved()
        return
      }

      if (ts.isIdentifier(target)) {
        const result = bindRuntimeArrayAliasFromSourceExpression(target.text, valueExpression, position, reasonPrefix)
        if (result.bound) bound = true
        if (result.unresolved) markUnresolved()
        return
      }

      if (ts.isArrayLiteralExpression(target)) {
        const sourceArrayLiteral = resolveRuntimeStaticArrayLiteral(valueExpression)
        if (!sourceArrayLiteral && valueExpression) {
          markUnresolved()
        }
        target.elements.forEach((element, index) => {
          if (ts.isOmittedExpression(element)) return
          if (ts.isSpreadElement(element)) {
            markUnresolved()
            bindAssignmentTarget(element.expression, null)
            return
          }
          const elementValueExpression = sourceArrayLiteral ? sourceArrayLiteral.elements[index] || null : null
          bindAssignmentTarget(element, elementValueExpression)
        })
        return
      }

      if (ts.isObjectLiteralExpression(target)) {
        const sourceObjectLiteral = resolveRuntimeStaticObjectLiteral(valueExpression)
        if (!sourceObjectLiteral && valueExpression) {
          markUnresolved()
        }
        target.properties.forEach((property) => {
          if (ts.isSpreadAssignment(property)) {
            markUnresolved()
            return
          }
          if (ts.isShorthandPropertyAssignment(property)) {
            const propertyResult = sourceObjectLiteral
              ? resolveRuntimeObjectPropertyExpressionByKey(sourceObjectLiteral, property.name.text)
              : { expression: null, unresolved: true }
            if (propertyResult.unresolved) markUnresolved()
            bindAssignmentTarget(property.name, propertyResult.expression)
            return
          }
          if (!ts.isPropertyAssignment(property)) {
            markUnresolved()
            return
          }
          const sourceKeyInfo = classifyDestructureSourceKeyNode(property.name)
          if (sourceKeyInfo.keyClass !== 'literal_key') {
            markUnresolved()
            bindAssignmentTarget(property.initializer, null)
            return
          }
          const propertyResult = sourceObjectLiteral
            ? resolveRuntimeObjectPropertyExpressionByKey(sourceObjectLiteral, sourceKeyInfo.keyText)
            : { expression: null, unresolved: true }
          if (propertyResult.unresolved) markUnresolved()
          bindAssignmentTarget(property.initializer, propertyResult.expression)
        })
        return
      }

      markUnresolved()
    }

    bindAssignmentTarget(leftPatternExpression, sourceExpression)
    if (unresolved && runtimeArrayAliasMap.size > 0) {
      markRuntimeTrackedArraysUnknownForDestructure(sourceExpression, `${reasonPrefix}.UnresolvedAssignmentPattern`, position)
    }
    return { unresolved, bound }
  }

  const setRuntimeContainerAliases = (aliasName, initializer) => {
    if (ts.isArrayLiteralExpression(initializer)) {
      const arrayAnalysis = analyzeRuntimeMutatorArrayLiteral(
        initializer,
        runtimeMethodAliasMap,
        runtimeNamespaceAliasMap,
        runtimeArrayMethodContainerMap,
        runtimeObjectMethodContainerMap,
        runtimeGlobalContainerAliasMap,
      )
      if (arrayAnalysis) {
        runtimeArrayMethodContainerMap.set(aliasName, arrayAnalysis)
      } else {
        runtimeArrayMethodContainerMap.delete(aliasName)
      }
      runtimeObjectMethodContainerMap.delete(aliasName)
      return
    }

    if (ts.isObjectLiteralExpression(initializer)) {
      const objectAnalysis = analyzeRuntimeMutatorObjectLiteral(
        initializer,
        runtimeMethodAliasMap,
        runtimeNamespaceAliasMap,
        runtimeArrayMethodContainerMap,
        runtimeObjectMethodContainerMap,
        runtimeGlobalContainerAliasMap,
      )
      if (objectAnalysis) {
        runtimeObjectMethodContainerMap.set(aliasName, objectAnalysis)
      } else {
        runtimeObjectMethodContainerMap.delete(aliasName)
      }
      runtimeArrayMethodContainerMap.delete(aliasName)
      return
    }

    if (ts.isIdentifier(initializer)) {
      if (runtimeArrayMethodContainerMap.has(initializer.text)) {
        runtimeArrayMethodContainerMap.set(aliasName, runtimeArrayMethodContainerMap.get(initializer.text))
      } else {
        runtimeArrayMethodContainerMap.delete(aliasName)
      }

      if (runtimeObjectMethodContainerMap.has(initializer.text)) {
        runtimeObjectMethodContainerMap.set(aliasName, runtimeObjectMethodContainerMap.get(initializer.text))
      } else {
        runtimeObjectMethodContainerMap.delete(aliasName)
      }
      return
    }

    runtimeArrayMethodContainerMap.delete(aliasName)
    runtimeObjectMethodContainerMap.delete(aliasName)
  }

  const setRuntimeConstructorAliasBinding = (aliasName, initializer) => {
    const resolvedCtor = resolveRuntimeWorkerConstructorFromExpression(
      initializer,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    if (resolvedCtor?.constructorName && !resolvedCtor.unresolved) {
      runtimeConstructorAliasMap.set(aliasName, {
        constructorName: resolvedCtor.constructorName,
        boundArgs: resolvedCtor.boundArgs || [],
      })
      runtimeUnknownConstructorAliasMap.delete(aliasName)
      return
    }
    runtimeConstructorAliasMap.delete(aliasName)
    if (resolvedCtor?.unresolved) {
      runtimeUnknownConstructorAliasMap.set(aliasName, resolvedCtor.expressionText || initializer.getText())
    } else {
      runtimeUnknownConstructorAliasMap.delete(aliasName)
    }
  }

  const setRuntimeConstructorContainerAliases = (aliasName, initializer) => {
    if (ts.isArrayLiteralExpression(initializer)) {
      const arrayAnalysis = analyzeRuntimeWorkerArrayLiteral(
        initializer,
        runtimeConstructorAliasMap,
        runtimeUnknownConstructorAliasMap,
        runtimeConstructorFactoryAliasMap,
        runtimeUnknownConstructorFactoryAliasMap,
        runtimeNamespaceAliasMap,
        runtimeArrayConstructorContainerMap,
        runtimeObjectConstructorContainerMap,
        runtimeGlobalContainerAliasMap,
      )
      if (arrayAnalysis) {
        runtimeArrayConstructorContainerMap.set(aliasName, arrayAnalysis)
      } else {
        runtimeArrayConstructorContainerMap.delete(aliasName)
      }
      runtimeObjectConstructorContainerMap.delete(aliasName)
      return
    }

    if (ts.isObjectLiteralExpression(initializer)) {
      const objectAnalysis = analyzeRuntimeWorkerObjectLiteral(
        initializer,
        runtimeConstructorAliasMap,
        runtimeUnknownConstructorAliasMap,
        runtimeConstructorFactoryAliasMap,
        runtimeUnknownConstructorFactoryAliasMap,
        runtimeNamespaceAliasMap,
        runtimeArrayConstructorContainerMap,
        runtimeObjectConstructorContainerMap,
        runtimeGlobalContainerAliasMap,
      )
      if (objectAnalysis) {
        runtimeObjectConstructorContainerMap.set(aliasName, objectAnalysis)
      } else {
        runtimeObjectConstructorContainerMap.delete(aliasName)
      }
      runtimeArrayConstructorContainerMap.delete(aliasName)
      return
    }

    if (ts.isIdentifier(initializer)) {
      if (runtimeArrayConstructorContainerMap.has(initializer.text)) {
        runtimeArrayConstructorContainerMap.set(aliasName, runtimeArrayConstructorContainerMap.get(initializer.text))
      } else {
        runtimeArrayConstructorContainerMap.delete(aliasName)
      }

      if (runtimeObjectConstructorContainerMap.has(initializer.text)) {
        runtimeObjectConstructorContainerMap.set(aliasName, runtimeObjectConstructorContainerMap.get(initializer.text))
      } else {
        runtimeObjectConstructorContainerMap.delete(aliasName)
      }
      return
    }

    runtimeArrayConstructorContainerMap.delete(aliasName)
    runtimeObjectConstructorContainerMap.delete(aliasName)
  }

  const resolveFunctionLikeReturnExpression = (functionLikeNode) => {
    const target = unwrapExpression(functionLikeNode)
    if (!target) return null
    if (!ts.isFunctionDeclaration(target) && !ts.isFunctionExpression(target) && !ts.isArrowFunction(target)) {
      return null
    }

    if (ts.isArrowFunction(target) && !ts.isBlock(target.body)) {
      return target.body
    }

    if (!ts.isBlock(target.body)) return null

    let foundReturn = null
    for (const statement of target.body.statements) {
      if (ts.isEmptyStatement(statement)) continue
      if (ts.isReturnStatement(statement)) {
        if (!statement.expression || foundReturn) return undefined
        foundReturn = statement.expression
        continue
      }
      return null
    }
    return foundReturn
  }

  const setRuntimeConstructorFactoryAliasBinding = (aliasName, initializer) => {
    const returnExpr = resolveFunctionLikeReturnExpression(initializer)
    if (!returnExpr) {
      if (ts.isIdentifier(initializer) && runtimeConstructorFactoryAliasMap.has(initializer.text)) {
        runtimeConstructorFactoryAliasMap.set(aliasName, runtimeConstructorFactoryAliasMap.get(initializer.text))
        runtimeUnknownConstructorFactoryAliasMap.delete(aliasName)
        return
      }
      if (ts.isIdentifier(initializer) && runtimeUnknownConstructorFactoryAliasMap.has(initializer.text)) {
        runtimeConstructorFactoryAliasMap.delete(aliasName)
        runtimeUnknownConstructorFactoryAliasMap.set(
          aliasName,
          runtimeUnknownConstructorFactoryAliasMap.get(initializer.text),
        )
        return
      }
      runtimeConstructorFactoryAliasMap.delete(aliasName)
      runtimeUnknownConstructorFactoryAliasMap.delete(aliasName)
      return
    }

    if (returnExpr === undefined) {
      runtimeConstructorFactoryAliasMap.delete(aliasName)
      runtimeUnknownConstructorFactoryAliasMap.set(aliasName, initializer.getText ? initializer.getText() : aliasName)
      return
    }

    const resolvedCtor = resolveRuntimeWorkerConstructorFromExpression(
      returnExpr,
      runtimeConstructorAliasMap,
      runtimeUnknownConstructorAliasMap,
      runtimeConstructorFactoryAliasMap,
      runtimeUnknownConstructorFactoryAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayConstructorContainerMap,
      runtimeObjectConstructorContainerMap,
      runtimeGlobalContainerAliasMap,
    )

    if (resolvedCtor?.constructorName && !resolvedCtor.unresolved) {
      runtimeConstructorFactoryAliasMap.set(aliasName, {
        constructorName: resolvedCtor.constructorName,
        boundArgs: resolvedCtor.boundArgs || [],
      })
      runtimeUnknownConstructorFactoryAliasMap.delete(aliasName)
      return
    }

    runtimeConstructorFactoryAliasMap.delete(aliasName)
    if (resolvedCtor?.unresolved) {
      runtimeUnknownConstructorFactoryAliasMap.set(aliasName, resolvedCtor.expressionText || returnExpr.getText())
    } else {
      runtimeUnknownConstructorFactoryAliasMap.delete(aliasName)
    }
  }

  const pushRuntimeMutatorSourceFinding = (type, expressionText) => {
    runtimeMutatorSourceFindings.push({
      type,
      expressionText: normalizeComputedKeyExpr(expressionText || ''),
    })
  }

  const pushRuntimeCodegenSourceFinding = (type, expressionText) => {
    runtimeCodegenSourceFindings.push({
      type,
      expressionText: normalizeComputedKeyExpr(expressionText || ''),
    })
  }

  const updateTimerIdentifierBinding = (name, initializer) => {
    const target = unwrapExpression(initializer)
    if (!target) {
      timerCallbackIdentifierSet.delete(name)
      timerStringIdentifierSet.delete(name)
      return
    }
    if (ts.isArrowFunction(target) || ts.isFunctionExpression(target)) {
      timerCallbackIdentifierSet.add(name)
      timerStringIdentifierSet.delete(name)
      return
    }
    if (ts.isIdentifier(target) && timerCallbackIdentifierSet.has(target.text)) {
      timerCallbackIdentifierSet.add(name)
      timerStringIdentifierSet.delete(name)
      return
    }
    if (ts.isIdentifier(target) && timerStringIdentifierSet.has(target.text)) {
      timerStringIdentifierSet.add(name)
      timerCallbackIdentifierSet.delete(name)
      return
    }
    const staticString = resolveStaticStringValue(target)
    if (staticString !== null) {
      timerStringIdentifierSet.add(name)
      timerCallbackIdentifierSet.delete(name)
      return
    }
    timerCallbackIdentifierSet.delete(name)
    timerStringIdentifierSet.delete(name)
  }

  const runtimeFunctionSummaryMap = new Map()
  const runtimeFunctionNodeSummaryMap = new Map()
  let runtimeFunctionSummaryIdCounter = 0

  const resolveRuntimeFunctionLocalAliasRoot = (aliasMap, name) => {
    let current = name
    const seen = new Set()
    while (aliasMap.has(current) && !seen.has(current)) {
      seen.add(current)
      const next = aliasMap.get(current)
      if (!next || next === current) break
      current = next
    }
    return current
  }

  const collectRuntimeIdentifiersInExpression = (expressionNode, set = new Set()) => {
    const target = unwrapExpression(expressionNode)
    if (!target) return set
    const visitExpression = (node) => {
      const current = unwrapExpression(node)
      if (!current) return
      if (ts.isIdentifier(current)) {
        set.add(current.text)
      }
      ts.forEachChild(current, visitExpression)
    }
    visitExpression(target)
    return set
  }

  const analyzeRuntimeFunctionSummary = (functionNode) => {
    if (!functionNode) {
      return {
        function_id: `fn_${runtimeFunctionSummaryIdCounter += 1}`,
        declared_name: '',
        aliases: new Set(),
        captures_tracked_arrays: new Set(),
        mutates_array_ids: new Set(),
        escapes_array_ids: new Set(),
        has_unknown_side_effect: true,
        summary_confidence: 'unknown',
      }
    }
    if (runtimeFunctionNodeSummaryMap.has(functionNode)) {
      return runtimeFunctionNodeSummaryMap.get(functionNode)
    }

    const declaredName = ts.isFunctionDeclaration(functionNode) && functionNode.name ? functionNode.name.text : ''
    const summary = {
      function_id: `fn_${runtimeFunctionSummaryIdCounter += 1}`,
      declared_name: declaredName,
      aliases: new Set(),
      parameter_alias_bindings: new Map(),
      captures_tracked_arrays: new Set(),
      mutates_array_ids: new Set(),
      escapes_array_ids: new Set(),
      captures_parameter_aliases: new Set(),
      mutates_parameter_aliases: new Set(),
      escapes_parameter_aliases: new Set(),
      has_unknown_side_effect: false,
      summary_confidence: 'exact',
    }
    runtimeFunctionNodeSummaryMap.set(functionNode, summary)

    const localArrayAliasMap = new Map()
    const localArrayLiteralMap = new Map()
    const localObjectLiteralMap = new Map()
    const registerCapturedName = (name) => {
      if (!name) return
      const root = resolveRuntimeFunctionLocalAliasRoot(localArrayAliasMap, name)
      summary.captures_tracked_arrays.add(root)
      if (summary.parameter_alias_bindings.has(root)) {
        summary.captures_parameter_aliases.add(root)
      }
    }
    const registerMutatedName = (name) => {
      if (!name) return
      const root = resolveRuntimeFunctionLocalAliasRoot(localArrayAliasMap, name)
      summary.mutates_array_ids.add(root)
      if (summary.parameter_alias_bindings.has(root)) {
        summary.mutates_parameter_aliases.add(root)
      }
      registerCapturedName(root)
    }
    const registerEscapedName = (name) => {
      if (!name) return
      const root = resolveRuntimeFunctionLocalAliasRoot(localArrayAliasMap, name)
      summary.escapes_array_ids.add(root)
      if (summary.parameter_alias_bindings.has(root)) {
        summary.escapes_parameter_aliases.add(root)
      }
      registerCapturedName(root)
    }
    const markFunctionSummaryUnknown = () => {
      summary.has_unknown_side_effect = true
      if (summary.summary_confidence === 'exact') {
        summary.summary_confidence = 'conservative'
      }
    }

    const applyIdentifierSetAsEscaped = (identifierSet) => {
      for (const identifierName of identifierSet) {
        registerEscapedName(identifierName)
      }
    }

    const updateFunctionLocalStaticLiteralMaps = (identifierName, initializerExpression) => {
      if (!identifierName) return
      const initializer = unwrapExpression(initializerExpression)
      if (!initializer) {
        localArrayLiteralMap.delete(identifierName)
        localObjectLiteralMap.delete(identifierName)
        return
      }

      if (ts.isArrayLiteralExpression(initializer)) {
        localArrayLiteralMap.set(identifierName, initializer)
      } else if (ts.isIdentifier(initializer) && localArrayLiteralMap.has(initializer.text)) {
        localArrayLiteralMap.set(identifierName, localArrayLiteralMap.get(initializer.text))
      } else {
        localArrayLiteralMap.delete(identifierName)
      }

      if (ts.isObjectLiteralExpression(initializer)) {
        localObjectLiteralMap.set(identifierName, initializer)
      } else if (ts.isIdentifier(initializer) && localObjectLiteralMap.has(initializer.text)) {
        localObjectLiteralMap.set(identifierName, localObjectLiteralMap.get(initializer.text))
      } else {
        localObjectLiteralMap.delete(identifierName)
      }
    }

    const resolveRuntimeFunctionAliasNameFromExpression = (expression, depth = 0) => {
      if (!expression || depth > 8) return null
      const target = unwrapExpression(expression)
      if (!target) return null
      if (ts.isIdentifier(target)) {
        return resolveRuntimeFunctionLocalAliasRoot(localArrayAliasMap, target.text)
      }
      if (ts.isConditionalExpression(target)) {
        const whenTrue = resolveRuntimeFunctionAliasNameFromExpression(target.whenTrue, depth + 1)
        const whenFalse = resolveRuntimeFunctionAliasNameFromExpression(target.whenFalse, depth + 1)
        if (whenTrue && whenFalse && whenTrue === whenFalse) return whenTrue
      }
      return null
    }

    const resolveRuntimeFunctionStaticArrayLiteral = (expression, depth = 0) => {
      if (!expression || depth > 8) return null
      const target = unwrapExpression(expression)
      if (!target) return null
      if (ts.isArrayLiteralExpression(target)) return target
      if (ts.isIdentifier(target)) {
        return localArrayLiteralMap.get(target.text) || null
      }
      if (ts.isConditionalExpression(target)) {
        const whenTrue = resolveRuntimeFunctionStaticArrayLiteral(target.whenTrue, depth + 1)
        const whenFalse = resolveRuntimeFunctionStaticArrayLiteral(target.whenFalse, depth + 1)
        if (whenTrue && whenFalse && whenTrue.getText() === whenFalse.getText()) return whenTrue
      }
      return null
    }

    const resolveRuntimeFunctionStaticObjectLiteral = (expression, depth = 0) => {
      if (!expression || depth > 8) return null
      const target = unwrapExpression(expression)
      if (!target) return null
      if (ts.isObjectLiteralExpression(target)) return target
      if (ts.isIdentifier(target)) {
        return localObjectLiteralMap.get(target.text) || null
      }
      if (ts.isConditionalExpression(target)) {
        const whenTrue = resolveRuntimeFunctionStaticObjectLiteral(target.whenTrue, depth + 1)
        const whenFalse = resolveRuntimeFunctionStaticObjectLiteral(target.whenFalse, depth + 1)
        if (whenTrue && whenFalse && whenTrue.getText() === whenFalse.getText()) return whenTrue
      }
      return null
    }

    const bindRuntimeFunctionLocalAliasFromSourceExpression = (aliasName, sourceExpression) => {
      if (!aliasName) return { bound: false, unresolved: false }
      if (!sourceExpression) {
        localArrayAliasMap.delete(aliasName)
        return { bound: false, unresolved: true }
      }
      const resolvedAlias = resolveRuntimeFunctionAliasNameFromExpression(sourceExpression)
      if (resolvedAlias) {
        localArrayAliasMap.set(aliasName, resolvedAlias)
        registerCapturedName(resolvedAlias)
        return { bound: true, unresolved: false }
      }

      localArrayAliasMap.delete(aliasName)
      const identifiers = collectRuntimeIdentifiersInExpression(sourceExpression)
      identifiers.forEach((identifierName) => registerCapturedName(identifierName))
      return { bound: false, unresolved: true }
    }

    const bindRuntimeFunctionAliasesFromBindingPattern = (bindingPattern, sourceExpression) => {
      let unresolved = false

      const markUnresolved = () => {
        unresolved = true
      }

      const bindPattern = (patternNode, valueExpression) => {
        const pattern = unwrapExpression(patternNode)
        if (!pattern) {
          markUnresolved()
          return
        }

        if (ts.isIdentifier(pattern)) {
          const result = bindRuntimeFunctionLocalAliasFromSourceExpression(pattern.text, valueExpression)
          if (result.unresolved) markUnresolved()
          return
        }

        if (ts.isArrayBindingPattern(pattern)) {
          const sourceArrayLiteral = resolveRuntimeFunctionStaticArrayLiteral(valueExpression)
          if (!sourceArrayLiteral && valueExpression) {
            markUnresolved()
          }
          pattern.elements.forEach((element, index) => {
            if (ts.isOmittedExpression(element)) return
            if (!ts.isBindingElement(element)) {
              markUnresolved()
              return
            }
            if (element.dotDotDotToken) {
              markUnresolved()
              bindPattern(element.name, null)
              return
            }
            let elementValueExpression = sourceArrayLiteral ? sourceArrayLiteral.elements[index] || null : null
            if (!elementValueExpression && element.initializer) {
              elementValueExpression = element.initializer
              markUnresolved()
            }
            bindPattern(element.name, elementValueExpression)
          })
          return
        }

        if (ts.isObjectBindingPattern(pattern)) {
          const sourceObjectLiteral = resolveRuntimeFunctionStaticObjectLiteral(valueExpression)
          if (!sourceObjectLiteral && valueExpression) {
            markUnresolved()
          }
          pattern.elements.forEach((element) => {
            if (!ts.isBindingElement(element)) {
              markUnresolved()
              return
            }
            if (element.dotDotDotToken) {
              markUnresolved()
              bindPattern(element.name, null)
              return
            }
            const sourceKey = getBindingElementSourceKey(element)
            if (!sourceKey) {
              markUnresolved()
              bindPattern(element.name, element.initializer || null)
              return
            }
            const propertyResult = sourceObjectLiteral
              ? resolveRuntimeObjectPropertyExpressionByKey(sourceObjectLiteral, sourceKey)
              : { expression: null, unresolved: true }
            if (propertyResult.unresolved) markUnresolved()
            let propertyValueExpression = propertyResult.expression
            if (!propertyValueExpression && element.initializer) {
              propertyValueExpression = element.initializer
              markUnresolved()
            }
            bindPattern(element.name, propertyValueExpression)
          })
          return
        }

        markUnresolved()
      }

      bindPattern(bindingPattern, sourceExpression)
      if (unresolved) {
        markFunctionSummaryUnknown()
      }
    }

    const bindRuntimeFunctionAliasesFromAssignmentPattern = (leftPatternExpression, sourceExpression) => {
      let unresolved = false

      const markUnresolved = () => {
        unresolved = true
      }

      const bindTarget = (targetExpression, valueExpression) => {
        const target = unwrapExpression(targetExpression)
        if (!target) {
          markUnresolved()
          return
        }

        if (ts.isIdentifier(target)) {
          const result = bindRuntimeFunctionLocalAliasFromSourceExpression(target.text, valueExpression)
          if (result.unresolved) markUnresolved()
          return
        }

        if (ts.isArrayLiteralExpression(target)) {
          const sourceArrayLiteral = resolveRuntimeFunctionStaticArrayLiteral(valueExpression)
          if (!sourceArrayLiteral && valueExpression) {
            markUnresolved()
          }
          target.elements.forEach((element, index) => {
            if (ts.isOmittedExpression(element)) return
            if (ts.isSpreadElement(element)) {
              markUnresolved()
              bindTarget(element.expression, null)
              return
            }
            const elementValueExpression = sourceArrayLiteral ? sourceArrayLiteral.elements[index] || null : null
            bindTarget(element, elementValueExpression)
          })
          return
        }

        if (ts.isObjectLiteralExpression(target)) {
          const sourceObjectLiteral = resolveRuntimeFunctionStaticObjectLiteral(valueExpression)
          if (!sourceObjectLiteral && valueExpression) {
            markUnresolved()
          }
          target.properties.forEach((property) => {
            if (ts.isSpreadAssignment(property)) {
              markUnresolved()
              return
            }
            if (ts.isShorthandPropertyAssignment(property)) {
              const propertyResult = sourceObjectLiteral
                ? resolveRuntimeObjectPropertyExpressionByKey(sourceObjectLiteral, property.name.text)
                : { expression: null, unresolved: true }
              if (propertyResult.unresolved) markUnresolved()
              bindTarget(property.name, propertyResult.expression)
              return
            }
            if (!ts.isPropertyAssignment(property)) {
              markUnresolved()
              return
            }
            const sourceKeyInfo = classifyDestructureSourceKeyNode(property.name)
            if (sourceKeyInfo.keyClass !== 'literal_key') {
              markUnresolved()
              bindTarget(property.initializer, null)
              return
            }
            const propertyResult = sourceObjectLiteral
              ? resolveRuntimeObjectPropertyExpressionByKey(sourceObjectLiteral, sourceKeyInfo.keyText)
              : { expression: null, unresolved: true }
            if (propertyResult.unresolved) markUnresolved()
            bindTarget(property.initializer, propertyResult.expression)
          })
          return
        }

        markUnresolved()
      }

      bindTarget(leftPatternExpression, sourceExpression)
      if (unresolved) {
        markFunctionSummaryUnknown()
      }
    }

    const registerRuntimeFunctionParameterAlias = (aliasName, descriptor) => {
      if (!aliasName) return
      summary.parameter_alias_bindings.set(aliasName, descriptor)
      localArrayAliasMap.set(aliasName, aliasName)
    }

    const bindRuntimeFunctionParameterPattern = (patternNode, paramIndex, path = [], inheritedUnresolved = false) => {
      const pattern = unwrapExpression(patternNode)
      if (!pattern) {
        markFunctionSummaryUnknown()
        return
      }

      if (ts.isIdentifier(pattern)) {
        registerRuntimeFunctionParameterAlias(pattern.text, {
          param_index: paramIndex,
          path: Array.from(path),
          unresolved: inheritedUnresolved,
        })
        if (inheritedUnresolved) {
          markFunctionSummaryUnknown()
        }
        return
      }

      if (ts.isArrayBindingPattern(pattern)) {
        pattern.elements.forEach((element, index) => {
          if (ts.isOmittedExpression(element)) return
          if (!ts.isBindingElement(element)) {
            markFunctionSummaryUnknown()
            return
          }
          if (element.dotDotDotToken) {
            bindRuntimeFunctionParameterPattern(
              element.name,
              paramIndex,
              [...path, { kind: 'array_rest' }],
              true,
            )
            return
          }
          bindRuntimeFunctionParameterPattern(
            element.name,
            paramIndex,
            [...path, { kind: 'array_index', index }],
            inheritedUnresolved || Boolean(element.initializer),
          )
        })
        return
      }

      if (ts.isObjectBindingPattern(pattern)) {
        pattern.elements.forEach((element) => {
          if (!ts.isBindingElement(element)) {
            markFunctionSummaryUnknown()
            return
          }
          if (element.dotDotDotToken) {
            bindRuntimeFunctionParameterPattern(
              element.name,
              paramIndex,
              [...path, { kind: 'object_rest' }],
              true,
            )
            return
          }
          const sourceKey = getBindingElementSourceKey(element)
          if (!sourceKey) {
            bindRuntimeFunctionParameterPattern(
              element.name,
              paramIndex,
              [...path, { kind: 'object_unknown' }],
              true,
            )
            return
          }
          bindRuntimeFunctionParameterPattern(
            element.name,
            paramIndex,
            [...path, { kind: 'object_key', key: sourceKey }],
            inheritedUnresolved || Boolean(element.initializer),
          )
        })
        return
      }

      markFunctionSummaryUnknown()
    }

    const bindRuntimeFunctionParameterAliases = () => {
      if (!Array.isArray(functionNode.parameters)) return
      functionNode.parameters.forEach((parameter, index) => {
        bindRuntimeFunctionParameterPattern(parameter.name, index, [], Boolean(parameter.initializer))
      })
    }

    bindRuntimeFunctionParameterAliases()

    const analyzeFunctionBodyNode = (node) => {
      if (!node) return

      if (
        ts.isFunctionDeclaration(node) ||
        ts.isFunctionExpression(node) ||
        ts.isArrowFunction(node) ||
        ts.isMethodDeclaration(node)
      ) {
        if (node === functionNode) {
          ts.forEachChild(node, analyzeFunctionBodyNode)
        }
        return
      }

      if (ts.isVariableDeclaration(node) && node.initializer) {
        const rhs = unwrapExpression(node.initializer)
        if (ts.isIdentifier(node.name)) {
          const localName = node.name.text
          updateFunctionLocalStaticLiteralMaps(localName, rhs)
          if (ts.isIdentifier(rhs)) {
            const resolved = resolveRuntimeFunctionLocalAliasRoot(localArrayAliasMap, rhs.text)
            localArrayAliasMap.set(localName, resolved)
            registerCapturedName(resolved)
          } else {
            localArrayAliasMap.delete(localName)
            const identifiers = collectRuntimeIdentifiersInExpression(rhs)
            if (identifiers.has(localName)) {
              markFunctionSummaryUnknown()
            }
            identifiers.forEach((identifierName) => registerCapturedName(identifierName))
          }
        } else if (ts.isArrayBindingPattern(node.name) || ts.isObjectBindingPattern(node.name)) {
          bindRuntimeFunctionAliasesFromBindingPattern(node.name, rhs)
          collectRuntimeIdentifiersInExpression(rhs).forEach((identifierName) => registerCapturedName(identifierName))
        }
      }

      if (ts.isBinaryExpression(node) && isRuntimeWriteOperator(node.operatorToken.kind)) {
        const leftExpr = unwrapExpression(node.left)
        const rightExpr = unwrapExpression(node.right)

        if (node.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isIdentifier(leftExpr)) {
          updateFunctionLocalStaticLiteralMaps(leftExpr.text, rightExpr)
          if (ts.isIdentifier(rightExpr)) {
            const resolved = resolveRuntimeFunctionLocalAliasRoot(localArrayAliasMap, rightExpr.text)
            localArrayAliasMap.set(leftExpr.text, resolved)
            registerCapturedName(resolved)
          } else {
            localArrayAliasMap.delete(leftExpr.text)
            collectRuntimeIdentifiersInExpression(rightExpr).forEach((identifierName) =>
              registerCapturedName(identifierName),
            )
          }
        } else if (
          node.operatorToken.kind === ts.SyntaxKind.EqualsToken &&
          (ts.isArrayLiteralExpression(leftExpr) || ts.isObjectLiteralExpression(leftExpr))
        ) {
          bindRuntimeFunctionAliasesFromAssignmentPattern(leftExpr, rightExpr)
        }

        if (ts.isElementAccessExpression(leftExpr)) {
          const baseExpr = unwrapExpression(leftExpr.expression)
          if (ts.isIdentifier(baseExpr)) {
            registerMutatedName(baseExpr.text)
          } else {
            markFunctionSummaryUnknown()
          }
        } else if (ts.isPropertyAccessExpression(leftExpr)) {
          const baseExpr = unwrapExpression(leftExpr.expression)
          if (leftExpr.name.text === 'length' && ts.isIdentifier(baseExpr)) {
            registerMutatedName(baseExpr.text)
          } else if (ts.isIdentifier(baseExpr)) {
            registerCapturedName(baseExpr.text)
          }
        }

        collectRuntimeIdentifiersInExpression(rightExpr).forEach((identifierName) =>
          registerCapturedName(identifierName),
        )
      }

      if (ts.isReturnStatement(node) && node.expression) {
        const identifiers = collectRuntimeIdentifiersInExpression(node.expression)
        applyIdentifierSetAsEscaped(identifiers)
      }

      if (ts.isCallExpression(node)) {
        const calleeExpr = normalizeRuntimeCalleeExpression(node.expression)
        let treatedAsKnownMutatingCall = false
        const directIdentifierCallee = ts.isIdentifier(calleeExpr) ? calleeExpr.text : null
        const nestedSummary =
          directIdentifierCallee && runtimeFunctionSummaryMap.has(directIdentifierCallee)
            ? runtimeFunctionSummaryMap.get(directIdentifierCallee)
            : null

        if (ts.isPropertyAccessExpression(calleeExpr) || ts.isElementAccessExpression(calleeExpr)) {
          const memberName = getStaticMemberName(calleeExpr)
          const baseExpr = unwrapExpression(calleeExpr.expression)
          if (ts.isIdentifier(baseExpr) && memberName && runtimeArrayMutatingMethodNameSet.has(memberName)) {
            registerMutatedName(baseExpr.text)
            treatedAsKnownMutatingCall = true
          } else if (ts.isIdentifier(baseExpr) && !memberName) {
            markFunctionSummaryUnknown()
            registerCapturedName(baseExpr.text)
          } else if (memberName === 'call' || memberName === 'apply') {
            const invokedExpr = normalizeRuntimeCalleeExpression(calleeExpr.expression)
            const invokedMethodName = getStaticMemberName(invokedExpr)
            if (invokedMethodName && runtimeArrayMutatingMethodNameSet.has(invokedMethodName)) {
              const thisArg = unwrapExpression(node.arguments[0] || null)
              if (ts.isIdentifier(thisArg)) {
                registerMutatedName(thisArg.text)
              } else {
                markFunctionSummaryUnknown()
              }
              treatedAsKnownMutatingCall = true
            }
          }
        }

        if (!treatedAsKnownMutatingCall && nestedSummary) {
          for (const mutateName of nestedSummary.mutates_array_ids || []) {
            registerMutatedName(mutateName)
          }
          for (const escapeName of nestedSummary.escapes_array_ids || []) {
            registerEscapedName(escapeName)
          }
          if (nestedSummary.has_unknown_side_effect) {
            markFunctionSummaryUnknown()
          }
          treatedAsKnownMutatingCall = true
        }

        for (const argNode of node.arguments) {
          const identifiers = collectRuntimeIdentifiersInExpression(argNode)
          if (!treatedAsKnownMutatingCall) {
            applyIdentifierSetAsEscaped(identifiers)
          } else {
            identifiers.forEach((identifierName) => registerCapturedName(identifierName))
          }
        }

        if (!treatedAsKnownMutatingCall) {
          markFunctionSummaryUnknown()
        }
      }

      ts.forEachChild(node, analyzeFunctionBodyNode)
    }

    if (ts.isArrowFunction(functionNode) && !ts.isBlock(functionNode.body)) {
      analyzeFunctionBodyNode(functionNode.body)
    } else if (ts.isBlock(functionNode.body)) {
      functionNode.body.statements.forEach((statement) => analyzeFunctionBodyNode(statement))
    } else if (ts.isFunctionDeclaration(functionNode) && functionNode.body) {
      functionNode.body.statements.forEach((statement) => analyzeFunctionBodyNode(statement))
    } else {
      summary.summary_confidence = 'unknown'
      summary.has_unknown_side_effect = true
    }

    if (summary.summary_confidence === 'exact' && summary.has_unknown_side_effect) {
      summary.summary_confidence = 'conservative'
    }
    if (
      summary.summary_confidence === 'exact' &&
      summary.mutates_array_ids.size === 0 &&
      summary.escapes_array_ids.size === 0 &&
      summary.captures_tracked_arrays.size === 0
    ) {
      summary.summary_confidence = 'exact'
    }

    return summary
  }

  const resolveRuntimeFunctionSummaryFromExpression = (expression, depth = 0) => {
    if (depth > 10) return null
    const target = normalizeRuntimeCalleeExpression(expression)
    if (!target) return null

    if (ts.isIdentifier(target)) {
      return runtimeFunctionSummaryMap.get(target.text) || null
    }

    if (ts.isFunctionExpression(target) || ts.isArrowFunction(target)) {
      return analyzeRuntimeFunctionSummary(target)
    }

    if (ts.isCallExpression(target)) {
      const callee = normalizeRuntimeCalleeExpression(target.expression)
      if (callee && (ts.isPropertyAccessExpression(callee) || ts.isElementAccessExpression(callee))) {
        const memberName = getStaticMemberName(callee)
        if (memberName === 'bind') {
          return resolveRuntimeFunctionSummaryFromExpression(callee.expression, depth + 1)
        }
      }

      const returnExpr = resolveFunctionLikeReturnExpression(target.expression)
      if (returnExpr) {
        return resolveRuntimeFunctionSummaryFromExpression(returnExpr, depth + 1)
      }
      return null
    }

    if (ts.isConditionalExpression(target)) {
      const whenTrue = resolveRuntimeFunctionSummaryFromExpression(target.whenTrue, depth + 1)
      const whenFalse = resolveRuntimeFunctionSummaryFromExpression(target.whenFalse, depth + 1)
      if (whenTrue && whenFalse && whenTrue.function_id === whenFalse.function_id) {
        return whenTrue
      }
      return null
    }

    if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
      const memberName = getStaticMemberName(target)
      if (memberName === 'call' || memberName === 'apply' || memberName === 'bind') {
        return resolveRuntimeFunctionSummaryFromExpression(target.expression, depth + 1)
      }
      if (ts.isIdentifier(target.expression)) {
        const baseName = target.expression.text
        const objectContainer = runtimeObjectMethodContainerMap.get(baseName) || null
        if (objectContainer && !objectContainer.unresolved) {
          return null
        }
        const arrayContainer = runtimeArrayMethodContainerMap.get(baseName) || null
        if (arrayContainer && !arrayContainer.unresolved) {
          return null
        }
      }
    }

    return null
  }

  const setRuntimeFunctionAliasBinding = (aliasName, initializer) => {
    const summary = resolveRuntimeFunctionSummaryFromExpression(initializer)
    if (summary) {
      runtimeFunctionSummaryMap.set(aliasName, summary)
      summary.aliases.add(aliasName)
      return
    }
    runtimeFunctionSummaryMap.delete(aliasName)
  }

  const resolveRuntimeFunctionParameterBindingExpression = (callArguments, bindingDescriptor, callPosition) => {
    if (!bindingDescriptor || !Array.isArray(callArguments)) {
      return { expression: null, unresolved: true }
    }
    let currentExpression = callArguments[bindingDescriptor.param_index] || null
    if (!currentExpression) {
      return { expression: null, unresolved: true }
    }
    if (bindingDescriptor.unresolved) {
      return { expression: null, unresolved: true }
    }

    const path = Array.isArray(bindingDescriptor.path) ? bindingDescriptor.path : []
    for (const step of path) {
      if (!currentExpression) {
        return { expression: null, unresolved: true }
      }

      if (step?.kind === 'array_index') {
        const elements = resolveRuntimeStaticArrayElementsAtPosition(currentExpression, callPosition)
        if (!elements) {
          return { expression: null, unresolved: true }
        }
        currentExpression = elements[step.index] || null
        if (!currentExpression) {
          return { expression: null, unresolved: true }
        }
        continue
      }

      if (step?.kind === 'object_key') {
        const objectLiteral = resolveRuntimeStaticObjectLiteral(currentExpression)
        if (!objectLiteral) {
          return { expression: null, unresolved: true }
        }
        const propertyResult = resolveRuntimeObjectPropertyExpressionByKey(objectLiteral, step.key)
        if (propertyResult.unresolved || !propertyResult.expression) {
          return { expression: null, unresolved: true }
        }
        currentExpression = propertyResult.expression
        continue
      }

      return { expression: null, unresolved: true }
    }

    return { expression: currentExpression, unresolved: false }
  }

  const applyRuntimeFunctionParameterAliasState = (
    summary,
    aliasNames,
    status,
    reason,
    callArguments,
    callPosition,
  ) => {
    let marked = false
    let unresolved = false
    let sawTrackedCandidate = false
    for (const aliasName of aliasNames || []) {
      const bindingDescriptor = summary.parameter_alias_bindings?.get(aliasName) || null
      if (!bindingDescriptor) continue
      const callArgExpression = callArguments[bindingDescriptor.param_index] || null
      if (callArgExpression) {
        const callArgAliases = collectArrayAliasIdentifiersInExpression(callArgExpression)
        if (callArgAliases.size > 0) {
          sawTrackedCandidate = true
        }
      }
      const resolved = resolveRuntimeFunctionParameterBindingExpression(callArguments, bindingDescriptor, callPosition)
      if (resolved.unresolved || !resolved.expression) {
        unresolved = true
        continue
      }

      const directAliasName = resolveRuntimeArrayAliasNameFromExpression(resolved.expression)
      if (directAliasName && runtimeArrayAliasMap.has(directAliasName)) {
        markRuntimeArrayAliasState(directAliasName, status, reason, callPosition)
        marked = true
        continue
      }

      const referencedAliases = collectArrayAliasIdentifiersInExpression(resolved.expression)
      if (referencedAliases.size > 0) {
        sawTrackedCandidate = true
        for (const referencedAlias of referencedAliases) {
          markRuntimeArrayAliasState(referencedAlias, status, reason, callPosition)
        }
        marked = true
        continue
      }

      unresolved = true
    }
    return { marked, unresolved, sawTrackedCandidate }
  }

  const applyRuntimeFunctionSummaryAtCall = (summary, callNode, options = null) => {
    if (!summary) return false
    const callPosition =
      options && Number.isFinite(options.callPosition)
        ? options.callPosition
        : callNode && typeof callNode.getStart === 'function'
          ? callNode.getStart()
          : Number.MAX_SAFE_INTEGER
    const callArguments =
      options && Array.isArray(options.callArguments)
        ? options.callArguments
        : callNode && Array.isArray(callNode.arguments)
          ? callNode.arguments
          : []
    const summaryName = summary.declared_name || summary.function_id

    const parameterMutateResult = applyRuntimeFunctionParameterAliasState(
      summary,
      summary.mutates_parameter_aliases,
      'tainted',
      `FunctionCallMutate.${summaryName}`,
      callArguments,
      callPosition,
    )
    const parameterEscapeResult = applyRuntimeFunctionParameterAliasState(
      summary,
      summary.escapes_parameter_aliases,
      'escaped',
      `FunctionCallEscape.${summaryName}`,
      callArguments,
      callPosition,
    )
    if (
      (parameterMutateResult.unresolved || parameterEscapeResult.unresolved) &&
      (parameterMutateResult.sawTrackedCandidate || parameterEscapeResult.sawTrackedCandidate) &&
      runtimeArrayAliasMap.size > 0
    ) {
      for (const aliasName of runtimeArrayAliasMap.keys()) {
        markRuntimeArrayAliasState(aliasName, 'unknown', `FunctionCallParamUnknown.${summaryName}`, callPosition)
      }
    }

    for (const mutateName of summary.mutates_array_ids || []) {
      if (runtimeArrayAliasMap.has(mutateName)) {
        markRuntimeArrayAliasState(mutateName, 'tainted', `FunctionCallMutate.${summaryName}`, callPosition)
      }
    }

    for (const escapeName of summary.escapes_array_ids || []) {
      if (runtimeArrayAliasMap.has(escapeName)) {
        markRuntimeArrayAliasState(escapeName, 'escaped', `FunctionCallEscape.${summaryName}`, callPosition)
      }
    }

    if (summary.has_unknown_side_effect || summary.summary_confidence === 'unknown') {
      let marked = false
      const captureNames = Array.from(summary.captures_tracked_arrays || [])
      if (captureNames.length > 0) {
        for (const captureName of captureNames) {
          if (runtimeArrayAliasMap.has(captureName)) {
            markRuntimeArrayAliasState(captureName, 'unknown', `FunctionCallUnknown.${summaryName}`, callPosition)
            marked = true
          }
        }
      }
      const parameterCaptureResult = applyRuntimeFunctionParameterAliasState(
        summary,
        summary.captures_parameter_aliases,
        'unknown',
        `FunctionCallUnknown.${summaryName}`,
        callArguments,
        callPosition,
      )
      marked = marked || parameterCaptureResult.marked
      if (parameterCaptureResult.unresolved && parameterCaptureResult.sawTrackedCandidate) {
        marked = false
      }
      if (!marked) {
        for (const aliasName of runtimeArrayAliasMap.keys()) {
          markRuntimeArrayAliasState(aliasName, 'unknown', `FunctionCallUnknown.${summaryName}`, callPosition)
        }
      }
    }
    return true
  }

  const collectHoistedFunctionSummaries = (node) => {
    if (ts.isFunctionDeclaration(node) && node.name) {
      const summary = analyzeRuntimeFunctionSummary(node)
      runtimeFunctionSummaryMap.set(node.name.text, summary)
      summary.aliases.add(node.name.text)
    }
    ts.forEachChild(node, collectHoistedFunctionSummaries)
  }

  collectHoistedFunctionSummaries(sourceFile)

  const markAllRuntimeArraysUnknownAtPosition = (reason, position) => {
    for (const aliasName of runtimeArrayAliasMap.keys()) {
      markRuntimeArrayAliasState(aliasName, 'unknown', reason, position)
    }
  }

  const runtimeInvocationContext = {
    arrayLiteralVariableMap,
    runtimeArrayStateMap,
    runtimeArrayAliasMap,
  }

  const isRuntimeArrayNamespaceExpression = (expression, depth = 0) => {
    if (!expression || depth > 8) return false
    const target = normalizeRuntimeCalleeExpression(expression)
    if (!target) return false

    if (ts.isIdentifier(target)) {
      return target.text === 'Array'
    }

    if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
      const memberName = getStaticMemberName(target)
      if (memberName !== 'Array') return false
      const globalContainer = resolveGlobalContainerFromExpression(target.expression, runtimeGlobalContainerAliasMap)
      return Boolean(globalContainer)
    }

    if (ts.isConditionalExpression(target)) {
      const whenTrue = isRuntimeArrayNamespaceExpression(target.whenTrue, depth + 1)
      const whenFalse = isRuntimeArrayNamespaceExpression(target.whenFalse, depth + 1)
      return whenTrue && whenFalse
    }

    return false
  }

  const isRuntimeArrayPrototypeExpression = (expression, depth = 0) => {
    if (!expression || depth > 8) return false
    const target = normalizeRuntimeCalleeExpression(expression)
    if (!target) return false

    if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
      const memberName = getStaticMemberName(target)
      if (memberName !== 'prototype') return false
      return isRuntimeArrayNamespaceExpression(target.expression, depth + 1)
    }

    if (ts.isConditionalExpression(target)) {
      const whenTrue = isRuntimeArrayPrototypeExpression(target.whenTrue, depth + 1)
      const whenFalse = isRuntimeArrayPrototypeExpression(target.whenFalse, depth + 1)
      return whenTrue && whenFalse
    }

    return false
  }

  const resolveRuntimeArrayIterationMethodFromTargetExpression = (expression, depth = 0) => {
    if (!expression || depth > 8) {
      return { methodName: null, unresolved: true, expressionText: expression?.getText?.() || '' }
    }
    const target = normalizeRuntimeCalleeExpression(expression)
    if (!target) return { methodName: null, unresolved: false, expressionText: '' }

    if (ts.isIdentifier(target)) {
      if (runtimeArrayIterationMethodDescriptorMap.has(target.text)) {
        return { methodName: null, unresolved: true, expressionText: target.getText(sourceFile) }
      }
      return { methodName: null, unresolved: false, expressionText: target.getText(sourceFile) }
    }

    if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
      const memberName = getStaticMemberName(target)
      const baseExpression = unwrapExpression(target.expression)
      if (memberName && runtimeArrayIterationMethodDescriptorMap.has(memberName)) {
        if (isRuntimeArrayPrototypeExpression(baseExpression, depth + 1)) {
          return { methodName: memberName, unresolved: false, expressionText: target.getText(sourceFile) }
        }
        return { methodName: null, unresolved: true, expressionText: target.getText(sourceFile) }
      }
      if (!memberName && isRuntimeArrayPrototypeExpression(baseExpression, depth + 1)) {
        return { methodName: null, unresolved: true, expressionText: target.getText(sourceFile) }
      }
      return { methodName: null, unresolved: false, expressionText: target.getText(sourceFile) }
    }

    if (ts.isConditionalExpression(target)) {
      const whenTrue = resolveRuntimeArrayIterationMethodFromTargetExpression(target.whenTrue, depth + 1)
      const whenFalse = resolveRuntimeArrayIterationMethodFromTargetExpression(target.whenFalse, depth + 1)
      if (
        whenTrue.methodName &&
        whenFalse.methodName &&
        !whenTrue.unresolved &&
        !whenFalse.unresolved &&
        whenTrue.methodName === whenFalse.methodName
      ) {
        return { methodName: whenTrue.methodName, unresolved: false, expressionText: target.getText(sourceFile) }
      }
      if (
        whenTrue.methodName ||
        whenFalse.methodName ||
        whenTrue.unresolved ||
        whenFalse.unresolved
      ) {
        return { methodName: null, unresolved: true, expressionText: target.getText(sourceFile) }
      }
      return { methodName: null, unresolved: false, expressionText: target.getText(sourceFile) }
    }

    return { methodName: null, unresolved: false, expressionText: target.getText?.(sourceFile) || '' }
  }

  const buildRuntimeIterationCallDescriptor = ({
    argumentMode,
    methodName,
    iterableExpression,
    invocationArguments = [],
    unresolvedTarget = false,
    unresolvedArguments = false,
    unresolvedIterable = false,
    unresolvedExpression = '',
    boundArgs = [],
    laterArgs = [],
  }) => {
    if (unresolvedTarget) {
      return {
        matched: true,
        argumentMode,
        methodName: null,
        iterableExpression: null,
        callbackExpression: null,
        initialValueExpression: null,
        unresolvedTarget: true,
        unresolvedExpression,
        boundArgs,
        laterArgs,
      }
    }
    if (unresolvedArguments) {
      return {
        matched: true,
        argumentMode,
        methodName,
        iterableExpression: null,
        callbackExpression: null,
        initialValueExpression: null,
        unresolvedArguments: true,
        unresolvedExpression,
        boundArgs,
        laterArgs,
      }
    }
    if (unresolvedIterable || !iterableExpression) {
      return {
        matched: true,
        argumentMode,
        methodName,
        iterableExpression: null,
        callbackExpression: null,
        initialValueExpression: null,
        unresolvedIterable: true,
        unresolvedExpression,
        boundArgs,
        laterArgs,
      }
    }
    const methodDescriptor = methodName ? runtimeArrayIterationMethodDescriptorMap.get(methodName) || null : null
    const callbackArgumentIndex = methodDescriptor?.callback_argument_index ?? 0
    return {
      matched: true,
      argumentMode,
      methodName,
      iterableExpression,
      callbackExpression: unwrapExpression(invocationArguments[callbackArgumentIndex] || null),
      initialValueExpression: unwrapExpression(invocationArguments[callbackArgumentIndex + 1] || null),
      unresolvedArguments: false,
      unresolvedExpression: '',
      boundArgs,
      laterArgs,
    }
  }

  const resolveRuntimeArrayIterationBindAliasDescriptorFromExpression = (expression) => {
    const target = normalizeRuntimeCalleeExpression(expression)
    if (!target || !ts.isCallExpression(target)) return null
    const bindCallee = normalizeRuntimeCalleeExpression(target.expression)
    if (!(bindCallee && (ts.isPropertyAccessExpression(bindCallee) || ts.isElementAccessExpression(bindCallee)))) {
      return null
    }
    const bindMemberName = getStaticMemberName(bindCallee)
    if (bindMemberName !== 'bind') return null

    const targetMethod = resolveRuntimeArrayIterationMethodFromTargetExpression(bindCallee.expression)
    if (!targetMethod.methodName) {
      if (!targetMethod.unresolved) return null
      return buildRuntimeIterationCallDescriptor({
        argumentMode: 'bind',
        methodName: null,
        iterableExpression: null,
        unresolvedTarget: true,
        unresolvedExpression: targetMethod.expressionText || target.getText(sourceFile),
      })
    }

    const normalizedBindArgs = resolveRuntimeInvocationArgumentsFromNodes(
      Array.from(target.arguments),
      runtimeInvocationContext,
    )
    if (normalizedBindArgs.unresolved) {
      return buildRuntimeIterationCallDescriptor({
        argumentMode: 'bind',
        methodName: targetMethod.methodName,
        iterableExpression: null,
        unresolvedArguments: true,
        unresolvedExpression: normalizedBindArgs.expressionText || target.getText(sourceFile),
      })
    }

    const iterableExpression = unwrapExpression(normalizedBindArgs.args[0] || null)
    if (!iterableExpression) {
      return buildRuntimeIterationCallDescriptor({
        argumentMode: 'bind',
        methodName: targetMethod.methodName,
        iterableExpression: null,
        unresolvedIterable: true,
        unresolvedExpression: target.getText(sourceFile),
      })
    }

    return buildRuntimeIterationCallDescriptor({
      argumentMode: 'bind',
      methodName: targetMethod.methodName,
      iterableExpression,
      invocationArguments: normalizedBindArgs.args.slice(1),
      boundArgs: normalizedBindArgs.args.slice(1),
      laterArgs: [],
    })
  }

  const resolveRuntimeArrayIterationCallCallDescriptorFromNormalizedArgs = (
    normalizedArguments,
    callNode,
    argumentMode = 'call_call',
  ) => {
    if (normalizedArguments.unresolved) {
      return buildRuntimeIterationCallDescriptor({
        argumentMode,
        methodName: null,
        iterableExpression: null,
        unresolvedArguments: true,
        unresolvedExpression: normalizedArguments.expressionText || callNode.getText(sourceFile),
      })
    }

    const targetMethodExpression = unwrapExpression(normalizedArguments.args[0] || null)
    const targetMethod = resolveRuntimeArrayIterationMethodFromTargetExpression(targetMethodExpression)
    if (!targetMethod.methodName) {
      if (!targetMethod.unresolved) return null
      return buildRuntimeIterationCallDescriptor({
        argumentMode,
        methodName: null,
        iterableExpression: null,
        unresolvedTarget: true,
        unresolvedExpression: targetMethod.expressionText || callNode.getText(sourceFile),
      })
    }

    const iterableExpression = unwrapExpression(normalizedArguments.args[1] || null)
    const invocationArguments = normalizedArguments.args.slice(2)
    return buildRuntimeIterationCallDescriptor({
      argumentMode,
      methodName: targetMethod.methodName,
      iterableExpression,
      invocationArguments,
      boundArgs: [],
      laterArgs: invocationArguments,
      unresolvedExpression: callNode.getText(sourceFile),
    })
  }

  const resolveRuntimeArrayIterationCallDescriptor = (callNode, calleeExpression) => {
    const resolveCallArguments = () =>
      resolveRuntimeInvocationArgumentsFromNodes(Array.from(callNode.arguments), runtimeInvocationContext)

    if (ts.isIdentifier(calleeExpression)) {
      const bindAliasDescriptor = runtimeIterationInvocationAliasMap.get(calleeExpression.text) || null
      if (bindAliasDescriptor) {
        if (bindAliasDescriptor.unresolvedTarget) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'bind',
            methodName: null,
            iterableExpression: null,
            unresolvedTarget: true,
            unresolvedExpression: bindAliasDescriptor.unresolvedExpression || calleeExpression.text,
            boundArgs: bindAliasDescriptor.boundArgs || [],
          })
        }
        if (bindAliasDescriptor.unresolvedArguments) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'bind',
            methodName: bindAliasDescriptor.methodName || null,
            iterableExpression: null,
            unresolvedArguments: true,
            unresolvedExpression: bindAliasDescriptor.unresolvedExpression || calleeExpression.text,
            boundArgs: bindAliasDescriptor.boundArgs || [],
          })
        }
        if (bindAliasDescriptor.unresolvedIterable) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'bind',
            methodName: bindAliasDescriptor.methodName || null,
            iterableExpression: null,
            unresolvedIterable: true,
            unresolvedExpression: bindAliasDescriptor.unresolvedExpression || calleeExpression.text,
            boundArgs: bindAliasDescriptor.boundArgs || [],
          })
        }
        const normalizedArguments = resolveCallArguments()
        if (normalizedArguments.unresolved) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'bind',
            methodName: bindAliasDescriptor.methodName || null,
            iterableExpression: null,
            unresolvedArguments: true,
            unresolvedExpression: normalizedArguments.expressionText || callNode.getText(sourceFile),
            boundArgs: bindAliasDescriptor.boundArgs || [],
          })
        }
        const boundArgs = Array.from(bindAliasDescriptor.boundArgs || [])
        const laterArgs = normalizedArguments.args
        return buildRuntimeIterationCallDescriptor({
          argumentMode: 'bind',
          methodName: bindAliasDescriptor.methodName || null,
          iterableExpression: unwrapExpression(bindAliasDescriptor.iterableExpression || null),
          invocationArguments: [...boundArgs, ...laterArgs],
          unresolvedExpression: bindAliasDescriptor.unresolvedExpression || callNode.getText(sourceFile),
          boundArgs,
          laterArgs,
        })
      }

      const callCallAliasDescriptor = runtimeIterationCallCallAliasMap.get(calleeExpression.text) || null
      if (callCallAliasDescriptor) {
        if (callCallAliasDescriptor.unresolved) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'call_call',
            methodName: null,
            iterableExpression: null,
            unresolvedTarget: true,
            unresolvedExpression: callCallAliasDescriptor.expressionText || calleeExpression.text,
          })
        }
        const normalizedArguments = resolveCallArguments()
        const callCallDescriptor = resolveRuntimeArrayIterationCallCallDescriptorFromNormalizedArgs(
          normalizedArguments,
          callNode,
          'call_call',
        )
        if (callCallDescriptor) return callCallDescriptor
      }
    }

    if (ts.isCallExpression(calleeExpression)) {
      const inlineBindDescriptor = resolveRuntimeArrayIterationBindAliasDescriptorFromExpression(calleeExpression)
      if (inlineBindDescriptor) {
        if (
          inlineBindDescriptor.unresolvedTarget ||
          inlineBindDescriptor.unresolvedArguments ||
          inlineBindDescriptor.unresolvedIterable
        ) {
          return inlineBindDescriptor
        }
        const normalizedArguments = resolveCallArguments()
        if (normalizedArguments.unresolved) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'bind',
            methodName: inlineBindDescriptor.methodName || null,
            iterableExpression: null,
            unresolvedArguments: true,
            unresolvedExpression: normalizedArguments.expressionText || callNode.getText(sourceFile),
            boundArgs: inlineBindDescriptor.boundArgs || [],
          })
        }
        const boundArgs = Array.from(inlineBindDescriptor.boundArgs || [])
        const laterArgs = normalizedArguments.args
        return buildRuntimeIterationCallDescriptor({
          argumentMode: 'bind',
          methodName: inlineBindDescriptor.methodName || null,
          iterableExpression: unwrapExpression(inlineBindDescriptor.iterableExpression || null),
          invocationArguments: [...boundArgs, ...laterArgs],
          unresolvedExpression: inlineBindDescriptor.unresolvedExpression || callNode.getText(sourceFile),
          boundArgs,
          laterArgs,
        })
      }
    }

    if (ts.isPropertyAccessExpression(calleeExpression) || ts.isElementAccessExpression(calleeExpression)) {
      const memberName = getStaticMemberName(calleeExpression)

      if (memberName && runtimeArrayIterationMethodDescriptorMap.has(memberName)) {
        const normalizedArguments = resolveCallArguments()
        if (normalizedArguments.unresolved) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'direct',
            methodName: memberName,
            iterableExpression: null,
            unresolvedArguments: true,
            unresolvedExpression: normalizedArguments.expressionText || callNode.getText(sourceFile),
          })
        }
        return buildRuntimeIterationCallDescriptor({
          argumentMode: 'direct',
          methodName: memberName,
          iterableExpression: unwrapExpression(calleeExpression.expression),
          invocationArguments: normalizedArguments.args,
          unresolvedExpression: callNode.getText(sourceFile),
        })
      }

      if (memberName === 'call') {
        const callBaseExpression = normalizeRuntimeCalleeExpression(calleeExpression.expression)
        if (callBaseExpression && (ts.isPropertyAccessExpression(callBaseExpression) || ts.isElementAccessExpression(callBaseExpression))) {
          const callBaseMemberName = getStaticMemberName(callBaseExpression)
          if (callBaseMemberName === 'call') {
            const normalizedArguments = resolveCallArguments()
            const callCallDescriptor = resolveRuntimeArrayIterationCallCallDescriptorFromNormalizedArgs(
              normalizedArguments,
              callNode,
              'call_call',
            )
            if (callCallDescriptor) return callCallDescriptor
          }
        }
      }

      if (memberName === 'call' || memberName === 'apply') {
        const targetMethod = resolveRuntimeArrayIterationMethodFromTargetExpression(calleeExpression.expression)
        if (!targetMethod.methodName) {
          if (targetMethod.unresolved) {
            return buildRuntimeIterationCallDescriptor({
              argumentMode: memberName,
              methodName: null,
              iterableExpression: null,
              unresolvedTarget: true,
              unresolvedExpression: targetMethod.expressionText || callNode.getText(sourceFile),
            })
          }
          return null
        }

        const normalizedArguments = resolveCallArguments()
        if (normalizedArguments.unresolved) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: memberName,
            methodName: targetMethod.methodName,
            iterableExpression: null,
            unresolvedArguments: true,
            unresolvedExpression: normalizedArguments.expressionText || callNode.getText(sourceFile),
          })
        }

        const iterableExpression = unwrapExpression(normalizedArguments.args[0] || null)
        if (memberName === 'call') {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'call',
            methodName: targetMethod.methodName,
            iterableExpression,
            invocationArguments: normalizedArguments.args.slice(1),
            unresolvedExpression: callNode.getText(sourceFile),
            boundArgs: [],
            laterArgs: normalizedArguments.args.slice(1),
          })
        }

        const applyArgumentExpression = unwrapExpression(normalizedArguments.args[1] || null)
        const applyArguments = resolveRuntimeArgumentArrayElements(applyArgumentExpression, runtimeInvocationContext)
        if (applyArguments.unresolved) {
          return buildRuntimeIterationCallDescriptor({
            argumentMode: 'apply',
            methodName: targetMethod.methodName,
            iterableExpression,
            unresolvedArguments: true,
            unresolvedExpression: applyArguments.expressionText || callNode.getText(sourceFile),
          })
        }
        return buildRuntimeIterationCallDescriptor({
          argumentMode: 'apply',
          methodName: targetMethod.methodName,
          iterableExpression,
          invocationArguments: applyArguments.args,
          unresolvedExpression: callNode.getText(sourceFile),
          boundArgs: [],
          laterArgs: applyArguments.args,
        })
      }
    }

    const runtimeMethod = resolveRuntimeMethodFromExpression(
      calleeExpression,
      runtimeMethodAliasMap,
      runtimeNamespaceAliasMap,
      runtimeArrayMethodContainerMap,
      runtimeObjectMethodContainerMap,
      runtimeGlobalContainerAliasMap,
    )
    if (runtimeMethod !== 'Reflect.apply') {
      return null
    }

    const normalizedArguments = resolveCallArguments()
    if (normalizedArguments.unresolved) {
      return buildRuntimeIterationCallDescriptor({
        argumentMode: 'reflect_apply',
        methodName: null,
        iterableExpression: null,
        unresolvedArguments: true,
        unresolvedExpression: normalizedArguments.expressionText || callNode.getText(sourceFile),
      })
    }

    const targetMethodExpression = unwrapExpression(normalizedArguments.args[0] || null)
    const targetMethod = resolveRuntimeArrayIterationMethodFromTargetExpression(targetMethodExpression)
    if (!targetMethod.methodName) {
      if (targetMethod.unresolved) {
        return buildRuntimeIterationCallDescriptor({
          argumentMode: 'reflect_apply',
          methodName: null,
          iterableExpression: null,
          unresolvedTarget: true,
          unresolvedExpression: targetMethod.expressionText || callNode.getText(sourceFile),
        })
      }
      return null
    }

    const iterableExpression = unwrapExpression(normalizedArguments.args[1] || null)
    const reflectApplyArgumentExpression = unwrapExpression(normalizedArguments.args[2] || null)
    const reflectApplyArguments = resolveRuntimeArgumentArrayElements(
      reflectApplyArgumentExpression,
      runtimeInvocationContext,
    )
    if (reflectApplyArguments.unresolved) {
      return buildRuntimeIterationCallDescriptor({
        argumentMode: 'reflect_apply',
        methodName: targetMethod.methodName,
        iterableExpression,
        unresolvedArguments: true,
        unresolvedExpression: reflectApplyArguments.expressionText || callNode.getText(sourceFile),
      })
    }

    return buildRuntimeIterationCallDescriptor({
      argumentMode: 'reflect_apply',
      methodName: targetMethod.methodName,
      iterableExpression,
      invocationArguments: reflectApplyArguments.args,
      unresolvedExpression: callNode.getText(sourceFile),
      boundArgs: [],
      laterArgs: reflectApplyArguments.args,
    })
  }

  const resolveRuntimeIterationCallCallAliasFromExpression = (expression, depth = 0) => {
    if (!expression || depth > 8) return { matched: false, unresolved: true, expressionText: '' }
    const target = normalizeRuntimeCalleeExpression(expression)
    if (!target) return { matched: false, unresolved: true, expressionText: '' }

    if (ts.isIdentifier(target)) {
      const existingAlias = runtimeIterationCallCallAliasMap.get(target.text) || null
      if (existingAlias) {
        return {
          matched: true,
          unresolved: Boolean(existingAlias.unresolved),
          expressionText: existingAlias.expressionText || target.text,
        }
      }
      return { matched: false, unresolved: false, expressionText: target.text }
    }

    if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
      const memberName = getStaticMemberName(target)
      if (memberName !== 'call') return { matched: false, unresolved: false, expressionText: target.getText(sourceFile) }
      const innerTarget = normalizeRuntimeCalleeExpression(target.expression)
      if (innerTarget && (ts.isPropertyAccessExpression(innerTarget) || ts.isElementAccessExpression(innerTarget))) {
        const innerMemberName = getStaticMemberName(innerTarget)
        if (innerMemberName === 'call') {
          return { matched: true, unresolved: false, expressionText: target.getText(sourceFile) }
        }
      }
      return { matched: false, unresolved: true, expressionText: target.getText(sourceFile) }
    }

    if (ts.isConditionalExpression(target)) {
      const whenTrue = resolveRuntimeIterationCallCallAliasFromExpression(target.whenTrue, depth + 1)
      const whenFalse = resolveRuntimeIterationCallCallAliasFromExpression(target.whenFalse, depth + 1)
      if (whenTrue.matched && whenFalse.matched) {
        return {
          matched: true,
          unresolved: Boolean(whenTrue.unresolved || whenFalse.unresolved),
          expressionText: target.getText(sourceFile),
        }
      }
      if (whenTrue.matched || whenFalse.matched || whenTrue.unresolved || whenFalse.unresolved) {
        return { matched: true, unresolved: true, expressionText: target.getText(sourceFile) }
      }
      return { matched: false, unresolved: false, expressionText: target.getText(sourceFile) }
    }

    return { matched: false, unresolved: false, expressionText: target.getText?.(sourceFile) || '' }
  }

  const setRuntimeIterationInvocationAliasBinding = (aliasName, initializer) => {
    const target = normalizeRuntimeCalleeExpression(initializer)
    if (ts.isIdentifier(target)) {
      const existingAlias = runtimeIterationInvocationAliasMap.get(target.text) || null
      if (existingAlias) {
        runtimeIterationInvocationAliasMap.set(aliasName, {
          ...existingAlias,
          boundArgs: Array.from(existingAlias.boundArgs || []),
        })
        return
      }
      runtimeIterationInvocationAliasMap.delete(aliasName)
      return
    }

    const bindDescriptor = resolveRuntimeArrayIterationBindAliasDescriptorFromExpression(target)
    if (!bindDescriptor) {
      runtimeIterationInvocationAliasMap.delete(aliasName)
      return
    }
    runtimeIterationInvocationAliasMap.set(aliasName, {
      ...bindDescriptor,
      boundArgs: Array.from(bindDescriptor.boundArgs || []),
    })
  }

  const setRuntimeIterationCallCallAliasBinding = (aliasName, initializer) => {
    const resolvedAlias = resolveRuntimeIterationCallCallAliasFromExpression(initializer)
    if (!resolvedAlias.matched) {
      runtimeIterationCallCallAliasMap.delete(aliasName)
      return
    }
    runtimeIterationCallCallAliasMap.set(aliasName, {
      unresolved: Boolean(resolvedAlias.unresolved),
      expressionText: resolvedAlias.expressionText || aliasName,
    })
  }

  const applyRuntimeIterationCallbackSummaryAtCall = (callNode, calleeExpression) => {
    const iterationCallDescriptor = resolveRuntimeArrayIterationCallDescriptor(callNode, calleeExpression)
    if (!iterationCallDescriptor || !iterationCallDescriptor.matched) {
      return false
    }
    const memberName = iterationCallDescriptor.methodName || 'unknown'
    if (iterationCallDescriptor.unresolvedTarget && runtimeArrayAliasMap.size > 0) {
      markAllRuntimeArraysUnknownAtPosition(
        `IterationCallTargetUnknown.${iterationCallDescriptor.argumentMode || 'unknown'}.${memberName}`,
        callNode.getStart(),
      )
      return true
    }
    if (iterationCallDescriptor.unresolvedArguments && runtimeArrayAliasMap.size > 0) {
      markAllRuntimeArraysUnknownAtPosition(
        `IterationCallArgumentsUnknown.${iterationCallDescriptor.argumentMode || 'unknown'}.${memberName}`,
        callNode.getStart(),
      )
      return true
    }
    if (iterationCallDescriptor.unresolvedIterable && runtimeArrayAliasMap.size > 0) {
      markAllRuntimeArraysUnknownAtPosition(
        `IterationIterableUnknown.${iterationCallDescriptor.argumentMode || 'unknown'}.${memberName}`,
        callNode.getStart(),
      )
      return true
    }

    const methodDescriptor = memberName ? runtimeArrayIterationMethodDescriptorMap.get(memberName) || null : null
    if (!methodDescriptor) {
      return false
    }

    const callbackArgumentIndex = methodDescriptor.callback_argument_index
    const currentItemParameterIndex = methodDescriptor.current_item_parameter_index
    if (!Number.isInteger(callbackArgumentIndex) || callbackArgumentIndex < 0) {
      if (runtimeArrayAliasMap.size > 0) {
        markAllRuntimeArraysUnknownAtPosition(`IterationDescriptorUnknown.${memberName}`, callNode.getStart())
      }
      return true
    }
    if (!Number.isInteger(currentItemParameterIndex) || currentItemParameterIndex < 0) {
      if (runtimeArrayAliasMap.size > 0) {
        markAllRuntimeArraysUnknownAtPosition(`IterationDescriptorUnknown.${memberName}`, callNode.getStart())
      }
      return true
    }

    const callbackExpression = unwrapExpression(iterationCallDescriptor.callbackExpression || null)
    if (!callbackExpression) {
      if (runtimeArrayAliasMap.size > 0) {
        markAllRuntimeArraysUnknownAtPosition(`IterationCallbackMissing.${memberName}`, callNode.getStart())
      }
      return true
    }

    const callbackSummary = resolveRuntimeFunctionSummaryFromExpression(callbackExpression)
    const iterableExpression = unwrapExpression(iterationCallDescriptor.iterableExpression || null)
    const iterableElements = resolveRuntimeStaticArrayElementsAtPosition(iterableExpression, callNode.getStart())
    const callbackHasPotentialArraySideEffect =
      Boolean(callbackSummary) &&
      (
        (callbackSummary.mutates_parameter_aliases && callbackSummary.mutates_parameter_aliases.size > 0) ||
        (callbackSummary.escapes_parameter_aliases && callbackSummary.escapes_parameter_aliases.size > 0) ||
        callbackSummary.has_unknown_side_effect ||
        callbackSummary.summary_confidence === 'unknown'
      )
    if (!iterableElements) {
      if (runtimeArrayAliasMap.size > 0 && callbackHasPotentialArraySideEffect) {
        markAllRuntimeArraysUnknownAtPosition(`IterationIterableUnknown.${memberName}`, callNode.getStart())
      }
      return true
    }
    if (!callbackSummary) {
      if (runtimeArrayAliasMap.size > 0) {
        markAllRuntimeArraysUnknownAtPosition(`IterationCallbackUnknown.${memberName}`, callNode.getStart())
      }
      return true
    }

    if (iterableElements.length === 0) return true
    for (const elementExpression of iterableElements) {
      if (!elementExpression) continue
      const callbackArguments = []
      for (let index = 0; index <= currentItemParameterIndex; index += 1) {
        callbackArguments.push(undefined)
      }
      if (currentItemParameterIndex > 0) {
        const accumulatorExpression = unwrapExpression(iterationCallDescriptor.initialValueExpression || null)
        if (accumulatorExpression) {
          callbackArguments[0] = accumulatorExpression
        } else if (iterableElements[0]) {
          callbackArguments[0] = iterableElements[0]
        }
      }
      callbackArguments[currentItemParameterIndex] = elementExpression
      applyRuntimeFunctionSummaryAtCall(callbackSummary, callNode, {
        callArguments: callbackArguments,
        callPosition: callNode.getStart(),
      })
    }
    return true
  }

  const visit = (node) => {
    if (ts.isReturnStatement(node) && node.expression) {
      markArrayAliasesEscapedInExpression(node.expression, 'ReturnEscape', node.getStart())
    }

    if (ts.isCallExpression(node)) {
      const callee = normalizeRuntimeCalleeExpression(node.expression)
      let hasExplicitReflectConstructArrayArg = false
      let appliedRuntimeFunctionSummary = false
      const runtimeFunctionSummary = resolveRuntimeFunctionSummaryFromExpression(callee)
      if (runtimeFunctionSummary) {
        appliedRuntimeFunctionSummary = applyRuntimeFunctionSummaryAtCall(runtimeFunctionSummary, node)
      }
      const appliedRuntimeIterationSummary = applyRuntimeIterationCallbackSummaryAtCall(node, callee)

      if (ts.isPropertyAccessExpression(callee) || ts.isElementAccessExpression(callee)) {
        const baseExpr = unwrapExpression(callee.expression)
        const memberName = getStaticMemberName(callee)
        if (ts.isIdentifier(baseExpr) && runtimeArrayAliasMap.has(baseExpr.text)) {
          if (memberName && runtimeArrayMutatingMethodNameSet.has(memberName)) {
            markRuntimeArrayAliasState(baseExpr.text, 'tainted', `ArrayMutatingMethod.${memberName}`, node.getStart())
          } else if (!memberName) {
            markRuntimeArrayAliasState(baseExpr.text, 'unknown', 'ArrayDynamicMethodCall', node.getStart())
          }
        }

        if ((memberName === 'call' || memberName === 'apply') && (ts.isPropertyAccessExpression(callee.expression) || ts.isElementAccessExpression(callee.expression))) {
          const invokedMethodExpr = normalizeRuntimeCalleeExpression(callee.expression)
          const invokedMethodName = getStaticMemberName(invokedMethodExpr)
          if (invokedMethodName && runtimeArrayMutatingMethodNameSet.has(invokedMethodName)) {
            const thisArg = unwrapExpression(node.arguments[0] || null)
            if (ts.isIdentifier(thisArg) && runtimeArrayAliasMap.has(thisArg.text)) {
              markRuntimeArrayAliasState(
                thisArg.text,
                'tainted',
                `ArrayMutatingMethod.${invokedMethodName}.${memberName}`,
                node.getStart(),
              )
            } else if (thisArg) {
              markArrayAliasesEscapedInExpression(thisArg, 'ArrayMutatingMethodUnknownTarget', node.getStart())
            }
          }
        }
      }

      const workerConstructCallDescriptor = resolveRuntimeCallDescriptor(
        node,
        {
          runtimeMethodAliasMap,
          runtimeNamespaceAliasMap,
          runtimeGlobalContainerAliasMap,
          runtimeArrayMethodContainerMap,
          runtimeObjectMethodContainerMap,
          runtimeUnknownNamespaceAliasMap,
        },
        runtimeWorkerConstructorMethodSet,
      )
      if (workerConstructCallDescriptor?.method === 'Reflect.construct') {
        hasExplicitReflectConstructArrayArg = true
      }

      if (!appliedRuntimeFunctionSummary && !appliedRuntimeIterationSummary) {
        node.arguments.forEach((argNode, index) => {
          if (hasExplicitReflectConstructArrayArg && index === 1) return
          markArrayAliasesEscapedInExpression(argNode, 'CallArgumentEscape', node.getStart())
        })
      }

      if (
        !appliedRuntimeFunctionSummary &&
        !appliedRuntimeIterationSummary &&
        node.arguments.length === 0 &&
        runtimeArrayAliasMap.size > 0
      ) {
        const runtimeMethod = resolveRuntimeMethodFromExpression(
          callee,
          runtimeMethodAliasMap,
          runtimeNamespaceAliasMap,
          runtimeArrayMethodContainerMap,
          runtimeObjectMethodContainerMap,
          runtimeGlobalContainerAliasMap,
        )
        const memberName =
          ts.isPropertyAccessExpression(callee) || ts.isElementAccessExpression(callee)
            ? getStaticMemberName(callee)
            : null
        const looksLikePotentialFunctionAliasCall =
          ts.isIdentifier(callee) ||
          (ts.isElementAccessExpression(callee) && ts.isIdentifier(unwrapExpression(callee.expression))) ||
          (ts.isPropertyAccessExpression(callee) &&
            ts.isIdentifier(unwrapExpression(callee.expression)) &&
            (memberName === 'call' || memberName === 'apply' || memberName === 'bind'))
        if (!runtimeMethod && looksLikePotentialFunctionAliasCall) {
          for (const aliasName of runtimeArrayAliasMap.keys()) {
            markRuntimeArrayAliasState(aliasName, 'unknown', 'UnknownFunctionCallPotentialArraySideEffect', node.getStart())
          }
        }
      }
    }

    if (ts.isBinaryExpression(node) && isRuntimeWriteOperator(node.operatorToken.kind)) {
      const leftExpr = unwrapExpression(node.left)
      const rightExpr = unwrapExpression(node.right)

      if (ts.isElementAccessExpression(leftExpr)) {
        const baseExpr = unwrapExpression(leftExpr.expression)
        if (ts.isIdentifier(baseExpr) && runtimeArrayAliasMap.has(baseExpr.text)) {
          markRuntimeArrayAliasState(baseExpr.text, 'tainted', 'ArrayElementWrite', node.getStart())
        }
      } else if (ts.isPropertyAccessExpression(leftExpr)) {
        const baseExpr = unwrapExpression(leftExpr.expression)
        if (leftExpr.name.text === 'length' && ts.isIdentifier(baseExpr) && runtimeArrayAliasMap.has(baseExpr.text)) {
          markRuntimeArrayAliasState(baseExpr.text, 'tainted', 'ArrayLengthWrite', node.getStart())
        }
      } else if (
        ts.isIdentifier(leftExpr) &&
        runtimeArrayAliasMap.has(leftExpr.text) &&
        node.operatorToken.kind !== ts.SyntaxKind.EqualsToken
      ) {
        markRuntimeArrayAliasState(leftExpr.text, 'unknown', 'ArrayIdentifierCompoundWrite', node.getStart())
      }

      if (ts.isIdentifier(rightExpr) && runtimeArrayAliasMap.has(rightExpr.text) && !ts.isIdentifier(leftExpr)) {
        markRuntimeArrayAliasState(rightExpr.text, 'escaped', 'ArrayAliasEscapedByAssignment', node.getStart())
      }
    }

    if (ts.isForOfStatement(node)) {
      const forOfPosition = node.getStart()
      const iterationValueResult = resolveRuntimeIterationElementExpression(node.expression, forOfPosition)
      if (iterationValueResult.unresolved) {
        markRuntimeTrackedArraysUnknownForDestructure(node.expression, 'ForOf.UnresolvedIterable', forOfPosition)
      } else {
        const iterationValueExpression = iterationValueResult.expression
        if (ts.isVariableDeclarationList(node.initializer)) {
          if (node.initializer.declarations.length !== 1) {
            markRuntimeTrackedArraysUnknownForDestructure(
              node.expression,
              'ForOf.UnresolvedVariableDeclarationList',
              forOfPosition,
            )
          } else {
            const declaration = node.initializer.declarations[0]
            if (ts.isIdentifier(declaration.name)) {
              const bindResult = bindRuntimeArrayAliasFromSourceExpression(
                declaration.name.text,
                iterationValueExpression,
                forOfPosition,
                'ForOf.VariableBinding',
              )
              if (bindResult.unresolved) {
                markRuntimeTrackedArraysUnknownForDestructure(
                  iterationValueExpression,
                  'ForOf.VariableBindingUnresolved',
                  forOfPosition,
                )
              }
            } else if (ts.isArrayBindingPattern(declaration.name) || ts.isObjectBindingPattern(declaration.name)) {
              bindRuntimeArrayAliasesFromBindingPattern(
                declaration.name,
                iterationValueExpression,
                forOfPosition,
                'ForOf.BindingPattern',
              )
            } else {
              markRuntimeTrackedArraysUnknownForDestructure(
                iterationValueExpression,
                'ForOf.UnsupportedBinding',
                forOfPosition,
              )
            }
          }
        } else {
          const assignmentTarget = unwrapExpression(node.initializer)
          if (ts.isIdentifier(assignmentTarget)) {
            const bindResult = bindRuntimeArrayAliasFromSourceExpression(
              assignmentTarget.text,
              iterationValueExpression,
              forOfPosition,
              'ForOf.AssignmentBinding',
            )
            if (bindResult.unresolved) {
              markRuntimeTrackedArraysUnknownForDestructure(
                iterationValueExpression,
                'ForOf.AssignmentBindingUnresolved',
                forOfPosition,
              )
            }
          } else if (ts.isArrayLiteralExpression(assignmentTarget) || ts.isObjectLiteralExpression(assignmentTarget)) {
            bindRuntimeArrayAliasesFromAssignmentPattern(
              assignmentTarget,
              iterationValueExpression,
              forOfPosition,
              'ForOf.AssignmentPattern',
            )
          } else {
            markRuntimeTrackedArraysUnknownForDestructure(
              iterationValueExpression,
              'ForOf.UnsupportedInitializer',
              forOfPosition,
            )
          }
        }
      }
    }

    if (ts.isFunctionDeclaration(node) && node.name) {
      timerCallbackIdentifierSet.add(node.name.text)
      timerStringIdentifierSet.delete(node.name.text)
      setRuntimeConstructorFactoryAliasBinding(node.name.text, node)
    } else if (ts.isVariableDeclaration(node) && node.initializer) {
      const initializer = unwrapExpression(node.initializer)
      if (ts.isIdentifier(node.name)) {
        const varName = node.name.text
        updateTimerIdentifierBinding(varName, initializer)
        const namespaceName = resolveRuntimeNamespaceFromExpression(initializer, runtimeNamespaceAliasMap)
        if (namespaceName) {
          setRuntimeNamespaceAlias(varName, namespaceName)
        } else if (isPotentialRuntimeNamespaceConditional(initializer, runtimeNamespaceAliasMap)) {
          markRuntimeNamespaceAliasUnknown(varName, initializer.getText())
        }
        const globalContainer = resolveGlobalContainerFromExpression(initializer, runtimeGlobalContainerAliasMap)
        if (globalContainer) {
          runtimeGlobalContainerAliasMap.set(varName, globalContainer)
        }

        if (ts.isObjectLiteralExpression(initializer)) {
          objectLiteralVariableMap.set(varName, initializer)
        } else if (ts.isIdentifier(initializer) && objectLiteralVariableMap.has(initializer.text)) {
          objectLiteralVariableMap.set(varName, objectLiteralVariableMap.get(initializer.text))
        } else {
          objectLiteralVariableMap.delete(varName)
        }

        if (ts.isArrayLiteralExpression(initializer)) {
          arrayLiteralVariableMap.set(varName, initializer)
        } else if (ts.isIdentifier(initializer) && arrayLiteralVariableMap.has(initializer.text)) {
          arrayLiteralVariableMap.set(varName, arrayLiteralVariableMap.get(initializer.text))
        } else {
          arrayLiteralVariableMap.delete(varName)
        }
        bindRuntimeArrayAliasFromInitializer(varName, initializer, node.getStart())
        if (
          ts.isVariableDeclarationList(node.parent) &&
          ts.isVariableStatement(node.parent.parent) &&
          node.parent.parent.modifiers?.some((modifier) => modifier.kind === ts.SyntaxKind.ExportKeyword) &&
          runtimeArrayAliasMap.has(varName)
        ) {
          markRuntimeArrayAliasState(varName, 'escaped', 'ArrayEscapedByExport', node.getStart())
        }
        setRuntimeContainerAliases(varName, initializer)
        setRuntimeConstructorContainerAliases(varName, initializer)
        setRuntimeConstructorAliasBinding(varName, initializer)
        setRuntimeConstructorFactoryAliasBinding(varName, initializer)
        setRuntimeFunctionAliasBinding(varName, initializer)
        setRuntimeIterationInvocationAliasBinding(varName, initializer)
        setRuntimeIterationCallCallAliasBinding(varName, initializer)

        const runtimeMethod = resolveRuntimeMethodFromExpression(
          initializer,
          runtimeMethodAliasMap,
          runtimeNamespaceAliasMap,
          runtimeArrayMethodContainerMap,
          runtimeObjectMethodContainerMap,
          runtimeGlobalContainerAliasMap,
        )
        if (runtimeMethod) {
          runtimeMethodAliasMap.set(varName, runtimeMethod)
          if (runtimeMutatorSourceMethodSet.has(runtimeMethod)) {
            pushRuntimeMutatorSourceFinding('VariableDeclaration-mutator-source', initializer.getText())
          }
          if (runtimeCodegenSourceMethodSet.has(runtimeMethod)) {
            pushRuntimeCodegenSourceFinding('VariableDeclaration-codegen-source', initializer.getText())
          }
        } else {
          runtimeMethodAliasMap.delete(varName)
        }
      } else if (ts.isArrayBindingPattern(node.name) || ts.isObjectBindingPattern(node.name)) {
        bindRuntimeArrayAliasesFromBindingPattern(node.name, initializer, node.getStart(), 'VariableDestructure')
      }

      if (ts.isObjectBindingPattern(node.name)) {
        const namespaceName = resolveRuntimeNamespaceFromExpression(initializer, runtimeNamespaceAliasMap)
        const globalContainer = resolveGlobalContainerFromExpression(initializer, runtimeGlobalContainerAliasMap)
        for (const element of node.name.elements) {
          if (!ts.isIdentifier(element.name)) continue
          const localName = element.name.text
          const sourceKey = getBindingElementSourceKey(element)
          if (!sourceKey) {
            const propertyName = element.propertyName || null
            const keyInfo = classifyDestructureSourceKeyNode(propertyName)
            if (keyInfo.keyClass !== 'literal_key') {
              runtimeAliasRiskFindings.push({
                type: 'ObjectBindingPattern-non-literal-mutator-source',
                expressionText: keyInfo.expressionText || element.getText(),
              })
            }
            continue
          }

          if (namespaceName) {
            const runtimeMethod = classifyRuntimeMethodName(namespaceName, sourceKey)
            if (runtimeMethod) {
              runtimeMethodAliasMap.set(localName, runtimeMethod)
              if (runtimeMutatorSourceMethodSet.has(runtimeMethod)) {
                pushRuntimeMutatorSourceFinding('ObjectBindingPattern-mutator-source', element.getText())
              }
            }
          } else if (globalContainer) {
            if (sourceKey === 'Object' || sourceKey === 'Reflect' || sourceKey === 'URL') {
              setRuntimeNamespaceAlias(localName, sourceKey)
            } else if (sourceKey === 'Worker' || sourceKey === 'SharedWorker') {
              runtimeConstructorAliasMap.set(localName, {
                constructorName: sourceKey,
                boundArgs: [],
              })
              runtimeUnknownConstructorAliasMap.delete(localName)
            } else {
              const runtimeCodegenSource = classifyRuntimeCodegenGlobalName(sourceKey)
              if (runtimeCodegenSource) {
                runtimeMethodAliasMap.set(localName, runtimeCodegenSource)
                if (runtimeCodegenSourceMethodSet.has(runtimeCodegenSource)) {
                  pushRuntimeCodegenSourceFinding('ObjectBindingPattern-codegen-source', element.getText())
                }
              }
            }
          }
        }
      }
    } else if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
      const rhs = unwrapExpression(node.right)
      const leftExpr = unwrapExpression(node.left)

      if (ts.isIdentifier(leftExpr)) {
        const targetName = leftExpr.text
        updateTimerIdentifierBinding(targetName, rhs)
        const namespaceName = resolveRuntimeNamespaceFromExpression(rhs, runtimeNamespaceAliasMap)
        if (namespaceName) {
          setRuntimeNamespaceAlias(targetName, namespaceName)
        } else if (isPotentialRuntimeNamespaceConditional(rhs, runtimeNamespaceAliasMap)) {
          markRuntimeNamespaceAliasUnknown(targetName, rhs.getText())
        }
        const globalContainer = resolveGlobalContainerFromExpression(rhs, runtimeGlobalContainerAliasMap)
        if (globalContainer) {
          runtimeGlobalContainerAliasMap.set(targetName, globalContainer)
        }

        if (ts.isObjectLiteralExpression(rhs)) {
          objectLiteralVariableMap.set(targetName, rhs)
        } else if (ts.isIdentifier(rhs) && objectLiteralVariableMap.has(rhs.text)) {
          objectLiteralVariableMap.set(targetName, objectLiteralVariableMap.get(rhs.text))
        } else {
          objectLiteralVariableMap.delete(targetName)
        }

        if (ts.isArrayLiteralExpression(rhs)) {
          arrayLiteralVariableMap.set(targetName, rhs)
        } else if (ts.isIdentifier(rhs) && arrayLiteralVariableMap.has(rhs.text)) {
          arrayLiteralVariableMap.set(targetName, arrayLiteralVariableMap.get(rhs.text))
        } else {
          arrayLiteralVariableMap.delete(targetName)
        }
        bindRuntimeArrayAliasFromInitializer(targetName, rhs, node.getStart())
        setRuntimeContainerAliases(targetName, rhs)
        setRuntimeConstructorContainerAliases(targetName, rhs)
        setRuntimeConstructorAliasBinding(targetName, rhs)
        setRuntimeConstructorFactoryAliasBinding(targetName, rhs)
        setRuntimeFunctionAliasBinding(targetName, rhs)
        setRuntimeIterationInvocationAliasBinding(targetName, rhs)
        setRuntimeIterationCallCallAliasBinding(targetName, rhs)

        const runtimeMethod = resolveRuntimeMethodFromExpression(
          rhs,
          runtimeMethodAliasMap,
          runtimeNamespaceAliasMap,
          runtimeArrayMethodContainerMap,
          runtimeObjectMethodContainerMap,
          runtimeGlobalContainerAliasMap,
        )
        if (runtimeMethod) {
          runtimeMethodAliasMap.set(targetName, runtimeMethod)
          if (runtimeMutatorSourceMethodSet.has(runtimeMethod)) {
            pushRuntimeMutatorSourceFinding('Assignment-mutator-source', rhs.getText())
          }
          if (runtimeCodegenSourceMethodSet.has(runtimeMethod)) {
            pushRuntimeCodegenSourceFinding('Assignment-codegen-source', rhs.getText())
          }
        } else {
          runtimeMethodAliasMap.delete(targetName)
        }
      } else {
        if (ts.isArrayLiteralExpression(leftExpr) || ts.isObjectLiteralExpression(leftExpr)) {
          bindRuntimeArrayAliasesFromAssignmentPattern(leftExpr, rhs, node.getStart(), 'AssignmentDestructure')
        }

        const namespaceName = resolveRuntimeNamespaceFromExpression(rhs, runtimeNamespaceAliasMap)
        const globalContainer = resolveGlobalContainerFromExpression(rhs, runtimeGlobalContainerAliasMap)
        if (namespaceName) {
          const { aliases, unresolved } = extractObjectDestructureRuntimeAliases(leftExpr, namespaceName)
          for (const alias of aliases) {
            const runtimeMethod = classifyRuntimeMethodName(namespaceName, alias.sourceKey)
            if (runtimeMethod) {
              runtimeMethodAliasMap.set(alias.localName, runtimeMethod)
              if (runtimeMutatorSourceMethodSet.has(runtimeMethod)) {
                pushRuntimeMutatorSourceFinding(
                  'ObjectAssignmentPattern-mutator-source',
                  alias.expressionText || alias.localName,
                )
              }
            }
          }
          for (const expressionText of unresolved) {
            runtimeAliasRiskFindings.push({
              type: 'ObjectAssignmentPattern-non-literal-mutator-source',
              expressionText,
            })
          }
        } else if (globalContainer) {
          const { aliases, unresolved } = extractObjectDestructureRuntimeAliases(leftExpr, globalContainer)
          for (const alias of aliases) {
            if (alias.sourceKey === 'Object' || alias.sourceKey === 'Reflect' || alias.sourceKey === 'URL') {
              setRuntimeNamespaceAlias(alias.localName, alias.sourceKey)
            } else if (alias.sourceKey === 'Worker' || alias.sourceKey === 'SharedWorker') {
              runtimeConstructorAliasMap.set(alias.localName, {
                constructorName: alias.sourceKey,
                boundArgs: [],
              })
              runtimeUnknownConstructorAliasMap.delete(alias.localName)
            } else {
              const runtimeCodegenSource = classifyRuntimeCodegenGlobalName(alias.sourceKey)
              if (runtimeCodegenSource) {
                runtimeMethodAliasMap.set(alias.localName, runtimeCodegenSource)
                if (runtimeCodegenSourceMethodSet.has(runtimeCodegenSource)) {
                  pushRuntimeCodegenSourceFinding(
                    'ObjectAssignmentPattern-codegen-source',
                    alias.expressionText || alias.localName,
                  )
                }
              }
            }
          }
          for (const expressionText of unresolved) {
            runtimeAliasRiskFindings.push({
              type: 'ObjectAssignmentPattern-non-literal-namespace-source',
              expressionText,
            })
          }
        }
      }
    }

    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return {
    runtimeMethodAliasMap,
    runtimeConstructorAliasMap,
    runtimeUnknownConstructorAliasMap,
    runtimeConstructorFactoryAliasMap,
    runtimeUnknownConstructorFactoryAliasMap,
    runtimeNamespaceAliasMap,
    runtimeUnknownNamespaceAliasMap,
    runtimeGlobalContainerAliasMap,
    runtimeArrayMethodContainerMap,
    runtimeObjectMethodContainerMap,
    runtimeArrayConstructorContainerMap,
    runtimeObjectConstructorContainerMap,
    runtimeAliasRiskFindings,
    runtimeMutatorSourceFindings,
    runtimeCodegenSourceFindings,
    timerCallbackIdentifierSet,
    timerStringIdentifierSet,
    objectLiteralVariableMap,
    arrayLiteralVariableMap,
    runtimeArrayStateMap,
    runtimeArrayAliasMap,
  }
}

const collectRuntimeSourceReferenceFindings = (
  sourceFile,
  runtimeContext,
  {
    methodSet,
    typePrefix,
    includeUnknownNamespaceMember = false,
    includeUnknownGlobalNamespaceMember = false,
    includeReflectGetUnknownMember = false,
  },
) => {
  const findings = []
  const seen = new Set()
  const runtimeMethodAliasMap = runtimeContext.runtimeMethodAliasMap || new Map()
  const runtimeNamespaceAliasMap = runtimeContext.runtimeNamespaceAliasMap || new Map()
  const runtimeGlobalContainerAliasMap = runtimeContext.runtimeGlobalContainerAliasMap || new Map()
  const runtimeArrayMethodContainerMap = runtimeContext.runtimeArrayMethodContainerMap || new Map()
  const runtimeObjectMethodContainerMap = runtimeContext.runtimeObjectMethodContainerMap || new Map()

  const pushFinding = (type, expressionText) => {
    const normalized = normalizeComputedKeyExpr(expressionText || '')
    const dedupeKey = `${type}|${normalized}`
    if (seen.has(dedupeKey)) return
    seen.add(dedupeKey)
    findings.push({ type, expressionText: normalized })
  }

  const isSafeTimerReflectApplyCall = (callNode) => {
    const callDescriptor = resolveRuntimeCallDescriptor(callNode, runtimeContext, runtimeTimerMethodSet)
    if (!callDescriptor || !runtimeTimerMethodSet.has(callDescriptor.method || '')) return false
    if (callDescriptor.invoke !== 'reflect_apply') return false
    const normalizedCall = normalizeRuntimeCallArguments(callNode, callDescriptor)
    if (normalizedCall.unresolved) return false
    const argCheck = analyzeTimerFirstArgument(normalizedCall.args[0] || null, runtimeContext)
    return !argCheck.blocked
  }

  const isSafeIterationReflectApplyCall = (callNode) => {
    const targetMethodName = resolveStaticArrayPrototypeIterationMethodName(callNode.arguments[0] || null)
    return Boolean(targetMethodName)
  }

  const resolveChainedCalleeCallExpression = (startNode) => {
    let current = startNode
    while (
      current?.parent &&
      (ts.isPropertyAccessExpression(current.parent) || ts.isElementAccessExpression(current.parent)) &&
      current.parent.expression === current
    ) {
      current = current.parent
    }
    if (current?.parent && ts.isCallExpression(current.parent) && current.parent.expression === current) {
      return current.parent
    }
    return null
  }

  const isSafeIterationCallCallReference = (node) => {
    const callNode = resolveChainedCalleeCallExpression(node)
    if (!callNode) return false
    const callTarget = normalizeRuntimeCalleeExpression(callNode.expression)
    if (!(callTarget && (ts.isPropertyAccessExpression(callTarget) || ts.isElementAccessExpression(callTarget)))) {
      return false
    }
    if (getStaticMemberName(callTarget) !== 'call') return false
    const innerCallTarget = normalizeRuntimeCalleeExpression(callTarget.expression)
    if (!(innerCallTarget && (ts.isPropertyAccessExpression(innerCallTarget) || ts.isElementAccessExpression(innerCallTarget)))) {
      return false
    }
    if (getStaticMemberName(innerCallTarget) !== 'call') return false
    const targetMethodName = resolveStaticArrayPrototypeIterationMethodName(callNode.arguments[0] || null)
    return Boolean(targetMethodName)
  }

  const visit = (node) => {
    if (
      ts.isIdentifier(node) ||
      ts.isPropertyAccessExpression(node) ||
      ts.isElementAccessExpression(node)
    ) {
      const runtimeMethod = resolveRuntimeMethodFromExpression(
        node,
        runtimeMethodAliasMap,
        runtimeNamespaceAliasMap,
        runtimeArrayMethodContainerMap,
        runtimeObjectMethodContainerMap,
        runtimeGlobalContainerAliasMap,
      )
      if (runtimeMethod && methodSet.has(runtimeMethod)) {
        if (
          runtimeMethod === 'Reflect.apply' &&
          node.parent &&
          ts.isCallExpression(node.parent) &&
          node.parent.expression === node &&
          (isSafeTimerReflectApplyCall(node.parent) || isSafeIterationReflectApplyCall(node.parent))
        ) {
          // Allow safe timer callback usage through Reflect.apply(timer, thisArg, [callback, delay]).
        } else if (runtimeMethod === 'Global.Function' && isSafeIterationCallCallReference(node)) {
          // Allow Function.prototype.call.call(Array.prototype.xxx, ...) call forwarding without treating it as codegen source.
        } else {
          pushFinding(`${typePrefix}Reference`, node.getText(sourceFile))
        }
      }

      if (ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node)) {
        const memberName = getStaticMemberName(node)
        const baseExpr = unwrapExpression(node.expression)
        const namespaceName = resolveRuntimeNamespaceFromExpression(baseExpr, runtimeNamespaceAliasMap)
        if (includeUnknownNamespaceMember && namespaceName && !memberName) {
          pushFinding(`${typePrefix}UnknownNamespaceMember`, node.getText(sourceFile))
        }
        const globalContainer = resolveGlobalContainerFromExpression(baseExpr, runtimeGlobalContainerAliasMap)
        if (includeUnknownGlobalNamespaceMember && globalContainer && !memberName) {
          pushFinding(`${typePrefix}UnknownGlobalNamespaceMember`, node.getText(sourceFile))
        }
      }
    }

    if (ts.isCallExpression(node)) {
      const runtimeMethod = resolveRuntimeMethodFromExpression(
        node,
        runtimeMethodAliasMap,
        runtimeNamespaceAliasMap,
        runtimeArrayMethodContainerMap,
        runtimeObjectMethodContainerMap,
        runtimeGlobalContainerAliasMap,
      )
      if (runtimeMethod && methodSet.has(runtimeMethod)) {
        pushFinding(`${typePrefix}CallReference`, node.getText(sourceFile))
      }

      const reflectGetResolved = resolveRuntimeReflectGetCall(node, runtimeContext)
      if (reflectGetResolved?.method && methodSet.has(reflectGetResolved.method)) {
        pushFinding(`${typePrefix}ReflectGetReference`, node.getText(sourceFile))
      } else if (includeReflectGetUnknownMember && reflectGetResolved?.unresolved) {
        pushFinding(`${typePrefix}ReflectGetUnknownMember`, reflectGetResolved.expressionText || node.getText(sourceFile))
      }
    }

    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return findings
}

const collectRuntimeMutatorSourceReferenceFindings = (sourceFile, runtimeContext) =>
  collectRuntimeSourceReferenceFindings(sourceFile, runtimeContext, {
    methodSet: runtimeMutatorSourceMethodSet,
    typePrefix: 'RuntimeMutatorSource',
    includeUnknownNamespaceMember: true,
    includeUnknownGlobalNamespaceMember: true,
    includeReflectGetUnknownMember: true,
  })

const collectRuntimeCodegenSourceReferenceFindings = (sourceFile, runtimeContext) =>
  collectRuntimeSourceReferenceFindings(sourceFile, runtimeContext, {
    methodSet: runtimeCodegenSourceMethodSet,
    typePrefix: 'RuntimeCodegenSource',
    includeUnknownGlobalNamespaceMember: true,
  })

const analyzeTimerFirstArgument = (firstArg, runtimeContext) => {
  if (!firstArg) {
    return { blocked: true, type: 'RuntimeTimerCallMissingFirstArg', expressionText: '' }
  }
  const staticString = resolveStaticStringValue(firstArg)
  if (staticString !== null) {
    return {
      blocked: true,
      type: 'RuntimeTimerCallStringArgument',
      expressionText: firstArg.getText ? firstArg.getText() : staticString,
    }
  }

  const target = unwrapExpression(firstArg)
  if (ts.isArrowFunction(target) || ts.isFunctionExpression(target)) {
    return { blocked: false }
  }
  if (ts.isIdentifier(target)) {
    const timerCallbackIdentifierSet = runtimeContext.timerCallbackIdentifierSet || new Set()
    const timerStringIdentifierSet = runtimeContext.timerStringIdentifierSet || new Set()
    if (timerCallbackIdentifierSet.has(target.text)) {
      return { blocked: false }
    }
    if (timerStringIdentifierSet.has(target.text)) {
      return {
        blocked: true,
        type: 'RuntimeTimerCallStringIdentifierArgument',
        expressionText: target.getText(),
      }
    }
    return {
      blocked: true,
      type: 'RuntimeTimerCallUnresolvedIdentifierArgument',
      expressionText: target.getText(),
    }
  }

  return {
    blocked: true,
    type: 'RuntimeTimerCallUnresolvedArgument',
    expressionText: firstArg.getText ? firstArg.getText() : '',
  }
}

const dynamicImportAllowedLocalPrefixes = ['@/', './', '../']
const workerAllowedLocalPrefixes = ['@/', './', '../']
const scriptSrcAllowedLocalPrefixes = ['/', './', '../', '@/']
const runtimeProtocolPrefixRegex = /^[a-z][a-z0-9+.-]*:/i
const runtimeCodeLoadingProtocolRegex = /^(?:data|blob|javascript|http|https):/i

const hasRuntimeProtocolPrefix = (value) => {
  const normalized = `${value || ''}`.trim().toLowerCase()
  if (!normalized) return false
  if (normalized.startsWith('//')) return true
  return runtimeProtocolPrefixRegex.test(normalized)
}

const hasRuntimeCodeLoadingProtocol = (value) => {
  const normalized = `${value || ''}`.trim().toLowerCase()
  if (!normalized) return false
  if (normalized.startsWith('//')) return true
  return runtimeCodeLoadingProtocolRegex.test(normalized)
}

const isSafeStaticDynamicImportPath = (value) => {
  const text = `${value || ''}`.trim()
  if (!text) return false
  return dynamicImportAllowedLocalPrefixes.some((prefix) => text.startsWith(prefix))
}

const isSafeStaticWorkerPath = (value) => {
  const text = `${value || ''}`.trim()
  if (!text) return false
  return workerAllowedLocalPrefixes.some((prefix) => text.startsWith(prefix))
}

const isSafeStaticScriptSrcPath = (value) => {
  const text = `${value || ''}`.trim()
  if (!text) return false
  return scriptSrcAllowedLocalPrefixes.some((prefix) => text.startsWith(prefix))
}

const classifyDynamicImportSourceArgument = (sourceArg) => {
  if (!sourceArg) {
    return {
      blocked: true,
      type: 'RuntimeDynamicImportMissingSource',
      expressionText: '',
    }
  }
  const staticValue = resolveStaticStringValue(sourceArg)
  if (staticValue !== null) {
    const trimmed = `${staticValue}`.trim()
    if (hasRuntimeProtocolPrefix(trimmed)) {
      return {
        blocked: true,
        type: 'RuntimeDynamicImportForbiddenProtocol',
        expressionText: sourceArg.getText ? sourceArg.getText() : trimmed,
      }
    }
    if (!isSafeStaticDynamicImportPath(trimmed)) {
      return {
        blocked: true,
        type: 'RuntimeDynamicImportNonLocalLiteral',
        expressionText: sourceArg.getText ? sourceArg.getText() : trimmed,
      }
    }
    return { blocked: false }
  }
  return {
    blocked: true,
    type: 'RuntimeDynamicImportUnresolvedSource',
    expressionText: sourceArg.getText ? sourceArg.getText() : '',
  }
}

const isImportExpressionCall = (callNode) => {
  const callee = unwrapExpression(callNode.expression)
  if (!callee) return false
  return callee.kind === ts.SyntaxKind.ImportKeyword
}

const isImportMetaUrlExpression = (expression) => {
  const target = unwrapExpression(expression)
  if (!target || !ts.isPropertyAccessExpression(target)) return false
  if (target.name.text !== 'url') return false
  const base = unwrapExpression(target.expression)
  return Boolean(
    base &&
      ts.isMetaProperty(base) &&
      base.keywordToken === ts.SyntaxKind.ImportKeyword &&
      base.name.text === 'meta',
  )
}

const resolveGlobalMemberNamespace = (expression, memberName) => {
  const target = unwrapExpression(expression)
  if (!target) return null
  if (ts.isIdentifier(target) && target.text === memberName) return memberName
  if (ts.isPropertyAccessExpression(target) || ts.isElementAccessExpression(target)) {
    const currentMemberName = getStaticMemberName(target)
    const baseExpr = unwrapExpression(target.expression)
    if (
      currentMemberName === memberName &&
      ts.isIdentifier(baseExpr) &&
      (baseExpr.text === 'window' || baseExpr.text === 'globalThis')
    ) {
      return `${baseExpr.text}.${memberName}`
    }
  }
  return null
}

const isSafeWorkerNewUrlExpression = (expression) => {
  const target = unwrapExpression(expression)
  if (!target || !ts.isNewExpression(target)) return false
  if (!resolveGlobalMemberNamespace(target.expression, 'URL')) return false
  const args = target.arguments || []
  if (args.length < 2) return false
  const workerPath = resolveStaticStringValue(args[0])
  if (workerPath === null || !isSafeStaticWorkerPath(workerPath)) return false
  return isImportMetaUrlExpression(args[1])
}

const classifyWorkerSourceArgument = (sourceArg, isBlobUrlSourceExpression) => {
  if (!sourceArg) {
    return {
      blocked: true,
      type: 'RuntimeWorkerMissingSource',
      expressionText: '',
    }
  }
  if (isBlobUrlSourceExpression(sourceArg)) {
    return {
      blocked: true,
      type: 'RuntimeWorkerBlobUrlLoad',
      expressionText: sourceArg.getText ? sourceArg.getText() : '',
    }
  }
  const staticValue = resolveStaticStringValue(sourceArg)
  if (staticValue !== null) {
    const trimmed = `${staticValue}`.trim()
    if (hasRuntimeCodeLoadingProtocol(trimmed)) {
      return {
        blocked: true,
        type: 'RuntimeWorkerForbiddenProtocol',
        expressionText: sourceArg.getText ? sourceArg.getText() : trimmed,
      }
    }
    return {
      blocked: true,
      type: 'RuntimeWorkerNonCanonicalLiteral',
      expressionText: sourceArg.getText ? sourceArg.getText() : trimmed,
    }
  }

  if (isSafeWorkerNewUrlExpression(sourceArg)) {
    return { blocked: false }
  }

  return {
    blocked: true,
    type: 'RuntimeWorkerUnresolvedSource',
    expressionText: sourceArg.getText ? sourceArg.getText() : '',
  }
}

const resolveWorkerConstructorDescriptor = (expression, runtimeContext) =>
  resolveRuntimeWorkerConstructorFromExpression(
    expression,
    runtimeContext.runtimeConstructorAliasMap || new Map(),
    runtimeContext.runtimeUnknownConstructorAliasMap || new Map(),
    runtimeContext.runtimeConstructorFactoryAliasMap || new Map(),
    runtimeContext.runtimeUnknownConstructorFactoryAliasMap || new Map(),
    runtimeContext.runtimeNamespaceAliasMap || new Map(),
    runtimeContext.runtimeArrayConstructorContainerMap || new Map(),
    runtimeContext.runtimeObjectConstructorContainerMap || new Map(),
    runtimeContext.runtimeGlobalContainerAliasMap || new Map(),
  )

const resolveRuntimeInvocationArgConfidence = (args, hasSpread, unresolved) => {
  if (unresolved) {
    return hasSpread ? 'unsafe_spread' : 'unknown'
  }
  const firstArg = args[0] || null
  if (!firstArg) {
    return hasSpread ? 'unknown' : 'static'
  }
  if (resolveStaticStringValue(firstArg) !== null || isSafeWorkerNewUrlExpression(firstArg)) {
    return 'static_url_like'
  }
  if (
    ts.isNumericLiteral(firstArg) ||
    ts.isStringLiteral(firstArg) ||
    ts.isNoSubstitutionTemplateLiteral(firstArg) ||
    firstArg.kind === ts.SyntaxKind.TrueKeyword ||
    firstArg.kind === ts.SyntaxKind.FalseKeyword ||
    firstArg.kind === ts.SyntaxKind.NullKeyword
  ) {
    return 'static'
  }
  return 'unknown'
}

const resolveRuntimeArrayStateAtUsage = (runtimeContext, identifierName, usagePosition) => {
  const aliasMap = runtimeContext.runtimeArrayAliasMap || new Map()
  const stateMap = runtimeContext.runtimeArrayStateMap || new Map()
  const arrayId = aliasMap.get(identifierName)
  if (!arrayId) return null
  const state = stateMap.get(arrayId) || null
  if (!state) return null

  const events = state.mutation_events || []
  let effectiveStatus = 'clean'
  const reasons = []
  for (const event of events) {
    if (usagePosition !== null && usagePosition !== undefined && Number.isFinite(usagePosition)) {
      if (event.position > usagePosition) continue
    }
    reasons.push(event.reason)
    if ((runtimeArrayStatusRank[event.status] || 0) > (runtimeArrayStatusRank[effectiveStatus] || 0)) {
      effectiveStatus = event.status
    }
  }

  return {
    array_id: state.array_id,
    initial_elements: state.initial_elements || [],
    effective_status: effectiveStatus,
    reasons,
    declaration_position: state.declaration_position,
    last_safe_position: state.last_safe_position,
  }
}

const resolveRuntimeArrayElementsFromIdentifier = (identifierNode, runtimeContext, usagePosition) => {
  const arrayStateAtUsage = resolveRuntimeArrayStateAtUsage(runtimeContext, identifierNode.text, usagePosition)
  if (arrayStateAtUsage) {
    if (arrayStateAtUsage.effective_status === 'clean') {
      return {
        unresolved: false,
        elements: arrayStateAtUsage.initial_elements,
        expressionText: identifierNode.text,
      }
    }
    return {
      unresolved: true,
      elements: [],
      expressionText: `${identifierNode.text}#${arrayStateAtUsage.effective_status}`,
    }
  }

  const mappedArray = runtimeContext.arrayLiteralVariableMap?.get(identifierNode.text) || null
  if (mappedArray) {
    return {
      unresolved: false,
      elements: Array.from(mappedArray.elements),
      expressionText: identifierNode.text,
    }
  }

  return {
    unresolved: true,
    elements: [],
    expressionText: identifierNode.text,
  }
}

const resolveRuntimeSpreadArgumentElements = (spreadExpression, runtimeContext, depth = 0) => {
  if (depth > 12) {
    return {
      unresolved: true,
      args: [],
      hasSpread: true,
      expressionText: spreadExpression?.getText ? spreadExpression.getText() : '',
    }
  }
  const target = unwrapExpression(spreadExpression)
  if (!target) {
    return {
      unresolved: true,
      args: [],
      hasSpread: true,
      expressionText: '',
    }
  }

  if (ts.isArrayLiteralExpression(target)) {
    return resolveRuntimeInvocationArgumentsFromNodes(Array.from(target.elements), runtimeContext, depth + 1)
  }

  if (ts.isIdentifier(target)) {
    const resolvedArray = resolveRuntimeArrayElementsFromIdentifier(target, runtimeContext, target.getStart())
    if (!resolvedArray.unresolved) {
      return resolveRuntimeInvocationArgumentsFromNodes(resolvedArray.elements, runtimeContext, depth + 1)
    }
    return {
      unresolved: true,
      args: [],
      hasSpread: true,
      expressionText: resolvedArray.expressionText || target.text,
    }
  }

  return {
    unresolved: true,
    args: [],
    hasSpread: true,
    expressionText: target.getText ? target.getText() : '',
  }
}

const resolveRuntimeInvocationArgumentsFromNodes = (argumentNodes, runtimeContext, depth = 0) => {
  if (depth > 12) {
    return {
      unresolved: true,
      args: [],
      hasSpread: false,
      arg_confidence: 'unknown',
      expressionText: '',
    }
  }

  const normalizedArgs = []
  let hasSpread = false
  let unresolvedExpressionText = ''

  for (const rawArg of argumentNodes) {
    const arg = unwrapExpression(rawArg)
    if (!arg) {
      return {
        unresolved: true,
        args: [],
        hasSpread,
        arg_confidence: resolveRuntimeInvocationArgConfidence([], hasSpread, true),
        expressionText: unresolvedExpressionText || '',
      }
    }

    if (ts.isSpreadElement(arg)) {
      hasSpread = true
      const spreadResolved = resolveRuntimeSpreadArgumentElements(arg.expression, runtimeContext, depth + 1)
      if (spreadResolved.unresolved) {
        unresolvedExpressionText = spreadResolved.expressionText || arg.getText()
        return {
          unresolved: true,
          args: [],
          hasSpread: true,
          arg_confidence: resolveRuntimeInvocationArgConfidence([], true, true),
          expressionText: unresolvedExpressionText,
        }
      }
      normalizedArgs.push(...spreadResolved.args)
      continue
    }

    if (ts.isOmittedExpression(arg)) {
      unresolvedExpressionText = arg.getText ? arg.getText() : ''
      return {
        unresolved: true,
        args: [],
        hasSpread,
        arg_confidence: resolveRuntimeInvocationArgConfidence([], hasSpread, true),
        expressionText: unresolvedExpressionText,
      }
    }

    normalizedArgs.push(arg)
  }

  return {
    unresolved: false,
    args: normalizedArgs,
    hasSpread,
    arg_confidence: resolveRuntimeInvocationArgConfidence(normalizedArgs, hasSpread, false),
    expressionText: '',
  }
}

const resolveRuntimeArgumentArrayElements = (argumentExpression, runtimeContext) => {
  const target = unwrapExpression(argumentExpression)
  if (!target) {
    return { unresolved: true, args: [], hasSpread: false, arg_confidence: 'unknown', expressionText: '' }
  }

  if (ts.isArrayLiteralExpression(target)) {
    const resolved = resolveRuntimeInvocationArgumentsFromNodes(Array.from(target.elements), runtimeContext)
    if (resolved.unresolved) {
      return {
        unresolved: true,
        args: [],
        hasSpread: resolved.hasSpread,
        arg_confidence: resolved.arg_confidence,
        expressionText: resolved.expressionText || target.getText(),
      }
    }
    return {
      unresolved: false,
      args: resolved.args,
      hasSpread: resolved.hasSpread,
      arg_confidence: resolved.arg_confidence,
      expressionText: target.getText(),
    }
  }

  if (ts.isIdentifier(target)) {
    const resolvedArray = resolveRuntimeArrayElementsFromIdentifier(target, runtimeContext, target.getStart())
    if (!resolvedArray.unresolved) {
      return resolveRuntimeInvocationArgumentsFromNodes(resolvedArray.elements, runtimeContext)
    }
    return {
      unresolved: true,
      args: [],
      hasSpread: false,
      arg_confidence: 'unknown',
      expressionText: resolvedArray.expressionText || target.text,
    }
  }

  return {
    unresolved: true,
    args: [],
    hasSpread: false,
    arg_confidence: 'unknown',
    expressionText: target.getText ? target.getText() : '',
  }
}

const resolveWorkerInvocationSourceArg = (ctorDescriptor, runtimeArgs = []) => {
  const combined = [...(ctorDescriptor?.boundArgs || []), ...runtimeArgs]
  return combined[0] || null
}

const classifyUnknownWorkerConstructTargetSourceStrict = (sourceArg, isBlobUrlSourceExpression) => {
  if (!sourceArg) return { blocked: false }

  const target = unwrapExpression(sourceArg)
  if (!target || isBlobUrlSourceExpression(sourceArg)) {
    return {
      blocked: true,
      type: 'RuntimeWorkerConstructorUnknownTarget',
      expressionText: sourceArg.getText ? sourceArg.getText() : '',
    }
  }

  const staticValue = resolveStaticStringValue(sourceArg)
  if (staticValue !== null) {
    return {
      blocked: true,
      type: 'RuntimeWorkerConstructorUnknownTarget',
      expressionText: sourceArg.getText ? sourceArg.getText() : `${staticValue}`.trim(),
    }
  }

  if (isSafeWorkerNewUrlExpression(sourceArg)) {
    return {
      blocked: true,
      type: 'RuntimeWorkerConstructorUnknownTarget',
      expressionText: sourceArg.getText ? sourceArg.getText() : '',
    }
  }

  if (
    ts.isIdentifier(target) ||
    ts.isTemplateExpression(target) ||
    ts.isCallExpression(target) ||
    ts.isConditionalExpression(target) ||
    ts.isPropertyAccessExpression(target) ||
    ts.isElementAccessExpression(target) ||
    ts.isBinaryExpression(target) ||
    ts.isTaggedTemplateExpression(target)
  ) {
    return {
      blocked: true,
      type: 'RuntimeWorkerConstructorUnknownTarget',
      expressionText: sourceArg.getText ? sourceArg.getText() : '',
    }
  }

  return {
    blocked: false,
  }
}

const classifyScriptSrcSourceArgument = (sourceArg, isBlobUrlSourceExpression) => {
  if (!sourceArg) {
    return {
      blocked: true,
      type: 'RuntimeScriptSrcMissingSource',
      expressionText: '',
    }
  }
  if (isBlobUrlSourceExpression(sourceArg)) {
    return {
      blocked: true,
      type: 'RuntimeScriptBlobUrlLoad',
      expressionText: sourceArg.getText ? sourceArg.getText() : '',
    }
  }
  const staticValue = resolveStaticStringValue(sourceArg)
  if (staticValue !== null) {
    const trimmed = `${staticValue}`.trim()
    if (hasRuntimeCodeLoadingProtocol(trimmed)) {
      return {
        blocked: true,
        type: 'RuntimeScriptForbiddenProtocol',
        expressionText: sourceArg.getText ? sourceArg.getText() : trimmed,
      }
    }
    if (!isSafeStaticScriptSrcPath(trimmed)) {
      return {
        blocked: true,
        type: 'RuntimeScriptNonLocalLiteral',
        expressionText: sourceArg.getText ? sourceArg.getText() : trimmed,
      }
    }
    return { blocked: false }
  }
  return {
    blocked: true,
    type: 'RuntimeScriptUnresolvedSource',
    expressionText: sourceArg.getText ? sourceArg.getText() : '',
  }
}

const isSrcAssignmentLeft = (leftExpression) => {
  const left = unwrapExpression(leftExpression)
  if (!left) return false
  if (!(ts.isPropertyAccessExpression(left) || ts.isElementAccessExpression(left))) return false
  return getStaticMemberName(left) === 'src'
}

const resolveScriptSrcSetAttributeCall = (callNode) => {
  const callee = unwrapExpression(callNode.expression)
  if (!callee) return null
  if (!(ts.isPropertyAccessExpression(callee) || ts.isElementAccessExpression(callee))) return null
  if (getStaticMemberName(callee) !== 'setAttribute') return null
  const attrArg = callNode.arguments[0] || null
  const attrName = resolveStaticStringValue(attrArg)
  if (!attrName || `${attrName}`.trim().toLowerCase() !== 'src') return null
  return {
    valueArg: callNode.arguments[1] || null,
  }
}

const collectRuntimeDynamicModuleLoadingFindings = (sourceFile, runtimeContext) => {
  const findings = []
  const seen = new Set()
  const blobUrlIdentifierSet = new Set()

  const pushFinding = (type, expressionText) => {
    const normalized = normalizeComputedKeyExpr(expressionText || '')
    const dedupeKey = `${type}|${normalized}`
    if (seen.has(dedupeKey)) return
    seen.add(dedupeKey)
    findings.push({ type, expressionText: normalized })
  }

  const resolveBlobUrlCallDescriptor = (callNode) => {
    const callDescriptor = resolveRuntimeCallDescriptor(callNode, runtimeContext, runtimeBlobUrlMethodSet)
    if (!callDescriptor) return null
    if (callDescriptor.method && runtimeBlobUrlMethodSet.has(callDescriptor.method)) {
      const normalizedCall = normalizeRuntimeCallArguments(callNode, callDescriptor)
      if (normalizedCall.unresolved) {
        return { createsBlobUrl: true, unresolved: true, args: [] }
      }
      return { createsBlobUrl: true, unresolved: false, args: normalizedCall.args }
    }
    if (callDescriptor.unresolvedTarget) {
      return { createsBlobUrl: false, unresolvedTarget: true }
    }
    return null
  }

  const isBlobUrlSourceExpression = (expression) => {
    const target = unwrapExpression(expression)
    if (!target) return false
    if (ts.isIdentifier(target) && blobUrlIdentifierSet.has(target.text)) return true
    if (ts.isCallExpression(target)) {
      const blobCall = resolveBlobUrlCallDescriptor(target)
      if (blobCall?.createsBlobUrl) return true
    }
    return false
  }

  const resolveCtorKindForDescriptor = (ctorExpression) => {
    const workerCtorDescriptor = resolveWorkerConstructorDescriptor(ctorExpression, runtimeContext)
    if (workerCtorDescriptor?.unresolved) {
      return {
        ctor_kind: 'unknown',
        ctor_confidence: 'unknown',
        workerCtorDescriptor,
      }
    }
    if (workerCtorDescriptor?.constructorName === 'Worker') {
      return {
        ctor_kind: 'worker',
        ctor_confidence: 'known',
        workerCtorDescriptor,
      }
    }
    if (workerCtorDescriptor?.constructorName === 'SharedWorker') {
      return {
        ctor_kind: 'shared_worker',
        ctor_confidence: 'known',
        workerCtorDescriptor,
      }
    }
    const knownSafeCtor = resolveKnownSafeConstructorFromExpression(
      ctorExpression,
      runtimeContext.runtimeGlobalContainerAliasMap || new Map(),
    )
    if (knownSafeCtor) {
      return {
        ctor_kind: 'safe_known_constructor',
        ctor_confidence: 'known',
        workerCtorDescriptor: null,
      }
    }
    return {
      ctor_kind: 'unknown',
      ctor_confidence: 'unknown',
      workerCtorDescriptor: null,
    }
  }

  const resolveConstructorInvocationDescriptorFromNewExpression = (newNode) => {
    const ctorInfo = resolveCtorKindForDescriptor(newNode.expression)
    const normalizedArgs = resolveRuntimeInvocationArgumentsFromNodes(Array.from(newNode.arguments || []), runtimeContext)
    if (normalizedArgs.unresolved) {
      return {
        ctor_kind: 'unknown',
        ctor_confidence: 'unknown',
        url_expression: null,
        options_expression: null,
        source_trace: newNode.getText(sourceFile),
        unresolved_constructor: false,
        unresolved_expression: normalizedArgs.expressionText || '',
        unresolved_args: true,
        has_spread: normalizedArgs.hasSpread,
        arg_confidence: normalizedArgs.arg_confidence,
      }
    }
    const runtimeArgs = normalizedArgs.args
    const sourceArg =
      ctorInfo.workerCtorDescriptor?.constructorName && !ctorInfo.workerCtorDescriptor.unresolved
        ? resolveWorkerInvocationSourceArg(ctorInfo.workerCtorDescriptor, runtimeArgs)
        : runtimeArgs[0] || null
    return {
      ctor_kind: ctorInfo.ctor_kind,
      ctor_confidence: ctorInfo.ctor_confidence,
      url_expression: sourceArg,
      options_expression: runtimeArgs[1] || null,
      source_trace: newNode.getText(sourceFile),
      unresolved_constructor: Boolean(ctorInfo.workerCtorDescriptor?.unresolved),
      unresolved_expression: ctorInfo.workerCtorDescriptor?.expressionText || '',
      unresolved_args: false,
      has_spread: normalizedArgs.hasSpread,
      arg_confidence: normalizedArgs.arg_confidence,
    }
  }

  const resolveConstructorInvocationDescriptorFromReflectConstructCall = (callNode, normalizedCall) => {
    const ctorExpr = normalizedCall.args[0] || null
    const ctorInfo = resolveCtorKindForDescriptor(ctorExpr)
    const argsArrayExpr = normalizedCall.args[1] || null
    const runtimeArgs = resolveRuntimeArgumentArrayElements(argsArrayExpr, runtimeContext)
    if (runtimeArgs.unresolved) {
      return {
        ctor_kind: 'unknown',
        ctor_confidence: 'unknown',
        url_expression: null,
        options_expression: null,
        source_trace: callNode.getText(sourceFile),
        unresolved_constructor: false,
        unresolved_expression: runtimeArgs.expressionText || '',
        unresolved_args: true,
        has_spread: runtimeArgs.hasSpread,
        arg_confidence: runtimeArgs.arg_confidence,
      }
    }
    const sourceArg =
      ctorInfo.workerCtorDescriptor?.constructorName && !ctorInfo.workerCtorDescriptor.unresolved
        ? resolveWorkerInvocationSourceArg(ctorInfo.workerCtorDescriptor, runtimeArgs.args)
        : runtimeArgs.args[0] || null
    return {
      ctor_kind: ctorInfo.ctor_kind,
      ctor_confidence: ctorInfo.ctor_confidence,
      url_expression: sourceArg,
      options_expression: runtimeArgs.args[1] || null,
      source_trace: callNode.getText(sourceFile),
      unresolved_constructor: Boolean(ctorInfo.workerCtorDescriptor?.unresolved),
      unresolved_expression: ctorInfo.workerCtorDescriptor?.expressionText || '',
      unresolved_args: false,
      has_spread: runtimeArgs.hasSpread,
      arg_confidence: runtimeArgs.arg_confidence,
    }
  }

  const applyConstructorInvocationDescriptor = (descriptor) => {
    if (descriptor.unresolved_constructor) {
      pushFinding(
        'RuntimeWorkerConstructorUnresolved',
        descriptor.unresolved_expression || descriptor.source_trace || '',
      )
      return
    }
    if (descriptor.unresolved_args) {
      pushFinding(
        'RuntimeWorkerConstructUnresolvedArguments',
        descriptor.unresolved_expression || descriptor.source_trace || '',
      )
      return
    }

    if (descriptor.ctor_kind === 'worker' || descriptor.ctor_kind === 'shared_worker') {
      const workerArgCheck = classifyWorkerSourceArgument(descriptor.url_expression, isBlobUrlSourceExpression)
      if (workerArgCheck.blocked) {
        pushFinding(workerArgCheck.type, workerArgCheck.expressionText || descriptor.source_trace)
      }
      return
    }

    if (descriptor.ctor_kind === 'unknown' && descriptor.ctor_confidence === 'unknown') {
      if (
        !descriptor.url_expression &&
        (descriptor.has_spread || descriptor.arg_confidence === 'unknown' || descriptor.arg_confidence === 'unsafe_spread')
      ) {
        pushFinding('RuntimeWorkerConstructorUnknownTarget', descriptor.source_trace || '')
        return
      }
      const unknownSourceCheck = classifyUnknownWorkerConstructTargetSourceStrict(
        descriptor.url_expression,
        isBlobUrlSourceExpression,
      )
      if (unknownSourceCheck.blocked) {
        pushFinding(unknownSourceCheck.type, unknownSourceCheck.expressionText || descriptor.source_trace)
      }
    }
  }

  const collectBlobUrlIdentifiers = (node) => {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
      const initializer = unwrapExpression(node.initializer)
      if (ts.isCallExpression(initializer)) {
        const blobCall = resolveBlobUrlCallDescriptor(initializer)
        if (blobCall?.createsBlobUrl && !blobCall.unresolved) {
          blobUrlIdentifierSet.add(node.name.text)
        }
      }
    }
    if (
      ts.isBinaryExpression(node) &&
      isRuntimeWriteOperator(node.operatorToken.kind) &&
      ts.isIdentifier(unwrapExpression(node.left))
    ) {
      const target = unwrapExpression(node.right)
      const leftIdentifier = unwrapExpression(node.left)
      if (ts.isIdentifier(leftIdentifier) && ts.isCallExpression(target)) {
        const blobCall = resolveBlobUrlCallDescriptor(target)
        if (blobCall?.createsBlobUrl && !blobCall.unresolved) {
          blobUrlIdentifierSet.add(leftIdentifier.text)
        }
      }
    }
    ts.forEachChild(node, collectBlobUrlIdentifiers)
  }

  const visit = (node) => {
    if (ts.isCallExpression(node)) {
      if (isImportExpressionCall(node)) {
        const importSourceArg = node.arguments[0] || null
        if (importSourceArg && isBlobUrlSourceExpression(importSourceArg)) {
          pushFinding('RuntimeDynamicImportBlobUrlSource', importSourceArg.getText(sourceFile))
          ts.forEachChild(node, visit)
          return
        }
        const importArgCheck = classifyDynamicImportSourceArgument(importSourceArg)
        if (importArgCheck.blocked) {
          pushFinding(importArgCheck.type, importArgCheck.expressionText || node.getText(sourceFile))
        }
      }
      const blobUrlCall = resolveBlobUrlCallDescriptor(node)
      if (blobUrlCall?.createsBlobUrl) {
        if (blobUrlCall.unresolved) {
          pushFinding('RuntimeBlobUrlCreateObjectURLUnresolvedArguments', node.getText(sourceFile))
        } else {
          pushFinding('RuntimeBlobUrlCreateObjectURL', node.getText(sourceFile))
        }
      } else if (blobUrlCall?.unresolvedTarget) {
        pushFinding('RuntimeBlobUrlCreateObjectURLUnresolvedTarget', node.getText(sourceFile))
      }

      const scriptSetSrcCall = resolveScriptSrcSetAttributeCall(node)
      if (scriptSetSrcCall) {
        const srcCheck = classifyScriptSrcSourceArgument(scriptSetSrcCall.valueArg, isBlobUrlSourceExpression)
        if (srcCheck.blocked) {
          pushFinding(srcCheck.type, srcCheck.expressionText || node.getText(sourceFile))
        }
      }

      const workerConstructCall = resolveRuntimeCallDescriptor(node, runtimeContext, runtimeWorkerConstructorMethodSet)
      if (workerConstructCall?.method === 'Reflect.construct') {
        const normalizedCall = normalizeRuntimeCallArguments(node, workerConstructCall)
        if (normalizedCall.unresolved) {
          pushFinding('RuntimeWorkerConstructUnresolvedArguments', node.getText(sourceFile))
          ts.forEachChild(node, visit)
          return
        }
        const descriptor = resolveConstructorInvocationDescriptorFromReflectConstructCall(node, normalizedCall)
        applyConstructorInvocationDescriptor(descriptor)
      }
    }

    if (ts.isNewExpression(node)) {
      const descriptor = resolveConstructorInvocationDescriptorFromNewExpression(node)
      applyConstructorInvocationDescriptor(descriptor)
    }

    if (ts.isBinaryExpression(node) && isRuntimeWriteOperator(node.operatorToken.kind) && isSrcAssignmentLeft(node.left)) {
      const srcCheck = classifyScriptSrcSourceArgument(node.right, isBlobUrlSourceExpression)
      if (srcCheck.blocked) {
        pushFinding(srcCheck.type, srcCheck.expressionText || node.getText(sourceFile))
      }
    }

    ts.forEachChild(node, visit)
  }

  collectBlobUrlIdentifiers(sourceFile)
  visit(sourceFile)
  return findings
}

const collectRuntimeCodegenTimerCallFindings = (sourceFile, runtimeContext) => {
  const findings = []
  const seen = new Set()

  const pushFinding = (type, expressionText) => {
    const normalized = normalizeComputedKeyExpr(expressionText || '')
    const dedupeKey = `${type}|${normalized}`
    if (seen.has(dedupeKey)) return
    seen.add(dedupeKey)
    findings.push({ type, expressionText: normalized })
  }

  const visit = (node) => {
    if (ts.isCallExpression(node)) {
      const callDescriptor = resolveRuntimeCallDescriptor(node, runtimeContext, runtimeTimerMethodSet)
      if (callDescriptor?.method && runtimeTimerMethodSet.has(callDescriptor.method)) {
        const normalizedCall = normalizeRuntimeCallArguments(node, callDescriptor)
        if (normalizedCall.unresolved) {
          pushFinding('RuntimeTimerCallUnresolvedArguments', node.getText(sourceFile))
          ts.forEachChild(node, visit)
          return
        }
        const argCheck = analyzeTimerFirstArgument(normalizedCall.args[0] || null, runtimeContext)
        if (argCheck.blocked) {
          pushFinding(argCheck.type, argCheck.expressionText || node.getText(sourceFile))
        }
      } else if (callDescriptor?.invoke === 'reflect_apply' && callDescriptor.unresolvedTarget) {
        // Timer callee may be hidden behind an unresolved Reflect.apply target.
        pushFinding('RuntimeTimerCallUnresolvedTarget', node.getText(sourceFile))
      }
    }
    ts.forEachChild(node, visit)
  }

  visit(sourceFile)
  return findings
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
      const callDescriptor = resolveRuntimeCallDescriptor(node, runtimeContext)
      if (!callDescriptor) {
        ts.forEachChild(node, visit)
        return
      }
      const normalizedCall = normalizeRuntimeCallArguments(node, callDescriptor)

      if (normalizedCall.unresolved) {
        pushFinding(
          `${callDescriptor.method || 'RuntimeMutator'}.${callDescriptor.invoke}`,
          node.getText(sourceFile),
        )
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
      const callDescriptor = resolveRuntimeCallDescriptor(node, runtimeContext)
      if (!callDescriptor) {
        ts.forEachChild(node, visit)
        return
      }
      const normalizedCall = normalizeRuntimeCallArguments(node, callDescriptor)

      if (normalizedCall.unresolved) {
        pushFinding(
          `${callDescriptor.method || 'RuntimeMutator'}.${callDescriptor.invoke}-explicit-action`,
          node.getText(sourceFile),
        )
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
  const mutatorSourceFailureSeen = new Set()
  const codegenSourceFailureSeen = new Set()
  const dynamicModuleFailureSeen = new Set()
  const pushMutatorSourceFailure = (type, expressionText) => {
    const normalized = normalizeComputedKeyExpr(expressionText || '')
    const dedupeKey = `${type}|${normalized}`
    if (mutatorSourceFailureSeen.has(dedupeKey)) return
    mutatorSourceFailureSeen.add(dedupeKey)
    failures.push(
      `style-profit forbids runtime mutator source references; use object spread and readonly literal actions（款式利润前端禁止 runtime mutator 源引用，请使用对象 spread 与只读字面量 action）: ${targetPath} -> ${type} [${normalized}]`,
    )
  }
  const pushCodegenSourceFailure = (type, expressionText) => {
    const normalized = normalizeComputedKeyExpr(expressionText || '')
    const dedupeKey = `${type}|${normalized}`
    if (codegenSourceFailureSeen.has(dedupeKey)) return
    codegenSourceFailureSeen.add(dedupeKey)
    failures.push(
      `style-profit forbids runtime code generation entry points; use static readonly helpers（款式利润前端禁止运行时代码生成入口）: ${targetPath} -> ${type} [${normalized}]`,
    )
  }
  const pushDynamicModuleFailure = (type, expressionText) => {
    const normalized = normalizeComputedKeyExpr(expressionText || '')
    const dedupeKey = `${type}|${normalized}`
    if (dynamicModuleFailureSeen.has(dedupeKey)) return
    dynamicModuleFailureSeen.add(dedupeKey)
    failures.push(
      `style-profit forbids dynamic module loading entry points; use static local import literals only（款式利润前端禁止动态模块加载入口）: ${targetPath} -> ${type} [${normalized}]`,
    )
  }

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

    for (const finding of runtimeContext.runtimeMutatorSourceFindings) {
      pushMutatorSourceFailure(finding.type, finding.expressionText)
    }
    for (const finding of runtimeContext.runtimeCodegenSourceFindings || []) {
      pushCodegenSourceFailure(finding.type, finding.expressionText)
    }

    const runtimeMutatorSourceReferences = collectRuntimeMutatorSourceReferenceFindings(sourceFile, runtimeContext)
    for (const finding of runtimeMutatorSourceReferences) {
      pushMutatorSourceFailure(finding.type, finding.expressionText)
    }
    const runtimeCodegenSourceReferences = collectRuntimeCodegenSourceReferenceFindings(sourceFile, runtimeContext)
    for (const finding of runtimeCodegenSourceReferences) {
      pushCodegenSourceFailure(finding.type, finding.expressionText)
    }
    const runtimeTimerCallFindings = collectRuntimeCodegenTimerCallFindings(sourceFile, runtimeContext)
    for (const finding of runtimeTimerCallFindings) {
      pushCodegenSourceFailure(finding.type, finding.expressionText)
    }
    const runtimeDynamicModuleFindings = collectRuntimeDynamicModuleLoadingFindings(sourceFile, runtimeContext)
    for (const finding of runtimeDynamicModuleFindings) {
      pushDynamicModuleFailure(finding.type, finding.expressionText)
    }

    const runtimeDynamicFindings = collectRuntimeDynamicInjectionFindings(sourceFile, runtimeContext)
    for (const finding of runtimeDynamicFindings) {
      failures.push(
        `style-profit forbids runtime dynamic property injection; use explicit literal keys（款式利润前端禁止运行时动态属性注入，请使用显式字面量键）: ${targetPath} -> ${finding.type} [${finding.expressionText}]`,
      )
    }

    for (const finding of runtimeContext.runtimeAliasRiskFindings) {
      failures.push(
        `style-profit forbids runtime dynamic property injection; use explicit literal keys（款式利润前端禁止运行时动态属性注入，请使用显式字面量键）: ${targetPath} -> ${finding.type} [${normalizeComputedKeyExpr(finding.expressionText || '')}]`,
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

  const moduleConfig = {
    module: 'style_profit',
    surface: {
      moduleKey: 'style_profit',
      scanScopes: ['api', 'views', 'router', 'stores', 'components', 'utils'],
      entryGlobs: ['src/**'],
      extraPaths: ['src/App.vue', 'src/main.ts'],
    },
    allowedApis: ['fetchStyleProfitSnapshots', 'fetchStyleProfitSnapshotDetail'],
    forbiddenApis: ['/api/resource', '/internal/'],
    forbiddenActions: ['create', 'update', 'delete', 'confirm', 'cancel', 'generate', 'recalculate', 'sync', 'submit'],
    allowedReadOnlyActions: ['read', 'query', 'detail', 'export'],
    allowedHttpMethods: ['GET'],
    rules: FRONTEND_WRITE_GUARD_COMMON_RULES,
    enforceHttpMethodPolicy: false,
    enforceForbiddenActions: false,
    surfaceMatcher: ({ targetPath, content: sourceContent, projectRoot: sourceRoot }) =>
      isStyleProfitSurface(targetPath, sourceContent, sourceRoot),
  }

  const configValidation = validateModuleContractConfig(moduleConfig)
  if (!configValidation.ok) {
    for (const message of configValidation.failures) {
      fail(`[FWG-CONFIG-001] ${message}`)
    }
    return { ok: false, failures, scannedFiles: 0 }
  }

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

  const engineResult = runFrontendContractEngine(projectRoot, moduleConfig)
  if (!engineResult.ok) {
    for (const message of engineResult.failures) {
      fail(message)
    }
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

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  runContractCli({
    check: checkStyleProfitContracts,
    passMessage: 'Style-profit contract check passed.',
    failTitle: 'Style-profit contract check failed:',
  })
}
