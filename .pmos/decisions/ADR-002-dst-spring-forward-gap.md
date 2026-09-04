# ADR-002: DST spring-forward — what to report for a wall clock that never happens

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

cronx enumerates local wall-clock matches and maps each to a real instant (R-007). On a
spring-forward day some wall clocks do not exist: `America/New_York` 2026-03-08 02:30 is
skipped. `zoneinfo` does NOT raise for a gap — it returns a nominal datetime carrying the
PRE-transition offset, so the only reliable detection is
`dt.astimezone(utc).astimezone(tz) != dt` (KB: `cron-dst-transitions`).

The same chunk records Vixie's behaviour: after a forward jump the daemon runs the
**non-wildcard** jobs that were scheduled in the skipped minutes, once each, at the moment
it wakes up after the jump; **wildcard** jobs are simply not run. Vixie's own test for
"wildcard" is `MIN_STAR | HR_STAR` — the minute or hour field was written with a leading
literal `*` — which is exactly the flag ADR-001 already stores.

## Options considered

- **A — drop every gap occurrence.** Pro: two lines of code, defensible ("that time never
  existed"). Con: silently omits a run the user's daemon really does perform, which is the
  exact failure mode cronx exists to prevent.
- **B — emit every gap occurrence at the nominal instant** (`dt@fold=0 → UTC`, i.e. 02:30
  becomes 03:30 local). Pro: no extra work. Con: not what cron does; `0 2 * * *` and
  `30 2 * * *` would appear to fire an hour apart when in reality both fire at the jump.
- **C — Vixie split: non-wildcard jobs at the post-jump instant, wildcard jobs dropped.**
  Pro: faithful to the daemon, and the wildcard test is a flag we already carry. Con: one
  extra branch plus a search for the transition instant.

## Decision

**C.** A schedule is *wildcard* iff `minute.star or hour.star` (ADR-001's flag). For a
naive local candidate detected as a gap:

- wildcard schedule → the occurrence is dropped;
- otherwise → one occurrence at the **clock-jump instant**: the earliest instant whose
  local time is ≥ the requested wall clock, found by a bounded binary search between
  `naive@fold=1 → UTC` (before the jump) and `naive@fold=0 → UTC` (after it). It is
  reported with `dst: "gap_shifted"` and the requested, non-existent wall clock alongside,
  so the user sees both what was written and what will actually run.

Several gap candidates on the same day collapse to the same instant; the emitter's
strictly-increasing-instant rule (ADR-008) drops the duplicates, which is also what Vixie
does — the job runs once.

## Consequences

- Positive: `0 2 * * *` in `America/New_York` across 2026-03-08 answers the charter's named
  case correctly, with the substitution visible rather than implied.
- Negative: the emitted local time differs from the expression's text; every output format
  must therefore carry the annotation, which fixes `dst` and `nominal_local` into the JSON
  schema (ADR-010 / architecture.md).
- Risks: the binary search assumes local time is non-decreasing in instant across the gap
  window, which holds for a forward transition; the fall-back case never reaches it.

## Pinned by

T-005 unit tests on `resolve()`; T-008 oracle case `0 2 * * *` / `--tz America/New_York`
around 2026-03-08 (run at 03:00 EDT, annotated) and `* * * * *` on the same day (02:00–02:59
absent, no annotation).
