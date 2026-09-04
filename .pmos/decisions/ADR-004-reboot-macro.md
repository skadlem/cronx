# ADR-004: `@reboot` is explained, not rejected

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

R-003 commits to accepting the `@`-macros case-insensitively, `@reboot` among them.
`@reboot` has no wall-clock schedule at all — it fires when the daemon starts — so "the
next N run times" is undefined for it. The KB names this a decision point requiring an ADR
(KB: `cron-macros`).

The user for this tool is reading a crontab file they did not write. `@reboot` lines are
common and are perfectly valid crontab syntax.

## Options considered

- **A — reject it** with "`@reboot` has no schedule" and a non-zero exit. Pro: `next` is
  never empty-for-two-different-reasons. Con: tells an SRE that a valid, working line in
  their production crontab is invalid — the tool would be wrong about the one thing it
  claims to be right about.
- **B — explain it and emit zero occurrences**, exit 0. Pro: honest on both counts: the
  line is valid, and it has no run times. Con: `next: []` now has two possible causes
  (`@reboot`, and a satisfiable-looking schedule that never fires, e.g. `0 0 30 2 *`).

## Decision

**B.** `@reboot` parses successfully, sets `Schedule.reboot = True`, produces the fixed
sentence *"At system startup (`@reboot` has no wall-clock schedule)."*, emits an empty
run list, and exits 0. `-n`, `--from` and `--tz` are accepted and ignored.

To remove B's ambiguity, the JSON object carries a top-level `"reboot": true|false`, so a
CI consumer can tell `@reboot` apart from a schedule that matches nothing. The text output
distinguishes them in prose: the `@reboot` sentence versus
`no runs found within 9 years of <from>`.

## Consequences

- Positive: cronx never calls a valid crontab line invalid, which keeps the exit-code
  contract meaning what ADR-010 says it means (exit 1 = *the expression is wrong*).
- Positive: `reboot` is one boolean on the schedule and one branch in the CLI; no separate
  code path through matching or the timezone layer, which is never entered.
- Negative: a caller that only checks `len(next) > 0` treats `@reboot` as a dead schedule.
  Accepted — it is documented in the JSON schema, and the alternative is worse.
- Risks / follow-ups: none. If a future user wants "when did this host last boot", that is
  a different tool (charter §4: cronx never inspects the system).

## Pinned by

T-003: `@reboot` and `@REBOOT` both parse; exit code is 0; the run list is empty; `reboot`
is `true` in `--json`; the sentence matches the golden file entry (T-006).
