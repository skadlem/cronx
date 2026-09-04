# ADR-012: reject descending / wrap-around ranges (`22-2`, `FRI-MON`)

Date: 2026-09-04 | Decider: architect (coordinator-authored), approved by user at GATE 1
Status: accepted
Supersedes:

## Context

No earlier ADR covered ranges whose start exceeds its stop. ADR-006's validation line
mentioned "no wrap-around, so `22-2` is an error" in passing, but the case never got its own
rationale — and the KB chunk it would have rested on was wrong, asserting that "Vixie
requires a <= b (no wrap-around)".

**Measurement contradicts that.** The cron installed on this host accepts all of these
(`cron 3.0pl1-200ubuntu1`, via `crontab -n`, which installs nothing):

```
ACCEPT  0 22-2 * * *      ACCEPT  30-10 * * * *
ACCEPT  0 0 * * FRI-MON   ACCEPT  0 0 * NOV-FEB *
```

So a descending range is **accepted at parse time** by the reference implementation. The KB
chunk has been corrected (`cron-live-oracle-probe`, `cron-field-semantics`).

What it *means* at runtime could not be observed here: `crontab -n` only validates syntax,
and running the daemon to watch a job fire is out of scope. The strong prior is that it
matches nothing. Vixie's range expansion is a simple ascending loop —
`for (i = num1; i <= num2; i += step) set_element(...)` — whose body never executes when
`num1 > num2`, leaving the field's bitmask empty and the entry unable to ever fire. That is
consistent with what we can see (no error at parse time, because `set_element` is never
called with an out-of-range value), but it is an **inference from the implementation's
shape, not a measurement.** crontab(5) on this host documents neither behaviour.

## Options considered

- **A — reject with a precise error.** Pro: cronx refuses exactly where the truth is
  unknowable to it and the real-world outcome is most likely a job that silently never runs.
  Con: deviates from the reference implementation, which accepts the syntax.
- **B — accept with wrap-around** (`22-2` -> 22,23,0,1,2). Pro: matches what a user writing
  `22-2` almost certainly intends, and matches Quartz. Con: cronx would print a confident,
  plausible schedule for an expression that the host's own cron most likely never runs. This
  is precisely the silent-wrong-answer failure the tool exists to prevent, and it would be
  cronx inventing semantics no cited authority gives it.
- **C — accept and report an empty schedule.** Pro: most literal reproduction of the inferred
  Vixie behaviour. Con: rests entirely on the unverified inference; if the inference is wrong,
  cronx reports "never runs" about a schedule that in fact runs.

## Decision

**A — reject**, with an error naming the field, the token, and the ambiguity:

```
cronx: error: hour: '22-2' is a descending range; cron accepts it but its meaning is
       not defined by POSIX or documented by crontab(5) (it most likely matches nothing).
       Write '22-23,0-2' if you meant the wrap-around.
```

This is a **deliberate deviation from the reference implementation**, which is why it is an
ADR: cronx is deliberately stricter than the cron it models. The justification is the
charter's purpose (§1) — cronx exists so that a reader is not confidently misled — and A is
the only option that does not require cronx to assert something it cannot support. B and C
both make a claim about runtime behaviour that no authority available here can back.

The rewrite hint matters: a user who meant the wrap can express it exactly, in a form both
crons agree on.

## Consequences

- Positive: cronx never guesses at undocumented semantics; every schedule it explains is one
  where POSIX, Vixie and cronx agree.
- Positive: the check is one comparison in the shared element validator (`start <= stop`),
  covering numeric and name ranges (`FRI-MON` normalises to 5-1) in one place.
- Negative: cronx rejects a line that the user's crontab will happily install. The error says
  so explicitly rather than implying the line is malformed.
- Follow-up: if the empty-set inference is ever confirmed against a running daemon, option C
  becomes defensible and this ADR can be superseded — the change is one branch.

## Pinned by

T-002: `0 22-2 * * *`, `30-10 * * * *`, `0 0 * * FRI-MON`, `0 0 * NOV-FEB *` are each an
error naming the field and the token, and the message carries the rewrite hint; the
ascending equivalents `0 22-23,0-2 * * *` and `0 0 * * FRI,SAT,SUN,MON` are accepted.
T-008 records this as a KNOWN, INTENTIONAL divergence from `crontab -n` (cron accepts, cronx
rejects) so the differential test asserts the divergence rather than flagging it.
