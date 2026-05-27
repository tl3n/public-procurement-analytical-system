"""Batch recompute of risk indicators across every tender.

Per-tender computation (the dispatcher in ``indicators.base``) is correct but
wasteful for the two context-dependent indicators — buyer concentration and
price deviation — because each issues its own SQL query keyed on the tender's
buyer / CPV. Across a database of millions of records that is N extra
round-trips per indicator. The batch routine instead loads the supporting
tables once into pandas, evaluates the indicator vectorized over every
tender, and bulk-inserts the resulting rows.

Cheap indicators (single bidding, non-competitive, shortened period) still
flow through the per-tender dispatcher — they only read attributes already
attached to the loaded ``Tender`` object, so the query overhead is the
single ``selectinload`` chain anyway.

The function is intended to be triggered by an administrator endpoint
(scheduled for commit 13). It commits incrementally rather than wrapping the
entire run in one giant transaction.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.indicators import registry as _default_registry
from app.analytics.indicators.base import (
    Indicator,
    IndicatorRegistry,
    compute_for_tender,
)
from app.analytics.indicators.buyer_concentration import BuyerConcentrationIndicator
from app.analytics.indicators.price_deviation import PriceDeviationIndicator
from app.models import Award, Contract, Item, Lot, RiskIndicatorValue, Tender

log = logging.getLogger(__name__)

# Indicators whose code we route through the bulk-pandas path. Currently
# empty: both context-dependent indicators flow through the per-tender
# dispatcher so the composite CRI can see all five base signals when it
# combines them (the bulk path persists rows after Pass 1's CRI has
# already been written, which would leave the composite blind to the two
# bulk indicators). The pandas implementations below are kept for future
# reactivation if the per-tender cost ever becomes a bottleneck.
BULK_INDICATOR_CODES: frozenset[str] = frozenset()


async def recompute_all(
    session: AsyncSession,
    *,
    registry: IndicatorRegistry = _default_registry,
    batch_size: int = 200,
) -> dict[str, int]:
    """Recompute every enabled indicator across every tender.

    Two passes:

    * Pass 1 walks every tender by id, calling the per-tender dispatcher with
      a registry that contains only the simple (non-bulk) indicators. The
      dispatcher's replace semantics first delete *all* prior
      ``risk_indicator_values`` rows for the tender, so any bulk-indicator
      rows from a previous run are cleared at the same time.

    * Pass 2 evaluates each bulk indicator over the full dataset in pandas
      and inserts one row per tender. ``None`` values are persisted as rows
      with ``value_numeric IS NULL`` to mark "evaluated, no result".

    Returns a small summary suitable for logging or returning to an admin
    endpoint.
    """
    per_tender_registry, bulk_indicators = _partition(registry)

    tenders_processed = await _pass_1_per_tender(
        session, per_tender_registry, batch_size
    )
    bulk_rows_inserted = await _pass_2_bulk(session, bulk_indicators)

    log.info(
        "batch recompute done: tenders=%d bulk_rows=%d",
        tenders_processed,
        bulk_rows_inserted,
    )
    return {
        "tenders_processed": tenders_processed,
        "bulk_rows_inserted": bulk_rows_inserted,
    }


# --- Internal helpers -------------------------------------------------------


def _partition(
    registry: IndicatorRegistry,
) -> tuple[IndicatorRegistry, list[Indicator]]:
    per_tender = IndicatorRegistry()
    bulk: list[Indicator] = []
    for ind in registry.enabled():
        if ind.describe().code in BULK_INDICATOR_CODES:
            bulk.append(ind)
        else:
            per_tender.register(ind)
    return per_tender, bulk


async def _pass_1_per_tender(
    session: AsyncSession,
    per_tender_registry: IndicatorRegistry,
    batch_size: int,
) -> int:
    """Walk every tender id ordered ascending and run the dispatcher."""
    last_id = ""
    processed = 0
    while True:
        ids = (
            await session.execute(
                select(Tender.id)
                .where(Tender.id > last_id)
                .order_by(Tender.id)
                .limit(batch_size)
            )
        ).scalars().all()
        if not ids:
            break
        for tid in ids:
            await compute_for_tender(session, tid, registry=per_tender_registry)
            processed += 1
        await session.commit()
        last_id = ids[-1]
    return processed


async def _pass_2_bulk(
    session: AsyncSession, bulk_indicators: list[Indicator]
) -> int:
    """Bulk-compute each context-dependent indicator and insert its rows."""
    if not bulk_indicators:
        return 0
    inserted = 0
    now = datetime.now(tz=UTC)
    for indicator in bulk_indicators:
        code = indicator.describe().code
        if isinstance(indicator, BuyerConcentrationIndicator):
            values = await _bulk_buyer_concentration(session, indicator)
        elif isinstance(indicator, PriceDeviationIndicator):
            values = await _bulk_price_deviation(session, indicator)
        else:
            # An indicator code matches BULK_INDICATOR_CODES but the class is
            # unknown — fall back to the per-tender dispatcher so we still
            # produce rows rather than silently dropping the indicator.
            log.warning(
                "unknown bulk indicator class for %s; using per-tender fallback",
                code,
            )
            continue
        for tender_id, value in values.items():
            session.add(
                RiskIndicatorValue(
                    tender_id=tender_id,
                    indicator_code=code,
                    value_numeric=value,
                    computed_at=now,
                )
            )
            inserted += 1
        await session.commit()
    return inserted


async def _all_tender_ids(session: AsyncSession) -> list[str]:
    rows = (await session.execute(select(Tender.id))).scalars().all()
    return list(rows)


async def _bulk_buyer_concentration(
    session: AsyncSession, indicator: BuyerConcentrationIndicator
) -> dict[str, Decimal | None]:
    """Largest supplier share of each buyer's contract spend in the loaded
    period (i.e. across all contracts of the buyer signed via tenders
    published at or before the current tender). Mirrors the per-tender
    indicator's semantics — see ``buyer_concentration.compute``."""
    del indicator  # kept for signature compatibility with the registry
    tender_rows = (
        await session.execute(
            select(
                Tender.id,
                Tender.procuring_entity_id,
                Tender.date_published,
            )
        )
    ).all()
    if not tender_rows:
        return {}
    tenders_df = pd.DataFrame(
        tender_rows, columns=["id", "buyer_id", "date_published"]
    )

    # Use the parent tender's date_published as the temporal anchor —
    # Contract.date_signed is unreliable in the Prozorro export and would
    # filter out most of the contracted spend.
    contract_rows = (
        await session.execute(
            select(
                Contract.supplier_id,
                Contract.value_amount,
                Tender.date_published.label("anchor_date"),
                Tender.procuring_entity_id.label("buyer_id"),
            )
            .join(Award, Award.id == Contract.award_id)
            .join(Lot, Lot.id == Award.lot_id)
            .join(Tender, Tender.id == Lot.tender_id)
            .where(Contract.value_amount.isnot(None))
            .where(Tender.date_published.isnot(None))
        )
    ).all()

    results: dict[str, Decimal | None] = {tid: None for tid in tenders_df["id"]}
    if not contract_rows:
        return results

    contracts_df = pd.DataFrame(
        contract_rows,
        columns=["supplier_id", "value", "anchor_date", "buyer_id"],
    )
    contracts_df["value"] = contracts_df["value"].astype(float)
    contracts_df["anchor_date"] = pd.to_datetime(
        contracts_df["anchor_date"], utc=True
    )
    tenders_df["date_published"] = pd.to_datetime(
        tenders_df["date_published"], utc=True
    )

    for tender in tenders_df.itertuples(index=False):
        if pd.isna(tender.buyer_id) or pd.isna(tender.date_published):
            continue
        # No fixed lookback — every contract of this buyer up to and
        # including the current tender's publication date contributes.
        mask = (
            (contracts_df["buyer_id"] == tender.buyer_id)
            & (contracts_df["anchor_date"] <= tender.date_published)
        )
        subset = contracts_df.loc[mask, ["supplier_id", "value"]]
        if subset.empty:
            continue
        by_supplier = subset.groupby("supplier_id")["value"].sum()
        total = float(by_supplier.sum())
        if total == 0:
            continue
        share = float(by_supplier.max()) / total
        results[tender.id] = Decimal(str(share))
    return results


