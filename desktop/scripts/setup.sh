#!/bin/bash
# 企业知识管理桌面应用 — 环境初始化脚本
# rclone + SurrealDB: 优先使用安装包预置二进制, 回退在线下载
# Open Notebook: 在线 pip install (依赖复杂, 不预置)
set -e

APP_DIR="$HOME/.enterprise-km"
BIN_DIR="$APP_DIR/bin"
DATA_DIR="$APP_DIR/data"
VENV_DIR="$APP_DIR/venv"
NOTEBOOK_DIR="$APP_DIR/open-notebook"

RESOURCES_DIR="$(dirname "$0")/.."
BUNDLED_BIN="$RESOURCES_DIR/bin"

echo "=== 企业知识管理 — 环境初始化 ==="

mkdir -p "$BIN_DIR" "$DATA_DIR"

# ─── 1. rclone ───
if [ ! -f "$BIN_DIR/rclone" ]; then
    if [ -f "$BUNDLED_BIN/rclone" ]; then
        echo "[离线] 安装 rclone (预置)..."
        cp "$BUNDLED_BIN/rclone" "$BIN_DIR/rclone"
        chmod +x "$BIN_DIR/rclone"
    else
        echo "[在线] 下载 rclone..."
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
        ARCH=$(uname -m)
        [ "$ARCH" = "x86_64" ] && ARCH="amd64"
        [ "$ARCH" = "aarch64" ] && ARCH="arm64"
        curl -sL "https://downloads.rclone.org/rclone-current-${OS}-${ARCH}.zip" -o /tmp/rclone.zip
        unzip -qo /tmp/rclone.zip -d /tmp/rclone_extract
        cp /tmp/rclone_extract/rclone-*/rclone "$BIN_DIR/rclone"
        chmod +x "$BIN_DIR/rclone"
        rm -rf /tmp/rclone.zip /tmp/rclone_extract
    fi
    echo "  ✓ rclone"
fi

# ─── 2. SurrealDB ───
if [ ! -f "$BIN_DIR/surreal" ]; then
    if [ -f "$BUNDLED_BIN/surreal" ]; then
        echo "[离线] 安装 SurrealDB (预置)..."
        cp "$BUNDLED_BIN/surreal" "$BIN_DIR/surreal"
        chmod +x "$BIN_DIR/surreal"
    else
        echo "[在线] 下载 SurrealDB..."
        OS=$(uname -s | tr '[:upper:]' '[:lower:]')
        ARCH=$(uname -m)
        [ "$ARCH" = "x86_64" ] && ARCH="amd64"
        [ "$ARCH" = "aarch64" ] && ARCH="arm64"
        curl -sL "https://github.com/surrealdb/surrealdb/releases/download/v2.2.2/surreal-v2.2.2.${OS}-${ARCH}.tgz" -o /tmp/surreal.tgz
        tar xzf /tmp/surreal.tgz -C "$BIN_DIR"
        chmod +x "$BIN_DIR/surreal"
        rm -f /tmp/surreal.tgz
    fi
    echo "  ✓ SurrealDB"
fi

# ─── 3. Open Notebook (在线 pip install) ───
if [ ! -d "$VENV_DIR" ]; then
    echo "[在线] 安装 Open Notebook (首次启动, 约2-3分钟)..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet --upgrade pip
    "$VENV_DIR/bin/pip" install --quiet "git+https://github.com/lfnovo/open-notebook.git" 2>&1 | tail -3
    echo "  ✓ Open Notebook"
fi

# ─── 4. rclone 配置 ───
if [ ! -f "$APP_DIR/rclone.conf" ]; then
    cat > "$APP_DIR/rclone.conf" << 'RCLONECONF'
[enterprise-km]
type = s3
provider = Minio
endpoint = http://192.168.66.40:9000
access_key_id = minioadmin
secret_access_key = minioadmin
RCLONECONF
    echo "  ✓ rclone 配置"
fi

echo "=== 环境初始化完成 ==="
