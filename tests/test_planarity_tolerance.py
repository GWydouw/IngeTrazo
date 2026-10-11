# SPDX-License-Identifier: GPL-3.0-or-later
"""Sub-millimetre warps must not survive as a single planar polygon."""
import pytest
from PySide6.QtGui import QVector3D

from core.history import History, MoveVerticesCommand
from core.mesh import Mesh
from core.scene import Scene
from core.topology import fold_nonplanar_faces, is_planar


@pytest.mark.parametrize('axis', [0, 1, 2])
@pytest.mark.parametrize('offset, expected', [(0.0127e-3, True), (0.0508e-3, False), (0.8e-3, False)])
def test_planarity_boundary_in_metres(axis, offset, expected):
    def point(u, v, height=0):
        coordinates = [0, 0, 0]
        coordinates[axis] = height
        coordinates[(axis + 1) % 3] = u
        coordinates[(axis + 2) % 3] = v
        return QVector3D(*coordinates)
    points = [point(0, 0), point(2, 0), point(2, 2), point(0, 2, offset)]
    assert is_planar(points) is expected


def test_submillimetre_corner_move_keeps_fold_material_and_undo_redo():
    scene = Scene()
    history = History(scene)
    points = [QVector3D(0, 0, 0), QVector3D(2, 0, 0), QVector3D(2, 2, 0), QVector3D(0, 2, 0)]
    face = scene.mesh.add_face(points)
    face.attrs = {'color': [0.2, 0.3, 0.4], 'back': {'color': [0.5, 0.6, 0.7]}}
    history.execute(MoveVerticesCommand([points[-1]], QVector3D(0, 0, 0.8e-3)))
    assert len(scene.mesh.faces) == 2
    assert all(is_planar(list(piece.vertices)) for piece in scene.mesh.faces)
    assert all(piece.attrs == face.attrs for piece in scene.mesh.faces)
    assert len([edge for edge in scene.mesh.edges if len(edge.faces) == 2]) == 1
    expected = {tuple(p.toTuple()) for p in points[:-1]} | {tuple(QVector3D(0, 2, 0.8e-3).toTuple())}
    assert {tuple(p.toTuple()) for piece in scene.mesh.faces for p in piece.vertices} == expected
    assert history.undo()
    assert len(scene.mesh.faces) == 1
    assert {tuple(p.toTuple()) for p in scene.mesh.faces[0].vertices} == {tuple(p.toTuple()) for p in points}
    assert history.redo()
    assert len(scene.mesh.faces) == 2
    assert all(is_planar(list(piece.vertices)) for piece in scene.mesh.faces)


def test_explicit_planarity_tolerance_still_controls_folding():
    mesh = Mesh()
    face = mesh.add_face([QVector3D(0, 0, 0), QVector3D(2, 0, 0), QVector3D(2, 2, 0), QVector3D(0, 2, 0.8e-3)])
    assert is_planar(list(face.vertices), tolerance=1e-3)
    assert fold_nonplanar_faces(mesh, tolerance=1e-3) == []
    assert mesh.faces == [face]
    assert fold_nonplanar_faces(mesh) == [face]
    assert len(mesh.faces) == 2
