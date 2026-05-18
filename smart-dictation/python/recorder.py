import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import threading
import queue
import os

class AudioRecorder:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.channels = 1
        self.q = queue.Queue()
        self.recording = False
        self.stream = None

    def callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.q.put(indata.copy())

    def start_recording(self):
        if self.recording:
            return
        
        self.recording = True
        self.q = queue.Queue()
        self.stream = sd.InputStream(samplerate=self.sample_rate, channels=self.channels, callback=self.callback)
        self.stream.start()
        print("Recording started...")

    def stop_recording(self):
        if not self.recording:
            return None
        
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        print("Recording stopped.")
        
        # Gather all recorded audio data
        audio_data = []
        while not self.q.empty():
            audio_data.append(self.q.get())
        
        if not audio_data:
            return None

        audio_concat = np.concatenate(audio_data, axis=0)
        
        # Save to temp file
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, "smart_dictation_temp.wav")
        wav.write(file_path, self.sample_rate, audio_concat)
        
        return file_path
