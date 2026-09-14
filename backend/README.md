# Requirement Review API

基于 LangGraph 的需求评审 API：解析 Markdown 需求，检索项目背景知识，执行八维并行评审，在发布报告前暂停等待人工确认。

## 本地启动

```bash
cp .env.example .env
docker compose up -d postgres minio
python -m venv .venv
.venv/bin/pip install -e . pytest pytest-asyncio
.venv/bin/alembic upgrade head
.venv/bin/uvicorn requirement_review.api.app:app --reload
```

OpenAPI 位于 `http://localhost:8000/docs`。默认应用使用进程内运行时和安全的空模型提供者，方便验证 API 与人工审批流程；生产部署应在 `create_app()` 中注入数据库仓储、对象存储及 `PolicyModelGateway`。

## 调用示例

所有请求携带用户、项目和角色请求头：`X-User-ID`、`X-Project-ID`、`X-Role`。管理员先创建项目，然后使用返回的项目 ID 更新 `X-Project-ID`。

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H 'Content-Type: application/json' -H 'X-User-ID: admin' \
  -H 'X-Project-ID: bootstrap' -H 'X-Role: admin' \
  -d '{"name":"Payments","data_policy":"local_only"}'

curl -X POST http://localhost:8000/api/v1/projects/PROJECT_ID/knowledge/documents \
  -H 'X-User-ID: admin' -H 'X-Project-ID: PROJECT_ID' -H 'X-Role: admin' \
  -F 'file=@system.md;type=text/markdown'

curl -X POST http://localhost:8000/api/v1/reviews \
  -H 'Content-Type: application/json' -H 'X-User-ID: reviewer' \
  -H 'X-Project-ID: PROJECT_ID' -H 'X-Role: reviewer' \
  -d '{"project_id":"PROJECT_ID","text":"# Login\n\nThe system should log in quickly.","data_policy":"local_only"}'

curl http://localhost:8000/api/v1/reviews/REVIEW_ID \
  -H 'X-User-ID: reviewer' -H 'X-Project-ID: PROJECT_ID' -H 'X-Role: reviewer'

curl -X POST http://localhost:8000/api/v1/reviews/REVIEW_ID/approval \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: approval-1' \
  -H 'X-User-ID: reviewer' -H 'X-Project-ID: PROJECT_ID' -H 'X-Role: reviewer' \
  -d '{"action":"approve","comment":"approved"}'

curl http://localhost:8000/api/v1/reviews/REVIEW_ID/report \
  -H 'X-User-ID: reviewer' -H 'X-Project-ID: PROJECT_ID' -H 'X-Role: viewer'
```

## 模型与数据策略

- `local_only`：只允许调用本地模型。
- `cloud_allowed`：允许原文调用云模型。
- `cloud_redacted`：需求正文、证据引用和知识正文递归脱敏后才调用云模型。

生产代码通过 `PolicyModelGateway` 注入本地与云端 OpenAI-compatible 调用器。密钥只从环境或密钥服务读取，不写入配置、日志或报告。

## 测试

```bash
pytest -q
ruff check src tests alembic
mypy --follow-imports=skip src
alembic upgrade head --sql
```
