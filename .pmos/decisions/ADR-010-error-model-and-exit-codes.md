# ADR-010: one error type, one stderr line, three exit codes

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

R-009 requires a precise error naming the field and the offending token, with a non-zero
exit and no traceback. The secondary user is a CI pipeline (charter §2), which needs the
exit code to distinguish "this crontab line is bad" — a lint failure worth blocking a merge
— from "cronx was called wrong or the host is missing tzdata", which is an infrastructure
problem. `argparse` already exits 2 for its own usage errors, so the numbering has to be
chosen around that rather than fight it.

## Options considered

- **A — 0 / 1 for everything non-zero.** Pro: minimal. Con: the CI consumer cannot tell a
  bad expression from a broken container image, which is the one thing it needs.
- **B — a code per error category** (bad field, bad range, unknown macro, unknown zone, …).
  Pro: maximally precise. Con: an unbounded table that becomes API surface for a tool whose
  charter promises no API stability; the message already carries the detail.
- **C — three codes split by *who is at fault*: the expression, the invocation, neither.**
  Pro: matches the two distinct consumers and leaves argparse's 2 in place. Con: "unknown
  timezone" lands under invocation rather than input, which needs stating.

## Decision

**C.** One exception type, `CronxError`, raised by the parser and the timezone layer with a
finished user-facing message; `cli.main()` catches it, writes one line, and returns its code.
Nothing else is caught — an unexpected traceback is a bug and is allowed to look like one.

| exit | meaning | cases |
|---|---|---|
| 0 | success | including an empty run list (`@reboot`, unsatisfiable schedule) |
| 1 | the EXPRESSION is invalid | bad element, out-of-range value, wrong field count, name in a numeric field, unknown macro, rejected extension (ADR-007) |
| 2 | the INVOCATION or the environment is wrong | unknown `--tz`, no tz database (ADR-011), unparseable `--from`, `-n` < 1, argparse usage errors |

stderr format — exactly one line, always prefixed, never a traceback:

```
cronx: error: <field-name> field: <problem>: '<token>'      when the fault is in a field
cronx: error: <problem>                                     otherwise
```

e.g. `cronx: error: minute field: value out of range 0-59: '99'`. On any error stdout stays
empty, including under `--json`: errors are plain text on stderr in both modes, so a
consumer parses stdout only after checking the exit code.

## Consequences

- Positive: a CI job can gate on `exit == 1` and alert on `exit == 2` without parsing prose.
- Positive: one raise site convention — the parser builds the whole sentence, so there is no
  message assembly in the CLI and no partial output before a failure.
- Negative: no machine-readable error object under `--json`. Deliberate: a second output
  schema for errors is scope the charter's wedge does not buy, and the exit code carries the
  category.
- Risks / follow-ups: if `--json` consumers later need structured errors, that is a new ADR
  adding a field, not a change to these codes.

## Pinned by

T-002 (field messages name field and token), T-003 (macro and extension messages),
T-009: exit codes for `'99 * * * *'` → 1, `--tz Mars/Phobos` → 2, `--from nonsense` → 2,
`'0 0 30 2 *'` → 0; and an assertion that stderr is one line with no `Traceback`.
