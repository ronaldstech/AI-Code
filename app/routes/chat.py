from fastapi import APIRouter, Depends

from app.models.chat import ChatRequest
from app.routes.auth import current_user
from app.services.ollama import OllamaService
from app.routes.auth import auth, current_user


router = APIRouter()

ollama = OllamaService()


@router.post("/chat")
async def chat(request: ChatRequest, user=Depends(current_user)):

    messages = [
        {
            "role": message.role,
            "content": message.content
        }
        for message in request.messages
    ]

    data = await ollama.chat(messages)
    user_message = request.messages[-1]
    auth.save_chat_message(user["id"], user_message.role, user_message.content)
    auth.save_chat_message(user["id"], data["message"]["role"], data["message"]["content"])

    return {
        "message": data["message"],
        "model": data.get("model")
    }


@router.get("/chat/history")
async def chat_history(user=Depends(current_user)):
    return {"messages": auth.get_chat_history(user["id"])}