"""Unit tests for tools/build_release.py."""
import datetime
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.build_release import (
    COPY_FILES, PACKAGE_FILES, build, main,
)
from tools.version import git_tags

WHEN = datetime.date(2026, 7, 30)


def make_repo(tmp: Path) -> Path:
    """A minimal stand-in for the real repository layout.

    `git init` matters: main() always asks git for the tag list, and a
    bare temp directory would make git walk up to whatever repository
    happens to contain /tmp (or fail outright). An empty repository has
    no tags and needs no commit -- and therefore no git identity -- so
    the override path is exercised against a genuinely empty tag list.
    """
    repo = tmp / "repo"
    (repo / "ado").mkdir(parents=True)
    (repo / "sthlp").mkdir(parents=True)
    (repo / "ado" / "ssc2.ado").write_text(
        "*! version @VERSION@ @DATE_STATA@\n", encoding="utf-8")
    (repo / "sthlp" / "ssc2.sthlp").write_text(
        "{* *! version @VERSION@  @DATE_STATA@}{...}\n", encoding="utf-8")
    (repo / "ssc2.pkg").write_text(
        "v 3\nd Version: @VERSION@\nd Distribution-Date: @DATE_COMPACT@\n",
        encoding="utf-8")
    (repo / "stata.toc").write_text(
        "v 3\nd Version @VERSION@ (@DATE_ISO@)\n", encoding="utf-8")
    (repo / "README.md").write_text(
        "install from @VERSION_TAG@\n", encoding="utf-8")
    (repo / "LICENSE").write_text("MIT-ish @VERSION@ not rendered\n",
                                  encoding="utf-8")
    (repo / "CITATION.cff").write_text(
        "cff-version: 1.2.0\nversion: 0.0.0\ndate-released: 2000-01-01\n",
        encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


class TestFixture(unittest.TestCase):
    def test_the_stand_in_repo_has_no_tags(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(git_tags(make_repo(Path(t))), [])


class TestBuild(unittest.TestCase):
    def test_writes_every_package_file(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2", WHEN)
            for rel in PACKAGE_FILES + COPY_FILES:
                with self.subTest(file=rel):
                    self.assertTrue((out / rel).exists(), f"{rel} missing")

    def test_renders_the_ado_header(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2", WHEN)
            self.assertEqual((out / "ado" / "ssc2.ado").read_text(),
                             "*! version 2.2.2 30jul2026\n")

    def test_renders_the_pkg_metadata(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2", WHEN)
            text = (out / "ssc2.pkg").read_text()
            self.assertIn("d Version: 2.2.2", text)
            self.assertIn("d Distribution-Date: 20260730", text)

    def test_renders_the_version_tag_in_readme(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2", WHEN)
            self.assertEqual((out / "README.md").read_text(),
                             "install from v2.2.2\n")

    def test_copied_files_are_not_rendered(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2", WHEN)
            self.assertIn("@VERSION@", (out / "LICENSE").read_text())

    def test_output_directory_is_replaced_not_merged(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            out.mkdir()
            (out / "stale.txt").write_text("leftover", encoding="utf-8")
            build(repo, out, "2.2.2", WHEN)
            self.assertFalse((out / "stale.txt").exists())

    def test_prerelease_version_renders(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2-rc.1", WHEN)
            self.assertEqual((out / "README.md").read_text(),
                             "install from v2.2.2-rc.1\n")


class TestMainCLI(unittest.TestCase):
    def test_explicit_version_writes_github_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            gh_out = Path(t) / "gh_output"
            os.environ["GITHUB_OUTPUT"] = str(gh_out)
            try:
                rc = main(["--repo", str(repo), "--out", str(out),
                           "--version", "2.2.2", "--date", "2026-07-30"])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            self.assertEqual(rc, 0)
            written = gh_out.read_text(encoding="utf-8")
            self.assertIn("version=2.2.2\n", written)
            self.assertIn("tag=v2.2.2\n", written)
            self.assertIn("prerelease=false\n", written)

    def test_prerelease_flag_is_reported_in_outputs(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            gh_out = Path(t) / "gh_output"
            os.environ["GITHUB_OUTPUT"] = str(gh_out)
            try:
                main(["--repo", str(repo), "--out", str(Path(t) / "dist"),
                      "--version", "2.2.2-rc.1", "--prerelease",
                      "--date", "2026-07-30"])
            finally:
                del os.environ["GITHUB_OUTPUT"]
            written = gh_out.read_text(encoding="utf-8")
            self.assertIn("tag=v2.2.2-rc.1\n", written)
            self.assertIn("prerelease=true\n", written)

    def test_invalid_version_returns_nonzero_without_writing_output(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            rc = main(["--repo", str(repo), "--out", str(out),
                       "--version", "not-a-version", "--date", "2026-07-30"])
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())


class TestCitationInReleaseTree(unittest.TestCase):
    def test_citation_file_is_written(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2", WHEN)
            self.assertTrue((out / "CITATION.cff").exists())

    def test_citation_fields_are_substituted(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2", WHEN)
            text = (out / "CITATION.cff").read_text(encoding="utf-8")
            self.assertIn("\nversion: 2.2.2\n", text)
            self.assertIn("\ndate-released: 2026-07-30\n", text)

    def test_citation_keeps_no_placeholder_tokens(self):
        with tempfile.TemporaryDirectory() as t:
            repo = make_repo(Path(t))
            out = Path(t) / "dist"
            build(repo, out, "2.2.2-rc.1", WHEN)
            text = (out / "CITATION.cff").read_text(encoding="utf-8")
            self.assertNotIn("@", text)
            self.assertIn('version: "2.2.2-rc.1"', text)
