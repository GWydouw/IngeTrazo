# ModelShare — verkenning van een gedeeld model en eigen formaat

Datum: 10 oktober 2026.

Status: verslag van een brainstorm. Dit document bewaart de besproken visie,
uitgangspunten, voorstellen en open vragen. Het is geen definitieve specificatie,
implementatieplan of opdracht om nu te bouwen. Deze ontwikkeling is voor nu te
groot en vraagt later grondig ontwerpwerk. ModelShare is de historische naam en
wordt hier als werknaam gebruikt; een toekomstige productnaam is niet besloten.

## Aanleiding en historische proef

De gebruiker wil al lange tijd met meerdere gebruikers aan één SketchUp-model
kunnen werken. Ongeveer tien jaar geleden bestond daarvoor een proof of concept
met de naam ModelShare. Daarmee ontwierpen twee gebruikers samen een grote school.

Het systeem werkte volgens de gebruiker goed en gebruikte een centrale
Dropbox-map als bibliotheek:

- Iedere groep of component op modelniveau werd als afzonderlijk objectbestand
  weggeschreven. Nesting werd toen niet ondersteund.
- Het lokale model was standaard vergrendeld. Een gebruiker kon een object
  vrijmaken om het te bewerken en reserveerde het daarmee voor zichzelf.
- De reservering werd in de centrale map geregistreerd, zodat anderen hetzelfde
  object niet tegelijkertijd konden bewerken.
- Na een commit werd het object opnieuw beschikbaar.
- Andere gebruikers kregen een melding en konden de gewijzigde objecten ophalen.
- Gebruikers konden slechts een subset van het grote model laden en bewerken.
- Multitagging hielp om objecten te selecteren en versies of alternatieven samen
  te stellen.

Lokale SketchUp-bestanden konden al verschillende voorstellingen van hetzelfde
gedeelde model bevatten. De belangrijkste gewenste verandering ten opzichte van
die proef is samenwerken zonder verplichte objectreserveringen, met versiebeheer
en ondersteuning voor het oplossen van conflicten.

## Visie: een zelfstandig gedeeld model

Het voorstel is een eigen modelstructuur en bestandsformaat te ontwerpen die
onafhankelijk zijn van het gesloten `.skp`-formaat. SketchUp, ingeTrezo en een
eventuele webviewer krijgen toegang tot hetzelfde ModelShare-project via adapters.
In de huidige projectcontext betreft dit onder meer SiteRef for SketchUp en
SiteRef for ingeTrezo.

Het eigen formaat bepaalt de regels. Elke adapter is verantwoordelijk voor de
correcte heen-en-terugvertaling naar zijn applicatie. Het gedeelde model wordt
dus niet gedefinieerd door telkens een volledig lokaal applicatiemodel naar een
ander programma te kopiëren.

De technische uitdaging om adapters correct te bouwen blijft bestaan, maar de
definitie van correct gedrag ligt bij het eigen modelcontract. Het formaat alleen
garandeert nog geen verliesvrije omzetting of betrouwbare synchronisatie.

## Gedeeld model en lokale werkdocumenten

De gebruiker verduidelijkte dat het gedeelde model uitsluitend commits kent.
Lokaal opslaan blijft bestaan voor de applicatiegebonden werkomgeving.

In SketchUp kunnen bijvoorbeeld scenes, styles, camera's en andere lokale
presentatie-instellingen in een `.skp`-bestand worden bewaard. De geladen geometrie
is een lokale werkkopie van het ModelShare-model. Opslaan in SketchUp publiceert
geen modelwijzigingen naar ModelShare.

| Handeling | Betekenis |
| --- | --- |
| Bewerken | De lokale werkkopie veranderen |
| Lokaal opslaan | Het applicatiegebonden werkdocument bewaren |
| Committen | Modelwijzigingen als revisie vastleggen |
| Verspreiden | Lokale commits beschikbaar maken voor andere gebruikers |
| Updaten | Ontvangen commits in de lokale werkkopie verwerken |

