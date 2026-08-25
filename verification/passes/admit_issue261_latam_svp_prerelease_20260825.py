#!/usr/bin/env python3
"""Admit the positively evidenced LATAM releases from issue #261.

The exact ``SVP LA 184`` publisher asset already establishes the Latin-American
Spanish release.  This pass adds only the facts supported by the two new sources:

* Antique Store's Culiacan event page dates one Mexico prerelease wave to 2025-03-22.
* Pokemon's product article names Hop's Snorlax as one of four unique foil promo
  cards in the Journey Together Build & Battle Box.

The official set launch (2025-03-28) remains a separate control date.  The pass
does not claim that every LATAM market launched on March 22, that the event page
enumerates the promo, or that the positive finish list is complete.

The same pass also reads the two ordinary set cards from Pokemon's official LA
card database, expansion pages and LA checklists:

* JTG LA 117/159 is Rare, launched with the set on 2025-03-28, and the checklist
  positively identifies its ordinary set printing as holographic.
* POR LA 063/088 is Common, launched with the set on 2026-03-27, and the checklist
  positively identifies its ordinary set printing as non-holographic.

No reverse-holographic printing or complete finish list is inferred from either
ordinary-set source bundle.

    python verification/passes/admit_issue261_latam_svp_prerelease_20260825.py
    python verification/passes/admit_issue261_latam_svp_prerelease_20260825.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
GRAPH_PATH = VERIFY / "authoritative_graph.json"
SOURCES_PATH = VERIFY / "set_catalogue_sources.json"
SPECIMENS_PATH = VERIFY / "specimens.json"
sys.path.insert(0, str(ROOT / "scripts"))

import authoritative_graph as graph_projection  # noqa: E402

REVIEWED_AT = "2026-08-25"
RELEASE_ID = "RELEASE:LATAM:Spanish:SVP LA:184:unmapped-work:SPEC-0033"
EDITION_ID = "EDITION:LATAM:Spanish:SVP LA"
LOCAL_SET_ID = "LOCALSET:LATAM:SVP%20LA"
WORK_ID = "WORK:Hops-Snorlax-Extra-Helpings-Dynamic-Press"
WORK_KEY = "Hops-Snorlax-Extra-Helpings-Dynamic-Press"
SPECIMEN_ID = "SPEC-0033"
ASSET_URL = (
    "https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/"
    "img/cards/web/SVP/SVP_LA_184.png"
)
POKEMON_URL = (
    "https://www.pokemon.com/us/news/get-the-pokemon-tcg-scarlet-violet-"
    "journey-together-build-battle-box-early"
)
EVENT_URL = (
    "https://antiquestore.com.mx/event/"
    "pokemon-tcg-journey-together-prerelease/"
)


def stable_id(prefix: str, *parts: str) -> str:
    body = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(body).hexdigest()[:16]}"


NORMAL_SETS = (
    {
        "source_id": "SET-SRC-SF-05381DCC46F8",
        "release_id": "RELEASE:LATAM:Spanish:JTG LA:117/159:unmapped-work:SPEC-0035",
        "edition_id": "EDITION:LATAM:Spanish:JTG LA",
        "local_set_id": "LOCALSET:LATAM:JTG%20LA",
        "work_id": "WORK:Hops-Snorlax-Extra-Helpings-Dynamic-Press",
        "work_key": "Hops-Snorlax-Extra-Helpings-Dynamic-Press",
        "specimen_id": "SPEC-0035",
        "asset_url": (
            "https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/"
            "img/cards/web/SV09/SV09_LA_117.png"
        ),
        "detail_url": (
            "https://www.pokemon.com/el/jcc-pokemon/cartas-pokemon/"
            "series/sv09/117/"
        ),
        "set_url": (
            "https://www.pokemon.com/el/jcc-pokemon/"
            "escarlata-y-purpura-aventuras-compartidas"
        ),
        "checklist_url": (
            "https://www.pokemon.com/static-assets/content-assets/cms2-es-xl/"
            "pdf/trading-card-game/checklist/jtg_web_cardlist_latam.pdf"
        ),
        "set_name": "Aventuras Compartidas",
        "card_name": "Snorlax de Paul",
        "collector_number": "117/159",
        "hp": 150,
        "ability": "Raciones Extras",
        "attacks": [{"name": "Plancha Dinámica", "damage": 140}],
        "rarity_native": "Rare",
        "rarity": "rare",
        "illustrator": "GOSSAN",
        "release_date": "2025-03-28",
        "finish": "holo",
        "finish_basis": (
            "the official LA checklist marks exact row 117 with its holographic "
            "ordinary-set indicator"
        ),
        "work_basis": (
            "the official LA detail identifies Snorlax de Paul with Raciones Extras "
            "and Plancha Dinámica 140, matching the established Hop's Snorlax work"
        ),
    },
    {
        "source_id": "SET-SRC-SF-C0C742569A70",
        "release_id": "RELEASE:LATAM:Spanish:POR LA:063/088:unmapped-work:SPEC-0036",
        "edition_id": "EDITION:LATAM:Spanish:POR LA",
        "local_set_id": "LOCALSET:LATAM:POR%20LA",
        "work_id": "WORK:Snorlax-Gormandizer-Collapse",
        "work_key": "Snorlax-Gormandizer-Collapse",
        "specimen_id": "SPEC-0036",
        "asset_url": (
            "https://assets.pokemon.com/static-assets/content-assets/cms2-es-xl/"
            "img/cards/web/ME03/ME03_LA_63.png"
        ),
        "detail_url": (
            "https://www.pokemon.com/el/jcc-pokemon/cartas-pokemon/"
            "series/me03/63/"
        ),
        "set_url": (
            "https://www.pokemon.com/el/jcc-pokemon/"
            "megaevolucion-equilibrio-perfecto"
        ),
        "checklist_url": (
            "https://www.pokemon.com/static-assets/content-assets/cms2-es-xl/"
            "pdf/trading-card-game/checklist/por_web_cardlist_latam.pdf"
        ),
        "set_name": "Equilibrio Perfecto",
        "card_name": "Snorlax",
        "collector_number": "063/088",
        "hp": 160,
        "ability": None,
        "attacks": [
            {"name": "Comilona", "damage": None},
            {"name": "Colapso", "damage": 160},
        ],
        "rarity_native": "Common",
        "rarity": "common",
        "illustrator": "Toshinao Aoki",
        "release_date": "2026-03-27",
        "finish": "non-holo",
        "finish_basis": (
            "the official LA checklist marks exact row 063 with its non-holographic "
            "ordinary-set indicator"
        ),
        "work_basis": (
            "the official LA detail identifies Snorlax with Comilona and Colapso 160, "
            "matching the established Gormandizer and Collapse work"
        ),
    },
)


EVENT_SOURCE_ID = stable_id("SET-SRC-RETAIL-DATE", EVENT_URL, "2025-03-22")
PRODUCT_SOURCE_ID = stable_id("SET-SRC-POKEMON-SF", POKEMON_URL, ASSET_URL)
EVENT_ID = stable_id("EVENT", EVENT_SOURCE_ID, EDITION_ID)
RARITY_ID = stable_id("RARITYCLAIM", PRODUCT_SOURCE_ID, RELEASE_ID, "promo")
PHYSICAL_ID = stable_id(
    "PHYSICAL", RELEASE_ID, "holo", "Aventuras Compartidas", "prerelease"
)
PHYSICAL_CLAIM_ID = stable_id("CLAIM:positive", PRODUCT_SOURCE_ID, PHYSICAL_ID)
EVENT_ASSERTION_ID = stable_id("SOURCEASSERTION", EVENT_SOURCE_ID, EVENT_ID)
RARITY_ASSERTION_ID = stable_id("SOURCEASSERTION", PRODUCT_SOURCE_ID, RARITY_ID)
SET_ASSERTION_ID = stable_id("SOURCEASSERTION", PRODUCT_SOURCE_ID, LOCAL_SET_ID)

EVENT_SOURCE = {
    "sourceRecordId": EVENT_SOURCE_ID,
    "sourceKind": "release-date-record",
    "provider": "retailer-listing",
    "providerRecordKey": EVENT_URL + "#2025-03-22",
    "retrieved": REVIEWED_AT,
    "raw": {
        "localCode": None,
        "page": "Pokemon TCG - Journey Together PRERELEASE",
        "field": "event date",
        "date": "2025-03-22",
        "datePrecision": "day",
        "approximate": False,
        "status": "released",
        "locality": "LATAM",
        "languageScope": "Spanish",
        "marketScopes": ["MX"],
        "marketScopeBasis": "the venue line identifies Culiacan, Sinaloa, Mexico",
        "sourceUrl": EVENT_URL,
        "note": (
            "The organizer lists a Journey Together prerelease on March 22, 2025 "
            "and says entry includes a kit, two boosters and a Series 5 Prize Pack. "
            "The page does not enumerate the four possible promos or state the card language."
        ),
    },
}

PRODUCT_SOURCE = {
    "sourceRecordId": PRODUCT_SOURCE_ID,
    "sourceKind": "source-first-local-set-profile",
    "provider": "mixed-positive-evidence",
    "providerRecordKey": "LATAM\x1fSVP LA\x1f184\x1f2025-03-22",
    "retrieved": REVIEWED_AT,
    "raw": {
        "localCode": "SVP LA",
        "localName": None,
        "locality": "LATAM",
        "languages": ["Spanish"],
        "scripts": ["Latn"],
        "printIds": ["LATAM:SVP LA:184:base"],
        "providers": ["owner-attestation", "pokemon-official", "retailer-listing"],
        "sourceUrls": [EVENT_URL, ASSET_URL, POKEMON_URL],
        "printedSetSize": None,
        "printedSetSizeBasis": "the promo number has no printed denominator",
        "localeSuffix": "LA",
        "observedCollectorNumbers": ["184"],
        "observedCoverage": (
            "one exact LATAM promo asset plus the publisher's named Build & Battle "
            "promo contents; not a promo-series or finish manifest"
        ),
        "cardImageUrls": [ASSET_URL],
        "productFacts": {
            "articlePublished": "2025-03-10",
            "globalPrereleaseStart": "2025-03-15",
            "officialSetLaunch": "2025-03-28",
            "product": "Scarlet & Violet-Journey Together Build & Battle Box",
            "namedCard": "Hop's Snorlax",
            "classification": "one of four unique foil promo cards",
        },
        "ownerAttestation": {
            "recordedAt": REVIEWED_AT,
            "assertion": (
                "The collection owner identifies exact printing SVP LA 184 as one of the "
                "promos distributed at the cited Mexico prerelease."
            ),
        },
        "physicalPrintingEvidence": {
            "cardReleaseId": RELEASE_ID,
            "sourceUrl": POKEMON_URL,
            "finish": "holo",
            "edition": None,
            "foilPattern": None,
            "markings": [
                {
                    "kind": "set-logo",
                    "role": "distribution-promo",
                    "text": "Aventuras Compartidas",
                }
            ],
            "distribution": {
                "kind": "prerelease",
                "name": "Aventuras Compartidas Prerelease",
                "region": "MX",
                "date": "2025-03-22",
            },
            "cardSize": "unknown",
            "specimenIds": [SPECIMEN_ID],
            "positiveOnly": True,
            "completenessClaim": False,
            "basis": (
                "The exact LA asset supplies identity and marking; the official article calls "
                "Hop's Snorlax one of four unique foil promo cards; the dated Mexico event and "
                "owner statement supply the narrow distribution wave."
            ),
        },
        "scopeBoundary": (
            "The LA asset establishes the localized card. The product article establishes "
            "Hop's Snorlax as a foil promo, but does not itself date a LATAM market wave."
        ),
    },
}


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def encoded(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2) + "\n"


def reconcile(rows: list[dict[str, Any]], expected: dict[str, Any], key: str) -> None:
    matches = [row for row in rows if row.get(key) == expected[key]]
    if not matches:
        rows.append(expected)
    elif len(matches) != 1 or matches[0] != expected:
        raise ValueError(f"drift in {key} {expected[key]}")


def entity(graph: dict[str, Any], entity_type: str, entity_id: str) -> dict[str, Any]:
    matches = [
        row for row in graph["entities"]
        if row.get("entityType") == entity_type and row.get("entityId") == entity_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {entity_type} {entity_id}, found {len(matches)}")
    return matches[0]


def add_entity(
    graph: dict[str, Any], entity_type: str, entity_id: str, payload: dict[str, Any]
) -> None:
    expected = {
        "entityType": entity_type,
        "entityId": entity_id,
        "origin": "reviewed-evidence-issue-261",
        "payload": payload,
    }
    matches = [
        row for row in graph["entities"]
        if row.get("entityType") == entity_type and row.get("entityId") == entity_id
    ]
    if not matches:
        graph["entities"].append(expected)
    elif len(matches) != 1 or matches[0] != expected:
        raise ValueError(f"drift in {entity_type} {entity_id}")


def add_edge(
    graph: dict[str, Any], from_type: str, from_id: str, relation: str,
    to_type: str, to_id: str, provenance: dict[str, Any] | None = None,
) -> None:
    expected = {
        "fromType": from_type,
        "fromId": from_id,
        "relation": relation,
        "toType": to_type,
        "toId": to_id,
        "provenance": provenance or {},
    }
    key = (from_type, from_id, relation, to_type, to_id)
    matches = [
        row for row in graph["edges"]
        if (
            row.get("fromType"), row.get("fromId"), row.get("relation"),
            row.get("toType"), row.get("toId"),
        ) == key
    ]
    if not matches:
        graph["edges"].append(expected)
    elif len(matches) != 1 or matches[0] != expected:
        raise ValueError(f"drift in edge {key}")


def add_migration(graph: dict[str, Any], expected: dict[str, Any]) -> None:
    key = (expected["sourceKind"], expected["sourceId"])
    matches = [
        row for row in graph["migrationDispositions"]
        if (row.get("sourceKind"), row.get("sourceId")) == key
    ]
    if not matches:
        graph["migrationDispositions"].append(expected)
    elif len(matches) != 1 or matches[0] != expected:
        raise ValueError(f"drift in migration disposition {key}")


def append_unique(values: list[str], *new_values: str) -> None:
    values[:] = sorted(set(values) | set(new_values))


def one_row(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get(key) == value]
    if len(matches) != 1:
        raise ValueError(f"expected one {key} {value}, found {len(matches)}")
    return matches[0]


def apply_normal_source(source: dict[str, Any], facts: dict[str, Any]) -> None:
    source["retrieved"] = REVIEWED_AT
    raw = source["raw"]
    raw["localName"] = facts["set_name"]
    append_unique(
        raw.setdefault("sourceUrls", []),
        facts["asset_url"], facts["detail_url"], facts["set_url"],
        facts["checklist_url"],
    )
    raw["observedCoverage"] = (
        "one exact official LA card detail and checklist row; not a complete "
        "finish enumeration"
    )
    raw["cardDetailFacts"] = {
        "cardName": facts["card_name"],
        "hp": facts["hp"],
        "ability": facts["ability"],
        "attacks": facts["attacks"],
        "setName": facts["set_name"],
        "collectorNumber": facts["collector_number"],
        "rarity": facts["rarity_native"],
        "illustrator": facts["illustrator"],
        "sourceUrl": facts["detail_url"],
    }
    raw["releaseFacts"] = {
        "date": facts["release_date"],
        "datePrecision": "day",
        "approximate": False,
        "status": "released",
        "sourceUrl": facts["set_url"],
    }
    raw["checklistFacts"] = {
        "collectorNumber": facts["collector_number"],
        "ordinarySetFinish": facts["finish"],
        "sourceUrl": facts["checklist_url"],
        "basis": facts["finish_basis"],
    }
    raw["physicalPrintingEvidence"] = {
        "cardReleaseId": facts["release_id"],
        "sourceUrl": facts["checklist_url"],
        "finish": facts["finish"],
        "edition": None,
        "foilPattern": None,
        "markings": [],
        "distribution": {
            "kind": "booster-set",
            "name": facts["set_name"],
            "region": "LATAM",
            "date": facts["release_date"],
        },
        "cardSize": "unknown",
        "specimenIds": [facts["specimen_id"]],
        "positiveOnly": True,
        "completenessClaim": False,
        "basis": (
            f"{facts['finish_basis']}; the linked official card detail supplies "
            "identity and the linked official expansion page supplies the launch date"
        ),
    }
    raw["scopeBoundary"] = (
        "The official sources establish this ordinary printing only; no reverse-holo "
        "printing or complete finish list is inferred."
    )


def apply_sources(document: dict[str, Any]) -> None:
    rows = document["sourceRecords"]
    reconcile(rows, EVENT_SOURCE, "sourceRecordId")
    reconcile(rows, PRODUCT_SOURCE, "sourceRecordId")
    for facts in NORMAL_SETS:
        apply_normal_source(one_row(rows, "sourceRecordId", facts["source_id"]), facts)
    counts = document["meta"]["counts"]
    counts["sourceRecords"] = len(rows)
    counts["releaseDateRecords"] = sum(
        row["sourceKind"] == "release-date-record" for row in rows
    )
    counts["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile" for row in rows
    )


def apply_specimens(document: dict[str, Any]) -> None:
    observations = {
        "SPEC-0035": (
            "Official Latin-American Spanish scan of Snorlax de Paul: HP 150, "
            "Ability \"Raciones Extras\", attack \"Plancha Dinámica\" 140, Illus. "
            "GOSSAN, regulation mark I, and complete printed code \"JTG LA 117/159\". "
            "The official European-Spanish asset reads \"JTG ES 117/159\" and uses "
            "\"Presión Dinámica\". No finish is inferred from a publisher render."
        ),
        "SPEC-0036": (
            "Official Latin-American Spanish scan of Snorlax: HP 160, attacks "
            "\"Comilona\" and \"Colapso\" 160, Illus. Toshinao Aoki, regulation mark I, "
            "and complete printed code \"POR LA 063/088\". The official "
            "European-Spanish asset reads \"POR ES 063/088\" and uses \"Glotón\". "
            "No finish is inferred from a publisher render."
        ),
    }
    for specimen_id, observed in observations.items():
        specimen = one_row(document["specimens"], "specimenId", specimen_id)
        specimen["observed"] = observed
        specimen["recordedAt"] = REVIEWED_AT


def apply_normal_graph(graph: dict[str, Any], facts: dict[str, Any]) -> None:
    source_id = facts["source_id"]
    release_id = facts["release_id"]
    event_id = stable_id(
        "EVENT", source_id, facts["edition_id"], facts["release_date"]
    )
    rarity_id = stable_id(
        "RARITYCLAIM", source_id, release_id, facts["rarity"]
    )
    physical_id = stable_id(
        "PHYSICAL", release_id, facts["finish"], facts["set_name"], "ordinary-set"
    )
    physical_claim_id = stable_id("CLAIM:positive", source_id, physical_id)
    event_assertion_id = stable_id("SOURCEASSERTION", source_id, event_id)
    rarity_assertion_id = stable_id("SOURCEASSERTION", source_id, rarity_id)

    source = entity(graph, "set-source-record", source_id)["payload"]
    apply_normal_source(source, facts)

    release = entity(graph, "card-release", release_id)["payload"]
    if release.get("work") not in (None, facts["work_key"]):
        raise ValueError(f"{facts['collector_number']} is already mapped to another work")
    release["work"] = facts["work_key"]
    release["workMappingState"] = "mapped"
    append_unique(
        release.setdefault("sourceRecords", []),
        facts["asset_url"], facts["detail_url"], facts["set_url"],
        facts["checklist_url"],
    )

    local_set = entity(graph, "local-set", facts["local_set_id"])["payload"]
    append_unique(local_set.setdefault("observedNames", []), facts["set_name"])
    edition = entity(graph, "set-edition", facts["edition_id"])["payload"]["catalogue"]
    append_unique(edition.setdefault("establishingEvidenceIds", []), source_id)

    add_entity(
        graph, "release-event", event_id,
        {
            "releaseEventId": event_id,
            "localSetId": facts["local_set_id"],
            "setEditionIds": [facts["edition_id"]],
            "eventKind": "launch",
            "dateValue": facts["release_date"],
            "datePrecision": "day",
            "approximate": False,
            "status": "released",
            "timezone": None,
            "marketScopes": ["LATAM"],
            "marketScopeBasis": (
                "Pokemon's Latin-American Spanish expansion page gives the launch date"
            ),
            "sourceRecordId": source_id,
            "linkBasis": (
                "the official LA card detail places the collector number in this expansion; "
                "the matching LA expansion page gives its launch date"
            ),
        },
    )
    add_edge(
        graph, "release-event", event_id, "belongs-to", "local-set",
        facts["local_set_id"],
    )
    add_edge(
        graph, "release-event", event_id, "supports", "set-edition",
        facts["edition_id"],
    )
    add_entity(
        graph, "source-assertion", event_assertion_id,
        {
            "sourceAssertionId": event_assertion_id,
            "sourceRecordId": source_id,
            "assertionKind": "asserts-release-event",
            "releaseEventId": event_id,
        },
    )
    add_edge(
        graph, "source-assertion", event_assertion_id, "asserted-by",
        "set-source-record", source_id,
    )
    add_edge(
        graph, "source-assertion", event_assertion_id, "asserts-release-event",
        "release-event", event_id,
    )

    add_entity(
        graph, "rarity-claim", rarity_id,
        {
            "rarityClaimId": rarity_id,
            "cardReleaseId": release_id,
            "sourceRecordId": source_id,
            "sourceProvider": "mixed-positive-evidence",
            "sourceVocabulary": "pokemon-official-la-card-database",
            "sourceNativeValue": facts["rarity_native"],
            "normalizedRarityId": facts["rarity"],
            "sourceProductKey": facts["detail_url"],
        },
    )
    add_edge(
        graph, "rarity-claim", rarity_id, "asserts-rarity-for", "card-release",
        release_id,
    )
    add_edge(
        graph, "rarity-claim", rarity_id, "observed-by", "set-source-record",
        source_id,
    )
    add_entity(
        graph, "source-assertion", rarity_assertion_id,
        {
            "sourceAssertionId": rarity_assertion_id,
            "sourceRecordId": source_id,
            "assertionKind": "asserts-rarity-claim",
            "rarityClaimId": rarity_id,
        },
    )
    add_edge(
        graph, "source-assertion", rarity_assertion_id, "asserted-by",
        "set-source-record", source_id,
    )
    add_edge(
        graph, "source-assertion", rarity_assertion_id, "asserts-rarity-claim",
        "rarity-claim", rarity_id,
    )

    add_edge(
        graph, "card-release", release_id, "implements", "work", facts["work_id"],
        {
            "state": "mapped",
            "sourceRecordId": source_id,
            "basis": facts["work_basis"],
        },
    )

    reason = (
        f"{facts['finish_basis']}. This establishes one ordinary "
        f"{facts['finish']} printing, not a reverse-holo printing or a complete finish list."
    )
    add_entity(
        graph, "candidate-claim", physical_claim_id,
        {
            "claimId": physical_claim_id,
            "claimKind": "physical-printing",
            "sourceKind": "reviewed-positive-evidence",
            "sourceId": source_id,
            "sourceRecord": facts["checklist_url"],
            "evidenceStatus": "confirmed",
            "disposition": "established-and-mapped",
            "proposedTargetId": physical_id,
            "materializedTargetId": physical_id,
            "specimenIds": [facts["specimen_id"]],
            "reason": reason,
        },
    )
    add_entity(
        graph, "physical-printing", physical_id,
        {
            "physicalPrintingId": physical_id,
            "cardReleaseId": release_id,
            "finish": facts["finish"],
            "edition": None,
            "foilPattern": None,
            "markings": [],
            "distribution": {
                "kind": "booster-set",
                "name": facts["set_name"],
                "region": "LATAM",
                "date": facts["release_date"],
            },
            "cardSize": "unknown",
            "errorClass": None,
            "classificationState": "classified-from-positive-evidence",
            "sourceFinishUnitId": None,
            "sourcePrintingId": None,
            "sourceRecordIds": [source_id],
            "establishingClaimId": physical_claim_id,
            "specimenIds": [facts["specimen_id"]],
        },
    )
    add_edge(
        graph, "candidate-claim", physical_claim_id, "materializes",
        "physical-printing", physical_id,
        {"disposition": "established-and-mapped"},
    )
    add_edge(
        graph, "physical-printing", physical_id, "established-by",
        "candidate-claim", physical_claim_id,
    )
    add_edge(
        graph, "physical-printing", physical_id, "realizes", "card-release",
        release_id,
    )
    add_migration(
        graph,
        {
            "sourceKind": "reviewed-positive-evidence",
            "sourceId": source_id,
            "disposition": "established-and-mapped",
            "targetRef": physical_id,
            "reason": reason,
        },
    )


def apply_graph(graph: dict[str, Any]) -> dict[str, Any]:
    release = entity(graph, "card-release", RELEASE_ID)["payload"]
    if release.get("work") not in (None, WORK_KEY):
        raise ValueError("SVP LA 184 is already mapped to another work")
    release["work"] = WORK_KEY
    release["workMappingState"] = "mapped"
    append_unique(release.setdefault("sourceRecords", []), ASSET_URL, POKEMON_URL, EVENT_URL)

    local_set = entity(graph, "local-set", LOCAL_SET_ID)["payload"]
    append_unique(local_set.setdefault("sourceRecordIds", []), PRODUCT_SOURCE_ID)
    edition = entity(graph, "set-edition", EDITION_ID)["payload"]["catalogue"]
    append_unique(
        edition.setdefault("establishingEvidenceIds", []),
        PRODUCT_SOURCE_ID, EVENT_SOURCE_ID,
    )

    for source, target, reason in (
        (
            EVENT_SOURCE, EVENT_ID,
            "the dated organizer page maps to one Mexico prerelease wave, not a set scalar",
        ),
        (
            PRODUCT_SOURCE, LOCAL_SET_ID,
            "the exact LA asset and named official product contents support this local promo",
        ),
    ):
        add_entity(graph, "set-source-record", source["sourceRecordId"], source)
        add_entity(
            graph, "set-source-disposition", source["sourceRecordId"],
            {
                "sourceRecordId": source["sourceRecordId"],
                "disposition": "mapped",
                "targetRef": target,
                "reason": reason,
            },
        )
        add_edge(
            graph, "set-source-disposition", source["sourceRecordId"], "disposes",
            "set-source-record", source["sourceRecordId"],
        )
        add_migration(
            graph,
            {
                "sourceKind": "set-catalogue-source",
                "sourceId": source["sourceRecordId"],
                "disposition": "mapped",
                "targetRef": target,
                "reason": reason,
            },
        )

    add_entity(
        graph, "release-event", EVENT_ID,
        {
            "releaseEventId": EVENT_ID,
            "localSetId": LOCAL_SET_ID,
            "setEditionIds": [EDITION_ID],
            "eventKind": "prerelease-wave",
            "dateValue": "2025-03-22",
            "datePrecision": "day",
            "approximate": False,
            "status": "released",
            "timezone": None,
            "marketScopes": ["MX"],
            "marketScopeBasis": "the event venue is Culiacan, Sinaloa, Mexico",
            "sourceRecordId": EVENT_SOURCE_ID,
            "linkBasis": (
                "the collection owner identifies SVP LA 184 as distributed at this event; "
                "the organizer dates the Journey Together prerelease and the official product "
                "article independently names Hop's Snorlax among its four possible promos"
            ),
        },
    )
    add_edge(graph, "release-event", EVENT_ID, "belongs-to", "local-set", LOCAL_SET_ID)
    add_edge(graph, "release-event", EVENT_ID, "supports", "set-edition", EDITION_ID)

    add_entity(
        graph, "source-assertion", EVENT_ASSERTION_ID,
        {
            "sourceAssertionId": EVENT_ASSERTION_ID,
            "sourceRecordId": EVENT_SOURCE_ID,
            "assertionKind": "asserts-release-event",
            "releaseEventId": EVENT_ID,
        },
    )
    add_edge(
        graph, "source-assertion", EVENT_ASSERTION_ID, "asserted-by",
        "set-source-record", EVENT_SOURCE_ID,
    )
    add_edge(
        graph, "source-assertion", EVENT_ASSERTION_ID, "asserts-release-event",
        "release-event", EVENT_ID,
    )

    add_entity(
        graph, "source-assertion", SET_ASSERTION_ID,
        {
            "sourceAssertionId": SET_ASSERTION_ID,
            "sourceRecordId": PRODUCT_SOURCE_ID,
            "assertionKind": "asserts-local-set",
            "localSetId": LOCAL_SET_ID,
        },
    )
    add_edge(
        graph, "source-assertion", SET_ASSERTION_ID, "asserted-by",
        "set-source-record", PRODUCT_SOURCE_ID,
    )
    add_edge(
        graph, "source-assertion", SET_ASSERTION_ID, "asserts-local-set",
        "local-set", LOCAL_SET_ID,
    )
    add_edge(
        graph, "local-set", LOCAL_SET_ID, "observed-by",
        "set-source-record", PRODUCT_SOURCE_ID,
    )

    add_entity(
        graph, "rarity-claim", RARITY_ID,
        {
            "rarityClaimId": RARITY_ID,
            "cardReleaseId": RELEASE_ID,
            "sourceRecordId": PRODUCT_SOURCE_ID,
            "sourceProvider": "mixed-positive-evidence",
            "sourceVocabulary": "pokemon-official-journey-together-prerelease-2025",
            "sourceNativeValue": "promo card",
            "normalizedRarityId": "promo",
            "sourceProductKey": POKEMON_URL,
        },
    )
    add_edge(
        graph, "rarity-claim", RARITY_ID, "asserts-rarity-for",
        "card-release", RELEASE_ID,
    )
    add_edge(
        graph, "rarity-claim", RARITY_ID, "observed-by",
        "set-source-record", PRODUCT_SOURCE_ID,
    )
    add_entity(
        graph, "source-assertion", RARITY_ASSERTION_ID,
        {
            "sourceAssertionId": RARITY_ASSERTION_ID,
            "sourceRecordId": PRODUCT_SOURCE_ID,
            "assertionKind": "asserts-rarity-claim",
            "rarityClaimId": RARITY_ID,
        },
    )
    add_edge(
        graph, "source-assertion", RARITY_ASSERTION_ID, "asserted-by",
        "set-source-record", PRODUCT_SOURCE_ID,
    )
    add_edge(
        graph, "source-assertion", RARITY_ASSERTION_ID, "asserts-rarity-claim",
        "rarity-claim", RARITY_ID,
    )

    add_edge(
        graph, "card-release", RELEASE_ID, "implements", "work", WORK_ID,
        {
            "state": "mapped",
            "sourceRecordId": PRODUCT_SOURCE_ID,
            "basis": (
                "the official article names Hop's Snorlax and describes Extra Helpings plus "
                "its 170-damage attack; the exact LA asset carries their Spanish translation"
            ),
        },
    )

    physical_claim = {
        "claimId": PHYSICAL_CLAIM_ID,
        "claimKind": "physical-printing",
        "sourceKind": "reviewed-positive-evidence",
        "sourceId": PRODUCT_SOURCE_ID,
        "sourceRecord": POKEMON_URL,
        "evidenceStatus": "confirmed",
        "disposition": "established-and-mapped",
        "proposedTargetId": PHYSICAL_ID,
        "materializedTargetId": PHYSICAL_ID,
        "specimenIds": [SPECIMEN_ID],
        "reason": (
            "The exact official LA asset identifies SVP LA 184 and its Aventuras "
            "Compartidas mark; the official Build & Battle article names Hop's Snorlax "
            "as one of four unique foil promo cards. This establishes one holo prerelease "
            "printing, not Staff, another finish, or a complete finish list."
        ),
    }
    add_entity(graph, "candidate-claim", PHYSICAL_CLAIM_ID, physical_claim)
    add_entity(
        graph, "physical-printing", PHYSICAL_ID,
        {
            "physicalPrintingId": PHYSICAL_ID,
            "cardReleaseId": RELEASE_ID,
            "finish": "holo",
            "edition": None,
            "foilPattern": None,
            "markings": [
                {
                    "kind": "set-logo",
                    "role": "distribution-promo",
                    "text": "Aventuras Compartidas",
                }
            ],
            "distribution": {
                "kind": "prerelease",
                "name": "Aventuras Compartidas Prerelease",
                "region": "MX",
                "date": "2025-03-22",
            },
            "cardSize": "unknown",
            "errorClass": None,
            "classificationState": "classified-from-positive-evidence",
            "sourceFinishUnitId": None,
            "sourcePrintingId": None,
            "sourceRecordIds": [PRODUCT_SOURCE_ID, EVENT_SOURCE_ID],
            "establishingClaimId": PHYSICAL_CLAIM_ID,
            "specimenIds": [SPECIMEN_ID],
        },
    )
    add_edge(
        graph, "candidate-claim", PHYSICAL_CLAIM_ID, "materializes",
        "physical-printing", PHYSICAL_ID,
        {"disposition": "established-and-mapped"},
    )
    add_edge(
        graph, "physical-printing", PHYSICAL_ID, "established-by",
        "candidate-claim", PHYSICAL_CLAIM_ID,
    )
    add_edge(
        graph, "physical-printing", PHYSICAL_ID, "realizes",
        "card-release", RELEASE_ID,
    )
    add_migration(
        graph,
        {
            "sourceKind": "reviewed-positive-evidence",
            "sourceId": PRODUCT_SOURCE_ID,
            "disposition": "established-and-mapped",
            "targetRef": PHYSICAL_ID,
            "reason": physical_claim["reason"],
        },
    )

    for facts in NORMAL_SETS:
        apply_normal_graph(graph, facts)

    return graph_projection.project_physical_evidence(graph)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    original_sources = SOURCES_PATH.read_text(encoding="utf-8")
    original_graph = GRAPH_PATH.read_text(encoding="utf-8")
    original_specimens = SPECIMENS_PATH.read_text(encoding="utf-8")
    sources = json.loads(original_sources)
    graph = json.loads(original_graph)
    specimens = json.loads(original_specimens)
    apply_sources(sources)
    apply_specimens(specimens)
    graph = apply_graph(graph)
    wanted_sources = encoded(sources)
    wanted_graph = encoded(graph)
    wanted_specimens = encoded(specimens)

    if args.check:
        if (
            wanted_sources != original_sources
            or wanted_graph != original_graph
            or wanted_specimens != original_specimens
        ):
            raise SystemExit("issue #261 LATAM evidence pass is not applied")
        print("validated issue #261 LATAM release evidence")
        return 0

    SOURCES_PATH.write_text(wanted_sources, encoding="utf-8", newline="\n")
    GRAPH_PATH.write_text(wanted_graph, encoding="utf-8", newline="\n")
    SPECIMENS_PATH.write_text(wanted_specimens, encoding="utf-8", newline="\n")
    print("admitted issue #261 LATAM release evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