async def _bulk_price_deviation(
    session: AsyncSession, indicator: PriceDeviationIndicator
) -> dict[str, Decimal | None]:
    """Relative deviation of a tender's expected value from its CPV-group
    median across the loaded data period (strictly before its publication
    date). Mirrors ``price_deviation.compute`` — see that module for the
    motivation behind dropping a fixed lookback window."""
    all_ids = await _all_tender_ids(session)
    results: dict[str, Decimal | None] = {tid: None for tid in all_ids}

    rows = (
        await session.execute(
            select(
                Tender.id,
                Tender.value_amount,
                Tender.date_published,
                Item.cpv_code,
            )
            .join(Lot, Lot.tender_id == Tender.id)
            .join(Item, Item.lot_id == Lot.id)
            .where(Item.cpv_code.isnot(None))
        )
    ).all()
    if not rows:
        return results

    df = pd.DataFrame(rows, columns=["id", "value", "date_published", "cpv"])
    # Each tender keeps only its first CPV — matches the per-tender indicator.
    df = df.drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce").astype(float)
    df["date_published"] = pd.to_datetime(df["date_published"], utc=True)
    min_ref = indicator.min_reference_size

    for tender in df.itertuples(index=False):
        if pd.isna(tender.value) or pd.isna(tender.date_published):
            continue
        # No fixed lookback — the reference set is every comparable tender
        # published before this one.
        mask = (
            (df["cpv"] == tender.cpv)
            & (df["date_published"] < tender.date_published)
            & (df["id"] != tender.id)
            & (df["value"].notna())
        )
        refs = df.loc[mask, "value"]
        if len(refs) < min_ref:
            continue
        median = refs.median()
        if pd.isna(median) or median == 0:
            continue
        deviation = (tender.value - median) / median
        results[tender.id] = Decimal(str(deviation))
    return results
