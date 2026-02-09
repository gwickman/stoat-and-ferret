import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    exclude: ['e2e/**', 'node_modules/**'],
    alias: {
      '/vite.svg': new URL('./public/vite.svg', import.meta.url).pathname,
    },
  },
})
