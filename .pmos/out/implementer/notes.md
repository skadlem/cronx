# Implementer notes — Wave 2 chunk 1 RETRY (T-002, T-003)

Date: 2026-09-05 | Spawn model: qwen3.8-flash (hermes host) | Working dir: /home/madiyar/cronx

## Tasks done

- **T-002** (field/element parser): implemented `cronx/parse.py` (178 LOC, budget ~180).
  All five element forms (`*`, `a`, `a-b`, `a-b/s`, `*/s`), comma lists, per-field range
  validation, name resolution in month/dow only (ADR-005), dow 7→0 fold, bare `a/s`
  rejection with the `5-59/10` rewrite hint (ADR-006 revised), descending-range rejection
  with the wrap rewrite hint (ADR-012), verbatim `Field.text` and first-character
  `Field.star` (ADR-001 invariant — never derived from values, `1-31` not normalised),
  `str.split()`-style whitespace collapse, step expansion from the element's range floor
  with a bare `*` floor = FIELD minimum (dom `*/2` = {1,3,…,31}).
- **T-003** (macros + extension rejection): wrote `tests/test_macros.py` FIRST (TDD,
  16 tests, RED against the stub), then implemented: the eight-macro table,
  case-insensitive whole-expression macro match, non-@reboot macros rewritten to their
  five-field text and parsed normally, `@reboot` → `Schedule.reboot=True` with fields
  None and field parsing skipped (ADR-004), 6/7-field Quartz rejection, the
  2026-09-05 crontab-line amendment (command-shaped token 6 starting with `/`, `./` or
  `~` → "crontab LINE … pass only the first five fields" hint INSTEAD of Quartz),
  `L`/`W`/`#`/`?` dialect-naming rejections with the `#`-becomes-a-comment note from
  the live-oracle KB chunk, and `@every`/unknown-macro errors listing the supported set
  (ADR-007 + ADR-010 message/code contract). `CronxError(message, code)`; parser always
  code 1.

## ⚠ FLAGGED — one committed test contradicts ADR-001 (NOT edited, per procedure)

`tests/test_parse.py::WhitespaceTest::test_leading_trailing_and_double_spaces_parse`
(assertion on line 219):

    s = parse("  0  0 *  *  * \t")
    self.assertTrue(s.hour.star)

