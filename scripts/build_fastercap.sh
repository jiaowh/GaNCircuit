#!/bin/bash
# Headless FasterCap 6.0.7 build into .tools/FasterCap-bin; run under WSL: bash scripts/build_fastercap.sh
# Route: FasterCap README, "Linux 64 bits headless". Sources, cloned into the git-ignored .tools/ (LGPL 2.1+):
#   git clone https://github.com/ediloren/FasterCap.git   (b42179a8fdd25ab42fe45527282b4a738d7e7f87)
#   git clone https://github.com/ediloren/LinAlgebra.git  (627132d70bfd7eadd727f930286938a5a01d9914)
#   git clone https://github.com/ediloren/Geometry.git    (de03ffebfd5013b96102bd60f71c8fe8b73870e2)
# System packages (Ubuntu 24.04): cmake 3.28.3, libwxgtk3.2-dev 3.2.4; gcc 13.3.
# The only change, made in the build copy: CMakeLists asks wx-config for version 3.0; 3.2 is installed.
set -e
T=/mnt/c/Users/Jiaow/Documents/github/phd_circuit/.tools
B=$HOME/fcbuild
rm -rf "$B"; mkdir -p "$B/build"
cp -r "$T/FasterCap" "$T/LinAlgebra" "$T/Geometry" "$B/"
sed -i 's/--version=3.0/--version=3.2/' "$B/FasterCap/CMakeLists.txt"
cd "$B/build"
cmake -G"Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DFASTFIELDSOLVERS_HEADLESS=ON ../FasterCap > cmake.log
make -j4 > make.log 2>&1 || { tail -30 make.log; exit 1; }
mkdir -p "$T/FasterCap-bin"
cp FasterCap "$T/FasterCap-bin/"
echo built
