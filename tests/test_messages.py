"""Catalog coverage and Korean behavior recorded before the refactor."""
import ast
import json
import re
from pathlib import Path
from string import Formatter

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QWidget
import color_patch_maker.engine as engine
from color_patch_maker.engine import templates
from color_patch_maker.engine.messages import KO, EN, CATALOGS, t, Message, EngineError
from color_patch_maker.gui.window import MainWindow

ROOT=Path('color_patch_maker')
GOLDEN=json.loads((Path(__file__).parent/'fixtures/messages_ko.json').read_text(encoding='utf-8'))


def sources():
    return [(p,ast.parse(p.read_text(encoding='utf-8'))) for p in ROOT.rglob('*.py') if p.name!='messages.py']


def test_no_korean_literals_outside_catalog():
    for path,tree in sources():
        docstrings={id(n.body[0].value) for n in ast.walk(tree)
                    if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body
                    and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant)
                    and isinstance(n.body[0].value.value,str)}
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and id(node) not in docstrings:
                assert not re.search('[가-힣]',node.value),(path,node.lineno,node.value)


def test_catalog_keys_and_call_arguments():
    used=set()
    def keys(expr):
        if isinstance(expr,ast.Constant) and isinstance(expr.value,str):return [expr.value]
        if isinstance(expr,ast.IfExp):return keys(expr.body)+keys(expr.orelse)
        if isinstance(expr,ast.Subscript) and isinstance(expr.value,ast.Name) and expr.value.id=='_LABEL_KEYS':
            return list(templates._LABEL_KEYS.values())
        raise AssertionError(f'Untracked message key expression: {ast.dump(expr)}')
    for path,tree in sources():
        for call in ast.walk(tree):
            if not isinstance(call,ast.Call) or not ((isinstance(call.func,ast.Name) and call.func.id in ('t','translate','Message','EngineError')) or (isinstance(call.func,ast.Attribute) and call.func.attr=='t')):
                continue
            for key in keys(call.args[0]):
                assert key in KO,(path,key)
                used.add(key)
                required={field for _,field,_,_ in Formatter().parse(KO[key]) if field is not None}
                supplied={kw.arg for kw in call.keywords}
                if None not in supplied:
                    func = call.func.id if isinstance(call.func,ast.Name) else 't'
                    supplied-={'language'} if func in ('t','translate') else {'target','value'} if func=='EngineError' else set()
                    assert required==supplied,(path,key,required,supplied)
    assert used==set(KO)
    assert set(CATALOGS)=={'ko','en'}


@pytest.mark.parametrize('key',KO)
def test_every_template_formats_and_rejects_missing_values(key):
    class Sample:
        def __format__(self,spec):return format(2,spec)
    fields={field for _,field,_,_ in Formatter().parse(KO[key]) if field is not None}
    values={field:Sample() for field in fields}
    assert t(key,**values)
    for missing in fields:
        with pytest.raises(KeyError):t(key,**{k:v for k,v in values.items() if k!=missing})
    with pytest.raises(KeyError):t(key,**values,unexpected='value')


def test_unknown_keys_and_languages_fail():
    with pytest.raises(KeyError):t('missing.key')
    with pytest.raises(KeyError):t('app.title',language='missing')


@pytest.mark.parametrize('case',GOLDEN,ids=lambda case:case['code']+'-'+case['function'])
def test_error_text_matches_pre_refactor(case):
    fn=getattr(engine,case['function'],None) or getattr(templates,case['function'])
    with pytest.raises(EngineError) as caught:fn(*case['args'],**case['kwargs'])
    error=caught.value
    assert isinstance(error,ValueError)
    assert error.code==case['code']
    assert error.target is not None
    assert str(error)==error.render('ko')==case['text']


def test_field_errors_and_warning_objects():
    values=dict(cmyk=['40.5',70,20,0],channels='CM',step=1,cols=7,rows=7,
                paper=[305,505],margin=20,gap=3,patch_size=None)
    errors=engine.input_errors('grid',**values)
    assert set(errors)=={'cmyk.0'}
    error=errors['cmyk.0']
    assert error.code=='input.integer' and error.target=='cmyk.0' and error.value=='40.5'
    assert str(error)=='C: 인쇄기는 정수값만 출력합니다. 정수를 입력하세요.'
    warning=engine.layout('grid',cmyk=[0,100,20,0])['warnings'][0]
    assert isinstance(warning,Message) and warning.code=='warning.clamped'
    assert warning.values=={'count':33}
    assert str(warning)=='33개 패치 0/100 고정'
    assert str(Message('warning.split',count=8))=='한 장에 다 들어가지 않아 단일 페이지 PDF 8개로 나눕니다'


