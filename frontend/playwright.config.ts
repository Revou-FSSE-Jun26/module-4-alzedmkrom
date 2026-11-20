import { defineConfig, devices } from '@playwright/test';

try {
  process.loadEnvFile('.env.local');
} catch {
  // No .env.local file. Variables may come from the shell environment instead.
}

const baseURL = (process.env.PLAYWRIGHT_BASE_URL ?? '').trim();

if (baseURL === '') {
  throw new Error(
    'PLAYWRIGHT_BASE_URL is unset or empty. Set it to the deployed Vercel URL, for example in .env.local.',
  );
}

export default defineConfig({
  testDir: 'e2e',
  timeout: 60000,
  expect: { timeout: 10000 },
  retries: 0,
  fullyParallel: true,
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
