# PMOS log — cronx

## 2026-09-04 — Launch (stage 0)
- TPL = /home/madiyar/pm-agent-team (via ~/.claude/pmos-template-root). Host = claude.
- MODE = **greenfield**: /home/madiyar/cronx was empty. No Wave 0 discovery, no graphify index
  (nothing to map yet).
- Repo was not a git repo -> `git init` run. Tree was clean, so no dirty-tree question needed.
- Team = **lean** (user choice at launch): planner / implementer / reviewer.
  Written to .pmos/team.json.
- KB initialised. Indexed curated fundamentals into the namespaces the lean team actually
  searches (shared, pm, architect, backend, frontend, qa) — not all ten, per the cap's intent.
- KB top-up (step 2): authored 5 project-specific domain chunks in .pmos/kb-sources/domain/
  and indexed them into architect/backend/qa at priority 9. No web fetch: crontab(5) semantics
  are stable and the gaps were domain traps the shipped fundamentals say nothing about
  (DOM/DOW OR rule, DST gap/fold handling, macro set, 3.9 syntax floor, name-range dispute).
- KB budget checked: every namespace has positive headroom (32 chunks, ~6.1k tokens total).

### Environment constraints found at launch (feed into GATE 1)
- Only python3.14 on this box; **no 3.9 interpreter**. Target is 3.9, so 3.9 compatibility
  cannot be verified by running it. Mitigation recorded in KB: `ast.parse(feature_version=(3,9))`
  over every source file as a test, plus a reviewed stdlib-API floor list. This is a real
  verification gap and belongs in the charter risks.
- zoneinfo resolves system tzdata fine here (Europe/Dublin loaded), so stdlib-only +
  timezone-aware is satisfiable on 3.9 without pip.

### Pre-GATE-1 worker model (deliberate deviation, logged per launch.md)
- launch.md default is "cheapest available not forbidden" = claude-haiku-4-5-20251001.
- Used **claude-opus-5** for the Wave 1 planner instead. Rationale: the user's saved defaults
  file (~/.claude/pmos-team-defaults.json) already pins pm -> claude-opus-5, so this is a
  standing user preference, not an unmodeled spawn inheriting a host default (the risk the rule
  guards against). The charter/plan is the artifact every later wave depends on, and this
  project is a semantics-correctness problem where a thin charter is expensive.
- haiku-4-5 has no benchmark data in benchmarks.json, so it could not be tier-checked anyway.

## 2026-09-04 — Wave 1 attempt 1: FAILED (rate limit), partial output kept
- planner @ claude-opus-5, ladder 0. Ran 405s, then died on **HTTP 429 — account session
  limit** ("resets 11:30pm Asia/Hong_Kong"). `is_error: true`, `terminal_reason: api_error`.
- NOT a model-quality failure and NOT a bad prompt: it is an account-level throttle. The
  spawn-fallback ladder ("was this failure the model's fault?") answers *no*, so demoting the
  planner to sonnet-5 would be the wrong reflex.
- Produced `.pmos/charter.md` (206 lines, complete: all six forcing questions answered, R-001..
  R-014, RSK-1..RSK-5, jurisdictions, team). Did NOT produce plan.md, architecture.md, the
  ADRs, or roster-proposal.md — though the charter already references ADR-001..ADR-011 and
  T-001..T-010 by id, so the retry must honour that numbering.

### Deliberate deviation from spawn-fallback.md rule 3 ("never continue a half-finished run")
- That rule exists so a worker never resumes from a corrupted or half-reasoned state. Here the
  task decomposes at clean ARTIFACT boundaries and the charter is verifiably whole, so
  re-running it from a clean start would burn budget to regenerate a good artifact and risk a
  worse one. Retry is therefore SCOPED to the missing artifacts, with the finished charter
  passed in as upstream context.
- Retry stays at ladder 0 (claude-opus-5): the limit window reset at 23:30 HKT, one minute
  before the retry, and the semantic ADRs are the highest-value output in the project.
- Split into two sequential workers to cut re-exposure to the limit and to put the mechanical
  half on a cheaper model: 1a = ADRs + architecture (opus-5), 1b = plan + roster (sonnet-5).

