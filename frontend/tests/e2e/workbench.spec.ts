import { test, expect, type Page } from "@playwright/test";
import path from "node:path";
import { mkdirSync, writeFileSync } from "node:fs";

const FIXTURE_DIR = path.join(process.cwd(), "tests/e2e/.tmp");
mkdirSync(FIXTURE_DIR, { recursive: true });
writeFileSync(path.join(FIXTURE_DIR, "a.md"), "# A\n\nBody A", "utf8");
writeFileSync(path.join(FIXTURE_DIR, "B.Markdown"), "# B\n\nBody B", "utf8");
writeFileSync(path.join(FIXTURE_DIR, "ignore.txt"), "noise", "utf8");

async function bootstrap(page: Page) {
  await page.goto("/");
  await page.getByLabel(/用户 ID/).fill("u1");
  await page.getByLabel(/项目 ID/).fill("p1");
  await page.getByLabel(/角色/).selectOption("reviewer");
  await page.getByRole("button", { name: /开始/ }).click();
  const ok = await page.request.post("http://localhost:8000/api/v1/projects", {
    headers: { "X-User-ID": "u1", "X-Project-ID": "p1", "X-Role": "admin" },
    data: { name: "demo", data_policy: "local_only" },
  });
  expect(ok.status()).toBeLessThan(400);
}

test("directory → reviews → approval → report", async ({ page }) => {
  await bootstrap(page);
  await page.getByTestId("dir-input").setInputFiles([
    path.join(FIXTURE_DIR, "a.md"),
    path.join(FIXTURE_DIR, "B.Markdown"),
    path.join(FIXTURE_DIR, "ignore.txt"),
  ]);
  await expect(page.getByText(/忽略 1 个非 Markdown 文件/)).toBeVisible();
  await page.getByRole("button", { name: /开始提交/ }).click();

  await expect(page.getByRole("link", { name: /a\.md|B\.Markdown/ }).first()).toBeVisible({ timeout: 30_000 });
  await page.getByRole("link", { name: /a\.md/ }).first().click();
  const approveBtn = page.getByRole("button", { name: /最终确认/ });
  await expect(approveBtn).toBeEnabled({ timeout: 30_000 });
  await approveBtn.click();
  await expect(page.getByRole("button", { name: /已确认/ })).toBeVisible();
  await page.getByRole("link", { name: /查看最终报告/ }).click();
  await expect(page.getByRole("region", { name: /报告内容/ })).toBeVisible();
});
