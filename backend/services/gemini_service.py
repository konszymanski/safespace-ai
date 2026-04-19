import os
import json
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

# Zawsze próbuj `backend/.env` (niezależnie od cwd przy `uvicorn` z katalogu głównego repo).
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")
load_dotenv()


class GeminiService:
    def __init__(self, model_name="gemini-3-flash-preview"):
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = None
        self.init_error = None
        if not api_key:
            self.init_error = "Brak klucza GEMINI_API_KEY w pliku .env!"
        else:
            self.client = genai.Client(
                api_key=api_key,
                vertexai=False
            )
        self.model_name = model_name

        prompt_path = os.path.join("docs", "prompts", "system_prompt.txt")

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                self.system_instruction = f.read().strip()
        except FileNotFoundError:
            self.system_instruction = "Jesteś pomocnym asystentem."
            print(f"OSTRZEŻENIE: Nie znaleziono pliku {prompt_path}")

    def start_chat_session(self):
        if self.client is None:
            raise ValueError(self.init_error or "Gemini client nie został zainicjalizowany.")
        return self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=self.system_instruction
            )
        )

    def ask_gemini(self, prompt: str, system_instruction: str | None = None):
        if self.client is None:
            return f"Błąd: {self.init_error or 'Gemini client nie został zainicjalizowany.'}"
        final_instruction = system_instruction or self.system_instruction
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=final_instruction
                )
            )
            return response.text
        except Exception as e:
            return f"Błąd: {str(e)}"

    def analyze_to_json(self, prompt: str):
        if self.client is None:
            return {"error": self.init_error or "Gemini client nie został zainicjalizowany."}
        json_config = genai.types.GenerateContentConfig(
            system_instruction="Analizuj tekst i zwracaj TYLKO czysty JSON.",
            response_mime_type="application/json"
        )
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=json_config
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e)}

gemini_service = GeminiService()