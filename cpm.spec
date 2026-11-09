# onedir console bundle; build on the target operating system.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
icon = root / 'color_patch_maker/gui/resources/app.ico'
if not icon.is_file():
    raise RuntimeError(f'Application icon is missing: {icon}')
a = Analysis([str(root / 'scripts/cpm_entry.py')], pathex=[str(root)],
             datas=collect_data_files('reportlab'),
             excludes=['PySide6'], hiddenimports=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='cpm',
          console=True, strip=False, upx=False, icon=str(icon))
coll = COLLECT(exe, a.binaries, a.datas, name='cpm', strip=False, upx=False)
