/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/setupTests.ts',
    // Scope to unit tests under src/ -- e2e/ holds Playwright specs (a
    // different test runner/API), and Vitest's default glob would otherwise
    // pick them up too and fail on them.
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 180_000,
        proxyTimeout: 180_000,
      },
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        timeout: 30_000,
      },
    },
  },
})
