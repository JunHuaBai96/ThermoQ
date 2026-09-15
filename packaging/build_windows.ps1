# Build ThermoQ Windows onedir + optional Inno Setup installer.
# Run from repo root OR from packaging\:
#   powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
param(
    [switch]$SkipInstaller,
    [switch]$SkipIco
)

$ErrorActionPreference = 'Stop'
$PackagingDir = $PSScriptRoot
$Root = Split-Path -Parent $PackagingDir
Set-Location $Root

Write-Host "==> Repo root: $Root"

function Assert-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Assert-Command python

Write-Host "==> Installing Python build dependencies"
python -m pip install --upgrade pip
python -m pip install -r "$Root\requirements.txt"
python -m pip install pyinstaller

if (-not $SkipIco) {
    Write-Host "==> Generating images\thermoq.ico"
    python "$PackagingDir\make_ico.py"
}

Write-Host "==> PyInstaller (windowed onedir)"
python -m PyInstaller --noconfirm --clean "$PackagingDir\ThermoQ.spec"

$Exe = Join-Path $Root 'dist\ThermoQ\ThermoQ.exe'
if (-not (Test-Path $Exe)) {
    throw "Build failed: $Exe not found"
}
Write-Host "==> Built: $Exe"

if ($SkipInstaller) {
    Write-Host "==> Skipping Inno Setup (-SkipInstaller)"
    exit 0
}

$Iscc = $null
foreach ($cand in @(
        ${env:LocalAppData} + '\Programs\Inno Setup 6\ISCC.exe',
        ${env:ProgramFiles} + '\Inno Setup 6\ISCC.exe',
        ${env:ProgramFiles(x86)} + '\Inno Setup 6\ISCC.exe'
    )) {
    if ($cand -and (Test-Path $cand)) { $Iscc = $cand; break }
}
if (-not $Iscc) {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { $Iscc = $cmd.Source }
}

if (-not $Iscc) {
    Write-Warning "Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php then re-run, or compile packaging\thermoq.iss manually."
    Write-Host "Portable folder is ready: dist\ThermoQ\"
    exit 0
}

$Iss = Join-Path $PackagingDir 'thermoq.iss'
if (-not (Test-Path (Join-Path $Root 'images\thermoq.ico'))) {
    Write-Warning "images\thermoq.ico missing; Inno Setup may fail on SetupIconFile."
}

Write-Host "==> Compiling installer with $Iscc"
& $Iscc $Iss
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit $LASTEXITCODE" }

Write-Host "==> Installer: dist\ThermoQ-1.0.0-Windows-Setup.exe"
