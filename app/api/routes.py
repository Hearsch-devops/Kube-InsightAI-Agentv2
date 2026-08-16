from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from langchain_core.messages import HumanMessage

from app.agent.graph import graph


router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    try:

        result = await graph.ainvoke(
            {
                "message": request.message,
                "messages": [
                    HumanMessage(content=request.message)
                ],
                "response": "",
            }
        )

        messages = result.get("messages", [])

        if messages:

            final_message = messages[-1]

            return {
                "response": final_message.content
            }

        return {
            "response": result.get("response", "")
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )