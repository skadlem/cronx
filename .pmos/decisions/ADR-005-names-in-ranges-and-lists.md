# ADR-005: accept three-letter names inside ranges, lists and step bases

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

Month and day-of-week accept three-letter names (`JAN`…`DEC`, `SUN`…`SAT`),
case-insensitively, and only in those two fields. The authorities disagree about names in
compound elements: classic ISC/Vixie `crontab(5)` states outright that "ranges or lists of
names are not allowed", while Debian's cronie/vixie-cron accepts `MON-FRI` and `JAN,JUL` in
practice. The KB flags this as CONTESTED and requires an ADR either way
(KB: `cron-field-semantics`). R-002 already commits the charter to accepting them; this ADR
records why that deviation from the strict ISC text is the right one.

## Options considered

- **A — follow the ISC text: names only as bare single values.** Pro: literal conformance
  to the documented reference; the rejection message could teach the strict rule. Con:
  `MON-FRI` is in real crontabs on the majority of Linux hosts, where the local cron runs
  it fine. cronx would refuse to read a line that demonstrably works, sending the user back
  to guessing — the exact failure the charter's wedge exists to remove.
- **B — accept names anywhere a number is legal in those two fields** (range endpoints,
  list members, step bases: `MON-FRI`, `JAN,JUL`, `MON-FRI/2`). Pro: strict superset — every
  expression ISC accepts, cronx accepts identically. Con: cronx will explain a line that a
  strict-ISC cron would reject at install time, and says nothing about it.

## Decision

**B.** Names are resolved to their numeric value as the first step of parsing an element,
after which every element form behaves exactly as the numeric form does. Names remain
illegal in minute, hour and day-of-month (`0 0 MON * *` is an error naming the field and the
token). Range endpoints obey the same no-wrap rule as numbers, so `FRI-MON` is an error
("range start is after its end") — consistent with ADR-006, not a special case. `SUN`…`SAT`
map to 0…6, and the bare numeric `7` also means Sunday.

## Consequences

- Positive: strict superset — no expression changes meaning relative to ISC, only the set of
  accepted inputs grows. There is no schedule cronx explains differently from ISC because
  of this ADR.
- Positive: name resolution is one dict lookup at the front of the element parser; there is
  no second grammar for named fields.
- Negative: a user on a strict-ISC cron gets no warning that their host will reject the
  line. Accepted deliberately: cronx explains schedules, it does not lint installability
  (charter §4), and a false "invalid" is worse than a missing hint.
- Risks / follow-ups: if a user reports an ISC host rejecting a line cronx accepted, the fix
  is a documentation note, not a semantics change.

## Pinned by

T-002/T-008: `MON-FRI`, `mon-fri`, `JAN,JUL`, `MON-FRI/2` parse to the expected value sets;
`0 0 MON * *` and `0 0 * MON *` are errors naming the field and the token; `FRI-MON` is a
range error; `0 0 * * 0` ≡ `0 0 * * 7` ≡ `0 0 * * SUN`.
