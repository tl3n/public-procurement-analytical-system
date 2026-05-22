"""FastAPI application entrypoint.

Commit 1 exposes a minimal app with a /health endpoint. The health check is
wired to the database in commit 2.
"""

from fastapi import FastAPI

app = FastAPI(title="Аналітична система моніторингу державних закупівель")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe. Extended with a DB check in commit 2."""
    return {"status": "ok"}
