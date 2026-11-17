# Owner-run (PowerShell): install the knc-boinc anonymous-platform package into the local BOINC data directory.
# Run from the knc-boinc folder with BOINC stopped. Backs up the BOINC data directory first.
$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
$BoincData = 'C:\ProgramData\BOINC'
$Package = Join-Path $Repo 'dist\milkyway_package'
$Project = Join-Path $BoincData 'projects\milkyway.cs.rpi.edu_milkyway'

if (Get-Process -Name boinc -ErrorAction SilentlyContinue) {
    Write-Error 'BOINC is still running. In BOINC Manager use File > Exit (stop running tasks), then run this again.'
}
if (-not (Test-Path $Project)) { Write-Error "Project folder not found: $Project" }
if ((Test-Path (Join-Path $Project 'app_info.xml')) -or (Test-Path (Join-Path $Project 'app_config.xml'))) {
    Write-Error "Existing app_info.xml or app_config.xml in ${Project}: not overwriting. Tell the lead."
}
python (Join-Path $Repo 'packaging\check_package.py') $Package
if ($LASTEXITCODE -ne 0) { Write-Error 'Package check failed.' }

$Backup = Join-Path $Repo ("build\boinc-backup-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Force $Backup | Out-Null
Copy-Item -Path (Join-Path $BoincData '*') -Destination $Backup -Recurse -Force
Write-Host "Backup: $Backup"

Copy-Item -Path (Join-Path $Package '*') -Destination $Project -Force
$cfg = @'
host=192.168.1.100
user=root
ssh_key=C:/Users/xuzhi/.ssh/xeon_phi_rsa
known_hosts=C:/Users/xuzhi/Documents/gcc_knc/.work/_state/card/known_hosts
ssh_path=C:/Windows/System32/OpenSSH/ssh.exe
scp_path=C:/Windows/System32/OpenSSH/scp.exe
remote_base=/tmp/claude/claude-knc-boinc
package_dir=.
app=milkyway_nbody.mic
OMP_NUM_THREADS=240
poll_interval=10
snapshot_interval=5
connect_timeout=10
retry_limit=3
checkpoint_timeout=60
'@
[System.IO.File]::WriteAllText((Join-Path $Project 'knc_wrapper.cfg'), $cfg.Replace("`r`n", "`n"))
$appConfig = "<app_config>`n  <project_max_concurrent>1</project_max_concurrent>`n</app_config>`n"
[System.IO.File]::WriteAllText((Join-Path $Project 'app_config.xml'), $appConfig)
Write-Host "Installed into $Project"
Write-Host 'Next: start BOINC Manager, check the Event Log, keep other tasks suspended, and tell the lead before resuming 117676.'
