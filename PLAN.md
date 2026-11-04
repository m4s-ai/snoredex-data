<!-- doc: role=execution plan for the artwork gallery and binder; stage=task -->
# Snoredex Artwork-Galerie und Binder

Dieser ExecPlan bleibt während der Umsetzung aktuell. Siehe [OpenAI ExecPlan-Leitfaden](https://developers.openai.com/cookbook/articles/codex_exec_plans).

## Purpose / Big Picture

Über „Artwork gallery“ in der bestehenden Tabelle öffnet sich eine zweite, bildzentrierte Sicht des aktuellen Snoredex-Katalogs. Einzeldrucke bleiben getrennt. Nachdrucke desselben Motivs folgen auf das ursprüngliche Artwork. Der Binder zeigt dieselbe Reihenfolge auf konfigurierbaren Doppelseiten.

## Progress

- [x] (2026-11-04) Von aktualisiertem origin/main auf codex/artwork-gallery-plan abgezweigt.
- [x] (2026-11-04) Jungle, Pokémon Jungle, Legendary Collection und XY179 anhand lokaler Kartenbilder verglichen.
- [x] (2026-11-04) Galerieprojektion, Raster, Binder, Lightbox und lokales Fotoderivat implementiert. Der Projektionstest und die Allowlist-Prüfung des Pages-Artefakts sind grün.
- [x] (2026-11-04) Vollständigen Release-Check, 112 Browserprüfungen und die gezielte Galerieabnahme im gebauten Pages-Artefakt abgeschlossen.
- [x] (2026-11-04) Die vorhandene Artwork-Projektion für den gesamten Katalog übernommen und motivgleiche Bildgruppen anhand ihrer Kartenbilder verbunden.
- [x] (2026-11-04) Chronologische Artwork-Nummern ab 1 und umkehrbare Gruppensortierung für Galerie und Binder ergänzt.

## Surprises & Discoveries

- Die Artwork-Projektion enthält zur Planung keine geprüften Appearance-IDs. Automatische Bildgruppen sind Sichtungshilfen.
- CL 33 Prerelease und Staff sind als bestätigte englische Katalogeinträge vorhanden. Die französischen und italienischen Prerelease-Claims U0469 und U0471 stehen laut Evidenzprojektion auf `needs-evidence`. Sie bekommen eigene Recherchekacheln. Die italienische KSS Wave Holo ist eine Recherchehypothese. Der Owner hat Reverse Holo ausdrücklich ausgeschlossen und den belegten Finish-Stand bei Non-Holo geschlossen.

## Decision Log

- 2026-11-04. Aktive Katalogeinträge als Livebestand projizieren. Die KSS-Hypothese und die beiden offenen CL-Prerelease-Claims bleiben mit eigenen IDs und Evidenzstatus auf die Galerie beschränkt.
- 2026-11-04. Fehlende exakte Bilder behalten einen neutralen Platzhalter. Vorhandene exakte Render und Fotos verwenden lokale Derivate. Ein separat aufbereitetes Foto behält einen Verweis auf das unberührte SPEC-Original.
- 2026-11-04. Fünf vorhandene englische Kartenbilder wurden anhand der sichtbaren Merkmale konkreten Druckeinträgen zugeordnet. Die Zuordnung gilt ausschließlich für diese Einträge.
- 2026-11-04. Fortlaufendes Raster als Einstieg, 3×3 und seitenweise Befüllung als Binder-Standard. Der Browser hält diese Einstellungen bis zum Neuladen im Speicher.
- 2026-11-04. Artwork-Nummern bezeichnen die Position in der aktuellen historischen Reihenfolge. Ein später belegtes früheres Artwork kann nachfolgende Nummern verschieben. Stabile Katalog- und Gruppen-IDs bleiben die Referenz.

## Context and Orientation

scripts/site.py erzeugt die Website aus collector_catalogue.json. verification/artwork_review_projection.json liefert geprüfte Appearance-IDs, sofern vorhanden, und lokale Bildreferenzen. scripts/artwork_derivatives.py und sein Manifest liefern Thumbnail und Preview. scripts/publish.py bestimmt das freigegebene Pages-Artefakt.

## Plan of Work

1. Aktive Katalogeinträge mit ID, Merkmalen und Quellen in die Galerie übernehmen. Geprüfte Appearance-IDs bevorzugen. Die bestehenden Bildgruppen aus der Artwork-Projektion verwenden und Gruppen mit gesichtetem, gleichem Motiv zusammenführen. Das früheste belegte Datum eines bestätigten Gruppenmitglieds bestimmt die Gruppenposition. Die Kacheln behalten ihr eigenes Datum.
2. Aus scripts/site.py eine zweite Seite erzeugen und von der Tabelle verlinken. Auf Hover und Tastaturfokus erscheinen Set, Nummer und Künstler. Die Lightbox liefert Variante, Datum, Evidenzstatus und Quellen. Das Binder-Raster unterstützt zwei Seiten, 3×3, 4×4, 5×5 und freie Zeilen- und Spaltenwerte von 1 bis 8. Beide Befüllungsrichtungen verwenden dieselbe sortierte Liste.
3. Exakte lokale Bilder über Thumbnail und Preview anzeigen. Fotos mit geprüftem Zuschnitt getrennt speichern. Platzhalter bleiben interaktiv. Die Pages-Allowlist und der Browser-Workflow erfassen die neuen Dateien.

## Artifacts and Notes

site/gallery-review.json hält die Verbindungen zwischen bestehenden Bildgruppen, die konkreten Bildzuordnungen, die drei zusätzlichen Rechercheeinträge und die Zuschnittreferenz von SPEC-0601. Die vier Eckpunkte stehen in Originalpixeln in der Reihenfolge oben links, unten links, unten rechts, oben rechts. Für dieses Foto wurde die Kartenfläche mit Pillow QUAD und bikubischer Abtastung auf 520 × 728 Pixel ausgerichtet. Die WebP-Dateien wurden mit Qualitätsstufen 87 für die Vorschau und 84 für das 220 × 308 Pixel große Thumbnail gespeichert.

## Concrete Steps and Validation

Im Repository-Stamm python scripts/regen.py, python scripts/site.py --check und python verification/test_site.py ausführen. Dann python scripts/publish.py --out _site und python scripts/publish.py --out _site --verify ausführen. Die Projektion prüft Jungle mit LC 64 und XY179, deren Einzeldaten, CL 33 Prerelease und Staff, KSS und deterministische Sortierung. Im Browser müssen Navigation, Dialog, Fokus, Touch und Binderplatzierung funktionieren. Im 3×3-Binder wechselt Karte 4 von links in Zeile 2 zu rechts in Zeile 1.

## Interfaces and Dependencies

gallery.html verwendet lokale Styles und JavaScript sowie eine eingebettete, vom Site-Generator erzeugte Kartenliste. Die Eintrags-ID stammt aus dem Katalog, die Galerie-Hypothese hat eine eigene ID. Es gibt keinen neuen Browser-Speicher und keine Migration.

## Idempotence and Recovery

Der Site-Generator erzeugt dieselbe Projektion aus denselben Eingaben. Ein Rollback nimmt die Galerieänderungen zurück und generiert die Site erneut. Die Veröffentlichung folgt dem bestehenden Pages-Gate.

## Outcomes & Retrospective

Die Galerie projiziert 973 Kartenplätze in 54 Artwork-Gruppen. Alle 629 Releases sind über die vorhandene Artwork-Projektion abgedeckt. 244 bestehende Bildgruppen wurden nach visueller Sichtung zu 50 gemeinsamen Motiven verbunden. Vier eigenständige Bildgruppen bleiben separat. Von den Kartenplätzen haben 323 ein konkret zugeordnetes Bild und 650 einen Platzhalter.

Der abschließende Lauf von `python scripts/regen.py --check` bestätigte die Generatoren und Kernregressionen. Die Browser-Suite meldete 112 von 112 bestandene Prüfungen. Chrome lud außerdem die lokal gepackte Galerie samt Kartenbild und zeigte Hover-Effekt und Dunkelmodus im Pages-Artefakt.
