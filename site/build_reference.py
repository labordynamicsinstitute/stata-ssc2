#!/usr/bin/env python3
"""
build_reference.py -- translate a Stata help file (SMCL) into the site's
Reference page, as Jekyll-flavoured Markdown.

Usage:  python3 site/build_reference.py sthlp/ssc2.sthlp site/reference.md

Best-effort converter covering the SMCL directives actually used in this
project's help file (titles, paragraph modes, cmd/opt/it/bf inline
markup, help/browse links, p2col header, hline, markers). Unknown
directives degrade gracefully to their inner text, so an unhandled tag
can never break the page -- it just renders unstyled. Run by CI on every
build so the Reference page always matches sthlp/ssc2.sthlp.

Why Markdown rather than HTML: the generated page reads and diffs like
prose, and kramdown (Jekyll's Markdown engine) covers everything SMCL
asks for here. The two constructs Markdown has no syntax of its own for
-- hanging-indent option paragraphs and the monospaced syntax diagrams
-- are carried by kramdown inline attribute lists (`{: .hang}` /
`{: .syn}`), which attach the same CSS classes the previous HTML
emitter used, so the rendered page is unchanged.

Text outside markup is escaped, because SMCL help text is full of
characters Markdown would otherwise eat: the `[optional]` brackets of a
syntax diagram, the `_` of `ssc2 describe _`, the `|` alternation in
`{ pkgname | letter }`. Inline code is emitted through placeholders so
escaping can never leak into a code span, where kramdown would render
the backslashes literally.
"""
import re
import sys
from datetime import date

# Characters that would otherwise be read as Markdown syntax. Braces are
# escaped so no fragment of help text can be mistaken for a kramdown
# attribute list, and the pipe so a stray alternation bar cannot start a
# table.
ESCAPE_RE = re.compile(r'([\\`*_\[\]{}|<>])')

# Each paragraph is emitted as a single line, so only its first
# character can open an unwanted block: a heading, list item, or quote.
LEADING_RE = re.compile(r'^([#+>-]|\d+\.)')

SENTINEL = "\x00"


# ---------------------------------------------------------------- inline
class Spans:
    """Holds already-converted inline fragments behind placeholders.

    Escaping runs over the whole paragraph once markup conversion is
    done, so anything already converted has to be hidden from it first.
    """

    def __init__(self):
        self.items = []

    def hold(self, markdown: str) -> str:
        self.items.append(markdown)
        return f"{SENTINEL}{len(self.items) - 1}{SENTINEL}"

    def code(self, text: str) -> str:
        # Delimit with more backticks than the content contains, padding
        # when the content itself starts or ends with one. Nothing in the
        # current help file needs this, but a later edit to the .sthlp
        # should not be able to produce a broken code span.
        ticks = "`" * (max((len(m) for m in re.findall(r'`+', text)), default=0) + 1)
        pad = " " if text.startswith("`") or text.endswith("`") else ""
        return self.hold(f"{ticks}{pad}{text}{pad}{ticks}")

    def restore(self, s: str) -> str:
        # Repeatedly, because spans nest: {it:{help filename}} holds a
        # code span inside an emphasis span, and re.sub does not rescan
        # what it just substituted in.
        while SENTINEL in s:
            s = re.sub(rf'{SENTINEL}(\d+){SENTINEL}',
                       lambda m: self.items[int(m.group(1))], s)
        return s


