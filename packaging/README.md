# Packaging ThermoQ for Windows (V1.0)

This folder produces a **windowed** `ThermoQ.exe` (no console) and an optional **Inno Setup** installer so users without Python can install from GitHub Releases.

## What is bundled

| Item | Role |
|------|------|
| `main.py` | GUI entry |
| `periodic_table.py` | Element table |
| `images/` | Splash, window icon, header logo |
| `docs/ThermoQ_User_Manual_*.pdf` | Help → User Manual |
| `Example/` | Help → Example (~76 MB) |
| `LICENSE` | Installer license page |

**Not** bundled: `test/` (~2.4 GB), `scripts/`, source `__pycache__`.

## Prerequisites

- Windows 10/11 **64-bit**
- Python 3.10–3.12 (64-bit) with `pip`
- Disk: ~3 GB free during build (sklearn/scipy/matplotlib/plotly)
- Optional: [Inno Setup 6](https://jrsoftware.org/isinfo.php) for `ThermoQ-1.0.0-Windows-Setup.exe`

## One-command build

From the **repository root**:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
```

Outputs:

- Portable app: `dist\ThermoQ\ThermoQ.exe`
- Installer (if ISCC is installed): `dist\ThermoQ-1.0.0-Windows-Setup.exe`

PyInstaller only (no installer):

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1 -SkipInstaller
```

## Manual steps

```powershell
python -m pip install -r requirements.txt pyinstaller
python packaging\make_ico.py
python -m PyInstaller --noconfirm --clean packaging\ThermoQ.spec
# then open packaging\thermoq.iss in Inno Setup and compile
```

## Why onedir (not onefile)

A single-file exe would extract sklearn/scipy/matplotlib on every start (slow, antivirus-heavy). The installer copies the **folder** to `C:\Program Files\ThermoQ` and creates Start Menu / Desktop shortcuts.

## Frozen-app path behavior

- Bundled files are read via `resource_path()` / `sys._MEIPASS`.
- Working directory is set to `%USERPROFILE%\Documents\ThermoQ` so Plot/Save defaults are writable (Start Menu shortcuts otherwise start in System32).
- Default plot files therefore land under **Documents\ThermoQ**, not Program Files.

## GitHub Release (Windows V1.0)

1. Tag: `v1.0.0`
2. Attach `ThermoQ-1.0.0-Windows-Setup.exe` (preferred) and optionally zip `dist\ThermoQ`.
3. Or push a `v1.0.0` tag and let `.github/workflows/windows-release.yml` build and upload the installer.

Typical installed size is **several hundred MB** because of NumPy / SciPy / scikit-learn / Matplotlib / Plotly. That is expected.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Missing splash / icon | Rebuild after `images/` is present; paths must go through `resource_path`. |
| Help → Manual not found | Confirm PDFs are listed under `datas` in `ThermoQ.spec`. |
| Blank window / instant exit | Temporarily set `console=True` in the spec, rebuild, read the traceback. |
| Antivirus flags the exe | Unsigned PyInstaller binaries; submit a false-positive report or sign with a code-signing cert. |
| Inno compile error on ChineseSimplified.isl | Install Inno Setup with language files, or remove that `[Languages]` line. |
| Build path with CJK (OneDrive 文档) | Prefer cloning to `C:\src\ThermoQ` if PyInstaller fails to collect files. |
