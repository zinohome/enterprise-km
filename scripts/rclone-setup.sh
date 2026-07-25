#!/bin/bash
# rclone MinIO 配置脚本
# 用法: bash scripts/rclone-setup.sh

RCLONE_REMOTE="enterprise-km-minio"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://localhost:9000}"
MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-minioadmin}"
MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-minioadmin123}"
MINIO_BUCKET="${MINIO_BUCKET:-enterprise-km}"

echo "Configuring rclone remote: $RCLONE_REMOTE"

rclone config create "$RCLONE_REMOTE" s3 \
    provider=Minio \
    endpoint="$MINIO_ENDPOINT" \
    access_key_id="$MINIO_ACCESS_KEY" \
    secret_access_key="$MINIO_SECRET_KEY" \
    --non-interactive 2>&1

echo "Testing connection..."
rclone ls "$RCLONE_REMOTE:$MINIO_BUCKET" 2>&1

echo "Done! Remote '$RCLONE_REMOTE' configured."
echo ""
echo "Usage:"
echo "  rclone sync /local/path $RCLONE_REMOTE:$MINIO_BUCKET/user_001/"
echo "  rclone ls $RCLONE_REMOTE:$MINIO_BUCKET/"
