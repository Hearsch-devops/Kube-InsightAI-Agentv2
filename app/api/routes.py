from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.llm.llm import get_llm_response

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):

    try:
        response = get_llm_response(request.message)

        return {
            "response": response
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e),
        )