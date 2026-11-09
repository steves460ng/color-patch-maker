"""Write exclusive output bundles and verify our restricted PDF drawing format."""
import json
from pathlib import Path

import pikepdf
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from color_patch_maker.engine import LABEL_FONT, MIN_LABEL_PT, patch_label

MANIFEST_SCHEMA_VERSION = 2


def verify(pdf_path, manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    version = manifest.get('schema_version')
    if type(version) is not int or version not in (1, MANIFEST_SCHEMA_VERSION):
        raise ValueError('지원하지 않는 매니페스트 버전입니다.')
    with pikepdf.open(pdf_path) as pdf:
        if len(pdf.pages) != 1:
            raise ValueError('PDF는 정확히 한 페이지여야 합니다.')
        page = pdf.pages[0]
        expected_box = [0, 0, *(v*mm for v in manifest['paper_mm'])]
        if any(abs(float(a)-b) > .001 for a, b in zip(page.MediaBox, expected_box)):
            raise ValueError('PDF 용지 치수가 다릅니다.')
        if page.get('/Rotate', 0) != 0 or page.get('/UserUnit', 1) != 1:
            raise ValueError('PDF 좌표계가 변경되었습니다.')
        rects, labels, text_states = [], [], []
        font_name, font_size, text_matrix = None, None, None
        fill, pending = None, None
        leading = 0
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
            elif op == 'Tf':
                font_name = str(page.Resources.Font[operands[0]].BaseFont)
                font_size = float(operands[1])
            elif op == 'BT':
                text_matrix = [1, 0, 0, 1, 0, 0]
            elif op == 'TL':
                leading = float(operands[0])
            elif op == 'T*' and text_matrix is not None:
                a, b, c, d, e, f = text_matrix
                text_matrix = [a, b, c, d, e-leading*c, f-leading*d]
            elif op == 'Tm':
                text_matrix = [float(v) for v in operands]
            elif op == 'Tj':
                labels.append(str(operands[0]))
                text_states.append((font_name, font_size, text_matrix, fill))
        if version == MANIFEST_SCHEMA_VERSION:
            expected_labels = [patch_label(p) for p in manifest['patches']]
            if labels != expected_labels or labels != [p['label'] for p in manifest['patches']]:
                raise ValueError('PDF 라벨 또는 헤더 없는 출력 형식이 다릅니다.')
            for (font, size, matrix, ink), patch in zip(text_states, manifest['patches']):
                x, y, width, _ = patch['rect_mm']
                expected_size = min(7, 7*width*mm/stringWidth(patch['label'], LABEL_FONT, 7))
                if (font != '/' + LABEL_FONT or size is None or
                        not MIN_LABEL_PT-1e-5 <= size <= 7+1e-5 or
                        abs(size-expected_size) > 1e-5 or
                        abs(size-patch['label_font_pt']) > 1e-5 or
                        stringWidth(patch['label'], LABEL_FONT, size) > width*mm+1e-4):
                    raise ValueError('PDF 라벨 글꼴·크기·폭이 다릅니다.')
                expected_matrix = [1, 0, 0, 1, x*mm, (y-3)*mm]
                if (matrix is None or len(matrix) != 6 or
                        any(abs(a-b) > .001 for a,b in zip(matrix, expected_matrix)) or
                        ink != [0, 0, 0, 100]):
                    raise ValueError('PDF 라벨 위치·색이 다릅니다.')
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


def candidate_paths(document, out_dir, version):
    """One bundle's base paths; shared by preview and exclusive reservation."""
    base = document['stem'] + (f'_v{version}' if version > 1 else '')
    count = len(document['pages'])
    return [Path(out_dir)/(base + (f'_{i+1:02}' if count>1 else '')) for i in range(count)]


def preview_paths(document, out_dir):
    """Predict all PDF/JSON paths without writing; export rechecks atomically."""
    version = 1
    while True:
        paths = [p.with_suffix(ext) for p in candidate_paths(document,out_dir,version) for ext in ('.pdf','.json')]
        if not any(p.exists() or p.is_symlink() for p in paths):
            return [str(p) for p in paths]
        version += 1


def export(document, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = document['pages']
    version = 1
    while True:
        paths = candidate_paths(document, out_dir, version)
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
            manifest = dict(schema_version=MANIFEST_SCHEMA_VERSION, settings=document['settings'], paper_mm=document['paper_mm'],
                            page=page['number'], total_pages=len(pages), patches=page['patches'])
            canvas = Canvas(str(path.with_suffix('.pdf')), pagesize=[v*mm for v in document['paper_mm']], invariant=1)
            for p in page['patches']:
                x, y, w, h = p['rect_mm']
                canvas.setFillColorCMYK(*(v/100 for v in p['cmyk']))
                canvas.rect(x*mm, y*mm, w*mm, h*mm, stroke=0, fill=1)
                canvas.setFillColorCMYK(0, 0, 0, 1)
                font_size = p['label_font_pt']
                canvas.setFont(LABEL_FONT, font_size)
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
