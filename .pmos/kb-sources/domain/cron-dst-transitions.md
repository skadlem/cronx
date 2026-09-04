# Timezone transitions: what "next run" means across DST

cronx computes wall-clock occurrences in a target IANA zone; it is NOT a daemon, so it
should enumerate matches of local wall-clock time, then map each to a real instant.

Two hard cases, both must be decided explicitly (ADR) and tested:

1. SPRING FORWARD (gap). Local times in the skipped hour never occur. e.g. America/New_York
   2026-03-08 02:30 does not exist. Python's zoneinfo does NOT raise for a gap: it returns
   a nominal datetime whose utcoffset() is the PRE-transition offset, so .timestamp()
   round-trips to a DIFFERENT wall clock. Detect a gap by checking that
   dt.astimezone(utc).astimezone(tz) != dt. Vixie cron's own behaviour is to run
   fixed-time (non-wildcard) jobs once after the clock jump; wildcard jobs are simply
   skipped. Which of those cronx reports is a deliberate choice.

2. FALL BACK (ambiguous/repeated hour). e.g. 01:30 occurs twice. PEP 495 fold: fold=0 is
   the first (DST) occurrence, fold=1 the second (standard). Vixie suppresses the repeat
   for fixed-time jobs. cronx must decide whether "next 5 runs" lists such a time once or
   twice, and must produce correctly-offset ISO-8601 output either way.

Also: a schedule can be evaluated in a zone with a non-hour offset (Asia/Kathmandu +05:45)
and zones whose rules changed historically. Never assume offsets are whole hours.
Never do arithmetic on naive datetimes then attach a zone -- attach the zone, then step
in wall-clock terms, then resolve to an instant.
