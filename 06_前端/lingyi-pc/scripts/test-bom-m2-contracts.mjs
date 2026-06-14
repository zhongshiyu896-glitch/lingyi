import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const scriptDir = path.dirname(__filename)
const root = path.resolve(scriptDir, '..')

const read = (relativePath) => readFileSync(path.join(root, relativePath), 'utf8')

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message)
  }
}

const walkFiles = (directory, files = []) => {
  for (const entry of readdirSync(directory)) {
    const fullPath = path.join(directory, entry)
    const stats = statSync(fullPath)
    if (stats.isDirectory()) {
      walkFiles(fullPath, files)
      continue
    }
    files.push(fullPath)
  }
  return files
}

const assertContains = (source, needle, label) => {
  assert(source.includes(needle), `${label} 缺少 ${needle}`)
}

const assertNotContains = (source, needle, label) => {
  assert(!source.includes(needle), `${label} 不应包含 ${needle}`)
}

const bomApi = read('src/api/bom.ts')
const productionApi = read('src/api/production.ts')
const appShell = read('src/App.vue')
const bomList = read('src/views/bom/BomList.vue')
const bomDetail = read('src/views/bom/BomDetail.vue')
const bomListTemplate = bomList.split('<script setup')[0]
const bomDetailTemplate = bomDetail.split('<script setup')[0]
const bomViews = walkFiles(path.join(root, 'src/views/bom')).filter((file) => file.endsWith('.vue') || file.endsWith('.ts'))

for (const filePath of bomViews) {
  const source = readFileSync(filePath, 'utf8')
  const label = path.relative(root, filePath)
  assertNotContains(source, '/api/local-dev/bom', label)
  assertNotContains(source, 'createLocalBom', label)
  assertNotContains(source, 'updateLocalBom', label)
  assertNotContains(source, 'fetchLocalBomReadback', label)
  assertNotContains(source, 'rollbackLocalBomScenario', label)
}

assertNotContains(bomApi, 'LOCAL_BOM_', 'src/api/bom.ts')
assertNotContains(bomApi, 'LocalBomReadbackData', 'src/api/bom.ts')
assertNotContains(bomApi, 'createLocalBom', 'src/api/bom.ts')
assertNotContains(bomApi, 'updateLocalBom', 'src/api/bom.ts')
assertNotContains(bomApi, 'rollbackLocalBomScenario', 'src/api/bom.ts')
assertNotContains(productionApi, 'fetchLocalReadbackSalesOrders', 'src/api/production.ts')
assertNotContains(productionApi, 'fetchLocalReadbackProductionPlans', 'src/api/production.ts')

assertContains(bomList, 'createBom', 'BomList.vue')
assertContains(bomList, 'updateBomDraft', 'BomList.vue')
assertContains(bomApi, "request('/api/bom/'", 'createBom endpoint')
assertContains(bomApi, 'request(`/api/bom/${bomId}`', 'update/detail endpoint')
assertContains(bomDetail, 'setDefaultBom', 'BomDetail.vue')
assertContains(bomDetail, 'activateBom', 'BomDetail.vue')
assertContains(bomDetail, 'deactivateBom', 'BomDetail.vue')
assertContains(bomDetail, 'explodeBom', 'BomDetail.vue')
assertContains(bomDetail, "loadBomActions(bomId", 'BomDetail.vue button permission source')
assertContains(bomDetail, 'buttonPermissions.value.set_default', 'BomDetail.vue set default permission')
assertContains(bomDetail, 'buttonPermissions.value.publish', 'BomDetail.vue activate permission')
assertContains(bomDetail, 'buttonPermissions.value.deactivate', 'BomDetail.vue deactivate permission')

assertContains(appShell, 'VITE_LINGYI_READONLY_DIAGNOSTICS', 'App.vue readonly diagnostics env gate')
assertContains(
  appShell,
  "import.meta.env.DEV && import.meta.env.VITE_LINGYI_READONLY_DIAGNOSTICS === 'true'",
  'App.vue readonly diagnostics default-off gate',
)
assertContains(appShell, 'v-if="showReadonlyDiagnostics"', 'App.vue readonly diagnostics render gate')
assertContains(appShell, 'data-testid="m2-yisuan-app-shell"', 'App.vue BOM 1:1 business shell')
assertContains(appShell, 'data-testid="m2-yisuan-left-menu"', 'App.vue BOM 1:1 left menu')
assertContains(appShell, '基础资料', 'App.vue left menu')
assertContains(appShell, '款式设计', 'App.vue left menu')
assertContains(appShell, '物料开发', 'App.vue left menu')
assertContains(appShell, 'm2-yisuan-business-main', 'App.vue BOM business content')
assertNotContains(bomList, 'BomAlternateMaterialReadonlySection', 'BomList.vue mounted readonly section')
assertNotContains(bomList, 'useBomAlternateReadonly', 'BomList.vue readonly composable')
assertNotContains(bomList, 'useBomExceptionBaselineReadonly', 'BomList.vue readonly composable')
assertNotContains(bomList, 'useBomAuditDefaultVersionReadonly', 'BomList.vue readonly composable')
assertNotContains(bomDetail, 'BomAlternateMaterialReadonlySection', 'BomDetail.vue mounted readonly section')
assertNotContains(bomDetail, 'useBomAlternateReadonly', 'BomDetail.vue readonly composable')
assertNotContains(bomDetail, 'useBomExceptionBaselineReadonly', 'BomDetail.vue readonly composable')
assertNotContains(bomDetail, 'useBomAuditDefaultVersionReadonly', 'BomDetail.vue readonly composable')

assertContains(bomListTemplate, '物料开发', 'Yisuan list crumb')
assertContains(bomListTemplate, '请输入名称/供应商/编号', 'Yisuan list search placeholder')
assertContains(bomListTemplate, '批量删除', 'Yisuan list toolbar')
assertContains(bomListTemplate, '导入图片', 'Yisuan list toolbar')
assertContains(bomListTemplate, '列设置', 'Yisuan list toolbar')
assertContains(bomListTemplate, '图片', 'Yisuan list table header')
assertContains(bomListTemplate, '幅宽', 'Yisuan list table header')
assertContains(bomListTemplate, '克重', 'Yisuan list table header')
assertContains(bomListTemplate, '30条/页', 'Yisuan pagination')
assertContains(bomList, '#4e88f3', 'Yisuan primary color')
assertContains(bomList, '#f6f8f9', 'Yisuan page background')
assertContains(bomList, '#f5f7fa', 'Yisuan table header')
assertContains(bomList, 'm2_state', 'M2 state capture probe')
assertContains(bomDetail, 'm2_state', 'M2 detail state capture probe')

assertNotContains(bomListTemplate, 'scenario_tag', 'BomList template')
assertNotContains(bomDetailTemplate, 'scenario_tag', 'BomDetail template')
assertNotContains(bomListTemplate, '回读', 'BomList template')
assertNotContains(bomDetailTemplate, '回读', 'BomDetail template')
assertNotContains(bomListTemplate, '回滚', 'BomList template')
assertNotContains(bomDetailTemplate, '回滚', 'BomDetail template')

const baselinePath = path.join(
  root,
  '../../01_需求与资料/衣算云文档/证据数据/yisuan_ui_1to1_shots_20260405/04_物料开发_面料.png',
)
assert(existsSync(baselinePath), `缺少衣算云 1:1 基准截图: ${baselinePath}`)

console.log('BOM M2 contracts passed')
