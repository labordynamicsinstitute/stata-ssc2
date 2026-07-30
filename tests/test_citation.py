"""Unit tests for tools/citation.py."""
import datetime
import tempfile
import unittest
from pathlib import Path

from tools.citation import CITATION_FILE, main, set_release_fields

WHEN = datetime.date(2026, 7, 30)

# Trimmed but structurally faithful to the real CITATION.cff, including
# the block scalar and the nested author list, both of which contain
# lines that must not be mistaken for top-level fields.
SAMPLE = """cff-version: 1.2.0
message: "If you use this software, please cite it as below."
title: "ssc2: Install Stata packages from date-based snapshots"
version: 2.0.0
date-released: 2026-07-08
license: MIT
repository-code: "https://github.com/labordynamicsinstitute/stata-ssc2"
abstract: >-
  ssc2 is a drop-in replacement for the Stata ssc command.
  version: not-a-field
authors:
  - family-names: Vilhuber
    given-names: Lars
    affiliation: "Labor Dynamics Institute, Cornell University"
keywords:
  - stata
"""


class TestSetReleaseFields(unittest.TestCase):
    def test_sets_the_version(self):
        out = set_release_fields(SAMPLE, "2.2.2", WHEN)
        self.assertIn("\nversion: 2.2.2\n", out)
        self.assertNotIn("\nversion: 2.0.0\n", out)

    def test_sets_the_release_date(self):
        out = set_release_fields(SAMPLE, "2.2.2", WHEN)
        self.assertIn("\ndate-released: 2026-07-30\n", out)
        self.assertNotIn("2026-07-08", out)

    def test_leaves_indented_lookalikes_alone(self):
        # "  version: not-a-field" lives inside the abstract block scalar.
        out = set_release_fields(SAMPLE, "2.2.2", WHEN)
        self.assertIn("  version: not-a-field", out)

    def test_leaves_every_other_line_untouched(self):
        out = set_release_fields(SAMPLE, "2.2.2", WHEN)
        before = [l for l in SAMPLE.splitlines()
                  if not l.startswith(("version:", "date-released:"))]
        after = [l for l in out.splitlines()
                 if not l.startswith(("version:", "date-released:"))]
        self.assertEqual(before, after)

    def test_line_count_is_preserved(self):
        out = set_release_fields(SAMPLE, "2.2.2", WHEN)
        self.assertEqual(len(out.splitlines()), len(SAMPLE.splitlines()))

    def test_quotes_a_prerelease_version(self):
        # 2.2.2-rc.1 is fine bare, but quoting is harmless and protects
        # against a version that YAML would otherwise coerce.
        out = set_release_fields(SAMPLE, "2.2.2-rc.1", WHEN)
        self.assertIn('\nversion: "2.2.2-rc.1"\n', out)

    def test_plain_version_is_not_quoted(self):
        out = set_release_fields(SAMPLE, "2.2.2", WHEN)
        self.assertIn("\nversion: 2.2.2\n", out)

    def test_is_idempotent(self):
        once = set_release_fields(SAMPLE, "2.2.2", WHEN)
        twice = set_release_fields(once, "2.2.2", WHEN)
        self.assertEqual(once, twice)

    def test_raises_when_version_field_is_missing(self):
        text = "cff-version: 1.2.0\ndate-released: 2026-07-08\n"
        with self.assertRaises(ValueError) as cm:
            set_release_fields(text, "2.2.2", WHEN)
        self.assertIn("version", str(cm.exception))

    def test_raises_when_date_released_field_is_missing(self):
        text = "cff-version: 1.2.0\nversion: 2.0.0\n"
        with self.assertRaises(ValueError) as cm:
            set_release_fields(text, "2.2.2", WHEN)
        self.assertIn("date-released", str(cm.exception))

    def test_does_not_confuse_cff_version_with_version(self):
        out = set_release_fields(SAMPLE, "2.2.2", WHEN)
        self.assertIn("cff-version: 1.2.0", out)

    def test_filename_constant(self):
        self.assertEqual(CITATION_FILE, "CITATION.cff")


class TestAgainstTheRealFile(unittest.TestCase):
    def test_the_repository_file_can_be_updated(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / CITATION_FILE).read_text(encoding="utf-8")
        out = set_release_fields(text, "2.2.2", WHEN)
        self.assertIn("\nversion: 2.2.2\n", out)
        self.assertIn("\ndate-released: 2026-07-30\n", out)
        self.assertIn("cff-version: 1.2.0", out)


class TestCLI(unittest.TestCase):
    """The release workflow shells out to this; the flag order it uses
    (flags before the positional path) must keep working."""

    def _sample(self, tmp: Path) -> Path:
        path = tmp / "CITATION.cff"
        path.write_text(SAMPLE, encoding="utf-8")
        return path

    def test_in_place_rewrites_the_file(self):
        with tempfile.TemporaryDirectory() as t:
            path = self._sample(Path(t))
            rc = main(["--version", "2.2.2", "--date", "2026-07-30",
                       "--in-place", str(path)])
            self.assertEqual(rc, 0)
            text = path.read_text(encoding="utf-8")
            self.assertIn("\nversion: 2.2.2\n", text)
            self.assertIn("\ndate-released: 2026-07-30\n", text)

    def test_without_in_place_the_file_is_untouched(self):
        with tempfile.TemporaryDirectory() as t:
            path = self._sample(Path(t))
            rc = main(["--version", "2.2.2", "--date", "2026-07-30",
                       str(path)])
            self.assertEqual(rc, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), SAMPLE)

    def test_returns_nonzero_on_a_malformed_file(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "CITATION.cff"
            path.write_text("cff-version: 1.2.0\n", encoding="utf-8")
            rc = main(["--version", "2.2.2", "--in-place", str(path)])
            self.assertEqual(rc, 1)
            self.assertEqual(path.read_text(encoding="utf-8"),
                             "cff-version: 1.2.0\n")
