# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""X switches X-ray on and back off.

A look through the faces is a glance: the key goes into X-ray and, pressed
again, returns to the style you were in, edge and profile settings included.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

if QApplication.instance() is None:
    QApplication(sys.argv[:1])


def _window():
    from views.main_window import MainWindow
    return MainWindow()


def _close(win):
    win._saved_version = win.viewport.scene.version
    win.close()


def test_x_is_the_toggle_and_text_uses_shift_x():
    from views.shortcuts import collect_actions
    win = _window()
    try:
        x = QKeySequence("X")
        assert win._act_xray_toggle.shortcut() == x
        holders = [a for a in collect_actions(win) if x in a.shortcuts()]
        assert holders == [win._act_xray_toggle]
        assert win._tool_actions["text"].shortcut() == QKeySequence("Shift+X")
    finally:
        _close(win)


def test_the_toggle_goes_back_to_the_style_you_left():
    from core.style import style_by_name
    win = _window()
    try:
        win._apply_display_style(style_by_name("Shaded"))
        win._set_style_field("profiles", True)
        win._act_xray_toggle.trigger()
        style = win.viewport.scene.display_style
        assert style.face_mode == "xray"
        assert win._style_actions["X-ray"].isChecked()

        win._act_xray_toggle.trigger()
        style = win.viewport.scene.display_style
        assert style.name == "Shaded" and style.face_mode == "shaded"
        assert style.profiles is True              # your tweak came back too
        assert win._style_actions["Shaded"].isChecked()
    finally:
        _close(win)


def test_xray_picked_from_the_menu_toggles_out_to_default():
    from core.style import style_by_name
    win = _window()
    try:
        win._apply_display_style(style_by_name("X-ray"))
        win._act_xray_toggle.trigger()
        assert win.viewport.scene.display_style.name == "Default"
    finally:
        _close(win)


def test_face_toolbar_preserves_settings_and_follows_scene_style():
    from core.style import FACE_MODES, Style
    win = _window()
    try:
        assert set(win._face_mode_actions) == set(FACE_MODES)
        win.viewport.scene.display_style = Style(
            name="Custom", background=(0.2, 0.3, 0.4), sky=False,
            profiles=False)
        for mode, action in win._face_mode_actions.items():
            assert not action.icon().isNull()
            action.trigger()
            style = win.viewport.scene.display_style
            assert style.face_mode == mode
            assert style.background == (0.2, 0.3, 0.4)
            assert not style.sky and not style.profiles
            assert action.isChecked()
        win._apply_display_style(Style(face_mode="hidden_line"))
        assert win._face_mode_actions["hidden_line"].isChecked()
        win._act_style_back_edges.trigger()
        assert win.viewport.scene.display_style.back_edges
        assert win._act_style_back_edges in win.toolbars["face_styles"].actions()
    finally:
        _close(win)
