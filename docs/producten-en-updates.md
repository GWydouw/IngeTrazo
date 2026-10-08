# Productnamen, repositories en updates

Dit document is de vaste afspraak voor ontwikkeling van Guy's ingeTrezo- en
SiteRef-versies. `iT` betekent **ingeTrezo**, `SU` betekent **SketchUp**.
Afkortingen en volledige namen mogen door elkaar worden gebruikt; hun betekenis
blijft gelijk. De bestaande spelling `IngeTrazo` in broncode en repositorynamen
blijft behouden om imports, paden en bestaande installaties niet te breken.

## Vier ondubbelzinnige namen

| Vaste naam | Voluit | Betekenis | Repository / remote |
| --- | --- | --- | --- |
| officiële iT | officiële ingeTrezo | Het oorspronkelijke project van ingelibre; bron van officiële updates | `ingelibre/ingetrazo`, `upstream` |
| mijn iT | mijn ingeTrezo | Guy's publieke fork met algemene verbeteringen | `GWydouw/IngeTrazo`, `origin` |
| SiteRef for iT | SiteRef for ingeTrezo | Volledige mijn iT met alle standaard modelleertools en icoontjes, aangevuld met SiteRef | `GWydouw/SiteRef-IngeTrazo`, `siteref-private` |
| SiteRef for SU | SiteRef for SketchUp | De nieuwe companion met SketchUp-koppeling en dezelfde SiteRef-functionaliteit | `GWydouw/SiteRef-IngeTrazo`, `siteref-private` |

`officiële iT` is nooit Guy's fork. `mijn iT` bevat niet automatisch SiteRef.
`SiteRef for SU` betekent de nieuwe companion uit dit project, niet de oude
SketchUp-extensie in `GWydouw/SiteRef`. Gebruik in issues, commits, builds en
overdrachten een van deze vier namen. Een ongespecificeerd SiteRef-verzoek
betreft standaard de bestaande **SiteRef for SU**, totdat de gebruiker de andere
uitvoering noemt. Gedeelde SiteRef-wijzigingen gelden voor beide uitvoeringen.

## Eén basis en één SiteRef-implementatie

```text
officiële iT (upstream/main)
          |
          v  gecontroleerde integratie van officiële updates
mijn iT (origin/main + algemene featurebranches)
          |
          v  gedeelde basis naar de private repository
SiteRef gedeelde module (privé)
          |                          |
          v                          v
SiteRef for iT                 SiteRef for SU
normaal iT-hoofdvenster        companion + SketchUp-adapter
```

- `core/`, `tools/`, `views/` en standaardresources hebben één gedeelde oorsprong.
  Kopieer geen modelleertools, standaardicoontjes of het normale hoofdvenster.
- SiteRef for iT gebruikt `views/main_window.py` via de normale app-start.
  SiteRef wordt toegevoegd via het uitbreidingssysteem; ontbrekende generieke
  API's worden als afzonderlijke basisverbetering ontwikkeld.
- Pointcloud-I/O, rendering, snappen, clipboxes, scanbeheer, metingen en
  uitlijnen worden door beide private uitvoeringen gedeeld.
- Alleen de SU-adapter kent SketchUp-protocol, synchronisatie en Ruby-code.
  De pointcloudmodule mag geen SketchUp-verbinding nodig hebben.
- Aparte builds kiezen hun integratie en resources. Een andere branch is
  geen reden om dezelfde feature opnieuw te implementeren.

## Branches en werkmappen

| Doel | Lokale branch | Bestemming |
| --- | --- | --- |
| Publieke inrichting en documentatie | `codex/product-structure` | `origin/codex/product-structure` |
| Algemene basisverbeteringen | `codex/<onderwerp>` | `origin/codex/<onderwerp>`, daarna review naar `origin/main` |
| Officiële updates integreren | `codex/update-official-it-YYYY-MM-DD` | `origin`, daarna review naar `origin/main` |
| SiteRef for iT | `codex/siteref-for-it` | `siteref-private/siteref-for-it` |
| SiteRef for SU | `codex/siteref-for-su` | `siteref-private/siteref-for-su` |
| Gedeelde private SiteRef-wijziging | `codex/siteref-shared-<onderwerp>` | Alleen `siteref-private` |

