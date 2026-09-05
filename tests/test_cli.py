"""T-009 — the CLI contract: argparse surface, text and --json rendering,
exit codes (architecture §4 verbatim, ADR-010, ADR-004, ADR-011 defaults).

Every run pins --from so nothing depends on the clock (R-014). main() is
called directly with argv lists; stdout/stderr via contextlib. Errors: one
'cronx: error: ...' line on stderr, empty stdout, never a traceback.
"""
import contextlib
import io
import json
import unittest

from cronx.cli import main

NY = ["--tz", "America/New_York"]


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TextOutputTest(unittest.TestCase):
    def test_golden_text_block_exact(self):
        # architecture §4's worked example, reproduced byte for byte.
        code, out, err = run(["0 2 * * *"] + NY +
                             ["--from", "2026-03-07T00:00:00+00:00", "-n", "3"])
        self.assertEqual(err, "")
        self.assertEqual(code, 0)
        self.assertEqual(out, (
            "0 2 * * *\n"
            "At 02:00.\n"
            "\n"
            "next 3 runs in America/New_York:\n"
            "  2026-03-07 02:00:00-05:00   2026-03-07T07:00:00+00:00\n"
            "  2026-03-08 03:00:00-04:00   2026-03-08T07:00:00+00:00"
            "  (02:00 does not exist: DST gap, runs at the jump)\n"
            "  2026-03-09 02:00:00-04:00   2026-03-09T06:00:00+00:00\n"))

    def test_ambiguous_hour_suffixes(self):
        # ADR-003: a fixed time lists the ambiguous hour once (first pass);
        # only a wildcard minute/hour lists both passes.
        code, out, err = run(["30 1 * * *"] + NY +
                             ["--from", "2026-11-01T00:00:00-04:00", "-n", "1"])
        self.assertEqual(code, 0)
        self.assertIn("  2026-11-01 01:30:00-04:00   2026-11-01T05:30:00+00:00"
                      "  (first pass of an ambiguous hour)\n", out)
        self.assertNotIn("second pass", out)
        code, out, err = run(["* 1 * * *"] + NY +
                             ["--from", "2026-11-01T00:00:00-04:00", "-n", "2"])
        self.assertEqual(code, 0)
        self.assertIn("  2026-11-01 01:00:00-04:00   2026-11-01T05:00:00+00:00"
                      "  (first pass of an ambiguous hour)\n", out)
        self.assertIn("  2026-11-01 01:00:00-05:00   2026-11-01T06:00:00+00:00"
                      "  (second pass of an ambiguous hour)\n", out)

    def test_empty_run_list_prose(self):
        code, out, err = run(["0 0 30 2 *", "--from", "2026-01-01T00:00:00+00:00"])
        self.assertEqual(code, 0)                      # ADR-010: 0, not an error
        self.assertIn("no runs found within 9 years of 2026-01-01T00:00:00+00:00",
                      out)
        self.assertNotIn("next 5 runs", out)

    def test_default_tz_is_utc_and_visible(self):
        # ADR-011 / A-008: the zone name appears in text and JSON, always.
        code, out, _ = run(["0 0 * * *", "--from", "2026-01-01T12:00:00+00:00", "-n", "1"])
        self.assertEqual(code, 0)
        self.assertIn("next 1 runs in UTC:", out)
        _, out, _ = run(["0 0 * * *", "--from", "2026-01-01T12:00:00+00:00",
                         "-n", "1", "--json"])
        self.assertEqual(json.loads(out)["timezone"], "UTC")

    def test_reboot_text_has_no_run_list(self):
        code, out, _ = run(["@reboot", "--from", "2026-01-01T00:00:00+00:00"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "@reboot\nAt system startup "
                              "(`@reboot` has no wall-clock schedule).\n")


class JsonOutputTest(unittest.TestCase):
    def _obj(self, argv):
        code, out, err = run(argv)
        self.assertEqual((code, err), (0, ""))
        return json.loads(out)

    def test_every_key_always_present(self):
        o = self._obj(["0 2 * * *"] + NY +
                      ["--from", "2026-03-07T00:00:00+00:00", "-n", "2", "--json"])
        self.assertEqual(sorted(o), ["day_rule", "description", "expression",
                                     "fields", "from", "macro", "next",
                                     "reboot", "timezone"])
        self.assertEqual(sorted(o["fields"]),
                         ["day_of_month", "day_of_week", "hour", "minute", "month"])
        for name in o["fields"]:
            f = o["fields"][name]
            self.assertEqual(sorted(f), ["star", "text", "values"])
            self.assertEqual(f["values"], sorted(f["values"]))
            self.assertTrue(all(isinstance(v, int) for v in f["values"]))
        for entry in o["next"]:
            self.assertEqual(sorted(entry),
                             ["dst", "local", "nominal_local", "utc"])
        self.assertEqual(o["day_rule"], "and")
        self.assertIsNone(o["macro"])
        self.assertFalse(o["reboot"])
        self.assertEqual(o["description"], "At 02:00.")
        self.assertEqual(o["from"], "2026-03-07T00:00:00+00:00")
        self.assertTrue(o["next"][0]["utc"].endswith("+00:00"))

    def test_gap_entry_fields(self):
        o = self._obj(["0 2 * * *"] + NY +
                      ["--from", "2026-03-07T12:00:00+00:00", "-n", "1", "--json"])
        self.assertEqual(o["next"][0],
                         {"local": "2026-03-08T03:00:00-04:00",
                          "utc": "2026-03-08T07:00:00+00:00",
                          "dst": "gap_shifted",
                          "nominal_local": "2026-03-08T02:00:00"})

    def test_reboot_json_nulls_for_absent(self):
        o = self._obj(["@reboot", "--json", "--from", "2026-01-01T00:00:00+00:00"])
        self.assertTrue(o["reboot"])
        self.assertEqual(o["macro"], "@reboot")
        self.assertEqual(o["from"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(o["next"], [])
        self.assertIsNone(o["day_rule"])
        self.assertEqual(o["description"],
                         "At system startup (`@reboot` has no wall-clock schedule).")
        for name, f in o["fields"].items():
            self.assertIsNone(f, name)

    def test_json_indent_two_and_trailing_newline(self):
        code, out, _ = run(["0 0 * * *", "--from", "2026-01-01T00:00:00+00:00",
                            "-n", "1", "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(out.endswith("\n"))
        self.assertEqual(out, json.dumps(json.loads(out), indent=2,
                                         sort_keys=False) + "\n")


class FromArgumentTest(unittest.TestCase):
    def test_offsetless_from_is_wall_clock_in_tz(self):
        o1 = json.loads(run(["0 2 * * *"] + NY +
                            ["--from", "2026-03-07T00:00:00", "-n", "1",
                             "--json"])[1])
        self.assertEqual(o1["from"], "2026-03-07T05:00:00+00:00")  # EST -05:00

    def test_from_is_strictly_exclusive(self):
        # 2026-03-07T07:00Z == 02:00 EST — the from instant itself; excluded.
        o = json.loads(run(["0 2 * * *"] + NY +
                           ["--from", "2026-03-07T07:00:00+00:00",
                            "-n", "1", "--json"])[1])
        self.assertEqual(o["next"][0]["utc"], "2026-03-08T07:00:00+00:00")

    def test_bad_from_exits_2(self):
        code, out, err = run(["0 2 * * *", "--from", "nonsense"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith("cronx: error: "))
        self.assertNotIn("Traceback", err)


class ExitCodeTest(unittest.TestCase):
    def _assert_error(self, argv, code, prefix):
        rc, out, err = run(argv)
        self.assertEqual(rc, code)
        self.assertEqual(out, "")
        self.assertEqual(err.count("\n"), 1)
        self.assertTrue(err.startswith("cronx: error: "), err)
        self.assertIn(prefix, err)
        self.assertNotIn("Traceback", err)

    def test_invalid_expression_is_1(self):
        self._assert_error(["99 * * * *"], 1, "minute field: value out of range 0-59: '99'")

    def test_unknown_macro_is_1(self):
        self._assert_error(["@every"], 1, "unknown macro")

    def test_unknown_timezone_is_2(self):
        self._assert_error(["0 2 * * *", "--tz", "Mars/Phobos",
                            "--from", "2026-03-07T00:00:00+00:00"],
                           2, "unknown timezone 'Mars/Phobos'")

    def test_n_below_one_is_2(self):
        self._assert_error(["0 2 * * *", "-n", "0",
                            "--from", "2026-03-07T00:00:00+00:00"], 2, "-n")
        self._assert_error(["0 2 * * *", "-n", "-3",
                            "--from", "2026-03-07T00:00:00+00:00"], 2, "-n")

    def test_argparse_usage_errors_are_2(self):
        self._assert_error([], 2, "")
        self._assert_error(["0 2 * * *", "-n", "abc",
                            "--from", "2026-03-07T00:00:00+00:00"], 2, "")

    def test_errors_are_plain_text_even_with_json(self):
        code, out, err = run(["99 * * * *", "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertFalse(err.lstrip().startswith("{"))


class ModuleSurfaceTest(unittest.TestCase):
    def test_main_returns_int_never_raises_on_bad_input(self):
        for argv in (["* * * * *", "--from", "2026-01-01T00:00:00+00:00", "-n", "1"],
                     ["bad"], ["* * * * *", "--tz", "Nope/Nope",
                               "--from", "2026-01-01T00:00:00+00:00"]):
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                rc = main(argv)
            self.assertIn(rc, (0, 1, 2))

    def test_cli_is_the_only_module_touching_argparse_and_sys(self):
        import pathlib
        root = pathlib.Path(__file__).resolve().parent.parent / "cronx"
        for path in sorted(root.glob("*.py")):
            if path.name not in ("cli.py", "__main__.py"):
                src = path.read_text()
                self.assertNotIn("import argparse", src, path.name)
                self.assertNotIn("import sys", src, path.name)


if __name__ == "__main__":
    unittest.main()
