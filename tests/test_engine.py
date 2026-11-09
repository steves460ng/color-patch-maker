import json
import os
import subprocess
import sys

import pikepdf
import pytest
from color_patch_maker.engine import layout
from color_patch_maker.engine.pdf import export, verify


def patches(doc):
    return [p for page in doc['pages'] for p in page['patches']]


@pytest.mark.parametrize('cols,rows', [(7, 7), (4, 4), (4, 3), (1, 1)])
def test_grid(cols, rows):
    ps = patches(layout('grid', cmyk=[40, 70, 20, 0], cols=cols, rows=rows))
    base = [p for p in ps if p['reference']]
    assert len(base) == 1 and base[0]['cmyk'] == [40, 70, 20, 0]
    assert base[0]['id'] == f'R{rows-(rows-1)//2}C{(cols-1)//2+1}'
    assert ps[0]['cmyk'] == [40-(cols-1)//2, 70+(rows-1)//2, 20, 0]
    assert ps[-1]['cmyk'] == [40+cols-1-(cols-1)//2, 70+(rows-1)//2-(rows-1), 20, 0]


def test_clamp():
    d = layout('grid', cmyk=[0, 100, 20, 0])
    ps = patches(d)
    assert len(ps) == 49 and d['warnings']
    assert any(p['clamped'] for p in ps)
    assert all(0 <= v <= 100 for p in ps for v in p['cmyk'])
    assert len({tuple(p['cmyk']) for p in ps}) < 49


def test_ramp():
    a, b = [40, 70, 20, 0], [30, 75, 30, 5]
    forward = [p['cmyk'] for p in patches(layout('ramp', start=a, end=b, count=11))]
    reverse = [p['cmyk'] for p in patches(layout('ramp', start=b, end=a, count=11))]
    assert forward == reverse[::-1]
    assert forward[0] == a and forward[-1] == b
    assert [p[1] for p in forward] == [70,71,71,72,72,73,73,74,74,75,75]
    assert [p[0] for p in forward] == list(range(40,29,-1))
    assert [p[2] for p in forward] == list(range(20,31))
    assert [p[3] for p in forward] == [0,1,1,2,2,3,3,4,4,5,5]
    d = layout('ramp', start=[0]*4, end=[10]*4, count=21)
    assert patches(d)[1]['cmyk'] == [1]*4
    d = layout('ramp', start=[0]*4, end=[2]*4, count=11)
    assert len(patches(d)) == 11 and not d['warnings']


@pytest.mark.parametrize('mode,kwargs', [('grid', {'cmyk':[40,70,20,0]}), ('ramp', {'start':[0]*4,'end':[10]*4,'count':49})])
def test_split_and_export(tmp_path, mode, kwargs):
    auto = layout(mode, **kwargs)
    assert len(auto['pages']) == 1
    split = layout(mode, patch_size=60, cols=4, **kwargs)
    assert len(split['pages']) > 1
    ps = patches(split)
    expected = 28 if mode == 'grid' else 49
    assert len(ps) == len({p['id'] for p in ps}) == expected
    for p in ps:
        x,y,w,h = p['rect_mm']
        assert 20 <= x and x+w <= 285 and 26 <= y and y+h <= 485
        assert all(type(v) is int for v in p['cmyk'])
    files = export(split, tmp_path)
    original = {f: open(f,'rb').read() for f in files}
    assert '_01.pdf' in files[0]
    for pdf, manifest in zip(files[::2], files[1::2]):
        assert verify(pdf, manifest)
        with pikepdf.open(pdf) as p:
            assert len(p.pages) == 1
    second = export(split, tmp_path)
    assert '_v2_01.pdf' in second[0]
    assert all(open(f,'rb').read() == data for f,data in original.items())


@pytest.mark.parametrize('tamper', ['color', 'rect', 'paper', 'label', 'transform', 'pages'])
def test_tampering(tmp_path, tamper):
    files = export(layout('grid', cmyk=[40,70,20,0]), tmp_path)
    bad = tmp_path/'bad.pdf'
    with pikepdf.open(files[0]) as pdf:
        page = pdf.pages[0]
        content = page.Contents.read_bytes()
        if tamper == 'color':
            content = content.replace(b'.37 .73 .2 0 k', b'.99 .73 .2 0 k')
        elif tamper == 'rect':
            content = content.replace(b'56.69291', b'57.69291')
        elif tamper == 'paper':
            page.MediaBox = [0,0,500,500]
        elif tamper == 'label':
            content = content.replace(b'C37', b'C99')
        elif tamper == 'transform':
            content = b'2 0 0 2 0 0 cm\n' + content
        else:
            pdf.pages.append(page)
        page.Contents = pdf.make_stream(content)
        pdf.save(bad)
    with pytest.raises(ValueError):
        verify(bad, files[1])


@pytest.mark.parametrize('arguments', [
    ['grid','--cmyk','40.0','70','20','0'], ['grid','--cmyk','40.5','70','20','0'],
    ['grid','--cmyk','101','70','20','0'], ['grid','--cmyk','-1','70','20','0'],
    ['grid','--cmyk','40','70','20','0','--step','1.5'],
    ['grid','--cmyk','40','70','20','0','--cols','0'],
    ['grid','--cmyk','40','70','20','0','--channels','CC'],
    ['grid','--cmyk','40','70','20','0','--margin','nan'],
    ['grid','--cmyk','40','70','20','0','--patch-size','500'],
    ['ramp','--from','0','0','0','0','--to','10','10','10','10','--count','1'],
    ['ramp','--from','0','0','0','0','--to','0','0','0','0','--count','11'],
])
def test_cli_invalid(tmp_path, arguments):
    out = tmp_path/'output'
    result = subprocess.run([sys.executable,'-m','color_patch_maker.cli',*arguments,'--out-dir',str(out)], capture_output=True)
    assert result.returncode == 2 and result.stderr and not result.stdout
    assert not out.exists()


@pytest.mark.parametrize('encoding', [None, 'cp949'])
def test_cli_success(tmp_path, encoding):
    # JSON bytes assume UTF-8; native redirected CLI output follows its locale.
    # Exercise a Korean output path, including CP949 on non-Windows hosts.
    tmp_path = tmp_path / '한글 경로'
    env = os.environ.copy()
    if encoding:
        env['PYTHONIOENCODING'] = encoding
    for arguments in [ ['grid','--cmyk','0','100','20','0'], ['ramp','--from','40','70','20','0','--to','30','75','30','5','--count','11'] ]:
        result = subprocess.run([sys.executable,'-m','color_patch_maker.cli',*arguments,'--out-dir',str(tmp_path)],capture_output=True,text=True,encoding=encoding,env=env)
        assert result.returncode == 0, result.stderr
        files = json.loads(result.stdout)['files']
        assert bool(result.stderr) == (arguments[0] == 'grid')
        checked = subprocess.run([sys.executable,'-m','color_patch_maker.cli','verify',*files],capture_output=True,text=True,encoding=encoding,env=env)
        assert checked.returncode == 0 and json.loads(checked.stdout)['verified']


def test_ramp_width_and_auto_minimum():
    with pytest.raises(ValueError, match='최대'):
        layout('ramp',start=[0]*4,end=[10]*4,count=11,cols=7,patch_size=60)
    with pytest.raises(ValueError, match='5mm'):
        layout('grid',cmyk=[40]*4,cols=100)


def test_failure_cleanup(tmp_path, monkeypatch):
    import color_patch_maker.engine.pdf as module
    keep = tmp_path/'keep.pdf'
    keep.write_bytes(b'existing')
    def fail(*args):
        raise ValueError('verification failed')
    monkeypatch.setattr(module, 'verify', fail)
    with pytest.raises(ValueError):
        export(layout('grid',cmyk=[40]*4), tmp_path)
    assert list(tmp_path.iterdir()) == [keep] and keep.read_bytes() == b'existing'


def test_grid_block_order_and_ramp_row_order():
    grid = layout('grid',cmyk=[40]*4, cols=7, rows=7,patch_size=60)
    assert [page['patches'][0]['id'] for page in grid['pages']] == ['R7C1','R7C5','R1C1','R1C5']
    ramp = layout('ramp', start=[0]*4,end=[10]*4,count=30,patch_size=60)
    assert [p['id'] for p in patches(ramp)] == [f'{i:02}' for i in range(1,31)]
    assert len(ramp['pages'][0]['patches']) % ramp['settings']['cols'] == 0


def test_partial_collision(tmp_path):
    d = layout('grid', cmyk=[40]*4)
    existing = tmp_path/(d['stem']+'.json')
    existing.write_text('original')
    files = export(d,tmp_path)
    assert '_v2.pdf' in files[0]
    assert existing.read_text() == 'original'
    assert not (tmp_path/(d['stem']+'.pdf')).exists()


@pytest.mark.parametrize('cols', range(1, 16))
@pytest.mark.parametrize('rows', range(1, 16))
def test_auto_grid_single_page(tmp_path, cols, rows):
    # Large paper separates pagination from the independent readability limit.
    doc = layout('grid', cmyk=[40,70,20,0], cols=cols, rows=rows, paper=(1000,1000))
    assert len(doc['pages']) == 1
    files = export(doc, tmp_path)
    assert len(files) == 2 and verify(*files)
    try:
        default = layout('grid', cmyk=[40,70,20,0], cols=cols, rows=rows)
    except ValueError as exc:
        assert '최소 4.5pt' in str(exc)
    else:
        assert len(default['pages']) == 1


@pytest.mark.parametrize('count', range(2,61))
def test_auto_ramp_single_page(tmp_path, count):
    doc = layout('ramp', start=[40,70,20,0], end=[30,75,30,5], count=count)
    assert len(doc['pages']) == 1
    assert len(export(doc,tmp_path)) == 2


def test_fixed_size_exact_fit():
    size = (265-8*3)/9
    doc = layout('grid', cmyk=[0]*4,cols=9,rows=9,patch_size=size)
    assert len(doc['pages']) == 1
    # Height, too: use a generous width to keep labels readable.
    size = (465-8*3)/9-6
    doc = layout('grid', cmyk=[40]*4,cols=1,rows=9,patch_size=size)
    assert len(doc['pages']) == 1


def test_label_boundary_and_pdf_font(tmp_path):
    from color_patch_maker.engine import MIN_LABEL_PT, LABEL_FONT
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.units import mm
    label = 'C100 M100 Y100 K100 *'
    boundary = stringWidth(label,LABEL_FONT,MIN_LABEL_PT)/mm
    with pytest.raises(ValueError, match='패치 크기를 키우거나 칸 수를 줄이세요'):
        layout('grid',cmyk=[100]*4,cols=1,rows=1,patch_size=boundary-1e-6)
    doc = layout('grid',cmyk=[100]*4,cols=1,rows=1,patch_size=boundary+1e-6)
    assert patches(doc)[0]['label_font_pt'] >= MIN_LABEL_PT
    files = export(doc,tmp_path)
    with pikepdf.open(files[0]) as pdf:
        sizes = [float(args[1]) for args,op in pikepdf.parse_content_stream(pdf.pages[0]) if str(op)=='Tf']
    assert sizes[-1] >= MIN_LABEL_PT


@pytest.mark.parametrize('extra', [['--cols','15','--rows','15'],['--patch-size','10']])
def test_unreadable_cli_no_output(tmp_path,extra):
    out = tmp_path/'output'
    result = subprocess.run([sys.executable,'-m','color_patch_maker.cli','grid','--cmyk','100','100','100','100',*extra,'--out-dir',str(out)],capture_output=True,text=True)
    assert result.returncode == 2 and '최소 4.5pt' in result.stderr
    assert not out.exists()


@pytest.mark.parametrize('option', ['--margin','--gap','--patch-size','--paper'])
def test_invalid_mm_korean(tmp_path,option):
    values = ['abc','505'] if option == '--paper' else ['abc']
    result = subprocess.run([sys.executable,'-m','color_patch_maker.cli','grid','--cmyk','40','70','20','0',option,*values,'--out-dir',str(tmp_path/'out')],capture_output=True,text=True)
    assert result.returncode == 2 and option[2:] in result.stderr and 'mm 값을 입력하세요' in result.stderr
    assert not (tmp_path/'out').exists()


def test_endpoint_symbols():
    ps = patches(layout('ramp',start=[0]*4,end=[100]*4,count=3))
    assert ps[0]['label'].endswith(' >') and ps[-1]['label'].endswith(' <')
    assert 'start' not in ps[0]['label'] and 'end' not in ps[-1]['label']
