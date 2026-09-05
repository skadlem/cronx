# Plan: cronx

Status: draft | Owner: planner (PM + architect) | Updated: 2026-09-04

## Phases
<!-- Wave-aligned. One line each: what lands in it, what it unblocks. -->

- **Phase 1 — parse** (charter §6, Wave 2 phase 1): repo skeleton, the 3.9 syntax guard,
  the field/element parser, macros incl. `@reboot`, and the extension-rejection error model
  (T-001, T-002, T-003). Unblocks every other module — `parse` is the one dependency every
  other module has, directly or transitively (architecture §1).
- **Phase 2 — match and iterate** (Wave 2 phase 2): the local wall-clock match iterator and
  day rule, then the timezone resolution layer applying the DST policy (T-004, T-005).
  Unblocks the CLI.
- **Phase 3 — explain and serve** (Wave 2 phase 3): the English description generator and
  the CLI with both output formats, the exit-code contract, and the timezone-error path
  (T-006, T-009, T-007). This is the first runnable deliverable.
- **Phase 4 — verify** (Wave 3, charter §6): the crontab(5) oracle suite and monotonicity
  property test, the README/CLI-contract doc, and the reviewer's 3.9 stdlib-API floor audit
  with the test report (T-008, T-012, T-011, T-010) → GATE 2.

## Task graph
<!-- One `- id: T-NNN` block per task, ids stable for the life of the project. -->

```yaml
- id: T-001
  title: Repo skeleton (empty cronx/ package modules, __main__ entry point) plus the 3.9
    syntax-guard test that runs ast.parse(src, feature_version=(3,9)) over every file in
    cronx/ and tests/
  role: implementer
  satisfies: R-011
  depends_on:
  decided_by:
  touches: cronx/__init__.py, cronx/__main__.py, cronx/parse.py, cronx/match.py,
    cronx/occurrences.py, cronx/describe.py, cronx/cli.py, tests/test_py39_syntax.py
  test_strategy: python3 -m unittest tests.test_py39_syntax -v
```

```yaml
- id: T-002
  title: Field/element parser - the five element forms, per-field range validation, name
    resolution in month/day-of-week, rejection of `a/s` and descending ranges, and
    field-and-token error messages carrying a rewrite hint
  role: implementer
  satisfies: R-001, R-002, R-009
  depends_on: T-001
  decided_by: ADR-005, ADR-006, ADR-010, ADR-012
  touches: cronx/parse.py, tests/test_parse.py
  test_strategy: python3 -m unittest tests.test_parse -v
```

```yaml
- id: T-003
  title: Macro table (@yearly...@hourly, @reboot) and rejection of 6/7-field Quartz forms
    and the L/W/#/?/@every extensions with a dialect-naming error
  role: implementer
  satisfies: R-003, R-010
  depends_on: T-002
  decided_by: ADR-004, ADR-007
  touches: cronx/parse.py, tests/test_macros.py
  test_strategy: python3 -m unittest tests.test_macros -v
```

```yaml
- id: T-004
  title: Day rule (OR/AND on the star flag) and the bounded day-then-hour-then-minute
    match iterator, including the unsatisfiable-schedule horizon behaviour
  role: implementer
  satisfies: R-004
  depends_on: T-002
  decided_by: ADR-001, ADR-008
  touches: cronx/match.py, tests/test_match.py
  test_strategy: python3 -m unittest tests.test_match -v
```

```yaml
- id: T-005
  title: Timezone resolution (happy path), the DST gap/fold policy, and the
    strictly-greater-than-last-emitted dedupe filter that guarantees monotonic instants
  role: implementer
  satisfies: R-006, R-007
  depends_on: T-002, T-004
  decided_by: ADR-002, ADR-003, ADR-008, ADR-011
  touches: cronx/occurrences.py, tests/test_dst.py
  test_strategy: python3 -m unittest tests.test_dst -v
```

