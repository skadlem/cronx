# Project Charter: cronx

Status: draft | Owner: planner (PM + architect) | Updated: 2026-09-04

## 0. Before you write this charter (forcing questions)

1. **Demand reality.** There is no independent demand evidence and this charter will not
   pretend otherwise: **this is a developer utility the user asked for, and comparable tools
   already exist (crontab.guru, croniter, cron-descriptor).** The only honest signals are
   (a) the user's explicit request, and (b) the fact that three separate tools exist to do
   "explain this cron line" and "when does it next fire" — the job is real and recurring, it
   is just already served *when you have a browser or a package manager*. Questions 4 and 5
   carry the weight here, not this one.
2. **Status quo.** Today you paste the expression into crontab.guru (needs a browser, needs
   outbound network, and hands your production schedule to a third party), or you
   `pip install croniter` and write a throwaway script (needs network and a venv, and gives
   you no English explanation), or you read `crontab(5)` and reason by hand — which is exactly
   where the day-of-month/day-of-week OR rule and DST gaps produce confidently wrong answers.
   None of the three work on a host with no pip and no egress.
3. **Desperate specificity.** The SRE or on-call engineer on a hardened or air-gapped
   production host, mid change-review or mid-incident, holding a crontab line they did not
   write. Named case: they must answer "does `0 0 13 * FRI` fire only on Friday the 13th?"
   (it does not — it fires every 13th *and* every Friday) and "what are the next runs of
   `0 2 * * *` in `America/New_York` across 2026-03-08, when 02:00 local does not exist?".
   They cannot install anything and cannot paste the line into a website.
4. **Narrowest wedge.** One command, one expression, one answer:
   `cronx '<expr>' [--tz ZONE] [-n N] [--json]` prints one English sentence plus the next N
   run times, and exits non-zero with a precise error if the expression is invalid. Five
   fields and the `@`-macros. Nothing else: no crontab-file parsing, no config file, no plugin
   or extension mechanism, no packaging/registry, no library API promise, no daemon.
5. **Alternatives considered.**
   - **(a) `pip install croniter` (+ `cron-descriptor` for the English).** Mature and
     battle-tested. Loses on three counts: it is a pip+network dependency, which is *the*
     binding constraint of the brief; croniter produces no English explanation, so it does not
     satisfy the primary requirement even with the constraint lifted; and croniter makes the
     day-of-month/day-of-week rule a *configuration flag* (`day_or=`), so you still have to
     decide the semantics yourself — you have merely traded owning a documented decision for
     auditing someone else's default. Not a wedge, and not compliant.
   - **(b) Vendor croniter's source into the repo.** Satisfies "no pip install" literally, but
     carries ~1.5k lines of third-party semantics and its license, still ships no English
     output, pulls in `dateutil` in places, and makes the ADR trail dishonest: we would be
     shipping deviations we never decided. Rejected.
   - **(c) Shell out to the platform.** `systemd-analyze calendar` does exactly "explain +
     next N runs" — for *systemd calendar* syntax, not cron syntax, and only on systemd hosts.
     Wrong grammar and not portable. Rejected.
   - **(d) Write it: stdlib only, ~600 LOC over five small modules.** Wins because the domain
     is small and fully specified by `crontab(5)`: a field is a set of ints over a bounded
     range and "next run" is a bounded calendar search. The expensive part of this project is
     not the code, it is *deciding the ambiguous semantics* — and that cost is identical under
     every alternative above. (d) is the only option where paying it produces an artifact.
6. **Premises challenged.**
   - VERIFIED: `zoneinfo` is stdlib from 3.9 and resolves system tzdata on this box
     (`Europe/Dublin` loads). Stdlib-only + timezone-aware is satisfiable.
   - VERIFIED: this host has only python3.14; there is **no 3.9 interpreter**. 3.9
     compatibility cannot be verified by execution. → risk, section 7.
   - BELIEVED, not verified: the Vixie/POSIX semantics recorded in the KB domain chunks are
     accurate. There is no network and no guaranteed `cron` daemon here to diff against.
     Mitigation: every semantic claim becomes a named test citing its KB chunk as the oracle;
     a later correction is an ADR supersession, not a silent edit.
   - BELIEVED: POSIX text and the deployed Vixie/cronie implementation agree. They do **not**
     agree on whether `*/2` in the day field counts as "restricted" — see ADR-001, which
     picks the implementation and flags the residual uncertainty. This is the one open
     question for GATE 1.
   - ASSUMED: "plain-English explanation" is satisfied by a deterministic templated sentence,
     not crontab.guru-grade prose for every combination. Fixed by ADR-009; reversible.
   - ASSUMED: the user wants a CLI, not an importable library. The brief says CLI; the
     internals stay import-clean because that is free, but no API stability is promised.

