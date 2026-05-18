from google import genai
import urllib.request
import json

import re

class Cleaner:
    def __init__(self, provider="gemini", api_key="", ollama_model="qwen:4b"):
        self.provider = provider
        self.api_key = api_key
        self.ollama_model = ollama_model
        
        self.client = None
        if self.provider == "gemini" and self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def update_settings(self, provider, api_key, ollama_model):
        self.provider = provider
        self.api_key = api_key
        self.ollama_model = ollama_model
        
        if self.provider == "gemini" and self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def _strip_thinking(self, text):
        if not text:
            return ""
        # Remove <think>...</think> tags and everything inside them
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Remove any standard standalone thought steps starting with Thinking... or steps
        cleaned = re.sub(r'^(Thinking|Steps:|Okay, the user).*?\n\n', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        # Remove empty lines and return
        return cleaned.strip()

    def clean_text(self, raw_text):
        prompt = f"""You are a speech cleanup assistant.
Convert spoken text into polished written text.

Rules:
1. Remove filler words such as um, uh, like, you know.
2. Remove false starts and repeated words.
3. Keep the final corrected value when the speaker changes their mind.
4. Preserve meaning exactly.
5. Add proper punctuation.
6. Return only the cleaned text, without any conversational padding, introduction, or quotes.

Raw text: {raw_text}"""

        if self.provider == "ollama":
            return self._clean_text_ollama(prompt, raw_text)
        else:
            return self._clean_text_gemini(prompt, raw_text)

    def _clean_text_gemini(self, prompt, raw_text):
        if not self.client or not self.api_key:
            print("Gemini client or API key missing, falling back to raw text.")
            return raw_text

        try:
            print("Sending to Gemini for cleanup...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return raw_text

    def _clean_text_ollama(self, prompt, raw_text):
        url = "http://localhost:11434/api/generate"
        data = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "think": False,  # Instruct Ollama to bypass reasoning and output final response directly
            "options": {
                "temperature": 0.2
            }
        }
        try:
            print(f"Sending to local Ollama (model: {self.ollama_model}) for cleanup...")
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            # Add a timeout of 90 seconds to allow slow local models to complete
            with urllib.request.urlopen(req, timeout=90) as response:
                res = json.loads(response.read().decode("utf-8"))
                raw_response = res.get("response", "").strip()
                cleaned = self._strip_thinking(raw_response)
                if cleaned:
                    print(f"Ollama cleanup success! Cleaned text: '{cleaned}'")
                    return cleaned
                return raw_text
        except Exception as e:
            print(f"Error calling local Ollama: {e}")
            return raw_text