```yaml
- id: T-006
  title: English sentence generator (closed template grammar) plus the golden-file
    contract test
  role: implementer
  satisfies: R-005
  depends_on: T-002, T-003
  decided_by: ADR-001, ADR-004, ADR-009
  touches: cronx/describe.py, tests/test_describe.py, tests/golden/descriptions.txt
  test_strategy: python3 -m unittest tests.test_describe -v
```

```yaml
- id: T-009
  title: CLI - argparse contract, text and --json rendering, --from/-n/--tz wiring, and
    the CronxError-to-exit-code dispatch
  role: implementer
  satisfies: R-008, R-009, R-014
  depends_on: T-002, T-003, T-004, T-005, T-006
  decided_by: ADR-010, ADR-004, ADR-011
  touches: cronx/cli.py, cronx/__main__.py, tests/test_cli.py
  test_strategy: python3 -m unittest tests.test_cli -v
```

```yaml
- id: T-007
  title: ZoneInfoNotFoundError path - distinguish an unknown zone name from a missing tz
    database via the single UTC probe, routed through the CLI's exit-code dispatch
  role: implementer
  satisfies: R-009
  depends_on: T-005, T-009
  decided_by: ADR-011, ADR-010
  touches: cronx/occurrences.py, cronx/cli.py, tests/test_tz_errors.py
  test_strategy: python3 -m unittest tests.test_tz_errors -v
```

```yaml
- id: T-008
  title: crontab(5) oracle suite (KB-cited cases through the public entry points) and the
    ambiguous-hour/DST-gap monotonicity property test across three zones over five years
  role: implementer
  satisfies: R-012
  depends_on: T-004, T-005, T-006, T-009
  decided_by: ADR-001, ADR-002, ADR-003, ADR-005, ADR-006, ADR-008, ADR-012
  touches: tests/test_oracle.py, tests/test_monotonicity.py
  test_strategy: python3 -m unittest tests.test_oracle tests.test_monotonicity -v
```

```yaml
- id: T-012
  title: Differential test against the host's real cron - assert cronx's accept/reject
    verdict matches `crontab -n` over a corpus of expressions, with the deliberate
    divergences (ADR-012 descending ranges, and `#` per ADR-007) asserted AS divergences
  role: reviewer
  satisfies: R-012, R-013
  depends_on: T-008
  decided_by: ADR-005, ADR-006, ADR-007, ADR-012
  touches: tests/test_differential.py
  test_strategy: python3 -m unittest tests.test_differential -v
  note: skipUnless(shutil.which("crontab")) so the suite stays green on hosts without cron;
    `crontab -n` validates without installing (verified - it left the user's crontab absent).
    Syntax only - it cannot verify DST semantics or ADR-012's empty-set inference.
```

```yaml
- id: T-011
  title: README documenting the CLI usage, exit-code table, and --json schema, kept
    consistent with the shipped argparse help and cli.py's actual output
  role: implementer
  satisfies: R-013
  depends_on: T-009
  decided_by:
  touches: README.md, tests/test_readme.py
  test_strategy: python3 -m unittest tests.test_readme -v
```

```yaml
- id: T-010
  title: Reviewer's 3.9 stdlib-API floor audit (grep + per-import sign-off against the
    python39-stdlib-constraints KB chunk) over the whole cronx/ package, full-suite run,
    and the test report keyed by A-id
  role: reviewer
  satisfies: R-011, R-012
  depends_on: T-001, T-002, T-003, T-004, T-005, T-006, T-007, T-008, T-009, T-011
  decided_by:
  touches: cronx/
  test_strategy: "grep -rnE '\\bmatch [^=]+:|^\\s*case |datetime\\.UTC|tomllib|typing\\.Self|itertools\\.batched'
    cronx/ (zero matches) plus a per-import manual sign-off recorded in
    .pmos/out/reviewer/test-report.md; then python3 -m unittest discover -v"
```

## Acceptance criteria
<!-- One `- id: A-NNN` block per criterion. -->

```yaml
- id: A-001
  title: Any 3.10+ syntax in the source tree is caught before it ever needs to run
  form: WHEN ast.parse is run with feature_version=(3,9) over every file in cronx/ and
    tests/ THE SYSTEM SHALL report zero syntax errors
  verifies: T-001
  how: python3 -m unittest tests.test_py39_syntax -v
