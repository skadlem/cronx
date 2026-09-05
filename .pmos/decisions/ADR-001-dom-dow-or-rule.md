# ADR-001: day-of-month / day-of-week OR rule, and what counts as "restricted"

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

Cron does not AND all five fields. When both the day-of-month (DOM) and day-of-week (DOW)
fields are *restricted*, a job fires when EITHER matches; when at least one is unrestricted,
normal AND applies (KB: `cron-dom-dow-or-rule`). This is the single most common
mis-reading of a crontab line and is the reason R-004 exists.

Two things must be decided: (a) how "restricted" is tested, and (b) whether a step form
such as `*/2` in a day field is restricted. The KB records that Vixie tests the LITERAL
asterisk as written, not the resulting value set, so `1-31` is restricted but `*` is not.
It does not settle `*/2`, and POSIX prose and the Vixie implementation are read differently
here.
<!-- 2026-09-05 revision note: the original Context claimed there was no cron on this host
     to diff against. Wrong — GATE 1 found `cron 3.0pl1` + `crontab -n`, and crontab(5)'s
     NOTES section carries the worked `*/n` day-field case verbatim ("0 0 */2 * sun" =
     Sundays on uneven dates). The Decision below already cites it; Context kept as
     historical. -->

## Options considered

- **A — first-character test (Vixie `entry.c`: the `DOM_STAR`/`DOW_STAR` flag is set when
  the field's first character is `*`, before the element list is parsed).** Pro: matches the
  deployed implementation the user's crontab will actually run under. Con: `*/2` is then
  "unrestricted" even though it plainly restricts the days.
- **B — set-subset test (restricted iff the field's value set is a proper subset of the
  legal range).** Pro: matches a plain reading of the POSIX sentence "if both fields are
  restricted". Con: makes `1-31` equivalent to `*`, which the KB states outright is WRONG
  against Vixie; so B would have to be applied to `*/n` only, i.e. an inconsistent rule.

## Decision

**A.** `Field.star` is `field_text.startswith("*")`, computed once at parse time from the
raw text and carried through matching unchanged. The day rule is:

```
if dom.star or dow.star:  dom_match AND dow_match
else:                     dom_match OR  dow_match
```

Consequently `0 0 1-31 * MON` uses OR, `0 0 * * MON` uses AND, and — the sub-question —
`0 0 */2 * MON` uses **AND** (odd-numbered days of the month that are also Mondays; Vixie's
`get_list` starts a step walk at the field minimum, and the day-of-month minimum is 1, so
`*/2` = {1,3,…,31} — confirmed verbatim by crontab(5): "`0 0 */2 * sun` runs every Sunday
that's an uneven date"), not OR. Note
the rule is deliberately textual to the first character only: `5,*` is restricted,
`*/2,5` is not. That is what Vixie does.

## Consequences

- Positive: one boolean per field, computed in one place, reused by ADR-002/ADR-003 as
  Vixie's `MIN_STAR`/`HR_STAR` wildcard test. No second notion of "restricted" anywhere.
- Positive: the parser must never normalise `1-31` to `*`, which also keeps `--json`
  `fields[].text` honest.
- Negative: `*/2` in a day field surprises users who read the POSIX sentence. Mitigation:
  ADR-009's sentence always names both day clauses and the connective, so the output shows
  which rule was applied rather than hiding it.
- **Residual uncertainty: RETIRED 2026-09-05.** The original bullet said the literal-`*`
  rule could not be diffed against a live cron. The crontab(5) NOTES worked case
  (`0 0 */2 * sun` = Sundays on uneven dates) settles it for this Vixie build. Supersede
  protocol stays as written: only `star` and the day rule would change — one predicate and
  one branch, plus the oracle test.

## Pinned by

T-008 oracle cases: `0 0 13 * FRI` fires every 13th and every Friday; `0 0 1-31 * MON` ≠
`0 0 * * MON`; `0 0 */2 * MON` fires only on odd-numbered-date Mondays (see the crontab(5)
worked case above); `0 0 * * 0` ≡ `0 0 * * 7`.
<!-- corrected 2026-09-05 post-L-3 review: parenthetical originally said "even days",
     which inverts Vixie's minimum-start step expansion; mechanism unchanged -->
