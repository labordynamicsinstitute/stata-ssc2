# Versioned Release Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every hardcoded version string in the `ssc2` source with build-time placeholders, and add a manually-triggered GitHub Actions release workflow that resolves the next version, publishes a rendered package tree on an orphan `dist` branch, tags it, moves a floating `latest` tag, creates the GitHub release, and redeploys the website.

**Architecture:** Three thin layers. Two pure-Python modules hold all the logic — `tools/version.py` does semantic-version arithmetic over a list of tag strings, `tools/render.py` does `@TOKEN@` substitution over text. Two CLI scripts glue them to git and the filesystem — `tools/build_release.py` produces the release tree, `tools/render_docs.py` renders documentation in place for the site build. `main` keeps placeholders forever and is never rewritten by CI; the orphan `dist` branch carries the rendered, installable tree, and every release tag points into `dist`.

**Tech Stack:** Python 3.12 standard library only (no third-party dependencies — matching the existing `site/build_data.py` and `site/build_reference.py`), `unittest` for tests, GitHub Actions, `gh` CLI, Stata SMCL/`.pkg` package format.

## Global Constraints

- **Python standard library only.** No `pip install`, no `requirements.txt`. The repo has no dependency file and CI installs nothing today; keep it that way.
- **Python 3.12**, matching `actions/setup-python` in the existing `.github/workflows/site.yml`.
- **Tests are always run from the repository root** as `python3 -m unittest discover -s tests -v`. That puts the root on `sys.path`, so test modules import `tools.*` directly with no `sys.path` manipulation and no `if __name__` block. The two CLI modules (`tools/build_release.py`, `tools/render_docs.py`) do keep a `sys.path.insert`, because `python3 tools/build_release.py` puts `tools/` on the path rather than the root.
- **Placeholder token syntax is exactly `@UPPER_SNAKE@`** — matched by the regex `@[A-Z][A-Z0-9_]*@`. This deliberately does **not** match the existing `@@DATA-START@@` / `@@DATA-END@@` markers in `site/index.html` (the hyphen is outside the character class). Never widen this regex.
- **The five tokens are exactly:** `@VERSION@`, `@VERSION_TAG@`, `@DATE_STATA@`, `@DATE_ISO@`, `@DATE_COMPACT@`. No others.
- **Version strings never carry a leading `v`; tag strings always do.** `Version` objects stringify to `2.2.2`; `tag_of()` produces `v2.2.2`.
- **Pre-release suffix is exactly `-rc.N`**, N starting at 1. e.g. `2.2.2-rc.1`, `2.2.2-rc.2`.
- **Canonical repo owner is `labordynamicsinstitute`.** The strings `ian-joyce` and `TODO AT MERGE` must not appear anywhere in the tree when this plan is done.
- **The `main` branch is never committed to by CI.** All rendering output goes to `dist` or to ephemeral CI working copies. The single exception is deliberate and gated: after a stable release the workflow opens a **pull request** against `main` containing only the two updated `CITATION.cff` fields. It never pushes to `main`, and the PR merges only when a human approves it.
- **`CITATION.cff` never carries placeholders.** GitHub validates the default branch's copy to render the "Cite this repository" widget, and the CFF 1.2.0 schema pins `date-released` to a literal `YYYY-MM-DD`. It is field-substituted, not token-rendered. It is also the only file exempt from the "no literal versions" guard test.
- **`dist` is an orphan branch and must never be merged into `main`.** It shares no history with `main` and contains only the installable tree; a merge would delete `site/`, `tools/`, `tests/` and `.github/`.
- **Install URLs point at tags on `dist`**, in the form `https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/<ref>/` where `<ref>` is `latest` or a version tag like `v2.2.2`. The old `.../stata-ssc2/main` form is removed everywhere — `main` now holds unrendered placeholders and must not be installed from.
- **The first release must be run with an explicit version override of `2.2.2`.** The newest released tag today is `v1.1.7`, but `ado/ssc2.ado` claims `2.2.1-draft`; the decision is to adopt the source version. There is no `v2.2.1` tag and none will be created. After that first run, auto-increment works unattended because `v2.2.2` > `v1.1.7`.
- **The legacy `v0.5-beta` tag is not a parseable release version** and must be silently ignored by the resolver, never crash it.

### Note on `git config` in workflows

The user's global preferences forbid running `git config user.name` / `user.email`. That rule protects the user's own machine, where a git identity already exists. A GitHub Actions runner has **no** identity, so `git commit` there fails without one. `.github/workflows/release.yml` therefore sets the standard `github-actions[bot]` identity as a documented, CI-only exception. Do not add `git config` calls to anything that runs locally.

---

## File Structure

**Created:**

| Path | Responsibility |
|---|---|
| `tools/version.py` | Semantic-version parsing, comparison, bumping, and next-version resolution. Pure logic plus one documented subprocess helper (`git_tags`). |
| `tools/render.py` | Token context construction and `@TOKEN@` substitution over text and files. Pure. |
| `tools/citation.py` | Field substitution for `CITATION.cff`, the one file that must keep real values rather than placeholders. Pure. |
| `tools/build_release.py` | CLI: resolve the next version from git tags, render the package files into an output directory, emit GitHub Actions outputs. |
| `tools/render_docs.py` | CLI: render documentation files (`README.md`, `site/*.html`) **in place** to the current released version. Used by the site build. |
| `tests/test_version.py` | Unit tests for `tools/version.py`. |
| `tests/test_render.py` | Unit tests for `tools/render.py`. |
| `tests/test_citation.py` | Unit tests for `tools/citation.py`. |
| `tests/test_build_release.py` | Unit tests for `tools/build_release.py`'s `build()` function. |
| `tests/test_sources.py` | Repository-level guard tests: no hardcoded versions in source, no fork URLs, `@@DATA-*@@` markers survive. |
| `.github/workflows/tests.yml` | Runs the unit tests on every push to main and every PR. |
| `.github/workflows/release.yml` | The manual release workflow. |
| `docs/RELEASING.md` | Human runbook for cutting a release. |

**Modified:**

| Path | Change |
|---|---|
| `ado/ssc2.ado:1` | Version header line → placeholders. |
| `sthlp/ssc2.sthlp:2` | Version comment line → placeholders. |
| `ssc2.pkg` | `Distribution-Date` → placeholder; add a `Version` line. |
| `stata.toc` | Add a version description line. |
| `CITATION.cff` | Not templated. Keeps real values; `version:` and `date-released:` are field-substituted for `dist` and kept in step on `main` by an auto-opened pull request. |
| `README.md` | Rewrite the Installation section; add a Releasing section. |
| `site/about.html:68-69` | Fix fork URL, use version placeholder, drop the `TODO AT MERGE` comment. |
| `site/index.html:341-344` | Same, inside the JS `render()` function. |
| `.github/workflows/site.yml` | Add `workflow_call` trigger, `fetch-depth: 0`, and a docs-rendering step. |

---

## Task 1: Version resolution logic

**Files:**
- Create: `tools/version.py`
- Create: `tests/test_version.py`
- Create: `.github/workflows/tests.yml`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `class Version(NamedTuple)` with fields `major: int`, `minor: int`, `patch: int`, `rc: int | None`; properties `is_prerelease -> bool`, `base -> Version`, `sort_key -> tuple`; `__str__` gives `"2.2.2"` or `"2.2.2-rc.1"`.
  - `parse(text: str) -> Version | None`
  - `tag_of(v: Version) -> str`
  - `known_versions(tags: Iterable[str]) -> list[Version]`
  - `latest_release(tags: Iterable[str]) -> Version | None`
  - `bump(v: Version, part: str) -> Version` where `part` is `"major" | "minor" | "patch"`
  - `next_version(tags: Iterable[str], part: str = "patch", prerelease: bool = False, override: str | None = None) -> Version`
  - `git_tags(repo: Path) -> list[str]`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_version.py`:

```python
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

```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s tests -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools'`

- [ ] **Step 3: Create the package marker so `tools` is importable**

Create `tools/__init__.py` containing exactly one line:

```python
"""Build and release tooling for the ssc2 package."""
```

- [ ] **Step 4: Write the implementation**

Create `tools/version.py`:

