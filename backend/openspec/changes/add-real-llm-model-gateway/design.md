## Context

- 后端 `EmptyModelGateway` 是默认网关，仅用于本地启动与 CI；其 `review()` 返回 `[]`，导致 LangGraph 评审图产出空 findings。
- 根公共契约 `openspec/specs/public-contracts/spec.md` 已定义 `data_policy`、`errors`、`project isolation`、`evidence traceability`；本 change 只替换内部实现，不修改契约。
- 后端 telemetry 模块已经接入 LangSmith（通过环境变量 `LANGCHAIN_*`）；新增模型调用应自动获得 trace 覆盖，无需新加 SDK。
- 真实凭据仅在生产环境注入，CI 与本地开发都走 fake transport。

## Goals / Non-Goals

**Goals:**
- 用 `PolicyModelGateway` 抽象隔离供应商，提供 OpenAI-compatible 客户端构造器注入。
- 通过环境变量 `REVIEW_MODEL_BACKEND=real` 启用真实模型；缺该变量或 `MINIMAX_API_KEY` 时回退到 `EmptyModelGateway`，不破坏现有 e2e。
- 在 `cloud_redacted` 模式下对原文与证据做脱敏后再上行。
- 让单元测试可在零外网条件下覆盖全部路由、超时与重试分支。

**Non-Goals:**
- 不接入多家供应商；后续可单独起 change。
- 不改造 LangGraph 节点拓扑、维度定义、知识检索或持久化层。
- 不修改错误码、报告 schema 或 HTTP 路径。

## Decisions

### 1. 抽象层：`PolicyModelGateway` + 注入式 HTTP 客户端

- 新增 `backend/src/requirement_review/model_gateway/policy.py`：定义 `PolicyModelGateway`，依赖 `local_client: ModelGateway` 与 `cloud_client: ModelGateway`，按 `data_policy` 分发。
- 新增 `backend/src/requirement_review/model_gateway/openai_compatible.py`：基于 `httpx.AsyncClient` 实现 `OpenAICompatibleClient`，参数包括 `base_url`、`model`、`api_key_env`、`timeout_s`、`max_retries`。`api_key` 始终从环境变量读取；构造时若环境变量未设置且 `required=True` 抛 `ModelGatewayConfigError`。
- `PolicyModelGateway` 仅暴露 `review()`，与现有 `ModelGateway` 协议保持完全一致；`review_dimension` 节点无需感知切换。
- 不引入新的重量级 SDK；`httpx` 已通过 FastAPI 测试依赖间接存在，若未声明则加入 `pyproject.toml` `dependencies` 而非 `dev`。

### 2. 默认值切换：`app.py` 的二元逻辑

- `create_app()` 在初始化 `InMemoryApplicationServices` 之前读取 `REVIEW_MODEL_BACKEND`：
  - 未设置 / `empty` / `off` → 保持 `EmptyModelGateway`（本地/CI 默认）。
  - `real` → 实例化 `OpenAICompatibleClient`（base URL 与 model 从 `MINIMAX_BASE_URL` / `MINIMAX_MODEL` 读取，默认 `https://api.minimaxi.com/v1` 与 `MiniMax-Text-01`），再注入 `PolicyModelGateway(local=local_client, cloud=cloud_client)`，其中 local 客户端默认指向一个不可达的本地占位端口以避免误用，cloud 走 MiniMax。
- `data_policy=local_only` 时实际调用 local 客户端；其余两种走 cloud。`PolicyModelGateway` 自身不做脱敏，脱敏放在 `OpenAICompatibleClient` 的请求包装层以保证任何路径上行前都过同一道闸。

### 3. 脱敏：`cloud_redacted` 的最小规则集

- 新增 `backend/src/requirement_review/model_gateway/redact.py`，使用正则实现：
  - 邮箱：`[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}` → `<email>`
  - 手机号（中国大陆 11 位）：`\b1[3-9]\d{9}\b` → `<phone>`
  - 身份证号 18 位：粗略模式 `\b\d{17}[\dXx]\b` → `<id>`
  - IPv4 / IPv6、RFC1918 主机名 → `<host>`
- 对 `requirement.text`、`knowledge[].text` 与 `evidence[].quote` 全部递归替换；替换在 payload 序列化前完成，原对象不动。

### 4. 超时、重试与失败隔离

- `OpenAICompatibleClient` 暴露 `connect_timeout_s`、`read_timeout_s`、`max_retries`（默认 2）；指数回避 `0.5s * 2^n + jitter`。
- 单维度失败通过 `try/except` 在 `review_dimension` 节点捕获，写入 `failed_dimensions`，不影响其他维度。
- 全部失败时 LangGraph 路径返回 `FAILED`；HTTP 层复用既有根公共契约错误：`{"code":"review_unavailable","message":...,"correlation_id":...}`，不暴露上游供应商响应原文。

### 5. 凭据与日志卫生

- 仅 `OpenAICompatibleClient.__init__` 读环境变量；其它模块不接触 key。
- 结构化日志统一通过 `bind_review_context` 输出；key 仅记录前 4 字符 + `***`（通过自定义 filter 而非第三方 SDK）。
- `.env.example` 仅放占位变量名（`MINIMAX_API_KEY=<set via secrets manager>`），不含真实 key。

### 6. 测试架构

- 新增 `backend/tests/model_gateway/`：
  - `test_policy_routing.py`：用 fake client 验证三种 `data_policy` 的路由选择。
  - `test_redact.py`：覆盖脱敏规则与嵌套对象递归。
  - `test_openai_compatible.py`：用 `httpx.MockTransport` 模拟超时、重试与 HTTP 4xx/5xx；断言 fake transport 的调用次数与 payload 脱敏后状态。
  - `test_credentials.py`：缺 `MINIMAX_API_KEY` 时构造 `PolicyModelGateway(real)` 应抛 `ModelGatewayConfigError`。
- 现有 `backend/tests/` 不修改。

## Risks / Trade-offs

- **[MiniMax API 协议细节不确定]** OpenAI-compatible 是行业事实标准；模型名/请求格式差异可能要求后续微调。→ 用 fake transport 测试覆盖正常路径；真机接入留作实施阶段验证。
- **[脱敏规则可能误伤]** 误例如把"1.0.0.1"误判为版本号 → 影响低（仅在 `cloud_redacted` 路径生效，且仅替换为 `<host>` 占位；不删内容）。
- **[缺 `httpx` 直接依赖]** 若环境未声明，会引入新的运行时依赖。→ 在 `pyproject.toml` 显式添加并锁版本。

## Migration Plan

1. 在 `backend/` 跑 `pip install -e .` 与 `pytest tests/model_gateway -q` 验证新模块不破坏既有套件。
2. 在本地手动设置 `REVIEW_MODEL_BACKEND=real` 与真实 `MINIMAX_API_KEY`，跑一次完整 e2e（前端 + 后端 + curl 建项目 + 上传 + 报告），人工核对至少一条 finding。
3. 生产部署：在 secrets manager 注入真实 `MINIMAX_API_KEY`，并由部署流水线渲染到容器 env；部署后再跑回归冒烟。
4. 回滚：把 `REVIEW_MODEL_BACKEND` 改回 `empty` 或 unset，进程自动回退到 `EmptyModelGateway`，无需代码回滚。

## Open Questions

- MiniMax 端模型名清单与速率限制需在实施阶段首次握手时确认；本 spec 不绑定具体模型。
- 是否需要为多供应商做预留（注册表模式）— 当前决策是「否」，后续可起独立 change。
