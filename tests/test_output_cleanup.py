"""Headerless output contract, label sizing and verification regressions."""
import json
from pathlib import Path

import pikepdf
import pytest
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from color_patch_maker.engine import layout, MIN_LABEL_PT, LABEL_FONT, template_values
from color_patch_maker.engine.pdf import export, verify


def pdf_labels(path):
    result = []
    with pikepdf.open(path) as pdf:
        for args, op in pikepdf.parse_content_stream(pdf.pages[0]):
            if str(op) == 'Tf':
                size = float(args[1])
            elif str(op) == 'Tj':
                result.append((str(args[0]), size))
    return result


@pytest.mark.parametrize('mode', ['grid','ramp'])
def test_headerless_labels_and_metadata(tmp_path,mode):
    args = dict(cmyk=[100]*4) if mode=='grid' else dict(start=[0]*4,end=[100]*4,count=11)
    doc = layout(mode,**args,**template_values('card'))
    paths = export(doc,tmp_path)
    all_labels = []
    for page, pdf, manifest_path in zip(doc['pages'],paths[::2],paths[1::2]):
        manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
        assert manifest['schema_version']==2
        assert manifest['page']==page['number'] and manifest['total_pages']==len(doc['pages'])
        assert manifest['patches']==page['patches']
        labels=pdf_labels(pdf)
        assert [text for text,_ in labels]==[patch['label'] for patch in page['patches']]
        for patch,(text,size) in zip(page['patches'],labels):
            assert patch['id'] and text.startswith('C')
            assert MIN_LABEL_PT <= size <= 7
            assert size==pytest.approx(patch['label_font_pt'],abs=1e-5)
            assert stringWidth(text,LABEL_FONT,size)<=patch['rect_mm'][2]*mm+1e-4
            assert '\n' not in text
        all_labels += [text for text,_ in labels]
        assert verify(pdf,manifest_path)
    if mode=='grid':
        assert all_labels.count('C100 M100 Y100 K100 *')==1
    else:
        assert all_labels[0]=='C0 M0 Y0 K0 >'
        assert all_labels[-1]=='C100 M100 Y100 K100 <'


@pytest.mark.parametrize('suffix', [' *',' >',' <',''])
def test_minimum_boundary_all_markers(suffix):
    label='C100 M100 Y100 K100'+suffix
    boundary=stringWidth(label,LABEL_FONT,MIN_LABEL_PT)/mm
    # Use the endpoint/reference owning the longest label in each case.
    if suffix in (' *',''):
        args=dict(cmyk=[100]*4,cols=1,rows=1)
        mode='grid'
        if not suffix:
            # Plain label width is checked through a non-reference clamped patch.
            args.update(cols=2)
            # Reference still has *, so its larger boundary governs the layout.
            boundary=stringWidth(label+' *',LABEL_FONT,MIN_LABEL_PT)/mm
    else:
        args=dict(start=[100]*4 if suffix==' >' else [0]*4,
                  end=[0]*4 if suffix==' >' else [100]*4,count=2)
        mode='ramp'
    with pytest.raises(ValueError,match='최소 4.5pt'):
        layout(mode,**args,patch_size=boundary-1e-6)
    doc=layout(mode,**args,patch_size=boundary+1e-6)
    assert min(p['label_font_pt'] for page in doc['pages'] for p in page['patches'])==pytest.approx(MIN_LABEL_PT,abs=1e-5)


def test_automatic_height_and_card_capacity():
    doc=layout('grid',cmyk=[40,70,20,0],cols=3,rows=7)
    size=(505-40-6*3)/7-6
    first,last=doc['pages'][0]['patches'][0],doc['pages'][0]['patches'][-1]
    assert first['rect_mm'][2]==pytest.approx(size)
    assert first['rect_mm'][1]+size==pytest.approx(485)
    assert last['rect_mm'][1]-6==pytest.approx(20)
    card=layout('grid',cmyk=[100]*4,**template_values('card'))
    patches=card['pages'][0]['patches']
    assert len(patches)==8
    assert sorted({p['rect_mm'][0] for p in patches})==[2,21,40,59]
    assert sorted({p['rect_mm'][1] for p in patches})==[9,34]


