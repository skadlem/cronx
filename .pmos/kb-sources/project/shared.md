# cronx — shared project facts

## cronx goal and wedge
cronx is an offline CLI that explains one cron expression and lists its next N run times:
`cronx '<expr>' [--tz ZONE] [-n N] [--json]`. One English sentence + N correct instants, or a
precise error naming field and token. Built for SREs on air-gapped hosts where pip install and
browser paste are both unavailable. Out of scope: crontab files, daemon, plugins, library API
promise, i18n, seconds/year fields. See charter R-001..R-014.

## cronx hard constraints
Python 3.9 syntax floor, standard library ONLY (argparse, datetime, zoneinfo, json, re,
dataclasses, calendar, typing, unittest), no pip, no network at runtime or test time. Dev host
runs python3.14 and has NO 3.9 interpreter — 3.9 compat is guarded by ast.parse
(feature_version=(3,9)) tests (R-011, T-001) plus the reviewer's stdlib-API floor audit (T-010),
never by running 3.9. Tests must run offline via `python3 -m unittest discover` (needs
tests/__init__.py, which exists).

## cronx module map (five modules, ~600 LOC)
parse.py (text->Schedule; owns CronxError, Field, Element, Schedule, name+macro tables, ~180),
match.py (day rule + bounded naive-local iterator, ~90), occurrences.py (zone resolution + DST
policy + monotone dedupe, ~120), describe.py (English sentence, closed grammar, ~110),
cli.py (argparse, text/JSON render, the only module touching sys.exit, ~110), __main__.py
(3 LOC). Dependency direction acyclic: cli -> {parse,match,occurrences,describe};
occurrences -> {parse,match}; match -> parse; describe -> parse. parse imports nothing from the
package. Only occurrences imports zoneinfo.

## cronx glossary
"star flag" = Field.star, the ADR-001 OR-rule flag computed as field_text.startswith("*").
"day rule" = OR (not AND) of day-of-month and day-of-week when both restricted; AND when either
star flag is set. "gap" = spring-forward missing wall clock; "fold" = fall-back repeated wall
clock. "wildcard" = minute.star or hour.star (Vixie MIN_STAR|HR_STAR). "oracle" = the host's
`crontab -n` dry-run syntax checker (Debian vixie-cron) + KB domain chunks.
