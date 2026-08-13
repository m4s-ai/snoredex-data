#!/usr/bin/env python3
"""Replay the four LATAM/European Spanish admissions from issue #192.

The original mutations landed directly in c6ddefa; its declared predecessor is
bc2fc5549f7eb0e0045fa9ddfdbadadf9d8b1863. This is now the single write path for the four
source-first prints, SPEC-0033..0036 and their locality-bearing set profiles. Exact rows are
idempotent, missing rows are inserted, and conflicting rows are rejected. The retained official
image hashes are checked before any write; no missing asset is interpreted as absence.

    python verification/passes/admit_latam_spanish_prints_20260811.py
    python verification/passes/admit_latam_spanish_prints_20260811.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
DATA = json.loads(r'''{"prints":[{"printId":"LATAM:JTG LA:117/159:base","locality":"LATAM","localSetCode":"JTG LA","localNumber":"117/159","variant":"base","language":"Spanish","script":"Latn","name":"Snorlax de Paul","cardName":"Hop's Snorlax","catchUpOf":"the WEST Journey Together 117 work; equivalence is not admitted here","specimenId":"SPEC-0035","providerId":"pokemon-official","sourceUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SV09/SV09_LA_117.png","corroborated":false,"cardImageUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SV09/SV09_LA_117.png","translation":"Raciones Extra; Plancha Dinámica","distribution":"Latin America, established by the official es-xl asset and the printed LA modifier","evidence":"The official Latin-American Spanish card asset is retained as SPEC-0035. Its lower-left identifier reads the complete printed code \"JTG LA 117/159\"; the card is \"Snorlax de Paul\" with \"Raciones Extra\" and \"Plancha Dinámica\". The LA modifier is part of the printed set code and is retained verbatim. This establishes only this LATAM/es-419 release and its identifiers; it does not establish finish, xJTG, Prize Packs, or a complete era. Retrieved 2026-08-11."},{"printId":"LATAM:SVP LA:184:base","locality":"LATAM","localSetCode":"SVP LA","localNumber":"184","variant":"base","language":"Spanish","script":"Latn","name":"Snorlax de Paul","cardName":"Hop's Snorlax","catchUpOf":"the WEST SVP 184 work; equivalence is not admitted here","specimenId":"SPEC-0033","providerId":"pokemon-official","sourceUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SVP/SVP_LA_184.png","corroborated":false,"cardImageUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SVP/SVP_LA_184.png","comparisonAssetUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-es/img/cards/web/SVP/SVP_ES_184.png","setBranding":"Aventuras Compartidas","translation":"Raciones Extra; Plancha Dinámica","distribution":"Latin America, established by the official es-xl asset and the printed LA modifier","evidence":"The official Latin-American Spanish promo asset is retained as SPEC-0033. It reads the complete printed code \"SVP LA 184\", carries the \"Aventuras Compartidas\" stamp, and uses \"Plancha Dinámica\". SPEC-0034 retains the publisher's European-Spanish comparison, which instead reads \"SVP ES 184\", carries \"Juntos de Aventuras\", and uses \"Presión Dinámica\". This positive pair establishes a separate LATAM/es-419 release without inferring finish or completeness. Retrieved 2026-08-11."},{"printId":"WEST:SVP ES:184:base","locality":"WEST","localSetCode":"SVP ES","localNumber":"184","variant":"base","language":"Spanish","script":"Latn","name":"Snorlax de Paul","cardName":"Hop's Snorlax","catchUpOf":"the legacy WEST Spanish SVP 184 work; equivalence is not admitted here","specimenId":"SPEC-0034","providerId":"pokemon-official","sourceUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-es/img/cards/web/SVP/SVP_ES_184.png","corroborated":false,"cardImageUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-es/img/cards/web/SVP/SVP_ES_184.png","comparisonAssetUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SVP/SVP_LA_184.png","setBranding":"Juntos de Aventuras","translation":"Raciones Extra; Presión Dinámica","distribution":"European Spanish, established by the official es-es asset and the printed ES modifier","evidence":"The official European-Spanish promo asset is retained as SPEC-0034. It reads the complete printed code \"SVP ES 184\", carries the \"Juntos de Aventuras\" stamp, and uses \"Presión Dinámica\". The publisher's LATAM counterpart SPEC-0033 instead reads \"SVP LA 184\", carries \"Aventuras Compartidas\", and uses \"Plancha Dinámica\". The full printed modifier remains part of the local set code. Retrieved 2026-08-11."},{"printId":"LATAM:POR LA:063/088:base","locality":"LATAM","localSetCode":"POR LA","localNumber":"063/088","variant":"base","language":"Spanish","script":"Latn","name":"Snorlax","cardName":"Snorlax","catchUpOf":"the WEST POR 063 work; equivalence is not admitted here","specimenId":"SPEC-0036","providerId":"pokemon-official","sourceUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/ME03/ME03_LA_63.png","corroborated":false,"cardImageUrl":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/ME03/ME03_LA_63.png","translation":"Comilona; Colapso","distribution":"Latin America, established by the official es-xl asset and the printed LA modifier","evidence":"The official Latin-American Spanish card asset is retained as SPEC-0036. Its lower-left identifier reads the complete printed code \"POR LA 063/088\" and its first attack is \"Comilona\"; the European-Spanish asset uses \"Glotón\" and the ES modifier. The LA modifier is retained as part of the local set code. This establishes this positive LATAM/es-419 card only, not finish, Prize Packs, or a complete set/era. Retrieved 2026-08-11."}],"specimens":[{"specimenId":"SPEC-0033","setCode":"SVP LA","number":"184","variant":"base","language":"Spanish","heldBy":"publisher or database","inspectedFrom":"official database scan","photograph":"SPEC-0033.png","photographSource":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SVP/SVP_LA_184.png","observed":"Official Latin-American Spanish scan of Snorlax de Paul: HP 150, Ability \"Raciones Extra\", attack \"Plancha Dinámica\" 140, Illus. OKACHEKE, regulation mark I, complete printed code \"SVP LA 184\", and an \"Aventuras Compartidas\" artwork stamp. The paired European-Spanish official scan, SPEC-0034, instead reads \"SVP ES 184\", \"Presión Dinámica\", and \"Juntos de Aventuras\". No finish is inferred from a publisher render.","recordedAt":"2026-08-11","citedBy":["LATAM:SVP LA:184:base"]},{"specimenId":"SPEC-0034","setCode":"SVP ES","number":"184","variant":"base","language":"Spanish","heldBy":"publisher or database","inspectedFrom":"official database scan","photograph":"SPEC-0034.png","photographSource":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-es/img/cards/web/SVP/SVP_ES_184.png","observed":"Official European-Spanish scan of Snorlax de Paul: HP 150, Ability \"Raciones Extra\", attack \"Presión Dinámica\" 140, Illus. OKACHEKE, regulation mark I, complete printed code \"SVP ES 184\", and a \"Juntos de Aventuras\" artwork stamp. The paired Latin-American official scan, SPEC-0033, instead reads \"SVP LA 184\", \"Plancha Dinámica\", and \"Aventuras Compartidas\". No finish is inferred from a publisher render.","recordedAt":"2026-08-11","citedBy":["WEST:SVP ES:184:base"]},{"specimenId":"SPEC-0035","setCode":"JTG LA","number":"117/159","variant":"base","language":"Spanish","heldBy":"publisher or database","inspectedFrom":"official database scan","photograph":"SPEC-0035.png","photographSource":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SV09/SV09_LA_117.png","observed":"Official Latin-American Spanish scan of Snorlax de Paul: HP 150, Ability \"Raciones Extra\", attack \"Plancha Dinámica\" 140, Illus. GOSSAN, regulation mark I, and complete printed code \"JTG LA 117/159\". The official European-Spanish asset reads \"JTG ES 117/159\" and uses \"Presión Dinámica\". No finish is inferred from a publisher render.","recordedAt":"2026-08-11","citedBy":["LATAM:JTG LA:117/159:base"]},{"specimenId":"SPEC-0036","setCode":"POR LA","number":"063/088","variant":"base","language":"Spanish","heldBy":"publisher or database","inspectedFrom":"official database scan","photograph":"SPEC-0036.png","photographSource":"https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/ME03/ME03_LA_63.png","observed":"Official Latin-American Spanish scan of Snorlax: HP 160, attacks \"Comilona\" and \"Colapso\" 160, Illus. Yoshinobu Saito, regulation mark I, and complete printed code \"POR LA 063/088\". The official European-Spanish asset reads \"POR ES 063/088\" and uses \"Glotón\". No finish is inferred from a publisher render.","recordedAt":"2026-08-11","citedBy":["LATAM:POR LA:063/088:base"]}],"setProfiles":[{"sourceRecordId":"SET-SRC-SF-05381DCC46F8","sourceKind":"source-first-local-set-profile","provider":"mixed-positive-evidence","providerRecordKey":"LATAM\u001fJTG LA","retrieved":"2026-08-11","raw":{"localCode":"JTG LA","localName":null,"locality":"LATAM","languages":["Spanish"],"scripts":["Latn"],"printIds":["LATAM:JTG LA:117/159:base"],"providers":["pokemon-official"],"sourceUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SV09/SV09_LA_117.png"],"printedSetSize":159,"printedSetSizeBasis":"the denominator printed beside the collector number on the observed official card asset","localeSuffix":"LA","observedCollectorNumbers":["117/159"],"observedCoverage":"one official Snorlax card asset, not an enumeration of the set","markAssetUrls":[],"cardImageUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SV09/SV09_LA_117.png"]}},{"sourceRecordId":"SET-SRC-SF-6261E7F61EB7","sourceKind":"source-first-local-set-profile","provider":"mixed-positive-evidence","providerRecordKey":"WEST\u001fSVP ES","retrieved":"2026-08-11","raw":{"localCode":"SVP ES","localName":null,"locality":"WEST","languages":["Spanish"],"scripts":["Latn"],"printIds":["WEST:SVP ES:184:base"],"providers":["pokemon-official"],"sourceUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-es/img/cards/web/SVP/SVP_ES_184.png"],"printedSetSize":null,"printedSetSizeBasis":"the promo number has no printed denominator; no set size is inferred","localeSuffix":"ES","observedCollectorNumbers":["184"],"observedCoverage":"one official Snorlax promo asset, not an enumeration of the promo series","markAssetUrls":[],"cardImageUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-es/img/cards/web/SVP/SVP_ES_184.png"]}},{"sourceRecordId":"SET-SRC-SF-A58455C4E46C","sourceKind":"source-first-local-set-profile","provider":"mixed-positive-evidence","providerRecordKey":"LATAM\u001fSVP LA","retrieved":"2026-08-11","raw":{"localCode":"SVP LA","localName":null,"locality":"LATAM","languages":["Spanish"],"scripts":["Latn"],"printIds":["LATAM:SVP LA:184:base"],"providers":["pokemon-official"],"sourceUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SVP/SVP_LA_184.png"],"printedSetSize":null,"printedSetSizeBasis":"the promo number has no printed denominator; no set size is inferred","localeSuffix":"LA","observedCollectorNumbers":["184"],"observedCoverage":"one official Snorlax promo asset, not an enumeration of the promo series","markAssetUrls":[],"cardImageUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/SVP/SVP_LA_184.png"]}},{"sourceRecordId":"SET-SRC-SF-C0C742569A70","sourceKind":"source-first-local-set-profile","provider":"mixed-positive-evidence","providerRecordKey":"LATAM\u001fPOR LA","retrieved":"2026-08-11","raw":{"localCode":"POR LA","localName":null,"locality":"LATAM","languages":["Spanish"],"scripts":["Latn"],"printIds":["LATAM:POR LA:063/088:base"],"providers":["pokemon-official"],"sourceUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/ME03/ME03_LA_63.png"],"printedSetSize":88,"printedSetSizeBasis":"the denominator printed beside the collector number on the observed official card asset","localeSuffix":"LA","observedCollectorNumbers":["063/088"],"observedCoverage":"one official Snorlax card asset, not an enumeration of the set","markAssetUrls":[],"cardImageUrls":["https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/img/cards/web/ME03/ME03_LA_63.png"]}}],"assetHashes":{"SPEC-0033.png":"1c34eb3ec73660374eb12ea12d8f1e94b23b7479875249a88fec845ab3d402dc","SPEC-0034.png":"a1efa806f7cc9d4750bf1537336a9fa1195a709eecdaa8e1494fd31a4a72ff67","SPEC-0035.png":"c96add035a691266bd55695bfa17536037b75fdd059a5516b649b8f60cadb365","SPEC-0036.png":"9e5845d6bcafa4229e7f1c2d05e8925cb12c603653d7c625cd778f5f63f01f6a"}}''')


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def reconcile(rows: list[dict], expected: list[dict], key: str, check: bool) -> bool:
    by_id = {row[key]: row for row in rows}
    changed = False
    for wanted in expected:
        identifier = wanted[key]
        actual = by_id.get(identifier)
        if actual is None:
            if check:
                raise SystemExit(f"missing {key} {identifier}")
            rows.append(wanted)
            by_id[identifier] = wanted
            changed = True
        elif actual != wanted:
            raise SystemExit(f"drift in {key} {identifier}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    for name, expected in DATA["assetHashes"].items():
        path = VERIFY / "specimens" / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if actual != expected:
            raise SystemExit(f"retained asset missing or changed: {name}")

    prints_path = VERIFY / "source_first_prints.json"
    prints_doc = read(prints_path)
    changed = reconcile(prints_doc["prints"], DATA["prints"], "printId", args.check)
    expected_count = len(prints_doc["prints"])
    count_changed = prints_doc["meta"]["counts"].get("admitted") != expected_count
    if args.check and count_changed:
        raise SystemExit("source-first admitted count drift")
    if changed or count_changed:
        prints_doc["meta"]["counts"]["admitted"] = expected_count
        if changed:
            prints_doc["meta"]["generated"] = "2026-08-11"
        write(prints_path, prints_doc)

    specimens_path = VERIFY / "specimens.json"
    specimens_doc = read(specimens_path)
    changed = reconcile(specimens_doc["specimens"], DATA["specimens"], "specimenId", args.check)
    expected_count = len(specimens_doc["specimens"])
    count_changed = specimens_doc.get("count") != expected_count
    if args.check and count_changed:
        raise SystemExit("specimen count drift")
    if changed or count_changed:
        specimens_doc["count"] = expected_count
        write(specimens_path, specimens_doc)

    sets_path = VERIFY / "set_catalogue_sources.json"
    sets_doc = read(sets_path)
    records = sets_doc["sourceRecords"]
    changed = reconcile(records, DATA["setProfiles"], "sourceRecordId", args.check)
    if changed:
        wanted_ids = {row["sourceRecordId"] for row in DATA["setProfiles"]}
        records[:] = [row for row in records if row["sourceRecordId"] not in wanted_ids]
        insert_at = next((i for i, row in enumerate(records)
                          if row["sourceKind"] == "printed-set-size-record"), len(records))
        records[insert_at:insert_at] = DATA["setProfiles"]
    counts = sets_doc["meta"]["counts"]
    expected_total = len(records)
    expected_profiles = sum(row["sourceKind"] == "source-first-local-set-profile"
                            for row in records)
    count_changed = (counts.get("sourceRecords") != expected_total or
                     counts.get("sourceFirstLocalSets") != expected_profiles)
    if args.check and count_changed:
        raise SystemExit("set-catalogue source count drift")
    if changed or count_changed:
        counts["sourceRecords"] = expected_total
        counts["sourceFirstLocalSets"] = expected_profiles
        write(sets_path, sets_doc)

    print(("validated" if args.check else "replayed") +
          " 4 source-first prints, 4 specimens and 4 local-set profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
