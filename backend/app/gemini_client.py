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
        self.embedding_model = os.getenv(
            "GEMINI_EMBEDDING_MODEL", "gemini-embedding-001"
        )
        self.last_error: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def generate_json(
        self, prompt: str, response_schema: dict | None = None
    ) -> dict | None:
        if not self.api_key:
            self.last_error = "GEMINI_API_KEY is not set."
            return None

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            config = types.GenerateContentConfig(
                responseMimeType="application/json",
                responseSchema=response_schema,
            )
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            text = getattr(response, "text", "") or ""
            return _parse_json(text)
        except Exception as exc:  # pragma: no cover - network/API fallback.
            self.last_error = str(exc)
            return None

    def generate_text(self, prompt: str) -> str | None:
        if not self.api_key:
            self.last_error = "GEMINI_API_KEY is not set."
            return None

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(model=self.model, contents=prompt)
            return getattr(response, "text", None)
        except Exception as exc:
            self.last_error = str(exc)
            return None

    def generate_embedding(
        self,
        text: str,
        task_type: str = "RETRIEVAL_DOCUMENT",
        dimensions: int | None = None,
    ) -> list[float] | None:
        if not self.api_key:
            self.last_error = "GEMINI_API_KEY is not set."
            return None

        try:
            from google import genai
            from google.genai import types

            config_options: dict[str, str | int] = {"taskType": task_type}
            if dimensions is not None:
                config_options["outputDimensionality"] = dimensions
            config = types.EmbedContentConfig(**config_options)

            client = genai.Client(api_key=self.api_key)
            response = client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=config,
            )
            embeddings = getattr(response, "embeddings", None) or []
            if not embeddings:
                return None
            values = getattr(embeddings[0], "values", None)
            return list(values) if values else None
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
