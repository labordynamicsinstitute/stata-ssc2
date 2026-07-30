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
import sys

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
