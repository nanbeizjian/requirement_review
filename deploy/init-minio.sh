#!/usr/bin/env bash
# 初始化 MinIO bucket（requirement-review）
# 依赖: mc (MinIO Client)，需自行安装：brew install minio-mc 或下载官方二进制
# 用法: ./init-minio.sh
# 可选环境变量: MINIO_ENDPOINT / MINIO_ROOT_USER / MINIO_ROOT_PASSWORD / REVIEW_OBJECT_STORE_BUCKET
set -euo pipefail

MC=${MC:-mc}
ENDPOINT=${MINIO_ENDPOINT:-http://localhost:9000}
ACCESS_KEY=${MINIO_ROOT_USER:-review}
SECRET_KEY=${MINIO_ROOT_PASSWORD:-review-local-only}
BUCKET=${REVIEW_OBJECT_STORE_BUCKET:-requirement-review}
ALIAS=${MINIO_ALIAS:-local}

"$MC" alias set "$ALIAS" "$ENDPOINT" "$ACCESS_KEY" "$SECRET_KEY" >/dev/null
"$MC" mb --ignore-existing "$ALIAS/$BUCKET"
echo "[ok] bucket '$BUCKET' ready on $ENDPOINT"
