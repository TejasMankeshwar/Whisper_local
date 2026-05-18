import { register, unregisterAll } from '@tauri-apps/plugin-global-shortcut';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

let isListening = false;
let provider = 'gemini';
let apiKey = '';
let ollamaModel = 'gemma3:1b';
let autoPaste = true;

let lastPressTime = 0;
let pressTimeout = null;

const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const rawTranscriptText = document.getElementById('raw-transcript-text');
const transcriptText = document.getElementById('transcript-text');
const errorMsg = document.getElementById('error-msg');

const aiProviderSelect = document.getElementById('ai-provider');
const geminiGroup = document.getElementById('gemini-group');
const ollamaGroup = document.getElementById('ollama-group');
const apiKeyInput = document.getElementById('api-key');
const ollamaModelInput = document.getElementById('ollama-model');
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
  provider = aiProviderSelect.value;
  apiKey = apiKeyInput.value;
  ollamaModel = ollamaModelInput.value;
  autoPaste = autoPasteInput.checked;

  try {
    const res = await fetch(`${API_BASE}/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: provider,
        api_key: apiKey,
        ollama_model: ollamaModel,
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
        invoke('sync_listening_state', { listening: true }).catch(console.error);
        updateStatus('listening');
        rawTranscriptText.value = 'Listening...';
        transcriptText.value = 'Listening...';
        rawTranscriptText.classList.add('placeholder-text');
        transcriptText.classList.add('placeholder-text');
      }
    } catch (err) {
      showError('Failed to start recording. Backend down?');
    }
  } else {
    // Stop Recording & Process
    isListening = false;
    invoke('sync_listening_state', { listening: false }).catch(console.error);
    updateStatus('processing');
    rawTranscriptText.value = 'Transcribing voice...';
    transcriptText.value = 'Processing and cleaning...';

    try {
      const res = await fetch(`${API_BASE}/stop`, { method: 'POST' });
      const data = await res.json();

      if (data.error) {
        showError(data.error);
        updateStatus('idle');
        rawTranscriptText.value = 'Error processing speech.';
        transcriptText.value = 'Error processing speech.';
      } else {
        updateStatus('done');
        rawTranscriptText.value = data.raw_text || '(No text detected)';
        transcriptText.value = data.text || '(No text detected)';
        rawTranscriptText.classList.remove('placeholder-text');
        transcriptText.classList.remove('placeholder-text');

        setTimeout(() => updateStatus('idle'), 3000);
      }
    } catch (err) {
      showError('Failed to process recording.');
      updateStatus('idle');
    }
  }
}

async function handleShortcutTrigger() {
  const now = Date.now();
  const timeDiff = now - lastPressTime;
  lastPressTime = now;

  if (isListening) {
    // If already recording, a SINGLE press immediately stops it
    if (pressTimeout) {
      clearTimeout(pressTimeout);
      pressTimeout = null;
    }
    await toggleRecording();
  } else {
    // If idle, a DOUBLE press starts recording
    if (timeDiff < 400) { // 400ms double-press window
      if (pressTimeout) {
        clearTimeout(pressTimeout);
        pressTimeout = null;
      }
      await toggleRecording();
    } else {
      // First press of potential double-press
      pressTimeout = setTimeout(() => {
        pressTimeout = null;
      }, 400);
    }
  }
}

async function setup() {
  // Load settings (In real app, we'd use tauri-plugin-store)
  const savedProvider = localStorage.getItem('ai_provider') || 'gemini';
  const savedKey = localStorage.getItem('gemini_key') || '';
  const savedModel = localStorage.getItem('ollama_model') || 'gemma3:1b';
  const savedPaste = localStorage.getItem('auto_paste') !== 'false';

  aiProviderSelect.value = savedProvider;
  apiKeyInput.value = savedKey;
  ollamaModelInput.value = savedModel;
  autoPasteInput.checked = savedPaste;

  provider = savedProvider;
  apiKey = savedKey;
  ollamaModel = savedModel;
  autoPaste = savedPaste;

  function updateUIForProvider(p) {
    if (p === 'ollama') {
      geminiGroup.classList.add('hidden');
      ollamaGroup.classList.remove('hidden');
    } else {
      geminiGroup.classList.remove('hidden');
      ollamaGroup.classList.add('hidden');
    }
  }

  // Update UI immediately based on initial value
  updateUIForProvider(provider);

  aiProviderSelect.addEventListener('change', (e) => {
    updateUIForProvider(e.target.value);
  });

  saveBtn.addEventListener('click', () => {
    localStorage.setItem('ai_provider', aiProviderSelect.value);
    localStorage.setItem('gemini_key', apiKeyInput.value);
    localStorage.setItem('ollama_model', ollamaModelInput.value);
    localStorage.setItem('auto_paste', autoPasteInput.checked);
    saveSettings();
  });

  statusIndicator.addEventListener('click', toggleRecording);

  // Listen to native Fn/Globe key events from Rust
  listen('fn-shortcut', (event) => {
    console.log('Fn shortcut event received:', event.payload);
    if (event.payload === 'start' && !isListening) {
      toggleRecording();
    } else if (event.payload === 'stop' && isListening) {
      toggleRecording();
    }
  });

  // Register Global Shortcut
  try {
    await unregisterAll();
    await register('Option+Space', (event) => {
      if (event.state === 'Pressed') {
        handleShortcutTrigger();
      }
    });
  } catch (err) {
    console.error('Failed to register shortcut', err);
    // fallback for some mac systems where Option is Alt
    try {
      await register('Alt+Space', (event) => {
        if (event.state === 'Pressed') {
          handleShortcutTrigger();
        }
      });
    } catch (e) {
      showError('Failed to register global shortcut Option+Space');
    }
  }

  // Prevent Option+Space from inserting spaces in the webview
  window.addEventListener('keydown', (e) => {
    if (e.altKey && e.code === 'Space') {
      e.preventDefault();
      handleShortcutTrigger();
    }
  });

  // Initial settings sync
  saveSettings();
}

window.addEventListener('DOMContentLoaded', setup);
