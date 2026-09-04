"""Guards the Python 3.9 syntax floor. No 3.9 interpreter exists on this host,
so this ast.parse check is the only defence against accidental 3.10+ syntax.
"""
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _source_files():
    files = []
    for pkg in ("cronx", "tests"):
        files.extend(sorted((ROOT / pkg).rglob("*.py")))
    return files


class Py39SyntaxTest(unittest.TestCase):
    def test_every_source_file_parses_as_python39(self):
        files = _source_files()
        self.assertTrue(files, "no .py files found under cronx/ or tests/")
        for path in files:
            src = path.read_text()
            try:
                ast.parse(src, filename=str(path), feature_version=(3, 9))
            except SyntaxError as exc:
                self.fail("{}: not valid Python 3.9 syntax: {}".format(path, exc))


if __name__ == "__main__":
    unittest.main()
