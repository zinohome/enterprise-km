# Phase 4: 桌面应用

**Feature Name:** 企业级知识管理平台 — 桌面应用
**Goal:** Tauri 桌面应用，集成 Next.js 前端、rclone 同步、系统托盘、开机自启
**Architecture:** Tauri 2 (Rust) + Next.js 15 (React) + rclone
**Global Constraints:** 跨平台 Win/Mac/Linux；rclone 内置管理；Token 持久化

---

## T4.1: Tauri 项目骨架 (已完成 Phase 1)

已有文件：`desktop/package.json`, `desktop/src-tauri/Cargo.toml`, `desktop/src-tauri/tauri.conf.json`, `desktop/src-tauri/src/main.rs`, `desktop/src/app/page.tsx`

## T4.2: 登录页面

### Files: `desktop/src/app/login/page.tsx`, `desktop/src/lib/api.ts`, `desktop/src/lib/auth.ts`

## T4.3: rclone 集成

### Files: `desktop/src-tauri/src/rclone.rs`, `desktop/src/components/SyncStatus.tsx`

## T4.4: 系统托盘与自启

### Files: `desktop/src-tauri/src/tray.rs`
