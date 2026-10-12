"""Style persistence, category mixing, visibility, and presentation effects."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QVector3D as V
from PySide6.QtWidgets import QApplication, QMenu
from core.scene import Scene
from core.style import Style, save_user_style
from core.style_effects import ambient_occlusion, image_rect, profile_mesh_data, profile_segments
from tests.test_style_editor import _Win
from views.tray import StylesPanel, _LayerColorDelegate


@pytest.fixture
def panel(tmp_path,monkeypatch):
    import core.style as module
    monkeypatch.setattr(module,'_settings',lambda:QSettings(str(tmp_path/'styles.ini'),QSettings.IniFormat))
    window=_Win()
    widget=StylesPanel(window)
    yield widget
    widget.close()


def test_complete_style_survives_igz_and_independent_copy(tmp_path):
    from formats.igz import save_scene,load_into
    scene=Scene()
    scene.mesh.add_edge(V(0,0,0),V(1,0,0))
    scene.display_style=Style(name='Presentation',description='Site presentation',profile_width=5,
        extensions=True,extension_length=8,endpoints=True,edge_color_mode='by_axis',
        ambient_occlusion=True,ao_distance=2,guide_color=(1,0,0),selected_color=(0,1,1),
        ground=False,show_axes=False,section_line_width=5,
        watermarks=[dict(name='Logo',image='aW1hZ2U=',opacity=.4,layer='overlay')])
    path=tmp_path/'style.igz'
    save_scene(scene,path)
    restored=Scene();load_into(restored,path)
    assert restored.display_style.to_dict()==scene.display_style.to_dict()
    clone=scene.display_style.copy();clone.watermarks[0]['opacity']=1
    assert scene.display_style.watermarks[0]['opacity']==.4


def test_reference_tabs_categories_and_swatch_delegate(panel):
    assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())]==['Select','Edit','Mix']
    assert panel.pages.count()==5
    for chip in panel.swatches.values():
        assert isinstance(chip.itemDelegate(),_LayerColorDelegate)
    panel._category_changed(4)
    assert panel.category_title.text()=='Modeling'


def test_numeric_edits_apply_live_and_visibility_updates_pick_version(panel):
    scene=panel._window.viewport.scene
    panel.controls['profile_width'].setValue(5)
    assert scene.display_style.profile_width==5
    before=scene.version
    panel.controls['show_hidden_geometry'].setChecked(True)
    assert scene.show_hidden_geometry and scene.version>before
    panel.controls['show_guides'].setChecked(False)
    assert not scene.display_style.show_guides
    panel.controls['ground_opacity'].setValue(25)
    assert scene.display_style.ground_opacity==.75


def test_mix_changes_only_chosen_category_and_does_not_alias_watermarks(panel):
    source=Style(name='Source',edge_color=(1,0,0),profile_width=8,background=(0,1,0),
        watermarks=[dict(name='Logo',image='aW1hZ2U=')])
    save_user_style(source);panel.refresh()
    panel.mix_sources['Edge'].setCurrentIndex(panel.mix_sources['Edge'].findData('Source'))
    panel.mix_category('Edge')
    active=panel._style()
    assert active.edge_color==(1,0,0) and active.profile_width==8
    assert active.background != source.background
    panel.mix_sources['Watermark'].setCurrentIndex(panel.mix_sources['Watermark'].findData('Source'))
    panel.mix_category('Watermark')
    active.watermarks[0]['name']='Changed'
    from core.style import style_by_name
    assert style_by_name('Source').watermarks[0]['name']=='Logo'


def test_watermark_order_remove_and_malformed_image_do_not_break_panel(panel):
    panel._style().watermarks=[dict(name='A',image='bad!'),dict(name='B',image='bad!')]
    panel.refresh()
    panel.watermark_list.selectRow(0);panel.move_watermark(1)
    assert [mark['name'] for mark in panel._style().watermarks]==['B','A']
    panel.remove_watermark()
    assert [mark['name'] for mark in panel._style().watermarks]==['B']


def test_ssao_flat_plane_background_and_no_wrapped_border():
    depth=np.full((80,100),.5,dtype=np.float32)
    assert ambient_occlusion(depth,np.eye(4)).max()==0
    assert ambient_occlusion(np.ones_like(depth),np.eye(4)).max()==0
    depth[:,50:]=.3
    shaded=ambient_occlusion(depth,np.eye(4),distance=1,intensity=1)
    assert shaded[:,44:56].max()>0
    assert shaded[:,:4].max()==0 and shaded[:,-4:].max()==0


def test_legacy_sky_off_does_not_add_a_ground_backdrop():
    assert not Style.from_dict({'sky':False}).ground
    assert Style.from_dict({'sky':True}).ground


def test_image_placement_keeps_aspect_and_fits_view():
    x,y,w,h=image_rect(100,50,800,600,'bottom_right',.25)
    assert (x,y,w,h)==(592,492,200,100)
    assert image_rect(100,50,800,600,'stretch')==(0,0,800,600)


def test_hard_boundary_edges_are_profiles_even_without_soft_edges():
    scene=Scene()
    scene.mesh.add_face([V(0,0,0),V(1,0,0),V(1,1,0),V(0,1,0)])
    data=profile_mesh_data(scene.mesh,scene.entity_visible)
    assert profile_segments(data,(0,0,5)).shape==(4,2,3)


def test_material_edges_inherit_container_paint_but_explicit_paint_wins():
    from core.group import Group
    from core.mesh import Mesh
    from core.layer_display import layer_line_buffers
    scene=Scene();mesh=Mesh()
    face=mesh.add_face([V(0,0,0),V(1,0,0),V(1,1,0),V(0,1,0)])
    group=Group(mesh);group.material={'color':(1,0,0)};scene.groups.append(group)
    _,runs=layer_line_buffers(scene,(0,0,0),color_mode='by_material')
    assert runs[0][0]==(1,0,0)
    face.attrs['color']=(0,1,0)
    _,runs=layer_line_buffers(scene,(0,0,0),color_mode='by_material')
    assert runs[0][0]==(0,1,0)


from tests.test_sidebar_trays import settings_file  # isolated settings for a real window


def test_styles_dock_is_reachable_and_style_edits_mark_the_document_dirty(settings_file):
    from views.main_window import MainWindow
    window=MainWindow()
    try:
        menu=QMenu()
        window._fill_panels_menu(menu)
        assert 'Styles' in [action.text() for action in menu.actions()]
        window._show_styles_panel()
        assert not window.styles_dock.isHidden()
        window._saved_version=window.viewport.scene.version
        assert not window._is_dirty()
        window.styles_panel.controls['profile_width'].setValue(6)
        assert window._is_dirty()
        window._saved_version=window.viewport.scene.version
        assert not window._is_dirty()
        window.viewport.scene.select([])
        assert not window._is_dirty()
    finally:
        window._saved_version=window.viewport.scene.version
        window.close()


def test_mix_browser_samples_without_applying_and_drop_only_mixes_category(panel):
    from PySide6.QtCore import Qt, QPointF
    from PySide6.QtGui import QDropEvent
    from PySide6.QtWidgets import QListWidgetItem
    from views.style_browser import STYLE_MIME
    source = Style(name='Drag source', edge_color=(1,0,0), background=(0,1,0))
    item = QListWidgetItem(source.name)
    item.setData(Qt.UserRole, ('style', source.to_dict()))
    before = panel._style().to_dict()
    panel.mix_browser.choose(item)
    assert panel._style().to_dict() == before
    panel.mix_targets['Edge'].click()
    assert panel._style().edge_color == source.edge_color
    assert panel._style().background == tuple(before['background'])
    mime = panel.mix_browser.items.mimeData([item])
    assert mime.hasFormat(STYLE_MIME)
    event = QDropEvent(QPointF(5,5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    panel.mix_targets['Background'].dropEvent(event)
    assert event.isAccepted()
    assert panel._style().background == source.background
