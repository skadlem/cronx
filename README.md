# cronx

Explain a cron expression and list its next run times — offline, standard
library only (Python 3.9+), no third-party packages, no network: it runs
unchanged on an air-gapped host. cronx answers what cron gotchas actually
cause: *when* does this schedule really fire, across DST, in *my* zone.
Semantics follow Vixie cron / crontab(5) per ADR-001…012.

## Install

Clone and run — there is nothing to install (an OS tz database is needed;
on stripped images `pip install tzdata`):

```
git clone <repo> cronx && cd cronx
python3 -m cronx '0 2 * * *' --tz America/New_York
```

## Usage

```
usage: cronx [-h] [--tz ZONE] [-n N] [--from ISO8601] [--json] EXPRESSION

Explain a cron expression and list its next run times. Five fields or an
@macro.

positional arguments:
  EXPRESSION      five-field cron expression or @macro, e.g. '0 2 * * *'

options:
  -h, --help      show this help message and exit
  --tz ZONE       IANA timezone name (default: UTC)
  -n N            number of run times to list (default: 5)
  --from ISO8601  reference instant; runs listed are strictly after it
                  (default: now). A value with no offset is read as wall clock
                  in --tz.
  --json          print a JSON object on stdout instead of text
```

## Examples

The charter's named case — 02:00 on 2026-03-08 does not exist in New York;
the fixed job runs at the jump, visibly annotated:

```
$ python3 -m cronx '0 2 * * *' --tz America/New_York --from 2026-03-07T00:00:00+00:00 -n 3
0 2 * * *
At 02:00.

next 3 runs in America/New_York:
  2026-03-07 02:00:00-05:00   2026-03-07T07:00:00+00:00
  2026-03-08 03:00:00-04:00   2026-03-08T07:00:00+00:00  (02:00 does not exist: DST gap, runs at the jump)
  2026-03-09 02:00:00-04:00   2026-03-09T06:00:00+00:00
```

```
$ python3 -m cronx '@reboot'
@reboot
At system startup (`@reboot` has no wall-clock schedule).
```

⚠ Anti-footgun, the Vixie day rule: with **both** day fields restricted
(neither written with a leading `*`), they combine as **OR**, not AND —
`0 0 13 * FRI` fires on *every 13th* **and** *every Friday*:

```
$ python3 -m cronx '0 0 13 * FRI' --from 2026-01-01T00:00:00+00:00 -n 3
0 0 13 * FRI
At 00:00, on day-of-month 13 or on Friday.

next 3 runs in UTC:
  2026-01-02 00:00:00+00:00   2026-01-02T00:00:00+00:00
  2026-01-09 00:00:00+00:00   2026-01-09T00:00:00+00:00
  2026-01-13 00:00:00+00:00   2026-01-13T00:00:00+00:00
```

## Exit codes (ADR-010)

| Code | Meaning |
|------|---------|
| 0 | Success — including an empty run list (`no runs found within 9 years`) |
| 1 | The expression is invalid (parse/range/unsupported-dialect error) |
| 2 | Invocation/environment wrong: unknown `--tz`, no tz database, unparseable `--from`, `-n < 1`, argparse usage errors |

Errors are one `cronx: error: ...` line on stderr in both output modes;
stdout stays empty, never a traceback (ADR-010).

## JSON output (`--json`)

Every key is always present; optionality is `null`, never omission. `dst` is
`null`, `gap_shifted`, `ambiguous_first`, or `ambiguous_second`;
`nominal_local` is set only for `gap_shifted`. Shown one-line for width
(real output uses `indent=2`; the 3-element `values` samples hold every
matching int):

```json
{"expression": "0 2 * * *", "macro": null, "reboot": false, "timezone": "America/New_York", "from": "2026-03-07T00:00:00+00:00", "description": "At 02:00.", "day_rule": "and", "fields": {"minute": {"text": "0", "star": false, "values": [0]}, "hour": {"text": "2", "star": false, "values": [2]}, "day_of_month": {"text": "*", "star": true, "values": [1, 2, 3]}, "month": {"text": "*", "star": true, "values": [1, 2, 3]}, "day_of_week": {"text": "*", "star": true, "values": [0, 1, 2]}}, "next": [{"local": "2026-03-07T02:00:00-05:00", "utc": "2026-03-07T07:00:00+00:00", "dst": null, "nominal_local": null}, {"local": "2026-03-08T03:00:00-04:00", "utc": "2026-03-08T07:00:00+00:00", "dst": "gap_shifted", "nominal_local": "2026-03-08T02:00:00"}]}
```

## Deliberate rejections

Rejected with a rewrite hint (the message always names the replacement):

| Form | Example | Why → rewrite | ADR |
|---|---|---|---|
| step without range | `5/10 * * * *` | cronie/croniter, not POSIX/Vixie → `5-59/10` | ADR-006 |
| `@every`/unknown macro | `@every 5m` | not a cron macro; error lists the supported set | ADR-007 |
| `L` / `W` / `#` | `0 0 15W * *`, `0 0 5#2 * *` | Quartz syntax; host cron reads `#...` as a comment | ADR-007 |
| `?` | `0 0 ? * MON` | Quartz syntax → write `*` | ADR-007 |
| descending range | `0 0 * * FRI-MON` | undefined by POSIX/crontab(5) → `5-7,0-1` for the wrap | ADR-012 |
| 6/7 fields | `0 0 0 13 2 ?` | Quartz/Spring seconds-or-year; a 6th `/path` token is a crontab *line* — pass the first five fields | ADR-007 |

## Semantics

- **Day rule (ADR-001):** AND when either day field starts with a literal
  `*`, OR when both are restricted; the test is the written first character,
  so `0 0 1-31 * MON` is OR while `0 0 */2 * MON` is AND (odd-date Mondays).
- **DST gap (ADR-002):** a fixed job in the skipped hour runs once at the
  jump (`gap_shifted` + `nominal_local`); a wildcard-minute/hour job is
  dropped, as Vixie does.
- **Fall-back (ADR-003):** an ambiguous wall clock is listed once
  (`ambiguous_first`) for fixed times, both passes for wildcard jobs.
- **Bounded search (ADR-008):** nine years covers every satisfiable schedule
  (Feb-29 gaps are ≤ 8 years); then `no runs found within 9 years of <from>`,
  exit 0.
- **Timezone (ADR-011):** default UTC; unknown zone vs missing tz database
  are distinguished, both exit 2 before any output.