Bij offline werken kunnen committen en verspreiden op verschillende momenten
plaatsvinden. De precieze gebruikersinterface en terminologie hiervoor moeten
nog worden ontworpen.

Als voorstel kan een lokaal werkdocument ook ongecommitte wijzigingen bewaren
voor herstel en later verderwerken. Dit maakt die wijzigingen niet tot gedeelde
modelgeschiedenis. Hoe dat herstel werkt, is nog niet besloten.

Een werkdocument moet ten minste onthouden naar welk project en eventueel welke
projecttak het verwijst, van welke revisie het vertrekt en welke objecten geladen
zijn. Eventuele lokale wijzigingen moeten ook herkenbaar blijven.

## Meerdere lokale voorstellingen door dezelfde gebruiker

Eén gebruiker kan meerdere lokale `.skp`-bestanden bijhouden die hetzelfde
ModelShare-project voorstellen, bijvoorbeeld:

- Een presentatiebestand met eigen scenes en styles.
- Een werkvoorbereidingsbestand met slechts de relevante objecten geladen.
- Een gevelstudie met eigen camera's en doorsneden.

Deze bestanden kunnen naar dezelfde projecttak verwijzen, maar elk bestand heeft
zijn eigen werkomgeving, selectie, uitgangsrevisie en eventuele lokale wijzigingen.
Een commit vanuit het ene bestand wordt bij een update in het andere verwerkt.
Ook tussen werkdocumenten van dezelfde gebruiker kan dus een conflict ontstaan.

Een andere voorstelling van hetzelfde ontwerp vraagt een ander lokaal
werkdocument. Een werkelijk ander ontwerp kan een alternatief of projecttak in
ModelShare vragen. De precieze inrichting daarvan staat nog open.

## Voorgestelde onderdelen van het modelcontract

Dit zijn kandidaten voor de toekomstige specificatie, geen vastgesteld schema:

- Vaste, programmaonafhankelijke objectidentiteiten.
- Geometrie, materialen, texturen en modeleigenschappen.
- Componentdefinities en afzonderlijke plaatsingen die daarnaar verwijzen.
- Hiërarchie en nesting.
- Meerdere tags per object.
- Objectversies en commits met auteurschap en verwijzingen naar uitgangscommits.
- Projecttakken of een andere expliciete structuur voor ontwerpvarianten.

Het onderscheid tussen definitie en plaatsing is essentieel: één raam verplaatsen
is een andere wijziging dan het raamtype veranderen dat op twintig plaatsen
gebruikt wordt. SketchUp kent dit onderscheid eveneens tussen componentdefinities
en componentplaatsingen.

Als voorgestelde adapterregel geldt: informatie die een applicatie niet kan
bewerken, moet behouden blijven. Een adapter publiceert alleen bedoelde wijzigingen
en verwijdert geen onbekende eigenschappen doordat die lokaal niet weergegeven
worden. Een webviewer kan alleen lezen of beperkte wijzigingen ondersteunen.

Scenes en styles zijn in de besproken SketchUp-werkwijze lokaal. Welke overige
eigenschappen gedeeld zijn en welke lokaal blijven, moet expliciet worden bepaald;
bijvoorbeeld modelmaterialen tegenover instellingen voor materialenweergave.

## Gedeeltelijk laden en multitagging

Gedeeltelijk laden is een kernfunctie, geen latere optimalisatie. Een gebruiker
moet aan een beperkte selectie kunnen werken zonder alle geometrie te laden.

Als voorstel blijven van ongeladen objecten minstens identiteit, revisie,
begrenzing, plaatsing en tags bekend. Volledige geometrie wordt pas geladen wanneer
nodig. Hoe dit bij geneste objecten en gedeelde definities werkt, vraagt ontwerp.

Essentiële regel: een niet-geladen object is niet verwijderd en mag bij een commit
nooit impliciet als verwijderd worden beschouwd.

