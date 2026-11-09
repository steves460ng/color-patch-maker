"""Persist only folder and shared layout; never color or mode inputs."""
from pathlib import Path
from PySide6.QtWidgets import QLineEdit
from color_patch_maker.engine import layout

DEFAULTS = dict(layout_width='305',layout_height='505',layout_margin='20',layout_gap='3',layout_patch_size='auto')


def restore(window, settings):
    values = {name: str(settings.value(name,default)) for name,default in DEFAULTS.items()}
    try:
        layout('grid', cmyk=[40,70,20,0], cols=1, rows=1, paper=[values['layout_width'],values['layout_height']],
               margin=values['layout_margin'],gap=values['layout_gap'],
               patch_size=None if values['layout_patch_size']=='auto' else values['layout_patch_size'])
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
