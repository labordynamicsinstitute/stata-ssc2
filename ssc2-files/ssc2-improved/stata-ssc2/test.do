// -----------------------------------------------------------------------
// Test script for ssc2. Run interactively or via:  stata -b do test.do
// Uses assert-style checks (rc) so failures are loud.
// -----------------------------------------------------------------------
clear all
version 14

// install ssc2 itself from the repo under test
// NOTE: adjust the branch (main / your fork) as needed
global github "https://raw.githubusercontent.com"
capture ado uninstall ssc2
net install ssc2, all replace from("$github/labordynamicsinstitute/stata-ssc2/main")

// ---- 1. dated install --------------------------------------------------
capture ssc uninstall cmp
ssc2 install cmp, date(2022-01-07)
which cmp                       // expect: *! cmp 8.6.7 5 January 2022
ssc uninstall cmp

// ---- 2. date normalization (2022-1-7 == 2022-01-07) ---------------------
ssc2 install cmp, date(2022-1-7)
which cmp
ssc uninstall cmp

// ---- 3. plain install must delegate to official ssc ---------------------
ssc2 install cmp
which cmp                       // expect: current SSC version
ssc uninstall cmp

// ---- 4. date(latest) uses the releases branch of the mirror -------------
ssc2 install cmp, date(latest)
which cmp
ssc uninstall cmp

// ---- 5. delegated subcommands must not error ----------------------------
ssc2 hot, n(5)
ssc2 new
ssc2 describe cmp               // no date: delegated
ssc2 describe cmp, date(2022-01-07)
ssc2 describe c,   date(2022-01-07)

// ---- 6. copy/type with a date (previously broken) ------------------------
tempfile ignore
cd `c(tmpdir)'
ssc2 type  cmp.pkg, date(2022-01-07)
ssc2 copy  cmp.pkg, date(2022-01-07) replace

// ---- 7. error handling ----------------------------------------------------
capture noisily ssc2 install cmp, date(2099-01-01)
assert _rc==198                  // future date
capture noisily ssc2 install cmp, date(not-a-date)
assert _rc==198                  // malformed date
capture noisily ssc2 install cmp, date(2020-06-15)
assert _rc!=0                    // date in pre-daily-snapshot era with no tag
capture noisily ssc2 install thispackagedoesnotexist, date(2022-01-07)
assert _rc!=0                    // package not found in snapshot
capture noisily ssc2 badsubcommand
assert _rc==198

// ---- 8. informational subcommands ----------------------------------------
ssc2 snapshots
capture noisily ssc2 versions cmp
assert _rc==198                  // documented as not yet implemented

di as result "ALL TESTS PASSED"

// system used for testing
di "=== SYSTEM DIAGNOSTICS ==="
creturn list
query
di "=========================="
