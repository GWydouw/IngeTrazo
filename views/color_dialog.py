# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""The colour picker every panel opens: Qt's own dialog, not the desktop's.

On GNOME the native picker is GTK's small palette, and opened from a
right-click menu it came back without the colour chosen — editing a
material's colour did nothing (Marco, testing 0.5.7). Qt's dialog is the
same on Linux, Windows and macOS: a colour wheel, RGB, HSV, a hex field
and custom colours."""
from __future__ import annotations

from core.i18n import tr
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QColorDialog, QHBoxLayout, QLabel, QWidget


def get_color(*args, **kwargs):
    """``QColorDialog.getColor`` with Qt's own dialog."""
    checker_preview = kwargs.pop("checker_preview", False)
    if checker_preview:
        initial = args[0]
        dialog = QColorDialog(initial, args[1] if len(args) > 1 else None)
        if len(args) > 2:
            dialog.setWindowTitle(args[2])
        dialog.setOptions(QColorDialog.ColorDialogOption.DontUseNativeDialog
                          | QColorDialog.ColorDialogOption.ShowAlphaChannel)
        preview = _ColorPreview(initial, dialog)
        dialog.currentColorChanged.connect(preview.set_color)
        preview_row = QWidget(dialog)
        preview_layout = QHBoxLayout(preview_row)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.addWidget(QLabel(tr("Preview"), preview_row))
        preview_layout.addWidget(preview, 1)
        dialog.layout().insertWidget(dialog.layout().count() - 1, preview_row)
        if dialog.exec() == QColorDialog.Accepted:
            return dialog.selectedColor()
        return QColor()
    kwargs.setdefault("options",
                      QColorDialog.ColorDialogOption.DontUseNativeDialog)
    return QColorDialog.getColor(*args, **kwargs)


def paint_color_swatch(painter, rect, color, tile=4):
    """Composite translucent color over a neutral checkerboard."""
    rect = QRectF(rect)
    painter.save()
    clip = QPainterPath()
    clip.addRoundedRect(rect, 2, 2)
    painter.setClipPath(clip)
    if color.alpha() < 255:
        for row, y in enumerate(range(int(rect.top()), int(rect.bottom()) + 1, tile)):
            for column, x in enumerate(range(int(rect.left()), int(rect.right()) + 1, tile)):
                painter.fillRect(QRectF(x, y, tile, tile),
                                 QColor("#eeeeee" if (row + column) % 2 else "#aaaaaa"))
    painter.fillRect(rect, color)
    painter.restore()


class _ColorPreview(QWidget):
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setMinimumHeight(36)

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        paint_color_swatch(painter, self.rect().adjusted(0, 2, 0, -2), self._color, tile=8)
