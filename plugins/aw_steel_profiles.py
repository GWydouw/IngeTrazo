# SPDX-License-Identifier: GPL-3.0-or-later
"""Steel Profiles for IngeTrazo, ported from Guy Wydouw's AW Tools.

Self-contained extension: copy this file into the user plugins directory.
Section dimensions use millimetres; IngeTrazo geometry uses metres.
Like the original, sections have sharp corners and parallel flanges.
"""
from __future__ import annotations

import copy
import math

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QAction, QColor, QIcon, QMatrix4x4, QPainter, QPainterPath, QPen, QPixmap,
    QVector3D, QVector4D,
)
from PySide6.QtWidgets import (
    QAbstractSpinBox, QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMessageBox,
    QSizePolicy, QToolBar, QToolButton, QVBoxLayout, QWidget,
)

from core.group import Group
from core.history import Command
from core.i18n import tr
from core.mesh import Mesh
from tools.base import AxisMagnet, Tool

KEY = "aw_steel_profiles"
# CATALOG is appended below from the original AW Tools library.


def validate(params):
    kind = params['kind']
    if kind not in CATALOG:
        raise ValueError("Unknown profile family")
    w, h, tw, tf = params['dimensions']
    if not all(math.isfinite(v) and v > 0 for v in (w, h, tw, tf)):
        raise ValueError("Dimensions must be positive and finite")
    valid = True
    if kind in ('CHS', 'RHS', 'SHS'):
        valid = 2 * tw < min(w, h)
    elif kind in ('L1', 'L2'):
        valid = tw < min(w, h)
    elif kind not in ('ROUND', 'SQUARE', 'FLAT'):
        valid = tw < w and 2 * tf < h
    if not valid:
        raise ValueError("Thickness is too large for this section")
    if params['horizontal'] not in (0, 1, 2) or params['vertical'] not in (0, 1, 2):
        raise ValueError("Invalid alignment")


def section_rings(params):
    validate(params)
    w, h, tw, tf = [v / 1000 for v in params['dimensions']]
    kind, c = params['kind'], w / 2
    if kind in ('CHS', 'ROUND'):
        def circle(r):
            return [(c + r * math.cos(i * math.tau / 32),
                     c + r * math.sin(i * math.tau / 32)) for i in range(32)]
        rings = [circle(c)]
        if kind == 'CHS':
            rings.append(circle(c - tw))
    else:
        if kind in ('IPE', 'IPN', 'HEA', 'HEB', 'HEM'):
            outer = [(0,0),(w,0),(w,tf),(c+tw/2,tf),(c+tw/2,h-tf),
                     (w,h-tf),(w,h),(0,h),(0,h-tf),(c-tw/2,h-tf),
                     (c-tw/2,tf),(0,tf)]
        elif kind in ('UPE', 'UPN', 'UNP', 'C'):
            outer = [(0,0),(w,0),(w,tf),(tw,tf),(tw,h-tf),(w,h-tf),(w,h),(0,h)]
        elif kind == 'T':
            outer = [(c-tw/2,0),(c+tw/2,0),(c+tw/2,h-tf),(w,h-tf),
                     (w,h),(0,h),(0,h-tf),(c-tw/2,h-tf)]
        elif kind in ('L1', 'L2'):
            outer = [(0,0),(w,0),(w,tw),(tw,tw),(tw,h),(0,h)]
        elif kind == 'Z':
            outer = [(0,0),(c+tw/2,0),(c+tw/2,h-tf),(w,h-tf),
                     (w,h),(c-tw/2,h),(c-tw/2,tf),(0,tf)]
        else:
            outer = [(0,0),(w,0),(w,h),(0,h)]
        rings = [outer]
        if kind in ('RHS', 'SHS'):
            rings.append([(tw,tw),(w-tw,tw),(w-tw,h-tw),(tw,h-tw)])
    ox = params['horizontal'] * w / 2
    oy = params['vertical'] * h / 2
    return [[(x-ox, y-oy) for x,y in ring] for ring in rings]


def profile_mesh(params, length):
    if not math.isfinite(length) or length <= 1e-6:
        raise ValueError("Choose two distinct points")
    rings = section_rings(params)
    mesh = Mesh()
    bottom = [[QVector3D(x,y,0) for x,y in ring] for ring in rings]
    top = [[QVector3D(x,y,length) for x,y in ring] for ring in rings]
    mesh.add_face(list(reversed(bottom[0])), bottom[1:])
    mesh.add_face(top[0], [list(reversed(r)) for r in top[1:]])
    for index, ring in enumerate(bottom):
        for i in range(len(ring)):
            j = (i+1) % len(ring)
            quad = [ring[i], ring[j], top[index][j], top[index][i]]
            mesh.add_face(quad if index == 0 else list(reversed(quad)))
    return mesh


def make_profile(params, start, end):
    axis = end - start
    length = axis.length()
    mesh = profile_mesh(params, length)
    z = axis.normalized()
    x = QVector3D.crossProduct(QVector3D(0,0,1), z)
    if x.length() < 1e-6:
        x = QVector3D.crossProduct(QVector3D(0,1,0), z)
    x.normalize()
    y = QVector3D.crossProduct(z, x).normalized()
    matrix = QMatrix4x4()
    for i, vec in enumerate((x, y, z)):
        matrix.setColumn(i, QVector4D(vec, 0))
    matrix.setColumn(3, QVector4D(start, 1))
    group = Group(mesh, name=params['label'])
    group.xform = matrix
    group.ext = {KEY: {'version': 1, 'params': copy.deepcopy(params), 'length': length}}
    return group


class ProfileCommand(Command):
    """Create or replace a section atomically, retaining its placement."""
    def __init__(self, group, params=None):
        self.group, self.params = group, params
        self.before = self.after = None

    def do(self, scene):
        if scene.edit_group is not None:
            raise ValueError("Close the group before drawing or editing a steel profile")
        if self.params is None:
            scene.groups.append(self.group)
        else:
            g = self.group
            if g not in scene.groups or g.xform is None:
                raise ValueError("This profile's geometry was exploded or edited directly")
            if self.after is None:
                mesh = profile_mesh(self.params, g.ext[KEY]['length'])
                self.before = (g.mesh, g.name, copy.deepcopy(g.ext))
                ext = copy.deepcopy(g.ext)
                ext[KEY]['params'] = copy.deepcopy(self.params)
                self.after = (mesh, self.params['label'], ext)
            g.mesh, g.name, g.ext = self.after
        scene.selection.clear()
        scene.selection.add(self.group)
        scene.version += 1

    def undo(self, scene):
        if self.params is None:
            scene.groups.remove(self.group)
            scene.selection.discard(self.group)
        else:
            self.group.mesh, self.group.name, self.group.ext = self.before
        scene.version += 1


def execute(viewport, command):
    viewport.history.execute(command)
    if viewport.history.last_error:
        QMessageBox.warning(viewport, 'Steel Profiles', viewport.history.last_error)
        return False
    viewport.notify_scene_changed()
    viewport.update()
    return True


