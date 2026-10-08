import httpx
from fastapi import HTTPException

from app.config import (
    OLLAMA_CHAT_URL,
    OLLAMA_URL,
    MODEL,
    OLLAMA_TIMEOUT,
)


class OllamaService:

    async def health(self):

        try:

            async with httpx.AsyncClient(
                timeout=5
            ) as client:

                response = await client.get(
                    f"{OLLAMA_URL}/api/tags"
                )

            return {
                "backend": "online",
                "ollama": response.status_code == 200
            }

        except Exception as e:

            return {
                "backend": "online",
                "ollama": False,
                "error": str(e)
            }

    async def chat(self, messages, tools=None):

        payload = {
            "model": MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        }

        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(
                timeout=OLLAMA_TIMEOUT
            ) as client:

                response = await client.post(
                    OLLAMA_CHAT_URL,
                    json=payload
                )

                response.raise_for_status()

                return response.json()
        except httpx.HTTPStatusError as error:
            try:
                error_body = error.response.json()
                detail = error_body.get("error", error.response.text) if isinstance(error_body, dict) else error.response.text
            except ValueError:
                detail = error.response.text or str(error)
            raise HTTPException(
                status_code=502,
                detail=f"Ollama returned {error.response.status_code}: {detail}"
            ) from error
        except httpx.RequestError as error:
            raise HTTPException(
                status_code=503,
                detail=f"Ollama is unavailable at {OLLAMA_URL}. Ensure Ollama is running."
            ) from error