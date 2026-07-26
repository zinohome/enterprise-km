@echo off
REM ============================================================
REM Enterprise KM Desktop — Windows 构建脚本
REM 用法: build-windows.bat (以管理员身份运行)
REM 前提: 已安装 Node.js 22+, Rust, Visual Studio Build Tools
REM ============================================================
setlocal enabledelayedexpansion

echo === Enterprise KM Desktop — Windows 构建 ===

REM 1. 检查环境
echo [1/5] 检查环境...
where node >nul 2>&1 || (echo ❌ 需要 Node.js 22+ && exit /b 1)
where cargo >nul 2>&1 || (echo ❌ 需要 Rust (https://rustup.rs) && exit /b 1)
where npm >nul 2>&1 || (echo ❌ 需要 npm && exit /b 1)

for /f "tokens=1 delims=." %%a in ('node -v') do set NODE_MAJOR=%%a
echo   ✅ Node.js !NODE_MAJOR!
echo   ✅ Rust installed
echo   ✅ npm installed

REM 2. 安装 Tauri CLI
echo [2/5] 安装 Tauri CLI...
cargo install tauri-cli --version "^2" 2>nul || echo   (tauri-cli 已安装或跳过)

REM 3. 安装前端依赖 + 构建
echo [3/5] 构建前端...
cd desktop
call npm install
call npm run build
echo   ✅ 前端构建完成 (out/)

REM 4. 下载预置二进制 (rclone + SurrealDB)
echo [4/5] 准备预置二进制...
if not exist "src-tauri\scripts\bin" mkdir src-tauri\scripts\bin

REM rclone Windows amd64
if not exist "src-tauri\scripts\bin\rclone.exe" (
    echo   下载 rclone...
    curl -L "https://downloads.rclone.org/v1.70.0/rclone-v1.70.0-windows-amd64.zip" -o %TEMP%\rclone.zip
    powershell -Command "Expand-Archive -Path '%TEMP%\rclone.zip' -DestinationPath '%TEMP%\rclone-extract' -Force"
    copy /Y "%TEMP%\rclone-extract\rclone-*\rclone.exe" "src-tauri\scripts\bin\rclone.exe"
    del /Q %TEMP%\rclone.zip
    rmdir /S /Q %TEMP%\rclone-extract
    echo   ✅ rclone 已下载
)

REM SurrealDB Windows
if not exist "src-tauri\scripts\bin\surreal.exe" (
    echo   下载 SurrealDB...
    curl -L "https://download.surrealdb.com/2.2.1/surreal-v2.2.1.windows-amd64.exe" -o "src-tauri\scripts\bin\surreal.exe"
    echo   ✅ SurrealDB 已下载
)

REM 5. Tauri 构建
echo [5/5] Tauri 构建...
cd src-tauri
cargo tauri build

echo.
echo === 构建完成! ===
echo 安装包位置: desktop\src-tauri\target\release\bundle\
dir /B target\release\bundle\msi\ 2>nul
dir /B target\release\bundle\nsis\ 2>nul

endlocal
