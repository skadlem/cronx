"""T-008 (A-010) — crontab(5) oracle suite through the public entry points.

Each case cites its KB chunk id (kb.py search --db .pmos/kb.sqlite3 ... --role qa):
id=55  project qa 'cronx oracle cases (T-008, A-010) - the discriminating set'
id=39  cron-dom-dow-or-rule.md 'CONFIRMED by crontab(5)' / cron-field-semantics.md id=30
id=29  cron-dst-transitions.md — expectations are the SPEC (ADR-001/002/003/008), pinned
via explicit --from references, never now(). One case runs the real CLI subprocess.
"""
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from cronx.match import HORIZON_DAYS
from cronx.occurrences import next_runs
from cronx.parse import parse

UTC = timezone.utc
NY = "America/New_York"
KTM = "Asia/Kathmandu"


def runs(expr, tz, frm, n):
    return next_runs(parse(expr), ZoneInfo(tz), datetime.fromisoformat(frm), n)


class DayRuleOracleTest(unittest.TestCase):
    def test_or_rule_13th_and_friday(self):
        # KB id=55/39: `0 0 13 * FRI` fires every 13th AND every Friday (OR rule).
        r = runs("0 0 13 * FRI", "UTC", "2026-01-01T00:00:00+00:00", 10)
        local = [x.local for x in r]
        self.assertIn(datetime(2026, 1, 13, tzinfo=UTC), local)   # 13th, not a Friday
        self.assertEqual(local[0], datetime(2026, 1, 2, tzinfo=UTC))  # a Friday, not the 13th
        fri13 = [d for d in local if d.day == 13 and d.isoweekday() == 5]
        self.assertEqual(fri13, [datetime(2026, 2, 13, tzinfo=UTC)])  # Friday the 13th once
        self.assertEqual(len(set(local)), 10)                     # no duplicate instants

    def test_dow_0_equals_7(self):
        # KB id=55/30: `0 0 * * 0` and `0 0 * * 7` are the same schedule (Sunday).
        a = runs("0 0 * * 0", "UTC", "2026-01-01T00:00:00+00:00", 10)
        b = runs("0 0 * * 7", "UTC", "2026-01-01T00:00:00+00:00", 10)
        self.assertEqual([x.instant for x in a], [x.instant for x in b])
        self.assertTrue(all(x.local.isoweekday() == 7 for x in a))  # all Sundays

    def test_step_star_dom_is_and_with_monday(self):
        # KB id=39 (crontab(5) 'uneven date' case) + ADR-001: leading '*' of `*/2`
        # keeps the star flag -> AND: Mondays on odd-numbered dates only.
        s = parse("0 0 */2 * MON")
        self.assertTrue(s.dom.star and not s.dow.star)
        r = runs("0 0 */2 * MON", "UTC", "2026-01-01T00:00:00+00:00", 6)
        self.assertEqual([x.local.date() for x in r],
                         [datetime(2026, m, d).date() for m, d in
                          ((1, 5), (1, 19), (2, 9), (2, 23), (3, 9), (3, 23))])
        inst = {x.instant for x in r}
        # anti-cases: Monday 2026-01-12 (even date) and Tue 2026-01-13 (odd, not Mon)
        self.assertNotIn(datetime(2026, 1, 12, tzinfo=UTC), inst)
        self.assertNotIn(datetime(2026, 1, 13, tzinfo=UTC), inst)


