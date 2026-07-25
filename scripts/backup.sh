#!/bin/bash
# 企业知识管理平台 — 自动备份脚本
# 用法: bash /opt/enterprise-km/scripts/backup.sh
# 建议 crontab: 0 2 * * * bash /opt/enterprise-km/scripts/backup.sh

set -e
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/enterprise-km}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# 1. SurrealDB 导出
echo "  Backing up SurrealDB..."
SURREAL_URL="${SURREAL_URL:-ws://127.0.0.1:8000/rpc}"
SURREAL_USER="${SURREAL_USER:-root}"
SURREAL_PASS="${SURREAL_PASS:-root}"
SURREAL_NS="${SURREAL_NS:-open_notebook}"
SURREAL_DB="${SURREAL_DB:-open_notebook}"

# Use Python surrealdb client for export
python3 -c "
import asyncio, json
from surrealdb import AsyncSurreal

async def export():
    db = AsyncSurreal('$SURREAL_URL')
    await db.signin({'username': '$SURREAL_USER', 'password': '$SURREAL_PASS'})
    await db.use('$SURREAL_NS', '$SURREAL_DB')
    
    tables = ['user', 'team', 'team_member', 'knowledge_category', 'approval', 'audit_log']
    data = {}
    for table in tables:
        try:
            r = await db.query(f'SELECT * FROM {table};')
            data[table] = r
        except:
            data[table] = []
    
    with open('$BACKUP_DIR/surrealdb_$TIMESTAMP.json', 'w') as f:
        json.dump(data, f, default=str, indent=2)
    
    await db.close()

asyncio.run(export())
" 2>/dev/null || echo "  WARNING: SurrealDB backup failed (surreal CLI not available)"

# 2. MinIO 数据同步
echo "  Backing up MinIO..."
if rclone listremotes 2>/dev/null | grep -q enterprise-km-minio; then
    rclone sync enterprise-km-minio:enterprise-km "$BACKUP_DIR/minio_$TIMESTAMP/" --verbose 2>&1 | tail -3
else
    echo "  WARNING: rclone not configured, skipping MinIO backup"
fi

# 3. 清理旧备份
echo "  Cleaning backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
find "$BACKUP_DIR" -type d -empty -delete 2>/dev/null || true

echo "[$(date)] Backup complete: $BACKUP_DIR"
ls -lh "$BACKUP_DIR" | tail -5
