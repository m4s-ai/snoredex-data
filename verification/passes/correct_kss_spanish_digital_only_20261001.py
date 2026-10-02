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
EDITION = "EDITION:WEST:Spanish:KSS"
RETIRED_IDS = {RELEASE, EDITION, "RARITYCLAIM:889242fc11a1d286", "SOURCEASSERTION:f5428c8d92feecb1"}
EVIDENCE = (
    "The collection owner accepted WikiDex's explicit statement that Bienvenidos a Kalos "
    "was released in Spanish only in Pokemon TCG Online, not physically, and requested "
    "correction on 2026-10-01. Its card list includes Snorlax 26/39. SPEC-0132 is a digital "
    "localized render, not corroboration of a physical printing. The previous general "
    "Bulbapedia language-list inference is superseded. Final not-printed status rests on "
    "the collection-owner adjudication; the external statement supplies its rationale."
)
OLD_LANGUAGES = "English, German, French, Italian, Spanish, Portuguese and Russian"
PHYSICAL_LANGUAGES = "English, German, French, Italian, Portuguese and Russian"
HISTORICAL_EVIDENCE = (
    "Historical Bulbapedia language statement and prior inference (the source includes "
    "digital-only Spanish; it is not a physical-print manifest or absence evidence): "
)
HISTORICAL_QUOTE = (
    "Historical quote (its KSS language list includes digital-only Spanish, not a "
    "physical-print manifest; owner correction 2026-10-01):"
)
LIST_CORRECTION = (
    "The collection owner's 2026-10-01 correction supersedes the previous seven-language "
    "inference: the physical KSS languages are English, German, French, Italian, Portuguese "
    "and Russian. Spanish was released digitally only. The existing owner decision for "
    "this unit is unchanged."
)
OLD_RATIONALE = (
    "That matches Bulbapedia's article, which states the print languages as a closed list "
    "of seven — " + OLD_LANGUAGES + " — all seven of which are confirmed here."
)
SPECIMEN_OBSERVATION = (
    "Spanish digital card render of Kalos Starter Set Snorlax 26/39, released in Pokemon "
    "TCG Online only. Pokemon Basico, Golpe Roca, Fuerza and 26/39 identify the localized "
    "digital card. WikiDex explicitly excludes a Spanish physical release; the owner "
    "adjudicated U0482 not printed on 2026-10-01. This image establishes no physical finish."
)


def write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def retirement_entities(graph):
    """Retire only the physical identity established exclusively by U0482."""
    retired = [e for e in graph["entities"] if e["entityId"] in RETIRED_IDS]
    for row in retired:
        if row["entityId"] == EDITION:
            assert row["payload"]["identity"]["establishingClaimIds"] == [CLAIM]
            assert not any(e["entityType"] == "card-release" and e["entityId"] != RELEASE
                           and e["payload"].get("setEditionId") == EDITION
                           for e in graph["entities"])
    return retired


def correct_graph(graph):
    """Apply the whole reviewed KSS correction on initial and partial replays."""
    retired = retirement_entities(graph)
    graph["entities"] = [e for e in graph["entities"] if e["entityId"] not in RETIRED_IDS]
    graph["edges"] = [e for e in graph["edges"]
                      if e["fromId"] not in RETIRED_IDS and e["toId"] not in RETIRED_IDS]
    products = set()
    for row in graph["entities"]:
        p = row["payload"]
        if row["entityId"] == CLAIM:
            p.update(evidenceStatus="contradicted", disposition="bounded-contradicted",
                     proposedTargetId=None, materializedTargetId=None, reason=EVIDENCE)
        if p.get("proposedCardReleaseId") == RELEASE:
            p.pop("proposedCardReleaseId")
        if row["entityType"] == "legacy-cardmarket-product" and CLAIM in p.get("claimIds", []):
            p["cardReleaseIds"] = [r for r in p.get("cardReleaseIds", []) if r != RELEASE]
            p["reason"] = f"{len(p['cardReleaseIds'])} established language-bearing card release(s)"
            products.add(p["sourceId"])
    for row in graph["migrationDispositions"]:
        if row["sourceKind"] == "legacy-language-unit" and row["sourceId"] == "U0482":
            row.update(disposition="bounded-contradicted", targetRef=None, reason=EVIDENCE)
        if row["sourceKind"] == "legacy-cardmarket-product" and row["sourceId"] in products:
            row["targetRefs"] = [r for r in row["targetRefs"] if r != RELEASE]
            row["targetRef"] = row["targetRefs"][0] if row["targetRefs"] else None
            row["reason"] = f"{len(row['targetRefs'])} established language-bearing card release(s)"
    return retired


