import json
import httpx
from app.core.config import settings


class OllamaClient:
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        payload = {
            "model": model or settings.OLLAMA_CHAT_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": settings.TEMPERATURE,
                "top_p": settings.TOP_P,
                "top_k": settings.TOP_K,
                "seed": settings.SEED,
                "num_ctx": settings.OLLAMA_NUM_CTX,
            },
        }
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
            return data.get("message", {}).get("content", "")

    async def chat_stream(self, messages: list[dict], model: str | None = None):
        """Stream tokens from the Ollama chat API (async generator)."""
        payload = {
            "model": model or settings.OLLAMA_CHAT_MODEL,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": settings.TEMPERATURE,
                "top_p": settings.TOP_P,
                "top_k": settings.TOP_K,
                "seed": settings.SEED,
                "num_ctx": settings.OLLAMA_NUM_CTX,
            },
        }
        # For streaming: connect/write have a hard limit but read=None so slow
        # cloud token generation never cuts the stream mid-response.
        stream_timeout = httpx.Timeout(
            connect=30.0,
            read=None,   # no read timeout — wait as long as needed per token
            write=30.0,
            pool=30.0,
        )
        async with httpx.AsyncClient(timeout=stream_timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
                headers=self._headers(),
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        """Get embedding vector.

        Tries the newer /api/embed endpoint first (Ollama ≥ 0.1.26 and cloud),
        falls back to the legacy /api/embeddings if 404 is returned.
        """
        mdl = model or settings.OLLAMA_EMBED_MODEL
        async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
            # ── Try new endpoint first (/api/embed) ──────────────────────────
            r = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": mdl, "input": text},
                headers=self._headers(),
            )
            if r.status_code == 404:
                # ── Fall back to legacy endpoint (/api/embeddings) ───────────
                r = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": mdl, "prompt": text},
                    headers=self._headers(),
                )
            r.raise_for_status()
            data = r.json()
            # /api/embed  → {"embeddings": [[...]]}
            if "embeddings" in data and data["embeddings"]:
                return data["embeddings"][0]
            # /api/embeddings → {"embedding": [...]}
            if "embedding" in data:
                return data["embedding"]
            raise RuntimeError(f"No embedding in response: {data}")


chat_llm = OllamaClient(settings.OLLAMA_BASE_URL, settings.OLLAMA_API_KEY)
embed_llm = OllamaClient(settings.OLLAMA_EMBED_BASE_URL, settings.OLLAMA_EMBED_API_KEY)
local_llm = OllamaClient(settings.LOCAL_LLM_BASE_URL)   # local server for Qwen2.5 etc.
