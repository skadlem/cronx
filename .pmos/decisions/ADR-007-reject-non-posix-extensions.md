# ADR-007: reject 6/7-field forms and the `L` `W` `#` `?` `@every` extensions

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

Expressions that look like cron come from several incompatible dialects. Quartz and Spring
use six or seven fields (leading seconds, trailing year) and the extension characters `L`
(last), `W` (nearest weekday), `#` (nth weekday of month) and `?` (no specific value);
`@every 5m` is a Go/robfig invention. Crucially, Quartz also numbers day-of-week 1–7 for
SUN–SAT — one off from Vixie — so a six-field expression interpreted as five fields plus a
guess is not merely incomplete, it is *silently off by one day*.

R-010 requires these to be rejected with a precise error rather than guessed at.

## Options considered

- **A — best-effort: drop a leading seconds field, treat `?` as `*`, ignore `L`/`W`/`#`.**
  Pro: answers more inputs. Con: produces a confidently wrong schedule for the DOW
  off-by-one, which is precisely the failure mode the charter's success metric forbids
  ("never silently mis-explained").
- **B — reject with a generic parse error.** Pro: trivial; falls out of the field-count
  check and the element grammar. Con: "invalid day-of-week `MON#2`" leaves the user
  guessing whether they typoed or whether cronx is the wrong tool.
- **C — reject with a dialect-naming error.** Pro: the user learns in one line that their
  expression is a different grammar, so they stop debugging cronx. Con: a small table of
  recognised-but-unsupported tokens that must be kept honest.

## Decision

**C.** Detection happens in the parser, before element parsing, and produces exit 1
(ADR-010) with a message naming what was found and the dialect it belongs to:

- field count ≠ 5 (and not a macro) →
  `expected 5 fields (minute hour day-of-month month day-of-week), got 6 — 6- and 7-field
  forms with seconds or year are Quartz/Spring syntax, not POSIX cron`
  - Amendment 2026-09-05 (L-3 review): when the field count is exactly 6 and the sixth
    token starts with `/`, `~`, or a `$PATH`-style absolute/`./` path (the shape of a real
    command, not a Quartz year field), the message continues
    `; if your six tokens are a crontab LINE ('... /usr/bin/backup'), pass only the first
    five fields — the command is not part of the expression`. The Quartz diagnosis is
    printed only otherwise. Rationale: the charter's own named user holds a full crontab
    line, and this is its most likely first invocation; a wrong dialect name sends them to
    the wrong manual page. Detection is one startswith() test on token 6 — no command
    parsing, the non-goal in charter §4 stands.
- a field containing `L`, `W`, `#` or `?` →
  `day-of-week field: 'MON#2': the '#' extension (nth weekday of month) is Quartz syntax,
  not supported`
- `@every …` → `unknown macro '@every': supported macros are @yearly, @annually, @monthly,
  @weekly, @daily, @midnight, @hourly, @reboot`

The table is closed: any other unrecognised character falls through to the ordinary
per-element error, which names the field and the token.

## Consequences

- Positive: cronx is never wrong about a Quartz expression; it declines it by name. The
  off-by-one DOW trap cannot reach the output.
- Positive: the check is a substring scan plus a field count — no second grammar and no
  partial Quartz parser, so the rejection cannot drift into support.
- Negative: a user with a Quartz schedule gets no answer at all. Accepted: out of scope per
  charter §4, and a wrong answer costs more than no answer for the on-call reader.
- Risks / follow-ups: dialects not in the table (systemd calendar, e.g. `Mon *-*-* 02:00`)
  produce the generic field error rather than a named one. Acceptable — the field count and
  token are still reported.

## Pinned by

T-003: `0 0 2 * * *` (6 fields), `0 0 L * *`, `0 0 * * MON#2`, `0 0 ? * MON`, `0 0 15W * *`
and `@every 5m` each exit 1 with a message naming the offending token; no traceback on any
of them.

## Measurement added at GATE 1: `#` is worse than "unsupported"

Probing the host's cron turned up a sharper reason to reject `#` than "Quartz-only syntax":

```
$ printf '0 0 * * 5#2 /bin/true\n' > c; crontab -n c
The syntax of the crontab file was successfully checked.
```

It is **accepted — but not as Quartz's "2nd Friday"**. `#` opens a comment, so cron reads
day-of-week `5` and silently discards `#2` *and the command itself*. Someone pasting a
Quartz expression into a crontab gets a schedule that differs from what they wrote AND a
line that runs nothing at all, with no error at any point.

This is the strongest case in the project for rejecting loudly: the reference implementation
does not fail on `#`, it silently changes the meaning. cronx's error should say so:

```
cronx: error: day-of-week: '5#2' is Quartz syntax (nth weekday of the month), not supported
       by POSIX or Vixie cron; note that cron would read this as day-of-week 5 and treat
       '#2' as the start of a comment
```

The measured verdicts for the other extensions (all rejected by the host's cron, "bad
day-of-month"): `?`, `L`, `15W`. Six- and four-field lines are rejected too. KB:
`cron-live-oracle-probe`.

