import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import referrals, webhooks
from src.queue.worker import configure_celery

logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_celery()
    yield


app = FastAPI(title="Lynd Recruitment Voice Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(referrals.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/webhooks")


@app.get("/health")
def health():
    return {"status": "ok"}