The string splits `str.split()`-style to exactly FIVE tokens:
`['0', '0', '*', '*', '*']` → minute='0', hour='0', dom='*', month='*', dow='*'.
So `hour.text` is `"0"` and `Field.star` is `text.startswith("*")` = **False** by the
binding ADR-001 rule (architecture §2: "computed once in the parser … a test on the raw
text's first character, never derived from values"). `assertTrue(s.hour.star)` can only
pass if the parser violates ADR-001 (e.g. derives star from value-set coverage — the
exact normalisation ADR-001 forbids and which would silently break ADR-002/003's
MIN_STAR/HR_STAR reuse). The test's sibling assertion (`s.minute.values == {0}`) passes.

Likely author typo: intent was `s.dom.star` (or the string needed one more `*`). The
test was added at the L-3 review round (log.md 2026-09-05, "added RED alongside the
parser"); it stayed RED for the wrong reason. **Coordinator/planner action needed**:
fix the test (assert `s.dom.star`) — not the parser. Per my procedure ("if a test
contradicts an ADR, STOP and flag it instead of changing it") I did not touch
`tests/test_parse.py`. This is the ONLY failure in the tree.

## Decisions I did NOT make (all pre-decided; I implemented them)

Nothing semantic was mine. Everything binding carries an ADR/architecture number:
ADR-001 (first-char star, OR rule), ADR-004 (@reboot explain-don't-reject),
ADR-005 (names in month/dow incl. ranges/lists/step bases; illegal elsewhere),
ADR-006 revised (reject `a/s`, rewrite hint), ADR-007 + 2026-09-05 amendment (dialect
naming; crontab-LINE hint), ADR-010 (one error type, code 1 for expression faults),
ADR-012 (reject descending ranges with wrap rewrite), architecture §2 (data structures,
parsing order, field-minimum step expansion, whitespace collapse). Implementation-level
choices the docs left open (exact message wording beyond the asserted fragments,
token-shape test for the amendment, one regex for the element grammar) followed the
architecture and KB; none changes a decided behaviour.

## KB queries run (all `kb.py search --db .pmos/kb.sqlite3 … --role backend -k 5`)

1. "macro table @yearly @daily @reboot expansion" → cron-macros (id 26), live-oracle-probe
2. "field whitespace split crontab line parse" → live-oracle-probe measured verdicts (id 37)
3. "extension rejection L W # ? Quartz dialect error" → "`#` starts a COMMENT" (id 38),
   project/backend "cronx parser behaviour the tests pin" (id 51)
4. "step expansion field minimum vixie get_list star slash" → id 51, cron-dst-transitions
5. "names JUL WED three-letter range endpoints" → cron-field-semantics (id 25)
6. "error message field token exit code 1" → id 51, backend fundamentals

Priority-9 project chunks and the live-oracle probe were trusted over older prose, as
instructed (measured dom 1-31 / month 1-12 ranges, `a/s` rejected, `#` comment trap).

## Verification — exact command outputs

`python3 -m unittest discover -v` (repo root):

    Ran 55 tests in 0.006s
    FAILED (failures=1)

The single failure is the flagged ADR-contradicting assertion above. Breaking it down:

- `python3 -m unittest tests.test_macros -v` → **`Ran 16 tests … OK`** (T-003 green)
- `python3 -m unittest tests.test_parse` → `Ran 38 tests … FAILED (failures=1)`
  (37/38 pass; the 1 failure is the flagged self-contradiction; every ADR-encoded
  assertion — crontab-line hint, Quartz discrimination, star-flag invariant,
  whitespace values — passes)
- `python3 -m unittest tests.test_py39_syntax -v` → OK (3.9 syntax guard green on
  all files incl. the new test_macros.py)
- `python3 /home/madiyar/pm-agent-team/tools/artifacts.py --project . --strict` →
  exit 0: `artifacts OK: every reference resolves, every item is covered`
  (14 req / 12 task / 15 acceptance / 12 decision, 96 refs — ids untouched)
- LOC: `cronx/parse.py` 178, `tests/test_macros.py` 151
- `cronx/parse.py` imports only `re`, `dataclasses`, `typing` — nothing from the
  package; stdlib only.

## Files touched

- `cronx/parse.py` — written (was a 3-line stub docstring from T-001).
- `tests/test_macros.py` — created (TDD, before implementation).
- `tests/test_parse.py` — **NOT modified** (zero edits, zero weakenings).
- `.pmos/out/implementer/notes.md` — this file.

## Unchecked / deferred

- **WhitespaceTest fix** — needs a planner/coordinator decision (fix test, not parser).
- Python 3.9 *runtime* execution (RSK-1): no 3.9 interpreter on host; only the
  ast feature_version guard ran. Reviewer wave (T-010) owns the stdlib-API floor audit;
  my typing usage is 3.9-safe by the KB floor list (no match/case, no PEP-604 unions,
  no 3.10+ APIs — verified by the green T-001 guard).
- Differential `crontab -n` verdicts (T-012) — reviewer wave, out of my scope.
- `--json` / describe / match consumers of `Field.text`/`star` (later chunks) — the
  fields they need are pinned by the green tests here.
- Attempt-1 debris: none found beyond the docstring stub; nothing to clean.

## Wave 2 chunk 2 — T-004 (match.py) + T-005 (occurrences.py)

Implementer run 2026-09-05. Files: `cronx/match.py` (69 LOC, budget 90),
`cronx/occurrences.py` (124 LOC, budget 120 — see deviation note),
`tests/test_match.py` (16 tests), `tests/test_dst.py` (18 tests).

### TDD order kept
Tests written first for each task (test_match.py, then test_dst.py, then both
modules), per attempt-1's lesson. RED confirmed by import errors before
implementation, GREEN after.

### Suite result
`python3 -m unittest discover` (repo root, Python 3.14.4 host):

    Ran 89 tests in 0.013s
    OK

Breakdown: `tests.test_match` → `Ran 16 tests … OK`; `tests.test_dst` →
`Ran 18 tests … OK`; the existing 55 (`test_parse` 38 + `test_macros` 16 +
`test_py39_syntax` 1) → `Ran 55 tests … OK` unchanged. Note: chunk 1's notes
recorded the WhitespaceTest failure as the 1 red; it is now GREEN — the
ADR-007 amendment resolution landed between waves (test fixed, not the
parser; nothing I touched affects it).

`python3 /home/madiyar/pm-agent-team/tools/artifacts.py --project . --strict`
→ exit 0, `artifacts OK`.

### Binding-pseudocode fidelity
- `day_matches` is architecture §3.1 verbatim; `Field.star` read, never
  recomputed (ADR-001 star-flag invariant exercised from both ends:
  `1-31` restricted→OR, `*/2` star→AND-odd-dates crontab(5) worked case,
  `* * MON`→AND, `0`≡`7`).
- `iter_local`: outer date loop bounded by `HORIZON_DAYS = 366 * 9`, cheap
  whole-month skip when the month can't match, hour/minute sorted once
  outside. Horizon exhaustion = clean StopIteration (ADR-008:
  `0 0 30 2 *` and `0 0 31 4 *` yield zero, `0 0 29 2 *` from 2026 finds
  2028-02-29 — pinned exactly).
- `resolve`: gap detected by UTC round-trip (zoneinfo never raises),
  wildcard→[], fixed→integer-second bisection of the architecture snippet
  verbatim (int() timestamps only; the search is provably exact for the
  Lord_Howe 30-min step: 02:00→jump@15:30Z). Ambiguity by fold=0/fold=1
  utcoffset inequality *plus* an instant-equality guard (defensive: a
  zero-length offset change must not be read as a fold); wildcard→both
  passes in instant order, fixed→fold=0 once, ADR-003.
- `next_runs`: one strictly-greater filter (vs after_utc and last emitted) —
  no sort, no buffer (ADR-008/RSK-4); gap collapse pinned via `0,30 2 * * *`
  on 2026-03-08 where both candidates resolve to the same 07:00Z instant.
- `resolve_zone`: ADR-011 two-step diagnosis, exact messages, code 2. Also
  catches `ValueError` (non-relative-path keys — zoneinfo raises that, not
  ZoneInfoNotFoundError, for names with path artefacts) as "unknown
  timezone", never as a false "no tz database". The missing-database branch
  was exercised by hand once via `zoneinfo.reset_tzpath(['/tmp/emptytz'])`
  outside the suite (a permanent test would mutate global interpreter state
  shared with other test modules); its message text is asserted nowhere in
  the suite yet — T-007 owns that pin at CLI level.

### Deviations / judgement calls (flagged per protocol)
1. **occurrences.py 124 LOC vs ~120 budget** — the architecture's "~" budget;
   overage is docstring/comment density, no new machinery. Left as-is rather
   than de-documenting the ADR citations.
2. **`iter_local` reboot guard is eager**: `match.py`'s public entry raises
   `CronxError` code 2 ("@reboot has no wall-clock schedule…", architecture
   §1's ADR-004 note) *before* returning the generator, so a programming
   error surfaces at the call, not at first `next()` — `next_runs` reaches it
   even with `count <= 0`? No: count<=0 returns [] first; the guard fires on
   the real path. Task brief required "raise a clean CronxError code 2 if
   called with one" — eager raising satisfies the strictest reading.
3. **Three of my own fresh tests were wrong before GREEN and were fixed, not
   the code** (TDD-allowed per rules): (a) Lord_Howe — I first assumed the
   2026-04-05 northern-style date; LH is southern-hemisphere, spring-forward
   is 2026-10-04 with the jump at 2026-10-03 15:30Z (verified against
   zoneinfo); (b) fold-day fixed-minute run list — I listed Oct 31 as a run;
   after=2026-10-31T12:00Z is already past Oct 31 01:30 local, correct list
   starts Nov 1 05:30Z; (c) gap-collapse `--from` — placed after Mar 7 02:00
   local so the Mar 7 pair never entered the walk; re-pinned to Mar 8 and
   added the resolve()-level same-instant assertion.
4. **`resolve()` is exported with the architecture's signature**
   `(naive, tz, wildcard) -> List[Occurrence]`; `next_runs` computes
   wildcard itself as `s.minute.star or s.hour.star`. `Occurrence.local`
   carries fold set (0/1 as resolved) per §3.3.

### Import discipline verified
`grep` of the two new modules: match.py imports `.parse` + stdlib
(datetime/typing) only; occurrences.py additionally imports `zoneinfo` — the
only module that does; nothing imports `available_timezones`, `sys`, or the
CLI. 3.9 floor: no match/case, no PEP-604 unions (`Optional[...]`/
`Union[...]` throughout), no now() in tests (all pinned datetimes). Guard
test (test_py39_syntax) covers all four new/changed files and is green.

### Files touched (chunk 2)
- `cronx/match.py` — written (was a 3-line stub).
- `cronx/occurrences.py` — written (was a 3-line stub).
- `tests/test_match.py` — created (TDD-first).
- `tests/test_dst.py` — created (TDD-first).
- `.pmos/out/implementer/notes.md` — this section appended (chunk 1 untouched).

### Unchecked / deferred (chunk 2)
- Missing-tzdb message pinned only by manual probe (T-007's permanent test).
- Python 3.9 *runtime* still unavailable on host; ast guard is the defence
  (same as chunk 1; reviewer wave T-010 owns the stdlib-API floor audit).
- T-008 oracle/monotonicity suites (property test across 3 zones × 5 years)
  remain a later wave; my fixed cases are the unit-level seeds.
