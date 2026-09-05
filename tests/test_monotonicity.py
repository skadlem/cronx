"""T-008 (A-011) — monotonicity property test. A-011 pinned form (plan.md):

  WHEN next_runs is walked across every spring-forward and fall-back transition
  of America/New_York (1 h step), Australia/Lord_Howe (30 min step), and
  Asia/Kathmandu (permanent +05:45, no transitions — the no-op path) over
  2022-01-01..2026-12-31 (--from pinned, schedule `* * * * *` sampled per
  transition window and `*/17 * * * *` walked for a full year each zone) THE
  SYSTEM SHALL emit instants in strictly increasing order with no duplicate
  instant.

Sampling strategy (keeps the run well under A-011's 20 s budget): rather than
enumerating five years of every minute, the transition instants are located
with a cheap day-granularity utcoffset() scan (second bisection within the
change-day), then each transition is probed with a bounded next_runs walk of
361 minutes centred on it (-3 h to +2 h, enough to cross a 1 h jump, a 30 min
Lord_Howe step in either direction, and the following hour). The full-year
`*/17 * * * *` walk (24/17*60*366 < 32000 instants, -n pinned) covers
between-transition behaviour per zone.
"""
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from cronx.occurrences import next_runs
from cronx.parse import parse

UTC = timezone.utc
ZONES = ("America/New_York", "Australia/Lord_Howe", "Asia/Kathmandu")
WINDOW_START = datetime(2022, 1, 1, tzinfo=UTC)
WINDOW_END = datetime(2026, 12, 31, 23, 59, tzinfo=UTC)


def _transitions(zone):
    """UTC instants inside 2022..2026 where the zone's utcoffset changes."""
    tz = ZoneInfo(zone)

    def offset(ts):
        return datetime.fromtimestamp(ts, tz).utcoffset()

    found = []
    day = WINDOW_START
    prev = offset(int(day.timestamp()))
    while day < WINDOW_END:
        nxt = min(day + timedelta(days=1), WINDOW_END)
        cur = offset(int(nxt.timestamp()))
        if cur != prev:                       # the change is within [day, nxt)
            lo, hi = int(day.timestamp()), int(nxt.timestamp())
            while lo + 1 < hi:                # integer-second bisection
                mid = (lo + hi) // 2
                if offset(mid) != prev:
                    hi = mid
                else:
                    lo = mid
            found.append(datetime.fromtimestamp(hi, UTC))
        prev = cur
        day = nxt
    return found


def _assert_strictly_increasing(runs):
    instants = [o.instant for o in runs]
    assert len(set(instants)) == len(instants), "duplicate instant emitted"
    for i in range(len(instants) - 1):
        assert instants[i] < instants[i + 1], "non-increasing instants at %d" % i


class MonotonicityTest(unittest.TestCase):
    def test_wildcard_minute_across_every_transition(self):
        # A-011: `* * * * *` sampled per transition window, 3 zones.
        total = 0
        for zone in ZONES:
            trans = _transitions(zone)
            if zone == "Asia/Kathmandu":
                self.assertEqual(trans, [])   # permanent +05:45: no-op path
            for t in trans:
                runs = next_runs(parse("* * * * *"), ZoneInfo(zone),
                                 t - timedelta(hours=3), 361)
                self.assertEqual(len(runs), 361, zone)  # bounded, full window
                _assert_strictly_increasing(runs)
                total += len(runs)
        self.assertGreater(total, 7000)       # NY+LH: 20 transitions x 361

    def test_step_17_walks_a_full_year_per_zone(self):
        # A-011: `*/17 * * * *` for a full year in each zone (2024, a leap year),
        # crossing both 2024 transitions en route. */17 fires 4x/hour -> 96x/day,
        # and 2024 has 366 days: -n 35136 spans exactly the year, so the last
        # instant lands within a few hours of 2025-01-01T00:00Z in every zone
        # (the zone's local year-end maps there) — pinned, never clock-dependent.
        for zone in ZONES:
            runs = next_runs(parse("*/17 * * * *"), ZoneInfo(zone),
                             datetime(2024, 1, 1, tzinfo=UTC), 35136)
            self.assertEqual(len(runs), 35136, zone)
            _assert_strictly_increasing(runs)
            last = runs[-1].instant
            self.assertGreaterEqual(last, datetime(2024, 12, 31, 23, 0, tzinfo=UTC), zone)
            self.assertLess(last, datetime(2025, 1, 1, 5, 0, tzinfo=UTC), zone)
            trans = _transitions(zone)
            crossed = [t for t in trans if t < last]
            if zone == "Asia/Kathmandu":
                self.assertEqual(crossed, [])
            else:
                self.assertGreaterEqual(len(crossed), 2)  # both 2024 transitions


if __name__ == "__main__":
    unittest.main()
