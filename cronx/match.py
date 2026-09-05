"""Schedule -> ascending naive local datetimes. Owns the day rule (ADR-001)
and the bounded search (ADR-008).

Binding: architecture §3.1/§3.2. Iterates wall clock only; DST lives in
occurrences.py (KB: cron-dst-transitions). Stdlib only; Python 3.9 floor.
"""
from datetime import date, datetime, timedelta
from typing import Iterator

from .parse import CronxError, Schedule

# ADR-008: nine years covers the worst satisfiable gap (Feb 29 -> Feb 29, 8y).
HORIZON_DAYS = 366 * 9


def day_matches(s: Schedule, d: date) -> bool:
    """ADR-001 verbatim: month gate, then AND when either day field is a
    leading-'*' star, OR when both are restricted. Field.star is the literal
    first-character flag — never recomputed from values."""
    if d.month not in s.month.values:
        return False
    dom_ok = d.day in s.dom.values
    dow_ok = (d.isoweekday() % 7) in s.dow.values     # Mon..Sun 1..7 -> Sun == 0
    if s.dom.star or s.dow.star:
        return dom_ok and dow_ok                      # ADR-001
    return dom_ok or dow_ok


def _require_fields(s: Schedule) -> None:
    # ADR-004: @reboot has no wall-clock schedule; the CLI short-circuits it
    # upstream, so reaching here is a programming error, told with code 2.
    if (s.reboot or s.minute is None or s.hour is None or s.dom is None
            or s.month is None or s.dow is None):
        raise CronxError("@reboot has no wall-clock schedule: it runs at system "
                         "startup, not at cron times", 2)


def _first_of_next_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def iter_local(s: Schedule, after: datetime) -> Iterator[datetime]:
    """Naive local datetimes, strictly ascending and strictly after `after`.
    Exhausting the horizon ends the iterator with zero further results — an
    unsatisfiable schedule is not an error (ADR-008). The @reboot guard is
    eager: called with a reboot Schedule, this raises before returning."""
    _require_fields(s)
    return _iter_local(s, after)


def _iter_local(s: Schedule, after: datetime) -> Iterator[datetime]:
    hours = sorted(s.hour.values)     # sorted once, outside the loops (§3.1)
    minutes = sorted(s.minute.values)
    start = after.date()
    limit = start + timedelta(days=HORIZON_DAYS)
    d = start
    while d < limit:
        if d.month not in s.month.values:
            d = _first_of_next_month(d)   # cheap month skip (§3.1)
            continue
        if day_matches(s, d):
            for h in hours:
                for m in minutes:
                    dt = datetime(d.year, d.month, d.day, h, m)
                    if dt > after:        # strict: --from exclusivity
                        yield dt
        d += timedelta(days=1)
