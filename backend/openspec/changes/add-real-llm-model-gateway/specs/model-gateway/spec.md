## Purpose

定义 backend 评审图调用语言模型的网关契约、能力开关、数据策略路由与凭据处理，确保真实模型接入后仍符合根公共契约对错误、数据驻留与项目隔离的要求。

## ADDED Requirements

### Requirement: Policy-aware model gateway

后端 SHALL 通过 `PolicyModelGateway` 抽象执行模型评审；调用 SHALL 仅暴露 `ModelGateway` 协议，禁止业务节点直接 import 供应商客户端。`PolicyModelGateway` SHALL 接受 `data_policy`（来自根公共契约）并按 `local_only` / `cloud_allowed` / `cloud_redacted` 决定实际调用路径。

#### Scenario: Local-only review routes to local endpoint

- **WHEN** 评审请求的 `data_policy` 为 `local_only`
- **THEN** 网关 SHALL 仅调用本地模型客户端
- **AND** SHALL NOT 向云端供应商发起任何 HTTP 请求

#### Scenario: Cloud-allowed review reaches cloud endpoint

- **WHEN** `data_policy` 为 `cloud_allowed` 且云端凭据已注入
- **THEN** 网关 SHALL 直接调用云端供应商
- **AND** 原文 SHALL 按供应商要求传输

#### Scenario: Cloud-redacted review redacts before egress

- **WHEN** `data_policy` 为 `cloud_redacted`
- **THEN** 网关 SHALL 在调用云端前对需求正文、证据引用与知识正文递归脱敏
- **AND** 脱敏规则 SHALL 至少覆盖邮箱、手机号、身份证号、IPv4/IPv6、内部主机名

### Requirement: Read credentials only from environment

模型供应商凭据 SHALL 仅通过环境变量读取，禁止出现在代码、`.env`、`.env.example`、日志、错误响应或报告中。缺凭据 SHALL 拒绝启动并返回稳定的内部错误码。

#### Scenario: Missing cloud credentials

- **WHEN** `REVIEW_MODEL_BACKEND=real` 且 `MINIMAX_API_KEY` 未设置
- **THEN** `PolicyModelGateway` 构造 SHALL 抛出明确异常
- **AND** 进程 SHALL NOT 继续运行 LangGraph 评审

#### Scenario: Backend disabled

- **WHEN** `REVIEW_MODEL_BACKEND` 未设置或等于 `empty`
- **THEN** 后端 SHALL 继续使用 `EmptyModelGateway`，不读取云端凭据
- **AND** 现有 e2e 与单测 SHALL 维持既有行为

#### Scenario: Credential never appears in error responses

- **WHEN** 网关或上游供应商抛错
- **THEN** 公开错误响应 SHALL NOT 包含 API key、base URL 之外的身份信息
- **AND** 服务端日志 SHALL 仅记录 key 的前缀与掩码后缀

### Requirement: Bound call latency and retry budget

每次模型评审 SHALL 设置显式 connect / read 超时；超时 SHALL 按维度隔离，单维度失败 SHALL 标记为 `failed_dimension` 而非终止整份评审。指数回退 SHALL 有上限（最多 2 次重试），并 SHALL 记录到 LangSmith。

#### Scenario: Single dimension times out

- **WHEN** 某个评审维度在超时预算内未返回
- **THEN** 该维度 SHALL 被记入 `failed_dimensions`
- **AND** 其他维度 SHALL 继续完成评审

#### Scenario: All dimensions fail

- **WHEN** 所有维度都失败或超时
- **THEN** 评审 SHALL 进入 `FAILED` 终态
- **AND** 公开错误响应 SHALL 包含稳定的 `review_unavailable` 错误码与关联 ID

### Requirement: Enforce project isolation at gateway

`PolicyModelGateway.review()` SHALL 接收 `project_id` 并把它作为上下文约束传入供应商调用；上游返回的 findings SHALL 经过项目隔离校验：任何引用了其他项目知识或文档的证据 SHALL 被剔除并记录为无效。

#### Scenario: Cross-project evidence detected

- **WHEN** 模型在响应中引用了非 `project_id` 范围内的证据
- **THEN** 网关 SHALL 丢弃该 finding 并在诊断日志中记录原因
- **AND** 评审 SHALL 继续使用剩余 findings

### Requirement: Testability without network egress

`PolicyModelGateway` SHALL 提供可注入的传输接口（HTTP 客户端构造器），单元与集成测试 SHALL 通过 fake transport 覆盖三种 `data_policy`、超时、重试与凭据缺失路径，且 SHALL NOT 在 CI 中向真实供应商发送请求。

#### Scenario: Local CI test uses fake transport

- **WHEN** 测试未设置 `MINIMAX_API_KEY` 且使用 fake transport
- **THEN** 测试 SHALL 验证调用次数、payload 脱敏效果与超时分支
- **AND** SHALL NOT 触达任何外网主机
