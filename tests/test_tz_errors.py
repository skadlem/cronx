"""T-007 — ADR-011's two ZoneInfoNotFoundError branches, pinned through the
CLI's exit-code dispatch (A-009, RSK-5).

Branch 1 (unknown zone name) is triggered normally. Branch 2 (missing tz
DATABASE) needs zoneinfo pointed at a nonexistent directory; the C
implementation caches loaded zones un-invalidate-ably, so the pin drives
zoneinfo's documented pure-Python class (zoneinfo._zoneinfo.ZoneInfo, which
exposes clear_cache) through cronx.occurrences' ZoneInfo global. Both the
TZPATH (zoneinfo.reset_tzpath, as ADR-011 prescribes) and the patch are
restored in tearDown so no other module sees mutated interpreter state.

Note: reset_tzpath([]) is a no-op (zoneinfo falls back to the system dirs),
so the simulation uses a path guaranteed not to exist.
"""
import contextlib
import io
import os
import tempfile
import unittest
import zoneinfo
import zoneinfo._zoneinfo
from zoneinfo import reset_tzpath

import cronx.occurrences as occurrences
from cronx.cli import main

NO_TZDB_PREFIX = "cronx: error: no system timezone database found"


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class UnknownTimezoneTest(unittest.TestCase):
    def test_unknown_zone_exits_2_before_any_output(self):
        code, out, err = _run(["0 2 * * *", "--tz", "Mars/Phobos",
                               "--from", "2026-03-07T00:00:00+00:00"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertTrue(err.startswith(
            "cronx: error: unknown timezone 'Mars/Phobos'"), err)
        self.assertEqual(err.count("\n"), 1)
        self.assertNotIn("Traceback", err)

    def test_absolute_path_key_is_unknown_not_missing_database(self):
        # zoneinfo raises ValueError for non-relative keys; ADR-011's
        # diagnosis must not misreport a typo as a broken tz database.
        code, out, err = _run(["0 2 * * *", "--tz", "/etc/shadow",
                               "--from", "2026-03-07T00:00:00+00:00"])
        self.assertEqual((code, out), (2, ""))
        self.assertIn("unknown timezone", err)
        self.assertNotIn(NO_TZDB_PREFIX, err)


class MissingTzDatabaseTest(unittest.TestCase):
    def setUp(self):
        self._orig_tzpath = list(zoneinfo.TZPATH)
        self._orig_class = occurrences.ZoneInfo
        nonexistent = os.path.join(tempfile.mkdtemp(), "no-such-tzdir")
        reset_tzpath([nonexistent])
        occurrences.ZoneInfo = zoneinfo._zoneinfo.ZoneInfo
        occurrences.ZoneInfo.clear_cache()

    def tearDown(self):
        reset_tzpath(self._orig_tzpath)
        occurrences.ZoneInfo = self._orig_class   # C class: no cache to clear

    def test_missing_database_exits_2_with_distinguishable_message(self):
        code, out, err = _run(["0 2 * * *", "--tz", "Europe/Amsterdam",
                               "--from", "2026-03-07T00:00:00+00:00"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")                       # never partial output
        self.assertEqual(err.count("\n"), 1)            # one line
        self.assertTrue(err.startswith("cronx: error: "), err)
        self.assertIn("no system timezone database found", err)
        self.assertNotIn("unknown timezone", err)       # distinguishable branch
        self.assertNotIn("Traceback", err)

    def test_default_utc_also_reports_missing_database(self):
        # Even --tz UTC cannot load: the probe itself is the failure, and it
        # is told as the database message, not as a zone-name complaint.
        code, out, err = _run(["0 2 * * *", "--from", "2026-03-07T00:00:00"])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("no system timezone database found", err)


if __name__ == "__main__":
    unittest.main()
