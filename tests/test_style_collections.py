"""User styles live in models; collections never replace scene snapshots."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import pytest
from PySide6.QtCore import QSettings
from core.scene import Scene
from core.camera import OrbitCamera
from core.saved_views import SavedView
from core.style_library import create_model_style,model_styles,write_collection_style,read_collection,remember_collection,collections
from formats.igz import save_scene,load_into
from tests.test_style_editor import _Win
from views.styles_panel import StylesPanel

@pytest.fixture
def preferences(tmp_path,monkeypatch):
    import core.style as module
    monkeypatch.setattr(module,'_settings',lambda:QSettings(str(tmp_path/'styles.ini'),QSettings.IniFormat))


def test_two_custom_styles_and_scene_snapshots_survive_without_a_personal_library(tmp_path,preferences):
    scene=Scene();camera=OrbitCamera()
    first=create_model_style(scene,'Plan')
    first.face_mode='hidden_line';first.guide_color=(1,0,0)
    first.watermarks=[dict(name='Logo',image='aW1hZ2U=',opacity=.4)]
    scene.saved_views.append(SavedView.capture('Ground floor',scene,camera))
    second=create_model_style(scene,'Presentation')
    second.face_mode='textures';second.background=(.1,.2,.3)
    scene.saved_views.append(SavedView.capture('Exterior',scene,camera))
    # A subsequent edit and an exported dictionary must not mutate a scene snapshot.
    first.watermarks[0]['opacity']=1
    raw=scene.saved_views[0].to_dict();raw['style']['watermarks'][0]['opacity']=0
    assert scene.saved_views[0].style['watermarks'][0]['opacity']==.4
    path=tmp_path/'own-styles.igz';save_scene(scene,path)
    loaded=Scene();load_into(loaded,path)
    assert {s.name for s in loaded.styles}=={'Plan','Presentation'}
    loaded.saved_views[0].apply(loaded,camera)
    assert loaded.display_style.name=='Plan'
    assert loaded.display_style.face_mode=='hidden_line'
    assert loaded.display_style.watermarks[0]['opacity']==.4
    loaded.display_style.watermarks[0]['opacity']=.9
    loaded.saved_views[1].apply(loaded,camera)
    assert loaded.display_style.name=='Presentation'
    assert loaded.display_style.background==(.1,.2,.3)
    loaded.saved_views[0].apply(loaded,camera)
    assert loaded.display_style.watermarks[0]['opacity']==.4


def test_portable_collection_import_preserves_all_settings(tmp_path,preferences):
    scene=Scene();style=create_model_style(scene,'My red guide style')
    style.guide_color=(1,0,0);style.endpoint_size=10
    directory=tmp_path/'My collection'
    file=write_collection_style(directory,style)
    assert file.is_file()
    imported=read_collection(directory)
    assert imported[0].to_dict()==style.to_dict()
    remember_collection(directory)
    assert str(directory.resolve()) in collections()
    remember_collection(directory,False)
    assert str(directory.resolve()) not in collections()


def test_creating_and_browsing_are_separate_from_applying_a_style(preferences,monkeypatch):
    from views import prompts
    window=_Win();panel=StylesPanel(window)
    try:
        monkeypatch.setattr(prompts,'get_text',lambda *a,**k:('Own style',True))
        panel._on_save()
        assert window.viewport.scene.display_style.name=='Own style'
        assert any(s.name=='Own style' for s in window.viewport.scene.styles)
        assert panel.browser.location=='model'
        panel._mode.setCurrentIndex(panel._mode.findData('monochrome'))
        assert next(s for s in window.viewport.scene.styles if s.name=='Own style').face_mode=='monochrome'
        panel.browser.open('defaults')
        assert window.viewport.scene.display_style.name=='Own style'
        panel.browser.choose(panel.browser.items.item(3))
        assert window.viewport.scene.display_style.face_mode=='hidden_line'
        panel.browser.open('home')
        assert panel.browser.items.count()>=3
        panel.browser.navigate(-1)
        assert panel.browser.location=='defaults'
    finally:panel.close()


def test_new_document_clears_model_style_library_without_geometry():
    scene=Scene();create_model_style(scene,'Custom')
    scene.clear()
    assert scene.styles==[] and scene.display_style.name=='Default'
