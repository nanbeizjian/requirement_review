## Why

`ProjectReviewListPage` 只在 `actor` 变化时拉取项目评审，提交成功后停留在 `/reviews` 的审核人员看到列表仍为「暂无评审任务」，必须手动导航或刷新页面才能看到新建的评审。本地 e2e 复现与仓库 `tests/e2e/workbench.spec.ts` 均因此在 30 秒后超时失败。

## What Changes

- 在前端为 `directory-review-workbench` 增加一项要求：每次有 Markdown 文件提交成功后，`/reviews` 列表 SHALL 在不依赖全页刷新的前提下重新拉取并显示新建行。
- 引入一条轻量的列表失效通道（事件或上下文方法），由 `useDirectorySubmission` 在 `submitted` 终态时触发，由 `ProjectReviewListPage` 订阅并调用 `listReviews`。
- 保留现有 `actor` 触发的初次加载行为；新增触发源与 `actor` 并列，均使列表重新获取。

## Capabilities

### New Capabilities

无（不引入新 capability）。

### Modified Capabilities

- `directory-review-workbench`：增加「提交成功后自动刷新评审列表」要求，覆盖当前依赖页面卸载/重入才能看到新评审的缺陷。

## Impact

- 受影响代码：`frontend/src/features/reviews/ProjectReviewListPage.tsx`、`frontend/src/features/directory/useDirectorySubmission.ts`、`frontend/src/features/directory/DirectoryPicker.tsx`，必要时新增 `frontend/src/features/reviews/useReviewsRefresher.ts` 或共享上下文。
- 不改变任何 HTTP API、身份头、错误契约或后端行为；共享契约仍由仓库根 `openspec/specs/public-contracts/spec.md` 权威定义。
- 与现有 `directory-review-workbench` delta 的 `Restore server state`、`Communicate progress and errors` 要求兼容：刷新期间使用既有错误转换器呈现安全消息。

## Non-goals

- 不引入 WebSocket、Server-Sent Events 或专用状态库；仅复用现有 React 状态与一次额外 `listReviews` 调用。
- 不修改 `useReviewPolling` 的退避或终态判定。
- 不改变目录选择、文件过滤、决策或最终确认流程。
- 不动后端模型、知识库、项目或评审 API。
