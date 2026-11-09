"""Background export and output controls. File policy stays in the engine."""
from color_patch_maker.engine.messages import t
import copy
import errno
from pathlib import Path
from PySide6.QtCore import QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog
from color_patch_maker.engine.pdf import export, preview_paths


def failure_message(error):
    if isinstance(error, PermissionError):
        return t('output.permission')
    if isinstance(error, OSError) and error.errno == errno.ENOSPC:
        return t('output.disk_full')
    if isinstance(error, FileNotFoundError):
        return t('output.folder_missing')
    if isinstance(error, ValueError):
        return t('output.verify_failure', error=error)
    return t('output.failure', error=error)


class ExportThread(QThread):
    def __init__(self, document, folder, parent):
        super().__init__(parent)
        self.document = copy.deepcopy(document)
        self.folder = folder
        self.files = []
        self.error = None

    def run(self):
        try:
            self.files = export(self.document, self.folder)
        except Exception as exc:
            self.error = exc


class OutputController:
    def __init__(self, controller):
        self.controller = controller
        self.window = controller.window
        self.widget = controller.widget
        self.busy = False
        self.thread = None
        self.completed_folder = None
        self.widget('browse_button').setEnabled(True)
        self.widget('browse_button').clicked.connect(self.browse)
        self.widget('output_folder').textChanged.connect(self.folder_changed)
        self.widget('make_pdf_button').clicked.connect(self.start)
        self.widget('open_folder_button').clicked.connect(self.open_folder)
        self.update()

    def status(self, text):
        self.widget('output_status').setText(text)
        self.widget('notice_stack').setCurrentIndex(1 if text else 0)

    def clear_status(self):
        if not self.busy:
            self.status('')
            self.widget('open_folder_button').setEnabled(False)
            self.completed_folder = None

    def folder_changed(self):
        self.clear_status()
        self.update()

    def update(self):
        folder = self.widget('output_folder').text()
        error = ''
        if not folder:
            error = t('output.folder_required')
        elif not Path(folder).is_dir():
            error = t('output.folder_invalid')
        self.widget('output_folder_error').setText(error)
        document = self.controller.document
        if document and not error:
            try:
                names = [Path(p).name for p in preview_paths(document,folder) if p.endswith('.pdf')]
                self.widget('filename_preview').setText(names[0] if len(names)==1 else t('output.filename_range', first=names[0], last=names[-1]))
            except OSError as exc:
                error = failure_message(exc)
                self.widget('output_folder_error').setText(error)
        self.widget('make_pdf_button').setEnabled(bool(document and not error and not self.busy))

    def browse(self):
        folder = QFileDialog.getExistingDirectory(self.window,t('output.choose_folder'),self.widget('output_folder').text())
        if folder:
            self.widget('output_folder').setText(folder)

    def start(self):
        if self.busy:
            return
        self.update()
        if not self.widget('make_pdf_button').isEnabled():
            return
        self.clear_status()
        self.busy = True
        self.thread = ExportThread(self.controller.document, self.widget('output_folder').text(), self.window)
        self.lock(True)
        self.status(t('output.busy'))
        self.thread.finished.connect(self.finished)
        self.thread.start()

    def lock(self, locked):
        for name in ['mode_tabs','settings_scroll','output_folder','browse_button']:
            self.widget(name).setEnabled(not locked)
        self.window.preview.setEnabled(not locked)
        self.widget('make_pdf_button').setEnabled(False)

    def finished(self):
        thread = self.thread
        self.busy = False
        self.lock(False)
        if thread.error:
            self.status(failure_message(thread.error))
        else:
            self.completed_folder = thread.folder
            names = [Path(p).name for p in thread.files if p.endswith('.pdf')]
            self.status(t('output.success', names='\n'.join(names)))
            self.widget('open_folder_button').setEnabled(True)

        self.update()
        self.thread = None
        thread.deleteLater()

    def open_folder(self):
        if self.completed_folder:
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(self.completed_folder).resolve()))):
                self.status(t('output.open_failed'))
