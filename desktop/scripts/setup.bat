@echo off
REM 企业知识管理桌面应用 — Windows 环境初始化脚本
REM 支持离线(预置资源) + 在线(网络下载)双模式
setlocal enabledelayedexpansion

set APP_DIR=%USERPROFILE%\.enterprise-km
set BIN_DIR=%APP_DIR%\bin
set DATA_DIR=%APP_DIR%\data
set VENV_DIR=%APP_DIR%\venv

REM 安装包内预置资源路径
set RESOURCES_DIR=%~dp0..
set BUNDLED_BIN=%RESOURCES_DIR%\bin
set BUNDLED_VENV=%RESOURCES_DIR%\venv

echo === 企业知识管理 — 环境初始化 ===
if exist "%BUNDLED_BIN%" (
    echo 模式: 离线安装(预置资源^)
) else (
    echo 模式: 在线安装(网络下载^)
)

mkdir "%BIN_DIR%" 2>nul
mkdir "%DATA_DIR%" 2>nul

REM ─── 1. rclone ───
if not exist "%BIN_DIR%\rclone.exe" (
    if exist "%BUNDLED_BIN%\rclone.exe" (
        echo [离线] 安装 rclone...
        copy "%BUNDLED_BIN%\rclone.exe" "%BIN_DIR%\rclone.exe"
    ) else (
        echo [在线] 下载 rclone...
        powershell -Command "Invoke-WebRequest -Uri 'https://downloads.rclone.org/rclone-current-windows-amd64.zip' -OutFile '%TEMP%\rclone.zip'"
        powershell -Command "Expand-Archive -Path '%TEMP%\rclone.zip' -DestinationPath '%TEMP%\rclone_extract' -Force"
        for /d %%d in (%TEMP%\rclone_extract\rclone-*) do copy "%%d\rclone.exe" "%BIN_DIR%\rclone.exe"
        del /q %TEMP%\rclone.zip
        rmdir /s /q %TEMP%\rclone_extract
    )
    echo   rclone 安装完成
)

REM ─── 2. SurrealDB ───
if not exist "%BIN_DIR%\surreal.exe" (
    if exist "%BUNDLED_BIN%\surreal.exe" (
        echo [离线] 安装 SurrealDB...
        copy "%BUNDLED_BIN%\surreal.exe" "%BIN_DIR%\surreal.exe"
    ) else (
        echo [在线] 下载 SurrealDB...
        powershell -Command "Invoke-WebRequest -Uri 'https://github.com/surrealdb/surrealdb/releases/download/v2.2.2/surreal-v2.2.2.windows-amd64.exe' -OutFile '%BIN_DIR%\surreal.exe'"
    )
    echo   SurrealDB 安装完成
)

REM ─── 3. Open Notebook ───
if not exist "%VENV_DIR%\Scripts\python.exe" (
    if exist "%BUNDLED_VENV%" (
        echo [离线] 安装 Open Notebook (复制预置 venv^)...
        xcopy /E /I /Q "%BUNDLED_VENV%" "%VENV_DIR%"
    ) else (
        echo [在线] 安装 Open Notebook (pip install^)...
        python -m venv "%VENV_DIR%"
        "%VENV_DIR%\Scripts\pip" install --quiet --upgrade pip
        "%VENV_DIR%\Scripts\pip" install --quiet open-notebook
    )
    echo   Open Notebook 安装完成
)

REM ─── 4. rclone 配置 ───
if not exist "%APP_DIR%\rclone.conf" (
    (
        echo [enterprise-km]
        echo type = s3
        echo provider = Minio
        echo endpoint = http://192.168.66.40:9000
        echo access_key_id = minioadmin
        echo secret_access_key = minioadmin
    ) > "%APP_DIR%\rclone.conf"
    echo   rclone 配置完成
)

echo === 环境初始化完成 ===
