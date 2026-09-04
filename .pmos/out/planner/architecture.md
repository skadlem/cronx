# cronx architecture

Owner: planner (PM + architect) | Updated: 2026-09-04 | Charter: `.pmos/charter.md`

Binding constraints, from the charter: Python 3.9 syntax floor, standard library only, no
network at runtime or test time, stdlib `unittest`. Five small modules, ~600 LOC. No plugin
layer, no config file, no environment-variable configuration, no importable API promise.
Every semantic choice below is fixed by an ADR in `.pmos/decisions/`; the implementer decides
nothing that has an ADR number next to it.

## 1. Modules

```
cronx/__init__.py       __version__ only. No re-exports (no API promise).
cronx/parse.py          text -> validated Schedule. Owns CronxError, Field, Element,
                        Schedule, the name tables and the macro table.        ~180 LOC
cronx/match.py          Schedule -> ascending naive local datetimes. Owns the
                        day rule (ADR-001) and the bounded search (ADR-008).   ~90 LOC
cronx/occurrences.py    naive local -> aware instants. Owns zone resolution
                        (ADR-011) and the DST policy (ADR-002, ADR-003).      ~120 LOC
cronx/describe.py       Schedule -> one English sentence (ADR-009).           ~110 LOC
cronx/cli.py            argparse, text and --json rendering, exit codes
                        (ADR-010). The only module that touches sys.exit.     ~110 LOC
cronx/__main__.py       `from .cli import main; raise SystemExit(main())`.      3 LOC
tests/                  stdlib unittest; `python3 -m unittest discover`.
```

Dependency direction, acyclic and one-way: `cli -> {parse, match, occurrences, describe}`,
`occurrences -> {parse, match}`, `match -> parse`, `describe -> parse`. `parse` imports
nothing from the package. Only `cli` imports `argparse`, `json` and `sys`; only
`occurrences` imports `zoneinfo`.

## 2. Data structures (`parse.py`)

```python
@dataclass(frozen=True)
class Element:            # one comma-separated piece of a field, all forms normalised
    start: int            # to (start, stop, step); see ADR-006 for the table
    stop: int
    step: int
    star: bool            # this element was written as `*` or `*/s`

@dataclass(frozen=True)
class Field:
    name: str             # "minute" | "hour" | "day-of-month" | "month" | "day-of-week"
    text: str             # exactly as written, for errors, --json and describe
    elements: Tuple[Element, ...]
    values: FrozenSet[int]  # expanded, day-of-week 7 already folded to 0
    star: bool            # THE OR-RULE FLAG: text.startswith("*") -- see below

@dataclass(frozen=True)
class Schedule:
    text: str             # the expression as given
    macro: Optional[str]  # "@daily" etc. (lower-cased), else None
    reboot: bool          # ADR-004; when True the five fields are unset/ignored
    minute: Field; hour: Field; dom: Field; month: Field; dow: Field

class CronxError(Exception):
    def __init__(self, message: str, code: int): ...   # message is final, ADR-010
```

**The star flag is the trap.** `Field.star` is `field_text.startswith("*")` — a test on the
raw text's first character, computed once in the parser and never recomputed downstream
(ADR-001). It must NOT be derived from `values`: `1-31` expands to every legal day but is
restricted, and `*/2` is a proper subset but is not. Consequences: `Field.star` is what
`match.py` reads for the day rule, and what `occurrences.py` reads on `minute`/`hour` for
Vixie's wildcard test. Normalising `1-31` to `*`, or setting `star` from set coverage,
silently breaks all three ADRs at once — that is the single most important invariant here.

Parsing order inside a field, so error messages stay precise: reject `L`/`W`/`#`/`?`
(ADR-007) -> split on `,` -> per element, resolve names (month and day-of-week only,
ADR-005) -> match one of the six forms -> range and step validation (ADR-006) -> expand.
Macros are matched first, case-insensitively, against the whole expression; a macro other
than `@reboot` is rewritten to its five-field text and parsed normally (KB: `cron-macros`).

## 3. Pipeline

```
argv --> parse.parse(expr) --> Schedule
                                 |
         occurrences.resolve_zone(--tz) --> ZoneInfo        (ADR-011, fails before output)
                                 |
     match.iter_local(sched, after_local)  ->  naive local datetimes, ascending
                                 |
     occurrences.next_runs(...)  ->  [Occurrence]  (DST policy, dedupe, monotone)
                                 |
     describe.describe(sched)    ->  one sentence
                                 |
     cli --> text or JSON on stdout, exit 0 / 1 / 2
```

### 3.1 Matching (`match.py`)

```python
def day_matches(s: Schedule, d: date) -> bool:
    if d.month not in s.month.values:
        return False
    dom_ok = d.day in s.dom.values
    dow_ok = (d.isoweekday() % 7) in s.dow.values     # Mon..Sun 1..7 -> Sun == 0
    if s.dom.star or s.dow.star:
        return dom_ok and dow_ok                      # ADR-001
    return dom_ok or dow_ok
```

