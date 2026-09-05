import unittest

from cronx.parse import CronxError, parse

MIN_VALUES = frozenset(range(0, 60))


class ElementFormsTest(unittest.TestCase):
    def test_star_covers_full_range(self):
        s = parse("* * * * *")
        self.assertEqual(s.minute.values, MIN_VALUES)
        self.assertTrue(s.minute.star)

    def test_single_value(self):
        s = parse("5 * * * *")
        self.assertEqual(s.minute.values, frozenset({5}))
        self.assertFalse(s.minute.star)

    def test_range(self):
        s = parse("1-5 * * * *")
        self.assertEqual(s.minute.values, frozenset({1, 2, 3, 4, 5}))
        self.assertFalse(s.minute.star)

    def test_range_with_step(self):
        s = parse("0-59/15 * * * *")
        self.assertEqual(s.minute.values, frozenset({0, 15, 30, 45}))

    def test_star_with_step(self):
        s = parse("*/15 * * * *")
        self.assertEqual(s.minute.values, frozenset({0, 15, 30, 45}))
        self.assertTrue(s.minute.star)

    def test_step_larger_than_span_yields_start_only(self):
        s = parse("1-5/10 * * * *")
        self.assertEqual(s.minute.values, frozenset({1}))

    def test_comma_list(self):
        s = parse("0,15,30,45 * * * *")
        self.assertEqual(s.minute.values, frozenset({0, 15, 30, 45}))

    def test_field_text_preserved_verbatim(self):
        s = parse("*/15 * * * *")
        self.assertEqual(s.minute.text, "*/15")


class StarFlagTest(unittest.TestCase):
    """ADR-001: Field.star is a textual first-character test, never derived
    from the value set."""

    def test_leading_star_sets_flag_even_with_trailing_literal(self):
        s = parse("* * */2,5 * *")
        self.assertTrue(s.dom.star)

    def test_leading_literal_clears_flag_even_with_trailing_star(self):
        s = parse("* * 5,* * *")
        self.assertFalse(s.dom.star)

    def test_full_range_is_not_normalised_to_star(self):
        s = parse("* * 1-31 * *")
        self.assertFalse(s.dom.star)
        self.assertEqual(s.dom.values, frozenset(range(1, 32)))

    def test_star_slash_step_sets_flag(self):
        s = parse("* * */2 * *")
        self.assertTrue(s.dom.star)


class NameResolutionTest(unittest.TestCase):
    """ADR-005: names in month/day-of-week, including ranges/lists/step bases."""

    def test_month_name_case_insensitive(self):
        s = parse("* * * jan *")
        self.assertEqual(s.month.values, frozenset({1}))

    def test_dow_name_range(self):
        s = parse("* * * * MON-FRI")
        self.assertEqual(s.dow.values, frozenset({1, 2, 3, 4, 5}))

    def test_month_name_list(self):
        s = parse("* * * JAN,JUL *")
        self.assertEqual(s.month.values, frozenset({1, 7}))

    def test_dow_name_range_with_step(self):
        s = parse("* * * * MON-FRI/2")
        self.assertEqual(s.dow.values, frozenset({1, 3, 5}))

    def test_dow_seven_and_zero_both_mean_sunday(self):
        s7 = parse("* * * * 7")
        s0 = parse("* * * * 0")
        self.assertEqual(s7.dow.values, frozenset({0}))
        self.assertEqual(s0.dow.values, frozenset({0}))

    def test_name_rejected_in_minute_field(self):
        with self.assertRaises(CronxError) as ctx:
            parse("MON * * * *")
        self.assertIn("minute", ctx.exception.message)
        self.assertIn("MON", ctx.exception.message)
        self.assertEqual(ctx.exception.code, 1)

    def test_name_rejected_in_day_of_month_field(self):
        with self.assertRaises(CronxError) as ctx:
            parse("* * MON * *")
        self.assertIn("day-of-month", ctx.exception.message)


