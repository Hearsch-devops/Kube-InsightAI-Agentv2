import logging

from fastapi import FastAPI

from app.api.routes import router


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="Kube-InsightAI")


@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": "Kube-InsightAI",
    }


app.include_router(router, prefix="/api")