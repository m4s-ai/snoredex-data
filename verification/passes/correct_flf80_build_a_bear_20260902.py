#!/usr/bin/env python3
"""Separate the English-only FLF 80 Build-A-Bear promo from regular FLF 80."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
DATE = "2026-09-02"
CHECKED_AT = f"{DATE}T00:00:00"
IMAGE_URL = "https://product-images.s3.cardmarket.com/51/FLF/886906/886906.jpg"
PRODUCT_URL = (
    "https://www.tcgplayer.com/product/232309/pokemon-miscellaneous-cards-and-products-"
    "snorlax-80-106-build-a-bear-workshop-exclusive?page=1&Language=all"
)
CARDMARKET_URL = "https://www.cardmarket.com/en/Pokemon/Products/Singles/Flashfire/Snorlax-V2-FLF1"
VARIANT_NAME = "Build-A-Bear Workshop promo (English/USA only)"
VARIANT_SOURCE = "Exact retained product image plus collection-owner distribution adjudication"

ENGLISH_ID = "U0615"
EXCLUDED = {
    "U0616": "French",
    "U0617": "German",
    "U0618": "Spanish",
    "U0619": "Italian",
    "U0620": "Portuguese",
    "U0621": "Russian",
}

ENGLISH_EVIDENCE = (
    "The retained exact Cardmarket product image shows English card text, collector number 80/106 "
    "and the Build-A-Bear Workshop retailer stamp. It establishes Cardmarket V2 as the English "
    "promo and is retained as SPEC-0479."
)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def journal_key(row: dict) -> tuple[str | None, str | None, str]:
    evidence = row.get("evidence")
    if not isinstance(evidence, str):
        evidence = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    return row.get("unitId"), row.get("status"), evidence


def excluded_evidence(language: str) -> str:
    article = "an" if language == "Italian" else "a"
    return (
        "The retained exact Cardmarket product image identifies FLF 80 V2 as the English "
        "Build-A-Bear Workshop promo. The collection owner explicitly adjudicates that this "
        "promo was distributed only in the USA and printed only in English: \"Diese v2 ist nur "
        "für English belegt, vermisch das nicht. Diese promo gab es nur in den USA.\" The regular "
        f"localized FLF 80 V1 remains separate; this decision excludes only {article} {language} V2 promo."
    )


def remove_establishing_ref(value, claim_id: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"establishingClaimIds", "establishingEvidenceIds"} and isinstance(child, list):
                value[key] = [item for item in child if item != claim_id]
            else:
                remove_establishing_ref(child, claim_id)
    elif isinstance(value, list):
        for child in value:
            remove_establishing_ref(child, claim_id)


def update_graph() -> None:
    graph_path = VERIFY / "authoritative_graph.json"
    graph = read(graph_path)
    claims = {
        row["entityId"]: row["payload"]
        for row in graph["entities"]
        if row["entityType"] == "candidate-claim"
    }
    english_claim = claims[f"CLAIM:legacy:{ENGLISH_ID}"]
    english_claim["sourceRecord"] = IMAGE_URL

    reason = (
        "candidate remains non-establishing; another confirmed claim establishes the regular "
        "language release without transferring the English-only promo status"
    )
    for unit_id in EXCLUDED:
        claim_id = f"CLAIM:legacy:{unit_id}"
        claim = claims[claim_id]
        target = claim["proposedTargetId"]
        claim.update({
            "sourceRecord": None,
            "evidenceStatus": "contradicted",
            "disposition": "bounded-contradicted",
            "materializedTargetId": None,
            "reason": reason,
        })
        remove_establishing_ref(graph["entities"], claim_id)
        release = next(
            row["payload"] for row in graph["entities"]
            if row["entityType"] == "card-release" and row["entityId"] == target
        )
        release.setdefault("nonEstablishingClaimIds", [])
        if claim_id not in release["nonEstablishingClaimIds"]:
            release["nonEstablishingClaimIds"].append(claim_id)
            release["nonEstablishingClaimIds"].sort()
        graph["edges"] = [
            edge for edge in graph["edges"]
            if not (
                edge["fromType"] == "candidate-claim"
                and edge["fromId"] == claim_id
                and edge["relation"] == "materializes"
            )
        ]
        migration = next(
            row for row in graph["migrationDispositions"]
            if row["sourceKind"] == "legacy-language-unit" and row["sourceId"] == unit_id
        )
        migration.update({"disposition": "bounded-contradicted", "targetRef": None, "reason": reason})

    english_release = english_claim["materializedTargetId"]
    release = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "card-release" and row["entityId"] == english_release
    )
    release["sourceRecords"] = [url for url in release["sourceRecords"] if url != PRODUCT_URL]
    if IMAGE_URL not in release["sourceRecords"]:
        release["sourceRecords"].append(IMAGE_URL)
    release["sourceRecords"].sort()

    product = next(
        row["payload"] for row in graph["entities"]
        if row["entityType"] == "legacy-cardmarket-product" and row["payload"]["sourceId"] == CARDMARKET_URL
    )
    product.update({
        "disposition": "carried",
        "cardReleaseIds": [english_release],
        "reason": "1 established language-bearing card release(s)",
    })
    product_migration = next(
        row for row in graph["migrationDispositions"]
        if row["sourceKind"] == "legacy-cardmarket-product" and row["sourceId"] == CARDMARKET_URL
    )
    product_migration.update({
        "disposition": "carried",
        "targetRef": english_release,
        "targetRefs": [english_release],
        "reason": "1 established language-bearing card release(s)",
    })
    graph["summary"]["edges"] = len(graph["edges"])
    write(graph_path, graph)


def main() -> None:
    units_path = VERIFY / "units.json"
    units = read(units_path)
    by_id = {row["unitId"]: row for row in units}
    missing = sorted(({ENGLISH_ID} | set(EXCLUDED)) - set(by_id))
    if missing:
        raise SystemExit(f"Missing expected units: {', '.join(missing)}")

    english = by_id[ENGLISH_ID]
    if english["status"] != "confirmed":
        raise SystemExit(f"{ENGLISH_ID} has unexpected status {english['status']}")
    english.update({
        "variantName": VARIANT_NAME,
        "variantNameSource": VARIANT_SOURCE,
        "sourceUrl": IMAGE_URL,
        "sourceType": "Cardmarket exact card catalogue detail with retained product image",
        "providerId": "cardmarket-product-image",
        "sourceRef": "specimen:SPEC-0479",
        "corroborated": False,
        "evidence": ENGLISH_EVIDENCE,
        "checkedAt": CHECKED_AT,
    })

    journal_rows = [{
        "unitId": ENGLISH_ID,
        "lang": "English",
        "status": "confirmed",
        "source": IMAGE_URL,
        "evidence": ENGLISH_EVIDENCE,
        "at": CHECKED_AT,
    }]
    for unit_id, language in EXCLUDED.items():
        unit = by_id[unit_id]
        if unit["status"] not in {"confirmed", "contradicted"}:
            raise SystemExit(f"{unit_id} has unexpected status {unit['status']}")
        evidence = excluded_evidence(language)
        unit.update({
            "variantName": VARIANT_NAME,
            "variantNameSource": VARIANT_SOURCE,
            "status": "contradicted",
            "sourceUrl": None,
            "sourceType": "Collection owner attestation (not-printed adjudication); retained English product image for product identity only",
            "providerId": "owner-attestation",
            "sourceRef": None,
            "corroborated": False,
            "evidence": evidence,
            "checkedAt": CHECKED_AT,
        })
        journal_rows.append({
            "unitId": unit_id,
            "lang": language,
            "status": "contradicted",
            "source": "Owner attestation (domain expert)",
            "evidence": evidence,
            "at": CHECKED_AT,
        })
    write(units_path, units)

    journal_path = VERIFY / "evidence.jsonl"
    existing_rows = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    # Replace only the unpublished rows created by this pass. The image remains the English
    # identity evidence; the localized non-print decisions come from the owner adjudication.
    existing_rows = [
        row for row in existing_rows
        if not (
            row.get("unitId") in EXCLUDED
            and row.get("status") == "contradicted"
            and row.get("at") == CHECKED_AT
        )
    ]
    existing = {journal_key(row) for row in existing_rows}
    journal_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) for row in existing_rows)
        + "\n",
        encoding="utf-8",
    )
    with journal_path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in journal_rows:
            if journal_key(row) not in existing:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")

    adjudications_path = VERIFY / "owner_adjudications.json"
    adjudications = read(adjudications_path)
    decisions = {row["unitId"]: row for row in adjudications["decisions"]}
    for unit_id, language in EXCLUDED.items():
        decision = {
            "adjudicationId": f"OA-20260902-{unit_id}",
            "unitId": unit_id,
            "decision": "not-printed",
            "authority": "collection-owner",
            "basis": "multi-source-adjudication",
            "decidedAt": DATE,
            "rationale": excluded_evidence(language),
            "evidenceRefs": [PRODUCT_URL, f"unit:{unit_id}"],
        }
        if unit_id in decisions and decisions[unit_id]["adjudicationId"] != decision["adjudicationId"]:
            raise SystemExit(f"Conflicting existing adjudication for {unit_id}")
        decisions[unit_id] = decision
    adjudications["decisions"] = sorted(decisions.values(), key=lambda row: row["unitId"])
    adjudications["meta"]["generated"] = DATE
    write(adjudications_path, adjudications)

    update_graph()

    dataset_path = ROOT / "snorlax_cards.json"
    dataset = read(dataset_path)
    cards = [
        row for row in dataset["cards"]
        if row["setCode"] == "FLF" and row["number"] == "80" and row["variantToken"] == "V2"
    ]
    if len(cards) != 1:
        raise SystemExit(f"Expected one FLF 80 V2 product, found {len(cards)}")
    cards[0]["variantName"] = VARIANT_NAME
    cards[0]["variantNameSource"] = VARIANT_SOURCE
    dataset["meta"]["verification"].update({
        "confirmed": sum(row["status"] == "confirmed" for row in units),
        "contradicted": sum(row["status"] == "contradicted" for row in units),
        "needsManualReview": sum(row["status"] == "needs-manual-review" for row in units),
        "open": sum(row["status"] == "pending" for row in units),
        "totalUnits": len(units),
        "lastUpdated": DATE,
    })
    write(dataset_path, dataset)
    print("FLF 80 V2 retained for English only; six localized Cardmarket claims adjudicated not printed")


if __name__ == "__main__":
    main()
