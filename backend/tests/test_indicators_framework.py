"""Tests for the indicator framework primitives."""

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.analytics.indicators.base import (
    Indicator,
    IndicatorDescription,
    IndicatorRegistry,
    IndicatorResult,
    compute_for_tender,
)
from app.collector.normalizer import persist_tender
from app.models import RiskIndicatorValue

FIXTURE = Path(__file__).parent / "fixtures" / "tender_sample.json"


@pytest.fixture
def tender_data() -> dict:
    return json.loads(FIXTURE.read_text())["data"]


class _OpenProcedureIndicator(Indicator):
    """True when the procurement method is 'open' — exercises the boolean path."""

    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="dummy.open_procedure",
            name="Open procedure",
            value_type="boolean",
            interpretation="True when procurementMethod == 'open'",
        )

    async def compute(self, tender, session) -> IndicatorResult:
        return IndicatorResult(
            code="dummy.open_procedure",
            value_boolean=(tender.procurement_method == "open"),
        )


class _NotYetComputableIndicator(Indicator):
    """Always returns NULL — exercises the 'cannot compute yet' path."""

    def describe(self) -> IndicatorDescription:
        return IndicatorDescription(
            code="dummy.unknown",
            name="Unknown",
            value_type="boolean",
            interpretation="Always None — represents indicators that need more data",
        )

    async def compute(self, tender, session) -> IndicatorResult:
        return IndicatorResult(code="dummy.unknown")


async def test_dispatcher_runs_registered_indicators_and_persists(
    session, tender_data
):
    await persist_tender(session, tender_data)
    await session.commit()

    reg = IndicatorRegistry()
    reg.register(_OpenProcedureIndicator())
    reg.register(_NotYetComputableIndicator())

    persisted = await compute_for_tender(
        session, tender_data["id"], registry=reg
    )
    await session.commit()

    assert len(persisted) == 2

    rows = (
        await session.execute(
            select(RiskIndicatorValue).where(
                RiskIndicatorValue.tender_id == tender_data["id"]
            )
        )
    ).scalars().all()
    by_code = {r.indicator_code: r for r in rows}

    # True value persisted with NULL numeric.
    assert by_code["dummy.open_procedure"].value_boolean is True
    assert by_code["dummy.open_procedure"].value_numeric is None
    # 'Cannot compute' persisted as a row with both columns NULL — present so
    # callers can distinguish "tried, unknown" from "never attempted".
    assert by_code["dummy.unknown"].value_boolean is None
    assert by_code["dummy.unknown"].value_numeric is None


async def test_dispatcher_is_idempotent(session, tender_data):
    """Re-running over the same tender replaces, never duplicates."""
    await persist_tender(session, tender_data)
    await session.commit()

    reg = IndicatorRegistry()
    reg.register(_OpenProcedureIndicator())

    await compute_for_tender(session, tender_data["id"], registry=reg)
    await session.commit()
    await compute_for_tender(session, tender_data["id"], registry=reg)
    await session.commit()

    count = (
        await session.execute(
            select(func.count())
            .select_from(RiskIndicatorValue)
            .where(RiskIndicatorValue.tender_id == tender_data["id"])
        )
    ).scalar_one()
    assert count == 1


async def test_registry_disable_skips_an_indicator(session, tender_data):
    await persist_tender(session, tender_data)
    await session.commit()

    reg = IndicatorRegistry()
    reg.register(_OpenProcedureIndicator())
    reg.register(_NotYetComputableIndicator())
    reg.disable("dummy.unknown")

    persisted = await compute_for_tender(
        session, tender_data["id"], registry=reg
    )
    await session.commit()

    assert [p.indicator_code for p in persisted] == ["dummy.open_procedure"]


async def test_registry_rejects_duplicate_registration():
    reg = IndicatorRegistry()
    reg.register(_OpenProcedureIndicator())
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_OpenProcedureIndicator())


async def test_dispatcher_no_op_when_tender_missing(session):
    """Unknown tender id yields an empty result, no exception."""
    reg = IndicatorRegistry()
    reg.register(_OpenProcedureIndicator())
    persisted = await compute_for_tender(
        session, "nonexistent" + "0" * 21, registry=reg
    )
    assert persisted == []


async def test_indicator_exception_is_logged_and_skipped(session, tender_data):
    """A buggy indicator must not abort the rest of the run."""
    await persist_tender(session, tender_data)
    await session.commit()

    class _Boom(Indicator):
        def describe(self) -> IndicatorDescription:
            return IndicatorDescription(
                code="dummy.boom",
                name="Boom",
                value_type="boolean",
                interpretation="Always raises",
            )

        async def compute(self, tender, session) -> IndicatorResult:
            raise RuntimeError("explosion")

    reg = IndicatorRegistry()
    reg.register(_Boom())
    reg.register(_OpenProcedureIndicator())

    persisted = await compute_for_tender(
        session, tender_data["id"], registry=reg
    )
    await session.commit()

    # Only the working indicator produced a row.
    assert [p.indicator_code for p in persisted] == ["dummy.open_procedure"]