def synchronize_manifest():
    path = V / "evidence" / "issue-266-spanish-evidence.json"
    manifest = read(path)
    specimen = next(r for r in read(V / "specimens.json")["specimens"]
                    if r["specimenId"] == "SPEC-0132")
    next(r for r in manifest["observations"] if r["specimenId"] == "SPEC-0132")["observed"] = specimen["observed"]
    write(path, manifest)


def qualify_language_evidence(evidence):
    """Preserve the source statement separately from the later owner conclusion."""
    historical = evidence.removeprefix(HISTORICAL_EVIDENCE).removesuffix(" " + LIST_CORRECTION)
    # Recover the source list overwritten by the previous correction, before its owner suffix.
    historical = historical.replace(PHYSICAL_LANGUAGES, OLD_LANGUAGES)
    return HISTORICAL_EVIDENCE + historical + " " + LIST_CORRECTION


def main():
    units = read(V / "units.json")
    unit = next(row for row in units if row["unitId"] == "U0482")
    assert (unit["setCode"], unit["number"], unit["language"]) == ("KSS", "26", "Spanish")
    prior = deepcopy(unit)
    graph = read(V / "authoritative_graph.json")
    retired = correct_graph(graph)
    unit.update(status="contradicted", providerId="owner-attestation", sourceUrl=None,
                sourceRef=None, sourceType="Collection owner attestation (not-printed adjudication)",
                corroborated=False, evidence=EVIDENCE, checkedAt=DATE + "T00:00:00",
                evidenceGranularity="product-or-set", evidenceIncludesCardList=True)
    prior_siblings = []
    for row in units:
        if row["setCode"] == "KSS" and (OLD_LANGUAGES in row["evidence"]
                or (LIST_CORRECTION in row["evidence"] and PHYSICAL_LANGUAGES in row["evidence"])):
            qualified = qualify_language_evidence(row["evidence"])
            if qualified != row["evidence"]:
                prior_siblings.append(deepcopy(row))
                row["evidence"] = qualified
        elif row["unitId"] == "U0586" and OLD_LANGUAGES in row["evidence"] \
                and "products. Quote:" in row["evidence"]:
            prior_siblings.append(deepcopy(row))
            row["evidence"] = row["evidence"].replace("products. Quote:", "products. " + HISTORICAL_QUOTE)
    specimens = read(V / "specimens.json")
    spec = next(row for row in specimens["specimens"] if row["specimenId"] == "SPEC-0132")
    prior_spec = deepcopy(spec)
    spec["observed"] = SPECIMEN_OBSERVATION
    spec.pop("physicalObservation", None)
    adj = read(V / "owner_adjudications.json")
    prior_adj = deepcopy(adj["decisions"])
    decision = dict(adjudicationId="OA-20261001-U0482", unitId="U0482",
        decision="not-printed", authority="collection-owner", basis="multi-source-adjudication",
        decidedAt=DATE, rationale=EVIDENCE, evidenceRefs=[URL, "unit:U0482", "specimen:SPEC-0132"])
    existing = next((row for row in adj["decisions"] if row["unitId"] == "U0482"), None)
    if existing is None:
        adj["decisions"].append(decision)
    else:
        existing.clear()
        existing.update(decision)
    for row in adj["decisions"]:
        if row["unitId"] in {u["unitId"] for u in units if u["setCode"] == "KSS"} \
                and OLD_RATIONALE in row["rationale"]:
            row["rationale"] = row["rationale"].replace(OLD_RATIONALE, LIST_CORRECTION)
            if URL not in row["evidenceRefs"]:
                row["evidenceRefs"].append(URL)
    adj["decisions"].sort(key=lambda row: row["unitId"])
    adj["meta"]["generated"] = DATE
    if prior != unit or prior_spec != spec or retired or prior_siblings or prior_adj != adj["decisions"]:
        with (V / "evidence.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(dict(unitId="U0482", at=DATE, status="contradicted",
                source="Owner attestation (domain expert)", evidence=EVIDENCE, rationaleSource=URL,
                supersededObservation=prior, supersededSpecimenObservation=prior_spec,
                supersededGraphEntities=retired, supersededSiblingObservations=prior_siblings,
                supersededAdjudications=[r for r in prior_adj if r not in adj["decisions"]]),
                ensure_ascii=False) + "\n")
    write(V / "units.json", units)
    write(V / "specimens.json", specimens)
    write(V / "owner_adjudications.json", adj)
    write(V / "authoritative_graph.json", graph)
    synchronize_manifest()
    data = read(ROOT / "snorlax_cards.json")
    data["meta"]["verification"].update(confirmed=sum(u["status"] == "confirmed" for u in units),
        contradicted=sum(u["status"] == "contradicted" for u in units), lastUpdated=DATE)
    write(ROOT / "snorlax_cards.json", data)
    assert spec["photographSha256"] == prior_spec["photographSha256"]
    assert spec["recordedAt"] == prior_spec["recordedAt"]


if __name__ == "__main__":
    main()
