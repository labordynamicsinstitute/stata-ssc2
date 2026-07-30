"""Unit tests for tools/render.py."""
import datetime
import tempfile
import unittest
from pathlib import Path

from tools.render import (
    TOKEN_RE, context, render_file, render_text,
)

WHEN = datetime.date(2026, 7, 30)
CTX = context("2.2.2", WHEN)


class TestContext(unittest.TestCase):
    def test_version_token(self):
        self.assertEqual(CTX["@VERSION@"], "2.2.2")

    def test_version_tag_token_has_leading_v(self):
        self.assertEqual(CTX["@VERSION_TAG@"], "v2.2.2")

    def test_stata_date_is_lowercase_ddmonyyyy(self):
        self.assertEqual(CTX["@DATE_STATA@"], "30jul2026")

    def test_stata_date_keeps_leading_zero(self):
        # Stata itself writes 08jul2026, and the existing help file used
        # exactly that form.
        self.assertEqual(context("1.0.0", datetime.date(2026, 7, 8))["@DATE_STATA@"],
                         "08jul2026")

    def test_iso_date(self):
        self.assertEqual(CTX["@DATE_ISO@"], "2026-07-30")

    def test_compact_date_matches_pkg_distribution_date_format(self):
        self.assertEqual(CTX["@DATE_COMPACT@"], "20260730")

    def test_exactly_five_tokens(self):
        self.assertEqual(sorted(CTX), [
            "@DATE_COMPACT@", "@DATE_ISO@", "@DATE_STATA@",
            "@VERSION@", "@VERSION_TAG@",
        ])

    def test_prerelease_version_passes_through(self):
        ctx = context("2.2.2-rc.1", WHEN)
        self.assertEqual(ctx["@VERSION@"], "2.2.2-rc.1")
        self.assertEqual(ctx["@VERSION_TAG@"], "v2.2.2-rc.1")


class TestTokenRegex(unittest.TestCase):
    def test_matches_a_token(self):
        self.assertEqual(TOKEN_RE.findall("x @VERSION@ y"), ["@VERSION@"])

    def test_does_not_match_the_data_markers_in_index_html(self):
        # site/build_data.py rewrites the block between these markers.
        # If TOKEN_RE ever matched them, rendering site/index.html would
        # fail the build (or, worse, mangle the markers).
        marked = "/* @@DATA-START@@ */\nconst X=1;\n/* @@DATA-END@@ */"
        self.assertEqual(TOKEN_RE.findall(marked), [])

    def test_does_not_match_css_at_rules(self):
        self.assertEqual(TOKEN_RE.findall("@media (min-width:40em){}"), [])
        self.assertEqual(TOKEN_RE.findall("@keyframes blink{}"), [])

    def test_does_not_match_an_email_address(self):
        self.assertEqual(TOKEN_RE.findall("lars.vilhuber@cornell.edu"), [])


class TestRenderText(unittest.TestCase):
    def test_substitutes_every_token(self):
        src = "*! version @VERSION@ @DATE_STATA@\nd Distribution-Date: @DATE_COMPACT@"
        self.assertEqual(
            render_text(src, CTX),
            "*! version 2.2.2 30jul2026\nd Distribution-Date: 20260730")

    def test_substitutes_repeated_tokens(self):
        self.assertEqual(render_text("@VERSION@ @VERSION@", CTX), "2.2.2 2.2.2")

    def test_leaves_untokenised_text_alone(self):
        src = "@media screen { a { color: red } }"
        self.assertEqual(render_text(src, CTX), src)

    def test_raises_on_unknown_token(self):
        with self.assertRaises(ValueError) as cm:
            render_text("hello @NOPE@", CTX)
        self.assertIn("@NOPE@", str(cm.exception))

    def test_reports_every_unknown_token(self):
        with self.assertRaises(ValueError) as cm:
            render_text("@AAA@ @BBB@", CTX)
        self.assertIn("@AAA@", str(cm.exception))
        self.assertIn("@BBB@", str(cm.exception))


class TestRenderFile(unittest.TestCase):
    def test_writes_rendered_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.ado"
            dst = Path(tmp) / "sub" / "dir" / "out.ado"
            src.write_text("*! version @VERSION@\n", encoding="utf-8")
            render_file(src, dst, CTX)
            self.assertEqual(dst.read_text(encoding="utf-8"),
                             "*! version 2.2.2\n")

    def test_creates_missing_parent_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.txt"
            dst = Path(tmp) / "a" / "b" / "c" / "out.txt"
            src.write_text("@VERSION@", encoding="utf-8")
            render_file(src, dst, CTX)
            self.assertTrue(dst.exists())

    def test_error_names_the_offending_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bad.txt"
            src.write_text("@MYSTERY@", encoding="utf-8")
            with self.assertRaises(ValueError) as cm:
                render_file(src, Path(tmp) / "out.txt", CTX)
            self.assertIn("bad.txt", str(cm.exception))
            self.assertIn("@MYSTERY@", str(cm.exception))
