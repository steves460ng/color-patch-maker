"""Main window composition and input/preview controller."""
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
from .settings import restore, save
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from .sidebar import Sidebar, named
from .preview import Preview
from .controller import Controller

ICON_PATH = Path(__file__).with_name('resources') / 'app.ico'


def app_icon():
    """Application icon shared by the window, taskbar and the built executable."""
    return QIcon(str(ICON_PATH))


class MainWindow(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.setObjectName('main_window')
        self.setWindowTitle('Color Patch Maker')
        self.setWindowIcon(app_icon())
        self.setMinimumSize(1024, 720)
        self.resize(1200, 800)
        central = QWidget()
        box = QVBoxLayout(central)
        box.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        header.addWidget(QLabel('Color Patch Maker'))
        header.addStretch()
        header.addWidget(named(QLabel('–'), 'paper_info'))
        box.addLayout(header)
        columns = QHBoxLayout()
        columns.setSpacing(12)
        self.sidebar = Sidebar()
        self.preview = Preview()
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
        self.settings = settings if settings is not None else QSettings('ColorPatchMaker', 'ColorPatchMaker')
        self.restore_notice = restore(self, self.settings)
        self.controller = Controller(self)

    def closeEvent(self, event):
        if self.controller.output.busy:
            self.controller.output.status('PDF 작업이 끝난 뒤 창을 닫아 주세요.')
            event.ignore()
            return
        save(self, self.settings)
        event.accept()
