# @-macros (Vixie nickname extensions)

@yearly  = 0 0 1 1 *     @annually = same as @yearly
@monthly = 0 0 1 * *
@weekly  = 0 0 * * 0
@daily   = 0 0 * * *     @midnight = same as @daily
@hourly  = 0 * * * *
@reboot  = run at daemon startup. It has NO wall-clock schedule, so "next N run times"
           is undefined for it. cronx must either reject it with a precise error or
           explain it and emit zero occurrences -- a DECISION POINT requiring an ADR.

Macros are case-insensitive in most implementations; a macro occupies the entire
schedule spec (no other fields may follow it in the spec cronx parses).
