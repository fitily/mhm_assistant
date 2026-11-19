import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.VITE_BACKEND_URL || 'http://localhost:8000'

  return {
    plugins: [vue()],
    resolve: {
      alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
    },
    server: {
      port: 5173,
      // En développement, /api/xxx est redirigé vers le backend FastAPI : /xxx
      // (ex. /api/v1/chat -> http://localhost:8000/v1/chat). Le préfixe /api est retiré.
      proxy: {
        '/api': {
          target: backend,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
          timeout: 300000, // le LLM local peut être lent
          proxyTimeout: 300000,
        },
      },
    },
  }
})
