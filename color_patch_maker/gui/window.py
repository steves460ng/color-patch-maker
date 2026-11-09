"""Main window composition and input/preview controller."""
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
from .settings import restore, save
from .language import normalize_preference, resolve_language, translator
from color_patch_maker.engine.messages import t
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from .sidebar import Sidebar, named
from .preview import Preview
from .controller import Controller

ICON_PATH = Path(__file__).with_name('resources') / 'app.ico'


def app_icon():
    """Application icon shared by the window, taskbar and the built executable."""
    return QIcon(str(ICON_PATH))


class MainWindow(QMainWindow):
    def __init__(self, settings=None, locale_name=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings('ColorPatchMaker', 'ColorPatchMaker')
        self.language_preference = normalize_preference(self.settings.value('language', 'auto'))
        self.locale_name = locale_name
        self.language = resolve_language(self.language_preference, self.locale_name)
        self.t = translator(self.language)
        self.setObjectName('main_window')
        self.setWindowTitle(self.t('app.title'))
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1024, 720)
        self.resize(1200, 800)
        central = QWidget()
        box = QVBoxLayout(central)
        box.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        header.addWidget(QLabel(self.t('app.title')))
        header.addStretch()
        header.addWidget(named(QLabel('–'), 'paper_info'))
        self.language_combo = named(QComboBox(), 'language_selector')
        self.language_combo.setAccessibleName(self.t('language.title'))
        self.language_combo.addItem(self.t('language.auto'), 'auto')
        self.language_combo.addItem(t('language.ko', 'ko'), 'ko')
        self.language_combo.addItem(t('language.en', 'en'), 'en')
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.language_preference))
        # Match the existing title row's height so the body retains its space.
        self.language_combo.setFixedHeight(15)
        header.addWidget(self.language_combo)
        box.addLayout(header)
        columns = QHBoxLayout()
        columns.setSpacing(12)
        self.sidebar = Sidebar(self.t)
        self.preview = Preview(self.t)
        columns.addWidget(self.sidebar)
        columns.addWidget(self.preview, 1)
        box.addLayout(columns, 1)
        self.setCentralWidget(central)
        for before, after in zip(self.sidebar.focus_widgets, self.sidebar.focus_widgets[1:]):
            QWidget.setTabOrder(before, after)
        self.setStyleSheet('''
            QWidget { font-size: 12px; }
            QGroupBox { font-weight: bold; border: 1px solid #c5cbd2;
                        border-radius: 5px; margin-top: 7px; padding-top: 5px; }
            QGroupBox::title { subcontrol-origin: margin; left: 9px; }
            QTabBar::tab { padding: 10px 18px; }
            QScrollArea { border: none; }
            QPushButton { min-height: 28px; }
        ''')
        self.restore_notice = restore(self, self.settings)
        self.controller = Controller(self)
        self.language_combo.currentIndexChanged.connect(self.change_language)

    def change_language(self):
        self.language_preference = self.language_combo.currentData()
        self.settings.setValue('language', self.language_preference)
        self.settings.sync()
        restart_notice = self.t('language.restart')
        if resolve_language(self.language_preference, self.locale_name) != self.language:
            self.controller.output.status(restart_notice)
        elif self.controller.widget('output_status').text() == restart_notice:
            self.controller.output.status('')

    def closeEvent(self, event):
        if self.controller.output.busy:
            self.controller.output.status(self.t('output.close_busy'))
            event.ignore()
            return
        save(self, self.settings)
        event.accept()
