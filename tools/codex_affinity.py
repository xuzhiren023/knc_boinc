#!/usr/bin/env python3
"""Launch an engineer with CPUs 0-9; descendants inherit the Windows mask."""
import ctypes
from ctypes import wintypes
import subprocess
import sys


def main():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    kernel.SetProcessAffinityMask.restype = wintypes.BOOL
    if not kernel.SetProcessAffinityMask(kernel.GetCurrentProcess(), 0x3FF):
        raise ctypes.WinError(ctypes.get_last_error())
    return subprocess.call(sys.argv[1:])


if __name__ == '__main__':
    sys.exit(main())
