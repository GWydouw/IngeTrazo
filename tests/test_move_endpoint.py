# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 IngeTrazo contributors.
"""Move a loose endpoint as a deformation handle, preserving selected moves."""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QVector3D
import pytest

from core.group import Group
from core.history import History
from core.mesh import Mesh
from core.scene import Scene
from core.snap import SnapResult
from tools.base import ToolContext
from tools.move import MoveTool, gather_targets


def V(x, y, z=0):
    return QVector3D(float(x), float(y), float(z))


class Viewport:
    def __init__(self):
        self.scene = Scene()
        self.history = History(self.scene)
        self.face = self.scene.mesh.add_face([V(0, 0), V(2, 0), V(2, 2), V(0, 2)])
        self.edge = self.scene.mesh.edges[0]
        self.group = None

    def pick_group(self, x, y):
        return self.group

    def pick_edge(self, x, y):
        return self.edge

    def pick_face(self, x, y):
        return self.face

    def update(self):
        pass

    def flash_status(self, *args, **kwargs):
        pass


def ctx(vp, point, kind=None, context=None):
    snap = SnapResult(point, kind, context=context) if kind else None
    return ToolContext(viewport=vp, world=point, screen=QPointF(0, 0),
                       modifiers=Qt.NoModifier, snap=snap)


def test_endpoint_deforms_shared_geometry_and_undo_redo():
    vp = Viewport()
    other = vp.scene.mesh.add_edge(V(0, 0), V(-1, 0))
    tool = MoveTool()
    tool.on_click(ctx(vp, V(0, 0), "endpoint"))
    tool.on_hover(ctx(vp, V(0, 0, 1)))
    assert vp.edge.a == V(0, 0, 1)
    assert vp.edge.b == V(2, 0)
    assert vp.face.vertices[0] == V(0, 0, 1)
    assert other.a == V(0, 0, 1)
    assert other.b == V(-1, 0)
    assert not vp.history.undo_stack
    tool.on_click(ctx(vp, V(0, 0, 1)))
    vp.history.undo()
    assert vp.edge.a == V(0, 0)
    assert vp.edge.b == V(2, 0)
    vp.history.redo()
    assert vp.edge.a == V(0, 0, 1)
    assert vp.edge.b == V(2, 0)


def test_endpoint_cancel_restores_geometry():
    vp = Viewport()
    tool = MoveTool()
    tool.on_click(ctx(vp, V(0, 0), "endpoint"))
    tool.on_hover(ctx(vp, V(0, 0, 1)))
    tool.on_cancel(vp)
    assert vp.edge.a == V(0, 0)
    assert vp.edge.b == V(2, 0)
    assert not vp.history.undo_stack


@pytest.mark.parametrize("entity", ["edge", "face"])
def test_explicit_selection_moves_whole_entity_at_endpoint(entity):
    vp = Viewport()
    selected = getattr(vp, entity)
    vp.scene.selection = [selected]
    tool = MoveTool()
    tool.on_click(ctx(vp, V(0, 0), "endpoint"))
    tool.on_click(ctx(vp, V(0, 0, 1)))
    assert vp.edge.a == V(0, 0, 1)
    assert vp.edge.b == V(2, 0, 1)


@pytest.mark.parametrize("kind,context", [(None, None), ("midpoint", None),
                                           ("endpoint", "component")])
def test_non_loose_endpoint_keeps_whole_edge_target(kind, context):
    vp = Viewport()
    tool = MoveTool()
    tool.on_click(ctx(vp, V(0, 0), kind, context))
    tool.on_click(ctx(vp, V(0, 0, 1)))
    assert vp.edge.a == V(0, 0, 1)
    assert vp.edge.b == V(2, 0, 1)


def test_endpoint_snap_outside_active_mesh_does_not_create_vertex():
    vp = Viewport()
    original = len(vp.scene.mesh.vertices)
    groups, positions = MoveTool()._gather(ctx(vp, V(10, 10), "endpoint"))
    assert not groups
    assert positions == [V(0, 0), V(2, 0)]
    assert len(vp.scene.mesh.vertices) == original


def test_hovered_group_has_priority_over_endpoint():
    vp = Viewport()
    vp.group = Group(Mesh())
    groups, positions = MoveTool()._gather(ctx(vp, V(0, 0), "endpoint"))
    assert groups == [vp.group]
    assert not positions


def test_other_transform_tools_keep_whole_edge_target():
    vp = Viewport()
    groups, positions = gather_targets(ctx(vp, V(0, 0), "endpoint"))
    assert not groups
    assert positions == [V(0, 0), V(2, 0)]
