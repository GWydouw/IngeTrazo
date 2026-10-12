"""Selection outlines include geometry, retain transforms and scale with DPI."""
from array import array
from types import SimpleNamespace

import pytest
from PySide6.QtGui import QMatrix4x4, QVector3D as V

from core.group import Group
from core.mesh import Mesh
from tests.test_edit_inside_group_draws import _uploaded_edges
from views.viewport import Viewport


def _sync_selection(vp):
    _uploaded_edges(vp)
    return vp._selected_count


def test_selected_face_includes_outer_and_hole_boundaries():
    vp = Viewport(None)
    face = vp.scene.mesh.add_face(
        [V(0, 0, 0), V(4, 0, 0), V(4, 4, 0), V(0, 4, 0)],
        [[V(1, 1, 0), V(1, 2, 0), V(2, 2, 0), V(2, 1, 0)]])
    vp.scene.selection.add(face)
    vp.scene.version += 1
    assert _sync_selection(vp) == 16  # eight segments, not just the face dots


def test_selected_container_includes_transformed_child_edges_but_not_hidden_children():
    vp = Viewport(None)
    mesh = Mesh()
    mesh.add_edge(V(0, 0, 0), V(1, 1, 1))
    child = Group(mesh)
    child.xform = QMatrix4x4()
    child.xform.translate(10, 20, 30)
    hidden = Group(mesh)
    hidden.hidden = True
    root = Group(Mesh())
    root.children = [child, hidden]
    vp.scene.groups.append(root)
    vp.scene.selection.add(root)
    vp.scene.version += 1
    assert _sync_selection(vp) == 26  # box + one visible geometric segment
    # Capture the actual upload, verifying the world-space endpoints as well.
    sent = {}
    def upload(_vbo, slot, parts, empty=24):
        data = b''.join(parts)
        sent[slot] = data
        return len(data)
    vp._upload_vbo = upload
    vp.scene.version += 1
    vp._sync_edges()
    coords = array('f')
    coords.frombytes(sent['sel_edges'])
    assert list(coords[-6:]) == [10, 20, 30, 11, 21, 31]


@pytest.mark.parametrize('dpr', [1.0, 2.0])
def test_thick_selection_restores_matrix_and_depth_state(dpr):
    draws, masks, matrices = [], [], []
    gl = SimpleNamespace(glDrawArrays=lambda *args: draws.append(args),
                         glDepthMask=masks.append)
    vao = SimpleNamespace(bind=lambda: None, release=lambda: None)
    vp = SimpleNamespace(_fb_size=lambda: (int(800*dpr), int(600*dpr)),
                         devicePixelRatioF=lambda: dpr, _gl=gl,
                         _set_color=lambda *args: None, _loc_mvp=7,
                         _program=SimpleNamespace(setUniformValue=lambda _, m: matrices.append(m)))
    mvp = QMatrix4x4()
    Viewport._draw_selection_lines(vp, vao, 24, mvp)
    assert len(draws) == (5 if dpr == 1 else 24)
    assert all(count == 24 for _, _, count in draws)
    assert matrices[-1] == mvp
    assert masks == [False, True]
    extent = max(abs(m.column(3).x()) for m in matrices)
    assert extent == pytest.approx((3*dpr - 1)/(800*dpr))
