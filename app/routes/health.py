from fastapi import APIRouter

from app.services.ollama import OllamaService


router = APIRouter()

ollama = OllamaService()


@router.get("/health")
async def health():

    return await ollama.health()