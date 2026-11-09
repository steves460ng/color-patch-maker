import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import copy
import json
import subprocess
import sys
import threading
from pathlib import Path
import errno
import pytest
import pikepdf
from PySide6.QtCore import QSettings, QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from color_patch_maker.gui.window import MainWindow
from color_patch_maker.engine import layout
from color_patch_maker.engine.pdf import export, preview_paths, verify
import color_patch_maker.gui.output as output


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    w=MainWindow();w.show();app.processEvents()
    yield w
    wait_until(lambda:not w.controller.output.busy)
    w.close();w.deleteLater();app.processEvents()


def wait_until(predicate):
    for _ in range(500):
        QApplication.processEvents()
        if predicate(): return
        QTest.qWait(10)
    raise AssertionError('worker did not complete')


def wid(w,name):return w.findChild(QWidget,name)
def value(w,name,text):wid(w,name).setText(str(text))


def test_folder_and_dialog(window,tmp_path,monkeypatch):
    assert not wid(window,'make_pdf_button').isEnabled()
    assert '선택' in wid(window,'output_folder_error').text()
    value(window,'output_folder',tmp_path/'missing')
    assert not wid(window,'make_pdf_button').isEnabled()
    assert '존재' in wid(window,'output_folder_error').text()
    monkeypatch.setattr(output.QFileDialog,'getExistingDirectory',lambda *a:str(tmp_path))
    wid(window,'browse_button').click()
    assert wid(window,'output_folder').text()==str(tmp_path)
    assert wid(window,'make_pdf_button').isEnabled()
    value(window,'grid_cmyk_c','40.0')
    assert not wid(window,'make_pdf_button').isEnabled()


