# Wave 2 chunk 2 spawn prompt (verbatim of what was dispatched, deleg_875c093f)
# 2026-09-05 13:58 HKT, T-004 + T-005, qwen3.8-flash via delegate_task.
# See the child context for the full binding text; key points:

- T-004 match.py: day_matches per architecture §3.1 VERBATIM (month gate; AND if
  s.dom.star or s.dow.star else OR; dow = d.isoweekday() % 7). iter_local bounded by
  HORIZON_DAYS = 366*9, sorted(hour)/sorted(minute) computed once outside the loops,
  strictly-after, ascending; exhaustion = stop, not error.
- T-005 occurrences.py: Occurrence dataclass per §3.3; resolve_zone with UTC-probe
  discrimination (ADR-011, code 2); wildcard = minute.star or hour.star (never recomputed);
  integer-second binary search for the gap jump instant EXACTLY as written (float timestamps
  forbidden); gap wildcard->[], fixed->gap_shifted@jump w/ nominal; fold wildcard->both,
  fixed->ambiguous_first; next_runs single strictly-greater filter (no sort/buffer).
- TDD: tests/test_match.py + tests/test_dst.py written FIRST (discriminating set: 0 0 13 * FRI
  OR; 0 0 */2 * MON AND odd; 0 0 30 2 * found Feb 29 2028; NY gap 2026-03-08; NY fold
  2026-11-01; Lord_Howe 30-min; Kathmandu +05:45; pinned datetimes, never now()).
- STOP-and-flag if an existing committed test contradicts an ADR (chunk-1 precedent upheld).
- Touch only: cronx/match.py, cronx/occurrences.py, tests/test_match.py, tests/test_dst.py,
  .pmos/out/implementer/notes.md (append).
