import json
import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class GeminiClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.last_error: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate_json(self, prompt: str) -> dict | None:
        if not self.api_key:
            self.last_error = "GEMINI_API_KEY is not set."
            return None

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(model=self.model, contents=prompt)
            text = getattr(response, "text", "") or ""
            return _parse_json(text)
        except Exception as exc:  # pragma: no cover - network/API fallback.
            self.last_error = str(exc)
            return None


def _parse_json(text: str) -> dict | None:
    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()

    first = cleaned.find("{")
    last = cleaned.rfind("}")

    if first == -1 or last == -1:
        return None

    try:
        parsed = json.loads(cleaned[first : last + 1])
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


gemini_client = GeminiClient()
