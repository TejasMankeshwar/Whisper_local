import { register, unregisterAll } from '@tauri-apps/plugin-global-shortcut';

let isListening = false;
let autoPaste = true;
let apiKey = '';

const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const transcriptText = document.getElementById('transcript-text');
const errorMsg = document.getElementById('error-msg');

const apiKeyInput = document.getElementById('api-key');
const autoPasteInput = document.getElementById('auto-paste');
const saveBtn = document.getElementById('save-btn');

const API_BASE = 'http://127.0.0.1:8000';

function updateStatus(state) {
  statusIndicator.className = `status ${state}`;
  statusText.textContent = state.charAt(0).toUpperCase() + state.slice(1);
}

function showError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove('hidden');
  setTimeout(() => {
    errorMsg.classList.add('hidden');
  }, 5000);
}

async function saveSettings() {
  apiKey = apiKeyInput.value;
  autoPaste = autoPasteInput.checked;
  
  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: apiKey,
        auto_paste: autoPaste,
        language: 'en'
      })
    });
    if (res.ok) {
      saveBtn.textContent = 'Saved!';
      setTimeout(() => saveBtn.textContent = 'Save Settings', 2000);
    }
  } catch (err) {
    showError('Could not connect to backend server. Make sure Python backend is running.');
  }
}

async function toggleRecording() {
  if (!isListening) {
    // Start Recording
    try {
      const res = await fetch(`${API_BASE}/start`, { method: 'POST' });
      if (res.ok) {
        isListening = true;
        updateStatus('listening');
        transcriptText.textContent = 'Listening...';
        transcriptText.classList.add('placeholder-text');
      }
    } catch (err) {
      showError('Failed to start recording. Backend down?');
    }
  } else {
    // Stop Recording & Process
    isListening = false;
    updateStatus('processing');
    transcriptText.textContent = 'Processing and cleaning...';
    
    try {
      const res = await fetch(`${API_BASE}/stop`, { method: 'POST' });
      const data = await res.json();
      
      if (data.error) {
        showError(data.error);
        updateStatus('idle');
        transcriptText.textContent = 'Error processing speech.';
      } else {
        updateStatus('done');
        transcriptText.textContent = data.text || '(No text detected)';
        transcriptText.classList.remove('placeholder-text');
        
        setTimeout(() => updateStatus('idle'), 3000);
      }
    } catch (err) {
      showError('Failed to process recording.');
      updateStatus('idle');
    }
  }
}

async function setup() {
  // Load settings (In real app, we'd use tauri-plugin-store)
  const savedKey = localStorage.getItem('gemini_key') || '';
  const savedPaste = localStorage.getItem('auto_paste') !== 'false';
  
  apiKeyInput.value = savedKey;
  autoPasteInput.checked = savedPaste;
  apiKey = savedKey;
  autoPaste = savedPaste;

  saveBtn.addEventListener('click', () => {
    localStorage.setItem('gemini_key', apiKeyInput.value);
    localStorage.setItem('auto_paste', autoPasteInput.checked);
    saveSettings();
  });

  // Register Global Shortcut
  try {
    await unregisterAll();
    await register('Option+Space', (event) => {
      if (event.state === 'Pressed') {
        toggleRecording();
      }
    });
  } catch (err) {
    console.error('Failed to register shortcut', err);
    // fallback for some mac systems where Option is Alt
    try {
      await register('Alt+Space', (event) => {
        if (event.state === 'Pressed') {
          toggleRecording();
        }
      });
    } catch (e) {
      showError('Failed to register global shortcut Option+Space');
    }
  }

  // Initial settings sync
  if (apiKey) {
    saveSettings();
  }
}

window.addEventListener('DOMContentLoaded', setup);
