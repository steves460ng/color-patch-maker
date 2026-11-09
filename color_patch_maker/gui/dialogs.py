"""Application-owned dialog buttons follow the window language."""
from PySide6.QtWidgets import QInputDialog, QMessageBox


class InputDialog:
    @staticmethod
    def getText(parent, title, prompt):
        dialog = QInputDialog(parent)
        dialog.setWindowTitle(title)
        dialog.setLabelText(prompt)
        dialog.setOkButtonText(parent.t('dialog.ok'))
        dialog.setCancelButtonText(parent.t('dialog.cancel'))
        accepted = dialog.exec() == QInputDialog.DialogCode.Accepted
        return dialog.textValue(), accepted


class MessageBox:
    StandardButton = QMessageBox.StandardButton

    @staticmethod
    def question(parent, title, prompt, buttons, default):
        dialog = QMessageBox(QMessageBox.Icon.Question, title, prompt, buttons, parent)
        dialog.setDefaultButton(default)
        dialog.button(QMessageBox.StandardButton.Yes).setText(parent.t('dialog.yes'))
        dialog.button(QMessageBox.StandardButton.No).setText(parent.t('dialog.no'))
        return dialog.exec()

    @staticmethod
    def warning(parent, title, prompt):
        dialog = QMessageBox(QMessageBox.Icon.Warning, title, prompt, QMessageBox.StandardButton.Ok, parent)
        dialog.button(QMessageBox.StandardButton.Ok).setText(parent.t('dialog.ok'))
        return dialog.exec()