## 1. Problem and goal

Reading a cron expression correctly requires knowing several traps that the syntax does not
advertise: day-of-month and day-of-week are OR'd rather than AND'd when both are restricted,
`*/n` and `a/n` mean different things than they look like, names are legal in only two fields,
and a local wall-clock schedule crossing a DST boundary either loses an hour or repeats one.
Existing tools that answer these questions need either a browser and network egress or a
package install. cronx answers them offline, from the standard library, on the host where the
crontab actually lives. Solved looks like: one command, one sentence of English, N correct
instants in a named timezone, and a precise error instead of a wrong answer.

## 2. Users / beneficiaries

Primary: SREs, sysadmins and backend engineers on locked-down or air-gapped hosts, reading a
crontab line during a change review, an incident, or a migration between timezones. Frequency:
occasional but high-stakes — a handful of invocations per incident, where a wrong reading costs
a missed batch window. Today they guess from `crontab(5)`, or copy the line to a machine that
does have a browser. Secondary: CI pipelines that want to lint a schedule without adding a
dependency (served by `--json` and the exit codes).

## 3. Success metrics

- A crontab expression built from any documented element form is either explained correctly or
  rejected with an error naming the offending field and token — never silently mis-explained.
- All oracle cases recorded in the KB domain chunks pass as tests (`0 0 13 * FRI` OR-semantics,
  `0 0 * * 0` ≡ `0 0 * * 7`, the spring-forward gap, the fall-back repeat, a +05:45 zone).
- `python3 -m unittest discover` completes with zero failures, offline, with no installed
  package outside the standard library.
- Every semantic choice where POSIX, Vixie and common practice disagree has an ADR whose
  rationale a reviewer can check without re-deriving crontab(5).

## 4. Scope

### In scope (this project)

- R-001: Parse the five-field syntax — `*`, `a`, `a-b`, `a-b/s`, `*/s`, `a/s`, and
  comma-separated lists of those — with per-field legal-range validation.
- R-002: Accept three-letter month and day-of-week names case-insensitively, including as
  range endpoints, list members and step bases (`MON-FRI`, `JAN,JUL`).
- R-003: Accept the `@`-macros case-insensitively: `@yearly`, `@annually`, `@monthly`,
  `@weekly`, `@daily`, `@midnight`, `@hourly`, `@reboot`.
- R-004: Apply Vixie day-of-month / day-of-week OR semantics, with the star flag tested on the
  field's leading `*` character rather than on the resulting value set.
- R-005: Print a deterministic one-sentence plain-English explanation of the schedule.
- R-006: Print the next N run times (default 5) in a specified IANA timezone, in increasing
  instant order, each rendered with its local UTC offset and its UTC equivalent.
- R-007: Handle DST spring-forward gaps and fall-back ambiguity explicitly, including
  non-whole-hour offsets and zones whose rules changed historically.
- R-008: `--json` emits a documented, stable machine-readable object on stdout.
- R-009: Exit non-zero with a precise error message — naming the field and the offending
  token — for an invalid expression, unknown macro or unknown timezone. No traceback.
- R-010: Reject non-POSIX syntax extensions (6- and 7-field forms with seconds or year, `L`,
  `W`, `#`, `?`, `@every N`) with a precise error rather than guessing.
- R-011: Run on Python 3.9 using only the standard library: no pip install, no network at
  runtime or at test time.
- R-012: Ship a stdlib `unittest` suite that runs offline and encodes the crontab(5) oracle
  cases from the KB domain chunks as named tests.
- R-013: Document the public CLI contract (usage, exit codes, JSON schema) and record every
  deliberate semantic deviation as an ADR with its rationale.
- R-014: Accept `--from <ISO-8601>` as the reference instant, so output is deterministic and
  testable without patching the clock.

### Out of scope (explicit non-goals)

cronx does not read or write crontab files, does not install or manage cron jobs, and is not a
scheduler or daemon — it never executes anything. No config file, no environment-variable
configuration, no plugin or extension mechanism, no locale or i18n for the English output, no
packaging metadata or publication to any registry (there is nothing to install: it is stdlib
source in a repo). No Quartz/Jenkins/systemd calendar syntax, no seconds or year fields, no
`L`/`W`/`#`/`?` extensions, no `@every 5m`. No stable importable library API. No past-run
enumeration, no "previous N runs", no schedule diffing, no crontab linting beyond validating
the single expression given. No colour, no TUI, no shell completion.

