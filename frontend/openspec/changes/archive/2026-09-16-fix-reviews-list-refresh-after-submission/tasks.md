## 1. Context 与 Refresh 信号

- [x] 1.1 在 `frontend/src/features/reviews/` 新增 `ReviewsRefreshContext.tsx`，导出 `ReviewsRefreshProvider` 与 `useReviewsRefresher()`，包含 `refreshCounter` 与 `requestRefresh()`；同一 tick 内的多次 `requestRefresh` 仅递增一次，验证方式：手写最小 Vitest 单元测试（同 tick 双调用 → counter 增 1；跨 tick 双调用 → counter 增 2），测试通过即视为完成。
- [x] 1.2 在 `frontend/src/features/directory/DirectoryPicker.tsx` 中以 `ReviewsRefreshProvider` 包裹当前内容，并在调用 `submit()` 后 await 一次 `requestRefresh()`；验证方式：在 DevTools React DevTools 中可见 Provider 包裹树，且提交任意 .md 后 `refreshCounter` 递增。

## 2. 列表组件接入 Refresh

- [x] 2.1 重构 `frontend/src/features/reviews/ProjectReviewListPage.tsx`：把当前 `useEffect` 拉取评审的逻辑抽成内部函数 `loadReviews`，由 `actor` 与 `refreshCounter` 共同触发；引入 ref 合并并发请求，下一轮 `refreshCounter` 变化且上一轮未完成时仅标记「需要再来一次」，resolve 后立即重跑。验证方式：新增 Vitest 组件测试覆盖（a）初始 actor 触发加载、（b）`refreshCounter` 从 0 跳到 1 触发加载、（c）刷新失败保留旧行不崩溃，测试通过即视为完成。
- [x] 2.2 修改 `useDirectorySubmission.ts`：在 `updateItem(id, { status: "submitted", reviewId })` 同一调用之后递增 `requestRefresh()`，但要保证 `failed` 分支不递增；验证方式：Vitest 单元测试覆盖（a）`submitted` 后调用 `requestRefresh` 一次、（b）`failed` 后不调用，测试通过即视为完成。

## 3. 错误与边界行为

- [x] 3.1 让 `ProjectReviewListPage` 在刷新失败时复用既有 `Alert` 错误呈现，且不重置已加载的 `reviews`；验证方式：组件测试模拟 `listReviews` 抛 `ApiError`，断言列表仍渲染刷新前数据且错误以 `Alert` 形式显示。
- [x] 3.2 验证非 `/reviews` 页（如详情、报告）提交完成时不影响该页焦点或输入；验证方式：在详情页焦点放在评论 textarea 上运行 Playwright，触发后台提交完成，断言 `document.activeElement` 仍是 textarea 且文本不丢失。

## 4. 验证与回归

- [x] 4.1 在 `frontend/` 运行 `npm test -- --run`，全部用例通过视为完成。
- [x] 4.2 在 `frontend/` 运行 `npm run lint` 与 `npm run typecheck`，无错误视为完成。
- [x] 4.3 在 `frontend/` 运行 `npm run build`，构建成功视为完成。
- [x] 4.4 在 `frontend/` 运行 `openspec validate fix-reviews-list-refresh-after-submission --strict`，组件 change 校验零错误视为完成。
- [x] 4.5 在 `frontend/` 运行 `npx playwright test`，`tests/e2e/workbench.spec.ts` 中「review row should appear in the list」由当前超时失败变为通过视为完成；同时复用 `e2e-out/run-e2e.mjs` 端到端脚本，截图 `05a-after-submit-still-empty` 与 `05b-after-reload-row-visible` 之间不再需要 `page.goto('/reviews')` 强制刷新，列表在脚本等待窗口内自动出现新行。


## 实施备注

- **任务 1.2 的小幅调整**：spec 文字是「DirectoryPicker 中包裹」，但 `ProjectReviewListPage` 与 `DirectoryPicker` 需要共享同一 Provider 实例才能让 `useDirectorySubmission`（在被 DirectoryPicker 调用的 hook）通知列表（ProjectReviewListPage 同级）。实际把 Provider 上移到 `App.tsx`（与 `SessionProvider` 同层），与既有 root-provider 模式一致；DirectoryPicker 通过 React Context 自然拿到同一实例。
- 既有 `tests/e2e/workbench.spec.ts`（用户本地的 uncommitted 修改）bootstrap 用字符串 `e2e-project` 作为 projectId，未使用创建项目返回的 UUID，导致 upload 拿到 404；这是测试设置问题，与本 change 无关。
