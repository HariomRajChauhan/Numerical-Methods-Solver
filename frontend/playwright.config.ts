import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./src/test/e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    viewport: { width: 1366, height: 768 },
  },
});
