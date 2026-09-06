<!-- doc: role=independent repository audit and implementation handoff; stage=reference -->
# ASTRA — unabhängige Prüfung von Snoredex-Data

**Audit:** 2026-09-06. **Umsetzung:** später durch 5.6 Luna Max.

Dieser Bericht dokumentiert Beobachtungen und vorgeschlagene Änderungen. Er setzt nichts davon um und ersetzt weder `CLAUDE.md` noch einen Datenvertrag. Alle Befunde beziehen sich auf den unten festgehaltenen Stand. Die ursprüngliche Aufgabenstellung wurde aus dem ersten Commit und den maßgeblichen Issues rekonstruiert; ein vollständiges ursprüngliches Chatprotokoll liegt im Repository nicht vor.

## 1. Gesamturteil

**Die fachliche Grundlage ist gut, die Umsetzung hat jedoch erhebliche Schwächen an ihren Schnittstellen.** Das Repository bewahrt Quellen, trennt Sprache und Finish, unterscheidet Widerspruch von entschiedener Abwesenheit und lässt offene Fragen sichtbar. Diese Komplexität ist überwiegend durch reale Eigenschaften der Karten und durch konkrete frühere Fehler begründet.

Weniger gut gelöst sind die Autoritätsgrenzen zwischen gespeicherten Eingaben und erzeugten Ansichten, die einheitliche Sammlersemantik und einige Prüf- und Schreibpfade. Es gibt reproduzierbare Fehler trotz grüner Tests: Ein Wort im Quellenbeschreibungstext kann eine unzureichend belegte Bestätigung aufwerten; zwei Identitätsfunktionen behandeln die Reihenfolge von Markierungen unterschiedlich; ein fehlgeschlagener Graph-Schreibvorgang hinterlässt ungültige Daten; vermeintliche Prüfmodi überschreiben oder löschen Dateien. Die Browseroberfläche kann Eingaben verlieren und trotzdem eine lokale Speicherung melden.

**Kein Neuentwurf ist erforderlich.** Zuerst müssen diese konkreten Fehler behoben werden. Danach lohnen sich wenige gezielte Vereinfachungen: eine gemeinsame Druckidentität, eindeutige Zuständigkeit für kanonische Daten, eine konsistente Sammleransicht, weniger wiederholte Parserarbeit und eine bei Bedarf aufgebaute Artwork-Oberfläche. Zusätzliche Frameworks, Dienste, generische Workflow-Engines oder eine Aufteilung in sehr viele kleine Module wären derzeit keine angemessene Antwort.

Ein grüner Gate beweist hier eine umfangreiche, aber begrenzte Menge an Eigenschaften. Er beweist weder historische Vollständigkeit noch, dass alle fachlichen Aussagen unabhängig erneut recherchiert wurden, noch die Fehlerfreiheit der nicht getesteten Fehlerszenarien.

## 2. Prüfstand und Grenzen

| Merkmal | Geprüfter Stand |
|---|---|
| Branch | `codex/issue-256-dpp126-work-mapping` |
| HEAD | `7cc60230db0e6bbc5f9ea09e8fb589dfac1f377f` |
| Nach `git fetch origin`: `origin/main` | `4f5e58d6643f2b38bf1ebb5b6cfed7f8e356122d` |
| Vergleich | HEAD ist einen Merge-Commit hinter `origin/main`; beide enthalten denselben Dateibaum |
| Gemeinsamer Tree | `953f2aeb77712a109fa7b8199bc51b8074630456` |
| Ausgangszustand | Sauberer Arbeitsbaum; keine vorgefundenen Änderungen |
| Lokale Laufzeit | Windows, Python 3.12.10; CI konfiguriert Python 3.11 |
| Geänderte Repository-Dateien durch dieses Audit | Nur `ASTRA.md` |

Es wurde kein Branch gewechselt, keine Umsetzung begonnen, kein Issue erstellt und nichts veröffentlicht. Temporäre Reproduktionen, Browserprofile, Screenshots, Laufzeitprotokolle und ein Test-Publikationsartefakt lagen außerhalb des Repositorys. Fehlerfälle wurden mit Kopien oder Eingaben im Speicher geprüft. Die produktiven Zustandsdateien wurden dafür nicht geändert.

Die Prüfung umfasste:

- Zielentwicklung anhand des ersten Commits, der aktuellen Dokumentation, ADRs und der Issues #7, #132, #229, #254 und #285;
- Inventarisierung des gesamten versionierten Baums, Syntaxprüfung aller 144 Python-Dateien und Komplexitätsmessung sämtlicher 43 aktiven Python-Dateien;
- Nachverfolgung von Rohbelegen über Status, Finish, Graph und Projektionen bis zu SQLite, Tracker, Website und Veröffentlichung;
- vollständigen vorhandenen Offline-Gate, Browser-Suite, begrenzte Live-Quellenprüfung und Publikationsprüfung;
- gezielte manuelle Codeprüfung der maßgeblichen Identitäts-, Beweis-, Schreib-, Prüf-, Import-, Export-, Browser- und Orchestrierungsfunktionen;
- zusätzliche negative Reproduktionen, die über den vorhandenen Gate hinausgehen;
- Browserprüfung per HTTP und über die vorhandene `file://`-Suite, einschließlich 320, 375, 768, 1440 und 1920 Pixel Breite.

**Grenzen:** Die 1.271 registrierten URLs wurden nicht sämtlich neu geöffnet und ihre Kartenbehauptungen nicht einzeln neu adjudiziert. Das ist eine eigene Rechercheaufgabe. Historische Pässe wurden als Provenienz und hinsichtlich ihrer Einordnung geprüft, nicht erneut ausgeführt. Nicht jede der 9.727 Dateien wurde Zeile für Zeile manuell gelesen. Die Prüfung des realen Ergebnisses erfolgte am lokalen, zu `origin/main` inhaltsgleichen Stand; ein Abgleich mit dem aktuell öffentlich ausgerollten Pages-Stand war nicht Teil dieses Audits. Es gab keinen zusätzlichen Lauf auf Linux oder Python 3.11 und keinen vollständigen Screenreader-Test.

## 3. Ursprüngliche Idee und heutiges Ergebnis

### 3.1 Entwicklung des Auftrags

Der erste Commit `c2cf236` vom 2026-07-23 beschreibt einen Cardmarket-Datensatz: Aus einer Suche mit 242 Produkten bleiben 198 Singles, ergänzt um Bilder, Künstler, Varianten und eine externe Überprüfung der Sprachbehauptungen. Schon dort steht die zentrale Erkenntnis: Marktverfügbarkeit ist kein Druckverzeichnis. Die damalige README enthält aber noch widersprüchliche Aussagen zu `KSS 26`; die spätere Evidenzdisziplin war also eine notwendige fachliche Verbesserung.

Die späteren Erweiterungen waren überwiegend ausdrücklich beauftragt:

