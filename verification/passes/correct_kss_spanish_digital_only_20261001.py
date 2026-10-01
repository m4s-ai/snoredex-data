"""Retain the digital Spanish KSS evidence and retire its false physical release."""
import json
from copy import deepcopy
from pathlib import Path
from correct_flf80_build_a_bear_20260902 import read

ROOT = Path(__file__).resolve().parents[2]
V = ROOT / "verification"
DATE = "2026-10-01"
URL = "https://www.wikidex.net/index.php?title=XY_(TCG):_Bienvenidos_a_Kalos&oldid=3402059"
RELEASE = "RELEASE:WEST:Spanish:KSS:26:Snorlax-Rock-Smash-Strength"
CLAIM = "CLAIM:legacy:U0482"
EVIDENCE = (
    "The collection owner accepted WikiDex's explicit statement that Bienvenidos a Kalos "
    "was released in Spanish only in Pokemon TCG Online, not physically, and requested "
    "correction on 2026-10-01. Its card list includes Snorlax 26/39. SPEC-0132 is a digital "
    "localized render, not corroboration of a physical printing. The previous general "
    "Bulbapedia language-list inference is superseded. Final not-printed status rests on "
    "the collection-owner adjudication; the external statement supplies its rationale."
)


def write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def retire_dependent_assertion():
    """This catalogue-migration assertion is reviewed base, not a projected field."""
    path = V / "authoritative_graph.json"
    graph = read(path)
    assertion_id = "SOURCEASSERTION:f5428c8d92feecb1"
    retired = [e for e in graph["entities"] if e["entityId"] == assertion_id]
    if not retired:
        return
    assert retired[0]["payload"]["rarityClaimId"] == "RARITYCLAIM:889242fc11a1d286"
    assert not any(e["entityType"] == "card-release" and e["entityId"] == RELEASE
                   for e in graph["entities"])
    with (V / "evidence.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(dict(unitId="U0482", at=DATE, status="contradicted",
            source="Owner attestation (domain expert)", evidence=EVIDENCE,
            supersededGraphEntities=retired), ensure_ascii=False) + "\n")
    graph["entities"] = [e for e in graph["entities"] if e["entityId"] != assertion_id]
    graph["edges"] = [e for e in graph["edges"]
                      if e["fromId"] != assertion_id and e["toId"] != assertion_id]
    write(path, graph)


def synchronize_manifest():
    path = V / "evidence" / "issue-266-spanish-evidence.json"
    manifest = read(path)
    specimen = next(r for r in read(V / "specimens.json")["specimens"]
                    if r["specimenId"] == "SPEC-0132")
    next(r for r in manifest["observations"] if r["specimenId"] == "SPEC-0132")["observed"] = specimen["observed"]
    write(path, manifest)


def main():
    units = read(V / "units.json")
    unit = next(row for row in units if row["unitId"] == "U0482")
    if unit["providerId"] == "owner-attestation" and unit["evidence"] == EVIDENCE:
        unit["sourceType"] = "Collection owner attestation (not-printed adjudication)"
        write(V / "units.json", units)
        retire_dependent_assertion()
        for filename in ["units.json", "specimens.json", "owner_adjudications.json"]:
            write(V / filename, read(V / filename))
        synchronize_manifest()
        return
    assert (unit["setCode"], unit["number"], unit["language"]) == ("KSS", "26", "Spanish")
    prior = deepcopy(unit)
    graph = read(V / "authoritative_graph.json")
    removed = {RELEASE, "RARITYCLAIM:889242fc11a1d286", "SOURCEASSERTION:f5428c8d92feecb1"}
    retired = [row for row in graph["entities"] if row["entityId"] in removed]
    unit.update(status="contradicted", providerId="owner-attestation", sourceUrl=None,
                sourceRef=None, sourceType="Collection owner attestation (not-printed adjudication)",
                corroborated=False, evidence=EVIDENCE, checkedAt=DATE + "T00:00:00",
                evidenceGranularity="product-or-set", evidenceIncludesCardList=True)
    write(V / "units.json", units)
    specimens = read(V / "specimens.json")
    spec = next(row for row in specimens["specimens"] if row["specimenId"] == "SPEC-0132")
    prior_spec = deepcopy(spec)
    spec["observed"] = (
        "Spanish digital card render of Kalos Starter Set Snorlax 26/39, released in Pokemon "
        "TCG Online only. Pokemon Basico, Golpe Roca, Fuerza and 26/39 identify the localized "
        "digital card. WikiDex explicitly excludes a Spanish physical release; the owner "
        "adjudicated U0482 not printed on 2026-10-01. This image establishes no physical finish."
    )
    write(V / "specimens.json", specimens)
    synchronize_manifest()
    with (V / "evidence.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        for row in [dict(unitId="U0482", at=DATE, status=prior["status"], source=prior["sourceUrl"],
                         evidence=prior["evidence"], supersededObservation=prior,
                         supersededSpecimenObservation=prior_spec, supersededGraphEntities=retired),
                    dict(unitId="U0482", at=DATE, status="contradicted", source="Owner attestation (domain expert)",
                         evidence=EVIDENCE, rationaleSource=URL)]:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    adj = read(V / "owner_adjudications.json")
    assert not any(row["unitId"] == "U0482" for row in adj["decisions"])
    adj["decisions"].append(dict(adjudicationId="OA-20261001-U0482", unitId="U0482",
        decision="not-printed", authority="collection-owner", basis="multi-source-adjudication",
        decidedAt=DATE, rationale=EVIDENCE, evidenceRefs=[URL, "unit:U0482", "specimen:SPEC-0132"]))
    adj["decisions"].sort(key=lambda row: row["unitId"])
    adj["meta"]["generated"] = DATE
    write(V / "owner_adjudications.json", adj)
    graph["entities"] = [row for row in graph["entities"] if row["entityId"] not in removed]
    for row in graph["entities"]:
        p = row["payload"]
        if row["entityId"] == CLAIM:
            p.update(evidenceStatus="contradicted", disposition="bounded-contradicted",
                     proposedTargetId=None, materializedTargetId=None, reason=EVIDENCE)
        if p.get("proposedCardReleaseId") == RELEASE:
            p.pop("proposedCardReleaseId")
        if row["entityType"] == "legacy-cardmarket-product":
            p["cardReleaseIds"] = [r for r in p.get("cardReleaseIds", []) if r != RELEASE]
    graph["edges"] = [row for row in graph["edges"]
                       if row["fromId"] not in removed and row["toId"] not in removed]
    for row in graph["migrationDispositions"]:
        if row["sourceKind"] == "legacy-language-unit" and row["sourceId"] == "U0482":
            row.update(disposition="bounded-contradicted", targetRef=None, reason=EVIDENCE)
        if RELEASE in row.get("targetRefs", []):
            row["targetRefs"].remove(RELEASE)
            row["targetRef"] = row["targetRefs"][0] if row["targetRefs"] else None
            row["reason"] = f"{len(row['targetRefs'])} established language-bearing card release(s)"
    write(V / "authoritative_graph.json", graph)
    data = read(ROOT / "snorlax_cards.json")
    data["meta"]["verification"].update(confirmed=sum(u["status"] == "confirmed" for u in units),
        contradicted=sum(u["status"] == "contradicted" for u in units), lastUpdated=DATE)
    write(ROOT / "snorlax_cards.json", data)
    assert spec["photographSha256"] == prior_spec["photographSha256"]
    assert spec["recordedAt"] == prior_spec["recordedAt"]


if __name__ == "__main__":
    main()