Multitagging kan selecties ondersteunen op bijvoorbeeld verdieping, discipline,
bouwfase en zone. In de oude proef werden tags ook voor versies en alternatieven
gebruikt. Voor de nieuwe opzet is voorgesteld tags voor ordening en selectie te
gebruiken, en commits of projecttakken voor ontwerpgeschiedenis. Die scheiding is
nog geen definitieve keuze.

## Samenwerken zonder verplichte locks

De gewenste richting is vrij lokaal bewerken en conflicten herkennen bij het
samenbrengen van wijzigingen. De applicatie kan eventueel tonen wie aan een object
werkt. Tijdelijke exclusieve reserveringen zijn als optionele mogelijkheid
besproken, maar niet als vereiste en niet als besluit.

Het voorgestelde samenvoegprincipe vergelijkt drie toestanden:

1. De gezamenlijke uitgangsversie.
2. De eigen wijzigingen.
3. De wijzigingen van de andere gebruiker of gedeelde geschiedenis.

| Situatie | Beoogd gedrag, nog te specificeren |
| --- | --- |
| Verschillende onafhankelijke objecten gewijzigd | Wijzigingen combineren |
| Eén object verplaatst en onafhankelijk een tag toegevoegd | Vaak automatisch combineerbaar |
| Dezelfde geometrie verschillend gewijzigd | Conflict herkennen en visueel oplossen |
| Object verwijderd terwijl iemand het wijzigt | Expliciete keuze vragen |
| Definitie gewijzigd terwijl een plaatsing wordt gewijzigd | Afhankelijkheden controleren |

Verschillende objectidentiteiten betekenen niet altijd onafhankelijke wijzigingen:
gedeelde definities, nesting en andere relaties kunnen gevolgen buiten het bewerkte
object hebben. Ook dat moet het samenvoegmodel meenemen.

Voor visuele conflictcontrole zijn het oorspronkelijke object, de eigen versie
en de andere versie naast elkaar of over elkaar voorgesteld. Mogelijke keuzes zijn
één versie behouden, beide als alternatief bewaren of afzonderlijke eigenschappen
combineren. Sommige geometriewijzigingen zouden later echt samengevoegd kunnen
worden, maar automatische geometrische merges zijn geen veronderstelde garantie.

## Opslag, transport en het idee van één bestand

De bespreking onderscheidt drie zaken:

- Het modelcontract: de betekenis en regels van de gegevens.
- De opslagvorm: hoe objecten en geschiedenis fysiek bewaard worden.
- Het transport: hoe wijzigingen andere gebruikers bereiken.

Eerst werd een container met een centrale projectdienst voorgesteld. De gebruiker
wees vervolgens op de bewezen werking van de vroegere Dropbox-map. Daarop is het
voorstel bijgesteld: een centrale dienst is niet noodzakelijk voor een eerste
verkenning. Een objectmap is een serieuze kandidaat voor samenwerking.

Eén bestand voor uitwisseling hoeft niet dezelfde fysieke vorm te hebben als een
actief project tijdens samenwerking.

| Gebruik | Besproken mogelijkheid |
| --- | --- |
| Samenwerken via Dropbox | Projectmap met objectversies en commits |
| Lokaal snel zoeken en laden | Eigen SQLite-index of cache |
| Uitwisselen of archiveren | Eén verpakt containerbestand |
| Eventuele latere centrale samenwerking | Dienst die dezelfde modelregels gebruikt |

SQLite is een mogelijke lokale opslagtechniek en applicatiecontainer. SQL is de
vraagtaal, niet het eigen modelcontract. Geen database, containertechniek,
bestandsextensie of serverarchitectuur is gekozen.

## Kandidaat: onveranderlijke objectversies en commits in Dropbox

Het laatste voorstel in de bespreking was om voort te bouwen op de historische
objectmap, maar bestaande objectversies niet te overschrijven. Elke wijziging
voegt een nieuwe, uniek geïdentificeerde objectversie toe. Elke commit wordt
eveneens als nieuw bestand vastgelegd.

