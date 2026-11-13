import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', workers: 1, fullyParallel: false, timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:8766', channel: 'chrome', headless: true,
    viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: { command: 'python ../tests/serve_browser.py', url: 'http://127.0.0.1:8766/api/profile',
    reuseExistingServer: false, timeout: 30000 },
});
