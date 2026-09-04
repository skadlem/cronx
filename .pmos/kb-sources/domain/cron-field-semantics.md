# Vixie crontab(5) five-field semantics (cron core reference)

Fields, in order, all required: minute hour day-of-month month day-of-week.
Legal ranges: minute 0-59, hour 0-23, day-of-month 1-31, month 1-12,
day-of-week 0-7 where BOTH 0 and 7 mean Sunday.

Per-field element forms (comma-separated list of elements, no spaces inside a field):
- `*`        every legal value
- `a`        single value
- `a-b`      inclusive range; Vixie requires a <= b (no wrap-around like 22-2)
- `a-b/s`    range with step s (s >= 1); yields a, a+s, a+2s, ... <= b
- `*/s`      shorthand for first-last/s over the whole legal range
- `a/s`      Vixie extension: behaves as `a-last/s` (start value through field max).
             NOT in every cron. DECISION POINT -> needs an ADR either way.

Names: three-letter, case-insensitive. Month JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC.
Day-of-week SUN MON TUE WED THU FRI SAT. Names are only legal in the month and
day-of-week fields, never in minute/hour/day-of-month.

CONTESTED: classic ISC/Vixie crontab(5) states "ranges or lists of names are not allowed",
but Debian cronie/vixie-cron in practice accepts MON-FRI and JAN,JUL. Whichever cronx picks
is a deliberate deviation and MUST be an ADR with rationale. Do not silently choose.
