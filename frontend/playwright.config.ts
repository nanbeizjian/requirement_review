import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "retain-on-failure",
  },
  // webServer omitted: backend (uvicorn :8000) and frontend (vite :5173) are
  // expected to be running externally. Launch them with:
  //   cd backend && .venv/bin/python -m uvicorn requirement_review.api.app:app --host 127.0.0.1 --port 8000
  //   cd frontend && npm run dev
  projects: [
    {
      name: "chromium-headed",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: {
          executablePath: "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
          headless: false,
        },
      },
    },
  ],
});
