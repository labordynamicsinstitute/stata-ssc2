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
