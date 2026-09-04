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
