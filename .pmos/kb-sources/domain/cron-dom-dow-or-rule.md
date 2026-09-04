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
