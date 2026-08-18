"""Minimal application used to verify the scaffolding works.

The real endpoints arrive in stage 4.
"""

from fastapi import FastAPI

app = FastAPI(title="Fraud Detection API")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe. Does not check the database yet."""
    return {"status": "ok"}