```

```yaml
- id: A-002
  title: Every documented element form parses correctly or is rejected by field and token
  form: WHEN a five-field expression using any of *, a, a-b, a-b/s or */s (including comma
    lists and month/day-of-week names) is parsed THE SYSTEM SHALL produce the exact
    documented value set; WHEN a/s, a descending range, or an out-of-range or malformed
    element is given THE SYSTEM SHALL raise CronxError naming the offending field and token
    (ADR-006, ADR-012)
  verifies: T-002
  how: python3 -m unittest tests.test_parse -v
```

```yaml
- id: A-003
  title: Macros parse and non-POSIX dialects are named and rejected, never guessed at
  form: WHEN an @-macro is given case-insensitively THE SYSTEM SHALL parse it (or, for
    @reboot, set the reboot flag and skip matching); WHEN a 6/7-field, L/W/#/?, or @every
    expression is given THE SYSTEM SHALL exit 1 with a message naming the offending token
    and the dialect it belongs to — except a 6-field form whose last token is command-shaped
    gets the crontab-line hint instead (ADR-007 amendment 2026-09-05)
  verifies: T-003
  how: python3 -m unittest tests.test_macros -v
```

```yaml
- id: A-004
  title: The day rule and the search horizon match ADR-001/ADR-008 exactly
  form: WHEN both day-of-month and day-of-week are restricted (star=False) THE SYSTEM
    SHALL AND-match them if either is a leading-star form and OR-match them otherwise; WHEN
    a schedule cannot match within HORIZON_DAYS THE SYSTEM SHALL return zero occurrences
    and exit 0
  verifies: T-004
  how: python3 -m unittest tests.test_match -v
```

```yaml
- id: A-005
  title: DST gap and fold handling matches the Vixie wildcard split
  form: WHEN a candidate wall clock falls in a spring-forward gap or a fall-back repeat
    THE SYSTEM SHALL emit it per ADR-002/ADR-003 (dropped or shifted for a gap; once or
    twice for a repeat, depending on minute.star or hour.star) with the correct dst
    annotation
  verifies: T-005
  how: python3 -m unittest tests.test_dst -v
```

```yaml
- id: A-006
  title: The English sentence for every documented schedule shape matches the golden file
  form: WHEN describe() is called on any schedule in the golden-file set (including the
    ADR-001 OR-rule cases) THE SYSTEM SHALL produce exactly the recorded sentence, with no
    free-text fallback
  verifies: T-006
  how: python3 -m unittest tests.test_describe -v
```

```yaml
- id: A-007
  title: CLI exit codes, --json schema, and --from/-n honour the documented contract
  form: WHEN cronx is invoked with an invalid expression THE SYSTEM SHALL exit 1; WHEN
    invoked with a bad --tz, unparseable --from, or -n < 1 THE SYSTEM SHALL exit 2; WHEN
    invoked with --json THE SYSTEM SHALL print the documented object with every key
    present and no traceback ever reaches stderr
  verifies: T-009
  how: python3 -m unittest tests.test_cli -v
```

```yaml
- id: A-008
  title: --tz defaults to UTC and the resolved zone is always visible in the output
  form: WHEN cronx is invoked without --tz THE SYSTEM SHALL resolve UTC and print
    "UTC" in both the text header and the JSON "timezone" field
  verifies: T-009
  how: python3 -m unittest tests.test_cli -v
```

```yaml
- id: A-009
  title: An unknown timezone and a missing tz database are told apart, never a traceback
  form: WHEN --tz names a zone not in the system tz database THE SYSTEM SHALL exit 2 with
    "unknown timezone ..."; WHEN the tz database itself is unavailable THE SYSTEM SHALL
    exit 2 with "no system timezone database found ..."; in neither case does stdout
    receive output or does a traceback reach stderr
  verifies: T-007
  how: python3 -m unittest tests.test_tz_errors -v
