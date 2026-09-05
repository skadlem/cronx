You are the IMPLEMENTER on the cronx project (PMOS lean team). Working dir: /home/madiyar/cronx.
Spawn model: qwen3.8-flash (hermes host; effort inert). This is Wave 2 chunk 1 RETRY: attempt 1
died on infrastructure errors after writing tests but no implementation.

## Your assignment (finish Phase 1 — parse)
Tasks T-002 and T-003 from .pmos/plans/plan.md:
1. Implement cronx/parse.py completely so that `python3 -m unittest tests.test_parse -v` goes
   GREEN on the EXISTING tests (201+ lines, already reviewed — they encode the revised
   ADR-006/ADR-012 decisions; three new tests added today: crontab-line hint, Quartz
   discrimination, whitespace collapse). Do not weaken or edit existing assertions to make
   them pass; if a test contradicts an ADR, STOP and flag it in notes.md instead of changing it.
2. Write tests/test_macros.py FIRST (TDD), then implement T-003: the macro table (@yearly,
   @annually, @monthly, @weekly, @daily, @midnight, @hourly, @reboot — case-insensitive, whole-
   expression match; non-@reboot macros rewrite to their five-field text and parse normally;
   @reboot sets Schedule.reboot and skips field parsing) and rejection of 6/7-field forms,
   L/W/#/? tokens, and @every with the dialect-naming errors of ADR-007 (including its
   2026-09-05 crontab-line amendment: command-shaped token 6 gets the "pass only the first
   five fields" hint INSTEAD of the Quartz diagnosis — see tests/test_parse.py FieldCountTest
   for the message contract: contains "crontab LINE", must NOT contain "Quartz").
3. Deliver every artifact: source, tests, AND .pmos/out/implementer/notes.md — attempt 1 died
   before writing it. Notes must list: task ids done, decisions you did NOT make (everything
   with an ADR number is already decided), every KB/graphify query you ran, and the exact
   command outputs proving green.

## Mandatory procedure
1. Read .pmos/charter.md (scope R-001..R-014) and the ADRs that bind YOUR code:
   .pmos/decisions/ADR-001, ADR-004, ADR-005, ADR-006, ADR-007, ADR-010, ADR-012 — and
   .pmos/out/planner/architecture.md §2 (data structures, the star-flag invariant, parsing
   order, step-expansion-from-field-minimum, whitespace collapse). The architecture is
   binding: frozen dataclasses Element(start,stop,step,star), Field(name,text,elements,values,
   star), Schedule(text,macro,reboot,minute,hour,dom,month,dow), CronxError(message,code).
   Field.text and Field.star are VERBATIM/first-character semantics (ADR-001) — tests assert
   them and the reviewer wave depends on them.
2. KB search BEFORE coding domain specifics (never dump the DB):
   python3 /home/madiyar/pm-agent-team/tools/kb.py search --db .pmos/kb.sqlite3 "<query>" --role backend -k 5
   (also --role shared and --role architect allowed). Trust the project chunks (priority 9)
   over older fundamentals when they conflict; the live-oracle-probe chunk records what the
   host's real cron accepts.
3. HARD CONSTRAINTS: Python 3.9 syntax floor (no match/case, no PEP-604 `X | Y` evaluated
   unions, no `str.removeprefix`? — that one IS fine since 3.9 — but NO 3.10+ stdlib APIs);
   stdlib only; cronx/parse.py must import nothing from the rest of the package; module-level
   constants in UPPER_SNAKE; keep parse.py near the ~180-LOC budget (a couple over is fine, a
   doubling is a design smell — re-read architecture §6 "things deliberately absent").
4. Run `python3 -m unittest discover -v` from repo root; test_py39_syntax must stay green
   (it ast.parses every file with feature_version=(3,9)). test_parse/test_macros green =
   done; other test files may not exist yet — that is expected.
5. Self-check traceability before reporting: `python3 /home/madiyar/pm-agent-team/tools/
   artifacts.py --project . --strict` must still exit 0 (you change no ids).
6. Do NOT commit (coordinator handles git). Do NOT touch files outside: cronx/parse.py,
   tests/test_macros.py, tests/test_parse.py (additive only if a genuine gap vs ADRs —
   document any such edit in notes.md), .pmos/out/implementer/notes.md.
7. Report back: T-002/T-003 status, test counts and command output, decisions deferred,
   anything you could not verify marked unchecked.
