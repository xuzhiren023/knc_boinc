"""Extract production quadrature code, then build/run its boundary checks."""
from pathlib import Path
import os
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root/'third_party/milkywayathome_client_196/nbody/src/nbody_mixeddwarf.c'
text = source.read_text()
start = text.index('static real gauss_quad')
end = text.index('static inline real max_finder', start)
prefix = '''#include <omp.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define NBODY_PARALLEL_QUAD 1
#define TRUE 1
#define FALSE 0
typedef double real;
typedef int mwbool;
enum {Plummer, General_Hernquist, NFW, Cored};
typedef struct {int type; real p0;} Dwarf;
'''
out = root/'build/s8/quad-kernel.c'
kernel = text[start:end]
if 'gauss_quad_serial' not in kernel:
    kernel = kernel.replace('static real gauss_quad(', 'static real gauss_quad_serial(', 1)
    kernel += '\n#define gauss_quad gauss_quad_serial\n'
out.write_text(prefix + kernel + (root/'tests/quad_kernel.c').read_text())
cyg = Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared/toolchain/cygwin/bin')
exe = root/'build/s8/quad-kernel.exe'
subprocess.run([str(cyg/'gcc.exe'), '-O2', '-fopenmp', '-ffp-contract=off',
                str(out), '-o', str(exe)], check=True)
subprocess.run([str(exe)], check=True)
