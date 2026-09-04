# ADR-006: reject the `a/s` step-without-range form

Date: 2026-09-04 | Revised: 2026-09-04 (GATE 1) | Decider: architect, revised by user at GATE 1
Status: accepted

## Revision note (read this first)

The original ADR-006 decided to ACCEPT `a/s` as `a-max/s`. It rested on a KB claim that the
form "is present in Vixie". **That claim was false and has been corrected.** The coordinator
probed the cron actually installed on this host and the form is rejected outright:

```
$ printf '5/10 * * * * /bin/true\n' > c; crontab -n c
"c":0: bad minute
$ printf '0 0 5/10 * * /bin/true\n' > c; crontab -n c
"c":0: bad day-of-month
```

(`cron 3.0pl1-200ubuntu1`, Debian vixie-cron; `crontab -n` is a dry-run syntax check that
installs nothing. KB: `cron-live-oracle-probe`.) The decision is reversed on the evidence.
The id is not superseded because nothing was ever built against the old decision.

## Context

POSIX defines no step syntax at all; steps (`*/s`, `a-b/s`) are a Vixie extension. The bare
`a/s` form — a start value with a step and no explicit range — is a further extension found
in **cronie and croniter, but not in Debian vixie-cron**, which is the reference
implementation for this project and the cron a user's crontab on this host would actually
run under. R-001 lists the forms to parse; R-010 requires non-POSIX extensions to be
rejected with a precise error rather than guessed at.

## Options considered

- **A — reject `a/s`.** Pro: matches the reference implementation exactly; the brief asks for
  POSIX/Vixie semantics and this form is in neither. Consistent with how ADR-007 already
  handles `L`, `W`, `#`, `?` and `@every`: name the dialect rather than silently coping.
  Con: someone carrying a cronie or croniter expression gets an error instead of an answer.
- **B — accept as `a-max/s`, as a documented deviation.** Pro: friendlier to cronie/croniter
  users. Con: cronx would confidently explain an expression that the host's own cron rejects
  at install time — telling the user when a job will run when in fact it will never be
  accepted. For a tool whose purpose is preventing confident wrong answers, that is the
  worse failure.

## Decision

**A — reject.** `a/s` produces a `CronxError` naming the field and the token, and, per
ADR-007's pattern, naming the dialect it comes from so the user knows what to do:

```
cronx: error: minute: '5/10' is a cronie/croniter extension (step without a range),
       not supported by POSIX or Vixie cron; write '5-59/10' instead
```

The suggested rewrite is included because, unlike `L` or `W`, this form has an exact
five-field equivalent — the user can act on the error immediately.

The element table therefore has five shapes, not six:

| written | start | stop | step | field `star` contribution |
|---|---|---|---|---|
| `*`     | min | max | 1 | leading `*` |
| `a`     | a   | a   | 1 | — |
| `a-b`   | a   | b   | 1 | — |
| `a-b/s` | a   | b   | s | — |
| `*/s`   | min | max | s | leading `*` |

Validation, uniform across forms: `min <= start <= stop <= max` (no wrap-around — see
ADR-012), and `step >= 1` (`*/0` is an error). A step larger than the span is legal and
yields just the start value.

## Consequences

- Positive: cronx never explains a schedule that the reference cron would refuse to install.
- Positive: one fewer element shape in the parser, matcher and describer.
- Negative: cronie and croniter users hit an error. Mitigated by the rewrite hint in the
  message, which makes the fix mechanical.
- Follow-up: if cronx is ever pointed at a cronie host, this is the ADR to revisit; the
  change is one element shape and one error branch.

## Pinned by

T-002: `5/10 * * * *` and `0 0 5/10 * *` are both errors naming the field and the token, and
the message contains the `5-59/10` rewrite hint; `*/0` is an error; `1-5/10` -> {1};
`0-59/10` -> {0,10,20,30,40,50}. T-008 additionally asserts cronx's verdict on these matches
`crontab -n`'s verdict.
