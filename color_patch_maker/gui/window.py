"""Main window composition and input/preview controller."""
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from .sidebar import Sidebar, named
from .preview import Preview
from .controller import Controller


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName('main_window')
        self.setWindowTitle('Color Patch Maker')
        self.setMinimumSize(1024, 720)
        self.resize(1200, 800)
        central = QWidget()
        box = QVBoxLayout(central)
        box.setContentsMargins(12, 12, 12, 12)
        header = QHBoxLayout()
        header.addWidget(QLabel('Color Patch Maker'))
        header.addStretch()
        header.addWidget(named(QLabel('305×505mm · DeviceCMYK'), 'paper_info'))
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
        self.controller = Controller(self)
