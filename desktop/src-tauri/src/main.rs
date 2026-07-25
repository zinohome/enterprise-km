#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

mod rclone;
mod services;
mod tray;
mod updater;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_autostart::init(
            tauri_plugin_autostart::MacosLauncher::LaunchAgent,
            Some(vec!["--minimized"]),
        ))
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
        ])
        .setup(|app| {
            tray::setup_tray(app.handle())?;
            // Auto-init environment on startup
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                let _ = services::init_environment(handle).await;
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
