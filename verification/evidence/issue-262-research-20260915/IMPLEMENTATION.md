<!-- doc: role=Thai issue 262 draft implementation handoff; stage=reference -->
# Umsetzung der Empfehlungen aus #262

Stand: 15.09.2026. Branch: `codex/research-262-20260915`, Basis `2c1818c01f299d5f085721145a9d05e3f7dfebeb`. Sammelstand für einen ausdrücklich gewünschten Entwurfs-PR; weitere Recherche folgt. Noch nicht gemergt.

Der neu erzeugte Katalog erreicht **13/28 lückenfreie Thai-Veröffentlichungen** statt 8/28. Es bleiben 15 Veröffentlichungen mit fehlender physischer Bestätigung: zwölf ohne Kandidat und drei mit noch unbelegtem Kandidat. MA6 T 121/130 hat zusätzlich eine Seltenheitslücke. Die beiden Datumslücken sind geschlossen. Das ist keine Behauptung einer vollständigen Variantenliste.

## Umgesetzte Änderungen

- **s5a T 093/070:** offizielles Veröffentlichungsereignis am 30.04.2021.
- **s10a T 077/071:** offizielles Veröffentlichungsereignis am 29.07.2022.
- Beide Daten liegen in getrennten Quellen- und Ereignisdatensätzen mit einer auf die zwei offiziellen Thai-Seiten begrenzten Quellenfähigkeit. Die Foto-Belege bleiben für Identität und Finish zuständig; ihre eigenen Datumseinträge werden nicht mit Fremdquellen überschrieben.
- **SV-P 082/SV-P:** vorhandener Non-Holo-Override wird über den korrekten Legacy-Schlüssel `082` gefunden. Die lokale Sammlernummer bleibt `082/SV-P`. Stempeltext ist `CENTRAL PATTANA`; der Veranstaltungsname bleibt Verteilungskontext.
- **SPEC-0526:** originales Verkäufer-JPEG von sc3b T 126/158 mit sichtbarem Holo-Effekt, aufgenommen über den vorhandenen Manifest-Importer.
- **SPEC-0527:** vom Bildserver gelieferte JPEG-Fassung des geprüften sv4a T 145/190-Fotos mit sichtbarem Reverse-Holo-Effekt. Keine lokale Bildkonvertierung. Die vorhandene Thai-Identität `sv4a` bleibt erhalten; der vollständige gedruckte Code ist im Beobachtungstext dokumentiert.

Ein genauer Folienmustername und Kartenmaße wurden aus den Bildern nicht behauptet. Die eBay-Rückseite bleibt Recherchematerial, weil sie selbst keine Thai-Identität oder Finish-Eigenschaft belegt. Das saubere Promo-Bild ist kein zusätzlicher physischer Non-Holo-Nachweis. Widersprüchliche Verkäufer-Metadaten wurden nicht übernommen.

## Prüfung

- Vollständige Ausgangsprüfung sauber. Der erste eingeschränkte Lauf konnte temporäre Datenbank-Prüfdateien nicht bearbeiten; der vollständige Lauf mit dem erforderlichen Zugriff bestand.
- Manifest-Import und Bildintegrität bestanden; Originalbytes und SHA-256 sind erhalten.
- Physischer Workflow: `20260915T094604Z-physical`, eine erfolgreiche Runde, Ende `no-metric-change`. Diese Bestandsmetrik ist kein selbstständiger Vollständigkeitsnachweis.
- Daten vollständig neu erzeugt. Bestehende Tests hatten feste alte Bestandszahlen: zwei Legacy-Einträge wechseln von Forschung zu bestätigt. Die erwarteten Zahlen sind jetzt 713 bestätigt, 113 Finish-Kandidaten und 72 Platzhalter; insgesamt weiterhin 898 Legacy-Checklistenpositionen.
- Gezielte Katalogtests prüfen beide Datum/Quellen-Paare, beide Verkäuferbild/Finish-Paare und die unveränderte lokale Promo-Identität samt richtigem Stempel.
- Beide neuen Specimen-IDs erreichen physische Graph-Knoten, Quellenregister und Artwork-Ansichten. Die öffentlichen Bild- und Quellenlinks erreichen den jeweiligen Katalogeintrag.
- Die abschließende vollständige Prüfung `python scripts/regen.py --check` ist erfolgreich: alle abgeleiteten Dateien und Kernregressionen sind aktuell.

## GitHub-Aktualisierung und Entwurfsstatus

Der Nutzer hat die Veröffentlichung des vorbereiteten Issue-Texts sowie einen PR mit allen bisherigen Änderungen ausdrücklich freigegeben. Der PR bleibt als Entwurf offen, während weitere Informationen gesammelt werden. Kein Merge und keine Schließung von #262 sind beauftragt.

Drei Quellenantworten enthalten technische Webseiten-Skripte, die für die Belege irrelevant sind. Ihre veröffentlichten Fassungen sind ausdrücklich als abgeleitete Textauszüge gekennzeichnet; Originalantworten bleiben unverändert im ignorierten lokalen Cache. Original- und Auszug-Prüfsummen sind separat dokumentiert. Laufprotokolle bleiben lokal, die Prüfergebnisse werden im PR zusammengefasst.

Aktueller Katalog-Fingerprint: `sha256:5ce3e811a65336158b29e4e4139f5b80c842bd0b57041cf747688b0cf31169bd`.

Die vollständige Nachher-Liste steht in [catalogue-after-implementation.json](catalogue-after-implementation.json). [README.md](README.md) bewahrt die ursprüngliche Recherche vor der Umsetzung. [issue-update.md](issue-update.md) enthält die Aktualisierung für GitHub mit getrenntem Main- und lokalem Stand. Die abschließenden Prüfergebnisse stehen in `final-check.log`.
