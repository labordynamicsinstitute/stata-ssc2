#!/usr/bin/env python3
"""Render documentation placeholders in place.

Unlike tools/build_release.py, which renders the *next* version into a
fresh tree, this renders the *current* released version into files that
are about to be published as-is -- the website. It edits the given files
in place, so run it only on a throwaway checkout (a CI working copy),
never on a working tree you intend to commit.

Usage:
    python3 tools/render_docs.py README.md site/about.md site/index.html
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
