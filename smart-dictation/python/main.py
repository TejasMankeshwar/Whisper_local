from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from recorder import AudioRecorder
from transcriber import Transcriber
from cleaner import Cleaner
from clipboard import paste_text

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

recorder = AudioRecorder()
transcriber = Transcriber(model_size="small.en")
cleaner = Cleaner()

class Settings(BaseModel):
    api_key: str
    auto_paste: bool
    language: str

app_state = {
    "status": "idle", # idle, listening, processing, done, error
    "auto_paste": True,
}

@app.get("/status")
def get_status():
    return {"status": app_state["status"]}

@app.post("/settings")
def update_settings(settings: Settings):
    cleaner.update_api_key(settings.api_key)
    app_state["auto_paste"] = settings.auto_paste
    # In a real app we'd save to config/settings.json here
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
