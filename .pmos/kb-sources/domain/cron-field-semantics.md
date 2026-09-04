# Vixie crontab(5) five-field semantics (cron core reference)

Fields, in order, all required: minute hour day-of-month month day-of-week.
Legal ranges: minute 0-59, hour 0-23, day-of-month 1-31, month 1-12,
day-of-week 0-7 where BOTH 0 and 7 mean Sunday. (crontab(5)'s own table on this host
misprints dom/month as 0-31 and 0-12; the binary rejects 0 in both. Trust the binary.)

Per-field element forms (comma-separated list of elements, no spaces inside a field):
- `*`        every legal value
- `a`        single value
- `a-b`      inclusive range. NOTE: Debian's cron 3.0pl1 ALSO accepts a DESCENDING range
             (`22-2`, `FRI-MON`) -- measured, see `cron-live-oracle-probe`. Do not assume
             a <= b is enforced; decide the wrap semantics deliberately.
- `a-b/s`    range with step s (s >= 1); yields a, a+s, a+2s, ... <= b
- `*/s`      shorthand for first-last/s over the whole legal range
- `a/s`      MEASURED ON THIS HOST: **rejected** ("bad minute" / "bad day-of-month") by
             cron 3.0pl1. It is a cronie/other-dialect extension, NOT Debian vixie-cron.
             Accepting it is a deliberate deviation and needs an ADR saying so.

Names: three-letter, case-insensitive. Month JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC.
Day-of-week SUN MON TUE WED THU FRI SAT. Names are only legal in the month and
day-of-week fields, never in minute/hour/day-of-month.

RESOLVED BY MEASUREMENT: crontab(5) on this host still says "Ranges or lists of names are not
allowed", but the actual binary ACCEPTS `MON-FRI`, `JAN,JUL` and `MON-FRI/2`. The man sentence
is stale. cronx accepting them matches the implementation (ADR-005). See
`cron-live-oracle-probe`.
