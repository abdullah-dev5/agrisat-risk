import { defineConfig, devices } from '@playwright/test';

/**
 * E2E config. Requires the backend running separately on :8000 with real
 * Supabase + GEE credentials (backend/.env) -- these tests exercise the real
 * stack end to end, unlike the Vitest unit tests. See frontend/e2e/README.md.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false, // tests share one Supabase project + create real data; avoid races
  retries: 0,
  reporter: [['html', { open: 'never' }], ['list']],
  timeout: 60_000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'pnpm dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
