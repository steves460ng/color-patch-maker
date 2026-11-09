import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from string import Formatter

import pytest
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QAbstractButton, QLineEdit, QGroupBox, QInputDialog, QMessageBox
from color_patch_maker.engine.messages import KO, EN, t, Message, EngineError
from color_patch_maker.engine import template_values, reserved_template_names
from color_patch_maker.engine.pdf import export, verify
from color_patch_maker.gui.language import resolve_language
from color_patch_maker.gui.window import MainWindow
from color_patch_maker.gui.dialogs import InputDialog, MessageBox
from color_patch_maker.gui.output import failure_message


@pytest.fixture
def app():return QApplication.instance() or QApplication([])


def settings_at(path,language):
    settings=QSettings(str(path),QSettings.Format.IniFormat)
    settings.setValue('language',language)
    return settings


def widget(w,name):return w.findChild(QWidget,name)


@pytest.mark.parametrize('key',KO)
def test_catalog_parity_and_render(key):
    assert KO.keys()==EN.keys()
    def fields(text):return {name for _,name,_,_ in Formatter().parse(text) if name is not None}
    assert fields(KO[key])==fields(EN[key])
    assert not re.search('[가-힣]',EN[key])
    class Sample:
        def __format__(self,spec):return format(2,spec)
    values={name:Sample() for name in fields(KO[key])}
    assert t(key,'ko',**values) and t(key,'en',**values)


@pytest.mark.parametrize('preference,locale,expected',[
    ('auto','ko_KR','ko'),('auto','ko-KR','ko'),('auto','en_US','en'),('auto','ja_JP','en'),
    ('auto','C','en'),('ko','en_US','ko'),('en','ko_KR','en'),('unknown','ko_KR','ko'),
])
def test_resolve_locale(preference,locale,expected):
    assert resolve_language(preference,locale)==expected


def test_next_launch_persistence_without_input_changes(app,tmp_path):
    settings=settings_at(tmp_path/'language.ini','unknown')
    w=MainWindow(settings,locale_name='ko_KR')
    try:
        assert w.language=='ko' and w.language_preference=='auto'
        combo=widget(w,'layout_template');combo.setCurrentIndex(combo.findData('card'));combo.activated.emit(combo.currentIndex())
        widget(w,'grid_cmyk_c').setText('45')
        widget(w,'output_folder').setText(str(tmp_path))
        before={f.objectName():f.text() for f in w.findChildren(QLineEdit)}
        identity=combo.currentData();document=w.controller.document
        w.language_combo.setCurrentIndex(w.language_combo.findData('en'))
        assert settings.value('language')=='en' and w.language=='ko'
        assert {f.objectName():f.text() for f in w.findChildren(QLineEdit)}==before
        assert combo.currentData()==identity and w.controller.document is document
        assert widget(w,'output_status').text()=='다시 시작하면 적용됩니다'
    finally:w.close()
    restored=MainWindow(settings,locale_name='ko_KR')
    try:
        assert restored.language=='en'
        assert widget(restored,'layout_template').currentData()=='card'
        assert widget(restored,'layout_template').currentText()=='Card'
        assert widget(restored,'output_folder').text()==str(tmp_path)
        assert widget(restored,'grid_cmyk_c').text()=='40'
    finally:restored.close()


@pytest.mark.parametrize('language',['ko','en'])
@pytest.mark.parametrize('tab',[0,1])
@pytest.mark.parametrize('state',['default','invalid','generating','completed','failure'])
def test_language_notice_clearance(app,tmp_path,language,tab,state):
    w=MainWindow(settings_at(tmp_path/'clearance.ini',language))
    try:
        w.setFont(QFont('DejaVu Sans',10));w.resize(1024,720);w.show()
        w.sidebar.tabs.setCurrentIndex(tab)
        if state=='invalid':widget(w,('grid_cmyk' if tab==0 else 'ramp_start')+'_c').setText('40.5')
        elif state=='generating':w.controller.output.status(w.t('output.busy'))
        elif state=='completed':w.controller.output.status(w.t('output.success',names='chart_01.pdf\nchart_02.pdf'))
        elif state=='failure':w.controller.output.status(failure_message(PermissionError(),language))
        app.processEvents();QTest.qWait(30)
        panel=widget(w,'warnings_panel');viewport=w.sidebar.scroll.viewport()
        rect=panel.rect().translated(panel.mapTo(viewport,panel.rect().topLeft()))
        assert viewport.rect().contains(rect)
        assert viewport.height()-rect.bottom()-1>=16
        assert w.sidebar.scroll.verticalScrollBar().value()==0
        assert w.size().width()==1024 and w.size().height()==720
        if language=='en':
            for control in w.findChildren(QWidget):
                text=control.text() if isinstance(control,(QLabel,QAbstractButton)) else control.title() if isinstance(control,QGroupBox) else ''
                assert not re.search('[가-힣]',text),(control.objectName(),text)
    finally:w.close()


