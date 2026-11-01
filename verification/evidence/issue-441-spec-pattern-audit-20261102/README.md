<!-- doc: role=retained issue 441 existing specimen foil-pattern audit; stage=history -->

> Historical record — 2026-11-02; current values are determined by canonical stores.

# #441: Analyse vorhandener SPECs

Snapshot: `7827f857102a1788eaa6c7d38ec17e1773514c5f`. Die 57 offenen Einheiten betreffen **Folienmuster von Reverse-/Mirror-Holo-Ausführungen**; nicht jede Karte hat einen unbekannten technischen Finish.

Geprüft: **100 direkt/über explizite Brücken zugehörige SPEC-Datensätze mit 92 Bildern**, zusätzlich **vier koreanische sv2a-Vergleichs-SPECs mit vier Bildern**. Acht Datensätze besitzen kein gespeichertes Bild. Sämtliche 96 vorhandenen Bildhashes stimmen mit dem Register überein. Die vollständige Zuordnung und Einzel-SPEC-Prüfspur stehen in [review.json](review.json).

## Owner-Klarstellung und umgesetzte Korrektur

Der Owner hat die Grundannahme dieses Audits korrigiert: **Holo und Reverse Holo
brauchen keinen besonderen Musternamen, um vollständig bestimmt zu sein.** Die
folgende Tabelle dokumentiert den damaligen Prüfansatz; ihre Formulierungen über
„offene Reverse-Kandidaten“ belegen keine zusätzlichen physischen Ausführungen.
Von den 66 damals unbenannten Reverse-/Mirror-Zeilen waren 47 nur Marketplace-Claims
und 19 positiv bestätigt. Die 57 Einheiten sind daher keine Liste von 57 belegten
Spezialmustern, die noch benannt werden müssten.

Die Statuslogik verlangt jetzt keinen `foilPattern`-Wert mehr. Benannte Muster bleiben
erhalten; unbenannte Oberflächen erzeugen keine künstliche Muster-Suchaufgabe.
Ein fehlender Name wird dabei weder in „plain foil“ umbenannt noch als Nachweis einer
fehlenden Variante gewertet. Technische Finish-Evidenz und Printing-Identitäten
bleiben erhalten. Die Bildbeobachtung zu SPEC-0579 erfordert keine Benennung, um die
bereits bestätigte Reverse-Holo-Ausführung als solche gelten zu lassen.

## Historischer Bildbefund

- **Japanisch sv4a 145/190, SPEC-0579:** sichtbarer Kandidat für ein quadratisches Mosaikmuster im Artwork. Das ist eine deskriptive Bildbeobachtung, kein belegter offizieller Mustername. Die PSA-Finishbestätigung und der visuelle Musterbefund bleiben getrennt. Noch keine kanonische Aufnahme oder zusätzliche Printing-Identität erzeugt.
- **Koreanisch sv2a 143/165:** bereits bekannte Poké-/Master-Ball-SPECs existieren. SPEC-0617 bleibt in seinem genauen Ball-Untertyp unklar; Nachbarkopien lösen seine Zuordnung nicht.
- **CSM2bC 124 und japanisch mC 568:** PR #457 bearbeitet bereits die relevante Zusammenführung bzw. neue Fotoevidenz. Dieser Audit verdoppelt weder diese Arbeit noch die SPEC-IDs.
- Viele übrige Bilder belegen eine normale/Artwork-Holo-Geschwisterausführung oder sind Stockdarstellungen. Sie schließen die separate Reverse-/Mirror-Frage nicht. Kein offener Eintrag wird auf Abwesenheit entschieden.

Die Bildprüfung selbst ändert keine Evidenz. Die anschließend korrigierte Statuslogik beseitigt die unbegründete Pflicht, jeder Reverse-/Mirror-Oberfläche einen Musternamen zu geben. Die Tabelle bleibt ein historischer Bildbefund, keine aktive Aufgabenliste.

## Alle 57 ursprünglich aufgeführten Einheiten

