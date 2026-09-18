import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: {
    baseURL: process.env.TEST_BASE_URL || "http://localhost:8080",
    viewport: { width: 390, height: 844 },
    browserName: "chromium",
  },
  reporter: "list",
});
