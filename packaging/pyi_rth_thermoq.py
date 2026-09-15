# PyInstaller runtime hook: matplotlib must stay non-interactive in the frozen GUI.
import os
import sys

os.environ.setdefault('MPLBACKEND', 'Agg')

if getattr(sys, 'frozen', False):
    dest = os.path.join(os.path.expanduser('~'), 'Documents', 'ThermoQ')
    try:
        os.makedirs(dest, exist_ok=True)
        os.chdir(dest)
    except OSError:
        pass
