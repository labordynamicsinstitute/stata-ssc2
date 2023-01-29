*! version 1.1.7 29jan2023
// Based on 
// ssc2 version 1.1.6  15oct2019
program define ssc2
	version 7
	gettoken cmd 0 : 0, parse(" ,")

	di as txt "" _c		/* work around for net display problem */

	if `"`cmd'"'=="" {
		di as txt "ssc2 commands are"
		di as txt "    {cmd:ssc2 new}"
		di as txt "    {cmd:ssc2 hot}"
		di
		di as txt "    {cmd:ssc2 describe}  {it:pkgname}"
		di as txt "    {cmd:ssc2 describe}  {it:letter}"
		di
		di as txt "    {cmd:ssc2 install}   {it:pkgname}"
		di as txt "    {cmd:ssc2 uninstall} {it:pkgname}"
		di
		di as txt "    {cmd:ssc2 type}      {it:filename}  (less used)"
		di as txt "    {cmd:ssc2 copy}      {it:filename}  (less used)"
		di as txt "see help {help ssc2##|_new:ssc2}"
		exit 198
	}


	local l = length(`"`cmd'"')
	if `"`cmd'"' == bsubstr("whatsnew",1,max(4,`l')) {
		// unchanged
		sscwhatsnew `0'
		exit
	}
	if `"`cmd'"' == "new" { 
		// unchanged
		sscwhatsnew `0'
		exit
	}
	if `"`cmd'"' == bsubstr("whatshot",1,max(6,`l')) {
		// unchanged
		ssc_whatshot `0'
		exit
	}
	if `"`cmd'"' == "hot" { 
		// unchanged
		ssc_whatshot `0'
		exit
	}
	if `"`cmd'"' == bsubstr("describe",1,max(1,`l')) {
		ssc2describe `0'
		exit
	}
	if `"`cmd'"' == bsubstr("install",1,max(4,`l')) {
		ssc2install `0'
		exit
	}
	if `"`cmd'"' == "uninstall" {
		// unchanged
		sscuninstall `0'
		exit
	}
	if `"`cmd'"'=="copy" | `"`cmd'"'=="cp" {
		// unchanged?
		ssc2copy `0'
		exit
	}
	if `"`cmd'"'=="type" | `"`cmd'"'=="cat" {
		// unchanged
		ssc2type `0'
		exit
	}
	di as err `"{bf:ssc2 `cmd'}: invalid subcommand"'
	exit 198
end

// define the base url if not using options
global repecadr "fmwww.bc.edu/repec/bocode/"
global SSCMIRRORURL "raw.githubusercontent.com/labordynamicsinstitute/ssc-mirror"


program define ProcSSCDate, rclass
	local datetoken `"`0'"'
	gettoken date dateurl : datetoken, parse(" ,")
	gettoken nothing dateurl : datetoken, parse(" ,")

	if "`date'"=="" {
		InvalidDateURL `0'
	}
	local today  : display %tdCY-N-D date(c(current_date), "DMY")
	
	if "`today'" <  "`date'" {
		InvalidDateURL `0' `"Date is in the future!"'
	}
	ret local ssc2date "`date'"
	ret local ssc2url "https://${SSCMIRRORURL}/`date'/${repecadr}"

	// This should presumably fetch the list of valid dates, and validate against that
	// TBD
end


program define InvalidDateURL
    args date errormsg
	di as err `"option {bf:date(`date')}:  invalid date"'
	di as err `"  Date must be valid from https://${SSCMIRRORURL}/tags"'
	if "`errormsg'" != "" {
		di as err `"  `errormsg'"'
	}
	exit 198
end



program define ssc2describe
	* ssc2 describe <package>|<ltr> [, saving(<filename>[,replace]) date(<date string>)]
	gettoken pkgname 0 : 0, parse(" ,")
	if length(`"`pkgname'"')==1 {
		local pkgname = lower(`"`pkgname'"')
		if !index("abcdefghijklmnopqrstuvwxyz_",`"`pkgname'"') {
			di as err "{bf:ssc2 describe}: letter must be a-z or _"
			exit 198
		}
	}
	else {
		CheckPkgname "ssc2 describe" `"`pkgname'"'
		local pkgname `"`s(pkgname)'"'
	}
	syntax [, SAVING(string asis) DATE(string asis)]
	if `"`date'"' != "" {
		ProcSSCDate `date'
		local ssc2date `"`r(ssc2date)'"'
		local ssc2url  `"`r(ssc2url)'"'
	}
	else {
		local ssc2url "http://${repecadr}"
	}
	LogOutput `"`saving'"' ssc2describe_u `"`pkgname'"' `"`ssc2url'"' `"`ssc2date'"'
	if `"`s(loggedfn)'"' != "" {
		di as txt `"(output saved in `s(loggedfn)')"'
	}
end

