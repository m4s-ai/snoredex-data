"""Repair PR #375's set-only language claims from retained exact-card photos."""
import json
from pathlib import Path
from reconcile_pr375_photo_identifiers import specimen_evidence_url

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {"U0171": "SPEC-0520", "U0603": "SPEC-0519", "U0602": "SPEC-0489", "U0170": "SPEC-0522", "U0604": "SPEC-0523", "U0092": "SPEC-0134"}


def main():
    path = ROOT / "verification/units.json"
    units = json.loads(path.read_text(encoding="utf-8"))
    specimens = {s["specimenId"]: s for s in json.loads(
        (ROOT / "verification/specimens.json").read_text(encoding="utf-8"))["specimens"]}
    observations = []
    for unit in units:
        if unit["unitId"] not in TARGETS:
            continue
        specimen = specimens[TARGETS[unit["unitId"]]]
        ref = "specimen:" + specimen["specimenId"]
        source_url = specimen_evidence_url(specimen)
        already_applied = unit.get("sourceRef") == ref and unit["evidenceGranularity"] == "specimen-or-card"
        if already_applied and unit.get("sourceUrl") == source_url:
            continue
        assert already_applied or unit["evidenceGranularity"] == "product-or-set", unit["unitId"]
        assert unit["unitId"] in specimen["citedBy"]
        assert all(unit[k] == specimen[k] for k in ("variant", "language"))
        if unit["setCode"] != specimen["setCode"]:
            rekeys = json.loads((ROOT / "verification/legacy_issue_rekeys.json").read_text(encoding="utf-8"))
            assert any(m["legacyUnitId"] == unit["unitId"] and m["sourceFirstRecordId"] in specimen["citedBy"]
                       for q in rekeys["questionSets"] for m in q["mappings"])
        assert int(unit["number"]) == int(specimen["number"].split("/")[0])
        assert (ROOT / "verification/specimens" / specimen["photograph"]).is_file()
        before = dict(unit)
        provider = {"U0602": "52poke", "U0092": "wikidex", "U0604": "inspected-specimen"}.get(unit["unitId"], "seller-listing-photo")
        source_type = {"wikidex": "WikiDex exact-card photograph", "52poke": "52poke exact-card image", "inspected-specimen": "Owner-supplied physical photograph"}.get(provider, "Seller listing photograph")
        unit.update(
            status="confirmed", sourceUrl=source_url,
            sourceType=source_type,
            providerId=provider, sourceRef=ref, corroborated=bool(unit.get("corroborated")),

            evidence=f"{ref} establishes the exact {unit['language']} card from its readable face and printed identifier. "
                     "The retained photograph supplies card-level language evidence; its physical finish is recorded separately on the specimen.",
            checkedAt="2026-09-10", evidenceGranularity="specimen-or-card",
            evidenceIncludesCardList=False,
        )
        observations.append({"unitId":unit["unitId"], "at":"2026-09-10", "status":"confirmed",
                             "source":unit["sourceUrl"], "sourceRef":ref, "providerId":unit["providerId"],
                             "evidence":unit["evidence"], "supersededObservation":before,
                             "reason":"PR #375 review: project the retained exact-card evidence to the language claim"})
    if observations:
        path.write_text(json.dumps(units,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
        with (ROOT / "verification/evidence.jsonl").open("a",encoding="utf-8",newline="\n") as out:
            for row in observations:
                out.write(json.dumps(row,ensure_ascii=False)+"\n")
    print(f"Applied {len(observations)} exact-card language observations")


if __name__ == "__main__":
    main()
