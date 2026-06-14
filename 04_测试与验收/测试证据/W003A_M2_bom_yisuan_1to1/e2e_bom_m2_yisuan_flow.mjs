import { mkdirSync, writeFileSync } from 'node:fs'
import net from 'node:net'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import playwright from '../../../06_前端/lingyi-pc/node_modules/playwright/index.js'

const { chromium } = playwright

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '../../..')
const frontendRoot = path.join(repoRoot, '06_前端/lingyi-pc')
const outputDir = __dirname
const baselineScreenshot = path.join(
  repoRoot,
  '01_需求与资料/衣算云文档/证据数据/yisuan_ui_1to1_shots_20260405/04_物料开发_面料.png',
)

const viewport = { width: 1440, height: 900 }
const userData = {
  username: 'm2.bom.editor@example.com',
  roles: ['System Manager', 'BOM Editor'],
  is_service_account: false,
  source: 'erpnext',
}
const fullButtonPermissions = {
  create: true,
  update: true,
  publish: true,
  deactivate: true,
  set_default: true,
  read: true,
}
const localDevPattern = /\/api\/local-dev\/bom/i

mkdirSync(outputDir, { recursive: true })

const findFreePort = () =>
  new Promise((resolve, reject) => {
    const server = net.createServer()
    server.unref()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const address = server.address()
      server.close(() => resolve(address.port))
    })
  })

const waitForUrl = async (url, label) => {
  const started = Date.now()
  let lastError = null
  while (Date.now() - started < 30000) {
    try {
      const response = await fetch(url)
      if (response.status < 500) return
    } catch (error) {
      lastError = error
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`Timed out waiting for ${label}: ${url}; lastError=${lastError?.message || 'none'}`)
}

const startProcess = (command, args, options) => {
  const child = spawn(command, args, {
    ...options,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  const logs = []
  child.stdout.on('data', (chunk) => logs.push(chunk.toString()))
  child.stderr.on('data', (chunk) => logs.push(chunk.toString()))
  child.on('error', (error) => logs.push(`[spawn-error] ${error.message}`))
  child.on('exit', (code, signal) => {
    if (code !== 0 && signal !== 'SIGTERM') {
      logs.push(`[exit] code=${code} signal=${signal}`)
    }
  })
  return { child, logs }
}

const stopProcess = async (processHandle) => {
  if (!processHandle || processHandle.child.killed) return
  processHandle.child.kill('SIGTERM')
  await new Promise((resolve) => setTimeout(resolve, 500))
}

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message)
  }
}

const ok = (data, message = 'ok') => ({
  code: '0',
  message,
  data,
})

const jsonResponse = async (route, payload, status = 200) => {
  await route.fulfill({
    status,
    contentType: 'application/json',
    body: JSON.stringify(payload),
  })
}

const parseJsonBody = (request) => {
  const raw = request.postData() || '{}'
  return JSON.parse(raw)
}

const validateWriteCarrier = (payload, label) => {
  assert(/^Z002-BOM-\d{8}-001$/.test(payload.scenario_tag), `${label} 缺少受控 scenario_tag 载体`)
  assert(String(payload.idempotency_key || '').includes(payload.scenario_tag), `${label} idempotency_key 未绑定 scenario_tag`)
  assert(String(payload.source_ref || '').includes(payload.scenario_tag) || String(payload.bom_no || '').includes('BOM-'), `${label} source_ref 不合规`)
}

const materialRemark = (item, fallbackName = '雪纺里布') =>
  ['面料', fallbackName, `克重:${item.weight || 230}`].filter(Boolean).join(' / ')

