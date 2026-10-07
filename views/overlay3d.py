# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Transient extension geometry. CPU data only; the viewport owns GL objects."""
from __future__ import annotations

import math

import numpy as np


def _vertices(value, size, label):
    if value is None:
        return b"", 0
    points = np.asarray(value, dtype=np.float32)
    if points.size == 0:
        return b"", 0
    if points.ndim != 3 or points.shape[1:] != (size, 3):
        raise ValueError(f"{label} must have shape (N, {size}, 3)")
    if not np.isfinite(points).all():
        raise ValueError(f"{label} must contain finite world coordinates")
    return points.tobytes(), len(points) * size


def _rgba(value):
    color = tuple(float(c) for c in value)
    if len(color) == 3:
        color += (1.0,)
    if len(color) != 4 or any(not math.isfinite(c) or not 0 <= c <= 1
                              for c in color):
        raise ValueError("color must be RGB or RGBA values between 0 and 1")
    return color


class Overlay3D:
    """A named, non-document layer. All mutations run on the GUI thread.

    Geometry uses world metres, independent of the model's edit context.
    It neither participates in history nor changes the document version.
    ``set_geometry`` copies its inputs and replaces BOTH primitive sets.
    Handles survive New/Open/workspace switches, but their geometry clears.
    """

    def __init__(self, viewport, key):
        self._viewport = viewport
        self._key = key
        self._removed = False
        self._revision = 0
        self._lines = b""
        self._triangles = b""
        self._line_count = self._triangle_count = 0
        self._visible = True
        self._color = (0.1, 0.1, 0.1, 1.0)
        self._depth_test = True
        self._depth_bias = 0.0
        self._section_clip = True

    def _check(self):
        if self._removed:
            raise RuntimeError("this 3D overlay has been removed")

    def set_geometry(self, *, lines=None, triangles=None):
        """Replace segments (N,2,3) and triangles (N,3,3); omitted sets clear.

        Invalid input leaves the previous geometry untouched. Different
        colours can use separate named layers; no plugin callbacks run in GL.
        """
        self._check()
        line_data, line_count = _vertices(lines, 2, "lines")
        triangle_data, triangle_count = _vertices(triangles, 3, "triangles")
        self._lines, self._line_count = line_data, line_count
        self._triangles, self._triangle_count = triangle_data, triangle_count
        self._revision += 1
        self._viewport.update()

    def configure(self, *, color=None, depth_test=None, depth_bias=None,
                  section_clip=None):
        """Set appearance without re-uploading geometry.

        Positive ``depth_bias`` pulls towards the camera in normalized clip
        depth (try 1e-5 for coincident hatches); it is not a world displacement.
        Depth testing hides behind the model; False draws through it. Layers
        do not write depth, so they cannot change model depth picking. Alpha
        blends in layer order; this is not a solid/transparent mesh renderer.
        """
        self._check()
        rgba = self._color if color is None else _rgba(color)
        bias = self._depth_bias if depth_bias is None else float(depth_bias)
        if not math.isfinite(bias) or not 0 <= bias <= 0.01:
            raise ValueError("depth_bias must be between 0 and 0.01")
        self._color, self._depth_bias = rgba, bias
        if depth_test is not None:
            self._depth_test = bool(depth_test)
        if section_clip is not None:
            self._section_clip = bool(section_clip)
        self._viewport.update()

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._check()
        self._visible = bool(value)
        self._viewport.update()

    def clear(self):
        """Clear geometry, keeping this handle and its appearance."""
        self.set_geometry()

    def remove(self):
        """Unregister this layer; GPU resources are freed at the next paint."""
        if not self._removed:
            self._viewport._ext_overlays_3d.pop(self._key, None)
            self._removed = True
            self._lines = self._triangles = b""
            self._viewport.update()
