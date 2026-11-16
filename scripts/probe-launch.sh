#!/bin/sh
set -eu
export LD_LIBRARY_PATH=".:${LD_LIBRARY_PATH:-}"
exec ./libm_probe.mic log-input.bin
