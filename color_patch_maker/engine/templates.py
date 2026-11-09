"""Shared built-in layouts; values contain no color or mode inputs."""
from copy import deepcopy
from .messages import t, EngineError

_TEMPLATES = {
    'default': dict(paper=[305, 505], margin=20, gap=3, patch_size=None),
    'card': dict(paper=[85.6, 54], margin=2, gap=1, patch_size=18),
}
_LABEL_KEYS = {'default': 'template.default', 'card': 'template.card'}


def template_names():
    return tuple(_TEMPLATES)


def template_label(identifier, language='ko'):
    return t(_LABEL_KEYS[identifier], language)


def template_id(name):
    if name in _TEMPLATES:
        return name
    for identifier in _TEMPLATES:
        if name == template_label(identifier):
            return identifier
    raise EngineError('template.unknown', target='template', value=name)


def legacy_template_names():
    return frozenset((t('template.custom', 'en'), *(template_label(key, 'en') for key in _TEMPLATES)))


def reserved_template_names():
    return frozenset((*_TEMPLATES, *(template_label(key, 'ko') for key in _TEMPLATES),
                      t('template.custom', 'ko'), *legacy_template_names()))


def template_values(name):
    return deepcopy(_TEMPLATES[template_id(name)])


def validate_template(values):
    """Validate layout independently of current mode/color, using engine rules."""
    from . import layout
    if not isinstance(values, dict) or set(values) != {'paper', 'margin', 'gap', 'patch_size'}:
        raise EngineError('template.fields', target='template', value=values)
    paper = values['paper']
    if not isinstance(paper, (list, tuple)) or len(paper) != 2:
        raise EngineError('template.paper', target='paper', value=paper)
    document = layout('grid', cmyk=[0, 0, 0, 0], cols=1, rows=1, **values)
    return {key: deepcopy(document['settings'][key]) for key in values}
