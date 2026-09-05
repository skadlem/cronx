# Adversarial requirements review (pre-GATE-2)
Reviewer model: qwen3.8-flash
Date: 2026-09-05

Inputs read: `.pmos/charter.md` (R-001..R-014, A-refs, T-refs), `.pmos/plans/plan.md`
(T-001..T-012, A-001..A-015), `.pmos/out/planner/architecture.md`, all 12 ADRs in
`.pmos/decisions/`, KB chunks via `kb.py search --role qa` (ids 29–32, 54–56), and — only to
check delivered-half claims — `tests/test_parse.py`, `cronx/parse.py`, a full-suite run, and a
live re-probe of `crontab -n`.

## Requirements that failed review (with the checklist item)

- **R-001: AMBIGUOUS (item 2) / consistency** — the charter text still commits to *parsing*
  `a/s` ("`*`, `a`, `a-b`, `a-b/s`, `*/s`, `a/s`, and comma-separated lists of those"), but
  ADR-006 was **reversed at GATE 1 to reject `a/s`** (revision note; I re-verified the probe:
  `crontab -n` on `5/10 * * * *` → "bad minute", exit 1). Two engineers reading the charter
  vs the revised ADR implement opposite behavior and both cite a source. The charter was not
  updated after the revision. ADR-012's descending-range rejection has no home in charter
  text either (R-010's reject-list doesn't mention it). Fix: strike `a/s` from R-001, add
  `a/s` and descending ranges to R-010's reject list.
- **R-001 / A-002: TESTABLE (item 1)** — A-002's WHEN clause still lists `a/s` among the
  forms that "produce the exact documented value set", while its own task T-002's title says
  "rejection of `a/s`". The "or raise CronxError … if malformed" escape hatch makes A-002
  satisfiable both ways; it should enumerate the five post-revision shapes.
