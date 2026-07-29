*! version 2.2.1-draft 29jul2026  L. Vilhuber and contributors
*! Install Stata packages from date-based snapshots of the SSC archive,
*! mirrored at https://github.com/labordynamicsinstitute/ssc-mirror
*!
*! Design:
*!   - Subcommands with no snapshot-specific behavior (new/whatsnew,
*!     hot/whatshot, uninstall) are delegated verbatim to the official
*!     -ssc- command shipped with Stata.
*!   - describe/install/copy/type are also delegated to -ssc- whenever
*!     neither date() nor from() is specified, so that ssc2 remains a
*!     strict superset of ssc and automatically inherits upstream fixes.
*!   - With date() (or from()), the mirror is used instead.
*!
*! NOTE: version 14 is declared because the mirror is served over https
*! (raw.githubusercontent.com); older Statas cannot fetch https URLs.
*! The exact minimum version should be confirmed by testing.

program define ssc2
	version 14
	gettoken cmd 0 : 0, parse(" ,")

	di as txt "" _c		/* work-around for net display problem */

	if `"`cmd'"'=="" {
		di as txt "ssc2 commands are"
		di as txt "    {cmd:ssc2 new}        (delegated to {helpb ssc})"
		di as txt "    {cmd:ssc2 hot}        (delegated to {helpb ssc})"
		di
		di as txt "    {cmd:ssc2 describe}  {it:pkgname} [, date()]"
		di as txt "    {cmd:ssc2 describe}  {it:letter}  [, date()]"
		di
		di as txt "    {cmd:ssc2 install}   {it:pkgname} [, date()]"
		di as txt "    {cmd:ssc2 uninstall} {it:pkgname}"
		di
		di as txt "    {cmd:ssc2 type}      {it:filename} [, date()]  (less used)"
		di as txt "    {cmd:ssc2 copy}      {it:filename} [, date()]  (less used)"
		di
		di as txt "    {cmd:ssc2 snapshots}            (information on available snapshots)"
		di as txt "see help {help ssc2}"
		exit 198
	}

	local l = length(`"`cmd'"')

	* ---- pure pass-throughs to the official ssc command ----------------
	* The official -ssc- is present in every Stata installation; calling
	* the top-level command (rather than its internal subroutines, which
	* are undocumented and only in memory once ssc.ado has been loaded)
	* is the only reliable way to delegate.
	if `"`cmd'"'=="new" | `"`cmd'"'==substr("whatsnew",1,max(4,`l')) {
		ssc whatsnew `0'
		exit
	}
	if `"`cmd'"'=="hot" | `"`cmd'"'==substr("whatshot",1,max(6,`l')) {
		ssc hot `0'
		exit
	}
	if `"`cmd'"'=="uninstall" {
		ssc uninstall `0'
		exit
	}

	* ---- subcommands that gain date()/from() ---------------------------
	if `"`cmd'"'==substr("describe",1,max(1,`l')) {
		ssc2_describe `0'
		exit
	}
	if `"`cmd'"'==substr("install",1,max(4,`l')) {
		ssc2_install `0'
		exit
	}
	if `"`cmd'"'=="copy" | `"`cmd'"'=="cp" {
		ssc2_copy `0'
		exit
	}
	if `"`cmd'"'=="type" | `"`cmd'"'=="cat" {
		ssc2_type `0'
		exit
	}

	* ---- new informational / future subcommands ------------------------
	if `"`cmd'"'=="snapshots" {
		ssc2_snapshots `0'
		exit
	}
	if `"`cmd'"'=="versions" {
		di as err "{bf:ssc2 versions} is not yet implemented."
		di as err "It will list the versions of a package available across snapshots."
		di as err `"Meanwhile, browse {browse "https://github.com/labordynamicsinstitute/ssc-mirror/tags":the snapshot list}."'
		exit 198
	}

	di as err `"{bf:ssc2 `cmd'}: invalid subcommand"'
	exit 198
end


* =======================================================================
* ResolveSnapshot: turn date()/from() into a mirror URL
*   returns r(ref)  : git ref (tag YYYY-MM-DD, or "releases" for latest)
*   returns r(url)  : base URL ending in .../fmwww.bc.edu/repec/bocode/
*   returns r(shown): human-readable label for messages
* =======================================================================
program define ResolveSnapshot, rclass
	syntax [, DATE(string) FROM(string)]

	* Mirror URL precedence:
	*   1. from() option
	*   2. Stata global $SSC2_MIRROR
	*   3. environment variable SSC2_MIRROR
	*   4. built-in default
	* The mirror is expected to move to a different GitHub organization;
	* the overrides let users and scripts adapt without a code change.
	local isdefault 0
	if `"`from'"'=="" {
		local from `"$SSC2_MIRROR"'
	}
	if `"`from'"'=="" {
		local from : environment SSC2_MIRROR
	}
	if `"`from'"'=="" {
		local from "https://raw.githubusercontent.com/labordynamicsinstitute/ssc-mirror"
		local isdefault 1
	}

	* API base used only to diagnose failures (tag-existence check);
	* same precedence: $SSC2_MIRROR_API > env SSC2_MIRROR_API > default,
	* but the default applies only while the default mirror is in use.
	local api `"$SSC2_MIRROR_API"'
	if `"`api'"'=="" {
		local api : environment SSC2_MIRROR_API
	}
	if `"`api'"'=="" & `isdefault' {
		local api "https://api.github.com/repos/labordynamicsinstitute/ssc-mirror"
	}
	* strip one trailing slash, if any
	if substr(`"`from'"', -1, 1)=="/" {
		local from = substr(`"`from'"', 1, length(`"`from'"')-1)
	}

	if `"`date'"'=="" | lower(`"`date'"')=="latest" {
		* the mirror keeps its most recent state on the "releases" branch
		local ref   "releases"
		local shown "latest (releases branch)"
	}
	else {
		* accept YYYY-MM-DD (also normalizes e.g. 2022-1-7 -> 2022-01-07)
		local d = date(`"`date'"', "YMD")
		if `d' >= . {
			di as err `"option {bf:date(`date')}: invalid date"'
			di as err "  specify a date as YYYY-MM-DD, or {bf:date(latest)}"
			exit 198
		}
		local ref : display %tdCY-N-D `d'
		local ref = trim("`ref'")
		local today = date(c(current_date), "DMY")
		if `d' > `today' {
			di as err `"option {bf:date(`date')}: date is in the future"'
			exit 198
		}
		if `d' < date("2017-08-10", "YMD") {
			di as err `"option {bf:date(`date')}: no snapshots exist before 2017-08-10"'
			exit 198
		}
		if `d' < date("2021-12-21", "YMD") {
			di as txt "note: daily snapshots begin 2021-12-21; before that only"
			di as txt "      2017-08-10, 2021-04-15, and 2021-08-10 exist."
		}
		local shown "`ref'"
	}

	return local ref   `"`ref'"'
	return local shown `"`shown'"'
	return local api   `"`api'"'
	return local url   `"`from'/`ref'/fmwww.bc.edu/repec/bocode/"'
