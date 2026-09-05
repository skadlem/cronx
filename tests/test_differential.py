"""T-012 / A-015: differential verdict test against the host's real cron.

`crontab -n <file>` is a dry-run SYNTAX check (KB: cron-live-oracle-probe; verified
again 2026-09-05 — the user's crontab was absent before and after, and
test_crontab_n_installs_nothing re-pins that fact inside this suite). Expressions
are written only to temp files under /tmp; this test never installs or removes a
crontab.

CORPUS IS PINNED by A-015's note — not reviewer's choice:
  (a) every expression in the KB cron-live-oracle-probe transcript,
  (b) every 'Pinned by' expression in ADR-001/004/005/006/007/012,
  (c) boundary tokens per field (0,1,31,32,59,60 in each field; JAN/DEC/SUN/MON/7/8
      in the right fields).
107 cases >= the 40 minimum. For every case, cronx's accept/reject (parse succeeds
vs CronxError) must equal `crontab -n`'s (exit 0 vs non-zero) — EXCEPT the three
documented divergence classes, each asserted in its exact measured direction:
  * descending/wrapping ranges: cron ACCEPTS, cronx REJECTS (ADR-012),
  * '#' in a field: cron ACCEPTS via comment-truncation (`#2 ...` is discarded and
    dow reads 5), cronx REJECTS (ADR-007),
  * UPPERCASE/@-case macros: cronx ACCEPTS case-insensitively, cron's macro table
    is case-SENSITIVE and REJECTS (@YEARLY, @REBOOT, ... -> 'bad time
    specifier'). This direction is charter-mandated (R-003 'case-insensitively',
    ADR-004 pins '@reboot' AND '@REBOOT' parse) — it is a deliberate,
    coordinator-ruled (2026-09-05) divergence, not a bug.

`crontab -n` validates SYNTAX only (charter §7 RSK-2): no DST/runtime semantics
are asserted here — those are test_dst/test_oracle/test_monotonicity territory.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from cronx.parse import CronxError, parse

# (a) KB cron-live-oracle-probe + (b) ADR-001/004/005/006/007/012 'Pinned by' +
# (c) per-field boundary tokens. Values = verdict BOTH tools measured to agree on
# (2026-09-05, cron 3.0pl1-200ubuntu1, this host).
AGREE = {
    # --- KB transcript: names in ranges/lists/steps (man page said no; binary yes)
    "0 0 * * MON-FRI": "accept", "0 0 * JAN,JUL *": "accept",
    "0 0 * * MON-FRI/2": "accept", "0 0 * JAN-MAR *": "accept",
    # --- KB transcript: bare a/s rejected (ADR-006), dom/month 0 and 32/13 rejected
    "5/10 * * * *": "reject", "0 0 5/10 * *": "reject",
    "0 0 0 * *": "reject", "0 0 * 0 *": "reject",
    "0 0 32 * *": "reject", "0 0 * 13 *": "reject",
    # --- KB transcript: dow 0 and 7 legal, 8 not
    "0 0 * * 0": "accept", "0 0 * * 7": "accept", "* * * * 8": "reject",
    # --- KB transcript: ?, L, 15W rejected; 4-field and 6-field rejected
    "0 0 ? * *": "reject", "0 0 ? * MON": "reject", "0 0 L * *": "reject",
    "0 0 15W * *": "reject", "* * * *": "reject", "0 0 2 * * *": "reject",
    # --- ADR-001 pinned
    "0 0 13 * FRI": "accept", "0 0 1-31 * MON": "accept", "0 0 */2 * MON": "accept",
    # --- ADR-004 pinned (lowercase; the @REBOOT arm lives in MACRO_CASE below)
    "@reboot": "accept",
    # --- ADR-005 pinned
    "MON-FRI": "reject", "mon-fri": "reject", "JAN,JUL": "reject",
    "0 0 * * mon-fri": "accept", "0 0 MON * *": "reject", "0 0 * MON *": "reject",
    "0 0 * * SUN": "accept",
    # --- ADR-006 pinned
    "*/0 * * * *": "reject", "1-5/10 * * * *": "accept", "0-59/10 * * * *": "accept",
    # --- ADR-007 pinned (# arms live in HASH_FORM below; 6-field rejected agrees)
    "@every 5m": "reject",
    # --- ADR-012 pinned ascending equivalents
    "0 22-23,0-2 * * *": "accept", "0 0 * * FRI,SAT,SUN,MON": "accept",
    # --- ADR-008/009/010 pinned extras (all agree)
    "0 0 30 2 *": "accept", "0 0 31 4 *": "accept", "0 0 29 2 *": "accept",
    "* * * * *": "accept", "*/2 * * * *": "accept", "5 * * * *": "accept",
    "0 0 * * *": "accept", "0 9,17 * * *": "accept", "5 9-17 * * *": "accept",
    "*/15 9-17 * * MON-FRI": "accept", "0-59/15 * * * *": "accept",
    "@yearly": "accept", "@annually": "accept", "@monthly": "accept",
    "@weekly": "accept", "@daily": "accept", "@midnight": "accept",
    "@hourly": "accept", "99 * * * *": "reject",
    # --- boundary tokens per field: minute 0/1/31/32/59/60, hour 0/1/23/24/31/60
    "0 * * * *": "accept", "1 * * * *": "accept", "31 * * * *": "accept",
    "32 * * * *": "accept", "59 * * * *": "accept", "60 * * * *": "reject",
    "0 1 * * *": "accept", "0 23 * * *": "accept", "0 24 * * *": "reject",
    "0 31 * * *": "reject", "0 32 * * *": "reject", "0 59 * * *": "reject",
    "0 60 * * *": "reject",
    # --- day-of-month 1/2/31/32/59/60 (0 -> above), month 1/5/12/13/31/32/59/60
    "0 0 1 * *": "accept", "0 0 2 * *": "accept", "0 0 31 * *": "accept",
    "0 0 59 * *": "reject", "0 0 60 * *": "reject",
    "0 0 * 1 *": "accept", "0 0 * 5 *": "accept", "0 0 * 12 *": "accept",
    "0 0 * 31 *": "reject", "0 0 * 32 *": "reject", "0 0 * 59 *": "reject",
    "0 0 * 60 *": "reject",
    # --- names in the right fields: JAN/DEC (month), SUN/MON/7/8 (dow)
    "0 0 * JAN *": "accept", "0 0 * DEC *": "accept", "0 0 * jan *": "accept",
    "0 0 * jan,jul *": "accept", "0 0 * * sun-fri": "accept",
    "0 0 * * 1": "accept", "0 0 * * 6": "accept", "0 0 * * 8": "reject",
    "0 0 * * MON": "accept", "0 0 * * SAT": "accept", "0 0 * * FRI": "accept",
    "0 0 * * JAN": "reject",  # a month name in the dow field — both reject
}

# ADR-012 (Pinned by / T-008 clause): descending ranges are a KNOWN INTENTIONAL
# divergence — cron ACCEPTS (wrap-around reading), cronx REJECTS naming the token.
ADR012_DESCENDING = ["0 22-2 * * *", "30-10 * * * *", "0 0 * * FRI-MON",
                     "0 0 * NOV-FEB *"]

# ADR-007: '#' inside a field. cron ACCEPTS `0 0 * * 5#2` only because '#' opens a
# comment and the rest of the line is discarded (KB live-oracle-probe); cronx
# REJECTS with the dialect-naming error. Divergence direction: cron accept /
# cronx reject, licensed by ADR-007.
ADR007_HASH_FORM = ["0 0 * * 5#2", "0 0 * * MON#2"]

# Coordinator ruling 2026-09-05 (third documented class): vixie's macro table is
# case-SENSITIVE (@YEARLY -> 'bad time specifier'), while cronx MUST accept every
# spelling — charter R-003 'case-insensitively' and ADR-004's pinned '@REBOOT'.
# Divergence direction: cronx ACCEPT / crontab REJECT, licensed by R-003 + ADR-004.
MACRO_CASE = ["@REBOOT", "@ReBoot", "@YEARLY", "@ANNUALLY", "@MONTHLY",
              "@WEEKLY", "@DAILY", "@MIDNIGHT", "@HOURLY"]


@unittest.skipUnless(shutil.which("crontab"),
                     "host has no crontab(1): no live oracle to diff against")
class DifferentialOracleTest(unittest.TestCase):
    """cronx verdict == `crontab -n` verdict, modulo the three ADR'd divergences."""

    @classmethod
    def setUpClass(cls):
        # Oracle sanity: if this crontab lacks -n (non-Debian cron), the whole
        # method is meaningless — detect and skip rather than fail the suite.
        if cls._cron_verdict("* * * * *") != "accept" or \
           cls._cron_verdict("61 * * * *") != "reject":
            raise unittest.SkipTest("`crontab -n` dry-run syntax check unavailable here")

    @staticmethod
    def _cronx_verdict(expr):
        try:
            parse(expr)
            return "accept"
        except CronxError:
            return "reject"

    @staticmethod
    def _cron_verdict(expr):
        """Syntax-check expr in a temp file under /tmp; NEVER touch any crontab."""
        fd, path = tempfile.mkstemp(prefix="cronx-diff-", dir="/tmp")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(expr + " /bin/true\n")
            r = subprocess.run(["crontab", "-n", path],
                               capture_output=True, text=True, timeout=15)
            return "accept" if r.returncode == 0 else "reject"
        finally:
            os.unlink(path)

    def _crontab_state(self):
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        return (r.returncode, r.stdout)

    def test_crontab_n_installs_nothing(self):
        """Pin the safety premise: -n is a dry run — user crontab unchanged."""
        before = self._crontab_state()
        self._cron_verdict("0 4 * * 0")
        self.assertEqual(self._crontab_state(), before,
                         "`crontab -n` changed the user's crontab — unsafe oracle")

    def test_corpus_size_meets_pinned_minimum(self):
        total = len(AGREE) + len(ADR012_DESCENDING) + len(ADR007_HASH_FORM) + len(MACRO_CASE)
        self.assertGreaterEqual(total, 40, "A-015 requires a 40-case minimum corpus")

    def test_agreement_with_host_cron(self):
        for expr, expected in sorted(AGREE.items()):
            with self.subTest(expr=expr):
                cronx_v = self._cronx_verdict(expr)
                cron_v = self._cron_verdict(expr)
                self.assertEqual(cronx_v, expected, f"cronx verdict moved for {expr!r}")
                self.assertEqual(cron_v, expected,
                                 f"divergence not licensed by any ADR for {expr!r}")

    def test_adr012_descending_ranges_diverge_by_design(self):
        """ADR-012: cron ACCEPTS, cronx REJECTS — assert the exact direction."""
        for expr in ADR012_DESCENDING:
            with self.subTest(expr=expr):
                self.assertEqual(self._cronx_verdict(expr), "reject")
                self.assertEqual(self._cron_verdict(expr), "accept")

    def test_adr007_hash_forms_diverge_by_design(self):
        """ADR-007: cron accepts 5#2 via '#' comment-truncation, cronx rejects."""
        for expr in ADR007_HASH_FORM:
            with self.subTest(expr=expr):
                self.assertEqual(self._cronx_verdict(expr), "reject")
                self.assertEqual(self._cron_verdict(expr), "accept")

    def test_uppercase_macros_diverge_charter_mandated(self):
        """R-003/ADR-004 case-insensitivity vs vixie's case-SENSITIVE macro table:
        cronx ACCEPT, crontab -n REJECT. Coordinator ruling 2026-09-05."""
        for expr in MACRO_CASE:
            with self.subTest(expr=expr):
                self.assertEqual(self._cronx_verdict(expr), "accept")
                self.assertEqual(self._cron_verdict(expr), "reject")

    def test_temp_files_never_escape_tmp(self):
        """The probe writes only /tmp/cronx-diff-* files and cleans them up."""
        self._cron_verdict("@daily")
        leftovers = [f for f in os.listdir("/tmp") if f.startswith("cronx-diff-")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
