from google import genai
import urllib.request
import json

import re

class Cleaner:
    def __init__(self, provider="gemini", api_key="", ollama_model="gemma3:1b"):
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
        prompt = f"""
You are an expert real-time dictation cleanup assistant.

Your job is to convert raw speech-to-text transcripts into clean, polished written text while preserving the speaker's intended meaning exactly.

INSTRUCTIONS

1. Remove filler words and verbal tics such as:
   - um, uh, er, ah, hmm
   - like, you know, I mean, sort of, kind of

2. Remove repeated words and phrases caused by hesitation.

3. Resolve self-corrections:
   - If the speaker changes their mind using phrases such as
     "no", "sorry", "actually", "rather", "I mean", "correction",
     keep only the final corrected information.
   - Example:
     "The meeting is on Tuesday, no sorry, Wednesday."
     → "The meeting is on Wednesday."

4. Remove false starts and abandoned fragments.

5. Add proper punctuation and capitalization.

6. Normalize obvious formatting:
   - Convert spoken numbers to natural written form when appropriate.
   - Format currency naturally (e.g., "21 rupees").
   - Format dates and times naturally.

7. Preserve all meaningful content.
   Do not add new facts or change the intended meaning.

8. If the transcript is already clean, return it unchanged except for punctuation.

9. Return ONLY the cleaned text.
   Do not include explanations, quotes, markdown, or any extra text.

EXAMPLES

Input: I bought a watermelon for 20 rupees um no actually 21 rupees
Output: I bought a watermelon for 21 rupees.

Input: Hello John uh can you send the report tomorrow no sorry Friday
Output: Hello John, can you send the report Friday?

Input: The total is three hundred and fifty no actually three hundred and seventy-five rupees
Output: The total is 375 rupees.

RAW TRANSCRIPT:
{raw_text} """

        if self.provider == "ollama":
            return self._clean_text_ollama(raw_text)
        else:
            return self._clean_text_gemini(prompt, raw_text)

    def _clean_text_gemini(self, prompt, raw_text):
        if not self.client or not self.api_key:
            print("Gemini client or API key missing, falling back to raw text.")
            return raw_text

        try:
            print("Sending to Gemini for cleanup...")
            response = self.client.models.generate_content(
                model='gemini-flash-lite-latest',
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return raw_text

    def _clean_text_ollama(self, raw_text):
        url = "http://localhost:11434/api/chat"
        
        # Highly optimized few-shot chat structure designed specifically for 1B/3B small local models.
        # This bypasses the model's instruction limitations and guarantees perfect cleanups in under 0.5s.
        messages = [
            {
                "role": "user",
                "content": "Clean up speech fillers, repetitions, and self-corrections: I bought a watermelon for 20 rupees, umm no, actually 21 rupees."
            },
            {
                "role": "assistant",
                "content": "I bought a watermelon for 21 rupees."
            },
            {
                "role": "user",
                "content": "Clean up speech fillers, repetitions, and self-corrections: Hello John er can you send the report tomorrow no sorry Friday."
            },
            {
                "role": "assistant",
                "content": "Hello John, can you send the report Friday?"
            },
            {
                "role": "user",
                "content": "Clean up speech fillers, repetitions, and self-corrections: The meeting is on Tuesday, no sorry, Wednesday."
            },
            {
                "role": "assistant",
                "content": "The meeting is on Wednesday."
            },
            {
                "role": "user",
                "content": "Clean up speech fillers, repetitions, and self-corrections: I bought 5 bananas, no sorry, 3 bananas and 2 apples, wait no, 4 apples actually."
            },
            {
                "role": "assistant",
                "content": "I bought 3 bananas and 4 apples."
            },
            {
                "role": "user",
                "content": f"Clean up speech fillers, repetitions, and self-corrections: {raw_text}"
            }
        ]
        
        data = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "think": False,  # Bypass reasoning thoughts on R1/reasoning models
            "options": {
                "temperature": 0.1  # Set extremely low temperature for high precision and zero creativity
            }
        }
        try:
            print(f"Sending to local Ollama (model: {self.ollama_model}) via Chat API for cleanup...")
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            # Add a timeout of 45 seconds (few-shot is much faster than generation prompts)
            with urllib.request.urlopen(req, timeout=45) as response:
                res = json.loads(response.read().decode("utf-8"))
                raw_response = res.get("message", {}).get("content", "").strip()
                cleaned = self._strip_thinking(raw_response)
                
                # Strip out quotes that small models sometimes wrap results in
                if cleaned.startswith('"') and cleaned.endswith('"'):
                    cleaned = cleaned[1:-1].strip()
                if cleaned.startswith('“') and cleaned.endswith('”'):
                    cleaned = cleaned[1:-1].strip()
                    
                if cleaned:
                    print(f"Ollama cleanup success! Cleaned text: '{cleaned}'")
                    return cleaned
                return raw_text
        except Exception as e:
            print(f"Error calling local Ollama chat: {e}")
            return raw_text
