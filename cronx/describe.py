"""Schedule -> one English sentence (ADR-009).

Binding: ADR-009's clause grammar and element-phrase table, applied
mechanically; ADR-001 (the day connective reads Field.star, the same literal
first-character flag matching uses — never re-derived from values); ADR-004
(@reboot bypasses the grammar with its fixed sentence). The golden file
tests/golden/descriptions.txt is the contract; the tests in
tests/test_describe.py only check against it. Imports .parse only.
"""
from typing import Optional

from .parse import DOM, DOW, HOUR, MINUTE, MONTH, Element, Field, Schedule

REBOOT_SENTENCE = "At system startup (`@reboot` has no wall-clock schedule)."

_UNITS = {MINUTE: "minute", HOUR: "hour", DOM: "day-of-month",
          MONTH: "month", DOW: "day-of-week"}
_NAMED = (MONTH, DOW)
# day-of-week numbers -> full names (parse.py's table, inverted; 7 folded to 0)
_WEEKDAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return str(n) + suffix


def _label(field: Field, value: int) -> str:
    if field.name == DOW:
        return _WEEKDAYS[value % 7]
    if field.name == MONTH:
        return _MONTHS[value - 1]
    return str(value)


def _phrase(field: Field, element: Element, first: bool) -> str:
    """One element of ADR-009's table. `first` is the renderer's only state:
    the numeric `a` row prefixes its unit only for the first element."""
    unit = _UNITS[field.name]
    named = field.name in _NAMED
    if element.star and element.step == 1:
        return "every %s" % unit
    if element.star:
        return "every %s %s" % (_ordinal(element.step), unit)
    single = element.start == element.stop
    if single and element.step == 1:
        if named:
            return _label(field, element.start)
        return "%s %d" % (unit, element.start) if first else str(element.start)
    # Ranges: `a-b/s` always carries the ordinal prefix; plain `a-b` carries
    # "every <unit>" only in numeric fields (named: `Monday through Friday`).
    endpoints = " from %s through %s" % (_label(field, element.start),
                                         _label(field, element.stop))
    if element.step > 1:
        return "every %s %s%s" % (_ordinal(element.step), unit, endpoints)
    if named:
        return "%s through %s" % (_label(field, element.start),
                                  _label(field, element.stop))
    return "every %s%s" % (unit, endpoints)


def _p(field: Field) -> str:
    return ", ".join(_phrase(field, e, i == 0)
                     for i, e in enumerate(field.elements))


def _two(field: Field) -> bool:
    """Exactly one value (any notation) — the gate for the HH:MM form."""
    return len(field.values) == 1


def _time_phrase(mi: Field, ho: Field) -> str:
    if _two(mi) and _two(ho):
        return "at %02d:%02d" % (next(iter(ho.values)), next(iter(mi.values)))
    if mi.text == "*" and ho.text == "*":
        return "every minute"
    if mi.text == "*":
        return "every minute past %s" % _p(ho)
    head = "at %s" % _p(mi)
    if ho.text == "*":  # elision: an unrestricted hour clause is not said
        return head
    return head + " past " + _p(ho)


def _day_clause(dom: Field, dow: Field) -> Optional[str]:
    # "exactly *" is the literal text test — `*/2` carries ADR-001's star
    # flag but is one of the AND branch's named examples in the table.
    if dom.text == "*" and dow.text == "*":
        return None
    if dow.text == "*":
        return "on " + _p(dom)
    if dom.text == "*":
        return "on " + _p(dow)
    # ADR-001: OR only when both fields are restricted (no leading '*')
    connective = " or on " if not (dom.star or dow.star) else " and on "
    return "on %s%s%s" % (_p(dom), connective, _p(dow))


def describe(s: Schedule) -> str:
    # ADR-004: @reboot bypasses the grammar; None fields only ever occur for it.
    if (s.reboot or s.minute is None or s.hour is None or s.dom is None
            or s.month is None or s.dow is None):
        return REBOOT_SENTENCE
    parts = [_time_phrase(s.minute, s.hour)]
    day = _day_clause(s.dom, s.dow)
    if day:
        parts.append(day)
    if s.month.text != "*":
        parts.append("in " + _p(s.month))
    sentence = ", ".join(parts)
    return sentence[0].upper() + sentence[1:] + "."
