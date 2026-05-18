// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use std::ffi::c_void;
use std::sync::{OnceLock, Mutex};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter};

// macOS CoreGraphics and CoreFoundation event tap FFI
type CGEventTapProxy = *mut c_void;
type CGEventRef = *mut c_void;

#[link(name = "CoreGraphics", kind = "framework")]
extern "C" {
    fn CGEventTapCreate(
        tap: u32,
        place: u32,
        options: u32,
        eventsOfInterest: u64,
        callback: extern "C" fn(proxy: CGEventTapProxy, type_: u32, event: CGEventRef, refcon: *mut c_void) -> CGEventRef,
        refcon: *mut c_void,
    ) -> *mut c_void;

    fn CGEventGetIntegerValueField(event: CGEventRef, field: u32) -> i64;
    fn CGEventTapEnable(tap: *mut c_void, enable: u8);
}

#[link(name = "CoreFoundation", kind = "framework")]
extern "C" {
    static kCFRunLoopDefaultMode: *const c_void;
    fn CFRunLoopGetCurrent() -> *mut c_void;
    fn CFRunLoopAddSource(rl: *mut c_void, source: *mut c_void, mode: *const c_void);
    fn CFRunLoopRun();
    fn CFMachPortCreateRunLoopSource(
        allocator: *mut c_void,
        port: *mut c_void,
        order: i64,
    ) -> *mut c_void;
}

struct ShortcutState {
    key_pressed: bool,
    last_press_time: Option<Instant>,
    app_handle: Option<AppHandle>,
    is_listening: bool,
}

static STATE: OnceLock<Mutex<ShortcutState>> = OnceLock::new();

#[tauri::command]
fn sync_listening_state(listening: bool) {
    if let Some(state_mutex) = STATE.get() {
        if let Ok(mut state) = state_mutex.lock() {
            state.is_listening = listening;
        }
    }
}

extern "C" fn event_tap_callback(
    _proxy: CGEventTapProxy,
    _type: u32,
    event: CGEventRef,
    _refcon: *mut c_void,
) -> CGEventRef {
    // kCGKeyboardEventKeycode = 9
    let keycode = unsafe { CGEventGetIntegerValueField(event, 9) };
    if keycode == 58 || keycode == 61 { // Left Option (58) or Right Option (61) on macOS
        if let Some(state_mutex) = STATE.get() {
            if let Ok(mut state) = state_mutex.lock() {
                state.key_pressed = !state.key_pressed;
                if state.key_pressed {
                    // This is an Option Key Press event (ignoring key release event)
                    let now = Instant::now();
                    let mut is_double = false;

                    if let Some(last) = state.last_press_time {
                        if now.duration_since(last) < Duration::from_millis(400) {
                            is_double = true;
                        }
                    }

                    state.last_press_time = Some(now);

                    if let Some(app) = &state.app_handle {
                        if state.is_listening {
                            // If currently recording, a SINGLE press stops it!
                            let _ = app.emit("fn-shortcut", "stop");
                        } else if is_double {
                            // If idle, a DOUBLE press starts recording!
                            let _ = app.emit("fn-shortcut", "start");
                        }
                    }
                }
            }
        }
    }
    event
}

fn start_global_shortcut_listener(app_handle: AppHandle) {
    // Store app handle in the static state
    let _ = STATE.get_or_init(|| Mutex::new(ShortcutState {
        key_pressed: false,
        last_press_time: None,
        app_handle: Some(app_handle),
        is_listening: false,
    }));

    // Spawn background thread to run the macOS Event Tap loop
    std::thread::spawn(move || {
        unsafe {
            // Event type mask for FlagsChanged (kCGEventFlagsChanged = 12, mask = 1 << 12)
            let mask = 1 << 12;
            let tap = CGEventTapCreate(
                0, // kCGSessionEventTap
                0, // kCGHeadInsertEventTap
                0, // kCGEventTapOptionListenOnly
                mask,
                event_tap_callback,
                std::ptr::null_mut(),
            );

            if tap.is_null() {
                println!("Warning: Failed to create CGEventTap. Accessibility or Input Monitoring permissions might be required.");
                return;
            }

            let source = CFMachPortCreateRunLoopSource(std::ptr::null_mut(), tap, 0);
            if source.is_null() {
                println!("Warning: Failed to create Event Loop Source.");
                return;
            }

            let rl = CFRunLoopGetCurrent();
            CFRunLoopAddSource(rl, source, kCFRunLoopDefaultMode);

            // Enable event tap
            CGEventTapEnable(tap, 1);

            println!("macOS global Fn/Globe key event tap successfully initialized!");
            CFRunLoopRun();
        }
    });
}

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_global_shortcut::Builder::new().build())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            start_global_shortcut_listener(app.handle().clone());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet, sync_listening_state])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
