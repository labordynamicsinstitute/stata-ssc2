---
layout: default
title: About
nav_order: 2
---

# About

`ssc2` installs Stata packages from **date-based snapshots** of the SSC archive,
mirrored at [ssc-mirror](https://github.com/labordynamicsinstitute/ssc-mirror).
It is a drop-in replacement for the built-in `ssc` command.

## What it does

The SSC archive contains only the most recent version of each user-written Stata
package. When an author uploads an update, the previous version is no longer
available. This creates challenges for reproducibility: researchers seeking to
replicate older analyses may be unable to obtain the package versions originally
used.

`ssc2` addresses this limitation by adding a `date()` option to the standard
`ssc` workflow. It serves packages as they existed on a given date using daily
snapshots stored in the
[ssc-mirror](https://github.com/labordynamicsinstitute/ssc-mirror) repository,
following the same general approach that dated CRAN snapshots introduced for the
R ecosystem (MRAN/checkpoint, Posit Package Manager).

When no date is requested, `ssc2` delegates to the official `ssc` command,
ensuring that existing workflows continue to function unchanged. The subcommands
`new`, `hot`, and `uninstall` are always delegated.

Snapshots are date-stamped git tags in the mirror repository. Daily snapshots
exist from **2021-12-21** onward (with occasional gaps; see the mirror's
[ERRATA](https://github.com/labordynamicsinstitute/ssc-mirror/blob/main/ERRATA.md));
three earlier snapshots exist (2017-08-10, 2021-04-15, 2021-08-10).

## Installation

Released versions live on the `dist` branch and are tagged. The `latest`
tag always points at the newest stable release, never at a pre-release.

```stata
* The current stable release
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/latest/")
```

To pin an exact version in a replication package, use the release tag
instead of `latest`:

```stata
* A specific release
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/@VERSION_TAG@/")
```

## Quick example

```stata
// Install the version of reghdfe that was current on 7 January 2022
ssc2 install reghdfe, date(2022-01-07)
which reghdfe    // -> version 5.7.3 13nov2019

// Without date(), identical to -ssc install-
ssc2 install reghdfe, replace

// Most recent mirrored state
ssc2 install reghdfe, date(latest) replace

// Everything else passes through to ssc
ssc2 hot, n(5)
```

The [snapshot picker](.) on the home page writes these commands for you.

## Overriding the mirror location

The mirror may move to a different GitHub organization. The base URL is resolved
in this order of precedence:

1. the `from()` option;
2. the Stata global `SSC2_MIRROR` (e.g. `global SSC2_MIRROR "https://..."`, or
   populated from the environment via
   `global SSC2_MIRROR : environment SSC2_MIRROR`);
3. the environment variable `SSC2_MIRROR` (read automatically);
4. the built-in default.

`SSC2_MIRROR_API` (global or environment variable) analogously overrides the
GitHub API endpoint used only to produce better error messages when a snapshot
lookup fails.

See the [Reference](reference.html) page for full details.

## Testing

Run [`test.do`](https://github.com/labordynamicsinstitute/stata-ssc2/blob/main/test.do)
in Stata. It exercises dated installs, delegation to `ssc`, `date(latest)`,
`copy`/`type` with dates, and error handling.

## Links

- Source: [github.com/labordynamicsinstitute/stata-ssc2](https://github.com/labordynamicsinstitute/stata-ssc2)
- Snapshot mirror: [github.com/labordynamicsinstitute/ssc-mirror](https://github.com/labordynamicsinstitute/ssc-mirror)
- Issues and support: [issue tracker](https://github.com/labordynamicsinstitute/stata-ssc2/issues)
- License: see [LICENSE](https://github.com/labordynamicsinstitute/stata-ssc2/blob/main/LICENSE)

## Authors

Lars Vilhuber (Labor Dynamics Institute, Cornell University),
Ian Joyce (AEA Data Replicator Intern, University of Notre Dame), and contributors.

## Citation

A software article is in preparation; until it appears, please cite the GitHub
repository.