const createFixtureStore = () => {
  let nextId = 104
  const records = new Map()

  const setRecord = (record) => {
    records.set(record.id, record)
  }

  setRecord({
    id: 101,
    bom_no: 'BOM-20260320001',
    item_code: '20260320001',
    version_no: 'V1',
    is_default: false,
    status: 'draft',
    effective_date: null,
    items: [
      {
        id: 1001,
        material_item_code: '20260320001',
        color: '',
        size: '',
        qty_per_piece: '150',
        loss_rate: '0',
        uom: '米',
        remark: '面料 / 雪纺里布 / 克重:230',
      },
    ],
    operations: [],
  })
  setRecord({
    id: 102,
    bom_no: 'BOM-20260316001',
    item_code: '20260316001',
    version_no: 'V1',
    is_default: false,
    status: 'draft',
    effective_date: null,
    items: [
      {
        id: 1002,
        material_item_code: '20260316001',
        color: '',
        size: '',
        qty_per_piece: '150',
        loss_rate: '0',
        uom: '米',
        remark: '面料 / 针织布 / 克重:230',
      },
    ],
    operations: [],
  })
  setRecord({
    id: 103,
    bom_no: 'BOM-20260316002',
    item_code: '20260316002',
    version_no: 'V1',
    is_default: false,
    status: 'draft',
    effective_date: null,
    items: [
      {
        id: 1003,
        material_item_code: '20260316002',
        color: '黑色',
        size: '',
        qty_per_piece: '150',
        loss_rate: '0',
        uom: '米',
        remark: '面料 / 化纤 / 克重:0',
      },
    ],
    operations: [],
  })

  const list = () => Array.from(records.values()).map((record) => ({
    id: record.id,
    bom_no: record.bom_no,
    item_code: record.item_code,
    version_no: record.version_no,
    is_default: record.is_default,
    status: record.status,
    effective_date: record.effective_date,
  }))

  const detail = (id) => {
    const record = records.get(id)
    assert(record, `BOM fixture not found: ${id}`)
    return {
      bom: {
        id: record.id,
        bom_no: record.bom_no,
        item_code: record.item_code,
        version_no: record.version_no,
        is_default: record.is_default,
        status: record.status,
        effective_date: record.effective_date,
      },
      items: record.items,
      operations: record.operations,
    }
  }

  return {
    list,
    detail,
    create(payload) {
      validateWriteCarrier(payload, 'createBom')
      const id = nextId
      nextId += 1
      const primary = payload.bom_items[0]
      const bomNo = `${payload.scenario_tag}-BOM-${id}`
      const record = {
        id,
        bom_no: bomNo,
        item_code: payload.item_code,
        version_no: payload.version_no,
        is_default: false,
        status: 'draft',
        effective_date: null,
        items: [
          {
            id: id * 10,
            material_item_code: primary.material_item_code,
            color: primary.color || '',
            size: primary.size || '',
            qty_per_piece: String(primary.qty_per_piece),
            loss_rate: String(primary.loss_rate),
            uom: primary.uom,
            remark: primary.remark || materialRemark(primary),
          },
        ],
        operations: payload.operations || [],
      }
      setRecord(record)
      return { id, bomNo }
    },
    update(id, payload) {
      validateWriteCarrier(payload, 'updateBomDraft')
      const record = records.get(id)
      assert(record, `BOM update fixture not found: ${id}`)
      const primary = payload.bom_items[0]
      record.version_no = payload.version_no
      record.items = [
        {
          id: id * 10 + 1,
          material_item_code: primary.material_item_code,
          color: primary.color || '',
          size: primary.size || '',
          qty_per_piece: String(primary.qty_per_piece),
          loss_rate: String(primary.loss_rate),
          uom: primary.uom,
          remark: primary.remark || materialRemark(primary),
        },
      ]
      record.operations = payload.operations || []
      return record
    },
    setDefault(id, payload) {
      validateWriteCarrier(payload, 'setDefaultBom')
      for (const record of records.values()) {
        record.is_default = record.id === id
      }
      return records.get(id)
    },
    activate(id, payload) {
      validateWriteCarrier(payload, 'activateBom')
      const record = records.get(id)
      assert(record, `BOM activate fixture not found: ${id}`)
      record.status = 'active'
      record.effective_date = new Date().toISOString()
      return record
    },
    deactivate(id, payload) {
      validateWriteCarrier(payload, 'deactivateBom')
      assert(String(payload.reason || '').includes(payload.scenario_tag), 'deactivateBom reason 未绑定 scenario_tag')
      const record = records.get(id)
      assert(record, `BOM deactivate fixture not found: ${id}`)
      record.status = 'inactive'
      return record
    },
  }
}

