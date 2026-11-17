# knc-boinc correctness/portability copy; see CARD_RUN.md for provenance.
# Shared-card private-session helpers. Loaded on stdin, never installed globally.
# All helpers and their children inherit the private cwd.
resolve_tmp() {
    [ -z "${tmp_physical:-}" ] || return 0
    tmp_physical=$(cd /tmp && pwd -P) && [ -n "$tmp_physical" ] || {
        echo 'guard_dir: cannot resolve physical /tmp' >&2; return 91;
    }
}
resolve_run_dir() {
    case "$run_dir" in
        /tmp/knc-boinc/claude-????????????????????????????????) ;;
        *) echo "guard_dir: directory shape: $run_dir" >&2; return 91 ;;
    esac
    suffix=${run_dir##*/claude-}
    case "$suffix" in
        *[!0-9a-f]*) echo "guard_dir: job ID must be lowercase hex: $run_dir" >&2; return 91 ;;
    esac
    resolve_tmp || return 91
    physical_run_dir=${tmp_physical%/}/knc-boinc/claude-$suffix
}
guard_dir() {
    resolve_run_dir || return 91
    [ ! -L "$run_dir" ] || {
        echo "guard_dir: directory is a symlink: $run_dir" >&2; return 91;
    }
    [ -d "$run_dir" ] || {
        echo "guard_dir: directory missing: $run_dir" >&2; return 91;
    }
    [ "$(pwd -P)" = "$physical_run_dir" ] || {
        echo "guard_dir: physical cwd must equal $physical_run_dir" >&2; return 91;
    }
    [ "$(LC_ALL=C ls -ldn "$run_dir" | { read -r mode links owner rest; printf '%s' "$owner"; })" = "$(id -u)" ] || {
        echo "guard_dir: directory owner mismatch or unreadable: $run_dir" >&2; return 91;
    }
}
check_boot() {
    [ -n "$boot_id" ] || { echo 'check_boot: boot ID missing' >&2; return 92; }
    current_boot=$(cat /proc/sys/kernel/random/boot_id) && [ -n "$current_boot" ] || {
        echo 'check_boot: boot ID unreadable' >&2; return 92;
    }
    [ "$current_boot" = "$boot_id" ] || {
        echo 'check_boot: boot ID mismatch; no signalling or removal permitted' >&2; return 92;
    }
}
guard_boot() { guard_dir && check_boot; }
owned_pid() {
    [ "$1" != "$$" ] || return 1
    # Kernel-thread exe/cwd links exist to lstat but cannot be followed.
    # Read identity with shell builtins before any readlink/subshell per PID.
    [ "$1" != 2 ] || return 1
    pid_ppid=
    while read -r pid_key pid_value pid_rest; do
        if [ "$pid_key" = PPid: ]; then pid_ppid=$pid_value; break; fi
    done 2>/dev/null < "/proc/$1/status"
    [ -n "$pid_ppid" ] && [ "$pid_ppid" != 2 ] || return 1
    [ -L "/proc/$1/exe" ] || [ -L "/proc/$1/cwd" ] || return 1
    pid_exe=$(readlink "/proc/$1/exe" 2>/dev/null)
    pid_cwd=$(readlink "/proc/$1/cwd" 2>/dev/null)
    case "$pid_exe" in "$physical_run_dir"|"$physical_run_dir"/*) return 0 ;; esac
    case "$pid_cwd" in "$physical_run_dir"|"$physical_run_dir"/*) return 0 ;; esac
    return 1
}
snapshot() {
    IFS= read -r snapshot_boot < /proc/sys/kernel/random/boot_id || return 92
    printf 'BOOT\t%s\n' "$snapshot_boot"
    resolve_run_dir || return 91
    printf 'RUNDIR\t%s\n' "$physical_run_dir"
    {
    # Only admission needs the CPU map. Keep block separators for cpu_binding,
    # without shell read/printf commands for thousands of unused cpuinfo lines.
    if [ "${1:-}" != skip-cpu ]; then
        awk '/^processor[ \t]*:|^core id[ \t]*:/ {print "CPU\t" $0}
             /^$/ {print "CPU\t"}' /proc/cpuinfo
    fi
    awk '/^MemFree:/ {print "MEM\t" $0; exit}' /proc/meminfo
    set --
    for proc in /proc/[0-9]*; do
        proc_pid=${proc##*/}
        [ "$proc_pid" != "$$" ] || continue
        proc_ppid=
        while read -r proc_key proc_value proc_rest; do
            if [ "$proc_key" = PPid: ]; then proc_ppid=$proc_value; break; fi
        done 2>/dev/null < "$proc/status"
        # The control shell and its snapshot utilities are ours even before cd.
        # Match identities, never names that a foreign process could also use.
        # Name its other children (watchdog, launch shells): their descendants,
        # such as the watchdog's sleep, are ours on the host.
        if [ "$proc_ppid" = "$$" ]; then printf 'OWN\t%s\n' "$proc_pid"; continue; fi
        [ "$proc_pid" != 2 ] && [ "$proc_ppid" != 2 ] || continue
        printf 'IDENT\t%s\t%s\n' "$proc_pid" "$proc_ppid"
        set -- "$@" "$proc/exe" "$proc/cwd"
    done
    # One ls for all surviving user processes, no readlink/subshell per PID.
    # POSIX -q replaces control bytes (including tabs/newlines) with question
    # marks before awk sees them. The owned directory prefix is always ASCII.
    if [ "$#" -gt 0 ]; then LC_ALL=C ls -ldnq -- "$@" 2>/dev/null || :; fi
    } | awk '
        BEGIN { FS = "\t" }
        /^CPU\t|^MEM\t|^OWN\t/ { print; next }
        /^IDENT\t/ { ppid[$2] = $3; next }
        /^l/ && match($0, /\/[0-9]+\/(exe|cwd) -> /) {
            split(substr($0, RSTART, RLENGTH), link, "/")
            target = substr($0, RSTART + RLENGTH)
            if (link[3] == "exe -> ") exe[link[2]] = target
            else cwd[link[2]] = target
        }
        END {
            for (pid in ppid) {
                # Admit only with the parent from this same status read. The
                # earlier shell read may have raced or failed transiently.
                file = "/proc/" pid "/status"
                parent = ""
                while ((getline part < file) > 0) {
                    if (part ~ /^PPid:[ \t]+[0-9]+[ \t]*$/) {
                        split(part, status, /[ \t]+/)
                        parent = status[2]
                        break
                    }
                }
                close(file)
                if (pid == 2 || parent == 2) continue
                # Read comm directly in this one awk, preserving embedded line
                # breaks as ?. Never put raw comm bytes into the record stream.
                file = "/proc/" pid "/comm"
                name = ""; lines = 0
                while ((getline part < file) > 0) {
                    gsub(/[\t\r]/, "?", part)
                    name = name "" (lines++ ? "?" : "") part
                }
                close(file)
                tag = parent != "" && lines ? "PROC" : "SKIP"
                printf "%s\t%s\t%s\t%s\t%s\t%s\n", tag, pid, parent, name, exe[pid], cwd[pid]
            }
        }'
}
reap_one() {
    run_dir=$1
    case "$run_dir" in /tmp/knc-boinc/claude-????????????????????????????????) ;; *) return 0 ;; esac
    suffix=${run_dir##*/claude-}
    case "$suffix" in *[!0-9a-f]*) return 0 ;; esac
    [ ! -L "$run_dir" ] && [ -d "$run_dir" ] || return 0
    cd -- "$run_dir" || return 92
    guard_dir || return 0
    check_boot || return 92
    # A host interruption may leave a live SCIF endpoint or uncertain driver
    # cleanup. Only two successful endpoint close reports release this marker.
    if [ -e claude-dma-active ]; then
        printf 'STALE_KEPT\t%s\n' "$run_dir"
        return 0
    fi
    # Stale recovery never signals: any live user of this exact cwd/exe keeps it.
    for proc in /proc/[0-9]*; do
        if owned_pid "${proc##*/}"; then
            printf 'STALE_KEPT\t%s\n' "$run_dir"
            return 0
        fi
    done
    guard_boot || return 92
    rm -rf -- "$run_dir" || return 92
    printf 'REAPED\t%s\n' "$run_dir"
}
reap_stale() {
    check_boot || return 92
    reap_original=$run_dir
    reap_cwd=$PWD
    for stale_dir in /tmp/knc-boinc/claude-*; do
        reap_one "$stale_dir"
        reap_status=$?
        run_dir=$reap_original
        cd -- "$reap_cwd" || return 92
        [ "$reap_status" = 0 ] || return "$reap_status"
    done
    rmdir /tmp/knc-boinc 2>/dev/null || :
}
stop_owned() {
    guard_boot || return 92
    [ ! -e claude-dma-active ] || {
        echo 'SCIF endpoint cleanup unresolved; no signalling or removal' >&2
        return 93
    }
    for sig in TERM KILL; do
        for proc in /proc/[0-9]*; do
            proc_pid=${proc##*/}
            if owned_pid "$proc_pid"; then
                guard_boot || return 92
                # Recheck identity after the boot guard; never signal by name/group.
                if owned_pid "$proc_pid"; then
                    kill -"$sig" "$proc_pid" 2>/dev/null || :
                fi
            fi
        done
        [ "$sig" = KILL ] || sleep 1
    done
    # A surviving owned process makes removal unsafe (e.g. uninterruptible I/O).
    for proc in /proc/[0-9]*; do
        owned_pid "${proc##*/}" && return 93
    done
    return 0
}
cleanup() {
    check_boot || return 92
    # Admission may have refused before creating any remote directory.
    [ -e "$run_dir" ] || return 0
    stop_owned && guard_boot || return 92
    # No computed parent path, glob, symlink, or directory from another boot.
    rm -rf -- "$run_dir" || return 92
    rmdir /tmp/knc-boinc 2>/dev/null || :
}
start_job() {
    guard_boot && [ -f claude-watchdog.sh ] && [ -x claude-pin ] || return 92
    job_limit=$1
    job_cpus=$2
    job_memory=$3
    shift 3
    : > stdout
    : > stderr
    # Both background shells detach their SSH file descriptors and ignore HUP.
    # The watchdog survives a broken control connection and applies the same
    # exact-directory and boot guards as host-requested termination.
    (trap '' HUP; exec sh ./claude-watchdog.sh "$run_dir" "$boot_id" "$job_limit") \
        > /dev/null 2>&1 < /dev/null &
    (trap '' HUP
     printf claude-launch > /proc/self/comm
     ./claude-pin "$job_cpus" "$job_memory" ./claude-program "$@"
     printf '%s\n' "$?" > status) \
        > stdout 2> stderr < /dev/null &
}