end


* Helpful error when -net from- on a snapshot URL fails.
* If an API base is known, one cheap call checks whether the git tag for
* the requested date exists, so the user learns WHICH thing went wrong.
* Any API response other than a clean hit or a clean file-not-found
* (e.g., the 60/hour unauthenticated rate limit yields neither) is
* treated as inconclusive and the generic message is shown.
program define DiagnoseSnapshot
	args url ref rc api
	di as err `"could not read the package index at"'
	di as err `"    `url'"'
	local diagnosed 0
	if `"`api'"' != "" & `"`ref'"' != "releases" {
		tempfile chk
		capture copy `"`api'/git/ref/tags/`ref'"' `"`chk'"', replace
		local crc = _rc
		if `crc'==0 {
			di as err `"  the snapshot {bf:`ref'} exists on the mirror, so this is likely"'
			di as err "  a network problem or an unexpected mirror layout"
			local diagnosed 1
		}
		else if `crc'==601 {
			di as err `"  the mirror has {bf:no snapshot dated `ref'}"'
			di as err `"  (see {browse "https://github.com/labordynamicsinstitute/ssc-mirror/tags":the snapshot list} and {browse "https://github.com/labordynamicsinstitute/ssc-mirror/blob/main/ERRATA.md":ERRATA} for known gaps)"'
			local diagnosed 1
		}
	}
	if !`diagnosed' {
		di as err "possible reasons:"
		di as err `"  - no snapshot exists for {bf:`ref'}"'
		di as err "  - a network problem, or the mirror host is unreachable"
	}
	exit `rc'
end


program define ssc2_describe
	* ssc2 describe <package>|<ltr> [, saving(fn[,replace]) date() from()]
	gettoken pkgname 0 : 0, parse(" ,")
	if length(`"`pkgname'"')==1 {
		local pkgname = lower(`"`pkgname'"')
		if !index("abcdefghijklmnopqrstuvwxyz_", `"`pkgname'"') {
			di as err "{bf:ssc2 describe}: letter must be a-z or _"
			exit 198
		}
	}
	else {
		CheckPkgname "ssc2 describe" `"`pkgname'"'
		local pkgname `"`s(pkgname)'"'
	}
	syntax [, SAVING(string asis) DATE(string) FROM(string)]

	* no snapshot requested: delegate fully to official ssc
	if `"`date'`from'"'=="" {
		if `"`saving'"'!="" {
			ssc describe `pkgname', saving(`saving')
		}
		else {
			ssc describe `pkgname'
		}
		exit
	}

	ResolveSnapshot, date(`date') from(`from')
	local ref   `"`r(ref)'"'
	local shown `"`r(shown)'"'
	local url   `"`r(url)'"'
	local api   `"`r(api)'"'

	LogOutput `"`saving'"' ssc2_describe_u `"`pkgname'"' `"`url'"' `"`ref'"' `"`shown'"' `"`api'"'
	if `"`s(loggedfn)'"' != "" {
		di as txt `"(output saved in `s(loggedfn)')"'
	}
