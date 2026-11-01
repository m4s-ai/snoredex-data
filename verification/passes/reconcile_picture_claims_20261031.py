"""Repair ten legacy claim references from retained exact-card images (#434/#440).

This bulk repair uses existing reviewed locality mappings for differing local codes or V-tokens.
It changes language evidence only; physical finishes remain the manifest/projector's concern.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from source_registry import specimen_provider
from specimen_groups import specimen_source_type

TARGETS = {
    "U0169": "SPEC-0323", "U0508": "SPEC-0553", "U0557": "SPEC-0622", "U0601": "SPEC-0552",
    "U0183": "SPEC-0669", "U0599": "SPEC-0664", "U0213": "SPEC-0665",
    "U0761": "SPEC-0666", "U0266": "SPEC-0667", "U0521": "SPEC-0668",
}


def main():
    path = ROOT / "verification/units.json"
    units = json.loads(path.read_text(encoding="utf-8"))
    specimens = {s["specimenId"]: s for s in json.loads(
        (ROOT / "verification/specimens.json").read_text(encoding="utf-8"))["specimens"]}
    rekeys = json.loads((ROOT / "verification/legacy_issue_rekeys.json").read_text(encoding="utf-8"))
    mappings = {m["legacyUnitId"]: m["sourceFirstRecordId"]
                for q in rekeys["questionSets"] for m in q["mappings"]}
    assert set(TARGETS) <= {u["unitId"] for u in units}
    observations = []
    for unit in units:
        if unit["unitId"] not in TARGETS:
            continue
        spec = specimens[TARGETS[unit["unitId"]]]
        assert unit["language"] == spec["language"]
        assert int(unit["number"]) == int(spec["number"].split("/")[0])
        assert unit["unitId"] in spec["citedBy"]
        if (unit["setCode"], unit["variant"]) != (spec["setCode"], spec["variant"]):
            assert mappings[unit["unitId"]] in spec["citedBy"]
        photo = ROOT / "verification/specimens" / spec["photograph"]
        assert "sha256:" + hashlib.sha256(photo.read_bytes()).hexdigest() == spec["photographSha256"]
        source_type = specimen_source_type(spec)
        source_url = spec["photographSource"]
        provider = specimen_provider(source_url, source_type)
        assert provider in {"seller-listing-photo", "pikaqian", "retailer-listing"}
        before = dict(unit)
        ref = "specimen:" + spec["specimenId"]
        unit.update(sourceUrl=source_url, sourceType=source_type, providerId=provider, sourceRef=ref,
                    evidence=f"{ref} visibly identifies {spec['language']} {spec['setCode']} "
                             f"{spec['number']} from its printed card face. The reviewed legacy/local "
                             "identity mapping is preserved; this language observation asserts no "
                             "additional physical finish or complete finish list.",
                    checkedAt=spec["recordedAt"], evidenceGranularity="specimen-or-card",
                    evidenceIncludesCardList=False)
        if unit != before:
            observations.append({"unitId": unit["unitId"], "at": "2026-10-31",
                                 "observedAt": spec["recordedAt"], "status": unit["status"],
                                 "source": source_url, "sourceRef": ref, "providerId": provider,
                                 "evidence": unit["evidence"], "supersededObservation": before,
                                 "reason": "#434 picture audit: replace set-only evidence with retained exact-card identity"})
    if "--check" in sys.argv:
        print(f"pending exact-card reference repairs: {len(observations)}")
        return bool(observations)
    if observations:
        path.write_text(json.dumps(units, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        with (ROOT / "verification/evidence.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            for observation in observations:
                stream.write(json.dumps(observation, ensure_ascii=False) + "\n")
    print(f"Applied {len(observations)} exact-card reference repairs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
