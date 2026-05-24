"""Seed the database with a small live sample for demo / thesis defense.

Run from inside the backend image:

    docker compose run --rm backend python -m app.scripts.seed_demo
    docker compose run --rm backend python -m app.scripts.seed_demo 500
    docker compose run --rm backend python -m app.scripts.seed_demo --fresh

The script does three things:

1. Optionally clears the ``sync_state`` cursor so the crawl restarts from the
   configured INITIAL_LOAD_START_TIMESTAMP (use ``--fresh`` for this).
2. Walks the Prozorro feed and persists ``count`` tenders.
3. Triggers the full indicator recompute so the dashboard has values to show.

Assumes the schema is already in place (``alembic upgrade head`` has been run,
typically by the scheduler container's startup command).
"""

import argparse
import asyncio
import logging
import sys

from sqlalchemy import delete

from app.analytics.batch import recompute_all
from app.collector import crawler
from app.collector.http_client import create_client
from app.db import SessionLocal, engine
from app.models.sync import SyncState

log = logging.getLogger("seed-demo")


async def _reset_sync_cursor() -> None:
    async with SessionLocal() as session:
        await session.execute(delete(SyncState).where(SyncState.feed_name == "tenders"))
        await session.commit()
    log.info("cleared sync_state cursor — next crawl will use INITIAL_LOAD_START_TIMESTAMP")


async def _crawl(count: int) -> dict[str, int]:
    async with create_client() as client, SessionLocal() as session:
        return await crawler.run_sync(client, session, max_records=count)


async def _recompute() -> dict[str, int]:
    async with SessionLocal() as session:
        return await recompute_all(session)


async def main(count: int, fresh: bool) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if fresh:
        await _reset_sync_cursor()

    log.info("crawling up to %d tenders from the live Prozorro feed", count)
    crawl_result = await _crawl(count)
    log.info(
        "crawl finished: processed=%d failed=%d",
        crawl_result["processed"],
        crawl_result["failed"],
    )

    log.info("recomputing risk indicators across the dataset")
    recompute_result = await _recompute()
    log.info(
        "recompute finished: tenders=%d bulk_rows=%d",
        recompute_result["tenders_processed"],
        recompute_result["bulk_rows_inserted"],
    )

    await engine.dispose()
    log.info("demo seed complete — open http://localhost:5173/")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "count",
        type=int,
        nargs="?",
        default=200,
        help="Maximum number of tenders to ingest (default 200).",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Reset the sync cursor so the crawl restarts from the configured timestamp.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    asyncio.run(main(count=args.count, fresh=args.fresh))
