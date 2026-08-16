import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  // 相对路径，保证打包产物由 FastAPI 以任意子路径托管时资源可用
  base: './',
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8765', changeOrigin: true },
      '/ws': { target: 'ws://127.0.0.1:8765', ws: true },
    },
  },
})
