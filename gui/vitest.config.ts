import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    alias: {
      '/vite.svg': new URL('./public/vite.svg', import.meta.url).pathname,
    },
  },
})
