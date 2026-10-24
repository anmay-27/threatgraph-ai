import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
const python =
  process.env.THREATGRAPH_PYTHON ||
  resolve(
    process.platform === "win32"
      ? "../.venv/Scripts/python.exe"
      : "../.venv/bin/python",
  );
export default defineConfig({
  testDir: "./e2e",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:3000",
    channel:
      process.env.PLAYWRIGHT_CHANNEL ||
      (process.platform === "win32" ? "msedge" : undefined),
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: '"' + python + '" "' + resolve("../scripts/dev_api.py") + '"',
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      env: {
        DATABASE_URL: "sqlite:///./storage/e2e.db",
        MODEL_DIR: "models",
        TASK_ALWAYS_EAGER: "true",
      },
    },
    {
      command: "npm run preview -- --host 127.0.0.1",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
