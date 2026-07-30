use tauri::Emitter;

#[tauri::command]
pub fn notify(app: tauri::AppHandle, title: String, body: String) -> Result<(), String> {
    let _ = app.emit("notification:show", serde_json::json!({
        "title": title,
        "body": body,
    }));
    Ok(())
}

pub fn notify_sync_complete(app: &tauri::AppHandle, file_count: u32) {
    let _ = app.emit("notification:show", serde_json::json!({
        "title": "同步完成",
        "body": format!("已同步 {} 个文件", file_count),
    }));
}

pub fn notify_error(app: &tauri::AppHandle, message: &str) {
    let _ = app.emit("notification:show", serde_json::json!({
        "title": "错误",
        "body": message,
    }));
}
