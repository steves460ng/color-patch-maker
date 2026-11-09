"""Shared built-in layouts; values contain no color or mode inputs."""
from copy import deepcopy

_TEMPLATES = {
    '기본': dict(paper=[305, 505], margin=20, gap=3, patch_size=None),
    '카드': dict(paper=[85.6, 54], margin=3, gap=1, patch_size=25),
}
_ALIASES = {'default': '기본', 'card': '카드'}


def template_names():
    return tuple(_TEMPLATES)


def template_values(name):
    name = _ALIASES.get(name, name)
    if name not in _TEMPLATES:
        raise ValueError('템플릿: 기본, 카드, default, card 중 선택하세요.')
    return deepcopy(_TEMPLATES[name])


def validate_template(values):
    """Validate layout independently of current mode/color, using engine rules."""
    from . import layout
    if not isinstance(values, dict) or set(values) != {'paper', 'margin', 'gap', 'patch_size'}:
        raise ValueError('템플릿: 용지, 여백, 간격, 패치 크기를 모두 입력하세요.')
    paper = values['paper']
    if not isinstance(paper, (list, tuple)) or len(paper) != 2:
        raise ValueError('템플릿: 용지 가로·세로 두 값이 필요합니다.')
    document = layout('grid', cmyk=[0, 0, 0, 0], cols=1, rows=1, **values)
    return {key: deepcopy(document['settings'][key]) for key in values}