@pytest.mark.parametrize('language',['ko','en'])
def test_legacy_template_distinction_and_reservations(app,tmp_path,monkeypatch,language):
    from color_patch_maker.gui.templates import TemplateController
    settings=settings_at(tmp_path/'legacy.ini',language)
    users={name:template_values('card') for name in ('Default','Card','Custom')}
    settings.setValue('layout_templates',json.dumps(users))
    w=MainWindow(settings)
    try:
        combo=widget(w,'layout_template')
        for name in reserved_template_names():
            with pytest.raises(ValueError):TemplateController.check_name(name,language=language)
        for name in users:
            index=combo.findData('user:'+name)
            assert combo.itemText(index)==t('template.saved_name',language,name=name)
            combo.setCurrentIndex(index);combo.activated.emit(index)
            assert combo.currentData()=='user:'+name
            assert widget(w,'delete_template_button').isEnabled()
        monkeypatch.setattr(MessageBox,'question',lambda *a:MessageBox.StandardButton.Yes)
        w.controller.templates.delete()
        assert 'Custom' not in w.controller.templates.users
        assert combo.findData('default')>=0 and combo.findData('card')>=0
        assert set(json.loads(settings.value('layout_templates')))=={'Default','Card'}
    finally:w.close()


@pytest.mark.parametrize('language',['ko','en'])
def test_dialogs_use_window_language(app,tmp_path,language):
    w=MainWindow(settings_at(tmp_path/'dialogs.ini',language));seen=[]
    def input_dialog():
        d=app.activeModalWidget();assert isinstance(d,QInputDialog)
        seen.append((d.windowTitle(),d.labelText(),d.okButtonText(),d.cancelButtonText()))
        d.setTextValue('My paper');d.accept()
    def question():
        d=app.activeModalWidget();assert isinstance(d,QMessageBox)
        seen.append((d.windowTitle(),d.text(),d.button(QMessageBox.StandardButton.Yes).text(),d.button(QMessageBox.StandardButton.No).text()))
        d.button(QMessageBox.StandardButton.No).click()
    try:
        QTimer.singleShot(10,input_dialog)
        assert InputDialog.getText(w,w.t('template.save'),w.t('template.name'))==('My paper',True)
        QTimer.singleShot(10,question)
        assert MessageBox.question(w,w.t('template.delete'),w.t('template.delete_question',name='My paper'),
                                   QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.No
        assert seen[0]==tuple(w.t(k) for k in ['template.save','template.name','dialog.ok','dialog.cancel'])
        assert seen[1]==(w.t('template.delete'),w.t('template.delete_question',name='My paper'),w.t('dialog.yes'),w.t('dialog.no'))
    finally:w.close()


def test_bilingual_export_identical(app,tmp_path):
    outputs=[]
    for language in ('ko','en'):
        w=MainWindow(settings_at(tmp_path/(language+'.ini'),language))
        try:
            combo=widget(w,'layout_template');combo.setCurrentIndex(combo.findData('card'));combo.activated.emit(combo.currentIndex())
            files=export(w.controller.document,tmp_path/language)
            for pdf,manifest in zip(files[::2],files[1::2]):assert verify(pdf,manifest)
            outputs.append({Path(p).name:Path(p).read_bytes() for p in files})
        finally:w.close()
    assert outputs[0]==outputs[1]


@pytest.mark.parametrize('case',json.loads((Path(__file__).parent/'fixtures/messages_ko.json').read_text(encoding='utf-8')))
def test_engine_errors_both_languages(case):
    import color_patch_maker.engine as engine
    fn=getattr(engine,case['function'],None) or getattr(engine.templates,case['function'])
    with pytest.raises(EngineError) as caught:fn(*case['args'],**case['kwargs'])
    assert caught.value.render('ko')==case['text']
    english=caught.value.render('en')
    assert english and not re.search('[가-힣]',english)
    assert english.endswith('.')


def test_cli_english_in_korean_environment_cp949(tmp_path):
    env=os.environ.copy();env.update(LANG='ko_KR.UTF-8',LC_ALL='ko_KR.UTF-8',LANGUAGE='ko',PYTHONIOENCODING='cp949')
    for value in ('40.5','-1'):
        result=subprocess.run([sys.executable,'-m','color_patch_maker.cli','grid','--cmyk',value,'70','20','0'],
                              env=env,capture_output=True)
        assert result.returncode==2 and result.stdout==b''
        text=result.stderr.decode('cp949')
        assert text.startswith('error: ') and not re.search('[가-힣]',text)


def test_gui_translation_calls_are_explicit():
    for path in Path('color_patch_maker/gui').glob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='render':
                assert node.args or node.keywords,(path,node.lineno)
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='t':
                assert len(node.args)>=2 or any(k.arg=='language' for k in node.keywords),(path,node.lineno)
