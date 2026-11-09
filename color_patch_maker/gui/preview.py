"""Aspect-preserving paper placeholder, without patch drawing."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from .sidebar import named, label, button


class PaperPlaceholder(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName('paper_placeholder')
        self.setMinimumSize(100, 100)
        self.setAccessibleName('미리보기 용지')

    def paper_rect(self):
        height = min(max(0, self.height()-32), max(0, self.width()-32)*505/305)
        width = height*305/505
        return QRectF((self.width()-width)/2, (self.height()-height)/2, width, height)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#eef0f2'))
        rect = self.paper_rect()
        painter.setPen(QColor('#c5cbd2'))
        painter.setBrush(QColor('white'))
        painter.drawRect(rect)
        painter.setPen(QColor('#626c77'))
        painter.drawText(rect.adjusted(16, 16, -16, -16), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                         '미리보기는 다음 단계에서 연결됩니다')


class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName('preview')
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        self.paper = PaperPlaceholder()
        box.addWidget(self.paper, 1)
        pager = QHBoxLayout()
        pager.addStretch()
        pager.addWidget(button('이전', 'previous_page_button'))
        pager.addWidget(label('장 1 / 1', 'page_indicator'))
        pager.addWidget(button('다음', 'next_page_button'))
        pager.addStretch()
        box.addLayout(pager)
        note = label('화면 색은 인쇄색과 다를 수 있습니다', 'screen_color_note')
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        box.addWidget(note)