def inline(s: str) -> str:
    sp = Spans()
    # Literal braces, written as {c -(} / {c )-} in SMCL. Held rather
    # than substituted in place so the unknown-directive cleanup below
    # cannot mistake `{ pkgname }` for a directive and delete it.
    s = s.replace("{c -(}", sp.hold("\\{")).replace("{c )-}", sp.hold("\\}"))
    # {browse "url":text} and {browse "url"}
    s = re.sub(r'\{browse "([^"]+)":([^}]*)\}',
               lambda m: sp.hold(f"[{m.group(2)}]({m.group(1)})"), s)
    s = re.sub(r'\{browse "([^"]+)"\}', lambda m: sp.hold(f"<{m.group(1)}>"), s)
    # {help ssc2##marker:text}: a cross-reference within this same page
    s = re.sub(r'\{helpb? ssc2##([^}:]+):([^}]*)\}',
               lambda m: sp.hold(f"[{m.group(2)}](#{m.group(1)})"), s)
    # {manhelp cmd R} / {mansection R x:text} -> the manual reference in
    # plain text; there is no Stata PDF manual to link to from the web.
    s = re.sub(r'\{manhelp ([^} ]+) ([^}]+)\}',
               lambda m: sp.hold(f"\\[{m.group(2)}\\] `{m.group(1)}`"), s)
    # {help x} / {helpb x} / {help x:text} -> code (no Stata help on the web)
    s = re.sub(r'\{helpb? [^}:]+:([^}]*)\}', lambda m: sp.code(m.group(1)), s)
    s = re.sub(r'\{helpb? ([^}]+)\}', lambda m: sp.code(m.group(1)), s)
    # {opt d:escribe} -> describe ; {opt date(datespec)} unchanged inside code
    s = re.sub(r'\{opt ([^}]*)\}', lambda m: sp.code(m.group(1).replace(":", "")), s)
    s = re.sub(r'\{cmdab:([^}]*)\}', lambda m: sp.code(m.group(1).replace(":", "")), s)
    for tag, wrap in (("cmd", None), ("res", None), ("bf", "**"), ("hi", "**"),
                      ("err", "**"), ("it", "*")):
        pattern = r'\{%s:([^{}]*)\}' % tag
        if wrap is None:
            s = re.sub(pattern, lambda m: sp.code(m.group(1)), s)
        else:
            s = re.sub(pattern,
                       lambda m, w=wrap: sp.hold(f"{w}{m.group(1)}{w}")
                       if m.group(1).strip() else m.group(1), s)
    s = re.sub(r'\{hline (\d+)\}', lambda m: "—" * max(1, int(m.group(1)) // 2), s)
    s = s.replace("{hline}", sp.hold("\n\n---\n"))
    s = re.sub(r'\{marker [^}]+\}', '', s)
    s = re.sub(r'\{p_end\}', '', s)
    s = re.sub(r'\{\.\.\.\}', '', s)
    # anything still unknown: keep inner text after any colon
    for _ in range(3):
        s = re.sub(r'\{[a-zA-Z0-9_* ]+:([^{}]*)\}', r'\1', s)
        s = re.sub(r'\{[a-zA-Z0-9_* .]*\}', '', s)
    s = ESCAPE_RE.sub(r'\\\1', s).strip()
    return sp.restore(LEADING_RE.sub(r'\\\1', s))


def plain(s: str) -> str:
    """inline() with the Markdown taken back out.

    Used for the one-line description, which is quoted inside running
    prose rather than emitted as a block of its own.
    """
    return re.sub(r'[`*]', '', re.sub(r'\\(.)', r'\1', inline(s))).strip()


# ------------------------------------------------------------- structure
SKIP_SECTIONS = {"Description"}   # covered by the About page

# Paragraph mode -> kramdown inline attribute list. `hang` is the
# hanging indent used for option descriptions, `syn` the monospaced
# syntax diagram; both classes live in _sass/custom/custom.scss.
IAL = {"phang": "{: .hang}", "syn": "{: .syn}"}


def convert(smcl: str) -> str:
    out, para, mode = [], [], None
    convert.description = ""
    marker = None                          # anchors the next {title:}

    def flush():
        nonlocal para, mode
        # SMCL indents continuation lines; the indentation is layout for
        # the Stata viewer, so it collapses away here.
        text = inline(re.sub(r'\s+', ' ', " ".join(para)).strip())
        if text:
            out.append(text)
            if mode in IAL:
                out.append(IAL[mode])
            out.append("")
        para, mode = [], None

    skipping = False                       # inside a suppressed section?
    for raw in smcl.splitlines():
        line = raw.rstrip()
        if line.startswith("{smcl}") or line.startswith("{* "):
            continue
        # help-viewer navigation: meaningless on the web, drop entirely
        if line.lstrip().startswith(("{vieweralsosee", "{viewerjumpto")):
            continue
        m = re.match(r'\{marker ([^}]+)\}', line)
        if m:
            # Carried onto the heading that follows so the in-page
            # {help ssc2##marker:...} cross-references still resolve.
            marker = m.group(1)
            continue
        if re.match(r'\{p2col', line):        # manual-style header block
            _, sep, rest = line.partition("}}")
            if sep and not convert.description:  # keep the one-line description
                convert.description = plain(rest).rstrip(".")
            continue                           # h1/subtitle replace the header
        if line.startswith("{p2colreset"):
            continue
        m = re.match(r'\{title:(.*)\}', line)
        if m:
            flush()
            title = m.group(1).strip()
            skipping = title in SKIP_SECTIONS  # e.g. Description: About page covers it
            if not skipping:
                out.append(f"## {inline(title)}")
                if marker:
                    out.append(f"{{: #{marker}}}")
                out.append("")
            marker = None
            continue
        if skipping:
            continue
        if not line.strip():
            flush()
            continue
        m = re.match(r'\{(pstd|phang2?|pmore|p \d+ \d+ \d+?)\}(.*)', line)
        if m:
            flush()
            tag = m.group(1)
            mode = "phang" if tag in ("phang", "pmore") else \
                   ("syn" if tag in ("phang2",) or tag.startswith("p 8")
                    or tag.startswith("p 4 6") else None)
            para.append(m.group(2))
            continue
        if "{p_end}" in line:
            para.append(line)
            flush()
            continue
        para.append(line)
    flush()
    return "\n".join(out).strip() + "\n"


PAGE = """---
layout: default
title: Reference
nav_order: 3
---

# Reference

{desc}. Web rendering of the Stata help file (`help ssc2`).
{{: .manhead}}

{body}

Generated automatically from `sthlp/ssc2.sthlp` on {stamp}. The in-Stata
help file is the authoritative version.
{{: .gennote}}
"""


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "sthlp/ssc2.sthlp"
    dst = sys.argv[2] if len(sys.argv) > 2 else "site/reference.md"
    body = convert(open(src, encoding="utf-8").read())
    # quality gate: no raw SMCL may survive into the page. Failing the
    # build blocks a bad deploy and makes the problem visible in CI.
    # An escaped brace is literal text out of the help file and `{:`
    # opens a kramdown attribute list; neither is leftover SMCL.
    leftovers = re.findall(r'(?<!\\)\{[a-zA-Z][^}]*\}', body)
    if leftovers:
        print("ERROR: unconverted SMCL reached the output:", file=sys.stderr)
        for item in sorted(set(leftovers))[:10]:
            print("   ", item, file=sys.stderr)
        return 1
    desc = convert.description or "Stata help for the ssc2 command"
    open(dst, "w", encoding="utf-8").write(
        PAGE.format(body=body, desc=desc, stamp=date.today().isoformat()))
    print(f"wrote {dst} ({len(body)} chars of body) from {src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
