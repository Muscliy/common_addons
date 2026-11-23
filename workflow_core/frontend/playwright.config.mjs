import { defineConfig } from '@playwright/test';

export default defineConfig({
    testDir: './tests', workers: 1, timeout: 30000,
    use: { browserName: 'chromium', channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' },
});
