# LIVE ORACLE: this host has vixie-cron, and `crontab -n` validates expressions

RSK-2 assumed there was no cron to diff against. There is:
  - package `cron 3.0pl1-200ubuntu1` (Debian/Ubuntu vixie-cron), `/usr/sbin/cron`
  - `man 5 crontab`
  - **`crontab -n <file>` = "dry run: checks the syntax, then bails out"** -- it validates
    WITHOUT installing anything (verified: the user's crontab was absent before and after).

Use it as a differential oracle. Probe form: write `<5 fields> /bin/true` to a temp file, run
`crontab -n`, read the exit code. Rejection messages are precise: `"file":0: bad minute`,
`bad day-of-month`, `bad month`, `bad day-of-week`.

## Measured verdicts (2026-09-04, cron 3.0pl1-200ubuntu1) -- these BEAT the man page

ACCEPTED, though `crontab(5)` on this same box says "Ranges or lists of names are not allowed":
  `0 0 * * MON-FRI`   `0 0 * JAN,JUL *`   `0 0 * * MON-FRI/2`   `0 0 * JAN-MAR *`
  -> the man page sentence is STALE; the implementation takes name ranges, lists and steps.

REJECTED -- the bare `a/s` step-without-range form is NOT supported here:
  `5/10 * * * *`   -> bad minute
  `0 0 5/10 * *`   -> bad day-of-month
  -> `a/s` is a cronie/other-dialect extension, NOT Debian vixie-cron. Any earlier note
     calling it "a Vixie extension meaning a-last/s" is WRONG for this implementation.

REJECTED -- 0 is not legal in day-of-month or month, despite the man page's own table
printing the ranges as "0-31" and "0-12":
  `0 0 0 * *` -> bad day-of-month     `0 0 * 0 *` -> bad month
  `0 0 32 * *` -> bad day-of-month    `0 0 * 13 *` -> bad month
  -> real ranges are dom 1-31, month 1-12. The man page TABLE is misleading; trust the binary.

ACCEPTED -- day-of-week 0 and 7 both legal, 8 is not: `0 0 * * 0`, `0 0 * * 7` ok, `* * * * 8` bad.

ACCEPTED -- **reverse / wrapping ranges**, which plain Vixie is often documented as refusing:
  `0 22-2 * * *`   `30-10 * * * *`   `0 0 * * FRI-MON`   `0 0 * NOV-FEB *`
  -> Debian's cron takes a descending range. The intended reading is wrap-around
     (22-2 = 22,23,0,1,2). Acceptance is MEASURED; the wrap semantics are inferred, since the
     daemon's runtime behaviour was not observed. Needs its own ADR.

REJECTED: `?`, `L`, `15W` (all "bad day-of-month"), 6-field and 4-field lines.

## `#` does NOT mean Quartz's nth-weekday -- it starts a COMMENT

`0 0 * * 5#2 /bin/true` is ACCEPTED, but not as "2nd Friday": `#` opens a comment, so cron
reads day-of-week 5 and discards `#2 /bin/true`. A user who copies a Quartz expression gets a
silently different schedule AND loses the command. This is the strongest argument for cronx
rejecting `#` inside a field with an explicit error rather than passing it through.
