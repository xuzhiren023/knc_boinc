param([ValidateSet('Install','Uninstall','Restore')][string]$Action = 'Install')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
$log = Join-Path $PSScriptRoot ('KNC-launch-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N') + '.log')
try {
    Set-Content -LiteralPath $log -Value ("Launching $Action; requesting administrator approval.")
    $powershell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $installer = Join-Path $PSScriptRoot 'Installer.ps1'
    # File path is double-quoted for CreateProcess, never embedded in executable PowerShell text.
    if ($installer.Contains('"')) { throw 'Invalid installer folder path' }
    $args = '-NoProfile -STA -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $installer + '" -Action ' + $Action
    $process = Start-Process -FilePath $powershell -Verb RunAs -WindowStyle Hidden -ArgumentList $args -Wait -PassThru
    Add-Content -LiteralPath $log -Value ("Installer exit: " + $process.ExitCode)
} catch {
    Add-Content -LiteralPath $log -Value $_.ToString()
    [Windows.Forms.MessageBox]::Show(("Installer could not start or UAC was cancelled.`r`n" + $_ + "`r`nLog: " + $log), 'KNC BOINC', 'OK', 'Error') | Out-Null
    exit 1
}
