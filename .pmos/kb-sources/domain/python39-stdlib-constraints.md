# Python 3.9 + stdlib-only constraints for cronx

Available and appropriate: argparse, datetime, zoneinfo (stdlib SINCE 3.9), json, re,
dataclasses, enum, typing, calendar, unittest. No pip installs, no network at runtime.

zoneinfo on 3.9 reads the system tz database (/usr/share/zoneinfo on Linux). If absent it
raises zoneinfo.ZoneInfoNotFoundError -- cronx must catch that and emit a precise error,
not a traceback. `zoneinfo.available_timezones()` exists but is slow; do not call it on the
hot path.

3.9 SYNTAX FLOOR -- these are NOT available and must not appear:
- match/case statements (3.10)
- PEP 604 unions `int | None` in evaluated positions (3.10). Annotations are fine only
  under `from __future__ import annotations`; prefer typing.Optional/Union for clarity.
- typing.Self (3.11), ExceptionGroup / except* (3.11), tomllib (3.11)
- the `type X = ...` statement (3.12), PEP 695 generics (3.12)
- itertools.batched (3.12), datetime.UTC alias (3.11; use timezone.utc)
Available in 3.9 and fine to use: dict `|` merge, str.removeprefix/removesuffix,
functools.cache, graphlib.

VERIFY COMPAT WITHOUT A 3.9 INTERPRETER: this machine has only python3.14. Compile-check
with a 3.9 target using `ast.parse(src, feature_version=(3, 9))` over every source file in
a test; that catches 3.10+ syntax. It does NOT catch newer stdlib APIs, so those must be
caught by review against the list above.
