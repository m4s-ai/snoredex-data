#!/usr/bin/env python3
"""Apply the owner's English-only RR 33 V2 ruling; preserve regular RR 33."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERIFY = ROOT / "verification"
DATE = "2026-11-01"
TARGETS = {"U0473": "French", "U0474": "German", "U0475": "Italian"}
ISSUE = "https://github.com/m4s-ai/snoredex-data/issues/440"
QUOTE = "U0475 – RR 33/111 V2 die League variante gibt es nur auf englisch, im Gegensatz zum normalen Reverse Holo"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def main():
    units = read(VERIFY / "units.json")
    by_id = {row["unitId"]: row for row in units}
    decisions = read(VERIFY / "owner_adjudications.json")
    graph = read(VERIFY / "authoritative_graph.json")
    journal = VERIFY / "evidence.jsonl"
    history = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines() if line.strip()]
    new_history = []
    preserved = {key: copy.deepcopy(value) for key, value in by_id.items() if key not in TARGETS}
    for unit_id, language in TARGETS.items():
        unit = by_id[unit_id]
        assert (unit["setCode"], unit["number"], unit["variant"], unit["language"]) == ("RR", "33", "V2", language)
        rationale = (
            f'The collection owner explicitly ruled on {DATE}: "{QUOTE}". '
            f'This excludes the {language} RR 33/111 V2 League/Crosshatch promo only. '
            'Regular RR 33 V1, including its normal reverse-holo printing, remains separate. '
            'The previous base-card/set source did not establish the League treatment; '
            'not-printed is the owner decision, not an inference from source omission.'
        )
        decision_id = f"OA-20261101-{unit_id}"
        existing = [row for row in decisions["decisions"] if row["unitId"] == unit_id]
        assert not existing or existing[0]["adjudicationId"] == decision_id, unit_id
        if not existing:
            if not any(row.get("adjudicationId") == decision_id for row in history):
                new_history.append({
                    "unitId": unit_id, "at": DATE, "observedAt": DATE,
                    "status": "contradicted", "source": "Owner attestation (domain expert)",
                    "providerId": "owner-attestation", "evidence": rationale,
                    "adjudicationId": decision_id, "supersededObservation": copy.deepcopy(unit),
                })
            decisions["decisions"].append({
                "adjudicationId": decision_id, "unitId": unit_id, "decision": "not-printed",
                "authority": "collection-owner", "basis": "multi-source-adjudication",
                "decidedAt": DATE, "rationale": rationale, "evidenceRefs": [ISSUE, f"unit:{unit_id}"],
            })
        unit.update(status="contradicted", sourceUrl=None,
                    sourceType="Collection owner attestation (English-only League promo adjudication)",
                    providerId="owner-attestation", sourceRef=None, corroborated=False,
                    evidence=rationale, checkedAt=DATE, evidenceGranularity="specimen-or-card",
                    evidenceIncludesCardList=False)
        claim_id = f"CLAIM:legacy:{unit_id}"
        for entity in graph["entities"]:
            payload = entity["payload"]
            if entity["entityId"] == claim_id:
                payload.update(sourceRecord=None, evidenceStatus="contradicted",
                               disposition="bounded-contradicted", materializedTargetId=None,
                               reason="Owner excludes localized League promo; regular V1 independently establishes the release")
            for field in ("establishingClaimIds", "establishingEvidenceIds"):
                if claim_id in payload.get(field, []):
                    payload[field].remove(claim_id)
                    if entity["entityType"] == "card-release":
                        payload["nonEstablishingClaimIds"] = sorted(set(payload.get("nonEstablishingClaimIds", [])) | {claim_id})
        graph["edges"] = [edge for edge in graph["edges"]
                          if not (edge["fromId"] == claim_id and edge["relation"] == "materializes")]
        migration = next(row for row in graph["migrationDispositions"]
                         if row["sourceKind"] == "legacy-language-unit" and row["sourceId"] == unit_id)
        migration.update(disposition="bounded-contradicted", targetRef=None,
                         reason="Owner excludes localized League promo; regular V1 remains established")
    product = next(row["payload"] for row in graph["entities"]
                   if row["entityType"] == "legacy-cardmarket-product"
                   and row["payload"]["claimIds"] == [f"CLAIM:legacy:U{n:04d}" for n in range(472, 476)])
    english = next(row["payload"]["materializedTargetId"] for row in graph["entities"]
                   if row["entityId"] == "CLAIM:legacy:U0472")
    product.update(disposition="carried", cardReleaseIds=[english], reason="1 established language-bearing card release(s)")
    migration = next(row for row in graph["migrationDispositions"]
                     if row["sourceKind"] == "legacy-cardmarket-product" and row["sourceId"] == product["sourceId"])
    migration.update(disposition="carried", targetRef=english, targetRefs=[english], reason=product["reason"])
    graph["summary"]["edges"] = len(graph["edges"])
    assert preserved == {key: value for key, value in by_id.items() if key not in TARGETS}
    assert by_id["U0357"]["status"] == by_id["U0472"]["status"] == "confirmed"
    # Retain the old observation before replacing canonical evidence, including on interrupted replay.
    with journal.open("a", encoding="utf-8", newline="\n") as handle:
        for row in new_history:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    write(VERIFY / "units.json", units)
    write(VERIFY / "owner_adjudications.json", decisions)
    write(VERIFY / "authoritative_graph.json", graph)
    dataset = read(ROOT / "snorlax_cards.json")
    dataset["meta"]["verification"].update({
        "confirmed": sum(row["status"] == "confirmed" for row in units),
        "contradicted": sum(row["status"] == "contradicted" for row in units),
        "needsManualReview": sum(row["status"] == "needs-manual-review" for row in units),
        "open": sum(row["status"] == "pending" for row in units),
        "totalUnits": len(units), "lastUpdated": DATE,
    })
    write(ROOT / "snorlax_cards.json", dataset)
    print(f"RR 33 V2: English retained; three owner exclusions; {len(new_history)} journal observations appended")


if __name__ == "__main__":
    main()
