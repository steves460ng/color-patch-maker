"""Qt widgets tested directly; no pytest-qt dependency or display required."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import subprocess
import sys
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QLineEdit, QLabel, QPushButton
from color_patch_maker.gui.window import MainWindow


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    w = MainWindow()
    w.show()
    app.processEvents()
    yield w
    w.close()
    w.deleteLater()
    app.processEvents()


def test_window_and_named_widgets(window):
    assert window.isVisible()
    assert (window.minimumWidth(),window.minimumHeight()) == (1024,720)
    fields = {f'{prefix}_{c}':str(v) for prefix,values in [('grid_cmyk',(40,70,20,0)),('ramp_start',(40,70,20,0)),('ramp_end',(30,75,30,5))] for c,v in zip('cmyk',values)}
    fields.update(grid_step='1',grid_cols='7',grid_rows='7',ramp_count='11',ramp_cols='auto',layout_width='305',layout_height='505',layout_margin='20',layout_gap='3',layout_patch_size='auto')
    for name,value in fields.items():
        field = window.findChild(QLineEdit,name)
        assert field is not None and field.text() == value
        assert field.validator() is None
        assert window.findChild(QLabel,name+'_error').text() == ''
    for name in ['mode_tabs','grid_panel','ramp_panel','grid_channels','layout_toggle','layout_fields','layout_summary','selected_swatch','selected_id','selected_cmyk','selection_hint','warning_list','summary_patch_count','summary_pdf_count','summary_patch_size','output_folder','filename_preview','output_status','paper_placeholder','page_indicator','screen_color_note']:
        assert window.findChild(QWidget,name) is not None, name
    for name in ['make_pdf_button','browse_button','use_as_base_button','use_as_start_button','use_as_end_button','previous_page_button','next_page_button']:
        assert not window.findChild(QPushButton,name).isEnabled()
    for name in ['summary_patch_count','summary_pdf_count','summary_patch_size','filename_preview']:
        assert window.findChild(QLabel,name).text() == '–'


def test_tabs_and_disclosure(window,app):
    s=window.sidebar
    assert s.grid_panel.isVisible() and not s.ramp_panel.isVisible()
    s.tabs.setCurrentIndex(1);app.processEvents()
    assert not s.grid_panel.isVisible() and s.ramp_panel.isVisible()
    assert s.ramp_actions.isVisible() and not s.use_base.isVisible()
    s.tabs.setCurrentIndex(0);app.processEvents()
    assert s.grid_panel.isVisible() and not s.ramp_panel.isVisible()
    assert not s.layout_fields.isVisible()
    QTest.mouseClick(s.layout_toggle,Qt.MouseButton.LeftButton);app.processEvents()
    assert s.layout_fields.isVisible()
    QTest.mouseClick(s.layout_toggle,Qt.MouseButton.LeftButton);app.processEvents()
    assert not s.layout_fields.isVisible()


@pytest.mark.parametrize('size',[(1024,720),(1600,900)])
@pytest.mark.parametrize('mode',[0,1])
def test_geometry_and_fixed_regions(window,app,size,mode):
    window.resize(*size);s=window.sidebar;s.tabs.setCurrentIndex(mode)
    s.layout_toggle.setChecked(True);app.processEvents()
    assert (window.width(),window.height()) == size
    assert s.width() == 380
    paper=window.preview.paper.paper_rect()
    assert paper.width()/paper.height() == pytest.approx(305/505)
    assert window.preview.paper.rect().contains(paper.toAlignedRect())
    footer=window.findChild(QWidget,'output_footer')
    before=(s.tabs.mapTo(window,s.tabs.rect().topLeft()),footer.mapTo(window,footer.rect().topLeft()))
    bar=s.scroll.verticalScrollBar();assert bar.maximum()>0
    bar.setValue(bar.maximum());app.processEvents()
    assert before==(s.tabs.mapTo(window,s.tabs.rect().topLeft()),footer.mapTo(window,footer.rect().topLeft()))
    assert s.scroll.horizontalScrollBar().maximum()==0
    assert footer.isVisible() and window.preview.x() > s.x()+s.width()


def test_tab_order_and_raw_input(window,app):
    window.sidebar.layout_toggle.setChecked(True);app.processEvents()
    fields=['grid_cmyk_c','grid_cmyk_m','grid_cmyk_y','grid_cmyk_k','grid_channels','grid_step','grid_cols','grid_rows','layout_toggle','layout_width','layout_height','layout_margin','layout_gap','layout_patch_size','output_folder']
    window.findChild(QWidget,fields[0]).setFocus()
    for name in fields:
        assert app.focusWidget().objectName()==name
        QTest.keyClick(app.focusWidget(),Qt.Key.Key_Tab)
    field=window.findChild(QLineEdit,'grid_cmyk_c')
    field.setText('100.5')
    assert field.text()=='100.5' and window.findChild(QLabel,'grid_cmyk_c_error').text()==''


def test_no_engine_import_and_entrypoint():
    script='''
import importlib.abc, sys, runpy
class BlockEngine(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith('color_patch_maker.engine'):
            raise AssertionError(fullname)
sys.meta_path.insert(0,BlockEngine())
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
original = QApplication.exec
def timed_exec(self):
    assert any(w.isVisible() for w in self.topLevelWidgets())
    QTimer.singleShot(20,self.quit)
    return original()
QApplication.exec = timed_exec
runpy.run_module('color_patch_maker.gui',run_name='__main__')
'''
    result=subprocess.run([sys.executable,'-c',script],capture_output=True,text=True,timeout=15)
    assert result.returncode==0,result.stderr
