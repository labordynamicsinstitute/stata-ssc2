# Releasing ssc2

Releases are cut by the **release** workflow. Nothing is released by
pushing to `main`, and `main` is never rewritten by CI.

## Branch and tag layout

| Ref | What it holds |
|---|---|
| `main` | Source with `@TOKEN@` placeholders instead of version strings. Not installable. `CITATION.cff` is the one file here holding real values. |
| `dist` | Orphan branch. One commit per release, holding the rendered, installable tree. An output, never an input — **never merge it into `main`**. |
| `vX.Y.Z` | Tag on a `dist` commit. A stable release. |
| `vX.Y.Z-rc.N` | Tag on a `dist` commit. A pre-release. |
| `latest` | Floating tag, force-moved to the newest **stable** release. Never points at a pre-release. |
| `citation/vX.Y.Z` | Short-lived branch cut from `main`, holding the one-file citation update. Delete it when its pull request merges. |

## Cutting a release

1. Go to **Actions → release → Run workflow**.
2. Fill in the inputs:

   | Input | Meaning |
   |---|---|
   | `version` | Leave **blank** for normal releases. Fill in only to override, e.g. `3.0.0`. No leading `v`. |
   | `bump` | `patch` (default), `minor`, or `major`. Ignored when `version` is set. |
   | `prerelease` | Tick to cut an `-rc.N` candidate. The `latest` tag is not moved. |

3. Run it. In order, the workflow: runs the unit tests; builds the
   release tree; publishes it to the `dist` branch and pushes the tag
   (one atomic push); creates the GitHub release; for stable releases
   only, force-moves the `latest` tag; for stable releases only, opens
   the `CITATION.cff` pull request against `main`; and finally
   redeploys the website.

### What the version arithmetic does

Starting from a newest stable tag of `v2.2.2`:

| Inputs | Result |
|---|---|
| all defaults | `v2.2.3` |
| `bump: minor` | `v2.3.0` |
| `bump: major` | `v3.0.0` |
| `prerelease` ticked | `v2.2.3-rc.1` |
| `prerelease` ticked again | `v2.2.3-rc.2` |
| `prerelease` cleared after the candidates | `v2.2.3` — promotion, not a further bump |
| `version: 4.1.0` | `v4.1.0` |

The legacy `v0.5-beta` tag does not parse as a release version and is
ignored throughout.

### The first release

Run it **once** with `version` set to `2.2.2`. The newest released tag is
`v1.1.7`, but the source carried `2.2.1-draft` and the decision was to
adopt the source lineage. There is no `v2.2.1` tag and none will be
created. Every later run can leave `version` blank.

The first release's auto-generated notes (`--generate-notes`) will come
out empty or strange. `v1.1.7` lives on `main`'s history, which shares no
common history with the orphan `dist` branch the new tags live on, so
GitHub has nothing to diff the new tag against. Write that first
release's notes by hand instead of trusting `--generate-notes`.

There is currently no `latest` tag on the remote at all — only
`v0.5-beta` and `v1.1.7` exist. Until the first release runs, the
primary documented install command (the one using `latest`) is a 404.
Run the first release immediately after merging, in the same sitting,
so that window stays as short as possible.

## After the workflow runs: the CITATION.cff pull request

Stable releases leave one thing for you to do. The workflow opens a pull
request titled `chore: citation metadata for vX.Y.Z`, changing two lines
of `CITATION.cff` on `main`. Review and merge it.

It is **not** urgent and not load-bearing:

- The released tag on `dist` already carries the correct
  `CITATION.cff`, so anything reading a release — Zenodo included — is
  already right.
- `main`'s copy only drives the "Cite this repository" widget on the
  repository page. Until you merge, that widget shows the previous
  release's version.

If you skip a few, the next PR still brings `main` fully up to date; the
workflow always writes the current values rather than a diff. Close the
stale ones and delete their `citation/vX.Y.Z` branches.

Pre-releases do not open a PR at all.

### Why not merge `dist` into `main`?

Because it would destroy the repository. `dist` is an **orphan** branch:
no shared history with `main`, and its tree contains only the seven
installable files. Merging it would delete `site/`, `tools/`, `tests/`
and `.github/`, and replace the sources with their rendered copies.
`dist` is an output, never an input. The citation PR is branched from
`main`, not from `dist`.

## Zenodo archiving

The design is already Zenodo-ready; nothing in the release workflow needs
to change to enable it.

Zenodo's GitHub integration listens for the `release` webhook and
archives **the source tarball of the released tag**. Those tags live on
`dist`, so the archived tarball is the fully rendered tree:
`CITATION.cff` with the right `version` and `date-released`, `ssc2.pkg`
with the right `Distribution-Date`, and no `@TOKEN@` anywhere. Zenodo
reads `CITATION.cff` from that tarball for the deposition metadata, so
the DOI record is correct without any extra step.

To turn it on: log in to Zenodo with GitHub, flip the switch for
`labordynamicsinstitute/stata-ssc2`, then cut a release. Zenodo only sees
releases published *after* the switch is flipped.

Two things worth knowing before you enable it:

- **What gets archived is the package, not the repository.** The `dist`
  tarball holds `stata.toc`, `ssc2.pkg`, `ado/`, `sthlp/`, `README.md`,
  `LICENSE` and `CITATION.cff` — the installable artifact, with no
  `site/`, `tools/` or test suite, and no history. For a Stata package
  that is arguably the right thing to archive. If you would rather
  archive the full source, archive a tag on `main` instead, which means
  reworking where tags live.
