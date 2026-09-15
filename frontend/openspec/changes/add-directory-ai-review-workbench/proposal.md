## Why

仓库缺少审核人员可使用的前端，无法从本地需求目录批量发起 AI 评审，也无法把一份文档产生的多个 findings 作为独立记录逐条人工确认。需要建立聚焦该流程的前端工作台。

## What Changes

- 新增 React + TypeScript 前端工作台，支持选择本地目录并筛选 Markdown 文件。
- 为每份 Markdown 文档创建独立评审任务，展示逐文件进度和失败重试。
- 将每个 AI finding 展示为独立评审记录，并显示来源、维度、严重程度、影响、建议和证据。
- 支持 reviewer 对每条记录执行接受、拒绝或重新评审并填写意见。
- 在所有评审记录处理完成后启用整份文档最终确认，并提供最终报告页面。
- 页面刷新后从服务端恢复任务和人工审核状态。

## Capabilities

### New Capabilities

- `directory-review-workbench`: 定义目录选择、逐文件评审、评审点列表、人工审核、失败恢复和最终报告的前端行为。

### Modified Capabilities

无。

## Impact

- 新建 `frontend/` React + TypeScript + Vite 应用、组件、路由、typed API client 和测试。
- 依赖根 change `openspec/changes/add-directory-ai-review-workbench/` 定义的 `public-contracts` 扩展。
- 公共 API、授权、项目隔离、错误和评审工作流均引用仓库根 `openspec/specs/public-contracts/spec.md`，本组件不重复定义。
- 浏览器目录选择使用渐进增强，并提供多文件选择回退。

## Non-goals

- 不定义或修改共享 HTTP API 契约和后端领域模型。
- 不在服务端保存用户本地目录结构，也不上传非 Markdown 文件。
- 不实现登录、用户管理、多人任务分派、通知或实时协作。
- 不改变 AI 评审维度、模型策略或知识库管理流程。
