# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""A selected face is drawn as a dot pattern whose colour reads on its paint.

Selected faces get blue dots, with light cyan on saturated blue paint.
"""
from __future__ import annotations

import os

import pytest
from PySide6.QtGui import QVector3D


def V(x, y, z=0.0):
    return QVector3D(float(x), float(y), float(z))


def _viewport():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    elif not isinstance(app, QApplication):
        pytest.skip("another Qt application flavour is already running")
    from views.viewport import Viewport
    vp = Viewport(None)
    vp.resize(800, 600)
    return vp


def test_dot_colour_switches_on_blue_surfaces():
    from views.viewport import (SELECTION_DOT_ALT_COLOR, SELECTION_DOT_COLOR,
                                selection_dot_color)
    assert selection_dot_color((0.96, 0.95, 0.925)) == SELECTION_DOT_COLOR
    assert selection_dot_color((0.62, 0.70, 0.78)) == SELECTION_DOT_COLOR
    assert selection_dot_color(None) == SELECTION_DOT_COLOR
    assert selection_dot_color((0.0, 0.0, 1.0)) == SELECTION_DOT_ALT_COLOR
    assert selection_dot_color((0.85, 0.15, 0.10)) == SELECTION_DOT_COLOR
    # A pale, washed-out peach is not "orange" enough to hide the dots.
    assert selection_dot_color((0.95, 0.90, 0.85)) == SELECTION_DOT_COLOR


def test_each_side_is_judged_against_its_own_paint():
    from views.viewport import SELECTION_DOT_ALT_COLOR, SELECTION_DOT_COLOR
    vp = _viewport()
    face = vp.scene.mesh.add_face([V(0, 0), V(1, 0), V(1, 1), V(0, 1)])
    # Default cream front, default blue-grey back: blue on both.
    assert vp._selection_dot_colors(face) == (SELECTION_DOT_COLOR,
                                              SELECTION_DOT_COLOR)
    face.attrs["color"] = (0.0, 0.0, 1.0)                # blue front only
    assert vp._selection_dot_colors(face) == (SELECTION_DOT_ALT_COLOR,
                                              SELECTION_DOT_COLOR)
    face.attrs["back"] = True                           # both sides blue
    assert vp._selection_dot_colors(face) == (SELECTION_DOT_ALT_COLOR,
                                              SELECTION_DOT_ALT_COLOR)


def test_selected_faces_are_split_into_runs_per_dot_colour():
    vp = _viewport()
    plain = vp.scene.mesh.add_face([V(0, 0), V(1, 0), V(1, 1), V(0, 1)])
    blue = vp.scene.mesh.add_face([V(2, 0), V(3, 0), V(3, 1), V(2, 1)])
    blue.attrs["color"] = (0.0, 0.0, 1.0)
    vp.scene.selection.update({plain, blue})
    vp.scene.version += 1
    vp.show()
    vp.grab()                                           # forces a GL frame
    if vp._sel_faces_vbo is None:
        pytest.skip("no GL context in this environment")
    spans = vp._sel_faces_spans
    assert len(spans) == 2
    assert sum(n for *_c, _s, n in spans) == vp._sel_faces_count