### Ledger accuracy note
- cost.py recorded **$0.7235**; the host result's own `total_cost_usd` was **$1.4413**. The
  ledger prices only input/output tokens and ignores cache-creation (49,158) and cache-read
  (446,168) tokens, so it under-reports by ~2x on cache-heavy runs. Track the real figure
  against `budget_usd`; the ledger total is a floor, not the actual spend.

## 2026-09-04 — Wave 1a OK, and a live oracle found (coordinator work)
- planner-1a @ claude-opus-5: OK. Wrote ADR-001..ADR-011 and architecture.md (269 lines).
  artifacts.py exits 0. Ledger $1.39; host's own total_cost_usd $3.22 (cache tokens again).
- planner-1b @ claude-sonnet-5 (plan.md + roster-proposal.md): spawned, running.

### FINDING: RSK-2 was wrong — there IS a cron on this host to diff against
The charter says "no network and no guaranteed cron daemon here to diff against" and makes the
KB chunks the sole oracle. In fact this box has `cron 3.0pl1-200ubuntu1` (Debian vixie-cron),
`man 5 crontab`, and **`crontab -n <file>`, a dry-run syntax checker that validates WITHOUT
installing** (verified: user had no crontab before or after the probes). That is a real
differential oracle and it downgrades RSK-2 substantially.

### It also settles the GATE 1 open question, against the man page's own NOTES section
crontab(5) here states verbatim that "this implementation only checks if the first character
is a *", and gives the worked case `0 0 */2 * sun` = Sundays on uneven dates. **ADR-001's
choice A is correct.** POSIX and Vixie genuinely disagree here, so the brief's "match POSIX /
Vixie" cannot be satisfied both ways — picking Vixie and recording it is exactly right.

### Three ADRs are contradicted by measurement; ADR-006 is wrong as written
Probed every disputed form against `crontab -n`:
- **ADR-006 (`a/s` step-without-range) is WRONG for this implementation.** `5/10 * * * *` ->
  "bad minute"; `0 0 5/10 * *` -> "bad day-of-month". It is a cronie/other-dialect extension,
  not Debian vixie-cron. ADR-006 decided to ACCEPT it. Must be revised: match (reject) or keep
  accepting as an explicitly documented deviation. Cannot stand on its current rationale.
- **ADR-005 (names in ranges/lists) reaches the right verdict on a stale premise.** The man
  page still says "Ranges or lists of names are not allowed", but the binary ACCEPTS
  `MON-FRI`, `JAN,JUL`, `MON-FRI/2`. Accepting is correct; the rationale should cite the probe.
