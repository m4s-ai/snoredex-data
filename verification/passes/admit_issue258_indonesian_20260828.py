"""Admit reviewed positive Indonesian card evidence from issue #258."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import authoritative_graph as graph_projection  # noqa: E402
from admit_issue257_simplified_chinese_20260827 import (  # noqa: E402
    append_unique,
    encoded,
    source_profile,
    stable_profile_id,
    upsert_edge,
    upsert_entity,
    upsert_migration,
)


PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
FINISHES = ROOT / "verification" / "finish_overrides.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
DISCOVERY = ROOT / "verification" / "card_discovery_records.jsonl"
DISCOVERY_ADAPTERS = ROOT / "verification" / "card_discovery_adapters.json"
CAPABILITIES = ROOT / "verification" / "source_capabilities.json"


# Official detail records used by issue #258. Rarity is read from the exact retained
# publisher render (or recorded as a positive absence of a printed rarity symbol).
OFFICIAL: dict[str, dict[str, Any]] = {
    "454": {"print": "ID:sc1a I:127/154:base", "code": "sc1a I", "number": "127/154", "work": "Snorlax-Collect-Collapse", "rarity": ("U", "uncommon")},
    "600": {"print": "ID:sc1b I:119/153:base", "code": "sc1b I", "number": "119/153", "work": "Snorlax-V-Swallow-Falling-Down", "rarity": ("RR", "double-rare")},
    "601": {"print": "ID:sc1b I:120/153:base", "code": "sc1b I", "number": "120/153", "work": "Snorlax-VMAX-G-Max-Fall", "rarity": ("RRR", None)},
    "764": {"print": "ID:sc1D I:132/164:base", "code": "sc1D I", "number": "132/164", "work": "Snorlax-Rolling-Tackle-Heavy-Impact", "rarity": ("no printed rarity symbol", "fixed")},
    "765": {"print": "ID:sc1D I:133/164:base", "code": "sc1D I", "number": "133/164", "work": "Snorlax-V-Swallow-Falling-Down", "rarity": ("no printed rarity symbol", "fixed")},
    "1605": {"print": "ID:AS1b:112/150:base", "code": "AS1b", "number": "112/150", "work": "Snorlax-GX-Collapse-Thunderous-Snore-Pulverizing-Pancake-GX", "rarity": ("RR", "double-rare")},
    "2129": {"print": "ID:AC3a:145/205:base", "code": "AC3a", "number": "145/205", "work": "Snorlax-Lazy-Eating-Big-Counter", "rarity": ("C", "common")},
    "2501": {"print": "ID:AC3D:120/172:base", "code": "AC3D", "number": "120/172", "work": "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", "rarity": ("no printed rarity symbol", "fixed")},
    "2796": {"print": "ID:scA I:084/135:base", "code": "scA I", "number": "084/135", "work": "Snorlax-Gormandize-Body-Slam", "rarity": ("no printed rarity symbol", "fixed")},
    "3466": {"print": "ID:AS1D:108/140:base", "code": "AS1D", "number": "108/140", "work": "Snorlax-GX-Collapse-Thunderous-Snore-Pulverizing-Pancake-GX", "rarity": ("no printed rarity symbol", "fixed")},
    "3982": {"print": "ID:sc3b I:126/158:base", "code": "sc3b I", "number": "126/158", "work": "Snorlax-Gormandize-Body-Slam", "rarity": ("R", "rare")},
    "4527": {"print": "ID:scD I:111/159:base", "code": "scD I", "number": "111/159", "work": "Snorlax-Slap-Push-Single-Strike-Tackle", "rarity": ("no printed rarity symbol", "fixed")},
    "4795": {"print": "ID:S8b I:126/184:base", "code": "S8b I", "number": "126/184", "work": "Snorlax-Gormandize-Body-Slam", "rarity": ("R", "rare"), "legacy": ["U0175"]},
    "5067": {"print": "ID:S-P:030:base", "code": "S-P", "number": "030", "work": "Snorlax-V-Swallow-Falling-Down", "rarity": ("PROMO", "promo"), "date": ("2021", "year")},
    "5089": {"print": "ID:S-P:052:base", "code": "S-P", "number": "052", "work": "Snorlax-Gormandize-Body-Slam", "rarity": ("PROMO", "promo"), "date": ("2021-05", "month")},
    "5137": {"print": "ID:S-P:100:base", "code": "S-P", "number": "100", "work": "Snorlax-Rolling-Tackle-Heavy-Impact", "rarity": ("PROMO", "promo"), "date": ("2021", "year")},
    "5772": {"print": "ID:S10b I:056/071:base", "code": "S10b I", "number": "056/071", "work": "Snorlax-Block-Collapse", "rarity": ("R", "rare"), "legacy": ["U0204"]},
    "6007": {"print": "ID:S10a I:058/071:base", "code": "S10a I", "number": "058/071", "work": "Snorlax-Unfazed-Fat-Thumping-Snore", "rarity": ("R", "rare"), "legacy": ["U0346"]},
    "6671": {"print": "ID:S-P:356:base", "code": "S-P", "number": "356", "work": "Snorlax-Heavy-Impact", "rarity": ("PROMO", "promo"), "date": ("2022-12", "month")},
    "8554": {"print": "ID:SV2a I:143/165:base", "code": "SV2a I", "number": "143/165", "work": "Snorlax-Voraciousness-Thudding-Press", "rarity": ("U", "uncommon"), "legacy": ["U0105"]},
    "8760": {"print": "ID:SV2a I:181/165:base", "code": "SV2a I", "number": "181/165", "work": "Snorlax-Voraciousness-Thudding-Press", "rarity": ("AR", "illustration-rare"), "legacy": ["U0051"]},
    "9774": {"print": "ID:SV4s I:118/132:base", "code": "SV4s I", "number": "118/132", "work": "Snorlax-Doll", "rarity": ("U", "uncommon")},
    "10045": {"print": "ID:SV4a I:145/190:base", "code": "SV4a I", "number": "145/190", "work": "Snorlax-Voraciousness-Thudding-Press", "rarity": ("no printed rarity symbol", "fixed"), "legacy": ["U0308"]},
    "10239": {"print": "ID:SV4a I:310/190:base", "code": "SV4a I", "number": "310/190", "work": "Snorlax-Voraciousness-Thudding-Press", "rarity": ("S", "shiny-rare"), "legacy": ["U0386"]},
    "13757": {"print": "ID:SV6s I:136/167:base", "code": "SV6s I", "number": "136/167", "work": "Snorlax-But-First-Food-Heavy-Impact", "rarity": ("U", "uncommon")},
    "15253": {"print": "ID:SVM I:094/175:base", "code": "SVM I", "number": "094/175", "work": "Snorlax-ex-Strength-Toss-and-Turn-Press", "rarity": ("no printed rarity symbol", "fixed"), "legacy": ["U0404"]},
    "15784": {"print": "ID:SV9s I:109/139:base", "code": "SV9s I", "number": "109/139", "work": "Hops-Snorlax-Extra-Helpings-Dynamic-Press", "rarity": ("R", "rare")},
    "17374": {"print": "ID:MA3 I:136/193:base", "code": "MA3 I", "number": "136/193", "work": "Hops-Snorlax-Extra-Helpings-Dynamic-Press", "rarity": ("no printed rarity symbol", "fixed"), "legacy": ["U0129"]},
    "17792": {"print": "ID:MA3 I:136/193:V1", "code": "MA3 I", "number": "136/193", "work": "Hops-Snorlax-Extra-Helpings-Dynamic-Press", "rarity": ("no printed rarity symbol", "fixed"), "legacy": ["U0787"]},
    "17793": {"print": "ID:MA3 I:136/193:V2", "code": "MA3 I", "number": "136/193", "work": "Hops-Snorlax-Extra-Helpings-Dynamic-Press", "rarity": ("no printed rarity symbol", "fixed"), "legacy": ["U0792"]},
}


SET_DATES = {
    "AC3a": ("2020-07-10", "day"), "AC3D": ("2020-07-10", "day"),
    "AS1b": ("2019-08-08", "day"), "AS1D": ("2019-08-08", "day"),
    "sc1a I": ("2020-11-21", "day"), "sc1b I": ("2020-11-21", "day"),
    "sc1D I": ("2020-11-21", "day"), "sc3b I": ("2021-03-21", "day"),
    "scA I": ("2021-03-21", "day"), "scD I": ("2022-01-21", "day"),
    "S8b I": ("2022-01-21", "day"), "S10a I": ("2022-08-26", "day"),
    "S10b I": ("2022-06-17", "day"), "SV2a I": ("2023-07-28", "day"),
    "SV4a I": ("2024-01-26", "day"), "SV4s I": ("2023-12-15", "day"),
    "SV6s I": ("2024-05-31", "day"), "SV9s I": ("2025-04-18", "day"),
    "SVM I": ("2025-01-31", "day"), "MA3 I": ("2026-01-30", "day"),
}


PROMOS = [
    {
        "printId": "ID:SM-P:166:base", "locality": "ID", "localSetCode": "SM-P", "localNumber": "166", "variant": "base",
        "language": "Indonesian", "script": "Latn", "name": "Eevee & Snorlax GX", "cardName": "Eevee & Snorlax GX",
        "catchUpOf": None, "specimenId": "SPEC-0027", "providerId": "inspected-specimen",
        "sourceUrl": "https://pokumon.com/card/eevee-snorlax-tag-team-gx-166-sm-p-indonesian-promo/", "corroborated": True,
        "markAssetUrl": None, "cardImageUrl": None, "releaseDate": "2020-07-25", "releaseDatePrecision": "day", "releaseApproximate": False,
        "evidence": "SPEC-0027 shows the exact Indonesian 166/SM-P Indomaret card. Pokumon and the Indonesian SM-P list independently identify the July 25-August 31, 2020 campaign and ripple treatment.",
        "work": "Eevee-Snorlax-GX-Cheer-Up-Dump-Truck-Press-Megaton-Friends-GX", "rarity": ("PROMO", "promo"), "legacy": [],
    },
    {
        "printId": "ID:SV-P:117:V1", "locality": "ID", "localSetCode": "SV-P", "localNumber": "117", "variant": "V1",
        "language": "Indonesian", "script": "Latn", "name": "Snorlax", "cardName": "Snorlax", "catchUpOf": None,
        "specimenId": "SPEC-0019", "providerId": "inspected-specimen", "sourceUrl": "https://pokumon.com/card/poke-ball-holo-snorlax-117-sv-p-indonesian-promo/", "corroborated": True,
        "markAssetUrl": None, "cardImageUrl": None, "releaseDate": "2024-06-28", "releaseDatePrecision": "day", "releaseApproximate": False,
        "evidence": "SPEC-0019 positively shows the Indonesian 117/SV-P Poké Ball mirror card; Pokumon independently records its June 28-July 25, 2024 monthly-promo distribution.",
        "work": "Snorlax-Voraciousness-Thudding-Press", "rarity": ("PROMO", "promo"), "legacy": ["U0752"],
    },
    {
        "printId": "ID:SV-P:117:V2", "locality": "ID", "localSetCode": "SV-P", "localNumber": "117", "variant": "V2",
        "language": "Indonesian", "script": "Latn", "name": "Snorlax", "cardName": "Snorlax", "catchUpOf": None,
        "specimenId": "SPEC-0020", "providerId": "inspected-specimen", "sourceUrl": "https://pokumon.com/card/master-ball-holo-snorlax-117-sv-p-indonesian-promo/", "corroborated": True,
        "markAssetUrl": None, "cardImageUrl": None, "releaseDate": "2024-06-28", "releaseDatePrecision": "day", "releaseApproximate": False,
        "evidence": "SPEC-0020 positively shows the Indonesian 117/SV-P Master Ball mirror card; Pokumon independently records its June 28-July 25, 2024 monthly-promo distribution.",
        "work": "Snorlax-Voraciousness-Thudding-Press", "rarity": ("PROMO", "promo"), "legacy": ["U0772"],
    },
    {
        "printId": "ID:SV-P:278:base", "locality": "ID", "localSetCode": "SV-P", "localNumber": "278", "variant": "base",
        "language": "Indonesian", "script": "Latn", "name": "Snorlax", "cardName": "Snorlax", "catchUpOf": None,
        "specimenId": "SPEC-0187", "providerId": "pokumon", "sourceUrl": "https://pokumon.com/card/snorlax-278-sv-p-indonesian-promo/", "corroborated": False,
        "markAssetUrl": None, "cardImageUrl": None, "releaseDate": "2025-07-25", "releaseDatePrecision": "day", "releaseApproximate": False,
        "evidence": "The Pokumon record and retained copy of its exact Indonesian 278/SV-P image in SPEC-0187 identify Promo Pack 11 on July 25, 2025 and the non-holo treatment.",
        "work": "Snorlax-Spike-Draw-Mega-Punch", "rarity": ("PROMO", "promo"), "legacy": ["U0773"],
    },
    {
        "printId": "ID:SV-P:286:base", "locality": "ID", "localSetCode": "SV-P", "localNumber": "286", "variant": "base",
        "language": "Indonesian", "script": "Latn", "name": "Snorlax", "cardName": "Snorlax", "catchUpOf": None,
        "specimenId": "SPEC-0188", "providerId": "pokumon", "sourceUrl": "https://pokumon.com/card/snorlax-286-sv-p-indonesian-promo/", "corroborated": False,
        "markAssetUrl": None, "cardImageUrl": None, "releaseDate": "2026-01", "releaseDatePrecision": "month", "releaseApproximate": False,
        "evidence": "The Pokumon record and retained copy of its exact Indonesian 286/SV-P Taro-stamped image in SPEC-0188 identify the January-February 2026 promotion and non-holo treatment.",
        "work": "Snorlax-But-First-Food-Heavy-Impact", "rarity": ("PROMO", "promo"), "legacy": ["U0687"],
    },
]


SPEC_BY_DETAIL = {detail: f"SPEC-{157 + index:04d}" for index, detail in enumerate(OFFICIAL)}


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def discovery_rows() -> dict[str, dict[str, Any]]:
    rows = {}
    for line in DISCOVERY.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("locality") == "ID" and str(row.get("rawProviderId")) in OFFICIAL:
            rows[str(row["rawProviderId"])] = row
    if set(rows) != set(OFFICIAL):
        raise ValueError("retained Indonesian discovery frontier differs from reviewed issue #258 detail ids")
    return rows


def release_id(row: dict[str, Any]) -> str:
    return f"RELEASE:ID:Indonesian:{row['localSetCode']}:{row['localNumber']}:{row['work']}"


def official_prints() -> list[dict[str, Any]]:
    rows = discovery_rows()
    result = []
    for detail, facts in OFFICIAL.items():
        raw = rows[detail]
        variant = facts["print"].rsplit(":", 1)[1]
        date, precision = facts.get("date") or SET_DATES[facts["code"]]
        card_name = (
            "Eevee & Snorlax GX" if detail == "2501" else
            "Hop's Snorlax" if detail in {"15784", "17374", "17792", "17793"} else
            "Snorlax Doll" if detail == "9774" else
            "Snorlax GX" if detail in {"1605", "3466"} else raw["raw"]["localName"]
        )
        result.append({
            "printId": facts["print"], "locality": "ID", "localSetCode": facts["code"],
            "localNumber": facts["number"], "variant": variant, "language": "Indonesian", "script": "Latn",
            "name": raw["raw"]["localName"], "cardName": card_name,
            "catchUpOf": "the exact Indonesian counterpart identified by the retained official card detail and printed attacks",
            "specimenId": SPEC_BY_DETAIL[detail], "providerId": "pokemon-card-asia", "sourceUrl": raw["sourceUrl"],
            "corroborated": False, "markAssetUrl": raw["raw"].get("setSymbolUrl"),
            "cardImageUrl": raw["raw"]["cardImageUrl"], "releaseDate": date, "releaseDatePrecision": precision,
            "releaseApproximate": False,
            "evidence": (
                f"The retained official Indonesian card detail {detail} and SPEC-{SPEC_BY_DETAIL[detail].split('-')[1]} "
                f"show {raw['raw']['localName']} {facts['number']} in {facts['code']}, including the printed attacks used for the explicit Work mapping. "
                f"The exact render prints rarity {facts['rarity'][0]}. The image is identity and rarity evidence only; no physical finish is inferred."
            ),
            "work": facts["work"], "rarity": facts["rarity"], "legacy": facts.get("legacy", []),
        })
    return result


def specimen_rows(prints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    by_print = {row["printId"]: row for row in prints}
    for detail, facts in OFFICIAL.items():
        row = by_print[facts["print"]]
        rows.append({
            "specimenId": row["specimenId"], "setCode": row["localSetCode"], "number": row["localNumber"],
            "variant": row["variant"], "language": "Indonesian", "heldBy": "publisher or database",
            "inspectedFrom": "official Pokémon Asia Indonesian card-detail render",
            "photograph": row["specimenId"] + ".png", "photographSource": row["cardImageUrl"],
            "observed": (
                f"Complete official Indonesian render for {row['name']} {row['localSetCode']} {row['localNumber']} "
                f"({row['variant']}). The printed name, set code, collector number, attacks and rarity {row['rarity'][0]} "
                "establish card-release identity, Work equivalence and rarity. Retained as identity evidence only; no physical finish is inferred."
            ),
            "recordedAt": "2026-08-28", "citedBy": row["legacy"], "listingUrl": row["sourceUrl"],
        })
    rows.extend([
        {
            "specimenId": "SPEC-0187", "setCode": "SV-P", "number": "278", "variant": "base", "language": "Indonesian",
            "heldBy": "publisher or database", "inspectedFrom": "retained exact-card database image",
            "photograph": "SPEC-0187.png", "photographSource": "images/SV-P_ID_278_Snorlax_859884.png",
            "observed": "Complete Indonesian 278/SV-P Snorlax image. The printed Indonesian text, collector number and Pokémon TCG GYM stamp establish the exact card-release identity; finish is established separately by Pokumon.",
            "recordedAt": "2026-08-28", "citedBy": ["U0773"], "listingUrl": "https://pokumon.com/card/snorlax-278-sv-p-indonesian-promo/",
        },
        {
            "specimenId": "SPEC-0188", "setCode": "SV-P", "number": "286", "variant": "base", "language": "Indonesian",
            "heldBy": "publisher or database", "inspectedFrom": "retained exact-card database image",
            "photograph": "SPEC-0188.png", "photographSource": "images/SV-P_ID_286_Snorlax_879048.png",
            "observed": "Complete Indonesian 286/SV-P Snorlax image. The printed Indonesian text, collector number and Taro stamp establish the exact card-release identity; finish is established separately by Pokumon.",
            "recordedAt": "2026-08-28", "citedBy": ["U0687"], "listingUrl": "https://pokumon.com/card/snorlax-286-sv-p-indonesian-promo/",
        },
    ])
    return rows


def apply_profiles(document: dict[str, Any], prints: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in prints:
        grouped.setdefault(row["localSetCode"], []).append(row)
    profiles = {code: source_profile(group) for code, group in grouped.items()}
    by_id = {row["sourceRecordId"]: row for row in document["sourceRecords"]}
    by_id.update({row["sourceRecordId"]: row for row in profiles.values()})
    document["sourceRecords"] = sorted(by_id.values(), key=lambda row: row["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(document["sourceRecords"])
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile" for row in document["sourceRecords"]
    )
    return profiles


def apply_graph(graph: dict[str, Any], profiles: dict[str, dict[str, Any]], prints: list[dict[str, Any]]) -> dict[str, Any]:
    localization_id = "LOCALIZATION:ID:id"
    by_code: dict[str, list[dict[str, Any]]] = {}
    for row in prints:
        by_code.setdefault(row["localSetCode"], []).append(row)

    for code, group in by_code.items():
        profile = profiles[code]
        source_id = profile["sourceRecordId"]
        local_set_id = f"LOCALSET:ID:{quote(code, safe='')}"
        obsolete_local_set_id = f"LOCALSET:ID:{code}"
        edition_id = f"EDITION:ID:Indonesian:{code}"
        claim_ids = sorted(f"CLAIM:source-first:{row['printId']}" for row in group)
        upsert_entity(graph, "set-source-record", source_id, profile, origin="reviewed-evidence-issue-258")
        disposition = {"sourceRecordId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": "positive Indonesian source-first records establish this local set"}
        upsert_entity(graph, "set-source-disposition", source_id, disposition, origin="reviewed-evidence-issue-258")
        upsert_edge(graph, "set-source-disposition", source_id, "disposes", "set-source-record", source_id)
        upsert_migration(graph, {"sourceKind": "set-catalogue-source", "sourceId": source_id, "disposition": "mapped", "targetRef": local_set_id, "reason": disposition["reason"]})

        if obsolete_local_set_id != local_set_id:
            graph["entities"] = [
                row for row in graph["entities"]
                if not (
                    row.get("entityType") == "local-set"
                    and row.get("entityId") == obsolete_local_set_id
                    and row.get("origin") == "reviewed-evidence-issue-258"
                )
            ]
            graph["edges"] = [
                edge for edge in graph["edges"]
                if not (
                    (edge.get("fromType") == "local-set" and edge.get("fromId") == obsolete_local_set_id)
                    or (edge.get("toType") == "local-set" and edge.get("toId") == obsolete_local_set_id)
                )
            ]
        local_matches = [row for row in graph["entities"] if row.get("entityType") == "local-set" and row.get("entityId") == local_set_id]
        if local_matches:
            append_unique(local_matches[0]["payload"].setdefault("sourceRecordIds", []), source_id)
        else:
            upsert_entity(graph, "local-set", local_set_id, {"localSetId": local_set_id, "locality": "ID", "localCode": code, "observedNames": [], "productKind": "physical-card-set-or-product", "sourceRecordIds": [source_id]}, origin="reviewed-evidence-issue-258")
        upsert_edge(graph, "local-set", local_set_id, "observed-by", "set-source-record", source_id)

        edition_matches = [row for row in graph["entities"] if row.get("entityType") == "set-edition" and row.get("entityId") == edition_id]
        if edition_matches:
            payload = edition_matches[0]["payload"]
            append_unique(payload["identity"].setdefault("establishingClaimIds", []), *claim_ids)
            append_unique(payload["catalogue"].setdefault("establishingEvidenceIds", []), source_id)
            payload["catalogue"]["localSetId"] = local_set_id
        else:
            upsert_entity(graph, "set-edition", edition_id, {
                "setEditionId": edition_id,
                "identity": {"setEditionId": edition_id, "locality": "ID", "language": "Indonesian", "script": "Latn", "localSetCode": code, "localIdentifierKnown": True, "state": "identified", "viaLegacySetCodes": [], "establishingClaimIds": claim_ids, "localizationId": localization_id},
                "catalogue": {"setEditionId": edition_id, "localSetId": local_set_id, "locality": "ID", "language": "Indonesian", "script": "Latn", "localCode": code, "state": "identified", "establishingEvidenceIds": [source_id], "localizationId": localization_id},
            }, origin="reviewed-evidence-issue-258")
        upsert_edge(graph, "set-edition", edition_id, "belongs-to", "local-set", local_set_id)
        upsert_edge(graph, "set-edition", edition_id, "localized-as", "localization", localization_id, {"decisionRef": "https://github.com/m4s-ai/snoredex-data/issues/254", "reviewedAt": "2026-08-24"})

    release_groups: dict[str, list[dict[str, Any]]] = {}
    for row in prints:
        release_groups.setdefault(release_id(row), []).append(row)
    release_by_print = {row["printId"]: release_id(row) for row in prints}

    for rid, group in release_groups.items():
        first = group[0]
        edition_id = f"EDITION:ID:Indonesian:{first['localSetCode']}"
        work_id = f"WORK:{first['work']}"
        obsolete_release_ids = {
            item["entityId"] for item in graph["entities"]
            if item.get("entityType") == "card-release"
            and item.get("entityId") != rid
            and item.get("payload", {}).get("language") == "Indonesian"
            and item.get("payload", {}).get("localSetCode") == first["localSetCode"]
            and str(item.get("payload", {}).get("localNumber") or "").partition("/")[0].lstrip("0")
            == first["localNumber"].partition("/")[0].lstrip("0")
        }
        obsolete_catalogue_ids = {
            item["entityId"] for item in graph["entities"]
            if item.get("entityType") == "catalogue-card-release-ref"
            and item.get("payload", {}).get("cardReleaseId") in obsolete_release_ids
        }
        graph["entities"] = [
            item for item in graph["entities"]
            if not (
                (item.get("entityType") == "card-release" and item.get("entityId") in obsolete_release_ids)
                or (item.get("entityType") == "catalogue-card-release-ref" and item.get("entityId") in obsolete_catalogue_ids)
            )
        ]
        graph["edges"] = [
            edge for edge in graph["edges"]
            if not (
                (edge.get("fromType") == "card-release" and edge.get("fromId") in obsolete_release_ids)
                or (edge.get("toType") == "card-release" and edge.get("toId") in obsolete_release_ids)
                or (edge.get("fromType") == "catalogue-card-release-ref" and edge.get("fromId") in obsolete_catalogue_ids)
                or (edge.get("toType") == "catalogue-card-release-ref" and edge.get("toId") in obsolete_catalogue_ids)
            )
        ]
        claims = []
        urls = []
        legacy = []
        for row in group:
            claim_id = f"CLAIM:source-first:{row['printId']}"
            claims.append(claim_id)
            urls.append(row["sourceUrl"])
            legacy.extend(row.get("legacy", []))
            claim = {"claimId": claim_id, "claimKind": "card-release", "sourceKind": "source-first-record", "sourceId": row["printId"], "sourceRecord": row["sourceUrl"], "evidenceStatus": "confirmed", "disposition": "established-and-mapped", "proposedTargetId": rid, "materializedTargetId": rid, "reason": "positive exact Indonesian card record and retained image"}
            upsert_entity(graph, "candidate-claim", claim_id, claim, origin="reviewed-evidence-issue-258")
            upsert_edge(graph, "candidate-claim", claim_id, "materializes", "card-release", rid, {"disposition": "established-and-mapped"})
            upsert_migration(graph, {"sourceKind": "source-first-record", "sourceId": row["printId"], "disposition": "established-and-mapped", "targetRef": rid, "reason": claim["reason"]})

        mapping_state = "mapped-by-explicit-equivalence" if legacy else "mapped"
        payload = {
            "cardReleaseId": rid, "setEditionId": edition_id, "locality": "ID", "language": "Indonesian", "script": "Latn",
            "localSetCode": first["localSetCode"], "localNumber": first["localNumber"], "localIdentifierKnown": True, "state": "identified",
            "work": first["work"], "workMappingState": mapping_state, "viaLegacySetCode": None, "viaLegacyNumber": None,
            "claimIds": sorted(claims), "establishingClaimIds": sorted(claims), "nonEstablishingClaimIds": [],
            "legacyVariants": sorted({row["variant"] for row in group}), "legacyProducts": [], "sourceRecords": sorted(set(urls)),
            "sourceFirstRecordIds": sorted(row["printId"] for row in group), "legacyCounterpartUnitIds": sorted(set(legacy)),
            "releaseDate": first["releaseDate"], "releaseDatePrecision": first["releaseDatePrecision"], "releaseApproximate": bool(first.get("releaseApproximate")),
        }
        upsert_entity(graph, "card-release", rid, payload, origin="reviewed-evidence-issue-258")
        upsert_edge(graph, "card-release", rid, "belongs-to", "set-edition", edition_id)
        upsert_edge(graph, "card-release", rid, "implements", "work", work_id, {"state": mapping_state, "basis": "exact localized attacks and card traits"})
        upsert_entity(graph, "catalogue-card-release-ref", rid, {"cardReleaseId": rid, "setEditionId": edition_id, "collectorNumber": first["localNumber"], "origin": "issue-258-positive-evidence"}, origin="reviewed-evidence-issue-258")
        upsert_edge(graph, "catalogue-card-release-ref", rid, "belongs-to", "set-edition", edition_id)
        upsert_edge(graph, "catalogue-card-release-ref", rid, "references", "card-release", rid)

        source_id = stable_profile_id("ID", first["localSetCode"])
        rarity_id = "RARITYCLAIM:issue258:" + rid.removeprefix("RELEASE:ID:Indonesian:")
        rarity_native, rarity_normalized = first["rarity"]
        rarity_payload = {"rarityClaimId": rarity_id, "cardReleaseId": rid, "sourceRecordId": source_id, "sourceProvider": "mixed-positive-evidence", "sourceVocabulary": "printed-Indonesian-card-render", "sourceNativeValue": rarity_native, "normalizedRarityId": rarity_normalized, "sourceProductKey": first["sourceUrl"]}
        upsert_entity(graph, "rarity-claim", rarity_id, rarity_payload, origin="reviewed-evidence-issue-258")
        upsert_edge(graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release", rid)
        upsert_edge(graph, "rarity-claim", rarity_id, "observed-by", "set-source-record", source_id)

    mapping_rows = []
    for row in prints:
        for legacy_id in row.get("legacy", []):
            rid = release_by_print[row["printId"]]
            assertion_id = f"ASSERT:same-work:{legacy_id}:{row['printId']}"
            assertion = {"assertionId": assertion_id, "assertionType": "same-work-decision", "fromId": rid, "toId": f"WORK:{row['work']}", "legacyUnitId": legacy_id, "sourceFirstRecordId": row["printId"], "assertedBy": "repository verification pass", "assertedAt": "2026-08-28", "evidenceUrl": row["sourceUrl"], "evidence": "The exact Indonesian card identity and printed attacks establish this local counterpart without merging release identities.", "destructiveMergeAllowed": False}
            upsert_entity(graph, "equivalence-assertion", assertion_id, assertion, origin="reviewed-evidence-issue-258")
            upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "card-release", rid, assertion)
            upsert_edge(graph, "equivalence-assertion", assertion_id, "relates", "work", f"WORK:{row['work']}", assertion)
            upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": legacy_id, "disposition": "linked-local-counterpart", "targetRef": rid, "targetRefs": [rid], "reason": "issue #258 re-key"})
            mapping_rows.append({"legacyUnitId": legacy_id, "sourceFirstRecordId": row["printId"], "assertionType": "same-work-decision", "assertedBy": "repository verification pass", "assertedAt": "2026-08-28", "evidenceUrl": row["sourceUrl"], "evidence": assertion["evidence"]})

    for unresolved in ("U0170", "U0603"):
        upsert_migration(graph, {"sourceKind": "legacy-issue-rekey", "sourceId": unresolved, "disposition": "needs-positive-local-identity", "targetRef": None, "targetRefs": [], "reason": "issue #258 re-key"})

    return graph_projection.project_physical_evidence(graph), mapping_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    official = official_prints()
    issue_prints = official + PROMOS

    prints_doc = read(PRINTS)
    before_prints = encoded(prints_doc)
    by_print = {row["printId"]: row for row in prints_doc["prints"]}
    by_print.update({row["printId"]: {key: value for key, value in row.items() if key not in {"work", "rarity", "legacy"}} for row in issue_prints})
    prints_doc["prints"] = sorted(by_print.values(), key=lambda row: row["printId"])
    prints_doc["meta"]["generated"] = "2026-08-28"
    prints_doc["meta"]["counts"]["admitted"] = len(prints_doc["prints"])

    specimens_doc = read(SPECIMENS)
    before_specimens = encoded(specimens_doc)
    by_specimen = {row["specimenId"]: row for row in specimens_doc["specimens"]}
    for row in specimen_rows(official):
        current = by_specimen.get(row["specimenId"], {})
        sha256 = current.get("photographSha256")
        current.update(row)
        if sha256:
            current["photographSha256"] = sha256
        by_specimen[row["specimenId"]] = current
    by_specimen["SPEC-0019"]["setCode"] = "SV-P"
    by_specimen["SPEC-0020"]["setCode"] = "SV-P"
    specimen_27 = by_specimen["SPEC-0027"]
    specimen_27["physicalObservation"] = {"finish": "holo", "foilPattern": "ripple", "markings": "Indomaret logo in artwork", "markingRole": "distribution-promo", "distribution": {"kind": "purchase-promo", "name": "Indomaret booster pack purchase, July 25-August 31, 2020"}, "cardSize": "standard", "basis": "The owner photograph shows reflective treatment across the full-art card and Pokumon independently classifies the exact Indonesian 166/SM-P printing as Ripple."}
    specimen_27["citedBy"] = sorted(set(specimen_27.get("citedBy") or []) | {"ID:SM-P:166:base"})
    specimens_doc["specimens"] = sorted(by_specimen.values(), key=lambda row: int(row["specimenId"].split("-")[1]))

    finishes = read(FINISHES)
    before_finishes = encoded(finishes)
    finishes["sources"].update({
        "pokumon-id-svp278": {"url": "https://pokumon.com/card/snorlax-278-sv-p-indonesian-promo/", "sourceType": "Specialist per-language promo record", "authorityTier": "specialist-reference", "coverage": "positive-only", "supportsAbsence": False, "languages": ["Indonesian"], "retrievedAt": "2026-08-28", "evidence": "The exact 278/SV-P Indonesian promo record identifies the July 25, 2025 Gym Promo Pack 11 card as Non-holo."},
        "pokumon-id-svp286": {"url": "https://pokumon.com/card/snorlax-286-sv-p-indonesian-promo/", "sourceType": "Specialist per-language promo record", "authorityTier": "specialist-reference", "coverage": "positive-only", "supportsAbsence": False, "languages": ["Indonesian"], "retrievedAt": "2026-08-28", "evidence": "The exact 286/SV-P Indonesian promo record identifies the January-February 2026 Taro card as Non-holo."},
    })
    finish_rows = [
        {"setCode": "SV-P/ID", "releaseSetCode": "SV-P", "number": "117", "languages": ["Indonesian"], "printings": []},
        {"setCode": "SV-P/ID", "releaseSetCode": "SV-P", "number": "278", "languages": ["Indonesian"], "printings": [{"finish": "non-holo", "foilPattern": None, "markings": [{"kind": "stamp", "text": "Pokémon TCG GYM", "role": "distribution-promo"}], "distribution": {"kind": "event-promo-pack", "name": "Pokémon Card Gym Promo Card Pack 11"}, "cardSize": "standard", "mappedVariants": ["base"], "verificationStatus": "confirmed", "sourceRefs": ["pokumon-id-svp278"]}]},
        {"setCode": "SV-P/ID", "releaseSetCode": "SV-P", "number": "286", "languages": ["Indonesian"], "printings": [{"finish": "non-holo", "foilPattern": None, "markings": [{"kind": "stamp", "text": "Taro", "role": "distribution-promo"}], "distribution": {"kind": "purchase-promo", "name": "Taro Pokémon promotion"}, "cardSize": "standard", "mappedVariants": ["base"], "verificationStatus": "confirmed", "sourceRefs": ["pokumon-id-svp286"]}]},
    ]
    finish_by_key = {
        (row["setCode"], row["number"], tuple(row.get("languages") or [])): row
        for row in finish_rows
    }
    updated_overrides = []
    for row in finishes["overrides"]:
        key = (row["setCode"], row["number"], tuple(row.get("languages") or []))
        updated_overrides.append(finish_by_key.pop(key, row))
    finishes["overrides"] = updated_overrides + list(finish_by_key.values())
    for row in finishes["overrides"]:
        if row.get("setCode") == "SV-P/ID" and row.get("number") == "117" and "Indonesian" in (row.get("languages") or []):
            row["releaseSetCode"] = "SV-P"
    finishes["meta"]["lastUpdated"] = "2026-08-28"

    set_sources = read(SET_SOURCES)
    before_sources = encoded(set_sources)
    profiles = apply_profiles(set_sources, issue_prints)

    discovery_adapters = read(DISCOVERY_ADAPTERS)
    before_discovery_adapters = encoded(discovery_adapters)
    print_by_detail = {
        detail: next(row for row in official if row["printId"] == facts["print"])
        for detail, facts in OFFICIAL.items()
    }
    for mapping in discovery_adapters["explicitMappings"]:
        detail = str(mapping.get("rawProviderId") or "")
        if mapping.get("rawLocale") == "id" and detail in {"13757", "15784", "9774"}:
            mapping["targetCardReleaseId"] = release_id(print_by_detail[detail])

    capabilities = read(CAPABILITIES)
    before_capabilities = encoded(capabilities)
    asia_surface = next(
        row for row in capabilities["surfaces"]
        if row["surfaceId"] == "asia-card-search"
    )
    asia_edge = next(
        row for row in asia_surface["coverageEdges"]
        if row["edgeId"] == "asia-card-search-positive"
    )
    asia_edge["positiveEvidenceCapabilities"] = [
        "language", "card-existence", "local-set-identifier"
    ]
    image_surface = {
        "surfaceId": "asia-card-image",
        "providerId": "pokemon-card-asia",
        "label": "Official Asia localized card renders",
        "match": {
            "urlPrefixes": [
                "https://asia.pokemon-card.com/id/card-img/",
                "https://asia.pokemon-card.com/th/card-img/",
                "https://asia.pokemon-card.com/tw/card-img/",
            ],
            "nonUrlEvidenceIds": [],
        },
        "state": "incomplete",
        "failureState": "Only exact retained publisher renders are covered; the image host is not a complete historical manifest.",
        "accessMode": "direct-download",
        "adapterState": "planned",
        "lastCheckedAt": "2026-08-28",
        "freshnessPolicy": "Retain the exact card image, publisher detail URL, retrieval date and SHA-256.",
        "query": {
            "method": "GET",
            "endpoint": "https://asia.pokemon-card.com/{locale}/card-img/{asset}",
            "parameters": ["locale", "asset"],
            "pagination": "not paginated; each retained render establishes only the pictured card",
            "expectedIdentifiers": ["printed card name", "collector number", "set mark"],
        },
        "finishCapability": {
            "mode": "none",
            "vocabulary": [],
            "publicationForm": "publisher card render; not a physical finish photograph",
            "closedWithinScope": False,
        },
        "coverageEdges": [{
            "edgeId": "asia-card-image-positive",
            "coverage": {
                "localities": ["TW", "ID", "TH"],
                "languages": ["T-Chinese", "Indonesian", "Thai"],
                "scripts": ["Hant", "Latn", "Thai"],
                "productCategories": ["card"],
                "timeRange": {
                    "start": None,
                    "end": None,
                    "basis": "exact retained publisher renders only",
                },
            },
            "positiveEvidenceCapabilities": ["identity", "image"],
            "exhaustive": False,
            "absenceCapability": {
                "enabled": False,
                "dimensions": [],
                "exactScopes": [],
                "rationale": "A retained render proves the pictured identity; missing assets prove nothing.",
            },
            "knownPositiveObservationId": "obs-asia-card-image",
            "boundary": {
                "outsideScope": ["unretained cards", "physical finish", "complete set or era"],
                "zeroResultMeans": "unknown",
                "challenge": "No missing image or failed request can refute a card printing.",
            },
        }],
    }
    by_surface = {row["surfaceId"]: row for row in capabilities["surfaces"]}
    by_surface[image_surface["surfaceId"]] = image_surface
    surface_order = [
        "pokemon-cn-product-pages", "tpci-checklists", "tpci-localized-card-archive",
        "tpci-latam-spanish-card-assets", "tpci-eu-spanish-card-assets", "jp-card-search",
        "jp-product-pages", "asia-card-search", "pokemon-card-korea-historical-detail",
        "tcgdex-api", "bulbapedia-mediawiki", "tcgcsv-api", "psa-registry", "cgc-registry",
        "pokumon-search", "snkrdunk-listings", "52poke-wiki", "koreanpokemoncards-site",
        "elitefourum-topics", "ligapokemon-catalogue", "cardmarket-products",
        "pokemontcgio-api", "limitlesstcg-cards", "play-pokemon-gallery", "retailer-listings",
        "internal-derivations", "owner-attestations", "inspected-specimens",
        "cardmarket-listing-photos", "seller-listing-photos", "pokecottage-master-lists",
        "pokecardex-scan-archive", "pkparaiso-card-scans", "wikidex-card-scans",
        "asia-card-image",
    ]
    capabilities["surfaces"] = [by_surface[surface_id] for surface_id in surface_order]
    image_observation = {
        "observationId": "obs-asia-card-image",
        "surfaceId": "asia-card-image",
        "kind": "known-positive",
        "queryUrl": "https://asia.pokemon-card.com/id/card-img/id00004795.png",
        "queryParameters": {"locale": "id", "asset": "id00004795.png"},
        "retrievedAt": "2026-08-28",
        "fixtureRef": {
            "kind": "source-registry-evidence",
            "providerId": "pokemon-card-asia",
            "recordKey": "https://asia.pokemon-card.com/id/card-img/id00004795.png",
        },
        "expectedIdentifiers": ["SPEC-0169", "U0175"],
        "validatesEdges": ["asia-card-image-positive"],
        "outcome": "The retained publisher render positively identifies the Indonesian Snorlax card pictured in SPEC-0169.",
    }
    by_observation = {
        row["observationId"]: row for row in capabilities["observations"]
    }
    by_observation[image_observation["observationId"]] = image_observation
    observation_order = [
        "obs-tpci-checklist", "obs-tpci-outside-checklist", "obs-tpci-it-card-archive",
        "obs-tpci-latam-svp184", "obs-tpci-eu-svp184", "obs-jp-card-search",
        "obs-jp-product-page", "obs-asia-card-search", "obs-pokemon-card-korea-bs2010002030",
        "obs-tcgdex-west", "obs-tcgdex-asia", "obs-bulbapedia", "obs-tcgcsv", "obs-psa",
        "obs-cgc", "obs-pokumon", "obs-pokumon-finish-tag", "obs-pokecottage-snorlax-master-list",
        "obs-pokecardex-scan", "obs-pkparaiso-scan", "obs-wikidex-scan", "obs-snkrdunk",
        "obs-52poke", "obs-elitefourum", "obs-elitefourum-outside-table", "obs-ligapokemon",
        "obs-cardmarket", "obs-pokemontcgio", "obs-play-series7", "obs-play-outside-series7",
        "obs-retailer", "obs-internal-derivation", "obs-owner-attestation",
        "obs-inspected-specimen", "obs-cardmarket-listing-photo", "obs-seller-listing-photo",
        "obs-bulbapedia-historical-index", "obs-pokemon-cn-finish-rules", "obs-asia-card-image",
    ]
    capabilities["observations"] = [
        by_observation[observation_id] for observation_id in observation_order
    ]

    graph = read(GRAPH)
    before_graph = encoded(graph)
    graph, mappings = apply_graph(graph, profiles, issue_prints)

    rekeys = read(REKEYS)
    before_rekeys = encoded(rekeys)
    question = {"issueNumber": 258, "locality": "ID", "language": "Indonesian", "legacyUnitIds": sorted({"U0170", "U0603", *(row["legacyUnitId"] for row in mappings)}), "defaultDisposition": "needs-positive-local-identity", "mappings": sorted(mappings, key=lambda row: row["legacyUnitId"])}
    by_issue = {row["issueNumber"]: row for row in rekeys["questionSets"]}
    by_issue[258] = question
    rekeys["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])

    changed = any((before_prints != encoded(prints_doc), before_specimens != encoded(specimens_doc), before_finishes != encoded(finishes), before_sources != encoded(set_sources), before_discovery_adapters != encoded(discovery_adapters), before_capabilities != encoded(capabilities), before_graph != encoded(graph), before_rekeys != encoded(rekeys)))
    if args.check:
        missing = [row["specimenId"] for row in specimen_rows(official) if not by_specimen.get(row["specimenId"], {}).get("photographSha256")]
        if missing:
            raise SystemExit("unpinned issue #258 specimens: " + ", ".join(missing))
        if changed:
            raise SystemExit("issue #258 reviewed inputs are stale; run this pass without --check")
        print("issue #258 Indonesian reviewed inputs are current")
        return 0

    write(PRINTS, prints_doc)
    write(SPECIMENS, specimens_doc)
    write(FINISHES, finishes)
    SET_SOURCES.write_text(encoded(set_sources), encoding="utf-8", newline="\n")
    write(DISCOVERY_ADAPTERS, discovery_adapters)
    write(CAPABILITIES, capabilities)
    GRAPH.write_text(encoded(graph), encoding="utf-8", newline="\n")
    write(REKEYS, rekeys)
    print(f"admitted {len(issue_prints)} Indonesian source-first records, {len(mappings)} positive re-keys and {len(specimen_rows(official))} image specs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
