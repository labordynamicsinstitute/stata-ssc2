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