end

program define ssc2_describe_u
	args pkgname url ref shown api
	local ltr = substr(`"`pkgname'"', 1, 1)
	if length(`"`pkgname'"')==1 {
		capture noisily net from `url'`ltr'
		if _rc {
			DiagnoseSnapshot `"`url'`ltr'"' `"`ref'"' `=_rc' `"`api'"'
		}
		di as txt /*
*/ "(type {cmd:ssc2 describe} {it:pkgname}{cmd:, date(`ref')} for more information on {it:pkgname})"
	}
	else {
		capture quietly net from `url'`ltr'
		if _rc {
			DiagnoseSnapshot `"`url'`ltr'"' `"`ref'"' `=_rc' `"`api'"'
		}
		capture net describe `pkgname'
		local rc = _rc
		if `rc'==601 | `rc'==661 {
			di as err /*
*/ `"{bf:ssc2 describe}: "{bf:`pkgname'}" not found in snapshot `shown'"'
			di as err /*
*/ "(To find all packages in this snapshot that start with `ltr', type {stata ssc2 describe `ltr', date(`ref')})"
			exit `rc'
		}
		if `rc'==0 {
			net describe `pkgname'
			di as txt /*
*/ "(type {stata ssc2 install `pkgname', date(`ref')} to install)"
		}
		exit `rc'
	}
end


program define ssc2_install
	* ssc2 install <package> [, all replace date() from() <net_install opts>]
	gettoken pkgname 0 : 0, parse(" ,")
	CheckPkgname "ssc2 install" `"`pkgname'"'
	local pkgname `"`s(pkgname)'"'
	syntax [, ALL REPLACE UPDATE REPLACEALL DATE(string) FROM(string) *]

	* no snapshot requested: delegate to official ssc
	if `"`date'`from'"'=="" {
		if "`update'`replaceall'" != "" {
			di as err "options {bf:update} and {bf:replaceall} require {bf:date()} or {bf:from()}"
			exit 198
		}
		* Official -replace- means: replace whatever is there, no version
		* comparison. When the existing copy was installed from a mirror
		* snapshot, honoring that also requires retiring its tracker
		* entry (a snapshot is a different source URL, so ssc's install
		* would otherwise ADD an entry and -ado uninstall pkgname- would
		* later fail on multiple matches). Copies installed from SSC
		* itself are left for ssc to manage natively, so a call that
		* never involved the mirror remains a pure passthrough.
		if "`replace'" != "" {
			ScanInstalled `pkgname'
			local ninst  = r(n)
			local nums   `"`r(nums)'"'
			local idates `"`r(dates)'"'
			local dnums
			forvalues j = 1/`ninst' {
				local d : word `j' of `idates'
				if "`d'" != "." {
					local k : word `j' of `nums'
					local dnums `dnums' `k'
				}
			}
			local nd : word count `dnums'
			if `nd' > 0 {
				di as txt "(replace: superseding `nd' snapshot-installed cop" ///
					cond(`nd'==1,"y","ies") " of `pkgname')"
				RemoveByNums `dnums'
			}
		}
		ssc install `pkgname', `all' `replace' `options'
		exit
	}

	ResolveSnapshot, date(`date') from(`from')
	local ref   `"`r(ref)'"'
	local shown `"`r(shown)'"'
	local url   `"`r(url)'"'
	local api   `"`r(api)'"'
	local ltr = substr("`pkgname'", 1, 1)

	capture quietly net from `url'`ltr'
	if _rc {
		DiagnoseSnapshot `"`url'`ltr'"' `"`ref'"' `=_rc' `"`api'"'
	}
	capture net describe `pkgname'
	local rc = _rc
	if `rc'==601 | `rc'==661 {
		di as err /*
*/ `"{bf:ssc2 install}: "{bf:`pkgname'}" not found in snapshot `shown'"'
		di as err `"  at `url'"'
		di as err /*
*/ "(To find all packages in this snapshot that start with `ltr', type {stata ssc2 describe `ltr', date(`ref')})"
		exit `rc'
	}
	if `rc' {
		error `rc'
	}

	* --- replace / update / replaceall semantics -----------------------
	* Background: each snapshot date is a distinct source URL, so without
	* explicit handling, repeated dated installs accumulate multiple
	* tracker entries and -ado uninstall pkgname- later fails ("criterion
	* matches more than one package").  The "version" compared here is
	* the snapshot date recovered from each installed copy's source URL;
	* copies installed from plain SSC have no such date and count as
	* not comparable.
	*   (nothing)   existing installation refused, as official ssc does
	*   replace     reinstall the SAME snapshot only
	*   update      move to a NEWER snapshot only; older is a no-op
	*   replaceall  replace ANY installed version, downgrades included
	local nopts = ("`replace'"!="") + ("`update'"!="") + ("`replaceall'"!="")
	if `nopts' > 1 {
		di as err "only one of {bf:replace}, {bf:update}, and {bf:replaceall} may be specified"
		exit 198
	}
	ScanInstalled `pkgname'
	local ninst  = r(n)
	local nums   `"`r(nums)'"'
	local idates `"`r(dates)'"'
	if `ninst' > 0 & "`ref'"=="releases" & `nopts' > 0 & "`replaceall'"=="" {
		di as err "with {bf:date(latest)}, installed versions cannot be compared by date;"
		di as err "use {bf:replaceall} to replace unconditionally"
		exit 110
	}
	else if `ninst' > 0 & "`replaceall'" != "" {
		di as txt "(replaceall: superseding `ninst' installed cop" ///
			cond(`ninst'==1,"y","ies") " of `pkgname')"
		RemoveByNums `nums'
		local replace replace
	}
	else if `ninst' > 0 & "`replace'" != "" {
		local same 1
		foreach d of local idates {
			if "`d'" != "`ref'" local same 0
		}
		if `same' {
			di as txt "(replace: reinstalling snapshot `ref' of `pkgname')"
			RemoveByNums `nums'
		}
		else {
			di as err "{bf:ssc2 install}: an installed copy of {bf:`pkgname'} is not snapshot `ref' (found: `idates'; . = no snapshot date)"
			di as err "  {bf:replace} only reinstalls the same snapshot;"
			di as err "  use {bf:update} to move to a newer snapshot, or {bf:replaceall} to replace any version"
			exit 110
		}
	}
	else if `ninst' > 0 & "`update'" != "" {
		local newest ""
		local unknown 0
		foreach d of local idates {
			if "`d'"=="." local unknown 1
			else if "`d'" > "`newest'" local newest "`d'"
		}
		if `unknown' {
			di as err "{bf:ssc2 install}: an installed copy of {bf:`pkgname'} has no snapshot date (installed from SSC directly?), so versions cannot be compared"
			di as err "  use {bf:replaceall} to replace unconditionally"
			exit 110
		}
		if "`ref'" > "`newest'" {
			di as txt "(update: superseding snapshot `newest' with `ref')"
			RemoveByNums `nums'
			local replace replace
		}
		else {
			di as txt "(installed snapshot `newest' is the same as or newer than `ref'; nothing to do)"
			di as txt "(use {bf:replaceall} to downgrade)"
			exit 0
		}
	}
	* ninst>0 with no option: proceed without pre-removal; net install
	* will refuse because files exist, matching official ssc behavior.

	di as result `"snapshot selected: `shown'"'
	di as result `"installing from  `url'..."'
	capture noisily net install `pkgname', `all' `replace' `options'
	local rc = _rc
	if `rc'==601 | `rc'==661 {
		di
		di as err /*
*/ `"{p}{bf:ssc2 install}: apparent error in the package file for {bf:`pkgname'} in this snapshot; please open an issue at {browse "https://github.com/labordynamicsinstitute/ssc-mirror/issues":the mirror repository}, providing the package name and date{p_end}"'
	}
	exit `rc'
end


* Scan installed packages named exactly `pkgname'. Captures the output
* of -ado dir- into a temporary plain-text log (widening the linesize so
* source URLs do not wrap, and restoring any open log as in LogOutput),
* then returns:
*   r(n)      number of installed copies
*   r(nums)   their [#] entry numbers, in listing order
*   r(dates)  the snapshot date parsed from each copy's source URL,
*             aligned with r(nums); "." when the URL carries no date
program define ScanInstalled, rclass
	args pkgname
	tempfile lst
	local oldls = c(linesize)

	quietly log
	local logtype   `"`r(type)'"'
	local logstatus `"`r(status)'"'
	local logfn     `"`r(filename)'"'

	nobreak {
		if `"`logtype'"' != "" {
			qui log close
		}
		capture break {
			capture set linesize 255
			qui log using `"`lst'"', text replace
			capture noisily ado dir `pkgname'
			qui log close
		}
		local rc = _rc
		capture log close
		capture set linesize `oldls'
		if "`logtype'" != "" {
			qui log using `"`logfn'"', append `logtype'
			if "`logstatus'" != "on" {
				qui log off
			}
		}
	}
	if `rc' {
		* could not produce the listing; report nothing installed
		return scalar n = 0
		exit 0
	}

	local nums
	local dates
	local cur ""
	local curdate "."
	tempname fh
	file open `fh' using `"`lst'"', read text
	file read `fh' line
	while r(eof)==0 {
		local lline = lower(`"`line'"')
		if regexm(`"`lline'"', "^\[([0-9]+)\][ ]+package[ ]+`pkgname'([ ]|$)") {
			if "`cur'" != "" {
				local nums  `nums' `cur'
				local dates `dates' `curdate'
			}
			local cur = regexs(1)
			local curdate "."
			if regexm(`"`lline'"', "/([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])/") {
				local curdate = regexs(1)
			}
		}
		else if regexm(`"`lline'"', "^\[([0-9]+)\][ ]+package[ ]") {
			* a different package's header: close any open match
			if "`cur'" != "" {
				local nums  `nums' `cur'
				local dates `dates' `curdate'
			}
			local cur ""
		}
		else if "`cur'" != "" & "`curdate'"=="." {
			if regexm(`"`lline'"', "/([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])/") {
				local curdate = regexs(1)
			}
		}
		file read `fh' line
	}
	file close `fh'
	if "`cur'" != "" {
		local nums  `nums' `cur'
		local dates `dates' `curdate'
	}

	return scalar n = `: word count `nums''
	return local nums  `"`nums'"'
	return local dates `"`dates'"'
end

* Uninstall the listed [#] entries from the highest number down, so the
* remaining numbering stays valid throughout.
program define RemoveByNums
	local n : word count `0'
	forvalues i = `n'(-1)1 {
		local k : word `i' of `0'
		capture quietly ado uninstall [`k']
	}
end


program define ssc2_copy
	* ssc2 copy <filename> [, plus personal <copy_options> date() from()]
	* backwards compatibility: sjplus and stbplus are synonyms for plus
	gettoken fn 0 : 0, parse(" ,")
	CheckFilename "ssc2 copy" `"`fn'"'
	local fn `"`s(fn)'"'
	syntax [, PUBlic BINary REPLACE STBplus SJplus PLus Personal ///
	          DATE(string) FROM(string)]

	* no snapshot requested: delegate fully to official ssc
	if `"`date'`from'"'=="" {
		ssc copy `fn', `public' `binary' `replace' `stbplus' `sjplus' `plus' `personal'
		exit
	}

	ResolveSnapshot, date(`date') from(`from')
	local url `"`r(url)'"'

	local text = cond("`binary'"=="", "text", "")

	local op "stbplus"
	if "`sjplus'" != "" {
		local stbplus stbplus
		local op "sjplus"
	}
	if "`plus'" != "" {
		local stbplus stbplus
		local op "plus"
	}
	if "`stbplus'"!="" & "`personal'"!="" {
		di as err "options {bf:`op'} and {bf:personal} may not be specified together"
		exit 198
	}
	local ltr = substr(`"`fn'"', 1, 1)

	if "`stbplus'" != "" {
		local dir : sysdir STBPLUS
		local dirsep : dirsep
		local dir `"`dir'`ltr'`dirsep'"'
		local dfn `"`dir'`fn'"'
	}
	else if "`personal'" != "" {
		local dir : sysdir PERSONAL
		local dfn `"`dir'`fn'"'
	}
	else {
		local dir "current directory"
		local dfn `"`fn'"'
	}

	capture copy `"`url'`ltr'/`fn'"' `"`dfn'"', `public' `text' `replace'
	local rc = _rc
	if `rc'==601 | `rc'==661 {
		di as err /*
*/ `"{bf:ssc2 copy}: "{bf:`fn'}" not found in snapshot at `url'`ltr'/"'
		exit `rc'
	}
	if `rc' {
		error `rc'
	}
	di as txt "(file `fn' copied to `dir')"
end


program define ssc2_type
	gettoken fn 0 : 0, parse(" ,")
	syntax [, ASIS DATE(string) FROM(string)]
	CheckFilename "ssc2 type" `"`fn'"'
	local fn `"`s(fn)'"'

	* no snapshot requested: delegate fully to official ssc
	if `"`date'`from'"'=="" {
		ssc type `fn', `asis'
		exit
	}

	ResolveSnapshot, date(`date') from(`from')
	local url `"`r(url)'"'
	local ltr = substr(`"`fn'"', 1, 1)

	capture type `"`url'`ltr'/`fn'"'
	local rc = _rc
	if `rc'==601 | `rc'==661 {
		di as err /*
*/ `"{bf:ssc2 type}: "{bf:`fn'}" not found in snapshot at `url'`ltr'/"'
		exit `rc'
	}
	if `rc' {
		error `rc'
	}
	type `"`url'`ltr'/`fn'"', `asis'
