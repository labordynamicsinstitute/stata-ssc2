# ssc2

## Overview
Allow for installation of snapshot packages. Backward compatible.

## Description

This is a drop-in replacement for the system-provided {cmd:ssc} command, allowing for installation of date-specific snapshots of packages.
It adds a new option "{cmd:date()}" that allows to pick a specific snapshot of SSC as of that date.
All other options are passed through.

### Main programs

- `ssc2`

## Installation

```stata
* ssc2 may be installed directly from GitHub
net install ssc2, all replace from("https://raw.githubusercontent.com/aeadataeditor/ssc-mirror-stata/master")
```

```stata
* or a specific version, e.g. v1.0.0
net install ssc2, all replace from("https://raw.githubusercontent.com/aeadataeditor/ssc-mirror-stata/v1.0.0/")
```

## Why?

Inspired by the R `snapshot` functionality.

## Current Author(s)

 - Lars Vilhuber