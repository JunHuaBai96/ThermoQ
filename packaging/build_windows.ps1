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
python -m pip install -r "$PackagingDir\requirements-build.txt"

# If both PyQt5 and PySide6 are present, PyInstaller aborts.  Force exclude PySide6/PyQt6 so only PyQt5 side effects are skipped.
# (No Qt is actually needed because the GUI is Tkinter.)
$Env:PYINSTALLER_QT_API = "PyQt5"

# Avoid pulling huge unrelated ML frameworks if they are installed in the build environment.
$Env:PYTORCH_JIT = "0"

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
$pf = [Environment]::GetFolderPath('ProgramFiles')
$pf86 = [Environment]::GetFolderPath('ProgramFilesX86')
$localPrograms = Join-Path $env:LOCALAPPDATA 'Programs'
$searchDirs = @(
    (Join-Path $pf86 'Inno Setup 6'),
    (Join-Path $pf 'Inno Setup 6'),
    (Join-Path $localPrograms 'Inno Setup 6')
) | Where-Object { $_ -and (Test-Path $_) }

foreach ($dir in $searchDirs) {
    $cand = Join-Path $dir 'ISCC.exe'
    if (Test-Path -LiteralPath $cand) {
        $Iscc = $cand
        break
    }
}

# Fallback: registry uninstall entry (works when env ProgramFiles(x86) is empty)
if (-not $Iscc) {
    $regRoots = @(
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    foreach ($root in $regRoots) {
        $hit = Get-ItemProperty $root -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -like 'Inno Setup*' -and $_.InstallLocation } |
            Select-Object -First 1
        if ($hit) {
            $cand = Join-Path $hit.InstallLocation.TrimEnd('\') 'ISCC.exe'
            if (Test-Path -LiteralPath $cand) {
                $Iscc = $cand
                break
            }
        }
    }
}

if (-not $Iscc) {
    $cmd = Get-Command iscc, ISCC.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { $Iscc = $cmd.Source }
}

if (-not $Iscc) {
    Write-Warning @"
Inno Setup compiler (ISCC.exe) not found.
Install from https://jrsoftware.org/isinfo.php (include command-line compiler),
or open packaging\thermoq.iss in Inno Setup Compiler and click Build → Compile.
Portable app folder is ready: dist\ThermoQ\
"@
    exit 0
}

$Iss = Join-Path $PackagingDir 'thermoq.iss'
if (-not (Test-Path (Join-Path $Root 'images\thermoq.ico'))) {
    Write-Warning "images\thermoq.ico missing; Inno Setup may fail on SetupIconFile."
}

Write-Host "==> Compiling installer with $Iscc"
& $Iscc $Iss
if ($LASTEXITCODE -ne 0) { throw "ISCC failed with exit $LASTEXITCODE" }

Write-Host "==> Installer: dist\ThermoQ-1.0.1-Windows-Setup.exe"
