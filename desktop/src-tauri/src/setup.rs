use std::path::PathBuf;
use std::process::Command;
use tauri::Manager;

/// One-click initialization: set up rclone, SurrealDB, Open Notebook
pub async fn initialize(app: &tauri::AppHandle) -> Result<(), String> {
    let app_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("Failed to get app dir: {}", e))?;

    let scripts_dir = app_dir.join("scripts");
    let bin_dir = scripts_dir.join("bin");

    // Step 1: Copy pre-bundled binaries
    let _ = app.emit("setup:progress", serde_json::json!({
        "step": 1,
        "total": 4,
        "message": "正在安装 rclone..."
    }));

    let rclone_src = bin_dir.join("rclone");
    let rclone_dst = app_dir.join("bin").join("rclone");
    if rclone_src.exists() {
        std::fs::create_dir_all(rclone_dst.parent().unwrap())
            .map_err(|e| format!("Failed to create bin dir: {}", e))?;
        std::fs::copy(&rclone_src, &rclone_dst)
            .map_err(|e| format!("Failed to copy rclone: {}", e))?;
        #[cfg(unix)]
        {
            let _ = Command::new("chmod")
                .args(["+x", rclone_dst.to_str().unwrap()])
                .output();
        }
    }

    // Step 2: Copy SurrealDB binary
    let _ = app.emit("setup:progress", serde_json::json!({
        "step": 2,
        "total": 4,
        "message": "正在安装 SurrealDB..."
    }));

    let surreal_src = bin_dir.join("surreal");
    let surreal_dst = app_dir.join("bin").join("surreal");
    if surreal_src.exists() {
        std::fs::copy(&surreal_src, &surreal_dst)
            .map_err(|e| format!("Failed to copy surreal: {}", e))?;
        #[cfg(unix)]
        {
            let _ = Command::new("chmod")
                .args(["+x", surreal_dst.to_str().unwrap()])
                .output();
        }
    }

    // Step 3: Install Open Notebook (online)
    let _ = app.emit("setup:progress", serde_json::json!({
        "step": 3,
        "total": 4,
        "message": "正在安装 Open Notebook (需要网络)..."
    }));

    let on_dir = app_dir.join("open-notebook");
    if !on_dir.join("api").exists() {
        let output = Command::new("pip3")
            .args(["install", "--target", on_dir.join("venv").to_str().unwrap(), "git+https://github.com/lfnovo/open-notebook.git"])
            .output()
            .map_err(|e| format!("pip install failed: {}", e))?;
        if !output.status.success() {
            return Err(format!(
                "Open Notebook install failed: {}",
                String::from_utf8_lossy(&output.stderr)
            ));
        }
    }

    // Step 4: Start local services
    let _ = app.emit("setup:progress", serde_json::json!({
        "step": 4,
        "total": 4,
        "message": "正在启动本地服务..."
    }));

    crate::services::start_local_services(app, &app_dir).await?;

    let _ = app.emit("setup:complete", serde_json::json!({
        "message": "初始化完成！"
    }));

    Ok(())
}

/// Check if initialization is needed
pub fn needs_initialization(app: &tauri::AppHandle) -> bool {
    let app_dir = match app.path().app_data_dir() {
        Ok(d) => d,
        Err(_) => return true,
    };
    let marker = app_dir.join(".initialized");
    !marker.exists()
}

/// Mark initialization as complete
pub fn mark_initialized(app: &tauri::AppHandle) {
    if let Ok(app_dir) = app.path().app_data_dir() {
        let marker = app_dir.join(".initialized");
        let _ = std::fs::write(marker, "1");
    }
}
