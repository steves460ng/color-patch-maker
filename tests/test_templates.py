from color_patch_maker.gui.dialogs import InputDialog as QInputDialog, MessageBox as QMessageBox
import json
import subprocess
import sys
from pathlib import Path

import pikepdf
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QWidget, QLineEdit
from color_patch_maker.engine import layout, template_names, template_values
from color_patch_maker.engine.pdf import export, verify
from color_patch_maker.gui.window import MainWindow
from color_patch_maker.gui.settings import fields_from_values


@pytest.fixture
def window(tmp_path):
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path/'templates.ini'), QSettings.Format.IniFormat)
    w = MainWindow(settings); w.show(); app.processEvents()
    yield w
    w.close(); w.deleteLater(); app.processEvents()


def widget(w, name):
    return w.findChild(QWidget, name)


def choose(w, name):
    combo = widget(w, 'layout_template')
    combo.setCurrentText(name)
    combo.activated.emit(combo.currentIndex())


def unrelated(w):
    return {f.objectName(): f.text() for f in w.sidebar.findChildren(QLineEdit)
            if not f.objectName().startswith('layout_')} | {'channels': widget(w, 'grid_channels').currentText()}


def test_builtin_values_and_copies():
    assert template_names() == ('default', 'card')
    assert template_values('기본') == template_values('default') == dict(paper=[305,505],margin=20,gap=3,patch_size=None)
    assert template_values('카드') == template_values('card') == dict(paper=[85.6,54],margin=2,gap=1,patch_size=18)
    value = template_values('card'); value['paper'][0] = 1
    assert template_values('card')['paper'][0] == 85.6


@pytest.mark.parametrize('tab', [0, 1])
def test_choose_reset_and_name(window, tmp_path, tab):
    window.sidebar.tabs.setCurrentIndex(tab)
    widget(window, 'grid_cmyk_c').setText('41')
    widget(window, 'ramp_count').setText('12')
    widget(window, 'output_folder').setText(str(tmp_path))
    before = unrelated(window)
    for name in ('카드', '기본'):
        choose(window, name)
        assert unrelated(window) == before
        assert {key: widget(window,key).text() for key in fields_from_values(template_values(name))} == fields_from_values(template_values(name))
        assert widget(window,'layout_template').currentText() == name
        assert widget(window,'layout_summary').text().startswith(name+' · ')
        assert not widget(window,'delete_template_button').isEnabled()
    choose(window,'카드')
    widget(window,'layout_gap').setText('2')
    assert widget(window,'layout_template').currentText() == '사용자 설정'
    widget(window,'reset_layout_button').click()
    assert widget(window,'layout_template').currentText() == '기본'
    assert unrelated(window) == before


@pytest.mark.parametrize('count,pages', [(7,8),(3,2)])
@pytest.mark.parametrize('cmyk', [[40,70,20,0],[100,70,20,0],[100,100,100,100]])
def test_card_output(tmp_path,count,pages,cmyk):
    doc = layout('grid',cmyk=cmyk,cols=count,rows=count,**template_values('card'))
    assert len(doc['pages']) == pages
    paths = export(doc,tmp_path)
    for pdf, manifest in zip(paths[::2],paths[1::2]):
        assert verify(pdf,manifest)
        with pikepdf.open(pdf) as file:
            assert len(file.pages) == 1


def test_card_longest_label(window):
    for channel in 'cmyk':
        widget(window,'grid_cmyk_'+channel).setText('100')
    choose(window,'카드')
    assert len(window.controller.document['pages']) == 8
    assert '라벨' not in widget(window,'warning_list').text()
    assert any(p['label']=='C100 M100 Y100 K100 *'
               for page in window.controller.document['pages'] for p in page['patches'])


def dialog(monkeypatch, name, accepted=True, confirm=QMessageBox.StandardButton.Yes):
    monkeypatch.setattr(QInputDialog,'getText',lambda *a,**kw:(name,accepted))
    calls=[]
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**kw: calls.append(a[2]) or confirm)
    return calls


def test_user_roundtrip_overwrite_delete(window,monkeypatch):
    before = unrelated(window)
    widget(window,'layout_width').setText('310')
    dialog(monkeypatch,'내 용지')
    widget(window,'save_template_button').click()
    assert widget(window,'layout_template').currentText() == '내 용지'
    assert widget(window,'delete_template_button').isEnabled()
    choose(window,'기본'); choose(window,'내 용지')
    assert widget(window,'layout_width').text() == '310'
    widget(window,'layout_width').setText('320')
    calls=dialog(monkeypatch,'내 용지',confirm=QMessageBox.StandardButton.No)
    widget(window,'save_template_button').click()
    assert len(calls)==1 and window.controller.templates.users['내 용지']['paper'][0]==310
    calls=dialog(monkeypatch,'내 용지')
    widget(window,'save_template_button').click()
    assert len(calls)==1 and window.controller.templates.users['내 용지']['paper'][0]==320
    restored=MainWindow(window.settings)
    try:
        choose(restored,'내 용지')
        assert widget(restored,'layout_width').text()=='320'
    finally:
        restored.close()
    calls=dialog(monkeypatch,'',confirm=QMessageBox.StandardButton.No)
    widget(window,'delete_template_button').click()
    assert len(calls)==1 and '내 용지' in window.controller.templates.users
    calls=dialog(monkeypatch,'')
    widget(window,'delete_template_button').click()
    assert len(calls)==1 and not window.controller.templates.users
    assert widget(window,'layout_width').text()=='320'
    assert unrelated(window)==before
    assert json.loads(window.settings.value('layout_templates'))=={}


