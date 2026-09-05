# cronx — implementer notes (backend namespace)

## cronx parser behaviour the tests pin (T-002/T-003)
Five element forms: `*`, `a`, `a-b`, `a-b/s`, `*/s` (bare `a/s` is REJECTED per revised
ADR-006 — message must carry the ascending rewrite hint, e.g. 5/10 -> "5-59/10"). Step larger
than span yields start-only ({1} for 1-5/10). dow 7 folds to 0. Names resolve month/dow only;
a name in minute/dom/hour errors naming field+token. Descending ranges rejected with hint
(22-2 -> "22-23,0-2"). Field count != 5 -> error message contains "5 fields" and the count
given. Macros matched first, case-insensitive, against the WHOLE expression; non-@reboot macros
rewrite to five-field text and parse normally. Field.text preserves the verbatim token text —
tests assert `.star` and `.text` exactly (ADR-001 invariant).

## cronx CLI output contract (T-009, architecture §4)
Text: expression line, description line, blank, "next N runs in <zone>:", two-space-indented
rows "<local iso with offset>   <utc iso +00:00>" plus ADR annotation suffixes (gap_shifted ->
"(HH:MM does not exist: DST gap, runs at the jump)"; ambiguous first/second pass). Empty list ->
"no runs found within 9 years of <from>". --json: single object, json.dumps indent=2, ALL keys
always present (null for absent), fields key names day_of_month/day_of_week, values sorted ints.
Errors: stdout empty, one line "cronx: error: ..." on stderr, exit 1 expression / 2 invocation
(bad tz, bad --from, -n < 1, argparse). --from without offset = wall clock in --tz, exclusive.

## cronx conventions
stdlib-only, no third-party imports anywhere incl. tests. frozen dataclasses, Tuple/FrozenSet
typing generics (3.9 floor — no PEP 604 unions, no match/case, no datetime.UTC). No logging,
no caching, no available_timezones(). One Element triple covers all five accepted forms
(2026-09-05: was "six" pre-ADR-006-reversal) — no per-field
parser classes. Tests are plain unittest, one file per task (tests/test_<area>.py), run with
python3 -m unittest tests.test_<area> -v.
