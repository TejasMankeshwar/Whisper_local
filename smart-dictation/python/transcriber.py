import os
from faster_whisper import WhisperModel

class Transcriber:
    def __init__(self, model_size="small.en"):
        # We can use small.en for english or medium for multilingual
        # device="cpu" usually, or "auto" if we have an apple silicon device with ctranslate2 optimizations
        # Actually for macOS M-series, "cpu" works with Accelerate.
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def transcribe(self, audio_path):
        if not os.path.exists(audio_path):
            return ""
            
        print(f"Transcribing {audio_path}...")
        segments, info = self.model.transcribe(audio_path, beam_size=5)
        
        text = ""
        for segment in segments:
            text += segment.text + " "
            
        return text.strip()