@pytest.mark.parametrize('mode',['grid','ramp'])
@pytest.mark.parametrize('split',[False,True])
def test_collision_output_and_cli(window,tmp_path,split,mode):
    if mode=='ramp':window.sidebar.tabs.setCurrentIndex(1)
    if split:
        if mode=='ramp':value(window,'ramp_count',40)
        value(window,'layout_patch_size',60)
    document=copy.deepcopy(window.controller.document)
    old=export(document,tmp_path)
    unchanged={p:Path(p).read_bytes() for p in old}
    value(window,'output_folder',tmp_path)
    predicted=preview_paths(document,tmp_path)
    assert '_v2' in wid(window,'filename_preview').text()
    wid(window,'make_pdf_button').click()
    wait_until(lambda:not window.controller.output.busy)
    assert '역검사 통과' in wid(window,'output_status').text()
    for p in predicted:
        assert Path(p).exists()
        if p.endswith('.pdf'):
            assert Path(p).name in wid(window,'output_status').text()
            assert verify(p,str(Path(p).with_suffix('.json')))
            with pikepdf.open(p) as pdf: assert len(pdf.pages)==1
    assert all(Path(p).read_bytes()==data for p,data in unchanged.items())
    cli_dir=tmp_path/'cli'
    args=[sys.executable,'-m','color_patch_maker.cli',mode]
    args += ['--cmyk','40','70','20','0'] if mode=='grid' else ['--from','40','70','20','0','--to','30','75','30','5','--count','40' if split else '11']
    args += ['--out-dir',str(cli_dir)]
    if split:args+=['--patch-size','60']
    result=subprocess.run(args,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    cli_json=[p for p in json.loads(result.stdout)['files'] if p.endswith('.json')]
    gui_json=[p for p in predicted if p.endswith('.json')]
    assert [json.loads(Path(p).read_text())['patches'] for p in gui_json]==[json.loads(Path(p).read_text())['patches'] for p in cli_json]
    value(window,'grid_step',2)
    assert not wid(window,'output_status').isVisible() and not wid(window,'open_folder_button').isVisible()


def test_worker_snapshot_lock_close_and_enter(window,tmp_path,monkeypatch):
    gate=threading.Event();started=threading.Event();seen=[]
    original=output.export
    def delayed(document,folder):
        seen.append((copy.deepcopy(document),threading.get_ident()))
        started.set();assert gate.wait(5)
        return original(document,folder)
    monkeypatch.setattr(output,'export',delayed)
    value(window,'output_folder',tmp_path)
    snapshot=copy.deepcopy(window.controller.document)
    QTest.keyClick(wid(window,'grid_cmyk_c'),Qt.Key.Key_Return)
    wait_until(started.is_set)
    try:
        assert window.controller.output.busy
        for name in ['grid_cmyk_c','layout_width','mode_tabs','output_folder','browse_button','make_pdf_button']:
            assert not wid(window,name).isEnabled()
        window.controller.output.start();assert len(seen)==1
        ticks=[];QTimer.singleShot(0,lambda:ticks.append(True));QTest.qWait(20);assert ticks
        window.close();assert window.isVisible()
        assert '끝난 뒤' in wid(window,'output_status').text()
        window.controller.document['stem']='changed after start'
        assert seen[0][0]==snapshot and seen[0][1]!=threading.get_ident()
    finally:gate.set()
    wait_until(lambda:not window.controller.output.busy)
    assert wid(window,'grid_cmyk_c').isEnabled() and wid(window,'browse_button').isEnabled()
    assert snapshot['stem']+'.pdf' in wid(window,'output_status').text()


@pytest.mark.parametrize('failure',[PermissionError('denied'),OSError(errno.ENOSPC,'full'),ValueError('검증 오류')])
def test_failure_cleanup(window,tmp_path,monkeypatch,failure):
    import color_patch_maker.engine.pdf as pdf
    keep=tmp_path/'keep.pdf';keep.write_bytes(b'original')
    value(window,'output_folder',tmp_path)
    if isinstance(failure,PermissionError):
        original=Path.open
        def denied(path,*args,**kwargs):
            if path.parent==tmp_path and args and args[0]=='xb':raise failure
            return original(path,*args,**kwargs)
        monkeypatch.setattr(Path,'open',denied)
    else:
        def fail(*args):raise failure
        monkeypatch.setattr(pdf,'verify',fail)
    wid(window,'make_pdf_button').click();wait_until(lambda:not window.controller.output.busy)
    message=wid(window,'output_status').text()
    assert ('권한' if isinstance(failure,PermissionError) else '공간' if isinstance(failure,OSError) else '역검사') in message
    assert list(tmp_path.glob('*.pdf'))==[keep] and keep.read_bytes()==b'original'
    assert not list(tmp_path.glob('*.json'))
    assert wid(window,'make_pdf_button').isEnabled()
    value(window,'output_folder','')
    assert not wid(window,'output_status').isVisible()


def test_settings_restore_and_invalid(app,tmp_path):
    settings=QSettings(str(tmp_path/'prefs.ini'),QSettings.Format.IniFormat)
    folder=tmp_path/'out';folder.mkdir()
    w=MainWindow(settings)
    value(w,'output_folder',folder);value(w,'layout_width',400);value(w,'layout_gap',4);value(w,'layout_height',600);value(w,'layout_margin',15);value(w,'layout_patch_size',60);value(w,'grid_cmyk_c',22)
    w.close()
    restored=MainWindow(settings)
    assert wid(restored,'output_folder').text()==str(folder)
    assert wid(restored,'layout_width').text()=='400' and wid(restored,'layout_gap').text()=='4'
    assert wid(restored,'grid_cmyk_c').text()=='40'
    assert [wid(restored,n).text() for n in ['layout_height','layout_margin','layout_patch_size']]==['600','15','60']
    assert 'grid_cmyk_c' not in settings.allKeys()
    restored.close();folder.rmdir()
    settings.setValue('layout_width','abc')
    invalid=MainWindow(settings)
    assert wid(invalid,'output_folder').text()==''
    assert wid(invalid,'layout_width').text()=='305'
    assert '폴더가 없어' in wid(invalid,'warning_list').text()
    invalid.close()


def test_error_geometry_and_layout_info(window,app):
    window.resize(1024,720)
    for tab,prefix in [(0,'grid_cmyk'),(1,'ramp_start')]:
        window.sidebar.tabs.setCurrentIndex(tab)
        value(window,prefix+'_c','40.5');app.processEvents();QTest.qWait(30)
        warnings=wid(window,'warnings_panel');viewport=window.sidebar.scroll.viewport()
        rect=warnings.rect().translated(warnings.mapTo(viewport,warnings.rect().topLeft()))
        assert viewport.rect().contains(rect)
        assert wid(window,'paper_info').text()=='305×505mm · DeviceCMYK'
        assert '여백 20' in wid(window,'layout_summary').text()
        value(window,prefix+'_c',40)


def test_preview_does_not_write_and_race(tmp_path):
    document=layout('grid',cmyk=[40]*4)
    prediction=preview_paths(document,tmp_path)
    assert list(tmp_path.iterdir())==[]
    Path(prediction[1]).write_text('existing')
    actual=export(document,tmp_path)
    assert '_v2' in actual[0] and Path(prediction[1]).read_text()=='existing'


def test_open_folder(window,tmp_path,monkeypatch):
    calls=[]
    monkeypatch.setattr(output.QDesktopServices,'openUrl',lambda url:calls.append(url.toLocalFile()) or True)
    value(window,'output_folder',tmp_path);wid(window,'make_pdf_button').click()
    wait_until(lambda:not window.controller.output.busy)
    wid(window,'open_folder_button').click()
    assert calls==[str(tmp_path)]
