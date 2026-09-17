FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
# psycopg2-binary 供 alembic 迁移使用（应用运行时用 asyncpg）
RUN pip install --no-cache-dir . psycopg2-binary
# alembic 迁移文件
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000
# 启动前先执行数据库迁移，迁移成功后再拉起 API
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn requirement_review.api.app:app --host 0.0.0.0 --port 8000"]