program define ssc2describe_u
	args pkgname ssc2url ssc2date
	local ltr = bsubstr(`"`pkgname'"',1,1)
	if length(`"`pkgname'"')==1 {
		net from `ssc2url'`ltr'
		di as txt /*
*/ "(type {cmd:ssc2 describe} {it:pkgname} for more information on {it:pkgname})"
	}
	else {
		qui net from `ssc2url'`ltr'
		capture net describe `pkgname'
		local rc = _rc
		if _rc==601 | _rc==661  {
			di as err /*
*/ `"{bf:ssc2 describe}: "{bf:`pkgname'}" not found at SSC, type {stata search `pkgname'}"'
			di as err /*
*/ "(To find all packages at SSC that start with `ltr', type {stata ssc2 describe `ltr'})"
		}
		if _rc==0 {
			net describe `pkgname'
			di as txt /*
			*/ "(type {stata ssc2 install `pkgname', date(`ssc2date')} to install)"
		}
		exit `rc'
	}
end


program define ssc2install
	* ssc2 install <package> [, <net_install_options> DATE(string asis)]
	gettoken pkgname 0 : 0, parse(" ,")
	CheckPkgname "ssc2 install" `"`pkgname'"'
	local pkgname `"`s(pkgname)'"'
	syntax [, ALL REPLACE DATE(string asis)]
	local ltr = bsubstr("`pkgname'",1,1)
	if `"`date'"' != "" {
		ProcSSCDate `date'
		local ssc2date `"`r(ssc2date)'"'
		local ssc2url  `"`r(ssc2url)'"'
	}
	else {
		local ssc2url "http://${repecadr}"
	}

	qui net from `ssc2url'`ltr'
	capture net describe `pkgname'
	local rc = _rc
	if _rc==601 | _rc==661 {
		di as err /*
*/ `"{bf:ssc2 install}: "{bf:`pkgname'}" not found at SSC"'
        di as err `" at `ssc2url'"'
        di as err `" type {stata search `pkgname'}"'
		di as err /*
*/ "(To find all packages at SSC that start with `ltr', type {stata ssc2 describe `ltr'})"
		exit `rc'
	}
	if _rc {
		error `rc'
	}

	if "`ssc2date'" != "" {
		di as result `"snapshot selected: `ssc2date'"'
	}
	di as result `"installing from  `ssc2url'..."'
	capture noi net install `pkgname', `all' `replace'
	local rc = _rc
	if _rc==601 | _rc==661 {
		di
		di as err /*
*/ `"{p}{bf:ssc2 install}: apparent error in package file for {bf:`pkgname'}; please notify {browse "mailto:repec@repec.org":repec@repec.org}, providing package name{p_end}"'
	}
	exit `rc'
end


program define ssc2copy
	* ssc2 copy <filename> [, plus personal <copy_options>]
	*
	* backwards compatibility: sjplus and stbplus are synonyms for plus

	gettoken fn 0 : 0, parse(" ,")
	CheckFilename "ssc2 copy" `"`fn'"'
	local fn `"`s(fn)'"'
	syntax [, PUBlic BINary REPLACE STBplus SJplus PLus Personal]

	local text = cond("`binary'"=="","text","")

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
	local ltr = bsubstr(`"`fn'"',1,1)


	if "`stbplus'"!="" {
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

	capture copy `"https://${ssc2prefix}${ssc2url}`ltr'/`fn'"' /*
		*/ `"`dfn'"' , `public' `text' `replace'
	local rc = _rc
	if _rc==601 | _rc==661 {
		di as err /*
	*/ `"{bf:ssc2 copy}: "{bf:`fn'}" not found at ssc2, type {stata search `fn'}"'
		exit `rc'
	}
	if _rc {
		error `rc'
	}
	di as txt "(file `fn' copied to `dir')"
end


program define ssc2type
	gettoken fn 0 : 0, parse(" ,")
	syntax [, ASIS]
	CheckFilename "ssc2 type" `"`fn'"'
	local fn `"`s(fn)'"'
	local ltr = bsubstr(`"`fn'"',1,1)
	capture type `"https://${ssc2prefix}${ssc2url}`ltr'/`fn'"'
	local rc = _rc
	if _rc==601 | _rc==661 {
		di as err /*
	*/ `"{bf:ssc2 type}: "{bf:`fn'}" not found at ssc2, type {stata search `fn'}"'
		exit `rc'
	}
	if _rc {
		error `rc'
	}
	type `"https://${ssc2prefix}${ssc2url}`ltr'/`fn'"', `asis'
end


program define CheckPkgname, sclass
	args id pkgname
	sret clear
	if `"`pkgname'"' == "" {
		di as err `"{bf:`id'}: nothing found where package name expected"'
		exit 198
	}
	if length(`"`pkgname'"')==1 {
		di as err `"{bf:`id'}: "{bf:`pkgname'}" invalid ssc2 package name"'
		exit 198
	}
	local pkgname = lower(`"`pkgname'"')
	if !index("abcdefghijklmnopqrstuvwxyz_",bsubstr(`"`pkgname'"',1,1)) {
		di as err `"{bf:`id'}: "{bf:`pkgname'}" invalid ssc2 package name"'
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
		di as err `"{bf:`id'}: "{bf:`fn'}" invalid ssc2 filename"'
		exit 198
	}
	local fn = lower(`"`fn'"')
	if !index("abcdefghijklmnopqrstuvwxyz_",bsubstr(`"`fn'"',1,1)) {
		di as err `"{bf:`id'}: "{bf:`fn'}" invalid ssc2 filename"'
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
