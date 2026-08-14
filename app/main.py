from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="CalcCast Agent",
    description="AI Agent with LangGraph, LangChain and MCP",
    version="1.0.0",
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "CalcCast Agent is running",
        "status": "healthy"
    }