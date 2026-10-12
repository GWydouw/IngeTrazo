# SPDX-License-Identifier: GPL-3.0-or-later
"""Model-owned styles and portable user collections."""
import json
import uuid
from pathlib import Path
from core.style import Style, BUILTIN_STYLES, user_styles


def _settings():
    from core.style import _settings as settings
    return settings()


def model_styles(scene):
    """Current model and legacy scene snapshots remain independent of preferences."""
    result = {}
    for style in getattr(scene, 'styles', []):
        result[style.uid or style.name] = style.copy()
    active = getattr(scene, 'display_style', None)
    if active is not None:
        result[active.uid or active.name] = active.copy()
    return list(result.values())


def store_model_style(scene, style):
    if not style.uid:
        style.uid = str(uuid.uuid4())
    previous = next((s for s in scene.styles if s.uid == style.uid),None)
    if previous is not None and previous.to_dict() == style.to_dict():
        return
    kept = [s for s in scene.styles if s.uid != style.uid]
    scene.styles = kept + [style.copy()]
    scene.version += 1


def create_model_style(scene, name, source=None):
    name = name.strip()
    if not name:
        raise ValueError('Enter a style name.')
    if any(style.name == name for style in model_styles(scene)):
        raise ValueError('A style with this name already exists in the model.')
    style = (source or scene.display_style).copy()
    style.uid = str(uuid.uuid4())
    style.name = name
    store_model_style(scene, style)
    scene.display_style = style
    return style


def delete_model_style(scene, uid):
    before = len(scene.styles)
    scene.styles = [style for style in scene.styles if (style.uid or style.name) != uid]
    if len(scene.styles) != before:
        scene.version += 1
    # Scene snapshots and the current view still own their full style data.


def collections():
    raw = _settings().value('styles/collections', '[]', type=str)
    try:
        items = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return [str(path) for path in items if isinstance(path, str)] if isinstance(items, list) else []


def remember_collection(path, add=True):
    path = str(Path(path).resolve())
    values = [item for item in collections() if item != path]
    if add:
        values.append(path)
    settings = _settings()
    settings.setValue('styles/collections', json.dumps(values))
    settings.sync()


def read_collection(path):
    result = []
    for file in sorted(Path(path).glob('*.igstyle')):
        try:
            raw = json.loads(file.read_text())
            if isinstance(raw, dict) and isinstance(raw.get('style'), dict):
                result.append(Style.from_dict(raw['style']))
        except (OSError, ValueError, TypeError):
            continue
    return result


def write_collection_style(path, style):
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = style.copy()
    if not snapshot.uid:
        snapshot.uid = str(uuid.uuid4())
        style.uid = snapshot.uid
    import re
    filename = re.sub(r'[^\w .-]', '_', snapshot.name).strip(' .') or 'Style'
    import hashlib
    identifier = hashlib.sha256(snapshot.uid.encode()).hexdigest()[:12]
    destination = directory / (filename + '-' + identifier + '.igstyle')
    temporary = destination.with_suffix('.igstyle.tmp')
    temporary.write_text(json.dumps({'format': 'ingetrazo-style', 'version': 1,
                                     'style': snapshot.to_dict()}, indent=2)+'\n')
    temporary.replace(destination)
    return destination