`iter_local(s, after: datetime) -> Iterator[datetime]` (naive, ascending, strictly after
`after`): outer loop over `date`s from `after.date()` for `HORIZON_DAYS = 366 * 9` days,
skipping non-matching days; inner loops over `sorted(s.hour.values)` then
`sorted(s.minute.values)`. The hour and minute lists are sorted once, outside the loops.

### 3.2 Termination bound (ADR-008)

`HORIZON_DAYS = 366 * 9`. The only satisfiable schedule that can go years without matching is
a February 29 day-of-month, and the longest gap between consecutive February 29s is eight
years. Nine years therefore guarantees a match for anything satisfiable. When the horizon is
exhausted the iterator simply stops: `0 0 30 2 *` and `0 0 31 4 *` yield zero occurrences,
exit 0, with `no runs found within 9 years of <from>` (text) / `"next": []` (JSON), told
apart from `@reboot` by the `reboot` flag. Cost of proving a schedule dead: ~3.3k date checks.

### 3.3 Timezone and DST (`occurrences.py`)

```python
@dataclass(frozen=True)
class Occurrence:
    instant: datetime          # aware, UTC
    local: datetime            # aware, in the target zone, fold set
    dst: Optional[str]         # None | "gap_shifted" | "ambiguous_first" | "ambiguous_second"
    nominal: Optional[datetime]  # naive wall clock asked for; set only for gap_shifted
```

`wildcard = s.minute.star or s.hour.star` — Vixie's `MIN_STAR|HR_STAR`, reusing the same
flag as the day rule. `resolve(naive, tz, wildcard) -> List[Occurrence]`:

1. **Gap** (`naive.replace(tzinfo=tz).astimezone(utc).astimezone(tz).replace(tzinfo=None)
   != naive` — `zoneinfo` does not raise, KB: `cron-dst-transitions`): wildcard -> `[]`;
   otherwise one occurrence at the clock-jump instant, `dst="gap_shifted"`, `nominal=naive`
   (ADR-002). The jump instant is an integer-second binary search between the fold=1 instant
   (before the jump) and the fold=0 instant (after it), for the earliest instant whose local
   time is >= `naive`:

   ```python
   lo = int(naive.replace(tzinfo=tz, fold=1).timestamp())
   hi = int(naive.replace(tzinfo=tz, fold=0).timestamp())
   while lo + 1 < hi:
       mid = (lo + hi) // 2
       if datetime.fromtimestamp(mid, tz).replace(tzinfo=None) >= naive: hi = mid
       else: lo = mid
   return datetime.fromtimestamp(hi, timezone.utc)
   ```
   Verified exact against `America/New_York` (1 h), `Europe/Dublin` and
   `Australia/Lord_Howe` (30 min). Float timestamps must not be used — they leave
   sub-second residue.
2. **Ambiguous** (fold=0 and fold=1 give different instants): wildcard -> two occurrences,
   `"ambiguous_first"` then `"ambiguous_second"`; otherwise one, fold=0,
   `"ambiguous_first"` (ADR-003).
3. **Ordinary**: one occurrence, `dst=None`.

`next_runs(s, tz, after_utc, count)` converts `after_utc` to naive local, walks
`iter_local`, resolves each candidate, and emits an occurrence only if its instant is
**strictly greater** than both `after_utc` and the last emitted instant. That one filter
delivers `--from` exclusivity, the ADR-002 gap collapse (several skipped wall clocks share
the jump instant; the job runs once) and the RSK-4 monotonicity invariant — no sort, no
buffer, so `-n 1000` costs no more memory than `-n 5`.

Never do arithmetic on naive datetimes and attach a zone afterwards; step in wall clock,
then resolve (KB: `cron-dst-transitions`). Offsets are never assumed to be whole hours.

## 4. Public CLI contract

```
usage: cronx [-h] [--tz ZONE] [-n N] [--from ISO8601] [--json] EXPRESSION

Explain a cron expression and list its next run times. Five fields or an @macro.

positional arguments:
  EXPRESSION      five-field cron expression or @macro, e.g. '0 2 * * *'

optional arguments:
  -h, --help      show this help message and exit
  --tz ZONE       IANA timezone name (default: UTC)
  -n N            number of run times to list (default: 5)
  --from ISO8601  reference instant; runs listed are strictly after it (default: now).
                  A value with no offset is read as wall clock in --tz.
  --json          print a JSON object on stdout instead of text
```

Text output (stdout), exactly:

```
0 2 * * *
At 02:00.

next 5 runs in America/New_York:
  2026-03-07 02:00:00-05:00   2026-03-07T07:00:00+00:00
  2026-03-08 03:00:00-04:00   2026-03-08T07:00:00+00:00  (02:00 does not exist: DST gap, runs at the jump)
  2026-03-09 02:00:00-04:00   2026-03-09T06:00:00+00:00
```

