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
