param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$PackageRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$Installer = Join-Path $PackageRoot 'install-windows.ps1'
$Uninstaller = Join-Path $PackageRoot 'uninstall-windows.ps1'
if (!(Test-Path -LiteralPath $Installer -PathType Leaf) -or !(Test-Path -LiteralPath $Uninstaller -PathType Leaf)) {
    throw 'Run setup-windows.ps1 from an extracted Blank Box release.'
}

Write-Host 'Blank Box Community setup'
Write-Host '  1) Install or update Blank Box'
Write-Host '  2) Uninstall Blank Box'
Write-Host '  3) Exit'
$Action = Read-Host 'Choose [1-3]'

if ($Action -eq '2') {
    & $Uninstaller
    exit 0
}
if ($Action -eq '3') { exit 0 }
if ($Action -ne '1') { throw 'Choose 1, 2, or 3.' }

$PortText = Read-Host 'Web port [25265]'
if ([string]::IsNullOrWhiteSpace($PortText)) { $Port = 25265 }
else {
    $Port = 0
    if (![int]::TryParse($PortText,[ref]$Port) -or $Port -lt 1024 -or $Port -gt 65535) { throw 'Use a port from 1024 to 65535.' }
}
$LanAnswer = Read-Host 'Allow devices on your trusted home network? [y/N]'
$LanAccess = $LanAnswer -match '^(y|yes)$'
$StartupAnswer = Read-Host 'Start Blank Box when you sign in? [Y/n]'
$RegisterStartup = $StartupAnswer -notmatch '^(n|no)$'

if ($RegisterStartup) { & $Installer -RegisterStartupTask }
else {
    & $Installer
    $TaskTool = Get-Command schtasks.exe -ErrorAction SilentlyContinue
    if ($TaskTool) { & $TaskTool.Source /Delete /F /TN 'Blank Box' 2>$null | Out-Null }
}

$InstallRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BlankBox'
$ConfigPath = Join-Path $InstallRoot 'config.json'
$Config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
$Config.host = if ($LanAccess) { '0.0.0.0' } else { '127.0.0.1' }
$Config.port = $Port
[IO.File]::WriteAllText($ConfigPath,(($Config | ConvertTo-Json -Depth 5) + [Environment]::NewLine),(New-Object Text.UTF8Encoding($false)))

Write-Host ''
Write-Host "Blank Box is configured on port $Port."
if ($LanAccess) {
    Write-Host "Open http://$([Environment]::MachineName):$Port from your trusted network."
    Write-Host 'If prompted, allow Python only on Private networks in Windows Firewall.'
} else {
    Write-Host "Open http://127.0.0.1:$Port on this computer."
}
Write-Host "Start command: powershell.exe -ExecutionPolicy Bypass -File `"$(Join-Path $InstallRoot 'start-windows.ps1')`""
Write-Host "Access key: $(Join-Path $InstallRoot 'data\access-key.txt')"
