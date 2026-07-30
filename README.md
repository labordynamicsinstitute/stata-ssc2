# ssc2

## Overview

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

```stata
* ssc2 may be installed directly from GitHub
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/main")
```

```stata
* or a specific release, e.g. v1.0.0
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/v1.0.0/")
```

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

## Current Author(s)

- Lars Vilhuber
