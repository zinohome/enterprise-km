use serde::Serialize;
use std::process::Child;
use std::sync::Mutex;
use tauri::{Manager, State};

#[derive(Serialize, Clone)]
pub struct SyncStatus {
    pub running: bool,
    pub directory: String,
    pub last_sync: String,
    pub file_count: u32,
}

pub struct RcloneState {
    pub process: Mutex<Option<Child>>,
    pub status: Mutex<SyncStatus>,
    pub user_id: Mutex<String>,
}

/// Trigger a sync now (called by watcher)
pub async fn sync_now(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<RcloneState>();
    let mut proc = state.process.lock().map_err(|e| e.to_string())?;
    if proc.is_some() {
        return Ok(());
    }

    let dir = state.status.lock().unwrap().directory.clone();
    let user_id = state.user_id.lock().unwrap().clone();
    let remote_path = format!("enterprise-km-minio:enterprise-km/user_{}/", user_id);

    let child = std::process::Command::new("rclone")
        .args([
            "sync", &dir, &remote_path,
            "--verbose", "--exclude", ".DS_Store",
            "--exclude", "node_modules/**", "--exclude", ".git/**",
        ])
        .spawn()
        .map_err(|e| format!("Failed to start rclone: {}", e))?;

    *proc = Some(child);
    let mut status = state.status.lock().unwrap();
    status.running = true;
    Ok(())
}

#[tauri::command]
pub fn start_sync(state: State<RcloneState>) -> Result<SyncStatus, String> {
    let mut proc = state.process.lock().map_err(|e| e.to_string())?;
    if proc.is_some() {
        return Err("Sync already running".into());
    }

    let dir = state.status.lock().unwrap().directory.clone();
    let user_id = state.user_id.lock().unwrap().clone();
    let remote_path = format!("enterprise-km-minio:enterprise-km/user_{}/", user_id);

    let child = std::process::Command::new("rclone")
        .args([
            "sync", &dir, &remote_path,
            "--verbose", "--exclude", ".DS_Store",
            "--exclude", "node_modules/**", "--exclude", ".git/**",
        ])
        .spawn()
        .map_err(|e| format!("Failed to start rclone: {}", e))?;

    *proc = Some(child);
    let mut status = state.status.lock().unwrap();
    status.running = true;
    Ok(status.clone())
}

#[tauri::command]
pub fn stop_sync(state: State<RcloneState>) -> Result<SyncStatus, String> {
    let mut proc = state.process.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = proc.take() {
        child.kill().map_err(|e| format!("Failed to stop rclone: {}", e))?;
    }
    let mut status = state.status.lock().unwrap();
    status.running = false;
    Ok(status.clone())
}

#[tauri::command]
pub fn get_sync_status(state: State<RcloneState>) -> Result<SyncStatus, String> {
    state.status.lock().map(|s| s.clone()).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn set_sync_directory(dir: String, state: State<RcloneState>) -> Result<SyncStatus, String> {
    let mut status = state.status.lock().map_err(|e| e.to_string())?;
    status.directory = dir;
    Ok(status.clone())
}

#[tauri::command]
pub fn set_user_id(uid: String, state: State<RcloneState>) -> Result<(), String> {
    let mut user_id = state.user_id.lock().map_err(|e| e.to_string())?;
    *user_id = uid;
    Ok(())
}

#[tauri::command]
pub fn pick_directory() -> Result<String, String> {
    rfd::FileDialog::new()
        .pick_folder()
        .map(|p| p.to_string_lossy().to_string())
        .ok_or("No directory selected".into())
}
