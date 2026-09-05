# cronx — architect decisions

## cronx ADR index (what each decision fixes)
ADR-001 day rule: Field.star is the leading-character text test, never derived from the value
set; OR when both dom+dow restricted, AND if either star. ADR-002 spring-forward gap: fixed
schedule shifts to the jump instant (gap_shifted); wildcard minute/hour drops it. ADR-003
fall-back fold: wildcard emits both passes, fixed emits first only. ADR-004 @reboot parses,
sets reboot flag, matches nothing. ADR-005 names legal in month/dow only, incl. range
endpoints/step bases (MON-FRI/2); stale man-page ban is doc rot, not an enforced rule.
ADR-006 bare a/s REJECTED (revised after live probe — vixie says "bad minute").
ADR-007 reject L/W/#/?/6-7-field/@every with a dialect-naming error; cron silently mis-reads
`5#2`. ADR-008 bounded search: HORIZON_DAYS=366*9, zero results = exit 0 + "no runs" message.
ADR-009 English = closed template grammar + golden file, no free-text fallback. ADR-010 error
model: CronxError(message, code), exit 1 bad expression, exit 2 bad invocation/env, one line
stderr "cronx: error: ...", never a traceback. ADR-011 unknown --tz vs missing tzdata
distinguished via UTC probe, both exit 2. ADR-012 descending/wrap ranges (22-2, NOV-FEB)
REJECTED with ascending rewrite hint (22-23,0-2); empty-set reading of vixie is inference, not
measurement.

## cronx data-structure contracts (parse.py)
Element frozen dataclass: start/stop/step ints + star (element written as * or */s). Field
frozen dataclass: name, text (VERBATIM as written — errors, --json and describe all echo it),
elements tuple, values frozenset (dow 7 folded to 0), star flag (set once in parser, never
recomputed downstream). Schedule: text, macro (lower-cased or None), reboot, five Fields.
CronxError(Exception): __init__(message, code); message is final user-facing text (ADR-010).
Occurrence (occurrences.py): instant aware-UTC, local aware with fold set, dst
None|gap_shifted|ambiguous_first|ambiguous_second, nominal naive (set only for gap_shifted).

## cronx DST gap binary search (occurrences.py)
zoneinfo never raises on gap/fold. Detect gap: naive.replace(tzinfo=tz).astimezone(utc)
.astimezone(tz).replace(tzinfo=None) != naive. Jump instant = integer-second binary search
between lo=fold=1 ts and hi=fold=0 ts for earliest instant whose local >= naive; use
int(...timestamp()) — float timestamps leave sub-second residue. Ambiguous = fold0 and fold1
give different instants. Step in wall clock then resolve; never do naive arithmetic then attach
a zone. Offsets are not assumed whole hours (Asia/Kathmandu +05:45 is a test case). next_runs
emits only instants STRICTLY greater than after_utc and the last emitted — that one filter
delivers --from exclusivity, gap collapse, and RSK-4 monotonicity with no sort/buffer.
