# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ThermoQ Windows onedir build (used by Inno Setup)."""
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
SPECDIR = os.path.abspath(SPECPATH)
ROOT = os.path.abspath(os.path.join(SPECDIR, '..'))
ICON = os.path.join(ROOT, 'images', 'thermoq.ico')
if not os.path.isfile(ICON):
    ICON = os.path.join(ROOT, 'images', 'Simplified logo.png')

datas = [
    (os.path.join(ROOT, 'images'), 'images'),
    (os.path.join(ROOT, 'docs', 'ThermoQ_User_Manual_EN.pdf'), 'docs'),
    (os.path.join(ROOT, 'docs', 'ThermoQ_User_Manual_ZH.pdf'), 'docs'),
    (os.path.join(ROOT, 'Example'), 'Example'),
    (os.path.join(ROOT, 'LICENSE'), '.'),
]
binaries = []
hiddenimports = [
    'periodic_table',
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'openpyxl',
    'xlrd',
    'matplotlib',
    'matplotlib.backends.backend_agg',
    'mpl_toolkits.mplot3d',
    'plotly',
    'plotly.graph_objects',
    'sklearn.gaussian_process',
    'sklearn.gaussian_process.kernels',
    'scipy.interpolate',
    'scipy.spatial',
    'scipy.ndimage',
    'skimage',
    'skimage.measure',
    'kaleido',
]

for pkg in (
    'plotly',
    'kaleido',
    'sklearn',
    'scipy',
    'matplotlib',
    'skimage',
    'openpyxl',
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        try:
            hiddenimports += collect_submodules(pkg)
        except Exception:
            pass

excludes = [
    'pytest',
    'IPython',
    'notebook',
    'jupyter',
    'sphinx',
    'tkinter.test',
    'matplotlib.tests',
    'numpy.tests',
    'scipy.tests',
    'sklearn.tests',
]

a = Analysis(
    [os.path.join(ROOT, 'main.py')],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[os.path.join(SPECDIR, 'pyi_rth_thermoq.py')],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ThermoQ',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON if os.path.isfile(ICON) else None,
    version=os.path.join(SPECDIR, 'file_version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ThermoQ',
)
