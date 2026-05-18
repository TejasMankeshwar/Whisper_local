from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from recorder import AudioRecorder
from transcriber import Transcriber
from cleaner import Cleaner
from clipboard import paste_text

import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

def load_settings_file():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings file: {e}")
    return {}

def save_settings_file(settings_dict):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings_dict, f, indent=4)
    except Exception as e:
        print(f"Error saving settings file: {e}")

saved_settings = load_settings_file()
saved_api_key = saved_settings.get("api_key", "")
saved_auto_paste = saved_settings.get("auto_paste", True)

recorder = AudioRecorder()
transcriber = None  # Lazy loaded
cleaner = Cleaner(api_key=saved_api_key)

class Settings(BaseModel):
    api_key: str
    auto_paste: bool
    language: str

app_state = {
    "status": "idle", # idle, listening, processing, done, error
    "auto_paste": saved_auto_paste,
}

@app.get("/status")
def get_status():
    return {"status": app_state["status"]}

@app.post("/settings")
def update_settings(settings: Settings):
    cleaner.update_api_key(settings.api_key)
    app_state["auto_paste"] = settings.auto_paste
    save_settings_file({
        "api_key": settings.api_key,
        "auto_paste": settings.auto_paste,
        "language": settings.language
    })
    return {"status": "success"}

@app.post("/start")
def start_recording():
    if app_state["status"] == "listening":
        return {"status": "already_listening"}
    
    app_state["status"] = "listening"
    recorder.start_recording()
    return {"status": "success"}

@app.post("/stop")
def stop_recording():
    if app_state["status"] != "listening":
        return {"status": "not_listening"}
    
    app_state["status"] = "processing"
    
    # We do the processing synchronously for now so the HTTP request returns the final text
    # But it might be better to do in background task if it takes too long.
    # Since MVP needs to be simple, let's just do it here.
    audio_path = recorder.stop_recording()
    
    if not audio_path:
        app_state["status"] = "error"
        return {"error": "No audio recorded"}
    
    try:
        # Transcribe
        global transcriber
        if transcriber is None:
            print("Loading Whisper model (first time run, downloading if needed)...")
            transcriber = Transcriber(model_size="small.en")
            
        raw_text = transcriber.transcribe(audio_path)
        
        # Clean
        if raw_text:
            clean_text = cleaner.clean_text(raw_text)
        else:
            clean_text = ""
            
        # Paste
        if clean_text and app_state["auto_paste"]:
            paste_text(clean_text)
            
        app_state["status"] = "done"
        
        # Cleanup temp file
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        return {"text": clean_text}
        
    except Exception as e:
        app_state["status"] = "error"
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
