#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::path::PathBuf;

mod rclone;
mod services;
mod tray;
mod updater;
mod watcher;
mod notifications;
mod setup;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
        .plugin(tauri_plugin_notification::init())
        .manage(rclone::RcloneState {
            process: std::sync::Mutex::new(None),
            status: std::sync::Mutex::new(rclone::SyncStatus {
                running: false,
                directory: String::new(),
                last_sync: "从未同步".into(),
                file_count: 0,
            }),
            user_id: std::sync::Mutex::new(String::new()),
        })
        .manage(services::AppServices::new())
        .invoke_handler(tauri::generate_handler![
            rclone::start_sync,
            rclone::stop_sync,
            rclone::get_sync_status,
            rclone::set_sync_directory,
            rclone::set_user_id,
            rclone::pick_directory,
            services::init_environment,
            services::shutdown_services,
            services::get_service_status,
            run_initialization,
            check_initialization,
        ])
        .setup(|app| {
            tray::setup_tray(app.handle())?;

            let handle = app.handle().clone();

            // Check if first run — show setup wizard
            if setup::needs_initialization(&handle) {
                let _ = handle.emit("setup:needed", true);
            }

            // Start file watcher for sync directory
            let sync_dir = get_sync_dir(&handle);
            watcher::start_watcher(handle.clone(), sync_dir);

            // Start network monitor
            watcher::start_network_monitor(handle.clone());

            // Auto-init environment on startup
            let h = handle.clone();
            tauri::async_runtime::spawn(async move {
                let _ = services::init_environment(h).await;
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let handle = window.app_handle().clone();
                tauri::async_runtime::spawn(async move {
                    let _ = services::shutdown_services(handle).await;
                });
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn get_sync_dir(app: &tauri::AppHandle) -> PathBuf {
    if let Ok(dir) = app.path().app_data_dir() {
        dir.join("sync")
    } else {
        dirs_next::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("企业文档")
    }
}

// ─── Tauri Commands ───

#[tauri::command]
async fn run_initialization(app: tauri::AppHandle) -> Result<String, String> {
    setup::initialize(&app).await?;
    setup::mark_initialized(&app);
    Ok("ok".into())
}

#[tauri::command]
async fn check_initialization(app: tauri::AppHandle) -> Result<bool, String> {
    Ok(setup::needs_initialization(&app))
}
