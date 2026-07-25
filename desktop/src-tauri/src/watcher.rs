use notify::{Event, EventKind, RecursiveMode, Watcher, Config};
use std::path::PathBuf;
use std::sync::mpsc;
use tauri::Manager;
use tokio::time::{sleep, Duration};

/// Start file system watcher for the sync directory.
/// Detects new/modified/deleted files and triggers rclone sync.
pub fn start_watcher(app: tauri::AppHandle, sync_dir: PathBuf) {
    std::thread::spawn(move || {
        let (tx, rx) = mpsc::channel();
        let mut watcher = match notify::recommended_watcher(move |res| {
            if let Ok(event) = res {
                let _ = tx.send(event);
            }
        }) {
            Ok(w) => w,
            Err(e) => {
                eprintln!("Failed to create watcher: {}", e);
                return;
            }
        };

        if let Err(e) = watcher.watch(&sync_dir, RecursiveMode::Recursive) {
            eprintln!("Failed to watch directory: {}", e);
            return;
        }

        // Debounce: collect events for 500ms before triggering sync
        let mut pending = false;
        loop {
            match rx.recv_timeout(Duration::from_millis(500)) {
                Ok(event) => {
                    if is_relevant_event(&event) {
                        pending = true;
                    }
                }
                Err(mpsc::RecvTimeoutError::Timeout) => {
                    if pending {
                        pending = false;
                        let app = app.clone();
                        let dir = sync_dir.clone();
                        tokio::spawn(async move {
                            // Trigger rclone sync
                            if let Err(e) = crate::rclone::sync_now(&app).await {
                                eprintln!("Sync failed: {}", e);
                            }
                            // Notify frontend
                            let _ = app.emit("sync:triggered", dir.to_string_lossy().to_string());
                        });
                    }
                }
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
            }
        }
    });
}

fn is_relevant_event(event: &Event) -> bool {
    matches!(
        event.kind,
        EventKind::Create(_) | EventKind::Modify(_) | EventKind::Remove(_)
    )
}

/// Check if network is available
pub async fn is_online() -> bool {
    // Try to reach a known endpoint
    if let Ok(resp) = reqwest::get("https://www.baidu.com").await {
        resp.status().is_success()
    } else {
        false
    }
}

/// Monitor network status changes
pub fn start_network_monitor(app: tauri::AppHandle) {
    std::thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        let mut was_online = true;

        loop {
            let online = rt.block_on(is_online());
            if online != was_online {
                was_online = online;
                let _ = app.emit("network:changed", online);
            }
            std::thread::sleep(Duration::from_secs(10));
        }
    });
}