- **Pre-releases are archived too.** Zenodo's integration does not filter
  them, so every `-rc.N` release would mint its own DOI. If that is
  unwanted, stop publishing GitHub *releases* for candidates: delete the
  "Create the GitHub release" step's `--prerelease` branch and skip
  release creation when `steps.build.outputs.prerelease == 'true'`. The
  tag on `dist` still exists and is still installable, so candidates
  remain testable — they just stop appearing in the releases list.

## Placeholders

Five tokens, defined in `tools/render.py`. `CITATION.cff` uses none of
them — see below.

| Token | Example |
|---|---|
| `@VERSION@` | `2.2.2` |
| `@VERSION_TAG@` | `v2.2.2` |
| `@DATE_STATA@` | `30jul2026` |
| `@DATE_ISO@` | `2026-07-30` |
| `@DATE_COMPACT@` | `20260730` |

They appear in `ado/ssc2.ado`, `sthlp/ssc2.sthlp`, `ssc2.pkg`,
`stata.toc`, `README.md`, `site/about.md` and `site/index.html`.
`tests/test_sources.py` fails the build if a literal version creeps back
into a source file, or if an undefined token is used.

**`CITATION.cff` is the exception and must never contain a token.** The
CFF 1.2.0 schema requires `date-released` to be a literal `YYYY-MM-DD`,
and GitHub validates the default branch's copy in order to render the
citation widget — a placeholder there would show an error on the
repository page. It keeps real values everywhere and
`tools/citation.py` rewrites its two release fields by field
substitution: once into the `dist` tree at build time, and once into the
pull request that updates `main`. `tests/test_sources.py` enforces both
halves — no tokens in the file, and `date-released` parseable as a real
date.

The rendering pattern is `@[A-Z][A-Z0-9_]*@`. It deliberately does not
match the `@@DATA-START@@` / `@@DATA-END@@` markers that
`site/build_data.py` relies on in `site/index.html`. **Do not widen it.**

## Building a release tree locally

```bash
python3 tools/build_release.py --out /tmp/ssc2-dist --version 9.9.9
find /tmp/ssc2-dist -type f | sort
```

Seven files: `stata.toc`, `ssc2.pkg`, `ado/ssc2.ado`, `sthlp/ssc2.sthlp`,
`README.md`, `LICENSE` and `CITATION.cff`. That set is also exactly what
a Zenodo deposition would archive.

Nothing is pushed; this only shows what a release would contain. You can
point Stata at it directly to test:

```stata
net install ssc2, all replace from("/tmp/ssc2-dist")
which ssc2
```

## Caveats

- `raw.githubusercontent.com` caches for roughly five minutes. Right
  after a release, `net install` may briefly serve the previous content
  of a moved `latest` tag. A version tag is immutable and unaffected.
- The workflow needs **Settings → Actions → General → Workflow
  permissions = Read and write**, with **"Allow GitHub Actions to create
  and approve pull requests"** ticked (the citation PR needs it), and
  **Settings → Pages → Source = GitHub Actions**.
- If `main` is protected with required status checks, the citation PR
  can get stuck: it is opened with `GITHUB_TOKEN`, and PRs opened by
  `GITHUB_TOKEN` do not trigger `pull_request` workflows, so `tests.yml`
  and `site.yml` never report a status on the `citation/vX.Y.Z` branch.
  If `main` requires those checks to pass, the PR cannot be merged
  without an admin override. If *tags* are protected, add an exception
  for the `github-actions[bot]` identity.
- If the citation pull request step fails, the release itself is already
  done — the tag, the GitHub release and the `latest` tag all exist. Only
  the `main`-side metadata is missing, and you can apply it by hand:
  `python3 tools/citation.py --version X.Y.Z --in-place CITATION.cff`.
  Because the `site` job has `needs: release`, that failure also skips
  the website redeploy; rerun or manually dispatch `site.yml` to publish
  it.
- Deleting a release means deleting both the GitHub release and its tag.
  If it was the newest stable one, re-point `latest` by hand:
  `git push -f origin <previous-tag>^{}:refs/tags/latest`.
- Pre-release runs still trigger a full website redeploy, even though
  nothing on the site changes: `tools/render_docs.py` resolves the
  newest **stable** tag, so a candidate's rendered docs are identical to
  what is already published. This is harmless churn. If it ever becomes
  annoying, gate the `site` job on `prerelease == 'false'`.

### If a run fails partway

- The workflow refuses to run a version whose tag is already published,
  and says so.
- If a run pushed the tag but then failed at the GitHub-release step, do
  **not** re-run the workflow — it will refuse, since the tag now
  exists. Finish it by hand instead:

  ```bash
  gh release create vX.Y.Z --generate-notes
  # add --prerelease for a candidate
  ```

  Then, for a stable release, move `latest` yourself:

  ```bash
  git push -f origin vX.Y.Z^{}:refs/tags/latest
  ```

  The `^{}` matters: it peels the annotated tag down to the commit it
  points at. Omit it and you create a tag that points at another tag
  instead of at the commit, which breaks tools that expect `latest` to
  resolve straight to a commit.
- To genuinely re-cut a version — not just finish a failed run — delete
  both the GitHub release and its tag first. With both gone, the
  workflow's tag-exists guard passes and it permits the run. Also delete
  the `citation/vX.Y.Z` branch and close its pull request if one was
  opened for the version being re-cut: otherwise the re-cut run's
  `gh pr create` fails on a branch/PR that already exists, reddening a
  run whose release actually succeeded.
