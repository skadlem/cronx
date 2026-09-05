"""T-004: day rule (ADR-001), iter_local bounded search (ADR-008), strict
ascending + strictly-after semantics. Fixed datetimes only — never now().
"""
import unittest
from datetime import date, datetime

from cronx.match import HORIZON_DAYS, day_matches, iter_local
from cronx.parse import CronxError, parse


def _days(s, after, year, month):
    """Day-of-month numbers of every iter_local hit inside year-month."""
    out = []
    for dt in iter_local(s, after):
        if (dt.year, dt.month) == (year, month):
            out.append(dt.day)
        elif dt > datetime(year, month, 1):
            break
    return out


class DayRuleTest(unittest.TestCase):
    # ADR-001 discriminating set. Both day fields restricted -> OR; at least
    # one written with a leading '*' -> AND.

    def test_13th_or_friday_fires_on_both(self):
        # dom "13" and dow "FRI" are both restricted -> OR rule:
        # every 13th AND every Friday (crontab(5) worked case).
        s = parse("0 0 13 * FRI")
        after = datetime(2025, 12, 31, 23, 59)
        self.assertEqual(_days(s, after, 2026, 1), [2, 9, 13, 16, 23, 30])
        self.assertEqual(_days(s, after, 2026, 2), [6, 13, 20, 27])  # 13th is a Friday

    def test_dom_1_31_is_restricted_so_or(self):
        # "1-31" expands to every legal day but is NOT a star, so the OR rule
        # applies and the schedule fires every day of a matching month, not
        # just Mondays. The star-flag invariant, tested from the far end.
        s = parse("0 0 1-31 * MON")
        after = datetime(2025, 12, 31, 23, 59)
        self.assertEqual(_days(s, after, 2026, 1), list(range(1, 32)))
        self.assertNotEqual(_days(s, after, 2026, 1), _days(parse("0 0 * * MON"), after, 2026, 1))

    def test_star_dom_monday_ands(self):
        # dom "*" -> AND rule: Mondays only.
        s = parse("0 0 * * MON")
        after = datetime(2025, 12, 31, 23, 59)
        self.assertEqual(_days(s, after, 2026, 1), [5, 12, 19, 26])
        self.assertEqual(_days(s, after, 2026, 2), [2, 9, 16, 23])

    def test_step2_monday_is_star_so_ands_odd_dates(self):
        # "*/2" starts the Vixie step walk at the FIELD MINIMUM (1): {1,3,...,31},
        # and the leading '*' makes it unrestricted -> AND. Odd-date Mondays only
        # (crontab(5): "0 0 */2 * sun" runs every Sunday that's an uneven date).
        s = parse("0 0 */2 * MON")
        after = datetime(2025, 12, 31, 23, 59)
        self.assertEqual(_days(s, after, 2026, 1), [5, 19])
        self.assertEqual(_days(s, after, 2026, 2), [9, 23])

    def test_step2_sunday_uneven_date_worked_case(self):
        # The crontab(5) worked case itself, through day_matches directly:
        # 2026-02-01 is a Sunday on an uneven date -> matches.
        s = parse("0 0 */2 * sun")
        self.assertTrue(day_matches(s, date(2026, 2, 1)))     # Sun, day 1: odd -> match
        self.assertFalse(day_matches(s, date(2026, 2, 8)))    # Sun, day 8: even -> no match
        self.assertFalse(day_matches(s, date(2026, 2, 3)))    # Tue, day 3: odd but wrong dow

    def test_dow_zero_and_seven_equivalent(self):
        after = datetime(2025, 12, 31, 23, 59)
        self.assertEqual(_days(parse("0 0 * * 0"), after, 2026, 1),
                         _days(parse("0 0 * * 7"), after, 2026, 1))
        self.assertEqual(_days(parse("0 0 * * 7"), after, 2026, 1), [4, 11, 18, 25])

    def test_month_gates_the_day_rule(self):
        # "JUL" is restricted; dom "13" restricted; dow "*" star -> AND, so
        # only July 13ths fire.
        s = parse("0 0 13 JUL *")
        hits = list(iter_local(s, datetime(2026, 1, 1)))
        self.assertGreaterEqual(len(hits), 8)
        for dt in hits:
            self.assertEqual((dt.month, dt.day), (7, 13))


class HorizonTest(unittest.TestCase):
    # ADR-008: HORIZON_DAYS = 366 * 9; exhausted horizon = zero results, not an error.

    def test_horizon_constant(self):
        self.assertEqual(HORIZON_DAYS, 366 * 9)

    def test_february_30_never_fires(self):
        self.assertEqual(list(iter_local(parse("0 0 30 2 *"), datetime(2026, 1, 1))), [])

    def test_april_31_never_fires(self):
        self.assertEqual(list(iter_local(parse("0 0 31 4 *"), datetime(2026, 1, 1))), [])

    def test_feb_29_found_within_nine_years(self):
        # 0 0 29 2 * from 2026-01-01 finds 2028-02-29 (the satisfiable long-gap case).
        first = next(iter(iter_local(parse("0 0 29 2 *"), datetime(2026, 1, 1))))
        self.assertEqual(first, datetime(2028, 2, 29, 0, 0))


class IterLocalSemanticsTest(unittest.TestCase):
    def test_strictly_after_on_the_boundary(self):
        s = parse("0 0 * * MON")
        # 2026-01-05 00:00 is itself a Monday match -> excluded; next is the 12th.
        self.assertEqual(next(iter(iter_local(s, datetime(2026, 1, 5, 0, 0)))),
                         datetime(2026, 1, 12, 0, 0))

    def test_strictly_after_intraday(self):
        s = parse("*/30 * * * *")
        self.assertEqual(next(iter(iter_local(s, datetime(2026, 1, 5, 0, 30)))),
                         datetime(2026, 1, 5, 1, 0))

    def test_strictly_ascending(self):
        s = parse("*/30 8,9 * * *")
        it = iter_local(s, datetime(2026, 1, 5, 0, 0))
        seq = [next(it) for _ in range(10)]
        self.assertEqual(seq[:4], [datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 8, 30),
                                   datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 9, 30)])
        for a, b in zip(seq, seq[1:]):
            self.assertLess(a, b)

    def test_naive_datetimes_out(self):
        dt = next(iter(iter_local(parse("0 0 1 1 *"), datetime(2026, 1, 1))))
        self.assertIsNone(dt.tzinfo)


class RebootGuardTest(unittest.TestCase):
    def test_iter_local_rejects_reboot_cleanly(self):
        s = parse("@reboot")
        with self.assertRaises(CronxError) as ctx:
            list(iter_local(s, datetime(2026, 1, 1)))
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("reboot", ctx.exception.message.lower())


if __name__ == "__main__":
    unittest.main()
