"""T-003: macro table (ADR-004, R-003) and rejection of non-POSIX dialects
(ADR-007 incl. the 2026-09-05 crontab-line amendment, R-010)."""
import unittest

from cronx.parse import CronxError, parse

MACRO_EXPANSIONS = {
    "@yearly": {"minute": {0}, "hour": {0}, "dom": {1}, "month": {1}, "dow_star": True},
    "@annually": {"minute": {0}, "hour": {0}, "dom": {1}, "month": {1}, "dow_star": True},
    "@monthly": {"minute": {0}, "hour": {0}, "dom": {1}, "month": frozenset(range(1, 13)), "dow_star": True},
    "@weekly": {"minute": {0}, "hour": {0}, "dom_star": True, "month": frozenset(range(1, 13)), "dow": {0}},
    "@daily": {"minute": {0}, "hour": {0}, "dom_star": True, "month": frozenset(range(1, 13)), "dow_star": True},
    "@midnight": {"minute": {0}, "hour": {0}, "dom_star": True, "month": frozenset(range(1, 13)), "dow_star": True},
    "@hourly": {"minute": {0}, "hour_star": True, "dom_star": True, "month": frozenset(range(1, 13)), "dow_star": True},
}
ALL_MACRO_NAMES = ["@yearly", "@annually", "@monthly", "@weekly", "@daily",
                   "@midnight", "@hourly", "@reboot"]


class MacroTableTest(unittest.TestCase):
    def test_each_macro_expands_to_five_field_text(self):
        for name, expected in MACRO_EXPANSIONS.items():
            with self.subTest(macro=name):
                s = parse(name)
                self.assertEqual(s.macro, name)
                self.assertFalse(s.reboot)
                for fld in ("minute", "hour", "dom", "month", "dow"):
                    if fld + "_star" in expected:
                        self.assertTrue(getattr(s, fld).star, fld)
                        self.assertEqual(getattr(s, fld).text, "*")
                    if fld in expected:
                        self.assertEqual(getattr(s, fld).values, frozenset(expected[fld]))

    def test_macros_are_case_insensitive(self):
        s = parse("@DAILY")
        self.assertEqual(s.macro, "@daily")
        self.assertEqual(s.minute.values, frozenset({0}))
        self.assertEqual(s.hour.values, frozenset({0}))

    def test_macro_matched_against_whole_expression_only(self):
        with self.assertRaises(CronxError) as ctx:
            parse("@daily extra tokens here")
        self.assertIn("@daily", ctx.exception.message)
        self.assertEqual(ctx.exception.code, 1)

    def test_schedule_text_kept_as_given(self):
        self.assertEqual(parse("@WEEKLY").text, "@WEEKLY")
        self.assertEqual(parse(" 0 2 * * * ").text, " 0 2 * * * ")


class RebootMacroTest(unittest.TestCase):
    """ADR-004: @reboot is explained, not rejected; fields are unset."""

    def test_reboot_sets_flag_and_skips_fields(self):
        s = parse("@reboot")
        self.assertTrue(s.reboot)
        self.assertEqual(s.macro, "@reboot")
        self.assertIsNone(s.minute)

    def test_reboot_case_insensitive(self):
        s = parse("@REBOOT")
        self.assertTrue(s.reboot)
        self.assertEqual(s.macro, "@reboot")


class UnknownMacroTest(unittest.TestCase):
    def test_every_rejected_by_name(self):
        with self.assertRaises(CronxError) as ctx:
            parse("@every 5m")
        self.assertIn("@every", ctx.exception.message)
        self.assertEqual(ctx.exception.code, 1)

    def test_unknown_macro_lists_supported(self):
        with self.assertRaises(CronxError) as ctx:
            parse("@bogus")
        for name in ALL_MACRO_NAMES:
            self.assertIn(name, ctx.exception.message)


class FieldCountRejectionTest(unittest.TestCase):
    """ADR-007: 6/7-field forms rejected by dialect name."""

    def test_six_field_quartz_seconds_form(self):
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 0 * * *")
        msg = ctx.exception.message
        self.assertIn("5 fields", msg)
        self.assertIn("Quartz", msg)
        self.assertEqual(ctx.exception.code, 1)

    def test_seven_field_quartz_year_form(self):
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 0 * * * 2026")
        msg = ctx.exception.message
        self.assertIn("7", msg)
        self.assertIn("Quartz", msg)

    def test_command_shaped_sixth_token_gets_crontab_line_hint(self):
        # ADR-007 amendment 2026-09-05: absolute, ./ and ~ paths are commands.
        for cmd in ("/usr/bin/backup", "./run.sh", "~/jobs.sh"):
            with self.subTest(cmd=cmd):
                with self.assertRaises(CronxError) as ctx:
                    parse("0 0 13 * FRI " + cmd)
                msg = ctx.exception.message
                self.assertIn("crontab LINE", msg)
                self.assertNotIn("Quartz", msg)

    def test_four_fields_get_count_without_quartz_blame(self):
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 * *")
        msg = ctx.exception.message
        self.assertIn("5 fields", msg)
        self.assertIn("4", msg)

    def test_empty_expression_rejected(self):
        with self.assertRaises(CronxError):
            parse("   ")


class ExtensionTokenRejectionTest(unittest.TestCase):
    """ADR-007: L/W/#/? rejected with a dialect-naming error, not guessed at."""

    def test_each_extension_token_named_with_dialect(self):
        cases = [("0 0 L * *", "L"), ("0 0 15W * *", "15W"),
                 ("0 0 * * MON#2", "MON#2"), ("0 0 ? * MON", "?")]
        for expr, token in cases:
            with self.subTest(expr=expr):
                with self.assertRaises(CronxError) as ctx:
                    parse(expr)
                msg = ctx.exception.message
                self.assertIn(token, msg)
                self.assertIn("Quartz", msg)
                self.assertEqual(ctx.exception.code, 1)

    def test_hash_error_notes_the_comment_trap(self):
        # KB live-oracle-probe: the host's cron reads '#' as a comment start.
        with self.assertRaises(CronxError) as ctx:
            parse("0 0 * * 5#2")
        self.assertIn("comment", ctx.exception.message)

    def test_names_containing_l_and_w_are_not_false_positives(self):
        # JUL contains L, WED contains W — the rejection is per-element-token,
        # not a raw substring scan of the field.
        s = parse("* * * JUL,AUG *")
        self.assertEqual(s.month.values, frozenset({7, 8}))
        s = parse("* * * * WED-SAT")
        self.assertEqual(s.dow.values, frozenset({3, 4, 5, 6}))


if __name__ == "__main__":
    unittest.main()
