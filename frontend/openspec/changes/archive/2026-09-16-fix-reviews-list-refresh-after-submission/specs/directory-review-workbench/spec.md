## ADDED Requirements

### Requirement: Refresh the project review list after a successful submission

当 `useDirectorySubmission` 把一份 Markdown 文件标记为 `submitted` 后，前端 SHALL 在不要求审核人员刷新整页、离开页面或重新登录的前提下，使当前 `/reviews` 列表自动重新调用根公共契约中的 `GET /api/v1/reviews` 并展示新建评审行。该刷新 SHALL 独立于初次加载时的 `actor` 触发源；两者 SHALL 共存。

#### Scenario: One document finishes submitting

- **WHEN** 审核人员提交了一份 Markdown 文件且后端返回 `202 Accepted`，上传队列中对应项进入 `submitted` 状态
- **THEN** `/reviews` 列表在不超过一次后台轮询节拍（最长 1 秒）内重新拉取
- **AND** 新评审行出现在「项目评审」表格中，无需手动刷新或导航

#### Scenario: Several documents finish in parallel

- **WHEN** 审核人员一次性提交了多份 Markdown 文件且其中至少一份进入 `submitted`
- **THEN** 前端 SHALL 合并多次提交触发的刷新请求，避免对 `GET /api/v1/reviews` 产生冗余并发调用
- **AND** 列表最终展示所有后端确认存在的评审行

#### Scenario: Submission fails before reaching submitted

- **WHEN** 一份 Markdown 文件在读取、提交或服务端受理阶段失败并进入 `failed` 状态
- **THEN** 前端 SHALL NOT 因为该失败触发列表刷新
- **AND** 失败文件仍按既有契约显示安全错误信息和单独重试入口

#### Scenario: Reviewer is on a different page

- **WHEN** 提交进行时审核人员已离开 `/reviews` 进入详情或报告页
- **THEN** 提交完成事件 SHALL 被记录下来；审核人员下次访问 `/reviews` 时 SHALL 看到最新列表
- **AND** 不应在非列表页面产生意外导航

### Requirement: Surface refresh errors without losing previously loaded rows

刷新过程中如果 `listReviews` 抛出根公共错误契约中的安全错误，前端 SHALL 保留上一次成功加载的评审行，并以不阻塞新评审提交的方式呈现该错误。该要求 SHALL 与既有 `Communicate progress and errors` 要求并存。

#### Scenario: Background refresh fails after a successful submission

- **WHEN** 提交成功后触发的 `listReviews` 返回非 2xx 响应
- **THEN** 前端显示来自错误适配器的安全消息和关联 ID
- **AND** 列表保留刷新前的可见行
- **AND** 审核人员可继续手动重试或重新提交而不丢失上下文

#### Scenario: Reviewer keeps typing in the comment box

- **WHEN** 详情页意见输入框正在被使用且同时发生列表刷新失败
- **THEN** 详情页 SHALL NOT 因为列表错误而丢失焦点或清空未保存的意见
