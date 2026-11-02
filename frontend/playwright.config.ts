import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./src/test/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 300_000,
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    viewport: { width: 1366, height: 768 },
  },
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
