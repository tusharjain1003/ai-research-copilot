from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.sessions import router as sessions_router
from app.api.workflow import router as workflow_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(workflow_router)
