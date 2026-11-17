[CmdletBinding()]
param(
    [ValidateSet('Install','Uninstall','Restore')][string]$Action = 'Install',
    [string]$BackupPath = '',
    [string]$TestRoot = ''
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Check-Package.ps1')
$Brand = 'knc-boinc-installer-v1'
$Marker = '.knc-boinc-install.json'
$script:Stopped = $false
$script:Backup = ''
$script:Mutation = $false
$script:Control = @{}
$script:Log = ''
function Write-Log($Message) { Add-Content -LiteralPath $script:Log -Value ((Get-Date -Format o) + ' ' + $Message) -Encoding UTF8 }
function Tell($Message, $ErrorDialog = $false) {
    Write-Log $Message
    if ($TestRoot) { return }
    $icon = if ($ErrorDialog) { 'Error' } else { 'Information' }
    [Windows.Forms.MessageBox]::Show($Message, 'KNC BOINC', 'OK', $icon) | Out-Null
}
function Confirm($Message) {
    Write-Log $Message
    if ($TestRoot) { return -not $script:Control.Cancel }
    return ([Windows.Forms.MessageBox]::Show($Message, 'KNC BOINC', 'YesNo', 'Question', 'Button2') -eq 'Yes')
}
function Full($Path) { return [IO.Path]::GetFullPath($Path).TrimEnd('\') }
function No-Links($Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Links/junctions are not supported: $Path" }
    if ($item.PSIsContainer) { foreach ($child in Get-ChildItem -LiteralPath $Path -Force) { No-Links $child.FullName } }
}
function Check-Ancestors($Path) {
    $p = Full $Path
    while ($p) {
        if (Test-Path -LiteralPath $p) {
            if ((Get-Item -LiteralPath $p -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked path: $p" }
        }
        $p = Split-Path -Parent $p
    }
}
function Copy-Tree($Source, $Destination) {
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) { Copy-Item -LiteralPath $item.FullName -Destination $Destination -Recurse -Force }
}
function Clear-Data {
    # All recursive deletes stay in this validated BOINC tree, using one shell.
    if ((Full $Data) -ne $script:ValidatedData) { throw 'BOINC target changed' }
    No-Links $Data
    foreach ($item in Get-ChildItem -LiteralPath $Data -Force) {
        $target = Full $item.FullName
        if (-not $target.StartsWith($script:ValidatedData + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe removal target' }
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}
function Read-Json($Path) { return ([IO.File]::ReadAllText($Path) | ConvertFrom-Json) }
function Save-Json($Path, $Value) { [IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 8)) }
function Hash($Path) { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash }
# Recognition is read-only. Persist adoption only after confirmation, shutdown and backup.
function Recognize-ManualInstall {
    $info = Join-Path $Project 'app_info.xml'
    if ($Action -ne 'Install' -or -not (Test-Path -LiteralPath $info -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $Project 'knc_wrapper.cfg') -PathType Leaf)) { return $null }
    $packageFiles = @(Assert-Package $Package)
    $installed = [IO.File]::ReadAllText($info).Replace("`r`n", "`n")
    $current = [IO.File]::ReadAllText((Join-Path $Package 'app_info.xml')).Replace("`r`n", "`n")
    $reason = 'package app_info (CRLF normalized)'
    if ($installed -cne $current) {
        # Earlier 196/mt packages may differ in formatting/copy/graphics metadata.
        # Identity, the sole main program, and BOTH file inventories must still match.
        try {
            $doc = New-Object Xml.XmlDocument; $doc.XmlResolver = $null; $doc.LoadXml($installed)
            $root = $doc.DocumentElement
            if ($root.Name -cne 'app_info' -or @($root.SelectNodes('app')).Count -ne 1 -or
                @($root.SelectNodes('app_version')).Count -ne 1) { return $null }
            $appNames = @($root.SelectNodes('app/name'))
            if ($appNames.Count -ne 1 -or $appNames[0].InnerText -cne 'milkyway_nbody') { return $null }
            $version = $root.SelectSingleNode('app_version')
            foreach ($entry in @(@('app_name','milkyway_nbody'), @('version_num','196'), @('plan_class','mt'), @('platform','windows_x86_64'))) {
                $nodes = @($version.SelectNodes($entry[0]))
                if ($nodes.Count -ne 1 -or $nodes[0].InnerText -cne $entry[1]) { return $null }
            }
            $mains = @($version.SelectNodes('file_ref[main_program]'))
            if ($mains.Count -ne 1 -or @($mains[0].SelectNodes('main_program')).Count -ne 1 -or
                $mains[0].SelectSingleNode('file_name').InnerText -cne 'knc_wrapper.exe') { return $null }
            $expected = @($packageFiles | Where-Object { $_ -cne 'app_info.xml' })
            foreach ($query in @('file_info/name','app_version/file_ref/file_name')) {
                $names = @($root.SelectNodes($query) | ForEach-Object { $_.InnerText })
                if ($names.Count -ne $expected.Count -or @(Compare-Object $expected $names -CaseSensitive).Count) { return $null }
            }
            if (@($root.SelectNodes('file_info')).Count -ne $expected.Count -or
                @($version.SelectNodes('file_ref')).Count -ne $expected.Count) { return $null }
        } catch { return $null }
        $reason = 'earlier knc-boinc app_info (milkyway_nbody 196/mt, wrapper and file list)'
    }
    $hashes = @{'app_info.xml'=(Hash $info)}
    $appConfig = Join-Path $Project 'app_config.xml'
    if (Test-Path -LiteralPath $appConfig) {
        # The manual install script wrote this same one-task config. Other configs stay foreign.
        try {
            $cfgDoc = New-Object Xml.XmlDocument; $cfgDoc.XmlResolver = $null; $cfgDoc.Load($appConfig)
            if ($cfgDoc.OuterXml -cne '<app_config><project_max_concurrent>1</project_max_concurrent></app_config>') { return $null }
        } catch { return $null }
        $hashes['app_config.xml'] = Hash $appConfig
    }
    Write-Log "Recognized manual installation: $reason; keep existing knc_wrapper.cfg"
    return [pscustomobject]@{Brand=$Brand;Files=@($packageFiles) + @('knc_wrapper.cfg','app_config.xml');Manifests=$hashes;Adopt=$true}
}
function Check-Ownership {
    $path = Join-Path $Project $Marker
    $owner = $null
    if (Test-Path -LiteralPath $path) {
        $owner = Read-Json $path
        if ($owner.Brand -ne $Brand -or -not $owner.Files -or -not $owner.Manifests) { throw 'Unrecognized/foreign installation marker' }
        foreach ($n in $owner.Files) {
            if ($n -notmatch '^[A-Za-z0-9_][A-Za-z0-9_.+-]*$' -or $n -in @('.','..',$Marker)) { throw 'Unsafe installation inventory' }
        }
    }
    if (-not $owner) {
        $adopt = Recognize-ManualInstall
        if ($adopt) { return $adopt }
    }
    foreach ($n in @('app_info.xml','app_config.xml')) {
        $manifest = Join-Path $Project $n
        if (Test-Path -LiteralPath $manifest) {
            if (-not $owner -or (Hash $manifest) -ne $owner.Manifests.$n) { throw "Existing foreign $n. Nothing changed. Move/review it with the lead before retrying." }
        } elseif ($owner) { throw "Missing owned $n; installation needs review." }
    }
    if (-not $owner -and (Test-Path -LiteralPath (Join-Path $Project 'knc_wrapper.cfg'))) { throw 'Existing foreign knc_wrapper.cfg. Nothing changed.' }
    if ($owner) {
        $manifest = New-Object Xml.XmlDocument; $manifest.XmlResolver = $null
        $manifest.Load((Join-Path $Project 'app_info.xml'))
        $expected = @('app_info.xml','app_config.xml','knc_wrapper.cfg') + @($manifest.SelectNodes('/app_info/file_info/name') | ForEach-Object { $_.InnerText })
        if (@($owner.Files).Count -ne $expected.Count -or @(Compare-Object $expected @($owner.Files) -CaseSensitive).Count) { throw 'Foreign installation inventory; nothing changed.' }
    }
    return $owner
}
function Choose-Settings {
    $defaults = @{
        Data='C:\ProgramData\BOINC'; Boinc=(Join-Path $env:ProgramFiles 'BOINC');
        host='192.168.1.100'; user='root'; ssh_key=(Join-Path $env:USERPROFILE '.ssh\xeon_phi_rsa');
        known_hosts='C:\Users\xuzhi\Documents\gcc_knc\.work\_state\card\known_hosts';
        remote_base='/tmp/claude/claude-knc-boinc'
    }
    $reg = Get-ItemProperty 'HKLM:\SOFTWARE\Space Sciences Laboratory, U.C. Berkeley\BOINC Setup' -ErrorAction SilentlyContinue
    if ($reg.DATADIR) { $defaults.Data = $reg.DATADIR }
    if ($reg.INSTALLDIR) { $defaults.Boinc = $reg.INSTALLDIR }
    $form = New-Object Windows.Forms.Form
    $form.Text = "KNC BOINC - $Action"; $form.Width = 760; $form.Height = 410; $form.StartPosition = 'CenterScreen'
    $fields = @{}; $y = 18
    foreach ($name in @('Data','Boinc','host','user','ssh_key','known_hosts','remote_base')) {
        $label = New-Object Windows.Forms.Label; $label.Text = $name; $label.Left = 12; $label.Top = $y + 4; $label.Width = 100
        $box = New-Object Windows.Forms.TextBox; $box.Left = 120; $box.Top = $y; $box.Width = 600; $box.Text = $defaults[$name]
        $fields[$name] = $box; $form.Controls.Add($label); $form.Controls.Add($box); $y += 37
    }
    $hint = New-Object Windows.Forms.Label; $hint.Text = 'Update keeps the installed wrapper config; card fields apply to first install only.'
    $hint.Left = 12; $hint.Top = $y; $hint.Width = 710; $form.Controls.Add($hint)
    $ok = New-Object Windows.Forms.Button; $ok.Text = 'Continue'; $ok.Left = 520; $ok.Top = $y + 30; $ok.DialogResult = 'OK'
    $cancel = New-Object Windows.Forms.Button; $cancel.Text = 'Cancel'; $cancel.Left = 630; $cancel.Top = $y + 30; $cancel.DialogResult = 'Cancel'
    $form.Controls.Add($ok); $form.Controls.Add($cancel); $form.AcceptButton = $ok; $form.CancelButton = $cancel
    if ($form.ShowDialog() -ne 'OK') { $form.Dispose(); return $null }
    foreach ($name in $fields.Keys) { $defaults[$name] = $fields[$name].Text.Trim() }
    $form.Dispose(); return $defaults
}
function Check-Card($Config) {
    $cfg = @{}
    foreach ($line in ($Config -split "`r?`n")) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z_0-9]*)=(.*)$') { $cfg[$matches[1]] = $matches[2].Trim() }
    }
    foreach ($key in @('host','user','ssh_key','known_hosts','ssh_path','scp_path')) {
        if (-not $cfg[$key]) { throw "Missing wrapper setting: $key" }
    }
    if ($TestRoot) { Write-Log 'TEST: card prerequisite adapter'; return }
    foreach ($key in @('ssh_key','known_hosts','ssh_path','scp_path')) {
        if (-not (Test-Path -LiteralPath $cfg[$key] -PathType Leaf)) { throw "Not found: $key = $($cfg[$key])" }
    }
    if ($cfg.host -notmatch '^[A-Za-z0-9][A-Za-z0-9.:-]*$' -or $cfg.user -notmatch '^[A-Za-z0-9_][A-Za-z0-9_.-]*$') { throw 'Invalid SSH host/user' }
    $args = @('-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',
        '-o','ConnectionAttempts=1','-o',('UserKnownHostsFile="' + $cfg.known_hosts + '"'),'-i',$cfg.ssh_key,
        ($cfg.user + '@' + $cfg.host),'uname -m')
    $output = & $cfg.ssh_path @args 2>&1
    $code = $LASTEXITCODE
    Write-Log ("SSH exit $code : " + ($output -join ' '))
    if ($code -ne 0 -or ($output -join "`n").Trim() -ne 'k1om') { throw 'Card check failed (expected k1om). Check SSH key and known_hosts permissions for the BOINC login.' }
}
function Stop-Boinc {
    if ($TestRoot) {
        Add-Content -LiteralPath (Join-Path $TestRoot 'events.log') 'quit'
        if ($script:Control.StopTimeout) { throw 'BOINC still running; nothing changed. No process was killed.' }
        $script:Stopped = $true; return
    }
    if (Get-Process -Name boinc -ErrorAction SilentlyContinue) {
        Write-Log 'Requesting graceful boinccmd --quit'
        Push-Location $Data
        try {
            # Windows boinccmd changes cwd to its registry data directory. Supply the
            # selected directory's credential explicitly; never log it or the argv.
            $password = [IO.File]::ReadAllText((Join-Path $Data 'gui_rpc_auth.cfg')).Trim()
            $rpcArgs = @('--host','localhost')
            if ($password) { $rpcArgs += @('--passwd', $password) }
            $rpcArgs += '--quit'
            $output = & (Join-Path $Boinc 'boinccmd.exe') @rpcArgs 2>&1
            Write-Log ("boinccmd exit $LASTEXITCODE : " + ($output -join ' '))
            if ($LASTEXITCODE -ne 0) { throw 'BOINC refused graceful shutdown. Check RPC access; no files changed.' }
        } finally { Pop-Location }
        $deadline = (Get-Date).AddSeconds(90)
        while (Get-Process -Name boinc -ErrorAction SilentlyContinue) {
            if ((Get-Date) -ge $deadline) { throw 'BOINC still running after 90 seconds. No process was killed. Close the client in Manager and retry.' }
            Start-Sleep -Milliseconds 500
        }
    }
    $script:Stopped = $true
}
function Assert-Stopped {
    if (-not $TestRoot -and (Get-Process -Name boinc -ErrorAction SilentlyContinue)) { throw 'BOINC restarted during installation. Files cannot be changed safely.' }
}
function Start-Boinc {
    if ($TestRoot) { Add-Content -LiteralPath (Join-Path $TestRoot 'events.log') 'start'; $script:Stopped = $false; return }
    if ($script:Service) { Start-Service -Name $script:Service.Name }
    # Use the interactive Explorer shell so BOINC does not inherit our elevated token.
    $shell = New-Object -ComObject Shell.Application
    $hwnd = 0
    $desktop = $shell.Windows().FindWindowSW(0, 0, 8, [ref]$hwnd, 1)
    if (-not $desktop) { throw 'Unable to reach the interactive Windows desktop; open BOINC Manager from Start.' }
    $launcher = $desktop.Document.Application
    if (-not $script:Service -and -not (Get-Process -Name boinc -ErrorAction SilentlyContinue)) {
        $launcher.ShellExecute((Join-Path $Boinc 'boinc.exe'), ('--dir "' + $Data + '"'), $Boinc, 'open', 0)
    }
    $launcher.ShellExecute((Join-Path $Boinc 'boincmgr.exe'), '', $Boinc, 'open', 1)
    $script:Stopped = $false
    Write-Log 'Requested client/Manager restart through interactive desktop'
}
function Make-Backup {
    Assert-Stopped
    No-Links $Data
    $path = Join-Path $BackupRoot ((Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8))
    Copy-Tree $Data (Join-Path $path 'data')
    $files = @(Get-ChildItem -LiteralPath (Join-Path $path 'data') -File -Recurse -Force | ForEach-Object {
        @{Path=$_.FullName.Substring((Join-Path $path 'data').Length + 1); Hash=(Hash $_.FullName)}
    })
    Save-Json (Join-Path $path 'backup.json') @{Brand=$Brand;Data=$Data;Files=$files;Created=(Get-Date -Format o)}
    Write-Log "Full data backup: $path"
    return $path
}
function Validate-Backup($Path) {
    $fullBackup = Full $Path
    if ($fullBackup -eq $Data -or $fullBackup.StartsWith($Data + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase) -or $Data.StartsWith($fullBackup + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Backup must be outside and separate from the BOINC data tree.' }
    Check-Ancestors $Path; No-Links $Path
    $meta = Read-Json (Join-Path $Path 'backup.json')
    if ($meta.Brand -ne $Brand -or (Full $meta.Data) -ne $Data -or -not $meta.Files) { throw 'Backup identity/data directory does not match.' }
    $tree = Join-Path $Path 'data'
    if (@(Get-ChildItem -LiteralPath $tree -Recurse -File -Force).Count -ne @($meta.Files).Count) { throw 'Backup inventory mismatch' }
    foreach ($file in $meta.Files) {
        $p = Full (Join-Path $tree $file.Path)
        if (-not $p.StartsWith((Full $tree) + '\', [StringComparison]::OrdinalIgnoreCase) -or (Hash $p) -ne $file.Hash) { throw 'Backup checksum/path mismatch' }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $tree 'client_state.xml'))) { throw 'Backup lacks client_state.xml' }
}
try {
    if ($TestRoot) {
        # Test mode is confined to fixtures in this checkout, with fixed child paths.
        $Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
        $allowed = (Full (Join-Path $Repo 'build\installer-tests')) + '\'
        $TestRoot = Full $TestRoot
        if (-not $TestRoot.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase) -or
            -not (Test-Path -LiteralPath (Join-Path $TestRoot '.test-only'))) { throw 'Invalid test fixture root' }
        Check-Ancestors $TestRoot; No-Links $TestRoot
        $Data = Join-Path $TestRoot 'data'; $Package = Join-Path $TestRoot 'package'; $Boinc = Join-Path $TestRoot 'fake-boinc'
        $BackupRoot = Join-Path $TestRoot 'backups'; $LogRoot = Join-Path $TestRoot 'logs'
        if (Test-Path (Join-Path $TestRoot 'control.json')) { $script:Control = Read-Json (Join-Path $TestRoot 'control.json') }
    } else {
        Add-Type -AssemblyName System.Windows.Forms
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        if (-not (New-Object Security.Principal.WindowsPrincipal($identity)).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Use the double-click launcher to approve UAC elevation.' }
        $LogRoot = $PSScriptRoot
        $BackupRoot = Join-Path $PSScriptRoot 'backups'; $Package = Join-Path $PSScriptRoot 'package'
    }
    New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
    $script:Log = Join-Path $LogRoot ('KNC-' + $Action + '-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N').Substring(0,8) + '.log')
    Write-Log "Start $Action (test=$([bool]$TestRoot))"
    if (-not $TestRoot) {
        $settings = Choose-Settings
        if (-not $settings) { Write-Log 'Cancelled settings'; return }
        $Data = Full $settings.Data; $Boinc = Full $settings.Boinc
    }
    $Data = Full $Data; $script:ValidatedData = $Data
    $Project = Join-Path $Data 'projects\milkyway.cs.rpi.edu_milkyway'
    Check-Ancestors $Data; No-Links $Data
    if (-not (Test-Path -LiteralPath $Project -PathType Container)) { throw "MilkyWay project folder missing: $Project. Attach to MilkyWay in BOINC Manager first." }
    $state = New-Object Xml.XmlDocument; $state.XmlResolver = $null; $state.Load((Join-Path $Data 'client_state.xml'))
    if (-not @($state.SelectNodes('/client_state/project/master_url') | Where-Object { $_.InnerText -match '^https?://milkyway\.cs\.rpi\.edu/milkyway/?$' }).Count) { throw 'BOINC is not attached to MilkyWay.' }
    if ((Full $BackupRoot) -eq $Data -or (Full $PSScriptRoot) -eq $Data -or (Full $BackupRoot).StartsWith($Data + '\', [StringComparison]::OrdinalIgnoreCase) -or (Full $PSScriptRoot).StartsWith($Data + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Keep the installer and backups outside the BOINC data tree.' }
    Check-Ancestors $BackupRoot
    if (-not $TestRoot) {
        foreach ($n in @('boinc.exe','boinccmd.exe','boincmgr.exe')) { if (-not (Test-Path -LiteralPath (Join-Path $Boinc $n) -PathType Leaf)) { throw "BOINC is not installed here: $Boinc ($n missing)" } }
        $script:Service = Get-Service -Name BOINC -ErrorAction SilentlyContinue
    }
    $owner = Check-Ownership
    if ($Action -eq 'Install') {
        No-Links $Package
        $files = @(Assert-Package $Package)
        Write-Log "PASS package check: $($files.Count) files, milkyway_nbody 196/mt, 1 host CPU"
        foreach ($n in $files) {
            if ((Test-Path -LiteralPath (Join-Path $Project $n)) -and (-not $owner -or $n -notin $owner.Files)) { throw "Existing foreign package file $n. Nothing changed." }
        }
        $cfgPath = Join-Path $Project 'knc_wrapper.cfg'
        if ($owner -and (Test-Path -LiteralPath $cfgPath)) { $config = [IO.File]::ReadAllText($cfgPath) }
        else {
            if ($TestRoot) { $settings = @{host='fake-card';user='fixture';ssh_key='fake-key';known_hosts='fake-hosts';remote_base='/tmp/test'} }
            $config = @"
host=$($settings.host)
user=$($settings.user)
ssh_key=$($settings.ssh_key)
known_hosts=$($settings.known_hosts)
ssh_path=$env:WINDIR/System32/OpenSSH/ssh.exe
scp_path=$env:WINDIR/System32/OpenSSH/scp.exe
remote_base=$($settings.remote_base)
package_dir=.
app=milkyway_nbody.mic
OMP_NUM_THREADS=240
poll_interval=10
snapshot_interval=5
connect_timeout=10
retry_limit=3
checkpoint_timeout=60
"@
        }
        Check-Card $config
    } elseif ($Action -eq 'Uninstall' -and -not $owner) { throw 'No owned KNC installation found; nothing changed.' }
    if ($Action -eq 'Restore') {
        if (-not $BackupPath -and -not $TestRoot) {
            $picker = New-Object Windows.Forms.FolderBrowserDialog
            $picker.Description = 'Select a KNC backup folder containing backup.json and data (restores ALL BOINC state).'
            $picker.SelectedPath = $BackupRoot
            if ($picker.ShowDialog() -ne 'OK') { Write-Log 'Cancelled backup selection'; return }
            $BackupPath = $picker.SelectedPath; $picker.Dispose()
        }
        $BackupPath = Full $BackupPath
        Validate-Backup $BackupPath
    }
    $detail = if ($Action -eq 'Install' -and $owner) { 'Update binaries; keep your wrapper config.' } elseif ($Action -eq 'Install') { 'Install the KNC package and one-task concurrency config.' } elseif ($Action -eq 'Uninstall') { 'Remove only the recorded KNC files and configs. Keep stock files and task state.' } else { "Replace ALL current BOINC data with: $BackupPath. Old state can replay already reported results; restore only a suitable backup." }
    if (-not (Confirm "$detail`r`n`r`nData: $Data`r`nThe installer will request a graceful BOINC shutdown, wait up to 90 seconds, back up the entire data directory, then restart BOINC Manager. No running science process will be killed. Continue?")) { Write-Log 'Cancelled confirmation'; return }
    Stop-Boinc
    $owner = Check-Ownership
    $script:Backup = Make-Backup
    Assert-Stopped
    $script:Mutation = $true
    if ($Action -eq 'Restore') {
        Validate-Backup $BackupPath
        Clear-Data; Copy-Tree (Join-Path $BackupPath 'data') $Data
    } else {
        if ($owner) {
            if ($owner.Adopt) {
                Save-Json (Join-Path $Project $Marker) @{Brand=$owner.Brand;Files=$owner.Files;Manifests=$owner.Manifests}
                Write-Log 'Adopted manual installation: ownership marker/inventory written; updating normally'
            }
            foreach ($n in $owner.Files) {
                if ($Action -eq 'Install' -and $n -eq 'knc_wrapper.cfg') { continue }
                $target = Join-Path $Project $n
                if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
            }
            Remove-Item -LiteralPath (Join-Path $Project $Marker) -Force
        }
        if ($Action -eq 'Install') {
            foreach ($n in $files) { Copy-Item -LiteralPath (Join-Path $Package $n) -Destination (Join-Path $Project $n) -Force }
            if ($script:Control.FailAfterCopy) { throw 'injected copy failure' }
            if (-not (Test-Path -LiteralPath $cfgPath)) { [IO.File]::WriteAllText($cfgPath, $config.Replace("`r`n", "`n")) }
            [IO.File]::WriteAllText((Join-Path $Project 'app_config.xml'), "<app_config>`n  <project_max_concurrent>1</project_max_concurrent>`n</app_config>`n")
            $hashes = @{}; foreach ($n in @('app_info.xml','app_config.xml')) { $hashes[$n] = Hash (Join-Path $Project $n) }
            Save-Json (Join-Path $Project $Marker) @{Brand=$Brand; Files=@($files) + @('knc_wrapper.cfg','app_config.xml'); Manifests=$hashes}
        }
    }
    $script:Mutation = $false
    Start-Boinc
    if ($TestRoot) { Save-Json (Join-Path $TestRoot 'last-result.json') @{Action=$Action;Backup=$script:Backup} }
    Tell "$Action completed.`r`nBackup: $script:Backup`r`nLog: $script:Log`r`nKeep No new tasks selected and review Manager's Event Log before resuming science."
} catch {
    $message = $_.ToString()
    if ($script:Log) {
        Write-Log "FAIL: $message"
        if ($script:Mutation -and $script:Backup) {
            try { Assert-Stopped; Validate-Backup $script:Backup; Clear-Data; Copy-Tree (Join-Path $script:Backup 'data') $Data; Write-Log 'Rolled back failed operation' }
            catch { $script:Stopped = $false; $message += "`r`nAutomatic rollback failed: $_. Leave BOINC stopped and restore backup: $script:Backup" }
        }
        if ($script:Stopped) { try { Start-Boinc } catch { $message += "`r`nRestart failed: $_" } }
        Tell ("$message`r`nBackup: $script:Backup`r`nLog: $script:Log") $true
    } elseif (-not $TestRoot) { [Windows.Forms.MessageBox]::Show($message, 'KNC BOINC', 'OK', 'Error') | Out-Null }
    if ($TestRoot) { throw $message }
    exit 1
}
