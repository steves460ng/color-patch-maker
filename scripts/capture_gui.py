"""Capture GUI states with temporary settings/output; no real preferences touched."""
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QSettings
from PySide6.QtTest import QTest
from color_patch_maker.gui.window import MainWindow
import color_patch_maker.gui.output as output
import color_patch_maker.engine.pdf as pdf

app = QApplication([])
folder = Path('docs/ui/screens')
folder.mkdir(parents=True, exist_ok=True)
for path in folder.glob('*.png'):
    path.unlink()

def wait_for(predicate):
    for _ in range(500):
        app.processEvents()
        if predicate():return
        QTest.qWait(10)
    raise RuntimeError('Capture worker timeout')

with TemporaryDirectory() as temp:
    for width,height in [(1024,720),(1600,900)]:
        for state in ['grid','clamped','invalid','split','ramp','selected','generating','completed','failure','templates','card']:
            root=Path(temp)/f'{width}-{state}';root.mkdir()
            window=MainWindow(QSettings(str(root/'settings.ini'),QSettings.Format.IniFormat))
            window.resize(width,height);window.show()
            def field(name,value):window.findChild(QWidget,name).setText(str(value))
            field('output_folder',root)
            if state=='clamped':field('grid_cmyk_c',0);field('grid_cmyk_m',100)
            elif state=='invalid':field('grid_cmyk_c','40.5')
            elif state=='split':
                field('layout_patch_size',60)
                window.findChild(QWidget,'next_page_button').click()
            elif state=='ramp':window.sidebar.tabs.setCurrentIndex(1)
            elif state in ('templates','card'):
                combo=window.findChild(QWidget,'layout_template')
                combo.setCurrentText('카드')
                combo.activated.emit(combo.currentIndex())
                if state=='templates':
                    window.sidebar.layout_toggle.setChecked(True)
                    app.processEvents()
                    window.sidebar.scroll.ensureWidgetVisible(combo)
                else:
                    window.findChild(QWidget,'next_page_button').click()
            app.processEvents();QTest.qWait(40)
            if state=='selected':
                paper=window.preview.paper
                QTest.mouseClick(paper,Qt.MouseButton.LeftButton,pos=paper.patch_rect(paper.patches[3]).center().toPoint())
            original_export,original_verify=output.export,pdf.verify
            gate=Event();started=Event()
            try:
                if state=='generating':
                    # Hold a real export until its progress screen is captured.
                    def delayed(document,folder):
                        started.set()
                        if not gate.wait(10):raise RuntimeError('Capture timeout')
                        return original_export(document,folder)
                    output.export=delayed
                elif state=='failure':
                    # Deterministic verification failure after writing output.
                    def failed_verify(*args):raise ValueError('역검사 실패 확인용 오류')
                    pdf.verify=failed_verify
                if state in ('generating','completed','failure'):
                    window.controller.output.start()
                    wait_for(started.is_set if state=='generating' else lambda:not window.controller.output.busy)
                app.processEvents();QTest.qWait(40)
                assert window.grab().save(str(folder/f'{width}x{height}-{state}.png'))
            finally:
                gate.set()
                wait_for(lambda:not window.controller.output.busy)
                output.export,pdf.verify=original_export,original_verify
                window.close();window.deleteLater();app.processEvents()
