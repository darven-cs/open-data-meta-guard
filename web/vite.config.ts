import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
// 配置别名
import { fileURLToPath, URL } from "node:url"

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {                                    // 匹配 /api 开头的请求
        target: 'http://localhost:8001',           // 转发到后端 (uvicorn 8001)
        changeOrigin: true,                        // 改 Host header
        rewrite: (path) => {
          // /api/charts/* 不剥 /api 前缀（后端 mount 在 /api/charts）
          if (path.startsWith('/api/charts')) return path
          return path.replace(/^\/api/, '')
        },
      },
    },
  },
})