class BareStepRejectionTest(unittest.TestCase):
    """ADR-006 (revised): bare a/s is rejected, not accepted as a-max/s."""

    def test_bare_step_in_minute_rejected_with_rewrite_hint(self):
        with self.assertRaises(CronxError) as ctx:
            parse("5/10 * * * *")
        msg = ctx.exception.message
        self.assertIn("minute", msg)
        self.assertIn("5/10", msg)
        self.assertIn("5-59/10", msg)
        self.assertEqual(ctx.exception.code, 1)

    def test_bare_step_in_day_of_month_rejected(self):
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 5/10 * *")
        self.assertIn("day-of-month", ctx.exception.message)

    def test_step_zero_rejected(self):
        with self.assertRaises(CronxError):
            parse("*/0 * * * *")


class DescendingRangeTest(unittest.TestCase):
    """ADR-012: descending/wrap-around ranges are rejected with a rewrite hint."""

    def test_descending_numeric_hour_range_rejected(self):
        with self.assertRaises(CronxError) as ctx:
            parse("0 22-2 * * *")
        msg = ctx.exception.message
        self.assertIn("hour", msg)
        self.assertIn("22-2", msg)
        self.assertIn("22-23,0-2", msg)

    def test_descending_minute_range_rejected(self):
        with self.assertRaises(CronxError):
            parse("30-10 * * * *")

    def test_descending_name_range_rejected(self):
        with self.assertRaises(CronxError) as ctx:
            parse("* * * * FRI-MON")
        self.assertIn("FRI-MON", ctx.exception.message)

    def test_descending_month_name_range_rejected(self):
        with self.assertRaises(CronxError):
            parse("* * * NOV-FEB *")

    def test_ascending_wrap_rewrite_is_accepted(self):
        s = parse("0 22-23,0-2 * * *")
        self.assertEqual(s.hour.values, frozenset({22, 23, 0, 1, 2}))

    def test_ascending_dow_list_equivalent_is_accepted(self):
        s = parse("* * * * FRI,SAT,SUN,MON")
        self.assertEqual(s.dow.values, frozenset({5, 6, 0, 1}))


class RangeValidationTest(unittest.TestCase):
    def test_minute_out_of_range_high(self):
        with self.assertRaises(CronxError) as ctx:
            parse("99 * * * *")
        self.assertIn("minute", ctx.exception.message)
        self.assertIn("0-59", ctx.exception.message)
        self.assertIn("99", ctx.exception.message)

    def test_day_of_month_zero_rejected(self):
        with self.assertRaises(CronxError) as ctx:
            parse("* * 0 * *")
        self.assertIn("1-31", ctx.exception.message)

    def test_day_of_month_32_rejected(self):
        with self.assertRaises(CronxError):
            parse("* * 32 * *")

    def test_month_zero_rejected(self):
        with self.assertRaises(CronxError):
            parse("* * * 0 *")

    def test_month_13_rejected(self):
        with self.assertRaises(CronxError):
            parse("* * * 13 *")

    def test_dow_8_rejected(self):
        with self.assertRaises(CronxError):
            parse("* * * * 8")


class FieldCountTest(unittest.TestCase):
    def test_wrong_field_count_reported(self):
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 * * * *")
        self.assertIn("5 fields", ctx.exception.message)
        self.assertIn("6", ctx.exception.message)
        self.assertEqual(ctx.exception.code, 1)

    def test_crontab_line_gets_the_command_hint(self):
        # ADR-007 amendment: token 6 shaped like a command -> say so, don't blame Quartz.
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 13 * FRI /usr/bin/backup")
        msg = ctx.exception.message
        self.assertIn("crontab LINE", msg)
        self.assertNotIn("Quartz", msg)

    def test_six_field_quartz_year_still_blames_quartz(self):
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 2 * * 2026")
        self.assertIn("Quartz", ctx.exception.message)


class WhitespaceTest(unittest.TestCase):
    """Architecture §2: fields collapse str.split()-style."""

    def test_leading_trailing_and_double_spaces_parse(self):
        s = parse("  0  0 *  *  * \t")
        self.assertEqual(s.minute.values, frozenset({0}))
        self.assertTrue(s.hour.star)


if __name__ == "__main__":
    unittest.main()
