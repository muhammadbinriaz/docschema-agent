from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import init_db
from app.routers import jobs

log = logging.getLogger("docschema")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info(
        "DocSchema ready  llm=%s/%s",
        settings.llm_provider(),
        settings.llm_model() if settings.llm_api_key() else "regex-fallback",
    )
    yield


app = FastAPI(
    title="DocSchema API",
    version="0.1.0",
    description="Document → structured fields with human review.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm": {
            "provider": settings.llm_provider(),
            "model": settings.llm_model(),
            "configured": bool(settings.llm_api_key()),
        },
    }