Annotation suffixes, one per `dst` value: `gap_shifted` ->
`  (HH:MM does not exist: DST gap, runs at the jump)`; `ambiguous_first` ->
`  (first pass of an ambiguous hour)`; `ambiguous_second` ->
`  (second pass of an ambiguous hour)`; `None` -> no suffix. Empty run list ->
`no runs found within 9 years of <from>`. `@reboot` -> the ADR-004 sentence and no run list.

`--json` object (stdout, `json.dumps(..., indent=2, sort_keys=False)` + newline):

```json
{
  "expression": "0 2 * * *",          // string, as given
  "macro": null,                      // string ("@daily") or null
  "reboot": false,                    // bool (ADR-004)
  "timezone": "America/New_York",     // string, always present, even when defaulted
  "from": "2026-03-07T00:00:00+00:00",// string, ISO-8601 with offset
  "description": "At 02:00.",         // string, ADR-009
  "day_rule": "and",                  // string, "and" | "or" (ADR-001)
  "fields": {                         // object; absent keys never occur. null when reboot
    "minute":       {"text": "0", "star": false, "values": [0]},
    "hour":         {"text": "2", "star": false, "values": [2]},
    "day_of_month": {"text": "*", "star": true,  "values": [1, "...", 31]},
    "month":        {"text": "*", "star": true,  "values": [1, "...", 12]},
    "day_of_week":  {"text": "*", "star": true,  "values": [0, "...", 6]}
  },
  "next": [                           // array, possibly empty
    {"local": "2026-03-08T03:00:00-04:00",  // string, ISO-8601 with offset
     "utc":   "2026-03-08T07:00:00+00:00",  // string, ISO-8601, always +00:00
     "dst":   "gap_shifted",                // string or null (four values, §3.3)
     "nominal_local": "2026-03-08T02:00:00"}// string (naive ISO) or null
  ]
}
```

`values` arrays are sorted ints (`"..."` above is elision in this document, not in the
output). Every key is always present; optionality is expressed with `null`, never by
omission, so a consumer needs no key checks.

Exit codes (ADR-010): `0` success, including an empty run list; `1` the expression is
invalid; `2` the invocation or environment is wrong (unknown `--tz`, no tz database,
unparseable `--from`, `-n < 1`, argparse usage errors). Errors are one line on stderr,
`cronx: error: ...`, in both output modes; stdout stays empty and there is never a
traceback.

## 5. Test placement

| id | what | lands in |
|---|---|---|
| T-001 | repo skeleton + 3.9 syntax guard: `ast.parse(src, feature_version=(3, 9))` over every file in `cronx/` and `tests/` | `tests/test_py39_syntax.py` (RSK-1a) |
| T-002 | field/element parsing, ranges, steps, names, error messages | `cronx/parse.py`, `tests/test_parse.py` (ADR-005, ADR-006, ADR-010) |
| T-003 | macros, `@reboot`, rejected extensions and field count | `cronx/parse.py`, `tests/test_macros.py` (ADR-004, ADR-007) |
| T-004 | day rule, `iter_local`, horizon and unsatisfiable schedules | `cronx/match.py`, `tests/test_match.py` (ADR-001, ADR-008) |
| T-005 | zone layer, gap and fold policy, dedupe | `cronx/occurrences.py`, `tests/test_dst.py` (ADR-002, ADR-003) |
| T-006 | English sentence + golden file | `cronx/describe.py`, `tests/test_describe.py`, `tests/golden/descriptions.txt` (ADR-009) |
| T-007 | `ZoneInfoNotFoundError` path: unknown zone vs missing tz database | `cronx/occurrences.py` + `cronx/cli.py`, `tests/test_tz_errors.py` (ADR-011, RSK-5) |
| T-008 | crontab(5) oracle suite + ambiguous-hour monotonicity property test | `tests/test_oracle.py`, `tests/test_monotonicity.py` — no source module (RSK-2, RSK-4) |
| T-009 | CLI: argparse, text and JSON rendering, exit-code table | `cronx/cli.py`, `cronx/__main__.py`, `tests/test_cli.py` (ADR-010) |
| T-010 | reviewer's 3.9 stdlib-API floor audit against `python39-stdlib-constraints` | whole `cronx/` package; report at `.pmos/out/reviewer/test-report.md` (RSK-1b) |

T-008 needs no code of its own: it is oracle cases (`0 0 13 * FRI`, `0 0 * * 0` ≡
`0 0 * * 7`, `0 0 */2 * MON`, the spring-forward gap, the fall-back repeat,
`Asia/Kathmandu` at +05:45) driven through the same public entry points as the CLI, each
naming its KB chunk in a comment so a later correction is a localised test change plus an
ADR supersession.

## 6. Things deliberately absent

No `Field` subclasses or per-field parser classes — one `Element` triple covers all six
forms. No abstract "output formatter" — two functions in `cli.py`. No caching layer;
`ZoneInfo` already caches, and the search is thousands of cheap operations, not millions.
No logging. No `available_timezones()` anywhere (slow, KB: `python39-stdlib-constraints`).
No `--version`, no colour, no shell completion (charter §4). If a module needs a sixth
sibling, that is a signal to re-read this section, not to add one.
