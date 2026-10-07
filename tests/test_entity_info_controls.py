"""Selection facts and the visibility control use the same model/history."""
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QVector3D
from PySide6.QtWidgets import QApplication

from core.history import History
from core.scene import Scene
from views.tray import EntityInfoPanel

_app = QApplication.instance() or QApplication([])


def panel_for(scene):
    viewport = SimpleNamespace(scene=scene, history=History(scene), update=lambda: None)
    window = SimpleNamespace(viewport=viewport)
    return EntityInfoPanel(window), viewport


def test_face_fields_clear_when_selection_clears():
    scene = Scene()
    face = scene.mesh.add_face([QVector3D(0, 0, 0), QVector3D(2, 0, 0),
                               QVector3D(2, 2, 0), QVector3D(0, 2, 0)])
    scene.select([face])
    panel, _ = panel_for(scene)
    assert panel._label.text() == "Face"
    assert panel._facts[0][1].text() == "4.000 m²"
    assert panel._visible.isEnabled() and panel._visible.isChecked()
    scene.clear_selection()
    panel.refresh()
    assert all(value.text() == "" for _, value in panel._facts)
    assert not panel._visible.isEnabled()
    panel.close()


def test_hide_mixed_selection_is_one_undo_step():
    scene = Scene()
    face = scene.mesh.add_face([QVector3D(0, 0, 0), QVector3D(1, 0, 0),
                               QVector3D(1, 1, 0)])
    edge = next(iter(scene.mesh.edges))
    scene.select([face, edge])
    panel, viewport = panel_for(scene)
    panel._visible.click()
    assert face.attrs.get("hidden") and edge.hidden
    assert not scene.selection
    assert viewport.history.undo()
    assert not face.attrs.get("hidden") and not edge.hidden
    panel.close()
