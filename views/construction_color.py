# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared construction guide colour control."""
from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog


from views.color_selector import ColorSelector


class ConstructionColorControl(ColorSelector):
    colorChanged = Signal(QColor)

    def __init__(self,color,parent=None):
        super().__init__(parent)
        self.set_color(color)
        self.setToolTip("Click to choose the construction line color.")
        self.clicked.connect(self.choose_color)

    def choose_color(self, *_):
        color = QColorDialog.getColor(self.color(), self, "Construction line color")
        if color.isValid():
            self.set_color(color)
            self.colorChanged.emit(color)
