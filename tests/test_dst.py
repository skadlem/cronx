"""T-005: zone resolution (ADR-011), spring-forward gap policy (ADR-002),
fall-back ambiguity (ADR-003), monotone emission (ADR-008/RSK-4). All pinned
datetimes via explicit --from-style references — never now().
"""
import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from cronx.occurrences import Occurrence, next_runs, resolve, resolve_zone
from cronx.parse import CronxError, parse

NY = ZoneInfo("America/New_York")
LH = ZoneInfo("Australia/Lord_Howe")
UTC = timezone.utc


class ResolveZoneTest(unittest.TestCase):
    # ADR-011 error paths. Message substring asserted per the ADR text;
    # the exact ZoneInfo repr wording is pinned by T-007 (CLI level).

    def test_valid_zone(self):
        self.assertEqual(str(resolve_zone("America/New_York")), "America/New_York")
        self.assertEqual(str(resolve_zone("UTC")), "UTC")

    def test_unknown_zone_code_2(self):
        with self.assertRaises(CronxError) as ctx:
            resolve_zone("Not/AZone")
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("unknown timezone 'Not/AZone'", ctx.exception.message)

    def test_message_names_unknown_timezone(self):
        try:
            resolve_zone("Mars/Phobos")
            self.fail("expected CronxError")
        except CronxError as exc:
            self.assertIn("unknown timezone", exc.message)


class GapTest(unittest.TestCase):
    # ADR-002: America/New_York 2026-03-08, 02:00->03:00 EDT jump at 07:00Z.

    def test_fixed_minute_gap_shifted_to_jump(self):
        occs = resolve(datetime(2026, 3, 8, 2, 0), NY, wildcard=False)
        self.assertEqual(len(occs), 1)
        o = occs[0]
        self.assertEqual(o.instant, datetime(2026, 3, 8, 7, 0, tzinfo=UTC))
        self.assertEqual(o.local, datetime(2026, 3, 8, 3, 0, tzinfo=NY))
        self.assertEqual(o.dst, "gap_shifted")
        self.assertEqual(o.nominal, datetime(2026, 3, 8, 2, 0))

    def test_half_hour_gap_candidate_hits_same_jump(self):
        # Integer-second search, no float residue: 02:30 -> exactly 07:00Z.
        o = resolve(datetime(2026, 3, 8, 2, 30), NY, wildcard=False)[0]
        self.assertEqual(o.instant, datetime(2026, 3, 8, 7, 0, tzinfo=UTC))
        self.assertEqual(o.nominal, datetime(2026, 3, 8, 2, 30))

    def test_wildcard_drops_gap(self):
        self.assertEqual(resolve(datetime(2026, 3, 8, 2, 0), NY, wildcard=True), [])

    def test_lord_howe_thirty_minute_step(self):
        # Southern hemisphere: LH springs forward 2026-10-04, gap [02:00, 02:30)
        # with the jump at 2026-10-03 15:30Z — a 30-minute, not 60-minute, shift.
        o = resolve(datetime(2026, 10, 4, 2, 0), LH, wildcard=False)[0]
        self.assertEqual(o.instant, datetime(2026, 10, 3, 15, 30, tzinfo=UTC))
        self.assertEqual(o.local, datetime(2026, 10, 4, 2, 30, tzinfo=LH))
        self.assertEqual(o.local.utcoffset().total_seconds(), 11 * 3600)
        self.assertEqual(o.nominal, datetime(2026, 10, 4, 2, 0))
        self.assertEqual(o.dst, "gap_shifted")

    def test_kathmandu_ordinary_no_transition(self):
        # +05:45 offsets on the same resolution path (R-007), no DST: ordinary.
        occs = resolve(datetime(2026, 9, 15, 6, 30), ZoneInfo("Asia/Kathmandu"),
                       wildcard=False)
        self.assertEqual(len(occs), 1)
        self.assertIsNone(occs[0].dst)
        self.assertIsNone(occs[0].nominal)
        self.assertEqual(occs[0].instant, datetime(2026, 9, 15, 0, 45, tzinfo=UTC))


class AmbiguousTest(unittest.TestCase):
    # ADR-003: NY 2026-11-01, 01:00->02:00 repeats; 01:30 at 05:30Z and 06:30Z.

    def test_fixed_minute_single_first_fold(self):
        occs = resolve(datetime(2026, 11, 1, 1, 30), NY, wildcard=False)
        self.assertEqual(len(occs), 1)
        o = occs[0]
        self.assertEqual(o.instant, datetime(2026, 11, 1, 5, 30, tzinfo=UTC))
        self.assertEqual(o.local.utcoffset().total_seconds(), -4 * 3600)  # EDT, first pass
        self.assertEqual(o.dst, "ambiguous_first")
        self.assertIsNone(o.nominal)

    def test_wildcard_minute_both_passes_in_instant_order(self):
        occs = resolve(datetime(2026, 11, 1, 1, 30), NY, wildcard=True)
        self.assertEqual([o.dst for o in occs], ["ambiguous_first", "ambiguous_second"])
        self.assertLess(occs[0].instant, occs[1].instant)
        self.assertEqual(occs[1].instant, datetime(2026, 11, 1, 6, 30, tzinfo=UTC))


