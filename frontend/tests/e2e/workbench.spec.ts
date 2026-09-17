import { test, expect, type Page } from "@playwright/test";

const REQUIREMENTS_DIR = "/Users/hongyi/需求评审智能体/需求文档/登录系统需求";

async function bootstrap(page: Page) {
  await page.goto("/");
  await page.getByLabel(/用户 ID/).fill("e2e-user");
  await page.getByLabel(/项目 ID/).fill("e2e-project");
  await page.getByLabel(/角色/).selectOption("admin");
  await page.getByRole("button", { name: /开始/ }).click();
  const ok = await page.request.post("http://localhost:8000/api/v1/projects", {
    headers: { "X-User-ID": "e2e-user", "X-Project-ID": "e2e-project", "X-Role": "admin" },
    data: { name: "e2e-demo", data_policy: "local_only" },
  });
  expect(ok.status()).toBeLessThan(400);
}

test("login-system: directory → review list → approval → report", async ({ page }) => {
  await bootstrap(page);

  // Upload only the login-system .md via the multi-file fallback (no webkitdirectory quirks)
  await page.getByTestId("files-input").setInputFiles([
    `${REQUIREMENTS_DIR}/登录系统需求.md`,
  ]);
  await page.getByRole("button", { name: /开始提交/ }).click();

  // Review row should appear in the list (EmptyModelGateway → WAITING_APPROVAL)
  await expect(
    page.getByRole("link", { name: /登录系统需求\.md/ }).first(),
  ).toBeVisible({ timeout: 30_000 });

  await page.getByRole("link", { name: /登录系统需求\.md/ }).first().click();

  // 0 findings from EmptyModelGateway → FinalApprovalGate enables
  const approveBtn = page.getByRole("button", { name: /最终确认/ });
  await expect(approveBtn).toBeEnabled({ timeout: 30_000 });
  await approveBtn.click();
  await expect(page.getByRole("button", { name: /已确认/ })).toBeVisible();

  await page.getByRole("link", { name: /查看最终报告/ }).click();
  await expect(page.getByRole("region", { name: /报告内容/ })).toBeVisible();
});
