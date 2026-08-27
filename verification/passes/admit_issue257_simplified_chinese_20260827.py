"""Admit the positive Simplified-Chinese finish and re-key evidence from issue #257."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FINISHES = ROOT / "verification" / "finish_overrides.json"
PRINTS = ROOT / "verification" / "source_first_prints.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
sys.path.insert(0, str(ROOT / "scripts"))

import authoritative_graph as graph_projection  # noqa: E402


def source(
    url: str, source_type: str, evidence: str, *, tier: str, coverage: str | None = None,
) -> dict:
    return {
        "url": url,
        "sourceType": source_type,
        "authorityTier": tier,
        "coverage": coverage or ("product-line-description" if tier == "official-primary" else "positive-only"),
        "supportsAbsence": False,
        "languages": ["S-Chinese"],
        "retrievedAt": "2026-08-27",
        "evidence": evidence,
    }


SOURCES = {
    "pokemon-cn-simplified-finish-rules": source(
        "https://www.pokemon.cn/tcg/product/16377.html",
        "Official Mainland China Simplified Chinese card-finish guide",
        "The official guide states that cards of rarity R and above are foil cards produced with mirror processing, and that Simplified Chinese C, U and R cards can be pulled as the locality-specific patterned random foil treatment. It does not state that these are the only printings.",
        tier="official-primary", coverage="positive-only",
    ),
    "pokemon-cn-shining-synergy-starter": source(
        "https://www.pokemon.cn/tcg/product/16344.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official Shining Synergy GX starter-deck specification states that all 60 constructed-deck cards, drawn from its named 351-card pool, are 平卡 (non-holo).",
        tier="official-primary",
    ),
    "pokemon-cn-dynamax-clash-starter": source(
        "https://www.pokemon.cn/tcg/product/16268.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official Dynamax Clash specification states that all 60 cards in each constructed starter deck are 平卡 (non-holo), and that the Deck Building Box includes one random Pokémon V 闪卡 (foil card).",
        tier="official-primary",
    ),
    "pokemon-cn-primordial-arts-starter": source(
        "https://www.pokemon.cn/tcg/product/16070.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official Primordial Arts V starter-deck specification states that all 60 constructed-deck cards, drawn from its named 178-card pool, are 平卡 (non-holo).",
        tier="official-primary",
    ),
    "pokemon-cn-gallant-galaxy-starter": source(
        "https://www.pokemon.cn/tcg/product/15831.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official Gallant Galaxy V starter-deck specification states that all 60 constructed-deck cards, drawn from its named 160-card pool, are 平卡 (non-holo).",
        tier="official-primary",
    ),
    "pokemon-cn-battle-party-flat-and-foil": source(
        "https://www.pokemon.cn/tcg/product/15951.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official Battle Party specification describes ordinary and foil packs with the same card contents and different processing, positively establishing both flat and foil copies of each included deck card.",
        tier="official-primary",
    ),
    "pokemon-cn-battle-party-dream-decks": source(
        "https://www.pokemon.cn/tcg/product/19640.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official product specification states that Shared Dream has fourteen flat-card decks plus one foil Mewtwo deck and Shining Dream has eighteen flat-card decks plus two foil decks; the corresponding flat and foil decks have identical card contents and differ only in processing.",
        tier="official-primary",
    ),
    "pokemon-cn-happy-set-1-decks": source(
        "https://www.pokemon.cn/tcg/product/15585.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official first Happy Set specification positively describes the same constructed-deck contents in ordinary and foil processing, establishing both flat and foil copies for cards in the paired deck.",
        tier="official-primary",
    ),
    "pokemon-cn-happy-set-4-decks": source(
        "https://www.pokemon.cn/tcg/product/21022.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official fourth Happy Set specification positively describes ordinary and foil versions with the same constructed-deck contents and different processing.",
        tier="official-primary",
    ),
    "pokemon-cn-departure-special-pack": source(
        "https://www.pokemon.cn/tcg/product/15499.html",
        "Official Mainland China Simplified Chinese product specification",
        "The official Departure Special Pack specification states that the second card can be a newly included Pokémon special-illustration 闪卡; SPEC-0154 establishes the exact CSVL1C 109/049 Snorlax special-illustration identity.",
        tier="official-primary",
    ),
    "pokumon-s-p-cs-061": source(
        "https://pokumon.com/card/snorlax-061-s-p-simplified-chinese-promo/",
        "Specialist per-language promo record",
        "Pokumon's exact Simplified-Chinese 061/S-P Snorlax record identifies the Tournament Participation printing as Non-holo.",
        tier="specialist-reference",
    ),
}


def printing(finish: str, source_ref: str, *, distribution: dict | None = None) -> dict:
    return {
        "finish": finish,
        "foilPattern": None,
        "markings": None,
        "distribution": distribution,
        "cardSize": "standard",
        "mappedVariants": ["base"],
        "verificationStatus": "confirmed",
        "sourceRefs": [source_ref],
    }


def simple_override(
    set_code: str, number: str, finish: str, variant: str, source_ref: str,
    *, distribution: dict | None = None,
) -> dict:
    row = printing(finish, source_ref, distribution=distribution)
    row["mappedVariants"] = [variant]
    return {
        "setCode": set_code,
        "number": number,
        "languages": ["S-Chinese"],
        "printings": [row],
    }


OVERRIDES = [
    simple_override("151C", "143", "mirror-holo", "V1", "pokemon-cn-simplified-finish-rules"),
    simple_override("151C", "169", "holo", "V2", "pokemon-cn-simplified-finish-rules"),
    simple_override("CS1aC", "110", "mirror-holo", "base", "pokemon-cn-simplified-finish-rules"),
    simple_override("CS1aC", "111", "holo", "V1", "pokemon-cn-simplified-finish-rules"),
    simple_override("CS1aC", "112", "holo", "V1", "pokemon-cn-simplified-finish-rules"),
    simple_override("CS1aC", "207", "holo", "V2", "pokemon-cn-simplified-finish-rules"),
    simple_override(
        "CS1DC", "152", "non-holo", "base", "pokemon-cn-dynamax-clash-starter",
        distribution={"kind": "fixed-deck", "name": "Dynamax Clash V Starter Deck"},
    ),
    simple_override("CS2aC", "086", "mirror-holo", "V1", "pokemon-cn-simplified-finish-rules"),
    simple_override("CS2aC", "142", "holo", "V2", "pokemon-cn-simplified-finish-rules"),
    simple_override(
        "CS3DC", "117", "non-holo", "base", "pokemon-cn-primordial-arts-starter",
        distribution={"kind": "fixed-deck", "name": "Primordial Arts V Starter Deck"},
    ),
    simple_override("CS5aC", "093", "mirror-holo", "base", "pokemon-cn-simplified-finish-rules"),
    simple_override(
        "CS5DC", "097", "non-holo", "V1", "pokemon-cn-gallant-galaxy-starter",
        distribution={"kind": "fixed-deck", "name": "Gallant Galaxy V Starter Deck"},
    ),
    simple_override(
        "CS5DC", "098", "non-holo", "V2", "pokemon-cn-gallant-galaxy-starter",
        distribution={"kind": "fixed-deck", "name": "Gallant Galaxy V Starter Deck"},
    ),
    simple_override("CS6bC", "113", "mirror-holo", "base", "pokemon-cn-simplified-finish-rules"),
    simple_override("CSM1cC", "102", "holo", "base", "pokemon-cn-simplified-finish-rules"),
    simple_override("CSM2bC", "124", "mirror-holo", "base", "pokemon-cn-simplified-finish-rules"),
    simple_override("CSM2cC", "103", "holo", "V1", "pokemon-cn-simplified-finish-rules"),
    simple_override("CSM2cC", "170", "holo", "V2", "pokemon-cn-simplified-finish-rules"),
    simple_override("CSM2cC", "171", "holo", "V3", "pokemon-cn-simplified-finish-rules"),
    simple_override(
        "CSM2DC", "213", "non-holo", "base", "pokemon-cn-shining-synergy-starter",
        distribution={"kind": "fixed-deck", "name": "Shining Synergy GX Starter Deck"},
    ),
    simple_override("CSV10C", "175", "mirror-holo", "base", "pokemon-cn-simplified-finish-rules"),
    simple_override("CSV5C", "115", "mirror-holo", "base", "pokemon-cn-simplified-finish-rules"),
    simple_override("CSV7C", "158", "mirror-holo", "base", "pokemon-cn-simplified-finish-rules"),
    {
        "setCode": "CSAC", "number": "009", "languages": ["S-Chinese"],
        "printings": [printing("holo", "pokemon-cn-dynamax-clash-starter", distribution={"kind": "deck-building-box", "name": "Dynamax Clash Deck Building Box random Pokémon V foil"})],
    },
    {
        "setCode": "CSMPC", "number": "h009", "languages": ["S-Chinese"],
        "printings": [
            printing("non-holo", "pokemon-cn-battle-party-flat-and-foil", distribution={"kind": "fixed-deck", "name": "Battle Party ordinary deck"}),
            printing("holo", "pokemon-cn-battle-party-flat-and-foil", distribution={"kind": "fixed-deck", "name": "Battle Party foil deck"}),
        ],
    },
    {
        "setCode": "CSVE1C", "number": "093", "languages": ["S-Chinese"],
        "printings": [printing("non-holo", "pokemon-cn-battle-party-dream-decks", distribution={"kind": "fixed-deck", "name": "Battle Party Shared Dream flat-card deck"})],
    },
    {
        "setCode": "CSVE2C", "number": "122", "languages": ["S-Chinese"],
        "printings": [printing("non-holo", "pokemon-cn-battle-party-dream-decks", distribution={"kind": "fixed-deck", "name": "Battle Party Shining Dream flat-card deck"})],
    },
    {
        "setCode": "CSVH1C", "number": "a001", "languages": ["S-Chinese"],
        "printings": [
            printing("non-holo", "pokemon-cn-happy-set-1-decks", distribution={"kind": "fixed-deck", "name": "Happy Set 1 ordinary deck"}),
            printing("holo", "pokemon-cn-happy-set-1-decks", distribution={"kind": "fixed-deck", "name": "Happy Set 1 foil deck"}),
        ],
    },
    {
        "setCode": "CSVH4C", "number": "a003", "languages": ["S-Chinese"],
        "printings": [
            printing("non-holo", "pokemon-cn-happy-set-4-decks", distribution={"kind": "fixed-deck", "name": "Happy Set 4 ordinary deck"}),
            printing("holo", "pokemon-cn-happy-set-4-decks", distribution={"kind": "fixed-deck", "name": "Happy Set 4 foil deck"}),
        ],
    },
    {
        "setCode": "CSVH4C", "number": "p006", "languages": ["S-Chinese"],
        "printings": [
            printing("non-holo", "pokemon-cn-happy-set-4-decks", distribution={"kind": "fixed-deck", "name": "Happy Set 4 ordinary deck"}),
            printing("holo", "pokemon-cn-happy-set-4-decks", distribution={"kind": "fixed-deck", "name": "Happy Set 4 foil deck"}),
        ],
    },
    {
        "setCode": "CSVL1C", "number": "109", "languages": ["S-Chinese"],
        "printings": [printing("holo", "pokemon-cn-departure-special-pack", distribution={"kind": "special-pack", "name": "Departure Special Pack special-illustration foil slot"})],
    },
    {
        "setCode": "S-P/CS", "number": "061", "languages": ["S-Chinese"],
        "printings": [printing("non-holo", "pokumon-s-p-cs-061", distribution={"kind": "event-promo", "name": "2023 tournament participation promo"})],
    },
    {
        "setCode": "SV-P/CS", "number": "277", "languages": ["S-Chinese"],
        "printings": [printing("holo", "pokemon-cn-simplified-finish-rules", distribution={"kind": "event-promo-pack", "name": "Event Special Pack Part 3"})],
    },
]


SOURCE_FIRST_PRINTS = [
    {
        "printId": "CN:CS2aC:086:base", "locality": "CN", "localSetCode": "CS2aC", "localNumber": "086", "variant": "base",
        "language": "S-Chinese", "script": "Hans", "name": "卡比兽", "cardName": "Snorlax", "catchUpOf": "the legacy Japanese s4 084 work",
        "specimenId": None, "providerId": "52poke", "sourceUrl": "https://wiki.52poke.com/wiki/%E5%8D%A1%E6%AF%94%E5%85%BD%EF%BC%88S4%EF%BC%89", "corroborated": True,
        "markAssetUrl": None, "cardImageUrl": None,
        "evidence": "52poke's per-card language table identifies the Simplified-Chinese Vivid Portrayals printing as collector number 086, rarity R, released 2023-08-18. The existing reviewed U0289 evidence and shared card identity establish it as the local counterpart of legacy s4 084; the local release remains distinct.",
    },
    {
        "printId": "CN:CS2DaC:038/053:base", "locality": "CN", "localSetCode": "CS2DaC", "localNumber": "038/053", "variant": "base",
        "language": "S-Chinese", "script": "Hans", "name": "卡比兽", "cardName": "Snorlax", "catchUpOf": "the legacy Japanese sH 038 work",
        "specimenId": None, "providerId": "bulbapedia", "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Sword_%26_Shield_Family_Pok%C3%A9mon_Card_Game_(TCG)", "corroborated": True,
        "markAssetUrl": None, "cardImageUrl": None,
        "evidence": "The Family Pokémon Card Game article positively records the Mainland China release and its closed product card list includes Snorlax 038/053. PokemonLore's Simplified-Chinese CS2DaC set list independently identifies 038/053. This establishes the distinct local counterpart of legacy sH 038; no finish is inferred.",
    },
    {
        "printId": "CN:CS4DaC:341/414:base", "locality": "CN", "localSetCode": "CS4DaC", "localNumber": "341/414", "variant": "base",
        "language": "S-Chinese", "script": "Hans", "name": "卡比兽", "cardName": "Snorlax", "catchUpOf": "the legacy Japanese sI100 341 work",
        "specimenId": "SPEC-0155", "providerId": "bulbapedia", "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Start_Deck_100_(TCG)", "corroborated": True,
        "markAssetUrl": None, "cardImageUrl": None,
        "evidence": "The Start Deck 100 list identifies the Simplified-Chinese 341/414 Snorlax; SPEC-0155 independently shows the exact printed CS4DaC 341/414 identity and reverse-holo treatment. This establishes the distinct local counterpart of legacy sI100 341.",
    },
    {
        "printId": "CN:CS4DaC:342/414:base", "locality": "CN", "localSetCode": "CS4DaC", "localNumber": "342/414", "variant": "base",
        "language": "S-Chinese", "script": "Hans", "name": "卡比兽", "cardName": "Snorlax", "catchUpOf": "the legacy Japanese sI100 342 work",
        "specimenId": "SPEC-0156", "providerId": "bulbapedia", "sourceUrl": "https://bulbapedia.bulbagarden.net/wiki/Start_Deck_100_(TCG)", "corroborated": True,
        "markAssetUrl": None, "cardImageUrl": None,
        "evidence": "The Start Deck 100 list identifies the Simplified-Chinese 342/414 Snorlax; SPEC-0156 independently shows the exact printed CS4DaC 342/414 identity and the exact seller listing identifies it as Holo. This establishes the distinct local counterpart of legacy sI100 342.",
    },
]


QUESTION_SET = {
    "issueNumber": 257,
    "locality": "CN",
    "language": "S-Chinese",
    "legacyUnitIds": ["U0289", "U0639", "U0646", "U0651", "U0655"],
    "defaultDisposition": "needs-positive-local-identity",
    "mappings": [
        {
            "legacyUnitId": legacy, "sourceFirstRecordId": target, "assertionType": "same-work-decision",
            "assertedBy": "repository verification pass", "assertedAt": "2026-08-27", "evidenceUrl": url,
            "evidence": evidence,
        }
        for legacy, target, url, evidence in [
            ("U0289", "CN:CS2aC:086:base", "https://wiki.52poke.com/wiki/%E5%8D%A1%E6%AF%94%E5%85%BD%EF%BC%88S4%EF%BC%89", "The exact Simplified-Chinese 086 printing is the reviewed local counterpart of legacy s4 084; both release identities remain distinct."),
            ("U0639", "CN:CS2DaC:038/053:base", "https://bulbapedia.bulbagarden.net/wiki/Sword_%26_Shield_Family_Pok%C3%A9mon_Card_Game_(TCG)", "The closed Family Pokémon Card Game list and independent CS2DaC checklist establish the exact Simplified-Chinese 038/053 counterpart of legacy sH 038; both release identities remain distinct."),
            ("U0651", "CN:CS4DaC:341/414:base", "https://pikaqian.com/cards/fa648ddc-e3fa-40cf-9c5f-446d70f22568", "The Start Deck 100 list and SPEC-0155 establish the exact Simplified-Chinese CS4DaC 341/414 counterpart of legacy sI100 341."),
            ("U0655", "CN:CS4DaC:342/414:base", "https://www.ebay.com/itm/356156650452", "The Start Deck 100 list and SPEC-0156 establish the exact Simplified-Chinese CS4DaC 342/414 counterpart of legacy sI100 342."),
        ]
    ],
}


RELEASES = {
    "CN:CS2aC:086:base": {
        "releaseId": "RELEASE:CN:S-Chinese:CS2aC:086:Snorlax-Gormandize-Body-Slam",
        "work": "Snorlax-Gormandize-Body-Slam",
        "legacyUnitId": "U0289",
    },
    "CN:CS2DaC:038/053:base": {
        "releaseId": "RELEASE:CN:S-Chinese:CS2DaC:038/053:Snorlax-Heavy-Impact",
        "work": "Snorlax-Heavy-Impact",
        "legacyUnitId": "U0639",
    },
    "CN:CS4DaC:341/414:base": {
        "releaseId": "RELEASE:CN:S-Chinese:CS4DaC:341/414:Snorlax-Heavy-Impact",
        "work": "Snorlax-Heavy-Impact",
        "legacyUnitId": "U0651",
    },
    "CN:CS4DaC:342/414:base": {
        "releaseId": "RELEASE:CN:S-Chinese:CS4DaC:342/414:Snorlax-Heavy-Impact",
        "work": "Snorlax-Heavy-Impact",
        "legacyUnitId": "U0655",
    },
}


def stable_profile_id(locality: str, local_code: str) -> str:
    material = f"{locality}\x1f{local_code}".encode()
    return f"SET-SRC-SF-{hashlib.sha256(material).hexdigest()[:12].upper()}"


def encoded(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def append_unique(values: list[str], *new_values: str) -> None:
    values[:] = sorted(set(values) | set(new_values))


def upsert_entity(
    graph: dict[str, Any], entity_type: str, entity_id: str, payload: dict[str, Any],
    *, origin: str = "reviewed-evidence-issue-257",
) -> None:
    expected = {
        "entityType": entity_type,
        "entityId": entity_id,
        "origin": origin,
        "payload": payload,
    }
    matches = [
        row for row in graph["entities"]
        if row.get("entityType") == entity_type and row.get("entityId") == entity_id
    ]
    if not matches:
        graph["entities"].append(expected)
    elif len(matches) != 1:
        raise ValueError(f"ambiguous graph entity {entity_type} {entity_id}")
    else:
        matches[0].update(expected)


def entity(graph: dict[str, Any], entity_type: str, entity_id: str) -> dict[str, Any]:
    matches = [
        row for row in graph["entities"]
        if row.get("entityType") == entity_type and row.get("entityId") == entity_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {entity_type} {entity_id}, found {len(matches)}")
    return matches[0]


def upsert_edge(
    graph: dict[str, Any], from_type: str, from_id: str, relation: str,
    to_type: str, to_id: str, provenance: dict[str, Any] | None = None,
) -> None:
    key = (from_type, from_id, relation, to_type, to_id)
    expected = {
        "fromType": from_type,
        "fromId": from_id,
        "relation": relation,
        "toType": to_type,
        "toId": to_id,
        "provenance": provenance or {},
    }
    matches = [
        row for row in graph["edges"]
        if (
            row.get("fromType"), row.get("fromId"), row.get("relation"),
            row.get("toType"), row.get("toId"),
        ) == key
    ]
    if not matches:
        graph["edges"].append(expected)
    elif len(matches) != 1:
        raise ValueError(f"ambiguous graph edge {key}")
    else:
        matches[0].update(expected)


def upsert_migration(graph: dict[str, Any], expected: dict[str, Any]) -> None:
    key = (expected["sourceKind"], expected["sourceId"])
    matches = [
        row for row in graph["migrationDispositions"]
        if (row.get("sourceKind"), row.get("sourceId")) == key
    ]
    if not matches:
        graph["migrationDispositions"].append(expected)
    elif len(matches) != 1:
        raise ValueError(f"ambiguous graph migration {key}")
    else:
        matches[0].clear()
        matches[0].update(expected)


def source_profile(group: list[dict[str, Any]]) -> dict[str, Any]:
    locality = group[0]["locality"]
    local_code = group[0]["localSetCode"]
    numbers = sorted(row["localNumber"] for row in group)
    denominators = {
        number.partition("/")[2] for number in numbers if number.partition("/")[2].isdigit()
    }
    return {
        "sourceRecordId": stable_profile_id(locality, local_code),
        "sourceKind": "source-first-local-set-profile",
        "provider": "mixed-positive-evidence",
        "providerRecordKey": f"{locality}\x1f{local_code}",
        "retrieved": "2026-08-27",
        "raw": {
            "localCode": local_code,
            "localName": None,
            "locality": locality,
            "languages": sorted({row["language"] for row in group}),
            "scripts": sorted({row["script"] for row in group}),
            "printIds": sorted(row["printId"] for row in group),
            "providers": sorted({row["providerId"] for row in group}),
            "sourceUrls": sorted({row["sourceUrl"] for row in group}),
            "printedSetSize": int(next(iter(denominators))) if len(denominators) == 1 else None,
            "printedSetSizeBasis": (
                "the denominator printed beside the collector number on every observed card"
                if len(denominators) == 1
                else "the observed collector number has no printed denominator; no set size is inferred"
            ),
            "localeSuffix": None,
            "observedCollectorNumbers": numbers,
            "observedCoverage": "cards returned by the issue #257 Snorlax research, not an enumeration of the set",
            "markAssetUrls": sorted({row["markAssetUrl"] for row in group if row.get("markAssetUrl")}),
            "cardImageUrls": sorted({row["cardImageUrl"] for row in group if row.get("cardImageUrl")}),
        },
    }


def apply_set_sources(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in SOURCE_FIRST_PRINTS:
        grouped.setdefault(row["localSetCode"], []).append(row)
    profiles = {code: source_profile(group) for code, group in grouped.items()}
    by_id = {row["sourceRecordId"]: row for row in document["sourceRecords"]}
    by_id.update({row["sourceRecordId"]: row for row in profiles.values()})
    document["sourceRecords"] = sorted(by_id.values(), key=lambda row: row["sourceRecordId"])
    document["meta"]["counts"]["sourceRecords"] = len(document["sourceRecords"])
    document["meta"]["counts"]["sourceFirstLocalSets"] = sum(
        row["sourceKind"] == "source-first-local-set-profile"
        for row in document["sourceRecords"]
    )
    return profiles


def apply_graph(
    graph: dict[str, Any], profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    localization_id = "LOCALIZATION:CN:zh-Hans"

    for local_code, profile in profiles.items():
        source_id = profile["sourceRecordId"]
        local_set_id = f"LOCALSET:CN:{local_code}"
        edition_id = f"EDITION:CN:S-Chinese:{local_code}"
        source_claim_ids = sorted(
            f"CLAIM:source-first:{row['printId']}"
            for row in SOURCE_FIRST_PRINTS if row["localSetCode"] == local_code
        )

        upsert_entity(graph, "set-source-record", source_id, profile)
        disposition = {
            "sourceRecordId": source_id,
            "disposition": "mapped",
            "targetRef": local_set_id,
            "reason": "provider locality and raw local code identify this local-set node",
        }
        upsert_entity(graph, "set-source-disposition", source_id, disposition)
        upsert_edge(
            graph, "set-source-disposition", source_id, "disposes",
            "set-source-record", source_id,
        )
        upsert_migration(graph, {
            "sourceKind": "set-catalogue-source",
            "sourceId": source_id,
            "disposition": "mapped",
            "targetRef": local_set_id,
            "reason": disposition["reason"],
        })

        local_set_matches = [
            row for row in graph["entities"]
            if row.get("entityType") == "local-set" and row.get("entityId") == local_set_id
        ]
        if local_set_matches:
            if len(local_set_matches) != 1:
                raise ValueError(f"ambiguous local set {local_set_id}")
            append_unique(local_set_matches[0]["payload"].setdefault("sourceRecordIds", []), source_id)
        else:
            upsert_entity(graph, "local-set", local_set_id, {
                "localSetId": local_set_id,
                "locality": "CN",
                "localCode": local_code,
                "observedNames": [],
                "productKind": "physical-card-set-or-product",
                "sourceRecordIds": [source_id],
            })
        upsert_edge(graph, "local-set", local_set_id, "observed-by", "set-source-record", source_id)

        edition_matches = [
            row for row in graph["entities"]
            if row.get("entityType") == "set-edition" and row.get("entityId") == edition_id
        ]
        if edition_matches:
            if len(edition_matches) != 1:
                raise ValueError(f"ambiguous set edition {edition_id}")
            payload = edition_matches[0]["payload"]
            append_unique(payload["identity"].setdefault("establishingClaimIds", []), *source_claim_ids)
            append_unique(payload["catalogue"].setdefault("establishingEvidenceIds", []), source_id)
        else:
            upsert_entity(graph, "set-edition", edition_id, {
                "setEditionId": edition_id,
                "identity": {
                    "setEditionId": edition_id,
                    "locality": "CN",
                    "language": "S-Chinese",
                    "script": "Hans",
                    "localSetCode": local_code,
                    "localIdentifierKnown": True,
                    "state": "identified",
                    "viaLegacySetCodes": [],
                    "establishingClaimIds": source_claim_ids,
                    "localizationId": localization_id,
                },
                "catalogue": {
                    "setEditionId": edition_id,
                    "localSetId": local_set_id,
                    "locality": "CN",
                    "language": "S-Chinese",
                    "script": "Hans",
                    "localCode": local_code,
                    "state": "identified",
                    "establishingEvidenceIds": [source_id],
                    "localizationId": localization_id,
                },
            })
        upsert_edge(graph, "set-edition", edition_id, "belongs-to", "local-set", local_set_id)
        upsert_edge(
            graph, "set-edition", edition_id, "localized-as", "localization", localization_id,
            {
                "decisionRef": "https://github.com/m4s-ai/snoredex-data/issues/254",
                "reviewedAt": "2026-08-24",
            },
        )

    prints_by_id = {row["printId"]: row for row in SOURCE_FIRST_PRINTS}
    for print_id, facts in RELEASES.items():
        row = prints_by_id[print_id]
        claim_id = f"CLAIM:source-first:{print_id}"
        release_id = facts["releaseId"]
        edition_id = f"EDITION:CN:S-Chinese:{row['localSetCode']}"
        work_id = f"WORK:{facts['work']}"
        claim = {
            "claimId": claim_id,
            "claimKind": "card-release",
            "sourceKind": "source-first-record",
            "sourceId": print_id,
            "sourceRecord": row["sourceUrl"],
            "evidenceStatus": "confirmed",
            "disposition": "established-and-mapped",
            "proposedTargetId": release_id,
            "materializedTargetId": release_id,
            "reason": "positive source-first specimen/card record",
        }
        upsert_entity(graph, "candidate-claim", claim_id, claim)
        upsert_migration(graph, {
            "sourceKind": "source-first-record",
            "sourceId": print_id,
            "disposition": "established-and-mapped",
            "targetRef": release_id,
            "reason": claim["reason"],
        })

        release_matches = [
            item for item in graph["entities"]
            if item.get("entityType") == "card-release" and item.get("entityId") == release_id
        ]
        if release_matches:
            if len(release_matches) != 1:
                raise ValueError(f"ambiguous card release {release_id}")
            release = release_matches[0]["payload"]
            if release.get("work") != facts["work"]:
                raise ValueError(f"existing release has a different Work: {release_id}")
            release["workMappingState"] = "mapped-by-explicit-equivalence"
            append_unique(release.setdefault("claimIds", []), claim_id)
            append_unique(release.setdefault("establishingClaimIds", []), claim_id)
            append_unique(release.setdefault("sourceRecords", []), row["sourceUrl"])
            append_unique(release.setdefault("sourceFirstRecordIds", []), print_id)
            append_unique(release.setdefault("legacyCounterpartUnitIds", []), facts["legacyUnitId"])
        else:
            upsert_entity(graph, "card-release", release_id, {
                "cardReleaseId": release_id,
                "setEditionId": edition_id,
                "locality": "CN",
                "language": "S-Chinese",
                "script": "Hans",
                "localSetCode": row["localSetCode"],
                "localNumber": row["localNumber"],
                "localIdentifierKnown": True,
                "state": "identified",
                "work": facts["work"],
                "workMappingState": "mapped-by-explicit-equivalence",
                "viaLegacySetCode": None,
                "viaLegacyNumber": None,
                "claimIds": [claim_id],
                "establishingClaimIds": [claim_id],
                "nonEstablishingClaimIds": [],
                "legacyVariants": [],
                "legacyProducts": [],
                "sourceRecords": [row["sourceUrl"]],
                "sourceFirstRecordIds": [print_id],
                "legacyCounterpartUnitIds": [facts["legacyUnitId"]],
            })

        upsert_edge(
            graph, "candidate-claim", claim_id, "materializes", "card-release", release_id,
            {"disposition": "established-and-mapped"},
        )
        upsert_edge(graph, "card-release", release_id, "belongs-to", "set-edition", edition_id)
        upsert_edge(
            graph, "card-release", release_id, "implements", "work", work_id,
            {"state": "mapped-by-explicit-equivalence"},
        )

        upsert_entity(
            graph, "catalogue-card-release-ref", release_id,
            {
                "cardReleaseId": release_id,
                "setEditionId": edition_id,
                "collectorNumber": row["localNumber"],
                "origin": "issue-257-source-first-evidence",
            },
            origin="reviewed-evidence-issue-257",
        )
        upsert_edge(
            graph, "catalogue-card-release-ref", release_id, "belongs-to",
            "set-edition", edition_id,
        )
        upsert_edge(
            graph, "catalogue-card-release-ref", release_id, "references",
            "card-release", release_id,
        )

    mapping_by_legacy = {row["legacyUnitId"]: row for row in QUESTION_SET["mappings"]}
    for legacy_id in QUESTION_SET["legacyUnitIds"]:
        mapping = mapping_by_legacy.get(legacy_id)
        if mapping is None:
            upsert_migration(graph, {
                "sourceKind": "legacy-issue-rekey",
                "sourceId": legacy_id,
                "disposition": QUESTION_SET["defaultDisposition"],
                "targetRef": None,
                "targetRefs": [],
                "reason": "issue #257 re-key",
            })
            continue

        print_id = mapping["sourceFirstRecordId"]
        release_id = RELEASES[print_id]["releaseId"]
        work_id = f"WORK:{RELEASES[print_id]['work']}"
        assertion_id = f"ASSERT:same-work:{legacy_id}:{print_id}"
        assertion = {
            "assertionId": assertion_id,
            "assertionType": mapping["assertionType"],
            "fromId": release_id,
            "toId": work_id,
            "legacyUnitId": legacy_id,
            "sourceFirstRecordId": print_id,
            "assertedBy": mapping["assertedBy"],
            "assertedAt": mapping["assertedAt"],
            "evidenceUrl": mapping["evidenceUrl"],
            "evidence": mapping["evidence"],
            "destructiveMergeAllowed": False,
        }
        upsert_entity(graph, "equivalence-assertion", assertion_id, assertion)
        upsert_edge(
            graph, "equivalence-assertion", assertion_id, "relates",
            "card-release", release_id, assertion,
        )
        upsert_edge(
            graph, "equivalence-assertion", assertion_id, "relates",
            "work", work_id, assertion,
        )
        upsert_migration(graph, {
            "sourceKind": "legacy-issue-rekey",
            "sourceId": legacy_id,
            "disposition": "linked-local-counterpart",
            "targetRef": release_id,
            "targetRefs": [release_id],
            "reason": "issue #257 re-key",
        })

    return graph_projection.project_physical_evidence(graph)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    finish = read(FINISHES)
    before_finish = json.dumps(finish, sort_keys=True, ensure_ascii=False)
    finish["sources"].update(SOURCES)
    finish["sources"].pop("52poke-sv-p-cs-277", None)
    issue_keys = {
        (row["setCode"], row["number"], tuple(row["languages"])) for row in OVERRIDES
    }
    finish["overrides"] = [
        row for row in finish["overrides"]
        if (row["setCode"], row["number"], tuple(row.get("languages") or [])) not in issue_keys
    ] + OVERRIDES
    finish["meta"]["lastUpdated"] = "2026-08-27"

    prints = read(PRINTS)
    before_prints = json.dumps(prints, sort_keys=True, ensure_ascii=False)
    prints_by_id = {row["printId"]: row for row in prints["prints"]}
    prints_by_id.pop("CN:CS2aC:086/115:base", None)
    prints_by_id.update({row["printId"]: row for row in SOURCE_FIRST_PRINTS})
    prints["prints"] = sorted(prints_by_id.values(), key=lambda row: row["printId"])
    prints["meta"]["generated"] = "2026-08-27"
    prints["meta"]["counts"]["admitted"] = len(prints["prints"])

    rekeys = read(REKEYS)
    before_rekeys = json.dumps(rekeys, sort_keys=True, ensure_ascii=False)
    by_issue = {row["issueNumber"]: row for row in rekeys["questionSets"]}
    by_issue[257] = QUESTION_SET
    rekeys["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])

    set_sources = read(SET_SOURCES)
    before_set_sources = encoded(set_sources)
    profiles = apply_set_sources(set_sources)

    graph = read(GRAPH)
    before_graph = encoded(graph)
    graph = apply_graph(graph, profiles)

    specimens = {row["specimenId"]: row for row in read(SPECIMENS)["specimens"]}
    for specimen_id in ("SPEC-0146", "SPEC-0147", "SPEC-0148", "SPEC-0149", "SPEC-0150", "SPEC-0151", "SPEC-0152", "SPEC-0153", "SPEC-0154", "SPEC-0155", "SPEC-0156"):
        row = specimens.get(specimen_id)
        if not row or not row.get("photograph") or not row.get("photographSha256"):
            raise SystemExit(f"{specimen_id} is not a pinned issue-257 specimen")

    changed = any([
        before_finish != json.dumps(finish, sort_keys=True, ensure_ascii=False),
        before_prints != json.dumps(prints, sort_keys=True, ensure_ascii=False),
        before_rekeys != json.dumps(rekeys, sort_keys=True, ensure_ascii=False),
        before_set_sources != encoded(set_sources),
        before_graph != encoded(graph),
    ])
    if args.check:
        if changed:
            raise SystemExit("issue #257 reviewed inputs are stale; run this pass without --check")
        print("issue #257 Simplified-Chinese reviewed inputs are current")
        return 0

    write(FINISHES, finish)
    write(PRINTS, prints)
    write(REKEYS, rekeys)
    SET_SOURCES.write_text(encoded(set_sources), encoding="utf-8", newline="\n")
    GRAPH.write_text(encoded(graph), encoding="utf-8", newline="\n")
    print(f"admitted {len(OVERRIDES)} finish overrides, {len(SOURCE_FIRST_PRINTS)} local prints and 4 positive re-keys for issue #257")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
