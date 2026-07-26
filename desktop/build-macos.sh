#!/bin/bash
# ============================================================
# Enterprise KM Desktop — macOS 构建脚本
# 用法: bash build-macos.sh
# 前提: 已安装 Node.js 22+, Rust, Xcode Command Line Tools
# ============================================================
set -e

echo "=== Enterprise KM Desktop — macOS 构建 ==="

# 1. 检查环境
echo "[1/5] 检查环境..."
command -v node >/dev/null 2>&1 || { echo "❌ 需要 Node.js 22+"; exit 1; }
command -v cargo >/dev/null 2>&1 || { echo "❌ 需要 Rust (https://rustup.rs)"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ 需要 npm"; exit 1; }

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 22 ]; then
    echo "❌ Node.js 版本需要 >= 22，当前: $(node -v)"
    exit 1
fi
echo "  ✅ Node.js $(node -v)"
echo "  ✅ Rust $(rustc --version)"
echo "  ✅ npm $(npm -v)"

# 2. 安装 Tauri CLI
echo "[2/5] 安装 Tauri CLI..."
cargo install tauri-cli --version "^2" 2>/dev/null || echo "  (tauri-cli 已安装或跳过)"

# 3. 安装前端依赖 + 构建
echo "[3/5] 构建前端..."
cd desktop
npm install
npm run build
echo "  ✅ 前端构建完成 (out/)"

# 4. 下载预置二进制 (rclone + SurrealDB)
echo "[4/5] 准备预置二进制..."
mkdir -p src-tauri/scripts/bin

# rclone macOS arm64
if [ ! -f src-tauri/scripts/bin/rclone ]; then
    echo "  下载 rclone..."
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        RCLONE_URL="https://downloads.rclone.org/v1.70.0/rclone-v1.70.0-osx-arm64.zip"
    else
        RCLONE_URL="https://downloads.rclone.org/v1.70.0/rclone-v1.70.0-osx-amd64.zip"
    fi
    curl -L "$RCLONE_URL" -o /tmp/rclone.zip
    unzip -o /tmp/rclone.zip -d /tmp/rclone-extract
    cp /tmp/rclone-extract/rclone-*/rclone src-tauri/scripts/bin/rclone
    chmod +x src-tauri/scripts/bin/rclone
    rm -rf /tmp/rclone.zip /tmp/rclone-extract
    echo "  ✅ rclone 已下载"
fi

# SurrealDB macOS
if [ ! -f src-tauri/scripts/bin/surreal ]; then
    echo "  下载 SurrealDB..."
    ARCH=$(uname -m)
    if [ "$ARCH" = "arm64" ]; then
        SURREAL_URL="https://download.surrealdb.com/2.2.1/surreal-v2.2.1.darwin-arm64.tgz"
    else
        SURREAL_URL="https://download.surrealdb.com/2.2.1/surreal-v2.2.1.darwin-amd64.tgz"
    fi
    curl -L "$SURREAL_URL" -o /tmp/surreal.tgz
    tar xzf /tmp/surreal.tgz -C /tmp/
    cp /tmp/surreal src-tauri/scripts/bin/surreal
    chmod +x src-tauri/scripts/bin/surreal
    rm -f /tmp/surreal.tgz /tmp/surreal
    echo "  ✅ SurrealDB 已下载"
fi

# 5. Tauri 构建
echo "[5/5] Tauri 构建..."
cd src-tauri
cargo tauri build --target aarch64-apple-darwin 2>/dev/null || cargo tauri build --target x86_64-apple-darwin

echo ""
echo "=== 构建完成! ==="
echo "安装包位置: desktop/src-tauri/target/release/bundle/"
ls -la target/release/bundle/dmg/ 2>/dev/null || ls -la target/release/bundle/macos/ 2>/dev/null
