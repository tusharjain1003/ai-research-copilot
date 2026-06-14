from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.database.session import init_db
from app.utils.logging import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Research Copilot", lifespan=lifespan)

app.include_router(api_router)
