import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
  const explicitDevAuthFlag = (env.VITE_LINGYI_DEV_AUTH_HEADERS || '').trim().toLowerCase()
  const isLocalProxyTarget = (() => {
    try {
      const parsed = new URL(apiProxyTarget)
      return parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost'
    } catch {
      return false
    }
  })()
  const devAuthHeadersEnabled = explicitDevAuthFlag
    ? explicitDevAuthFlag === 'true'
    : (mode === 'development' && isLocalProxyTarget)
  const devUser = (env.VITE_LINGYI_DEV_USER || (devAuthHeadersEnabled ? 'local.dev' : '')).trim()
  const devRoles = (env.VITE_LINGYI_DEV_ROLES || (devAuthHeadersEnabled ? 'System Manager' : '')).trim()

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on('proxyReq', (proxyReq) => {
              if (!devAuthHeadersEnabled) {
                return
              }
              if (devUser) {
                proxyReq.setHeader('X-LY-Dev-User', devUser)
              }
              if (devRoles) {
                proxyReq.setHeader('X-LY-Dev-Roles', devRoles)
              }
            })
          },
        },
      },
    },
  }
})
