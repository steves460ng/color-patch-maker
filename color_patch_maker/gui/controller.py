"""Translate widget values to engine arguments and display engine results."""
from .language import error_text
from color_patch_maker.engine.messages import Message
from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QWidget, QLineEdit
from color_patch_maker.engine import input_errors, layout, output_names
from .preview import screen_color
from .output import OutputController
from .templates import TemplateController


class Controller:
    def __init__(self, window):
        self.window = window
        self.t = self.window.t
        self.language = self.window.language
        self.document = None
        self.page_index = 0
        self.selected = None
        for field in window.sidebar.findChildren(QLineEdit):
            if field.objectName() != 'output_folder':
                field.textChanged.connect(self.refresh)
        self.widget('grid_channels').currentTextChanged.connect(self.refresh)
        window.sidebar.tabs.currentChanged.connect(self.refresh)
        self.widget('previous_page_button').clicked.connect(lambda: self.change_page(-1))
        self.widget('next_page_button').clicked.connect(lambda: self.change_page(1))
        window.preview.paper.patch_clicked.connect(self.select)
        for name, prefix in [('use_as_base_button','grid_cmyk'),('use_as_start_button','ramp_start'),('use_as_end_button','ramp_end')]:
            self.widget(name).clicked.connect(lambda checked=False, p=prefix: self.apply_selection(p))
        self.templates = TemplateController(self)
        self.refresh()
        self.output = OutputController(self)

    def widget(self, name):
        return self.window.findChild(QWidget, name)

    def inputs(self):
        mode = 'grid' if self.window.sidebar.tabs.currentIndex() == 0 else 'ramp'
        mapping = {'paper.0':'layout_width','paper.1':'layout_height','margin':'layout_margin',
                   'gap':'layout_gap','patch_size':'layout_patch_size'}
        for argument, prefix in ([('cmyk','grid_cmyk')] if mode == 'grid' else [('start','ramp_start'),('end','ramp_end')]):
            mapping.update({f'{argument}.{i}':f'{prefix}_{c}' for i,c in enumerate('cmyk')})
        mapping.update({k:f'{mode}_{k}' for k in (('step','cols','rows') if mode == 'grid' else ('count','cols'))})
        args = {}
        for key, name in mapping.items():
            value = self.widget(name).text()
            if '.' in key:
                group, index = key.split('.')
                args.setdefault(group, []).append(value)
            else:
                args[key] = value
        if args['patch_size'] == 'auto':
            args['patch_size'] = None
        if mode == 'grid':
            args['channels'] = self.widget('grid_channels').currentText()
        return mode, args, mapping

    def refresh(self, *_):
        if hasattr(self, 'output'):
            if self.output.busy:
                return
            self.output.clear_status()
        self.document = None
        self.page_index = 0
        self.select(None)
        for field in self.window.sidebar.findChildren(QLineEdit):
            error = self.widget(field.objectName()+'_error')
            if error is not None and field.objectName() != 'output_folder':
                error.setText('')
                field.setStyleSheet('')
        mode, args, mapping = self.inputs()
        errors = input_errors(mode, **args)
        for key, message in errors.items():
            field = self.widget(mapping[key])
            field.setStyleSheet('border: 1px solid #b3261e;')
            compact = self.t('input.color_compact') if key.startswith(('cmyk.', 'start.', 'end.')) else message.render(self.language)
            self.widget(mapping[key]+'_error').setText(compact)
            self.widget(mapping[key]+'_error').setToolTip(message.render(self.language))
        problem = self.t('preview.invalid') if errors else None
        if not errors:
            try:
                self.document = layout(mode, **args)
            except ValueError as exc:
                problem = error_text(exc, self.language)
        if self.document is None:
            for name in ['summary_patch_count','summary_pdf_count','summary_patch_size','filename_preview']:
                self.widget(name).setText('–')
            self.widget('warning_list').setText(problem)
        else:
            d = self.document
            patches = [p for page in d['pages'] for p in page['patches']]
            self.widget('summary_patch_count').setText(str(len(patches)))
            self.widget('summary_pdf_count').setText(str(len(d['pages'])))
            self.widget('summary_patch_size').setText(f"{patches[0]['rect_mm'][2]:.1f}")
            settings = d['settings']
            paper = '×'.join(f'{v:g}' for v in d['paper_mm'])
            size = self.t('layout.auto') if settings['patch_size'] is None else self.t('layout.size_mm', size=settings['patch_size'])
            self.widget('layout_summary').setText(self.t('layout.summary', paper=paper, margin=settings['margin'], size=size))
            self.widget('paper_info').setText(self.t('layout.paper_info', paper=paper))
            names = output_names(d)
            self.widget('filename_preview').setText(names[0] if len(names)==1 else self.t('output.filename_range', first=names[0], last=names[-1]))
            notices = list(d['warnings'])
            if len(d['pages']) > 1:
                notices.append(Message('warning.split', count=len(d['pages'])))
            self.widget('warning_list').setText('\n'.join(notice.render(self.language) for notice in notices) or self.t('notice.none'))
        layout_keys = ('paper.', 'margin', 'gap', 'patch_size')
        if not any(key.startswith(layout_keys) for key in errors):
            paper = '×'.join(f'{float(v):g}' for v in args['paper'])
            size = self.t('layout.auto') if args['patch_size'] is None else self.t('layout.size_mm', size=float(args['patch_size']))
            self.widget('layout_summary').setText(self.t('layout.summary', paper=paper, margin=float(args['margin']), size=size))
            self.widget('paper_info').setText(self.t('layout.paper_info', paper=paper))
        else:
            self.widget('layout_summary').setText('–')
            self.widget('paper_info').setText('–')
        self.templates.update()
        if self.window.restore_notice:
            self.widget('warning_list').setText(self.widget('warning_list').text()+'\n'+self.window.restore_notice)
            self.window.restore_notice = ''
        self.show_page()
        if hasattr(self, 'output'):
            self.output.update()

    def show_page(self):
        count = len(self.document['pages']) if self.document else 0
        self.window.preview.paper.set_document(self.document, self.page_index)
        self.widget('page_indicator').setText(self.t('preview.page', current=self.page_index+1, total=count) if count else self.t('preview.page_empty'))
        self.widget('previous_page_button').setEnabled(bool(count and self.page_index > 0))
        self.widget('next_page_button').setEnabled(bool(count and self.page_index < count-1))

    def change_page(self, delta):
        if self.document and 0 <= self.page_index+delta < len(self.document['pages']):
            self.page_index += delta
            self.select(None)
            self.show_page()

    def select(self, patch):
        self.selected = patch
        self.widget('selection_details').setCurrentIndex(1 if patch else 0)
        paper = self.window.preview.paper
        paper.selected_id = patch['id'] if patch else None
        paper.update()
        self.widget('selected_id').setText(patch['id'] if patch else '–')
        self.widget('selected_cmyk').setText(' '.join(f'{c}{v}' for c,v in zip('CMYK',patch['cmyk'])) if patch else '–')
        color = screen_color(patch['cmyk']).name() if patch else '#e5e7eb'
        self.widget('selected_swatch').setStyleSheet(f'background: {color}; border: 1px solid #c5cbd2;')
        self.widget('selection_hint').setText(self.t('selection.ready') if patch else self.t('selection.empty'))
        for name in ['use_as_base_button','use_as_start_button','use_as_end_button']:
            self.widget(name).setEnabled(patch is not None)

    def apply_selection(self, prefix):
        if self.selected is None:
            return
        fields = [self.widget(f'{prefix}_{c}') for c in 'cmyk']
        blockers = [QSignalBlocker(field) for field in fields]
        for field,value in zip(fields,self.selected['cmyk']):
            field.setText(str(value))
        del blockers
        self.refresh()
