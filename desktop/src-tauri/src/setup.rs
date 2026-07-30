use std::path::PathBuf;
use std::process::Command;
use tauri::{Emitter, Manager};

pub fn needs_initialization(app: &tauri::AppHandle) -> bool {
    let app_dir = get_app_dir(app);
    let marker = app_dir.join(".initialized");
    !marker.exists()
}

pub fn mark_initialized(app: &tauri::AppHandle) {
    let app_dir = get_app_dir(app);
    std::fs::create_dir_all(&app_dir).ok();
    std::fs::write(app_dir.join(".initialized"), "done").ok();
}

pub async fn initialize(app: &tauri::AppHandle) -> Result<(), String> {
    let app_dir = get_app_dir(app);
    let bin_dir = app_dir.join("bin");
    let data_dir = app_dir.join("data");
    let venv_dir = app_dir.join("venv");

    std::fs::create_dir_all(&bin_dir).map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?;

    let _ = app.emit("setup:progress", serde_json::json!({"step": "rclone", "status": "checking"}));
    let rclone_bin = if cfg!(target_os = "windows") {
        bin_dir.join("rclone.exe")
    } else {
        bin_dir.join("rclone")
    };
    if !rclone_bin.exists() {
        let _ = app.emit("setup:progress", serde_json::json!({"step": "rclone", "status": "missing"}));
    } else {
        let _ = app.emit("setup:progress", serde_json::json!({"step": "rclone", "status": "ok"}));
    }

    let _ = app.emit("setup:progress", serde_json::json!({"step": "surrealdb", "status": "checking"}));
    let surreal_bin = if cfg!(target_os = "windows") {
        bin_dir.join("surreal.exe")
    } else {
        bin_dir.join("surreal")
    };
    if !surreal_bin.exists() {
        let _ = app.emit("setup:progress", serde_json::json!({"step": "surrealdb", "status": "missing"}));
    } else {
        let _ = app.emit("setup:progress", serde_json::json!({"step": "surrealdb", "status": "ok"}));
    }

    let _ = app.emit("setup:progress", serde_json::json!({"step": "python", "status": "checking"}));
    let python_bin = if cfg!(target_os = "windows") {
        venv_dir.join("Scripts/python.exe")
    } else {
        venv_dir.join("bin/python3")
    };
    if !python_bin.exists() {
        let _ = app.emit("setup:progress", serde_json::json!({"step": "python", "status": "creating_venv"}));
        let system_python = if cfg!(target_os = "windows") { "python" } else { "python3" };
        let status = Command::new(system_python)
            .args(["-m", "venv", venv_dir.to_str().unwrap_or(".")])
            .status()
            .map_err(|e| format!("Failed to create venv: {}", e))?;
        if !status.success() {
            return Err("Failed to create Python virtual environment".into());
        }
        let pip_bin = if cfg!(target_os = "windows") {
            venv_dir.join("Scripts/pip.exe")
        } else {
            venv_dir.join("bin/pip")
        };
        let status = Command::new(&pip_bin)
            .args(["install", "open-notebook"])
            .status()
            .map_err(|e| format!("Failed to install open-notebook: {}", e))?;
        if !status.success() {
            return Err("Failed to install open-notebook".into());
        }
    }
    let _ = app.emit("setup:progress", serde_json::json!({"step": "python", "status": "ok"}));

    let _ = app.emit("setup:progress", serde_json::json!({"step": "services", "status": "starting"}));
    crate::services::start_local_services(app, &app_dir).await?;
    let _ = app.emit("setup:progress", serde_json::json!({"step": "services", "status": "ok"}));

    let _ = app.emit("setup:complete", serde_json::json!({"status": "ok"}));
    Ok(())
}

fn get_app_dir(app: &tauri::AppHandle) -> PathBuf {
    if let Ok(dir) = app.path().app_data_dir() {
        dir
    } else {
        dirs_next::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".enterprise-km")
    }
}
