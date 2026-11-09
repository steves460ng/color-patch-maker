import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import ast
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from color_patch_maker.gui.window import MainWindow
from color_patch_maker.engine import layout, output_names


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    w=MainWindow();w.show();app.processEvents()
    yield w
    w.close();w.deleteLater();app.processEvents()


def widget(w,name):
    return w.findChild(QWidget,name)


def set_value(w,name,value):
    widget(w,name).setText(str(value))


@pytest.mark.parametrize('prefix,tab',[('grid_cmyk',0),('ramp_start',1),('ramp_end',1)])
@pytest.mark.parametrize('value',['40.5','40.0','101','-1','','abc'])
def test_field_errors(window,prefix,tab,value):
    window.sidebar.tabs.setCurrentIndex(tab)
    name=prefix+'_m';set_value(window,name,value)
    assert widget(window,name).text()==value
    assert widget(window,name+'_error').text()
    for c in 'cyk':
        assert widget(window,prefix+'_'+c+'_error').text()==''
    assert window.controller.document is None and not window.preview.paper.patches
    assert '#b3261e' in widget(window,name).styleSheet()
    set_value(window,name,70)
    assert widget(window,name+'_error').text()=='' and widget(window,name).styleSheet()==''
    assert window.controller.document


@pytest.mark.parametrize('name,value',[('grid_cols','0'),('grid_step','1.5'),('layout_margin','abc'),('layout_width',''),('ramp_count','1')])
def test_other_field_errors(window,name,value):
    if name.startswith('ramp'): window.sidebar.tabs.setCurrentIndex(1)
    set_value(window,name,value)
    assert widget(window,name+'_error').text() and not window.preview.paper.patches


@pytest.mark.parametrize('settings,part', [({'grid_cols':100},'5mm'),({'layout_patch_size':10},'6pt'),({'layout_patch_size':500},'들어가지')])
def test_layout_errors(window,settings,part):
    for name,value in settings.items(): set_value(window,name,value)
    assert part in widget(window,'warning_list').text()
    assert window.preview.paper.document is None
    assert widget(window,'summary_patch_count').text()=='–'


@pytest.mark.parametrize('mode,changes',[
    ('grid',{}),('grid',{'grid_cols':4,'grid_rows':4}),
    ('grid',{'grid_cmyk_c':0,'grid_cmyk_m':100}),('ramp',{}),
    ('grid',{'layout_patch_size':60}),('ramp',{'layout_patch_size':60,'ramp_count':40}),
])
def test_engine_identity_and_summary(window,mode,changes):
    window.sidebar.tabs.setCurrentIndex(0 if mode=='grid' else 1)
    for name,value in changes.items():set_value(window,name,value)
    actual_mode,args,_=window.controller.inputs()
    expected=layout(actual_mode,**args)
    assert window.controller.document == expected
    assert window.preview.paper.patches == expected['pages'][0]['patches']
    assert widget(window,'summary_patch_count').text()==str(sum(len(p['patches']) for p in expected['pages']))
    assert widget(window,'summary_pdf_count').text()==str(len(expected['pages']))
    assert widget(window,'summary_patch_size').text()==f"{expected['pages'][0]['patches'][0]['rect_mm'][2]:.1f}"
    names=output_names(expected)
    assert widget(window,'filename_preview').text()==(names[0] if len(names)==1 else f'{names[0]} … {names[-1]}')
    assert widget(window,'paper_info').text()=='305×505mm · DeviceCMYK'
    assert '305×505 · 여백 20' in widget(window,'layout_summary').text()
    for warning in expected['warnings']: assert warning in widget(window,'warning_list').text()
    if len(names)>1: assert f'PDF {len(names)}개' in widget(window,'warning_list').text()


