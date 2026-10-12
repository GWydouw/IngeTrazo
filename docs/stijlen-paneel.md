# Styles-paneel in mijn ingeTrezo

Het paneel volgt de aangeleverde SketchUp-referenties: stijlvoorbeeld, naam en
beschrijving, **Select / Edit / Mix**, en onder Edit de categorieën **Edge / Face /
Background / Watermark / Modeling**. Het staat in de zijbalk en is bereikbaar via
**Window → Panels → Styles** en de bestaande Styles-knop in de Panels-werkbalk.
De interface is Engels. Kleurvelden gebruiken de gedeelde `_LayerColorDelegate`
met een vierkant van 14 × 14 logische pixels, zoals afgesproken voor dit project.

## Analyse en implementatie

| Onderdeel | Bestond al | Toegevoegd |
| --- | --- | --- |
| Stijlbeheer | Ingebouwde presets, persoonlijke bibliotheek, opslaan/verwijderen, stijlgegevens in modellen en opgeslagen views | Select/Edit/Mix, visuele bibliotheek, bewerkbare naam/beschrijving, preview, bijwerken van een opgeslagen stijl en per categorie mengen |
| Edge | Edges, Back Edges, Profiles, één randkleur | Instelbare profielbreedte, Depth cue, Extension, Endpoints, Dashes, kleur By axis en By material |
| Face | Textures, Shaded, Hidden line, Monochrome, Wireframe, X-ray, voor- en achterkleur | Materiaaltransparantie aan/uit, Faster/Nicer, X-ray opacity, Ambient Occlusion met kleur, afstand, intensiteit en vermenigvuldiger |
| Background | Achtergrondkleur, luchtkleur, grondkleur, lucht aan/uit | Afzonderlijke grondschakelaar, horizonkleur, grondtransparantie, Show ground from below |
| Watermark | Geen stijlwatermerken | Achtergrond- en voorgrondwatermerken, toevoegen, verwijderen, wijzigen, volgorde, positie, grootte, opacity, stretch en tile |
| Modeling | Hidden Geometry/Objects, tagkleuren, doorsnedevlakken en -snedes, doorsnedevulling; vaste kleuren voor selecties en constructielijnen | Instelbare Selected/Locked/Guides/Active Section/Inactive Section/Section Lines; breedte van snedelijnen; Model Axes/Guides; Override Section Fill by Style; foto-overlays met afzonderlijke voor-/achtergrondopacity |

Nieuwe stijlvelden worden meegenomen in `.igz`, de persoonlijke stijlbibliotheek,
kopieën en opgeslagen views. Het wijzigen van een stijl maakt het model
onopgeslagen, zonder een selectiewijziging als modelbewerking te behandelen.
Kleur van constructielijnen kan in Modeling worden gekozen. Als een stijl geen
expliciete Guides-kleur heeft, blijft de eerder toegevoegde globale kleurinstelling
van toepassing. De standaardkleur in de bestaande SiteRef for SketchUp-werkmap
blijft daardoor rood.

## Rendering en grenzen

- Profielen, endpoints en extensions worden in schermpixels getekend, ook op
  drivers die `glLineWidth` tot één pixel beperken. Profielen omvatten harde
  buitenranden en de bestaande silhouetten van zachte gebogen oppervlakken.
- Depth cue varieert de randbreedte met de afstand tot de camera. By axis kleurt
  randen die langs een wereldas liggen. By material gebruikt het materiaal van
  het aangrenzende vlak, met overerving van de groep: ingeTrezo heeft nog geen
  afzonderlijke materiaalopslag voor iedere losse rand.
- Nicer sorteert driehoeken binnen een transparante materiaalrun van achter
  naar voren. Het is geen volledige order-independent transparency tussen alle
  verschillende materiaalruns.
- Ambient Occlusion is een begrensde screen-space berekening uit de bestaande
  dieptebuffer. Zij is standaard uitgeschakeld en geldt voor ondoorzichtige
  vlakweergaven. Grote modellen en hoge schermresoluties kunnen bij inschakelen
  extra rendertijd kosten; de berekening gebruikt een verkleind dieptebeeld.
- Watermerken worden als ingesloten PNG bewaard; model en stijl blijven daardoor
  bruikbaar zonder het oorspronkelijke externe afbeeldingsbestand. Achtergrond-
  en voorgrondwatermerken worden ook meegenomen in beeldexports.
- Match Photo biedt weergave van een gekozen foto vóór/achter het model met
  afzonderlijke opacity. Automatische camerakalibratie uit verdwijnpunten is
  geen bestaande functie van ingeTrezo en wordt hiermee niet toegevoegd.
- De indeling en instellingen volgen de referenties, maar gebruiken native Qt-
  bediening en de afgesproken kleine swatches. Dit is geen pixelidentieke kopie
  van SketchUp en de renderers zijn niet identiek.

## Validatie

