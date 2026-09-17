## Context

- `ProjectReviewListPage` 当前仅在 `actor` 变化时通过 `useEffect` 拉取评审列表；提交完成后该依赖不变化，列表停留在旧快照。
- `useDirectorySubmission` 在每份文件进入 `submitted` 时调用 `setItems`；这条状态更新没有跨组件可达的「我刚刚成功提交了一条」信号。
- 仓库已用 React Context 承载会话（`SessionContext`），无独立状态库，符合既有前端分层。
- 后端契约、错误转换器、API client 均不动；本设计只调整前端组件接线。

## Goals / Non-Goals

**Goals:**
- 在 `directory-review-workbench` 的现有能力下，新增一条「提交成功后自动刷新评审列表」的行为通道。
- 复用现有 React Context / Hook 工具，不引入新依赖。
- 多次并发提交触发合并为单次刷新，避免冗余 `GET /api/v1/reviews`。

**Non-Goals:**
- 不引入轮询、订阅、WebSocket 或 SSE。
- 不修改 `useReviewPolling`、决策表单或最终确认门控。
- 不改变根公共契约或后端行为。

## Decisions

### 1. 通过轻量 React Context 暴露「列表需要刷新」信号
- 新增 `frontend/src/features/reviews/ReviewsRefreshContext.tsx`，导出 `ReviewsRefreshProvider` 与 `useReviewsRefresher()` hook。
- Provider 维护一个 `refreshCounter` 状态与 `requestRefresh()` 函数；`requestRefresh` 调用一次即把 `refreshCounter` 递增，并通过 `useRef` 标记「本次有未消费的刷新请求」，避免同一 tick 内的多次递增被合并掉。
- `ProjectReviewListPage` 在该 hook 返回的 `refreshCounter` 变化时调用 `listReviews`；当 `actor` 变化时仍执行首次加载。两者并存，互不干扰。
- `DirectoryPicker` 渲染 `ReviewsRefreshProvider`，并在调用 `submit()` 后调一次 `requestRefresh()`，保证任意一层提交（目录、多文件回退、未来批量重试）都触发刷新。

**为何不用 window 自定义事件**：现有 `SessionContext` 已经展示了「用 React Context 共享跨页状态」的模式；自定义事件需要组件订阅 `window` 并解绑，调试链路也更隐式。

**为何不引入新状态管理库**：仓库根 `AGENTS.md` 与既有 `add-directory-ai-review-workbench/design.md` 都明确保持最少依赖；本场景只需一个计数器与一个回调函数。

### 2. 合并并发刷新请求
- `ProjectReviewListPage` 把「正在进行的 `listReviews`」保存到 ref；下一次 `refreshCounter` 变化时，如果上一轮请求尚未 `resolve`，先标记「还需要再拉一次」，等当前 promise 完成后立即再触发一次，而非堆积多次并发请求。
- 错误处理遵循 `useReviewPolling` 既有模式：失败时通过 `parseApiError` 暴露给组件层，UI 决定是否展示。

### 3. 提交失败不触发刷新
- `useDirectorySubmission` 仅在 `status === "submitted"` 时通知 Provider；`failed` / `submitting` / `pending` 不递增计数器，与 spec 中「Submission fails before reaching submitted」一致。
- 失败路径仍由 `FileEntryList` 通过 `onRetry` 提供独立重试入口，与现有契约保持一致。

### 4. 离开 `/reviews` 后提交完成的处理
- Provider 始终驻留在 `DirectoryPicker` 这一层，提交信号与导航解耦。
- 当审核人员不在 `/reviews` 时，`ProjectReviewListPage` 未挂载，计数变化不产生额外请求；下次进入时由 `actor` 触发的首次加载拿到最新列表（已经满足 spec 的「Reviewer is on a different page」分支）。

### 5. 测试与可观察性
- 新增单元测试覆盖 Provider 合并行为（两次 `requestRefresh` 在同 tick 内只触发一次 fetch）。
- 既有 `tests/e2e/workbench.spec.ts` 现有断言「Review row should appear in the list」在修复后应直接通过；保留它作为回归用例，并在 tasks 中明确验证。
- 控制台日志仅保留现有错误转换器产出，不增加调试噪音。

## Risks / Trade-offs

- [Provider 引入轻微组件耦合] → `ReviewsRefreshProvider` 仅服务评审刷新一类信号，与 `SessionContext` 一样保持职责单一；如果后续出现更多评审列表信号，再考虑扩展到 reviews 命名空间下。
- [刷新合并策略可能延迟最坏情况下 1 次额外拉取] → 与「避免并发冗余」取舍一致；最坏延迟为单次 `listReviews` 耗时，远低于「未刷新导致用户误以为提交失败」的风险。
- [离开页面后无主动 invalidate] → 既有「页面级 reload 即恢复」行为不变；不引入后台拉取以避免不必要带宽。

## Migration Plan

1. 提交本 change 后按 `tasks.md` 顺序执行。
2. 部署仅影响前端静态资源；后端不重启、不迁移数据。
3. 回滚只需恢复上一版前端构建产物；评审、决策与报告不变。
