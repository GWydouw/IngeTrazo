# SPDX-License-Identifier: GPL-3.0-or-later
"""Transient 3D layers: document isolation, retained uploads and depth drawing."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import math

import numpy as np
import pytest
from PySide6.QtGui import QMatrix4x4, QVector3D
from PySide6.QtWidgets import QApplication

from views.extension_api import ExtensionApp
from views.viewport import Viewport, GL_DEPTH_TEST, GL_FALSE, GL_TRUE


@pytest.fixture
def vp():
    widget = Viewport()
    yield widget
    widget.close()
    widget.deleteLater()


def app(vp, key="hatches"):
    return ExtensionApp(SimpleNamespace(viewport=vp), key)


def test_layers_are_owned_reused_and_explicitly_removed(vp):
    a = app(vp).add_overlay_3d("surface")
    assert app(vp).add_overlay_3d("surface") is a
    b = app(vp, "other").add_overlay_3d("surface")
    assert b is not a
    a.remove()
    a.remove()
    with pytest.raises(RuntimeError):
        a.set_geometry()
    assert app(vp).add_overlay_3d("surface") is not a
    assert app(vp, "other").add_overlay_3d("surface") is b


def test_submission_is_copied_atomic_and_never_enters_the_document(vp, tmp_path):
    from formats import igz
    from core.scene import Scene
    layer = app(vp).add_overlay_3d()
    version = vp.scene.version
    source = np.array([[[0., 0., 0.], [1., 1., 0.]]])
    layer.set_geometry(lines=source)
    original = layer._lines
    source[:] = 9
    assert layer._lines == original
    with pytest.raises(ValueError):
        layer.set_geometry(lines=source, triangles=[[[0, 0, 0]]])
    assert layer._lines == original
    with pytest.raises(ValueError):
        layer.set_geometry(lines=[[[0, 0, 0], [float("nan"), 0, 0]]])
    with pytest.raises(ValueError):
        layer.configure(color=(1, 0, 0), depth_bias=float("nan"))
    assert layer._color == (0.1, 0.1, 0.1, 1.0)
    assert vp.scene.version == version
    assert not vp.history.undo_stack and not vp.history.redo_stack
    path = tmp_path / "overlay.igz"
    igz.save_scene(vp.scene, path)
    loaded = Scene()
    igz.load_into(loaded, path)
    assert not loaded.loose_mesh.faces and not loaded.loose_mesh.edges
    assert not loaded.groups and not loaded.plugin_data


def test_document_boundary_clears_geometry_but_retains_the_handle(vp):
    layer = app(vp).add_overlay_3d()
    layer.set_geometry(lines=[[[0, 0, 0], [1, 0, 0]]])
    layer.configure(color=(1, 0, 0))
    vp.reset_document_caches()
    assert app(vp).add_overlay_3d() is layer
    assert not layer._lines and not layer._line_count
    assert layer._color == (1, 0, 0, 1)


def test_buffers_upload_only_when_geometry_changes_and_state_is_restored(vp, monkeypatch):
    vp._gl = MagicMock()
    vp._program = MagicMock()
    for i, name in enumerate(("use_tex", "use_vcolor", "stipple", "opacity",
                              "shade", "fade", "mvp", "color", "back_color")):
        setattr(vp, f"_loc_{name}", i)
    clips = []
    monkeypatch.setattr(vp, "_set_section_clip", clips.append)
    resources = []

    def create():
        vao, vbo = MagicMock(), MagicMock()
        resources.append((vao, vbo))
        return vao, vbo

    monkeypatch.setattr(vp, "_create_dynamic", create)
    layer = app(vp).add_overlay_3d()
    layer.set_geometry(lines=[[[0, 0, 0], [1, 0, 0]]],
                       triangles=[[[0, 0, 0], [1, 0, 0], [0, 1, 0]]])
    layer.configure(depth_test=False, depth_bias=1e-5)
    matrix = QMatrix4x4()
    vp._draw_extension_overlays_3d(matrix)
    vao, vbo = resources[0]
    assert vbo.allocate.call_count == 1
    assert vp._gl.glDrawArrays.call_count == 2
    assert clips == [True, False]
    assert vp._gl.glDepthMask.call_args_list[-2].args == (GL_FALSE,)
    assert vp._gl.glDepthMask.call_args.args == (GL_TRUE,)
    assert vp._gl.glEnable.call_args.args == (GL_DEPTH_TEST,)
    matrix_calls = [call for call in vp._program.setUniformValue.call_args_list
                    if call.args[0] == vp._loc_mvp]
    assert matrix_calls[-1].args[1] == matrix
    layer.configure(color=(1, 0, 0))
    vp._draw_extension_overlays_3d(matrix)
    assert vbo.allocate.call_count == 1
    layer.visible = False
    calls = vp._gl.glDrawArrays.call_count
    vp._draw_extension_overlays_3d(matrix)
    assert vp._gl.glDrawArrays.call_count == calls
    layer.visible = True
    layer.set_geometry(lines=[[[0, 0, 0], [2, 0, 0]]])
    vp._draw_extension_overlays_3d(matrix)
    assert vbo.allocate.call_count == 2
    layer.remove()
    vp._draw_extension_overlays_3d(matrix)
    vao.destroy.assert_called_once()
    vbo.destroy.assert_called_once()
    assert not vp._ext_overlay_3d_buffers


def test_real_gl_overlay_is_occluded_by_model_and_exports_when_visible(vp):
    if QApplication.platformName() == "offscreen":
        pytest.skip("requires a native OpenGL window (e.g. QT_QPA_PLATFORM=cocoa)")
    vp.resize(640, 480)
    vp.plano_style = "tecnico"
    vp.camera.pitch = math.pi / 2
    vp.camera.yaw = -math.pi / 2
    vp.camera.distance = 5
    vp.camera.perspective = False
    vp.scene.mesh.add_face([QVector3D(-2, -2, 0), QVector3D(2, -2, 0),
                            QVector3D(2, 2, 0), QVector3D(-2, 2, 0)])
    vp.show()
    QApplication.processEvents()
    assert vp._gl is not None, "native GL context did not initialize"
    layer = app(vp).add_overlay_3d()
    layer.configure(color=(1, 0, 0))

    def draw_at(z):
        layer.set_geometry(triangles=[[[-1, -1, z], [1, -1, z], [0, 1, z]]])
        image = vp.render_image(640, overlays=False)
        assert image is not None
        return image.pixelColor(320, 240)

    behind = draw_at(-1)
    assert behind.green() > 80
    front = draw_at(0.01)
    assert front.red() > 240 and front.green() < 10
    layer.configure(depth_test=False)
    through = draw_at(-1)
    assert through.red() > 240 and through.green() < 10
    layer.visible = False
    image = vp.render_image(640, overlays=False)
    assert image.pixelColor(320, 240).green() > 80
    layer.visible = True
    layer.configure(depth_test=True, depth_bias=1e-5)
    layer.set_geometry(lines=[[[-1, 0, 0], [1, 0, 0]]])
    image = vp.render_image(640, overlays=False)
    # A one-pixel GL line may straddle rows and be MSAA blended with white.
    red_pixels = sum(image.pixelColor(x, y).red() -
                     image.pixelColor(x, y).green() > 80
                     for x in range(220, 420) for y in range(237, 244))
    assert red_pixels > 20, "coplanar surface hatch was hidden by its face"
    vp.makeCurrent()
    vp.release_gl_textures()
