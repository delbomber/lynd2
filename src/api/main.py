from fastapi import FastAPI
from src.api.routes import referrals, webhooks

app = FastAPI(title="Lynd Recruitment Voice Agent", version="0.1.0")

app.include_router(referrals.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/webhooks")


@app.get("/health")
def health():
    return {"status": "ok"}
