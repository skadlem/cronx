# ADR-008: bounded calendar search, and emission ordered strictly by instant

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

"Next N runs" must terminate even when the schedule never fires: `0 0 30 2 *` (February
never has 30 days) and `0 0 31 4 *` match no date at all, and a naive "advance a minute
until N found" loop would run forever. The search must also produce a list that is strictly
increasing in *instant* while it iterates *wall clock*, because the DST policies of ADR-002
and ADR-003 can map two different wall clocks to one instant (two gap candidates on the same
day both collapse to the clock-jump instant) and one wall clock to two instants (the
ambiguous hour). RSK-4 names this the subtlest code in the project.

## Options considered

- **A — minute-by-minute scan with a wall-clock deadline.** Pro: one loop. Con: up to
  4.7 million iterations before concluding `0 0 30 2 *` never fires.
- **B — day-level outer loop over the calendar, inner loop over the precomputed sorted
  (hour, minute) pairs, with a fixed horizon in days.** Pro: at most ~3.3k date checks to
  prove a schedule is dead; the day loop is exactly where the ADR-001 OR rule lives. Con:
  a horizon constant that has to be justified.
- **C — closed-form "next matching date" arithmetic.** Pro: fastest. Con: leap years,
  month lengths and the OR rule make it the kind of clever code that is wrong at 3am, for a
  tool that prints five lines.

## Decision

**B**, with `HORIZON_DAYS = 366 * 9` (nine years). Justification for the bound: the only way
a satisfiable schedule can go years without matching is a February 29 day-of-month, and the
longest gap between consecutive February 29s is eight years (1896→1904, 2096→2104). Nine
years of days therefore guarantees at least one match for every satisfiable expression, and
any expression with no match in that window is unsatisfiable in practice. When the horizon
is exhausted the search stops and returns however many occurrences it found, possibly zero —
exit 0, with `no runs found within 9 years of <from>` in text output and `"next": []` in
JSON (distinguished from `@reboot` by the `reboot` flag, ADR-004).

Emission rule, applied uniformly: occurrences are yielded in ascending wall-clock order,
each resolved to an instant, and one is emitted only if its instant is **strictly greater**
than both the `--from` reference and the last emitted instant. That single rule delivers
`--from` exclusivity, the gap collapse of ADR-002, and the monotonicity invariant of RSK-4.

## Consequences

- Positive: termination is a loop bound, not an argument. Worst case is ~3.3k date checks
  plus at most `|hours| × |minutes|` per matching day.
- Positive: no sort and no buffer — the list is monotone by construction, so `-n 1000` costs
  no more memory than `-n 5`.
- Negative: a schedule that first fires more than nine years out (only constructible with a
  `--from` far in the past against a Feb-29 rule) would be reported as never firing. The
  bound is stated in the message, so the answer is falsifiable rather than silently wrong.
- Risks / follow-ups: the "strictly greater than the last emitted" filter is what hides gap
  duplicates; if it is ever removed for performance, ADR-002 breaks silently. The
  monotonicity property test is the guard.

## Pinned by

T-004: `0 0 30 2 *` and `0 0 31 4 *` return zero occurrences and exit 0 within the horizon;
`0 0 29 2 *` from 2026-01-01 finds 2028-02-29. T-008: the monotonicity property test asserts
strictly increasing instants across every transition of three zones over five years.
