"""Capture the connected GUI states from the repository root (offscreen supported)."""
from pathlib import Path
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from color_patch_maker.gui.window import MainWindow

app = QApplication([])
folder = Path('docs/ui/screens')
folder.mkdir(parents=True, exist_ok=True)
for path in folder.glob('*.png'):
    path.unlink()
for width, height in [(1024,720),(1600,900)]:
    for state in ['grid','clamped','invalid','split','ramp','selected']:
        window = MainWindow()
        window.resize(width,height)
        window.show()
        def field(name,value):
            window.findChild(QWidget,name).setText(str(value))
        if state=='clamped':
            field('grid_cmyk_c',0);field('grid_cmyk_m',100)
        elif state=='invalid':
            field('grid_cmyk_c','40.5')
        elif state=='split':
            field('layout_patch_size',60)
            window.findChild(QWidget,'next_page_button').click()
        elif state=='ramp':
            window.sidebar.tabs.setCurrentIndex(1)
        app.processEvents();QTest.qWait(40)
        if state=='selected':
            paper=window.preview.paper
            QTest.mouseClick(paper,Qt.MouseButton.LeftButton,pos=paper.patch_rect(paper.patches[3]).center().toPoint())
            app.processEvents();QTest.qWait(40)
        assert window.grab().save(str(folder/f'{width}x{height}-{state}.png'))
        window.close()
        window.deleteLater()
        app.processEvents()
