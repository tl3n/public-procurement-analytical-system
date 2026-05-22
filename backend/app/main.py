"""FastAPI application entrypoint."""

from fastapi import Depends, FastAPI, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

app = FastAPI(title="Аналітична система моніторингу державних закупівель")


@app.get("/health")
async def health(
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Liveness probe — verifies database connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok"}
    except Exception:
        response.status_code = 503
        return {"status": "degraded", "database": "error"}
