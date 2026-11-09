"""Settings widgets with stable names for future controller connections."""
from .settings import DEFAULTS
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QToolButton, QTabBar, QScrollArea, QGroupBox,
    QSizePolicy, QStackedWidget, QPlainTextEdit,
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


class StatusText(QPlainTextEdit):
    """Bounded result area so long output lists cannot enlarge the main window."""
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFixedHeight(40)
        self.setObjectName('output_status')

    def setText(self, text):
        self.setPlainText(text)

    def text(self):
        return self.toPlainText()


class Sidebar(QWidget):
    def __init__(self, translate):
        super().__init__()
        self.t = translate
        self.setObjectName('sidebar')
        self.setFixedWidth(380)
        self.focus_widgets = []
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.tabs = named(QTabBar(), 'mode_tabs')
        self.tabs.addTab(self.t('mode.grid'))
        self.tabs.addTab(self.t('mode.ramp'))
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
        content.setSpacing(4)
        self.grid_panel, grid = self.group(self.t('grid.title'), 'grid_panel')
        self.cmyk(grid, self.t('grid.base'), 'grid_cmyk', (40, 70, 20, 0))
        channel = named(QComboBox(), 'grid_channels')
        channel.addItems(['CM', 'CY', 'CK', 'MY', 'MK', 'YK'])
        self.row(grid, [(self.t('grid.channels'), 'grid_channels', channel), (self.t('grid.step'), 'grid_step', '1')])
        self.row(grid, [(self.t('layout.columns_label'), 'grid_cols', '7'), (self.t('grid.rows'), 'grid_rows', '7')])
        grid.addStretch()
        self.ramp_panel, ramp = self.group(self.t('ramp.title'), 'ramp_panel')
        self.cmyk(ramp, self.t('ramp.start'), 'ramp_start', (40, 70, 20, 0))
        self.cmyk(ramp, self.t('ramp.end'), 'ramp_end', (30, 75, 30, 5))
        self.row(ramp, [(self.t('ramp.count'), 'ramp_count', '11'), (self.t('layout.columns_label'), 'ramp_cols', 'auto')])
        ramp.addWidget(label(self.t('ramp.auto_hint'), 'ramp_auto_hint'))
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
        self.layout_toggle.setText(self.t('layout.title'))
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
        templates = named(QComboBox(), 'layout_template')
        fields.addWidget(templates)
        self.focus_widgets.append(templates)
        actions = QHBoxLayout()
        for title, name in [(self.t('template.save'), 'save_template_button'), (self.t('template.delete'), 'delete_template_button')]:
            action = button(title, name)
            action.setEnabled(True)
            actions.addWidget(action)
            self.focus_widgets.append(action)
        fields.addLayout(actions)
        reset = button(self.t('layout.reset'), 'reset_layout_button')
        reset.setEnabled(True)
        fields.addWidget(reset)
        self.focus_widgets.append(reset)
        self.row(fields, [(self.t('layout.width'), 'layout_width', DEFAULTS['layout_width']), (self.t('layout.height'), 'layout_height', DEFAULTS['layout_height'])])
        self.row(fields, [(self.t('layout.margin'), 'layout_margin', DEFAULTS['layout_margin']), (self.t('layout.gap'), 'layout_gap', DEFAULTS['layout_gap'])])
        self.row(fields, [(self.t('layout.patch_size'), 'layout_patch_size', DEFAULTS['layout_patch_size'])])
        layout_outer.addWidget(self.layout_fields)
        self.layout_fields.hide()
        self.layout_toggle.toggled.connect(self.toggle_layout)
        content.addWidget(layout_box)

        picked, picked_layout = self.group(self.t('selection.title'), 'selected_panel')
        selected_row = QHBoxLayout()
        chip = label('', 'selected_swatch')
        chip.setFixedSize(26, 26)
        chip.setStyleSheet('background: #e5e7eb; border: 1px solid #c5cbd2;')
        selected_row.addWidget(chip)
        text = QHBoxLayout()
        text.addWidget(label('–', 'selected_id'))
        text.addWidget(label('–', 'selected_cmyk'))
        text.setSpacing(6)
        text.addStretch()
        selected_row.addLayout(text, 1)
        self.selection_details = named(QStackedWidget(), 'selection_details')
        self.selection_details.setFixedHeight(26)
        self.selection_details.addWidget(label(self.t('selection.empty'), 'selection_hint'))
        details = QWidget()
        details.setLayout(selected_row)
        selected_row.setContentsMargins(0, 0, 0, 0)
        self.selection_details.addWidget(details)
        picked_layout.addWidget(self.selection_details)
        self.use_base = button(self.t('selection.base'), 'use_as_base_button')

        self.ramp_actions = QWidget()
        actions = QHBoxLayout(self.ramp_actions)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addWidget(button(self.t('selection.start'), 'use_as_start_button'))
        actions.addWidget(button(self.t('selection.end'), 'use_as_end_button'))
        self.selection_actions = named(QStackedWidget(), 'selection_actions')
        self.selection_actions.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.selection_actions.addWidget(self.use_base)
        self.selection_actions.addWidget(self.ramp_actions)
        picked_layout.addWidget(self.selection_actions)
        content.addWidget(picked)
        warnings, warnings_layout = self.group(self.t('notice.title'), 'warnings_panel')
        notice_stack = named(QStackedWidget(), 'notice_stack')
        notice_stack.setFixedHeight(40)
        notice_stack.addWidget(label(self.t('notice.none'), 'warning_list'))
        notice_stack.addWidget(StatusText())
        warnings_layout.addWidget(notice_stack)
        content.addWidget(warnings)
        content.addStretch()
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)

        footer = named(QWidget(), 'output_footer')
        foot = QVBoxLayout(footer)
        foot.setContentsMargins(10, 6, 10, 6)
        foot.setSpacing(3)
        stats = QHBoxLayout()
        for title, name in [(self.t('summary.count'), 'summary_patch_count'), (self.t('summary.pdf_count'), 'summary_pdf_count'), (self.t('layout.patch_size'), 'summary_patch_size')]:
            box = QVBoxLayout()
            box.addWidget(label('–', name))
            box.addWidget(QLabel(title))
            stats.addLayout(box, 1)
        foot.addLayout(stats)
        folder_row = QHBoxLayout()
        folder = named(QLineEdit(), 'output_folder')
        folder.setPlaceholderText(self.t('output.folder'))
        folder.setAccessibleName(self.t('output.folder'))
        self.focus_widgets.append(folder)
        folder_row.addWidget(folder, 1)
        folder_row.addWidget(button(self.t('output.browse'), 'browse_button'))
        foot.addLayout(folder_row)
        foot.addWidget(ErrorLabel('output_folder_error'))
        foot.addWidget(label('–', 'filename_preview'))
        output_actions = QHBoxLayout()
        output_actions.addWidget(button(self.t('output.make'), 'make_pdf_button'), 1)
        output_actions.addWidget(button(self.t('output.open'), 'open_folder_button'), 1)
        foot.addLayout(output_actions)
        outer.addWidget(footer)
        self.tabs.currentChanged.connect(self.set_mode)
        self.set_mode(0)

    @staticmethod
    def group(title, name):
        group = named(QGroupBox(title), name)
        group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        box = QVBoxLayout(group)
        box.setContentsMargins(8, 6, 8, 4)
        box.setSpacing(2)
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
            widget.setFixedHeight(24)
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
