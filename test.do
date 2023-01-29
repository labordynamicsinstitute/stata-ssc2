// testing
net install ssc2, all replace from("https://raw.githubusercontent.com/labordynamicsinstitute/ssc-mirror-stata/master")
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

// system used for testing


di "=== SYSTEM DIAGNOSTICS ==="
creturn list
query
di "=========================="