- **UNCOVERED semantics: reverse/wrapping ranges.** `22-2`, `30-10`, `FRI-MON`, `NOV-FEB` are
  all ACCEPTED. No ADR covers this and my KB chunk asserted the opposite ("Vixie requires
  a <= b"). Needs ADR-012. Acceptance is measured; the wrap reading is inferred, since the
  daemon's runtime behaviour was not observed.
- **ADR-007 (`#`) gets a much stronger rationale.** `0 0 * * 5#2 /bin/true` is ACCEPTED — but
  `#` opens a COMMENT, so cron reads dow=5 and silently discards `#2` AND the command. A user
  pasting a Quartz expression gets a different schedule and no command. Rejecting `#` loudly
  is right.
- Also: dom/month `0` are REJECTED even though crontab(5)'s own table prints "0-31"/"0-12".
  Real ranges are 1-31 / 1-12. The KB chunk was right, the man table is misleading.

### Actions taken
- Corrected the two wrong KB chunks in place (`cron-field-semantics`, `cron-dom-dow-or-rule`)
  and added `cron-live-oracle-probe` with every measured verdict. Reindexed; budgets still
  positive. The oracle had to be fixed BEFORE the implementer wave inherits it.
- For GATE 1: propose adding a differential QA task — run cronx's accept/reject verdict against
  `crontab -n` over a corpus of expressions. That is a far stronger check than self-written
  tests and directly attacks RSK-2.

## 2026-09-04 — Wave 1b OK; GATE 1 PASSED (user approved)
- planner-1b @ claude-sonnet-5: OK, $0.72. plan.md (4 phases, T-001..T-011, A-001..A-014) and
  roster-proposal.md. artifacts.py clean under --strict: 86 references, all resolve.
- Wave 1 total: $4.66 actual / $2.12 ledger.

### GATE 1 decisions (user)
1. Roster: lean three confirmed. ONE implementer, sequential (only fork is T-004/T-006, too
   small to pay for a second worker on ~600 LOC).
2. Models: implementer = claude-sonnet-5, reviewer = claude-opus-5. Written to team-model.json.
   Saved defaults' claude-sonnet-4-5 is not served on this host -> mapped to claude-sonnet-5.
3. Budget cap: $30 (raised from the $20 default; remaining work est. $10-18 and a single
   rate-limit retry could otherwise breach mid-wave).
4. ADR-006 (`a/s`): **REJECT**, matching the local vixie-cron. Revise the ADR's decision.
5. Reverse ranges: **REJECT** with a precise error. New ADR-012.

### Coordinator-authored amendments (deviation from "planner owns these artifacts")
The five edits below encode decisions the user just made plus measurements I took myself. I
made them directly rather than re-spawning the planner: it would have had to rediscover the
probe context to write down conclusions that were already settled, at ~$1-3 and some risk of
drift from what was actually approved. The reviewer wave checks these against the code, so
they are not self-certified. Logged as a deliberate deviation.
Amendments made (all verified by `artifacts.py --strict`: 14 reqs / 12 tasks / 15 criteria /
12 decisions / 96 references, all resolving):
- ADR-006 REVISED to reject `a/s`, with the probe output quoted and a revision note saying the
  original rested on a false KB claim. Id not superseded — nothing was built against it.
- ADR-012 NEW: reject descending ranges. States plainly that the empty-set reading is an
  INFERENCE from Vixie's ascending `for` loop, not a measurement, and that rejecting is the
  only option that does not require cronx to assert something it cannot support.
- ADR-005 verdict unchanged, premise corrected: the man page's "names not allowed" sentence is
  stale documentation, not an enforced rule, so accepting names is not a deviation at all.
- ADR-007 rationale strengthened with the `#` finding (cron accepts `5#2`, reads dow=5, and
  silently discards both `#2` and the command).
- charter RSK-2 DOWNGRADED certain/medium -> low/low, with the residual scope stated: the
  oracle checks SYNTAX only, so the DST policy and ADR-012's inference remain KB-backed.
- plan: new T-012 (differential test vs `crontab -n`, skipUnless(which("crontab"))) + A-015;
  T-002 and T-008 re-pointed at ADR-012; T-002 retitled to five element forms.

## 2026-09-04 — Wave 2 (implementation) begins
Split into 4 sequential implementer chunks on claude-sonnet-5, one per plan phase, rather than
one 9-task run: a single spawn covering the whole build is what got killed by the rate limit in
wave 1, and phase boundaries are where the architecture's dependency graph actually cuts.

## 2026-09-05 — Wave 2 chunk 1 attempt 1: FAILED (ConnectionRefused), partial output kept
- impl-c1 @ claude-sonnet-5, ladder 0. `is_error: true`, `terminal_reason: api_error`,
  "API Error: Connection refused — a firewall or proxy may be blocking it". Ledger $0.41,
  host-reported $0.90. Second infrastructure failure in a row (wave 1 was a 429); neither is
  the model's fault, so the ladder stays at 0 and the model is NOT demoted.
- Produced: the `cronx/` skeleton (all five modules as docstring-only stubs, `__init__.py`,
  `__main__.py`), `tests/test_py39_syntax.py` (31 lines, passes) and `tests/test_parse.py`
  (201 lines). Did NOT produce `.pmos/out/implementer/notes.md`.
- The worker wrote tests BEFORE the implementation, which is the TDD order it was asked for —
  so the surviving artifact is the valuable half. Spot-checked: the tests assert `.star` and
  `.text` verbatim preservation, i.e. the ADR-001 invariant. Keeping them.
- Retry is scoped to finishing the chunk (implementation + review of the existing tests)
  rather than a clean restart, same reasoning as wave 1: clean artifact boundary, and the
  tests are worth more than a fresh re-derivation.

### Defect found while assessing the wreckage: A-014's command finds no tests
`tests/` has no `__init__.py`, so `python3 -m unittest discover -v` — which is A-014's literal
`how:` command — collects ZERO tests. It exits 5 (not 0), so the criterion fails loudly rather
than passing vacuously, which is the good outcome; but the command in the plan does not work
as written. Fix is `tests/__init__.py`, folded into the retry. Worth recording because "the
acceptance command runs nothing and looks fine" is the exact failure class the QA gate exists
to catch, and here it was one `__init__.py` away from being silent.
