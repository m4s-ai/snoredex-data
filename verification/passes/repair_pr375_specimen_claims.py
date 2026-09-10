"""Repair PR #375's set-only language claims from retained exact-card photos."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {"U0171": "SPEC-0520", "U0603": "SPEC-0519", "U0602": "SPEC-0489"}


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
        if unit.get("sourceRef") == ref and unit["evidenceGranularity"] == "specimen-or-card":
            continue
        assert unit["evidenceGranularity"] == "product-or-set", unit["unitId"]
        assert unit["unitId"] in specimen["citedBy"]
        assert all(unit[k] == specimen[k] for k in ("variant", "language"))
        if unit["setCode"] != specimen["setCode"]:
            rekeys = json.loads((ROOT / "verification/legacy_issue_rekeys.json").read_text(encoding="utf-8"))
            assert any(m["legacyUnitId"] == unit["unitId"] and m["sourceFirstRecordId"] in specimen["citedBy"]
                       for q in rekeys["questionSets"] for m in q["mappings"])
        assert int(unit["number"]) == int(specimen["number"].split("/")[0])
        assert (ROOT / "verification/specimens" / specimen["photograph"]).is_file()
        before = dict(unit)
        unit.update(
            status="confirmed", sourceUrl=specimen["photographSource"],
            sourceType="Retained exact-card specimen image",
            providerId="52poke" if unit["unitId"] == "U0602" else "seller-listing-photo", sourceRef=ref, corroborated=False,
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
