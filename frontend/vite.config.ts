import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api/auth':  'http://localhost:4000',
      '/api/chat':  'http://localhost:4000',
      '/api/files': 'http://localhost:4000',
      '/api/otp':   'http://localhost:4000',
      '/api':       'http://localhost:8002',
    },
    historyApiFallback: true,
  },
})