@pytest.mark.parametrize('change', ['extra_header','missing_duplicate','font_size','font_face','text_position','line_move','ink','manifest_label','manifest_font'])
def test_verifier_rejects_label_tampering(tmp_path,change):
    paths=export(layout('grid',cmyk=[100]*4,**template_values('card')),tmp_path)
    pdf_path,manifest_path=paths[:2]
    if change.startswith('manifest'):
        manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
        manifest['patches'][0]['label' if change=='manifest_label' else 'label_font_pt']='R7C1 bad' if change=='manifest_label' else 7
        Path(manifest_path).write_text(json.dumps(manifest),encoding='utf-8')
        with pytest.raises(ValueError):verify(pdf_path,manifest_path)
        return
    bad=tmp_path/'bad.pdf'
    with pikepdf.open(pdf_path) as pdf:
        content=pdf.pages[0].Contents.read_bytes()
        if change=='extra_header':
            content+=b'\nBT /F1 8 Tf 1 0 0 1 10 140 Tm (grid unwanted header) Tj ET\n'
        elif change=='missing_duplicate':
            # Adjacent clamped patches share labels: membership-only checks miss this.
            instructions=list(pikepdf.parse_content_stream(pdf.pages[0]))
            index=next(i for i,(_,op) in enumerate(instructions) if str(op)=='Tj')
            del instructions[index]
            content=pikepdf.unparse_content_stream(instructions)
        elif change=='font_face':
            pdf.pages[0].Resources.Font['/F1'].BaseFont=pikepdf.Name('/Courier')
        else:
            instructions=list(pikepdf.parse_content_stream(pdf.pages[0]))
            first_text=next(i for i,(_,op) in enumerate(instructions) if str(op)=='Tj')
            target='Tf' if change=='font_size' else 'k' if change=='ink' else 'Tm'
            index=max(i for i,(_,op) in enumerate(instructions[:first_text]) if str(op)==target)
            args,op=instructions[index];args=list(args)
            if change=='font_size':args[1]=4
            elif change=='text_position':args[5]=float(args[5])+10
            elif change=='ink':args=[1,0,0,0]
            if change=='line_move':
                instructions.insert(first_text,pikepdf.ContentStreamInstruction([],pikepdf.Operator('T*')))
            else:
                instructions[index]=pikepdf.ContentStreamInstruction(args,op)
            content=pikepdf.unparse_content_stream(instructions)
        pdf.pages[0].Contents=pdf.make_stream(content)
        pdf.save(bad)
    with pytest.raises(ValueError):verify(bad,manifest_path)


def test_legacy_schema_one_still_verified(tmp_path):
    # Previous output contract: header plus ID-prefixed labels, same stored keys.
    pdf_path=tmp_path/'legacy.pdf';manifest_path=tmp_path/'legacy.json'
    patch=dict(id='R1C1',cmyk=[40,70,20,0],rect_mm=[20,420,50,50],
               reference=True,label='R1C1 C40 M70 Y20 K0 *',label_font_pt=7)
    canvas=Canvas(str(pdf_path),pagesize=(305*mm,505*mm))
    canvas.setFillColorCMYK(0,0,0,1);canvas.setFont('Helvetica',8)
    canvas.drawString(20*mm,480*mm,'grid C40_M70_Y20_K0_CM_s1 | 1/1 | R1C1 - R1C1')
    canvas.setFillColorCMYK(.4,.7,.2,0);canvas.rect(20*mm,420*mm,50*mm,50*mm,fill=1,stroke=0)
    canvas.setFillColorCMYK(0,0,0,1);canvas.setFont('Helvetica',7)
    canvas.drawString(20*mm,417*mm,patch['label']);canvas.save()
    manifest=dict(schema_version=1,paper_mm=[305,505],settings={},page=1,total_pages=1,patches=[patch])
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    assert verify(pdf_path,manifest_path)
    manifest['patches'][0]['cmyk'][0]=41
    manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(ValueError):verify(pdf_path,manifest_path)


def test_preview_uses_engine_font_and_text(tmp_path,monkeypatch):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QPainter
    from color_patch_maker.gui.window import MainWindow
    import color_patch_maker.gui.preview as preview
    app=QApplication.instance() or QApplication([])
    drawn=[]
    class RecordingPainter(QPainter):
        def drawText(self,*args):
            drawn.append((args[-1],self.font().pointSizeF()))
            return super().drawText(*args)
    monkeypatch.setattr(preview,'QPainter',RecordingPainter)
    window=MainWindow(QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat))
    try:
        doc=layout('grid',cmyk=[100]*4,**template_values('card'))
        window.preview.paper.set_document(doc)
        window.show();app.processEvents()
        drawn.clear();window.preview.paper.grab()
        paper=window.preview.paper
        scale=paper.paper_rect().width()/doc['paper_mm'][0]
        assert [text for text,_ in drawn]==[p['label'] for p in doc['pages'][0]['patches']]
        for (_,size),patch in zip(drawn,doc['pages'][0]['patches']):
            assert size==pytest.approx(patch['label_font_pt']*scale*25.4/paper.logicalDpiX())
        assert paper.patches==doc['pages'][0]['patches']
    finally:window.close()
