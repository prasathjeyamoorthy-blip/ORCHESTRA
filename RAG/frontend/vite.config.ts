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
      '/api/auth':        'http://localhost:4000',
      '/api/chat':        'http://localhost:4000',   // includes /api/chat/voice/speak and /api/chat/voice/tts
      '/api/files':       'http://localhost:4000',
      '/api/otp':         'http://localhost:4000',
      '/api/voice':       'http://localhost:8002',   // direct STT/TTS (called by Node, not frontend)
      '/api':             'http://localhost:8000',   // pan-rag (ask, flow, upload)
    },
    historyApiFallback: true,
  },
})