def test_paging_and_input_reset(window):
    set_value(window,'layout_patch_size',60)
    c=window.controller;n=len(c.document['pages'])
    assert n>1 and not widget(window,'previous_page_button').isEnabled()
    for i in range(1,n):
        widget(window,'next_page_button').click()
        assert widget(window,'page_indicator').text()==f'장 {i+1} / {n}'
        assert window.preview.paper.patches==c.document['pages'][i]['patches']
    assert not widget(window,'next_page_button').isEnabled()
    widget(window,'previous_page_button').click();assert c.page_index==n-2
    set_value(window,'grid_cmyk_y',21)
    assert c.page_index==0 and not widget(window,'previous_page_button').isEnabled()


@pytest.mark.parametrize('tab,button,prefix',[(0,'use_as_base_button','grid_cmyk'),(1,'use_as_start_button','ramp_start'),(1,'use_as_end_button','ramp_end')])
def test_click_and_apply(window,app,tab,button,prefix):
    window.sidebar.tabs.setCurrentIndex(tab);app.processEvents()
    paper=window.preview.paper
    patch=paper.patches[3]
    QTest.mouseClick(paper,Qt.MouseButton.LeftButton,pos=paper.patch_rect(patch).center().toPoint())
    assert window.controller.selected==patch and paper.selected_id==patch['id']
    assert widget(window,'selected_id').text()==patch['id']
    assert widget(window,button).isEnabled()
    widget(window,button).click()
    assert [widget(window,prefix+'_'+c).text() for c in 'cmyk']==[str(v) for v in patch['cmyk']]
    assert window.controller.document is not None
    assert window.controller.selected is None and paper.selected_id is None
    assert not widget(window,button).isEnabled()


def test_tab_memory_and_shared_paper(window,app):
    set_value(window,'grid_cmyk_c',42)
    paper=window.preview.paper
    QTest.mouseClick(paper,Qt.MouseButton.LeftButton,pos=paper.patch_rect(paper.patches[0]).center().toPoint())
    window.sidebar.tabs.setCurrentIndex(1)
    assert window.controller.selected is None
    assert widget(window,'ramp_start_c').text()=='40'
    set_value(window,'ramp_start_c',45)
    set_value(window,'layout_width',400)
    window.sidebar.tabs.setCurrentIndex(0);app.processEvents()
    assert widget(window,'grid_cmyk_c').text()=='42'
    assert window.preview.paper.paper_rect().width()/window.preview.paper.paper_rect().height()==pytest.approx(400/505)
    assert widget(window,'paper_info').text()=='400×505mm · DeviceCMYK'
    window.sidebar.tabs.setCurrentIndex(1)
    assert widget(window,'ramp_start_c').text()=='45'
    assert not widget(window,'make_pdf_button').isEnabled() and not widget(window,'browse_button').isEnabled()


def test_engine_has_no_qt_imports():
    for path in Path('color_patch_maker/engine').glob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            names=[n.name for n in node.names] if isinstance(node,ast.Import) else [node.module or ''] if isinstance(node,ast.ImportFrom) else []
            assert not any('PySide' in n or 'PyQt' in n for n in names)


def test_one_error_keeps_cmyk_row_aligned(window,app):
    set_value(window,'grid_cmyk_c','40.5')
    app.processEvents();QTest.qWait(30)
    fields=[widget(window,'grid_cmyk_'+c) for c in 'cmyk']
    assert len({field.y() for field in fields})==1
    error=widget(window,'grid_cmyk_c_error')
    assert error.height() >= error.heightForWidth(error.width())


def test_input_change_clears_selection_and_invalid_paging(window,app):
    paper=window.preview.paper
    QTest.mouseClick(paper,Qt.MouseButton.LeftButton,pos=paper.patch_rect(paper.patches[0]).center().toPoint())
    set_value(window,'grid_step','2')
    assert window.controller.selected is None and paper.selected_id is None
    set_value(window,'layout_patch_size','60')
    assert widget(window,'next_page_button').isEnabled()
    set_value(window,'grid_cols','')
    assert not widget(window,'next_page_button').isEnabled()
    assert not widget(window,'previous_page_button').isEnabled()
    assert widget(window,'page_indicator').text()=='장 – / –'
