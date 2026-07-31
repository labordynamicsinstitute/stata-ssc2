"""Unit tests for site/build_reference.py (SMCL -> Markdown).

The converter's job is to hand kramdown something it will render the way
the Stata help viewer renders the SMCL. Two things can go wrong quietly:
markup that is dropped, and help text that Markdown reinterprets as
syntax. Both are covered here, plus an end-to-end pass over the real
help file.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site"))

import build_reference as br  # noqa: E402


class TestInline(unittest.TestCase):
    def test_cmd_becomes_code(self):
        self.assertEqual(br.inline("{cmd:ssc2 install}"), "`ssc2 install`")

    def test_opt_drops_the_abbreviation_colon(self):
        self.assertEqual(br.inline("{opt d:escribe}"), "`describe`")

    def test_it_becomes_emphasis(self):
        self.assertEqual(br.inline("{it:pkgname}"), "*pkgname*")

    def test_bf_and_hi_become_strong(self):
        self.assertEqual(br.inline("{bf:latest}"), "**latest**")
        self.assertEqual(br.inline("{hi:oaxaca}"), "**oaxaca**")

    def test_nested_markup_keeps_both_layers(self):
        # {it:{help filename}} -- the inner span must survive the outer.
        self.assertEqual(br.inline("{it:{help filename}}"), "*`filename`*")

    def test_browse_becomes_a_link(self):
        self.assertEqual(br.inline('{browse "https://example.org":text}'),
                         "[text](https://example.org)")

    def test_in_page_help_reference_becomes_an_anchor_link(self):
        self.assertEqual(br.inline("{help ssc2##options_ssc2_install:Options}"),
                         "[Options](#options_ssc2_install)")

    def test_plain_help_becomes_code_not_a_dead_link(self):
        self.assertEqual(br.inline("{helpb sysdir}"), "`sysdir`")

    def test_manhelp_renders_the_manual_reference(self):
        self.assertEqual(br.inline("{manhelp search R}"), "\\[R\\] `search`")

    def test_literal_braces_are_escaped(self):
        # {c -(} / {c )-} are how SMCL writes a literal brace; unescaped,
        # kramdown could read one as an attribute list.
        self.assertEqual(br.inline("{c -(} x {c )-}"), "\\{ x \\}")

    def test_markdown_metacharacters_in_plain_text_are_escaped(self):
        self.assertEqual(br.inline("[a] | b_c *d*"),
                         "\\[a\\] \\| b\\_c \\*d\\*")

    def test_escaping_does_not_leak_into_code_spans(self):
        # Inside a code span kramdown renders a backslash literally, so
        # `_` must reach the output bare.
        self.assertEqual(br.inline("{opt _}"), "`_`")

    def test_leading_character_cannot_open_a_block(self):
        self.assertEqual(br.inline("- not a list item"), "\\- not a list item")

    def test_unknown_directive_degrades_to_its_text(self):
        self.assertEqual(br.inline("{mansection R x:Quick start}"), "Quick start")


class TestConvert(unittest.TestCase):
    def test_title_becomes_a_heading(self):
        self.assertIn("## Syntax", br.convert("{title:Syntax}"))

    def test_marker_anchors_the_following_heading(self):
        out = br.convert("{marker syntax}{...}\n{title:Syntax}")
        self.assertIn("## Syntax\n{: #syntax}", out)

    def test_phang_carries_the_hanging_indent_class(self):
        out = br.convert("{phang}\n{opt all} does things\n")
        self.assertIn("{: .hang}", out)

    def test_syntax_diagram_carries_the_syn_class(self):
        out = br.convert("{p 8 12 2}\n{cmd:ssc2} {opt d:escribe}\n")
        self.assertIn("{: .syn}", out)

    def test_description_section_is_left_to_the_about_page(self):
        out = br.convert("{title:Description}\n{pstd}\nblah\n\n{title:Remarks}\n")
        self.assertNotIn("blah", out)
        self.assertIn("## Remarks", out)

    def test_viewer_navigation_is_dropped(self):
        out = br.convert('{viewerjumpto "Syntax" "ssc2##syntax"}{...}\n')
        self.assertEqual(out.strip(), "")

    def test_p2col_header_yields_the_one_line_description(self):
        br.convert("{p2col:{bf:ssc2} {hline 2}}Does a thing.{p_end}")
        self.assertEqual(br.convert.description, "Does a thing")


class TestRealHelpFile(unittest.TestCase):
    """End-to-end over sthlp/ssc2.sthlp, the file CI actually converts."""

    @classmethod
    def setUpClass(cls):
        cls.body = br.convert((ROOT / "sthlp" / "ssc2.sthlp").read_text())

    def test_no_smcl_survives(self):
        # Same gate main() enforces: an escaped brace is literal help
        # text and `{:` opens an attribute list, so neither counts.
        self.assertEqual(re.findall(r'(?<!\\)\{[a-zA-Z][^}]*\}', self.body), [])

    def test_every_section_heading_is_anchored(self):
        headings = re.findall(r'^## .*\n(.*)$', self.body, re.M)
        self.assertTrue(headings)
        for following in headings:
            self.assertRegex(following, r'^\{: #\S+\}$')

    def test_in_page_links_resolve_to_an_anchor_on_the_page(self):
        anchors = set(re.findall(r'^\{: #(\S+)\}$', self.body, re.M))
        targets = set(re.findall(r'\]\(#([^)]+)\)', self.body))
        self.assertTrue(targets)
        self.assertEqual(targets - anchors, set())

    def test_placeholders_are_all_restored(self):
        self.assertNotIn(br.SENTINEL, self.body)

    def test_version_placeholder_line_is_not_carried_into_the_page(self):
        self.assertNotIn("@VERSION@", self.body)


if __name__ == "__main__":
    unittest.main()