```python
"""Semantic-version arithmetic for ssc2 releases.

Everything here except git_tags() is pure -- no filesystem, no network,
no subprocess -- so the release logic can be unit-tested without a
repository. git_tags() is the single deliberate exception, kept here so
both CLI scripts can share one definition of "what tags exist".

Convention: version strings never carry a leading "v"; tag strings always
do. Use tag_of() to convert. parse() accepts either.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, NamedTuple, Optional
import re

# 2.2.2 or 2.2.2-rc.3, and nothing else. The legacy "v0.5-beta" tag and
# the old "-draft" suffixes deliberately do not match: they are not
# releases and must never take part in version arithmetic.
_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?$")


class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    rc: Optional[int] = None          # None => a final release

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return base if self.rc is None else f"{base}-rc.{self.rc}"

    @property
    def is_prerelease(self) -> bool:
        return self.rc is not None

    @property
    def base(self) -> "Version":
        """This version with any -rc suffix stripped."""
        return Version(self.major, self.minor, self.patch)

    @property
    def sort_key(self) -> tuple:
        # A final release sorts *after* all of its own release
        # candidates, so rc=None gets a marker that outranks any integer.
        return (self.major, self.minor, self.patch,
                1 if self.rc is None else 0,
                0 if self.rc is None else self.rc)


def parse(text: str) -> Optional[Version]:
    """Parse "2.2.2", "v2.2.2" or "v2.2.2-rc.1".

    Returns None -- never raises -- for anything that is not a release
    version, so a tag list containing junk can be filtered rather than
    guarded.
    """
    body = text[1:] if text.startswith("v") else text
    m = _RE.match(body)
    if m is None:
        return None
    major, minor, patch, rc = m.groups()
    return Version(int(major), int(minor), int(patch),
                   None if rc is None else int(rc))


def tag_of(v: Version) -> str:
    return f"v{v}"


def known_versions(tags: Iterable[str]) -> list:
    """Every tag that parses as a release version, ascending."""
    found = [v for v in (parse(t) for t in tags) if v is not None]
    return sorted(found, key=lambda v: v.sort_key)


def latest_release(tags: Iterable[str]) -> Optional[Version]:
    """Highest final (non-prerelease) version among tags, or None."""
    finals = [v for v in known_versions(tags) if not v.is_prerelease]
    return finals[-1] if finals else None


def bump(v: Version, part: str) -> Version:
    if part == "major":
        return Version(v.major + 1, 0, 0)
    if part == "minor":
        return Version(v.major, v.minor + 1, 0)
    if part == "patch":
        return Version(v.major, v.minor, v.patch + 1)
    raise ValueError(f"bump part must be major, minor or patch; got {part!r}")


def next_version(tags: Iterable[str], part: str = "patch",
                 prerelease: bool = False,
                 override: Optional[str] = None) -> Version:
    """Decide the version for the release being cut.

    With an override, that version is used verbatim after validation.
    Otherwise the newest final release is bumped by `part`; when
    `prerelease` is set the result gains the next free -rc.N suffix for
    that base. Clearing `prerelease` promotes an existing candidate
    series to its own base version rather than bumping past it, so
    2.2.2-rc.2 is followed by 2.2.2, not 2.2.3.
    """
    tags = list(tags)
    if override:
        v = parse(override)
        if v is None:
            raise ValueError(
                f"{override!r} is not a valid version: expected N.N.N or "
                f"N.N.N-rc.N, without a leading 'v'")
        if tag_of(v) in set(tags):
            raise ValueError(f"tag {tag_of(v)} already exists")
        if v.is_prerelease != prerelease:
            raise ValueError(
                f"version {v} is "
                f"{'a pre-release' if v.is_prerelease else 'a final release'} "
                f"but the pre-release flag is "
                f"{'set' if prerelease else 'not set'}")
        return v

    current = latest_release(tags)
    if current is None:
        raise ValueError(
            "no previous final release was found, so there is nothing to "
            "increment; pass an explicit version override for the first "
            "release")

    target = bump(current, part)
    if not prerelease:
        return target
    counters = [v.rc for v in known_versions(tags)
                if v.is_prerelease and v.base == target]
    return Version(target.major, target.minor, target.patch,
                   max(counters) + 1 if counters else 1)


def git_tags(repo: Path) -> list:
    """All tag names in `repo`. The one impure function in this module."""
    out = subprocess.run(
        ["git", "-C", str(repo), "tag", "--list"],
        check=True, capture_output=True, text=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all tests in `tests/test_version.py` ok.

- [ ] **Step 6: Add the CI workflow that runs these tests**

Create `.github/workflows/tests.yml`:

```yaml
# Unit tests for the release tooling in tools/.
#
# Standard library only -- no dependency installation step -- matching
# the rest of this repository's Python.

name: tests
on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch: {}

permissions:
  contents: read

jobs:
  unittest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          # tests/test_sources.py inspects the working tree; the release
          # tooling reads tags. Fetch everything so both behave the same
          # in CI as they do locally.
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Run unit tests
        run: python3 -m unittest discover -s tests -v
```

- [ ] **Step 7: Commit**

```bash
git add tools/__init__.py tools/version.py tests/test_version.py .github/workflows/tests.yml
git commit -m "feat: add semantic-version resolution for releases"
```

---

## Task 2: Placeholder rendering

**Files:**
- Create: `tools/render.py`
- Create: `tests/test_render.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `TOKEN_RE` — compiled `re.Pattern` matching `@[A-Z][A-Z0-9_]*@`
  - `context(version: str, when: datetime.date) -> dict[str, str]`
  - `render_text(text: str, ctx: dict[str, str]) -> str`
  - `render_file(src: Path, dst: Path, ctx: dict[str, str]) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_render.py`:

```python
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

```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_render -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.render'`

- [ ] **Step 3: Write the implementation**

Create `tools/render.py`:

```python
"""Placeholder substitution for release builds.

Source files on `main` carry @TOKEN@ placeholders instead of version
strings; cutting a release renders them to concrete values. The tokens
are deliberately loud so that an unrendered file is obvious on sight and
easy to catch in a test.

The token pattern is intentionally narrow. It must not match the
@@DATA-START@@ / @@DATA-END@@ markers that site/build_data.py depends on
in site/index.html -- the hyphens keep them out of the character class --
and it must not match CSS at-rules such as @media, which are lowercase.
Do not widen it.
"""
from __future__ import annotations

import datetime
import re
from pathlib import Path

TOKEN_RE = re.compile(r"@[A-Z][A-Z0-9_]*@")

# Stata writes dates as 08jul2026: two-digit day, lowercase three-letter
# month, four-digit year.
_STATA_MONTHS = ("jan", "feb", "mar", "apr", "may", "jun",
                 "jul", "aug", "sep", "oct", "nov", "dec")


def context(version: str, when: datetime.date) -> dict:
    """The complete token -> replacement mapping for one release.

    `version` carries no leading "v"; @VERSION_TAG@ adds it.
    """
    return {
        "@VERSION@": version,
        "@VERSION_TAG@": f"v{version}",
        "@DATE_STATA@": f"{when.day:02d}{_STATA_MONTHS[when.month - 1]}{when.year}",
        "@DATE_ISO@": when.isoformat(),
        "@DATE_COMPACT@": f"{when.year}{when.month:02d}{when.day:02d}",
    }


def render_text(text: str, ctx: dict) -> str:
    """Substitute every known token.

    Raises ValueError if any @TOKEN@-shaped string survives, which means
    a source file references a placeholder the build does not define.
    Failing loudly here is the point: a silently unrendered version
    string would ship to users.
    """
    for token, value in ctx.items():
        text = text.replace(token, value)
    leftover = sorted(set(TOKEN_RE.findall(text)))
    if leftover:
        raise ValueError("unknown placeholder(s): " + ", ".join(leftover))
    return text


def render_file(src: Path, dst: Path, ctx: dict) -> None:
    """Render `src` into `dst`, creating parent directories as needed."""
    try:
        out = render_text(src.read_text(encoding="utf-8"), ctx)
    except ValueError as exc:
        raise ValueError(f"{src}: {exc}") from None
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(out, encoding="utf-8")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — tests from Task 1 and Task 2 all ok.

- [ ] **Step 5: Commit**

```bash
git add tools/render.py tests/test_render.py
git commit -m "feat: add placeholder rendering for release builds"
```

---

## Task 3: Put placeholders into the package source files

**Files:**
- Modify: `ado/ssc2.ado:1`
- Modify: `sthlp/ssc2.sthlp:2`
- Modify: `ssc2.pkg`
- Modify: `stata.toc`
- Create: `tests/test_sources.py`

**Interfaces:**
- Consumes: `tools.render.TOKEN_RE` and `tools.render.context` from Task 2.
- Produces: a working tree in which `ado/ssc2.ado`, `sthlp/ssc2.sthlp`, `ssc2.pkg` and `stata.toc` contain `@VERSION@`, `@DATE_STATA@`, `@DATE_COMPACT@` and `@DATE_ISO@` instead of literal versions and dates.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_sources.py`:

