import { defineConfig, devices } from "@playwright/test"
import path from "path"

const PROJECT_ROOT = path.resolve(__dirname, "..")
const E2E_DIR = __dirname

export default defineConfig({
  testDir: E2E_DIR,
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "setup",
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: path.join(E2E_DIR, ".auth/user.json"),
      },
      dependencies: ["setup"],
    },
  ],
  webServer: [
    {
      command: `cd "${PROJECT_ROOT}" && PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/backend" DATASTORE_EMULATOR_HOST=localhost:8081 backend/.venv/bin/uvicorn backend.app.main:app --port 8000`,
      port: 8000,
      reuseExistingServer: !process.env.CI,
      env: {
        PYTHONPATH: `${PROJECT_ROOT}:${PROJECT_ROOT}/backend`,
        DATASTORE_EMULATOR_HOST: "localhost:8081",
        AUTH_MOCK_MODE: "true",
        ALLOWED_EMAILS: "",
      },
    },
    {
      command: `cd "${PROJECT_ROOT}/frontend" && npm run dev`,
      port: 5173,
      reuseExistingServer: !process.env.CI,
    },
  ],
})
