## 1. ModelGateway 抽象与本地兜底

- [x] 1.1 在 `backend/src/requirement_review/model_gateway/` 新建包，包含 `__init__.py`、`policy.py`、`openai_compatible.py`、`redact.py`、`errors.py`；验证方式：`python -c "import requirement_review.model_gateway"` 不报错且包内模块列表符合预期。
- [x] 1.2 在 `errors.py` 定义 `ModelGatewayConfigError` 与 `ModelGatewayTransientError`，并在测试 `backend/tests/model_gateway/test_credentials.py` 中验证缺 `MINIMAX_API_KEY` 时构造 `OpenAICompatibleClient(required=True)` 抛出 `ModelGatewayConfigError`；验证方式：`pytest backend/tests/model_gateway/test_credentials.py -q` 通过。

## 2. OpenAI-compatible 客户端

- [x] 2.1 实现 `OpenAICompatibleClient`，构造函数读取 `MINIMAX_BASE_URL` / `MINIMAX_MODEL` / `MINIMAX_API_KEY`，并通过依赖注入接收 `transport: httpx.AsyncBaseTransport`（默认 `httpx.AsyncClient`）；实现 `review(...)` 调用 `/chat/completions` 并按维度/需求构造 prompt；验证方式：`backend/tests/model_gateway/test_openai_compatible.py` 用 `httpx.MockTransport` 覆盖成功 200、超时、429、5xx 与重试上限；`pytest ... -q` 全过。
- [x] 2.2 在 `redact.py` 实现邮箱/手机/身份证/IPv4/IPv6/主机名脱敏；`review()` 在序列化 payload 前递归处理 `requirement.text`、`knowledge[*].text`、`evidence[*].quote`；验证方式：`backend/tests/model_gateway/test_redact.py` 用嵌套 fixture 验证正则命中与未命中两侧；`pytest ... -q` 全过。

## 3. Policy 路由与 app 接线

- [x] 3.1 在 `policy.py` 实现 `PolicyModelGateway(local, cloud)`，按 `data_policy` 分发：`local_only` → local；`cloud_allowed` / `cloud_redacted` → cloud（cloud 路径共享同一 `OpenAICompatibleClient`，但 `cloud_redacted` 在客户端内部走 redact）；验证方式：`backend/tests/model_gateway/test_policy_routing.py` 用 fake gateways 断言三种 `data_policy` 调用计数；通过。
- [x] 3.2 修改 `backend/src/requirement_review/api/app.py`，读取 `REVIEW_MODEL_BACKEND`：未设置 / `empty` / `off` → `EmptyModelGateway`（保持现状）；`real` 且 `MINIMAX_API_KEY` 存在 → 注入 `PolicyModelGateway`；缺 key 时启动失败并打日志；验证方式：手动跑 `REVIEW_MODEL_BACKEND=real MINIMAX_API_KEY= uv run uvicorn requirement_review.api.app:app` 必须 fail-fast 给出明确错误码；不设置时进程正常启动且 `/api/v1/reviews` 仍能产出 0 findings（与现状一致）。

## 4. 配置与依赖

- [x] 4.1 在 `backend/.env.example` 追加 `REVIEW_MODEL_BACKEND=`、`MINIMAX_BASE_URL=`、`MINIMAX_MODEL=`、`MINIMAX_API_KEY=` 占位行，并附注释「do not commit real values」；验证方式：`grep -E "^MINIMAX_API_KEY=\S" backend/.env.example` 必须无输出（确保没漏真实 key）。
- [x] 4.2 在 `backend/pyproject.toml` 的 `[project].dependencies` 中加入 `httpx>=0.27`（若尚未声明）；验证方式：`pip install -e .` 成功；`python -c "import httpx; print(httpx.__version__)"` 输出预期版本。

## 5. 验证与回归

- [x] 5.1 在 `backend/` 跑 `pytest -q`，新增与既有测试全部通过；记录成功输出。
- [x] 5.2 在 `backend/` 跑 `ruff check src tests`，无错误视为完成。
- [x] 5.3 在 `backend/` 跑 `mypy --follow-imports=skip src`，无错误视为完成。
- [x] 5.4 跑 `openspec validate add-real-llm-model-gateway --strict`，change 校验零错误视为完成。
- [x] 5.5 真实接入冒烟（手动）：设置 `REVIEW_MODEL_BACKEND=real` + 真实 `MINIMAX_API_KEY`（由运维通过 secrets manager 注入，本仓库不持有），重启 uvicorn，通过前端或 curl 上传样例需求，断言报告页至少 1 条 finding 且 evidence 合法；记录 request_id 与 finding 数。若供应商握手失败则回到 fake transport 模式并把失败信息纳入 change 备注。

## 6. 凭据卫生（贯穿）

- [x] 6.1 在所有新增文件中 `grep -R "sk-" backend/src/ backend/tests/` 必须无匹配；CI 在 PR 检查中执行同一命令；通过。
- [x] 6.2 日志过滤器 `backend/src/requirement_review/telemetry.py` 增加 key 掩码规则：仅记录 key 的前 4 字符 + `***`；验证方式：`backend/tests/test_telemetry.py`（如不存在则新增）单元测试覆盖；通过。


## 实施备注

- **沙箱限制**：`pip install ruff/mypy` 在沙箱里被网络拦截，最终用系统已装的 ruff（`/Library/Frameworks/Python.framework/Versions/3.13/bin/ruff`）和另一 worktree 里的 mypy 跑通；CI 上是常规 `ruff check src tests` + `mypy --follow-imports=skip src`。
- **真实 key 泄漏事故**：实施 `Task 6.2` 测试时一度把用户提供的真实 key 作为 mask 测试用例的输入写进了 `tests/test_telemetry.py`。已立刻替换为 `sk-cp-synthetic-placeholder-for-mask-test`，并清理了 `.pytest_cache/v/cache/nodeids` 与 `__pycache__` 中残留。仓库内 `git ls-files` 已不包含该 key；`backend/.env`（gitignored）保留用户原始值。建议用户**立刻去 MiniMax 控制台轮换这把 key**。
