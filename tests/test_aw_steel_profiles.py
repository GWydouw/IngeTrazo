"""AW Tools port: closed solids, persistent parameters and atomic undo."""
import copy
import math

import pytest
from PySide6.QtGui import QVector3D

from core.extensions import discover_plugins
from core.history import History
from core.scene import Scene
from formats.igz import load_into, save_scene
from plugins.aw_steel_profiles import (
    CATALOG, KEY, ProfileCommand, ProfileDialog, _DrawProfile, make_profile,
    profile_mesh, section_rings, validate,
)
from plugins.solid_inspector import inspect_mesh


def params(kind='IPE', dimensions=None):
    return dict(kind=kind, label=kind, dimensions=dimensions or CATALOG[kind]['defaults'],
                horizontal=1, vertical=1)


@pytest.mark.parametrize('kind', list(CATALOG))
def test_every_original_preset_is_a_closed_solid(kind):
    for label, *dimensions in CATALOG[kind]['presets']:
        p = params(kind, dimensions)
        mesh = profile_mesh(p, 2)
        report = inspect_mesh(mesh)
        assert report['watertight'], label
        assert report['volume'] > 0, label
        assert all(face.triangulate() for face in mesh.faces)


@pytest.mark.parametrize('kind,dimensions,area', [
    ('IPE', [100,200,5.6,8.5], (2*100*8.5 + 5.6*(200-17))/1e6),
    ('RHS', [100,200,8,8], (100*200-84*184)/1e6),
    ('CHS', [100,100,5,5], 16*math.sin(math.tau/32)*(.05**2-.045**2)),
])
def test_section_volume_preserves_voids(kind, dimensions, area):
    mesh = profile_mesh(params(kind, dimensions), 3)
    assert inspect_mesh(mesh)['volume'] == pytest.approx(area*3, rel=1e-5)


def test_creation_edit_undo_redo_and_save_after_move(tmp_path):
    scene = Scene()
    hist = History(scene)
    group = make_profile(params(), QVector3D(1,2,3), QVector3D(4,6,8))
    hist.execute(ProfileCommand(group))
    assert scene.groups == [group]
    assert scene.version > 0
    hist.undo()
    assert not scene.groups
    hist.redo()
    group.xform.translate(0,0,2)
    placement = copy.copy(group.xform)
    before = group.mesh
    hist.execute(ProfileCommand(group, params('RHS')))
    after = group.mesh
    assert after is not before
    assert group.xform == placement
    hist.undo()
    assert group.mesh is before and group.ext[KEY]['params']['kind'] == 'IPE'
    hist.redo()
    assert group.mesh is after
    path = tmp_path/'steel.igz'
    save_scene(scene, path)
    restored = Scene()
    load_into(restored, path)
    assert restored.groups[0].ext == group.ext
    assert restored.groups[0].xform == placement
    assert inspect_mesh(restored.groups[0].mesh)['watertight']


def test_alignment_and_vertical_placement():
    p = params('RHS')
    p.update(horizontal=0, vertical=0)
    ring = section_rings(p)[0]
    assert min(x for x,y in ring) == min(y for x,y in ring) == 0
    g = make_profile(p, QVector3D(1,2,3), QVector3D(1,2,6))
    assert g.xform.map(QVector3D(0,0,3)) == QVector3D(1,2,6)


def test_dialog_family_switch_and_normalization():
    dialog = ProfileDialog(None)
    dialog.preset.setCurrentIndex(1)
    assert dialog.preset.currentData() is not None
    dialog.dimensions[0].setValue(99)
    assert dialog.preset.currentData() is None
    dialog.family.setCurrentText('CHS')
    assert dialog.dimensions[0].isEnabled()
    dialog.dimensions[0].setValue(100)
    dialog.dimensions[2].setValue(5)
    assert dialog.params()['dimensions'] == [100,100,5,5]
    validate(dialog.params())


def test_graphical_alignment_changes_the_saved_anchor():
    dialog = ProfileDialog(None)
    from PySide6.QtTest import QTest
    from PySide6.QtCore import Qt
    dialog.show()
    for horizontal, vertical in ((0, 2), (2, 0), (1, 1)):
        QTest.mouseClick(dialog.alignment.buttons.button(vertical*3+horizontal), Qt.LeftButton)
        assert dialog.params()['horizontal'] == horizontal
        assert dialog.params()['vertical'] == vertical
    dialog.close()


def test_bad_dimensions_and_zero_length_are_refused():
    with pytest.raises(ValueError):
        profile_mesh(params('RHS', [100,200,50,50]), 2)
    with pytest.raises(ValueError):
        make_profile(params(), QVector3D(), QVector3D())


def test_discovery_has_setup_without_internal_drawing_tool():
    from pathlib import Path
    plugins, errors = discover_plugins([Path(__file__).resolve().parents[1]/'plugins'])
    aw = next(p for p in plugins if p.stem == KEY)
    assert aw.setup and not aw.tools
    assert not any(e.stem == KEY for e in errors)


def test_preview_maps_edges_to_world():
    tool = _DrawProfile(params())
    tool.start_point, tool.hover_point = QVector3D(1,2,3), QVector3D(4,2,3)
    assert len(tool.rubber_band_lines()) > 12


def test_toolbar_has_original_icons_and_picker_samples_settings():
    from types import SimpleNamespace
    from PySide6.QtCore import QPointF
    from PySide6.QtWidgets import QMainWindow, QMenu, QToolBar
    from plugins.aw_steel_profiles import setup

    group = make_profile(params('RHS'), QVector3D(), QVector3D(3, 0, 0))
    activated = []
    viewport = SimpleNamespace(
        set_active_tool=activated.append, flash_status=lambda *args: None,
        pick_group=lambda *args: group,
    )
    window = QMainWindow()
    app = SimpleNamespace(
        window=window, viewport=viewport, scene=Scene(),
        add_menu=lambda text: QMenu(text, window), add_context_menu=lambda fn: None,
    )
    setup(app)
    toolbar = window.findChild(QToolBar, 'aw_steel_profiles_toolbar')
    assert toolbar is not None and len(toolbar.actions()) == 2
    assert all(not action.icon().isNull() for action in toolbar.actions())
    toolbar.actions()[1].trigger()
    picker = activated[-1]
    picker.on_click(SimpleNamespace(viewport=viewport, screen=QPointF(10, 10)))
    assert activated[-1].params == group.ext[KEY]['params']
    assert activated[-1].params is not group.ext[KEY]['params']
    window.close()
