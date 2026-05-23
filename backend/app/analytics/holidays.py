"""Ukrainian public holidays used by working-day calculations.

A compact static reference: official fixed-date holidays 2020–2026. Movable
holidays (Easter, Trinity) are intentionally omitted — they shift the count by
at most one or two days twice a year, well within the precision the
shortened-period indicator targets. Promoting this set into a database
reference table managed by an admin is a logical future enhancement.
"""

from datetime import date

_FIXED_DATES = [
    (1, 1),    # New Year's Day
    (1, 7),    # Christmas (Orthodox / Julian calendar — until the 2023 reform)
    (3, 8),    # International Women's Day
    (5, 1),    # Labour Day
    (5, 9),    # Day of Remembrance and Victory over Nazism
    (6, 28),   # Constitution Day
    (7, 15),   # Statehood Day (introduced 2022)
    (8, 24),   # Independence Day
    (10, 14),  # Defenders of Ukraine Day
    (12, 25),  # Christmas (Gregorian — official since 2023)
]

UKRAINIAN_HOLIDAYS: frozenset[date] = frozenset(
    date(year, month, day)
    for year in range(2020, 2027)
    for month, day in _FIXED_DATES
)


def is_working_day(d: date) -> bool:
    """True if ``d`` is a Ukrainian working day (Mon–Fri, not a public holiday)."""
    return d.weekday() < 5 and d not in UKRAINIAN_HOLIDAYS


def working_days_between(start: date, end: date) -> int:
    """Inclusive of ``start``, exclusive of ``end`` — the bidder's actual
    business-day window between publication and the submission deadline."""
    if end <= start:
        return 0
    from datetime import timedelta

    count = 0
    cursor = start
    while cursor < end:
        if is_working_day(cursor):
            count += 1
        cursor += timedelta(days=1)
    return count
