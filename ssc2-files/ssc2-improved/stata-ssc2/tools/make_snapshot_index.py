#!/usr/bin/env python3
"""
Build a machine-readable index of SSC-mirror snapshots.

Writes snapshots.csv (one row per snapshot date). Intended to be run by a
scheduled GitHub Action and committed to this repository (or served via
GitHub Pages), so that a future `ssc2 snapshots` / `ssc2 versions`
subcommand can fetch it with Stata's -copy- or -import delimited-.

Uses `git ls-remote --tags`, which needs no authentication and is not
subject to the GitHub REST API rate limits.

Future extension for `ssc2 versions <pkg>`: for each snapshot date, fetch
fmwww.bc.edu/repec/bocode/<l>/<pkg>.pkg and record its Distribution-Date
and the starbang version line of the main ado file. That is expensive
across ~1,600 tags, so it should be done incrementally (only new tags per
run) and cached in a per-package CSV.
"""
import csv
import re
import subprocess
import sys

MIRROR = "https://github.com/labordynamicsinstitute/ssc-mirror.git"
DATE_TAG = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def list_snapshot_tags(remote: str = MIRROR) -> list[str]:
    out = subprocess.run(
        ["git", "ls-remote", "--tags", remote],
        check=True, capture_output=True, text=True,
    ).stdout
    tags = set()
    for line in out.splitlines():
        ref = line.split("refs/tags/")[-1].removesuffix("^{}")
        if DATE_TAG.match(ref):
            tags.add(ref)
    return sorted(tags)


def main() -> int:
    tags = list_snapshot_tags()
    with open("snapshots.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date"])
        for t in tags:
            w.writerow([t])
    print(f"wrote snapshots.csv with {len(tags)} snapshot dates "
          f"({tags[0]} .. {tags[-1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
