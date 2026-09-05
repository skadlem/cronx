"""naive local -> aware instants. Owns zone resolution (ADR-011) and the DST
policy (ADR-002, ADR-003).

Binding: architecture §3.3. The only module allowed to import zoneinfo.
Float timestamps are forbidden in the gap search (sub-second residue); the
search is integer-second bisection. Offsets are never assumed whole hours.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .match import iter_local
from .parse import CronxError, Schedule

UTC = timezone.utc


@dataclass(frozen=True)
class Occurrence:
    instant: datetime              # aware, UTC
    local: datetime                # aware, in the target zone, fold set
    dst: Optional[str]             # None | gap_shifted | ambiguous_first | ambiguous_second
    nominal: Optional[datetime]    # naive wall clock asked for; set only for gap_shifted


def _unknown_zone(name):
    return "unknown timezone '%s': not in the system tz database" % name


_NO_TZDB = ("no system timezone database found: zoneinfo could not load 'UTC' "
            "(install the OS tzdata package or set PYTHONTZPATH)")


def resolve_zone(name: str) -> ZoneInfo:
    """ADR-011: one ZoneInfo(name), and on failure a cheap ZoneInfo('UTC')
    probe distinguishes an unknown zone from a missing tz database. Both are
    CronxError code 2; resolution happens before any output."""
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        pass
    except ValueError:  # non-relative-path key: a typo, not a missing database
        raise CronxError(_unknown_zone(name), 2)
    try:
        ZoneInfo("UTC")
    except Exception:
        raise CronxError(_NO_TZDB, 2)
    raise CronxError(_unknown_zone(name), 2)


def _is_gap(naive: datetime, tz: ZoneInfo) -> bool:
    # zoneinfo does not raise in a gap (KB: cron-dst-transitions); the only
    # detection is the UTC round-trip landing on a different wall clock.
    back = naive.replace(tzinfo=tz).astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    return back != naive


def _jump_instant(naive: datetime, tz: ZoneInfo) -> datetime:
    """Earliest instant whose local time is >= `naive`, bisected over integer
    seconds between fold=1 (before the jump) and fold=0 (at/after it). The
    architecture's pseudocode, verbatim — int() timestamps, never float."""
    lo = int(naive.replace(tzinfo=tz, fold=1).timestamp())
    hi = int(naive.replace(tzinfo=tz, fold=0).timestamp())
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if datetime.fromtimestamp(mid, tz).replace(tzinfo=None) >= naive:
            hi = mid
        else:
            lo = mid
    return datetime.fromtimestamp(hi, UTC)


def resolve(naive: datetime, tz: ZoneInfo, wildcard: bool) -> List[Occurrence]:
    """One wall clock -> 0, 1 or 2 instants under ADR-002/ADR-003."""
    if _is_gap(naive, tz):                    # order matters: a gap is fold-split too
        if wildcard:
            return []                         # Vixie: MIN_STAR|HR_STAR jobs are skipped
        instant = _jump_instant(naive, tz)
        return [Occurrence(instant, instant.astimezone(tz), "gap_shifted", naive)]
    first = naive.replace(tzinfo=tz, fold=0)
    second = naive.replace(tzinfo=tz, fold=1)
    if first.utcoffset() != second.utcoffset():
        first_i = first.astimezone(UTC)
        second_i = second.astimezone(UTC)
        if second_i == first_i:               # same instant: ordinary, not ambiguous
            return [Occurrence(first_i, first, None, None)]
        first_occ = Occurrence(first_i, first, "ambiguous_first", None)
        if wildcard:                          # ADR-003: both passes, in instant order
            return [first_occ, Occurrence(second_i, second, "ambiguous_second", None)]
        return [first_occ]                    # fixed time: once, the earlier pass
    return [Occurrence(first.astimezone(UTC), first, None, None)]


def _zone(tz: Union[str, ZoneInfo]) -> ZoneInfo:
    return resolve_zone(tz) if isinstance(tz, str) else tz


def _wildcard(s: Schedule) -> bool:
    # Vixie's MIN_STAR | HR_STAR, reusing ADR-001's flag — never recomputed
    # from values (architecture §2).
    return s.minute.star or s.hour.star


def next_runs(s: Schedule, tz, after_utc: datetime, count: int) -> List[Occurrence]:
    """Ascending-by-instant run list, strictly after `after_utc` (ADR-008).
    The one strictly-greater filter gives --from exclusivity, the ADR-002 gap
    collapse and RSK-4 monotonicity — no sort, no buffer."""
    zone = _zone(tz)
    if count <= 0:
        return []
    after_local = after_utc.astimezone(zone).replace(tzinfo=None)
    candidates = iter_local(s, after_local)  # raises cleanly for @reboot (ADR-004)
    wildcard = _wildcard(s)
    out = []
    last = after_utc
    for naive in candidates:
        for occ in resolve(naive, zone, wildcard):
            if occ.instant > last:
                out.append(occ)
                last = occ.instant
                if len(out) >= count:
                    return out
    return out
