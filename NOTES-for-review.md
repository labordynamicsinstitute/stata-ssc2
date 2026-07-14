# ssc2 — notes for review, round 2 (2026-07-08)

## Changes in response to review

1. **Structure cleanup**: removed `tools/` and `snapshots.csv`; the fork
   now mirrors the pre-fork directory structure exactly (`ado/`, `sthlp/`,
   root metadata files). This file is the only addition and can be dropped
   at merge time (its content belongs in the PR description).
2. **Test suite rewritten around reghdfe** (`test.do`): generic install
   with fallback onto ssc; dated install validated against ground truth
   (snapshot 2022-01-07 carries reghdfe *! version 5.7.3 13nov2019,
   verified by reading the mirrored ado file); date normalization;
   date(latest); URL-override precedence; pass-throughs (hot, new,
   describe, uninstall); dated type/copy; error handling. Installs ssc2
   via `net install ... from()` as requested (local path by default, fork
   URL in a comment).
3. **URL override**: precedence is from() option > global SSC2_MIRROR >
   environment variable SSC2_MIRROR > built-in default, implemented in
   one place (ResolveSnapshot). SSC2_MIRROR_API analogously for the API
   endpoint. Ready for the move away from labordynamicsinstitute.
4. **GitHub API pre-check, as suggested — but on failure only.** When a
   dated `net from` fails, ssc2 makes one `copy` call to
   `<api>/git/ref/tags/<date>`: success means the tag exists (so the
   problem is network/layout); a clean file-not-found means the snapshot
   genuinely does not exist. Anything else is treated as inconclusive.
   Reason for the caution: unauthenticated GitHub API calls are limited
   to 60/hour per IP and return HTTP 403 over the limit (observed while
   developing this). Putting the check on the happy path would burn that
   budget and add latency to every dated install; as a failure diagnostic
   it costs nothing when things work.

## Data finding: an undocumented gap

Computing the complete exception set from the mirror's 1,659 date tags
(as of 2026-07-08):

- daily era begins **2021-12-21** (confirming the review comment; the
  README/help previously said 2021-12-23 and have been corrected)
- pre-daily inclusions: 2017-08-10, 2021-04-15, 2021-08-10
- missing dates since 2021-12-21: **2021-12-22, 2024-08-11,
  2026-03-08, 2026-03-09, 2026-03-10**

**2021-12-22 and 2024-08-11 are not in ERRATA.md**, which lists only the
2026-03 gap. Worth adding.

## Proposal: machine-readable exceptions file

Suggested: a small `exceptions.csv` maintained in the **ssc-mirror**
repository (main branch), updated by the mirror workflow, so it can
never go stale relative to the tags. ssc2 could then fetch it (one
`copy` of a ~10-line file, cacheable) to validate dates offline of the
API and to power `ssc2 snapshots`. Suggested format, with today's
complete content:

    type,date,note
    daily_start,2021-12-21,daily snapshots begin
    include,2017-08-10,pre-daily snapshot
    include,2021-04-15,pre-daily snapshot
    include,2021-08-10,pre-daily snapshot
    missing,2021-12-22,workflow failure
    missing,2024-08-11,workflow failure
    missing,2026-03-08,workflow failure
    missing,2026-03-09,workflow failure
    missing,2026-03-10,workflow failure

ERRATA.md could be regenerated *from* this file (human-readable rendering
of the machine-readable source), rather than maintained in parallel.

## Still open from round 1

- Rename to ssctm (issue #1) — mechanical once decided.
- Web page tool — awaiting choice; Quarto + GitHub Pages recommended.
- Help-file provenance (derived from StataCorp's ssc help) before any
  Stata Journal submission.
- Minimum Stata version (currently declared 14 on https grounds) — to be
  confirmed empirically.