def test_old_settings_and_identifier_selection(tmp_path):
    app=QApplication.instance() or QApplication([])
    settings=QSettings(str(tmp_path/'old.ini'),QSettings.Format.IniFormat)
    settings.setValue('layout_width','310')
    settings.setValue('output_folder',str(tmp_path))
    # These English names were permitted before the reservation list expanded.
    users={name:engine.template_values('card') for name in ('내 용지','Default','Card','Custom')}
    settings.setValue('layout_templates',json.dumps(users,ensure_ascii=False))
    w=MainWindow(settings)
    try:
        def widget(name):return w.findChild(QWidget,name)
        assert widget('layout_width').text()=='310'
        assert widget('output_folder').text()==str(tmp_path)
        assert set(w.controller.templates.users)==set(users)
        combo=widget('layout_template')
        index=combo.findData('card');assert index>=0
        combo.setCurrentIndex(index);combo.activated.emit(index)
        assert combo.currentData()=='card' and combo.currentText()=='카드'
        assert widget('layout_summary').text()=='카드 · 85.6×54 · 여백 2 · 18mm'
        widget('reset_layout_button').click()
        assert combo.currentData()=='default' and combo.currentText()=='기본'
        index=combo.findData('user:Card');combo.setCurrentIndex(index);combo.activated.emit(index)
        assert combo.currentData()=='user:Card' and combo.currentText()=='Card (저장)'
        assert widget('delete_template_button').isEnabled()
        assert widget('grid_cmyk_c').text()=='40'
    finally:w.close()
    assert json.loads(settings.value('layout_templates'))==users


def test_expanded_reserved_names():
    from color_patch_maker.gui.templates import TemplateController
    assert engine.reserved_template_names()=={'사용자 설정','Custom','기본','카드','Default','Card','default','card'}
    for name in engine.reserved_template_names():
        with pytest.raises(ValueError,match='기본 제공 이름·별칭과 사용자 설정은 이름으로 사용할 수 없습니다.'):
            TemplateController.check_name(name, language='ko')


CLI_GOLDEN=json.loads((Path(__file__).parent/'fixtures/cli_en.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case',CLI_GOLDEN,ids=lambda case:' '.join(case['args']))
def test_cli_english_output(case,tmp_path):
    import hashlib
    import os
    import subprocess
    import sys
    from color_patch_maker.engine.pdf import verify
    folder=tmp_path/'출력'
    args=case['args'] if '--help' in case['args'] else [*case['args'],'--out-dir',str(folder)]
    env=os.environ.copy();env['PYTHONIOENCODING']='utf-8'
    result=subprocess.run([sys.executable,'-m','color_patch_maker.cli',*args],env=env,
                          capture_output=True,text=True,encoding='utf-8')
    encoded_path=json.dumps(str(folder),ensure_ascii=False)[1:-1]
    assert result.stdout.replace(encoded_path,'{OUTPUT}')==case['stdout']
    assert result.stderr==case['stderr']
    assert result.returncode==case['code']
    assert {p.name for p in folder.glob('*')}==set(case['hashes'])
    for file in folder.glob('*.json'):
        # Text files use native newlines on Windows; compare their UTF-8 content.
        assert hashlib.sha256(file.read_text(encoding='utf-8').encode('utf-8')).hexdigest()==case['hashes'][file.name]
        assert verify(file.with_suffix('.pdf'),file)


def test_template_dialog_wording_unchanged(tmp_path,monkeypatch):
    from color_patch_maker.gui.dialogs import InputDialog as QInputDialog, MessageBox as QMessageBox
    app=QApplication.instance() or QApplication([])
    window=MainWindow(QSettings(str(tmp_path/'dialogs.ini'),QSettings.Format.IniFormat))
    inputs=[];questions=[];warnings=[]
    monkeypatch.setattr(QInputDialog,'getText',lambda parent,title,prompt:(inputs.append((title,prompt)) or ('내 용지',True)))
    monkeypatch.setattr(QMessageBox,'question',lambda parent,title,prompt,*args:(questions.append((title,prompt)) or QMessageBox.StandardButton.No))
    monkeypatch.setattr(QMessageBox,'warning',lambda parent,title,prompt:warnings.append((title,prompt)))
    try:
        window.findChild(QWidget,'layout_width').setText('310')
        controller=window.controller.templates
        controller.save();controller.save();controller.delete()
        assert inputs==[('템플릿 저장','템플릿 이름')]*2
        assert questions==[('템플릿 덮어쓰기','“내 용지” 템플릿을 덮어쓸까요?'),
                           ('템플릿 삭제','“내 용지” 템플릿을 삭제할까요?')]
        monkeypatch.setattr(QInputDialog,'getText',lambda *args:('기본',True))
        controller.save()
        assert warnings==[('템플릿 저장','기본 제공 이름·별칭과 사용자 설정은 이름으로 사용할 수 없습니다.')]
    finally:window.close()
