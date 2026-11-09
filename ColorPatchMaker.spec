# Qt hooks collect native libraries and plugins for the build OS.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks.qt import pyside6_library_info

root = Path(SPECPATH)
icon = root / 'color_patch_maker/gui/resources/app.ico'
if not icon.is_file():
    raise RuntimeError(f'Application icon is missing: {icon}')
platforms = pyside6_library_info.collect_plugins('platforms')
if sys.platform == 'win32' and not any(Path(src).name.lower() == 'qwindows.dll' for src, _ in platforms):
    raise RuntimeError('PySide6 Windows platform plugin qwindows.dll is missing')
a = Analysis([str(root / 'scripts/gui_entry.py')], pathex=[str(root)],
             datas=collect_data_files('reportlab') + [(str(icon), 'color_patch_maker/gui/resources')], binaries=platforms,
             hiddenimports=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ColorPatchMaker',
          console=False, strip=False, upx=False, icon=str(icon))
coll = COLLECT(exe, a.binaries, a.datas, name='ColorPatchMaker', strip=False, upx=False)
