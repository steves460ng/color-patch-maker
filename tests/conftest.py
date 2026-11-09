"""Never read or write the developer's real Qt settings during tests."""
import pytest
from PySide6.QtCore import QSettings


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path/"config"))
    import color_patch_maker.gui.language as language
    monkeypatch.setattr(language, 'system_locale_name', lambda: 'ko_KR')
    import color_patch_maker.gui.window as module
    monkeypatch.setattr(module, 'QSettings', lambda *args: QSettings(str(tmp_path/'settings.ini'),QSettings.Format.IniFormat))
