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
      '/api/chat':        'http://localhost:4000',
      '/api/files':       'http://localhost:4000',
      '/api/otp':         'http://localhost:4000',
      '/api/voice/speak': 'http://localhost:4000',  // routed through Node chat pipeline
      '/api/voice/tts':   'http://localhost:4000',  // proxied through Node with auth
      '/api/voice':       'http://localhost:8002',  // voice agent (STT/TTS direct)
      '/api':             'http://localhost:8000',  // pan-rag (chat, ask, flow)
    },
    historyApiFallback: true,
  },
})
