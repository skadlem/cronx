# ADR-006: accept the `a/s` step-without-range form as `a-max/s`

Date: 2026-09-04 | Decider: architect
Status: accepted
Supersedes:

## Context

POSIX has no step syntax at all; steps (`*/s`, `a-b/s`) are a Vixie extension. Vixie also
accepts a bare start with a step and no range — `5/10` — which it treats as `a-last/s`:
the start value through the field's maximum. The KB records this as present in Vixie but
"NOT in every cron", and marks it a decision point requiring an ADR either way
(KB: `cron-field-semantics`). R-001 lists `a/s` among the forms to parse.

The form is easy to misread: `5/10` looks like a fraction or like "every 10th of 5", and in
the minute field it means 5, 15, 25, 35, 45, 55 — never 0. That misreading is worth a
correct answer.

## Options considered

- **A — reject `a/s`**, telling the user to write `5-59/10`. Pro: only the forms all crons
  agree on are accepted; nothing ambiguous is explained. Con: the same objection as ADR-005
  — the line runs on the user's host, so refusing it makes cronx useless exactly when it is
  needed, and the "write it differently" advice does not help someone reading a file.
- **B — accept it as `a-max/s`.** Pro: matches the deployed implementation; the upper bound
  comes from the field, so no new rule is needed. Con: cronx accepts a form some crons
  reject, and the semantics are unusual enough to need spelling out in the English output.

## Decision

**B.** `a/s` parses to the element `(start=a, stop=field_max, step=s)`. The four element
shapes therefore normalise to one triple plus a star flag:

| written | start | stop | step | field `star` contribution |
|---|---|---|---|---|
| `*`     | min | max | 1 | leading `*` |
| `a`     | a   | a   | 1 | — |
| `a-b`   | a   | b   | 1 | — |
| `a-b/s` | a   | b   | s | — |
| `*/s`   | min | max | s | leading `*` |
| `a/s`   | a   | max | s | — |

Validation, uniform across forms: `min <= start <= stop <= max` (no wrap-around, so `22-2`
is an error), and `step >= 1` (`*/0` is an error). A step larger than the span is legal and
yields just the start value. `a/s` does not set the star flag, so it is *restricted* for
ADR-001's day rule and *non-wildcard* for ADR-002/ADR-003.

## Consequences

- Positive: one element representation covers every form; the parser, the matcher and the
  describer each have one code path rather than six.
- Positive: because `stop` is the field maximum rather than something computed at match
  time, `--json` `fields[].values` is fully explicit and self-checking.
- Negative: `5/10` in the hour field means 5, 15 — a user expecting "every 10 hours from 5"
  to wrap to 1 gets a different answer. ADR-009's sentence renders it as "every 10th hour
  from 5 through 23", which states the bound rather than leaving it implied.
- Risks / follow-ups: none; if a strict cron rejects the form, that is an installability
  question, out of scope per charter §4.

## Pinned by

T-002: `5/10` in minute → {5,15,25,35,45,55}; `5/10` in hour → {5,15}; `*/0` and `22-2` are
errors naming the field and the token; `1-5/10` → {1}; `0 0 5/10 * MON` uses OR semantics
(the field does not start with `*`).
