## Why

后端 `EmptyModelGateway` 默认返回空 findings，导致 LangGraph 评审图跑完也是 0 条问题——本地端到端跑通但没有任何真实 AI 评审结果。要让产品具备真正的需求评审能力，需要接入 OpenAI-compatible 模型供应商并按 `data_policy` 在本地/云端之间路由。

## What Changes

- 新增 backend capability `model-gateway`：定义 `PolicyModelGateway`、MiniMax（OpenAI-compatible）的客户端构造、按 `data_policy` 的本地/云端/脱敏云三种调用路径，以及对凭据、错误、超时与成本护栏的要求。
- 在 `backend/src/requirement_review/` 增加一个 OpenAI-compatible HTTP 客户端模块，使用环境变量注入凭据与 base URL；任何凭据仅从环境读取，不写入代码、`.env`、`.env.example`、日志或报告。
- 替换 `create_app()` 中的默认服务构造：当 `REVIEW_MODEL_BACKEND=real` 且环境变量齐全时，构造 `PolicyModelGateway`；否则继续使用 `EmptyModelGateway` 以保留「空模型即开箱即用」的本地体验。
- 增加面向 `model-gateway` 的单元/集成测试：覆盖凭据缺失拒绝启动、`local_only` 拒绝云端调用、`cloud_redacted` 走脱敏路径、空响应与超时重试。

## Capabilities

### New Capabilities

- `model-gateway`: backend 内部 capability，覆盖 model gateway 抽象、供应商客户端、数据策略路由、凭据与失败处理。后端 spec 仅在 `backend/openspec/specs/model-gateway/spec.md` 维护；公共 HTTP 契约由根 `openspec/specs/public-contracts/spec.md` 定义，本 change 不修改。

### Modified Capabilities

无（HTTP 契约字段 `data_policy`、`errors`、`project isolation`、`evidence traceability` 已在根 public-contracts 中定义；本 change 仅替换实现，不改变契约）。

## Impact

- 新增代码：`backend/src/requirement_review/model_gateway/`（policy + MiniMax 客户端）、`backend/tests/model_gateway/`。
- 修改：`backend/src/requirement_review/api/app.py`（根据环境变量选择默认服务）；`backend/.env.example`（新增占位变量说明，不含真实值）；`backend/pyproject.toml`（如果引入新 HTTP 客户端依赖）。
- 部署/运行：新增环境变量 `REVIEW_MODEL_BACKEND`、`MINIMAX_API_KEY` / `MINIMAX_BASE_URL` / `MINIMAX_MODEL`（占位符在 `.env.example`，真实值由运维在 secrets manager 或容器 env 注入）。**不会**提交真实凭据。
- 兼容性：`EmptyModelGateway` 仍可用并继续作为无凭据场景下的默认；现有 e2e 与单测在不设置 `REVIEW_MODEL_BACKEND=real` 时不受影响。
- 安全：仅后端进程持有模型凭据；本地 e2e 测试不发送任何真实请求到 MiniMax。

## Non-goals

- 不引入新存储、不修改持久化层。
- 不修改 LangGraph 节点拓扑、不改变 review 维度的拆解逻辑。
- 不修改错误码、不修改事件 schema。
- 不写任何真实 API key 到仓库（包括注释、测试 fixture、`.env.example`）。
- 不在本 change 范围内接入多个模型供应商；后续如需多家可起独立 change 复用本 capability。
