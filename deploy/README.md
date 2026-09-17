---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 130c2f895c4051dd8abf72b73e72caee_c913e5f6b27b11f18368525400248c00
    ReservedCode1: 6VGTX8RqdUVs/xJHLonFdUBSlAIkwGseECrJVl2tdNR2vMWEepMNNhAJppi5x7M0WEPOA42mmCQGHLiQs45DHG9Q+2A/SPTUl4ZeNKPhocjJnGhtNpk4rKQ66CR1sSMk/pJIXNyJKhRhnp1X7SxkhFE/PBFyZW3q8xpyWxKiZA3geXknu7d89WPdYoU=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 130c2f895c4051dd8abf72b73e72caee_c913e5f6b27b11f18368525400248c00
    ReservedCode2: 6VGTX8RqdUVs/xJHLonFdUBSlAIkwGseECrJVl2tdNR2vMWEepMNNhAJppi5x7M0WEPOA42mmCQGHLiQs45DHG9Q+2A/SPTUl4ZeNKPhocjJnGhtNpk4rKQ66CR1sSMk/pJIXNyJKhRhnp1X7SxkhFE/PBFyZW3q8xpyWxKiZA3geXknu7d89WPdYoU=
---

# requirement_review 部署指南

目标：把 requirement_review（FastAPI 后端 + Vite/React 前端 + PostgreSQL + MinIO）部署到新的服务器/环境。

## 部署文件清单（deploy/）

| 文件 | 用途 |
|------|------|
| `init.sql` | 数据库初始化 SQL（等价 `alembic upgrade head`，含全部表、约束、索引、外键，已写入 alembic 版本标记 0001） |
| `docker-compose.prod.yml` | 生产栈编排：postgres + minio + api(backend) + web(nginx 托管前端) |
| `frontend.Dockerfile` | 前端多阶段构建镜像（node 构建 → nginx 托管） |
| `nginx.conf` | nginx 配置：静态资源 + `/api/v1` 反代到 api:8000 |
| `init-minio.sh` | MinIO bucket 初始化脚本（需 `mc` 客户端） |
| `README.md` | 本文档 |

## 一、快速开始（全新部署）

```bash
# 1. 进入项目根目录，确认 deploy/ 与 backend/ frontend/ 同级
cd requirement_review

# 2. 准备密钥配置（可选，至少建议改数据库密码和 MinIO 密码）
cp deploy/.env.example deploy/.env   # 若未提供 .env.example 则手动创建，见下节
vi deploy/.env

# 3. 一键启动全部服务
docker compose -f deploy/docker-compose.prod.yml up -d --build

# 4. 初始化 MinIO bucket（先装 mc：brew install minio-mc 或下载官方二进制）
./deploy/init-minio.sh

# 5. 验证
curl http://localhost/api/v1/reviews -H 'X-User-ID: admin' -H 'X-Project-ID: bootstrap' -H 'X-Role: admin'
open http://localhost            # 前端
```

api 容器启动时会先执行 `alembic upgrade head` 自动建表/升级，迁移成功后才拉起 uvicorn，**无需手动初始化数据库**。

## 二、配置初始化

### 2.1 密钥与敏感配置（deploy/.env）

`docker compose` 会自动读取 `deploy/.env`（与 compose 文件同目录）中的变量。必填/常用项：

```bash
# 数据库（生产务必修改默认密码）
POSTGRES_PASSWORD=review

# MinIO 凭据
MINIO_ROOT_USER=review
MINIO_ROOT_PASSWORD=review-local-only

# 真实模型网关（留空 REVIEW_MODEL_API_KEY 则走本地空模型，评审不调用云端）
REVIEW_MODEL_BACKEND=real
REVIEW_MODEL_PROVIDER=minimax          # 或 openai_compatible
REVIEW_MODEL_BASE_URL=https://api.minimaxi.com/v1
REVIEW_MODEL_NAME=MiniMax-M3
REVIEW_MODEL_API_KEY=your-key-here
REVIEW_MODEL_TIMEOUT_S=60
REVIEW_MODEL_MAX_RETRIES=3
REVIEW_MODEL_CONCURRENCY=2
```

