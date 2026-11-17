#!/bin/bash
# Local-only OpenSSH argv regression; refuse all external transport.
printf '%s\n' "$@" >> transport-args.txt
if [[ "$1" == -O ]]; then
    [[ "$2" == -T ]] || { echo 'missing legacy scp -T' >&2; exit 91; }
    touch scp-options-ok
    exit 1
fi
# Initial mkdir and state poll succeed locally without a card. Upload then fails.
exit 0
