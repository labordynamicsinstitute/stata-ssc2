# ssc2

Install Stata packages from **date-based snapshots** of the SSC archive,
mirrored at <https://github.com/labordynamicsinstitute/ssc-mirror>.
Backward compatible with `ssc`.

## Description

`ssc2` is a drop-in replacement for the system-provided `ssc` command.
It adds:

- **`date()`** — install/describe/type/copy a package *as of a given date*
  (`YYYY-MM-DD`), or `date(latest)` for the most recent mirrored state.
- **`from()`** — point at an alternative clone of the snapshot mirror.

Where nothing snapshot-specific is requested, `ssc2` delegates to the
official `ssc` command (which ships with every Stata installation), so it
behaves as a strict superset of `ssc` and automatically inherits upstream
behavior. The subcommands `new`, `hot`, and `uninstall` are always
delegated.

Snapshots are date-stamped git tags in the mirror repository. Daily
snapshots exist from **2021-12-21** onward (with occasional gaps, see the
mirror's [ERRATA](https://github.com/labordynamicsinstitute/ssc-mirror/blob/main/ERRATA.md));
three earlier snapshots exist (2017-08-10, 2021-04-15, 2021-08-10). Type
`ssc2 snapshots` for details.

### Overriding the mirror location

The mirror may move to a different GitHub organization. The base URL is
resolved in this order of precedence:

1. the `from()` option;
2. the Stata global `SSC2_MIRROR` (e.g. `global SSC2_MIRROR "https://..."`,
   or populated from the environment via `global SSC2_MIRROR : environment SSC2_MIRROR`);
3. the environment variable `SSC2_MIRROR` (read automatically);
4. the built-in default.

`SSC2_MIRROR_API` (global or environment variable) analogously overrides
the GitHub API endpoint used only to produce better error messages when a
snapshot lookup fails.

### Main programs

- `ssc2`

## Installation

Released versions live on the `dist` branch and are tagged. The `latest`
tag always points at the newest stable release, never at a pre-release.

```stata
* the current stable release
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/latest/")
```

To pin an exact version — which is what you want in a replication
package — use the release tag instead of `latest`:

```stata
* a specific release
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/@VERSION_TAG@/")
```

> The tag above is substituted at release time. On the `main` branch you
> will see an unrendered placeholder there instead — `main` is the
> template, not an installable version. See
> [Releases](https://github.com/labordynamicsinstitute/stata-ssc2/releases)
> for every tag you can substitute. Do **not** install from `main`.

## Example

```stata
// install the package version that was current on 2022-01-07
ssc2 install reghdfe, date(2022-01-07)
which reghdfe    // -> version 5.7.3 13nov2019

// without date(), ssc2 delegates to the official ssc command
ssc2 install reghdfe, replace
which reghdfe    // -> current SSC version

// most recent mirrored state
ssc2 install reghdfe, date(latest) replace

// everything else passes through to ssc
ssc2 hot, n(5)
```

## Why?

Reproducibility. Inspired by the R ecosystem's snapshot functionality
(MRAN/checkpoint, Posit Package Manager): a replication package can pin
the SSC package versions that were current when the analysis was run.

## Testing

Run [`test.do`](test.do) in Stata. It exercises dated installs,
delegation to `ssc`, `date(latest)`, `copy`/`type` with dates, and error
handling.

## Website

The project website is at <https://labordynamicsinstitute.github.io/stata-ssc2/>,
built with Jekyll using the
[just-the-docs](https://just-the-docs.com/) theme.

To preview it locally, use [`tools/serve_site.sh`](tools/serve_site.sh),
which runs Jekyll in a container built from
[`site/Dockerfile`](site/Dockerfile) with the same Ruby and gems as the
**site** workflow. Docker or Podman is the only prerequisite.

```bash
tools/serve_site.sh          # live-reloading preview, then open the URL it prints
tools/serve_site.sh build    # full CI replay: generators + jekyll build into site/_site
tools/serve_site.sh test     # build, then run the checks in tests/test_site.py
```

The preview is served under the site's `baseurl`, at
<http://localhost:4000/stata-ssc2/> rather than at `localhost:4000` —
deliberately, because it is how GitHub project Pages serves it. Serving
at the root would hide broken asset paths, which is precisely the bug
this harness was built to catch.

## Releasing

Releases are cut by the **release** GitHub Actions workflow, which
renders the version placeholders, publishes the installable tree on the
`dist` branch, tags it, and redeploys the website. See
[`docs/RELEASING.md`](docs/RELEASING.md).

## Current Author(s)

- Lars Vilhuber
- Ian Joyce and contributors
