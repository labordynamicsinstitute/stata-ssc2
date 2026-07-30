"""Guard tests over the repository's own source files.

These do not test a function; they assert properties of the tree that
are easy to break by hand-editing -- a version string creeping back into
a source file, or a fork URL surviving a merge.
"""
import datetime
import re
import unittest
from pathlib import Path

from tools.render import TOKEN_RE, context

ROOT = Path(__file__).resolve().parents[1]

# Files that must carry placeholders rather than literal versions.
PLACEHOLDER_FILES = [
    "ado/ssc2.ado",
    "sthlp/ssc2.sthlp",
    "ssc2.pkg",
    "stata.toc",
]

KNOWN_TOKENS = set(context("0.0.0", datetime.date(2000, 1, 1)))

# A dotted three-part version, optionally tagged. Deliberately broad so
# that a stray "2.2.1-draft" is caught too.
VERSION_LITERAL = re.compile(r"\bv?\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?\b")

# Version-shaped strings that are legitimately not the ssc2 version. The
# README's worked example quotes the version of reghdfe that a dated
# install returns; that number is data, not our version.
ALLOWED_LITERALS = {"5.7.3"}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class TestPlaceholdersPresent(unittest.TestCase):
    def test_ado_header_uses_placeholders(self):
        first = read("ado/ssc2.ado").splitlines()[0]
        self.assertIn("@VERSION@", first)
        self.assertIn("@DATE_STATA@", first)

    def test_sthlp_header_uses_placeholders(self):
        second = read("sthlp/ssc2.sthlp").splitlines()[1]
        self.assertIn("@VERSION@", second)
        self.assertIn("@DATE_STATA@", second)

    def test_pkg_declares_version_and_distribution_date(self):
        text = read("ssc2.pkg")
        self.assertIn("d Version: @VERSION@", text)
        self.assertIn("d Distribution-Date: @DATE_COMPACT@", text)

    def test_toc_declares_version(self):
        self.assertIn("@VERSION@", read("stata.toc"))


class TestNoStrayTokens(unittest.TestCase):
    def test_every_token_used_is_one_the_build_defines(self):
        for rel in PLACEHOLDER_FILES:
            with self.subTest(file=rel):
                used = set(TOKEN_RE.findall(read(rel)))
                self.assertLessEqual(used, KNOWN_TOKENS,
                                     f"{rel} uses undefined placeholders")


class TestNoHardcodedVersions(unittest.TestCase):
    def test_no_literal_version_strings_remain(self):
        for rel in PLACEHOLDER_FILES:
            with self.subTest(file=rel):
                found = {m for m in VERSION_LITERAL.findall(read(rel))
                         if m.lstrip("v") not in ALLOWED_LITERALS}
                self.assertEqual(found, set(),
                                 f"{rel} still hardcodes a version")


class TestDataMarkersIntact(unittest.TestCase):
    def test_index_html_still_has_the_data_markers(self):
        # site/build_data.py rewrites the block between these. Rendering
        # must never touch them.
        text = read("site/index.html")
        self.assertIn("@@DATA-START@@", text)
        self.assertIn("@@DATA-END@@", text)

    def test_token_regex_ignores_the_data_markers(self):
        text = read("site/index.html")
        self.assertNotIn("@@DATA-START@@",
                         "".join(TOKEN_RE.findall(text)))


class TestCitationFile(unittest.TestCase):
    """CITATION.cff is the one file that must NOT carry placeholders."""

    def test_uses_no_placeholder_tokens(self):
        self.assertEqual(TOKEN_RE.findall(read("CITATION.cff")), [])

    def test_date_released_is_a_real_iso_date(self):
        # The CFF 1.2.0 schema requires YYYY-MM-DD here; GitHub refuses
        # to render the citation widget if this is malformed.
        m = re.search(r"^date-released: (\S+)$", read("CITATION.cff"),
                      re.MULTILINE)
        self.assertIsNotNone(m, "no top-level date-released field")
        datetime.date.fromisoformat(m.group(1))

    def test_has_a_top_level_version_field(self):
        self.assertRegex(read("CITATION.cff"), r"(?m)^version: \S+$")


DOC_FILES = ["README.md", "site/about.html", "site/index.html"]


class TestDocsUsePlaceholders(unittest.TestCase):
    def test_readme_pins_via_placeholder(self):
        self.assertIn("@VERSION_TAG@", read("README.md"))

    def test_about_page_pins_via_placeholder(self):
        self.assertIn("@VERSION_TAG@", read("site/about.html"))

    def test_index_page_pins_via_placeholder(self):
        self.assertIn("@VERSION_TAG@", read("site/index.html"))

    def test_docs_only_use_defined_tokens(self):
        for rel in DOC_FILES:
            with self.subTest(file=rel):
                used = set(TOKEN_RE.findall(read(rel)))
                self.assertLessEqual(used, KNOWN_TOKENS,
                                     f"{rel} uses undefined placeholders")

    def test_docs_quote_no_stale_ssc2_version(self):
        # README.md carried "v1.0.0" and site/index.html carried "v1.1.7"
        # in hand-written install instructions. Both go stale silently,
        # which is the whole reason for the placeholder scheme.
        for rel in DOC_FILES:
            with self.subTest(file=rel):
                found = {m for m in VERSION_LITERAL.findall(read(rel))
                         if m.lstrip("v") not in ALLOWED_LITERALS}
                self.assertEqual(found, set(),
                                 f"{rel} hardcodes an ssc2 version")


class TestNoForkReferences(unittest.TestCase):
    def test_no_fork_owner_anywhere(self):
        for rel in PLACEHOLDER_FILES + DOC_FILES:
            with self.subTest(file=rel):
                self.assertNotIn("ian-joyce", read(rel))

    def test_no_merge_todos_left(self):
        for rel in PLACEHOLDER_FILES + DOC_FILES:
            with self.subTest(file=rel):
                self.assertNotIn("TODO AT MERGE", read(rel))

    def test_nothing_installs_from_main(self):
        # main carries unrendered placeholders; installing from it would
        # give the user an ado file whose version reads "@VERSION@".
        for rel in DOC_FILES:
            with self.subTest(file=rel):
                self.assertNotIn("stata-ssc2/main", read(rel))
