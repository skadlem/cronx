"""T-006 — golden-file contract for describe() (ADR-009, R-005, A-006).

tests/golden/descriptions.txt was HAND-DERIVED from ADR-009's clause grammar
and element-phrase table before describe.py produced any output; it is a
contract, not a snapshot. This test only ever asks: does describe(parse(x))
equal the pinned sentence? A wording change must arrive as an intentional
diff to the golden file, never as regenerated output.
"""
import pathlib
import unittest

from cronx.describe import describe
from cronx.parse import parse

GOLDEN = pathlib.Path(__file__).resolve().parent / "golden" / "descriptions.txt"

# ADR-009 "Pinned by" list — every one of these must have a golden row.
ADR009_PINNED = [
    "* * * * *", "*/2 * * * *", "5 * * * *", "0 0 * * *", "0 9,17 * * *",
    "5 9-17 * * *", "*/15 9-17 * * MON-FRI", "0 0 13 * FRI", "0 0 */2 * MON",
    "0 0 1-31 * MON", "0-59/15 * * * *", "@yearly", "@weekly", "@reboot",
]


def _rows():
    rows = []
    for line in GOLDEN.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        expr, sentence = line.split("\t")
        rows.append((expr, sentence))
    return rows


class GoldenContractTest(unittest.TestCase):
    def test_golden_file_is_present_and_nonempty(self):
        self.assertTrue(GOLDEN.is_file(), "missing golden contract file")
        self.assertGreaterEqual(len(_rows()), len(ADR009_PINNED))

    def test_describe_matches_every_golden_sentence(self):
        for expr, sentence in _rows():
            with self.subTest(expr=expr):
                self.assertEqual(describe(parse(expr)), sentence)

    def test_golden_covers_the_adr009_pinned_expressions(self):
        exprs = set(expr for expr, _ in _rows())
        for pinned in ADR009_PINNED:
            self.assertIn(pinned, exprs)

    def test_sentences_are_capitalised_single_period_statements(self):
        for expr, sentence in _rows():
            with self.subTest(expr=expr):
                self.assertEqual(sentence[-1], ".")
                self.assertEqual(sentence.count("."), 1, sentence)
                self.assertEqual(sentence[0], sentence[0].upper())

    def test_first_element_unit_prefix_state_is_per_field(self):
        # Pinned by the `0 9,17 * * *` row: "minute 0 past hour 9, 17" —
        # the `a` row's unit prefix applies to each field's first element.
        self.assertEqual(describe(parse("0 9,17 * * *")),
                         "At minute 0 past hour 9, 17.")

    def test_or_rule_connective_is_visible_for_both_restricted_days(self):
        # ADR-009 Consequences' worked example, verbatim.
        self.assertEqual(describe(parse("0 0 13 * FRI")),
                         "At 00:00, on day-of-month 13 or on Friday.")

    def test_reboot_bypasses_the_grammar(self):
        # ADR-004's fixed sentence, and case-insensitive macro parsing.
        self.assertEqual(describe(parse("@reboot")),
                         "At system startup (`@reboot` has no wall-clock schedule).")
        self.assertEqual(describe(parse("@REBOOT")), describe(parse("@reboot")))


if __name__ == "__main__":
    unittest.main()