end


program define ssc2_snapshots
	* informational for now; a machine-readable exceptions file is planned
	syntax [, FROM(string)]
	di as txt "Snapshots of the SSC archive are stored as date-stamped git tags"
	di as txt "(YYYY-MM-DD) in the mirror repository:"
	di as txt `"    {browse "https://github.com/labordynamicsinstitute/ssc-mirror/tags"}"'
	di
	di as txt "  - daily snapshots exist from {bf:2021-12-21} onward, with occasional"
	di as txt `"    gaps listed in the mirror's {browse "https://github.com/labordynamicsinstitute/ssc-mirror/blob/main/ERRATA.md":ERRATA}"'
	di as txt "  - three earlier snapshots exist: {bf:2017-08-10}, {bf:2021-04-15}, {bf:2021-08-10}"
	di as txt "  - {bf:date(latest)} uses the most recent mirrored state"
	di
	di as txt "The mirror location can be overridden with the {bf:from()} option,"
	di as txt "the Stata global {bf:SSC2_MIRROR}, or the environment variable of"
	di as txt "the same name (see help {help ssc2})."
	di
	di as txt "Example:  {stata ssc2 install reghdfe, date(2022-01-07)}"
end



program define CheckPkgname, sclass
	args id pkgname
	sret clear
	if `"`pkgname'"' == "" {
		di as err `"{bf:`id'}: nothing found where package name expected"'
		exit 198
	}
	if length(`"`pkgname'"')==1 {
		di as err `"{bf:`id'}: "{bf:`pkgname'}" invalid package name"'
		exit 198
	}
	local pkgname = lower(`"`pkgname'"')
	if !index("abcdefghijklmnopqrstuvwxyz_", substr(`"`pkgname'"',1,1)) {
		di as err `"{bf:`id'}: "{bf:`pkgname'}" invalid package name"'
		exit 198
	}
	sret local pkgname `"`pkgname'"'
