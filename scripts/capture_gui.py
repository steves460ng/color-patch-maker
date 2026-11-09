"""Run from repository root: QT_QPA_PLATFORM=offscreen python scripts/capture_gui.py."""
from pathlib import Path
from PySide6.QtWidgets import QApplication
from color_patch_maker.gui.window import MainWindow

app = QApplication([])
window = MainWindow()
window.show()
folder = Path('docs/ui/screens')
folder.mkdir(parents=True, exist_ok=True)
for width, height in [(1024,720),(1600,900)]:
    for mode, title in [(0,'grid'),(1,'ramp')]:
        for expanded in [False,True]:
            window.resize(width,height)
            window.sidebar.tabs.setCurrentIndex(mode)
            window.sidebar.layout_toggle.setChecked(expanded)
            app.processEvents()
            if expanded:
                window.sidebar.scroll.ensureWidgetVisible(window.sidebar.layout_fields)
            else:
                window.sidebar.scroll.verticalScrollBar().setValue(0)
            app.processEvents()
            path = folder/f'{width}x{height}-{title}-{"expanded" if expanded else "collapsed"}.png'
            assert window.grab().save(str(path))
window.close()
