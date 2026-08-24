#!/usr/bin/env python3
"""Historical record of the four photographed Dutch Jungle printings from issue #269.

SUPERSEDED: routine physical evidence now enters through
``verification/fetch_attachment.py --issue ... --manifest ...`` and the canonical projectors.
Keep this file as an auditable provenance record; do not add new issue-specific passes.

The issue supplies positive physical evidence for holo 11/64 and non-holo 27/64 in
both 1st Edition and Unlimited.  Unlimited is recorded from the collection owner's
explicit printing identification together with the retained full-card photograph;
it is not inferred from catalogue silence.  The pass is idempotent.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECIMENS = ROOT / "verification" / "specimens.json"
OVERRIDES = ROOT / "verification" / "finish_overrides.json"
GRAPH = ROOT / "verification" / "authoritative_graph.json"
ISSUE = "https://github.com/m4s-ai/snoredex-data/issues/269"
RECORDED_AT = "2026-08-24"

ATTACHMENT_11_UNLIMITED = (
    "https://github.com/user-attachments/assets/08b12485-3115-4d90-abb9-e2e9fb867f8d"
)
ATTACHMENT_11_FIRST = (
    "https://github.com/user-attachments/assets/6ea2a81b-a8da-41a6-96b2-b0e575175475"
)
CARDMARKET_27_FIRST_A = (
    "https://marketplace-article-scans.s3.cardmarket.com/2122869820/2122869820.jpg"
)
CARDMARKET_27_FIRST_B = (
    "https://marketplace-article-scans.s3.cardmarket.com/1993695317/1993695317.jpg"
)
ATTACHMENT_27_UNLIMITED = (
    "https://github.com/user-attachments/assets/7279c09d-7892-44cd-9297-7a2694687b5d"
)

RELEASE_11 = "RELEASE:WEST:Dutch:JU:11:Snorlax-Thick-Skinned-Body-Slam"
RELEASE_27 = "RELEASE:WEST:Dutch:JU:27:Snorlax-Thick-Skinned-Body-Slam"

SPECIMENS_TO_ADD = [
    {
        "specimenId": "SPEC-0040",
        "setCode": "JU",
        "number": "11/64",
        "variant": "V1",
        "language": "Dutch",
        "heldBy": "collection-owner supplied source image",
        "inspectedFrom": "owner-supplied physical card image",
        "photograph": None,
        "observed": (
            "Dutch Jungle Snorlax 11/64 photographed as a complete physical card and "
            "explicitly identified by the collection owner as the Unlimited printing. "
            "The Dutch name Relaxo, 11/64 collector number and reflective holographic "
            "art field are legible."
        ),
        "recordedAt": RECORDED_AT,
        "citedBy": ["F0167-P02"],
        "physicalObservation": {
            "finish": "holo",
            "edition": "Unlimited",
            "foilPattern": None,
            "markings": None,
            "markingRole": None,
            "cardSize": "standard",
            "basis": (
                "The collection owner explicitly identified this physical card as the "
                "Unlimited printing; the retained full-card photograph independently shows "
                "Dutch Jungle 11/64 and a reflective holographic artwork field."
            ),
        },
    },
    {
        "specimenId": "SPEC-0041",
        "setCode": "JU",
        "number": "11/64",
        "variant": "V1",
        "language": "Dutch",
        "heldBy": "collection-owner supplied source image",
        "inspectedFrom": "owner-supplied physical card image",
        "photograph": None,
        "observed": (
            "Dutch Jungle Relaxo 11/64 in a CGC holder. The card face visibly carries "
            "the EDITIE 1 stamp and a reflective holographic art field; the grading label "
            "independently reads 1st Edition 11/64 Holo."
        ),
        "recordedAt": RECORDED_AT,
        "citedBy": ["F0167-P01"],
        "physicalObservation": {
            "finish": "holo",
            "edition": "1st Edition",
            "foilPattern": None,
            "markings": "EDITIE 1",
            "markingRole": "print-identity",
            "cardSize": "standard",
            "basis": (
                "The photographed Dutch 11/64 card visibly carries EDITIE 1 and a "
                "reflective holographic artwork field; the CGC label also identifies it "
                "as 1st Edition 11/64 Holo."
            ),
        },
    },
    {
        "specimenId": "SPEC-0042",
        "setCode": "JU",
        "number": "27/64",
        "variant": "V2",
        "language": "Dutch",
        "heldBy": "third-party seller",
        "inspectedFrom": "Cardmarket article-scan photograph",
        "photograph": None,
        "observed": (
            "Cardmarket article scan of a complete Dutch Jungle Relaxo 27/64 physical "
            "card. The card face visibly carries the EDITIE 1 stamp and the artwork field "
            "is printed non-holo."
        ),
        "recordedAt": RECORDED_AT,
        "citedBy": ["F0174-P01"],
        "physicalObservation": {
            "finish": "non-holo",
            "edition": "1st Edition",
            "foilPattern": None,
            "markings": "EDITIE 1",
            "markingRole": "print-identity",
            "cardSize": "standard",
            "basis": (
                "The Dutch 27/64 card visibly carries EDITIE 1 and its artwork window "
                "shows the uniformly printed non-holo treatment."
            ),
        },
    },
    {
        "specimenId": "SPEC-0043",
        "setCode": "JU",
        "number": "27/64",
        "variant": "V2",
        "language": "Dutch",
        "heldBy": "third-party seller",
        "inspectedFrom": "Cardmarket article-scan photograph",
        "photograph": None,
        "observed": (
            "Independent Cardmarket article scan corroborating the Dutch Jungle Relaxo "
            "27/64 1st Edition non-holo printing. EDITIE 1 and the matte printed artwork "
            "field are visible on the complete card face."
        ),
        "recordedAt": RECORDED_AT,
        "citedBy": ["F0174-P01"],
        "physicalObservation": {
            "finish": "non-holo",
            "edition": "1st Edition",
            "foilPattern": None,
            "markings": "EDITIE 1",
            "markingRole": "print-identity",
            "cardSize": "standard",
            "basis": (
                "A second physical scan visibly carries EDITIE 1 and shows the Dutch "
                "27/64 card with a uniformly printed non-holo artwork window."
            ),
        },
    },
    {
        "specimenId": "SPEC-0044",
        "setCode": "JU",
        "number": "27/64",
        "variant": "V2",
        "language": "Dutch",
        "heldBy": "collection-owner supplied source image",
        "inspectedFrom": "owner-supplied physical card image",
        "photograph": None,
        "observed": (
            "Dutch Jungle Relaxo 27/64 photographed as a complete physical card and "
            "explicitly identified by the collection owner as the Unlimited printing. "
            "The card number and non-holographic printed artwork field are legible."
        ),
        "recordedAt": RECORDED_AT,
        "citedBy": ["F0174-P02"],
        "physicalObservation": {
            "finish": "non-holo",
            "edition": "Unlimited",
            "foilPattern": None,
            "markings": None,
            "markingRole": None,
            "cardSize": "standard",
            "basis": (
                "The collection owner explicitly identified this physical card as the "
                "Unlimited printing; the retained full-card photograph independently shows "
                "Dutch Jungle 27/64 with a uniformly printed non-holo artwork field."
            ),
        },
    },
]

SOURCES_TO_ADD = {
    "issue269-dutch-ju11-unlimited": {
        "url": ATTACHMENT_11_UNLIMITED,
        "sourceType": "Owner-supplied physical card photograph",
        "evidence": (
            "Full Dutch Relaxo 11/64 card face, identified by the collection owner as "
            "Unlimited, with the holographic artwork field visible; retained as SPEC-0040."
        ),
    },
    "issue269-dutch-ju11-first": {
        "url": ATTACHMENT_11_FIRST,
        "sourceType": "Owner-supplied physical card photograph",
        "evidence": (
            "Dutch Relaxo 11/64 in a CGC holder with visible EDITIE 1 stamp, holographic "
            "art field and a 1st Edition 11/64 Holo label; retained as SPEC-0041."
        ),
    },
    "issue269-dutch-ju27-first-a": {
        "url": CARDMARKET_27_FIRST_A,
        "sourceType": "Cardmarket seller listing photograph",
        "evidence": (
            "Complete Dutch Relaxo 27/64 card face with visible EDITIE 1 stamp and "
            "non-holo art field; retained as SPEC-0042."
        ),
    },
    "issue269-dutch-ju27-first-b": {
        "url": CARDMARKET_27_FIRST_B,
        "sourceType": "Cardmarket seller listing photograph",
        "evidence": (
            "Independent complete Dutch Relaxo 27/64 scan corroborating EDITIE 1 and "
            "the non-holo treatment; retained as SPEC-0043."
        ),
    },
    "issue269-dutch-ju27-unlimited": {
        "url": ATTACHMENT_27_UNLIMITED,
        "sourceType": "Owner-supplied physical card photograph",
        "evidence": (
            "Full Dutch Relaxo 27/64 card face, identified by the collection owner as "
            "Unlimited, with the non-holo art field visible; retained as SPEC-0044."
        ),
    },
}

FIRST_MARKING = [{"kind": "edition-stamp", "text": "EDITIE 1", "role": "print-identity"}]

OVERRIDES_TO_ADD = [
    {
        "setCode": "JU",
        "number": "11",
        "languages": ["Dutch"],
        "suppressAutoFinishes": ["holo"],
        "printings": [
            {
                "finish": "holo",
                "edition": "1st Edition",
                "foilPattern": None,
                "markings": FIRST_MARKING,
                "distribution": None,
                "image": "verification/specimens/SPEC-0041.png",
                "cardSize": "standard",
                "mappedVariants": ["V1"],
                "verificationStatus": "confirmed",
                "sourceRefs": ["issue269-dutch-ju11-first"],
            },
            {
                "finish": "holo",
                "edition": "Unlimited",
                "foilPattern": None,
                "markings": [],
                "distribution": None,
                "image": "verification/specimens/SPEC-0040.png",
                "cardSize": "standard",
                "mappedVariants": ["V1"],
                "verificationStatus": "confirmed",
                "sourceRefs": ["issue269-dutch-ju11-unlimited"],
            },
        ],
    },
    {
        "setCode": "JU",
        "number": "27",
        "languages": ["Dutch"],
        "suppressAutoFinishes": ["non-holo"],
        "printings": [
            {
                "finish": "non-holo",
                "edition": "1st Edition",
                "foilPattern": None,
                "markings": FIRST_MARKING,
                "distribution": None,
                "image": "verification/specimens/SPEC-0042.jpg",
                "cardSize": "standard",
                "mappedVariants": ["V2"],
                "verificationStatus": "confirmed",
                "sourceRefs": [
                    "issue269-dutch-ju27-first-a",
                    "issue269-dutch-ju27-first-b",
                ],
            },
            {
                "finish": "non-holo",
                "edition": "Unlimited",
                "foilPattern": None,
                "markings": [],
                "distribution": None,
                "image": "verification/specimens/SPEC-0044.png",
                "cardSize": "standard",
                "mappedVariants": ["V2"],
                "verificationStatus": "confirmed",
                "sourceRefs": ["issue269-dutch-ju27-unlimited"],
            },
        ],
    },
]

PHYSICALS = [
    ("F0167-P01", "F0167", RELEASE_11, "holo", "1st Edition", FIRST_MARKING),
    ("F0167-P02", "F0167", RELEASE_11, "holo", "Unlimited", []),
    ("F0174-P01", "F0174", RELEASE_27, "non-holo", "1st Edition", FIRST_MARKING),
    ("F0174-P02", "F0174", RELEASE_27, "non-holo", "Unlimited", []),
]

SPECIMEN_TARGETS = {
    "SPEC-0040": "PHYSICAL:F0167-P02",
    "SPEC-0041": "PHYSICAL:F0167-P01",
    "SPEC-0042": "PHYSICAL:F0174-P01",
    "SPEC-0043": "PHYSICAL:F0174-P01",
    "SPEC-0044": "PHYSICAL:F0174-P02",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, document: dict) -> None:
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def record_specimens() -> None:
    document = read(SPECIMENS)
    by_id = {row["specimenId"]: row for row in document["specimens"]}
    for expected in SPECIMENS_TO_ADD:
        current = by_id.get(expected["specimenId"])
        if current is None:
            document["specimens"].append(expected)
            by_id[expected["specimenId"]] = expected
            continue
        current_without_filed_photo = {
            key: value
            for key, value in current.items()
            if key not in {"photograph", "photographSource"}
        }
        expected_without_filed_photo = {
            key: value
            for key, value in expected.items()
            if key not in {"photograph", "photographSource"}
        }
        if current_without_filed_photo != expected_without_filed_photo:
            raise ValueError(f"{expected['specimenId']} exists with different evidence")
    document["specimens"].sort(key=lambda row: row["specimenId"])
    document["count"] = len(document["specimens"])
    write(SPECIMENS, document)


def record_finish_overrides() -> None:
    document = read(OVERRIDES)
    for source_id, expected in SOURCES_TO_ADD.items():
        current = document["sources"].get(source_id)
        if current is not None and current != expected:
            raise ValueError(f"finish source {source_id} exists with different data")
        document["sources"][source_id] = expected

    def override_key(row: dict) -> tuple:
        return (row.get("setCode"), str(row.get("number") or ""), tuple(row.get("languages") or []))

    by_key = {override_key(row): row for row in document["overrides"]}
    for expected in OVERRIDES_TO_ADD:
        key = override_key(expected)
        current = by_key.get(key)
        if current is not None and current != expected:
            raise ValueError(f"finish override {key} exists with different data")
        if current is None:
            document["overrides"].append(expected)
            by_key[key] = expected
    document["meta"]["lastUpdated"] = RECORDED_AT
    write(OVERRIDES, document)


def entity(entity_type: str, entity_id: str, payload: dict) -> dict:
    return {
        "entityType": entity_type,
        "entityId": entity_id,
        "origin": "issue-269-dutch-physical-evidence",
        "payload": payload,
    }


def record_graph() -> None:
    graph = read(GRAPH)
    entities = graph["entities"]
    by_key = {(row["entityType"], row["entityId"]): row for row in entities}

    for printing_id, finish_unit_id, release_id, finish, edition, markings in PHYSICALS:
        claim_id = f"CLAIM:finish:{printing_id}"
        physical_id = f"PHYSICAL:{printing_id}"
        claim_payload = {
            "claimId": claim_id,
            "claimKind": "physical-printing",
            "sourceKind": "finish-printing-record",
            "sourceId": printing_id,
            "evidenceStatus": "confirmed",
            "disposition": "established-and-mapped",
            "proposedTargetId": physical_id,
            "materializedTargetId": physical_id,
            "reason": "issue #269 physical photographs confirm the exact finish and edition",
        }
        claim_key = ("candidate-claim", claim_id)
        if claim_key in by_key:
            by_key[claim_key]["payload"] = claim_payload
        else:
            row = entity("candidate-claim", claim_id, claim_payload)
            entities.append(row)
            by_key[claim_key] = row

        physical_payload = {
            "physicalPrintingId": physical_id,
            "cardReleaseId": release_id,
            "finish": finish,
            "edition": edition,
            "foilPattern": None,
            "markings": markings,
            "distribution": None,
            "cardSize": "standard",
            "errorClass": None,
            "classificationState": "classified-from-positive-evidence",
            "sourceFinishUnitId": finish_unit_id,
            "sourcePrintingId": printing_id,
            "establishingClaimId": claim_id,
        }
        physical_key = ("physical-printing", physical_id)
        current = by_key.get(physical_key)
        if current is not None and current["payload"] != physical_payload:
            raise ValueError(f"physical printing {physical_id} exists with different data")
        if current is None:
            row = entity("physical-printing", physical_id, physical_payload)
            entities.append(row)
            by_key[physical_key] = row

    for specimen_id, corroborated_physical_id in SPECIMEN_TARGETS.items():
        claim_id = f"CLAIM:specimen:{specimen_id}"
        payload = {
            "claimId": claim_id,
            "claimKind": "physical-printing",
            "sourceKind": "specimen-observation",
            "sourceId": specimen_id,
            "evidenceStatus": "observed",
            "disposition": "candidate-needs-evidence",
            "proposedTargetId": f"PHYSICAL:specimen:{specimen_id}",
            "materializedTargetId": None,
            "reason": (
                f"corroborates {corroborated_physical_id}, already established from the "
                "finish store"
            ),
        }
        key = ("candidate-claim", claim_id)
        current = by_key.get(key)
        if current is not None and current["payload"] != payload:
            raise ValueError(f"specimen claim {claim_id} exists with different data")
        if current is None:
            row = entity("candidate-claim", claim_id, payload)
            entities.append(row)
            by_key[key] = row

    promoted_claim_ids = {f"CLAIM:finish:{row[0]}" for row in PHYSICALS}
    graph["edges"] = [
        row
        for row in graph["edges"]
        if not (row["fromId"] in promoted_claim_ids and row["relation"] == "proposes-for")
    ]
    edge_keys = {
        (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
        for row in graph["edges"]
    }
    for printing_id, _finish_unit_id, release_id, _finish, _edition, _markings in PHYSICALS:
        claim_id = f"CLAIM:finish:{printing_id}"
        physical_id = f"PHYSICAL:{printing_id}"
        additions = [
            {
                "fromType": "candidate-claim",
                "fromId": claim_id,
                "relation": "materializes",
                "toType": "physical-printing",
                "toId": physical_id,
                "provenance": {"disposition": "established-and-mapped"},
            },
            {
                "fromType": "physical-printing",
                "fromId": physical_id,
                "relation": "established-by",
                "toType": "candidate-claim",
                "toId": claim_id,
                "provenance": {},
            },
            {
                "fromType": "physical-printing",
                "fromId": physical_id,
                "relation": "realizes",
                "toType": "card-release",
                "toId": release_id,
                "provenance": {},
            },
        ]
        for row in additions:
            key = (row["fromType"], row["fromId"], row["relation"], row["toType"], row["toId"])
            if key not in edge_keys:
                graph["edges"].append(row)
                edge_keys.add(key)

    disposition_rows = graph["migrationDispositions"]
    dispositions = {
        (row["sourceKind"], row["sourceId"]): row
        for row in disposition_rows
    }

    def upsert_disposition(key: tuple[str, str], row: dict) -> None:
        current = dispositions.get(key)
        if current is None:
            disposition_rows.append(row)
            dispositions[key] = row
        else:
            current.clear()
            current.update(row)

    for printing_id, *_rest in PHYSICALS:
        upsert_disposition(("finish-printing-record", printing_id), {
            "sourceKind": "finish-printing-record",
            "sourceId": printing_id,
            "disposition": "established-and-mapped",
            "targetRef": f"PHYSICAL:{printing_id}",
            "reason": "issue #269 physical photographs confirm the exact finish and edition",
        })
    for specimen_id, physical_id in SPECIMEN_TARGETS.items():
        upsert_disposition(("specimen-observation", specimen_id), {
            "sourceKind": "specimen-observation",
            "sourceId": specimen_id,
            "disposition": "candidate-needs-evidence",
            "targetRef": None,
            "reason": f"corroborates {physical_id}, already established from the finish store",
        })

    entity_counts = Counter(row["entityType"] for row in entities)
    disposition_counts = Counter(row["disposition"] for row in graph["migrationDispositions"])
    graph["summary"] = {
        "entities": len(entities),
        "edges": len(graph["edges"]),
        "migrationInputs": len(graph["migrationDispositions"]),
        "migrationDispositions": dict(sorted(disposition_counts.items())),
        "candidateClaims": entity_counts["candidate-claim"],
        "cardReleases": entity_counts["card-release"],
        "physicalPrintings": entity_counts["physical-printing"],
        "setSourceRecords": entity_counts["set-source-record"],
        "setSourceDispositions": sum(
            row["sourceKind"] == "set-catalogue-source"
            for row in graph["migrationDispositions"]
        ),
        "localizations": entity_counts["localization"],
    }
    graph["meta"]["generated"] = RECORDED_AT
    write(GRAPH, graph)


def main() -> int:
    record_specimens()
    record_finish_overrides()
    record_graph()
    print("recorded 5 specimens and 4 Dutch Jungle physical printings for issue #269")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