end

program define CheckFilename, sclass
	args id fn
	sret clear
	if `"`fn'"'=="" {
		di as err `"{bf:`id'}: nothing found where filename expected"'
		exit 198
	}
	if length(`"`fn'"')==1 {
		di as err `"{bf:`id'}: "{bf:`fn'}" invalid filename"'
		exit 198
	}
	local fn = lower(`"`fn'"')
	if !index("abcdefghijklmnopqrstuvwxyz_", substr(`"`fn'"',1,1)) {
		di as err `"{bf:`id'}: "{bf:`fn'}" invalid filename"'
		exit 198
	}
	sret local fn `"`fn'"'
end


program define LogOutput, sclass
	gettoken saving 0 : 0

	sret clear
	ParseSaving `saving'
	local fn      `"`s(fn)'"'
	local replace  "`s(replace)'"
	sret clear

	if `"`fn'"'=="" {
		`0'
		exit
	}

	quietly log
	local logtype   `"`r(type)'"'
	local logstatus `"`r(status)'"'
	local logfn     `"`r(filename)'"'

	nobreak {
		if `"`logtype'"' != "" {
			qui log close
		}
		capture break {
			capture log using `"`fn'"' , `replace'
			if _rc {
				noisily log using `"`fn'"', `replace'
				/*NOTREACHED*/
			}
			local loggedfn `"`r(filename)'"'
			noisily `0'
		}
		local rc = _rc
		capture log close
		if "`logtype'" != "" {
			qui log using `"`logfn'"', append `logtype'
			if "`logstatus'" != "on" {
				qui log off
			}
		}
	}
	sret local loggedfn `"`loggedfn'"'
	exit `rc'
end


program define ParseSaving, sclass
	* fn[,replace]
	sret clear
	if `"`0'"' == "" {
		exit
	}
	gettoken fn      0 : 0, parse(", ")
	gettoken comma   0 : 0
	gettoken replace 0 : 0

	if `"`fn'"'!="" & `"`0'"'=="" {
		if `"`comma'"'=="" | (`"`comma'"'=="," & `"`replace'"'=="") {
			sret local fn `"`fn'"'
			exit
		}
		if `"`comma'"'=="," & `"`replace'"'=="replace" {
			sret local fn `"`fn'"'
			sret local replace "replace"
			exit
		}
	}
	di as err "option {bf:saving()} misspecified"
	exit 198
end