```

```yaml
- id: A-010
  title: Every KB-cited crontab(5) oracle case passes as a named test
  form: WHEN each oracle case from the KB domain chunks (0 0 13 * FRI, 0 0 * * 0 ≡
    0 0 * * 7, 0 0 */2 * MON, the spring-forward and fall-back cases, Asia/Kathmandu
    +05:45) is run through the public entry points THE SYSTEM SHALL produce the documented
    answer
  verifies: T-008
  how: python3 -m unittest tests.test_oracle -v
```

```yaml
- id: A-011
  title: Emitted instants are strictly increasing across every DST transition
  form: WHEN next_runs is walked across every spring-forward and fall-back transition of
    America/New_York (1 h step), Australia/Lord_Howe (30 min step), and Asia/Kathmandu
    (permanent +05:45, no transitions — the no-op path) over 2022-01-01..2026-12-31
    (--from pinned, schedule `* * * * *` sampled per transition window and `*/17 * * * *`
    walked for a full year each zone) THE SYSTEM SHALL emit instants in strictly increasing
    order with no duplicate instant
  verifies: T-008
  how: python3 -m unittest tests.test_monotonicity -v
```

```yaml
- id: A-012
  title: README's documented contract matches the CLI's real output
  form: WHEN the CLI usage line, the exit-code table, and the --json field names are
    compared against README.md THE SYSTEM SHALL show no discrepancy
  verifies: T-011
  how: python3 -m unittest tests.test_readme -v
```

```yaml
- id: A-013
  title: No 3.9-incompatible stdlib API reaches the shipped source
  form: WHEN every import and attribute access in cronx/ is checked against the
    python39-stdlib-constraints KB chunk THE SYSTEM SHALL show zero forbidden APIs (no
    match/case, no evaluated PEP-604 unions, no datetime.UTC, no tomllib, no typing.Self,
    no itertools.batched), recorded in .pmos/out/reviewer/test-report.md
  verifies: T-010
  how: "grep -rnE '\\bmatch [^=]+:|^\\s*case |datetime\\.UTC|tomllib|typing\\.Self|itertools\\.batched' cronx/"
```

```yaml
- id: A-014
  title: The full offline suite is green with nothing beyond the standard library
  form: WHEN python3 -m unittest discover is run from the repo root with no network
    access and no installed package outside the standard library THE SYSTEM SHALL
    complete with zero failures
  verifies: T-010
  how: python3 -m unittest discover -v
```

```yaml
- id: A-015
  title: cronx's accept/reject verdict agrees with the host's real cron, except where an
    ADR says otherwise
  form: WHEN each expression in the differential corpus is given to both cronx and
    `crontab -n` THE SYSTEM SHALL reach the same accept/reject verdict, except for the
    cases ADR-012 and ADR-007 name as intentional divergences, which SHALL diverge in the
    documented direction
  verifies: T-012
  how: python3 -m unittest tests.test_differential -v
  note: corpus is PINNED, not reviewer's choice — the KB `cron-live-oracle-probe` transcript
    cases plus every ADR "Pinned by" expression (ADR-001/004/005/006/007/012), plus
    boundary tokens per field (0/1/31/32/59/60, JAN/DEC/SUN/MON/7/8) — 40 minimum.
```

## Out of plan
<!-- Work deliberately deferred, so it is not silently dropped. -->

Per charter §4 (non-goals), none of the following is built in this plan: reading or
writing crontab files, installing or managing cron jobs, any scheduler/daemon behaviour,
a config file or environment-variable configuration, a plugin or extension mechanism,
locale/i18n for the English output, packaging metadata or registry publication, a stable
importable library API, past-run enumeration or "previous N runs", schedule diffing,
crontab linting beyond validating the single given expression, colour output, a TUI, or
shell completion. Quartz/Jenkins/systemd-calendar syntax, seconds/year fields, and the
`L`/`W`/`#`/`?`/`@every` extensions are rejected by name (T-003) rather than supported.