## 5. Tech stack and constraints

Python 3.9 (syntax floor), standard library only — `argparse`, `datetime`, `zoneinfo`, `json`,
`re`, `dataclasses`, `calendar`, `typing`, `unittest`. No third-party packages, no pip install,
no network at runtime or in tests. Tests are stdlib `unittest` (pytest would be a pip install).
Timezone data comes from the system tz database via `zoneinfo`; its absence is a handled error,
not a crash. Deadline: none stated. Development host has python3.14 only — see risk RSK-1.
Reference semantics: POSIX `crontab` and Vixie/ISC `crontab(5)`, as recorded in the project KB
domain chunks, which are the designated oracle for this project.

## 6. Milestones and phases

- **Wave 1 (this wave, planning):** charter, plan, architecture, ADRs, roster proposal → GATE 1.
- **Wave 2 (implementation), phase 1 — parse:** repo skeleton, the 3.9 syntax guard, the field
  parser, macros, the error model. Unblocks everything.
- **Wave 2, phase 2 — match and iterate:** the local wall-clock match iterator, then the
  timezone resolution layer that applies the DST policy. Unblocks the CLI.
- **Wave 2, phase 3 — explain and serve:** the English description generator and the CLI with
  both output formats and the exit-code contract. This is the first runnable deliverable.
- **Wave 3 (verification):** the crontab(5) oracle suite, the README/CLI contract, and the
  reviewer's semantics-and-3.9-API audit with a test report → GATE 2.

## 7. Risks

- **RSK-1 — 3.9 compatibility is unverifiable by execution (likelihood: certain; impact:
  high).** This host has only python3.14, so the target interpreter cannot run the code.
  Mitigation, two layers, both with acceptance criteria: (a) T-001 ships a test that runs
  `ast.parse(source, feature_version=(3, 9))` over every source file, which catches 3.10+
  *syntax*; (b) because that cannot catch newer *stdlib APIs*, T-010 makes the reviewer audit
  every import and attribute against the floor list in the `python39-stdlib-constraints` KB
  chunk (no `match`/`case`, no evaluated PEP-604 unions, no `datetime.UTC`, no `tomllib`, no
  `typing.Self`, no `itertools.batched`). Residual risk is accepted and stated: a 3.9 API
  regression can still ship undetected. It is disclosed at GATE 1, not papered over.
- **RSK-2 — the semantic oracle cannot be diffed against a live cron (likelihood: certain;
  impact: medium).** No network, no guaranteed cron daemon. Mitigation: the KB domain chunks
  are the declared oracle; T-008 encodes each documented case as a named test that cites its
  chunk, so a later correction is a localised test change plus an ADR supersession. The single
  place where the authorities genuinely conflict (`*/n` and the star flag) is isolated in
  ADR-001 and raised as the GATE 1 question.
- **RSK-3 — scope creep in the English output (likelihood: medium; impact: medium).** "Plain
  English" is an invitation to build a natural-language generator. Mitigation: ADR-009 fixes a
  closed template grammar and makes a golden file the contract (T-006); anything the grammar
  cannot say is out of scope, not a new template.
- **RSK-4 — an ordering bug in the ambiguous-hour path (likelihood: medium; impact: high).**
  Emitting occurrences sorted by *instant* while iterating *local* time is the subtlest code in
  the project, and it is only exercised twice a year. Mitigation: T-008 adds a monotonicity
  property test asserting strictly increasing instants across every transition of three zones
  over five years, plus the explicit fixed-vs-wildcard cases from ADR-002 and ADR-003.
- **RSK-5 — the host has no tz database (likelihood: low; impact: low).** `zoneinfo` raises
  `ZoneInfoNotFoundError`. Mitigation: ADR-011 and T-007 turn it into a precise stderr message
  and exit 2, never a traceback.

## 8. Deployment jurisdictions (required)

N/A — offline local CLI, no data collection, no distribution surface beyond the source repo.

## 9. Team

- **planner (PM + architect)** — this charter, the plan, the architecture and the ADRs; owns
  scope and the semantic decisions. Answers GATE 1 questions.
- **implementer** — builds T-001…T-009 in phase order against the architecture and the ADRs;
  each task ships with its own tests green before handoff.
- **reviewer** — audits the built code against the ADRs and the charter scope, performs the
  3.9 stdlib-API floor review that no test on this host can perform, and writes the test
  report at `.pmos/out/reviewer/test-report.md` keyed by A-id.
