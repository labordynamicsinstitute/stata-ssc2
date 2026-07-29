// -----------------------------------------------------------------------
// Test suite for ssc2.  Run from the repository root:
//     stata -b do test.do          (or interactively after -cd- here)
// Example package: reghdfe (per project specification).
// Known ground truth, read from the mirror on 2026-07-08:
//   snapshot 2022-01-07 -> reghdfe "*! version 5.7.3 13nov2019"
// -----------------------------------------------------------------------
clear all
version 14

// ---- helper: assert the installed reghdfe.ado starbang contains a string
capture program drop assert_reghdfe_version
program define assert_reghdfe_version
    args needle
    quietly findfile reghdfe.ado
    tempname fh
    file open `fh' using `"`r(fn)'"', read text
    file read `fh' line
    file close `fh'
    di as txt `"    installed: `line'"'
    assert strpos(`"`line'"', `"`needle'"') > 0
end

// ---- 0. install the ssc2 under test (from THIS working copy) ------------
// To test-install over the network instead, use your fork, e.g.:
//   net install ssc2, all replace from("https://raw.githubusercontent.com/<user>/stata-ssc2/<branch>")
capture ado uninstall ssc2
discard
net install ssc2, all replace from("`c(pwd)'")
discard
capture noisily ssc2 snapshots     // canary: exists only in the rewrite
assert _rc==0

// ---- 1. generic install: ssc2 must fall back onto ssc -------------------
capture ado uninstall reghdfe
ssc2 install reghdfe
assert_reghdfe_version "version"        // installed, starbang present
capture noisily assert_reghdfe_version "5.7.3"
assert _rc!=0                           // current SSC version is NOT 5.7.3
ssc2 uninstall reghdfe                  // exercises uninstall pass-through

// ---- 2. dated snapshot install: validate the older version --------------
ssc2 install reghdfe, date(2022-01-07)
assert_reghdfe_version "5.7.3"
ssc2 uninstall reghdfe

// ---- 3. date normalization: 2022-1-7 must equal 2022-01-07 --------------
ssc2 install reghdfe, date(2022-1-7)
assert_reghdfe_version "5.7.3"
ssc2 uninstall reghdfe

// ---- 3b. replace / update / replaceall semantics -------------------------
// ground truth: reghdfe is 5.7.3 in 2022-01-07 and 6.12.3 in 2024-09-27
ssc2 install reghdfe, date(2022-01-07)
* no option + existing installation: refused (native ssc-like behavior)
capture noisily ssc2 install reghdfe, date(2024-09-27)
assert_reghdfe_version "5.7.3"            // unchanged either way
* replace reinstalls the SAME snapshot only
ssc2 install reghdfe, date(2022-01-07) replace
assert_reghdfe_version "5.7.3"
capture noisily ssc2 install reghdfe, date(2024-09-27) replace
assert _rc==110                            // different snapshot: refused
assert_reghdfe_version "5.7.3"
* update moves forward...
ssc2 install reghdfe, date(2024-09-27) update
assert_reghdfe_version "6.12.3"
* ...but never backward (friendly no-op, rc 0)
ssc2 install reghdfe, date(2022-01-07) update
assert_reghdfe_version "6.12.3"
* replaceall replaces anything, downgrades included
ssc2 install reghdfe, date(2022-01-07) replaceall
assert_reghdfe_version "5.7.3"
ssc2 uninstall reghdfe            // exactly one tracked copy throughout
capture noisily which reghdfe
assert _rc!=0
* update/replaceall require a snapshot context
capture noisily ssc2 install reghdfe, update
assert _rc==198
capture noisily ssc2 install reghdfe, replaceall
assert _rc==198
* only one of the three may be given
capture noisily ssc2 install reghdfe, date(2022-01-07) replace update
assert _rc==198

// ---- 4. date(latest): releases branch of the mirror ---------------------
ssc2 install reghdfe, date(latest)
assert_reghdfe_version "version"
ssc2 uninstall reghdfe

// ---- 5. URL override precedence -----------------------------------------
// global override with a bad URL must break dated installs...
global SSC2_MIRROR "https://raw.githubusercontent.com/nonexistent-org/nonexistent-repo"
capture noisily ssc2 install reghdfe, date(2022-01-07)
assert _rc!=0
// ...and the from() option must take precedence over the (bad) global
ssc2 install reghdfe, date(2022-01-07) from("https://raw.githubusercontent.com/labordynamicsinstitute/ssc-mirror")
assert_reghdfe_version "5.7.3"
ssc2 uninstall reghdfe
macro drop SSC2_MIRROR

// ---- 6. other pass-through functionality --------------------------------
ssc2 hot, n(5)
ssc2 new
ssc2 describe reghdfe                   // no date: delegated to ssc
ssc2 describe reghdfe, date(2022-01-07)
ssc2 describe r, date(2022-01-07)
ssc2 type reghdfe.pkg, date(2022-01-07)
cd "`c(tmpdir)'"
ssc2 copy reghdfe.pkg, date(2022-01-07) replace

// ---- 7. error handling ----------------------------------------------------
capture noisily ssc2 install reghdfe, date(2099-01-01)
assert _rc==198                          // future date
capture noisily ssc2 install reghdfe, date(not-a-date)
assert _rc==198                          // malformed date
capture noisily ssc2 install reghdfe, date(2021-12-22)
assert _rc!=0                            // known missing snapshot (workflow gap)
capture noisily ssc2 install thispackagedoesnotexist, date(2022-01-07)
assert _rc!=0                            // snapshot exists, package does not
capture noisily ssc2 badsubcommand
assert _rc==198
capture noisily ssc2 versions reghdfe
assert _rc==198                          // documented as not yet implemented

di as result "ALL TESTS PASSED"

// system used for testing
di "=== SYSTEM DIAGNOSTICS ==="
creturn list
query
di "=========================="
