# onedir console bundle; build on the target operating system.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

root = Path(SPECPATH)
a = Analysis([str(root / 'scripts/cpm_entry.py')], pathex=[str(root)],
             datas=collect_data_files('reportlab'),
             excludes=['PySide6'], hiddenimports=[])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='cpm',
          console=True, strip=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='cpm', strip=False, upx=False)