class DSTOracleTest(unittest.TestCase):
    def test_spring_forward_fixed_shifts_to_jump(self):
        # ADR-002 / KB id=29,55: 02:00 NY 2026-03-08 does not exist -> 03:00-04:00
        # at the jump instant, gap_shifted, nominal 02:00; neighbours unaffected.
        r = runs("0 2 * * *", NY, "2026-03-07T00:00:00+00:00", 3)
        self.assertEqual([(x.local.isoformat(), x.instant.isoformat(), x.dst)
                          for x in r],
                         [("2026-03-07T02:00:00-05:00", "2026-03-07T07:00:00+00:00", None),
                          ("2026-03-08T03:00:00-04:00", "2026-03-08T07:00:00+00:00",
                           "gap_shifted"),
                          ("2026-03-09T02:00:00-04:00", "2026-03-09T06:00:00+00:00", None)])
        self.assertEqual(r[1].nominal, datetime(2026, 3, 8, 2, 0))

    def test_spring_forward_wildcard_no_dupes(self):
        # ADR-002/ADR-008: `* * * * *` walks the gap: 01:59->03:00 local, instants
        # strictly increasing minute by minute, no duplicate instant.
        r = runs("* * * * *", NY, "2026-03-08T06:50:00+00:00", 12)
        inst = [x.instant for x in r]
        self.assertEqual(len(set(inst)), 12)                      # no duplicate instants
        self.assertTrue(all(inst[i] + timedelta(minutes=1) == inst[i + 1]
                            for i in range(11)))                 # strictly increasing
        self.assertEqual(inst[8], datetime(2026, 3, 8, 6, 59, tzinfo=UTC))
        self.assertEqual(inst[9], datetime(2026, 3, 8, 7, 0, tzinfo=UTC))
        self.assertEqual(r[9].local.strftime("%H:%M"), "03:00")   # the gap jumped over 02:xx
        self.assertTrue(all(x.dst is None for x in r))            # wildcard: skipped, not marked

    def test_fall_back_fixed_once_ambiguous_first(self):
        # ADR-003 / KB id=55: `30 1 * * *` lists the ambiguous 01:30 exactly once,
        # the earlier (fold=0) pass; the next day is ordinary.
        r = runs("30 1 * * *", NY, "2026-11-01T00:00:00-04:00", 2)
        self.assertEqual((r[0].local.isoformat(), r[0].instant.isoformat(), r[0].dst),
                         ("2026-11-01T01:30:00-04:00", "2026-11-01T05:30:00+00:00",
                          "ambiguous_first"))
        self.assertEqual(r[1].local.date().isoformat(), "2026-11-02")
        self.assertIsNone(r[1].dst)

    def test_fall_back_wildcard_both_passes(self):
        # ADR-003: `* 1 * * *` emits both passes of 01:30, first then second,
        # instants strictly increasing.
        r = runs("* 1 * * *", NY, "2026-11-01T01:29:00-04:00", 2)
        self.assertEqual([(x.local.isoformat(), x.instant.isoformat(), x.dst) for x in r],
                         [("2026-11-01T01:30:00-04:00", "2026-11-01T05:30:00+00:00",
                           "ambiguous_first"),
                          ("2026-11-01T01:30:00-05:00", "2026-11-01T06:30:00+00:00",
                           "ambiguous_second")])
        self.assertLess(r[0].instant, r[1].instant)


class ZoneAndHorizonOracleTest(unittest.TestCase):
    def test_kathmandu_non_whole_hour_offset(self):
        # KB id=29/55: Asia/Kathmandu +05:45 renders :45; normal emit, dst None.
        r = runs("0 0 * * *", KTM, "2026-01-01T00:00:00+00:00", 3)
        self.assertEqual(r[0].local.isoformat(), "2026-01-02T00:00:00+05:45")
        self.assertEqual(r[0].instant.isoformat(), "2026-01-01T18:15:00+00:00")
        self.assertTrue(all(x.local.utcoffset() == timedelta(hours=5, minutes=45)
                            and x.dst is None for x in r))

    def test_unsatisfiable_empty_within_horizon(self):
        # ADR-008 / KB id=55: `0 0 30 2 *` -> zero occurrences inside HORIZON_DAYS.
        frm = datetime(2026, 1, 1, tzinfo=UTC)
        self.assertEqual(runs("0 0 30 2 *", "UTC", frm.isoformat(), 5), [])
        self.assertLess(frm + timedelta(days=HORIZON_DAYS),
                        datetime(2036, 1, 1, tzinfo=UTC))  # window is the 9-year bound

    def test_feb29_found_within_horizon(self):
        # ADR-008: `0 0 29 2 *` from 2026 finds 2028-02-29 (and 2032-02-29).
        r = runs("0 0 29 2 *", "UTC", "2026-01-01T00:00:00+00:00", 3)
        self.assertEqual([x.local.date().isoformat() for x in r],
                         ["2028-02-29", "2032-02-29"])

    def test_cli_unsatisfiable_exit0_and_message(self):
        # ADR-010/ADR-008: exit 0, prose line, no stderr (public CLI subprocess).
        p = subprocess.run([sys.executable, "-m", "cronx", "0 0 30 2 *",
                            "--from", "2026-01-01T00:00:00+00:00"],
                           capture_output=True, text=True, cwd=None)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stderr, "")
        self.assertIn("no runs found within 9 years of 2026-01-01T00:00:00+00:00",
                      p.stdout)


if __name__ == "__main__":
    unittest.main()