Illustratieve indeling, geen specificatie of gekozen extensie:

```text
School.modelshare/
    project.json
    objects/
        raam-A/
            versie-001
            versie-002
        deur-B/
            versie-001
    commits/
        commit-abc.json
        commit-def.json
```

Een commit verwijst naar zijn uitgangscommit(s) en beschrijft toegevoegde,
gewijzigde en verwijderde objecten. Meerdere objectwijzigingen kunnen één
samenhangende ontwerpwijziging vormen. De nummering hierboven dient alleen om het
voorbeeld te lezen; onafhankelijke schrijvers mogen geen botsende versienummers
genereren. De identiteitstechniek moet later worden gekozen.

Dropbox verspreidt de bestanden. ModelShare interpreteert de geschiedenis en
lost modelconflicten op. Bij twee wijzigingen aan hetzelfde object blijven beide
versies bestaan; hun afkomst maakt het conflict herkenbaar.

Daarbij zijn de volgende ontwerpvoorwaarden besproken:

- Pas een commit pas toe zodra alle benodigde bestanden ontvangen en op
  volledigheid en integriteit gecontroleerd zijn. Een commitbestand kan eerder
  aankomen dan zijn geometriebestanden.
- Laat gelijktijdige commits naast elkaar bestaan en registreer het samenvoegen
  als een volgende commit.
- Vermijd één gezamenlijk bestand met de steeds overschreven “laatste versie”.
  Hoe actuele projecttakken worden ontdekt en aangewezen, staat nog open.
- Leg verwijderingen expliciet in de geschiedenis vast; verwijder niet simpelweg
  de oude objectversies die andere commits nog nodig hebben.
- Specificeer ook hoe veranderlijke projectmetadata worden bijgewerkt. Het
  illustratieve `project.json` is nog geen oplossing voor gelijktijdige wijzigingen.

Zonder centrale coördinatie kan een gebruiker niet weten of alle commits van
anderen al ontvangen zijn. Offline committen en later synchroniseren zijn mogelijk
in deze voorgestelde opzet, maar een onmiddellijk wereldwijd actuele toestand is
niet gegarandeerd. Na ontvangst en eventuele conflictresolutie moeten gebruikers
tot dezelfde modeltoestand kunnen komen; hoe dat betrouwbaar gebeurt vraagt
specificatie en validatie.

Dropbox kan conflictkopieën maken wanneer gebruikers hetzelfde bestand wijzigen.
Onveranderlijke, uniek benoemde bestanden verminderen dat specifieke probleem;
ze lossen niet automatisch modelconflicten, onvolledige ontvangst of andere
synchronisatiefouten op.

Een voortdurend gewijzigd gedeeld SQLite-bestand via Dropbox is daarom niet de
voorgestelde eerste richting. Rechtstreeks een database openen op een
netwerkbestandsysteem is bovendien een ander scenario dan lokale Dropbox-kopieën:
bij het eerste zijn netwerklocking en databaseconsistentie een aandachtspunt;
bij het tweede het verspreiden en samenbrengen van afzonderlijk gewijzigde kopieën.

## Relatie met de huidige synchronisatie

De aanleiding voor de brainstorm is mede het synchronisatieprobleem van
SiteRef for SketchUp. Een gedeeld model met vaste identiteiten, bekende
uitgangsrevisies en expliciete wijzigingen kan daarvoor een structurele richting
zijn. Het verplaatst de synchronisatie naar een gemeenschappelijk modelcontract.

De huidige koppeling bevat aanknopingspunten zoals geometriewijzigingen,
objectpaden en componenthergebruik. Daarmee is ModelShare echter nog niet
geïmplementeerd. Deze brainstorm bewijst ook niet dat het huidige concrete
synchronisatieprobleem hiermee al opgelost is.

## Mogelijke eerste proef, uitsluitend voor later

