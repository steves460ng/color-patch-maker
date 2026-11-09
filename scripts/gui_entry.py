"""Frozen GUI entry point; optional offscreen packaging smoke check."""
import os
import sys
from PySide6.QtCore import QTimer, QSettings
from PySide6.QtWidgets import QApplication
from color_patch_maker.gui.window import MainWindow, app_icon

app = QApplication(sys.argv)
app.setWindowIcon(app_icon())
# Packaging checks use a temporary settings directory, never user settings.
smoke_settings = os.environ.get('CPM_OFFSCREEN_SMOKE_SETTINGS')
if smoke_settings and os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, smoke_settings)
window = MainWindow()
window.show()
if smoke_settings and os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    QTimer.singleShot(500, window.close)
sys.exit(app.exec())
