import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Proxy API requests to Django dev server
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // Media files
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // WebSocket proxy for Django Channels (if frontend uses /ws)
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
