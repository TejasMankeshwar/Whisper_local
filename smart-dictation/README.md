# Smart Dictation Assistant (Wispr Flow Clone)

A macOS desktop application that converts live speech into polished text by removing filler words, correcting self-edits, and automatically typing the cleaned text into any active application.

## Features
- **Global Hotkey (Option + Space)**: Press to start recording, press again to stop.
- **AI Cleanup**: Powered by Google Gemini 2.5 Flash API to perfectly clean up speech.
- **Auto Paste**: Directly types into any active application on your Mac using `Cmd+V`.
- **Private & Local Audio**: Audio is processed locally using `faster-whisper`.
- **Beautiful Dark UI**: Minimalist and sleek settings menu.

## Architecture
- **Frontend**: HTML/CSS/JS wrapped in Tauri for a fast, native-feeling macOS App.
- **Backend**: Python HTTP server (FastAPI) handling local AI generation and clipboard manipulation.

## Setup Instructions

### 1. Python Environment Setup
Navigate to the `smart-dictation` directory and set up the Python environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Tauri App Setup
Ensure you have the latest Rust toolchain (`rustup update`) and Node.js.
```bash
npm install
```

### 3. Running for Development
You need to run the Python backend, then launch the Tauri app.
In Terminal 1 (Python Backend):
```bash
source venv/bin/activate
python python/main.py
```
In Terminal 2 (Tauri UI):
```bash
npm run tauri dev
```

### 4. Building for Release (DMG)
To build a macOS application (`.app`) and a disk image (`.dmg`):
```bash
npm run tauri build
```
Note: The Python backend currently needs to be started manually. In a fully polished production release, the Python environment would be bundled using `PyInstaller` and spawned as a Tauri Sidecar. For this MVP, Tauri spawns the local Python script automatically, but assumes `venv` is configured on the host machine.

## Privacy & Permissions
- **Microphone**: Needed to capture your voice.
- **Accessibility**: Needed to simulate the `Cmd+V` keystroke into the active application.

---
*Built with Antigravity & Tauri.*
