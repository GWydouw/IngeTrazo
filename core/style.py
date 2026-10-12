# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Marco Sumari Tellez and IngeTrazo contributors.
"""Display styles — Styles, scoped to what serves plans/printing.

A style bundles how the model DRAWS (not what it is): the face mode, edge
look and background. It feeds the viewport live and, through scenes, the
sheet composer (frames rendered in the live look inherit the active style;
the composer's own "tecnico"/"lineas" overrides map to Hidden line /
Wireframe).

Face modes (Face Styles):
- ``textures``    Shaded with textures — the default working look.
- ``shaded``      Colours only: textured faces draw in their texture's
                  average colour (the material colour).
- ``hidden_line`` Flat white faces + edges — THE printing/plan style.
- ``monochrome``  Flat default front/back colours, no materials — the
                  reversed-face checker.
- ``wireframe``   Edges only, no faces (nothing occludes).
- ``xray``        Everything translucent, edges always visible — the ones
                  behind a face washed toward the background.

Select/Edit/Mix editing categories share this serialised style record.
Screen-space edge effects, watermarks and ambient occlusion are opt-in;
legacy documents retain their historical defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FACE_MODES = ("textures", "shaded", "hidden_line", "monochrome",
              "wireframe", "xray")

#: The classic default back-face blue-grey: a visible back face means "you are
#: looking at the inside" (or at a genuinely inverted face).
DEFAULT_BACK_COLOR = (0.62, 0.70, 0.78)


@dataclass
class Style:
    name: str = "Default"
    face_mode: str = "textures"
    color_by_layer: bool = False
    edges: bool = True
    profiles: bool = True                    # silhouette/profile edge pass
    # Back Edges (K): the edges hidden behind faces, drawn dashed, over an
    # opaque model — where a bar continues behind a face in a shop drawing
    # (issue #234). Off in every preset.
    back_edges: bool = False
    edge_color: tuple = (0.13, 0.17, 0.23)
    front_color: tuple = (1.0, 1.0, 1.0)     # hidden line / monochrome faces
    # Back-face tint (Back color). ``None`` = automatic: the
    # document's adopted tint (``scene.back_face_color``, e.g. from an
    # imported .skp) or ``DEFAULT_BACK_COLOR``. A picked colour wins over
    # both — see ``effective_back_color``.
    back_color: tuple | None = None
    background: tuple = (0.90, 0.91, 0.92)
    sky: bool = True
    # The sky/ground backdrop tones (drawn when ``sky`` is on; with it off
    # the flat ``background`` shows instead). Defaults match the viewport's
    # historical constants, so old documents look identical.
    sky_color: tuple = (0.925, 0.935, 0.945)
    ground_color: tuple = (0.815, 0.820, 0.815)
    # Section Fill: paint the cut-through areas of solids.
    # Lives in the STYLE, with the other modeling settings.
    section_fill: bool = True
    section_fill_color: tuple = (0.35, 0.37, 0.41)

    uid: str = ""
    description: str = ""
    profile_width: int = 2
    depth_cue: bool = False
    depth_cue_width: int = 4
    extensions: bool = False
    extension_length: int = 2
    endpoints: bool = False
    endpoint_size: int = 7
    dashes: bool = True
    edge_color_mode: str = "all_same"
    material_transparency: bool = True
    transparency_quality: str = "faster"
    xray_opacity: float = 0.6
    ambient_occlusion: bool = False
    ao_default_color: bool = True
    ao_color: tuple = (0.0, 0.0, 0.0)
    ao_distance: float = 1.0
    ao_intensity: float = 0.5
    ao_multiplier: float = 1.0
    ground: bool = True
    horizon_color: tuple | None = None
    ground_opacity: float = 1.0
    show_ground_below: bool = True
    selected_color: tuple = (0.0, 0.0, 1.0)
    locked_color: tuple = (1.0, 0.0, 0.0)
    guide_color: tuple | None = None
    inactive_section_color: tuple = (0.698, 0.714, 0.737)
    active_section_color: tuple = (0.0, 0.0, 1.0)
    section_line_color: tuple | None = None
    section_line_width: float = 2.5
    show_axes: bool = True
    show_guides: bool = True
    show_hidden_geometry: bool = False
    show_hidden_objects: bool = False
    show_section_planes: bool = True
    show_section_cuts: bool = True
    override_section_fill: bool = False
    display_watermarks: bool = True
    watermarks: list = field(default_factory=list)
    photo_image: str = ""
    foreground_photo: bool = False
    foreground_photo_opacity: float = 0.8
    background_photo: bool = False
    background_photo_opacity: float = 1.0

    def to_dict(self) -> dict:
        from dataclasses import asdict
        def json_value(value):
            if isinstance(value, (list, tuple)):
                return [json_value(item) for item in value]
            if isinstance(value, dict):
                return {key: json_value(item) for key, item in value.items()}
            return value
        return json_value(asdict(self))

    @classmethod
    def from_dict(cls, raw: dict) -> "Style":
        from dataclasses import fields
        import copy
        import math
        default = cls()
        values = {}
        for spec in fields(cls):
            fallback = getattr(default, spec.name)
            value = raw.get(spec.name, fallback)
            if isinstance(fallback, bool):
                value = bool(value)
            elif isinstance(fallback, (float, int)):
                try:
                    value = type(fallback)(value)
                    if not math.isfinite(value):
                        value = fallback
                except (TypeError, ValueError, OverflowError):
                    value = fallback
            elif isinstance(fallback, tuple) or spec.name in (
                    "back_color", "guide_color", "horizon_color", "section_line_color"):
                value = _opt_rgb(value)
                if value is None:
                    value = fallback
                elif not all(math.isfinite(c) for c in value):
                    value = fallback
                else:
                    value = tuple(max(0.0, min(1.0, c)) for c in value)
            elif isinstance(fallback, str):
                value = value if isinstance(value, str) else fallback
            elif isinstance(fallback, list):
                value = copy.deepcopy(value) if isinstance(value, list) else []
            values[spec.name] = value
        if "ground" not in raw:
            values["ground"] = values["sky"]  # legacy sky switch controlled both halves
        for key, choices in {"face_mode": FACE_MODES,
                             "edge_color_mode": ("all_same", "by_material", "by_axis"),
                             "transparency_quality": ("faster", "nicer")}.items():
            if values[key] not in choices:
                values[key] = getattr(default, key)
        for key in ("profile_width", "depth_cue_width", "endpoint_size", "extension_length"):
            values[key] = max(1, min(32, values[key]))
        values["section_line_width"] = max(1.0, min(32.0, values["section_line_width"]))
        for key in ("xray_opacity", "ground_opacity", "ao_intensity",
                    "foreground_photo_opacity", "background_photo_opacity"):
            values[key] = max(0.0, min(1.0, values[key]))
        values["ao_distance"] = max(0.001, values["ao_distance"])
        values["ao_multiplier"] = max(0.1, min(100.0, values["ao_multiplier"]))
        values["watermarks"] = [entry for entry in values["watermarks"]
                               if isinstance(entry, dict) and isinstance(entry.get("image"), str)]
        for mark in values["watermarks"]:
            for key, fallback, low, high in (("opacity", .5, 0., 1.), ("scale", .25, .01, 2.)):
                if key not in mark:
                    continue
                try:
                    amount = float(mark.get(key, fallback))
                    mark[key] = max(low,min(high,amount)) if math.isfinite(amount) else fallback
                except (TypeError,ValueError):
                    mark[key] = fallback
            if "layer" in mark and mark.get("layer") not in ("background", "overlay"):
                mark["layer"] = "overlay"
            if "position" in mark and mark.get("position") not in ("top_left", "top_right", "center", "bottom_left", "bottom_right", "stretch", "tile"):
                mark["position"] = "bottom_right"
            if "name" in mark:
                mark["name"] = str(mark["name"])
        return cls(**values)

    def copy(self) -> "Style":
        return Style.from_dict(self.to_dict())


def _opt_rgb(raw) -> tuple | None:
    """An optional RGB from a dict: ``None`` (or anything malformed — an
    old or hand-edited document must never break the style) stays
    ``None``, i.e. automatic."""
    if raw is None:
        return None
    try:
        rgb = tuple(float(c) for c in raw)
    except (TypeError, ValueError):
        return None
    return rgb[:3] if len(rgb) >= 3 else None


def effective_back_color(style, scene=None) -> tuple:
    """The back-face tint that actually draws: the style's own
    ``back_color`` if picked, else the document's adopted tint
    (``scene.back_face_color``), else the classic default blue-grey."""
    picked = getattr(style, "back_color", None)
    if picked is not None:
        return tuple(picked[:3])
    adopted = getattr(scene, "back_face_color", None)
    if adopted is not None:
        return tuple(adopted[:3])
    return DEFAULT_BACK_COLOR


# The usual style collections, adapted: Default (working look),
# Architectural (clean white presentation), and the classic face styles.
def style_by_name(name: str, scene=None) -> Style | None:
    """A COPY of the style called ``name`` — a built-in preset first, then
    the user's saved library (composer frames keep a ``"style:<name>"``
    reference, so both must resolve here). ``None`` if unknown."""
    if scene is not None:
        from core.style_library import model_styles
        for saved in model_styles(scene):
            if saved.name == name:
                return saved.copy()
    for preset in BUILTIN_STYLES:
        if preset.name == name:
            return preset.copy()
    for saved in user_styles():
        if saved.name == name:
            return saved
    return None


BUILTIN_STYLES: list[Style] = [
    Style(name="Default"),
    Style(name="Architectural", background=(1.0, 1.0, 1.0), sky=False, ground=False),
    Style(name="Shaded", face_mode="shaded"),
    Style(name="Hidden line", face_mode="hidden_line",
          background=(1.0, 1.0, 1.0), sky=False, ground=False),
    Style(name="Monochrome", face_mode="monochrome",
          background=(1.0, 1.0, 1.0), sky=False, ground=False),
    Style(name="Wireframe", face_mode="wireframe",
          background=(1.0, 1.0, 1.0), sky=False, ground=False),
    Style(name="X-ray", face_mode="xray"),
]


# ---- User style library ------------------------------------------------------
# Saved styles live in QSettings ("styles/user", a JSON list) like the custom
# basemap sources: small, named, survive across sessions until removed. A
# document doesn't NEED the library — the .igz and saved views carry the full
# style dict — the library is what "Save style…" in the panel feeds and what
# lets a composer frame or another document reference the look by name.

def builtin_names() -> set[str]:
    return {p.name for p in BUILTIN_STYLES}


def _settings():
    """One place to get the QSettings handle, so tests can point it at a
    temp file."""
    from PySide6.QtCore import QSettings
    return QSettings()


def user_styles() -> list[Style]:
    """The saved user styles, in saved order. A broken entry is dropped, not
    fatal — a hand-edited config must never take the panel down."""
    import json
    raw = _settings().value("styles/user", "", type=str)
    if not raw:
        return []
    try:
        entries = json.loads(raw)
    except ValueError:
        return []
    out: list[Style] = []
    if isinstance(entries, list):
        for e in entries:
            if isinstance(e, dict) and e.get("name"):
                out.append(Style.from_dict(e))
    return out


def _store_user_styles(styles: list[Style]) -> None:
    import json
    s = _settings()
    s.setValue("styles/user", json.dumps([st.to_dict() for st in styles]))
    # Flush NOW: a saved style must survive even a crash right after saving
    # (QSettings otherwise buffers until a clean exit).
    s.sync()


def save_user_style(style: Style) -> None:
    """Add ``style`` to the library, replacing a same-named entry. A built-in
    preset's name is refused: the presets are the stable vocabulary that
    ``"style:<name>"`` frame references resolve first, so a user style under
    that name could never be reached."""
    if style.name in builtin_names():
        raise ValueError(f"'{style.name}' is a built-in style")
    kept = [s for s in user_styles() if s.name != style.name]
    _store_user_styles(kept + [style.copy()])


def delete_user_style(name: str) -> bool:
    """Remove the user style called ``name``. True if something was removed."""
    styles = user_styles()
    kept = [s for s in styles if s.name != name]
    if len(kept) == len(styles):
        return False
    _store_user_styles(kept)
    return True