class NextRunsTest(unittest.TestCase):
    def test_gap_collapse_two_candidates_one_instant(self):
        # "0 2 * * *" and "30 2 * * *" are distinct wall clocks but the same
        # jump instant; emission stays strictly increasing so one run appears.
        s = parse("0,30 2 * * *")
        self.assertEqual(resolve(datetime(2026, 3, 8, 2, 0), NY, False)[0].instant,
                         resolve(datetime(2026, 3, 8, 2, 30), NY, False)[0].instant)
        runs = next_runs(s, NY, datetime(2026, 3, 8, 6, 0, tzinfo=UTC), 3)
        # both Mar 8 candidates resolve to 07:00Z; only one emission. From Mar 9
        # the two wall clocks are ordinary and real, so both appear (1 h later).
        self.assertEqual([r.instant for r in runs],
                         [datetime(2026, 3, 8, 7, 0, tzinfo=UTC),
                          datetime(2026, 3, 9, 6, 0, tzinfo=UTC),
                          datetime(2026, 3, 9, 6, 30, tzinfo=UTC)])
        self.assertEqual(runs[0].dst, "gap_shifted")
        self.assertIsNone(runs[1].dst)
        self.assertIsNone(runs[2].dst)

    def test_wildcard_gap_hour_absent_from_run_list(self):
        s = parse("*/30 * * * *")  # wildcard minute -> gap drops, ambiguity doubles
        runs = next_runs(s, NY, datetime(2026, 3, 8, 5, 0, tzinfo=UTC), 6)
        local_hours = [r.local.replace(tzinfo=None) for r in runs]
        self.assertLess(datetime(2026, 3, 8, 1, 30), max(local_hours))
        for r in runs:
            self.assertFalse(r.local.date() == date(2026, 3, 8)
                             and datetime(2026, 3, 8, 2, 0) <= r.local.replace(tzinfo=None)
                             < datetime(2026, 3, 8, 3, 0))
        inst = [r.instant for r in runs]
        self.assertEqual(inst, sorted(inst))
        self.assertEqual(len(set(inst)), len(inst))

    def test_fixed_vs_wildcard_on_fold_day(self):
        fixed = parse("30 1 * * *")
        wild = parse("* 1 * * *")
        after = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
        fr = next_runs(fixed, NY, after, 2)
        self.assertEqual([r.instant for r in fr],
                         [datetime(2026, 11, 1, 5, 30, tzinfo=UTC),
                          datetime(2026, 11, 2, 6, 30, tzinfo=UTC)])
        self.assertEqual(fr[0].dst, "ambiguous_first")
        self.assertIsNone(fr[1].dst)
        wr = next_runs(wild, NY, datetime(2026, 11, 1, 5, 29, tzinfo=UTC), 2)
        self.assertEqual([(r.instant, r.dst) for r in wr],
                         [(datetime(2026, 11, 1, 5, 30, tzinfo=UTC), "ambiguous_first"),
                          (datetime(2026, 11, 1, 6, 30, tzinfo=UTC), "ambiguous_second")])

    def test_monotonic_across_spring_transition(self):
        s = parse("* * * * *")
        runs = next_runs(s, NY, datetime(2026, 3, 8, 6, 55, tzinfo=UTC), 10)
        inst = [r.instant for r in runs]
        self.assertEqual(inst, sorted(inst))
        self.assertEqual(len(set(inst)), len(inst))
        self.assertGreater(inst[0], datetime(2026, 3, 8, 6, 55, tzinfo=UTC))

    def test_from_is_exclusive(self):
        s = parse("0 0 * * *")
        ref = datetime(2026, 1, 5, 5, 0, tzinfo=UTC)  # == 00:00 EST Jan 5 in NY
        runs = next_runs(s, NY, ref, 1)
        self.assertEqual(runs[0].instant, datetime(2026, 1, 6, 5, 0, tzinfo=UTC))

    def test_zone_string_accepted(self):
        runs = next_runs(parse("0 12 * * *"), "UTC",
                         datetime(2026, 1, 1, 0, 0, tzinfo=UTC), 1)
        self.assertEqual(runs[0].instant, datetime(2026, 1, 1, 12, 0, tzinfo=UTC))

    def test_reboot_schedule_raises_clean(self):
        with self.assertRaises(CronxError) as ctx:
            next_runs(parse("@reboot"), NY, datetime(2026, 1, 1, tzinfo=UTC), 1)
        self.assertEqual(ctx.exception.code, 2)


class OccurrenceShapeTest(unittest.TestCase):
    def test_frozen_dataclass_fields(self):
        self.assertTrue(Occurrence.__dataclass_params__.frozen)
        o = resolve(datetime(2026, 6, 1, 12, 0), NY, wildcard=False)[0]
        self.assertEqual(o.dst, None)
        self.assertEqual(o.nominal, None)
        self.assertEqual(o.local.tzinfo, NY)
        self.assertEqual(o.instant.tzinfo, UTC)


if __name__ == "__main__":
    unittest.main()