```python
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

```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_sources -v`
Expected: FAIL — `test_ado_header_uses_placeholders` fails because line 1 is still `*! version 2.2.1-draft 29jul2026  L. Vilhuber and contributors`, and `test_no_literal_version_strings_remain` reports `2.2.1-draft`.

- [ ] **Step 3: Replace the version header in `ado/ssc2.ado`**

Change line 1 of `ado/ssc2.ado` from:

```stata
*! version 2.2.1-draft 29jul2026  L. Vilhuber and contributors
```

to:

```stata
*! version @VERSION@ @DATE_STATA@  L. Vilhuber and contributors
```

Leave lines 2–16 untouched. Note that `which ssc2` in Stata prints the
`*!` lines, so this header is how a user reads the installed version —
which is exactly why it must never ship unrendered.

- [ ] **Step 4: Replace the version comment in `sthlp/ssc2.sthlp`**

Change line 2 of `sthlp/ssc2.sthlp` from:

```
{* *! version 2.0.0-draft  08jul2026}{...}
```

to:

```
{* *! version @VERSION@  @DATE_STATA@}{...}
```

This line begins with `{* `, which `site/build_reference.py` skips
outright (see its `convert()` loop), so the Reference page is unaffected
either way.

- [ ] **Step 5: Add version metadata to `ssc2.pkg`**

Change the `Distribution-Date` line from:

```
d Distribution-Date: 20260708
```

to these two lines, in this order:

```
d Version: @VERSION@
d Distribution-Date: @DATE_COMPACT@
```

- [ ] **Step 6: Add a version line to `stata.toc`**

Change `stata.toc` from:

```
v 3
d ssc2: Install Stata packages from date-based snapshots of the SSC archive
d Labor Dynamics Institute
d https://github.com/labordynamicsinstitute/stata-ssc2
p ssc2 Install Stata packages from date-based snapshots of the SSC archive
```

to:

```
v 3
d ssc2: Install Stata packages from date-based snapshots of the SSC archive
d Labor Dynamics Institute
d Version @VERSION@ (@DATE_ISO@)
d https://github.com/labordynamicsinstitute/stata-ssc2
p ssc2 Install Stata packages from date-based snapshots of the SSC archive
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all tests ok.

- [ ] **Step 8: Verify the files render cleanly**

Run:

```bash
python3 - <<'PY'
import datetime, sys
from pathlib import Path
sys.path.insert(0, ".")
from tools.render import context, render_text
ctx = context("2.2.2", datetime.date(2026, 7, 30))
for rel in ["ado/ssc2.ado", "sthlp/ssc2.sthlp", "ssc2.pkg", "stata.toc"]:
    out = render_text(Path(rel).read_text(encoding="utf-8"), ctx)
    print(rel, "OK")
print(render_text(Path("ssc2.pkg").read_text(encoding="utf-8"), ctx))
PY
```

Expected: four `OK` lines, then the rendered `ssc2.pkg` showing
`d Version: 2.2.2` and `d Distribution-Date: 20260730`.

- [ ] **Step 9: Commit**

```bash
git add ado/ssc2.ado sthlp/ssc2.sthlp ssc2.pkg stata.toc tests/test_sources.py
git commit -m "refactor: replace hardcoded versions with build placeholders"
```

---

## Task 4: Release-tree builder CLI

**Files:**
- Create: `tools/build_release.py`
- Create: `tests/test_build_release.py`

**Interfaces:**
- Consumes: `tools.version.{git_tags, next_version, tag_of}` (Task 1), `tools.render.{context, render_file}` (Task 2).
- Produces:
  - `PACKAGE_FILES: list[str]` — repo-relative paths that get rendered.
  - `COPY_FILES: list[str]` — repo-relative paths copied verbatim.
  - `build(repo: Path, out: Path, version: str, when: datetime.date) -> None`
  - `main(argv: list[str] | None = None) -> int`
  - CLI writing `version=`, `tag=`, `prerelease=` to `$GITHUB_OUTPUT`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_build_release.py`:

```python
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

```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_build_release -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.build_release'`

- [ ] **Step 3: Write the implementation**

Create `tools/build_release.py`:

```python
#!/usr/bin/env python3
"""Build the release tree that gets published on the `dist` branch.

Resolves the next version from the repository's git tags, then renders
the package files -- the ones Stata's -net install- needs -- into an
output directory with every @TOKEN@ placeholder substituted.

Usage:
    python3 tools/build_release.py --out dist
    python3 tools/build_release.py --out dist --bump minor
    python3 tools/build_release.py --out dist --prerelease
    python3 tools/build_release.py --out dist --version 2.2.2

When $GITHUB_OUTPUT is set, writes `version=`, `tag=` and `prerelease=`
lines to it so the calling GitHub Actions job can consume them.
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.render import context, render_file          # noqa: E402
from tools.version import git_tags, next_version, tag_of  # noqa: E402

# Rendered into the release tree. Order is cosmetic. This is exactly the
# set -net install- needs (stata.toc + ssc2.pkg + the files ssc2.pkg
# lists) plus a README so the dist branch is readable on GitHub.
PACKAGE_FILES = [
    "stata.toc",
    "ssc2.pkg",
    "ado/ssc2.ado",
    "sthlp/ssc2.sthlp",
    "README.md",
]

# Copied byte-for-byte, never rendered.
COPY_FILES = ["LICENSE"]


def build(repo: Path, out: Path, version: str, when: datetime.date) -> None:
    """Render the release tree for `version` from `repo` into `out`.

    `out` is replaced wholesale, so a rerun never leaves a stale file
    from a previous build in the published tree.
    """
    ctx = context(version, when)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for rel in PACKAGE_FILES:
        render_file(repo / rel, out / rel, ctx)
    for rel in COPY_FILES:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / rel, dst)


def _emit_outputs(version: str, tag: str, prerelease: bool) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as fh:
        fh.write(f"version={version}\n")
        fh.write(f"tag={tag}\n")
        fh.write(f"prerelease={'true' if prerelease else 'false'}\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--repo", default=".", type=Path,
                   help="repository root (default: current directory)")
    p.add_argument("--out", required=True, type=Path,
                   help="directory to write the release tree into")
    p.add_argument("--bump", default="patch",
                   choices=["patch", "minor", "major"],
                   help="which part to increment when --version is absent")
    p.add_argument("--prerelease", action="store_true",
                   help="cut a -rc.N pre-release")
    p.add_argument("--version", default=None,
                   help="explicit version without a leading v, e.g. 2.2.2")
    p.add_argument("--date", default=None,
                   help="release date as YYYY-MM-DD (default: today, UTC)")
    args = p.parse_args(argv)

    when = (datetime.date.fromisoformat(args.date) if args.date
            else datetime.datetime.now(datetime.timezone.utc).date())

    try:
        version = next_version(git_tags(args.repo), part=args.bump,
                               prerelease=args.prerelease,
                               override=args.version)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    build(args.repo, args.out, str(version), when)
    tag = tag_of(version)
    print(f"built {version} ({tag}) into {args.out}")
    _emit_outputs(str(version), tag, version.is_prerelease)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all tests ok.

- [ ] **Step 5: Build the real release tree and inspect it**

Run:

```bash
python3 tools/build_release.py --out /tmp/ssc2-dist --version 2.2.2 --date 2026-07-30
find /tmp/ssc2-dist -type f | sort
head -1 /tmp/ssc2-dist/ado/ssc2.ado
cat /tmp/ssc2-dist/ssc2.pkg
cat /tmp/ssc2-dist/stata.toc
grep -c '@[A-Z]' -r /tmp/ssc2-dist/ado /tmp/ssc2-dist/sthlp /tmp/ssc2-dist/ssc2.pkg /tmp/ssc2-dist/stata.toc || echo "no placeholders survived"
```

Expected: six files listed (`README.md`, `LICENSE`, `ssc2.pkg`,
`stata.toc`, `ado/ssc2.ado`, `sthlp/ssc2.sthlp`); the ado header reads
`*! version 2.2.2 30jul2026  L. Vilhuber and contributors`; `ssc2.pkg`
shows `d Version: 2.2.2` and `d Distribution-Date: 20260730`; and
"no placeholders survived".

(`README.md` will still be the pre-Task-6 version at this point; that is
expected — Task 6 rewrites its Installation section. `CITATION.cff` is
not in the tree yet either; Task 5 adds it.)

- [ ] **Step 6: Commit**

```bash
git add tools/build_release.py tests/test_build_release.py
git commit -m "feat: add release-tree builder CLI"
```

---

## Task 5: Citation metadata

**Files:**
- Create: `tools/citation.py`
- Create: `tests/test_citation.py`
- Modify: `tools/build_release.py` (the `build()` function and the module docstring)
- Modify: `tests/test_build_release.py` (the `make_repo` fixture)

**Interfaces:**
- Consumes: nothing from earlier tasks — `tools/citation.py` is self-contained.
- Produces:
  - `set_release_fields(text: str, version: str, when: datetime.date) -> str`
  - `CITATION_FILE = "CITATION.cff"`
  - `build()` in `tools/build_release.py` gains the behaviour of writing a
    field-substituted `CITATION.cff` into the release tree. Its signature
    is unchanged: `build(repo: Path, out: Path, version: str, when: datetime.date) -> None`.

**Why this file is different from every other file in the plan.**
`CITATION.cff` must stay schema-valid on `main`, because GitHub validates
the default branch's copy to render the "Cite this repository" widget,
and an invalid file shows an error there. The CFF 1.2.0 schema constrains
`date-released` to a literal `YYYY-MM-DD` pattern, so `@DATE_ISO@` would
fail validation. `CITATION.cff` therefore keeps **real values** on `main`
and is updated by field substitution rather than token rendering. Task 8
opens a pull request that keeps `main`'s copy in step after each release.

Zenodo is the reason this matters beyond the widget: its GitHub
integration archives the source tarball **of the released tag**, which
lives on `dist` and is fully rendered, so DOI metadata is correct
regardless. `main`'s copy only drives the on-page widget.

A YAML parser is deliberately not used — the standard library has none,
and the whole job is replacing two top-level scalar lines.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_citation.py`:

```python
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

```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_citation -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.citation'`

- [ ] **Step 3: Write the implementation**

Create `tools/citation.py`:

```python
"""Keep CITATION.cff's release fields in step with the released version.

CITATION.cff is the one file in this project that cannot carry @TOKEN@
placeholders. GitHub validates the default branch's copy in order to
render the "Cite this repository" widget, and the CFF 1.2.0 schema
requires date-released to match YYYY-MM-DD exactly -- a placeholder
would make the file invalid and the widget would break.

So the file keeps real values everywhere and this module rewrites the
two release-dependent fields in place. Two callers use it: the release
builder, which writes the rendered copy into the dist tree, and the
release workflow, which opens a pull request bringing main's copy up to
date after a release.

Line-oriented on purpose. The standard library ships no YAML parser, and
adding a dependency to substitute two scalars would be absurd. Only
lines that begin at column zero are touched, so "version:" appearing
inside the indented abstract block or an author entry is left alone.
"""
from __future__ import annotations

import datetime
import re

CITATION_FILE = "CITATION.cff"

# Anchored at column zero: a top-level mapping key, not a nested one.
_VERSION_RE = re.compile(r"^version:.*$", re.MULTILINE)
_DATE_RE = re.compile(r"^date-released:.*$", re.MULTILINE)

# A bare YAML scalar is safe when it is only digits and dots. Anything
# else -- notably the "-rc.1" suffix -- gets quoted so the value is
# unambiguously a string.
_BARE_SAFE = re.compile(r"^\d+(?:\.\d+)*$")


def set_release_fields(text: str, version: str,
                       when: datetime.date) -> str:
    """Return `text` with `version:` and `date-released:` set.

    Raises ValueError if either top-level field is absent, rather than
    silently producing a file that omits the version.
    """
    if _VERSION_RE.search(text) is None:
        raise ValueError(
            f"{CITATION_FILE} has no top-level 'version:' field")
    if _DATE_RE.search(text) is None:
        raise ValueError(
            f"{CITATION_FILE} has no top-level 'date-released:' field")

    rendered = version if _BARE_SAFE.match(version) else f'"{version}"'
    text = _VERSION_RE.sub(f"version: {rendered}", text, count=1)
    text = _DATE_RE.sub(f"date-released: {when.isoformat()}", text,
                        count=1)
    return text


def main(argv=None) -> int:
    """Update a CITATION.cff in place.

    Used by the release workflow to produce the one-file pull request
    that keeps main's copy in step:

        python3 tools/citation.py --version 2.2.2 --in-place CITATION.cff
    """
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(description="Set CITATION.cff release fields")
    p.add_argument("path", type=Path, help="the CITATION.cff to update")
    p.add_argument("--version", required=True,
                   help="version without a leading v, e.g. 2.2.2")
    p.add_argument("--date", default=None,
                   help="release date as YYYY-MM-DD (default: today, UTC)")
    p.add_argument("--in-place", action="store_true",
                   help="write the file back; otherwise print to stdout")
    args = p.parse_args(argv)

    when = (datetime.date.fromisoformat(args.date) if args.date
            else datetime.datetime.now(datetime.timezone.utc).date())
    try:
        out = set_release_fields(args.path.read_text(encoding="utf-8"),
                                 args.version, when)
    except ValueError as exc:
        print(f"error: {args.path}: {exc}", file=sys.stderr)
        return 1

    if args.in_place:
        args.path.write_text(out, encoding="utf-8")
        print(f"updated {args.path} to {args.version} ({when.isoformat()})")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

The module's imports at the top must therefore be:

```python
import datetime
import re
import sys
```

Note that the workflow passes the positional path **after** the flags
(`--version 2.2.2 --in-place CITATION.cff`); `argparse` accepts that
ordering.

Note the anchoring: `^version:` under `re.MULTILINE` matches only at the
start of a line, so `cff-version:` (which does not start with `version`)
and the indented `  version:` inside the abstract are both safe.

- [ ] **Step 4: Run the citation tests**

Run: `python3 -m unittest tests.test_citation -v`
Expected: FAIL on `TestAgainstTheRealFile` only — the other tests pass.
`CITATION.cff` exists on `main` already (merged in PR #7), so if it does
not exist in your worktree, run `git pull` first and re-run.

- [ ] **Step 5: Teach the release builder about CITATION.cff**

In `tools/build_release.py`, add the import beneath the existing ones:

```python
from tools.citation import CITATION_FILE, set_release_fields  # noqa: E402
```

Then replace the `build()` function with:

```python
def build(repo: Path, out: Path, version: str, when: datetime.date) -> None:
    """Render the release tree for `version` from `repo` into `out`.

    `out` is replaced wholesale, so a rerun never leaves a stale file
    from a previous build in the published tree.
    """
    ctx = context(version, when)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for rel in PACKAGE_FILES:
        render_file(repo / rel, out / rel, ctx)
    for rel in COPY_FILES:
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / rel, dst)
    # CITATION.cff carries real values rather than placeholders, so it
    # is field-substituted instead of rendered. See tools/citation.py.
    src = (repo / CITATION_FILE).read_text(encoding="utf-8")
    (out / CITATION_FILE).write_text(
        set_release_fields(src, version, when), encoding="utf-8")
