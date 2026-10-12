"""Render supplied Styles SVGs on their shared 24-point design canvas.

The source SVGs have cropped viewBoxes. Scaling those bounds independently
would enlarge the cubes relative to the background icon's ground plane.
Requires rsvg-convert because QtSvg does not render the source filters.
"""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


def main():
    icons = Path(__file__).resolve().parents[1] / 'resources' / 'icons'
    for category in ('edge', 'face', 'environment', 'watermark', 'working'):
        source = icons / f'dlg_style_{category}.svg'
        root = ET.parse(source).getroot()
        root.set('viewBox', '0 0 24 24')
        root.set('width', '24pt')
        root.set('height', '24pt')
        subprocess.run(
            ['rsvg-convert', '--width', '96', '--height', '96',
             '--output', str(source.with_suffix('.png'))],
            input=ET.tostring(root), check=True)


if __name__ == '__main__':
    main()
