# Projectafspraken

- Kleurvelden in panelen gebruiken altijd dezelfde stijl als de Tags- en
  Clipboxes-panelen: een gecentreerd vierkant van 14 × 14 logische pixels,
  met een dunne donkere rand en afgeronde hoeken (2 pixels), getekend via
  de gedeelde `_LayerColorDelegate` uit `views/tray.py`. Behoud de normale
  selectiekleur van de rij; gebruik geen losse rechthoekige kleuriconen.

- Lees voor productnamen, branches, builds en updates `docs/producten-en-updates.md`.
  Vaste namen: **officiële iT** (ingelibre), **mijn iT** (Guy's publieke fork),
  **SiteRef for iT** (volledige iT + SiteRef) en **SiteRef for SU** (nieuwe SketchUp-companion).
  `iT` = ingeTrezo; `SU` = SketchUp. De gebruiker mag deze afkortingen gebruiken;
  de assistent gebruikt in alle communicatie altijd de volledige namen:
  **officiële ingeTrezo**, **mijn ingeTrezo**, **SiteRef for ingeTrezo** en
  **SiteRef for SketchUp**. Schrijf ook losstaande verwijzingen naar ingeTrezo
  en SketchUp altijd voluit. Deze communicatieafspraak heeft voorrang op
  afkortingen in bestaande documentatie; technische identifiers blijven intact.
- Officiële updates gaan via `upstream` naar mijn iT (`origin`) en daarna naar de
  private uitvoeringen (`siteref-private`). Merge nooit private geschiedenis terug
  naar publiek; neem uitsluitend afzonderlijke gecontroleerde algemene commits over.
- Houd SiteRef-code gedeeld tussen de twee private uitvoeringen. Houd modelleertools
  en standaardicoontjes in de gedeelde iT-basis; alleen de SU-adapter kent SketchUp.
- De standaard SiteRef-uitvoering is **SiteRef for SU** zolang geen andere wordt
  genoemd. Noem bij uitvoeringsspecifieke wijzigingen altijd expliciet het product.

- Als de gebruiker niet expliciet aangeeft dat een verzoek over de algemene versie of over Ingetrazo gaat, ga dan altijd uit van de Siteref-versie. Pas deze standaard toe bij interpretatie en uitvoering van verzoeken.
- Binnen dit project (`ingetrazo`) verwijst "SiteRef" altijd naar de nieuwe SiteRef die hier wordt ontwikkeld en de oude SketchUp-extensie vervangt. Gebruik voor uitvoering en SketchUp-koppelingen de code van dit project; controleer eerst welk startbestand daarbij hoort.
- De actieve SiteRef-devcode staat momenteel in de werkmap `/Users/guywydouw/.codex/worktrees/siteref-pointcloud/ingetrazo`, onder `poc/siteref`. De SketchUp-connector is `poc/siteref/sketchup/siteref_poc.rb`; de viewer is `poc/siteref/viewer.py`. De hoofdcheckout bevat deze bestanden momenteel niet. Controleer bij toekomstige koppelingen of deze werkmap en startbestanden nog bestaan; kies nooit op basis van alleen de naam een andere SiteRef-repository.
- De repository `SiteRef for SketchUp` bevat de oude SiteRef. Gebruik die alleen als de gebruiker expliciet de oude versie bedoelt, of als die repository het actieve project/de werkdirectory van de chat is. Een gelijknamige map, extensie of menuoptie is op zichzelf geen reden om naar die repository over te schakelen.

- De volledige programma-interface is altijd Engels: menu’s, knoppen, tooltips, dialogen, statusmeldingen, foutmeldingen en standaardteksten. Voeg geen Nederlandse gebruikersinterface toe; deze afspraak geldt ook voor nieuwe functionaliteit en beide SiteRef-uitvoeringen. Gebruikersnamen en inhoud van modellen/bestanden blijven behouden.
