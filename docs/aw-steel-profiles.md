# Steel Profiles for IngeTrazo

Port of Guy Wydouw's steel-profile extension from AW Tools for SketchUp.
The extension is a single self-contained Python file, with the original
19 profile families and 424 presets embedded. It uses IngeTrazo's extension
API and does not need SketchUp or Ruby at runtime.

## Install

In an installed IngeTrazo, choose **Extensions → Open plugins folder**.
Copy `aw_steel_profiles.py` from `dist/AW-Steel-Profiles-IngeTrazo.zip`
into that folder and restart IngeTrazo. In a source checkout, the extension
is already in `plugins/` and loads on the next launch.

## Draw and edit

Choose **Extensions → Steel Profiles → Draw steel profile…**.
Select a family and size, or use Custom dimensions. Section dimensions
are in millimetres. Choose Left/Centre/Right and Bottom/Middle/Top to
position the section relative to the line you draw.

The compact dialog shows section icons, a nine-point alignment grid and
collapsible dimensions. Click an anchor to choose the section's position.
Editing a preset's dimensions automatically switches to Custom dimensions.

The movable **Steel Profiles** toolbar has the original two SketchUp
icons: the I-section opens the profile picker; the eyedropper lets you click
an existing steel profile to copy its type, dimensions and alignment, then draw
new profiles with those settings. Its visibility can be toggled from the
extension submenu, and its position follows IngeTrazo's saved window layout.

Click a start point and an end point in the viewport. Native snapping and
axis inference apply, and a wireframe shows the forming profile. After
the first click, point in a direction and type a length into IngeTrazo's
Measurements box for an exact length in the document's units. Esc cancels
the pending profile. The tool remains available for another two-point profile.

Select a generated group and choose **Edit selected profile…**, or use
**Edit steel profile…** in its right-click menu. Editing replaces the
section while retaining the group's placement, including moves, rotations
and transforms. Creation and editing each take one undo step. Parameters
are saved in the `.igz` document and travel with copied groups.

Close any open group-editing context before drawing or editing profiles.
Directly editing or exploding a profile's geometry can remove its
parametric placement; use the extension's edit command to change its section.

## Families and geometry

IPE (including IPEA, IPEAA, IPEO and IPER), IPN, HEA, HEB, HEM,
UPE, UPN, UNP, C, T, equal and unequal L, Z, RHS, SHS, CHS,
flat bar, square bar and round bar.

The section construction matches the original AW Tools: sharp corners,
parallel flanges and 32 segments for round sections. IPN and UPN use the
original simplified outlines, without tapered flanges or root fillets.
Hollow sections contain an actual void, with annular end caps and inward
wall faces. Presets describe the source library's modelling geometry;
this extension does not calculate structural capacity.

## Validation

`tests/test_aw_steel_profiles.py` checks all 424 presets for watertightness
and triangulation, known section volumes including hollow sections,
undo/redo, editing after a transform, `.igz` persistence, alignment,
dialog state, invalid dimensions, plugin discovery and the preview.
