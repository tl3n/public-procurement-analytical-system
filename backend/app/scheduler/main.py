"""Periodic Prozorro sync — the entrypoint of the ``scheduler`` Docker service.

Drives the collector on a fixed interval via APScheduler's AsyncIOScheduler. Each
firing opens a fresh HTTP client + DB session, walks the feed once via
``crawler.run_sync``, logs a one-line summary, and releases its resources.

Concurrency: a single job instance at a time (``max_instances=1``); overlapping
firings are coalesced. This is the right behavior for a feed walker, since two
parallel runs would race on the ``sync_state`` cursor.
"""

import asyncio
import logging
import signal
import time
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.collector import crawler
from app.collector.http_client import create_client
from app.config import settings
from app.db import SessionLocal, engine

log = logging.getLogger("scheduler")


async def run_one_sync() -> None:
    """Execute a single sync cycle and log its outcome.

    Branches on ``settings.collection_mode`` between the historical continuous
    walk and the stratified monthly mode.
    """
    started = time.monotonic()
    mode = settings.collection_mode
    log.info("sync starting (mode=%s)", mode)
    try:
        async with create_client() as client, SessionLocal() as session:
            if mode == "monthly":
                result = await crawler.run_sync_monthly(client, session)
            else:
                result = await crawler.run_sync(client, session)
        elapsed = time.monotonic() - started
        log.info(
            "sync finished: processed=%d failed=%d duration=%.1fs",
            result["processed"],
            result["failed"],
            elapsed,
        )
    except Exception:
        # Never let one bad cycle kill the scheduler — log and wait for the next.
        log.exception("sync cycle aborted with an unexpected error")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    log.info(
        "scheduler starting; sync interval = %d minutes",
        settings.sync_interval_minutes,
    )

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_one_sync,
        trigger="interval",
        minutes=settings.sync_interval_minutes,
        # Trigger the first sync immediately on startup, then on the interval.
        next_run_time=datetime.now(),
        max_instances=1,
        coalesce=True,
        id="prozorro-sync",
    )
    scheduler.start()

    # Block forever until SIGINT/SIGTERM arrives, then unwind gracefully.
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    log.info("scheduler running (Ctrl-C or SIGTERM to stop)")
    await stop_event.wait()

    log.info("scheduler shutting down")
    scheduler.shutdown(wait=True)
    await engine.dispose()
    log.info("scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())
