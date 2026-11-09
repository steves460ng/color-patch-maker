"""Template selection and dialogs; engine owns values and validation."""
import json
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QInputDialog, QMessageBox
from color_patch_maker.engine import template_names, template_values, validate_template
from .settings import DEFAULTS, fields_from_values, values_from_fields


class TemplateController:
    def __init__(self, controller):
        self.controller = controller
        self.window = controller.window
        self.users = {}
        self.combo = controller.widget('layout_template')
        skipped = []
        try:
            saved = json.loads(str(self.window.settings.value('layout_templates', '{}')))
            if not isinstance(saved, dict):
                raise ValueError('템플릿 목록')
        except (ValueError, TypeError):
            saved = {}
            skipped.append('목록')
        for name, values in saved.items():
            try:
                self.check_name(name)
                self.users[name] = validate_template(values)
            except (ValueError, TypeError, OverflowError):
                skipped.append(name)
        if skipped:
            notice = '잘못된 저장 템플릿을 건너뛰었습니다: ' + ', '.join(skipped)
            self.window.restore_notice = '\n'.join(filter(None, [self.window.restore_notice, notice]))
        self.repopulate()
        self.combo.activated.connect(self.choose)
        controller.widget('save_template_button').clicked.connect(self.save)
        controller.widget('delete_template_button').clicked.connect(self.delete)
        controller.widget('reset_layout_button').clicked.connect(self.reset)

    @staticmethod
    def check_name(name):
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError('템플릿 이름을 입력하세요. 앞뒤 공백은 사용할 수 없습니다.')
        if name in (*template_names(), 'default', 'card', '사용자 설정'):
            raise ValueError('기본 제공 이름·별칭과 사용자 설정은 이름으로 사용할 수 없습니다.')

    def repopulate(self):
        with QSignalBlocker(self.combo):
            self.combo.clear()
            self.combo.addItem('사용자 설정')
            self.combo.addItems([*template_names(), *self.users])

    def current_values(self):
        fields = {key: self.controller.widget(key).text() for key in DEFAULTS}
        return validate_template(values_from_fields(fields))

    def values(self, name):
        return self.users[name] if name in self.users else template_values(name)

    def update(self):
        try:
            values = self.current_values()
        except (ValueError, TypeError, OverflowError):
            values = None
        # Retain the selected name when multiple templates share the same values.
        names = [self.combo.currentText(), *template_names(), *self.users]
        match = next((name for name in names if name != '사용자 설정' and self.values(name) == values), '사용자 설정')
        with QSignalBlocker(self.combo):
            self.combo.setCurrentText(match)
        self.controller.widget('delete_template_button').setEnabled(match in self.users)
        summary = self.controller.widget('layout_summary')
        summary.setText(f'{match} · {summary.text()}')

    def choose(self, index):
        name = self.combo.itemText(index)
        if name != '사용자 설정':
            self.apply(self.values(name))
        else:
            self.controller.refresh()

    def apply(self, values):
        fields = fields_from_values(values)
        blockers = [QSignalBlocker(self.controller.widget(key)) for key in fields]
        for key, value in fields.items():
            self.controller.widget(key).setText(value)
        del blockers
        self.controller.refresh()

    def reset(self):
        self.combo.setCurrentText('기본')
        self.apply(template_values('default'))

    def persist(self):
        self.window.settings.setValue('layout_templates', json.dumps(self.users, ensure_ascii=False))
        self.window.settings.sync()

    def save(self):
        try:
            values = self.current_values()
        except (ValueError, TypeError, OverflowError) as exc:
            QMessageBox.warning(self.window, '템플릿 저장', str(exc))
            return
        name, accepted = QInputDialog.getText(self.window, '템플릿 저장', '템플릿 이름')
        if not accepted:
            return
        name = name.strip()
        try:
            self.check_name(name)
        except ValueError as exc:
            QMessageBox.warning(self.window, '템플릿 저장', str(exc))
            return
        if name in self.users and QMessageBox.question(self.window, '템플릿 덮어쓰기',
                f'“{name}” 템플릿을 덮어쓸까요?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.users[name] = values
        self.persist()
        self.repopulate()
        self.combo.setCurrentText(name)
        self.controller.refresh()

    def delete(self):
        name = self.combo.currentText()
        if name not in self.users:
            return
        if QMessageBox.question(self.window, '템플릿 삭제', f'“{name}” 템플릿을 삭제할까요?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        del self.users[name]
        self.persist()
        self.repopulate()
        self.controller.refresh()
