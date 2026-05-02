import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), visualizer({ open: false, filename: 'dist/stats.html', gzipSize: true, brotliSize: true })],
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
