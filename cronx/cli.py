"""argparse, text and --json rendering, exit codes (ADR-010). The only
module that touches argparse, json, sys and SystemExit. Output contract:
architecture §4 verbatim; ADR-004 (@reboot), ADR-011 (UTC default).
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from typing import List, Optional

from .describe import describe
from .occurrences import Occurrence, next_runs, resolve_zone
from .parse import CronxError, Schedule, parse

_SUFFIX = {
    "gap_shifted": "  (%s does not exist: DST gap, runs at the jump)",
    "ambiguous_first": "  (first pass of an ambiguous hour)",
    "ambiguous_second": "  (second pass of an ambiguous hour)",
    None: "",
}

_FIELD_KEYS = (("minute", "minute"), ("hour", "hour"), ("day_of_month", "dom"),
               ("month", "month"), ("day_of_week", "dow"))


class _Parser(argparse.ArgumentParser):
    """ADR-010: usage errors are ONE prefixed stderr line, never a block."""

    def error(self, message):  # overrides argparse's usage-dump-and-exit(2)
        sys.stderr.write("cronx: error: %s\n" % message)
        raise SystemExit(2)


def _build_parser() -> argparse.ArgumentParser:
    p = _Parser(prog="cronx", description="Explain a cron expression and list "
                "its next run times. Five fields or an @macro.")
    p.add_argument("expression", metavar="EXPRESSION",
                   help="five-field cron expression or @macro, e.g. '0 2 * * *'")
    p.add_argument("--tz", default="UTC", metavar="ZONE",
                   help="IANA timezone name (default: UTC)")
    p.add_argument("-n", type=int, default=5, metavar="N",
                   help="number of run times to list (default: 5)")
    p.add_argument("--from", dest="from_text", default=None, metavar="ISO8601",
                   help="reference instant; runs listed are strictly after it "
                        "(default: now). A value with no offset is read as "
                        "wall clock in --tz.")
    p.add_argument("--json", action="store_true", dest="as_json",
                   help="print a JSON object on stdout instead of text")
    return p


def _reference(from_text: Optional[str], zone) -> datetime:
    if from_text is None:
        return datetime.now(timezone.utc)
    try:
        value = datetime.fromisoformat(from_text)
    except ValueError:
        raise CronxError("--from: not a valid ISO-8601 timestamp: '%s'"
                         % from_text, 2)
    if value.tzinfo is None:      # naive = wall clock in --tz (exclusive)
        value = value.replace(tzinfo=zone)
    return value.astimezone(timezone.utc)


def _row(o: Occurrence) -> str:
    line = "  %s   %s" % (o.local.isoformat(sep=" "), o.instant.isoformat())
    if o.dst == "gap_shifted" and o.nominal is not None:
        return line + _SUFFIX[o.dst] % o.nominal.strftime("%H:%M")
    return line + _SUFFIX[o.dst]


def _render_text(s: Schedule, tz_name: str, n: int, from_utc: datetime,
                 occurrences: List[Occurrence]) -> str:
    lines = [s.text, describe(s)]
    if s.reboot:  # ADR-004: the sentence, and no run list
        return "\n".join(lines) + "\n"
    if not occurrences:
        return "\n".join(lines + ["", "no runs found within 9 years of %s"
                                 % from_utc.isoformat()]) + "\n"
    lines.extend(["", "next %d runs in %s:" % (n, tz_name)])
    lines.extend(_row(o) for o in occurrences)
    return "\n".join(lines) + "\n"


def _day_rule(s: Schedule) -> Optional[str]:
    # ADR-001: the OR fires only when NEITHER day field's text leads with '*'
    # (match.py's `dom.star or dow.star` inverted); @reboot has no day rule.
    if s.reboot or s.dom is None or s.dow is None:
        return None
    return "or" if not (s.dom.star or s.dow.star) else "and"


def _render_json(s: Schedule, tz_name: str, from_utc: datetime,
                 occurrences: List[Occurrence]) -> str:
    fields = {}
    for key, attr in _FIELD_KEYS:
        f = getattr(s, attr)
        fields[key] = None if f is None else {"text": f.text, "star": f.star,
                                              "values": sorted(f.values)}
    obj = {
        "expression": s.text,
        "macro": s.macro,
        "reboot": s.reboot,
        "timezone": tz_name,
        "from": from_utc.isoformat(),
        "description": describe(s),
        "day_rule": _day_rule(s),
        "fields": fields,
        "next": [{"local": o.local.isoformat(), "utc": o.instant.isoformat(),
                  "dst": o.dst, "nominal_local": None if o.nominal is None
                  else o.nominal.isoformat()} for o in occurrences],
    }
    return json.dumps(obj, indent=2, sort_keys=False) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exc:          # usage error 2 / --help 0
        return int(exc.code or 0)
    try:
        if args.n < 1:
            raise CronxError("-n must be >= 1, got %d" % args.n, 2)
        s = parse(args.expression)
        zone = resolve_zone(args.tz)   # before any output (ADR-011)
        from_utc = _reference(args.from_text, zone)
        runs = [] if s.reboot else next_runs(s, zone, from_utc, args.n)
    except CronxError as exc:          # finished message + code (ADR-010)
        sys.stderr.write("cronx: error: %s\n" % exc.message)
        return exc.code
    if args.as_json:
        sys.stdout.write(_render_json(s, args.tz, from_utc, runs))
    else:
        sys.stdout.write(_render_text(s, args.tz, args.n, from_utc, runs))
    return 0