const installApiMocks = async (context, store, apiCalls, localDevHits) => {
  await context.route('**/api/**', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    const pathname = url.pathname
    const method = request.method()
    if (!pathname.startsWith('/api/')) {
      await route.continue()
      return
    }
    apiCalls.push({ method, path: `${pathname}${url.search}` })

    if (localDevPattern.test(pathname)) {
      localDevHits.push(`${method} ${pathname}`)
      await jsonResponse(route, { code: 'LOCAL_DEV_FORBIDDEN', message: 'local-dev BOM endpoint is forbidden', data: null }, 500)
      return
    }

    if (method === 'GET' && pathname === '/api/auth/me') {
      await jsonResponse(route, ok(userData))
      return
    }

    if (method === 'GET' && pathname === '/api/auth/actions') {
      await jsonResponse(
        route,
        ok({
          username: userData.username,
          module: url.searchParams.get('module') || 'bom',
          actions: ['bom:create', 'bom:update', 'bom:publish', 'bom:set_default', 'bom:deactivate', 'bom:read'],
          status: 'authenticated',
          button_permissions: fullButtonPermissions,
        }),
      )
      return
    }

    if (method === 'GET' && /^\/api\/auth\/actions\/bom\/\d+$/.test(pathname)) {
      await jsonResponse(
        route,
        ok({
          username: userData.username,
          module: 'bom',
          actions: ['bom:create', 'bom:update', 'bom:publish', 'bom:set_default', 'bom:deactivate', 'bom:read'],
          status: 'authenticated',
          button_permissions: fullButtonPermissions,
        }),
      )
      return
    }

    if (method === 'GET' && pathname === '/api/bom/') {
      await jsonResponse(
        route,
        ok({
          items: store.list(),
          total: store.list().length,
          page: Number(url.searchParams.get('page') || '1'),
          page_size: Number(url.searchParams.get('page_size') || '30'),
        }),
      )
      return
    }

    if (method === 'POST' && pathname === '/api/bom/') {
      assert(request.headers()['x-request-id'], 'createBom 缺少 X-Request-ID')
      const payload = parseJsonBody(request)
      const created = store.create(payload)
      await jsonResponse(route, ok({ name: created.bomNo }, 'created'))
      return
    }

    const detailMatch = pathname.match(/^\/api\/bom\/(\d+)$/)
    if (detailMatch && method === 'GET') {
      await jsonResponse(route, ok(store.detail(Number(detailMatch[1]))))
      return
    }

    if (detailMatch && method === 'PUT') {
      assert(request.headers()['x-request-id'], 'updateBomDraft 缺少 X-Request-ID')
      const id = Number(detailMatch[1])
      const record = store.update(id, parseJsonBody(request))
      await jsonResponse(route, ok({ name: record.bom_no, status: record.status, updated_at: new Date().toISOString() }))
      return
    }

    const actionMatch = pathname.match(/^\/api\/bom\/(\d+)\/(set-default|activate|deactivate|explode)$/)
    if (actionMatch && method === 'POST') {
      assert(request.headers()['x-request-id'], `${actionMatch[2]} 缺少 X-Request-ID`)
      const id = Number(actionMatch[1])
      const action = actionMatch[2]
      const payload = parseJsonBody(request)
      if (action === 'set-default') {
        const record = store.setDefault(id, payload)
        await jsonResponse(route, ok({ name: record.bom_no, item_code: record.item_code, is_default: record.is_default }))
        return
      }
      if (action === 'activate') {
        const record = store.activate(id, payload)
        await jsonResponse(route, ok({ name: record.bom_no, status: record.status, effective_date: record.effective_date }))
        return
      }
      if (action === 'deactivate') {
        const record = store.deactivate(id, payload)
        await jsonResponse(route, ok({ name: record.bom_no, status: record.status }))
        return
      }
      if (action === 'explode') {
        validateWriteCarrier(payload, 'explodeBom')
        await jsonResponse(
          route,
          ok({
            material_requirements: [
              {
                material_item_code: store.detail(id).items[0].material_item_code,
                color: store.detail(id).items[0].color,
                size: store.detail(id).items[0].size,
                uom: '米',
                qty: '1500.00',
              },
            ],
            operation_costs: [],
            total_material_qty: '1500.00',
            total_operation_cost: '0.00',
          }),
        )
        return
      }
    }

    await jsonResponse(route, { code: 'NOT_FOUND', message: `Unhandled ${method} ${pathname}`, data: null }, 404)
  })
}

