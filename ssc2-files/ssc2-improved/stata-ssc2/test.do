// -----------------------------------------------------------------------
// Test script for ssc2. Run interactively or via:  stata -b do test.do
// Uses assert-style checks (rc) so failures are loud.
// -----------------------------------------------------------------------
clear all
version 14

// ---- 0. install the ssc2 under test -------------------------------------
// Default: install from THIS working copy. Run test.do from the repo root
// (in batch mode, `stata -b do test.do` from the repo root does this).
// Do NOT install from the GitHub main branch: that still hosts the old
// released version, not the code you are testing.
capture ado uninstall ssc2
discard                          // flush any old ssc2 program from memory
net install ssc2, all replace from("`c(pwd)'")
// alternative: install from your fork/branch on GitHub, e.g.
// net install ssc2, all replace from("https://raw.githubusercontent.com/<youruser>/stata-ssc2/improve-ssc2")
discard

// canary: -ssc2 snapshots- exists only in the rewritten version.
// If this fails, the OLD released ssc2 is installed -- stop and fix that
// before trusting any result below.
capture noisily ssc2 snapshots
assert _rc==0

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
