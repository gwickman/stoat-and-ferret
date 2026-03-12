import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/gui/',
  server: {
    proxy: {
      '/api': 'http://localhost:8765',
      '/health': 'http://localhost:8765',
      '/metrics': 'http://localhost:8765',
      '/ws': {
        target: 'http://localhost:8765',
        ws: true,
      },
    },
  },
})
