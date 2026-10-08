from fastapi import APIRouter, HTTPException

from app.models.agent import AgentRequest
from app.services.container import agent_service


router = APIRouter()

@router.post("/agent")
async def agent(request: AgentRequest):

    try:

        return await agent_service.process(
            request.message
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )