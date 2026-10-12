# SPDX-License-Identifier: GPL-3.0-or-later
"""Styles editor with Select, Edit and Mix and five editing categories."""
from __future__ import annotations

import base64
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QTextEdit, QTabWidget, QStackedWidget, QToolButton,
    QButtonGroup, QCheckBox, QComboBox, QSpinBox, QDoubleSpinBox, QSlider,
    QScrollArea, QFrame, QPushButton, QListWidget, QListWidgetItem,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMenu,
    QDialog, QDialogButtonBox, QFormLayout, QRadioButton)
from core.i18n import tr
from core.paths import app_root
from views.color_dialog import get_color
from views import prompts as _prompts
from PySide6.QtWidgets import QMessageBox
from core.style import Style, BUILTIN_STYLES, user_styles, style_by_name, save_user_style, builtin_names

def _dialog_parent(widget):
    from views.tray import _dialog_parent as parent_for_dialog
    parent = parent_for_dialog(widget)
    return getattr(parent, "dialog_parent", parent)


CATEGORIES = ('Edge', 'Face', 'Background', 'Watermark', 'Modeling')
CATEGORY_FIELDS = {
    'Edge': ('edges', 'back_edges', 'profiles', 'profile_width', 'depth_cue',
             'depth_cue_width', 'extensions', 'extension_length', 'endpoints',
             'endpoint_size', 'dashes', 'edge_color_mode', 'edge_color'),
    'Face': ('front_color', 'back_color', 'face_mode', 'material_transparency',
             'transparency_quality', 'xray_opacity', 'ambient_occlusion',
             'ao_default_color', 'ao_color', 'ao_distance', 'ao_intensity', 'ao_multiplier'),
    'Background': ('background', 'sky', 'sky_color', 'horizon_color', 'ground',
                   'ground_color', 'ground_opacity', 'show_ground_below'),
    'Watermark': ('display_watermarks', 'watermarks'),
    'Modeling': ('selected_color', 'locked_color', 'guide_color', 'inactive_section_color',
                 'active_section_color', 'section_fill_color', 'section_line_color',
                 'section_line_width', 'show_hidden_geometry', 'show_hidden_objects',
                 'color_by_layer', 'show_guides', 'show_axes', 'show_section_planes',
                 'show_section_cuts', 'section_fill', 'override_section_fill', 'photo_image',
                 'foreground_photo', 'foreground_photo_opacity', 'background_photo',
                 'background_photo_opacity'),
}
SCENE_FLAGS = ('show_hidden_geometry', 'show_hidden_objects', 'show_section_planes', 'show_section_cuts')


def style_thumbnail(style, size=80):
    """A native vector preview of the style, without needing a GL context."""
    pm = QPixmap(size, size)
    pm.fill(QColor.fromRgbF(*style.background))
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    if style.sky:
        painter.fillRect(0, 0, size, size//2, QColor.fromRgbF(*style.sky_color))
    if style.ground:
        painter.fillRect(0, size//2, size, size//2, QColor.fromRgbF(*style.ground_color))
    painter.scale(size/80, size/80)
    a,b,c,d,e,f,g = [QPointF(*p) for p in ((15,26),(45,15),(66,29),(36,40),(15,58),(36,70),(66,59))]
    painter.setPen(QPen(QColor.fromRgbF(*style.edge_color), style.profile_width if style.profiles else 1))
    if not style.edges:
        painter.setPen(Qt.NoPen)
    for poly, tone in (((a,b,c,d), 1), ((a,d,f,e), .85), ((d,c,g,f), .7)):
        base = style.front_color if style.face_mode in ('hidden_line','monochrome') else (.78,.72,.59)
        color = QColor.fromRgbF(*(min(1, v*tone) for v in base))
        if style.face_mode == 'wireframe':
            painter.setBrush(Qt.NoBrush)
        else:
            if style.face_mode == 'xray':
                color.setAlphaF(style.xray_opacity)
            painter.setBrush(color)
        painter.drawPolygon(QPolygonF(poly))
    # Cylinder gives the preview a curved surface as well as planar faces.
    base = style.front_color if style.face_mode in ('hidden_line','monochrome') else (.78,.80,.75)
    cylinder = QColor.fromRgbF(*base)
    if style.face_mode == 'xray':cylinder.setAlphaF(style.xray_opacity)
    painter.setBrush(Qt.NoBrush if style.face_mode == 'wireframe' else cylinder)
    painter.drawRect(QRectF(53,43,20,23))
    painter.drawEllipse(QRectF(53,62,20,8))
    painter.drawEllipse(QRectF(53,39,20,8))
    painter.end()
    return pm


from views.color_selector import ColorSelector


class ColorChip(ColorSelector):
    def __init__(self,title,callback):
        super().__init__()
        self.setToolTip(title)
        self.clicked.connect(callback)

    def set_color(self,color):
        super().set_color(QColor.fromRgbF(*color[:3]))


class _MixTarget(QPushButton):
    """Click to sample a style, or drop a style directly on this category."""
    def __init__(self, category, icon, apply, parent=None):
        super().__init__(parent)
        self.category = category
        self.apply_style = apply
        self.setAcceptDrops(True)
        self.setMinimumHeight(36)
        self.setFixedWidth(230)
        self.setAccessibleName(category + ' Settings')
        self.setToolTip('Apply ' + category.lower() + ' settings from the sampled style, or drop a style here')
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 3, 8, 3)
        glyph = QLabel()
        glyph.setPixmap(icon.pixmap(24, 24))
        glyph.setAttribute(Qt.WA_TransparentForMouseEvents)
        row.addWidget(glyph)
        text = QLabel(category + ' Settings')
        text.setAlignment(Qt.AlignCenter)
        text.setAttribute(Qt.WA_TransparentForMouseEvents)
        row.addWidget(text, 1)
        self.clicked.connect(lambda: apply(category))

    def dragEnterEvent(self, event):
        from views.style_browser import STYLE_MIME
        if event.mimeData().hasFormat(STYLE_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        import json
        from views.style_browser import STYLE_MIME
        try:
            data = json.loads(bytes(event.mimeData().data(STYLE_MIME)))
            if not isinstance(data, dict):
                return
            self.apply_style(self.category, Style.from_dict(data))
        except (ValueError, TypeError):
            return
        event.setDropAction(Qt.CopyAction)
        event.accept()


class StylesPanel(QWidget):
    _MODES = (("wireframe", "Wireframe"), ("hidden_line", "Hidden line"),
              ("shaded", "Shaded"), ("textures", "Textures"),
              ("monochrome", "Monochrome"), ("xray", "X-ray"))
    def __init__(self, window):
        QWidget.__init__(self)
        self._window = window
        self._updating = True
        self.controls = {}
        self.swatches = {}
        self._dependent = []
        self.setMinimumWidth(380)
        self.setMaximumWidth(560)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        header = QGridLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(80, 80)
        self.preview.setFrameShape(QFrame.StyledPanel)
        header.addWidget(self.preview, 0, 0, 2, 1)
        self.name = QLineEdit()
        self.name.setPlaceholderText('Style name')
        self.name.editingFinished.connect(self._metadata_changed)
        header.addWidget(self.name, 0, 1)
        self.description = QTextEdit()
        self.description.setPlaceholderText('Style description')
        self.description.setFixedHeight(54)
        self.description.textChanged.connect(self._metadata_changed)
        header.addWidget(self.description, 1, 1)
        buttons = QVBoxLayout()
        for text, tip, callback in (('＋', 'Create style', self._on_save),
                                    ('↻', 'Update the saved style', self._update_saved),
                                    ('▾', 'Style options', self._options)):
            button = QToolButton()
            button.setText(text)
            button.setToolTip(tip)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        header.addLayout(buttons, 0, 2, 2, 1)
        outer.addLayout(header)
        self._separator(outer)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)
        select = QWidget()
        select_layout = QVBoxLayout(select)
        self._combo = QComboBox()
        self._combo.activated.connect(self._on_pick)
        self._combo.hide()  # compatibility lookup; the visible combo browses collections
        from views.style_browser import StyleBrowser
        self.browser = StyleBrowser(window.viewport.scene,style_thumbnail)
        self.browser.styleSelected.connect(self._apply_browser_style)
        self.browser.modelChanged.connect(self._changed)
        self.library = self.browser.items
        select_layout.addWidget(self.browser)
        self._del_btn = QPushButton('Delete style')
        self._del_btn.clicked.connect(self._on_delete)
        select_layout.addWidget(self._del_btn)
        self.tabs.addTab(select, 'Select')
        edit = QWidget()
        edit_layout = QVBoxLayout(edit)
        edit_layout.setContentsMargins(0, 4, 0, 0)
        category_row = QHBoxLayout()
        self.category_buttons = QButtonGroup(self)
        icon_dir = app_root() / 'resources' / 'icons'
        # Shared 24-point canvas preserves the original relative icon sizes.
        category_icons = ('edge', 'face', 'environment', 'watermark', 'working')
        for index, (title, icon) in enumerate(zip(CATEGORIES, category_icons)):
            button = QToolButton()
            button.setCheckable(True)
            button.setIcon(QIcon(str(icon_dir / f'dlg_style_{icon}.png')))
            button.setIconSize(QSize(24, 24))
            button.setToolTip(title + ' Settings')
            button.setAccessibleName(title + ' Settings')
            self.category_buttons.addButton(button, index)
            category_row.addWidget(button)
        category_row.addStretch()
        self.category_title = QLabel('Edge')
        self.category_title.setStyleSheet('font-weight: bold;')
        category_row.addWidget(self.category_title)
        edit_layout.addLayout(category_row)
        self._separator(edit_layout)
        self.pages = QStackedWidget()
        self.pages.setMinimumHeight(460)
        edit_layout.addWidget(self.pages)
        for title in CATEGORIES:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            content = QWidget()
            layout = QVBoxLayout(content)
            layout.setContentsMargins(4, 4, 4, 4)
            getattr(self, '_build_' + title.lower())(layout)
            layout.addStretch()
            scroll.setWidget(content)
            self.pages.addWidget(scroll)
        self.category_buttons.idClicked.connect(self._category_changed)
        self.category_buttons.button(0).setChecked(True)
        self.tabs.addTab(edit, 'Edit')
        mix = QWidget()
        mix_layout = QVBoxLayout(mix)
        mix_layout.setContentsMargins(0, 8, 0, 0)
        label = QLabel('To mix settings into your current style, sample or drag from the lower pane and apply to the desired settings categories.')
        label.setWordWrap(True)
        mix_layout.addWidget(label)
        mix_layout.addSpacing(24)
        self._mix_source = None
        self.mix_sources = {}  # Legacy programmatic source lookup, hidden from the UI.
        self.mix_targets = {}
        targets = QVBoxLayout()
        targets.setContentsMargins(18, 0, 0, 0)
        targets.setSpacing(6)
        for category, icon in zip(CATEGORIES, category_icons):
            combo = QComboBox(self)
            combo.hide()
            self.mix_sources[category] = combo
            button = _MixTarget(category, QIcon(str(icon_dir / f'dlg_style_{icon}.png')), self._apply_mix_target)
            self.mix_targets[category] = button
            targets.addWidget(button, 0, Qt.AlignLeft)
        mix_layout.addLayout(targets)
        mix_layout.addSpacing(24)
        mix_layout.addStretch(1)
        self._separator(mix_layout)
        source_tabs = QTabWidget()
        self.mix_browser = StyleBrowser(window.viewport.scene, style_thumbnail)
        self.mix_browser.setMinimumHeight(220)
        self.mix_browser.styleSelected.connect(self._sample_mix_style)
        self.mix_browser.modelChanged.connect(self._changed)
        source_tabs.addTab(self.mix_browser, 'Select')
        mix_layout.addWidget(source_tabs, 2)
        self.tabs.addTab(mix, 'Mix')
        self.tabs.setCurrentIndex(1)
        self._updating = False
        self.refresh()

    @staticmethod
    def _separator(layout):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

    def _check(self, layout, label, key):
        box = QCheckBox(label)
        self.controls[key] = box
        box.toggled.connect(self._apply_edits)
        layout.addWidget(box)
        return box

    def _combo_control(self, layout, label, key, choices):
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        combo = QComboBox()
        for text, value in choices:
            combo.addItem(text, value)
        combo.currentIndexChanged.connect(self._apply_edits)
        self.controls[key] = combo
        row.addWidget(combo, 1)
        layout.addLayout(row)
        return combo

    def _number(self, key, low, high, decimals=None):
        number = QSpinBox() if decimals is None else QDoubleSpinBox()
        if decimals is not None:
            number.setDecimals(decimals)
        number.setRange(low, high)
        number.setKeyboardTracking(False)
        number.valueChanged.connect(self._apply_edits)
        number.setMaximumWidth(80)
        self.controls[key] = number
        return number

    def _check_number(self, layout, label, key, amount):
        row = layout.rowCount()
        label_cell = QHBoxLayout()
        box = self._check(label_cell, label, key)
        number = self._number(amount, 1, 32)
        number.setFixedWidth(80)
        layout.addLayout(label_cell, row, 0)
        layout.addWidget(number, row, 1)
        self._dependent.append((number, key))
        return box

    def _slider(self, layout, label, key, low=0, high=100, scale=100):
        layout.addWidget(QLabel(label))
        row = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(low, high)
        slider.valueChanged.connect(self._apply_edits)
        slider.setProperty('scale', scale)
        self.controls[key] = slider
        row.addWidget(slider, 1)
        percentage = scale == 100 and (key.endswith('_opacity') or key == 'xray_opacity')
        number_scale = 1 if percentage else scale
        value = QDoubleSpinBox() if number_scale != 1 else QSpinBox()
        if number_scale != 1:
            value.setDecimals(2)
        value.setRange(low/number_scale, high/number_scale)
        value.setKeyboardTracking(False)
        value.setMaximumWidth(76)
        value.setValue(slider.value()/number_scale)
        # A user edit follows the same signal path as dragging the slider.
        value.valueChanged.connect(lambda v: slider.setValue(round(v*number_scale)))
        slider.valueChanged.connect(lambda v: value.setValue(v/number_scale))
        row.addWidget(value)
        layout.addLayout(row)
        return slider

    def _swatch(self, title, attr):
        chip = ColorChip(title, lambda: self._pick_color(title, attr))
        self.swatches[attr] = chip
        return chip

    def _color_row(self, layout, label, key):
        row = QHBoxLayout()
        row.addWidget(QLabel(label), 1)
        chip = self._swatch(label, key)
        row.addWidget(chip)
        row.addStretch()
        layout.addLayout(row)
        return chip

    def _build_edge(self, layout):
        self._edges = self._check(layout, 'Edges', 'edges')
        self._back_edges = self._check(layout, 'Back Edges', 'back_edges')
        self._separator(layout)
        effects = QGridLayout()
        effects.setColumnStretch(2, 1)
        layout.addLayout(effects)
        self._profiles = self._check_number(effects, 'Profiles', 'profiles', 'profile_width')
        self._check_number(effects, 'Depth cue', 'depth_cue', 'depth_cue_width')
        self._check_number(effects, 'Extension', 'extensions', 'extension_length')
        self._check_number(effects, 'Endpoints', 'endpoints', 'endpoint_size')
        self._check(layout, 'Dashes', 'dashes')
        self._separator(layout)
        row = QHBoxLayout()
        row.addWidget(QLabel('Color:'))
        combo = QComboBox()
        for label, key in [('All same', 'all_same'), ('By material', 'by_material'), ('By axis', 'by_axis')]:
            combo.addItem(label,key)
        self.controls['edge_color_mode'] = combo
        combo.currentIndexChanged.connect(self._apply_edits)
        row.addWidget(combo,1)
        self._edge_c = self._swatch('Edge color', 'edge_color')
        row.addWidget(self._edge_c)
        layout.addLayout(row)

    def _build_face(self, layout):
        self._front_c = self._color_row(layout, 'Front color', 'front_color')
        self._back_c = self._color_row(layout, 'Back color', 'back_color')
        self._separator(layout)
        row = QHBoxLayout()
        styles_column = QVBoxLayout()
        styles_column.addWidget(QLabel('Style'))
        buttons = QHBoxLayout()
        self._mode = QComboBox(self)
        self._mode.hide()
        self.controls['face_mode'] = self._mode
        self._mode.currentIndexChanged.connect(self._apply_edits)
        for key, label in self._MODES:
            self._mode.addItem(label, key)
        self.face_buttons = QButtonGroup(self)
        icon_dir = app_root() / 'resources' / 'icons'
        self._xray_base_mode = 'textures'
        for index, (key, label) in enumerate(self._MODES[:-1]):
            button = QToolButton()
            filename = 'hiddenline' if key == 'hidden_line' else key
            button.setIcon(QIcon(str(icon_dir / f'dlg_style_face_{filename}.png')))
            button.setIconSize(QSize(24, 24))
            button.setToolTip(label)
            button.setAccessibleName(label)
            button.setCheckable(True)
            self.face_buttons.addButton(button, index)
            buttons.addWidget(button)
            if key == 'monochrome':
                self.pbr_button = QToolButton()
                self.pbr_button.setIcon(QIcon(str(icon_dir / 'dlg_style_face_pbr.png')))
                self.pbr_button.setIconSize(QSize(24, 24))
                self.pbr_button.setEnabled(False)
                self.pbr_button.setToolTip('Physically Based Rendering is not supported yet')
                self.pbr_button.setAccessibleName('Physically Based Rendering')
                buttons.addWidget(self.pbr_button)
        self.face_buttons.idClicked.connect(lambda i: self._mode.setCurrentIndex(i))
        styles_column.addLayout(buttons)
        row.addLayout(styles_column)
        row.addSpacing(12)
        xray_column = QVBoxLayout()
        self.face_style_name = QLabel('X-ray')
        xray_column.addWidget(self.face_style_name)
        self.xray_button = QToolButton()
        self.xray_button.setIcon(QIcon(str(icon_dir / 'tb_xray.png')))
        self.xray_button.setIconSize(QSize(24, 24))
        self.xray_button.setToolTip('X-ray')
        self.xray_button.setAccessibleName('X-ray')
        self.xray_button.setCheckable(True)
        self.xray_button.toggled.connect(self._toggle_xray)
        xray_column.addWidget(self.xray_button, 0, Qt.AlignLeft)
        row.addLayout(xray_column)
        row.addStretch()
        layout.addLayout(row)
        self._separator(layout)
        self._check(layout, 'Material transparency', 'material_transparency')
        quality = self._combo_control(layout, 'Transparency quality:', 'transparency_quality',
                                     [('Faster', 'faster'), ('Nicer', 'nicer')])
        self._dependent.append((quality, 'material_transparency'))
        self._slider(layout, 'X-ray opacity:', 'xray_opacity', 20, 80)
        self._separator(layout)
        self._check(layout, 'Ambient Occlusion', 'ambient_occlusion')
        ao = QRadioButton('Default color')
        self.controls['ao_default_color'] = ao
        ao.toggled.connect(self._apply_edits)
        layout.addWidget(ao)
        self.ao_picker = QRadioButton('Use color picker')
        self.ao_picker.toggled.connect(lambda on: self.controls['ao_default_color'].setChecked(False) if on else None)
        layout.addWidget(self.ao_picker)
        self._dependent.append((ao, 'ambient_occlusion'))
        self._dependent.append((self.ao_picker, 'ambient_occlusion'))
        self._color_row(layout, 'Select Color', 'ao_color')
        self._slider(layout, 'Distance:', 'ao_distance', 1, 1000, 100)
        self._slider(layout, 'Intensity:', 'ao_intensity')
        self._slider(layout, 'Distance Multiplier', 'ao_multiplier', 1, 1000, 10)

    def _toggle_xray(self, enabled):
        if self._updating:
            return
        if enabled:
            current = self._mode.currentData()
            if current != 'xray':
                self._xray_base_mode = current
            self._mode.setCurrentIndex(self._mode.findData('xray'))
        else:
            self._mode.setCurrentIndex(self._mode.findData(self._xray_base_mode))

    def _build_background(self, layout):
        grid = QGridLayout()
        grid.setColumnStretch(3, 1)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)
        layout.addLayout(grid)
        grid.addWidget(QLabel('Background'), 0, 0)
        self._bg_c = self._swatch('Background', 'background')
        grid.addWidget(self._bg_c, 0, 1)
        sky_label = QHBoxLayout()
        self._sky = self._check(sky_label, 'Sky', 'sky')
        grid.addLayout(sky_label, 1, 0)
        self._sky_c = self._swatch('Sky color', 'sky_color')
        grid.addWidget(self._sky_c, 1, 1)
        grid.addWidget(QLabel('Horizon'), 2, 0)
        grid.addWidget(self._swatch('Horizon', 'horizon_color'), 2, 1)
        ground_label = QHBoxLayout()
        self._check(ground_label, 'Ground', 'ground')
        grid.addLayout(ground_label, 3, 0)
        self._ground_c = self._swatch('Ground color', 'ground_color')
        grid.addWidget(self._ground_c, 3, 1)
        transparency_label = QLabel('Transparency')
        grid.addWidget(transparency_label, 2, 2, Qt.AlignLeft | Qt.AlignBottom)
        transparency = QSlider(Qt.Horizontal)
        transparency.setRange(0, 100)
        transparency.setProperty('scale', 100)
        transparency.setFixedWidth(110)
        transparency.valueChanged.connect(self._apply_edits)
        self.controls['ground_opacity'] = transparency
        grid.addWidget(transparency, 3, 2)
        below = self._check(layout, 'Show ground from below', 'show_ground_below')
        self._dependent.extend(((transparency_label, 'ground'),
                                (transparency, 'ground'), (below, 'ground')))

    def _build_watermark(self, layout):
        self._check(layout, 'Display watermarks', 'display_watermarks')
        self._separator(layout)
        row = QHBoxLayout()
        for text, tip, callback in (('＋', 'Add watermark', self.add_watermark),
                                    ('−', 'Remove watermark', self.remove_watermark),
                                    ('⚙', 'Watermark settings', self.edit_watermark)):
            button = QToolButton()
            button.setText(text)
            button.setToolTip(tip)
            button.clicked.connect(callback)
            row.addWidget(button)
        row.addStretch()
        for text, delta in (('↓', 1), ('↑', -1)):
            button = QToolButton()
            button.setText(text)
            button.setToolTip('Move watermark ' + ('down' if delta == 1 else 'up'))
            button.clicked.connect(lambda checked=False, d=delta: self.move_watermark(d))
            row.addWidget(button)
        layout.addLayout(row)
        self.watermark_list = QTableWidget(0, 2)
        self.watermark_list.setHorizontalHeaderLabels(['Thumb', 'Name'])
        self.watermark_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.watermark_list.verticalHeader().hide()
        self.watermark_list.setSelectionBehavior(QTableWidget.SelectRows)
        self.watermark_list.setSelectionMode(QTableWidget.SingleSelection)
        self.watermark_list.setEditTriggers(QTableWidget.NoEditTriggers)
        self.watermark_list.cellDoubleClicked.connect(lambda *_: self.edit_watermark())
        layout.addWidget(self.watermark_list, 1)

    def _build_modeling(self, layout):
        grid = QGridLayout()
        pairs = [('selected_color', 'Selected'), ('inactive_section_color', 'Inactive Section'),
                 ('locked_color', 'Locked'), ('active_section_color', 'Active Section'),
                 ('guide_color', 'Guides'), ('section_fill_color', 'Section Fill'),
                 (None, None), ('section_line_color', 'Section Lines')]
        for i, (key, label) in enumerate(pairs):
            if key is None:
                continue
            row = QHBoxLayout()
            chip = self._swatch(label, key)
            if key == 'section_fill_color':
                self._fill_c = chip
            row.addWidget(chip)
            row.addWidget(QLabel(label), 1)
            grid.addLayout(row, i//2, i%2)
        layout.addLayout(grid)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(QLabel('Section Line Width'))
        row.addWidget(self._number('section_line_width', 1, 32, 1))
        layout.addLayout(row)
        self._separator(layout)
        grid = QGridLayout()
        for index, (key, label) in enumerate((
                ('show_hidden_geometry', 'Hidden Geometry'), ('show_axes', 'Model Axes'),
                ('show_hidden_objects', 'Hidden Objects'), ('show_section_planes', 'Section Planes'),
                ('color_by_layer', 'Color by Tag'), ('show_section_cuts', 'Section Cuts'),
                ('show_guides', 'Guides'), ('section_fill', 'Section Fill'))):
            row = QHBoxLayout()
            box = self._check(row, label, key)
            if key == 'section_fill':
                self._fill = box
            grid.addLayout(row, index//2, index%2)
        layout.addLayout(grid)
        self._check(layout, 'Override Section Fill by Style', 'override_section_fill')
        self._separator(layout)
        title = QLabel('Match Photo')
        title.setStyleSheet('font-weight: bold;')
        layout.addWidget(title)
        photo = QPushButton('Choose matched photo…')
        photo.clicked.connect(self.choose_photo)
        photo.setToolTip('Use an image for the current camera view. Camera matching is performed separately.')
        layout.addWidget(photo)
        self._check(layout, 'Foreground Photo', 'foreground_photo')
        self._slider(layout, 'Opacity', 'foreground_photo_opacity')
        self._check(layout, 'Background Photo', 'background_photo')
        self._slider(layout, 'Opacity', 'background_photo_opacity')

    def _category_changed(self, index):
        self.pages.setCurrentIndex(index)
        self.category_title.setText(CATEGORIES[index])

    def _shown_color(self, attr):
        style = self._style()
        if attr == 'guide_color' and style.guide_color is None:
            vp = self._window.viewport
            if hasattr(vp, 'construction_line_color'):
                color = vp.construction_line_color()
                return color.redF(), color.greenF(), color.blueF()
            return (.27, .35, .47)
        if attr == 'horizon_color' and style.horizon_color is None:
            return (1, 1, 1)
        if attr == 'section_line_color' and style.section_line_color is None:
            return style.edge_color
        if attr == 'back_color':
            from core.style import effective_back_color
            return effective_back_color(style,self._window.viewport.scene)
        return getattr(style,attr)

    def refresh(self):
        style = self._style()
        if style is None:
            return
        self._updating = True
        try:
            from core.style_library import model_styles
            presets = BUILTIN_STYLES + user_styles() + model_styles(self._window.viewport.scene)
            signature = [s.to_dict() for s in presets]
            if getattr(self,'_library_signature',None) != signature:
                self._library_signature = signature
                self._combo.clear()
                for s in presets:
                    self._combo.addItem(s.name,s.name)
                    self._combo.setItemData(self._combo.count()-1,s.to_dict(),Qt.UserRole+1)
                for combo in self.mix_sources.values():
                    selected = combo.currentData()
                    combo.clear()
                    for s in presets:
                        combo.addItem(s.name,s.name)
                        combo.setItemData(combo.count()-1,s.to_dict(),Qt.UserRole+1)
                    combo.setCurrentIndex(max(0,combo.findData(selected)))
            self.browser.scene = self._window.viewport.scene
            self.browser.refresh()
            self.mix_browser.scene = self._window.viewport.scene
            self.mix_browser.refresh()
            self._combo.setCurrentIndex(self._combo.findData(style.name))
            if self.name.text() != style.name:
                self.name.setText(style.name)
            if self.description.toPlainText() != style.description:
                self.description.setPlainText(style.description)
            self.preview.setPixmap(style_thumbnail(style))
            for key, control in self.controls.items():
                value = getattr(style, key)
                if key == 'ground_opacity':
                    value = 1-value
                if key in SCENE_FLAGS:
                    value = getattr(self._window.viewport.scene, key, value)
                if isinstance(control, (QCheckBox, QRadioButton)):
                    control.setChecked(value)
                elif isinstance(control, QComboBox):
                    control.setCurrentIndex(control.findData(value))
                elif isinstance(control, QSlider):
                    control.setValue(round(value * control.property('scale')))
                else:
                    control.setValue(value)
            for key, chip in self.swatches.items():
                color = self._shown_color(key)
                chip.set_color(color)
            for control, key in self._dependent:
                control.setEnabled(getattr(style, key))
            self.ao_picker.setChecked(not style.ao_default_color)
            self.controls['xray_opacity'].setEnabled(style.face_mode == 'xray')
            for key in ('ao_distance', 'ao_intensity', 'ao_multiplier'):
                self.controls[key].setEnabled(style.ambient_occlusion)
            self.swatches['ao_color'].setEnabled(style.ambient_occlusion and not style.ao_default_color)
            for key in ('foreground_photo', 'background_photo'):
                self.controls[key].setEnabled(bool(style.photo_image))
                self.controls[key + '_opacity'].setEnabled(bool(style.photo_image) and getattr(style, key))
            selected_mode = self._xray_base_mode if style.face_mode == 'xray' else style.face_mode
            self.face_buttons.button(self._mode.findData(selected_mode)).setChecked(True)
            self.xray_button.setChecked(style.face_mode == 'xray')
            self._del_btn.setEnabled(any(s.uid == style.uid for s in self._window.viewport.scene.styles) if style.uid else style.name not in builtin_names())
            self._refresh_watermarks()
        finally:
            self._updating = False

    def _apply_edits(self, *_):
        if self._updating:
            return
        style = self._style()
        for key, control in self.controls.items():
            if isinstance(control, (QCheckBox, QRadioButton)):
                value = control.isChecked()
            elif isinstance(control, QComboBox):
                value = control.currentData()
                if value is None:
                    continue
            elif isinstance(control, QSlider):
                value = control.value()/control.property('scale')
            else:
                value = control.value()
            if key == 'ground_opacity':
                value = 1-value
            setattr(style, key, value)
            if key in SCENE_FLAGS:
                scene = self._window.viewport.scene
                if getattr(scene, key) != value:
                    setter = getattr(self._window, '_set_hidden_view' if key.startswith('show_hidden') else '_set_section_visibility', None)
                    if setter is not None:
                        setter(key, value)
                    else:
                        setattr(scene, key, value)
                        scene.version += 1
        self._changed()

    def _persist_model_style(self):
        style=self._style()
        scene=self._window.viewport.scene
        if style.uid and any(s.uid==style.uid for s in scene.styles):
            from core.style_library import store_model_style
            store_model_style(scene,style)

    def _changed(self):
        self._persist_model_style()
        self._window._sync_style_menu()
        if hasattr(self._window, '_sync_section_menu'):
            self._window._sync_section_menu()
        self.refresh()
        self._window.viewport.update()
        if hasattr(self._window, '_update_title'):
            self._window._update_title()

    def _metadata_changed(self):
        if not self._updating:
            self._style().name = self.name.text().strip() or 'Untitled style'
            self._style().description = self.description.toPlainText()
            self._persist_model_style()
            self.preview.setPixmap(style_thumbnail(self._style()))
            if hasattr(self._window, '_update_title'):
                self._window._update_title()

    def _on_pick(self, index):
        raw = self._combo.itemData(index,Qt.UserRole+1)
        picked = Style.from_dict(raw) if isinstance(raw,dict) else None
        if picked is not None:
            self._window.viewport.scene.display_style = picked
            self._apply_scene_flags(picked)
            self._changed()

    def _apply_browser_style(self,style):
        from core.style_library import store_model_style
        scene = self._window.viewport.scene
        scene.display_style = style.copy()
        store_model_style(scene,scene.display_style)
        self._apply_scene_flags(scene.display_style)
        self._changed()

    def _apply_scene_flags(self, style):
        scene = self._window.viewport.scene
        changed = any(getattr(scene,key) != getattr(style,key) for key in SCENE_FLAGS)
        for key in SCENE_FLAGS:
            setattr(scene, key, getattr(style, key))
        if changed:
            scene.version += 1

    def _pick_library(self, item):
        self._on_pick(self._combo.findData(item.data(Qt.UserRole)))

    def _apply_mix_target(self, category, source=None):
        source = source or self._mix_source
        if source is not None:
            self.mix_category(category, source)

    def _sample_mix_style(self, source):
        # Sampling never changes the active style until a category is chosen.
        self._mix_source = source.copy()
        for category, button in self.mix_targets.items():
            button.setToolTip('Apply ' + category.lower() + ' settings from ' + source.name)

    def mix_category(self, category, source=None):
        import copy
        if source is None:
            source = self._mix_source
        if source is None:
            raw = self.mix_sources[category].currentData(Qt.UserRole+1)
            source = Style.from_dict(raw) if isinstance(raw,dict) else None
        if source is None:
            return
        style = self._style()
        for key in CATEGORY_FIELDS[category]:
            setattr(style, key, copy.deepcopy(getattr(source, key)))
        if category == 'Modeling':
            self._apply_scene_flags(style)
        self._changed()

    def _pick_color(self, title, attr):
        self._pick_color_impl(title,attr)
        self._persist_model_style()
        if hasattr(self._window, '_update_title'):
            self._window._update_title()

    def _on_save(self):
        from core.style_library import create_model_style, model_styles
        scene=self._window.viewport.scene
        for key in SCENE_FLAGS:setattr(self._style(),key,getattr(scene,key))
        existing={style.name for style in model_styles(scene)}
        number=1
        while 'Style '+str(number) in existing:number+=1
        name,ok=_prompts.get_text(_dialog_parent(self),'Create Style','Style name:',text='Style '+str(number))
        if not ok:return
        try:create_model_style(scene,name)
        except ValueError as error:
            QMessageBox.warning(_dialog_parent(self),'Create Style',str(error));return
        self.browser.open('model')
        self._changed()

    def _update_saved(self):
        from core.style_library import store_model_style
        scene=self._window.viewport.scene
        for key in SCENE_FLAGS:setattr(self._style(),key,getattr(scene,key))
        store_model_style(scene,self._style())
        self._changed()

    def _options(self):
        menu=QMenu(self)
        menu.addAction('Create a new style…',self._on_save)
        menu.addAction('Update style in model',self._update_saved)
        menu.addAction('Save to collection…',self.browser.save_to_collection)
        menu.addAction('Delete style from model',self._on_delete)
        menu.exec(self.mapToGlobal(self.rect().topRight()))

    def _refresh_watermarks(self):
        row = self.watermark_list.currentRow()
        self.watermark_list.setRowCount(len(self._style().watermarks))
        for index, mark in enumerate(self._style().watermarks):
            thumb = QTableWidgetItem()
            pm = QPixmap()
            try:
                pm.loadFromData(base64.b64decode(mark.get('image', ''), validate=True))
            except (ValueError, TypeError):
                pass
            thumb.setIcon(QIcon(pm))
            self.watermark_list.setItem(index, 0, thumb)
            self.watermark_list.setItem(index, 1, QTableWidgetItem(mark.get('name', 'Watermark')))
        if 0 <= row < self.watermark_list.rowCount():
            self.watermark_list.selectRow(row)

    def _read_image(self, title):
        path, _ = QFileDialog.getOpenFileName(self, title, '', 'Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if not path:
            return None
        from PySide6.QtGui import QImage
        image = QImage(path)
        if image.isNull():
            return None
        # Store a bounded PNG in the style so libraries and models travel together.
        image = image.scaled(2048, 2048, Qt.KeepAspectRatio, Qt.SmoothTransformation) if max(image.width(), image.height()) > 2048 else image
        from PySide6.QtCore import QBuffer, QIODevice
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, 'PNG')
        return Path(path).stem, base64.b64encode(bytes(buffer.data())).decode('ascii')

    def add_watermark(self):
        result = self._read_image('Add watermark')
        if result is None:
            return
        name, image = result
        self._style().watermarks.append(dict(name=name, image=image, opacity=0.5,
                                            position='bottom_right', scale=0.25, layer='overlay'))
        self._changed()
        self.watermark_list.selectRow(len(self._style().watermarks)-1)
        self.edit_watermark()

    def remove_watermark(self):
        row = self.watermark_list.currentRow()
        if 0 <= row < len(self._style().watermarks):
            del self._style().watermarks[row]
            self._changed()

    def move_watermark(self, delta):
        row = self.watermark_list.currentRow()
        target = row + delta
        marks = self._style().watermarks
        if 0 <= row < len(marks) and 0 <= target < len(marks):
            marks[row], marks[target] = marks[target], marks[row]
            self._changed()
            self.watermark_list.selectRow(target)

    def edit_watermark(self):
        row = self.watermark_list.currentRow()
        if not 0 <= row < len(self._style().watermarks):
            return
        mark = self._style().watermarks[row]
        dialog = QDialog(self)
        dialog.setWindowTitle('Watermark Settings')
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        name = QLineEdit(mark.get('name', 'Watermark'))
        form.addRow('Name', name)
        position = QComboBox()
        for key in ('top_left', 'top_right', 'center', 'bottom_left', 'bottom_right', 'stretch', 'tile'):
            position.addItem(key.replace('_', ' ').title(), key)
        position.setCurrentIndex(max(0, position.findData(mark.get('position'))))
        form.addRow('Position', position)
        layer = QComboBox()
        layer.addItem('Overlay', 'overlay')
        layer.addItem('Background', 'background')
        layer.setCurrentIndex(max(0, layer.findData(mark.get('layer'))))
        form.addRow('Layer', layer)
        opacity = QDoubleSpinBox()
        opacity.setRange(0, 1)
        opacity.setSingleStep(.05)
        opacity.setValue(mark.get('opacity', .5))
        form.addRow('Opacity', opacity)
        scale = QDoubleSpinBox()
        scale.setRange(.01, 2)
        scale.setSingleStep(.05)
        scale.setValue(mark.get('scale', .25))
        form.addRow('Size relative to view', scale)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.Accepted:
            mark.update(name=name.text(), position=position.currentData(), layer=layer.currentData(),
                        opacity=opacity.value(), scale=scale.value())
            self._changed()

    def choose_photo(self):
        result = self._read_image('Choose matched photo')
        if result:
            self._style().photo_image = result[1]
            self._style().background_photo = True
            self._changed()


    def _style(self):
        return getattr(self._window.viewport.scene, "display_style", None)


    def _pick_color_impl(self, title: str, attr: str) -> None:
        style = self._style()
        if style is None:
            return
        c = self._shown_color(attr)
        chosen = get_color(
            QColor.fromRgbF(*(float(v) for v in c[:3])), _dialog_parent(self), title)
        if not chosen.isValid():
            return
        setattr(style, attr, (chosen.redF(), chosen.greenF(), chosen.blueF()))
        self.refresh()
        self._window.viewport.update()
        # Every colour is editable in every mode (build the look, save it) —
        # but an edit that can't show RIGHT NOW says so, or it reads as
        # "styles don't work" (it did, live, 2026-08-31).
        hint = self._color_hint(attr)
        if hint:
            bar = getattr(self._window, "statusBar", None)
            if callable(bar):
                bar().showMessage(hint, 4000)


    def _color_hint(self, attr: str) -> str | None:
        """Why the colour just edited may not be visible right now (``None``
        when it should be showing)."""
        style = self._style()
        if style is None:
            return None
        mode = style.face_mode
        if attr == "front_color" and mode not in ("hidden_line", "monochrome"):
            return tr("Front color saved — it paints faces in Hidden line "
                      "and Monochrome modes.")
        if attr == "back_color" and mode in ("hidden_line", "wireframe"):
            return tr("Back color saved — it paints back faces in Textures, "
                      "Shaded, Monochrome and X-ray modes.")
        if attr == "background" and style.sky:
            return tr("Background saved — it shows with the sky off.")
        if attr in ("sky_color", "ground_color") and not style.sky:
            return tr("Sky and ground colors show with the sky on.")
        if attr == "edge_color" and not style.edges and mode != "wireframe":
            return tr("Edge color saved — this style has edges off.")
        if attr == "section_fill_color" and not style.section_fill:
            return tr("Section fill color saved — section fill is off in "
                      "this style.")
        return None


    def _on_delete(self):
        from core.style_library import delete_model_style
        style=self._style()
        if QMessageBox.question(_dialog_parent(self),'Delete Style',
                "Remove '"+style.name+"' from the model library? Saved scenes keep their style.") != QMessageBox.Yes:return
        scene=self._window.viewport.scene
        delete_model_style(scene,style.uid or style.name)
        scene.display_style=Style()
        self._changed()
