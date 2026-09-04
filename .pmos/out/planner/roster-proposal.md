# cronx: roster proposal

Owner: planner (PM + architect) | Updated: 2026-09-04

## Roster: confirm the lean team (planner / implementer / reviewer)

- **planner** — this wave already produced the only artifacts that need product/architecture
  judgment (charter, ADRs, architecture, plan); nothing left needs a fourth perspective.
- **implementer** — the whole build is one dependency chain in one language, one repo,
  ~600 LOC across five modules (architecture §1); a single build role is sufficient, no
  frontend/backend split exists to justify.
- **reviewer** — T-010's stdlib-API floor audit is the one check the implementer structurally
  cannot self-certify (RSK-1b: the dev host has no 3.9 interpreter to run against), so a
  separate reviewer role is load-bearing, not ceremony.

No designer, QA, devops, or business role is justified: no UI, no separate QA phase (tests
ship inside each task per `test_strategy`), no deployment surface (§8: N/A), no demand
question left open (charter §0 already closed it). **Confirmed: keep the three-role roster.**

## Wave 2 parallelism: one implementer, not several

Dependency graph (architecture §1): `cli -> {parse, match, occurrences, describe}`,
`occurrences -> {parse, match}`, `match -> parse`, `describe -> parse`.

- `parse` (T-001–T-003) is the one dependency everything else has, directly or
  transitively — it must land first and is inherently sequential.
- After `parse` lands, `match` (T-004) and `describe` (T-006) depend only on `parse`, not
  on each other — that is the one genuine fork where two workers could run concurrently.
- `occurrences` (T-005) depends on `match`, so it cannot start until T-004 lands even if
  `describe` is still in flight.
- `cli` (T-009) depends on all four, so it is always the last task before phase 3's
  error-path and verification work (T-007, T-008, T-011, T-010).

**Recommendation: one implementer, sequential.** The parallel window is two tasks
(T-004/T-006) out of nine implementer tasks on a ~600 LOC codebase — the coordination cost
of a second worker (context handoff, shared `tests/` layout, two review cycles instead of
one) exceeds the few hours saved by running that one fork concurrently. Revisit only if the
codebase estimate turns out to be badly wrong once T-002/T-003 are actually built.
