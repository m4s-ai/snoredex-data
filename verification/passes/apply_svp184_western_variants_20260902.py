"""Apply the owner's SVP 184 prerelease/Staff evidence without merging ES and LA."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FINISHES = ROOT / "verification" / "finish_overrides.json"
REKEYS = ROOT / "verification" / "legacy_issue_rekeys.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
SPECIMENS = ROOT / "verification" / "specimens.json"
SET_SOURCES = ROOT / "verification" / "set_catalogue_sources.json"


REVIEWED_AT = "2026-09-02"
INSTAGRAM_URL = "https://www.instagram.com/p/DO6tQd5jNK8/"
ES_ASSET_URL = (
    "https://assets.pokemon.com/static-assets/content-assets/cms2-es-es/"
    "img/cards/web/SVP/SVP_ES_184.png"
)
OWNER_SOURCE_ID = "owner-svp184-western-prerelease-variants"
ES_SOURCE_ID = "pokemon-official-svp-es-184"
SOURCE_FIRST_ID = "WEST:SVP ES:184:base"
OLD_SOURCE_RELEASE = "RELEASE:WEST:Spanish:SVP ES:184:unmapped-work:SPEC-0034"
OLD_LEGACY_RELEASE = (
    "RELEASE:WEST:Spanish:SVP:184:Hops-Snorlax-Extra-Helpings-Dynamic-Press"
)
ES_RELEASE = (
    "RELEASE:WEST:Spanish:SVP ES:184:Hops-Snorlax-Extra-Helpings-Dynamic-Press"
)
WORK = "Hops-Snorlax-Extra-Helpings-Dynamic-Press"
WORK_ID = f"WORK:{WORK}"
ES_EDITION = "EDITION:WEST:Spanish:SVP ES"
LATAM_RELEASE = "RELEASE:LATAM:Spanish:SVP LA:184:unmapped-work:SPEC-0033"
LATAM_PHYSICAL = "PHYSICAL:d6b6feeffd3d1268"
LATAM_CLAIM = "CLAIM:positive:56aee25aabfce91a"
LATAM_SOURCE = "SET-SRC-POKEMON-SF:5fd21ee23dadfd0c"
LEGACY_IDS = ("U0282", "U0319")


SOURCES = {
    OWNER_SOURCE_ID: {
        "url": None,
        "sourceType": "Collection owner attestation (localized prerelease variants)",
        "authorityTier": "owner-attestation",
        "coverage": "positive-only",
        "supportsAbsence": False,
        "languages": ["English", "French", "German", "Italian", "Spanish", "Portuguese"],
        "retrievedAt": REVIEWED_AT,
        "evidence": (
            "The collection owner explicitly confirms that Hop's Snorlax SVP 184 exists "
            "as the normal prerelease promo and as the Staff prerelease promo in every "
            "Western language, and explicitly keeps European Spanish and Latin-American "
            "Spanish as separate localized releases. This establishes the two positive "
            "printings only; it does not close the finish list or identify a foil pattern."
        ),
    },
}


def printing(variant: str, *, staff: bool, spanish: bool = False) -> dict[str, Any]:
    label = "Juntos de Aventuras" if spanish else "Journey Together"
    return {
        "finish": "holo",
        "foilPattern": None,
        "markings": ([{
            "kind": "staff",
            "text": "Staff",
            "role": "distribution-promo",
        }] if staff else [{
            "kind": "set-logo",
            "text": label,
            "role": "distribution-promo",
        }]),
        "distribution": ({
            "kind": "prerelease-staff",
            "name": f"{label} Prerelease Staff",
        } if staff else {
            "kind": "prerelease",
            "name": f"{label} Prerelease",
        }),
        "cardSize": "unknown",
        "mappedVariants": [variant],
        "refinesAuto": not staff,
        "verificationStatus": "confirmed",
        "sourceRefs": [OWNER_SOURCE_ID],
    }


OVERRIDES = [
    {
        "setCode": "SVP",
        "number": "184",
        "languages": ["French", "German", "Italian", "Portuguese"],
        "suppressAutoFinishes": ["holo"],
        "mapAutoFinishes": {"holo": ["V1"]},
        "printings": [printing("V1", staff=False), printing("V2", staff=True)],
    },
    {
        "setCode": "SVP",
        "number": "184",
        "languages": ["Spanish"],
        "releaseSetCode": "SVP ES",
        "suppressAutoFinishes": ["holo"],
        "mapAutoFinishes": {"holo": ["V1"]},
        "printings": [
            printing("V1", staff=False, spanish=True),
            printing("V2", staff=True, spanish=True),
        ],
    },
]


QUESTION_SET = {
    "issueNumber": 266,
    "locality": "WEST",
    "language": "Spanish",
    "legacyUnitIds": list(LEGACY_IDS),
    "defaultDisposition": "needs-positive-local-identity",
    "mappings": [
        {
            "legacyUnitId": legacy_id,
            "sourceFirstRecordId": SOURCE_FIRST_ID,
            "assertionType": "same-work-decision",
            "assertedBy": "collection owner",
            "assertedAt": REVIEWED_AT,
            "evidenceUrl": ES_ASSET_URL,
            "evidence": (
                "The owner explicitly distinguishes European Spanish from Latin-American "
                "Spanish and confirms both the normal prerelease and Staff printings in each. "
                "The official SVP ES 184 asset positively establishes the European-Spanish "
                "localized card; both legacy product variants map to this same local release."
            ),
        }
        for legacy_id in LEGACY_IDS
    ],
}


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def encoded(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(encoded(payload), encoding="utf-8", newline="\n")


def append_unique(values: list[str], *new_values: str) -> None:
    values[:] = sorted(set(values) | set(new_values))


def entity(graph: dict[str, Any], entity_type: str, entity_id: str) -> dict[str, Any]:
    matches = [
        row for row in graph["entities"]
        if row.get("entityType") == entity_type and row.get("entityId") == entity_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one {entity_type} {entity_id}, found {len(matches)}")
    return matches[0]


def upsert_entity(
    graph: dict[str, Any], entity_type: str, entity_id: str, payload: dict[str, Any]
) -> None:
    graph["entities"] = [
        row for row in graph["entities"]
        if not (row.get("entityType") == entity_type and row.get("entityId") == entity_id)
    ]
    graph["entities"].append({
        "entityType": entity_type,
        "entityId": entity_id,
        "origin": "reviewed-evidence-issue-266",
        "payload": payload,
    })


def upsert_edge(
    graph: dict[str, Any], from_type: str, from_id: str, relation: str,
    to_type: str, to_id: str, provenance: dict[str, Any] | None = None,
) -> None:
    graph["edges"] = [
        row for row in graph["edges"]
        if (row.get("fromType"), row.get("fromId"), row.get("relation"),
            row.get("toType"), row.get("toId"))
        != (from_type, from_id, relation, to_type, to_id)
    ]
    graph["edges"].append({
        "fromType": from_type,
        "fromId": from_id,
        "relation": relation,
        "toType": to_type,
        "toId": to_id,
        "provenance": provenance or {},
    })


def upsert_migration(graph: dict[str, Any], row: dict[str, Any]) -> None:
    graph["migrationDispositions"] = [
        item for item in graph["migrationDispositions"]
        if (item.get("sourceKind"), item.get("sourceId"))
        != (row["sourceKind"], row["sourceId"])
    ]
    graph["migrationDispositions"].append(row)


def replace_release_ids(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: replace_release_ids(item) for key, item in value.items()}
    if isinstance(value, list):
        return [replace_release_ids(item) for item in value]
    if value in {OLD_SOURCE_RELEASE, OLD_LEGACY_RELEASE}:
        return ES_RELEASE
    return value


def deduplicate_graph(graph: dict[str, Any]) -> None:
    entities: dict[tuple[str, str], dict[str, Any]] = {}
    for row in graph["entities"]:
        entities[(row["entityType"], row["entityId"])] = row
    graph["entities"] = list(entities.values())
    edges: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in graph["edges"]:
        key = (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
        edges[key] = row
    graph["edges"] = list(edges.values())


def apply_finish_overrides(document: dict[str, Any]) -> None:
    document["sources"].update(SOURCES)
    document["sources"].pop(ES_SOURCE_ID, None)
    by_key = {
        (row["setCode"], row["number"], tuple(row.get("languages") or [])): row
        for row in OVERRIDES
    }
    kept = []
    for row in document["overrides"]:
        key = (row["setCode"], row["number"], tuple(row.get("languages") or []))
        kept.append(by_key.pop(key, row))
    document["overrides"] = kept + list(by_key.values())
    document["meta"]["lastUpdated"] = REVIEWED_AT


def apply_graph(graph: dict[str, Any], set_sources: dict[str, Any]) -> dict[str, Any]:
    graph = replace_release_ids(graph)
    deduplicate_graph(graph)

    source_claim = entity(graph, "candidate-claim", f"CLAIM:source-first:{SOURCE_FIRST_ID}")
    source_claim["payload"]["proposedTargetId"] = ES_RELEASE
    source_claim["payload"]["materializedTargetId"] = ES_RELEASE
    for legacy_id in LEGACY_IDS:
        claim = entity(graph, "candidate-claim", f"CLAIM:legacy:{legacy_id}")
        claim["payload"]["proposedTargetId"] = ES_RELEASE
        claim["payload"]["materializedTargetId"] = ES_RELEASE

    claim_ids = [f"CLAIM:legacy:{value}" for value in LEGACY_IDS]
    source_claim_id = f"CLAIM:source-first:{SOURCE_FIRST_ID}"
    upsert_entity(graph, "card-release", ES_RELEASE, {
        "cardReleaseId": ES_RELEASE,
        "setEditionId": ES_EDITION,
        "locality": "WEST",
        "language": "Spanish",
        "script": "Latn",
        "localSetCode": "SVP ES",
        "localNumber": "184",
        "localIdentifierKnown": True,
        "state": "identified",
        "work": WORK,
        "workMappingState": "mapped-by-explicit-equivalence",
        "viaLegacySetCode": None,
        "viaLegacyNumber": None,
        "claimIds": sorted(claim_ids + [source_claim_id]),
        "establishingClaimIds": sorted(claim_ids + [source_claim_id]),
        "nonEstablishingClaimIds": [],
        "legacyVariants": ["V1", "V2"],
        "legacyProducts": [
            "https://www.cardmarket.com/en/Pokemon/Products/Singles/"
            "SV-Black-Star-Promos/Hops-Snorlax-V1-SVP184",
            "https://www.cardmarket.com/en/Pokemon/Products/Singles/"
            "SV-Black-Star-Promos/Hops-Snorlax-V2-SVP184",
        ],
        "sourceRecords": sorted({ES_ASSET_URL, "https://api.tcgdex.net/v2/es/cards/svp-184"}),
        "sourceFirstRecordIds": [SOURCE_FIRST_ID],
        "legacyCounterpartUnitIds": list(LEGACY_IDS),
        "legacyIdentityAliases": [["SVP", "184"]],
    })
    upsert_entity(graph, "catalogue-card-release-ref", ES_RELEASE, {
        "cardReleaseId": ES_RELEASE,
        "setEditionId": ES_EDITION,
        "collectorNumber": "184",
        "origin": "issue-266-explicit-equivalence",
    })
    upsert_edge(graph, "card-release", ES_RELEASE, "belongs-to", "set-edition", ES_EDITION)
    upsert_edge(
        graph, "card-release", ES_RELEASE, "implements", "work", WORK_ID,
        {"state": "mapped-by-explicit-equivalence"},
    )
    upsert_edge(
        graph, "catalogue-card-release-ref", ES_RELEASE, "belongs-to",
        "set-edition", ES_EDITION,
    )
    upsert_edge(
        graph, "catalogue-card-release-ref", ES_RELEASE, "references",
        "card-release", ES_RELEASE,
    )

    graph["edges"] = [
        row for row in graph["edges"]
        if not (
            row.get("fromId") == ES_RELEASE
            and row.get("relation") == "belongs-to"
            and row.get("toId") != ES_EDITION
        )
    ]

    for mapping in QUESTION_SET["mappings"]:
        legacy_id = mapping["legacyUnitId"]
        assertion_id = f"ASSERT:same-work:{legacy_id}:{SOURCE_FIRST_ID}"
        assertion = {
            "assertionId": assertion_id,
            "assertionType": mapping["assertionType"],
            "fromId": ES_RELEASE,
            "toId": WORK_ID,
            "legacyUnitId": legacy_id,
            "sourceFirstRecordId": SOURCE_FIRST_ID,
            "assertedBy": mapping["assertedBy"],
            "assertedAt": mapping["assertedAt"],
            "evidenceUrl": mapping["evidenceUrl"],
            "evidence": mapping["evidence"],
            "destructiveMergeAllowed": False,
        }
        upsert_entity(graph, "equivalence-assertion", assertion_id, assertion)
        upsert_edge(
            graph, "equivalence-assertion", assertion_id, "relates",
            "card-release", ES_RELEASE, assertion,
        )
        upsert_edge(
            graph, "equivalence-assertion", assertion_id, "relates",
            "work", WORK_ID, assertion,
        )
        upsert_migration(graph, {
            "sourceKind": "legacy-issue-rekey",
            "sourceId": legacy_id,
            "disposition": "linked-local-counterpart",
            "targetRef": ES_RELEASE,
            "targetRefs": [ES_RELEASE],
            "reason": "issue #266 re-key",
        })

    latam_release = entity(graph, "card-release", LATAM_RELEASE)["payload"]
    append_unique(latam_release.setdefault("sourceRecords", []), INSTAGRAM_URL)
    latam_claim = entity(graph, "candidate-claim", LATAM_CLAIM)["payload"]
    append_unique(latam_claim.setdefault("specimenIds", []), "SPEC-0478")
    latam_physical = entity(graph, "physical-printing", LATAM_PHYSICAL)["payload"]
    append_unique(latam_physical.setdefault("specimenIds", []), "SPEC-0478")
    source = next(
        row for row in set_sources["sourceRecords"]
        if row.get("sourceRecordId") == LATAM_SOURCE
    )
    upsert_entity(graph, "set-source-record", LATAM_SOURCE, source)

    deduplicate_graph(graph)
    graph["entities"].sort(key=lambda row: (row["entityType"], row["entityId"]))
    graph["edges"].sort(key=lambda row: (
        row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"]
    ))
    graph["migrationDispositions"].sort(
        key=lambda row: (row["sourceKind"], row["sourceId"])
    )
    return graph


def apply_set_sources(document: dict[str, Any]) -> None:
    matches = [
        row for row in document["sourceRecords"]
        if row.get("sourceRecordId") == LATAM_SOURCE
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one set source {LATAM_SOURCE}, found {len(matches)}")
    source = matches[0]
    source["retrieved"] = REVIEWED_AT
    raw = source["raw"]
    append_unique(raw.setdefault("providers", []), "owner-instagram")
    append_unique(raw.setdefault("sourceUrls", []), INSTAGRAM_URL)
    raw["ownerAttestation"] = {
        "recordedAt": REVIEWED_AT,
        "assertion": (
            "The collection owner confirms both the normal prerelease and Staff "
            "prerelease printings for SVP LA 184 and supplies the retained Instagram "
            "photographs SPEC-0477 and SPEC-0478."
        ),
    }
    append_unique(
        raw["physicalPrintingEvidence"].setdefault("specimenIds", []), "SPEC-0478"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    specimens = read(SPECIMENS)
    by_id = {row["specimenId"]: row for row in specimens["specimens"]}
    for specimen_id in ("SPEC-0477", "SPEC-0478"):
        row = by_id.get(specimen_id)
        if not row or not row.get("photograph") or not row.get("photographSha256"):
            raise SystemExit(f"{specimen_id} is not a pinned Instagram specimen")

    finishes = read(FINISHES)
    rekeys = read(REKEYS)
    graph = read(GRAPH)
    set_sources = read(SET_SOURCES)
    before = (encoded(finishes), encoded(rekeys), encoded(graph), encoded(set_sources))

    apply_finish_overrides(finishes)
    by_issue = {row["issueNumber"]: row for row in rekeys["questionSets"]}
    by_issue[266] = QUESTION_SET
    rekeys["questionSets"] = sorted(by_issue.values(), key=lambda row: row["issueNumber"])
    apply_set_sources(set_sources)
    graph = apply_graph(graph, set_sources)
    after = (encoded(finishes), encoded(rekeys), encoded(graph), encoded(set_sources))

    if args.check:
        if before != after:
            raise SystemExit("SVP 184 Western-variant inputs are stale; run this pass without --check")
        print("SVP 184 Western-variant inputs are current")
        return 0

    write(FINISHES, finishes)
    write(REKEYS, rekeys)
    write(GRAPH, graph)
    write(SET_SOURCES, set_sources)
    print("applied SVP 184 Western prerelease/Staff evidence with separate ES and LA releases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
