from fastapi import FastAPI
from pydantic import BaseModel

from lc_demos.langchain_rag_chain import rag_chain

app = FastAPI(title="Kube-InsightAI")


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "Kube-InsightAI",
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    answer = rag_chain.invoke(request.question)

    return ChatResponse(answer=answer)
