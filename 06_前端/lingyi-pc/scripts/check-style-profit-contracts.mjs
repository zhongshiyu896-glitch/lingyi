import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

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

const actionInteractiveKeys = ['onClick', 'handler', 'action', 'command', 'onSelect', 'onCommand', 'callback', 'execute', 'submit']
const actionInteractiveKeyAlternation = actionInteractiveKeys.map(escapeRegex).join('|')
const actionInteractiveAssignmentPattern = `(?:['"\`]\\s*)?(?:${actionInteractiveKeyAlternation})(?:\\s*['"\`])?\\s*:`
const actionInteractiveMethodPattern = `(?:\\basync\\s+)?(?:['"\`]\\s*)?(?:${actionInteractiveKeyAlternation})(?:\\s*['"\`])?\\s*\\([^)]*\\)\\s*\\{`
const actionInteractiveComputedAssignmentPattern = `\\[\\s*['"\`]\\s*(?:${actionInteractiveKeyAlternation})\\s*['"\`]\\s*\\]\\s*:`
const actionInteractiveComputedMethodPattern = `(?:\\basync\\s+)?\\[\\s*['"\`]\\s*(?:${actionInteractiveKeyAlternation})\\s*['"\`]\\s*\\]\\s*\\([^)]*\\)\\s*\\{`
const computedPropertyKeyRegex = /[,{]\s*(?:async\s+)?\[\s*([^\]]+?)\s*\]\s*(?::|\([^)]*\)\s*\{)/g
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

const isLiteralComputedKey = (computedExpr) => /^['"`][^'"`]+['"`]$/.test(normalizeComputedKeyExpr(computedExpr))

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
      let computedKeyMatch = computedPropertyKeyRegex.exec(content)
      while (computedKeyMatch) {
        const keyExpression = computedKeyMatch[1] ?? ''
        if (!isLiteralComputedKey(keyExpression)) {
          const normalizedExpression = normalizeComputedKeyExpr(keyExpression)
          fail(
            `style-profit forbids non-literal computed action keys; use explicit onClick/handler/command keys or quoted literal computed keys（款式利润前端禁止非字面量计算属性 action key）: ${targetPath} -> [${normalizedExpression}]`,
          )
          break
        }
        computedKeyMatch = computedPropertyKeyRegex.exec(content)
      }
      computedPropertyKeyRegex.lastIndex = 0

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
