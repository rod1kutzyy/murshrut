import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  forbidOnly: !!process.env.CI,
  workers: 1,
  use: {
    baseURL: process.env.TEST_BASE_URL || "http://localhost:8080",
    viewport: { width: 390, height: 844 },
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
});
