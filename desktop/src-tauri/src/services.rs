use std::process::{Child, Command};
use std::sync::Mutex;
use tauri::Manager;

pub struct AppServices {
    surrealdb: Mutex<Option<Child>>,
    open_notebook: Mutex<Option<Child>>,
    rclone: Mutex<Option<Child>>,
    initialized: Mutex<bool>,
}

impl AppServices {
    pub fn new() -> Self {
        Self {
            surrealdb: Mutex::new(None),
            open_notebook: Mutex::new(None),
            rclone: Mutex::new(None),
            initialized: Mutex::new(false),
        }
    }
}

#[tauri::command]
pub async fn init_environment(app: tauri::AppHandle) -> Result<String, String> {
    let services = app.state::<AppServices>();
    let mut initialized = services.initialized.lock().map_err(|e| e.to_string())?;
    if *initialized {
        return Ok("already_initialized".into());
    }

    let home = dirs_next::home_dir().ok_or("Cannot find home dir")?;
    let app_dir = home.join(".enterprise-km");
    let bin_dir = app_dir.join("bin");
    let data_dir = app_dir.join("data");
    let venv_dir = app_dir.join("venv");

    // Run setup script if needed
    let setup_script = app
        .path()
        .resource_dir()
        .map_err(|e| e.to_string())?
        .join("scripts/setup.sh");

    if setup_script.exists() {
        let status = Command::new("bash")
            .arg(&setup_script)
            .status()
            .map_err(|e| format!("Setup failed: {}", e))?;
        if !status.success() {
            return Err("Setup script failed".into());
        }
    }

    // Start SurrealDB
    let surreal_bin = bin_dir.join("surreal");
    if surreal_bin.exists() {
        let surreal_data = data_dir.join("surrealdb");
        std::fs::create_dir_all(&surreal_data).ok();

        let child = Command::new(&surreal_bin)
            .args([
                "start",
                "--log",
                "info",
                "--user",
                "root",
                "--pass",
                "root",
                &format!("rocksdb:{}", surreal_data.join("db").display()),
                "--bind",
                "127.0.0.1:8001",
            ])
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to start SurrealDB: {}", e))?;

        let mut db = services.surrealdb.lock().map_err(|e| e.to_string())?;
        *db = Some(child);
    }

    // Start Open Notebook
    let python_bin = if cfg!(target_os = "windows") {
        venv_dir.join("Scripts/python.exe")
    } else {
        venv_dir.join("bin/python3")
    };

    if python_bin.exists() {
        let child = Command::new(&python_bin)
            .args([
                "-m",
                "uvicorn",
                "api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "5055",
            ])
            .env("SURREAL_URL", "ws://127.0.0.1:8001/rpc")
            .env("SURREAL_USER", "root")
            .env("SURREAL_PASSWORD", "root")
            .env("SURREAL_NAMESPACE", "open_notebook")
            .env("SURREAL_DATABASE", "open_notebook")
            .env("OPEN_NOTEBOOK_ENCRYPTION_KEY", "local_encryption_key_2024")
            .current_dir(&venv_dir)
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to start Open Notebook: {}", e))?;

        let mut on = services.open_notebook.lock().map_err(|e| e.to_string())?;
        *on = Some(child);
    }

    *initialized = true;
    Ok("initialized".into())
}

#[tauri::command]
pub async fn shutdown_services(app: tauri::AppHandle) -> Result<String, String> {
    let services = app.state::<AppServices>();

    if let Ok(mut rclone) = services.rclone.lock() {
        if let Some(mut child) = rclone.take() {
            let _ = child.kill();
        }
    }

    if let Ok(mut on) = services.open_notebook.lock() {
        if let Some(mut child) = on.take() {
            let _ = child.kill();
        }
    }

    if let Ok(mut db) = services.surrealdb.lock() {
        if let Some(mut child) = db.take() {
            let _ = child.kill();
        }
    }

    Ok("shutdown".into())
}

#[tauri::command]
pub async fn get_service_status(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let services = app.state::<AppServices>();
    let initialized = services.initialized.lock().map_err(|e| e.to_string())?;

    Ok(serde_json::json!({
        "initialized": *initialized,
        "open_notebook": "http://localhost:5055",
        "surrealdb": "ws://localhost:8001/rpc",
    }))
}
