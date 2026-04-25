import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000'
  const devAuthHeadersEnabled = env.VITE_LINGYI_DEV_AUTH_HEADERS === 'true'
  const devUser = (env.VITE_LINGYI_DEV_USER || '').trim()
  const devRoles = (env.VITE_LINGYI_DEV_ROLES || '').trim()

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
