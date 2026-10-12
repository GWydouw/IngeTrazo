# SPDX-License-Identifier: GPL-3.0-or-later
"""Compact colour selector using the same chip as the Tags and Clipboxes panels."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget,QTableWidgetItem,QFrame


class ColorSelector(QTableWidget):
    clicked = Signal()

    def __init__(self,parent=None):
        super().__init__(1,1,parent)
        from views.tray import _LayerColorDelegate
        self.setItemDelegate(_LayerColorDelegate(self))
        self.setItem(0,0,QTableWidgetItem())
        self.item(0,0).setTextAlignment(Qt.AlignCenter)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.horizontalHeader().setMinimumSectionSize(0)
        self.verticalHeader().setMinimumSectionSize(0)
        self.setFrameShape(QFrame.NoFrame)
        self.setShowGrid(False)
        self.setSelectionMode(QTableWidget.NoSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet('QTableWidget { background: transparent; border: none; } '
                          'QTableWidget::item { background: transparent; border: none; padding: 0; }')
        self.setFixedSize(28,28)
        self.viewport().setAutoFillBackground(False)
        self.cellClicked.connect(lambda *_:self.clicked.emit())

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.setColumnWidth(0,self.viewport().width())
        self.setRowHeight(0,self.viewport().height())

    def color(self):
        return self.item(0,0).data(Qt.UserRole+2)

    def set_color(self,color):
        self.item(0,0).setData(Qt.UserRole+2,QColor(color) if color is not None else None)

    def text(self):
        return self.item(0,0).text()

    def setText(self,text):
        self.item(0,0).setText(text)
