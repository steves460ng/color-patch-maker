"""Resolve one window's language without changing engine or process globals."""
from functools import partial
from PySide6.QtCore import QLocale
from color_patch_maker.engine.messages import t, EngineError, Message


def normalize_preference(value):
    return value if value in ('auto', 'ko', 'en') else 'auto'


def system_locale_name():
    return QLocale.system().name()


def resolve_language(preference='auto', locale_name=None):
    preference = normalize_preference(preference)
    if preference != 'auto':
        return preference
    name = locale_name if locale_name is not None else system_locale_name()
    return 'ko' if name.lower().replace('-', '_').split('_')[0] == 'ko' else 'en'


def translator(language):
    return partial(t, language=language)


def error_text(error, language):
    return error.render(language) if isinstance(error, (EngineError, Message)) else str(error)