def _DrawProfile(params):
    """Construct the interactive tool without registering a one-shot menu tool."""
    class DrawProfile(AxisMagnet, Tool):
        name = 'Steel Profiles'
        vcb_label = 'Length'

        def __init__(self, params):
            self.params = copy.deepcopy(params)
            self.start_point = self.hover_point = None

        def on_activate(self, viewport):
            self.on_cancel(viewport)
            viewport.flash_status('Choose the start and end of the steel profile.', 5000)

        def on_deactivate(self, viewport):
            self.start_point = self.hover_point = None

        def on_cancel(self, viewport):
            self.start_point = self.hover_point = None
            viewport.update()

        def on_click(self, ctx):
            if self.start_point is None:
                self.start_point = QVector3D(ctx.world)
            else:
                self._commit(ctx.viewport, ctx.world)
            ctx.viewport.update()

        def on_hover(self, ctx):
            self.hover_point = QVector3D(ctx.world)
            ctx.viewport.update()

        def on_value(self, viewport, value):
            if self.start_point is None or self.hover_point is None or value <= 0:
                return False
            direction = self.hover_point - self.start_point
            if direction.length() < 1e-6:
                return False
            return self._commit(viewport, self.start_point + direction.normalized() * value)

        def _commit(self, viewport, end):
            if (end - self.start_point).length() <= 1e-6:
                return False
            group = make_profile(self.params, self.start_point, end)
            if execute(viewport, ProfileCommand(group)):
                self.on_cancel(viewport)
                return True
            return False

        def rubber_band_lines(self):
            if self.start_point is None or self.hover_point is None:
                return []
            if (self.hover_point-self.start_point).length() <= 1e-6:
                return []
            g = make_profile(self.params, self.start_point, self.hover_point)
            return [(g.xform.map(e.a), g.xform.map(e.b)) for e in g.mesh.edges]

        def status_clause(self):
            return f"{self.params['label']} · click two points · Esc cancels · type a length"
    return DrawProfile(params)


def profile_icon(kind: str) -> QIcon:
    """Render a crisp section icon using the same outline as the model."""
    params = dict(kind=kind, dimensions=CATALOG[kind]['defaults'],
                  horizontal=0, vertical=0)
    rings = section_rings(params)
    width, height = [v / 1000 for v in params['dimensions'][:2]]
    pixmap = QPixmap(96, 96)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#f3f7fb'))
    painter.drawRoundedRect(QRectF(2, 2, 92, 92), 10, 10)
    scale = 76 / max(width, height)
    path = QPainterPath()
    path.setFillRule(Qt.OddEvenFill)
    for ring in rings:
        points = [QPointF(48 + (x-width/2)*scale, 48 - (y-height/2)*scale)
                  for x, y in ring]
        path.moveTo(points[0])
        for point in points[1:]:
            path.lineTo(point)
        path.closeSubpath()
    painter.setPen(QPen(QColor('#284c6a'), 4))
    painter.setBrush(QColor('#88a8c2'))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


