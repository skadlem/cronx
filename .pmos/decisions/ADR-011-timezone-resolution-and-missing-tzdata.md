# ADR-011: timezone resolution, and the missing tz database error path

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

`zoneinfo` reads the system tz database (`/usr/share/zoneinfo` on Linux) and raises
`ZoneInfoNotFoundError` both when the requested key does not exist and when there is no tz
database at all — the same exception for a user typo and for a broken container image
(KB: `python39-stdlib-constraints`). RSK-5 requires that neither becomes a traceback.
The same chunk warns that `available_timezones()` is slow and must not be on the hot path,
which rules out the obvious "did you mean" implementation.

A default for `--tz` also has to be chosen. The host's cron runs in the host's local zone,
which argues for local; but Python cannot name the local IANA zone portably —
`datetime.now().astimezone().tzinfo` yields a fixed offset with no DST rules, which would
make every answer in ADR-002/ADR-003 wrong.

## Options considered

- **A — default to the local zone, derived from `TZ` or the `/etc/localtime` symlink.** Pro:
  matches what the daemon does with no flag. Con: symlink-sniffing is a platform-specific
  guess, and the fixed-offset fallback silently disables the DST behaviour that is the
  tool's main value.
- **B — default to UTC and always print the zone.** Pro: deterministic, testable, no
  environment dependence, and the zone is on screen so a misreading is impossible. Con: the
  user must pass `--tz` to get their host's real answer.

## Decision

**B**, plus a two-step diagnosis of `ZoneInfoNotFoundError`:

- `--tz` defaults to `UTC`; the resolved zone name is printed in the run-list header and in
  the JSON `timezone` field, always, including the default.
- `ZoneInfo(name)` failing is caught once. cronx then tries `ZoneInfo("UTC")` — a single
  cheap probe, not `available_timezones()` — to tell the two causes apart:
  - probe succeeds → `cronx: error: unknown timezone 'Mars/Phobos': not in the system tz
    database` (exit 2)
  - probe also fails → `cronx: error: no system timezone database found: zoneinfo could not
    load 'UTC' (install the OS tzdata package or set PYTHONTZPATH)` (exit 2)

Both are raised as `CronxError` and rendered by the single stderr path of ADR-010. Zone
resolution happens once, before any search, so a bad zone fails before any output.

## Consequences

- Positive: RSK-5 becomes a one-line message and a fixed exit code, and the message tells a
  container maintainer exactly what is missing rather than showing a `zoneinfo` traceback.
- Positive: every run is reproducible from its own output — expression, `--from`, `--tz` and
  `-n` fully determine it, which is what makes T-008's oracle cases writable without
  patching the clock (R-014).
- Negative: a user who forgets `--tz` gets UTC answers for a host that is not on UTC. The
  header line naming the zone is the mitigation; a wrong-by-default local guess would be
  worse because it would be silent.
- Risks / follow-ups: the "install tzdata" advice names the OS package first because cronx
  is a no-pip tool by charter; the `PYTHONTZPATH` hint covers the non-root case.

## Pinned by

T-007: `--tz Mars/Phobos` exits 2 with the "unknown timezone" message; with `PYTHONTZPATH`
pointed at an empty directory (or `zoneinfo.reset_tzpath([])`) the same call exits 2 with
the "no system timezone database" message; neither writes a traceback or anything to stdout.
T-009 asserts the default zone is `UTC` and that it appears in both output formats.
