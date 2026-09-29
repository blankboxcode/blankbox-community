param(
    [string]$InstallRoot = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BlankBox'),
    [switch]$RestorePreUpgradeCatalog
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)

function Get-BlankBoxPython([string]$Root) {
    if ([Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([Runtime.InteropServices.OSPlatform]::Windows)) {
        $bundled = Join-Path $Root 'runtime/windows/python.exe'
        if (Test-Path -LiteralPath $bundled -PathType Leaf) { return @{ Command = $bundled; Prefix = @() } }
    }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return @{ Command = $py.Source; Prefix = @('-3') } }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return @{ Command = $python.Source; Prefix = @() } }
    $python3 = Get-Command python3 -ErrorAction SilentlyContinue
    if ($python3) { return @{ Command = $python3.Source; Prefix = @() } }
    throw 'Python 3.10 or newer was not found.'
}
function Invoke-Core([hashtable]$Python,[string[]]$Arguments,[switch]$AllowFailure) {
    $all = @($Python.Prefix) + $Arguments
    $output = & $Python.Command @all
    if (!$AllowFailure -and $LASTEXITCODE -ne 0) { throw "Blank Box command failed with exit code $LASTEXITCODE." }
    return @{ ExitCode = $LASTEXITCODE; Output = $output }
}
function Write-Utf8NoBom([string]$Path,[string]$Value) {
    [IO.File]::WriteAllText($Path,$Value,(New-Object Text.UTF8Encoding($false)))
}

$configFile = Join-Path $InstallRoot 'config.json'
$currentFile = Join-Path $InstallRoot 'current.json'
if (!(Test-Path -LiteralPath $configFile -PathType Leaf) -or !(Test-Path -LiteralPath $currentFile -PathType Leaf)) { throw 'Blank Box is not installed.' }
$current = [IO.Path]::GetFullPath([string](Get-Content -LiteralPath $currentFile -Raw | ConvertFrom-Json).release)
$python = Get-BlankBoxPython $current
$maintenance = Join-Path $current 'maintenance.py'
$config = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json
$data = [IO.Path]::GetFullPath([string]$config.data)
$pidFile = Join-Path $data 'blankbox.pid'
if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
    $recorded = 0
    if ([int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$recorded) -and (Get-Process -Id $recorded -ErrorAction SilentlyContinue)) { throw "Stop Blank Box process $recorded before rollback." }
    Remove-Item -LiteralPath $pidFile -Force
}

$status = (Invoke-Core $python @($maintenance,'state-field','--config',$configFile,'--field','status')).Output | Select-Object -Last 1
$previous = (Invoke-Core $python @($maintenance,'state-field','--config',$configFile,'--field','previousRelease')).Output | Select-Object -Last 1
$activated = (Invoke-Core $python @($maintenance,'state-field','--config',$configFile,'--field','currentRelease')).Output | Select-Object -Last 1
$preUpgrade = (Invoke-Core $python @($maintenance,'state-field','--config',$configFile,'--field','catalogBackup')).Output | Select-Object -Last 1
if ($status -ne 'active' -or [IO.Path]::GetFullPath([string]$activated) -ne $current) { throw 'The installed release is not in an active rollback state.' }
$previous = [IO.Path]::GetFullPath([string]$previous)
$releasesRoot = [IO.Path]::GetFullPath((Join-Path $InstallRoot 'releases')) + [IO.Path]::DirectorySeparatorChar
if (!$previous.StartsWith($releasesRoot,[StringComparison]::OrdinalIgnoreCase) -or !(Test-Path -LiteralPath (Join-Path $previous 'doctor.py') -PathType Leaf)) { throw 'The previous managed release is unavailable.' }

$upgrades = Join-Path $data 'upgrades';New-Item -ItemType Directory -Force -Path $upgrades | Out-Null
$emergencyName = 'pre-rollback-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '.sqlite3'
$emergencyResult = Invoke-Core $python @($maintenance,'backup','--config',$configFile,'--destination',(Join-Path $upgrades $emergencyName))
$emergency = [string]($emergencyResult.Output | Select-Object -Last 1)
$compatible = Invoke-Core $python @((Join-Path $previous 'doctor.py'),'--config',$configFile) -AllowFailure
$restored = $false
if ($compatible.ExitCode -ne 0) {
    if (!$RestorePreUpgradeCatalog) { throw 'The previous Core cannot read the current catalog. Re-run with -RestorePreUpgradeCatalog only if losing post-upgrade catalog changes is acceptable.' }
    if (!$preUpgrade -or !(Test-Path -LiteralPath ([string]$preUpgrade) -PathType Leaf)) { throw 'The verified pre-upgrade catalog backup is unavailable.' }
    Invoke-Core $python @($maintenance,'restore','--config',$configFile,'--backup',[string]$preUpgrade) | Out-Null
    $restored = $true
    $compatible = Invoke-Core $python @((Join-Path $previous 'doctor.py'),'--config',$configFile) -AllowFailure
    if ($compatible.ExitCode -ne 0) {
        if ($emergency) { Invoke-Core $python @($maintenance,'restore','--config',$configFile,'--backup',$emergency) | Out-Null }
        throw 'The previous release failed diagnostics after catalog restoration. No code switch was made.'
    }
}

$pending = Join-Path $InstallRoot ('.current.' + [guid]::NewGuid().ToString('N') + '.json')
try {
    Write-Utf8NoBom $pending ((@{ release = $previous } | ConvertTo-Json) + [Environment]::NewLine)
    Move-Item -LiteralPath $pending -Destination $currentFile -Force
    $arguments = @($maintenance,'write-state','--config',$configFile,'--previous',$current,'--current',$previous,'--status','rolled-back')
    if ($emergency) { $arguments += @('--backup',$emergency) }
    Invoke-Core $python $arguments | Out-Null
} catch {
    Write-Utf8NoBom $currentFile ((@{ release = $current } | ConvertTo-Json) + [Environment]::NewLine)
    if ($restored -and $emergency) { Invoke-Core $python @($maintenance,'restore','--config',$configFile,'--backup',$emergency) | Out-Null }
    throw
} finally {
    Remove-Item -LiteralPath $pending -Force -ErrorAction SilentlyContinue
}

if ($restored) { Write-Host "Rolled back to $previous with the pre-upgrade catalog. Emergency newer-catalog backup: $emergency" }
else { Write-Host "Rolled back to $previous and preserved the current compatible catalog." }