```

Also extend the module docstring's first paragraph to mention it —
replace:

```python
Resolves the next version from the repository's git tags, then renders
the package files -- the ones Stata's -net install- needs -- into an
output directory with every @TOKEN@ placeholder substituted.
```

with:

```python
Resolves the next version from the repository's git tags, then renders
the package files -- the ones Stata's -net install- needs -- into an
output directory with every @TOKEN@ placeholder substituted. CITATION.cff
is handled separately, by field substitution rather than rendering,
because it must stay schema-valid on main; see tools/citation.py.
```

- [ ] **Step 6: Extend the builder's test fixture and add coverage**

In `tests/test_build_release.py`, add this line to `make_repo`, directly
before the `subprocess.run(["git", "init", ...])` call:

```python
    (repo / "CITATION.cff").write_text(
        "cff-version: 1.2.0\nversion: 0.0.0\ndate-released: 2000-01-01\n",
        encoding="utf-8")
```

Then append this class at the end of the file:

```python
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
```

- [ ] **Step 7: Add CITATION.cff to the source guard tests**

In `tests/test_sources.py`, append this class at the end of the file:

```python
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
```

- [ ] **Step 8: Run the whole suite**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — every test ok, including `TestAgainstTheRealFile`.

- [ ] **Step 9: Build a real release tree and inspect the citation file**

Run:

```bash
python3 tools/build_release.py --out /tmp/ssc2-dist --version 2.2.2 --date 2026-07-30
cat /tmp/ssc2-dist/CITATION.cff
```

Expected: the file is byte-identical to the repository's `CITATION.cff`
except `version: 2.2.2` and `date-released: 2026-07-30`. Confirm the
authors block and the abstract are intact.

- [ ] **Step 10: Commit**

```bash
git add tools/citation.py tests/test_citation.py tools/build_release.py tests/test_build_release.py tests/test_sources.py
git commit -m "feat: keep CITATION.cff in step with the released version"
```

---

## Task 6: Placeholders in the documentation, and fix the fork URLs

**Files:**
- Create: `tools/render_docs.py`
- Modify: `README.md`
- Modify: `site/about.html:68-69`
- Modify: `site/index.html:341-344`
- Modify: `tests/test_sources.py`

**Interfaces:**
- Consumes: `tools.render.{context, render_text}` (Task 2), `tools.version.{git_tags, latest_release}` (Task 1).
- Produces: `main(argv: list[str] | None = None) -> int` in `tools/render_docs.py`, invoked as
  `python3 tools/render_docs.py [--version V] [--date YYYY-MM-DD] [--repo .] FILE...`,
  rendering each FILE **in place**.

- [ ] **Step 1: Extend the guard tests**

In `tests/test_sources.py`, append these two classes at the end of the file:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest tests.test_sources -v`
Expected: FAIL — `test_no_fork_owner_anywhere` fails on `site/about.html`
and `site/index.html`; `test_readme_pins_via_placeholder` fails.

