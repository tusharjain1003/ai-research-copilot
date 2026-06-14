from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.database.session import init_db
from app.services.llm import LLMConfigurationError
from app.utils.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Research Copilot", lifespan=lifespan)


@app.exception_handler(LLMConfigurationError)
async def llm_config_error_handler(request: Request, exc: LLMConfigurationError):
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )


app.include_router(api_router)
