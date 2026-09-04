# ADR-003: DST fall-back — how often an ambiguous wall clock is listed, and which fold

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

On a fall-back day a local wall clock occurs twice: `America/New_York` 2026-11-01 01:30
happens at 05:30Z (EDT) and again at 06:30Z (EST). PEP 495 exposes the two as `fold=0`
(first, still on the pre-transition offset) and `fold=1` (second). The KB records that Vixie
suppresses the repeat for fixed-time jobs, while wildcard jobs — which the daemon fires on
every real minute — run in both passes (KB: `cron-dst-transitions`).

cronx must decide how many entries `--from` … `-n 5` shows for such a time, and it must keep
the emitted list strictly increasing in *instant* while it iterates *wall clock* (RSK-4).

## Options considered

- **A — always once, `fold=0`.** Pro: simplest; the sentence "01:30 daily" reads as one run
  per day. Con: wrong for `* 1 * * *` and `*/10 * * * *`, which really do run twice.
- **B — always twice.** Pro: never hides a real run. Con: wrong for `30 1 * * *`, which
  Vixie runs once; an SRE would go looking for a duplicate batch that never happened.
- **C — Vixie split on the same `MIN_STAR|HR_STAR` flag as ADR-002:** wildcard → twice,
  non-wildcard → once at `fold=0`. Pro: faithful, and reuses machinery already present.
  Con: the two DST ADRs must stay in step; a change to the wildcard test changes both.

## Decision

**C.** For a naive local candidate that is ambiguous (detected as
`naive@fold=0 → UTC` ≠ `naive@fold=1 → UTC`):

- wildcard schedule (`minute.star or hour.star`) → two occurrences, `fold=0` then `fold=1`,
  annotated `dst: "ambiguous_first"` and `"ambiguous_second"`;
- otherwise → one occurrence, `fold=0` — the earlier, pre-transition instant — annotated
  `"ambiguous_first"`.

Both are emitted in instant order, which is also wall-clock order here, so the global
monotonicity invariant (ADR-008) holds without a sort.

## Consequences

- Positive: `30 1 * * *` and `* 1 * * *` in `America/New_York` on 2026-11-01 give visibly
  different answers, which is the truth and is exactly the kind of question the tool is for.
- Positive: choosing `fold=0` for the single case means "the first time the clock reads
  01:30", which is what a reader assumes and what the daemon does.
- Negative: the annotation is always present even in the single-emission case, so a consumer
  cannot use `dst != null` to mean "something was skipped or duplicated"; the specific value
  carries the meaning. Documented in the JSON schema.
- Risks: zones with a fall-back of other than one hour, or two transitions close together,
  are handled by the same code path but are not covered by hand-written cases — the
  monotonicity property test is what covers them.

## Pinned by

T-005 unit tests on `resolve()`; T-008 oracle cases `30 1 * * *` (once) and `* 1 * * *`
(twice) over `America/New_York` 2026-11-01, plus the monotonicity property test asserting
strictly increasing instants across every transition of three zones (including
`Asia/Kathmandu`, +05:45) over five years.
