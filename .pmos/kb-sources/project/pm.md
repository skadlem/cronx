# cronx — pm facts

## cronx phases and task order
Phase 1 parse (T-001 skeleton+3.9 guard, T-002 parser, T-003 macros) -> Phase 2 match/iterate
(T-004 day rule+iterator, T-005 tz+DST+dedupe) -> Phase 3 explain/serve (T-006 describe+golden,
T-009 CLI, T-007 tz-error path) -> Phase 4 verify (T-008 oracle+monotonicity, T-012
differential vs crontab -n, T-011 README, T-010 reviewer audit+report). Implementation runs as
4 sequential implementer chunks, one per phase (rate-limit exposure cut at the dependency
boundary). T-012 and T-010 belong to the reviewer role, not the implementer.

## cronx risks and their live state
RSK-1 3.9 unverifiable by execution: CERTAIN/high, mitigated by T-001 guard + T-010 audit;
residual accepted and disclosed. RSK-2 oracle risk: DOWNGRADED to low/low at GATE 1 after the
live `crontab -n` probe (it reversed ADR-006, spawned ADR-012, corrected ADR-005's premise);
residual = syntax-only oracle, DST semantics stay KB-backed. RSK-3 English-output scope creep:
ADR-009 closed grammar + golden file. RSK-4 ambiguous-hour ordering bug: the strictly-greater
dedupe filter + T-008 monotonicity property test. RSK-5 missing tzdata: ADR-011 precise exit-2
error. Infrastructure pattern so far: wave-1 planner died on a 429 session limit, wave-2 chunk 1
on ConnectionRefused, retry also 429 (resets 4:30 HKT) — both ledger-recorded as failed runs.