Relevante tests controleren stijl- en modelpersistentie, categorieën mengen,
zichtbaarheid, swatches, watermerkvolgorde, omgevingsschaduw op een vlak en aan een
hoek, materiaalovererving, profielen, zijbalk, selectie en gewijzigde modellen.
Aanvullend zijn beide shaderprogramma's gecompileerd en gekoppeld met een native
macOS OpenGL-context. Native beeldexports zijn gecontroleerd voor gewone randen,
rand-effecten, materiaalranden, Ambient Occlusion, Nicer-transparantie,
uitgeschakelde materiaaltransparantie, verborgen assen/hulplijnen, X-ray en
achtergrond-/voorgrondwatermerken, zonder OpenGL-fouten.

## Stijlbeheer en scènes (12 oktober 2026)

Select is een collectiebrowser, geen vlakke lijst van vlakweergaven. Home toont
**In Model**, **Default Styles**, **My Styles** en favoriete collectiemappen. De
keuzelijst wisselt van collectie zonder het model anders weer te geven. Back,
Forward en Home werken als in een bestandsbrowser; een stijlthumbnail toepassen
is een afzonderlijke handeling. Er zijn kleine/grote thumbnails en een lijstweergave.

De **＋ Create style**-knop maakt een benoemde kopie van de huidige stijl in de
modelbibliotheek. Eigen stijlen krijgen een vaste identiteit. Wijzigingen aan een
modelstijl blijven in die modelstijl bewaard; **Update style in model** slaat ook
de huidige weergave expliciet op. Alle modelstijlen reizen mee in het `.igz`-bestand,
ook stijlen die op het moment van opslaan niet actief zijn.

Een scène bewaart bovendien een onafhankelijke, volledige stijlsnapshot. Het later
bewerken, hernoemen of verwijderen van een bibliotheekstijl verandert een bestaande
scènesnapshot niet. **Update Scene** neemt de nieuwe toestand over. Scènes en
watermerken worden diep gekopieerd, zodat bewerkingen geen gedeelde lijsten wijzigen.
Modellen uit de vorige uitvoering blijven leesbaar: bestaande scènesnapshots worden
bij het openen ook als modelstijlen beschikbaar gemaakt.

Eigen collecties zijn gewone mappen met draagbare `.igstyle`-bestanden. De opties
kunnen een map openen/aanmaken, als favoriet bewaren, de huidige stijl erin bewaren
en stijlen naar de modelbibliotheek importeren. Favorieten zijn persoonlijke
voorkeuren; een model of scène is voor zijn weergave niet van die mappen afhankelijk.

## Kleurselectors (12 oktober 2026)

Alle losse kleurvelden in Styles, Preferences, materiaal-tint, maatvoering en
bladopmaak gebruiken `views/color_selector.py`. Die tekent de bestaande 14 × 14
kleurchip via `_LayerColorDelegate`, met de dunne donkere rand en afgeronde hoeken.
De losse selector heeft geen tabelgrid, buitenkader, knopachtergrond of blijvende
selectieachtergrond. De normale rijselectie in Tags en Clipboxes blijft behouden.
De constructielijnselector van SiteRef for SketchUp gebruikt dezelfde component.

## Categorie-iconen (12 oktober 2026)

De vijf categorieën gebruiken de aangeleverde SketchUp-iconen, in volgorde:
`dlg_style_edge`, `dlg_style_face`, `dlg_style_environment`,
`dlg_style_watermark` en `dlg_style_working` (Modeling). De oorspronkelijke SVGs
staan in `resources/icons`. Hun filters en compositing worden niet correct
weergegeven door QtSvg. Het paneel gebruikt daarom PNG-weergaven op viermaal
de logische iconengrootte, met behoud van transparantie en oorspronkelijke kleuren.
Beide formaten worden mee verpakt. De PNGs gebruiken alle dezelfde oorspronkelijke 24-punts ontwerpcoördinaten,
zodat de kubussen even groot zijn en de grondplaat van Background breder blijft.
De PNGs zijn opnieuw te maken met:

```bash
python3 scripts/render_style_icons.py
```

## Mix layout and sampling (12 October 2026)

Mix uses five category targets with the same category artwork as Edit, followed
by a separate Select collection browser below. Selecting a style in this browser
samples it without applying it. Clicking a target copies only that category from
the sampled style. Dragging a style thumbnail directly onto a target has the same
category-only behavior. Nested lists such as watermarks are copied independently.
The old per-category dropdowns are no longer visible. Collections show actual
available model, default, personal and favorite libraries, with a shared vector
collection-folder icon.

## Collection navigation artwork (12 October 2026)

Select and Mix share the supplied `previous_arrow`, `next_arrow`, `dlg_in_model`
and `dlg_flyout_menu` artwork. Their original 24-point PDF canvases are rendered
as transparent 96-pixel PNGs and displayed at 24 logical pixels. The toolbar
buttons use auto-raise, showing no permanent button frame. In Model opens the
model-owned style collection; Back and Forward follow collection navigation.
