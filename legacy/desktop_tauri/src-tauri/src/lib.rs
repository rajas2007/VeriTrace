// Tauri 2 Desktop Shell Library for VeriTrace
// Manages application lifecycle and local Python supervisor execution

pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // Milestone 0 will initialize the Python supervisor and dynamic port handshake here
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running VeriTrace desktop application");
}
