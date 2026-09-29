param(
    [string]$InstallRoot = (Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'BlankBox')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

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
    throw 'The selected Blank Box release has no bundled Windows runtime and Python 3.10 or newer was not found.'
}

$currentFile = Join-Path $InstallRoot 'current.json'
$configFile = Join-Path $InstallRoot 'config.json'
if (!(Test-Path -LiteralPath $currentFile -PathType Leaf) -or !(Test-Path -LiteralPath $configFile -PathType Leaf)) {
    throw 'Blank Box is not installed for this Windows account. Run install-windows.ps1 first.'
}
$current = Get-Content -LiteralPath $currentFile -Raw | ConvertFrom-Json
$release = [IO.Path]::GetFullPath([string]$current.release)
$releasesRoot = [IO.Path]::GetFullPath((Join-Path $InstallRoot 'releases')) + [IO.Path]::DirectorySeparatorChar
if (!$release.StartsWith($releasesRoot, [StringComparison]::OrdinalIgnoreCase) -or !(Test-Path -LiteralPath (Join-Path $release 'server.py') -PathType Leaf)) {
    throw 'The selected Blank Box release is invalid.'
}

$config = Get-Content -LiteralPath $configFile -Raw | ConvertFrom-Json
$data = [IO.Path]::GetFullPath([string]$config.data)
New-Item -ItemType Directory -Force -Path $data | Out-Null
$pidFile = Join-Path $data 'blankbox.pid'
if (Test-Path -LiteralPath $pidFile -PathType Leaf) {
    $recorded = 0
    if ([int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$recorded) -and (Get-Process -Id $recorded -ErrorAction SilentlyContinue)) {
        throw "Blank Box is already running as process $recorded."
    }
    Remove-Item -LiteralPath $pidFile -Force
}

$python = Get-BlankBoxPython $release
Set-Content -LiteralPath $pidFile -Value $PID -Encoding ascii
Push-Location $release
try {
    $arguments = @($python.Prefix) + @((Join-Path $release 'server.py'), '--config', $configFile)
    & $python.Command @arguments
    $exitCode = $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Pop-Location
}
exit $exitCode
