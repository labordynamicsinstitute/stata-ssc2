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
