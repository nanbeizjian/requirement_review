## ADDED Requirements

### Requirement: Review source metadata

创建评审的公开请求 SHALL 接受可选的 `source_name` 字段用于保存用户可见的文档名称。服务端 SHALL NOT 要求或推断客户端绝对路径，并 SHALL 在评审查询响应中返回经过安全处理的 `source_name`。不提供该字段的现有请求 SHALL 继续有效。

#### Scenario: Client submits a local document name

- **WHEN** 客户端创建评审并提供 `source_name`
- **THEN** 服务端将该名称关联到评审任务并在后续查询中返回
- **AND** 不保存客户端绝对目录路径

#### Scenario: Existing client omits source name

- **WHEN** 现有客户端创建评审但不提供 `source_name`
- **THEN** 服务端按原有行为接受请求
- **AND** 响应仍满足原有字段契约

### Requirement: Project-scoped review listing

服务端 SHALL 提供 `GET /api/v1/reviews`，按已认证项目列出该项目的评审任务。响应中的每项 SHALL 至少包含 `review_id`、`project_id`、`source_name`、`status`、`finding_count`、`pending_decision_count` 和创建时间，并 SHALL 支持稳定排序。调用者 MUST NOT 通过查询参数扩大到其他项目范围。

#### Scenario: Reviewer lists project reviews

- **WHEN** 已认证调用者请求评审任务列表
- **THEN** 服务端仅返回请求头所标识项目的评审任务
- **AND** 按创建时间倒序并以 `review_id` 作为稳定的次级排序键

#### Scenario: Project has no reviews

- **WHEN** 当前项目没有评审任务
- **THEN** 服务端返回成功响应和空项目列表

### Requirement: Finding decision projection

`GET /api/v1/reviews/{review_id}/findings` SHALL 保持返回 finding 数组，并 SHALL 为每个 finding 增加可空的 `decision` 字段。非空决策 SHALL 包含 `action`、`comment`、`actor_id`、`decided_at` 和 `idempotency_key`，代表该 finding 的最新有效人工决策。

#### Scenario: Finding has not been reviewed

- **WHEN** finding 尚无人工决策
- **THEN** 查询结果中的 `decision` 为 `null`

#### Scenario: Finding has a decision

- **WHEN** reviewer 已对 finding 提交有效决策
- **THEN** 查询结果包含最新决策的操作、意见、审核人、时间和幂等键
- **AND** 原有 finding 字段保持兼容

### Requirement: Idempotent finding decisions

finding 决策请求 SHALL 使用 `Idempotency-Key` 在项目、评审和 finding 范围内实现幂等。使用同一幂等键和相同请求体的重试 SHALL 返回原决策；使用同一幂等键但不同请求体 SHALL 返回兼容错误契约中的冲突错误。

#### Scenario: Decision request is retried

- **WHEN** 客户端以相同幂等键和相同请求体重试 finding 决策
- **THEN** 服务端返回首次创建的决策
- **AND** 不生成重复审计记录

#### Scenario: Idempotency key is reused with different content

- **WHEN** 客户端以相同幂等键提交不同决策内容
- **THEN** 服务端拒绝请求并返回稳定的冲突错误码

### Requirement: Document finalization gate

服务端 SHALL 仅在评审的每个当前 finding 均具有 `accept` 或 `reject` 人工决策时接受整份文档的 `approve` 操作。存在未决 finding 或最新决策为 `re-review` 时，服务端 SHALL 返回兼容错误契约且 SHALL NOT 发布最终报告。没有 findings 的成功评审 SHALL 允许人工最终确认。

#### Scenario: Approval is attempted with undecided findings

- **WHEN** reviewer 在仍有未决 finding 时提交整份文档批准
- **THEN** 服务端拒绝批准并返回稳定的前置条件错误码
- **AND** 评审报告不成为最终状态

#### Scenario: Approval follows all finding decisions

- **WHEN** 所有当前 findings 的最新决策均为接受或拒绝且 reviewer 提交最终批准
- **THEN** 服务端完成评审并生成可获取的最终报告

#### Scenario: Review has no findings

- **WHEN** 自动评审成功完成但没有产生 finding
- **THEN** reviewer 仍可执行整份文档最终批准

### Requirement: Contract compatibility and migration

新增查询端点和新增响应字段 SHALL 向后兼容。现有创建评审、查询单个评审、提交 finding 决策和最终审批的 URL 及既有请求字段 SHALL 保持有效。部署升级 SHALL 使用可空字段和向前迁移保存来源名称、决策时间及查询索引，无需客户端停机迁移。

#### Scenario: Legacy client uses existing API shape

- **WHEN** 旧客户端不发送 `source_name` 且忽略新增响应字段
- **THEN** 其现有评审生命周期继续工作

#### Scenario: Deployment migrates existing records

- **WHEN** 服务端升级包含历史评审和 finding 决策的数据存储
- **THEN** 历史记录保持可查询
- **AND** 缺失的新增元数据以空值或可推导的安全默认值表示
