# ssc2 rewrite — notes for review (2026-07-08)

## What changed and why

1. **Fixed broken delegation.** The old code called `sscwhatsnew`,
   `ssc_whatshot`, and `sscuninstall` — internal subroutines of
   StataCorp's `ssc.ado`. Those are only in memory after `ssc` itself has
   been run in the session, and their names are undocumented internals
   that can change between Stata releases. `ssc2 new|hot|uninstall` now
   call the public `ssc` command instead.
2. **Full delegation when no snapshot is requested.** `describe`,
   `install`, `copy`, `type` now delegate to `ssc` whenever neither
   `date()` nor `from()` is given. ssc2 is a strict superset of ssc and
   inherits upstream behavior/fixes for free (e.g., `ssc describe,
   saving()` and `ssc new` options work untouched).
3. **`from()` option** (per issue #2), defaulting to the LDI mirror.
   Users can point at their own clone with the same layout.
4. **`date(latest)`** maps to the mirror's `releases` branch (verified:
   it carries the current tree; `main` does not).
5. **Fixed `copy` and `type`.** They referenced globals
   (`$ssc2prefix`, `$ssc2url`) that were never defined anywhere — both
   subcommands could not have worked. They now build the snapshot URL
   correctly and accept `date()`/`from()`.
6. **No more globals.** `$repecadr`/`$SSCMIRRORURL` polluted the user's
   global namespace; all URL logic now lives in `ResolveSnapshot`.
7. **Real date validation.** `YYYY-MM-DD` parsed with `date(...,"YMD")`
   (so `2022-1-7` normalizes to `2022-01-07`), future dates and dates
   before the first snapshot (2017-08-10) rejected, note printed for the
   sparse pre-2021-12-23 era, and a targeted error (with a link to the
   tag list) when `net from` fails on a snapshot URL.
8. **`ssc2 snapshots`** (informational) and a stub for `ssc2 versions`.
9. **Metadata fixes.** `stata.toc` had no valid `p pkgname` line (its `p`
   line would be parsed as a package named "This"); `test.do` pointed at
   a nonexistent repo path (`ssc-mirror-stata/master`); README install
   URL said `master` but the branch is `main`. All fixed; `Distribution-
   Date` bumped; version set to 2.0.0-draft pending testing.
10. **`tools/make_snapshot_index.py`** generates `snapshots.csv` from the
    mirror's tags (1,659 dates as of today) — groundwork for `ssc2
    versions` and for a CI-refreshed, Stata-fetchable index.

## Verified against the live mirror (2026-07-08)

- snapshots are git *tags* `YYYY-MM-DD`; daily since 2021-12-23; also
  2017-08-10, 2021-04-15, 2021-08-10; known gap 2026-03-08..-10 (ERRATA)
- every URL pattern the code builds returns HTTP 200 on the mirror
  (per-letter `stata.toc`, `.pkg`, `.ado`, `releases` branch), and the
  error paths return 404 as expected

## NOT yet done / needs a decision

- **Not tested in Stata.** This was developed without a Stata license in
  the loop; test.do is ready to run. Treat 2.0.0-draft as untested.
- **Rename to `ssctm`** (issue #1): trivially done with a rename +
  search/replace once decided; held off pending confirmation.
- **Default target when no date() is given** — the task email says
  "fall back to ssc" (implemented); issue #2's "default to the snapshot
  URL" could be read as defaulting to the mirror. Confirm intent.
- **Issue #2's "copy the system-level SSC command"**: StataCorp's
  ssc.ado (and its help file, from which sthlp/ssc2.sthlp derives) is
  copyrighted material; delegation avoids copying code, but the help
  file's provenance is worth cleaning up before a Stata Journal
  submission.
- **Web page tool (TBD)**: options — (a) Quarto site in docs/ rendered
  by GitHub Actions to Pages (fits the LDI toolchain, easy to include
  Stata output); (b) plain GitHub Pages from docs/ markdown (zero
  tooling); (c) Stata's `log html` / a small SMCL→HTML converter to
  publish the help file itself. Recommend (a); awaiting the "TBD tool"
  decision.
- Minimum Stata version: set to 14 on the reasoning that the mirror is
  https-only and older Statas can't fetch https; the true floor should
  be confirmed empirically.
