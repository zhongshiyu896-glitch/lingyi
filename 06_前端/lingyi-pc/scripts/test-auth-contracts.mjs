import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')

const read = (relativePath) => readFileSync(path.join(projectRoot, relativePath), 'utf8')

const assertIncludes = (content, expected, label) => {
  if (!content.includes(expected)) {
    throw new Error(`${label}: missing ${expected}`)
  }
}

const assertNotIncludes = (content, unexpected, label) => {
  if (content.includes(unexpected)) {
    throw new Error(`${label}: unexpected ${unexpected}`)
  }
}

const loginPage = read('src/views/auth/LoginPage.vue')
assertIncludes(loginPage, 'data-testid="m1-login-password"', 'LoginPage password field')
assertIncludes(loginPage, 'type="password"', 'LoginPage password field')
assertIncludes(loginPage, 'v-if="!isProductionLogin"', 'LoginPage dev profile gate')
assertIncludes(loginPage, "import.meta.env.MODE === 'production'", 'LoginPage production mode gate')
assertIncludes(loginPage, "errorMessage.value = isProductionLogin ? '请输入用户名和密码' : '请输入用户名'", 'LoginPage empty input fail closed')
assertIncludes(loginPage, 'payload.profile = profile.value', 'LoginPage local profile payload')

const authApi = read('src/api/auth.ts')
assertIncludes(authApi, 'password?: string', 'auth login payload')
assertIncludes(authApi, 'profile?: LocalLoginProfile', 'auth local profile payload')
assertIncludes(authApi, "request('/api/auth/login'", 'auth login endpoint')

const permissionStore = read('src/stores/permission.ts')
assertIncludes(permissionStore, 'const AUTH_ME_GUEST_CACHE_TTL_MS = 5000', 'auth guest ttl')
assertIncludes(permissionStore, 'const AUTH_ME_USER_CACHE_TTL_MS = 5000', 'auth user ttl')
assertIncludes(permissionStore, 'currentUserCacheUntil > Date.now()', 'auth positive cache')

const router = read('src/router/index.ts')
assertNotIncludes(router, 'loadCurrentUser({ force: true })', 'router auth cache')

console.log('PASS: auth login contracts')
