use tauri::Emitter;

#[tauri::command]
pub async fn check_update(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let _ = app.emit("update:checking", true);

    Ok(serde_json::json!({
        "available": false,
        "version": env!("CARGO_PKG_VERSION"),
        "message": "已是最新版本",
    }))
}

#[tauri::command]
pub fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}