| Finish-Einheit | Karte / Sprache | Geprüfte SPECs | Befund / noch fehlender Nachweis |
|---|---|---|---|
| F0000 | 151C 143 / S-Chinese | [SPEC-0667](../../specimens/SPEC-0667.png) | SPEC-0667 ist eine Stockdarstellung mit Master-Ball-Symbol. Kein belastbarer Nachweis der physischen Oberfläche. |
| F0002 | 20th 047 / Japanese | [SPEC-0195](../../specimens/SPEC-0195.jpg), [SPEC-0588](../../specimens/SPEC-0588.png) | SPEC-0195 ist eine Referenzansicht; SPEC-0588 ist ausdrücklich als Non-Holo vom Owner bestimmt. Kein Musterbeleg für die offene Reverse-Ausführung. |
| F0003 | 20th 047 / Korean | [SPEC-0629](../../specimens/SPEC-0629.jpg) | Referenzansicht; gedruckte Pastelltöne reichen nicht als Foliennachweis. |
| F0025 | BW-P 207 / Japanese | [SPEC-0196](../../specimens/SPEC-0196.jpg), [SPEC-0521](../../specimens/SPEC-0521.jpg) | SPEC-0521 zeigt die vom Owner als Non-Holo bestimmte Plasma-Karte. Die offene Reverse-Ausführung ist dadurch nicht belegt. |
| F0037 | CLF 016 / T-Chinese | [SPEC-0319](../../specimens/SPEC-0319.jpg), [SPEC-0320](../../specimens/SPEC-0320.jpg), [SPEC-0321](../../specimens/SPEC-0321.jpg), [SPEC-0322](../../specimens/SPEC-0322.jpg) | Die vier Ansichten zeigen die bereits als Holo dokumentierte Ausführung. Glitzer im Artwork/Rahmen darf nicht auf die separate offene Mirror-Ausführung übertragen werden. |
| F0051 | CS1aC 110 / S-Chinese | [SPEC-0664](../../specimens/SPEC-0664.png) | SPEC-0664 zeigt Stern-/Typensymbole in einer kleinen Referenzdarstellung. Physisches Muster bleibt unbestätigt. |
| F0060 | CS5aC 093 / S-Chinese | [SPEC-0669](../../specimens/SPEC-0669.png) | SPEC-0669 zeigt die bereits bekannte Mirror-Ausführung mit vertikalen Linien. Die zusätzliche offene Reverse-Ausführung bleibt ohne Musterbeleg. |
| F0063 | CS6bC 113 / S-Chinese | [SPEC-0665](../../specimens/SPEC-0665.png) | Referenzdarstellung mit Artwork-Effekt; kein Beleg für ein eigenständiges Reverse-Muster. |
| F0067 | CSM2bC 124 / S-Chinese | [SPEC-0433](../../specimens/SPEC-0433.png), [SPEC-0434](../../specimens/SPEC-0434.png) | SPEC-0434 trägt bereits large-type-symbol-left. Der ungemusterte Marketplace-Eintrag ist ein Zuordnungskandidat; PR #457 bearbeitet genau diese Zusammenführung. |
| F0074 | CSV10C 175 / S-Chinese | [SPEC-0666](../../specimens/SPEC-0666.png) | Stockdarstellung mit großem Poké-Ball-Motiv; keine unabhängig lesbare physische Folienoberfläche. |
| F0075 | CSV5C 115 / S-Chinese | [SPEC-0668](../../specimens/SPEC-0668.png) | Zusammengesetzte Stockdarstellung mit Poké-/Master-Ball-Versionen. Kein neuer physischer Nachweis für die offenen Ausführungen. |
| F0076 | CSV7C 158 / S-Chinese | keine | Kein passender SPEC im geprüften Bestand vorhanden. |
| F0083 | CSZC 018 / S-Chinese | [SPEC-0149](../../specimens/SPEC-0149.jpg), [SPEC-0150](../../specimens/SPEC-0150.jpg) | SPEC-0149 belegt bereits die bekannte mehrfarbige Glitzeroberfläche; SPEC-0150 ist die Rückseite. Kein Beleg für das zusätzliche offene Reverse-Muster. |
| F0208 | m2a 136 / Japanese | keine | Kein passender SPEC im geprüften Bestand vorhanden. |
| F0219 | mC 568 / Japanese | [SPEC-0663](../../specimens/SPEC-0663.jpg) | SPEC-0663 ist eine flache Referenzansicht. PR #457 führt einen neuen physischen Nachweis ein; dieser gehört nicht zum geprüften Main-Snapshot. |
| F0220 | mC 568 / Korean | [SPEC-0459](../../specimens/SPEC-0459.png), [SPEC-0614](../../specimens/SPEC-0614.png), [SPEC-0615](../../specimens/SPEC-0615.png) | Die Ansichten und Detailaufnahme reichen nicht für ein sicher benennbares Motiv der offenen Reverse-Ausführung. |
| F0221 | mC 568 / T-Chinese | [SPEC-0315](../../specimens/SPEC-0315.png), [SPEC-0318](../../specimens/SPEC-0318.png), [SPEC-0503](../../specimens/SPEC-0503.png), [SPEC-0555](../../specimens/SPEC-0555.png) | Referenz-/Katalogansichten und bestehende Finish-Attestierung. Farbverlauf allein bestimmt kein exaktes Muster. |
| F0258 | PKMTCH S-P S-P 145 / T-Chinese | [SPEC-0030](../../specimens/SPEC-0030.png), [SPEC-0292](../../specimens/SPEC-0292.png) | SPEC-0030 ist eine physische Mirror-Aufnahme. Dunkle Reflexion und feine Körnung sind sichtbar; ein benennbares wiederholtes Motiv ist nicht sicher lesbar. Nicht als plain-foil aus bloßer Motiv-Abwesenheit klassifizieren. |
| F0301 | Pt2 070 / Japanese | [SPEC-0230](../../specimens/SPEC-0230.jpg), [SPEC-0571](../../specimens/SPEC-0571.jpg), [SPEC-0582](../../specimens/SPEC-0582.png), [SPEC-0635](../../specimens/SPEC-0635.jpg), [SPEC-0636](../../specimens/SPEC-0636.jpg) | Mehrere Referenz-/Detailansichten geprüft. Kein sicher lesbares Muster, das die offene Reverse-Ausführung eindeutig bestimmt. |
| F0324 | s10a 058 / Japanese | [SPEC-0206](../../specimens/SPEC-0206.jpg) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0325 | s10a 058 / Korean | [SPEC-0236](../../specimens/SPEC-0236.png), [SPEC-0451](../../specimens/SPEC-0451.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0326 | s10a 058 / T-Chinese | [SPEC-0295](../../specimens/SPEC-0295.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0327 | s10a 058 / Indonesian | [SPEC-0174](../../specimens/SPEC-0174.png), SPEC-0369 (ohne Bild), [SPEC-0550](../../specimens/SPEC-0550.jpg), [SPEC-0560](../../specimens/SPEC-0560.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0328 | s10a 058 / Thai | [SPEC-0264](../../specimens/SPEC-0264.png), SPEC-0368 (ohne Bild) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0351 | s2 77 / Japanese | [SPEC-0209](../../specimens/SPEC-0209.jpg), [SPEC-0574](../../specimens/SPEC-0574.png), [SPEC-0591](../../specimens/SPEC-0591.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0352 | s2 77 / Korean | [SPEC-0239](../../specimens/SPEC-0239.png), [SPEC-0455](../../specimens/SPEC-0455.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0354 | s4 84 / Japanese | [SPEC-0210](../../specimens/SPEC-0210.jpg) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0355 | s4 84 / Korean | [SPEC-0240](../../specimens/SPEC-0240.png), [SPEC-0456](../../specimens/SPEC-0456.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0356 | s4 84 / T-Chinese | [SPEC-0278](../../specimens/SPEC-0278.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0358 | s5a 93 / Japanese | [SPEC-0211](../../specimens/SPEC-0211.jpg) | Die gezeigte Karte ist die goldene reguläre Holo-Ausführung. Sie bestimmt nicht das Muster des separaten Reverse-Kandidaten. |
| F0359 | s5a 93 / Korean | [SPEC-0552](../../specimens/SPEC-0552.png) | Die gezeigte Karte ist die goldene reguläre Holo-Ausführung. Sie bestimmt nicht das Muster des separaten Reverse-Kandidaten. |
| F0360 | s5a 93 / T-Chinese | [SPEC-0489](../../specimens/SPEC-0489.png) | Die gezeigte Karte ist die goldene reguläre Holo-Ausführung. Sie bestimmt nicht das Muster des separaten Reverse-Kandidaten. |
| F0361 | s5a 93 / Indonesian | [SPEC-0519](../../specimens/SPEC-0519.png) | Die gezeigte Karte ist die goldene reguläre Holo-Ausführung. Sie bestimmt nicht das Muster des separaten Reverse-Kandidaten. |
| F0362 | s5a 93 / Thai | SPEC-0362 (ohne Bild), [SPEC-0523](../../specimens/SPEC-0523.png) | Die gezeigte Karte ist die goldene reguläre Holo-Ausführung. Ein weiterer SPEC hat kein gespeichertes Bild. Kein Musterbeleg für den separaten Reverse-Kandidaten. |
| F0363 | s8b 126 / Japanese | [SPEC-0212](../../specimens/SPEC-0212.jpg), [SPEC-0610](../../specimens/SPEC-0610.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0364 | s8b 126 / Korean | [SPEC-0241](../../specimens/SPEC-0241.png), [SPEC-0453](../../specimens/SPEC-0453.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0365 | s8b 126 / T-Chinese | [SPEC-0291](../../specimens/SPEC-0291.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0366 | s8b 126 / Indonesian | [SPEC-0169](../../specimens/SPEC-0169.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0367 | s8b 126 / Thai | [SPEC-0261](../../specimens/SPEC-0261.png), SPEC-0359 (ohne Bild), [SPEC-0597](../../specimens/SPEC-0597.png) | Referenz-/reguläre Artwork-Holo-Ansichten geprüft. Sichtbare Artwork-Linien bzw. Glanz gehören nicht automatisch zum Muster des separaten offenen Reverse-Kandidaten. |
| F0368 | sA 10 / Japanese | [SPEC-0213](../../specimens/SPEC-0213.jpg) | Flache Normal-/Katalogansicht; kein sicher lesbares Mirror-Motiv. |
| F0375 | sI100 341 / Japanese | [SPEC-0215](../../specimens/SPEC-0215.jpg), [SPEC-0593](../../specimens/SPEC-0593.png) | Normal-/Referenzansichten bzw. bestehende Non-Holo-Beobachtungen. Keine dieser Ansichten bestimmt das Muster des offenen Reverse-Kandidaten. |
| F0376 | sI100 341 / Korean | [SPEC-0242](../../specimens/SPEC-0242.png) | Normal-/Referenzansichten bzw. bestehende Non-Holo-Beobachtungen. Keine dieser Ansichten bestimmt das Muster des offenen Reverse-Kandidaten. |
| F0377 | sI100 341 / T-Chinese | [SPEC-0293](../../specimens/SPEC-0293.png), [SPEC-0499](../../specimens/SPEC-0499.png) | Normal-/Referenzansichten bzw. bestehende Non-Holo-Beobachtungen. Keine dieser Ansichten bestimmt das Muster des offenen Reverse-Kandidaten. |
| F0378 | sI100 341 / S-Chinese | [SPEC-0155](../../specimens/SPEC-0155.png) | SPEC-0155 zeigt eine reflektierende Kartenfläche; kein wiederholtes Motiv sicher auflösbar. Gedruckte Pastellflächen nicht als Folienmuster lesen. |
| F0379 | sI100 342 / Japanese | [SPEC-0216](../../specimens/SPEC-0216.jpg), [SPEC-0592](../../specimens/SPEC-0592.png) | Normal-/Referenzansichten bzw. bestehende Non-Holo-Beobachtungen. Keine dieser Ansichten bestimmt das Muster des offenen Reverse-Kandidaten. |
| F0380 | sI100 342 / Korean | [SPEC-0243](../../specimens/SPEC-0243.png) | Normal-/Referenzansichten bzw. bestehende Non-Holo-Beobachtungen. Keine dieser Ansichten bestimmt das Muster des offenen Reverse-Kandidaten. |
| F0381 | sI100 342 / T-Chinese | [SPEC-0294](../../specimens/SPEC-0294.png) | Normal-/Referenzansichten bzw. bestehende Non-Holo-Beobachtungen. Keine dieser Ansichten bestimmt das Muster des offenen Reverse-Kandidaten. |
| F0382 | sI100 342 / S-Chinese | [SPEC-0156](../../specimens/SPEC-0156.png) | SPEC-0156 ist bereits als Holo beobachtet. Daraus folgt kein Muster für die offene Reverse-Ausführung. |
| F0402 | sm10 076 / Japanese | [SPEC-0414](../../specimens/SPEC-0414.png) | Ansichten zeigen die reguläre Artwork-Holo-Ausführung. Kein sicher zugeordneter Musterbeleg für den separaten Reverse-Kandidaten. |
| F0403 | sm10 076 / Korean | [SPEC-0248](../../specimens/SPEC-0248.png), [SPEC-0415](../../specimens/SPEC-0415.png) | Ansichten zeigen die reguläre Artwork-Holo-Ausführung. Kein sicher zugeordneter Musterbeleg für den separaten Reverse-Kandidaten. |
| F0462 | sv2a 143 / Korean | [SPEC-0617](../../specimens/SPEC-0617.png) | SPEC-0617 zeigt wiederholte Ballformen, aber kein sicher lesbares Master-Ball-M. Vier zusätzliche xsv2a-SPECs bestätigen bereits bekannte Poké-/Master-Ball-Kopien; keine davon identifiziert die Oberfläche dieser Kopie. |
| F0471 | sv4a 145 / Japanese | [SPEC-0219](../../specimens/SPEC-0219.jpg), [SPEC-0575](../../specimens/SPEC-0575.png), [SPEC-0579](../../specimens/SPEC-0579.jpg), [SPEC-0580](../../specimens/SPEC-0580.jpg) | SPEC-0579 zeigt im Original wiederholte quadratische Mosaikflächen im Artwork (visueller Musterkandidat). PSA 94474867 benennt Reverse Holo, aber keinen exakten Musternamen. SPEC-0580 ist dieselbe Kartenrückseite. Noch keine kanonische Musterannahme: deskriptive Benennung und eindeutige Bindung an die vorhandene PSA-Ausführung getrennt prüfen. |
| F0472 | sv4a 145 / Korean | [SPEC-0624](../../specimens/SPEC-0624.png) | SPEC-0624 zeigt drei Karten. Die mittlere koreanische Karte hat eine geometrisch reflektierende Oberfläche; kleine/überlappende Ansicht reicht nicht zur sicheren Motivbestimmung. Japanische Nachbarkarte nicht übertragen. |
| F0473 | sv4a 145 / T-Chinese | [SPEC-0302](../../specimens/SPEC-0302.png), [SPEC-0500](../../specimens/SPEC-0500.png) | Ansichten reichen nicht zur sicheren Bestimmung eines wiederholten Musters der offenen Reverse-Ausführung. |
| F0474 | sv4a 145 / Indonesian | [SPEC-0179](../../specimens/SPEC-0179.png), SPEC-0381 (ohne Bild), SPEC-0382 (ohne Bild), [SPEC-0562](../../specimens/SPEC-0562.png) | SPEC-0562 ist eine Darstellung mit Pixel-/Glitzereffekten und bestehender Finish-Attestierung, kein eigenständiger fotografischer Musterbeleg. Zwei weitere SPECs ohne Bild. |
| F0475 | sv4a 145 / Thai | [SPEC-0269](../../specimens/SPEC-0269.png), SPEC-0379 (ohne Bild), SPEC-0380 (ohne Bild), [SPEC-0527](../../specimens/SPEC-0527.jpg) | SPEC-0527 zeigt eine reflektierende Fläche, aber kein sicher isolierbares Motiv. Feine Diagonalstrukturen können Aufnahme-/Druckraster sein. Japanisches Mosaik nicht übertragen. Zwei SPECs ohne Bild. |
| F0622 | XY-P 261 / Japanese | [SPEC-0223](../../specimens/SPEC-0223.jpg) | Die bekannte gesprenkelte Holo-Oberfläche ist eine andere Ausführung. Sie bestimmt nicht das offene Reverse-Muster. |

## Vergleichs-SPECs und Grenzen

Zusätzlich separat geprüft: SPEC-0061, SPEC-0612, SPEC-0659, SPEC-0660 (koreanisches xsv2a 143/165; bekannte Varianten). Bestehende Same-card-Gruppenverweise wurden als Kontext gelesen, nicht als zusätzliche unbekannte Ausführungen gezählt.

Dies ist ein eingefrorener Bild-/Metadaten-Audit, keine neue Webrecherche oder physische Inspektion. Kontaktbögen dienten der vollständigen Sichtung; ausgewählte schwierige Bilder wurden zusätzlich im Original geöffnet. Kein Tesseract verfügbar. Bei flachen Scans, kleinen Bildern oder unbekanntem Aufnahmewinkel bleibt das Muster offen. Stockeffekte sind höchstens Recherchehinweise. Die anschließende Owner-Klarstellung ändert ausschließlich die Statuslogik und daraus generierte Ausgaben; keine Finish-Evidenz oder Owner-Abwesenheitsentscheidung wurde umgedeutet.