De bestaande private `main` en `codex/siteref-sketchup` zijn historische
companionreferenties. Laat die intact tijdens de overgang. Nieuwe expliciete
productbranches voorkomen dat `main` of "SiteRef" twee uitvoeringen kan betekenen.

De bestaande actieve SU-werkmap staat in
`/Users/guywydouw/.codex/worktrees/siteref-pointcloud/ingetrazo`.
De startbestanden zijn `poc/siteref/viewer.py` en
`poc/siteref/sketchup/siteref_poc.rb`. Controleer altijd of die nog bestaan.
Gebruik `git worktree list` om aanvullende werkmappen te vinden. Een tijdelijke
werkmap onder `/private/tmp` is geen permanente installatie of startpad.

## Officiële updates naar mijn iT

Voer dit uit vanuit een schone publieke checkout. Fetch wijzigt de huidige
bestanden niet. Begin vanaf `origin/main`, niet vanaf een willekeurige featurebranch.

```bash
git status --short --branch
git fetch upstream
git fetch origin
git switch -c codex/update-official-it-YYYY-MM-DD origin/main
git log --oneline HEAD..upstream/main
git diff HEAD...upstream/main
git merge --no-ff upstream/main
```

Los conflicten op met behoud van de bedoelde algemene forkverbeteringen.
Gebruik `git merge --abort` als de integratie moet worden afgebroken; gebruik
geen force-push of hard reset om conflicten te verbergen.