> 若走 `REVIEW_MODEL_PROVIDER=openai_compatible`，把 `REVIEW_MODEL_BASE_URL` / `REVIEW_MODEL_NAME` 换成你的兼容端点与模型名即可。

### 2.2 后端代码配置

后端所有配置项集中在 `backend/src/requirement_review/config.py`，通过 `REVIEW_` 前缀环境变量注入：

- `REVIEW_DATABASE_URL` — 数据库连接串（compose 已注入 `postgresql+asyncpg://...@postgres:5432/review`）
- `REVIEW_OBJECT_STORE_*` — MinIO 端点/bucket/凭据（compose 已注入）
- 其余模型相关变量见 2.1

**不建议**修改 `backend/.env` 的默认值，生产环境以 compose 注入的环境变量为准。

## 三、数据库初始化（alembic migrator）

数据库初始化统一走 **alembic 迁移**，不再依赖 init.sql 挂载。

### 全新部署：api 容器启动时自动迁移

`backend/Dockerfile` 已改为：镜像内置 `alembic.ini` + `alembic/` 迁移目录，CMD 先执行 `alembic upgrade head` 再拉起 uvicorn。compose 中 `REVIEW_DATABASE_URL` 已注入，`backend/alembic/env.py` 优先读取该环境变量作为迁移连接串，无需手动干预。

### 已有库升级：宿主机或容器内执行迁移

```bash
# 宿主机方式（需 backend 依赖 + psycopg2）
cd backend
pip install psycopg2-binary                # pyproject 未声明，迁移依赖它
REVIEW_DATABASE_URL=postgresql://review:review@localhost:5432/review .venv/bin/alembic upgrade head
```

### 迁移实现说明

- `backend/alembic/env.py` 新增 `resolve_database_url()`：优先使用 `REVIEW_DATABASE_URL` 环境变量（自动把 `+asyncpg` 归一化为同步协议），未设置时回退 `alembic.ini` 的 `sqlalchemy.url`；
- 当前仅一个版本 `0001`（`Base.metadata.create_all`），`deploy/init.sql` 与其等价，仅作为手动导入/对照的参考；
- 迁移需要同步 driver：镜像已安装 `psycopg2-binary`，宿主机升级需自行安装。

## 四、MinIO 初始化

当前代码未在运行时自动创建 bucket，需手动执行一次：

```bash
./deploy/init-minio.sh          # 默认连 http://localhost:9000，凭据同 2.1
```

> 代码层面 grep 未发现 `create_bucket`/对象存储调用点（配置中虽声明 `REVIEW_OBJECT_STORE_*`），即当前版本实际业务不强制依赖 MinIO；保留它以便后续版本接入。若不需要可直接从 compose 中注释掉 minio 服务与 api 的依赖。

## 五、常见问题

1. **前端访问 API 404**：前端请求的是相对路径 `/api/v1/*`，由 nginx 反代到 `api:8000`；确认 `web` 服务已启动且 compose 网络内 `api` 服务名可解析。
2. **npm ci 失败**：`frontend.Dockerfile` 要求 `frontend/package-lock.json` 存在且与 `package.json` 一致；锁定版本有变动时先本地 `npm install` 重新生成 lock 文件。
3. **npm ci 失败**：`frontend/Dockerfile` 要求 `frontend/package-lock.json` 存在且与 `package.json` 一致；锁定版本有变动时先本地 `npm install` 重新生成 lock 文件。
4. **构建上下文**：`web` 镜像 context 为 `frontend/`，已提供 `frontend/.dockerignore` 排除 `node_modules`/`dist` 等；nginx 配置通过 compose 挂载 `deploy/nginx.conf`，修改配置无需重建镜像。
5. **docker compose 未读取 deploy/.env**：确保 `.env` 与 `docker-compose.prod.yml` 同目录（即 `deploy/.env`），或显式 `--env-file deploy/.env`。
6. **API 请求头**：所有请求需携带 `X-User-ID` / `X-Project-ID` / `X-Role`（admin/reviewer/viewer），否则接口拒绝访问。
*（内容由AI生成，仅供参考）*
