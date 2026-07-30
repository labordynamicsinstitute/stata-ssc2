#!/usr/bin/env python3
"""
build_reference.py -- translate a Stata help file (SMCL) into the site's
Reference page.

Usage:  python3 site/build_reference.py sthlp/ssc2.sthlp site/reference.html

Best-effort converter covering the SMCL directives actually used in this
project's help file (titles, paragraph modes, cmd/opt/it/bf inline
markup, help/browse links, p2col header, hline, markers). Unknown
directives degrade gracefully to their inner text, so an unhandled tag
can never break the page -- it just renders unstyled. Run by CI on every
build so the Reference page always matches sthlp/ssc2.sthlp.
"""
import html
import re
import sys
from datetime import date

# ---------------------------------------------------------------- inline
def inline(s: str) -> str:
    s = html.escape(s, quote=False)
    # literal braces written as {c -(} / {c )-}
    s = s.replace("{c -(}", "&#123;").replace("{c )-}", "&#125;")
    # {browse "url":text} and {browse "url"}
    s = re.sub(r'\{browse "([^"]+)":([^}]*)\}', r'<a href="\1">\2</a>', s)
    s = re.sub(r'\{browse "([^"]+)"\}', r'<a href="\1">\1</a>', s)
    # {help x} / {helpb x} / {help x:text} -> code (no Stata help on the web)
    s = re.sub(r'\{helpb? ([^}:]+):([^}]*)\}', r'<code>\2</code>', s)
    s = re.sub(r'\{helpb? ([^}]+)\}', r'<code>\1</code>', s)
    # {opt d:escribe} -> describe ; {opt date(datespec)} unchanged inside code
    s = re.sub(r'\{opt ([^}]*)\}', lambda m: f'<code>{m.group(1).replace(":","")}</code>', s)
    s = re.sub(r'\{cmdab:([^}]*)\}', lambda m: f'<code>{m.group(1).replace(":","")}</code>', s)
    for tag, out in (("cmd", "code"), ("bf", "b"), ("it", "i"), ("hi", "b"),
                     ("err", "b"), ("res", "code")):
        s = re.sub(r'\{%s:([^{}]*)\}' % tag, r'<%s>\1</%s>' % (out, out), s)
    s = re.sub(r'\{hline (\d+)\}', lambda m: "&mdash;" * max(1, int(m.group(1)) // 2), s)
    s = s.replace("{hline}", "<hr>")
    s = re.sub(r'\{marker ([^}]+)\}', r'<a id="\1"></a>', s)
    s = re.sub(r'\{p_end\}', '', s)
    s = re.sub(r'\{\.\.\.\}', '', s)
    # anything still unknown: keep inner text after any colon
    for _ in range(3):
        s = re.sub(r'\{[a-zA-Z0-9_* ]+:([^{}]*)\}', r'\1', s)
        s = re.sub(r'\{[a-zA-Z0-9_* .]*\}', '', s)
    return s


# ------------------------------------------------------------- structure
SKIP_SECTIONS = {"Description"}   # covered by the About page

def convert(smcl: str) -> str:
    out, para, mode = [], [], None
    convert.description = ""

    def flush():
        nonlocal para, mode
        text = inline(" ".join(para).strip())
        if text:
            css = {"phang": "hang", "syn": "syn"}.get(mode, "")
            out.append(f'<p class="{css}">{text}</p>' if css else f"<p>{text}</p>")
        para, mode = [], None

    skipping = False                       # inside a suppressed section?
    for raw in smcl.splitlines():
        line = raw.rstrip()
        if line.startswith("{smcl}") or line.startswith("{* "):
            continue
        # help-viewer navigation: meaningless on the web, drop entirely
        if line.lstrip().startswith(("{vieweralsosee", "{viewerjumpto")):
            continue
        if re.match(r'\{p2col', line):        # manual-style header block
            m = re.search(r'\{p2col:(.*?)\}(.*)', line)
            if m and not convert.description:  # keep the one-line description
                d = inline(m.group(2)).strip().rstrip('.')
                convert.description = re.sub(r'^(?:&mdash;|[}\s])+', '', d)
            continue                           # h1/subtitle replace the header
        if line.startswith("{p2colreset"):
            continue
        m = re.match(r'\{title:(.*)\}', line)
        if m:
            flush()
            title = m.group(1).strip()
            skipping = title in SKIP_SECTIONS  # e.g. Description: About page covers it
            if not skipping:
                out.append(f"<h2>{inline(title)}</h2>")
            continue
        if skipping:
            continue
        if not line.strip():
            flush()
            continue
        m = re.match(r'\{(pstd|phang|pmore|p \d+ \d+ \d+?)\}(.*)', line)
        if m:
            flush()
            tag = m.group(1)
            mode = "phang" if tag in ("phang", "pmore") else \
                   ("syn" if tag.startswith("p 8") or tag.startswith("p 4 6") else None)
            para.append(m.group(2))
            continue
        if "{p_end}" in line:
            para.append(line)
            flush()
            continue
        para.append(line)
    flush()
    return "\n".join(out)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reference — ssc2</title>
<style>
  :root{{--navy:#123a63;--ink:#20242a;--muted:#5c6572;--paper:#fafbfc;
    --line:#d7dde4;--accent:#1b6fae;--navy-soft:#e8eef5}}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--paper);color:var(--ink);
    font:16px/1.6 -apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
    padding:2.5rem 1.25rem 4rem}}
  main{{max-width:700px;margin:0 auto}}
  .topnav{{background:var(--navy);margin:-2.5rem -1.25rem 2.2rem;padding:0 1.25rem}}
  .nav-inner{{max-width:700px;margin:0 auto;display:flex;gap:1.4rem;align-items:center}}
  .topnav a{{color:#c8d8e8;text-decoration:none;font-size:.9rem;padding:.7rem 0}}
  .topnav a:hover{{color:#fff}}
  .topnav a.on{{color:#fff;font-weight:600;box-shadow:inset 0 -3px 0 #fff}}
  .topnav .brand{{font-family:ui-monospace,Consolas,Menlo,monospace;font-weight:700;
    font-size:1rem;color:#fff}}
  h1,h2{{font-family:Charter,Georgia,"Times New Roman",serif;color:var(--navy)}}
  h1{{font-size:1.8rem;margin-bottom:.3rem}}
  h2{{font-size:1.25rem;margin:1.8rem 0 .6rem;border-bottom:1px solid var(--line);
    padding-bottom:.25rem}}
  p{{margin:.55rem 0}}
  p.hang{{padding-left:1.6rem;text-indent:-1.6rem;margin:.65rem 0}}
  p.syn{{font-family:ui-monospace,"Cascadia Code",Consolas,Menlo,monospace;
    font-size:.88rem;background:var(--navy-soft);border-radius:6px;
    padding:.55rem .8rem;margin:.4rem 0}}
  p.manhead{{color:var(--muted);font-size:.9rem}}
  code{{font-family:ui-monospace,"Cascadia Code",Consolas,Menlo,monospace;
    font-size:.9em;color:var(--navy)}}
  a{{color:var(--accent)}}
  .gennote{{margin-top:2.5rem;font-size:.8rem;color:var(--muted);
    border-top:1px solid var(--line);padding-top:.8rem}}
</style>
</head>
<body>
<nav class="topnav"><div class="nav-inner">
  <a class="brand" href="index.html">ssc2</a>
  <a href="about.html">About</a>
  <a class="on" href="reference.html">Reference</a>
  <a href="articles.html">Articles</a>
</div></nav>
<main>
<h1>Reference</h1>
<p class="manhead">{desc}. Web rendering of the Stata help file
(<code>help ssc2</code>).</p>
{body}
<p class="gennote">Generated automatically from
<code>sthlp/ssc2.sthlp</code> on {stamp}. The in-Stata help file is the
authoritative version.</p>
</main>
</body>
</html>
"""


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "sthlp/ssc2.sthlp"
    dst = sys.argv[2] if len(sys.argv) > 2 else "site/reference.html"
    body = convert(open(src, encoding="utf-8").read())
    # quality gate: no raw SMCL may survive into the page. Failing the
    # build blocks a bad deploy and makes the problem visible in CI.
    leftovers = re.findall(r'\{[a-zA-Z][^}]*\}', body)
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
