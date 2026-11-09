"""GUI-independent patch and layout engine; coordinates use bottom-left mm."""
from color_patch_maker.engine.messages import EngineError, Message
from .templates import template_names, template_values, validate_template, template_label, template_id, reserved_template_names

import math
import re

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

MIN_LABEL_PT = 4.5
LABEL_FONT = "Helvetica"
FIT_TOLERANCE_MM = 1e-9


def capacity(available, cell):
    """Ignore sub-nanometre rounding at an exact physical fit."""
    return math.floor((available + FIT_TOLERANCE_MM) / cell)


def integer(value, name, minimum=0, maximum=None):
    if isinstance(value, bool) or not re.fullmatch(r'[+-]?[0-9]+', str(value)):
        raise EngineError('input.integer', target=name, value=value, name=name)
    result = int(value)
    if result < minimum or (maximum is not None and result > maximum):
        if maximum is None:
            raise EngineError('input.minimum', target=name, value=value, name=name, minimum=minimum)
        raise EngineError('input.range', target=name, value=value, name=name, minimum=minimum, maximum=maximum)
    return result


def color(values):
    if len(values) != 4:
        raise EngineError('input.color_count', target='cmyk', value=values)
    return [integer(v, k, 0, 100) for k, v in zip('CMYK', values)]


def number(value, name, minimum=0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise EngineError('input.number', target=name, value=value, name=name, minimum=minimum) from None
    if not math.isfinite(value) or value < minimum:
        raise EngineError('input.finite', target=name, value=value, name=name, minimum=minimum)
    return value


def color_name(c):
    return '_'.join(f'{k}{v}' for k, v in zip('CMYK', c))


def layout(mode, *, cmyk=None, start=None, end=None, channels='CM', step=1,
           cols=None, rows=7, count=None, paper=(305, 505), margin=20, gap=3,
           patch_size=None):
    if mode not in ('grid', 'ramp'):
        raise EngineError('input.mode', target='mode', value=mode)
    paper = [number(v, 'paper') for v in paper]
    if len(paper) != 2:
        raise EngineError('input.paper_count', target='paper', value=paper)
    margin, gap = number(margin, 'margin'), number(gap, 'gap')
    width, height = paper[0] - 2 * margin, paper[1] - 2 * margin
    size = None if patch_size is None else number(patch_size, 'patch-size', 5)
    if width <= 0 or height <= 6:
        raise EngineError('layout.paper_space', target='paper/margin', value=dict(paper=paper, margin=margin))
    settings = dict(mode=mode, paper=paper, margin=margin, gap=gap, patch_size=size)
    patches = []
    if mode == 'grid':
        cmyk = color(cmyk)
        if channels not in ('CM', 'CY', 'CK', 'MY', 'MK', 'YK'):
            raise EngineError('input.channels', target='channels', value=channels)
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
            raise EngineError('input.identical_endpoints', target='from/to', value=dict(start=start, end=end))
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
            raise EngineError('layout.auto_small', target='patch_size', value=size)
    capacity_x = cols if automatic else capacity(width + gap, size + gap)
    capacity_y = rows if automatic else capacity(height + gap, size + 6 + gap)
    if min(capacity_x, capacity_y) < 1:
        raise EngineError('layout.patch_fit', target='patch_size', value=size)
    if mode == 'ramp' and cols > capacity_x:
        raise EngineError('layout.columns', target='cols', value=cols, maximum=capacity_x)
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
                    p['rect_mm'] = [margin + (c-left)*(size+gap), paper[1]-margin-size-(r-top)*(size+6+gap), size, size]
                    p['label'] = patch_label(p)
                    font_size = min(7, 7*size*mm/stringWidth(p['label'], LABEL_FONT, 7))
                    if font_size < MIN_LABEL_PT:
                        raise EngineError('layout.label_size', target='patch_size', value=size, minimum=MIN_LABEL_PT)
                    p['label_font_pt'] = font_size
                    page.append(p)
            pages.append(dict(patches=page, number=len(pages)+1))
    return dict(settings=settings, stem=stem, paper_mm=paper, pages=pages,
                warnings=[Message("warning.clamped", count=sum(p.get("clamped", False) for p in patches))] if any(p.get('clamped') for p in patches) else [])


def input_errors(mode, **values):
    """Return field-keyed errors using the same scalar validators as layout().

    Keys use argument names, with .index for CMYK and paper components.
    Cross-field/layout errors remain the responsibility of layout().
    """
    errors = {}
    def check(key, validator, *args):
        try:
            validator(*args)
        except ValueError as exc:
            exc.target = key
            errors[key] = exc
    for key in (('cmyk',) if mode == 'grid' else ('start', 'end')):
        for i, value in enumerate(values[key]):
            check(f'{key}.{i}', integer, value, 'CMYK'[i], 0, 100)
    for i, value in enumerate(values['paper']):
        check(f'paper.{i}', number, value, 'paper')
    for key in ('margin', 'gap'):
        check(key, number, values[key], key)
    if values['patch_size'] is not None:
        check('patch_size', number, values['patch_size'], 'patch-size', 5)
    for key in (('step', 'cols', 'rows') if mode == 'grid' else ('count', 'cols')):
        if key == 'cols' and mode == 'ramp' and values[key] == 'auto':
            continue
        check(key, integer, values[key], key, 2 if key == 'count' else 1)
    return errors


def output_names(document):
    """PDF names before filesystem collision handling."""
    count = len(document['pages'])
    return [document['stem'] + (f'_{i+1:02}' if count > 1 else '') + '.pdf' for i in range(count)]


def patch_label(patch):
    """Printed CMYK line; identifiers remain separate manifest/GUI data."""
    suffix = ' *' if patch.get('reference') else ''
    if patch.get('endpoint'):
        suffix = ' >' if patch['endpoint'] == 'start' else ' <'
    return color_name(patch['cmyk']).replace('_', ' ') + suffix
