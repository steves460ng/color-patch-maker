import sys
from PySide6.QtWidgets import QApplication
from .window import MainWindow, app_icon


def main():
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
