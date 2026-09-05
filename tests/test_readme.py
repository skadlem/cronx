"""T-011 (A-012) — the README's documented contract must match the shipped CLI.

Mechanical, not aspirational: the usage line is taken from
`python3 -m cronx --help` via subprocess; the --json key sets are read from
the README's fenced json block and compared against cli.main() output driven
with capture; every `$ python3 -m cronx ...` example block is executed and its
stdout diffed against the README; exit codes {0,1,2} are each exercised once.
If README and CLI disagree, the CLI wins and this test fails.
"""
import contextlib
import io
import json
import os
import re
import shlex
import subprocess
import sys
import unittest

from cronx.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class UsageLineTest(unittest.TestCase):
    def test_help_usage_line_is_verbatim_in_readme(self):
        env = dict(os.environ, COLUMNS="80")
        proc = subprocess.run([sys.executable, "-m", "cronx", "--help"],
                              capture_output=True, text=True, cwd=ROOT, env=env)
        self.assertEqual(proc.returncode, 0)
        usage = proc.stdout.splitlines()[0]
        self.assertTrue(usage.startswith("usage: cronx "), usage)
        self.assertIn(usage, README)


class JsonSchemaTest(unittest.TestCase):
    """README's json block vs the real --json object: identical key names
    (five fields, their sub-keys, the four next-item keys, top level)."""

    @classmethod
    def setUpClass(cls):
        block = re.search(r"```json\n(.*?)\n```", README, re.S)
        assert block, "README has no fenced ```json block"
        cls.doc = json.loads(block.group(1))
        code, out, err = run_cli(["0 2 * * *", "--tz", "America/New_York",
                                  "--from", "2026-03-07T00:00:00+00:00",
                                  "-n", "2", "--json"])
        assert code == 0 and err == ""
        cls.real = json.loads(out)

    def test_top_level_keys_exact(self):
        self.assertEqual(list(self.real.keys()), list(self.doc.keys()))

    def test_field_keys_exact(self):
        self.assertEqual(list(self.real["fields"].keys()),
                         list(self.doc["fields"].keys()))
        for name, f in self.doc["fields"].items():
            self.assertEqual(list(self.real["fields"][name].keys()),
                             list(f.keys()), name)

    def test_next_item_keys_exact(self):
        self.assertEqual(list(self.real["next"][0].keys()),
                         list(self.doc["next"][0].keys()))

    def test_four_dst_values_documented(self):
        # the dst column names all four values of architecture §3.3
        # (backticked in prose or quoted in the json block both count)
        for value in ("gap_shifted", "ambiguous_first", "ambiguous_second"):
            self.assertRegex(README, r"[`\"]%s[`\"]" % value)
        # ... and lists all four, `null` first, in one sentence
        self.assertRegex(
            README,
            r"`null`,\s*`gap_shifted`,\s*`ambiguous_first`,\s*(?:or\s+)?`ambiguous_second`")
        self.assertIn("gap_shifted", [o["dst"] for o in self.real["next"]])


class ExitCodeTableTest(unittest.TestCase):
    ROW = re.compile(r"^\|\s*(\d)\s*\|", re.M)

    def test_table_rows_and_behaviour_agree(self):
        documented = set(int(m) for m in self.ROW.findall(README))
        self.assertEqual(documented, {0, 1, 2})
        exercised = {
            run_cli(["0 0 * * *", "--from", "2026-01-01T00:00:00+00:00"])[0],
            run_cli(["0 0 30 2 *", "--from", "2026-01-01T00:00:00+00:00"])[0],
            run_cli(["0 0 32 * *"])[0],
            run_cli(["0 0 * * *", "--tz", "Nowhere/Sville"])[0],
            run_cli(["0 0 * * *", "-n", "0", "--from",
                     "2026-01-01T00:00:00+00:00"])[0],
        }
        self.assertEqual(exercised, {0, 1, 2})


class ExampleBlockTest(unittest.TestCase):
    """Every `$ python3 -m cronx ...` example runs and prints what the
    README claims, byte for byte."""

    def test_examples_match_stdout(self):
        blocks = re.findall(r"```\n(\$ python3 -m cronx .*?)\n```", README, re.S)
        checked = 0
        for block in blocks:
            lines = block.splitlines()
            cmd = shlex.split(lines[0][2:])          # strip "$ "
            self.assertEqual(cmd[:3], ["python3", "-m", "cronx"], cmd)
            proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            expected = "\n".join(lines[1:]) + "\n"
            self.assertEqual(proc.stdout, expected, lines[0])
            self.assertEqual(proc.stderr, "", lines[0])
            self.assertEqual(proc.returncode, 0, lines[0])
            checked += 1
        self.assertGreaterEqual(checked, 3)          # gap, @reboot, OR-rule


if __name__ == "__main__":
    unittest.main()
