"""Settings widgets with stable names for future controller connections."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QToolButton, QTabBar, QScrollArea, QGroupBox,
    QSizePolicy, QStackedWidget,
)


def named(widget, name):
    widget.setObjectName(name)
    return widget


def label(text, name):
    result = named(QLabel(text), name)
    result.setWordWrap(True)
    return result


def button(text, name):
    result = named(QPushButton(text), name)
    result.setEnabled(False)
    return result


class ErrorLabel(QLabel):
    """Reserve space only for an actual message; keep fixed regions stable."""
    def __init__(self, name):
        super().__init__('')
        self.setObjectName(name)
        self.setWordWrap(True)
        self.setStyleSheet('color: #b3261e;')
        self.hide()

    def setText(self, text):
        super().setText(text)
        self.setVisible(bool(text))
        self.fit_message()

    def fit_message(self):
        self.setMinimumHeight(max(0, self.heightForWidth(max(1, self.width()))) if self.text() else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_message()


class StableStack(QStackedWidget):
    """Use all pages' wrapped heights, not just the active page's height."""
    def heightForWidth(self, width):
        return max(self.widget(i).heightForWidth(width) if self.widget(i).hasHeightForWidth()
                   else self.widget(i).sizeHint().height() for i in range(self.count()))

    def sizeHint(self):
        hint = super().sizeHint()
        if self.count() and self.width() > 0:
            hint.setHeight(max(hint.height(), self.heightForWidth(self.width())))
        return hint


class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName('sidebar')
        self.setFixedWidth(380)
        self.focus_widgets = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.tabs = named(QTabBar(), 'mode_tabs')
        self.tabs.addTab('두 채널 격자')
        self.tabs.addTab('시작·끝 보간')
        self.tabs.setExpanding(True)
        self.tabs.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        outer.addWidget(self.tabs)
        self.focus_widgets.append(self.tabs)

        self.scroll = named(QScrollArea(), 'settings_scroll')
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        body = named(QWidget(), 'settings_body')
        content = QVBoxLayout(body)
        content.setContentsMargins(10, 6, 10, 6)
        content.setSpacing(6)
        self.grid_panel, grid = self.group('격자 설정', 'grid_panel')
        self.cmyk(grid, '기준 CMYK (%)', 'grid_cmyk', (40, 70, 20, 0))
        channel = named(QComboBox(), 'grid_channels')
        channel.addItems(['CM', 'CY', 'CK', 'MY', 'MK', 'YK'])
        self.row(grid, [('변형 채널', 'grid_channels', channel), ('간격 (%p)', 'grid_step', '1')])
        self.row(grid, [('가로 칸 수', 'grid_cols', '7'), ('세로 칸 수', 'grid_rows', '7')])
        grid.addStretch()
        self.ramp_panel, ramp = self.group('보간 설정', 'ramp_panel')
        self.cmyk(ramp, '시작 CMYK (%)', 'ramp_start', (40, 70, 20, 0))
        self.cmyk(ramp, '끝 CMYK (%)', 'ramp_end', (30, 75, 30, 5))
        self.row(ramp, [('패치 수 (시작·끝 포함)', 'ramp_count', '11'), ('가로 칸 수', 'ramp_cols', 'auto')])
        ramp.addWidget(label('가로 칸 수 auto: 자동 크기면 7칸, 패치 크기를 정하면 한 줄 최대 칸 수', 'ramp_auto_hint'))
        ramp.addStretch()
        self.mode_panels = named(StableStack(), 'mode_panels')
        self.mode_panels.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        for panel in (self.grid_panel, self.ramp_panel):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            page_layout.addWidget(panel)
            self.mode_panels.addWidget(page)
        content.addWidget(self.mode_panels)

        layout_box = named(QWidget(), 'layout_section')
        layout_outer = QVBoxLayout(layout_box)
        layout_outer.setContentsMargins(0, 0, 0, 0)
        heading = QHBoxLayout()
        self.layout_toggle = named(QToolButton(), 'layout_toggle')
        self.layout_toggle.setText('레이아웃')
        self.layout_toggle.setCheckable(True)
        self.layout_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.layout_toggle.setArrowType(Qt.ArrowType.RightArrow)
        self.focus_widgets.append(self.layout_toggle)
        heading.addWidget(self.layout_toggle)
        heading.addWidget(label('–', 'layout_summary'), 1)
        layout_outer.addLayout(heading)
        self.layout_fields = named(QWidget(), 'layout_fields')
        fields = QVBoxLayout(self.layout_fields)
        fields.setContentsMargins(0, 0, 0, 0)
        self.row(fields, [('용지 가로 mm', 'layout_width', '305'), ('용지 세로 mm', 'layout_height', '505')])
        self.row(fields, [('여백 mm (사방)', 'layout_margin', '20'), ('패치 간격 mm', 'layout_gap', '3')])
        self.row(fields, [('패치 크기 mm', 'layout_patch_size', 'auto')])
        layout_outer.addWidget(self.layout_fields)
        self.layout_fields.hide()
        self.layout_toggle.toggled.connect(self.toggle_layout)
        content.addWidget(layout_box)

        picked, picked_layout = self.group('선택한 패치', 'selected_panel')
        selected_row = QHBoxLayout()
        chip = label('', 'selected_swatch')
        chip.setFixedSize(26, 26)
        chip.setStyleSheet('background: #e5e7eb; border: 1px solid #c5cbd2;')
        selected_row.addWidget(chip)
        text = QHBoxLayout()
        text.addWidget(label('–', 'selected_id'))
        text.addWidget(label('–', 'selected_cmyk'))
        selected_row.addLayout(text, 1)
        picked_layout.addLayout(selected_row)
        picked_layout.addWidget(label('미리보기에서 패치를 선택하세요.', 'selection_hint'))
        self.use_base = button('이 값을 기준으로', 'use_as_base_button')

        self.ramp_actions = QWidget()
        actions = QHBoxLayout(self.ramp_actions)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addWidget(button('시작으로', 'use_as_start_button'))
        actions.addWidget(button('끝으로', 'use_as_end_button'))
        self.selection_actions = named(QStackedWidget(), 'selection_actions')
        self.selection_actions.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.selection_actions.addWidget(self.use_base)
        self.selection_actions.addWidget(self.ramp_actions)
        picked_layout.addWidget(self.selection_actions)
        content.addWidget(picked)
        warnings, warnings_layout = self.group('알림', 'warnings_panel')
        warnings_layout.addWidget(label('없음', 'warning_list'))
        content.addWidget(warnings)
        content.addStretch()
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)

        footer = named(QWidget(), 'output_footer')
        foot = QVBoxLayout(footer)
        foot.setContentsMargins(10, 6, 10, 6)
        foot.setSpacing(3)
        stats = QHBoxLayout()
        for title, name in [('패치 수', 'summary_patch_count'), ('PDF 수', 'summary_pdf_count'), ('패치 크기 mm', 'summary_patch_size')]:
            box = QVBoxLayout()
            box.addWidget(label('–', name))
            box.addWidget(QLabel(title))
            stats.addLayout(box, 1)
        foot.addLayout(stats)
        folder_row = QHBoxLayout()
        folder = named(QLineEdit(), 'output_folder')
        folder.setPlaceholderText('저장 폴더')
        folder.setAccessibleName('저장 폴더')
        self.focus_widgets.append(folder)
        folder_row.addWidget(folder, 1)
        folder_row.addWidget(button('찾기', 'browse_button'))
        foot.addLayout(folder_row)
        foot.addWidget(label('–', 'filename_preview'))
        foot.addWidget(button('PDF 만들기', 'make_pdf_button'))
        status = label('', 'output_status')
        status.setMinimumHeight(18)
        foot.addWidget(status)
        outer.addWidget(footer)
        self.tabs.currentChanged.connect(self.set_mode)
        self.set_mode(0)

    @staticmethod
    def group(title, name):
        group = named(QGroupBox(title), name)
        group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        box = QVBoxLayout(group)
        box.setContentsMargins(8, 8, 8, 6)
        box.setSpacing(3)
        return group, box

    def row(self, parent, specs):
        row = QHBoxLayout()
        row.setSpacing(6)
        for title, name, value in specs:
            field = QVBoxLayout()
            field.setSpacing(2)
            field.setAlignment(Qt.AlignmentFlag.AlignTop)
            widget = named(QLineEdit(value), name) if isinstance(value, str) else value
            widget.setMinimumWidth(0)
            widget.setFixedHeight(26)
            widget.setAccessibleName(title)
            caption = QLabel(title)
            caption.setBuddy(widget)
            field.addWidget(caption)
            field.addWidget(widget)
            error = ErrorLabel(name + '_error')
            field.addWidget(error)
            row.addLayout(field, 1)
            self.focus_widgets.append(widget)
        parent.addLayout(row)

    def cmyk(self, parent, title, prefix, values):
        parent.addWidget(QLabel(title))
        self.row(parent, [(c, f'{prefix}_{c.lower()}', str(v)) for c, v in zip('CMYK', values)])

    def set_mode(self, index):
        self.mode_panels.setCurrentIndex(index)
        self.selection_actions.setCurrentIndex(index)

    def toggle_layout(self, expanded):
        self.layout_fields.setVisible(expanded)
        self.layout_toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