class AlignmentGrid(QWidget):
    """Nine keyboard-accessible anchors arranged like the section bounds."""
    changed = Signal(int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        self.buttons = QButtonGroup(self)
        self.buttons.setExclusive(True)
        for row in range(3):
            for column in range(3):
                vertical = 2-row
                button = QToolButton()
                button.setCheckable(True)
                button.setFixedSize(16, 16)
                text = tr('{vertical} {horizontal}',
                          vertical=tr(('Bottom', 'Middle', 'Top')[vertical]),
                          horizontal=tr(('Left', 'Centre', 'Right')[column]))
                button.setToolTip(text)
                button.setAccessibleName(text)
                button.setStyleSheet(
                    'QToolButton {border: none; background: transparent; '
                    'color: palette(text); font-size: 9px; border-radius: 8px;} '
                    'QToolButton:checked {color: #4da9ed; font-size: 15px;} '
                    'QToolButton:hover, QToolButton:focus {background: #d9eafa;}')
                button.setText('●')
                self.buttons.addButton(button, vertical*3+column)
                grid.addWidget(button, row, column)
        self.buttons.idClicked.connect(self._clicked)
        self.set_alignment(1, 1)

    def _clicked(self, anchor):
        self.set_alignment(anchor % 3, anchor // 3)
        self.changed.emit(anchor % 3, anchor // 3)

    def set_alignment(self, horizontal: int, vertical: int) -> None:
        """Select an anchor without emitting a user edit."""
        self.buttons.button(vertical*3+horizontal).setChecked(True)
        for button in self.buttons.buttons():
            button.setText('◎' if button.isChecked() else '●')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(QPen(QColor('#c8cdd3'), 1.5))
        painter.drawRect(QRectF(8, 8, 32, 32))


class DimensionSpinBox(QDoubleSpinBox):
    """Show compact dimensions while retaining submillimetre precision."""

    def textFromValue(self, value):
        return self.locale().toString(value, 'f', 3).rstrip('0').rstrip(
            self.locale().decimalPoint())


class ProfileDialog(QDialog):
    """Compact section picker with icons, dimensions and graphical alignment."""
    def __init__(self, parent, params=None, *, editing=False):
        super().__init__(parent)
        self._loading_dimensions = False
        self.setWindowTitle(tr('Steel Profiles'))
        self.resize(440, 190)
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        top = QHBoxLayout()
        top.setSpacing(6)
        self.family = QComboBox()
        self.family.setIconSize(QSize(26, 26))
        self.family.setMinimumHeight(36)
        self.family.setAccessibleName(tr('Profile family'))
        self.family.setStyleSheet('QComboBox {font-size: 12px; padding: 2px 6px;}')
        names = {'L1': tr('Equal angle'), 'L2': tr('Unequal angle'),
                 'FLAT': tr('Flat bar'), 'SQUARE': tr('Square bar'),
                 'ROUND': tr('Round bar')}
        for kind in CATALOG:
            self.family.addItem(profile_icon(kind), names.get(kind, kind), kind)
        self.preset = QComboBox()
        self.preset.setMinimumHeight(36)
        self.preset.setAccessibleName(tr('Size'))
        self.preset.setStyleSheet('QComboBox {font-size: 12px; padding: 2px 6px;}')
        self.family.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.family.setMinimumWidth(120)
        self.preset.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.preset.setMinimumWidth(130)
        top.addWidget(self.family, 4)
        top.addWidget(self.preset, 5)
        self.alignment = AlignmentGrid()
        top.addWidget(self.alignment)
        layout.addLayout(top)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)
        self.fold = QToolButton()
        self.fold.setText(tr('DIMENSIONS'))
        self.fold.setCheckable(True)
        self.fold.setChecked(True)
        self.fold.setArrowType(Qt.DownArrow)
        self.fold.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.fold.setStyleSheet('QToolButton {border: none; font-weight: 600; padding: 2px;}')
        layout.addWidget(self.fold)
        self.dimension_panel = QWidget()
        fields = QHBoxLayout(self.dimension_panel)
        fields.setContentsMargins(0, 0, 0, 0)
        fields.setSpacing(4)
        self.dimensions, self.rows, self.field_widgets = [], [], []
        for text in ('Width', 'Height', 'Web', 'Flange'):
            field = QWidget()
            column = QVBoxLayout(field)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(2)
            label = QLabel(tr(text))
            spin = DimensionSpinBox()
            spin.setDecimals(3)
            spin.setRange(0.001, 100000)
            spin.setSuffix(' mm')
            spin.setAlignment(Qt.AlignRight)
            spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
            spin.setMinimumHeight(28)
            spin.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
            spin.setMinimumWidth(60)
            spin.setAccessibleName(tr(text))
            spin.setStyleSheet('QDoubleSpinBox {font-size: 12px; padding: 2px 4px;}')
            spin.valueChanged.connect(self._custom_dimensions)
            column.addWidget(label)
            column.addWidget(spin)
            fields.addWidget(field, 1)
            self.dimensions.append(spin)
            self.rows.append(label)
            self.field_widgets.append(field)
        layout.addWidget(self.dimension_panel)
        self.fold.toggled.connect(self._fold_dimensions)
        # Hidden combo state keeps the established parameter contract.
        self.horizontal, self.vertical = QComboBox(self), QComboBox(self)
        self.horizontal.addItems(['Left', 'Centre', 'Right'])
        self.vertical.addItems(['Bottom', 'Middle', 'Top'])
        self.horizontal.hide()
        self.vertical.hide()
        self.horizontal.setCurrentIndex(1)
        self.vertical.setCurrentIndex(1)
        self.alignment.changed.connect(self._alignment_changed)
        self.horizontal.currentIndexChanged.connect(self._sync_alignment)
        self.vertical.currentIndexChanged.connect(self._sync_alignment)
        layout.addSpacing(3)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(tr('Apply') if editing else tr('Draw'))
        buttons.button(QDialogButtonBox.Cancel).setText(tr('Cancel'))
        buttons.button(QDialogButtonBox.Ok).setMinimumHeight(28)
        buttons.button(QDialogButtonBox.Cancel).setMinimumHeight(28)
        buttons.button(QDialogButtonBox.Ok).setStyleSheet(
            'QPushButton {background: #1769aa; color: white; font-weight: 600; '
            'border-radius: 6px; padding: 4px 14px;}')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.family.currentIndexChanged.connect(self._family_changed)
        self.preset.currentIndexChanged.connect(self._preset_changed)
        self._family_changed()
        if params:
            self.family.setCurrentIndex(self.family.findData(params['kind']))
            index = self.preset.findText(params['label'])
            self.preset.setCurrentIndex(max(0, index))
            self._loading_dimensions = True
            for spin, value in zip(self.dimensions, params['dimensions']):
                spin.setValue(value)
            self._loading_dimensions = False
            self.horizontal.setCurrentIndex(params['horizontal'])
            self.vertical.setCurrentIndex(params['vertical'])

    def _fold_dimensions(self, visible):
        self.dimension_panel.setVisible(visible)
        self.fold.setArrowType(Qt.DownArrow if visible else Qt.RightArrow)
        QTimer.singleShot(0, self.adjustSize)

    def _alignment_changed(self, horizontal, vertical):
        self.horizontal.setCurrentIndex(horizontal)
        self.vertical.setCurrentIndex(vertical)

    def _sync_alignment(self, *_):
        self.alignment.set_alignment(self.horizontal.currentIndex(), self.vertical.currentIndex())

    def _family_changed(self, *_):
        kind = self.family.currentData()
        self.preset.blockSignals(True)
        self.preset.clear()
        self.preset.addItem(tr('Custom dimensions'), None)
        for label, *dims in CATALOG[kind]['presets']:
            self.preset.addItem(label, dims)
        self.preset.blockSignals(False)
        self._loading_dimensions = True
        for spin, value in zip(self.dimensions, CATALOG[kind]['defaults']):
            spin.setValue(value)
        self._loading_dimensions = False
        visible = {'CHS': (0,2), 'SHS': (0,2), 'L1': (0,2),
                   'ROUND': (0,), 'SQUARE': (0,), 'FLAT': (0,1),
                   'RHS': (0,1,2), 'L2': (0,1,2)}.get(kind, (0,1,2,3))
        for i, (label, spin) in enumerate(zip(self.rows, self.dimensions)):
            self.field_widgets[i].setVisible(i in visible)
        labels = ['Width', 'Height', 'Web', 'Flange']
        if kind in ('CHS', 'ROUND'):
            labels[0] = 'Diameter'
        if kind in ('CHS', 'RHS', 'SHS'):
            labels[2] = 'Wall thickness'
        elif kind in ('L1', 'L2'):
            labels[2] = 'Thickness'
        elif kind == 'FLAT':
            labels[1] = 'Thickness'
        for label, text in zip(self.rows, labels):
            label.setText(tr(text))
        defaults = CATALOG[kind]['defaults']
        for index in range(1, self.preset.count()):
            if self.preset.itemData(index) == defaults:
                self.preset.setCurrentIndex(index)
                break
        self._preset_changed()

    def _preset_changed(self, *_):
        dims = self.preset.currentData()
        if dims:
            self._loading_dimensions = True
            for spin, value in zip(self.dimensions, dims):
                spin.setValue(value)
            self._loading_dimensions = False

    def _custom_dimensions(self, *_):
        if not self._loading_dimensions:
            self.preset.setCurrentIndex(0)

    def params(self):
        kind = self.family.currentData()
        w,h,tw,tf = [spin.value() for spin in self.dimensions]
        if kind in ('ROUND', 'SQUARE'):
            h = tw = tf = w
        elif kind == 'FLAT':
            tw = tf = h
        elif kind in ('SHS', 'CHS', 'L1'):
            h, tf = w, tw
        elif kind in ('RHS', 'L2'):
            tf = tw
        label = self.preset.currentText() if self.preset.currentData() else (
            f'{kind} {h:g}×{w:g} ({tw:g}/{tf:g})')
        return dict(kind=kind, label=label, dimensions=[w,h,tw,tf],
                    horizontal=self.horizontal.currentIndex(), vertical=self.vertical.currentIndex())

    def accept(self):
        try:
            validate(self.params())
        except ValueError as exc:
            QMessageBox.warning(self, 'Steel Profiles', str(exc))
            return
        super().accept()


def setup(app):
    last = None

    def draw():
        nonlocal last
        if app.scene.edit_group is not None:
            QMessageBox.warning(app.window, 'Steel Profiles', 'Close the group you are editing first.')
            return
        dialog = ProfileDialog(app.window, last)
        if dialog.exec() == QDialog.Accepted:
            last = dialog.params()
            app.viewport.set_active_tool(_DrawProfile(last))

    def edit():
        groups = [g for g in app.scene.selection if isinstance(g, Group)
                  and g.ext and KEY in g.ext]
        if len(groups) != 1:
            QMessageBox.warning(app.window, 'Steel Profiles', 'Select one steel profile to edit.')
            return
        group = groups[0]
        dialog = ProfileDialog(app.window, group.ext[KEY]['params'], editing=True)
        if dialog.exec() == QDialog.Accepted:
            execute(app.viewport, ProfileCommand(group, dialog.params()))

    def pick():
        def sampled(params):
            nonlocal last
            last = copy.deepcopy(params)
            app.viewport.set_active_tool(_DrawProfile(last))
        app.viewport.set_active_tool(profile_picker(sampled))

    menu = app.add_menu('Steel Profiles')
    menu.addAction('Draw steel profile…', draw)
    menu.addAction('Edit selected profile…', edit)
    menu.addAction(tr('Sample steel profile'), pick)

    toolbar = QToolBar(tr('Steel Profiles'), app.window)
    toolbar.setObjectName('aw_steel_profiles_toolbar')
    toolbar.setMovable(True)
    toolbar.setFloatable(True)
    toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
    from views.icons import toolbar_icon_px
    toolbar.setIconSize(QSize(toolbar_icon_px(), toolbar_icon_px()))
    for text, svg, callback in (
        ('Draw steel profile', DRAW_ICON_SVG, draw),
        ('Sample steel profile', PICK_ICON_SVG, pick),
    ):
        action = QAction(svg_icon(svg), tr(text), toolbar)
        action.setToolTip(tr(text))
        action.setStatusTip(tr(text))
        action.triggered.connect(callback)
        toolbar.addAction(action)
    app.window.addToolBar(Qt.TopToolBarArea, toolbar)
    menu.addAction(toolbar.toggleViewAction())

    def context(menu, selection):
        if any(isinstance(g, Group) and g.ext and KEY in g.ext for g in selection):
            menu.addAction('Edit steel profile…', lambda: QTimer.singleShot(0, edit))
    app.add_context_menu(context)


def svg_icon(svg: str) -> QIcon:
    """Reuse AW Tools' original toolbar artwork at Retina resolution."""
    from PySide6.QtCore import QByteArray
    from PySide6.QtSvg import QSvgRenderer
    pixmap = QPixmap(96, 96)
    pixmap.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#f3f7fb'))
    painter.drawRoundedRect(QRectF(2, 2, 92, 92), 10, 10)
    renderer.render(painter, QRectF(6, 6, 84, 84))
    painter.end()
    return QIcon(pixmap)


def profile_picker(sampled):
    """Pick an existing profile and continue drawing with its parameters."""
    class Picker(Tool):
        name = 'Steel Profile Picker'
        uses_snap = False

        def on_activate(self, viewport):
            viewport.flash_status(tr('Click a steel profile to copy its settings.'), 5000)

        def on_deactivate(self, viewport):
            pass

        def on_cancel(self, viewport):
            viewport.set_active_tool(None)

        def on_click(self, ctx):
            group = ctx.viewport.pick_group(ctx.screen.x(), ctx.screen.y())
            if isinstance(group, Group) and group.ext and KEY in group.ext:
                sampled(copy.deepcopy(group.ext[KEY]['params']))
            else:
                ctx.viewport.flash_status(tr('Choose a profile made with Steel Profiles.'), 3000)

    return Picker()


# 19 families / 424 presets from AW Tools; dimensions [width, height, web, flange].
CATALOG = {'IPE': {'defaults': [100.0, 200.0, 5.6, 8.5],
         'presets': [['IPE 80', 46, 80, 3.8, 5.2],
                     ['IPEA 80', 46, 78, 3.3, 4.2],
                     ['IPEAA 80', 46, 78, 3.2, 4.2],
                     ['IPE 100', 55, 100, 4.1, 5.7],
                     ['IPEA 100', 55, 98, 3.6, 4.7],
                     ['IPEAA 100', 55, 97.6, 3.6, 4.5],
                     ['IPE 120', 64, 120, 4.4, 6.3],
                     ['IPEA 120', 64, 117.6, 3.8, 5.1],
                     ['IPEAA 120', 64, 117, 3.8, 4.8],
                     ['IPE 140', 73, 140, 4.7, 6.9],
                     ['IPEA 140', 73, 137.4, 3.8, 5.6],
                     ['IPEAA 140', 73, 136.6, 3.8, 5.2],
                     ['IPE 160', 82, 160, 5, 7.4],
                     ['IPEA 160', 82, 157, 4, 5.9],
                     ['IPEAA 160', 82, 156.4, 4, 5.6],
                     ['IPE 180', 91, 180, 5.3, 8],
                     ['IPEA 180', 91, 177, 4.3, 6.5],
                     ['IPEAA 180', 91, 176.4, 4.3, 6.2],
                     ['IPEO 180', 92, 182, 6, 9],
                     ['IPE 200', 100, 200, 5.6, 8.5],
                     ['IPEA 200', 100, 197, 4.5, 7],
                     ['IPEAA 200', 100, 196.4, 4.5, 6.7],
                     ['IPEO 200', 102, 202, 6.2, 9.5],
                     ['IPE 220', 110, 220, 5.9, 9.2],
                     ['IPEA 220', 110, 217, 5, 7.7],
                     ['IPEAA 220', 110, 216.4, 4.7, 7.4],
                     ['IPEO 220', 112, 222, 6.6, 10.2],
                     ['IPE 240', 120, 240, 6.2, 9.8],
                     ['IPEA 240', 120, 237, 5.2, 8.3],
                     ['IPEAA 240', 120, 236.4, 4.8, 8],
                     ['IPEO 240', 122, 242, 7, 10.8],
                     ['IPE 270', 135, 270, 6.6, 10.2],
                     ['IPEA 270', 135, 267, 5.5, 8.7],
                     ['IPEO 270', 136, 274, 7.5, 12.2],
                     ['IPE 300', 150, 300, 7.1, 10.7],
                     ['IPEA 300', 150, 297, 6.1, 9.2],
                     ['IPEO 300', 152, 304, 8, 12.7],
                     ['IPE 330', 160, 330, 7.5, 11.5],
                     ['IPEA 330', 160, 327, 6.5, 10],
                     ['IPEO 330', 162, 334, 8.5, 13.5],
                     ['IPE 360', 170, 360, 8, 12.7],
                     ['IPEA 360', 170, 357.6, 6.6, 11.5],
                     ['IPEO 360', 172, 364, 9.2, 14.7],
                     ['IPE 400', 180, 400, 8.6, 13.5],
                     ['IPEA 400', 180, 397, 7, 12],
                     ['IPEO 400', 182, 404, 9.7, 15.5],
                     ['IPER 400', 182, 408, 10.6, 17.5],
                     ['IPE 450', 190, 450, 9.4, 14.6],
                     ['IPEA 450', 190, 447, 7.6, 13.1],
                     ['IPEO 450', 192, 456, 11, 17.6],
                     ['IPER 450', 194, 460, 12.4, 19.6],
                     ['IPE 500', 200, 500, 10.2, 16],
                     ['IPEA 500', 200, 497, 8.4, 14.5],
                     ['IPEO 500', 202, 506, 12, 19],
                     ['IPER 500', 204, 514, 14.2, 23],
                     ['IPE 550', 210, 550, 11.1, 17.2],
                     ['IPEA 550', 210, 547, 9, 15.7],
                     ['IPEO 550', 212, 556, 12.7, 20.2],
                     ['IPER 550', 216, 566, 17.1, 25.2],
                     ['IPE 600', 220, 600, 12, 19],
                     ['IPEA 600', 220, 597, 9.8, 17.5],
                     ['IPEO 600', 224, 610, 15, 24],
                     ['IPER 600', 228, 618, 18, 28]]},
 'IPN': {'defaults': [90.0, 200.0, 7.5, 11.3],
         'presets': [['IPN 80', 42, 80, 3.9, 5.9],
                     ['IPN 100', 50, 100, 4.5, 6.8],
                     ['IPN 120', 58, 120, 5.1, 7.7],
                     ['IPN 140', 66, 140, 5.7, 8.6],
                     ['IPN 160', 74, 160, 6.3, 9.5],
                     ['IPN 180', 82, 180, 6.9, 10.4],
                     ['IPN 200', 90, 200, 7.5, 11.3],
                     ['IPN 220', 98, 220, 8.1, 12.2],
                     ['IPN 240', 106, 240, 8.7, 13.1],
                     ['IPN 260', 113, 260, 9.4, 14.1],
                     ['IPN 280', 119, 280, 10.1, 15.2],
                     ['IPN 300', 125, 300, 10.8, 16.2],
                     ['IPN 320', 131, 320, 11.5, 17.3],
                     ['IPN 340', 137, 340, 12.2, 18.3],
                     ['IPN 360', 143, 360, 13.0, 19.5],
                     ['IPN 380', 149, 380, 13.7, 20.5],
                     ['IPN 400', 155, 400, 14.4, 21.6],
                     ['IPN 450', 170, 450, 16.2, 24.3],
                     ['IPN 500', 185, 500, 18.0, 27.0],
                     ['IPN 550', 200, 550, 19.0, 30.0],
                     ['IPN 600', 215, 600, 21.6, 32.4]]},
 'HEA': {'defaults': [200.0, 190.0, 6.5, 10.0],
         'presets': [['HEA 100', 100, 96, 5, 8],
                     ['HEA 120', 120, 114, 5, 8],
                     ['HEA 140', 140, 133, 5.5, 8.5],
                     ['HEA 160', 160, 152, 6, 9],
                     ['HEA 180', 180, 171, 6, 9.5],
                     ['HEA 200', 200, 190, 6.5, 10],
                     ['HEA 220', 220, 210, 7, 11],
                     ['HEA 240', 240, 230, 7.5, 12],
                     ['HEA 260', 260, 250, 7.5, 12.5],
                     ['HEA 280', 280, 270, 8, 13],
                     ['HEA 300', 300, 290, 8.5, 14],
                     ['HEA 320', 300, 310, 9, 15.5],
                     ['HEA 340', 300, 330, 9.5, 16.5],
                     ['HEA 360', 300, 350, 10, 17.5],
                     ['HEA 400', 300, 390, 11, 19],
                     ['HEA 450', 300, 440, 11.5, 21],
                     ['HEA 500', 300, 490, 12, 23],
                     ['HEA 550', 300, 540, 12.5, 24],
                     ['HEA 600', 300, 590, 13, 25]]},
 'HEB': {'defaults': [200.0, 200.0, 9.0, 15.0],
         'presets': [['HEB 100', 100, 100, 6, 10],
                     ['HEB 120', 120, 120, 6.5, 11],
                     ['HEB 140', 140, 140, 7, 12],
                     ['HEB 160', 160, 160, 8, 13],
                     ['HEB 180', 180, 180, 8.5, 14],
                     ['HEB 200', 200, 200, 9, 15],
                     ['HEB 220', 220, 220, 9.5, 16],
                     ['HEB 240', 240, 240, 10, 17],
                     ['HEB 260', 260, 260, 10, 17.5],
                     ['HEB 280', 280, 280, 10.5, 18],
                     ['HEB 300', 300, 300, 11, 19],
                     ['HEB 320', 300, 320, 11.5, 20.5],
                     ['HEB 340', 300, 340, 12, 21.5],
                     ['HEB 360', 300, 360, 12.5, 22.5],
                     ['HEB 400', 300, 400, 13.5, 24],
                     ['HEB 450', 300, 450, 14, 26],
                     ['HEB 500', 300, 500, 14.5, 28],
                     ['HEB 550', 300, 550, 15, 29],
                     ['HEB 600', 300, 600, 15.5, 30]]},
 'HEM': {'defaults': [206.0, 220.0, 15.0, 25.0],
         'presets': [['HEM 100', 106, 120, 12, 20],
                     ['HEM 120', 126, 140, 12.5, 21],
                     ['HEM 140', 146, 160, 13, 22],
                     ['HEM 160', 166, 180, 14, 23],
                     ['HEM 180', 186, 200, 14.5, 24],
                     ['HEM 200', 206, 220, 15, 25],
                     ['HEM 220', 226, 240, 15.5, 26],
                     ['HEM 240', 248, 270, 18, 32],
                     ['HEM 260', 268, 290, 18, 32.5],
                     ['HEM 280', 288, 310, 18.5, 33],
                     ['HEM 600', 305, 620, 21, 40],
                     ['HEM 500', 306, 524, 21, 40],
                     ['HEM 550', 306, 572, 21, 40],
                     ['HEM 400', 307, 432, 21, 40],
                     ['HEM 450', 307, 478, 21, 40],
                     ['HEM 360', 308, 395, 21, 40],
                     ['HEM 320', 309, 359, 21, 40],
                     ['HEM 340', 309, 377, 21, 40],
                     ['HEM 300', 310, 340, 21, 39]]},
 'UPE': {'defaults': [80.0, 200.0, 6.0, 9.0],
         'presets': [['UPE 80', 50, 80, 4, 7],
                     ['UPE 100', 55, 100, 4.5, 7.5],
                     ['UPE 120', 60, 120, 5, 8],
                     ['UPE 140', 65, 140, 5, 9],
                     ['UPE 160', 70, 160, 5.5, 9.5],
                     ['UPE 180', 75, 180, 5.5, 10.5],
                     ['UPE 200', 80, 200, 6, 11],
                     ['UPE 220', 85, 220, 6.5, 12],
                     ['UPE 240', 90, 240, 7, 12.5],
                     ['UPE 270', 95, 270, 7.5, 13.5],
                     ['UPE 300', 100, 300, 9.5, 15],
                     ['UPE 330', 105, 330, 11, 16],
                     ['UPE 360', 110, 360, 12, 17],
                     ['UPE 400', 115, 400, 13.5, 18]]},
 'UPN': {'defaults': [75.0, 200.0, 8.5, 11.5],
         'presets': [['UPN 50', 38, 50, 5, 7],
                     ['UPN 65', 42, 65, 5.5, 7.5],
                     ['UPN 80', 45, 80, 6, 8],
                     ['UPN 100', 50, 100, 6, 8.5],
                     ['UPN 120', 55, 120, 7, 9],
                     ['UPN 140', 60, 140, 7, 10],
                     ['UPN 160', 65, 160, 7.5, 10.5],
                     ['UPN 180', 70, 180, 8, 11],
                     ['UPN 200', 75, 200, 8.5, 11.5],
                     ['UPN 220', 80, 220, 9, 12.5],
                     ['UPN 240', 85, 240, 9.5, 13],
                     ['UPN 260', 90, 260, 10, 14],
                     ['UPN 280', 95, 280, 10, 15],
                     ['UPN 300', 100, 300, 10, 16],
                     ['UPN 320', 100, 320, 14, 17.5],
                     ['UPN 350', 100, 350, 14, 16],
                     ['UPN 380', 102, 380, 13.5, 16],
                     ['UPN 400', 110, 400, 14, 18]]},
 'UNP': {'defaults': [75.0, 200.0, 8.5, 11.5],
         'presets': [['UNP 50', 38, 50, 5, 7],
                     ['UNP 65', 42, 65, 5.5, 7.5],
                     ['UNP 80', 45, 80, 6, 8],
                     ['UNP 100', 50, 100, 6, 8.5],
                     ['UNP 120', 55, 120, 7, 9],
                     ['UNP 140', 60, 140, 7, 10],
                     ['UNP 160', 65, 160, 7.5, 10.5],
                     ['UNP 180', 70, 180, 8, 11],
                     ['UNP 200', 75, 200, 8.5, 11.5],
                     ['UNP 220', 80, 220, 9, 12.5],
                     ['UNP 240', 85, 240, 9.5, 13],
                     ['UNP 260', 90, 260, 10, 14],
                     ['UNP 280', 95, 280, 10, 15],
                     ['UNP 300', 100, 300, 10, 16],
                     ['UNP 320', 100, 320, 14, 17.5],
                     ['UNP 350', 100, 350, 14, 16],
                     ['UNP 380', 102, 380, 13.5, 16],
                     ['UNP 400', 110, 400, 14, 18]]},
 'T': {'defaults': [100.0, 100.0, 8.0, 12.0],
       'presets': [['T 30x30x4', 30, 30, 4, 4],
                   ['T 35x35x4.5', 35, 35, 4.5, 4.5],
                   ['T 40x40x5', 40, 40, 5, 5],
                   ['T 50x50x6', 50, 50, 6, 6],
                   ['T 60x60x7', 60, 60, 7, 7],
                   ['T 70x70x8', 70, 70, 8, 8],
                   ['T 80x80x9', 80, 80, 9, 9],
                   ['T 100x100x11', 100, 100, 11, 11],
                   ['T 120x120x13', 120, 120, 13, 13],
                   ['T 140x140x15', 140, 140, 15, 15]]},
 'L1': {'defaults': [100.0, 100.0, 10.0, 10.0],
        'presets': [['L 20x20x3', 20, 20, 3, 3],
                    ['L 25x25x3', 25, 25, 3, 3],
                    ['L 30x30x3', 30, 30, 3, 3],
                    ['L 30x30x4', 30, 30, 4, 4],
                    ['L 35x35x4', 35, 35, 4, 4],
                    ['L 40x40x4', 40, 40, 4, 4],
                    ['L 40x40x5', 40, 40, 5, 5],
                    ['L 45x45x5', 45, 45, 5, 5],
                    ['L 50x50x5', 50, 50, 5, 5],
                    ['L 50x50x6', 50, 50, 6, 6],
                    ['L 60x60x6', 60, 60, 6, 6],
                    ['L 60x60x8', 60, 60, 8, 8],
                    ['L 70x70x7', 70, 70, 7, 7],
                    ['L 70x70x8', 70, 70, 8, 8],
                    ['L 80x80x8', 80, 80, 8, 8],
                    ['L 80x80x10', 80, 80, 10, 10],
                    ['L 90x90x9', 90, 90, 9, 9],
                    ['L 100x100x10', 100, 100, 10, 10],
                    ['L 100x100x12', 100, 100, 12, 12],
                    ['L 120x120x12', 120, 120, 12, 12],
                    ['L 150x150x15', 150, 150, 15, 15],
                    ['L 200x200x20', 200, 200, 20, 20]]},
 'L2': {'defaults': [100.0, 150.0, 10.0, 10.0],
        'presets': [['L 40x25x4', 25, 40, 4, 4],
                    ['L 50x30x5', 30, 50, 5, 5],
                    ['L 60x40x5', 40, 60, 5, 5],
                    ['L 60x40x6', 40, 60, 6, 6],
                    ['L 80x40x6', 40, 80, 6, 6],
                    ['L 70x50x6', 50, 70, 6, 6],
                    ['L 100x50x8', 50, 100, 8, 8],
                    ['L 80x60x7', 60, 80, 7, 7],
                    ['L 100x65x8', 65, 100, 8, 8],
                    ['L 120x80x10', 80, 120, 10, 10],
                    ['L 150x90x12', 90, 150, 12, 12],
                    ['L 200x100x12', 100, 200, 12, 12]]},
 'Z': {'defaults': [100.0, 200.0, 8.0, 8.0],
       'presets': [['Z 75x40x2', 40, 75, 2, 2],
                   ['Z 100x50x2', 50, 100, 2, 2],
                   ['Z 100x50x3', 50, 100, 3, 3],
                   ['Z 120x50x2.5', 50, 120, 2.5, 2.5],
                   ['Z 140x60x2.5', 60, 140, 2.5, 2.5],
                   ['Z 150x65x3', 65, 150, 3, 3],
                   ['Z 160x65x3', 65, 160, 3, 3],
                   ['Z 180x70x3', 70, 180, 3, 3],
                   ['Z 200x75x3', 75, 200, 3, 3],
                   ['Z 200x75x4', 75, 200, 4, 4],
                   ['Z 250x80x4', 80, 250, 4, 4],
                   ['Z 300x100x5', 100, 300, 5, 5]]},
 'C': {'defaults': [75.0, 200.0, 8.0, 12.0],
       'presets': [['C 75x40x2', 40, 75, 2, 2],
                   ['C 100x50x2', 50, 100, 2, 2],
                   ['C 100x50x3', 50, 100, 3, 3],
                   ['C 120x50x2.5', 50, 120, 2.5, 2.5],
                   ['C 140x60x2.5', 60, 140, 2.5, 2.5],
                   ['C 150x65x3', 65, 150, 3, 3],
                   ['C 160x65x3', 65, 160, 3, 3],
                   ['C 180x70x3', 70, 180, 3, 3],
                   ['C 200x75x3', 75, 200, 3, 3],
                   ['C 200x75x4', 75, 200, 4, 4],
                   ['C 250x80x4', 80, 250, 4, 4],
                   ['C 300x100x5', 100, 300, 5, 5]]},
 'RHS': {'defaults': [100.0, 200.0, 8.0, 8.0],
         'presets': [['RHS 50x30x3', 30, 50, 3, 3],
                     ['RHS 50x30x4', 30, 50, 4, 4],
                     ['RHS 60x40x3', 40, 60, 3, 3],
                     ['RHS 60x40x4', 40, 60, 4, 4],
                     ['RHS 80x40x3', 40, 80, 3, 3],
                     ['RHS 80x40x4', 40, 80, 4, 4],
                     ['RHS 80x40x5', 40, 80, 5, 5],
                     ['RHS 100x50x4', 50, 100, 4, 4],
                     ['RHS 100x50x5', 50, 100, 5, 5],
                     ['RHS 100x50x6.3', 50, 100, 6.3, 6.3],
                     ['RHS 80x60x4', 60, 80, 4, 4],
                     ['RHS 80x60x5', 60, 80, 5, 5],
                     ['RHS 100x60x4', 60, 100, 4, 4],
                     ['RHS 100x60x5', 60, 100, 5, 5],
                     ['RHS 100x60x6.3', 60, 100, 6.3, 6.3],
                     ['RHS 120x60x5', 60, 120, 5, 5],
                     ['RHS 120x60x6.3', 60, 120, 6.3, 6.3],
                     ['RHS 120x80x5', 80, 120, 5, 5],
                     ['RHS 120x80x6.3', 80, 120, 6.3, 6.3],
                     ['RHS 120x80x8', 80, 120, 8, 8],
                     ['RHS 140x80x6.3', 80, 140, 6.3, 6.3],
                     ['RHS 140x80x8', 80, 140, 8, 8],
                     ['RHS 160x80x6.3', 80, 160, 6.3, 6.3],
                     ['RHS 160x80x8', 80, 160, 8, 8],
                     ['RHS 150x100x6.3', 100, 150, 6.3, 6.3],
                     ['RHS 150x100x8', 100, 150, 8, 8],
                     ['RHS 150x100x10', 100, 150, 10, 10],
                     ['RHS 180x100x8', 100, 180, 8, 8],
                     ['RHS 180x100x10', 100, 180, 10, 10],
                     ['RHS 200x100x8', 100, 200, 8, 8],
                     ['RHS 200x100x10', 100, 200, 10, 10],
                     ['RHS 200x100x12.5', 100, 200, 12.5, 12.5],
                     ['RHS 200x120x8', 120, 200, 8, 8],
                     ['RHS 200x120x10', 120, 200, 10, 10],
                     ['RHS 200x120x12.5', 120, 200, 12.5, 12.5],
                     ['RHS 250x150x10', 150, 250, 10, 10],
                     ['RHS 250x150x12.5', 150, 250, 12.5, 12.5],
                     ['RHS 300x200x10', 200, 300, 10, 10],
                     ['RHS 300x200x12.5', 200, 300, 12.5, 12.5],
                     ['RHS 300x200x16', 200, 300, 16, 16],
                     ['RHS 400x200x12.5', 200, 400, 12.5, 12.5],
                     ['RHS 400x200x16', 200, 400, 16, 16]]},
 'SHS': {'defaults': [100.0, 100.0, 8.0, 8.0],
         'presets': [['SHS 30x30x3', 30, 30, 3, 3],
                     ['SHS 40x40x3', 40, 40, 3, 3],
                     ['SHS 40x40x4', 40, 40, 4, 4],
                     ['SHS 50x50x3', 50, 50, 3, 3],
                     ['SHS 50x50x4', 50, 50, 4, 4],
                     ['SHS 50x50x5', 50, 50, 5, 5],
                     ['SHS 60x60x4', 60, 60, 4, 4],
                     ['SHS 60x60x5', 60, 60, 5, 5],
                     ['SHS 70x70x4', 70, 70, 4, 4],
                     ['SHS 70x70x5', 70, 70, 5, 5],
                     ['SHS 80x80x4', 80, 80, 4, 4],
                     ['SHS 80x80x5', 80, 80, 5, 5],
                     ['SHS 80x80x6.3', 80, 80, 6.3, 6.3],
                     ['SHS 90x90x5', 90, 90, 5, 5],
                     ['SHS 90x90x6.3', 90, 90, 6.3, 6.3],
                     ['SHS 100x100x5', 100, 100, 5, 5],
                     ['SHS 100x100x6.3', 100, 100, 6.3, 6.3],
                     ['SHS 100x100x8', 100, 100, 8, 8],
                     ['SHS 120x120x6.3', 120, 120, 6.3, 6.3],
                     ['SHS 120x120x8', 120, 120, 8, 8],
                     ['SHS 140x140x6.3', 140, 140, 6.3, 6.3],
                     ['SHS 140x140x8', 140, 140, 8, 8],
                     ['SHS 140x140x10', 140, 140, 10, 10],
                     ['SHS 150x150x6.3', 150, 150, 6.3, 6.3],
                     ['SHS 150x150x8', 150, 150, 8, 8],
                     ['SHS 150x150x10', 150, 150, 10, 10],
                     ['SHS 160x160x8', 160, 160, 8, 8],
                     ['SHS 160x160x10', 160, 160, 10, 10],
                     ['SHS 180x180x8', 180, 180, 8, 8],
                     ['SHS 180x180x10', 180, 180, 10, 10],
                     ['SHS 200x200x8', 200, 200, 8, 8],
                     ['SHS 200x200x10', 200, 200, 10, 10],
                     ['SHS 200x200x12.5', 200, 200, 12.5, 12.5],
                     ['SHS 250x250x10', 250, 250, 10, 10],
                     ['SHS 250x250x12.5', 250, 250, 12.5, 12.5],
                     ['SHS 300x300x10', 300, 300, 10, 10],
                     ['SHS 300x300x12.5', 300, 300, 12.5, 12.5],
                     ['SHS 300x300x16', 300, 300, 16, 16]]},
 'CHS': {'defaults': [114.3, 114.3, 6.3, 6.3],
         'presets': [['CHS Ø33.7x3.2', 33.7, 33.7, 3.2, 3.2],
                     ['CHS Ø42.4x3.2', 42.4, 42.4, 3.2, 3.2],
                     ['CHS Ø42.4x4', 42.4, 42.4, 4, 4],
                     ['CHS Ø48.3x3.2', 48.3, 48.3, 3.2, 3.2],
                     ['CHS Ø48.3x4', 48.3, 48.3, 4, 4],
                     ['CHS Ø60.3x3.2', 60.3, 60.3, 3.2, 3.2],
                     ['CHS Ø60.3x4', 60.3, 60.3, 4, 4],
                     ['CHS Ø60.3x5', 60.3, 60.3, 5, 5],
                     ['CHS Ø76.1x3.2', 76.1, 76.1, 3.2, 3.2],
                     ['CHS Ø76.1x4', 76.1, 76.1, 4, 4],
                     ['CHS Ø76.1x5', 76.1, 76.1, 5, 5],
                     ['CHS Ø88.9x4', 88.9, 88.9, 4, 4],
                     ['CHS Ø88.9x5', 88.9, 88.9, 5, 5],
                     ['CHS Ø88.9x6.3', 88.9, 88.9, 6.3, 6.3],
                     ['CHS Ø114.3x4', 114.3, 114.3, 4, 4],
                     ['CHS Ø114.3x5', 114.3, 114.3, 5, 5],
                     ['CHS Ø114.3x6.3', 114.3, 114.3, 6.3, 6.3],
                     ['CHS Ø114.3x8', 114.3, 114.3, 8, 8],
                     ['CHS Ø139.7x5', 139.7, 139.7, 5, 5],
                     ['CHS Ø139.7x6.3', 139.7, 139.7, 6.3, 6.3],
                     ['CHS Ø139.7x8', 139.7, 139.7, 8, 8],
                     ['CHS Ø168.3x5', 168.3, 168.3, 5, 5],
                     ['CHS Ø168.3x6.3', 168.3, 168.3, 6.3, 6.3],
                     ['CHS Ø168.3x8', 168.3, 168.3, 8, 8],
                     ['CHS Ø168.3x10', 168.3, 168.3, 10, 10],
                     ['CHS Ø193.7x6.3', 193.7, 193.7, 6.3, 6.3],
                     ['CHS Ø193.7x8', 193.7, 193.7, 8, 8],
                     ['CHS Ø193.7x10', 193.7, 193.7, 10, 10],
                     ['CHS Ø219.1x6.3', 219.1, 219.1, 6.3, 6.3],
                     ['CHS Ø219.1x8', 219.1, 219.1, 8, 8],
                     ['CHS Ø219.1x10', 219.1, 219.1, 10, 10],
                     ['CHS Ø219.1x12.5', 219.1, 219.1, 12.5, 12.5],
                     ['CHS Ø273.0x8', 273.0, 273.0, 8, 8],
                     ['CHS Ø273.0x10', 273.0, 273.0, 10, 10],
                     ['CHS Ø273.0x12.5', 273.0, 273.0, 12.5, 12.5],
                     ['CHS Ø323.9x10', 323.9, 323.9, 10, 10],
                     ['CHS Ø323.9x12.5', 323.9, 323.9, 12.5, 12.5],
                     ['CHS Ø323.9x16', 323.9, 323.9, 16, 16],
                     ['CHS Ø355.6x10', 355.6, 355.6, 10, 10],
                     ['CHS Ø355.6x12.5', 355.6, 355.6, 12.5, 12.5],
                     ['CHS Ø355.6x16', 355.6, 355.6, 16, 16],
                     ['CHS Ø406.4x12.5', 406.4, 406.4, 12.5, 12.5],
                     ['CHS Ø406.4x16', 406.4, 406.4, 16, 16],
                     ['CHS Ø406.4x20', 406.4, 406.4, 20, 20]]},
 'FLAT': {'defaults': [100.0, 10.0, 10.0, 10.0],
          'presets': [['Plat 20x3', 20, 3, 3, 3],
                      ['Plat 25x3', 25, 3, 3, 3],
                      ['Plat 30x3', 30, 3, 3, 3],
                      ['Plat 40x4', 40, 4, 4, 4],
                      ['Plat 50x5', 50, 5, 5, 5],
                      ['Plat 60x6', 60, 6, 6, 6],
                      ['Plat 80x8', 80, 8, 8, 8],
                      ['Plat 100x10', 100, 10, 10, 10],
                      ['Plat 120x10', 120, 10, 10, 10],
                      ['Plat 150x12', 150, 12, 12, 12],
                      ['Plat 200x15', 200, 15, 15, 15],
                      ['Plat 250x20', 250, 20, 20, 20],
                      ['Plat 300x20', 300, 20, 20, 20]]},
 'SQUARE': {'defaults': [50.0, 50.0, 50.0, 50.0],
            'presets': [['Vierkant 6', 6, 6, 6, 6],
                        ['Vierkant 8', 8, 8, 8, 8],
                        ['Vierkant 10', 10, 10, 10, 10],
                        ['Vierkant 12', 12, 12, 12, 12],
                        ['Vierkant 15', 15, 15, 15, 15],
                        ['Vierkant 16', 16, 16, 16, 16],
                        ['Vierkant 20', 20, 20, 20, 20],
                        ['Vierkant 25', 25, 25, 25, 25],
                        ['Vierkant 30', 30, 30, 30, 30],
                        ['Vierkant 40', 40, 40, 40, 40],
                        ['Vierkant 50', 50, 50, 50, 50],
                        ['Vierkant 60', 60, 60, 60, 60],
                        ['Vierkant 80', 80, 80, 80, 80],
                        ['Vierkant 100', 100, 100, 100, 100]]},
 'ROUND': {'defaults': [50.0, 50.0, 50.0, 50.0],
           'presets': [['Rond Ø6', 6, 6, 6, 6],
                       ['Rond Ø8', 8, 8, 8, 8],
                       ['Rond Ø10', 10, 10, 10, 10],
                       ['Rond Ø12', 12, 12, 12, 12],
                       ['Rond Ø15', 15, 15, 15, 15],
                       ['Rond Ø16', 16, 16, 16, 16],
                       ['Rond Ø20', 20, 20, 20, 20],
                       ['Rond Ø25', 25, 25, 25, 25],
                       ['Rond Ø30', 30, 30, 30, 30],
                       ['Rond Ø40', 40, 40, 40, 40],
                       ['Rond Ø50', 50, 50, 50, 50],
                       ['Rond Ø60', 60, 60, 60, 60],
                       ['Rond Ø80', 80, 80, 80, 80],
                       ['Rond Ø100', 100, 100, 100, 100]]}}


# Original AW Tools toolbar artwork.
DRAW_ICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">\n  <path\n    d="M4 3.5h24v5h-9v15h9v5H4v-5h9v-15H4z"\n    fill="#83abc7"\n    stroke="#173f5e"\n    stroke-width="1.6"\n    stroke-linejoin="round"\n  />\n</svg>\n'
PICK_ICON_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">\n  <path d="M2 3h19v4h-7v18h7v4H2v-4h7V7H2z" fill="#83abc7" stroke="#173f5e" stroke-width="1.4" stroke-linejoin="round"/>\n  <circle cx="12" cy="27" r="3.2" fill="#f0aa32" stroke="#fff" stroke-width="2"/>\n  <g fill="#fff">\n    <rect x="19" y="0" width="12" height="16" rx="6" transform="rotate(-45 25 8)"/>\n    <rect x="17.5" y="5" width="10" height="12" rx="4" transform="rotate(-45 22.5 11)"/>\n  </g>\n  <path d="M21 11L13 26M24 14L15 28" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round"/>\n  <g fill="#173f5e">\n    <rect x="20" y="1" width="10" height="14" rx="5" transform="rotate(-45 25 8)"/>\n    <rect x="18.5" y="6" width="8" height="10" rx="3" transform="rotate(-45 22.5 11)"/>\n  </g>\n  <path d="M21 11L13 26M24 14L15 28" fill="none" stroke="#173f5e" stroke-width="3" stroke-linecap="round"/>\n  <circle cx="12" cy="27" r="3.2" fill="#f0aa32" stroke="#9b6411" stroke-width=".8"/>\n</svg>\n'
