use tauri::Manager;

/// Send a native system notification
pub fn notify(app: &tauri::AppHandle, title: &str, body: &str) {
    // Use Tauri notification plugin
    let _ = app.emit("notification:show", serde_json::json!({
        "title": title,
        "body": body,
    }));
}

/// Notify that sync is complete
pub fn notify_sync_complete(app: &tauri::AppHandle, count: u32) {
    notify(app, "同步完成", &format!("{} 个文件已同步", count));
}

/// Notify that new knowledge is available
pub fn notify_new_knowledge(app: &tauri::AppHandle, title: &str) {
    notify(app, "新知识入库", &format!("{} 已加入企业知识库", title));
}

/// Notify that a document needs review
pub fn notify_review_needed(app: &tauri::AppHandle, count: u32) {
    notify(app, "待审核", &format!("{} 份文档等待审核", count));
}

/// Notify that the app is offline
pub fn notify_offline(app: &tauri::AppHandle) {
    notify(app, "离线模式", "网络已断开，恢复后将自动同步");
}

/// Notify that the app is back online
pub fn notify_online(app: &tauri::AppHandle) {
    notify(app, "已恢复连接", "正在同步离线期间的变更...");
}
