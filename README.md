# ssc2

## Overview

Allow for installation of SSC snapshot packages from [https://github.com/labordynamicsinstitute/ssc-mirror/](https://github.com/labordynamicsinstitute/ssc-mirror/). Backward compatible with `ssc`.

## Description

This is a drop-in replacement for the system-provided {cmd:ssc} command, allowing for installation of date-specific snapshots of packages.
It adds a new option "{cmd:date()}" that allows to pick a specific snapshot of SSC as of that date.
All other options are passed through.

### Main programs

- `ssc2`

## Installation

```stata
* ssc2 may be installed directly from GitHub
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/master")
```

```stata
* or a specific version, e.g. v1.0.0
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/stata-ssc2/v1.0.0/")
```
## Example

Example run on 2023-01-29:

```stata
// testing
global github "https://raw.githubusercontent.com"
net install ssc2, all replace from("$github/labordynamicsinstitute/stata-ssc2/master")
// install a specific version
ssc2 install cmp, date(2022-01-07)
which cmp
ssc uninstall cmp
// install using standard command
ssc install cmp
which cmp
ssc uninstall cmp
// show that the redirect also works
ssc2 install cmp
which cmp
```

This yields

```stata

. do test.do 

. // testing
. global github "https://raw.githubusercontent.com"
. net install ssc2, all replace from("$github/labordy
> namicsinstitute/stata-ssc2/master")
checking ssc2 consistency and verifying not already installed...
installing into /home/statauser/ado/plus/...
installation complete.

. ssc2 install cmp, date(2022-01-07)
snapshot selected: 2022-01-07
installing from  https://raw.githubusercontent.com/labordynamicsinstitute/ssc-m
> irror/2022-01-07/fmwww.bc.edu/repec/bocode/...
checking cmp consistency and verifying not already installed...
installing into /home/statauser/ado/plus/...
installation complete.

. which cmp
/home/statauser/ado/plus/c/cmp.ado
*! cmp 8.6.7 5 January 2022
*! Copyright (C) 2007-22 David Roodman 
*! Version history at bottom

. ssc uninstall cmp

package cmp from https://raw.githubusercontent.com/labordynamicsinstitute/ssc-m
> irror/2022-01-07/fmwww.bc.edu/repec/bocode/c
      'CMP': module to implement conditional (recursive) mixed process estimato
> r

(package uninstalled)

. ssc install cmp
checking cmp consistency and verifying not already installed...
installing into /home/statauser/ado/plus/...
installation complete.

. which cmp
/home/statauser/ado/plus/c/cmp.ado
*! cmp 8.7.5 3 July 2023
*! Copyright (C) 2007-23 David Roodman 

. ssc uninstall cmp

package cmp from http://fmwww.bc.edu/repec/bocode/c
      'CMP': module to implement conditional (recursive) mixed process estimato
> r

(package uninstalled)

. ssc2 install cmp
installing from  http://fmwww.bc.edu/repec/bocode/...
checking cmp consistency and verifying not already installed...
installing into /home/statauser/ado/plus/...
installation complete.

. which cmp
/home/statauser/ado/plus/c/cmp.ado
*! cmp 8.7.5 3 July 2023
*! Copyright (C) 2007-23 David Roodman 

. 
end of do-file
```

## Why?

Inspired by the R `snapshot` functionality.

## Current Author(s)

 - Lars Vilhuber
