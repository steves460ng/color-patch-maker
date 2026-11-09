"""Write exclusive output bundles and verify our restricted PDF drawing format."""
import json
from pathlib import Path

import pikepdf
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth


def verify(pdf_path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text())
    with pikepdf.open(pdf_path) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError('PDF는 정확히 한 페이지여야 합니다.')
        page = pdf.pages[0]
        expected_box = [0, 0, *(v*mm for v in manifest['paper_mm'])]
        if any(abs(float(a)-b) > .001 for a, b in zip(page.MediaBox, expected_box)):
            raise ValueError('PDF 용지 치수가 다릅니다.')
        if page.get('/Rotate', 0) != 0 or page.get('/UserUnit', 1) != 1:
            raise ValueError('PDF 좌표계가 변경되었습니다.')
        rects, labels = [], []
        fill, pending = None, None
        allowed = {'cm', 'BT', 'ET', 'Tf', 'TL', 'Tm', 'Tj', 'T*', 'k', 'n', 're', 'f*', 'f'}
        for operands, operator in pikepdf.parse_content_stream(page):
            op = str(operator)
            if op not in allowed:
                raise ValueError(f'지원하지 않는 PDF 그리기 연산: {op}')
            if op == 'cm' and [float(x) for x in operands] != [1, 0, 0, 1, 0, 0]:
                raise ValueError('PDF 좌표 변환이 변경되었습니다.')
            if op == 'k':
                fill = [float(v)*100 for v in operands]
            elif op == 're':
                pending = [float(v)/mm for v in operands]
            elif op in ('f', 'f*'):
                if pending is None or fill is None:
                    raise ValueError('DeviceCMYK 사각형이 아닙니다.')
                rects.append((fill, pending))
                pending = None
            elif op == 'Tj':
                labels.append(str(operands[0]))
        if len(rects) != len(manifest['patches']):
            raise ValueError('PDF 패치 개수가 다릅니다.')
        for (values, rect), patch in zip(rects, manifest['patches']):
            if any(type(v) is not int or not 0 <= v <= 100 for v in patch['cmyk']):
                raise ValueError('매니페스트 CMYK가 정수가 아닙니다.')
            if len(values) != 4 or any(abs(a-b) > .0001 for a, b in zip(values, patch['cmyk'])):
                raise ValueError('PDF CMYK 저장값이 다릅니다.')
            if any(abs(a-b) > .001 for a, b in zip(rect, patch['rect_mm'])):
                raise ValueError('PDF 패치 좌표가 다릅니다.')
            if patch['label'] not in labels:
                raise ValueError('PDF 라벨이 다릅니다.')
    return True


def export(document, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = document['pages']
    version = 1
    while True:
        base = document['stem'] + (f'_v{version}' if version > 1 else '')
        paths = [out_dir / (base + (f'_{i+1:02}' if len(pages)>1 else '')) for i in range(len(pages))]
        reserved = []
        try:
            for path in paths:
                for suffix in ('.pdf', '.json'):
                    target = path.with_suffix(suffix)
                    with target.open('xb'):
                        pass
                    reserved.append(target)
            break
        except FileExistsError:
            for target in reserved:
                target.unlink()
            version += 1
        except Exception:
            for target in reserved:
                target.unlink()
            raise
    try:
        for path, page in zip(paths, pages):
            manifest = dict(schema_version=1, settings=document['settings'], paper_mm=document['paper_mm'],
                            page=page['number'], total_pages=len(pages), patches=page['patches'])
            canvas = Canvas(str(path.with_suffix('.pdf')), pagesize=[v*mm for v in document['paper_mm']], invariant=1)
            canvas.setFillColorCMYK(0, 0, 0, 1)
            canvas.setFont('Helvetica', 8)
            header = f"{document['settings']['mode']} {document['stem']} | {page['number']}/{len(pages)} | {page['patches'][0]['id']} - {page['patches'][-1]['id']}"
            available = (document['paper_mm'][0]-2*document['settings']['margin'])*mm
            canvas.setFont('Helvetica', min(8, 8*available/stringWidth(header, 'Helvetica', 8)))
            canvas.drawString(document['settings']['margin']*mm, (document['paper_mm'][1]-document['settings']['margin']-5)*mm, header)
            for p in page['patches']:
                x, y, w, h = p['rect_mm']
                canvas.setFillColorCMYK(*(v/100 for v in p['cmyk']))
                canvas.rect(x*mm, y*mm, w*mm, h*mm, stroke=0, fill=1)
                canvas.setFillColorCMYK(0, 0, 0, 1)
                font_size = min(7, 7*w*mm/stringWidth(p['label'], 'Helvetica', 7))
                canvas.setFont('Helvetica', font_size)
                canvas.drawString(x*mm, (y-3)*mm, p['label'])
            canvas.showPage()
            canvas.save()
            path.with_suffix('.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
            verify(path.with_suffix('.pdf'), path.with_suffix('.json'))
    except Exception:
        for target in reserved:
            target.unlink(missing_ok=True)
        raise
    return [str(p) for p in reserved]
