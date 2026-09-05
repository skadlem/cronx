# cronx — GATE 2 coordinator notes (living file)

## Step 7 jurisdiction pack — skipped with reason
Charter section 8 records deployment jurisdictions as N/A (offline local CLI, no data
collection, no distribution surface beyond the source repo). config legal_strict=true, but
state.py's missing-jurisdiction WARN is informational (stage came from later evidence). The
country-by-country legal pack is conditional on the charter field; it is N/A here. Logged so
the QA gate does not chase it.

## L-3 adversarial review — outcome (2026-09-05)
Verdict CONCERNS with 6 findings; all fixed in-artifact (charter R-001/R-007/R-008/R-010,
A-002/A-003/A-011/A-015, ADR-001 "even->odd" correction, ADR-009 a/s row+golden, ADR-007
crontab-line amendment, architecture §2 expansion+whitespace, 3 new RED tests). Headline
catch: the `0 0 */2 * MON` oracle case contradicted itself across ADR-001 / my KB chunk / the
architecture expansion table; reference (crontab(5) NOTES worked case) says odd dates AND
Mondays. Re-review subagent verifies before the gate is presented. Full detail: log.md
2026-09-05 L-3 entry.

## Risk-register shape at GATE 2 (as of 2026-09-05, pre-reviews)
Charter risks are RSK-1..RSK-5 (likelihood/impact style; no L-NNN register exists — that is the
expensive roster's legal artifact). No risk is both high-impact AND open: RSK-1 (certain/high)
is mitigated by T-001 + T-010 with the residual explicitly accepted by the user at GATE 1;
RSK-2 was downgraded to low/low at GATE 1; RSK-3/4/5 carry mitigating tasks (T-006, T-008,
T-007). The wave2.md second-opinion trigger ("whenever a high-severity open risk exists at this
gate") is therefore read as NOT fired for a new high+open risk; the reviewer's audit role still
checks the mitigations hold. If any high+open risk appears before the gate closes, the second
opinion re-arms (recommend.py second-opinion --pm-model claude-opus-5 --available
.pmos/available-models.txt).

## GATE 2 sequencing deviation — recorded
GATE 1 approved plan + ADRs + models and implementation began the same day, so the pre-GATE-2
adversarial review (L-3) lands AFTER chunk 1's tests exist. The review sees the artifacts as
planned; its findings on the running build go into the next implementer spawn. Flagged because
wave2.md orders the review pre-build.

## Complexity report (wave2.md requires it at the gate)
complexity.py flags 12/12 tasks at/above threshold with "consider splitting". Pre-approved
mitigation decided at GATE 1: implementation runs as 4 SEQUENTIAL chunks of 2-4 tasks on ONE
implementer (lean roster, ~600 LOC, dependency graph is a chain — splitting T-009 further adds
interfaces, not clarity). Justification stands unless the gate user says otherwise; per-task
test_strategy: lines present on all 12 (grep of plan.md).
