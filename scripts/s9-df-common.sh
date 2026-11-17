# Source from the repository root in Git Bash.
mkdir -p build/tmp build/s9/df
export TMPDIR="$PWD/build/tmp" TMP="$PWD/build/tmp" TEMP="$PWD/build/tmp"
S9_DF_SHARED=/c/Users/xuzhi/Documents/gcc_knc/.work/_shared
export PATH="$S9_DF_SHARED/toolchain/cygwin/bin:$PATH"
export OMP_DYNAMIC=FALSE OMP_NUM_THREADS=12 PYTHONDONTWRITEBYTECODE=1
