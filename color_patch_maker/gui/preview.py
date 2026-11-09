"""Aspect-preserving engine layout preview and patch hit testing."""
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from .sidebar import named, label, button
from color_patch_maker.engine import LABEL_FONT, template_values


def screen_color(values):
    c, m, y, k = [v/100 for v in values]
    return QColor.fromRgbF((1-c)*(1-k), (1-m)*(1-k), (1-y)*(1-k))


class PaperPlaceholder(QWidget):
    patch_clicked = Signal(object)
    def __init__(self):
        super().__init__()
        self.setObjectName('paper_placeholder')
        self.setMinimumSize(100, 100)
        self.setAccessibleName('미리보기 용지')
        self.document = None
        self.page_index = 0
        self.selected_id = None

    def paper_rect(self):
        pw, ph = self.document['paper_mm'] if self.document else template_values('default')['paper']
        height = min(max(0, self.height()-32), max(0, self.width()-32)*ph/pw)
        width = height*pw/ph
        return QRectF((self.width()-width)/2, (self.height()-height)/2, width, height)

    @property
    def patches(self):
        return self.document['pages'][self.page_index]['patches'] if self.document else []

    def set_document(self, document, page_index=0):
        self.document = document
        self.page_index = page_index
        self.selected_id = None
        self.update()

    def patch_rect(self, patch):
        paper = self.paper_rect()
        scale = paper.width()/self.document['paper_mm'][0]
        x, y, w, h = patch['rect_mm']
        return QRectF(paper.left()+x*scale, paper.bottom()-(y+h)*scale, w*scale, h*scale)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            patch = next((p for p in self.patches if self.patch_rect(p).contains(event.position())), None)
            self.patch_clicked.emit(patch)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor('#eef0f2'))
        rect = self.paper_rect()
        painter.setPen(QColor('#c5cbd2'))
        painter.setBrush(QColor('white'))
        painter.drawRect(rect)
        painter.setPen(QColor('#626c77'))
        if not self.document:
            painter.drawText(rect.adjusted(16,16,-16,-16), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                             '입력값을 확인하세요')
            return
        scale = rect.width()/self.document['paper_mm'][0]
        for patch in self.patches:
            box = self.patch_rect(patch)
            painter.fillRect(box, screen_color(patch['cmyk']))
            if patch.get('reference') or patch.get('endpoint') or patch['id'] == self.selected_id:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(QColor('#087fbe') if patch['id']==self.selected_id else QColor('#111111'), 2))
                painter.drawRect(box.adjusted(1,1,-1,-1))
            # Clip every label to its own engine-assigned 6 mm label strip.
            strip = QRectF(box.left(),box.bottom(),box.width(),6*scale)
            painter.save()
            painter.setClipRect(strip)
            painter.setPen(QColor('#111111'))
            font = QFont(LABEL_FONT)
            font.setPointSizeF(patch['label_font_pt']*scale*25.4/self.logicalDpiX())
            painter.setFont(font)
            painter.drawText(strip,Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,patch['label'])
            painter.restore()


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
