# ADR-009: a closed template grammar for the English explanation

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

R-005 asks for "a deterministic one-sentence plain-English explanation". That is an open
invitation to build a natural-language generator (RSK-3): the schedule domain is finite, but
the prose describing it is not. The grammar must be closed and testable, and — because of
ADR-001 — it must make the day-rule connective visible, since that is the trap the tool
exists to defuse.

## Options considered

- **A — one template per schedule shape.** Pro: reads perfectly where covered. Con: the
  shape space is the product of five fields, so the table grows without bound and every gap
  is a bug report.
- **B — a closed compositional grammar: render each element, join into per-field phrases,
  assemble a fixed clause order, elide unrestricted clauses.** Pro: total by construction —
  every parseable expression has exactly one sentence. Con: some sentences are stiff.

## Decision

**B.** The grammar is closed and total; there is no free-text path and no fallback prose.

```
sentence   := Time [ ", " DayClause ] [ ", " MonthClause ] "."      capitalised, one period
Time       := "at HH:MM"                        if minute and hour are each one value
            | "every minute"                    if both fields are exactly "*"
            | "every minute past " P(hour)      if minute is exactly "*"
            | "at " P(minute) [ " past " P(hour) ]   ("past …" elided if hour is exactly "*")
DayClause   := "on " P(dom)                     if dow is exactly "*"
            | "on " P(dow)                      if dom is exactly "*"
            | "on " P(dom) " or on " P(dow)     both restricted  -> OR rule  (ADR-001)
            | "on " P(dom) " and on " P(dow)    otherwise (e.g. "*/2" in a day field)
            | <elided>                          if both fields are exactly "*"
MonthClause := "in " P(month)                   elided if month is exactly "*"
P(field)    := element phrases joined by ", "
```

Element phrases, by field family — numeric (minute, hour, day-of-month) and named (month,
day-of-week, using full names: January, Monday):

| element | numeric field | named field |
|---|---|---|
| `*` | `every <unit>` | `every <unit>` |
| `*/s` | `every <ord(s)> <unit>` | `every <ord(s)> <unit>` |
| `a` | `<unit> a` if first element, else `a` | `Monday` |
| `a-b` | `every <unit> from a through b` | `Monday through Friday` |
| `a-b/s`, `a/s` | `every <ord(s)> <unit> from a through b` | `every <ord(s)> <unit> from Monday through Friday` |

`<unit>` is `minute`, `hour`, `day-of-month`, `month`, `day-of-week`. `@reboot` bypasses the
grammar entirely with the fixed sentence from ADR-004. The timezone is not part of the
sentence; it belongs to the run list.

## Consequences

- Positive: total, deterministic and diffable — T-006's golden file is the contract, so a
  wording change is a visible test diff, not a silent regression.
- Positive: the day connective is always printed when both day fields are constrained, so
  the ADR-001 trap is on screen (`At 00:00, on day-of-month 13 or on Friday.`).
- Negative: stiff phrasings exist and stay (charter §4: no i18n, no locale). Anything the
  grammar cannot say is not a new template — it is not said. That is RSK-3's stop valve.
- Risks: the "first element only" unit prefix is the renderer's only state; the golden file
  covers a multi-element list to pin it.

## Pinned by

T-006 golden file `tests/golden/descriptions.txt`, one line per expression, including:
`* * * * *`, `*/2 * * * *`, `5 * * * *`, `0 0 * * *`, `0 9,17 * * *`, `5 9-17 * * *`,
`*/15 9-17 * * MON-FRI`, `0 0 13 * FRI`, `0 0 */2 * MON`, `0 0 1-31 * MON`, `5/10 * * * *`,
`@yearly`, `@weekly`, `@reboot`.
