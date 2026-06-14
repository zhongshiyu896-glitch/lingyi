import { mkdirSync, writeFileSync } from 'node:fs'
import http from 'node:http'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn } from 'node:child_process'
import playwright from '../../../06_前端/lingyi-pc/node_modules/playwright/index.js'

const { chromium } = playwright

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '../../..')
const backendRoot = path.join(repoRoot, '07_后端/lingyi_service')
const frontendRoot = path.join(repoRoot, '06_前端/lingyi-pc')
const outputDir = __dirname
const e2eUsername = 'erp.user@example.com'
const e2ePassword = 'secret-pass'
const sidValue = 'mock-erpnext-sid-w003a'

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

const startMockERPNext = (port) => {
  const requests = []
  const server = http.createServer((req, res) => {
    requests.push({ method: req.method, url: req.url, hasSidCookie: (req.headers.cookie || '').includes('sid=') })
    const sendJson = (status, payload, headers = {}) => {
      res.writeHead(status, { 'Content-Type': 'application/json', ...headers })
      res.end(JSON.stringify(payload))
    }

    if (req.method === 'POST' && req.url === '/api/method/login') {
      let body = ''
      req.on('data', (chunk) => {
        body += chunk
      })
      req.on('end', () => {
        const params = new URLSearchParams(body)
        if (params.get('usr') === e2eUsername && params.get('pwd') === e2ePassword) {
          sendJson(200, { message: 'Logged In' }, { 'Set-Cookie': `sid=${sidValue}; Path=/; HttpOnly; SameSite=Lax` })
          return
        }
        sendJson(401, { exc_type: 'AuthenticationError', message: 'Invalid login' })
      })
      return
    }

    if (req.method === 'GET' && req.url === '/api/method/frappe.auth.get_logged_user') {
      if ((req.headers.cookie || '').includes(`sid=${sidValue}`)) {
        sendJson(200, { message: e2eUsername })
        return
      }
      sendJson(401, { exc_type: 'AuthenticationError', message: 'Not logged in' })
      return
    }

    if (req.method === 'GET' && req.url?.startsWith('/api/resource/User/')) {
      sendJson(200, { data: { name: e2eUsername, roles: [{ role: 'System Manager' }, { role: 'BOM Editor' }] } })
      return
    }

    if (req.method === 'GET' && req.url?.startsWith('/api/resource/User%20Permission')) {
      sendJson(200, { data: [] })
      return
    }

    if (req.method === 'GET' && req.url?.startsWith('/api/method/frappe.model.workflow.get_transitions')) {
      sendJson(200, { message: [] })
      return
    }

    sendJson(404, { message: `Unhandled mock ERPNext route: ${req.method} ${req.url}` })
  })

  return new Promise((resolve) => {
    server.listen(port, '127.0.0.1', () => resolve({ server, requests }))
  })
}

const startProcess = (command, args, options) => {
  const child = spawn(command, args, {
    ...options,
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  const logs = []
  child.stdout.on('data', (chunk) => logs.push(chunk.toString()))
  child.stderr.on('data', (chunk) => logs.push(chunk.toString()))
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

const screenshot = async (page, filename) => {
  await page.screenshot({ path: path.join(outputDir, filename), fullPage: true })
}

const main = async () => {
  const mockPort = await findFreePort()
  const backendPort = await findFreePort()
  const frontendPort = await findFreePort()
  const mock = await startMockERPNext(mockPort)
  const backendUrl = `http://127.0.0.1:${backendPort}`
  const frontendUrl = `http://127.0.0.1:${frontendPort}`

  const backend = startProcess(
    './.venv/bin/python',
    ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(backendPort)],
    {
      cwd: backendRoot,
      env: {
        ...process.env,
        APP_ENV: 'production',
        LINGYI_ALLOW_DEV_AUTH: 'false',
        LINGYI_PERMISSION_SOURCE: 'erpnext',
        LINGYI_ERPNEXT_BASE_URL: `http://127.0.0.1:${mockPort}`,
        LINGYI_DB_URL: `sqlite:///${path.join(outputDir, 'e2e_auth.sqlite3')}`,
      },
    },
  )

  const frontend = startProcess('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(frontendPort), '--mode', 'production'], {
    cwd: frontendRoot,
    env: {
      ...process.env,
      VITE_API_PROXY_TARGET: backendUrl,
      VITE_LINGYI_DEV_AUTH_HEADERS: 'false',
    },
  })

  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } })
  const page = await context.newPage()
  const network = []
  page.on('request', (request) => {
    network.push({ type: 'request', method: request.method(), url: request.url() })
  })
  page.on('response', (response) => {
    network.push({ type: 'response', status: response.status(), url: response.url() })
  })

  try {
    await waitForUrl(`${backendUrl}/api/auth/me`, 'backend')
    await waitForUrl(frontendUrl, 'frontend')

    await page.goto(`${frontendUrl}/bom/list`, { waitUntil: 'networkidle' })
    await page.waitForURL(/\/login\?redirect=/)
    await page.waitForSelector('[data-testid="m1-login-password"]')
    if (await page.locator('[data-testid="m1-login-profile"]').count()) {
      throw new Error('production login page must not show dev role profile selector')
    }
    await screenshot(page, '01_unauth_redirect_to_login.png')

    await page.locator('[data-testid="m1-login-username"]').fill(e2eUsername)
    await page.locator('[data-testid="m1-login-password"]').fill('bad-pass')
    await page.locator('[data-testid="m1-login-submit"]').click()
    await page.waitForSelector('[data-testid="m1-login-error"]')
    await screenshot(page, '02_login_error_fail_closed.png')

    await page.locator('[data-testid="m1-login-password"]').fill(e2ePassword)
    await page.locator('[data-testid="m1-login-submit"]').click()
    await page.waitForURL(/\/bom\/list/)
    await page.waitForSelector('[data-testid="global-auth-logout"]')
    await screenshot(page, '03_login_redirect_success.png')

    await page.locator('[data-testid="global-auth-logout"]').click()
    await page.waitForURL(/\/login/)
    await screenshot(page, '04_logout_returns_to_login.png')

    await page.locator('[data-testid="m1-login-username"]').fill(e2eUsername)
    await page.locator('[data-testid="m1-login-password"]').fill(e2ePassword)
    await page.locator('[data-testid="m1-login-submit"]').click()
    await page.waitForURL(/\/home|\/bom\/list/)
    await context.clearCookies()
    await page.goto(`${frontendUrl}/warehouse`, { waitUntil: 'networkidle' })
    await page.waitForURL(/\/login\?redirect=/)
    await screenshot(page, '05_session_expired_redirect.png')
  } finally {
    await browser.close()
    await stopProcess(frontend)
    await stopProcess(backend)
    mock.server.close()
    writeFileSync(
      path.join(outputDir, 'e2e_summary.json'),
      JSON.stringify(
        {
          backendUrl,
          frontendUrl,
          mockERPNextUrl: `http://127.0.0.1:${mockPort}`,
          screenshots: [
            '01_unauth_redirect_to_login.png',
            '02_login_error_fail_closed.png',
            '03_login_redirect_success.png',
            '04_logout_returns_to_login.png',
            '05_session_expired_redirect.png',
          ],
          network,
          mockERPNextRequests: mock.requests,
          backendLogs: backend.logs.slice(-80),
          frontendLogs: frontend.logs.slice(-80),
        },
        null,
        2,
      ),
      'utf8',
    )
  }
}

main().catch((error) => {
  writeFileSync(path.join(outputDir, 'e2e_error.txt'), String(error?.stack || error), 'utf8')
  process.exit(1)
})