@pytest.mark.parametrize('name', ['기본','카드','default','card','사용자 설정','Default','Card','Custom',''])
def test_reserved_names(window,monkeypatch,name):
    dialog(monkeypatch,name)
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a: warnings.append(a[2]))
    widget(window,'save_template_button').click()
    assert warnings and not window.controller.templates.users


def test_cancel_and_invalid_layout(window,monkeypatch):
    dialog(monkeypatch,'취소',accepted=False)
    widget(window,'save_template_button').click()
    assert not window.controller.templates.users
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *a: warnings.append(a[2]))
    for name,value in [('layout_width','abc'),('layout_width','0'),('layout_patch_size','4')]:
        choose(window,'기본')
        widget(window,name).setText(value)
        widget(window,'save_template_button').click()
    assert len(warnings)==3 and not window.controller.templates.users


@pytest.mark.parametrize('saved', [
    {'정상':template_values('card'),'고장':{'paper':[1]},'card':template_values('default')},
    {'정상':template_values('card'),'고장':dict(paper=[85,54],margin=3,gap=1,patch_size=4)},
    [], 'broken json',
])
def test_corrupt_restore(tmp_path,saved):
    app=QApplication.instance() or QApplication([])
    settings=QSettings(str(tmp_path/'corrupt.ini'),QSettings.Format.IniFormat)
    settings.setValue('layout_templates', saved if isinstance(saved,str) else json.dumps(saved))
    w=MainWindow(settings)
    try:
        assert '건너뛰' in widget(w,'warning_list').text()
        assert set(w.controller.templates.users)==({'정상'} if isinstance(saved,dict) else set())
    finally:w.close()


@pytest.mark.parametrize('mode', ['grid','ramp'])
def test_cli_gui_manifest(window,tmp_path,mode):
    if mode=='ramp':window.sidebar.tabs.setCurrentIndex(1)
    choose(window,'카드')
    gui=export(window.controller.document,tmp_path/'gui')
    args=['--cmyk','40','70','20','0'] if mode=='grid' else ['--from','40','70','20','0','--to','30','75','30','5','--count','11']
    result=subprocess.run([sys.executable,'-m','color_patch_maker.cli',mode,*args,'--template','card','--out-dir',str(tmp_path/'cli')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    cli=json.loads(result.stdout)['files']
    def patches(files):
        return [json.loads(Path(p).read_text(encoding='utf-8'))['patches'] for p in files if p.endswith('.json')]
    assert patches(gui)==patches(cli)


def test_cli_priority_and_unknown(tmp_path):
    args=[sys.executable,'-m','color_patch_maker.cli','grid','--cmyk','40','70','20','0','--template','card','--out-dir',str(tmp_path/'cli')]
    result=subprocess.run([*args,'--paper','305','505','--margin','20','--gap','3','--patch-size','35'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    manifest=next(p for p in json.loads(result.stdout)['files'] if p.endswith('.json'))
    expected=layout('grid',cmyk=[40,70,20,0],paper=[305,505],margin=20,gap=3,patch_size=35)
    paths=export(expected,tmp_path/'expected')
    assert json.loads(Path(manifest).read_text(encoding='utf-8'))['patches']==json.loads(Path(paths[1]).read_text(encoding='utf-8'))['patches']
    result=subprocess.run([*args,'--template','unknown'],capture_output=True,text=True)
    assert result.returncode==2 and all(s in result.stderr for s in ['default','card'])


def test_cli_partial_override(tmp_path):
    result=subprocess.run([sys.executable,'-m','color_patch_maker.cli','grid','--cmyk','40','70','20','0',
                           '--template','card','--gap','0','--out-dir',str(tmp_path/'cli')],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    actual=json.loads(result.stdout)['files']
    values=template_values('card');values['gap']=0
    expected=export(layout('grid',cmyk=[40,70,20,0],**values),tmp_path/'expected')
    for a,b in zip(actual[1::2],expected[1::2]):
        assert json.loads(Path(a).read_text(encoding='utf-8'))==json.loads(Path(b).read_text(encoding='utf-8'))
    assert len(actual)==len(expected)==16


def test_duplicate_values_reset(window,monkeypatch):
    dialog(monkeypatch,'내 기본')
    widget(window,'save_template_button').click()
    assert widget(window,'layout_template').currentText()=='내 기본'
    widget(window,'reset_layout_button').click()
    assert widget(window,'layout_template').currentText()=='기본'
    assert not widget(window,'delete_template_button').isEnabled()


def test_template_decimal_precision(window,monkeypatch):
    widget(window,'layout_width').setText('305.123456789')
    dialog(monkeypatch,'정밀 용지')
    widget(window,'save_template_button').click()
    choose(window,'기본');choose(window,'정밀 용지')
    assert widget(window,'layout_width').text()=='305.123456789'
    assert widget(window,'layout_template').currentText()=='정밀 용지'
