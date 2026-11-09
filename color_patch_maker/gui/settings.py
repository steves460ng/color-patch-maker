"""Persist only folder and shared layout; never color or mode inputs."""
from pathlib import Path
from PySide6.QtWidgets import QLineEdit
from color_patch_maker.engine import validate_template, template_values

def fields_from_values(values):
    def text(value):
        if value is None:
            return 'auto'
        value = float(value)
        return str(int(value)) if value.is_integer() else str(value)
    return dict(zip(('layout_width', 'layout_height', 'layout_margin', 'layout_gap', 'layout_patch_size'),
                    map(text, [*values['paper'], values['margin'], values['gap'], values['patch_size']])))


def values_from_fields(values):
    return dict(paper=[values['layout_width'], values['layout_height']],
                margin=values['layout_margin'], gap=values['layout_gap'],
                patch_size=None if values['layout_patch_size']=='auto' else values['layout_patch_size'])


DEFAULTS = fields_from_values(template_values('default'))


def restore(window, settings):
    values = {name: str(settings.value(name,default)) for name,default in DEFAULTS.items()}
    try:
        validate_template(values_from_fields(values))
    except (ValueError, TypeError, OverflowError):
        values = DEFAULTS
    for name,value in values.items():
        window.findChild(QLineEdit,name).setText(value)
    folder = str(settings.value('output_folder',''))
    missing = bool(folder and not Path(folder).is_dir())
    window.findChild(QLineEdit,'output_folder').setText('' if missing else folder)
    return '저장된 폴더가 없어 초기화했습니다. 폴더를 다시 선택하세요.' if missing else ''


def save(window, settings):
    for name in [*DEFAULTS,'output_folder']:
        settings.setValue(name,window.findChild(QLineEdit,name).text())
    settings.sync()
