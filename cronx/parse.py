"""text -> validated Schedule. Owns CronxError, Field, Element, Schedule,
the name tables and the macro table.

Binding: architecture §2, ADR-001/004/005/006/007/010/012. Parses nothing from
the rest of the package; stdlib only; Python 3.9 syntax floor.
"""
import re
from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple

MINUTE, HOUR, DOM, MONTH, DOW = "minute", "hour", "day-of-month", "month", "day-of-week"

# (display name, lo, hi, name table or None) in schedule order
FIELD_SPECS = ((MINUTE, 0, 59, None), (HOUR, 0, 23, None), (DOM, 1, 31, None),
               (MONTH, 1, 12, {m: i + 1 for i, m in enumerate(
                   "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}),
               (DOW, 0, 7, {d: i for i, d in enumerate("SUN MON TUE WED THU FRI SAT".split())}))

ALL_NAMES = frozenset(FIELD_SPECS[3][3]) | frozenset(FIELD_SPECS[4][3])

MACROS = {"@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *",
          "@weekly": "0 0 * * 0", "@daily": "0 0 * * *", "@midnight": "0 0 * * *",
          "@hourly": "0 * * * *", "@reboot": "@reboot"}

_ELEMENT_RE = re.compile(r"^(\*|\d+)(?:-(\*|\d+))?(?:/(\d+))?$")


@dataclass(frozen=True)
class Element:
    """One comma-separated piece of a field, all forms normalised. ADR-006 table."""
    start: int
    stop: int
    step: int
    star: bool  # written as `*` or `*/s`


@dataclass(frozen=True)
class Field:
    name: str
    text: str  # verbatim, ADR-001
    elements: Tuple[Element, ...]
    values: FrozenSet[int]
    star: bool  # THE OR-RULE FLAG: text.startswith("*"), never derived from values


@dataclass(frozen=True)
class Schedule:
    text: str
    macro: Optional[str]
    reboot: bool
    minute: Optional[Field]
    hour: Optional[Field]
    dom: Optional[Field]
    month: Optional[Field]
    dow: Optional[Field]


class CronxError(Exception):
    """Finished user-facing message + exit code (ADR-010). Parser always uses 1."""

    def __init__(self, message, code=1):
        Exception.__init__(self, message)
        self.message = message
        self.code = code


def _extension_message(name, raw):
    # ADR-007: name the token and its dialect; `#` additionally warns about
    # the host cron's comment-folding (KB: cron-live-oracle-probe).
    if "#" in raw:
        return ("%s field: '%s': the '#' extension (nth weekday of the month) is Quartz "
                "syntax, not supported by POSIX or Vixie cron; note that the host's cron "
                "would read this as a day value and treat '#...' as the start of a comment"
                % (name, raw))
    for char, what in (("?", "'?' (no specific value)"), ("L", "'L' (last)"),
                       ("W", "'W' (nearest weekday)")):
        if char in raw.upper():
            return ("%s field: '%s': the %s extension is Quartz syntax, not supported "
                    "by POSIX or Vixie cron" % (name, raw, what))
    return "%s field: '%s': unsupported extension" % (name, raw)


def _parse_element(name, raw, lo, hi, names):
    if "#" in raw or "?" in raw:
        raise CronxError(_extension_message(name, raw))
    for run in re.findall(r"[A-Za-z]+", raw):
        if names is not None and run.upper() in names:
            continue
        if names is None and run.upper() in ALL_NAMES:
            raise CronxError("%s field: '%s': names are only allowed in month and "
                             "day-of-week" % (name, raw))
        if run.upper() in ("L", "W", "LW", "WL"):
            raise CronxError(_extension_message(name, raw))
        raise CronxError("%s field: invalid element: '%s'" % (name, raw))
    orig = raw  # error messages must name the token as written (FRI-MON, not 5-1)
    if names is not None:
        raw = re.sub(r"[A-Za-z]+", lambda m: str(names[m.group(0).upper()]), raw)
    m = _ELEMENT_RE.match(raw)
    if not m:
        raise CronxError("%s field: invalid element: '%s'" % (name, orig))
    head, tail, step_text = m.group(1), m.group(2), m.group(3)
    step = int(step_text) if step_text else 1
    if step < 1:
        raise CronxError("%s field: step must be >= 1: '%s'" % (name, orig))
    if head == "*":
        if tail is not None:
            raise CronxError("%s field: invalid element: '%s'" % (name, orig))
        return Element(lo, hi, step, True)
    start = _validated(name, lo, hi, int(head), orig)
    if tail is None:
        if step_text:  # bare a/s: ADR-006 rejection with the exact ascending rewrite
            raise CronxError("%s: '%s' is a cronie/croniter extension (step without a "
                             "range), not supported by POSIX or Vixie cron; write "
                             "'%d-%d/%s' instead" % (name, orig, start, hi, step_text))
        return Element(start, start, 1, False)
    if tail == "*":
        raise CronxError("%s field: invalid element: '%s'" % (name, orig))
    stop = _validated(name, lo, hi, int(tail), orig)
    if start > stop:  # ADR-012
        raise CronxError("%s: '%s' is a descending range; cron accepts it but its meaning "
                         "is not defined by POSIX or documented by crontab(5) (it most "
                         "likely matches nothing). Write '%d-%d,%d-%d' if you meant the "
                         "wrap-around" % (name, orig, start, hi, lo, stop))
    return Element(start, stop, step, False)


def _validated(name, lo, hi, value, raw):
    if not lo <= value <= hi:
        raise CronxError("%s field: value out of range %d-%d: '%s'" % (name, lo, hi, raw))
    return value


def _parse_field(name, text, lo, hi, names):
    elements = tuple(_parse_element(name, part, lo, hi, names)
                     for part in text.split(","))
    values = set()
    for e in elements:
        values.update(range(e.start, e.stop + 1, e.step))
    if name == DOW:  # 7 folds to Sunday 0 (ADR-005)
        values = {0 if v == 7 else v for v in values}
    return Field(name=name, text=text, elements=elements,
                 values=frozenset(values), star=text.startswith("*"))


def parse(text):
    tokens = text.split()  # leading/trailing/repeated whitespace collapses (architecture §2)
    macro = None
    if tokens and tokens[0].startswith("@"):
        name = tokens[0].lower()
        if name not in MACROS:
            raise CronxError("unknown macro '%s': supported macros are %s"
                             % (tokens[0], ", ".join(MACROS)))
        if len(tokens) > 1:
            raise CronxError("'%s' must be the whole expression: a macro replaces the "
                             "five fields, extra tokens are not allowed" % tokens[0])
        macro = name
        if name == "@reboot":  # ADR-004: valid, but no wall-clock schedule; skip fields
            return Schedule(text=text, macro=macro, reboot=True,
                            minute=None, hour=None, dom=None, month=None, dow=None)
        tokens = MACROS[name].split()
    if len(tokens) != 5:
        msg = ("expected 5 fields (minute hour day-of-month month day-of-week), got %d"
               % len(tokens))
        # ADR-007 amendment 2026-09-05: a command-shaped token 6 is a pasted
        # crontab LINE, not a Quartz year field — name the right manual page.
        if len(tokens) == 6 and tokens[5].startswith(("/", "./", "~")):
            raise CronxError(msg + "; if your six tokens are a crontab LINE "
                             "(e.g. '0 0 13 * FRI /usr/bin/backup'), pass only the "
                             "first five fields — the command is not part of the "
                             "expression")
        if len(tokens) in (6, 7):
            raise CronxError(msg + " — 6- and 7-field forms with seconds or year are "
                             "Quartz/Spring syntax, not POSIX cron")
        raise CronxError(msg)
    fields = tuple(_parse_field(spec[0], tokens[i], spec[1], spec[2], spec[3])
                   for i, spec in enumerate(FIELD_SPECS))
    return Schedule(text=text, macro=macro, reboot=False, minute=fields[0],
                    hour=fields[1], dom=fields[2], month=fields[3], dow=fields[4])
