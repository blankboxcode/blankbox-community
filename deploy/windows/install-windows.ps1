param(
    [string]$InstallRoot = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BlankBox'),
    [switch]$RegisterStartupTask
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$PackageRoot = [IO.Path]::GetFullPath($PSScriptRoot)
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
    throw 'This package does not include its Windows runtime and Python 3.10 or newer was not found. Use the Blank Box Windows x64 offline package.'
}

function Invoke-BlankBoxPython([string[]]$Arguments) {
    $all = @($script:Python.Prefix) + $Arguments
    & $script:Python.Command @all
    if ($LASTEXITCODE -ne 0) { throw "Blank Box Python command failed with exit code $LASTEXITCODE." }
}

function Write-Utf8NoBom([string]$Path,[string]$Value) {
    [IO.File]::WriteAllText($Path,$Value,(New-Object Text.UTF8Encoding($false)))
}

function Test-ReleaseManifest([string]$Root) {
    $manifest = Join-Path $Root 'MANIFEST.sha256'
    if (!(Test-Path -LiteralPath $manifest -PathType Leaf)) { throw 'MANIFEST.sha256 is missing.' }
    $rootPrefix = [IO.Path]::GetFullPath($Root) + [IO.Path]::DirectorySeparatorChar
    foreach ($line in Get-Content -LiteralPath $manifest) {
        if ($line -notmatch '^([a-f0-9]{64})  (.+)$') { throw "Invalid manifest line: $line" }
        $expected = $Matches[1]
        $relative = $Matches[2] -replace '/', [IO.Path]::DirectorySeparatorChar
        if ([IO.Path]::IsPathRooted($relative) -or $relative.Split([IO.Path]::DirectorySeparatorChar) -contains '..') { throw "Unsafe manifest path: $relative" }
        $path = [IO.Path]::GetFullPath((Join-Path $Root $relative))
        if (!$path.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase) -or !(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Manifest file is missing: $relative" }
        if ((Get-Item -LiteralPath $path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Manifest file cannot be a reparse point: $relative" }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { throw "Manifest checksum failed: $relative" }
    }
}

$packagePrefix = $PackageRoot + [IO.Path]::DirectorySeparatorChar
$installPrefix = $InstallRoot + [IO.Path]::DirectorySeparatorChar
if ($InstallRoot.Equals($PackageRoot,[StringComparison]::OrdinalIgnoreCase) -or $InstallRoot.StartsWith($packagePrefix,[StringComparison]::OrdinalIgnoreCase) -or $PackageRoot.StartsWith($installPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'The installation directory and extracted release package must not contain one another.' }
foreach ($required in @('server.py','doctor.py','maintenance.py','MANIFEST.sha256','VERSION','deploy/windows/start-windows.ps1','deploy/windows/rollback-windows.ps1','deploy/windows/uninstall-windows.ps1')) {
    if (!(Test-Path -LiteralPath (Join-Path $PackageRoot $required) -PathType Leaf)) { throw "Release file is missing: $required" }
}
$env:PYTHONDONTWRITEBYTECODE = "1"
Test-ReleaseManifest $PackageRoot
$script:Python = Get-BlankBoxPython $PackageRoot
Invoke-BlankBoxPython @('-c','import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)')
Invoke-BlankBoxPython @((Join-Path $PackageRoot 'release_files.py'),$PackageRoot)
Invoke-BlankBoxPython @('-c','import sys; sys.path.insert(0,sys.argv[1]); from file_safety import reject_links; [reject_links(p) for p in sys.argv[2:]]',$PackageRoot,$InstallRoot,(Join-Path $InstallRoot 'config.json'),(Join-Path $InstallRoot 'current.json'),(Join-Path $InstallRoot 'releases'))

$manifestHash = (Get-FileHash -LiteralPath (Join-Path $PackageRoot 'MANIFEST.sha256') -Algorithm SHA256).Hash.ToLowerInvariant()
$releaseVersion = (Get-Content -LiteralPath (Join-Path $PackageRoot 'VERSION') -Raw).Trim()
if ($releaseVersion -notmatch '^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$') { throw 'VERSION is invalid.' }
$releaseId = $releaseVersion + '-' + $manifestHash.Substring(0,12)
if (Test-Path -LiteralPath $InstallRoot) {
    if ((Get-Item -LiteralPath $InstallRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'InstallRoot cannot be a reparse point.' }
    if (!(Test-Path -LiteralPath (Join-Path $InstallRoot 'current.json')) -and (Get-ChildItem -LiteralPath $InstallRoot -Force | Where-Object { $_.Name -notin @('data','config.json') })) { throw 'Choose an empty directory or an existing managed installation. Existing files were preserved.' }
}
$releasesRoot = Join-Path $InstallRoot 'releases'
$release = Join-Path $releasesRoot $releaseId
$configFile = Join-Path $InstallRoot 'config.json'
$currentFile = Join-Path $InstallRoot 'current.json'
$previous = $null
if (Test-Path -LiteralPath $currentFile -PathType Leaf) {
    $savedCurrent = Get-Content -LiteralPath $currentFile -Raw | ConvertFrom-Json
    $previous = [IO.Path]::GetFullPath([string]$savedCurrent.release)
    $releasePrefix = [IO.Path]::GetFullPath($releasesRoot) + [IO.Path]::DirectorySeparatorChar
    if (!$previous.StartsWith($releasePrefix,[StringComparison]::OrdinalIgnoreCase) -or !(Test-Path -LiteralPath $previous -PathType Container)) { throw 'The selected existing release is outside the managed release directory.' }
}
foreach ($name in @('start-windows.ps1','rollback-windows.ps1','uninstall-windows.ps1')) {
    $launcher = Join-Path $InstallRoot $name
    Invoke-BlankBoxPython @('-c','import sys; sys.path.insert(0,sys.argv[1]); from file_safety import reject_links; reject_links(sys.argv[2])',$PackageRoot,$launcher)
    if (Test-Path -LiteralPath $launcher) {
        $original = if ($previous) { Join-Path $previous $name } else { Join-Path $PackageRoot $name }
        if (!(Test-Path -LiteralPath $original -PathType Leaf) -or (Get-FileHash -LiteralPath $launcher).Hash -ne (Get-FileHash -LiteralPath $original).Hash) {
            throw "Existing customized launcher was preserved: $launcher. Save it separately before deliberately replacing it."
        }
    }
}
New-Item -ItemType Directory -Force -Path $releasesRoot | Out-Null

if (!(Test-Path -LiteralPath $release -PathType Container)) {
    $staging = Join-Path $releasesRoot ('.' + $releaseId + '.installing')
    if (Test-Path -LiteralPath $staging) { throw "Incomplete staging directory already exists: $staging" }
    New-Item -ItemType Directory -Path $staging | Out-Null
    Get-ChildItem -LiteralPath $PackageRoot -Force | Copy-Item -Destination $staging -Recurse -Force
    Test-ReleaseManifest $staging
    Move-Item -LiteralPath $staging -Destination $release
}
Test-ReleaseManifest $release

if (!(Test-Path -LiteralPath $configFile -PathType Leaf)) {
    $config = [ordered]@{
        data = (Join-Path $InstallRoot 'data')
        sources = @()
        backup = $null
        host = '127.0.0.1'
        port = 25265
        backupEveryHours = $null
    }
    Write-Utf8NoBom $configFile (($config | ConvertTo-Json -Depth 4) + [Environment]::NewLine)
} else {
    Write-Host "Preserving existing configuration: $configFile"
}

$config = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json
$data = [IO.Path]::GetFullPath([string]$config.data)
Invoke-BlankBoxPython @('-c','import sys; sys.path.insert(0,sys.argv[1]); from file_safety import reject_links; [reject_links(p) for p in sys.argv[2:]]',$PackageRoot,$data,(Join-Path $data 'blankbox.pid'))
New-Item -ItemType Directory -Force -Path $data | Out-Null
$pidFile = Join-Path $data 'blankbox.pid'
if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
    $recorded = 0
    if ([int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$recorded) -and (Get-Process -Id $recorded -ErrorAction SilentlyContinue)) {
        throw "Stop Blank Box process $recorded before installing or upgrading."
    }
    Remove-Item -LiteralPath $pidFile -Force
}

Invoke-BlankBoxPython @((Join-Path $release 'doctor.py'),'--config',$configFile)
$catalogBackup = $null
if ($previous -and $previous -ne [IO.Path]::GetFullPath($release)) {
    $upgradeDirectory = Join-Path $data 'upgrades'
    New-Item -ItemType Directory -Force -Path $upgradeDirectory | Out-Null
    $backupName = 'pre-' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ') + '-' + $releaseId + '.sqlite3'
    $output = Invoke-BlankBoxPython @((Join-Path $release 'maintenance.py'),'backup','--config',$configFile,'--destination',(Join-Path $upgradeDirectory $backupName))
    if ($output) { $catalogBackup = [string]($output | Select-Object -Last 1) }
}

try {
    Invoke-BlankBoxPython @((Join-Path $release 'server.py'),'--config',$configFile,'--check-startup')
} catch {
    if ($catalogBackup) { Invoke-BlankBoxPython @((Join-Path $release 'maintenance.py'),'restore','--config',$configFile,'--backup',$catalogBackup) }
    throw
}

$pending = Join-Path $InstallRoot ('.current.' + [guid]::NewGuid().ToString('N') + '.json')
try {
    Write-Utf8NoBom $pending ((@{ release = [IO.Path]::GetFullPath($release) } | ConvertTo-Json) + [Environment]::NewLine)
    Move-Item -LiteralPath $pending -Destination $currentFile -Force
    if ($previous -and $previous -ne [IO.Path]::GetFullPath($release)) {
        $arguments = @((Join-Path $release 'maintenance.py'),'write-state','--config',$configFile,'--previous',$previous,'--current',$release)
        if ($catalogBackup) { $arguments += @('--backup',$catalogBackup) }
        Invoke-BlankBoxPython $arguments | Out-Null
    }
} catch {
    if ($previous) { Write-Utf8NoBom $currentFile ((@{ release = $previous } | ConvertTo-Json) + [Environment]::NewLine) }
    else { Remove-Item -LiteralPath $currentFile -Force -ErrorAction SilentlyContinue }
    throw
} finally {
    Remove-Item -LiteralPath $pending -Force -ErrorAction SilentlyContinue
}

Copy-Item -LiteralPath (Join-Path $release 'start-windows.ps1') -Destination (Join-Path $InstallRoot 'start-windows.ps1') -Force
Copy-Item -LiteralPath (Join-Path $release 'rollback-windows.ps1') -Destination (Join-Path $InstallRoot 'rollback-windows.ps1') -Force
Copy-Item -LiteralPath (Join-Path $release 'uninstall-windows.ps1') -Destination (Join-Path $InstallRoot 'uninstall-windows.ps1') -Force
if ($RegisterStartupTask) {
    $startScript = Join-Path $InstallRoot 'start-windows.ps1'
    $taskCommand = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $startScript + '"'
    $existingTask = & schtasks.exe /Query /TN 'Blank Box' /XML 2>$null
    if ($LASTEXITCODE -eq 0) {
        if (($existingTask -join "`n") -notlike "*$startScript*") { throw 'An unrelated Blank Box startup task already exists. It was preserved.' }
        Write-Host 'Preserving the existing Blank Box startup task.'
    } else {
        & schtasks.exe /Create /SC ONLOGON /TN 'Blank Box' /TR $taskCommand | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Windows startup task registration failed.' }
        Write-Host 'Registered the optional Blank Box task for this user at logon.'
    }
}

Write-Host "Blank Box $releaseId is installed for this Windows account."
Write-Host "Start it with: powershell.exe -ExecutionPolicy Bypass -File `"$(Join-Path $InstallRoot 'start-windows.ps1')`""
Write-Host "Open: http://127.0.0.1:25265"
Write-Host "Access key: $(Join-Path $data 'access-key.txt')"
