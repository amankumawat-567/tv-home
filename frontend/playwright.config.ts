import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 15_000,
  // All projects share one backend process (TV Home only ever runs as a
  // single instance on the real PC, so the mock backend isn't built for
  // per-test isolation). Running fully parallel lets one test's WS state
  // broadcast land mid-keypress in another and glitch its focus geometry —
  // serial execution matches how the app is actually used and avoids that.
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "off",
  },
  webServer: [
    {
      command: "npm run dev -- --port 5173",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
    },
    {
      command: "../backend/.venv/bin/uvicorn tv_home.main:app --port 8000",
      cwd: "../backend",
      env: { TV_HOME_MOCK: "1" },
      url: "http://127.0.0.1:8000/api/state",
      reuseExistingServer: true,
    },
  ],
  projects: [
    { name: "1366x768", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 } } },
    { name: "1920x1080", use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 } } },
  ],
});
