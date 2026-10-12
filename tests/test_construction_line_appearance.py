"""Construction guide settings and screen-space visibility."""
from types import SimpleNamespace

import pytest
from PySide6 import QtCore
from PySide6.QtGui import QMatrix4x4
from views.viewport import Viewport


def test_saved_color_and_invalid_color_fallback(tmp_path, monkeypatch):
    settings = QtCore.QSettings(str(tmp_path / 'guides.ini'), QtCore.QSettings.IniFormat)
    monkeypatch.setattr(QtCore, 'QSettings', lambda: settings)
    viewport = SimpleNamespace(construction_color_key='siteref/construction_line_color',
                               construction_color_default='#ff0000')
    assert Viewport.construction_line_color(viewport).name() == '#ff0000'
    settings.setValue(viewport.construction_color_key, '#00aa44')
    assert Viewport.construction_line_color(viewport).name() == '#00aa44'
    settings.setValue(viewport.construction_color_key, 'invalid')
    assert Viewport.construction_line_color(viewport).name() == '#ff0000'


@pytest.mark.parametrize('dpr', [1, 2])
def test_guide_width_color_and_depth_on_drivers_with_one_pixel_lines(dpr):
    draws, colors, masks, matrices = [], [], [], []
    viewport = SimpleNamespace(
        _fb_size=lambda: (800 * dpr, 600 * dpr), devicePixelRatioF=lambda: dpr,
        _gl=SimpleNamespace(glDrawArrays=lambda *args: draws.append(args),
                            glDepthMask=masks.append),
        _set_color=lambda *args: colors.append(args), _loc_mvp=7,
        _program=SimpleNamespace(setUniformValue=lambda _, matrix: matrices.append(matrix)))
    vao = SimpleNamespace(bind=lambda: None, release=lambda: None)
    matrix = QMatrix4x4()
    Viewport._draw_selection_lines(viewport, vao, 12, matrix, first=6,
                                   color=(1, 0, 0), width=2)
    assert colors == [(1, 0, 0, 1)]
    assert len(draws) > 1
    assert all(first == 6 and count == 12 for _, first, count in draws)
    assert masks == [False, True]
    assert matrices[-1] == matrix
    extent = max(abs(m.column(3).x()) for m in matrices)
    assert extent == pytest.approx((2 * dpr - 1) / (800 * dpr))
