# The day-of-month / day-of-week OR rule (the #1 cron correctness trap)

Cron does NOT simply AND all five fields. Day-of-month and day-of-week interact specially:

- If BOTH day-of-month and day-of-week are restricted (neither is the literal `*`),
  the job runs when EITHER field matches. This is a UNION, not an intersection.
- If exactly one of them is `*`, normal AND applies against the other.
- If both are `*`, both match everything.

Vixie's actual test is on the LITERAL asterisk character as written in the crontab, not on
whether the resulting set happens to cover the whole range. Therefore:
  `0 0 1-31 * MON`  -> restricted DOM (even though 1-31 is every day) => OR semantics
  `0 0 * * MON`     -> DOM is literal `*`                             => AND semantics
These two produce DIFFERENT schedules. A parser that normalises `1-31` to `*` before
matching is WRONG against Vixie. Preserve the "was this field written as a bare star" flag
through parsing into matching.

Test oracle examples (UTC):
  `0 0 13 * FRI` fires on every 13th AND on every Friday, not only Friday the 13th.
  `0 0 * * 0` and `0 0 * * 7` are the same schedule (Sunday).

## CONFIRMED by crontab(5) on this host (ends the ADR-001 open question)

The Debian crontab(5) NOTES section states it outright:

  "POSIX specifies that the day of month and the day of week fields both need to match the
   current time if either of them is a *. However, this implementation only checks if the
   first character is a *. This is why "0 0 */2 * sun" runs every Sunday that's an uneven
   date while the POSIX standard would have it run every Sunday and on every uneven date."

So `*/2` in a day field SETS the star flag (first character is `*`) and therefore selects
AND, not OR. POSIX and Vixie genuinely DISAGREE here; the brief demands both, so cronx must
pick one and record it (ADR-001 picks Vixie). Worked case: `0 0 */2 * sun` = Sundays falling
on odd-numbered dates, NOT "every Sunday plus every odd date".