const screenshot = async (page, filename) => {
  await page.screenshot({ path: path.join(outputDir, filename), fullPage: true })
}

const waitForSelector = async (page, selector, label) => {
  await page.waitForSelector(selector, { state: 'visible', timeout: 12000 }).catch((error) => {
    throw new Error(`Timed out waiting for ${label}: ${selector}; ${error.message}`)
  })
}

const countCalls = (apiCalls, method, pathMatcher) =>
  apiCalls.filter((call) => call.method === method && pathMatcher(call.path)).length

const collectStyleChecks = async (page) =>
  page.evaluate(() => {
    const readBox = (selector) => {
      const element = document.querySelector(selector)
      if (!element) return null
      const rect = element.getBoundingClientRect()
      return { width: Math.round(rect.width), height: Math.round(rect.height), top: Math.round(rect.top) }
    }
    const readStyle = (selector, prop) => {
      const element = document.querySelector(selector)
      if (!element) return ''
      return window.getComputedStyle(element).getPropertyValue(prop)
    }
    return {
      pageBg: readStyle('[data-testid="yisuan-1to1-bom-list-shell"]', 'background-color'),
      primaryBg: readStyle('[data-testid="m2-bom-new-button"]', 'background-color'),
      tableHeadBg: readStyle('.ys-bom-table th', 'background-color'),
      bodyColor: readStyle('.ys-bom-table td', 'color'),
      topbarBox: readBox('[data-testid="m2-bom-yisuan-topbar"]'),
      tabsBox: readBox('.ys-bom-tabs'),
      toolbarBox: readBox('[data-testid="yisuan-1to1-bom-list-toolbar"]'),
      headers: Array.from(document.querySelectorAll('.ys-bom-table th'))
        .map((node) => node.textContent?.trim() || '')
        .filter(Boolean),
      toolbarText: document.querySelector('[data-testid="yisuan-1to1-bom-list-toolbar"]')?.textContent || '',
      paginationText: document.querySelector('[data-testid="m2-bom-pagination"]')?.textContent || '',
    }
  })

const assertYisuanStyleChecks = (checks) => {
  assert(checks.pageBg === 'rgb(246, 248, 249)', `页面背景不符合 1:1 基准: ${checks.pageBg}`)
  assert(checks.primaryBg === 'rgb(78, 136, 243)', `主按钮色不符合 1:1 基准: ${checks.primaryBg}`)
  assert(checks.tableHeadBg === 'rgb(245, 247, 250)', `表头背景不符合 1:1 基准: ${checks.tableHeadBg}`)
  assert(checks.bodyColor === 'rgb(81, 90, 110)', `表格正文色不符合 1:1 基准: ${checks.bodyColor}`)
  assert(Math.abs((checks.topbarBox?.height || 0) - 60) <= 1, `顶部栏高度不是 60px: ${checks.topbarBox?.height}`)
  assert(Math.abs((checks.tabsBox?.height || 0) - 50) <= 1, `页签栏高度不是 50px: ${checks.tabsBox?.height}`)
  for (const header of ['图片', '编号', '部位', '名称', '颜色', '成分', '幅宽', '克重', '操作']) {
    assert(checks.headers.includes(header), `表格列缺失: ${header}`)
  }
  for (const actionText of ['新建', '筛选', '批量删除', '导入图片', '导入', '导出', '导入物料计价', '列设置']) {
    assert(checks.toolbarText.includes(actionText), `工具栏缺失: ${actionText}`)
  }
  assert(checks.paginationText.includes('30条/页'), '分页缺少 30条/页')
}