| Auftrag | Heutige Umsetzung | Bewertung |
|---|---|---|
| Ausgangsidee: Cardmarket-Angaben überprüfen | Unveränderliche Kandidatengrenze, `units.json`, Quellenregister, Entscheidungen | Gut nachvollziehbar; die ursprüngliche Rohbehauptung bleibt erhalten |
| [#7: öffentliche statische Seite](https://github.com/m4s-ai/snoredex-data/issues/7) | Generator, Vanilla JS/CSS, Filter, Korrekturlinks, Druckansicht | Grundfunktion erfüllt; große Zusatzoberfläche und alte Sammlersemantik belasten das Ergebnis |
| [#132: source-first und Lokalität](https://github.com/m4s-ai/snoredex-data/issues/132) | Retained Runs, Discovery-Staging, Graph, Lokalitätsmatrizen, Completeness-Gate | Bedeutender Fortschritt; die begrenzte Eingangsmenge wird bilanziert, keine historische Vollständigkeit bewiesen |
| ADR-0007 / #120: Artwork-Prüfung | Statische Vorschläge mit Download und Browserablage | Nützliche Grundlage; Persistenz, Versionierung und Begriffe sind noch nicht zuverlässig genug |
| [#229: alltagstaugliche Sammlungsliste](https://github.com/m4s-ai/snoredex-data/issues/229), später [#254: Producer-Vertrag](https://github.com/m4s-ai/snoredex-data/issues/254) | `collector_catalogue.json`, Migrationen, Deployment-Manifest | Gute Trennung öffentlicher Katalogdaten und privater Sammlung; ältere Einstiegspunkte verwenden weiterhin andere Regeln |
| [#285: Workflow-DAG](https://github.com/m4s-ai/snoredex-data/issues/285) | `WORKFLOW-MAP.md`, zentraler Gate, Scoped Lanes, Messung und Loops | Die zentrale Reihenfolge hilft; Messung und Loop-Zustand besitzen eigene Fehler und überlappende Definitionen |

Die Entscheidung für Lokalitäten, stabile Druckidentitäten, getrennte Quellenbelege und einen Sammlervertrag ist keine bloße Überentwicklung. Die dokumentierten Fälle, etwa europäisches und lateinamerikanisches Spanisch oder unterschiedliche lokale Nummerierungen, erfordern diese Trennung. Problematisch ist, dass mehrere Generationen der Anwendung gleichzeitig als aktuelle Einstiegspunkte weiterleben.

Die historischen Issue-Texte enthalten teilweise inzwischen überholte Evidenzregeln. Für neue Arbeit gilt die aktuelle Regel in `CLAUDE.md`: Externe Quellen begründen keine Abwesenheit durch Auslassung; nur die ausdrücklich aufgezeichnete Eigentümerentscheidung kann eine solche Frage abschließen.

### 3.2 Aktuelle Daten, ohne vermischte Nenner

| Datenebene | Gemessener Inhalt |
|---|---:|
| Eingefrorene Produkte | 198, davon 191 sammelbare Produkte und 7 Codekarten |
| Legacy-Sprachclaims | 719: 629 roh bestätigt, 90 widersprochen |
| Anwendungssichere Sprachstatus | 618 `exists`, 11 `needs-evidence`, 86 `not-printed`, 4 `disputed` |
| Finish-Einheiten / logische Finish-Einträge | 637 / 843 |
| Alte physische Checkliste | 889 Einträge: 813 als dokumentiert gezählt, 76 Platzhalter |
| Neuer Sammlervertrag | 995 Einträge: 737 `verified-printing`, 112 `finish-candidate`, 146 `research-placeholder` |
| Neuer Sammlerfortschritt | 737 `current-known`, 258 `research` |
| Graph | 7.894 Entitäten, 11.793 Kanten, 2.755 Migrationsdispositionen |
| Graph-Kartenreleases / physische Drucke | 632 / 737 |
| Neuer Sammlervertrag: Stammdaten | 16 Lokalisierungen, 338 lokale Sets, 545 Set-Editionen, 41 Works |
| Quellenregister | 32 Provider, 1.278 Evidenzdatensätze, 1.271 unterschiedliche URLs |
| Noch ohne Künstler / physische V-Token-Benennung | 82 Produkte / 58 Produkte |
| Release-Zeilen ohne Quelle auf Zeilenebene | 141 von 203 |

Die 889 und 995 sind keine widersprüchlichen Summen derselben Menge. Die Projektionen besitzen unterschiedliche Reichweite und unterschiedliche Behandlung von Kandidaten. **Die Zahl 813 darf insbesondere nicht als 813 positiv bestätigte physische Drucke gelesen werden:** Darin stecken 111 `marketplace-claimed` und ein `owner-attested` Finish. F06 beschreibt die Konsequenz für den bestehenden Tracker.

Quellen für diese Tabelle: [Datenübergabe-Audit](verification/DATA-HANDOFF-AUDIT.md), [Collector-Katalog](collector_catalogue.json), [alte Checkliste](analysis_checklist.json), [Evidenzsemantik](verification/evidence_semantics.json) und direkte lesende SQLite-Abfragen.

### 3.3 Tatsächlicher Datenfluss

```text
Legacy-Kandidaten + geprüfte Belege + Entscheidungen
             |                         |
             v                         v
    Sprachsemantik             Finish-Projektion
             |                         |
             +----------+--------------+
                        v
             geprüfter Graph-Bestand
             + erzeugte physische Teile
                        |
              +---------+---------+
              |                   |
      neuer Collector-Vertrag   Artwork-Review

Parallel weiterhin aktiv:
Legacy-Produkte -> Editionen/Releases -> alte Checkliste -> SQLite/Tracker/Haupttabelle

Unabhängige Discovery:
Provider -> unveränderte Runs -> Staging/Kandidaten -> explizite Prüfung/Zuordnung
```

Die Discovery macht Kandidaten sichtbar; sie kann eine neue Karte nicht allein durch Auftauchen in einem Run zur Katalogwahrheit machen. Das ist richtig. Der Graph ist in der Praxis zugleich ein geprüfter Ausgangsbestand und das Ziel einer Teilprojektion. Genau diese Doppelrolle wird in mehreren Dokumenten zu ungenau als vollständig „generiert“ beschrieben.

## 4. Was gut gelöst ist und erhalten bleiben sollte

1. **Positive Belege und explizite Ungewissheit.** Die Trennung von `confirmed`, `exists`, `needs-evidence`, `disputed` und Eigentümerentscheidung vermeidet mehrere bekannte Fehlschlüsse.
2. **Belege bleiben nachprüfbar.** Rohantworten, Hashes, SPEC-IDs, Herkunft und Migrationsdispositionen sind wertvoller als bloße Quellenlinks.
3. **Sprache, Lokalität, Artwork, Kartentext, Ausgabe und Finish werden grundsätzlich getrennt.** Ein zusammengezogenes „Kartenobjekt mit allen Varianten“ würde wesentliche Information verlieren.
4. **Der neue Collector-Vertrag ist vorsichtig.** Er unterscheidet belegte Drucke, Finish-Kandidaten und Forschungsplatzhalter und versieht sie ausdrücklich mit einer Fortschrittsklasse.
5. **Migrationen sind Bestandteil des Produkts.** Rekeys und Splits werden nicht einfach als neue IDs ausgegeben; private Sammlungsdaten liegen außerhalb des öffentlichen Datenbestands.
6. **Normale Regeneration ist offline.** Versionierte TCGdex-Eingaben verhindern, dass die tägliche Ausgabegenerierung von einem zufälligen Live-Ergebnis abhängt.
7. **Die Laufzeitabhängigkeiten bleiben klein.** Python-Standardbibliothek für die Generatoren, SQLite als portables Übergabeformat, Vanilla JS/CSS für die Website; Playwright ist eine Prüfabhängigkeit.
8. **Es existieren echte Verhaltenstests.** Die Browser-Suite prüft nicht nur erzeugten Text, sondern Interaktion, Druck, Bilder, Themes, Kontraste und einfache Markup-Injection-Fälle.
9. **Die mobile Hauptansicht funktioniert.** Kleine Displays erhalten Karten statt einer unbedienbar breiten Gesamttabelle. Bei den fünf geprüften Breiten blieb die Gesamtseite innerhalb des Viewports.
10. **Veröffentlichung ist bewusst getrennt.** Allowlist, manueller Pages-Lauf und Commit-/Katalog-Handoff sind sinnvoll. Ein Merge veröffentlicht nicht automatisch.
11. **Historische Pässe sind erkennbar historische Provenienz.** Sie nicht erneut auszuführen und das Archiv gegen Änderungen zu prüfen, schützt die Nachvollziehbarkeit.

Diese Eigenschaften dürfen bei einer Vereinfachung nicht verloren gehen. Insbesondere sind eine zweite Provider-Bestätigung nicht überall zwingend und Eigentümerbelege nicht pauschal schwach. Maßgeblich bleibt die tatsächlich implementierte E3-Regel, nicht eine strengere erfundene Evidenzleiter.

## 5. Priorisierte Befunde

**P1:** Risiko falscher fachlicher Behandlung, instabiler Identität, Datenverlust oder ein entscheidender Gate-Fehler. **P2:** reproduzierbarer Funktions-, Vertrags-, Wartungs- oder Effizienzfehler ohne nachgewiesene Beschädigung des aktuellen Bestands. **P3:** Dokumentations- und Bedienungsverbesserung. Es wurde kein aktueller P0-Schaden nachgewiesen.

„Reproduziert“ bezeichnet ein tatsächlich ausgeführtes isoliertes Beispiel. „Beobachtet“ bezeichnet einen aktuellen Code-, Daten- oder Laufzeitbefund. Ein hypothetischer Ausbau wird ausdrücklich als solcher benannt.

### F01 · P1 · Freitext steuert die Beweiskraft einer Bestätigung

**Ort:** [scripts/evidence_semantics.py](scripts/evidence_semantics.py), `granularity()` ab Zeile 158 und die regulären Ausdrücke am Dateianfang.

**Reproduziert:** Für die vorhandene Einheit `U0169` wurde ausschließlich an `sourceType` die Zeichenfolge `; specimen unavailable` angehängt. `evidence`, Quelle und Rohverdict blieben unverändert. Ein Aufruf von `build()` änderte den Anwendungsstatus von `needs-evidence` zu `exists`.

Ursache: Das Wort `specimen` trifft den allgemeinen CARD_LEVEL-Ausdruck. Der Klassifizierer erkennt weder die Verneinung noch eine strukturierte Reichweite des Belegs. Beschreibungstext ist dadurch zugleich ausführbare Fachlogik.

**Folge:** Eine redaktionelle Änderung kann stärkere Datenaussagen erzeugen. Nachgewiesen ist der Fehler im Statusprojektor; damit ist nicht behauptet, dass jede solche Änderung unbemerkt durch sämtliche weiteren Graph-Prüfungen käme.

**Kleinste tragfähige Verbesserung:** Die geprüfte Granularität und ihr exaktes Ziel strukturiert im kanonischen Beleg erfassen. Den bisherigen Textklassifizierer nur als begrenzte Legacy-Migration verwenden; unbekannte neue Belegarten bleiben offen. Keine automatische Neuadjudikation aller alten Zeilen.

**Abnahme:** Eine reine Textkorrektur einschließlich „no specimen“, „specimen unavailable“ und „sibling card page“ ändert keinen Wahrheitsstatus. Eine fachliche Aufwertung benötigt einen expliziten, belegten Zustandswechsel. Die aktuellen gültigen Karten- und Setlistenbelege bleiben wirksam.

### F02 · P1 · Reihenfolge von Markierungen verändert die Collector-Identität

**Orte:** [scripts/authoritative_graph.py](scripts/authoritative_graph.py), Zeilen 80–103; [scripts/collector_catalogue.py](scripts/collector_catalogue.py), Zeilen 248–273 und `normalized_markings()` ab 647.

**Reproduziert:** Zwei physisch identische Eingaben mit denselben zwei Markierungen in umgekehrter Reihenfolge erzeugen im Graph dieselbe semantische Identität. Im Collector unterscheiden sich sowohl `printing_semantic_key()` als auch `printing_semantic_core_key()`.

Der Graph sortiert Markierungen; der Collector übernimmt ihre Listenreihenfolge. Das ist für die vorhandenen Daten relevant: `PHYSICAL:F0107-P02` enthält zwei Markierungen. Eine bereits falsch zugeordnete Sammlung wurde nicht festgestellt.

**Folge:** Vorgängerabgleich und Rekey-Erkennung können auf eine andere Ordnung desselben Eingangs unterschiedlich reagieren. Die zugesagte Reihenfolgeunabhängigkeit und die gemeinsame Identitätsdefinition sind nicht erfüllt.

**Verbesserung:** Eine kanonische Normalisierung und einen Besitzer der physischen Signatur verwenden. Gültigkeitsprüfung und Darstellung dürfen zusätzliche Aufgaben behalten, aber nicht eine zweite Identitätsregel implementieren. Die Umstellung muss bestehende IDs und Migrationen prüfen; keine unkommentierte Neuschlüsselung.

**Abnahme:** Permutationen der Markierungen ergeben gleiche Signaturen, gleiche Vorgängerzuordnung und gleiche Sammlungsreferenzen. Eine inhaltlich andere Markierung bleibt ein anderer Druck. Den vorhandenen Zweimarkierungsfall als Regression verwenden.

### F03 · P1 · Der Graph wird vor der Validierung geschrieben

**Ort:** [scripts/authoritative_graph.py](scripts/authoritative_graph.py), `main()` ab 1987; `write_graph(graph)` steht vor `validate(graph)`.

**Reproduziert:** Auf temporären Kopien wurde bei einem bestätigten Finish der Wert `audit-invalid-finish` eingesetzt. `--write` endete mit Exit 1 und einer Stale-Printing-Meldung. Trotzdem war der Graph bereits geändert und enthielt den ungültigen Wert.

Zusätzlich schreibt `write_graph()` direkt in die Zieldatei. Ein abgebrochener Schreibvorgang kann deshalb gerade den Bestand beschädigen, der als geprüfte Ausgangsbasis erhalten bleiben muss.

**Verbesserung:** Vollständig im Speicher projizieren und validieren, erst danach schreiben. Für diese kanonische Datei einen eindeutig benannten temporären Nachbarn und atomaren Austausch verwenden. Die bisherige Datei muss bis zur erfolgreichen Validierung erhalten bleiben.

**Abnahme:** Ungültiger Finish-Wert, ungültige Referenz und Schreibfehler lassen den alten Graph byte-identisch zurück. Der gültige Schreibpfad und unmittelbar anschließende Offline-Check funktionieren weiter.

### F04 · P1 · Prüfmodi besitzen Schreib- und Löschnebenwirkungen

**Orte:** [scripts/database.py](scripts/database.py), ab 1347; [scripts/tracker.py](scripts/tracker.py), ab 421; [scripts/finishes.py](scripts/finishes.py), CLI-Verzweigung ab 1955.

**Reproduktion A:** Neben eine temporäre Kopie der Datenbank wurden vorhandene Dateien `<datenbank>.check` und `<datenbank>.check.tmp` gelegt. `validate_database()` meldete keine Probleme und löschte beide. Dasselbe geschah bei `tracker.check_template()`.

Die Prüfer verwenden vorhersehbare Nachbarpfade, bauen dorthin und entfernen sie anschließend. Die Schlusskontrolle auf einen sauberen Git-Diff erkennt diese vorübergehenden Eingriffe nicht. Auch ohne dauerhaften Diff ist das kein rein beobachtender Prüfer.

**Reproduktion B:** In einer isolierten Kopie wurde eine Finish-Projektion absichtlich entfernt. `finishes.py --check --reproject` endete mit Exit 0 und schrieb die fehlende Projektion zurück. Der `--reproject`-Zweig umgeht die `--check`-Behandlung in `main()`.

**Verbesserung:** Datenbankvergleich in `TemporaryDirectory` außerhalb des Prüfziels; niemals bestehende Nachbardateien entfernen. CLI-Modi einmal zentral validieren, bevor irgendein Schreibpfad erreicht wird. Gegensätzliche Modi müssen zurückgewiesen werden. `_project_cards()` für den Reproject-Pfad wiederverwenden statt die Projektion doppelt zu halten.

**Abnahme:** Vorhandene Sentinel-Nachbardateien bleiben unverändert; ein tatsächlich schreibgeschützter Eingangsbaum lässt sich prüfen. `--check --reproject` endet ohne Änderung mit einem Argumentfehler. Zusätzlich Inhalt und Zeitstempel der geprüften Eingaben kontrollieren, nicht nur den abschließenden Git-Status.

### F05 · P1 · Ein P6-Fehler wird pauschal in einen grünen Gate verwandelt

**Ort:** [scripts/regen.py](scripts/regen.py), Zeilen 204–212.

**Reproduziert:** Ein isoliert eingespeistes Ergebnis `returncode=1` mit genau einem `[FAIL] P6` führte in `regen.main()` zu Exit 0 und `regen.py: OK`. Der Lauf behauptete zusätzlich `CI gate is green`, ohne CI abgefragt zu haben.

Der Code unterscheidet nicht zwischen einem lokalen zusätzlichen Ref, einem flachen Clone, nicht lesbarer Historie oder einem tatsächlichen Fund in zu veröffentlichender Historie. Die Ausnahme läuft auch im normalen CI-Aufruf dieses Skripts. Der separate Post-Push-Job ist hilfreich, ersetzt aber diese fehlende Unterscheidung nicht.

**Verbesserung:** Ein P6-Fehler bleibt standardmäßig ein Fehler. Falls eine lokale Sonderbehandlung erforderlich ist, muss sie explizit auf den geprüften Ref-Umfang beschränkt und als unvollständige lokale Prüfung ausgewiesen sein. Keine Aussage über einen nicht gelesenen CI-Zustand.

**Abnahme:** P6-Fehler in veröffentlichten Refs und fehlende prüfbare Historie führen zu einem nichtgrünen Vollgate. Eine bewusst eingeschränkte Diagnose darf sich nicht als vollständiger erfolgreicher Gate ausgeben. Der tatsächliche Audit-Baseline-Lauf hatte keinen P6-Fund; hier wurde ein Fehlerpfad geprüft.

### F06 · P1 · Der alte Tracker fordert Kandidaten als fehlende Sammlungskarten an

**Orte:** [scripts/checklist.py](scripts/checklist.py), Zählung ab 262; [scripts/database.py](scripts/database.py), Statuszuweisung bei 1018; [scripts/tracker.py](scripts/tracker.py), Initialisierung bei 286; [README.md](README.md), Einstiegstabelle.

**Beobachtet und per SQLite geprüft:**

```text
Alte Tracker-Vorlage:
confirmed             -> need       701
marketplace-claimed   -> need       111
owner-attested        -> need         1
pending               -> research    76

Neuer Collector-Vertrag für die 813 alten „documented“-Einträge:
verified-printing     701
finish-candidate      112
```

Der alte Pfad nennt einen Eintrag dokumentiert, sobald ein Printing-Datensatz existiert. Er berücksichtigt dessen Beweisstatus für die Kauf-/Sammlungsaufforderung nicht. Der neue Vertrag ordnet genau diese 112 Kandidaten ausdrücklich `research` zu. Diese konservative Fortschrittsentscheidung ist im Katalog als angenommene Eigentümerentscheidung dokumentiert.

**Folge:** Die Wahl des empfohlenen Einstiegspunkts verändert, welche Dinge ein Sammler als tatsächlich fehlend behandeln soll. Außerdem sind source-first-Karten ohne Legacy-Vorgänger im neuen Vertrag vorhanden, aber nicht in der alten Haupttabelle/Checkliste. Beispielsweise existiert ein bestätigter `SVP LA 184`-Eintrag ohne `legacyChecklistIds`; die alte Sprachliste hat keinen LATAM-Eintrag.

Das Artwork-Review enthält auch solche Graph-Releases; die Lücke betrifft die Haupttabelle, Druckcheckliste und den alten Tracker, nicht jede Oberfläche im Repository.

**Verbesserung:** Den neuen Collector-Vertrag zum klaren Einstieg für neue Sammleranwendungen machen. Den alten Pfad ausdrücklich als Kompatibilitätsansicht kennzeichnen und dessen Fortschrittssemantik mit der bereits getroffenen Kandidatenentscheidung abstimmen. Bestehende private Besitzstände, Mengen, Notizen und bewusste Kaufentscheidungen bei einer Migration erhalten.

**Abnahme:** Ein reiner Marketplace-Finish-Kandidat landet ohne zusätzliche Entscheidung nicht automatisch im regulären `need`-Nenner. Ein belegter LATAM-Druck ist im unterstützten Sammlereinstieg auffindbar. Alt-/Neuzahlen werden mit ihren unterschiedlichen Nennern erklärt, nicht künstlich angeglichen.

### F07 · P2 · Die Artwork-Projektionsversion deckt ihren Inhalt nicht ab

**Ort:** [scripts/artwork_review.py](scripts/artwork_review.py), `projectionVersion` ab 350.

**Reproduziert:** In einer Graph-Kopie wurde das `cardKey` eines vorhandenen Work geändert, ohne die unveränderten Metadaten anzufassen. `artwork_review.build()` erzeugte einen anderen Projektionsinhalt, aber dieselbe `projectionVersion`.

Der Versionshash umfasst Graph-`meta.inputs`, Graph-Schemaversion, Units, Finishes und Source-first-Prints. Tatsächlich gelesene Entitäten/Kanten, Specimens, Karten-/Release-Ergänzungen und Bildbytes werden dadurch nicht vollständig erfasst.

**Folge:** Zwei unterschiedliche Review-Grundlagen können dieselbe Version tragen. Einzelne zusätzliche Bild- und Beobachtungshashes helfen, ersetzen aber nicht die zugesagte vollständige Projektionsbindung. Ein zukünftiger Importer darf sich nicht allein auf diesen Wert verlassen.

**Verbesserung:** Den semantischen Projektionsinhalt mit Ausnahme des eigenen Hashfelds deterministisch hashen oder alle tatsächlich maßgeblichen Eingaben vollständig binden. Für reine Mengen Eingangsreihenfolge normalisieren. Bestehende Browserentwürfe mit abweichender Grundlage sichtbar als veraltet behandeln.

**Abnahme:** Änderung von Work-Zuordnung, Beleg, Bild oder Release-Anzeige ändert die Projektionsversion; unveränderte Eingaben und reine Mengenpermutationen nicht. Veraltete Vorschläge bleiben exportierbar, werden jedoch nicht als aktuell geprüft ausgegeben.

### F08 · P2 · Artwork-Eingaben gehen beim Speichern verloren; Speicherfehler bleiben unsichtbar

**Ort:** [site/app.js](site/app.js), `persist()` ab 1223, vollständiges Rendern ab 1454 und Speichern ab 1468.

**Reproduktion A:** In zwei Artwork-Karten Notizen eingeben, nur die erste speichern. Das Speichern rendert sämtliche Karten neu. Die noch nicht gespeicherte Notiz der zweiten Karte ist danach leer. Filteränderungen können denselben Verlust verursachen.

**Reproduktion B:** In einem isolierten Browserkontext `Storage.setItem()` einen `QuotaExceededError` auslösen lassen. Nach dem Speichern meldet die Übersicht `1 proposals saved locally`. Nach Neuladen sind es wieder 0. Es erscheint keine verlässliche Fehlermeldung zur fehlenden Persistenz.

**Verbesserung:** Den Persistenzerfolg auswerten und ehrlich anzeigen. Bei nicht verfügbarem Speicher den Download als notwendige Sicherung anbieten. Beim Speichern einer Karte andere noch eingegebene Werte erhalten, beispielsweise durch Aktualisieren nur dieser Karte und der Zusammenfassung. Kein globales Neurendern aller Formulare für eine einzelne Speicherung.

**Abnahme:** Ein Speicherfehler führt nicht zu einer Erfolgsmeldung. Speichern, Filtern und Theme-Wechsel löschen keine Eingaben in anderen Karten. Die bestehenden Download-, Versions- und Bildschutzregeln bleiben erhalten.

### F09 · P2 · Der Workflow bestimmt den neuesten Run anhand von Dateizeitstempeln

**Ort:** [scripts/workflow_loop.py](scripts/workflow_loop.py), `latest_manifests()` ab 44.

**Reproduziert:** Zwei Manifeste wurden mit Run-IDs aus Januar und September angelegt. Der alte unvollständige Januar-Run bekam nur einen neueren Dateizeitstempel. Die Funktion wählte ihn als neuesten Run.

Dateizeitstempel ändern sich durch Checkout, Kopieren, Wiederherstellen und Synchronisation. Der eigentliche Discovery-Pfad entscheidet dagegen anhand unveränderlicher Run-Identität sowie Erwerbungs- und Capability-Kompatibilität.

**Verbesserung:** Zwischen „letzter Versuch“ und „kanonisch verwendeter erfolgreicher Run“ unterscheiden. Beide anhand der vorhandenen Run-Verträge bestimmen und im Bericht benennen. Keine eigene Mtime-Definition von Aktualität.

**Abnahme:** Umgekehrte Dateizeitstempel ändern den ausgewählten kanonischen Run nicht. Ein neuer fehlgeschlagener Versuch bleibt sichtbar, verdrängt aber nicht unbemerkt die letzte kompatible erfolgreiche Grundlage.

### F10 · P2 · Die Workflow-Messung übersieht echte Änderungen

**Orte:** [scripts/scoped_regen.py](scripts/scoped_regen.py), `tree_paths()` und Zeile 101; [scripts/measure_workflow.py](scripts/measure_workflow.py), Zeile 221 und `pages_specs()` ab 147.

**Reproduziert:** Eine bereits geänderte, versionierte Datei wurde in einem temporären Git-Repository durch einen Step nochmals inhaltlich geändert. Der Step meldete `observedChangedPaths: []`. Die Messung vergleicht nur Mengen geänderter Dateinamen: Ein schon vor dem Step als dirty bekannter Pfad kann nicht erneut in `after - before` auftauchen.

Die Messung übersieht außerdem Änderungen, die eine Datei wieder an den Indexstand angleichen; gestagte Unterschiede sind in dieser Erfassung ebenfalls kein vollständiger Ausgangszustand. Für aufeinanderfolgende Generatoren mit demselben Ziel ist das besonders irreführend.

**Zweiter beobachteter Fehler:** `pages_specs()` hält eine eigene Generatorliste. Die aktuelle Pages-Pipeline übernimmt dagegen das L4-Artefakt und baut diese zweite Projektionsfolge gerade nicht mehr. Das Messprofil misst damit nicht zuverlässig den heute beschriebenen Ablauf.

**Verbesserung:** Entweder Inhalte der relevanten Vorher-/Nachherdateien vergleichen oder das Feld präzise als „neu dirty gewordene Pfade“ benennen. Den tatsächlich veränderten Byteinhalt nicht aus einem Statusmengenvergleich behaupten. Messprofile an die wirklichen zentralen Ausführungsgrenzen binden und die veraltete Pages-Buildliste entfernen.

**Abnahme:** Ein zweiter Writer auf dieselbe Datei wird erfasst; eine Rückkehr zum Ausgangsinhalt ebenfalls. Die Pages-Messung führt keine Pipeline aus, die Pages selbst nicht mehr verwendet.

### F11 · P2 · Ein fehlgeschlagenes Live-Recording überschreibt die Fixture und meldet Erfolg

**Ort:** [verification/verify_finish_sources.py](verification/verify_finish_sources.py), `if args.record` ab 147, vor der Fehlerauswertung.

**Reproduziert:** Alle Antworten wurden in einer isolierten Ausführung als Netzfehler simuliert. `--record` ersetzte eine vorhandene Fixture durch `responses: {}` und endete mit Exit 0. Auch Datenabweichungen werden vor dieser Schreibentscheidung nicht abschließend ausgewertet.

**Verbesserung:** Netz- und Datenfehler vor dem Ersetzen prüfen. Nur einen vollständigen, erfolgreichen neuen Record übernehmen; die bisherige Fixture ansonsten unverändert erhalten. Kein neues allgemeines Snapshot-System bauen: Die hier benötigte Transaktion ist klein.

**Abnahme:** Totalausfall, Teilausfall und Subtypabweichung erhalten die alte Fixture und geben einen passenden Fehlerstatus zurück. Ein vollständiger erfolgreicher Record ist anschließend offline reproduzierbar.

### F12 · P2 · Kanonischer Bestand und Wegwerfprojektion sind nicht eindeutig getrennt

**Orte:** [WORKFLOW-MAP.md](WORKFLOW-MAP.md), [HANDOVER.md](HANDOVER.md), [scripts/authoritative_graph.py](scripts/authoritative_graph.py), [scripts/regen.py](scripts/regen.py), [ADR-0008](verification/ADR-0008-reviewed-catalogue-basis-lists.md).

**Beobachtet:** Der Graph wird teilweise als generiertes Artefakt bezeichnet. Das Skript nennt ihn ausdrücklich einen autoritativen, versionierten Input und verweigert den Betrieb, wenn die bestehende Datei fehlt. `project_physical_evidence()` übernimmt die geprüfte Lokalitätsbasis und ersetzt nur die ihm gehörenden Teile. Ein kompletter Neuaufbau allein aus allen übrigen aktuellen Stores ist somit nicht implementiert.

Auch `snorlax_cards.json` ist zugleich Rohdatenbestand und mehrfach beschriebenes Projektionsziel: Editionen, Finish und Sprachprojektion werden in die Eingabedatei zurückgeschrieben. Das kann kontrolliert funktionieren, ist aber nicht dasselbe wie ein einfacher Einweg-DAG mit austauschbaren Ausgaben.

**Folge:** Wer „generated“ als „löschbar und jederzeit vollständig wiederherstellbar“ versteht, kann geprüfte Wahrheit entfernen. Die bestehende Hash-/Diff-Prüfung verhindert nicht, dass die Zuständigkeit konzeptionell missverstanden wird.

**Verbesserung:** Zuerst die wirkliche Grenze dokumentieren: welche Graph-Entitäten und Felder sind geprüfter Bestand, welche gehören welchem Projektor? Den Hybrid nicht als vollständig disposable bezeichnen. Eine spätere Trennung der geprüften Basis von der Materialisierung ist sinnvoll, wenn sie den Schreibpfad vereinfacht; eine flächige Datenmigration nur für schönere Architektur ist nicht erforderlich.

**Abnahme:** Für jede Datei und jeden gemischten Store ist die Wiederherstellungsquelle eindeutig. Entweder lässt sich eine als vollständig generiert bezeichnete Ausgabe aus den verbleibenden kanonischen Eingaben neu erzeugen, oder sie ist ausdrücklich als zu erhaltender Bestand klassifiziert. Bestehende IDs und Belege bleiben unverändert.

### F13 · P2 · Karten-Discovery verarbeitet die gesamte Historie immer wieder

**Ort:** [scripts/card_discovery.py](scripts/card_discovery.py), `build_latest()` ab 1367, Parser ab 375/464 und `replay_run()`; [verification/runs](verification/runs).

**Gemessen:** Der Vollgate benötigte für `card_discovery.py --check` 103,40 Sekunden. Ein späterer separater Profiling-Lauf dauerte 44,54 Sekunden und führte 23 `build_projection()`-Aufrufe, 5.926 `parse_detail()`-Aufrufe und rund 80,3 Millionen Funktionsaufrufe aus. Davon entfielen etwa 33,1 Sekunden kumulativ auf `HTMLParser.feed()`/dessen Parsing. Die Zahlen überlappen; sie dürfen nicht addiert werden.

Der zweite Lauf war wärmer und instrumentiert. Er ist keine direkt vergleichbare Geschwindigkeitsmessung und kein Benchmark-Median. Er belegt aber deutlich, wo die Arbeit liegt: sämtliche 23 aufbewahrten Karten-Runs werden neu projiziert.

Zusätzlich liegen in `verification/runs` 8.761 Dateien mit 131,88 MiB. Inhaltsgleiche Bytes eingerechnet sind es nur 1.608 verschiedene Inhalte mit 20,95 MiB. Die Differenz beträgt 110,93 MiB im Arbeitsbaum. **Das ist keine entsprechende Git-Pack-Ersparnis:** Git kann identische Blobs bereits teilen.

**Kleinste Verbesserung:** Identische Antworten innerhalb eines Laufs nur einmal parsen. Cache-Schlüssel müssen neben dem Antwortinhalt alle relevanten Parser-/Locale-/Vertragsparameter berücksichtigen. Hash- und Provenienzprüfungen bleiben erhalten. Historische Integritätsprüfung und aktuelle Projektion dürfen getrennt organisiert werden, sofern die vollständige Prüfabdeckung im Release-Gate erhalten bleibt.

Erst danach prüfen, ob neue Replay-Manifestversionen unveränderte Payloads referenzieren können. Bestehende unveränderliche Runs nicht zur Platzersparnis umschreiben oder löschen. Kein externer Cache-Dienst und keine Datenbank als erste Maßnahme.

**Abnahme:** Alle bisherigen Determinismus-, Run-Kompatibilitäts- und Manipulationsfälle bestehen. Vorher/Nachher unter gleichen Bedingungen mit mehreren Läufen messen; Parsing identischer Inhalte wird nachweislich reduziert. Keine Zielzeit erfinden, bevor gemessen wurde.

### F14 · P2 · Das Artwork-Review baut beim Seitenstart zehntausende Elemente auf

**Orte:** [site/app.js](site/app.js), `initArtworkReview()` und `render()` ab 1454; [scripts/site.py](scripts/site.py), eingebettete Projektion.

**Gemessen im frischen HTTP-Browserkontext bei 1440 × 1000:** 73.348 DOM-Elemente, 8.566 Formular-/Bedienelemente und 559 sofort gerenderte Artwork-Mitglieder. Die Dokumenthöhe lag bei rund 291.292 Pixeln. Alle 632 Releases sind im Datenmodell vorhanden; der Standardfilter zeigt 559 davon.

`index.html` umfasst 4.203.356 Bytes. Der Artwork-JSON-Block allein enthält 2.960.721 Zeichen. `loading="lazy"` verzögert Bilder, nicht JSON-Parsing, HTML-Erzeugung, Formulare oder Layout. Suchereignisse und das Speichern eines einzelnen Vorschlags rendern die ganze sichtbare Menge erneut.

Der lokale Seitenstart benötigte im beobachteten HTTP-Lauf 1,43 Sekunden und erzeugte keine JavaScript-Fehler. Das ist kein Nachweis guter Leistung auf einem Mobilgerät. Die unnötige Vorarbeit ist unabhängig von diesem günstigen lokalen Einzelwert messbar.

**Verbesserung:** Review-DOM erst beim Öffnen des Review-Bereichs erzeugen, Mitglieder gruppenweise aufklappen oder in einfachen Seiten darstellen. Zunächst native Disclosure-Elemente und kleine Renderbereiche verwenden. Das eingebettete JSON darf für die ausdrücklich gewünschte `file://`-Nutzung erhalten bleiben; ein erzwungener Netzwerkfetch wäre keine gleichwertige Vereinfachung.

**Abnahme:** Der reine Sammlerbesuch erzeugt nicht hunderte unbenutzte Review-Formulare. Suche, Tastaturbedienung, alle Releases, Vorschläge und Downloads bleiben erreichbar. F08 wird nicht durch ein weiteres globales Neurendern verschärft.

### F15 · P2 · Vollauflösende Belegbilder dominieren Repository und Publikation

**Orte:** [scripts/publish.py](scripts/publish.py), `TREES`; `verification/specimens/`; Asset-Erzeugung in [scripts/collector_catalogue.py](scripts/collector_catalogue.py).

**Gemessen:** Der versionierte Arbeitsbaum umfasst 878,11 MiB. Davon entfallen 679,02 MiB auf 397 Specimen-Bilddateien. Einzelne PNGs sind etwa 16–17 MB groß. Das überprüfte Publikationsartefakt enthält 648 Dateien einschließlich `.nojekyll` und rund 725,83 MiB. Alle freigegebenen Bilder des Specimen-Verzeichnisses werden übernommen.

Originalbelege in hoher Qualität zu erhalten ist fachlich sinnvoll. Dieselben Bytes für kleine Kachelansichten zu verwenden und bei jedem Publikationslauf vollständig zu transportieren, ist dennoch teuer.

**Verbesserung:** Unveränderte, gehashte Originale erhalten; bei nachgewiesenem Bedarf separate deterministische Vorschaudateien für normale Anzeige erzeugen. Original und Vorschau müssen unterscheidbare Pfade, Hashes und Zwecke besitzen. Vor dem Einschränken der veröffentlichten Bildmenge alle Beleg-, Collector- und Dokumentationsreferenzen berücksichtigen, nicht nur aktuell sichtbare Karten.

**Abnahme:** Die Erstansicht einer Kachel lädt eine angemessen kleine Vorschau. Ein expliziter Belegaufruf erreicht das Original. Kein SPEC-Nachweis, Originalhash oder Herkunftseintrag geht verloren. Dies ist ein gezielter Asset-Workflow, kein Auftrag zur nachträglichen Veränderung der Beweisbilder.

### F16 · P2 · Test- und CI-Arbeit wird unnötig wiederholt und ungleich eingesetzt

**Orte:** [verification/test_findings_harness.py](verification/test_findings_harness.py), `rf.collect()`; [scripts/regen.py](scripts/regen.py), TESTS; [Release-Workflow](.github/workflows/release-gate.yml), Installations- und Browserbedingungen.

**Gemessen:** Der Findings-Harness benötigte 147,11 Sekunden, der spätere eigentliche Findings-Lauf weitere 35,59 Sekunden. Der Harness führt die reale vollständige Sammlung aus, obwohl ein erheblicher Teil seiner Aussagen Importfreiheit, Ergebnisprotokoll und Fehlerisolierung betrifft. Unterschiedliche Cache-/Systemzustände erklären einen Teil der Zeitdifferenz; nicht 147 Sekunden pauschal als reine Verschwendung deklarieren.

**Beobachtet:** Linux-PR-Jobs installieren Playwright und Chromium. Die Browser-Suite wird aber ausdrücklich nur außerhalb eines `pull_request` ausgeführt. Änderungen an `site/app.js`, CSS oder dem Site-Generator erhalten deshalb aus diesem PR-Workflow keinen Verhaltenstest, obwohl seine Laufzeitumgebung bezahlt wird.

**Verbesserung:** Harness-Verhalten mit kleinen isolierten Fixtures prüfen und den realen vollständigen Findings-Lauf einmal an seiner Integrationsgrenze behalten. Browserabhängigkeiten nur dort installieren, wo sie benutzt werden; UI-relevante PRs sollten einen passenden Browserlauf erhalten. Keine zweite kopierte Gesamtliste von Tests in Workflow-Dateien einführen.

**Abnahme:** Manipulations-, Historien- und Artefaktprüfungen bleiben im vollständigen Release-Vertrag abgedeckt. Ein absichtlicher Browser-Regressionsfall in einer UI-Änderung fällt vor dem Merge auf. Eine reine Datenänderung installiert keinen unbenutzten Browser, falls kein Browserlauf für sie vorgesehen ist.

### F17 · P2 · Der Komplexitätsguard schützt die Baseline, aber noch nicht die Wartbarkeit

**Orte:** [verification/complexity.py](verification/complexity.py), [verification/complexity_baseline.json](verification/complexity_baseline.json), [verification/review_findings.py](verification/review_findings.py) und die Hotspots in Abschnitt 6.

**Gemessen:** 802 aktive Funktionen, davon 177 oberhalb CC 10, maximal CC 111. Es gibt keine Überschreitung der hinterlegten individuellen Grenzwerte. Das ist ein funktionierender Regressionsschutz, aber keine Aussage, dass die Ausgangswerte gut sind.

Besonders schwer zu lesen sind fachlich namenlose Verschachtelungen wie `_collect_g12_part2_if_part4`, die mit vielen `nonlocal`-Variablen arbeiten. Die äußere Funktion wirkt nach der Aufteilung im Einzelmetrikwert kleiner, der gekoppelte Zustand bleibt jedoch bestehen. Die Messung bewertet geschachtelte Funktionen absichtlich getrennt.

**Verbesserung:** Nur bei tatsächlicher Berührung solcher Bereiche fachlich zusammenhängende Schritte benennen und Übergaben explizit machen. Validatoren dürfen repetitive, gut lesbare Regeln enthalten. Deklarative SQL-/HTML-/Schema-Blöcke nicht allein wegen ihrer Zeilenzahl zerlegen. Abgesenkte Baselines nachziehen, Ausnahmen nicht erhöhen, um eine Regression grün zu machen.

**Abnahme:** Ein betroffener Regelblock lässt sich mit kleinen fachlichen Eingaben isoliert prüfen. Weniger impliziter Zustand, weniger doppelte Logik und unveränderte Fachabdeckung sind die Ziele. Ein niedrigerer CC-Wert durch bloßes mechanisches Auslagern genügt nicht.

### F18 · P2 · Artwork-Dateigleichheit und geprüfte Artwork-Identität werden vermischt

**Orte:** [scripts/artwork_review.py](scripts/artwork_review.py), Zeilen 280–292 und Gruppenbildung; [ADR-0007](verification/ADR-0007-embedded-artwork-review-ui.md); [ADR-0008](verification/ADR-0008-reviewed-catalogue-basis-lists.md).

**Beobachtet:** Sobald irgendein lokales, gehashtes Bild vorhanden ist, wird die Appearance als `verified-image-match` bezeichnet. Ihre ID entsteht aus dem Hash der gesamten Menge zugehöriger Bildhashes. Diese Menge kann sowohl ein Legacy-Produktbild als auch weitere Specimen-Fotos enthalten. Ein zusätzliches Foto verändert daher die Appearance-ID, auch wenn die Illustration identisch bleibt.

Bytegleichheit beweist die Wiederverwendung einer Bilddatei. Sie beweist für sich weder eine menschlich geprüfte Artwork-Gruppierung noch, dass ein generisches Produktfoto jede lokalisierte Ausgabe zeigt. Der aktuelle Graph besitzt keine vollständige separate, geprüfte Artwork-/Appearance-Registry entsprechend dem Zielbild aus ADR-0008. Der Browser bleibt zwar korrekt eine Vorschlagsoberfläche; seine Bezeichnungen suggerieren teilweise mehr Bestätigung als tatsächlich gespeichert ist.

**Verbesserung:** Generierte Bildgruppen ausdrücklich als Bildgruppen/Vorschläge benennen. Falls die geprüfte Artwork-Registry weiterhin Produktziel ist, ihre stabilen IDs von der wechselnden Menge an Bildern trennen und Bildverknüpfungen als Belege modellieren. Vorher den tatsächlichen Bedarf des noch fehlenden Vorschlagsimports klären; kein Backend voraussetzen.

**Abnahme:** Ein weiteres Foto benennt eine bereits angenommene Artwork-Identität nicht um. Eine automatisch gruppierte Bildmenge wird nicht als menschlich bestätigte Artwork-Gleichheit ausgegeben. Unterschiedliche Sprachen, Drucke und Werke bleiben getrennt referenzierbar.

### F19 · P3 · Aktive Dokumentation führt noch an mehreren Stellen in die Irre

**Konkrete Beispiele:**

- `CLAUDE.md` verweist bei den Datenmodellfallen auf `HANDOVER.md` §4; das aktuelle Handover besitzt nur die Abschnitte 1 und 2.
- `verification/RESUME.md` verweist für das Evidenzjournal noch auf `HANDOVER` §5.
- Der Site-Generator nennt in seiner Artwork-Erklärung `summary.mappedWorks` „mapped artwork groups“. Gemessen sind 41 Works, aber 181 bildbasierte Appearance-Gruppen plus 73 ungelöste Gruppen. Kartentext und Artwork werden dadurch in der öffentlichen Erklärung wieder vermischt.
- Der öffentliche Satz „Every claim carries a source outside the marketplace“ ist stärker als der tatsächlich sichtbare Bestand mit Marketplace-Finish-Kandidaten. Die Einschränkungen folgen später, sollten aber nicht erst einen uneingeschränkten Eingangssatz korrigieren müssen.
- `CLAUDE.md` nannte im Auditstand neun ausschließlich auf inspizierten Specimens beruhende Einheiten. Im aktuellen Store gibt es insgesamt acht Einheiten mit `providerId=inspected-specimen`, fünf davon ohne Korroboration. Der aktive Begleitwert wurde in PR #358 auf acht korrigiert; die Zahl 19 für reine Eigentümerattestation wurde überprüft und passt weiterhin.
- `ANALYSIS.md` ist eine ausdrücklich datierte Dokumentationsprüfung mit Implementierungsledger. Ihr damaliger blockierter Stand darf nicht als aktueller operativer Backlog gelesen werden; die gegenwärtige Discovery-/Gate-Lage ist anhand der aktuellen Stores zu bestimmen.

**Verbesserung:** Tote Abschnittsverweise reparieren, Work und Artwork sauber benennen, statische Zähler durch Verweise auf erzeugte Werte ersetzen und Eingangsversprechen an die wirkliche Reichweite anpassen. Historische Aussagen als historische Aussagen erhalten; keine alten Belegpässe rückwirkend „korrigieren“.

**Abnahme:** Aktive Verweise erreichen existierende Ziele. Die aktuelle Startseite und README führen konsistent zum unterstützten Sammlerpfad. Historische Berichte bleiben datierte Evidenz statt einer zweiten Prioritätenliste.

## 6. Komplexität und Effizienz im Detail

### 6.1 Größe ist ein Hinweis, kein Urteil

| Messung | Ergebnis |
|---|---:|
| Versionierte Dateien | 9.727 |
| Versionierter Arbeitsbaum | 878,11 MiB |
| Aktive Python-Dateien ohne Tests/Pässe/Archiv | 43 |
| Zeilen dieser aktiven Python-Dateien | 27.223 |
| Python-Testdateien | 28 |
| Testzeilen | 8.855 |
| Alle versionierten Python-Dateien einschließlich Pässe | 144 |
| Aktive Funktionen nach Repository-Metrik | 802 |
| Funktionen oberhalb CC 10 | 177, rund 22 Prozent |
| Runtime-Frontend | 1.701 Zeilen JS, 678 Zeilen CSS |

Die Repository-Metrik ist ein eigener deterministischer AST-Zähler, keine vollständige Messung kognitiver Komplexität oder Testabdeckung. Historische Pässe, Tests und JavaScript gehen nicht in ihren aktiven Python-Grenzwert ein. Sie bewertet geschachtelte Funktionen getrennt und bildet nicht jede Belastung durch große gekoppelte Abläufe ab.

### 6.2 Wichtigste Funktionen

| Datei / Funktion | CC | Umfang / Einordnung |
|---|---:|---|
| `asia_locality_matrix.py:175 validate` | 111 | 249 Zeilen; umfangreicher fachlicher Validator, Regeln sinnvoll gliedern, nicht pauschal löschen |
| `database.py:638 build_database` | 98 | 499 Zeilen; Schemaaufbau, Normalisierung und Datenbefüllung in einem Ablauf |
| `collector_catalogue.py:1785 validate_catalogue` | 89 | zentrale Vertragsprüfung, hohe Folgewirkung einer falschen Vereinfachung |
| `authoritative_graph.py:157 project_physical_evidence` | 79 | 316 Zeilen; kritisch für Identität und Provenienz, zuerst F02/F03 absichern |
| `collector_catalogue.py:1005 build_catalogue` | 79 | 582 Zeilen einschließlich geschachtelter Bausteine |
| `card_discovery.py:578 validate_contract` | 67 | 193 Zeilen; Eingangsgrenze beibehalten |
| `collector_catalogue.py:1185 common_item` | 64 | viele alternative Quellen/Fallbacks; Feldherkunft explizit halten |
| `checklist.py:129 main` | 63 | 225 Zeilen; ältere Semantik, vor großem Refactor den künftigen Consumer-Pfad entscheiden |
| `card_discovery.py:1057 build_projection` | 62 | 262 Zeilen; gemessener Performance-Schwerpunkt liegt zusätzlich in den wiederholten Parsern |
| `source_capabilities.py:213 validate_semantics` | 61 | wichtige Routinggrenze; keine generische Graph-Engine notwendig |
| `fetch_attachment.py:765 command_issue` | 54 | vertrauliche/ungeprüfte Eingaben werden zu Belegen; Validierung und Rollback erhalten |
| `site.py:405 main` | 32 | 627 Zeilen, großer Anteil deklaratives HTML; kein Beweis für 627 Zeilen komplizierte Fachlogik |

`verification/review_findings.py` umfasst 3.517 Zeilen. Einige seiner großen Blöcke bestehen aus mechanisch geschachtelten Teilfunktionen und gemeinsamem Zustand. Hier wäre eine fachliche Gliederung ein wirklicher Gewinn. Das Modul in dutzende Dateien nach Checknummer zu zerlegen wäre dagegen eher neue Navigation als weniger Komplexität.

### 6.3 Was gezielt vereinfacht werden kann

Die folgenden Größen sind grobe lokale Schätzungen, keine bereits gemessenen Einsparungen. Überlappungen sind nicht doppelt zu zählen.

| Kennung | Konkreter Schnitt | Ersatz | Größenordnung |
|---|---|---|---:|
| `shrink` | Doppelte Produktprojektion in `_project_cards()` und `reproject()` in `finishes.py` | ein Aufruf der vorhandenen gemeinsamen Projektion | etwa 60–80 Zeilen |
| `shrink` | Zweite Normalisierung/Definition derselben Druckidentität im Collector | eine kanonische Signatur mit vorhandenen Validierungsgrenzen | etwa 15–30 Zeilen |
| `delete` | Veraltete Pages-Generatorliste im Messprofil | Messung des heutigen Artefakt-Handoffs | etwa 10–20 Zeilen |
| `shrink` | Opaque `_partN`-Closures und `nonlocal`-Gerüst in Findings | fachlich benannte, explizite Übergaben | Einsparung erst nach einem einzelnen umgebauten Block seriös bezifferbar |
| `native` | Vollständig erzeugte, unbenutzte Artwork-Formulare | native Disclosure-Bereiche und kleine Renderfenster | primär weniger DOM-/Layoutarbeit, nicht zwingend weniger Quelltext |
| `stdlib` | Wiederholtes Parsen gleicher Antwortbytes | begrenzter In-Process-Cache mit vollständigem Schlüssel | primär weniger Rechenarbeit, keine neue Abhängigkeit |

**Vorsichtige direkte Netto-Schätzung:** etwa 85–130 Zeilen weniger und 0 neue Abhängigkeiten für die ersten drei Schnitte. Für größere Umbauten wird ausdrücklich keine erfundene Nettozahl angegeben. Sicherheitsprüfungen, Migrationsdaten und unveränderliche Belege sind kein Kürzungsmaterial.

### 6.4 Gemessene Laufzeit und Konsequenz

| Schritt im ersten vollständigen Gate | Sekunden |
|---|---:|
| `test_findings_harness.py` | 147,11 |
| `card_discovery.py --check` | 103,40 |
| `review_findings.py` | 35,59 |
| `test_authoritative_graph.py` | 8,28 |
| `fetch_attachment.py --evidence-check` | 4,56 |
| Restliche protokollierte Schritte | 31,83 |
| **Summe der 55 protokollierten Schritte** | **330,77** |

Die ersten drei Schritte verursachen rund 86,5 Prozent der gemessenen Zeit. Deshalb zuerst diese Arbeit verstehen und reduzieren. Mikrooptimierungen an kleinen JSON-Helfern oder ein Rewrite der SQLite-Übergabe lösen den gemessenen Engpass nicht. Die erste Messung lief während weiterer lesender Auditarbeit und ist ein lokaler Orientierungswert, keine kontrollierte Leistungszusage.

## 7. Daten- und Produktfragen, die nicht als bewiesene Fehler ausgegeben werden dürfen

1. **Offene Quellen sind nicht automatisch Codefehler.** 11 unzureichend belegte Sprachclaims, 4 ungeklärte Widersprüche, unvollständige Finishes und fehlende Künstler sind ehrliche Forschungszustände. Sie durch Heuristik zu schließen wäre eine Verschlechterung.
2. **`complete` im Completeness-Gate ist begrenzt.** Die aktuellen retained Eingaben sind bilanziert; nicht alle historischen Snorlax-Drucke entdeckt. Vollständigkeitsprosa muss diesen Bezug behalten.
3. **Nicht jeder Discovery-Adapter entdeckt neue Dinge.** `confirmed-source-json`, `source-first-print-json` und die historischen positiven Frontiers können bereits geprüfte IDs erneut transportieren. Das ist als Wiederholungs-/Kompatibilitätsweg zulässig, ersetzt aber keine unabhängige Suche nach unbekannten Karten. Diese Reichweiten sollten je Slice lesbar bleiben.
4. **Artwork-Import ist noch kein geschlossener Arbeitsablauf.** ADR-0007 nennt ausdrücklich keinen vorhandenen Importer/Entscheidungsstore. Downloadbare Vorschläge sind implementiert; automatische oder kanonische Übernahme ist eine ausstehende Produktentscheidung, kein heimlicher Funktionsumfang.
5. **`errorClass` ist bislang ein Ausbaupunkt.** Alle aktuellen physischen Graph-Drucke haben keinen positiven `errorClass`-Wert. Die Signaturfunktionen berücksichtigen das Feld nicht und der physische Projektor setzt es auf `None`. Vor dem ersten echten Fehlerkartenfall muss geklärt werden, ob dies eine Druckidentität oder eine individuelle Exemplareigenschaft ist. Jetzt ohne konkrete Evidenz neue Kartenarten zu erzeugen wäre falsch.
6. **Der eigene Schema-Validator ist bewusst begrenzt.** Er validiert einen verwendeten JSON-Schema-Teilumfang. Eine Schema-Erweiterung muss deshalb gegen seinen tatsächlich implementierten Umfang geprüft werden; die bloße Existenz einer `.schema.json` garantiert keine vollständige Standardvalidierung. Kein unbedingter Auftrag für eine zusätzliche Laufzeitabhängigkeit.
7. **Die alte SQLite-Schnittstelle hat reale Nutzerverträge.** Sie allein wegen der neuen Collector-Projektion abrupt zu entfernen würde Migrationen und private Tracker riskieren. Erst eindeutige neue Einstiegspunkte und ein überprüfter Kompatibilitätsplan, dann eine mögliche Stilllegung.
8. **Die Lizenzdokumente sind vorhanden und technisch geprüft.** Dieses Audit trifft keine neue rechtliche Aussage über einzelne Drittanbieterbilder und ändert keine bestehende Freigabe. Eine Vorschaupipeline muss die bestehenden Herkunfts- und Freigabegrenzen respektieren.

## 8. Abdeckung nach Teilbereich

| Bereich | Schwerpunkt dieser Prüfung | Ergebnis / Folgearbeit |
|---|---|---|
| Legacy-Baseline, `analyze.py` | Mitgliedschaft, Inputrolle, reine Auswertungen | gute historische Grenze; gemischte Zieldatei präzisieren, F12 |
| Evidenzsemantik, `absence_model.py`, Sprachstatus | Granularität, Scope, Eigentümerentscheidung | Grundmodell gut; F01 ist die wesentliche Schwachstelle |
| Editionen und chronologische Releases | Vermeidung erfundener Kreuzprodukte, Datumsscope, alte Consumer | ausdrückliche Zuordnungen erhalten; viele fehlende Zeilenquellen bleiben Forschungsbedarf |
| Finish-Pipeline und Snapshot | Offlinebetrieb, Kandidatenannahme, Projektion | gute Trennung; F04, doppelte Projektion und F11 korrigieren |
| Specimen-Importer | Manifest, Herkunft, Format, Hash, Rollback | sinnvoller zentraler Eingang; keine neuen Routinepässe statt des Importers |
| Quellenregister und Capability-Modell | Provider-Routing und positive Reichweite | fachlich sinnvoll; keine Abwesenheitsautorität hinzufügen |
| Set-/Card-Discovery | Raw-Retention, inkompatible/fehlgeschlagene Runs, Wiederholung | starke Nachvollziehbarkeit; Performance F13 und Loop-Auswahl F09 |
| Lokalitätsmatrizen und Completeness | Bilanzierung, Grenzen, unabhängige Lokalität | sinnvoll; komplexe Validatoren gezielt lesbarer machen |
| Autoritativer Graph | Teilprojektion, Signaturen, Referenzen, Schreibreihenfolge | F02/F03/F12 zuerst beheben |
| Alte Checkliste, SQLite, Tracker | Status, Besitzschutz, logische DB-Deterministik | stabile Trennung privater Daten gut; F04/F06 betreffen Nutzersicherheit |
| Collector-Vertrag und Migrationen | Item-Grain, progressClass, Alt-IDs, Hashes | guter neuer Consumer-Pfad; F02 und klare Einstiegsempfehlung fehlen |
| Artwork-Projektion und Browser | IDs, Bildgruppen, Versionsbindung, Formulare, Download | F07/F08/F14/F18; noch kein angenommener Decision-Import |
| Hauptwebsite, Print und Exporte | reale Interaktion, mobile Breiten, Themes, Dateipfade | 122 Checks grün; alte Semantik und große Zusatzoberfläche adressieren |
| README, Handover, Regeln, ADRs | Zuständigkeit, aktuelle versus historische Aussage | wertvolle Dokumentation, aber F12/F19 und zu viele konkurrierende Einstiegssignale |
| Regen, Scoped Lanes, Loops, Messung | Reihenfolge, Status, Seiteneffekte, Kosten | F04/F05/F09/F10/F16 |
| Publikation und Gate-Manifeste | Allowlist, lokale Referenzen, Commit-/Katalogbindung | geprüftes Artefakt konsistent; Bildkosten F15 und P6-Ausnahme F05 |
| Tests und Komplexitätsguard | vorhandene Abdeckung und negative Ergänzungen | breite Baseline, aber konkrete Lücken; F17 beschreibt sinnvolle Weiterentwicklung |
| Historische Pässe und Archiv | aktive Rolle, Hashschutz, Nicht-Wiederholung | bewahren; erst bei fachlich gleichwertiger Regression kontrolliert archivieren |

## 9. Regeln für die spätere Umsetzung durch 5.6 Luna Max

Diese Übergaberegeln beschreiben die Umsetzung des Audits. Die ausführlichen bestehenden Repository-Regeln bleiben in [CLAUDE.md](CLAUDE.md), die Pipeline in [WORKFLOW-MAP.md](WORKFLOW-MAP.md) und [scripts/regen.py](scripts/regen.py).

1. **Befund zuerst erneut reproduzieren.** Der Umsetzungsbranch wird vom dann aktuellen `origin/main` erstellt. Ein hier beschriebener Fehler kann bis dahin bereits behoben sein.
2. **Ein begrenztes Problem pro Änderung.** Kein gemeinsamer Megarefactor aus Evidenzsemantik, Graphmigration, UI und Performance.
3. **Positive Belege erhalten.** Keine verlorene Karte aus einem fehlenden Datenbanktreffer ableiten; keine Sprache in ein Finish umdeuten; keine Nachbarevidenz für die Zielkarte ausgeben.
4. **Eigentümerentscheidung nicht erfinden.** Abwesenheit und abgeschlossene Finishlisten verlangen die bereits festgelegten Entscheidungsgrenzen. Das Audit erteilt keine neuen Datenentscheidungen.
5. **IDs und private Sammlung vor Formatästhetik schützen.** Vor einer geänderten Signatur Alt-IDs, 1:1-Rekeys und 1:N-Splits bilanzieren. Mengen, Notizen und bewusste Besitzerzustände dürfen nicht automatisch auf einen anderen Druck wandern.
6. **Vor dem Schreiben validieren.** Geprüfte Eingaben bleiben bei Parser-, Validierungs-, Netz- oder Schreibfehlern erhalten. Kleine lokale Transaktionen reichen; kein allgemeines Transaktionsframework nötig.
7. **Prüfen heißt beobachten.** Keine Produktionsdatei zurückschreiben, keine Zeitstempel ändern und keine vorhersehbaren Nachbarpfade beanspruchen. Temporäre Vergleichsartefakte außerhalb des geprüften Baums halten.
8. **Fehler ehrlich ausgeben.** Ein übersprungener oder eingeschränkter Gate ist kein vollständiger Erfolg. „Gespeichert“ verlangt erfolgreiches Speichern; „CI grün“ verlangt tatsächlich gelesenen CI-Zustand.
9. **Eine Fachregel, eine Implementierung.** Insbesondere Drucksignatur, Anwendungsstatus, kanonische Run-Auswahl und Consumer-Fortschritt nicht erneut in einem weiteren Skript nachbauen.
10. **Weniger Arbeit vor mehr Parallelität.** Wiederholte Parses und DOM-Erzeugung beseitigen, bevor Threads, Prozesse, Worker oder neue Infrastruktur hinzukommen. Unveränderliche Belege bleiben überprüfbar.
11. **Originalbilder bleiben Beweisbilder.** Vorschaubilder sind gesonderte abgeleitete Assets. Keine komprimierte Datei unter einem bestehenden SPEC-Originalpfad ablegen.
12. **Keine mechanische CC-Kosmetik.** Gute Namen und explizite Übergaben sind wichtiger als eine neue `_part7`-Funktion. Ausnahmen nicht aufweichen; erforderliche Validierung nicht entfernen.
13. **Tests müssen den Fehler verhindern.** Die isolierten Reproduktionen aus F01–F11 in bestehende passende Suites integrieren. Nicht für jeden simplen Helfer neue Testdateien und kein neues Testframework anlegen.
14. **Dokumentation nach dem finalen Verhalten aktualisieren.** Keine zweite vollständige Befehlsliste in diesem Bericht oder einer neuen Workflowdatei pflegen. Historische Dokumente als historische Dokumente behandeln.
15. **Scoped Gates bleiben Hilfsmittel.** Vor einer späteren Zusammenführung den aktuellen vollständigen Repository-Gate ausführen; Browser-/Publikationsprüfung passend zum Änderungsbereich ergänzen. Für tatsächliche Commits/Pushes die bestehenden Historienregeln beachten.
16. **Keine Umsetzung durch diesen Bericht behaupten.** Checklisten werden erst nach bestandenem Abnahmekriterium abgehakt. Dieses Audit wurde ohne Implementierung erstellt.

## 10. Empfohlene Reihenfolge der Umsetzung

| Schritt | Befunde | Begrenztes Ergebnis | Abhängigkeit |
|---|---|---|---|
| 1 | F04, danach F03/F11 | sichere Prüf-, Graph- und Recording-Pfade mit Fehlerregressionen | keiner; getrennte kleine Änderungen |
| 2 | F05 | vollständiger Gate kann keinen relevanten P6-Fehler mehr als Erfolg melden | keiner |
| 3 | F02 | gemeinsame reihenfolgeunabhängige Drucksignatur, erhaltene Alt-IDs | vor Änderungen am Consumer-Matching |
| 4 | F01 | explizite Evidenzgranularität statt freier Worttreffer | sorgfältige Legacy-Zuordnung, fachliche Regeln lesen |
| 5 | F06 | klarer neuer Sammlereinstieg und kompatible Kandidaten-/Trackerbehandlung | Identitäts-/Migrationsschutz aus Schritt 3 |
| 6 | F07, F08 | korrekt versionierte und verlustarme Review-Vorschläge | vor größeren UI-Umbauten |
| 7 | F09, F10 | reproduzierbare Run-Auswahl und ehrliche Workflow-Messung | vor neuen Performancebehauptungen |
| 8 | F13, F16 | weniger wiederholte Parser-/Prüfarbeit und passende Browser-CI | Messbasis aus Schritt 7 |
| 9 | F14, F15 | kleine initiale Review-Oberfläche und geeignete Vorschaubilder | Persistenzschutz aus Schritt 6 |
| 10 | F12, F17, F18, F19 | eindeutige Autorität, gezielte fachliche Vereinfachung, klare Dokumentation | schrittweise; keine vollständige Neuarchitektur voraussetzen |

F12 und die jeweils unmittelbar betroffenen Dokumentationsstellen sollten bereits bei den früheren Schritten präzisiert werden. Die Tabelle meint nicht, dass wichtige Erklärungen bis zum letzten Schritt warten müssen.

Für den ersten Umsetzungslauf genügen die konkreten Sicherheits- und Integritätskorrekturen aus den Schritten 1 bis 3. Danach neu messen und die nächsten abgegrenzten Änderungen wählen. Die Reihenfolge verlangt keine parallelen Agenten und keine neu angelegte Aufgabenstruktur.

## 11. Durchgeführte Verifikation

| Prüfung | Ergebnis |
|---|---|
| `git fetch origin`, Branch-/Tree-Vergleich | aktuelle Remote-Information gelesen; inhaltsgleich mit `origin/main` |
| AST-Parsing aller versionierten Python-Dateien | 144 Dateien, keine Syntaxfehler |
| Repository-Komplexitätsmessung | 802 aktive Funktionen, 177 bestehende Ausnahmen, keine Baseline-Überschreitung |
| `python scripts/regen.py --check` | Exit 0; 55 protokollierte Schritte, Summe 330,77 s; kein `[FAIL]` |
| Git-Status nach vollständigem Gate und Reproduktionen | sauber, bevor dieser Bericht angelegt wurde |
| `python verification/test_site.py` | Exit 0; 122/122 Browserchecks bestanden |
| Zusätzlicher HTTP-Browserlauf | kein JavaScript-Laufzeitfehler; fünf Viewportbreiten ohne Gesamtseitenüberlauf |
| `python verification/verify_finish_sources.py` | Exit 0; 13 TCGCSV-Produkte über 8 Quellenrecords live geprüft |
| Publikationsbuild und `publish.verify()` in temporärem Ziel | Exit 0; 648 Dateien, 743.254 KiB; Allowlist und lokale Links bestanden |
| Separates `cProfile` für Card-Discovery-Check | Exit 0; 23 Run-Projektionen, 44,54 s im späteren instrumentierten Lauf |
| Zusätzliche negative Reproduktionen | F01–F05 sowie F07–F11 bestätigt; F06 durch aktuelle Daten-/SQLite-Abfragen bestätigt |

Für den Publikationsversuch wurden die bestehenden `build()`-/`verify()`-Funktionen verwendet und ausschließlich die Zielpfadprüfung im Auditprozess auf genau ein temporäres Verzeichnis außerhalb des Repositorys beschränkt. Es wurde keine Produktionsdatei dafür angepasst und kein Deployment ausgeführt. Die reguläre Schutzprüfung für `_site*` wurde hier nicht erneut als CLI-End-to-End-Test bewertet.

Die vorhandene Browser-Suite deckt unter anderem A4/Letter-Druck, Dark Mode, Kontrastmessungen, Sortierung, Filter, URL-Roundtrip, Bilder, lokale Vorschläge und TSV-Export ab. Sie deckt die zusätzlich gefundenen Speicher- und Versionsfehler bisher nicht hinreichend ab. Ein bestandener Test ist deshalb in diesem Bericht immer an seinen konkreten Prüfbereich gebunden.

## 12. Umsetzungsstatus

- [x] Zielsetzung aus Historie und aktuellen Aufträgen rekonstruiert.
- [x] Aktuellen Daten-, Code-, UI- und Workflowstand geprüft.
- [x] Vorhandene Gates und zusätzliche isolierte Fehlerreproduktionen ausgeführt.
- [x] Beobachtungen, Regeln und Abnahmekriterien in `ASTRA.md` zusammengeführt.
- [ ] F01–F19 später am dann aktuellen Stand erneut bewerten und gegebenenfalls umsetzen.

**Es wurde ausschließlich dieser Bericht erstellt. Keine Korrektur aus F01–F19 ist durch dieses Audit umgesetzt.**
