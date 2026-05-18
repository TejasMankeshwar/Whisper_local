from google import genai

class Cleaner:
    def __init__(self, api_key=""):
        self.api_key = api_key
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    def update_api_key(self, api_key):
        self.api_key = api_key
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def clean_text(self, raw_text):
        if not self.client or not self.api_key:
            return raw_text # Fallback to raw text if no API key

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
        
        try:
            print("Sending to Gemini for cleanup...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return raw_text # Fallback to raw text on error
