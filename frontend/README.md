# Requirement Review Workbench — Frontend

聚焦目录级 AI 评审流程的 React + TypeScript 前端工作台。

## 开发

```bash
npm install
npm run dev          # http://localhost:5173；/api/v1 代理到 http://localhost:8000
npm run typecheck
npm test -- --run
npm run build
npm run lint
```

## 会话

首次访问 `/` 进入"建立会话"页。输入 `user_id / project_id / role` 后写入 `sessionStorage['rr:session:v1']`。
后续请求由 `apiClient` 自动注入 `X-User-ID` / `X-Project-ID` / `X-Role` 头。**审核事实**（findings、decisions、idempotency keys）不写入本地存储。

## 目录选择

`<input webkitdirectory>` 是首选；当浏览器不支持时退回到多文件 `<input type="file" multiple>`。
仅 `.md` 与 `.markdown`（大小写不敏感）进入提交队列，其他文件计入"忽略"。
请求体只携带 Markdown 文本与文件名（basename），绝不发送绝对路径。

## 审核与确认

- 每份 Markdown 文档对应一个独立 review；并发上限 3。
- 每个 finding 是独立卡片；reviewer/admin 可执行 accept / reject / re-review 并填意见。
- 决策与最终确认使用 UUID v4 幂等键；同 key 重试返回原结果，同 key 异 body 返回 409。
- 所有 finding 最新决策均为 accept/reject（或无 finding）时才启用最终确认。
- 报告页将 Markdown 文本以 `<pre>` 转义展示，无第三方渲染依赖。

## 角色门控

| 角色 | 列表 | 详情 | 决策 | 最终确认 |
|------|------|------|------|----------|
| viewer | ✓ | ✓ | – | – |
| reviewer | ✓ | ✓ | ✓ | ✓ |
| admin | ✓ | ✓ | ✓ | ✓ |

后端是授权最终来源；UI 门控是建议性的。

## 测试

- `npm test` — Vitest + RTL + MSW，覆盖单元、组件、集成
- `npm run test:e2e` — Playwright 真实后端端到端
