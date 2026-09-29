param(
    [string]$InstallRoot = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BlankBox'),
    [switch]$RemoveData,
    [switch]$PreserveData,
    [string]$ConfirmDataRemoval = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
if ($RemoveData -and $PreserveData) { throw 'Choose either -RemoveData or -PreserveData, not both.' }
$DataPath = Join-Path $InstallRoot 'data'
$PidFile = Join-Path $DataPath 'blankbox.pid'
if (Test-Path -LiteralPath $PidFile -PathType Leaf) {
    $Recorded = 0
    if ([int]::TryParse((Get-Content -LiteralPath $PidFile -Raw).Trim(),[ref]$Recorded) -and (Get-Process -Id $Recorded -ErrorAction SilentlyContinue)) {
        throw "Stop Blank Box process $Recorded before uninstalling."
    }
}

if (!$RemoveData -and !$PreserveData -and [Environment]::UserInteractive) {
    Write-Host 'The normal uninstall preserves configuration and library data.'
    $Answer = Read-Host 'Also permanently delete the catalog, key, and imported media? [y/N]'
    if ($Answer -match '^(y|yes)$') {
        $ConfirmDataRemoval = Read-Host 'Type DELETE BLANK BOX DATA to continue'
        if ($ConfirmDataRemoval -ne 'DELETE BLANK BOX DATA') { Write-Host 'Data deletion cancelled.'; exit 1 }
        $RemoveData = $true
    }
}
if ($RemoveData -and $ConfirmDataRemoval -ne 'DELETE BLANK BOX DATA') {
    throw 'Refusing data removal without the exact confirmation phrase.'
}

$TaskTool = Get-Command schtasks.exe -ErrorAction SilentlyContinue
if ($TaskTool) {
    $TaskXml = & $TaskTool.Source /Query /TN 'Blank Box' /XML 2>$null
    if ($LASTEXITCODE -eq 0 -and ($TaskXml -join '') -match [regex]::Escape($InstallRoot)) {
        & $TaskTool.Source /Delete /F /TN 'Blank Box' 2>$null | Out-Null
    }
}
Write-Host 'Blank Box startup was removed. All application, configuration, library, and other files were retained.'
Write-Host "Retained: $InstallRoot"
if ($RemoveData) { Write-Host 'Inspect and remove only the intended catalog/media files manually after verifying a separate backup.' }
