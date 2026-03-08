from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.api.routes import referrals, webhooks
from src.queue.worker import configure_celery


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_celery()
    yield


app = FastAPI(title="Lynd Recruitment Voice Agent", version="0.1.0", lifespan=lifespan)

app.include_router(referrals.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/webhooks")


@app.get("/health")
def health():
    return {"status": "ok"}
