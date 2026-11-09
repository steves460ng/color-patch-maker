"""GUI-independent patch and layout engine; coordinates use bottom-left mm."""
import math
import re

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

MIN_LABEL_PT = 6
LABEL_FONT = "Helvetica"
FIT_TOLERANCE_MM = 1e-9


def capacity(available, cell):
    """Ignore sub-nanometre rounding at an exact physical fit."""
    return math.floor((available + FIT_TOLERANCE_MM) / cell)


def integer(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not re.fullmatch(r'[+-]?[0-9]+', str(value)):
        raise ValueError(f'{name}: 인쇄기는 정수값만 출력합니다. 정수를 입력하세요.')
    result = int(value)
    if result < minimum or (maximum is not None and result > maximum):
        raise ValueError(f'{name}: {minimum} 이상' + (f' {maximum} 이하' if maximum is not None else '') + '로 입력하세요.')
    return result


def color(values):
    if len(values) != 4:
        raise ValueError('CMYK: 네 값을 입력하세요.')
    return [integer(v, k, 0, 100) for k, v in zip('CMYK', values)]


def number(value, name, minimum=0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: 숫자로 된 {minimum} 이상의 mm 값을 입력하세요.") from None
    if not math.isfinite(value) or value < minimum:
        raise ValueError(f'{name}: 유한한 {minimum} 이상의 mm 값을 입력하세요.')
    return value


def color_name(c):
    return '_'.join(f'{k}{v}' for k, v in zip('CMYK', c))


def layout(mode, *, cmyk=None, start=None, end=None, channels='CM', step=1,
           cols=None, rows=7, count=None, paper=(305, 505), margin=20, gap=3,
           patch_size=None):
    if mode not in ('grid', 'ramp'):
        raise ValueError('방식은 grid 또는 ramp여야 합니다.')
    paper = [number(v, 'paper') for v in paper]
    if len(paper) != 2:
        raise ValueError('paper: 폭과 높이를 입력하세요.')
    margin, gap = number(margin, 'margin'), number(gap, 'gap')
    width, height = paper[0] - 2 * margin, paper[1] - 2 * margin - 15
    size = None if patch_size is None else number(patch_size, 'patch-size', 5)
    if width <= 0 or height <= 6:
        raise ValueError('paper/margin: 패치 공간이 없습니다. 용지를 키우거나 여백을 줄이세요.')
    settings = dict(mode=mode, paper=paper, margin=margin, gap=gap, patch_size=size)
    patches = []
    if mode == 'grid':
        cmyk = color(cmyk)
        if channels not in ('CM', 'CY', 'CK', 'MY', 'MK', 'YK'):
            raise ValueError('channels: CM, CY, CK, MY, MK, YK 중 선택하세요.')
        step = integer(step, 'step', 1)
        cols, rows = integer(cols if cols is not None else 7, 'cols', 1), integer(rows, 'rows', 1)
        for r in range(rows):
            for c in range(cols):
                raw = cmyk.copy()
                raw['CMYK'.index(channels[0])] += (c - (cols - 1) // 2) * step
                raw['CMYK'.index(channels[1])] += ((rows - 1) // 2 - r) * step
                values = [min(100, max(0, v)) for v in raw]
                patches.append(dict(id=f'R{rows-r}C{c+1}', cmyk=values, raw=raw,
                                    clamped=raw != values, reference=(c == (cols-1)//2 and r == (rows-1)//2)))
        settings.update(cmyk=cmyk, channels=channels, step=step, cols=cols, rows=rows)
        stem = f'{color_name(cmyk)}_{channels}_s{step}'
    else:
        start, end = color(start), color(end)
        if start == end:
            raise ValueError('from/to: 서로 다른 시작·끝 값을 입력하세요.')
        count = integer(count, 'count', 2)
        auto_cols = 7 if size is None else capacity(width + gap, size + gap)
        cols = integer(auto_cols if cols in (None, 'auto') else cols, 'cols', 1)
        rows = (count + cols - 1) // cols
        for i in range(count):
            values = [(2 * (a * (count-1) + (b-a)*i) + count-1) // (2*(count-1)) for a, b in zip(start, end)]
            patches.append(dict(id=f'{i+1:02}', cmyk=values, endpoint='start' if i == 0 else 'end' if i == count-1 else ''))
        settings.update(start=start, end=end, count=count, cols=cols)
        stem = f'{color_name(start)}_to_{color_name(end)}_n{count}'
    automatic = size is None
    if automatic:
        size = min((width - (cols-1)*gap)/cols, (height - (rows-1)*gap)/rows - 6)
        if size < 5:
            raise ValueError('patch-size: 자동 크기가 5mm 미만입니다. 패치 크기를 지정하세요.')
    capacity_x = cols if automatic else capacity(width + gap, size + gap)
    capacity_y = rows if automatic else capacity(height + gap, size + 6 + gap)
    if min(capacity_x, capacity_y) < 1:
        raise ValueError('patch-size: 패치가 용지에 들어가지 않습니다. 크기를 줄이세요.')
    if mode == 'ramp' and cols > capacity_x:
        raise ValueError(f'cols: 최대 {capacity_x}칸으로 줄이세요.')
    pages = []
    for top in range(0, rows, capacity_y):
        for left in range(0, cols, capacity_x):
            page = []
            for r in range(top, min(rows, top + capacity_y)):
                for c in range(left, min(cols, left + capacity_x)):
                    index = r * cols + c
                    if index >= len(patches):
                        continue
                    p = patches[index].copy()
                    p['rect_mm'] = [margin + (c-left)*(size+gap), paper[1]-margin-15-size-(r-top)*(size+6+gap), size, size]
                    p['label'] = p['id'] + ' ' + color_name(p['cmyk']).replace('_', ' ') + (' *' if p.get('reference') else '') + (' >' if p.get('endpoint') == 'start' else ' <' if p.get('endpoint') == 'end' else '')
                    font_size = min(7, 7*size*mm/stringWidth(p['label'], LABEL_FONT, 7))
                    if font_size < MIN_LABEL_PT:
                        raise ValueError(f'라벨: 최소 {MIN_LABEL_PT}pt를 확보할 수 없습니다. 패치 크기를 키우거나 칸 수를 줄이세요.')
                    p['label_font_pt'] = font_size
                    page.append(p)
            pages.append(dict(patches=page, number=len(pages)+1))
    return dict(settings=settings, stem=stem, paper_mm=paper, pages=pages,
                warnings=[f'{sum(p.get("clamped", False) for p in patches)}개 패치 0/100 고정'] if any(p.get('clamped') for p in patches) else [])
