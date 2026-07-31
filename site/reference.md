---
layout: default
title: Reference
nav_order: 3
---

# Reference

Install and uninstall packages from SSC, including from date-based snapshots of an SSC mirror. Web rendering of the Stata help file (`help ssc2`).
{: .manhead}

## Syntax
{: #syntax}

Describe a specified package at SSC mirror
{: .hang}

`ssc2` `describe` \{ *pkgname* \| *letter* \} \[`,` `saving(`*`filename`*\[`, replace`\]`)` `date(datespec)` `from(url)`\]
{: .syn}

Install a specified package from SSC mirror
{: .hang}

`ssc2` `install` *pkgname* \[`,` `all` `replace` `update` `replaceall` `date(datespec)` `from(url)`\]
{: .syn}

Type a specific file stored at SSC mirror
{: .hang}

`ssc2` `type` *`filename`* \[`, asis` `date(datespec)` `from(url)`\]
{: .syn}

Copy a specific file from SSC mirror to your computer
{: .hang}

`ssc2` `copy` *`filename`* \[`,` `plus` `personal` `replace` `public` `binary` `date(datespec)` `from(url)`\]
{: .syn}

where *letter* in `ssc2 describe` is `a`-`z` or `_`, and *datespec* is a date in **YYYY-MM-DD** format or the word **latest**.
{: .syn}

## Links to PDF documentation
{: #linkspdf}

Quick start

Remarks and examples

The above sections are not included in this help file.

## Command overview
{: #overview}

`ssc2 describe` *pkgname* describes, but does not install, the specified package. Use `search` to find packages; see \[R\] `search`. If you know the package name but do not know the exact spelling, type `ssc2 describe` followed by one letter, `a`-`z` or `_` (underscore), to list all the packages starting with that letter.
{: .hang}

`ssc2 install` *pkgname* installs the specified package. You do not have to describe a package before installing it. (You may also install a package by using `net` `install`; see \[R\] `net`.)
{: .hang}

`ssc2 uninstall` *pkgname* removes the previously installed package from your computer. It does not matter how the package was installed. (`ssc2 uninstall` is a synonym for `ado uninstall`, so either may be used to uninstall any package.)
{: .hang}

`ssc2 type` *`filename`* types a specific file stored at ssc2. `ssc2 cat` is a synonym for `ssc2 type`, which may appeal to those familiar with Unix.
{: .hang}

`ssc2 copy` *filename* copies a specific file stored at ssc2 to your computer. By default, the file is copied to the current directory, but you can use options to change this. `ssc2 copy` is a rarely used alternative to `ssc2 install` ...`, all`. `ssc2 cp` is a synonym for `ssc2 copy`.
{: .hang}

## Options for use with ssc2 new
{: #options_ssc2_new}

`saving(`*`filename`*\[`, replace`\]`)` specifies that the "what's new" summary be saved in *filename*. If *filename* is specified without a suffix, *filename*`.smcl` is assumed. If `saving()` is not specified, `saving(ssc2_result.smcl)` is assumed.
{: .hang}

`type` specifies that the "what's new" results be displayed in the Results window rather than in the Viewer.
{: .hang}

## Options for use with ssc2 hot
{: #options_ssc2_hot}

`n(`*#*`)` specifies the number of packages to list; `n(10)` is the default. Specify `n(.)` to list all packages in order of popularity.
{: .hang}

`author(`*name*`)` lists the 10 most popular packages by the specified author. If `n(`*#*`)` is also specified, the top *#* packages are listed.
{: .hang}

## Options for selecting a snapshot (describe, install, type, copy)
{: #options_snapshot}

`date(datespec)` selects the snapshot of the SSC archive as of the specified date. *datespec* is either a date in **YYYY-MM-DD** format (for example, `date(2022-01-07)`) or **latest**, which uses the most recently mirrored state of the archive. With `ssc2 install`, how an already-installed copy of the same package is handled is governed by `replace`, `update`, and `replaceall`; see [Options for use with ssc2 install](#options_ssc2_install). If no snapshot exists for the specified date, an error message points to the [list of available snapshot dates](https://github.com/labordynamicsinstitute/ssc-mirror/tags).
{: .hang}

`from(url)` specifies the base URL of the snapshot mirror. If `from()` is not specified, the URL is taken from the Stata global `SSC2_MIRROR` if that is set; otherwise from the environment variable `SSC2_MIRROR` if that is set; otherwise the built-in default `https://raw.githubusercontent.com/labordynamicsinstitute/ssc-mirror` is used. The overrides exist because the mirror may move to a different host; they also let you point at your own clone, which must use the same layout (*url*`/`*ref*`/fmwww.bc.edu/repec/bocode/`). The analogous `SSC2_MIRROR_API` global or environment variable overrides the API endpoint used only for diagnosing failed snapshot lookups.
{: .hang}

## Option for use with ssc2 describe
{: #option_ssc2_describe}

`saving(`*`filename`*\[`, replace`\]`)` specifies that, in addition to the description's being displayed on your screen, it be saved in the specified file.
{: .hang}

If *filename* is specified without an extension, `.smcl` will be assumed, and the file will be saved as a `SMCL` file.
{: .hang}

If *filename* is specified with an extension, no default extension is added. If the extension is `.log`, the file will be stored as a text file.
{: .hang}

If `replace` is specified, *filename* is replaced if it already exists.
{: .hang}

## Options for use with ssc2 install
{: #options_ssc2_install}

`all` specifies that any ancillary files associated with the package be downloaded to your current directory, in addition to the program and help files being installed. Ancillary files are files that do not end in `.ado` or `.sthlp` and typically contain datasets or examples of the use of the new command.
{: .hang}

You can find out which files are associated with the package by typing `ssc2 describe` *pkgname* before or after installing. If you install without using the `all` option and then want the ancillary files, you can `ssc2 install` again.
{: .hang}

`replace` specifies that any files being downloaded that already exist on your computer be replaced by the downloaded files. If `replace` is not specified and any files already exist, none of the files from the package is downloaded or installed.
{: .hang}

It is better not to specify the `replace` option and wait to see if there is a problem. If there is a problem, it is usually better to uninstall the old package by using `ssc2 uninstall` or `ado uninstall` (which are, in fact, the same command).
{: .hang}

When a snapshot is requested with `date()` or `from()`, `ssc2 install` compares the requested snapshot with any installed copy of the same package, using the snapshot date recorded in the installed copy's source; a copy installed from SSC directly carries no snapshot date and cannot be compared. The behavior is then: without any of the options below, an existing installation is refused, as with official `ssc`; `replace` reinstalls the *same* snapshot only; `update` moves to a *newer* snapshot only (an older snapshot is a no-op); `replaceall` replaces *any* installed version, downgrades included. Because repeated dated installs would otherwise accumulate multiple tracker entries (each snapshot is a distinct source URL), all three options remove the superseded copies before installing. Without `date()` or `from()`, `ssc2 install` delegates to official `ssc`; if `replace` is specified and a snapshot-installed copy of the package exists, that copy is retired first (official `replace` means replacing whatever is installed, and retiring the snapshot entry keeps the package singly tracked).

`update` (only with `date()` or `from()`) installs the requested snapshot only if it is newer than every installed copy of the package. If the installed copy is the same age or newer, nothing is done.
{: .hang}

`replaceall` (only with `date()` or `from()`) replaces any installed version of the package without comparing versions; this is the option to use for downgrading, and the only applicable one with `date(latest)`.
{: .hang}

## Option for use with ssc2 type
{: #option_ssc2_type}

`asis` affects how files with the suffixes `.smcl` and `.sthlp` are displayed. The default is to interpret SMCL directives the file might contain. `asis` specifies that the file be displayed in raw, uninterpreted form.
{: .hang}

## Options for use with ssc2 copy
{: #options_ssc2_copy}

`plus` specifies that the file be copied to the `PLUS` directory, the directory where community-contributed additions are installed. Typing `sysdir` will display the identity of the `PLUS` directory on your computer.
{: .hang}

`personal` specifies that the file be copied to your `PERSONAL` directory as reported by `sysdir`.
{: .hang}

If neither `plus` nor `personal` is specified, the default is to copy the file to the current directory.
{: .hang}

`replace` specifies that, if the file already exists on your computer, the new file replace it.
{: .hang}

`public` specifies that the new file be made readable by everyone; otherwise, the file will be created according to the default permission you have set with your operating system.
{: .hang}

`binary` specifies that the file being copied is a binary file and that it is to be copied as is. The default is to assume that the file is a text file and change the end-of-line characters to those appropriate for your computer/operating system.
{: .hang}

## Remarks
{: #remarks}

Users can add new features to Stata, and some users choose to make new features that they have written available to others via the web. The files that comprise a new feature are called a package, and a package usually consists of one or more ado-files and help files. The `net` command makes it reasonably easy to install and uninstall packages regardless of where they are on the web. One site, the ssc2, has become particularly popular as a repository for additions to Stata. Command `ssc2` is an easier to use version of `net` designed especially for the ssc2.

Many packages are available at the ssc2. Packages are named, such as **oaxaca**, **estout**, or **egenmore**. At ssc2, capitalization is not significant, so **Oaxaca**, **ESTOUT**, and **EGENmore** are ways of writing the same package names.

When you type

`. ssc2 install oaxaca`

the files associated with the package are downloaded and installed on your computer. Package names usually correspond to the names of the commands being added to Stata, so one would expect that installing the package **oaxaca** will add command `oaxaca` to Stata on your computer, and expect that typing `help oaxaca` will provide the documentation. That is the situation here, but that is not always so. Before or after installing a package, type `ssc2 describe` *pkgname* to obtain the details.

## Examples
{: #examples}

Describe most recently added or updated packages at ssc2

`. ssc2 new`
{: .syn}

Describe the most popular packages at ssc2

`. ssc2 hot`
{: .syn}

Describe the package `oaxaca`

`. ssc2 describe oaxaca`
{: .syn}

Describe the package `oaxaca` and save the description to the file `oaxaca.log`

`. ssc2 describe oaxaca, saving(oaxaca.log)`
{: .syn}

List all packages, along with a brief description, that begin with the letter `o`

`. ssc2 describe o`
{: .syn}

Same as above, but also save the listing to the file `o.index`

`. ssc2 describe o, saving(o.index)`
{: .syn}

Install package `oaxaca`

`. ssc2 install oaxaca`
{: .syn}

Uninstall previously installed package `oaxaca`

`. ssc2 uninstall oaxaca`
{: .syn}

Type file `whitetst.hlp` that is stored at ssc2

`. ssc2 type whitetst.hlp`
{: .syn}

Copy file `whitetst.ado` from ssc2 to your computer

`. ssc2 copy whitetst.ado`
{: .syn}


Generated automatically from `sthlp/ssc2.sthlp` on 2026-07-30. The in-Stata
help file is the authoritative version.
{: .gennote}