- [ ] **Step 3: Rewrite the README Installation section**

In `README.md`, replace this block:

````markdown
## Installation

```stata
* ssc2 may be installed directly from GitHub
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/main")
```

```stata
* or a specific release, e.g. v1.0.0
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/v1.0.0/")
```
````

with:

````markdown
## Installation

Released versions live on the `dist` branch and are tagged. The `latest`
tag always points at the newest stable release, never at a pre-release.

```stata
* the current stable release
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/latest/")
```

To pin an exact version — which is what you want in a replication
package — use the release tag instead of `latest`:

```stata
* a specific release
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/@VERSION_TAG@/")
```

> On the `main` branch `@VERSION_TAG@` above is a build placeholder. Each
> published release renders it to that release's own tag; see
> [Releases](https://github.com/labordynamicsinstitute/stata-ssc2/releases)
> for every tag you can substitute. Do **not** install from `main` — its
> version strings are unrendered placeholders.
````

- [ ] **Step 4: Fix the About page install block**

In `site/about.html`, replace lines 68–69:

```html
<!-- TODO AT MERGE: change ian-joyce -> labordynamicsinstitute -->
<pre>net install ssc2, all replace from("https://raw.githubusercontent.com/ian-joyce/stata-ssc2/main")</pre>
```

with:

```html
<pre>net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/latest/")</pre>
<p>To pin an exact version in a replication package, use the release tag
instead of <code>latest</code>:</p>
<pre>net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/@VERSION_TAG@/")</pre>
```

- [ ] **Step 5: Fix the snapshot picker's bootstrap line**

In `site/index.html`, inside `function render()`, replace these four
lines (around lines 341–344):

```js
    lines.push('<span class="cm">* one-time: install the ssc2 command itself</span>');
    // TODO AT MERGE: change ian-joyce -> labordynamicsinstitute once the
    // rewrite is merged upstream (upstream main still serves ssc2 v1.1.7)
    lines.push('<span class="p">. </span>net install ssc2, all replace from("https://raw.githubusercontent.com/ian-joyce/stata-ssc2/main")');
```

with:

```js
    lines.push('<span class="cm">* one-time: install ssc2 itself (@VERSION_TAG@; use "latest" to track releases)</span>');
    lines.push('<span class="p">. </span>net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/@VERSION_TAG@/")');
```

- [ ] **Step 6: Write the docs renderer**

Create `tools/render_docs.py`:

```python
#!/usr/bin/env python3
"""Render documentation placeholders in place.

Unlike tools/build_release.py, which renders the *next* version into a
fresh tree, this renders the *current* released version into files that
are about to be published as-is -- the website. It edits the given files
in place, so run it only on a throwaway checkout (a CI working copy),
never on a working tree you intend to commit.

Usage:
    python3 tools/render_docs.py README.md site/about.html site/index.html
    python3 tools/render_docs.py --version 2.2.2 site/index.html

With no --version, the newest stable release tag in --repo is used, so
the deployed site always advertises a tag that actually exists.
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.render import context, render_text            # noqa: E402
from tools.version import git_tags, latest_release       # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+", type=Path,
                   help="files to render in place")
    p.add_argument("--repo", default=".", type=Path,
                   help="repository root used to resolve tags (default: .)")
    p.add_argument("--version", default=None,
                   help="version to render; defaults to the newest stable tag")
    p.add_argument("--date", default=None,
                   help="date as YYYY-MM-DD (default: today, UTC)")
    args = p.parse_args(argv)

    version = args.version
    if version is None:
        current = latest_release(git_tags(args.repo))
        if current is None:
            print("error: no stable release tag was found, so there is no "
                  "version to advertise; pass --version explicitly",
                  file=sys.stderr)
            return 1
        version = str(current)

    when = (datetime.date.fromisoformat(args.date) if args.date
            else datetime.datetime.now(datetime.timezone.utc).date())
    ctx = context(version, when)

    for path in args.files:
        try:
            rendered = render_text(path.read_text(encoding="utf-8"), ctx)
        except ValueError as exc:
            print(f"error: {path}: {exc}", file=sys.stderr)
            return 1
        path.write_text(rendered, encoding="utf-8")
        print(f"rendered {path} at {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — all tests ok.

- [ ] **Step 8: Verify the docs render without touching the data markers**

Run:

```bash
rm -rf /tmp/ssc2-doccheck && mkdir -p /tmp/ssc2-doccheck/site
cp README.md /tmp/ssc2-doccheck/
cp site/about.html site/index.html /tmp/ssc2-doccheck/site/
python3 tools/render_docs.py --version 2.2.2 --date 2026-07-30 \
  /tmp/ssc2-doccheck/README.md \
  /tmp/ssc2-doccheck/site/about.html \
  /tmp/ssc2-doccheck/site/index.html
grep -n "stata-ssc2/v2.2.2" /tmp/ssc2-doccheck/README.md /tmp/ssc2-doccheck/site/*.html
grep -c "@@DATA-START@@\|@@DATA-END@@" /tmp/ssc2-doccheck/site/index.html
grep -rn "ian-joyce" /tmp/ssc2-doccheck/ || echo "no fork URLs"
```

Expected: three `rendered ...` lines; `stata-ssc2/v2.2.2` found in all
three files; the marker count is `2`; and "no fork URLs".

- [ ] **Step 9: Confirm the data-refresh script still works on the rendered page**

`site/build_data.py` runs before the docs renderer in CI, but it must
also be safe after it. Run:

```bash
python3 site/build_data.py /tmp/ssc2-doccheck/site/index.html && \
  grep -c "@@DATA-START@@" /tmp/ssc2-doccheck/site/index.html
```

Expected: the script reports success and the marker count is still `1`
for `@@DATA-START@@`. If this step needs network access and the sandbox
has none, note the failure as environmental and confirm instead that
both markers are present with `grep -c "@@DATA-" /tmp/ssc2-doccheck/site/index.html`
returning `2`.

- [ ] **Step 10: Commit**

```bash
git add tools/render_docs.py README.md site/about.html site/index.html tests/test_sources.py
git commit -m "docs: pin install instructions to release tags, drop fork URLs"
```

---

## Task 7: Wire the docs renderer into the site build

**Files:**
- Modify: `.github/workflows/site.yml`

**Interfaces:**
- Consumes: `tools/render_docs.py` (Task 6).
- Produces: a `site` workflow that is callable from another workflow via
  `uses: ./.github/workflows/site.yml`, and whose deployed pages show a
  real release tag.

- [ ] **Step 1: Add the `workflow_call` trigger and full tag history**

In `.github/workflows/site.yml`, change the `on:` block from:

```yaml
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "30 6 * * 1"      # Mondays 06:30 UTC (after the mirror's daily run)
  workflow_dispatch: {}
```

to:

```yaml
on:
  push:
    branches: [main]
  pull_request:
  schedule:
    - cron: "30 6 * * 1"      # Mondays 06:30 UTC (after the mirror's daily run)
  workflow_dispatch: {}
  # Called by release.yml so a new release republishes the site with its
  # install instructions pointing at the version just published.
  workflow_call: {}
```

- [ ] **Step 2: Fetch tags in the build job**

In the `build` job, change:

```yaml
      - uses: actions/checkout@v4
```

to:

```yaml
      - uses: actions/checkout@v4
        with:
          # tools/render_docs.py resolves the newest stable release tag,
          # which the default shallow checkout does not fetch.
          fetch-depth: 0
```

- [ ] **Step 3: Add the rendering step**

In the `build` job, insert this step immediately **after** the
"Regenerate Reference page from the Stata help file" step and **before**
"Upload site artifact":

```yaml
      - name: Render version placeholders in the site
        # Edits the CI working copy in place; nothing is committed back.
        run: python3 tools/render_docs.py site/about.html site/index.html
```

- [ ] **Step 4: Update the workflow's header comment**

Replace the comment block at the top of `.github/workflows/site.yml`
(the lines from `# Build and deploy` down to `# Requires: ...`) with:

```yaml
# Build and deploy the ssc2 website (site/ directory) via Action-based
# GitHub Pages deployment.
#
#   build:  runs on every PR and every push to main, weekly by cron, and
#           whenever release.yml calls this workflow. Refreshes the
#           embedded snapshot/package data, regenerates the Reference
#           page from the Stata help file, renders version placeholders
#           to the newest stable release tag, then uploads the site as
#           the Pages artifact. On PRs this artifact can be downloaded
#           from the run page to inspect the HTML without deploying.
#   deploy: runs only for main (pushes, cron, and release calls), never PRs.
#
# The weekly rebuild keeps embedded data at most 7 days stale; the page's
# own single async API call tops up newer snapshot dates per visit.
# Data regeneration and placeholder rendering happen in CI at build time
# and land in the deployed artifact only -- nothing is committed back to
# the repository, so main keeps its @TOKEN@ placeholders.
#
# Requires: repository Settings -> Pages -> Source = "GitHub Actions".
```

- [ ] **Step 5: Validate the workflow file parses**

Run:

```bash
python3 -c "
import sys
try:
    import yaml
except ImportError:
    sys.exit('PyYAML unavailable; skipping (CI will validate)')
d = yaml.safe_load(open('.github/workflows/site.yml'))
trig = d[True] if True in d else d['on']
assert 'workflow_call' in trig, trig
assert d['jobs']['build']['steps'][0]['with']['fetch-depth'] == 0
names = [s.get('name','') for s in d['jobs']['build']['steps']]
assert 'Render version placeholders in the site' in names, names
assert names.index('Render version placeholders in the site') < names.index('Upload site artifact')
print('site.yml OK')
"
```

Expected: `site.yml OK` (or the skip message if PyYAML is not installed —
in that case just re-read the file and confirm the step ordering by eye).

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/site.yml
git commit -m "ci: render version placeholders during the site build"
```

---

## Task 8: The release workflow

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `tools/build_release.py` (Tasks 4 and 5) and its `version` / `tag` /
  `prerelease` step outputs; `.github/workflows/site.yml`'s
  `workflow_call` trigger (Task 7).
- Produces: a `release` workflow triggered by `workflow_dispatch` with
  inputs `version` (string), `bump` (choice), `prerelease` (boolean).

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/release.yml`:

```yaml
# Cut a release of the ssc2 package. Manual trigger only.
#
# What a run does, in order:
#   1. runs the unit tests, so a broken tree cannot be released;
#   2. resolves the version -- the explicit `version` input if given,
#      otherwise the newest stable tag incremented by `bump`, with an
#      -rc.N suffix when `prerelease` is ticked;
#   3. renders the @TOKEN@ placeholders into a release tree;
#   4. publishes that tree as a commit on the orphan `dist` branch and
#      tags it. `main` is never modified;
#   5. creates the GitHub release -- which is also what Zenodo watches,
#      and Zenodo archives the tag's tarball, so the DOI metadata comes
#      from the rendered CITATION.cff on dist;
#   6. for stable releases only, force-moves the floating `latest` tag.
#      This happens after the release exists, so a failed release cannot
#      leave `latest` pointing at a version with nothing behind it;
#   7. for stable releases only, opens a pull request against main
#      updating CITATION.cff's two release fields. It is never pushed
#      straight to main -- a human merges it;
#   8. calls site.yml so the website advertises the new version.
#
# The very first run must pass version = 2.2.2 explicitly: the newest
# released tag is v1.1.7 while the source claimed 2.2.1-draft, and the
# decision was to adopt the source version. Later runs need no input.
#
# Users install from the tags this creates:
#   net install ssc2, all replace ///
#     from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/latest/")

name: release
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Explicit version, no leading v (e.g. 2.2.2 or 2.3.0-rc.1). Blank = auto-increment."
        required: false
        type: string
      bump:
        description: "Which part to increment when version is blank"
        required: false
        default: patch
        type: choice
        options: [patch, minor, major]
      prerelease:
        description: "Mark as a pre-release (adds/advances -rc.N; the latest tag is NOT moved)"
        required: false
        default: false
        type: boolean

permissions:
  contents: write        # push the dist branch and tags, create the release
  pull-requests: write   # open the CITATION.cff sync PR against main
  pages: write           # the site job this workflow calls
  id-token: write        # ditto

concurrency:
  group: release
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    # A release must be cut from main: dist's history, the citation PR's
    # base (origin/main), and site.yml's deploy gate (github.ref ==
    # refs/heads/main) all assume it, so a dispatch from a feature branch
    # would silently disagree with all three.
    if: github.ref == 'refs/heads/main'
    outputs:
      version: ${{ steps.build.outputs.version }}
      tag: ${{ steps.build.outputs.tag }}
      prerelease: ${{ steps.build.outputs.prerelease }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0      # version resolution reads every tag
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Run the unit tests
        run: python3 -m unittest discover -s tests -v

      - name: Build the release tree
        id: build
        env:
          IN_VERSION: ${{ inputs.version }}
          IN_BUMP: ${{ inputs.bump }}
          IN_PRERELEASE: ${{ inputs.prerelease }}
        run: |
          set -euo pipefail
          args=(--out "$RUNNER_TEMP/dist" --bump "$IN_BUMP")
          if [ "$IN_PRERELEASE" = "true" ]; then
            args+=(--prerelease)
          fi
          if [ -n "$IN_VERSION" ]; then
            args+=(--version "$IN_VERSION")
          fi
          python3 tools/build_release.py "${args[@]}"

      - name: Publish the release tree on the dist branch
        env:
          TAG: ${{ steps.build.outputs.tag }}
        run: |
          set -euo pipefail
          # A runner has no git identity of its own; this is the standard
          # bot identity and applies to CI only.
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          # Fail early and legibly on an accidental rerun, before anything
          # is pushed. Without this, a rerun renders a byte-identical tree
          # and dies on an opaque "nothing to commit" from git instead.
          if git ls-remote --exit-code origin "refs/tags/$TAG" >/dev/null 2>&1; then
            echo "error: tag $TAG is already published." >&2
            echo "  To finish a run that failed after the tag was pushed, create the" >&2
            echo "  release manually:  gh release create $TAG --generate-notes" >&2
            echo "  To re-cut this version, delete the release and its tag first." >&2
            exit 1
          fi

          if git ls-remote --exit-code --heads origin dist >/dev/null 2>&1; then
            git fetch origin dist:dist
            git worktree add "$RUNNER_TEMP/wt" dist
          else
            # First release: start dist with no history from main.
            git worktree add --detach "$RUNNER_TEMP/wt"
            git -C "$RUNNER_TEMP/wt" checkout --orphan dist
            git -C "$RUNNER_TEMP/wt" rm -rf --quiet . || true
          fi

          # Replace the tree wholesale so a file dropped from a release
          # really disappears.
          find "$RUNNER_TEMP/wt" -mindepth 1 -maxdepth 1 \
               ! -name .git -exec rm -rf {} +
          cp -a "$RUNNER_TEMP/dist/." "$RUNNER_TEMP/wt/"

          git -C "$RUNNER_TEMP/wt" add -A
          # --allow-empty covers re-cutting a version whose tag was
          # deleted (see the runbook): the tag is gone so the guard above
          # passes, but the previous release commit is still on dist, so
          # the freshly rendered tree is byte-identical and a plain
          # commit would fail with "nothing to commit".
          git -C "$RUNNER_TEMP/wt" commit --allow-empty -m "release $TAG"
          git -C "$RUNNER_TEMP/wt" tag -a "$TAG" -m "ssc2 $TAG"
          # One atomic push: a branch that lands without its tag would
          # leave an untagged release commit on dist and wedge the rerun.
          git -C "$RUNNER_TEMP/wt" push --atomic origin dist "refs/tags/$TAG"

      - name: Create the GitHub release
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.build.outputs.tag }}
          IS_PRE: ${{ steps.build.outputs.prerelease }}
        run: |
          set -euo pipefail
          if [ "$IS_PRE" = "true" ]; then
            flag=--prerelease
          else
            flag=--latest
          fi
          gh release create "$TAG" \
            --title "ssc2 $TAG" \
            --generate-notes \
            "$flag"

      - name: Move the latest tag
        # Runs AFTER the release exists. If gh release create fails, we do
        # not want `latest` already advertising a version with no release
        # (and so no Zenodo archive) behind it.
        if: ${{ steps.build.outputs.prerelease == 'false' }}
        env:
          TAG: ${{ steps.build.outputs.tag }}
        run: |
          set -euo pipefail
          # "$TAG^{}" peels the annotated tag object down to its commit.
          # Without the peel git creates a nested tag-of-a-tag, and the
          # entire documented install path rests on this ref.
          git -C "$RUNNER_TEMP/wt" tag -f latest "$TAG^{}"
          git -C "$RUNNER_TEMP/wt" push -f origin "refs/tags/latest:refs/tags/latest"

      - name: Open a pull request syncing CITATION.cff on main
        # Stable releases only: an -rc.N candidate should not change the
        # citation metadata people see on the repository page.
        #
        # This is a branch cut from main touching exactly one file, NOT a
        # merge from dist. dist is an orphan branch whose tree is only
        # the installable files; merging it into main would delete site/,
        # tools/, tests/ and .github/.
        if: ${{ steps.build.outputs.prerelease == 'false' }}
        env:
          GH_TOKEN: ${{ github.token }}
          VERSION: ${{ steps.build.outputs.version }}
          TAG: ${{ steps.build.outputs.tag }}
        run: |
          set -euo pipefail
          # The checkout for this job is main; branch from a clean copy
          # of it so nothing the build wrote can leak into the PR.
          git checkout -B "citation/$TAG" origin/main

          python3 tools/citation.py --version "$VERSION" --in-place CITATION.cff

          if git diff --quiet -- CITATION.cff; then
            echo "CITATION.cff already matches $TAG; no pull request needed."
            exit 0
          fi

          # Build the body in a file: a multi-line --body argument would
          # otherwise carry this block's YAML indentation into the PR.
          {
            printf 'Updates `CITATION.cff` to the values published in %s/%s/releases/tag/%s.\n\n' \
              "$GITHUB_SERVER_URL" "$GITHUB_REPOSITORY" "$TAG"
            printf 'Opened automatically by the release workflow. Merging is manual and optional: the released tag on `dist` already carries the correct metadata, so Zenodo archiving is unaffected either way. This PR only keeps the "Cite this repository" widget on `main` current.\n\n'
            printf 'Two lines change: `version` and `date-released`.\n'
          } > "$RUNNER_TEMP/pr-body.md"

          git add CITATION.cff
          git commit -m "chore: citation metadata for $TAG"
          # Plain --force, not --force-with-lease: a fresh runner has no
          # remote-tracking ref for this branch, so the lease has no
          # baseline and git rejects the push as "stale info". The branch
          # is workflow-owned and disposable, so --force is appropriate.
          git push --force -u origin "citation/$TAG"
          gh pr create \
            --base main \
            --head "citation/$TAG" \
            --title "chore: citation metadata for $TAG" \
            --body-file "$RUNNER_TEMP/pr-body.md"

      - name: Summarise
        env:
          TAG: ${{ steps.build.outputs.tag }}
          IS_PRE: ${{ steps.build.outputs.prerelease }}
        run: |
          {
            echo "## Released \`$TAG\`"
            echo
            echo "Pre-release: \`$IS_PRE\`"
            echo
            echo '```stata'
            echo "net install ssc2, all replace from(\"https://raw.githubusercontent.com/${GITHUB_REPOSITORY}/${TAG}/\")"
            echo '```'
            if [ "$IS_PRE" = "false" ]; then
              echo
              echo 'The `latest` tag now points here.'
            fi
          } >> "$GITHUB_STEP_SUMMARY"

  site:
    needs: release
    permissions:
      contents: read
      pages: write
      id-token: write
    uses: ./.github/workflows/site.yml
```

- [ ] **Step 2: Validate the workflow file parses and is internally consistent**

Run:

```bash
python3 -c "
import sys
try:
    import yaml
except ImportError:
    sys.exit('PyYAML unavailable; skipping (CI will validate)')
d = yaml.safe_load(open('.github/workflows/release.yml'))
trig = d[True] if True in d else d['on']
inputs = trig['workflow_dispatch']['inputs']
assert set(inputs) == {'version','bump','prerelease'}, set(inputs)
assert inputs['bump']['options'] == ['patch','minor','major']
assert inputs['prerelease']['type'] == 'boolean'
rel = d['jobs']['release']
assert set(rel['outputs']) == {'version','tag','prerelease'}
assert d['permissions']['pull-requests'] == 'write'
names = [s.get('name','') for s in rel['steps']]
pr = 'Open a pull request syncing CITATION.cff on main'
assert pr in names, names
# The PR must come after the release exists, and both it and the latest
# tag must be gated on this NOT being a pre-release.
assert names.index('Create the GitHub release') < names.index(pr)
# latest must move only after the release it points at actually exists.
assert names.index('Create the GitHub release') < names.index('Move the latest tag')
for n in ('Move the latest tag', pr):
    step = rel['steps'][names.index(n)]
    assert \"prerelease == 'false'\" in step['if'], (n, step.get('if'))
assert d['jobs']['site']['needs'] == 'release'
assert d['jobs']['site']['uses'] == './.github/workflows/site.yml'
print('release.yml OK')
"
```

Expected: `release.yml OK` (or the skip message; then verify by eye).

- [ ] **Step 3: Dry-run the version resolution against the real tag list**

This proves the workflow's step 2 would pick the versions the plan
promises, without pushing anything:

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, ".")
from pathlib import Path
from tools.version import git_tags, next_version

tags = git_tags(Path("."))
print("tags in repo:", tags)

# First release: an explicit override is required.
print("override 2.2.2      ->", next_version(tags, override="2.2.2"))

# After that first release, auto-increment takes over.
after = tags + ["v2.2.2"]
print("auto patch          ->", next_version(after))
print("auto minor          ->", next_version(after, part="minor"))
print("auto prerelease     ->", next_version(after, prerelease=True))
print("second prerelease   ->", next_version(after + ["v2.2.3-rc.1"], prerelease=True))
print("promote candidate   ->", next_version(after + ["v2.2.3-rc.1"]))

# Why the first release needs the override: left alone, today's tags
# would continue the v1.1.x line instead of adopting the source version.
print("no override today   ->", next_version(tags))

# The legacy tag on its own is not a release, so there is nothing to
# increment from.
try:
    next_version(["v0.5-beta"])
except ValueError as exc:
    print("legacy tag only     -> refused:", exc)
PY
```

Expected output:

```
tags in repo: ['v0.5-beta', 'v1.1.7']
override 2.2.2      -> 2.2.2
auto patch          -> 2.2.3
auto minor          -> 2.3.0
auto prerelease     -> 2.2.3-rc.1
second prerelease   -> 2.2.3-rc.2
promote candidate   -> 2.2.3
no override today   -> 1.1.8
legacy tag only     -> refused: no previous final release was found, ...
```

The `no override today -> 1.1.8` line is the point: `v1.1.7` is a valid
prior release, so auto-increment would quietly continue that line. That
is exactly why the first run must pass `2.2.2` explicitly.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add manual release workflow publishing to a dist branch"
```

---

## Task 9: The release runbook

**Files:**
- Create: `docs/RELEASING.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above. Produces no code.

- [ ] **Step 1: Write the runbook**

Create `docs/RELEASING.md`:

````markdown
# Releasing ssc2

Releases are cut by the **release** workflow. Nothing is released by
pushing to `main`, and `main` is never rewritten by CI.

## Branch and tag layout

| Ref | What it holds |
|---|---|
| `main` | Source with `@TOKEN@` placeholders instead of version strings. Not installable. `CITATION.cff` is the one file here holding real values. |
| `dist` | Orphan branch. One commit per release, holding the rendered, installable tree. An output, never an input — **never merge it into `main`**. |
| `vX.Y.Z` | Tag on a `dist` commit. A stable release. |
| `vX.Y.Z-rc.N` | Tag on a `dist` commit. A pre-release. |
| `latest` | Floating tag, force-moved to the newest **stable** release. Never points at a pre-release. |
| `citation/vX.Y.Z` | Short-lived branch cut from `main`, holding the one-file citation update. Delete it when its pull request merges. |

## Cutting a release

1. Go to **Actions → release → Run workflow**.
2. Fill in the inputs:

   | Input | Meaning |
   |---|---|
   | `version` | Leave **blank** for normal releases. Fill in only to override, e.g. `3.0.0`. No leading `v`. |
   | `bump` | `patch` (default), `minor`, or `major`. Ignored when `version` is set. |
   | `prerelease` | Tick to cut an `-rc.N` candidate. The `latest` tag is not moved. |

3. Run it. The workflow tests, builds, tags, releases, and redeploys the
   website.

### What the version arithmetic does

Starting from a newest stable tag of `v2.2.2`:

| Inputs | Result |
|---|---|
| all defaults | `v2.2.3` |
| `bump: minor` | `v2.3.0` |
| `bump: major` | `v3.0.0` |
| `prerelease` ticked | `v2.2.3-rc.1` |
| `prerelease` ticked again | `v2.2.3-rc.2` |
| `prerelease` cleared after the candidates | `v2.2.3` — promotion, not a further bump |
| `version: 4.1.0` | `v4.1.0` |

The legacy `v0.5-beta` tag does not parse as a release version and is
ignored throughout.

### The first release

Run it **once** with `version` set to `2.2.2`. The newest released tag is
`v1.1.7`, but the source carried `2.2.1-draft` and the decision was to
adopt the source lineage. There is no `v2.2.1` tag and none will be
created. Every later run can leave `version` blank.

## After the workflow runs: the CITATION.cff pull request

Stable releases leave one thing for you to do. The workflow opens a pull
request titled `chore: citation metadata for vX.Y.Z`, changing two lines
of `CITATION.cff` on `main`. Review and merge it.

It is **not** urgent and not load-bearing:

- The released tag on `dist` already carries the correct
  `CITATION.cff`, so anything reading a release — Zenodo included — is
  already right.
- `main`'s copy only drives the "Cite this repository" widget on the
  repository page. Until you merge, that widget shows the previous
  release's version.

If you skip a few, the next PR still brings `main` fully up to date; the
workflow always writes the current values rather than a diff. Close the
stale ones and delete their `citation/vX.Y.Z` branches.

Pre-releases do not open a PR at all.

### Why not merge `dist` into `main`?

Because it would destroy the repository. `dist` is an **orphan** branch:
no shared history with `main`, and its tree contains only the six
installable files. Merging it would delete `site/`, `tools/`, `tests/`
and `.github/`, and replace the sources with their rendered copies.
`dist` is an output, never an input. The citation PR is branched from
`main`, not from `dist`.

## Zenodo archiving

The design is already Zenodo-ready; nothing in the release workflow needs
to change to enable it.

Zenodo's GitHub integration listens for the `release` webhook and
archives **the source tarball of the released tag**. Those tags live on
`dist`, so the archived tarball is the fully rendered tree:
`CITATION.cff` with the right `version` and `date-released`, `ssc2.pkg`
with the right `Distribution-Date`, and no `@TOKEN@` anywhere. Zenodo
reads `CITATION.cff` from that tarball for the deposition metadata, so
the DOI record is correct without any extra step.

To turn it on: log in to Zenodo with GitHub, flip the switch for
`labordynamicsinstitute/stata-ssc2`, then cut a release. Zenodo only sees
releases published *after* the switch is flipped.

Two things worth knowing before you enable it:

- **What gets archived is the package, not the repository.** The `dist`
  tarball holds `stata.toc`, `ssc2.pkg`, `ado/`, `sthlp/`, `README.md`,
  `LICENSE` and `CITATION.cff` — the installable artifact, with no
  `site/`, `tools/` or test suite, and no history. For a Stata package
  that is arguably the right thing to archive. If you would rather
  archive the full source, archive a tag on `main` instead, which means
  reworking where tags live.
- **Pre-releases are archived too.** Zenodo's integration does not filter
  them, so every `-rc.N` release would mint its own DOI. If that is
  unwanted, stop publishing GitHub *releases* for candidates: delete the
  "Create the GitHub release" step's `--prerelease` branch and skip
  release creation when `steps.build.outputs.prerelease == 'true'`. The
  tag on `dist` still exists and is still installable, so candidates
  remain testable — they just stop appearing in the releases list.

## Placeholders

Five tokens, defined in `tools/render.py`. `CITATION.cff` uses none of
them — see below.

| Token | Example |
|---|---|
| `@VERSION@` | `2.2.2` |
| `@VERSION_TAG@` | `v2.2.2` |
| `@DATE_STATA@` | `30jul2026` |
| `@DATE_ISO@` | `2026-07-30` |
| `@DATE_COMPACT@` | `20260730` |

They appear in `ado/ssc2.ado`, `sthlp/ssc2.sthlp`, `ssc2.pkg`,
`stata.toc`, `README.md`, `site/about.html` and `site/index.html`.
`tests/test_sources.py` fails the build if a literal version creeps back
into a source file, or if an undefined token is used.

**`CITATION.cff` is the exception and must never contain a token.** The
CFF 1.2.0 schema requires `date-released` to be a literal `YYYY-MM-DD`,
and GitHub validates the default branch's copy in order to render the
citation widget — a placeholder there would show an error on the
repository page. It keeps real values everywhere and
`tools/citation.py` rewrites its two release fields by field
substitution: once into the `dist` tree at build time, and once into the
pull request that updates `main`. `tests/test_sources.py` enforces both
halves — no tokens in the file, and `date-released` parseable as a real
date.

The rendering pattern is `@[A-Z][A-Z0-9_]*@`. It deliberately does not
match the `@@DATA-START@@` / `@@DATA-END@@` markers that
`site/build_data.py` relies on in `site/index.html`. **Do not widen it.**

## Building a release tree locally

```bash
python3 tools/build_release.py --out /tmp/ssc2-dist --version 9.9.9
find /tmp/ssc2-dist -type f | sort
```

Seven files: `stata.toc`, `ssc2.pkg`, `ado/ssc2.ado`, `sthlp/ssc2.sthlp`,
`README.md`, `LICENSE` and `CITATION.cff`. That set is also exactly what
a Zenodo deposition would archive.

Nothing is pushed; this only shows what a release would contain. You can
point Stata at it directly to test:

```stata
net install ssc2, all replace from("/tmp/ssc2-dist")
which ssc2
```

## Caveats

- `raw.githubusercontent.com` caches for roughly five minutes. Right
  after a release, `net install` may briefly serve the previous content
  of a moved `latest` tag. A version tag is immutable and unaffected.
- The workflow needs **Settings → Actions → General → Workflow
  permissions = Read and write**, with **"Allow GitHub Actions to create
  and approve pull requests"** ticked (the citation PR needs it), and
  **Settings → Pages → Source = GitHub Actions**.
- If `main` is protected, nothing breaks: the workflow pushes only to
  `dist`, to tags, and to `citation/*` branches, and reaches `main`
  solely through a pull request you merge. If *tags* are protected, add
  an exception for the `github-actions[bot]` identity.
- If the citation pull request step fails, the release itself is already
  done — the tag, the GitHub release and the `latest` tag all exist. Only
  the `main`-side metadata is missing, and you can apply it by hand:
  `python3 tools/citation.py --version X.Y.Z --in-place CITATION.cff`.
- Deleting a release means deleting both the GitHub release and its tag.
  If it was the newest stable one, re-point `latest` by hand:
  `git push -f origin <previous-tag>^{}:refs/tags/latest`.
````

- [ ] **Step 2: Link the runbook from the README**

In `README.md`, insert this section immediately before the
`## Current Author(s)` section:

```markdown
## Releasing

Releases are cut by the **release** GitHub Actions workflow, which
renders the version placeholders, publishes the installable tree on the
`dist` branch, tags it, and redeploys the website. See
[`docs/RELEASING.md`](docs/RELEASING.md).
```

- [ ] **Step 3: Verify the whole suite still passes**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS — every test ok.

- [ ] **Step 4: Verify nothing hardcodes a version or names the fork**

Run:

```bash
grep -rn "ian-joyce\|TODO AT MERGE" \
  README.md ssc2.pkg stata.toc ado sthlp site docs tools \
  && echo "FOUND — fix before committing" || echo "clean"
grep -rn "stata-ssc2/main" README.md site docs \
  && echo "FOUND — fix before committing" || echo "clean"
```

Expected: `clean` twice.

- [ ] **Step 5: Commit**

```bash
git add docs/RELEASING.md README.md
git commit -m "docs: add release runbook"
```

---

## Post-implementation: cutting the first release

Not part of the plan's tasks — these are the manual steps the maintainer
takes once the branch is merged to `main`.

1. Confirm **Settings → Actions → General → Workflow permissions** is
   *Read and write*, with *"Allow GitHub Actions to create and approve
   pull requests"* ticked.
2. Confirm **Settings → Pages → Source** is *GitHub Actions*.
3. **Actions → release → Run workflow**, with `version` = `2.2.2`,
   `bump` = `patch`, `prerelease` unticked.
4. When it finishes, verify from Stata:

   ```stata
   net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/v2.2.2/")
   which ssc2
   ```

   Expected: the `*!` header reads `version 2.2.2` followed by the
   release date, with no `@` characters.
5. Repeat with `latest` in place of `v2.2.2` and confirm the same result.
6. Review and merge the `chore: citation metadata for v2.2.2` pull
   request, then delete its `citation/v2.2.2` branch. Check the repository
   page afterwards: the "Cite this repository" widget should show 2.2.2
   and no validation error.
7. Confirm the release tarball is what you want archived, before turning
   Zenodo on:

   ```bash
   gh release download v2.2.2 --archive=tar.gz --output /tmp/ssc2-v2.2.2.tar.gz
   tar tzf /tmp/ssc2-v2.2.2.tar.gz
   tar xzf /tmp/ssc2-v2.2.2.tar.gz -O --wildcards '*/CITATION.cff'
   ```

   Expected: the rendered package tree only — no `site/`, `tools/` or
   `tests/` — and a `CITATION.cff` reading `version: 2.2.2`. See the
   Zenodo section of `docs/RELEASING.md` for the trade-off.
8. Delete the stale zip artifacts still staged for deletion in the
   working tree (`ssc2-site*.zip`, `ssc2-update-v*.zip`) — GitHub now
   generates source archives for each tag automatically.
````