Controleer de snelle tests en relevante handmatige regressies: opstarten,
modelleertools, undo/redo, openen/opslaan en werkbalken. Bekijk bij API-wijzigingen
ook de gevolgen voor SiteRef. Publiceer de updatebranch expliciet:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q -m 'not slow'
git push -u origin HEAD
```

Maak een PR naar **mijn iT**, niet naar officiële iT. Neem pas na review de
gecontroleerde publieke basis over in de private repository. Houd een korte
update-notitie bij: officiële SHA, mijn-iT-SHA, conflicten en validatie.
Officiële updates zijn op aanvraag; deze inrichting plant geen automatische merges.

## Mijn iT naar de private uitvoeringen

Vanuit de betreffende schone private productwerkmap:

```bash
git fetch origin
git merge --no-ff origin/main
```

Controleer behalve de basistests ook de SiteRef-tests en de betrokken host.
Publiceer expliciet naar de productbranch, bijvoorbeeld:

```bash
git push siteref-private HEAD:refs/heads/siteref-for-su
# of, vanuit de iT-productwerkmap:
git push siteref-private HEAD:refs/heads/siteref-for-it
```

Werk beide uitvoeringen bij vanaf dezelfde gecontroleerde basis. Leg gedeelde
private wijzigingen in afzonderlijke commits vast en merge hun featurebranch
naar beide productbranches. Hostspecifieke wijzigingen blijven afzonderlijk.
Branches kunnen tijdelijk een andere basis-SHA hebben; vermeld dat bij de build.

## Verbeteringen die tijdens SiteRef-werk ontstaan

1. Bepaal eerst of de wijziging algemeen is of SiteRef-specifiek.
2. Ontwikkel algemene code bij voorkeur op een publieke featurebranch vanaf
   mijn iT. Die commit bevat geen private imports, paden, assets of dependencies.
3. Ontstaat de algemene fix eerst privé, neem uitsluitend die gecontroleerde
   commit over met `git cherry-pick <sha>` op een publieke featurebranch.
   Controleer de volledige diff en voer de relevante tests opnieuw uit.
4. Laat de algemene verbetering via mijn iT naar beide private versies gaan.
5. Bied een algemene verbetering alleen op expliciet verzoek als PR aan
   officiële iT aan. Beheer de eigen afwijking totdat upstream haar overneemt.

**Merge nooit een private productbranch naar mijn iT of officiële iT.**
Ook als de laatste commit alleen een algemene fix bevat, kan zijn geschiedenis
private code bevatten. Een gecontroleerde cherry-pick neemt die geschiedenis
niet mee. Gebruik nooit `push --all`, `push --mirror` of private tags naar publiek.

## Pushbeveiliging en installatie op een andere machine

`scripts/pre_push_guard.py` controleert branch-/tagnamen én de volledige
bereikbare geschiedenis op private paden. De enige toegestane bestemming voor
private geschiedenis is `GWydouw/SiteRef-IngeTrazo`. De officiële remote is voor
deze workflow alleen voor ophalen ingesteld. De controle is lokaal en kan met
`--no-verify` worden omzeild: doe dat niet. GitHub-repositoryrechten blijven de
uiteindelijke toegangsgrens; een lokale hook is aanvullende bescherming.

Installeer na een clone of wijziging aan de guard:

```bash
python3 scripts/install_push_guard.py
```

De installer vervangt geen onbekende bestaande hook en respecteert een afwijkend
`core.hooksPath` door installatie te weigeren met een uitleg. Worktrees delen
dezelfde Git-configuratie en hooks; afzonderlijke clones installeren die apart.

Benodigde remotes:

```bash
git remote add upstream https://github.com/ingelibre/ingetrazo.git
git config remote.upstream.pushurl DISABLED-official-upstream
git remote add siteref-private https://github.com/GWydouw/SiteRef-IngeTrazo.git
git config push.default simple
```

Gebruik `git remote set-url` in plaats van `add` als de remote al bestaat.
Productbranches hebben hun eigen `pushRemote` en upstream. `origin` blijft
altijd mijn iT, ook in de private werkmappen. Stel nooit een algemene
`remote.siteref-private.push` in die elke push naar de oude companion-`main` stuurt.
Controleer voor publiceren `git remote -v`, `git branch -vv` en `git push --dry-run`.

De lokale `codex/siteref-for-*`-namen verschillen bewust van de korte private
remote-branchnamen. Met `push.default=simple` kan een gewone `git push` daarom
weigeren. Gebruik de expliciete productpush hierboven; die noemt altijd de
bedoelde bestemming. Laat de oude companionbranch eveneens expliciet naar
`siteref-private` pushen zolang die nog wordt gebruikt.

## Buildprofielen en traceerbaarheid

`products/mijn-it.json` beschrijft de publieke uitvoering. Private profielen,
code en toekomstige packaging blijven uitsluitend in de private branches.
Controleer een profiel met:

```bash
python3 scripts/product_profile.py mijn-it
```

Een profiel vermeldt product-ID, vaste naam, host, bron-entrypoint,
voorgestelde app-identiteit en de gereedheid van bronintegratie en packaging.
`--require-ready` weigert een uitvoering waarvan de integratie nog niet klaar is.
De uitvoer bevat de exacte bron-SHA en de werkboomstatus. Een release vereist een
schone werkboom, een vastgelegde publieke basis-SHA, geslaagde tests en een
gevalideerde installer. Een profiel alleen is geen voltooide app-build.

De private uitvoeringen krijgen verschillende app-/instellingenidentiteiten,
zodat zij naast mijn iT en naast elkaar kunnen bestaan. Die identiteiten zijn
in de profielen gereserveerd; bestaande runtime-instellingen veranderen pas
bij implementatie en migratie, nooit alleen door dit document.

## Implementatiestatus bij inrichting (8 oktober 2026)

- De normale mijn-iT-app bestaat en behoudt haar huidige packaging.
- SiteRef for SU bestaat in `poc/siteref`; de bestaande launcher blijft werken.
- SiteRef for iT krijgt een eigen private branch en profiel. De integratie van
  pointclouds in het volledige normale iT-hoofdvenster moet nog worden uitgevoerd.
- De bestaande pointcloudcode wordt niet gekopieerd. Extractie naar een
  hostonafhankelijke module en scheiding van de SU-adapter gebeuren stapsgewijs.
- Nieuwe private installers, gescheiden runtime-instellingen en een volledige
  buildmatrix zijn vervolgstappen; presenteer die niet als reeds werkend.

## Acceptatie van de volgende integratiestap

SiteRef for iT is pas gereed wanneer het volledige normale iT-venster met alle
standaard tools en icoontjes opent, pointclouds dezelfde gedeelde implementatie
gebruiken als SU, openen/opslaan en undo werken, er geen SketchUp-verbinding
nodig is en een eigen installer naast de andere apps is getest. SiteRef for SU
moet tijdens die extractie blijven werken. Werk deze status en de profielen
bij wanneer een stap werkelijk is gevalideerd.
