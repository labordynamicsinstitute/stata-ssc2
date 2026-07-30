"""Unit tests for tools/version.py."""
import unittest

from tools.version import (
    Version, bump, known_versions, latest_release, next_version, parse, tag_of,
)

# The tag list as it actually exists in this repository today, plus the
# legacy non-semver tag that the resolver must ignore rather than crash on.
REAL_TAGS = ["v0.5-beta", "v1.1.7"]


class TestParse(unittest.TestCase):
    def test_parses_plain_version(self):
        self.assertEqual(parse("2.2.2"), Version(2, 2, 2, None))

    def test_parses_tag_with_leading_v(self):
        self.assertEqual(parse("v2.2.2"), Version(2, 2, 2, None))

    def test_parses_release_candidate(self):
        self.assertEqual(parse("v2.2.2-rc.3"), Version(2, 2, 2, 3))

    def test_rejects_legacy_beta_tag(self):
        self.assertIsNone(parse("v0.5-beta"))

    def test_rejects_draft_suffix(self):
        self.assertIsNone(parse("2.2.1-draft"))

    def test_rejects_two_part_version(self):
        self.assertIsNone(parse("v2.2"))

    def test_rejects_empty_string(self):
        self.assertIsNone(parse(""))


class TestFormatting(unittest.TestCase):
    def test_str_of_final(self):
        self.assertEqual(str(Version(2, 2, 2)), "2.2.2")

    def test_str_of_rc(self):
        self.assertEqual(str(Version(2, 2, 2, 1)), "2.2.2-rc.1")

    def test_tag_of_adds_v(self):
        self.assertEqual(tag_of(Version(2, 2, 2)), "v2.2.2")

    def test_tag_of_rc(self):
        self.assertEqual(tag_of(Version(2, 2, 2, 1)), "v2.2.2-rc.1")

    def test_is_prerelease(self):
        self.assertFalse(Version(2, 2, 2).is_prerelease)
        self.assertTrue(Version(2, 2, 2, 1).is_prerelease)

    def test_base_strips_rc(self):
        self.assertEqual(Version(2, 2, 2, 5).base, Version(2, 2, 2))


class TestOrdering(unittest.TestCase):
    def test_final_sorts_after_its_own_candidates(self):
        got = known_versions(["v2.2.2", "v2.2.2-rc.2", "v2.2.2-rc.1"])
        self.assertEqual([str(v) for v in got],
                         ["2.2.2-rc.1", "2.2.2-rc.2", "2.2.2"])

    def test_known_versions_drops_unparseable(self):
        self.assertEqual([str(v) for v in known_versions(REAL_TAGS)], ["1.1.7"])

    def test_numeric_not_lexicographic(self):
        got = known_versions(["v1.1.7", "v1.1.10", "v1.1.9"])
        self.assertEqual([str(v) for v in got], ["1.1.7", "1.1.9", "1.1.10"])


class TestLatestRelease(unittest.TestCase):
    def test_ignores_prereleases(self):
        self.assertEqual(latest_release(["v1.1.7", "v2.0.0-rc.1"]),
                         Version(1, 1, 7))

    def test_none_when_only_prereleases(self):
        self.assertIsNone(latest_release(["v2.0.0-rc.1", "v0.5-beta"]))

    def test_none_when_no_tags(self):
        self.assertIsNone(latest_release([]))


class TestBump(unittest.TestCase):
    def test_patch(self):
        self.assertEqual(bump(Version(2, 2, 1), "patch"), Version(2, 2, 2))

    def test_minor_resets_patch(self):
        self.assertEqual(bump(Version(2, 2, 7), "minor"), Version(2, 3, 0))

    def test_major_resets_minor_and_patch(self):
        self.assertEqual(bump(Version(2, 2, 7), "major"), Version(3, 0, 0))

    def test_rejects_unknown_part(self):
        with self.assertRaises(ValueError):
            bump(Version(2, 2, 2), "epoch")


class TestNextVersion(unittest.TestCase):
    def test_patch_increment_is_the_default(self):
        self.assertEqual(str(next_version(["v2.2.1"])), "2.2.2")

    def test_ignores_legacy_tag_when_incrementing(self):
        self.assertEqual(str(next_version(REAL_TAGS)), "1.1.8")

    def test_minor_bump(self):
        self.assertEqual(str(next_version(["v2.2.1"], part="minor")), "2.3.0")

    def test_first_prerelease_is_rc_1(self):
        self.assertEqual(str(next_version(["v2.2.1"], prerelease=True)),
                         "2.2.2-rc.1")

    def test_second_prerelease_advances_the_counter(self):
        tags = ["v2.2.1", "v2.2.2-rc.1"]
        self.assertEqual(str(next_version(tags, prerelease=True)), "2.2.2-rc.2")

    def test_prerelease_counter_ignores_other_bases(self):
        tags = ["v2.2.1", "v2.9.9-rc.7"]
        self.assertEqual(str(next_version(tags, prerelease=True)), "2.2.2-rc.1")

    def test_clearing_prerelease_promotes_without_further_bump(self):
        tags = ["v2.2.1", "v2.2.2-rc.1", "v2.2.2-rc.2"]
        self.assertEqual(str(next_version(tags, prerelease=False)), "2.2.2")

    def test_override_wins(self):
        self.assertEqual(str(next_version(["v2.2.1"], override="5.0.0")),
                         "5.0.0")

    def test_override_works_with_no_prior_release(self):
        self.assertEqual(str(next_version(["v0.5-beta"], override="2.2.2")),
                         "2.2.2")

    def test_override_rejects_existing_tag(self):
        with self.assertRaises(ValueError):
            next_version(["v2.2.1"], override="2.2.1")

    def test_override_rejects_unparseable(self):
        with self.assertRaises(ValueError):
            next_version(["v2.2.1"], override="2.2.2-draft")

    def test_override_must_agree_with_prerelease_flag(self):
        with self.assertRaises(ValueError):
            next_version(["v2.2.1"], override="2.2.2", prerelease=True)
        with self.assertRaises(ValueError):
            next_version(["v2.2.1"], override="2.2.2-rc.1", prerelease=False)

    def test_no_prior_release_and_no_override_is_an_error(self):
        with self.assertRaises(ValueError):
            next_version(["v0.5-beta"])
