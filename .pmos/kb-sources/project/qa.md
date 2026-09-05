# cronx — reviewer notes (qa namespace)

## cronx test strategy and gates
Suite: stdlib unittest, offline, `python3 -m unittest discover -v` from repo root (A-014;
tests/__init__.py exists so discovery works — without it discover collects ZERO tests and exits
5). One test file per task: test_py39_syntax, test_parse, test_macros, test_match, test_dst,
test_describe (+ tests/golden/descriptions.txt), test_tz_errors, test_cli, test_oracle,
test_monotonicity, test_differential, test_readme. The 3.9 guard (A-001) ast.parses every file
in cronx/ and tests/ with feature_version=(3,9). T-010 grep guard: no `match X:`, `case `,
datetime.UTC, tomllib, typing.Self, itertools.batched anywhere.

## cronx oracle cases (T-008, A-010) — the discriminating set
`0 0 13 * FRI` fires every 13th AND every Friday (OR rule, NOT Friday-the-13th).
`0 0 * * 0` ≡ `0 0 * * 7`. `0 0 */2 * MON` = odd dates AND Mondays (leading star -> AND; Vixie expands `*/2` from the
field minimum 1. crontab(5) worked case: "0 0 */2 * sun" = Sundays on uneven dates).
Spring-forward: 02:00 America/New_York 2026-03-08 does not exist — fixed shifts to 03:00 EDT
jump instant (gap_shifted), wildcard-minute `0 * * * *`-style drops it. Fall-back 2026-11-01:
wildcard emits both 01:30 passes, fixed emits first only. Asia/Kathmandu +05:45 non-whole-hour.
Unsatisfiable `0 0 30 2 *` -> zero occurrences, exit 0. Monotonicity (A-011): instants strictly
increasing across 3 zones x 5 years.

## cronx differential oracle (T-012, A-015)
Host has Debian vixie-cron `crontab -n <file>` — dry-run SYNTAX check, installs nothing
(verified against user's absent crontab). assert cronx accept/reject == crontab -n verdict over
a corpus, skipUnless(shutil.which("crontab")). KNOWN deliberate divergences asserted AS
divergences: descending ranges (cron accepts, cronx rejects, ADR-012) and `#` (cron accepts
`5#2` silently mis-reading, cronx rejects, ADR-007). crontab -n validates syntax ONLY — DST
runtime semantics and ADR-012's empty-set inference stay KB-backed (residual RSK-2).
