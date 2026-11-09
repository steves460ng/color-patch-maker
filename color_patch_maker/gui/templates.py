"""Template selection and dialogs; engine owns values and validation."""
from color_patch_maker.engine.messages import t
import json
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QInputDialog, QMessageBox
from color_patch_maker.engine import template_names, template_values, validate_template, template_label, reserved_template_names
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
                raise ValueError(t('template.list_error'))
        except (ValueError, TypeError):
            saved = {}
            skipped.append(t('template.list'))
        for name, values in saved.items():
            try:
                self.check_name(name, restoring=True)
                self.users[name] = validate_template(values)
            except (ValueError, TypeError, OverflowError):
                skipped.append(name)
        if skipped:
            notice = t('template.skipped', names=', '.join(skipped))
            self.window.restore_notice = '\n'.join(filter(None, [self.window.restore_notice, notice]))
        self.repopulate()
        self.combo.activated.connect(self.choose)
        controller.widget('save_template_button').clicked.connect(self.save)
        controller.widget('delete_template_button').clicked.connect(self.delete)
        controller.widget('reset_layout_button').clicked.connect(self.reset)

    @staticmethod
    def check_name(name, restoring=False):
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ValueError(t('template.name_invalid'))
        if restoring and name in ('Custom', 'Default', 'Card'):
            return  # These names were valid in existing settings.
        if name in reserved_template_names():
            raise ValueError(t('template.name_reserved'))

    def repopulate(self):
        with QSignalBlocker(self.combo):
            self.combo.clear()
            self.combo.addItem(t('template.custom'), None)
            for identifier in template_names():
                self.combo.addItem(template_label(identifier), identifier)
            for name in self.users:
                self.combo.addItem(name, 'user:' + name)

    def current_values(self):
        fields = {key: self.controller.widget(key).text() for key in DEFAULTS}
        return validate_template(values_from_fields(fields))

    def values(self, identity):
        return self.users[identity[5:]] if identity.startswith('user:') else template_values(identity)

    def update(self):
        try:
            values = self.current_values()
        except (ValueError, TypeError, OverflowError):
            values = None
        identities = [self.combo.currentData(),
                      *template_names(),
                      *('user:' + name for name in self.users)]
        match = next((identity for identity in identities if identity is not None and self.values(identity) == values), None)
        with QSignalBlocker(self.combo):
            self.combo.setCurrentIndex(self.combo.findData(match))
        self.controller.widget('delete_template_button').setEnabled(match is not None and match.startswith('user:'))
        summary = self.controller.widget('layout_summary')
        summary.setText(t('layout.named_summary', name=self.combo.currentText(), summary=summary.text()))

    def choose(self, index):
        identity = self.combo.itemData(index)
        if identity is not None:
            self.apply(self.values(identity))
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
        self.combo.setCurrentIndex(self.combo.findData('default'))
        self.apply(template_values('default'))

    def persist(self):
        self.window.settings.setValue('layout_templates', json.dumps(self.users, ensure_ascii=False))
        self.window.settings.sync()

    def save(self):
        try:
            values = self.current_values()
        except (ValueError, TypeError, OverflowError) as exc:
            QMessageBox.warning(self.window, t('template.save'), str(exc))
            return
        name, accepted = QInputDialog.getText(self.window, t('template.save'), t('template.name'))
        if not accepted:
            return
        name = name.strip()
        try:
            self.check_name(name)
        except ValueError as exc:
            QMessageBox.warning(self.window, t('template.save'), str(exc))
            return
        if name in self.users and QMessageBox.question(self.window, t('template.overwrite'),
                t('template.overwrite_question', name=name), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        self.users[name] = values
        self.persist()
        self.repopulate()
        self.combo.setCurrentIndex(self.combo.findData('user:' + name))
        self.controller.refresh()

    def delete(self):
        identity = self.combo.currentData()
        if identity is None or not identity.startswith('user:'):
            return
        name = identity[5:]
        if QMessageBox.question(self.window, t('template.delete'), t('template.delete_question', name=name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        del self.users[name]
        self.persist()
        self.repopulate()
        self.controller.refresh()
