import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src')
        }
    },
    // 关键：添加代理配置
    server: {
        port: 4173,
        proxy: {
            // 本地开发固定转发到手动启动的 Uvicorn，避免 Docker 的 localhost 端口抢占。
            '/api': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true
            }
        }
    }
})