- **R-005: AMBIGUOUS (item 2)** — ADR-009 was not updated after ADR-006's reversal: its
  element-phrase table still has an `a/s` row, and its Pinned-by golden-file list still
  includes `5/10 * * * *`, which now cannot be parsed at all. A-006 ("any schedule in the
  golden-file set") therefore has no defined expected output for that entry. Related stale
  artifact: architecture.md §6 says "one `Element` triple covers all six forms" — the
  grammar is five forms post-ADR-006.
- **R-004: AMBIGUOUS (item 2)** — the discriminating oracle for `0 0 */2 * MON` is
  contradictory across three artifacts, and T-008/A-010 must pin one expected value set:
  ADR-001 says AND of "**even** days of the month" (pinned-by repeats "even-numbered
  Mondays"); architecture.md's element table expands `*/s` from the field minimum, so dom
  `*/2` = 1,3,…,31 = **odd**; KB oracle chunk (id=55) says "uneven dates **∪** Mondays
  (leading-star -> AND)" — a union is OR, annotated AND. At most one of these can be the
  expected answer; as written, two competent T-008 implementers will write contradictory
  tests. (Star-flag *mechanism* itself is fine and pinned by T-002's delivered tests —
  verified in `tests/test_parse.py`, the `*`/`5,*`/`*/2`/`1-31` cases match ADR-001.)
- **R-007: UNMEASURED (item 3) / AMBIGUOUS (item 2)** — the clause "zones whose rules
  changed historically" has no criterion anywhere: A-011's five-year window (~2026 backward)
  cannot contain a historical tz-rule change, and no other A-NNN touches it. Worse, A-011's
  "three zones (including a non-whole-hour offset)" are **never named** in plan.md,
  architecture.md, or ADR-003 — only the KB chunk suggests `Asia/Kathmandu`. Two engineers
  pass A-011 with different zone sets and different schedule densities. Fix: name the three
  zones and the `--from` anchor in A-011, or drop the historical-rule clause from R-007.
- **R-008: TESTABLE (item 1), minor** — "`--json` emits a documented, **stable**
  machine-readable object": no criterion measures "stable" (A-007 checks keys present,
  A-012 checks README agreement — neither pins schema stability). The charter elsewhere
  refuses API-stability promises (§0.6, §4); "stable" as written is an unchecked adjective.
  Strike it or define it (e.g., "keys listed in README.md, verified by A-012").

Requirements that survived all six checks: R-002, R-003, R-006, R-009, R-010 (text matches
ADR-007's reject table, and I re-verified three of its probe claims live), R-011, R-012,
R-013, R-014. (R-012's *coverage strength* depends on item 6's corpus note below.)

Checklist item 4 (DEPENDENCY) passes: every T-001..T-012 satisfies an existing R-NNN; every
R-001..R-014 is claimed by ≥1 task; every T-NNN is verified by ≥1 A-NNN (A: T-001→A-001,
T-002→A-002, T-003→A-003, T-004→A-004, T-005→A-005, T-006→A-006, T-007→A-009, T-008→A-010+
A-011, T-009→A-007+A-008, T-010→A-013+A-014, T-011→A-012, T-012→A-015). No orphan R, no
orphan T. Minor wrinkle, not a failure: A-004's "exit 0" clause is only observable through
the CLI (T-009/T-008), not through T-004's own test file.

Checklist item 6 (RISK-BLIND) mostly passes: RSK-1→T-001(A-001)+T-010(A-013/A-014), residual
explicitly accepted and disclosed; RSK-2→T-012(A-015) with residual (runtime semantics,
ADR-012 empty-set inference) explicitly accepted; RSK-3→T-006(A-006); RSK-4→T-008(A-011);
RSK-5→T-007(A-009). One soft spot: A-015's "corpus of expressions" is never enumerated
(KB id=56 lists the deliberate divergences but not the corpus), so RSK-2's mitigation
strength is whatever the reviewer happens to write — pin the corpus to the ADR Pinned-by
cases plus the `cron-live-oracle-probe` transcript.

## Missing requirements (concrete scenarios)

- **The charter's own named user pastes a crontab *line*, not a bare expression.** §0.3/§2
  say the SRE is "holding a crontab line they did not write"; a real crontab line ends in a
  command. `cronx '0 0 13 * FRI /usr/bin/backup'` hits ADR-007's six-field error and is told
  this is "Quartz/Spring syntax" — a wrong diagnosis for the single most likely first input
  (it's a POSIX crontab line with a command; `crontab -n` on such a line *accepts* it,
  verified here). The charter's "no crontab-file parsing" non-goal doesn't say what the
  six-field-plus-command case should do, and A-003 pins the misleading message. Decide: a
  dedicated hint ("if your line includes a command, pass only the first five fields") or an
  explicit accepted-wrong-answer note.
- **No stated behavior for leading/trailing or doubled whitespace** inside the quoted
  EXPRESSION (e.g. `'0  0 * * * '` from a copy-paste). Unspecified whether parse() splits on
  whitespace or on single spaces; A-002 doesn't cover it; two engineers differ. One sentence
  in the CLI contract fixes it.
- **Default `--from` is "now", i.e. the only nondeterministic path**, and no criterion
  asserts anything about the default-mode text output beyond A-008's zone line. Acceptable
  as an R-014 consequence, but worth stating that no oracle test may run without `--from`
  (currently true in the plan — verified by reading T-008's pinned cases).

## Delivery-state notes (not requirement failures)

- Verified live: `crontab -n` exists, is syntax-only, installs nothing (user crontab still
  absent after probing), and reproduces ADR-006's rejection of `5/10`, ADR-012's acceptance
  by host cron of `22-2`, and ADR-005's acceptance of `MON-FRI`. RSK-2's probe claims check
  out.
- Repo state at review time: `cronx/*.py` are docstring stubs; `tests/test_parse.py` (201
  lines) exists and matches the *revised* ADR-006/ADR-012 direction (rejects `5/10` with the
  rewrite hint, rejects `FRI-MON`/`NOV-FEB`), but `python3 -m unittest discover` is currently
  RED (`ImportError: cannot import name 'CronxError'` — parser not yet written). Expected
  mid-chunk-1 per the gate2 note's sequencing deviation, but it contradicts charter §9's
  "each task ships with its own tests green before handoff" until the parser lands.
  `unchecked`: whether this is transient.

## Verdict

**CONCERNS — fix the listed items first.** The charter was not re-synced after GATE 1:
R-001/A-002 still promise a syntax that revised ADR-006 forbids, ADR-009's golden set pins a
sentence for a now-unparseable expression, and the project's headline OR-rule oracle case
(`0 0 */2 * MON`) has three mutually inconsistent expected answers across ADR-001, the
architecture's expansion table, and the KB chunk that T-008/A-010 must cite. These are
text-level fixes (charter, plan A-002, ADR-009, ADR-001's parenthetical, name A-011's three
zones), each one commit, but they sit directly on the acceptance tests — approving now
guarantees contradictory test-writes in the next wave. Everything else (dependency map,
risk register, R-002..R-014 individually) holds.

## Re-review (2026-09-05)

Re-reviewer model: qwen3.8-flash (independent worker). Scope: verify the six prior fixes only.
Inputs re-read: charter (incl. §0.6 as re-synced at GATE 1 — the VERIFIED/RESOLVED premise
bullets are the coordinator's separate fix and are consistent with RSK-2), plan
(A-002/A-003/A-011/A-015), architecture §2/§6, ADR-001/006/007/009/012,
kb-sources/project/{qa,backend,architect}.md, kb-sources/domain/cron-dom-dow-or-rule.md,
tests/test_parse.py (new tests), and `artifacts.py --project . --strict`.

Per-finding verification:

1. **R-001 / A-002 — FIXED.** Charter R-001 lists only the five post-revision forms with an
   explicit removal note; R-010 now names bare `a/s` (ADR-006) and descending ranges (ADR-012);
   A-002's WHEN clause enumerates exactly the five shapes and moves `a/s`/descending into the
   reject branch; T-002's title matches. No artifact still promises `a/s` parses (the only
   remaining `a/s` mentions are the removal notes themselves).
2. **OR-rule oracle — FIXED and consistent.** ADR-001 (decision + Pinned-by, with correction
   note), architecture §2, and kb-sources/project/qa.md now all say `0 0 */2 * MON` = odd dates
   AND Mondays. Sanity-check of the stated expansion rule: Vixie `get_list` steps from the
   field minimum, dom min = 1 → `*/2` = {1,3,…,31} = odd — matches crontab(5)'s verbatim
   "uneven date" worked case quoted in the KB domain chunk; minute `*/2` = {0,2,…}. No
   `crontab -n` was run for this (syntax-only oracle; prior review's note stands).
3. **ADR-009 — FIXED.** No `a/s` row in the element-phrase table (removal note present); the
   golden list replaces `5/10 * * * *` with `0-59/15 * * * *`, which keeps the `a-b/s` phrase
   pinned and parses. Architecture §6 "six forms" corrected to "five".
4. **A-011 — FIXED.** Three zones named (America/New_York 1 h, Australia/Lord_Howe 30 min,
   Asia/Kathmandu permanent +05:45), window 2022-01-01..2026-12-31, `--from` pinned, schedules
   (`* * * * *` per transition window + `*/17 * * * *` per zone-year). Charter R-007's clause
   now delegates to "pinned zones named in A-011" and describes exactly what A-011 measures;
   the unmeasurable "rules changed historically" criterion is gone.
5. **A-015 corpus — FIXED.** The note pins the corpus (KB `cron-live-oracle-probe` transcript
   cases + every ADR "Pinned by" expression + per-field boundary tokens, 40 minimum). No
   longer reviewer's choice.
6. **ADR-007 amendment + whitespace contract — COHERENT.** The command-shape hint is one
   `startswith()` test on token 6 (`/`, `~`, `./`) — no command parsing, no crontab-file
   reading; charter §4 non-goals untouched and §4 already framed the "no crontab-file parsing"
   boundary. A-003's form was amended to match the hint exception. Architecture §2's
   `str.split()`-style whitespace collapse matches the prior review's suggested one-sentence
   fix. New tests match the amended contracts exactly:
   `test_crontab_line_gets_the_command_hint` (`'0 0 13 * FRI /usr/bin/backup'` → message
   contains "crontab LINE", not "Quartz"), `test_six_field_quartz_year_still_blames_quartz`
   (`'0 0 2 * * 2026'` → Quartz), `test_leading_trailing_and_double_spaces_parse` (spaces +
   tab, `hour.star` true) — all consistent with ADR-007 amendment and architecture §2.

Machine check: `python3 /home/madiyar/pm-agent-team/tools/artifacts.py --project . --strict`
→ exit 0 (14 requirements, 12 tasks, 15 acceptances, 12 decisions, 96 refs, all resolve).
`tests/test_parse.py` still RED at the import (cronx/parse.py is a stub) — unchanged from the
prior review's delivery-state note; not a planning-artifact failure.

Residual nits introduced/left by the fixes (text-level, none change a test expectation):

- **ADR-001 stale context/residual lines**: the Context still says "There is no cron daemon on
  this host to diff against (RSK-2)" and the Residual-uncertainty bullet still claims the
  literal-`*` rule "cannot be diffed against a live cron here" — both contradict the amended
  Decision paragraph (which cites crontab(5) verbatim) and charter §0.6/RSK-2 post-GATE 1.
  The GATE 1 question is closed; these two sentences should be retired in the next ADR touch.
- **kb-sources/project/backend.md line 25**: "One Element triple covers all six forms" — the
  stale twin of the architecture §6 sentence that was fixed. Same file's line 4 lists the five
  forms correctly, so the implementer gets the right behavior from the first read, but the
  file is now self-contradictory.
- charter R-007's phrase "historical offset steps" survives in softened form; with the
  "(pinned zones named in A-011)" delegation it is now measurable, but Kathmandu's role in the
  window is the *permanent* offset, not a step — cosmetic.

None of these creates a second source of truth for any A-NNN acceptance: every normative
statement (R-001, R-005, R-010, A-002, A-003, A-009, A-011, A-015, ADR-001 decision, ADR-006
table, ADR-009 table+golden, architecture §2, qa.md, backend.md line 4) agrees.

**PASS** — all six findings are fixed and mutually consistent; carry the three residual nits
into the next artifact touch (suggest the reviewer fixes backend.md:25 and ADR-001's stale
sentences opportunistically with the parser commit).
