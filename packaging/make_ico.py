"""Create a multi-size Windows .ico from the app logo PNG."""
from __future__ import annotations

import os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(ROOT, 'images', 'Simplified logo.png')
DST = os.path.join(ROOT, 'images', 'thermoq.ico')
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> None:
    img = Image.open(SRC).convert('RGBA')
    # Pillow writes all provided sizes into one ICO.
    img.save(DST, format='ICO', sizes=SIZES)
    print(f'Wrote {DST}')


if __name__ == '__main__':
    main()