Als het concept later voldoende uitgewerkt is, werd deze beperkte proef genoemd:

1. Open één klein project met geneste objecten in SketchUp en
   SiteRef for ingeTrezo.
2. Wijzig verschillende onafhankelijke objecten en combineer de commits.
3. Wijzig hetzelfde object vanuit twee werkkopieën en los het conflict visueel op.
4. Laat een object ongeladen en controleer dat het behouden blijft.
5. Controleer heen-en-terugvertaling zonder bewerking en daarna met een gerichte
   wijziging, inclusief behoud van onbekende eigenschappen.

Dit is een mogelijke toets van het concept, geen huidige bouwopdracht.

## Open vragen voor de volgende ontwerpsessie

- Welke geometrische representatie is leidend, met welke eenheden, precisie,
  topologie en regels voor geldigheid?
- Wat is de granulariteit van identiteit, revisies en samenvoegen: object,
  definitie, plaatsing, vlak, rand of eigenschap?
- Hoe blijven identiteiten behouden bij kopiëren, splitsen, samenvoegen,
  uniek maken, opnieuw importeren en wijzigen van nesting?
- Hoe herkennen adapters werkelijke wijzigingen zonder verschillen door
  afronding of herordening telkens als edits te publiceren?
- Welke eigenschappen zijn gedeeld en welke blijven lokaal? Hoe blijven lokale
  scenes en objectverwijzingen bruikbaar na updates of verwijderingen?
- Hoe worden lokale wijzigingen bewaard, teruggedraaid en hersteld? Wat betekent
  undo vóór en na een commit?
- Hoe werkt een commit op een gedeeltelijk geladen model met gedeelde definities?
- Hoe worden projecttakken, alternatieven, tags en uiteengevallen geschiedenissen
  voorgesteld en ontdekt?
- Welke conflicten kunnen automatisch worden gecombineerd, en welke moeten een
  gebruiker beoordelen? Hoe voorkomen we herhaalde tegenstrijdige mergebesluiten?
- Hoe worden bestanden atomair gepubliceerd, gecontroleerd en opnieuw opgehaald
  na onderbroken of onvolledige synchronisatie?
- Hoe blijft een grote geschiedenis beheersbaar: indexering, caches, ophalen op
  aanvraag, archivering en veilig opruimen van oude gegevens?
- Welke structuur maakt een project draagbaar als één containerbestand, en hoe
  verhoudt die momentopname zich tot de actieve gedeelde map?
- Hoe krijgen een webviewer of andere adapters toegang tot dezelfde geschiedenis
  wanneer ze niet rechtstreeks met een lokale Dropbox-map werken?
- Welke formaatversies, adaptermogelijkheden en migratieregels zijn nodig?
- Wanneer volstaat Dropbox en wanneer is centrale coördinatie wenselijk?

## Bronnen bij de technische verkenning

De historische ModelShare-werking en de gewenste werkwijze zijn door de gebruiker
beschreven. De architectuur hierboven is een voorstel uit deze bespreking.
Onderstaande documentatie ondersteunt specifieke technische aandachtspunten,
niet een claim dat de voorgestelde architectuur al gevalideerd is.

- [SketchUp: ComponentDefinition](https://ruby.sketchup.com/Sketchup/ComponentDefinition.html)
  en [ComponentInstance](https://ruby.sketchup.com/Sketchup/ComponentInstance.html):
  onderscheid tussen componentinhoud en plaatsingen.
- [Dropbox: conflicted copies](https://help.dropbox.com/organize/conflicted-copy):
  conflictkopieën bij gelijktijdige wijzigingen aan hetzelfde bestand.
- [SQLite als applicatiebestandsformaat](https://www.sqlite.org/appfileformat.html):
  mogelijkheden van SQLite als lokale container.
- [SQLite over een netwerk](https://www.sqlite.org/useovernet.html):
  aandachtspunten bij rechtstreeks databasegebruik via netwerkbestandsystemen.