const main = async () => {
  const frontendPort = await findFreePort()
  const frontendUrl = `http://127.0.0.1:${frontendPort}`
  const viteBin = path.join(frontendRoot, 'node_modules/vite/bin/vite.js')
  const frontend = startProcess(process.execPath, [viteBin, '--host', '127.0.0.1', '--port', String(frontendPort)], {
    cwd: frontendRoot,
    env: {
      ...process.env,
      VITE_LINGYI_DEV_AUTH_HEADERS: 'false',
    },
  })

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 })
  const page = await context.newPage()
  const apiCalls = []
  const localDevHits = []
  const pageErrors = []
  const consoleErrors = []
  const screenshots = []
  const store = createFixtureStore()

  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text())
    }
  })

  await installApiMocks(context, store, apiCalls, localDevHits)

  try {
    await waitForUrl(frontendUrl, 'frontend')

    await page.goto(`${frontendUrl}/bom/list`, { waitUntil: 'networkidle' })
    await waitForSelector(page, '[data-testid="yisuan-1to1-bom-table"]', 'BOM list table')
    const styleChecks = await collectStyleChecks(page)
    assertYisuanStyleChecks(styleChecks)
    await screenshot(page, '01_list_yisuan_1to1_baseline.png')
    screenshots.push('01_list_yisuan_1to1_baseline.png')

    await page.locator('[data-testid="m2-bom-new-button"]').click()
    await waitForSelector(page, '[data-testid="m2-bom-record-dialog"]', 'BOM create dialog')
    await page.locator('[data-testid="m2-bom-form-item-code"]').fill('Z002-BOM-20260614-001')
    await page.locator('[data-testid="m2-bom-form-material-code"]').fill('FAB-Z002-001')
    await page.locator('[data-testid="m2-bom-form-material-name"]').fill('雪纺里布')
    await screenshot(page, '02_create_dialog_yisuan_build.png')
    screenshots.push('02_create_dialog_yisuan_build.png')
    await page.locator('[data-testid="m2-bom-save-button"]').click()
    await page.locator('[data-testid="m2-bom-record-dialog"]').waitFor({ state: 'hidden', timeout: 12000 })
    assert(countCalls(apiCalls, 'POST', (item) => item === '/api/bom/') === 1, 'createBom 未命中 POST /api/bom/')
    await waitForSelector(page, 'text=Z002-BOM-20260614-001', 'created BOM row')
    await screenshot(page, '03_after_create_list_true_endpoint.png')
    screenshots.push('03_after_create_list_true_endpoint.png')

    await page.locator('button.ys-link', { hasText: 'Z002-BOM-20260614-001' }).first().click()
    await page.waitForURL(/\/bom\/detail/)
    await waitForSelector(page, '[data-testid="yisuan-1to1-bom-detail-table"]', 'BOM detail table')
    await screenshot(page, '04_detail_yisuan_lifecycle_toolbar.png')
    screenshots.push('04_detail_yisuan_lifecycle_toolbar.png')

    await page.locator('[data-testid="m2-bom-detail-edit-button"]').click()
    await waitForSelector(page, '[data-testid="m2-bom-detail-edit-dialog"]', 'BOM edit dialog')
    await screenshot(page, '05_edit_dialog_yisuan_build.png')
    screenshots.push('05_edit_dialog_yisuan_build.png')
    await page.locator('[data-testid="m2-bom-detail-save-button"]').click()
    await page.locator('[data-testid="m2-bom-detail-edit-dialog"]').waitFor({ state: 'hidden', timeout: 12000 })
    assert(countCalls(apiCalls, 'PUT', (item) => /^\/api\/bom\/\d+$/.test(item)) === 1, 'updateBomDraft 未命中 PUT /api/bom/{id}')
    await screenshot(page, '06_after_edit_detail_true_endpoint.png')
    screenshots.push('06_after_edit_detail_true_endpoint.png')

    await page.locator('[data-testid="m2-bom-set-default-button"]').click()
    await page.waitForTimeout(300)
    await page.locator('[data-testid="m2-bom-activate-button"]').click()
    await page.waitForTimeout(300)
    await page.locator('[data-testid="m2-bom-deactivate-button"]').click()
    await page.waitForTimeout(300)
    assert(countCalls(apiCalls, 'POST', (item) => /\/set-default$/.test(item)) === 1, 'setDefaultBom 未命中 POST /api/bom/{id}/set-default')
    assert(countCalls(apiCalls, 'POST', (item) => /\/activate$/.test(item)) === 1, 'activateBom 未命中 POST /api/bom/{id}/activate')
    assert(countCalls(apiCalls, 'POST', (item) => /\/deactivate$/.test(item)) === 1, 'deactivateBom 未命中 POST /api/bom/{id}/deactivate')
    await screenshot(page, '07_after_default_activate_deactivate.png')
    screenshots.push('07_after_default_activate_deactivate.png')

    await page.locator('[data-testid="m2-bom-explode-button"]').click()
    await waitForSelector(page, '[data-testid="m2-bom-explode-result"]', 'BOM explode result')
    assert(countCalls(apiCalls, 'POST', (item) => /\/explode$/.test(item)) === 1, 'explodeBom 未命中 POST /api/bom/{id}/explode')
    await screenshot(page, '08_explode_result_true_endpoint.png')
    screenshots.push('08_explode_result_true_endpoint.png')

    const stateRoutes = [
      ['loading', '09_state_loading.png'],
      ['error', '10_state_error.png'],
      ['disabled', '11_state_disabled.png'],
      ['empty', '12_state_empty.png'],
      ['no_permission', '13_state_no_permission.png'],
    ]
    for (const [stateName, filename] of stateRoutes) {
      await page.goto(`${frontendUrl}/bom/list?m2_state=${stateName}`, { waitUntil: 'networkidle' })
      await waitForSelector(page, '[data-testid="yisuan-1to1-bom-table"]', `BOM state ${stateName}`)
      await screenshot(page, filename)
      screenshots.push(filename)
    }

    assert(localDevHits.length === 0, `BOM local-dev endpoint was called: ${localDevHits.join(', ')}`)
    assert(pageErrors.length === 0, `页面错误: ${pageErrors.join('\n')}`)
    assert(consoleErrors.length === 0, `控制台错误: ${consoleErrors.join('\n')}`)

    const summary = {
      task_id: 'W003A_M2_BOM_YISUAN_1TO1',
      generated_at: new Date().toISOString(),
      frontend_url: frontendUrl,
      baseline_screenshot: baselineScreenshot,
      viewport,
      screenshots,
      style_checks: styleChecks,
      endpoint_assertions: {
        create_bom_post: countCalls(apiCalls, 'POST', (item) => item === '/api/bom/'),
        update_bom_put: countCalls(apiCalls, 'PUT', (item) => /^\/api\/bom\/\d+$/.test(item)),
        set_default_post: countCalls(apiCalls, 'POST', (item) => /\/set-default$/.test(item)),
        activate_post: countCalls(apiCalls, 'POST', (item) => /\/activate$/.test(item)),
        deactivate_post: countCalls(apiCalls, 'POST', (item) => /\/deactivate$/.test(item)),
        explode_post: countCalls(apiCalls, 'POST', (item) => /\/explode$/.test(item)),
        local_dev_bom_calls: localDevHits.length,
      },
      api_calls: apiCalls,
      page_errors: pageErrors,
      console_errors: consoleErrors,
      frontend_logs: frontend.logs.slice(-80),
    }
    writeFileSync(path.join(outputDir, 'e2e_bom_m2_yisuan_flow_summary.json'), JSON.stringify(summary, null, 2), 'utf8')
    console.log(JSON.stringify(summary.endpoint_assertions, null, 2))
  } catch (error) {
    await page.screenshot({ path: path.join(outputDir, 'zz_error_state.png'), fullPage: true }).catch(() => {})
    await writeFileSync(path.join(outputDir, 'zz_error_state.html'), await page.content().catch(() => ''), 'utf8')
    writeFileSync(
      path.join(outputDir, 'zz_error_diagnostics.json'),
      JSON.stringify(
        {
          url: page.url(),
          api_calls: apiCalls,
          local_dev_hits: localDevHits,
          page_errors: pageErrors,
          console_errors: consoleErrors,
          frontend_logs: frontend.logs.slice(-120),
          error: String(error?.stack || error),
        },
        null,
        2,
      ),
      'utf8',
    )
    throw error
  } finally {
    await browser.close().catch(() => {})
    await stopProcess(frontend)
  }
}

main().catch((error) => {
  writeFileSync(path.join(outputDir, 'e2e_bom_m2_yisuan_flow_error.txt'), String(error?.stack || error), 'utf8')
  process.exit(1)
})
