import logging

from fastapi import FastAPI

from app.api.routes import router

from app.database import init_db

from app.api.auth_routes import router as auth_router

from app.api.admin_routes import router as admin_router

from app.api.remediation_routes import router as remediation_router

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="Kube-InsightAI")

@app.on_event("startup")
async def initialize_database():
    init_db()
    logger.info("Database initialized successfully")

@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": "Kube-InsightAI",
    }


app.include_router(router, prefix="/api")

app.include_router(auth_router, prefix="/api")

app.include_router(admin_router, prefix="/api")

app.include_router(remediation_router, prefix="/api")