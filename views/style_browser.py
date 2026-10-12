# SPDX-License-Identifier: GPL-3.0-or-later
"""Collection browser for model-owned and reusable styles."""
from pathlib import Path
from PySide6.QtCore import Qt, QSize, Signal, QMimeData
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QToolButton,QComboBox,
    QListWidget,QListWidgetItem,QMenu,QFileDialog,QStyle,QMessageBox)
from core.style import BUILTIN_STYLES,user_styles
from core.paths import app_root
from core.style_library import (model_styles,collections,remember_collection,read_collection,
                                write_collection_style,store_model_style)


STYLE_MIME = 'application/x-ingetrazo-style'


class _StyleList(QListWidget):
    def mimeData(self, items):
        import json
        mime = QMimeData()
        for item in items:
            kind, data = item.data(Qt.UserRole)
            if kind == 'style':
                mime.setData(STYLE_MIME, json.dumps(data).encode('utf-8'))
                break
        return mime

    def supportedDropActions(self):
        return Qt.CopyAction


class StyleBrowser(QWidget):
    styleSelected = Signal(object)
    modelChanged = Signal()

    def __init__(self, scene, thumbnail, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.thumbnail = thumbnail
        self.location = 'home'
        self.history = ['home']
        self.history_index = 0
        self.view_mode = 'large'
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        row = QHBoxLayout()
        self.back = self._button(row,'previous_arrow','Back',lambda:self.navigate(-1))
        self.forward = self._button(row,'next_arrow','Forward',lambda:self.navigate(1))
        self.in_model = self._button(row,'dlg_in_model','In Model',lambda:self.open('model'))
        self.collection = QComboBox()
        self.collection.activated.connect(lambda index:self.open(self.collection.itemData(index)))
        row.addWidget(self.collection,1)
        self._button(row,'dlg_flyout_menu','Collection options',self.options)
        layout.addLayout(row)
        self.items = _StyleList()
        self.items.setDragEnabled(True)
        self.items.setResizeMode(QListWidget.Adjust)
        self.items.itemClicked.connect(self.choose)
        self.items.setContextMenuPolicy(Qt.CustomContextMenu)
        self.items.customContextMenuRequested.connect(self.style_options)
        layout.addWidget(self.items,1)
        self.refresh()

    def _button(self,row,icon,tip,callback):
        button=QToolButton()
        button.setIcon(QIcon(str(app_root() / 'resources' / 'icons' / (icon + '.png'))))
        button.setIconSize(QSize(24,24))
        button.setAutoRaise(True)
        button.setFixedSize(28,28)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.clicked.connect(callback);row.addWidget(button)
        return button

    def locations(self):
        return [('Styles','home'),('In Model','model'),('Default Styles','defaults'),('My Styles','personal')] + [
            (Path(path).name,'dir:'+path) for path in collections()]

    def open(self,location,record=True):
        if not location:return
        self.location=location
        if record and self.history[self.history_index]!=location:
            self.history=self.history[:self.history_index+1]+[location]
            self.history_index+=1
        self.refresh()

    def navigate(self,delta):
        index=self.history_index+delta
        if 0<=index<len(self.history):
            self.history_index=index
            self.open(self.history[index],False)

    def shown_styles(self):
        if self.location=='model':return model_styles(self.scene)
        if self.location=='defaults':
            styles=[style.copy() for style in BUILTIN_STYLES]
            for style in styles:style.uid='builtin:'+style.name
            return styles
        if self.location=='personal':return user_styles()
        if self.location.startswith('dir:'):return read_collection(self.location[4:])
        return []

    def refresh(self):
        selected=self.items.currentRow()
        self.collection.blockSignals(True)
        self.collection.clear()
        locations=self.locations()
        if self.location.startswith('dir:') and self.location not in [key for _,key in locations]:
            locations.append((Path(self.location[4:]).name,self.location))
        for label,key in locations:self.collection.addItem(label,key)
        self.collection.setCurrentIndex(self.collection.findData(self.location))
        self.collection.blockSignals(False)
        self.back.setEnabled(self.history_index>0)
        self.forward.setEnabled(self.history_index<len(self.history)-1)
        self.items.clear()
        if self.view_mode=='list':
            self.items.setViewMode(QListWidget.ListMode);self.items.setIconSize(QSize(32,32));self.items.setGridSize(QSize())
        else:
            pixels=64 if self.view_mode=='small' else 96
            self.items.setViewMode(QListWidget.IconMode);self.items.setIconSize(QSize(pixels,pixels))
            self.items.setGridSize(QSize(pixels+18,pixels+36))
        if self.location=='home':
            for label,key in locations[1:]:
                item=QListWidgetItem(QIcon(str(app_root() / 'resources/icons/style_collection.svg')),label)
                item.setData(Qt.UserRole,('collection',key));self.items.addItem(item)
        else:
            active=self.scene.display_style
            for style in self.shown_styles():
                item=QListWidgetItem(QIcon(self.thumbnail(style,96)),style.name)
                item.setToolTip(style.description or style.name)
                item.setData(Qt.UserRole,('style',style.to_dict()));self.items.addItem(item)
                if style.uid and style.uid==active.uid or not style.uid and style.name==active.name:
                    item.setSelected(True)
        if 0<=selected<self.items.count():self.items.setCurrentRow(selected)

    def choose(self,item):
        kind,data=item.data(Qt.UserRole)
        if kind=='collection':self.open(data)
        else:
            from core.style import Style
            self.styleSelected.emit(Style.from_dict(data))

    def options(self):
        menu=QMenu(self)
        menu.addAction('Open or create a collection…',self.open_directory)
        menu.addAction('Add collection to favorites…',lambda:remember_collection(self.location[4:]) if self.location.startswith('dir:') else self.open_directory())
        remove=menu.addAction('Remove collection from favorites…',self.remove_favorite)
        remove.setEnabled(self.location.startswith('dir:'))
        import_action=menu.addAction('Import to model library…',self.import_collection)
        import_action.setEnabled(self.location not in ('home','model'))
        menu.addAction('Save current style to collection…',self.save_to_collection)
        menu.addSeparator()
        for label,key in [('Small Thumbnails','small'),('Large Thumbnails','large'),('List View','list')]:
            action=menu.addAction(label);action.setCheckable(True);action.setChecked(self.view_mode==key)
            action.triggered.connect(lambda checked=False,k=key:self.set_view(k))
        menu.addSeparator();menu.addAction('Refresh',self.refresh)
        menu.exec(self.mapToGlobal(self.rect().topRight()))

    def set_view(self,mode):self.view_mode=mode;self.refresh()

    def open_directory(self):
        path=QFileDialog.getExistingDirectory(self,'Open or create a collection','',QFileDialog.ShowDirsOnly)
        if path:remember_collection(path);self.open('dir:'+str(Path(path).resolve()))

    def remove_favorite(self):
        if self.location.startswith('dir:'):
            remember_collection(self.location[4:],False);self.open('home')

    def import_collection(self):
        for style in self.shown_styles():store_model_style(self.scene,style)
        self.open('model');self.modelChanged.emit()

    def save_to_collection(self):
        path=self.location[4:] if self.location.startswith('dir:') else QFileDialog.getExistingDirectory(self,'Save style to collection')
        if not path:return
        try:
            write_collection_style(path,self.scene.display_style)
            remember_collection(path)
        except OSError as error:
            QMessageBox.warning(self,'Save style',str(error));return
        self.open('dir:'+str(Path(path).resolve()))
        self.modelChanged.emit()

    def style_options(self,position):
        item=self.items.itemAt(position)
        if item is None or item.data(Qt.UserRole)[0]!='style':return
        menu=QMenu(self)
        menu.addAction('Apply style',lambda:self.choose(item))
        menu.addAction('Save current style to collection…',self.save_to_collection)
        menu.exec(self.items.mapToGlobal(position))
